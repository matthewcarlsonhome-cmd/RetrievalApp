# Knowledge Expert - System Design Document

**Version:** 1.0.0
**Last Updated:** February 2026
**Status:** Production (Deployed on Render)

---

## Executive Summary

Knowledge Expert is a multi-tenant Retrieval-Augmented Generation (RAG) platform that enables businesses to create AI-powered knowledge assistants from their documents. The system combines semantic search, keyword matching, and curated Q&A to deliver accurate, grounded responses with source citations.

**Key Differentiators:**
- True multi-tenant isolation (not just user-level, but organization-level)
- Hybrid search combining 3 retrieval strategies
- Embeddable widget for external websites
- Auto-generated Q&A from documents
- Production-ready with persistent storage and authentication

---

## System Architecture

### High-Level Overview

```
┌────────────────────────────────────────────────────────────────────────┐
│                          Client Layer                                   │
├─────────────────────┬─────────────────────┬────────────────────────────┤
│   Web Application   │   Embeddable Widget │      External APIs         │
│   (Flask Templates) │   (JavaScript)      │   (REST + API Keys)        │
└─────────────────────┴─────────────────────┴────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────────┐
│                       Application Layer (Flask)                         │
├─────────────────────┬─────────────────────┬────────────────────────────┤
│   Authentication    │   Tenant Context    │      Rate Limiting         │
│   (Session/API Key) │   (Organization)    │      (Future)              │
└─────────────────────┴─────────────────────┴────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────────┐
│                         Service Layer                                   │
├──────────────┬──────────────┬──────────────┬──────────────┬────────────┤
│  Ingestion   │  Retrieval   │  Generation  │  Analytics   │  Caching   │
│  Pipeline    │  Engine      │  Engine      │  Engine      │  Layer     │
└──────────────┴──────────────┴──────────────┴──────────────┴────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────────┐
│                          Data Layer                                     │
├────────────────────────┬───────────────────────┬───────────────────────┤
│   SQLite Database      │   ChromaDB Vectors    │   File Storage        │
│   (Metadata, Users)    │   (Embeddings)        │   (Original Docs)     │
└────────────────────────┴───────────────────────┴───────────────────────┘
```

### Component Details

#### 1. Ingestion Pipeline (`ingestion/`)

**Parsers (`parsers.py`):**
| Format | Library | Notes |
|--------|---------|-------|
| PDF | PyMuPDF (fitz) | Extracts text, preserves page numbers |
| DOCX | python-docx | Extracts paragraphs and tables |
| XLSX | openpyxl | Converts sheets to text tables |
| PPTX | python-pptx | Extracts slide content |
| HTML | BeautifulSoup | Strips tags, preserves structure |
| Markdown | markdown | Converts to plain text |
| JSON | built-in | Flattens nested structures |
| CSV | built-in | Converts to readable format |
| Email | email module | Extracts headers and body |
| Audio | Whisper (optional) | Transcription |

**Chunker (`chunker.py`):**
```python
class ChunkingStrategy(Enum):
    SENTENCE = "sentence"      # Split on sentence boundaries
    FIXED = "fixed"            # Fixed character count
    PARAGRAPH = "paragraph"    # Split on paragraphs
    SECTION = "section"        # Split on headers/sections
    SEMANTIC = "semantic"      # LLM-guided (future)
```

Default: `SENTENCE` with 500 character chunks, 50 character overlap

**Embedder (`embedder.py`):**
- Model: `all-MiniLM-L6-v2` (384 dimensions)
- Batch processing for efficiency
- Fallback to mock embeddings if model unavailable

#### 2. Retrieval Engine (`retrieval/`)

**Hybrid Search (`search.py`):**
```python
class HybridSearch:
    def search(
        self,
        query: str,
        n_results: int = 5,
        semantic_weight: float = 0.85,   # Embedding similarity
        keyword_weight: float = 0.7,     # BM25-style matching
        qa_weight: float = 1.0           # Direct Q&A (full confidence)
    ) -> List[SearchResult]:
        # 1. Semantic search via ChromaDB
        semantic_results = self._semantic_search(query, n_results * 2)
        
        # 2. Keyword search via SQLite FTS
        keyword_results = self._keyword_search(query, n_results * 2)
        
        # 3. Direct Q&A matching
        qa_results = self._qa_search(query, n_results)
        
        # 4. Combine, deduplicate, rank
        return self._combine_results(all_results, n_results)
```

