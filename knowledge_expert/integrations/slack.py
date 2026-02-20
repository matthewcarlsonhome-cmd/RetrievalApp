"""
Slack Integration for Knowledge Expert.

Provides a Slack bot that can answer questions using the knowledge base.

Setup:
1. Create a Slack app at https://api.slack.com/apps
2. Enable Socket Mode or use Events API
3. Add bot scopes: app_mentions:read, chat:write, im:history, im:read, im:write
4. Set SLACK_BOT_TOKEN and SLACK_SIGNING_SECRET environment variables
5. Subscribe to events: app_mention, message.im

Usage:
The bot responds to:
- Direct messages
- @mentions in channels

Configuration environment variables:
- SLACK_BOT_TOKEN: Bot User OAuth Token (xoxb-...)
- SLACK_SIGNING_SECRET: Signing secret for verifying requests
- SLACK_APP_TOKEN: App-level token for Socket Mode (xapp-...) [optional]
"""

import hashlib
import hmac
import json
import logging
import os
import time
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class SlackBot:
    """
    Slack bot integration for Knowledge Expert.

    Handles incoming Slack events and responds with answers from the knowledge base.
    """

    def __init__(self, bot_token: str = None, signing_secret: str = None):
        self.bot_token = bot_token or os.environ.get('SLACK_BOT_TOKEN')
        self.signing_secret = signing_secret or os.environ.get('SLACK_SIGNING_SECRET')
        self._bot_user_id = None

    def is_configured(self) -> bool:
        """Check if Slack integration is properly configured."""
        return bool(self.bot_token and self.signing_secret)

    def verify_request(self, timestamp: str, signature: str, body: bytes) -> bool:
        """
        Verify that a request came from Slack.

        Args:
            timestamp: X-Slack-Request-Timestamp header
            signature: X-Slack-Signature header
            body: Raw request body

        Returns:
            True if signature is valid
        """
        if not self.signing_secret:
            return False

        # Check timestamp to prevent replay attacks
        try:
            request_timestamp = int(timestamp)
            if abs(time.time() - request_timestamp) > 300:  # 5 minutes
                return False
        except ValueError:
            return False

        # Compute signature
        sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
        computed_signature = 'v0=' + hmac.new(
            self.signing_secret.encode('utf-8'),
            sig_basestring.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(computed_signature, signature)

    def get_bot_user_id(self) -> Optional[str]:
        """Get the bot's user ID from Slack."""
        if self._bot_user_id:
            return self._bot_user_id

        try:
            import requests
            response = requests.post(
                'https://slack.com/api/auth.test',
                headers={'Authorization': f'Bearer {self.bot_token}'}
            )
            data = response.json()
            if data.get('ok'):
                self._bot_user_id = data.get('user_id')
                return self._bot_user_id
        except Exception as e:
            logger.error(f"Failed to get bot user ID: {e}")

        return None

    def send_message(self, channel: str, text: str, thread_ts: str = None) -> bool:
        """
        Send a message to a Slack channel.

        Args:
            channel: Channel ID or user ID
            text: Message text
            thread_ts: Thread timestamp to reply in thread

        Returns:
            True if message was sent successfully
        """
        try:
            import requests

            payload = {
                'channel': channel,
                'text': text,
                'mrkdwn': True
            }

            if thread_ts:
                payload['thread_ts'] = thread_ts

            response = requests.post(
                'https://slack.com/api/chat.postMessage',
                headers={
                    'Authorization': f'Bearer {self.bot_token}',
                    'Content-Type': 'application/json'
                },
                json=payload
            )

            data = response.json()
            if not data.get('ok'):
                logger.error(f"Slack API error: {data.get('error')}")
                return False

            return True

        except Exception as e:
            logger.error(f"Failed to send Slack message: {e}")
            return False

    def send_typing(self, channel: str):
        """Send typing indicator (not directly supported, but can be simulated)."""
        pass  # Slack doesn't have a direct typing indicator API for bots

    def extract_question(self, text: str) -> str:
        """
        Extract the question from a message, removing bot mentions.

        Args:
            text: Raw message text

        Returns:
            Cleaned question text
        """
        import re

        # Remove bot mentions
        cleaned = re.sub(r'<@[A-Z0-9]+>', '', text)

        # Remove extra whitespace
        cleaned = ' '.join(cleaned.split())

        return cleaned.strip()

    def format_response(self, response: str, citations: list = None) -> str:
        """
        Format a response for Slack with optional citations.

        Args:
            response: Response text
            citations: List of citation dicts

        Returns:
            Formatted Slack message
        """
        formatted = response

        # Add citations if available
        if citations:
            formatted += "\n\n_Sources:_"
            seen_sources = set()
            for i, citation in enumerate(citations[:3], 1):
                source = citation.get('document', 'Unknown')
                if source not in seen_sources:
                    seen_sources.add(source)
                    section = citation.get('section', '')
                    if section:
                        formatted += f"\n• {source} ({section})"
                    else:
                        formatted += f"\n• {source}"

        return formatted

    def handle_event(self, event: Dict[str, Any], query_function) -> Optional[str]:
        """
        Handle a Slack event.

        Args:
            event: Slack event payload
            query_function: Function to call for querying (takes query text, returns dict)

        Returns:
            Response text if should reply, None otherwise
        """
        event_type = event.get('type')

        # Handle message events
        if event_type == 'message':
            return self._handle_message(event, query_function)

        # Handle app_mention events
        if event_type == 'app_mention':
            return self._handle_mention(event, query_function)

        return None

    def _handle_message(self, event: Dict[str, Any], query_function) -> Optional[str]:
        """Handle a direct message."""
        # Ignore bot messages
        if event.get('bot_id') or event.get('subtype') == 'bot_message':
            return None

        # Only respond to DMs (channel starts with D)
        channel = event.get('channel', '')
        if not channel.startswith('D'):
            return None

        text = event.get('text', '')
        if not text:
            return None

        question = self.extract_question(text)
        if not question:
            return "I didn't catch that. Could you please rephrase your question?"

        # Query the knowledge base
        try:
            result = query_function(question)
            if result.get('error'):
                return f"Sorry, I encountered an error: {result['error']}"

            return self.format_response(
                result.get('response', "I couldn't find an answer to that."),
                result.get('citations', [])
            )
        except Exception as e:
            logger.error(f"Query error in Slack handler: {e}")
            return "Sorry, something went wrong. Please try again later."

    def _handle_mention(self, event: Dict[str, Any], query_function) -> Optional[str]:
        """Handle an @mention of the bot."""
        text = event.get('text', '')
        if not text:
            return None

        question = self.extract_question(text)
        if not question:
            return "Hi! Ask me a question and I'll try to help."

        # Query the knowledge base
        try:
            result = query_function(question)
            if result.get('error'):
                return f"Sorry, I encountered an error: {result['error']}"

            return self.format_response(
                result.get('response', "I couldn't find an answer to that."),
                result.get('citations', [])
            )
        except Exception as e:
            logger.error(f"Query error in Slack handler: {e}")
            return "Sorry, something went wrong. Please try again later."


# Global Slack bot instance
_slack_bot: Optional[SlackBot] = None


def get_slack_bot() -> SlackBot:
    """Get or create the global Slack bot instance."""
    global _slack_bot

    if _slack_bot is None:
        _slack_bot = SlackBot()

    return _slack_bot


def is_slack_configured() -> bool:
    """Check if Slack integration is configured."""
    return get_slack_bot().is_configured()
