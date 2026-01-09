"""
Reranking Module.

Reranking is critical for production RAG:
- Initial retrieval optimizes for recall (don't miss relevant docs)
- Reranking optimizes for precision (put best docs first)
"""

from abc import ABC, abstractmethod
from typing import Optional

from retrieval_app.retrieval.vector_store import SearchResult


class RerankerBase(ABC):
    """Base class for rerankers."""

    @abstractmethod
    def rerank(
        self,
        query: str,
        results: list[SearchResult],
        top_k: int = 5
    ) -> list[SearchResult]:
        """Rerank search results."""
        pass


class CrossEncoderReranker(RerankerBase):
    """
    Reranker using cross-encoder models.

    Cross-encoders are more accurate than bi-encoders because they
    see query and document together, but are slower.
    """

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model_name = model_name
        self._model = None

    @property
    def model(self):
        """Lazy load the cross-encoder model."""
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder
                self._model = CrossEncoder(self.model_name)
            except ImportError:
                raise ImportError(
                    "sentence-transformers is required for cross-encoder reranking. "
                    "Install with: pip install sentence-transformers"
                )
        return self._model

    def rerank(
        self,
        query: str,
        results: list[SearchResult],
        top_k: int = 5
    ) -> list[SearchResult]:
        """Rerank results using cross-encoder scores."""
        if not results:
            return []

        pairs = [(query, r.chunk.content) for r in results]
        scores = self.model.predict(pairs)

        for result, score in zip(results, scores):
            result.score = float(score)

        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]


class CohereReranker(RerankerBase):
    """Reranker using Cohere's rerank API."""

    def __init__(self, api_key: Optional[str] = None, model: str = "rerank-english-v2.0"):
        import os
        self.api_key = api_key or os.environ.get("COHERE_API_KEY")
        self.model = model
        self._client = None

    @property
    def client(self):
        """Lazy load Cohere client."""
        if self._client is None:
            try:
                import cohere
                self._client = cohere.Client(self.api_key)
            except ImportError:
                raise ImportError("cohere is required. Install with: pip install cohere")
        return self._client

    def rerank(
        self,
        query: str,
        results: list[SearchResult],
        top_k: int = 5
    ) -> list[SearchResult]:
        """Rerank using Cohere API."""
        if not results:
            return []

        documents = [r.chunk.content for r in results]

        response = self.client.rerank(
            query=query,
            documents=documents,
            model=self.model,
            top_n=top_k
        )

        reranked = []
        for item in response.results:
            result = results[item.index]
            result.score = item.relevance_score
            reranked.append(result)

        return reranked


class MMRReranker(RerankerBase):
    """
    Maximal Marginal Relevance reranker.

    Balances relevance with diversity to avoid returning
    near-duplicate chunks.
    """

    def __init__(self, lambda_param: float = 0.5):
        self.lambda_param = lambda_param

    def rerank(
        self,
        query: str,
        results: list[SearchResult],
        top_k: int = 5
    ) -> list[SearchResult]:
        """Rerank using MMR algorithm."""
        if not results or len(results) <= 1:
            return results[:top_k]

        import numpy as np

        embeddings = []
        for r in results:
            if r.chunk.embedding:
                embeddings.append(np.array(r.chunk.embedding))
            else:
                return results[:top_k]

        selected_indices = []
        remaining_indices = list(range(len(results)))

        first_idx = max(remaining_indices, key=lambda i: results[i].score)
        selected_indices.append(first_idx)
        remaining_indices.remove(first_idx)

        while len(selected_indices) < top_k and remaining_indices:
            best_score = float('-inf')
            best_idx = None

            for idx in remaining_indices:
                relevance = results[idx].score

                max_sim = 0.0
                for selected_idx in selected_indices:
                    sim = self._cosine_similarity(
                        embeddings[idx],
                        embeddings[selected_idx]
                    )
                    max_sim = max(max_sim, sim)

                mmr_score = (
                    self.lambda_param * relevance -
                    (1 - self.lambda_param) * max_sim
                )

                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = idx

            if best_idx is not None:
                selected_indices.append(best_idx)
                remaining_indices.remove(best_idx)
            else:
                break

        return [results[i] for i in selected_indices]

    def _cosine_similarity(self, vec1, vec2) -> float:
        """Calculate cosine similarity."""
        import numpy as np
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot_product / (norm1 * norm2)


class Reranker:
    """
    Factory class for creating rerankers.

    Usage:
        reranker = Reranker.create("cross-encoder")
        reranked = reranker.rerank(query, results, top_k=5)
    """

    @staticmethod
    def create(
        reranker_type: str = "cross-encoder",
        **kwargs
    ) -> RerankerBase:
        """Create a reranker instance."""
        if reranker_type == "cross-encoder":
            return CrossEncoderReranker(**kwargs)
        elif reranker_type == "cohere":
            return CohereReranker(**kwargs)
        elif reranker_type == "mmr":
            return MMRReranker(**kwargs)
        else:
            raise ValueError(f"Unknown reranker type: {reranker_type}")
