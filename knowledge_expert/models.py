"""
Database models for Knowledge Expert.
Supports multi-tenant architecture with organizations, users, and access control.
"""

import sqlite3
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict, field
from contextlib import contextmanager
import hashlib
import secrets

from .config import config


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class Organization:
    """A tenant organization."""
    name: str
    slug: str  # URL-friendly identifier
    id: Optional[str] = None
    settings: Dict[str, Any] = field(default_factory=dict)
    created_at: str = None

    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()


@dataclass
class User:
    """A user with organization membership and role-based access."""
    email: str
    name: str
    organization_id: str
    id: Optional[str] = None
    role: str = "member"  # admin, editor, member, viewer
    password_hash: str = None
    api_key: str = None
    created_at: str = None
    last_login: str = None

    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password with salt."""
        salt = secrets.token_hex(16)
        hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return f"{salt}${hash_obj.hex()}"

    def verify_password(self, password: str) -> bool:
        """Verify a password against the stored hash."""
        if not self.password_hash:
            return False
        salt, hash_value = self.password_hash.split('$')
        hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return hash_obj.hex() == hash_value


@dataclass
class KnowledgeItem:
    """A document in the knowledge base."""
    title: str
    content: str
    type: str = "document"  # document, faq, qa_direct
    id: Optional[str] = None
    organization_id: Optional[str] = None
    source_file: Optional[str] = None
    file_type: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    chunk_count: int = 0
    chunking_strategy: str = "sentence"
    chunk_size: int = 500

    # Access control
    access_level: str = "organization"  # public, organization, restricted
    allowed_users: List[str] = field(default_factory=list)
    created_by: Optional[str] = None

    # Citation support
    source_url: Optional[str] = None  # Original URL if applicable
    page_count: int = 0  # For PDFs

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
        if self.allowed_users is None:
            self.allowed_users = []


@dataclass
class Chunk:
    """A chunk of text from a knowledge item."""
    id: str
    document_id: str
    content: str
    chunk_index: int
    organization_id: Optional[str] = None
    section_title: Optional[str] = None
    token_count: int = 0
    chunking_strategy: str = "sentence"
    chunk_size_setting: int = 500

    # Citation support
    start_char: int = 0
    end_char: int = 0
    page_number: int = None  # For PDFs


@dataclass
class Conversation:
    """A conversation session for memory."""
    organization_id: str
    id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None  # For anonymous users
    title: str = "New Conversation"
    started_at: str = None
    last_message_at: str = None
    message_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())
        if self.started_at is None:
            self.started_at = datetime.utcnow().isoformat()
        if self.last_message_at is None:
            self.last_message_at = self.started_at


@dataclass
class ConversationMessage:
    """A message in a conversation."""
    conversation_id: str
    role: str  # user, assistant
    content: str
    id: Optional[str] = None
    timestamp: str = None
    chunks_used: List[str] = field(default_factory=list)
    chunk_scores: List[float] = field(default_factory=list)

    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()


@dataclass
class Query:
    """A user query with response and feedback."""
    question: str
    answer: Optional[str] = None
    id: Optional[str] = None
    organization_id: Optional[str] = None
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None

    # Sources and chunks
    sources: Optional[List[Any]] = None
    chunks_used: List[str] = field(default_factory=list)
    chunk_scores: List[float] = field(default_factory=list)

    # Performance
    model_used: Optional[str] = None
    tokens_used: int = 0
    response_time_ms: int = 0

    # Feedback
    feedback: Optional[str] = None  # positive, negative
    feedback_score: Optional[int] = None  # 1-5
    feedback_comment: Optional[str] = None
    is_good_example: bool = False  # Marked for training export

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
    organization_id: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    use_count: int = 0
    created_by: Optional[str] = None
    created_at: str = None

    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()
        if self.tags is None:
            self.tags = []


@dataclass
class KnowledgeGap:
    """A query that couldn't be answered - represents a knowledge gap."""
    query_text: str
    organization_id: str
    id: Optional[str] = None
    failure_reason: str = "no_results"  # no_results, negative_feedback, low_confidence
    occurrence_count: int = 1
    suggested_action: Optional[str] = None
    resolved: bool = False
    resolved_by: Optional[str] = None
    resolved_at: Optional[str] = None
    created_at: str = None

    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()


# =============================================================================
# DATABASE
# =============================================================================

