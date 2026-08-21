# RESULT — detector validation on real activations — 2026-08-21

**This is the model-testing data. Goal step 6, run through the attested engine on real `pythia-160m` weights, local CPU, `$0`, no pod, no GPU, no guardian.** Preregistered: `PREREG_DETECTOR_VALIDATION.md`. Raw numbers: `detector_validation_results.json` (sha256 `376c34d9…`). Script: `detector_validation.py`.

## The headline

**Verdict by the prereg's own rule: `DETECTOR_VALIDATED_ON_REAL_ACTIVATIONS`.** A CAS-axis detector separated the `^2` Positive / `^3` Negative contrast on held-out real activations, beat both null controls, and all four preregistered predictions held. This is research-grade (`n=40`, one model, one layer, one seed) — not a customer ACCEPT and not a Gate-5 pass.

## What ran

- 40 real forward passes through `load_open_weight_runtime` with full attestation (weight-value manifest `AD7CB93367AB338244B79D56A16EF3AF620CD624EE237EAB03D57CE940D2B7BB`, 12 layers, hidden 768).
- Clean capture set: **20 `^2` Positive** (affinity/attraction) + **20 `^3` Negative** (aversion/repulsion) sentences, residual stream captured at **layer 6, step 0**.
- Fixed split: 10+10 train, 10+10 held-out test.

## Detectors, each on its own (held-out test, 20 items)

| detector | accuracy | AUC | margin (SD) |
|---|---:|---:|---:|
| **D1 — mean-difference (CAS drive-direction)** | **1.000** | **1.000** | **+5.488** |
| **D2 — Fisher LDA** | **1.000** | **1.000** | **+6.206** |

Both linear detectors, frozen from train only, separated the held-out set perfectly.

## Controls — the honesty layer

| control | result | reading |
|---|---|---|
| **C1 — label shuffle** | acc **0.300** (both detectors) | **Collapsed** below chance. The detector reads the label, not an artifact — if it were fitting noise, shuffled accuracy would stay high. |
| **C2 — random direction** (same-norm unit vector) | acc **0.800**, AUC 0.900 | The CAS direction beats it (`1.000 − 0.800 = 0.200 ≥ 0.15`), but see the caveat. |

## Predictions — all four held

- **P1 (acc ≥ 0.70):** PASS — 1.000.
- **P2 (beats random direction by ≥ 0.15):** PASS — 0.200 margin.
- **P3 (label-shuffle collapses ≤ 0.60):** PASS — 0.300.
- **P4 (AUC ≥ 0.70):** PASS — 1.000.

## Honest caveat — do not oversell this

**The random-direction control scored 0.800, which is high.** On this small held-out set (`n=20`), the two valence classes are so far apart in activation space that even a random projection separates them fairly well. So the *dominant* finding is that valence is strongly linearly encoded at layer 6 — the CAS drive-direction detector is the *best* reader of it (perfect vs 0.800), but the gap over a random line is real yet modest. A larger held-out set and a harder control (e.g. a within-topic contrast) would tighten this. This is why the verdict is `research-grade`, not `ACCEPT`.

## Claim states

- **Real:** the 40 captures, both detectors, all controls, every number above — measured on real weights through the attested engine (`is_real_model` path).
- **Simulated:** none.
- **Accepted:** none — explicitly not a customer ACCEPT.
- **Open:** larger models (this is where the A40 pod would help — same procedure, bigger model), more items for significance, harder controls, more CAS axes than `^2`/`^3`, more layers than 6.
- **Not licensed:** any product- or regulator-facing sentence citing these numbers.

## What this proves about the harness — and about the launch

**The harness can produce detector-validation data on real models right now, with none of the Gate 4/5 cloud machinery.** The capture set, control set, and per-detector test all ran locally through the attested engine. The A40 pod is a way to run this *same* procedure on a *bigger* model; it is not a prerequisite for the data itself. The model-testing the whole project is for has started here, on real weights, for `$0`.

**No pod created. No GPU used. The A40/Gate-5 canary remains `NOT RUN` — and is now visibly not on the critical path to the science.**
