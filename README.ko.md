<p align="center">
  <img src="assets/icons/HermesFleetControl-1024.png" alt="Hermes Fleet Control app icon" width="92" height="92">
</p>

<h1 align="center">Hermes Fleet Control</h1>

<p align="center">
  한 대의 머신에서 Hermes Agent 프로필 fleet, Discord gateway, OAuth 상태, preview-first 복구 흐름을 관리하는 local-first macOS 메뉴바 앱과 Python CLI.
</p>

<p align="center">
  <a href="https://github.com/TheStack-ai/hermes-fleet-control"><img alt="GitHub repo" src="https://img.shields.io/badge/GitHub-TheStack--ai%2Fhermes--fleet--control-181717?logo=github"></a>
  <img alt="macOS menu bar app" src="https://img.shields.io/badge/macOS-menu%20bar%20app-111827">
  <img alt="Python CLI" src="https://img.shields.io/badge/Python-CLI-3776AB?logo=python&logoColor=white">
  <img alt="Local first" src="https://img.shields.io/badge/local--first-no%20tokens%20shown-2E7D32">
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue.svg"></a>
</p>

<p align="center">
  <a href="README.md">English</a> ·
  <strong>한국어</strong> ·
  <a href="README.zh-CN.md">简体中文</a>
</p>

<p align="center">
  <a href="#빠른-시작">빠른 시작</a> ·
  <a href="#macos-메뉴바-앱">macOS 앱</a> ·
  <a href="#왜-필요한가">필요성</a> ·
  <a href="#기여하기">기여하기</a> ·
  <a href="#로드맵">로드맵</a>
</p>

<p align="center">
  <img src="assets/readme/hermes-fleet-control-hero.png" alt="Hermes Fleet Control README hero showing the actual macOS menu-bar app with profile fleet status, auth repair, diagnostics, and recovery controls" width="100%">
</p>

---

## 왜 필요한가

Discord agent가 offline처럼 보일 때, 원인이 항상 gateway는 아니다.

원인은 다음 중 하나일 수 있다:

- Hermes gateway 프로세스가 중지되었거나 재연결 중인 상태;
- OAuth 또는 model-provider 인증 상태 복구가 필요한 상태;
- 로컬에는 프로필이 있지만 fleet group에 아직 매핑되지 않은 상태;
- 네트워크 체크와 로컬 프로필 헬스를 분리해서 봐야 하는 상태;
- live process를 건드리기 전에 복구 액션을 먼저 preview해야 하는 상태.

**Hermes Fleet Control은 이 상태들을 분리해서 보여준다.** 복잡한 로컬 Hermes 구성을 status, diagnostics, profile mapping, safe recovery를 위한 작은 operator surface로 바꿔준다.

## 제공 기능

| Surface | 기능 |
|---|---|
| **macOS 메뉴바 앱** | fleet status, auth repair action, logs, diagnostics, H icon, optional login autostart를 제공하는 로컬 UI. |
| **Python CLI** | cross-platform status snapshot, metadata-only auth check, dry-run planning, safe gateway action. |
| **Auto-discovery** | private manifest가 없어도 `~/.hermes`와 `~/.hermes/profiles/*`를 자동 감지. |
| **Preview-first recovery** | reconnect/restart 흐름을 실제 실행 전에 먼저 확인 가능. |
| **Privacy-safe support path** | redacted diagnostics만 사용. raw token, cookie, private ID, signed URL, connection string을 표시하지 않음. |

## 빠른 시작

```bash
git clone https://github.com/TheStack-ai/hermes-fleet-control.git
cd hermes-fleet-control
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[dev]"
python3 -m pytest -q
```

읽기 전용 status snapshot 실행:

```bash
python3 control/fleetctl.py status --json --skip-network
```

첫 실행 시 Fleet Control은 다음 위치의 Hermes profiles를 자동 감지한다:

```text
~/.hermes
~/.hermes/profiles/*
```

정리된 fleet view를 원하면 local manifest를 만든다:

```bash
cp config/fleet.yaml config/fleet.local.yaml
$EDITOR config/fleet.local.yaml
```

`config/fleet.local.yaml`은 git에서 ignore되므로 private profile name은 로컬에만 남는다.

## macOS 메뉴바 앱

로컬 release 앱 build/install:

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

패키징된 `.app`은 Python control layer를 `Contents/Resources` 아래에 포함하므로 cloned repo 밖으로 이동해도 동작할 수 있다. Runtime logs, audit history, generated auth-repair scripts는 app bundle 내부가 아니라 사용자의 Application Support directory에 기록된다.

### 선택: 로그인 시 자동 실행

Autostart는 기본으로 설치되지 않는다. 메뉴바 앱을 로그인 시 열고 싶다면:

```bash
HERMES_FLEET_APP_PATH=/Applications/HermesFleetControl.app python3 scripts/launchagent.py install
python3 scripts/launchagent.py status
```

LaunchAgent는 Fleet Control 메뉴바 앱만 시작한다. Hermes gateway를 재시작하지 않고 Discord를 변경하지 않는다.

## CLI 예시

```bash
# Read-only health snapshot
python3 control/fleetctl.py status --json --skip-network

# Dry-run reconnect for a manifest group
python3 control/fleetctl.py reconnect --group local --safe --dry-run --json --skip-network

# Profile-scoped auth repair helper
python3 control/fleetctl.py auth-repair --profile default --action reauth --json
python3 control/fleetctl.py auth-repair --profile default --action smoke --json
```

