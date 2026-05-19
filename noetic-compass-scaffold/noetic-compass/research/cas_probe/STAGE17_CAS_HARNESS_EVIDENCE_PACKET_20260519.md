# Stage 17 CAS Harness Evidence Packet

Date: 2026-05-19

Branch: `experiment/cas-probe-pythia`

Status: `EVIDENCE_PACKET_LOCKED_NO_NEW_EXPERIMENT`

Stage 17 is not a GPU run. It consolidates Stages 7-16 into one
reviewer-facing packet so the CAS Harness claim can be audited without
threading through every intermediate report.

## Executive Summary

Plain English:

> CAS Harness reads a bounded CAS structure from an open model's hidden
> activations, realizes that structure as readable context, and tests whether
> the host model's semantic likelihood shifts in the intended direction.

The current evidence supports this bounded claim:

> CAS Harness has pass-clean eta-to-epsilon readable-prefix likelihood evidence
> across three model families: Pythia, OLMo, and Qwen.

The current evidence does not support these stronger claims:

- CAS sees exact causal neurons.
- CAS sees weights "firing."
- Raw CAS symbols alone steer host models.
- CAS directly controls open-ended generated text.
- Host models internally run a CAS compiler.
- CAS has solved the whole black-box problem.

## Core Mechanism

CAS Harness is a two-step loop.

1. Eta/read: hidden activations -> CAS readout.
2. Epsilon/realize: CAS readout -> readable CAS context -> likelihood test.

This is different from hidden-state steering.

Hidden-state steering says:

> Push a direction inside the model and make the model say something different.

CAS Harness says:

> Read a structured signal, realize it into ordinary language context, and
> check whether the model's semantic likelihood moves in the intended
> direction.

That distinction is load-bearing. Earlier hidden-state steering attempts were
negative. The eta-to-epsilon bridge passed.

## Evidence Ladder

| Tier | Status | Load-bearing evidence | Boundary |
|---|---|---|---|
| 28 Foundations readout | Supported | Stage 7 Pythia-160M, test acc `0.7857`, +28.9 pp over text | Fixture-bound hidden-state readout |
| Readout causality | Supported | Stage 7 targeted removal drops `0.7857 -> 0.0357` exact chance | Causal for trained readout, not generation |
| Drive factor | Supported | Stage 7 Drive readout `0.8907`, ablation to `0.1429` chance | Factor-level readout only |
| 40 Elements | Supported | Stage 9 full 40-way acc `0.8980`, +39.7 pp over text | Pythia-160M fixture |
| Operators | Grey | Stage 10 acc `0.9918`, ablation to `0.2000`, but text `0.9557` | Ceiling-limited isolated task |
| Expression shapes | Supported | Stage 11 acc `0.9300`, +28.6 pp over text, ablation to chance | Grammar-shape readout, not formula solving |
| Formula families | Supported | Stage 12 acc `0.8995`, +26.0 pp over text, compiler-backed fixture | Pythia does not internally validate CAS formulas |
| Multi-layer blind spots | Supported as diagnostic | Stage 13 best acc `0.9540`; `22.3%` problem-like traces | Weak/unstable readout evidence, not proof of incapacity |
| Blind-spot sanity | Supported | Stage 13.1 confirms balanced fixture and documented thresholds | Per-readout boundary required |
| Weight geometry | Supported as technical appendix | Stage 14.1 output logit-lens energy `2.83x` random, p `0.0099` | Static geometry, not weights firing |
| Eta-to-epsilon bridge | Supported | Stages 7, 8, 14, 15, 16 all pass CPL2-style readable-prefix tests | Likelihood conditioning, not open-ended control |
| Raw CAS symbols | Not supported | Raw controls near null across CPL2 runs | Use readable realization, not raw notation |
| Hidden-state generation steering | Not supported | Stage 7 steering/additive routes failed random controls | Do not claim neuron steering |
| Visible text quality | Open | Earlier visible generation tests were directional but not pass-clean | Next experimental gate |

## Cross-Model CPL2 Line

Load-bearing condition: `probe_readable`.

