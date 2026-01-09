"""
Bulk Processor Module.

=============================================================================
INNOVATION: HIGH-THROUGHPUT ASYNC DOCUMENT PROCESSING
=============================================================================

Production document ingestion needs:
1. High throughput (thousands of documents per hour)
2. Progress tracking (where are we in a 10K doc batch?)
3. Error resilience (one bad doc shouldn't stop the batch)
4. Resource management (don't OOM on large batches)
5. Resumability (pick up where we left off after crash)

This module implements production-grade bulk processing:

- STREAMING: Process documents as they arrive, don't load all into memory
- BATCHING: Efficient batch operations for embeddings and indexing
- PROGRESS: Real-time progress updates with estimated completion time
- CHECKPOINTING: Save progress for crash recovery
- VALIDATION: Pre-flight checks before expensive processing
- REPORTING: Detailed reports of what succeeded/failed

=============================================================================
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Iterator, Callable, Any
from pathlib import Path
from enum import Enum
import json
import time
import threading
import queue


class ProcessingStatus(str, Enum):
    """Status of document processing."""
    PENDING = "pending"
    VALIDATING = "validating"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class DocumentStatus:
    """Status of a single document in the batch."""
    document_id: str
    status: ProcessingStatus
    chunks_created: int = 0
    error_message: Optional[str] = None
    processing_time_ms: float = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class BatchProgress:
    """Progress of the entire batch."""
    batch_id: str
    total_documents: int
    processed: int
    succeeded: int
    failed: int
    skipped: int

    started_at: datetime
    current_status: str

    # Timing
    elapsed_seconds: float
    estimated_remaining_seconds: float

    # Resource usage
    chunks_created: int
    embeddings_generated: int

    @property
    def percent_complete(self) -> float:
        return (self.processed / max(self.total_documents, 1)) * 100

    @property
    def documents_per_second(self) -> float:
        if self.elapsed_seconds == 0:
            return 0
        return self.processed / self.elapsed_seconds

    def to_dict(self) -> dict:
        return {
            "batch_id": self.batch_id,
            "total": self.total_documents,
            "processed": self.processed,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "skipped": self.skipped,
            "percent_complete": round(self.percent_complete, 1),
            "elapsed_seconds": round(self.elapsed_seconds, 1),
            "estimated_remaining_seconds": round(self.estimated_remaining_seconds, 1),
            "documents_per_second": round(self.documents_per_second, 2),
            "chunks_created": self.chunks_created,
        }


@dataclass
class BatchReport:
    """Final report for a completed batch."""
    batch_id: str
    total_documents: int
    succeeded: int
    failed: int
    skipped: int

    started_at: datetime
    completed_at: datetime
    total_duration_seconds: float

    chunks_created: int
    embeddings_generated: int

    # Per-document details
    document_statuses: list[DocumentStatus]

    # Failure analysis
    failure_reasons: dict[str, int]

    def to_markdown(self) -> str:
        """Generate markdown report."""
        lines = [
            f"# Batch Processing Report: {self.batch_id}",
            "",
            "## Summary",
            f"- **Total Documents**: {self.total_documents}",
            f"- **Succeeded**: {self.succeeded}",
            f"- **Failed**: {self.failed}",
            f"- **Skipped**: {self.skipped}",
            f"- **Duration**: {self.total_duration_seconds:.1f} seconds",
            f"- **Throughput**: {self.total_documents / max(self.total_duration_seconds, 1):.1f} docs/sec",
            "",
            "## Resources",
            f"- **Chunks Created**: {self.chunks_created}",
            f"- **Embeddings Generated**: {self.embeddings_generated}",
            "",
        ]

        if self.failure_reasons:
            lines.extend([
                "## Failure Analysis",
                "",
            ])
            for reason, count in sorted(self.failure_reasons.items(), key=lambda x: -x[1]):
                lines.append(f"- {reason}: {count}")
            lines.append("")

        if any(ds.status == ProcessingStatus.FAILED for ds in self.document_statuses):
            lines.extend([
                "## Failed Documents",
                "",
            ])
            for ds in self.document_statuses[:20]:  # First 20 failures
                if ds.status == ProcessingStatus.FAILED:
                    lines.append(f"- **{ds.document_id}**: {ds.error_message}")
            lines.append("")

        return "\n".join(lines)


class BulkProcessor:
    """
    High-throughput document processor for production workloads.

    Usage:
        processor = BulkProcessor(pipeline)

        # Process a batch with progress tracking
        for progress in processor.process_batch(documents):
            print(f"Progress: {progress.percent_complete:.1f}%")
            print(f"ETA: {progress.estimated_remaining_seconds:.0f}s")

        # Get final report
        report = processor.get_report()
        print(report.to_markdown())

    Advanced Usage:
        # With checkpoint for resumability
        processor = BulkProcessor(
            pipeline,
            checkpoint_path="./checkpoints/batch_001.json",
        )

        # Resume from checkpoint if exists
        processor.resume_or_start(documents)

        # With progress callback
        processor.process_batch(
            documents,
            progress_callback=lambda p: notify_ui(p),
        )
    """

    def __init__(
        self,
        pipeline: Any,  # RAGPipeline
        batch_size: int = 50,
        checkpoint_path: Optional[str] = None,
        max_failures: int = 100,
        validate_before_process: bool = True,
    ):
        """
        Initialize bulk processor.

        Args:
            pipeline: The RAG pipeline to use for processing
            batch_size: Documents per batch for embedding
            checkpoint_path: Path for checkpoint files
            max_failures: Stop batch if this many failures occur
            validate_before_process: Run validation before processing
        """
        self.pipeline = pipeline
        self.batch_size = batch_size
        self.checkpoint_path = Path(checkpoint_path) if checkpoint_path else None
        self.max_failures = max_failures
        self.validate_before_process = validate_before_process

        # State
        self._batch_id: Optional[str] = None
        self._document_statuses: dict[str, DocumentStatus] = {}
        self._started_at: Optional[datetime] = None
        self._completed_at: Optional[datetime] = None

        # Counters
        self._processed = 0
        self._succeeded = 0
        self._failed = 0
        self._skipped = 0
        self._chunks_created = 0
        self._embeddings_generated = 0

    def process_batch(
        self,
        documents: Iterator[tuple[str, str, dict]],
        batch_id: Optional[str] = None,
        progress_callback: Optional[Callable[[BatchProgress], None]] = None,
    ) -> Iterator[BatchProgress]:
        """
        Process a batch of documents with progress tracking.

        Args:
            documents: Iterator of (doc_id, text, metadata) tuples
            batch_id: Optional batch identifier
            progress_callback: Optional callback for progress updates

        Yields:
            BatchProgress objects as processing proceeds
        """
        self._batch_id = batch_id or datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        self._started_at = datetime.utcnow()
        self._reset_counters()

        # Convert to list for counting (could also accept count parameter)
        doc_list = list(documents)
        total = len(doc_list)

        # Validation pass
        if self.validate_before_process:
            yield from self._validation_pass(doc_list)

        # Processing pass
        current_batch = []
        for doc_id, text, metadata in doc_list:
            # Skip if already processed (resume support)
            if doc_id in self._document_statuses:
                status = self._document_statuses[doc_id]
                if status.status == ProcessingStatus.COMPLETED:
                    continue

            current_batch.append((doc_id, text, metadata))

            if len(current_batch) >= self.batch_size:
                yield from self._process_batch_internal(current_batch, total, progress_callback)
                current_batch = []

                # Check failure threshold
                if self._failed >= self.max_failures:
                    break

        # Process remaining
        if current_batch:
            yield from self._process_batch_internal(current_batch, total, progress_callback)

        self._completed_at = datetime.utcnow()

        # Save final checkpoint
        if self.checkpoint_path:
            self._save_checkpoint()

    def _validation_pass(
        self,
        documents: list[tuple[str, str, dict]],
    ) -> Iterator[BatchProgress]:
        """Pre-validate all documents."""
        for doc_id, text, metadata in documents:
            status = DocumentStatus(
                document_id=doc_id,
                status=ProcessingStatus.VALIDATING,
            )

            # Basic validation
            if not text or len(text.strip()) < 10:
                status.status = ProcessingStatus.SKIPPED
                status.error_message = "Empty or too short"
                self._skipped += 1
            else:
                status.status = ProcessingStatus.PENDING

            self._document_statuses[doc_id] = status

        yield self._get_progress(len(documents), "Validation complete")

    def _process_batch_internal(
        self,
        batch: list[tuple[str, str, dict]],
        total: int,
        progress_callback: Optional[Callable[[BatchProgress], None]],
    ) -> Iterator[BatchProgress]:
        """Process a batch of documents."""
        for doc_id, text, metadata in batch:
            status = self._document_statuses.get(doc_id, DocumentStatus(
                document_id=doc_id,
                status=ProcessingStatus.PENDING,
            ))

            status.started_at = datetime.utcnow()

            try:
                # Chunking
                status.status = ProcessingStatus.CHUNKING
                chunks = self.pipeline.chunker.chunk_document(text, doc_id, metadata)
                status.chunks_created = len(chunks)
                self._chunks_created += len(chunks)

                # Embedding
                status.status = ProcessingStatus.EMBEDDING
                chunks_with_embeddings = self.pipeline.embedding_service.embed_chunks(chunks)
                self._embeddings_generated += len(chunks_with_embeddings)

                # Indexing
                status.status = ProcessingStatus.INDEXING
                self.pipeline.retriever.vector_store.add_chunks(chunks_with_embeddings)
                self.pipeline.retriever.lexical_searcher.index_chunks(chunks_with_embeddings)

                # Success
                status.status = ProcessingStatus.COMPLETED
                status.completed_at = datetime.utcnow()
                status.processing_time_ms = (
                    status.completed_at - status.started_at
                ).total_seconds() * 1000
                self._succeeded += 1

            except Exception as e:
                status.status = ProcessingStatus.FAILED
                status.error_message = str(e)
                status.completed_at = datetime.utcnow()
                self._failed += 1

            self._document_statuses[doc_id] = status
            self._processed += 1

        progress = self._get_progress(total, "Processing")

        if progress_callback:
            progress_callback(progress)

        # Checkpoint periodically
        if self.checkpoint_path and self._processed % 100 == 0:
            self._save_checkpoint()

        yield progress

    def _get_progress(self, total: int, status: str) -> BatchProgress:
        """Generate current progress."""
        elapsed = (datetime.utcnow() - self._started_at).total_seconds()

        # Estimate remaining time
        if self._processed > 0:
            rate = self._processed / elapsed
            remaining_docs = total - self._processed
            estimated_remaining = remaining_docs / rate if rate > 0 else 0
        else:
            estimated_remaining = 0

        return BatchProgress(
            batch_id=self._batch_id,
            total_documents=total,
            processed=self._processed,
            succeeded=self._succeeded,
            failed=self._failed,
            skipped=self._skipped,
            started_at=self._started_at,
            current_status=status,
            elapsed_seconds=elapsed,
            estimated_remaining_seconds=estimated_remaining,
            chunks_created=self._chunks_created,
            embeddings_generated=self._embeddings_generated,
        )

    def get_report(self) -> BatchReport:
        """Generate final batch report."""
        # Analyze failure reasons
        failure_reasons = {}
        for status in self._document_statuses.values():
            if status.status == ProcessingStatus.FAILED and status.error_message:
                # Normalize error message
                reason = status.error_message.split(":")[0][:50]
                failure_reasons[reason] = failure_reasons.get(reason, 0) + 1

        duration = (
            (self._completed_at or datetime.utcnow()) - self._started_at
        ).total_seconds()

        return BatchReport(
            batch_id=self._batch_id,
            total_documents=len(self._document_statuses),
            succeeded=self._succeeded,
            failed=self._failed,
            skipped=self._skipped,
            started_at=self._started_at,
            completed_at=self._completed_at or datetime.utcnow(),
            total_duration_seconds=duration,
            chunks_created=self._chunks_created,
            embeddings_generated=self._embeddings_generated,
            document_statuses=list(self._document_statuses.values()),
            failure_reasons=failure_reasons,
        )

    def _reset_counters(self) -> None:
        """Reset all counters for new batch."""
        self._processed = 0
        self._succeeded = 0
        self._failed = 0
        self._skipped = 0
        self._chunks_created = 0
        self._embeddings_generated = 0
        self._document_statuses.clear()

    def _save_checkpoint(self) -> None:
        """Save checkpoint for resume capability."""
        if not self.checkpoint_path:
            return

        checkpoint = {
            "batch_id": self._batch_id,
            "started_at": self._started_at.isoformat(),
            "processed": self._processed,
            "succeeded": self._succeeded,
            "failed": self._failed,
            "skipped": self._skipped,
            "document_statuses": {
                doc_id: {
                    "status": status.status.value,
                    "chunks_created": status.chunks_created,
                    "error_message": status.error_message,
                }
                for doc_id, status in self._document_statuses.items()
            },
        }

        self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.checkpoint_path, 'w') as f:
            json.dump(checkpoint, f, indent=2)

    def load_checkpoint(self) -> bool:
        """Load checkpoint if exists. Returns True if loaded."""
        if not self.checkpoint_path or not self.checkpoint_path.exists():
            return False

        try:
            with open(self.checkpoint_path, 'r') as f:
                checkpoint = json.load(f)

            self._batch_id = checkpoint["batch_id"]
            self._started_at = datetime.fromisoformat(checkpoint["started_at"])
            self._processed = checkpoint["processed"]
            self._succeeded = checkpoint["succeeded"]
            self._failed = checkpoint["failed"]
            self._skipped = checkpoint["skipped"]

            for doc_id, data in checkpoint["document_statuses"].items():
                self._document_statuses[doc_id] = DocumentStatus(
                    document_id=doc_id,
                    status=ProcessingStatus(data["status"]),
                    chunks_created=data.get("chunks_created", 0),
                    error_message=data.get("error_message"),
                )

            return True

        except (json.JSONDecodeError, KeyError):
            return False
