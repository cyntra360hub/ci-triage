"""Minimal GitHub REST API client for workflow runs and jobs -- the same
data `gh api` would return, fetched directly via `urllib.request` so the
package has no dependency on the `gh` CLI being installed.

Deliberately does NOT fetch job logs: `GET /repos/{owner}/{repo}/actions/
jobs/{job_id}/logs` requires admin rights on the target repository (
confirmed empirically -- a real anonymous request against a public
repo's failed job returned `403 Must have admin rights to Repository`),
so it isn't usable for triaging an arbitrary/external target repo.
Classification instead works from job/step *metadata* (names,
conclusions), which the read-only `.../actions/runs` and
`.../actions/jobs/{id}` endpoints expose for any public repo without
special permissions.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

# Run conclusions worth triaging -- excludes "success", "neutral", and
# "skipped" (nothing to classify), but includes GitHub's own explicit
# "timed_out" and "startup_failure" conclusions (strong, direct signals
# -- see classifier.py) alongside the general "failure" case.
TRIAGEABLE_CONCLUSIONS = ("failure", "timed_out", "startup_failure", "cancelled")

Fetcher = Callable[[str, str | None, float], str]


class GitHubApiError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"GitHub API error {status_code}: {detail}")


def fetch_json(url: str, token: str | None, timeout: float) -> str:
    """Real HTTP GET against the GitHub REST API, returning the raw JSON
    text. The default `fetcher` -- swapped out entirely in tests, so no
    live network call happens in the test suite."""
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise GitHubApiError(exc.code, exc.read().decode("utf-8", "replace")) from exc


def list_runs(
    repo: str,
    lookback: int,
    token: str | None = None,
    timeout: float = 15.0,
    fetcher: Fetcher = fetch_json,
) -> list[dict[str, Any]]:
    url = f"https://api.github.com/repos/{repo}/actions/runs?per_page={lookback}"
    raw = fetcher(url, token, timeout)
    return json.loads(raw).get("workflow_runs", [])


def list_run_jobs(
    repo: str,
    run_id: int,
    token: str | None = None,
    timeout: float = 15.0,
    fetcher: Fetcher = fetch_json,
) -> list[dict[str, Any]]:
    url = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/jobs"
    raw = fetcher(url, token, timeout)
    return json.loads(raw).get("jobs", [])
