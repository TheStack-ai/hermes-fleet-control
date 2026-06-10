# Hermes Fleet Control Safety Model

Generated: 2026-06-09 11:41:13 KST

## Core rule

The app is a local operational control plane, not a secret manager and not a Discord admin mutation tool.

## Secret handling

Forbidden in UI, logs, JSON output, notifications, and docs:

- Discord bot tokens
- OpenAI/Codex access or refresh tokens
- cookies
- private raw Discord IDs
- signed URLs
- passwords
- API keys
- connection strings

Allowed metadata:

- token present: yes/no
- token expiry timestamp if already non-sensitive
- last_auth_error code
- relogin_required boolean
- profile name and display name

## Action gates

| Action | Default | Gate |
|---|---|---|
| Status refresh | allowed | read-only |
| DNS/TCP check | allowed | read-only |
| Start stopped gateway | allowed | local side effect |
| Safe restart/reconnect | allowed if `active_agents=0` | local side effect |
| Stop gateway | confirmation | local side effect |
| Force restart | blocked by default | explicit local confirmation |
| Token repair | P1 only | explicit local terminal/browser action; no raw token display |
| Discord channel/role mutation | forbidden | separate DD approval outside app |

## Redaction patterns

The Python CLI must run a final leak guard before printing JSON. If a leak pattern is detected, output should be replaced with:

```json
{"ok": false, "error": "redaction_guard_failed", "pattern_type": "..."}
```

## Recovery and rollback

- Restart actions are reversible by restarting/starting the gateway.
- Stop actions should show profile list and require confirmation.
- Token repair should be run in a user-owned terminal/browser session and should never expose raw token values.
- Config edits are out of P0.
