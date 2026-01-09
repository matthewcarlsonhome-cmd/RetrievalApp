"""
Generation Module.

Handles response generation with:
- Token management and context budgeting
- Evidence selection strategies
- Prompt engineering for RAG
- Hallucination prevention
- Source attribution
"""

from retrieval_app.generation.generator import ResponseGenerator
from retrieval_app.generation.prompt_manager import PromptManager
from retrieval_app.generation.evidence_selector import EvidenceSelector

__all__ = ["ResponseGenerator", "PromptManager", "EvidenceSelector"]
