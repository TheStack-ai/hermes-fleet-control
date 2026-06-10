# Contributing to Hermes Fleet Control

Thanks for helping improve Hermes Fleet Control. This project is a local-first operator surface for Hermes Agent profile fleets, so contributions should keep user safety, privacy, and reversible local actions at the center.

## Good first contribution areas

- First-run UX for clean Hermes installs.
- Profile auto-discovery and mapping edge cases.
- macOS menu-bar UI polish and accessibility.
- Windows/Linux CLI compatibility.
- Safer redaction and diagnostics tests.
- Documentation, screenshots, examples, and troubleshooting notes.

## Local setup

```bash
git clone https://github.com/TheStack-ai/hermes-fleet-control.git
cd hermes-fleet-control
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[dev]"
python3 -m pytest -q
```

For the macOS app:

```bash
/opt/homebrew/bin/python3 scripts/generate_app_icon.py
cd app/HermesFleetControl
swift build -c release
```

## Before opening a PR

Run the relevant checks:

```bash
python3 -m compileall control scripts
python3 -m pytest -q
cd app/HermesFleetControl && swift build -c release
python3 control/fleetctl.py status --json --skip-network --skip-auth
```

If you change packaging or the macOS app, also run:

```bash
python3 scripts/package_app.py --configuration release --zip
```

## Safety rules

Do not include or print:

- Discord tokens;
- OAuth access or refresh tokens;
- cookies;
- private IDs;
- signed URLs;
- connection strings;
- raw logs that may contain user/private data.

Gateway actions should remain preview-first where possible. Live restart/reconnect behavior must stay narrow, explicit, and testable.

## PR expectations

A good PR includes:

- a short summary of the user-facing change;
- tests or a clear reason tests are not applicable;
- screenshots or notes for UI changes;
- confirmation that no secrets/private local paths were added;
- any remaining risks or follow-up work.

## Commit style

Use concise conventional-style subjects:

```text
fix: avoid overlapping status refreshes
feat: add profile mapping diagnostics
docs: improve first-run guide
chore: update release checklist
```

## Scope boundaries

Fleet Control must not mutate Discord guild structure, channels, roles, permissions, or slash commands. It should not become a hosted cloud control plane. Keep it local-first, inspectable, and safe by default.
