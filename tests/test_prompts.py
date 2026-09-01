from __future__ import annotations

from daily_pm_case_lab.models import CaseStudy, ReviewerReport
from daily_pm_case_lab.prompts import revision_prompt, synthesis_prompt

from .factories import packet


def test_synthesis_prompt_protects_decision_time_and_experiment_rigor() -> None:
    prompt = synthesis_prompt(packet())

    assert "must not be used to claim" in prompt
    assert "on or before the cutoff" in prompt
    assert "Label any causal mechanism" in prompt
    assert "evaluation window" in prompt
    assert "threshold-setting logic" in prompt
    assert "scenario assumption" in prompt
    assert "remove every citation" in prompt
    assert "without exception" in prompt


def test_revision_prompt_requires_literal_removal_of_unsupported_history() -> None:
    study = CaseStudy(
        overview_markdown="overview",
        challenge_markdown="challenge",
        evidence_pack_markdown="evidence",
        what_company_did_markdown="decision",
        pm_analysis_markdown="analysis",
        model_answer_markdown="answer",
        interview_drill_markdown="drill",
        estimated_exercise_minutes=60,
        competencies=["strategy"],
    )
    reviewer = ReviewerReport(
        score=70,
        checks=[],
        unsupported_claims=["The company rejected every alternative."],
    )

    prompt = revision_prompt(packet(), study, reviewer)

    assert "literal edit checklist" in prompt
    assert "delete the unsupported clause" in prompt
    assert "labels cannot rescue an unsupported historical claim" in prompt
    assert "The company rejected every alternative." in prompt
