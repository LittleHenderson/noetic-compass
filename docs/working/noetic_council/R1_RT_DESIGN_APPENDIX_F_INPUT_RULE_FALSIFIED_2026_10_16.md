# R1-RT design, appendix F: the frozen input rule is falsified, and the ceiling it puts on the brain

**Date:** 2026-10-16
**Status:** appendix A's frozen input rule, combined with the brain's own RPM Gate, means the brain
**cannot answer the runtime's task at all** except on the one case where every leg is present. This
is a measurement, not a reading of the prose. The design's own appendix A said nobody had measured
whether the brain can answer this task; this is that measurement, and the answer is no.

## 1. What was assumed

Appendix A froze: each route leg is an ingredient, requirement exactly `1`, stock exactly `1` if the
leg is in the edge set and `0` if not, yield `stock / requirement`, and the answer is the first leg
attaining the minimum.

The brain would then compute that minimum and name the leg.

## 2. What the brain's own gate does with a zero

`RecipeBrain.readout` computes the best yield across recipes and then:

```
best = max(values[r] for r in firing)
if best == ZERO:
    return Readout(UNDETERMINED, "G2", None, values, None)
```

A stock of `0` gives a yield of `0` whatever the requirement is. So one missing leg drives the best
yield to zero, and the brain refuses with **G2** instead of naming the leg.

Measured with a live `RecipeBrain`, requirement `1`, all stocks `1` except one:

| input | label | gate | limiting cell |
|---|---|---|---|
| every leg present, all stock 1 | `'SOME_LABEL'` (the configured beta) | `None` | `0` |
| one leg missing, stock 0 at one cell | `'UNDETERMINED'` | **`'G2'`** | `None` |

## 3. Nothing rescues it

**The requirement is the only free value, and it does not help.** Sweeping it across the brain's own
allowed bounds `[0.05, 20]` with one leg missing:

| requirement | 0.05 | 0.25 | 1.0 | 2.0 | 20.0 |
|---|---|---|---|---|---|
| label | `UNDETERMINED` | `UNDETERMINED` | `UNDETERMINED` | `UNDETERMINED` | `UNDETERMINED` |
| gate | `G2` | `G2` | `G2` | `G2` | `G2` |

Zero divided by anything is still zero.

**A second allocated recipe makes it worse, not better.** With two allocated recipes and one leg
missing, the label is `UNDETERMINED` on gate **`G1`**, and both active sets are **empty**
(`[[], []]`). So the second recipe removes the recipe that could have fired rather than adding one.

## 4. The ceiling this puts on the brain

The runtime's own dataset is authored **balanced across its eight answers**:
`native_task.py:189` sets `target = len(cases[split]) % len(ANSWER_LABELS)`. So `ALL_LEGS_PRESENT`
is exactly one eighth of the cases.

Counted from the runtime's own generator, by split:

| split | cases | every leg present |
|---|---|---|
| train | 128 | 16 |
| qualification | 32 | 4 |
| retention | 64 | 8 |
| heldout | 64 | 8 |
| heldout_twins | 64 | 8 |
| **total** | **288** | **36** |

**The brain's ceiling on this task is 36 of 288 = 0.125.** It reaches even that only if its beta is
set to `ALL_LEGS_PRESENT`. On the other 252 cases its answer is `UNDETERMINED`, which the project's
own scoring — `rb/common.py`, `outcome()` — counts as **not wrong, not right**.

## 5. A second, smaller mismatch: how many answers can be named at all

Read from a live brain and a live task module, in separate processes:

| | value | source |
|---|---|---|
| the brain's recipe slots | **4** | `rb/common.py` `RECIPES`, and `len(RecipeBrain().beta)` |
| the brain's own label strings | `L0`, `L1`, `L2`, `L3` | `rb/common.py` `LABELS` |
| the runtime's answer labels | **8** | `native_task.py:23`, and the decoder contract |
| the decoder's channels | `0,1,2,3,4,5,6,7` | `native_task.task_decoder_contracts` |

