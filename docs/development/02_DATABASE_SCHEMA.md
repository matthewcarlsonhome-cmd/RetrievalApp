# Database Schema Specification

## Overview

This document defines the complete PostgreSQL database schema for the Company Knowledge Expert system. The schema supports knowledge storage, user management, feedback collection, and training data generation.

---

## Entity Relationship Diagram

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│   knowledge_    │       │    chunks       │       │   embeddings    │
│     items       │───────│                 │───────│                 │
│                 │  1:N  │                 │  1:1  │                 │
└────────┬────────┘       └────────┬────────┘       └─────────────────┘
         │                         │
         │ 1:N                     │ 1:N
         ▼                         ▼
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│    entities     │       │    queries      │       │     users       │
│                 │       │                 │───────│                 │
└─────────────────┘       │                 │  N:1  │                 │
                          └────────┬────────┘       └────────┬────────┘
                                   │                         │
                                   │ 1:1                     │ 1:N
                                   ▼                         │
                          ┌─────────────────┐                │
                          │   responses     │                │
                          │                 │◀───────────────┘
                          └────────┬────────┘
                                   │
                                   │ 1:N
                                   ▼
                          ┌─────────────────┐       ┌─────────────────┐
                          │    feedback     │───────│ training_data   │
                          │                 │  1:1  │                 │
                          └─────────────────┘       └─────────────────┘


                          ┌─────────────────┐       ┌─────────────────┐
                          │ model_versions  │───────│ training_jobs   │
                          │                 │  1:N  │                 │
                          └─────────────────┘       └─────────────────┘
```

---

## Core Tables

### 1. knowledge_items

Stores all knowledge documents, FAQs, workflows, and products.

```sql
CREATE TABLE knowledge_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Classification
    type VARCHAR(50) NOT NULL,           -- 'document', 'faq', 'workflow', 'product'
    category VARCHAR(100) NOT NULL,      -- 'product', 'policy', 'technical', 'support'
    subcategory VARCHAR(100),            -- More specific classification

    -- Content
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,               -- Full content (may be long)
    summary TEXT,                        -- AI-generated summary

    -- FAQ-specific fields
    question TEXT,                       -- For FAQ type
    answer TEXT,                         -- For FAQ type

    -- Workflow-specific fields
    steps JSONB,                         -- Array of step objects

    -- Source tracking
    source_file VARCHAR(500),            -- Original file path
    source_url VARCHAR(1000),            -- Original URL if web-sourced

    -- Metadata
    author VARCHAR(200),
    version VARCHAR(50),
    audience TEXT[],                     -- ['customer', 'employee', 'partner']
    tags TEXT[],

    -- Quality metrics
    confidence_score DECIMAL(3,2),       -- 0.00 - 1.00
    usage_count INTEGER DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    content_date DATE,                   -- When the content was written

    -- Soft delete
    is_active BOOLEAN DEFAULT TRUE,
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- Indexes
CREATE INDEX idx_knowledge_items_type ON knowledge_items(type);
CREATE INDEX idx_knowledge_items_category ON knowledge_items(category);
CREATE INDEX idx_knowledge_items_audience ON knowledge_items USING GIN(audience);
CREATE INDEX idx_knowledge_items_tags ON knowledge_items USING GIN(tags);
CREATE INDEX idx_knowledge_items_active ON knowledge_items(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_knowledge_items_question ON knowledge_items(question) WHERE type = 'faq';

-- Full-text search index
CREATE INDEX idx_knowledge_items_fts ON knowledge_items
    USING GIN(to_tsvector('english', title || ' ' || content));
```

### 2. chunks

Stores chunked content for retrieval.

```sql
CREATE TABLE chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    knowledge_item_id UUID NOT NULL REFERENCES knowledge_items(id) ON DELETE CASCADE,

    -- Chunk content
    content TEXT NOT NULL,

    -- Position tracking
    chunk_index INTEGER NOT NULL,        -- Order within document
    start_char INTEGER,                  -- Character position in original
    end_char INTEGER,

    -- Context
    section_title VARCHAR(500),          -- Section this chunk belongs to
    previous_chunk_id UUID REFERENCES chunks(id),
    next_chunk_id UUID REFERENCES chunks(id),

    -- Metadata
    token_count INTEGER,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(knowledge_item_id, chunk_index)
);

