# Stage 8 Claims Matrix / Evidence Packet

**Status:** Stage 8 supports a cross-scale eta-to-epsilon CAS Harness
likelihood-conditioning claim from Pythia-160M to Pythia-1B. It does not
support hidden-state steering, raw CAS-symbol understanding, or pass-clean
open-ended generated-language control.

**Branch:** `experiment/cas-probe-pythia`

**Purpose:** lock the evidence boundary after the pre-registered Pythia-1B
CPL2 replication run. The Stage 8 result tests transfer of the Stage 7 harness
mechanism, not a new steering claim.

## Executive Summary

Plain English:

> CAS read a 28-Foundation label from Pythia-1B hidden states, realized that
> label as readable CAS context, and fed it back to Pythia-1B. The readable
> CAS prefix moved Pythia-1B's semantic likelihood toward the intended Drive
> phrase under the pre-registered gate.

What this proves:

> The eta-to-epsilon CAS Harness bridge replicated across scale within the
> Pythia family: Pythia-160M and Pythia-1B both show pass-clean likelihood
> conditioning from probe-predicted readable CAS prefixes.

What this does not prove:

> CAS has not shown direct hidden-neuron steering, raw CAS-symbol
> understanding, or pass-clean visible generated-text control.

Stakeholder-safe one-liner:

> CAS Harness can read a bounded cognitive structure from an open model and
> realize that structure as ordinary language context that measurably shifts
> the model's semantic likelihood; the stronger claim that CAS directly
> controls generated language remains unproven.

## Locked Artifacts

| Artifact | File | SHA-256 / Status |
|---|---|---|
| Pre-registration | `STAGE8_CROSS_MODEL_GATES_20260517.md` | committed before run in `ea5e191` |
| Capture script | `capture_stage8_pythia1b_activations.py` | committed before run in `01795fb` |
| CPL2 script | `probe_stage8_pythia1b_cpl2.py` | committed before run in `01795fb` |
| Locked Stage 7 fixture | `stage7_foundation_pilot_20260517.jsonl` | `3e4a1aca9f168a190116578b0b4fdb5bab633232ba06902039b233e589121250` |
| Pythia-1B activation binary | `stage8_pythia1b_activations_20260517.npz` | `3d1a118a6290ddfe9780c9693c9938d26815d43fca009f3b756a5ab0ab0a80ab`; RunPod artifact, not committed |
| Pythia-1B activation manifest | `stage8_pythia1b_activations_manifest_20260517.json` | `b1b4fe0fa04a5a2bcb2af47e1828ada5e5c99bd6a9963585553b2fb0cec0c896` |
| Pythia-1B probe report | `STAGE8_PYTHIA1B_PROBE_REPORT_20260517.json` | `fd87c7e072f019f512ef3884789611d59ebe4f9a0da37847129aca574914b0f6` |
| Pythia-1B CPL2 report | `STAGE8_PYTHIA1B_CPL2_REPORT_20260517.json` | `a7a43bc8f68df1bf4c24a820c14dcb69db0c4c15dbc5d171647ab3ddf10ae06c` |
| Pythia-1B summary | `STAGE8_PYTHIA1B_SUMMARY_20260517.md` | committed |

## Pre-Registered Gate Result

| Gate | Floor | Actual | Status |
|---|---:|---:|---|
| Probe-readable delta vs no-prefix | `> +0.15` | `+0.5542` | PASS |
| Paired Wilcoxon p | `< 0.05` | `2.58e-14` | PASS |
| Probe-readable minus partner-readable margin | `> +0.30` | `+1.2460` | PASS |
| Positive cases | `> 60/112` | `90/112` | PASS |

Verdict: `PASS_CLEAN_STAGE8_PYTHIA1B_CPL2_REPLICATES`.

## Claim Matrix

