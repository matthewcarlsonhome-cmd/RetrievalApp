"""
RAG Pipeline Module.

The main orchestrating class that ties together all components.
"""

import time
import uuid
from dataclasses import dataclass
from typing import Optional

from retrieval_app.core.config import RAGConfig, FallbackMode
from retrieval_app.data_prep.chunker import DocumentChunker, Chunk
from retrieval_app.data_prep.embedder import EmbeddingService
from retrieval_app.data_prep.validator import DataValidator
from retrieval_app.retrieval.hybrid_retriever import HybridRetriever
from retrieval_app.retrieval.vector_store import VectorStore
from retrieval_app.generation.generator import ResponseGenerator, GenerationResult, MockLLMProvider
from retrieval_app.orchestration.router import QueryRouter, RoutingDecision
from retrieval_app.orchestration.query_processor import QueryProcessor
from retrieval_app.orchestration.fallback_handler import FallbackHandler, FallbackReason
from retrieval_app.observability.logger import RAGLogger
from retrieval_app.observability.metrics import MetricsCollector, Timer
from retrieval_app.observability.feedback import FeedbackCollector


@dataclass
class RAGResponse:
    """Complete response from the RAG pipeline."""
    query_id: str
    query: str
    answer: str
    sources: list[str]
    confidence: float
    retrieval_count: int
    tokens_used: int
    latency_ms: float
    routing_decision: str
    fallback_used: bool
    metadata: dict


