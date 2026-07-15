import json

from ci_triage.config import Config
from ci_triage.reporting import ReportingError, report_run
from ci_triage.triage import RunTriage, TriageResult
from ci_triage.classifier import Cause


class _FakePoster:
    def __init__(self):
        self.calls = []

    def __call__(self, url, body, headers):
        self.calls.append((url, body, headers))
        return {"id": "evt_123"}


def test_report_disabled_returns_none():
    poster = _FakePoster()
    config = Config(report_enabled=False)
    result = TriageResult(target_repo="o/r", runs=())
    assert report_run(config, result, poster=poster) is None
    assert poster.calls == []


def test_report_enabled_sends_started_then_completed():
    poster = _FakePoster()
    config = Config(report_enabled=True, agent_key_id="ak_test", agent_secret="s3cret")
    result = TriageResult(target_repo="o/r", runs=())
    response = report_run(config, result, poster=poster)
    assert response == {"id": "evt_123"}
    kinds = [json.loads(c[1])["event_type"] for c in poster.calls]
    assert kinds == ["task_started", "task_completed"]


def test_outcome_escalated_when_runs_triaged():
    poster = _FakePoster()
    config = Config(report_enabled=True, agent_key_id="ak_test", agent_secret="s3cret")
    result = TriageResult(
        target_repo="o/r",
        runs=(RunTriage(run_id=1, name="CI", conclusion="failure", cause=Cause.TEST),),
    )
    report_run(config, result, poster=poster)
    second_body = json.loads(poster.calls[1][1])
    assert second_body["outcome"] == "escalated"


def test_outcome_failure_when_triage_errored():
    poster = _FakePoster()
    config = Config(report_enabled=True, agent_key_id="ak_test", agent_secret="s3cret")
    result = TriageResult(target_repo="o/r", runs=(), error="boom")
    report_run(config, result, poster=poster)
    second_body = json.loads(poster.calls[1][1])
    assert second_body["outcome"] == "failure"


def test_reporting_error_carries_status_and_detail():
    err = ReportingError(422, '{"detail": "bad request"}')
    assert err.status_code == 422
    assert "bad request" in err.detail
