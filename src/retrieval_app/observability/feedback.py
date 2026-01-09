"""
Feedback Collection Module.

"Building feedback loops so the system actually learns instead of rotting silently."
"""

import json
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional
from enum import Enum


class FeedbackType(str, Enum):
    """Types of feedback."""
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    RATING = "rating"
    CORRECTION = "correction"
    MISSING_INFO = "missing_info"
    WRONG_ANSWER = "wrong_answer"
    IRRELEVANT_SOURCES = "irrelevant_sources"


@dataclass
class FeedbackEntry:
    """A piece of user feedback."""
    id: str
    timestamp: str
    query_id: str
    query: str
    answer: str
    feedback_type: FeedbackType
    score: Optional[float] = None
    comment: Optional[str] = None
    correct_answer: Optional[str] = None
    relevant_chunk_ids: Optional[list[str]] = None
    user_id: Optional[str] = None

    def to_dict(self) -> dict:
        result = asdict(self)
        result["feedback_type"] = self.feedback_type.value
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "FeedbackEntry":
        data["feedback_type"] = FeedbackType(data["feedback_type"])
        return cls(**data)


@dataclass
class FeedbackAnalysis:
    """Analysis of collected feedback."""
    total_feedback: int
    positive_rate: float
    negative_rate: float
    average_rating: Optional[float]
    common_issues: list[tuple[str, int]]
    queries_needing_review: list[str]


