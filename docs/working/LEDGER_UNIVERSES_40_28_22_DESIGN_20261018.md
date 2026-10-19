# Ledger universes on the real CAS structures: 40 states, 28 drives, 22 pathways

Fix G. Written 2026-10-18. **Design only.** No code reads or writes this yet. The only artifact besides this page is the frozen schema `docs/working/LEDGER_UNIVERSES_40_28_22_SCHEMA_20261018.json` (sha256 `a8217c9d821244a4f3da9ce145a432bddd6f3550604795f8d30a04bd92a26a3f`).

Claim status of this page: **ENGINEERED-NOT-VALIDATED** (a design). Nothing here is a result.

## 1. Why this exists, in plain words

The Lacunarity Machine (`Documents\Codex\2026-10-14\lacunarity_machine_v1`) keeps a write history and tells four things apart for each "cell" (each thing the brain could know):

| state | plain meaning |
|---|---|
| COVERED | we tested it, and it was right often enough |
| NO_EVIDENCE | we never tested it |
| LACUNA | we tested it, it was wrong, and it was **never taught** |
| FADED | we tested it, it was wrong, but it **was taught** before (it slipped) |

Today its cells are synthetic: four keys, eight memory slots, sixteen panel items, a list of arms. The owner asked to "redeem 22×40": put the same machine on the real CAS structures.

A word of warning about names. `helm_brain_22x40.py` uses "22×40" for **22 ingredients × 40 parameters**. That is a different thing. In this design "22×40" means **22 capability pathways × 40 cognitive states**. The two must never be mixed up in any document.

## 2. The five universes

Three **marginal** universes (one CAS structure each) and two **grids** (two structures at once). Each is read on its own. They are never joined (see section 6).

| id | cells | what one cell is | eligible cells |
|---|---|---|---|
| **U40** | 40 | one cognitive state: a Noetic (`^0`..`^9`) in a Domain (P, C, E, O). Written `P0`..`O9`. | 40 |
| **U28** | 28 | one domain-specific drive: a Drive (F1..F7) in a Domain. Written `F5^O`. | 28 |
| **U22** | 22 | one capability pathway: A0, D1..D7, W1..W7, P1..P7 | 22 |
| **G22x40** | 880 | (pathway, cognitive state), e.g. `W5/O6` | 880 |
| **G28x40** | 1,120 | (domain drive, cognitive state), e.g. `F5^O/O6` | 280 (see below) |

**Why only 280 of the 1,120 G28x40 cells are eligible.** In CAS notation a compound state `^n^D_{F_k}` has **one** Domain `D`, shared by the Noetic and the Drive. So one event can only reach the cells where the drive's Domain equals the state's Domain: 7 drives × 10 Noetics × 4 Domains = 280. The other 840 cells are marked `NOT_ELIGIBLE` with the reason "drive domain differs from state domain; needs an event that names both domains". They are **not** lacunae. They become eligible only if receipts one day carry a separate Domain for the drive.

**Registers are a tag, not a fifth axis of cells.** Each cell keeps a register set `|⟨…⟩` (Clarification 10, section 6, step 1): the Registers (T, A, f, E) its charges arrived in. That is occupancy only. It makes no claim about how registers interact. No `+` and no `×` are written for it.

## 3. Charge rules (CR-1)

A **charge** is an event that writes to a cell: "this was taught". The machine also records **REFUSED** (a write that was offered and turned down) and **PROBE** (a test answer: RIGHT, WRONG or UNDETERMINED).

### 3.1 Which events charge, and which Noetic they charge

The Noetic of a charge is chosen by the **Colloquialism Test** (Clarification 6): write the plain phrase a person would use for what happened, then match it to the canonical colloquialism map. The table is frozen as rule set CR-1.

