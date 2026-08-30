from __future__ import annotations

import json
from datetime import date

from daily_pm_case_lab.evidence import canonicalize_source_ids
from daily_pm_case_lab.publisher import publish_case
from daily_pm_case_lab.quality import REQUIRED_FILES, evaluate_quality, validate_case_directory

from .factories import packet, reviewer, study


def test_quality_gate_passes_grounded_spoiler_free_case() -> None:
    research = packet()
    report = evaluate_quality(
        packet=research,
        study=study(),
        reviewer=reviewer(),
        candidate_score=86,
        history=[],
    )
    assert report.publishable
    assert report.score == 86


def test_quality_gate_rejects_spoiler() -> None:
    research = packet()
    generated = study()
    generated.challenge_markdown += "\nThe answer is dynamic pricing."
    report = evaluate_quality(
        packet=research,
        study=generated,
        reviewer=reviewer(),
        candidate_score=90,
        history=[],
    )
    assert not report.publishable
    assert report.score <= 74
    assert any(
        check.name == "spoiler_free_challenge" and not check.passed for check in report.checks
    )


def test_canonicalizes_positional_and_repeated_digit_source_ids() -> None:
    research = packet()
    for index, source in enumerate(research.sources, start=1):
        source.id = f"S{index}{index}"
    research.claims[0].source_ids = ["S1", "S2"]
    research.timeline[0].source_ids = ["S11"]
    research.actual_decision[0].source_ids = ["S1"]
    normalized = canonicalize_source_ids(research)
    assert [source.id for source in normalized.sources] == [
        "S01",
        "S02",
        "S03",
        "S04",
        "S05",
    ]
    assert normalized.claims[0].source_ids == ["S01", "S02"]
    assert normalized.timeline[0].source_ids == ["S01"]


def test_atomic_publisher_writes_exact_file_set(tmp_path) -> None:
    research = packet()
    generated = study()
    report = evaluate_quality(
        packet=research,
        study=generated,
        reviewer=reviewer(),
        candidate_score=86,
        history=[],
    )
    final, manifest = publish_case(
        cases_dir=tmp_path / "cases",
        run_date=date(2026, 8, 30),
        packet=research,
        study=generated,
        quality=report,
        model="test-model",
    )
    assert {item.name for item in final.iterdir()} == REQUIRED_FILES
    assert manifest.quality_score == 86
    assert json.loads((final / "sources.json").read_text(encoding="utf-8"))["sources"]
    assert validate_case_directory(final).publishable
