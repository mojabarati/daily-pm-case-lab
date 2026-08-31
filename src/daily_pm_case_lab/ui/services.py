from __future__ import annotations

import asyncio
import os
import shutil
import sys
from collections import Counter
from collections.abc import Awaitable, Callable, Mapping, MutableMapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Protocol

from dotenv import load_dotenv
from pydantic import ValidationError

from daily_pm_case_lab import __version__
from daily_pm_case_lab.catalog import load_catalog
from daily_pm_case_lab.config import Settings
from daily_pm_case_lab.history import coverage_counts, last_seen, load_history
from daily_pm_case_lab.logging_utils import redact
from daily_pm_case_lab.models import (
    Company,
    GenerationResult,
    HistoryRecord,
    Manifest,
    QualityReport,
)
from daily_pm_case_lab.orchestrator import DailyCaseOrchestrator
from daily_pm_case_lab.progress import GenerationProgress, ProgressCallback, emit_progress
from daily_pm_case_lab.quality import REQUIRED_FILES, validate_case_directory

MARKDOWN_FILES = {
    "Overview": "00-overview.md",
    "Challenge": "01-challenge.md",
    "Evidence": "02-evidence-pack.md",
    "What Company Did": "03-what-company-did.md",
    "PM Analysis": "04-pm-analysis.md",
    "Model Answer": "05-model-answer.md",
    "Interview Drill": "06-interview-drill.md",
}
SPOILER_SECTIONS = {"What Company Did", "PM Analysis", "Model Answer"}


@dataclass(frozen=True, slots=True)
class LoadIssue:
    location: str
    message: str


@dataclass(frozen=True, slots=True)
class CatalogSnapshot:
    companies: tuple[Company, ...]
    issues: tuple[LoadIssue, ...] = ()


@dataclass(frozen=True, slots=True)
class HistorySnapshot:
    records: tuple[HistoryRecord, ...]
    issues: tuple[LoadIssue, ...] = ()


@dataclass(frozen=True, slots=True)
class CaseEntry:
    path: Path
    manifest: Manifest
    missing_files: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CaseLibrarySnapshot:
    entries: tuple[CaseEntry, ...]
    issues: tuple[LoadIssue, ...] = ()


@dataclass(frozen=True, slots=True)
class CompanyCoverage:
    company: Company
    case_count: int
    last_covered: date | None


@dataclass(frozen=True, slots=True)
class IssueDeliveryStatus:
    available: bool
    reason: str


@dataclass(frozen=True, slots=True)
class SystemStatus:
    api_key_configured: bool
    model_name: str
    max_case_candidates: int
    max_research_passes: int
    max_sources: int
    max_agent_runs: int
    model_timeout_seconds: float
    generation_timeout_seconds: float
    github_repository_configured: bool
    issue_delivery_available: bool
    issue_delivery_reason: str
    python_version: str
    application_version: str
    catalog_company_count: int
    catalog_healthy: bool
    cases_directory_exists: bool
    case_count: int
    history_file_exists: bool
    history_healthy: bool
    history_record_count: int
    env_file_exists: bool


@dataclass(frozen=True, slots=True)
class GenerationRequest:
    run_date: date
    company_override: str | None = None
    dry_run: bool = False
    deliver_issue: bool = False


@dataclass(frozen=True, slots=True)
class GenerationOutcome:
    result: GenerationResult | None
    error_type: str | None
    message: str
    wrote_case_or_history: bool
    progress: tuple[GenerationProgress, ...] = ()

    @property
    def successful(self) -> bool:
        return self.result is not None and self.result.status in {"published", "dry_run"}


class Orchestrator(Protocol):
    async def generate(
        self,
        *,
        run_date: date,
        company_override: str | None = None,
        dry_run: bool = False,
        deliver_issue: bool = False,
        progress_callback: ProgressCallback | None = None,
    ) -> GenerationResult: ...


OrchestratorFactory = Callable[[Settings], Orchestrator]


def build_settings(root_dir: Path) -> Settings:
    """Load the existing local env convention and create the application settings."""
    load_dotenv(root_dir / ".env.local", override=False)
    return Settings(root_dir=root_dir)


