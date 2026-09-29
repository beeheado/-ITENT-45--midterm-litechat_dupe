"""Capture real proxy responses into fixtures/proxy/ (keys redacted).

Usage: python scripts/capture_proxy.py [case ...]   (cases: models completion stream stream_truncated stream_system_prompt error_bad_model error_bad_key)
Tooling only: not part of the Django app. Reads keys from .env.
"""

import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "fixtures" / "proxy"
load_dotenv(ROOT / ".env")

BASE = os.environ["LITECHAT_PROXY_URL"].rstrip("/")
KEYS = {
    "openai": os.environ["OPENAI_PROXY_KEY"],
    "anthropic": os.environ["ANTHROPIC_PROXY_KEY"],
    "google": os.environ["GOOGLE_PROXY_KEY"],
}
PROMPT = "Reply with exactly: pong"

# provider -> (auth headers builder, model)
PROVIDERS = {
    "openai": {
        "model": "gpt-5.6-luna",
        "headers": lambda k: {"Authorization": f"Bearer {k}"},
        "models_url": f"{BASE}/openai/v1/models",
        "chat_url": f"{BASE}/openai/v1/chat/completions",
        "body": lambda m: {
            "model": m,
            "messages": [{"role": "user", "content": PROMPT}],
        },
        "stream_body": lambda m: {
            "model": m,
            "stream": True,
            "stream_options": {"include_usage": True},
            "messages": [{"role": "user", "content": PROMPT}],
        },
        "stream_url": f"{BASE}/openai/v1/chat/completions",
    },
    "anthropic": {
        "model": "claude-haiku-4-5-20251001",
        "headers": lambda k: {"x-api-key": k, "anthropic-version": "2023-06-01"},
        "models_url": f"{BASE}/anthropic/v1/models",
        "chat_url": f"{BASE}/anthropic/v1/messages",
        "body": lambda m: {
            "model": m,
            "max_tokens": 256,
            "messages": [{"role": "user", "content": PROMPT}],
        },
        "stream_body": lambda m: {
            "model": m,
            "max_tokens": 256,
            "stream": True,
            "messages": [{"role": "user", "content": PROMPT}],
        },
        "stream_url": f"{BASE}/anthropic/v1/messages",
    },
    "google": {
        "model": "gemini-3.8-flash",
        "headers": lambda k: {"x-goog-api-key": k},
        "models_url": f"{BASE}/google/v1beta/models",
        "chat_url": f"{BASE}/google/v1beta/models/gemini-3.8-flash:generateContent",
        "body": lambda m: {"contents": [{"role": "user", "parts": [{"text": PROMPT}]}]},
        "stream_body": lambda m: {
            "contents": [{"role": "user", "parts": [{"text": PROMPT}]}]
        },
        "stream_url": f"{BASE}/google/v1beta/models/gemini-3.8-flash:streamGenerateContent?alt=sse",
    },
}


LONG_PROMPT = "Explain in detail how TCP congestion control works."


def truncated_body(name: str, model: str) -> dict:
    """A streaming request with a tiny token budget so a reasoning model runs out before answering."""
    msgs = [{"role": "user", "content": LONG_PROMPT}]
    if name == "openai":
        return {"model": model, "stream": True, "max_tokens": 30, "stream_options": {"include_usage": True}, "messages": msgs}
    if name == "anthropic":
        return {"model": model, "stream": True, "max_tokens": 30, "messages": msgs}
    return {
        "contents": [{"role": "user", "parts": [{"text": LONG_PROMPT}]}],
        "generationConfig": {"maxOutputTokens": 30},
    }


SYSTEM_PROMPT = "Start every reply with the single word BONJOUR in capitals, then answer normally."


def system_prompt_body(name: str, model: str) -> dict:
    """A streaming request carrying a system prompt in each provider's native slot."""
    q = "What is 2+2?"
    if name == "openai":
        return {"model": model, "stream": True, "max_tokens": 2000, "stream_options": {"include_usage": True},
                "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": q}]}
    if name == "anthropic":
        return {"model": model, "stream": True, "max_tokens": 2000, "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": q}]}
    return {"systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [{"role": "user", "parts": [{"text": q}]}],
            "generationConfig": {"maxOutputTokens": 2000}}


def redact(text: str) -> str:
    for key in KEYS.values():
        text = text.replace(key, "REDACTED")
    return text


def save(provider: str, case: str, status: int, body: str, ext: str = "json") -> None:
    d = OUT / provider
    d.mkdir(parents=True, exist_ok=True)
    body = redact(body)
    if ext == "json":
        try:
            body = json.dumps(json.loads(body), indent=2)
        except ValueError:
            pass
    (d / f"{case}.{ext}").write_text(f"{body}\n")
    print(f"{provider}/{case}.{ext}: HTTP {status}")


def main() -> int:
    only = set(sys.argv[1:])

    def want(case: str) -> bool:
        return not only or case in only

    with httpx.Client(timeout=60) as c:
        for name, p in PROVIDERS.items():
            h = {**p["headers"](KEYS[name]), "Content-Type": "application/json"}
            model = p["model"]

            if want("models"):
                r = c.get(p["models_url"], headers=h)
                save(name, "models", r.status_code, r.text)

            if want("completion"):
                r = c.post(p["chat_url"], headers=h, json=p["body"](model))
                save(name, "completion", r.status_code, r.text)

            if want("stream"):
                with c.stream(
                    "POST", p["stream_url"], headers=h, json=p["stream_body"](model)
                ) as r:
                    raw = "".join(r.iter_text())
                save(name, "stream", r.status_code, raw, ext="txt")

            if want("stream_truncated"):
                with c.stream(
                    "POST", p["stream_url"], headers=h, json=truncated_body(name, model)
                ) as r:
                    raw = "".join(r.iter_text())
                save(name, "stream_truncated", r.status_code, raw, ext="txt")

            if want("stream_system_prompt"):
                with c.stream(
                    "POST", p["stream_url"], headers=h, json=system_prompt_body(name, model)
                ) as r:
                    raw = "".join(r.iter_text())
                save(name, "stream_system_prompt", r.status_code, raw, ext="txt")

            if want("error_bad_model"):
                # Google carries the model in the URL, others in the body: swap both.
                bad_url = p["chat_url"].replace(model, "no-such-model")
                r = c.post(bad_url, headers=h, json=p["body"]("no-such-model"))
                save(name, "error_bad_model", r.status_code, r.text)

            if want("error_bad_key"):
                bad_h = {
                    **p["headers"]("lp_invalid_key"),
                    "Content-Type": "application/json",
                }
                r = c.post(p["chat_url"], headers=bad_h, json=p["body"](model))
                save(name, "error_bad_key", r.status_code, r.text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
