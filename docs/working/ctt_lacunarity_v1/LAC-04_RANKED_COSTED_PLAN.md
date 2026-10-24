# LAC-04 — Ranked, costed experimental plan (CAS-LAC-001, Phase 1 exit)

Status: **plan only. Nothing below is approved or running.** Spend to date ~2.40 USD (historical, two training runs).
Each item states the decision its result could change, because an experiment that cannot change a decision should not
run.

## Rank 1 — Re-run N1 with the preregistered exposure and deduplicated rows (free)

**What.** Recompute the held-out Noetic result using (a) row-count exposure as preregistered, not token occurrences;
(b) the 500 distinct (text, target) rows, not 588 with duplicates; (c) the preregistered unit `cas_val` as a separate
reading, since `notation_dev99` was an undeclared substitution.

**Decision it changes.** Whether the project's current claim is "neglect" (low-exposure cells worse, 3 of 3 under the
row split) or "overfitting" (the published, uncorrected claim). It also settles whether the 88 duplicate rows changed
the verdict.

**Cost.** 0 USD, under an hour, on existing scores.

**Gate.** If the corrected verdict does not survive deduplication, the N1 result becomes a null and the Noetic family
drops to "diagnostically unevaluated".

## Rank 2 — Mathematical verification of the implemented family (free)

**What.** Hand-computed cases and negative controls for the five CAS dimensions (Rust and Python must agree on a
shared vector), the 40-slot gate read-out with the correction disabled, and the gliding-box estimator at `b=1`
(where the identity `Λ = L − 1` holds).

**Decision it changes.** Whether any existing number produced by `lacunarity.rs` / `api/pipeline/lacunarity.py` can be
trusted as the formula it claims to be, and whether the two implementations are the same measure.

**Cost.** 0 USD, coding plus tests.

## Rank 3 — Implement and falsify R-2 and P-2 on synthetic structures (free)

**What.** Recipe fragility (`F`) and RPM chain fragility on small hand-built graphs where the right answer is
obvious: a single-ingredient recipe, a two-path recipe, a chain, a star, a cycle. Negative controls: uniform graphs
should score near 0.

**Decision it changes.** Whether the Recipe and RPM families are implementable at all from the current compiler and
RPM engines, or whether they need new structural export first.

**Cost.** 0 USD, coding.

## Rank 4 — Second independent Noetic source (costed)

**What.** Build a second held-out Noetic set from source material that never touched training. The 99 DEV rows are
exhausted; the three SDG files are fully used. Options: a new SDG generation batch (LLM cost, roughly 3–5 USD at the
2026-05 rates recorded in the SDG files, needing owner approval), or an independently authored set (human time).

**Decision it changes.** Whether the N1 result replicates; without it the Noetic family cannot pass "Replicated" and
cannot be proposed as a control signal.

**Cost.** 3–5 USD for generated SDG plus 0 GPU. Requires approval.

## Rank 5 — One intervention trial, only if Ranks 1–4 pass (costed)

**What.** Target the low-exposure cells (or the gap cells from N-2) with a bounded replay set, against undirected
extra training and against a random-replay control, at equal compute. Primary outcomes: held-out generation
composite and held-out Noetic error.

**Decision it changes.** Whether a diagnosis can select a repair that beats undirected training. This is the only
experiment that can move a measure from "predicts" to "intervention validated".

**Cost.** One g5.xlarge run is ~1.1–1.2 USD at the measured rate; three arms would be three runs, ~3.5 USD, or one
run with three conditions if the harness allows. Requires explicit approval.

## What must not happen yet

- No training-loop wiring, no shadow mode, no automatic repairs.
- No combined "Λ" score (LAC-06 is not reached).
- No promotion of any measure above "Diagnostically Evaluated" without Ranks 1–4.

## Dependencies

```
Rank 1 (correction) ──► decides whether Noetic family continues
Rank 2 (math) ───────► required before any existing CAS number is quoted
Rank 3 (recipe/RPM) ─► required before those families get an evaluation plan
Rank 4 (second source) ─► required for Replicated status
Rank 5 (intervention) ──► only after 1–4, with approval
```

## The decision requested from the owner

Approve Rank 1 only (free, immediate). Ranks 2 and 3 need no money and no approval beyond "go". Rank 4 needs 3–5 USD.
Rank 5 needs a further 3.5 USD and should not be considered until 1–4 report.
