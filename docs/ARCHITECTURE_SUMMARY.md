# Knowledge Expert: Enterprise RAG System Architecture

## Executive Summary

**Knowledge Expert** is a production-ready Retrieval-Augmented Generation (RAG) platform that transforms how organizations manage and retrieve knowledge. Unlike simple LLM wrappers, it implements a complete document intelligence pipeline with multi-tenant isolation, adaptive learning, and enterprise integrations.

**31,500+ lines of production code** | **Multi-tenant SaaS-ready** | **20+ file formats** | **Self-improving architecture**

---

## What Makes This Different From a "Claude Wrapper"

### 1. True Knowledge Management
A Claude wrapper sends your question directly to an LLM. Knowledge Expert:
- **Indexes and chunks your documents** into semantic units optimized for retrieval
- **Creates vector embeddings** that capture meaning, not just keywords
- **Performs hybrid search** combining semantic similarity, keyword matching, and direct Q&A
- **Cites sources** with exact document locations and page numbers

### 2. Learning Over Time
The system improves through user feedback:
- **Positive feedback** is collected and exported for model fine-tuning
- **Knowledge gaps** are automatically detected when queries can't be answered
- **A/B testing framework** measures which chunking strategies perform best
- **Local model training** via LoRA allows deploying organization-specific models

### 3. Multi-Tenant Architecture
Enterprise-grade data isolation:
- Each organization has **separate ChromaDB collections**
- Documents, queries, and analytics are **tenant-isolated**
- API keys provide **programmatic access** per user/organization
- Role-based access control (admin, editor, member, viewer)

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           USER INTERFACES                                │
├──────────────┬──────────────┬──────────────┬──────────────┬─────────────┤
│   Web Chat   │  Admin Panel │  Analytics   │ Embed Widget │  Slack Bot  │
└──────┬───────┴──────┬───────┴──────┬───────┴──────┬───────┴──────┬──────┘
       │              │              │              │              │
       └──────────────┴──────────────┼──────────────┴──────────────┘
                                     │
┌────────────────────────────────────┴────────────────────────────────────┐
│                            FLASK API LAYER                              │
│  • Authentication (Email/Password + Google OAuth)                       │
│  • Rate Limiting & API Keys                                             │
│  • Request Validation & Content Moderation                              │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
       ┌─────────────────────────────┼─────────────────────────────┐
       │                             │                             │
┌──────┴──────┐             ┌────────┴────────┐           ┌───────┴───────┐
│  INGESTION  │             │    RETRIEVAL    │           │   GENERATION  │
│   PIPELINE  │             │     ENGINE      │           │    ENGINE     │
├─────────────┤             ├─────────────────┤           ├───────────────┤
│ • Parsers   │             │ • Hybrid Search │           │ • LLM Client  │
│   (20+ fmt) │             │ • Vector Store  │           │ • Prompts     │
│ • Chunkers  │             │ • Embeddings    │           │ • Moderation  │
│ • Embedder  │             │ • Direct Q&A    │           │ • Response    │
│             │             │ • Tenant Filter │           │   Caching     │
└──────┬──────┘             └────────┬────────┘           └───────┬───────┘
       │                             │                             │
       └─────────────────────────────┼─────────────────────────────┘
                                     │
