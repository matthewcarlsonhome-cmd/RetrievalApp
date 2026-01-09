"""
RAG Logger Module.

Structured logging for RAG systems with focus on debugging retrieval issues.
"""

import json
import logging
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Any
from pathlib import Path


@dataclass
class RetrievalLogEntry:
    """Structured log entry for retrieval operations."""
    timestamp: str
    query_id: str
    query: str
    retrieval_mode: str
    results_count: int
    top_score: float
    avg_score: float
    latency_ms: float
    metadata_filter: Optional[dict] = None
    reranked: bool = False


@dataclass
class GenerationLogEntry:
    """Structured log entry for generation operations."""
    timestamp: str
    query_id: str
    tokens_used: int
    confidence: float
    latency_ms: float
    sources_count: int
    hallucination_check: Optional[bool] = None


@dataclass
class MissLogEntry:
    """Log entry for retrieval misses - critical for improving the system."""
    timestamp: str
    query_id: str
    query: str
    reason: str
    top_score: float
    suggested_action: str


class RAGLogger:
    """
    Structured logger for RAG pipelines.

    Captures:
    - Retrieval operations with scores and latency
    - Generation operations with confidence
    - Retrieval misses for analysis
    - Error conditions
    """

    def __init__(
        self,
        name: str = "rag",
        log_level: str = "INFO",
        log_file: Optional[str] = None,
        structured_output: bool = True
    ):
        self.name = name
        self.structured_output = structured_output

        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, log_level.upper()))

        if not self.logger.handlers:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.DEBUG)

            if structured_output:
                formatter = logging.Formatter(
                    '{"time": "%(asctime)s", "level": "%(levelname)s", '
                    '"logger": "%(name)s", "message": %(message)s}'
                )
            else:
                formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

            if log_file:
                file_handler = logging.FileHandler(log_file)
                file_handler.setLevel(logging.DEBUG)
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)

        self._miss_log_path: Optional[Path] = None

    def set_miss_log_path(self, path: str) -> None:
        """Set path for logging retrieval misses."""
        self._miss_log_path = Path(path)
        self._miss_log_path.parent.mkdir(parents=True, exist_ok=True)

    def log_retrieval(
        self,
        query_id: str,
        query: str,
        results_count: int,
        scores: list[float],
        latency_ms: float,
        retrieval_mode: str = "hybrid",
        metadata_filter: Optional[dict] = None,
        reranked: bool = False
    ) -> None:
        """Log a retrieval operation."""
        entry = RetrievalLogEntry(
            timestamp=datetime.utcnow().isoformat(),
            query_id=query_id,
            query=query,
            retrieval_mode=retrieval_mode,
            results_count=results_count,
            top_score=max(scores) if scores else 0.0,
            avg_score=sum(scores) / len(scores) if scores else 0.0,
            latency_ms=latency_ms,
            metadata_filter=metadata_filter,
            reranked=reranked
        )

        self._log("INFO", "retrieval", asdict(entry))

    def log_generation(
        self,
        query_id: str,
        tokens_used: int,
        confidence: float,
        latency_ms: float,
        sources_count: int,
        hallucination_check: Optional[bool] = None
    ) -> None:
        """Log a generation operation."""
        entry = GenerationLogEntry(
            timestamp=datetime.utcnow().isoformat(),
            query_id=query_id,
            tokens_used=tokens_used,
            confidence=confidence,
            latency_ms=latency_ms,
            sources_count=sources_count,
            hallucination_check=hallucination_check
        )

        self._log("INFO", "generation", asdict(entry))

    def log_miss(
        self,
        query_id: str,
        query: str,
        reason: str,
        top_score: float,
        suggested_action: str = "review_query"
    ) -> None:
        """
        Log a retrieval miss for later analysis.

        Misses are critical signals for improving the RAG system:
        - Missing documents in the index
        - Poor chunking
        - Query-document mismatch
        """
        entry = MissLogEntry(
            timestamp=datetime.utcnow().isoformat(),
            query_id=query_id,
            query=query,
            reason=reason,
            top_score=top_score,
            suggested_action=suggested_action
        )

        self._log("WARNING", "retrieval_miss", asdict(entry))

        if self._miss_log_path:
            with open(self._miss_log_path, 'a') as f:
                f.write(json.dumps(asdict(entry)) + '\n')

    def log_error(
        self,
        query_id: str,
        error_type: str,
        error_message: str,
        context: Optional[dict] = None
    ) -> None:
        """Log an error."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "query_id": query_id,
            "error_type": error_type,
            "error_message": error_message,
            "context": context or {}
        }

        self._log("ERROR", "error", entry)

    def log_fallback(
        self,
        query_id: str,
        fallback_mode: str,
        reason: str,
        handled: bool
    ) -> None:
        """Log a fallback event."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "query_id": query_id,
            "fallback_mode": fallback_mode,
            "reason": reason,
            "handled": handled
        }

        self._log("INFO", "fallback", entry)

    def _log(self, level: str, event_type: str, data: dict) -> None:
        """Internal logging method."""
        message = {"event": event_type, **data}

        if self.structured_output:
            log_message = json.dumps(message)
        else:
            log_message = f"[{event_type}] {json.dumps(data)}"

        getattr(self.logger, level.lower())(log_message)

    def get_miss_summary(self, limit: int = 100) -> list[dict]:
        """Get summary of recent retrieval misses."""
        if not self._miss_log_path or not self._miss_log_path.exists():
            return []

        misses = []
        with open(self._miss_log_path, 'r') as f:
            for line in f:
                try:
                    misses.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

        return misses[-limit:]
