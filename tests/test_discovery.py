import json
import subprocess
import sys

from control.discovery import auto_discovered_manifest, discover_profiles, is_public_default_manifest


def test_discover_profiles_includes_default_and_named_profiles(tmp_path):
    hermes_home = tmp_path / ".hermes"
    profiles_root = hermes_home / "profiles"
    (hermes_home / "logs").mkdir(parents=True)
    (hermes_home / "config.yaml").write_text("model: {}\n", encoding="utf-8")
    for name in ["alpha", "beta_team"]:
        root = profiles_root / name
        root.mkdir(parents=True)
        (root / "config.yaml").write_text("model: {}\n", encoding="utf-8")

    profiles = discover_profiles(hermes_home, profiles_root)

    assert [p["profile"] for p in profiles] == ["default", "alpha", "beta_team"]
    assert profiles[0]["profile_root"] == str(hermes_home)
    assert profiles[1]["profile_root"] == str(profiles_root / "alpha")


def test_auto_discovered_manifest_shape(tmp_path):
    hermes_home = tmp_path / ".hermes"
    profile = hermes_home / "profiles" / "worker"
    profile.mkdir(parents=True)
    (profile / "config.yaml").write_text("model: {}\n", encoding="utf-8")

    manifest = auto_discovered_manifest(hermes_home, hermes_home / "profiles")

    assert manifest is not None
    assert list(manifest["servers"].keys()) == ["detected"]
    assert manifest["servers"]["detected"]["display"] == "Auto-detected Hermes profiles"
    assert manifest["servers"]["detected"]["profiles"][0]["profile"] == "worker"


def test_public_default_manifest_detection():
    manifest = {"servers": {"local": {"profiles": [{"profile": "default", "display": "Default"}]}}}
    assert is_public_default_manifest(manifest) is True
    assert is_public_default_manifest({"servers": {"team": {"profiles": [{"profile": "default"}]}}}) is False


def test_status_auto_discovers_when_public_manifest_has_no_local_override(tmp_path):
    project = tmp_path / "project"
    config = project / "config"
    config.mkdir(parents=True)
    manifest = config / "fleet.yaml"
    manifest.write_text("servers:\n  local:\n    display: Local Hermes profiles\n    profiles:\n      - profile: default\n        display: Default\n        critical: true\n", encoding="utf-8")

    hermes_home = tmp_path / ".hermes"
    profiles_root = hermes_home / "profiles"
    worker = profiles_root / "worker"
    (worker / "logs").mkdir(parents=True)
    (worker / "config.yaml").write_text("model: {}\n", encoding="utf-8")
    (worker / "gateway_state.json").write_text(json.dumps({
        "gateway_state": "running",
        "active_agents": 0,
        "platforms": {"discord": {"status": "connected"}},
    }), encoding="utf-8")
    (worker / "logs" / "gateway.log").write_text("2026-06-09 11:18:15 INFO gateway.run: Gateway running with 1 platform(s)\n", encoding="utf-8")

    result = subprocess.run([
        sys.executable, "control/fleetctl.py", "status", "--json", "--manifest", str(manifest),
        "--profiles-root", str(profiles_root), "--skip-network", "--skip-auth"
    ], cwd=".", text=True, capture_output=True, check=True, env={"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "HOME": str(tmp_path), "HERMES_HOME": str(hermes_home), "HERMES_FLEET_ROOT": str(project)})

    data = json.loads(result.stdout)
    assert data["manifest_source"] == "auto_discovery"
    assert data["servers"][0]["key"] == "detected"
    assert data["servers"][0]["profiles"][0]["profile"] == "worker"
    assert data["servers"][0]["profiles"][0]["status"] == "healthy"


def test_status_no_auto_discover_preserves_public_manifest(tmp_path):
    manifest = tmp_path / "fleet.yaml"
    manifest.write_text("servers:\n  local:\n    display: Local Hermes profiles\n    profiles:\n      - profile: default\n        display: Default\n        critical: true\n", encoding="utf-8")
    hermes_home = tmp_path / ".hermes"
    (hermes_home / "profiles" / "worker").mkdir(parents=True)
    (hermes_home / "profiles" / "worker" / "config.yaml").write_text("model: {}\n", encoding="utf-8")

    result = subprocess.run([
        sys.executable, "control/fleetctl.py", "status", "--json", "--manifest", str(manifest),
        "--profiles-root", str(hermes_home / "profiles"), "--skip-network", "--skip-auth", "--no-auto-discover"
    ], text=True, capture_output=True, check=True, env={"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "HOME": str(tmp_path), "HERMES_HOME": str(hermes_home)})

    data = json.loads(result.stdout)
    assert data["manifest_source"] == "manifest"
    assert data["servers"][0]["key"] == "local"
    assert data["servers"][0]["profiles"][0]["profile"] == "default"
