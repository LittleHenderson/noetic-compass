# Validation Framework

Reproducibility, sensitivity, and empirical validation tools for the Noetic Compass CAS pipeline.

## Automated Tests

```bash
make validate   # or: pytest validation/ -v
```

- **reproducibility_test.py** — Deterministic mock scoring and benchmark fixture compliance
- **sensitivity_test.py** — Dial sensitivity, prompt sensitivity, open simplex validation

## Validation Study Tooling

### 1. Run Baseline Study

Generate machine scores for prompts from the scenario library:

```bash
# Mock mode (no API key needed, instant)
python validation/run_baseline_study.py --provider mock --count 50

# Real provider (requires API key in .env)
python validation/run_baseline_study.py --provider openai --count 100
```

Outputs `validation/baseline_results.json` with per-prompt scores and summary statistics.

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
