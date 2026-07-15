"""Orchestrates a triage pass: list a target repo's recent workflow
runs, classify each triageable one, and reduce to a run-level report."""

from __future__ import annotations

from dataclasses import dataclass

from ci_triage.classifier import Cause, classify_run
from ci_triage.config import Config
from ci_triage.github_client import (
    TRIAGEABLE_CONCLUSIONS,
    Fetcher,
    fetch_json,
    list_run_jobs,
    list_runs,
)


@dataclass(frozen=True)
class RunTriage:
    run_id: int
    name: str
    conclusion: str
    cause: Cause
    html_url: str | None = None


@dataclass(frozen=True)
class TriageResult:
    target_repo: str
    runs: tuple[RunTriage, ...]
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None

    @property
    def outcome(self) -> str:
        """Maps to the AiOps Enabler `task_completed` outcome enum
        (success | failure | escalated)."""
        if not self.ok:
            return "failure"
        if self.runs:
            return "escalated"
        return "success"

    @property
    def cause_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for run in self.runs:
            counts[run.cause.value] = counts.get(run.cause.value, 0) + 1
        return counts


def run_triage(config: Config, fetcher: Fetcher = fetch_json) -> TriageResult:
    try:
        runs = list_runs(
            config.target_repo,
            config.lookback,
            token=config.github_token,
            timeout=config.timeout_seconds,
            fetcher=fetcher,
        )
    except Exception as exc:  # noqa: BLE001 - any fetch/parse failure is a hard error
        return TriageResult(target_repo=config.target_repo, runs=(), error=str(exc))

    triaged: list[RunTriage] = []
    for run in runs:
        if run.get("conclusion") not in TRIAGEABLE_CONCLUSIONS:
            continue
        try:
            jobs = list_run_jobs(
                config.target_repo,
                run["id"],
                token=config.github_token,
                timeout=config.timeout_seconds,
                fetcher=fetcher,
            )
        except Exception as exc:  # noqa: BLE001
            return TriageResult(target_repo=config.target_repo, runs=(), error=str(exc))

        cause = classify_run(run, jobs)
        triaged.append(
            RunTriage(
                run_id=run["id"],
                name=run.get("name", "(unnamed workflow)"),
                conclusion=run["conclusion"],
                cause=cause,
                html_url=run.get("html_url"),
            )
        )

    return TriageResult(target_repo=config.target_repo, runs=tuple(triaged))