def load_catalog_safe(path: Path) -> CatalogSnapshot:
    try:
        return CatalogSnapshot(companies=tuple(load_catalog(path)))
    except (OSError, ValueError, TypeError, ValidationError) as exc:
        return CatalogSnapshot(
            companies=(),
            issues=(LoadIssue(str(path), safe_message(exc)),),
        )


def load_history_safe(path: Path) -> HistorySnapshot:
    try:
        return HistorySnapshot(records=tuple(load_history(path)))
    except (OSError, ValueError, TypeError, ValidationError) as exc:
        return HistorySnapshot(
            records=(),
            issues=(LoadIssue(str(path), safe_message(exc)),),
        )


def _case_entry(case_dir: Path) -> CaseEntry:
    manifest_path = case_dir / "manifest.json"
    manifest = Manifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    present = {item.name for item in case_dir.iterdir()}
    return CaseEntry(
        path=case_dir,
        manifest=manifest,
        missing_files=tuple(sorted(REQUIRED_FILES - present)),
    )


def load_case_library(cases_dir: Path) -> CaseLibrarySnapshot:
    if not cases_dir.exists():
        return CaseLibrarySnapshot(entries=())
    entries: list[CaseEntry] = []
    issues: list[LoadIssue] = []
    try:
        case_dirs = sorted(
            (
                item
                for item in cases_dir.iterdir()
                if item.is_dir() and not item.name.startswith(".tmp-")
            ),
            key=lambda item: item.name,
            reverse=True,
        )
    except OSError as exc:
        return CaseLibrarySnapshot(
            entries=(),
            issues=(LoadIssue(str(cases_dir), safe_message(exc)),),
        )
    for case_dir in case_dirs:
        try:
            entries.append(_case_entry(case_dir))
        except (OSError, ValueError, TypeError, ValidationError) as exc:
            issues.append(LoadIssue(str(case_dir), safe_message(exc)))
    entries.sort(
        key=lambda entry: (entry.manifest.date, entry.manifest.generated_at),
        reverse=True,
    )
    return CaseLibrarySnapshot(entries=tuple(entries), issues=tuple(issues))


def list_case_directories(cases_dir: Path) -> tuple[Path, ...]:
    if not cases_dir.exists():
        return ()
    try:
        return tuple(
            sorted(
                (
                    item
                    for item in cases_dir.iterdir()
                    if item.is_dir() and not item.name.startswith(".tmp-")
                ),
                key=lambda item: item.name,
                reverse=True,
            )
        )
    except OSError:
        return ()


def company_coverage(
    companies: Sequence[Company], history: Sequence[HistoryRecord]
) -> tuple[CompanyCoverage, ...]:
    counts = coverage_counts(list(history))
    seen = last_seen(list(history))
    return tuple(
        CompanyCoverage(
            company=company,
            case_count=counts.get(company.id, 0),
            last_covered=seen.get(company.id),
        )
        for company in companies
    )


def history_category_counts(history: Sequence[HistoryRecord]) -> Counter[str]:
    return Counter(record.case_category for record in history)


def read_case_markdown(cases_dir: Path, case_dir: Path, section: str) -> str:
    filename = MARKDOWN_FILES.get(section)
    if filename is None:
        raise ValueError(f"Unknown case section: {section}")
    safe_dir = _safe_case_directory(cases_dir, case_dir)
    return (safe_dir / filename).read_text(encoding="utf-8")


def read_case_json(cases_dir: Path, case_dir: Path, filename: str) -> object:
    import json

    if filename not in {"manifest.json", "sources.json"}:
        raise ValueError(f"Unsupported JSON artifact: {filename}")
    safe_dir = _safe_case_directory(cases_dir, case_dir)
    return json.loads((safe_dir / filename).read_text(encoding="utf-8"))


def _safe_case_directory(cases_dir: Path, case_dir: Path) -> Path:
    root = cases_dir.resolve()
    candidate = case_dir.resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError("Case directory must be inside the configured cases directory")
    return candidate


