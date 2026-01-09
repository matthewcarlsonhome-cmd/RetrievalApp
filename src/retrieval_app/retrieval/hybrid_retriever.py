"""
Hybrid Retriever Module.

Combines semantic and lexical search for better retrieval quality.

"Retrieval becomes a blend of semantic + lexical matching, metadata filters,
reranking strategies and tradeoffs between precision and recall."
"""

from dataclasses import dataclass
from typing import Optional

from retrieval_app.core.config import RetrievalConfig, RetrievalMode
from retrieval_app.data_prep.chunker import Chunk
from retrieval_app.data_prep.embedder import EmbeddingService
from retrieval_app.retrieval.vector_store import VectorStore, VectorStoreBase, SearchResult
from retrieval_app.retrieval.lexical_search import LexicalSearcher
from retrieval_app.retrieval.reranker import Reranker, RerankerBase, MMRReranker


@dataclass
class RetrievalResult:
    """Complete result from hybrid retrieval."""
    results: list[SearchResult]
    query: str
    mode_used: RetrievalMode
    semantic_results_count: int
    lexical_results_count: int
    reranked: bool
    metadata_filter_applied: bool


class HybridRetriever:
    """
    Production-ready hybrid retriever combining multiple strategies.

    Features:
    - Hybrid search (semantic + lexical)
    - Configurable weights between search types
    - Metadata filtering
    - Multiple reranking options
    - MMR for diversity
    - Score normalization and fusion
    """

    def __init__(
        self,
        config: RetrievalConfig,
        embedding_service: EmbeddingService,
        vector_store: Optional[VectorStoreBase] = None,
        reranker: Optional[RerankerBase] = None
    ):
        self.config = config
        self.embedding_service = embedding_service
        self.vector_store = vector_store or VectorStore.create("memory")
        self.lexical_searcher = LexicalSearcher()

        if config.enable_reranking and reranker is None:
            try:
                self.reranker = Reranker.create(
                    "cross-encoder",
                    model_name=config.reranker_model
                )
            except ImportError:
                self.reranker = None
        else:
            self.reranker = reranker

        self.mmr_reranker = MMRReranker(lambda_param=config.mmr_lambda)

    def index_chunks(self, chunks: list[Chunk]) -> None:
        """Index chunks for both semantic and lexical search."""
        chunks_with_embeddings = self.embedding_service.embed_chunks(chunks)
        self.vector_store.add_chunks(chunks_with_embeddings)
        self.lexical_searcher.index_chunks(chunks_with_embeddings)

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        metadata_filter: Optional[dict] = None,
        mode_override: Optional[RetrievalMode] = None
    ) -> RetrievalResult:
        """
        Retrieve relevant chunks for a query.

        Args:
            query: The search query
            top_k: Number of results to return (defaults to config)
            metadata_filter: Optional metadata constraints
            mode_override: Override the configured retrieval mode

        Returns:
            RetrievalResult with ranked chunks and metadata
        """
        top_k = top_k or self.config.top_k
        mode = mode_override or self.config.mode

        semantic_results: list[SearchResult] = []
        lexical_results: list[SearchResult] = []

        if mode in (RetrievalMode.SEMANTIC_ONLY, RetrievalMode.HYBRID):
            query_embedding = self.embedding_service.embed_text(query)
            semantic_results = self.vector_store.search(
                query_embedding=query_embedding,
                top_k=top_k * 2,
                metadata_filter=metadata_filter
            )

        if mode in (RetrievalMode.LEXICAL_ONLY, RetrievalMode.HYBRID):
            lexical_results = self.lexical_searcher.search(
                query=query,
                top_k=top_k * 2,
                metadata_filter=metadata_filter
            )

        if mode == RetrievalMode.HYBRID:
            combined = self._fuse_results(
                semantic_results,
                lexical_results,
                self.config.semantic_weight,
                self.config.lexical_weight
            )
        elif mode == RetrievalMode.SEMANTIC_ONLY:
            combined = semantic_results
        else:
            combined = lexical_results

        combined = [r for r in combined if r.score >= self.config.min_relevance_score]

        reranked = False
        if self.config.enable_reranking and self.reranker and len(combined) > 0:
            combined = self.reranker.rerank(
                query=query,
                results=combined,
                top_k=self.config.rerank_top_k
            )
            reranked = True

        if self.config.enable_mmr and len(combined) > 1:
            combined = self.mmr_reranker.rerank(
                query=query,
                results=combined,
                top_k=top_k
            )

        combined = combined[:top_k]

        return RetrievalResult(
            results=combined,
            query=query,
            mode_used=mode,
            semantic_results_count=len(semantic_results),
            lexical_results_count=len(lexical_results),
            reranked=reranked,
            metadata_filter_applied=metadata_filter is not None
        )

    def _fuse_results(
        self,
        semantic_results: list[SearchResult],
        lexical_results: list[SearchResult],
        semantic_weight: float,
        lexical_weight: float
    ) -> list[SearchResult]:
        """
        Fuse semantic and lexical results using Reciprocal Rank Fusion (RRF).

        RRF is robust to score distribution differences between retrieval methods.
        """
        k = 60
        chunk_scores: dict[str, float] = {}
        chunk_map: dict[str, SearchResult] = {}

        for rank, result in enumerate(semantic_results):
            chunk_id = result.chunk.id
            rrf_score = semantic_weight / (k + rank + 1)
            chunk_scores[chunk_id] = chunk_scores.get(chunk_id, 0) + rrf_score
            if chunk_id not in chunk_map:
                chunk_map[chunk_id] = result

        for rank, result in enumerate(lexical_results):
            chunk_id = result.chunk.id
            rrf_score = lexical_weight / (k + rank + 1)
            chunk_scores[chunk_id] = chunk_scores.get(chunk_id, 0) + rrf_score
            if chunk_id not in chunk_map:
                chunk_map[chunk_id] = result

        sorted_chunks = sorted(chunk_scores.items(), key=lambda x: x[1], reverse=True)

        fused_results = []
        for chunk_id, score in sorted_chunks:
            result = chunk_map[chunk_id]
            result.score = score
            result.search_type = "hybrid"
            fused_results.append(result)

        return fused_results

    def get_chunk_ids(self, query: str, top_k: int = 10) -> list[str]:
        """Convenience method returning just chunk IDs (for truth set evaluation)."""
        result = self.retrieve(query, top_k=top_k)
        return [r.chunk.id for r in result.results]
