import json
import subprocess
import sys


def test_action_command_with_degraded_only_targets_only_degraded_profiles(tmp_path):
    fixture_root = tmp_path / "profiles"
    healthy = fixture_root / "alpha"
    degraded = fixture_root / "beta"
    for profile in [healthy, degraded]:
        (profile / "logs").mkdir(parents=True)
        (profile / "gateway_state.json").write_text(json.dumps({
            "gateway_state": "running",
            "active_agents": 0,
            "platforms": {"discord": {"status": "connected"}},
        }), encoding="utf-8")
    (healthy / "logs" / "agent.log").write_text("2026-06-09 11:18:15 INFO gateway.run: ✓ discord connected\n", encoding="utf-8")
    (degraded / "logs" / "agent.log").write_text(
        "2026-06-09 11:00:00 INFO gateway.run: ✓ discord connected\n"
        "2026-06-09 11:08:52 ERROR discord.client: Attempting a reconnect in 949.75s\n",
        encoding="utf-8",
    )
    manifest = tmp_path / "fleet.yaml"
    manifest.write_text("servers:\n  team:\n    display: Team\n    profiles:\n      - profile: alpha\n        display: Alpha\n        critical: true\n      - profile: beta\n        display: Beta\n        critical: true\n", encoding="utf-8")

    result = subprocess.run([
        sys.executable, "control/fleetctl.py", "reconnect", "--group", "team", "--degraded-only", "--safe", "--dry-run", "--json", "--manifest", str(manifest), "--profiles-root", str(fixture_root), "--skip-network"
    ], text=True, capture_output=True, check=True)

    data = json.loads(result.stdout)
    assert data["ok"] is True
    assert data["plan"]["targets"] == ["beta"]


def test_action_command_accepts_group_dry_run_alias(tmp_path):
    fixture_root = tmp_path / "profiles"
    for name in ["alpha", "beta"]:
        profile = fixture_root / name
        (profile / "logs").mkdir(parents=True)
        (profile / "gateway_state.json").write_text(json.dumps({
            "gateway_state": "running",
            "active_agents": 0,
            "platforms": {"discord": {"status": "connected"}},
        }), encoding="utf-8")
        (profile / "logs" / "agent.log").write_text("2026-06-09 11:18:15 INFO gateway.run: ✓ discord connected\n", encoding="utf-8")
    manifest = tmp_path / "fleet.yaml"
    manifest.write_text("servers:\n  team:\n    display: Team\n    profiles:\n      - profile: alpha\n        display: Alpha\n        critical: true\n      - profile: beta\n        display: Beta\n        critical: true\n", encoding="utf-8")

    result = subprocess.run([
        sys.executable, "control/fleetctl.py", "reconnect", "--group", "team", "--safe", "--dry-run", "--json", "--manifest", str(manifest), "--profiles-root", str(fixture_root), "--skip-network"
    ], text=True, capture_output=True, check=True)

    data = json.loads(result.stdout)
    assert data["ok"] is True
    assert data["dry_run"] is True
    assert data["plan"]["targets"] == ["alpha", "beta"]


def test_live_degraded_only_with_no_degraded_profiles_is_noop(tmp_path):
    fixture_root = tmp_path / "profiles"
    profile = fixture_root / "beta"
    (profile / "logs").mkdir(parents=True)
    (profile / "gateway_state.json").write_text(json.dumps({
        "gateway_state": "running",
        "active_agents": 0,
        "platforms": {"discord": {"status": "connected"}},
    }), encoding="utf-8")
    (profile / "logs" / "agent.log").write_text("2026-06-09 11:18:15 INFO gateway.run: ✓ discord connected\n", encoding="utf-8")
    manifest = tmp_path / "fleet.yaml"
    manifest.write_text("servers:\n  team:\n    display: Team\n    profiles:\n      - profile: beta\n        display: Beta\n        critical: true\n", encoding="utf-8")

    result = subprocess.run([
        sys.executable, "control/fleetctl.py", "reconnect", "--group", "team", "--degraded-only", "--safe", "--json", "--manifest", str(manifest), "--profiles-root", str(fixture_root), "--skip-network", "--skip-auth"
    ], text=True, capture_output=True, check=True)

    data = json.loads(result.stdout)
    assert data["ok"] is True
    assert data["dry_run"] is False
    assert data["plan"]["targets"] == []
    assert data["plan"]["command"] == []


def test_status_command_emits_redacted_snapshot_for_fixture(tmp_path):
    fixture_root = tmp_path / "profiles"
    profile = fixture_root / "beta"
    (profile / "logs").mkdir(parents=True)
    (profile / "gateway_state.json").write_text(json.dumps({
        "gateway_state": "running",
        "active_agents": 0,
        "platforms": {"discord": {"status": "connected"}},
    }), encoding="utf-8")
    (profile / "logs" / "agent.log").write_text("2026-06-09 11:18:15 INFO gateway.run: ✓ discord connected\n", encoding="utf-8")
    manifest = tmp_path / "fleet.yaml"
    manifest.write_text("servers:\n  team:\n    display: Team\n    profiles:\n      - profile: beta\n        display: Beta\n        critical: true\n", encoding="utf-8")

    result = subprocess.run([
        sys.executable, "control/fleetctl.py", "status", "--json", "--manifest", str(manifest), "--profiles-root", str(fixture_root), "--skip-network"
    ], text=True, capture_output=True, check=True)

    data = json.loads(result.stdout)
    assert data["ok"] is True
    assert data["auth_health"]["metadata_only"] is True
    assert data["auth_health"]["codex_openai"]["status"] in {"present", "missing"}
    assert data["servers"][0]["profiles"][0]["status"] == "healthy"
    assert data["servers"][0]["profiles"][0]["auth"]["metadata_only"] is True
    assert "123456789012345678" not in result.stdout