def validate_existing_case(cases_dir: Path, case_dir: Path) -> QualityReport:
    return validate_case_directory(_safe_case_directory(cases_dir, case_dir))


def issue_delivery_status(
    settings: Settings, environ: Mapping[str, str] | None = None
) -> IssueDeliveryStatus:
    environment = os.environ if environ is None else environ
    missing: list[str] = []
    if not settings.github_repository:
        missing.append("PM_CASE_GITHUB_REPOSITORY")
    if not environment.get("GITHUB_TOKEN") and not environment.get("GH_TOKEN"):
        missing.append("GITHUB_TOKEN or GH_TOKEN")
    if shutil.which("gh") is None:
        missing.append("GitHub CLI (gh)")
    if missing:
        return IssueDeliveryStatus(False, "Unavailable: " + ", ".join(missing))
    return IssueDeliveryStatus(True, "Configured for delivery after successful publication")


def build_system_status(
    settings: Settings,
    *,
    catalog: CatalogSnapshot,
    history: HistorySnapshot,
    library: CaseLibrarySnapshot,
    environ: Mapping[str, str] | None = None,
) -> SystemStatus:
    issue_status = issue_delivery_status(settings, environ)
    api_key_configured = bool(
        settings.openai_api_key and settings.openai_api_key.get_secret_value().strip()
    )
    return SystemStatus(
        api_key_configured=api_key_configured,
        model_name=settings.openai_model,
        max_case_candidates=settings.max_case_candidates,
        max_research_passes=settings.max_research_passes,
        max_sources=settings.max_sources,
        max_agent_runs=settings.max_agent_runs,
        model_timeout_seconds=settings.model_timeout_seconds,
        generation_timeout_seconds=settings.generation_timeout_seconds,
        github_repository_configured=bool(settings.github_repository),
        issue_delivery_available=issue_status.available,
        issue_delivery_reason=issue_status.reason,
        python_version=sys.version.split()[0],
        application_version=__version__,
        catalog_company_count=len(catalog.companies),
        catalog_healthy=not catalog.issues,
        cases_directory_exists=settings.cases_dir.is_dir(),
        case_count=len(library.entries),
        history_file_exists=(settings.data_dir / "history.jsonl").is_file(),
        history_healthy=not history.issues,
        history_record_count=len(history.records),
        env_file_exists=(settings.root_dir / ".env.local").is_file(),
    )


def _publication_state(settings: Settings) -> tuple[tuple[str, ...], tuple[int, int] | None]:
    case_names = tuple(path.name for path in list_case_directories(settings.cases_dir))
    history_path = settings.data_dir / "history.jsonl"
    if not history_path.exists():
        return case_names, None
    try:
        stat = history_path.stat()
        return case_names, (stat.st_size, stat.st_mtime_ns)
    except OSError:
        return case_names, None


def safe_message(exc: BaseException, secrets: Sequence[str] = ()) -> str:
    message = str(exc) or type(exc).__name__
    for secret in secrets:
        if secret:
            message = message.replace(secret, "[REDACTED]")
    sanitized = redact(message)
    return sanitized if isinstance(sanitized, str) else type(exc).__name__


def _known_secrets(settings: Settings, environ: Mapping[str, str]) -> tuple[str, ...]:
    values = [environ.get("GITHUB_TOKEN", ""), environ.get("GH_TOKEN", "")]
    if settings.openai_api_key:
        values.append(settings.openai_api_key.get_secret_value())
    return tuple(value for value in values if value)


def generation_error_message(
    exc: Exception,
    settings: Settings,
    environment: Mapping[str, str],
) -> str:
    message = safe_message(exc, _known_secrets(settings, environment))
    lowered = message.casefold()
    if any(
        marker in lowered
        for marker in ("credit_balance_exhausted", "insufficient_quota", "no credits remaining")
    ):
        return (
            "OpenAI API credits are exhausted for this project. Add credits in OpenAI Platform "
            "billing, then start a new generation."
        )
    return message


