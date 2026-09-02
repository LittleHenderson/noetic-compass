# CMB-P1 — RESULT: `PHASE_MEMORY_UNSAFE` (no single repair survives)

**Run:** `cmb-p1-1788330740` · instance `i-0b5acbf6e8d2efa9d` · Tesla T4, `us-west-2`
**Cost:** **$0.1135** (12.9 min; a first attempt cost **$0.14** and crashed — see §8)
**Hash:** `98c9233289c9ccd47e5ed8baad46f878` · peak VRAM `95,621,120` · harness wall `613.39 s`
**Held-out:** 20 worlds per K, per substep budget. Every arm paired on identical worlds.
**Status emitted by the program** from frozen thresholds, not by prose.

---

## 1. The headline

**No single repair survives. `PHASE_MEMORY_UNSAFE` stands.** The reason emitted is *"a repair
kept accuracy but not attribution"* — which is precisely the CMB-P0 failure, unrepaired.

**But the registered prediction held, and the interesting result is the one that carries no
verdict:** the **exploratory** `P8+P9` combination lands close to the oracle on *both* axes.

## 2. Held-out top-1 / merge fraction

`P0` = 0.503 / 0.343 / 0.251 at K=2/3/4. `P1` is an **oracle ceiling, never a method**.

### At the CONVERGED budget (200 substeps) — the one that decides

| arm | K=2 | K=3 | K=4 |
|---|---|---|---|
| `P0_SCALAR` | 0.503 | 0.343 | 0.251 |
| `P1_ORACLE` *(ceiling)* | 0.780 | 0.677 | 0.560 |
| `P2_INFERRED_TAG` | 0.459 / **0.045** | 0.352 / 0.051 | 0.263 / 0.049 |
| `B_STRUCT_GATE_REACH` *(phase-free)* | 0.532 | 0.361 | 0.263 |
| **`P4_PHASE`** | **0.503 / 1.000** | **0.343 / 1.000** | **0.251 / 1.000** |
| `P7_SIGNED_COUPLING` | 0.490 / 0.125 | 0.320 / 0.118 | 0.168 / 0.095 |
| `P8_FREQUENCY` | 0.584 / 0.147 | 0.445 / 0.115 | 0.322 / 0.116 |
| `P9_TRAJECTORY` | 0.548 / 0.512 | 0.409 / 0.468 | 0.305 / 0.437 |
| **`P8P9` *(exploratory, NO verdict)*** | **0.704 / 0.002** | **0.571 / 0.003** | **0.432 / 0.001** |

## 3. The sharpest single number: at convergence, phase is exactly nothing

```
P4 @200 :  0.503 / 0.343 / 0.251     merge fraction 1.000 / 1.000 / 1.000
P0      :  0.503 / 0.343 / 0.251
```

**Identical to three decimals at every K.** At its fixed point the oscillator merges *every*
chain pair, `cos(Δθ) = 1` everywhere, and the phase readout degenerates into the scalar
engine. The CMB-P0 numbers were a transient; this is the destination. This is the held-out
confirmation of amendment A3.1, and it settles the question the two-budget rule was added to
ask.

## 4. Why each repair failed — the criteria are explicit

| repair | @10 substeps | @200 substeps |
|---|---|---|
| `P7_SIGNED_COUPLING` | fails 1, 3, 4, 7, 9 | fails 1, 2, 3, 4, 7, 9 |
| `P8_FREQUENCY` | **fails 2 only** | fails 1, 2, 7, 9 |
| `P9_TRAJECTORY` | fails 1, 7, 9 | fails 2, 9 |

- **`P7` genuinely fixes the synchronisation** — global order parameter **0.218 / 0.264**
  versus `P4`'s **1.000** — and still loses. It buys attribution by destroying retrieval:
  0.490 vs `P0`'s 0.503 at K=2, and 0.168 vs 0.251 at K=4. The dev finding that the trade is
  monotone with no window reproduced on held-out.
- **`P8` came closest: one criterion, narrowly.** At 10 substeps it fails *only* the merge
  test, at 0.158 against a 0.15 ceiling — and against `P2`'s 0.045 + 0.05 slack. It is more
  accurate than everything except the oracle and the combination, and less accountable than
  the cheap tag arm.
- **`P9` confirms it is a readout repair, not a dynamics repair.** Its global order parameter
  is **identical to `P4`'s** (0.9583/0.9482 at 10; **1.0000** at 200) because its dynamics are
  byte-identical. Its attribution advantage evaporates at convergence (merge fraction
  0.094 → 0.512) for the stated reason: once most of the trajectory is spent merged, averaging
  over it averages over the collapse.

## 5. `P8`'s structural claim is NOT supported — the control caught it

Pre-registered honest reading: *"frequency spread helps, and structurally-derived frequency
helps more."* The first half survives. **The second does not.**

