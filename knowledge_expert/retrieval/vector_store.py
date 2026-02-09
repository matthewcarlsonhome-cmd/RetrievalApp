"""
Vector store using ChromaDB for embedding storage and retrieval.
Embedded mode - no external service required.
"""

import logging
from typing import List, Dict, Any, Optional
import numpy as np

from ..config import config

logger = logging.getLogger(__name__)

# Global vector store instance (lazy loaded)
_vector_store = None


def get_vector_store() -> "VectorStore":
    """Get or create the global vector store instance."""
    global _vector_store

    if _vector_store is None:
        _vector_store = VectorStore()

    return _vector_store


class VectorStore:
    """
    ChromaDB-based vector store for semantic search.

    Uses persistent storage for durability across restarts.
    """

    COLLECTION_NAME = "knowledge_chunks"

    def __init__(self, persist_directory: str = None):
        self.persist_directory = persist_directory or str(config.CHROMA_PATH)
        self._client = None
        self._collection = None

    @property
    def client(self):
        """Lazy load ChromaDB client."""
        if self._client is None:
            try:
                import chromadb
                from chromadb.config import Settings

                # Ensure directory exists
                import os
                os.makedirs(self.persist_directory, exist_ok=True)

                # Create persistent client
                self._client = chromadb.PersistentClient(
                    path=self.persist_directory,
                    settings=Settings(
                        anonymized_telemetry=False,
                        allow_reset=True
                    )
                )
                logger.info(f"ChromaDB initialized at {self.persist_directory}")

            except ImportError:
                logger.error("chromadb not installed. Run: pip install chromadb")
                raise ImportError("chromadb is required for vector storage")

        return self._client

    @property
    def collection(self):
        """Get or create the main collection."""
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"}  # Use cosine similarity
            )
            logger.info(f"Collection '{self.COLLECTION_NAME}' ready with {self._collection.count()} documents")

        return self._collection

    def add_chunks(
        self,
        chunk_ids: List[str],
        embeddings: np.ndarray,
        texts: List[str],
        metadatas: List[Dict[str, Any]] = None
    ) -> None:
        """
        Add chunks to the vector store.

        Args:
            chunk_ids: Unique IDs for each chunk
            embeddings: Numpy array of embeddings (n_chunks, embedding_dim)
            texts: Original text content for each chunk
            metadatas: Optional metadata dicts for each chunk
        """
        if len(chunk_ids) == 0:
            return

        # Convert embeddings to list format for ChromaDB
        embeddings_list = embeddings.tolist() if isinstance(embeddings, np.ndarray) else embeddings

        # Ensure metadatas is provided
        if metadatas is None:
            metadatas = [{} for _ in chunk_ids]

        # Clean metadata - ChromaDB only accepts str, int, float, bool
        clean_metadatas = []
        for meta in metadatas:
            clean_meta = {}
            for k, v in meta.items():
                if isinstance(v, (str, int, float, bool)):
                    clean_meta[k] = v
                elif v is None:
                    clean_meta[k] = ""
                else:
                    clean_meta[k] = str(v)
            clean_metadatas.append(clean_meta)

        # Add to collection
        self.collection.add(
            ids=chunk_ids,
            embeddings=embeddings_list,
            documents=texts,
            metadatas=clean_metadatas
        )

        logger.info(f"Added {len(chunk_ids)} chunks to vector store")

    def search(
        self,
        query_embedding: np.ndarray,
        n_results: int = 5,
        where: Dict[str, Any] = None,
        where_document: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Search for similar chunks.

        Args:
            query_embedding: Query embedding vector
            n_results: Number of results to return
            where: Optional metadata filter
            where_document: Optional document content filter

        Returns:
            Dict with ids, documents, metadatas, distances
        """
        # Convert to list format
        query_list = query_embedding.tolist() if isinstance(query_embedding, np.ndarray) else query_embedding

        # Build query kwargs
        query_kwargs = {
            "query_embeddings": [query_list],
            "n_results": n_results,
            "include": ["documents", "metadatas", "distances"]
        }

        if where:
            query_kwargs["where"] = where

        if where_document:
            query_kwargs["where_document"] = where_document

        results = self.collection.query(**query_kwargs)

        # Flatten results (ChromaDB returns nested lists)
        return {
            "ids": results["ids"][0] if results["ids"] else [],
            "documents": results["documents"][0] if results["documents"] else [],
            "metadatas": results["metadatas"][0] if results["metadatas"] else [],
            "distances": results["distances"][0] if results["distances"] else []
        }

    def delete_by_document(self, document_id: str) -> int:
        """
        Delete all chunks for a document.

        Args:
            document_id: The source document ID

        Returns:
            Number of chunks deleted
        """
        # Get chunks for this document
        results = self.collection.get(
            where={"document_id": document_id},
            include=[]
        )

        if results["ids"]:
            self.collection.delete(ids=results["ids"])
            logger.info(f"Deleted {len(results['ids'])} chunks for document {document_id}")
            return len(results["ids"])

        return 0

    def delete_chunks(self, chunk_ids: List[str]) -> None:
        """Delete specific chunks by ID."""
        if chunk_ids:
            self.collection.delete(ids=chunk_ids)
            logger.info(f"Deleted {len(chunk_ids)} chunks")

    def get_chunk(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific chunk by ID."""
        results = self.collection.get(
            ids=[chunk_id],
            include=["documents", "metadatas", "embeddings"]
        )

        if results["ids"]:
            return {
                "id": results["ids"][0],
                "document": results["documents"][0] if results["documents"] else None,
                "metadata": results["metadatas"][0] if results["metadatas"] else None,
                "embedding": results["embeddings"][0] if results["embeddings"] else None
            }

        return None

    def count(self) -> int:
        """Get total number of chunks in the store."""
        return self.collection.count()

    def reset(self) -> None:
        """Delete all data and reset the collection."""
        self.client.delete_collection(self.COLLECTION_NAME)
        self._collection = None
        logger.warning("Vector store reset - all data deleted")

    def get_all_document_ids(self) -> List[str]:
        """Get unique document IDs in the store."""
        # Get all metadata
        results = self.collection.get(include=["metadatas"])

        document_ids = set()
        for meta in results["metadatas"]:
            if meta and "document_id" in meta:
                document_ids.add(meta["document_id"])

        return list(document_ids)


def is_chromadb_available() -> bool:
    """Check if ChromaDB is available."""
    try:
        import chromadb
        return True
    except ImportError:
        return False
