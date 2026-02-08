# API Specification

## Overview

RESTful API for the Company Knowledge Expert system. Built with FastAPI for async support and automatic OpenAPI documentation.

---

## Base URL

```
Production: https://api.company.com/knowledge/v1
Staging:    https://api-staging.company.com/knowledge/v1
Local:      http://localhost:8000/api/v1
```

---

## Authentication

All endpoints require authentication via API key or JWT token.

```http
Authorization: Bearer <token>
X-API-Key: <api_key>
```

### Rate Limits

| Tier | Requests/min | Requests/day |
|------|--------------|--------------|
| Free | 10 | 100 |
| Standard | 60 | 5,000 |
| Enterprise | 300 | Unlimited |

---

## Endpoints

### Query Endpoints

#### POST /query

Submit a question to the knowledge expert.

**Request:**
```json
{
  "query": "How do I reset my password?",
  "context": {
    "user_type": "customer",
    "session_id": "sess_abc123"
  },
  "options": {
    "include_sources": true,
    "max_sources": 3,
    "response_format": "markdown"
  }
}
```

**Response:**
```json
{
  "response_id": "resp_xyz789",
  "answer": "To reset your password, follow these steps:\n\n1. Go to **Settings** > **Account**\n2. Click **Reset Password**\n3. Enter your email address\n4. Check your inbox for the reset link\n\nThe link expires in 24 hours.",
  "confidence": 0.92,
  "sources": [
    {
      "title": "User Account Guide",
      "section": "Password Management",
      "url": "/docs/user-guide#password",
      "relevance_score": 0.95
    },
    {
      "title": "Security FAQ",
      "section": "Password Reset",
      "relevance_score": 0.88
    }
  ],
  "metadata": {
    "intent": "how_to",
    "processing_time_ms": 1250,
    "model_version": "v2.1.0"
  }
}
```

**Error Response:**
```json
{
  "error": {
    "code": "INSUFFICIENT_CONTEXT",
    "message": "Unable to find relevant information to answer this question",
    "suggestions": [
      "Try rephrasing your question",
      "Contact support at support@company.com"
    ]
  }
}
```

---

#### POST /query/stream

Stream response for real-time display.

**Request:** Same as `/query`

**Response:** Server-Sent Events (SSE)
```
event: chunk
data: {"text": "To reset your password, "}

event: chunk
data: {"text": "follow these steps:\n\n"}

event: chunk
data: {"text": "1. Go to Settings..."}

event: sources
data: {"sources": [...]}

event: done
data: {"response_id": "resp_xyz789", "confidence": 0.92}
```

---

### Feedback Endpoints

#### POST /feedback

Submit feedback on a response.

**Request:**
```json
{
  "response_id": "resp_xyz789",
  "feedback_type": "thumbs_up",
  "comment": null
}
```

**Thumbs Down with Details:**
```json
{
  "response_id": "resp_xyz789",
  "feedback_type": "thumbs_down",
  "issue_type": "wrong_answer",
  "comment": "The password reset is under Security, not Account",
  "correction": "To reset your password:\n1. Go to Settings > Security\n2. Click Reset Password..."
}
```

**Response:**
```json
{
  "feedback_id": "fb_abc123",
  "status": "received",
  "message": "Thank you for your feedback!"
}
```

---

#### GET /feedback/stats

Get feedback statistics (admin only).

**Response:**
```json
{
  "period": "last_7_days",
  "total_queries": 5420,
  "total_feedback": 1823,
  "feedback_rate": 0.336,
  "satisfaction_rate": 0.847,
  "by_intent": {
    "how_to": {"up": 523, "down": 87},
    "what_is": {"up": 312, "down": 45},
    "troubleshoot": {"up": 198, "down": 67}
  },
  "top_issues": [
    {"type": "outdated", "count": 34},
    {"type": "incomplete", "count": 28}
  ]
}
```

---

### Knowledge Management Endpoints

#### POST /knowledge/ingest

Ingest a new document (admin only).