| Model | Family | Selected layer | Test acc | Delta vs none | Margin over partner | Positive cases | Wilcoxon p |
|---|---|---:|---:|---:|---:|---:|---:|
| `EleutherAI/pythia-160m` | Pythia | 6 | `0.7857` | `+0.2828` | `+0.6829` | `81/112` | sign p near zero |
| `EleutherAI/pythia-1b` | Pythia | 8 | `0.8240` | `+0.5542` | `+1.2460` | `90/112` | `2.58e-14` |
| `EleutherAI/pythia-2.8b` | Pythia | 14 | `0.8588` | `+0.5832` | `+1.3363` | `92/112` | `3.08e-15` |
| `allenai/OLMo-1B-hf` | OLMo | 16 | `0.9060` | `+0.6037` | `+1.3047` | `87/112` | `3.17e-12` |
| `Qwen/Qwen2.5-1.5B` | Qwen | 11 | `0.8202` | `+0.7960` | `+1.6253` | `83/112` | `2.92e-12` |

Interpretation:

> The readable eta-to-epsilon bridge is no longer a one-model result. It
> replicated across Pythia scale and across OLMo and Qwen architectures.

Boundary:

> This is still a bounded likelihood assay. It does not prove open-ended
> generation control.

## Provenance Index

| Stage | Primary artifact | Pre-run gate / commit | Result artifact |
|---|---|---|---|
| 7 | `STAGE7_CLAIMS_MATRIX_20260517.md` | Stage 7 artifacts locked in branch history | `stage7_cas_prefix_full_loop_20260517.json` |
| 8 | `STAGE8_CROSS_MODEL_GATES_20260517.md` | gate committed before run | `STAGE8_PYTHIA1B_CPL2_REPORT_20260517.json` |
| 9 | `STAGE9_40_ELEMENTS_GATES_20260517.md` | gate committed before run | `stage9_factor_ablation_report_20260517.json` |
| 10 | `STAGE10_OPERATORS_GATES_20260517.md` | gate committed before run | `stage10_operator_probe_report_20260517.json` |
| 11 | `STAGE11_EXPRESSION_SHAPES_GATES_20260517.md` | gate committed before run | `stage11_expression_shape_probe_report_20260517.json` |
| 12 | `STAGE12_EQUATIONS_FORMULAS_GATES_20260517.md` | gate committed before run | `stage12_equations_formula_probe_report_20260517.json` |
| 13 | `STAGE13_MULTILAYER_TRACE_AUDIT_GATES_20260518.md` | `d2c18bf`; bug fix `80377ab` documented | `stage13_multilayer_formula_trace_audit_20260518.json` |
| 13.1 | `STAGE13_BLINDSPOT_SANITY_AUDIT_GATES_20260519.md` | `ad52f91` | `stage13_blindspot_sanity_audit_20260519.json` |
| 14 | `STAGE14_PYTHIA28B_GATES_20260518.md` | `ae518ad` | `STAGE14_PYTHIA28B_CPL2_REPORT_20260518.json` |
| 14.1 | `STAGE14_WEIGHT_GEOMETRY_GATES_20260519.md` | `ad52f91` | `stage14_weight_geometry_alignment_20260519.json` |
| 15 | `STAGE15_OLMO1B_GATES_20260519.md` | `502b293` | `STAGE15_OLMO1B_CPL2_REPORT_20260519.json` |
| 16 | `STAGE16_QWEN15B_GATES_20260519.md` | `f5caf5c` | `STAGE16_QWEN15B_CPL2_REPORT_20260519.json` |

## Model And Artifact Hashes

| Model | Revision | Activation SHA-256 |
|---|---|---|
| `EleutherAI/pythia-160m` | `50f5173d932e8e61f858120bcb800b97af589f46` | `d2fc03ad2572f49f8cfbb79898b074fc4c552502fe62bc62a4427963ab67c47f` |
| `EleutherAI/pythia-1b` | `f73d7dcc545c8bd326d8559c8ef84ffe92fea6b2` | `3d1a118a6290ddfe9780c9693c9938d26815d43fca009f3b756a5ab0ab0a80ab` |
| `EleutherAI/pythia-2.8b` | `2a259cdd96a4beb1cdf467512e3904197345f6a9` | `fc8204bc749ea9932532487f28c7462e491058a2f705e26e9e141427e81901d7` |
| `allenai/OLMo-1B-hf` | `aee7752d9c08ee4775e9b0091426d8410e8f6a89` | `b2fbf6661c4b3b9067bdc74edb27c587cee498bc9b6717ee4f74682d07a47e8b` |
| `Qwen/Qwen2.5-1.5B` | `8faed761d45a263340a0528343f099c05c9a4323` | `ccb79afe5a3215f0f6aac828c574a0d14cf8115ab769489ea4269c70ce43fe8e` |

