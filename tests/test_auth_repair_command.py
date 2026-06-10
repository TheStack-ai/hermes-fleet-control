import json
import platform
import subprocess
import sys

from control.fleetctl import _terminal_command_for_auth_repair, _terminal_script, _write_terminal_command_file


def test_auth_repair_command_prepares_profile_scoped_reauth_without_opening_terminal(tmp_path):
    manifest = tmp_path / "fleet.yaml"
    manifest.write_text(
        "servers:\n"
        "  local:\n"
        "    display: Local\n"
        "    profiles:\n"
        "      - profile: default\n"
        "        display: Default\n"
        "        critical: true\n",
        encoding="utf-8",
    )

    result = subprocess.run([
        sys.executable,
        "control/fleetctl.py",
        "auth-repair",
        "--profile",
        "default",
        "--action",
        "reauth",
        "--manifest",
        str(manifest),
        "--json",
    ], text=True, capture_output=True, check=True)

    data = json.loads(result.stdout)
    assert data["ok"] is True
    assert data["profile"] == "default"
    assert data["provider"] == "openai-codex"
    assert data["opened_terminal"] is False
    assert data["command"][-5:] == ["auth", "add", "openai-codex", "--type", "oauth"]
    assert "access_token" not in result.stdout
    assert "refresh_token" not in result.stdout


def test_auth_repair_writes_executable_command_file_for_terminal(tmp_path):
    command = _terminal_command_for_auth_repair("default", "reauth")
    script = _terminal_script("default", "reauth", command)
    path = _write_terminal_command_file("default", "reauth", script, directory=tmp_path)

    expected_suffix = ".ps1" if platform.system() == "Windows" else ".command"
    assert path.suffix == expected_suffix
    assert path.name.endswith(f"-default-reauth{expected_suffix}")
    assert path.stat().st_mode & 0o111
    text = path.read_text(encoding="utf-8")
    assert "osascript" not in text
    assert "openai-codex" in text
    assert "-p default" in text or '"-p" "default"' in text
    assert "auth add openai-codex" in text or '"auth" "add" "openai-codex"' in text
    assert "access_token" not in text
    assert "refresh_token" not in text


def test_auth_repair_command_blocks_profiles_outside_manifest(tmp_path):
    manifest = tmp_path / "fleet.yaml"
    manifest.write_text("servers:\n  local:\n    display: Local\n    profiles:\n      - profile: default\n", encoding="utf-8")

    result = subprocess.run([
        sys.executable,
        "control/fleetctl.py",
        "auth-repair",
        "--profile",
        "unknown",
        "--manifest",
        str(manifest),
        "--json",
    ], text=True, capture_output=True)

    data = json.loads(result.stdout)
    assert result.returncode == 1
    assert data["ok"] is False
    assert data["error"] == "unknown_profile"


def test_auth_repair_restart_uses_safe_fleetctl_wrapper(tmp_path):
    manifest = tmp_path / "fleet.yaml"
    manifest.write_text("servers:\n  local:\n    display: Local\n    profiles:\n      - profile: default\n", encoding="utf-8")

    result = subprocess.run([
        sys.executable,
        "control/fleetctl.py",
        "auth-repair",
        "--profile",
        "default",
        "--action",
        "restart",
        "--manifest",
        str(manifest),
        "--json",
    ], text=True, capture_output=True, check=True)

    data = json.loads(result.stdout)
    command = " ".join(data["command"])
    assert "control/fleetctl.py restart --profile default --safe" in command
    assert data["opened_terminal"] is False