| rule | brain event (from its receipt) | plain phrase | Noetic charged | why (canonical colloquialism) |
|---|---|---|---|---|
| CR-1.1 | **Recipe fit**: an admitted write that sets or changes what an outcome is made of (a recipe requirement) | "worked out what it's made of" | `^6` Male | "Breaking it down." / "Looking at what's underneath." An Idea composed of other Ideas. |
| CR-1.2 | **Teaching step, first time** for that item: an admitted, receipted write into memory | "now it's part of what I know" | `^5` Female | "It's who I am." / "We are the sum of our experiences." The Mind is composed of what it took in. |
| CR-1.3 | **Teaching step, repeat** (the same item taught again in a later pass) | "practice makes perfect" | `^7` Rhythm | "Practice makes perfect." / "Getting into a groove." Rate and pattern of exposure. |
| CR-1.4 | **Repair**: a wrong answer found, taken apart, corrected, and the corrected answer returned | "found the flaw and fixed it" | `^6` Male | Anti-drift note: audit / find-flaws vocabulary is `^6`, **not** `^3` (which is visceral) and **not** `^8` (which is associative). |
| CR-1.5 | **Gate refusal** (RPM Gate G1..G4, `G-ABSENT`), receipt failed, memory check refused | "it wouldn't take it" | **none** | Refusals do not charge. They are logged as REFUSED against the cell they would have charged. |
| CR-1.6 | **RPM order refusal**: a pathway stage offered before its prerequisite | "you can't skip a step" | **none** | Logged as REFUSED with reason `RPM_ORDER`. See 3.4. |
| CR-1.7 | **Readout** (an answer on a panel or a held-out case) | "let's see if it knows" | **none** | A PROBE, scored RIGHT / WRONG / UNDETERMINED. UNDETERMINED is not wrong (owner ruling), but it is not right either, so it does not reach the floor. It is counted on its own line. |

Noetics with **no charging event today**: `^0`, `^1`, `^2`, `^3`, `^4`, `^8`, `^9`. The recipe brain has no event whose plain phrase matches their colloquialisms. Their cells stay NO_EVIDENCE. They are not lacunae, because nothing was ever offered.

### 3.2 Domain

The Domain comes **from the receipt** (`domain` field: P, C, E or O). The receipt says which level the work was at. If the receipt has no domain, a source adapter may declare one **frozen default** for the whole source (for example: "the live kitchen recipe loop is Operational, O"). The event then records `domain_source = ADAPTER_DEFAULT`. If neither exists, `domain_source = NONE` and **no U40, U28 or grid cell can be charged** by that event.

### 3.3 Drive

The Drive comes **from the RPM pathway the receipt used**. Pathways D*n*, W*n*, P*n* belong to Drive F*n*. A0 (Pure Desire) belongs to no single drive, so an A0 event charges U22 only. If the receipt names no pathway, no U28, U22 or grid cell is charged.

Not used for the Drive: drive levels, stages (Rising / Peak / Waning / Absent) or any "operating point". No receipt carries one today (section 7).

### 3.4 Pathways follow the RPM chain in one direction only

The chain is `A0 → Dn → Wn → Pn → outcome`. Per Correction 2 (section-retraction, not adjunction), meeting a prerequisite works in one direction only.

- A charge on `Dn` is admitted only if `A0` was charged at or before that time. A charge on `Wn` needs `Dn`. A charge on `Pn` needs `Wn`. Otherwise it is REFUSED with reason `RPM_ORDER`.
- A later charge on the prerequisite does **not** turn an earlier refusal into a charge. The refusal stays in the history.
- A charge on `Pn` does **not** back-fill `Wn` or `Dn`. Each cell is charged only by its own events.
- If a prerequisite later reads FADED, the cells after it keep their charges. Prerequisite results are cached when first met (Correction 2: do not assume reversibility).

### 3.5 One event, several universes

One receipt makes one event. That event lists every cell it touches, at most one per universe:

- U40 if it has Noetic + Domain;
- U28 if it has Drive + Domain;
- U22 if it has a pathway;
- G22x40 if it has pathway + Noetic + Domain;
- G28x40 if it has Drive + Domain + Noetic (and the cell is eligible).

