"""
Text chunking for semantic search.
Splits documents into searchable chunks with overlap.
"""

import re
from typing import List, Tuple
from dataclasses import dataclass

from ..config import config


@dataclass
class TextChunk:
    """A chunk of text with metadata."""
    content: str
    index: int
    section_title: str = None
    token_count: int = 0


def chunk_text(
    text: str,
    chunk_size: int = None,
    overlap: int = None
) -> List[TextChunk]:
    """
    Split text into chunks for embedding.

    Uses sentence-based splitting to avoid cutting mid-sentence.

    Args:
        text: The text to chunk
        chunk_size: Target chunk size in tokens (default from config)
        overlap: Overlap between chunks in tokens (default from config)

    Returns:
        List of TextChunk objects
    """
    chunk_size = chunk_size or config.CHUNK_SIZE
    overlap = overlap or config.CHUNK_OVERLAP

    # Split into sentences
    sentences = split_into_sentences(text)

    if not sentences:
        return []

    chunks = []
    current_chunk = []
    current_tokens = 0

    for sentence in sentences:
        sentence_tokens = estimate_tokens(sentence)

        # If single sentence is too long, split it
        if sentence_tokens > chunk_size:
            # Save current chunk first
            if current_chunk:
                chunk_text = " ".join(current_chunk)
                chunks.append(TextChunk(
                    content=chunk_text,
                    index=len(chunks),
                    token_count=current_tokens
                ))
                current_chunk = []
                current_tokens = 0

            # Split long sentence into smaller pieces
            sub_chunks = split_long_text(sentence, chunk_size)
            for sub in sub_chunks:
                chunks.append(TextChunk(
                    content=sub,
                    index=len(chunks),
                    token_count=estimate_tokens(sub)
                ))
            continue

        # Check if adding this sentence exceeds chunk size
        if current_tokens + sentence_tokens > chunk_size and current_chunk:
            # Save current chunk
            chunk_text = " ".join(current_chunk)
            chunks.append(TextChunk(
                content=chunk_text,
                index=len(chunks),
                token_count=current_tokens
            ))

            # Start new chunk with overlap
            overlap_sentences = get_overlap_sentences(current_chunk, overlap)
            current_chunk = overlap_sentences
            current_tokens = sum(estimate_tokens(s) for s in overlap_sentences)

        current_chunk.append(sentence)
        current_tokens += sentence_tokens

    # Don't forget the last chunk
    if current_chunk:
        chunk_text = " ".join(current_chunk)
        chunks.append(TextChunk(
            content=chunk_text,
            index=len(chunks),
            token_count=current_tokens
        ))

    return chunks


def chunk_with_sections(text: str, chunk_size: int = None) -> List[TextChunk]:
    """
    Chunk text while preserving section boundaries.

    Splits on markdown headers or other section markers.
    """
    chunk_size = chunk_size or config.CHUNK_SIZE

    # Split by headers
    sections = split_by_headers(text)

    chunks = []
    for section_title, section_content in sections:
        section_chunks = chunk_text(section_content, chunk_size)

        for chunk in section_chunks:
            chunk.section_title = section_title
            chunk.index = len(chunks)
            chunks.append(chunk)

    return chunks


def split_into_sentences(text: str) -> List[str]:
    """Split text into sentences."""
    # Simple sentence splitting
    # Handle common abbreviations to avoid false splits
    text = text.replace("Mr.", "Mr")
    text = text.replace("Mrs.", "Mrs")
    text = text.replace("Dr.", "Dr")
    text = text.replace("Prof.", "Prof")
    text = text.replace("Inc.", "Inc")
    text = text.replace("Ltd.", "Ltd")
    text = text.replace("e.g.", "eg")
    text = text.replace("i.e.", "ie")
    text = text.replace("etc.", "etc")

    # Split on sentence boundaries
    sentences = re.split(r'(?<=[.!?])\s+', text)

    # Clean up and filter empty sentences
    sentences = [s.strip() for s in sentences if s.strip()]

    return sentences


def split_by_headers(text: str) -> List[Tuple[str, str]]:
    """
    Split text by markdown headers.

    Returns list of (header, content) tuples.
    """
    # Pattern for markdown headers
    header_pattern = r'^(#{1,6})\s+(.+)$'

    sections = []
    current_header = "Introduction"
    current_content = []

    for line in text.split("\n"):
        match = re.match(header_pattern, line)
        if match:
            # Save previous section
            if current_content:
                sections.append((current_header, "\n".join(current_content)))

            current_header = match.group(2).strip()
            current_content = []
        else:
            current_content.append(line)

    # Save last section
    if current_content:
        sections.append((current_header, "\n".join(current_content)))

    return sections


def split_long_text(text: str, max_tokens: int) -> List[str]:
    """Split text that's too long for a single chunk."""
    words = text.split()
    chunks = []
    current = []
    current_tokens = 0

    for word in words:
        word_tokens = estimate_tokens(word)
        if current_tokens + word_tokens > max_tokens and current:
            chunks.append(" ".join(current))
            current = []
            current_tokens = 0

        current.append(word)
        current_tokens += word_tokens

    if current:
        chunks.append(" ".join(current))

    return chunks


def get_overlap_sentences(sentences: List[str], overlap_tokens: int) -> List[str]:
    """Get sentences for overlap from the end of a chunk."""
    overlap = []
    tokens = 0

    for sentence in reversed(sentences):
        sentence_tokens = estimate_tokens(sentence)
        if tokens + sentence_tokens > overlap_tokens:
            break
        overlap.insert(0, sentence)
        tokens += sentence_tokens

    return overlap


def estimate_tokens(text: str) -> int:
    """
    Estimate token count for text.

    Uses a simple approximation: ~4 characters per token.
    For more accuracy, use tiktoken.
    """
    return len(text) // 4 + 1


def count_tokens_tiktoken(text: str) -> int:
    """Count tokens using tiktoken (more accurate but requires dependency)."""
    try:
        import tiktoken
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except ImportError:
        return estimate_tokens(text)
