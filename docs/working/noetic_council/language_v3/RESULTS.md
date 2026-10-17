# LM-T1 results (run LM_T1_MSI_ONCE, 2026-10-14 about 9:24 PM Pacific)

What this tested: does a small, strict part of English (CCE v0.1) carry CAS content out to English and back with
nothing lost? The only acceptance test is the round trip: render the content to English, parse it back, and the
content must be identical. This is a FORM test. It makes **no meaning claim** and no claim about Noetic labels in
free English. Claim ceiling for the translator: **ENGINEERED-NOT-VALIDATED**.

Run: once on MSI under `supervisor.ps1`. Sign line
`APPROVE lm_t1, source 0db2fcdb, LOCAL_CPU_ONCE on MSI, 300 s cap, no spend.` (supplied by the builder on the owner's
behalf, citing the owner's words; see `runs/LM_T1_MSI_ONCE/OWNER_APPROVAL_EVIDENCE.md`). Wall 14.16 s, worker CPU
13.36 s, peak working set 46,493,696 bytes (about 44 MiB), sockets blocked, spend 0. Unit tests 26 of 26 passed
inside the worker before scoring.

Program reading (`runs/LM_T1_MSI_ONCE/READING.json`): **LM-T1 core = PASS** (all hard marks). **SDG mark met.**

| | Mark | Exact result |
|---|---|---|
| 🟩 | M1 round trip, fixed wording, SDG recipe seeds | **576 of 576** (LOOKUP table also 576 of 576: this mark alone cannot tell a grammar from a table) |
| 🟩 | M2 wording draws (576 x 8 x seeds 11, 29, 47 = 13,824 draws) | 0 sentences said that fail read-back; 576 of 576 sayable; COIN-WORDING read-back equal **0 of 13,824**; distinct admitted wordings per content min 8 / median 22 / max 25 (LOOKUP: 1) |
| 🟩 | M3 hand set (64, written by an independent sub-agent that never saw the parser) | **64 of 64** (48 positives, 5 trap-parse, 11 trap-refuse with the named code). LOOKUP: 19 of 64; ALIAS-wording positives CCE 18 of 18, LOOKUP 1 of 18 |
| 🟩 | M4 SDG English, ALIAS-WIDE, 439 headline rows | **MATCH 233 of 439** (53.1%) vs PROPOSED mark 176 and bridge v2 baseline 118. MISMATCH 9, UNPARSEABLE 197. All 118 bridge-v2 matches still match; 115 new. Register and drive also agree in 174 of the 233. Strict CCE parses 0; LOOKUP 0 |
| 🟩 | M5 negative control 00459 | **MISMATCH** (English 2 -> ^8^O, CAS 2 -> ^9^O) |
| ⬜ | M5 the six suspect rows | 00229, 00193, 00360, 00353, 00320, 00528 all **MISMATCH**: 0 flags. 00026 (reported only): MISMATCH |
| 🟩 | M5b label-shuffled control (439 deranged pairs, seed 11) | **0 MATCH** |
| 🟩 | M6 coverage ledger (Lacunarity Machine) | 2,600 cells: **COVERED 2,600**, NO_EVIDENCE 0, LACUNA 0, FADED 0; covered_without_charge 0 |
| 🟩 | M7 CAS compiler cross-check | recipes 576 of 576 agree; frame terms 2,283 of 2,283 agree; 1 register-set term is unit-test only |

Side universes (reported, never joined): U-TURN COVERED 4, **LACUNA 2** (REFUSE, CLOSE: CCE v0.1 has no form for
them). U-DRIVE COVERED 8 of 8. U-RECIPE COVERED 7 of 7. U-CATEGORY COVERED 14, **LACUNA 7** (general `∘`
composition, CoverOf, PartitionOf, union, intersection, difference, let).

## Disclosures

- The coverage probes are built by the same builder who wrote the grammar, one probe per cell. 2,600 COVERED says
  "every cell has a rule that round-trips its own probe". It does not say the cells are well chosen.
- M3 hit 64 of 64 on the first run (prediction was 56-64). The writer read only FUNDAMENTALS.md, MAP.md and
  `GRAMMAR_CCE_v0_1.md`. The hand set was hashed on receipt (`handset/HAND_SET_FREEZE.json`) and was not read
  by the builder before scoring. Note: `cce.py` was on disk during the last seconds of the writer's run; the
  writer reports it opened no .py file.
- M4 counts form agreement only ("the numbers bind to the same states by these rules"), not good descriptions.
  The 9 new MISMATCH rows (00562, 00335, 00066, 00427, 00139, 00499, 00443, 00099, 00555) were not read.
- The ALIAS-WIDE lexicon adds a closed inflection table and a "verb frame first" rule over canon phrases. No new
  alias word. The builder had seen two SDG English rows (00459, 00229), both in the excluded 42.
- Brief conflict: the brief said "embedding to depth 5"; owner default Q9 says depth at most 2. Frozen: 2. The
  recursion is unit-tested at depth 5 with the limit raised inside the test only.
- Not built: the gap-filling loop (GAP_FILLING.md, level L3). No grammar rule was learned.

Files: `FROZEN.json`, `GRAMMAR_CCE_v0_1.md`, `ALIAS_WIDE_LEXICON_v0_1.json`, `cce.py`, `aliaswide.py`,
`coverage.py`, `scoring.py`, `test_lm_t1.py`, `worker.py`, `supervisor.ps1`, `handset/`, `runs/LM_T1_MSI_ONCE/`.
