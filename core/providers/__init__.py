from .anthropic import AnthropicAdapter
from .google import GoogleAdapter
from .openai import OpenAIAdapter

ADAPTERS = {a.provider: a for a in (OpenAIAdapter(), AnthropicAdapter(), GoogleAdapter())}


def get_adapter(provider: str):
    return ADAPTERS[provider]
