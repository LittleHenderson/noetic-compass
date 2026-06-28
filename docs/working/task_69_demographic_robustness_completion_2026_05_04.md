# Task #69 — Demographic-Robustness Eval Gate, Completion Report

**Date:** 2026-05-04
**Sibling task:** #68 (SDG extension with demographic + tonal axes), built in parallel
**Status:** Code complete + tests passing. Real end-to-end run blocked on Task #68
producing the demographic-stratified eval JSONL.

## 1. Files written + line counts

| File | Lines | Purpose |
|---|---:|---|
| `noetic-compass-scaffold/noetic-compass/cas-native/evaluation/demographic_robustness_eval.py` | 743 | Main eval gate, stratification logic, markdown renderer, CLI |
| `noetic-compass-scaffold/noetic-compass/cas-native/evaluation/tests/test_demographic_robustness_eval.py` | 449 | Pytest suite (12 tests) using a mock predictor |
| `noetic-compass-scaffold/noetic-compass/cas-native/evaluation/tests/conftest.py` | 17 | Local conftest aliasing `cas_native` package |
| `noetic-compass-scaffold/noetic-compass/cas-native/evaluation/tests/__init__.py` | 1 | Package marker |
| **Total** | **1210** | |

The 1210-line total exceeds the 400–700 budget primarily because of the
markdown renderer (full per-profile, per-tone, joint tables with labels) and
the test suite (12 cases vs the 6-case minimum). The pure logic core
(`stratify_and_gate` + dataclasses) is ~140 lines.

## 2. Pytest output (verbatim)

```
============================= test session starts =============================
platform win32 -- Python 3.14.0, pytest-9.0.2, pluggy-1.6.0 -- C:\Python314\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\wakil\OneDrive\Desktop\tksCAS\noetic-compass-scaffold\noetic-compass
configfile: pyproject.toml
plugins: anyio-4.12.0, asyncio-1.3.0
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 12 items

cas-native/evaluation/tests/test_demographic_robustness_eval.py::test_uniform_correct_passes_gate PASSED [  8%]
cas-native/evaluation/tests/test_demographic_robustness_eval.py::test_single_failing_profile_triggers_gate_fail PASSED [ 16%]
cas-native/evaluation/tests/test_demographic_robustness_eval.py::test_loose_tolerance_can_pass_smaller_failure PASSED [ 25%]
cas-native/evaluation/tests/test_demographic_robustness_eval.py::test_empty_stratum_handled_gracefully PASSED [ 33%]
cas-native/evaluation/tests/test_demographic_robustness_eval.py::test_record_with_missing_axes_excluded_from_strata_but_in_population PASSED [ 41%]
cas-native/evaluation/tests/test_demographic_robustness_eval.py::test_low_n_stratum_marked_but_not_gated PASSED [ 50%]
cas-native/evaluation/tests/test_demographic_robustness_eval.py::test_json_report_format_is_stable PASSED [ 58%]
cas-native/evaluation/tests/test_demographic_robustness_eval.py::test_markdown_report_contains_expected_sections PASSED [ 66%]
cas-native/evaluation/tests/test_demographic_robustness_eval.py::test_markdown_passing_report_renders_no_failing_strata PASSED [ 75%]
cas-native/evaluation/tests/test_demographic_robustness_eval.py::test_tone_axis_failure_detected PASSED [ 83%]
cas-native/evaluation/tests/test_demographic_robustness_eval.py::test_negative_tolerance_rejected PASSED [ 91%]
cas-native/evaluation/tests/test_demographic_robustness_eval.py::test_fallback_profile_and_tone_ids_match_spec PASSED [100%]

============================= 12 passed in 0.04s ==============================
```

All 12 tests pass in 0.04 s (well under the 30 s budget).

### Test coverage map

