# Adaptive-τ Fisher-Rao — NOT RUN, because the sweep already determines its answer

**Status:** `NOT RUN / PRE-ANSWERED BY EXISTING MEASUREMENTS / NO COMPUTE SPENT`

## The proposal

Replace the fixed softmax temperature (which voided instrument ten by collapsing all geodesics
under `0.018`) with a deterministic rule: `τ = max(0.005, std(off-diagonal cosine similarities))`,
computed per arm. A rule, not a tuned dial.

The reasoning is sound and the defect it targets is real.

## Why it cannot produce new information

**Measured what the rule actually selects** (`pythia-1b`, layer 12, 4 frames, last token):

| Arm | off-diagonal cosine mean | std | **adaptive τ** |
|---|---|---|---|
| TKS | `0.9411` | `0.01326` | **`0.01326`** |
| compact CAS | `0.9658` | `0.01484` | **`0.01484`** |

Both land inside `[0.01, 0.02]`. The pre-registered temperature sweep (`616a9dfd`, run at `837aa6c2`)
already measured **both endpoints**, found both usable, and found compact winning at each:

```
T=0.01   TKS 2.0462   compact 0.6183   USABLE   compact wins
T=0.02   TKS 0.8045   compact 0.2280   USABLE   compact wins
```

The adaptive rule selects a temperature **fully bracketed by two agreeing measurements**. Its outcome
is interpolation between numbers already in hand, not a new observation.

## The general point

The sweep did not merely answer one temperature — it made the whole parameter family answerable
without further compute. Any selection rule landing in `[0.005, 0.05]` is pre-answered (compact wins,
no reversal); outside that range the metric saturates and the run voids by guard `S1`/`F5`.

That is the value of sweeping over picking: it forecloses the entire "but what if you tuned it
differently" line, which is otherwise unfalsifiable and could absorb unlimited GPU time.

## Correction to the accompanying analysis

The analysis proposing this rule reported results for it — *"real spread across 0.15–0.70 on 0–π"*.
Those are not adaptive-τ numbers. They are the **Option 3 output-distribution** results
(`02d78177`): compact `0.150255`, TKS `0.475994`, shuffled `0.699542`. No adaptive-τ run has ever
been executed. Results were attributed to an experiment that did not happen.

## Conclusion

Not declined on principle — declined because it is **mathematically redundant**. Twelve instruments
stand. Gate 2 remains OPEN at `0.38`.
