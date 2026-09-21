# Helm — why the curve is flat, and how to make it climb

**Written 2026-09-20 by the audit session.** Companion to
`AUDIT_REPORT_20260920_INDEPENDENT.md`. **Nothing here is authorised. It is a proposal.**
Item F1 changes the shape of the brain, so under `BRAIN_LINEAGE.md`'s own versioning scheme it
is a **2.0**, not a 1.1.

---

## The headline

**Helm's eight reasoning rounds are one round, repeated eight times with the same input.**

The loop never reads its own state. Every round recomputes its message from the frozen input
features, so the thing fed to the reasoning block is **bitwise identical on all eight rounds**.
I proved this two ways, with the real trained weights from `final.pt`.

That means Helm can see **one hop** — a node's parents and its children — and nothing beyond.
Not two hops. Not at round 8, not at round 800.

This single fact explains every result in the audit: the flat curve, the score landing exactly
on the zero-learning floor, `analogy` at 0.00, `correspondence` at 0.09, and the collapse on the
ten-node panel. **It also means more neurons, more passes and more compute buy you nothing
today.** Fix the loop first. After that, every one of those levers starts paying.

---

## 1. The defect, exactly

`research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/pointer_learner.py`, `_rounds`,
lines 1022–1047:

```python
hidden = _rms_unit(torch, model.node_encode(raw))          # 1014  the state is born
for round_index in range(CORE_ROUNDS):                     # 1022  eight rounds
    for position, (start, stop) in enumerate(offsets):
        block = hidden[start:stop, :]                      # 1027  READ ... and never used
        raw   = blocks[position][2]                        # 1028  the FROZEN input rows
        adjacency = blocks[position][3]
        inputs.append(  _rms_unit(torch, raw))                              # 1031
        parents.append( _rms_unit(torch, adjacency.matmul(raw)))            # 1032
        children.append(_rms_unit(torch, adjacency.t().matmul(raw)))        # 1033
    ...
    update = model.core_block(hidden_input)                # 1046
    hidden = _rms_unit(torch, hidden + cap*tanh(rate)*update)   # 1047  the ONLY write
```

Line 1027 is the only line in the loop body that reads `hidden`, and its result `block` is
**dead** — assigned, never used. The three aggregates on lines 1031–1033 are built from `raw`,
the static feature rows. So `update` is a constant across the loop, and the recurrence is

```
h_{k+1} = rms(h_k + c·u)        with the SAME u, eight times
```

instead of the documented

```
h_{k+1} = rms(h_k + c·f([norm(h_k), norm(A·h_k), norm(Aᵀ·h_k)]))
```

**The function's own docstring says `norm(h)`. The code says `norm(raw)`.** The code
contradicts its documentation, which is what marks this as a defect and not a design choice.

### Proof 1 — static

An AST walk of `_rounds` reports exactly one name assigned and never read: **`block`**.

### Proof 2 — numerical, with the real trained weights

Loaded `final.pt` (seed 20260917) into the real container on CPU, ran `_rounds` with an
`observe` hook on a 4-node chain:

```
rounds observed: 8
ALL 8 round inputs bitwise identical: True
  round 1..7 vs round 0: max|diff| = 0.000e+00   (every one)
```

### Proof 3 — the consequence, measured

Two six-node graphs. Node 0's one-hop neighbourhood is **identical** in both — same parent,
same child, same feature rows. One edge is moved **two hops away** (`5→3` becomes `5→4`).

```
row of node 1 identical: True          (node 0's parent, unchanged)
row of node 2 identical: True          (node 0's child,  unchanged)
row of node 4 CHANGED  : True          (the graph really is different)

AS SHIPPED, after all 8 rounds : node 0 max|diff| = 0.000e+00   identical: True
WITH AN ITERATING LOOP         : node 0 max|diff| = 1.775e-03   identical: False
```

**As shipped, a change two hops away is invisible. With the loop iterating, it arrives.**

---

## 2. Every measured result falls out of this

| kind | train | held | what the architecture can do |
|---|---|---|---|
| `context` | 1.00 | 1.00 | read one declaration ✅ saturated |
| `definition` | 1.00 | 1.00 | read one declaration ✅ saturated |
| `parts` | 1.00 | 1.00 | **one hop** — children of the named whole ✅ saturated |
| `edge_account` | 1.00 | 1.00 | **one hop** — copy the adjacency ✅ saturated |
| `reach` | 0.94 | 0.88–0.96 | DIRECT is one hop ✅; **VIA needs two** ❌ |
| `analogy` | **0.42** | **0.00** | needs cross-world structure ❌ memorises only |
| `correspondence` | **0.09** | **0.00** | needs a bijection ❌ cannot express it |
| `role_set` | 0.13 / 1.00 / 0.77 | — | unstable across seeds ❌ optimisation, not capacity |