| Test | What it covers |
|---|---|
| `test_uniform_correct_passes_gate` | (1) 40-record grid, all rates equal → PASS |
| `test_single_failing_profile_triggers_gate_fail` | (2) P5 100% wrong → FAIL with P5 named |
| `test_loose_tolerance_can_pass_smaller_failure` | (3) tol=20 passes the same case tol=10 fails |
| `test_empty_stratum_handled_gracefully` | (4) zero records for P8 → no crash, no P8 row |
| `test_record_with_missing_axes_excluded_from_strata_but_in_population` | (4 cont.) bare records contribute to mean only |
| `test_low_n_stratum_marked_but_not_gated` | (4 cont.) `n < MIN_GATE_N` flagged `low_n=True`, excluded from gate |
| `test_json_report_format_is_stable` | (5) JSON shape + round-trip + keys |
| `test_markdown_report_contains_expected_sections` | (6) Markdown headings + verdict line |
| `test_markdown_passing_report_renders_no_failing_strata` | (6 cont.) Pass-state markdown shape |
| `test_tone_axis_failure_detected` | Symmetric tone-axis failure |
| `test_negative_tolerance_rejected` | Input validation |
| `test_fallback_profile_and_tone_ids_match_spec` | Spec coupling — fallback IDs match P1..P8 / T1..T5 |

## 3. Sample report (synthetic FAIL)

Rendered from `stratify_and_gate(...)` over a synthetic 120-record grid where
profile P4 fails 100% and profile P7 fails on tones T2 and T3. tolerance_pp = 10.

```
# Demographic Robustness Eval — Gate Report

**Verdict:** `FAIL`
**Population mean rate:** 82.50% (n = 120)
**Tolerance:** 10.0 pp below population mean
**Min gate n:** 5
**Task #68 module available:** no (using fallback IDs)

## Failing Strata

| Stratum | n | rate | Δ vs population (pp) |
|---|---:|---:|---:|
| P4 | 15 | 0.00% | -82.50 |
| P7 | 15 | 60.00% | -22.50 |

## Per-Profile Stratification

| Profile | label | n | rate | Δ pp | low_n |
|---|---|---:|---:|---:|---|
| P1 | young_professional_technical | 15 | 100.00% | +17.50 | no |
| P2 | senior_academic_humanities | 15 | 100.00% | +17.50 | no |
| P3 | mid_career_clinician_direct | 15 | 100.00% | +17.50 | no |
| P4 | global_english_indirect | 15 | 0.00% | -82.50 | no |
| P5 | lay_casual | 15 | 100.00% | +17.50 | no |
| P6 | skeptical_analyst | 15 | 100.00% | +17.50 | no |
| P7 | anxious_first_timer | 15 | 60.00% | -22.50 | no |
| P8 | confident_veteran | 15 | 100.00% | +17.50 | no |

## Per-Tone Stratification

| Tone | label | n | rate | Δ pp | low_n |
|---|---|---:|---:|---:|---|
| T1 | neutral | 24 | 87.50% | +5.00 | no |
| T2 | anxious | 24 | 75.00% | -7.50 | no |
| T3 | frustrated | 24 | 75.00% | -7.50 | no |
| T4 | excited | 24 | 87.50% | +5.00 | no |
| T5 | reflective | 24 | 87.50% | +5.00 | no |

## Joint (Profile × Tone) Stratification

(40 cells; all `n=3`, hence all `low_n=yes`. P4×T*, P7×T2, P7×T3 show
`-82.50 pp`. Joint cells with `low_n=yes` do NOT contribute to the gate.)
```

Note that the joint cells in this synthetic example are all `low_n=yes`
because `per_cell=3 < MIN_GATE_N=5`. They're reported but not gated. This is
the intended behavior — joint cells need at least 5 records to participate
in the verdict, otherwise spurious 0/3 rates would dominate. To gate jointly,
the SDG run must produce ≥ 5 records per (profile, tone) cell — for the K=4
expansion factor in the spec's example invocation, that means ≥ ~2 base records
per cell, yielding 8 augmented variants per cell.

## 4. Integration plan — when does this gate fire?

### (a) Standalone CLI for ad-hoc retraining checks (default path)

```bash
python cas-native/evaluation/demographic_robustness_eval.py \
    --checkpoint cas-native/training/runs/<run_dir>/best_structured_token_model.pt \
    --eval-input cas-synthetic/data/level2_scaffold/level3_recoverable_eval_demographic_K4.jsonl \
    --tolerance-pp 10 \
    --out-json runs/<run_dir>/demographic_robustness_report.json \
    --out-markdown runs/<run_dir>/demographic_robustness_report.md \
    --device cuda
```

Exit 0 = PASS, exit 1 = FAIL. CI workflows can branch on the exit code; the
JSON report is the artifact for any post-mortem.

### (b) Post-training hook in `train_structured_prediction.py` (recommended after #68 lands)

Add an optional `--demographic-eval-input <jsonl>` flag to
`train_structured_prediction.py`. When present, after final eval the trainer:

