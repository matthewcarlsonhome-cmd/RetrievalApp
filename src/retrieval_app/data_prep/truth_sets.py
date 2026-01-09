"""
Truth Set Management Module.

Essential for evaluating and improving RAG systems over time.
Without ground truth, you can't measure or improve retrieval quality.
"""

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class TruthSetEntry:
    """A single query-answer pair with expected retrieval results."""
    id: str
    query: str
    expected_answer: str
    relevant_chunk_ids: list[str]
    metadata: dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    tags: list[str] = field(default_factory=list)
    difficulty: str = "medium"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "TruthSetEntry":
        return cls(**data)


@dataclass
class EvaluationResult:
    """Result of evaluating retrieval against truth set."""
    entry_id: str
    query: str
    retrieved_chunk_ids: list[str]
    expected_chunk_ids: list[str]
    precision: float
    recall: float
    f1_score: float
    reciprocal_rank: float
    retrieved_in_top_k: dict[int, bool]


@dataclass
class TruthSetEvaluation:
    """Aggregated evaluation results across a truth set."""
    truth_set_name: str
    total_queries: int
    mean_precision: float
    mean_recall: float
    mean_f1: float
    mean_reciprocal_rank: float
    recall_at_k: dict[int, float]
    results: list[EvaluationResult]
    evaluated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class TruthSetManager:
    """
    Manages truth sets for RAG evaluation.

    Truth sets are critical for:
    1. Measuring retrieval quality (precision, recall, MRR)
    2. A/B testing different configurations
    3. Catching regressions before they hit production
    4. Building feedback loops for continuous improvement
    """

    def __init__(self, storage_path: str = "./truth_sets"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._truth_sets: dict[str, list[TruthSetEntry]] = {}

    def create_truth_set(self, name: str) -> None:
        """Create a new truth set."""
        self._truth_sets[name] = []
        self._save_truth_set(name)

    def add_entry(
        self,
        truth_set_name: str,
        query: str,
        expected_answer: str,
        relevant_chunk_ids: list[str],
        metadata: Optional[dict] = None,
        tags: Optional[list[str]] = None,
        difficulty: str = "medium"
    ) -> TruthSetEntry:
        """Add an entry to a truth set."""
        if truth_set_name not in self._truth_sets:
            self.create_truth_set(truth_set_name)

        entry = TruthSetEntry(
            id=str(uuid.uuid4()),
            query=query,
            expected_answer=expected_answer,
            relevant_chunk_ids=relevant_chunk_ids,
            metadata=metadata or {},
            tags=tags or [],
            difficulty=difficulty
        )

        self._truth_sets[truth_set_name].append(entry)
        self._save_truth_set(truth_set_name)

        return entry

    def get_truth_set(self, name: str) -> list[TruthSetEntry]:
        """Get all entries in a truth set."""
        if name not in self._truth_sets:
            self._load_truth_set(name)
        return self._truth_sets.get(name, [])

    def evaluate_retrieval(
        self,
        truth_set_name: str,
        retrieval_fn: callable,
        k_values: list[int] = [1, 3, 5, 10]
    ) -> TruthSetEvaluation:
        """
        Evaluate a retrieval function against a truth set.

        Args:
            truth_set_name: Name of the truth set to evaluate against
            retrieval_fn: Function that takes a query and returns list of chunk IDs
            k_values: K values for recall@k calculation

        Returns:
            TruthSetEvaluation with aggregated metrics
        """
        entries = self.get_truth_set(truth_set_name)
        if not entries:
            raise ValueError(f"Truth set '{truth_set_name}' is empty or doesn't exist")

        results = []
        for entry in entries:
            retrieved_ids = retrieval_fn(entry.query)
            result = self._evaluate_single(entry, retrieved_ids, k_values)
            results.append(result)

        recall_at_k = {k: 0.0 for k in k_values}
        for k in k_values:
            recall_at_k[k] = sum(
                1 for r in results if r.retrieved_in_top_k.get(k, False)
            ) / len(results)

        return TruthSetEvaluation(
            truth_set_name=truth_set_name,
            total_queries=len(results),
            mean_precision=sum(r.precision for r in results) / len(results),
            mean_recall=sum(r.recall for r in results) / len(results),
            mean_f1=sum(r.f1_score for r in results) / len(results),
            mean_reciprocal_rank=sum(r.reciprocal_rank for r in results) / len(results),
            recall_at_k=recall_at_k,
            results=results
        )

    def _evaluate_single(
        self,
        entry: TruthSetEntry,
        retrieved_ids: list[str],
        k_values: list[int]
    ) -> EvaluationResult:
        """Evaluate retrieval for a single query."""
        expected_set = set(entry.relevant_chunk_ids)
        retrieved_set = set(retrieved_ids)

        true_positives = len(expected_set & retrieved_set)
        precision = true_positives / len(retrieved_ids) if retrieved_ids else 0
        recall = true_positives / len(expected_set) if expected_set else 0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0 else 0
        )

        reciprocal_rank = 0.0
        for i, chunk_id in enumerate(retrieved_ids):
            if chunk_id in expected_set:
                reciprocal_rank = 1.0 / (i + 1)
                break

        retrieved_in_top_k = {}
        for k in k_values:
            top_k_set = set(retrieved_ids[:k])
            retrieved_in_top_k[k] = bool(expected_set & top_k_set)

        return EvaluationResult(
            entry_id=entry.id,
            query=entry.query,
            retrieved_chunk_ids=retrieved_ids,
            expected_chunk_ids=entry.relevant_chunk_ids,
            precision=precision,
            recall=recall,
            f1_score=f1,
            reciprocal_rank=reciprocal_rank,
            retrieved_in_top_k=retrieved_in_top_k
        )

    def _save_truth_set(self, name: str) -> None:
        """Save a truth set to disk."""
        path = self.storage_path / f"{name}.json"
        entries = self._truth_sets.get(name, [])
        data = [e.to_dict() for e in entries]
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    def _load_truth_set(self, name: str) -> None:
        """Load a truth set from disk."""
        path = self.storage_path / f"{name}.json"
        if path.exists():
            with open(path, 'r') as f:
                data = json.load(f)
            self._truth_sets[name] = [TruthSetEntry.from_dict(d) for d in data]
        else:
            self._truth_sets[name] = []

    def export_for_annotation(
        self,
        truth_set_name: str,
        output_path: str
    ) -> None:
        """Export truth set in a format suitable for human annotation."""
        entries = self.get_truth_set(truth_set_name)
        export_data = []

        for entry in entries:
            export_data.append({
                "id": entry.id,
                "query": entry.query,
                "expected_answer": entry.expected_answer,
                "relevant_chunks": entry.relevant_chunk_ids,
                "annotator_notes": "",
                "is_correct": None,
                "suggested_improvements": ""
            })

        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)

    def import_annotations(
        self,
        truth_set_name: str,
        annotations_path: str
    ) -> None:
        """Import human annotations to update truth set."""
        with open(annotations_path, 'r') as f:
            annotations = json.load(f)

        entries = {e.id: e for e in self.get_truth_set(truth_set_name)}

        for annotation in annotations:
            entry_id = annotation.get("id")
            if entry_id in entries:
                entry = entries[entry_id]
                if annotation.get("relevant_chunks"):
                    entry.relevant_chunk_ids = annotation["relevant_chunks"]
                if annotation.get("expected_answer"):
                    entry.expected_answer = annotation["expected_answer"]
                entry.metadata["last_annotated"] = datetime.utcnow().isoformat()
                if annotation.get("annotator_notes"):
                    entry.metadata["annotator_notes"] = annotation["annotator_notes"]

        self._truth_sets[truth_set_name] = list(entries.values())
        self._save_truth_set(truth_set_name)
