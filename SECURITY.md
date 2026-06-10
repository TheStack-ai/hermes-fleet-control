# Security Policy

Hermes Fleet Control is a local-first operator tool. Security reports are especially important when they involve token exposure, unsafe gateway actions, or diagnostics that reveal private local state.

## Supported versions

This repository is currently in developer-preview form. Please report security issues against the latest `main` branch unless a release notes page says otherwise.

## What to report

Please report issues involving:

- raw token, cookie, credential, signed URL, or connection string exposure;
- diagnostics that reveal private IDs or unredacted local logs;
- gateway restart/reconnect behavior that bypasses preview/safety checks;
- command injection or unsafe shell argument handling;
- packaged app behavior that writes outside its documented local runtime paths;
- CI, release, or packaging behavior that could publish private artifacts.

## What not to include

Do not paste real secrets into issues, PRs, screenshots, or logs. Redact values and describe the pattern instead.

Good:

```text
The copied diagnostics include a value that matches `providers.openai-codex.tokens.refresh_token`.
```

Bad:

```text
Here is my full auth.json: ...
```

## Reporting path

If GitHub private vulnerability reporting is enabled for the repository, use that. Otherwise, open a minimal public issue that says a private security report is needed and avoid details that would help exploitation.

## Maintainer response goals

- Acknowledge valid reports as soon as practical.
- Reproduce with a redacted fixture or local-only smoke test.
- Patch with tests when possible.
- Avoid requesting raw secrets from reporters.
