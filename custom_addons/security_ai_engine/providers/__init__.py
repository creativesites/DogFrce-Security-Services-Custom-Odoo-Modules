from .claude import ClaudeProvider
from .openai_provider import OpenAIProvider
from .gemini import GeminiProvider

PROVIDER_MAP = {
    "claude": ClaudeProvider,
    "openai": OpenAIProvider,
    "gemini": GeminiProvider,
}


def get_provider(provider_key, api_key, model_override=None):
    cls = PROVIDER_MAP.get(provider_key)
    if not cls:
        raise ValueError(f"Unknown AI provider: {provider_key!r}")
    return cls(api_key=api_key, model_override=model_override)
