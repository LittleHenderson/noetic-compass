# CAS Probe — Pythia interpretability experiment (research-only)

**Status:** research, not production. **DO NOT** import anything in this
directory from `api/`, `cas-native/`, `dashboard/`, or any production stack.

## Purpose

Test the central pitch of CAS Mode 7 against a fully-open language model:

> When a language model processes English text, are CAS structural axes
> (noetic, domain, register, drive) detectably present inside the model's
> internal activations — not just on its output?

If yes, CAS gives us a real interpretability handle on any open model.
If no, the CAS framing requires explicit training to surface, and the
"Mode 7 as anti-black-box" pitch needs revision.

Two tests:

1. **Detection (Stage 2).** Train a small linear classifier (a probe) to
   read CAS axis labels from Pythia hidden states. Beating chance is
   **not** enough on its own — the labels could be recoverable from the
   English text alone. The probe must also reliably beat plain-text
   baselines (TF-IDF, count-vector) by at least 5 percentage points
   with a McNemar p < 0.05 on the paired discordant samples. See the
   revised decision gates below.
2. **Causal influence (Stage 3, gated on Stage 2).** Mess with the
   detected direction inside Pythia (turn it down, scramble it) and see
   if the output changes. If yes, the structure is not just there — it's
   load-bearing. This is a different kind of evidence (causal, not
   discriminative) and remains worth running even when Stage 2 lands at
   `LABELS_RECOVERABLE_MOSTLY_FROM_TEXT`.

## Isolation guardrails (user-ratified 2026-05-15)

This directory is sandboxed. Hard rules:

1. **Branch:** all work on `experiment/cas-probe-pythia`. Never merged to
   `master` without separate audit + explicit user approval.
2. **Directory:** code lives ONLY under `research/cas_probe/`. No Pythia
   imports anywhere else.
3. **Production isolation:** no Pythia imports in `api/`, `dashboard/`,
   `cas-native/` loader, chat REPL, or training stack. Pythia is the
   test subject, not part of CAS Native.
4. **Frozen labels:** the probe never reads live Wave 2.5 / Wave 3
   corpus files. It uses a frozen snapshot named
   `pythia_probe_labels_YYYYMMDD.jsonl` with a companion manifest
   (sha256, source files, record count, extraction rules).
5. **Naming:** all artifacts prefixed `pythia_` or marked
   `research_only`.
6. **Failure protocol:** if the experiment fails or is abandoned, delete
   this branch and the artifacts cleanly. CAS Native is untouched.

The key invariant: **Pythia never becomes CAS Native. It is the test
subject. CAS is the measuring instrument.**

## Stages

| Stage | Status | Deliverable |
|---|---|---|
| 1.0 | done | `README.md`, `build_pythia_probe_snapshot.py`, frozen labels jsonl, manifest |
| 1.1 | done | Pythia-160M activation capture script + smoke test |
| 2 | done | per-layer linear probe training |
| 2.1 | done | TF-IDF baseline, shuffled-label control, val-selected headline, confusion matrix |
| 2.2 | done — labels recoverable, mostly text-baseline explained | majority / stratified / count-vector baselines, paired contingency, McNemar test |
| 3 | done — narrow newline-token test | ablation of noetic subspace; sanity gate passed (probe acc 0.899 → 0.101); immediate next-token argmax unchanged on 69/69 prompts, but all top tokens were newline |
| 3.1 | done — continuation effect present | forced semantic continuations; first-step top-1 changes in 30/207 cases; full 8-token continuation changes in 157/207 cases |
| 3.2 | done — mixed specificity evidence | clean RunPod GPU rerun on RTX A6000 (`cuda`, 147 sec); first-token specificity fails (diag 0.079 vs off-diag 0.062), but 8-token match shows weak same-class disruption (diag match 0.659 vs off-diag 0.738). Verdict: `MIXED_SPECIFICITY_EVIDENCE`. |
| 3.2-control | **done — suggestive control passed** | random orthogonal control on RTX A6000 (140 sec); random arm mean disruption −0.009 (t=−0.24, p=0.82), noetic arm +0.079 (t=2.56, p=0.031); Welch noetic-vs-random t=1.82 (p=0.086, borderline). Verdict: `NOETIC_EFFECT_SUGGESTIVE_CONTROL_PASSED`; no full direction-meaningful upgrade until the direct comparison passes. |
| 3.3 | **done — n=30 permutation control passed** | 30 random orthogonal complement directions on RTX A6000 (389 sec), sampled into 10-direction matched null sets with 10,000 permutations. Noetic mean disruption +0.0787 vs random null mean +0.0002; null p95 +0.0352; one-sided permutation p=0.0003. Verdict: `NOETIC_EFFECT_DIRECTION_MEANINGFUL_N30_PERMUTATION`. |

