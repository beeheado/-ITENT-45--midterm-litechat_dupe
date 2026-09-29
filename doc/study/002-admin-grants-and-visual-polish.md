# Study 002: Admin credit grants and visual polish

Timestamp: 2026-09-29T23:30:00-07:00 (approximate)
Status: approved by the user ("start plan 002 ... improve the visuals without compromising usability")

## 1. Goal
1. Close a real gap found after plan 001: the README claims admins can grant credits, but the Wallet balance is read-only and ledger entries can't be added in admin, so nobody can top up a user.
2. Improve the look of the site without hurting usability.

## 2. Credit grants: options
| Option | Pros | Cons |
|---|---|---|
| Make `balance_micros` editable in admin | Trivial | Breaks the ledger invariant (balance != sum of entries). Rejected. |
| Allow adding `LedgerEntry` rows in admin | Uses the ledger | Admin form can't compute `balance_after` or lock the wallet. Rejected. |
| **Admin actions on Wallet: "Grant $1 / $5 / $10"** calling `ledger.credit(kind="topup")` | Reuses the atomic, tested path; no new UI; invariant preserved | Fixed amounts only (fine for a demo) |

**Decision:** admin actions. Note in the ledger row who granted it.

## 3. Visual polish: principles (usability first)
- Keep every existing control and flow; change presentation, not behaviour.
- Contrast: text and controls meet WCAG AA (4.5:1 body text). Visible keyboard focus rings on every control.
- Respect `prefers-color-scheme` (dark default, light supported) and `prefers-reduced-motion`.
- Responsive: the sidebar collapses above the chat on narrow screens, and the composer stays reachable.
- Feedback: a visible "thinking" state between Send and the first token (today the bubble is just empty), a copy button on replies, disabled/busy button state.
- No new dependencies, no build step, no external fonts (system font stack), so the app still works offline apart from HTMX's CDN tag.
- Not doing: markdown rendering (needs a sanitiser or a dependency and is a separate study), web fonts, animations beyond a subtle typing indicator.

## 4. Verification approach
There is no browser test harness, so: render each page through the Django test client to static HTML and screenshot it with headless Chrome at desktop and phone widths, in dark and light. Node syntax-check the inline JS. Existing tests must stay green.

## 5. Risks
- CSS/JS changes can't be exercised in a real interactive session by the agent. The user should click through once after merge.
- Whether to build it: yes, both are small and low risk.