┌────────────────────────────────────┴────────────────────────────────────┐
│                           DATA LAYER                                    │
├──────────────────────┬────────────────────┬─────────────────────────────┤
│      SQLite DB       │    ChromaDB        │     File Storage            │
│  (Metadata, Users,   │  (Vector Index)    │  (Uploaded Documents)       │
│   Queries, Feedback) │  (Per-Tenant)      │  (Per-Organization)         │
└──────────────────────┴────────────────────┴─────────────────────────────┘
```

---

## Database Schema Design

### Core Tables

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `organizations` | Multi-tenant isolation | id, name, slug, settings |
| `users` | Authentication & access | email, password_hash, api_key, role, organization_id |
| `knowledge_items` | Document metadata | title, source_file, file_type, chunk_count, organization_id |
| `chunks` | Searchable text segments | content, document_id, section_title, page_number |
| `queries` | User interactions | question, answer, feedback, latency_ms |
| `direct_qa` | Curated Q&A pairs | question, answer, category, use_count |
| `knowledge_gaps` | Unanswered questions | query_text, occurrence_count, resolved |
| `experiments` | A/B testing configs | chunking_strategy, semantic_weight, is_active |
| `conversations` | Chat memory | user_id, session_id, message_count |

### Schema Migrations
The system includes automatic migrations for existing databases, adding new columns without data loss using `ALTER TABLE` statements checked against `PRAGMA table_info()`.

---

## Core Intelligence: Chunking, Embedding & Retrieval

### Chunking Strategies

| Strategy | Use Case | Description |
|----------|----------|-------------|
| **Sentence** | General documents | Splits on sentence boundaries, respects natural breaks |
| **Paragraph** | FAQs, policies | Preserves paragraph structure as logical units |
| **Fixed** | Dense technical docs | Consistent token-count chunks |
| **Sliding Window** | Conversations | Overlapping windows for context continuity |
| **Semantic** | Complex documents | Groups semantically related content |
| **Hybrid** | Mixed content | Adapts strategy based on content type |

**Configurable presets**: `default`, `faq`, `technical`, `legal`, `conversation`, `dense`

### Embedding & Vector Search

- **Model**: `all-MiniLM-L6-v2` (384 dimensions, fast, accurate)
- **Storage**: ChromaDB with per-tenant collections (`tenant_{org_id}`)
- **Similarity**: Cosine similarity with configurable minimum threshold

### Hybrid Search Algorithm

```
Final Score = (semantic_weight × semantic_score)
            + (keyword_weight × keyword_score)
            + (qa_weight × direct_qa_score)
```

Default weights: **70% semantic**, **20% keyword**, **10% direct Q&A**

This combination ensures:
- Semantic search captures meaning and synonyms
- Keyword search catches exact terms (product names, codes)
- Direct Q&A provides instant answers for known questions

---

## Supported File Types (20+)

| Category | Extensions | Parser Technology |
|----------|-----------|-------------------|
| **Documents** | PDF, DOCX, DOC, MD, TXT, HTML | PyMuPDF, python-docx, BeautifulSoup |
| **Spreadsheets** | XLSX, XLS, CSV | openpyxl, pandas |
| **Presentations** | PPTX, PPT | python-pptx |
| **Email** | EML, MBOX | Python email library |
| **Exports** | JSON | Confluence/Notion export support |
| **Audio** | MP3, WAV, M4A, OGG, FLAC, WEBM | OpenAI Whisper transcription |

---

## Model Training & Continuous Improvement

### The Feedback Loop

```
User Query → RAG Response → User Feedback (👍/👎)
                                    ↓
                            Stored in Database
                                    ↓
                         Export Positive Examples
                                    ↓
                          Fine-tune Local Model
                                    ↓
                     Deploy Improved Model (Ollama)
```

### Fine-Tuning Pipeline (`scripts/finetune.py`)

1. **Export Training Data**: Positive feedback examples from production
2. **Prepare Format**: Convert to chat template (user/assistant turns)
3. **LoRA Training**: Low-Rank Adaptation for efficient fine-tuning
   - Trains only ~0.1% of model parameters
   - Works on consumer GPUs (8GB+ VRAM)
   - QLoRA option for 4-bit quantization
4. **Merge & Export**: Create GGUF for Ollama deployment
5. **Cloud Option**: Together.ai API for serverless training

### What Actually Happens During Training

```
For each positive example:
1. Forward Pass: Model predicts next token
2. Loss Calculation: Compare prediction to actual good answer
3. Backpropagation: Calculate gradients for LoRA adapter weights
4. Weight Update: Adjust adapter (not base model) to minimize loss