| 4.0 | **done - cross-axis probe screen** | Domain/register/drive probes trained from the same activation file. Domain shows the strongest breadth signal (layer 5 test 0.810 vs text 0.730, lift +0.079, McNemar p=0.267). Register is weak (test 0.333, below stratified dummy 0.370). Drive is modest and mostly text-explained (test 0.324 vs text 0.294, lift +0.029). |
| 4.1 | **done - domain ablation negative** | Domain layer-5 ablation with 30 random-complement directions and 10,000 matched permutations. Domain mean disruption +0.0142 vs random null p95 +0.0396; p=0.2931. Probe self-ablation also failed for O (kept-rate 1.000). Verdict: `DOMAIN_EFFECT_NOT_ABOVE_RANDOM_N30_PERMUTATION`. |
| 5.0 | **done - original TKS dog-training noetic transfer smoke** | Ten hand-authored dog-training examples from the original TKS noetic demonstration, corrected to CAS zero-indexed numbering (`^0` Idea, `^1` Mind, ..., `^9` Below/Effect). Layer-3 noetic probe gets 4/10; best layer gets 6/10; count-vector text baseline gets 4/10; TF-IDF gets 2/10. Verdict: `TKS_DOG_TRANSFER_MIXED`. |
| 5.1 | **done - multi-scenario TKS-style transfer smoke** | Dog training plus four definition-anchored hand-authored scenarios (debate prep, lost keys, software debugging, gallery viewing), 50 rows total. Layer-3 noetic probe gets 16/50; best layer gets 23/50; count-vector gets 11/50; TF-IDF gets 16/50. Verdict: `TKS_NOETIC_TRANSFER_MIXED`. |
| 5.2 | **done - paraphrase-controlled TKS-style transfer smoke** | 60 rows: 10 noetics x 6 paraphrase styles. Layer-3 noetic probe gets 29/60; best layer gets 31/60; count-vector gets 16/60; TF-IDF gets 25/60. Probe beats count-vector reliably (paired p=0.007) but not TF-IDF (paired p=0.481). Verdict: `TKS_NOETIC_TRANSFER_MIXED`, suggestive but not clean pass. |
| 5.3 | **done - targeted `^6` Male diagnostic** | 48 rows: 30 Male probes plus 18 contrast controls. Layer-3 gets only 7/30 Male rows. All 7 hits come from training-alias language (`breaking down` / `unpacking` / `looking underneath`): 7/10. Corrected nested-composition language is 0/10, and no-alias plain composition is 0/10. Diagnosis: current probe learned the alias, not the full corrected `^6` concept. |
| 5.4 | **done - v2 noetic probe repair** | Built `pythia_probe_labels_v2_20260516.jsonl` (551 rows = 457 base + 94 augment rows) with corrected `^6` coverage and hard `^5`/`^6` contrasts. V2 fixes Male on held-out diagnostics: Stage 5.3 Male rows move 7/30 -> 29/30; Stage 5.2 Male moves 0/6 -> 6/6. Global transfer improves but remains mixed: Stage 5.2 headline 29/60 -> 38/60, still not reliably above TF-IDF. |
| 6.0 | **done - role-bound counterfactual pilot** | Built `stage6_role_bound_pilot_20260516.jsonl` (100 rows = 10 bundles x 5 noetic pairs x 2 focused roles) plus `validate_stage6_role_bound.py`. Validation passes with 0 errors and 49 expected pilot warnings. This proves the same-sentence/different-focus data shape and validator, not any probe claim. |
| 6.1 | **done - role-bound activation smoke** | Captured focus-token, final-token, and mean-pooled Pythia activations for the 100-row pilot. Mechanics smoke: focus-token layer 6 reaches 20/20 test rows vs best text baseline 10/20; metadata focus-only and layer-0 focus-token stay at chance. Follow-up tests pin terminal `Focus: A/B` token indexing. This is a pipeline signal only, not a claim-bearing result. |
| 6.2 | **done - full role-bound fixture locked** | Built `stage6_role_bound_full_20260516.jsonl` (3,000 rows = 60 bundles, 1,500 counterfactual pairs, 300 rows per noetic). Split is train 1,200 / val 400 / locked test 1,400. Validation passes with 0 errors and 653 expected review warnings; max token concentration is 0.5 and all >0.4 tokens are label-tied. No activation capture or probe claim yet. |
| 6.3 | **done - full activation capture** | Captured Pythia-160M focus-token, final-token, and mean-pooled activations for all 3,000 locked rows. Shapes: `X_focus`, `X_final`, `X_mean` all `(3000, 13, 768)`. Local artifact SHA is `6641e28519eefeadc66d053c4996075d640401f6f650ef14b80435ccd57206f2`. The binary is not committed because it is 217.9 MB and exceeds GitHub's 100 MB file limit; manifest/report are committed. |
| 6.4 | **done - full role-bound probe passes text gate** | First claim-bearing Stage 6 evaluation. Validation-selected headline is `focus_token` layer 5: val 0.9925, locked-test 0.7393. Best validation-selected text baseline is `tfidf_char_3_5`: locked-test 0.4643. Lift is +27.5 pp; paired McNemar p=8.14e-50. Focus-only metadata stays chance at 0.100. Verdict: `ROLE_BOUND_PROBE_RELIABLY_ABOVE_TEXT_BASELINE`. This is discriminative evidence only, not causal proof. |
| 6.5 | **done - layer-5 readout subspace ablation passes** | Causal intervention on the Stage 6.4 representation/readout, not generation. Removing the trained focus-token layer-5 noetic subspace drops locked-test readout accuracy from 0.7393 to 0.1000 chance; changed prediction rate 0.9007. Thirty same-rank random orthogonal removals produce 0.0 mean/max disruption; empirical p=0.0323. Verdict: `ROLE_BOUND_SUBSPACE_CAUSAL_FOR_PROBE_READOUT`. Next needed: live generation hook. |
| 6.6 | **done - generation hook subset negative** | Live Pythia generation hook on a 20-row locked subset (2 per noetic, 3 prompt templates, 3 random controls). Noetic removal changes continuations, but not more than same-rank random controls: noetic mean token match 0.667 vs random mean 0.587; noetic first-step KL 0.0255 vs random 0.0574. Verdict: `GENERATION_EFFECT_NOT_ABOVE_RANDOM_CONTROL`. Stage 6.4/6.5 still stand; no generated-language causal upgrade yet. |
| 6.6A | **done - localized generation hook numerical signal** | Fixed Stage 6.6's broad-hook issue by removing the subspace only at the original focus-token position. No-hook reproducibility was exact (1.000). Localized noetic removal changes generation slightly more than localized random controls: noetic mean token match 0.831 vs random mean 0.867, but only 3 random controls means empirical p=0.25. Verdict: `LOCALIZED_GENERATION_EFFECT_NUMERICALLY_ABOVE_RANDOM_CONTROL`, not a reliable pass. |
| 6.6C | **done - rank-1 localized hook negative** | Tested Claude's "wrong dimensionality" hypothesis by removing only the strongest noetic direction at the focus token. No-hook reproducibility was exact (1.000). Rank-1 noetic removal does not beat rank-1 random controls: noetic mean token match 0.885 vs random mean 0.883, empirical p=0.75. Verdict: `LOCALIZED_GENERATION_EFFECT_NOT_ABOVE_RANDOM_CONTROL`. Stage 6.6B remains the only unresolved generation closure test: full-subspace localized hook with `n_random >= 30` on GPU. |
| 6.6R | **done - paired re-analysis gray zone** | Re-analyzed 6.6A/6.6C using matched sample/template pairs instead of aggregate means. Full localized hook remains promising but underpowered: sample-level mean delta +0.0361, sign-flip p=0.1005, all 3 templates positive. Rank-1 remains null: sample-level mean delta -0.0028, p=0.5377. Decision: run full localized `n_random=30` on both the original 20-row subset and a fresh seeded holdout (`per_label=4`, 40 rows / 120 prompts, excluding old selected ids). |
| 6.6B | **done - generated-language causality blocked** | Ran full focus-token-localized noetic-subspace hook with `n_random=30` on A6000. Old subset fails: noetic match 0.902 vs random 0.888, extra divergence -0.0146, paired p=0.8006. Fresh seeded holdout is tiny positive but fails gates: noetic match 0.876 vs random 0.886, extra +0.0100, paired p=0.2932. Verdict: Stage 6 supports internal readout detection and readout-causal ablation, but not generated-language causality. |
| 6.CM | **done - claims matrix locked** | `STAGE6_CLAIMS_MATRIX_20260517.md` locks the evidence boundary before Stage 6.7: supported claims are hidden-state readout above text baseline and readout-causal subspace removal; unsupported claims are generated-language causality, full black-box solution, and cross-model Glass House validation. Includes Stage 6.7 pre-registration boundary for counterfactual focus-token patching. |
| 6.7 | **done - counterfactual patching negative** | Tested matched A/B focus-token activation patching on A6000. Smoke: 10 receivers, 30 cases, true patch directional score -0.125 vs random -0.079, p=1.0. Fresh confirmatory: 40 receivers, 120 cases, `n_random=30`, true patch directional score -0.0729 vs random -0.0646, extra -0.0083, p=0.6774. Verdict: matched counterfactual patching does not route generated language toward the donor role in this setup. |
| 7.P | **done - 28-Foundation preflight diagnostics** | Confirmed 28 = original TKS seven foundations x four worlds/registers, mapped as `F1T..F7E`; not Drive x Domain. Built a 4,368-row balanced pilot fixture and validator (0 errors, 0 warnings), but claims remain gated. Retrospective lacunarity-style gap map flags `^3` and `^5` as wrong-direction slots, but not uniquely (`^1`, `^4`, `^6` also weak). Existing CAS fractal classifier marks Stage 3.2 and fresh Stage 6.6B trajectories as `oscillatory`, while the older 20-row subset is `stabilizing`. See `STAGE7_PREFLIGHT_DIAGNOSTICS_20260517.md`. |
| 7.0 | **done - 28-Foundation pilot passes text gate** | Full Pythia-160M activation capture and locked-test probe on the 4,368-row original-TKS 28-Foundation fixture. Validation-selected headline is `focus_token` layer 6: val 0.9985, locked-test 0.7857, macro-F1 0.7906. Best validation-selected text baseline is `tfidf_char_3_5`: locked-test 0.4966. Lift is +28.9 pp; paired McNemar p=2.66e-95. Strongest surface-metadata baseline is 0.6667; activation still beats it by +11.9 pp, p=4.38e-20. Verdict: `FOUNDATION_PROBE_RELIABLY_ABOVE_TEXT_BASELINE`. This is discriminative hidden-state readout evidence only; no generation-control claim. See `STAGE7_FOUNDATION_PILOT_REPORT_20260517.md`. |
| 7.1 | **done - 28-Foundation readout ablation passes** | Causal intervention on the Stage 7.0 readout, not generation. Removing the trained `focus_token` layer-6 28-Foundation subspace drops locked-test readout accuracy from 0.7857 to exact chance 0.0357, with 95.6% changed predictions and collapse to one label (`F6A`). Thirty same-rank random complement removals produce 0.0 mean/max disruption; empirical p=0.0323. Verdict: `FOUNDATION_SUBSPACE_CAUSAL_FOR_PROBE_READOUT`. See `STAGE7_FOUNDATION_ABLATION_REPORT_20260517.md`. |
| 7.2 | **done - factor check mixed** | Split the Stage 7 signal into Drive, Register, and full 28-way interaction using the locked `focus_token` layer 6 readout. Drive passes: activation 0.8907 vs best text 0.6679 (+22.3 pp, p=1.13e-73), ablation drops to exact chance 0.1429. Register is causal but text-explained: activation 0.8563 vs text 0.8971, ablation drops to exact chance 0.2500. Full interaction repeats the Stage 7.0/7.1 pass: activation 0.7857 vs text 0.4966, ablation to 0.0357. Verdict: `STAGE7_FACTOR_CHECK_MIXED`. See `STAGE7_FACTOR_CHECK_REPORT_20260517.md`. |
| 7.3 | **done - Drive generation hook negative** | Focus-token-localized Drive-subspace removal during greedy generation on 28 fresh Drive-contrast test rows (4 per Drive), 3 forced continuation templates, 30 same-rank random controls. No-hook reproducibility is exact (1.0). Drive removal mean token match is 0.9301, while random removals are more disruptive at 0.8863; extra divergence is -0.0438, empirical p=1.0, paired sign p=1.0. Verdict: `DRIVE_LOCALIZED_GENERATION_EFFECT_NOT_ABOVE_RANDOM_CONTROL`. Stage 7 supports internal readout/readout-causal evidence, not generated-language control. See `STAGE7_DRIVE_GENERATION_REPORT_20260517.md`. |
| 7.CM | **done - claims matrix locked** | `STAGE7_CLAIMS_MATRIX_20260517.md` locks the evidence boundary: Stage 7 supports internal 28-Foundation readout, readout-causal ablation, and factorization evidence; it does not support generated-language control or semantic steering. Next-route boundary: no more unmodified ablation hooks; do a theory/method roundtable and pre-register any counterfactual routing or fresh-fixture experiment before running it. |
| 7.RT | **done - research roundtable next route** | `STAGE7_NEXT_ROUTE_ROUNDTABLE_20260517.md` integrates the CAS/TKS, mathematical, experiment-design, and skeptical-statistics reviews. Consensus: do not run another unmodified generation hook. Recommended Stage 7.4 is a fresh Drive forced-choice logit-margin fixture using the frozen layer-6 rank-6 Drive projection, with calibration gates, random/shuffled controls, cluster-aware statistics, and locked pass/fail thresholds. |
| 7.OA | **done - output-alignment diagnostics negative** | Ran Claude's free diagnostic before spending more GPU. The raw principal-angle test against Pythia's full unembedding row-space is degenerate because the unembedding is full hidden-rank (768/768). The useful rank-matched energy/logit-lens checks say the Stage 7 Drive and 28-way interaction subspaces are `OUTPUT_ALIGNMENT_NEAR_RANDOM`, not specially output-aligned. Verdict: `STAGE7_SUBSPACES_NOT_OUTPUT_ALIGNED_ABOVE_RANDOM`. This explains the layer-6 subtraction failure and argues against more layer-6 generation hooks. See `STAGE7_OUTPUT_ALIGNMENT_DIAGNOSTICS_20260517.md`. |
| 7.LA | **done - late-layer additive probe negative** | Tried Claude's fallback: layers 10/11, additive +/- alpha Drive directions, two-choice logit-margin scoring, random rank-1 controls. All-register run fails the exploratory gate; best condition layer 11 alpha -2 has extra signed margin +0.0488 but p=0.258 and positive share 0.179. Embodied-only `|E` run also fails; best condition layer 11 alpha +4 has extra +0.0440 but p=0.194 and positive share 0.357. Verdict: `EXPLORATORY_LATE_LAYER_ADDITIVE_NOT_ABOVE_RANDOM_GATE`. See `STAGE7_LATE_LAYER_ADDITIVE_PROBE_20260517.md` and `STAGE7_LATE_LAYER_ADDITIVE_PROBE_EMBODIED_20260517.md`. |
| 7.CPL | **done - readable CAS prefix likelihood bridge passes** | Tested the user's eta-to-epsilon / CAS-prefix hypothesis without relying on numbered-choice behavior. Raw CAS-symbol prefixes (`F#|R`) do not help: raw_correct delta -0.0200. Human-readable CAS realization prefixes do condition Pythia's semantic likelihood: gloss_correct delta +0.3573 with 77/112 positive cases; gloss_partner delta -0.3742; plain_correct delta +0.4839 with 90/112 positive cases; plain_partner delta -0.4662. Verdict: `READABLE_PREFIX_CONDITIONS_PYTHIA_LIKELIHOOD`. This supports a CAS Harness bridge, not internal-neuron steering. See `STAGE7_CAS_PREFIX_LIKELIHOOD_20260517.md`. |
| 7.CPL2 | **done - full eta-to-epsilon loop passes** | Closed the actual harness loop: Pythia hidden states -> Stage 7 Foundation probe prediction -> readable CAS realization prefix -> Pythia likelihood. Selected-row probe accuracy: Foundation 0.7857, Drive 0.8482. Probe-predicted readable prefix moves semantic likelihood: margin 0.2860, delta +0.2828 vs no prefix, 81/112 positive cases, sign p ~0; wrong partner readable prefix moves opposite (delta -0.4000). Raw probe/gold CAS symbols stay flat. Verdict: `PROBE_PREDICTED_CAS_PREFIX_CONDITIONS_PYTHIA`. This is the first pass-clean CAS Harness conditioning result. See `STAGE7_CAS_PREFIX_FULL_LOOP_20260517.md`. |
| 7.CPL3 | **done - short generation heuristic not clean** | Tested the full eta-to-epsilon harness loop in visible greedy continuations (`max_new_tokens=16`) using probe-predicted readable prefixes, wrong-partner readable prefixes, raw-symbol prefixes, and no-prefix controls. Selected-row probe accuracy is higher on this smaller 56-row slice: Foundation 0.8750, Drive 0.9286. Probe-readable prefixes move in the expected direction (target-win 0.125, margin +0.107, delta +0.071 vs none) and wrong-partner prefixes move opposite (target-win 0.054, margin -0.125), but the key probe-minus-partner margin is +0.2321, just under the pre-set +0.25 clean-pass floor. Raw symbols stay flat. Verdict: `PROBE_PREFIX_GENERATION_HEURISTIC_NOT_CLEAN`. CPL2 likelihood remains the load-bearing harness result; CPL3 is an exploratory generated-text smoke, not an open-ended generation-control claim. See `STAGE7_CAS_PREFIX_GENERATION_20260517.md` and `STAGE7_CAS_PREFIX_GENERATION_SAMPLES_20260517.md`. |
| 7.CPL4 | **done - generated-text judge not clean** | Trained independent text-only judges on the original Stage 7 fixture, then applied them to CPL3 generated continuations. The Drive judge selected `tfidf_char_3_5` but its own held-out test accuracy is only 0.6679, below the 0.70 reliability floor; Foundation judge is 0.4966. Probe-readable continuations have small positive deltas vs no-prefix (Drive +0.0256, Foundation +0.0202), but do not beat wrong-partner readable prefixes (Drive probe-minus-partner -0.0103; Foundation -0.0047). Verdict: `PROBE_PREFIX_GENERATED_TEXT_CLASSIFIER_SHIFT_NOT_CLEAN`. This formally keeps visible generation exploratory; CPL2 remains the load-bearing result. See `STAGE7_CAS_PREFIX_GENERATION_TEXT_JUDGE_20260517.md`. |
| 8.0 | **done - Pythia-1B CPL2 cross-scale replication passes** | Pre-registered in `STAGE8_CROSS_MODEL_GATES_20260517.md` before the run. Captured Pythia-1B layers 6-13 on the frozen 4,368-row Stage 7 fixture. Validation-selected layer is `focus_token` layer 8: val acc 1.0000, test acc 0.8240, test lacunarity 0.0152. CPL2 on the locked 112-row pack passes clean: probe-readable delta +0.5542 vs no prefix, Wilcoxon p=2.58e-14, probe-minus-partner margin +1.2460, 90/112 positive. Raw CAS-symbol prefixes remain flat/slightly negative. Verdict: `PASS_CLEAN_STAGE8_PYTHIA1B_CPL2_REPLICATES`. This supports cross-scale CAS Harness likelihood conditioning, not hidden-state steering or pass-clean visible generation. See `STAGE8_PYTHIA1B_SUMMARY_20260517.md` and `STAGE8_CLAIMS_MATRIX_20260517.md`. |
| 9.0 | **done - original TKS 40 Elements readout passes** | Pre-registered in `STAGE9_40_ELEMENTS_GATES_20260517.md`. Built a balanced 8,320-row role-bound fixture for the original TKS `A1..D10` 40 Elements: 4 worlds/domains x 10 noetics, 208 rows per element, no literal label/framework leakage in model-facing prompts. Pythia-160M activation capture completed on the pod; binary SHA `c70582b54f309c805fd90a69e7d23a80a714fc692aac4c1364ebc4e21b410cfb` is manifest-only, not committed. Validation-selected headline is `focus_token` layer 5: locked-test acc 0.8980, macro-F1 0.9088. Best text baseline `tfidf_char_3_5` gets 0.5009; best metadata `pair_focus` gets 0.5000. Lift over text is +39.7 pp, McNemar p=0. Verdict: `STAGE9_40_ELEMENTS_READOUT_PASS_CLEAN`. This supports a 40-slot hidden-state readout claim only; no steering or generation claim yet. See `STAGE9_40_ELEMENTS_PROBE_REPORT_20260517.md`. |
| 9.1 | **done - 40 Elements factorization + ablation full pass** | Pre-registered in `STAGE9_FACTOR_ABLATION_GATES_20260517.md`; locked to the Stage 9.0 validation-selected `focus_token` layer 5. Domain/World passes: acc 0.9230 vs text 0.7500, ablated to exact chance 0.2500, rank 3, random p=0.0323. Noetic passes: acc 0.9154 vs text 0.7500, ablated to exact chance 0.1000, rank 9, random p=0.0323. Full 40-way interaction passes: acc 0.8980 vs text 0.5009, ablated to exact chance 0.0250, rank 39, random p=0.0323. Verdict: `STAGE9_FACTOR_CHECK_FULL_PASS`. This is readout-level factorization/causality, not steering or generation control. See `STAGE9_FACTOR_ABLATION_REPORT_20260517.md` and `STAGE9_CLAIMS_MATRIX_20260517.md`. |
| 10.0 | **done - five CAS operators grey, readout-causal** | Pre-registered in `STAGE10_OPERATORS_GATES_20260517.md`. Built a balanced 6,000-row role-bound fixture for the five CAS generative operators, 1,200 rows per operator, no literal symbol/framework leakage in model-facing prompts. Pythia-160M activation capture completed on the pod; binary SHA `bf86393c0a922f714a68698d9133e108e0fac74f23ecc6cf0ac078f00d65abfc` is manifest-only, not committed. Validation-selected headline is `mean_over_seq_len` layer 0: locked-test acc 0.9918. Best text baseline `tfidf_char_3_5` gets 0.9557. Activation lift is +3.61 pp, McNemar p=3.21e-22; this misses the pre-registered +5 pp absolute-lift floor, so formal verdict is `STAGE10_OPERATORS_GREY`. Targeted rank-4 readout-subspace removal drops acc to exact chance 0.2000; random max disruption 0.0000, p=0.0323. Interpretation: strong readable/readout-causal operator signal, but isolated operator labels are ceiling-limited against text. See `STAGE10_OPERATORS_PROBE_REPORT_20260517.md` and `STAGE10_CLAIMS_MATRIX_20260517.md`. |
| 11.0 | **done - expression grammar-shape full pass** | Pre-registered in `STAGE11_EXPRESSION_SHAPES_GATES_20260517.md`. Built a balanced 9,000-row role-bound fixture for 10 existing Path D grammar shapes: state literal, binary composition, let binding, recipe, rpm chain, fractal sequence, cross-register omega, meta-logic relation, inversion, and diagram export. Model-facing text avoids literal labels, CAS notation, and formula symbols. Pythia-160M activation capture completed on the pod; binary SHA `ecc9c29c32ebc3e50993c9edc00ee4d894dd9b5096897f31fd497c3a1a3351ac` is manifest-only, not committed. Validation-selected headline is `final_token` layer 2: locked-test acc 0.9300, macro-F1 0.9312. Best text baseline `tfidf_char_3_5` gets 0.6443; best metadata baseline gets 0.6667. Lift over text is +28.6 pp, McNemar p=2.94e-227. Targeted rank-9 removal drops acc to exact chance 0.1000; random max disruption 0.0000, p=0.0323. Verdict: `STAGE11_EXPRESSION_SHAPES_FULL_PASS`. This supports expression-shape hidden-state readout and readout-causal subspace evidence, not formula solving or generation control. See `STAGE11_EXPRESSION_SHAPES_PROBE_REPORT_20260517.md` and `STAGE11_CLAIMS_MATRIX_20260517.md`. |
| 11.A | **done - readout coherence audit** | Refit the locked Stage 11 `final_token` layer-2 probe from the fixture and activation binary, reproduced the reported test accuracy exactly (0.9300), and emitted per-class examples for high-confidence corrects, low-confidence corrects, and high-confidence errors. Verdict: `COHERENT_WITH_ADJACENT_CONFUSIONS`. No class collapse; worst class is `fractal_sequence` at 0.8571. Largest confusions are structurally adjacent or hard-boundary cases: `fractal_sequence -> meta_logic_relation` (40), `let_binding -> meta_logic_relation` (37), `rpm_chain -> recipe` (35), and `state_literal -> binary_composition` (26). See `STAGE11_READOUT_COHERENCE_AUDIT_20260517.md` and `stage11_readout_coherence_audit_20260517.json`. |
| 12.0 | **done - compiler-validated equations/formulas full pass** | Pre-registered in `STAGE12_EQUATIONS_FORMULAS_GATES_20260517.md`. Built a balanced 9,000-row role-bound fixture for 10 compiler-supported formula/equation families: relation dependency, typed program, production recipe, yield query, state vector, emergent register assignment, membership assertion, cardinality assertion, finite set operation, and cover/partition formula. Every row stores a real compiler-valid `cas_formula` in metadata while model-facing text withholds raw CAS notation and internal labels. Pythia-160M activation capture completed on the pod; binary SHA `2a1b5ee2890bead1cd85761bba64f8f886b0a5ebedb6a487201e97ea5fa9116b` is manifest-only, not committed. Validation-selected headline is `final_token` layer 2: locked-test acc 0.8995, macro-F1 0.9037. Best text baseline `tfidf_char_3_5` gets 0.6393; best metadata baseline gets 0.6667. Lift over text is +26.0 pp, McNemar p=3.04e-176. Targeted rank-9 removal drops acc to exact chance 0.1000; random max disruption 0.0000, p=0.0323. Verdict: `STAGE12_EQUATIONS_FORMULAS_FULL_PASS`. This supports compiler-validated formula-family hidden-state readout and readout-causal subspace evidence, not raw-symbol parsing, formula execution, or generation control. See `STAGE12_EQUATIONS_FORMULAS_PROBE_REPORT_20260517.md` and `STAGE12_CLAIMS_MATRIX_20260517.md`. |

