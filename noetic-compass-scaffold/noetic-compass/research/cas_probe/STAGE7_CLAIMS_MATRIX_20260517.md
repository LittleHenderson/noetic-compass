# Stage 7 Claims Matrix / Evidence Packet

**Status:** Stage 7 supports strong internal readout, readout-causal
ablation, factorization evidence, and an eta-to-epsilon CAS Harness
conditioning bridge for the original-TKS 28 Foundations in Pythia-160M.
Stage 7 does **not** currently support internal hidden-state steering or
pass-clean open-ended generated-language control.

**Branch:** `experiment/cas-probe-pythia`

**Purpose:** lock the evidence boundary after Stage 7.0-7.CPL4 before any
cross-model or product-strategy claim. This prevents the project from sliding
from discovery into test-chasing. Negative internal steering hooks are not a
reason to stop; they are evidence that eta/readout directions are not epsilon/
realization directions. CPL2 then tests the missing bridge directly.

## Executive Summary

Plain English:

> CAS tested the original TKS 28 Foundations inside Pythia-160M. The hidden
> states carry a strong Foundation signal beyond text-only baselines. Removing
> the trained Foundation subspace collapses the CAS readout to exact chance.
> Splitting the signal shows Drive and the full 28-way Drive x Register
> interaction are strong, while Register is real but text-explained in this
> fixture. Removing Drive during greedy generation did not change Pythia's
> language more than random controls. But when CAS reads a Foundation label
> from Pythia hidden states, realizes it as readable CAS context, and feeds it
> back as a prefix, Pythia's semantic likelihood moves strongly toward the
> intended Drive phrase. That is the eta-to-epsilon bridge.

What this proves:

> CAS can locate and causally test an internal 28-Foundation readout channel in
> an open model, then use that readout to condition the model through readable
> realized CAS context.

What this does not prove:

> CAS has shown direct hidden-neuron steering or pass-clean open-ended
> generated-language control.

Stakeholder-safe one-liner:

> CAS opens a verified readout window inside an open model and can feed that
> readout back as readable CAS context that changes semantic likelihood. The
> stronger claim that CAS directly steers Pythia's internal generation path is
> still unproven.

## Locked Artifacts

| Artifact | File | SHA-256 / Status |
|---|---|---|
| Locked Stage 7 fixture | `stage7_foundation_pilot_20260517.jsonl` | `3e4a1aca9f168a190116578b0b4fdb5bab633232ba06902039b233e589121250` |
| Activation capture | `stage7_foundation_pilot_activations_20260517.npz` | `d2fc03ad2572f49f8cfbb79898b074fc4c552502fe62bc62a4427963ab67c47f`; RunPod artifact, not committed because it is about 304 MB |
| Activation manifest | `stage7_foundation_pilot_activations_manifest_20260517.json` | committed |
| Stage 7.0 probe report | `stage7_foundation_pilot_probe_report_20260517.json` | `ffe6d3fbab2f3b7e57fd40aa0d4c4a67271034418adda6caaddc24da6e821f67` |
| Stage 7.1 readout-ablation report | `stage7_foundation_layer6_ablation_report_20260517.json` | `8e07cbef36c76bd8bc5984f599dfee7eab13be46cf250ce759cb502f439eb6a5` |
| Stage 7.2 factor-check report | `stage7_factor_check_report_20260517.json` | `ec1a1b5a1581000fb6bcf0bde981d58e200cc89a2992c3ecc10522899ba96317` |
| Stage 7.3 Drive generation report | `stage7_drive_generation_localized_report_20260517.json` | `a8ee76f62b960137070af5e24a355a9242e1b5625a1ad44868c242ccc3549da2` |
| Stage 7.CPL likelihood bridge report | `stage7_cas_prefix_likelihood_20260517.json` | `33971f02017af364aa60a0d865eb8af441c045cd0efdb5a6aefa9ffd781f91ea` |
| Stage 7.CPL2 full eta-to-epsilon report | `stage7_cas_prefix_full_loop_20260517.json` | `b69a22f06c6c66d6fc1266d257a4f0699c35ce4f562d093a383fedaecbc1140a` |
| Stage 7.CPL3 short generation report | `stage7_cas_prefix_generation_20260517.json` | `001d1df6b6f2490e87b7bdd859f2cfd886d09efc63363e27e7f7256aad96900e` |
| Stage 7.CPL4 text judge report | `stage7_cas_prefix_generation_text_judge_20260517.json` | `51eb8ba54dbc7a3d1183d0e56f723d8c802af42a49ac5673612a083199a6b51b` |

