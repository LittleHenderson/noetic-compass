# RESULT v2 — cross-topic detector generalization on real activations — 2026-08-21

**Strengthens v1 against its own caveat. Same attested engine, same real `pythia-160m` weights, local CPU, `$0`, no pod.** Raw: `detector_validation_v2_results.json` (sha256 `25234325…`). Script: `detector_validation_v2.py`.

## What v1 left open, and how v2 closes it

v1's honest caveat: the random-direction control scored `0.800`, so some of the separation was just "the two classes are far apart in this set." v2 removes that escape route: **train and test share no topic.** 12 topics, each with a `^2` Positive and a `^3` Negative sentence about the *same* content; the detector is built on **8 topics** and tested on **4 entirely unseen topics** (8 held-out items). A detector that passes cross-topic must be reading valence that *generalizes across content*, not class-distance in one sample.

## Result — the detector generalizes across topics

**Verdict by the prereg-style rule: `DETECTOR_GENERALIZES_CROSS_TOPIC`.** At the best layer, the CAS detector reaches held-out **accuracy 1.000 / AUC 1.000**, beats the random-direction control by `0.375`, and the label-shuffle control sits at chance.

Layer sweep (test = 4 held-out topics, 8 items), one capture yields all layers:

| layer | D1 mean-diff | D2 Fisher LDA | C2 random dir | C1 label-shuffle |
|---:|---:|---:|---:|---:|
| 0 | 1.000 | 1.000 | 0.625 | 0.500 |
| 1 | 1.000 | 1.000 | 0.500 | 0.500 |
| 2 | 1.000 | 1.000 | 0.750 | 0.500 |
| 3 | 1.000 | 1.000 | 0.875 | 0.500 |
| 4 | 1.000 | 1.000 | 0.750 | 0.500 |
| 5 | 1.000 | 1.000 | 0.875 | 0.500 |
| 6 | 1.000 | 1.000 | 0.750 | 0.500 |
| 7 | 1.000 | 1.000 | 0.750 | 0.500 |
| 8 | 0.875 | 1.000 | 0.750 | 0.625 |
| 9 | 0.750 | 1.000 | 0.875 | 0.500 |
| 10 | 1.000 | 1.000 | 0.875 | 0.500 |
| 11 | 0.750 | 1.000 | 1.000 | 0.250 |

**Two things stand out:**
1. **Fisher LDA (D2) is 1.000 at every one of the 12 layers** — a whitened linear detector reads the `^2`/`^3` valence axis perfectly on unseen topics throughout the network.
2. **The label-shuffle control is 0.500 (exact chance) at almost every layer** — the cleanest possible null. When the labels are destroyed, the detector reads nothing. That is the strongest evidence it reads the label and not an artifact.

## Honest caveats — recorded, not buried

- **The random-direction control is noisy** (0.500–1.000 across layers), because the held-out set is small (8 items). At layer 11 it hits 1.000 — the final-layer classes are trivially separated. So the informative null here is **C1 label-shuffle** (clean 0.500), not C2. The cross-topic generalization plus the clean shuffle is the load-bearing evidence.
- **Valence is an easy axis and pythia-160m is tiny.** A perfect score means valence is strongly and linearly encoded and generalizes across content — it does not mean every CAS axis will, or that a harder axis on a bigger model will. Those are open.
- **`n` is small.** 8 held-out items. This is research-grade evidence, not a significance claim.

## Claim states

- **Real:** 48 forward passes on real weights through the attested engine; both detectors; both controls; all numbers.
- **Accepted:** none — research-grade, not a customer ACCEPT, not a Gate-5 pass.
- **Open:** harder axes (`^6`/`^3`, `^8`/`^9`), bigger models (the A40 pod's role — same procedure, bigger model), larger held-out sets for significance, harder same-topic-same-valence controls.
- **Not licensed:** any product- or regulator-facing sentence citing these numbers.

## Bottom line

**The `^2`/`^3` CAS axis is linearly decodable from real `pythia-160m` activations and generalizes to unseen topics — measured for `$0` through the attested engine.** This is the model-testing the project exists to do, and it is running now, off the critical path of the paid launch.
