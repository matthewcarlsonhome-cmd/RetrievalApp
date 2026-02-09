"""
Content moderation for input and output filtering.
"""

import re
import logging
from typing import List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

from ..config import moderation_config

logger = logging.getLogger(__name__)


class ModerationAction(Enum):
    """Actions to take based on moderation result."""
    ALLOW = "allow"
    BLOCK = "block"
    FILTER = "filter"
    WARN = "warn"


@dataclass
class ModerationResult:
    """Result of content moderation."""
    action: ModerationAction
    reason: str = None
    filtered_content: str = None
    violations: List[str] = None

    @property
    def is_allowed(self) -> bool:
        return self.action in (ModerationAction.ALLOW, ModerationAction.FILTER)

    @property
    def is_blocked(self) -> bool:
        return self.action == ModerationAction.BLOCK


class ContentModerator:
    """
    Content moderation for queries and responses.

    Checks for:
    - Blocked words (profanity, explicit content)
    - Blocked topics (politics, religion, etc.)
    - Competitor mentions
    - Prompt injection attempts
    """

    def __init__(self):
        self.blocked_words = set(w.lower() for w in moderation_config.BLOCKED_WORDS)
        self.blocked_topics = set(t.lower() for t in moderation_config.BLOCKED_TOPICS)
        self.competitor_names = set(c.lower() for c in moderation_config.COMPETITOR_NAMES)

    def moderate_query(self, query: str) -> ModerationResult:
        """
        Moderate an incoming user query.

        Args:
            query: The user's question

        Returns:
            ModerationResult with action and details
        """
        violations = []

        # Check for blocked words
        blocked = self._check_blocked_words(query)
        if blocked:
            violations.extend(blocked)

        # Check for blocked topics
        topics = self._check_blocked_topics(query)
        if topics:
            violations.extend(topics)

        # Check for prompt injection attempts
        injection = self._check_prompt_injection(query)
        if injection:
            violations.append(injection)

        if violations:
            return ModerationResult(
                action=ModerationAction.BLOCK,
                reason="Query contains inappropriate content",
                violations=violations
            )

        return ModerationResult(action=ModerationAction.ALLOW)

    def moderate_response(self, response: str) -> ModerationResult:
        """
        Moderate an LLM-generated response.

        Args:
            response: The generated response text

        Returns:
            ModerationResult with optional filtered content
        """
        violations = []
        filtered = response

        # Check for blocked words and filter them
        blocked = self._check_blocked_words(response)
        if blocked:
            violations.extend(blocked)
            filtered = self._filter_blocked_words(filtered)

        # Check for competitor mentions
        competitors = self._check_competitors(response)
        if competitors:
            violations.extend(competitors)
            filtered = self._filter_competitors(filtered)

        # Check for off-topic content
        off_topic = self._check_off_topic_response(response)
        if off_topic:
            violations.append(off_topic)

        if violations:
            if filtered != response:
                return ModerationResult(
                    action=ModerationAction.FILTER,
                    reason="Response contained filtered content",
                    filtered_content=filtered,
                    violations=violations
                )
            else:
                return ModerationResult(
                    action=ModerationAction.WARN,
                    reason="Response may contain inappropriate content",
                    violations=violations
                )

        return ModerationResult(action=ModerationAction.ALLOW)

    def _check_blocked_words(self, text: str) -> List[str]:
        """Check for blocked words in text."""
        text_lower = text.lower()
        found = []

        for word in self.blocked_words:
            # Use word boundary matching
            pattern = r'\b' + re.escape(word) + r'\b'
            if re.search(pattern, text_lower):
                found.append(f"blocked_word:{word}")

        return found

    def _check_blocked_topics(self, text: str) -> List[str]:
        """Check for blocked topics in text."""
        text_lower = text.lower()
        found = []

        for topic in self.blocked_topics:
            if topic in text_lower:
                found.append(f"blocked_topic:{topic}")

        return found

    def _check_competitors(self, text: str) -> List[str]:
        """Check for competitor mentions."""
        text_lower = text.lower()
        found = []

        for competitor in self.competitor_names:
            pattern = r'\b' + re.escape(competitor) + r'\b'
            if re.search(pattern, text_lower):
                found.append(f"competitor:{competitor}")

        return found

    def _check_prompt_injection(self, text: str) -> Optional[str]:
        """
        Check for prompt injection attempts.

        Looks for patterns that try to override system instructions.
        """
        injection_patterns = [
            r"ignore\s+(previous|above|all)\s+instructions",
            r"disregard\s+(previous|above|all)\s+instructions",
            r"forget\s+(previous|above|all)\s+instructions",
            r"new\s+instructions?:",
            r"system\s*:\s*you\s+are",
            r"pretend\s+you\s+are",
            r"act\s+as\s+if",
            r"override\s+your\s+rules",
            r"jailbreak",
            r"dan\s+mode",
            r"\[system\]",
            r"<\|im_start\|>",
        ]

        text_lower = text.lower()

        for pattern in injection_patterns:
            if re.search(pattern, text_lower):
                return "prompt_injection_attempt"

        return None

    def _check_off_topic_response(self, text: str) -> Optional[str]:
        """Check if response goes off-topic."""
        # Check for topics we shouldn't discuss
        off_topic_indicators = [
            "i cannot provide medical advice",
            "i cannot provide legal advice",
            "i cannot provide financial advice",
            "as an ai language model",
            "i don't have personal opinions",
            "i cannot make political statements",
        ]

        text_lower = text.lower()

        for indicator in off_topic_indicators:
            if indicator in text_lower:
                return "potentially_off_topic"

        return None

    def _filter_blocked_words(self, text: str) -> str:
        """Replace blocked words with asterisks."""
        result = text

        for word in self.blocked_words:
            pattern = r'\b' + re.escape(word) + r'\b'
            replacement = '*' * len(word)
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

        return result

    def _filter_competitors(self, text: str) -> str:
        """Remove or replace competitor mentions."""
        result = text

        for competitor in self.competitor_names:
            pattern = r'\b' + re.escape(competitor) + r'\b'
            result = re.sub(pattern, "[competitor]", result, flags=re.IGNORECASE)

        return result


