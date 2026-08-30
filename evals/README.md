# Local evals

`cases.jsonl` records the core behavioral regression matrix. The default fixture mode validates any
published case directories through the same artifact validator used by the CLI:

```powershell
uv run python evals/run_local.py --fixtures
```

Validate an explicit artifact:

```powershell
uv run python evals/run_local.py --case-dir cases/CASE_DIRECTORY
```

The live mode exercises the real deterministic orchestrator and Agents SDK path. It consumes API and
hosted web-search usage and should be run deliberately:

```powershell
uv run python evals/run_local.py --live-company Uber --date 2026-08-30
```

Results are written to ignored `evals/results/latest.json`; no credentials or source content are added.

