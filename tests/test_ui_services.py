from __future__ import annotations

import asyncio
import json
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from daily_pm_case_lab.config import Settings
from daily_pm_case_lab.models import (
    Company,
    GenerationResult,
    HistoryRecord,
    Manifest,
    QualityReport,
    ResearchPriority,
)
from daily_pm_case_lab.ui import launcher
from daily_pm_case_lab.ui.services import (
    CaseLibrarySnapshot,
    CatalogSnapshot,
    GenerationAlreadyRunning,
    GenerationOutcome,
    GenerationRequest,
    HistorySnapshot,
    build_system_status,
    company_coverage,
    generate_case,
    generation_error_message,
    load_case_library,
    load_history_safe,
    read_case_markdown,
    run_generation_with_state,
    validate_existing_case,
)


def _manifest(*, company: str = "Uber", quality_score: int = 88) -> Manifest:
    return Manifest(
        date=date(2026, 8, 30),
        company=company,
        case_title="Marketplace balance",
        case_slug="marketplace-balance",
        category="Marketplace liquidity",
        difficulty="Hard",
        source_count=7,
        primary_source_count=2,
        quality_score=quality_score,
        generated_at=datetime.fromisoformat("2026-08-30T12:00:00+03:30"),
        model="test-model",
    )


def _company(company_id: str, name: str) -> Company:
    return Company(
        id=company_id,
        name=name,
        category="Marketplace",
        country="United States",
        public_company=True,
        research_priority=ResearchPriority.HIGH,
    )


def _history(company_id: str, company: str, run_date: date) -> HistoryRecord:
    return HistoryRecord(
        date=run_date,
        company=company,
        company_id=company_id,
        case_slug=f"{company_id}-case",
        case_title=f"{company} case",
        primary_problem="Marketplace imbalance",
        case_category="Marketplace",
        difficulty="Hard",
        sources_count=6,
    )


def test_case_library_uses_manifest_and_isolates_malformed_cases(tmp_path: Path) -> None:
    cases_dir = tmp_path / "cases"
    valid = cases_dir / "valid-case"
    invalid = cases_dir / "invalid-case"
    valid.mkdir(parents=True)
    invalid.mkdir()
    (valid / "manifest.json").write_text(_manifest().model_dump_json(), encoding="utf-8")
    (invalid / "manifest.json").write_text("{not-json", encoding="utf-8")

    snapshot = load_case_library(cases_dir)

    assert len(snapshot.entries) == 1
    assert snapshot.entries[0].manifest.case_title == "Marketplace balance"
    assert "01-challenge.md" in snapshot.entries[0].missing_files
    assert len(snapshot.issues) == 1
    assert snapshot.issues[0].location.endswith("invalid-case")


def test_case_reader_rejects_paths_outside_cases_directory(tmp_path: Path) -> None:
    cases_dir = tmp_path / "cases"
    cases_dir.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "01-challenge.md").write_text("secret", encoding="utf-8")

    with pytest.raises(ValueError, match="inside the configured cases directory"):
        read_case_markdown(cases_dir, outside, "Challenge")


def test_malformed_history_returns_a_safe_issue(tmp_path: Path) -> None:
    history_path = tmp_path / "history.jsonl"
    history_path.write_text('{"broken": true}\n', encoding="utf-8")

    snapshot = load_history_safe(history_path)

    assert snapshot.records == ()
    assert len(snapshot.issues) == 1
    assert "line 1" in snapshot.issues[0].message


def test_company_coverage_combines_catalog_and_history() -> None:
    companies = (_company("uber", "Uber"), _company("doordash", "DoorDash"))
    records = (
        _history("uber", "Uber", date(2026, 8, 1)),
        _history("uber", "Uber", date(2026, 8, 20)),
    )

    coverage = {item.company.id: item for item in company_coverage(companies, records)}

    assert coverage["uber"].case_count == 2
    assert coverage["uber"].last_covered == date(2026, 8, 20)
    assert coverage["doordash"].case_count == 0
    assert coverage["doordash"].last_covered is None


