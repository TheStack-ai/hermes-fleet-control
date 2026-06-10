# Hermes Fleet Control Technical Architecture

## Architecture summary

Hermes Fleet Control uses a two-layer local architecture:

1. **SwiftUI menu-bar app** for macOS display and local button actions.
2. **Python control CLI** for Hermes/gateway/profile operations and cross-platform automation.

```text
MenuBarExtra SwiftUI App (macOS)
        │ Process(JSON)
        ▼
control/fleetctl.py
        │
        ├── Reads fleet manifest
        ├── Reads profile state/log summaries
        ├── Plans/runs Hermes gateway start/stop/restart
        ├── Runs optional Discord network checks
        ├── Checks provider/auth metadata only
        └── Emits redacted JSON
```

## Configuration

### Fleet manifest

The public repo ships `config/fleet.yaml` as a minimal example. Users should copy it to `config/fleet.local.yaml` or set `$HERMES_FLEET_MANIFEST`.

```yaml
servers:
  local:
    display: Local Hermes profiles
    profiles:
      - profile: default
        display: Default
        critical: true
```

### Path discovery

Path defaults are profile/user-safe and overridable:

- `$HERMES_FLEET_ROOT` → repository root
- `$HERMES_HOME` → Hermes home, defaults to `~/.hermes`
- `$HERMES_PROFILES_ROOT` → profile root, defaults to `$HERMES_HOME/profiles`
- `$HERMES_BIN` → Hermes executable
- `$HERMES_FLEET_PYTHON` → Python executable
- `$HERMES_FLEET_AUTH_REPAIR_DIR` → generated local auth repair scripts

## CLI duties

`control/fleetctl.py` is the single control-plane entrypoint. Required properties:

- deterministic JSON output
- no raw log dumps
- no secret output
- dry-run mode for side-effect actions
- safe mode default for restarts/reconnects
- profile allowlist from the manifest

```text
control/
  fleetctl.py             # CLI entrypoint
  paths.py                # path/env/platform discovery
  hermes_profiles.py      # profile state/config/log summaries
  gateway_actions.py      # start/stop/restart planning and execution
  network_checks.py       # DNS/TCP Discord checks
  redaction.py            # leakage guard
  auth_health.py          # metadata-only auth checks
```

## Swift app duties

- poll `fleetctl.py status --json`
- render group/profile status
- call action commands through the CLI only
- render command result summary
- never parse `.env` or `auth.json` directly

## Status classification inputs

- `<profiles-root>/<profile>/gateway_state.json`
- recent `logs/agent.log` and `logs/gateway.log` summarized only
- optional launchd process map on macOS
- optional DNS/TCP checks to Discord gateway hosts
- metadata-only auth checks; token values are never returned

## Action model

### Read-only actions

- status
- network-check
- log summary
- auth metadata health

### Safe local actions

- start gateway
- stop gateway after confirmation in UI
- safe restart/reconnect when `active_agents = 0`
- open local auth repair command in the user’s terminal

### Privileged / gated actions

- force restart while `active_agents > 0`
- auto-recovery policy execution
- changing macOS LaunchAgent autostart

### Out of scope

- Discord role/channel/permission mutation
- external posting
- deploys
- Hermes core updates

## Platform boundaries

- Python CLI: macOS, Windows, Linux with platform fallbacks.
- macOS app: `MenuBarExtra`, LaunchAgent, ad-hoc local packaging.
- Windows native tray UI: not yet implemented; use CLI.

## Testing strategy

```bash
python3 -m compileall control scripts
python3 -m pytest -q
cd app/HermesFleetControl && swift build
python3 scripts/package_app.py
```
