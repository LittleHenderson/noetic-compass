# Stage 7 Research Roundtable: Next Route After 28-Foundation Results

**Status:** research planning artifact. No new experiment launched in this
document.

**Date:** 2026-05-17

**Branch:** `experiment/cas-probe-pythia`

**Purpose:** integrate the four-agent research roundtable after Stage 7.0-7.3
so the next experiment is a real solution attempt, not another unbounded hook
variant.

## One-Paragraph Read

Stage 7 is not a failure. It proves that Pythia-160M carries a strong
28-Foundation / Drive internal readout beyond text, and that removing the
trained subspace collapses the CAS readout to chance. Stage 7.3 only failed the
stronger claim that this same focus-token Drive removal steers short greedy
generation better than random removals. The next route is to stop measuring
generic free-text drift and instead test a fresh, bounded semantic decision:
does removing the Drive subspace reduce Pythia's logit margin for the correct
Drive choice more than random rank-matched removals?

## Roundtable Inputs

Four independent research threads were used:

| Thread | Focus | Main Finding |
|---|---|---|
| CAS / TKS internals | Original TKS 28 Foundations, CAS architecture, lacunarity, fractals, compiler semantics | The 28-Foundation factorization cleaned up readout because Drive x Register is structurally cleaner than the 10-noetic axis, but Pythia lacks the typed CAS decoder machinery that would make CAS transitions directly control output. |
| Mathematical / mechanistic theory | Linear algebra, observability vs controllability, Jacobian routing, logit margins | A probe can observe a direction without that direction controlling the model's output logits. Readout-causal ablation is not the same as generation-causal control. |
| Experiment design | Endpoint design, controls, preregistration | Free generation token match is too blunt. The next claim-bearing test should be a fresh forced-choice Drive logit-margin assay with locked layer/subspace choices. |
| Skeptical statistics | Confounds, controls, claims discipline | Stage 7.0-7.2 are strong for readout. Stage 7.3 is a real negative for the tested hook. Any next positive must use fresh data, cluster-aware statistics, stronger controls, and predeclared pass gates. |

## What Stage 7.3 Actually Ruled Out

Stage 7.3 rules out this narrow claim:

> Removing the Stage 7 Drive readout subspace at the focus token, layer 6,
> during short greedy continuation changes generated text more than same-rank
> random removals.

It does not rule out:

- Drive or 28-Foundation hidden-state readout. Stage 7.0 passed that.
- Readout-causal ablation. Stage 7.1 and Stage 7.2 passed that.
- Generation effects at other positions, other layers, longer semantic tasks,
  nonlinear directions, or forced-choice logits.
- Semantic steering. Stage 7.3 measured token-match disruption, not semantic
  routing toward a target Drive.

The current boundary is:

> CAS can read and verify the Foundation signal inside Pythia. CAS has not yet
> shown that this signal can steer Pythia's open-ended generated language.

## Why The Gap Exists

The math is simple:

- The probe reads a vector from hidden states.
- Removing that vector breaks the probe.
- But Pythia's next-token head may not use that same vector to choose words.

In control-theory language, the signal is **observable** by CAS, but not yet
shown to be **controllable** for generation.

In linear-algebra language, Stage 7.1 proves the trained readout depends on the
Drive / Foundation subspace. It does not prove that Pythia's output logits have
a large Jacobian along that same subspace.

In CAS language, the 28 Foundations appear as an inspectable internal
structure. Pythia does not have CAS Native's typed transition system, compiler
constraints, or CAS decoder, so the internal structure does not automatically
become a clean steering knob.

## What Not To Do Next

The roundtable consensus is to stop these as primary claim-bearing tests:

- Do not run another unmodified free-generation ablation hook.
- Do not promote Register generation claims; Register was text-explained in
  Stage 7.2.
- Do not run full 28-rank generation hooks as the next pass gate; rank 27 is
  too broad and likely to cause collateral damage.
- Do not start cross-model spending until the within-model endpoint is clean.
- Do not refresh Glass House public strategy language until this next boundary
  test is complete.
- Do not claim "generation control" from readout-causal ablation alone.

## Recommended Stage 7.4

**Name:** Fresh Drive Forced-Choice Logit-Margin Test

**Question:** When Pythia must choose between two Drive meanings, does removing
the locked Drive subspace reduce the correct Drive choice margin more than
random rank-matched removals?

This is a better endpoint because it avoids open-ended prose drift. It asks a
bounded semantic question with a measurable probability margin.

## Stage 7.4 Design

### Fixture

- Build a fresh held-out fixture, not copied from the existing Stage 7 rows.
- Use same-register Drive contrasts only.
- Each record gives two role descriptions, one focus marker, and a two-choice
  question.
