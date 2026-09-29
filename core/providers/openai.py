import json

from django.conf import settings

from .base import ProviderAdapter, iter_sse
from .types import ChatRequest, Done, Error, ReasoningDelta, TextDelta, Usage


class OpenAIAdapter(ProviderAdapter):
    provider = "openai"

    def url(self, req):
        return f"{settings.PROXY_URL}/openai/v1/chat/completions"

    def headers(self, key):
        return {"Authorization": f"Bearer {key}"}

    def body(self, req: ChatRequest):
        return {
            "model": req.model_id,
            "stream": True,
            # Without this the proxy sends no usage at all, and we can't bill.
            "stream_options": {"include_usage": True},
            "max_tokens": req.max_tokens,
            "messages": [{"role": m.role, "content": m.content} for m in req.messages],
        }

    def parse_stream(self, lines):
        finish, usage = "", None
        for _event, data in iter_sse(lines):
            if data == "[DONE]":
                break
            try:
                chunk = json.loads(data)
            except ValueError:
                yield Error("protocol", "unparseable stream chunk")
                return
            for choice in chunk.get("choices") or []:
                delta = choice.get("delta") or {}
                if delta.get("reasoning_content"):
                    yield ReasoningDelta(delta["reasoning_content"])
                if delta.get("content"):
                    yield TextDelta(delta["content"])
                finish = choice.get("finish_reason") or finish
            if chunk.get("usage"):
                u = chunk["usage"]
                usage = Usage(u.get("prompt_tokens", 0), u.get("completion_tokens", 0))
        if usage:
            yield usage
        yield Done(finish)
