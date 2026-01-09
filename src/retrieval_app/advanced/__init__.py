"""
Advanced RAG Features Module.

This module contains production-grade innovations that go beyond standard RAG:

1. AdaptiveRetriever - Dynamically adjusts retrieval parameters based on query
2. SemanticCache - Caches not just exact queries but semantically similar ones
3. AutoTuner - Learns optimal parameters from query performance data
4. ExplainableRetrieval - Shows WHY results were retrieved
5. BulkProcessor - High-throughput async ingestion with progress tracking
6. ContextCompressor - Reduces token usage while preserving information
7. QueryAnalytics - Deep insights into query patterns and system performance

These features represent patterns from leading retrieval systems at scale.
"""

from retrieval_app.advanced.adaptive_retriever import AdaptiveRetriever
from retrieval_app.advanced.semantic_cache import SemanticCache
from retrieval_app.advanced.auto_tuner import AutoTuner
from retrieval_app.advanced.explainable import ExplainableRetrieval
from retrieval_app.advanced.bulk_processor import BulkProcessor
from retrieval_app.advanced.analytics import QueryAnalytics

__all__ = [
    "AdaptiveRetriever",
    "SemanticCache",
    "AutoTuner",
    "ExplainableRetrieval",
    "BulkProcessor",
    "QueryAnalytics",
]
