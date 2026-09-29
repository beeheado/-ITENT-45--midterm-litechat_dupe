import json

from django.conf import settings

from .base import ProviderAdapter, iter_sse
from .types import ChatRequest, Done, Error, TextDelta, Usage

ROLE = {"user": "user", "assistant": "model"}  # Gemini calls the assistant "model"


class GoogleAdapter(ProviderAdapter):
    provider = "google"

    def url(self, req):
        return f"{settings.PROXY_URL}/google/v1beta/models/{req.model_id}:streamGenerateContent?alt=sse"

    def headers(self, key):
        return {"x-goog-api-key": key}

    def body(self, req: ChatRequest):
        body = {
            "contents": [{"role": ROLE[m.role], "parts": [{"text": m.content}]} for m in req.messages],
            "generationConfig": {"maxOutputTokens": req.max_tokens},
        }
        if req.system:
            body["systemInstruction"] = {"parts": [{"text": req.system}]}
        return body

    def parse_stream(self, lines):
        finish, usage = "", None
        for _event, data in iter_sse(lines):
            try:
                chunk = json.loads(data)
            except ValueError:
                yield Error("protocol", "unparseable stream chunk")
                return
            for cand in chunk.get("candidates") or []:
                for part in (cand.get("content") or {}).get("parts") or []:
                    if part.get("text"):
                        yield TextDelta(part["text"])
                finish = cand.get("finishReason") or finish
            meta = chunk.get("usageMetadata")
            if meta:
                out = meta.get("candidatesTokenCount", 0) + meta.get("thoughtsTokenCount", 0)
                usage = Usage(meta.get("promptTokenCount", 0), out)
        if usage:
            yield usage
        yield Done(finish)
