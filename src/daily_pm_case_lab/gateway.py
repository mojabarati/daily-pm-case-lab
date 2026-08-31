from __future__ import annotations

import logging
import time
from datetime import date
from typing import Protocol, TypeVar

from agents import Agent, ModelBehaviorError, ModelSettings, Runner, WebSearchTool
from pydantic import BaseModel

from .config import Settings
from .models import (
    CaseCandidate,
    CaseStudy,
    Company,
    ResearchPacket,
    ReviewerReport,
    ScoutResult,
)
from .prompts import (
    RESEARCH_INSTRUCTIONS,
    REVIEW_INSTRUCTIONS,
    SCOUT_INSTRUCTIONS,
    SYNTHESIS_INSTRUCTIONS,
    research_prompt,
    review_prompt,
    scout_prompt,
    synthesis_prompt,
)

LOGGER = logging.getLogger(__name__)
OutputT = TypeVar("OutputT", bound=BaseModel)


class AgentBudgetExceeded(RuntimeError):
    pass


class AgentGateway(Protocol):
    @property
    def runs_used(self) -> int: ...

    async def scout(
        self,
        companies: list[Company],
        history_summary: list[dict[str, str]],
        run_date: date,
    ) -> ScoutResult: ...

    async def research(
        self,
        candidate: CaseCandidate,
        pass_number: int,
        prior_packet: ResearchPacket | None,
    ) -> ResearchPacket: ...

    async def synthesize(self, packet: ResearchPacket) -> CaseStudy: ...

    async def review(self, packet: ResearchPacket, study: CaseStudy) -> ReviewerReport: ...


class OpenAIAgentGateway:
    """Small typed Agents SDK boundary with one global call budget."""

    def __init__(self, settings: Settings, run_id: str) -> None:
        self.settings = settings
        self.run_id = run_id
        self._runs_used = 0

    @property
    def runs_used(self) -> int:
        return self._runs_used

    async def _run(
        self,
        *,
        stage: str,
        instructions: str,
        prompt: str,
        output_type: type[OutputT],
        web_search: bool,
        max_turns: int,
    ) -> OutputT:
        tools = [WebSearchTool()] if web_search else []
        agent: Agent[None] = Agent(
            name=f"Daily PM Case Lab — {stage}",
            instructions=instructions,
            model=self.settings.openai_model,
            tools=tools,
            output_type=output_type,
            model_settings=ModelSettings(timeout=self.settings.model_timeout_seconds),
        )
        stage_attempt = 0
        while True:
            if self._runs_used >= self.settings.max_agent_runs:
                raise AgentBudgetExceeded(
                    f"MAX_AGENT_RUNS={self.settings.max_agent_runs} exhausted before {stage}"
                )
            self._runs_used += 1
            attempt = self._runs_used
            stage_attempt += 1
            started = time.monotonic()
            LOGGER.info(
                "agent stage started",
                extra={
                    "event": "agent.started",
                    "run_id": self.run_id,
                    "stage": stage,
                    "attempt": attempt,
                    "retry_attempt": stage_attempt,
                    "model": self.settings.openai_model,
                    "agent_runs": self._runs_used,
                    "status": "started",
                },
            )
            try:
                result = await Runner.run(agent, prompt, max_turns=max_turns)
                final = result.final_output
                parsed = (
                    final if isinstance(final, output_type) else output_type.model_validate(final)
                )
            except ModelBehaviorError as exc:
                duration_ms = round((time.monotonic() - started) * 1000)
                can_retry = stage_attempt < 2 and self._runs_used < self.settings.max_agent_runs
                LOGGER.log(
                    logging.WARNING if can_retry else logging.ERROR,
                    "agent stage returned invalid structured output; retrying"
                    if can_retry
                    else "agent stage failed",
                    extra={
                        "event": "agent.retrying" if can_retry else "agent.failed",
                        "run_id": self.run_id,
                        "stage": stage,
                        "attempt": attempt,
                        "retry_attempt": stage_attempt,
                        "duration_ms": duration_ms,
                        "model": self.settings.openai_model,
                        "agent_runs": self._runs_used,
                        "status": "retrying" if can_retry else "failed",
                        "error_type": type(exc).__name__,
                    },
                )
                if can_retry:
                    continue
                raise
            except Exception as exc:
                LOGGER.exception(
                    "agent stage failed",
                    extra={
                        "run_id": self.run_id,
                        "stage": stage,
                        "attempt": attempt,
                        "retry_attempt": stage_attempt,
                        "duration_ms": round((time.monotonic() - started) * 1000),
                        "model": self.settings.openai_model,
                        "agent_runs": self._runs_used,
                        "status": "failed",
                        "event": "agent.failed",
                        "error_type": type(exc).__name__,
                    },
                )
                raise

            input_tokens = output_tokens = tool_calls = 0
            for response in getattr(result, "raw_responses", []):
                usage = getattr(response, "usage", None)
                input_tokens += int(getattr(usage, "input_tokens", 0) or 0)
                output_tokens += int(getattr(usage, "output_tokens", 0) or 0)
                for item in getattr(response, "output", []):
                    item_type = str(getattr(item, "type", ""))
                    tool_calls += int("tool" in item_type or "search_call" in item_type)
            LOGGER.info(
                "agent stage completed",
                extra={
                    "run_id": self.run_id,
                    "stage": stage,
                    "attempt": attempt,
                    "retry_attempt": stage_attempt,
                    "duration_ms": round((time.monotonic() - started) * 1000),
                    "model": self.settings.openai_model,
                    "agent_runs": self._runs_used,
                    "tool_calls": tool_calls,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "status": "completed",
                    "event": "agent.completed",
                },
            )
            return parsed

    async def scout(
        self,
        companies: list[Company],
        history_summary: list[dict[str, str]],
        run_date: date,
    ) -> ScoutResult:
        return await self._run(
            stage="scout",
            instructions=SCOUT_INSTRUCTIONS,
            prompt=scout_prompt(companies, history_summary, run_date),
            output_type=ScoutResult,
            web_search=True,
            max_turns=8,
        )

    async def research(
        self,
        candidate: CaseCandidate,
        pass_number: int,
        prior_packet: ResearchPacket | None,
    ) -> ResearchPacket:
        return await self._run(
            stage=f"research-pass-{pass_number}",
            instructions=RESEARCH_INSTRUCTIONS,
            prompt=research_prompt(candidate, self.settings.max_sources, pass_number, prior_packet),
            output_type=ResearchPacket,
            web_search=True,
            max_turns=10,
        )

    async def synthesize(self, packet: ResearchPacket) -> CaseStudy:
        return await self._run(
            stage="synthesis",
            instructions=SYNTHESIS_INSTRUCTIONS,
            prompt=synthesis_prompt(packet),
            output_type=CaseStudy,
            web_search=False,
            max_turns=5,
        )

    async def review(self, packet: ResearchPacket, study: CaseStudy) -> ReviewerReport:
        return await self._run(
            stage="review",
            instructions=REVIEW_INSTRUCTIONS,
            prompt=review_prompt(packet, study),
            output_type=ReviewerReport,
            web_search=False,
            max_turns=5,
        )
