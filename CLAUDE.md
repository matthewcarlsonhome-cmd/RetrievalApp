# Knowledge Expert - Development Context

## Project Overview

**Knowledge Expert** is a production-ready, multi-tenant Retrieval-Augmented Generation (RAG) system that enables businesses to create AI-powered knowledge assistants from their documents. The system is deployed on Render and includes an embeddable widget for external websites.

**Live Deployment:** `https://knowledge-expert-ntdd.onrender.com`

## Quick Start for Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export ANTHROPIC_API_KEY="your-key"
export SECRET_KEY="your-secret"
export DATA_DIR="/data"  # On Render, or ./knowledge_expert/data locally

# Run locally
python -m knowledge_expert.app

# Or with gunicorn
gunicorn knowledge_expert.app:app --bind 0.0.0.0:8000
```

## Architecture Overview

```
knowledge_expert/
├── app.py              # Flask application, all API routes (~1700 lines)
├── models.py           # SQLite database models and migrations
├── config.py           # Configuration management
├── caching.py          # Response caching (in-memory + SQLite)
├── experiments.py      # A/B testing framework
├── ingestion/
│   ├── parsers.py      # Document parsing (12+ file types)
│   ├── chunker.py      # Text chunking strategies
│   └── embedder.py     # Sentence-transformer embeddings
├── retrieval/
│   ├── search.py       # Hybrid search (semantic + keyword + Q&A)
│   └── vector_store.py # ChromaDB wrapper with tenant isolation
├── generation/
│   ├── llm.py          # LLM client (Claude/OpenAI)
│   ├── prompts.py      # Prompt templates
│   ├── moderation.py   # Content moderation
│   └── qa_generator.py # Auto Q&A generation from documents
├── auth/
│   └── google_oauth.py # Google OAuth integration
├── integrations/
│   └── slack.py        # Slack bot integration
├── static/js/
│   └── widget.js       # Embeddable widget (popup + inline modes)
└── templates/          # Jinja2 HTML templates
```

## Key Design Decisions

### 1. Multi-Tenant Isolation
- Every entity (documents, chunks, Q&A, queries) has `organization_id`
- ChromaDB uses separate collections per tenant: `tenant_{org_id}`
- `get_tenant_context()` determines org from API key → session → (no fallback)
- Authentication required for all management routes

### 2. Hybrid Search Architecture
```python
# Default weights in retrieval/search.py
semantic_weight = 0.85   # Embedding similarity
keyword_weight = 0.7     # BM25-style keyword matching  
qa_weight = 1.0          # Direct Q&A (full confidence for curated answers)
```

### 3. Database Schema
SQLite with automatic migrations for existing databases:
```python
# In models.py _run_migrations()
migrations = [
    ("knowledge_items", "organization_id", "TEXT"),
    ("knowledge_items", "file_type", "TEXT"),
    ("knowledge_items", "metadata", "TEXT"),
    # ... etc
]
```

### 4. Widget Embedding
Two modes controlled by `data-container` attribute:
```html
<!-- Floating popup (default) -->
<script src=".../widget.js" data-api-key="KEY"></script>

<!-- Inline embed -->
<script src=".../widget.js" data-api-key="KEY" data-container="my-div"></script>
```

## Critical Files to Understand

| File | Purpose | Key Functions |
|------|---------|---------------|
| `app.py` | All routes, auth, tenant context | `get_tenant_context()`, `login_required` |
| `models.py` | Database schema, migrations | `_run_migrations()`, `Database` class |
| `search.py` | Hybrid search implementation | `HybridSearch.search()` |
| `vector_store.py` | ChromaDB wrapper | `get_tenant_store()` |
| `widget.js` | Embeddable widget | `init()`, `initInline()`, `initPopup()` |

## Common Development Tasks

### Adding a New API Endpoint
```python
@app.route('/api/new-endpoint', methods=['POST'])
@login_required  # Add if requires authentication
def api_new_endpoint():
    organization_id, user_id = get_tenant_context()
    # ... implementation
```

### Adding a Database Column
Add to migrations list in `models.py`:
```python
migrations = [
    # ... existing
    ("table_name", "new_column", "TEXT DEFAULT ''"),
]
```

### Modifying Search Behavior
Edit weights in `retrieval/search.py` `HybridSearch.search()` method.

## Challenges Solved (Reference for Future Issues)

### 1. "Table has no column named X"
**Cause:** Column exists in model but not in migrations list
**Fix:** Add to `_run_migrations()` in `models.py`

### 2. Widget Shows "Loading..." Forever
**Cause:** Missing CORS headers or wrong container mode
**Fix:** 
- Ensure `flask-cors` installed and CORS enabled for `/api/*`
- Add `data-container="id"` for inline mode

### 3. Direct Q&A Shows Low Confidence (10%)
**Cause:** Search weights multiplying scores incorrectly
**Fix:** Set `qa_weight=1.0` in search.py

### 4. Anonymous Users See All Documents
**Cause:** `get_tenant_context()` falling back to default org
**Fix:** Remove default org fallback, require auth

### 5. ChromaDB "Readonly Database" Error
**Cause:** Corrupted ChromaDB after partial delete
**Fix:** Delete `/data/chroma_db/*` and restart service

### 6. Documents Upload But Not Searchable
**Cause:** Chunks created but not embedded (embedder unavailable)
**Fix:** Check `/api/health` for component status, ensure embedder loads

## Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...     # Claude API key
SECRET_KEY=random-secret          # Flask session secret

# Optional
DATA_DIR=/data                    # Persistent storage path
GOOGLE_CLIENT_ID=...              # For Google OAuth
GOOGLE_CLIENT_SECRET=...
ADMIN_EMAILS=admin@example.com    # Auto-admin these users
OPENAI_API_KEY=...                # Fallback LLM
```

## Testing Checklist

Before deploying changes:
1. [ ] Document upload works and creates chunks
2. [ ] Search returns relevant results with citations
3. [ ] Widget works on external site (test CORS)
4. [ ] Anonymous users cannot access /upload, /admin, /qa
5. [ ] Logged-in users only see their own documents
6. [ ] `/api/health` shows all components "ok"

## Render Deployment Notes

- **Disk:** Must attach persistent disk at `/data` for data persistence
- **Build Command:** `pip install -r requirements.txt && python -m knowledge_expert.scripts.seed_data`
- **Start Command:** `gunicorn knowledge_expert.app:app`
- **Environment:** Set all required env vars in Render dashboard

## API Authentication

### Session-Based (Web UI)
- Login via `/auth/google` or `/api/auth/login`
- Session cookie stores `user_id` and `organization_id`

### API Key (Widget/External)
- Header: `Authorization: Bearer <api_key>`
- Get key from `/api/auth/api-key` when logged in
- Key is tied to user's organization

## File Type Support

PDF, DOCX, XLSX, PPTX, MD, HTML, TXT, JSON, CSV, EML, MBOX, audio (via Whisper)

## Code Statistics

- ~9,000 lines Python (knowledge_expert module)
- ~500 lines JavaScript (widget)
- 12+ supported file types
- 3 search strategies
- 5 chunking strategies
