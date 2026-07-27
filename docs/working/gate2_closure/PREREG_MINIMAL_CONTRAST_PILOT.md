# PRE-REGISTRATION — `MINIMAL-CONTRAST-PILOT-v2`

**Committed BEFORE any v2 item is generated AND before `SPEC-AUTHORED-SCENARIOS-v1` produced a
single accuracy number.** At time of writing, v1 had authored `39/84` items and judged `0`.
That ordering is deliberate: the hypotheses and bars below were specified by the owner without
sight of any result, and this commit preserves that fact.

**Date:** 2026-07-27
**Gate 2 status:** OPEN at `0.38`
**Design authority:** owner-specified. Deviations are listed in §9 and are all conservative.

---

## 1. What this supersedes and why

`SMALL-MODEL-SEMANTIC-MATCH-v1` was voided (`cb0eaffd`) for testing **positional** equivalence
rather than demonstrated **semantic** equivalence: the 28-Foundation material defines slots `5`–`7`
as *power*, *material resources*, and *lust/reproduction*, so substituting *Agency*, *Structure*,
and *Purpose* changes the construct even when the grid coordinate is fixed. That void stands, and
its partial numbers remain published exactly as recorded.

`SPEC-AUTHORED-SCENARIOS-v1` (`59d63dd5`) remains valid on its own terms as a **first-pass
authoring-quality probe**. It lacks contrast pairs, staged judge decomposition, and a pairwise
endpoint. This design adds all three.

**This is the first valid test of *behaviorally encoded Foundation recoverability under lexical
distance*.**

---

## 2. Item structure — `84` base items

Every Foundation receives three items:

| Slot | Contrast type | Purpose |
|---|---|---|
| 1 | `target` | positive item |
| 2 | `same_drive_diff_world` | tests **World** discrimination |
| 3 | `same_world_diff_drive` | tests **drive** discrimination |

`28 × 3 = 84`. The third "nearest semantic neighbor" contrast is **deferred** to a second stage,
after the pilot shows where confusion actually concentrates.

### Minimal-contrast construction rule (addition to the owner's spec §14)

> **A minimal-contrast pair must be written by modifying a shared scenario plan, not by
> independently generating two stories.**

The pair must preserve: `actor`, `setting`, `stakes`, `length`, `tone`, `number of entities`,
`narrative complexity`, `outcome polarity`. Only the intended World or drive signal changes.
Independently generated pairs make the contrast uncontrolled and are a generation failure.

---

## 3. Authoring / acceptance separation

Strict order. **The author never sees the independent judge's answer, at any point.**

1. Author model generates the structured **plan** (shared across a minimal pair).
2. Author model writes both **vignettes** from that one plan.
3. Author model performs its own leakage and consistency checks — **lint only**.
4. Independent judge receives **only the vignette** plus the canonical 28 labels.
5. Baselines receive the **identical** vignette.
6. Acceptance is determined from **independent outputs only**.

Author-side blind reclassification (spec §19) is recorded as metadata and **gates nothing**. Item
repair informed by judge output would be indirect judge-fitting.

---

## 4. Frozen fields — recorded per item

```
target_code           contrast_type          contrast_code
scenario_length_range  author_model           author_prompt_hash
judge_model            judge_prompt_hash      definition_set_hash
temperature            random_seed            generation_retry_limit
acceptance_threshold   primary_metric         baseline_models
exclusion_rules
```

**Rejection handling, frozen now:** rejected items are **counted as generation failures and
reported**; they are **NOT silently regenerated**. `generation_retry_limit = 2`, and retries are
permitted **only for API/transport errors**, never for quality. Silent regeneration until an item
passes would measure search effort plus model ability rather than authoring quality.

**Reported unconditionally:** `first_pass_recovery`, `post_revision_recovery`, `n_revisions`,
`rejection_reasons`.

**No judge-as-pre-release-gate in this pilot.** The frozen batch is generated and *everything* is
scored. Using the evaluator to select items and then reporting performance on the survivors is
circular. An acceptance gate is defined only afterward, and tested on a **fresh holdout**.

---

## 5. Endpoints

### Primary — pairwise minimal-contrast accuracy

For each minimal pair the judge chooses between **only the two intended Foundations**. This
directly tests whether the changed World or drive is recoverable. Chance = `0.50`.

