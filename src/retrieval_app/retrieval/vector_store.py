"""
Vector Store Module.

Manages embedding storage and semantic search.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import numpy as np

from retrieval_app.data_prep.chunker import Chunk


@dataclass
class SearchResult:
    """Result from a search operation."""
    chunk: Chunk
    score: float
    search_type: str = "semantic"


class VectorStoreBase(ABC):
    """Base class for vector stores."""

    @abstractmethod
    def add_chunks(self, chunks: list[Chunk]) -> None:
        """Add chunks to the vector store."""
        pass

    @abstractmethod
    def search(
        self,
        query_embedding: list[float],
        top_k: int = 10,
        metadata_filter: Optional[dict] = None
    ) -> list[SearchResult]:
        """Search for similar chunks."""
        pass

    @abstractmethod
    def delete(self, chunk_ids: list[str]) -> None:
        """Delete chunks from the store."""
        pass


class InMemoryVectorStore(VectorStoreBase):
    """Simple in-memory vector store for development and testing."""

    def __init__(self):
        self._chunks: dict[str, Chunk] = {}
        self._embeddings: dict[str, np.ndarray] = {}

    def add_chunks(self, chunks: list[Chunk]) -> None:
        """Add chunks to the in-memory store."""
        for chunk in chunks:
            if chunk.embedding is None:
                raise ValueError(f"Chunk {chunk.id} has no embedding")
            self._chunks[chunk.id] = chunk
            self._embeddings[chunk.id] = np.array(chunk.embedding)

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 10,
        metadata_filter: Optional[dict] = None
    ) -> list[SearchResult]:
        """Search using cosine similarity."""
        query_vec = np.array(query_embedding)

        results = []
        for chunk_id, chunk in self._chunks.items():
            if metadata_filter:
                if not self._matches_filter(chunk.metadata, metadata_filter):
                    continue

            chunk_vec = self._embeddings[chunk_id]
            similarity = self._cosine_similarity(query_vec, chunk_vec)

            results.append(SearchResult(
                chunk=chunk,
                score=float(similarity),
                search_type="semantic"
            ))

        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]

    def delete(self, chunk_ids: list[str]) -> None:
        """Delete chunks from the store."""
        for chunk_id in chunk_ids:
            self._chunks.pop(chunk_id, None)
            self._embeddings.pop(chunk_id, None)

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity."""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot_product / (norm1 * norm2)

    def _matches_filter(self, metadata: dict, filter_dict: dict) -> bool:
        """Check if metadata matches the filter criteria."""
        for key, value in filter_dict.items():
            if key not in metadata:
                return False
            if isinstance(value, dict):
                if "$eq" in value and metadata[key] != value["$eq"]:
                    return False
                if "$ne" in value and metadata[key] == value["$ne"]:
                    return False
                if "$in" in value and metadata[key] not in value["$in"]:
                    return False
                if "$gt" in value and not metadata[key] > value["$gt"]:
                    return False
                if "$gte" in value and not metadata[key] >= value["$gte"]:
                    return False
                if "$lt" in value and not metadata[key] < value["$lt"]:
                    return False
                if "$lte" in value and not metadata[key] <= value["$lte"]:
                    return False
            elif metadata[key] != value:
                return False
        return True

    def get_all_chunks(self) -> list[Chunk]:
        """Get all stored chunks."""
        return list(self._chunks.values())

    def get_chunk(self, chunk_id: str) -> Optional[Chunk]:
        """Get a specific chunk by ID."""
        return self._chunks.get(chunk_id)


class ChromaVectorStore(VectorStoreBase):
    """Vector store using ChromaDB for persistence."""

    def __init__(
        self,
        collection_name: str = "rag_chunks",
        persist_directory: Optional[str] = None
    ):
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self._client = None
        self._collection = None
        self._chunk_cache: dict[str, Chunk] = {}

    @property
    def client(self):
        """Lazy load ChromaDB client."""
        if self._client is None:
            try:
                import chromadb
                if self.persist_directory:
                    self._client = chromadb.PersistentClient(path=self.persist_directory)
                else:
                    self._client = chromadb.Client()
            except ImportError:
                raise ImportError("chromadb is required. Install with: pip install chromadb")
        return self._client

    @property
    def collection(self):
        """Get or create the collection."""
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
        return self._collection

    def add_chunks(self, chunks: list[Chunk]) -> None:
        """Add chunks to ChromaDB."""
        ids = []
        embeddings = []
        documents = []
        metadatas = []

        for chunk in chunks:
            if chunk.embedding is None:
                raise ValueError(f"Chunk {chunk.id} has no embedding")

            ids.append(chunk.id)
            embeddings.append(chunk.embedding)
            documents.append(chunk.content)

            safe_metadata = {}
            for k, v in chunk.metadata.items():
                if isinstance(v, (str, int, float, bool)):
                    safe_metadata[k] = v
            safe_metadata["document_id"] = chunk.document_id
            safe_metadata["chunk_index"] = chunk.chunk_index
            metadatas.append(safe_metadata)

            self._chunk_cache[chunk.id] = chunk

        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 10,
        metadata_filter: Optional[dict] = None
    ) -> list[SearchResult]:
        """Search ChromaDB for similar chunks."""
        where = None
        if metadata_filter:
            where = self._convert_filter(metadata_filter)

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"]
        )

        search_results = []
        if results["ids"] and results["ids"][0]:
            for i, chunk_id in enumerate(results["ids"][0]):
                distance = results["distances"][0][i] if results["distances"] else 0
                score = 1 - distance

                if chunk_id in self._chunk_cache:
                    chunk = self._chunk_cache[chunk_id]
                else:
                    chunk = Chunk(
                        id=chunk_id,
                        content=results["documents"][0][i],
                        document_id=results["metadatas"][0][i].get("document_id", ""),
                        chunk_index=results["metadatas"][0][i].get("chunk_index", 0),
                        start_char=0,
                        end_char=len(results["documents"][0][i]),
                        metadata=results["metadatas"][0][i]
                    )

                search_results.append(SearchResult(
                    chunk=chunk,
                    score=score,
                    search_type="semantic"
                ))

        return search_results

    def delete(self, chunk_ids: list[str]) -> None:
        """Delete chunks from ChromaDB."""
        self.collection.delete(ids=chunk_ids)
        for chunk_id in chunk_ids:
            self._chunk_cache.pop(chunk_id, None)

    def _convert_filter(self, metadata_filter: dict) -> dict:
        """Convert our filter format to ChromaDB's where clause."""
        return metadata_filter


class VectorStore:
    """
    Factory class for creating vector stores.

    Usage:
        store = VectorStore.create("chroma", persist_directory="./data")
        store.add_chunks(chunks)
        results = store.search(query_embedding, top_k=10)
    """

    @staticmethod
    def create(
        store_type: str = "memory",
        **kwargs
    ) -> VectorStoreBase:
        """Create a vector store instance."""
        if store_type == "memory":
            return InMemoryVectorStore()
        elif store_type == "chroma":
            return ChromaVectorStore(**kwargs)
        else:
            raise ValueError(f"Unknown store type: {store_type}")
