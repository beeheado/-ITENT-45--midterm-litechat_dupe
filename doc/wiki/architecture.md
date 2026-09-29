# Architecture

Django 5.2 + SQLite, server-rendered templates, one small inline JS streaming reader. All model traffic goes through `proxy.litechat.ai` (see `proxy-api.md`).

## Request flow for one message
1. Browser POSTs `content` + `model` to `/c/<id>/send/` (form + CSRF).
2. `views.send` validates, rejects if a reply is already pending (409), and runs `ledger.ensure_can_afford(reserve)`; if the balance can't cover the reserve it returns 402 and calls nothing.
3. It saves the user message and a `pending` assistant message, then returns a `StreamingHttpResponse` of newline-delimited JSON (`reasoning` / `text` / `done` events).
4. `_stream_reply` iterates `adapter.stream(request)`. Adapters turn each provider's SSE dialect into the neutral events in `core/providers/types.py`.
5. In all outcomes it calls `ledger.finalize_message(...)`, which saves the message and writes the ledger charge in **one transaction**.
   - success: billed from provider-reported usage
   - provider error / stream ended without `Done`: status `failed`
   - browser disconnected (`GeneratorExit`): status `cancelled`, saved partial text
   - no usage reported: not billed

## Modules
- `core/providers/`: `base.py` (SSE framing, HTTP, error mapping), `openai.py`, `anthropic.py`, `google.py`, `types.py`
- `core/ledger.py`: `cost_for`, `estimate_reserve`, `ensure_can_afford`, `credit`, `finalize_message`
- `core/signals.py`: new user => `Wallet` + welcome grant (`STARTING_GRANT_MICROS`, $1.00)
- `core/views.py`: auth, chat, send/stream, rename, delete, usage

## Testing approach
- Adapters: replay `fixtures/proxy/*/stream.txt` and error fixtures; HTTP layer via `httpx.MockTransport`.
- Views: a `FakeAdapter` patched into `core.views.get_adapter`.
- Ledger: invariant helper (sum of entries == balance == last `balance_after`, never negative), rollback test.
- Live check: a manual smoke run against the real proxy (see `decisions.md`, 2026-09-29).

## Frontend (after plan 002)
`static/style.css` holds all styling (tokens for dark/light, one breakpoint at 800px). `templates/chat.html` contains a small inline script: it POSTs the form, reads the NDJSON stream, shows a "thinking" state until the first token, renders reasoning in a collapsed `<details>`, and attaches a Copy button. Message text is only ever set with `textContent`.
Admin: Wallet list actions grant credit through `core.ledger.credit`.

## Account page and how settings reach the model (plan 004)
`/account/` (`core/account_views.py`) shows the profile, saves the global system prompt, manages memory items, stores the auto-memory switch and the default app, and shows billing. Every mutation is a POST that redirects back with a flash message, so it works without JavaScript.
- **System prompt path:** `send()` calls `prompting.build_system_prompt(user)` (the saved prompt, then a "Things to remember about the user:" block of memories, oldest first) and puts it in `ChatRequest.system`. Adapters map it to each provider's native slot: OpenAI a leading `system` message, Anthropic top-level `system`, Gemini `systemInstruction`. It is read at send time, so edits apply to existing conversations immediately. It is billed as input tokens on every message, and `ledger.estimate_reserve` counts it.
- **Login redirect:** `AppLoginView` sends the user to `APP_HOME[profile.default_app]`. SimGen and Ask do not exist yet, so all three map to the chat home; an explicit `?next=` still wins.
- **Auto-memory:** the switch is stored only. No code reads past conversations or writes AI memories yet.