## Claim Matrix

| Claim | Status | Evidence Supporting It | Evidence Blocking / Limiting It | Allowed Language |
|---|---|---|---|---|
| Stage 7 maps 28 as original TKS seven Foundations x four Worlds/Register positions. | Supported | Source PDF plus `docs/reference/tks_28_foundations_translation_key.md`; fixture labels `F1T..F7E`. | Translation is a CAS v7.5 operational mapping, not a metaphysical endorsement of TKS framing. | "Stage 7 operationalizes the original 28 Foundations as Drive x Register positions." |
| The Stage 7 fixture is frozen, balanced, and validation-clean. | Supported | 4,368 rows; 156 rows per label; train/val/test = 1,344/672/2,352; validator reports 0 errors and 0 warnings. | Synthetic role-bound fixture, not a natural web benchmark. | "The experiment uses a frozen, balanced, role-bound Foundation fixture." |
| Pythia hidden states carry the full 28-Foundation signal beyond text baselines. | Supported | Stage 7.0 `focus_token` layer 6: test acc `0.7857`; best text `0.4966`; lift `+0.2891`; McNemar p `2.66e-95`. | Text baseline still performs far above chance. Fixture has learnable wording. | "The activation readout materially beats strong text-only baselines." |
| The 28-way signal is not explained by strongest surface metadata alone. | Supported | Strongest metadata baseline `0.6667`; activation `0.7857`; lift `+0.1190`; paired p `4.38e-20`. | Metadata can still narrow the problem because pair/focus structure is visible. | "The activation readout beats both text and the strongest surface metadata baseline." |
| The full 28-Foundation subspace is causal for the CAS readout. | Supported | Stage 7.1: removing the trained rank-27 subspace drops readout from `0.7857` to exact chance `0.0357`; 30 same-rank random complement removals produce `0.0` mean/max disruption; empirical p `0.0323`. | This is causality for the trained CAS readout, not for Pythia generation. | "Removing the Foundation subspace collapses the CAS readout to chance while random removals do not." |
| Drive is a strong factor inside the 28-Foundation result. | Supported | Stage 7.2 Drive: activation `0.8907`; best text `0.6679`; lift `+0.2228`; p `1.13e-73`; ablation to exact chance `0.1429`; rank 6. | Drive evidence remains fixture-bound and Pythia-160M-bound. | "Drive is readable beyond text and causal for the Drive readout." |
| Register is a clean beyond-text factor in this fixture. | Not supported | Register readout is real: activation `0.8563`; ablation to exact chance `0.2500`. | Best text baseline reaches `0.8971`, beating activation by `+0.0408`; metadata reaches `1.0000`. | "Register is real as a readout but text-explained in this fixture." |
| The full Drive x Register interaction is the strongest Stage 7 internal signal. | Supported | Full interaction repeats Stage 7.0/7.1: activation `0.7857` vs text `0.4966`, metadata `0.6667`; ablation to `0.0357`. | Rank 27 is broad; generation hooks may cause collateral damage or route nowhere. | "The full 28-way interaction is the strongest readout-level signal." |
| Drive removal controls generated language under localized ablation. | Not supported | Stage 7.3 no-hook reproducibility is exact; Drive hook was properly localized and used Drive-contrast rows only. | Drive removal mean token match `0.9301`; random removals are more disruptive at `0.8863`; extra divergence `-0.0438`; empirical p `1.0`; paired sign p `1.0`. | "The Drive generation hook did not beat random controls." |
| Late-layer additive hidden-state steering works on Pythia-160M. | Not supported | Stage 7.LA tested layer 10/11 additive Drive directions and Embodied-only `|E`. | Best all-register condition p `0.258`; best Embodied condition p `0.194`; both fail random-control gates. | "Late-layer additive steering did not clear controls on Pythia-160M." |
| Raw CAS symbols condition Pythia. | Not supported | Raw-prefix controls were included in CPL and CPL2. | CPL2 raw prefixes stay flat: `gold_raw` delta `-0.0032`, `probe_raw` delta `-0.0011`, `partner_raw` delta `+0.0294`. | "Pythia does not appear to understand raw CAS notation in this setup." |
| Readable CAS realization prefixes condition Pythia's semantic likelihood. | Supported | CPL: gloss/plain readable prefixes move likelihood strongly while wrong partner prefixes move opposite. CPL2 closes the loop: Pythia hidden state -> probe label -> readable prefix -> likelihood shift. Probe-readable delta `+0.2828`; wrong partner delta `-0.4000`; `81/112` positive cases. | This is likelihood-space conditioning through ordinary text attention, not internal hidden-neuron steering. | "CAS Harness can read a Foundation label and realize it as readable context that moves Pythia's semantic likelihood." |
| Probe-predicted readable prefixes produce pass-clean visible generated text. | Not supported / suggestive only | CPL3 has directional shape: probe-readable delta `+0.071`, wrong-partner delta `-0.161`, key margin `+0.2321`. | CPL3 misses the pre-set `+0.25` floor. CPL4 independent text judge is not clean: Drive judge reliability `0.6679`; probe-readable margin minus partner `-0.0103`. | "Visible generation shows directional hints, but the generated-text tier remains exploratory." |
| The eta-to-epsilon bridge is the product mechanism for CAS Harness. | Supported as a bounded mechanism | Eta: hidden states -> CAS readout. Epsilon: CAS readout -> readable realized context. CPL2 connects them end to end and passes. | It is external harness conditioning, not proof that the host model natively reasons in CAS or that CAS controls all output behavior. | "The harness mechanism is read, realize, condition; not hidden-state surgery." |
| CAS has solved the black-box problem. | Not supported | Stage 7 opens a verified internal readout channel. | It does not expose every internal cause, every neuron, or generation control. | "CAS reduces opacity for this tested signal; it does not fully solve the black-box problem." |
| Glass House AI is validated across models. | Not tested | Pythia-160M is the first open-model subject. | No OLMo/Qwen/Llama replication yet. | "This is a first open-model result, not cross-model validation." |

