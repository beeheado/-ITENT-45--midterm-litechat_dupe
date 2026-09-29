# Plan 001: Architecture to working MVP

Timestamp: 2026-09-29T22:20:00-07:00 (approximate)
Based on: `doc/study/001-architecture-study.md`
Status: **awaiting user approval. Do not execute yet.**

Each task is one conventional commit on its own `feat/<slug>` branch (one branch per milestone). Each milestone ends with a rendezvous (`pytest`, `manage.py check`, smoke test, `--no-ff` merge to `main`) and a `docs:` wiki sync.

New dependencies to approve: `django-htmx` (optional, helpers only). Everything else is already installed.

## M1: Scaffold (`feat/scaffold`)
- [ ] `chore:` create Django project `darkchat` and app `core` (`django-admin startproject`, `startapp`)
- [ ] `chore:` load settings from `.env` via python-dotenv (secret key, debug, proxy URL and keys); fail loudly when missing
- [ ] `chore:` configure pytest-django (`pytest.ini`, `conftest.py`)
- [ ] `feat:` base template with HTMX via CDN and minimal CSS
- [ ] `feat:` signup, login, logout views and templates (Django auth)
- [ ] `test:` auth flow tests

## M2: Models and admin (`feat/models`)
- [ ] `feat:` `LLMModel` model with per-million-token prices
- [ ] `feat:` `Wallet` and `LedgerEntry` models (integer micro-credits, `CHECK balance >= 0`)
- [ ] `feat:` `Conversation` and `Message` models
- [ ] `feat:` data migration seeding the three proxy models and placeholder prices
- [ ] `feat:` register all models in admin (ledger read-only)
- [ ] `feat:` create a wallet with a starting grant on signup (signal or service)
- [ ] `test:` model constraint tests

## M3: Provider adapters (`feat/adapters`)
- [ ] `feat:` internal types (`ChatRequest`, `StreamEvent` variants) and the `ProviderAdapter` base
- [ ] `test:` fixture loader helper that replays `fixtures/proxy/*/stream.txt`
- [ ] `feat:` OpenAI adapter (request body, SSE parser, usage chunk, reasoning vs content)
- [ ] `feat:` Anthropic adapter (event parser, usage from `message_start` + `message_delta`)
- [ ] `feat:` Google adapter (role mapping, `parts`, `usageMetadata`)
- [ ] `feat:` error mapping (401/400/429/5xx to `Error` events)
- [ ] `chore:` re-capture Google bad-model fixture and the missing error cases
- [ ] `test:` adapter tests replaying every fixture, with no network

## M4: Metering and ledger (`feat/ledger`)
- [ ] `feat:` `cost_for(model, input, output)` in integer math
- [ ] `feat:` `credit(wallet, amount, kind, note)` service: atomic, locks the wallet, writes ledger and balance together
- [ ] `feat:` `charge_message(message, usage)` service
- [ ] `feat:` pre-flight balance/reserve check
- [ ] `feat:` failure policy (charge only when usage is known; otherwise mark failed)
- [ ] `test:` ledger invariants (sum of entries equals balance, never negative, atomic rollback)

## M5: Chat UI and streaming (`feat/chat`)
- [ ] `feat:` conversation list + new-conversation page
- [ ] `feat:` model picker (active `LLMModel`s, showing provider and price)
- [ ] `feat:` send-message view: saves messages, streams via `StreamingHttpResponse`, finalises and charges on completion
- [ ] `feat:` chat page renders the stream token by token (HTMX SSE extension or minimal fetch)
- [ ] `feat:` show reasoning collapsed under the reply (pending user answer)
- [ ] `feat:` "insufficient balance" and provider error states in the UI
- [ ] `test:` view tests with a fake adapter (success, insufficient balance, mid-stream failure)
- [ ] `test:` one manual end-to-end smoke test against the real proxy (recorded in the wiki, not in CI)

## M6: History and billing views (`feat/history`)
- [ ] `feat:` conversation history sidebar with rename and delete
- [ ] `feat:` balance in the header, demo "add credits" button (creates a `topup` entry)
- [ ] `feat:` usage/ledger page with per-message cost
- [ ] `test:` ownership tests (users can't see each other's data)

## M7: Polish (`feat/polish`)
- [ ] `feat:` auto-title conversations from the first message
- [ ] `feat:` empty, error and loading states
- [ ] `chore:` rate-limit / double-submit guard
- [ ] `docs:` README setup and run instructions, wiki sync (architecture, data model, decisions)
- [ ] `docs:` export session transcripts to `doc/transcripts/`

## Out of scope (deferred; needs a new study)
Uploads, web search, real payments, deployment.
