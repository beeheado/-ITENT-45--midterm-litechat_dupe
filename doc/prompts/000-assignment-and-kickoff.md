# Assignment and kickoff prompt

The two inputs that started the project. API keys from the original text are removed; the real values live only in the untracked `.env`.

## 1. The assignment (ITENT 45 midterm)

> You are asked to replicate the core functionality of Litechat. Litechat is a web app that allows its users metered, *a la carte* access to LLMs from various providers. The intent of the platform is to allow regular users (i.e., not power users) access to powerful AI models, which would normally require an upfront investment in a subscription that regular users are unwilling to pay for.
> You can view the real Litechat app at https://litechat.ai. An API key for a set of LLMs is available at https://proxy.litechat.ai (three keys: OpenAI, Anthropic, Google).
>
> FAQ: *What is the core functionality of Litechat?* That is part of the test. *How will this be graded?* By how well you can convince me that you can drive an agentically-coded project.
>
> Deliverables. Minimally: the transcripts of your coding sessions, and the GitHub repository of your final codebase. Optionally: any other artifacts that contributed to your management of your project.

## 2. How the human adapted the course's sample workflow prompt
The course provided a template ("[INSERT PROJECT NAME] - Initial Agent Prompt") with the loop *study => plan => execute plan => rendezvous => sync docs*, conventional commits, and an emphasis on exogenous inputs. Changes requested:
- Python + Django instead of Next.js.
- `CLAUDE.md` instead of `AGENTS.md`, so the harness loads it automatically.
- A shorter loop (lightweight mode for small changes).
- Proxy keys go in `.env` and are never committed.

## 3. The kickoff prompt
Written from the template plus those changes and used as the first prompt of session 1. **This is a condensed copy**: the tech-stack constraints are verbatim, the numbered steps are summarised. The full original is in the session transcript (`doc/transcripts/`).

~~~text
# Darkchat: Initial Agent Prompt

You are an autonomous AI software engineer working in Claude Code. I make the strategic decisions and you make the tactical ones. I will stay behind the interface described below and will not collaborate on the implementation itself. Your job is to build Darkchat, a clone of the core functionality of Litechat (https://litechat.ai).

Litechat gives regular users (not power users) metered, a la carte access to LLMs from several providers, so they pay only for what they use and don't need a subscription. Part of your job is to work out what "core functionality" means. Study the real site and state your conclusions in the study doc.

## Tech stack and constraints
- Python + Django, not Next.js or any JS framework. Use Django's batteries (auth, ORM, admin, migrations, templates) to keep tactical decisions to a minimum.
- Frontend: Django templates with HTMX for interactivity and a minimal CSS approach. No JS build step. Use Server-Sent Events or StreamingHttpResponse for streaming model output.
- Database: SQLite for development.
- LLM access: only through the course proxy at https://proxy.litechat.ai. The URL and three keys (OpenAI, Anthropic, Google) are already in .env. Load them with django-environ or python-dotenv.
- Secrets: never print, log, echo, or commit the key values. .env must be in .gitignore before the first commit. Commit a .env.example that has placeholder values only.
- Python: system Python is 3.9.6, which is too old for current Django. Use Homebrew Python 3.12+ or uv, create a project venv (.venv/), and pin dependencies. Record the choice in the wiki.
- Tests: use pytest + pytest-django. Tests must never call the real proxy. They use recorded fixtures.

CRITICAL RULE: do not write application code in this session. This session only configures the workflow, initializes the repo, and completes the first study and plan.

1. Workspace initialization: git init on main; create doc/study, doc/plan, doc/wiki, doc/transcripts, fixtures/proxy; Django .gitignore (.env, .venv/, db.sqlite3, __pycache__/); .env.example and stub README; venv with Django; commit "chore: initialize repository and workflow scaffolding".
2. Encode the workflow in CLAUDE.md (under ~120 lines): project summary; commands; the loop study -> plan -> execute -> rendezvous -> sync docs (timestamped study and plan docs, checklist plans, stop for approval after a plan, feature branches, one conventional commit per logical change, tests with code, rendezvous = full tests + manage.py check + smoke test + merge --no-ff, sync doc/wiki); exogenous inputs (capture real provider samples with keys redacted into fixtures/proxy, describe them in doc/wiki/proxy-api.md, tests replay them); guardrails (stay in the stack, note new dependencies in the plan, ask before strategic changes, log tactical decisions in doc/wiki/decisions.md). Commit "docs: add CLAUDE.md workflow".
3. First study (study phase only): research Litechat's features and mark core vs nice-to-have; probe the proxy (auth, base paths, models, non-streaming and streaming completions, where usage appears, error responses), save redacted captures and summarise them in doc/wiki/proxy-api.md; write doc/study/001-architecture-study.md covering scope, Django fit (WSGI vs ASGI streaming, sync vs async, HTMX vs SPA, SQLite limits), a provider abstraction, a schema (User, Wallet in integer micro-credits, append-only LedgerEntry, LLMModel with per-token prices, Conversation, Message), atomic charging and failure handling, how demo credits are added, risks and open questions; read it back and write doc/plan/001-architecture-plan.md as a milestone checklist. Commit "docs: add architecture study, proxy captures, and plan".

Do not execute the plan. Stop after the plan is committed, summarise in five bullets or fewer (proxy findings, schema, open questions), and wait for my review.
~~~