## Evidence Ladder

| Tier | Question | Current Answer |
|---|---|---|
| Dataset | Is the test frozen, balanced, and auditable? | Yes. |
| Axis | Is 28 correctly defined for this experiment? | Yes: Foundation x Register, not Drive x Domain. |
| Readout | Can CAS recover the full Foundation label from hidden states? | Yes. |
| Baseline | Does the full readout beat text-only classifiers? | Yes. |
| Metadata | Does the full readout beat the strongest surface metadata baseline? | Yes. |
| Readout causality | Does removing the subspace break the CAS readout? | Yes. |
| Factorization | Do Drive and Register behave differently? | Yes. Drive passes; Register is text-explained. |
| Internal generation causality | Does Drive removal affect generated language above random controls? | No. |
| Hidden-state steering | Do late-layer additive directions steer output above controls? | No. |
| Readable realization bridge | Can CAS read a Foundation label and feed it back as readable context that moves likelihood? | Yes. |
| Visible generated-text quality | Does that bridge produce pass-clean short generated text? | Not yet. CPL3/CPL4 are directional/negative. |
| Semantic steering | Can CAS directly steer open-ended output toward a chosen Drive/Foundation? | Not shown. |
| Cross-model generality | Does this hold across open models? | Not tested. |

## What Changed From Stage 6

Stage 6 proved the project should not stop at a failed generation hook.
The noetic path looked weak until the experiment was reframed:

- newline-token trap was caught
- lacunarity-style reread exposed weak/wrong-direction noetic slots
- fractal classification suggested oscillatory, not cleanly stabilizing,
  trajectories
- the original-TKS 28 Foundations supplied a more factorized axis

Stage 7 validates that redesign at the readout level:

- full 28-way readout is much stronger than the earlier raw noetic route
- Drive is clean and compact
- Register is visible in text and must not be overclaimed
- hidden-state generation hooks still fail
- readable realization succeeds in likelihood space

