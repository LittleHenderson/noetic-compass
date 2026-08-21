# PREREG — detector validation on a real model through the attested engine

**Written before any capture. This is the "real work" (goal step 6): one clean capture set, one control set, each detector tested on its own. Research-grade: `NOT_PACKET_ELIGIBLE`, `NOT_A_CUSTOMER_ACCEPT`. Runs locally on CPU, `$0`, no pod, no GPU, no guardian — deliberately decoupled from the Gate 4/5 launch, which by the owner's own words proves only plumbing.**

## Question

On real model activations, does a CAS-axis detector separate a labelled cognitive contrast **above matched controls** — and does that separation survive the two null controls that would expose a detector finding structure that is not there?

## The CAS axis under test

The `^2` Positive / `^3` Negative involution pair — affinity/attraction vs aversion/repulsion. Canonical, involution-paired, and it passes the Universal Applicability Test. Operationalised as valence-bearing sentences (the same axis the earlier CAV steering run moved), because valence is where `^2`/`^3` is least ambiguous in short English.

## Fixed design

- **Model:** `EleutherAI/pythia-160m` @ revision `50f5173d932e8e61f858120bcb800b97af589f46`, loaded through the **real** `load_open_weight_runtime` with full attestation (the reserialized fp16 snapshot `d5861d32…`, byte-provenance from the pinned original). `device=cpu`, `seed=0`, greedy, `max_new_tokens=1`.
- **Capture point:** residual stream at **layer 6** of 12, step 0. Fixed in advance.
- **Clean capture set:** **20 `^2` Positive** + **20 `^3` Negative** sentences, parallel in structure, fixed in the script before any run.
- **Split:** first 10 of each class = **train**, last 10 of each class = **test**. Fixed by index, no shuffling of the split.

## Detectors (each tested on its own)

1. **D1 — Mean-difference (CAS drive-direction) detector.** Direction `w = μ⁺_train − μ⁻_train`; score `= x·ŵ`; threshold at the midpoint of the two train-class score means; predict `^2` if above.
2. **D2 — Fisher LDA detector.** Same but whitened by the pooled within-class covariance (ridge `1e-2·tr(Σ)/d`), the classic optimal linear detector. Pure numpy.

Both are frozen from **train only** and evaluated on the **held-out test** set.

## Metrics (exact)

- **Test accuracy** (20 held-out items, 10 per class).
- **AUC** of the projection score vs the true label (Mann–Whitney form, exact).
- **Separation margin** = (mean test⁺ score − mean test⁻ score) / pooled test score SD.

## Controls (the honesty layer)

- **C1 — Label-shuffle control.** Re-evaluate each detector after a fixed-seed permutation of the **test** labels. A real detector's accuracy must **collapse toward 0.5**; if shuffled accuracy stays high, the detector is reading something other than the label.
- **C2 — Random-direction control.** Replace `ŵ` with a fixed-seed random unit vector (`numpy` seed `1729`) of the same dimension; same threshold procedure on train, same test evaluation. Real geometric structure must beat this.

## Predictions, fixed now

- **P1 (signal):** at least one detector reaches **test accuracy ≥ 0.70** on the 20 held-out items.
- **P2 (beats random direction):** that detector's test accuracy exceeds the C2 random-direction accuracy by **≥ 0.15**.
- **P3 (label-shuffle collapses):** under C1 the same detector's accuracy falls to **≤ 0.60**.
- **P4 (AUC):** that detector's test AUC **≥ 0.70**.

## Decision rule

All four hold → **`DETECTOR_VALIDATED_ON_REAL_ACTIVATIONS` (research-grade, n=40, one model, one layer, one seed — no significance claim).** P1 fails → **`NULL` on this model/layer** (recorded with the same care as a positive). P1 holds but a control fails → **`CONFOUNDED`, investigate before any interpretation.** Every number reported exactly; a null is a result.

## What this is and is not

- **Is:** the first end-to-end detector-validation on real activations captured through the attested engine — capture set, control set, detector, on real weights.
- **Is not:** a customer ACCEPT, a Gate-5 pass, or a claim about larger models. pythia-160m is tiny; a null here bounds the method, not the harness.
- The A40 pod would let this same procedure run on a larger model. It is **not** a prerequisite for producing detector-validation data, which is what this run demonstrates.
