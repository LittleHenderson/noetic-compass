# Receipt tags + 28-cell Eye pairing — TEST PLAN (v1, 2026-10-20 PDT). Frozen before any package. Nothing run.

## 0. Order of work

1. **Tag census, laptop, 0 USD, counts only.** Apply the stage-1 rules to every receipt and backlog item of the wave-6
   c50 host records and the RB-I3 run (both spent, both on disk). Publish per-field counts: tagged vs `UNTAGGED`, and
   the 28-cell histogram. Floor: **at least 20 of 28 cells with 8 or more items** across the planted backlog families,
   else the stage-2 exam cannot separate cells and the plan STOPS at stage 1 (`NOT_EXERCISED`; report).
2. **Build stage 1** (tag rules, `cas_address/1`, back-off) with laptop tests; no behaviour change when the switch
   `EYE_CELLS` is OFF (byte-identical records: a hard gate).
3. **Build stage 2** behind `EYE_CELLS`; laptop practice on the RB-I3 synthetic world extended with Domain-tagged item
   kinds (each item kind gets a hidden cell, each cell a hidden primary and secondary faculty, as RB-I3 does per
   Foundation).
4. Sealed package + preregistration + custodian exam + owner sign line (hash and cap). Then one CPU run.

## 1. Arms

| Arm | What |
|---|---|
| FULL | wave-6 brain, EYE_PAIRING (7 x 7) ON, EYE_CELLS OFF — **the baseline to beat** |
| CELLS | EYE_CELLS ON (196-cell table + 28-simplex attention) |
| CELLS_RATIO | CELLS with the count-ratio focus (no geometry) |
| CELLS_NOTAG | CELLS with every tag forced `UNTAGGED` (must equal FULL by the back-off rule: an instrument row) |
| CELLS_RANDOMTAG | tags drawn at random from a recorded seed (DeepSeek's noise control: must not beat FULL) |
| CUT_VIOLATOR, GUARD_VIOLATOR | as in wave 6 (must fail) |
| REPLAY | CELLS re-run (determinism) |

## 2. Exams (custodian, builder blind)

- **XC-PAIR:** the RB-I3 idle exam with items planted per cell (28 cells x 3 kinds x lives), keys hidden from the builder.
- **XC-PAIRW:** the same with K7 = a real recipe (wave 6's form), on a fresh draw from the real pool excluding every spent id.
- **Language and conversation no-harm:** English-64, Faces-64, 64 conversations, byte-identical across arms.

## 3. Hard gates

| Gate | Rule |
|---|---|
| H-OFF | EYE_CELLS OFF = wave-6 FULL byte for byte on every record |
| H-NOTAG | CELLS_NOTAG = FULL on the backlog (back-off works) |
| H-RANDOM | CELLS_RANDOMTAG resolved <= FULL resolved + margin (random tags must not help) |
| H-WRITE | Eye writes 0; tags never enter a value, a verdict or the gate (audited) |
| H-CUT | 0 faculty calls and 0 attention steps in conversation; the violator trips |
| H-GUARD | 0 guard trips on clean arms; the violator trips |
| H-NOHARM | 0 items lost on the language and conversation exams |

## 4. Marks

| Mark | Rule |
|---|---|
| M-C1 | XC-PAIR resolved: CELLS >= FULL + 1/16 of the backlog (pooled over lives) |
| M-C2 | XC-PAIRW resolved: CELLS >= FULL + 1/16 |
| M-C3 | wrong fixes 0 in CELLS |
| R1 (reported) | CELLS vs CELLS_RATIO (the geometry must at least tie) |
| R2 (reported) | per-cell tagged share; cells below the floor named |

## 5. Status words (frozen order)

1. instrument problem, floor not met, H-OFF or H-NOTAG false -> `INSTRUMENT_ERROR` / `INCONCLUSIVE`;
2. H-RANDOM, H-WRITE, H-CUT, H-GUARD or H-NOHARM false -> `FAILURE` / `EYE_CELLS_HARMED`;
3. all gates true, M-C1..M-C3 held -> `PASS` / `EYE_CELLS_EARNED_KEEP`;
4. all gates true, a mark missed -> `PASS` / `EYE_CELLS_NO_GAIN`.
Stage 3 (22 pathways) opens only on word 3. Spec-sheet words: `ENGINEERED-NOT-VALIDATED` unless word 3.

## 6. Honest predictions (before any data)

- The tag census is the first risk: kitchen items cluster in a few cells; `INCONCLUSIVE` at the floor about 0.4.
- If exercised on the synthetic world with hidden per-cell solvers: `EYE_CELLS_EARNED_KEEP` about 0.4 (the finer
  table matches the finer hidden structure), `EYE_CELLS_NO_GAIN` about 0.15, `EYE_CELLS_HARMED` about 0.05.
- On the real-recipe backlog (XC-PAIRW) the gain is expected small: the K7 items are all one kind.

## 7. Cost

Laptop for stages 1-3 (0 USD). The sealed run: one m6i.xlarge CPU host, about 0.02-0.10 USD; proposed cap 1.00 USD,
one attempt + one plumbing retry.
