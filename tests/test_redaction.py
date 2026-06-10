import pytest

from control.redaction import redact_text, leak_guard, RedactionError


def test_redacts_discord_tokens_private_ids_and_signed_urls():
    raw_token = ".".join([
        "ABCDEFGHIJKLMNOPQRSTUVWX",
        "ABCDEF",
        "abcdefghijklmnopqrstuvwxyz1",
    ])
    raw = f"bot={raw_token} id=123456789012345678 s" + "ig=https://x.test?a=1&to" + "ken=secretvalue"

    redacted = redact_text(raw)

    assert "ABCDEFGHIJKLMNOPQRSTUVWX" not in redacted
    assert "123456789012345678" not in redacted
    assert "secretvalue" not in redacted
    assert "[REDACTED_TOKEN]" in redacted
    assert "[REDACTED_ID]" in redacted
    assert "[REDACTED_SIGNED_PARAM]" in redacted


def test_leak_guard_raises_on_unredacted_secret_patterns():
    with pytest.raises(RedactionError):
        leak_guard("to" + "ken=supersecret")
