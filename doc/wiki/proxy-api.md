# Proxy API reference

Source of truth: live captures in `fixtures/proxy/<provider>/` (made by `scripts/capture_proxy.py`, captured 2026-09-29) plus https://proxy.litechat.ai/docs (revision 2026-09-19).

The proxy exposes each provider's *native* wire format. It is not one unified API. Per the proxy docs, all three interfaces are backed by the same underlying model (DeepSeek Flash), so behaviour does not match the named providers. Only the interface shapes do.

## Endpoints and auth

| Provider | Base URL | Auth header | Model id | Chat path |
|---|---|---|---|---|
| OpenAI | `/openai/v1` | `Authorization: Bearer <key>` | `gpt-5.6-luna` | `POST /chat/completions` (Responses API also exists) |
| Anthropic | `/anthropic` | `x-api-key: <key>` + `anthropic-version: 2023-06-01` | `claude-haiku-4-5-20251001` | `POST /v1/messages` |
| Google | `/google` | `x-goog-api-key: <key>` | `gemini-3.8-flash` | `POST /v1beta/models/{model}:generateContent` (stream: `:streamGenerateContent?alt=sse`) |

Each provider has its own key. Each `models` endpoint lists exactly one model.

## Captures and shapes

| File | Shape notes |
|---|---|
| `*/models.json` | OpenAI: `{data:[{id,...}]}`. Anthropic: `{data:[{id,display_name}]}`. Google: `{models:[{name:"models/<id>",displayName}]}`. |
| `openai/completion.json` | `choices[0].message.content` (answer) and `.reasoning_content` (thinking, non-standard). `choices[0].finish_reason`. Usage: `usage.prompt_tokens`, `completion_tokens` (includes `completion_tokens_details.reasoning_tokens`), `total_tokens`. |
| `anthropic/completion.json` | `content[]` blocks: `{type:"thinking",thinking}` then `{type:"text",text}`. `stop_reason`. Usage: `usage.input_tokens`, `output_tokens`. |
| `google/completion.json` | `candidates[0].content.parts[].text`, `finishReason`. Usage: `usageMetadata.promptTokenCount`, `candidatesTokenCount`, `totalTokenCount`. |
| `openai/stream.txt` | SSE `data:` lines of `chat.completion.chunk`, ending with `data: [DONE]`. Reasoning arrives first in `delta.reasoning_content`, then the answer in `delta.content`. Final `finish_reason` chunk, then **a separate chunk with `choices: []` and `usage`** (only because we sent `stream_options.include_usage`). |
| `anthropic/stream.txt` | SSE with `event:` + `data:`. Order: `message_start` (input tokens), `content_block_start/delta/stop` (thinking block 0, text block 1), `message_delta` (**final `output_tokens`** and `stop_reason`), `message_stop`. `ping` events can appear. |
| `google/stream.txt` | SSE `data:` lines only, each a partial `GenerateContentResponse`. Final chunk has `finishReason` and `usageMetadata`. No terminator line. |
| `*/error_*.json` | See below. |

## Errors

| Case | HTTP | Body shape |
|---|---|---|
| Bad key, OpenAI | 401 | `{error:{code,message,param,type:"authentication_error"}}` |
| Bad key, Anthropic | 401 | `{type:"error",error:{type:"authentication_error",message}}` |
| Bad key, Google | 401 | `{error:{code:401,message,status:"UNAUTHORIZED"}}` |
| Bad model, OpenAI / Anthropic | 400 | `unknown model`, same envelope as above with `invalid_request_error` |
| Bad model, Google | not captured | Google puts the model in the URL, so the capture script's "bad model" call did not use a bad model. Re-probe with a bad URL model when needed. |

Documented by the proxy: 400 fix request; 401/403 key/provider/expiry; 429 back off; 502/504 upstream failure; **usage can be unknown after a failure; do not auto-retry after partial output**.

## Gotchas that shape the design
1. **Token usage differs per provider and arrives at different times.** OpenAI: last chunk (opt-in). Anthropic: input in `message_start`, output in `message_delta`. Google: last chunk.
2. **Reasoning tokens are billed as output tokens** (`completion_tokens` includes them). Reasoning text is separate from the answer and must be kept out of the visible message, or shown collapsed.
3. **A tiny prompt reports ~208 input tokens.** The proxy adds hidden overhead. Meter from reported usage, never from our own estimate.
4. **Usage may be missing on failure or cancellation.** The ledger needs a policy for this (see study 001).
5. **The proxy publishes no prices.** Per-model prices must be defined by us (seed data).
6. Images and provider file APIs exist (files expire after 1 hour, 64 MiB per file). Not needed for the MVP.
7. Assistant roles differ: OpenAI/Anthropic use `assistant`, Google uses `model`. Google has `parts` instead of `content`.
