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
