# Darkchat

Darkchat is a clone of the core functionality of Litechat (https://litechat.ai): metered, a la carte access to LLMs from several providers, paid for from a prepaid balance.
Stack: Python 3.11 + Django 5.2, Django templates + HTMX, SQLite, pytest. All LLM traffic goes through the course proxy (`LITECHAT_PROXY_URL`).
I (the user) make strategic decisions; you make tactical ones. Log tactical decisions in `doc/wiki/decisions.md`.

## Commands
Fill these in as they come to exist.
- Activate venv: `source .venv/bin/activate` (or call `.venv/bin/python` directly)
- Install deps: `pip install -r requirements.txt` (re-freeze after adding one)
- Run server: `python manage.py runserver`
- Tests: `pytest`
- Checks: `python manage.py check`
- Migrations: `python manage.py makemigrations && python manage.py migrate`
- Proxy capture script: `python scripts/capture_proxy.py` (to be created in study 001)

## Workflow loop
Every new outcome goes through: **study -> plan -> execute -> rendezvous -> sync docs**.

1. **Study**: write `doc/study/NNN-<slug>.md`. Start with an ISO 8601 timestamp. Cover the goal, options, tradeoffs, a recommendation, and whether to build it at all.
   - Lightweight mode: a small or obvious change (bug fix, copy tweak, under ~50 LOC) may skip the study and note its rationale in the plan.
2. **Plan**: write `doc/plan/NNN-<slug>.md` with an ISO 8601 timestamp and a checklist of `- [ ]` tasks, each sized for one conventional commit. Tick items off as you finish them.
   - Stop and wait for my approval after writing a plan, unless I have said "proceed" for that plan.
3. **Execute**: work on a branch (`feat/<slug>`, `fix/<slug>`, ...).
   - One conventional commit per logical change: `feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`.
   - Write tests alongside the code.
   - Never commit secrets.
4. **Rendezvous**: before merging, run `pytest` and `python manage.py check`, and smoke-test the feature in the running server. Report results honestly, including failures. Then merge into `main` with `--no-ff`.
5. **Sync docs**: update `doc/wiki/` (architecture, data model, proxy API, decisions) to match the code. Commit with `docs:`.

## Exogenous inputs
The proxy API, provider response formats and any binary assets are external contracts.
- Capture real samples before writing parsers: streaming and non-streaming responses, usage fields, errors, model lists.
- Save captures to `fixtures/proxy/<provider>/<case>.json` (raw SSE as `.txt`) with keys redacted.
- Describe each capture's shape in `doc/wiki/proxy-api.md`.
- Tests replay these fixtures. Tests must never call the real proxy.

## Guardrails
- Secrets live in `.env` (gitignored). Never print, log, echo or commit key values.
- Stay within the stack. Note any new dependency in the plan first.
- Ask me before strategic changes: scope, schema redesign, new framework.
- Store money as integer micro-units, never floats.
- Transcripts of sessions go in `doc/transcripts/` (copy from `~/.claude/projects/-Users-luismariano-Downloads-darkchat/`).
