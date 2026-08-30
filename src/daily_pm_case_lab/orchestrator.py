from __future__ import annotations

import logging
import uuid
from datetime import date

from .catalog import load_catalog, resolve_company
from .config import Settings
from .delivery import GitHubIssueDelivery
from .gateway import AgentBudgetExceeded, AgentGateway, OpenAIAgentGateway
from .history import append_history, duplicate_reason, load_history
from .models import GenerationResult, HistoryRecord, ResearchPacket
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

    async def generate(
        self,
        *,
        run_date: date,
        company_override: str | None = None,
        dry_run: bool = False,
        deliver_issue: bool = False,
    ) -> GenerationResult:
        catalog_path = self.settings.data_dir / "company_catalog.yaml"
        history_path = self.settings.data_dir / "history.jsonl"
        companies = load_catalog(catalog_path)
        history = load_history(history_path)
        if company_override:
            shortlist = [resolve_company(companies, company_override)]
        else:
            shortlist = shortlist_companies(
                companies, history, run_date, self.settings.max_case_candidates
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
        scout_result = await self.gateway.scout(shortlist, history_summary, run_date)
        allowed_ids = {company.id for company in shortlist}
        candidates = [
            candidate
            for candidate in scout_result.candidates
            if candidate.company_id in allowed_ids and duplicate_reason(candidate, history) is None
        ]
        candidates.sort(key=lambda candidate: candidate.score.total, reverse=True)
        candidates = candidates[: self.settings.max_case_candidates]
        attempted = 0

        for candidate in candidates:
            attempted += 1
            best_packet: ResearchPacket | None = None
            best_total = -1
            prior_packet: ResearchPacket | None = None
            for pass_number in range(1, self.settings.max_research_passes + 1):
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
                    break
                score = researched_score(candidate, packet)
                packet.candidate = with_score(candidate, score)
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
            quality = evaluate_quality(
                packet=best_packet,
                study=study,
                reviewer=reviewer,
                candidate_score=best_packet.candidate.score.total,
                history=history,
            )
            if not quality.publishable:
                LOGGER.warning(
                    "candidate failed quality gate",
                    extra={
                        "run_id": self.run_id,
                        "stage": "quality-gate",
                        "attempt": attempted,
                        "status": "rejected",
                    },
                )
                continue

            final_path, manifest = publish_case(
                cases_dir=self.settings.cases_dir,
                run_date=run_date,
                packet=best_packet,
                study=study,
                quality=quality,
                model=self.settings.openai_model,
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
            append_history(history_path, record)
            issue_url = None
            if deliver_issue:
                if not self.settings.github_repository:
                    raise RuntimeError("PM_CASE_GITHUB_REPOSITORY is required with --deliver-issue")
                repository_relative_path = final_path.relative_to(self.settings.root_dir)
                issue_url = GitHubIssueDelivery(self.settings.github_repository).deliver(
                    repository_relative_path, manifest
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
            attempted_candidates=attempted,
            agent_runs=self.gateway.runs_used,
            message="No candidate reached the 75/100 quality threshold and all hard checks.",
        )
