# `CORPUS_TKS_672_v1` — INCOMPLETE, NOT FROZEN, NOT SCORED

**Generator lock:** `ee5dcefd` · **Date:** 2026-07-27
**Disposition:** `REPAIR_GENERATOR_UNDER_NEW_VERSION` — per the frozen decision tree.

**No surface gate has been run. No judge has been run. No readout will run against this.**

---

## Authoring yield — reported before anything else, per protocol

```
target                          672
generated siblings              630
accepted                        513
rejected                        117
first-pass acceptance rate      0.8143
mean retries                    0.014
rejections by cause             direct_world_label 116, terminology_leak 1
World/Register leak rejection   0.1841
```

## The gate worked — that part is a success

**`116` items were rejected at admission for containing a direct World label.** In the 84-item
run, `56%` of scenarios carried that leak and **nobody caught it until a post-hoc audit of a
passing result**. Here it was caught at generation time and those items never entered a corpus.

Leak pressure is uneven by World, which is itself informative:

```
d Physical   42        a Spiritual  32
b Mental     25        c Emotional  17
```

## Why the corpus is nevertheless unusable

Raw count is not the problem. **Group structure is.**

```
complete 3-sibling plan families      126 / 224
intact-group corpus                   378 items   (clears the 336 minimum on count)

complete families per Foundation      min 1   max 7   mean 4.5
worst:  6a=1   1d=2   3d=2   5d=2   7c=2   6b=3
```

A **balanced** subset is limited by the worst Foundation: `28 × 1 × 3 = 84 items` — exactly the
size of the lane that was just closed. The count target is met while the design is not.

**The fold design requires 8 plan families per Foundation** so each of four folds receives two
independent groups from every class. With `6a` at one complete family, that Foundation cannot
appear in both training and test with intact sibling groups. Supervised 28-way remains impossible,
which was the entire reason for building `672`.

## Root causes

1. **The prohibition is stated but not enforced during generation.** The author was told the four
   World words were absolutely forbidden and used them anyway in `18.41%` of siblings. A stated
   rule is not a mechanism.
2. **No oversampling.** Each plan family was asked for exactly `3` siblings, so a single rejection
   destroyed the family's group integrity. `98` of `224` families were left incomplete.

## Repair — `v2`, disclosed as a version bump, not a retry

Per the frozen decision tree (*"repair the generator under a new version; do not score the
corpus"*):

| Change | Rationale |
|---|---|
| Request **5** siblings per plan, keep the **first 3 that pass the mechanical prohibition** | Oversampling protects group integrity. The surplus is discarded by a **mechanical rule**, never by a judge. |
| Author performs an explicit **self-check pass** against the prohibited list before returning | Converts a stated rule into a step. |
| **Backfill only Foundations below 8 complete families**, with **new independent plan families** | Not a re-roll of rejected items — those stay rejected and recorded. |

**Not changed:** the `0.60` June threshold, the gate code, the judge, the canon, the prohibited
list, the item schema, the retry policy, the no-judge-repair rule. **No bar moves.**

## Discipline notes

- `v1` records are **retained in full** — every rejected item keeps its text and reason. The
  surviving corpus is never reported alone.
- Rejected items are **not repaired and resubmitted**. `v2` authors *new* plan families.
- This is **not** retry-until-the-evaluator-approves: no evaluator has run, and the discard rule
  is a regex, not a model.

## Status

`v1 INCOMPLETE / NOT FROZEN / NOT SCORED / NO READOUT PERMITTED`
Gate 2 remains **OPEN at `0.38`**.
