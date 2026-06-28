# CAS Harness AI2 One-Pager

**Moniker:** Turn your black box into a glass house.

**One-sentence claim:** CAS Harness is an open-weight AI audit system that reads model-internal CAS structure, tests whether that structure is causally load-bearing, and returns an ACCEPT / SUPPRESS / FLAG verdict with an Evidence Packet.

## What CAS Harness Does

1. Connect an open-weight model.
2. Capture hidden states across layers.
3. Probe for CAS taxonomies that were defined before the model run.
4. Test whether those signals survive controls and collapse under targeted removal.
5. Measure whether CAS-conditioned interventions move model output in the predicted direction.
6. Return a verdict with confidence, proof chips, and a trace-id-keyed Evidence Packet.

The product is not just a visualization layer. Atlas Viewer is the cockpit. CAS Harness is the audit engine and evidence protocol underneath it.

## Core Mechanism: Eta To Epsilon Bridge

**Eta:** read CAS structure from the foreign model's hidden states.

**Epsilon:** realize that detected CAS structure as readable English prefix tokens.

**Bridge:** run the model once, read the CAS state, prepend the readable CAS realization, then run the model again and measure whether the likelihood shifts in the CAS-predicted direction.

This matters because ablation-based generation steering repeatedly failed. Prefix realization worked. The reason is architectural: later transformer positions can attend to prefix positions by construction. CAS uses that property instead of pretending that every hidden-state ablation should directly steer generation.

## What Is Already Closed

| Evidence tier | Result | Why it matters |
|---|---:|---|
| 28 Foundations readout | Pythia-160M: 78.6%, +28.9 points over text baseline | CAS reads a model-internal Foundation structure above surface-text guessing. |
| 40 Elements readout | Pythia-160M: 89.8%, +39.7 points over text baseline | The strongest original readout used the TKS 40 Element grid. |
| Causal subspace ablation | 28 Foundations: 78.6% -> 3.57% exact 1-in-28 chance | Removing the CAS subspace kills the signal. |
| Random controls | Same-rank random ablations: mean disruption 0.000, max 0.000 | The collapse is not explained by generic damage. |
| Likelihood bridge | Pythia-160M +0.283, Pythia-1B +0.554, OLMo-1B +0.604, Qwen2.5-1.5B +0.796 | CAS conditioning changes output likelihood in the predicted direction across model families. |
| Raw-symbol control | Qwen raw-CAS-symbol control: -0.0002 | The effect requires readable epsilon realization, not decorative CAS symbols. |
| Verification Stack | OLMo: 98.16% accepted accuracy at 71.73% coverage; Qwen: 99.49% at 74.57% coverage | CAS separates high-confidence accepted rows from suppress / review rows. |
| Weight geometry | Pythia-2.8B: 2.83x random alignment, p = 0.0099 | Static output-weight evidence independently agrees with the dynamic probe story. |

## Fresh 20B Status

**Model:** GPT-NeoX-20B, real open weights, 44 transformer layers.

**What passed:**

| Run | Dataset | Readout | Controls | Status |
|---|---:|---:|---:|---|
| Compact-gloss TKS40 v0 | 400 rows, 40 classes | Hidden signal present, but not claim-bearing | Text-only baseline reached 100.00% | Blocked for CAS-beats-text claims |
| Original Stage 9 40E | 8,320 rows, 40 classes, 208/class | 95.625% at layer 2 | 49.241% confirmed text / 50.000% text-hash / 2.619% shuffled / 2.500% majority | Claim-bearing readout pass |
| Exact original Stage 7 Foundation-28 | 4,368 rows, 156 per class | 51.04% initial; 86.8622% under corrected balanced-logistic bridge readout | 3.57% chance / 3.40% shuffled / 42.28% text | Foundation bridge path pass |

**Plain English:** the compact-gloss TKS40 v0 set taught us what not to claim: if text alone gets 100%, it is an answer-key fixture, not proof that CAS beats surface text. The corrected original Stage 9 40E run fixes that: GPT-NeoX-20B hidden states score 95.625% while text-only stays near 49-50% on the same fixed split.

