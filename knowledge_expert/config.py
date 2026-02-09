"""
Configuration for Knowledge Expert application.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Config:
    """Application configuration."""

    # Paths
    BASE_DIR: Path = field(default_factory=lambda: Path(__file__).parent.parent)
    DATA_DIR: Path = field(default_factory=lambda: Path(__file__).parent.parent / "data")
    KNOWLEDGE_BASE_DIR: Path = field(default_factory=lambda: Path(__file__).parent.parent / "data" / "knowledge_base")
    CHROMA_DB_DIR: Path = field(default_factory=lambda: Path(__file__).parent.parent / "data" / "chroma_db")
    SQLITE_DB_PATH: Path = field(default_factory=lambda: Path(__file__).parent.parent / "data" / "knowledge_expert.db")

    # Flask
    SECRET_KEY: str = field(default_factory=lambda: os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production"))
    DEBUG: bool = field(default_factory=lambda: os.environ.get("FLASK_DEBUG", "0") == "1")

    # Upload limits
    MAX_UPLOAD_SIZE_MB: int = field(default_factory=lambda: int(os.environ.get("MAX_UPLOAD_SIZE_MB", "10")))
    ALLOWED_EXTENSIONS: set = field(default_factory=lambda: {".pdf", ".docx", ".md", ".txt", ".html"})

    # Embedding model
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384

    # Chunking
    CHUNK_SIZE: int = 500  # tokens
    CHUNK_OVERLAP: int = 50  # tokens

    # LLM
    LLM_PROVIDER: str = field(default_factory=lambda: "anthropic" if os.environ.get("ANTHROPIC_API_KEY") else "openai")
    ANTHROPIC_API_KEY: Optional[str] = field(default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY"))
    OPENAI_API_KEY: Optional[str] = field(default_factory=lambda: os.environ.get("OPENAI_API_KEY"))
    LLM_MODEL: str = field(default_factory=lambda: os.environ.get("LLM_MODEL", "claude-3-5-sonnet-20241022"))
    LLM_MAX_TOKENS: int = 1024
    LLM_TEMPERATURE: float = 0.1

    # Retrieval
    TOP_K_RESULTS: int = 5
    MIN_RELEVANCE_SCORE: float = 0.3

    # Content moderation
    ENABLE_MODERATION: bool = True


@dataclass
class ContentModeration:
    """Content moderation configuration."""

    # Blocked words (profanity, slurs, etc.)
    BLOCKED_WORDS: List[str] = field(default_factory=lambda: [
        # Add profanity list here - keeping minimal for example
        "fuck", "shit", "ass", "bitch", "damn", "crap",
        "bastard", "hell", "piss", "dick", "cock", "pussy",
    ])

    # Blocked topics
    BLOCKED_TOPICS: List[str] = field(default_factory=lambda: [
        "politics", "election", "democrat", "republican", "trump", "biden",
        "religion", "religious", "christian", "muslim", "jewish", "atheist",
        "porn", "pornography", "xxx", "adult content", "nsfw",
        "drugs", "cocaine", "heroin", "meth",
        "violence", "murder", "kill", "weapon",
    ])

    # Competitor names to avoid mentioning (customize per client)
    COMPETITORS: List[str] = field(default_factory=lambda: [
        # Add competitor names here
    ])

    # Response rules
    SYSTEM_RULES: str = """
IMPORTANT RULES:
1. Only answer based on the provided context. Never make up information.
2. If the answer is not in the context, say "I don't have information about that in my knowledge base."
3. Always maintain a professional, helpful tone.
4. Never use profanity or inappropriate language.
5. Never discuss politics, religion, or other sensitive topics.
6. Never provide medical, legal, or financial advice unless explicitly in the knowledge base.
7. Always cite your sources when providing information.
8. If asked about competitors, politely redirect to the company's own services.
"""


# Global config instance
config = Config()
moderation = ContentModeration()


def init_directories():
    """Create required directories if they don't exist."""
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    config.KNOWLEDGE_BASE_DIR.mkdir(parents=True, exist_ok=True)
    config.CHROMA_DB_DIR.mkdir(parents=True, exist_ok=True)


# Initialize directories on import
init_directories()
