# Study 001: Architecture

Timestamp: 2026-09-29T22:10:00-07:00 (approximate)
Status: proposed, awaiting user review

## 1. Goal
Build Darkchat, a clone of Litechat's core functionality: metered, a la carte access to LLMs for non-power users. Nothing here is built yet.

## 2. What Litechat's core functionality is
Evidence: the public landing page at litechat.ai (fetched 2026-09-29). It discloses no pricing, credit or balance model, so the metering features below are inferred from the assignment brief ("metered, a la carte") and marked as such.

| Feature | Source | Scope |
|---|---|---|
| Login / accounts | site | **Core** |
| Chat with streaming replies | site | **Core** |
| Switch between models from several providers (OpenAI, Anthropic; Google via proxy) | site + brief | **Core** |
| Conversation history: saved, retrievable, renameable | site | **Core** |
| Prepaid balance, and per-message cost deducted from it | brief (inferred) | **Core** (this is the differentiator) |
| Usage / transaction history | inferred | Core-lite (a ledger view) |
| Real-time web search toggle | site | Nice-to-have, likely out (proxy has no search tool) |
| Uploads: images, documents, PDFs, spreadsheets | site | Nice-to-have (proxy supports images and files; defer) |
| Real payments (Stripe) | inferred | Out of scope unless the user says otherwise |

**Recommendation:** implement accounts, multi-model streaming chat, history with rename, and a metered prepaid balance with a visible ledger. Defer uploads and web search.

## 3. Exogenous inputs: what the proxy really is
Full detail in `doc/wiki/proxy-api.md`. Findings that drive the design:
- Three **native-format** endpoints (OpenAI chat completions, Anthropic messages, Gemini generateContent), each with its own key and header. Each exposes **one model**.
- All three are backed by one underlying model (per proxy docs), so "model choice" is real at the interface level only.
- Streaming is SSE in three different dialects. **Usage arrives at a different time in each** (OpenAI: opt-in final chunk; Anthropic: split across `message_start` and `message_delta`; Google: final chunk).
- Reasoning text is streamed separately and billed as output tokens.
- A trivial prompt reports ~208 input tokens, so hidden overhead exists. We meter from reported usage only.
- **No prices are provided.**
- Usage may be unknown after failures, and the proxy says not to retry after partial output.

**Pricing source (proposal):** seed `LLMModel` rows with our own per-million-token prices, set to realistic values that differ per provider so that the model choice affects cost. Example: gpt-5.6-luna at 0.25 in / 2.00 out, claude-haiku at 1.00 in / 5.00 out, gemini-3.8-flash at 0.30 in / 2.50 out (USD per million tokens; placeholders, editable in admin). This is an open question for the user.

## 4. Framework fit: Django

**Fits well:** auth, ORM, migrations, admin (for granting credits and editing prices with no UI work), templates and forms, and a strong test story with pytest-django.

**Friction, with mitigations:**
- **Streaming.** Under WSGI, a `StreamingHttpResponse` holds one worker per active stream. That is fine for a course project with a handful of users. Under ASGI with async views, streams don't pin a thread. *Recommendation:* run dev with `runserver` (which supports streaming) and write the streaming view as a **sync generator over `httpx` streaming** first. Keep the adapter interface such that an async version is a small change. Note ASGI (uvicorn) as the deploy path if we deploy.
- **Sync vs async ORM.** Mixing the async ORM with money code is risky. Keep ledger writes in plain sync transactions (a short one at the end of a stream), and only the network I/O streams.
- **HTMX vs SPA.** HTMX with the SSE extension (or a tiny `fetch` + `ReadableStream` snippet) gives streaming UI with no build step, which honours "no JS framework." Cost: the token-by-token render is less polished than React. Acceptable.
- **SQLite.** Single-writer, so concurrent balance updates serialise, which is actually *safe* for a ledger here. Use `transaction.atomic()` plus `select_for_update()` (a no-op on SQLite but correct on Postgres). Limits: no real concurrency, so switch to Postgres if deployed.

## 5. Provider abstraction
One interface, three adapters. Internal types:

```
ChatRequest(model: LLMModel, messages: list[Msg(role, content)], max_tokens)
StreamEvent = TextDelta(text) | ReasoningDelta(text) | Usage(input, output, reasoning?) | Done(finish_reason) | Error(kind, message)

class ProviderAdapter:
    def stream(self, req: ChatRequest) -> Iterator[StreamEvent]
```

