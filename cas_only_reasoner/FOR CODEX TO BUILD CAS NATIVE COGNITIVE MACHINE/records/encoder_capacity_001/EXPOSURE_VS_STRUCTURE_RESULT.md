# EXPOSURE_VS_STRUCTURE — the machine is not memorising worlds, and the held-out panel's failure needs a different explanation

**Round 39. Three measurements that refine round 38's interpretation, and one honest failure.**
**$0.00. Pure standard library plus the project's pure modules. No torch, no GPU, no model, no
training, no new run.**

Script: `records/encoder_capacity_001/measure_exposure_vs_structure.py`.
Output: `exposure_vs_structure.txt`.

---

## 1. The course uses 24 focus worlds, and accuracy is NOT carried per world

```
worlds: 24
  worlds with 100% of their questions correct: 0
  worlds with   0% of their questions correct: 0
  worlds strictly between: 24
  best world 48.3333% over 20 questions, worst 15.0000% over 20 questions

  even split by world, mean correctness:
     half 0:  288 questions   35.3588%
     half 1:  276 questions   33.9372%
```

**Two facts, both new.**

**The exposed course draws on 24 distinct focus worlds, not the bank's 64, and each carries about 20
questions** (564 / 24 = 23.5). The bank supplies 64; the course uses 24 of them.

**And not one world is polarised.** No world has all its questions right, none has all of them wrong,
and **all 24 sit between 15.0000% and 48.3333%** — a band 33.3 points wide, centred on the overall
mean of 34.6631%. Splitting the worlds in half gives 35.3588% against 33.9372%, a 1.42-point
difference.

**That is direct evidence against per-world memorisation.** A machine that memorised answers world by
world would show polarisation — worlds it had learned near 100%, worlds it had not near 0%. **Instead
every world is middling, and they are all middling to about the same degree.**

## 2. This refines round 38 rather than confirming it

Round 38 read the development panel's 0 of 59 as "it answers from memorised layout rather than from
structure — a readout that memorises layout scores zero on a layout it has never seen."

**§1 shows the memorisation is not at the world level**, because per-world performance is uniform. So
the reading has to be narrower: whatever is memorised is memorised at the **slot and layout** level —
the shape of a pair, the arity of a slot — and it is shared across worlds rather than attached to
them. That is consistent with everything else in this record (the packet inert per slot, `W36` in six
runs, `edge_account` at 54.6353% balanced) **and it means "unseen world" is not by itself the reason
the panel fails.** The panel differs in **world size** (ten nodes against four) and in who authored
the declarations (`NEW_CALLER_AUTHORED_DEVELOPMENT_FACTS_NOT_WORLD_TRUTH`).

**Round 38's stronger wording is therefore narrowed here, and the claim that survives is the narrower
one.**

## 3. World size does not explain the failures *within* the exposed course

The exposed course itself varies — worlds of three nodes and worlds of four:

| focus world nodes | questions | mean recorded correctness |
|---|---|---|
| 3 | 115 | **39.4203%** |
| 4 | 449 | **33.4447%** |

**The machine does BETTER on the smaller worlds**, by 5.98 points. By kind:

| kind | 3 nodes | 4 nodes |
|---|---|---|
| `correspondence` | **100.0000%** (18 q) | 93.0952% (70 q) |
| `reach` | **82.1429%** (28 q) | 74.4726% (79 q) |
| `parts` | 26.6667% (5 q) | 29.5139% (48 q) |
| `role_set` | 0.0000% (7 q) | 12.6437% (29 q) |
| `context`, `definition`, `edge_account` | 0.0000% | 0.0000% |

Smaller worlds are easier, which is structurally sensible — fewer pairs, fewer permutations — and it
means **size is not the axis on which the machine fails inside the course.** The panel is a ten-node
extrapolation, three times the largest world seen and two and a half times the commonest, and nothing
here measures what happens out there.

## 4. Exposure is weakly associated, and the association is confounded

The course presents 1,152 times over 564 questions, so questions differ in exposure:

```
 presentations  questions   mean correctness
             1        384          31.4236%
             2         36          24.5370%
             3         78          35.2564%
             4          8          12.5000%
             5         17          86.2745%
             6         16          18.7500%
             7          2         100.0000%
             8         12          68.0556%
            11          6          83.3333%
            14          4          91.6667%
            17          1         100.0000%

Spearman correlation, exposure vs correctness (all 564): +0.1451
```

**+0.1451 is a real but weak association, and it cannot be read as memorisation.** Exposure is
**confounded with kind** — the high-exposure cells are 1 to 17 questions each and their rates track
which kinds they contain, not how often they were shown. `correspondence` already scores 94.5076% and
`reach` 76.4798% on their own. **A within-kind correlation is the measurement that would settle it,
and it is not computed here.** Recorded as **OPEN**.

## 5. A measurement that failed, recorded as a failure

Section 4 of the script was to split the 64 worlds into two halves and show that the constraint
layer's gain is the same on both — a direct test of round 37's claim that the layer is carried by the
**packet** and not by which worlds were seen more often.

**It produced no observations.**

```
  half  records    obs  unconstrained  constrained      gain  missing  undecided
     0      269      0             --           --        --        0          0   NO OBSERVATIONS
     1      295      0             --           --        --        0          0   NO OBSERVATIONS
```

`records` counts correctly (269 and 295), but `obs` is zero **and so are the `missing` and
`undecided` counters**, which means the inner loop over the six receipts never incremented anything —
not even its own failure counters. **The cause is not identified.** The loop is over a list defined
once at the top of `main()`, the same list that populated `row_for` and `scores_for` for §4's earlier
sections, both of which produced data.

**This is a defect in the measuring script, not a result, and it is recorded rather than removed.** The
earlier version of the same section raised `ZeroDivisionError` for the same reason; the guard added
there turned a crash into a visible zero, which is an improvement but not a diagnosis. **Round 37's
world-invariance claim therefore remains asserted and untested**, and §5 does not support it.

## 6. What this round is worth

- **A new fact about the course**: 24 focus worlds, about 20 questions each, none polarised.
- **A narrowing of round 38**: the memorisation is at the slot/layout level, not the world level, so
  "unseen world" is not by itself why the panel fails. The stronger round-38 wording is withdrawn.
- **A negative that closes an easy explanation**: world size does not explain the in-course failures —
  smaller worlds score *better*.
- **An open question with the missing measurement named**: exposure within kind.
- **One failed measurement, recorded as failed.**

## 7. Claim status

- **REAL:** §1, §3 and §4's tables, from the frozen course and the recorded six-run score table.
  Artifact: `exposure_vs_structure.txt`.
- **WITHDRAWN:** round 38's "it answers from memorised layout" as stated. §1 shows per-world accuracy
  is uniform across all 24 worlds, so the memorisation is not world-attached. The narrower claim — that
  what is memorised is slot- and layout-shaped — survives.
- **OPEN:** the within-kind exposure correlation.
- **OPEN, and a defect:** §5. The world-invariance measurement produced no observations for an
  unidentified reason. **It is not evidence for or against round 37's claim.**
- **NOT LICENSED:** any inference about the ten-node development panel from in-course data. The panel
  is a 2.5× extrapolation in world size and its packets are absent, so nothing here bears on it.
