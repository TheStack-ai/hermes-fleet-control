import json

from control.auth_health import build_auth_health, inspect_env_auth


def test_inspect_env_auth_reports_key_presence_without_values(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("OPENROUTER_API_KEY=sk-redacted\nANTHROPIC_API_KEY=\n", encoding="utf-8")

    health = inspect_env_auth("openrouter", ["OPENROUTER_API_KEY"], [env_file])
    serialized = json.dumps(health, ensure_ascii=False)

    assert health["provider"] == "openrouter"
    assert health["status"] == "present"
    assert health["key_present"] is True
    assert health["metadata_only"] is True
    assert "sk-redacted" not in serialized


def test_build_auth_health_includes_common_provider_metadata(tmp_path):
    codex = tmp_path / "auth.json"
    codex.write_text('{"auth_mode":"chatgpt","tokens":{"access_token":"a"}}', encoding="utf-8")
    env_file = tmp_path / ".env"
    env_file.write_text("OPENROUTER_API_KEY=value\nGEMINI_API_KEY=value2\n", encoding="utf-8")

    health = build_auth_health(codex, env_paths=[env_file])

    assert health["metadata_only"] is True
    assert health["codex_openai"]["tokens_present"] is True
    assert health["providers"]["openrouter"]["key_present"] is True
    assert health["providers"]["google_gemini"]["key_present"] is True
    assert health["providers"]["anthropic"]["key_present"] is False
