# AUDIT DIRECTIVE — `D0` / `S0` CLOSURE AUDIT (fresh GLM)

**Issued by the owner, 2026-09-02.** This closes the 🔒 owner-actionable item that had been open
since the `D0` ruling: *name a third, distinct auditor.*

**Auditor:** a **fresh GLM instance**, appropriate for this **deterministic closure audit**.

> **Standing limit, owner's words:** a future **claim-bearing `D1` neural result** must still
> receive a **different-model-family or human replication**. This assignment covers deterministic
> closure only — it does not make GLM eligible for a neural claim on this line.

## Commits under audit

```
a47b951b   D0 design-invalidity closure
60727805   cascade span-gate correction
8b5c2ee3   S0_DO_NOT_BUILD_AS_A_CAS_BENCH
```

---

## ADDENDUM — `CJT-CASCADE-S0` CLOSURE AUDIT

```
# ADDENDUM
# CJT-CASCADE-S0 CLOSURE AUDIT

Also audit exact commits:

    60727805
    8b5c2ee3

Do not modify either commit.

Independently verify:

1. The committed package outputs:
       standalone residual
       full-run residual

2. Whether 0.2096 came from the committed package or from a separate
   GLM reimplementation.

3. Whether the residual depends on prior consumption of a shared random
   stream.

4. The 15-system random-baseline distribution and the committed
   system's percentile within it.

5. The full scale sweep over s and the exact point at which the
   registered gate changes status.

6. Whether the scale threshold is normalized or independently grounded.

7. Stage operator norms and whether any stability claim follows from them.

8. All 24 ordering permutations and the claimed exact parameter-
   relabelling equivalence.

9. Whether CAS_TYPED_ORDER and GENERIC_RELABELLED_ORDER are genuinely
   different hypothesis classes in the committed construction.

10. Whether any CAS-defined transformation, type-specific interface,
    legal action, memory port, or transition law appears in the measured
    Basis object.

11. Whether the strongest supported statement is only:

       GENERIC_SEQUENTIAL_PRODUCT_OUTSIDE_ADDITIVE_SPAN

    rather than:

       CAS_CASCADE_VALUE

12. Whether S0_DO_NOT_BUILD_AS_A_CAS_BENCH follows from the executable
    evidence without relying on the disputed 0.2096 number.

Return one:

    D0_S0_CLOSURE_AUDIT_PASS

    D0_S0_CLOSURE_AUDIT_PARTIAL:<typed unresolved item>

    D0_S0_CLOSURE_AUDIT_FAIL:<typed contradiction>

No fixes.
No redesign.
No training.
No AWS launch.
```

---

## Artifacts the auditor will need

| Item | Path |
|---|---|
| Span-gate re-measurement (items 1, 3, 4, 5, 7) | `CJT_CASCADE_S0/verify_span_gate.py` |
| Order-permutation equivalence (items 8, 9) | `CJT_CASCADE_S0/verify_order_absorption.py` |
| Order-blindness + ε side channel | `CJT_CASCADE_S0/verify_attack_findings.py` |
| `D0` 720-permutation equivalence | `CJT_OHM_D0/verify_d5_equivariance.py` |
| The construction under audit (item 10) | `CJT_OHM_0R/ohm0r.py`, class `Basis`, check `c13` |
| Written closure | `CJT_CASCADE_S0/DESIGN_REVIEW_OUTCOME.md`, `CJT_OHM_D0/DESIGN_REVIEW_OUTCOME.md` |
| The provenance correction (item 2) | `CJT_OHM_0R/CJT_OHM_0R_FINDINGS.md` §14 |

## Answers already on record, for the auditor to CONTRADICT rather than inherit

These are our own measurements. **The audit's value lies in disagreeing with them if they are
wrong** — do not treat this table as the answer key.

| # | Our recorded answer |
|---|---|
| 1 | standalone `0.054458` (additive `1.785643e-15`); full-run `0.0746` (additive `1.473e-15`) |
| 2 | **separate GLM reimplementation** — not the committed package |
| 3 | **yes** — the two committed figures differ from each other for this reason |
| 4 | 15 systems: min `0.026937`, mean `0.047810`, max `0.071911`, sd `0.013662`; committed at the **60th percentile**, `0.49` sd from the mean |
| 5 | `9.508132e-02` at `s=1.0` → `5.990553e-06` at `s=0.01`; gate flips to `FAIL` at **`s ≤ 0.05`** |
| 6 | **neither** — the `1e-3` threshold is absolute, un-normalized and not independently grounded |
| 7 | mean operator norm `1.2385` at `s=0.7`; **no stability claim follows** — this was narrowed by owner ruling, the load-bearing issue is **depth**, not the norm |
| 8 | worst `\|CAS_ordered − generic_relabelled\|` = **`0.0000e+00`** over all 24 orderings |
| 9 | **no** — they are the same hypothesis class |
| 10 | **none** — `W0`, `A`, `B`, `U` are all `RNG.normal` draws |
| 11 | **yes** — only `GENERIC_SEQUENTIAL_PRODUCT_OUTSIDE_ADDITIVE_SPAN` is supported, and §7 B4 shows the gate does not even read order |
| 12 | **yes** — the verdict rests on items 4, 8 and 10, none of which uses `0.2096` |