Read the first four rows: **100% on training and 100% on held-out.** There is no gap to close
and no headroom to buy. That is what a flat curve looks like from the inside.

Now the ten-node development panel — the only task on the run with real headroom:

| | p00 | p01 | p02 | p04 | p06 | p08 | p10 | at p10, by kind |
|---|---|---|---|---|---|---|---|---|
| seed 17 | 0/59 | 4 | 4 | 4 | 3 | 4 | **7/59** | `parts` 1/6, `reach` 6/53 |
| seed 18 | 0/59 | 6 | 5 | 4 | 5 | 7 | **9/59** | `parts` 1/6, `reach` 8/53 |
| seed 19 | 0/59 | 4 | 5 | 5 | 6 | 5 | **6/59** | `parts` 1/6, `reach` 5/53 |

Ten-node worlds need long containment chains. One hop is not enough, and the panel shows it:
**12%, 15%, 10%.** This is the honest picture of what Helm can do when the answer is more than
one link away.

And the zero-learning floor from the audit now has an explanation rather than a coincidence:
**the one-hop adjacency rule IS the architecture's ceiling.** Helm converged to the trivial
baseline because the trivial baseline is exactly what this network can compute.

### The optimiser is also telling you it is finished

Mean loss and mean squared gradient, per pass:

| pass | seed 20260918 loss | grad² | seed 20260917 loss | grad² |
|---|---|---|---|---|
| 1 | 0.4398 | 46.44 | 0.5026 | 76.20 |
| 4 | 0.2404 | 1.97 | 0.2515 | 1.42 |
| 7 | 0.1936 | 0.609 | 0.2263 | 0.622 |
| 8 | 0.1750 | 0.341 | **0.2500** | **19.16** |
| 9 | 0.1686 | 0.307 | **0.2992** | **28.82** |
| 10 | 0.1598 | 0.261 | 0.2511 | 8.82 |

Seed 18: gradient has gone to 0.26 and stayed. **Converged. More passes cannot help.**
Seed 17: the gradient **blows up 30× at pass 8** and the loss goes back up. That is the seed
whose `role_set` collapsed to 0.13 while seed 18 reached 1.00. The learning rate is a constant
`0.003` with no warm-up, no decay and no gradient clipping. **That variance is an optimiser
problem, not a brain-size problem.**

---

## 3. Where the parameters actually are

157,919 numbers in 46 groups. Sorted by what they are *for*:

| part | numbers | share | what it is |
|---|---|---|---|
| `declaration_table` (1024×64) | 65,536 | **41.5%** | a **hash lookup table**. Memory, not reasoning. |
| `world_projection` (64×196) | 12,544 | 7.9% | squashes a whole world into one 64-vector |
| six per-kind heads | ~52,600 | 33.3% | each is `Linear(→64) → act → norm → Linear(64→2)` |
| **`left`+`merge`+`right`** | **16,384** | **10.4%** | **the entire reasoning core** |
| `node_encode` (64×18) | 1,152 | 0.7% | the node reader |
| `attention_key` (1×64) | 64 | 0.04% | **all of the attention** |
| everything else | ~3,600 | 2.3% | |

Three things to see here:

1. **The reasoning core is 10% of the brain.** Forty-one per cent is a lookup table. That is the
   ratio of a memoriser, and it matches `analogy`: 0.42 on training, 0.00 held — it looked the
   answer up and had nothing to generalise with.
2. **Attention is 64 numbers.** One scalar score per node, one softmax, one pooled vector per
   world. There is no multi-head attention, no pairwise attention, no way for two nodes to
   compare themselves to each other.
3. **Every head ends in `Linear(64 → 2)`.** Every candidate is scored **independently**, two
   logits at a time. Nothing anywhere enforces a joint answer.

That last point is why `correspondence` sits at 0.09 **on its own training data**. A bijection
is a joint constraint — each source node matched to exactly one target node, and no target used
twice. Independent per-pair binary scores **cannot represent that**, at any width. It is not
short of neurons. It is the wrong output shape. `records/typed_pointer_001` already books this
under the class `inexpressible`, and that classification is correct.

A related one, smaller but worth fixing: `_reach_options` builds its `ABSENT`/`DIRECT` logits
from `(query vector, whole-world vector, 4 degree scalars)`. **It never sees the candidate
pair.** The per-node pointer options do, but the two mode options do not. That is a plain
information starvation on the kind that carries 6 of the 18 gate questions.

---

## 4. The plan — in order, because each step unlocks the next

Doing these out of order wastes money. F1 before everything.

### 🔧 F1 — make the loop loop. **Do this first. Nothing else matters until it is done.**

Aggregate the **state**, not the frozen input row:

