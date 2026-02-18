"""
Text chunking for semantic search.
Supports multiple chunking strategies with configurable parameters.
"""

import re
from typing import List, Tuple, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from ..config import config


class ChunkingStrategy(Enum):
    """Available chunking strategies."""
    SENTENCE = "sentence"       # Split on sentence boundaries (default)
    FIXED = "fixed"            # Fixed token-count chunks
    PARAGRAPH = "paragraph"    # Split on paragraph boundaries
    SEMANTIC = "semantic"      # Group semantically related content
    HYBRID = "hybrid"          # Combination of strategies
    SLIDING_WINDOW = "sliding" # Overlapping sliding window


@dataclass
class TextChunk:
    """A chunk of text with metadata."""
    content: str
    index: int
    section_title: str = None
    token_count: int = 0
    strategy: str = "sentence"
    start_char: int = 0  # For citation linking
    end_char: int = 0    # For citation linking


@dataclass
class ChunkingConfig:
    """Configuration for chunking behavior."""
    strategy: ChunkingStrategy = ChunkingStrategy.SENTENCE
    chunk_size: int = 500       # Target chunk size in tokens
    chunk_overlap: int = 50     # Overlap between chunks in tokens
    min_chunk_size: int = 100   # Minimum chunk size
    max_chunk_size: int = 1000  # Maximum chunk size
    respect_sections: bool = True  # Preserve section boundaries
    include_metadata: bool = True  # Add section titles to chunks

    @classmethod
    def from_preset(cls, preset: str) -> "ChunkingConfig":
        """Create config from a preset name."""
        presets = {
            "default": cls(),
            "faq": cls(
                strategy=ChunkingStrategy.PARAGRAPH,
                chunk_size=200,
                chunk_overlap=20,
                min_chunk_size=50
            ),
            "technical": cls(
                strategy=ChunkingStrategy.SENTENCE,
                chunk_size=600,
                chunk_overlap=100,
                respect_sections=True
            ),
            "legal": cls(
                strategy=ChunkingStrategy.PARAGRAPH,
                chunk_size=1000,
                chunk_overlap=150,
                respect_sections=True
            ),
            "conversation": cls(
                strategy=ChunkingStrategy.SLIDING_WINDOW,
                chunk_size=400,
                chunk_overlap=100
            ),
            "dense": cls(
                strategy=ChunkingStrategy.FIXED,
                chunk_size=256,
                chunk_overlap=32
            )
        }
        return presets.get(preset, cls())


def chunk_text(
    text: str,
    chunk_size: int = None,
    overlap: int = None,
    strategy: str = None,
    config_obj: ChunkingConfig = None
) -> List[TextChunk]:
    """
    Split text into chunks for embedding.

    Args:
        text: The text to chunk
        chunk_size: Target chunk size in tokens (default from config)
        overlap: Overlap between chunks in tokens (default from config)
        strategy: Chunking strategy name (sentence, fixed, paragraph, etc.)
        config_obj: Full ChunkingConfig object (overrides other params)

    Returns:
        List of TextChunk objects
    """
    if config_obj is None:
        config_obj = ChunkingConfig(
            chunk_size=chunk_size or config.CHUNK_SIZE,
            chunk_overlap=overlap or config.CHUNK_OVERLAP,
            strategy=ChunkingStrategy(strategy) if strategy else ChunkingStrategy.SENTENCE
        )

    strategy_func = _get_strategy_function(config_obj.strategy)
    return strategy_func(text, config_obj)


