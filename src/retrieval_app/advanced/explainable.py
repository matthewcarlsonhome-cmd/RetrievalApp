"""
Explainable Retrieval Module.

=============================================================================
INNOVATION: TRANSPARENT RETRIEVAL DECISIONS
=============================================================================

Production RAG systems are often black boxes. When retrieval fails or returns
unexpected results, debugging is nearly impossible without understanding WHY
certain results were retrieved.

This module provides explainability at multiple levels:

1. QUERY UNDERSTANDING
   - What did the system understand from the query?
   - What search strategies were used and why?

2. RESULT EXPLANATIONS
   - Why was each result retrieved?
   - What terms/concepts matched?
   - How did different signals (semantic, lexical) contribute?

3. CONFIDENCE BREAKDOWN
   - Where does the confidence score come from?
   - What would improve confidence?

4. COUNTERFACTUAL ANALYSIS
   - What would have been retrieved with different parameters?
   - Why were certain documents NOT retrieved?

This is essential for:
- Debugging retrieval issues
- Building user trust (show your work)
- Continuous improvement (understand failures)

=============================================================================
"""

from dataclasses import dataclass, field
from typing import Optional
import re

from retrieval_app.retrieval.vector_store import SearchResult
from retrieval_app.retrieval.hybrid_retriever import HybridRetriever, RetrievalResult


@dataclass
class TermMatch:
    """A term match explanation."""
    term: str
    query_occurrence: int
    document_occurrence: int
    contribution_type: str  # "exact", "semantic", "stem"
    importance: float


@dataclass
class ResultExplanation:
    """Explanation for why a single result was retrieved."""
    chunk_id: str
    rank: int
    final_score: float

    # Score breakdown
    semantic_score: float
    lexical_score: float
    rerank_score: Optional[float]

    # Term matches
    term_matches: list[TermMatch]

    # Human-readable explanation
    explanation: str

    # Factors that boosted/penalized this result
    boost_factors: list[str]
    penalty_factors: list[str]


@dataclass
class RetrievalExplanation:
    """Complete explanation for a retrieval operation."""
    query: str

    # Query understanding
    detected_intent: str
    key_concepts: list[str]
    search_strategy: str

    # Parameters used
    parameters: dict

    # Result explanations
    result_explanations: list[ResultExplanation]

    # What wasn't retrieved and why
    near_misses: list[dict]

    # Confidence analysis
    confidence_factors: dict

    # Suggestions for improvement
    improvement_suggestions: list[str]

    def to_markdown(self) -> str:
        """Generate human-readable markdown explanation."""
        lines = [
            "# Retrieval Explanation",
            "",
            f"**Query**: {self.query}",
            "",
            "## Query Understanding",
            f"- **Detected Intent**: {self.detected_intent}",
            f"- **Key Concepts**: {', '.join(self.key_concepts)}",
            f"- **Search Strategy**: {self.search_strategy}",
            "",
            "## Parameters Used",
        ]

        for k, v in self.parameters.items():
            lines.append(f"- {k}: {v}")

        lines.extend(["", "## Results Explanation", ""])

        for exp in self.result_explanations[:5]:
            lines.extend([
                f"### Rank {exp.rank}: {exp.chunk_id}",
                f"**Score**: {exp.final_score:.3f}",
                f"- Semantic: {exp.semantic_score:.3f}",
                f"- Lexical: {exp.lexical_score:.3f}",
                "",
                f"**Why Retrieved**: {exp.explanation}",
                "",
                "**Key Matches**:",
            ])
            for match in exp.term_matches[:5]:
                lines.append(f"- \"{match.term}\" ({match.contribution_type})")
            lines.append("")

        if self.improvement_suggestions:
            lines.extend([
                "## Suggestions for Improvement",
                "",
            ])
            for suggestion in self.improvement_suggestions:
                lines.append(f"- {suggestion}")

        return "\n".join(lines)


