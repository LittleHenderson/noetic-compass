# RESULT — `WORLD_REALIZATION_GRAMMAR_V1_PILOT_S2` (`R1` + `R1B` only)

**Lock:** `89fb3dba` · silent enforcement · same 16 frozen cells as v1
**Decides:** `R1` (leakage) and the `R1B` diagnostic. `R2`–`R6` have not run.

---

## 1. Three arms, same cell set — the comparison that matters

| Arm | Prompt contents | Leak rate (16 cells) |
|---|---|---|
| pilot v1 (VOID) | **label printed in capitals** + prohibition + full spec | `0.4058` |
| v2 generator | label in header + full definitions + **explicit prohibition** + self-check | `0.1625` *(restricted to these 16 cells; overall was `0.142`)* |
| **S2** | **silent** — criterion only, no label, no prohibition | `0.1969` |

Two readings — **with owner-corrected evidential weight**:

1. **Suggestive, not causal:** v1's `0.4058` falling to `≈0.16–0.20` when the label leaves the
   prompt is a *demonstration that the contaminated prompt produced heavy leakage* — v1 differed
   in multiple ways and had an apparatus defect, so it is not a clean estimate of label priming.
2. **The clean causal test of the instruction is S2 vs E only.** v2 is informative but
   uncontrolled (it also carried definitions and other context S2 lacked). See
   `RESULT_PILOT_E_VS_S2.md` for the controlled comparison.

## 2. But the aggregate hides the real structure — the variance moved

**Starved cells (the grammar's target) improved dramatically under S2:**

```
7c  0.375 → 0.000   -0.375        6a  0.300 → 0.050   -0.250
7a  0.300 → 0.100   -0.200        5d  0.350 → 0.300   -0.050
1d  0.275 → 0.500   +0.225  ← the exception
starved mean delta: -0.130
```

**Previously-clean cells got worse:** `1b 0.050 → 0.700` (!), `2b 0.000 → 0.250`,
`2c 0.075 → 0.250`, `3d 0.150 → 0.250`.

## 3. The discovery: a DRIVE-topic leak channel, distinct from the World channel

```
leak rate by drive:   1: 0.600   2: 0.233   3: 0.250   5: 0.225   6: 0.075   7: 0.062
1b leak words:  spiritual ×13, mental ×1     ← a MENTAL cell leaking "spiritual"
1d leak words:  spiritual ×9,  physical ×3
own-World-name share of leaks:  0.471   (v1: 0.719)
```

**Drive-1 (God) cells leak the word "spiritual" regardless of their World.** This is not the
World-realization problem — it is topical vocabulary: writing about longing for God without the
word "spiritual" is hard *unless something tells the author not to use it*. v2's explicit
instruction suppressed exactly this channel (`1b` was `0.050` there); silence reopened it.

So there are **two separate leak mechanisms**, now measured:

| Channel | Cause | Suppressed by |
|---|---|---|
| **label priming** | target word printed in the prompt | removing the label (S2 *and* a clean explicit arm) |
| **topic vocabulary** | the drive's subject matter invites a World word (`God → "spiritual"`) | the explicit instruction — silence reopens it |

## 4. `R1` disposition — reported against a bar I under-specified

The frozen `R1` reads *"starved-cell leakage reduced materially from v2"* without a number —
a defect in my pre-registration, disclosed. On the starved cells: mean delta **`-0.130`**,
`4/5` baselined cells improved, `7c` to zero; exception `1d +0.225` (drive-1 topic channel).

**Formal status, per owner correction: `R1_PRIMARY_UNSCORABLE_THRESHOLD_UNDEFINED`** — the
pre-registered bar had no number, so no pass/fail is scorable against it, and a custom
post-result category must not be mistaken for a preregistered pass. Descriptive findings:
`4/5` baselined starved cells improved; `1d` worsened; starved-cell mean decreased `0.130`;
overall leakage `0.1969` (v2 on the same cells: `0.1625`).

`R1B` criterion-copy: mean recall **`0.039`** — the authors are *not* copying the grammar text.
Held-out transfer (`R4`/`R5`) remains the decisive test, but the copying channel looks quiet.

## 5. Consequence for the v3 budget

Per-cell pass rates now vary by mechanism: worst observed is `1b` at `p_pass = 0.30` under
silence — where `P(≥3 clean of 8) ≈ 0.45`. **A uniform candidate budget cannot survive drive-1
under silent enforcement.** Either the explicit instruction returns (clean form, no label), or
drive-1 cells get materially larger budgets, or the arms are compared head-to-head first.

## 6. Running now

The owner-sanctioned matched diagnostic: an **E-arm** — identical criterion, families, cells,
and budget; the ONLY difference is one frozen prohibition paragraph (no label anywhere). This
cleanly separates *instruction compliance* from *label priming*, which v2 cannot do (its prompt
also carried the label and full definitions). Quarantined, non-claim-bearing, per the owner's
arm-separation rule.

## Status

`R1 mixed-improved / R1B quiet / R2–R6 pending / QUARANTINED / Gate 2 OPEN at 0.38`