**Vector Store (`vector_store.py`):**
- ChromaDB with persistent storage
- Tenant isolation via separate collections: `tenant_{organization_id}`
- HNSW index for approximate nearest neighbor search
- Cosine similarity metric

#### 3. Generation Engine (`generation/`)

**LLM Client (`llm.py`):**
```python
class LLMClient:
    def generate(self, prompt: str, context: List[str]) -> str:
        # Uses Claude API (primary) or OpenAI (fallback)
        # Includes retrieved context in system prompt
        # Returns grounded response
```

**Prompt Builder (`prompts.py`):**
```python
SYSTEM_PROMPT = """You are a helpful assistant answering questions based on 
the provided context. Always cite your sources. If the context doesn't 
contain the answer, say so clearly."""

def build_prompt(query: str, context: List[SearchResult]) -> str:
    context_text = "\n\n".join([
        f"[Source: {r.document_title}]\n{r.content}"
        for r in context
    ])
    return f"{SYSTEM_PROMPT}\n\nContext:\n{context_text}\n\nQuestion: {query}"
```

**Moderation (`moderation.py`):**
- Input validation (length, format)
- Content moderation (blocked topics)
- Rate limiting (future)

#### 4. Data Models (`models.py`)

**Core Entities:**
```sql
-- Organizations (tenants)
CREATE TABLE organizations (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT UNIQUE,
    settings TEXT,  -- JSON
    created_at TEXT
);

-- Users
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    organization_id TEXT,
    role TEXT DEFAULT 'member',  -- admin, member
    password_hash TEXT,
    api_key TEXT UNIQUE,
    google_id TEXT,
    created_at TEXT,
    last_login TEXT
);

-- Knowledge Items (documents)
CREATE TABLE knowledge_items (
    id TEXT PRIMARY KEY,
    organization_id TEXT,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    type TEXT DEFAULT 'document',
    source_file TEXT,
    file_type TEXT,
    category TEXT,
    tags TEXT,  -- JSON array
    metadata TEXT,  -- JSON
    chunk_count INTEGER DEFAULT 0,
    chunking_strategy TEXT DEFAULT 'sentence',
    chunk_size INTEGER DEFAULT 500,
    access_level TEXT DEFAULT 'organization',
    created_by TEXT,
    source_url TEXT,
    page_count INTEGER DEFAULT 0,
    created_at TEXT,
    updated_at TEXT
);

-- Chunks (for retrieval)
CREATE TABLE chunks (
    id TEXT PRIMARY KEY,
    knowledge_item_id TEXT NOT NULL,
    organization_id TEXT,
    content TEXT NOT NULL,
    chunk_index INTEGER,
    section_title TEXT,
    token_count INTEGER DEFAULT 0,
    start_char INTEGER DEFAULT 0,
    end_char INTEGER DEFAULT 0,
    page_number INTEGER
);

-- Direct Q&A pairs
CREATE TABLE direct_qa (
    id TEXT PRIMARY KEY,
    organization_id TEXT,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    category TEXT DEFAULT 'General',
    tags TEXT,  -- JSON array
    use_count INTEGER DEFAULT 0,
    created_by TEXT,
    created_at TEXT
);

-- Query history
CREATE TABLE queries (
    id TEXT PRIMARY KEY,
    organization_id TEXT,
    user_id TEXT,
    query_text TEXT NOT NULL,
    response TEXT,
    chunks_used TEXT,  -- JSON array of chunk IDs
    chunk_scores TEXT,  -- JSON array of scores
    response_time_ms INTEGER DEFAULT 0,
    feedback_score INTEGER,
    feedback_comment TEXT,
    is_good_example INTEGER DEFAULT 0,
    conversation_id TEXT,
    created_at TEXT
);
```