class ExplainableRetrieval:
    """
    Wrapper that adds explainability to retrieval operations.

    Usage:
        explainable = ExplainableRetrieval(retriever)

        # Get results with explanation
        result, explanation = explainable.retrieve_with_explanation(query)

        # Print human-readable explanation
        print(explanation.to_markdown())

        # Or access specific explanations
        for exp in explanation.result_explanations:
            print(f"Result {exp.rank}: {exp.explanation}")
    """

    def __init__(
        self,
        retriever: HybridRetriever,
    ):
        self.retriever = retriever

    def retrieve_with_explanation(
        self,
        query: str,
        metadata_filter: Optional[dict] = None,
    ) -> tuple[RetrievalResult, RetrievalExplanation]:
        """
        Retrieve with full explainability.

        Returns:
            Tuple of (RetrievalResult, RetrievalExplanation)
        """
        # Analyze query
        intent = self._detect_intent(query)
        concepts = self._extract_concepts(query)

        # Perform retrieval
        result = self.retriever.retrieve(query, metadata_filter=metadata_filter)

        # Generate explanations for each result
        result_explanations = []
        for rank, search_result in enumerate(result.results, 1):
            exp = self._explain_result(query, search_result, rank, result)
            result_explanations.append(exp)

        # Analyze confidence
        confidence_factors = self._analyze_confidence(result)

        # Generate improvement suggestions
        suggestions = self._generate_suggestions(result, confidence_factors)

        # Describe search strategy
        strategy = self._describe_strategy(result)

        explanation = RetrievalExplanation(
            query=query,
            detected_intent=intent,
            key_concepts=concepts,
            search_strategy=strategy,
            parameters={
                "mode": result.mode_used.value,
                "semantic_results": result.semantic_results_count,
                "lexical_results": result.lexical_results_count,
                "reranked": result.reranked,
            },
            result_explanations=result_explanations,
            near_misses=[],  # Would require additional retrieval
            confidence_factors=confidence_factors,
            improvement_suggestions=suggestions,
        )

        return result, explanation

    def explain_why_not(
        self,
        query: str,
        expected_chunk_ids: list[str],
    ) -> dict:
        """
        Explain why certain expected documents weren't retrieved.

        Useful for debugging when you know what SHOULD have been retrieved.
        """
        result = self.retriever.retrieve(query, top_k=50)  # Wide net

        retrieved_ids = {r.chunk.id for r in result.results}
        missing = [cid for cid in expected_chunk_ids if cid not in retrieved_ids]

        explanations = {}
        for chunk_id in missing:
            # Find if it was retrieved at all
            all_retrieved = {r.chunk.id: r for r in result.results}

            if chunk_id in all_retrieved:
                search_result = all_retrieved[chunk_id]
                explanations[chunk_id] = {
                    "status": "retrieved_but_filtered",
                    "score": search_result.score,
                    "reason": f"Score {search_result.score:.3f} below threshold or ranked too low",
                }
            else:
                explanations[chunk_id] = {
                    "status": "not_retrieved",
                    "reason": "Document not in top 50 results",
                    "suggestions": [
                        "Check if document is indexed",
                        "Review chunking - relevant content may be in different chunk",
                        "Query may not match document vocabulary",
                    ],
                }

        return {
            "query": query,
            "expected": expected_chunk_ids,
            "retrieved": list(retrieved_ids)[:10],
            "missing_explanations": explanations,
        }

    def _detect_intent(self, query: str) -> str:
        """Detect query intent."""
        query_lower = query.lower()

        if any(w in query_lower for w in ["how to", "how do", "steps"]):
            return "procedural"
        elif any(w in query_lower for w in ["what is", "define", "meaning"]):
            return "definitional"
        elif any(w in query_lower for w in ["compare", "difference", "vs"]):
            return "comparative"
        elif any(w in query_lower for w in ["why", "reason", "cause"]):
            return "explanatory"
        elif any(w in query_lower for w in ["list", "examples", "types"]):
            return "enumerative"
        else:
            return "factual"

    def _extract_concepts(self, query: str) -> list[str]:
        """Extract key concepts from query."""
        # Remove stopwords and get significant terms
        stopwords = {
            'the', 'a', 'an', 'is', 'are', 'what', 'how', 'why', 'when',
            'where', 'which', 'who', 'do', 'does', 'did', 'can', 'could',
            'would', 'should', 'to', 'of', 'in', 'for', 'on', 'with', 'at',
            'by', 'from', 'and', 'or', 'but', 'this', 'that', 'these', 'those',
        }

        words = re.findall(r'\b\w+\b', query.lower())
        concepts = [w for w in words if w not in stopwords and len(w) > 2]

        return concepts[:5]  # Top 5

    def _explain_result(
        self,
        query: str,
        result: SearchResult,
        rank: int,
        retrieval_result: RetrievalResult,
    ) -> ResultExplanation:
        """Generate explanation for a single result."""
        # Find term matches
        query_terms = set(re.findall(r'\b\w+\b', query.lower()))
        doc_terms = set(re.findall(r'\b\w+\b', result.chunk.content.lower()))

        exact_matches = query_terms & doc_terms

        term_matches = [
            TermMatch(
                term=term,
                query_occurrence=1,
                document_occurrence=result.chunk.content.lower().count(term),
                contribution_type="exact",
                importance=0.8
            )
            for term in list(exact_matches)[:5]
        ]

        # Determine boost/penalty factors
        boost_factors = []
        penalty_factors = []

        if len(exact_matches) > 3:
            boost_factors.append(f"Strong term overlap ({len(exact_matches)} matching terms)")

        if result.score > 0.8:
            boost_factors.append("High semantic similarity")

        if result.search_type == "hybrid":
            boost_factors.append("Matched both semantic and lexical search")

        if len(result.chunk.content) < 100:
            penalty_factors.append("Short chunk may lack context")

        # Generate human-readable explanation
        explanation = self._generate_explanation(
            query, result, term_matches, boost_factors, penalty_factors
        )

        return ResultExplanation(
            chunk_id=result.chunk.id,
            rank=rank,
            final_score=result.score,
            semantic_score=result.score if result.search_type in ["semantic", "hybrid"] else 0,
            lexical_score=result.score if result.search_type in ["lexical", "hybrid"] else 0,
            rerank_score=result.score if retrieval_result.reranked else None,
            term_matches=term_matches,
            explanation=explanation,
            boost_factors=boost_factors,
            penalty_factors=penalty_factors,
        )

    def _generate_explanation(
        self,
        query: str,
        result: SearchResult,
        matches: list[TermMatch],
        boosts: list[str],
        penalties: list[str],
    ) -> str:
        """Generate human-readable explanation."""
        parts = []

        if matches:
            match_terms = [m.term for m in matches[:3]]
            parts.append(f"Contains key terms: {', '.join(match_terms)}")

        if result.search_type == "semantic":
            parts.append("semantically similar to query")
        elif result.search_type == "lexical":
            parts.append("strong keyword match")
        elif result.search_type == "hybrid":
            parts.append("matched both meaning and keywords")

        if boosts:
            parts.append(f"Boosted by: {boosts[0]}")

        return "; ".join(parts) if parts else "Retrieved based on combined relevance score"

    def _analyze_confidence(self, result: RetrievalResult) -> dict:
        """Analyze what contributes to confidence."""
        if not result.results:
            return {"score": 0, "factors": ["No results retrieved"]}

        top_score = result.results[0].score
        score_spread = top_score - result.results[-1].score if len(result.results) > 1 else 0

        factors = []

        if top_score > 0.8:
            factors.append(f"High top score ({top_score:.2f})")
        elif top_score < 0.5:
            factors.append(f"Low top score ({top_score:.2f}) - results may not be relevant")

        if score_spread > 0.3:
            factors.append("Good score separation - clear relevance hierarchy")
        elif score_spread < 0.1:
            factors.append("Similar scores - ambiguous relevance")

        if result.reranked:
            factors.append("Reranking applied for precision")

        return {
            "score": top_score,
            "factors": factors,
        }

    def _generate_suggestions(self, result: RetrievalResult, confidence: dict) -> list[str]:
        """Generate improvement suggestions based on results."""
        suggestions = []

        if confidence["score"] < 0.5:
            suggestions.append("Consider adding more relevant documents to knowledge base")
            suggestions.append("Try rephrasing the query with different terminology")

        if len(result.results) < 3:
            suggestions.append("Few results found - consider lowering relevance threshold")

        if not result.reranked:
            suggestions.append("Enable reranking for potentially better precision")

        return suggestions

    def _describe_strategy(self, result: RetrievalResult) -> str:
        """Describe the search strategy used."""
        parts = []

        if result.mode_used.value == "hybrid":
            parts.append("Hybrid search (semantic + lexical)")
        else:
            parts.append(f"{result.mode_used.value} search")

        parts.append(f"retrieved {result.semantic_results_count + result.lexical_results_count} candidates")

        if result.reranked:
            parts.append("then reranked for precision")

        return ", ".join(parts)
