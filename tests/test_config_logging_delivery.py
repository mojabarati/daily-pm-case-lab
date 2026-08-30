from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from daily_pm_case_lab.config import Settings
from daily_pm_case_lab.delivery import GitHubIssueDelivery
from daily_pm_case_lab.logging_utils import redact
from daily_pm_case_lab.models import Manifest


def test_settings_enforce_bounded_limits(tmp_path) -> None:
    with pytest.raises(ValidationError):
        Settings(root_dir=tmp_path, max_agent_runs=100)


def test_recursive_redaction_removes_secret_values() -> None:
    payload = {"OPENAI_API_KEY": "not-for-output", "message": "value sk-testSecret123456"}
    sanitized = redact(payload)
    assert sanitized["OPENAI_API_KEY"] == "[REDACTED]"
    assert "sk-" not in sanitized["message"]


def test_github_delivery_uses_argument_list_and_returns_url(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    manifest = Manifest(
        date="2026-08-30",
        company="Uber",
        case_title="Marketplace balance",
        case_slug="marketplace-balance",
        category="Marketplace liquidity",
        difficulty="Hard",
        source_count=7,
        primary_source_count=2,
        quality_score=88,
        generated_at="2026-08-30T12:00:00+03:30",
        model="test-model",
    )
    completed = subprocess.CompletedProcess(
        args=[], returncode=0, stdout="https://github.com/acme/lab/issues/1\n", stderr=""
    )
    with patch("daily_pm_case_lab.delivery.subprocess.run", return_value=completed) as run:
        url = GitHubIssueDelivery("acme/lab").deliver(Path("cases/2026-08-30-uber-case"), manifest)
    assert url.endswith("/issues/1")
    args = run.call_args.args[0]
    assert args[:3] == ["gh", "issue", "create"]
    assert run.call_args.kwargs["timeout"] == 30
