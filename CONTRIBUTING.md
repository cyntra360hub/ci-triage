# Contributing to ci-triage

Thanks for considering a contribution! This is a small, focused tool —
keep changes deterministic (no LLM calls, no paid APIs) and offline-testable
(mock the network, don't call the real GitHub API in tests).

## Getting started

```bash
git clone https://github.com/cyntra360hub/ci-triage.git
cd ci-triage
pip install -e ".[dev]"
pytest
```

## Workflow

1. Open an issue first for anything beyond a trivial fix, so we can agree
   on approach before you invest time.
2. Fork, branch, make your change, add/update tests.
3. Run `pytest` — all tests must pass, and new behavior needs new tests.
4. Open a PR describing what changed and why.

## Good first issues

These are scoped to be approachable without deep familiarity with the
codebase:

- **`good-first-issue`: Add more dependency-manager keywords.**
  `classifier.py`'s `_DEPENDENCY_PATTERN` covers npm/pip/yarn/poetry/
  bundler/nuget/cargo/go — add patterns for others you use (e.g. `uv`,
  `pnpm`, `conda`) with tests in `test_classifier.py`.
- **`good-first-issue`: Add a `--since` CLI flag.** Let a caller triage
  runs created after a given ISO date instead of just "the last N runs",
  using the GitHub API's `created` query parameter.
- **`good-first-issue`: Per-workflow-name grouping.** `TriageResult.
  cause_counts` aggregates across all workflows in the repo. Add a
  breakdown by `run.name` (e.g. "CI: 3 test failures, Release: 1 infra
  failure") for repos running multiple workflows.
- **`good-first-issue`: Add a JSON output mode.** Add a `--json` flag (or
  `CI_TRIAGE_OUTPUT=json` env var) to `cli.py` that prints the
  `TriageResult` as machine-readable JSON instead of the human-readable
  report, for piping into other tools.
- **`good-first-issue`: Retry on GitHub API rate limiting.** `github_client.py`
  currently raises `GitHubApiError` immediately on any non-2xx response.
  Add a single retry-after-backoff specifically for `403`/`429` responses
  that include a `Retry-After` or `X-RateLimit-Reset` header.

## Code style

- Standard library only, including AiOps Enabler reporting
  (`signing.py`/`reporting.py` use only `hmac`/`hashlib`/
  `urllib.request` — no SDK dependency, by design; see README).
- Keep network I/O behind an injectable `fetcher`/`poster` parameter (see
  `github_client.py`, `reporting.py`) so tests never touch the network.
- Classification (`classifier.py`) must stay metadata-only — see the
  README's "Why metadata, not log text" section for why log-text parsing
  isn't viable here.
- No comments explaining *what* code does — only *why*, when non-obvious.
