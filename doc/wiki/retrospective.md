# Retrospective

Written 2026-09-29, after plans 001 and 002. Facts here come from the repo history and the session transcript; where something is a judgement, it says so.

## What was built
Darkchat: a Django app where a user signs up, gets a $1.00 credit, chats with three models (through the course proxy), sees the exact token count and cost of every reply, and can review a full ledger. Streaming replies, conversation history with rename/delete, admin credit grants, light/dark responsive UI. 67 tests at the time of writing, none of which touch the network.

## How the loop actually ran
| Step | Plan 001 | Plan 002 |
|---|---|---|
| Study | `doc/study/001` (architecture, proxy findings, schema, open questions) | `doc/study/002` (admin grants, visual principles) |
| Plan | `doc/plan/001`: 7 milestones, 43 tasks | `doc/plan/002`: 3 milestones |
| Execute | one `feat/*` branch per milestone, one conventional commit per task | one branch plus a `fix/*` branch |
| Rendezvous | `check` + tests + live smoke against the real proxy, then `merge --no-ff` | same, plus screenshots |
| Sync docs | wiki updated at the end of each plan | same |

Every non-merge commit subject follows the conventional-commit format (checked mechanically at the end).

## Who decided what
**Human (strategic):** Django instead of Next.js; `CLAUDE.md` instead of `AGENTS.md`; shorter loop; answers to the study's open questions (placeholder prices fine, uploads/web search/payments out of scope, reasoning shown collapsed, local hosting only, no top-up button); the go-ahead for each plan; the visual-refresh request.
**Agent (tactical), all logged in `decisions.md`:** provider adapter design, integer micro-credit ledger, charge-only-from-reported-usage policy, NDJSON to the browser instead of SSE, test strategy, CSS approach.

## Where the process bent (honest notes)
- The workflow says to stop for approval after each plan. For plan 001 the human replied "proceed... you have approval for anything you need", so execution ran straight through. For plan 002 the human said to start it "if needed and ready", and the agent read that as approval, writing study, plan and code in one go. Both were reasonable readings, but the gate was effectively waived, not exercised.
- The agent switched models mid-session (planning on one, executing on another); nothing in the repo depends on that.
- Commit authorship is the machine's auto-generated identity, so GitHub does not link commits to an account. Left as is rather than rewriting pushed history.

## Bugs, and what caught them
1. **The proxy rejects `max_completion_tokens`** (OpenAI interface). Fixture-replay tests passed because fixtures only prove *parsing*. A live smoke run against the real proxy exposed it. Now captured as a fixture with a regression test.
2. **The site served no CSS** (`/static/style.css` returned 404: root `static/` was not in `STATICFILES_DIRS`). Present since plan 001, invisible to every test, and invisible in screenshots that loaded the CSS by file path. Found by requesting the stylesheet from the running server. Now guarded by a test.
3. **The README claimed admins could grant credits; the app could not do it.** Found by re-reading the code against the docs after plan 001. Became plan 002.
4. **Tests that could not fail:** two ledger tests had a bare `assert_ledger_consistent(w) and balance == 0` expression, so the balance was never asserted. Found by re-reading the tests; fixed.
5. **Phone layout hid the Send button** (model dropdown overflowed the composer). Found only after rendering at a real narrow viewport (a first attempt at a "phone" screenshot was silently a cropped desktop render and was discarded).

**Pattern:** each serious bug lived in the gap between "the tests pass" and "the real thing works". The steps that closed the gap were cheap: run the real proxy once, request the real static URL, look at the real pixels.

## Exogenous inputs
The proxy exposes three native API dialects, not one. Real captures (models, completions, SSE streams, four kinds of errors) are in `fixtures/proxy/`, reproducible with `scripts/capture_proxy.py`, described in `proxy-api.md`, and replayed by the adapter tests. Notable findings: usage arrives at a different point in each stream; reasoning tokens are billed as output; a trivial prompt reports about 208 input tokens (hidden overhead); the proxy publishes no prices; all three "providers" are the same underlying model.

## Handling the API keys
The keys were pasted into the very first prompt, so they exist in the raw session log. `.env` is untracked; `scripts/export_transcripts.sh` redacts keys before anything is copied into the repo and aborts if any key-like string remains; the pushed history was checked and contains none. The keys themselves were shared in plain text in a chat, so treat them as exposed to that chat and ask the instructor for replacements if that matters.

## Not verified / known limits
- The streaming chat page has not been driven in an interactive browser by the agent (only its JavaScript syntax-checked, the server side exercised over HTTP, and static renders screenshotted). The human should click through once.
- Low-balance behaviour is tested at the view level, not by eye.
- Model choice is cosmetic at the answer level (one backend model), and prices are invented placeholders.
- Single-worker dev server; SQLite; no deployment. Streaming under WSGI pins a worker per active stream.

## Deferred (would need a new study)
Markdown rendering of replies, a Stop button, file uploads, web search, real payments, loading the model list from the proxy, deployment (ASGI + Postgres).