Each adapter owns: URL, auth header, request body building (`assistant` vs `model` role, `parts`), SSE parsing, and mapping errors (401/400/429/5xx) into `Error`. The chat view only consumes `StreamEvent`s and never sees a provider format. Adapters are tested by **replaying `fixtures/proxy/*/stream.txt`** through the parser with no network.

Design choice: streaming-only. Non-streaming is a special case, so having one code path halves the test surface.

## 6. Proposed schema
Credits are stored as **integer micro-credits** (1 credit = 1 USD = 1,000,000 micro-units), never floats.

- `User`: Django's built-in auth user.
- `Wallet`: `user` (1:1), `balance_micros` (int, `CHECK >= 0`). A cached total. The ledger is the truth.
- `LedgerEntry` (append-only): `wallet`, `kind` (`topup` / `charge` / `adjustment`), `amount_micros` (signed), `balance_after_micros`, `message` (nullable FK), `note`, `created_at`. Never updated or deleted; corrections are new rows.
- `LLMModel`: `provider` (openai/anthropic/google), `model_id`, `display_name`, `input_price_micros_per_mtok`, `output_price_micros_per_mtok`, `is_active`, `max_output_tokens`.
- `Conversation`: `user`, `title` (renameable), `model` (last used), `created_at`, `updated_at`.
- `Message`: `conversation`, `role` (user/assistant), `content`, `reasoning` (nullable), `model` (FK, snapshot of which model answered), `input_tokens`, `output_tokens`, `cost_micros`, `status` (`pending` / `complete` / `failed` / `cancelled`), `error`, `created_at`.

Prices and cost are snapshotted onto the message (`cost_micros`), so later price edits never rewrite history.

### Charging: atomicity and failure handling
1. **Pre-check:** before calling the proxy, require `balance >= a reserve` (e.g., the cost of `max_tokens` output plus estimated input). If not, return an "insufficient balance" response and make no call.
2. Create the user `Message` and an assistant `Message(status=pending)`.
3. Stream to the client, accumulating text and usage.
4. **On completion**, in one `transaction.atomic()` block: lock the wallet, compute cost from *reported* usage, mark the message `complete`, insert the `LedgerEntry`, decrement the balance. Message finalisation and the charge commit or roll back together.
5. **On failure/disconnect with usage known:** charge for the reported usage, status `failed`/`cancelled`. **With usage unknown** (the proxy says this can happen): do not charge, mark `failed`, and record the fact in `error`. The user is never billed for nothing. Tradeoff: a small leakage if a client can force cancellations, mitigated by the reserve pre-check and a per-request `max_tokens` cap.
6. The balance can slightly overshoot only within the reserve margin. Clamp at 0 and record an adjustment rather than going negative (the DB check constraint enforces it).

## 7. Getting credits in a demo
Real payments are out of scope. Options: (a) admin grants credits in Django admin, (b) a "Add $5 demo credits" button that creates a `topup` ledger entry, (c) a starting grant at signup. **Recommendation:** (b) + (c), with (a) for the grader. All go through the same ledger function, so real payments could slot in later.

## 8. Risks
- The three providers being one model can make "model switching" look identical. Mitigation: show the provider/model per message and use different prices.
- The proxy is a shared course resource with unknown rate limits. Handle 429 with a bounded retry only *before* output starts.
- Hidden ~208-token overhead makes cost estimates wrong, so we only charge on reported usage.
- Streaming under WSGI pins workers. Fine at this scale.
- Keys live only in `.env`. They must never reach the browser, so all calls stay server-side.
- Transcripts are a graded deliverable, so remember to export them.

## 9. Open questions for you
1. **Prices:** are the placeholder per-token prices acceptable, or do you want a specific rate card (or one flat price)?
2. **Scope:** confirm uploads and web search are deferred, and that no real payments are wanted.
3. **Credits:** confirm the demo top-up button and starting grant.
4. **Reasoning text:** show it collapsed under the reply, or hide it entirely? (It's billed either way.)
5. **Deployment:** local only, or deployed somewhere? This decides WSGI/ASGI and SQLite vs Postgres.
6. **Google bad-model probe:** low priority, and I'll re-capture it when we build the adapter.

## 10. Decision
Build it: Django + HTMX + SQLite, a streaming-only provider adapter interface, an append-only micro-credit ledger, and charging on reported usage.