## 4. Four states per cell, and the write history

The states are exactly the Lacunarity Machine's (README of `lacunarity_machine_v1`), plus one eligibility state:

| state | rule |
|---|---|
| COVERED | probed; the last deciding probes reach the floor (default floor: 3 RIGHT of the last 4 probes, as in c21) |
| NO_EVIDENCE | never probed |
| LACUNA | probed below the floor, and **never charged** at or before that probe |
| FADED | probed below the floor, and **charged at least once** at or before that probe |
| NOT_ELIGIBLE | the cell cannot be reached by any event under CR-1 (only in G28x40, section 2) |
| UNCOVERED_NO_WRITE_HISTORY | a miss in a universe that has no write history at all, so LACUNA and FADED cannot be told apart |

Extra flags, kept from the machine: `reached_floor_earlier` (it held, then slipped) and `covered_without_charge` (right without ever being taught: a chance hit).

**Write history.** One append-only ledger for all five universes. Each event carries `t` (an integer time), the source receipt's sha256, the rule id (CR-1.x), the coordinates (Noetic, Domain, Drive, pathway, where the Domain came from), the register set, and the cells touched. An event whose `t` is earlier than the last written `t` is refused, as in `ledger.py`. Readers are deterministic. Fractions are written as `{"exact": "a/b", "decimal4": "0.xxxx"}`. Floats are refused.

The symbol Λ is not used. In CAS v7.6 it means leakage. Concentration is always labelled "concentration (CV² = n·HHI − 1, exact)" and never called lacunarity.

## 5. How "22×40" and "28×40" become true statements

Today both phrases are **not licensed** as descriptions of HELM's brain.

- **"22×40" becomes true** when all three of these hold:
  1. G22x40 exists with its 880 frozen cells;
  2. at least one admitted CHARGE event carries a pathway **and** a Noetic **and** a Domain from a receipt or a declared adapter default;
  3. a reading reports the state of all 880 cells.

  The true statement then has this form: "Of the 880 pathway × state cells, *a* are COVERED, *b* FADED, *c* LACUNA, *d* NO_EVIDENCE." It is never "HELM is a 22×40 brain".
- **"28×40" becomes true** the same way, on G28x40. It must also say "of the 280 eligible cells (840 not eligible)".
- Until then the honest sentence is: "the grid exists; every cell is NO_EVIDENCE; 0 events carried both coordinates".

## 6. Marginal profiles only, never silently joined

- U40, U28 and U22 are each read on their own. Each has its own coverage, gap set and concentration.
- A grid cell is charged **only** by an event that carried both coordinates itself. A grid cell is **never** filled by combining U22 and U40, multiplying marginal coverages, or matching events by time.
- Every reading carries `joined_from_marginals: false` (a constant in the schema) and `events_with_all_coordinates`. If that count is 0, the grid reading is "NO_EVIDENCE everywhere". It is not "0% coverage".
- A report may show the marginals beside each other. It must not draw a product table from them.

## 7. What cannot be charged today (honest list)

1. **No operating point is computed.** Receipts carry no drive level, no stage (Rising / Peak / Waning / Absent) and no purpose / wisdom / power reading. So the Drive axis can only come from the pathway used, and no receipt names one.
2. **No registers in receipts.** No receipt says T, A, f or E. Every register set is empty (register-neutral, valid under v7.5). The voice writer (`helm_voice.py`, Fix F) picks a tone for its English sentence. That is the register of the **reply**, not of the brain's operation. It must **never** be used to tag a cell, because that would be a made-up charge.
3. **No pathway in receipts.** The c34 recipe brain (`HELM_R1_W1_20261015_v3\rb\brain.py`) answers with `label`, `gate` (G1..G4), `winner`, `yields`, `limiting_cell`. Its writer (`rb\writer.py`) records `admitted`, `reason` (ADMITTED / RECEIPT_FAILED / MEMORY_CHECK_REFUSED / UNPLACED), `faded_seeds`, `memory_check_ok`. There is no pathway field. So U22, U28 and both grids get **0 charges** from c34.
4. **No domain in receipts.** The c34 worlds are synthetic (keys k0..k3, labels L0..L3, 8 memory cells = 2 slots × 4 channels). They have no CAS Domain. Any U40 charge from c34 needs an adapter default. That is a declaration, not a reading.
5. **c34's cells are not CAS states.** Its 8 memory cells and 4 recipes are positions in a synthetic world. They do not map to `^n^D` states. Only the event **kind** (fit, teaching step, repair, refusal) carries CAS meaning under CR-1.
6. **First write vs repeat write is not split** in the c34 reading. The split needs the per-step records in the host file `R1_W1_HOST.json`.
7. Noetics `^0`, `^1`, `^2`, `^3`, `^4`, `^8`, `^9` have no charging event (section 3.1).