**Automatic Migrations:**
```python
def _run_migrations(self, conn):
    """Add missing columns to existing databases."""
    migrations = [
        ("knowledge_items", "organization_id", "TEXT"),
        ("knowledge_items", "file_type", "TEXT"),
        ("knowledge_items", "metadata", "TEXT"),
        # ... all columns that might be missing
    ]
    for table, column, col_type in migrations:
        # Check if column exists, add if not
```

---

## Authentication & Authorization

### Authentication Methods

1. **Session-Based (Web UI):**
   ```python
   @app.route('/api/auth/login', methods=['POST'])
   def login():
       # Validate credentials
       # Set session['user_id'] and session['organization_id']
   ```

2. **Google OAuth:**
   ```python
   @app.route('/auth/google')
   def google_login():
       # Redirect to Google OAuth
       # On callback, create/update user
       # Auto-assign to organization (create if needed)
   ```

3. **API Key (Widget/External):**
   ```python
   # In request headers
   Authorization: Bearer <api_key>
   
   # Checked first in get_tenant_context()
   ```

### Authorization Flow

```python
def get_tenant_context():
    """Determine current tenant from auth context."""
    # 1. Check API key in Authorization header
    if api_key := get_api_key_from_header():
        user = db.get_user_by_api_key(api_key)
        return user.organization_id, user.id
    
    # 2. Check session
    if 'user_id' in session:
        return session['organization_id'], session['user_id']
    
    # 3. No fallback - require explicit auth
    return None, None

@login_required
def protected_route():
    # Decorator redirects to login if no session
```

---

## Widget Architecture

### Embedding Modes

**1. Floating Popup (Default):**
```html
<script src="https://app.com/static/js/widget.js" 
        data-api-key="KEY"></script>
```
- Creates fixed-position chat button
- Opens popup on click
- Closeable, persists position

**2. Inline Embed:**
```html
<div id="my-container"></div>
<script src="https://app.com/static/js/widget.js" 
        data-api-key="KEY"
        data-container="my-container"></script>
```
- Replaces container contents
- Adapts to container size
- No floating elements

### Widget Initialization Flow

```javascript
// 1. Auto-detect from script tag
const scriptTag = document.querySelector('script[data-api-key]');
config.apiKey = scriptTag.getAttribute('data-api-key');
config.apiUrl = new URL(scriptTag.src).origin;
config.container = scriptTag.getAttribute('data-container');

// 2. Determine mode
isInlineMode = !!config.container;

// 3. Initialize appropriate mode
if (isInlineMode) {
    initInline();  // Render into container
} else {
    initPopup();   // Create floating button + popup
}

// 4. Handle late DOM load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();  // DOM already loaded
}
```

### CORS Configuration

```python
from flask_cors import CORS

# Enable CORS for API endpoints
CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=False)
```

---

## Caching Strategy

### Response Cache (`caching.py`)

**Two-Level Cache:**
```python
class ResponseCache:
    def __init__(self):
        self.memory_cache = InMemoryCache(max_size=1000, ttl=300)
        self.disk_cache = SQLiteCache(db_path, ttl=3600)
    
    def get(self, key: str):
        # Check memory first (fast)
        if value := self.memory_cache.get(key):
            return value
        # Then disk (persistent)
        if value := self.disk_cache.get(key):
            self.memory_cache.set(key, value)  # Promote to memory
            return value
        return None
```

**Cache Key Generation:**
```python
def generate_cache_key(query: str, org_id: str) -> str:
    normalized = query.lower().strip()
    return hashlib.sha256(f"{org_id}:{normalized}".encode()).hexdigest()
```

---

## Error Handling

### Standardized Error Responses

```python
# All API errors return JSON:
{
    "error": "Human-readable message",
    "code": "ERROR_CODE",  # Optional
    "details": {}          # Optional
}

# HTTP status codes:
# 400 - Bad request (validation errors)
# 401 - Authentication required
# 403 - Forbidden (not authorized)
# 404 - Not found
# 429 - Rate limited (future)
# 500 - Internal server error
```

