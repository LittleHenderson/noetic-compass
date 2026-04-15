# Validation Framework

Reproducibility, sensitivity, and empirical validation tools for the Noetic Compass CAS pipeline.

## Automated Tests

```bash
make validate   # or: pytest validation/ -v
```

- **reproducibility_test.py** — Deterministic mock scoring and benchmark fixture compliance
- **sensitivity_test.py** — Dial sensitivity, prompt sensitivity, open simplex validation

## Validation Study Tooling

See [VALIDATION_PROTOCOL.md](./VALIDATION_PROTOCOL.md) for the documented evidence-collection and review process used by the validation UI/API.

### 1. Run Baseline Study

Generate machine scores for prompts from the scenario library:

```bash
# Mock mode (no API key needed, instant)
python validation/run_baseline_study.py --provider mock --count 50

# Real provider (requires API key in .env)
python validation/run_baseline_study.py --provider openai --count 100
```

Each run is archived to `validation/studies/`. By default the latest canonical run also updates `validation/baseline_results.json`.

### 1b. Run a Benchmark Matrix

Generate multiple archived benchmark studies across scenario collections:

```bash
python validation/run_suite_matrix.py --provider mock --count-per-suite 3
python validation/run_suite_matrix.py --provider openai --count-per-suite 5 --suites sample_prompts,ai_safety,finance
```

This is the fastest way to populate benchmark evidence/trend views without manually logging each suite.

### 2. Human Labeling

Collect human ratings for machine-scored prompt-response pairs:

```bash
python validation/human_labeling_tool.py --results validation/baseline_results.json --rater "Dr. Smith"
```

Saves to `validation/human_labels.json`. Each item gets 10 CO scores (0-10) and 4 domain ratings.

### 3. Correlation Analysis

Compare machine scores against human labels:

```bash
python validation/correlation_analysis.py
```

Produces:
- Pearson correlation per Cognitive Operator (machine vs human)
- Inter-rater reliability (Cohen's kappa) if multiple raters
- Test-retest reliability from reproducibility data
- Summary statistics with 95% confidence intervals

## Benchmark Fixture

`benchmark_fixture.json` contains a frozen reference input and expected output ranges for regression testing.

## Evidence Log Seeding

Seed the validation evidence log from the current baseline study and human labels:

```bash
python validation/seed_evidence_log.py
```

This produces `validation/evidence_log.json` with scorer-agreement cases, benchmark runs from `validation/studies/`, and tier-disagreement error cases derived from the current artifacts.

## Admin / UI Workflow

The validation leaderboard now supports:
- running a baseline study + reseed directly from the UI/API
- running a suite matrix + reseed directly from the UI/API
- reviewing archived study history
- reviewing rater calibration / reconciliation hotspots
- filtering/exporting evidence by kind/provider/model
