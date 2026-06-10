#!/usr/bin/env python3
from __future__ import annotations

import plistlib
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "app" / "HermesFleetControl"
DIST = ROOT / "dist"
APP = DIST / "HermesFleetControl.app"
EXECUTABLE_NAME = "HermesFleetControl"


def run(cmd: list[str], cwd: Path) -> None:
    subprocess.run(cmd, cwd=str(cwd), check=True)


def main() -> int:
    run(["xcrun", "swift", "build", "-c", "debug"], PACKAGE)
    binary = PACKAGE / ".build" / "debug" / EXECUTABLE_NAME
    if not binary.exists():
        raise FileNotFoundError(binary)

    if APP.exists():
        shutil.rmtree(APP)
    macos_dir = APP / "Contents" / "MacOS"
    resources_dir = APP / "Contents" / "Resources"
    macos_dir.mkdir(parents=True)
    resources_dir.mkdir(parents=True)

    shutil.copy2(binary, macos_dir / EXECUTABLE_NAME)
    plist = {
        "CFBundleDisplayName": "Hermes Fleet Control",
        "CFBundleExecutable": EXECUTABLE_NAME,
        "CFBundleIdentifier": "ai.hermes.fleet-control",
        "CFBundleInfoDictionaryVersion": "6.0",
        "CFBundleName": "HermesFleetControl",
        "CFBundlePackageType": "APPL",
        "CFBundleShortVersionString": "0.1.0",
        "CFBundleVersion": "1",
        "LSMinimumSystemVersion": "14.0",
        "LSUIElement": True,
        "NSHighResolutionCapable": True,
    }
    with (APP / "Contents" / "Info.plist").open("wb") as f:
        plistlib.dump(plist, f)
    run(["codesign", "--force", "--deep", "--sign", "-", str(APP)], ROOT)
    print(APP)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
