# Hermes Fleet Control Operating Contract

## Role
Build a local-first status/control surface for Hermes Agent profile fleets.

## Safety
- Do not print, persist, or UI-display raw tokens, refresh tokens, cookies, private Discord IDs, signed URLs, or connection strings.
- Treat gateway start/stop/restart as local operational side effects. Require safe preflight and block active-agent interruption by default.
- Treat token repair/reconnect as privileged: metadata-only summaries, explicit local user action, no raw token copy in logs.
- Do not mutate Discord guild structure, permissions, roles, channels, slash commands, or external services from this app.
- Do not modify Hermes Agent source code from this repository.

## Development discipline
- Analyze → plan → execute → verify.
- Keep docs and implementation in small verified slices.
- Keep Python control logic testable without touching live gateways through fixtures and dry-run mode.
- The macOS app must call the local CLI; it must not parse `.env` or auth files directly.
- Live gateway operations must call one narrow control surface, not duplicate shell snippets throughout the UI.

## Source of truth
- Fleet membership comes from `config/fleet.yaml` or user-local `config/fleet.local.yaml` / `$HERMES_FLEET_MANIFEST`.
- Hermes profile roots default to `$HERMES_HOME/profiles`, or `$HERMES_PROFILES_ROOT` when set.
- Hermes executable discovery uses `$HERMES_BIN`, `PATH`, then a conventional `$HERMES_HOME/hermes-agent/venv/bin/hermes` fallback.

## Verification contract
Every implementation report must include:
- changed files
- command/test output
- whether live gateway operations were run
- what remains approval-gated
