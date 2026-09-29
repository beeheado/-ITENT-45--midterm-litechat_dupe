"""Build the single downloadable submission transcript (with a header) from the redacted readable export.

Usage: python scripts/package_transcript.py [output.md]     (default: ~/Downloads/darkchat-session-transcript.md)
Run scripts/export_transcripts.sh first. Refuses to write if a key or personal email is still present.
"""
import glob
import re
import sys
from pathlib import Path

from redact import leaks

ROOT = Path(__file__).resolve().parent.parent
REPO = "https://github.com/beeheado/-ITENT-45--midterm-litechat_dupe"

src = sorted(glob.glob(str(ROOT / "doc" / "transcripts" / "*.md")))[-1]
body = Path(src).read_text(encoding="utf-8")
stamps = re.findall(r"^### (?:USER|CLAUDE) · (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) UTC", body, re.M)
typed = decisions = agent = 0
for block in re.split(r"\n---\n", body):
    m = re.match(r"\s*### (USER|CLAUDE)", block)
    if not m:
        continue
    if m.group(1) == "CLAUDE":
        agent += 1
    elif block.split("\n", 3)[-1].strip().startswith("> **User"):
        decisions += 1
    else:
        typed += 1

jsonl = Path(src).with_suffix(".jsonl").name
header = f"""# ITENT 45 Midterm: Darkchat coding session transcript

| | |
|---|---|
| **Project** | Darkchat, a Django clone of Litechat (metered, a la carte LLM access) |
| **Repository** | {REPO} |
| **Harness** | Claude Code (single continuous session) |
| **Session span** | {stamps[0]} to {stamps[-1]} UTC |
| **Turns** | {typed} messages typed by the user, {agent} agent replies, {decisions} recorded decisions (plan approvals and answers to questions) |

## Reading guide
- Each `### USER` block is what the human typed; each `### CLAUDE` block is the agent's reply. Lines starting with `> tool:` are the agent's tool calls, one line each (command, file or purpose).
- Lines starting with `> **User decision:**` / `> **User answered:**` mark where the human approved a plan or made a product decision.
- Omitted here to keep it readable: raw tool output, hidden reasoning and the harness's internal reminders. The complete machine-readable log is in the repository at `doc/transcripts/{jsonl}`.
- The proxy API keys the assignment supplied were pasted in the first prompt, and the user's email appears in harness context. Both are redacted in this file and in the repository.
- The transcript ends at the moment it was generated, so the final steps of the request that produced it (packaging, committing, pushing) are not part of it.

The workflow followed is in `CLAUDE.md` (study, plan, execute, rendezvous, sync docs). The studies, plans, wiki and retrospective are under `doc/`; a good starting point is `doc/README.md`.

"""
if body.startswith("# Session transcript (readable)"):
    body = body.split("\n", 4)[4]
out = header + "\n" + body.lstrip("\n")
if leaks(out):
    sys.exit("ABORT: sensitive strings remain in the packaged transcript")
dest = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "Downloads" / "darkchat-session-transcript.md"
dest.write_text(out, encoding="utf-8")
print(f"wrote {dest} ({len(out.splitlines())} lines; {typed} typed, {agent} agent, {decisions} decisions)")
