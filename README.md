# Darkchat

A Django clone of the core functionality of [Litechat](https://litechat.ai): metered, a la carte access to LLMs from several providers.

Status: workflow scaffolding and architecture study. See `CLAUDE.md` for the workflow and `doc/` for studies, plans and the wiki.

## Setup
    python3.11 -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env   # then fill in the proxy keys
