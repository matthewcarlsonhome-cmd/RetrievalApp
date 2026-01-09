"""
Orchestration Module.

Handles the decision-making layer:
- Query routing and classification
- Deciding when to skip retrieval
- Fallback strategies
- Query rewriting and decomposition
- Tool and human handoff
"""

from retrieval_app.orchestration.router import QueryRouter
from retrieval_app.orchestration.query_processor import QueryProcessor
from retrieval_app.orchestration.fallback_handler import FallbackHandler

__all__ = ["QueryRouter", "QueryProcessor", "FallbackHandler"]
