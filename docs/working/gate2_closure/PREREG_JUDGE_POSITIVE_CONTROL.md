# PRE-REGISTRATION — `JUDGE-POSITIVE-CONTROL-v1`

**Committed BEFORE any data is collected.**
**Date:** 2026-07-27
**Gate 2 status at time of writing:** OPEN at `0.38`

---

## The gap this closes

Every instrument in this campaign compared **two things that might both be undetectable**.
Sixteen runs, and not one of them ever asked the prior question:

> Can this measurement apparatus detect a signal it definitely should catch?

That is a **positive control**, and its absence is a real methodological hole. Without it, a
null result has two explanations that cannot be told apart:

1. There is no signal to find. *(the substantive reading)*
2. The apparatus cannot find any signal, including ones that are certainly present.
   *(the plumbing reading)*

Eight `NOT_LICENSED` verdicts currently rest on explanation (1) being assumed rather than shown.

---

## Design

Same judge, same choice set, same harness, same parse path as the scaled matched A/B
(`run_matched_ab.py`). **Only the item text varies.** Three difficulty tiers:

| Tier | Item text | Purpose |
|---|---|---|
| `T0` | The choice-key definition, **verbatim** | Plumbing / ceiling. Judge is shown the exact string that is also the correct answer. |
| `T1` | The same definition under a **deterministic, meaning-preserving rewrite** (clause reordering + fixed synonym table; **no LLM**, so it cannot vary run to run) | Sensitivity. Can the judge discriminate 28-way when information is complete but wording differs? |
| `T2` | **Real authored items**, sampled from the existing committed fixtures | The actual task. Known to sit near chance. |

- `28` foundations × `10` items = **`280` rows per tier**, `840` total.
- Chance accuracy = `1/28` = **`0.0357`**.
- Judge `models/gemini-2.5-flash`, `temperature 0.0`, batch size `10` — identical to the A/B run.
- `T2` rows are drawn from committed fixtures with a fixed seed; **no new authoring**, so the
  arm-A/arm-D question is untouched by this control.

---

## Frozen criteria

| # | Criterion | Bar |
|---|---|---|
| `C1` | **Harness integrity** | `T0` accuracy `>= 0.90` |
| `C2` | **Instrument sensitivity** | `T1` accuracy `>= 0.50` |
| `C3` | **Difficulty localization** | `T1 - T2 >= 0.20` |
| `C4` | **No degenerate collapse** | no single foundation predicted for `> 30%` of rows, any tier |

---

## Pre-committed consequences

These are written now so they cannot be chosen after seeing the numbers.

- **`C1` FAILS** → `HARNESS_DEFECT`. The judge cannot identify a definition when handed that
  definition verbatim, which means the wiring is broken (choice-set mismatch, id misalignment,
  parse failure, or prompt defect). **Every `NOT_LICENSED` verdict in the ledger is
  reclassified as uninterpretable pending repair**, and the handoff package is corrected. This
  is the branch that matters most and the reason this control is worth running.

- **`C1` passes, `C2` FAILS** → `TASK_INTRACTABLE`. The harness is fine, but 28-way matching
  defeats this judge even with complete information. The instrument is **not fit for purpose**
  and a different readout is required. This does **NOT** speak to the definitions either way —
  it means the question was never actually put to a competent referee.

- **`C1` passes, `C2` passes, `C3` passes** → `JUDGE_FUNCTIONAL`. The scoring apparatus
  demonstrably discriminates on a small model with fair comparison and honest error bars, and
  the difficulty is localized to the **authoring/paraphrase** step rather than the judge. This
  is a genuine positive demonstration of instrument function.

- **`C1` passes, `C2` passes, `C3` FAILS** → `UNLOCALIZED`. Judge works, paraphrase is not the
  bottleneck. Requires separate investigation; no claim licensed.

- **`C4` FAILS** → `VOID_DEGENERATE` for the affected tier.

---

## Ceiling on what a PASS licenses

A `JUDGE_FUNCTIONAL` outcome licenses **only** this wording:

> *"The 28-way foundation-matching judge discriminates above chance on `models/gemini-2.5-flash`
> when definition information is complete, and the near-chance performance observed in the
> matched A/B is attributable to the authored-item step rather than to the judge."*

It licenses **nothing** about TKS versus CAS, nothing about any other model, and no product
claim. It does not by itself close Gate 2 — it establishes whether the instrument used for
Gate 2 is capable of the discrimination Gate 2 asks about.

---

## Why this cannot manufacture a favourable result

- `T0` and `T1` items are generated **mechanically from the canon file**, with no LLM in the
  loop, so they cannot be tuned toward a pass.
- `T2` items are **already committed to git** and are sampled with a fixed seed.
- The synonym table and clause-reordering rule are frozen in the runner **before** execution and
  committed with this pre-registration.
- No arm comparison occurs, so no superiority claim is reachable from this design at all.

---

## Status

`LOCKED / COMMITTED BEFORE DATA / NOTHING LICENSED`
