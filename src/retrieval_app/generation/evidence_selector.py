"""
Evidence Selection Module.

Smart selection of which chunks to include in the prompt,
respecting token budgets while maximizing answer quality.
"""

from dataclasses import dataclass
from typing import Optional
import math

from retrieval_app.retrieval.vector_store import SearchResult


@dataclass
class TokenBudget:
    """Token budget allocation for prompt construction."""
    total_budget: int
    system_tokens: int
    question_tokens: int
    context_budget: int
    output_reserve: int

    @classmethod
    def from_limits(
        cls,
        max_context_tokens: int,
        max_output_tokens: int,
        question: str,
        system_overhead: int = 200
    ) -> "TokenBudget":
        """Calculate budget from token limits."""
        question_tokens = len(question) // 4
        total = max_context_tokens + max_output_tokens
        context_budget = max_context_tokens - system_overhead - question_tokens

        return cls(
            total_budget=total,
            system_tokens=system_overhead,
            question_tokens=question_tokens,
            context_budget=max(context_budget, 500),
            output_reserve=max_output_tokens
        )


class EvidenceSelector:
    """
    Selects the best evidence to include in prompts.

    Strategies:
    - Relevance-weighted: Prioritize highest scoring chunks
    - Coverage: Maximize topic coverage with diverse chunks
    - Recency: Prefer more recent information
    - Token-optimal: Maximize information per token
    """

    def __init__(
        self,
        strategy: str = "relevance_weighted",
        chars_per_token: float = 4.0
    ):
        self.strategy = strategy
        self.chars_per_token = chars_per_token

    def select(
        self,
        results: list[SearchResult],
        budget: TokenBudget,
        max_chunks: Optional[int] = None
    ) -> list[SearchResult]:
        """Select evidence within token budget."""
        if not results:
            return []

        if self.strategy == "relevance_weighted":
            return self._select_by_relevance(results, budget, max_chunks)
        elif self.strategy == "coverage":
            return self._select_for_coverage(results, budget, max_chunks)
        elif self.strategy == "token_optimal":
            return self._select_token_optimal(results, budget, max_chunks)
        else:
            return self._select_by_relevance(results, budget, max_chunks)

    def _select_by_relevance(
        self,
        results: list[SearchResult],
        budget: TokenBudget,
        max_chunks: Optional[int]
    ) -> list[SearchResult]:
        """Select chunks by relevance score until budget is exhausted."""
        sorted_results = sorted(results, key=lambda x: x.score, reverse=True)

        selected = []
        used_tokens = 0

        for result in sorted_results:
            if max_chunks and len(selected) >= max_chunks:
                break

            chunk_tokens = self._estimate_tokens(result.chunk.content)

            if used_tokens + chunk_tokens <= budget.context_budget:
                selected.append(result)
                used_tokens += chunk_tokens
            elif not selected:
                truncated_content = self._truncate_to_tokens(
                    result.chunk.content,
                    budget.context_budget
                )
                result.chunk.content = truncated_content
                selected.append(result)
                break

        return selected

    def _select_for_coverage(
        self,
        results: list[SearchResult],
        budget: TokenBudget,
        max_chunks: Optional[int]
    ) -> list[SearchResult]:
        """Select chunks to maximize topic coverage."""
        if not results:
            return []

        selected = [results[0]]
        used_tokens = self._estimate_tokens(results[0].chunk.content)
        selected_content = set(results[0].chunk.content.lower().split())

        for result in results[1:]:
            if max_chunks and len(selected) >= max_chunks:
                break

            chunk_tokens = self._estimate_tokens(result.chunk.content)
            if used_tokens + chunk_tokens > budget.context_budget:
                continue

            chunk_words = set(result.chunk.content.lower().split())
            new_words = chunk_words - selected_content
            novelty_ratio = len(new_words) / len(chunk_words) if chunk_words else 0

            if novelty_ratio > 0.3:
                selected.append(result)
                used_tokens += chunk_tokens
                selected_content.update(chunk_words)

        return selected

    def _select_token_optimal(
        self,
        results: list[SearchResult],
        budget: TokenBudget,
        max_chunks: Optional[int]
    ) -> list[SearchResult]:
        """Select chunks that maximize information per token."""
        scored_results = []
        for result in results:
            tokens = self._estimate_tokens(result.chunk.content)
            info_density = self._estimate_information_density(result.chunk.content)
            efficiency = (result.score * info_density) / math.log(tokens + 1)
            scored_results.append((result, efficiency, tokens))

        scored_results.sort(key=lambda x: x[1], reverse=True)

        selected = []
        used_tokens = 0

        for result, _, tokens in scored_results:
            if max_chunks and len(selected) >= max_chunks:
                break
            if used_tokens + tokens <= budget.context_budget:
                selected.append(result)
                used_tokens += tokens

        selected.sort(key=lambda x: x.score, reverse=True)
        return selected

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count from text."""
        return int(len(text) / self.chars_per_token)

    def _truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """Truncate text to fit within token limit."""
        max_chars = int(max_tokens * self.chars_per_token)
        if len(text) <= max_chars:
            return text

        truncated = text[:max_chars]
        last_sentence = max(
            truncated.rfind('. '),
            truncated.rfind('! '),
            truncated.rfind('? ')
        )
        if last_sentence > max_chars * 0.7:
            truncated = truncated[:last_sentence + 1]

        return truncated + "..."

    def _estimate_information_density(self, text: str) -> float:
        """
        Estimate information density of text.
        Higher density = more unique information per character.
        """
        words = text.lower().split()
        if not words:
            return 0.0

        unique_words = set(words)
        uniqueness = len(unique_words) / len(words)

        avg_word_length = sum(len(w) for w in words) / len(words)
        length_factor = min(avg_word_length / 6.0, 1.0)

        return (uniqueness + length_factor) / 2

    def get_budget_utilization(
        self,
        selected: list[SearchResult],
        budget: TokenBudget
    ) -> dict:
        """Get statistics on budget utilization."""
        total_tokens = sum(
            self._estimate_tokens(r.chunk.content)
            for r in selected
        )

        return {
            "selected_chunks": len(selected),
            "used_tokens": total_tokens,
            "budget_tokens": budget.context_budget,
            "utilization_pct": (total_tokens / budget.context_budget) * 100,
            "remaining_tokens": budget.context_budget - total_tokens
        }
