"""Document ingestion package."""

from .parsers import parse_document, extract_text
from .chunker import chunk_text
from .embedder import EmbeddingGenerator
