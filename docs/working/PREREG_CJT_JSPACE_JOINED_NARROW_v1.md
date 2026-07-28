# PRE-REGISTRATION — `CJT-JSPACE-JOINED-NARROW-v1`

**The mainline scientific lane.** Committed before any joined measurement.
**Date:** 2026-07-27 · **Gate 2:** OPEN at `0.38`
**Governing contract:** `docs/working/CAS_HARNESS_CJT_BIAS_RPM_OHM_EXPERIMENT_CONTRACT_20260721.md`
(not restated here; this document only fixes the *first, narrow* experiment against it).

---

## 1. Why this lane, and why now

Gate 1 was earned on 2026-07-24 by **Attempt 11**, receiver-confirmed (`f95cc610`). The Jacobian
machinery — model graph, registered hooks, JVP/VJP path, artifact contract, evidence chain — is
**no longer the pending prerequisite**. It is proven to produce technically valid derivatives.

The open question is different: **does that machinery measure a native CAS circuit, or does it
merely produce valid derivatives?**

The 84-item scenario lane is **CLOSED** (`NOT_LICENSED_LEXICAL`, `bed3fc94`). Its negative
constrains mean-pooled bulk hidden states under a linear probe at `160M`. It does **not** test
output-causal J-space directions, which is the instrument the program actually intends to deploy.

## 2. Scope — deliberately narrow

**Not** all 28 Foundations. **Not** prompt injection. **Not** a complete PCBA board.
**One** identifiable cause–bias–effect circuit and **one** ordered prerequisite gate:

```
V_ext
  |
  v
C : ^8 Above/Cause
  |
  v
CJT< C | B:^5 Female  =>  E:^9 Below/Effect >
  ^
  |
RPM interlock: Desire -> Wisdom -> Power
```

The PCBA source assigns these directly: `^8` to the entering cause, `^5` to the accumulated bias
substrate, `^9` to the produced output. **RPM is not a fourth CJT terminal**, and a downstream
result cannot prove the prerequisite sequence ran (contract §, restated because it is the most
common error mode).

## 3. Observation map — chosen and FROZEN before measurement

The contract offers two. **This experiment freezes:**

> **`C_EQUALS_I_AT_REGISTERED_TEST_POINT`** — `c` and `i` are the same registered quantity at the
> registered test point.

Chosen because it is the weaker assumption and requires no additional transduction function to be
validated first. `EXPLICIT_TRANSDUCTION` (`c = T(V_ext, B)` with `I_internal` measured downstream)
is **not** used here and would be a separate pre-registration. Without a frozen choice the CJT and
CAS-Ohm equations are disconnected.

## 4. Phases — AMENDMENT 1, added before any measurement

The original version of this pre-registration went straight to the CAS interpretation. That is
**the same error the campaign made sixteen times** and it is corrected here, before any data.

> **Attempt 11 proved that derivatives can be produced correctly. It did NOT prove that a
> registered semantic direction is identifiable.** Those are different claims, and only the first
> is established.

### Phase A — positive control, MANDATORY, runs first

The joined experiment's equivalent of `T0`. Before testing any CAS interpretation, prove the
joined instrument can recover a **deliberately present, output-causal signal**:

- one exact target output token
- one matched distractor
- one frozen layer, hook, and token position
- one known direction expected to move the target logit margin
- random, orthogonal, wrong-sign, wrong-layer, wrong-token controls

**If Phase A fails, STOP. Do not interpret the CAS arm.** A null in the CAS arm is
uninterpretable without this, exactly as eight `NOT_LICENSED` verdicts were uninterpretable until
`d755665b` ran.

### Phase B — observational CAS map

Design: `external-drive dose × bias condition × RPM condition × prompt family × seed`.

RPM prerequisites manipulated independently on a controlled microtask:

| Prerequisite | Operationalization |
|---|---|
| **Desire** | explicit target or requested outcome |
| **Wisdom** | the rule or information necessary to derive it |
| **Power** | the available execution affordance or response capability |

Conditions: intact `D→W→P` · Desire missing · Wisdom missing · Power missing · all three present
but **reordered** · irrelevant rank/decodability-matched chain · corrupted prerequisite · restored
chain · semantic sham.

**A final correct answer is not proof that RPM ran.** The ordered prerequisite trace must itself
be observed or manipulated.

### Phase C — freeze, before any intervention

Freeze: cause direction · bias direction · output functional · operating region · layer and token ·
intervention dose range · all thresholds · control distributions · untouched holdout groups.

**The mediator is not revised after observing intervention outcomes.**

### Phase D — causal intervention

