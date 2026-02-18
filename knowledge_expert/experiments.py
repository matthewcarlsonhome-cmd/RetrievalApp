"""
Experimental Framework for Testing Chunking and Retrieval Strategies.

This module provides tools to:
1. Run A/B tests on different chunking strategies
2. Compare retrieval quality across configurations
3. Track chunk-level performance metrics
4. Export data for external analysis and model training
"""

import json
import uuid
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from contextlib import contextmanager
import statistics

from .config import config
from .ingestion.chunker import (
    chunk_text,
    chunk_with_sections,
    ChunkingConfig,
    ChunkingStrategy,
    get_available_strategies,
    get_recommended_chunk_size,
    TextChunk
)
from .ingestion.parsers import parse_document, get_file_category

logger = logging.getLogger(__name__)


# =============================================================================
# DATA MODELS FOR EXPERIMENTS
# =============================================================================

@dataclass
class ExperimentConfig:
    """Configuration for a chunking/retrieval experiment."""
    id: str = None
    name: str = ""
    description: str = ""

    # Chunking parameters
    chunking_strategy: str = "sentence"
    chunk_size: int = 500
    chunk_overlap: int = 50

    # Retrieval parameters
    semantic_weight: float = 0.7
    keyword_weight: float = 0.2
    qa_weight: float = 0.1
    top_k: int = 5

    # Embedding model
    embedding_model: str = "all-MiniLM-L6-v2"

    # Metadata
    created_at: str = None
    is_active: bool = True
    is_control: bool = False  # Control group for A/B testing

    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()


@dataclass
class ExperimentResult:
    """Results from a single query in an experiment."""
    id: str = None
    experiment_id: str = ""
    query_text: str = ""
    response_text: str = ""

    # Chunks used
    chunk_ids: List[str] = field(default_factory=list)
    chunk_scores: List[float] = field(default_factory=list)
    chunk_strategies: List[str] = field(default_factory=list)

    # Performance metrics
    response_time_ms: int = 0
    total_chunks_searched: int = 0
    chunks_above_threshold: int = 0

    # Quality metrics (from feedback)
    feedback: str = None  # positive, negative, null
    feedback_score: int = None  # 1-5 rating
    feedback_comment: str = None

    # Computed metrics
    avg_chunk_score: float = 0.0
    max_chunk_score: float = 0.0
    min_chunk_score: float = 0.0

    created_at: str = None

    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()

        # Compute score metrics
        if self.chunk_scores:
            self.avg_chunk_score = statistics.mean(self.chunk_scores)
            self.max_chunk_score = max(self.chunk_scores)
            self.min_chunk_score = min(self.chunk_scores)


@dataclass
class ChunkPerformance:
    """Performance metrics for a specific chunk."""
    chunk_id: str
    document_id: str
    strategy: str
    chunk_size: int

    # Usage stats
    times_retrieved: int = 0
    times_led_to_positive: int = 0
    times_led_to_negative: int = 0

    # Score stats
    avg_retrieval_score: float = 0.0
    retrieval_scores: List[float] = field(default_factory=list)

    @property
    def positive_rate(self) -> float:
        """Rate of positive feedback when this chunk was used."""
        total = self.times_led_to_positive + self.times_led_to_negative
        if total == 0:
            return 0.0
        return self.times_led_to_positive / total


@dataclass
class StrategyComparison:
    """Comparison metrics between chunking strategies."""
    strategy_a: str
    strategy_b: str

    # Sample sizes
    queries_a: int = 0
    queries_b: int = 0

    # Feedback metrics
    positive_rate_a: float = 0.0
    positive_rate_b: float = 0.0

    # Performance metrics
    avg_response_time_a: float = 0.0
    avg_response_time_b: float = 0.0

    avg_chunk_score_a: float = 0.0
    avg_chunk_score_b: float = 0.0

    # Statistical significance
    p_value: float = None
    is_significant: bool = False
    winner: str = None


# =============================================================================
# EXPERIMENT MANAGER
# =============================================================================

