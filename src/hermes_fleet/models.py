"""Small serializable models for read-only fleet status."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class PlatformStatus:
    platform: str
    configured: bool
    required_keys: dict[str, bool] = field(default_factory=dict)
    config_sources: list[str] = field(default_factory=list)
    status: str = "missing"
    confidence: str = "medium"
    hints: list[str] = field(default_factory=list)


@dataclass
class GatewayRuntime:
    state: str = "unknown"
    pid: int | None = None
    supervisor: str = "unknown"


@dataclass
class ProfileStatus:
    name: str
    home: str
    has_config: bool
    has_env: bool
    platforms: list[PlatformStatus] = field(default_factory=list)
    gateway: GatewayRuntime = field(default_factory=GatewayRuntime)
    overall: str = "unknown"


@dataclass
class FleetStatus:
    schema_version: str
    hermes_home: str
    profiles: list[ProfileStatus]
    safety: dict[str, Any] = field(default_factory=lambda: {
        "secret_values_retained": False,
        "secret_values_printed": False,
        "external_side_effects": False,
        "processes_modified": False,
    })

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def path_str(path: Path) -> str:
    return str(path.expanduser())
