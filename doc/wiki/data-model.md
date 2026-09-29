# Data model

Money is stored as **integer micro-credits** (1 credit = $1 = 1,000,000). Prices are micro-credits per million tokens. `ledger.cost_for` rounds up.

| Model | Key fields | Notes |
|---|---|---|
| `User` | Django auth | |
| `Wallet` | `user` 1:1, `balance_micros` | DB `CHECK balance >= 0`. Cache of the ledger. |
| `LedgerEntry` | `wallet`, `kind` (grant/topup/charge/adjustment), signed `amount_micros`, `balance_after_micros`, `message` (SET_NULL), `note` | Append-only; read-only in admin. Survives conversation deletion. |
| `LLMModel` | `provider`, `model_id`, `display_name`, `input/output_price_micros_per_mtok`, `max_output_tokens`, `is_active` | Seeded by migration 0002; edit in admin. `max_output_tokens` is 8192 (migration 0004): the models think first and thinking counts against it, so a small budget yields reasoning and no answer. |
| `Conversation` | `user`, `title`, `model` (last used) | Title auto-set from the first message; renameable. |
| `Message` | `role`, `content`, `reasoning`, `model`, `input_tokens`, `output_tokens`, `cost_micros`, `status` (pending/complete/failed/cancelled), `error`, `finish_reason` | `cost_micros` is a snapshot: later price edits never change history. `finish_reason` is the provider's stop reason (`stop`, `length`, ...). The derived `notice` property tells the user what went wrong, including for old blank rows. |

## Invariants (tested in `core/test_ledger.py`)
- Sum of a wallet's ledger amounts == `balance_micros`.
- Balance never goes negative. Overdrafts are clamped and noted in the ledger row; the message keeps its true cost.
- A message's finalisation and its charge commit or roll back together.
- **Billing policy** (`ledger.finalize_message`): charge only from provider-reported usage and only when the user got a visible answer. No usage, or no visible answer (e.g. the whole budget spent thinking): saved, marked failed, `cost_micros = 0`, tokens still recorded. A partial answer cut off at the limit is kept and billed.

## Account settings (plan 004)
| Model | Key fields | Notes |
|---|---|---|
| `UserProfile` | `user` 1:1, `system_prompt` (max 4000 chars, enforced by the form), `auto_memory` bool, `default_app` (simgen/ask/chat) | Created with the account by the post-save signal; `profile_for(user)` creates one on demand; migration 0007 backfilled existing users. |
| `MemoryItem` | `user`, `kind` (preference/fact/goal/context), `content` (max 500), `source` (user/ai), `created_at` | Max 50 per user. `source = "ai"` is reserved for future generated memories; nothing writes it yet. Newest first. |
Users with ledger history cannot be deleted (wallets are `PROTECT`ed by the append-only ledger); profiles and memories cascade with their user if that ever changes.
