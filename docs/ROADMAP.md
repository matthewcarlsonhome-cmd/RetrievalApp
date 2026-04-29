# Knowledge Expert - Development Roadmap

## Current State (v1.0 - Production Ready)

### Completed Features
- [x] Multi-tenant document management with organization isolation
- [x] 12+ file type parsing (PDF, DOCX, XLSX, PPTX, MD, HTML, JSON, CSV, EML, MBOX, TXT, audio)
- [x] Hybrid search (semantic + keyword + direct Q&A)
- [x] LLM response generation with Claude API
- [x] User authentication (email/password + Google OAuth)
- [x] Embeddable widget (floating popup + inline modes)
- [x] CORS-enabled API for cross-origin widget
- [x] Auto Q&A generation from documents
- [x] Response caching (in-memory + SQLite)
- [x] Analytics dashboard with query tracking
- [x] User feedback collection
- [x] Knowledge gap detection
- [x] Database migration system for schema evolution
- [x] Persistent storage with Render Disks

---

## Phase 2: Enhanced Intelligence (Next Priority)

### 2.1 Conversation Memory
**Goal:** Multi-turn conversations with context retention

**Implementation:**
```python
# New table: conversations
CREATE TABLE conversations (
    id TEXT PRIMARY KEY,
    organization_id TEXT,
    user_id TEXT,
    created_at TEXT,
    last_message_at TEXT,
    summary TEXT  # LLM-generated conversation summary
);

# New table: conversation_messages
CREATE TABLE conversation_messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT,
    role TEXT,  # user, assistant
    content TEXT,
    created_at TEXT
);
```

**API Changes:**
```python
@app.route('/api/query', methods=['POST'])
def api_query():
    data = request.get_json()
    conversation_id = data.get('conversation_id')  # Optional
    
    # If conversation exists, include recent context in prompt
    if conversation_id:
        history = get_conversation_history(conversation_id, limit=5)
        context = format_history_for_prompt(history)
```

**Estimated Effort:** 2-3 days

---

### 2.2 Document Versioning
**Goal:** Track document changes over time, allow rollback

**Implementation:**
```python
# New table: document_versions
CREATE TABLE document_versions (
    id TEXT PRIMARY KEY,
    document_id TEXT,
    version_number INTEGER,
    content TEXT,
    content_hash TEXT,
    created_at TEXT,
    created_by TEXT
);
```

**Features:**
- Automatic version creation on re-upload
- Version diff viewer
- Rollback to previous version
- Re-embed specific versions

**Estimated Effort:** 2-3 days

---

### 2.3 Smart Chunking Improvements
**Goal:** Better chunk boundaries using semantic understanding

**Implementation:**
```python
# In ingestion/chunker.py
def semantic_chunk(content: str, model: str = "gpt-3.5-turbo") -> List[Chunk]:
    """Use LLM to identify natural topic boundaries."""
    # 1. Split into paragraphs
    # 2. Ask LLM to group related paragraphs
    # 3. Create chunks at semantic boundaries
```

**Estimated Effort:** 1-2 days

---

## Phase 3: Enterprise Features

### 3.1 Team & Permissions System
**Goal:** Fine-grained access control within organizations

**New Tables:**
```sql
CREATE TABLE teams (
    id TEXT PRIMARY KEY,
    organization_id TEXT,
    name TEXT,
    created_at TEXT
);

CREATE TABLE team_members (
    team_id TEXT,
    user_id TEXT,
    role TEXT,  # admin, member, viewer
    PRIMARY KEY (team_id, user_id)
);

CREATE TABLE document_permissions (
    document_id TEXT,
    team_id TEXT,
    permission TEXT,  # read, write, admin
    PRIMARY KEY (document_id, team_id)
);
```

**Estimated Effort:** 3-4 days

---

### 3.2 Audit Logging
**Goal:** Track all actions for compliance

**Implementation:**
```python
# New table: audit_log
CREATE TABLE audit_log (
    id TEXT PRIMARY KEY,
    organization_id TEXT,
    user_id TEXT,
    action TEXT,  # upload, delete, query, login, etc.
    resource_type TEXT,
    resource_id TEXT,
    details TEXT,  # JSON
    ip_address TEXT,
    created_at TEXT
);

# Decorator for automatic logging
@audit_log(action="document.upload")
def api_upload_document():
    ...
```