## 설정

| Variable | Purpose |
|---|---|
| `HERMES_FLEET_ROOT` | packaged app에서 실행할 때 repository root 지정 |
| `HERMES_HOME` | Hermes home, 기본값 `~/.hermes` |
| `HERMES_PROFILES_ROOT` | profile root override, 기본값 `$HERMES_HOME/profiles` |
| `HERMES_BIN` | Hermes executable override |
| `HERMES_FLEET_PYTHON` | Python executable override |
| `HERMES_FLEET_MANIFEST` | Manifest path override |
| `HERMES_FLEET_PROFILE_MAP` | Local profile classification map override |
| `HERMES_FLEET_AUTH_REPAIR_DIR` | generated auth-repair scripts를 위한 runtime directory |
| `CODEX_AUTH_FILE` | metadata-only check용 optional Codex auth file path |

## Safety model

Hermes Fleet Control은 cloud control plane이 아니라 local operator surface로 설계되었다.

- Status check는 기본적으로 read-only다.
- Reconnect/restart flow는 dry-run/preview-first다.
- Active agent가 감지되면 명시적인 force path 없이는 gateway restart를 막는다.
- Token repair는 로컬 사용자 액션이다. Fleet Control은 command를 준비하거나 열어주고, OAuth는 사용자의 terminal/browser에서 진행된다.
- Discord channel, role, permission, slash-command mutation은 범위 밖이다.
- Raw Discord token, OAuth token, cookie, raw private ID, signed URL, connection string은 절대 출력하거나 표시하지 않는다.

## 검색 / AI 요약

Hermes Fleet Control은 여러 Hermes profile, Discord agent, gateway process, model-provider auth state를 운영하는 사용자를 위한 local-first Hermes Agent dashboard다. Gateway offline 문제와 OAuth login 문제, profile mapping 설정, network check, safe recovery action을 구분하도록 돕는다. macOS 메뉴바 앱, Python CLI, local Hermes profile auto-discovery, redacted diagnostics, preview-first reconnect/restart planning, optional login autostart를 포함한다.

Keywords: Hermes Agent, Hermes profile manager, Discord agent dashboard, local-first AI agent operations, macOS menu-bar app, OAuth repair, gateway status, AI agent fleet control, Python CLI for Hermes, profile mapping, redacted diagnostics, preview-first recovery.

## FAQ

### Cloud service인가?

아니다. Fleet Control은 local-first다. 로컬 Hermes state를 읽고 사용자 머신의 local runtime file을 쓴다.

### Discord server permission이나 slash command를 관리하나?

아니다. Discord guild structure, role, permission, channel, slash-command mutation은 의도적으로 범위 밖이다.

### Token이나 raw private ID가 보이나?

아니다. Support path는 redacted diagnostics와 metadata-only auth state를 기준으로 설계되었다.

### macOS 앱 없이 사용할 수 있나?

가능하다. Python CLI가 core control surface이며 cross-platform에서 graceful fallback으로 동작하도록 설계되었다.

## 로드맵

Fleet Control은 현재 local operator use와 developer preview에 집중하고 있다. 다음 public-facing program release는 더 polished된 installer/update experience, 명확한 first-run onboarding, 더 풍부한 profile mapping, 더 부드러운 support workflow에 집중할 예정이다.

Planned areas:

- release-grade macOS app distribution and update flow;
- new Hermes user를 위한 first-run onboarding;
- profile grouping, ignore/inactive control 개선;
- 더 명확한 logs와 diagnostics export;
- stable/beta build를 위한 optional release channels;
- macOS 외 native tray experience.

## 기여하기

다음 영역의 기여를 환영한다:

- clean Hermes install을 위한 first-run UX;
- profile auto-discovery와 mapping edge case;
- macOS menu-bar polish와 accessibility;
- Windows/Linux CLI behavior;
- safer diagnostics와 redaction tests;
- docs, screenshots, onboarding examples.

Start here:

- [`CONTRIBUTING.md`](CONTRIBUTING.md) — local setup, PR expectations, safety rules.
- [`SECURITY.md`](SECURITY.md) — vulnerability 또는 token-safety issue 보고 방법.
- [Issue templates](.github/ISSUE_TEMPLATE) — bug reports, feature requests, docs improvements.

## Windows / Linux status

- Python CLI는 macOS, Windows, Linux에서 graceful platform fallback으로 동작하도록 설계되었다.
- LaunchAgent, `MenuBarExtra` 같은 macOS-only feature는 macOS가 아니면 unsupported로 표시된다.
- Windows native tray packaging은 아직 포함되지 않았다. PowerShell/Terminal에서 CLI를 사용하면 된다.

## Development checks

```bash
python3 -m compileall control scripts
python3 -m pytest -q
cd app/HermesFleetControl && swift build -c release
python3 scripts/package_app.py --configuration release --zip --install
python3 control/fleetctl.py status --json --skip-network --skip-auth
```

## Support / sponsor

Fleet Control은 troubleshooting action을 앱 안에서 명확히 보여준다: `Guide`, `Logs`, `Profiles`, `Copy`, `Source`, `Sponsor`.

Public fork는 publishing 전에 `.github/FUNDING.yml`과 app sponsor URL을 업데이트해야 한다.

## License

MIT — [`LICENSE`](LICENSE) 참고.
