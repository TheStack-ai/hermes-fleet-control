import json
import subprocess
import sys


def make_degraded_fixture(tmp_path):
    fixture_root = tmp_path / "profiles"
    profile = fixture_root / "beta"
    (profile / "logs").mkdir(parents=True)
    (profile / "gateway_state.json").write_text(json.dumps({
        "gateway_state": "running",
        "active_agents": 0,
        "platforms": {"discord": {"status": "connected"}},
    }), encoding="utf-8")
    (profile / "logs" / "agent.log").write_text(
        "2026-06-09 11:00:00 INFO gateway.run: ✓ discord connected\n"
        "2026-06-09 11:08:52 ERROR discord.client: Attempting a reconnect in 949.75s\n",
        encoding="utf-8",
    )
    manifest = tmp_path / "fleet.yaml"
    manifest.write_text(
        "servers:\n  team:\n    display: Team\n    profiles:\n      - profile: beta\n        display: Beta\n        critical: true\n",
        encoding="utf-8",
    )
    return fixture_root, manifest


def test_watchdog_dry_run_plans_degraded_only_reconnect(tmp_path):
    fixture_root, manifest = make_degraded_fixture(tmp_path)
    result = subprocess.run([
        sys.executable,
        "control/fleetctl.py",
        "watchdog",
        "--group", "team",
        "--policy", "dry-run",
        "--json",
        "--manifest", str(manifest),
        "--profiles-root", str(fixture_root),
        "--skip-network",
        "--skip-auth",
    ], text=True, capture_output=True, check=True)

    data = json.loads(result.stdout)
    assert data["ok"] is True
    assert data["watchdog"]["policy"] == "dry-run"
    assert data["watchdog"]["actions"][0]["plan"]["targets"] == ["beta"]
    assert data["watchdog"]["actions"][0]["plan"]["degraded_only"] is True
    assert data["watchdog"]["actions"][0]["dry_run"] is True


def test_watchdog_auto_noops_when_no_degraded_targets(tmp_path):
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
        sys.executable,
        "control/fleetctl.py",
        "watchdog",
        "--group", "team",
        "--policy", "auto",
        "--json",
        "--manifest", str(manifest),
        "--profiles-root", str(fixture_root),
        "--skip-network",
        "--skip-auth",
    ], text=True, capture_output=True, check=True)

    data = json.loads(result.stdout)
    assert data["ok"] is True
    assert data["watchdog"]["actions"] == []
    assert data["watchdog"]["message"] == "no degraded profiles matched; no gateway action planned"
