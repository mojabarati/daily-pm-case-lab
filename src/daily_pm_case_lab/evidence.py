from __future__ import annotations

from .models import Claim, ResearchPacket


def canonicalize_source_ids(packet: ResearchPacket) -> ResearchPacket:
    """Rewrite model-proposed source IDs to S01.. and preserve references."""

    original_ids = [source.id for source in packet.sources]
    if len(original_ids) != len(set(original_ids)):
        raise ValueError("Research packet contains duplicate source IDs")

    aliases: dict[str, str] = {}
    for index, source in enumerate(packet.sources, start=1):
        canonical = f"S{index:02d}"
        for alias in (source.id, f"S{index}", canonical):
            existing = aliases.get(alias)
            if existing is not None and existing != canonical:
                raise ValueError(f"Ambiguous source alias: {alias}")
            aliases[alias] = canonical
        source.id = canonical

    def references(values: list[str]) -> list[str]:
        normalized: list[str] = []
        for value in values:
            if value not in aliases:
                raise ValueError(f"Unresolved source ID: {value}")
            canonical = aliases[value]
            if canonical not in normalized:
                normalized.append(canonical)
        return normalized

    claim_groups: list[list[Claim]] = [
        packet.claims,
        packet.market_context,
        packet.competitor_context,
        packet.actual_decision,
        packet.outcomes,
    ]
    for claims in claim_groups:
        for claim in claims:
            claim.source_ids = references(claim.source_ids)
    for statement in packet.statements:
        statement.source_id = references([statement.source_id])[0]
    for event in packet.timeline:
        event.source_ids = references(event.source_ids)
    return packet
