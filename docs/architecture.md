# Daily PM Case Lab — Architecture

Status: implementation contract for the MVP  
Runtime: Python 3.12+, `uv`, OpenAI Agents SDK, GitHub Actions  
Business timezone: `Asia/Tehran`

## Product contract

Daily PM Case Lab creates one evidence-backed Persian product/business case study per successful manual run. It is a deliberate-practice system, not a content aggregator: the learner first receives a spoiler-free challenge, then an evidence pack, the company's observed response, senior-PM analysis, a model answer, and an interview drill.

Success means that a published case:

- concerns a real problem at one of exactly 100 catalogued technology companies;
- has a deterministic, auditable selection path and is not a duplicate;
- scores at least 75/100 under the local quality gate;
- normally includes at least five distinct meaningful sources, at least one primary source when reasonably available, and at least two source categories;
- labels facts, inferences, analysis, and counterfactuals separately;
- never invents metrics, dates, decisions, quotations, causal claims, or URLs;
- keeps `00-overview.md` and `01-challenge.md` free of the actual decision and outcome;
- writes the complete Markdown/JSON artifact set atomically before changing history;
- can notify through a GitHub Issue without making delivery a prerequisite for artifact correctness.

## Constraints and decisions

- Python 3.12+ and `uv`; no frontend, database, queue, cache, vector store, or extra SaaS.
- OpenAI Agents SDK over the Responses API. The default model is configurable and starts at `gpt-5.6-terra`, the balanced GPT-5.6 model; production owners can override `OPENAI_MODEL` after evals.
- Hosted `WebSearchTool` is the only MVP research integration. No scraping and no claim that multimedia was reviewed beyond the recorded access level.
- Deterministic Python owns orchestration, budgets, scoring, validation, filesystem writes, history, and delivery. Models propose researched structured data and educational prose; they do not control loops or side effects.
- Pydantic models are the stage contracts. Large free-form handoffs are confined to final Markdown sections.
- Secrets are loaded from the process environment or ignored `.env.local`, never logged, serialized into cases, or committed.

## Runtime flow

```text
CLI / GitHub Actions
        |
        v
Config + catalog/history validation
        |
        v
Deterministic company shortlist
  (coverage, rotation, category diversity, optional override)
        |
        v
Case Scout (Agents SDK + WebSearchTool)
        |
        v
Candidate scoring and duplicate rejection
        |
        v
Researcher (Agents SDK + WebSearchTool)
        |
        v
Evidence normalization and deterministic checks
        |
        v
Case Synthesizer (Agents SDK, structured output)
        |
        v
Critical Reviewer (Agents SDK, structured QualityReport)
        |
        v
Local quality gate (must be >= 75)
        |
   pass | fail -> next candidate, within fixed budgets
        v
Atomic file publication + history append
        |
        v
Optional GitHubIssueDelivery
```

The initial agent topology is four logical calls, not an autonomous multi-agent mesh. Agent instances are stage-specific because their tools and output schemas differ. The runner remains a bounded sequential state machine.

## Stage contracts

Core Pydantic models:

- `Company`: the fixed catalog record.
- `Source`: provenance, access level, credibility, primary status, relevant sections, and multimedia timestamps.
- `Claim`: text, source IDs, `FACT | INFERENCE | ANALYSIS | COUNTERFACTUAL`, and confidence.
- `PersonStatement`: person, role-at-the-time, date, context, paraphrase/short quote, and source ID.
- `CaseCandidate`: company/problem/category/period plus learning and trade-off attributes.
- `CandidateScore`: five weighted dimensions totaling 100.
- `ResearchPacket`: candidate, sources, claims, statements, timeline, decision/outcome evidence, conflicts, and evidence gaps.
- `CaseStudy`: metadata plus the seven required Markdown documents.
- `QualityReport`: deterministic checks, reviewer findings, score, publish decision, and blockers.
- `Manifest` and `HistoryRecord`: publication metadata.

All models forbid unexpected fields where practical. URLs must be HTTP(S), source IDs must be unique, claim references must resolve, and important unknowns remain explicit evidence gaps.

## Selection and duplicate protection

The selector first calculates catalog coverage from immutable catalog IDs plus append-only history. It sorts by:

1. lowest historical case count;
2. longest time since the company appeared;
3. underrepresented company category and recent case category;
4. stable daily hash for deterministic tie-breaking.

An explicit `--company` override narrows research but does not bypass evidence, duplicate, or quality gates.

Duplicate checks reject:

- an existing `case_slug`;
- normalized exact title or primary-problem matches;
- high token-set similarity against earlier title/problem pairs;
- a candidate the scout labels as the same decision/outcome already covered.

Company rotation is a preference, not permission to publish a weak case. The orchestrator tries a bounded shortlist and stops cleanly if nothing reaches the threshold.

## Candidate scoring

The required score is computed as:

| Dimension | Weight |
|---|---:|
| Evidence quality | 30 |
| Product learning value | 25 |
| Decision/trade-off richness | 20 |
| Business relevance | 15 |
| Source diversity | 10 |

