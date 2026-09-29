# Plan 002: Admin credit grants and visual polish

Timestamp: 2026-09-29T23:35:00-07:00 (approximate)
Based on: `doc/study/002-admin-grants-and-visual-polish.md`
Status: approved; executing on `feat/admin-grants-and-visuals`

No new dependencies.

## M1: Admin grants
- [ ] `feat:` admin actions on Wallet: grant $1 / $5 / $10 via `ledger.credit(kind="topup")`, note names the granting admin
- [ ] `test:` action credits the wallet, writes a ledger row, and keeps the ledger consistent; non-superusers cannot run it
- [ ] `docs:` correct the README claim to match

## M2: Visual refresh
- [ ] `feat:` design tokens (light and dark), type scale, spacing, focus rings in `static/style.css`
- [ ] `feat:` app shell: header, balance pill, responsive sidebar
- [ ] `feat:` auth pages as centred cards
- [ ] `feat:` chat bubbles (user right, assistant left), meta line, collapsed reasoning styling, empty state
- [ ] `feat:` "thinking" indicator until first token, copy button on replies, busy send button
- [ ] `feat:` polished usage table with summary cards
- [ ] `test:` markup regression tests (controls still present) and Node syntax check of inline JS
- [ ] `chore:` screenshots of every page (desktop + phone, dark + light) checked by eye, kept out of git

## M3: Sync
- [ ] `docs:` wiki decisions and architecture updated, plan ticked, transcripts re-exported