## Related standing item

`CJT-OHM-D1` is authorized for **design attack only** — no implementation, no training, no AWS
GPU, no CNCM integration. If `D1` ever produces a claim-bearing neural result, the
different-model-family or human replication requirement above applies to it.

---

# EXTENSION 2026-09-02 — add commit `90248303` (`CJT-OHM-D1`)

## Status correction, owner-issued

I previously wrote that filing this directive **closed** the third-auditor item. **That was an
overstatement.** The precise state:

```
Third auditor selected and briefed    CLOSED
Independent audit result              STILL OPEN
```

## Additional commit under audit

```
90248303   CJT-OHM-D1 design attack: D1_DO_NOT_BUILD + the precedence-chain finding
```

## The auditor should verify

```
 1. The zero-call rule really matches the four-call oracle over the reported
    200,000 items.
 2. The mask-only fraction is really 0.501350.
 3. All 119 x 120 precedence permutations were enumerated correctly.
 4. The precedence residual is reproducible.
 5. The flat residual is exactly zero.
 6. The chance test is genuinely independent of the correct action.
 7. No hidden action mask or repair mapping entered the chain.
 8. The effect comes from evidence timing and position, not mismatched
    dimensions, positional capacity, or compute.
 9. A matched generic recurrent chain cannot absorb the mechanism through a
    more general transformation than simple parameter permutation.
10. The label-accuracy versus recovery correlation is reproduced.
```

## Artifacts

| Item | Path |
|---|---|
| 1, 2, 10 | `CJT_OHM_D1/verify_d1_attack.py` |
| 3, 4, 5, 6, 7, 8 | `CJT_OHM_D1/verify_d1_attack.py`, section S4 |
| **9** | `CJT_OHM_D1/extend_absorption_test.py` |
| Written closure | `CJT_OHM_D1/DESIGN_ATTACK_OUTCOME.md` |

## Item 9 — partially answered before the audit, and the answer narrows my own claim

My original test searched **permutations only**, the weakest absorption group. Because `tanh` is
odd, the correct natural group is the **signed permutations** (`32x` larger). I enlarged the search
to all `119` relabelings by `3840` signed permutations:

```
PRECEDENCE CHAIN      4.0097e-02      (permutation-only: 4.6108e-02)
FLAT (D0/S0 shape)    0.0000e+00      (permutation-only: 0.0000e+00)
```

**The chain survives; the flat control is still exactly absorbed.**

> **This does NOT fully discharge item 9.** It settles absorption under the natural group. It does
> **not** settle whether a matched generic recurrent chain can **LEARN** the same function —
> expressivity, not absorption. **That part of item 9 is still open and the auditor should treat
> it as unanswered.**

## Answers on record for commit `90248303` — to CONTRADICT, not inherit

| # | Our recorded answer |
|---|---|
| 1 | relative shortfall `1.845175e-14`, action agreement `1.000000` over `200,000` items |
| 2 | **`0.501350`** (ours). The design attack reported `0.249850` under different cause priors — **different constructions, not merged** |
| 3 | all `119` relabelings, each against all `120` compensating permutations |
| 4 | chain best-case residual **`4.6108e-02`** (logit scale `1.116813`) |
| 5 | flat control **`0.0000e+00`** — reproduces the `D0`/`S0` death, proving the test is sensitive |
| 6 | free lunch **`0.201300`** vs chance **`0.200000`**; singleton action mask **`1.000000`** |
| 7 | no mask in the chain construction — every module emits into the full shared action space |
| 8 | **NOT independently isolated by us.** Positional capacity and compute are equal by construction (identical module shapes), but we did not run a dedicated control. **Treat as OPEN.** |
| 9 | signed-permutation absorption **`4.0097e-02`**; the **expressivity** half is **OPEN** |
| 10 | Pearson `r = 0.022389`, reproduced at `0.022779` on a second seed (attack-measured, not ours) |
