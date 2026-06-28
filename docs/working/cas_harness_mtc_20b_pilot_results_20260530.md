# CAS Harness MTC 20B Pilot Results - 2026-05-30

## Plain-English Bottom Line

This run did **not** prove CAS specificity.

It also does **not** kill the CAS Harness project.

What it proved is narrower and important: the new marker-balanced MTC pilot fixture did not make the CAS labels recoverable from GPT-NeoX-20B hidden states. If CAS itself is not recoverable on a fixture, then CAS cannot beat a matched taxonomy on that fixture. The correct next move is to treat this pilot fixture/configuration as a null and redesign the MTC fixture before claiming specificity.

## What Was Actually Run

Model: `EleutherAI/gpt-neox-20b`

Captured activations:

- 40E fixture: `1000 x 44 x 6144`
- F28 fixture: `700 x 44 x 6144`
- Max token lengths: 40E `406`, F28 `343`
- No truncation against the `max_length=768` capture setting.

Pilot reports copied locally:

- `C:\tmp\cas-harness-mtc-20b-20260530\mtc_40e_20b_layer20_smoke_report_20260530.json`
- `C:\tmp\cas-harness-mtc-20b-20260530\mtc_f28_20b_layer20_smoke_report_20260530.json`
- `C:\tmp\cas-harness-mtc-20b-20260530\mtc_cas_only_layer_sweep_20260530.json`

Local SHA256:

- 40E layer-20 smoke: `FC11A5340C01643E6989F093252E1E905CBFCB23A7E257CA746F9DAC40385FE5`
- F28 layer-20 smoke: `D2E22B217F4EF0361F0D1932B546973C6B472F321DB0A39D7E0E9CE3A631BE2B`
- CAS-only layer sweep: `FBBA93EF626AACB9C62B8FE6E49FB86CDABF2AE90E094F5AFE7022C4158320E2`

## Results

### 40E Smoke

- CAS 40E hidden readout: `5.5%`
- Text baseline: `2.5%`
- Lift over text: `+3.0 pp`
- Chance for 40-way classification: `2.5%`
- Verdict from runner: `FALSIFY`

Plain English: CAS barely beat chance on this fixture. That is not enough. The pre-registered lift gate required `+20 pp`.

### F28 Smoke

- CAS F28 hidden readout: `0.0%`
- Text baseline: `0.0%`
- Lift over text: `0.0 pp`
- Chance for 28-way classification: `3.57%`
- Verdict from runner: `FALSIFY`

Plain English: F28 did not recover at all in this smoke.

### CAS-Only Layer Sweep

The layer sweep checked all 44 GPT-NeoX-20B layers for CAS recoverability on the new marker-balanced fixtures.

- Best 40E layer: layer `20`, accuracy `5.5%`
- Best F28 layer: layer `0`, accuracy `3.57%`, macro-F1 `0.00246`

Plain English: the problem was not just choosing the wrong layer. Across the stack, this pilot fixture did not expose the CAS signal.

## What This Means

Do not present this as:

- "CAS failed universally."
- "20B disproves CAS."
- "Matched taxonomy control is closed."
- "CAS specificity is falsified globally."

The correct wording is:

"The first marker-balanced 20B MTC pilot failed because CAS itself was not recoverable on that fixture. This is a fixture/configuration null, not a global CAS null. The MTC gate remains open until a fixture recovers CAS above the pre-registered readout gate and then tests whether CAS beats matched alternatives."

## Why This Happened

The marker-balanced fixture fixed the earlier text-leakage problem by showing all cue definitions in every prompt and cycling the selected marker independently of class.

That did its job against surface text leakage, but it appears to have overcorrected: the prompt became too uniform and cue-card-like, so the model did not encode the intended CAS distinction strongly enough for the probe to recover it.

Metaphor:

- The old fixture put the answer too visibly on the page.
- The new fixture hid the answer so hard that the model may not have had a real reason to internally represent it.
- The correct fixture must do the middle thing: no visible label shortcuts, but still real scenario content that naturally requires the target CAS distinction.