Result: Model learns patterns from YOUR successful interactions
```

---

## Key Features for Businesses

### For Individual Users
- Upload documents and ask questions in natural language
- Get cited answers with source references
- Auto-generate Q&A from documents
- Export knowledge base for offline use

### For Teams & Organizations
- **Data Isolation**: Each organization's documents are completely separate
- **User Management**: Invite team members with role-based permissions
- **Analytics Dashboard**: Query volumes, satisfaction rates, knowledge gaps
- **Embeddable Widget**: Add chat to your website with one line of code
- **API Access**: Integrate with existing tools via REST API
- **Slack Integration**: Answer questions directly in Slack channels

### For Enterprises
- **A/B Testing**: Experiment with retrieval configurations
- **White-labeling**: Customize branding and appearance
- **Audit Trail**: Full query and response logging
- **Training Pipeline**: Continuously improve with production feedback

---

## Development Journey & Challenges Overcome

### Challenge 1: SQLite Migration on Render
**Problem**: Existing production database lacked new columns after schema updates.
**Solution**: Implemented runtime migration system that checks existing columns via `PRAGMA table_info()` and applies `ALTER TABLE` only for missing columns.

### Challenge 2: Multi-Tenant Vector Isolation
**Problem**: ChromaDB doesn't natively support tenant isolation.
**Solution**: Created `TenantVectorStore` class that:
- Creates separate collections per organization
- Sanitizes organization IDs for collection names
- Adds `organization_id` metadata filter as backup safety

### Challenge 3: Large File Parsing
**Problem**: Memory issues with large PDFs and audio files.
**Solution**:
- Streaming PDF parser with page-by-page processing
- Audio chunking before Whisper transcription
- Configurable upload size limits

### Challenge 4: Response Latency
**Problem**: Cold start latency with ML models.
**Solution**:
- `SKIP_ML_MODELS` environment variable for lightweight mode
- Response caching layer (in-memory + SQLite backends)
- Lazy loading of embedding models

### Challenge 5: Citation Accuracy
**Problem**: Users needed to verify AI responses against source documents.
**Solution**:
- Track `start_char` and `end_char` for each chunk
- Store `page_number` for PDFs
- Return clickable citations in responses

---

## Recommendations for Stable Client Release

### Must-Have for v1.0
- [x] Core RAG functionality (chunking, embedding, retrieval)
- [x] Multi-tenant data isolation
- [x] User authentication (email + Google OAuth)
- [x] Document upload and parsing
- [x] Response caching
- [x] Embeddable website widget
- [x] API key management
- [x] Basic analytics

### Recommended Additions
- [ ] **Rate Limiting**: Protect API from abuse (add Flask-Limiter)
- [ ] **Email Notifications**: Password reset, weekly usage reports
- [ ] **Backup/Export**: Allow users to download their data
- [ ] **Usage Quotas**: Set limits per organization tier
- [ ] **Health Check Endpoint**: For load balancer monitoring
- [ ] **Structured Logging**: JSON logs for production debugging

### Nice-to-Have for v1.1
- [ ] Microsoft Teams integration
- [ ] Document versioning
- [ ] Scheduled re-indexing
- [ ] Custom embedding models
- [ ] Webhook notifications
- [ ] Multi-language support

---

## Quick Start for Clients

### Environment Variables Required
```bash
# LLM Provider (choose one)
ANTHROPIC_API_KEY=your-key
# or
OPENAI_API_KEY=your-key

# Security
SECRET_KEY=generate-a-secure-random-string

# Optional: Google OAuth
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-secret

# Optional: Admin users
ADMIN_EMAILS=admin@company.com
```

### Deployment on Render
1. Connect GitHub repository
2. Set environment variables
3. Add persistent disk at `/data`
4. Deploy - that's it!

---

## Codebase Statistics

| Metric | Value |
|--------|-------|
| Total Lines of Code | 31,500+ |
| Python Backend | 26,000+ |
| HTML Templates | 3,500+ |
| JavaScript | 1,500+ |
| Core Application (`knowledge_expert/`) | 8,000+ |
| Test & Scripts | 5,000+ |

### Key Files
- `knowledge_expert/app.py` (1,652 lines) - Flask application & API routes
- `knowledge_expert/models.py` (1,204 lines) - Database models & migrations
- `knowledge_expert/experiments.py` (995 lines) - A/B testing framework
- `knowledge_expert/ingestion/parsers.py` (849 lines) - Document parsing
- `knowledge_expert/ingestion/chunker.py` (755 lines) - Text chunking strategies
- `scripts/finetune.py` (673 lines) - Model fine-tuning pipeline

---

## Contact

**Matthew Carlson Consulting**
Building intelligent systems that learn and improve.

[matthewcarlsonconsulting.com](https://matthewcarlsonconsulting.com)

---

*This document was generated from the Knowledge Expert codebase. Last updated: February 2026.*
