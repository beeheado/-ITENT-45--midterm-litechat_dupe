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
- **Bug: the site was served unstyled** (`/static/style.css` 404) because the root `static/` dir was not in `STATICFILES_DIRS`. It existed since plan 001 and passed every test and my screenshots (which loaded the CSS by `file://` path). Found by curl-ing the running server's static URL during plan 002's live smoke test. Fixed in `fix/static-files`; guarded by `test_stylesheet_is_discoverable_by_staticfiles`. Lesson: verify assets through the real server, not the filesystem.

## Plan 003: replies that showed only "Reasoning" (2026-09-29)
- **Bug (found by the user in their browser):** the answer bubble was blank and only the Reasoning toggle worked. Root cause: the proxy's models think before answering and thinking counts against `max_tokens`; the seeded budget was 1024, so a real question spent it all reasoning (`output_tokens = 1024`, `content = ""`, status `complete`). The app discarded the provider's finish reason and never told the user.
- **Reproduced with real data first:** with a 30-token budget all three providers returned reasoning only. Finish strings: OpenAI `length`, Anthropic `max_tokens`, Gemini `MAX_TOKENS`; usage is still reported. Saved as `fixtures/proxy/*/stream_truncated.txt` (`scripts/capture_proxy.py stream_truncated`).
- **Measured what budget is needed** (real proxy, OpenAI interface): "17 * 23" 32 tokens; a short poem 246; "explain X in detail" more than 8192 (about 6000 of reasoning). Gemini and Claude answered the detailed question in 3.7k and 7.5k tokens.
- **Budget raised to 8192** (migration 0004, admin-editable). Live check with the hard prompt: all three gave full answers of 12k to 13.5k characters. Cost of one such question at the placeholder prices: about $0.038 (Claude), $0.010 (Gemini, GPT); conversation history makes later messages dearer.
- **Reasoning controls probed and NOT adopted.** Anthropic `thinking: {"type":"disabled"}` and Gemini `thinkingConfig.thinkingBudget: 0` work and give full answers with no reasoning. OpenAI `reasoning_effort` is accepted but ignored (2000 of 2000 tokens still spent thinking). Adopting it for two of three providers would make the models behave inconsistently, so it is a candidate for a future study, not this fix.
- **Billing policy (user's decision): no visible answer means $0.** Status becomes `failed` with a clear notice; tokens are still recorded on the message. A partial answer cut off at the limit is kept, billed, and annotated. Implemented in `ledger.finalize_message`. This keeps the earlier rule "the user is never billed for nothing".
- **Reserve check capped at 2048 output tokens** (`ledger.RESERVE_OUTPUT_TOKENS`). Without the cap, the bigger budget would make a user with under about $0.05 unable to send even a one-line question. Overshoot beyond the reserve is still clamped at a zero balance.
- **`Message.finish_reason` and `Message.notice`.** The notice is derived, so replies saved blank before this fix also render an explanation instead of an empty bubble. Those old blank replies were already charged and are not refunded automatically.
- **Why my smoke test missed it:** it used five-word prompts, so reasoning stayed tiny. Smoke prompts now must include one that needs real thinking.
- **Process mistake, disclosed:** while running smoke tests I deleted the user's local `db.sqlite3` (their test account and chats) with `rm -f`. It is gitignored dev data, but I should have used a separate database. Smoke tests must not touch the user's database.
