<p align="center">
  <img src="assets/icons/HermesFleetControl-1024.png" alt="Hermes Fleet Control app icon" width="92" height="92">
</p>

<h1 align="center">Hermes Fleet Control</h1>

<p align="center">
  A local-first macOS menu-bar app and Python CLI for supervising Hermes Agent profile fleets, Discord gateways, OAuth health, and preview-first recovery from one machine.
</p>

<p align="center">
  <a href="https://github.com/TheStack-ai/hermes-fleet-control"><img alt="GitHub repo" src="https://img.shields.io/badge/GitHub-TheStack--ai%2Fhermes--fleet--control-181717?logo=github"></a>
  <img alt="macOS menu bar app" src="https://img.shields.io/badge/macOS-menu%20bar%20app-111827">
  <img alt="Python CLI" src="https://img.shields.io/badge/Python-CLI-3776AB?logo=python&logoColor=white">
  <img alt="Local first" src="https://img.shields.io/badge/local--first-no%20tokens%20shown-2E7D32">
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue.svg"></a>
</p>

<p align="center">
  <a href="#quick-start">Quick start</a> ·
  <a href="#macos-menu-bar-app">macOS app</a> ·
  <a href="#why-it-exists">Why</a> ·
  <a href="#contributing">Contribute</a> ·
  <a href="#roadmap">Roadmap</a>
</p>

<p align="center">
  <img src="assets/readme/hermes-fleet-control-hero.png" alt="Hermes Fleet Control README hero showing a dark local-first menu-bar status panel with Ready, Auth, Mapping, Logs, Diagnostics, and Preview Recovery rows" width="100%">
</p>

---

## Why it exists

When a Discord agent looks offline, the root cause is not always the gateway.

It might be:

- a Hermes gateway process that stopped or is reconnecting;
- an OAuth/model-provider auth state that needs repair;
- a profile that exists locally but has not been mapped to a fleet group;
- a network check that should be separated from local profile health;
- a recovery action that should be previewed before it touches a live process.

**Hermes Fleet Control separates those states.** It turns a messy local Hermes setup into a small operator surface for status, diagnostics, profile mapping, and safe recovery.

## What you get

| Surface | What it does |
|---|---|
| **macOS menu-bar app** | Native-feeling local UI with fleet status, auth repair actions, logs, diagnostics, H icon, and optional login autostart. |
| **Python CLI** | Cross-platform status snapshots, metadata-only auth checks, dry-run planning, and safe gateway actions. |
| **Auto-discovery** | Detects `~/.hermes` and `~/.hermes/profiles/*` when no private manifest exists. |
| **Preview-first recovery** | Reconnect/restart flows can be inspected before live actions run. |
| **Privacy-safe support path** | Redacted diagnostics only; no raw tokens, cookies, private IDs, signed URLs, or connection strings are displayed. |

## Quick start

```bash
git clone https://github.com/TheStack-ai/hermes-fleet-control.git
cd hermes-fleet-control
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[dev]"
python3 -m pytest -q
```

Run a read-only status snapshot:

```bash
python3 control/fleetctl.py status --json --skip-network
```

On first launch, Fleet Control auto-detects local Hermes profiles from:

```text
~/.hermes
~/.hermes/profiles/*
```

If you want a curated fleet view, create a local manifest:

```bash
cp config/fleet.yaml config/fleet.local.yaml
$EDITOR config/fleet.local.yaml
```

`config/fleet.local.yaml` is ignored by git so private profile names stay local.

## macOS menu-bar app

Build and install the local release app:

```bash
/opt/homebrew/bin/python3 scripts/generate_app_icon.py
python3 scripts/package_app.py --configuration release --zip --install
open /Applications/HermesFleetControl.app
```

Artifacts:

```text
/Applications/HermesFleetControl.app       installed local app
dist/HermesFleetControl.app                packaged app bundle
dist/HermesFleetControl-macOS.zip          zip handoff artifact
```

The packaged `.app` bundles the Python control layer under `Contents/Resources`, so it can be moved outside the cloned repo. Runtime logs, audit history, and generated auth-repair scripts are written to the user's Application Support directory, not inside the app bundle.

### Optional login autostart

Autostart is not installed by default. If you want the menu-bar app to open at login:

```bash
HERMES_FLEET_APP_PATH=/Applications/HermesFleetControl.app python3 scripts/launchagent.py install
python3 scripts/launchagent.py status
```

The LaunchAgent starts only the Fleet Control menu-bar app. It does not restart Hermes gateways and does not mutate Discord.

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

## Configuration

