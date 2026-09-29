"""Provider-neutral types. Views and services only ever see these, never a provider wire format."""
from dataclasses import dataclass, field


@dataclass
class ChatMessage:
    role: str  # "user" | "assistant"
    content: str


@dataclass
class ChatRequest:
    model_id: str
    messages: list[ChatMessage]
    max_tokens: int = 1024
    system: str = ""  # instructions for the model; each adapter maps it to the provider's native slot


@dataclass
class TextDelta:
    text: str


@dataclass
class ReasoningDelta:
    text: str


@dataclass
class Usage:
    input_tokens: int
    output_tokens: int  # includes reasoning tokens, as billed by the proxy


@dataclass
class Done:
    finish_reason: str = ""


@dataclass
class Error:
    kind: str  # auth | bad_request | rate_limit | upstream | network | protocol
    message: str
    status: int = 0


StreamEvent = TextDelta | ReasoningDelta | Usage | Done | Error


# Provider spellings of "stopped because the token budget ran out" (see fixtures/proxy/*/stream_truncated.txt).
TRUNCATION_REASONS = {"length", "max_tokens", "MAX_TOKENS"}


def is_truncated(finish_reason: str) -> bool:
    return finish_reason in TRUNCATION_REASONS


def error_kind(status: int) -> str:
    if status in (401, 403):
        return "auth"
    if status == 429:
        return "rate_limit"
    if status in (400, 404, 422):
        return "bad_request"
    return "upstream"