- Options are randomized and balanced.
- Correct and incorrect answer tokens must be tokenizer-verified as single
  tokens before the record is accepted.
- The fixture must include lexical bundles / template ids so analysis can
  bootstrap by cluster, not just by row.

Example shape:

```text
Role A: The trainer gives a reward the animal wants.
Role B: The trainer repeats the same command at fixed intervals.
Focus: A
Question: Which option best describes the focused role?
Options:
1. Reward / affinity
2. Repetition / rhythm
Answer:
```

The model is not asked to generate a paragraph. The scored target is the logit
margin between the correct and incorrect option token.

### Locked Intervention

- Use the frozen Stage 7.2 Drive projection.
- Layer: `focus_token` layer 6.
- Rank: 6.
- No layer shopping.
- No direction shopping.
- No prompt-template fishing after locked test starts.

### Primary Metric

For each row:

```text
margin = logit(correct_option_token) - logit(incorrect_option_token)
```

Then compare:

```text
extra_margin_drop =
  (baseline_margin - drive_ablation_margin)
  - mean(baseline_margin - random_ablation_margin)
```

Positive means the Drive ablation damages the correct Drive choice more than
random removals.

### Controls

Minimum controls for calibration:

- 30 same-rank random controls.
- No-hook determinism.
- Option-order balance.
- Label-shuffled sanity check.

Preferred controls for locked test:

- 100 same-rank random controls if runtime stays practical.
- Shuffled-label probe subspace as a negative control.
- Cluster-aware bootstrap by lexical bundle / pair / template.
- Row-level paired permutation test.

### Calibration Gate

Run calibration first, then stop if the task itself is not viable:

- `n = 280` calibration rows.
- Unablated two-choice accuracy must be at least `0.60`.
- Mean correct margin must be at least `0.25` logits.

If calibration fails, the assay is invalid. Do not interpret that as a causal
negative.

### Locked Test

If calibration passes:

- `n = 840` locked rows.
- No changes to layer, rank, metric, pass gates, or prompt family.

Pass gates:

- Mean extra margin drop over random controls `>= 0.10` logits.
- One-sided paired permutation p `<= 0.01`.
- Bootstrap 95 percent confidence interval lower bound `> 0.03`.
- At least `5/7` Drives positive.
- At least `3/4` registers positive.
- Secondary gate: Drive ablation reduces two-choice accuracy at least `5 pp`
  more than random controls.

### Expected Cost

This is cheaper and cleaner than autoregressive generation. It scores logits at
one answer position, not 8-token continuations.

Approximate locked-test size:

```text
840 rows x (1 baseline + 1 Drive hook + 30 to 100 random hooks)
```

Expected runtime on A6000: roughly 10-30 minutes, depending on the random
control count.

## Interpretation Matrix

| Result | Meaning |
|---|---|
| Calibration fails | The forced-choice fixture is not valid for Pythia-160M. Redesign the assay before any causal claim. |
| Calibration passes, Drive margin drop fails | Pythia carries a Drive readout, but that readout is not controlling this bounded semantic decision. Treat Stage 7 as readout-only for Pythia-160M. |
| Calibration passes, margin drop beats random | Drive subspace is not only readable and readout-causal; it also influences a bounded semantic Drive decision. This upgrades the mechanistic claim beyond Stage 7.3. |
| Margin passes but only for a few Drives/registers | Localized partial control. Report as partial and inspect lacunarity/gap map. |
| Margin passes broadly | Strong within-model evidence. Next step becomes counterfactual patching or cross-model replication. |

## Optional Diagnostic After Stage 7.4

If Stage 7.4 fails but calibration is strong, run diagnostics rather than
changing the pass gate:

1. Jacobian routing score: measure whether the output logits are sensitive to
   the Drive subspace relative to random rank-6 subspaces.
2. Unembedding alignment: check whether Drive directions project into answer
   option logits.
3. Margin sensitivity: check whether the hook effect is smaller than the
   baseline top-choice margin.

These diagnostics explain failure. They should not be allowed to replace the
pre-registered pass gate.

## Stakeholder-Safe Wording

Safe now:

> "CAS found a verified internal 28-Foundation readout inside Pythia-160M.
> Removing that subspace collapses the CAS readout to chance. That is real
> internal evidence, but not yet proof that CAS controls Pythia's generated
> language."

Safe after a Stage 7.4 pass:

> "On a fresh forced-choice Drive task, removing the Drive subspace reduced the
> correct Drive choice margin more than random removals. That shows the internal
> CAS Drive signal affects a bounded semantic decision in Pythia-160M."

