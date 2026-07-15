# ci-triage

A small, deterministic Python agent that inspects a target GitHub repo's
recent Actions runs and classifies failures into one of four causes:
**timeout**, **dependency**, **test**, or **infra** — using only the
GitHub REST API's job/step metadata, no log parsing, no LLM calls, no
paid APIs, no server to run.

## What it does

1. Lists the target repo's most recent workflow runs (`GET
   /repos/{owner}/{repo}/actions/runs`).
2. For each run whose conclusion needs triage (`failure`, `timed_out`,
   `startup_failure`, `cancelled`), fetches its jobs and their steps
   (`GET .../actions/runs/{id}/jobs`).
3. Classifies the run deterministically from that metadata alone — see
   `src/ci_triage/classifier.py` for the exact priority-ordered rules.
4. Prints a report grouped by cause.

Default target: `cyntra360hub/agent-pulse`, configurable via
`CI_TRIAGE_TARGET_REPO`.

### Why metadata, not log text

An earlier design fetched and parsed raw job logs for stronger signal.
That doesn't work for a generic triage tool: `GET .../actions/jobs/{id}/
logs` requires **admin rights on the target repository** — confirmed
against a real public repo's failed job, which returned `403 Must have
admin rights to Repository`. Job/step *metadata* (names, conclusions),
by contrast, is readable for any public repo with no special
permissions, which is what a tool meant to triage an arbitrary target
repo actually needs. The tradeoff: classification is coarser than
log-text matching would allow, and steps with no recognizable keyword in
their name are honestly reported as `unknown` rather than guessed.

## Install

Requires Python 3.12+.

```bash
pip install .
```

## Usage

```bash
ci-triage
```

Or as a module:

```bash
python -m ci_triage.cli
```

### Configuration (environment variables)

| Variable | Default | Meaning |
|---|---|---|
| `CI_TRIAGE_TARGET_REPO` | `cyntra360hub/agent-pulse` | `owner/repo` to triage |
| `CI_TRIAGE_LOOKBACK` | `20` | how many recent runs to inspect |
| `CI_TRIAGE_GITHUB_TOKEN` | unset | optional token for a higher GitHub API rate limit (falls back to `GITHUB_TOKEN` if set, then anonymous) |
| `CI_TRIAGE_TIMEOUT_SECONDS` | `15` | network timeout per API call |

Copy `.env.example` to `.env` to set these locally; `.env` is gitignored
and never committed.

## Optional: AiOps Enabler integration

ci-triage can optionally report each triage pass as a signed task event
to [AiOps Enabler](https://aiopsenabler.com), a public-interest registry
of verified AI agent performance. **This is opt-in and off by default**
— the agent never phones home unless you explicitly configure
credentials.

This repo's reporting path is deliberately its own **spec-completeness
test**: `src/ci_triage/signing.py` and `reporting.py` implement raw
HMAC-signed REST calls built *purely* from the platform's own published
docs — [skill.md](https://aiopsenabler.com/skill.md) and
[openapi.json](https://api.aiopsenabler.com/openapi.json) — with zero
dependency on the official `aiops-enabler` SDK (which, separately, is
currently unusable by the public anyway: its install command points at
a private GitHub repo — see cert-sentinel's and status-watch's READMEs
for the full story). If this repo's tests pass, that's a working proof
that the platform's own documentation is sufficient, on its own, to
build a correct integration from scratch.

To enable it, set two environment variables (in `.env` locally, or as
GitHub Actions secrets in CI — see `.github/workflows/scheduled.yml`):

```
CI_TRIAGE_AGENT_KEY_ID=ak_...
CI_TRIAGE_AGENT_SECRET=...
```

With both set, each run sends a signed `task_started` / `task_completed`
event pair to `POST /api/v1/events`, with `outcome` set to `success` (no
triageable runs found), `escalated` (failures found and classified), or
`failure` (the triage pass itself couldn't complete, e.g. a GitHub API
error).

## Development

```bash
pip install -e ".[dev]"
pytest
```

All tests run fully offline — GitHub API calls are replaced with an
injected fake fetcher, so the suite never touches the network.

## License

MIT — see [LICENSE](LICENSE).