class ExperimentManager:
    """
    Manages experiments for testing chunking and retrieval strategies.

    Usage:
        manager = ExperimentManager()

        # Create experiments
        exp_a = manager.create_experiment("Sentence 500", strategy="sentence", chunk_size=500)
        exp_b = manager.create_experiment("Paragraph 300", strategy="paragraph", chunk_size=300)

        # Run A/B test
        manager.set_ab_test(exp_a.id, exp_b.id)

        # Get experiment for a query (randomly assigned)
        exp = manager.get_active_experiment()

        # Record result
        manager.record_result(exp.id, query, response, chunks, feedback)

        # Analyze results
        comparison = manager.compare_strategies()
        report = manager.generate_report()
    """

    def __init__(self, db_path: Path = None):
        self.db_path = db_path or config.SQLITE_DB_PATH.parent / "experiments.db"
        self._init_db()
        self._ab_test_experiments: List[str] = []
        self._current_ab_index = 0

    @contextmanager
    def _get_conn(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self):
        """Initialize experiment database."""
        with self._get_conn() as conn:
            conn.executescript("""
                -- Experiment configurations
                CREATE TABLE IF NOT EXISTS experiments (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    chunking_strategy TEXT,
                    chunk_size INTEGER,
                    chunk_overlap INTEGER,
                    semantic_weight REAL,
                    keyword_weight REAL,
                    qa_weight REAL,
                    top_k INTEGER,
                    embedding_model TEXT,
                    created_at TEXT,
                    is_active INTEGER DEFAULT 1,
                    is_control INTEGER DEFAULT 0
                );

                -- Experiment results (per query)
                CREATE TABLE IF NOT EXISTS experiment_results (
                    id TEXT PRIMARY KEY,
                    experiment_id TEXT NOT NULL,
                    query_text TEXT NOT NULL,
                    response_text TEXT,
                    chunk_ids TEXT,
                    chunk_scores TEXT,
                    chunk_strategies TEXT,
                    response_time_ms INTEGER,
                    total_chunks_searched INTEGER,
                    chunks_above_threshold INTEGER,
                    feedback TEXT,
                    feedback_score INTEGER,
                    feedback_comment TEXT,
                    avg_chunk_score REAL,
                    max_chunk_score REAL,
                    min_chunk_score REAL,
                    created_at TEXT,
                    FOREIGN KEY (experiment_id) REFERENCES experiments(id)
                );

                -- Chunk-level performance tracking
                CREATE TABLE IF NOT EXISTS chunk_performance (
                    chunk_id TEXT PRIMARY KEY,
                    document_id TEXT,
                    strategy TEXT,
                    chunk_size INTEGER,
                    times_retrieved INTEGER DEFAULT 0,
                    times_led_to_positive INTEGER DEFAULT 0,
                    times_led_to_negative INTEGER DEFAULT 0,
                    avg_retrieval_score REAL DEFAULT 0,
                    retrieval_scores TEXT DEFAULT '[]'
                );

                -- Document-level experiment tracking
                CREATE TABLE IF NOT EXISTS document_experiments (
                    id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    experiment_id TEXT NOT NULL,
                    chunk_count INTEGER,
                    strategy_used TEXT,
                    chunk_size_used INTEGER,
                    created_at TEXT,
                    FOREIGN KEY (experiment_id) REFERENCES experiments(id)
                );

                -- Indexes
                CREATE INDEX IF NOT EXISTS idx_results_exp ON experiment_results(experiment_id);
                CREATE INDEX IF NOT EXISTS idx_results_feedback ON experiment_results(feedback);
                CREATE INDEX IF NOT EXISTS idx_chunk_perf_strategy ON chunk_performance(strategy);
                CREATE INDEX IF NOT EXISTS idx_doc_exp_doc ON document_experiments(document_id);
            """)

    # -------------------------------------------------------------------------
    # Experiment CRUD
    # -------------------------------------------------------------------------

    def create_experiment(
        self,
        name: str,
        description: str = "",
        strategy: str = "sentence",
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.2,
        qa_weight: float = 0.1,
        top_k: int = 5,
        is_control: bool = False
    ) -> ExperimentConfig:
        """Create a new experiment configuration."""
        exp = ExperimentConfig(
            name=name,
            description=description,
            chunking_strategy=strategy,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            semantic_weight=semantic_weight,
            keyword_weight=keyword_weight,
            qa_weight=qa_weight,
            top_k=top_k,
            is_control=is_control
        )

        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO experiments
                (id, name, description, chunking_strategy, chunk_size, chunk_overlap,
                 semantic_weight, keyword_weight, qa_weight, top_k, embedding_model,
                 created_at, is_active, is_control)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                exp.id, exp.name, exp.description, exp.chunking_strategy,
                exp.chunk_size, exp.chunk_overlap, exp.semantic_weight,
                exp.keyword_weight, exp.qa_weight, exp.top_k, exp.embedding_model,
                exp.created_at, 1 if exp.is_active else 0, 1 if exp.is_control else 0
            ))

        logger.info(f"Created experiment: {exp.name} (ID: {exp.id})")
        return exp

    def get_experiment(self, exp_id: str) -> Optional[ExperimentConfig]:
        """Get an experiment by ID."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM experiments WHERE id = ?", (exp_id,)
            ).fetchone()

            if row:
                return self._row_to_experiment(row)
        return None

    def get_all_experiments(self, active_only: bool = False) -> List[ExperimentConfig]:
        """Get all experiments."""
        with self._get_conn() as conn:
            if active_only:
                rows = conn.execute(
                    "SELECT * FROM experiments WHERE is_active = 1 ORDER BY created_at DESC"
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM experiments ORDER BY created_at DESC"
                ).fetchall()

            return [self._row_to_experiment(row) for row in rows]

    def deactivate_experiment(self, exp_id: str):
        """Deactivate an experiment."""
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE experiments SET is_active = 0 WHERE id = ?", (exp_id,)
            )

    def _row_to_experiment(self, row) -> ExperimentConfig:
        """Convert database row to ExperimentConfig."""
        return ExperimentConfig(
            id=row['id'],
            name=row['name'],
            description=row['description'],
            chunking_strategy=row['chunking_strategy'],
            chunk_size=row['chunk_size'],
            chunk_overlap=row['chunk_overlap'],
            semantic_weight=row['semantic_weight'],
            keyword_weight=row['keyword_weight'],
            qa_weight=row['qa_weight'],
            top_k=row['top_k'],
            embedding_model=row['embedding_model'],
            created_at=row['created_at'],
            is_active=bool(row['is_active']),
            is_control=bool(row['is_control'])
        )

    # -------------------------------------------------------------------------
    # A/B Testing
    # -------------------------------------------------------------------------

    def set_ab_test(self, experiment_a_id: str, experiment_b_id: str):
        """Set up an A/B test between two experiments."""
        self._ab_test_experiments = [experiment_a_id, experiment_b_id]
        self._current_ab_index = 0
        logger.info(f"A/B test configured: {experiment_a_id} vs {experiment_b_id}")

    def get_active_experiment(self) -> Optional[ExperimentConfig]:
        """
        Get the experiment to use for the current query.
        Alternates between A/B test experiments if configured.
        """
        if self._ab_test_experiments:
            exp_id = self._ab_test_experiments[self._current_ab_index]
            self._current_ab_index = (self._current_ab_index + 1) % len(self._ab_test_experiments)
            return self.get_experiment(exp_id)

        # Return first active experiment
        experiments = self.get_all_experiments(active_only=True)
        return experiments[0] if experiments else None

    def get_ab_assignment(self, session_id: str) -> Optional[ExperimentConfig]:
        """
        Get consistent A/B assignment based on session ID.
        Ensures same user always gets same experiment.
        """
        if not self._ab_test_experiments:
            return self.get_active_experiment()

        # Use hash to consistently assign
        index = hash(session_id) % len(self._ab_test_experiments)
        return self.get_experiment(self._ab_test_experiments[index])

    # -------------------------------------------------------------------------
    # Result Recording
    # -------------------------------------------------------------------------

    def record_result(
        self,
        experiment_id: str,
        query_text: str,
        response_text: str,
        chunk_ids: List[str],
        chunk_scores: List[float],
        chunk_strategies: List[str] = None,
        response_time_ms: int = 0,
        total_chunks_searched: int = 0,
        feedback: str = None,
        feedback_score: int = None,
        feedback_comment: str = None
    ) -> ExperimentResult:
        """Record a query result for an experiment."""
        result = ExperimentResult(
            experiment_id=experiment_id,
            query_text=query_text,
            response_text=response_text,
            chunk_ids=chunk_ids,
            chunk_scores=chunk_scores,
            chunk_strategies=chunk_strategies or [],
            response_time_ms=response_time_ms,
            total_chunks_searched=total_chunks_searched,
            chunks_above_threshold=len(chunk_ids),
            feedback=feedback,
            feedback_score=feedback_score,
            feedback_comment=feedback_comment
        )

        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO experiment_results
                (id, experiment_id, query_text, response_text, chunk_ids, chunk_scores,
                 chunk_strategies, response_time_ms, total_chunks_searched,
                 chunks_above_threshold, feedback, feedback_score, feedback_comment,
                 avg_chunk_score, max_chunk_score, min_chunk_score, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.id, result.experiment_id, result.query_text, result.response_text,
                json.dumps(result.chunk_ids), json.dumps(result.chunk_scores),
                json.dumps(result.chunk_strategies), result.response_time_ms,
                result.total_chunks_searched, result.chunks_above_threshold,
                result.feedback, result.feedback_score, result.feedback_comment,
                result.avg_chunk_score, result.max_chunk_score, result.min_chunk_score,
                result.created_at
            ))

            # Update chunk performance
            self._update_chunk_performance(conn, chunk_ids, chunk_scores, feedback)

        return result

    def update_result_feedback(
        self,
        result_id: str,
        feedback: str,
        feedback_score: int = None,
        feedback_comment: str = None
    ):
        """Update feedback for a result."""
        with self._get_conn() as conn:
            # Get existing result
            row = conn.execute(
                "SELECT chunk_ids, chunk_scores FROM experiment_results WHERE id = ?",
                (result_id,)
            ).fetchone()

            if row:
                chunk_ids = json.loads(row['chunk_ids'])
                chunk_scores = json.loads(row['chunk_scores'])

                # Update result
                conn.execute("""
                    UPDATE experiment_results
                    SET feedback = ?, feedback_score = ?, feedback_comment = ?
                    WHERE id = ?
                """, (feedback, feedback_score, feedback_comment, result_id))

                # Update chunk performance
                self._update_chunk_performance(conn, chunk_ids, chunk_scores, feedback)

    def _update_chunk_performance(
        self,
        conn,
        chunk_ids: List[str],
        chunk_scores: List[float],
        feedback: str
    ):
        """Update chunk-level performance metrics."""
        for i, chunk_id in enumerate(chunk_ids):
            score = chunk_scores[i] if i < len(chunk_scores) else 0.0

            # Check if chunk exists
            row = conn.execute(
                "SELECT * FROM chunk_performance WHERE chunk_id = ?", (chunk_id,)
            ).fetchone()

            if row:
                # Update existing
                scores = json.loads(row['retrieval_scores'])
                scores.append(score)
                avg_score = statistics.mean(scores)

                positive_delta = 1 if feedback == 'positive' else 0
                negative_delta = 1 if feedback == 'negative' else 0

                conn.execute("""
                    UPDATE chunk_performance
                    SET times_retrieved = times_retrieved + 1,
                        times_led_to_positive = times_led_to_positive + ?,
                        times_led_to_negative = times_led_to_negative + ?,
                        avg_retrieval_score = ?,
                        retrieval_scores = ?
                    WHERE chunk_id = ?
                """, (positive_delta, negative_delta, avg_score, json.dumps(scores), chunk_id))
            else:
                # Insert new
                positive = 1 if feedback == 'positive' else 0
                negative = 1 if feedback == 'negative' else 0

                conn.execute("""
                    INSERT INTO chunk_performance
                    (chunk_id, document_id, strategy, chunk_size, times_retrieved,
                     times_led_to_positive, times_led_to_negative, avg_retrieval_score,
                     retrieval_scores)
                    VALUES (?, '', '', 0, 1, ?, ?, ?, ?)
                """, (chunk_id, positive, negative, score, json.dumps([score])))

    # -------------------------------------------------------------------------
    # Analysis & Reporting
    # -------------------------------------------------------------------------

    def get_experiment_stats(self, experiment_id: str) -> Dict[str, Any]:
        """Get statistics for a specific experiment."""
        with self._get_conn() as conn:
            # Basic counts
            total = conn.execute(
                "SELECT COUNT(*) FROM experiment_results WHERE experiment_id = ?",
                (experiment_id,)
            ).fetchone()[0]

            positive = conn.execute(
                "SELECT COUNT(*) FROM experiment_results WHERE experiment_id = ? AND feedback = 'positive'",
                (experiment_id,)
            ).fetchone()[0]

            negative = conn.execute(
                "SELECT COUNT(*) FROM experiment_results WHERE experiment_id = ? AND feedback = 'negative'",
                (experiment_id,)
            ).fetchone()[0]

            # Averages
            avgs = conn.execute("""
                SELECT
                    AVG(response_time_ms) as avg_response_time,
                    AVG(avg_chunk_score) as avg_chunk_score,
                    AVG(chunks_above_threshold) as avg_chunks_used
                FROM experiment_results
                WHERE experiment_id = ?
            """, (experiment_id,)).fetchone()

            feedback_total = positive + negative
            positive_rate = positive / feedback_total if feedback_total > 0 else 0

            return {
                "experiment_id": experiment_id,
                "total_queries": total,
                "positive_feedback": positive,
                "negative_feedback": negative,
                "no_feedback": total - feedback_total,
                "positive_rate": positive_rate,
                "avg_response_time_ms": avgs['avg_response_time'] or 0,
                "avg_chunk_score": avgs['avg_chunk_score'] or 0,
                "avg_chunks_used": avgs['avg_chunks_used'] or 0
            }

    def compare_experiments(
        self,
        experiment_a_id: str,
        experiment_b_id: str
    ) -> StrategyComparison:
        """Compare two experiments."""
        stats_a = self.get_experiment_stats(experiment_a_id)
        stats_b = self.get_experiment_stats(experiment_b_id)

        exp_a = self.get_experiment(experiment_a_id)
        exp_b = self.get_experiment(experiment_b_id)

        comparison = StrategyComparison(
            strategy_a=exp_a.chunking_strategy if exp_a else "unknown",
            strategy_b=exp_b.chunking_strategy if exp_b else "unknown",
            queries_a=stats_a['total_queries'],
            queries_b=stats_b['total_queries'],
            positive_rate_a=stats_a['positive_rate'],
            positive_rate_b=stats_b['positive_rate'],
            avg_response_time_a=stats_a['avg_response_time_ms'],
            avg_response_time_b=stats_b['avg_response_time_ms'],
            avg_chunk_score_a=stats_a['avg_chunk_score'],
            avg_chunk_score_b=stats_b['avg_chunk_score']
        )

        # Determine winner (simple comparison)
        if comparison.positive_rate_a > comparison.positive_rate_b + 0.05:
            comparison.winner = comparison.strategy_a
        elif comparison.positive_rate_b > comparison.positive_rate_a + 0.05:
            comparison.winner = comparison.strategy_b
        else:
            comparison.winner = "tie"

        return comparison

    def get_chunk_performance_by_strategy(self) -> Dict[str, Dict[str, Any]]:
        """Get aggregated chunk performance by strategy."""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT
                    strategy,
                    COUNT(*) as chunk_count,
                    SUM(times_retrieved) as total_retrievals,
                    SUM(times_led_to_positive) as total_positive,
                    SUM(times_led_to_negative) as total_negative,
                    AVG(avg_retrieval_score) as avg_score
                FROM chunk_performance
                WHERE strategy != ''
                GROUP BY strategy
            """).fetchall()

            results = {}
            for row in rows:
                strategy = row['strategy']
                total_feedback = row['total_positive'] + row['total_negative']
                positive_rate = row['total_positive'] / total_feedback if total_feedback > 0 else 0

                results[strategy] = {
                    "chunk_count": row['chunk_count'],
                    "total_retrievals": row['total_retrievals'],
                    "total_positive": row['total_positive'],
                    "total_negative": row['total_negative'],
                    "positive_rate": positive_rate,
                    "avg_retrieval_score": row['avg_score'] or 0
                }

            return results

    def get_best_performing_chunks(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get the best performing chunks by positive feedback rate."""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT *,
                    CASE WHEN (times_led_to_positive + times_led_to_negative) > 0
                         THEN CAST(times_led_to_positive AS REAL) /
                              (times_led_to_positive + times_led_to_negative)
                         ELSE 0 END as positive_rate
                FROM chunk_performance
                WHERE times_retrieved >= 3
                ORDER BY positive_rate DESC, times_retrieved DESC
                LIMIT ?
            """, (limit,)).fetchall()

            return [dict(row) for row in rows]

    def get_worst_performing_chunks(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get the worst performing chunks by negative feedback rate."""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT *,
                    CASE WHEN (times_led_to_positive + times_led_to_negative) > 0
                         THEN CAST(times_led_to_negative AS REAL) /
                              (times_led_to_positive + times_led_to_negative)
                         ELSE 0 END as negative_rate
                FROM chunk_performance
                WHERE times_retrieved >= 3
                ORDER BY negative_rate DESC, times_retrieved DESC
                LIMIT ?
            """, (limit,)).fetchall()

            return [dict(row) for row in rows]

    def generate_report(self) -> Dict[str, Any]:
        """Generate a comprehensive experiment report."""
        experiments = self.get_all_experiments()

        report = {
            "generated_at": datetime.utcnow().isoformat(),
            "experiments": [],
            "strategy_comparison": {},
            "recommendations": []
        }

        # Per-experiment stats
        for exp in experiments:
            stats = self.get_experiment_stats(exp.id)
            stats["name"] = exp.name
            stats["config"] = {
                "strategy": exp.chunking_strategy,
                "chunk_size": exp.chunk_size,
                "chunk_overlap": exp.chunk_overlap,
                "weights": {
                    "semantic": exp.semantic_weight,
                    "keyword": exp.keyword_weight,
                    "qa": exp.qa_weight
                }
            }
            report["experiments"].append(stats)

        # Strategy comparison
        report["strategy_comparison"] = self.get_chunk_performance_by_strategy()

        # Generate recommendations
        report["recommendations"] = self._generate_recommendations(report)

        return report

    def _generate_recommendations(self, report: Dict) -> List[str]:
        """Generate recommendations based on experiment data."""
        recommendations = []

        # Find best strategy
        strategy_perf = report.get("strategy_comparison", {})
        if strategy_perf:
            best_strategy = max(
                strategy_perf.items(),
                key=lambda x: x[1].get('positive_rate', 0)
            )
            if best_strategy[1].get('positive_rate', 0) > 0.6:
                recommendations.append(
                    f"Strategy '{best_strategy[0]}' shows strong performance "
                    f"({best_strategy[1]['positive_rate']:.1%} positive rate). "
                    f"Consider using it as default."
                )

        # Find experiments needing more data
        for exp in report.get("experiments", []):
            if exp.get("total_queries", 0) < 20:
                recommendations.append(
                    f"Experiment '{exp.get('name')}' has insufficient data "
                    f"({exp.get('total_queries')} queries). Collect more samples."
                )

        # Check for underperforming chunks
        worst_chunks = self.get_worst_performing_chunks(5)
        if worst_chunks:
            high_negative = [c for c in worst_chunks if c.get('negative_rate', 0) > 0.5]
            if high_negative:
                recommendations.append(
                    f"Found {len(high_negative)} chunks with >50% negative feedback. "
                    f"Consider reviewing and re-chunking these documents."
                )

        return recommendations

    # -------------------------------------------------------------------------
    # Export Functions
    # -------------------------------------------------------------------------

    def export_training_data(
        self,
        experiment_id: str = None,
        positive_only: bool = True,
        format: str = "jsonl"
    ) -> str:
        """
        Export query-response pairs for fine-tuning.

        Args:
            experiment_id: Filter by experiment (None for all)
            positive_only: Only include positive feedback responses
            format: Output format ('jsonl', 'json', 'csv')

        Returns:
            Formatted string of training data
        """
        with self._get_conn() as conn:
            query = """
                SELECT query_text, response_text, feedback, chunk_ids, chunk_scores
                FROM experiment_results
            """
            params = []

            conditions = []
            if experiment_id:
                conditions.append("experiment_id = ?")
                params.append(experiment_id)
            if positive_only:
                conditions.append("feedback = 'positive'")

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            rows = conn.execute(query, params).fetchall()

        if format == "jsonl":
            lines = []
            for row in rows:
                entry = {
                    "messages": [
                        {"role": "user", "content": row['query_text']},
                        {"role": "assistant", "content": row['response_text']}
                    ],
                    "metadata": {
                        "feedback": row['feedback'],
                        "chunks_used": json.loads(row['chunk_ids']),
                        "chunk_scores": json.loads(row['chunk_scores'])
                    }
                }
                lines.append(json.dumps(entry))
            return "\n".join(lines)

        elif format == "json":
            data = []
            for row in rows:
                data.append({
                    "query": row['query_text'],
                    "response": row['response_text'],
                    "feedback": row['feedback'],
                    "chunks_used": json.loads(row['chunk_ids']),
                    "chunk_scores": json.loads(row['chunk_scores'])
                })
            return json.dumps(data, indent=2)

        elif format == "csv":
            import csv
            from io import StringIO
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow(["query", "response", "feedback"])
            for row in rows:
                writer.writerow([row['query_text'], row['response_text'], row['feedback']])
            return output.getvalue()

        return ""

    def export_chunk_analysis(self) -> str:
        """Export chunk performance analysis as JSON."""
        best = self.get_best_performing_chunks(50)
        worst = self.get_worst_performing_chunks(50)
        by_strategy = self.get_chunk_performance_by_strategy()

        analysis = {
            "exported_at": datetime.utcnow().isoformat(),
            "best_performing_chunks": best,
            "worst_performing_chunks": worst,
            "performance_by_strategy": by_strategy
        }

        return json.dumps(analysis, indent=2)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_default_experiments() -> List[ExperimentConfig]:
    """Create a set of default experiments for comparison."""
    manager = ExperimentManager()

    experiments = [
        # Control: Default settings
        manager.create_experiment(
            name="Control (Sentence 500)",
            description="Default sentence-based chunking with 500 token chunks",
            strategy="sentence",
            chunk_size=500,
            is_control=True
        ),
        # Smaller chunks
        manager.create_experiment(
            name="Small Chunks (Sentence 300)",
            description="Smaller sentence chunks for more precise retrieval",
            strategy="sentence",
            chunk_size=300,
            chunk_overlap=30
        ),
        # Larger chunks
        manager.create_experiment(
            name="Large Chunks (Sentence 800)",
            description="Larger chunks for more context",
            strategy="sentence",
            chunk_size=800,
            chunk_overlap=80
        ),
        # Paragraph-based
        manager.create_experiment(
            name="Paragraph 400",
            description="Paragraph-based chunking",
            strategy="paragraph",
            chunk_size=400
        ),
        # Semantic
        manager.create_experiment(
            name="Semantic 500",
            description="Semantic boundary chunking",
            strategy="semantic",
            chunk_size=500
        ),
        # Different retrieval weights
        manager.create_experiment(
            name="High Semantic Weight",
            description="90% semantic, 10% keyword",
            strategy="sentence",
            chunk_size=500,
            semantic_weight=0.9,
            keyword_weight=0.1,
            qa_weight=0.0
        ),
        manager.create_experiment(
            name="Balanced Weights",
            description="Equal semantic and keyword",
            strategy="sentence",
            chunk_size=500,
            semantic_weight=0.5,
            keyword_weight=0.5,
            qa_weight=0.0
        )
    ]

    return experiments


