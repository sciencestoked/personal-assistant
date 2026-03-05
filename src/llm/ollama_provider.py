"""
Ollama LLM provider implementation.
Supports local LLM models like LLaMA 3.1.
"""

from typing import List, Optional, AsyncIterator
import httpx
from .base import BaseLLM, Message


class OllamaProvider(BaseLLM):
    """Ollama provider for local LLM models"""

    def __init__(self, model: str, base_url: str = "http://localhost:11434", **kwargs):
        super().__init__(model, **kwargs)
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=120.0)

    async def generate(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """Generate a response using Ollama"""
        url = f"{self.base_url}/api/chat"

        payload = {
            "model": self.model,
            "messages": [msg.to_dict() for msg in messages],
            "stream": False,
            "options": {
                "temperature": temperature,
            }
        }

        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            return result.get("message", {}).get("content", "")
        except Exception as e:
            raise Exception(f"Ollama API error: {str(e)}")

    async def generate_stream(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Generate a streaming response using Ollama"""
        url = f"{self.base_url}/api/chat"

        payload = {
            "model": self.model,
            "messages": [msg.to_dict() for msg in messages],
            "stream": True,
            "options": {
                "temperature": temperature,
            }
        }

        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        try:
            async with self.client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        import json
                        try:
                            data = json.loads(line)
                            if "message" in data:
                                content = data["message"].get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            raise Exception(f"Ollama streaming error: {str(e)}")

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
