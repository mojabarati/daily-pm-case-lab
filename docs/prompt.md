# Runtime prompt contract

The production prompt text lives in `src/daily_pm_case_lab/prompts.py` so it is versioned and tested with
the code that consumes it. Its invariants are:

- hosted web search is mandatory for scouting and research;
- only returned public evidence may become a source or fact;
- facts cite stable source IDs and remain distinct from inference, analysis, and counterfactual;
- metadata-only multimedia is never described as fully reviewed;
- overview/challenge hide the actual decision, implementation, and outcome;
- synthesis uses only the structured `ResearchPacket`;
- adversarial review fails unsupported, spoiled, or shallow output;
- Persian is the default educational language with common PM terms retained in English.

Prompts describe outcomes and validation boundaries. Python, not prompt prose, owns budgets, retries,
selection, duplicate checks, quality thresholds, filesystem writes, and GitHub delivery.

