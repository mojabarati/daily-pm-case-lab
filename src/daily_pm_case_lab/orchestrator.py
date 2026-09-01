from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import date

from .catalog import load_catalog, resolve_company
from .config import Settings
from .delivery import GitHubIssueDelivery
from .evidence import canonicalize_source_ids
from .gateway import AgentBudgetExceeded, AgentGateway, OpenAIAgentGateway
from .history import append_history, duplicate_reason, load_history
from .logging_utils import redact
from .models import GenerationResult, HistoryRecord, ResearchPacket
from .progress import ProgressCallback, emit_progress
from .publisher import publish_case
from .quality import evaluate_quality
from .scoring import researched_score, with_score
from .selection import shortlist_companies

LOGGER = logging.getLogger(__name__)


class DailyCaseOrchestrator:
    def __init__(self, settings: Settings, gateway: AgentGateway | None = None) -> None:
        self.settings = settings
        self.run_id = uuid.uuid4().hex
        self.gateway = gateway or OpenAIAgentGateway(settings, self.run_id)

    def _retain_failed_diagnostic(self, candidate_slug, packet, study, quality) -> str | None:
        if not self.settings.retain_failed:
            return None
        diagnostics_dir = self.settings.root_dir / "logs" / "failed"
        diagnostics_dir.mkdir(parents=True, exist_ok=True)
        path = diagnostics_dir / f"{self.run_id}-{candidate_slug}.json"
        payload = redact(
            {
                "run_id": self.run_id,
                "model": self.settings.openai_model,
                "research_packet": packet.model_dump(mode="json"),
                "case_study": study.model_dump(mode="json"),
                "quality_report": quality.model_dump(mode="json"),
            }
        )
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return str(path)

    async def generate(
        self,
        *,
        run_date: date,
        company_override: str | None = None,
        dry_run: bool = False,
        deliver_issue: bool = False,
        progress_callback: ProgressCallback | None = None,
    ) -> GenerationResult:
        def progress(
            event: str,
            stage: str,
            status: str,
            message: str,
            *,
            company_id: str | None = None,
            candidate_slug: str | None = None,
            attempt: int | None = None,
            elapsed_ms: int | None = None,
        ) -> None:
            emit_progress(
                progress_callback,
                event=event,
                stage=stage,
                status=status,  # type: ignore[arg-type]
                message=message,
                run_id=self.run_id,
                run_date=run_date,
                company_id=company_id,
                candidate_slug=candidate_slug,
                attempt=attempt,
                elapsed_ms=elapsed_ms,
            )

        catalog_path = self.settings.data_dir / "company_catalog.yaml"
        history_path = self.settings.data_dir / "history.jsonl"
        companies = load_catalog(catalog_path)
        history = load_history(history_path)
        progress(
            "config.validated",
            "configuration",
            "completed",
            (
                f"Configuration validated; loaded {len(companies)} companies and "
                f"{len(history)} history records."
            ),
        )
        selection_started = time.monotonic()
        progress(
            "company.selection.started",
            "company-selection",
            "started",
            "Selecting the company shortlist.",
        )
        if company_override:
            shortlist = [resolve_company(companies, company_override)]
        else:
            shortlist = shortlist_companies(
                companies, history, run_date, self.settings.max_case_candidates
            )
        progress(
            "company.selection.completed",
            "company-selection",
            "completed",
            "Company shortlist selected: " + ", ".join(company.name for company in shortlist),
            company_id=shortlist[0].id if len(shortlist) == 1 else None,
            elapsed_ms=round((time.monotonic() - selection_started) * 1000),
        )
        if dry_run:
            return GenerationResult(
                status="dry_run",
                selected_company=shortlist[0].name if shortlist else None,
                attempted_candidates=0,
                agent_runs=0,
                message="Shortlist: " + ", ".join(company.name for company in shortlist),
            )

        self.settings.require_api_key()
        history_summary = [
            {
                "company": record.company,
                "case_title": record.case_title,
                "primary_problem": record.primary_problem,
                "category": record.case_category,
            }
            for record in history[-30:]
        ]
        candidate_started = time.monotonic()
        progress(
            "candidate.selection.started",
            "candidate-selection",
            "started",
            "Researching and ranking candidate cases.",
        )
        scout_result = await self.gateway.scout(shortlist, history_summary, run_date)
        allowed_ids = {company.id for company in shortlist}
        candidates = [
            candidate
            for candidate in scout_result.candidates
            if candidate.company_id in allowed_ids and duplicate_reason(candidate, history) is None
        ]
        candidates.sort(key=lambda candidate: candidate.score.total, reverse=True)
        candidates = candidates[: self.settings.max_case_candidates]
        progress(
            "candidate.selection.completed",
            "candidate-selection",
            "completed",
            f"Selected {len(candidates)} non-duplicate candidate case(s).",
            elapsed_ms=round((time.monotonic() - candidate_started) * 1000),
        )
        attempted = 0
        last_quality_score: int | None = None
        last_company: str | None = None
        last_blockers: list[str] = []
        last_diagnostic: str | None = None

        for candidate in candidates:
            attempted += 1
            best_packet: ResearchPacket | None = None
            best_total = -1
            prior_packet: ResearchPacket | None = None
            for pass_number in range(1, self.settings.max_research_passes + 1):
                research_started = time.monotonic()
                progress(
                    "research.started",
                    "research",
                    "started",
                    f"Research pass {pass_number} started for {candidate.company_name}.",
                    company_id=candidate.company_id,
                    candidate_slug=candidate.case_slug,
                    attempt=pass_number,
                )
                try:
                    packet = await self.gateway.research(candidate, pass_number, prior_packet)
                except AgentBudgetExceeded:
                    return GenerationResult(
                        status="budget_exhausted",
                        selected_company=candidate.company_name,
                        attempted_candidates=attempted,
                        agent_runs=self.gateway.runs_used,
                        message="Agent call budget exhausted before a case passed quality gates.",
                    )
                progress(
                    "research.completed",
                    "research",
                    "completed",
                    f"Research pass {pass_number} returned {len(packet.sources)} sources.",
                    company_id=candidate.company_id,
                    candidate_slug=candidate.case_slug,
                    attempt=pass_number,
                    elapsed_ms=round((time.monotonic() - research_started) * 1000),
                )
                evidence_started = time.monotonic()
                progress(
                    "evidence.validation.started",
                    "evidence-validation",
                    "started",
                    "Validating source IDs and evidence integrity.",
                    company_id=candidate.company_id,
                    candidate_slug=candidate.case_slug,
                    attempt=pass_number,
                )
                if (
                    packet.candidate.company_id != candidate.company_id
                    or packet.candidate.case_slug != candidate.case_slug
                ):
                    LOGGER.warning(
                        "research packet candidate mismatch",
                        extra={
                            "run_id": self.run_id,
                            "stage": "research-validation",
                            "status": "rejected",
                        },
                    )
                    progress(
                        "evidence.validation.rejected",
                        "evidence-validation",
                        "rejected",
                        "Research packet did not match the selected candidate.",
                        company_id=candidate.company_id,
                        candidate_slug=candidate.case_slug,
                        attempt=pass_number,
                    )
                    break
                try:
                    packet = canonicalize_source_ids(packet)
                except ValueError as exc:
                    LOGGER.warning(
                        "research packet evidence integrity failed: %s",
                        str(exc),
                        extra={
                            "run_id": self.run_id,
                            "stage": "research-validation",
                            "status": "rejected",
                        },
                    )
                    progress(
                        "evidence.validation.rejected",
                        "evidence-validation",
                        "rejected",
                        f"Evidence validation rejected pass {pass_number}: {exc}",
                        company_id=candidate.company_id,
                        candidate_slug=candidate.case_slug,
                        attempt=pass_number,
                    )
                    continue
                progress(
                    "evidence.validation.completed",
                    "evidence-validation",
                    "completed",
                    "Evidence integrity checks completed.",
                    company_id=candidate.company_id,
                    candidate_slug=candidate.case_slug,
                    attempt=pass_number,
                    elapsed_ms=round((time.monotonic() - evidence_started) * 1000),
                )
                scoring_started = time.monotonic()
                progress(
                    "candidate.scoring.started",
                    "candidate-scoring",
                    "started",
                    "Scoring the researched candidate.",
                    company_id=candidate.company_id,
                    candidate_slug=candidate.case_slug,
                    attempt=pass_number,
                )
                score = researched_score(candidate, packet)
                packet.candidate = with_score(candidate, score)
                progress(
                    "candidate.scoring.completed",
                    "candidate-scoring",
                    "completed",
                    f"Candidate research score: {score.total}/100.",
                    company_id=candidate.company_id,
                    candidate_slug=candidate.case_slug,
                    attempt=pass_number,
                    elapsed_ms=round((time.monotonic() - scoring_started) * 1000),
                )
                if score.total > best_total:
                    best_packet, best_total = packet, score.total
                prior_packet = packet
                source_types = {source.type.casefold() for source in packet.sources}
                if (
                    score.total >= 75
                    and len({str(source.url) for source in packet.sources}) >= 5
                    and len(source_types) >= 2
                    and (
                        any(source.is_primary for source in packet.sources)
                        or packet.primary_source_unavailable_reason
                    )
                ):
                    break
            if best_packet is None:
                continue
            synthesis_started = time.monotonic()
            progress(
                "case.generation.started",
                "case-generation",
                "started",
                "Generating the case study and independent review.",
                company_id=candidate.company_id,
                candidate_slug=candidate.case_slug,
            )
            try:
                study = await self.gateway.synthesize(best_packet)
                reviewer = await self.gateway.review(best_packet, study)
            except AgentBudgetExceeded:
                return GenerationResult(
                    status="budget_exhausted",
                    selected_company=candidate.company_name,
                    attempted_candidates=attempted,
                    agent_runs=self.gateway.runs_used,
                    message="Agent call budget exhausted before synthesis/review completed.",
                )
            progress(
                "case.generation.completed",
                "case-generation",
                "completed",
                "Case synthesis and review completed.",
                company_id=candidate.company_id,
                candidate_slug=candidate.case_slug,
                elapsed_ms=round((time.monotonic() - synthesis_started) * 1000),
            )
            quality_started = time.monotonic()
            progress(
                "quality.validation.started",
                "quality-validation",
                "started",
                "Running deterministic quality and spoiler checks.",
                company_id=candidate.company_id,
                candidate_slug=candidate.case_slug,
            )
            quality = evaluate_quality(
                packet=best_packet,
                study=study,
                reviewer=reviewer,
                candidate_score=best_packet.candidate.score.total,
                history=history,
            )
            for revision_number in range(1, self.settings.max_revision_passes + 1):
                if quality.publishable:
                    break
                remaining_runs = self.settings.max_agent_runs - self.gateway.runs_used
                if remaining_runs < 2:
                    break
                progress(
                    "quality.validation.rejected",
                    "quality-validation",
                    "rejected",
                    (
                        f"Draft scored {quality.score}/100; starting bounded reviewer-guided "
                        f"revision {revision_number}/{self.settings.max_revision_passes}."
                    ),
                    company_id=candidate.company_id,
                    candidate_slug=candidate.case_slug,
                    elapsed_ms=round((time.monotonic() - quality_started) * 1000),
                )
                revision_started = time.monotonic()
                progress(
                    "case.revision.started",
                    "case-revision",
                    "started",
                    f"Revision {revision_number}: correcting every reviewer finding.",
                    company_id=candidate.company_id,
                    candidate_slug=candidate.case_slug,
                    attempt=revision_number,
                )
                try:
                    study = await self.gateway.revise(best_packet, study, reviewer)
                    reviewer = await self.gateway.review(best_packet, study)
                except AgentBudgetExceeded:
                    return GenerationResult(
                        status="budget_exhausted",
                        selected_company=candidate.company_name,
                        attempted_candidates=attempted,
                        agent_runs=self.gateway.runs_used,
                        message="Agent call budget exhausted during reviewer-guided revision.",
                    )
                quality = evaluate_quality(
                    packet=best_packet,
                    study=study,
                    reviewer=reviewer,
                    candidate_score=best_packet.candidate.score.total,
                    history=history,
                )
                progress(
                    "case.revision.completed",
                    "case-revision",
                    "completed",
                    f"Revision {revision_number} re-reviewed at {quality.score}/100.",
                    company_id=candidate.company_id,
                    candidate_slug=candidate.case_slug,
                    attempt=revision_number,
                    elapsed_ms=round((time.monotonic() - revision_started) * 1000),
                )
                quality_started = time.monotonic()
            if not quality.publishable:
                progress(
                    "quality.validation.rejected",
                    "quality-validation",
                    "rejected",
                    f"Candidate scored {quality.score}/100 and did not pass all hard checks.",
                    company_id=candidate.company_id,
                    candidate_slug=candidate.case_slug,
                    elapsed_ms=round((time.monotonic() - quality_started) * 1000),
                )
                last_quality_score = quality.score
                last_company = candidate.company_name
                last_blockers = quality.blockers
                last_diagnostic = self._retain_failed_diagnostic(
                    candidate.case_slug, best_packet, study, quality
                )
                LOGGER.warning(
                    "candidate failed quality gate: %s",
                    "; ".join(quality.blockers[:5]),
                    extra={
                        "run_id": self.run_id,
                        "stage": "quality-gate",
                        "attempt": attempted,
                        "status": "rejected",
                    },
                )
                continue

            progress(
                "quality.validation.completed",
                "quality-validation",
                "completed",
                f"Quality gate passed at {quality.score}/100.",
                company_id=candidate.company_id,
                candidate_slug=candidate.case_slug,
                elapsed_ms=round((time.monotonic() - quality_started) * 1000),
            )
            publishing_started = time.monotonic()
            progress(
                "publishing.started",
                "publishing",
                "started",
                "Publishing Markdown and JSON case artifacts.",
                company_id=candidate.company_id,
                candidate_slug=candidate.case_slug,
            )

            final_path, manifest = publish_case(
                cases_dir=self.settings.cases_dir,
                run_date=run_date,
                packet=best_packet,
                study=study,
                quality=quality,
                model=self.settings.openai_model,
            )
            progress(
                "publishing.completed",
                "publishing",
                "completed",
                "Case artifacts published locally.",
                company_id=candidate.company_id,
                candidate_slug=candidate.case_slug,
                elapsed_ms=round((time.monotonic() - publishing_started) * 1000),
            )
            record = HistoryRecord(
                date=run_date,
                company=best_packet.candidate.company_name,
                company_id=best_packet.candidate.company_id,
                case_slug=best_packet.candidate.case_slug,
                case_title=best_packet.candidate.case_title,
                primary_problem=best_packet.candidate.primary_problem,
                case_category=best_packet.candidate.case_category,
                difficulty=best_packet.candidate.difficulty,
                sources_count=len(best_packet.sources),
            )
            history_started = time.monotonic()
            progress(
                "history.update.started",
                "history-update",
                "started",
                "Updating duplicate-protection history.",
                company_id=candidate.company_id,
                candidate_slug=candidate.case_slug,
            )
            append_history(history_path, record)
            progress(
                "history.update.completed",
                "history-update",
                "completed",
                "History updated.",
                company_id=candidate.company_id,
                candidate_slug=candidate.case_slug,
                elapsed_ms=round((time.monotonic() - history_started) * 1000),
            )
            issue_url = None
            if deliver_issue:
                if not self.settings.github_repository:
                    raise RuntimeError("PM_CASE_GITHUB_REPOSITORY is required with --deliver-issue")
                repository_relative_path = final_path.relative_to(self.settings.root_dir)
                issue_started = time.monotonic()
                progress(
                    "issue.delivery.started",
                    "issue-delivery",
                    "started",
                    "Creating the GitHub Issue.",
                    company_id=candidate.company_id,
                    candidate_slug=candidate.case_slug,
                )
                issue_url = GitHubIssueDelivery(self.settings.github_repository).deliver(
                    repository_relative_path, manifest
                )
                progress(
                    "issue.delivery.completed",
                    "issue-delivery",
                    "completed",
                    "GitHub Issue created.",
                    company_id=candidate.company_id,
                    candidate_slug=candidate.case_slug,
                    elapsed_ms=round((time.monotonic() - issue_started) * 1000),
                )
            return GenerationResult(
                status="published",
                case_directory=str(final_path),
                quality_score=quality.score,
                selected_company=best_packet.candidate.company_name,
                attempted_candidates=attempted,
                agent_runs=self.gateway.runs_used,
                issue_url=issue_url,
                message="Case passed all hard checks and was published.",
            )

        return GenerationResult(
            status="no_publishable_candidate",
            quality_score=last_quality_score,
            selected_company=last_company,
            attempted_candidates=attempted,
            agent_runs=self.gateway.runs_used,
            diagnostic_file=last_diagnostic,
            message=(
                "No candidate reached the 75/100 quality threshold and all hard checks. "
                + ("Top blockers: " + "; ".join(last_blockers[:5]) if last_blockers else "")
            ).strip(),
        )
