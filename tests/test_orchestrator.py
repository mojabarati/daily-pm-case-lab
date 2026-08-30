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
    result = await DailyCaseOrchestrator(settings, gateway).generate(
        run_date=date(2026, 8, 30), company_override="Uber"
    )
    assert result.status == "published"
    assert result.quality_score >= 75
    assert Path(result.case_directory or "").exists()
    assert len((data_dir / "history.jsonl").read_text(encoding="utf-8").splitlines()) == 1


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
