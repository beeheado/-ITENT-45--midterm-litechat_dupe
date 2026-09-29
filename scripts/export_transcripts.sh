#!/usr/bin/env bash
# Copy Claude Code session transcripts into doc/transcripts/ with proxy keys redacted.
# The raw .jsonl files can contain API keys (pasted prompts, .env writes), so never copy them by hand.
set -euo pipefail
SRC="$HOME/.claude/projects/-Users-luismariano-Downloads-darkchat"
DEST="$(cd "$(dirname "$0")/.." && pwd)/doc/transcripts"
mkdir -p "$DEST"
for f in "$SRC"/*.jsonl; do
  sed -E 's/lp_[A-Za-z0-9_-]{20,}/lp_REDACTED/g' "$f" > "$DEST/$(basename "$f")"
done
if grep -rEq 'lp_[A-Za-z0-9_-]{20,}' "$DEST"; then
  echo "ABORT: key-like strings remain in $DEST" >&2; exit 1
fi
echo "Exported $(ls "$DEST"/*.jsonl | wc -l | tr -d ' ') transcript(s) to $DEST (keys redacted)"
