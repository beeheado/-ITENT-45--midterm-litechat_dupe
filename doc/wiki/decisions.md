# Decisions log

Tactical decisions made by the agent. Strategic ones are made by the user.

## 2026-09-29
- **Python 3.11 (Homebrew) for the venv.** System Python is 3.9.6, too old for Django 5.x. Homebrew 3.11 is clean and supported by Django 5.2 LTS. Anaconda's 3.13 was available but avoided to keep the environment reproducible. No `uv`.
- **Django 5.2 LTS**, pinned in `requirements.txt` via `pip freeze`.
- **python-dotenv** to load `.env` (lighter than django-environ).
- **httpx** for proxy calls (sync + async streaming) and the capture script.
- **pytest + pytest-django** for tests.
- **`.claude/` gitignored.** It holds local session state.
- **`CLAUDE.md` replaces `AGENTS.md`.** Claude Code loads it automatically.
- **Capture script in `scripts/`** is tooling and not part of the app. It writes redacted fixtures.

## Execution of plan 001 (2026-09-29)
- **Answers from the user:** placeholder prices OK; uploads, web search and real payments out of scope; reasoning shown collapsed; local hosting only; "keep it simple" on credits, so **no top-up button**: new accounts get a $1.00 grant and admins can add ledger entries. (Plan M6's top-up button dropped.)
- **`django-htmx` not added.** The streaming UI uses a ~50-line `fetch` reader, and HTMX is loaded from CDN only for future use. Fewer dependencies.
- **Streaming wire format to the browser is NDJSON**, not SSE. Simpler to parse with `fetch`, and POST with CSRF just works (`EventSource` is GET-only).
- **Provider adapters emit a single `Usage` event** just before `Done`, hiding the per-provider timing differences.
- **Charge only from provider-reported usage.** No usage => message saved, user not billed. Cancelled streams are not billed (usage unknown).
- **Reserve check** uses a pessimistic chars/3 input estimate plus `max_output_tokens`. It only gates the request, never sets a price.
- **Auto-title** from the first message was implemented in M5 instead of M7.
- **One in-flight reply per conversation** (409), with a 3-minute staleness window so a crashed request can't lock a chat.
- **Bug found only by live smoke test:** the proxy rejects `max_completion_tokens` on the OpenAI interface, so we send `max_tokens`. Captured as `fixtures/proxy/openai/error_unsupported_param.json`. Lesson: fixtures replay proves parsing, not that requests are accepted, so keep a live smoke step.
- **Not verified in a browser.** The inline JS was syntax-checked with Node and the server side was exercised over HTTP, but no browser-based UI test has been run.

## Plan 002 (2026-09-29)
- **Admin credit grants are actions, not editable fields.** "Grant $1/$5/$10" on the Wallet list calls `ledger.credit(kind="topup")`, so the ledger invariant holds. Wallet add is disabled. This fixes a wrong claim the README made after plan 001.
- **No web fonts, no CSS framework, no new dependencies.** System font stack, CSS variables, `color-mix` for the translucent header.
- **Theme follows the OS** (`prefers-color-scheme`); dark is the default. No manual toggle (kept simple).
- **Thinking indicator is class-driven** (`.body.thinking`) and removed by JS on the first token or on completion. An earlier `:empty` selector was dropped because JS inserts an empty text node.
- **Phone composer bug** found by screenshot: the model `<select>` pushed Send off-screen. Fixed with `width:0; flex:1 1 0`. Lesson: check layouts at a real narrow viewport (an iframe), not a cropped desktop render.
- **Balance pill now links to `/usage/`.**
- **Markdown rendering deferred.** It needs a sanitiser or a dependency and deserves its own study.