```python
hidden = _rms_unit(torch, model.node_encode(raw))
for round_index in range(CORE_ROUNDS):
    for position, (start, stop) in enumerate(offsets):
        state = hidden[start:stop, :]                 # <-- USE IT
        adjacency = blocks[position][3]
        inputs.append(  _rms_unit(torch, state))
        parents.append( _rms_unit(torch, adjacency.matmul(state)))
        children.append(_rms_unit(torch, adjacency.t().matmul(state)))
```

**Cost:** `node_encode` changes from `Linear(64, 18)` to `Linear(64, 64)`. That is
1,152 → 4,096 numbers, **+2,944 in total, +1.9% of the brain.** Nothing else moves.

**What it buys:** receptive field goes from 1 hop to `CORE_ROUNDS` = 8 hops. Transitive
containment, `reach`-with-`VIA`, and ten-node chains become *representable* for the first time.

**How you will know it worked, before spending on a full run:** it is a CPU test, $0.
Re-run Proof 3 above — node 0's vector must **change** when an edge moves two hops away. And
re-run the `observe` hook — the eight round inputs must stop being identical. Both are in this
document and both take seconds. **If those two checks do not flip, do not launch anything.**

**A warning:** iterating the state makes the loop a real recurrent network, which can now
diverge. Keep `PER_ROUND_UPDATE_CAP` and the `rms` after each round — they are already there
and they are what will hold it. Add gradient clipping (F4) in the same change.

### 🔧 F2 — give the heads a shape that can hold the answer

Two separate repairs, both small:

- **`correspondence` — replace independent pair scores with a matching layer.** Score all
  source×target pairs into a matrix, then run a few Sinkhorn normalisation steps (alternate
  normalising rows and columns) before the loss. That makes "one-to-one" a property of the
  output, not a hope. ~4k new parameters. This is the only change that can move 0.09.
- **`reach` — let the mode head see the pair.** Feed `_reach_options` the `whole` and `part`
  node states, the same states `_node_options` already uses. It is a concatenation change, a few
  thousand parameters. Cheap, and it feeds the kind that carries a third of the gate.

Also consider replacing the single scalar `attention_key` with 4 heads of width 16 (same total
width, 4×64 = 256 numbers instead of 64). Cheap, and it lets the world vector attend to more
than one thing.

### 🔧 F3 — build a ruler that a curve can be drawn on. **Do this before scaling anything.**

**You cannot see a continuous curve on 18 yes/no questions about 4-node worlds.** Eighteen
binary items give you nineteen possible scores, eleven of which a trivial rule already reaches.
That instrument cannot show a smooth climb even if the brain is climbing.

What a curve needs:

1. **A difficulty ladder, not one difficulty.** Worlds at 4, 6, 10, 16, 25, 40 nodes, and
   questions at hop-distance 1, 2, 3, 4, 5+. Then "how far can it reach" becomes a number that
   moves continuously instead of a pass/fail. The ten-node development panel is already the
   first rung — keep it and extend it.
2. **A continuous score alongside the exact-match score.** Per-slot log-likelihood, or edge-set
   F1, or graph edit distance. Exact match is a step function; it hides every partial gain.
   Report both, always.
3. **Many more held-out questions.** 18 is a gate, not a measuring instrument. For a curve you
   want hundreds, stratified by hop-distance and world size, and a *separate* frozen gate set
   kept for claims. Do not enlarge the frozen 18 — add a second, larger, curve-measuring set
   beside it, and never use it for the label.
4. **Keep the mechanism-free baseline on every chart.** Plot the one-hop rule's score as a line
   on the same axes, at every difficulty. A curve that runs above that line is a result. A curve
   that tracks it is not. This is the single most important habit from the audit.

### 🔧 F4 — fix the optimiser before you buy more compute

- **Warm-up then cosine decay** instead of a constant `0.003`. Seed 17's pass-8 blow-up is the
  symptom.
- **Gradient clipping** at a fixed global norm. `grad²` went 0.62 → 28.8 in two passes.
- **More updates.** 1,470 total weight updates is very small — 147 per pass, 10 passes, batch
  ≈ 8. Once F1 gives the model something left to learn, this number should go up by one or two
  orders, and that alone is a large, cheap win.
- **Report the loss on the held-back set every pass**, not only training loss. Trap 4 in
  `AUDIT_PACK.md` already says training loss is not learning; the fix is to measure the right
  loss continuously.

### 🔧 F5 — *now* scale. This is where "more neurons, more compute" starts paying.

Only once F1–F4 are in and the CPU checks flip. Then the levers in the order I would pull them:

1. **`CORE_ROUNDS`**: 8 → 12 → 16. With F1 this is literally "how many hops can it think".
   Cheapest capability per parameter in the whole system — **it costs zero new parameters**,
   because the round is shared. Scan it first.
2. **`d_model`**: 64 → 128 → 256. Quadratic in the core (`left`/`merge`/`right` are 64×64,
   64×128, 64×64), so 128 turns 16k into 65k and the brain into roughly 400k. Do this *after*
   the rounds scan, so you know how many hops you need before you pay for width.
