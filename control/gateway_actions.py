from __future__ import annotations

import copy
import subprocess
from pathlib import Path
from typing import Any

from .paths import hermes_executable, python_executable, safe_restart_script


class ActionBlocked(RuntimeError):
    """Raised when a requested gateway action is not safe."""


def _profile_name(profile: dict[str, Any] | str) -> str:
    return profile if isinstance(profile, str) else str(profile.get("profile"))


def _ensure_not_busy(profiles: list[dict[str, Any]]) -> None:
    busy = [p for p in profiles if int(p.get("active_agents") or 0) > 0]
    if busy:
        names = ", ".join(_profile_name(p) for p in busy)
        raise ActionBlocked(f"active_agents present; refusing safe gateway action for: {names}")


def _hermes_gateway_command(profile: str, action: str) -> list[str]:
    hermes_action = "restart" if action == "reconnect" else action
    return [hermes_executable(), "-p", profile, "gateway", hermes_action]


def _display_command(command: list[str]) -> list[str]:
    if not command:
        return []
    repo = Path(__file__).resolve().parents[1]
    out: list[str] = []
    for part in command:
        p = Path(part)
        if p.is_absolute():
            try:
                out.append(str(p.relative_to(repo)))
            except ValueError:
                out.append(p.name)
        else:
            out.append(part)
    return out


def _display_plan(plan: dict[str, Any]) -> dict[str, Any]:
    safe = copy.deepcopy(plan)
    safe.pop("_commands", None)
    safe["command"] = _display_command(list(safe.get("command") or []))
    return safe


def plan_action(
    action: str,
    *,
    profile: dict[str, Any] | None = None,
    group: str | None = None,
    profiles: list[dict[str, Any]] | None = None,
    safe: bool = True,
    force: bool = False,
    dry_run: bool = True,
) -> dict[str, Any]:
    if action not in {"start", "stop", "restart", "reconnect"}:
        raise ValueError(f"unsupported action: {action}")
    targets = profiles or ([profile] if profile else [])
    targets = [p for p in targets if p]
    if not targets:
        raise ValueError("at least one profile is required")
    if safe and action in {"restart", "reconnect"} and not force:
        _ensure_not_busy(targets)  # type: ignore[arg-type]
    names = [_profile_name(p) for p in targets]  # type: ignore[arg-type]

    wrapper = safe_restart_script() if action in {"restart", "reconnect"} and len(names) > 1 else None
    if wrapper:
        command = [python_executable(), str(wrapper), *names]
        commands = [command]
    else:
        commands = [_hermes_gateway_command(name, action) for name in names]
        command = commands[0] if len(commands) == 1 else [hermes_executable(), "gateway", action, f"{len(commands)} profiles"]

    return {
        "action": action,
        "group": group,
        "targets": names,
        "safe": safe,
        "force": force,
        "dry_run": dry_run,
        "command": command,
        "_commands": commands,
    }


def execute_plan(plan: dict[str, Any]) -> dict[str, Any]:
    display_plan = _display_plan(plan)
    commands: list[list[str]] = [list(cmd) for cmd in (plan.get("_commands") or [plan.get("command") or []]) if cmd]
    if plan.get("dry_run"):
        return {"ok": True, "dry_run": True, "plan": display_plan}
    outputs: list[dict[str, Any]] = []
    ok = True
    for command in commands:
        proc = subprocess.run(command, text=True, capture_output=True, timeout=180)
        item = {
            "returncode": proc.returncode,
            "stdout": proc.stdout[-4000:],
            "stderr": proc.stderr[-4000:],
            "command": _display_command(command),
        }
        outputs.append(item)
        if proc.returncode != 0:
            ok = False
            break
    return {"ok": ok, "dry_run": False, "returncode": 0 if ok else outputs[-1]["returncode"], "outputs": outputs, "plan": display_plan}
