from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, date, datetime
from typing import Literal

from .models import StrictModel

LOGGER = logging.getLogger(__name__)

ProgressStatus = Literal["started", "completed", "rejected", "failed"]


class GenerationProgress(StrictModel):
    event: str
    stage: str
    status: ProgressStatus
    message: str
    timestamp: datetime
    run_id: str
    run_date: date
    company_id: str | None = None
    candidate_slug: str | None = None
    attempt: int | None = None
    elapsed_ms: int | None = None


ProgressCallback = Callable[[GenerationProgress], None]


def emit_progress(
    callback: ProgressCallback | None,
    *,
    event: str,
    stage: str,
    status: ProgressStatus,
    message: str,
    run_id: str,
    run_date: date,
    company_id: str | None = None,
    candidate_slug: str | None = None,
    attempt: int | None = None,
    elapsed_ms: int | None = None,
) -> GenerationProgress:
    progress = GenerationProgress(
        event=event,
        stage=stage,
        status=status,
        message=message,
        timestamp=datetime.now(UTC),
        run_id=run_id,
        run_date=run_date,
        company_id=company_id,
        candidate_slug=candidate_slug,
        attempt=attempt,
        elapsed_ms=elapsed_ms,
    )
    level = {"failed": logging.ERROR, "rejected": logging.WARNING}.get(status, logging.INFO)
    LOGGER.log(
        level,
        message,
        extra={
            "event": event,
            "stage": stage,
            "status": status,
            "run_id": run_id,
            "run_date": run_date.isoformat(),
            "company_id": company_id,
            "candidate_slug": candidate_slug,
            "attempt": attempt,
            "elapsed_ms": elapsed_ms,
        },
    )
    if callback is not None:
        try:
            callback(progress)
        except Exception as exc:
            LOGGER.warning(
                "Progress callback failed without interrupting generation",
                extra={
                    "event": "progress.callback.failed",
                    "stage": stage,
                    "status": "failed",
                    "run_id": run_id,
                    "error_type": type(exc).__name__,
                },
            )
    return progress
