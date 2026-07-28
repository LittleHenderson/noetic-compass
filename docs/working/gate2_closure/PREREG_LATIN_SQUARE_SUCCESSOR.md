# PRE-REGISTRATION — `LATIN-SQUARE-SUCCESSOR-v1`

**Committed BEFORE the successor runs.** Owner-specified design.
**Date:** 2026-07-27 · **Gate 2:** OPEN at `0.38`

---

## 1. What this fixes

`SMALL-MODEL-RECOVERY-v1` produced a valid drive endpoint and a **structurally unidentifiable**
World endpoint. `GroupKFold` over foundations sorted `1a,1b,1c,1d,2a,…` placed every group sharing
a World into the same fold, so each test fold held exactly one World, absent from its own training
set. `world = 0.0000` across every representation is the signature of an impossible generalization
setup, not a negative result. **Void, not negative.**

## 2. Frozen fold table — Latin square over the 7 × 4 grid

`fold = (world_index + drive_index) mod 4`, with `world_index = "abcd".index(letter)` and
`drive_index = int(digit) - 1`. **The explicit cell-to-fold table is frozen here rather than
relying on library ordering:**

| | `a` | `b` | `c` | `d` |
|---|---|---|---|---|
| **1** | `F0` | `F1` | `F2` | `F3` |
| **2** | `F1` | `F2` | `F3` | `F0` |
| **3** | `F2` | `F3` | `F0` | `F1` |
| **4** | `F3` | `F0` | `F1` | `F2` |
| **5** | `F0` | `F1` | `F2` | `F3` |
| **6** | `F1` | `F2` | `F3` | `F0` |
| **7** | `F2` | `F3` | `F0` | `F1` |

Every test fold receives exactly one group per drive, all four Worlds, seven foundation groups,
and no separated siblings. Training folds contain all seven drives and all four Worlds.

## 3. Task validity at `n = 84` — stated limits

Each Foundation has **one** three-item sibling group. When it enters the test fold that class is
absent from training, so **a supervised 28-way classifier cannot learn the held-out class**. The
`direct 28-way` vs `predicted_drive × predicted_world` comparison is therefore **NOT RUNNABLE**
on this dataset and is not attempted.

| Task | Status | Chance |
|---|---|---|
| 7-way drive | **valid** | `0.1429` |
| 4-way World (corrected folds) | **valid** | `0.2500` |
| pairwise designated-contrast | **valid** | `0.5000` |
| zero-shot 28-way vs label descriptions | **valid, DIFFERENT TASK — labeled as such** | `0.0357` |
| supervised 28-way CV | **NOT RUNNABLE** — insufficient groups per class | — |

**Required next dataset** for the compositional test: `28 Foundations × 4 independent scenario
plans × 3 sibling variants = 336 items`. The four plans must be **independently authored**, not
paraphrases of one plan, so each Foundation can appear in both training and test while sibling
families stay intact.

## 4. Controls

**`C-PERM` — group-level label permutation.** Labels permuted **at the group level**, so all three
siblings retain the same permuted label. Row-level permutation would break the sibling structure
and create an easier, less relevant null. **Expected: return to chance.** Any above-chance result
means leakage through ordering, file structure, position, or split construction.

**`C-BODY` — body removed.** Every row is fed **the same constant text token**. None of the
following may reach the feature extractor: foundation code, World or drive fields, file name, row
identifier, generation order, group identifier, contrast type, prompt fragment. **Expected: exactly
chance / majority.** Any variation in model input defeats the control.

## 5. Criteria

| # | Criterion | Bar |
|---|---|---|
| `L1` | drive above chance | `> 0.1429`, permutation `p < 0.01` |
| `L2` | drive beats best lexical | `>= +0.10` AND group-bootstrap CI excludes `0` |
| `L3` | World identifiable | every test fold contains `>= 2` Worlds — **structural check, verified before scoring** |
| `L4` | World above chance | `> 0.2500` — reported **only** with the `56%` leak disclosure |
| `L5` | `C-PERM` returns to chance | permuted drive accuracy within `[0.05, 0.25]` |
| `L6` | `C-BODY` returns to chance | body-removed accuracy `<=` majority-class rate |

`L5` or `L6` failing → `VOID_PIPELINE_LEAKAGE` for the whole run, regardless of `L1`/`L2`.

## 6. Reporting rule carried forward from the owner

> **"Statistical uncertainty cannot convert *did not exceed* into *exceeded*."**

If the observed ordering puts a lexical baseline above the model, `L2` **fails**, whatever the
interval says. The numerical ordering is reported as **descriptive**; the significance of the
difference is reported **separately** and never used to rescue a failed criterion.

## 7. Canon

Per owner ruling, **"28 Foundations 1.0"** is the canonical authority. Full elaborated definitions
at `tootra_28_full_definitions.json`. Worlds `a/b/c/d = Spiritual/Mental/Emotional/Physical`;
drives `1`–`7` as defined there. **No silent renaming, remapping, reconciliation, or semantic
replacement** — `Agency`/`Structure`/`Purpose` are positional relabels and are not used.

## Status

`LOCKED / COMMITTED BEFORE RUN / NOTHING LICENSED`
