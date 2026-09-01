from __future__ import annotations

import asyncio
from collections.abc import Sequence
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import streamlit as st

from daily_pm_case_lab.config import Settings
from daily_pm_case_lab.logging_utils import configure_logging
from daily_pm_case_lab.models import Company, HistoryRecord
from daily_pm_case_lab.progress import GenerationProgress
from daily_pm_case_lab.ui.services import (
    MARKDOWN_FILES,
    SPOILER_SECTIONS,
    CaseEntry,
    CaseLibrarySnapshot,
    CatalogSnapshot,
    GenerationAlreadyRunning,
    GenerationOutcome,
    GenerationRequest,
    HistorySnapshot,
    build_settings,
    build_system_status,
    company_coverage,
    history_category_counts,
    issue_delivery_status,
    list_case_directories,
    load_case_library,
    load_catalog_safe,
    load_history_safe,
    read_case_json,
    read_case_markdown,
    run_generation_with_state,
    safe_message,
    validate_existing_case,
)

ROOT_DIR = Path(__file__).resolve().parents[3]
TEHRAN = ZoneInfo("Asia/Tehran")
NAVIGATION = (
    "Dashboard",
    "Generate Case",
    "Case Library",
    "Companies",
    "Validation",
    "History",
    "Settings / System Status",
)
READER_SECTIONS = (
    "Challenge",
    "Overview",
    "Evidence",
    "Interview Drill",
    "What Company Did",
    "PM Analysis",
    "Model Answer",
    "Sources",
    "Metadata",
)


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
        .block-container { max-width: 1180px; padding-top: 2rem; padding-bottom: 4rem; }
        [data-testid="stSidebar"] { border-right: 1px solid rgba(128,128,128,.18); }
        [data-testid="stMetric"] {
            border: 1px solid rgba(128,128,128,.22);
            border-radius: .65rem;
            padding: .85rem 1rem;
        }
        .st-key-rtl-case-content {
            direction: rtl;
            text-align: right;
            line-height: 2;
            font-family: Tahoma, "Segoe UI", sans-serif;
        }
        .st-key-rtl-case-content pre,
        .st-key-rtl-case-content code,
        .st-key-rtl-case-content a { direction: ltr; unicode-bidi: embed; }
        .st-key-rtl-case-content table { direction: rtl; }
        .muted { color: rgba(128,128,128,.95); font-size: .9rem; }
        @media (max-width: 760px) {
            .block-container { padding: 1rem .8rem 3rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _show_load_issues(*snapshots: object) -> None:
    for snapshot in snapshots:
        for issue in getattr(snapshot, "issues", ()):
            st.warning(f"Could not load {issue.location}: {issue.message}")


def _relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT_DIR.resolve()).as_posix()
    except ValueError:
        return path.name


def _format_date(value: date | None) -> str:
    return value.isoformat() if value else "Never"


def _set_active_case(path: Path) -> None:
    st.session_state["active_case"] = str(path.resolve())


def _active_entry(entries: Sequence[CaseEntry]) -> CaseEntry | None:
    active = st.session_state.get("active_case")
    if not active:
        return None
    for entry in entries:
        if str(entry.path.resolve()) == active:
            return entry
    return None


def _case_row(entry: CaseEntry, *, key_prefix: str) -> None:
    manifest = entry.manifest
    with st.container(border=True):
        title, score, action = st.columns([5, 1, 1.3], vertical_alignment="center")
        with title:
            st.markdown(f"**{manifest.company} — {manifest.case_title}**")
            st.caption(
                f"{manifest.date.isoformat()} · {manifest.category} · "
                f"{manifest.difficulty} · {manifest.status}"
            )
        score.metric("Quality", f"{manifest.quality_score}/100")
        action.button(
            "Open Case",
            key=f"{key_prefix}-{entry.path.name}",
            on_click=_set_active_case,
            args=(entry.path,),
            width="stretch",
        )
        if entry.missing_files:
            st.warning("Missing files: " + ", ".join(entry.missing_files))


def _render_case_reader(settings: Settings, entry: CaseEntry) -> None:
    manifest = entry.manifest
    st.divider()
    st.subheader(f"{manifest.company} — {manifest.case_title}")
    st.caption(
        f"{manifest.date.isoformat()} · Quality {manifest.quality_score}/100 · "
        f"{manifest.source_count} sources · {_relative_path(entry.path)}"
    )
    section = st.selectbox(
        "Reading section",
        READER_SECTIONS,
        index=0,
        key=f"reader-section-{entry.path.name}",
        help="Challenge opens first. Answer sections require a deliberate reveal.",
    )
    if section in SPOILER_SECTIONS:
        reveal_key = f"revealed-{entry.path.name}-{section}"
        if not st.session_state.get(reveal_key, False):
            st.warning(
                "This section reveals the company's decision or the model analysis. "
                "Work through the Challenge first."
            )
            if st.button(f"Reveal {section}", key=f"reveal-button-{reveal_key}"):
                st.session_state[reveal_key] = True
                st.rerun()
            return
    try:
        if section in MARKDOWN_FILES:
            content = read_case_markdown(settings.cases_dir, entry.path, section)
            with st.container(key="rtl-case-content"):
                st.markdown(content)
        elif section == "Sources":
            st.json(read_case_json(settings.cases_dir, entry.path, "sources.json"), expanded=1)
        else:
            st.json(read_case_json(settings.cases_dir, entry.path, "manifest.json"), expanded=1)
    except (OSError, ValueError, TypeError) as exc:
        st.error(f"This section could not be opened: {safe_message(exc)}")


def _render_dashboard(
    settings: Settings,
    catalog: CatalogSnapshot,
    history: HistorySnapshot,
    library: CaseLibrarySnapshot,
) -> None:
    st.title("Daily PM Case Lab")
    st.caption("A local workspace for evidence-backed product and business case practice.")
    _show_load_issues(catalog, history, library)

    latest = library.entries[0] if library.entries else None
    unique_companies = len({record.company_id for record in history.records})
    if not history.records:
        unique_companies = len({entry.manifest.company for entry in library.entries})
    columns = st.columns(5)
    columns[0].metric("Generated cases", len(library.entries))
    columns[1].metric("Companies covered", unique_companies)
    columns[2].metric("Catalog companies", len(catalog.companies))
    columns[3].metric("Latest quality", f"{latest.manifest.quality_score}/100" if latest else "—")
    columns[4].metric("Latest date", _format_date(latest.manifest.date if latest else None))
    if latest:
        st.caption(
            f"Latest generated case: {latest.manifest.company} — {latest.manifest.case_title}"
        )

    st.subheader("Recent cases")
    if not library.entries:
        st.info("No published cases are available yet. Start with Generate Case or a Dry Run.")
    for entry in library.entries[:8]:
        _case_row(entry, key_prefix="dashboard-open")

    if catalog.companies:
        st.subheader("Coverage")
        coverage = company_coverage(catalog.companies, history.records)
        most = sorted(coverage, key=lambda item: (-item.case_count, item.company.name))[:8]
        least = sorted(coverage, key=lambda item: (item.case_count, item.company.name))[:8]
        left, right = st.columns(2)
        with left:
            st.markdown("**Most covered**")
            st.dataframe(
                [
                    {
                        "Company": item.company.name,
                        "Cases": item.case_count,
                        "Last covered": _format_date(item.last_covered),
                    }
                    for item in most
                ],
                hide_index=True,
                width="stretch",
            )
        with right:
            st.markdown("**Least covered**")
            st.dataframe(
                [
                    {
                        "Company": item.company.name,
                        "Cases": item.case_count,
                        "Last covered": _format_date(item.last_covered),
                    }
                    for item in least
                ],
                hide_index=True,
                width="stretch",
            )
        categories = history_category_counts(history.records)
        st.markdown("**Category distribution**")
        if categories:
            st.dataframe(
                [
                    {"Category": category, "Cases": count}
                    for category, count in categories.most_common()
                ],
                hide_index=True,
                width="stretch",
            )
        else:
            st.caption("Category coverage will appear after the first published case.")

    active = _active_entry(library.entries)
    if active:
        _render_case_reader(settings, active)


def _company_label(company: Company) -> str:
    return f"{company.name} ({company.id})"


def _render_generation_outcome(settings: Settings, outcome: GenerationOutcome) -> None:
    st.subheader("Latest generation result")
    result = outcome.result
    if outcome.successful and result is not None:
        st.success(result.message)
    elif result is not None:
        st.warning(result.message)
    else:
        st.error(outcome.message)
        if "API credits are exhausted" in outcome.message:
            st.link_button(
                "Open OpenAI billing",
                "https://platform.openai.com/settings/organization/billing",
            )

    values = st.columns(4)
    values[0].metric("Status", result.status if result else "failed")
    values[1].metric("Company", result.selected_company or "—" if result else "—")
    values[2].metric(
        "Quality",
        f"{result.quality_score}/100" if result and result.quality_score is not None else "—",
    )
    values[3].metric("Files/history changed", "Yes" if outcome.wrote_case_or_history else "No")
    if result:
        st.caption(
            f"Candidate attempts: {result.attempted_candidates} · Agent runs: {result.agent_runs}"
        )
        if result.issue_url:
            st.link_button("Open GitHub Issue", result.issue_url)
        if result.case_directory:
            case_path = Path(result.case_directory)
            st.code(_relative_path(case_path), language=None)
            matching = next(
                (
                    entry
                    for entry in load_case_library(settings.cases_dir).entries
                    if entry.path.resolve() == case_path.resolve()
                ),
                None,
            )
            if matching:
                st.markdown(f"**Case title:** {matching.manifest.case_title}")
                st.caption(
                    f"Run date: {matching.manifest.date.isoformat()} · "
                    f"Sources: {matching.manifest.source_count} · "
                    f"Category: {matching.manifest.category}"
                )
                if st.button("Open Generated Case", width="stretch"):
                    _set_active_case(matching.path)
                    st.session_state["show_generated_case"] = True
                if st.session_state.get("show_generated_case"):
                    _render_case_reader(settings, matching)
    if outcome.error_type:
        st.caption(f"Error type: {outcome.error_type}")
    if outcome.progress:
        with st.expander("Generation trace", expanded=False):
            for progress in outcome.progress:
                st.caption(_progress_line(progress))


def _progress_line(progress: GenerationProgress) -> str:
    marker = {
        "started": "▶",
        "completed": "✓",
        "rejected": "!",
        "failed": "x",
    }[progress.status]
    timestamp = progress.timestamp.astimezone(TEHRAN).strftime("%H:%M:%S")
    elapsed = f" · {progress.elapsed_ms / 1000:.1f}s" if progress.elapsed_ms is not None else ""
    return f"{marker} {timestamp} · {progress.message}{elapsed}"


def _render_generate(
    settings: Settings,
    catalog: CatalogSnapshot,
    history: HistorySnapshot,
) -> None:
    st.title("Generate Case")
    st.caption("Run the existing application pipeline with visual controls.")
    _show_load_issues(catalog, history)
    if not catalog.companies:
        st.error("Generation is unavailable until the company catalog is valid.")
        return

    if "generation_running" not in st.session_state:
        st.session_state["generation_running"] = False
    coverage = {
        item.company.id: item for item in company_coverage(catalog.companies, history.records)
    }
    delivery = issue_delivery_status(settings)
    api_configured = bool(
        settings.openai_api_key and settings.openai_api_key.get_secret_value().strip()
    )

    with st.form("generate-case-form", border=True):
        selection_mode = st.radio(
            "Company selection",
            ("Automatic Selection", "Specific Company"),
            horizontal=True,
        )
        selected_company: Company | None = None
        if selection_mode == "Specific Company":
            selected_company = st.selectbox(
                "Company",
                catalog.companies,
                format_func=_company_label,
                help="Search by typing a company name or catalog ID.",
            )
            if selected_company:
                item = coverage[selected_company.id]
                st.caption(
                    f"{selected_company.category} · {selected_company.country} · "
                    f"Public: {'Yes' if selected_company.public_company else 'No'} · "
                    f"Priority: {selected_company.research_priority.value} · "
                    f"Previous cases: {item.case_count} · Last covered: "
                    f"{_format_date(item.last_covered)}"
                )
        run_date = st.date_input(
            "Run date",
            value=datetime.now(TEHRAN).date(),
            help="Defaults to today in Asia/Tehran and maps directly to run_date.",
        )
        mode = st.radio("Mode", ("Generate Case", "Dry Run"), horizontal=True)
        if mode == "Dry Run":
            st.caption(
                "Dry Run performs deterministic company selection only. It makes no agent calls "
                "and does not write cases or history."
            )
        elif not api_configured:
            st.error("OPENAI_API_KEY is not configured. Dry Run remains available.")
        deliver_issue = st.toggle(
            "Create GitHub Issue after successful generation",
            value=False,
            disabled=not delivery.available or mode == "Dry Run",
            help=delivery.reason,
        )
        disabled = bool(st.session_state["generation_running"]) or (
            mode == "Generate Case" and not api_configured
        )
        submitted = st.form_submit_button(
            "Generate Case" if mode == "Generate Case" else "Run Dry Run",
            type="primary",
            disabled=disabled,
            width="stretch",
        )

    if submitted:
        st.session_state["show_generated_case"] = False
        request = GenerationRequest(
            run_date=run_date,
            company_override=selected_company.id if selected_company else None,
            dry_run=mode == "Dry Run",
            deliver_issue=deliver_issue,
        )
        with st.status("Starting generation…", expanded=True) as status:
            status.write("The backend will report each real stage as it starts and finishes.")

            def show_progress(progress: GenerationProgress) -> None:
                status.write(_progress_line(progress))
                if progress.status == "started":
                    status.update(label=progress.message, state="running", expanded=True)

            try:
                outcome = asyncio.run(
                    run_generation_with_state(
                        st.session_state,
                        settings,
                        request,
                        progress_callback=show_progress,
                    )
                )
                if outcome.successful:
                    status.update(label="Generation completed", state="complete", expanded=False)
                elif outcome.result is not None:
                    status.update(
                        label="Generation completed without publication",
                        state="error",
                        expanded=True,
                    )
                else:
                    status.update(label="Generation failed", state="error", expanded=True)
            except GenerationAlreadyRunning as exc:
                status.update(label=str(exc), state="error", expanded=True)
            except Exception as exc:
                status.update(label="Unexpected UI failure", state="error", expanded=True)
                st.error(safe_message(exc))

    last_outcome = st.session_state.get("last_generation")
    if isinstance(last_outcome, GenerationOutcome):
        _render_generation_outcome(settings, last_outcome)


def _render_case_library(settings: Settings, library: CaseLibrarySnapshot) -> None:
    st.title("Case Library")
    st.caption("Authoritative metadata is read from each case's manifest.json.")
    _show_load_issues(library)
    if not library.entries:
        st.info("No readable case manifests were found.")
        return

    search = st.text_input("Search case titles")
    companies = sorted({entry.manifest.company for entry in library.entries})
    categories = sorted({entry.manifest.category for entry in library.entries})
    filters = st.columns(2)
    company = filters[0].selectbox("Company", ("All", *companies))
    category = filters[1].selectbox("Category", ("All", *categories))
    scores = st.slider("Quality score", 0, 100, (0, 100))
    use_dates = st.checkbox("Filter by date")
    from_date = min(entry.manifest.date for entry in library.entries)
    to_date = max(entry.manifest.date for entry in library.entries)
    if use_dates:
        dates = st.columns(2)
        from_date = dates[0].date_input("From", value=from_date)
        to_date = dates[1].date_input("To", value=to_date)

    needle = search.strip().casefold()
    filtered = [
        entry
        for entry in library.entries
        if (not needle or needle in entry.manifest.case_title.casefold())
        and (company == "All" or entry.manifest.company == company)
        and (category == "All" or entry.manifest.category == category)
        and scores[0] <= entry.manifest.quality_score <= scores[1]
        and (not use_dates or from_date <= entry.manifest.date <= to_date)
    ]
    st.caption(f"{len(filtered)} of {len(library.entries)} cases")
    for entry in filtered:
        _case_row(entry, key_prefix="library-open")
    active = _active_entry(library.entries)
    if active:
        _render_case_reader(settings, active)


def _render_companies(catalog: CatalogSnapshot, history: HistorySnapshot) -> None:
    st.title("Companies")
    st.caption("Catalog fields are read directly from data/company_catalog.yaml.")
    _show_load_issues(catalog, history)
    if not catalog.companies:
        st.error("The company catalog is unavailable or invalid.")
        return

    search = st.text_input("Search name, ID, or alias", key="company-search")
    categories = sorted({company.category for company in catalog.companies})
    countries = sorted({company.country for company in catalog.companies})
    filters = st.columns(3)
    category = filters[0].selectbox("Category", ("All", *categories), key="company-category")
    country = filters[1].selectbox("Country", ("All", *countries), key="company-country")
    priority = filters[2].selectbox(
        "Research priority", ("All", "high", "medium", "low"), key="company-priority"
    )
    needle = search.strip().casefold()
    coverage = company_coverage(catalog.companies, history.records)
    filtered = [
        item
        for item in coverage
        if (
            not needle
            or needle in item.company.name.casefold()
            or needle in item.company.id.casefold()
            or any(needle in alias.casefold() for alias in item.company.aliases)
        )
        and (category == "All" or item.company.category == category)
        and (country == "All" or item.company.country == country)
        and (priority == "All" or item.company.research_priority.value == priority)
    ]
    st.caption(f"{len(filtered)} of {len(catalog.companies)} companies")
    st.dataframe(
        [
            {
                "Name": item.company.name,
                "ID": item.company.id,
                "Aliases": ", ".join(item.company.aliases),
                "Category": item.company.category,
                "Country": item.company.country,
                "Public": "Yes" if item.company.public_company else "No",
                "Priority": item.company.research_priority.value,
                "Cases": item.case_count,
                "Last covered": _format_date(item.last_covered),
            }
            for item in filtered
        ],
        hide_index=True,
        width="stretch",
    )


def _render_validation(settings: Settings) -> None:
    st.title("Validation")
    st.caption("Runs the same validate_case_directory logic used by pm-case-lab validate.")
    case_dirs = list_case_directories(settings.cases_dir)
    if not case_dirs:
        st.info("No case directories are available to validate.")
        return
    selected = st.selectbox("Case directory", case_dirs, format_func=_relative_path)
    if st.button("Validate Case", type="primary"):
        try:
            st.session_state["validation_result"] = (
                str(selected.resolve()),
                validate_existing_case(settings.cases_dir, selected),
                None,
            )
        except (OSError, ValueError, TypeError) as exc:
            st.session_state["validation_result"] = (
                str(selected.resolve()),
                None,
                safe_message(exc),
            )
    stored = st.session_state.get("validation_result")
    if stored and stored[0] == str(selected.resolve()):
        _, report, error = stored
        if error:
            st.error(error)
            return
        if report.publishable:
            st.success("Publishable: Yes")
        else:
            st.error("Publishable: No")
        st.metric("Validation score", report.score)
        if report.blockers:
            st.markdown("**Blockers**")
            for blocker in report.blockers:
                st.write(f"- {blocker}")
        st.dataframe(
            [
                {
                    "Check": check.name,
                    "Passed": "Yes" if check.passed else "No",
                    "Detail": check.detail,
                }
                for check in report.checks
            ],
            hide_index=True,
            width="stretch",
        )


def _render_history(history: HistorySnapshot) -> None:
    st.title("History")
    st.caption("Publication history is read from data/history.jsonl.")
    _show_load_issues(history)
    records: Sequence[HistoryRecord] = history.records
    columns = st.columns(3)
    columns[0].metric("Published records", len(records))
    columns[1].metric("Companies covered", len({record.company_id for record in records}))
    columns[2].metric("Categories covered", len({record.case_category for record in records}))
    if not records:
        st.info("History is empty. A successful published generation will add the first record.")
        return
    st.dataframe(
        [
            {
                "Date": record.date.isoformat(),
                "Company": record.company,
                "Company ID": record.company_id,
                "Case title": record.case_title,
                "Slug": record.case_slug,
                "Category": record.case_category,
                "Difficulty": record.difficulty,
                "Sources": record.sources_count,
            }
            for record in sorted(records, key=lambda item: item.date, reverse=True)
        ],
        hide_index=True,
        width="stretch",
    )
    categories = history_category_counts(records)
    st.markdown("**Category coverage**")
    st.dataframe(
        [{"Category": name, "Cases": count} for name, count in categories.most_common()],
        hide_index=True,
        width="stretch",
    )


def _render_system_status(
    settings: Settings,
    catalog: CatalogSnapshot,
    history: HistorySnapshot,
    library: CaseLibrarySnapshot,
) -> None:
    st.title("Settings / System Status")
    st.caption("Read-only, secret-safe configuration and local filesystem health.")
    status = build_system_status(
        settings,
        catalog=catalog,
        history=history,
        library=library,
    )
    st.subheader("OpenAI")
    columns = st.columns(2)
    columns[0].metric("API key configured", "Yes" if status.api_key_configured else "No")
    columns[1].metric("Model", status.model_name)
    st.dataframe(
        [
            {"Setting": "MAX_CASE_CANDIDATES", "Value": status.max_case_candidates},
            {"Setting": "MAX_RESEARCH_PASSES", "Value": status.max_research_passes},
            {"Setting": "MAX_SOURCES", "Value": status.max_sources},
            {"Setting": "MAX_AGENT_RUNS", "Value": status.max_agent_runs},
            {"Setting": "MAX_REVISION_PASSES", "Value": status.max_revision_passes},
            {
                "Setting": "OPENAI_MODEL_TIMEOUT_SECONDS",
                "Value": status.model_timeout_seconds,
            },
            {
                "Setting": "GENERATION_TIMEOUT_SECONDS",
                "Value": status.generation_timeout_seconds,
            },
        ],
        hide_index=True,
        width="stretch",
    )
    if not status.api_key_configured:
        st.warning("Real generation is disabled. Dry Run and all read-only pages remain available.")

    st.subheader("GitHub")
    columns = st.columns(2)
    columns[0].metric(
        "Repository configured", "Yes" if status.github_repository_configured else "No"
    )
    columns[1].metric(
        "Issue delivery available", "Yes" if status.issue_delivery_available else "No"
    )
    st.caption(status.issue_delivery_reason)

    st.subheader("Local environment")
    st.dataframe(
        [
            {"Item": "Python", "Status": status.python_version},
            {"Item": "Application", "Status": status.application_version},
            {
                "Item": "Local env file",
                "Status": "Present" if status.env_file_exists else "Missing",
            },
            {
                "Item": "Company catalog",
                "Status": (
                    f"Healthy ({status.catalog_company_count} companies)"
                    if status.catalog_healthy
                    else "Invalid"
                ),
            },
            {
                "Item": "Cases directory",
                "Status": (
                    f"Present ({status.case_count} readable cases)"
                    if status.cases_directory_exists
                    else "Not created yet"
                ),
            },
            {
                "Item": "History",
                "Status": (
                    f"Healthy ({status.history_record_count} records)"
                    if status.history_healthy and status.history_file_exists
                    else "Missing"
                    if not status.history_file_exists
                    else "Invalid"
                ),
            },
        ],
        hide_index=True,
        width="stretch",
    )
    _show_load_issues(catalog, history, library)


def main() -> None:
    st.set_page_config(
        page_title="Daily PM Case Lab",
        page_icon=None,
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _inject_styles()
    try:
        settings = build_settings(ROOT_DIR)
        configure_logging(settings.log_level)
    except Exception as exc:
        st.title("Daily PM Case Lab")
        st.error(f"Configuration could not be loaded: {safe_message(exc)}")
        st.info("Review .env.local values. Secret values are never displayed here.")
        st.stop()

    catalog = load_catalog_safe(settings.data_dir / "company_catalog.yaml")
    history = load_history_safe(settings.data_dir / "history.jsonl")
    library = load_case_library(settings.cases_dir)

    with st.sidebar:
        st.markdown("## Daily PM Case Lab")
        st.caption("Local learning workspace")
        page = st.radio("Navigation", NAVIGATION, label_visibility="collapsed")
        st.divider()
        st.caption("Local UI · No automatic git commit or push")

    if page == "Dashboard":
        _render_dashboard(settings, catalog, history, library)
    elif page == "Generate Case":
        _render_generate(settings, catalog, history)
    elif page == "Case Library":
        _render_case_library(settings, library)
    elif page == "Companies":
        _render_companies(catalog, history)
    elif page == "Validation":
        _render_validation(settings)
    elif page == "History":
        _render_history(history)
    else:
        _render_system_status(settings, catalog, history, library)


if __name__ == "__main__":
    main()
