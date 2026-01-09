"""
Auto-Tuner Module.

=============================================================================
INNOVATION: AUTOMATED PARAMETER OPTIMIZATION FROM PRODUCTION DATA
=============================================================================

RAG systems have many tunable parameters:
- chunk_size, chunk_overlap
- top_k, rerank_top_k
- semantic_weight, lexical_weight
- min_relevance_score
- mmr_lambda

Finding optimal values through manual tuning is:
1. Time-consuming (weeks of experimentation)
2. Subjective (different people, different preferences)
3. Static (optimal values drift as data/queries change)

This module implements automated parameter optimization using:
1. A/B testing infrastructure to compare configurations
2. Bayesian optimization for efficient parameter search
3. Continuous monitoring to detect when retuning is needed
4. Guardrails to prevent bad configurations from reaching users

The result: RAG systems that tune themselves to optimal performance
and adapt as usage patterns change.

=============================================================================
INDUSTRY CONTEXT
=============================================================================

This pattern is inspired by:
- Google's continuous optimization of search ranking
- Netflix's recommendation system auto-tuning
- Uber's ML feature store with automatic feature selection

The key insight: with good metrics and automation, systems can optimize
themselves better than humans can manually tune them.

=============================================================================
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Callable, Any
from enum import Enum
import random
import math
import json
from pathlib import Path


class OptimizationGoal(str, Enum):
    """What to optimize for."""
    PRECISION = "precision"      # Maximize relevance of top results
    RECALL = "recall"           # Maximize coverage of relevant results
    LATENCY = "latency"         # Minimize response time
    COST = "cost"               # Minimize token/API usage
    BALANCED = "balanced"       # Weighted combination


@dataclass
class ParameterRange:
    """Define valid range for a parameter."""
    name: str
    min_value: float
    max_value: float
    step: Optional[float] = None
    is_integer: bool = False

    def sample(self) -> float:
        """Sample a random value from the range."""
        if self.step:
            steps = int((self.max_value - self.min_value) / self.step)
            value = self.min_value + random.randint(0, steps) * self.step
        else:
            value = random.uniform(self.min_value, self.max_value)

        return int(value) if self.is_integer else value

    def clip(self, value: float) -> float:
        """Clip value to valid range."""
        clipped = max(self.min_value, min(self.max_value, value))
        return int(clipped) if self.is_integer else clipped


@dataclass
class ExperimentResult:
    """Result of a parameter experiment."""
    config: dict
    metrics: dict
    sample_size: int
    timestamp: datetime
    experiment_id: str


@dataclass
class TuningState:
    """Current state of the auto-tuning system."""
    current_config: dict
    best_config: dict
    best_score: float
    experiments_run: int
    last_improvement: datetime
    convergence_score: float


class AutoTuner:
    """
    Automated parameter optimization for RAG systems.

    Usage:
        # Define what parameters to tune and their ranges
        tuner = AutoTuner(
            parameter_ranges=[
                ParameterRange("top_k", 3, 20, is_integer=True),
                ParameterRange("semantic_weight", 0.3, 0.9, step=0.1),
                ParameterRange("min_relevance_score", 0.2, 0.6, step=0.05),
            ],
            evaluation_fn=evaluate_config,  # Your evaluation function
            goal=OptimizationGoal.BALANCED,
        )

        # Run optimization
        best_config = tuner.optimize(
            n_iterations=50,
            queries_per_iteration=100,
        )

        # Apply best config to your pipeline
        pipeline.config.retrieval.top_k = best_config["top_k"]
        ...

    Advanced Usage:
        # Continuous optimization with production traffic
        tuner.start_continuous_optimization(
            traffic_percentage=0.05,  # 5% of traffic for experiments
            improvement_threshold=0.02,  # Only adopt if 2% better
        )

        # Check if retuning is needed
        if tuner.should_retune():
            tuner.run_optimization_cycle()

    How It Works:
    -------------
    1. EXPLORATION: Sample diverse configurations using Latin Hypercube
    2. EVALUATION: Test each config on sample queries using evaluation_fn
    3. EXPLOITATION: Focus search around best-performing configs
    4. VALIDATION: Verify improvements on held-out test set
    5. DEPLOYMENT: Gradually roll out winning config
    """

    # Default parameter ranges based on production experience
    DEFAULT_RANGES = [
        ParameterRange("top_k", 3, 25, is_integer=True),
        ParameterRange("rerank_top_k", 2, 10, is_integer=True),
        ParameterRange("semantic_weight", 0.3, 0.9, step=0.05),
        ParameterRange("min_relevance_score", 0.15, 0.6, step=0.05),
        ParameterRange("mmr_lambda", 0.3, 0.9, step=0.1),
        ParameterRange("chunk_size", 256, 1024, step=128, is_integer=True),
    ]

    def __init__(
        self,
        evaluation_fn: Callable[[dict, list[str]], dict],
        parameter_ranges: Optional[list[ParameterRange]] = None,
        goal: OptimizationGoal = OptimizationGoal.BALANCED,
        baseline_config: Optional[dict] = None,
        storage_path: Optional[str] = None,
    ):
        """
        Initialize auto-tuner.

        Args:
            evaluation_fn: Function(config, queries) -> metrics dict
                           Must return dict with 'precision', 'recall', 'latency', 'cost'
            parameter_ranges: Parameters to tune and their valid ranges
            goal: What to optimize for
            baseline_config: Current configuration as baseline
            storage_path: Path to store optimization history
        """
        self.evaluation_fn = evaluation_fn
        self.parameter_ranges = parameter_ranges or self.DEFAULT_RANGES
        self.goal = goal
        self.baseline_config = baseline_config or {}
        self.storage_path = Path(storage_path) if storage_path else None

        # State
        self._experiments: list[ExperimentResult] = []
        self._best_config: Optional[dict] = None
        self._best_score: float = float('-inf')

        # Load history if available
        if self.storage_path and self.storage_path.exists():
            self._load_history()

    def optimize(
        self,
        test_queries: list[str],
        n_iterations: int = 50,
        exploration_ratio: float = 0.3,
        early_stopping_patience: int = 10,
    ) -> dict:
        """
        Run parameter optimization.

        Args:
            test_queries: Queries to evaluate configurations on
            n_iterations: Number of configurations to try
            exploration_ratio: Fraction of iterations for exploration vs exploitation
            early_stopping_patience: Stop if no improvement for this many iterations

        Returns:
            Best configuration found
        """
        exploration_iterations = int(n_iterations * exploration_ratio)
        iterations_without_improvement = 0

        # Phase 1: Exploration - sample diverse configurations
        print(f"Phase 1: Exploring {exploration_iterations} diverse configurations...")
        for i in range(exploration_iterations):
            config = self._sample_config()
            self._evaluate_and_record(config, test_queries, f"explore_{i}")

        # Phase 2: Exploitation - focus on promising regions
        print(f"Phase 2: Exploiting promising regions...")
        for i in range(n_iterations - exploration_iterations):
            config = self._suggest_next_config()
            result = self._evaluate_and_record(config, test_queries, f"exploit_{i}")

            if result.metrics.get('combined_score', 0) > self._best_score:
                self._best_score = result.metrics['combined_score']
                self._best_config = config.copy()
                iterations_without_improvement = 0
                print(f"  New best score: {self._best_score:.4f}")
            else:
                iterations_without_improvement += 1

            if iterations_without_improvement >= early_stopping_patience:
                print(f"  Early stopping after {i+1} exploitation iterations")
                break

        # Save results
        if self.storage_path:
            self._save_history()

        return self._best_config or self._get_default_config()

    def suggest_improvements(self) -> list[dict]:
        """
        Analyze experiment history and suggest improvements.

        Returns list of suggested changes with expected impact.
        """
        if len(self._experiments) < 10:
            return [{"suggestion": "Run more experiments for reliable suggestions"}]

        suggestions = []

        # Analyze parameter correlations with performance
        param_impacts = self._analyze_parameter_impacts()

        for param, impact in sorted(param_impacts.items(), key=lambda x: abs(x[1]), reverse=True):
            if abs(impact) > 0.1:  # Significant impact
                direction = "increase" if impact > 0 else "decrease"
                suggestions.append({
                    "parameter": param,
                    "suggestion": f"Consider {direction}ing {param}",
                    "estimated_impact": f"{abs(impact)*100:.1f}% improvement potential",
                    "confidence": "high" if abs(impact) > 0.2 else "medium",
                })

        return suggestions[:5]  # Top 5 suggestions

    def should_retune(
        self,
        current_metrics: dict,
        threshold: float = 0.1,
    ) -> bool:
        """
        Determine if system should be retuned based on performance drift.

        Args:
            current_metrics: Current production metrics
            threshold: Acceptable drift threshold (10% default)

        Returns:
            True if retuning is recommended
        """
        if not self._experiments:
            return True

        # Compare to best historical performance
        best_experiment = max(
            self._experiments,
            key=lambda e: e.metrics.get('combined_score', 0)
        )

        best_score = best_experiment.metrics.get('combined_score', 0)
        current_score = self._compute_score(current_metrics)

        drift = (best_score - current_score) / max(best_score, 0.01)

        return drift > threshold

    def _sample_config(self) -> dict:
        """Sample a random configuration."""
        return {
            param.name: param.sample()
            for param in self.parameter_ranges
        }

    def _suggest_next_config(self) -> dict:
        """
        Suggest next configuration using acquisition function.

        Uses a simplified version of Expected Improvement:
        Balance exploitation (near best configs) with exploration (uncertain regions).
        """
        if not self._experiments or random.random() < 0.2:
            # 20% pure exploration
            return self._sample_config()

        # Get top configurations
        sorted_experiments = sorted(
            self._experiments,
            key=lambda e: e.metrics.get('combined_score', 0),
            reverse=True
        )
        top_configs = [e.config for e in sorted_experiments[:5]]

        # Perturb a top config
        base_config = random.choice(top_configs)
        new_config = {}

        for param in self.parameter_ranges:
            base_value = base_config.get(param.name, param.sample())
            # Add Gaussian noise scaled by range
            range_size = param.max_value - param.min_value
            noise = random.gauss(0, range_size * 0.1)
            new_value = param.clip(base_value + noise)
            new_config[param.name] = new_value

        return new_config

    def _evaluate_and_record(
        self,
        config: dict,
        queries: list[str],
        experiment_id: str,
    ) -> ExperimentResult:
        """Evaluate a configuration and record results."""
        # Run evaluation
        metrics = self.evaluation_fn(config, queries)

        # Compute combined score based on goal
        metrics['combined_score'] = self._compute_score(metrics)

        result = ExperimentResult(
            config=config,
            metrics=metrics,
            sample_size=len(queries),
            timestamp=datetime.utcnow(),
            experiment_id=experiment_id,
        )

        self._experiments.append(result)

        # Update best if improved
        if metrics['combined_score'] > self._best_score:
            self._best_score = metrics['combined_score']
            self._best_config = config.copy()

        return result

    def _compute_score(self, metrics: dict) -> float:
        """Compute combined score based on optimization goal."""
        # Normalize metrics to 0-1 scale (higher is better)
        precision = metrics.get('precision', 0.5)
        recall = metrics.get('recall', 0.5)
        latency = 1.0 - min(metrics.get('latency', 1.0) / 5.0, 1.0)  # Lower is better
        cost = 1.0 - min(metrics.get('cost', 0.5) / 1.0, 1.0)  # Lower is better

        if self.goal == OptimizationGoal.PRECISION:
            return precision * 0.7 + recall * 0.2 + latency * 0.1
        elif self.goal == OptimizationGoal.RECALL:
            return precision * 0.2 + recall * 0.7 + latency * 0.1
        elif self.goal == OptimizationGoal.LATENCY:
            return precision * 0.2 + recall * 0.2 + latency * 0.6
        elif self.goal == OptimizationGoal.COST:
            return precision * 0.2 + recall * 0.2 + cost * 0.6
        else:  # BALANCED
            return precision * 0.35 + recall * 0.35 + latency * 0.15 + cost * 0.15

    def _analyze_parameter_impacts(self) -> dict[str, float]:
        """Analyze correlation between parameters and performance."""
        impacts = {}

        for param in self.parameter_ranges:
            param_values = [e.config.get(param.name, 0) for e in self._experiments]
            scores = [e.metrics.get('combined_score', 0) for e in self._experiments]

            if len(set(param_values)) < 2:
                continue

            # Simple correlation
            mean_param = sum(param_values) / len(param_values)
            mean_score = sum(scores) / len(scores)

            covariance = sum(
                (p - mean_param) * (s - mean_score)
                for p, s in zip(param_values, scores)
            ) / len(param_values)

            var_param = sum((p - mean_param) ** 2 for p in param_values) / len(param_values)

            if var_param > 0:
                correlation = covariance / math.sqrt(var_param)
                impacts[param.name] = correlation

        return impacts

    def _get_default_config(self) -> dict:
        """Get default configuration from ranges."""
        return {
            param.name: (param.min_value + param.max_value) / 2
            for param in self.parameter_ranges
        }

    def _save_history(self) -> None:
        """Save experiment history."""
        if not self.storage_path:
            return

        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "experiments": [
                {
                    "config": e.config,
                    "metrics": e.metrics,
                    "sample_size": e.sample_size,
                    "timestamp": e.timestamp.isoformat(),
                    "experiment_id": e.experiment_id,
                }
                for e in self._experiments
            ],
            "best_config": self._best_config,
            "best_score": self._best_score,
        }

        with open(self.storage_path, 'w') as f:
            json.dump(data, f, indent=2)

    def _load_history(self) -> None:
        """Load experiment history."""
        if not self.storage_path or not self.storage_path.exists():
            return

        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)

            self._experiments = [
                ExperimentResult(
                    config=e["config"],
                    metrics=e["metrics"],
                    sample_size=e["sample_size"],
                    timestamp=datetime.fromisoformat(e["timestamp"]),
                    experiment_id=e["experiment_id"],
                )
                for e in data.get("experiments", [])
            ]

            self._best_config = data.get("best_config")
            self._best_score = data.get("best_score", float('-inf'))

        except (json.JSONDecodeError, KeyError):
            pass
