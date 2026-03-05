"""
Groq LLM provider implementation.
Supports fast inference with LLaMA and other models via Groq API.
"""

from typing import List, Optional, AsyncIterator
from openai import AsyncOpenAI
from .base import BaseLLM, Message


class GroqProvider(BaseLLM):
    """Groq provider for fast LLM inference"""

    def __init__(self, model: str, api_key: str, **kwargs):
        super().__init__(model, **kwargs)
        # Groq uses OpenAI-compatible API
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1"
        )

    async def generate(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """Generate a response using Groq"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[msg.to_dict() for msg in messages],
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            raise Exception(f"Groq API error: {str(e)}")

    async def generate_stream(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Generate a streaming response using Groq"""
        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=[msg.to_dict() for msg in messages],
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                **kwargs
            )
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            raise Exception(f"Groq streaming error: {str(e)}")

    async def close(self):
        """Close the client"""
        await self.client.close()
