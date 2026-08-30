from __future__ import annotations

import hashlib
from collections import Counter
from datetime import date

from .history import coverage_counts, last_seen
from .models import Company, HistoryRecord, ResearchPriority

PRIORITY_ORDER = {
    ResearchPriority.HIGH: 0,
    ResearchPriority.MEDIUM: 1,
    ResearchPriority.LOW: 2,
}


def _stable_tiebreak(run_date: date, company_id: str) -> str:
    return hashlib.sha256(f"{run_date.isoformat()}:{company_id}".encode()).hexdigest()


def shortlist_companies(
    companies: list[Company],
    history: list[HistoryRecord],
    run_date: date,
    limit: int,
) -> list[Company]:
    coverage = coverage_counts(history)
    seen = last_seen(history)
    company_category_coverage: Counter[str] = Counter()
    company_by_id = {company.id: company for company in companies}
    for record in history:
        if company := company_by_id.get(record.company_id):
            company_category_coverage[company.category] += 1

    never = date.min
    ordered = sorted(
        companies,
        key=lambda company: (
            coverage[company.id] + company.case_count,
            company_category_coverage[company.category],
            seen.get(company.id, never),
            PRIORITY_ORDER[company.research_priority],
            _stable_tiebreak(run_date, company.id),
        ),
    )
    return ordered[:limit]
