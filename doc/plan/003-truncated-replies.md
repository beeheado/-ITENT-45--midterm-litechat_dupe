# Plan 003: Replies that show only "Reasoning" (out-of-tokens fix)

Timestamp: 2026-09-29T23:55:00-07:00 (approximate)
Mode: lightweight (bug fix, no separate study). Rationale is in the checklist and in `doc/wiki/decisions.md`.
Status: executed on `fix/truncated-replies`

## Problem
User report: the chat showed only the collapsible Reasoning bubble, never the answer. The local DB showed assistant messages with `output_tokens = 1024` (the cap), empty `content`, 3k+ characters of `reasoning`, status `complete`. The proxy's models think before answering and thinking counts against `max_tokens`, so a real question could spend the whole budget on reasoning.

## Decisions
- Waive the charge when there is no visible answer (user's choice). Partial answers are still billed.
- Do not adopt reasoning controls: probed on the real proxy, Anthropic `thinking: disabled` and Gemini `thinkingBudget: 0` work, but OpenAI `reasoning_effort` is accepted and ignored. Applying it to two of three providers would make the models behave inconsistently.
- Budget 8192 (measured: a "detailed" question needs 8000+ tokens on the OpenAI interface; simple questions under 300). Reserve check capped at 2048 output tokens so users with a few cents can still ask short questions.

## Tasks
- [x] `chore:` capture real truncated streams for all three providers (`scripts/capture_proxy.py stream_truncated`, `fixtures/proxy/*/stream_truncated.txt`)
- [x] Probe reasoning controls and measure real token needs on the proxy (results in `doc/wiki/decisions.md`)
- [x] `feat:` `Message.finish_reason`, `is_truncated()`, `Message.notice`
- [x] `feat:` migrations: `finish_reason` field, seeded budget 1024 to 8192, new field default
- [x] `feat:` `finalize_message`: no visible answer means failed, $0, tokens recorded; partial answers billed with a "cut off" note
- [x] `feat:` reserve check capped at `RESERVE_OUTPUT_TOKENS = 2048`
- [x] `fix:` `_stream_reply` keeps the provider's finish reason; `done` event carries a `notice`
- [x] `fix:` chat page never renders an empty bubble; shows the notice (also for old blank rows)
- [x] `test:` truncated fixtures per adapter, billing policy, view behaviour, old-row rendering, seeded budget (80 tests; mutation-checked: disabling the free-if-empty rule fails 4 of them)
- [x] Live smoke with a hard prompt on all three models: full answers (12k to 13.5k chars)
- [ ] Live smoke of the out-of-tokens path with a forced low budget (see notes)
- [ ] `docs:` sync wiki, retrospective; final transcript export; push

## Notes
- The original smoke test used five-word prompts, so reasoning stayed tiny and the bug never showed. Smoke prompts must include one that needs real thinking.
- Existing replies that were already saved blank (and charged) before the fix are not refunded automatically. They now render a notice instead of a blank bubble.
