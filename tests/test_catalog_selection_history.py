from __future__ import annotations

from datetime import date
from pathlib import Path

from daily_pm_case_lab.catalog import load_catalog, resolve_company
from daily_pm_case_lab.history import duplicate_reason, token_similarity
from daily_pm_case_lab.models import HistoryRecord
from daily_pm_case_lab.selection import shortlist_companies

from .factories import candidate

ROOT = Path(__file__).resolve().parents[1]


def test_catalog_has_exactly_100_unique_companies() -> None:
    companies = load_catalog(ROOT / "data" / "company_catalog.yaml")
    assert len(companies) == 100
    assert len({company.id for company in companies}) == 100
    assert resolve_company(companies, "Booking.com").id == "booking-holdings"


def test_shortlist_is_deterministic_and_prefers_uncovered() -> None:
    companies = load_catalog(ROOT / "data" / "company_catalog.yaml")
    first = shortlist_companies(companies, [], date(2026, 8, 30), 5)
    second = shortlist_companies(companies, [], date(2026, 8, 30), 5)
    assert [company.id for company in first] == [company.id for company in second]

    covered = HistoryRecord(
        date=date(2026, 8, 29),
        company=first[0].name,
        company_id=first[0].id,
        case_slug="old-case",
        case_title="Old title",
        primary_problem="Old problem",
        case_category="Growth",
        difficulty="Medium",
        sources_count=5,
    )
    rotated = shortlist_companies(companies, [covered], date(2026, 8, 30), 100)
    assert rotated[-1].id == first[0].id


def test_duplicate_protection_uses_exact_and_similarity_checks() -> None:
    prior = HistoryRecord(
        date=date(2026, 8, 1),
        company="Uber",
        company_id="uber",
        case_slug="prior-slug",
        case_title="Balancing driver supply and rider demand",
        primary_problem="Long waits from marketplace supply demand imbalance",
        case_category="Marketplace liquidity",
        difficulty="Hard",
        sources_count=8,
    )
    assert token_similarity("driver supply demand", "demand driver supply") == 1.0
    assert duplicate_reason(candidate(), [prior]) is not None
