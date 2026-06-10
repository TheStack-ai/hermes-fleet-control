from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterable

from .paths import codex_auth_file, default_env_paths

DEFAULT_CODEX_AUTH = codex_auth_file()
PROVIDER_ENV_KEYS = {
    "openrouter": ["OPENROUTER_API_KEY"],
    "anthropic": ["ANTHROPIC_API_KEY"],
    "google_gemini": ["GOOGLE_API_KEY", "GEMINI_API_KEY"],
    "xai": ["XAI_API_KEY"],
    "deepseek": ["DEEPSEEK_API_KEY"],
}
CODEX_AUTH_PROVIDER_KEYS = ("openai-codex", "codex_openai")


def _extract_profile_codex_provider(data: dict[str, Any]) -> dict[str, Any]:
    providers = data.get("providers")
    if isinstance(providers, dict):
        for key in CODEX_AUTH_PROVIDER_KEYS:
            provider = providers.get(key)
            if isinstance(provider, dict):
                return provider
    for key in CODEX_AUTH_PROVIDER_KEYS:
        provider = data.get(key)
        if isinstance(provider, dict):
            return provider
    return {}


def inspect_profile_codex_auth(profile_home: Path | str) -> dict[str, Any]:
    """Inspect profile-local OpenAI-Codex auth metadata without token values."""
    profile_path = Path(profile_home)
    auth_path = profile_path / "auth.json"
    base: dict[str, Any] = {
        "provider": "openai-codex",
        "status": "missing",
        "auth_file_present": auth_path.exists(),
        "provider_present": False,
        "tokens_present": False,
        "access_token_present": False,
        "refresh_token_present": False,
        "last_auth_error_code": None,
        "relogin_required": False,
        "metadata_only": True,
    }
    if not auth_path.exists():
        return base
    try:
        data = json.loads(auth_path.read_text(encoding="utf-8"))
    except Exception as exc:
        base.update({"status": "unreadable", "error_type": type(exc).__name__})
        return base
    if not isinstance(data, dict):
        base.update({"status": "invalid"})
        return base
    provider = _extract_profile_codex_provider(data)
    tokens = provider.get("tokens") if isinstance(provider, dict) else None
    last_error = provider.get("last_auth_error") if isinstance(provider, dict) else None
    error_code = None
    if isinstance(last_error, dict):
        error_code = last_error.get("code") or last_error.get("error") or last_error.get("type")
    has_relogin_error = bool(error_code in {"refresh_token_reused", "token_expired", "invalid_grant"})
    tokens_present = isinstance(tokens, dict) and bool(tokens)
    access_present = isinstance(tokens, dict) and bool(tokens.get("access_token"))
    refresh_present = isinstance(tokens, dict) and bool(tokens.get("refresh_token"))
    token_pair_present = access_present and refresh_present
    # A stale last_auth_error can remain after a later successful login. Treat it
    # as urgent only when the usable token pair is missing; otherwise surface it
    # as advisory metadata instead of saying the Discord bot/profile is offline.
    if bool(provider) and (not tokens_present or not token_pair_present):
        status = "relogin_required"
    elif has_relogin_error and token_pair_present:
        status = "stale_error"
    elif tokens_present:
        status = "present"
    elif provider:
        status = "incomplete"
    else:
        status = "missing"
    base.update({
        "status": status,
        "provider_present": bool(provider),
        "tokens_present": tokens_present,
        "access_token_present": access_present,
        "refresh_token_present": refresh_present,
        "last_auth_error_code": error_code,
        "relogin_required": status == "relogin_required",
    })
    return base


def inspect_codex_auth(path: Path | str = DEFAULT_CODEX_AUTH) -> dict[str, Any]:
    p = Path(path)
    base: dict[str, Any] = {
        "provider": "codex_openai",
        "path": str(p),
        "status": "missing",
        "auth_mode_present": False,
        "tokens_present": False,
        "api_key_present": False,
        "last_refresh_present": False,
        "metadata_only": True,
    }
    if not p.exists():
        return base
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        base.update({"status": "unreadable", "error_type": type(exc).__name__})
        return base
    if not isinstance(data, dict):
        base.update({"status": "invalid"})
        return base
    tokens = data.get("tokens")
    api_key = data.get("OPENAI_API_KEY")
    base.update({
        "status": "present",
        "auth_mode_present": bool(data.get("auth_mode")),
        "tokens_present": isinstance(tokens, dict) and bool(tokens),
        "api_key_present": bool(api_key),
        "last_refresh_present": bool(data.get("last_refresh")),
        "top_level_keys_present": sorted(str(k) for k in data.keys()),
    })
    return base


def _env_key_present_in_file(key: str, path: Path) -> bool:
    if not path.exists():
        return False
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return False
    prefix = f"{key}="
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or not stripped.startswith(prefix):
            continue
        value = stripped[len(prefix):].strip().strip('"').strip("'")
        return bool(value)
    return False


def inspect_env_auth(provider: str, env_keys: Iterable[str], env_paths: Iterable[Path | str] | None = None) -> dict[str, Any]:
    paths = [Path(p) for p in (env_paths or default_env_paths())]
    keys = list(env_keys)
    env_present = any(bool(os.environ.get(key)) for key in keys)
    file_present = any(_env_key_present_in_file(key, path) for key in keys for path in paths)
    return {
        "provider": provider,
        "status": "present" if env_present or file_present else "missing",
        "key_present": bool(env_present or file_present),
        "env_keys_checked": keys,
        "source_files_present": [str(path) for path in paths if path.exists()],
        "metadata_only": True,
    }


def build_auth_health(path: Path | str = DEFAULT_CODEX_AUTH, env_paths: Iterable[Path | str] | None = None) -> dict[str, Any]:
    codex = inspect_codex_auth(path)
    providers = {
        provider: inspect_env_auth(provider, keys, env_paths)
        for provider, keys in PROVIDER_ENV_KEYS.items()
    }
    return {
        "metadata_only": True,
        "codex_openai": codex,
        "providers": providers,
    }
