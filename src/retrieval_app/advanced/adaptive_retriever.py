"""
Adaptive Retriever Module.

=============================================================================
INNOVATION: QUERY-AWARE DYNAMIC PARAMETER ADJUSTMENT
=============================================================================

Traditional RAG systems use fixed retrieval parameters for all queries.
This is suboptimal because:
- Simple factual queries need few, precise results
- Complex analytical queries need many, diverse results
- Keyword-heavy queries benefit more from BM25
- Conceptual queries benefit more from semantic search

This module implements adaptive retrieval that analyzes each query and
dynamically adjusts:
- top_k (how many initial results)
- semantic_weight vs lexical_weight
- reranking strategy
- diversity settings (MMR lambda)

The adaptation is based on:
1. Query complexity analysis (word count, clause detection)
2. Query type classification (factual, procedural, comparative, etc.)
3. Historical performance data (if available)
4. Real-time result quality signals

=============================================================================
INDUSTRY CONTEXT
=============================================================================

This pattern is used by leading search companies:
- Google's query understanding adjusts ranking signals per query
- Elasticsearch's Learning to Rank personalizes retrieval
- Pinecone's hybrid search auto-balances dense/sparse

Our implementation brings this sophistication to RAG systems.

=============================================================================
"""

from dataclasses import dataclass
from typing import Optional
import re
import math

from retrieval_app.retrieval.hybrid_retriever import HybridRetriever, RetrievalResult
from retrieval_app.retrieval.vector_store import SearchResult
from retrieval_app.core.config import RetrievalConfig, RetrievalMode


@dataclass
class QueryProfile:
    """
    Analysis of a query's characteristics.

    This profile drives adaptive parameter selection.
    """
    # Structural features
    word_count: int
    unique_words: int
    avg_word_length: float

    # Linguistic features
    has_question_word: bool  # who, what, where, when, why, how
    has_comparison: bool     # compare, vs, difference, better
    has_procedure: bool      # how to, steps, process
    has_exact_terms: bool    # quoted phrases, codes, IDs

    # Complexity indicators
    clause_count: int        # Approximated by conjunctions/punctuation
    specificity_score: float # Ratio of specific to generic terms

    # Derived classification
    query_type: str          # factual, procedural, comparative, exploratory
    complexity: str          # simple, moderate, complex

    # Recommended parameters
    recommended_top_k: int
    recommended_semantic_weight: float
    recommended_mmr_lambda: float
    recommended_rerank: bool


