"""Redaction shared by the transcript tools: proxy API keys and personal email addresses.

Usage as a filter:  python scripts/redact.py < in > out
Exit status 1 (and a message on stderr) if anything sensitive is still present after redaction.
"""
import re
import sys
from pathlib import Path

KEY = re.compile(r"lp_[A-Za-z0-9_-]{20,}")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
# Addresses that are not personal: commit-trailer and placeholder addresses, and GitHub's privacy-preserving noreply.
SAFE_DOMAINS = ("anthropic.com", "users.noreply.github.com", "example.com")


def _extras():
    """Extra strings to scrub, one per line, from the git-ignored `.redact_extra` (e.g. the local part of your email)."""
    f = Path(__file__).resolve().parent.parent / ".redact_extra"
    return [ln.strip() for ln in f.read_text().splitlines() if ln.strip()] if f.exists() else []


def _email(m):
    return m.group(0) if m.group(0).lower().endswith(SAFE_DOMAINS) else "[email redacted]"


def redact(text: str) -> str:
    text = EMAIL.sub(_email, KEY.sub("lp_REDACTED", text))
    for extra in _extras():
        text = text.replace(extra, "[redacted]")
    return text


def leaks(text: str) -> list:
    found = KEY.findall(text)
    found += [e for e in EMAIL.findall(text) if not e.lower().endswith(SAFE_DOMAINS)]
    found += [x for x in _extras() if x in text]
    return found


if __name__ == "__main__":
    out = redact(sys.stdin.read())
    if leaks(out):
        sys.exit("ABORT: sensitive strings remain after redaction")
    sys.stdout.write(out)
