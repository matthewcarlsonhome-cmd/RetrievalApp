# Company Knowledge Expert - Architecture Design

## Executive Summary

This document outlines the architectural evolution from a **Resume Matching System** to a **General-Purpose Company Knowledge Expert** - an AI-powered system that can answer questions about any aspect of a business: products, services, workflows, policies, and more.

---

## Table of Contents

1. [Vision and Use Cases](#vision-and-use-cases)
2. [Current vs. Target Architecture](#current-vs-target-architecture)
3. [Knowledge Repository Architecture](#knowledge-repository-architecture)
4. [Ingestion Pipeline](#ingestion-pipeline)
5. [Query Understanding and Routing](#query-understanding-and-routing)
6. [Retrieval Strategy](#retrieval-strategy)
7. [Response Generation](#response-generation)
8. [Domain Training and Adaptation](#domain-training-and-adaptation)
9. [Feedback and Continuous Learning](#feedback-and-continuous-learning)
10. [Implementation Roadmap](#implementation-roadmap)

---

## Vision and Use Cases

### The Goal

Transform from a specialized matching tool into a **Company Knowledge Expert** that can:

```
┌─────────────────────────────────────────────────────────────────┐
│                    COMPANY KNOWLEDGE EXPERT                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  "What's our return policy?"                                    │
│  "How do I configure the enterprise API?"                       │
│  "What's the difference between Pro and Enterprise plans?"      │
│  "Walk me through the onboarding workflow"                      │
│  "Who should I contact about billing issues?"                   │
│  "What certifications does our product have?"                   │
│                                                                  │
│  ──────────────────────────────────────────────────────────────│
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Customer   │  │   Employee   │  │    Sales     │          │
│  │   Support    │  │   Onboarding │  │  Enablement  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Product    │  │   Partner    │  │   Internal   │          │
│  │   Questions  │  │   Portal     │  │     Ops      │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Primary Use Cases

| Use Case | Audience | Example Queries |
|----------|----------|-----------------|
| **Customer Support** | End users, prospects | "How do I reset my password?", "What's included in the free tier?" |
| **Sales Enablement** | Sales team | "What are our competitive advantages vs. Competitor X?" |
| **Employee Onboarding** | New hires | "What's the PTO policy?", "How do I submit expenses?" |
| **Technical Documentation** | Developers, integrators | "How do I authenticate with the API?", "What are the rate limits?" |
| **Product Knowledge** | Anyone | "What features are in the Q2 roadmap?", "How does feature X work?" |
| **Process/Workflow** | Internal teams | "What's the approval process for vendor contracts?" |

---

## Current vs. Target Architecture

### Current Architecture (Resume Matching)

```
┌─────────────────────────────────────────────────────────────────┐
│                    CURRENT: RESUME MATCHING                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐    │
│  │   Resumes    │────▶│   Matcher    │────▶│   Ranked     │    │
│  │   (JSON)     │     │  TF-IDF/     │     │   Results    │    │
│  └──────────────┘     │   Neural     │     └──────────────┘    │
│                       └──────────────┘                          │
│  ┌──────────────┐            ▲                                  │
│  │     Job      │────────────┘                                  │
│  │ Description  │                                               │
│  └──────────────┘                                               │
│                                                                  │
│  DATA: Structured JSON (resumes, jobs)                          │
│  QUERY: Job requirements                                         │
│  OUTPUT: Ranked candidate list with scores                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Target Architecture (Company Knowledge Expert)

```
┌─────────────────────────────────────────────────────────────────┐
│                  TARGET: COMPANY KNOWLEDGE EXPERT                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   KNOWLEDGE REPOSITORY                    │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │   │
│  │  │  Docs   │ │  FAQs   │ │Workflows│ │ Product │       │   │
│  │  │ (PDF,   │ │ (Q&A    │ │ (BPMN,  │ │  Info   │       │   │
│  │  │  MD)    │ │  pairs) │ │  steps) │ │ (specs) │       │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   INGESTION PIPELINE                      │   │
│  │  Parse → Chunk → Embed → Index → Validate                │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   QUERY PROCESSING                        │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐              │   │
│  │  │  Intent  │─▶│  Query   │─▶│  Route   │              │   │
│  │  │ Classify │  │ Rewrite  │  │ (FAQ/Doc/│              │   │
│  │  └──────────┘  └──────────┘  │ Workflow)│              │   │
│  │                               └──────────┘              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                 HYBRID RETRIEVAL                          │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐              │   │
│  │  │ Semantic │  │  BM25    │  │  FAQ     │──▶ RRF Fusion│   │
│  │  │  Search  │  │ Keyword  │  │ Matching │              │   │
│  │  └──────────┘  └──────────┘  └──────────┘              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                 RESPONSE GENERATION                       │   │
│  │  Context Selection → LLM Synthesis → Citation → Validate │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              NATURAL LANGUAGE RESPONSE                    │   │
│  │  "Based on our documentation, here's how to..."          │   │
│  │  [Source: Product Guide v2.3, Section 4.1]               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Knowledge Repository Architecture

### Knowledge Categories

```
knowledge_repository/
├── documents/              # Long-form documentation
│   ├── product/           # Product guides, manuals
│   ├── technical/         # API docs, integration guides
│   ├── policies/          # Company policies, procedures
│   └── training/          # Training materials
│
├── faqs/                   # Question-Answer pairs
│   ├── customer/          # Customer-facing FAQs
│   ├── internal/          # Employee FAQs
│   └── technical/         # Developer FAQs
│
├── workflows/              # Step-by-step processes
│   ├── customer/          # Customer journeys
│   ├── internal/          # Internal processes
│   └── approvals/         # Approval workflows
│
├── products/               # Product information
│   ├── features/          # Feature descriptions
│   ├── pricing/           # Pricing information
│   └── comparisons/       # Competitive comparisons
│
├── people/                 # Organizational knowledge
│   ├── directory/         # Who to contact
│   ├── teams/             # Team structures
│   └── expertise/         # Subject matter experts
│
└── metadata/               # Knowledge metadata
    ├── taxonomy.json      # Category hierarchy
    ├── access_control.json # Who can access what
    └── freshness.json     # Last updated dates
```

### Knowledge Schema

```python
@dataclass
class KnowledgeItem:
    """Universal schema for all knowledge types."""

    # Identity
    id: str                          # Unique identifier
    type: KnowledgeType              # document, faq, workflow, product, person
    category: str                    # Product, Policy, Technical, etc.
    subcategory: str                 # More specific classification

    # Content
    title: str                       # Human-readable title
    content: str                     # Main content (may be chunked)
    summary: str                     # AI-generated summary

    # Structure (varies by type)
    sections: List[Section]          # For documents
    steps: List[Step]                # For workflows
    question: str                    # For FAQs
    answer: str                      # For FAQs

    # Metadata
    source: str                      # Original source file/URL
    author: str                      # Content owner
    created_at: datetime
    updated_at: datetime
    version: str

    # Access Control
    audience: List[str]              # customer, employee, partner, public
    permissions: List[str]           # Who can view

    # Search Optimization
    tags: List[str]                  # Manual tags
    entities: List[str]              # Extracted entities (products, features)
    embedding: np.ndarray            # Vector embedding

    # Quality Metrics
    confidence: float                # How reliable is this info
    usage_count: int                 # How often retrieved
    feedback_score: float            # User ratings
```

### Knowledge Types

| Type | Schema Fields | Example |
|------|---------------|---------|
| **Document** | title, content, sections | Product manual, API guide |
| **FAQ** | question, answer, category | "How do I reset my password?" |
| **Workflow** | title, steps, decision_points | Expense approval process |
| **Product** | name, features, pricing, comparisons | Feature comparison table |
| **Person** | name, role, expertise, contact | "Contact Sarah for billing" |

---

## Ingestion Pipeline

### Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     INGESTION PIPELINE                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  SOURCE FILES                                                    │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐              │
│  │ PDF │ │ MD  │ │DOCX │ │HTML │ │ CSV │ │JSON │              │
│  └──┬──┘ └──┬──┘ └──┬──┘ └──┬──┘ └──┬──┘ └──┬──┘              │
│     └───────┴───────┴───────┴───────┴───────┘                   │
│                          │                                       │
│                          ▼                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 1. EXTRACTION                                            │   │
│  │    - Parse document structure                            │   │
│  │    - Extract text, tables, images                        │   │
│  │    - Preserve formatting/hierarchy                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                       │
│                          ▼                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 2. CLASSIFICATION                                        │   │
│  │    - Detect knowledge type (doc/faq/workflow/product)    │   │
│  │    - Assign category and subcategory                     │   │
│  │    - Identify audience (customer/internal/public)        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                       │
│                          ▼                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 3. CHUNKING                                              │   │
│  │    - Semantic chunking (by section/topic)                │   │
│  │    - Overlap for context preservation                    │   │
│  │    - Special handling for Q&A, steps, tables             │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                       │
│                          ▼                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 4. ENRICHMENT                                            │   │
│  │    - Generate summaries (LLM)                            │   │
│  │    - Extract entities (products, features, people)       │   │
│  │    - Generate Q&A pairs from documents (LLM)             │   │
│  │    - Link related content                                │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                       │
│                          ▼                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 5. EMBEDDING                                             │   │
│  │    - Generate vector embeddings                          │   │
│  │    - Domain-adapted model preferred                      │   │
│  │    - Multiple embeddings (title, content, summary)       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                       │
│                          ▼                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 6. INDEXING                                              │   │
│  │    - Vector store (semantic search)                      │   │
│  │    - BM25 index (keyword search)                         │   │
│  │    - FAQ index (question matching)                       │   │
│  │    - Metadata index (filtering)                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                       │
│                          ▼                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 7. VALIDATION                                            │   │
│  │    - Check for duplicates                                │   │
│  │    - Verify links and references                         │   │
│  │    - Flag outdated content                               │   │
│  │    - Quality scoring                                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Chunking Strategies by Content Type

| Content Type | Chunking Strategy | Chunk Size | Overlap |
|--------------|-------------------|------------|---------|
| **Long Documents** | Semantic (by heading/section) | 500-1000 tokens | 100 tokens |
| **FAQs** | Keep Q&A pairs together | Varies | None |
| **Workflows** | By step, preserve sequence | 200-400 tokens | Include prev step context |
| **Tables** | Keep table intact or row-by-row | Varies | Include headers |
| **Code Examples** | By function/block | 300-500 tokens | Include imports/context |

### Auto-Generated Q&A Pairs

For every document, automatically generate FAQ-style entries:

```python
def generate_qa_pairs(document: str, llm: LLM) -> List[Tuple[str, str]]:
    """
    Generate question-answer pairs from document content.

    Example Input:
        "Our return policy allows returns within 30 days of purchase.
         Items must be in original packaging with receipt."

    Example Output:
        [
            ("What is the return window?", "30 days from purchase"),
            ("Do I need my receipt for returns?", "Yes, receipt required"),
            ("What condition must items be in?", "Original packaging")
        ]
    """
    prompt = """
    Generate 3-5 question-answer pairs from this content.
    Questions should be natural queries a user might ask.
    Answers should be concise and directly from the content.

    Content: {document}

    Format: Q: [question]\nA: [answer]
    """
    return llm.generate(prompt.format(document=document))
```

---

## Query Understanding and Routing

### Query Processing Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                    QUERY PROCESSING                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  User Query: "How do I integrate with Salesforce?"              │
│                          │                                       │
│                          ▼                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 1. INTENT CLASSIFICATION                                 │   │
│  │                                                          │   │
│  │    ┌──────────────┐                                     │   │
│  │    │   Intents    │                                     │   │
│  │    ├──────────────┤                                     │   │
│  │    │ • how_to     │ ◄── DETECTED                        │   │
│  │    │ • what_is    │                                     │   │
│  │    │ • comparison │                                     │   │
│  │    │ • pricing    │                                     │   │
│  │    │ • contact    │                                     │   │
│  │    │ • troubleshoot│                                    │   │
│  │    │ • policy     │                                     │   │
│  │    └──────────────┘                                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                       │
│                          ▼                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 2. ENTITY EXTRACTION                                     │   │
│  │                                                          │   │
│  │    Entities: [Salesforce (integration), integrate (action)]│   │
│  │    Products: [API, integrations]                         │   │
│  │    Features: [Salesforce connector]                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                       │
│                          ▼                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 3. QUERY EXPANSION                                       │   │
│  │                                                          │   │
│  │    Original: "How do I integrate with Salesforce?"       │   │
│  │    Expanded: "Salesforce integration setup guide API     │   │
│  │              connector CRM sync configuration"           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                       │
│                          ▼                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 4. ROUTING DECISION                                      │   │
│  │                                                          │   │
│  │    Intent: how_to                                        │   │
│  │    Entity: integration                                   │   │
│  │                                                          │   │
│  │    Route: TECHNICAL_DOCS + WORKFLOW                      │   │
│  │    Filters: category=technical, type=[doc, workflow]     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Intent Classification

```python
class QueryIntent(Enum):
    HOW_TO = "how_to"           # Step-by-step instructions
    WHAT_IS = "what_is"         # Definitions, explanations
    COMPARISON = "comparison"    # Compare options/products
    PRICING = "pricing"          # Cost, plans, billing
    CONTACT = "contact"          # Who to reach out to
    TROUBLESHOOT = "troubleshoot" # Fix problems
    POLICY = "policy"            # Rules, procedures
    STATUS = "status"            # Current state of something
    GENERAL = "general"          # Catch-all


INTENT_ROUTING = {
    QueryIntent.HOW_TO: {
        "primary": ["workflow", "document"],
        "boost_categories": ["technical", "guides"],
        "response_style": "step_by_step"
    },
    QueryIntent.WHAT_IS: {
        "primary": ["faq", "document"],
        "boost_categories": ["product", "concepts"],
        "response_style": "explanatory"
    },
    QueryIntent.COMPARISON: {
        "primary": ["product"],
        "boost_categories": ["comparisons", "features"],
        "response_style": "table_comparison"
    },
    QueryIntent.PRICING: {
        "primary": ["product", "faq"],
        "boost_categories": ["pricing", "plans"],
        "response_style": "structured"
    },
    QueryIntent.CONTACT: {
        "primary": ["person", "faq"],
        "boost_categories": ["directory", "support"],
        "response_style": "direct"
    },
    QueryIntent.TROUBLESHOOT: {
        "primary": ["faq", "document"],
        "boost_categories": ["troubleshooting", "technical"],
        "response_style": "diagnostic"
    },
}
```

---

## Retrieval Strategy

### Multi-Index Hybrid Retrieval

```
┌─────────────────────────────────────────────────────────────────┐
│                    HYBRID RETRIEVAL                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Query: "How do I integrate with Salesforce?"                   │
│                          │                                       │
│     ┌────────────────────┼────────────────────┐                 │
│     ▼                    ▼                    ▼                 │
│  ┌─────────┐       ┌─────────┐       ┌─────────┐               │
│  │ SEMANTIC│       │ KEYWORD │       │   FAQ   │               │
│  │ SEARCH  │       │  BM25   │       │ MATCHER │               │
│  │         │       │         │       │         │               │
│  │Vector DB│       │Elastic/ │       │Question │               │
│  │(Pinecone│       │BM25 idx │       │Similarity│              │
│  │Weaviate)│       │         │       │         │               │
│  └────┬────┘       └────┬────┘       └────┬────┘               │
│       │                 │                 │                     │
│       │ top 20          │ top 20          │ top 10             │
│       │                 │                 │                     │
│       └────────────────┬┴─────────────────┘                     │
│                        │                                         │
│                        ▼                                         │
│              ┌─────────────────┐                                │
│              │   RRF FUSION    │                                │
│              │                 │                                │
│              │ Combine ranks   │                                │
│              │ from all sources│                                │
│              └────────┬────────┘                                │
│                       │                                          │
│                       ▼                                          │
│              ┌─────────────────┐                                │
│              │   RERANKING     │                                │
│              │                 │                                │
│              │ Cross-encoder   │                                │
│              │ relevance score │                                │
│              └────────┬────────┘                                │
│                       │                                          │
│                       ▼                                          │
│              ┌─────────────────┐                                │
│              │  MMR DIVERSITY  │                                │
│              │                 │                                │
│              │ Remove redundant│                                │
│              │ results         │                                │
│              └────────┬────────┘                                │
│                       │                                          │
│                       ▼                                          │
│              Top 5 Diverse, Relevant Results                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### FAQ-Optimized Retrieval

For FAQ-type queries, use specialized matching:

```python
class FAQMatcher:
    """
    Specialized matching for FAQ-style Q&A pairs.

    Uses question-to-question similarity rather than
    question-to-document similarity.
    """

    def __init__(self):
        self.question_embeddings = {}  # question_id -> embedding
        self.question_index = None     # FAISS/Annoy index

    def index_faqs(self, faqs: List[FAQ]):
        """Index just the questions, not answers."""
        for faq in faqs:
            # Embed the question only
            embedding = self.embed(faq.question)
            self.question_embeddings[faq.id] = embedding

        # Build fast similarity index
        self.question_index = build_index(self.question_embeddings)

    def find_similar_questions(self, query: str, top_k: int = 5):
        """Find FAQs with similar questions."""
        query_embedding = self.embed(query)

        # Find similar questions
        similar_ids = self.question_index.search(query_embedding, top_k)

        return [self.faqs[id] for id in similar_ids]
```

### Metadata Filtering

```python
def apply_filters(results: List[Result], filters: QueryFilters) -> List[Result]:
    """
    Apply metadata filters based on query context.

    Filters:
    - audience: Only show content user has access to
    - category: Limit to relevant categories
    - freshness: Prefer recent content
    - confidence: Minimum quality threshold
    """
    filtered = results

    # Access control
    if filters.user_audience:
        filtered = [r for r in filtered
                   if filters.user_audience in r.metadata.audience]

    # Category filtering
    if filters.categories:
        filtered = [r for r in filtered
                   if r.metadata.category in filters.categories]

    # Freshness boost (not filter)
    for r in filtered:
        age_days = (datetime.now() - r.metadata.updated_at).days
        if age_days < 30:
            r.score *= 1.1  # 10% boost for recent content
        elif age_days > 365:
            r.score *= 0.9  # 10% penalty for old content

    return filtered
```

---

## Response Generation

### Generation Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                   RESPONSE GENERATION                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Retrieved Context (5 relevant chunks)                          │
│                          │                                       │
│                          ▼                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 1. CONTEXT SELECTION                                     │   │
│  │                                                          │   │
│  │    - Token budget allocation (e.g., 4000 tokens)        │   │
│  │    - Relevance-weighted selection                        │   │
│  │    - Diversity consideration                             │   │
│  │    - Source coverage (multiple sources preferred)        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                       │
│                          ▼                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 2. PROMPT CONSTRUCTION                                   │   │
│  │                                                          │   │
│  │    System: You are a helpful company knowledge assistant │   │
│  │    Context: [selected chunks with source citations]      │   │
│  │    Query: [user's question]                              │   │
│  │    Instructions: Answer using ONLY the context provided  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                       │
│                          ▼                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 3. LLM GENERATION                                        │   │
│  │                                                          │   │
│  │    Model: GPT-4 / Claude / Llama                        │   │
│  │    Temperature: 0.1 (factual)                           │   │
│  │    Max tokens: 500                                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                       │
│                          ▼                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 4. CITATION INJECTION                                    │   │
│  │                                                          │   │
│  │    Add source references: [1], [2], etc.                │   │
│  │    Link to original documents                            │   │
│  │    Include "Last updated" dates                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                       │
│                          ▼                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 5. VALIDATION                                            │   │
│  │                                                          │   │
│  │    - Check for hallucination (claims not in context)    │   │
│  │    - Verify citations are accurate                       │   │
│  │    - Confidence scoring                                  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                       │
│                          ▼                                       │
│                                                                  │
│  FINAL RESPONSE:                                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ To integrate with Salesforce, follow these steps:       │   │
│  │                                                          │   │
│  │ 1. Navigate to Settings > Integrations [1]              │   │
│  │ 2. Click "Add New" and select Salesforce                │   │
│  │ 3. Enter your Salesforce API credentials [2]            │   │
│  │ 4. Configure field mappings as needed                    │   │
│  │                                                          │   │
│  │ For detailed configuration options, see the             │   │
│  │ Integration Guide [3].                                   │   │
│  │                                                          │   │
│  │ Sources:                                                 │   │
│  │ [1] Admin Guide v2.1 - Integrations (Updated: Jan 2025) │   │
│  │ [2] API Documentation - Authentication                   │   │
│  │ [3] Salesforce Integration Guide                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Response Styles by Intent

```python
RESPONSE_TEMPLATES = {
    "step_by_step": """
        Based on our documentation, here's how to {action}:

        {numbered_steps}

        {additional_tips}

        Sources: {sources}
    """,

    "explanatory": """
        {concept} is {definition}.

        Key points:
        {bullet_points}

        {examples}

        Learn more: {related_links}
    """,

    "table_comparison": """
        Here's a comparison of {options}:

        | Feature | {option_a} | {option_b} |
        |---------|------------|------------|
        {comparison_rows}

        Recommendation: {recommendation}
    """,

    "diagnostic": """
        This issue is usually caused by: {common_causes}

        To resolve:
        {troubleshooting_steps}

        If the issue persists, contact {support_contact}.
    """,
}
```

---

## Domain Training and Adaptation

### Approach 1: Fine-tuned Embeddings

```python
class DomainAdaptedEmbedder:
    """
    Fine-tune embedding model on company-specific content.

    Benefits:
    - Better understanding of domain terminology
    - Improved semantic similarity for company concepts
    - Higher retrieval accuracy
    """

    def __init__(self, base_model: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(base_model)

    def fine_tune(self, training_data: List[Tuple[str, str, float]]):
        """
        Fine-tune on triplets: (anchor, positive, negative)

        Training data examples:
        - (query, relevant_doc, irrelevant_doc)
        - (question, correct_answer, wrong_answer)
        """
        train_examples = [
            InputExample(texts=[anchor, positive], label=1.0)
            for anchor, positive, _ in training_data
        ]

        train_dataloader = DataLoader(train_examples, batch_size=16)
        train_loss = losses.CosineSimilarityLoss(self.model)

        self.model.fit(
            train_objectives=[(train_dataloader, train_loss)],
            epochs=3,
            warmup_steps=100
        )

    def generate_training_data(self, faqs: List[FAQ], docs: List[Document]):
        """
        Auto-generate training triplets from existing content.
        """
        training_data = []

        for faq in faqs:
            # Positive: question -> answer
            # Negative: question -> random other answer
            positive = (faq.question, faq.answer)
            negative_answer = random.choice([f.answer for f in faqs if f.id != faq.id])
            training_data.append((faq.question, faq.answer, negative_answer))

        return training_data
```

### Approach 2: Retrieval-Augmented Fine-tuning

```python
class RAGFineTuner:
    """
    Fine-tune the generation model on company Q&A pairs.

    Steps:
    1. Collect real user questions and expert answers
    2. Create training examples with retrieved context
    3. Fine-tune LLM on (context, question) -> answer
    """

    def create_training_example(
        self,
        question: str,
        expert_answer: str,
        retriever: Retriever
    ) -> Dict:
        """Create a single training example."""
        # Get context that would be retrieved
        context = retriever.retrieve(question, top_k=5)

        return {
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Context: {context}\n\nQuestion: {question}"},
                {"role": "assistant", "content": expert_answer}
            ]
        }

    def fine_tune(self, examples: List[Dict], base_model: str = "gpt-3.5-turbo"):
        """Fine-tune using OpenAI fine-tuning API or similar."""
        # Upload training file
        training_file = upload_training_data(examples)

        # Start fine-tuning job
        job = create_fine_tuning_job(
            training_file=training_file,
            model=base_model,
            hyperparameters={"n_epochs": 3}
        )

        return job.fine_tuned_model
```

### Approach 3: In-Context Learning with Examples

```python
class FewShotPromptBuilder:
    """
    Use curated examples in prompts for better responses.

    No fine-tuning required - just good examples.
    """

    def __init__(self, example_store: ExampleStore):
        self.examples = example_store

    def build_prompt(self, query: str, context: str) -> str:
        """Build prompt with relevant few-shot examples."""

        # Find similar past Q&A examples
        similar_examples = self.examples.find_similar(query, top_k=3)

        examples_text = "\n\n".join([
            f"Example {i+1}:\n"
            f"Question: {ex.question}\n"
            f"Context: {ex.context_used}\n"
            f"Answer: {ex.answer}"
            for i, ex in enumerate(similar_examples)
        ])

        return f"""
        You are a helpful company knowledge assistant.

        Here are some examples of good answers:

        {examples_text}

        Now answer this question using ONLY the provided context:

        Context: {context}

        Question: {query}

        Answer:
        """
```

---

## Feedback and Continuous Learning

### Feedback Collection

```
┌─────────────────────────────────────────────────────────────────┐
│                   FEEDBACK LOOP                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  USER INTERACTION                                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Q: How do I reset my password?                          │   │
│  │                                                          │   │
│  │ A: To reset your password, go to Settings > Security... │   │
│  │                                                          │   │
│  │    ┌─────────┐  ┌─────────┐  ┌─────────────────┐       │   │
│  │    │   👍    │  │   👎    │  │ "Not what I     │       │   │
│  │    │ Helpful │  │  Wrong  │  │  was looking for│       │   │
│  │    └─────────┘  └─────────┘  └─────────────────┘       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                       │
│                          ▼                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ FEEDBACK TYPES                                           │   │
│  │                                                          │   │
│  │ Explicit:                                                │   │
│  │   • Thumbs up/down                                       │   │
│  │   • Star ratings                                         │   │
│  │   • "This didn't answer my question"                    │   │
│  │   • User corrections                                     │   │
│  │                                                          │   │
│  │ Implicit:                                                │   │
│  │   • Click-through to sources                            │   │
│  │   • Time spent reading                                   │   │
│  │   • Follow-up questions (indicates incomplete answer)    │   │
│  │   • Support ticket created after (answer failed)         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                       │
│                          ▼                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ FEEDBACK PROCESSING                                      │   │
│  │                                                          │   │
│  │ Daily:                                                   │   │
│  │   • Aggregate feedback by query/answer                   │   │
│  │   • Flag low-rated responses for review                  │   │
│  │                                                          │   │
│  │ Weekly:                                                  │   │
│  │   • Identify knowledge gaps (unanswered questions)       │   │
│  │   • Update FAQ pairs from user corrections               │   │
│  │   • Retrain models on new examples                       │   │
│  │                                                          │   │
│  │ Monthly:                                                 │   │
│  │   • Full retrieval quality evaluation                    │   │
│  │   • Content freshness audit                              │   │
│  │   • Model performance benchmarking                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Automatic Improvement Pipeline

```python
class ContinuousImprover:
    """
    Automatically improve the knowledge base from feedback.
    """

    def daily_improvement_job(self):
        """Run daily to incorporate feedback."""

        # 1. Collect negative feedback
        bad_responses = self.feedback_store.get_negative(since="yesterday")

        for response in bad_responses:
            # 2. Analyze why it failed
            analysis = self.analyze_failure(response)

            if analysis.cause == "missing_content":
                # Flag for content team to add
                self.create_content_request(response.query)

            elif analysis.cause == "outdated_content":
                # Flag content for review
                self.flag_for_update(analysis.source_docs)

            elif analysis.cause == "retrieval_miss":
                # Add as training example for retrieval
                self.add_retrieval_training_example(
                    query=response.query,
                    relevant_doc=response.user_correction
                )

            elif analysis.cause == "generation_error":
                # Add as training example for generation
                self.add_generation_training_example(
                    query=response.query,
                    context=response.retrieved_context,
                    correct_answer=response.user_correction
                )

    def weekly_retraining_job(self):
        """Weekly model updates."""

        # Get new training examples
        new_examples = self.training_store.get_new_examples()

        if len(new_examples) > 100:
            # Retrain embedding model
            self.embedder.fine_tune(new_examples)

            # Re-index affected documents
            self.reindex_affected_docs(new_examples)
```

---

## Implementation Roadmap

### Phase 1: Foundation (Weeks 1-4)

| Task | Effort | Deliverable |
|------|--------|-------------|
| Knowledge schema design | 1 week | `KnowledgeItem` dataclass, storage schema |
| Basic ingestion pipeline | 2 weeks | PDF/MD/DOCX parsing, chunking, embedding |
| Query processing | 1 week | Intent classification, basic routing |

**Milestone**: Can ingest documents and answer basic queries

### Phase 2: Core Features (Weeks 5-8)

| Task | Effort | Deliverable |
|------|--------|-------------|
| FAQ-optimized retrieval | 1 week | Question-to-question matching |
| Hybrid search | 1 week | Semantic + BM25 + FAQ fusion |
| Response generation | 1 week | LLM integration, citation injection |
| Basic UI | 1 week | Chat interface, source display |

**Milestone**: Functional knowledge assistant with citations

### Phase 3: Intelligence (Weeks 9-12)

| Task | Effort | Deliverable |
|------|--------|-------------|
| Auto Q&A generation | 1 week | Generate FAQs from documents |
| Feedback collection | 1 week | Thumbs up/down, corrections |
| Domain adaptation | 2 weeks | Fine-tuned embeddings or few-shot |

**Milestone**: Self-improving system with domain expertise

### Phase 4: Production (Weeks 13-16)

| Task | Effort | Deliverable |
|------|--------|-------------|
| Access control | 1 week | Role-based content access |
| Analytics dashboard | 1 week | Usage, gaps, quality metrics |
| API & integrations | 1 week | Slack, Teams, website widget |
| Performance optimization | 1 week | Caching, async, scaling |

**Milestone**: Production-ready enterprise deployment

---

## Technology Stack Recommendations

### Core Components

| Component | Recommended | Alternative |
|-----------|-------------|-------------|
| **Vector Store** | Pinecone | Weaviate, Qdrant, Milvus |
| **Keyword Search** | Elasticsearch | OpenSearch, Meilisearch |
| **LLM** | GPT-4 / Claude | Llama 2, Mistral (self-hosted) |
| **Embeddings** | OpenAI ada-002 | Cohere, Sentence-Transformers |
| **Database** | PostgreSQL | MongoDB (for flexibility) |
| **Queue** | Redis + Celery | RabbitMQ |
| **Cache** | Redis | Memcached |

### Cost Estimates (Monthly)

| Scale | Vector Store | LLM API | Compute | Total |
|-------|--------------|---------|---------|-------|
| Small (<10K queries) | $70 | $50 | $100 | ~$220 |
| Medium (10K-100K queries) | $250 | $500 | $300 | ~$1,050 |
| Large (100K+ queries) | $1,000 | $2,000 | $1,000 | ~$4,000 |

---

## Conclusion

This architecture transforms the current Resume Matching System into a powerful Company Knowledge Expert by:

1. **Expanding the knowledge base** from structured resumes to diverse content types
2. **Adding intelligent query routing** to handle different question types
3. **Implementing hybrid retrieval** for better accuracy
4. **Integrating LLM generation** for natural language responses
5. **Building feedback loops** for continuous improvement

The modular design allows incremental implementation, starting with basic document Q&A and evolving into a fully-trained domain expert.
