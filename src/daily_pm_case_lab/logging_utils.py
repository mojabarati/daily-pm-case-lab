from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from typing import Any

SECRET_KEY_RE = re.compile(
    r"(api[_-]?key|authorization|access[_-]?token|github[_-]?token|gh[_-]?token|secret|password)",
    re.IGNORECASE,
)
SECRET_VALUE_RE = re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b")


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if SECRET_KEY_RE.search(str(key)) else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact(item) for item in value]
    if isinstance(value, str):
        return SECRET_VALUE_RE.sub("[REDACTED]", value)
    return value


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in (
            "event",
            "run_id",
            "run_date",
            "stage",
            "attempt",
            "retry_attempt",
            "duration_ms",
            "elapsed_ms",
            "model",
            "agent_runs",
            "company_id",
            "candidate_slug",
            "tool_calls",
            "input_tokens",
            "output_tokens",
            "status",
            "error_type",
        ):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(redact(payload), ensure_ascii=False, separators=(",", ":"))


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())