| Variable | Purpose |
|---|---|
| `HERMES_FLEET_ROOT` | Repository root when launching from a packaged app |
| `HERMES_HOME` | Hermes home, defaults to `~/.hermes` |
| `HERMES_PROFILES_ROOT` | Profile root override, defaults to `$HERMES_HOME/profiles` |
| `HERMES_BIN` | Hermes executable override |
| `HERMES_FLEET_PYTHON` | Python executable override |
| `HERMES_FLEET_MANIFEST` | Manifest path override |
| `HERMES_FLEET_PROFILE_MAP` | Local profile classification map override |
| `HERMES_FLEET_AUTH_REPAIR_DIR` | Runtime directory for generated auth-repair scripts |
| `CODEX_AUTH_FILE` | Optional Codex auth file path for metadata-only checks |

## Safety model

Hermes Fleet Control is designed as a local operator surface, not a cloud control plane.

- Status checks are read-only by default.
- Reconnect/restart flows are dry-run/preview-first.
- Gateway restarts are blocked when active agents are detected unless an explicit force path is used.
- Token repair is a local user action: Fleet Control prepares or opens a command, and OAuth happens in the user's terminal/browser.
- Discord channel, role, permission, and slash-command mutation is out of scope.
- Raw Discord tokens, OAuth tokens, cookies, raw private IDs, signed URLs, and connection strings must never be printed or displayed.

## Search / AI summary

Hermes Fleet Control is a local-first Hermes Agent dashboard for operators who run multiple Hermes profiles, Discord agents, gateway processes, and model-provider auth states. It helps distinguish gateway offline errors from OAuth login issues, profile mapping setup, network checks, and safe recovery actions. It includes a macOS menu-bar app, a Python CLI, local Hermes profile auto-discovery, redacted diagnostics, preview-first reconnect/restart planning, and optional login autostart.

Keywords: Hermes Agent, Hermes profile manager, Discord agent dashboard, local-first AI agent operations, macOS menu-bar app, OAuth repair, gateway status, AI agent fleet control, Python CLI for Hermes, profile mapping, redacted diagnostics, preview-first recovery.

## FAQ

### Is this a cloud service?

No. Fleet Control is local-first. It reads local Hermes state and writes local runtime files on your machine.

### Does it manage Discord server permissions or slash commands?

No. Discord guild structure, roles, permissions, channels, and slash-command mutation are intentionally out of scope.

### Does it show tokens or raw private IDs?

No. The support path is designed around redacted diagnostics and metadata-only auth state.

### Can I use it without the macOS app?

Yes. The Python CLI is the core control surface and is designed to run cross-platform with graceful platform fallbacks.

## Roadmap

Fleet Control is currently focused on local operator use and developer preview. The next public-facing program release will focus on a more polished installer/update experience, clearer first-run onboarding, richer profile mapping, and a smoother support workflow.

Planned areas:

- release-grade macOS app distribution and update flow;
- first-run onboarding for new Hermes users;
- richer profile grouping and ignore/inactive controls;
- clearer logs and diagnostics export;
- optional release channels for stable/beta builds;
- future native tray experience beyond macOS.

## Contributing

Contributions are welcome, especially around:

- first-run UX for clean Hermes installs;
- profile auto-discovery and mapping edge cases;
- macOS menu-bar polish and accessibility;
- Windows/Linux CLI behavior;
- safer diagnostics and redaction tests;
- docs, screenshots, and onboarding examples.

Start here:

- [`CONTRIBUTING.md`](CONTRIBUTING.md) — local setup, PR expectations, and safety rules.
- [`SECURITY.md`](SECURITY.md) — how to report vulnerabilities or token-safety issues.
- [Issue templates](.github/ISSUE_TEMPLATE) — bug reports, feature requests, and docs improvements.

## Windows / Linux status

- The Python CLI is designed to run on macOS, Windows, and Linux with graceful platform fallbacks.
- macOS-only features such as LaunchAgent and `MenuBarExtra` report as unsupported off macOS.
- Windows native tray packaging is not included yet; use the CLI with PowerShell/Terminal.

## Development checks

```bash
python3 -m compileall control scripts
python3 -m pytest -q
cd app/HermesFleetControl && swift build -c release
python3 scripts/package_app.py --configuration release --zip --install
python3 control/fleetctl.py status --json --skip-network --skip-auth
```

## Support / sponsor

Fleet Control keeps troubleshooting actions visible in the app: `Guide`, `Logs`, `Profiles`, `Copy`, `Source`, and `Sponsor`.

Public forks should update `.github/FUNDING.yml` and the app sponsor URL before publishing.

## License

MIT — see [`LICENSE`](LICENSE).
