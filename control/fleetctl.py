#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import platform
import json
import re
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Allow running as `python control/fleetctl.py` from repo root.
if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from control.audit_log import DEFAULT_AUDIT_LOG, append_action_entry, build_action_entry, build_audit_summary
from control.gateway_actions import ActionBlocked, execute_plan, plan_action
from control.auth_health import build_auth_health, inspect_profile_codex_auth
from control.discovery import auto_discovered_manifest, is_public_default_manifest
from control.local_mappings import load_profile_map, upsert_profile_mapping
from control.hermes_profiles import launchd_pid_map, summarize_profile
from control.manifest import load_manifest
from control.network_checks import check_discord_network
from control.paths import auth_repair_script_dir, codex_auth_file, default_manifest_path, hermes_executable, hermes_home, profiles_root, repo_root, user_home, launch_plist_path, profile_map_path
from control.redaction import RedactionError, leak_guard, redact_text
from scripts.launchagent import disable as launchagent_disable, enable as launchagent_enable, install as launchagent_install, launchagent_status, uninstall as launchagent_uninstall, write_plist
DEFAULT_MANIFEST = default_manifest_path()
DEFAULT_PROFILES_ROOT = profiles_root()
AUTH_REPAIR_SCRIPT_DIR = auth_repair_script_dir()



def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _should_auto_discover(args: argparse.Namespace, manifest: dict[str, Any]) -> bool:
    if getattr(args, "no_auto_discover", False):
        return False
    if os.environ.get("HERMES_FLEET_MANIFEST"):
        return False
    if (repo_root() / "config" / "fleet.local.yaml").exists():
        return False
    return is_public_default_manifest(manifest)


def _load_effective_manifest(args: argparse.Namespace) -> tuple[dict[str, Any], str]:
    manifest = load_manifest(Path(args.manifest))
    if _should_auto_discover(args, manifest):
        mapping = load_profile_map(Path(getattr(args, "map_file", profile_map_path())))
        discovered = auto_discovered_manifest(hermes_home(), Path(args.profiles_root), profile_map=mapping)
        if discovered:
            return discovered, "auto_discovery"
    return manifest, "manifest"


def _profile_root_for_item(item: dict[str, Any], args: argparse.Namespace) -> Path:
    explicit = item.get("profile_root")
    if explicit:
        return Path(str(explicit)).expanduser()
    name = str(item["profile"])
    candidate = Path(args.profiles_root) / name
    if name == "default" and not candidate.exists():
        return hermes_home()
    return candidate


def build_status(args: argparse.Namespace) -> dict[str, Any]:
    manifest, manifest_source = _load_effective_manifest(args)
    use_launchd_pid_map = args.profiles_root == str(DEFAULT_PROFILES_ROOT) and not os.environ.get("HERMES_HOME") and not os.environ.get("HERMES_PROFILES_ROOT")
    pid_map = launchd_pid_map() if use_launchd_pid_map else None
    servers = []
    for key, server in manifest["servers"].items():
        if args.group and key != args.group:
            continue
        profiles = []
        counts = {"healthy": 0, "degraded": 0, "stopped": 0, "busy": 0, "unknown": 0, "unclassified": 0, "inactive": 0, "ignored": 0}
        for item in server.get("profiles", []):
            name = item["profile"]
            profile_root = _profile_root_for_item(item, args)
            pid_present = pid_map.get(name, False) if pid_map is not None else True
            summary = summarize_profile(profile_root, name, launchd_pid_present=pid_present)
            if item.get("status_override"):
                summary["status"] = str(item["status_override"])
                summary["safe_actions"] = []
            summary["auth"] = inspect_profile_codex_auth(profile_root)
            summary["display"] = item.get("display", name)
            summary["critical"] = bool(item.get("critical", False))
            profiles.append(summary)
            status = summary["status"]
            if status == "healthy":
                counts["healthy"] += 1
            elif status == "busy":
                counts["busy"] += 1
            elif status == "stopped":
                counts["stopped"] += 1
            elif status == "unclassified":
                counts["unclassified"] += 1
            elif status == "inactive":
                counts["inactive"] += 1
            elif status == "ignored":
                counts["ignored"] += 1
            elif status.startswith("degraded"):
                counts["degraded"] += 1
            else:
                counts["unknown"] += 1
        servers.append({"key": key, "display": server.get("display", key), "summary": counts, "profiles": profiles})
    network = {"skipped": True} if args.skip_network else check_discord_network()
    if getattr(args, "skip_auth", False):
        auth_health = {"skipped": True, "metadata_only": True}
    else:
        env_files = getattr(args, "env_file", None)
        auth_health = build_auth_health(Path(args.auth_file), env_paths=[Path(p) for p in env_files] if env_files else None)
    audit = build_audit_summary(Path(args.audit_log), limit=getattr(args, "audit_limit", 5))
    return {"ok": True, "generated_at": now_iso(), "manifest_source": manifest_source, "network": network, "auth_health": auth_health, "audit": audit, "servers": servers}