def run_chunk_size_experiment(
    document_text: str,
    sizes: List[int] = None
) -> Dict[int, List[TextChunk]]:
    """
    Run an experiment comparing different chunk sizes on the same document.

    Returns dict mapping chunk_size -> resulting chunks.
    """
    sizes = sizes or [200, 300, 400, 500, 600, 800, 1000]
    results = {}

    for size in sizes:
        chunks = chunk_text(document_text, chunk_size=size, overlap=size // 10)
        results[size] = chunks
        logger.info(f"Chunk size {size}: {len(chunks)} chunks")

    return results


def run_strategy_experiment(
    document_text: str,
    strategies: List[str] = None
) -> Dict[str, List[TextChunk]]:
    """
    Run an experiment comparing different chunking strategies.

    Returns dict mapping strategy -> resulting chunks.
    """
    strategies = strategies or ["sentence", "paragraph", "semantic", "hybrid", "sliding"]
    results = {}

    for strategy in strategies:
        try:
            chunks = chunk_text(document_text, strategy=strategy, chunk_size=500)
            results[strategy] = chunks
            logger.info(f"Strategy '{strategy}': {len(chunks)} chunks")
        except Exception as e:
            logger.error(f"Strategy '{strategy}' failed: {e}")

    return results


# Global experiment manager instance
experiment_manager = ExperimentManager()