## Decision gates (revised post-audit 2026-05-16)

These are the stricter gates after Codex audit `6a7d657`. Beating
chance is necessary but **not sufficient**. To claim a model adds
structure beyond plain text we require BOTH:

- Pythia headline test accuracy minus best-text-baseline test
  accuracy **>= 5 percentage points**, AND
- McNemar's exact binomial test on the paired discordant pairs
  (Pythia-only-correct vs text-baseline-only-correct) **p < 0.05**.

Verdict tiers:

- `PROBE_RELIABLY_ABOVE_TEXT_BASELINE` — both criteria pass.
- `LABELS_RECOVERABLE_MOSTLY_FROM_TEXT` — headline beats chance but
  not text reliably. This is where Stage 2.2 lands.
- `PROBE_WEAKLY_ABOVE_CHANCE` — between chance and the 30% strong
  threshold.
- `NULL_RESULT` — at or below chance.

## Stage 2.2 headline result (2026-05-16, post-second-Codex-audit)

**Verdict: `LABELS_RECOVERABLE_MOSTLY_FROM_TEXT`.** No reliable
beyond-text lift is established yet.

The pre-Codex Stage 2 framing ("92.8% strong signal") and the Stage
2.1 framing ("Pythia adds +1.4 pp over text") were both too strong.
Codex's second audit `6a7d657` re-ran the paired contingency on the
same 69-sample test set:

- both correct: 59
- Pythia layer-3 only correct: **3**
- TF-IDF only correct: **2**
- both wrong: 5
- discordant total: 5
- McNemar exact binomial p (two-sided): **1.0000**

The +1.4 pp Pythia-over-TF-IDF gap reduces to **one net sample**
on the discordant set, which is indistinguishable from chance
imbalance. **The honest claim is that the noetic label is recoverable
from this corpus, but Pythia's mid-network does not add reliable
signal over plain text on this evidence.**

**Full baseline + headline table:**

| Source | Val acc | Test acc | macro-F1 |
|---|---:|---:|---:|
| Chance (1/10) | 0.100 | 0.100 | — |
| Majority class | 0.130 | 0.130 | — |
| Stratified random | 0.130 | 0.188 | — |
| Count-vector + LogReg | 0.855 | **0.884** | 0.882 |
| TF-IDF + LogReg | 0.841 | **0.884** | 0.882 |
| **Pythia layer 3 (val-selected)** | **0.899** | **0.899** | 0.902 |
| Shuffled-label control on layer 3 | 0.130 | 0.101 | — |

Notable: count-vector and TF-IDF tie at 0.884. TF-IDF re-weighting
adds nothing here. Lexical patterns in Claude's English do almost all
the work.

**Per-layer Pythia probe accuracies for the record:**

| Layer | Train | Val | Test | macro-F1 |
|---:|---:|---:|---:|---:|
| 0 (embed) | 1.000 | 0.855 | 0.884 | 0.886 |
| 1 | 1.000 | 0.884 | 0.913 | 0.912 |
| 2 | 1.000 | 0.884 | 0.913 | 0.912 |
| **3** ← headline (val) | 1.000 | **0.899** | 0.899 | 0.902 |
| 4 | 1.000 | 0.899 | 0.928 | 0.931 |
| 5 | 1.000 | 0.884 | 0.928 | 0.926 |
| 6 | 1.000 | 0.855 | 0.913 | 0.916 |
| 7 | 1.000 | 0.812 | 0.884 | 0.884 |
| 8 | 1.000 | 0.841 | 0.899 | 0.902 |
| 9 | 1.000 | 0.812 | 0.884 | 0.887 |
| 10 | 1.000 | 0.812 | 0.870 | 0.868 |
| 11 | 1.000 | 0.812 | 0.884 | 0.886 |
| 12 | 1.000 | 0.812 | 0.870 | 0.872 |

(Same per-layer numbers as Stage 2.1; only the interpretation changed.)

**Reserved-language verdict:**

> On this CAS-labeled English corpus (n=457, test n=69), a linear
> probe on Pythia-160M layer-3 hidden states recovers the noetic label
> at test accuracy 0.899 (macro-F1 0.902), vs a 10% chance baseline
> and a 0.130 majority-class baseline. TF-IDF and count-vector
> baselines on the same text both reach 0.884. The Pythia probe adds
> +1.4 pp over TF-IDF. The paired contingency table shows 59 both
> correct, 3 Pythia-only correct, 2 TF-IDF-only correct, 5 both wrong
> (discordant n=5). McNemar's exact binomial test on the discordant
> pairs gives p=1.0000. The shuffled-label control drops to 0.101,
> ruling out a split leak.
>
> Honest claim on current evidence: the noetic label is recoverable
> from this corpus, but the lift Pythia adds over a plain text baseline
> is NOT statistically reliable on this test size. No reliable
> beyond-text lift is established yet. Causal (ablation) and
> paraphrase-control tests are required before any "Pythia
> mechanistically encodes CAS" claim. Verdict treated as
> tamper-evident, reproducible, independently inspectable; not as
> proof of mechanistic alignment.

**What this means for the Glass House AI pitch:**

The strategy memo's core claim — that probing open-model activations
gives interpretability signal beyond what plain text classifiers
offer — is **not supported by current evidence**. The memo at
`STRATEGY_GLASS_HOUSE.md` needs a re-read under the stricter standard,
and any external-facing copy must be paused until Stage 3 ablation
delivers a separate line of evidence.

**Three next moves and the order I'd take them:**

1. **Stage 3 ablation, exploratory only.** Ablate the layer-3 direction
   in Pythia and check whether the output changes in a CAS-semantically-
   correct way. This is a different kind of evidence (causal, not
   discriminative). It is the test that could rescue or kill the
   mechanistic claim — but no public Glass House claims off this single
   experiment regardless.
2. **Cross-axis (domain, register, drive).** Cheap rerun. Maybe noetic
   is the lexically-easiest axis and others show a real Pythia-over-text
   lift. Same paired-baseline gates apply.
3. **Larger Pythia.** Pythia-160M is the smallest member of the family.
   Pythia-1.4B or 2.8B may carry richer internal structure that doesn't
   appear in the 160M slice. Still gated on the same paired-baseline
   reliability check.

Public Glass House messaging stays paused until at least one of these
delivers a `PROBE_RELIABLY_ABOVE_TEXT_BASELINE` verdict.

Artifacts on disk (unchanged shapes; only the report and README
revised under Stage 2.2):

- `pythia_noetic_probes_20260515.npz` — trained probes + split indices.
- `pythia_noetic_probes_report_20260515.json` — per-layer metrics,
  full baseline set (chance, majority, stratified, count-vector,
  TF-IDF), shuffled-label control, paired Pythia-vs-TF-IDF
  contingency + McNemar p-value, headline confusion matrix,
  reserved-language verdict.

## Stage 3 result (2026-05-16) — immediate next-token ablation

**Verdict: `ABLATION_NO_CAUSAL_BITE`.**

The narrow Stage 3 question: even if the layer-3 probe's lift over
TF-IDF is small, does ablating the direction the probe reads change
Pythia's actual next-token behaviour?

Method:

- The 10 trained probe coefficients at layer 3 span a 9-dimensional
  subspace in standardized activation space (the rank drops by one
  because the multinomial logistic regression has a redundant
  degree of freedom).
- Translate that subspace into raw-activation coordinates by dividing
  each probe coefficient by the StandardScaler scale.
- Build an orthonormal basis (SVD) of the resulting matrix in raw
  space; construct the projection matrix `P` onto that subspace.
- Register a forward hook on transformer block index 2 (whose output
  is the captured "layer 3" residual stream). The hook replaces the
  residual stream `h` with `h - h @ P` — the orthogonal complement
  of the probe-readout subspace.
- For each of the 69 test-set prompts, do two forward passes
  through Pythia-160M: baseline (no hook) and ablated (hook
  installed). Compare the top-1 next-token argmax.

Two checks gate the result:

**Check 1 — probe-self-ablation sanity gate:** PASSED.

| Probe accuracy on layer-3 activations | Test |
|---|---:|
| unablated (raw activations) | 0.899 |
| ablated (subspace projection removed) | **0.101** |

Ablation drops the probe to chance. The construction does what it
says it does: it removes the signal the probe reads.

**Check 2 — next-token causal effect:**

| Metric | Value |
|---|---:|
| test records | 69 |
| baseline_top1 == ablated_top1 | **69 / 69 (100.0%)** |
| KL(baseline ‖ ablated), mean | 0.12 nats |
| KL(baseline ‖ ablated), median | 0.12 nats |

Removing the entire 9-dimensional noetic subspace from Pythia's
layer-3 residual stream changes the top-1 next-token prediction on
**zero** of the 69 test prompts. The KL divergence in the full
logit distribution is small but non-zero (~0.12 nats), so the
ablation does shift probability mass around in the tail — but not
enough to flip any argmax.

**Honest interpretation, revised after Stage 3.1:**

The noetic subspace at layer 3 of Pythia-160M carries readable
information about the noetic axis. The immediate next-token test did
not change because every baseline top-1 token was newline (`"\n"`).
So Stage 3 proves only the narrow claim that removing the layer-3
noetic probe subspace does not change Pythia's immediate newline
prediction after these complete English descriptions.

It does **not** prove the subspace is behaviorally inert under
generation-style prompts. Stage 3.1 below supersedes that broader
interpretation.

**What this does and doesn't conclude:**

It rules out, on this single model + single axis + single layer +
single ablation method, the strongest version of the cross-model
interpretability pitch. It does NOT rule out:

- The same test on **other axes** (domain, register, drive). Maybe
  noetic is the lexically-easiest axis and others carry more
  causal weight.
- The same test on **larger Pythia** (1.4B or 2.8B). Mechanistic
  structure may not appear in the smallest member of the family.
- The same test on **other layers** (we ablated layer 3 only —
  layers 4-12 were not ablated and could carry causal weight).
- Tests on **other open models** (OLMo, Qwen).
- The Harness use case where the value is forensic / documentation,
  not mechanistic — that pitch is independent of this result.

Artifacts:

- `pythia_ablation_per_class_layer3_clean_20260516.json` - clean
  RTX A6000 rerun with `local_files_only`, device, model revision,
  package versions, structured sanity gate, token-match specificity,
  and verdict `MIXED_SPECIFICITY_EVIDENCE`.
- `stage3_2_progress_gpu_clean.log` - clean rerun stdout.

- `ablate_noetic_layer3.py` — Stage 3 script.
- `pythia_ablation_layer3_20260515.json` — full per-record report
  with baseline / ablated token IDs and decoded strings, KL stats,
  sanity gate result, verdict, decision thresholds.

---

## Stage 3.1 result (2026-05-16) — forced continuation ablation

**Verdict: `CONTINUATION_CAUSAL_EFFECT_PRESENT`.**

Codex re-audit of Stage 3 found that all 69 immediate next-token
predictions were the same newline token. Stage 3.1 keeps the same
ablation construction but forces Pythia into semantic continuation
with three suffixes:

- `In other words,`
- `This concept means`
- `A good explanation is`

Each of the 69 held-out records is tested under all three suffixes,
for 207 total continuation cases. Greedy generation is run for 8 new
tokens, baseline vs ablated.

**Sanity gate still passes:**

| Probe accuracy on layer-3 activations | Test |
|---|---:|
| unablated | 0.899 |
| ablated | **0.101** |

The ablation still removes what the probe reads.

**Continuation effect:**

| Metric | Value |
|---|---:|
| records | 69 |
| continuation cases | 207 |
| first-step top-1 match | 177/207 = 0.855 |
| full 8-token exact continuation match | 50/207 = 0.242 |
| mean token match rate | 0.499 |
| first-step KL mean | 0.0310 |
| first-step KL median | 0.0307 |

The forced-continuation test reverses the broad Stage 3 reading. The
layer-3 noetic probe subspace is not merely read-only under this
stronger setup: removing it changes continuation behavior often.

**Careful interpretation:**

This does **not** prove Pythia mechanistically encodes CAS in a clean
semantic sense. The continuations are short, greedy, and often generic.
A human semantic audit is still required to ask whether the changes
track noetic meaning or are just distributional perturbations.

The honest updated claim is:

> In Pythia-160M, the layer-3 noetic probe subspace is readable, mostly
> explainable from text, and behaviorally active under forced
> continuation prompts. It is not proven to be a clean CAS-mechanistic
> axis.

Artifacts:

- `ablate_noetic_layer3_continuation.py` — Stage 3.1 script.
- `pythia_ablation_layer3_continuation_20260515.json` — full
  per-case continuation report.

---

## Stage 3.2 result (2026-05-16) — per-class targeted ablation

**Current verdict: `MIXED_SPECIFICITY_EVIDENCE`.**

The original JSON report said `NO_PER_CLASS_SPECIFICITY`, but Codex audit
found that verdict too absolute because it was based on first-token change
only. The clean rerun report records the mixed result directly: first-token
specificity fails, while the full 8-token match metric points to weak
same-class disruption (`0.659` diagonal token-match vs `0.738` off-diagonal
token-match).

Stage 3.1 showed the layer-3 noetic subspace is behaviourally active
under forced continuation. The follow-up question (Codex audit
`1dbcc99`): are those changes class-specific, or does the subspace
behave like a shared "noetic-shaped" axis?

Method: ablate one class's unit-normalized raw-space direction at a
time (1D projection per class, 10 separate runs), then compare each
ablation's effect on its own-class prompts vs other-class prompts.

Clean rerun: **RunPod RTX A6000, `device: cuda`, 147.3 seconds total
wall-clock**. Report records `local_files_only: true`,
`cuda_device_name: NVIDIA RTX A6000`, model revision
`50f5173d932e8e61f858120bcb800b97af589f46`, and package versions.

**Pre-flight: per-direction sanity gate.**

For each class `^c`, ablate only direction `c` then re-run the
trained probe. Sanity: if direction `c` is the only place the probe
reads class-`c`, ablation should drive its "predict ^c on true-y=c"
rate to zero.

| Class | self-class kept-rate after ablation | direction quality |
|---:|---:|---|
| ^0 | 0.000 | clean |
| **^1** | **0.714** | redundant — same info encoded along other axes |
| ^2 | 0.000 | clean |
| **^3** | **0.429** | partially redundant |
| ^4 | 0.000 | clean |
| ^5 | 0.000 | clean |
| ^6 | 0.000 | clean |
| ^7 | 0.000 | clean |
| ^8 | 0.000 | clean |
| ^9 | 0.000 | clean |

8 of 10 directions are single-axis-clean. ^1 and ^3 are partially
redundant — ablating just their named direction leaves the probe
mostly intact. This is a real diagnostic finding: the noetic
subspace has class-pair redundancy, not full per-class
orthogonality.