class RAGPipeline:
    """
    Production-ready RAG pipeline.

    Integrates all five critical components:
    1. Data Preparation - chunking, embeddings, validation
    2. Retrieval - hybrid search, reranking, filtering
    3. Generation - prompts, token management, hallucination prevention
    4. Orchestration - routing, fallbacks, tool handoff
    5. Observability - logging, metrics, feedback
    """

    def __init__(
        self,
        config: Optional[RAGConfig] = None,
        use_mock_llm: bool = False
    ):
        self.config = config or RAGConfig()

        self.chunker = DocumentChunker(self.config.chunking)
        self.embedding_service = EmbeddingService(self.config.embedding)
        self.validator = DataValidator()

        vector_store = VectorStore.create("memory")
        self.retriever = HybridRetriever(
            config=self.config.retrieval,
            embedding_service=self.embedding_service,
            vector_store=vector_store
        )

        if use_mock_llm:
            llm = MockLLMProvider()
        else:
            llm = None
        self.generator = ResponseGenerator(
            config=self.config.generation,
            llm_provider=llm
        )

        self.router = QueryRouter(
            retrieval_confidence_threshold=self.config.retrieval.min_relevance_score
        )
        self.query_processor = QueryProcessor(
            enable_rewriting=self.config.orchestration.enable_query_rewriting,
            enable_decomposition=self.config.orchestration.enable_query_decomposition
        )
        self.fallback_handler = FallbackHandler(
            default_mode=self.config.orchestration.fallback_mode,
            direct_llm_handler=(
                lambda q: self.generator.generate_without_context(q).answer
            )
        )

        self.logger = RAGLogger(
            log_level=self.config.observability.log_level,
            structured_output=True
        )
        self.metrics = MetricsCollector(
            enable_prometheus=self.config.observability.enable_metrics
        )
        self.feedback = FeedbackCollector(
            storage_path=self.config.observability.feedback_storage_path
        )

        if self.config.observability.log_retrieval_misses:
            self.logger.set_miss_log_path("./logs/retrieval_misses.jsonl")

    def ingest_documents(
        self,
        documents: list[tuple[str, str, dict]]
    ) -> dict:
        """
        Ingest documents into the RAG system.

        Args:
            documents: List of (doc_id, text, metadata) tuples

        Returns:
            Ingestion statistics
        """
        all_chunks: list[Chunk] = []
        stats = {
            "documents_processed": 0,
            "chunks_created": 0,
            "validation_issues": 0,
            "documents_failed": []
        }

        for doc_id, text, metadata in documents:
            doc_validation = self.validator.validate_document(text, doc_id)
            if not doc_validation.is_valid:
                stats["documents_failed"].append(doc_id)
                continue

            chunks = self.chunker.chunk_document(text, doc_id, metadata)
            chunk_validation = self.validator.validate_chunks(chunks)

            if chunk_validation.warnings:
                stats["validation_issues"] += len(chunk_validation.warnings)

            valid_chunks = [
                c for c in chunks
                if not any(
                    issue.chunk_id == c.id and issue.severity.value == "error"
                    for issue in chunk_validation.issues
                )
            ]

            all_chunks.extend(valid_chunks)
            stats["documents_processed"] += 1

        if all_chunks:
            self.retriever.index_chunks(all_chunks)
            stats["chunks_created"] = len(all_chunks)

        return stats

    def query(
        self,
        query: str,
        metadata_filter: Optional[dict] = None
    ) -> RAGResponse:
        """
        Process a query through the full RAG pipeline.

        Args:
            query: User's question
            metadata_filter: Optional metadata constraints

        Returns:
            RAGResponse with answer and metadata
        """
        query_id = str(uuid.uuid4())[:8]
        start_time = time.perf_counter()

        self.metrics.record_query()

        processed = self.query_processor.process(query)

        route = self.router.route(processed.rewritten_query)

        fallback_used = False
        if route.decision == RoutingDecision.SKIP_RETRIEVAL:
            gen_result = self.generator.generate_without_context(query)
            fallback_used = True

        elif route.decision == RoutingDecision.REQUEST_CLARIFICATION:
            fallback_result = self.fallback_handler.handle(
                FallbackReason.LOW_CONFIDENCE,
                query
            )
            return self._build_response(
                query_id=query_id,
                query=query,
                answer=fallback_result.response or "",
                sources=[],
                confidence=0.5,
                retrieval_count=0,
                tokens_used=0,
                start_time=start_time,
                routing_decision=route.decision.value,
                fallback_used=True
            )

        elif route.decision == RoutingDecision.ESCALATE_TO_HUMAN:
            fallback_result = self.fallback_handler.handle(
                FallbackReason.OUT_OF_SCOPE,
                query
            )
            return self._build_response(
                query_id=query_id,
                query=query,
                answer=fallback_result.response or "",
                sources=[],
                confidence=0.0,
                retrieval_count=0,
                tokens_used=0,
                start_time=start_time,
                routing_decision=route.decision.value,
                fallback_used=True
            )

        else:
            with Timer(self.metrics, "retrieval"):
                if processed.extracted_filters:
                    combined_filter = {**(metadata_filter or {}), **processed.extracted_filters}
                else:
                    combined_filter = metadata_filter

                retrieval_result = self.retriever.retrieve(
                    query=processed.rewritten_query,
                    metadata_filter=combined_filter
                )

            scores = [r.score for r in retrieval_result.results]
            self.logger.log_retrieval(
                query_id=query_id,
                query=query,
                results_count=len(retrieval_result.results),
                scores=scores,
                latency_ms=(time.perf_counter() - start_time) * 1000,
                retrieval_mode=retrieval_result.mode_used.value,
                metadata_filter=combined_filter,
                reranked=retrieval_result.reranked
            )

            if not retrieval_result.results or (
                scores and max(scores) < self.config.retrieval.min_relevance_score
            ):
                self.metrics.record_miss()
                self.logger.log_miss(
                    query_id=query_id,
                    query=query,
                    reason="no_relevant_results",
                    top_score=max(scores) if scores else 0.0,
                    suggested_action="expand_knowledge_base"
                )

                fallback_result = self.fallback_handler.handle(
                    FallbackReason.NO_RESULTS,
                    query,
                    mode_override=FallbackMode.DIRECT_LLM
                )
                gen_result = GenerationResult(
                    answer=fallback_result.response or "",
                    sources_used=[],
                    confidence=0.3,
                    tokens_used=0
                )
                fallback_used = True

            else:
                with Timer(self.metrics, "generation"):
                    gen_result = self.generator.generate(
                        question=query,
                        retrieval_results=retrieval_result.results
                    )

                for score in scores:
                    self.metrics.record_relevance_score(score)

        self.metrics.record_confidence(gen_result.confidence)
        self.metrics.record_tokens(gen_result.tokens_used)

        if fallback_used:
            self.metrics.record_fallback()
            self.logger.log_fallback(
                query_id=query_id,
                fallback_mode=self.config.orchestration.fallback_mode.value,
                reason=route.decision.value,
                handled=True
            )

        self.logger.log_generation(
            query_id=query_id,
            tokens_used=gen_result.tokens_used,
            confidence=gen_result.confidence,
            latency_ms=(time.perf_counter() - start_time) * 1000,
            sources_count=len(gen_result.sources_used),
            hallucination_check=gen_result.hallucination_check_passed
        )

        return self._build_response(
            query_id=query_id,
            query=query,
            answer=gen_result.answer,
            sources=gen_result.sources_used,
            confidence=gen_result.confidence,
            retrieval_count=len(retrieval_result.results) if 'retrieval_result' in locals() else 0,
            tokens_used=gen_result.tokens_used,
            start_time=start_time,
            routing_decision=route.decision.value,
            fallback_used=fallback_used
        )

    def _build_response(
        self,
        query_id: str,
        query: str,
        answer: str,
        sources: list[str],
        confidence: float,
        retrieval_count: int,
        tokens_used: int,
        start_time: float,
        routing_decision: str,
        fallback_used: bool
    ) -> RAGResponse:
        """Build a RAGResponse object."""
        latency_ms = (time.perf_counter() - start_time) * 1000
        self.metrics.record_e2e_latency(latency_ms)

        return RAGResponse(
            query_id=query_id,
            query=query,
            answer=answer,
            sources=sources,
            confidence=confidence,
            retrieval_count=retrieval_count,
            tokens_used=tokens_used,
            latency_ms=latency_ms,
            routing_decision=routing_decision,
            fallback_used=fallback_used,
            metadata={}
        )

    def record_feedback(
        self,
        query_id: str,
        query: str,
        answer: str,
        is_positive: bool,
        comment: Optional[str] = None
    ) -> None:
        """Record user feedback for a response."""
        self.feedback.record_thumbs(
            query_id=query_id,
            query=query,
            answer=answer,
            is_positive=is_positive,
            comment=comment
        )

    def get_metrics_summary(self) -> dict:
        """Get current metrics summary."""
        summary = self.metrics.get_summary()
        return {
            "total_queries": summary.total_queries,
            "retrieval_latency_p50": summary.retrieval_latency.p50_ms,
            "retrieval_latency_p95": summary.retrieval_latency.p95_ms,
            "generation_latency_p50": summary.generation_latency.p50_ms,
            "generation_latency_p95": summary.generation_latency.p95_ms,
            "mean_confidence": summary.quality.mean_confidence,
            "miss_rate": summary.quality.miss_rate,
            "fallback_rate": summary.quality.fallback_rate,
            "tokens_used": summary.tokens_used,
            "errors": summary.error_count
        }