**Estimated Effort:** 2 days

---

### 3.3 SSO Integration (SAML/OIDC)
**Goal:** Enterprise single sign-on support

**Dependencies:**
```
python-saml>=1.15.0
authlib>=1.2.0
```

**Implementation:**
- SAML 2.0 for enterprise IdPs (Okta, Azure AD)
- OIDC for modern providers
- Auto-provisioning users from IdP

**Estimated Effort:** 4-5 days

---

## Phase 4: Advanced RAG

### 4.1 Re-ranking with Cross-Encoders
**Goal:** Improve retrieval precision with two-stage ranking

**Implementation:**
```python
# In retrieval/search.py
from sentence_transformers import CrossEncoder

class HybridSearch:
    def __init__(self):
        self.cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
    
    def search(self, query: str, n_results: int = 5):
        # Stage 1: Get top 20 candidates with current method
        candidates = self._get_candidates(query, n=20)
        
        # Stage 2: Re-rank with cross-encoder
        pairs = [(query, c.content) for c in candidates]
        scores = self.cross_encoder.predict(pairs)
        
        # Return top n after re-ranking
        reranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
        return [c for c, s in reranked[:n_results]]
```

**Estimated Effort:** 1-2 days

---

### 4.2 Query Expansion
**Goal:** Improve recall by expanding queries with synonyms/related terms

**Implementation:**
```python
def expand_query(query: str, llm_client) -> List[str]:
    """Generate query variations for better recall."""
    prompt = f"""Generate 3 alternative phrasings for this search query:
    Query: {query}
    
    Return as JSON: ["variation1", "variation2", "variation3"]"""
    
    response = llm_client.generate(prompt)
    variations = json.loads(response)
    return [query] + variations
```

**Estimated Effort:** 1 day

---

### 4.3 Hypothetical Document Embeddings (HyDE)
**Goal:** Generate hypothetical answer, embed that instead of query

**Implementation:**
```python
def hyde_search(query: str, llm_client, embedder, vector_store):
    # Generate hypothetical answer
    prompt = f"Write a detailed answer to: {query}"
    hypothetical = llm_client.generate(prompt)
    
    # Embed the hypothetical answer (not the query)
    embedding = embedder.embed([hypothetical])[0]
    
    # Search with hypothetical embedding
    results = vector_store.search(embedding, n_results=5)
    return results
```

**Estimated Effort:** 1 day

---

## Phase 5: Integrations

### 5.1 Slack Bot (Enhance Existing)
**Current:** Basic event handling
**Enhanced:**
- Slash commands (`/ask <question>`)
- Thread-based conversations
- Document upload via DM
- Admin commands for managing knowledge base

**Estimated Effort:** 2-3 days

---

### 5.2 Microsoft Teams Integration
**Implementation:**
- Bot Framework SDK
- Adaptive Cards for rich responses
- Tab app for document management

**Estimated Effort:** 3-4 days

---

### 5.3 Zapier/Make Integration
**Goal:** Connect to 5000+ apps via automation platforms

**Implementation:**
- Webhook triggers for new documents, queries, feedback
- Actions for querying, uploading, managing Q&A

**Estimated Effort:** 2-3 days

---

### 5.4 API Webhook System
**Goal:** Push notifications for events

**Implementation:**
```python
# New table: webhooks
CREATE TABLE webhooks (
    id TEXT PRIMARY KEY,
    organization_id TEXT,
    url TEXT,
    events TEXT,  # JSON array: ["document.uploaded", "query.received"]
    secret TEXT,
    active INTEGER DEFAULT 1,
    created_at TEXT
);

# Webhook delivery
def deliver_webhook(event_type: str, payload: dict, org_id: str):
    webhooks = get_webhooks_for_event(event_type, org_id)
    for webhook in webhooks:
        signature = hmac.new(webhook.secret, json.dumps(payload), 'sha256').hexdigest()
        requests.post(webhook.url, json=payload, headers={'X-Signature': signature})
```

**Estimated Effort:** 2 days

---

## Phase 6: Analytics & Optimization

### 6.1 Advanced Analytics Dashboard
**Features:**
- Query volume over time
- Most/least answered topics
- User engagement metrics
- Response quality trends
- Knowledge coverage heatmap