**Per-direction direction quality:** off-diagonal cosine
similarities mean −0.109, max abs 0.234 — directions are roughly
orthogonal with mild correlation.

**Headline metric: 10×10 first-token-changed matrix.**

Rows = ablated class. Columns = true_y of the prompt.

```
        ^0    ^1    ^2    ^3    ^4    ^5    ^6    ^7    ^8    ^9
^0    0.12  0.05  0.04  0.00  0.00  0.06  0.06  0.25  0.00  0.10
^1    0.08  0.14  0.11  0.00  0.06  0.00  0.11  0.04  0.27  0.05
^2    0.00  0.10  0.07  0.00  0.00  0.06  0.00  0.12  0.13  0.00
^3    0.04  0.10  0.04  0.00  0.00  0.00  0.11  0.12  0.07  0.10
^4    0.08  0.05  0.04  0.00  0.00  0.06  0.06  0.12  0.00  0.05
^5    0.04  0.05  0.04  0.10  0.00  0.06  0.00  0.04  0.13  0.14
^6    0.04  0.05  0.04  0.00  0.00  0.11  0.00  0.08  0.13  0.10
^7    0.17  0.10  0.04  0.00  0.00  0.11  0.00  0.17  0.13  0.14
^8    0.00  0.14  0.04  0.00  0.00  0.06  0.00  0.08  0.13  0.10
^9    0.12  0.10  0.04  0.10  0.00  0.06  0.00  0.17  0.13  0.10
```

| Aggregate | value |
|---|---:|
| diagonal mean first_token_changed (ablate ^c on class ^c prompts) | **0.079** |
| off-diagonal mean first_token_changed (ablate ^c on other classes) | **0.062** |
| delta (diag − off) | **+0.017 pp** |

**Per-class specificity ratio (self / cross):**

| Class | self | cross | ratio | note |
|:---:|---:|---:|---:|---|
| ^0 | 0.125 | 0.060 | **2.08** | clean direction, mild specificity |
| ^1 | 0.143 | 0.080 | 1.79 | redundant direction; ratio may be inflated |
| ^2 | 0.074 | 0.045 | 1.63 | clean direction, mild specificity |
| ^3 | 0.000 | 0.064 | 0.00 | redundant direction; effect deflated |
| ^4 | 0.000 | 0.050 | 0.00 | clean direction; no self-effect |
| ^5 | 0.056 | 0.060 | 0.93 | clean direction; no specificity |
| ^6 | 0.000 | 0.061 | 0.00 | clean direction; no self-effect |
| ^7 | 0.167 | 0.076 | **2.19** | clean direction, mild specificity |
| ^8 | 0.133 | 0.046 | **2.90** | clean direction, strongest specificity |
| ^9 | 0.095 | 0.079 | 1.21 | clean direction; weak specificity |

**Honest interpretation:**

The aggregate diagonal-vs-off-diagonal delta is +1.7 percentage
points — basically noise on per-cell sample sizes of ~6-9 prompts.
Per-class results are scattered: four classes show modest
specificity (^0 ~2.1, ^2 ~1.6, ^7 ~2.2, ^8 ~2.9), three clean
directions show no self-effect (^4, ^6, sometimes ^5), and ^3/^1
are confounded by direction redundancy.

On the first-token metric, **ablating one class's direction is not
measurably more disruptive to its own class than to other classes**.
On the full 8-token match metric, same-class ablation is more
disruptive by about 7.9 percentage points (`0.659` diagonal match vs
`0.738` off-diagonal match). The Stage 3.1 behavioural effect is real,
but Stage 3.2 currently gives mixed evidence rather than a clean
per-class mechanism.

**What this means for the Glass House pitch:**

The cleanest mechanistic claim — that each named CAS direction in
Pythia's layer-3 residual stream controls behaviour on its own
class — is **not supported**. The subspace acts more like a shared
"noetic-shaped" axis than as 10 distinct per-class controls.

The pitch must drop "Pythia has class-specific noetic readouts" as
a claim. What's left: "the Probe finds linearly-decodable noetic
information; ablating the full subspace changes behaviour under
continuation; but the behaviour change is not class-specific."
That's a much weaker statement than the original Glass House
framing. After the clean rerun, read that sentence narrowly: the
behaviour change is not cleanly class-specific at the first token, but
full-continuation token match gives weak same-class disruption. This
is still not strong enough for a Glass House claim.

**What this does NOT rule out** (kept narrow on purpose):

- The same test on **other layers** (4-12 unablated for per-class).
- The same test with **multi-direction ablation per class** (full
  rank, not unit-direction). With ^1 and ^3 redundancy noted, a
  multi-direction targeted ablation might show specificity that
  the unit-direction test missed.
- The same test on **other axes** (domain, register, drive).
- The same test on **larger Pythia** or **other open models**.
- The **Harness-as-forensic-documentation** product, which is
  independent of mechanistic interpretability claims.

Artifacts:

- `ablate_noetic_per_class_layer3.py` — Stage 3.2 script.
- `pythia_ablation_per_class_layer3_20260515.json` — 10×10
  matrices (first_token_changed + mean_token_match), per-case
  rows, per-class specificity ratios, sanity-gate per-direction
  results, full verdict.
- `stage3_2_progress.log` — RunPod stdout, includes the per-class
  elapsed times.

---

## Stage 3.2 random-direction control (2026-05-16) — audit Patch 3

**Verdict: `NOETIC_EFFECT_SUGGESTIVE_CONTROL_PASSED`**. The control is
useful and points in the expected direction, but the direct between-arm
comparison is still borderline.

Came out of the Claude-seat audit on commit `d8afd7d` (entry in
`inbox_claude.md` 2026-05-16T10:40Z). The concern: Stage 3.2's
"same-class is more disrupted than cross-class" finding might be
class-difficulty (^7-typical continuations are vocabulary-narrow
and disrupted by ANY ablation), not direction-meaningful.

Method: sample 10 random unit directions in the orthogonal
complement of the noetic subspace (seed=42, QR-orthonormalized so
the 10 random directions are mutually orthogonal AND orthogonal to
the entire noetic basis), run the same 207-prompt × 10-direction
ablation experiment, compute the same disruption stats.

Hardware: RunPod RTX A6000, 140 sec wall-clock.

Direction quality verification (printed in log + report):

  random direction norms: min=1.0000 max=1.0000
  random × noetic cosine: max_abs = 0.000000 (target 0)
  random × random off-diag cosine: max_abs = 0.000000 (target 0)

**Head-to-head per-direction-index disruption (token-match cross −
self; positive = same-pseudoclass more disrupted):**

| dir | noetic | random |
|:---:|---:|---:|
| 0 | +0.120 | +0.073 |
| 1 | +0.000 | +0.138 |
| 2 | **+0.186** | +0.002 |
| 3 | −0.059 | −0.110 |
| 4 | +0.026 | −0.194 |
| 5 | −0.043 | −0.037 |
| 6 | +0.057 | −0.149 |
| 7 | **+0.214** | +0.116 |
| 8 | **+0.175** | +0.106 |
| 9 | +0.111 | −0.033 |

| Aggregate | noetic | random |
|---|---:|---:|
| mean disruption | **+0.079** | **−0.009** |
| std | 0.092 | 0.111 |
| positive count | 8 / 10 | 5 / 10 |
| one-sample t against 0 | **t = 2.56, p = 0.031** | t = −0.24, **p = 0.82** |

**Welch t-test, noetic vs random distributions (n=10 each):**

  **t = 1.82, p = 0.086**

### Honest interpretation

Three signals layered:

1. **Random arm is a clean null** — 5/10 positive, mean −0.009,
   p = 0.82. Random unit ablations do not create class-aligned
   disruption. This is the control working as designed.
2. **Noetic arm is reliably non-zero against the null** —
   p = 0.031 one-sample. The Stage 3.2 +0.079 effect survives the
   one-sample test against zero.
3. **Direct noetic-vs-random comparison is borderline** —
   p = 0.086 Welch on n=10 vs n=10. The arms differ in the expected
   direction (noetic > random by +0.088 mean) but with limited
   sample-size power.

**The defensible claim:**

> The noetic subspace's per-class directions produce same-class
> continuation disruption that is (a) statistically reliable
> against a zero baseline (p=0.031), (b) absent when matched
> random orthogonal directions are ablated (p=0.82), and (c)
> larger than the random control by +0.088 mean disruption
> (Welch p=0.086, borderline at α=0.05 with n=10 per arm). On
> this evidence is suggestive, not a full direction-meaningful
> verdict, because the direct between-arm test is still borderline
> and would benefit from more directions or a more sensitive metric.

**What this upgrades:**

- Stage 3.2 narrative from `MIXED_SPECIFICITY_EVIDENCE` to
  `NOETIC_EFFECT_SUGGESTIVE_CONTROL_PASSED`.
- The random-control construction itself passes: random directions are
  unit-length, mutually orthogonal, and orthogonal to the noetic
  subspace. The random arm behaves like a null control.
**What this does NOT upgrade:**

- It does not upgrade to `NOETIC_EFFECT_DIRECTION_MEANINGFUL`.
  That stronger verdict now requires Welch noetic-vs-random p < 0.05.
  Current p=0.086 keeps the claim conservative.
- Any external Glass House messaging should cite both the per-arm
  one-sample results and the borderline between-arm comparison, with
  reserved language.
- ^3 and ^5 still show no specificity (and ^3 still aligns with the
  sanity-gate redundancy diagnosis).
- ^7's noetic disruption (+0.214) is partly explained by random
  baseline +0.116 — half of ^7's effect IS class-difficulty. ^2's
  +0.186 vs random +0.002 is the cleanest direction-specific
  signal in the experiment.
- Single model (Pythia-160M), single layer (3), single axis
  (noetic). Cross-axis / cross-layer / cross-model still
  unaddressed.

### What this means for Glass House

The cleanest defensible plain-English version, post-control:

> CAS noetic directions in Pythia-160M's mid-network show a
> suggestive mechanistic signal: ablating them produces modest
> same-class continuation disruption, while matched random
> ablations behave like a null control. The direct noetic-vs-random
> comparison is borderline, so this is preliminary evidence, not a
> settled cross-model interpretability claim.

That's the current claim that survives the control. Earlier
Glass House framing ("see how this model thinks in CAS") still
overshoots. The corrected pitch: "structured probes can find
CAS-correlated structure in open models; whether that structure is
robust across layers, axes, and architectures is the next empirical
question."

### Artifacts

- `ablate_random_direction_layer3.py` — control script with
  fixed-seed random direction sampling, QR-orthonormalization,
  and one-sample t-test on per-direction disruptions; also pulls
  the noetic arm's per-class disruption from the Stage 3.2 clean
  report for side-by-side comparison.
- `pythia_ablation_random_control_layer3_20260516.json` — full
  report including the 10×10 random matrix, per-direction
  disruption deltas, one-sample t-test, the noetic-arm
  one-sample t-test for compare, and verdict.
- `random_control_progress.log` — pod stdout with per-direction
  elapsed times and direction-quality diagnostics.

---

## Stage 3.3 n=30 permutation control (2026-05-16)

**Verdict: `NOETIC_EFFECT_DIRECTION_MEANINGFUL_N30_PERMUTATION`.**

This follow-up addresses the Stage 3.2-control limitation: n=10 vs n=10
Welch was underpowered and only borderline (`p=0.086`). Instead of adding
fake CAS classes, Stage 3.3 samples 30 random directions in the noetic
subspace's orthogonal complement, then repeatedly builds matched
10-direction null sets.

Method:

- Sample 30 random unit directions in the noetic complement
  (`seed=4242`), QR-orthonormalized.
- Run the same forced-continuation ablation for all 30 directions.
- For each of 10,000 permutations, sample 10 random directions without
  replacement, randomly assign them to the 10 noetic class slots, and
  compute the same mean same-class disruption statistic as the real
  noetic arm.
- Use a one-sided plus-one-corrected permutation p-value:
  `p = (1 + count(null >= observed)) / (1 + n_permutations)`.

Direction quality verification:

```text
random direction norms: min=1.0000 max=1.0000
random x noetic cosine: max_abs=0.00000000
random x random off-diag: max_abs=0.00000000
```

Result:

| Statistic | Value |
|---|---:|
| Noetic mean disruption | +0.0787 |
| Random null mean | +0.0002 |
| Random null std | 0.0209 |
| Random null p95 | +0.0352 |
| Random null p99 | +0.0489 |
| Effect over null mean | +0.0786 |
| One-sided permutation p | 0.0003 |

Plain-English claim:

> In Pythia-160M layer 3, CAS noetic directions produce same-class
> continuation disruption that is far above matched random directions
> drawn from the same orthogonal complement. This is direction-meaningful
> mechanistic evidence for this model/layer/axis. It is not yet a
> cross-model product claim.

What this upgrades:

- Stage 3.2-control's `NOETIC_EFFECT_SUGGESTIVE_CONTROL_PASSED` becomes
  `NOETIC_EFFECT_DIRECTION_MEANINGFUL_N30_PERMUTATION`.
- The random-control story no longer rests on the borderline Welch
  comparison. The permutation test matches the actual question: does the
  real 10-direction noetic set beat 10-direction random sets sampled from
  the orthogonal complement?

What this still does **not** prove:

- It is only Pythia-160M, only layer 3, only the noetic axis.
- It does not prove every noetic class is individually clean; ^3 and ^5
  remain weak/wrong-direction in the earlier per-class read.
- It does not yet prove the same effect across domain/register/drive axes,
  larger Pythia models, OLMo/Qwen, or CAS Native itself.
- It does not support "we can read every thought" language. It supports a
  bounded mechanistic claim: this CAS-labelled direction set has a
  behavioral effect beyond matched random directions.

Artifacts:

- `ablate_random_direction_layer3_n30.py`
- `pythia_ablation_random_control_layer3_n30_20260516.json`
- `random_control_n30_progress.log`

---

## Stage 4.1 domain ablation (2026-05-16)

**Verdict: `DOMAIN_EFFECT_NOT_ABOVE_RANDOM_N30_PERMUTATION`.**

This was the causal follow-up to the Stage 4.0 domain probe screen. The
experiment used the domain probe's best layer (layer 5), ablated the four
domain directions (`P`, `C`, `E`, `O`), and compared their mean
same-class continuation disruption against 30 matched random directions
from the domain-subspace complement.

Result:

| Statistic | Value |
|---|---:|
| Domain mean disruption | +0.0142 |
| Domain one-sample p | 0.5116 |
| Random null mean | -0.0000 |
| Random null p95 | +0.0396 |
| Effect over null mean | +0.0143 |
| One-sided permutation p | 0.2931 |

The result does **not** clear the causal bar. The observed domain effect
is well inside the matched random null. The self-ablation sanity gate
also flagged a serious weakness:

| Domain | True-class kept rate after ablating its direction |
|---|---:|
| P | 0.000 |
| C | 0.000 |
| E | 0.000 |
| O | 1.000 |

The `O` direction did not suppress `O` predictions at all; after ablation,
the probe still predicted `O` for 87.3% of the domain test set. That means
the domain probe's class directions are not clean enough to support a
domain mechanistic claim.

Plain-English read:

> Domain labels are recoverable from Pythia layer-5 activations, but the
> domain directions do not yet show a reliable causal behavioral effect.
> The current strong mechanistic result remains noetic-only.

Next implication:

