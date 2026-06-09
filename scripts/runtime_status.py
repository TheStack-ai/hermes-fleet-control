#!/usr/bin/env python3
"""Safe local runtime snapshot for Hermes Fleet Control work.

This script intentionally reports process/gateway metadata only. It does not read
or print auth tokens, API keys, cookies, Discord IDs, or provider secret values.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import platform
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

FLEET_PATTERNS = [
    # Keep these narrow: matching a project directory name like
    # `hermes-fleet-control-oss` would make the status command report itself.
    re.compile(r"HermesFleetControl", re.I),
    re.compile(r"Hermes Fleet", re.I),
    re.compile(r"fleet_watchdog", re.I),
]
GATEWAY_PATTERN = re.compile(r"hermes_cli\.main\s+--profile\s+(\S+)\s+gateway\s+run", re.I)
LAUNCHD_PATTERNS = [
    re.compile(r"ai\.hermes\.gateway", re.I),
    re.compile(r"hermes.*fleet", re.I),
]


def run(cmd: list[str], timeout: int = 8) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)
        return proc.returncode, proc.stdout, proc.stderr
    except FileNotFoundError as exc:
        return 127, "", str(exc)
    except subprocess.TimeoutExpired as exc:
        return 124, exc.stdout or "", exc.stderr or "timeout"


def parse_ps() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    code, out, err = run(["/bin/ps", "-axo", "pid,ppid,stat,lstart,command"])
    if code != 0:
        return [], [{"error": f"ps failed: {err.strip()}"}]

    fleet: list[dict[str, Any]] = []
    gateways: list[dict[str, Any]] = []
    for line in out.splitlines()[1:]:
        raw = line.rstrip()
        if not raw:
            continue
        # ps columns are: pid, ppid, stat, lstart(5 words), command.
        # That is 9 fields before command arguments are considered.
        parts = raw.split(maxsplit=8)
        if len(parts) < 9:
            continue
        pid, ppid, stat = parts[0], parts[1], parts[2]
        started = " ".join(parts[3:8])
        command = parts[8]

        gw = GATEWAY_PATTERN.search(command)
        if gw:
            gateways.append(
                {
                    "pid": int(pid),
                    "ppid": int(ppid),
                    "stat": stat,
                    "started": started,
                    "profile": gw.group(1),
                    "kind": "hermes_gateway",
                }
            )
            continue

        if any(p.search(command) for p in FLEET_PATTERNS):
            fleet.append(
                {
                    "pid": int(pid),
                    "ppid": int(ppid),
                    "stat": stat,
                    "started": started,
                    "kind": "fleet_related",
                    "command": compact_command(command),
                }
            )
    return fleet, gateways


def compact_command(command: str) -> str:
    # Keep paths/commands useful but avoid accidentally carrying huge args.
    command = re.sub(r"(token|key|secret|password)=\S+", r"\1=<redacted>", command, flags=re.I)
    return command if len(command) <= 240 else command[:237] + "..."


def launchctl_matches() -> list[dict[str, Any]]:
    if platform.system() != "Darwin":
        return []
    code, out, _ = run(["/bin/launchctl", "list"])
    if code != 0:
        return []
    rows: list[dict[str, Any]] = []
    for line in out.splitlines()[1:]:
        if not any(p.search(line) for p in LAUNCHD_PATTERNS):
            continue
        cols = line.split(None, 2)
        if len(cols) == 3:
            pid, status, label = cols
        elif len(cols) == 2:
            pid, status, label = cols[0], "", cols[1]
        else:
            continue
        rows.append({"pid": pid, "status": status, "label": label})
    return rows


def app_bundle_status() -> dict[str, Any]:
    candidates = [
        Path.home() / "Applications" / "HermesFleetControl.app",
        Path("/Applications/HermesFleetControl.app"),
    ]
    return {
        "candidates": [str(p) for p in candidates if p.exists()],
        "note": "Generic app bundle probe; runtime snapshots should not be published.",
    }


def collect() -> dict[str, Any]:
    fleet, gateways = parse_ps()
    return {
        "generated_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "host": platform.node(),
        "system": f"{platform.system()} {platform.release()}",
        "user": os.getenv("USER", ""),
        "fleet_processes": fleet,
        "hermes_gateways": sorted(gateways, key=lambda item: item.get("profile", "")),
        "launchctl_matches": launchctl_matches(),
        "app_bundle_status": app_bundle_status(),
        "safety": {
            "secret_values_read": False,
            "secret_values_printed": False,
            "external_side_effects": False,
            "processes_modified": False,
        },
    }


def render_text(data: dict[str, Any]) -> str:
    lines = []
    lines.append("Hermes Fleet runtime status")
    lines.append(f"generated_at: {data['generated_at']}")
    lines.append(f"host: {data['host']}")
    lines.append(f"system: {data['system']}")
    lines.append("")

    lines.append(f"Fleet-related processes: {len(data['fleet_processes'])}")
    for proc in data["fleet_processes"]:
        lines.append(f"- pid={proc['pid']} stat={proc['stat']} started='{proc['started']}' cmd={proc['command']}")
    if not data["fleet_processes"]:
        lines.append("- none detected")
    lines.append("")

    lines.append(f"Hermes gateway processes: {len(data['hermes_gateways'])}")
    for proc in data["hermes_gateways"]:
        lines.append(f"- profile={proc['profile']} pid={proc['pid']} stat={proc['stat']} started='{proc['started']}'")
    if not data["hermes_gateways"]:
        lines.append("- none detected")
    lines.append("")

    lines.append(f"launchctl matches: {len(data['launchctl_matches'])}")
    for row in data["launchctl_matches"]:
        lines.append(f"- label={row['label']} pid={row['pid']} status={row['status']}")
    if not data["launchctl_matches"]:
        lines.append("- none detected")
    lines.append("")

    bundles = data["app_bundle_status"]["candidates"]
    lines.append(f"Known app bundles found: {len(bundles)}")
    for path in bundles:
        lines.append(f"- {path}")
    if not bundles:
        lines.append("- none detected")
    lines.append("")

    lines.append("Safety: metadata-only, no secrets read/printed, no process changes.")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Show safe Hermes/Fleet runtime status.")
    parser.add_argument("--json", action="store_true", help="print JSON instead of text")
    args = parser.parse_args()

    data = collect()
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(render_text(data), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
