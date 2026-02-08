# Company Knowledge Expert - Development Plan

## Executive Summary

This document outlines the complete development plan for transforming the Resume Matching System into a **Company Knowledge Expert** with continuous learning capabilities. The system will be fine-tuned on company-specific data and improve over time through customer feedback.

---

## Project Goals

| Goal | Success Metric |
|------|----------------|
| Answer company questions accurately | >85% user satisfaction rating |
| Learn from feedback | Model accuracy improves week-over-week |
| Fast response times | <3 seconds for 95% of queries |
| Reduce support burden | 40% reduction in repetitive support tickets |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    COMPANY KNOWLEDGE EXPERT                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                      KNOWLEDGE LAYER                              │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐            │  │
│  │  │Documents│  │  FAQs   │  │Workflows│  │Products │            │  │
│  │  │(PDF,MD) │  │ (Q&A)   │  │ (Steps) │  │ (Specs) │            │  │
│  │  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘            │  │
│  │       └───────────┬┴───────────┴─────────────┘                  │  │
│  │                   ▼                                              │  │
│  │  ┌────────────────────────────────────────────────────────────┐ │  │
│  │  │              INGESTION PIPELINE                             │ │  │
│  │  │  Extract → Classify → Chunk → Enrich → Embed → Index       │ │  │
│  │  └────────────────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                    │                                     │
│                                    ▼                                     │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                      RETRIEVAL LAYER                              │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐                       │  │
│  │  │ Semantic │  │ Keyword  │  │   FAQ    │ ──▶ Fusion ──▶ Rerank │  │
│  │  │ (Vector) │  │ (BM25)   │  │ Matcher  │                       │  │
│  │  └──────────┘  └──────────┘  └──────────┘                       │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                    │                                     │
│                                    ▼                                     │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                     GENERATION LAYER                              │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │  │
│  │  │ Fine-Tuned   │  │   Content    │  │  Response    │           │  │
│  │  │     LLM      │  │  Moderation  │  │  Formatting  │           │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘           │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                    │                                     │
│                                    ▼                                     │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                      FEEDBACK LAYER                               │  │
│  │                                                                    │  │
│  │   User Response ──▶ Feedback Capture ──▶ Training Queue          │  │
│  │        │                   │                    │                 │  │
│  │        │                   ▼                    ▼                 │  │
│  │        │           Analytics DB          Training Pipeline       │  │
│  │        │                   │                    │                 │  │
│  │        │                   ▼                    ▼                 │  │
│  │        └────────────▶ Model Retraining ◀────────┘                │  │
│  │                                                                    │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Phase Breakdown

### Phase 1: Foundation (Weeks 1-3)

**Objective**: Build core infrastructure and data pipeline

| Week | Tasks | Deliverables |
|------|-------|--------------|
| 1 | Database schema, project structure | PostgreSQL schema, project scaffold |
| 1 | Document parsers (PDF, MD, DOCX, HTML) | `parsers/` module |
| 2 | Chunking strategies by content type | `chunking/` module |
| 2 | Embedding pipeline (Sentence-Transformers) | `embeddings/` module |
| 3 | Vector store integration (ChromaDB → Pinecone) | `vectorstore/` module |
| 3 | BM25 keyword index | `search/bm25.py` |

**Exit Criteria**:
- Can ingest 1000 documents in under 10 minutes
- Vector search returns relevant results
- All tests passing

### Phase 2: Retrieval (Weeks 4-5)

**Objective**: Build hybrid retrieval with FAQ matching

| Week | Tasks | Deliverables |
|------|-------|--------------|
| 4 | FAQ matcher (question-to-question similarity) | `retrieval/faq_matcher.py` |
| 4 | Hybrid fusion (RRF algorithm) | `retrieval/fusion.py` |
| 5 | Cross-encoder reranking | `retrieval/reranker.py` |
| 5 | Query intent classification | `query/intent.py` |

**Exit Criteria**:
- FAQ queries return exact matches when available
- Hybrid retrieval outperforms single-method by 15%+
- Intent classification >90% accuracy on test set

### Phase 3: Generation (Weeks 6-7)

**Objective**: LLM integration with content moderation

