import json

from ci_triage.config import Config
from ci_triage.triage import run_triage


def _runs_payload(*runs):
    return json.dumps({"workflow_runs": list(runs)})


def _jobs_payload(*jobs):
    return json.dumps({"jobs": list(jobs)})


def test_no_triageable_runs_is_success():
    config = Config(target_repo="owner/repo")

    def fetcher(url, token, timeout):
        if "/jobs" in url:
            raise AssertionError("should not fetch jobs when no runs need triage")
        return _runs_payload({"id": 1, "conclusion": "success", "name": "CI"})

    result = run_triage(config, fetcher=fetcher)
    assert result.ok
    assert result.runs == ()
    assert result.outcome == "success"


def test_failed_run_is_triaged_and_classified():
    config = Config(target_repo="owner/repo")

    def fetcher(url, token, timeout):
        if "/jobs" in url:
            return _jobs_payload(
                {"conclusion": "failure", "steps": [{"name": "Run pytest", "conclusion": "failure"}]}
            )
        return _runs_payload(
            {"id": 42, "conclusion": "failure", "name": "CI", "html_url": "https://x"}
        )

    result = run_triage(config, fetcher=fetcher)
    assert result.ok
    assert len(result.runs) == 1
    assert result.runs[0].run_id == 42
    assert result.runs[0].cause.value == "test"
    # Classifying a failing run is this agent doing its job -- still success.
    assert result.outcome == "success"
    assert result.findings_summary == "1 run(s) triaged: test=1"


def test_run_level_fetch_error_is_reported():
    config = Config(target_repo="owner/repo")

    def failing_fetcher(url, token, timeout):
        raise TimeoutError("connection timed out")

    result = run_triage(config, fetcher=failing_fetcher)
    assert not result.ok
    assert result.outcome == "failure"
    assert "timed out" in result.error


def test_jobs_fetch_error_is_reported():
    config = Config(target_repo="owner/repo")

    def fetcher(url, token, timeout):
        if "/jobs" in url:
            raise TimeoutError("connection timed out")
        return _runs_payload({"id": 1, "conclusion": "failure", "name": "CI"})

    result = run_triage(config, fetcher=fetcher)
    assert not result.ok


def test_non_triageable_conclusions_are_skipped():
    config = Config(target_repo="owner/repo")
    calls = []

    def fetcher(url, token, timeout):
        calls.append(url)
        if "/jobs" in url:
            return _jobs_payload()
        return _runs_payload(
            {"id": 1, "conclusion": "success", "name": "a"},
            {"id": 2, "conclusion": "skipped", "name": "b"},
            {"id": 3, "conclusion": "neutral", "name": "c"},
        )

    result = run_triage(config, fetcher=fetcher)
    assert result.runs == ()
    assert len(calls) == 1  # only the runs list call, no per-run jobs calls


def test_cause_counts_aggregates_multiple_runs():
    config = Config(target_repo="owner/repo")

    def fetcher(url, token, timeout):
        if "/jobs" in url:
            if "/runs/1/" in url:
                return _jobs_payload({"conclusion": "failure", "steps": [{"name": "Run pytest", "conclusion": "failure"}]})
            return _jobs_payload({"conclusion": "failure", "steps": [{"name": "npm install", "conclusion": "failure"}]})
        return _runs_payload(
            {"id": 1, "conclusion": "failure", "name": "a"},
            {"id": 2, "conclusion": "failure", "name": "b"},
        )

    result = run_triage(config, fetcher=fetcher)
    assert result.cause_counts == {"test": 1, "dependency": 1}
    assert result.findings_summary == "2 run(s) triaged: dependency=1, test=1"
    assert result.outcome == "success"


def test_findings_summary_none_when_no_runs_triaged():
    config = Config(target_repo="owner/repo")
    fetcher = lambda url, token, timeout: _runs_payload({"id": 1, "conclusion": "success", "name": "a"})
    result = run_triage(config, fetcher=fetcher)
    assert result.findings_summary is None
