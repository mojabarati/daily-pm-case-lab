from __future__ import annotations

from collections import Counter
from pathlib import Path

import yaml
from pydantic import TypeAdapter

from .models import Company

EXPECTED_COMPANY_COUNT = 100


def load_catalog(path: Path) -> list[Company]:
    if not path.exists():
        raise FileNotFoundError(f"Company catalog not found: {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    companies = TypeAdapter(list[Company]).validate_python(raw)
    validate_catalog(companies)
    return companies


def validate_catalog(companies: list[Company]) -> None:
    if len(companies) != EXPECTED_COMPANY_COUNT:
        raise ValueError(f"Company catalog must contain exactly {EXPECTED_COMPANY_COUNT} entries")
    ids = [company.id for company in companies]
    names = [company.name.casefold() for company in companies]
    if duplicates := [item for item, count in Counter(ids).items() if count > 1]:
        raise ValueError(f"Duplicate company IDs: {', '.join(sorted(duplicates))}")
    if duplicates := [item for item, count in Counter(names).items() if count > 1]:
        raise ValueError(f"Duplicate company names: {', '.join(sorted(duplicates))}")
    if len({company.category for company in companies}) < 8:
        raise ValueError("Company catalog must span at least eight categories")


def resolve_company(companies: list[Company], query: str) -> Company:
    needle = query.strip().casefold()
    for company in companies:
        names = {company.id.casefold(), company.name.casefold()}
        names.update(alias.casefold() for alias in company.aliases)
        if needle in names:
            return company
    raise ValueError(f"Unknown company: {query}")