**Estimated Effort:** 3-4 days

---

### 6.2 A/B Testing Framework (Enhance Existing)
**Current:** Basic experiment tracking
**Enhanced:**
- Statistical significance calculation
- Automatic winner selection
- Multi-variate testing
- Feature flags integration

**Estimated Effort:** 2-3 days

---

### 6.3 Cost Optimization
**Features:**
- LLM token usage tracking per query
- Caching hit rate monitoring
- Embedding cost analysis
- Recommendations for optimization

**Implementation:**
```python
# Track costs per query
class CostTracker:
    COSTS = {
        'claude-3-opus': {'input': 0.015, 'output': 0.075},  # per 1K tokens
        'claude-3-sonnet': {'input': 0.003, 'output': 0.015},
        'embedding': 0.0001  # per 1K tokens
    }
    
    def track_query(self, model, input_tokens, output_tokens, embedding_tokens):
        cost = (
            self.COSTS[model]['input'] * input_tokens / 1000 +
            self.COSTS[model]['output'] * output_tokens / 1000 +
            self.COSTS['embedding'] * embedding_tokens / 1000
        )
        # Store for analytics
```

**Estimated Effort:** 1-2 days

---

## Phase 7: Self-Service & White-Label

### 7.1 Self-Service Onboarding
**Features:**
- Sign-up flow with email verification
- Organization creation wizard
- Guided document upload
- Widget configuration UI
- Billing integration (Stripe)

**Estimated Effort:** 5-7 days

---

### 7.2 White-Label Customization
**Features:**
- Custom branding (logo, colors, fonts)
- Custom domain support
- Branded widget
- Custom email templates

**Estimated Effort:** 3-4 days

---

### 7.3 Usage-Based Billing
**Implementation:**
```python
# Track usage
class UsageTracker:
    def track_query(self, org_id, tokens_used):
        # Increment monthly usage
        
    def track_storage(self, org_id, bytes_added):
        # Update storage usage
        
    def check_limits(self, org_id) -> bool:
        # Check against plan limits
```

**Tiers:**
- Free: 100 queries/month, 10 documents
- Pro: 10K queries/month, 500 documents
- Enterprise: Unlimited

**Estimated Effort:** 3-4 days

---

## Implementation Priority Matrix

| Feature | Impact | Effort | Priority |
|---------|--------|--------|----------|
| Conversation Memory | High | Medium | P1 |
| Re-ranking | High | Low | P1 |
| Audit Logging | Medium | Low | P1 |
| Query Expansion | Medium | Low | P2 |
| Document Versioning | Medium | Medium | P2 |
| Teams/Permissions | High | High | P2 |
| Slack Bot Enhanced | Medium | Medium | P2 |
| Webhooks | Medium | Low | P2 |
| Advanced Analytics | Medium | Medium | P3 |
| Self-Service | High | High | P3 |
| SSO/SAML | High | High | P3 |
| White-Label | Medium | Medium | P4 |
| Teams Integration | Medium | High | P4 |

---

## Development Guidelines for New Features

### 1. Adding a New Feature
```bash
# Create feature branch
git checkout -b feature/your-feature

# Implement with tests
# Update CLAUDE.md if architecture changes
# Add migration if DB schema changes

# Test locally
python -m pytest tests/

# Deploy to staging (if available)
# Test on staging

# Create PR
git push origin feature/your-feature
```

### 2. Database Changes
- Always add to `_run_migrations()` in `models.py`
- Never modify existing migrations
- Test with existing production data copy

### 3. API Changes
- Maintain backwards compatibility
- Version breaking changes: `/api/v2/...`
- Update CLAUDE.md API documentation

### 4. Widget Changes
- Test in both popup and inline modes
- Test cross-origin on external site
- Maintain backwards compatibility for existing integrations

---

## Technical Debt to Address

1. **Test Coverage:** Add comprehensive tests for all endpoints
2. **Error Handling:** Standardize error responses across all endpoints
3. **Logging:** Add structured logging with correlation IDs
4. **Rate Limiting:** Add per-user/per-org rate limits
5. **Input Validation:** Use Pydantic or similar for request validation
6. **API Documentation:** Generate OpenAPI/Swagger docs
7. **Type Hints:** Add comprehensive type hints throughout
