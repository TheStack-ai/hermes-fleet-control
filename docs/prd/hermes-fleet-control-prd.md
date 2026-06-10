# Hermes Fleet Control PRD

## Problem

Hermes profile fleets can look “offline” to users even when local processes are alive. Common causes include Discord gateway reconnect backoff, stale provider auth, stopped gateways, or missing profile state. A local control center should identify the layer and offer safe, dry-run-first recovery without exposing secrets.

## Goals

1. Show grouped status for configured Hermes profiles.
2. Separate gateway health from model/provider auth health.
3. Provide safe local actions: refresh, dry-run reconnect, degraded-only reconnect, auth repair command prep, and optional autostart management.
4. Keep all secret material out of UI, logs, notifications, and JSON output.
5. Work as a cross-platform Python CLI, with a polished macOS menu-bar UI.

## Non-goals

- Discord role/channel/permission mutation.
- Remote deploys or cloud control plane.
- Hermes core updates.
- Raw token backup/restore inside the app.
- Windows native tray UI in the current release.

## User stories

- “Are my configured Hermes profiles ready?”
- “Is this a Discord gateway problem or a model auth problem?”
- “Show me what would restart before you actually restart it.”
- “Open the correct profile-scoped login command so I can re-authenticate myself.”
- “Keep the app available after login on macOS, but don’t mutate gateways automatically unless I choose it.”

## UX shape

```text
Hermes Fleet Control
Ready 8  · Gateway 1 · Auth 2

Action needed
  Profile A   Auth Fix   Re-auth
  Profile B   Backoff    Preview

Profiles
  Local Hermes profiles
    Ready 8 · Fix 1 · Busy 0

Control
  Watchdog Preview   Refresh
  Run Recovery       Alerts
  Autostart

Local only · secrets never shown
```

## Safety requirements

- Token values, cookies, private IDs, signed URLs, passwords, and connection strings are forbidden in output.
- Auth checks return booleans/metadata only.
- Restart/reconnect defaults to dry-run and safe mode.
- Safe restart/reconnect refuses active agents unless a force path is explicitly used.
- Auth repair opens/prepares a local terminal command; OAuth happens in the user’s terminal/browser.
- macOS LaunchAgent installation is an explicit local side effect.

## Platform requirements

- Python CLI should run on macOS, Windows, and Linux.
- macOS menu-bar app uses SwiftUI `MenuBarExtra` and LaunchAgent.
- Non-macOS systems should return clear unsupported status for macOS-only features.

## Acceptance criteria

1. `python3 control/fleetctl.py status --json --skip-network --skip-auth` emits redacted JSON.
2. `python3 control/fleetctl.py reconnect --group local --safe --dry-run --json` plans without running live side effects.
3. `python3 control/fleetctl.py auth-repair --profile default --action reauth --json` returns a profile-scoped command with no token values.
4. Python test suite passes.
5. Swift package builds.
6. Packaged macOS app codesigns locally.
7. Git-tracked files do not include local runtime, private manifests, raw tokens, or operator state.