One readout returns exactly one `beta[winner]`, and there are four beta slots. So **at most four
distinct answers can ever be named by one readout**, against eight the task can produce. This
mismatch is smaller than the gate problem and would be reachable by a wider brain, but it is a second
independent thing that has to be solved.

## 6. What this does NOT say

- **It is not a defect in the brain.** G2 is the brain's canonical refusal to answer when the yield
  is zero, and refusing is the correct behaviour for the case it was built for. The mismatch is
  between this task and this brain, not a fault in either.
- **It does not touch wave 1.** Wave 1's result stands, and this finding does not weaken it.
- **It does not mean the brain is useless for the runtime's task.** See the candidate below. It means
  the *frozen input rule* as written cannot work.

## 7. A candidate repair: its arithmetic is measured, its permission is not

The gate fires only because the missing leg's stock is `0`. Give the cells values that are never zero
and let the brain's own argmin find the leg:

- a reference cell at index `0`: stock `1` when every leg is present, `3` otherwise;
- leg cell `j+1`: stock `2` if that leg is present, `1` if not;
- padding cells: stock `3`;
- requirement `1` everywhere.

The minimum is then `1`, never `0`, so G2 does not fire, and the **first cell attaining the minimum**
names the answer:

| case | minimum | first cell at the minimum | reading |
|---|---|---|---|
| every leg present | 1 | 0 | `ALL_LEGS_PRESENT` |
| leg `j` missing | 1 | `j+1` | `FIRST_UNSUPPORTED_LEG_j` |

The bridge reads `readout.limiting_cell` and spells its name. It does not compute the answer.

**Its arithmetic is measured, not argued.** Run on a live `RecipeBrain` over every route length from
one leg to seven, and every position of a single missing leg:

| cases checked | cases gated | cases where the limiting cell named the answer |
|---|---|---|
| **35** | **0** | **35** |

Reproduce with `probe_candidate_input_rule.py <v3-package-root>`.

**What is NOT measured, and is the whole remaining question.** The reference cell has to know whether
*every* leg is present. That is a conjunction over the same facts the rule already reads, so it may be
legitimate — but it is closer to the answer than anything else in the bridge, and `RT_SHIM_NO_MATH`
exists to draw exactly that line. **Whether it crosses the line is a design question and is not
decided here.** The candidate also changes appendix A, which is frozen, so it would need its own
freeze and the owner's line before any run.

## 8. The candidate's arithmetic, proved against the runtime's own LIVE oracle

**Date:** 2026-10-16. **Status:** the arithmetic in section 7 now agrees with the runtime's own oracle
on every case tried, using the **live** recipe brain and the **live** `native_task` — not
transcriptions of them.

| | |
|---|---|
| cases compared | **323,851** |
| disagreements | **0** |
| cases the brain could not answer (gated) | **0** |
| sha256 of the candidate's answers | `c591c5685b84f96ae2ab05ceedc4720ccabc16efd68ab9d908832ecf9383dd8e` |
| sha256 of the oracle's answers | `c591c5685b84f96ae2ab05ceedc4720ccabc16efd68ab9d908832ecf9383dd8e` |

The two answer streams are **byte-identical**, not merely equal case by case. One file was written by
a process that has never seen torch and holds a live `RecipeBrain`; the other by a process holding the
live `native_task`. They cannot share an interpreter (appendix E), so the comparison crosses the
process boundary the design already has to cross.

Reproduce with `prove_candidate_vs_oracle.py <v3-package-root> <r6-source-root>`.

<!-- DIGESTS-VERIFIED-BY-THE-WRITER -->

### Why this is stronger than appendix A's own proof

Appendix A's 118,304-case comparison put a hand-written copy of the oracle against a hand-written copy
of the rule, in one file, with no brain and no runtime. It showed the two **rules** agree. It could not
show that the live brain obeys its own rule — and section 2 of this appendix is precisely the finding
that it does not. This run uses the live objects, so it can fail for the reason that matters.