**Request (multipart/form-data):**
```
file: [binary data]
metadata: {
  "title": "Product Guide v3.0",
  "category": "product",
  "audience": ["customer", "partner"],
  "tags": ["onboarding", "getting-started"]
}
```

**Response:**
```json
{
  "knowledge_item_id": "ki_def456",
  "status": "processing",
  "chunks_created": 0,
  "estimated_completion": "2025-01-15T10:30:00Z"
}
```

---

#### GET /knowledge/ingest/{job_id}

Check ingestion status.

**Response:**
```json
{
  "job_id": "ing_ghi789",
  "status": "completed",
  "knowledge_item_id": "ki_def456",
  "chunks_created": 45,
  "entities_extracted": 23,
  "qa_pairs_generated": 12,
  "completed_at": "2025-01-15T10:28:45Z"
}
```

---

#### GET /knowledge/items

List knowledge items (admin only).

**Query Parameters:**
- `type`: document, faq, workflow, product
- `category`: product, technical, policy, support
- `search`: text search
- `page`: page number (default: 1)
- `limit`: items per page (default: 20)

**Response:**
```json
{
  "items": [
    {
      "id": "ki_abc123",
      "type": "document",
      "title": "API Reference Guide",
      "category": "technical",
      "chunk_count": 78,
      "usage_count": 1245,
      "satisfaction_rate": 0.89,
      "updated_at": "2025-01-10T14:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 156,
    "total_pages": 8
  }
}
```

---

#### DELETE /knowledge/items/{id}

Delete a knowledge item (admin only).

**Response:**
```json
{
  "status": "deleted",
  "chunks_removed": 45,
  "embeddings_removed": 45
}
```

---

### Model Management Endpoints

#### GET /models

List model versions (admin only).

**Response:**
```json
{
  "models": [
    {
      "id": "mv_abc123",
      "type": "embedding",
      "name": "company-embeddings",
      "version": "v2.1.0",
      "is_active": true,
      "traffic_percentage": 100,
      "metrics": {
        "triplet_accuracy": 0.923
      },
      "created_at": "2025-01-08T00:00:00Z"
    },
    {
      "id": "mv_def456",
      "type": "generation",
      "name": "company-gpt",
      "version": "v1.3.0",
      "is_active": true,
      "traffic_percentage": 75,
      "metrics": {
        "satisfaction_rate": 0.867
      },
      "created_at": "2025-01-12T00:00:00Z"
    }
  ]
}
```

---

#### POST /models/{id}/traffic

Update model traffic allocation (admin only).

**Request:**
```json
{
  "traffic_percentage": 50
}
```

**Response:**
```json
{
  "model_id": "mv_def456",
  "previous_traffic": 25,
  "new_traffic": 50,
  "status": "updated"
}
```

---

#### POST /models/{id}/rollback

Rollback to a previous model version (admin only).

**Response:**
```json
{
  "status": "rolled_back",
  "deactivated_model": "mv_def456",
  "active_model": "mv_abc123",
  "message": "Traffic restored to v1.2.0"
}
```

---

### Training Endpoints

#### GET /training/jobs

List training jobs (admin only).

**Response:**
```json
{
  "jobs": [
    {
      "id": "tj_abc123",
      "type": "embedding",
      "status": "completed",
      "training_examples": 2500,
      "metrics": {
        "triplet_accuracy": 0.934,
        "improvement": "+1.2%"
      },
      "started_at": "2025-01-12T02:00:00Z",
      "completed_at": "2025-01-12T02:45:00Z"
    }
  ]
}
```

---

#### POST /training/trigger

Manually trigger a training job (admin only).

**Request:**
```json
{
  "type": "embedding",
  "options": {
    "min_quality": 0.8,
    "epochs": 3
  }
}
```

**Response:**
```json
{
  "job_id": "tj_xyz789",
  "status": "queued",
  "estimated_start": "2025-01-15T02:00:00Z"
}
```

---

#### GET /training/data/stats

Get training data statistics (admin only).

