from ci_triage.classifier import Cause, classify_job, classify_run


def _job(conclusion="failure", steps=None):
    return {"conclusion": conclusion, "steps": steps or []}


def _step(name, conclusion="failure"):
    return {"name": name, "conclusion": conclusion}


def test_job_level_timed_out_conclusion():
    job = _job(conclusion="timed_out")
    assert classify_job(job) == Cause.TIMEOUT


def test_step_level_timed_out_conclusion():
    job = _job(steps=[_step("Run integration tests", "timed_out")])
    assert classify_job(job) == Cause.TIMEOUT


def test_dependency_install_step_failure():
    job = _job(steps=[_step("Install dependencies")])
    assert classify_job(job) == Cause.DEPENDENCY


def test_pip_install_step_failure():
    job = _job(steps=[_step("pip install -e .[dev]")])
    assert classify_job(job) == Cause.DEPENDENCY


def test_test_step_failure():
    job = _job(steps=[_step("Run pytest suite")])
    assert classify_job(job) == Cause.TEST


def test_real_world_vscode_example():
    # From an actual public failed run (microsoft/vscode, job 87243821423)
    # inspected during Step 0 research for this repo.
    job = _job(steps=[_step("\U0001f9ea Run integration tests (Electron)")])
    assert classify_job(job) == Cause.TEST


def test_infra_checkout_step_failure():
    job = _job(steps=[_step("Checkout repository")])
    assert classify_job(job) == Cause.INFRA


def test_unknown_when_no_keyword_matches():
    job = _job(steps=[_step("Do the thing")])
    assert classify_job(job) == Cause.UNKNOWN


def test_dependency_takes_priority_over_test_when_both_present():
    job = _job(steps=[_step("Install dependencies"), _step("Run tests")])
    assert classify_job(job) == Cause.DEPENDENCY


def test_only_failed_steps_are_considered():
    job = _job(steps=[_step("Run tests", "success"), _step("Deploy", "failure")])
    assert classify_job(job) == Cause.INFRA


def test_classify_run_timed_out_conclusion_short_circuits():
    run = {"conclusion": "timed_out"}
    assert classify_run(run, jobs=[]) == Cause.TIMEOUT


def test_classify_run_startup_failure_is_infra():
    run = {"conclusion": "startup_failure"}
    assert classify_run(run, jobs=[]) == Cause.INFRA


def test_classify_run_cancelled_with_no_failed_jobs_is_infra():
    run = {"conclusion": "cancelled"}
    jobs = [_job(conclusion="success")]
    assert classify_run(run, jobs) == Cause.INFRA


def test_classify_run_uses_first_specific_job_cause():
    run = {"conclusion": "failure"}
    jobs = [
        _job(conclusion="failure", steps=[_step("Do the thing")]),  # UNKNOWN
        _job(conclusion="failure", steps=[_step("Run pytest")]),  # TEST
    ]
    assert classify_run(run, jobs) == Cause.TEST


def test_classify_run_all_unknown_stays_unknown():
    run = {"conclusion": "failure"}
    jobs = [_job(conclusion="failure", steps=[_step("Mystery step")])]
    assert classify_run(run, jobs) == Cause.UNKNOWN
