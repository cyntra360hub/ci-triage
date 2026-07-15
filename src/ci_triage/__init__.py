"""ci-triage: classifies recent GitHub Actions failures of a target repo
into deterministic causes (timeout / dependency / test / infra)."""

from ci_triage.triage import TriageResult, run_triage

__all__ = ["TriageResult", "run_triage"]
__version__ = "0.1.0"