## 8. Worked example: c34 (HELM-R1 wave 1, verdict PASS, headline R1_BEATS_GB3)

Source: `Documents\Codex\2026-10-01\task-2\helm_operator_preparation\R1_W1_RESULT_20261016\R1_W1_READING.json` (sha256 `9b1dfdd88568012cabbcfa6d00e97c15dee07d445dfa5daff8be185975f4cf3a`), arm A1, Gate B, `marks.R1_HOLDS_GB.a1_rows_detail`, plus `marks.R1_BEATS_T_TB`. The numbers below are copied exactly.

| c34 field | value | CR-1 event | rule | U40 cell (adapter default O) | U28 / U22 / grids |
|---|---|---|---|---|---|
| `admitted` | 480 | 480 CHARGE (teaching steps) | CR-1.2 first time / CR-1.3 repeat | `O5` (first) and `O7` (repeat); split not in the reading | none: no pathway |
| `refused_receipt` | 30 | 30 REFUSED | CR-1.5 | logged against `O5`/`O7` | none |
| `refused_memory_check` | 0 | 0 | CR-1.5 | — | — |
| `unplaced` | 2 | 2 REFUSED (no target) | CR-1.5 | logged, no cell | none |
| `row2_stage2_revisions` | 4 | 4 CHARGE (recipe fit: requirement changed) | CR-1.1 | `O6` | none |
| `row0_repair_returned` / `row0_repair_total` | 4 / 4 | 4 CHARGE (repair) | CR-1.4 | `O6` | none |
| `row1_plain_right`, `row2_new_right` | 16, 15 | PROBE RIGHT | CR-1.7 | probes of the cells their items were taught in; the reading gives totals, not per-item cells | none |
| `row1_twin_undetermined` | 16 | PROBE UNDETERMINED | CR-1.7 | counted on its own line, not as wrong | none |
| `R1_BEATS_T_TB` SUM_A1 / SUM_T | "32" / "9", margin 4 | PROBE (limiting-reagent answers on held-out compositions) | CR-1.7 | probes of `O6` (what an outcome is made of) | none |

What a reader would print, honestly:

- **U40**: 3 of 40 cells have evidence (`O5`, `O6`, `O7`), **only under the declared adapter default O**. The other 37 cells: NO_EVIDENCE.
- **U28**: 28 of 28 NO_EVIDENCE. **U22**: 22 of 22 NO_EVIDENCE.
- **G22x40**: 0 events with all coordinates, so 880 of 880 NO_EVIDENCE. **G28x40**: 0 events, so 280 of 280 eligible NO_EVIDENCE, 840 NOT_ELIGIBLE.
- So, from c34, **"22×40" and "28×40" are still not true statements**. Making them true needs receipts that name the pathway, and ideally the domain, at the moment of each write.

What it would take (each step is new work, none is approved):

1. Add `domain` and `pathway` fields to the recipe brain's write receipt.
2. Add an optional `register` field, filled only by the brain's own operation. Never by the voice.
3. Add an adapter to `lacunarity_machine_v1/adapters/` for CR-1, following the frozen schema.
