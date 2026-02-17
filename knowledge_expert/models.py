"""
Database models for Knowledge Expert.
Uses SQLite for simplicity and Render compatibility.
"""

import sqlite3
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from contextlib import contextmanager

from .config import config


@dataclass
class KnowledgeItem:
    """A document or Q&A in the knowledge base."""
    title: str
    content: str
    type: str = "document"  # 'document', 'faq', 'qa_direct'
    id: Optional[str] = None
    source_file: Optional[str] = None
    file_type: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    chunk_count: int = 0
    status: str = "pending"
    source: Optional[str] = None
    created_at: str = None
    updated_at: str = None

    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()
        if self.updated_at is None:
            self.updated_at = self.created_at
        if self.tags is None:
            self.tags = []


@dataclass
class Chunk:
    """A chunk of text from a knowledge item."""
    id: str
    document_id: str  # Also known as knowledge_item_id
    content: str
    chunk_index: int
    section_title: Optional[str] = None
    token_count: int = 0


@dataclass
class Query:
    """A user query."""
    question: str
    answer: Optional[str] = None
    id: Optional[str] = None
    sources: Optional[List[Any]] = None
    model_used: Optional[str] = None
    tokens_used: int = 0
    conversation_id: Optional[str] = None
    feedback: Optional[str] = None  # 'positive', 'negative', None
    feedback_text: Optional[str] = None
    created_at: str = None

    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()


@dataclass
class DirectQA:
    """A directly entered Q&A pair."""
    question: str
    answer: str
    id: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    created_at: str = None

    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()
        if self.tags is None:
            self.tags = []


