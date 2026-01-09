"""
Metrics Collection Module.

Tracks key performance indicators for RAG systems.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
from collections import deque
import statistics


@dataclass
class LatencyStats:
    """Latency statistics."""
    count: int
    mean_ms: float
    p50_ms: float
    p90_ms: float
    p95_ms: float
    p99_ms: float


@dataclass
class QualityStats:
    """Quality statistics."""
    mean_confidence: float
    mean_relevance_score: float
    miss_rate: float
    fallback_rate: float


@dataclass
class MetricsSummary:
    """Summary of all metrics."""
    period_start: str
    period_end: str
    total_queries: int
    retrieval_latency: LatencyStats
    generation_latency: LatencyStats
    quality: QualityStats
    tokens_used: int
    error_count: int


class MetricsCollector:
    """
    Collects and aggregates metrics for RAG pipeline monitoring.

    Key metrics:
    - Latency (retrieval, generation, end-to-end)
    - Quality (confidence, relevance scores)
    - Errors and fallbacks
    - Token usage
    """

    def __init__(
        self,
        window_size: int = 1000,
        enable_prometheus: bool = False,
        prometheus_port: int = 8000
    ):
        self.window_size = window_size

        self._retrieval_latencies: deque[float] = deque(maxlen=window_size)
        self._generation_latencies: deque[float] = deque(maxlen=window_size)
        self._e2e_latencies: deque[float] = deque(maxlen=window_size)

        self._confidence_scores: deque[float] = deque(maxlen=window_size)
        self._relevance_scores: deque[float] = deque(maxlen=window_size)

        self._query_count = 0
        self._miss_count = 0
        self._fallback_count = 0
        self._error_count = 0
        self._tokens_used = 0

        self._period_start = datetime.utcnow()

        self._prometheus_metrics = None
        if enable_prometheus:
            self._setup_prometheus(prometheus_port)

    def _setup_prometheus(self, port: int) -> None:
        """Setup Prometheus metrics endpoint."""
        try:
            from prometheus_client import (
                Counter, Histogram, Gauge, start_http_server
            )

            self._prometheus_metrics = {
                "queries_total": Counter(
                    "rag_queries_total",
                    "Total number of queries processed"
                ),
                "retrieval_latency": Histogram(
                    "rag_retrieval_latency_seconds",
                    "Retrieval latency in seconds",
                    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
                ),
                "generation_latency": Histogram(
                    "rag_generation_latency_seconds",
                    "Generation latency in seconds",
                    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
                ),
                "confidence_score": Gauge(
                    "rag_confidence_score",
                    "Current average confidence score"
                ),
                "miss_rate": Gauge(
                    "rag_miss_rate",
                    "Current retrieval miss rate"
                ),
                "tokens_used": Counter(
                    "rag_tokens_total",
                    "Total tokens used"
                ),
                "errors_total": Counter(
                    "rag_errors_total",
                    "Total errors"
                ),
            }

            start_http_server(port)

        except ImportError:
            self._prometheus_metrics = None

    def record_query(self) -> None:
        """Record a query."""
        self._query_count += 1
        if self._prometheus_metrics:
            self._prometheus_metrics["queries_total"].inc()

    def record_retrieval_latency(self, latency_ms: float) -> None:
        """Record retrieval latency."""
        self._retrieval_latencies.append(latency_ms)
        if self._prometheus_metrics:
            self._prometheus_metrics["retrieval_latency"].observe(latency_ms / 1000)

    def record_generation_latency(self, latency_ms: float) -> None:
        """Record generation latency."""
        self._generation_latencies.append(latency_ms)
        if self._prometheus_metrics:
            self._prometheus_metrics["generation_latency"].observe(latency_ms / 1000)

    def record_e2e_latency(self, latency_ms: float) -> None:
        """Record end-to-end latency."""
        self._e2e_latencies.append(latency_ms)

    def record_confidence(self, confidence: float) -> None:
        """Record confidence score."""
        self._confidence_scores.append(confidence)
        if self._prometheus_metrics:
            avg = statistics.mean(self._confidence_scores) if self._confidence_scores else 0
            self._prometheus_metrics["confidence_score"].set(avg)

    def record_relevance_score(self, score: float) -> None:
        """Record relevance score."""
        self._relevance_scores.append(score)

    def record_miss(self) -> None:
        """Record a retrieval miss."""
        self._miss_count += 1
        if self._prometheus_metrics:
            miss_rate = self._miss_count / max(self._query_count, 1)
            self._prometheus_metrics["miss_rate"].set(miss_rate)

    def record_fallback(self) -> None:
        """Record a fallback event."""
        self._fallback_count += 1

    def record_error(self) -> None:
        """Record an error."""
        self._error_count += 1
        if self._prometheus_metrics:
            self._prometheus_metrics["errors_total"].inc()

    def record_tokens(self, tokens: int) -> None:
        """Record token usage."""
        self._tokens_used += tokens
        if self._prometheus_metrics:
            self._prometheus_metrics["tokens_used"].inc(tokens)

    def get_latency_stats(self, latencies: deque) -> LatencyStats:
        """Calculate latency statistics."""
        if not latencies:
            return LatencyStats(0, 0, 0, 0, 0, 0)

        sorted_latencies = sorted(latencies)
        count = len(sorted_latencies)

        return LatencyStats(
            count=count,
            mean_ms=statistics.mean(sorted_latencies),
            p50_ms=sorted_latencies[int(count * 0.5)],
            p90_ms=sorted_latencies[int(count * 0.9)] if count >= 10 else sorted_latencies[-1],
            p95_ms=sorted_latencies[int(count * 0.95)] if count >= 20 else sorted_latencies[-1],
            p99_ms=sorted_latencies[int(count * 0.99)] if count >= 100 else sorted_latencies[-1]
        )

    def get_quality_stats(self) -> QualityStats:
        """Calculate quality statistics."""
        return QualityStats(
            mean_confidence=(
                statistics.mean(self._confidence_scores)
                if self._confidence_scores else 0.0
            ),
            mean_relevance_score=(
                statistics.mean(self._relevance_scores)
                if self._relevance_scores else 0.0
            ),
            miss_rate=self._miss_count / max(self._query_count, 1),
            fallback_rate=self._fallback_count / max(self._query_count, 1)
        )

    def get_summary(self) -> MetricsSummary:
        """Get a summary of all metrics."""
        now = datetime.utcnow()

        return MetricsSummary(
            period_start=self._period_start.isoformat(),
            period_end=now.isoformat(),
            total_queries=self._query_count,
            retrieval_latency=self.get_latency_stats(self._retrieval_latencies),
            generation_latency=self.get_latency_stats(self._generation_latencies),
            quality=self.get_quality_stats(),
            tokens_used=self._tokens_used,
            error_count=self._error_count
        )

    def reset(self) -> None:
        """Reset all metrics."""
        self._retrieval_latencies.clear()
        self._generation_latencies.clear()
        self._e2e_latencies.clear()
        self._confidence_scores.clear()
        self._relevance_scores.clear()
        self._query_count = 0
        self._miss_count = 0
        self._fallback_count = 0
        self._error_count = 0
        self._tokens_used = 0
        self._period_start = datetime.utcnow()


class Timer:
    """Context manager for timing operations."""

    def __init__(self, metrics: MetricsCollector, metric_type: str):
        self.metrics = metrics
        self.metric_type = metric_type
        self.start_time: Optional[float] = None

    def __enter__(self) -> "Timer":
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, *args) -> None:
        if self.start_time:
            elapsed_ms = (time.perf_counter() - self.start_time) * 1000
            if self.metric_type == "retrieval":
                self.metrics.record_retrieval_latency(elapsed_ms)
            elif self.metric_type == "generation":
                self.metrics.record_generation_latency(elapsed_ms)
            elif self.metric_type == "e2e":
                self.metrics.record_e2e_latency(elapsed_ms)