def chunk_with_sections(
    text: str,
    chunk_size: int = None,
    strategy: str = None,
    config_obj: ChunkingConfig = None
) -> List[TextChunk]:
    """
    Chunk text while preserving section boundaries.

    Splits on markdown headers or other section markers.
    """
    if config_obj is None:
        config_obj = ChunkingConfig(
            chunk_size=chunk_size or config.CHUNK_SIZE,
            chunk_overlap=config.CHUNK_OVERLAP,
            strategy=ChunkingStrategy(strategy) if strategy else ChunkingStrategy.SENTENCE,
            respect_sections=True
        )

    # Split by headers
    sections = split_by_headers(text)

    chunks = []
    char_offset = 0

    for section_title, section_content in sections:
        # Track character position for citations
        section_start = text.find(section_content, char_offset)
        if section_start == -1:
            section_start = char_offset

        section_chunks = chunk_text(section_content, config_obj=config_obj)

        for chunk in section_chunks:
            chunk.section_title = section_title
            chunk.index = len(chunks)
            chunk.start_char = section_start + chunk.start_char
            chunk.end_char = section_start + chunk.end_char
            chunks.append(chunk)

        char_offset = section_start + len(section_content)

    return chunks


# =============================================================================
# CHUNKING STRATEGIES
# =============================================================================

def _get_strategy_function(strategy: ChunkingStrategy) -> Callable:
    """Get the chunking function for a strategy."""
    strategies = {
        ChunkingStrategy.SENTENCE: _chunk_by_sentence,
        ChunkingStrategy.FIXED: _chunk_fixed_size,
        ChunkingStrategy.PARAGRAPH: _chunk_by_paragraph,
        ChunkingStrategy.SEMANTIC: _chunk_semantic,
        ChunkingStrategy.HYBRID: _chunk_hybrid,
        ChunkingStrategy.SLIDING_WINDOW: _chunk_sliding_window,
    }
    return strategies.get(strategy, _chunk_by_sentence)


def _chunk_by_sentence(text: str, cfg: ChunkingConfig) -> List[TextChunk]:
    """Chunk by sentence boundaries (default strategy)."""
    sentences = split_into_sentences(text)

    if not sentences:
        return []

    chunks = []
    current_chunk = []
    current_tokens = 0
    chunk_start = 0
    current_pos = 0

    for sentence in sentences:
        sentence_tokens = estimate_tokens(sentence)
        sentence_start = text.find(sentence, current_pos)
        if sentence_start == -1:
            sentence_start = current_pos

        # If single sentence is too long, split it
        if sentence_tokens > cfg.max_chunk_size:
            # Save current chunk first
            if current_chunk:
                chunk_text_content = " ".join(current_chunk)
                chunks.append(TextChunk(
                    content=chunk_text_content,
                    index=len(chunks),
                    token_count=current_tokens,
                    strategy="sentence",
                    start_char=chunk_start,
                    end_char=current_pos
                ))
                current_chunk = []
                current_tokens = 0

            # Split long sentence into smaller pieces
            sub_chunks = split_long_text(sentence, cfg.chunk_size)
            sub_pos = sentence_start
            for sub in sub_chunks:
                chunks.append(TextChunk(
                    content=sub,
                    index=len(chunks),
                    token_count=estimate_tokens(sub),
                    strategy="sentence",
                    start_char=sub_pos,
                    end_char=sub_pos + len(sub)
                ))
                sub_pos += len(sub)

            chunk_start = sub_pos
            current_pos = sentence_start + len(sentence)
            continue

        # Check if adding this sentence exceeds chunk size
        if current_tokens + sentence_tokens > cfg.chunk_size and current_chunk:
            # Save current chunk
            chunk_text_content = " ".join(current_chunk)
            chunks.append(TextChunk(
                content=chunk_text_content,
                index=len(chunks),
                token_count=current_tokens,
                strategy="sentence",
                start_char=chunk_start,
                end_char=current_pos
            ))

            # Start new chunk with overlap
            overlap_sentences = get_overlap_sentences(current_chunk, cfg.chunk_overlap)
            current_chunk = overlap_sentences
            current_tokens = sum(estimate_tokens(s) for s in overlap_sentences)
            chunk_start = sentence_start - sum(len(s) + 1 for s in overlap_sentences)

        current_chunk.append(sentence)
        current_tokens += sentence_tokens
        current_pos = sentence_start + len(sentence)

    # Don't forget the last chunk
    if current_chunk:
        chunk_text_content = " ".join(current_chunk)
        chunks.append(TextChunk(
            content=chunk_text_content,
            index=len(chunks),
            token_count=current_tokens,
            strategy="sentence",
            start_char=chunk_start,
            end_char=len(text)
        ))

    return chunks