There is a second reason appendix A's proof could not have been reused as it stood: its exhaustive
part uses cases on **four** nodes, and the live oracle **refuses** them. `native_task.validate_case`
requires `case["nodes"] == list(range(8))` exactly (`native_task.py:71-72`). So the old proof's
exhaustive half can never be handed to `derive_answer` at all.

### What was covered, and why it is enough

`native_task.derive_answer` reads one thing: whether each **route leg** is a member of the edge set.
Edges outside the route never affect the answer. The task's answer function therefore has exactly two
inputs — the route, and which of the route's legs are present — and the coverage targets both:

| part | cases | what it covers |
|---|---|---|
| exhaustive on structure | **122,304** | every route of 2, 3 and 4 links over eight nodes — 8,736 routes — crossed with **every** subset of that route's own legs |
| random | **200,000** | the full eight nodes, random edge subsets, routes of 2 to 8 links, fixed seed |
| adversarial | **1,547** | every route length: all legs present, each leg missing in turn, and all legs missing |

The exhaustive part leaves nothing about a short route untried. The long routes cannot be exhausted on
a laptop — full exhaustion is every route of 2 to 8 links crossed with every leg subset, roughly
2.6e7 cases — so they are covered by 200,000 random cases plus the adversarial set.

The comparison is not vacuous. Every one of the eight labels occurs in the answers:

| label | count |
|---|---|
| `ALL_LEGS_PRESENT` | 29,915 |
| `FIRST_UNSUPPORTED_LEG_0` | 183,367 |
| `FIRST_UNSUPPORTED_LEG_1` | 69,487 |
| `FIRST_UNSUPPORTED_LEG_2` | 28,271 |
| `FIRST_UNSUPPORTED_LEG_3` | 11,770 |
| `FIRST_UNSUPPORTED_LEG_4` | 828 |
| `FIRST_UNSUPPORTED_LEG_5` | 174 |
| `FIRST_UNSUPPORTED_LEG_6` | 39 |

### What this does NOT establish

1. **It does not decide whether the candidate is allowed.** The reference cell is part of the thing
   being proved, so this shows the arithmetic agrees with the oracle — not that the design's own
   `RT_SHIM_NO_MATH` line permits a reference cell. That is still the open question, and it is still a
   design question rather than a measurement.
2. **It does not cover the long routes exhaustively.** Stated above rather than glossed.
3. **It does not touch the eight-answer alphabet problem.** The brain still has four beta slots. The
   candidate gets round that by reading `limiting_cell` rather than the label, which is why the label
   is irrelevant here — but that is an argument, and the alphabet mismatch in section 5 stands
   unmeasured against as a separate thing to solve.
4. **It is not a runtime result.** No tensor was produced, no decoder ran, no store was written. What
   runs between the label and HELM's runtime is appendix B's rule, unchanged.

## 9. What is not known

1. Whether the candidate in section 7 survives the `RT_SHIM_NO_MATH` line. **This is the one that
   matters, and it is not a measurement.**
2. Whether the four-slot brain can carry the candidate's answers. It needs one bit plus a leg index,
   and only the limiting cell carries them, so probably yes — and it is untested.
3. Whether the gate's other conditions, G3 and G4, fire on the candidate's inputs. None fired in the
   35 cases tried, which is not the same as proving they cannot.
4. ~~Whether the candidate can be proved equivalent to the runtime's own oracle the way appendix A
   was proved, over the same 118,304 cases.~~ **ANSWERED by section 8: it was proved on 323,851
   cases with 0 disagreements, against the LIVE oracle rather than a transcription.** What remains
   open is not agreement but coverage: the long routes are random and adversarial rather than
   exhaustive, and full exhaustion is about 2.6e7 cases.
5. Whether any of this is worth doing, given what it would cost against wave 1's already-licensed
   result. **That is the owner's call, and this appendix does not make it.**
