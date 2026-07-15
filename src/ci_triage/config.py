"""Configuration for ci-triage, sourced from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_TARGET_REPO = "cyntra360hub/agent-pulse"
DEFAULT_LOOKBACK = 20
DEFAULT_TIMEOUT_SECONDS = 15.0


@dataclass(frozen=True)
class Config:
    target_repo: str = DEFAULT_TARGET_REPO
    lookback: int = DEFAULT_LOOKBACK
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    github_token: str | None = None
    report_enabled: bool = False
    agent_key_id: str | None = None
    agent_secret: str | None = None
    base_url: str = "https://api.aiopsenabler.com"


def load_config(env: dict[str, str] | None = None) -> Config:
    """Build a Config from environment variables (or an injected mapping,
    for tests). Reporting is opt-in: it only turns on when both
    CI_TRIAGE_AGENT_KEY_ID and CI_TRIAGE_AGENT_SECRET are set."""
    source = env if env is not None else os.environ

    target_repo = source.get("CI_TRIAGE_TARGET_REPO", DEFAULT_TARGET_REPO)
    lookback = int(source.get("CI_TRIAGE_LOOKBACK", DEFAULT_LOOKBACK))
    timeout_seconds = float(
        source.get("CI_TRIAGE_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)
    )
    # A token is optional (public repos are readable anonymously) but
    # raises the GitHub API rate limit from 60/hr to 5000/hr -- in CI,
    # the workflow's own automatic GITHUB_TOKEN is enough for read-only
    # cross-repo access to a *public* target repo.
    github_token = source.get("CI_TRIAGE_GITHUB_TOKEN") or source.get("GITHUB_TOKEN") or None

    key_id = source.get("CI_TRIAGE_AGENT_KEY_ID") or None
    secret = source.get("CI_TRIAGE_AGENT_SECRET") or None
    base_url = source.get("CI_TRIAGE_BASE_URL", "https://api.aiopsenabler.com")

    return Config(
        target_repo=target_repo,
        lookback=lookback,
        timeout_seconds=timeout_seconds,
        github_token=github_token,
        report_enabled=bool(key_id and secret),
        agent_key_id=key_id,
        agent_secret=secret,
        base_url=base_url,
    )