| Week | Tasks | Deliverables |
|------|-------|--------------|
| 6 | LLM integration (Claude/GPT-4 API) | `generation/llm.py` |
| 6 | System prompt with content rules | `prompts/system.py` |
| 6 | Citation injection | `generation/citations.py` |
| 7 | Content moderation layer | `moderation/filter.py` |
| 7 | Response validation | `generation/validator.py` |

**Exit Criteria**:
- Responses include accurate citations
- Zero profanity/explicit content in 1000 test responses
- Average response time <2 seconds

### Phase 4: Feedback System (Weeks 8-9)

**Objective**: Capture and process user feedback

| Week | Tasks | Deliverables |
|------|-------|--------------|
| 8 | Feedback capture UI (thumbs, corrections) | `web/feedback.py` |
| 8 | Feedback database schema | `models/feedback.py` |
| 8 | Analytics pipeline | `analytics/` module |
| 9 | Training data generator | `training/data_generator.py` |
| 9 | Feedback quality scoring | `training/quality.py` |

**Exit Criteria**:
- Feedback captured for >80% of interactions
- Training data auto-generated from positive feedback
- Analytics dashboard shows key metrics

### Phase 5: Fine-Tuning Pipeline (Weeks 10-12)

**Objective**: Continuous model improvement

| Week | Tasks | Deliverables |
|------|-------|--------------|
| 10 | Embedding fine-tuning pipeline | `training/embedding_tuner.py` |
| 10 | Training data validation | `training/validator.py` |
| 11 | LLM fine-tuning integration (OpenAI/Anthropic) | `training/llm_tuner.py` |
| 11 | A/B testing framework | `evaluation/ab_test.py` |
| 12 | Automated retraining scheduler | `training/scheduler.py` |
| 12 | Model versioning and rollback | `models/versioning.py` |

**Exit Criteria**:
- Automated weekly embedding retraining
- Fine-tuned model outperforms base model by 10%+
- Rollback possible within 5 minutes

### Phase 6: Production (Weeks 13-14)

**Objective**: Production-ready deployment

| Week | Tasks | Deliverables |
|------|-------|--------------|
| 13 | API endpoints (REST) | `api/` module |
| 13 | Authentication and rate limiting | `api/auth.py` |
| 13 | Caching layer (Redis) | `cache/` module |
| 14 | Monitoring and alerting | Grafana dashboards |
| 14 | Documentation and runbooks | `docs/operations/` |

**Exit Criteria**:
- API handles 100 concurrent requests
- 99.5% uptime over 1 week
- Complete operations documentation

---

## Technology Decisions

### Selected Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **Language** | Python 3.11+ | ML ecosystem, team familiarity |
| **Database** | PostgreSQL 15 | JSONB for flexibility, proven reliability |
| **Vector Store** | ChromaDB (dev) → Pinecone (prod) | Local dev, scalable prod |
| **Embeddings** | Sentence-Transformers (fine-tunable) | Free, fine-tunable, good quality |
| **LLM** | Claude 3.5 Sonnet | Best quality/cost ratio |
| **Queue** | Redis + Celery | Training jobs, async processing |
| **Cache** | Redis | Response caching, rate limiting |
| **Search** | Elasticsearch | BM25 + metadata filtering |
| **Web** | FastAPI | Async, OpenAPI docs, type hints |

### Fine-Tuning Strategy

```
                    CONTINUOUS IMPROVEMENT LOOP

     ┌─────────────────────────────────────────────────────┐
     │                                                      │
     ▼                                                      │
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐  │
│ Customer│───▶│ Response│───▶│ Feedback│───▶│ Training│──┘
│  Query  │    │         │    │  👍/👎  │    │  Queue  │
└─────────┘    └─────────┘    └─────────┘    └─────────┘
                                                   │
                                                   ▼
                                            ┌─────────────┐
                                            │   Weekly    │
                                            │  Retraining │
                                            │             │
                                            │ • Embeddings│
                                            │ • LLM (if   │
                                            │   enough    │
                                            │   data)     │
                                            └──────┬──────┘
                                                   │
                                                   ▼
                                            ┌─────────────┐
                                            │   A/B Test  │
                                            │  New Model  │
                                            │             │
                                            │ If better:  │
                                            │  promote    │
                                            │ If worse:   │
                                            │  rollback   │
                                            └─────────────┘
```

