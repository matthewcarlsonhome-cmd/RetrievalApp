"""
Prompt templates for LLM generation.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from ..retrieval.search import SearchResult
from ..config import moderation_config


@dataclass
class PromptContext:
    """Context for building prompts."""
    query: str
    search_results: List[SearchResult]
    conversation_history: List[Dict[str, str]] = None
    company_name: str = "Matthew Carlson Consulting"


class PromptBuilder:
    """Build prompts for LLM generation."""

    def __init__(self, company_name: str = "Matthew Carlson Consulting"):
        self.company_name = company_name

    def build_system_prompt(self) -> str:
        """Build the system prompt with rules and guidelines."""
        rules = "\n".join(f"- {rule}" for rule in moderation_config.SYSTEM_RULES)

        return f"""You are a helpful AI assistant for {self.company_name}. Your role is to answer questions about the company's services, policies, and expertise based on the provided knowledge base.

## Core Responsibilities
- Answer questions accurately using ONLY information from the provided context
- Cite sources when providing information
- Maintain a professional, helpful tone
- Admit when you don't have enough information to answer

## Response Rules
{rules}

## Citation Format
When citing sources, use this format:
[Source: Document Title]

If information comes from direct Q&A, cite as:
[Source: FAQ]

## Handling Unknown Information
If the question cannot be answered from the provided context:
1. Acknowledge that you don't have that specific information
2. Suggest what related information you do have
3. Offer to help with related questions

## Tone Guidelines
- Professional but friendly
- Concise and clear
- Helpful and solution-oriented
- Never defensive or dismissive"""

    def build_context_block(self, search_results: List[SearchResult]) -> str:
        """Build the context block from search results."""
        if not search_results:
            return "No relevant context found in the knowledge base."

        context_parts = []
        for i, result in enumerate(search_results, 1):
            source_info = f"[{result.document_title}]"
            if result.section_title:
                source_info += f" - {result.section_title}"

            context_parts.append(f"""
---
Source {i}: {source_info}
{result.content}
---""")

        return "\n".join(context_parts)

    def build_user_message(
        self,
        query: str,
        search_results: List[SearchResult]
    ) -> str:
        """Build the user message with context."""
        context = self.build_context_block(search_results)

        return f"""## Available Context
{context}

## User Question
{query}

Please provide a helpful answer based on the context above. Remember to cite your sources."""

    def build_messages(
        self,
        context: PromptContext
    ) -> List[Dict[str, str]]:
        """
        Build the full message list for the LLM.

        Args:
            context: PromptContext with query and search results

        Returns:
            List of message dicts for the LLM
        """
        messages = []

        # Add conversation history if present
        if context.conversation_history:
            for msg in context.conversation_history[-6:]:  # Keep last 3 turns
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

        # Add current query with context
        user_message = self.build_user_message(
            context.query,
            context.search_results
        )
        messages.append({
            "role": "user",
            "content": user_message
        })

        return messages

    def build_qa_response_prompt(
        self,
        question: str,
        answer: str
    ) -> str:
        """Build prompt for reformatting a direct Q&A response."""
        return f"""The user asked: "{question}"

The direct answer from our FAQ is:
"{answer}"

Please provide this answer in a natural, conversational way while maintaining accuracy. You may add relevant context if appropriate, but do not add information not contained in the answer.

[Source: FAQ]"""


class FeedbackPromptBuilder:
    """Build prompts for feedback-based improvements."""

    def build_improvement_prompt(
        self,
        original_query: str,
        original_response: str,
        feedback: str,
        feedback_type: str
    ) -> str:
        """Build prompt for improving a response based on feedback."""
        return f"""A user provided feedback on a previous response.

Original Question: {original_query}

Original Response:
{original_response}

Feedback Type: {feedback_type}
User Feedback: {feedback}

Please analyze:
1. What was good about the original response?
2. What could be improved?
3. How should similar questions be answered in the future?

Provide specific recommendations."""


# Prompt templates for specific scenarios

CLARIFICATION_PROMPT = """The user's question is ambiguous. Please ask for clarification.

User Question: {query}

Possible interpretations:
{interpretations}

Ask the user to clarify which interpretation they meant, in a friendly way."""

OUT_OF_SCOPE_PROMPT = """The user asked a question outside our knowledge base scope.

User Question: {query}

Politely explain that this question is outside the scope of what we can answer, and suggest how they can get help:
- For general inquiries, they can contact us directly
- For specific topics we do cover, redirect them

Keep the response brief and helpful."""

ESCALATION_PROMPT = """The user's question may require human assistance.

User Question: {query}

Context: {context}

Reason for escalation: {reason}

Provide a helpful response that:
1. Acknowledges their question
2. Explains that a team member will follow up
3. Asks for any additional context that might be helpful"""
