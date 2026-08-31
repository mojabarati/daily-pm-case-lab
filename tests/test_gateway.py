from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from agents import ModelBehaviorError

from daily_pm_case_lab.config import Settings
from daily_pm_case_lab.gateway import OpenAIAgentGateway
from daily_pm_case_lab.models import Company, ResearchPriority, ScoutResult


@pytest.mark.asyncio
async def test_gateway_retries_invalid_structured_output_once(tmp_path) -> None:
    settings = Settings(root_dir=tmp_path, openai_api_key="test-only-key", max_agent_runs=3)
    gateway = OpenAIAgentGateway(settings, "test-run")
    company = Company(
        id="uber",
        name="Uber",
        category="Marketplace",
        country="United States",
        public_company=True,
        research_priority=ResearchPriority.HIGH,
    )
    expected = ScoutResult(candidates=[])
    successful_result = SimpleNamespace(final_output=expected, raw_responses=[])

    with patch(
        "daily_pm_case_lab.gateway.Runner.run",
        new=AsyncMock(side_effect=[ModelBehaviorError("Invalid JSON"), successful_result]),
    ) as run:
        result = await gateway.scout([company], [], date(2026, 9, 1))

    assert result is expected
    assert run.await_count == 2
    assert gateway.runs_used == 2
