from pytest import raises as pytest_raises

from control.gateway_actions import ActionBlocked, execute_plan, plan_action


def test_safe_restart_blocks_active_agents():
    profile = {"profile": "beta", "active_agents": 1, "status": "busy"}

    with pytest_raises(ActionBlocked) as exc:
        plan_action("restart", profile=profile, safe=True, dry_run=True)

    assert "active_agents" in str(exc.value)


def test_reconnect_group_dry_run_builds_portable_multi_profile_plan():
    profiles = [
        {"profile": "alpha", "active_agents": 0, "status": "healthy"},
        {"profile": "beta", "active_agents": 0, "status": "degraded_backoff"},
    ]

    plan = plan_action("reconnect", group="team", profiles=profiles, safe=True, dry_run=True)
    result = execute_plan(plan)

    assert result["dry_run"] is True
    assert result["plan"]["targets"] == ["alpha", "beta"]
    assert result["plan"]["command"]
    assert not any(part.startswith("/Users/") for part in result["plan"]["command"])
