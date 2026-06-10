from __future__ import annotations

from pathlib import Path
from typing import Any


def _load_with_pyyaml(path: Path) -> dict[str, Any] | None:
    try:
        import yaml  # type: ignore
    except Exception:
        return None
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("manifest root must be a mapping")
    return data


def _load_simple_manifest(path: Path) -> dict[str, Any]:
    """Tiny parser for this repo's non-secret fleet.yaml shape.

    This avoids requiring PyYAML when the menu-bar app invokes system Python.
    It intentionally supports only the manifest structure used by this project.
    """
    servers: dict[str, Any] = {}
    current_server: str | None = None
    current_profile: dict[str, Any] | None = None
    in_profiles = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()
        if indent == 2 and line.endswith(":"):
            current_server = line[:-1]
            servers[current_server] = {"profiles": []}
            current_profile = None
            in_profiles = False
        elif current_server and indent == 4 and line.startswith("display:"):
            servers[current_server]["display"] = line.split(":", 1)[1].strip()
        elif current_server and indent == 4 and line == "profiles:":
            in_profiles = True
        elif current_server and in_profiles and indent == 6 and line.startswith("- profile:"):
            current_profile = {"profile": line.split(":", 1)[1].strip()}
            servers[current_server]["profiles"].append(current_profile)
        elif current_profile is not None and indent == 8 and ":" in line:
            key, value = line.split(":", 1)
            value = value.strip()
            if value.lower() == "true":
                current_profile[key] = True
            elif value.lower() == "false":
                current_profile[key] = False
            else:
                current_profile[key] = value
    return {"servers": servers}


def load_manifest(path: Path | str) -> dict[str, Any]:
    p = Path(path)
    data = _load_with_pyyaml(p)
    if data is None:
        data = _load_simple_manifest(p)
    if "servers" not in data or not isinstance(data["servers"], dict):
        raise ValueError("manifest must contain servers mapping")
    return data


def all_profiles(manifest: dict[str, Any]) -> list[str]:
    profiles: list[str] = []
    for server in manifest.get("servers", {}).values():
        for item in server.get("profiles", []):
            profiles.append(str(item["profile"]))
    return profiles