**Fresh behavioral bridge result:** the exact Stage 7 eta-to-epsilon likelihood bridge was run on GPT-NeoX-20B with 112 same-register drive-cycle cases. Under the original balanced-logistic readout methodology, the probe-predicted readable epsilon loop passes: `+0.596413` mean likelihood-margin delta, `90/112` positive rows, sign-test p = `3e-11`, and `+1.244917` separation from the wrong readable partner. Gold/readable epsilon prefixes remain strong: `+0.660065`, `93/112` positive rows. Raw CAS-symbol prefixes stay near zero (`+0.002524` probe raw, `+0.002186` gold raw), confirming the load-bearing route is readable epsilon realization, not decorative symbols.

**Methodology correction:** the earlier weak bridge used nearest-centroid readout, which was not the original closure probe family. Replacing it with sklearn `LogisticRegression(C=0.1, class_weight="balanced")` after `StandardScaler` raises heldout Foundation readout to `86.8622%`, selected bridge-row Foundation accuracy to `85.7143%`, and selected Drive accuracy to `93.75%`.

**Plain English:** the 20B bridge works when we use the original probe method. The failure was not the TKS definitions and not the eta-to-epsilon mechanism. It was a readout implementation mismatch: centroid was too weak; balanced logistic is the correct Stage 7 readout.

**40E baseline rule:** every 40-Element scenario library must earn its own text-only baseline before it can support a CAS-beats-text claim. The method label for the corrected 20B run is `S9-40E-ORIGINAL-BASELINE-READOUT`: original Stage 9 role-bound/counterfactual fixture, fixed historical split, zero train/test group overlap, hidden 95.625%, confirmed text 49.241%, text-hash 50.000%, shuffled-label mean 2.619%.

**Fresh trace diagnostic result:** the exact Stage 7 Foundation-28 trace also passes the lacunarity/fractal preflight on GPT-NeoX-20B. At bridge layer 40, heldout Foundation accuracy is `86.8622%`, Foundation lacunarity is `0.006715` against a pass threshold of `<= 0.05`, drive lacunarity is `0.002752`, register lacunarity is `0.001283`, and the layer-trace preflight class is `Amplifying`. For comparison, the original Pythia-160M Foundation lacunarity was `0.021`, so the 20B Foundation trace is cleaner on this gate.

**What is not closed yet on 20B:** this is now a probe-predicted behavioral likelihood-bridge pass plus a trace-diagnostic pass, but not yet a full CAS Harness ACCEPT/SUPPRESS verdict. The next gate is a fresh Evidence Packet verdict and final verifier merge. The fractal result above is a numeric layer-trace proxy, not yet the discrete `cas-engine` orbit classifier.

## Why This Is Different From Existing Interpretability Tools

Neuronpedia, TransformerLens, nnsight, and attribution-graph tools are useful. CAS Harness is aiming at a different product line:

- It turns interpretation into an audit verdict: ACCEPT, SUPPRESS, or FLAG.
- It binds every verdict to an Evidence Packet instead of leaving it as a notebook result.
- It tests readout, causal removal, matched controls, output prediction, and replication as one protocol.
- It uses source-defined TKS/CAS taxonomies instead of post-hoc feature naming.
- It is being extended from small models to 20B+ open-weight models with the same methodology.

## What Would Prove Universality

CAS universality is not proven by a pretty cockpit or by one successful probe. The standard is:

1. Same source-derived TKS/CAS taxonomies.
2. Same hidden-state readout protocol.
3. Same matched controls.
4. Same targeted ablation / cover-removal test.
5. Same eta-to-epsilon likelihood bridge.
6. Same Evidence Packet format.
7. Replication across model families and sizes, including 20B, 100B, and 300B open-weight systems.

## What We Want AI2 To React To

1. Is the corrected TKS 28 Foundation / 40 Element methodology scientifically credible?
2. What would AI2 consider the cleanest 20B closure threshold?
3. What model family should be the next serious replication target after GPT-NeoX-20B?
4. What infrastructure would make 100B / 300B open-weight CAS Harness audits practical?
5. What Evidence Packet fields would senior researchers need before treating a CAS verdict as audit-grade?

## Honest Boundary

CAS Harness has strong closed evidence on Pythia, OLMo, and Qwen, plus fresh 20B evidence: exact Stage 7 Foundation readout, targeted ablation, eta-to-epsilon behavioral bridge, and lacunarity/fractal trace preflight. It is not yet a completed 300B enterprise audit product. The next scientific step is to merge the 20B chain into a full Evidence Packet and verifier verdict.
