"""
Document Processing Inspector Module.

=============================================================================
INNOVATION: VISIBILITY INTO THE DATA PREPARATION BLACK BOX
=============================================================================

The Problem (as stated by a senior engineer):
"You can't see what your parser actually did to that PDF table until you're
wondering why the model keeps citing garbage. Same with chunking strategy,
you pick some defaults, run it, and hope for the best without ever seeing
what the output looks like."

This module provides VISIBILITY at every transformation step:

1. PARSING INSPECTION
   - See exactly what was extracted from each document
   - Detect lost tables, images, formatting
   - Compare source vs extracted text

2. CHUNKING PREVIEW
   - Visual representation of chunk boundaries
   - Identify chunks that split sentences/paragraphs
   - Detect orphaned context (pronouns without antecedents)

3. QUALITY SCORING
   - Automatic detection of problematic chunks
   - Coherence scoring (does chunk make sense standalone?)
   - Context dependency detection

4. TRANSFORMATION DIFF
   - Side-by-side comparison at each pipeline stage
   - Highlight what was lost/changed
   - Quantify information loss

The key insight: "Being able to preview what your docs look like after each
transformation, BEFORE they hit the vector store."

=============================================================================
USAGE EXAMPLE
=============================================================================

    inspector = DocumentInspector()

    # Inspect a document through the full pipeline
    report = inspector.inspect_document(
        raw_text=pdf_text,
        chunker=my_chunker,
        document_id="doc_001",
    )

    # Check for problems BEFORE indexing
    if report.has_critical_issues:
        print("WARNING: Document has quality issues!")
        for issue in report.issues:
            print(f"  - {issue}")

    # Visual preview of chunks
    for chunk_preview in report.chunk_previews:
        print(f"Chunk {chunk_preview.index}:")
        print(f"  Quality: {chunk_preview.quality_score:.2f}")
        print(f"  Issues: {chunk_preview.issues}")
        print(f"  Preview: {chunk_preview.content[:100]}...")

=============================================================================
"""

from dataclasses import dataclass, field
from typing import Optional, Callable
from enum import Enum
import re
import math

from retrieval_app.data_prep.chunker import DocumentChunker, Chunk


class IssueType(str, Enum):
    """Types of document/chunk issues."""
    # Parsing issues
    ENCODING_ERROR = "encoding_error"
    LOST_TABLE = "lost_table"
    LOST_IMAGE = "lost_image"
    FORMATTING_LOSS = "formatting_loss"

    # Chunking issues
    SENTENCE_SPLIT = "sentence_split"
    PARAGRAPH_SPLIT = "paragraph_split"
    ORPHANED_REFERENCE = "orphaned_reference"
    TOO_SHORT = "too_short"
    TOO_LONG = "too_long"

    # Content issues
    LOW_INFORMATION = "low_information"
    HIGH_BOILERPLATE = "high_boilerplate"
    INCOHERENT = "incoherent"
    MISSING_CONTEXT = "missing_context"


class IssueSeverity(str, Enum):
    """Severity levels for issues."""
    CRITICAL = "critical"  # Will definitely cause problems
    WARNING = "warning"    # Might cause problems
    INFO = "info"          # FYI, might be fine


@dataclass
class Issue:
    """A detected issue in document processing."""
    type: IssueType
    severity: IssueSeverity
    message: str
    location: Optional[str] = None  # Where in the document/chunk
    suggestion: Optional[str] = None  # How to fix it


@dataclass
class ChunkPreview:
    """Preview of a single chunk with quality analysis."""
    index: int
    content: str
    start_char: int
    end_char: int

    # Quality metrics
    quality_score: float  # 0-1, higher is better
    coherence_score: float
    information_density: float
    context_dependency: float  # Higher = needs more context

    # Issues found
    issues: list[Issue] = field(default_factory=list)

    # Context
    preceding_text: str = ""  # Text before chunk
    following_text: str = ""  # Text after chunk

    @property
    def is_problematic(self) -> bool:
        """Check if chunk has critical issues."""
        return any(i.severity == IssueSeverity.CRITICAL for i in self.issues)


@dataclass
class TransformationDiff:
    """Diff between two stages of transformation."""
    stage_name: str
    input_text: str
    output_text: str
    characters_removed: int
    characters_added: int
    lines_removed: int
    lines_added: int
    notable_changes: list[str]


