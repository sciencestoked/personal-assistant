"""
Anthropic Claude LLM provider implementation.
Supports Claude 3.5 Sonnet and other Claude models.
"""

from typing import List, Optional, AsyncIterator
from anthropic import AsyncAnthropic
from .base import BaseLLM, Message


class AnthropicProvider(BaseLLM):
    """Anthropic provider for Claude models"""

    def __init__(self, model: str, api_key: str, **kwargs):
        super().__init__(model, **kwargs)
        self.client = AsyncAnthropic(api_key=api_key)

    async def generate(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = 1024,
        **kwargs
    ) -> str:
        """Generate a response using Claude"""
        # Separate system messages from conversation
        system_message = ""
        conversation_messages = []

        for msg in messages:
            if msg.role == "system":
                system_message += msg.content + "\n"
            else:
                conversation_messages.append(msg.to_dict())

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens or 1024,
                temperature=temperature,
                system=system_message.strip() if system_message else None,
                messages=conversation_messages,
                **kwargs
            )
            return response.content[0].text
        except Exception as e:
            raise Exception(f"Anthropic API error: {str(e)}")

    async def generate_stream(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = 1024,
        **kwargs
    ) -> AsyncIterator[str]:
        """Generate a streaming response using Claude"""
        # Separate system messages from conversation
        system_message = ""
        conversation_messages = []

        for msg in messages:
            if msg.role == "system":
                system_message += msg.content + "\n"
            else:
                conversation_messages.append(msg.to_dict())

        try:
            async with self.client.messages.stream(
                model=self.model,
                max_tokens=max_tokens or 1024,
                temperature=temperature,
                system=system_message.strip() if system_message else None,
                messages=conversation_messages,
                **kwargs
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as e:
            raise Exception(f"Anthropic streaming error: {str(e)}")

    async def close(self):
        """Close the client"""
        await self.client.close()
