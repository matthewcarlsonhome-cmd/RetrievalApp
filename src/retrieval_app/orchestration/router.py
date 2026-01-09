"""
Query Router Module.

"Orchestration [means] routing queries, skipping retrieval when it's useless,
choosing fallback modes and deciding when a human or tool should take over."
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Callable
import re


class QueryIntent(str, Enum):
    """Classified query intents."""
    FACTUAL = "factual"
    PROCEDURAL = "procedural"
    COMPARATIVE = "comparative"
    CONVERSATIONAL = "conversational"
    CALCULATION = "calculation"
    CREATIVE = "creative"
    CLARIFICATION = "clarification"
    OUT_OF_SCOPE = "out_of_scope"


class RoutingDecision(str, Enum):
    """Routing decisions for queries."""
    USE_RAG = "use_rag"
    SKIP_RETRIEVAL = "skip_retrieval"
    USE_TOOL = "use_tool"
    ESCALATE_TO_HUMAN = "escalate_to_human"
    REQUEST_CLARIFICATION = "request_clarification"


@dataclass
class RouteResult:
    """Result of query routing."""
    decision: RoutingDecision
    intent: QueryIntent
    confidence: float
    reason: str
    suggested_tool: Optional[str] = None
    rewritten_query: Optional[str] = None


class QueryRouter:
    """
    Routes queries to appropriate handling strategies.

    Not every query needs RAG - some are better handled by:
    - Direct LLM response (simple questions)
    - Tools (calculations, lookups)
    - Human escalation (sensitive topics)
    - Clarification (ambiguous queries)
    """

    def __init__(
        self,
        retrieval_confidence_threshold: float = 0.3,
        tools: Optional[dict[str, Callable]] = None
    ):
        self.retrieval_threshold = retrieval_confidence_threshold
        self.tools = tools or {}

        self._simple_patterns = [
            r"^(hi|hello|hey|thanks|thank you|bye|goodbye)[\s!.?]*$",
            r"^what is (your name|the date|the time|today)",
            r"^who are you",
            r"^can you help",
        ]

        self._calculation_patterns = [
            r"(calculate|compute|what is) [\d+\-*/\s\(\)]+",
            r"(\d+)\s*[\+\-\*/]\s*(\d+)",
            r"(sum|average|mean|median|total) of",
        ]

        self._tool_keywords = {
            "calculator": ["calculate", "compute", "math", "equation"],
            "web_search": ["latest", "current", "today's", "recent news"],
            "code_executor": ["run", "execute", "compile"],
        }

    def route(
        self,
        query: str,
        retrieval_scores: Optional[list[float]] = None
    ) -> RouteResult:
        """
        Route a query to the appropriate handler.

        Args:
            query: The user's query
            retrieval_scores: Optional scores from a preliminary retrieval

        Returns:
            RouteResult with routing decision and metadata
        """
        query_lower = query.lower().strip()

        if self._is_simple_query(query_lower):
            return RouteResult(
                decision=RoutingDecision.SKIP_RETRIEVAL,
                intent=QueryIntent.CONVERSATIONAL,
                confidence=0.9,
                reason="Simple conversational query doesn't need retrieval"
            )

        if self._needs_clarification(query_lower):
            return RouteResult(
                decision=RoutingDecision.REQUEST_CLARIFICATION,
                intent=QueryIntent.CLARIFICATION,
                confidence=0.8,
                reason="Query is too vague or ambiguous"
            )

        tool = self._detect_tool_need(query_lower)
        if tool:
            return RouteResult(
                decision=RoutingDecision.USE_TOOL,
                intent=QueryIntent.CALCULATION if tool == "calculator" else QueryIntent.FACTUAL,
                confidence=0.85,
                reason=f"Query is better handled by {tool} tool",
                suggested_tool=tool
            )

        if self._should_escalate(query_lower):
            return RouteResult(
                decision=RoutingDecision.ESCALATE_TO_HUMAN,
                intent=QueryIntent.OUT_OF_SCOPE,
                confidence=0.9,
                reason="Query requires human intervention"
            )

        intent = self._classify_intent(query_lower)

        if retrieval_scores:
            avg_score = sum(retrieval_scores) / len(retrieval_scores)
            max_score = max(retrieval_scores)

            if max_score < self.retrieval_threshold:
                return RouteResult(
                    decision=RoutingDecision.SKIP_RETRIEVAL,
                    intent=intent,
                    confidence=0.7,
                    reason="Retrieved results have low relevance scores"
                )

        return RouteResult(
            decision=RoutingDecision.USE_RAG,
            intent=intent,
            confidence=0.8,
            reason="Query should be answered using retrieval"
        )

    def _is_simple_query(self, query: str) -> bool:
        """Check if query is simple enough to skip retrieval."""
        for pattern in self._simple_patterns:
            if re.match(pattern, query, re.IGNORECASE):
                return True
        return False

    def _needs_clarification(self, query: str) -> bool:
        """Check if query needs clarification."""
        if len(query.split()) < 2:
            return True

        vague_patterns = [
            r"^(it|this|that|these|those)[\s\?]*$",
            r"^(what|how|why)[\s\?]*$",
            r"^tell me more$",
            r"^explain$",
        ]
        for pattern in vague_patterns:
            if re.match(pattern, query, re.IGNORECASE):
                return True

        return False

    def _detect_tool_need(self, query: str) -> Optional[str]:
        """Detect if a tool should handle this query."""
        for pattern in self._calculation_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                if "calculator" in self.tools:
                    return "calculator"

        for tool, keywords in self._tool_keywords.items():
            if tool in self.tools:
                if any(kw in query for kw in keywords):
                    return tool

        return None

    def _should_escalate(self, query: str) -> bool:
        """Check if query should be escalated to human."""
        escalation_patterns = [
            r"speak to (a |an )?(human|person|agent|representative)",
            r"(legal|medical|financial) advice",
            r"(complaint|sue|lawsuit)",
            r"(emergency|urgent|critical)",
        ]
        for pattern in escalation_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return True
        return False

    def _classify_intent(self, query: str) -> QueryIntent:
        """Classify the intent of a query."""
        if any(q in query for q in ["how to", "how do", "steps to", "process for"]):
            return QueryIntent.PROCEDURAL

        if any(q in query for q in ["compare", "difference", "vs", "versus", "better"]):
            return QueryIntent.COMPARATIVE

        if any(q in query for q in ["write", "create", "generate", "compose"]):
            return QueryIntent.CREATIVE

        if query.startswith(("what", "who", "when", "where", "which")):
            return QueryIntent.FACTUAL

        return QueryIntent.FACTUAL

    def register_tool(self, name: str, handler: Callable) -> None:
        """Register a tool for query routing."""
        self.tools[name] = handler