@dataclass
class DocumentInspectionReport:
    """Complete inspection report for a document."""
    document_id: str
    original_length: int
    processed_length: int

    # Quality summary
    overall_quality: float  # 0-1
    chunk_count: int
    avg_chunk_quality: float

    # Chunk previews
    chunk_previews: list[ChunkPreview]

    # Issues
    issues: list[Issue]

    # Transformation history
    transformations: list[TransformationDiff]

    @property
    def has_critical_issues(self) -> bool:
        """Check if any critical issues were found."""
        return any(i.severity == IssueSeverity.CRITICAL for i in self.issues)

    @property
    def issue_summary(self) -> dict:
        """Summarize issues by type."""
        summary = {}
        for issue in self.issues:
            key = f"{issue.severity.value}:{issue.type.value}"
            summary[key] = summary.get(key, 0) + 1
        return summary

    def to_markdown(self) -> str:
        """Generate markdown report."""
        lines = [
            f"# Document Inspection Report: {self.document_id}",
            "",
            "## Summary",
            f"- **Overall Quality**: {self.overall_quality:.2%}",
            f"- **Chunks Created**: {self.chunk_count}",
            f"- **Average Chunk Quality**: {self.avg_chunk_quality:.2%}",
            f"- **Critical Issues**: {sum(1 for i in self.issues if i.severity == IssueSeverity.CRITICAL)}",
            "",
        ]

        if self.issues:
            lines.extend([
                "## Issues Detected",
                "",
            ])
            for issue in self.issues:
                icon = {"critical": "🔴", "warning": "🟡", "info": "🔵"}[issue.severity.value]
                lines.append(f"- {icon} **{issue.type.value}**: {issue.message}")
                if issue.suggestion:
                    lines.append(f"  - *Suggestion*: {issue.suggestion}")
            lines.append("")

        lines.extend([
            "## Chunk Previews",
            "",
        ])
        for preview in self.chunk_previews[:10]:  # First 10 chunks
            quality_bar = "█" * int(preview.quality_score * 10) + "░" * (10 - int(preview.quality_score * 10))
            lines.extend([
                f"### Chunk {preview.index}",
                f"Quality: [{quality_bar}] {preview.quality_score:.2%}",
                f"```",
                preview.content[:200] + ("..." if len(preview.content) > 200 else ""),
                f"```",
                "",
            ])

        return "\n".join(lines)


