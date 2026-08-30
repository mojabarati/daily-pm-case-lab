from __future__ import annotations

from datetime import date

from daily_pm_case_lab.models import (
    CandidateScore,
    CaseCandidate,
    CaseStudy,
    Claim,
    ClaimType,
    Confidence,
    ContentAccessLevel,
    QualityCheck,
    ResearchPacket,
    ReviewerReport,
    Source,
    TimelineEvent,
)


def candidate(company_id: str = "uber") -> CaseCandidate:
    return CaseCandidate(
        company_id=company_id,
        company_name="Uber" if company_id == "uber" else company_id.title(),
        case_title="Balancing rider demand and driver supply",
        case_slug="marketplace-liquidity-inflection",
        primary_problem="Long pickup times caused by an imbalanced two-sided marketplace",
        case_category="Marketplace liquidity",
        time_period="2014-2016",
        product="Rides marketplace",
        difficulty="Hard",
        why_educational="The case exposes incentives, pricing, trust, and network-effect trade-offs.",
        likely_primary_sources=["investor relations", "company engineering blog"],
        score=CandidateScore(
            evidence_quality=90,
            product_learning_value=90,
            decision_tradeoff_richness=90,
            business_relevance=85,
            source_diversity=85,
            rationale="Strong public evidence and a rich two-sided decision.",
        ),
    )


def packet(case_candidate: CaseCandidate | None = None) -> ResearchPacket:
    case_candidate = case_candidate or candidate()
    sources = [
        Source(
            id=f"S{index:02d}",
            type="company_blog" if index == 1 else "reputable_news",
            title=f"Source {index}",
            publisher="Uber" if index == 1 else f"Publisher {index}",
            url=f"https://example.com/source-{index}",
            published_at=date(2016, 1, min(index, 28)).isoformat(),
            accessed_at=date(2026, 8, 30).isoformat(),
            is_primary=index == 1,
            content_access_level=ContentAccessLevel.FULL,
            credibility_score=90 if index == 1 else 75,
            relevant_sections=["marketplace signals", "decision"],
            used_for=["problem", "timeline"],
        )
        for index in range(1, 6)
    ]
    return ResearchPacket(
        candidate=case_candidate,
        sources=sources,
        claims=[
            Claim(
                claim="Public reporting described a marketplace balance problem.",
                source_ids=["S01", "S02"],
                claim_type=ClaimType.FACT,
                confidence=Confidence.HIGH,
            )
        ],
        statements=[],
        timeline=[
            TimelineEvent(
                date_or_period="2015",
                event="The company tested a marketplace intervention.",
                source_ids=["S01"],
                confidence=Confidence.HIGH,
            )
        ],
        actual_decision=[
            Claim(
                claim="The company introduced dynamic pricing in constrained periods.",
                source_ids=["S01"],
                claim_type=ClaimType.FACT,
                confidence=Confidence.HIGH,
            )
        ],
        outcomes=[],
        decision_terms=["dynamic pricing", "surge multiplier"],
        evidence_gaps=["No public experiment-level conversion metric was found."],
    )


def study() -> CaseStudy:
    challenge_core = """# Challenge\n\n## Context\nیک marketplace دوسویه با عدم تعادل روبه‌رو است. [S01]\n\n## Current situation\nزمان انتظار و قابلیت اطمینان تجربه تحت فشار است. [S02]\n\n## Users / Actors\nراننده، مسافر، تیم عملیات و رگولاتور.\n\n## Signals\nشواهد عمومی وجود مسئله را نشان می‌دهد. [S01]\n\n## Constraints\nUnit Economics، اعتماد، ظرفیت عملیاتی و رقابت.\n\n## Available Data\nفقط داده‌های عمومی بسته شواهد؛ داده داخلی فرض نمی‌شود.\n\n## Your Role\nشما PM مسئول سلامت marketplace هستید.\n\n## Your Assignment\n1. مسئله واقعی چیست؟\n2. symptom و root cause چه تفاوتی دارند؟\n3. بازیگران کلیدی چه کسانی‌اند؟\n4. چه فرضیه‌هایی را بررسی می‌کنید؟\n5. چه داده دیگری می‌خواهید؟\n6. چه گزینه‌هایی دارید؟\n7. چگونه اولویت‌بندی می‌کنید؟\n8. MVP چیست؟\n9. Metrics اصلی چیست؟\n10. Guardrail Metrics چیست؟\n11. چه ریسک‌هایی رویکرد شما را باطل می‌کنند؟\n12. چه تصمیمی می‌گیرید؟\n"""
    challenge = challenge_core + ("\nتحلیل خود را با فرض‌های روشن و روش ابطال بنویسید." * 20)
    model_answer = (
        "# Model PM Answer\n\nProblem framing، actors، symptoms، root-cause hypotheses، data needed، "
        "strategic options، option comparison، recommended approach، MVP، Post-MVP، non-goals، "
        "Metrics، Guardrail Metrics، Experiment design، risks، dependencies، rollout و kill/continue "
        "criteria.\n\n"
        + ("گزینه‌ها باید با ارزش کاربر، Unit Economics و ریسک اجرایی مقایسه شوند. " * 35)
    )
    return CaseStudy(
        overview_markdown="# Overview\n\nمعرفی بدون راه‌حل و ترتیب مطالعه.",
        challenge_markdown=challenge,
        evidence_pack_markdown="# Evidence Pack\n\nFACT [S01]\n\n# Who Said What\n",
        what_company_did_markdown="# What Company Did\n\nتصمیم مستند [S01].",
        pm_analysis_markdown=(
            "# PM Analysis\n\nTrade-off میان تجربه و اقتصاد.\n\n"
            "# What Could Have Been Done Better?\n\nObserved weakness، Evidence [S01]، Why it "
            "mattered، Alternative، Expected benefit، Trade-off، Risk، How to validate."
        ),
        model_answer_markdown=model_answer,
        interview_drill_markdown=(
            "# Interview Drill\n\nپنج سوال اصلی، پنج follow-up و سه challenge.\n\n"
            "### Evaluation Rubric\nProblem framing، customer، business، metrics و execution."
        ),
        estimated_exercise_minutes=75,
        competencies=["Product Sense", "Marketplace", "Metrics", "Trade-offs"],
    )


def reviewer(score: int = 88) -> ReviewerReport:
    return ReviewerReport(
        score=score,
        checks=[QualityCheck(name="review_depth", passed=True, detail="Depth acceptable")],
        analytical_depth_notes=["Alternatives and validation are explicit."],
    )
