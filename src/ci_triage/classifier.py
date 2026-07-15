"""Deterministic cause classification for a failed workflow run, from
job/step *metadata* alone (names + conclusions) -- no log text, which
GitHub's API won't serve for a repo we don't administer (see
github_client.py's module docstring).

Priority order (first match wins, evaluated top to bottom):
  1. Explicit GitHub conclusions that already mean exactly one thing:
     run or step conclusion "timed_out" -> TIMEOUT;
     run conclusion "startup_failure" -> INFRA (the workflow/runner
     itself failed to start, before any job step ran);
     run conclusion "cancelled" with no failed step -> INFRA (typically
     a runner/queue-level cancellation, not a code problem).
  2. Failed step name matches a dependency-install keyword -> DEPENDENCY.
  3. Failed step name matches a test-running keyword -> TEST.
  4. Failed step name matches an infra/setup keyword -> INFRA.
  5. No rule matched -> UNKNOWN (reported honestly rather than guessed).

Keyword lists are intentionally simple substring/regex checks on step
names -- deterministic and auditable, no scoring/ML involved.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any


class Cause(str, Enum):
    TIMEOUT = "timeout"
    DEPENDENCY = "dependency"
    TEST = "test"
    INFRA = "infra"
    UNKNOWN = "unknown"


_DEPENDENCY_PATTERN = re.compile(
    r"\b(install|dependenc\w*|npm ci|npm install|pip install|yarn|poetry|"
    r"bundle install|composer|nuget|cargo build|go mod|cache)\b",
    re.IGNORECASE,
)
_TEST_PATTERN = re.compile(
    r"\b(tests?|pytest|jest|specs?|e2e|smoke)\b",
    re.IGNORECASE,
)
_INFRA_PATTERN = re.compile(
    r"\b(checkout\w*|setup\w*|runner\w*|docker|deploy\w*|artifact\w*|publish\w*|"
    r"set up job|complete job|actions/cache|release\w*)\b",
    re.IGNORECASE,
)


def _failed_steps(job: dict[str, Any]) -> list[dict[str, Any]]:
    return [s for s in job.get("steps") or [] if s.get("conclusion") == "failure"]


def _timed_out_steps(job: dict[str, Any]) -> list[dict[str, Any]]:
    return [s for s in job.get("steps") or [] if s.get("conclusion") == "timed_out"]


def classify_job(job: dict[str, Any]) -> Cause:
    """Classify a single job's failure from its own + its steps' metadata."""
    if job.get("conclusion") == "timed_out" or _timed_out_steps(job):
        return Cause.TIMEOUT

    failed = _failed_steps(job)
    for step in failed:
        name = step.get("name", "")
        if _DEPENDENCY_PATTERN.search(name):
            return Cause.DEPENDENCY
    for step in failed:
        name = step.get("name", "")
        if _TEST_PATTERN.search(name):
            return Cause.TEST
    for step in failed:
        name = step.get("name", "")
        if _INFRA_PATTERN.search(name):
            return Cause.INFRA

    return Cause.UNKNOWN


def classify_run(run: dict[str, Any], jobs: list[dict[str, Any]]) -> Cause:
    """Classify a whole run's failure. Run-level explicit conclusions are
    checked first (strongest, cheapest signal); otherwise the run's cause
    is the first non-UNKNOWN classification among its failed jobs, or
    UNKNOWN if no job yields a specific cause."""
    conclusion = run.get("conclusion")
    if conclusion == "timed_out":
        return Cause.TIMEOUT
    if conclusion == "startup_failure":
        return Cause.INFRA

    failed_jobs = [j for j in jobs if j.get("conclusion") in ("failure", "timed_out", "cancelled")]
    if conclusion == "cancelled" and not failed_jobs:
        return Cause.INFRA

    for job in failed_jobs:
        cause = classify_job(job)
        if cause != Cause.UNKNOWN:
            return cause

    return Cause.UNKNOWN
