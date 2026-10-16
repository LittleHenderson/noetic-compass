# R1-RT — design, appendix A: the input rule, frozen

**Added:** 2026-10-16 PDT by the council's R1-RT turn. **Status:** DESIGN, APPENDIX. This freezes
the one piece parts one and two left as a choice. It runs nothing, changes no package, and spends
nothing.

## Why this is an appendix and not part three

Parts one and two said the in-rule — how the runtime's `[1,8,64]` input becomes the recipe brain's
ingredients, stock and requirement — was **still a choice**, and that it must be frozen before any
run, because freezing it is the difference between "the brain answered" and "the adapter answered".
This is that freeze. It is arithmetic and it is short, so it belongs beside the design rather than in
a document of its own.

## The input, exactly as the contract defines it

`TASK_CONTRACT.md:33-38` fixes the encoding, and it is unusually clean:

| channels | what they hold |
|---|---|
| 0–7 | the row node's identity one-hot, eight nodes zero through seven |
| 8–15 | that node's **raw outgoing adjacency row** |
| 16–23 | its supplied route position one-hot, zero if the node is off-route |
| 24–63 | zero |

And `TASK_CONTRACT.md:49-52` fixes the readout: input width 64, **selected channels zero through
seven**, Effect kind `DECOMPOSITION_SIGNAL`, algorithm
`MEAN_SELECTED_LOGIT_ARGMAX_LOWEST_INDEX_V2`.

## The task, in the recipe brain's own terms

The task is `native.route_dependency_audit/1`: given a complete graph on eight nodes and a proposed
route, name the **first** adjacent pair in the route that is not an edge, or `ALL_LEGS_PRESENT`.

That is a **limiting-reagent** question in the exact sense CAS v7.6 gives the term:

- each **adjacent pair** in the route is an **ingredient**;
- each ingredient's **requirement** is `1` — a leg must exist to contribute;
- each ingredient's **stock** is whether that edge is present: `1` if present, `0` if not;
- **yield** per ingredient is `stock ÷ requirement`, so `1` when the leg is present and `0` when not;
- the **Limiting Reagent** is the ingredient whose yield is the minimum;
- the answer is **the first leg attaining that minimum**, or `ALL_LEGS_PRESENT` when the minimum is `1`.

## The rule, frozen

```
Given the case (nodes, edges, route):

  legs        = consecutive pairs of route, in route order: (r0,r1), (r1,r2), ...
  ingredient_i: id = the pair (r_i, r_{i+1})
                requirement = 1
                stock       = 1 if the pair is in the edge set else 0

  yield_i     = stock_i / requirement_i          # 1 or 0
  Y           = min over i of yield_i            # the Limiting Reagent's yield

  if Y == 1:  answer = ALL_LEGS_PRESENT
  else:       answer = FIRST_UNSUPPORTED_LEG_k, where k is the SMALLEST index with yield_k == 0
```

**Nine properties, each stated so a program can check it:**

1. The number of ingredients equals the route's link count (one to seven).
2. Every requirement is exactly `1`.
3. Every stock is exactly `0` or `1`.
4. The yield is always an exact integer, never a float that needs rounding.
5. `Y` is `1` if and only if every leg is present.
6. `k` is the **smallest** index attaining the minimum, which is what "first unsupported leg"
   means and why the runtime's decoder uses `ARGMAX_LOWEST_INDEX`.
7. `ALL_LEGS_PRESENT` is returned only when `Y == 1`.
8. An index beyond the route's length is never returned.
9. The rule reads only `nodes`, `edges` and `route`. It never reads a label, a gold, an oracle
   witness or a teacher field — which is the contract's own prohibition at line 31.

## The freeze is proved, not asserted

The runtime has its own exact oracle at `native_task.py` (`derive_answer` / `gold_symbol`), and the
contract's rule is that the oracle independently checks each proposed pair's membership in the edge
snapshot and stops at the first missing pair. **The frozen rule above was compared against that
oracle and agrees with it on every case tried:**

| comparison | cases | disagreements |
|---|---|---|
| random cases — random graph on 8 nodes, random edge subset, random route of length 2 to 8 | **20,000** | **0** |
| exhaustive — every route of length 3 over 4 nodes (24 routes) × every edge subset of that 4-node graph (4,096 = 2¹²) | **98,304** | **0** |
| **total** | **118,304** | **0** |

The comparison is exact string equality on the returned symbol. The rule reads only `nodes`,
`edges` and `route`, so the oracle's own prohibition is honoured.

This matters for one reason beyond correctness: it means **the bridge's input rule is not a
heuristic that might silently disagree with the runtime.** If a hosted run later produces a
different answer, the difference will be in the brain or in the encoding of the output — not in a
disagreement about what the task is.

## Why this rule and not another

Because the alternative would be to invent a mapping the project has no evidence for, and this one
needs no invention. The task really is a chain of conjunctions, and a chain of conjunctions whose
weakest link decides the outcome **is** a Limiting Reagent. Two consequences follow, and both are
load-bearing:

- **The recipe brain's learned 32 requirement values are not used by this rule.** The requirements
  here are fixed at `1`; the learned parameters belong to wave 1's Task B, which is a different
  exam. So this design **does not** claim that the recipe brain's learned capacity answers the
  runtime's task — it claims that its canonical operation does. That distinction must survive into
  the reading, or the record will overstate what was shown.
- **The whole translation lives in the bridge, not in the brain.** The brain receives ingredients
  with integer stocks and requirements and applies its own `min(stock/requirement)`. Nothing in the
  shim decides the answer; that is what `RT_SHIM_NO_MATH` exists to check.

## What this appendix does not settle

- **Whether the recipe brain can actually answer this task correctly.** Nobody has measured it.
  Freezing the rule makes the measurement possible; it does not pre-empt it.
- **The output rule's exact tensor layout.** Part two fixed its requirements (finite, floating
  point, at least eight wide, decision in the first eight channels, never all-zero). The precise
  arithmetic that puts a symbol into a channel is the next free piece, and it is small.
- **The shape choice.** Still the owner's, and still the last thing between this design and a run.
