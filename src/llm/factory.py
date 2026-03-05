"""
LLM Factory for creating appropriate LLM provider instances.
"""

from typing import Optional
from .base import BaseLLM, LLMProvider
from .ollama_provider import OllamaProvider
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider
from .groq_provider import GroqProvider


class LLMFactory:
    """Factory class for creating LLM provider instances"""

    @staticmethod
    def create_llm(
        provider: str,
        model: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        **kwargs
    ) -> BaseLLM:
        """
        Create an LLM provider instance based on the provider type.

        Args:
            provider: Provider name (ollama, openai, anthropic, groq)
            model: Model name to use
            api_key: API key for cloud providers
            base_url: Base URL for local providers (e.g., Ollama)
            **kwargs: Additional provider-specific parameters

        Returns:
            Instance of the appropriate LLM provider

        Raises:
            ValueError: If provider is not supported or required parameters are missing
        """
        provider = provider.lower()

        if provider == LLMProvider.OLLAMA:
            return OllamaProvider(
                model=model,
                base_url=base_url or "http://localhost:11434",
                **kwargs
            )

        elif provider == LLMProvider.OPENAI:
            if not api_key:
                raise ValueError("OpenAI provider requires an API key")
            return OpenAIProvider(model=model, api_key=api_key, **kwargs)

        elif provider == LLMProvider.ANTHROPIC:
            if not api_key:
                raise ValueError("Anthropic provider requires an API key")
            return AnthropicProvider(model=model, api_key=api_key, **kwargs)

        elif provider == LLMProvider.GROQ:
            if not api_key:
                raise ValueError("Groq provider requires an API key")
            return GroqProvider(model=model, api_key=api_key, **kwargs)

        else:
            raise ValueError(
                f"Unsupported LLM provider: {provider}. "
                f"Supported providers: {[p.value for p in LLMProvider]}"
            )
