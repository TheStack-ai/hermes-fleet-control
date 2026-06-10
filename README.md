# Hermes Fleet Control

Local-first control center for Hermes Agent profile fleets.

It has two layers:

- **Python CLI**: cross-platform status, dry-run planning, metadata-only auth checks, and safe gateway actions.
- **macOS menu-bar app**: polished local UI for the same CLI. Windows users can use the CLI today; a native Windows tray UI is intentionally separate future work.

## What it does

- Auto-detects local Hermes profiles on first launch when no private manifest exists.
- Reads a fleet manifest and summarizes Hermes profile health.
- Separates **Discord gateway health** from **model/provider auth health**.
- Shows metadata-only auth state; it never displays raw tokens.
- Provides dry-run-first reconnect/restart planning.
- Opens a local terminal auth-repair helper so the user performs OAuth directly.
- Supports macOS LaunchAgent management for the menu-bar app.

## Install / setup

```bash
git clone https://github.com/<owner>/hermes-fleet-control.git
cd hermes-fleet-control
python3 -m pytest -q
```

On first launch, Fleet Control auto-detects local Hermes profiles from `~/.hermes` and `~/.hermes/profiles/*` when no private manifest exists. For a curated fleet view, create your local manifest by copying the example:

```bash
cp config/fleet.yaml config/fleet.local.yaml
$EDITOR config/fleet.local.yaml
```

`config/fleet.local.yaml` is ignored by git so private profile names stay local.

### Environment overrides

| Variable | Purpose |
|---|---|
| `HERMES_FLEET_ROOT` | Repository root when launching from a packaged app |
| `HERMES_HOME` | Hermes home, defaults to `~/.hermes` |
| `HERMES_PROFILES_ROOT` | Profile root override, defaults to `$HERMES_HOME/profiles` |
| `HERMES_BIN` | Hermes executable override |
| `HERMES_FLEET_PYTHON` | Python executable override |
| `HERMES_FLEET_MANIFEST` | Manifest path override |
| `HERMES_FLEET_AUTH_REPAIR_DIR` | Runtime directory for generated auth-repair scripts |
| `CODEX_AUTH_FILE` | Optional Codex auth file path for metadata-only checks |

## CLI examples

```bash
# Read-only health snapshot
python3 control/fleetctl.py status --json --skip-network

# Dry-run reconnect for a manifest group
python3 control/fleetctl.py reconnect --group local --safe --dry-run --json --skip-network

# Profile-scoped auth repair helper
python3 control/fleetctl.py auth-repair --profile default --action reauth --json
python3 control/fleetctl.py auth-repair --profile default --action smoke --json
```

## macOS menu-bar app

```bash
python3 scripts/package_app.py
open dist/HermesFleetControl.app
```

Autostart is not installed by default:

```bash
python3 scripts/launchagent.py status
python3 scripts/launchagent.py install   # local side effect: adds/loads LaunchAgent
```

## Windows / Linux status

- The Python CLI is designed to run on macOS, Windows, and Linux with graceful platform fallbacks.
- macOS-only features such as LaunchAgent and `MenuBarExtra` report as unsupported off macOS.
- Windows native tray packaging is not included yet; use the CLI with PowerShell/Terminal.

## Safety principles

- Never print or display raw Discord tokens, OAuth tokens, cookies, raw private IDs, signed URLs, or connection strings.
- Gateway restarts are blocked when `active_agents > 0` unless the user explicitly uses a force path.
- Token repair is a local user action: Fleet Control prepares/opens a command, and OAuth happens in the user’s terminal/browser.
- Discord channel/role/permission mutation is out of scope.

## Release readiness checklist

```bash
python3 -m compileall control scripts
python3 -m pytest -q
cd app/HermesFleetControl && swift build
python3 scripts/package_app.py
python3 control/fleetctl.py status --json --skip-network --skip-auth
```