The lesson is not "give up." The lesson is:

> Eta is not epsilon. A failed hidden-state generation hook is a diagnostic: it
> tells us the current readout/intervention direction is not the route Pythia
> uses for next-token generation. The successful route is to read the structure,
> realize it as readable context, and condition the model through attention.

## Reviewer Playbook

1. Verify the Stage 7 fixture SHA:
   `3e4a1aca9f168a190116578b0b4fdb5bab633232ba06902039b233e589121250`.
2. If the RunPod/local activation artifact is available, verify:
   `d2fc03ad2572f49f8cfbb79898b074fc4c552502fe62bc62a4427963ab67c47f`.
3. Inspect Stage 7.0:
   `STAGE7_FOUNDATION_PILOT_REPORT_20260517.md`.
4. Inspect Stage 7.1:
   `STAGE7_FOUNDATION_ABLATION_REPORT_20260517.md`.
5. Inspect Stage 7.2:
   `STAGE7_FACTOR_CHECK_REPORT_20260517.md`.
6. Inspect Stage 7.3:
   `STAGE7_DRIVE_GENERATION_REPORT_20260517.md`.
7. Inspect Stage 7.CPL2:
   `STAGE7_CAS_PREFIX_FULL_LOOP_20260517.md`.
8. Inspect Stage 7.CPL3/CPL4:
   `STAGE7_CAS_PREFIX_GENERATION_20260517.md` and
   `STAGE7_CAS_PREFIX_GENERATION_TEXT_JUDGE_20260517.md`.
9. Confirm the claim boundary:
   internal readout, readout causality, factorization, and likelihood-space
   readable-prefix conditioning are supported; hidden-state steering and
   pass-clean visible generation control are not.

## Stakeholder Language

Use this:

> "CAS found a 28-Foundation signal inside an open model. The signal beats
> text-only baselines, beats the strongest surface metadata baseline, and the
> CAS readout collapses to chance when the signal is removed. That is evidence
> for a real internal readout channel. When CAS realizes that readout as
> readable context, Pythia's semantic likelihood moves toward the intended
> continuation."

Use this:

> "Drive is the strongest factor so far: it beats text and metadata, and
> removing the Drive subspace collapses the Drive readout to chance. Register
> is real but text-explained in the current fixture."

Use this:

> "The harness bridge is read, realize, condition. It is not a claim that raw
> CAS symbols work, or that CAS can directly edit Pythia's hidden neurons into
> producing arbitrary text."

Do not use this:

> "CAS reads Pythia's thoughts."

Do not use this:

> "CAS solved the black box."

Do not use this:

> "CAS can control Pythia's generated language."

Do not use this:

> "Pythia understands CAS notation."

## Next-Route Boundary

The next experiment should not be another unmodified ablation hook. Stage 7.3,
7.OA, and 7.LA already tested that route and failed. Stage 7.CPL2 shows the
productive route is the CAS Harness eta-to-epsilon bridge.

Allowed next routes:

1. **Theory/method roundtable first.** Re-read CAS/TKS internals, linear algebra,
   control theory, information geometry, and mechanistic interpretability before
   writing new code.
2. **Better generated-text evaluation only if pre-registered.** CPL3/CPL4 did
   not close visible generation. Any retry needs a stronger scoring design
   before generation runs.
3. **Cross-model eta-to-epsilon replication.** The next product-relevant gate is
   whether CPL2 repeats on Pythia-1B/2.8B or another open architecture.
4. **Fresh fixture if needed.** If cross-model likelihood repeats but visible
   text remains weak, build a fixture where generated continuation naturally
   requires the target Drive.

## Current Bottom Line

The honest Stage 7 result is strong and bounded:

> CAS does not open the whole black box. It opens a verified readout channel:
> the original-TKS 28-Foundation structure can be found inside Pythia-160M,
> shown to beat text and metadata baselines, decomposed into factors, and
> removed from the CAS readout. The hidden-state generation route did not pass.
> The eta-to-epsilon CAS Harness route did pass in likelihood space: CAS reads a
> Foundation label, realizes it as readable context, and Pythia's semantic
> likelihood moves in the intended direction. Visible generated text remains the
> open tier.

The work continues from that boundary.
