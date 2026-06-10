# macOS release checklist

Hermes Fleet Control is a local-first menu-bar app. A release-ready local build means the app can be installed from `/Applications`, launches from Spotlight/Finder, runs as a menu-bar app, has the H icon, bundles the Python control layer, and passes the safety checks below.

## Build/package

```bash
/opt/homebrew/bin/python3 scripts/generate_app_icon.py
python3 scripts/package_app.py --configuration release --zip --install
```

Artifacts:

- `/Applications/HermesFleetControl.app` — installed local app
- `dist/HermesFleetControl.app` — packaged app bundle
- `dist/HermesFleetControl-macOS.zip` — zip handoff artifact

## Optional login autostart

```bash
HERMES_FLEET_APP_PATH=/Applications/HermesFleetControl.app python3 scripts/launchagent.py install
python3 scripts/launchagent.py status
```

The LaunchAgent starts only the menu-bar app. It does not restart Hermes gateways and does not mutate Discord.

## Required validation

```bash
/opt/homebrew/bin/python3 -m compileall control scripts
/opt/homebrew/bin/python3 -m pytest -q
cd app/HermesFleetControl && swift build -c release
python3 scripts/package_app.py --configuration release --zip --install
codesign --verify --deep --strict /Applications/HermesFleetControl.app
python3 control/fleetctl.py status --json --skip-network --skip-auth
```

## Public program release gate

Current local release is intended for local operator use and developer preview. A polished public program release should pass the macOS distribution signing, notarization, and update-flow checklist before it is announced as frictionless for non-technical users.

```bash
security find-identity -v -p codesigning
xcrun notarytool submit dist/HermesFleetControl-macOS.zip --wait
```

Do not claim a public signed release unless distribution signing, notarization, and first-launch validation all pass.
