"""
Retrieval Module.

Implements hybrid search combining:
- Semantic (dense) retrieval using embeddings
- Lexical (sparse) retrieval using BM25
- Metadata filtering
- Reranking for precision
- MMR for diversity
"""

from retrieval_app.retrieval.hybrid_retriever import HybridRetriever
from retrieval_app.retrieval.reranker import Reranker
from retrieval_app.retrieval.vector_store import VectorStore
from retrieval_app.retrieval.lexical_search import LexicalSearcher

__all__ = ["HybridRetriever", "Reranker", "VectorStore", "LexicalSearcher"]