-- Indexes
CREATE INDEX idx_chunks_knowledge_item ON chunks(knowledge_item_id);
CREATE INDEX idx_chunks_section ON chunks(section_title);
```

### 3. embeddings

Stores vector embeddings for semantic search.

```sql
CREATE TABLE embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chunk_id UUID NOT NULL REFERENCES chunks(id) ON DELETE CASCADE,

    -- Embedding data
    model_name VARCHAR(100) NOT NULL,    -- 'all-MiniLM-L6-v2', 'fine-tuned-v1'
    model_version VARCHAR(50) NOT NULL,
    embedding VECTOR(384) NOT NULL,      -- Dimension depends on model

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(chunk_id, model_name, model_version)
);

-- Vector similarity index (pgvector extension required)
CREATE INDEX idx_embeddings_vector ON embeddings
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_embeddings_model ON embeddings(model_name, model_version);
```

### 4. entities

Stores extracted entities from knowledge items.

```sql
CREATE TABLE entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    knowledge_item_id UUID NOT NULL REFERENCES knowledge_items(id) ON DELETE CASCADE,

    -- Entity data
    entity_type VARCHAR(50) NOT NULL,    -- 'product', 'feature', 'person', 'term'
    entity_value VARCHAR(500) NOT NULL,
    normalized_value VARCHAR(500),       -- Canonical form

    -- Context
    context TEXT,                        -- Surrounding text

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_entities_knowledge_item ON entities(knowledge_item_id);
CREATE INDEX idx_entities_type_value ON entities(entity_type, normalized_value);
```

---

## User & Session Tables

### 5. users

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Identity
    external_id VARCHAR(200),            -- SSO/OAuth ID
    email VARCHAR(200),
    name VARCHAR(200),

    -- Classification
    user_type VARCHAR(50) NOT NULL,      -- 'customer', 'employee', 'partner', 'anonymous'
    organization VARCHAR(200),

    -- Permissions
    roles TEXT[],                        -- ['admin', 'viewer', 'contributor']

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_active_at TIMESTAMP WITH TIME ZONE
);

-- Indexes
CREATE INDEX idx_users_external_id ON users(external_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_type ON users(user_type);
```

### 6. sessions

```sql
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),

    -- Session data
    session_token VARCHAR(500) UNIQUE,
    ip_address INET,
    user_agent TEXT,

    -- Timestamps
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ended_at TIMESTAMP WITH TIME ZONE,
    last_activity_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_sessions_user ON sessions(user_id);
CREATE INDEX idx_sessions_token ON sessions(session_token);
```

---

## Query & Response Tables

### 7. queries

Stores all user queries for analytics and training.

```sql
CREATE TABLE queries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(id),
    user_id UUID REFERENCES users(id),

    -- Query data
    query_text TEXT NOT NULL,
    query_embedding VECTOR(384),         -- For deduplication/clustering

    -- Classification
    detected_intent VARCHAR(50),         -- 'how_to', 'what_is', 'troubleshoot', etc.
    detected_entities JSONB,             -- Extracted entities

    -- Processing metadata
    processing_time_ms INTEGER,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_queries_user ON queries(user_id);
CREATE INDEX idx_queries_session ON queries(session_id);
CREATE INDEX idx_queries_intent ON queries(detected_intent);
CREATE INDEX idx_queries_created ON queries(created_at);
```

### 8. responses

Stores generated responses.

```sql
CREATE TABLE responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_id UUID NOT NULL REFERENCES queries(id) ON DELETE CASCADE,

    -- Response content
    response_text TEXT NOT NULL,

    -- Generation metadata
    model_name VARCHAR(100) NOT NULL,    -- 'claude-3.5-sonnet', 'fine-tuned-v1'
    model_version VARCHAR(50),
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    generation_time_ms INTEGER,

    -- Retrieved context
    retrieved_chunk_ids UUID[],          -- Chunks used for context
    retrieval_scores DECIMAL[],          -- Corresponding scores

    -- Quality indicators
    confidence_score DECIMAL(3,2),       -- Model's confidence
    citations JSONB,                     -- Citation metadata

    -- Moderation
    moderation_passed BOOLEAN DEFAULT TRUE,
    moderation_flags TEXT[],

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_responses_query ON responses(query_id);
CREATE INDEX idx_responses_model ON responses(model_name);
CREATE INDEX idx_responses_created ON responses(created_at);
```