def test_system_status_exposes_no_secret_values(tmp_path: Path) -> None:
    secret = "sk-testSecretValue123456"
    github_token = "github-test-token"
    settings = Settings(
        root_dir=tmp_path,
        openai_api_key=secret,
        github_repository="acme/lab",
    )
    with patch("daily_pm_case_lab.ui.services.shutil.which", return_value="/usr/bin/gh"):
        status = build_system_status(
            settings,
            catalog=CatalogSnapshot(companies=(_company("uber", "Uber"),)),
            history=HistorySnapshot(records=()),
            library=CaseLibrarySnapshot(entries=()),
            environ={"GITHUB_TOKEN": github_token},
        )

    payload = json.dumps(asdict(status))
    assert status.api_key_configured
    assert status.issue_delivery_available
    assert secret not in payload
    assert github_token not in payload
    assert "OPENAI_API_KEY" not in payload


def test_exhausted_credit_error_is_concise_and_actionable(tmp_path: Path) -> None:
    settings = Settings(root_dir=tmp_path, openai_api_key="sk-testSecretValue123456")
    error = RuntimeError("429 insufficient_quota credit_balance_exhausted; no credits remaining")

    message = generation_error_message(error, settings, {})

    assert message == (
        "OpenAI API credits are exhausted for this project. Add credits in OpenAI Platform "
        "billing, then start a new generation."
    )
    assert "429" not in message
    assert "sk-" not in message


@pytest.mark.asyncio
async def test_generation_adapter_calls_existing_orchestrator_without_writes(
    tmp_path: Path,
) -> None:
    settings = Settings(root_dir=tmp_path, openai_api_key=None)
    captured: dict[str, object] = {}

    class FakeOrchestrator:
        async def generate(self, **kwargs):
            captured.update(kwargs)
            return GenerationResult(
                status="dry_run",
                selected_company="Uber",
                message="Shortlist: Uber",
            )

    request = GenerationRequest(
        run_date=date(2026, 8, 30),
        company_override="uber",
        dry_run=True,
    )
    outcome = await generate_case(
        settings,
        request,
        orchestrator_factory=lambda _: FakeOrchestrator(),
        environ={},
    )

    assert outcome.successful
    assert not outcome.wrote_case_or_history
    assert [event.event for event in outcome.progress] == [
        "generation.requested",
        "generation.started",
        "generation.completed",
    ]
    assert callable(captured.pop("progress_callback"))
    assert captured == {
        "run_date": date(2026, 8, 30),
        "company_override": "uber",
        "dry_run": True,
        "deliver_issue": False,
    }


@pytest.mark.asyncio
async def test_generation_adapter_redacts_known_secrets_from_failures(tmp_path: Path) -> None:
    secret = "sk-testSecretValue123456"
    settings = Settings(root_dir=tmp_path, openai_api_key=secret)

    class FailingOrchestrator:
        async def generate(self, **kwargs):
            raise RuntimeError(f"provider rejected {secret}")

    outcome = await generate_case(
        settings,
        GenerationRequest(run_date=date(2026, 8, 30)),
        orchestrator_factory=lambda _: FailingOrchestrator(),
        environ={},
    )

    assert not outcome.successful
    assert outcome.error_type == "RuntimeError"
    assert secret not in outcome.message
    assert "[REDACTED]" in outcome.message
    assert outcome.progress[-1].event == "generation.failed"


@pytest.mark.asyncio
async def test_generation_lifecycle_clears_running_state_after_success(tmp_path: Path) -> None:
    settings = Settings(root_dir=tmp_path)
    state: dict[str, object] = {"generation_running": False, "generation_state": "idle"}

    async def successful_generator(current_settings, request, callback):
        return GenerationOutcome(
            result=GenerationResult(status="dry_run", message="Done"),
            error_type=None,
            message="Done",
            wrote_case_or_history=False,
        )

    outcome = await run_generation_with_state(
        state,
        settings,
        GenerationRequest(run_date=date(2026, 8, 30), dry_run=True),
        generator=successful_generator,
    )

    assert outcome.successful
    assert state["generation_running"] is False
    assert state["generation_state"] == "dry_run"
    assert state["last_generation"] is outcome


