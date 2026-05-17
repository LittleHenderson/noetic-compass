# Stage 9 Claims Matrix / Evidence Packet

**Status:** Stage 9 supports a strong original-TKS 40 Elements hidden-state
readout claim in Pythia-160M, plus readout-causal factorization into
Domain/World, Noetic, and the full 40-way interaction. It does not support
hidden-state steering, raw-symbol understanding, visible generated-language
control, or cross-model generality.

**Branch:** `experiment/cas-probe-pythia`

## Executive Summary

Plain English:

> CAS tested the user's original TKS 40 Elements: `A1..D10`, or four
> Worlds/Domains crossed with ten Noetics. Pythia-160M hidden states recovered
> the full 40-way label at `89.8%` locked-test accuracy, far above the best
> text baseline at `50.1%`. Removing the trained readout subspace dropped the
> full 40-way readout to exact chance, and the same was true for Domain/World
> and Noetic factors separately.

What this proves:

> The 40 Elements are not just a text-labeling scheme in this fixture. There is
> a strong, load-bearing hidden-state readout channel for the 40-slot
> Domain/World x Noetic structure.

What this does not prove:

> It does not prove that CAS can steer Pythia's generated text, that Pythia
> understands raw TKS/CAS symbols, or that the result transfers to other model
> families.

## Locked Artifacts

| Artifact | File | SHA-256 / Status |
|---|---|---|
| Stage 9.0 gates | `STAGE9_40_ELEMENTS_GATES_20260517.md` | committed before run in `be9b4a3` |
| Stage 9.1 gates | `STAGE9_FACTOR_ABLATION_GATES_20260517.md` | committed before run in `0f31fc7` |
| Fixture | `stage9_elements_pilot_20260517.jsonl` | `2f8637eedff0fb4d9e6191bd5c051ddc21cea699e33621896469a2e522306889` |
| Fixture manifest | `stage9_elements_pilot_manifest_20260517.json` | committed |
| Activation binary | `stage9_elements_pilot_activations_20260517.npz` | `c70582b54f309c805fd90a69e7d23a80a714fc692aac4c1364ebc4e21b410cfb`; RunPod artifact, not committed |
| Activation manifest | `stage9_elements_pilot_activations_manifest_20260517.json` | committed |
| Stage 9.0 probe report | `stage9_elements_pilot_probe_report_20260517.json` | committed |
| Stage 9.1 factor/ablation report | `stage9_factor_ablation_report_20260517.json` | `8a4f9a0d1f73c69d4023f4405b28e85d275c11826ecd48f7485892befa505df8` |

## Claim Matrix

