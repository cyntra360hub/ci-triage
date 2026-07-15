"""ci-triage command-line entry point."""

from __future__ import annotations

import sys

from ci_triage.config import load_config
from ci_triage.reporting import report_run
from ci_triage.triage import TriageResult, run_triage


def _print_report(result: TriageResult) -> None:
    print(f"Target repo: {result.target_repo}")
    if not result.ok:
        print(f"[ERROR] triage failed: {result.error}")
        return
    if not result.runs:
        print("No triageable runs found in the lookback window.")
    for run in result.runs:
        print(f"  #{run.run_id} {run.name!r} conclusion={run.conclusion} -> cause={run.cause.value}")
    print()
    print(f"Overall: outcome={result.outcome}, {len(result.runs)} run(s) triaged, "
          f"by cause: {result.cause_counts}")


def main() -> int:
    config = load_config()
    result = run_triage(config)
    _print_report(result)

    if config.report_enabled:
        try:
            report_run(config, result)
            print("Reported run to AiOps Enabler.")
        except Exception as exc:  # noqa: BLE001
            print(f"AiOps Enabler reporting failed (non-fatal): {exc}", file=sys.stderr)
    else:
        print("AiOps Enabler reporting disabled (no credentials configured).")

    return 1 if not result.ok else 0


if __name__ == "__main__":
    raise SystemExit(main())