Still not safe:

> "CAS solved the black-box problem."

> "CAS can steer any model."

> "Pythia thinks in CAS."

## Roundtable Consensus

The next move is not surrender and not hype. The next move is a cleaner test.

Stage 7 already earned the right to continue because the 28-Foundation signal
beat text, beat metadata, and survived readout-causal ablation. Stage 7.3 taught
us that open-ended generation token matching is the wrong endpoint for the next
claim. Stage 7.4 should test a bounded semantic decision where the Drive signal
has a fair chance to matter and where the statistic is direct enough for an
outside reviewer to audit.

## Audit Questions For Codex

1. Is the Stage 7.4 forced-choice logit-margin endpoint the right next
   claim-bearing test after the Stage 7.3 negative?
2. Should locked-test random controls be 30 or 100, given runtime and
   statistical resolution?
3. Are the pass gates strict enough to avoid p-hacking while still allowing a
   real effect to surface?
4. Should the shuffled-label probe subspace be mandatory in the locked test or
   only a diagnostic?
5. Does this memo preserve the correct claim boundary from the Stage 7 claims
   matrix?

## Post-Roundtable Execution Addendum

The user then supplied a Claude research synthesis that challenged this memo's
ordering. It argued that two free output-alignment diagnostics should run before
any fresh Stage 7.4 fixture, and that if the old layer-6 subtraction route
looked wrong, the fallback should be a late-layer additive probe at layers 10
and 11, with the Embodied register tested explicitly.

Those checks were run.

### Stage 7.OA: Output-Alignment Diagnostics

Report:

- `stage7_output_alignment_diagnostics_20260517.json`
- `STAGE7_OUTPUT_ALIGNMENT_DIAGNOSTICS_20260517.md`

Result:

- Raw principal-angle-to-unembedding-row-space test is degenerate for
  Pythia-160M because the unembedding is full hidden-rank: `768/768`.
- Drive subspace: `OUTPUT_ALIGNMENT_NEAR_RANDOM`.
- 28-way interaction subspace: `OUTPUT_ALIGNMENT_NEAR_RANDOM`.
- Verdict: `STAGE7_SUBSPACES_NOT_OUTPUT_ALIGNED_ABOVE_RANDOM`.

Interpretation:

> The Stage 7 layer-6 readout subspaces are real observer/readout directions,
> but they are not specially aligned with Pythia's output head by these
> diagnostics. This explains why layer-6 subtraction did not steer generation.

### Stage 7.LA: Late-Layer Additive Probe

Reports:

- `stage7_late_layer_additive_probe_20260517.json`
- `STAGE7_LATE_LAYER_ADDITIVE_PROBE_20260517.md`
- `stage7_late_layer_additive_probe_embodied_20260517.json`
- `STAGE7_LATE_LAYER_ADDITIVE_PROBE_EMBODIED_20260517.md`

All-register exploratory run:

- Layers: 10 and 11.
- Alpha sweep: `-4, -2, +2, +4`.
- Random rank-1 controls: 30.
- Best condition: layer 11, alpha `-2`.
- Extra signed margin over random: `+0.0488`.
- Empirical p: `0.2581`.
- Positive share: `0.179`.
- Verdict: `EXPLORATORY_LATE_LAYER_ADDITIVE_NOT_ABOVE_RANDOM_GATE`.

Embodied-only `|E` run:

- Same layers, alpha sweep, and controls.
- Best condition: layer 11, alpha `+4`.
- Extra signed margin over random: `+0.0440`.
- Empirical p: `0.1935`.
- Positive share: `0.357`.
- Verdict: `EXPLORATORY_LATE_LAYER_ADDITIVE_NOT_ABOVE_RANDOM_GATE`.

Interpretation:

> Claude's fallback was worth trying, but it did not clear the random-control
> gate in this Pythia-160M setup. The best effects are small, not reliable, and
> not broad across cases.

### Updated Route

The evidence now supports this stricter boundary:

- Stage 7 readout is strong.
- Stage 7 readout-causal ablation is strong.
- Stage 7 factorization is strong for Drive and full Drive x Register
  interaction.
- Layer-6 output alignment is not above random.
- Late-layer additive Drive steering is not above random in the exploratory
  test, including the Embodied-only slice.

The next move should not be another simple ablation/addition hook. If we keep
working Pythia-160M, the next route is either:

1. **Fresh Stage 7.4 forced-choice fixture** as a final bounded confirmation
   that Pythia-160M remains readout-only under a clean held-out assay, or
2. **Path/SAE diagnostics** to locate whether the Foundation signal routes
   through polysemantic features that a linear Drive direction cannot isolate.