---

## Feedback Tables

### 9. feedback

Captures user feedback on responses.

```sql
CREATE TABLE feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    response_id UUID NOT NULL REFERENCES responses(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id),

    -- Feedback type
    feedback_type VARCHAR(50) NOT NULL,  -- 'thumbs_up', 'thumbs_down', 'correction', 'report'

    -- Feedback data
    rating INTEGER,                      -- 1-5 scale
    comment TEXT,                        -- User comment
    correction TEXT,                     -- User-provided correct answer

    -- Issue classification (for negative feedback)
    issue_type VARCHAR(50),              -- 'wrong_answer', 'outdated', 'incomplete', 'inappropriate'

    -- Processing status
    reviewed BOOLEAN DEFAULT FALSE,
    reviewed_by UUID REFERENCES users(id),
    reviewed_at TIMESTAMP WITH TIME ZONE,

    -- Training data generation
    training_data_generated BOOLEAN DEFAULT FALSE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_feedback_response ON feedback(response_id);
CREATE INDEX idx_feedback_user ON feedback(user_id);
CREATE INDEX idx_feedback_type ON feedback(feedback_type);
CREATE INDEX idx_feedback_unreviewed ON feedback(reviewed) WHERE reviewed = FALSE;
CREATE INDEX idx_feedback_not_trained ON feedback(training_data_generated)
    WHERE training_data_generated = FALSE;
```

### 10. feedback_analytics

Aggregated feedback metrics.

```sql
CREATE TABLE feedback_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Time bucket
    date DATE NOT NULL,
    hour INTEGER,                        -- 0-23, NULL for daily aggregates

    -- Metrics
    total_queries INTEGER DEFAULT 0,
    total_responses INTEGER DEFAULT 0,
    total_feedback INTEGER DEFAULT 0,
    thumbs_up_count INTEGER DEFAULT 0,
    thumbs_down_count INTEGER DEFAULT 0,
    correction_count INTEGER DEFAULT 0,

    -- Calculated
    satisfaction_rate DECIMAL(5,4),      -- thumbs_up / total_feedback
    feedback_rate DECIMAL(5,4),          -- total_feedback / total_responses

    -- Breakdowns
    feedback_by_intent JSONB,            -- {intent: {up: X, down: Y}}
    feedback_by_category JSONB,          -- {category: {up: X, down: Y}}

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(date, hour)
);

-- Indexes
CREATE INDEX idx_feedback_analytics_date ON feedback_analytics(date);
```

---

## Training Tables

### 11. training_data

Stores validated training examples.

```sql
CREATE TABLE training_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Source
    feedback_id UUID REFERENCES feedback(id),
    source_type VARCHAR(50) NOT NULL,    -- 'positive_feedback', 'correction', 'manual', 'synthetic'

    -- Training example
    training_type VARCHAR(50) NOT NULL,  -- 'embedding', 'generation'

    -- For embedding training (triplets)
    anchor_text TEXT,                    -- Query text
    positive_text TEXT,                  -- Relevant document/answer
    negative_text TEXT,                  -- Irrelevant document/answer

    -- For LLM training
    system_prompt TEXT,
    user_message TEXT,                   -- Context + question
    assistant_message TEXT,              -- Correct answer

    -- Quality
    quality_score DECIMAL(3,2),          -- 0.00 - 1.00
    validated BOOLEAN DEFAULT FALSE,
    validated_by UUID REFERENCES users(id),
    validated_at TIMESTAMP WITH TIME ZONE,

    -- Usage tracking
    used_in_training BOOLEAN DEFAULT FALSE,
    training_job_id UUID,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_training_data_type ON training_data(training_type);
CREATE INDEX idx_training_data_source ON training_data(source_type);
CREATE INDEX idx_training_data_unused ON training_data(used_in_training)
    WHERE used_in_training = FALSE AND validated = TRUE;
CREATE INDEX idx_training_data_quality ON training_data(quality_score);
```

