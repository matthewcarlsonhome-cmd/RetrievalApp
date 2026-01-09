"""
Production-ready RAG (Retrieval-Augmented Generation) System.

This package provides a robust implementation addressing the five critical areas
of production RAG systems:

1. Data Preparation - Chunking, embeddings, and validation
2. Retrieval - Hybrid search, reranking, and metadata filtering
3. Generation - Token management, prompt structuring, and hallucination prevention
4. Orchestration - Query routing, fallbacks, and tool handoff
5. Observability - Logging, metrics, and feedback loops
"""

from retrieval_app.core.pipeline import RAGPipeline
from retrieval_app.core.config import RAGConfig

__version__ = "0.1.0"
__all__ = ["RAGPipeline", "RAGConfig"]
