from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from typing import Any

from .local_mappings import profile_override

PROFILE_MARKERS = ("config.yaml", ".env", "auth.json", "gateway_state.json", "SOUL.md")


def _looks_like_profile(root: Path) -> bool:
    if not root.exists() or not root.is_dir():
        return False
    if any((root / marker).exists() for marker in PROFILE_MARKERS):
        return True
    if (root / "logs" / "gateway.log").exists() or (root / "logs" / "agent.log").exists():
        return True
    return False


def _display_name(name: str) -> str:
    if name == "default":
        return "Default"
    return name.replace("-", " ").replace("_", " ").title()


def discover_profiles(hermes_home: Path, profiles_root: Path) -> list[dict[str, Any]]:
    """Discover local Hermes profiles without reading secret values.

    Hermes' default profile lives directly under ~/.hermes, while named profiles
    live under ~/.hermes/profiles/<name>. The menu bar app should work on a
    clean GitHub install before a user writes config/fleet.local.yaml, so this
    returns manifest-shaped profile entries with explicit profile_root metadata.
    """
    profiles: list[dict[str, Any]] = []
    seen: set[str] = set()

    if _looks_like_profile(hermes_home):
        profiles.append({
            "profile": "default",
            "display": "Default",
            "critical": True,
            "profile_root": str(hermes_home),
        })
        seen.add("default")

    if profiles_root.exists() and profiles_root.is_dir():
        for child in sorted(profiles_root.iterdir(), key=lambda p: p.name.lower()):
            if child.name.startswith(".") or child.name == "home" or not child.is_dir():
                continue
            if child.name in seen or not _looks_like_profile(child):
                continue
            profiles.append({
                "profile": child.name,
                "display": _display_name(child.name),
                "critical": True,
                "profile_root": str(child),
            })
            seen.add(child.name)
    return profiles


def _has_runtime_signal(root: Path) -> bool:
    for path in (root / "gateway_state.json", root / "logs" / "gateway.log", root / "logs" / "agent.log"):
        try:
            if path.exists() and path.stat().st_size > 0:
                return True
        except OSError:
            continue
    return False


def is_public_default_manifest(manifest: dict[str, Any]) -> bool:
    servers = manifest.get("servers")
    if not isinstance(servers, dict) or set(servers.keys()) != {"local"}:
        return False
    local = servers.get("local") or {}
    profiles = local.get("profiles")
    if not isinstance(profiles, list) or len(profiles) != 1:
        return False
    only = profiles[0]
    return isinstance(only, dict) and only.get("profile") == "default"


def _auto_manifest(hermes_home: Path, profiles_root: Path, servers: "OrderedDict[str, dict[str, Any]]", *, profiles_found: int) -> dict[str, Any]:
    return {
        "servers": dict(servers),
        "metadata": {
            "source": "auto_discovery",
            "hermes_home": str(hermes_home),
            "profiles_root": str(profiles_root),
            "profiles_found": profiles_found,
        },
    }


def auto_discovered_manifest(hermes_home: Path, profiles_root: Path, profile_map: dict[str, Any] | None = None) -> dict[str, Any] | None:
    profiles = discover_profiles(hermes_home, profiles_root)
    servers: "OrderedDict[str, dict[str, Any]]" = OrderedDict()
    if not profiles:
        return _auto_manifest(hermes_home, profiles_root, servers, profiles_found=0)
    def add_profile(server_key: str, server_display: str, profile: dict[str, Any]) -> None:
        server = servers.setdefault(server_key, {"display": server_display, "profiles": []})
        server["profiles"].append(profile)

    for profile in profiles:
        name = str(profile["profile"])
        override = profile_override(profile_map or {}, name)
        if override.get("ignored") is True or override.get("status") == "ignored":
            continue
        effective = dict(profile)
        if override.get("display"):
            effective["display"] = str(override["display"])
        if override.get("enabled") is False or override.get("status") == "inactive":
            effective["status_override"] = "inactive"
            add_profile("inactive", "Inactive profiles", effective)
            continue
        if override.get("status") == "unclassified":
            effective["status_override"] = "unclassified"
            add_profile("unclassified", "Unclassified profiles", effective)
            continue
        if override.get("server"):
            add_profile(str(override["server"]), str(override.get("server_display") or override["server"]), effective)
            continue
        if name == "default" or not _has_runtime_signal(Path(str(profile.get("profile_root", ""))).expanduser()):
            effective["status_override"] = "unclassified"
            add_profile("unclassified", "Unclassified profiles", effective)
        else:
            add_profile("detected", "Auto-detected Hermes profiles", effective)

    return _auto_manifest(hermes_home, profiles_root, servers, profiles_found=len(profiles))
