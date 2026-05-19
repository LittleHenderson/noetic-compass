# CAS Harness Product Evidence Packet

Date: 2026-05-19

Branch: `experiment/cas-probe-pythia`

Status: `PRODUCT_PACKET_LOCKED`

This is the reviewer/customer packet for CAS Harness. It compresses the
Stage 7-18 research chain into a product-facing evidence surface.

## Decision

Build the Evidence Packet. Stop chasing visible free-form text for now.

Stage 18 is informative because it shows where the bridge ends:

> readable CAS realization moves likelihood, but free-form greedy generation is
> a lossy surface channel.

That does not break the product. The product is not "make the host model say a
different sentence." The product is:

> read internal cognitive structure, prove the readout is real, expose weak or
> conflicted regions, and attach an auditable evidence packet.

## Decision Record: Product Packet vs More Visible Text

Two paths were available after Stage 18:

| Path | Value | Limitation | Decision |
|---|---|---|---|
| More visible text tests | Useful research follow-up for forced-choice or constrained decoding. | Free-form generated text is a lossy channel and Stage 18 already showed prompt blending. | Defer. |
| Product Evidence Packet | Packages the strongest evidence now: readout, controls, blind spots, hashes, and CPL2 likelihood. | Does not claim open-ended generation control. | Build now. |

The product decision is based on measurement quality. CPL2 likelihood is closer
to the host model's probability state than generated prose. Stage 18 does not
erase CPL2; it shows why the product should expose the distribution-level
evidence instead of waiting for free-form text to become clean.

## One-Sentence Product Claim

> CAS Harness reads bounded CAS cognitive structure from open-model hidden
> activations, validates the readout with controls, flags blind spots, and
> packages the evidence so a reviewer can verify what was measured and what was
> not claimed.

## What Is Proven

| Capability | Evidence | Product meaning |
|---|---|---|
| Hidden-state readout | Stage 7, 9, 11, 12 | CAS can recover bounded CAS labels from open-model activations. |
| Beyond-text signal | Stage 7, 9, 11, 12 | The activation readout is not merely a text classifier on these fixtures. |
| Readout causality | Stage 7, 9, 11, 12 | Removing the trained subspace collapses the CAS readout while random removals do not. |
| Blind-spot tracing | Stage 13 and 13.1 | CAS can flag weak, drifting, or conflicted readout paths. |
| Weight geometry inspection | Stage 14.1 | CAS can inspect whether a learned CAS subspace aligns with static output geometry above random. |
| Cross-model likelihood bridge | Stage 7, 8, 14, 15, 16 | Readable CAS realization shifts semantic likelihood across Pythia, OLMo, and Qwen. |
| Raw-symbol control | Stages 7, 8, 14, 15, 16 | Raw CAS notation does not drive the effect; readable realization does. |

## What Is Not Proven

| Claim | Status |
|---|---|
| CAS sees exact causal neurons. | Not proven. Current evidence is probe/subspace/trace level. |
| CAS sees weights firing. | Rejected phrasing. Weights are static; activations change per input. |
| Host models run a CAS compiler internally. | Not proven. Compiler validation is external fixture provenance. |
| Raw CAS symbols steer host models. | Not supported. Raw controls are near null. |
| Hidden-state steering controls generated language. | Not supported. Stage 7 steering/additive routes failed controls. |
| Free-form visible generation is solved. | Not supported. Stage 18 is a clean null. |
| CAS fully solves the black-box problem. | Not supported. CAS reduces opacity for tested structures. |

## Cross-Model Evidence Line

Load-bearing condition: `probe_readable`.

| Model | Family | Selected layer | Test acc | Delta vs none | Margin over partner | Positive cases | p |
|---|---|---:|---:|---:|---:|---:|---:|
| `EleutherAI/pythia-160m` | Pythia | 6 | `0.7857` | `+0.2828` | `+0.6829` | `81/112` | sign p near zero |
| `EleutherAI/pythia-1b` | Pythia | 8 | `0.8240` | `+0.5542` | `+1.2460` | `90/112` | `2.58e-14` |
| `EleutherAI/pythia-2.8b` | Pythia | 14 | `0.8588` | `+0.5832` | `+1.3363` | `92/112` | `3.08e-15` |
| `allenai/OLMo-1B-hf` | OLMo | 16 | `0.9060` | `+0.6037` | `+1.3047` | `87/112` | `3.17e-12` |
| `Qwen/Qwen2.5-1.5B` | Qwen | 11 | `0.8202` | `+0.7960` | `+1.6253` | `83/112` | `2.92e-12` |

Interpretation:

> The eta-to-epsilon readable realization bridge replicated across five model
> runs and three architecture families.

Boundary:

> This is likelihood conditioning. It is stronger and cleaner than the
> free-form text surface for this product claim.

## Stage 18 Null: Why It Does Not Break The Packet

Stage 18 tested whether Qwen's free-form generated continuation visibly shifts
under `probe_readable` context.

Result: `NULL_STAGE18_QWEN_VISIBLE_TEXT_SHIFT_NOT_ESTABLISHED`.

Key numbers:

- Probe-readable minus partner-readable margin: `-0.1414`.
- Probe-readable delta vs none: `+0.0178`.
- Probe > partner rows: `12/112`.
- Wilcoxon p: `0.999759`.

Why this does not overturn the bridge:

- CPL2 measures the probability distribution before decoding.
- Free-form greedy generation adds an output bottleneck.
- Qwen often repeats or blends both focused roles from the prompt.
- The visible text surface can hide a likelihood shift.

Product decision:

> Do not wait for free-form visible text. Use CPL2 likelihood, readout
> causality, blind-spot diagnostics, and provenance as the product evidence.

