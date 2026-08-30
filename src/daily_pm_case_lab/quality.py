from __future__ import annotations

import json
import re
from pathlib import Path

from .history import duplicate_reason, normalized_tokens
from .models import (
    CaseStudy,
    HistoryRecord,
    QualityCheck,
    QualityReport,
    ResearchPacket,
    ReviewerReport,
)

MIN_QUALITY_SCORE = 75
SECRET_RE = re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b")
REQUIRED_FILES = {
    "00-overview.md",
    "01-challenge.md",
    "02-evidence-pack.md",
    "03-what-company-did.md",
    "04-pm-analysis.md",
    "05-model-answer.md",
    "06-interview-drill.md",
    "sources.json",
    "manifest.json",
}


def contains_spoiler(text: str, decision_terms: list[str]) -> list[str]:
    haystack = normalized_tokens(text)
    matches: list[str] = []
    for term in decision_terms:
        tokens = normalized_tokens(term)
        if tokens and tokens <= haystack:
            matches.append(term)
    return matches


def _all_markdown(study: CaseStudy) -> str:
    return "\n".join(
        [
            study.overview_markdown,
            study.challenge_markdown,
            study.evidence_pack_markdown,
            study.what_company_did_markdown,
            study.pm_analysis_markdown,
            study.model_answer_markdown,
            study.interview_drill_markdown,
        ]
    )


def evaluate_quality(
    *,
    packet: ResearchPacket,
    study: CaseStudy,
    reviewer: ReviewerReport,
    candidate_score: int,
    history: list[HistoryRecord],
) -> QualityReport:
    source_ids = {source.id for source in packet.sources}
    unique_urls = {str(source.url).rstrip("/").casefold() for source in packet.sources}
    source_types = {source.type.casefold() for source in packet.sources}
    primary_count = sum(source.is_primary for source in packet.sources)
    referenced_ids: set[str] = set()
    for claim in [
        *packet.claims,
        *packet.market_context,
        *packet.competitor_context,
        *packet.actual_decision,
        *packet.outcomes,
    ]:
        referenced_ids.update(claim.source_ids)
    for statement in packet.statements:
        referenced_ids.add(statement.source_id)
    for event in packet.timeline:
        referenced_ids.update(event.source_ids)

    duplicate = duplicate_reason(packet.candidate, history)
    candidate_context = normalized_tokens(
        " ".join(
            [
                packet.candidate.company_name,
                packet.candidate.case_title,
                packet.candidate.primary_problem,
                packet.candidate.product,
                packet.candidate.case_category,
            ]
        )
    )
    distinctive_decision_terms = [
        term
        for term in packet.decision_terms
        if not normalized_tokens(term) <= candidate_context
    ]
    spoiler_matches = contains_spoiler(
        f"{study.overview_markdown}\n{study.challenge_markdown}",
        distinctive_decision_terms,
    )
    all_markdown = _all_markdown(study)
    checks = [
        QualityCheck(
            name="meaningful_sources",
            passed=len(unique_urls) >= 5,
            detail=f"{len(unique_urls)} unique source URLs",
        ),
        QualityCheck(
            name="primary_source",
            passed=primary_count >= 1 or bool(packet.primary_source_unavailable_reason),
            detail=(
                f"{primary_count} primary sources"
                if primary_count
                else packet.primary_source_unavailable_reason
                or "No primary source and no evidence-backed explanation"
            ),
        ),
        QualityCheck(
            name="source_diversity",
            passed=len(source_types) >= 2,
            detail=f"{len(source_types)} source categories",
        ),
        QualityCheck(
            name="source_references_resolve",
            passed=referenced_ids <= source_ids,
            detail=f"Unresolved IDs: {sorted(referenced_ids - source_ids)}",
        ),
        QualityCheck(
            name="spoiler_free_challenge",
            passed=not spoiler_matches,
            detail=f"Decision terms found: {spoiler_matches}",
        ),
        QualityCheck(
            name="duplicate_protection",
            passed=duplicate is None,
            detail=duplicate or "No duplicate detected",
        ),
        QualityCheck(
            name="challenge_depth",
            passed=len(study.challenge_markdown) >= 900
            and "Metrics" in study.challenge_markdown
            and "Guardrail" in study.challenge_markdown,
            detail="Challenge length and metrics/guardrail prompts",
        ),
        QualityCheck(
            name="critical_analysis",
            passed="What Could Have Been Done Better" in study.pm_analysis_markdown
            and "Trade-off" in study.pm_analysis_markdown,
            detail="Required critique and trade-off analysis",
        ),
        QualityCheck(
            name="model_answer",
            passed=len(study.model_answer_markdown) >= 1200
            and "MVP" in study.model_answer_markdown
            and "Guardrail" in study.model_answer_markdown,
            detail="Model answer depth and required concepts",
        ),
        QualityCheck(
            name="interview_drill",
            passed="Evaluation Rubric" in study.interview_drill_markdown,
            detail="Interview evaluation rubric present",
        ),
        QualityCheck(
            name="secret_scan",
            passed=SECRET_RE.search(all_markdown) is None,
            detail="Generated Markdown contains no API-key-like value",
        ),
    ]
    blockers = [check.detail for check in checks if not check.passed]
    blockers.extend(reviewer.blockers)
    blockers.extend(f"Unsupported: {claim}" for claim in reviewer.unsupported_claims)
    blockers.extend(f"Spoiler: {finding}" for finding in reviewer.spoiler_findings)
    score = min(candidate_score, reviewer.score)
    if blockers:
        score = min(score, 74)
    return QualityReport(
        score=score,
        publishable=score >= MIN_QUALITY_SCORE and not blockers,
        checks=[*checks, *reviewer.checks],
        blockers=blockers,
    )


def validate_case_directory(path: Path) -> QualityReport:
    present = {item.name for item in path.iterdir()} if path.is_dir() else set()
    missing = sorted(REQUIRED_FILES - present)
    checks = [
        QualityCheck(
            name="required_files",
            passed=not missing,
            detail=f"Missing files: {missing}",
        )
    ]
    blockers = list(checks[0].detail for _ in [0] if missing)
    if not missing:
        try:
            manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
            sources = json.loads((path / "sources.json").read_text(encoding="utf-8"))
            source_rows = sources.get("sources", [])
            urls = [row.get("url", "") for row in source_rows]
            source_check = len(urls) >= 5 and all(
                value.startswith(("http://", "https://")) for value in urls
            )
            checks.extend(
                [
                    QualityCheck(
                        name="manifest_status",
                        passed=manifest.get("status") == "published"
                        and int(manifest.get("quality_score", 0)) >= MIN_QUALITY_SCORE,
                        detail="Published manifest with quality score >= 75",
                    ),
                    QualityCheck(
                        name="source_file",
                        passed=source_check,
                        detail=f"{len(urls)} HTTP(S) sources",
                    ),
                ]
            )
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            blockers.append(f"Invalid JSON artifact: {type(exc).__name__}")
    blockers.extend(check.detail for check in checks if not check.passed)
    return QualityReport(
        score=100 if not blockers else 0,
        publishable=not blockers,
        checks=checks,
        blockers=blockers,
    )