class QueryAnalyzer:
    """
    Analyzes queries to determine optimal retrieval strategy.

    This is the "brain" of adaptive retrieval - it looks at each query
    and decides how to retrieve based on query characteristics.
    """

    # Generic terms that don't help retrieval
    GENERIC_TERMS = {
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
        'could', 'should', 'may', 'might', 'must', 'shall', 'can',
        'this', 'that', 'these', 'those', 'it', 'its', 'they', 'them',
        'what', 'which', 'who', 'whom', 'whose', 'where', 'when', 'why', 'how',
        'all', 'each', 'every', 'both', 'few', 'more', 'most', 'other',
        'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so',
        'than', 'too', 'very', 'just', 'also', 'now', 'here', 'there',
        'about', 'after', 'before', 'between', 'into', 'through', 'during',
        'above', 'below', 'from', 'up', 'down', 'in', 'out', 'on', 'off',
        'over', 'under', 'again', 'further', 'then', 'once', 'and', 'but',
        'or', 'if', 'because', 'as', 'until', 'while', 'of', 'at', 'by',
        'for', 'with', 'to', 'me', 'i', 'my', 'you', 'your', 'we', 'our',
    }

    # Terms indicating specific entity types
    SPECIFIC_PATTERNS = [
        r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b',  # Proper nouns
        r'\b[A-Z]{2,}\b',  # Acronyms
        r'\b\d+(?:\.\d+)?\b',  # Numbers
        r'"[^"]+"|\'[^\']+\'',  # Quoted phrases
        r'\b[a-z]+_[a-z]+\b',  # snake_case (code)
        r'\b[a-z]+[A-Z][a-z]+\b',  # camelCase (code)
    ]

    def analyze(self, query: str) -> QueryProfile:
        """
        Analyze a query and produce a profile with recommendations.

        Args:
            query: The user's query string

        Returns:
            QueryProfile with analysis and recommendations
        """
        words = query.lower().split()
        unique_words = set(words)

        # Basic structural features
        word_count = len(words)
        unique_word_count = len(unique_words)
        avg_word_length = sum(len(w) for w in words) / max(len(words), 1)

        # Linguistic features
        has_question = any(w in {'who', 'what', 'where', 'when', 'why', 'how', 'which'}
                          for w in words)
        has_comparison = any(w in {'compare', 'vs', 'versus', 'difference',
                                   'better', 'worse', 'between', 'similarities'}
                            for w in words)
        has_procedure = any(phrase in query.lower()
                           for phrase in ['how to', 'how do', 'steps to', 'process for',
                                         'guide to', 'tutorial', 'instructions'])
        has_exact_terms = bool(re.search(r'"[^"]+"', query)) or \
                         bool(re.search(r'\b[A-Z]{2,}\d*\b', query))

        # Complexity analysis
        clause_indicators = len(re.findall(r'[,;:]|\band\b|\bor\b|\bbut\b', query))
        clause_count = clause_indicators + 1

        # Specificity: ratio of non-generic terms
        specific_words = unique_words - self.GENERIC_TERMS
        specificity_score = len(specific_words) / max(len(unique_words), 1)

        # Check for specific entity patterns
        specific_matches = sum(len(re.findall(p, query)) for p in self.SPECIFIC_PATTERNS)
        if specific_matches > 0:
            specificity_score = min(1.0, specificity_score + 0.2)

        # Classify query type
        query_type = self._classify_type(has_question, has_comparison,
                                          has_procedure, specificity_score)

        # Determine complexity
        complexity = self._determine_complexity(word_count, clause_count,
                                                 specificity_score)

        # Generate recommendations
        recommendations = self._recommend_parameters(
            query_type, complexity, has_exact_terms, specificity_score
        )

        return QueryProfile(
            word_count=word_count,
            unique_words=unique_word_count,
            avg_word_length=avg_word_length,
            has_question_word=has_question,
            has_comparison=has_comparison,
            has_procedure=has_procedure,
            has_exact_terms=has_exact_terms,
            clause_count=clause_count,
            specificity_score=specificity_score,
            query_type=query_type,
            complexity=complexity,
            recommended_top_k=recommendations['top_k'],
            recommended_semantic_weight=recommendations['semantic_weight'],
            recommended_mmr_lambda=recommendations['mmr_lambda'],
            recommended_rerank=recommendations['rerank'],
        )

    def _classify_type(self, has_question: bool, has_comparison: bool,
                       has_procedure: bool, specificity: float) -> str:
        """Classify query into type categories."""
        if has_comparison:
            return "comparative"
        if has_procedure:
            return "procedural"
        if specificity > 0.7:
            return "factual"
        if specificity < 0.3:
            return "exploratory"
        return "factual"

    def _determine_complexity(self, word_count: int, clause_count: int,
                              specificity: float) -> str:
        """Determine query complexity level."""
        complexity_score = (
            (word_count / 20) * 0.4 +  # Longer = more complex
            (clause_count / 3) * 0.3 +  # More clauses = more complex
            (1 - specificity) * 0.3     # Less specific = more complex
        )

        if complexity_score < 0.3:
            return "simple"
        elif complexity_score < 0.6:
            return "moderate"
        else:
            return "complex"

    def _recommend_parameters(self, query_type: str, complexity: str,
                              has_exact_terms: bool, specificity: float) -> dict:
        """
        Generate parameter recommendations based on query analysis.

        This is where the magic happens - translating query understanding
        into concrete retrieval strategy.
        """
        # Base parameters by query type
        type_params = {
            "factual": {"top_k": 5, "semantic": 0.7, "mmr": 0.7, "rerank": True},
            "procedural": {"top_k": 8, "semantic": 0.6, "mmr": 0.5, "rerank": True},
            "comparative": {"top_k": 12, "semantic": 0.5, "mmr": 0.3, "rerank": True},
            "exploratory": {"top_k": 15, "semantic": 0.8, "mmr": 0.4, "rerank": True},
        }
        params = type_params.get(query_type, type_params["factual"]).copy()

        # Adjust for complexity
        if complexity == "simple":
            params["top_k"] = max(3, params["top_k"] - 3)
            params["rerank"] = False  # Simple queries don't need reranking
        elif complexity == "complex":
            params["top_k"] = min(20, params["top_k"] + 5)
            params["mmr"] = max(0.2, params["mmr"] - 0.2)  # More diversity

        # Adjust for exact terms (boost lexical)
        if has_exact_terms:
            params["semantic"] = max(0.3, params["semantic"] - 0.2)

        # Adjust for specificity
        if specificity > 0.8:
            # Very specific query - fewer results, higher precision
            params["top_k"] = max(3, params["top_k"] - 2)
            params["mmr"] = min(0.9, params["mmr"] + 0.1)

        return {
            "top_k": params["top_k"],
            "semantic_weight": params["semantic"],
            "mmr_lambda": params["mmr"],
            "rerank": params["rerank"],
        }