3. **Data.** 19 taught worlds is a very small world. Generating more worlds is cheap and is
   almost certainly the largest single win available after F1 — `analogy` at 0.00 held is what
   too-few-examples looks like once the architecture can generalise at all.
4. **Shrink the lookup table.** 41.5% of the brain in `declaration_table` is a memoriser's
   budget. Once the core can reason, try 512×64 and spend the freed 32k on the core. Measure
   both ways.

---

## 5. What "continuous and exponential" will actually look like

Be ready for this, so it is not a disappointment:

- **Against world size / hop-distance, expect a smooth, falling curve** — accuracy high at 1
  hop, dropping as the chain lengthens, with the drop-off point moving right as `CORE_ROUNDS`
  goes up. That curve is your real capability measure, and it *is* continuous.
- **Against parameters and compute, expect a straight line on a log-log chart** — the usual
  shape. Steady, not explosive. You get a power law, and you get it only when the task has
  headroom, which is why F3 comes before F5.
- **What you will not get is a rising exponential on the frozen 18.** It is already at 12 of 18,
  6 of which are `analogy` and `reach`-VIA questions the architecture cannot currently reach.
  The most that set can ever show is 18. Treat it as a gate that says pass or fail, and draw
  your curves elsewhere.

The honest target after F1+F2+F3: **`analogy` off 0.00, `correspondence` off 0.09, and the
ten-node panel off 10–15%.** Any one of those moving is worth more than another point on the 18,
because all three are things a zero-learning rule cannot do.

---

## 6. Order of operations, and what each costs

| step | where it runs | cost | what proves it |
|---|---|---|---|
| F1 make the loop loop | local CPU | **$0** | the two checks in section 1 must flip |
| F1 smoke | local RTX 4070 | **$0** | worker runs end to end, 1 pass |
| F2 heads | local CPU | **$0** | `correspondence` moves off 0.09 **on training data** |
| F3 new ladder + continuous score | local CPU | **$0** | the trivial-rule line is on every chart |
| F4 optimiser | local CPU | **$0** | seed-to-seed variance in `role_set` collapses |
| F1–F4 together, 3 seeds | AWS GPU | ~$45 | the frozen grader, unchanged, on the unchanged 18 |
| F5 rounds scan 8/12/16 | AWS GPU | ~$45–90 | the hop-distance curve moves right |
| F5 width 64→128 | AWS GPU | ~$90 | log-log line |

**Everything up to the first AWS line is free and can be done today.** The two CPU checks in
section 1 are the gate: if they do not flip, the change did not land, and no money should move.

Under the project's GPU-first rule the claim-bearing runs go to AWS, and the local 4070 is smoke
only. Under the research-governance rule, none of this is a decision I get to make.

---

## 7. What I would not do

- **Do not add parameters first.** Four of the eight kinds are at 100/100 and one seed's
  gradient is already at 0.26. There is nothing for extra neurons to do until F1 lands.
- **Do not train longer first.** `MORE_PRACTICE_population` failed for a reason, and it is this
  one. Ten passes is already nine more than the architecture needs.
- **Do not change the frozen 18 or the pass mark.** Rule 4 in `BRAIN_LINEAGE.md`. Build the new
  measuring set **beside** it.
- **Do not re-label Helm 1.0.** The run happened, the numbers are real, and the record stays.
  F1 makes a different-shaped brain, so it is Helm **2.0** and gets its own row.

---

## For the owner — decisions only you can make

1. **Confirm the loop defect is a defect and not an intention.** The code and its own docstring
   disagree. I read it as a bug. If it was deliberate, say so and I will record it as a design
   limit instead, and the whole plan below it changes.

2. **Authorise F1 as a $0 local change** — make the loop read its own state, then run the two
   CPU checks in section 1. No GPU, no money, and it is reversible. This is the one thing I
   would ask for today.

3. **Decide whether Helm 2.0 opens a new lineage row now or after F1 is measured.** The
   versioning scheme says a shape change is a 2.0. I have not touched `BRAIN_LINEAGE.md`.

4. **Decide the new measuring set before any GPU spend** (F3). If the ladder and the continuous
   score are not built first, a scaling run produces numbers nobody can draw a curve through,
   and we will have paid for another flat line.

5. **Rule on the parameter budget.** 41.5% of Helm is a lookup table and 10% is the reasoning
   core. Shrinking the table is a real change with a real risk to `definition`/`context`, which
   are currently perfect. Your call whether to try it.

6. **Still open from the audit, unchanged:** the zero-learning floor is missing from
   `BRAIN_LINEAGE.md`, the grader does not check the scoring files against their own recorded
   digests, and "new wiring" is not accurate. Those are separate from this plan.
