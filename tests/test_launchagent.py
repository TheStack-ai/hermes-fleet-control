import plistlib

from scripts.launchagent import build_plist, LABEL, APP_PATH, PLIST_PATH


def test_build_launchagent_plist_for_menu_bar_app_autostart():
    plist = build_plist()

    assert plist["Label"] == LABEL
    assert plist["RunAtLoad"] is True
    assert plist["KeepAlive"] is False
    assert plist["ProgramArguments"] == ["/usr/bin/open", str(APP_PATH)]
    assert str(PLIST_PATH).endswith(f"{LABEL}.plist")
    assert "StandardOutPath" in plist
    assert "StandardErrorPath" in plist

    # Ensure generated plist is macOS-plist serializable.
    plistlib.dumps(plist)
