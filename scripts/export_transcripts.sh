#!/usr/bin/env bash
# Copy Claude Code session transcripts into doc/transcripts/ with proxy keys redacted:
#   <session>.jsonl  raw log (complete, machine-readable)
#   <session>.md     readable rendering (conversation + one-line tool calls)
# The raw logs can contain API keys (pasted prompts, .env writes), so never copy them by hand.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$HOME/.claude/projects/-Users-luismariano-Downloads-darkchat"
DEST="$ROOT/doc/transcripts"
PY="$ROOT/.venv/bin/python"; [ -x "$PY" ] || PY=python3
mkdir -p "$DEST"
for f in "$SRC"/*.jsonl; do
  id="$(basename "$f" .jsonl)"
  sed -E 's/lp_[A-Za-z0-9_-]{20,}/lp_REDACTED/g' "$f" > "$DEST/$id.jsonl"
  "$PY" "$ROOT/scripts/render_transcript.py" "$DEST/$id.jsonl" "$DEST/$id.md"
done
if grep -rEq 'lp_[A-Za-z0-9_-]{20,}' "$DEST"; then
  echo "ABORT: key-like strings remain in $DEST" >&2; exit 1
fi
echo "Exported $(ls "$DEST"/*.jsonl | wc -l | tr -d ' ') transcript(s) to $DEST (keys redacted)"