Model-proposed dimension scores are clamped and re-evaluated against observable evidence. The deterministic gate also caps evidence quality when minimum source, primary-source, citation-resolution, or category-diversity requirements are absent. Publishing requires both a total of at least 75 and every hard validation check.

## Quality and spoiler gates

Hard checks include:

- exact required files and valid JSON;
- at least five unique meaningful sources, at least two source categories, and a primary source unless the packet explicitly records why none was reasonably available;
- valid, deduplicated HTTP(S) URLs and resolvable source references;
- every factual `Claim` has source IDs;
- fact/inference labels and confidence values;
- critique, alternatives, metrics, risks, guardrails, second-order effects, and model answer;
- history rotation and duplicate checks;
- spoiler terms from the actual decision/outcome absent from the overview/challenge;
- no secret-like tokens in generated content.

The critical reviewer can lower the score or add blockers. It cannot override a failed deterministic check.

## Output and atomicity

Successful runs create:

```text
cases/YYYY-MM-DD-company-case-slug/
  00-overview.md
  01-challenge.md
  02-evidence-pack.md
  03-what-company-did.md
  04-pm-analysis.md
  05-model-answer.md
  06-interview-drill.md
  sources.json
  manifest.json
```

Files are first written to a temporary sibling directory, parsed and validated, then renamed into place. `data/history.jsonl` is appended only after publication succeeds. A pre-existing final path is never overwritten.

## Cost and runaway controls

Environment limits:

- `MAX_CASE_CANDIDATES=5`
- `MAX_RESEARCH_PASSES=3`
- `MAX_SOURCES=12`
- `MAX_AGENT_RUNS=12`
- `OPENAI_MODEL=gpt-5.6-terra`

The call budget is checked before every SDK run. Research passes and candidate attempts are fixed loops. No agent is allowed to recursively hand off or schedule more work. Logs record stage, attempt, duration, model/tool-call counts, token usage when exposed, outcome, and sanitized error class.

## Failure behavior

- Configuration/catalog/history errors fail before API calls.
- Transient model/tool errors receive a small bounded retry with backoff owned by Python.
- Schema failures count against the same call budget; they never create partial output.
- A quality score below 75 advances to the next candidate.
- Exhausted candidates/budgets exit non-zero with a structured summary and no history change.
- GitHub Issue delivery failures are reported and make the command fail after local publication; generated files remain available for retry and are not duplicated.

## Interfaces

CLI commands:

- `pm-case-lab generate [--date YYYY-MM-DD] [--company ID_OR_NAME] [--dry-run] [--deliver-issue]`
- `pm-case-lab validate [CASE_DIRECTORY]`
- `pm-case-lab catalog-check`
- `pm-case-lab history`

`--dry-run` performs selection and reports planned candidates without API calls, filesystem publication, history mutation, or delivery.

`GitHubIssueDelivery` uses GitHub's CLI with `GITHUB_TOKEN`/Actions permissions and an explicit repository. It sends only a concise case summary and repository-relative links; it never includes credentials or large generated content.

## Manual GitHub Actions execution

GitHub Actions runs only through `workflow_dispatch`. The optional `company` input accepts a catalog company ID, name, or alias; when it is empty, the application performs its normal automatic catalog selection. Workflow concurrency permits one non-cancelling run at a time. The workflow installs `uv`, syncs the locked environment, runs the generator, commits only generated case/history changes, pushes, and creates the optional Issue using the repository token.

## Verification strategy

- Unit tests: catalog exactly 100, deterministic rotation, history parsing, duplicate similarity, candidate score math, hard quality checks, spoiler detection, atomic publication, secret redaction, delivery command construction, and configuration limits.
- Integration tests: full offline run through a fake typed agent gateway, including retry, fallback candidate, threshold rejection, and output/history success.
- Local eval harness: representative pass/fail fixtures grade source grounding, spoiler freedom, analytical depth, evidence labels, and required sections against the real workflow when credentials are present.
- Live smoke: one Uber or DoorDash case only after the credential gate. Inspect every source URL, nearby support for major claims, spoiler separation, unsupported specifics, and PM depth. A smoke failure is reported honestly and does not justify a production-ready claim.

## Security and repository policy

`.env*` is ignored except `.env.example`. Logging recursively redacts values under secret-like keys and strings matching API-key patterns. Generated content is scanned before publication. Git commits are granular: architecture, core data/models, pipeline/output, delivery/automation/docs, and tests/evals. A private GitHub repository is created and pushed only when authenticated GitHub tooling is available and the target name is safe to create.

## Post-MVP

Potential extensions, justified only by observed needs: richer URL-content verification, RSS and public transcript adapters, manual reviewer approvals, semantic duplicate embeddings, platform eval datasets/trace graders, cost dashboards, and multi-language output. Paid search, brittle scraping, a database, and a frontend remain out of scope until evidence supports them.