## Methodology Rule Added

For future MTC runs:

1. A fixture must pass the text-baseline ceiling: text-only classifier `<= 60%`.
2. A fixture must also pass the CAS recoverability floor before matched controls matter:
   - 40E: CAS hidden readout must beat text by at least `+20 pp`.
   - F28: CAS hidden readout must beat text by at least `+20 pp`.
3. If CAS recoverability fails, stop. Do not interpret matched-taxonomy comparison. The fixture is not valid for specificity testing.

## Next Move

Build MTC v2 fixture using ordinary concrete scenarios, not source-vocabulary labels and not marker cue cards.

Requirements:

- No direct TKS source nouns as class anchors.
- No visible class badges.
- No fixed cue-card marker list shown in every prompt.
- Use concrete situations that require the CAS distinction by meaning.
- Keep lexical distractors and balanced splits.
- Re-run text-baseline diagnostic before GPU capture.
- Only capture 20B activations if text baseline stays `<= 60%`.

## V2 Generator Gate-One Attempt

Status: partially fixed; still blocked for matched-taxonomy specificity.

The first concrete-scenario generator attempt produced balanced 40E/F28 files, but the text-only diagnostic still reached `100.00%` on both CAS labels and matched-control labels:

- 40E fixture: `mtc_v2_concrete_40e_pilot_20260530.json`
- 40E diagnostic: `mtc_v2_concrete_40e_pilot_text_baseline_20260530.json`
- F28 fixture: `mtc_v2_concrete_f28_pilot_20260530.json`
- F28 diagnostic: `mtc_v2_concrete_f28_pilot_text_baseline_20260530.json`

Cause: the generator used stable class-specific phrases in prompt text. Examples include per-operator, per-domain, per-drive, and per-register request phrases that repeat across train/test. A text classifier can learn those phrases as answer keys.

Decision: do not capture these first v2 fixtures on RunPod. Patch the generator so surface phrase families are not reusable class labels, regenerate, and rerun the text-baseline gate.

## V2 Generator Patch-One Result

Status: CAS text leakage fixed; matched-control text leakage still blocked.

Regenerated fixtures:

- 40E fixture SHA: `760e3b8e3050e5e275f66f3d0729ab33eec161963a879d0835785f97c59e08c6`
- F28 fixture SHA: `762d774ec0e598e0a764c632ea48b7fbd51d317340c187fcc5388d7a8f111e76`

Text baseline:

- CAS 40E: `1.00%`
- CAS F28: `1.43%`
- Matched control NC40: `100.00%`
- Matched control NC28: `100.00%`

Interpretation:

The CAS side now passes the surface-text leakage gate. The control side still fails because the prompt surface visibly carries topic/frame/function labels that the matched-control taxonomy uses.

This means the patched v2 fixtures may be usable for a **CAS recoverability pilot** after review, but they are not yet valid for the **matched-taxonomy specificity gate**. A proper specificity fixture must make the non-CAS control labels non-trivial too, or it must derive matched-control labels from reviewer annotations that are not directly visible as topic/function words in the prompt.

## V2 Generator Patch-Two Result - Full 20B Capture

Status: Gate 1 passed; Gate 2 failed. Do not proceed to specificity claims on this fixture.

Patch-two decoupled visible scenario wording from both CAS labels and matched-control labels. That fixed the surface-text leakage gate for both sides:

- CAS 40E text baseline: `1.50%`
- Matched NC40 text baseline: `2.50%`
- CAS F28 text baseline: `0.71%`
- Matched NC28 text baseline: `2.14%`

Corrected fixture SHA256:

- 40E fixture: `B6AA3B9693F4C30CF245A092CB98788BE3E133E6860EBA1F911972324ACF925A`
- F28 fixture: `8513DEF96F1DBCA7B2B36D820EF9BA06E3AE6488275A234561707B6729973FF5`

Captured GPT-NeoX-20B activations on RunPod:

- 40E dataset: `/workspace/cas-harness-large-eval/datasets/gpt_neox_20b_mtc_v2_concrete_40e_pilot_20260530_layers_0_43.npz`
- 40E dataset SHA256: `ce4226af7bd481a9e76c84b25ff678427b3edd2fddd89c69c12a1c84f48401e7`
- F28 dataset: `/workspace/cas-harness-large-eval/datasets/gpt_neox_20b_mtc_v2_concrete_f28_pilot_20260530_layers_0_43.npz`
- F28 dataset SHA256: `d996c71eb5d031c494ce26a4199372d7b10a108dbd984994c826cbebbd7fa6ad`

Recoverability reports copied locally:

- `C:\tmp\mtc_v2_40e_20b_recoverability_20260530.json`
- `C:\tmp\mtc_v2_f28_20b_recoverability_20260530.json`
- `C:\tmp\mtc_v2_40e_capture_20260530.log`
- `C:\tmp\mtc_v2_f28_capture_20260530.log`

Report SHA256:

- 40E recoverability report: `ac5ee5cdd8e241c9d33b3db054d536e59117e4cabede4ba4dae52c903e387d01`
- F28 recoverability report: `c9cf387276f32c2f37e0beaf15d83d3c49927566b43af2966b117186f1c8ee4f`

### 40E Patch-Two Recoverability

- Best layer: `18`
- Hidden readout accuracy: `5.50%`
- Hidden readout macro-F1: `5.314%`
- Text baseline accuracy in runner: `4.50%`
- Text baseline macro-F1: `3.907%`
- Lift over text: `+1.00 pp`
- Required lift gate: `+20.00 pp`
- Verdict: `FALSIFY`

Plain English: the fixture no longer leaks the answer through text, but GPT-NeoX-20B hidden states do not recover the CAS 40E distinction on this fixture. The readout is near chance and far below the gate.

### F28 Patch-Two Recoverability

- Best layer: `3`
- Hidden readout accuracy: `5.036%`
- Hidden readout macro-F1: `4.655%`
- Text baseline accuracy in runner: `2.878%`
- Text baseline macro-F1: `2.792%`
- Lift over text: `+2.158 pp`
- Required lift gate: `+20.00 pp`
- Verdict: `FALSIFY`

Plain English: F28 is slightly above its text baseline but still nowhere near the recoverability floor. This fixture cannot test whether CAS is cleaner than matched alternatives.

### Patch-Two Interpretation

The v2 patch-two fixture solved the obvious leakage problem but failed the CAS recoverability floor. That means the fixture is too semantically decoupled from the CAS labels to serve as a specificity test.

Do not say:

- "CAS failed on 20B."
- "CAS specificity is falsified."
- "Matched taxonomy controls beat CAS globally."

Say:

"The leakage-controlled v2 concrete fixture did not make CAS recoverable from 20B hidden states. This is a fixture-design null. Matched-taxonomy specificity remains open and must be rerun on a human-reviewed fixture where CAS labels are meaningfully grounded without being visible as text shortcuts."

Next fixture requirement:

The labels cannot be arbitrary metadata decoupled from the scenario. The prompt must be plain English and non-leaky, but the scenario meaning must still genuinely require the target TKS/CAS distinction. That likely requires a smaller human-reviewed seed set before expansion.

## Stage LSA Next Gate

Do not jump straight to v2.5 fixture generation.

The v1 to v2 collapse opened a fork:

- v2 may have over-corrected and destroyed legitimate CAS meaning.
- Or v1's detection lift may have been substantially carried by surface leakage.

The next gate is Stage LSA: Leakage-vs-Signal Adjudication.

Prereg draft:

- `docs/working/cas_harness_leakage_signal_adjudication_prereg_20260530.md`

Load-bearing correction in v0.2:

- Arm A: v2 notation-stripped items.
- Arm B: original v1 items with the same strip operation applied.

Arm B is the direct test. If stripped v1 remains recoverable by CAS-competent judges, v2 over-corrected. If stripped v1 also fails, v1 detection-lift claims must be caveated as surface-carried pending re-derivation.