class Database:
    """SQLite database manager."""

    def __init__(self, db_path: Path = None):
        self.db_path = db_path or config.SQLITE_DB_PATH
        self._init_db()

    @contextmanager
    def get_connection(self):
        """Get a database connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        """Initialize database schema."""
        with self.get_connection() as conn:
            conn.executescript("""
                -- Knowledge items (documents, FAQs)
                CREATE TABLE IF NOT EXISTS knowledge_items (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source_file TEXT,
                    category TEXT,
                    tags TEXT,
                    chunk_count INTEGER DEFAULT 0,
                    created_at TEXT,
                    updated_at TEXT
                );

                -- Chunks for vector search
                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT PRIMARY KEY,
                    knowledge_item_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    section_title TEXT,
                    token_count INTEGER DEFAULT 0,
                    FOREIGN KEY (knowledge_item_id) REFERENCES knowledge_items(id)
                );

                -- User queries and responses
                CREATE TABLE IF NOT EXISTS queries (
                    id TEXT PRIMARY KEY,
                    query_text TEXT NOT NULL,
                    response_text TEXT,
                    sources TEXT,
                    confidence REAL,
                    feedback TEXT,
                    created_at TEXT
                );

                -- Direct Q&A entries
                CREATE TABLE IF NOT EXISTS direct_qa (
                    id TEXT PRIMARY KEY,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    category TEXT,
                    tags TEXT,
                    created_at TEXT
                );

                -- Content exclusion list
                CREATE TABLE IF NOT EXISTS exclusion_list (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    value TEXT NOT NULL,
                    created_at TEXT
                );

                -- Create indexes
                CREATE INDEX IF NOT EXISTS idx_chunks_item ON chunks(knowledge_item_id);
                CREATE INDEX IF NOT EXISTS idx_queries_created ON queries(created_at);
                CREATE INDEX IF NOT EXISTS idx_knowledge_type ON knowledge_items(type);
            """)

    # Knowledge Items
    def add_knowledge_item(self, item: KnowledgeItem) -> str:
        """Add a knowledge item."""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO knowledge_items (id, type, title, content, source_file, category, tags, chunk_count, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item.id, item.type, item.title, item.content,
                item.source_file, item.category,
                json.dumps(item.tags) if item.tags else None,
                item.chunk_count, item.created_at, item.updated_at
            ))
        return item.id

    def get_knowledge_item(self, item_id: str) -> Optional[KnowledgeItem]:
        """Get a knowledge item by ID."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM knowledge_items WHERE id = ?", (item_id,)
            ).fetchone()
            if row:
                return self._row_to_knowledge_item(row)
        return None

    def get_all_knowledge_items(self, item_type: str = None) -> List[KnowledgeItem]:
        """Get all knowledge items, optionally filtered by type."""
        with self.get_connection() as conn:
            if item_type:
                rows = conn.execute(
                    "SELECT * FROM knowledge_items WHERE type = ? ORDER BY created_at DESC",
                    (item_type,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM knowledge_items ORDER BY created_at DESC"
                ).fetchall()
            return [self._row_to_knowledge_item(row) for row in rows]

    def delete_knowledge_item(self, item_id: str):
        """Delete a knowledge item and its chunks."""
        with self.get_connection() as conn:
            conn.execute("DELETE FROM chunks WHERE knowledge_item_id = ?", (item_id,))
            conn.execute("DELETE FROM knowledge_items WHERE id = ?", (item_id,))

    def update_knowledge_item_status(self, item_id: str, status: str, chunk_count: int = None):
        """Update status of a knowledge item."""
        with self.get_connection() as conn:
            if chunk_count is not None:
                conn.execute(
                    "UPDATE knowledge_items SET chunk_count = ?, updated_at = ? WHERE id = ?",
                    (chunk_count, datetime.utcnow().isoformat(), item_id)
                )
            # Note: status field not in current schema, but could be added

    def _row_to_knowledge_item(self, row) -> KnowledgeItem:
        """Convert a database row to KnowledgeItem."""
        return KnowledgeItem(
            id=row["id"],
            type=row["type"],
            title=row["title"],
            content=row["content"],
            source_file=row["source_file"],
            category=row["category"],
            tags=json.loads(row["tags"]) if row["tags"] else [],
            chunk_count=row["chunk_count"],
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )

    # Chunks
    def add_chunk(self, chunk: Chunk):
        """Add a chunk."""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO chunks (id, knowledge_item_id, content, chunk_index, section_title, token_count)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                chunk.id, chunk.document_id, chunk.content,
                chunk.chunk_index, chunk.section_title, chunk.token_count
            ))

    def add_chunks(self, chunks: List[Chunk]):
        """Add multiple chunks."""
        with self.get_connection() as conn:
            conn.executemany("""
                INSERT INTO chunks (id, knowledge_item_id, content, chunk_index, section_title, token_count)
                VALUES (?, ?, ?, ?, ?, ?)
            """, [
                (c.id, c.document_id, c.content, c.chunk_index, c.section_title, c.token_count)
                for c in chunks
            ])

    def get_chunks_by_item(self, item_id: str) -> List[Chunk]:
        """Get all chunks for a knowledge item."""
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM chunks WHERE knowledge_item_id = ? ORDER BY chunk_index",
                (item_id,)
            ).fetchall()
            return [self._row_to_chunk(row) for row in rows]

    def get_chunk(self, chunk_id: str) -> Optional[Chunk]:
        """Get a chunk by ID."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM chunks WHERE id = ?", (chunk_id,)
            ).fetchone()
            if row:
                return self._row_to_chunk(row)
        return None

    def _row_to_chunk(self, row) -> Chunk:
        """Convert a database row to Chunk."""
        return Chunk(
            id=row["id"],
            document_id=row["knowledge_item_id"],
            content=row["content"],
            chunk_index=row["chunk_index"],
            section_title=row["section_title"],
            token_count=row["token_count"]
        )

    # Queries
    def add_query(self, query: Query) -> str:
        """Add a query record."""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO queries (id, query_text, response_text, sources, confidence, feedback, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                query.id, query.question, query.answer,
                json.dumps(query.sources) if query.sources else None,
                None, query.feedback, query.created_at
            ))
        return query.id

    def update_query_feedback(self, query_id: str, feedback: str, feedback_text: str = None):
        """Update feedback for a query."""
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE queries SET feedback = ? WHERE id = ?",
                (feedback, query_id)
            )

    def get_queries(self, limit: int = 100) -> List[Query]:
        """Get recent queries."""
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM queries ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
            return [self._row_to_query(row) for row in rows]

    def _row_to_query(self, row) -> Query:
        """Convert a database row to Query."""
        return Query(
            id=row["id"],
            question=row["query_text"],
            answer=row["response_text"],
            sources=json.loads(row["sources"]) if row["sources"] else None,
            feedback=row["feedback"],
            created_at=row["created_at"]
        )

    # Direct Q&A
    def add_direct_qa(self, qa: DirectQA) -> str:
        """Add a direct Q&A entry."""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO direct_qa (id, question, answer, category, tags, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                qa.id, qa.question, qa.answer, qa.category,
                json.dumps(qa.tags) if qa.tags else None, qa.created_at
            ))
        return qa.id

    def get_all_direct_qa(self) -> List[DirectQA]:
        """Get all direct Q&A entries."""
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM direct_qa ORDER BY created_at DESC"
            ).fetchall()
            return [self._row_to_direct_qa(row) for row in rows]

    def delete_direct_qa(self, qa_id: str):
        """Delete a direct Q&A entry."""
        with self.get_connection() as conn:
            conn.execute("DELETE FROM direct_qa WHERE id = ?", (qa_id,))

    def _row_to_direct_qa(self, row) -> DirectQA:
        """Convert a database row to DirectQA."""
        return DirectQA(
            id=row["id"],
            question=row["question"],
            answer=row["answer"],
            category=row["category"],
            tags=json.loads(row["tags"]) if row["tags"] else [],
            created_at=row["created_at"]
        )

    # Stats
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        with self.get_connection() as conn:
            items = conn.execute("SELECT COUNT(*) FROM knowledge_items").fetchone()[0]
            chunks = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
            queries = conn.execute("SELECT COUNT(*) FROM queries").fetchone()[0]
            qa_direct = conn.execute("SELECT COUNT(*) FROM direct_qa").fetchone()[0]
            positive = conn.execute(
                "SELECT COUNT(*) FROM queries WHERE feedback = 'positive'"
            ).fetchone()[0]
            negative = conn.execute(
                "SELECT COUNT(*) FROM queries WHERE feedback = 'negative'"
            ).fetchone()[0]

            return {
                "total_documents": items,
                "total_chunks": chunks,
                "total_queries": queries,
                "total_qa_pairs": qa_direct,
                "positive_feedback": positive,
                "negative_feedback": negative,
                "satisfaction_rate": positive / (positive + negative) if (positive + negative) > 0 else None
            }


# Global database instance
db = Database()