class FeedbackCollector:
    """
    Collects and analyzes user feedback for continuous improvement.

    Feedback signals:
    - Explicit ratings (thumbs up/down, stars)
    - Corrections (user provides correct answer)
    - Missing information flags
    - Source relevance feedback
    """

    def __init__(self, storage_path: str = "./feedback"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._feedback: list[FeedbackEntry] = []
        self._load_feedback()

    def _load_feedback(self) -> None:
        """Load existing feedback from storage."""
        feedback_file = self.storage_path / "feedback.jsonl"
        if feedback_file.exists():
            with open(feedback_file, 'r') as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        self._feedback.append(FeedbackEntry.from_dict(data))
                    except (json.JSONDecodeError, KeyError):
                        continue

    def _save_entry(self, entry: FeedbackEntry) -> None:
        """Append a feedback entry to storage."""
        feedback_file = self.storage_path / "feedback.jsonl"
        with open(feedback_file, 'a') as f:
            f.write(json.dumps(entry.to_dict()) + '\n')

    def record_thumbs(
        self,
        query_id: str,
        query: str,
        answer: str,
        is_positive: bool,
        user_id: Optional[str] = None,
        comment: Optional[str] = None
    ) -> FeedbackEntry:
        """Record thumbs up/down feedback."""
        entry = FeedbackEntry(
            id=str(uuid.uuid4()),
            timestamp=datetime.utcnow().isoformat(),
            query_id=query_id,
            query=query,
            answer=answer,
            feedback_type=FeedbackType.THUMBS_UP if is_positive else FeedbackType.THUMBS_DOWN,
            score=1.0 if is_positive else 0.0,
            user_id=user_id,
            comment=comment
        )

        self._feedback.append(entry)
        self._save_entry(entry)
        return entry

    def record_rating(
        self,
        query_id: str,
        query: str,
        answer: str,
        rating: float,
        user_id: Optional[str] = None,
        comment: Optional[str] = None
    ) -> FeedbackEntry:
        """Record numerical rating (0-1 scale)."""
        entry = FeedbackEntry(
            id=str(uuid.uuid4()),
            timestamp=datetime.utcnow().isoformat(),
            query_id=query_id,
            query=query,
            answer=answer,
            feedback_type=FeedbackType.RATING,
            score=max(0.0, min(1.0, rating)),
            user_id=user_id,
            comment=comment
        )

        self._feedback.append(entry)
        self._save_entry(entry)
        return entry

    def record_correction(
        self,
        query_id: str,
        query: str,
        wrong_answer: str,
        correct_answer: str,
        user_id: Optional[str] = None
    ) -> FeedbackEntry:
        """Record a correction when the answer was wrong."""
        entry = FeedbackEntry(
            id=str(uuid.uuid4()),
            timestamp=datetime.utcnow().isoformat(),
            query_id=query_id,
            query=query,
            answer=wrong_answer,
            feedback_type=FeedbackType.CORRECTION,
            score=0.0,
            correct_answer=correct_answer,
            user_id=user_id
        )

        self._feedback.append(entry)
        self._save_entry(entry)

        self._save_to_review_queue(entry)

        return entry

    def record_source_feedback(
        self,
        query_id: str,
        query: str,
        answer: str,
        relevant_chunk_ids: list[str],
        irrelevant_chunk_ids: list[str],
        user_id: Optional[str] = None
    ) -> FeedbackEntry:
        """Record feedback on source relevance."""
        entry = FeedbackEntry(
            id=str(uuid.uuid4()),
            timestamp=datetime.utcnow().isoformat(),
            query_id=query_id,
            query=query,
            answer=answer,
            feedback_type=FeedbackType.IRRELEVANT_SOURCES,
            relevant_chunk_ids=relevant_chunk_ids,
            user_id=user_id,
            comment=f"Irrelevant sources: {irrelevant_chunk_ids}"
        )

        self._feedback.append(entry)
        self._save_entry(entry)
        return entry

    def _save_to_review_queue(self, entry: FeedbackEntry) -> None:
        """Save correction to review queue for truth set updates."""
        review_file = self.storage_path / "review_queue.jsonl"
        with open(review_file, 'a') as f:
            f.write(json.dumps(entry.to_dict()) + '\n')

    def analyze(self, days: Optional[int] = None) -> FeedbackAnalysis:
        """Analyze collected feedback."""
        feedback = self._feedback

        if days:
            cutoff = datetime.utcnow().isoformat()[:10]
            feedback = [
                f for f in feedback
                if f.timestamp[:10] >= cutoff
            ]

        if not feedback:
            return FeedbackAnalysis(
                total_feedback=0,
                positive_rate=0.0,
                negative_rate=0.0,
                average_rating=None,
                common_issues=[],
                queries_needing_review=[]
            )

        positive = sum(1 for f in feedback if f.score and f.score >= 0.5)
        negative = sum(1 for f in feedback if f.score is not None and f.score < 0.5)

        ratings = [f.score for f in feedback if f.score is not None]
        avg_rating = sum(ratings) / len(ratings) if ratings else None

        issue_counts: dict[str, int] = {}
        for f in feedback:
            if f.feedback_type in (
                FeedbackType.WRONG_ANSWER,
                FeedbackType.MISSING_INFO,
                FeedbackType.IRRELEVANT_SOURCES,
                FeedbackType.CORRECTION
            ):
                issue_counts[f.feedback_type.value] = issue_counts.get(
                    f.feedback_type.value, 0
                ) + 1

        common_issues = sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)

        review_queries = list(set(
            f.query for f in feedback
            if f.feedback_type == FeedbackType.CORRECTION
        ))

        return FeedbackAnalysis(
            total_feedback=len(feedback),
            positive_rate=positive / len(feedback),
            negative_rate=negative / len(feedback),
            average_rating=avg_rating,
            common_issues=common_issues,
            queries_needing_review=review_queries
        )

    def get_corrections_for_truth_set(self) -> list[dict]:
        """Get corrections formatted for truth set updates."""
        corrections = [
            f for f in self._feedback
            if f.feedback_type == FeedbackType.CORRECTION and f.correct_answer
        ]

        return [
            {
                "query": c.query,
                "expected_answer": c.correct_answer,
                "original_answer": c.answer,
                "feedback_id": c.id
            }
            for c in corrections
        ]

    def export_for_training(self, output_path: str) -> None:
        """Export feedback for model fine-tuning."""
        training_data = []

        for f in self._feedback:
            if f.feedback_type == FeedbackType.CORRECTION and f.correct_answer:
                training_data.append({
                    "prompt": f.query,
                    "response": f.correct_answer,
                    "source": "user_correction"
                })
            elif f.score and f.score >= 0.8:
                training_data.append({
                    "prompt": f.query,
                    "response": f.answer,
                    "source": "positive_feedback"
                })

        with open(output_path, 'w') as f:
            json.dump(training_data, f, indent=2)
