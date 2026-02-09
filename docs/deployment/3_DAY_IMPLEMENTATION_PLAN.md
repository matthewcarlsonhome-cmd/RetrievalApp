# 3-Day MVP Implementation Plan

## Target: Company Knowledge Expert for matthewcarlsonconsulting.com

### Client Business Context
- **Company**: Matthew Carlson Consulting (Madison, WI)
- **Services**: AI Automation, Digital Marketing, Document Retrieval, Semantic Search
- **Specialties**: Google Shopping feeds, Meta ads, PMax campaigns, Marketing Analytics
- **Rate**: $200/hour consulting
- **Differentiator**: Rapid deployment - "idea to production in days"

---

## Day 1: Core Backend (Today)

### Morning: Project Structure & Database
- [x] Review existing codebase
- [ ] Create new knowledge expert module structure
- [ ] Set up SQLite database (simple, no external DB needed for Render)
- [ ] Create core data models

### Afternoon: Ingestion & Retrieval
- [ ] Document upload endpoint (PDF, DOCX, MD, TXT)
- [ ] Text extraction and chunking
- [ ] Embedding generation (sentence-transformers)
- [ ] Vector storage (ChromaDB - embedded, no external service)
- [ ] Hybrid retrieval (semantic + keyword)

### Evening: LLM Generation
- [ ] Claude/OpenAI API integration
- [ ] System prompt with content rules
- [ ] Response generation with citations
- [ ] Content moderation (exclusion list)

---

## Day 2: Frontend & Features

### Morning: Chat Interface
- [ ] New Flask templates for Knowledge Expert
- [ ] Chat UI with message history
- [ ] Real-time typing indicator
- [ ] Source citations display

### Afternoon: Document Management
- [ ] Document upload UI (drag & drop)
- [ ] Upload progress tracking
- [ ] Document list view
- [ ] Direct Q&A entry form

### Evening: Feedback & Admin
- [ ] Thumbs up/down feedback
- [ ] Admin dashboard (document stats)
- [ ] Content exclusion list management

---

## Day 3: Deployment & Documentation

### Morning: Testing & Polish
- [ ] End-to-end testing
- [ ] Error handling
- [ ] Loading states
- [ ] Mobile responsiveness

### Afternoon: Render Deployment
- [ ] Update render.yaml
- [ ] Environment variables setup
- [ ] Production configuration
- [ ] Health checks

### Evening: Documentation & Training
- [ ] Deployment guide
- [ ] User training guide
- [ ] Mock data for matthewcarlsonconsulting.com
- [ ] Content moderation configuration

---

## Technical Stack (Render-Compatible)

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **Web Framework** | Flask | Already in place, simple |
| **Database** | SQLite | No external DB needed, free tier compatible |
| **Vector Store** | ChromaDB (embedded) | No external service, persists to disk |
| **Embeddings** | sentence-transformers | Local, no API costs |
| **LLM** | Claude API | Best quality, user has API key |
| **File Storage** | Local filesystem | Simple, Render persistent disk |

### Render Plan Requirements
- **Starter Plan ($7/mo)**: 512MB RAM, 1GB disk
  - Sufficient for ChromaDB + small document set
  - sentence-transformers may be tight on memory
- **Standard Plan ($25/mo)**: 2GB RAM, 10GB disk
  - Recommended for production
  - Comfortable for neural embeddings

---

## MVP Feature Set

### Included (Must Have)
1. ✅ Document upload (PDF, DOCX, MD, TXT)
2. ✅ Chat Q&A interface
3. ✅ Semantic search with citations
4. ✅ Direct Q&A entry
5. ✅ Feedback capture (thumbs up/down)
6. ✅ Content exclusion list
7. ✅ Basic admin view

### Deferred (Post-MVP)
- Multi-turn conversation memory
- Human handoff/escalation
- Slack/Teams integration
- Fine-tuning pipeline
- Advanced analytics
- Multi-language support

---

## Mock Data for matthewcarlsonconsulting.com

### Documents to Create
1. **Services Overview** - AI automation, digital marketing
2. **Pricing Guide** - Consulting rates, project pricing
3. **Case Studies** - Example client successes
4. **Process Guide** - How engagements work
5. **FAQ Document** - Common questions

### Q&A Pairs to Create (20+)
- What services do you offer?
- What are your consulting rates?
- How quickly can you deliver a project?
- Do you work with marketing agencies?
- What AI tools do you specialize in?
- How does the engagement process work?
- What industries do you serve?
- Can you help with Google Shopping feeds?
- Do you offer Meta/Facebook advertising?
- What is PMax and can you help with it?
- Where are you located?
- Do you work remotely?
- What makes you different from other consultants?
- Can you help build a RAG/document search system?
- What is semantic search?
- How long have you been in business?
- Do you offer training?
- Can you integrate AI into my existing systems?
- What's your typical project timeline?
- How do I get started?

---

## File Structure (New)

```
RetrievalApp/
├── knowledge_expert/              # NEW - Main application
│   ├── __init__.py
│   ├── app.py                     # Flask app
│   ├── config.py                  # Configuration
│   ├── models.py                  # SQLite models
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── parsers.py            # PDF, DOCX, MD parsers
│   │   ├── chunker.py            # Text chunking
│   │   └── embedder.py           # Embedding generation
│   ├── retrieval/
│   │   ├── __init__.py
│   │   ├── vector_store.py       # ChromaDB wrapper
│   │   └── search.py             # Hybrid search
│   ├── generation/
│   │   ├── __init__.py
│   │   ├── llm.py                # Claude/OpenAI client
│   │   ├── prompts.py            # System prompts
│   │   └── moderation.py         # Content filtering
│   ├── templates/
│   │   ├── base.html
│   │   ├── chat.html             # Main chat interface
│   │   ├── upload.html           # Document upload
│   │   └── admin.html            # Admin dashboard
│   └── static/
│       ├── css/
│       └── js/
├── data/
│   ├── knowledge_base/           # Uploaded documents
│   ├── chroma_db/                # Vector store
│   └── mock/                     # Mock data for demo
├── docs/
│   └── deployment/               # Deployment guides
└── render.yaml                   # Updated for Knowledge Expert
```

---

## Environment Variables (Render)

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...     # For Claude LLM
# OR
OPENAI_API_KEY=sk-...            # For GPT-4

# Optional
SECRET_KEY=random-secret-key     # Flask sessions
FLASK_ENV=production
MAX_UPLOAD_SIZE_MB=10
```

---

## Exclusion List (Default)

Content that will be blocked/filtered:

### Blocked Words
- Profanity list (standard)
- Competitor names (configurable)
- Inappropriate content

### Blocked Topics
- Political content
- Religious content
- Adult/explicit content
- Medical advice (unless in knowledge base)
- Legal advice (unless in knowledge base)
- Financial advice (unless in knowledge base)

### Response Rules
- Always cite sources
- Admit when information is not in knowledge base
- Maintain professional tone
- Never make up information

---

## Success Criteria

By end of Day 3:
1. ✅ Can upload PDF/DOCX/MD documents
2. ✅ Can ask questions and get accurate answers
3. ✅ Answers include source citations
4. ✅ Can add Q&A pairs directly
5. ✅ Content exclusion list blocks inappropriate responses
6. ✅ Deployed and running on Render
7. ✅ Documentation complete
