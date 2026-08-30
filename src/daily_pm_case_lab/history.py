from __future__ import annotations

import json
import re
from collections import Counter
from datetime import date
from pathlib import Path

from pydantic import ValidationError

from .models import CaseCandidate, HistoryRecord

TOKEN_RE = re.compile(r"[a-z0-9\u0600-\u06ff]+", re.IGNORECASE)


def load_history(path: Path) -> list[HistoryRecord]:
    if not path.exists():
        return []
    records: list[HistoryRecord] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            records.append(HistoryRecord.model_validate_json(line))
        except (ValidationError, json.JSONDecodeError) as exc:
            raise ValueError(f"Invalid history record at line {line_number}") from exc
    return records


def append_history(path: Path, record: HistoryRecord) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(record.model_dump_json() + "\n")
        handle.flush()


def normalized_tokens(value: str) -> set[str]:
    return set(TOKEN_RE.findall(value.casefold()))


def token_similarity(left: str, right: str) -> float:
    left_tokens = normalized_tokens(left)
    right_tokens = normalized_tokens(right)
    if not left_tokens and not right_tokens:
        return 1.0
    return len(left_tokens & right_tokens) / max(1, len(left_tokens | right_tokens))


def duplicate_reason(
    candidate: CaseCandidate, history: list[HistoryRecord], threshold: float = 0.72
) -> str | None:
    for record in history:
        if candidate.case_slug == record.case_slug:
            return f"case_slug already exists: {record.case_slug}"
        if candidate.case_title.casefold() == record.case_title.casefold():
            return f"case title already exists: {record.case_title}"
        if candidate.primary_problem.casefold() == record.primary_problem.casefold():
            return f"primary problem already exists: {record.primary_problem}"
        if candidate.company_id == record.company_id:
            combined_new = f"{candidate.case_title} {candidate.primary_problem}"
            combined_old = f"{record.case_title} {record.primary_problem}"
            similarity = max(
                token_similarity(candidate.case_title, record.case_title),
                token_similarity(candidate.primary_problem, record.primary_problem),
                token_similarity(combined_new, combined_old),
            )
            if similarity >= threshold:
                return f"similar to prior case: {record.case_slug}"
    return None


def coverage_counts(history: list[HistoryRecord]) -> Counter[str]:
    return Counter(record.company_id for record in history)


def category_counts(history: list[HistoryRecord]) -> Counter[str]:
    return Counter(record.case_category for record in history)


def last_seen(history: list[HistoryRecord]) -> dict[str, date]:
    result: dict[str, date] = {}
    for record in history:
        result[record.company_id] = max(record.date, result.get(record.company_id, record.date))
    return result
