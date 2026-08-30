from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

from .catalog import load_catalog
from .config import Settings
from .history import load_history
from .logging_utils import configure_logging
from .orchestrator import DailyCaseOrchestrator
from .quality import validate_case_directory

TEHRAN = ZoneInfo("Asia/Tehran")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pm-case-lab")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="Generate and quality-gate a daily case")
    generate.add_argument("--date", dest="run_date", type=date.fromisoformat)
    generate.add_argument("--company")
    generate.add_argument("--dry-run", action="store_true")
    generate.add_argument("--deliver-issue", action="store_true")

    validate = subparsers.add_parser("validate", help="Validate a published case directory")
    validate.add_argument("case_directory", type=Path)
    subparsers.add_parser("catalog-check", help="Validate the 100-company catalog")
    subparsers.add_parser("history", help="Summarize publication history")
    return parser


def _settings() -> Settings:
    load_dotenv(Path.cwd() / ".env.local", override=False)
    return Settings(root_dir=Path.cwd())


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    settings = _settings()
    configure_logging(settings.log_level)
    try:
        if args.command == "generate":
            run_date = args.run_date or datetime.now(TEHRAN).date()
            result = asyncio.run(
                DailyCaseOrchestrator(settings).generate(
                    run_date=run_date,
                    company_override=args.company,
                    dry_run=args.dry_run,
                    deliver_issue=args.deliver_issue,
                )
            )
            print(result.model_dump_json(indent=2))
            return 0 if result.status in {"published", "dry_run"} else 2
        if args.command == "validate":
            report = validate_case_directory(args.case_directory)
            print(report.model_dump_json(indent=2))
            return 0 if report.publishable else 2
        if args.command == "catalog-check":
            companies = load_catalog(settings.data_dir / "company_catalog.yaml")
            print(
                json.dumps(
                    {
                        "valid": True,
                        "company_count": len(companies),
                        "categories": dict(Counter(company.category for company in companies)),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0
        if args.command == "history":
            records = load_history(settings.data_dir / "history.jsonl")
            print(
                json.dumps(
                    {
                        "case_count": len(records),
                        "company_counts": dict(Counter(record.company for record in records)),
                        "category_counts": dict(
                            Counter(record.case_category for record in records)
                        ),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0
    except Exception as exc:
        print(
            json.dumps(
                {"status": "failed", "error_type": type(exc).__name__, "message": str(exc)},
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