### Secondary
28-way top-1 · 28-way top-3 recall · target probability · top-1 minus top-2 margin ·
**World accuracy** · **drive accuracy**

### Diagnostics
evidence-span sufficiency · confusion matrix · lexical-baseline accuracy · scenario rejection rate

### Staged judge output

```json
{"world":"Spiritual|Mental|Emotional|Physical","drive":"1|2|3|4|5|6|7",
 "foundation_code":"2b","top_3":["2b","2d","5b"],
 "evidence_spans":["quoted span 1","quoted span 2"],"confidence":0.00}
```

Scored separately because a judge may recover the drive while confusing the World, or the reverse,
and a single 28-way number hides that:

| Component | Chance |
|---|---|
| World | `0.2500` |
| Drive | `0.1429` |
| Full Foundation | `0.0357` |

---

## 6. Baselines

- character 3–5-gram classifier
- word TF-IDF classifier
- label-description cosine similarity
- majority / random

Lexical baselines see only permitted training material — **never paraphrases derived from the test
scenarios**.

```
success pattern     independent semantic judge  >  lexical baselines  >  chance
suspicious pattern  character n-grams  >=  independent judge      -> dataset is lexical/stylistic
```

---

## 7. Frozen hypotheses

| # | Hypothesis | Bar |
|---|---|---|
| `H1` | Spec-authored exceed original `T2` | `> 0.0429` *(practical benchmark only — see note)* |
| `H2` | Spec-authored exceed 28-way chance | `> 0.0357`, binomial `p < 0.01` |
| `H3` | **Pairwise minimal-contrast accuracy** | `> 0.50` |
| `H4` | Judge exceeds char n-gram **and** word TF-IDF | both, on identical items |
| `H5` | World and drive each recoverable | `> 0.2500` and `> 0.1429` respectively |
| `H6` | Human-authored exceed original generated | **DEFERRED — see §8** |

**`H1` caveat, per owner:** the item populations differ, so this is a **practical benchmark, not a
perfectly controlled causal comparison.** It will be reported with that sentence attached.

---

## 8. Human arm — DEFERRED, with the reason stated

**No human test-subject pool is available.** The only human author on hand is the owner, who
created the framework.

That is not a neutral substitution. An owner-authored arm reintroduces the **shared-authorship
confound** — the defect that defeated sixteen instruments — at the authoring step instead of the
scoring step. It would test *"can the framework's creator encode a Foundation recoverably,"* not
*"can a trained human do so."*

It is therefore **not** a valid test of `H6` as written, and running it would not license the
`Low/High` or `High/Low` cells of the owner's four-cell interpretation table.

**It is still worth running later as a bounded existence proof**, and only that:

- If the owner **cannot** write a recoverable scenario, that is strong evidence the task is hard
  independent of any model.
- If the owner **can**, it shows recoverability is possible in principle and localizes the failure
  to the generator.

Neither reading generalizes to trained non-author humans. That arm requires a real panel and stays
open in `HANDOFF_PACKAGE.md` §7.

**Consequence for this pilot:** the four-cell table cannot be completed. A `Low` generated result
will therefore be reported as *"generator failed OR task is hard — not separable without an
independent human arm"*, exactly per the owner's spec §26.

---

## 9. Disclosed deviations

1. **Human arm deferred** (§8) — no subject pool exists; owner-as-author is confounded.
2. **Nearest-semantic-neighbor contrast deferred** to stage 2, per owner instruction.
3. **Author self-rubric and self-classification recorded, never gating** — author-side filtering
   would let the generator select its own test set.

All three are conservative: each removes a way for the run to look better than it is.

---

## 10. Ceiling

A full pass licenses:

> *"Scenarios authored under the owner's specification, from shared minimal-contrast plans, carry
> Foundation signal recoverable by an independent judge above chance, above character- and
> word-level lexical baselines on identical items, and above `0.50` on forced two-way
> minimal-contrast decisions — with World and drive each independently recoverable."*

It licenses **nothing** about: TKS vs CAS definition quality, any **small model** (the judge is
`gemini-2.5-flash`), human authoring or human judging, or product capability. **It does not close
Gate 2**, whose wording requires a small model.

## Status

`LOCKED / COMMITTED BEFORE v2 GENERATION AND BEFORE v1 PRODUCED ANY NUMBER / NOTHING LICENSED`
