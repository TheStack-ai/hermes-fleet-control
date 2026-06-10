#!/usr/bin/env python3
from __future__ import annotations

import argparse
import platform
import plistlib
import subprocess
import sys
from pathlib import Path

ROOT_FOR_IMPORTS = Path(__file__).resolve().parents[1]
if str(ROOT_FOR_IMPORTS) not in sys.path:
    sys.path.insert(0, str(ROOT_FOR_IMPORTS))

from control.paths import launch_label, launch_plist_path, repo_root

ROOT = repo_root()
APP_PATH = ROOT / "dist" / "HermesFleetControl.app"
LABEL = launch_label()
PLIST_PATH = launch_plist_path()
LOG_DIR = ROOT / "runtime" / "logs"


def _is_macos() -> bool:
    return platform.system() == "Darwin"


def build_plist() -> dict[str, object]:
    return {
        "Label": LABEL,
        "ProgramArguments": ["/usr/bin/open", str(APP_PATH)],
        "RunAtLoad": True,
        "KeepAlive": False,
        "StandardOutPath": str(LOG_DIR / "launchagent.out.log"),
        "StandardErrorPath": str(LOG_DIR / "launchagent.err.log"),
    }


def write_plist(path: Path = PLIST_PATH) -> Path:
    if not _is_macos():
        raise RuntimeError("LaunchAgent autostart is available on macOS only")
    if path == PLIST_PATH and not APP_PATH.exists():
        raise FileNotFoundError(f"package the app first: {APP_PATH}")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        plistlib.dump(build_plist(), f)
    return path


def uid() -> str:
    return subprocess.check_output(["id", "-u"], text=True).strip()


def launchagent_status(path: Path = PLIST_PATH) -> dict[str, object]:
    installed = path.exists()
    enabled = False
    loaded = False
    if _is_macos() and path == PLIST_PATH:
        domain = f"gui/{uid()}"
        domain_label = f"{domain}/{LABEL}"
        enabled_proc = subprocess.run(["launchctl", "print-disabled", domain], text=True, capture_output=True, check=False)
        if enabled_proc.returncode == 0:
            disabled_line = f'"{LABEL}" => true'
            enabled = disabled_line not in enabled_proc.stdout
        print_proc = subprocess.run(["launchctl", "print", domain_label], text=True, capture_output=True, check=False)
        loaded = print_proc.returncode == 0
    return {
        "label": LABEL,
        "plist": str(path),
        "installed": installed,
        "enabled": bool(enabled and installed),
        "loaded": bool(loaded and installed),
        "platform": platform.system(),
        "supported": _is_macos(),
    }


def install(path: Path = PLIST_PATH, bootstrap: bool = True) -> Path:
    path = write_plist(path)
    if bootstrap and path == PLIST_PATH:
        subprocess.run(["launchctl", "bootstrap", f"gui/{uid()}", str(path)], check=False)
        subprocess.run(["launchctl", "enable", f"gui/{uid()}/{LABEL}"], check=False)
    return path


def disable() -> Path:
    if not _is_macos():
        raise RuntimeError("LaunchAgent autostart is available on macOS only")
    subprocess.run(["launchctl", "disable", f"gui/{uid()}/{LABEL}"], check=False)
    return PLIST_PATH


def enable() -> Path:
    if not _is_macos():
        raise RuntimeError("LaunchAgent autostart is available on macOS only")
    subprocess.run(["launchctl", "enable", f"gui/{uid()}/{LABEL}"], check=False)
    return PLIST_PATH


def uninstall(path: Path = PLIST_PATH, bootstrap: bool = True) -> Path:
    if not _is_macos():
        raise RuntimeError("LaunchAgent autostart is available on macOS only")
    if bootstrap and path == PLIST_PATH:
        subprocess.run(["launchctl", "bootout", f"gui/{uid()}/{LABEL}"], check=False)
    if path.exists():
        path.unlink()
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare/install Hermes Fleet Control LaunchAgent")
    parser.add_argument("action", choices=["print", "status", "write", "install", "enable", "disable", "uninstall"])
    parser.add_argument("--plist", default=str(PLIST_PATH))
    parser.add_argument("--no-bootstrap", action="store_true")
    args = parser.parse_args(argv)
    plist_path = Path(args.plist).expanduser()

    if args.action == "print":
        print(plistlib.dumps(build_plist()).decode("utf-8"))
    elif args.action == "status":
        print(launchagent_status(plist_path))
    elif args.action == "write":
        print(write_plist(plist_path))
    elif args.action == "install":
        print(install(plist_path, bootstrap=not args.no_bootstrap))
    elif args.action == "enable":
        print(enable())
    elif args.action == "disable":
        print(disable())
    elif args.action == "uninstall":
        print(uninstall(plist_path, bootstrap=not args.no_bootstrap))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