### Error Logging

```python
import logging

logger = logging.getLogger(__name__)

try:
    # Operation
except Exception as e:
    logger.error(f"Operation failed: {e}", exc_info=True)
    return jsonify({'error': 'Operation failed'}), 500
```

---

## Performance Considerations

### Embedding Generation
- Batch processing: embed multiple chunks together
- Lazy loading: only load model when first needed
- Memory management: ~500MB for sentence-transformers

### Search Optimization
- HNSW index in ChromaDB for fast approximate search
- Keyword search via SQLite FTS5 (if enabled)
- Result caching for repeated queries

### Database
- SQLite for simplicity and portability
- WAL mode for concurrent reads
- Indexed columns: `organization_id`, `created_at`

---

## Deployment Architecture (Render)

```
┌─────────────────────────────────────────────┐
│              Render Service                  │
│  ┌─────────────────────────────────────┐    │
│  │         Gunicorn (WSGI)             │    │
│  │  ┌──────────────────────────────┐   │    │
│  │  │     Flask Application        │   │    │
│  │  └──────────────────────────────┘   │    │
│  └─────────────────────────────────────┘    │
│                    │                         │
│  ┌─────────────────┴─────────────────┐      │
│  │        Render Disk (/data)        │      │
│  │  ├── knowledge_expert.db          │      │
│  │  ├── chroma_db/                   │      │
│  │  └── uploads/                     │      │
│  └───────────────────────────────────┘      │
└─────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│          External Services                   │
│  ┌─────────────┐  ┌─────────────┐           │
│  │ Claude API  │  │ Google OAuth│           │
│  └─────────────┘  └─────────────┘           │
└─────────────────────────────────────────────┘
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Claude API access |
| `SECRET_KEY` | Yes | Flask session encryption |
| `DATA_DIR` | No | Storage path (default: /data) |
| `GOOGLE_CLIENT_ID` | No | Google OAuth |
| `GOOGLE_CLIENT_SECRET` | No | Google OAuth |
| `ADMIN_EMAILS` | No | Auto-admin users (comma-separated) |
| `OPENAI_API_KEY` | No | Fallback LLM |

---

## Security Measures

### Implemented
- [x] Multi-tenant data isolation
- [x] Authentication required for management routes
- [x] API key authentication for external access
- [x] HTTPS enforced (via Render)
- [x] Session-based CSRF protection (Flask default)
- [x] Input validation and sanitization
- [x] Content moderation for queries

### Future
- [ ] Rate limiting per user/organization
- [ ] API key rotation
- [ ] Audit logging
- [ ] IP allowlisting for API keys
- [ ] SSO/SAML integration

---

## Novel Design Patterns

### 1. Hybrid Search with Weighted Combination
Unlike pure semantic search, combines three strategies with configurable weights. Direct Q&A gets full weight (1.0) to prioritize curated answers.

### 2. Automatic Schema Migrations
Database evolves without migrations scripts. New columns are detected and added on startup, enabling seamless updates to production.

### 3. Dual-Mode Widget
Single script supports both floating and inline modes, determined by presence of `data-container` attribute. Handles late DOM loading gracefully.

### 4. Tenant-Isolated Vector Store
ChromaDB collections are namespaced by organization, providing complete data isolation without separate databases.

---

## Lessons Learned

1. **Default Org Fallback is Dangerous:** Anonymous users getting a shared default organization breaks tenant isolation. Always require explicit authentication.

2. **Widget CORS is Tricky:** Cross-origin requests from embedded widgets require proper CORS headers. `flask-cors` simplifies this significantly.

3. **Embeddings Without Search = Wasted Work:** Documents can be chunked and stored without embeddings if the embedder fails to load. Always verify the full pipeline.

4. **Search Weights Matter:** Initial 10% weight for Direct Q&A made curated answers appear low-confidence. Weights should reflect the reliability of each source.

5. **Schema Migrations on Live Databases:** Adding columns to existing tables requires explicit migration logic. The automatic migration system prevents "no such column" errors.
