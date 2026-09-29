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
