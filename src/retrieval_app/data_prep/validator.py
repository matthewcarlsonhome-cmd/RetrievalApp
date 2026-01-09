"""
Data Validation Module.

Ensures data quality at ingestion time - because garbage in, garbage out.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from retrieval_app.data_prep.chunker import Chunk


class ValidationSeverity(str, Enum):
    """Severity levels for validation issues."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """Represents a validation issue found in data."""
    severity: ValidationSeverity
    code: str
    message: str
    chunk_id: Optional[str] = None
    details: Optional[dict] = None


@dataclass
class ValidationResult:
    """Result of data validation."""
    is_valid: bool
    issues: list[ValidationIssue]
    stats: dict

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.ERROR]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]


class DataValidator:
    """
    Validates data quality for RAG systems.

    Catches issues early that would cause problems downstream:
    - Empty or near-empty chunks
    - Chunks that are too large
    - Low-quality content (too many special chars, encoding issues)
    - Duplicate content
    - Missing required metadata
    """

    def __init__(
        self,
        min_chunk_length: int = 50,
        max_chunk_length: int = 5000,
        min_word_ratio: float = 0.5,
        max_special_char_ratio: float = 0.3,
        required_metadata_fields: Optional[list[str]] = None
    ):
        self.min_chunk_length = min_chunk_length
        self.max_chunk_length = max_chunk_length
        self.min_word_ratio = min_word_ratio
        self.max_special_char_ratio = max_special_char_ratio
        self.required_metadata_fields = required_metadata_fields or []

    def validate_chunks(self, chunks: list[Chunk]) -> ValidationResult:
        """Validate a list of chunks."""
        issues: list[ValidationIssue] = []
        seen_content_hashes: set[str] = set()
        stats = {
            "total_chunks": len(chunks),
            "valid_chunks": 0,
            "total_characters": 0,
            "avg_chunk_length": 0,
            "duplicate_count": 0,
        }

        for chunk in chunks:
            chunk_issues = self._validate_single_chunk(chunk, seen_content_hashes)
            issues.extend(chunk_issues)

            if not any(i.severity == ValidationSeverity.ERROR for i in chunk_issues):
                stats["valid_chunks"] += 1

            stats["total_characters"] += len(chunk.content)

        if chunks:
            stats["avg_chunk_length"] = stats["total_characters"] / len(chunks)

        is_valid = not any(i.severity == ValidationSeverity.ERROR for i in issues)

        return ValidationResult(is_valid=is_valid, issues=issues, stats=stats)

    def _validate_single_chunk(
        self,
        chunk: Chunk,
        seen_hashes: set[str]
    ) -> list[ValidationIssue]:
        """Validate a single chunk."""
        issues = []

        if len(chunk.content) < self.min_chunk_length:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="CHUNK_TOO_SHORT",
                message=f"Chunk is too short ({len(chunk.content)} chars, min {self.min_chunk_length})",
                chunk_id=chunk.id
            ))

        if len(chunk.content) > self.max_chunk_length:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="CHUNK_TOO_LONG",
                message=f"Chunk is too long ({len(chunk.content)} chars, max {self.max_chunk_length})",
                chunk_id=chunk.id
            ))

        content_hash = hash(chunk.content.strip().lower())
        if content_hash in seen_hashes:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="DUPLICATE_CONTENT",
                message="Chunk content appears to be a duplicate",
                chunk_id=chunk.id
            ))
        seen_hashes.add(content_hash)

        word_chars = len(re.findall(r'\w', chunk.content))
        total_chars = len(chunk.content)
        if total_chars > 0 and word_chars / total_chars < self.min_word_ratio:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="LOW_WORD_RATIO",
                message=f"Chunk has low word character ratio ({word_chars/total_chars:.2f})",
                chunk_id=chunk.id
            ))

        special_chars = len(re.findall(r'[^\w\s]', chunk.content))
        if total_chars > 0 and special_chars / total_chars > self.max_special_char_ratio:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="HIGH_SPECIAL_CHAR_RATIO",
                message=f"Chunk has high special character ratio ({special_chars/total_chars:.2f})",
                chunk_id=chunk.id
            ))

        if self._has_encoding_issues(chunk.content):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="ENCODING_ISSUES",
                message="Chunk may have encoding issues (replacement characters found)",
                chunk_id=chunk.id
            ))

        for field in self.required_metadata_fields:
            if field not in chunk.metadata:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="MISSING_METADATA",
                    message=f"Required metadata field '{field}' is missing",
                    chunk_id=chunk.id
                ))

        if chunk.embedding is not None:
            if not chunk.embedding or len(chunk.embedding) == 0:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="INVALID_EMBEDDING",
                    message="Chunk has empty embedding",
                    chunk_id=chunk.id
                ))
            elif all(v == 0 for v in chunk.embedding):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="ZERO_EMBEDDING",
                    message="Chunk has all-zero embedding",
                    chunk_id=chunk.id
                ))

        return issues

    def _has_encoding_issues(self, text: str) -> bool:
        """Check for common encoding issues."""
        replacement_char = '\ufffd'
        if replacement_char in text:
            return True

        mojibake_patterns = [
            r'Ã¢â‚¬',
            r'â€',
            r'Ã©',
            r'Ã¨',
        ]
        for pattern in mojibake_patterns:
            if pattern in text:
                return True

        return False

    def validate_document(
        self,
        text: str,
        document_id: str
    ) -> ValidationResult:
        """Validate a raw document before chunking."""
        issues = []
        stats = {
            "document_id": document_id,
            "length": len(text),
            "line_count": text.count('\n') + 1,
            "word_count": len(text.split()),
        }

        if len(text.strip()) == 0:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="EMPTY_DOCUMENT",
                message="Document is empty"
            ))

        if len(text) < 100:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="SHORT_DOCUMENT",
                message=f"Document is very short ({len(text)} chars)"
            ))

        if self._has_encoding_issues(text):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="DOCUMENT_ENCODING_ISSUES",
                message="Document may have encoding issues"
            ))

        is_valid = not any(i.severity == ValidationSeverity.ERROR for i in issues)
        return ValidationResult(is_valid=is_valid, issues=issues, stats=stats)
