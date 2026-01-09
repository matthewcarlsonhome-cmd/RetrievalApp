"""
Embedding Service Module.

Handles embedding generation with caching, batching, and multiple provider support.
"""

import hashlib
import json
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
import numpy as np

from retrieval_app.core.config import EmbeddingConfig
from retrieval_app.data_prep.chunker import Chunk


class EmbeddingProvider(ABC):
    """Base class for embedding providers."""

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the embedding dimension."""
        pass


class SentenceTransformerProvider(EmbeddingProvider):
    """Embedding provider using sentence-transformers."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None
        self._dimension: Optional[int] = None

    @property
    def model(self):
        """Lazy load the model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
                self._dimension = self._model.get_sentence_embedding_dimension()
            except ImportError:
                raise ImportError(
                    "sentence-transformers is required. Install with: "
                    "pip install sentence-transformers"
                )
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings using sentence-transformers."""
        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        return embeddings.tolist()

    @property
    def dimension(self) -> int:
        if self._dimension is None:
            _ = self.model
        return self._dimension or 384


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """Embedding provider using OpenAI API."""

    def __init__(self, model: str = "text-embedding-3-small", api_key: Optional[str] = None):
        self.model = model
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self._client = None
        self._dimensions = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
        }

    @property
    def client(self):
        """Lazy load the OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("openai is required. Install with: pip install openai")
        return self._client

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings using OpenAI API."""
        response = self.client.embeddings.create(
            input=texts,
            model=self.model
        )
        return [item.embedding for item in response.data]

    @property
    def dimension(self) -> int:
        return self._dimensions.get(self.model, 1536)


class EmbeddingCache:
    """Cache for embeddings to avoid redundant computation."""

    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = Path(cache_dir) if cache_dir else Path(".embedding_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._memory_cache: dict[str, list[float]] = {}

    def _get_cache_key(self, text: str, model_name: str) -> str:
        """Generate a cache key for a text/model combination."""
        content = f"{model_name}:{text}"
        return hashlib.sha256(content.encode()).hexdigest()

    def get(self, text: str, model_name: str) -> Optional[list[float]]:
        """Retrieve embedding from cache."""
        key = self._get_cache_key(text, model_name)

        if key in self._memory_cache:
            return self._memory_cache[key]

        cache_file = self.cache_dir / f"{key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, "r") as f:
                    embedding = json.load(f)
                self._memory_cache[key] = embedding
                return embedding
            except (json.JSONDecodeError, IOError):
                pass

        return None

    def set(self, text: str, model_name: str, embedding: list[float]) -> None:
        """Store embedding in cache."""
        key = self._get_cache_key(text, model_name)
        self._memory_cache[key] = embedding

        cache_file = self.cache_dir / f"{key}.json"
        try:
            with open(cache_file, "w") as f:
                json.dump(embedding, f)
        except IOError:
            pass

    def clear(self) -> None:
        """Clear all cached embeddings."""
        self._memory_cache.clear()
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()


class EmbeddingService:
    """
    Main embedding service with caching and batching support.

    Usage:
        service = EmbeddingService(config)
        chunks_with_embeddings = service.embed_chunks(chunks)
    """

    def __init__(
        self,
        config: EmbeddingConfig,
        provider: Optional[EmbeddingProvider] = None
    ):
        self.config = config
        self.provider = provider or SentenceTransformerProvider(config.model_name)
        self.cache = EmbeddingCache(config.cache_dir) if config.cache_embeddings else None

    @property
    def dimension(self) -> int:
        """Return the embedding dimension."""
        return self.provider.dimension

    def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        if self.cache:
            cached = self.cache.get(text, self.config.model_name)
            if cached is not None:
                return cached

        embeddings = self.provider.embed([text])
        embedding = embeddings[0]

        if self.config.normalize:
            embedding = self._normalize(embedding)

        if self.cache:
            self.cache.set(text, self.config.model_name, embedding)

        return embedding

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts with batching."""
        results: list[Optional[list[float]]] = [None] * len(texts)
        texts_to_embed: list[tuple[int, str]] = []

        if self.cache:
            for i, text in enumerate(texts):
                cached = self.cache.get(text, self.config.model_name)
                if cached is not None:
                    results[i] = cached
                else:
                    texts_to_embed.append((i, text))
        else:
            texts_to_embed = list(enumerate(texts))

        if texts_to_embed:
            for batch_start in range(0, len(texts_to_embed), self.config.batch_size):
                batch = texts_to_embed[batch_start:batch_start + self.config.batch_size]
                batch_texts = [t[1] for t in batch]

                embeddings = self.provider.embed(batch_texts)

                for (idx, text), embedding in zip(batch, embeddings):
                    if self.config.normalize:
                        embedding = self._normalize(embedding)
                    results[idx] = embedding
                    if self.cache:
                        self.cache.set(text, self.config.model_name, embedding)

        return [r for r in results if r is not None]

    def embed_chunks(self, chunks: list[Chunk]) -> list[Chunk]:
        """Generate embeddings for chunks and attach to chunk objects."""
        texts = [chunk.content for chunk in chunks]
        embeddings = self.embed_texts(texts)

        for chunk, embedding in zip(chunks, embeddings):
            chunk.embedding = embedding

        return chunks

    def _normalize(self, embedding: list[float]) -> list[float]:
        """Normalize embedding to unit length."""
        arr = np.array(embedding)
        norm = np.linalg.norm(arr)
        if norm > 0:
            arr = arr / norm
        return arr.tolist()

    def compute_similarity(
        self,
        embedding1: list[float],
        embedding2: list[float]
    ) -> float:
        """Compute cosine similarity between two embeddings."""
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        return float(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2)))
