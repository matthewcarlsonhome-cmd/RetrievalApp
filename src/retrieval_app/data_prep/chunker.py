"""
Document Chunking Module.

Implements multiple chunking strategies because "if the foundation is sloppy,
nothing downstream can save you."
"""

import re
import hashlib
from dataclasses import dataclass, field
from typing import Optional
from abc import ABC, abstractmethod

from retrieval_app.core.config import ChunkingConfig, ChunkingStrategy


@dataclass
class Chunk:
    """Represents a document chunk with metadata."""
    id: str
    content: str
    document_id: str
    chunk_index: int
    start_char: int
    end_char: int
    metadata: dict = field(default_factory=dict)
    embedding: Optional[list[float]] = None

    @property
    def token_estimate(self) -> int:
        """Rough estimate of tokens (4 chars per token)."""
        return len(self.content) // 4

    def __hash__(self) -> int:
        return hash(self.id)


class ChunkingStrategyBase(ABC):
    """Base class for chunking strategies."""

    @abstractmethod
    def chunk(self, text: str, document_id: str, metadata: dict) -> list[Chunk]:
        """Split text into chunks."""
        pass

    def _generate_chunk_id(self, document_id: str, content: str, index: int) -> str:
        """Generate a unique ID for a chunk."""
        hash_input = f"{document_id}:{index}:{content[:100]}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]


class FixedSizeChunker(ChunkingStrategyBase):
    """Simple fixed-size chunking with overlap."""

    def __init__(self, chunk_size: int = 512, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str, document_id: str, metadata: dict) -> list[Chunk]:
        chunks = []
        start = 0
        index = 0

        while start < len(text):
            end = start + self.chunk_size
            chunk_text = text[start:end]

            if chunk_text.strip():
                chunk_id = self._generate_chunk_id(document_id, chunk_text, index)
                chunks.append(Chunk(
                    id=chunk_id,
                    content=chunk_text,
                    document_id=document_id,
                    chunk_index=index,
                    start_char=start,
                    end_char=min(end, len(text)),
                    metadata=metadata.copy()
                ))
                index += 1

            start = end - self.overlap
            if start >= len(text):
                break

        return chunks


class SentenceChunker(ChunkingStrategyBase):
    """Chunk by sentences, respecting natural boundaries."""

    def __init__(self, target_size: int = 512, min_size: int = 100):
        self.target_size = target_size
        self.min_size = min_size
        self.sentence_pattern = re.compile(r'(?<=[.!?])\s+')

    def chunk(self, text: str, document_id: str, metadata: dict) -> list[Chunk]:
        sentences = self.sentence_pattern.split(text)
        chunks = []
        current_chunk = []
        current_length = 0
        chunk_start = 0
        index = 0
        char_pos = 0

        for sentence in sentences:
            sentence_length = len(sentence)

            if current_length + sentence_length > self.target_size and current_chunk:
                chunk_text = ' '.join(current_chunk)
                if len(chunk_text) >= self.min_size:
                    chunk_id = self._generate_chunk_id(document_id, chunk_text, index)
                    chunks.append(Chunk(
                        id=chunk_id,
                        content=chunk_text,
                        document_id=document_id,
                        chunk_index=index,
                        start_char=chunk_start,
                        end_char=char_pos,
                        metadata=metadata.copy()
                    ))
                    index += 1
                current_chunk = []
                current_length = 0
                chunk_start = char_pos

            current_chunk.append(sentence)
            current_length += sentence_length
            char_pos += sentence_length + 1

        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            if len(chunk_text) >= self.min_size or not chunks:
                chunk_id = self._generate_chunk_id(document_id, chunk_text, index)
                chunks.append(Chunk(
                    id=chunk_id,
                    content=chunk_text,
                    document_id=document_id,
                    chunk_index=index,
                    start_char=chunk_start,
                    end_char=len(text),
                    metadata=metadata.copy()
                ))

        return chunks