The safe claim does not change:

> CAS opens a verified internal readout window inside Pythia-160M. It has not
> shown steering control over Pythia-160M generated language.

## Eta-To-Epsilon Addendum: CAS Prefix Likelihood

The user then identified the missing mathematical bridge more precisely:

- The Foundation probe is an embedding/readout map (`eta`): hidden states to
  CAS structure.
- Generation needs a realization map (`epsilon`): CAS structure to tokens /
  language.
- Prior tests tried to use `eta` as if it were `epsilon`.

That led to a separate prefix-likelihood test:

- Script: `probe_stage7_cas_prefix_likelihood.py`
- Report: `stage7_cas_prefix_likelihood_20260517.json`
- Summary: `STAGE7_CAS_PREFIX_LIKELIHOOD_20260517.md`

This test avoids the failed numbered-choice behavior. It scores whether Pythia
assigns higher conditional likelihood to the true Drive phrase than the partner
Drive phrase under different prefixes.

Result:

- Status: `READABLE_PREFIX_CONDITIONS_PYTHIA_LIKELIHOOD`.
- Raw CAS-symbol prefix does not help:
  - `raw_correct` delta vs none: `-0.0200`.
  - `raw_correct_minus_raw_partner_margin`: `-0.0182`.
- Human-readable CAS realization does help:
  - `gloss_correct` delta vs none: `+0.3573`, with `77/112`
    positive cases.
  - `gloss_partner` delta vs none: `-0.3742`.
  - `gloss_correct_minus_gloss_partner_margin`: `+0.7314`.
  - `plain_correct` delta vs none: `+0.4839`, with `90/112`
    positive cases.
  - `plain_partner` delta vs none: `-0.4662`.
  - `plain_correct_minus_plain_partner_margin`: `+0.9501`.

Interpretation:

> The missing bridge is not "Pythia understands CAS symbols." It does not. The
> bridge is "CAS can realize its readout into readable structure, and that
> readable structure conditions Pythia through normal attention."

This reopens the practical CAS Harness route while keeping the internal-claims
boundary clean:

- Still not proven: internal-neuron steering.
- Now supported: external CAS Harness conditioning via readable realization.
- Product implication: the Harness can read a CAS structure, render it as an
  auditable prefix/context, and make Pythia's likelihood move toward the
  intended semantic continuation.

Next clean experiment:

1. Replace gold prefixes with probe-predicted prefixes (`eta -> epsilon` full
   loop).
2. Compare correct probe prediction vs intentionally wrong prefix on fresh
   held-out rows.
3. If pass-clean, move from likelihood scoring to short constrained generation.

## Full Eta-To-Epsilon Loop Result

The next clean experiment was run.

- Script: `probe_stage7_cas_prefix_full_loop.py`
- Report: `stage7_cas_prefix_full_loop_20260517.json`
- Summary: `STAGE7_CAS_PREFIX_FULL_LOOP_20260517.md`

Design:

1. Fit the Stage 7 Foundation probe on the locked activation split.
2. Predict each selected test row's Foundation label from Pythia hidden states.
3. Realize the predicted label as readable CAS context.
4. Score Pythia's conditional likelihood of the true Drive phrase vs the
   partner Drive phrase.
5. Compare against gold-readable, wrong-partner-readable, and raw-symbol
   controls.

Result:

- Status: `PROBE_PREDICTED_CAS_PREFIX_CONDITIONS_PYTHIA`.
- Selected-row Foundation accuracy: `0.7857`.
- Selected-row Drive accuracy: `0.8482`.
- No prefix margin: `+0.0031`.
- Gold readable prefix:
  - margin `+0.3954`
  - delta vs none `+0.3923`
  - `91/112` positive cases.
- Probe-predicted readable prefix:
  - margin `+0.2860`
  - delta vs none `+0.2828`
  - `81/112` positive cases.
  - sign p reported as `0.0000` in the summary table.
- Wrong partner readable prefix:
  - margin `-0.3969`
  - delta vs none `-0.4000`.
- Raw CAS symbols stay flat:
  - `gold_raw` delta `-0.0032`.
  - `probe_raw` delta `-0.0011`.

Updated claim:

> CAS Harness can close the loop on Pythia-160M by reading a Foundation label
> from hidden states, realizing that label as readable CAS context, and moving
> Pythia's semantic likelihood in the intended direction.

Still not claimed:

- Raw CAS notation steering.
- Hidden-neuron steering.
- Pythia-native CAS understanding.
- Open-ended generation control.

The next experiment should be short constrained generation using
probe-predicted readable prefixes, with wrong-prefix controls and sample-read
auditing.

## Short Generation Follow-Up

