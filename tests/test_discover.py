from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from hermes_fleet.cli import main
from hermes_fleet.discover import collect_status, parse_env_keys, read_config_sections, scan_root


def make_profile(root: Path, name: str, env: str = "", config: str = "") -> Path:
    home = root / "profiles" / name
    home.mkdir(parents=True)
    if env:
        (home / ".env").write_text(env, encoding="utf-8")
    if config:
        (home / "config.yaml").write_text(config, encoding="utf-8")
    return home


class DiscoveryTests(unittest.TestCase):
    def test_scan_root_expands_profile_home_to_parent_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            profile_home = Path(tmp) / "profiles" / "agent"
            profile_home.mkdir(parents=True)
            self.assertEqual(scan_root(profile_home), Path(tmp))

    def test_parse_env_keys_never_returns_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = Path(tmp) / ".env"
            env.write_text("SLACK_BOT_TOKEN=fake-slack-bot-token-value\nPLAIN=value\n", encoding="utf-8")
            keys = parse_env_keys(env)
            self.assertEqual(keys, {"SLACK_BOT_TOKEN", "PLAIN"})
            self.assertNotIn("fake-slack-bot-token-value", keys)

    def test_read_config_sections_never_returns_nested_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.yaml"
            config.write_text(
                "discord:\n  token: fake-discord-token-value\nslack:\n  app_token: fake-slack-app-token-value\n",
                encoding="utf-8",
            )
            sections = read_config_sections(config)
            self.assertEqual(sections, {"discord", "slack"})
            self.assertNotIn("fake-discord-token-value", sections)
            self.assertNotIn("fake-slack-app-token-value", sections)

    def test_collect_status_detects_platforms_without_secret_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_profile(
                root,
                "team",
                env="SLACK_BOT_TOKEN=fake-slack-bot-token-value\nSLACK_APP_TOKEN=fake-slack-app-token-value\n",
            )
            make_profile(
                root,
                "tg",
                env="TELEGRAM_BOT_TOKEN=fake-telegram-token-value\n",
            )

            status = collect_status(str(root)).to_dict()
            by_name = {p["name"]: p for p in status["profiles"]}

            self.assertIn(by_name["team"]["overall"], {"offline", "healthy"})
            slack = next(p for p in by_name["team"]["platforms"] if p["platform"] == "slack")
            self.assertTrue(slack["configured"])
            self.assertEqual(slack["required_keys"], {"SLACK_BOT_TOKEN": True, "SLACK_APP_TOKEN": True})

            telegram = next(p for p in by_name["tg"]["platforms"] if p["platform"] == "telegram")
            self.assertTrue(telegram["configured"])
            self.assertEqual(telegram["status"], "blocked")
            rendered = json.dumps(status)
            self.assertNotIn("fake-telegram-token-value", rendered)
            self.assertNotIn("fake-slack-bot-token-value", rendered)
            self.assertNotIn("fake-slack-app-token-value", rendered)

    def test_cli_status_json_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_profile(root, "discordbot", env="DISCORD_BOT_TOKEN=fake-discord-token-value\n")
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = main(["status", "--home", str(root), "--json"])
            self.assertEqual(rc, 0)
            out = buf.getvalue()
            data = json.loads(out)
            self.assertEqual(data["schema_version"], "0.1")
            self.assertEqual(data["profiles"][0]["name"], "discordbot")
            self.assertNotIn("fake-discord-token-value", out)


if __name__ == "__main__":
    unittest.main()