1. Calls `run_demographic_robustness_eval(checkpoint_path, demographic_eval, tolerance_pp=...)`.
2. Writes `<run_dir>/demographic_robustness_report.{json,md}`.
3. Logs the `passed` verdict to `manifest.json` under a new `demographic_robustness_gate` key.
4. **Does NOT crash the training run on FAIL** — surfaces the verdict so the
   operator decides whether to keep or discard the checkpoint. Crashing the
   training run on a stratum gap would too easily mask checkpoints worth
   keeping for diagnostic comparison.

This keeps the gate cheap (single forward pass over the demographic eval
once at the end) and integrates naturally with the existing run_dir
convention.

### (c) Periodic CI cron (suggested, not blocking)

Once the demographic eval set is sized stably and a baseline checkpoint is
selected, schedule a nightly run on the latest `master` checkpoint with the
calibrated threshold (see Section 5). FAIL verdicts open a single proposal
PR for diagnostic follow-up.

## 5. Honest assessment — how robust is the 10 pp tolerance?

**Short answer: 10 pp is a placeholder, not a calibrated threshold. Real
checkpoints could trivially pass it (false negative — real demographic
drift exists but is < 10 pp) or trivially fail it (false positive — some
strata happen to be naturally noisier than 10 pp around the mean).**

### Why the threshold matters

The gate's tolerance is the only threshold separating "checkpoint OK" from
"checkpoint must not ship". 10 pp was the spec's default. It is a defensible
*starting* point but not a *finished* threshold for three reasons:

1. **Per-stratum rate variance scales as ~1/√n.** For a stratum with n = 100
   records and a true rate equal to the population mean, the empirical rate
   will fluctuate by ≈ ±5 pp at one σ and ≈ ±10 pp at two σ purely from
   sampling noise. Strata with smaller n (the joint cells, mostly) will
   exceed 10 pp by chance even when there is no real demographic effect.
   `MIN_GATE_N=5` softens this somewhat, but joint cells with `n` in the
   5–20 range will still trip false positives.

2. **A K=9 baseline checkpoint has not been measured against this gate yet.**
   We do not know what real demographic drift looks like for our model. It
   could be < 5 pp (10 pp is far too loose, a real failure would slip through)
   or > 20 pp (10 pp is far too tight, the gate fails on every checkpoint
   and gets ignored).

3. **The Task #68 SDG extension itself can introduce demographic drift
   artifacts.** If a profile (e.g., P5 lay_casual) happens to systematically
   produce shorter or syntactically different prompts, the model's recoverable
   slot extraction may regress against P5 not because of any real demographic
   robustness issue but because of an SDG artifact. The gate cannot
   distinguish these.

### Recommended calibration step (before the gate becomes load-bearing)

1. **Calibrate against the K=9 baseline.** Once Task #68 lands and produces
   `level3_recoverable_eval_demographic_K4.jsonl`, run the gate against the
   K=9 baseline checkpoint and the K9_DiagLoop checkpoint **without
   gating** — extract per-stratum rates and the worst-case observed Δ.

2. **Set `tolerance_pp = max(5, |worst observed Δ| + 5)`.**
   Adding a 5 pp pad above the worst observed real stratum gives a margin
   for noise without setting the bar so loose that the gate is uninformative.
   For example, if the worst K=9 stratum is P7 at -7.2 pp, set
   `tolerance_pp = 12.2 → 13` (round up). If the worst is -3 pp, set
   `tolerance_pp = 10`. If the worst is -22 pp, the model is already
   unacceptably non-robust on demographics and the threshold question is moot.

3. **Re-calibrate after every sustained model architecture change** (e.g.,
   adding a graph encoder, swapping embedding init, doubling d_model).
   The gate is an empirically calibrated artifact, not a fixed-axiom one.

4. **Treat low_n joint cells as advisory.** Even with `MIN_GATE_N=5`, joint
   strata with `n` in the 5–10 range are noisy. Consider raising
   `MIN_GATE_N` to 10 for joint cells specifically once SDG output sizes are
   known.

### What this gate is and is not

* **It IS:** a structural fairness check that catches gross demographic
  failure modes (e.g., the model collapses on global_english_indirect or
  on the anxious tonal register). The single-axis (per-profile and per-tone)
  stratification with sane `n` thresholds is reliable.