- Do **not** run register/drive ablations yet.
- Do **not** broaden Glass House claims to "all CAS axes."
- The best next scientific path is either cross-model noetic replication
  (OLMo/Qwen) or a cleaner domain-label corpus/probe before another domain
  ablation.

Artifacts:

- `ablate_domain_layer5_n30.py`
- `pythia_ablation_domain_layer5_n30_20260516.json`
- `domain_layer5_n30_progress.log`

---

## Stage 4.0 cross-axis probe screen (2026-05-16)

**Verdict: mixed. Domain is the only promising next ablation target.**

This stage trains the same per-layer linear probes used for noetic, but
for three additional CAS axes extracted from the frozen
`source_cas_expression` field:

- **domain**: P, C, E, O
- **register**: T, A, f, E
- **drive**: F1-F7

Only records with exactly one unique label for the target axis are used.
Multi-label and missing-label rows are excluded per-axis.

| Axis | Eligible records | Headline layer | Pythia test | Best text test | Lift | McNemar p | Verdict |
|---|---:|---:|---:|---:|---:|---:|---|
| domain | 415 | 5 | 0.810 | 0.730 | +0.079 | 0.267 | `LABELS_RECOVERABLE_MOSTLY_FROM_TEXT` |
| register | 176 | 0 | 0.333 | 0.259 | +0.074 | 0.688 | `PROBE_WEAKLY_ABOVE_CHANCE` |
| drive | 226 | 3 | 0.324 | 0.294 | +0.029 | 1.000 | `LABELS_RECOVERABLE_MOSTLY_FROM_TEXT` |

Domain is the only axis with enough signal to justify a causal follow-up:
the Pythia probe beats the best text baseline by +7.9 pp, but the paired
McNemar test is not significant. That means this is promising but not
yet reliable beyond-text evidence.

Register is weak. Its Pythia headline test accuracy (0.333) is below the
stratified dummy baseline from this split (0.370), so it should not move
to ablation yet.

Drive is above chance and above text by a small amount (+2.9 pp), but the
paired test gives no reliable lift.

Recommended next experiment:

> Stage 4.1 domain ablation only. Use the same discipline as Stage 3.3:
> targeted domain directions at the best domain layer (layer 5), matched
> random directions from the domain-subspace complement, and a permutation
> null. Do not spend pod time on register or drive ablation until their
> discriminative signal improves.

Artifacts:

- `train_cross_axis_probes.py`
- `pythia_cross_axis_probes_20260516.npz`
- `pythia_cross_axis_probes_report_20260516.json`

---

## Stage 2.1 result (kept for audit trail)

**Verdict: `PROBE_RECOVERS_LABELS_NOT_ABOVE_TEXT_BASELINE`.**

Per Codex audit `f0eadd0`, the previous Stage 2 framing ("Pythia
detectably encodes CAS at 92.8%") was overclaim. Two problems:

1. The headline cherry-picked the best **test** layer. The test set
   must be held out and used once, not used to pick the layer. The
   val-selected layer is layer **3** with **test acc 0.899**, not
   layer 4 at 0.928.
2. No text baseline was reported. A plain TF-IDF + logistic regression
   on the same English text reaches **0.884** test acc. Pythia's
   probe adds only **+1.4 pp** over the text baseline. The 88%-90%
   range is almost entirely a property of the English text the SDG
   pipeline produced, not of Pythia's internals.

**Honest headline table:**

| Source | Val acc | Test acc | macro-F1 |
|---|---:|---:|---:|
| TF-IDF text baseline | 0.841 | **0.884** | 0.882 |
| Pythia layer 3 (val-selected headline) | 0.899 | **0.899** | 0.902 |
| Pythia layer 4 (highest test, but test-leakage) | 0.899 | 0.928 | 0.931 |
| Shuffled-label control on layer 3 | 0.130 | **0.101** | — |
| Chance | 0.100 | 0.100 | — |

The shuffled-label control at 10.1% confirms the split is clean: when
labels are randomized on train, the probe drops to chance. The +1.4 pp
Pythia-over-TF-IDF gap is real but small.

**Per-layer accuracies (val + test) for the record:**

| Layer | Train | Val | Test | macro-F1 |
|---:|---:|---:|---:|---:|
| 0 (embed) | 1.000 | 0.855 | 0.884 | 0.886 |
| 1 | 1.000 | 0.884 | 0.913 | 0.912 |
| 2 | 1.000 | 0.884 | 0.913 | 0.912 |
| **3** ← headline (val) | 1.000 | **0.899** | 0.899 | 0.902 |
| 4 | 1.000 | 0.899 | 0.928 | 0.931 |
| 5 | 1.000 | 0.884 | 0.928 | 0.926 |
| 6 | 1.000 | 0.855 | 0.913 | 0.916 |
| 7 | 1.000 | 0.812 | 0.884 | 0.884 |
| 8 | 1.000 | 0.841 | 0.899 | 0.902 |
| 9 | 1.000 | 0.812 | 0.884 | 0.887 |
| 10 | 1.000 | 0.812 | 0.870 | 0.868 |
| 11 | 1.000 | 0.812 | 0.884 | 0.886 |
| 12 | 1.000 | 0.812 | 0.870 | 0.872 |

**Reserved-language verdict:**

> On this CAS-labeled English corpus (n=457), a linear probe on
> Pythia-160M layer-3 hidden states recovers the noetic label at test
> accuracy 0.899 (macro-F1 0.902), against a 10% chance baseline. A
> TF-IDF + logistic-regression baseline on the same text reaches
> 0.884; the Pythia probe adds +1.4 pp over text alone. A
> shuffled-label control on the same layer drops to 0.101, ruling out
> a split leak. This evidence is consistent with Pythia's internal
> representations carrying noetic-axis information beyond what is
> recoverable from surface wording, **but the marginal lift over the
> TF-IDF baseline is modest**. Causal-influence (ablation) and
> paraphrase-control tests are required before any claim that Pythia
> mechanistically encodes CAS structure beyond lexical association.
> Verdict treated as tamper-evident, reproducible, independently
> inspectable; not as proof of mechanistic alignment.

**Confusion matrix (val-headline layer 3, test set, rows = true y,
cols = pred y):**

```
     ^0  ^1  ^2  ^3  ^4  ^5  ^6  ^7  ^8  ^9
^0    7   0   0   1   0   0   0   0   0   0
^1    0   6   0   1   0   0   0   0   0   0
^2    0   0   9   0   0   0   0   0   0   0
^3    1   1   0   5   0   0   0   0   0   0
^4    0   0   0   0   6   0   0   0   0   0
^5    0   0   0   0   0   6   0   0   0   0
^6    0   0   0   0   0   0   6   0   0   0
^7    0   0   0   0   0   0   0   8   0   0
^8    1   0   0   0   0   0   0   0   4   0
^9    1   0   0   1   0   0   0   0   0   5
```

Mostly diagonal. ^0 (Idea — the generic "all things in/outside Mind"
catch-all) absorbs misclassifications from ^3, ^8, and ^9 — consistent
with ^0's broader semantic scope.

**What this means for the Glass House AI pitch:**

The honest current claim is **weaker** than Stage 2's initial framing.
On this single model, with this single axis, with Claude-generated
English, the bulk of the probe's signal is recoverable from plain
text. That's not nothing, but it does not yet support claims about
"Pythia mechanistically encoding CAS." The Glass House strategy memo
should be re-read and revised under this stricter standard.

**Decision-gate revisions for next stages.**

- Stage 3 (causal ablation) is still the right test. If ablating the
  detected layer-3 direction changes Pythia's output in a CAS-
  semantically-correct way, the +1.4 pp gap is mechanistically
  meaningful. If ablation just scrambles output, the gap is
  decoration.
- Cross-axis (domain, register, drive) is also worth running on the
  same activations — cheap (~10 min total). Maybe noetic happens to
  be the lexically-easiest axis and the others show a larger
  Pythia-over-TF-IDF lift.
- Cross-model (OLMo or Qwen) is the larger investment. Only worth it
  after at least one axis or one ablation suggests Pythia adds real
  structure over text.

Artifacts on disk:

- `pythia_noetic_probes_20260515.npz` — trained probes (coefs,
  intercepts, scaler params, per-layer, plus the train/val/test
  index arrays).
- `pythia_noetic_probes_report_20260515.json` — per-layer metrics,
  TF-IDF baseline section, shuffled-label control section, headline
  confusion matrix, Pythia-vs-TF-IDF delta, reserved-language verdict.

## Files

- `.gitattributes` — pins LF line endings on the research JSON / JSONL /
  Python / Markdown files so the manifest's sha256 of the snapshot
  matches the on-disk bytes on any host (Windows, Linux, macOS).
- `pythia_probe_source_wave3_cas_to_english_20260515.jsonl` — vendored
  slice of the wave3 corpus, containing only the 1,129 `cas_to_english`
  records. Vendored inside the branch so a clean checkout can rebuild
  the labels snapshot without depending on out-of-branch files.
- `build_pythia_probe_snapshot.py` — joins the vendored wave3 slice with
  `cas-synthetic/data/path_d/seeds.jsonl` (tracked at its canonical
  path) and writes a frozen snapshot + manifest. Deterministic: re-running
  with the same source files produces byte-identical output. Includes a
  regex-based CAS-notation leakage filter (added post-audit) so the
  probe cannot read its label off the prompt.
- `pythia_probe_labels_20260515.jsonl` — frozen labels for the
  experiment. **Read-only.** Regenerate by re-running the builder.
- `pythia_probe_manifest_20260515.json` — sha256 of the snapshot,
  source-file paths + hashes, record count, class distribution,
  extraction rules in plain text, and rejection counts (including the
  new leakage-regex rejections).
- `capture_pythia_activations.py` — Stage 1.1 capture script. Loads
  Pythia-160M, mean-pools hidden states per layer, dumps a `.npz`. NOT
  YET RUN — requires explicit user OK to install `transformers` and
  download Pythia weights.

## Decision gates (superseded — see "Decision gates (revised)" above)

The original pre-experiment gates listed below proved insufficient.
Beating chance only proves the labels are recoverable from the
English text the SDG pipeline produced — it does not show the model
adds structure beyond plain bag-of-words classification. The Stage
2.2 audit (commit `0421e7f`) replaced these gates with the stricter
paired-baseline + McNemar criterion in the **"Decision gates
(revised post-audit 2026-05-16)"** section near the top of this
README. The bullets below are retained for the audit trail only:

- ~~**Stage 2 pass:** best-layer noetic-probe test accuracy ≥ 30%
  (vs 10% chance baseline across 10 noetic classes).~~
- ~~**Stage 2 weak:** 20%–30%. Run ablation analysis to understand
  which noetics are detectable and which are not.~~
- ~~**Stage 2 fail:** <20%. CAS structure is not naturally factored
  in Pythia's activations at the prompt-encoding level.~~
- **Stage 3 pass (still load-bearing):** ablating the detected
  direction changes the output measurably (output similarity drops
  below a threshold).

## What CAS Mode 7 means here

Mode 7's mechanistic-attribution surface (`Mode7LiveShell` in the
dashboard, `api/routes/mode7.py` on the backend) was built against CAS
Native's own activations — which have named axes by construction.

For a fully-open foreign model like Pythia, "Mode 7" means the same
*idea* — bind activations to CAS commitments, trace them through the
network, test their causal role — but the binding needs trained probes
because Pythia doesn't have CAS axes baked into its architecture.

If this experiment succeeds, the pitch becomes: *"Mode 7 works on any
open-weight model after training probes; with CAS Native, the probes are
the architecture."*

## Stage 5.0 result - original TKS dog-training noetic transfer smoke

**Verdict: `TKS_DOG_TRANSFER_MIXED`.**

This stage adds a tiny hand-authored transfer set from the original TKS
dog-training demonstration. It is deliberately not training data. The
purpose is to ask whether the saved Pythia noetic probe recognizes a
clean original-TKS example outside the Claude/SDG snapshot style.

Canonical numbering correction:

| Original TKS | CAS Native | Meaning |
|---:|---:|---|
| 10 | `^0` | Idea |
| 1 | `^1` | Mind |
| 2 | `^2` | Positive |
| 3 | `^3` | Negative |
| 4 | `^4` | Vibration |
| 5 | `^5` | Female |
| 6 | `^6` | Male |
| 7 | `^7` | Rhythm |
| 8 | `^8` | Above/Cause |
| 9 | `^9` | Below/Effect |

The `^6` row is user-clarified rather than quoted directly from the
page: Male is treated as an idea made of nested ideas while itself
belonging to a larger set of ideas. In the dog-training frame, "sit on
command" contains the cue, posture, reward expectation, trainer
relationship, and repeated practice, while also belonging to the larger
training system.

Result:

| Evaluator | Accuracy |
|---|---:|
| Pythia noetic probe, headline layer 3 | 4/10 |
| Pythia noetic probe, best layer 9 | 6/10 |
| Count-vector text baseline | 4/10 |
| TF-IDF text baseline | 2/10 |

Layer-3 gets Mind, Negative, Rhythm, and Below/Effect correct. The main
failure mode is over-predicting `^7 Rhythm` for dog-training language:
Idea, Positive, Female, and Male all collapse toward Rhythm at layer 3.
That makes conceptual sense as a failure mode because the whole example
is framed by training, command, repetition, schedule, and practice.

Honest read:

> The noetic probe partially transfers to an original TKS example, but
> not cleanly. It recognizes some classes outside the snapshot style,
> while also showing a strong dog-training lexical bias toward Rhythm.
> This strengthens the case for adding more original-TKS hand-authored
> transfer sets before making any broad cross-model claim.

Artifacts:

- `tks_dog_training_noetic_eval_20260516.jsonl` - 10-row canonical
  fixture, one row per noetic.
- `evaluate_tks_dog_noetics.py` - applies the saved Pythia noetic probe
  and retrains text baselines on the original snapshot train split.
- `tks_dog_training_noetic_eval_report_20260516.json` - full per-layer
  and per-row report.

## Stage 5.1 result - multi-scenario TKS-style noetic transfer smoke

**Verdict: `TKS_NOETIC_TRANSFER_MIXED` - mixed transfer, not a pass.**

After the dog-training-only smoke showed a Rhythm-heavy bias, Stage 5.1
added four more hand-authored, definition-anchored scenarios: debate
preparation, lost keys, software debugging, and gallery viewing. The
fixture now has 50 rows: five scenarios times ten noetics.

Result:

| Evaluator | Accuracy |
|---|---:|
| Pythia noetic probe, headline layer 3 | 16/50 |
| Pythia noetic probe, best layer 4 | 23/50 |
| Count-vector text baseline | 11/50 |
| TF-IDF text baseline | 16/50 |

Layer-3 ties TF-IDF on the expanded transfer suite, so it does not show
clean beyond-text transfer. The best layer does better, but that is an
exploratory post-hoc layer pick and should not be treated as the main
claim.

Layer-3 by scenario:

| Scenario | Accuracy |
|---|---:|
| Debate preparation | 3/10 |
| Dog training | 3/10 |
| Gallery viewing | 4/10 |
| Lost keys | 4/10 |
| Software debugging | 2/10 |

Layer-3 by noetic:

