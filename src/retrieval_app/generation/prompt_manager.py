"""
Prompt Management Module.

"Generation isn't 'stuff all the context in the prompt' - it's about
token limits, prompt structure, evidence selection and avoiding
hallucination by not flooding the model."
"""

from dataclasses import dataclass
from typing import Optional
from string import Template

from retrieval_app.retrieval.vector_store import SearchResult


@dataclass
class PromptTemplate:
    """A prompt template with metadata."""
    name: str
    template: str
    description: str
    required_vars: list[str]
    optional_vars: list[str] = None

    def __post_init__(self):
        if self.optional_vars is None:
            self.optional_vars = []


class PromptManager:
    """
    Manages prompt templates and construction for RAG.

    Design principles:
    1. Clear instruction structure
    2. Explicit grounding in evidence
    3. Uncertainty acknowledgment
    4. Source attribution guidance
    """

    DEFAULT_RAG_TEMPLATE = """You are a helpful assistant that answers questions based on the provided context.

## Instructions
- Answer the question using ONLY the information in the provided context
- If the context doesn't contain enough information, say so clearly
- When you use information from the context, cite the source using [Source N] notation
- Be concise but complete
- If multiple sources provide conflicting information, acknowledge this

## Context
$context

## Question
$question

## Answer"""

    DEFAULT_NO_CONTEXT_TEMPLATE = """You are a helpful assistant.

## Instructions
- The retrieval system found no relevant documents for this question
- Either answer from your general knowledge OR explain that you cannot answer
- Be clear about the source of your information

## Question
$question

## Answer"""

    HALLUCINATION_CHECK_TEMPLATE = """Review the following answer and verify it against the provided sources.

## Sources
$context

## Answer to verify
$answer

## Verification task
1. For each claim in the answer, check if it's supported by the sources
2. List any claims that are NOT supported by the sources
3. Rate confidence: HIGH (all claims supported), MEDIUM (most supported), LOW (many unsupported)

## Verification result"""

    def __init__(self):
        self.templates: dict[str, PromptTemplate] = {}
        self._register_default_templates()

    def _register_default_templates(self) -> None:
        """Register default prompt templates."""
        self.register_template(PromptTemplate(
            name="rag_default",
            template=self.DEFAULT_RAG_TEMPLATE,
            description="Default RAG prompt with citation instructions",
            required_vars=["context", "question"]
        ))

        self.register_template(PromptTemplate(
            name="no_context",
            template=self.DEFAULT_NO_CONTEXT_TEMPLATE,
            description="Prompt for when no context is retrieved",
            required_vars=["question"]
        ))

        self.register_template(PromptTemplate(
            name="hallucination_check",
            template=self.HALLUCINATION_CHECK_TEMPLATE,
            description="Template for verifying answer against sources",
            required_vars=["context", "answer"]
        ))

    def register_template(self, template: PromptTemplate) -> None:
        """Register a custom prompt template."""
        self.templates[template.name] = template

    def get_template(self, name: str) -> PromptTemplate:
        """Get a template by name."""
        if name not in self.templates:
            raise ValueError(f"Template '{name}' not found")
        return self.templates[name]

    def build_prompt(
        self,
        template_name: str,
        **kwargs
    ) -> str:
        """Build a prompt from a template."""
        template = self.get_template(template_name)

        for var in template.required_vars:
            if var not in kwargs:
                raise ValueError(f"Missing required variable: {var}")

        prompt_template = Template(template.template)
        return prompt_template.safe_substitute(**kwargs)

    def build_rag_prompt(
        self,
        question: str,
        results: list[SearchResult],
        include_scores: bool = False,
        max_context_chars: Optional[int] = None
    ) -> str:
        """Build a RAG prompt with formatted context."""
        if not results:
            return self.build_prompt("no_context", question=question)

        context = self.format_context(
            results,
            include_scores=include_scores,
            max_chars=max_context_chars
        )

        return self.build_prompt(
            "rag_default",
            context=context,
            question=question
        )

    def format_context(
        self,
        results: list[SearchResult],
        include_scores: bool = False,
        max_chars: Optional[int] = None
    ) -> str:
        """Format search results into context string."""
        context_parts = []
        total_chars = 0

        for i, result in enumerate(results, 1):
            source_info = f"[Source {i}]"

            if result.chunk.metadata.get("source"):
                source_info += f" ({result.chunk.metadata['source']})"

            if include_scores:
                source_info += f" (relevance: {result.score:.2f})"

            chunk_text = f"{source_info}\n{result.chunk.content}"

            if max_chars and total_chars + len(chunk_text) > max_chars:
                remaining = max_chars - total_chars
                if remaining > 100:
                    chunk_text = chunk_text[:remaining] + "..."
                    context_parts.append(chunk_text)
                break

            context_parts.append(chunk_text)
            total_chars += len(chunk_text) + 2

        return "\n\n".join(context_parts)

    def build_hallucination_check_prompt(
        self,
        answer: str,
        results: list[SearchResult]
    ) -> str:
        """Build a prompt for hallucination checking."""
        context = self.format_context(results, include_scores=False)
        return self.build_prompt(
            "hallucination_check",
            context=context,
            answer=answer
        )