| Claim | Status | Evidence Supporting It | Evidence Blocking / Limiting It | Allowed Language |
|---|---|---|---|---|
| Pythia-1B carries the 28-Foundation signal in hidden states. | Supported | Validation-selected `focus_token` layer 8: val acc `1.0000`, test acc `0.8240`, test lacunarity `0.0152`. | This is the frozen Stage 7 synthetic role-bound fixture, not a natural web benchmark. | "Pythia-1B hidden states carry a strong 28-Foundation readout on this fixture." |
| Pythia-1B factorization is at least as clean as the Pythia-160M reference. | Supported | Stage 8 test lacunarity `0.0152`; Stage 7 reference lacunarity `0.021`. | Lacunarity is computed on probe prediction distribution, not a full mechanistic decomposition. | "The selected Pythia-1B readout is cleanly factorized by the same lacunarity check." |
| The Pythia-1B probe predicts the selected CPL2 rows well enough for the harness loop. | Supported | Selected-row Foundation accuracy `0.7321`; selected-row Drive accuracy `0.9464`. | Foundation-level errors remain; CPL2 is mostly testing Drive likelihood. | "The Pythia-1B probe supplies a usable Drive-level CAS readout for CPL2." |
| Probe-predicted readable CAS prefixes condition Pythia-1B semantic likelihood. | Supported | Probe-readable margin `0.6096`, delta `+0.5542` vs no-prefix, `90/112` positive, Wilcoxon p `2.58e-14`. | Likelihood-space result, not open-ended text-quality proof. | "Readable CAS realization prefixes condition Pythia-1B's semantic likelihood." |
| The readable-prefix bridge transfers across Pythia scale. | Supported | Pythia-160M CPL2: delta `+0.2828`, margin over partner `+0.6829`, `81/112` positive. Pythia-1B CPL2: delta `+0.5542`, margin over partner `+1.2460`, `90/112` positive. | Only tested within the Pythia family; not yet cross-architecture. | "The eta-to-epsilon bridge replicated from Pythia-160M to Pythia-1B." |
| Raw CAS notation conditions Pythia-1B. | Not supported | Raw controls included. | `gold_raw` delta `-0.0233`; `probe_raw` delta `-0.0227`; `partner_raw` delta `-0.0219`. | "Raw CAS symbols did not condition Pythia-1B in this setup." |
| CAS directly steers Pythia-1B hidden neurons. | Not supported | Stage 8 did not run hidden-state steering; Stage 7 hidden-state steering routes were negative. | CPL2 works through readable text prefix attention, not hidden-state surgery. | "Stage 8 is harness conditioning, not hidden-neuron steering." |
| CAS controls open-ended generated language. | Not supported | Stage 8 primary assay is likelihood. | Stage 7 CPL3/CPL4 visible generation did not close; Stage 8 did not run CPL3/CPL4. | "Open-ended visible generation remains an open tier." |
| Glass House / CAS Harness has cross-model validation. | Partially supported | Cross-scale within-architecture replication: Pythia-160M and Pythia-1B. | No OLMo, Llama, Qwen, or other architecture replication yet. | "The harness bridge is cross-scale within Pythia; cross-architecture remains the next gate." |

## Evidence Ladder

| Tier | Question | Current Answer |
|---|---|---|
| Pre-registration | Were gates locked before the run? | Yes: `STAGE8_CROSS_MODEL_GATES_20260517.md` committed in `ea5e191`. |
| Dataset | Was the frozen Stage 7 fixture reused? | Yes: 4,368 rows, SHA `3e4a1...1250`. |
| Capture | Was the full Pythia-1B activation artifact verified by manifest? | Yes: SHA `3d1a1...80ab`, manifest committed. |
| Layer choice | Was layer selected by validation before test reporting? | Yes: layer 8 selected by highest validation accuracy with lacunarity tie-break. |
| Readout | Can Pythia-1B recover the 28-Foundation label? | Yes: selected layer test acc `0.8240`. |
| Factorization | Is the selected readout low-lacunarity? | Yes: `0.0152`, cleaner than Stage 7 reference `0.021`. |
| CPL2 | Does probe-readable prefix pass the likelihood gate? | Yes: all four pre-registered thresholds pass. |
| Raw symbol control | Do raw CAS symbols work? | No. |
| Hidden-state steering | Did Stage 8 prove internal steering? | No. |
| Cross-architecture | Does it transfer beyond Pythia? | Not tested. |

## Reviewer Playbook

1. Verify the Stage 8 pre-registration exists before result artifacts:
   `STAGE8_CROSS_MODEL_GATES_20260517.md`, commit `ea5e191`.
2. Verify the implementation scripts were committed before the run:
   `capture_stage8_pythia1b_activations.py` and
   `probe_stage8_pythia1b_cpl2.py`, commit `01795fb`.
3. Verify the fixture SHA:
   `3e4a1aca9f168a190116578b0b4fdb5bab633232ba06902039b233e589121250`.
4. If the RunPod activation artifact is available, verify:
   `3d1a118a6290ddfe9780c9693c9938d26815d43fca009f3b756a5ab0ab0a80ab`.
5. Inspect `STAGE8_PYTHIA1B_PROBE_REPORT_20260517.md` for the validation-selected layer.
6. Inspect `STAGE8_PYTHIA1B_CPL2_REPORT_20260517.md` for the four gate thresholds.
7. Confirm the claim boundary:
   cross-scale likelihood conditioning is supported; hidden-state steering,
   raw-symbol understanding, and visible generated-language control are not.

## Stakeholder Language

Use this:

> "CAS Harness replicated the read-realize-condition loop from Pythia-160M to
> Pythia-1B. The system reads a bounded CAS Foundation label from hidden
> states, realizes it as readable context, and the host model's semantic
> likelihood moves in the intended direction."

Use this:

> "This is stronger than a one-off demo because the same locked CPL2 test
> passed on two model sizes in the same family."

Do not use this:

> "CAS directly controls Pythia's neurons."

Do not use this:

> "Pythia understands raw CAS symbols."

Do not use this:

> "CAS can control open-ended generated text."

## Current Bottom Line

Stage 8 changes the Glass House / CAS Harness boundary:

> The Pythia-160M CPL2 result is no longer a one-model curiosity. The same
> eta-to-epsilon likelihood bridge passes cleanly on Pythia-1B, with a larger
> measured effect under the pre-registered gate. The supported product claim
> is cross-scale readable-prefix likelihood conditioning. The unsupported
> claims remain direct hidden-state steering, raw-symbol conditioning, and
> pass-clean visible generation.

The next clean gate is cross-architecture replication.
