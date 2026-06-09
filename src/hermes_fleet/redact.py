"""Secret-safe helpers."""

from __future__ import annotations

import re

SECRET_NAME_RE = re.compile(r"(token|secret|password|api[_-]?key|cookie|credential|private)", re.I)
SECRET_VALUE_RE = re.compile(
    r"("
    r"xox[baprs]-[A-Za-z0-9-]+|"
    r"xapp-[A-Za-z0-9-]+|"
    r"[0-9]{6,}:[A-Za-z0-9_-]{20,}|"
    r"sk-[A-Za-z0-9_-]{20,}|"
    r"gh[pousr]_[A-Za-z0-9_]{20,}|"
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----"
    r")",
    re.I,
)


def is_secret_key(name: str) -> bool:
    return bool(SECRET_NAME_RE.search(name))


def redact_value(text: str) -> str:
    return SECRET_VALUE_RE.sub("<redacted>", text)


def presence(value: object) -> str:
    return "present" if value not in (None, "", False) else "missing"
