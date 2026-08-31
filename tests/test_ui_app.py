from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

from daily_pm_case_lab.ui.app import NAVIGATION
from daily_pm_case_lab.ui.services import GenerationOutcome

ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "src" / "daily_pm_case_lab" / "ui" / "app.py"


def _app() -> AppTest:
    app = AppTest.from_file(str(APP_PATH), default_timeout=20)
    app.run()
    assert not list(app.exception)
    return app


def test_all_sidebar_pages_render_without_exceptions() -> None:
    app = _app()
    for page in NAVIGATION:
        app.sidebar.radio[0].set_value(page)
        app.run()
        assert not list(app.exception), page


def test_dry_run_can_be_submitted_from_generate_page() -> None:
    app = _app()
    app.sidebar.radio[0].set_value("Generate Case")
    app.run()
    mode = next(radio for radio in app.radio if radio.label == "Mode")
    mode.set_value("Dry Run")
    app.run()
    submit = next(button for button in app.button if button.label == "Run Dry Run")
    submit.click()
    app.run()

    assert not list(app.exception)
    outcome = app.session_state["last_generation"]
    assert isinstance(outcome, GenerationOutcome)
    assert outcome.successful
    assert outcome.result is not None
    assert outcome.result.status == "dry_run"
    assert not outcome.wrote_case_or_history