### 12. training_jobs

Tracks training job execution.

```sql
CREATE TABLE training_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Job type
    training_type VARCHAR(50) NOT NULL,  -- 'embedding', 'llm'
    model_type VARCHAR(100) NOT NULL,    -- Base model being fine-tuned

    -- Status
    status VARCHAR(50) NOT NULL,         -- 'pending', 'running', 'completed', 'failed'

    -- Configuration
    config JSONB NOT NULL,               -- Hyperparameters, settings

    -- Training data
    training_data_count INTEGER,
    validation_data_count INTEGER,

    -- Results
    metrics JSONB,                       -- Training metrics
    output_model_id UUID,                -- Reference to model_versions

    -- External references
    external_job_id VARCHAR(200),        -- OpenAI fine-tune job ID, etc.

    -- Error handling
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Indexes
CREATE INDEX idx_training_jobs_status ON training_jobs(status);
CREATE INDEX idx_training_jobs_type ON training_jobs(training_type);
CREATE INDEX idx_training_jobs_created ON training_jobs(created_at);
```

### 13. model_versions

Tracks all model versions for A/B testing and rollback.

```sql
CREATE TABLE model_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Model identification
    model_type VARCHAR(50) NOT NULL,     -- 'embedding', 'generation'
    model_name VARCHAR(100) NOT NULL,
    version VARCHAR(50) NOT NULL,

    -- Source
    training_job_id UUID REFERENCES training_jobs(id),
    base_model VARCHAR(200),             -- Parent model

    -- Storage
    model_path VARCHAR(500),             -- Local path or S3 URI
    external_model_id VARCHAR(200),      -- OpenAI model ID, etc.

    -- Evaluation
    evaluation_metrics JSONB,            -- Benchmark results

    -- Deployment status
    is_active BOOLEAN DEFAULT FALSE,
    traffic_percentage INTEGER DEFAULT 0, -- For gradual rollout

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    activated_at TIMESTAMP WITH TIME ZONE,
    deactivated_at TIMESTAMP WITH TIME ZONE,

    UNIQUE(model_type, model_name, version)
);

-- Indexes
CREATE INDEX idx_model_versions_active ON model_versions(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_model_versions_type ON model_versions(model_type);
```

---

## Content Moderation Tables

### 14. moderation_rules

Configurable moderation rules.

```sql
CREATE TABLE moderation_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Rule identification
    rule_type VARCHAR(50) NOT NULL,      -- 'blocked_word', 'blocked_topic', 'required_disclaimer'
    rule_name VARCHAR(100) NOT NULL,

    -- Rule definition
    pattern VARCHAR(500),                -- Regex pattern
    keywords TEXT[],                     -- Word list

    -- Action
    action VARCHAR(50) NOT NULL,         -- 'block', 'replace', 'flag', 'add_disclaimer'
    replacement_text TEXT,               -- For 'replace' action
    disclaimer_text TEXT,                -- For 'add_disclaimer' action

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 100,        -- Lower = higher priority

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_moderation_rules_type ON moderation_rules(rule_type);
CREATE INDEX idx_moderation_rules_active ON moderation_rules(is_active, priority);
```

### 15. moderation_logs

Logs moderation actions.

```sql
CREATE TABLE moderation_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    response_id UUID REFERENCES responses(id),

    -- What was caught
    rule_id UUID REFERENCES moderation_rules(id),
    matched_text TEXT,

    -- Action taken
    action_taken VARCHAR(50),
    original_text TEXT,
    modified_text TEXT,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_moderation_logs_response ON moderation_logs(response_id);
CREATE INDEX idx_moderation_logs_rule ON moderation_logs(rule_id);
CREATE INDEX idx_moderation_logs_created ON moderation_logs(created_at);
```

---

## Views

### Feedback Summary View

