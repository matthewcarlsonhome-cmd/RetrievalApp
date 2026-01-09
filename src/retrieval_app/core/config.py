"""
Configuration management for the RAG pipeline.

Centralizes all tunable parameters with sensible defaults for production use.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ChunkingStrategy(str, Enum):
    """Available chunking strategies."""
    FIXED_SIZE = "fixed_size"
    SEMANTIC = "semantic"
    RECURSIVE = "recursive"
    SENTENCE = "sentence"


class RetrievalMode(str, Enum):
    """Retrieval strategies."""
    SEMANTIC_ONLY = "semantic_only"
    LEXICAL_ONLY = "lexical_only"
    HYBRID = "hybrid"


class FallbackMode(str, Enum):
    """Fallback behaviors when retrieval fails or is skipped."""
    DIRECT_LLM = "direct_llm"
    TOOL_HANDOFF = "tool_handoff"
    HUMAN_ESCALATION = "human_escalation"
    CLARIFICATION = "clarification"


@dataclass
class ChunkingConfig:
    """Configuration for document chunking."""
    strategy: ChunkingStrategy = ChunkingStrategy.RECURSIVE
    chunk_size: int = 512
    chunk_overlap: int = 50
    min_chunk_size: int = 100
    max_chunk_size: int = 1000
    preserve_sentences: bool = True
    preserve_paragraphs: bool = True


@dataclass
class EmbeddingConfig:
    """Configuration for embedding generation."""
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    batch_size: int = 32
    normalize: bool = True
    cache_embeddings: bool = True
    cache_dir: Optional[str] = None


@dataclass
class RetrievalConfig:
    """Configuration for the retrieval system."""
    mode: RetrievalMode = RetrievalMode.HYBRID
    semantic_weight: float = 0.7
    lexical_weight: float = 0.3
    top_k: int = 10
    rerank_top_k: int = 5
    enable_reranking: bool = True
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    min_relevance_score: float = 0.3
    enable_metadata_filtering: bool = True
    enable_mmr: bool = True  # Maximal Marginal Relevance for diversity
    mmr_lambda: float = 0.5


@dataclass
class GenerationConfig:
    """Configuration for response generation."""
    model: str = "gpt-4"
    max_context_tokens: int = 6000
    max_output_tokens: int = 1000
    temperature: float = 0.1
    evidence_selection_strategy: str = "relevance_weighted"
    max_evidence_chunks: int = 5
    include_source_citations: bool = True
    hallucination_check: bool = True
    confidence_threshold: float = 0.7


@dataclass
class OrchestrationConfig:
    """Configuration for query orchestration."""
    enable_query_routing: bool = True
    skip_retrieval_threshold: float = 0.8  # Skip if query is simple enough
    fallback_mode: FallbackMode = FallbackMode.CLARIFICATION
    max_retries: int = 3
    timeout_seconds: float = 30.0
    enable_query_rewriting: bool = True
    enable_query_decomposition: bool = True


@dataclass
class ObservabilityConfig:
    """Configuration for observability and monitoring."""
    enable_logging: bool = True
    log_level: str = "INFO"
    enable_metrics: bool = True
    metrics_port: int = 8000
    enable_tracing: bool = True
    trace_sample_rate: float = 0.1
    enable_feedback_collection: bool = True
    feedback_storage_path: str = "./feedback"
    log_retrieval_misses: bool = True
    log_latency_percentiles: list[float] = field(default_factory=lambda: [0.5, 0.9, 0.95, 0.99])


@dataclass
class RAGConfig:
    """Master configuration for the RAG pipeline."""
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    generation: GenerationConfig = field(default_factory=GenerationConfig)
    orchestration: OrchestrationConfig = field(default_factory=OrchestrationConfig)
    observability: ObservabilityConfig = field(default_factory=ObservabilityConfig)

    @classmethod
    def for_high_precision(cls) -> "RAGConfig":
        """Configuration optimized for precision over recall."""
        config = cls()
        config.retrieval.min_relevance_score = 0.5
        config.retrieval.rerank_top_k = 3
        config.generation.confidence_threshold = 0.8
        config.generation.hallucination_check = True
        return config

    @classmethod
    def for_high_recall(cls) -> "RAGConfig":
        """Configuration optimized for recall over precision."""
        config = cls()
        config.retrieval.top_k = 20
        config.retrieval.rerank_top_k = 10
        config.retrieval.min_relevance_score = 0.2
        config.generation.max_evidence_chunks = 8
        return config

    @classmethod
    def for_low_latency(cls) -> "RAGConfig":
        """Configuration optimized for speed."""
        config = cls()
        config.retrieval.enable_reranking = False
        config.retrieval.top_k = 5
        config.orchestration.timeout_seconds = 10.0
        config.generation.max_context_tokens = 3000
        return config
