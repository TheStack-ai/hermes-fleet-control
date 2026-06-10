from __future__ import annotations

import json
from pathlib import Path
from typing import Any

VALID_STATES = {"managed", "unclassified", "inactive", "ignored"}


def load_profile_map(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": 1, "profiles": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"profile map is not valid JSON: {path}") from exc
    if not isinstance(data, dict):
        raise ValueError("profile map root must be an object")
    profiles = data.setdefault("profiles", {})
    if not isinstance(profiles, dict):
        raise ValueError("profile map profiles must be an object")
    data.setdefault("version", 1)
    return data


def save_profile_map(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def profile_override(mapping: dict[str, Any], profile: str) -> dict[str, Any]:
    profiles = mapping.get("profiles") if isinstance(mapping, dict) else {}
    item = profiles.get(profile, {}) if isinstance(profiles, dict) else {}
    return item if isinstance(item, dict) else {}


def upsert_profile_mapping(
    path: Path,
    profile: str,
    *,
    display: str | None = None,
    server: str | None = None,
    server_display: str | None = None,
    state: str = "managed",
) -> dict[str, Any]:
    if state not in VALID_STATES:
        raise ValueError(f"unsupported profile state: {state}")
    data = load_profile_map(path)
    profiles = data.setdefault("profiles", {})
    item: dict[str, Any] = dict(profiles.get(profile, {})) if isinstance(profiles.get(profile, {}), dict) else {}
    if display:
        item["display"] = display
    if server:
        item["server"] = server
    if server_display:
        item["server_display"] = server_display
    if state == "managed":
        item["enabled"] = True
        item.pop("status", None)
        item.pop("ignored", None)
    elif state == "unclassified":
        item["enabled"] = True
        item["status"] = "unclassified"
        item.pop("ignored", None)
    elif state == "inactive":
        item["enabled"] = False
        item["status"] = "inactive"
        item.pop("ignored", None)
    elif state == "ignored":
        item["enabled"] = False
        item["status"] = "ignored"
        item["ignored"] = True
    profiles[profile] = item
    save_profile_map(path, data)
    return data