| Noetic | Accuracy |
|---|---:|
| Idea | 0/5 |
| Mind | 1/5 |
| Positive | 0/5 |
| Negative | 4/5 |
| Vibration | 0/5 |
| Female | 4/5 |
| Male | 0/5 |
| Rhythm | 3/5 |
| Above/Cause | 2/5 |
| Below/Effect | 2/5 |

Honest read:

> The saved Pythia noetic probe carries some real signal into
> original-TKS-style examples, especially Negative, Female, and Rhythm.
> But it does not cleanly transfer across the noetic vocabulary. It
> misses Idea, Positive, Vibration, and Male completely on this wording,
> and headline layer 3 only ties TF-IDF. This supports the stricter
> conclusion that current Pythia results are mechanistically interesting
> for the frozen snapshot, but not yet robust semantic understanding of
> the full TKS noetic system.

Stage 5.1 reinforces the current roadmap decision: do not spend pod time
on drive/register ablations yet. The next useful science step is either
more carefully designed original-TKS semantic fixtures, or cross-model
noetic replication with a cleaner, paraphrase-controlled dataset.

Artifacts:

- `tks_noetic_transfer_eval_20260516.jsonl` - 50-row multi-scenario
  fixture.
- `tks_noetic_transfer_eval_report_20260516.json` - full report.

## Stage 5.2 result - paraphrase-controlled noetic transfer smoke

**Verdict: `TKS_NOETIC_TRANSFER_MIXED` - suggestive improvement, not a
clean pass.**

Stage 5.2 controls the wording more directly: ten noetics, six
paraphrase styles each. The styles are definition-plain, concrete-human,
system-analog, neutral-minimal, story-context, and stakeholder-plain.

Result:

| Evaluator | Accuracy |
|---|---:|
| Pythia noetic probe, headline layer 3 | 29/60 |
| Pythia noetic probe, best layer 0 | 31/60 |
| Count-vector text baseline | 16/60 |
| TF-IDF text baseline | 25/60 |

Paired baseline check:

| Comparison | Probe-only correct | Text-only correct | p |
|---|---:|---:|---:|
| Layer-3 probe vs count-vector | 17 | 4 | 0.007 |
| Layer-3 probe vs TF-IDF | 11 | 7 | 0.481 |

So the paraphrase-controlled set is better than the prior transfer
smokes, but it is still not a clean pass under the stricter standard.
The probe clearly beats raw count-vector word presence, but it does not
reliably beat TF-IDF on paired discordant examples.

Layer-3 by noetic:

| Noetic | Accuracy |
|---|---:|
| Idea | 2/6 |
| Mind | 4/6 |
| Positive | 2/6 |
| Negative | 4/6 |
| Vibration | 2/6 |
| Female | 5/6 |
| Male | 0/6 |
| Rhythm | 4/6 |
| Above/Cause | 2/6 |
| Below/Effect | 4/6 |

Layer-3 by paraphrase style:

| Style | Accuracy |
|---|---:|
| system_analog | 7/10 |
| definition_plain | 6/10 |
| concrete_human | 6/10 |
| neutral_minimal | 5/10 |
| story_context | 3/10 |
| stakeholder_plain | 2/10 |

Honest read:

> Paraphrase control improves the transfer result. The saved Pythia
> noetic probe now shows partial wording robustness and beats a raw
> word-count baseline. But the lift over TF-IDF is not statistically
> reliable, and Male remains completely missed. This is real progress,
> not a pass. The next dataset should target Male and the weak
> noetics, while using held-out paraphrases designed before evaluation.

Artifacts:

- `tks_noetic_paraphrase_eval_20260516.jsonl` - 60-row paraphrase
  fixture.
- `tks_noetic_paraphrase_eval_report_20260516.json` - full report,
  including paired baseline contingencies.

## Stage 5.3 result - targeted `^6` Male diagnostic

**Verdict: `^6` is alias-bound, not concept-robust.**

The Stage 5.2 failure mode was specific: Male (`^6`) scored 0/6 even
though other noetics partially transferred. Stage 5.3 isolates that
failure with 30 Male rows and 18 contrast rows.

Result:

| Evaluator | Accuracy |
|---|---:|
| Pythia noetic probe, headline layer 3 | 18/48 |
| Pythia noetic probe, best layer 4 | 19/48 |
| Count-vector text baseline | 8/48 |
| TF-IDF text baseline | 20/48 |

Layer-3 target focus:

| Focus | Accuracy |
|---|---:|
| Male rows | 7/30 |
| Contrast rows | 11/18 |

Male rows by wording family:

| Wording family | Accuracy |
|---|---:|
| `male_alias_breakdown` | 7/10 |
| `male_nested_composition` | 0/10 |
| `male_no_alias_plain` | 0/10 |

This resolves the question. The saved Pythia probe recognizes `^6` only
when the text uses the training aliases: "breaking down," "unpacking,"
"pulls apart," or "looking underneath." It does **not** recognize the
cleaner corrected definition:

> an idea made of nested ideas, while itself being part of a larger set
> of ideas

Honest read:

> The current `^6` readout is a wording detector, not a robust Male
> concept detector. The correct next repair is not more ablation. It is
> a better noetic probe dataset whose `^6` examples include nested
> composition language, no-alias plain language, and hard contrasts
> against `^5` Female.

Artifacts:

- `tks_noetic_male_diagnostic_eval_20260516.jsonl` - targeted `^6`
  diagnostic fixture.
- `tks_noetic_male_diagnostic_eval_report_20260516.json` - full report.

## Stage 5.4 result - v2 noetic probe repair

**Verdict: targeted `^6` repair succeeded; global transfer still mixed.**

Stage 5.4 builds a v2 probe snapshot from the original 457-row frozen
snapshot plus 94 hand-authored augment rows:

- 36 corrected `^6` Male rows:
  - nested-composition wording
  - no-alias composition wording
  - alias-plus-definition bridge wording
- 18 hard `^5` Female contrast rows
- 40 support rows for previously weak noetics (`^0`, `^2`, `^4`, `^8`)

The v2 snapshot has 551 rows. Exact-text overlap with the held-out Stage
5.2 paraphrase fixture and Stage 5.3 Male diagnostic fixture is zero.

Internal v2 train/val/test result:

| Metric | Value |
|---|---:|
| v2 headline layer | 4 |
| v2 headline test accuracy | 0.916 |
| TF-IDF test accuracy | 0.867 |
| paired probe-only vs TF-IDF-only | 7 vs 3 |
| paired p | 0.344 |

So the internal v2 split is strong, but still not a statistically
reliable beyond-TF-IDF proof.

Held-out Stage 5.2 paraphrase fixture:

| Metric | v1 | v2 |
|---|---:|---:|
| headline probe accuracy | 29/60 | 38/60 |
| best layer accuracy | 31/60 | 41/60 |
| count-vector baseline | 16/60 | 29/60 |
| TF-IDF baseline | 25/60 | 35/60 |
| paired vs TF-IDF | p=0.481 | p=0.607 |

V2 repairs several weak noetics on Stage 5.2:

| Noetic | v1 | v2 |
|---|---:|---:|
| Idea | 2/6 | 6/6 |
| Male | 0/6 | 6/6 |
| Vibration | 2/6 | 6/6 |
| Above/Cause | 2/6 | 5/6 |

But it also shifts errors elsewhere:

| Noetic | v1 | v2 |
|---|---:|---:|
| Below/Effect | 4/6 | 1/6 |
| Mind | 4/6 | 2/6 |
| Negative | 4/6 | 2/6 |
| Rhythm | 4/6 | 2/6 |

Held-out Stage 5.3 Male diagnostic:

| Metric | v1 | v2 |
|---|---:|---:|
| Male rows total | 7/30 | 29/30 |
| alias-breakdown Male | 7/10 | 10/10 |
| nested-composition Male | 0/10 | 10/10 |
| no-alias Male | 0/10 | 9/10 |
| full diagnostic accuracy | 18/48 | 40/48 |
| TF-IDF baseline | 20/48 | 40/48 |

Honest read:

> The v2 probe repair worked for its target: `^6` Male is no longer
> alias-bound on the held-out diagnostic. It now recognizes nested
> composition and no-alias composition wording. However, global noetic
> transfer is still mixed because improving `^6`, `^0`, `^4`, and `^8`
> shifted errors into `^1`, `^3`, `^7`, and `^9`, and the probe still
> does not reliably beat TF-IDF on paired held-out checks.

Next scientific step:

> Build a balanced v3 noetic transfer dataset with hard contrast pairs
> for the confused involution pairs: `^5`/`^6`, `^8`/`^9`, `^2`/`^3`,
> plus Rhythm-vs-Vibration contrasts. V2 proves targeted repair is
> possible; v3 needs to stabilize the whole vocabulary.

Artifacts:

- `build_pythia_probe_snapshot_v2.py`
- `capture_pythia_activations_for_labels.py`
- `train_noetic_probes_for_activations.py`
- `pythia_probe_labels_v2_20260516.jsonl`
- `pythia_probe_manifest_v2_20260516.json`
- `pythia_probe_activations_v2_20260516.npz`
- `pythia_probe_activations_v2_manifest_20260516.json`
- `pythia_noetic_probes_v2_20260516.npz`
- `pythia_noetic_probes_v2_report_20260516.json`
- `tks_noetic_paraphrase_eval_v2_layer4_report_20260516.json`
- `tks_noetic_male_diagnostic_eval_v2_layer4_report_20260516.json`

## Stage 13 result - multi-layer formula trace audit

**Verdict: CAS Harness can trace hidden activation evidence and flag blind spots across layers.**

Stage 13 reuses the Stage 12 equation/formula activation artifact. It does not run
Pythia again. It trains the same 10-way formula-family readout at every layer and
readout position, then traces each test example across depth.

Headline:

| Metric | Value |
|---|---:|
| Prior Stage 12 reproduction | 0.8995 exactly |
| Best Stage 13 readout | `focus_token` layer 12 |
| Best Stage 13 test accuracy | 0.9540 |
| Best Stage 13 macro-F1 | 0.9551 |
| Test lacunarity | 0.0016 |
| Mean confidence | 0.9637 |
| Normalized entropy | 0.0452 |

Layer scan:

| Readout | Best val layer | Test accuracy | Test lacunarity |
|---|---:|---:|---:|
| `focus_token` | 12 | 0.9540 | 0.0016 |
| `final_token` | 7 | 0.9186 | 0.0018 |
| `mean_over_seq_len` | 5 | 0.6752 | 0.0134 |

Trace stability over all three readouts:

| Trace class | Count |
|---|---:|
| Stable-like | 9,794 / 12,600 |
| Problem-like | 2,806 / 12,600 |
| Stable-like share | 77.7% |
| Problem-like share | 22.3% |

Blind spot candidates are relative to a readout path, not absolute proof that
Pythia cannot represent a concept. The overall top candidates were:
`relation_dependency`, `production_recipe`, `membership_assertion`,
`cover_partition_formula`, and `yield_query`.

Honest read:

> CAS Harness can inspect open-model hidden activations and report where a CAS
> readout is strong, weak, stable, drifting, or internally conflicted. This is
> a real blind-spot audit surface. It does not mean CAS sees exact causal
> neurons, and it does not mean weights "fire." Weights are static parameters;
> activations are the per-input values that change.

Artifacts:

- `STAGE13_MULTILAYER_TRACE_AUDIT_GATES_20260518.md`
- `audit_stage13_multilayer_formula_trace.py`
- `stage13_multilayer_formula_trace_audit_20260518.json`
- `STAGE13_MULTILAYER_FORMULA_TRACE_AUDIT_20260518.md`
- `STAGE13_CLAIMS_MATRIX_20260518.md`

## Stage 14 result - Pythia-2.8B scale replication

**Verdict: `PASS_CLEAN_STAGE14_PYTHIA28B_CPL2_REPLICATES`.**

Stage 14 repeats the Stage 8 eta-to-epsilon readable-prefix likelihood
bridge on `EleutherAI/pythia-2.8b`, using the same frozen Stage 7
28-Foundation fixture and the same CPL2 gate.

Layer selection:

| Metric | Value |
|---|---:|
| Candidate layers | `12-27` |
| Selected layer | `14` |
| Validation accuracy | `1.0000` |
| Test accuracy | `0.8588` |
| Test lacunarity | `0.0059` |

CPL2 result:

| Metric | Value |
|---|---:|
| Probe-readable delta vs none | `+0.5832` |
| Probe-readable minus partner-readable margin | `+1.3363` |
| Positive cases | `92/112` |
| Wilcoxon p | `3.08e-15` |

Scale comparison:

| Model | Delta vs none | Margin over partner | Positive cases |
|---|---:|---:|---:|
| Pythia-160M | `+0.2828` | `+0.6829` | `81/112` |
| Pythia-1B | `+0.5542` | `+1.2460` | `90/112` |
| Pythia-2.8B | `+0.5832` | `+1.3363` | `92/112` |

Honest read:

> The eta-to-epsilon bridge now replicates across three Pythia scales.
> CAS Harness can read a bounded 28-Foundation signal from open-model
> hidden activations and realize it as readable context that shifts semantic
> likelihood. This is still likelihood conditioning, not hidden-neuron
> steering, raw CAS-symbol understanding, or open-ended generation control.

Artifacts:

- `STAGE14_PYTHIA28B_GATES_20260518.md`
- `capture_stage14_pythia28b_activations.py`
- `probe_stage14_pythia28b_cpl2.py`
- `stage14_pythia28b_activations_manifest_20260518.json`
- `STAGE14_PYTHIA28B_PROBE_REPORT_20260518.json`
- `STAGE14_PYTHIA28B_PROBE_REPORT_20260518.md`
- `STAGE14_PYTHIA28B_CPL2_REPORT_20260518.json`
- `STAGE14_PYTHIA28B_CPL2_REPORT_20260518.md`
- `STAGE14_PYTHIA28B_SUMMARY_20260518.md`
- `STAGE14_CLAIMS_MATRIX_20260518.md`

## Stage 13.1 result - blind-spot sanity audit

**Verdict: `BLINDSPOT_LANGUAGE_DEFENSIBLE_WITH_PER_READOUT_BOUNDARY`.**

The Stage 13 blind-spot claim was sanity-checked before publication.

Findings:

- The Stage 12 formula fixture is perfectly balanced: train `360`, val `120`, test `420` per class.
- The `22.3%` problem-like trace count is not explained by fewer rows for the flagged classes.
- The trace thresholds are documented:
  - confidence `< 0.45` on at least half of layer positions
  - entropy `> 70%` of max entropy on at least half of layer positions
  - stable majority `>= 70%` and longest stable run `>= 5`
  - conflicted if switches `>= 5` or no majority over half the layers
- The `80377ab` bug fix changed invalid switch-count iteration only; it did not change thresholds.
- `relation_dependency` is not weak at the best headline readout: `focus_token` layer 12 accuracy `0.9738`. It is mainly a mean-over-sequence readout-path weakness.

Artifact:

- `STAGE13_BLINDSPOT_SANITY_AUDIT_20260519.md`
- `stage13_blindspot_sanity_audit_20260519.json`

## Stage 14.1 result - Pythia-2.8B weight geometry

**Verdict: `CAS_SUBSPACE_WEIGHT_ALIGNMENT_ABOVE_RANDOM_ON_SOME_CHECK`.**

Weights do not fire. This inspection checks whether the learned CAS
Foundation probe subspace is geometrically aligned with Pythia-2.8B's static
token-weight matrices.

