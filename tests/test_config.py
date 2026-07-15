from ci_triage.config import DEFAULT_TARGET_REPO, load_config


def test_defaults_when_env_empty():
    config = load_config(env={})
    assert config.target_repo == DEFAULT_TARGET_REPO
    assert config.lookback == 20
    assert config.report_enabled is False
    assert config.github_token is None


def test_custom_target_repo_from_env():
    config = load_config(env={"CI_TRIAGE_TARGET_REPO": "someone/else"})
    assert config.target_repo == "someone/else"


def test_github_token_prefers_ci_triage_specific_var():
    config = load_config(
        env={"CI_TRIAGE_GITHUB_TOKEN": "specific", "GITHUB_TOKEN": "generic"}
    )
    assert config.github_token == "specific"


def test_github_token_falls_back_to_generic_var():
    config = load_config(env={"GITHUB_TOKEN": "generic"})
    assert config.github_token == "generic"


def test_reporting_enabled_only_when_both_creds_present():
    assert load_config(env={"CI_TRIAGE_AGENT_KEY_ID": "ak_x"}).report_enabled is False
    assert (
        load_config(
            env={"CI_TRIAGE_AGENT_KEY_ID": "ak_x", "CI_TRIAGE_AGENT_SECRET": "s"}
        ).report_enabled
        is True
    )
