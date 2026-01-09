"""
Fallback Handler Module.

Manages fallback strategies when primary RAG path fails or is inappropriate.
"""

from dataclasses import dataclass
from typing import Optional, Callable
from enum import Enum

from retrieval_app.core.config import FallbackMode


class FallbackReason(str, Enum):
    """Reasons for triggering fallback."""
    NO_RESULTS = "no_results"
    LOW_CONFIDENCE = "low_confidence"
    RETRIEVAL_ERROR = "retrieval_error"
    GENERATION_ERROR = "generation_error"
    TIMEOUT = "timeout"
    OUT_OF_SCOPE = "out_of_scope"
    USER_REQUEST = "user_request"


@dataclass
class FallbackResult:
    """Result from fallback handling."""
    handled: bool
    response: Optional[str]
    fallback_mode: FallbackMode
    reason: FallbackReason
    next_action: Optional[str] = None
    metadata: Optional[dict] = None


class FallbackHandler:
    """
    Handles fallback scenarios gracefully.

    Production RAG needs fallbacks for:
    - No relevant documents found
    - Low confidence in generated answer
    - System errors (retrieval/generation)
    - Out-of-scope queries
    - Timeout situations
    """

    def __init__(
        self,
        default_mode: FallbackMode = FallbackMode.CLARIFICATION,
        direct_llm_handler: Optional[Callable] = None,
        tool_handlers: Optional[dict[str, Callable]] = None,
        human_escalation_handler: Optional[Callable] = None
    ):
        self.default_mode = default_mode
        self.direct_llm_handler = direct_llm_handler
        self.tool_handlers = tool_handlers or {}
        self.human_escalation_handler = human_escalation_handler

        self._clarification_templates = {
            FallbackReason.NO_RESULTS: (
                "I couldn't find relevant information in my knowledge base. "
                "Could you please:\n"
                "- Rephrase your question with different terms\n"
                "- Provide more context about what you're looking for\n"
                "- Specify which topic area this relates to"
            ),
            FallbackReason.LOW_CONFIDENCE: (
                "I found some information but I'm not confident it fully answers "
                "your question. Could you clarify:\n"
                "- What specific aspect are you most interested in?\n"
                "- Is there additional context that might help?"
            ),
            FallbackReason.OUT_OF_SCOPE: (
                "This question appears to be outside my knowledge domain. "
                "I can help with questions about {domain}. "
                "Would you like to rephrase your question or ask about something else?"
            ),
        }

    def handle(
        self,
        reason: FallbackReason,
        query: str,
        mode_override: Optional[FallbackMode] = None,
        context: Optional[dict] = None
    ) -> FallbackResult:
        """
        Handle a fallback scenario.

        Args:
            reason: Why fallback was triggered
            query: The original user query
            mode_override: Override the default fallback mode
            context: Additional context for handling

        Returns:
            FallbackResult with handling outcome
        """
        mode = mode_override or self.default_mode
        context = context or {}

        if mode == FallbackMode.DIRECT_LLM:
            return self._handle_direct_llm(reason, query, context)
        elif mode == FallbackMode.TOOL_HANDOFF:
            return self._handle_tool_handoff(reason, query, context)
        elif mode == FallbackMode.HUMAN_ESCALATION:
            return self._handle_human_escalation(reason, query, context)
        else:
            return self._handle_clarification(reason, query, context)

    def _handle_direct_llm(
        self,
        reason: FallbackReason,
        query: str,
        context: dict
    ) -> FallbackResult:
        """Fall back to direct LLM response without retrieval."""
        if self.direct_llm_handler:
            try:
                response = self.direct_llm_handler(query)
                return FallbackResult(
                    handled=True,
                    response=response,
                    fallback_mode=FallbackMode.DIRECT_LLM,
                    reason=reason,
                    metadata={"source": "direct_llm"}
                )
            except Exception as e:
                return FallbackResult(
                    handled=False,
                    response=f"Error in direct LLM fallback: {str(e)}",
                    fallback_mode=FallbackMode.DIRECT_LLM,
                    reason=reason,
                    next_action="retry_or_escalate"
                )

        return FallbackResult(
            handled=False,
            response="Direct LLM fallback not configured",
            fallback_mode=FallbackMode.DIRECT_LLM,
            reason=reason,
            next_action="configure_llm_handler"
        )

    def _handle_tool_handoff(
        self,
        reason: FallbackReason,
        query: str,
        context: dict
    ) -> FallbackResult:
        """Hand off to an appropriate tool."""
        suggested_tool = context.get("suggested_tool")

        if suggested_tool and suggested_tool in self.tool_handlers:
            try:
                handler = self.tool_handlers[suggested_tool]
                response = handler(query)
                return FallbackResult(
                    handled=True,
                    response=response,
                    fallback_mode=FallbackMode.TOOL_HANDOFF,
                    reason=reason,
                    metadata={"tool": suggested_tool}
                )
            except Exception as e:
                return FallbackResult(
                    handled=False,
                    response=f"Tool '{suggested_tool}' error: {str(e)}",
                    fallback_mode=FallbackMode.TOOL_HANDOFF,
                    reason=reason,
                    next_action="try_alternative_tool"
                )

        return FallbackResult(
            handled=False,
            response="No appropriate tool available for this query",
            fallback_mode=FallbackMode.TOOL_HANDOFF,
            reason=reason,
            next_action="use_clarification"
        )

    def _handle_human_escalation(
        self,
        reason: FallbackReason,
        query: str,
        context: dict
    ) -> FallbackResult:
        """Escalate to human support."""
        if self.human_escalation_handler:
            try:
                ticket_info = self.human_escalation_handler(query, context)
                return FallbackResult(
                    handled=True,
                    response=(
                        "I've escalated your question to our support team. "
                        f"Reference: {ticket_info.get('ticket_id', 'N/A')}"
                    ),
                    fallback_mode=FallbackMode.HUMAN_ESCALATION,
                    reason=reason,
                    metadata=ticket_info
                )
            except Exception as e:
                pass

        return FallbackResult(
            handled=True,
            response=(
                "This question requires human assistance. "
                "Please contact our support team directly or try rephrasing your question."
            ),
            fallback_mode=FallbackMode.HUMAN_ESCALATION,
            reason=reason,
            next_action="contact_support"
        )

    def _handle_clarification(
        self,
        reason: FallbackReason,
        query: str,
        context: dict
    ) -> FallbackResult:
        """Request clarification from user."""
        template = self._clarification_templates.get(
            reason,
            "I'm having trouble answering your question. "
            "Could you please provide more details or rephrase it?"
        )

        if "{domain}" in template:
            domain = context.get("domain", "the topics in my knowledge base")
            template = template.format(domain=domain)

        return FallbackResult(
            handled=True,
            response=template,
            fallback_mode=FallbackMode.CLARIFICATION,
            reason=reason,
            next_action="await_user_response"
        )

    def register_tool(self, name: str, handler: Callable) -> None:
        """Register a tool handler."""
        self.tool_handlers[name] = handler

    def set_clarification_template(
        self,
        reason: FallbackReason,
        template: str
    ) -> None:
        """Set a custom clarification template."""
        self._clarification_templates[reason] = template
