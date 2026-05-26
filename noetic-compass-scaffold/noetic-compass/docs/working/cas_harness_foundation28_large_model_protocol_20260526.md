# CAS Harness Foundation-28 Large-Model Replication Protocol

Date: 2026-05-26

Status: concrete protocol draft for the 20B/100B/300B open-weight path.

Companion axis: 40 Elements (`10 Noetics/operators x 4 Domains`) is the strongest original Pythia readout axis. This document focuses on Foundation-28 because that was the taxonomy drift risk, but large-model replication should test both Foundation-28 and 40 Elements.

Important source-definition rule: the original successful methodology used the TKS definition surfaces, not generic CAS paraphrases. Foundation-28 must preserve the legacy `1a..7d -> F1|T..F7|E` mapping. 40 Elements must preserve the legacy `A1..D10 -> operator x domain` mapping. This is not optional. The first Foundation-28 v0 library used compact source-derived Stage-7/TKS28 glosses and the first 40-Element check only derived `operator x domain` labels from an existing dataset. Treat those as engineering/probe-path runs. The final headline methodology needs source-faithful scenario libraries grounded in the original TKS definitions or in the original Stage 7/Stage 9 fixture builders.

## Purpose

This protocol prevents axis drift in large-model CAS Harness evaluations.

The original Pythia headline was not drive-only, domain-only, or operator-only. The strongest closed result was the **28-Foundation axis**, with downstream causal tests and likelihood-tier evidence.

Large-model replication must therefore test Foundation-28 directly before making claims against the original Pythia result.

## Canonical Axis

Foundation-28 means:

```text
7 Drives x 4 Registers = 28 classes
```

Examples:

```text
F1T, F1A, F1f, F1E
F2T, F2A, F2f, F2E
...
F7T, F7A, F7f, F7E
```

The Stage 27 smoke artifacts use same-drive/different-register contrasts and labels such as `F1T`, `F1A`, `F1f`, and `F1E`. If a document says "Drive x Domain" for this result, treat that as naming drift unless the labels are explicitly `P/C/E/O`. Do not confuse the 4-register Foundation axis (`T/A/f/E`) with the separate 4-domain axis (`P/C/E/O`).

## Original Closed Evidence To Replicate

The replication target is the original Pythia evidence chain:

| Gate | Original Pythia result | Meaning |
| --- | --- | --- |
| Foundation readout | Pythia-160M `78.6%`, `+28.9 pp`, p about `1e-95` | The model hidden states carried Foundation-28 structure. |
| Foundation ablation | `78.6% -> 3.57%` | Removing the CAS Foundation subspace collapsed readout to exact `1/28` chance. |
| Random controls | Same-rank random ablations clean/null | The collapse was not caused by arbitrary damage. |
| Lacunarity | Foundation `0.021` | Foundation was much cleaner than the noisier Noetic axis. |
| Stage 27F covers | Targeted drop beat random `28/28`, p `3.72529e-09` | Class-specific neuron covers mattered for the readout. |
| Stage 27G readout steering | Amplification and polarity flip beat random `28/28` | Cover interventions controlled the trained Foundation readout. |
| Eta-to-epsilon likelihood bridge | Pythia-160M `+0.283`, Pythia-1B `+0.554` | Probe-predicted readable prefixes moved next-token likelihood in the predicted direction. |

The original Pythia notes also record the 40-Element readout:

| Gate | Original Pythia result | Meaning |
| --- | --- | --- |
| 40 Elements readout | Pythia-160M `89.8%`, `+39.7 pp`, McNemar p at machine precision | The `10 Noetics/operators x 4 Domains` cross-product was the strongest readout result. |
| 40 Elements ablation | Listed as pending Stage 9.1 in the 2026-05-17 spec | Do not claim a closed 40-Element ablation chain unless a later artifact is cited. |

## Explicit Non-Claims

The following were not the original closed headline and must not be used as substitutes:

- Drive-only readout.
- Domain-only readout.
- Operator-only readout.
- Drive-only forward-pass steering.
- Free-form generation steering.
- Any run that lacks Foundation labels.

Also do not present an imbalanced 40-Element relabel run as the clean headline comparator. It can be an early signal test, but the rigorous comparator needs a balanced 40-class library.

The original notes also record null/bounded findings:

- Stage 6.6 noetic generation steering: NULL.
- Stage 7.3 drive-subspace generation steering: NULL.
- Stage 7.LA late-layer additive steering: NULL.
- Stage 27H / 27I prefix-plus-neuron steering: diagnostic/null at Pythia-160M scale.

These nulls are not failures of the Foundation-28 readout/ablation claim. They bound what can be said about visible generation steering.

## Required Large-Model Sequence

### Gate 0: Dataset Validity

Build or recover a balanced Foundation-28 scenario set.

Minimum requirements:

- Every row has a drive label: `F1..F7`.
- Every row has a register label: `T`, `A`, `f`, or `E`.
- Every row has a derived Foundation label such as `F1T` or machine-safe equivalent `F1|T`.
- Prompt semantics are grounded in the TKS Foundation definition for that `drive x register` cell, not only in generic CAS drive/register wording.
- Metadata preserves the legacy TKS code (`1a..7d`) for auditability.
- All 28 classes are represented.
- Class counts are reported.
- Train/eval split is disjoint.
- Prompt text may use canonical CAS colloquialisms. These are approved English aliases, not contamination.

Fail condition:

- If the captured metadata lacks register/foundation labels, the run is not a Foundation-28 replication.