**Embedding Fine-Tuning** (Weekly):
- Minimum 500 new positive feedback examples
- Train on (query, relevant_doc, irrelevant_doc) triplets
- Validation against held-out test set
- Auto-promote if metrics improve

**LLM Fine-Tuning** (Monthly):
- Minimum 1000 high-quality Q&A pairs
- Fine-tune on (context + question) → answer
- Human review of sample outputs before promotion
- Gradual traffic shift (10% → 50% → 100%)

---

## Content Moderation System

```
┌─────────────────────────────────────────────────────────────────┐
│                    CONTENT MODERATION PIPELINE                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  LLM Response                                                    │
│       │                                                          │
│       ▼                                                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 1. PROFANITY FILTER                                      │   │
│  │    - Blocked word list (customizable)                   │   │
│  │    - Regex patterns for variations                       │   │
│  │    - Action: Replace or reject                           │   │
│  └─────────────────────────────────────────────────────────┘   │
│       │                                                          │
│       ▼                                                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 2. TOPIC FILTER                                          │   │
│  │    - Block: politics, religion, competitors              │   │
│  │    - Block: personal opinions, speculation               │   │
│  │    - Action: Redirect to approved topics                 │   │
│  └─────────────────────────────────────────────────────────┘   │
│       │                                                          │
│       ▼                                                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 3. FACTUALITY CHECK                                      │   │
│  │    - Verify claims against source documents              │   │
│  │    - Flag unsupported statements                         │   │
│  │    - Action: Remove or add disclaimer                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│       │                                                          │
│       ▼                                                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 4. TONE CHECK                                            │   │
│  │    - Professional language                               │   │
│  │    - Helpful, not dismissive                            │   │
│  │    - Action: Rephrase if needed                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│       │                                                          │
│       ▼                                                          │
│  Approved Response                                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## File Structure

```
company_knowledge_expert/
├── src/
│   ├── __init__.py
│   ├── config.py                    # Configuration management
│   │
│   ├── ingestion/                   # Document ingestion
│   │   ├── __init__.py
│   │   ├── parsers/                 # File type parsers
│   │   │   ├── pdf.py
│   │   │   ├── markdown.py
│   │   │   ├── docx.py
│   │   │   └── html.py
│   │   ├── chunking.py              # Text chunking strategies
│   │   ├── enrichment.py            # Entity extraction, summaries
│   │   └── pipeline.py              # Orchestration
│   │
│   ├── embeddings/                  # Embedding generation
│   │   ├── __init__.py
│   │   ├── base.py                  # Base embedder class
│   │   ├── sentence_transformer.py  # ST implementation
│   │   └── fine_tuner.py            # Fine-tuning logic
│   │
│   ├── vectorstore/                 # Vector storage
│   │   ├── __init__.py
│   │   ├── base.py                  # Abstract interface
│   │   ├── chromadb.py              # ChromaDB implementation
│   │   └── pinecone.py              # Pinecone implementation
│   │
│   ├── search/                      # Search implementations
│   │   ├── __init__.py
│   │   ├── bm25.py                  # Keyword search
│   │   └── elasticsearch.py         # ES integration
│   │
│   ├── retrieval/                   # Retrieval logic
│   │   ├── __init__.py
│   │   ├── faq_matcher.py           # FAQ-specific matching
│   │   ├── fusion.py                # RRF fusion
│   │   ├── reranker.py              # Cross-encoder reranking
│   │   └── pipeline.py              # Full retrieval pipeline
│   │
│   ├── query/                       # Query processing
│   │   ├── __init__.py
│   │   ├── intent.py                # Intent classification
│   │   ├── entities.py              # Entity extraction
│   │   └── expansion.py             # Query expansion
│   │
│   ├── generation/                  # Response generation
│   │   ├── __init__.py
│   │   ├── llm.py                   # LLM client wrapper
│   │   ├── prompts.py               # Prompt templates
│   │   ├── citations.py             # Citation injection
│   │   └── validator.py             # Response validation
│   │
│   ├── moderation/                  # Content moderation
│   │   ├── __init__.py
│   │   ├── profanity.py             # Word filtering
│   │   ├── topics.py                # Topic filtering
│   │   ├── factuality.py            # Fact checking
│   │   └── pipeline.py              # Moderation pipeline
│   │
│   ├── feedback/                    # Feedback system
│   │   ├── __init__.py
│   │   ├── capture.py               # Feedback capture
│   │   ├── storage.py               # Feedback storage
│   │   └── analytics.py             # Feedback analytics
│   │
│   ├── training/                    # Model training
│   │   ├── __init__.py
│   │   ├── data_generator.py        # Training data from feedback
│   │   ├── embedding_tuner.py       # Embedding fine-tuning
│   │   ├── llm_tuner.py             # LLM fine-tuning
│   │   ├── scheduler.py             # Training scheduler
│   │   └── versioning.py            # Model versioning
│   │
│   ├── evaluation/                  # Evaluation
│   │   ├── __init__.py
│   │   ├── metrics.py               # Evaluation metrics
│   │   ├── ab_test.py               # A/B testing
│   │   └── benchmark.py             # Benchmark suite
│   │
│   ├── api/                         # API layer
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI app
│   │   ├── routes/                  # Route handlers
│   │   │   ├── query.py             # Query endpoints
│   │   │   ├── feedback.py          # Feedback endpoints
│   │   │   ├── admin.py             # Admin endpoints
│   │   │   └── health.py            # Health checks
│   │   ├── auth.py                  # Authentication
│   │   └── middleware.py            # Middleware
│   │
│   ├── models/                      # Data models
│   │   ├── __init__.py
│   │   ├── knowledge.py             # Knowledge item models
│   │   ├── feedback.py              # Feedback models
│   │   ├── training.py              # Training data models
│   │   └── user.py                  # User models
│   │
│   └── db/                          # Database
│       ├── __init__.py
│       ├── connection.py            # DB connection
│       ├── migrations/              # Alembic migrations
│       └── repositories/            # Data access layer
│
├── tests/                           # Test suite
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── scripts/                         # Utility scripts
│   ├── ingest_documents.py
│   ├── train_embeddings.py
│   ├── evaluate_model.py
│   └── export_training_data.py
│
├── data/                            # Data directories
│   ├── knowledge_base/              # Source documents
│   ├── training/                    # Training datasets
│   └── models/                      # Model checkpoints
│
├── docs/                            # Documentation
│   ├── development/                 # Dev docs (this folder)
│   ├── api/                         # API documentation
│   └── operations/                  # Runbooks
│
├── docker/                          # Docker configs
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## Success Metrics

