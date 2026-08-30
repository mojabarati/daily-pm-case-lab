from __future__ import annotations

import json
import os
import shutil
import tempfile
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .models import CaseStudy, Manifest, QualityReport, ResearchPacket
from .quality import REQUIRED_FILES

TEHRAN = ZoneInfo("Asia/Tehran")


def case_directory_name(run_date: date, packet: ResearchPacket) -> str:
    return f"{run_date.isoformat()}-{packet.candidate.company_id}-{packet.candidate.case_slug}"


def publish_case(
    *,
    cases_dir: Path,
    run_date: date,
    packet: ResearchPacket,
    study: CaseStudy,
    quality: QualityReport,
    model: str,
) -> tuple[Path, Manifest]:
    final_path = cases_dir / case_directory_name(run_date, packet)
    if final_path.exists():
        raise FileExistsError(f"Refusing to overwrite existing case: {final_path}")
    cases_dir.mkdir(parents=True, exist_ok=True)
    temp_path = Path(tempfile.mkdtemp(prefix=".tmp-", dir=cases_dir))
    try:
        files = {
            "00-overview.md": study.overview_markdown,
            "01-challenge.md": study.challenge_markdown,
            "02-evidence-pack.md": study.evidence_pack_markdown,
            "03-what-company-did.md": study.what_company_did_markdown,
            "04-pm-analysis.md": study.pm_analysis_markdown,
            "05-model-answer.md": study.model_answer_markdown,
            "06-interview-drill.md": study.interview_drill_markdown,
        }
        for name, content in files.items():
            (temp_path / name).write_text(content.rstrip() + "\n", encoding="utf-8", newline="\n")

        sources_payload = {"sources": [source.model_dump(mode="json") for source in packet.sources]}
        (temp_path / "sources.json").write_text(
            json.dumps(sources_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        manifest = Manifest(
            date=run_date,
            company=packet.candidate.company_name,
            case_title=packet.candidate.case_title,
            case_slug=packet.candidate.case_slug,
            category=packet.candidate.case_category,
            difficulty=packet.candidate.difficulty,
            source_count=len(packet.sources),
            primary_source_count=sum(source.is_primary for source in packet.sources),
            quality_score=quality.score,
            generated_at=datetime.now(TEHRAN),
            model=model,
        )
        (temp_path / "manifest.json").write_text(
            manifest.model_dump_json(indent=2) + "\n", encoding="utf-8", newline="\n"
        )
        if {path.name for path in temp_path.iterdir()} != REQUIRED_FILES:
            raise RuntimeError("Staged publication does not contain the exact required file set")
        os.replace(temp_path, final_path)
        return final_path, manifest
    except Exception:
        if temp_path.exists():
            shutil.rmtree(temp_path)
        raise