### Gate 1: Real Activation Capture

Run the open-weight model and capture hidden states for all selected layers.

Required output:

- model id and revision
- architecture
- parameter count
- dtype
- device map / worker assignment
- layers captured
- feature tensor shape
- scenario path hash
- label distribution

Fail condition:

- No fabricated `cas_axis_readout`, `blindspot_overlay`, or verdict fields. Missing downstream fields must remain missing until computed.

### Gate 2: Foundation-28 Readout

Train/evaluate Foundation-28 readout from hidden states.

Required comparisons:

- hidden-state readout accuracy
- majority-class control
- shuffled-label control
- canonical-English surface baseline
- best layer and per-layer table
- per-class accuracy

Interpretation:

- Hidden-state readout beating weak controls means the model carries recoverable Foundation structure.
- Strong surface baseline is not automatically a flaw, because the colloquialisms are canonical English aliases.
- The stronger claim requires Gate 3.

### Gate 3: Foundation Causal Ablation

Run ablation/intervention against the Foundation readout.

Required comparisons:

- true Foundation cover/subspace ablation
- same-size random control
- wrong-Foundation control
- clean readout accuracy/margin
- ablated readout accuracy/margin
- drop versus random
- sign test or matched statistical test

Pass target:

- The true Foundation intervention damages the Foundation readout materially more than matched random/wrong-label controls.

Strong Pythia reference:

- Pythia-160M collapsed from `78.6%` to exact `3.57%` chance.

### Gate 4: Foundation Cover Discovery

Build class-specific covers for the 28 Foundation labels.

Required shape:

```json
{
  "covers": {
    "foundation": {
      "F1|T": {"layer": 5, "neuron_cover": ["L5N2346"]},
      "F1|A": {"layer": 5, "neuron_cover": ["L5N2648"]}
    }
  }
}
```

Required controls:

- same-drive/different-register pair checks
- random same-size covers
- patch-back sanity when applicable

Pass target:

- Targeted cover effects beat random controls across Foundation classes.

### Gate 5: Foundation Output / Likelihood Bridge

Only after Gates 2-4 pass, run the output-side bridge.

Required comparisons:

- clean likelihood of true Foundation verbalizer
- target-cover intervention likelihood
- wrong-Foundation intervention likelihood
- random-cover intervention likelihood
- multiple verbalizers per Foundation class when possible

Interpretation:

- This is likelihood/output evidence.
- It is not a final CAS Harness ACCEPT/SUPPRESS verdict unless merged with verifier outputs and an Evidence Packet.

### Gate 6: Evidence Packet Merge

Merge the run into a real Evidence Packet only after the chain above produces artifacts.

Required packet fields:

- model proof
- Foundation readout proof
- causal ablation proof
- control proof
- output/likelihood proof
- packet hash/provenance
- confidence and coverage
- explicit caveats

Fail condition:

- No final ACCEPT/SUPPRESS for large-model universality without packet-backed proof.

## Current 20B Status Under This Protocol

The current GPT-NeoX-20B evidence is **not yet** a final source-faithful Foundation-28 or 40-Element replication.

What exists:

- Real GPT-NeoX-20B activation capture.
- Domain/drive/operator readouts.
- Activation-level candidate cover ablations for domain/drive/operator.
- A drive-only forward-pass pilot that returned null/negative against matched random controls.
- A balanced Foundation-28 v0 engineering run with real hidden-state readout and matched activation ablation.
- Worker-side builders that preserve legacy TKS mappings for Foundation-28 (`1a..7d`) and 40 Elements (`A1..D10`).

What is missing:

- Source-faithful rerun from the original Stage 7/Stage 9 definition surfaces.
- Balanced 40-Element scenario capture.
- 40-Element hidden-state readout on that balanced source library.
- Foundation-28 and 40-Element cover maps from the source-faithful libraries.
- Matched ablation on the source-faithful libraries.
- Foundation-level likelihood bridge.
- Fresh full Evidence Packet.

The earlier 400-row GPT-NeoX-20B dataset can derive a 40-Element label from existing `operator x domain` labels, but it is imbalanced and has only 39 populated classes. That run is useful as a zero-new-GPU signal check, not a final 40-Element headline replication.

The final 40-Element library must use the TKS Element definitions directly: A1-A10 spiritual, B1-B10 mental, C1-C10 emotional, D1-D10 physical. A pure relabel of an unrelated dataset is not enough for a clean methodology claim. Worker tooling now has a source-derived TKS40 builder (`live-trace-worker/scripts/build_tks40_scenarios.py`) ported from the original Stage 9 fixture surface.

## Product Rule

The UI and investor/demo language must use this distinction:

```text
Current 20B status: real model run, real activation capture, early non-random CAS signal, plus a Foundation-28 v0 engineering run.
Not yet: source-faithful TKS definition replication, behavioral pass, or CAS universality proof.
Next gate: rerun Foundation-28 and 40 Elements using the source-derived Stage 7/Stage 9 methodology.
```

## Concrete Next Work

1. Build balanced source-derived Foundation-28 and 40-Element scenario libraries.
2. Verify metadata keeps legacy TKS codes (`1a..7d`, `A1..D10`) and current CAS labels.
3. Re-capture GPT-NeoX-20B hidden states for both source-faithful libraries.
4. Run Foundation-28 and 40-Element readout evaluation.
5. Generate candidate covers.
6. Run matched ablation.
7. If positive, run likelihood/output bridge.
8. Produce Evidence Packet and a one-page result summary.
