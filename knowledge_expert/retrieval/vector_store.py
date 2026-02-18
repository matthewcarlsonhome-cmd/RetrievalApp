"""
Vector store using ChromaDB for embedding storage and retrieval.
Supports strict multi-tenant isolation with per-organization collections.
"""

import logging
from typing import List, Dict, Any, Optional
import numpy as np
import re

from ..config import config

logger = logging.getLogger(__name__)

# Global vector store instance (lazy loaded)
_vector_store = None
_tenant_stores: Dict[str, "TenantVectorStore"] = {}


def get_vector_store(organization_id: str = None) -> "VectorStore":
    """
    Get vector store instance.

    Args:
        organization_id: If provided, returns a tenant-isolated store.
                        If None, returns the legacy global store.
    """
    global _vector_store

    if organization_id:
        return get_tenant_store(organization_id)

    if _vector_store is None:
        _vector_store = VectorStore()

    return _vector_store


def get_tenant_store(organization_id: str) -> "TenantVectorStore":
    """Get or create a tenant-isolated vector store."""
    global _tenant_stores

    if organization_id not in _tenant_stores:
        _tenant_stores[organization_id] = TenantVectorStore(organization_id)

    return _tenant_stores[organization_id]


def sanitize_collection_name(name: str) -> str:
    """
    Sanitize organization ID for use as ChromaDB collection name.
    ChromaDB collection names must:
    - Be 3-63 characters
    - Start and end with alphanumeric
    - Contain only alphanumeric, underscores, hyphens
    - Not contain consecutive periods
    """
    # Replace invalid characters with underscores
    sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', name)

    # Ensure starts with alphanumeric
    if sanitized and not sanitized[0].isalnum():
        sanitized = 'org_' + sanitized

    # Ensure ends with alphanumeric
    if sanitized and not sanitized[-1].isalnum():
        sanitized = sanitized + '_col'

    # Truncate to 63 chars max
    if len(sanitized) > 63:
        sanitized = sanitized[:60] + '_col'

    # Ensure minimum length
    if len(sanitized) < 3:
        sanitized = 'org_' + sanitized

    return sanitized


