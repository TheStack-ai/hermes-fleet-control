#!/usr/bin/env python3
from __future__ import annotations

import argparse
import plistlib
import shutil
import subprocess
from pathlib import Path

RESOURCE_DIRS = ("control", "scripts", "config")
RESOURCE_FILES = ("README.md", "pyproject.toml")
EXCLUDED_RESOURCE_NAMES = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
ICON_SOURCE = Path("assets/icons/HermesFleetControl.icns")

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "app" / "HermesFleetControl"
DIST = ROOT / "dist"
APP = DIST / "HermesFleetControl.app"
EXECUTABLE_NAME = "HermesFleetControl"


def run(cmd: list[str], cwd: Path) -> None:
    subprocess.run(cmd, cwd=str(cwd), check=True)


def ignore_runtime_artifacts(_directory: str, names: list[str]) -> set[str]:
    return {name for name in names if name in EXCLUDED_RESOURCE_NAMES or name.endswith((".pyc", ".pyo"))}


def copy_runtime_resources(resources_dir: Path) -> None:
    for directory in RESOURCE_DIRS:
        shutil.copytree(ROOT / directory, resources_dir / directory, ignore=ignore_runtime_artifacts)
    for filename in RESOURCE_FILES:
        source = ROOT / filename
        if source.exists():
            shutil.copy2(source, resources_dir / filename)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build and package Hermes Fleet Control.app")
    parser.add_argument("--configuration", choices=("debug", "release"), default="release")
    parser.add_argument("--install", action="store_true", help="Copy the packaged app to /Applications")
    parser.add_argument("--zip", action="store_true", help="Create a distributable zip in dist/")
    return parser.parse_args()


def package_app(configuration: str) -> Path:
    run(["xcrun", "swift", "build", "-c", configuration], PACKAGE)
    binary = PACKAGE / ".build" / configuration / EXECUTABLE_NAME
    if not binary.exists():
        raise FileNotFoundError(binary)

    if APP.exists():
        shutil.rmtree(APP)
    macos_dir = APP / "Contents" / "MacOS"
    resources_dir = APP / "Contents" / "Resources"
    macos_dir.mkdir(parents=True)
    resources_dir.mkdir(parents=True)

    shutil.copy2(binary, macos_dir / EXECUTABLE_NAME)
    copy_runtime_resources(resources_dir)
    icon_source = ROOT / ICON_SOURCE
    if not icon_source.exists():
        raise FileNotFoundError(f"missing app icon; run scripts/generate_app_icon.py: {icon_source}")
    shutil.copy2(icon_source, resources_dir / "HermesFleetControl.icns")
    plist = {
        "CFBundleDisplayName": "Hermes Fleet Control",
        "CFBundleExecutable": EXECUTABLE_NAME,
        "CFBundleIconFile": "HermesFleetControl",
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
    return APP


def install_app(app: Path) -> Path:
    destination = Path("/Applications") / app.name
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(app, destination, symlinks=True)
    subprocess.run(["xattr", "-dr", "com.apple.quarantine", str(destination)], check=False)
    return destination


def create_zip(app: Path) -> Path:
    archive = DIST / "HermesFleetControl-macOS.zip"
    if archive.exists():
        archive.unlink()
    run(["ditto", "-c", "-k", "--sequesterRsrc", "--keepParent", str(app), str(archive)], ROOT)
    return archive


def main() -> int:
    args = parse_args()
    app = package_app(args.configuration)
    print(app)
    if args.zip:
        print(create_zip(app))
    if args.install:
        print(install_app(app))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
