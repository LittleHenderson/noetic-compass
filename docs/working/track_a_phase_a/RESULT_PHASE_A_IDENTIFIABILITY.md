# RESULT — `PHASE_A_IDENTIFIABILITY`

**Track:** `TRACK_A_PHASE_A_IDENTIFIABILITY` · **Lock:** `00a2d986`
**Protocol:** `PREREG_CJT_JSPACE_JOINED_NARROW_v1` amendment 1 (`17159fce`)
**Verdict:** **`PHASE_A_IDENTIFIABILITY_PASS`**

---

## Result

Target `" Paris"` → token `7785`. Distractor `" London"` → token `4693`. Both verified single tokens.

| Condition | Δ target-logit margin | CI 95% |
|---|---|---|
| **registered** | **`+1.2500`** | `[+1.0000, +1.5000]` |
| wrong sign | `-1.6667` | `[-3.5000, +0.0000]` |
| random | `+0.0000` | `[-1.1375, +1.1375]` |
| orthogonal | `+0.0333` | `[-1.1375, +1.0000]` |
| wrong layer | `+0.4167` | `[+0.0000, +0.5000]` |
| wrong token | `+0.1667` | `[+0.0000, +0.5000]` |
| sham (shuffled groups) | `+0.4167` | `[+0.0000, +0.5000]` |

```
control envelope (max |mean| over controls)  0.4167
registered - envelope                       +0.8333   bar 0.50   PASS
generalizes to untouched groups              True
```

## The independence check passed in its strongest form

```
calibration-group effect (diagnostic only)   +0.8333
UNTOUCHED-group effect                       +1.2500
```

The direction performs **better on groups it never saw** than on the groups it was built from.
That is not direction fitting — a fitted direction decays on held-out data, it does not strengthen.

Wrong-sign inverts cleanly (`-1.6667`), so the effect is directional rather than a generic
magnitude artifact. Random and orthogonal sit at essentially zero (`+0.0000`, `+0.0333`).

**What this licenses:** the joined instrument can recover a deliberately-planted, output-causal
direction on untouched data. Attempt 11 established that derivatives are computed correctly; this
establishes that a registered direction is **identifiable**. Different claims, both now held.

---

## Two caveats, recorded because the pass does not excuse them

### 1. Effective `n` is `6`, not `30`

The seed loop varies only `random` and `orthogonal`. For every deterministic arm — `registered`,
`wrong_sign`, `wrong_layer`, `wrong_token`, `sham` — the direction is identical across seeds, so
the 30 logged values are **6 unique measurements repeated 5×**.

The reported `sd` and CI for those arms therefore reflect variation **across the 6 untouched
prompts**, not across seeds, and the intervals are **narrower than an independent-sample reading
would justify**. Effective `n = 6` untouched prompt families.

This is the same row-vs-group distinction that has bitten this campaign before, and it is
disclosed rather than left for someone to find.

### 2. `wrong_layer` and `sham` are not zero

Both sit at `+0.4167`. They are what set the control envelope, and they mean **a non-specific
component exists** — injecting any vector of norm `alpha = 4.0` into the residual stream perturbs
logits somewhat, and the sham direction still lives in the same activation subspace.

The registered effect is `3×` the envelope and clears the pre-registered bar, so the pass stands.
But the correct reading is *"registered strongly exceeds a non-zero control floor"*, **not**
*"only the registered direction does anything."*

---

## What this does and does not unlock

**Unlocks:** Phase B, the observational native-CAS map. Per the frozen protocol, a Phase A failure
would have forbidden any CAS interpretation; it passed, so Phase B may proceed.

**Does not license:** anything about CAS Cause/Bias/Effect, RPM prerequisite dependence, the 28
Foundations, Gate 2, or Gate 3. This is a **calibration control on a factual microtask**. It proves
the instrument, not the theory.

**Does not close Gate 2.** Gate 2 requires small-model semantic authority by classification
(`GATE_2_SUCCESSOR_CLOSURE_CONTRACT`, Q1–Q3). Causal identifiability is Gate 3 evidence.

## Recommended before Phase B

Widen the deterministic arms to more untouched prompt families so effective `n` exceeds `6`, and
add a dose-response sweep over `alpha` — a genuine causal direction should scale, while a
non-specific perturbation floor should not.

Receipt with full provenance: `phase_a_receipt.json`.
