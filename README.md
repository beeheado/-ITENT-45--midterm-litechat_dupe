# Darkchat

A Django clone of the core of [Litechat](https://litechat.ai): chat with several LLMs and pay only for what you use, from a prepaid balance. Built for ITENT 45 with an agentic workflow (see `CLAUDE.md`, `doc/`).

## Run it locally
    python3.11 -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env          # fill in the three proxy keys
    python manage.py migrate      # also seeds the three models and prices
    python manage.py createsuperuser
    python manage.py runserver    # http://127.0.0.1:8000

Tests: `pytest` (no network; provider streams are replayed from `fixtures/proxy/`).

## Using it
- Sign up: every new account gets a $1.00 welcome credit.
- Pick a model per message. Each reply shows its token counts and exact cost, and the balance in the header updates live.
- `/usage/` shows the full ledger. Admins can edit prices at `/admin/`, and grant $1 / $5 / $10 to selected wallets with the *Wallet* list's action menu. Grants go through the ledger (balances are never edited directly).

## Layout
- `core/providers/`: one adapter per provider, normalising streams to `TextDelta / ReasoningDelta / Usage / Done / Error`
- `core/ledger.py`: cost math, balance check, atomic charging
- `core/views.py`, `templates/`: chat UI (Django templates + a small streaming `fetch` reader)
- `doc/study`, `doc/plan`, `doc/wiki`: the study -> plan -> execute -> sync workflow record
- `scripts/capture_proxy.py`: re-capture real proxy responses into `fixtures/proxy/`

## How this was built
Built with Claude Code under a study -> plan -> execute -> rendezvous -> sync-docs loop, scoped to conventional commits. Start at [`doc/README.md`](doc/README.md) for the index: studies, plans, living wiki, the retrospective, the session transcripts, and the real API captures in `fixtures/proxy/`.
