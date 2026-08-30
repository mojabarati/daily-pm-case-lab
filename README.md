# Daily PM Case Lab

Daily PM Case Lab is a CLI-first learning system that researches and publishes one Persian
product/business case study per day. It is designed to improve Product Sense, problem framing,
strategy, metrics, trade-off analysis, and decision-making through real technology-company cases.

The MVP uses deterministic Python orchestration around a small number of typed OpenAI Agents SDK
calls. The scout and researcher use OpenAI's hosted `WebSearchTool`; synthesis and critical review
operate only on the structured evidence packet. A case is published only when it clears every hard
check and scores at least 75/100.

## What it produces

Each successful run writes:

```text
cases/YYYY-MM-DD-company-case-slug/
  00-overview.md             # spoiler-free orientation
  01-challenge.md            # solve this before reading further
  02-evidence-pack.md        # facts, inferences, timeline, Who Said What
  03-what-company-did.md     # observed decision and outcome
  04-pm-analysis.md          # senior-PM critique and alternatives
  05-model-answer.md         # independent model PM answer
  06-interview-drill.md      # questions and evaluation rubric
  sources.json               # structured source provenance
  manifest.json              # publication metadata and quality score
```

The append-only `data/history.jsonl` is updated only after all files are atomically published.

## Prerequisites

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/)
- an OpenAI Platform API key with access to the configured model
- GitHub CLI only when using Issue delivery

Current implementation choices follow the official [OpenAI Agents SDK guide](https://developers.openai.com/api/docs/guides/agents), [web-search guide](https://developers.openai.com/api/docs/guides/tools-web-search), and [Structured Outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs). The default `gpt-5.6-terra` model is configurable; measure quality, latency, and cost against your own evals before changing it.

## Local setup

```powershell
uv sync --all-groups --python 3.12
Copy-Item .env.example .env.local
```

Set `OPENAI_API_KEY` in `.env.local`. Never commit that file. The provided `.gitignore` excludes all
`.env*` files except the intentionally blank `.env.example`.

Configuration:

| Variable | Default | Purpose |
|---|---:|---|
| `OPENAI_MODEL` | `gpt-5.6-terra` | Responses-based model used by Agents SDK |
| `MAX_CASE_CANDIDATES` | `5` | Maximum daily candidate count |
| `MAX_RESEARCH_PASSES` | `3` | Research retries per candidate |
| `MAX_SOURCES` | `12` | Maximum sources returned in a packet |
| `MAX_AGENT_RUNS` | `12` | Absolute SDK-call budget per command |
| `PM_CASE_LOG_LEVEL` | `INFO` | structured-log level |
| `PM_CASE_GITHUB_REPOSITORY` | unset | `owner/repo` for Issue delivery |

The application does not contain token prices. Usage, tool calls, duration, and stage outcome are
logged as sanitized JSON when exposed by the SDK.

## Commands

Validate the exact 100-company catalog:

```powershell
uv run pm-case-lab catalog-check
```

Preview deterministic company selection without API calls or writes:

```powershell
uv run pm-case-lab generate --dry-run
uv run pm-case-lab generate --dry-run --company Uber --date 2026-08-30
```

Generate today's case (date is evaluated in `Asia/Tehran`):

```powershell
uv run pm-case-lab generate
```

Run a focused smoke case and optionally create an Issue:

```powershell
uv run pm-case-lab generate --company Uber --date 2026-08-30
$env:PM_CASE_GITHUB_REPOSITORY = "OWNER/daily-pm-case-lab"
uv run pm-case-lab generate --company DoorDash --deliver-issue
```

Validate a published directory and inspect history:

```powershell
uv run pm-case-lab validate cases/2026-08-30-uber-example-slug
uv run pm-case-lab history
```

Run code quality and tests:

```powershell
uv run ruff check .
uv run pytest
uv run python evals/run_local.py --fixtures
```

## Selection and quality behavior

Selection prefers the lowest-covered companies, categories with less history, and companies not seen
recently. A stable date/company hash breaks ties, so a dry run is reproducible. `--company` is a
research override, not a quality bypass.

Candidates are scored with the required weights: evidence 30%, learning value 25%, trade-off richness
20%, business relevance 15%, and source diversity 10%. Local code recomputes the evidence dimensions
from the packet. A model reviewer may lower the score or add blockers but cannot override local hard
checks.

Hard failures include fewer than five distinct sources, weak source diversity, unresolved citations,
missing primary evidence without an explicit evidence gap, duplicate history, spoiler terms in the
challenge, missing analytical sections, or API-key-like content. Exhausting candidates or the call
budget exits non-zero without mutating history.

## GitHub Actions scheduler

`.github/workflows/daily-case.yml` supports manual dispatch and uses `30 8 * * *`, which is 12:00 in
`Asia/Tehran` under the current UTC+03:30 civil-time rule. GitHub cron is UTC; if Iran's timezone law
changes, update the expression. Scheduled workflows can be delayed by GitHub load, so 12:00 is a
target rather than a real-time guarantee.

Repository settings required:

- Actions secret `OPENAI_API_KEY`.
- Workflow permissions for `contents: write` and `issues: write` (already requested in YAML; the
  organization/repository policy must allow them).
- Default branch `main`.

The workflow serializes runs with a non-cancelling concurrency group, installs the locked environment,
runs Ruff and pytest, generates a case, commits only `cases/` and `data/history.jsonl`, pushes it, then
creates a concise Issue. The application never stores `GITHUB_TOKEN` or the OpenAI key in artifacts.

## Evidence and language rules

Educational content defaults to professional Persian while retaining useful English terms such as
Retention, Marketplace Liquidity, Unit Economics, North Star Metric, Guardrail Metric, CAC, LTV, MVP,
Experiment, Funnel, and Conversion. Significant facts require nearby `[Sxx]` references. Unknowns stay
unknown; inferences and counterfactuals are explicit.

Video and podcast records describe the actual access level. Metadata discovery is never represented as
full-content review. Long quotations, brittle scraping, access-control bypasses, and paid search APIs are
outside the MVP.

## Known limitations

- URL shape, source identity, and claim references are checked locally, but a future adapter should
  independently fetch and archive source excerpts for stronger entailment verification.
- The spoiler gate combines distinctive decision terms with adversarial model review; nuanced semantic
  spoilers can still require human review.
- Public evidence may not reveal internal experiments, rationale, or metrics. The correct behavior is to
  publish an evidence gap or reject the candidate.
- GitHub Issues are notifications, not a transactional delivery queue. A post-publication delivery
  failure leaves the generated case intact and returns a failure for explicit retry.
- The fixed UTC cron must be reviewed after any Iranian civil-time change.

See [the architecture contract](docs/architecture.md) for the full state machine and design rationale.

## Post-MVP candidates

Evidence-driven extensions include independent URL/content verification, RSS and public-transcript
adapters, human approval, semantic duplicate embeddings, platform trace graders, cost dashboards, and
additional output languages. A frontend, database, queue, paid search, and scraping remain intentionally
out of scope.

