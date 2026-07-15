import json

from ci_triage.github_client import list_run_jobs, list_runs


def test_list_runs_parses_workflow_runs_array():
    payload = json.dumps({"workflow_runs": [{"id": 1}, {"id": 2}]})
    runs = list_runs("owner/repo", lookback=10, fetcher=lambda url, token, timeout: payload)
    assert [r["id"] for r in runs] == [1, 2]


def test_list_runs_builds_correct_url_and_passes_token():
    seen = {}

    def fetcher(url, token, timeout):
        seen["args"] = (url, token, timeout)
        return json.dumps({"workflow_runs": []})

    list_runs("owner/repo", lookback=5, token="tok123", timeout=9.0, fetcher=fetcher)
    url, token, timeout = seen["args"]
    assert url == "https://api.github.com/repos/owner/repo/actions/runs?per_page=5"
    assert token == "tok123"
    assert timeout == 9.0


def test_list_run_jobs_parses_jobs_array():
    payload = json.dumps({"jobs": [{"id": 10}]})
    jobs = list_run_jobs("owner/repo", 999, fetcher=lambda url, token, timeout: payload)
    assert jobs == [{"id": 10}]


def test_list_run_jobs_builds_correct_url():
    seen = {}

    def fetcher(url, token, timeout):
        seen["url"] = url
        return json.dumps({"jobs": []})

    list_run_jobs("owner/repo", 999, fetcher=fetcher)
    assert seen["url"] == "https://api.github.com/repos/owner/repo/actions/runs/999/jobs"