def _chunk_fixed_size(text: str, cfg: ChunkingConfig) -> List[TextChunk]:
    """Chunk by fixed token count (simple, fast)."""
    words = text.split()
    chunks = []
    current_chunk = []
    current_tokens = 0
    current_pos = 0

    for word in words:
        word_tokens = estimate_tokens(word)
        word_start = text.find(word, current_pos)
        if word_start == -1:
            word_start = current_pos

        if current_tokens + word_tokens > cfg.chunk_size and current_chunk:
            chunk_text_content = " ".join(current_chunk)
            chunks.append(TextChunk(
                content=chunk_text_content,
                index=len(chunks),
                token_count=current_tokens,
                strategy="fixed",
                start_char=current_pos - len(chunk_text_content),
                end_char=current_pos
            ))

            # Overlap
            overlap_words = current_chunk[-cfg.chunk_overlap // 4:] if cfg.chunk_overlap else []
            current_chunk = overlap_words
            current_tokens = sum(estimate_tokens(w) for w in overlap_words)

        current_chunk.append(word)
        current_tokens += word_tokens
        current_pos = word_start + len(word)

    if current_chunk:
        chunk_text_content = " ".join(current_chunk)
        chunks.append(TextChunk(
            content=chunk_text_content,
            index=len(chunks),
            token_count=current_tokens,
            strategy="fixed",
            start_char=len(text) - len(chunk_text_content),
            end_char=len(text)
        ))

    return chunks


def _chunk_by_paragraph(text: str, cfg: ChunkingConfig) -> List[TextChunk]:
    """Chunk by paragraph boundaries."""
    # Split on double newlines (paragraphs)
    paragraphs = re.split(r'\n\s*\n', text)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    chunks = []
    current_chunk = []
    current_tokens = 0
    current_pos = 0

    for para in paragraphs:
        para_tokens = estimate_tokens(para)
        para_start = text.find(para, current_pos)
        if para_start == -1:
            para_start = current_pos

        # If single paragraph is too long, use sentence chunking
        if para_tokens > cfg.max_chunk_size:
            # Save current chunk first
            if current_chunk:
                chunk_text_content = "\n\n".join(current_chunk)
                chunks.append(TextChunk(
                    content=chunk_text_content,
                    index=len(chunks),
                    token_count=current_tokens,
                    strategy="paragraph",
                    start_char=current_pos,
                    end_char=para_start
                ))
                current_chunk = []
                current_tokens = 0

            # Split paragraph by sentences
            sub_chunks = _chunk_by_sentence(para, cfg)
            for sub in sub_chunks:
                sub.start_char += para_start
                sub.end_char += para_start
                sub.index = len(chunks)
                chunks.append(sub)

            current_pos = para_start + len(para)
            continue

        # Check if adding paragraph exceeds limit
        if current_tokens + para_tokens > cfg.chunk_size and current_chunk:
            chunk_text_content = "\n\n".join(current_chunk)
            chunks.append(TextChunk(
                content=chunk_text_content,
                index=len(chunks),
                token_count=current_tokens,
                strategy="paragraph",
                start_char=current_pos,
                end_char=para_start
            ))
            current_chunk = []
            current_tokens = 0

        current_chunk.append(para)
        current_tokens += para_tokens
        current_pos = para_start + len(para)

    if current_chunk:
        chunk_text_content = "\n\n".join(current_chunk)
        chunks.append(TextChunk(
            content=chunk_text_content,
            index=len(chunks),
            token_count=current_tokens,
            strategy="paragraph",
            start_char=len(text) - len(chunk_text_content),
            end_char=len(text)
        ))

    return chunks


def _chunk_semantic(text: str, cfg: ChunkingConfig) -> List[TextChunk]:
    """
    Semantic chunking - group related content together.
    Uses topic boundaries and discourse markers.
    """
    # Identify semantic boundaries
    boundaries = _find_semantic_boundaries(text)

    if not boundaries:
        return _chunk_by_sentence(text, cfg)

    chunks = []
    current_pos = 0

    for boundary_pos in boundaries:
        segment = text[current_pos:boundary_pos].strip()
        if segment:
            segment_tokens = estimate_tokens(segment)

            # If segment is too large, sub-chunk it
            if segment_tokens > cfg.max_chunk_size:
                sub_chunks = _chunk_by_sentence(segment, cfg)
                for sub in sub_chunks:
                    sub.start_char += current_pos
                    sub.end_char += current_pos
                    sub.index = len(chunks)
                    sub.strategy = "semantic"
                    chunks.append(sub)
            else:
                chunks.append(TextChunk(
                    content=segment,
                    index=len(chunks),
                    token_count=segment_tokens,
                    strategy="semantic",
                    start_char=current_pos,
                    end_char=boundary_pos
                ))

        current_pos = boundary_pos

    # Handle remaining text
    if current_pos < len(text):
        segment = text[current_pos:].strip()
        if segment:
            chunks.append(TextChunk(
                content=segment,
                index=len(chunks),
                token_count=estimate_tokens(segment),
                strategy="semantic",
                start_char=current_pos,
                end_char=len(text)
            ))

    return chunks


def _find_semantic_boundaries(text: str) -> List[int]:
    """Find semantic boundaries in text."""
    boundaries = []

    # Discourse markers that indicate topic shifts
    markers = [
        r'\n\s*(?:However|Moreover|Furthermore|In addition|On the other hand|'
        r'Nevertheless|Consequently|Therefore|Thus|Hence|Meanwhile|'
        r'In contrast|Similarly|Likewise|For example|For instance|'
        r'In conclusion|To summarize|Finally|First|Second|Third|'
        r'Next|Then|After that|Before this)',
        r'\n\s*\d+\.\s',  # Numbered lists
        r'\n\s*[-•*]\s',  # Bullet points
        r'\n\s*#{1,6}\s',  # Headers
    ]

    for pattern in markers:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            boundaries.append(match.start())

    # Also add paragraph boundaries
    for match in re.finditer(r'\n\s*\n', text):
        boundaries.append(match.start())

    # Sort and dedupe
    boundaries = sorted(set(boundaries))

    return boundaries


def _chunk_hybrid(text: str, cfg: ChunkingConfig) -> List[TextChunk]:
    """
    Hybrid chunking - combines multiple strategies.
    First splits by sections, then by semantic boundaries, then by sentences.
    """
    # First, identify sections
    sections = split_by_headers(text)

    chunks = []

    for section_title, section_content in sections:
        section_start = text.find(section_content)
        if section_start == -1:
            section_start = 0

        # Try semantic chunking first
        semantic_chunks = _chunk_semantic(section_content, cfg)

        for chunk in semantic_chunks:
            chunk.section_title = section_title
            chunk.start_char += section_start
            chunk.end_char += section_start
            chunk.index = len(chunks)
            chunk.strategy = "hybrid"
            chunks.append(chunk)

    return chunks


def _chunk_sliding_window(text: str, cfg: ChunkingConfig) -> List[TextChunk]:
    """
    Sliding window chunking with configurable overlap.
    Good for ensuring no information is lost at boundaries.
    """
    words = text.split()
    total_words = len(words)

    if total_words == 0:
        return []

    # Calculate step size (chunk_size - overlap)
    words_per_chunk = cfg.chunk_size // 4  # Rough: 4 chars per token
    overlap_words = cfg.chunk_overlap // 4
    step = max(1, words_per_chunk - overlap_words)

    chunks = []
    current_pos = 0

    for i in range(0, total_words, step):
        chunk_words = words[i:i + words_per_chunk]
        chunk_content = " ".join(chunk_words)

        # Find position in original text
        start_pos = text.find(chunk_words[0], current_pos) if chunk_words else current_pos
        if start_pos == -1:
            start_pos = current_pos
        end_pos = start_pos + len(chunk_content)

        chunks.append(TextChunk(
            content=chunk_content,
            index=len(chunks),
            token_count=estimate_tokens(chunk_content),
            strategy="sliding",
            start_char=start_pos,
            end_char=end_pos
        ))

        current_pos = start_pos + len(" ".join(words[i:i + step]))

        # Stop if we've covered the text
        if i + words_per_chunk >= total_words:
            break

    return chunks


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def split_into_sentences(text: str) -> List[str]:
    """Split text into sentences."""
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
    text = text.replace("vs.", "vs")
    text = text.replace("Sr.", "Sr")
    text = text.replace("Jr.", "Jr")

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


# =============================================================================
# PRESET FUNCTIONS FOR COMMON USE CASES
# =============================================================================

def chunk_for_faq(text: str) -> List[TextChunk]:
    """Optimized chunking for FAQ-style content."""
    cfg = ChunkingConfig.from_preset("faq")
    return chunk_text(text, config_obj=cfg)


def chunk_for_technical_docs(text: str) -> List[TextChunk]:
    """Optimized chunking for technical documentation."""
    cfg = ChunkingConfig.from_preset("technical")
    return chunk_with_sections(text, config_obj=cfg)


def chunk_for_legal(text: str) -> List[TextChunk]:
    """Optimized chunking for legal documents."""
    cfg = ChunkingConfig.from_preset("legal")
    return chunk_with_sections(text, config_obj=cfg)


def chunk_for_conversation(text: str) -> List[TextChunk]:
    """Optimized chunking for conversational content."""
    cfg = ChunkingConfig.from_preset("conversation")
    return chunk_text(text, config_obj=cfg)


def get_available_strategies() -> List[dict]:
    """Get list of available chunking strategies with descriptions."""
    return [
        {
            "id": "sentence",
            "name": "Sentence-based",
            "description": "Splits on sentence boundaries. Best for general content.",
            "recommended_for": ["articles", "blogs", "general documentation"]
        },
        {
            "id": "fixed",
            "name": "Fixed Size",
            "description": "Fixed token-count chunks. Fast and predictable.",
            "recommended_for": ["large documents", "batch processing"]
        },
        {
            "id": "paragraph",
            "name": "Paragraph-based",
            "description": "Preserves paragraph boundaries. Good for structured text.",
            "recommended_for": ["reports", "structured documents", "FAQs"]
        },
        {
            "id": "semantic",
            "name": "Semantic",
            "description": "Groups related content using topic markers.",
            "recommended_for": ["technical docs", "tutorials", "guides"]
        },
        {
            "id": "hybrid",
            "name": "Hybrid",
            "description": "Combines section, semantic, and sentence splitting.",
            "recommended_for": ["complex documents", "mixed content"]
        },
        {
            "id": "sliding",
            "name": "Sliding Window",
            "description": "Overlapping windows ensure no boundary information loss.",
            "recommended_for": ["conversations", "transcripts", "continuous text"]
        }
    ]


def get_recommended_chunk_size(document_type: str) -> dict:
    """Get recommended chunk size for a document type."""
    recommendations = {
        "faq": {"chunk_size": 200, "overlap": 20, "strategy": "paragraph"},
        "technical": {"chunk_size": 600, "overlap": 100, "strategy": "sentence"},
        "legal": {"chunk_size": 1000, "overlap": 150, "strategy": "paragraph"},
        "email": {"chunk_size": 300, "overlap": 50, "strategy": "paragraph"},
        "conversation": {"chunk_size": 400, "overlap": 100, "strategy": "sliding"},
        "spreadsheet": {"chunk_size": 500, "overlap": 50, "strategy": "fixed"},
        "presentation": {"chunk_size": 300, "overlap": 30, "strategy": "paragraph"},
        "default": {"chunk_size": 500, "overlap": 50, "strategy": "sentence"}
    }
    return recommendations.get(document_type, recommendations["default"])