@pytest.mark.asyncio
async def test_generation_lifecycle_clears_running_state_after_quality_rejection(
    tmp_path: Path,
) -> None:
    settings = Settings(root_dir=tmp_path)
    state: dict[str, object] = {}

    async def rejected_generator(current_settings, request, callback):
        return GenerationOutcome(
            result=GenerationResult(
                status="no_publishable_candidate",
                quality_score=58,
                message="Quality gate rejected the candidate",
            ),
            error_type=None,
            message="Quality gate rejected the candidate",
            wrote_case_or_history=False,
        )

    outcome = await run_generation_with_state(
        state,
        settings,
        GenerationRequest(run_date=date(2026, 8, 30)),
        generator=rejected_generator,
    )

    assert not outcome.successful
    assert state["generation_running"] is False
    assert state["generation_state"] == "no_publishable_candidate"


@pytest.mark.asyncio
async def test_generation_lifecycle_clears_running_state_after_failure(tmp_path: Path) -> None:
    settings = Settings(root_dir=tmp_path)
    state: dict[str, object] = {}

    async def failing_generator(current_settings, request, callback):
        raise RuntimeError("UI runner failed")

    with pytest.raises(RuntimeError, match="UI runner failed"):
        await run_generation_with_state(
            state,
            settings,
            GenerationRequest(run_date=date(2026, 8, 30)),
            generator=failing_generator,
        )

    assert state["generation_running"] is False
    assert state["generation_state"] == "failed"


@pytest.mark.asyncio
async def test_generation_lifecycle_rejects_duplicate_submit(tmp_path: Path) -> None:
    settings = Settings(root_dir=tmp_path)
    state: dict[str, object] = {"generation_running": True}

    with pytest.raises(GenerationAlreadyRunning):
        await run_generation_with_state(
            state,
            settings,
            GenerationRequest(run_date=date(2026, 8, 30)),
        )


@pytest.mark.asyncio
async def test_generation_timeout_returns_terminal_failure(tmp_path: Path) -> None:
    settings = Settings(root_dir=tmp_path)
    settings.generation_timeout_seconds = 0.01

    class SlowOrchestrator:
        run_id = "slow-run"

        async def generate(self, **kwargs):
            await asyncio.sleep(1)
            raise AssertionError("unreachable")

    outcome = await generate_case(
        settings,
        GenerationRequest(run_date=date(2026, 8, 30)),
        orchestrator_factory=lambda _: SlowOrchestrator(),
        environ={},
    )

    assert outcome.error_type == "TimeoutError"
    assert outcome.progress[-1].event == "generation.failed"
    assert "limit" in outcome.message


def test_validation_adapter_calls_existing_validator(tmp_path: Path) -> None:
    cases_dir = tmp_path / "cases"
    case_dir = cases_dir / "case"
    case_dir.mkdir(parents=True)
    report = QualityReport(score=100, publishable=True, checks=[])
    with patch(
        "daily_pm_case_lab.ui.services.validate_case_directory", return_value=report
    ) as validator:
        assert validate_existing_case(cases_dir, case_dir) is report
    validator.assert_called_once_with(case_dir.resolve())


def test_ui_launcher_uses_streamlit_module(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["pm-case-ui", "--server.headless=true"])
    with patch(
        "daily_pm_case_lab.ui.launcher.subprocess.run",
        return_value=SimpleNamespace(returncode=0),
    ) as run:
        assert launcher.main() == 0
    args = run.call_args.args[0]
    assert args[:4] == [launcher.sys.executable, "-m", "streamlit", "run"]
    assert args[-1] == "--server.headless=true"