class ChunkQualityAnalyzer:
    """
    Analyzes chunk quality and detects issues.

    This is the core of the inspection system - it looks at each chunk
    and determines if it will cause problems downstream.
    """

    # Pronouns that indicate dependency on previous context
    CONTEXT_DEPENDENT_PATTERNS = [
        r'^(It|This|That|These|Those|They|He|She|The)\s',
        r'^(However|Therefore|Thus|Hence|Consequently|Furthermore|Moreover)\s',
        r'^(As mentioned|As stated|As shown|As discussed)',
    ]

    # Boilerplate patterns
    BOILERPLATE_PATTERNS = [
        r'click here',
        r'read more',
        r'sign up',
        r'subscribe',
        r'copyright \d{4}',
        r'all rights reserved',
        r'terms (of|and) (service|use)',
        r'privacy policy',
    ]

    def analyze_chunk(
        self,
        chunk: Chunk,
        original_text: str,
        preceding_text: str = "",
        following_text: str = "",
    ) -> ChunkPreview:
        """
        Analyze a single chunk for quality issues.

        Args:
            chunk: The chunk to analyze
            original_text: Full original document text
            preceding_text: Text before this chunk
            following_text: Text after this chunk

        Returns:
            ChunkPreview with quality metrics and issues
        """
        issues = []

        # Check for sentence splitting
        sentence_split_issue = self._check_sentence_split(chunk.content, preceding_text, following_text)
        if sentence_split_issue:
            issues.append(sentence_split_issue)

        # Check for orphaned references
        orphan_issue = self._check_orphaned_references(chunk.content)
        if orphan_issue:
            issues.append(orphan_issue)

        # Check length
        length_issue = self._check_length(chunk.content)
        if length_issue:
            issues.append(length_issue)

        # Check information density
        info_density = self._calculate_information_density(chunk.content)
        if info_density < 0.3:
            issues.append(Issue(
                type=IssueType.LOW_INFORMATION,
                severity=IssueSeverity.WARNING,
                message=f"Low information density ({info_density:.2%})",
                suggestion="Consider merging with adjacent chunks or excluding"
            ))

        # Check for boilerplate
        boilerplate_ratio = self._calculate_boilerplate_ratio(chunk.content)
        if boilerplate_ratio > 0.3:
            issues.append(Issue(
                type=IssueType.HIGH_BOILERPLATE,
                severity=IssueSeverity.WARNING,
                message=f"High boilerplate content ({boilerplate_ratio:.2%})",
                suggestion="Consider filtering boilerplate during preprocessing"
            ))

        # Calculate scores
        coherence = self._calculate_coherence(chunk.content)
        context_dependency = self._calculate_context_dependency(chunk.content)

        # Overall quality score
        quality_score = self._calculate_quality_score(
            info_density, coherence, context_dependency, len(issues)
        )

        return ChunkPreview(
            index=chunk.chunk_index,
            content=chunk.content,
            start_char=chunk.start_char,
            end_char=chunk.end_char,
            quality_score=quality_score,
            coherence_score=coherence,
            information_density=info_density,
            context_dependency=context_dependency,
            issues=issues,
            preceding_text=preceding_text[-100:] if preceding_text else "",
            following_text=following_text[:100] if following_text else "",
        )

    def _check_sentence_split(
        self,
        content: str,
        preceding: str,
        following: str,
    ) -> Optional[Issue]:
        """Check if chunk starts or ends mid-sentence."""
        # Check if starts mid-sentence (lowercase start without preceding period)
        if content and content[0].islower():
            if preceding and not preceding.rstrip().endswith(('.', '!', '?', ':')):
                return Issue(
                    type=IssueType.SENTENCE_SPLIT,
                    severity=IssueSeverity.CRITICAL,
                    message="Chunk starts mid-sentence",
                    location="start",
                    suggestion="Adjust chunking to respect sentence boundaries"
                )

        # Check if ends mid-sentence
        last_char = content.rstrip()[-1] if content.rstrip() else ''
        if last_char and last_char not in '.!?:"\')':
            if following and following.lstrip() and following.lstrip()[0].islower():
                return Issue(
                    type=IssueType.SENTENCE_SPLIT,
                    severity=IssueSeverity.CRITICAL,
                    message="Chunk ends mid-sentence",
                    location="end",
                    suggestion="Adjust chunking to respect sentence boundaries"
                )

        return None

    def _check_orphaned_references(self, content: str) -> Optional[Issue]:
        """Check if chunk starts with context-dependent language."""
        for pattern in self.CONTEXT_DEPENDENT_PATTERNS:
            if re.match(pattern, content, re.IGNORECASE):
                return Issue(
                    type=IssueType.ORPHANED_REFERENCE,
                    severity=IssueSeverity.WARNING,
                    message=f"Chunk starts with context-dependent reference",
                    suggestion="Include preceding context or use overlap"
                )
        return None

    def _check_length(self, content: str) -> Optional[Issue]:
        """Check if chunk length is appropriate."""
        word_count = len(content.split())

        if word_count < 20:
            return Issue(
                type=IssueType.TOO_SHORT,
                severity=IssueSeverity.WARNING,
                message=f"Chunk is very short ({word_count} words)",
                suggestion="Consider increasing minimum chunk size"
            )

        if word_count > 500:
            return Issue(
                type=IssueType.TOO_LONG,
                severity=IssueSeverity.INFO,
                message=f"Chunk is very long ({word_count} words)",
                suggestion="Consider decreasing maximum chunk size"
            )

        return None

    def _calculate_information_density(self, content: str) -> float:
        """Calculate information density (unique meaningful words / total words)."""
        words = re.findall(r'\b\w+\b', content.lower())
        if not words:
            return 0.0

        # Remove stopwords
        stopwords = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'must', 'shall', 'can',
            'this', 'that', 'these', 'those', 'it', 'its', 'and', 'or',
            'but', 'if', 'then', 'else', 'when', 'where', 'which', 'who',
            'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
            'as', 'into', 'through', 'during', 'before', 'after', 'above',
            'below', 'between', 'under', 'again', 'further', 'once',
        }

        meaningful = [w for w in words if w not in stopwords and len(w) > 2]
        unique_meaningful = set(meaningful)

        return len(unique_meaningful) / max(len(words), 1)

    def _calculate_boilerplate_ratio(self, content: str) -> float:
        """Calculate what fraction of content is boilerplate."""
        content_lower = content.lower()
        boilerplate_chars = 0

        for pattern in self.BOILERPLATE_PATTERNS:
            matches = re.findall(pattern, content_lower, re.IGNORECASE)
            for match in matches:
                boilerplate_chars += len(match) if isinstance(match, str) else len(match[0])

        return boilerplate_chars / max(len(content), 1)

    def _calculate_coherence(self, content: str) -> float:
        """
        Calculate chunk coherence (does it make sense standalone?).

        Uses simple heuristics:
        - Complete sentences
        - Topic consistency (word repetition)
        - Structural completeness
        """
        sentences = re.split(r'[.!?]+', content)
        complete_sentences = [s for s in sentences if s.strip()]

        if not complete_sentences:
            return 0.3

        # Check sentence completeness
        completeness_score = 1.0
        for sentence in complete_sentences:
            words = sentence.strip().split()
            if len(words) < 3:
                completeness_score -= 0.1

        # Check topic consistency (repeated important words)
        words = re.findall(r'\b\w{4,}\b', content.lower())
        if words:
            word_counts = {}
            for w in words:
                word_counts[w] = word_counts.get(w, 0) + 1
            repeated = sum(1 for c in word_counts.values() if c > 1)
            consistency_score = min(repeated / 3, 1.0)
        else:
            consistency_score = 0.5

        return min(1.0, (completeness_score * 0.6 + consistency_score * 0.4))

    def _calculate_context_dependency(self, content: str) -> float:
        """Calculate how much this chunk depends on surrounding context."""
        dependency_score = 0.0

        # Check for context-dependent starts
        for pattern in self.CONTEXT_DEPENDENT_PATTERNS:
            if re.match(pattern, content, re.IGNORECASE):
                dependency_score += 0.3

        # Check for unresolved pronouns
        pronouns = len(re.findall(r'\b(it|this|that|they|he|she|these|those)\b', content.lower()))
        nouns = len(re.findall(r'\b[A-Z][a-z]+\b', content))  # Proper nouns as proxy

        if pronouns > nouns:
            dependency_score += 0.2 * (pronouns - nouns) / max(pronouns, 1)

        return min(1.0, dependency_score)

    def _calculate_quality_score(
        self,
        info_density: float,
        coherence: float,
        context_dependency: float,
        issue_count: int,
    ) -> float:
        """Calculate overall quality score."""
        base_score = (
            info_density * 0.3 +
            coherence * 0.4 +
            (1 - context_dependency) * 0.3
        )

        # Penalize for issues
        issue_penalty = min(issue_count * 0.1, 0.3)

        return max(0.0, min(1.0, base_score - issue_penalty))