class RecursiveChunker(ChunkingStrategyBase):
    """
    Recursive chunking that tries to split on natural boundaries.
    Attempts splits in order: paragraphs -> sentences -> words -> characters.
    """

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        min_chunk_size: int = 100
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.separators = ["\n\n", "\n", ". ", " ", ""]

    def chunk(self, text: str, document_id: str, metadata: dict) -> list[Chunk]:
        chunks = self._recursive_split(text, self.separators)
        result = []

        char_pos = 0
        for index, chunk_text in enumerate(chunks):
            chunk_text = chunk_text.strip()
            if chunk_text:
                chunk_id = self._generate_chunk_id(document_id, chunk_text, index)
                start_pos = text.find(chunk_text, char_pos)
                if start_pos == -1:
                    start_pos = char_pos
                end_pos = start_pos + len(chunk_text)

                result.append(Chunk(
                    id=chunk_id,
                    content=chunk_text,
                    document_id=document_id,
                    chunk_index=index,
                    start_char=start_pos,
                    end_char=end_pos,
                    metadata=metadata.copy()
                ))
                char_pos = end_pos

        return result

    def _recursive_split(self, text: str, separators: list[str]) -> list[str]:
        """Recursively split text using progressively finer separators."""
        if not text:
            return []

        if len(text) <= self.chunk_size:
            return [text]

        if not separators:
            return [text[i:i + self.chunk_size]
                    for i in range(0, len(text), self.chunk_size - self.chunk_overlap)]

        separator = separators[0]
        remaining_separators = separators[1:]

        if separator == "":
            return [text[i:i + self.chunk_size]
                    for i in range(0, len(text), self.chunk_size - self.chunk_overlap)]

        splits = text.split(separator)
        chunks = []
        current_chunk = []
        current_length = 0

        for split in splits:
            split_length = len(split) + len(separator)

            if current_length + split_length > self.chunk_size:
                if current_chunk:
                    merged = separator.join(current_chunk)
                    if len(merged) > self.chunk_size:
                        chunks.extend(self._recursive_split(merged, remaining_separators))
                    else:
                        chunks.append(merged)
                current_chunk = [split]
                current_length = len(split)
            else:
                current_chunk.append(split)
                current_length += split_length

        if current_chunk:
            merged = separator.join(current_chunk)
            if len(merged) > self.chunk_size:
                chunks.extend(self._recursive_split(merged, remaining_separators))
            else:
                chunks.append(merged)

        return chunks


class SemanticChunker(ChunkingStrategyBase):
    """
    Semantic chunking based on content similarity.
    Groups sentences with similar topics together.
    """

    def __init__(
        self,
        embedding_fn: Optional[callable] = None,
        similarity_threshold: float = 0.5,
        max_chunk_size: int = 1000
    ):
        self.embedding_fn = embedding_fn
        self.similarity_threshold = similarity_threshold
        self.max_chunk_size = max_chunk_size
        self.sentence_pattern = re.compile(r'(?<=[.!?])\s+')

    def chunk(self, text: str, document_id: str, metadata: dict) -> list[Chunk]:
        sentences = self.sentence_pattern.split(text)
        if not sentences:
            return []

        if self.embedding_fn is None:
            chunker = SentenceChunker(target_size=self.max_chunk_size)
            return chunker.chunk(text, document_id, metadata)

        sentence_embeddings = [self.embedding_fn(s) for s in sentences]
        chunks = []
        current_group = [sentences[0]]
        current_embedding = sentence_embeddings[0]
        chunk_start = 0
        char_pos = len(sentences[0])
        index = 0

        for i in range(1, len(sentences)):
            similarity = self._cosine_similarity(current_embedding, sentence_embeddings[i])
            current_length = sum(len(s) for s in current_group)

            if similarity < self.similarity_threshold or current_length > self.max_chunk_size:
                chunk_text = ' '.join(current_group)
                chunk_id = self._generate_chunk_id(document_id, chunk_text, index)
                chunks.append(Chunk(
                    id=chunk_id,
                    content=chunk_text,
                    document_id=document_id,
                    chunk_index=index,
                    start_char=chunk_start,
                    end_char=char_pos,
                    metadata=metadata.copy()
                ))
                index += 1
                current_group = [sentences[i]]
                current_embedding = sentence_embeddings[i]
                chunk_start = char_pos
            else:
                current_group.append(sentences[i])
                n = len(current_group)
                current_embedding = [
                    (current_embedding[j] * (n - 1) + sentence_embeddings[i][j]) / n
                    for j in range(len(current_embedding))
                ]

            char_pos += len(sentences[i]) + 1

        if current_group:
            chunk_text = ' '.join(current_group)
            chunk_id = self._generate_chunk_id(document_id, chunk_text, index)
            chunks.append(Chunk(
                id=chunk_id,
                content=chunk_text,
                document_id=document_id,
                chunk_index=index,
                start_char=chunk_start,
                end_char=len(text),
                metadata=metadata.copy()
            ))

        return chunks

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot_product / (norm1 * norm2)


