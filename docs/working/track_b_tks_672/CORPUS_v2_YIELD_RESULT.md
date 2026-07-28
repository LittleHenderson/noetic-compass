# `CORPUS_TKS_672_v2` — `FAIL_AUTHORING_YIELD`

**Lock:** `2bee2612` · **Cohort:** `v2`, single process, no backfill
**Budget verdict:** **`FAIL_AUTHORING_YIELD`** — computed by the runner, not by judgement.

---

## Yield

```
candidates generated     1120     (224 families x 5)
selected siblings         653
COMPLETE families         211 / 224      v1 was 126 / 224
world-leak rate          0.142 of candidates
```

**The oversample worked.** v1 lost an entire family whenever one sibling leaked; v2 takes the next
passing candidate. Complete families went `126 → 211`, a jump from `56%` to `94%`.

**The self-check instruction did not.** `14.2%` of candidates still contain a forbidden World word
despite an explicit eight-form list and a mandatory re-read. A stated rule is still not a
mechanism; the regex does the work.

## Why it still fails

Eight Foundations finished below the frozen 8-family bar:

```
5d = 5    2a = 6    7a = 6    7c = 6
1d = 7    6a = 7    6b = 7    7d = 7
```

Under the frozen budget this is a **failure**, and extending requires a new successor lock.

---

## The failure is not random — the World axis is lexically asymmetric

Leak rate by World:

```
b Mental      0.046      <- easy to write around
c Emotional   0.150
a Spiritual   0.182
d Physical    0.189      <- 4x harder than Mental
```

Leak rate by drive:

```
2 wisdom      0.069  (lowest)
7 lust/sex/reproduction   0.212  (highest)
```

Worst individual cells: `7c` `0.375` · `5d` `0.350` · `6a` `0.300` · `7a` `0.300` · `1d` `0.275`.
**Zero leaks:** `2b`, `7b` — both Mental.

**This is a property of English, not a generator defect.** "Mental" has abundant ordinary
substitutes — thinking, reasoning, weighing, analysing. "Physical" and "spiritual" are
load-bearing: writing bodily action or transcendent longing without those words is genuinely
harder, and the author reaches for them under pressure.

It also **explains two earlier findings retrospectively**: why June found Register/World to be the
surface-loud axis, and why `56%` of the 84-item corpus leaked. The same asymmetry was operating
each time.

**This is a finding about the framework's expressibility in natural language**, not an authoring
hiccup — and it lands squarely on the Worlds the canon most needs distinguishable.

---

## Options, with their costs — owner's decision

| | Option | Result | Cost |
|---|---|---|---|
| **A** | **Balance down to the worst cell** | `28 × 5 × 3 = 420` items, perfectly balanced, **above the `336` minimum** | discards `233` selected siblings; `5` families/Foundation means some 4-fold splits get `1` family per class — thin for 28-way |
| **B** | **New `v3` successor lock**, more plans for **all** Foundations | could reach `8`+ everywhere | more spend; must regenerate **all 28** to preserve one cohort, not just the starved 8 |
| **C** | **Approved substitute vocabulary** for Physical/Spiritual in the author prompt | attacks the actual cause | changes the authoring instrument — needs its own lock, and the substitutes could themselves become a shortcut |

**Not recommended:** topping up only the eight starved Foundations. That is the cohort confound
this v2 run existed to avoid.

**My read:** Option A is defensible today at `420` balanced items and needs no new spend. Option C
is the only one that addresses *why* this happened, and would make any future corpus cheaper — but
substitutes must be checked for becoming a new leak channel, since a fixed synonym list is exactly
the kind of thing a character n-gram model finds.

---

## Status

```
v1   NOT_FROZEN / NOT_SCORED / AUTHORING-YIELD EVIDENCE
v2   FAIL_AUTHORING_YIELD / NOT FROZEN / NOT SCORED
```

No surface gate has run. No judge has run. No readout is permitted. Gate 2 remains **OPEN at
`0.38`**.