The short generated-text follow-up was run as Stage 7.CPL3.

- Script: `probe_stage7_cas_prefix_generation.py`
- Report: `stage7_cas_prefix_generation_20260517.json`
- Summary: `STAGE7_CAS_PREFIX_GENERATION_20260517.md`
- Sample read: `STAGE7_CAS_PREFIX_GENERATION_SAMPLES_20260517.md`

Design:

1. Fit the same Stage 7 Foundation probe.
2. Select locked test rows with same-register Drive-cycle partners.
3. Predict each selected row's Foundation label from Pythia hidden states.
4. Generate short greedy continuations (`max_new_tokens=16`) under five
   conditions:
   - no prefix
   - gold-readable CAS realization
   - probe-predicted readable CAS realization
   - wrong-partner readable CAS realization
   - probe-predicted raw CAS symbol
5. Score visible continuations with a simple target-vs-partner Drive keyword
   heuristic and preserve samples for human review.

Result:

- Status: `PROBE_PREFIX_GENERATION_HEURISTIC_NOT_CLEAN`.
- Selected rows: `56` (`8` per Drive).
- Selected-row Foundation accuracy: `0.8750`.
- Selected-row Drive accuracy: `0.9286`.
- No-prefix baseline:
  - target win `0.018`
  - margin `+0.036`.
- Probe-predicted readable prefix:
  - target win `0.125`
  - margin `+0.107`
  - delta vs none `+0.071`.
- Wrong partner readable prefix:
  - target win `0.054`
  - margin `-0.125`
  - delta vs none `-0.161`.
- Key comparison:
  - `probe_readable_margin_minus_partner_readable = +0.2321`.
  - The pre-set clean-pass floor was `+0.25`.
- Probe-predicted raw CAS symbols:
  - target win `0.018`
  - margin `0.000`
  - delta vs none `-0.036`.

Interpretation:

> The generated text shows the same directional shape as the likelihood test:
> readable CAS realization helps more than no prefix, wrong-readable pushes
> against the target, and raw symbols do not help. But the short-generation
> heuristic is too weak/noisy to clear the pre-registered clean-pass floor.

Claim boundary:

- Still supported: CPL2 likelihood-space CAS Harness conditioning.
- Weakly suggested: readable prefixing can alter visible short continuations in
  the expected direction.
- Not supported: pass-clean open-ended generation control.
- Still unsupported: raw-symbol steering or internal hidden-neuron steering.

## Generated-Text Classifier Judge

A stricter generated-text quality check was then run as Stage 7.CPL4.

- Script: `judge_stage7_cas_prefix_generation.py`
- Report: `stage7_cas_prefix_generation_text_judge_20260517.json`
- Summary: `STAGE7_CAS_PREFIX_GENERATION_TEXT_JUDGE_20260517.md`
- Blind judge pack:
  `STAGE7_CAS_PREFIX_GENERATION_TEXT_JUDGE_PACK_20260517.md`

Design:

1. Train independent text-only judges on the original Stage 7 fixture text.
2. Select judge model by validation accuracy.
3. Evaluate judge reliability on the locked Stage 7 fixture test split.
4. Apply the judge to CPL3 generated continuations only after training.
5. Compare probe-readable outputs against no-prefix, wrong-partner-readable,
   and raw-prefix controls.

Result:

- Status: `PROBE_PREFIX_GENERATED_TEXT_CLASSIFIER_SHIFT_NOT_CLEAN`.
- Drive judge: `tfidf_char_3_5`, test accuracy `0.6679`, macro-F1 `0.6546`.
- Foundation judge: `tfidf_char_3_5`, test accuracy `0.4966`, macro-F1
  `0.4801`.
- Drive axis:
  - probe-readable delta vs none `+0.0256`.
  - probe-readable margin minus partner-readable `-0.0103`.
  - probe target-pred rate minus partner target-pred rate `0.0000`.
- Foundation axis:
  - probe-readable delta vs none `+0.0202`.
  - probe-readable margin minus partner-readable `-0.0047`.
  - probe target-pred rate minus partner target-pred rate `0.0000`.

Interpretation:

> The generated text does not close under an independent text classifier. The
> classifier sees a small positive delta versus no prefix, but not a clean
> target-over-partner shift. The Drive judge is also below the pre-set `0.70`
> reliability floor.

Updated boundary:

- Load-bearing positive: CPL2 likelihood-space eta-to-epsilon bridge.
- Directional but not clean: CPL3 short generated-text keyword heuristic.
- Not clean: CPL4 independent classifier judge.
- Next product-relevant gate: cross-model CPL2 replication, not more
  hidden-state surgery.
