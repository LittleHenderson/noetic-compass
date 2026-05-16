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
