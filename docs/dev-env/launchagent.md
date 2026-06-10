# Hermes Fleet Control LaunchAgent

macOS LaunchAgent support is optional and **not installed by default**.

## Safety boundary

- Packaging the app is safe/local.
- Printing or writing a plist is local config preparation.
- Installing/loading the LaunchAgent changes macOS login/runtime behavior.
- The LaunchAgent starts only the menu-bar app. It does not restart Hermes gateways and does not mutate Discord.

## Package app first

```bash
python3 scripts/package_app.py
```

## Inspect generated plist without installing

```bash
python3 scripts/launchagent.py print
```

## Status

```bash
python3 scripts/launchagent.py status
```

## Install/load at login

```bash
python3 scripts/launchagent.py install
```

## Disable / enable / uninstall

```bash
python3 scripts/launchagent.py disable
python3 scripts/launchagent.py enable
python3 scripts/launchagent.py uninstall
```

## Overrides

```bash
HERMES_FLEET_LAUNCH_LABEL=ai.hermes.fleet-control \
HERMES_FLEET_LAUNCH_PLIST="$HOME/Library/LaunchAgents/ai.hermes.fleet-control.plist" \
python3 scripts/launchagent.py status
```
