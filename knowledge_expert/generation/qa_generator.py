"""
Automatic Q&A Generation from Documents.

Uses LLM to generate high-quality question-answer pairs from document content
that can be used to improve the knowledge base and provide instant responses.
"""

import json
import logging
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

from .llm import get_llm_client, LLMClient

logger = logging.getLogger(__name__)


@dataclass
class GeneratedQA:
    """A generated Q&A pair with metadata."""
    question: str
    answer: str
    source_document_id: str
    source_chunk_id: Optional[str] = None
    category: str = "Generated"
    confidence: float = 0.8
    tags: List[str] = field(default_factory=list)


class QAGenerator:
    """
    Generates Q&A pairs from document content using an LLM.

    Supports multiple generation strategies:
    - Factual Q&A: Direct questions about facts in the content
    - Conceptual Q&A: Questions about concepts and relationships
    - Procedural Q&A: How-to questions for instructional content
    """

    # Prompt templates for Q&A generation
    FACTUAL_PROMPT = """You are an expert at creating educational question-answer pairs from documents.

Given the following document content, generate {num_pairs} high-quality factual question-answer pairs.

Rules:
1. Questions should be clear and specific
2. Answers should be accurate and directly based on the content
3. Avoid yes/no questions - prefer open-ended questions
4. Questions should be useful for someone learning about this topic
5. Include a mix of simple and complex questions
6. Answers should be comprehensive but concise (2-4 sentences)

Document Title: {title}
Document Content:
{content}

Generate exactly {num_pairs} Q&A pairs in the following JSON format:
```json
[
  {{"question": "...", "answer": "...", "category": "factual", "tags": ["tag1", "tag2"]}},
  ...
]
```

Only output the JSON array, no other text."""

    CONCEPTUAL_PROMPT = """You are an expert at creating conceptual question-answer pairs that test understanding.

Given the following document content, generate {num_pairs} conceptual question-answer pairs that test deeper understanding.

Rules:
1. Ask about relationships, causes, effects, and implications
2. Ask "why" and "how" questions, not just "what"
3. Answers should explain concepts clearly
4. Questions should help someone truly understand the material
5. Avoid trivial questions that just repeat facts

Document Title: {title}
Document Content:
{content}

Generate exactly {num_pairs} Q&A pairs in the following JSON format:
```json
[
  {{"question": "...", "answer": "...", "category": "conceptual", "tags": ["tag1", "tag2"]}},
  ...
]
```

Only output the JSON array, no other text."""

    PROCEDURAL_PROMPT = """You are an expert at creating how-to question-answer pairs from instructional content.

Given the following document content, generate {num_pairs} procedural question-answer pairs about how to do things.

Rules:
1. Focus on "how to" questions
2. Answers should provide clear step-by-step guidance
3. Include any prerequisites or requirements
4. Note any warnings or common mistakes
5. Make questions practical and actionable

Document Title: {title}
Document Content:
{content}

Generate exactly {num_pairs} Q&A pairs in the following JSON format:
```json
[
  {{"question": "...", "answer": "...", "category": "procedural", "tags": ["tag1", "tag2"]}},
  ...
]
```

Only output the JSON array, no other text."""

    FAQ_PROMPT = """You are an expert at predicting what questions users will ask about a topic.

Given the following document content, generate {num_pairs} FAQ-style question-answer pairs that a user would likely ask.

Rules:
1. Think about what questions a new user would ask
2. Include common clarification questions
3. Include questions about edge cases and exceptions
4. Questions should sound natural (how a real person would ask)
5. Answers should be helpful and complete

Document Title: {title}
Document Content:
{content}

Generate exactly {num_pairs} Q&A pairs in the following JSON format:
```json
[
  {{"question": "...", "answer": "...", "category": "faq", "tags": ["tag1", "tag2"]}},
  ...
]
```

Only output the JSON array, no other text."""

    def __init__(self, llm_client: LLMClient = None):
        """Initialize the Q&A generator."""
        self.llm_client = llm_client or get_llm_client()

    def generate_from_content(
        self,
        content: str,
        title: str,
        document_id: str,
        num_pairs: int = 5,
        strategy: str = "mixed",
        chunk_id: str = None
    ) -> List[GeneratedQA]:
        """
        Generate Q&A pairs from content.

        Args:
            content: Document or chunk text content
            title: Document title
            document_id: ID of the source document
            num_pairs: Number of Q&A pairs to generate
            strategy: Generation strategy - "factual", "conceptual", "procedural", "faq", or "mixed"
            chunk_id: Optional chunk ID if generating from a specific chunk

        Returns:
            List of GeneratedQA objects
        """
        if not self.llm_client or not self.llm_client.is_available():
            logger.warning("LLM client not available for Q&A generation")
            return []

        if not content or len(content.strip()) < 100:
            logger.warning("Content too short for Q&A generation")
            return []

        # Truncate content if too long (keep ~4000 tokens worth)
        max_content_length = 12000  # ~3000 tokens
        if len(content) > max_content_length:
            content = content[:max_content_length] + "..."

        # Select prompt based on strategy
        if strategy == "mixed":
            # Generate a mix of all types
            return self._generate_mixed(content, title, document_id, num_pairs, chunk_id)
        else:
            return self._generate_single_strategy(
                content, title, document_id, num_pairs, strategy, chunk_id
            )

    def _generate_mixed(
        self,
        content: str,
        title: str,
        document_id: str,
        num_pairs: int,
        chunk_id: str = None
    ) -> List[GeneratedQA]:
        """Generate a mix of different Q&A types."""
        results = []

        # Distribute pairs across strategies
        pairs_per_strategy = max(1, num_pairs // 3)
        remainder = num_pairs % 3

        strategies = [
            ("faq", pairs_per_strategy + (1 if remainder > 0 else 0)),
            ("factual", pairs_per_strategy + (1 if remainder > 1 else 0)),
            ("conceptual", pairs_per_strategy)
        ]

        for strategy, count in strategies:
            if count > 0:
                qa_pairs = self._generate_single_strategy(
                    content, title, document_id, count, strategy, chunk_id
                )
                results.extend(qa_pairs)

        return results

    def _generate_single_strategy(
        self,
        content: str,
        title: str,
        document_id: str,
        num_pairs: int,
        strategy: str,
        chunk_id: str = None
    ) -> List[GeneratedQA]:
        """Generate Q&A pairs using a single strategy."""
        prompts = {
            "factual": self.FACTUAL_PROMPT,
            "conceptual": self.CONCEPTUAL_PROMPT,
            "procedural": self.PROCEDURAL_PROMPT,
            "faq": self.FAQ_PROMPT
        }

        prompt_template = prompts.get(strategy, self.FACTUAL_PROMPT)
        prompt = prompt_template.format(
            title=title,
            content=content,
            num_pairs=num_pairs
        )

        try:
            response = self.llm_client.generate(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0.7
            )

            # Parse the JSON response
            qa_pairs = self._parse_qa_response(response.content)

            # Convert to GeneratedQA objects
            results = []
            for qa in qa_pairs:
                generated = GeneratedQA(
                    question=qa.get("question", ""),
                    answer=qa.get("answer", ""),
                    source_document_id=document_id,
                    source_chunk_id=chunk_id,
                    category=qa.get("category", strategy.title()),
                    confidence=0.8,
                    tags=qa.get("tags", [])
                )
                if generated.question and generated.answer:
                    results.append(generated)

            return results

        except Exception as e:
            logger.error(f"Q&A generation failed: {e}")
            return []

    def _parse_qa_response(self, response_text: str) -> List[Dict]:
        """Parse the LLM's JSON response."""
        try:
            # Try to extract JSON from the response
            # First, try direct JSON parse
            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                pass

            # Try to find JSON array in the response
            json_match = re.search(r'\[[\s\S]*\]', response_text)
            if json_match:
                return json.loads(json_match.group())

            # Try to find code block with JSON
            code_match = re.search(r'```(?:json)?\s*(\[[\s\S]*?\])\s*```', response_text)
            if code_match:
                return json.loads(code_match.group(1))

            logger.warning("Could not parse Q&A response as JSON")
            return []

        except Exception as e:
            logger.error(f"Error parsing Q&A response: {e}")
            return []

    def generate_from_document(
        self,
        document_id: str,
        db,
        num_pairs: int = 10,
        strategy: str = "mixed",
        use_chunks: bool = True
    ) -> List[GeneratedQA]:
        """
        Generate Q&A pairs from a document in the database.

        Args:
            document_id: ID of the document
            db: Database instance
            num_pairs: Total number of Q&A pairs to generate
            strategy: Generation strategy
            use_chunks: If True, generate from individual chunks

        Returns:
            List of GeneratedQA objects
        """
        # Get the document
        document = db.get_knowledge_item(document_id)
        if not document:
            logger.error(f"Document not found: {document_id}")
            return []

        results = []

        if use_chunks and document.chunk_count > 0:
            # Get chunks and generate from each
            chunks = db.get_chunks_by_item(document_id)

            # Calculate pairs per chunk
            pairs_per_chunk = max(1, num_pairs // len(chunks))
            remaining = num_pairs

            for chunk in chunks:
                if remaining <= 0:
                    break

                chunk_pairs = min(pairs_per_chunk, remaining)

                # Generate from this chunk
                qa_pairs = self.generate_from_content(
                    content=chunk.content,
                    title=f"{document.title} - {chunk.section_title or f'Section {chunk.chunk_index + 1}'}",
                    document_id=document_id,
                    num_pairs=chunk_pairs,
                    strategy=strategy,
                    chunk_id=chunk.id
                )

                results.extend(qa_pairs)
                remaining -= len(qa_pairs)
        else:
            # Generate from full document content
            results = self.generate_from_content(
                content=document.content,
                title=document.title,
                document_id=document_id,
                num_pairs=num_pairs,
                strategy=strategy
            )

        return results

    def save_generated_qa(
        self,
        qa_pairs: List[GeneratedQA],
        db,
        organization_id: str,
        created_by: str = None,
        auto_approve: bool = False
    ) -> List[str]:
        """
        Save generated Q&A pairs to the database.

        Args:
            qa_pairs: List of GeneratedQA objects
            db: Database instance
            organization_id: Organization ID for tenant isolation
            created_by: User ID who initiated generation
            auto_approve: If True, save directly. If False, save as pending review.

        Returns:
            List of created Q&A IDs
        """
        from ..models import DirectQA

        saved_ids = []

        for qa in qa_pairs:
            # Create DirectQA entry
            direct_qa = DirectQA(
                question=qa.question,
                answer=qa.answer,
                organization_id=organization_id,
                category=f"Generated - {qa.category}",
                tags=qa.tags + [f"source:{qa.source_document_id}"],
                created_by=created_by
            )

            try:
                qa_id = db.add_direct_qa(direct_qa)
                saved_ids.append(qa_id)
            except Exception as e:
                logger.error(f"Failed to save generated Q&A: {e}")

        return saved_ids


# Module-level generator instance
_qa_generator = None


def get_qa_generator() -> QAGenerator:
    """Get or create the global Q&A generator."""
    global _qa_generator

    if _qa_generator is None:
        _qa_generator = QAGenerator()

    return _qa_generator
