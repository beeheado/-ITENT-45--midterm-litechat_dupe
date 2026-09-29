import json
from collections.abc import Iterable, Iterator

import httpx
from django.conf import settings

from .types import ChatRequest, Error, StreamEvent, error_kind


def iter_sse(lines: Iterable[str]) -> Iterator[tuple[str, str]]:
    """Yield (event, data) for each SSE frame. `event` is "" when the frame has none."""
    event, data = "", []
    for line in lines:
        line = line.rstrip("\r\n")
        if not line:
            if data:
                yield event, "\n".join(data)
            event, data = "", []
        elif line.startswith("event:"):
            event = line[6:].strip()
        elif line.startswith("data:"):
            data.append(line[5:].lstrip())
    if data:
        yield event, "\n".join(data)


class ProviderAdapter:
    provider = ""

    # --- subclass hooks (pure functions, unit-tested against fixtures) ---
    def url(self, req: ChatRequest) -> str:
        raise NotImplementedError

    def headers(self, key: str) -> dict:
        raise NotImplementedError

    def body(self, req: ChatRequest) -> dict:
        raise NotImplementedError

    def parse_stream(self, lines: Iterable[str]) -> Iterator[StreamEvent]:
        raise NotImplementedError

    def parse_error(self, status: int, text: str) -> Error:
        try:
            err = json.loads(text).get("error", {})
            message = err.get("message", "") if isinstance(err, dict) else str(err)
        except (ValueError, AttributeError):
            message = ""
        return Error(error_kind(status), message or f"HTTP {status}", status)

    # --- network ---
    def stream(self, req: ChatRequest) -> Iterator[StreamEvent]:
        key = settings.PROXY_KEYS.get(self.provider, "")
        headers = {**self.headers(key), "Content-Type": "application/json"}
        try:
            with httpx.Client(timeout=httpx.Timeout(60, read=120)) as client:
                with client.stream("POST", self.url(req), headers=headers, json=self.body(req)) as resp:
                    if resp.status_code != 200:
                        resp.read()
                        yield self.parse_error(resp.status_code, resp.text)
                        return
                    yield from self.parse_stream(resp.iter_lines())
        except httpx.HTTPError as exc:
            yield Error("network", f"{type(exc).__name__}: connection to the model provider failed")
