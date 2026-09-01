from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path

import pytest

from daily_pm_case_lab.config import Settings
from daily_pm_case_lab.models import ScoutResult
from daily_pm_case_lab.orchestrator import DailyCaseOrchestrator

from .factories import candidate, packet, reviewer, study

ROOT = Path(__file__).resolve().parents[1]


class FakeGateway:
    def __init__(self) -> None:
        self._runs = 0
        self.case_candidate = candidate()

    @property
    def runs_used(self) -> int:
        return self._runs

    async def scout(self, companies, history_summary, run_date):
        self._runs += 1
        self.case_candidate.company_id = companies[0].id
        self.case_candidate.company_name = companies[0].name
        return ScoutResult(candidates=[self.case_candidate])

    async def research(self, case_candidate, pass_number, prior_packet):
        self._runs += 1
        return packet(case_candidate)

    async def synthesize(self, research_packet):
        self._runs += 1
        return study()

    async def review(self, research_packet, generated_study):
        self._runs += 1
        return reviewer()

    async def revise(self, research_packet, generated_study, reviewer_report):
        self._runs += 1
        return study()


@pytest.mark.asyncio
async def test_offline_full_orchestration_publishes_and_updates_history(tmp_path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    shutil.copyfile(ROOT / "data" / "company_catalog.yaml", data_dir / "company_catalog.yaml")
    (data_dir / "history.jsonl").write_text("", encoding="utf-8")
    settings = Settings(
        root_dir=tmp_path,
        openai_api_key="test-only-key",
        max_case_candidates=1,
        max_research_passes=1,
        max_agent_runs=4,
    )
    gateway = FakeGateway()
    progress = []
    result = await DailyCaseOrchestrator(settings, gateway).generate(
        run_date=date(2026, 8, 30),
        company_override="Uber",
        progress_callback=progress.append,
    )
    assert result.status == "published"
    assert result.quality_score >= 75
    assert Path(result.case_directory or "").exists()
    assert len((data_dir / "history.jsonl").read_text(encoding="utf-8").splitlines()) == 1
    events = [item.event for item in progress]
    assert events.index("company.selection.completed") < events.index("candidate.selection.started")
    assert events.index("research.started") < events.index("research.completed")
    assert events.index("quality.validation.completed") < events.index("publishing.started")
    assert events[-1] == "history.update.completed"


@pytest.mark.asyncio
async def test_dry_run_makes_no_agent_calls_or_writes(tmp_path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    shutil.copyfile(ROOT / "data" / "company_catalog.yaml", data_dir / "company_catalog.yaml")
    (data_dir / "history.jsonl").write_text("", encoding="utf-8")
    settings = Settings(root_dir=tmp_path, openai_api_key=None)
    gateway = FakeGateway()
    result = await DailyCaseOrchestrator(settings, gateway).generate(
        run_date=date(2026, 8, 30), dry_run=True
    )
    assert result.status == "dry_run"
    assert gateway.runs_used == 0
    assert not (tmp_path / "cases").exists()


@pytest.mark.asyncio
async def test_rejected_draft_gets_bounded_revisions_before_publish(tmp_path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    shutil.copyfile(ROOT / "data" / "company_catalog.yaml", data_dir / "company_catalog.yaml")
    (data_dir / "history.jsonl").write_text("", encoding="utf-8")
    settings = Settings(
        root_dir=tmp_path,
        openai_api_key="test-only-key",
        max_case_candidates=1,
        max_research_passes=1,
        max_agent_runs=8,
    )

    class RevisionGateway(FakeGateway):
        def __init__(self) -> None:
            super().__init__()
            self.review_calls = 0
            self.revision_calls = 0

        async def review(self, research_packet, generated_study):
            self._runs += 1
            self.review_calls += 1
            report = reviewer(score=70 if self.review_calls <= 2 else 88)
            if self.review_calls <= 2:
                report.blockers = ["Unsupported draft assumption"]
            return report

        async def revise(self, research_packet, generated_study, reviewer_report):
            self._runs += 1
            self.revision_calls += 1
            return study()

    gateway = RevisionGateway()
    progress = []
    result = await DailyCaseOrchestrator(settings, gateway).generate(
        run_date=date(2026, 9, 1),
        company_override="Uber",
        progress_callback=progress.append,
    )

    assert result.status == "published"
    assert gateway.review_calls == 3
    assert gateway.revision_calls == 2
    events = [item.event for item in progress]
    assert events.count("case.revision.started") == 2
    assert events.index("case.revision.completed") < events.index("publishing.started")