Result:

| Check | Actual | Random mean | Random p95 | p(random >= actual) |
|---|---:|---:|---:|---:|
| Output-weight energy fraction | `0.011178` | `0.010524` | `0.010826` | `0.0099` |
| Input-weight energy fraction | `0.010583` | `0.010547` | `0.010667` | `0.3465` |
| Output logit-lens energy on test activations | `0.027121` | `0.009582` | `0.013912` | `0.0099` |

Honest read:

> The Stage 14 CAS Foundation subspace is above random relative to output
> token-weight geometry and logit-lens energy. This supports bounded
> weight-alignment inspection. It does not prove exact causal neurons or
> hidden-state generation steering.

Artifacts:

- `STAGE14_WEIGHT_GEOMETRY_ALIGNMENT_20260519.md`
- `stage14_weight_geometry_alignment_20260519.json`

## Stage 15 result - OLMo-1B cross-architecture replication

**Verdict: `PASS_CLEAN_STAGE15_OLMO1B_CPL2_REPLICATES`.**

Stage 15 repeats the eta-to-epsilon readable-prefix likelihood bridge on
`allenai/OLMo-1B-hf`, a different model family from Pythia.

Layer selection:

| Metric | Value |
|---|---:|
| Candidate layers | `6-16` |
| Selected layer | `16` |
| Validation accuracy | `0.9911` |
| Test accuracy | `0.9060` |
| Test lacunarity | `0.0038` |

CPL2 result:

| Metric | Value |
|---|---:|
| Probe-readable delta vs none | `+0.6037` |
| Probe-readable minus partner-readable margin | `+1.3047` |
| Positive cases | `87/112` |
| Wilcoxon p | `3.17e-12` |

Cross-model comparison:

| Model | Delta vs none | Margin over partner | Positive cases |
|---|---:|---:|---:|
| Pythia-160M | `+0.2828` | `+0.6829` | `81/112` |
| Pythia-1B | `+0.5542` | `+1.2460` | `90/112` |
| Pythia-2.8B | `+0.5832` | `+1.3363` | `92/112` |
| OLMo-1B | `+0.6037` | `+1.3047` | `87/112` |

Honest read:

> The eta-to-epsilon bridge now has pass-clean cross-architecture evidence.
> CAS Harness can read a bounded 28-Foundation signal from OLMo-1B hidden
> activations and realize it as readable context that shifts semantic
> likelihood. This remains likelihood conditioning, not hidden-neuron
> steering, raw CAS-symbol understanding, or open-ended generation control.

Artifacts:

- `STAGE15_OLMO1B_GATES_20260519.md`
- `capture_stage15_olmo1b_activations.py`
- `probe_stage15_olmo1b_cpl2.py`
- `stage15_olmo1b_activations_manifest_20260519.json`
- `STAGE15_OLMO1B_PROBE_REPORT_20260519.json`
- `STAGE15_OLMO1B_PROBE_REPORT_20260519.md`
- `STAGE15_OLMO1B_CPL2_REPORT_20260519.json`
- `STAGE15_OLMO1B_CPL2_REPORT_20260519.md`
- `STAGE15_OLMO1B_SUMMARY_20260519.md`
- `STAGE15_CLAIMS_MATRIX_20260519.md`
- `CAS_HARNESS_EVIDENCE_PACKET_REVIEWER_PLAYBOOK_20260519.md`

## Stage 16 result - Qwen2.5-1.5B cross-architecture replication

**Verdict: `PASS_CLEAN_STAGE16_QWEN15B_CPL2_REPLICATES`.**

Stage 16 repeats the eta-to-epsilon readable-prefix likelihood bridge on
`Qwen/Qwen2.5-1.5B`, giving a third model-family replication after Pythia and
OLMo.

Layer selection:

| Metric | Value |
|---|---:|
| Candidate layers | `8-28` |
| Selected layer | `11` |
| Validation accuracy | `0.9985` |
| Test accuracy | `0.8202` |
| Test lacunarity | `0.0084` |

CPL2 result:

| Metric | Value |
|---|---:|
| Probe-readable delta vs none | `+0.7960` |
| Probe-readable minus partner-readable margin | `+1.6253` |
| Positive cases | `83/112` |
| Wilcoxon p | `2.92e-12` |

Cross-model comparison:

| Model | Delta vs none | Margin over partner | Positive cases |
|---|---:|---:|---:|
| Pythia-160M | `+0.2828` | `+0.6829` | `81/112` |
| Pythia-1B | `+0.5542` | `+1.2460` | `90/112` |
| Pythia-2.8B | `+0.5832` | `+1.3363` | `92/112` |
| OLMo-1B | `+0.6037` | `+1.3047` | `87/112` |
| Qwen2.5-1.5B | `+0.7960` | `+1.6253` | `83/112` |

Honest read:

> The eta-to-epsilon bridge now has pass-clean evidence across three model
> families: Pythia, OLMo, and Qwen. CAS Harness can read a bounded
> 28-Foundation signal from Qwen hidden activations and realize it as readable
> context that shifts semantic likelihood. This remains likelihood
> conditioning, not hidden-neuron steering, raw CAS-symbol understanding, or
> open-ended generation control.

Artifacts:

- `STAGE16_QWEN15B_GATES_20260519.md`
- `capture_stage16_qwen15b_activations.py`
- `probe_stage16_qwen15b_cpl2.py`
- `stage16_qwen15b_activations_manifest_20260519.json`
- `STAGE16_QWEN15B_PROBE_REPORT_20260519.json`
- `STAGE16_QWEN15B_PROBE_REPORT_20260519.md`
- `STAGE16_QWEN15B_CPL2_REPORT_20260519.json`
- `STAGE16_QWEN15B_CPL2_REPORT_20260519.md`
- `STAGE16_QWEN15B_SUMMARY_20260519.md`
- `STAGE16_CLAIMS_MATRIX_20260519.md`

## Stage 17 result - consolidated CAS Harness evidence packet

**Verdict: `CAS_HARNESS_CROSS_ARCHITECTURE_LIKELIHOOD_CONDITIONING_SUPPORTED`.**

Stage 17 is not a new GPU experiment. It consolidates Stages 7-16 into one
reviewer-facing packet and one stricter claims matrix.

Current supported claim:

> CAS Harness replicated a bounded eta-to-epsilon readable-prefix likelihood
> bridge across three model families: Pythia, OLMo, and Qwen.

Current boundary:

> This supports readout, readout-causal tests, blind-spot diagnostics,
> bounded weight-geometry inspection, and readable-prefix likelihood
> conditioning. It does not support exact causal-neuron claims, weights firing,
> raw CAS-symbol understanding, host-model internal compiler validation,
> hidden-state generation steering, or open-ended generated-language control.

Multi-harness composition is recorded as the next hidden-content audit
architecture: current eta-1 readouts are mostly single-axis, while a composite
eta-1 tensor would compare multiple CAS axes and layer bands against emitted
text. The components are supported; a completed multi-axis hiding benchmark is
not yet done.

Artifacts:

- `STAGE17_CAS_HARNESS_EVIDENCE_PACKET_20260519.md`
- `STAGE17_CONSOLIDATED_CLAIMS_MATRIX_20260519.md`

## Stage 18 result - Qwen visible text-quality judge

**Verdict: `NULL_STAGE18_QWEN_VISIBLE_TEXT_SHIFT_NOT_ESTABLISHED`.**

Stage 18 tested whether the Stage 16 Qwen eta-to-epsilon bridge is visible in
generated text, not only in likelihood scores.

Gate result:

| Metric | Result | Gate |
|---|---:|---:|
| Drive judge test accuracy | `0.6679` | `>= 0.65` |
| Probe-readable minus partner-readable margin | `-0.1414` | `>= +0.10` |
| Probe-readable delta vs none | `+0.0178` | `>= +0.05` |
| Probe > partner rows | `12/112` | `>= 65/112` |
| Probe > partner Wilcoxon p | `0.999759` | `< 0.05` |
| Probe raw delta vs none | `-0.1116` | `< +0.05` |

Honest read:

> Stage 18 does not establish visible generated-text shift. The independent
> Drive judge cleared the minimum reliability threshold, but `probe_readable`
> continuations were not judged more target-aligned than `partner_readable`
> continuations. CPL2 likelihood remains the load-bearing eta-to-epsilon
> result.

Observed failure mode:

> Qwen often repeats or blends both focused roles from the prompt. That makes
> the generated continuation visible, but not cleanly separable by the target
> vs partner condition under this prompt and judge.

Artifacts:

- `STAGE18_QWEN_VISIBLE_TEXT_GATES_20260519.md`
- `run_stage18_qwen_visible_text_judge.py`
- `STAGE18_QWEN_VISIBLE_TEXT_REPORT_20260519.json`
- `STAGE18_QWEN_VISIBLE_TEXT_REPORT_20260519.md`
- `STAGE18_QWEN_VISIBLE_TEXT_SAMPLE_PACK_20260519.md`
- `STAGE18_QWEN_VISIBLE_TEXT_CLAIMS_20260519.md`

## Product evidence packet - CAS Harness

**Verdict: `PRODUCT_PACKET_LOCKED`.**

After Stage 18, the product direction is no longer "keep chasing visible
free-form text." The load-bearing measurement is CPL2 likelihood:
`probe_readable` CAS realization shifts semantic likelihood across five model
runs and three architecture families, while raw CAS symbols stay near null.

Stage 18 remains important, but as a boundary:

> Free-form generated text is a lossy channel. Qwen often repeats or blends
> both focused roles from the prompt, so visible continuation text does not
> cleanly expose the likelihood shift.

The CAS Harness product should therefore center on Evidence Packets:

- hidden-state readout
- text/metadata baselines
- readout-causal ablation controls
- lacunarity and blind-spot traces
- weight-geometry appendices
- readable-prefix likelihood conditioning
- raw-symbol controls
- rejected claims and caveats

Language boundary:

> CAS Harness influences semantic likelihood through readable realization. That
> is output influence at the probability-distribution level. The unsupported
> claim is exact sentence forcing in free-form decoding, not output influence
> itself.

And:

> CAS Harness materially opens bounded parts of the black box: readout,
> readout-causal controls, layer traces, blind spots, weight geometry, and
> likelihood conditioning. The unsupported claim is a complete
> neuron-by-neuron causal map of the entire model.

Artifacts:

- `CAS_HARNESS_PRODUCT_EVIDENCE_PACKET_20260519.md`
- `CAS_HARNESS_PRODUCT_EVIDENCE_PACKET_20260519.json`

## Stage 19A result - CAS Verification Stack

**Verdict: `PASS_STRONG_AUDIT_CLEAN`.**

Stage 19A tested the product-realistic verifier on the locked Stage 12
formula-family fixture. Runtime acceptance used only non-oracle signals:
selected-layer ensemble agreement plus trace stability/conflict states. Gold
labels were used only after the fact for scoring.

Headline:

| Metric | Value |
|---|---:|
| Baseline `focus_token` layer-12 accuracy | `0.9540` |
| Ensemble-only accuracy | `0.9550` |
| Ensemble-only coverage | `0.9569` |
| Stack accepted accuracy | `0.9978` |
| Stack coverage | `0.8760` |
| Stack silent error rate | `0.0022` |
| Stack suppressed rate | `0.1240` |
| Accepted examples | `3679/4200` |
| Suppressed examples | `521/4200` |
| Silent accepted errors | `8/3679` |

Product read:

> On this locked formula-family fixture, the CAS Verification Stack accepted
> 87.6% of examples at 99.78% accuracy and suppressed 12.4% as conflicted or
> unstable. A deterministic rerun after commit `05ac687` reproduced every
> headline metric exactly, resolving the initial pre-commit caveat.

Artifacts:

- `STAGE19_CAS_VERIFICATION_STACK_GATES_20260519.md`
- `CAS_VERIFICATION_STACK_SPEC_20260519.md`
- `run_stage19a_formula_verification_stack.py`
- `stage19a_formula_verification_stack_20260519.json`
- `STAGE19A_FORMULA_VERIFICATION_STACK_20260519.md`
- `stage19a_formula_verification_stack_rerun_20260519.json`
- `STAGE19A_FORMULA_VERIFICATION_STACK_RERUN_20260519.md`

## Stage 19B result - Cross-architecture Foundation Verification Stack

**Report status: `NULL`. Practical verdict: `DIAGNOSTIC_ONLY_CROSS_ARCH`.**

Stage 19B reran the runtime-safe Verification Stack on the Stage 15 OLMo and
Stage 16 Qwen Foundation fixtures. It added the Stage 19B factor gate:
independent Drive/Register predictions must recompose to the same 28-way
Foundation label as the Foundation ensemble. Gold labels were used only after
acceptance for scoring.

Headline:

| Model | Best single | Stack accepted acc | Coverage | Silent error | Suppressed |
|---|---:|---:|---:|---:|---:|
| OLMo-1B | `0.9060` | `0.9816` | `0.7173` | `0.0184` | `0.2827` |
| Qwen2.5-1.5B | `0.8537` | `0.9949` | `0.7457` | `0.0051` | `0.2543` |

The stack did **not** reach the pre-registered `PASS_BOUNDED` coverage gate
(`>= 0.800`). So this is not yet a high-coverage external-license result.

The useful finding is diagnostic: on accepted examples, the stack is very
precise across both non-Pythia architectures. The ladder is coherent:

| Model | Ensemble-only | + Factor consistency | + Trace stability |
|---|---:|---:|---:|
| OLMo-1B | `0.8975 / 0.9039` | `0.9422 / 0.8240` | `0.9816 / 0.7173` |
| Qwen2.5-1.5B | `0.9281 / 0.8988` | `0.9661 / 0.8274` | `0.9949 / 0.7457` |

Each gate trades coverage for precision. This supports CAS Harness as a
high-precision diagnostic verifier across architectures, but it does not yet
support the stronger product claim that the Stack is high-coverage across
architectures.

Artifacts:

- `STAGE19B_CROSS_ARCH_FOUNDATION_VERIFICATION_STACK_GATES_20260519.md`
- `run_stage19b_cross_arch_foundation_verification_stack.py`
- `stage19b_cross_arch_foundation_verification_stack_20260519.json`
- `STAGE19B_CROSS_ARCH_FOUNDATION_VERIFICATION_STACK_20260519.md`
- `STAGE19B_CLAIMS_MATRIX_20260519.md`

## Stage 19C result - Verification Stack user-selectable modes

**Verdict: `MODE_SELECTOR_READY`.**

Stage 19C does not rerun hidden-state inference. It packages the locked Stage
19B precision/coverage ladder as explicit user-selectable Verification Stack
modes.

| Mode | OLMo acc / coverage / silent error | Qwen acc / coverage / silent error | Product use |
|---|---:|---:|---|
| `HIGH_PRECISION` | `0.9816 / 0.7173 / 0.0184` | `0.9949 / 0.7457 / 0.0051` | Regulator, legal, safety, and high-trust review where suppression is preferred over a wrong accepted answer. |
| `BALANCED` | `0.9422 / 0.8240 / 0.0578` | `0.9661 / 0.8274 / 0.0339` | Normal customer audit flow where throughput matters but factor conflicts should still be suppressed. |
| `MAX_COVERAGE_TRIAGE` | `0.8975 / 0.9039 / 0.1025` | `0.9281 / 0.8988 / 0.0719` | Exploratory triage and batch review queues where human review remains expected. |

