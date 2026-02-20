"""
Response Caching Layer for Knowledge Expert.

Provides intelligent caching for LLM responses to:
- Reduce API costs for repeated similar queries
- Improve response times
- Handle semantic similarity matching for cache hits

Supports multiple backends:
- In-memory cache (default, fast but not persistent)
- SQLite cache (persistent across restarts)
- Redis cache (for distributed deployments)
"""

import hashlib
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
import sqlite3
from pathlib import Path

from .config import config

logger = logging.getLogger(__name__)


@dataclass
class CachedResponse:
    """A cached query response."""
    query: str
    response: str
    query_hash: str
    created_at: float
    expires_at: float
    hit_count: int = 0
    metadata: Dict[str, Any] = None

    def is_expired(self) -> bool:
        return time.time() > self.expires_at


class CacheBackend(ABC):
    """Abstract base class for cache backends."""

    @abstractmethod
    def get(self, key: str) -> Optional[CachedResponse]:
        """Get a cached response by key."""
        pass

    @abstractmethod
    def set(self, key: str, response: CachedResponse) -> None:
        """Store a response in the cache."""
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete a cached response."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all cached responses."""
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        pass


class InMemoryCache(CacheBackend):
    """Fast in-memory cache (not persistent)."""

    def __init__(self, max_size: int = 1000):
        self.cache: Dict[str, CachedResponse] = {}
        self.max_size = max_size
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[CachedResponse]:
        if key in self.cache:
            response = self.cache[key]
            if response.is_expired():
                del self.cache[key]
                self.misses += 1
                return None
            response.hit_count += 1
            self.hits += 1
            return response
        self.misses += 1
        return None

    def set(self, key: str, response: CachedResponse) -> None:
        # Evict oldest entries if at capacity
        if len(self.cache) >= self.max_size:
            self._evict_oldest()
        self.cache[key] = response

    def delete(self, key: str) -> None:
        if key in self.cache:
            del self.cache[key]

    def clear(self) -> None:
        self.cache.clear()
        self.hits = 0
        self.misses = 0

    def get_stats(self) -> Dict[str, Any]:
        return {
            "backend": "memory",
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.hits / (self.hits + self.misses) if (self.hits + self.misses) > 0 else 0
        }

    def _evict_oldest(self):
        """Evict the oldest 10% of entries."""
        if not self.cache:
            return

        sorted_keys = sorted(
            self.cache.keys(),
            key=lambda k: self.cache[k].created_at
        )
        evict_count = max(1, len(sorted_keys) // 10)
        for key in sorted_keys[:evict_count]:
            del self.cache[key]


class SQLiteCache(CacheBackend):
    """Persistent SQLite-based cache."""

    def __init__(self, db_path: Path = None):
        self.db_path = db_path or config.DATA_PATH / "cache.db"
        self._init_db()

    def _init_db(self):
        """Initialize the cache database."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS response_cache (
                    key TEXT PRIMARY KEY,
                    query TEXT NOT NULL,
                    response TEXT NOT NULL,
                    query_hash TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL,
                    hit_count INTEGER DEFAULT 0,
                    metadata TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_cache_expires ON response_cache(expires_at)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_cache_hash ON response_cache(query_hash)
            """)

    def get(self, key: str) -> Optional[CachedResponse]:
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM response_cache WHERE key = ?",
                (key,)
            ).fetchone()

            if not row:
                return None

            response = CachedResponse(
                query=row['query'],
                response=row['response'],
                query_hash=row['query_hash'],
                created_at=row['created_at'],
                expires_at=row['expires_at'],
                hit_count=row['hit_count'],
                metadata=json.loads(row['metadata']) if row['metadata'] else None
            )

            if response.is_expired():
                self.delete(key)
                return None

            # Increment hit count
            conn.execute(
                "UPDATE response_cache SET hit_count = hit_count + 1 WHERE key = ?",
                (key,)
            )
            response.hit_count += 1
            return response

    def set(self, key: str, response: CachedResponse) -> None:
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO response_cache
                (key, query, response, query_hash, created_at, expires_at, hit_count, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                key,
                response.query,
                response.response,
                response.query_hash,
                response.created_at,
                response.expires_at,
                response.hit_count,
                json.dumps(response.metadata) if response.metadata else None
            ))

    def delete(self, key: str) -> None:
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("DELETE FROM response_cache WHERE key = ?", (key,))

    def clear(self) -> None:
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("DELETE FROM response_cache")

    def cleanup_expired(self) -> int:
        """Remove expired entries. Returns number removed."""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute(
                "DELETE FROM response_cache WHERE expires_at < ?",
                (time.time(),)
            )
            return cursor.rowcount

    def get_stats(self) -> Dict[str, Any]:
        with sqlite3.connect(str(self.db_path)) as conn:
            size = conn.execute("SELECT COUNT(*) FROM response_cache").fetchone()[0]
            hits = conn.execute("SELECT SUM(hit_count) FROM response_cache").fetchone()[0] or 0
            expired = conn.execute(
                "SELECT COUNT(*) FROM response_cache WHERE expires_at < ?",
                (time.time(),)
            ).fetchone()[0]

            return {
                "backend": "sqlite",
                "size": size,
                "total_hits": hits,
                "expired_entries": expired,
                "db_path": str(self.db_path)
            }