class DocumentChunker:
    """
    Main chunking interface that supports multiple strategies.

    Usage:
        chunker = DocumentChunker(config)
        chunks = chunker.chunk_document(text, doc_id, metadata)
    """

    def __init__(self, config: ChunkingConfig, embedding_fn: Optional[callable] = None):
        self.config = config
        self.embedding_fn = embedding_fn
        self._strategy = self._create_strategy()

    def _create_strategy(self) -> ChunkingStrategyBase:
        """Create the appropriate chunking strategy."""
        if self.config.strategy == ChunkingStrategy.FIXED_SIZE:
            return FixedSizeChunker(
                chunk_size=self.config.chunk_size,
                overlap=self.config.chunk_overlap
            )
        elif self.config.strategy == ChunkingStrategy.SENTENCE:
            return SentenceChunker(
                target_size=self.config.chunk_size,
                min_size=self.config.min_chunk_size
            )
        elif self.config.strategy == ChunkingStrategy.RECURSIVE:
            return RecursiveChunker(
                chunk_size=self.config.chunk_size,
                chunk_overlap=self.config.chunk_overlap,
                min_chunk_size=self.config.min_chunk_size
            )
        elif self.config.strategy == ChunkingStrategy.SEMANTIC:
            return SemanticChunker(
                embedding_fn=self.embedding_fn,
                max_chunk_size=self.config.max_chunk_size
            )
        else:
            raise ValueError(f"Unknown chunking strategy: {self.config.strategy}")

    def chunk_document(
        self,
        text: str,
        document_id: str,
        metadata: Optional[dict] = None
    ) -> list[Chunk]:
        """
        Chunk a document into smaller pieces.

        Args:
            text: The document text to chunk
            document_id: Unique identifier for the source document
            metadata: Optional metadata to attach to each chunk

        Returns:
            List of Chunk objects
        """
        if metadata is None:
            metadata = {}

        text = self._preprocess_text(text)
        chunks = self._strategy.chunk(text, document_id, metadata)
        chunks = self._post_process_chunks(chunks)

        return chunks

    def _preprocess_text(self, text: str) -> str:
        """Clean and normalize text before chunking."""
        text = re.sub(r'\r\n', '\n', text)
        text = re.sub(r'\r', '\n', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        return text.strip()

    def _post_process_chunks(self, chunks: list[Chunk]) -> list[Chunk]:
        """Apply post-processing to chunks."""
        processed = []
        for chunk in chunks:
            if len(chunk.content.strip()) < self.config.min_chunk_size:
                continue

            chunk.content = chunk.content.strip()
            chunk.metadata["char_count"] = len(chunk.content)
            chunk.metadata["token_estimate"] = chunk.token_estimate
            processed.append(chunk)

        return processed
