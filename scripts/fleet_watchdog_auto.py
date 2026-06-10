#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT_FOR_IMPORTS = Path(__file__).resolve().parents[1]
if str(ROOT_FOR_IMPORTS) not in sys.path:
    sys.path.insert(0, str(ROOT_FOR_IMPORTS))

from control.paths import python_executable, repo_root

ROOT = repo_root()
FLEETCTL = ROOT / "control" / "fleetctl.py"


def main() -> int:
    proc = subprocess.run([
        python_executable(), str(FLEETCTL), "watchdog", "--policy", "auto", "--json", "--skip-network", "--skip-auth"
    ], cwd=str(ROOT), text=True, capture_output=True, timeout=180)
    if proc.returncode != 0:
        print("⚠️ Hermes Fleet watchdog failed")
        tail = (proc.stderr or proc.stdout)[-1200:]
        if tail:
            print(tail)
        return proc.returncode
    data = json.loads(proc.stdout)
    watchdog = data.get("watchdog", {})
    actions = watchdog.get("actions") or []
    if not actions:
        return 0
    lines = ["🛡️ Hermes Fleet watchdog auto-recovery ran"]
    for action in actions:
        plan = action.get("plan") or {}
        targets = ", ".join(plan.get("targets") or []) or "no targets"
        status = "OK" if action.get("ok") else "FAILED"
        lines.append(f"- {status}: {plan.get('group')} {plan.get('action')} degraded-only → {targets}")
    print("\n".join(lines))
    return 0 if data.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