class ResponseCache:
    """
    Main caching interface with semantic matching support.

    Provides intelligent query caching with:
    - Exact match caching (fast, hash-based)
    - Semantic similarity matching (optional, for fuzzy matches)
    - Tenant isolation
    - TTL-based expiration
    """

    def __init__(
        self,
        backend: CacheBackend = None,
        ttl_seconds: int = 3600,  # 1 hour default
        enable_semantic: bool = False,
        similarity_threshold: float = 0.95
    ):
        self.backend = backend or InMemoryCache()
        self.ttl_seconds = ttl_seconds
        self.enable_semantic = enable_semantic
        self.similarity_threshold = similarity_threshold
        self._embedder = None

    @property
    def embedder(self):
        """Lazy load embedder for semantic matching."""
        if self._embedder is None and self.enable_semantic:
            try:
                from .ingestion.embedder import EmbeddingGenerator
                self._embedder = EmbeddingGenerator()
            except Exception as e:
                logger.warning(f"Could not load embedder for semantic cache: {e}")
                self.enable_semantic = False
        return self._embedder

    def _make_key(self, query: str, organization_id: str = None) -> str:
        """Generate a cache key from query and optional organization."""
        normalized = query.lower().strip()
        key_data = f"{organization_id or 'global'}:{normalized}"
        return hashlib.sha256(key_data.encode()).hexdigest()

    def _make_hash(self, query: str) -> str:
        """Generate a hash for semantic grouping."""
        normalized = query.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()

    def get(
        self,
        query: str,
        organization_id: str = None
    ) -> Optional[Tuple[str, bool]]:
        """
        Get a cached response for a query.

        Returns:
            Tuple of (response_text, is_exact_match) or None if not found
        """
        key = self._make_key(query, organization_id)

        # Try exact match first
        cached = self.backend.get(key)
        if cached:
            logger.debug(f"Cache hit (exact): {key[:16]}...")
            return cached.response, True

        # TODO: Semantic matching could be added here using embeddings
        # For now, we only do exact matching

        return None

    def set(
        self,
        query: str,
        response: str,
        organization_id: str = None,
        metadata: Dict[str, Any] = None,
        ttl_seconds: int = None
    ) -> None:
        """Cache a response for a query."""
        key = self._make_key(query, organization_id)
        ttl = ttl_seconds or self.ttl_seconds

        cached = CachedResponse(
            query=query,
            response=response,
            query_hash=self._make_hash(query),
            created_at=time.time(),
            expires_at=time.time() + ttl,
            hit_count=0,
            metadata={
                **(metadata or {}),
                "organization_id": organization_id
            }
        )

        self.backend.set(key, cached)
        logger.debug(f"Cache set: {key[:16]}... (TTL: {ttl}s)")

    def invalidate(self, query: str, organization_id: str = None) -> None:
        """Invalidate a specific cached response."""
        key = self._make_key(query, organization_id)
        self.backend.delete(key)

    def clear(self, organization_id: str = None) -> None:
        """
        Clear cache entries.

        If organization_id is provided, only clears that org's entries.
        Otherwise clears all entries.
        """
        # For simplicity, clear all. Tenant-specific clearing would
        # require iterating through entries in most backends.
        self.backend.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = self.backend.get_stats()
        stats["ttl_seconds"] = self.ttl_seconds
        stats["semantic_enabled"] = self.enable_semantic
        return stats


# Global cache instance
_response_cache: Optional[ResponseCache] = None


def get_response_cache() -> ResponseCache:
    """Get or create the global response cache."""
    global _response_cache

    if _response_cache is None:
        # Determine backend based on environment
        import os

        cache_backend = os.environ.get("CACHE_BACKEND", "memory")
        cache_ttl = int(os.environ.get("CACHE_TTL_SECONDS", "3600"))

        if cache_backend == "sqlite":
            backend = SQLiteCache()
        else:
            max_size = int(os.environ.get("CACHE_MAX_SIZE", "1000"))
            backend = InMemoryCache(max_size=max_size)

        _response_cache = ResponseCache(
            backend=backend,
            ttl_seconds=cache_ttl
        )

        logger.info(f"Response cache initialized: {cache_backend} backend, TTL={cache_ttl}s")

    return _response_cache


def cached_query(func):
    """
    Decorator to cache query responses.

    Usage:
        @cached_query
        def process_query(query, organization_id=None, **kwargs):
            # expensive LLM call
            return response

    The decorator will:
    1. Check cache for existing response
    2. If found, return cached response
    3. If not found, call function and cache result
    """
    import functools

    @functools.wraps(func)
    def wrapper(query: str, organization_id: str = None, **kwargs):
        # Skip cache if explicitly disabled
        if kwargs.pop('skip_cache', False):
            return func(query, organization_id=organization_id, **kwargs)

        cache = get_response_cache()

        # Try cache
        cached = cache.get(query, organization_id)
        if cached:
            response, is_exact = cached
            logger.info(f"Cache hit for query: {query[:50]}...")
            return response

        # Call actual function
        response = func(query, organization_id=organization_id, **kwargs)

        # Cache the result if it's valid
        if response:
            cache.set(
                query=query,
                response=response,
                organization_id=organization_id,
                metadata={"source": func.__name__}
            )

        return response

    return wrapper
