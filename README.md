# Production RAG System

A production-ready Retrieval-Augmented Generation (RAG) system that addresses the five critical areas often overlooked in tutorials:

1. **Data Preparation** - Chunking, embeddings, and validation
2. **Retrieval** - Hybrid search, reranking, and metadata filtering
3. **Generation** - Token management, prompt engineering, hallucination prevention
4. **Orchestration** - Query routing, fallbacks, tool handoff
5. **Observability** - Logging, metrics, and feedback loops

## Installation

```bash
pip install -e .
```

## Quick Start

```python
from retrieval_app import RAGPipeline

# Initialize the pipeline
pipeline = RAGPipeline()

# Ingest documents
documents = [
    ("doc_id", "Document text content...", {"source": "file.pdf"})
]
pipeline.ingest_documents(documents)

# Query
response = pipeline.query("What is machine learning?")
print(response.answer)
print(f"Confidence: {response.confidence}")
print(f"Sources: {response.sources}")
```

## Architecture

### Data Preparation (`data_prep/`)

- **Chunker**: Multiple strategies (fixed-size, sentence, recursive, semantic)
- **Embedder**: Embedding generation with caching and batch processing
- **Validator**: Data quality checks before indexing
- **Truth Sets**: Ground truth management for evaluation

### Retrieval (`retrieval/`)

- **Hybrid Retriever**: Combines semantic and lexical (BM25) search
- **Vector Store**: Pluggable backends (in-memory, ChromaDB)
- **Reranker**: Cross-encoder and MMR reranking for precision
- **Metadata Filtering**: Filter results by document attributes

### Generation (`generation/`)

- **Prompt Manager**: Template-based prompt construction
- **Evidence Selector**: Smart selection within token budgets
- **Response Generator**: LLM integration with hallucination checks

### Orchestration (`orchestration/`)

- **Query Router**: Route queries to appropriate handlers
- **Query Processor**: Rewriting, decomposition, filter extraction
- **Fallback Handler**: Graceful degradation strategies

### Observability (`observability/`)

- **Logger**: Structured logging with retrieval miss tracking
- **Metrics**: Latency percentiles, quality scores, Prometheus export
- **Feedback**: User feedback collection and analysis

## Configuration

```python
from retrieval_app import RAGConfig

# Use preset configurations
config = RAGConfig.for_high_precision()  # Optimize for accuracy
config = RAGConfig.for_high_recall()     # Optimize for coverage
config = RAGConfig.for_low_latency()     # Optimize for speed

# Or customize
config = RAGConfig()
config.retrieval.mode = RetrievalMode.HYBRID
config.retrieval.semantic_weight = 0.7
config.generation.max_context_tokens = 4000
```

## Evaluation

```python
from retrieval_app.data_prep.truth_sets import TruthSetManager

# Create truth sets
manager = TruthSetManager()
manager.add_entry(
    truth_set_name="my_test_set",
    query="What is X?",
    expected_answer="X is...",
    relevant_chunk_ids=["chunk_1", "chunk_2"]
)

# Evaluate
results = manager.evaluate_retrieval(
    truth_set_name="my_test_set",
    retrieval_fn=pipeline.retriever.get_chunk_ids
)
print(f"Mean Recall: {results.mean_recall:.2%}")
```

## Key Design Decisions

### Why Hybrid Search?
Semantic search alone misses exact keyword matches. BM25 alone misses semantic similarity. Combining them with Reciprocal Rank Fusion gives the best of both.

### Why Reranking?
Initial retrieval optimizes for recall. Reranking with cross-encoders optimizes for precision, ensuring the most relevant chunks appear first.

### Why Token Budgeting?
"Stuffing all context in the prompt" leads to worse answers. Smart evidence selection respects token limits while maximizing information value.

### Why Query Routing?
Not every query needs RAG. Simple questions, calculations, and out-of-scope queries should be handled differently to save resources and improve UX.

### Why Feedback Loops?
Without feedback, RAG systems "rot silently." Collecting user feedback enables continuous improvement and catch regressions.

## License

MIT