`alpha` applied separately to the registered cause and bias directions. Requires **all six**:

1. intended internal coordinate moves in the registered direction
2. downstream `E` moves in the predicted direction
3. wrong-sign, random, orthogonal, wrong-layer, wrong-token, sham all remain bounded
4. bias intervention does not move `V_ext` or `C` beyond frozen tolerance
5. RPM ordering and trace remain intact
6. clean-task capability stays inside the preregistered budget

All registered coordinates, the mediator, and `E` are **frozen before labels are opened**. No layer
or token-position search on evaluation data.

## 4b. Scientific pass gates

| Gate | Passes only if |
|---|---|
| **`J-POS`** | the intended direction moves the target output beyond the preregistered control envelope |
| **`J-OBS`** | `beta_dir` sign-stable across seeds and groups; interval excludes the registered null region; held-out relationship beats null, affine-only, saturating, Hill, piecewise, and monotone alternatives under the frozen comparison; transfers to untouched groups |
| **`J-BIAS`** | manipulation changes `B`; `V_ext` and `C` stay within hold tolerances; `g_B` stable and independently identified; `r_pi_CAS_derived` not denominator-dominated |
| **`J-RPM`** | intact ordered chain beats every missing, reordered, irrelevant, and sham condition after bounding subspace containment, unequal probe strength, token count, lexical intensity, and rank/decodability differences |

**Causal intervention runs only after every observational gate passes.**

## 5. Primary quantities

```
beta_dir = d e / d c
g_B      = d e / d b
G_eff    from  Delta i = G_eff * Delta V_ext + error
Delta_RPM = E(intact ordered D->W->P) - E(disrupted prerequisite condition)
```

`beta_FR` and `beta_dir` are **not interchangeable** (contract) — a norm measures magnitude, not
directional sensitivity. Only `beta_dir` is primary.

`r_pi_CAS_derived = beta_dir / g_B` is computed **only** when `beta_dir` and `g_B` are
independently identified in the same local regime **and** the CI for `g_B` stays away from zero.
Near-zero or sign-unstable `g_B` makes it `UNAVAILABLE` — **not** an estimate with wide bars.

**CAS-Ohm slope is primary only after the observation map above is frozen**, which it now is.

## 6. Frozen hypotheses

| # | Hypothesis |
|---|---|
| `J1` **Cause direction** | The registered Jacobian/J-space cause direction predicts untouched output change better than surface, random, and orthogonal controls. |
| `J2` **Bias identification** | Bias manipulation moves the registered `B` coordinate while `V_ext` and `C` stay within frozen tolerances; `g_B` is sign-stable across groups. |
| `J3` **RPM prerequisite dependence** | The intact ordered `D->W->P` chain differs from missing, reordered, irrelevant, and sham chains, after containment and probe-strength controls. |
| `J4` **Causal control** | A registered intervention `alpha` moves the intended mediator **and** downstream `E` in the predicted direction, while wrong-sign, wrong-layer, wrong-token, random, orthogonal, and sham interventions stay bounded. |

## 7. Required controls

Random directions · orthogonal directions · wrong sign · wrong layer · wrong token · bias sham ·
RPM sham · missing prerequisites · reordered prerequisites · surface-text baselines · competing
nonlinear response curves.

`alpha` is **never applied silently** (contract). Every intervention is dosed and logged.

## 8. Order of operations — non-negotiable

1. Build and run the **observational map**.
2. **Freeze** the mediator and the output functional.
3. Only then run cause / bias / RPM **interventions**.

Running intervention before the observational map is frozen would let the intervention define its
own target.

## 9. What a pass licenses

> *"On the registered model and test point, an output-causal J-space direction instantiates a
> measurable CAS Cause–Bias–Effect relation with ordered RPM prerequisite dependence, and a dosed
> intervention on that direction predicts downstream output change beyond surface, sham, random,
> orthogonal, wrong-layer, and wrong-token controls."*

Licenses **nothing** about: the 28 Foundations, prompt injection, board-level PCBA claims, other
models, or product capability. **It does not close Gate 2** — that is a separate governance
decision under `G2-JSPACE-SUCCESSOR`, and it is the owner's call, never declared equivalent after
the fact.

## 10. Standing rules carried in

- Statistical uncertainty cannot convert *did not exceed* into *exceeded*.
- Grid position never licenses semantic equivalence; TKS and CAS manifests stay separate.
- A control that fires is evidence, not an obstacle.
- Effective `n` is the honest grouping unit, never the row count.

## Status

`LOCKED / COMMITTED BEFORE JOINED MEASUREMENT / NOTHING LICENSED`
