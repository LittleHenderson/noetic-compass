# Noetic Compass Validation Protocol

This protocol defines the minimum process for collecting, reviewing, and presenting evidence for the CAS scoring pipeline. It is intentionally operational rather than theoretical.

## 1. Scope

The protocol covers four evidence streams:

1. Human-rater agreement against machine operator scores
2. Scorer-agreement checks between generation and assessment systems
3. Benchmark-suite runs with reproducible provider/model metadata
4. False-positive and false-negative case logging

The protocol does **not** claim that CAS is a validated psychological instrument. It defines how validation evidence should be collected and reviewed.

## 2. Baseline Study

1. Generate a baseline machine study from a fixed prompt set:
   `python validation/run_baseline_study.py --provider <provider> --count <n>`
2. Archive every run under `validation/studies/` and keep `validation/baseline_results.json` reserved for the currently labeled canonical study
3. Record provider, model, prompt count, elapsed time, success/failure counts, and score distribution
4. Freeze the exact prompt set for any benchmark or stakeholder-facing comparison
5. If a live-provider run fails, keep the archived failed run; do not quietly drop it
6. Do not show stakeholder-facing ranking tables built from fewer than 10 prompts. Prefer 10-20 frozen prompts before presenting provider comparisons.

## 2A. Scoring Mode Protocol

There is no zero-bias scoring mode.

- Best least-biased automated baseline: `heuristic_fallback`
  - Avoids model-as-judge bias entirely
  - Tradeoff: structurally consistent, but less semantically rich
- Best overall current app mode: `secondary_llm` with a separate scorer provider
  - Richer than heuristics and closer to real assessment
  - Constraint: the scorer must be external to the generator
- Worst stakeholder comparison mode: `self_reported`
  - The model grades its own output

Stakeholder-facing reporting sequence:

1. Run the frozen prompt set in `heuristic_fallback` for all providers
2. Run the same prompt set in `secondary_llm` with one fixed external scorer
3. Review disagreement cases in the calibration workflow
4. Report heuristic, external-LLM, and human reconciliation results separately

Do not mix scoring modes inside one ranking table.

## 3. Human Labeling

1. Use at least two raters for each prompt-response pair
2. Each rater scores:
   - 10 Cognitive Operators on a 0-10 scale
   - 4 Processing Domains on a 0-10 scale
3. Raters should work independently before reviewing disagreements
4. Save labels in `validation/human_labels.json`

Minimum operational target:
- 50 prompt-response pairs
- 2 raters per item
- 100 total label records

## 4. Correlation Review

Run:

```bash
python validation/correlation_analysis.py --baseline validation/baseline_results.json --labels validation/human_labels.json
```

Review:
- Pearson correlation per operator
- Inter-rater reliability
- Overall machine-human agreement
- Operators flagged for recalibration

Interpretation rule:
- Strong correlation: `r >= 0.70`
- Moderate correlation: `0.40 <= r < 0.70`
- Weak correlation: `r < 0.40`

## 5. Evidence Logging

Seed the evidence log from the baseline study and human labels:

```bash
python validation/seed_evidence_log.py
```

This generates:
- `scorer_agreement` entries from machine vs human-panel item means
- `benchmark_suites` entries from baseline study summaries
- `error_cases` entries where machine tier and human-panel tier disagree

Additional entries may be logged manually through the validation API/UI for:
- external scorer checks
- new benchmark-suite runs
- confirmed false positives / false negatives

Benchmark evidence should be reseeded whenever new studies are added:

```bash
python validation/seed_evidence_log.py
```

The validation leaderboard now exposes:
- archived study history
- provider/model benchmark trends
- filtered evidence review/export
- rater calibration and reconciliation queues

## 6. Error Case Policy

Log an error case when:
- the machine materially overstates quality relative to human review
- the machine materially understates quality relative to human review
- a safety-sensitive answer passes prototype thresholds when raters judge it should not

Each logged case should include:
- prompt excerpt
- expected tier
- observed tier
- provider/model if known
- notes explaining why the case matters

## 7. Reporting Standard

Any stakeholder-facing report should state:

1. The current sample size
2. Number of raters
3. Whether evidence comes from heuristic scoring, self-report, or secondary LLM assessment
4. That `social_engineering` and `bias_flags` remain heuristic risk signals under active validation
5. That the system is a research prototype and not a validated safety or psychological instrument

## 8. Minimum Credibility Threshold Before Stronger Claims

Do not present the system as validated unless all of the following are true:

1. Two or more raters have labeled the benchmark set
2. Inter-rater reliability is no longer poor
3. Operator correlations remain stable across multiple benchmark runs
4. False positives and false negatives are being tracked and reviewed systematically
5. Provider/model provenance is retained for benchmark and scorer-agreement evidence

## 9. Operational Workflow

Recommended sequence:

1. Run one canonical baseline study for the prompt set that humans will label
2. Run additional benchmark suites through `python validation/run_suite_matrix.py --provider <provider>`
3. Collect at least two independent human ratings per canonical item
4. Review calibration on the validation leaderboard before stakeholder use
5. Reseed evidence so the archived-study directory and evidence log stay in sync

## 10. Current Known Limitation

`social_engineering` and `bias_flags` are implemented as heuristic risk signals. They may be useful, but they are not yet validated instruments. Any interpretation of those signals should be presented as provisional.