class TenantVectorStore:
    """
    Tenant-isolated vector store.

    Each organization gets its own ChromaDB collection, ensuring strict
    data separation between tenants.
    """

    def __init__(self, organization_id: str, persist_directory: str = None):
        self.organization_id = organization_id
        self.collection_name = f"tenant_{sanitize_collection_name(organization_id)}"
        self.persist_directory = persist_directory or str(config.CHROMA_PATH)
        self._client = None
        self._collection = None

        logger.info(f"TenantVectorStore initialized for org: {organization_id}")

    @property
    def client(self):
        """Lazy load ChromaDB client."""
        if self._client is None:
            try:
                import chromadb
                from chromadb.config import Settings

                import os
                os.makedirs(self.persist_directory, exist_ok=True)

                self._client = chromadb.PersistentClient(
                    path=self.persist_directory,
                    settings=Settings(
                        anonymized_telemetry=False,
                        allow_reset=True
                    )
                )

            except ImportError:
                logger.error("chromadb not installed. Run: pip install chromadb")
                raise ImportError("chromadb is required for vector storage")

        return self._client

    @property
    def collection(self):
        """Get or create the tenant's collection."""
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={
                    "hnsw:space": "cosine",
                    "organization_id": self.organization_id
                }
            )
            logger.info(f"Tenant collection '{self.collection_name}' ready with {self._collection.count()} documents")

        return self._collection

    def add_chunks(
        self,
        chunk_ids: List[str],
        embeddings: np.ndarray,
        texts: List[str],
        metadatas: List[Dict[str, Any]] = None
    ) -> None:
        """Add chunks to the tenant's vector store."""
        if len(chunk_ids) == 0:
            return

        embeddings_list = embeddings.tolist() if isinstance(embeddings, np.ndarray) else embeddings

        if metadatas is None:
            metadatas = [{} for _ in chunk_ids]

        # Add organization_id to all metadata and clean
        clean_metadatas = []
        for meta in metadatas:
            clean_meta = {"organization_id": self.organization_id}
            for k, v in meta.items():
                if isinstance(v, (str, int, float, bool)):
                    clean_meta[k] = v
                elif v is None:
                    clean_meta[k] = ""
                else:
                    clean_meta[k] = str(v)
            clean_metadatas.append(clean_meta)

        self.collection.add(
            ids=chunk_ids,
            embeddings=embeddings_list,
            documents=texts,
            metadatas=clean_metadatas
        )

        logger.info(f"Added {len(chunk_ids)} chunks to tenant {self.organization_id}")

    def search(
        self,
        query_embedding: np.ndarray,
        n_results: int = 5,
        where: Dict[str, Any] = None,
        where_document: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Search for similar chunks within this tenant's collection."""
        query_list = query_embedding.tolist() if isinstance(query_embedding, np.ndarray) else query_embedding

        query_kwargs = {
            "query_embeddings": [query_list],
            "n_results": n_results,
            "include": ["documents", "metadatas", "distances"]
        }

        # Always filter by organization_id for safety
        org_filter = {"organization_id": self.organization_id}
        if where:
            query_kwargs["where"] = {"$and": [org_filter, where]}
        else:
            query_kwargs["where"] = org_filter

        if where_document:
            query_kwargs["where_document"] = where_document

        results = self.collection.query(**query_kwargs)

        return {
            "ids": results["ids"][0] if results["ids"] else [],
            "documents": results["documents"][0] if results["documents"] else [],
            "metadatas": results["metadatas"][0] if results["metadatas"] else [],
            "distances": results["distances"][0] if results["distances"] else []
        }

    def delete_by_document(self, document_id: str) -> int:
        """Delete all chunks for a document within this tenant."""
        results = self.collection.get(
            where={"$and": [
                {"organization_id": self.organization_id},
                {"document_id": document_id}
            ]},
            include=[]
        )

        if results["ids"]:
            self.collection.delete(ids=results["ids"])
            logger.info(f"Deleted {len(results['ids'])} chunks for document {document_id} in tenant {self.organization_id}")
            return len(results["ids"])

        return 0

    def delete_chunks(self, chunk_ids: List[str]) -> None:
        """Delete specific chunks by ID."""
        if chunk_ids:
            self.collection.delete(ids=chunk_ids)
            logger.info(f"Deleted {len(chunk_ids)} chunks in tenant {self.organization_id}")

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
        """Get total number of chunks in this tenant's store."""
        return self.collection.count()

    def reset(self) -> None:
        """Delete all data and reset this tenant's collection."""
        self.client.delete_collection(self.collection_name)
        self._collection = None
        logger.warning(f"Tenant {self.organization_id} vector store reset - all data deleted")

    def get_all_document_ids(self) -> List[str]:
        """Get unique document IDs in this tenant's store."""
        results = self.collection.get(
            where={"organization_id": self.organization_id},
            include=["metadatas"]
        )

        document_ids = set()
        for meta in results["metadatas"]:
            if meta and "document_id" in meta:
                document_ids.add(meta["document_id"])

        return list(document_ids)


class VectorStore:
    """
    ChromaDB-based vector store for semantic search.

    This is the legacy global store. For multi-tenant deployments,
    use TenantVectorStore via get_tenant_store().
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

                import os
                os.makedirs(self.persist_directory, exist_ok=True)

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
                metadata={"hnsw:space": "cosine"}
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
        """Add chunks to the vector store."""
        if len(chunk_ids) == 0:
            return

        embeddings_list = embeddings.tolist() if isinstance(embeddings, np.ndarray) else embeddings

        if metadatas is None:
            metadatas = [{} for _ in chunk_ids]

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
        """Search for similar chunks."""
        query_list = query_embedding.tolist() if isinstance(query_embedding, np.ndarray) else query_embedding

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

        return {
            "ids": results["ids"][0] if results["ids"] else [],
            "documents": results["documents"][0] if results["documents"] else [],
            "metadatas": results["metadatas"][0] if results["metadatas"] else [],
            "distances": results["distances"][0] if results["distances"] else []
        }

    def delete_by_document(self, document_id: str) -> int:
        """Delete all chunks for a document."""
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