Honest read:

> Users can choose the operating mode. They cannot choose away the tradeoff:
> precision, coverage, silent-error, and suppression move together.

Product rule:

> Default to `BALANCED`; offer `HIGH_PRECISION` for regulator/legal/safety
> workflows where suppression is preferred over wrong acceptance; reserve
> `MAX_COVERAGE_TRIAGE` for candidate surfacing with human review.

Source verification:

> `factor_consistent` was checked against the Stage 19B runner source. It
> requires Foundation ensemble consensus, independently requires Drive and
> Register consensus, recomposes Drive x Register into the 28-way Foundation
> label, and suppresses rows as `factor_conflicted` when recomposition disagrees
> with the Foundation prediction.

Artifacts:

- `STAGE19C_VERIFICATION_MODE_SELECTOR_SPEC_20260519.md`
- `run_stage19c_verification_mode_selector.py`
- `stage19c_verification_mode_selector_20260519.json`
- `STAGE19C_VERIFICATION_MODE_SELECTOR_20260519.md`

## Stage 20 result - Generation Readiness Gate

**Verdict: `IMPLEMENTED_CPU_TESTED`.**

Stage 20 implements the safe version of the old TKS valve intuition as a
diagnostic policy gate, not a learned tensor throttle.

The prior Phase 3 valve lineage is treated as design history and a negative
control: that version learned to suppress generation. Stage 20 therefore does
not port old checkpoints and does not scale `bottleneck_z`, logits, hidden
states, or generated text. It reads existing CAS signals and returns one of:

- `allow`
- `caveat`
- `constrain`
- `suppress`

Inputs:

- lacunarity scores
- lacunarity gap map
- domain confidence
- inversion flags
- RPM satisfaction
- optional Stage 19C Verification Stack decision

Default mode is `BALANCED`, matching Stage 19C.

Product read:

> CAS does not silently choke generation. CAS reports whether generation is
> supported, caveated, constrained, or suppressed, and records the exact
> structural reasons for that decision.

Artifacts:

- `cas-native/model/generation_readiness_gate.py`
- `cas-native/tests/model/test_generation_readiness_gate.py`
- `STAGE20_GENERATION_READINESS_GATE_SPEC_20260519.md`

## Stage 20B result - Generation Readiness packet integration

**Verdict: `PACKET_INTEGRATION_READY`.**

Stage 20B ran the Generation Readiness Gate over locked Stage 19A/19B
Verification Stack reports. No fresh hidden-state inference was run. Neural
lacunarity-head values are not present in the Stage 19 reports, so this run
validates the Verification Stack path of the readiness policy.

Default mode remains `BALANCED`.

Default-mode aggregate policy:

| Source | Allow | Caveat | Constrain | Suppress |
|---|---:|---:|---:|---:|
| Stage 19A Pythia-160M formula fixture | `3678` | `1` | `0` | `521` |
| Stage 19B OLMo-1B cross-arch stack | `1651` | `36` | `0` | `665` |
| Stage 19B Qwen2.5-1.5B cross-arch stack | `1746` | `8` | `0` | `598` |

Triage behavior:

> The same rejected rows that are `suppress` in `BALANCED` become `constrain`
> in `MAX_COVERAGE_TRIAGE`, preserving triage as candidate surfacing rather
> than license-grade acceptance.

Artifacts:

- `run_stage20b_generation_readiness_packets.py`
- `stage20b_generation_readiness_packets_20260519.json`
- `STAGE20B_GENERATION_READINESS_PACKETS_20260519.md`

## Stage 21A result - EvidencePacket v1 export

**Verdict: `EVIDENCE_PACKET_EXPORT_READY`.**

Stage 21A turns the report stack into concrete customer/reviewer artifacts:
one JSON packet and one Markdown packet per trace.

Canonical packets:

| Trace ID | Model | Mode | Accepted | Readiness |
|---|---|---:|---:|---:|
| `stage21a_allow_qwen15b_000` | Qwen2.5-1.5B | `BALANCED` | `true` | `allow` |
| `stage21a_caveat_olmo1b_009` | OLMo-1B | `BALANCED` | `true` | `caveat` |
| `stage21a_suppress_olmo1b_054` | OLMo-1B | `BALANCED` | `false` | `suppress` |
| `stage21a_constrain_olmo1b_054` | OLMo-1B | `MAX_COVERAGE_TRIAGE` | `false` | `constrain` |

Each packet includes:

- model name and revision
- fixture SHA-256
- activation SHA-256
- readout axis/layer/position/label
- Verification Stack mode and mode profile
- Generation Readiness policy
- CPL2 conditioning metrics
- caveats
- rejected claims

Artifacts:

- `evidence_packet.py`
- `run_stage21a_evidence_packet_exporter.py`
- `stage21a_evidence_packet_export_20260519.json`
- `STAGE21A_EVIDENCE_PACKET_EXPORT_20260519.md`
- `evidence_packets/stage21a_*.json`
- `evidence_packets/stage21a_*.md`

## Stage 22 pre-registration - CAS Harness ablation bench

**Verdict: `PREREGISTERED_NO_GPU`.**

Stage 22 applies harness-engineering discipline to the external CAS Harness
product, not to the future CAS Native inner loop. The naming boundary is
locked:

- **CAS Harness** = external inspection/conditioning product around frozen
  open-weight models.
- **CAS Native Cognitive Runtime** = future from-scratch CAS Native inner loop;
  not Stage 22.

The ablation matrix includes a floor, the eta-to-epsilon bridge, user-selectable
Verification Stack modes, the Generation Readiness policy, the full Evidence
Packet/Atlas surface, and a frontier-LLM ceiling reference.

Required metric discipline:

- report useful-output rate with suppression rate
- report coverage with accepted accuracy
- report CPL2 likelihood delta separately from visible free-form generation
- report floor and ceiling comparators so harness lift is interpretable

Default customer mode remains `BALANCED` unless Stage 22 data overturns it.
`HIGH_PRECISION` is opt-in for regulator/legal/safety workflows.
`MAX_COVERAGE_TRIAGE` is opt-in for human-review queues.

Stage 22 is the coarse bench. The upstream gate bundle (Wrap Output Gate,
RPM, Lacunarity, Inversion Scan, Verification Stack, Mode Selector, and
Generation Readiness) is intentionally split in a recommended Stage 22.1
follow-up only after the coarse bench identifies where fine-grained attribution
is worth the extra matrix size.

Artifacts:

- `stage22_harness_ablation_spec.py`
- `run_stage22_harness_ablation_prereg.py`
- `stage22_cas_harness_ablation_prereg_20260519.json`
- `STAGE22_CAS_HARNESS_ABLATION_PREREG_20260519.md`
- `tests/test_stage22_harness_ablation_spec.py`

## Stage 22 result - CAS Harness no-GPU ablation bench

**Verdict: `STAGE22_NO_GPU_ABLATION_BENCH_COMPLETE`.**

Stage 22 executed the first artifact-only harness bench over locked local
reports. No fresh hidden-state inference or GPU run was performed.

Headline:

| Layer | Result |
|---|---:|
| Raw no-prefix floor | mean margin `0.0498` |
| Eta-to-epsilon bridge | mean CPL2 delta `0.5640`; range `0.2828` to `0.7960`; positives `433/560` |
| BALANCED selector | mean coverage `82.6%`; mean accepted accuracy `95.4%` |
| HIGH_PRECISION selector | mean coverage `73.2%`; mean accepted accuracy `98.8%` |
| MAX_COVERAGE_TRIAGE selector | mean coverage `90.1%`; mean accepted accuracy `91.3%` |
| Evidence Packet surface | `4/4` canonical packets complete |
| Frontier ceiling | reference-only; not run |

Product read:

> The harness layers add measurable structure. The readable eta-to-epsilon
> bridge is the largest likelihood-conditioning lift; the mode selector exposes
> the precision/coverage tradeoff; the Evidence Packet layer adds auditability
> rather than model accuracy. Suppression remains paired with useful-output
> rate, so over-refusal is not rewarded.

Artifacts:

- `run_stage22_harness_ablation_bench.py`
- `stage22_cas_harness_ablation_bench_20260519.json`
- `STAGE22_CAS_HARNESS_ABLATION_BENCH_20260519.md`
- `tests/test_stage22_harness_ablation_bench.py`

## Stage 22.1 result - Fine-grained gate attribution

**Verdict: `STAGE22_1_GATE_ATTRIBUTION_COMPLETE`.**

Stage 22.1 split the measurable Stage 19B/19C/20B/21A harness gates without
running fresh inference. It also identified which requested gates cannot be
attributed from the current locked artifacts.

Measured attribution:

| Gate | Attribution |
|---|---:|
| Ensemble-only gate | coverage `90.1%`; accepted accuracy `91.3%` |
| Factor consistency over ensemble | accepted accuracy `+4.1pp`; coverage `-7.6pp` |
| Trace stability over factor consistency | accepted accuracy `+3.4pp`; coverage `-9.4pp` |
| Evidence Packet gate | canonical packet completeness `100.0%` |

Not measurable from locked artifacts:

- RPM gate
- Lacunarity gate
- Inversion scan gate

Reason: Stage 20B explicitly validates the Verification Stack path only; neural
lacunarity-head values and per-row RPM/inversion signals are not present in
the Stage 19/20 locked reports.

Artifacts:

- `stage22_1_gate_attribution_spec.py`
- `run_stage22_1_gate_attribution_bench.py`
- `stage22_1_gate_attribution_prereg_20260519.json`
- `STAGE22_1_GATE_ATTRIBUTION_PREREG_20260519.md`
- `stage22_1_gate_attribution_bench_20260519.json`
- `STAGE22_1_GATE_ATTRIBUTION_BENCH_20260519.md`
- `tests/test_stage22_1_gate_attribution.py`

## Stage 22.2 preflight - Diagnostic gate instrumentation

**Verdict: `INSTRUMENTATION_REQUIRED_BEFORE_ATTRIBUTION`.**

Stage 22.2 defines the artifact contract needed to measure RPM, lacunarity,
and inversion independently. The current locked Stage 19/20 reports do not
contain per-row values for those gates, so treating their absence as a null
effect would be wrong.

Current artifact status:

| Gate | Status | Reason |
|---|---|---|
| RPM | `not_measurable_from_locked_artifacts` | only placeholder `rpm_satisfaction=1.0` policy evidence is present |
| Lacunarity | `not_measurable_from_locked_artifacts` | neural LacunarityHead values are absent |
| Inversion scan | `not_measurable_from_locked_artifacts` | per-row inversion axis outputs are absent |

Required fresh-run per-row fields:

- `rpm_satisfaction`
- `rpm_gate_decision`
- `lacunarity_scores`
- `gap_map_summary`
- `lacunarity_gate_decision`
- `inversion_axis_scores`
- `inversion_flag_count`
- `inversion_gate_decision`
- `gate_decisions`

Product read:

> Stage 22.2 does not weaken the Stage 22/22.1 result. It prevents a false
> attribution claim. The measurable gates already show a precision/coverage
> ladder; RPM, lacunarity, and inversion need a fresh instrumented runner
> before they can be credited or removed.

Artifacts:

- `stage22_2_diagnostic_instrumentation_spec.py`
- `run_stage22_2_diagnostic_instrumentation_audit.py`
- `stage22_2_diagnostic_instrumentation_audit_20260519.json`
- `STAGE22_2_DIAGNOSTIC_INSTRUMENTATION_AUDIT_20260519.md`
- `tests/test_stage22_2_diagnostic_instrumentation.py`

## Stage 22.3 result - Diagnostic sample instrumentation

**Verdict: `STAGE22_3_SAMPLE_INSTRUMENTATION_PARTIAL`.**

Stage 22.3 applied the Stage 22.2 row contract to the accepted sample rows
that retain enough runtime data in the locked Stage 19B report.

Result:

| Item | Value |
|---|---:|
| Accepted sample rows instrumented | `50` |
| Rows with required field names present | `50` |
| Suppressed sample rows seen | `50` |
| Suppressed sample rows with votes | `0` |
| Inversion-ready rows | `0` |

Boundary:

> RPM and lacunarity are proxy-measurable on accepted samples through
> Drive/Register recomposition and readout-vote concentration. They are not
> fresh neural RPM/lacunarity diagnostics. Inversion remains unmeasured.
> Suppressed rows cannot be fully instrumented because the locked report stores
> mostly `index` + `reason`, not readout votes or per-gate signals.

Next requirement:

The Stage 19B-style verifier must be rerun with full per-row diagnostic
emission for accepted and suppressed rows. Until then, Stage 22.3 proves the
row shape but does not close RPM/lacunarity/inversion attribution.

Artifacts:

- `run_stage22_3_diagnostic_sample_instrumentation.py`
- `stage22_3_diagnostic_sample_instrumentation_20260519.json`
- `STAGE22_3_DIAGNOSTIC_SAMPLE_INSTRUMENTATION_20260519.md`
- `tests/test_stage22_3_diagnostic_sample_instrumentation.py`

## Stage 22.4 preflight - Instrumented verifier rerun

**Verdict: `RUNNER_PATCH_READY_LOCAL_ARTIFACTS_MISSING`.**

Stage 22.4 patched the Stage 19B cross-architecture verifier so a fresh
OLMo/Qwen run can emit Stage 22.2-compatible diagnostic rows for every test
example, including suppressed rows. This closes the artifact-shape gap found in
Stage 22.3.

What changed:

- `run_stage19b_cross_arch_foundation_verification_stack.py` now accepts
  `--emit-diagnostics`.
- The runner emits `diagnostic_rows[]` with `rpm_satisfaction`,
  `lacunarity_scores`, `gap_map_summary`, `inversion_axis_scores`,
  `inversion_gate_decision`, and `gate_decisions`.
- Accepted and suppressed rows both get diagnostic rows when the flag is on.
- Gold labels remain scoring-only; runtime diagnostics are derived from votes,
  factor recomposition, and trace states.

Local execution is blocked because the activation binaries are not in this
workspace:

- `stage15_olmo1b_activations_20260519.npz`
- `stage16_qwen15b_activations_20260519.npz`

Pod command:

```bash
python research/cas_probe/run_stage19b_cross_arch_foundation_verification_stack.py \
  --models olmo1b,qwen15b \
  --emit-diagnostics \
  --out-report stage22_4_instrumented_cross_arch_verification_stack_20260519.json \
  --out-md STAGE22_4_INSTRUMENTED_CROSS_ARCH_VERIFICATION_STACK_20260519.md
```

Boundary:

> Stage 22.4 makes RPM and lacunarity proxy attribution runnable on full
> accepted/suppressed rows. It does not yet make inversion attribution numeric:
> inversion fields are emitted as `not_evaluated` / `not_measurable` until a
> real inversion scanner is wired into the verifier.

Artifacts:

- `run_stage19b_cross_arch_foundation_verification_stack.py`
- `run_stage22_4_instrumented_verifier_preflight.py`
- `stage22_4_instrumented_verifier_preflight_20260519.json`
- `STAGE22_4_INSTRUMENTED_VERIFIER_PREFLIGHT_20260519.md`
- `STAGE22_4_INSTRUMENTED_VERIFIER_RUNBOOK_20260519.md`
- `tests/test_stage22_4_instrumented_verifier.py`