class DocumentInspector:
    """
    Main interface for document inspection.

    Provides visibility into every stage of document processing
    BEFORE documents hit the vector store.
    """

    def __init__(self):
        self.chunk_analyzer = ChunkQualityAnalyzer()

    def inspect_document(
        self,
        raw_text: str,
        chunker: DocumentChunker,
        document_id: str,
        metadata: Optional[dict] = None,
    ) -> DocumentInspectionReport:
        """
        Inspect a document through the full processing pipeline.

        This is the key function - call this BEFORE indexing to catch problems.

        Args:
            raw_text: Original document text
            chunker: The chunker that will process this document
            document_id: ID for the document
            metadata: Optional metadata

        Returns:
            Comprehensive inspection report
        """
        transformations = []
        issues = []

        # Stage 1: Pre-processing inspection
        preprocessed = chunker._preprocess_text(raw_text)
        transformations.append(self._diff_texts(
            "preprocessing", raw_text, preprocessed
        ))

        # Check for significant content loss in preprocessing
        if len(preprocessed) < len(raw_text) * 0.7:
            issues.append(Issue(
                type=IssueType.FORMATTING_LOSS,
                severity=IssueSeverity.WARNING,
                message=f"Preprocessing removed {len(raw_text) - len(preprocessed)} characters ({(1 - len(preprocessed)/len(raw_text)):.1%})",
                suggestion="Review preprocessing rules for data loss"
            ))

        # Stage 2: Chunking
        chunks = chunker.chunk_document(raw_text, document_id, metadata or {})

        # Stage 3: Analyze each chunk
        chunk_previews = []
        for i, chunk in enumerate(chunks):
            # Get surrounding context
            preceding = raw_text[:chunk.start_char][-200:] if chunk.start_char > 0 else ""
            following = raw_text[chunk.end_char:][:200] if chunk.end_char < len(raw_text) else ""

            preview = self.chunk_analyzer.analyze_chunk(
                chunk, raw_text, preceding, following
            )
            chunk_previews.append(preview)

            # Aggregate critical issues to document level
            for issue in preview.issues:
                if issue.severity == IssueSeverity.CRITICAL:
                    issue.location = f"Chunk {i}"
                    issues.append(issue)

        # Calculate summary metrics
        avg_quality = sum(p.quality_score for p in chunk_previews) / max(len(chunk_previews), 1)
        overall_quality = self._calculate_overall_quality(chunk_previews, issues)

        return DocumentInspectionReport(
            document_id=document_id,
            original_length=len(raw_text),
            processed_length=sum(len(c.content) for c in chunks),
            overall_quality=overall_quality,
            chunk_count=len(chunks),
            avg_chunk_quality=avg_quality,
            chunk_previews=chunk_previews,
            issues=issues,
            transformations=transformations,
        )

    def preview_chunks(
        self,
        raw_text: str,
        chunker: DocumentChunker,
        document_id: str = "preview",
    ) -> list[dict]:
        """
        Quick preview of how a document will be chunked.

        Useful for interactive exploration and chunking strategy selection.
        """
        report = self.inspect_document(raw_text, chunker, document_id)

        return [
            {
                "index": p.index,
                "quality": round(p.quality_score, 2),
                "length": len(p.content),
                "preview": p.content[:100] + "..." if len(p.content) > 100 else p.content,
                "issues": [i.message for i in p.issues],
            }
            for p in report.chunk_previews
        ]

    def compare_chunking_strategies(
        self,
        raw_text: str,
        chunkers: dict[str, DocumentChunker],
        document_id: str = "comparison",
    ) -> dict:
        """
        Compare different chunking strategies on the same document.

        Useful for selecting the best strategy for your content.
        """
        results = {}

        for name, chunker in chunkers.items():
            report = self.inspect_document(raw_text, chunker, f"{document_id}_{name}")
            results[name] = {
                "overall_quality": round(report.overall_quality, 3),
                "chunk_count": report.chunk_count,
                "avg_chunk_quality": round(report.avg_chunk_quality, 3),
                "critical_issues": sum(1 for i in report.issues if i.severity == IssueSeverity.CRITICAL),
                "warnings": sum(1 for i in report.issues if i.severity == IssueSeverity.WARNING),
            }

        # Rank strategies
        ranked = sorted(
            results.items(),
            key=lambda x: x[1]["overall_quality"],
            reverse=True
        )

        return {
            "results": results,
            "recommended": ranked[0][0] if ranked else None,
            "ranking": [name for name, _ in ranked],
        }

    def _diff_texts(self, stage: str, before: str, after: str) -> TransformationDiff:
        """Create a diff between two text states."""
        before_lines = before.split('\n')
        after_lines = after.split('\n')

        notable = []
        if len(after) < len(before) * 0.9:
            notable.append(f"Significant reduction: {len(before)} -> {len(after)} chars")

        return TransformationDiff(
            stage_name=stage,
            input_text=before[:500] + "..." if len(before) > 500 else before,
            output_text=after[:500] + "..." if len(after) > 500 else after,
            characters_removed=max(0, len(before) - len(after)),
            characters_added=max(0, len(after) - len(before)),
            lines_removed=max(0, len(before_lines) - len(after_lines)),
            lines_added=max(0, len(after_lines) - len(before_lines)),
            notable_changes=notable,
        )

    def _calculate_overall_quality(
        self,
        previews: list[ChunkPreview],
        issues: list[Issue],
    ) -> float:
        """Calculate overall document quality score."""
        if not previews:
            return 0.0

        avg_chunk_quality = sum(p.quality_score for p in previews) / len(previews)

        # Penalize for critical issues
        critical_count = sum(1 for i in issues if i.severity == IssueSeverity.CRITICAL)
        critical_penalty = min(critical_count * 0.15, 0.5)

        # Penalize for warnings
        warning_count = sum(1 for i in issues if i.severity == IssueSeverity.WARNING)
        warning_penalty = min(warning_count * 0.05, 0.2)

        return max(0.0, avg_chunk_quality - critical_penalty - warning_penalty)
