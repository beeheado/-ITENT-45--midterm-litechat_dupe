# Data model

Money is stored as **integer micro-credits** (1 credit = $1 = 1,000,000). Prices are micro-credits per million tokens. `ledger.cost_for` rounds up.

| Model | Key fields | Notes |
|---|---|---|
| `User` | Django auth | |
| `Wallet` | `user` 1:1, `balance_micros` | DB `CHECK balance >= 0`. Cache of the ledger. |
| `LedgerEntry` | `wallet`, `kind` (grant/topup/charge/adjustment), signed `amount_micros`, `balance_after_micros`, `message` (SET_NULL), `note` | Append-only; read-only in admin. Survives conversation deletion. |
| `LLMModel` | `provider`, `model_id`, `display_name`, `input/output_price_micros_per_mtok`, `max_output_tokens`, `is_active` | Seeded by migration 0002; edit in admin. |
| `Conversation` | `user`, `title`, `model` (last used) | Title auto-set from the first message; renameable. |
| `Message` | `role`, `content`, `reasoning`, `model`, `input_tokens`, `output_tokens`, `cost_micros`, `status` (pending/complete/failed/cancelled), `error` | `cost_micros` is a snapshot: later price edits never change history. |

## Invariants (tested in `core/test_ledger.py`)
- Sum of a wallet's ledger amounts == `balance_micros`.
- Balance never goes negative. Overdrafts are clamped and noted in the ledger row; the message keeps its true cost.
- A message's finalisation and its charge commit or roll back together.
