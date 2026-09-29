#!/usr/bin/env bash
# Copy Claude Code session transcripts into doc/transcripts/ with proxy keys and personal emails redacted:
#   <session>.jsonl  raw log (complete, machine-readable)
#   <session>.md     readable rendering (conversation + one-line tool calls)
# The raw logs can contain API keys (pasted prompts, .env writes) and the user's email (harness context),
# so never copy them by hand.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$HOME/.claude/projects/-Users-luismariano-Downloads-darkchat"
DEST="$ROOT/doc/transcripts"
PY="$ROOT/.venv/bin/python"; [ -x "$PY" ] || PY=python3
mkdir -p "$DEST"
for f in "$SRC"/*.jsonl; do
  id="$(basename "$f" .jsonl)"
  "$PY" "$ROOT/scripts/redact.py" < "$f" > "$DEST/$id.jsonl"
  "$PY" "$ROOT/scripts/render_transcript.py" "$DEST/$id.jsonl" "$DEST/$id.md"
done
for f in "$DEST"/*.jsonl "$DEST"/*.md; do
  "$PY" "$ROOT/scripts/redact.py" < "$f" | cmp -s - "$f" || { echo "ABORT: sensitive strings remain in $f" >&2; exit 1; }
done
echo "Exported $(ls "$DEST"/*.jsonl | wc -l | tr -d ' ') transcript(s) to $DEST (keys and emails redacted)"
