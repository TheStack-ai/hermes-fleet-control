import json
from pathlib import Path

from control.auth_health import inspect_codex_auth, inspect_profile_codex_auth


def test_inspect_codex_auth_reports_metadata_only(tmp_path):
    auth = tmp_path / "auth.json"
    auth.write_text(json.dumps({
        "auth_mode": "chatgpt",
        "OPENAI_API_KEY": None,
        "tokens": {"access_token": "value-a", "refresh_token": "value-b"},
        "last_refresh": "2026-06-09T12:00:00Z",
    }), encoding="utf-8")

    health = inspect_codex_auth(auth)
    serialized = json.dumps(health, ensure_ascii=False)

    assert health["provider"] == "codex_openai"
    assert health["status"] == "present"
    assert health["auth_mode_present"] is True
    assert health["tokens_present"] is True
    assert health["api_key_present"] is False
    assert health["last_refresh_present"] is True
    assert "value-a" not in serialized
    assert "value-b" not in serialized


def test_inspect_codex_auth_missing_file_is_metadata_only_missing(tmp_path):
    health = inspect_codex_auth(tmp_path / "missing.json")

    assert health["status"] == "missing"
    assert health["tokens_present"] is False


def test_inspect_profile_codex_auth_reports_relogin_without_values(tmp_path):
    auth = tmp_path / "auth.json"
    auth.write_text(json.dumps({
        "providers": {
            "openai-codex": {
                "tokens": {},
                "last_auth_error": {"code": "refresh_token_reused", "message": "do not expose token details"},
            }
        }
    }), encoding="utf-8")

    health = inspect_profile_codex_auth(tmp_path)
    serialized = json.dumps(health, ensure_ascii=False)

    assert health["provider"] == "openai-codex"
    assert health["status"] == "relogin_required"
    assert health["relogin_required"] is True
    assert health["last_auth_error_code"] == "refresh_token_reused"
    assert "do not expose token details" not in serialized


def test_inspect_profile_codex_auth_reports_present_without_token_values(tmp_path):
    auth = tmp_path / "auth.json"
    auth.write_text(json.dumps({
        "providers": {
            "openai-codex": {
                "tokens": {"access_token": "secret-a", "refresh_token": "secret-b"},
            }
        }
    }), encoding="utf-8")

    health = inspect_profile_codex_auth(tmp_path)
    serialized = json.dumps(health, ensure_ascii=False)

    assert health["status"] == "present"
    assert health["tokens_present"] is True
    assert health["access_token_present"] is True
    assert health["refresh_token_present"] is True
    assert "secret-a" not in serialized
    assert "secret-b" not in serialized


def test_inspect_profile_codex_auth_treats_error_with_tokens_as_advisory(tmp_path):
    auth = tmp_path / "auth.json"
    auth.write_text(json.dumps({
        "providers": {
            "openai-codex": {
                "tokens": {"access_token": "secret-a", "refresh_token": "secret-b"},
                "last_auth_error": {"code": "refresh_token_reused", "message": "old failure"},
            }
        }
    }), encoding="utf-8")

    health = inspect_profile_codex_auth(tmp_path)
    serialized = json.dumps(health, ensure_ascii=False)

    assert health["status"] == "stale_error"
    assert health["relogin_required"] is False
    assert health["tokens_present"] is True
    assert health["access_token_present"] is True
    assert health["refresh_token_present"] is True
    assert health["last_auth_error_code"] == "refresh_token_reused"
    assert "secret-a" not in serialized
    assert "secret-b" not in serialized
    assert "old failure" not in serialized
