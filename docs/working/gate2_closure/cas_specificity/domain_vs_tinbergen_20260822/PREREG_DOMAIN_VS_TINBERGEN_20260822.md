# PREREG — Domain axis vs matched non-CAS abstractness taxonomy (Tinbergen) — 2026-08-22

**Status: PRE-REGISTERED BEFORE CAPTURE.** This document pins the design. The run may not begin before this file exists, and no criterion may be edited after the run starts.

---

## 1. Purpose

Execute the single most available lever named in spec sheet frontier #1 (10.1):

> "an MTC-style matched non-CAS four-level abstractness taxonomy run against the domain axis on the same fixtures. Domain precedence is the last surviving CAS relation; if a generic abstractness taxonomy does not do worse, that relation also folds into the generic explanation. The machinery exists (`arm_E_non_tks_ontology.json`). It has not been run."

This run uses Arm E's externally-authored four-level axis — **Tinbergen's four questions** (mechanism / ontogeny / function / phylogeny), the canonical abstractness ladder of ethology, as encoded in `docs/working/gate2_closure/item4_arms/arm_E_non_tks_ontology.json` — as the matched non-CAS taxonomy, run against the CAS Domain axis on the SAME fixtures and the SAME captured activations. Cost: **$0** (pythia-160m, local CPU, attested engine).

## 2. Fixture — verbatim, machine-extracted

The domain fixture from `detector_validation_v4_domain.py` (successor branch, file at commit `e889d190`): **8 topics × 4 domains = 32 sentences**, each topic holding one P / C / E / O framing of the same subject. Extraction is by AST (`ast.literal_eval` of the `TOPICS` assignment), so the fixture is byte-identical to v4's, not a copy-typed reproduction.

- canonical fixture JSON: `fixture_domain_v4.json` (written by the runner before capture)
- **fixture sha256:** `0fb11c26a17203edfa8d3bb3a8017e80ea1707c99103612151ca0e7454ce0d7b`
- train topics (6): cooking, medicine, finance, law, sports, music
- test topics (2, held out, unseen at train time): gardening, travel
- test items: 8; 4-way balanced chance: **0.25**

## 3. Design

### 3.1 Model and capture (identical for both arms)

- model: `pythia-160m-reserialized`, revision `d5861d3237c5f8e952b4ebf05179f3bc50d479186fbe96845d22660d96c50d97`, local snapshot store (5 files, engine-attested on load)
- engine: `load_open_weight_runtime` + `capture_greedy_trajectory`, scenario_id `dom4tin`, `max_new_tokens=1`, `seed=0`, device `cpu`, dtype `auto`
- features: last-token `residual_states[0]` at **every** layer (12 layers × 768), float64 — the same capture used by v4
- one capture pass total; **both arms probe the identical vectors**

### 3.2 Classifier (identical for both arms)

Nearest-centroid, 4-way, train 6 topics / test 2 topics (v4's exact split), reported at every layer, with:
- layer-mean accuracy (the verdict statistic, per the W-series convention)
- best-layer accuracy (reported; not the verdict statistic)
- shuffled-test-label null, 100 seeds (base 20260822)
- random-4-dim-subspace control per layer (seed 1729 + layer, as v4)

### 3.3 Bijections — FROZEN BEFORE CAPTURE

**PRIMARY (abstractness-aligned).** CAS Domain Descent P ≻ C ≻ E ≻ O (abstract → concrete) maps onto Tinbergen ordered ultimate → proximate:

- P (Principled) → phylogeny / evolutionary history
- C (Cognitive) → function / survival value
- E (Evaluative) → ontogeny / development
- O (Operational) → mechanism / proximate causation

Rationale: this is the severe form of the frontier's question. If activations encode only an abstract-to-concrete gradient, the aligned Tinbergen labels name the same rungs and should recover at least as well as CAS labels; a CAS win then cannot be a relabeling artifact.

**SENSITIVITY (positional, Arm E's own convention: first-listed → first-listed).** P → mechanism, C → ontogeny, E → function, O → phylogeny. Reported for completeness; no verdict rests on it.

Both bijections are written into the runner before capture and never searched over.

## 4. Pre-registered criteria and verdict

- **C1 (CAS sanity):** CAS best-layer ≥ **0.50** AND CAS layer-mean ≥ **0.40** (reproduces v4's cross-topic domain decodability).
- **C2 (TIN sanity):** TINBERGEN-primary layer-mean ≥ **0.40** — the comparison must be between two real signals, not signal vs noise.
- **C3 (THE COMPARISON):** CAS layer-mean − TINBERGEN-primary layer-mean ≥ **+0.10**.
- **C4 (significance):** two-sided exact McNemar p ≤ **0.05** on the 8 test items at the best CAS layer, pairing each item's CAS-arm correctness against its TIN-arm correctness.

**Verdict:**
- `DOMAIN_BEATS_MATCHED_ABSTRACTNESS` iff **C1 ∧ C2 ∧ C3 ∧ C4** — the first clean matched-comparator WIN for the CAS domain axis (frontier #1 lever returns positive).
- Otherwise `DOMAIN_DOES_NOT_BEAT_GENERIC_ABSTRACTNESS` — reported with the exact Δ and p either way. That outcome sharpens the negative: the last surviving CAS relation folds into the generic abstractness explanation. **Both outcomes are results; neither is hidden.**

## 5. What a WIN would and would NOT license

A WIN licenses exactly: *"on the same fixtures and the same captured activations, CAS domain labels are more linearly recoverable than a matched four-level abstractness taxonomy (Tinbergen), at the pre-registered margin."*

A WIN does **not** license: CAS-specificity generally (one arm, one model point, 160m, assistant-assigned bijection); any claim about the Schwartz × Tinbergen 40-cell ontology as a whole (only the Tinbergen axis is used here); any claim about domain **precedence** geometry (this run probes label recoverability, not the P≻C≻E≻O order fit); any claim beyond pythia-160m.

Authorship note (inherited from `arm_E_non_tks_ontology.json`): Schwartz's values and Tinbergen's questions are externally published; the domain→Tinbergen bijection and this experiment's label assignment are OURS, fixed before capture.

## 6. Pinned hashes

- prereg (this file): computed after writing, recorded in the result JSON
- runner: `75cc73d9301ad23dbd058be2cecec37ef9a9cbb85794cc367c652d626cabf043`
- fixture: `0fb11c26a17203edfa8d3bb3a8017e80ea1707c99103612151ca0e7454ce0d7b`

## 7. Stop rules

- Engine fails attestation on load → **abort**, report `NO_RUN`, touch nothing.
- Fixture extraction deviates from 8 topics / 32 rows → **abort**.
- Any capture exception → **abort**, report `NO_RUN`, no partial results are promoted.