* **It IS NOT:** a statistical fairness audit. There is no FDR correction, no
  bootstrap CI, no comparison to a fairness baseline. Strata are compared
  to the *population mean*, not to *each other*, so a uniform regression
  across all profiles would not trip the gate. The tolerance is a single
  pre-committed threshold, not a confidence-interval test.

For a load-bearing fairness audit (e.g., for regulator-facing reports), this
gate would be one input among several, not the final word.

### Concrete recommendation

Before this gate fires in CI on any branch, run the calibration step (Step
2 above) and commit the calibrated `tolerance_pp` value to a config rather
than relying on the 10 pp default. Until then, the gate is suitable for
ad-hoc diagnostic use but should not block merges.

## 6. Code architecture notes

### Spec coupling to Task #68

The eval gate imports `PROFILES, TONES` from
`cas_synthetic.generator.demographic_tonal_axes` (Task #68's module). When
that import fails (Task #68 hasn't landed), it falls back to a hardcoded
`_FALLBACK_PROFILE_IDS` / `_FALLBACK_TONE_IDS` set that matches the spec
exactly: P1..P8 and T1..T5, with the canonical profile labels
(`young_professional_technical` etc.) and tone labels (`neutral`, `anxious`,
`frustrated`, `excited`, `reflective`).

The fallback path is what the tests exercise, so test results are
deterministic regardless of whether Task #68 is present in any given branch.
A `verdict.task_68_available` flag on the JSON report makes the binding
explicit so downstream consumers know whether they're seeing real Task #68
profile labels or the fallback ones.

### Predictor abstraction

The pure-logic core `stratify_and_gate(records, predictor, tolerance_pp)`
takes a predictor closure rather than a model. Tests inject mock predictors
that return hardcoded `{"all_heads_exact": bool}` per record, so the model
loading path is never exercised in tests.

The end-to-end function `run_demographic_robustness_eval` constructs a real
predictor via `_build_real_predictor` which mirrors the model construction
in `evaluate_structured_token_run.py`. Graph encoder + fusion modules are
imported defensively — they exist in the diagloop branches but not main.
For main-tree (K=9 baseline) checkpoints, the graph branch is skipped and
the model is built without them. For diagloop checkpoints loaded against
a graph-free model, partial state-dict load (`strict=False`) is used as a
fallback.

### Stratification edge cases (covered by tests)

* Empty stratum: skipped silently. No row in profile/tone tables.
* `n < MIN_GATE_N`: row appears with `low_n=True`, excluded from gate.
* Profile present, tone missing: contributes to profile and population only.
* Both missing: contributes to population mean only.
* Tonal_register T3 only failing: tone-axis stratification flags T3.
* Negative tolerance: `ValueError` at entry.

## 7. Done / Not done

**Done**

* `demographic_robustness_eval.py` (gate logic, model loader, markdown, CLI).
* Pytest suite (12 tests, 0.04 s wall-clock).
* Spec-conformant CLI (`--checkpoint`, `--eval-input`, `--tolerance-pp`,
  `--out-json`, `--out-markdown`, `--device`).
* Exit-code semantics (0 PASS, 1 FAIL) for CI integration.
* Stub fallback for Task #68 import absence.

**Not done (deferred)**

* End-to-end run against a real checkpoint. Blocked on Task #68 producing
  `level3_recoverable_eval_demographic_K4.jsonl`. Once Task #68 lands, a
  single-shot calibration run against the K=9 baseline + K9_DiagLoop
  checkpoint is the next step (see Section 5).
* Threshold calibration. Currently fixed at 10 pp default; should be
  empirically set per Section 5 recommendation.
* `train_structured_prediction.py` post-training hook. Spec calls for it as
  a follow-on; deferred until the gate has been calibrated against a real
  baseline.
* `MIN_GATE_N` separation between profile-axis and joint-axis strata. Joint
  cells are noisier; consider raising the joint threshold to 10 once SDG
  output sizes are known.

## 8. Constraints honored

* DID NOT execute the gate against any real checkpoint.
* DID NOT modify any data file.
* DID NOT depend on the Anthropic API.
* DID type-hint the public surface (dataclasses + function signatures).
* DID mirror the existing eval-script style (model construction parallel to
  `evaluate_structured_token_run.py`; same UTF-8 stdout init; same package
  alias bootstrapping).
* DID keep tests under 30 s (0.04 s actual).