class Database:
    """SQLite database manager with multi-tenant support."""

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
        """Initialize database schema with migration support for existing databases."""
        with self.get_connection() as conn:
            # First, run migrations for existing tables (add missing columns)
            self._run_migrations(conn)

            # Then create any new tables
            conn.executescript("""
                -- Organizations (tenants)
                CREATE TABLE IF NOT EXISTS organizations (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    slug TEXT UNIQUE NOT NULL,
                    settings TEXT DEFAULT '{}',
                    created_at TEXT
                );

                -- Users
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    organization_id TEXT,
                    role TEXT DEFAULT 'member',
                    password_hash TEXT,
                    api_key TEXT UNIQUE,
                    created_at TEXT,
                    last_login TEXT
                );

                -- Knowledge items (documents)
                CREATE TABLE IF NOT EXISTS knowledge_items (
                    id TEXT PRIMARY KEY,
                    organization_id TEXT,
                    type TEXT DEFAULT 'document',
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source_file TEXT,
                    file_type TEXT,
                    category TEXT,
                    tags TEXT,
                    metadata TEXT,
                    chunk_count INTEGER DEFAULT 0,
                    chunking_strategy TEXT DEFAULT 'sentence',
                    chunk_size INTEGER DEFAULT 500,
                    access_level TEXT DEFAULT 'organization',
                    allowed_users TEXT DEFAULT '[]',
                    created_by TEXT,
                    source_url TEXT,
                    page_count INTEGER DEFAULT 0,
                    created_at TEXT,
                    updated_at TEXT
                );

                -- Chunks for vector search
                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT PRIMARY KEY,
                    knowledge_item_id TEXT NOT NULL,
                    organization_id TEXT,
                    content TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    section_title TEXT,
                    token_count INTEGER DEFAULT 0,
                    chunking_strategy TEXT,
                    chunk_size_setting INTEGER,
                    start_char INTEGER DEFAULT 0,
                    end_char INTEGER DEFAULT 0,
                    page_number INTEGER
                );

                -- Conversations
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    organization_id TEXT,
                    user_id TEXT,
                    session_id TEXT,
                    title TEXT DEFAULT 'New Conversation',
                    started_at TEXT,
                    last_message_at TEXT,
                    message_count INTEGER DEFAULT 0,
                    metadata TEXT DEFAULT '{}'
                );

                -- Conversation messages
                CREATE TABLE IF NOT EXISTS conversation_messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT,
                    chunks_used TEXT DEFAULT '[]',
                    chunk_scores TEXT DEFAULT '[]'
                );

                -- Queries and responses
                CREATE TABLE IF NOT EXISTS queries (
                    id TEXT PRIMARY KEY,
                    organization_id TEXT,
                    conversation_id TEXT,
                    user_id TEXT,
                    query_text TEXT NOT NULL,
                    response_text TEXT,
                    sources TEXT,
                    chunks_used TEXT DEFAULT '[]',
                    chunk_scores TEXT DEFAULT '[]',
                    model_used TEXT,
                    tokens_used INTEGER DEFAULT 0,
                    response_time_ms INTEGER DEFAULT 0,
                    feedback TEXT,
                    feedback_score INTEGER,
                    feedback_comment TEXT,
                    is_good_example INTEGER DEFAULT 0,
                    created_at TEXT
                );

                -- Direct Q&A entries
                CREATE TABLE IF NOT EXISTS direct_qa (
                    id TEXT PRIMARY KEY,
                    organization_id TEXT,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    category TEXT,
                    tags TEXT,
                    use_count INTEGER DEFAULT 0,
                    created_by TEXT,
                    created_at TEXT
                );

                -- Knowledge gaps
                CREATE TABLE IF NOT EXISTS knowledge_gaps (
                    id TEXT PRIMARY KEY,
                    organization_id TEXT,
                    query_text TEXT NOT NULL,
                    failure_reason TEXT,
                    occurrence_count INTEGER DEFAULT 1,
                    suggested_action TEXT,
                    resolved INTEGER DEFAULT 0,
                    resolved_by TEXT,
                    resolved_at TEXT,
                    created_at TEXT
                );

                -- Indexes (safe to run multiple times)
                CREATE INDEX IF NOT EXISTS idx_users_org ON users(organization_id);
                CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
                CREATE INDEX IF NOT EXISTS idx_items_org ON knowledge_items(organization_id);
                CREATE INDEX IF NOT EXISTS idx_chunks_item ON chunks(knowledge_item_id);
                CREATE INDEX IF NOT EXISTS idx_chunks_org ON chunks(organization_id);
                CREATE INDEX IF NOT EXISTS idx_conv_org ON conversations(organization_id);
                CREATE INDEX IF NOT EXISTS idx_conv_session ON conversations(session_id);
                CREATE INDEX IF NOT EXISTS idx_messages_conv ON conversation_messages(conversation_id);
                CREATE INDEX IF NOT EXISTS idx_queries_org ON queries(organization_id);
                CREATE INDEX IF NOT EXISTS idx_queries_conv ON queries(conversation_id);
                CREATE INDEX IF NOT EXISTS idx_queries_feedback ON queries(feedback);
                CREATE INDEX IF NOT EXISTS idx_qa_org ON direct_qa(organization_id);
                CREATE INDEX IF NOT EXISTS idx_gaps_org ON knowledge_gaps(organization_id);
                CREATE INDEX IF NOT EXISTS idx_gaps_resolved ON knowledge_gaps(resolved);
            """)

            # Create default organization if none exists
            cursor = conn.execute("SELECT COUNT(*) FROM organizations")
            if cursor.fetchone()[0] == 0:
                default_org = Organization(name="Default Organization", slug="default")
                conn.execute(
                    "INSERT INTO organizations (id, name, slug, settings, created_at) VALUES (?, ?, ?, ?, ?)",
                    (default_org.id, default_org.name, default_org.slug, '{}', default_org.created_at)
                )

    def _run_migrations(self, conn):
        """Run schema migrations for existing databases."""
        # Get list of existing tables
        tables = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}

        # Migration: Add organization_id to existing tables
        migrations = [
            # knowledge_items migrations
            ("knowledge_items", "organization_id", "TEXT"),
            ("knowledge_items", "type", "TEXT DEFAULT 'document'"),
            ("knowledge_items", "chunking_strategy", "TEXT DEFAULT 'sentence'"),
            ("knowledge_items", "chunk_size", "INTEGER DEFAULT 500"),
            ("knowledge_items", "access_level", "TEXT DEFAULT 'organization'"),
            ("knowledge_items", "allowed_users", "TEXT DEFAULT '[]'"),
            ("knowledge_items", "created_by", "TEXT"),
            ("knowledge_items", "source_url", "TEXT"),
            ("knowledge_items", "page_count", "INTEGER DEFAULT 0"),
            ("knowledge_items", "source_file", "TEXT"),
            ("knowledge_items", "updated_at", "TEXT"),

            # chunks migrations
            ("chunks", "organization_id", "TEXT"),
            ("chunks", "chunking_strategy", "TEXT"),
            ("chunks", "chunk_size_setting", "INTEGER"),
            ("chunks", "start_char", "INTEGER DEFAULT 0"),
            ("chunks", "end_char", "INTEGER DEFAULT 0"),
            ("chunks", "page_number", "INTEGER"),

            # queries migrations
            ("queries", "organization_id", "TEXT"),
            ("queries", "conversation_id", "TEXT"),
            ("queries", "user_id", "TEXT"),
            ("queries", "chunks_used", "TEXT DEFAULT '[]'"),
            ("queries", "chunk_scores", "TEXT DEFAULT '[]'"),
            ("queries", "response_time_ms", "INTEGER DEFAULT 0"),
            ("queries", "feedback_score", "INTEGER"),
            ("queries", "feedback_comment", "TEXT"),
            ("queries", "is_good_example", "INTEGER DEFAULT 0"),

            # direct_qa migrations
            ("direct_qa", "organization_id", "TEXT"),
            ("direct_qa", "use_count", "INTEGER DEFAULT 0"),
            ("direct_qa", "created_by", "TEXT"),

            # users migrations (if table exists)
            ("users", "organization_id", "TEXT"),
            ("users", "role", "TEXT DEFAULT 'member'"),
            ("users", "password_hash", "TEXT"),
            ("users", "api_key", "TEXT"),
            ("users", "last_login", "TEXT"),
        ]

        for table, column, col_type in migrations:
            if table in tables:
                # Check if column exists
                cursor = conn.execute(f"PRAGMA table_info({table})")
                existing_columns = {row[1] for row in cursor.fetchall()}

                if column not in existing_columns:
                    try:
                        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
                    except Exception as e:
                        # Column might already exist or other error - continue
                        pass

    # -------------------------------------------------------------------------
    # Organizations
    # -------------------------------------------------------------------------

    def create_organization(self, org: Organization) -> Organization:
        """Create a new organization."""
        with self.get_connection() as conn:
            conn.execute(
                "INSERT INTO organizations (id, name, slug, settings, created_at) VALUES (?, ?, ?, ?, ?)",
                (org.id, org.name, org.slug, json.dumps(org.settings), org.created_at)
            )
        return org

    def get_organization(self, org_id: str) -> Optional[Organization]:
        """Get organization by ID."""
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM organizations WHERE id = ?", (org_id,)).fetchone()
            if row:
                return Organization(
                    id=row['id'], name=row['name'], slug=row['slug'],
                    settings=json.loads(row['settings'] or '{}'),
                    created_at=row['created_at']
                )
        return None

    def get_organization_by_slug(self, slug: str) -> Optional[Organization]:
        """Get organization by slug."""
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM organizations WHERE slug = ?", (slug,)).fetchone()
            if row:
                return Organization(
                    id=row['id'], name=row['name'], slug=row['slug'],
                    settings=json.loads(row['settings'] or '{}'),
                    created_at=row['created_at']
                )
        return None

    def get_default_organization(self) -> Optional[Organization]:
        """Get the default organization."""
        return self.get_organization_by_slug("default")

    # -------------------------------------------------------------------------
    # Users
    # -------------------------------------------------------------------------

    def create_user(self, user: User) -> User:
        """Create a new user."""
        if not user.api_key:
            user.api_key = secrets.token_urlsafe(32)

        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO users (id, email, name, organization_id, role, password_hash, api_key, created_at, last_login)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user.id, user.email, user.name, user.organization_id, user.role,
                  user.password_hash, user.api_key, user.created_at, user.last_login))
        return user

    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            if row:
                return self._row_to_user(row)
        return None

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
            if row:
                return self._row_to_user(row)
        return None

    def get_user_by_api_key(self, api_key: str) -> Optional[User]:
        """Get user by API key."""
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE api_key = ?", (api_key,)).fetchone()
            if row:
                return self._row_to_user(row)
        return None

    def _row_to_user(self, row) -> User:
        return User(
            id=row['id'], email=row['email'], name=row['name'],
            organization_id=row['organization_id'], role=row['role'],
            password_hash=row['password_hash'], api_key=row['api_key'],
            created_at=row['created_at'], last_login=row['last_login']
        )

    def check_access(self, user_id: str, document_id: str) -> bool:
        """Check if user has access to a document."""
        with self.get_connection() as conn:
            user_row = conn.execute(
                "SELECT organization_id, role FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            if not user_row:
                return False

            doc_row = conn.execute(
                "SELECT organization_id, access_level, allowed_users FROM knowledge_items WHERE id = ?",
                (document_id,)
            ).fetchone()
            if not doc_row:
                return False

            # Public documents are accessible to all
            if doc_row['access_level'] == 'public':
                return True

            # Must be in same org
            if doc_row['organization_id'] != user_row['organization_id']:
                return False

            # Organization-level access
            if doc_row['access_level'] == 'organization':
                return True

            # Restricted access
            if doc_row['access_level'] == 'restricted':
                allowed = json.loads(doc_row['allowed_users'] or '[]')
                return user_id in allowed or user_row['role'] == 'admin'

            return False

    # -------------------------------------------------------------------------
    # Knowledge Items
    # -------------------------------------------------------------------------

    def add_knowledge_item(self, item: KnowledgeItem) -> str:
        """Add a knowledge item."""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO knowledge_items
                (id, organization_id, type, title, content, source_file, file_type, category,
                 tags, metadata, chunk_count, chunking_strategy, chunk_size, access_level,
                 allowed_users, created_by, source_url, page_count, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item.id, item.organization_id, item.type, item.title, item.content,
                item.source_file, item.file_type, item.category,
                json.dumps(item.tags), json.dumps(item.metadata) if item.metadata else None,
                item.chunk_count, item.chunking_strategy, item.chunk_size, item.access_level,
                json.dumps(item.allowed_users), item.created_by, item.source_url,
                item.page_count, item.created_at, item.updated_at
            ))
        return item.id

    def get_knowledge_item(self, item_id: str) -> Optional[KnowledgeItem]:
        """Get a knowledge item by ID."""
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM knowledge_items WHERE id = ?", (item_id,)).fetchone()
            if row:
                return self._row_to_knowledge_item(row)
        return None

    def get_all_knowledge_items(self, organization_id: str = None, item_type: str = None) -> List[KnowledgeItem]:
        """Get all knowledge items, optionally filtered."""
        with self.get_connection() as conn:
            query = "SELECT * FROM knowledge_items WHERE 1=1"
            params = []

            if organization_id:
                query += " AND organization_id = ?"
                params.append(organization_id)
            if item_type:
                query += " AND type = ?"
                params.append(item_type)

            query += " ORDER BY created_at DESC"
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_knowledge_item(row) for row in rows]

    def delete_knowledge_item(self, item_id: str):
        """Delete a knowledge item and its chunks."""
        with self.get_connection() as conn:
            conn.execute("DELETE FROM chunks WHERE knowledge_item_id = ?", (item_id,))
            conn.execute("DELETE FROM knowledge_items WHERE id = ?", (item_id,))

    def update_knowledge_item_chunks(self, item_id: str, chunk_count: int, strategy: str = None, chunk_size: int = None):
        """Update chunk info for a knowledge item."""
        with self.get_connection() as conn:
            updates = ["chunk_count = ?", "updated_at = ?"]
            params = [chunk_count, datetime.utcnow().isoformat()]

            if strategy:
                updates.append("chunking_strategy = ?")
                params.append(strategy)
            if chunk_size:
                updates.append("chunk_size = ?")
                params.append(chunk_size)

            params.append(item_id)
            conn.execute(f"UPDATE knowledge_items SET {', '.join(updates)} WHERE id = ?", params)

    def _row_to_knowledge_item(self, row) -> KnowledgeItem:
        return KnowledgeItem(
            id=row['id'], organization_id=row['organization_id'], type=row['type'],
            title=row['title'], content=row['content'], source_file=row['source_file'],
            file_type=row['file_type'], category=row['category'],
            tags=json.loads(row['tags']) if row['tags'] else [],
            metadata=json.loads(row['metadata']) if row['metadata'] else None,
            chunk_count=row['chunk_count'],
            chunking_strategy=row['chunking_strategy'] or 'sentence',
            chunk_size=row['chunk_size'] or 500,
            access_level=row['access_level'] or 'organization',
            allowed_users=json.loads(row['allowed_users']) if row['allowed_users'] else [],
            created_by=row['created_by'], source_url=row['source_url'],
            page_count=row['page_count'] or 0,
            created_at=row['created_at'], updated_at=row['updated_at']
        )

    # -------------------------------------------------------------------------
    # Chunks
    # -------------------------------------------------------------------------

    def add_chunk(self, chunk: Chunk):
        """Add a chunk."""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO chunks
                (id, knowledge_item_id, organization_id, content, chunk_index, section_title,
                 token_count, chunking_strategy, chunk_size_setting, start_char, end_char, page_number)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                chunk.id, chunk.document_id, chunk.organization_id, chunk.content,
                chunk.chunk_index, chunk.section_title, chunk.token_count,
                chunk.chunking_strategy, chunk.chunk_size_setting,
                chunk.start_char, chunk.end_char, chunk.page_number
            ))

    def add_chunks(self, chunks: List[Chunk]):
        """Add multiple chunks."""
        with self.get_connection() as conn:
            conn.executemany("""
                INSERT INTO chunks
                (id, knowledge_item_id, organization_id, content, chunk_index, section_title,
                 token_count, chunking_strategy, chunk_size_setting, start_char, end_char, page_number)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                (c.id, c.document_id, c.organization_id, c.content, c.chunk_index,
                 c.section_title, c.token_count, c.chunking_strategy, c.chunk_size_setting,
                 c.start_char, c.end_char, c.page_number)
                for c in chunks
            ])

    def get_chunk(self, chunk_id: str) -> Optional[Chunk]:
        """Get a chunk by ID."""
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM chunks WHERE id = ?", (chunk_id,)).fetchone()
            if row:
                return self._row_to_chunk(row)
        return None

    def get_chunks_by_item(self, item_id: str) -> List[Chunk]:
        """Get all chunks for a knowledge item."""
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM chunks WHERE knowledge_item_id = ? ORDER BY chunk_index",
                (item_id,)
            ).fetchall()
            return [self._row_to_chunk(row) for row in rows]

    def _row_to_chunk(self, row) -> Chunk:
        return Chunk(
            id=row['id'], document_id=row['knowledge_item_id'],
            organization_id=row['organization_id'], content=row['content'],
            chunk_index=row['chunk_index'], section_title=row['section_title'],
            token_count=row['token_count'],
            chunking_strategy=row['chunking_strategy'],
            chunk_size_setting=row['chunk_size_setting'],
            start_char=row['start_char'] or 0, end_char=row['end_char'] or 0,
            page_number=row['page_number']
        )

    # -------------------------------------------------------------------------
    # Conversations
    # -------------------------------------------------------------------------

    def create_conversation(self, conv: Conversation) -> Conversation:
        """Create a new conversation."""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO conversations
                (id, organization_id, user_id, session_id, title, started_at, last_message_at, message_count, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                conv.id, conv.organization_id, conv.user_id, conv.session_id,
                conv.title, conv.started_at, conv.last_message_at,
                conv.message_count, json.dumps(conv.metadata)
            ))
        return conv

    def get_conversation(self, conv_id: str) -> Optional[Conversation]:
        """Get a conversation by ID."""
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,)).fetchone()
            if row:
                return self._row_to_conversation(row)
        return None

    def get_or_create_conversation(
        self,
        organization_id: str,
        session_id: str = None,
        user_id: str = None
    ) -> Conversation:
        """Get existing conversation or create new one."""
        with self.get_connection() as conn:
            # Try to find recent conversation
            if session_id:
                row = conn.execute(
                    """SELECT * FROM conversations
                       WHERE session_id = ? AND organization_id = ?
                       ORDER BY started_at DESC LIMIT 1""",
                    (session_id, organization_id)
                ).fetchone()
            elif user_id:
                row = conn.execute(
                    """SELECT * FROM conversations
                       WHERE user_id = ? AND organization_id = ?
                       ORDER BY started_at DESC LIMIT 1""",
                    (user_id, organization_id)
                ).fetchone()
            else:
                row = None

            if row:
                return self._row_to_conversation(row)

        # Create new conversation
        conv = Conversation(
            organization_id=organization_id,
            user_id=user_id,
            session_id=session_id
        )
        return self.create_conversation(conv)

    def get_conversations(self, organization_id: str, user_id: str = None, limit: int = 20) -> List[Conversation]:
        """Get recent conversations."""
        with self.get_connection() as conn:
            if user_id:
                rows = conn.execute(
                    """SELECT * FROM conversations
                       WHERE organization_id = ? AND user_id = ?
                       ORDER BY last_message_at DESC LIMIT ?""",
                    (organization_id, user_id, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT * FROM conversations
                       WHERE organization_id = ?
                       ORDER BY last_message_at DESC LIMIT ?""",
                    (organization_id, limit)
                ).fetchall()
            return [self._row_to_conversation(row) for row in rows]

    def _row_to_conversation(self, row) -> Conversation:
        return Conversation(
            id=row['id'], organization_id=row['organization_id'],
            user_id=row['user_id'], session_id=row['session_id'],
            title=row['title'], started_at=row['started_at'],
            last_message_at=row['last_message_at'],
            message_count=row['message_count'],
            metadata=json.loads(row['metadata'] or '{}')
        )

    def add_message(self, message: ConversationMessage) -> ConversationMessage:
        """Add a message to a conversation."""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO conversation_messages
                (id, conversation_id, role, content, timestamp, chunks_used, chunk_scores)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                message.id, message.conversation_id, message.role, message.content,
                message.timestamp, json.dumps(message.chunks_used),
                json.dumps(message.chunk_scores)
            ))

            # Update conversation
            conn.execute("""
                UPDATE conversations
                SET last_message_at = ?, message_count = message_count + 1
                WHERE id = ?
            """, (message.timestamp, message.conversation_id))

        return message

    def get_conversation_history(self, conversation_id: str, limit: int = 10) -> List[ConversationMessage]:
        """Get recent messages from a conversation."""
        with self.get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM conversation_messages
                WHERE conversation_id = ?
                ORDER BY timestamp DESC LIMIT ?
            """, (conversation_id, limit)).fetchall()

            messages = []
            for row in rows:
                messages.append(ConversationMessage(
                    id=row['id'], conversation_id=row['conversation_id'],
                    role=row['role'], content=row['content'],
                    timestamp=row['timestamp'],
                    chunks_used=json.loads(row['chunks_used'] or '[]'),
                    chunk_scores=json.loads(row['chunk_scores'] or '[]')
                ))

            return list(reversed(messages))

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def add_query(self, query: Query) -> str:
        """Add a query record."""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO queries
                (id, organization_id, conversation_id, user_id, query_text, response_text,
                 sources, chunks_used, chunk_scores, model_used, tokens_used, response_time_ms,
                 feedback, feedback_score, feedback_comment, is_good_example, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                query.id, query.organization_id, query.conversation_id, query.user_id,
                query.question, query.answer,
                json.dumps(query.sources) if query.sources else None,
                json.dumps(query.chunks_used), json.dumps(query.chunk_scores),
                query.model_used, query.tokens_used, query.response_time_ms,
                query.feedback, query.feedback_score, query.feedback_comment,
                1 if query.is_good_example else 0, query.created_at
            ))
        return query.id

    def get_query(self, query_id: str) -> Optional[Query]:
        """Get a query by ID."""
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM queries WHERE id = ?", (query_id,)).fetchone()
            if row:
                return self._row_to_query(row)
        return None

    def update_query_feedback(self, query_id: str, feedback: str, score: int = None, comment: str = None):
        """Update feedback for a query."""
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE queries SET feedback = ?, feedback_score = ?, feedback_comment = ?
                WHERE id = ?
            """, (feedback, score, comment, query_id))

            # If negative feedback, record as knowledge gap
            if feedback == 'negative':
                row = conn.execute("SELECT * FROM queries WHERE id = ?", (query_id,)).fetchone()
                if row:
                    self._record_knowledge_gap(
                        conn, row['organization_id'], row['query_text'], 'negative_feedback'
                    )

    def mark_as_good_example(self, query_id: str, is_good: bool = True):
        """Mark a query as a good training example."""
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE queries SET is_good_example = ? WHERE id = ?",
                (1 if is_good else 0, query_id)
            )

    def get_queries(self, organization_id: str = None, limit: int = 100) -> List[Query]:
        """Get recent queries."""
        with self.get_connection() as conn:
            if organization_id:
                rows = conn.execute(
                    "SELECT * FROM queries WHERE organization_id = ? ORDER BY created_at DESC LIMIT ?",
                    (organization_id, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM queries ORDER BY created_at DESC LIMIT ?",
                    (limit,)
                ).fetchall()
            return [self._row_to_query(row) for row in rows]

    def _row_to_query(self, row) -> Query:
        return Query(
            id=row['id'], organization_id=row['organization_id'],
            conversation_id=row['conversation_id'], user_id=row['user_id'],
            question=row['query_text'], answer=row['response_text'],
            sources=json.loads(row['sources']) if row['sources'] else None,
            chunks_used=json.loads(row['chunks_used'] or '[]'),
            chunk_scores=json.loads(row['chunk_scores'] or '[]'),
            model_used=row['model_used'], tokens_used=row['tokens_used'],
            response_time_ms=row['response_time_ms'],
            feedback=row['feedback'], feedback_score=row['feedback_score'],
            feedback_comment=row['feedback_comment'],
            is_good_example=bool(row['is_good_example']),
            created_at=row['created_at']
        )

    # -------------------------------------------------------------------------
    # Direct Q&A
    # -------------------------------------------------------------------------

    def add_direct_qa(self, qa: DirectQA) -> str:
        """Add a direct Q&A entry."""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO direct_qa
                (id, organization_id, question, answer, category, tags, use_count, created_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                qa.id, qa.organization_id, qa.question, qa.answer, qa.category,
                json.dumps(qa.tags), qa.use_count, qa.created_by, qa.created_at
            ))
        return qa.id

    def get_all_direct_qa(self, organization_id: str = None) -> List[DirectQA]:
        """Get all direct Q&A entries."""
        with self.get_connection() as conn:
            if organization_id:
                rows = conn.execute(
                    "SELECT * FROM direct_qa WHERE organization_id = ? ORDER BY use_count DESC",
                    (organization_id,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM direct_qa ORDER BY use_count DESC").fetchall()
            return [self._row_to_direct_qa(row) for row in rows]

    def increment_qa_use_count(self, qa_id: str):
        """Increment use count for a Q&A pair."""
        with self.get_connection() as conn:
            conn.execute("UPDATE direct_qa SET use_count = use_count + 1 WHERE id = ?", (qa_id,))

    def delete_direct_qa(self, qa_id: str):
        """Delete a direct Q&A entry."""
        with self.get_connection() as conn:
            conn.execute("DELETE FROM direct_qa WHERE id = ?", (qa_id,))

    def _row_to_direct_qa(self, row) -> DirectQA:
        return DirectQA(
            id=row['id'], organization_id=row['organization_id'],
            question=row['question'], answer=row['answer'],
            category=row['category'],
            tags=json.loads(row['tags']) if row['tags'] else [],
            use_count=row['use_count'], created_by=row['created_by'],
            created_at=row['created_at']
        )

    # -------------------------------------------------------------------------
    # Knowledge Gaps
    # -------------------------------------------------------------------------

    def _record_knowledge_gap(self, conn, organization_id: str, query_text: str, reason: str):
        """Record or update a knowledge gap."""
        # Check if similar gap exists
        row = conn.execute(
            "SELECT id, occurrence_count FROM knowledge_gaps WHERE organization_id = ? AND query_text = ?",
            (organization_id, query_text)
        ).fetchone()

        if row:
            conn.execute(
                "UPDATE knowledge_gaps SET occurrence_count = occurrence_count + 1 WHERE id = ?",
                (row['id'],)
            )
        else:
            gap = KnowledgeGap(
                organization_id=organization_id,
                query_text=query_text,
                failure_reason=reason
            )
            conn.execute("""
                INSERT INTO knowledge_gaps
                (id, organization_id, query_text, failure_reason, occurrence_count,
                 suggested_action, resolved, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                gap.id, gap.organization_id, gap.query_text, gap.failure_reason,
                gap.occurrence_count, gap.suggested_action, 0, gap.created_at
            ))

    def record_knowledge_gap(self, organization_id: str, query_text: str, reason: str = "no_results"):
        """Record a knowledge gap (public method)."""
        with self.get_connection() as conn:
            self._record_knowledge_gap(conn, organization_id, query_text, reason)

    def get_knowledge_gaps(self, organization_id: str = None, resolved: bool = False, limit: int = 50) -> List[KnowledgeGap]:
        """Get knowledge gaps."""
        with self.get_connection() as conn:
            query = "SELECT * FROM knowledge_gaps WHERE resolved = ?"
            params = [1 if resolved else 0]

            if organization_id:
                query += " AND organization_id = ?"
                params.append(organization_id)

            query += " ORDER BY occurrence_count DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
            return [self._row_to_knowledge_gap(row) for row in rows]

    def resolve_knowledge_gap(self, gap_id: str, resolved_by: str = None):
        """Mark a knowledge gap as resolved."""
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE knowledge_gaps
                SET resolved = 1, resolved_by = ?, resolved_at = ?
                WHERE id = ?
            """, (resolved_by, datetime.utcnow().isoformat(), gap_id))

    def _row_to_knowledge_gap(self, row) -> KnowledgeGap:
        return KnowledgeGap(
            id=row['id'], organization_id=row['organization_id'],
            query_text=row['query_text'], failure_reason=row['failure_reason'],
            occurrence_count=row['occurrence_count'],
            suggested_action=row['suggested_action'],
            resolved=bool(row['resolved']), resolved_by=row['resolved_by'],
            resolved_at=row['resolved_at'], created_at=row['created_at']
        )

    # -------------------------------------------------------------------------
    # Stats & Analytics
    # -------------------------------------------------------------------------

    def get_stats(self, organization_id: str = None) -> Dict[str, Any]:
        """Get database statistics."""
        with self.get_connection() as conn:
            org_filter = "WHERE organization_id = ?" if organization_id else ""
            params = (organization_id,) if organization_id else ()

            items = conn.execute(f"SELECT COUNT(*) FROM knowledge_items {org_filter}", params).fetchone()[0]
            chunks = conn.execute(f"SELECT COUNT(*) FROM chunks {org_filter}", params).fetchone()[0]
            queries = conn.execute(f"SELECT COUNT(*) FROM queries {org_filter}", params).fetchone()[0]
            qa_direct = conn.execute(f"SELECT COUNT(*) FROM direct_qa {org_filter}", params).fetchone()[0]

            positive = conn.execute(
                f"SELECT COUNT(*) FROM queries {org_filter} {'AND' if organization_id else 'WHERE'} feedback = 'positive'",
                params
            ).fetchone()[0]
            negative = conn.execute(
                f"SELECT COUNT(*) FROM queries {org_filter} {'AND' if organization_id else 'WHERE'} feedback = 'negative'",
                params
            ).fetchone()[0]

            gaps = conn.execute(
                f"SELECT COUNT(*) FROM knowledge_gaps {org_filter} {'AND' if organization_id else 'WHERE'} resolved = 0",
                params
            ).fetchone()[0]

            conversations = conn.execute(f"SELECT COUNT(*) FROM conversations {org_filter}", params).fetchone()[0]

            return {
                "total_documents": items,
                "total_chunks": chunks,
                "total_queries": queries,
                "total_qa_pairs": qa_direct,
                "total_conversations": conversations,
                "positive_feedback": positive,
                "negative_feedback": negative,
                "knowledge_gaps": gaps,
                "satisfaction_rate": positive / (positive + negative) if (positive + negative) > 0 else None
            }

    def export_training_data(self, organization_id: str = None, positive_only: bool = True) -> List[Dict]:
        """Export query-response pairs for fine-tuning."""
        with self.get_connection() as conn:
            query = "SELECT * FROM queries WHERE 1=1"
            params = []

            if organization_id:
                query += " AND organization_id = ?"
                params.append(organization_id)
            if positive_only:
                query += " AND (feedback = 'positive' OR is_good_example = 1)"

            rows = conn.execute(query, params).fetchall()

            return [
                {
                    "messages": [
                        {"role": "user", "content": row['query_text']},
                        {"role": "assistant", "content": row['response_text']}
                    ],
                    "feedback": row['feedback'],
                    "chunks_used": json.loads(row['chunks_used'] or '[]')
                }
                for row in rows if row['response_text']
            ]


# Global database instance
db = Database()
