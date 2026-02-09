"""
LLM client for Claude and OpenAI APIs.
"""

import logging
import os
from typing import List, Dict, Any, Optional, Generator
from dataclasses import dataclass

from ..config import config

logger = logging.getLogger(__name__)

# Global LLM client (lazy loaded)
_llm_client = None


def get_llm_client() -> "LLMClient":
    """Get or create the global LLM client."""
    global _llm_client

    if _llm_client is None:
        _llm_client = LLMClient()

    return _llm_client


@dataclass
class LLMResponse:
    """Response from LLM."""
    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: str


class LLMClient:
    """
    Unified LLM client supporting Claude and OpenAI.

    Automatically selects based on available API keys.
    """

    def __init__(self):
        self.anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        self.openai_key = os.environ.get("OPENAI_API_KEY")
        self.provider = self._detect_provider()
        self._client = None

        logger.info(f"LLM Client initialized with provider: {self.provider}")

    def _detect_provider(self) -> str:
        """Detect which LLM provider to use."""
        if self.anthropic_key:
            return "anthropic"
        elif self.openai_key:
            return "openai"
        else:
            logger.warning("No LLM API key found. Set ANTHROPIC_API_KEY or OPENAI_API_KEY")
            return "none"

    @property
    def client(self):
        """Lazy load the appropriate client."""
        if self._client is None:
            if self.provider == "anthropic":
                try:
                    import anthropic
                    self._client = anthropic.Anthropic(api_key=self.anthropic_key)
                except ImportError:
                    raise ImportError("anthropic package required. Run: pip install anthropic")

            elif self.provider == "openai":
                try:
                    from openai import OpenAI
                    self._client = OpenAI(api_key=self.openai_key)
                except ImportError:
                    raise ImportError("openai package required. Run: pip install openai")

        return self._client

    def generate(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = None,
        max_tokens: int = None,
        temperature: float = None,
        stream: bool = False
    ) -> LLMResponse:
        """
        Generate a response from the LLM.

        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: Optional system prompt
            max_tokens: Max tokens to generate
            temperature: Sampling temperature
            stream: Whether to stream the response

        Returns:
            LLMResponse object
        """
        max_tokens = max_tokens or config.MAX_TOKENS
        temperature = temperature or config.TEMPERATURE

        if self.provider == "anthropic":
            return self._generate_anthropic(
                messages, system_prompt, max_tokens, temperature, stream
            )
        elif self.provider == "openai":
            return self._generate_openai(
                messages, system_prompt, max_tokens, temperature, stream
            )
        else:
            raise RuntimeError("No LLM provider configured")

    def _generate_anthropic(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        max_tokens: int,
        temperature: float,
        stream: bool
    ) -> LLMResponse:
        """Generate using Claude API."""
        kwargs = {
            "model": config.LLM_MODEL,
            "max_tokens": max_tokens,
            "messages": messages
        }

        if system_prompt:
            kwargs["system"] = system_prompt

        if temperature is not None:
            kwargs["temperature"] = temperature

        if stream:
            return self._stream_anthropic(**kwargs)

        response = self.client.messages.create(**kwargs)

        return LLMResponse(
            content=response.content[0].text,
            model=response.model,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens
            },
            finish_reason=response.stop_reason
        )

    def _stream_anthropic(self, **kwargs) -> Generator[str, None, None]:
        """Stream response from Claude."""
        with self.client.messages.stream(**kwargs) as stream:
            for text in stream.text_stream:
                yield text

    def _generate_openai(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        max_tokens: int,
        temperature: float,
        stream: bool
    ) -> LLMResponse:
        """Generate using OpenAI API."""
        # Convert to OpenAI format
        openai_messages = []

        if system_prompt:
            openai_messages.append({
                "role": "system",
                "content": system_prompt
            })

        openai_messages.extend(messages)

        kwargs = {
            "model": config.LLM_MODEL if "gpt" in config.LLM_MODEL else "gpt-4",
            "messages": openai_messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }

        if stream:
            return self._stream_openai(**kwargs)

        response = self.client.chat.completions.create(**kwargs)

        return LLMResponse(
            content=response.choices[0].message.content,
            model=response.model,
            usage={
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens
            },
            finish_reason=response.choices[0].finish_reason
        )

    def _stream_openai(self, **kwargs) -> Generator[str, None, None]:
        """Stream response from OpenAI."""
        kwargs["stream"] = True
        response = self.client.chat.completions.create(**kwargs)

        for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def is_available(self) -> bool:
        """Check if LLM is available."""
        return self.provider != "none"

    def count_tokens(self, text: str) -> int:
        """
        Estimate token count for text.

        Uses tiktoken for OpenAI, approximation for Anthropic.
        """
        if self.provider == "openai":
            try:
                import tiktoken
                encoding = tiktoken.encoding_for_model(config.LLM_MODEL)
                return len(encoding.encode(text))
            except:
                pass

        # Rough approximation: ~4 chars per token
        return len(text) // 4


class MockLLMClient(LLMClient):
    """Mock LLM client for testing without API keys."""

    def __init__(self):
        self.provider = "mock"
        self._client = None

    def generate(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = None,
        max_tokens: int = None,
        temperature: float = None,
        stream: bool = False
    ) -> LLMResponse:
        """Return a mock response."""
        last_message = messages[-1]["content"] if messages else ""

        mock_content = f"""Based on the available knowledge base, I can provide the following information:

This is a mock response for testing purposes. In production, this would be replaced with actual LLM-generated content based on the retrieved context.

Your question was: "{last_message[:100]}..."

Please configure ANTHROPIC_API_KEY or OPENAI_API_KEY for production use."""

        return LLMResponse(
            content=mock_content,
            model="mock-model",
            usage={"input_tokens": 100, "output_tokens": 50},
            finish_reason="stop"
        )

    def is_available(self) -> bool:
        return True
