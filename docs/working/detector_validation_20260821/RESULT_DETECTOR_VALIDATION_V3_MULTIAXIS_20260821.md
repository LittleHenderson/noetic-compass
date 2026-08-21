# RESULT v3 — multi-axis detector validation on real activations — 2026-08-21

**Extends the result to a SECOND CAS involution pair. Same attested engine, real `pythia-160m` weights, local CPU, `$0`, no pod.** Raw: `detector_validation_v3_results.json` (sha256 `e47e1657…`). Script: `detector_validation_v3_multiaxis.py`.

## Two CAS axes, same pipeline, cross-topic

| axis | operationalisation | best | random ctrl | shuffle ctrl | verdict |
|---|---|---|---|---|---|
| **`^2`/`^3`** Positive/Negative | valence-bearing clauses | L0 D1 **acc 1.000 / AUC 1.000** | 0.625 | 0.500 | **GENERALIZES** |
| **`^8`/`^9`** Above-Cause/Below-Effect | cause-framed vs effect-framed clauses, same content | L8 D1 **acc 1.000 / AUC 1.000** | **0.500** | 0.500 | **GENERALIZES** |

Both: train on 8 topics, test on 4 unseen topics; two linear detectors; two null controls. All four preregistered predictions held for **both** axes.

**The `^8`/`^9` axis is the stronger of the two by control quality:** at its best layer the random-direction control sits at exact chance (0.500), so the detector's perfect score has an unambiguous 0.500 gap over a random line — no "classes just far apart" escape. `^8`/`^9` is also the harder, more abstract contrast (associative-cause language vs the landed-effect language), and the harness detector separates it and generalizes across content.

## Honest confound — flagged, not buried

The `^8`/`^9` sentences carry surface function-word signatures (cause clauses open with *because/since*; effect clauses with *so/therefore/and*). Cross-topic controls for **content** but not for these **function-word cues**, so part of what the detector reads may be the causal *framing markers*, not a deeper causal-role representation. That is still a real, generalizing linear signal for the `^8`/`^9` *framing* — but it is not evidence of causal *reasoning*. A future run with matched connectives (or connectives stripped) would separate framing from role. Recorded so the claim stays exactly as strong as the evidence.

## Claim states

- **Real:** 48 forward passes (24 per axis) on real weights through the attested engine; both detectors; both controls; every number.
- **Accepted:** none — research-grade, not a customer ACCEPT.
- **Open:** the function-word confound on `^8`/`^9`; more axes (`^5`/`^6`, `^0`/`^1`); bigger models (the A40's role); larger sets for significance.
- **Not licensed:** any product- or regulator-facing sentence citing these numbers.

## Bottom line

**The harness now has detector-validation data on two CAS involution pairs from real activations — `^2`/`^3` and `^8`/`^9` — both generalizing cross-topic, for `$0`.** This is the model-testing the project exists for, broadening beyond a single axis, and it runs entirely off the paid-launch critical path.
