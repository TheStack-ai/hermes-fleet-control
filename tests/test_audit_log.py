import json
import subprocess
import sys


def make_manifest(tmp_path):
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
        "servers:\n"
        "  team:\n"
        "    display: Team\n"
        "    profiles:\n"
        "      - profile: beta\n"
        "        display: Beta\n"
        "        critical: true\n",
        encoding="utf-8",
    )
    return fixture_root, manifest


def test_dry_run_action_appends_redacted_audit_entry(tmp_path):
    fixture_root, manifest = make_manifest(tmp_path)
    audit_log = tmp_path / "runtime" / "actions.jsonl"

    result = subprocess.run([
        sys.executable,
        "control/fleetctl.py",
        "reconnect",
        "--group", "team",
        "--degraded-only",
        "--safe",
        "--dry-run",
        "--json",
        "--manifest", str(manifest),
        "--profiles-root", str(fixture_root),
        "--skip-network",
        "--skip-auth",
        "--audit-log", str(audit_log),
    ], text=True, capture_output=True, check=True)

    data = json.loads(result.stdout)
    assert data["ok"] is True
    entries = [json.loads(line) for line in audit_log.read_text(encoding="utf-8").splitlines()]
    assert len(entries) == 1
    assert entries[0]["event"] == "gateway_action"
    assert entries[0]["action"] == "reconnect"
    assert entries[0]["group"] == "team"
    assert entries[0]["targets"] == ["beta"]
    assert entries[0]["dry_run"] is True
    assert entries[0]["ok"] is True
    assert "command" not in entries[0]


def test_status_includes_recent_audit_entries(tmp_path):
    fixture_root, manifest = make_manifest(tmp_path)
    audit_log = tmp_path / "runtime" / "actions.jsonl"
    audit_log.parent.mkdir(parents=True)
    audit_log.write_text(json.dumps({
        "ts": "2026-06-09T05:30:00Z",
        "event": "gateway_action",
        "action": "reconnect",
        "group": "team",
        "targets": ["beta"],
        "dry_run": False,
        "ok": True,
        "message": "executed",
    }) + "\n", encoding="utf-8")

    result = subprocess.run([
        sys.executable,
        "control/fleetctl.py",
        "status",
        "--json",
        "--manifest", str(manifest),
        "--profiles-root", str(fixture_root),
        "--skip-network",
        "--skip-auth",
        "--audit-log", str(audit_log),
    ], text=True, capture_output=True, check=True)

    data = json.loads(result.stdout)
    assert data["audit"]["last_actions"][0]["action"] == "reconnect"
    assert data["audit"]["last_actions"][0]["targets"] == ["beta"]