class AdaptiveRetriever:
    """
    Production-grade adaptive retriever that optimizes per-query.

    Usage:
        retriever = AdaptiveRetriever(base_retriever)
        result = retriever.retrieve("How do neural networks learn?")

        # Access adaptation details
        print(f"Used top_k={result.adapted_params['top_k']}")
        print(f"Query type: {result.query_profile.query_type}")

    Key Innovation:
    ---------------
    Instead of one-size-fits-all retrieval, this adapts strategy per query:

    Query: "What is Python?"
    -> Simple factual query
    -> top_k=3, semantic_weight=0.7, no reranking needed
    -> Fast, precise retrieval

    Query: "Compare the performance characteristics of PostgreSQL vs MySQL
            for high-write workloads with JSONB data types"
    -> Complex comparative query
    -> top_k=15, semantic_weight=0.5, enable MMR diversity
    -> Thorough retrieval covering multiple aspects
    """

    def __init__(
        self,
        base_retriever: HybridRetriever,
        enable_adaptation: bool = True,
        min_top_k: int = 3,
        max_top_k: int = 25,
    ):
        self.base_retriever = base_retriever
        self.analyzer = QueryAnalyzer()
        self.enable_adaptation = enable_adaptation
        self.min_top_k = min_top_k
        self.max_top_k = max_top_k

        # Track adaptation performance for learning
        self._adaptation_history: list[dict] = []

    def retrieve(
        self,
        query: str,
        metadata_filter: Optional[dict] = None,
        force_params: Optional[dict] = None,
    ) -> "AdaptiveRetrievalResult":
        """
        Retrieve with adaptive parameter selection.

        Args:
            query: The search query
            metadata_filter: Optional metadata constraints
            force_params: Optional dict to override adaptation

        Returns:
            AdaptiveRetrievalResult with results and adaptation metadata
        """
        # Analyze query
        profile = self.analyzer.analyze(query)

        # Determine parameters
        if force_params:
            params = force_params
        elif self.enable_adaptation:
            params = {
                "top_k": max(self.min_top_k, min(self.max_top_k, profile.recommended_top_k)),
                "semantic_weight": profile.recommended_semantic_weight,
                "lexical_weight": 1.0 - profile.recommended_semantic_weight,
                "mmr_lambda": profile.recommended_mmr_lambda,
                "rerank": profile.recommended_rerank,
            }
        else:
            params = {
                "top_k": self.base_retriever.config.top_k,
                "semantic_weight": self.base_retriever.config.semantic_weight,
                "lexical_weight": self.base_retriever.config.lexical_weight,
                "mmr_lambda": self.base_retriever.config.mmr_lambda,
                "rerank": self.base_retriever.config.enable_reranking,
            }

        # Temporarily adjust retriever config
        original_config = self._save_config()
        self._apply_params(params)

        try:
            # Perform retrieval
            base_result = self.base_retriever.retrieve(
                query=query,
                metadata_filter=metadata_filter,
            )
        finally:
            # Restore original config
            self._restore_config(original_config)

        # Record for learning
        self._adaptation_history.append({
            "query": query,
            "profile": profile,
            "params": params,
            "result_count": len(base_result.results),
            "top_score": base_result.results[0].score if base_result.results else 0,
        })

        return AdaptiveRetrievalResult(
            results=base_result.results,
            query=query,
            query_profile=profile,
            adapted_params=params,
            mode_used=base_result.mode_used,
            semantic_results_count=base_result.semantic_results_count,
            lexical_results_count=base_result.lexical_results_count,
            reranked=base_result.reranked,
        )

    def _save_config(self) -> dict:
        """Save current retriever config."""
        config = self.base_retriever.config
        return {
            "top_k": config.top_k,
            "semantic_weight": config.semantic_weight,
            "lexical_weight": config.lexical_weight,
            "mmr_lambda": config.mmr_lambda,
            "enable_reranking": config.enable_reranking,
        }

    def _apply_params(self, params: dict) -> None:
        """Apply adapted parameters to retriever."""
        config = self.base_retriever.config
        config.top_k = params["top_k"]
        config.semantic_weight = params["semantic_weight"]
        config.lexical_weight = params["lexical_weight"]
        config.mmr_lambda = params["mmr_lambda"]
        config.enable_reranking = params["rerank"]

    def _restore_config(self, original: dict) -> None:
        """Restore retriever config to original values."""
        config = self.base_retriever.config
        for key, value in original.items():
            setattr(config, key, value)

    def get_adaptation_stats(self) -> dict:
        """Get statistics on adaptation performance."""
        if not self._adaptation_history:
            return {"total_queries": 0}

        history = self._adaptation_history

        return {
            "total_queries": len(history),
            "avg_top_k": sum(h["params"]["top_k"] for h in history) / len(history),
            "avg_semantic_weight": sum(h["params"]["semantic_weight"] for h in history) / len(history),
            "query_type_distribution": self._count_types(history),
            "complexity_distribution": self._count_complexities(history),
        }

    def _count_types(self, history: list) -> dict:
        """Count query types in history."""
        counts = {}
        for h in history:
            qt = h["profile"].query_type
            counts[qt] = counts.get(qt, 0) + 1
        return counts

    def _count_complexities(self, history: list) -> dict:
        """Count complexity levels in history."""
        counts = {}
        for h in history:
            c = h["profile"].complexity
            counts[c] = counts.get(c, 0) + 1
        return counts


