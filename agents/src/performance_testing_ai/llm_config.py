import os
from enum import Enum
from typing import Optional
from crewai import LLM
from dotenv import load_dotenv

load_dotenv()

class LLMProvider(str, Enum):
    MOCK = "mock"
    OPENAI = "openai"
    GEMINI = "gemini"
    OLLAMA = "ollama"
    ANTHROPIC = "anthropic"
    CUSTOM = "custom"

def is_mock_mode() -> bool:
    """Returns True if MOCK_MODE is enabled via environment variable (default: true)."""
    return os.getenv("PERFORMANCE_TESTING_MOCK_MODE", "true").lower() in ("true", "1", "yes")

def get_configured_provider() -> LLMProvider:
    """
    Determines the active LLM provider based on environment variables.
    If MOCK_MODE is enabled, returns LLMProvider.MOCK.
    Otherwise reads LLM_PROVIDER or auto-detects from available API keys.
    """
    if is_mock_mode():
        return LLMProvider.MOCK

    provider_str = os.getenv("LLM_PROVIDER", "").lower().strip()
    if provider_str in (p.value for p in LLMProvider):
        return LLMProvider(provider_str)

    # Auto-detection from environment variables
    if os.getenv("GEMINI_API_KEY"):
        return LLMProvider.GEMINI
    if os.getenv("OPENAI_API_KEY"):
        return LLMProvider.OPENAI
    if os.getenv("ANTHROPIC_API_KEY"):
        return LLMProvider.ANTHROPIC
    if os.getenv("OLLAMA_BASE_URL"):
        return LLMProvider.OLLAMA

    # Default to MOCK if no provider credentials are configured
    return LLMProvider.MOCK

def create_llm(
    provider: Optional[LLMProvider] = None,
    model: Optional[str] = None,
    **kwargs,
) -> Optional[LLM]:
    """
    Factory function for instantiating a CrewAI LLM instance based on provider configuration.
    Returns None if provider is MOCK or MOCK_MODE is enabled.
    Does NOT require API keys when in MOCK_MODE.
    """
    active_provider = provider or get_configured_provider()

    if active_provider == LLMProvider.MOCK:
        return None

    if active_provider == LLMProvider.OPENAI:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY is required for OpenAI provider. "
                "Set OPENAI_API_KEY in your .env or run with PERFORMANCE_TESTING_MOCK_MODE=true."
            )
        model_name = model or os.getenv("OPENAI_MODEL_NAME") or os.getenv("MODEL", "gpt-4o-mini")
        return LLM(model=model_name, api_key=api_key, **kwargs)

    if active_provider == LLMProvider.GEMINI:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY is required for Gemini provider. "
                "Set GEMINI_API_KEY in your .env or run with PERFORMANCE_TESTING_MOCK_MODE=true."
            )
        model_name = model or os.getenv("GEMINI_MODEL_NAME", "gemini/gemini-3.5-flash")
        return LLM(model=model_name, api_key=api_key, **kwargs)

    if active_provider == LLMProvider.OLLAMA:
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        model_name = model or os.getenv("OLLAMA_MODEL", "ollama/llama3.2")
        return LLM(model=model_name, base_url=base_url, **kwargs)

    if active_provider == LLMProvider.ANTHROPIC:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is required for Anthropic provider. "
                "Set ANTHROPIC_API_KEY in your .env or run with PERFORMANCE_TESTING_MOCK_MODE=true."
            )
        model_name = model or os.getenv("ANTHROPIC_MODEL", "anthropic/claude-3-5-sonnet-20241022")
        return LLM(model=model_name, api_key=api_key, **kwargs)

    if active_provider == LLMProvider.CUSTOM:
        model_name = model or os.getenv("CUSTOM_LLM_MODEL")
        if not model_name:
            raise ValueError("CUSTOM_LLM_MODEL is required for custom provider.")
        return LLM(model=model_name, **kwargs)

    return None