| | spectral | ω shuffled | ω random | structure adds beyond spread? |
|---|---|---|---|---|
| @10 K=2 | 0.597 | 0.542 | 0.382 | **False** |
| @10 K=3 | 0.436 | 0.383 | 0.389 | True |
| @200 K=2 | 0.584 | 0.534 | 0.406 | **False** |
| @200 K=3 | 0.445 | 0.356 | 0.411 | **False** |

**3 of 4 cells: False.** Shuffling the frequency values across nodes — destroying every trace
of structure while keeping the distribution — costs only ~0.05. So most of `P8`'s benefit is
**desynchronisation**, not structural coding. The registered claim narrows to:

> **A frequency spread breaks the pathological synchrony. Deriving that spread from graph
> structure is NOT shown to add beyond the spread itself.**

This is exactly what the `SHUFFLED`/`RANDOM` controls were carried for, and it is the outcome
that would have been easiest to overstate without them.

## 6. The phase-free baselines did their job

`B_STRUCT_GATE_REACH` scores 0.532 / 0.361 / 0.263 — *above* `P0`, and above `P7` and `P9` at
several points, but well below `P8` and `P8P9`. So the oscillator is not merely re-reading the
world's wiring. And `B_STRUCT_GATE_CONTENT` now scores 0.328 / 0.180 / 0.105, **below `P0`** —
the content leak repair (A3.2) verified on held-out. Before the repair that same one-liner
scored 0.583 / 0.544 / 0.594 and beat the phase arm at every K.

## 7. The finding that carries no verdict — and must be escalated

`P8P9` — structural frequency **plus** trajectory readout — at the converged budget:

| | `P8P9` | oracle `P1` | tag arm `P2` | `P0` |
|---|---|---|---|---|
| K=2 top-1 | **0.704** | 0.780 | 0.459 | 0.503 |
| K=3 top-1 | **0.571** | 0.677 | 0.352 | 0.343 |
| K=4 top-1 | **0.432** | 0.560 | 0.263 | 0.251 |
| merge fraction K=2/3/4 | **0.002 / 0.003 / 0.001** | 0.000 | 0.045 / 0.051 / 0.049 | — |

It reaches **90% / 84% / 77% of oracle accuracy** while merging essentially nothing — better
attribution than the tag arm by more than an order of magnitude, and better accuracy than it
by +0.245 / +0.219 / +0.169.

**It carries no verdict, by construction**, because the ruling requires repairs to stand
alone. That was the right rule: `P7`, `P8` and `P9` each failed alone, and only their
combination works — which is exactly the confound the rule exists to prevent being hidden.

> **🟥 IT IS ALSO NOT YET SHOWN TO WORK.** `P8P9` has **no shuffle control** in this run. I
> registered criterion 5 — *"loses its advantage when phase correspondence is shuffled"* — and
> then did not build the shuffled variant of the exploratory arm. **Without it, `P8P9` is an
> unverified number, not a result.** It cannot be promoted on this evidence even if the
> combination rule were relaxed. That gap is mine and it needs one more run to close.

## 8. Process record — the first attempt cost $0.14 and returned nothing

The first launch completed **every** GPU computation and then died writing the receipt:
`TypeError: Object of type module is not JSON serializable`. Cause: `frozen_params` collected
`{n: getattr(P1,n) for n in dir(P1) if n.isupper()}`, and **`"P0".isupper()` is `True`**
(`0` is uncased), so it tried to serialise the imported module.

Worse, the partial-receipt handler I had written to make a crash survivable wrapped only the
world loop, so a failure *building* the receipt discarded a finished run. Both fixed; raw
results are now dumped the moment they exist. **Root cause: I smoke-tested `run_world()` but
never `main()`.** An end-to-end test of the whole path now exists and would have caught it for
free.

## 9. What is licensed

**Licensed — this exact sentence:**

> On synthetic multi-chain worlds of this construction, no single repair — structurally-derived
> repulsive coupling, structurally-derived frequency heterogeneity, or trajectory-integrated
> readout — preserved the phase engine's retrieval advantage while bringing chain merging below
> the preregistered safety threshold, at both the transient and converged substep budgets. At
> its converged fixed point the unrepaired phase engine is numerically identical to the scalar
> engine and merges every chain pair.

**NOT licensed:** any resonance-specific or CAS-specific claim; any claim for `P8P9` (no
shuffle control); any claim that structurally-derived frequency beats an unstructured spread
(3 of 4 cells say it does not); anything beyond these synthetic worlds; any merge into CMB-R1.

## 10. Stop condition

**Stopped, as directed.** No merge into CMB-R1. The phase system remains a quarantined
experimental subsystem and the production memory board stays scalar and accountable. Next step
is the **third-party audit** — 🔒 owner-actionable; neither Claude nor GLM may serve.