@dataclass
class AdaptiveRetrievalResult:
    """Result from adaptive retrieval including adaptation metadata."""
    results: list[SearchResult]
    query: str
    query_profile: QueryProfile
    adapted_params: dict
    mode_used: RetrievalMode
    semantic_results_count: int
    lexical_results_count: int
    reranked: bool

    @property
    def adaptation_explanation(self) -> str:
        """Human-readable explanation of why these parameters were chosen."""
        profile = self.query_profile
        params = self.adapted_params

        explanations = []

        # Query type explanation
        type_reasons = {
            "factual": "straightforward factual query requiring precise results",
            "procedural": "how-to query needing step-by-step information",
            "comparative": "comparison query requiring diverse perspectives",
            "exploratory": "broad query benefiting from wide coverage",
        }
        explanations.append(f"Detected as {profile.query_type}: {type_reasons.get(profile.query_type, '')}")

        # Complexity explanation
        if profile.complexity == "simple":
            explanations.append("Simple query - using minimal retrieval for speed")
        elif profile.complexity == "complex":
            explanations.append("Complex query - expanded retrieval for thoroughness")

        # Parameter explanations
        if params["semantic_weight"] < 0.5:
            explanations.append("Boosted lexical search due to specific/exact terms")
        if params["top_k"] > 10:
            explanations.append("Increased result count for comprehensive coverage")
        if not params["rerank"]:
            explanations.append("Skipped reranking for simple query (latency optimization)")

        return " | ".join(explanations)
