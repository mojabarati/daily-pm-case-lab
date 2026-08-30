from __future__ import annotations

import json
from datetime import date

from .models import CaseCandidate, CaseStudy, Company, ResearchPacket

EVIDENCE_POLICY = """
Evidence policy:
- Use only real public evidence returned by WebSearchTool. Never invent a URL, date, metric,
  quotation, experiment, decision, outcome, or causal relationship.
- Prefer original company material, filings, investor relations, official documentation,
  engineering/product blogs, and first-party interviews. Treat syndications of one report as one
  evidence line.
- Normally collect 7-12 sources (minimum 5), including a primary source when reasonably available
  and at least two source categories.
- Every FACT must cite one or more source IDs. Mark INFERENCE, ANALYSIS, and COUNTERFACTUAL
  explicitly; do not promote low-confidence evidence to fact.
- For YouTube and podcasts, accurately label full content, public transcript, partial transcript,
  metadata only, or secondary coverage. Add a timestamp only when reliably available.
- Prefer paraphrase. Any direct quote must be short and source-supported.
- When evidence is absent, record "Public evidence was not found" as an evidence gap.
"""


def scout_prompt(
    companies: list[Company], history_summary: list[dict[str, str]], run_date: date
) -> str:
    return f"""
Today is {run_date.isoformat()} in Asia/Tehran. Discover strong real product/business cases for only
the company shortlist below. Search the public web before proposing cases. Return at most one
candidate per company and no more than {len(companies)} candidates. A candidate must center on a
specific decision-rich product problem, not a broad company story. Historical and recent cases are
both allowed.

Score each candidate 0-100 on evidence quality, product learning value, decision/trade-off richness,
business relevance, and source diversity. Use conservative scores; likely sources are discovery
hints, not proof. Slugs must be lowercase ASCII kebab-case and must not include the company name.

{EVIDENCE_POLICY}

Allowed companies:
{json.dumps([company.model_dump(mode="json") for company in companies], ensure_ascii=False)}

Recent history to avoid:
{json.dumps(history_summary, ensure_ascii=False)}
"""


def research_prompt(
    candidate: CaseCandidate,
    max_sources: int,
    pass_number: int,
    prior_packet: ResearchPacket | None,
) -> str:
    prior = "None."
    if prior_packet is not None:
        prior = json.dumps(
            {
                "source_urls": [str(source.url) for source in prior_packet.sources],
                "evidence_gaps": prior_packet.evidence_gaps,
                "conflicts": prior_packet.evidence_conflicts,
            },
            ensure_ascii=False,
        )
    return f"""
Research pass {pass_number}. Build a rigorous evidence packet for this candidate:
{candidate.model_dump_json(indent=2)}

Use WebSearchTool broadly but return no more than {max_sources} distinct meaningful sources. Search
for the actual problem signals, constraints, actors, chronology, the company's eventual decision,
rollout, product-relevant operational/technical changes, and measurable outcomes. Include market and
competitor context only when sourced. Capture "Who Said What" statements with role at the time and
context. The `decision_terms` list must contain distinctive phrases that would reveal the real
solution or outcome if they appeared in the learner challenge.

On later passes, close evidence gaps rather than merely repeating the same URLs. Prior pass summary:
{prior}

{EVIDENCE_POLICY}
"""


def synthesis_prompt(packet: ResearchPacket) -> str:
    return f"""
Create the seven required Persian learning documents from the evidence packet below. Keep common PM
terms in English where clearer. Source IDs like [S01] must appear immediately near every significant
factual claim. Do not add facts or URLs outside the packet.

Spoiler boundary:
- `overview_markdown` and especially `challenge_markdown` must not reveal the actual decision,
  implementation, rollout, or outcome.
- The challenge may include only pre-decision context, actors, signals, constraints, and genuinely
  supported data. It must assign the learner a PM role and ask all 12 core assignment questions,
  including metrics, guardrails, risks, and a decision.

Required document contents:
- overview: company, product, period, category, difficulty, exercise time, competencies, short intro,
  and reading order; no major spoilers.
- challenge: Context, Current situation, Users/Actors, Signals, Constraints, Available Data, Your Role,
  and Your Assignment.
- evidence pack: timeline, FACT/INFERENCE labels, known data, stakeholder statements, a `Who Said
  What` section, market/competitor context, conflicts, evidence gaps, and linked Sources.
- what company did: sourced decision, sequence, rollout, changes, and outcomes. Label any inferred
  rationale exactly as an inference not publicly confirmed.
- PM analysis: problem, root cause, strategy, alternatives, prioritization, trade-offs, design,
  metrics, execution, risks, and second-order effects. Include `What Could Have Been Done Better?`.
  For each criticism state observed weakness, evidence, why it mattered, alternative, expected
  benefit, trade-off, risk, and validation. Separate evidence-backed criticism, plausible alternative,
  and speculative counterfactual.
- model answer: problem framing, actors, symptoms, hypotheses, data needed, options/comparison,
  recommendation, MVP, Post-MVP, non-goals, metrics, guardrails, experiment, risks, dependencies,
  rollout, and kill/continue criteria. Reason independently rather than copying the company.
- interview drill: about 5 main, 5 follow-up, and 3 challenge questions, plus an evaluation rubric for
  framing, customer/business understanding, reasoning, prioritization, metrics, trade-offs,
  execution, and communication.

Evidence packet:
{packet.model_dump_json(indent=2)}
"""


def review_prompt(packet: ResearchPacket, study: CaseStudy) -> str:
    return f"""
Act as a skeptical evidence editor and Senior Product Manager. Review this generated case against the
evidence packet. Identify unsupported factual claims, invented specificity, misleading citations,
spoilers in overview/challenge, shallow trade-off analysis, hindsight criticism, missing alternatives,
and weak metrics/guardrails. A blocker means the case must not publish. Score conservatively from
0-100; 75 is the minimum but never pass a blocker merely because the numeric score is high.

Evidence packet:
{packet.model_dump_json(indent=2)}

Generated case:
{study.model_dump_json(indent=2)}
"""


SCOUT_INSTRUCTIONS = """You are the Case Scout for a product-management learning system. Use hosted
web search before returning schema-valid candidates. Follow the evidence and duplicate constraints
literally. Do not write the final case."""

RESEARCH_INSTRUCTIONS = """You are a meticulous product and business researcher. Use hosted web
search and return a structured evidence packet. Treat source provenance and fact/inference separation
as hard requirements. Never fabricate or fill evidence gaps with plausible detail."""

SYNTHESIS_INSTRUCTIONS = """You are a senior Persian-language PM educator. Write an analytically
deep case from only the supplied evidence. Preserve the challenge spoiler boundary and exact citation
IDs. Unknowns remain explicit."""

REVIEW_INSTRUCTIONS = """You are an adversarial evidence reviewer and senior PM. Fail unsupported,
spoiled, shallow, or hindsight-driven cases. Return only the structured review."""
