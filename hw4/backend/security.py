"""Session tokens, request throttling, and outbound PII scrubbing.

Three jobs, all of them about the same question: can a stranger with `curl`
make this agent do something it shouldn't?

1. **Identity is signed, not claimed.** Before Problem 12, `/api/chat` took a
   bare `user_id` integer from the request body and believed it. Anyone could
   post `{"user_id": 2}` and both read that customer's saved conversation and
   have their real name and email injected into the agent's system prompt.
   Identity now comes from an HMAC-signed token the server issued at login, so
   the worst a forged request can do is be rejected.

2. **Requests are throttled.** Every chat turn costs a real model call, so an
   open endpoint is simultaneously a billing hole and a denial-of-service
   surface.

3. **Replies are scrubbed on the way out.** Defence in depth: the system prompt
   forbids reading an email back, but a prompt rule is a request, not a
   guarantee. The regex pass is the guarantee.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import time
from collections import deque
from pathlib import Path

from models import RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW_SECONDS

BACKEND_DIR = Path(__file__).resolve().parent
SECRET_FILE = BACKEND_DIR / ".session_secret"

#: A week. Long enough that testing isn't constant re-login, short enough that a
#: token copied out of localStorage doesn't work forever.
SESSION_TTL_SECONDS = 7 * 24 * 60 * 60


def _load_secret() -> bytes:
    """Signing key: environment first, then a gitignored local file.

    Generating a fresh key per boot would be marginally safer and completely
    unusable — uvicorn `--reload` restarts on every edit, which would sign the
    developer out mid-sentence. Persisting it to a 0600 file that git ignores
    keeps sessions alive across restarts without the key ever entering the
    repository. In a real deployment this would come from the environment and
    the file branch would never run.
    """
    from_env = os.environ.get("CAMPUS_CUSTOMS_SECRET")
    if from_env:
        return from_env.encode("utf-8")

    if SECRET_FILE.is_file():
        existing = SECRET_FILE.read_text(encoding="utf-8").strip()
        if existing:
            return existing.encode("utf-8")

    generated = secrets.token_hex(32)
    SECRET_FILE.write_text(generated, encoding="utf-8")
    SECRET_FILE.chmod(0o600)
    return generated.encode("utf-8")


_SECRET = _load_secret()


def issue_session_token(user_id: int) -> str:
    """Mint `user_id.expiry.signature` for a shopper who just proved who they are."""
    expiry = int(time.time()) + SESSION_TTL_SECONDS
    payload = f"{user_id}.{expiry}"
    signature = hmac.new(_SECRET, payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def verify_session_token(token: str | None) -> int | None:
    """Return the user_id a token vouches for, or None if it doesn't vouch.

    Rejects anything malformed, expired, or wrongly signed. The comparison is
    constant-time so the endpoint can't be used as a signature oracle.
    """
    if not token:
        return None

    parts = token.split(".")
    if len(parts) != 3:
        return None

    raw_user_id, raw_expiry, signature = parts
    expected = hmac.new(
        _SECRET, f"{raw_user_id}.{raw_expiry}".encode("utf-8"), hashlib.sha256
    ).hexdigest()
    if not secrets.compare_digest(signature, expected):
        return None

    try:
        user_id = int(raw_user_id)
        expiry = int(raw_expiry)
    except ValueError:
        return None

    if expiry < time.time():
        return None
    return user_id


def bearer_token(authorization: str | None) -> str | None:
    """Pull the token out of an `Authorization: Bearer <token>` header."""
    if not authorization:
        return None
    scheme, _, value = authorization.partition(" ")
    if scheme.lower() != "bearer" or not value:
        return None
    return value.strip()


class RateLimiter:
    """Fixed-window-per-caller throttle, held in memory.

    In-process on purpose: this is a single-process teaching app, and a Redis
    dependency would be ceremony around a dict. The honest limitation is that
    it resets on restart and wouldn't coordinate across workers — stated here
    rather than discovered later.
    """

    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = {}

    def check(self, key: str) -> bool:
        """Record a hit. False means the caller is over their allowance."""
        now = time.time()
        cutoff = now - self.window

        # Drop callers who have gone quiet, so a flood of distinct source
        # addresses can't grow this dict without bound.
        if len(self._hits) > 2_000:
            for stale_key in [
                k for k, v in self._hits.items() if not v or v[-1] < cutoff
            ]:
                del self._hits[stale_key]

        hits = self._hits.setdefault(key, deque())
        while hits and hits[0] < cutoff:
            hits.popleft()

        if len(hits) >= self.limit:
            return False
        hits.append(now)
        return True


chat_rate_limiter = RateLimiter(RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW_SECONDS)


# What must never appear in a reply sent to a browser, regardless of what the
# model decided to say. Ordered most-specific first.
_OUTBOUND_REDACTIONS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"pbkdf2_sha256\$[A-Za-z0-9$]+"), "[removed]"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"), "[removed]"),
    (re.compile(r"\b[\w.%+-]+@[\w.-]+\.[A-Za-z]{2,}\b"), "[removed]"),
    (re.compile(r"\b(?:\d[ -]?){13,19}\b"), "[removed]"),
]


def scrub_reply(text: str) -> tuple[str, bool]:
    """Strip credentials and personal identifiers from an outbound reply.

    Returns the cleaned text and whether anything was removed. A True here is
    worth auditing: the agent was asked never to say these things, so it
    firing means either a prompt-injection attempt landed or the model slipped,
    and both are things you want a record of.
    """
    cleaned = text
    for pattern, replacement in _OUTBOUND_REDACTIONS:
        cleaned = pattern.sub(replacement, cleaned)
    return cleaned, cleaned != text
