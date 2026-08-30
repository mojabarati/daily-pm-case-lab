from __future__ import annotations

from datetime import date as Date
from datetime import datetime as DateTime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ResearchPriority(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ClaimType(StrEnum):
    FACT = "FACT"
    INFERENCE = "INFERENCE"
    ANALYSIS = "ANALYSIS"
    COUNTERFACTUAL = "COUNTERFACTUAL"


class Confidence(StrEnum):
    HIGH = "High confidence"
    MEDIUM = "Medium confidence"
    LOW = "Low confidence"


class ContentAccessLevel(StrEnum):
    FULL = "full_content_reviewed"
    PUBLIC_TRANSCRIPT = "public_transcript_reviewed"
    PARTIAL_TRANSCRIPT = "partial_transcript_reviewed"
    METADATA_ONLY = "metadata_only"
    SECONDARY_ONLY = "secondary_coverage_only"


class Company(StrictModel):
    id: str = Field(pattern=r"^[a-z0-9-]+$")
    name: str
    aliases: list[str] = Field(default_factory=list)
    category: str
    country: str
    public_company: bool
    research_priority: ResearchPriority
    case_count: int = Field(default=0, ge=0)


class Source(StrictModel):
    id: str = Field(pattern=r"^S\d{2,3}$")
    type: str
    title: str
    publisher: str
    author: str | None = None
    speaker: str | None = None
    speaker_role: str | None = None
    url: HttpUrl
    published_at: Date | None = None
    accessed_at: Date
    is_primary: bool = False
    content_access_level: ContentAccessLevel
    credibility_score: int = Field(ge=0, le=100)
    relevant_sections: list[str] = Field(default_factory=list)
    timestamps: list[str] = Field(default_factory=list)
    used_for: list[str] = Field(default_factory=list)


class Claim(StrictModel):
    claim: str
    source_ids: list[str] = Field(default_factory=list)
    claim_type: ClaimType
    confidence: Confidence

    @model_validator(mode="after")
    def facts_require_sources(self) -> Claim:
        if self.claim_type == ClaimType.FACT and not self.source_ids:
            raise ValueError("FACT claims require at least one source ID")
        return self


class PersonStatement(StrictModel):
    person: str
    role_at_time: str
    date: Date | None = None
    context: str
    statement_or_paraphrase: str
    source_id: str
    is_direct_quote: bool = False


class CandidateScore(StrictModel):
    evidence_quality: int = Field(ge=0, le=100)
    product_learning_value: int = Field(ge=0, le=100)
    decision_tradeoff_richness: int = Field(ge=0, le=100)
    business_relevance: int = Field(ge=0, le=100)
    source_diversity: int = Field(ge=0, le=100)
    rationale: str

    @property
    def total(self) -> int:
        return round(
            self.evidence_quality * 0.30
            + self.product_learning_value * 0.25
            + self.decision_tradeoff_richness * 0.20
            + self.business_relevance * 0.15
            + self.source_diversity * 0.10
        )


class CaseCandidate(StrictModel):
    company_id: str
    company_name: str
    case_title: str
    case_slug: str = Field(pattern=r"^[a-z0-9-]+$")
    primary_problem: str
    case_category: str
    time_period: str
    product: str
    difficulty: str
    why_educational: str
    likely_primary_sources: list[str] = Field(default_factory=list)
    score: CandidateScore


class ScoutResult(StrictModel):
    candidates: list[CaseCandidate]


class TimelineEvent(StrictModel):
    date_or_period: str
    event: str
    source_ids: list[str]
    confidence: Confidence


class ResearchPacket(StrictModel):
    candidate: CaseCandidate
    sources: list[Source]
    claims: list[Claim]
    statements: list[PersonStatement] = Field(default_factory=list)
    timeline: list[TimelineEvent] = Field(default_factory=list)
    market_context: list[Claim] = Field(default_factory=list)
    competitor_context: list[Claim] = Field(default_factory=list)
    actual_decision: list[Claim]
    outcomes: list[Claim] = Field(default_factory=list)
    decision_terms: list[str] = Field(default_factory=list)
    evidence_conflicts: list[str] = Field(default_factory=list)
    evidence_gaps: list[str] = Field(default_factory=list)
    primary_source_unavailable_reason: str | None = None


class CaseStudy(StrictModel):
    overview_markdown: str
    challenge_markdown: str
    evidence_pack_markdown: str
    what_company_did_markdown: str
    pm_analysis_markdown: str
    model_answer_markdown: str
    interview_drill_markdown: str
    estimated_exercise_minutes: int = Field(ge=15, le=240)
    competencies: list[str]


class QualityCheck(StrictModel):
    name: str
    passed: bool
    detail: str


class ReviewerReport(StrictModel):
    score: int = Field(ge=0, le=100)
    checks: list[QualityCheck]
    blockers: list[str] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)
    spoiler_findings: list[str] = Field(default_factory=list)
    analytical_depth_notes: list[str] = Field(default_factory=list)


class QualityReport(StrictModel):
    score: int = Field(ge=0, le=100)
    publishable: bool
    checks: list[QualityCheck]
    blockers: list[str] = Field(default_factory=list)


class Manifest(StrictModel):
    date: Date
    company: str
    case_title: str
    case_slug: str
    category: str
    difficulty: str
    source_count: int = Field(ge=0)
    primary_source_count: int = Field(ge=0)
    quality_score: int = Field(ge=0, le=100)
    generated_at: DateTime
    model: str
    status: str = "published"


class HistoryRecord(StrictModel):
    date: Date
    company: str
    company_id: str
    case_slug: str
    case_title: str
    primary_problem: str
    case_category: str
    difficulty: str
    sources_count: int = Field(ge=0)


class GenerationResult(StrictModel):
    status: str
    case_directory: str | None = None
    quality_score: int | None = None
    selected_company: str | None = None
    attempted_candidates: int = 0
    agent_runs: int = 0
    issue_url: str | None = None
    message: str


ScoreValue = Annotated[int, Field(ge=0, le=100)]
