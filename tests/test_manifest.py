from pathlib import Path

from control.manifest import load_manifest, all_profiles


def test_default_manifest_is_public_example_without_secret_keys():
    manifest = load_manifest(Path("config/fleet.yaml"))

    assert set(manifest["servers"]) == {"local"}
    assert all_profiles(manifest) == ["default"]
    forbidden = ["token", "secret", "cookie", "password", "api_key"]
    text = Path("config/fleet.yaml").read_text(encoding="utf-8").lower()
    assert not any(key in text for key in forbidden)
