# Project documentation index

Suggested reading order for someone opening this repo cold:

1. **`../CLAUDE.md`**: the operating rules the agent followed (study -> plan -> execute -> rendezvous -> sync docs).
2. **`prompts/000-assignment-and-kickoff.md`**: the assignment and the first prompt.
3. **`study/`**: why: options, tradeoffs, decisions. `001` architecture, `002` admin grants + visual polish.
4. **`plan/`**: what: timestamped checklists derived from the studies (all ticked).
5. **`wiki/`**: the living docs, kept in sync with the code:
   - `architecture.md`, `data-model.md`
   - `proxy-api.md`: the external API's real shape, from captured data
   - `decisions.md`: tactical decisions and lessons, in order
   - `retrospective.md`: what happened, including the bugs and where the process bent
6. **`transcripts/`**: the coding sessions. `<id>.md` is readable; `<id>.jsonl` is the complete raw log. Both have API keys redacted.
7. **`../fixtures/proxy/`**: real responses captured from the proxy (the "exogenous inputs").

Regenerate transcripts with `scripts/export_transcripts.sh` (never copy the raw logs by hand: they contain keys).
