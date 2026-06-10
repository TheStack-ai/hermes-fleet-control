from pathlib import Path

from control import paths


def test_profiles_root_uses_parent_when_hermes_home_is_profile(monkeypatch, tmp_path):
    hermes_root = tmp_path / ".hermes"
    profile_home = hermes_root / "profiles" / "worker"
    profile_home.mkdir(parents=True)
    (profile_home / "config.yaml").write_text("model: {}\n", encoding="utf-8")

    monkeypatch.setenv("HERMES_HOME", str(profile_home))
    monkeypatch.delenv("HERMES_PROFILES_ROOT", raising=False)

    assert paths.profiles_root() == hermes_root / "profiles"


def test_user_home_recovers_from_profile_local_home(monkeypatch, tmp_path):
    real_home = tmp_path / "user"
    profile_local_home = real_home / ".hermes" / "profiles" / "worker" / "home"
    profile_local_home.mkdir(parents=True)

    monkeypatch.setattr(Path, "home", lambda: profile_local_home)
    monkeypatch.delenv("HERMES_FLEET_USER_HOME", raising=False)

    assert paths.user_home() == real_home


def test_explicit_profile_root_override_wins(monkeypatch, tmp_path):
    override = tmp_path / "profiles-root"
    monkeypatch.setenv("HERMES_PROFILES_ROOT", str(override))
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / ".hermes" / "profiles" / "worker"))

    assert paths.profiles_root() == override