### Weekly Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| User satisfaction (thumbs up %) | >85% | Feedback system |
| Query success rate | >90% | Answer provided / total queries |
| Response time (p95) | <3s | API monitoring |
| Citation accuracy | >95% | Manual sample review |

### Monthly Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Model improvement | +2% accuracy | A/B test vs previous |
| Knowledge coverage | 95% questions answered | Unanswered query rate |
| Training data growth | +500 examples | Training data count |
| User engagement | 20% return users | Analytics |

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM hallucination | High | Strict prompt engineering, factuality check |
| Inappropriate content | High | Multi-layer moderation, human review |
| Model degradation | Medium | A/B testing, automatic rollback |
| Data quality | Medium | Feedback quality scoring, human validation |
| API costs | Medium | Caching, rate limiting, model optimization |

---

## Next Steps

1. Review and approve this development plan
2. Set up project infrastructure (repo, CI/CD, environments)
3. Begin Phase 1 implementation
4. Weekly progress reviews

---

## Related Documents

- `02_DATABASE_SCHEMA.md` - Complete database schema
- `03_INGESTION_PIPELINE.md` - Document ingestion details
- `04_FEEDBACK_TRAINING.md` - Feedback and training loops
- `05_API_SPECIFICATION.md` - API endpoint specifications
- `06_IMPLEMENTATION_CHECKLIST.md` - Task-by-task checklist
