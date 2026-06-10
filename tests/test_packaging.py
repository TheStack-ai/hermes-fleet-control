import plistlib
import subprocess
import sys
from pathlib import Path

from scripts.package_app import copy_runtime_resources


def test_copy_runtime_resources_bundles_cli_without_caches(tmp_path):
    resources = tmp_path / "Resources"
    resources.mkdir()

    copy_runtime_resources(resources)

    assert (resources / "control" / "fleetctl.py").exists()
    assert (resources / "scripts" / "launchagent.py").exists()
    assert (resources / "config" / "fleet.yaml").exists()
    assert not list(resources.rglob("__pycache__"))
    assert not list(resources.rglob("*.pyc"))


def test_generated_icon_assets_exist_for_release_packaging():
    icon = Path("assets/icons/HermesFleetControl.icns")
    preview = Path("assets/icons/HermesFleetControl-1024.png")

    assert icon.exists()
    assert preview.exists()
    assert icon.stat().st_size > 10_000
    assert preview.stat().st_size > 10_000


def test_launchagent_honors_packaged_app_path_override(tmp_path):
    app_path = tmp_path / "HermesFleetControl.app"
    app_path.mkdir()

    result = subprocess.run(
        [sys.executable, "scripts/launchagent.py", "print"],
        text=True,
        capture_output=True,
        check=True,
        env={"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "HERMES_FLEET_APP_PATH": str(app_path)},
    )

    plist = plistlib.loads(result.stdout.encode("utf-8"))
    assert plist["ProgramArguments"] == ["/usr/bin/open", str(app_path)]


def test_help_section_keeps_diagnostics_source_and_sponsor_visible():
    menu = Path("app/HermesFleetControl/Sources/HermesFleetControl/MenuViews.swift").read_text()
    funding = Path(".github/FUNDING.yml").read_text()

    for label in ["Guide", "Logs", "Profiles", "Copy", "Source", "Sponsor"]:
        assert f'ActionChip("{label}"' in menu
    assert "sponsorURL" in menu
    assert "github: [TheStack-ai]" in funding
    assert "github.com/TheStack-ai/hermes-fleet-control" in menu


def test_readme_has_public_landing_assets_and_contribution_paths():
    readme = Path("README.md").read_text()

    assert "assets/readme/hermes-fleet-control-hero.png" in readme
    assert "Search / AI summary" in readme
    assert "CONTRIBUTING.md" in readme
    assert "SECURITY.md" in readme
    blocked_terms = ["Developer" + " ID", "Apple" + " Developer"]
    for term in blocked_terms:
        assert term not in readme
    assert Path("assets/readme/hermes-fleet-control-hero.png").stat().st_size > 100_000
    assert Path("CONTRIBUTING.md").exists()
    assert Path("SECURITY.md").exists()
    assert Path(".github/PULL_REQUEST_TEMPLATE.md").exists()
    assert Path(".github/workflows/ci.yml").exists()