async def generate_case(
    settings: Settings,
    request: GenerationRequest,
    *,
    orchestrator_factory: OrchestratorFactory = DailyCaseOrchestrator,
    environ: Mapping[str, str] | None = None,
    progress_callback: ProgressCallback | None = None,
) -> GenerationOutcome:
    """Call the real application orchestrator and report only secret-safe UI details."""
    environment = os.environ if environ is None else environ
    before = _publication_state(settings)
    orchestrator = orchestrator_factory(settings)
    run_id = str(getattr(orchestrator, "run_id", "ui-service"))
    progress_events: list[GenerationProgress] = []

    def forward_progress(progress: GenerationProgress) -> None:
        progress_events.append(progress)
        if progress_callback is not None:
            progress_callback(progress)

    emit_progress(
        forward_progress,
        event="generation.requested",
        stage="generation",
        status="started",
        message="Generation request received from the UI.",
        run_id=run_id,
        run_date=request.run_date,
        company_id=request.company_override,
    )
    emit_progress(
        forward_progress,
        event="generation.started",
        stage="generation",
        status="started",
        message="Generation request accepted.",
        run_id=run_id,
        run_date=request.run_date,
        company_id=request.company_override,
    )
    try:
        async with asyncio.timeout(settings.generation_timeout_seconds):
            result = await orchestrator.generate(
                run_date=request.run_date,
                company_override=request.company_override,
                dry_run=request.dry_run,
                deliver_issue=request.deliver_issue,
                progress_callback=forward_progress,
            )
        terminal_status = "completed" if result.status in {"published", "dry_run"} else "rejected"
        emit_progress(
            forward_progress,
            event=f"generation.{terminal_status}",
            stage="generation",
            status=terminal_status,
            message=result.message,
            run_id=run_id,
            run_date=request.run_date,
            company_id=request.company_override,
        )
        after = _publication_state(settings)
        return GenerationOutcome(
            result=result,
            error_type=None,
            message=result.message,
            wrote_case_or_history=before != after,
            progress=tuple(progress_events),
        )
    except Exception as exc:
        after = _publication_state(settings)
        message = generation_error_message(exc, settings, environment)
        if isinstance(exc, TimeoutError):
            timeout_seconds = settings.generation_timeout_seconds
            message = (
                f"Generation exceeded the configured {timeout_seconds:g}-second "
                "limit and was cancelled safely. No successful publication was reported."
            )
        active_stage = next(
            (
                item.stage
                for item in reversed(progress_events)
                if item.status == "started" and item.stage != "generation"
            ),
            "generation",
        )
        message = f"Generation failed during {active_stage}: {message}"
        emit_progress(
            forward_progress,
            event="generation.failed",
            stage="generation",
            status="failed",
            message=message,
            run_id=run_id,
            run_date=request.run_date,
            company_id=request.company_override,
        )
        return GenerationOutcome(
            result=None,
            error_type=type(exc).__name__,
            message=message,
            wrote_case_or_history=before != after,
            progress=tuple(progress_events),
        )


class GenerationAlreadyRunning(RuntimeError):
    pass


GenerationRunner = Callable[
    [Settings, GenerationRequest, ProgressCallback | None], Awaitable[GenerationOutcome]
]


async def run_generation_with_state(
    state: MutableMapping[str, object],
    settings: Settings,
    request: GenerationRequest,
    *,
    progress_callback: ProgressCallback | None = None,
    generator: GenerationRunner | None = None,
) -> GenerationOutcome:
    """Own the UI lifecycle so every terminal path clears the running lock."""
    if bool(state.get("generation_running", False)):
        raise GenerationAlreadyRunning("A generation is already running in this session.")
    state["generation_running"] = True
    state["generation_state"] = "running"
    runner = generator or (
        lambda current_settings, current_request, callback: generate_case(
            current_settings,
            current_request,
            progress_callback=callback,
        )
    )
    try:
        outcome = await runner(settings, request, progress_callback)
        state["last_generation"] = outcome
        state["generation_state"] = (
            outcome.result.status if outcome.result is not None else "failed"
        )
        return outcome
    except BaseException:
        state["generation_state"] = "failed"
        raise
    finally:
        state["generation_running"] = False
