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
