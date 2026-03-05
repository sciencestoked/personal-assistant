"""
Base LLM provider interface for the personal assistant.
Supports multiple providers: Ollama, OpenAI, Anthropic, and Groq.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from enum import Enum


class LLMProvider(str, Enum):
    """Supported LLM providers"""
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GROQ = "groq"


class Message:
    """Standard message format for LLM interactions"""
    def __init__(self, role: str, content: str):
        self.role = role  # 'system', 'user', or 'assistant'
        self.content = content

    def to_dict(self) -> Dict[str, str]:
        return {"role": self.role, "content": self.content}


class BaseLLM(ABC):
    """Abstract base class for LLM providers"""

    def __init__(self, model: str, **kwargs):
        self.model = model
        self.config = kwargs

    @abstractmethod
    async def generate(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Generate a response from the LLM.

        Args:
            messages: List of conversation messages
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters

        Returns:
            Generated text response
        """
        pass

    @abstractmethod
    async def generate_stream(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ):
        """
        Generate a streaming response from the LLM.

        Args:
            messages: List of conversation messages
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters

        Yields:
            Chunks of generated text
        """
        pass

    def create_system_message(self, content: str) -> Message:
        """Helper to create a system message"""
        return Message(role="system", content=content)

    def create_user_message(self, content: str) -> Message:
        """Helper to create a user message"""
        return Message(role="user", content=content)

    def create_assistant_message(self, content: str) -> Message:
        """Helper to create an assistant message"""
        return Message(role="assistant", content=content)
