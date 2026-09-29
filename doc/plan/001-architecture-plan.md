# Plan 001: Architecture to working MVP

Timestamp: 2026-09-29T22:20:00-07:00 (approximate)
Based on: `doc/study/001-architecture-study.md`
Status: **approved 2026-09-29; executed (see notes on deviations below)**

Each task is one conventional commit on its own `feat/<slug>` branch (one branch per milestone). Each milestone ends with a rendezvous (`pytest`, `manage.py check`, smoke test, `--no-ff` merge to `main`) and a `docs:` wiki sync.

New dependencies: none added (`django-htmx` was not needed).

## M1: Scaffold (`feat/scaffold`)
- [x] `chore:` create Django project `darkchat` and app `core` (`django-admin startproject`, `startapp`)
- [x] `chore:` load settings from `.env` via python-dotenv (secret key, debug, proxy URL and keys); fail loudly when missing
- [x] `chore:` configure pytest-django (`pytest.ini`, `conftest.py`)
- [x] `feat:` base template with HTMX via CDN and minimal CSS
- [x] `feat:` signup, login, logout views and templates (Django auth)
- [x] `test:` auth flow tests

## M2: Models and admin (`feat/models`)
- [x] `feat:` `LLMModel` model with per-million-token prices
- [x] `feat:` `Wallet` and `LedgerEntry` models (integer micro-credits, `CHECK balance >= 0`)
- [x] `feat:` `Conversation` and `Message` models
- [x] `feat:` data migration seeding the three proxy models and placeholder prices
- [x] `feat:` register all models in admin (ledger read-only)
- [x] `feat:` create a wallet with a starting grant on signup (signal or service)
- [x] `test:` model constraint tests

## M3: Provider adapters (`feat/adapters`)
- [x] `feat:` internal types (`ChatRequest`, `StreamEvent` variants) and the `ProviderAdapter` base
- [x] `test:` fixture loader helper that replays `fixtures/proxy/*/stream.txt`
- [x] `feat:` OpenAI adapter (request body, SSE parser, usage chunk, reasoning vs content)
- [x] `feat:` Anthropic adapter (event parser, usage from `message_start` + `message_delta`)
- [x] `feat:` Google adapter (role mapping, `parts`, `usageMetadata`)
- [x] `feat:` error mapping (401/400/429/5xx to `Error` events)
- [x] `chore:` re-capture Google bad-model fixture and the missing error cases
- [x] `test:` adapter tests replaying every fixture, with no network

## M4: Metering and ledger (`feat/ledger`)
- [x] `feat:` `cost_for(model, input, output)` in integer math
- [x] `feat:` `credit(wallet, amount, kind, note)` service: atomic, locks the wallet, writes ledger and balance together
- [x] `feat:` `charge_message(message, usage)` service
- [x] `feat:` pre-flight balance/reserve check
- [x] `feat:` failure policy (charge only when usage is known; otherwise mark failed)
- [x] `test:` ledger invariants (sum of entries equals balance, never negative, atomic rollback)

## M5: Chat UI and streaming (`feat/chat`)
- [x] `feat:` conversation list + new-conversation page
- [x] `feat:` model picker (active `LLMModel`s, showing provider and price)
- [x] `feat:` send-message view: saves messages, streams via `StreamingHttpResponse`, finalises and charges on completion
- [x] `feat:` chat page renders the stream token by token (HTMX SSE extension or minimal fetch)
- [x] `feat:` show reasoning collapsed under the reply
- [x] `feat:` "insufficient balance" and provider error states in the UI
- [x] `test:` view tests with a fake adapter (success, insufficient balance, mid-stream failure)
- [x] `test:` one manual end-to-end smoke test against the real proxy (recorded in the wiki, not in CI)

## M6: History and billing views (`feat/history`)
- [x] `feat:` conversation history sidebar with rename and delete
- [x] `feat:` balance in the header (~~demo "add credits" button~~ dropped: user chose to keep it simple)
- [x] `feat:` usage/ledger page with per-message cost
- [x] `test:` ownership tests (users can't see each other's data)

## M7: Polish (`feat/polish`)
- [x] `feat:` auto-title conversations from the first message (done in M5)
- [x] `feat:` empty, error and loading states
- [x] `chore:` double-submit guard (server-side 409)
- [x] `docs:` README setup and run instructions, wiki sync (architecture, data model, decisions)
- [x] `docs:` export session transcripts to `doc/transcripts/` via `scripts/export_transcripts.sh` (redacted; re-run at the end of every session)

## Out of scope (deferred; needs a new study)
Uploads, web search, real payments, deployment.

## Deviations
- No top-up button (user: keep it simple). Welcome grant + admin adjustments only.
- Auto-title landed in M5.
- Smoke test found and fixed the `max_completion_tokens` bug (see `doc/wiki/decisions.md`).
- The `chat UI` and `history` UI have not been exercised in a real browser.
