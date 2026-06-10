# Swift build notes

## Build

```bash
cd app/HermesFleetControl
xcrun swift build -c debug
```

## Package local app bundle

```bash
python3 scripts/package_app.py
```

The package script builds the Swift executable, creates `dist/HermesFleetControl.app`, and applies ad-hoc local codesigning.

## Runtime configuration

The app discovers the repository root from `HERMES_FLEET_ROOT` or, when launched from `dist/HermesFleetControl.app`, from the app bundle location.

Useful overrides:

```bash
HERMES_FLEET_ROOT="$PWD" \
HERMES_FLEET_PYTHON="$(command -v python3)" \
open dist/HermesFleetControl.app
```
