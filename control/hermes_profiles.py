from __future__ import annotations

import json
import platform
import re
import subprocess
from pathlib import Path
from typing import Any

from .redaction import redact_text

BACKOFF_RE = re.compile(r"Attempting a reconnect in\s+([0-9.]+)s|ClientConnectorDNSError|Cannot connect to host gateway.*discord", re.I)
CONNECT_RE = re.compile(r"Connected as|✓ discord connected|Gateway running", re.I)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return {}


def _read_recent_lines(root: Path, limit: int = 500) -> list[str]:
    out: list[str] = []
    for rel in ("logs/agent.log", "logs/gateway.log"):
        p = root / rel
        if p.exists():
            try:
                out.extend(p.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:])
            except Exception:
                pass
    return out


def _latest_signal(lines: list[str]) -> tuple[str, str]:
    last_connect = -1
    last_backoff = -1
    last_backoff_line = ""
    for i, line in enumerate(lines):
        if CONNECT_RE.search(line):
            last_connect = i
        if BACKOFF_RE.search(line):
            last_backoff = i
            last_backoff_line = line
    if last_backoff > last_connect:
        return "degraded_backoff", redact_text(f"Discord gateway backoff after latest connect: {last_backoff_line[-180:]}")
    if last_connect >= 0:
        return "connected", redact_text(lines[last_connect][-180:])
    return "unknown", "No recent Discord connection signal found"


def summarize_profile(root: Path, profile: str, launchd_pid_present: bool | None = None) -> dict[str, Any]:
    state = _read_json(root / "gateway_state.json")
    gateway_state = state.get("gateway_state") or state.get("state") or "unknown"
    active_agents = int(state.get("active_agents") or 0)
    platforms = state.get("platforms") if isinstance(state.get("platforms"), dict) else {}
    discord = platforms.get("discord", {}) if isinstance(platforms, dict) else {}
    discord_state = discord.get("status") or discord.get("state") or "unknown"
    pid_present = bool(launchd_pid_present) if launchd_pid_present is not None else bool(state.get("pid") or state.exists if False else True)
    signal, last_signal = _latest_signal(_read_recent_lines(root))

    if active_agents > 0:
        status = "busy"
    elif not pid_present or gateway_state not in {"running", "unknown"}:
        status = "stopped"
    elif signal == "degraded_backoff":
        status = "degraded_backoff"
    elif signal == "connected" or discord_state == "connected":
        status = "healthy"
    else:
        status = "unknown"

    safe_actions = ["start"] if status == "stopped" else ["stop"]
    if status != "busy":
        safe_actions.extend(["restart", "reconnect"])

    return {
        "profile": profile,
        "profile_root": str(root),
        "status": status,
        "launchd_pid_present": pid_present,
        "gateway_state": gateway_state,
        "discord_state": discord_state,
        "active_agents": active_agents,
        "safe_actions": sorted(set(safe_actions)),
        "last_signal": last_signal,
    }


def launchd_pid_map() -> dict[str, bool]:
    if platform.system() != "Darwin":
        return {}
    try:
        proc = subprocess.run(["launchctl", "list"], text=True, capture_output=True, timeout=15)
    except Exception:
        return {}
    mapping: dict[str, bool] = {}
    for line in proc.stdout.splitlines():
        if "ai.hermes.gateway-" not in line:
            continue
        parts = line.split()
        if len(parts) >= 3:
            profile = parts[2].replace("ai.hermes.gateway-", "")
            mapping[profile] = parts[0] != "-"
    return mapping
