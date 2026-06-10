import json

from control.hermes_profiles import summarize_profile


def make_profile(tmp_path, name="worker", state=None, agent_log=""):
    root = tmp_path / name
    (root / "logs").mkdir(parents=True)
    (root / "gateway_state.json").write_text(json.dumps(state or {
        "gateway_state": "running",
        "active_agents": 0,
        "platforms": {"discord": {"status": "connected"}},
    }), encoding="utf-8")
    (root / "logs" / "agent.log").write_text(agent_log, encoding="utf-8")
    return root


def test_summarize_profile_marks_healthy_when_connected_after_old_error(tmp_path):
    root = make_profile(tmp_path, agent_log="""
2026-06-09 11:05:14 ERROR discord.client: Attempting a reconnect in 875.62s
2026-06-09 11:18:15 INFO gateway.run: ✓ discord connected
""")

    summary = summarize_profile(root, "worker", launchd_pid_present=True)

    assert summary["status"] == "healthy"
    assert summary["active_agents"] == 0
    assert "reconnect" in summary["safe_actions"]


def test_summarize_profile_redacts_connected_discord_handle(tmp_path):
    root = make_profile(tmp_path, agent_log="2026-06-09 11:18:15 INFO gateway.run: Connected as PrivateBot#1234\n")

    summary = summarize_profile(root, "worker", launchd_pid_present=True)

    assert summary["status"] == "healthy"
    assert "PrivateBot#1234" not in summary["last_signal"]
    assert "[REDACTED_DISCORD_HANDLE]" in summary["last_signal"]


def test_summarize_profile_marks_degraded_backoff_when_error_after_latest_connect(tmp_path):
    root = make_profile(tmp_path, agent_log="""
2026-06-09 11:00:00 INFO gateway.run: ✓ discord connected
2026-06-09 11:08:52 ERROR discord.client: Attempting a reconnect in 949.75s
2026-06-09 11:08:52 aiohttp.client_exceptions.ClientConnectorDNSError: Cannot connect to host gateway-us-east1-b.discord.gg:443 ssl:default [nodename nor servname provided, or not known]
""")

    summary = summarize_profile(root, "worker", launchd_pid_present=True)

    assert summary["status"] == "degraded_backoff"
    assert "backoff" in summary["last_signal"].lower()


def test_summarize_profile_marks_busy_and_removes_restart_actions(tmp_path):
    root = make_profile(tmp_path, state={
        "gateway_state": "running",
        "active_agents": 2,
        "platforms": {"discord": {"status": "connected"}},
    }, agent_log="2026-06-09 11:18:15 INFO gateway.run: ✓ discord connected\n")

    summary = summarize_profile(root, "worker", launchd_pid_present=True)

    assert summary["status"] == "busy"
    assert "restart" not in summary["safe_actions"]
    assert "reconnect" not in summary["safe_actions"]
