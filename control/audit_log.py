from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .redaction import RedactionError, leak_guard, redact_text

DEFAULT_AUDIT_LOG = Path(
    os.environ.get("HERMES_FLEET_AUDIT_LOG")
    or (Path(os.environ["HERMES_FLEET_RUNTIME_DIR"]) / "audit" / "actions.jsonl" if os.environ.get("HERMES_FLEET_RUNTIME_DIR") else "runtime/audit/actions.jsonl")
)
MAX_MESSAGE_CHARS = 500


def _safe_entry(entry: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "ts",
        "event",
        "action",
        "group",
        "targets",
        "safe",
        "force",
        "dry_run",
        "degraded_only",
        "ok",
        "error",
        "returncode",
        "message",
    }
    safe = {k: v for k, v in entry.items() if k in allowed}
    if "message" in safe and safe["message"] is not None:
        safe["message"] = redact_text(str(safe["message"]))[:MAX_MESSAGE_CHARS]
    text = json.dumps(safe, ensure_ascii=False, sort_keys=True)
    leak_guard(text)
    return safe


def build_action_entry(*, ts: str, result: dict[str, Any]) -> dict[str, Any]:
    raw_plan = result.get("plan")
    plan: dict[str, Any] = raw_plan if isinstance(raw_plan, dict) else {}
    message = result.get("message") or result.get("error")
    return _safe_entry({
        "ts": ts,
        "event": "gateway_action",
        "action": plan.get("action"),
        "group": plan.get("group"),
        "targets": list(plan.get("targets") or []),
        "safe": bool(plan.get("safe", True)),
        "force": bool(plan.get("force", False)),
        "dry_run": bool(result.get("dry_run", plan.get("dry_run", False))),
        "degraded_only": bool(plan.get("degraded_only", False)),
        "ok": bool(result.get("ok", False)),
        "error": result.get("error"),
        "returncode": result.get("returncode"),
        "message": message,
    })


def append_action_entry(path: Path, entry: dict[str, Any]) -> None:
    safe = _safe_entry(entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(safe, ensure_ascii=False, sort_keys=True) + "\n")


def tail_actions(path: Path, limit: int = 5) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]
    except Exception:
        return []
    entries: list[dict[str, Any]] = []
    for line in lines:
        try:
            parsed = json.loads(line)
            if isinstance(parsed, dict):
                entries.append(_safe_entry(parsed))
        except (json.JSONDecodeError, RedactionError):
            continue
    return list(reversed(entries))


def build_audit_summary(path: Path, limit: int = 5) -> dict[str, Any]:
    return {
        "path": str(path),
        "last_actions": tail_actions(path, limit=limit),
    }
