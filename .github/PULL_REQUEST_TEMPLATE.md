## Summary

<!-- What changed and why? -->

## Type of change

- [ ] Bug fix
- [ ] Feature
- [ ] Documentation
- [ ] macOS app / UI
- [ ] Packaging / release
- [ ] Tests / CI

## Validation

<!-- Paste commands run and results. Do not paste secrets or unredacted logs. -->

- [ ] `python3 -m pytest -q`
- [ ] `cd app/HermesFleetControl && swift build -c release` (if Swift/macOS app changed)
- [ ] `python3 scripts/package_app.py --configuration release --zip` (if packaging changed)
- [ ] Manual UI check / screenshot attached (if UI changed)

## Safety checklist

- [ ] No raw tokens, cookies, credentials, private IDs, signed URLs, or connection strings are included.
- [ ] Gateway actions remain preview-first or explicitly gated.
- [ ] Discord guild/channel/role/permission/slash-command mutation is not introduced.
- [ ] Diagnostics remain redacted by default.

## Notes for reviewers

<!-- Risks, follow-up work, or areas where review should focus. -->
