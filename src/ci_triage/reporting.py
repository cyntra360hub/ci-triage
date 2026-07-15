"""Optional AiOps Enabler reporting via raw HMAC-signed REST calls to
POST /api/v1/events, built purely from skill.md/openapi.json (see
signing.py's module docstring for why this repo doesn't use the SDK).

Reporting only happens when the caller explicitly enables it (see
`config.load_config`). This module never phones home by default.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
import uuid
from collections.abc import Callable
from typing import Any

from ci_triage.config import Config
from ci_triage.signing import sign_request
from ci_triage.triage import TriageResult

Poster = Callable[[str, bytes, dict[str, str]], dict[str, Any]]


class ReportingError(Exception):
    """Raised when the AiOps Enabler API rejects a signed request."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"AiOps Enabler API error {status_code}: {detail}")


def post_signed(url: str, body: bytes, headers: dict[str, str]) -> dict[str, Any]:
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=10.0) as response:
            raw = response.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raise ReportingError(exc.code, exc.read().decode("utf-8", "replace")) from exc


def _send_event(config: Config, payload: dict[str, Any], poster: Poster) -> dict[str, Any]:
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    headers = sign_request(
        key_id=config.agent_key_id, secret=config.agent_secret, body=body  # type: ignore[arg-type]
    )
    url = f"{config.base_url.rstrip('/')}/api/v1/events"
    return poster(url, body, headers)


def report_run(
    config: Config, result: TriageResult, poster: Poster = post_signed
) -> dict[str, Any] | None:
    """Report one ci-triage pass as a signed task_started/task_completed
    event pair. Returns the platform's task_completed response, or None
    if reporting is disabled."""
    if not config.report_enabled:
        return None

    task_id = str(uuid.uuid4())
    started = time.monotonic()

    _send_event(config, {"event_type": "task_started", "task_id": task_id}, poster)
    duration_ms = int((time.monotonic() - started) * 1000)
    return _send_event(
        config,
        {
            "event_type": "task_completed",
            "task_id": task_id,
            "outcome": result.outcome,
            "duration_ms": duration_ms,
            "category": "incident-response",
        },
        poster,
    )
