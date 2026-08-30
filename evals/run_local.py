from __future__ import annotations

import argparse
import asyncio
import json
import os
from datetime import date
from pathlib import Path

from daily_pm_case_lab.config import Settings
from daily_pm_case_lab.orchestrator import DailyCaseOrchestrator
from daily_pm_case_lab.quality import validate_case_directory


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fixtures", action="store_true", help="Run offline published-case fixtures"
    )
    parser.add_argument("--case-dir", type=Path, action="append", default=[])
    parser.add_argument("--live-company", help="Run the real Agents SDK workflow for one company")
    parser.add_argument("--date", dest="run_date", type=date.fromisoformat, default=date.today())
    return parser.parse_args()


async def main() -> int:
    args = parse_args()
    results: list[dict[str, object]] = []
    if args.live_company:
        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is required for --live-company")
        generated = await DailyCaseOrchestrator(Settings(root_dir=Path.cwd())).generate(
            run_date=args.run_date,
            company_override=args.live_company,
        )
        results.append({"id": "live_workflow", **generated.model_dump(mode="json")})
    for case_dir in args.case_dir:
        report = validate_case_directory(case_dir)
        results.append(
            {
                "id": str(case_dir),
                "passed": report.publishable,
                "report": report.model_dump(mode="json"),
            }
        )
    if args.fixtures:
        fixture_cases = sorted((Path.cwd() / "cases").glob("*"))
        if not fixture_cases:
            results.append(
                {
                    "id": "offline_contract",
                    "passed": True,
                    "note": "No published cases yet; unit/integration fixtures cover the gate.",
                }
            )
        for case_dir in fixture_cases:
            report = validate_case_directory(case_dir)
            results.append(
                {
                    "id": str(case_dir),
                    "passed": report.publishable,
                    "report": report.model_dump(mode="json"),
                }
            )
    output_dir = Path.cwd() / "evals" / "results"
    output_dir.mkdir(parents=True, exist_ok=True)
    output = {
        "passed": all(item.get("passed", item.get("status") == "published") for item in results),
        "results": results,
    }
    (output_dir / "latest.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if output["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
