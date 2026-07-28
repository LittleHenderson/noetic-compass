# RESULT — `S3-1` FINAL: `ALL_ROWS_PASS`

**The 13-row mechanical table is fully green.** No prose override was used; the last two rows
were earned under the motive-repaired prompt, not carried from the pre-repair arms.

```
R1     PASS   0.0219 overall, worst cell 0.100
R1B    PASS   0.0415
R2-G   PASS   world 0.4948 · drive 0.5365 · foundation16 0.0573   (all ≤ 0.60, grouped)
R3-W   ----   train 0.7986
R3-D   ----   train 0.9167
R3-J   PASS   train 0.7569  (bar 0.70 — FIRST joint pass of the campaign)
R4     PASS   heldout 0.6042, gap +0.1528  (≤ 0.20)
R5     PASS   judge 0.6875 vs char 0.5417 / tfidf 0.4792
R6A    PASS   0.0125 (160, flash, motive-repaired prompt)
R6B    PASS   0.0187 (160, claude-haiku, motive-repaired prompt)
P12    PASS   0.9333 vs baseline 0.6833
P63    PASS   0.8500 vs baseline 0.7333
P74    PASS   0.9375 vs baseline 0.5833
```

## The arc, in three instrument generations

| | joint recovery (train) | cause of change |
|---|---|---|
| confirmatory, thin judge key | `0.2222` | — |
| same items, full canon (`S3-0`) | `0.6181` | evaluator was starving |
| motive-repaired items (`S3-1`) | **`0.7569`** | scenarios now reject the close rival |

Each step attributed by changing one thing. The boundary that was the whole point — generative
union vs companionship — went `0.5833 → 0.9375`.

## Disclosed caveats (unchanged from the eval report)

Held-out World on the new items (`0.6875`) sits below the old items' `0.8750` — motive-heavy
scenarios trade some World surface for drive structure. Family-clustered `n` is `48/16`.
`P74` remains one-sided (no drive-4 cells among the 16). Twelve of 28 cells are unobserved under
the repaired instrument.

## v3 budget — from the frozen rule (worst-cell LCB, all rejection stages, dependence)

```
worst observed cell         2c: 18/20 clean → Wilson 95% LCB 0.6990
family-level rejection      0/64 observed → rule-of-three upper bound 0.0469
P(complete family)          P(≥3 of 8 at LCB) × (1 − rej UB) = 0.9885 × 0.9531 = 0.9422

12 plans/cell   P(all 28 cells reach 8 families) = 0.9899     2,688 candidates
13 plans/cell   P(all 28) = 0.9987                            2,912 candidates
14 plans/cell   P(all 28) = 0.9999                            3,136 candidates
```

**Recommended: `13` plans per cell** — `0.9987` at the *lower-bound* rate, modest margin over 12
for the 12 unobserved cells. Structure: `28 × first-8-passing-of-13 × 3 = 672`, selection by
frozen plan order, surplus preserved as reserve.

## What this authorizes — and what it does not

**Authorized by the mechanical table:** proceeding to the `TKS_672_V3` full-corpus lock under the
motive-repaired instrument.

**NOT authorized:** Gate 2. Per `GATE_2_SUCCESSOR_CLOSURE_CONTRACT`, Gate 2 requires the frozen
v3 corpus to carry independently recoverable signal, a **small-model** internal readout beating
char and TF-IDF on untouched grouped data, the advantage on the clean drive axis *and* an
admissible World axis, all controls passing, and **the owner's explicit acceptance**. The corpus
is the prerequisite; the small-model readout ladder is the gate.

## Status

`S3-1 ALL_ROWS_PASS / v3 lock is next / Gate 2 OPEN at 0.38`