The large `.npz` activation binaries are not committed. Their manifests and
SHA-256 values are committed so a reviewer with the artifacts can verify them.

## What A Researcher Does With This Packet

1. Read the claim boundary first.
2. Pick a claim tier: readout, readout causality, blind spots, weight geometry,
   or eta-to-epsilon conditioning.
3. Check that the relevant gate file predates the result.
4. Verify the fixture SHA and model revision.
5. If the activation binary is available, recompute its SHA-256 and compare it
   to the manifest.
6. Confirm layer selection used validation accuracy and lacunarity before test
   reporting.
7. Inspect the text and metadata baselines.
8. Inspect targeted ablation and random controls for readout-causality claims.
9. Inspect trace thresholds before accepting blind-spot language.
10. Inspect raw-symbol controls before accepting any CAS-prefix claim.
11. Check the rejected-claims table and make sure public wording does not
    exceed it.

## What A Developer Does With This Packet

1. Load the frozen fixture and model revision.
2. Capture hidden activations for the pre-registered layer/readout positions.
3. Train per-layer probes on the frozen train split.
4. Select the layer on validation only.
5. Emit a probe report with test accuracy, macro-F1, lacunarity, and splits.
6. For readout causality, remove the trained subspace and compare against
   same-rank random removals.
7. For blind spots, emit per-example layer traces with confidence, entropy,
   stability, drift, and conflicted flags.
8. For eta-to-epsilon, convert the probe label into readable CAS context and
   score `none`, `gold_readable`, `probe_readable`, `partner_readable`, and raw
   controls.
9. Attach hashes, model revisions, package versions, and claim-level badges.
10. Export the packet as reviewer JSON/markdown.

## Multi-Harness Composition And Hidden Content

Current CAS Harness evidence mostly uses one readout at a time:

> eta-1 = probe on internal activations for one CAS axis.

That is useful, but it is still a thin view of the host model. A single probe
can say "this Foundation signal is present here." It cannot yet give the full
CAS Working Memory profile.

Multi-harness composition is the next architectural upgrade:

> eta-1 becomes a structured internal tensor across CAS axes, with each axis
> read at its own optimal layer or layer band.

That matters for hidden-content detection because the audit compares:

- eta-1: what the model internally represents
- eta-2: what the model emits in text

The richer eta-1 becomes, the more precisely CAS can describe the gap between
internal representation and emitted answer.

Concrete effects:

1. Denser baseline. More CAS axes create more dimensions where emitted text can
   be compared against internal state.
2. Cross-axis tension. If one harness reads principled aversion while another
   reads warmth or approach, that inconsistency is itself an audit signal.
3. Trajectory localization. Multiple harnesses across layer bands can show
   where internal coherence starts to diverge before output.
4. Disagreement-as-signal. Agreement means the internal profile is coherent;
   disagreement tells reviewers where to inspect.

This does not change the evidence method. It scales the granularity of the
internal profile. The current Stage 7-16 result proves that the harness loop is
real for a bounded axis. Multi-harness composition is how that loop becomes a
primary hidden-content audit surface.

## Stakeholder-Safe Language

Use this:

> CAS Harness has replicated a bounded read-realize-condition loop across
> Pythia, OLMo, and Qwen. It reads a CAS Foundation signal from hidden
> activations, realizes that signal as readable context, and the host model's
> semantic likelihood moves in the intended direction.

Use this:

> CAS can expose blind spots in the sense of weak, unstable, drifting, or
> conflicted readout evidence across layers and readout paths.

Do not use this:

> CAS sees the exact neurons that caused the answer.

Do not use this:

> CAS sees weights firing.

Do not use this:

> CAS directly controls any open model's generated language.

## Next Gate

The next scientific gate should be visible text quality:

> Given readable CAS realization context, do independent judges or classifiers
> see the generated continuation align more strongly with the target Foundation?

That should be pre-registered as Stage 18. Stage 17 locks the evidence before
that visible-generation claim is attempted.