**Response:**
```json
{
  "embedding_triplets": {
    "total": 15420,
    "validated": 14200,
    "used_in_training": 12000,
    "pending": 1420
  },
  "llm_examples": {
    "total": 3200,
    "validated": 2800,
    "used_in_training": 2000,
    "pending": 400
  },
  "quality_distribution": {
    "high (>0.9)": 8500,
    "medium (0.7-0.9)": 5200,
    "low (<0.7)": 920
  }
}
```

---

### Health & Status Endpoints

#### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.5.0",
  "components": {
    "database": "healthy",
    "vector_store": "healthy",
    "llm_api": "healthy",
    "cache": "healthy"
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

---

#### GET /status

Detailed system status (admin only).

**Response:**
```json
{
  "system": {
    "uptime_hours": 720,
    "version": "1.5.0",
    "environment": "production"
  },
  "knowledge_base": {
    "total_items": 1250,
    "total_chunks": 45000,
    "last_ingestion": "2025-01-14T18:00:00Z"
  },
  "models": {
    "embedding": {
      "version": "v2.1.0",
      "last_trained": "2025-01-12T02:45:00Z"
    },
    "generation": {
      "version": "v1.3.0",
      "last_trained": "2025-01-01T03:30:00Z"
    }
  },
  "performance": {
    "avg_response_time_ms": 1250,
    "p95_response_time_ms": 2100,
    "queries_last_24h": 5420,
    "satisfaction_rate": 0.847
  }
}
```

---

## Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_REQUEST` | 400 | Malformed request body |
| `UNAUTHORIZED` | 401 | Invalid or missing authentication |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `RATE_LIMITED` | 429 | Rate limit exceeded |
| `INSUFFICIENT_CONTEXT` | 422 | Cannot answer question with available knowledge |
| `MODEL_UNAVAILABLE` | 503 | Model service temporarily unavailable |
| `INTERNAL_ERROR` | 500 | Internal server error |

---

## Webhooks

### Feedback Webhook

Receive notifications when feedback is submitted.

**Payload:**
```json
{
  "event": "feedback.submitted",
  "timestamp": "2025-01-15T10:30:00Z",
  "data": {
    "feedback_id": "fb_abc123",
    "response_id": "resp_xyz789",
    "feedback_type": "thumbs_down",
    "issue_type": "wrong_answer",
    "has_correction": true
  }
}
```

### Training Webhook

Receive notifications about training job status.

**Payload:**
```json
{
  "event": "training.completed",
  "timestamp": "2025-01-15T02:45:00Z",
  "data": {
    "job_id": "tj_abc123",
    "type": "embedding",
    "status": "completed",
    "model_version": "v2.2.0",
    "metrics": {
      "improvement": "+1.5%"
    }
  }
}
```

---

## SDK Examples

### Python

```python
from company_knowledge import KnowledgeClient

client = KnowledgeClient(api_key="your_api_key")

# Ask a question
response = client.query("How do I reset my password?")
print(response.answer)
print(f"Confidence: {response.confidence}")

# Submit feedback
client.feedback(
    response_id=response.id,
    feedback_type="thumbs_up"
)

# Stream response
for chunk in client.query_stream("Explain our pricing plans"):
    print(chunk.text, end="", flush=True)
```

### JavaScript

```javascript
import { KnowledgeClient } from '@company/knowledge-sdk';

const client = new KnowledgeClient({ apiKey: 'your_api_key' });

// Ask a question
const response = await client.query('How do I reset my password?');
console.log(response.answer);

// Submit feedback
await client.feedback({
  responseId: response.id,
  feedbackType: 'thumbs_up'
});

// Stream response
for await (const chunk of client.queryStream('Explain our pricing')) {
  process.stdout.write(chunk.text);
}
```

### cURL

```bash
# Query
curl -X POST https://api.company.com/knowledge/v1/query \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "How do I reset my password?"}'

# Feedback
curl -X POST https://api.company.com/knowledge/v1/feedback \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"response_id": "resp_xyz789", "feedback_type": "thumbs_up"}'
```

---

## OpenAPI Specification

Full OpenAPI 3.0 specification available at:
- `/docs` - Swagger UI
- `/redoc` - ReDoc
- `/openapi.json` - Raw OpenAPI JSON
