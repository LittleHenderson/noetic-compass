# Atlas Alpha Risk Language

Date: 2026-05-25
Purpose: keep stakeholder language direct, accurate, and hard to misread.

## Say This

```text
Atlas Viewer is live-verified on EleutherAI/pythia-160m.
```

Meaning: the realmode endpoint passes, the worker has Pythia weights loaded, fake mode is off, and the stream emits real-model token events.

```text
CAS beats baseline comparison methods on the validated jobs shown in the evidence panel.
```

Meaning: CAS has measured wins on internal readout, causal removal, output effect prediction, accept/suppress verification, and inversion proxy coverage.

```text
Blindspot confidence is cover-level evidence.
```

Meaning: the score belongs to a tested neuron cover, not to one single neuron with a human meaning.

```text
Unavailable means not enough evidence to score.
```

Meaning: do not fill the gap with a guess.

```text
The live alpha is Pythia-160M only.
```

Meaning: external models need adapters and validation before support is claimed.

## Do Not Say This

```text
CAS works on any AI model.
```

Problem: unvalidated external models are not supported.

```text
CAS proves mathematical certainty.
```

Problem: the evidence is empirical: probes, ablations, controls, output effects, verification, and replication.

```text
This neuron means consent.
```

Problem: the current blindspot confidence is cover-level, not single-neuron monosemantic proof.

```text
The 3D picture proves the claim.
```

Problem: the visualization helps humans inspect the trace. The claim is proven by benchmark artifacts and runtime proof fields.

```text
Live means the badge says live.
```

Problem: live means the realmode proof passes and the SSE stream emits real-model events.

## Fast Correction Phrases

If you accidentally overstate, correct immediately:

```text
Let me tighten that: the verified live path today is Pythia-160M, not every model.
```

```text
Let me be precise: that confidence is cover-level evidence, not a single-neuron meaning claim.
```

```text
Let me separate the visual from the evidence: the 3D view shows the trace, and the benchmark numbers support the product claim.
```

```text
Let me not overclaim: inversion is numeric proxy attribution here, not a full semantic theorem.
```

## Allowed Numbers

Use these numbers when asked what CAS has actually produced:

```text
Pythia-160M Foundation probe: 78.6%
Pythia-160M 40-element probe: 89.8%
OLMo-1B internal readout: 90.6%
Qwen2.5-1.5B internal readout: 82.0%
Text baseline gap: +28.9 to +39.7 percentage points
CAS subspace ablation: 78.6% down to 3.57%
Chance level: 3.57%, exact 1-in-28
Random same-rank ablations: mean disruption 0.000, max 0.000
Likelihood shifts: Pythia-160M +0.283, Pythia-1B +0.554, OLMo-1B +0.604, Qwen2.5-1.5B +0.796
Raw-CAS-symbol Qwen control: -0.0002
OLMo accepted accuracy: 98.16% at 71.73% coverage
Qwen accepted accuracy: 99.49% at 74.57% coverage
Inversion proxy measured rows: 4,704 / 4,704
```

## The Cleanest Stakeholder Answer

If someone asks, "Why should I believe CAS is real?", say:

> Because CAS has to beat comparison opponents. It beat text-only readout baselines, its signal collapsed when the CAS direction was ablated, random ablations did not cause the same collapse, CAS-conditioned choices predicted output shifts, and the verifier reached 98-99% accepted accuracy on rows it accepted. That is why this is not just a naming system.

