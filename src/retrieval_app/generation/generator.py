"""
Response Generator Module.

Handles the actual LLM call with proper error handling,
retries, and hallucination prevention.
"""

import os
from dataclasses import dataclass
from typing import Optional
from abc import ABC, abstractmethod

from retrieval_app.core.config import GenerationConfig
from retrieval_app.retrieval.vector_store import SearchResult
from retrieval_app.generation.prompt_manager import PromptManager
from retrieval_app.generation.evidence_selector import EvidenceSelector, TokenBudget


@dataclass
class GenerationResult:
    """Result from response generation."""
    answer: str
    sources_used: list[str]
    confidence: float
    tokens_used: int
    hallucination_check_passed: Optional[bool] = None
    hallucination_details: Optional[str] = None


class LLMProvider(ABC):
    """Base class for LLM providers."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float
    ) -> tuple[str, int]:
        """Generate a response. Returns (response, tokens_used)."""
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI LLM provider."""

    def __init__(
        self,
        model: str = "gpt-4",
        api_key: Optional[str] = None
    ):
        self.model = model
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self._client = None

    @property
    def client(self):
        """Lazy load OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("openai is required. Install with: pip install openai")
        return self._client

    def generate(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float
    ) -> tuple[str, int]:
        """Generate response using OpenAI."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature
        )

        answer = response.choices[0].message.content or ""
        tokens = response.usage.total_tokens if response.usage else 0

        return answer, tokens


class MockLLMProvider(LLMProvider):
    """Mock LLM provider for testing."""

    def __init__(self, responses: Optional[dict[str, str]] = None):
        self.responses = responses or {}
        self.call_count = 0

    def generate(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float
    ) -> tuple[str, int]:
        """Return mock response."""
        self.call_count += 1

        for key, response in self.responses.items():
            if key.lower() in prompt.lower():
                return response, len(response) // 4

        return "This is a mock response based on the provided context.", 50


class ResponseGenerator:
    """
    Production-ready response generator with hallucination prevention.

    Key features:
    - Smart evidence selection within token budgets
    - Optional hallucination checking
    - Source attribution tracking
    - Confidence scoring
    """

    def __init__(
        self,
        config: GenerationConfig,
        llm_provider: Optional[LLMProvider] = None
    ):
        self.config = config
        self.llm = llm_provider or OpenAIProvider(model=config.model)
        self.prompt_manager = PromptManager()
        self.evidence_selector = EvidenceSelector(
            strategy=config.evidence_selection_strategy
        )

    def generate(
        self,
        question: str,
        retrieval_results: list[SearchResult]
    ) -> GenerationResult:
        """
        Generate a response to a question using retrieved evidence.

        Args:
            question: The user's question
            retrieval_results: Results from the retrieval system

        Returns:
            GenerationResult with answer and metadata
        """
        budget = TokenBudget.from_limits(
            max_context_tokens=self.config.max_context_tokens,
            max_output_tokens=self.config.max_output_tokens,
            question=question
        )

        selected_evidence = self.evidence_selector.select(
            results=retrieval_results,
            budget=budget,
            max_chunks=self.config.max_evidence_chunks
        )

        prompt = self.prompt_manager.build_rag_prompt(
            question=question,
            results=selected_evidence,
            include_scores=False
        )

        answer, tokens_used = self.llm.generate(
            prompt=prompt,
            max_tokens=self.config.max_output_tokens,
            temperature=self.config.temperature
        )

        sources = self._extract_sources(selected_evidence)
        confidence = self._calculate_confidence(selected_evidence, answer)

        result = GenerationResult(
            answer=answer,
            sources_used=sources,
            confidence=confidence,
            tokens_used=tokens_used
        )

        if self.config.hallucination_check and confidence < self.config.confidence_threshold:
            result = self._check_hallucination(result, selected_evidence)

        if self.config.include_source_citations:
            result.answer = self._add_source_references(
                result.answer,
                selected_evidence
            )

        return result

    def generate_without_context(self, question: str) -> GenerationResult:
        """Generate a response without retrieval context."""
        prompt = self.prompt_manager.build_prompt("no_context", question=question)

        answer, tokens_used = self.llm.generate(
            prompt=prompt,
            max_tokens=self.config.max_output_tokens,
            temperature=self.config.temperature
        )

        return GenerationResult(
            answer=answer,
            sources_used=[],
            confidence=0.5,
            tokens_used=tokens_used
        )

    def _extract_sources(self, evidence: list[SearchResult]) -> list[str]:
        """Extract source identifiers from evidence."""
        sources = []
        for result in evidence:
            source = result.chunk.metadata.get(
                "source",
                result.chunk.document_id
            )
            if source not in sources:
                sources.append(source)
        return sources

    def _calculate_confidence(
        self,
        evidence: list[SearchResult],
        answer: str
    ) -> float:
        """
        Calculate confidence score based on evidence quality.

        Factors:
        - Average relevance score of evidence
        - Number of evidence chunks
        - Answer length relative to evidence
        """
        if not evidence:
            return 0.3

        avg_score = sum(r.score for r in evidence) / len(evidence)

        evidence_factor = min(len(evidence) / 3, 1.0)

        total_evidence_chars = sum(len(r.chunk.content) for r in evidence)
        answer_ratio = len(answer) / max(total_evidence_chars, 1)
        grounding_factor = 1.0 - min(answer_ratio, 1.0) * 0.3

        confidence = (avg_score * 0.5 + evidence_factor * 0.3 + grounding_factor * 0.2)
        return min(max(confidence, 0.0), 1.0)

    def _check_hallucination(
        self,
        result: GenerationResult,
        evidence: list[SearchResult]
    ) -> GenerationResult:
        """Run hallucination check on the generated answer."""
        check_prompt = self.prompt_manager.build_hallucination_check_prompt(
            answer=result.answer,
            results=evidence
        )

        verification, _ = self.llm.generate(
            prompt=check_prompt,
            max_tokens=500,
            temperature=0.0
        )

        if "HIGH" in verification.upper():
            result.hallucination_check_passed = True
        elif "LOW" in verification.upper():
            result.hallucination_check_passed = False
            result.confidence *= 0.5
        else:
            result.hallucination_check_passed = None

        result.hallucination_details = verification
        return result

    def _add_source_references(
        self,
        answer: str,
        evidence: list[SearchResult]
    ) -> str:
        """Add source reference section to answer."""
        if not evidence:
            return answer

        sources_section = "\n\n---\n**Sources:**\n"
        for i, result in enumerate(evidence, 1):
            source = result.chunk.metadata.get("source", result.chunk.document_id)
            sources_section += f"[{i}] {source}\n"

        return answer + sources_section
