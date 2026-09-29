import json

from django.conf import settings

from .base import ProviderAdapter, iter_sse
from .types import ChatRequest, Done, Error, ReasoningDelta, TextDelta, Usage


class AnthropicAdapter(ProviderAdapter):
    provider = "anthropic"

    def url(self, req):
        return f"{settings.PROXY_URL}/anthropic/v1/messages"

    def headers(self, key):
        return {"x-api-key": key, "anthropic-version": "2023-06-01"}

    def body(self, req: ChatRequest):
        body = {
            "model": req.model_id,
            "stream": True,
            "max_tokens": req.max_tokens,
            "messages": [{"role": m.role, "content": m.content} for m in req.messages],
        }
        if req.system:
            body["system"] = req.system
        return body

    def parse_stream(self, lines):
        input_tokens = output_tokens = 0
        seen_usage, finish = False, ""
        for event, data in iter_sse(lines):
            try:
                payload = json.loads(data)
            except ValueError:
                yield Error("protocol", "unparseable stream chunk")
                return
            kind = payload.get("type", event)
            if kind == "message_start":
                u = payload["message"].get("usage", {})
                input_tokens, seen_usage = u.get("input_tokens", 0), True
            elif kind == "content_block_delta":
                d = payload["delta"]
                if d.get("type") == "text_delta":
                    yield TextDelta(d["text"])
                elif d.get("type") == "thinking_delta":
                    yield ReasoningDelta(d["thinking"])
            elif kind == "message_delta":
                # output_tokens here is the running total, not an increment.
                u = payload.get("usage", {})
                output_tokens = u.get("output_tokens", output_tokens)
                input_tokens = u.get("input_tokens", input_tokens)
                finish = payload.get("delta", {}).get("stop_reason") or finish
                seen_usage = True
            elif kind == "error":
                yield Error("upstream", payload.get("error", {}).get("message", "stream error"))
                return
        if seen_usage:
            yield Usage(input_tokens, output_tokens)
        yield Done(finish)
