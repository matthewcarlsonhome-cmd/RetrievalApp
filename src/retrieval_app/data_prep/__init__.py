"""
Data Preparation Module.

Handles the critical foundation of any RAG system:
- Document chunking with multiple strategies
- Embedding generation and caching
- Data validation and quality checks
- Truth set management for evaluation
"""

from retrieval_app.data_prep.chunker import DocumentChunker, Chunk
from retrieval_app.data_prep.embedder import EmbeddingService
from retrieval_app.data_prep.validator import DataValidator
from retrieval_app.data_prep.truth_sets import TruthSetManager

__all__ = ["DocumentChunker", "Chunk", "EmbeddingService", "DataValidator", "TruthSetManager"]
