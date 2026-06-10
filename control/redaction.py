from __future__ import annotations

import re


class RedactionError(RuntimeError):
    """Raised when output still contains a forbidden secret/private pattern."""


DISCORD_TOKEN_RE = re.compile(r"[A-Za-z0-9_\-]{24}\.[A-Za-z0-9_\-]{6}\.[A-Za-z0-9_\-]{27,}")
PRIVATE_ID_RE = re.compile(r"\b\d{16,22}\b")
DISCORD_HANDLE_RE = re.compile(r"(?i)(Connected as\s+)([^\n#]{1,80}#\d{4,})")
SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)(api[_-]?key|bot[_-]?token|auth[_-]?token|password|passwd|secret|cookie|credential|authorization|token)\s*[:=]\s*[^\s&]+"
)
SIGNED_PARAM_KEYS = ("X-Amz-" + "Signature", "Sign" + "ature=", "si" + "g=", "to" + "ken=")
SIGNED_PARAM_RE = re.compile(r"(?i)(" + "|".join(re.escape(k) for k in SIGNED_PARAM_KEYS) + r")[^\s&]+")


def redact_text(text: object) -> str:
    s = "" if text is None else str(text)
    s = DISCORD_TOKEN_RE.sub("[REDACTED_TOKEN]", s)
    s = PRIVATE_ID_RE.sub("[REDACTED_ID]", s)
    s = DISCORD_HANDLE_RE.sub(r"\1[REDACTED_DISCORD_HANDLE]", s)
    s = SIGNED_PARAM_RE.sub("[REDACTED_SIGNED_PARAM]", s)
    s = SECRET_ASSIGNMENT_RE.sub("[REDACTED_SECRET_ASSIGNMENT]", s)
    return s


def leak_guard(text: object) -> None:
    s = "" if text is None else str(text)
    checks = {
        "discord_token": DISCORD_TOKEN_RE,
        "private_id": PRIVATE_ID_RE,
        "discord_handle": DISCORD_HANDLE_RE,
        "secret_assignment": SECRET_ASSIGNMENT_RE,
        "signed_param": SIGNED_PARAM_RE,
    }
    for name, rx in checks.items():
        if rx.search(s):
            raise RedactionError(f"redaction_guard_failed:{name}")