class InputValidator:
    """Validate and sanitize user inputs."""

    MAX_QUERY_LENGTH = 2000
    MAX_FEEDBACK_LENGTH = 500

    def validate_query(self, query: str) -> Tuple[bool, str]:
        """
        Validate a user query.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not query or not query.strip():
            return False, "Query cannot be empty"

        if len(query) > self.MAX_QUERY_LENGTH:
            return False, f"Query too long (max {self.MAX_QUERY_LENGTH} characters)"

        # Check for minimum meaningful content
        words = query.split()
        if len(words) < 2:
            return False, "Please provide more detail in your question"

        return True, ""

    def validate_feedback(self, feedback: str) -> Tuple[bool, str]:
        """Validate user feedback text."""
        if not feedback:
            return True, ""  # Feedback text is optional

        if len(feedback) > self.MAX_FEEDBACK_LENGTH:
            return False, f"Feedback too long (max {self.MAX_FEEDBACK_LENGTH} characters)"

        return True, ""

    def sanitize_input(self, text: str) -> str:
        """Sanitize user input for storage."""
        if not text:
            return ""

        # Remove null bytes
        text = text.replace('\x00', '')

        # Normalize whitespace
        text = ' '.join(text.split())

        # Remove control characters except newlines
        text = ''.join(c for c in text if c == '\n' or c >= ' ')

        return text.strip()


# Global instances
moderator = ContentModerator()
validator = InputValidator()


def moderate_query(query: str) -> ModerationResult:
    """Convenience function to moderate a query."""
    return moderator.moderate_query(query)


def moderate_response(response: str) -> ModerationResult:
    """Convenience function to moderate a response."""
    return moderator.moderate_response(response)