| Claim | Status | Evidence Supporting It | Evidence Blocking / Limiting It | Allowed Language |
|---|---|---|---|---|
| The original TKS 40 Elements can be operationalized as 4 Worlds/Domains x 10 Noetics. | Supported for this experiment | Fixture labels `A1..D10`; mapping locked in `STAGE9_40_ELEMENTS_GATES_20260517.md`. | Operational mapping, not endorsement of every metaphysical claim in source text. | "Stage 9 operationalizes the original TKS 40 Elements as Domain/World x Noetic slots." |
| The Stage 9 fixture is balanced and leakage-checked. | Supported | 8,320 rows; 208 per element; no literal element code or CAS/TKS/noetic words in model-facing prompts. | Synthetic role-bound fixture, not natural web text. | "The fixture is balanced, frozen, and avoids literal label leakage." |
| Pythia-160M hidden states carry the full 40-Element signal beyond text. | Supported | Stage 9.0 `focus_token` layer 5 test acc `0.8980`; best text `0.5009`; lift `+0.3971`; McNemar p `0`. | Text baseline remains strong because the fixture has learnable semantics. | "The activation readout materially beats strong text-only baselines." |
| The full 40-way interaction is causal for the CAS readout. | Supported | Stage 9.1 interaction acc `0.8980`; targeted ablation drops to exact chance `0.0250`; same-rank random max disruption `0.0000`; p `0.0323`. | This is causality for the trained CAS readout, not for Pythia generation. | "Removing the 40-Element readout subspace collapses the CAS readout to chance while random removals do not." |
| Domain/World is a real factor in the 40 Elements readout. | Supported | Domain acc `0.9230`; best text `0.7500`; ablated to exact chance `0.2500`; rank `3`; random p `0.0323`. | Domain wording is partially visible to text; text baseline is high. | "Domain/World is readable beyond text and causal for the Domain readout." |
| Noetic is a real factor in the 40 Elements readout. | Supported | Noetic acc `0.9154`; best text `0.7500`; ablated to exact chance `0.1000`; rank `9`; random p `0.0323`. | Noetic wording is partially visible to text; text baseline is high. | "Noetic is readable beyond text and causal for the Noetic readout." |
| The 40 Elements result is stronger than the earlier raw noetic route. | Supported as an internal comparison | Raw noetic transfer stayed mixed; Stage 9 full interaction gets `0.8980` and exact-chance ablation. | Different fixture and label space; not a direct apples-to-apples benchmark. | "The 40-Element formulation gives a much cleaner readout result than earlier raw noetic-only probes." |
| CAS can steer Pythia's hidden states to control generated text. | Not supported | Stage 9 did not test generation steering. | Stage 7 steering routes were negative; Stage 9 is readout-level only. | "Stage 9 is readout and readout-causal evidence, not hidden-state steering." |
| Raw TKS/CAS element symbols condition Pythia. | Not tested / not supported | Stage 9 prompts did not use raw symbols in model-facing text. | No raw-symbol conditioning assay was run. | "Raw element-symbol understanding remains untested here." |
| The 40 Elements result transfers across models. | Not tested | Pythia-160M only. | No Pythia-1B or cross-architecture Stage 9 run yet. | "This is a Pythia-160M result; cross-model transfer remains a next gate." |

## Evidence Ladder

| Tier | Question | Current Answer |
|---|---|---|
| Dataset | Is the 40-Element fixture frozen and balanced? | Yes. |
| Readout | Can Pythia-160M recover the full 40-way label? | Yes: `0.8980`. |
| Text baseline | Does activation beat text? | Yes: +39.7 pp, McNemar p `0`. |
| Metadata baseline | Does activation beat diagnostic metadata? | Yes: +39.8 pp for full interaction. |
| Full ablation | Does removing the full readout subspace collapse the readout? | Yes: exact chance `0.0250`. |
| Domain factor | Does Domain/World pass readout + ablation? | Yes. |
| Noetic factor | Does Noetic pass readout + ablation? | Yes. |
| Generation | Does this control generated language? | Not tested. |
| Cross-model | Does this transfer to Pythia-1B or another architecture? | Not tested. |

## Stakeholder Language

Use this:

> "CAS found the original TKS 40-Element structure inside Pythia-160M hidden
> states. The full 40-way readout beats text by almost 40 points, and removing
> the trained readout subspace drops the readout to exact chance."

Use this:

> "The signal decomposes cleanly: Domain/World, Noetic, and the full
> Domain-by-Noetic interaction each pass readout and ablation gates."

Do not use this:

> "CAS controls Pythia's generated language."

Do not use this:

> "Pythia understands TKS symbols."

Do not use this:

> "CAS solved the entire black box."

## Current Bottom Line

Stage 9 is the cleanest internal-readout result so far:

> The original TKS 40 Elements form a strong, factorized, load-bearing
> hidden-state readout in Pythia-160M. The readout is stronger than text,
> stronger than metadata, and collapses to exact chance under targeted
> subspace removal. The supported claim is readout-level interpretability,
> not generation control.

The next clean gates are either a 40-Element eta-to-epsilon likelihood bridge
or cross-scale replication on Pythia-1B.