def _profiles_from_status(status: dict[str, Any], group: str | None, profile: str | None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for server in status["servers"]:
        if group and server["key"] != group:
            continue
        for item in server["profiles"]:
            if profile and item["profile"] != profile:
                continue
            out.append(item)
    return out


def _manifest_profile_names(manifest: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for server in manifest.get("servers", {}).values():
        for item in server.get("profiles", []):
            if item.get("profile"):
                names.add(str(item["profile"]))
    return names


def _terminal_command_for_auth_repair(profile: str, action: str) -> list[str]:
    if action == "reauth":
        return [hermes_executable(), "-p", profile, "auth", "add", "openai-codex", "--type", "oauth"]
    if action == "reauth-manual":
        return [hermes_executable(), "-p", profile, "auth", "add", "openai-codex", "--type", "oauth", "--manual-paste"]
    if action == "smoke":
        return [hermes_executable(), "-p", profile, "chat", "-Q", "-q", "Reply exactly: OK"]
    if action == "restart":
        return [sys.executable, str(Path(__file__).resolve()), "restart", "--profile", profile, "--safe", "--json", "--skip-network", "--skip-auth"]
    raise ValueError(f"unsupported auth repair action: {action}")

def _display_command(command: list[str]) -> list[str]:
    out: list[str] = []
    root = Path(__file__).resolve().parents[1]
    for part in command:
        p = Path(part)
        if p.is_absolute():
            try:
                out.append(str(p.relative_to(root)))
            except ValueError:
                out.append(p.name)
        else:
            out.append(part)
    return out

def _terminal_script(profile: str, action: str, command: list[str]) -> str:
    if platform.system() == "Windows":
        quoted = " ".join('"' + part.replace('"', '`"') + '"' for part in command)
        title = f"Hermes Fleet auth repair · {profile} · {action}"
        lines = [
            "$ErrorActionPreference = 'Stop'",
            f"Write-Host {json.dumps(title)}",
            "Write-Host 'Provider: openai-codex'",
            "Write-Host 'Sign in directly in this terminal; only the selected profile auth is updated.'",
        ]
        if action == "restart":
            lines.append("Read-Host 'Press Enter to continue, or Ctrl-C to cancel'")
        lines.extend([
            quoted,
            "$status = $LASTEXITCODE",
            "Write-Host ''",
            "Write-Host ('Done. Exit code: ' + $status)",
            "Read-Host 'Press Enter to close this window'",
            "exit $status",
        ])
        return "\n".join(lines) + "\n"
    quoted = " ".join(shlex.quote(part) for part in command)
    title = f"Hermes Fleet auth repair · {profile} · {action}"
    lines = [
        "#!/bin/bash",
        f"export HOME={shlex.quote(str(user_home()))}",
        "unset HERMES_HOME",
        f"cd {shlex.quote(str(user_home()))}",
        f"printf {shlex.quote(title + chr(10))}",
        "printf 'Provider: openai-codex\\n'",
        "printf '이 창에서 직접 로그인하면 선택한 profile auth.json만 갱신됩니다.\\n\\n'",
    ]
    if action == "restart":
        lines.append("printf 'This will restart only the selected Hermes gateway after auth repair.\\n'")
        lines.append("read -r -p 'Press Enter to continue, or Ctrl-C to cancel: ' _")
    lines.extend([
        quoted,
        "status=$?",
    ])
    if action.startswith("reauth"):
        lines.append("printf '\\n로그인이 끝나면 상태바 앱에서 Smoke를 눌러 OK인지 확인하세요.\\n'")
        lines.append("printf 'OK면 필요한 profile gateway만 Restart 하면 됩니다.\\n'")
    if action == "smoke":
        lines.append("printf '\\nIf this prints OK, restart the profile gateway from Fleet Control if Discord still errors.\\n'")
    lines.extend([
        "printf '\\nDone. Exit code: %s\\n' \"$status\"",
        "read -r -p 'Press Enter to close this window: ' _",
        "exit \"$status\"",
    ])
    return "\n".join(lines) + "\n"


def _write_terminal_command_file(profile: str, action: str, script: str, directory: Path = AUTH_REPAIR_SCRIPT_DIR) -> Path:
    safe_profile = re.sub(r"[^A-Za-z0-9_.-]+", "-", profile).strip("-") or "profile"
    safe_action = re.sub(r"[^A-Za-z0-9_.-]+", "-", action).strip("-") or "action"
    stamp = now_iso().replace(":", "").replace("-", "").replace("Z", "Z")
    directory.mkdir(parents=True, exist_ok=True)
    suffix = ".ps1" if platform.system() == "Windows" else ".command"
    path = directory / f"{stamp}-{safe_profile}-{safe_action}{suffix}"
    path.write_text(script, encoding="utf-8")
    path.chmod(0o700)
    return path


def _open_terminal(script: str, profile: str, action: str) -> Path:
    script_path = _write_terminal_command_file(profile, action, script)
    system = platform.system()
    if system == "Darwin":
        subprocess.run(["open", str(script_path)], check=True, text=True, capture_output=True, timeout=20)
    elif system == "Windows":
        subprocess.run([
            "powershell", "-NoProfile", "-Command", "Start-Process", "powershell",
            "-ArgumentList", f"-NoExit -ExecutionPolicy Bypass -File {script_path}",
        ], check=True, text=True, capture_output=True, timeout=20)
    else:
        opener = next((cmd for cmd in ("xdg-open", "gio") if subprocess.run(["which", cmd], text=True, capture_output=True).returncode == 0), None)
        if not opener:
            raise RuntimeError(f"No terminal opener found; run script manually: {script_path}")
        subprocess.run([opener, str(script_path)], check=True, text=True, capture_output=True, timeout=20)
    return script_path


def auth_repair_command(args: argparse.Namespace) -> dict[str, Any]:
    manifest, _ = _load_effective_manifest(args)
    allowed = _manifest_profile_names(manifest)
    if args.profile not in allowed:
        return {"ok": False, "error": "unknown_profile", "message": f"profile not in fleet manifest: {args.profile}"}
    command = _terminal_command_for_auth_repair(args.profile, args.auth_action)
    script = _terminal_script(args.profile, args.auth_action, command)
    result: dict[str, Any] = {
        "ok": True,
        "generated_at": now_iso(),
        "profile": args.profile,
        "provider": "openai-codex",
        "action": args.auth_action,
        "opened_terminal": False,
        "command": _display_command(command),
        "message": "Terminal auth repair command prepared; no token values are displayed or stored.",
    }
    if args.open_terminal:
        try:
            script_path = _open_terminal(script, args.profile, args.auth_action)
            result["opened_terminal"] = True
            result["script_path"] = str(script_path)
            result["message"] = "Opened Terminal for profile-scoped auth repair."
        except Exception as exc:
            result.update({"ok": False, "error": type(exc).__name__, "message": str(exc)})
    return result


def print_json(data: dict[str, Any]) -> int:
    text = redact_text(json.dumps(data, ensure_ascii=False, indent=2))
    try:
        leak_guard(text)
    except RedactionError as exc:
        safe = {"ok": False, "error": "redaction_guard_failed", "detail": str(exc)}
        print(json.dumps(safe, ensure_ascii=False))
        return 2
    print(text)
    return 0 if data.get("ok", False) else 1


def record_action_result(args: argparse.Namespace, result: dict[str, Any]) -> None:
    entry = build_action_entry(ts=now_iso(), result=result)
    append_action_entry(Path(args.audit_log), entry)


def launchagent_command(args: argparse.Namespace) -> dict[str, Any]:
    plist = Path(args.plist)
    try:
        if args.launchagent_action == "status":
            status = launchagent_status(plist)
        elif args.launchagent_action == "write":
            write_plist(plist)
            status = launchagent_status(plist)
        elif args.launchagent_action == "install":
            launchagent_install(plist, bootstrap=not args.no_bootstrap)
            status = launchagent_status(plist)
        elif args.launchagent_action == "enable":
            launchagent_enable()
            status = launchagent_status(plist)
        elif args.launchagent_action == "disable":
            launchagent_disable()
            status = launchagent_status(plist)
        elif args.launchagent_action == "uninstall":
            launchagent_uninstall(plist, bootstrap=not args.no_bootstrap)
            status = launchagent_status(plist)
        else:
            return {"ok": False, "error": "unsupported_launchagent_action"}
    except Exception as exc:
        return {"ok": False, "error": type(exc).__name__, "message": str(exc)}
    return {"ok": True, "generated_at": now_iso(), "launchagent": status}


def profile_map_command(args: argparse.Namespace) -> dict[str, Any]:
    try:
        mapping = upsert_profile_mapping(
            Path(args.map_file),
            args.profile,
            display=args.display,
            server=args.server,
            server_display=args.server_display,
            state=args.state,
        )
    except Exception as exc:
        return {"ok": False, "error": type(exc).__name__, "message": str(exc)}
    return {
        "ok": True,
        "generated_at": now_iso(),
        "profile": args.profile,
        "map_file": str(Path(args.map_file).expanduser()),
        "mapping": mapping,
        "message": "Profile classification saved locally. No secrets were read or written.",
    }


def run_watchdog(args: argparse.Namespace) -> dict[str, Any]:
    status = build_status(args)
    actions: list[dict[str, Any]] = []
    groups = [args.group] if args.group else [server["key"] for server in status["servers"]]
    for group in groups:
        targets = [p for p in _profiles_from_status(status, group, None) if str(p.get("status", "")).startswith("degraded")]
        if not targets:
            continue
        try:
            plan = plan_action("reconnect", group=group, profiles=targets, safe=True, force=False, dry_run=args.policy != "auto")
            plan["degraded_only"] = True
            result = execute_plan(plan)
        except (ActionBlocked, ValueError) as exc:
            result = {"ok": False, "error": type(exc).__name__, "message": str(exc), "plan": {"action": "reconnect", "group": group, "targets": [p.get("profile") for p in targets], "safe": True, "force": False, "dry_run": args.policy != "auto", "degraded_only": True}}
        record_action_result(args, result)
        actions.append(result)
    message = "no degraded profiles matched; no gateway action planned" if not actions else "watchdog action evaluated"
    return {"ok": all(action.get("ok") for action in actions) if actions else True, "generated_at": now_iso(), "watchdog": {"policy": args.policy, "groups": groups, "actions": actions, "message": message}}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Hermes Fleet Control CLI")
    sub = ap.add_subparsers(dest="command", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    common.add_argument("--profiles-root", default=str(DEFAULT_PROFILES_ROOT))
    common.add_argument("--group", default=None)
    common.add_argument("--skip-network", action="store_true")
    common.add_argument("--auth-file", default=str(codex_auth_file()))
    common.add_argument("--env-file", action="append")
    common.add_argument("--skip-auth", action="store_true")
    common.add_argument("--audit-log", default=str(DEFAULT_AUDIT_LOG))
    common.add_argument("--audit-limit", type=int, default=5)
    common.add_argument("--no-auto-discover", action="store_true", help="use the manifest exactly; do not auto-discover local Hermes profiles")
    common.add_argument("--map-file", default=str(profile_map_path()), help="local profile classification map JSON")

    sp = sub.add_parser("status", parents=[common])
    sp.add_argument("--json", action="store_true")

    np = sub.add_parser("network-check")
    np.add_argument("--json", action="store_true")

    lp = sub.add_parser("launchagent")
    lp.add_argument("launchagent_action", choices=["status", "write", "install", "enable", "disable", "uninstall"])
    lp.add_argument("--json", action="store_true")
    lp.add_argument("--plist", default=str(launch_plist_path()))
    lp.add_argument("--no-bootstrap", action="store_true")

    mp = sub.add_parser("profile-map")
    mp.add_argument("--profile", required=True)
    mp.add_argument("--display")
    mp.add_argument("--server")
    mp.add_argument("--server-display")
    mp.add_argument("--state", choices=["managed", "unclassified", "inactive", "ignored"], default="managed")
    mp.add_argument("--map-file", default=str(profile_map_path()))
    mp.add_argument("--json", action="store_true")

    wp = sub.add_parser("watchdog", parents=[common])
    wp.add_argument("--policy", choices=["dry-run", "auto"], default="dry-run")
    wp.add_argument("--json", action="store_true")

    arp = sub.add_parser("auth-repair")
    arp.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    arp.add_argument("--profiles-root", default=str(DEFAULT_PROFILES_ROOT))
    arp.add_argument("--map-file", default=str(profile_map_path()))
    arp.add_argument("--no-auto-discover", action="store_true")
    arp.add_argument("--profile", required=True)
    arp.add_argument("--action", dest="auth_action", choices=["reauth", "reauth-manual", "smoke", "restart"], default="reauth")
    arp.add_argument("--open-terminal", action="store_true")
    arp.add_argument("--json", action="store_true")

    for name in ["start", "stop", "restart", "reconnect"]:
        p = sub.add_parser(name, parents=[common])
        # `--group` is inherited from status filtering and doubles as the group
        # target for action commands so the documented command stays simple:
        # `fleetctl.py reconnect --group local --safe --dry-run`.
        p.add_argument("--profile")
        p.add_argument("--target-group", dest="target_group", help=argparse.SUPPRESS)
        p.add_argument("--safe", action="store_true", default=True)
        p.add_argument("--force", action="store_true")
        p.add_argument("--dry-run", action="store_true")
        p.add_argument("--degraded-only", action="store_true", help="target only profiles currently classified as degraded")
        p.add_argument("--json", action="store_true")

    args = ap.parse_args(argv)
    if args.command == "network-check":
        return print_json({"ok": True, "generated_at": now_iso(), "network": check_discord_network()})
    if args.command == "launchagent":
        return print_json(launchagent_command(args))
    if args.command == "profile-map":
        return print_json(profile_map_command(args))
    if args.command == "status":
        return print_json(build_status(args))
    if args.command == "watchdog":
        return print_json(run_watchdog(args))
    if args.command == "auth-repair":
        return print_json(auth_repair_command(args))

    # Action commands build a fresh status snapshot first to apply active-agent gates.
    action_group = getattr(args, "target_group", None) or args.group
    if getattr(args, "profile", None) and action_group:
        return print_json({"ok": False, "error": "invalid_target", "message": "choose either --profile or --group, not both"})
    if not getattr(args, "profile", None) and not action_group:
        return print_json({"ok": False, "error": "missing_target", "message": "provide --profile or --group"})
    args.group = action_group
    status = build_status(args)
    targets = _profiles_from_status(status, action_group, getattr(args, "profile", None))
    if getattr(args, "degraded_only", False):
        targets = [p for p in targets if str(p.get("status", "")).startswith("degraded")]
        if not targets:
            result = {
                "ok": True,
                "dry_run": bool(args.dry_run),
                "message": "no degraded profiles matched; no gateway action planned",
                "plan": {
                    "action": args.command,
                    "group": action_group,
                    "targets": [],
                    "safe": args.safe,
                    "force": args.force,
                    "dry_run": args.dry_run,
                    "command": [],
                    "degraded_only": True,
                },
            }
            record_action_result(args, result)
            return print_json(result)
    try:
        plan = plan_action(args.command, group=action_group, profiles=targets, safe=args.safe, force=args.force, dry_run=args.dry_run)
        if getattr(args, "degraded_only", False):
            plan["degraded_only"] = True
        result = execute_plan(plan)
    except (ActionBlocked, ValueError) as exc:
        result = {"ok": False, "error": type(exc).__name__, "message": str(exc), "plan": {"action": args.command, "group": action_group, "targets": [p.get("profile") for p in targets], "safe": args.safe, "force": args.force, "dry_run": args.dry_run, "degraded_only": getattr(args, "degraded_only", False)}}
    record_action_result(args, result)
    return print_json(result)


if __name__ == "__main__":
    raise SystemExit(main())
