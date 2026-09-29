# Plan 002: Admin credit grants and visual polish

Timestamp: 2026-09-29T23:35:00-07:00 (approximate)
Based on: `doc/study/002-admin-grants-and-visual-polish.md`
Status: executed on `feat/admin-grants-and-visuals`

No new dependencies.

## M1: Admin grants
- [x] `feat:` admin actions on Wallet: grant $1 / $5 / $10 via `ledger.credit(kind="topup")`, note names the granting admin
- [x] `test:` action credits the wallet, writes a ledger row, and keeps the ledger consistent; non-superusers cannot run it
- [x] `docs:` correct the README claim to match

## M2: Visual refresh
- [x] `feat:` design tokens (light and dark), type scale, spacing, focus rings in `static/style.css`
- [x] `feat:` app shell: header, balance pill, responsive sidebar
- [x] `feat:` auth pages as centred cards
- [x] `feat:` chat bubbles (user right, assistant left), meta line, collapsed reasoning styling, empty state
- [x] `feat:` "thinking" indicator until first token, copy button on replies, busy send button
- [x] `feat:` polished usage table with summary cards
- [x] `test:` markup regression tests (controls still present) and Node syntax check of inline JS
- [x] `chore:` screenshots of every page (desktop + phone, dark + light) checked by eye, kept out of git (found and fixed a phone composer overflow that hid the Send button)

## M3: Sync
- [x] `docs:` wiki decisions and architecture updated, plan ticked, transcripts re-exported

## Notes
- Visual checks used headless Chrome on pages rendered by the Django test client. Two pitfalls found along the way: headless Chrome ignores `preferredColorScheme` and has a minimum window width, so dark/light were produced by CSS copies and the phone view by a 390px iframe.
- Streaming behaviour (thinking dots disappearing on first token, copy button on a live reply) is covered by `node --check` and by reading the code, not by an interactive browser run. Please click through once.