```sql
CREATE VIEW v_feedback_summary AS
SELECT
    DATE(f.created_at) as date,
    q.detected_intent,
    COUNT(*) as total_feedback,
    COUNT(*) FILTER (WHERE f.feedback_type = 'thumbs_up') as thumbs_up,
    COUNT(*) FILTER (WHERE f.feedback_type = 'thumbs_down') as thumbs_down,
    COUNT(*) FILTER (WHERE f.feedback_type = 'correction') as corrections,
    ROUND(
        COUNT(*) FILTER (WHERE f.feedback_type = 'thumbs_up')::DECIMAL /
        NULLIF(COUNT(*), 0),
        4
    ) as satisfaction_rate
FROM feedback f
JOIN responses r ON f.response_id = r.id
JOIN queries q ON r.query_id = q.id
GROUP BY DATE(f.created_at), q.detected_intent;
```

### Training Data Ready View

```sql
CREATE VIEW v_training_data_ready AS
SELECT
    td.*,
    f.feedback_type,
    q.query_text,
    r.response_text
FROM training_data td
LEFT JOIN feedback f ON td.feedback_id = f.id
LEFT JOIN responses r ON f.response_id = r.id
LEFT JOIN queries q ON r.query_id = q.id
WHERE td.validated = TRUE
AND td.used_in_training = FALSE
AND td.quality_score >= 0.7;
```

### Model Performance View

```sql
CREATE VIEW v_model_performance AS
SELECT
    r.model_name,
    r.model_version,
    DATE(r.created_at) as date,
    COUNT(*) as response_count,
    AVG(r.confidence_score) as avg_confidence,
    COUNT(*) FILTER (WHERE f.feedback_type = 'thumbs_up') as thumbs_up,
    COUNT(*) FILTER (WHERE f.feedback_type = 'thumbs_down') as thumbs_down,
    ROUND(
        COUNT(*) FILTER (WHERE f.feedback_type = 'thumbs_up')::DECIMAL /
        NULLIF(COUNT(*) FILTER (WHERE f.feedback_type IN ('thumbs_up', 'thumbs_down')), 0),
        4
    ) as satisfaction_rate
FROM responses r
LEFT JOIN feedback f ON r.id = f.response_id
GROUP BY r.model_name, r.model_version, DATE(r.created_at);
```

---

## Migration Script

```sql
-- Migration: 001_initial_schema.sql

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";      -- pgvector for embeddings
CREATE EXTENSION IF NOT EXISTS "pg_trgm";     -- Trigram similarity

-- Create tables in order (respecting foreign keys)
-- 1. Core tables
-- [knowledge_items, chunks, embeddings, entities as above]

-- 2. User tables
-- [users, sessions as above]

-- 3. Query/Response tables
-- [queries, responses as above]

-- 4. Feedback tables
-- [feedback, feedback_analytics as above]

-- 5. Training tables
-- [training_data, training_jobs, model_versions as above]

-- 6. Moderation tables
-- [moderation_rules, moderation_logs as above]

-- 7. Views
-- [v_feedback_summary, v_training_data_ready, v_model_performance as above]

-- Insert default moderation rules
INSERT INTO moderation_rules (rule_type, rule_name, keywords, action, is_active, priority)
VALUES
    ('blocked_word', 'profanity', ARRAY['<list of blocked words>'], 'block', TRUE, 10),
    ('blocked_topic', 'politics', ARRAY['election', 'vote', 'political party'], 'redirect', TRUE, 20),
    ('blocked_topic', 'competitors', ARRAY['competitor names'], 'redirect', TRUE, 20);
```

---

## Indexes Summary

| Table | Index | Purpose |
|-------|-------|---------|
| knowledge_items | type, category, audience, tags | Filtering |
| knowledge_items | FTS index | Full-text search |
| chunks | knowledge_item_id | Join performance |
| embeddings | vector (ivfflat) | Approximate NN search |
| queries | user_id, session_id, created_at | Analytics |
| responses | query_id, model_name | Joins, analytics |
| feedback | response_id, type, unreviewed | Processing queue |
| training_data | unused, quality_score | Training batch selection |
| model_versions | active, type | Model serving |

---

## Data Retention Policy

| Table | Retention | Archive Strategy |
|-------|-----------|------------------|
| knowledge_items | Indefinite | Soft delete |
| chunks, embeddings | Match knowledge_items | Cascade delete |
| queries | 2 years | Archive to cold storage |
| responses | 2 years | Archive to cold storage |
| feedback | Indefinite | Critical for training |
| training_data | Indefinite | Critical for retraining |
| moderation_logs | 1 year | Archive monthly |
