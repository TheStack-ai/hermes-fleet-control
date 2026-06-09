# Hermes Fleet Control

A local-first control plane for Hermes Agent fleets.

Hermes Fleet Control discovers your existing Hermes Agent profiles and messaging gateways, then shows which agents are healthy, degraded, offline, or unknown — without uploading tokens or replacing your Hermes setup.

## Why

Hermes can run agents through Discord, Telegram, Slack, and other messaging gateways. Once users run multiple profiles, day-2 operations get hard:

- Which profile is connected to which platform?
- Is the gateway stopped, or is the platform misconfigured?
- Is the model/provider auth broken instead of Discord/Telegram/Slack?
- Can I restart one agent without interrupting active work?

This project starts with a read-only CLI and a secret-safe discovery model.

## Core principle

> Attach to Hermes locally through layered discovery and probes, not by owning users' Slack, Telegram, or Discord credentials.

Fleet Control reads safe metadata from existing Hermes homes/profiles. It reports token/key presence, never token values, and avoids retaining config or environment values.

## Install from source

```bash
git clone https://github.com/TheStack-ai/hermes-fleet-control.git
cd hermes-fleet-control
python3 -m pip install .
```

For local development without installing:

```bash
PYTHONPATH=src python3 -m hermes_fleet.cli status
```

## Usage

```bash
hermes-fleet status
hermes-fleet status --json
hermes-fleet status --home ~/.hermes
```

Current MVP commands are read-only.

## Development

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py' -v
```

## Safety model

- No cloud service required.
- No raw secrets printed.
- No process mutation in `status`.
- Private IDs are counted/redacted by default.
- Unknown platform-side facts stay `unknown` until an explicit live validation is added.

See [`docs/prd/hermes-fleet-control-prd.md`](docs/prd/hermes-fleet-control-prd.md) for the full product design.
