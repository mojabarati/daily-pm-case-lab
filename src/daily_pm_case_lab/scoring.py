from __future__ import annotations

from .models import CandidateScore, CaseCandidate, ResearchPacket


def researched_score(candidate: CaseCandidate, packet: ResearchPacket) -> CandidateScore:
    unique_urls = {str(source.url).rstrip("/").casefold() for source in packet.sources}
    source_types = {source.type.casefold() for source in packet.sources}
    primary_count = sum(source.is_primary for source in packet.sources)
    cited_facts = [claim for claim in packet.claims if claim.claim_type.value == "FACT"]
    resolved_fact_ratio = (
        sum(bool(claim.source_ids) for claim in cited_facts) / len(cited_facts)
        if cited_facts
        else 0.0
    )
    evidence = min(
        100,
        len(unique_urls) * 10
        + min(primary_count, 2) * 10
        + min(len(source_types), 4) * 5
        + round(resolved_fact_ratio * 10),
    )
    diversity = min(100, len(source_types) * 25 + min(primary_count, 2) * 10)
    return CandidateScore(
        evidence_quality=evidence,
        product_learning_value=candidate.score.product_learning_value,
        decision_tradeoff_richness=candidate.score.decision_tradeoff_richness,
        business_relevance=candidate.score.business_relevance,
        source_diversity=diversity,
        rationale=(
            f"Observed {len(unique_urls)} unique sources across {len(source_types)} types, "
            f"including {primary_count} primary sources."
        ),
    )


def with_score(candidate: CaseCandidate, score: CandidateScore) -> CaseCandidate:
    # Pydantic models are mutable by default, but a validated copy keeps the boundary explicit.
    data = candidate.model_dump()
    data["score"] = score.model_dump()
    return CaseCandidate.model_validate(data)
