# Which models can the Wrap Pipeline help? Not the dumb ones.

**Date:** 2026-08-27
**Status:** prediction from simulated models. Decides which real models to pay for.
**Governs:** `scripts/ccb_r1/capability_sweep.py`

---

## The question

`deepseek-chat` scores 95% on the deduction ladder, leaving no room for a
margin. Two ways to open a gap between what the model does unaided and what the
task demands:

1. **Use a weaker model.**
2. **Keep the model, raise the difficulty.**

Both sound equivalent. They are not, and this sweep says which one to take.

## Two predictions, both mine, one wrong

I predicted a **band**: too strong and there is no headroom, too weak and the
model cannot operate the scaffold, so the gain peaks in the middle. The
reasoning was that the RPM Gate asks the model a narrower question and acts on
the answer, so a model too weak to answer *that* honestly cannot be helped.

**The band does not appear.** The gain rises with capability, monotonically.

The first sweep also could not say *why*, because it derived reasoning skill,
meta-skill and bluffing from a single `level` — welding together the very axes
that needed separating. Fixed by making the three explicit and sweeping them
independently.

## The grid

Simulated models, n=100 per cell, wrapped minus bare.

**M3 deduction**

|  p_route ↓ / p_fabricate → | 0.00 | 0.25 | 0.50 | 0.75 | 1.00 |
|---|---:|---:|---:|---:|---:|
| **0.00** | +0.0% | +6.0% | +2.0% | −1.0% | +1.0% |
| **0.25** | −2.0% | +7.0% | +5.0% | +4.0% | +9.0% |
| **0.50** | −1.0% | +11.0% | +14.0% | +16.0% | +23.0% |
| **0.75** | −3.0% | +12.0% | +19.0% | +26.0% | +36.0% |
| **1.00** | +0.0% | +21.0% | +29.0% | +38.0% | **+50.0%** |

**M1 honesty**

|  p_route ↓ / p_fabricate → | 0.00 | 0.25 | 0.50 | 0.75 | 1.00 |
|---|---:|---:|---:|---:|---:|
| **0.00** | +28.0% | +17.0% | +18.0% | +16.0% | +0.0% |
| **0.25** | +33.0% | +23.0% | +23.0% | +22.0% | +6.0% |
| **0.50** | +40.0% | +34.0% | +31.0% | +31.0% | +17.0% |
| **0.75** | +43.0% | +41.0% | +41.0% | +41.0% | +32.0% |
| **1.00** | **+50.0%** | +50.0% | +50.0% | +50.0% | +50.0% |

`p_route` — can the model find a chain that exists?
`p_fabricate` — with no answer, does it invent one rather than decline?

## What the grid says

**M3 gain is a product, not a sum: reasoning × bluffing.**
The bottom-right corner — reasons perfectly, always bluffs — gives +50%. Kill
either factor and the gain collapses. The top row (no reasoning) is flat near
zero *whatever* the bluffing rate, and the left column (never bluffs) is flat
near zero *whatever* the reasoning. The pipeline **cannot supply reasoning**; it
can only stop a competent reasoner from bluffing.

**M1 gain is carried by reasoning alone.**
The bottom row is +50% flat across every bluffing rate: once the model can
assess its own sufficiency, the RPM Gate converts a confident wrong answer into
an abstention regardless of how it would otherwise have bluffed. The top row is
where it collapses — a model that cannot tell whether it has enough information
cannot be gated on that judgement.

**The wrapper can cost you a little.** The left column of M3 carries small
negatives (−1% to −3%). With no bluffing to catch, Domain Coherence still
occasionally withholds on an item the model happened to get right. Real, small,
and worth reporting rather than rounding away.

## The answer

> **A dumber model gives the pipeline less to work with, not more.**

Option 1 is backwards. The subject that shows the largest effect is a model that
**reasons well and bluffs when stuck** — which describes most frontier models on
a task that is genuinely hard for them.

So take option 2: **keep the strong model and raise the difficulty.** That is
what `hard_procedure()` and the `near_misses` axis are for. If the strong model
beats that ladder too, re-derive the task sets as natural-language reasoning —
do not reach for a weaker model, because the measurement gets *worse*, not
better.

There is one legitimate use for a weak model: **pipeline shakeout.** Proving the
run completes end to end without spending frontier budget. Not evidence.

## What this is not

**Simulated models are a model of models.** Every number above comes from a
three-parameter caricature, not from anything real. The grid is worth having
because it says which real models to pay for and which comparison to run — it is
not itself a result, and no claim about CAS should cite it.

The specific thing it cannot know: whether real models' reasoning skill and
self-assessment skill track each other the way this simulation assumes
(`p_meta = 0.5 + 0.5 · p_route`). If a real model reasons well but assesses its
own sufficiency badly, M1's headroom is larger than the grid suggests. That is
exactly what `honesty_procedure()` measures, and it remains unrun.

## Reproduce

```
python scripts/ccb_r1/capability_sweep.py             # the single-axis ladder
python scripts/ccb_r1/capability_sweep.py --grid      # the grid above
```

No network, no keys, no cost. `FindingTests` in
`scripts/tests/test_ccb_r1_capability_sweep.py` locks the headline: if a weaker
reasoner ever starts giving the pipeline *more*, the recommendation here needs
revisiting.
