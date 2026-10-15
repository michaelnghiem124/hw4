"""Append-only audit trail for agent-loop activity.

Every agent run writes a `run_start`, one `tool_call` per tool the model
invokes, and exactly one terminal `run_end` carrying a stop reason. Requests
that are refused before the model is ever reached (rate limit, oversized input,
bad session token) write a `request_rejected` instead, so the log also shows
what the system *declined* to do.

Two design decisions worth stating, because both are deliberate:

**The file is JSON Lines, not a JSON array.** One self-contained JSON object per
line, appended with `open(..., "a")`. A real JSON array would have to be read,
parsed, re-serialised and rewritten on every event — which is a whole-file
rewrite pretending to be an append, and the one failure mode an audit trail must
not have is "a crash mid-write truncates the history". Appending a line can only
ever add; it has no code path that shortens the file. Nothing in this project
opens the trail in `"w"` mode.

**Nothing personal goes in.** Shopper text is passed through `redact()` and
truncated to a preview before it is written. Tool arguments and results are
summarised to catalogue facts (product ids, prices, counts) which contain no
customer data by construction. Identity is recorded as the integer `user_id`
only — never a name or an email. The trail is committed to a public repository,
so it is written as though it will be read by a stranger, because it will be.
"""

from __future__ import annotations

import json
import os
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AUDIT_PATH = Path(__file__).resolve().parent.parent / "output" / "audit_trail.json"

#: Shopper text is never stored in full — this is the cap on any logged preview.
PREVIEW_CHARS = 160

# One writer at a time. uvicorn runs sync endpoints in a threadpool and the
# agent loop is async, so two runs really can finish at the same moment; a
# single process-wide lock keeps lines from interleaving mid-write.
_write_lock = threading.Lock()

# Patterns scrubbed from anything a human typed before it reaches the file.
# Ordered most-specific first so a credential isn't partially matched by a
# looser pattern further down.
_REDACTIONS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"pbkdf2_sha256\$[A-Za-z0-9$]+"), "[redacted:password-hash]"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"), "[redacted:api-key]"),
    (re.compile(r"\b[\w.%+-]+@[\w.-]+\.[A-Za-z]{2,}\b"), "[redacted:email]"),
    # Card-like runs of digits, allowing spaces or dashes between groups.
    (re.compile(r"\b(?:\d[ -]?){13,19}\b"), "[redacted:long-number]"),
    (re.compile(r"\b(?:\+?\d[\s().-]?){9,}\d\b"), "[redacted:phone]"),
]


def redact(text: str) -> str:
    """Strip anything that looks like a credential or a personal identifier."""
    for pattern, replacement in _REDACTIONS:
        text = pattern.sub(replacement, text)
    return text


def preview(text: str | None, limit: int = PREVIEW_CHARS) -> str | None:
    """Redact, collapse whitespace, and truncate free text down to a preview.

    Used for the shopper's message and the assistant's reply. Enough to tell
    what a run was about when reading the trail back; never enough to
    reconstruct the conversation.
    """
    if text is None:
        return None
    cleaned = redact(" ".join(text.split()))
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1] + "…"


def new_run_id() -> str:
    """Short correlation id tying a run's start, tool calls, and end together."""
    return uuid.uuid4().hex[:12]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def record(event: str, **fields: Any) -> None:
    """Append one event to the trail.

    Deliberately swallows its own errors. An audit trail that can take the
    storefront down when the disk is full is a worse outcome than a missing
    line, and the caller is always in the middle of serving a shopper.
    """
    entry = {"ts": _utc_now(), "event": event, **fields}
    try:
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(entry, ensure_ascii=False, default=str)
        with _write_lock:
            # "a" is the whole guarantee: the file is only ever extended.
            with AUDIT_PATH.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
                handle.flush()
                os.fsync(handle.fileno())
    except Exception:  # pragma: no cover - logging must never break a request
        pass


def read_events() -> list[dict[str, Any]]:
    """Read the trail back. Used by the verification script, not by the app.

    Skips unparseable lines rather than raising, so a single torn line from a
    hard kill can't make the rest of the history unreadable.
    """
    if not AUDIT_PATH.is_file():
        return []
    events: list[dict[str, Any]] = []
    for line in AUDIT_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events
