from __future__ import annotations

import os
import platform
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def repo_root() -> Path:
    override = os.environ.get("HERMES_FLEET_ROOT")
    return Path(override).expanduser() if override else ROOT


def user_home() -> Path:
    override = os.environ.get("HERMES_FLEET_USER_HOME")
    if override:
        return Path(override).expanduser()
    home = Path.home().expanduser()
    # Hermes profile shells can set HOME to
    # ~/.hermes/profiles/<profile>/home. Fleet Control is an operator app and
    # should inspect the user's real profile fleet by default, not a nested
    # profile-local home directory.
    if home.name == "home" and home.parent.parent.name == "profiles" and home.parent.parent.parent.name == ".hermes":
        return home.parent.parent.parent.parent
    return home


def hermes_home() -> Path:
    return Path(os.environ.get("HERMES_HOME") or (user_home() / ".hermes")).expanduser()


def profiles_root() -> Path:
    override = os.environ.get("HERMES_PROFILES_ROOT")
    if override:
        return Path(override).expanduser()
    home = hermes_home()
    # If HERMES_HOME already points at a concrete profile
    # (~/.hermes/profiles/<profile>), the fleet root is its parent. This avoids
    # accidentally checking ~/.hermes/profiles/<profile>/profiles/<name> and
    # marking every real profile as unknown/missing.
    if home.parent.name == "profiles" and (home / "config.yaml").exists():
        return home.parent
    return (home / "profiles").expanduser()


def codex_auth_file() -> Path:
    return Path(os.environ.get("CODEX_AUTH_FILE") or (user_home() / ".codex" / "auth.json")).expanduser()


def default_env_paths() -> list[Path]:
    raw = os.environ.get("HERMES_FLEET_ENV_FILES")
    if raw:
        return [Path(part).expanduser() for part in raw.split(os.pathsep) if part]
    paths: list[Path] = []
    profile = os.environ.get("HERMES_PROFILE")
    if profile:
        paths.append(profiles_root() / profile / ".env")
    paths.append(hermes_home() / ".env")
    return paths


def default_manifest_path() -> Path:
    override = os.environ.get("HERMES_FLEET_MANIFEST")
    if override:
        return Path(override).expanduser()
    local = repo_root() / "config" / "fleet.local.yaml"
    if local.exists():
        return local
    return repo_root() / "config" / "fleet.yaml"


def hermes_executable() -> str:
    override = os.environ.get("HERMES_BIN")
    if override:
        return str(Path(override).expanduser())
    found = shutil.which("hermes")
    if found:
        return found
    suffix = "Scripts/hermes.exe" if platform.system() == "Windows" else "venv/bin/hermes"
    candidate = hermes_home() / "hermes-agent" / suffix
    return str(candidate)


def python_executable() -> str:
    return os.environ.get("HERMES_FLEET_PYTHON") or sys.executable


def auth_repair_script_dir() -> Path:
    if os.environ.get("HERMES_FLEET_AUTH_REPAIR_DIR"):
        return Path(os.environ["HERMES_FLEET_AUTH_REPAIR_DIR"]).expanduser()
    if os.environ.get("HERMES_FLEET_RUNTIME_DIR"):
        return Path(os.environ["HERMES_FLEET_RUNTIME_DIR"]).expanduser() / "auth-repair"
    return repo_root() / "runtime" / "auth-repair"


def safe_restart_script() -> Path | None:
    override = os.environ.get("HERMES_SAFE_RESTART_SCRIPT")
    return Path(override).expanduser() if override else None


def profile_map_path() -> Path:
    override = os.environ.get("HERMES_FLEET_PROFILE_MAP")
    if override:
        return Path(override).expanduser()
    if platform.system() == "Darwin":
        return user_home() / "Library" / "Application Support" / "HermesFleetControl" / "profile-map.json"
    if platform.system() == "Windows":
        base = os.environ.get("APPDATA")
        if base:
            return Path(base) / "HermesFleetControl" / "profile-map.json"
    return user_home() / ".config" / "hermes-fleet-control" / "profile-map.json"


def launch_label() -> str:
    return os.environ.get("HERMES_FLEET_LAUNCH_LABEL") or "ai.hermes.fleet-control"


def launch_plist_path() -> Path:
    return Path(os.environ.get("HERMES_FLEET_LAUNCH_PLIST") or (user_home() / "Library" / "LaunchAgents" / f"{launch_label()}.plist")).expanduser()
