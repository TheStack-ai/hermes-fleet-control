"""Read-only Hermes home/profile discovery."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from .models import FleetStatus, GatewayRuntime, PlatformStatus, ProfileStatus
from .redact import is_secret_key

PLATFORM_KEY_PREFIXES = {
    "discord": ["DISCORD_"],
    "telegram": ["TELEGRAM_"],
    "slack": ["SLACK_"],
}

REQUIRED_PLATFORM_KEYS = {
    "discord": ["DISCORD_BOT_TOKEN"],
    "telegram": ["TELEGRAM_BOT_TOKEN", "TELEGRAM_ALLOWED_USERS"],
    "slack": ["SLACK_BOT_TOKEN", "SLACK_APP_TOKEN"],
}

GATEWAY_PROFILE_RE = re.compile(r"(?:hermes_cli\.main|hermes).*?(?:--profile|-p)\s+(\S+)\s+gateway\s+run", re.I)


def resolve_home(home: str | None = None) -> Path:
    if home:
        return Path(home).expanduser()
    if os.environ.get("HERMES_HOME"):
        return Path(os.environ["HERMES_HOME"]).expanduser()
    return Path.home() / ".hermes"


def scan_root(home: Path) -> Path:
    """Return the Hermes root to scan.

    Hermes profile shells often set HERMES_HOME directly to
    ~/.hermes/profiles/<name>. For fleet discovery, scan the parent Hermes root
    so sibling profiles are visible. A future --profile-home flag can opt into a
    single profile view.
    """
    if home.parent.name == "profiles" and home.parent.parent.exists():
        return home.parent.parent
    return home


def parse_env_keys(env_path: Path) -> set[str]:
    keys: set[str] = set()
    if not env_path.exists():
        return keys
    try:
        for raw in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key = line.split("=", 1)[0].strip().removeprefix("export ").strip()
            if key:
                keys.add(key)
    except OSError:
        return keys
    return keys


def read_config_sections(config_path: Path) -> set[str]:
    """Return top-level config section names without retaining config values.

    Hermes users may place credentials in config-like files. Fleet Control only
    needs to know whether sections such as `discord:`, `telegram:`, or `slack:`
    exist, so this parser intentionally keeps section names only.
    """
    sections: set[str] = set()
    if not config_path.exists():
        return sections
    try:
        with config_path.open("r", encoding="utf-8", errors="ignore") as handle:
            for raw in handle:
                if raw.startswith((" ", "\t", "#")) or ":" not in raw:
                    continue
                key = raw.split(":", 1)[0].strip()
                if key:
                    sections.add(key)
    except OSError:
        return sections
    return sections


def platform_from_config(platform: str, config_sections: set[str]) -> bool:
    return platform in config_sections


def detect_platform(platform: str, env_keys: set[str], config_sections: set[str]) -> PlatformStatus:
    required = {key: key in env_keys for key in REQUIRED_PLATFORM_KEYS[platform]}
    has_prefix = any(any(key.startswith(prefix) for prefix in PLATFORM_KEY_PREFIXES[platform]) for key in env_keys)
    has_config = platform_from_config(platform, config_sections)
    configured = has_prefix or has_config
    sources = []
    if has_prefix:
        sources.append("env_keys")
    if has_config:
        sources.append("config_yaml")

    hints: list[str] = []
    status = "missing"
    confidence = "medium"
    if configured:
        missing_required = [key for key, ok in required.items() if not ok]
        if has_prefix and missing_required:
            status = "blocked"
            hints.append("required env key(s) missing: " + ", ".join(missing_required))
        else:
            status = "configured"
            confidence = "high" if not missing_required else "medium"
            if missing_required:
                hints.append(
                    "required env key(s) not found in .env metadata; they may be stored in config, another secret source, or need setup: "
                    + ", ".join(missing_required)
                )

    if platform == "discord" and configured:
        hints.append("Discord portal intents cannot be proven locally; Message Content Intent may still need portal verification.")
    if platform == "telegram" and configured:
        hints.append("Telegram group privacy mode cannot be proven locally; check BotFather if groups are silent.")
    if platform == "slack" and configured:
        hints.append("Slack scopes/events and Messages Tab cannot be fully proven locally; use live validation later if channels are silent.")

    return PlatformStatus(
        platform=platform,
        configured=configured,
        required_keys=required,
        config_sources=sources,
        status=status,
        confidence=confidence,
        hints=hints,
    )


def enumerate_profiles(home: Path) -> list[tuple[str, Path]]:
    profiles: list[tuple[str, Path]] = []
    if (home / "config.yaml").exists() or (home / ".env").exists():
        profiles.append(("default", home))
    profiles_dir = home / "profiles"
    if profiles_dir.exists():
        for child in sorted(profiles_dir.iterdir()):
            if child.is_dir() and ((child / "config.yaml").exists() or (child / ".env").exists()):
                profiles.append((child.name, child))
    return profiles


def process_gateway_map() -> dict[str, GatewayRuntime]:
    try:
        proc = subprocess.run(
            ["/bin/ps", "-axo", "pid,command"],
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
        )
    except Exception:
        return {}
    gateways: dict[str, GatewayRuntime] = {}
    if proc.returncode != 0:
        return gateways
    for raw in proc.stdout.splitlines()[1:]:
        line = raw.strip()
        if not line:
            continue
        pid_text, _, command = line.partition(" ")
        match = GATEWAY_PROFILE_RE.search(command)
        if match and pid_text.isdigit():
            gateways[match.group(1)] = GatewayRuntime(state="running", pid=int(pid_text), supervisor="process")
    return gateways


def synthesize_overall(platforms: list[PlatformStatus], gateway: GatewayRuntime) -> str:
    configured_platforms = [p for p in platforms if p.configured]
    if not configured_platforms:
        return "missing"
    if gateway.state != "running":
        return "offline"
    if any(p.status == "blocked" for p in configured_platforms):
        return "blocked"
    return "healthy"


def collect_status(home: str | None = None) -> FleetStatus:
    requested_home = resolve_home(home)
    resolved_home = scan_root(requested_home)
    gateways = process_gateway_map()
    profiles: list[ProfileStatus] = []
    for name, profile_home in enumerate_profiles(resolved_home):
        config_path = profile_home / "config.yaml"
        env_path = profile_home / ".env"
        env_keys = parse_env_keys(env_path)
        config_sections = read_config_sections(config_path)
        platforms = [detect_platform(platform, env_keys, config_sections) for platform in ("discord", "telegram", "slack")]
        gateway = gateways.get(name, GatewayRuntime(state="stopped", supervisor="unknown"))
        profiles.append(
            ProfileStatus(
                name=name,
                home=str(profile_home),
                has_config=config_path.exists(),
                has_env=env_path.exists(),
                platforms=platforms,
                gateway=gateway,
                overall=synthesize_overall(platforms, gateway),
            )
        )
    return FleetStatus(schema_version="0.1", hermes_home=str(resolved_home), profiles=profiles)


def safe_env_key_summary(env_path: Path) -> dict[str, str]:
    """Expose only key presence categories; useful for future doctor output."""
    keys = parse_env_keys(env_path)
    return {key: ("secret_present" if is_secret_key(key) else "present") for key in sorted(keys)}
