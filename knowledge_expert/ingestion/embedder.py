"""
Embedding generation for semantic search.
Uses sentence-transformers for local embedding generation.
"""

import logging
from typing import List, Optional
import numpy as np

from ..config import config

logger = logging.getLogger(__name__)

# Global embedding model (lazy loaded)
_embedding_model = None


def get_embedding_model():
    """Get or load the embedding model."""
    global _embedding_model

    if _embedding_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading embedding model: {config.EMBEDDING_MODEL}")
            _embedding_model = SentenceTransformer(config.EMBEDDING_MODEL)
            logger.info("Embedding model loaded successfully")
        except ImportError:
            logger.error("sentence-transformers not installed. Run: pip install sentence-transformers")
            raise ImportError("sentence-transformers is required for embeddings")

    return _embedding_model


class EmbeddingGenerator:
    """Generate embeddings for text."""

    def __init__(self, model_name: str = None):
        self.model_name = model_name or config.EMBEDDING_MODEL
        self._model = None

    @property
    def model(self):
        """Lazy load the model."""
        if self._model is None:
            self._model = get_embedding_model()
        return self._model

    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        return self.model.get_sentence_embedding_dimension()

    def embed(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """
        Generate embeddings for a list of texts.

        Args:
            texts: List of text strings
            batch_size: Batch size for encoding

        Returns:
            numpy array of shape (len(texts), embedding_dim)
        """
        if not texts:
            return np.array([])

        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=len(texts) > 100,
            convert_to_numpy=True
        )

        return embeddings

    def embed_single(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text.

        Args:
            text: Text string

        Returns:
            numpy array of shape (embedding_dim,)
        """
        return self.model.encode(text, convert_to_numpy=True)

    def embed_query(self, query: str) -> np.ndarray:
        """
        Generate embedding for a query.
        May use different encoding for queries vs documents.

        Args:
            query: Query string

        Returns:
            numpy array of shape (embedding_dim,)
        """
        # Some models have separate query encoding
        # For now, use the same encoding
        return self.embed_single(query)


def is_embedding_available() -> bool:
    """Check if embedding model is available."""
    try:
        from sentence_transformers import SentenceTransformer
        return True
    except ImportError:
        return False
