"""Adapter tests. Every stream is replayed from fixtures/proxy/: no network, no keys."""
from pathlib import Path

import httpx
import pytest

from core.providers import get_adapter
from core.providers import base as base_module
from core.providers.base import iter_sse
from core.providers.types import ChatMessage, ChatRequest, Done, Error, ReasoningDelta, TextDelta, Usage

FIX = Path(__file__).resolve().parent.parent / "fixtures" / "proxy"


def fixture(provider, name):
    return (FIX / provider / name).read_text()


def replay(provider):
    return list(get_adapter(provider).parse_stream(fixture(provider, "stream.txt").splitlines(keepends=True)))


def text_of(events):
    return "".join(e.text for e in events if isinstance(e, TextDelta))


def test_iter_sse_frames():
    frames = list(iter_sse(["event: a\n", 'data: {"x":1}\n', "\n", "data: two\n", "\n"]))
    assert frames == [("a", '{"x":1}'), ("", "two")]


def test_openai_stream():
    ev = replay("openai")
    assert text_of(ev) == "pong"
    assert "".join(e.text for e in ev if isinstance(e, ReasoningDelta)).startswith("The user wants")
    assert Usage(208, 11) in ev  # completion_tokens already includes reasoning tokens
    assert ev[-1] == Done("stop")
    assert ev.index(Usage(208, 11)) < len(ev) - 1  # usage is emitted before Done


def test_anthropic_stream():
    ev = replay("anthropic")
    assert text_of(ev) == "pong"
    assert any(isinstance(e, ReasoningDelta) for e in ev)
    assert Usage(208, 17) in ev  # input from message_start, output total from message_delta
    assert ev[-1] == Done("end_turn")


def test_google_stream():
    ev = replay("google")
    assert text_of(ev) == "pong"
    assert Usage(208, 14) in ev
    assert ev[-1] == Done("STOP")


def frames_before(provider, marker):
    """The stream text up to (not including) the first frame containing `marker`."""
    frames = fixture(provider, "stream.txt").split("\n\n")
    kept = []
    for f in frames:
        if marker in f:
            break
        kept.append(f)
    return "\n\n".join(kept) + "\n\n"


@pytest.mark.parametrize("provider,marker", [("openai", '"choices":[]'), ("google", "usageMetadata")])
def test_truncated_stream_reports_no_usage(provider, marker):
    ev = list(get_adapter(provider).parse_stream(frames_before(provider, marker).splitlines(keepends=True)))
    assert text_of(ev) == "pong"
    assert not any(isinstance(e, Usage) for e in ev)
    assert isinstance(ev[-1], Done)  # consumer decides what a stream with no usage means


def test_anthropic_disconnect_after_start_reports_only_known_input():
    ev = list(get_adapter("anthropic").parse_stream(frames_before("anthropic", "content_block_start").splitlines(keepends=True)))
    assert Usage(208, 0) in ev


def test_garbage_chunk_is_a_protocol_error():
    ev = list(get_adapter("openai").parse_stream(["data: {not json\n", "\n"]))
    assert ev == [Error("protocol", "unparseable stream chunk")]


REQ = ChatRequest("m", [ChatMessage("user", "hi"), ChatMessage("assistant", "yo"), ChatMessage("user", "again")], 77)


def test_request_bodies():
    o = get_adapter("openai").body(REQ)
    assert o["stream_options"] == {"include_usage": True} and o["messages"][1] == {"role": "assistant", "content": "yo"}
    a = get_adapter("anthropic").body(REQ)
    assert a["max_tokens"] == 77 and a["stream"] is True
    g = get_adapter("google").body(REQ)
    assert [c["role"] for c in g["contents"]] == ["user", "model", "user"]  # assistant -> model
    assert g["contents"][0]["parts"] == [{"text": "hi"}]


def test_urls_and_auth(settings):
    settings.PROXY_URL = "https://p.example"
    assert get_adapter("openai").url(REQ) == "https://p.example/openai/v1/chat/completions"
    assert get_adapter("anthropic").url(REQ) == "https://p.example/anthropic/v1/messages"
    assert get_adapter("google").url(REQ).endswith("/google/v1beta/models/m:streamGenerateContent?alt=sse")
    assert get_adapter("openai").headers("K") == {"Authorization": "Bearer K"}
    assert get_adapter("anthropic").headers("K")["x-api-key"] == "K"
    assert get_adapter("google").headers("K") == {"x-goog-api-key": "K"}


@pytest.mark.parametrize(
    "provider,case,status,kind",
    [
        ("openai", "error_bad_key.json", 401, "auth"),
        ("anthropic", "error_bad_key.json", 401, "auth"),
        ("google", "error_bad_key.json", 401, "auth"),
        ("openai", "error_bad_model.json", 400, "bad_request"),
        ("anthropic", "error_bad_model.json", 400, "bad_request"),
        ("google", "error_bad_model.json", 404, "bad_request"),
    ],
)
def test_error_fixtures(provider, case, status, kind):
    err = get_adapter(provider).parse_error(status, fixture(provider, case))
    assert isinstance(err, Error) and err.kind == kind and err.status == status and err.message


def test_error_kinds_for_rate_limit_and_upstream():
    a = get_adapter("openai")
    assert a.parse_error(429, "{}").kind == "rate_limit"
    assert a.parse_error(502, "not json").kind == "upstream"


def _patch_transport(monkeypatch, handler):
    real = httpx.Client
    monkeypatch.setattr(base_module.httpx, "Client", lambda **kw: real(transport=httpx.MockTransport(handler), **kw))


def test_stream_over_http_success(monkeypatch, settings):
    settings.PROXY_KEYS = {"openai": "K"}
    seen = {}

    def handler(request):
        seen["auth"] = request.headers["authorization"]
        return httpx.Response(200, text=fixture("openai", "stream.txt"))

    _patch_transport(monkeypatch, handler)
    ev = list(get_adapter("openai").stream(REQ))
    assert seen["auth"] == "Bearer K" and text_of(ev) == "pong" and ev[-1] == Done("stop")


def test_stream_http_error_becomes_error_event(monkeypatch):
    _patch_transport(monkeypatch, lambda r: httpx.Response(401, text=fixture("anthropic", "error_bad_key.json")))
    ev = list(get_adapter("anthropic").stream(REQ))
    assert len(ev) == 1 and ev[0].kind == "auth"


def test_stream_network_failure_becomes_error_event(monkeypatch):
    def boom(request):
        raise httpx.ConnectError("nope")

    _patch_transport(monkeypatch, boom)
    ev = list(get_adapter("google").stream(REQ))
    assert len(ev) == 1 and ev[0].kind == "network"
    assert "nope" not in ev[0].message  # don't leak transport internals
