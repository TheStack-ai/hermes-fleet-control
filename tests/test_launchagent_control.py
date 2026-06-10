import json
import subprocess
import sys


def test_fleetctl_launchagent_status_reports_plist_metadata(tmp_path):
    plist = tmp_path / "agent.plist"
    result = subprocess.run([
        sys.executable,
        "control/fleetctl.py",
        "launchagent",
        "status",
        "--json",
        "--plist", str(plist),
    ], text=True, capture_output=True, check=True)

    data = json.loads(result.stdout)
    assert data["ok"] is True
    assert data["launchagent"]["installed"] is False
    assert data["launchagent"]["enabled"] is False
    assert data["launchagent"]["label"] == "ai.hermes.fleet-control"


def test_fleetctl_launchagent_write_creates_plist_without_bootstrap(tmp_path):
    plist = tmp_path / "agent.plist"
    result = subprocess.run([
        sys.executable,
        "control/fleetctl.py",
        "launchagent",
        "write",
        "--json",
        "--plist", str(plist),
        "--no-bootstrap",
    ], text=True, capture_output=True, check=True)

    data = json.loads(result.stdout)
    assert data["ok"] is True
    assert data["launchagent"]["installed"] is True
    assert plist.exists()