## Comparison To NLA-Style Interpretability

Anthropic's Natural Language Autoencoders (NLA) frame activation
interpretability as an autoencoding problem: an activation verbalizer maps an
activation to text, and an activation reconstructor maps that text back toward
the original activation. The training objective is reconstruction quality.

Source note: Anthropic's May 7, 2026 NLA paper describes the activation
verbalizer / activation reconstructor loop and the reconstruction-loss training
objective at `https://transformer-circuits.pub/2026/nla/index.html`; Anthropic's
research post summarizes the same round trip at
`https://www.anthropic.com/research/natural-language-autoencoders`.

CAS Harness is different:

| Dimension | NLA-style approach | CAS Harness |
|---|---|---|
| Output form | Natural-language explanation | Typed CAS labels, traces, and claim badges |
| Main score | Reconstruction quality / variance explained | Probe accuracy, text/metadata lift, ablation, lacunarity, CPL2 likelihood |
| Risk | Explanation can sound plausible while being hard to type-check | Typed labels can be wrong, but are easier to gate and falsify |
| Strength | Rich natural-language descriptions of activations | Structured, auditable, no-confabulation claim surface |
| Product use | Interpret internal activation content | Evidence packet: what was read, how strongly, where weak, what controls passed |

Cleaner product position:

> CAS Harness is not trying to beat NLA at prose explanation. It offers a
> typed evidence layer: structured readouts, controls, blind spots, hashes,
> and explicit claim boundaries.

## Evidence Packet Contents

Each packet should contain:

- `trace_id`
- model name and revision
- code commit
- fixture SHA-256
- activation artifact SHA-256
- selected layer and readout
- predicted CAS label
- confidence and entropy
- lacunarity
- per-layer trace
- blind-spot flags
- text and metadata baselines
- ablation result and random controls, when available
- raw-symbol controls, when testing prefixes
- readable-prefix likelihood result
- claim-level badge
- caveats

## Claim-Level Badges

| Level | Badge | Meaning |
|---|---|---|
| 1 | Provenance | Files, hashes, model revision, and commit are inspectable. |
| 2 | Readout | A trained CAS probe recovers a label from activations. |
| 3 | Beyond text | Activation readout beats text and/or metadata baselines. |
| 4 | Readout causal | Targeted subspace removal collapses readout; random controls do not. |
| 5 | Trace diagnostic | Layer trace flags stability, drift, conflict, or blind spots. |
| 6 | Weight geometry | CAS subspace aligns with static weight geometry above random. |
| 7 | Harness conditioning | Readable CAS realization shifts likelihood under controls. |
| 8 | Visible generation | Generated text visibly shifts. Not closed yet. |

## Reviewer Walkthrough

1. Read the claim badge and boundary.
2. Verify model revision and fixture SHA.
3. Verify the pre-registration predates the result.
4. Confirm layer selection used validation data only.
5. Inspect text and metadata baselines.
6. Inspect readout accuracy and lacunarity.
7. Inspect ablation and random controls if the claim is causal.
8. Inspect blind-spot trace thresholds.
9. Inspect raw-symbol controls if prefix conditioning is claimed.
10. Check rejected claims before quoting the result externally.

## Developer Build Target

Build the product surface around a `EvidencePacket` object.

Minimum fields:

```json
{
  "trace_id": "string",
  "model": {"name": "string", "revision": "string"},
  "provenance": {"code_commit": "string", "fixture_sha256": "string", "activation_sha256": "string"},
  "readout": {"axis": "foundation", "layer": 11, "position": "focus_token", "label": "F3A", "confidence": 0.0},
  "diagnostics": {"lacunarity": 0.0, "blindspot_flags": []},
  "controls": {"text_baseline": null, "metadata_baseline": null, "random_ablation": null, "raw_symbol": null},
  "conditioning": {"probe_readable_delta": null, "partner_margin": null, "p_value": null},
  "claim_badges": [],
  "caveats": []
}
```

UI behavior:

- Show the claim badge first.
- Show provenance next.
- Show the readout and layer trace.
- Show controls before any interpretation.
- Show caveats in the same view, not hidden in a footer.
- Do not call the result "thought control."

## Stakeholder Script

Use this:

> "This packet shows exactly what CAS Harness measured. It names the model,
> data, code, activation artifact, selected layer, readout accuracy, controls,
> blind spots, and claim boundary. The result is not a claim that CAS controls
> the model. It is a claim that CAS can expose a structured, auditable readout
> of the model's internal activations and validate that readout with controls."

Use this:

> "The strongest result is likelihood-level. That is intentional. Likelihood
> is closer to the model's probability state than free-form text, which can
> hedge, blend, or echo the prompt."

Do not use this:

> "CAS reads the model's exact thoughts."

Do not use this:

> "CAS solved the black box."

Do not use this:

> "CAS can force the model to say a chosen sentence."

## Next Product Step

Build the Evidence Packet UI and export path.

Research can continue later with forced-choice visible text or multi-harness
hidden-content benchmarks, but the product should now center on:

> inspectable readouts, controls, blind spots, hashes, and claim boundaries.

## Implementation Lock

Immediate implementation target:

1. Add a reusable CAS Harness `EvidencePacket` schema.
2. Add a backend endpoint that serves packet JSON by trace or artifact id.
3. Attach committed manifests, model revisions, report paths, and SHA-256
   values.
4. Render a reviewer drawer that opens with the claim badge, then provenance,
   then readout, controls, blind spots, and caveats.
5. Add export buttons for JSON and markdown.
6. Keep visible-generation results in the packet as a bounded negative, not as
   a blocker.

Do not run more GPU experiments before this product surface exists unless a
new gate is explicitly authorized.
