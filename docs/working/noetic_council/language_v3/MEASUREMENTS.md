# MEASUREMENTS — every headline number, before and after

Two raw files sit beside this one: `MEASURE_BEFORE.json` (the base, copied into this folder and measured before
any edit) and `MEASURE_AFTER.json` (the same code after the two additions). Both were produced by

    C:\Python314\python.exe -X utf8 -B measure_marks.py

from this folder, with the `PYTHONPATH` recorded in `PROVENANCE.md`, on the same machine, a few minutes apart.

`measure_marks.py` is not a run. It has no owner permit, blocks no sockets and writes nothing to `runs/`. It calls
the same scoring functions `worker.py` calls, in the same order, and prints what they return. `RESULTS.md` remains
the frozen record of the 2026-10-14 run and was not edited.

## The numbers that prove the work

| what | before | after |
|---|---|---|
| **M1** round trip, 576 SDG recipe seeds | **576 of 576** | **576 of 576** |
| **M3** hand set, independently written | **64 of 64** | **64 of 64** |
| **M4** free English read correctly, ALIAS-WIDE | **233 of 439** | **233 of 439** |
| **M6** coverage ledger | **2,600 COVERED** | **2,600 COVERED** |
| **M6** `covered_without_charge` | **0** | **0** |
| tests | **26**, **11**, **5** | **26**, **11**, **5**, and **26** new |
| **U-TURN** ledger | COVERED 4, **LACUNA 2** | **COVERED 6, LACUNA 0** |
| LM-T1 core reading | PASS | PASS |

Nothing went down. One number went up, and only one: U-TURN, from 4 covered with 2 lacunae to 6 covered with
none. That is the two turn forms.

The test counts read `Ran 26 tests ... OK`, `Ran 11 tests ... OK`, `Ran 5 tests ... OK` and, for the new suite,
`Ran 26 tests ... OK`. The three base suites are byte-identical files; twenty-six new tests were added in
`test_lm_t1v3.py` and no existing test was touched.

## Every mark, on both sides

| mark | before | after |
|---|---|---|
| M1 recipes round-tripping | 576 of 576 | 576 of 576 |
| M2 sentences said that fail read-back | 0 | 0 |
| M2 contents sayable | 576 | 576 |
| M2 COIN wording read-back equal | 0 of 13,824 | 0 of 13,824 |
| M2 distinct admitted wordings, min / median / max | 8 / 22 / 25 | 8 / 22 / 25 |
| M3 hand set | 64 of 64 | 64 of 64 |
| M3 LOOKUP baseline | 19 | 19 |
| M3 ALIAS-wording positives | 18 of 18 | 18 of 18 |
| M4 MATCH of 439 headline rows | 233 | 233 |
| M4 MISMATCH | 9 | 9 |
| M4 UNPARSEABLE_ENGLISH | 197 | 197 |
| M4 bridge v2 baseline on the same rows | 118 | 118 |
| M4 strict CCE parses equal | 0 | 0 |
| M4 register and drive agree among MATCH | 174 | 174 |
| M5 negative control 00459 is MISMATCH | true | true |
| M5 suspect six matching (flags) | 0 | 0 |
| M5b label-shuffled control | 0 MATCH | 0 MATCH |
| M6 cells in exactly one state | 2,600 of 2,600 | 2,600 of 2,600 |
| M6 COVERED | 2,600 | 2,600 |
| M6 `covered_without_charge` | 0 | 0 |
| M6 COVERED cells with a receipt id | 2,600 | 2,600 |
| M7 recipes agreeing with the CAS compiler | 576 of 576 | 576 of 576 |
| M7 frame terms agreeing | 2,283 of 2,283 | 2,283 of 2,283 |
| M7 register-set term (unit test only) | 1 | 1 |
| U-TURN COVERED / LACUNA | 4 / 2 | **6 / 0** |
| U-DRIVE COVERED / LACUNA | 8 / 0 | 8 / 0 |
| U-RECIPE COVERED / LACUNA | 7 / 0 | 7 / 0 |
| U-CATEGORY COVERED / LACUNA | 14 / 7 | 14 / 7 |
| hand set sha256 matches its freeze | true | true |
| LM-T1 core | PASS | PASS |
| failed hard marks | none | none |

U-CATEGORY keeps its own seven declared lacunae (general `∘` composition, `CoverOf`, `PartitionOf`, union,
intersection, difference, `let`). They did not move, and they were not papered over.

## What the two additions prove, in their own words

**The `1/3` round trip.** A recipe whose coefficient is `1/3` renders to
`To make Ω_t, use 1/3 of Below/Effect, operational.` and parses back to a coefficient whose exact value is `1/3`,
with the content identical after normalization. It is written `1/3` every time, including across twelve seeded
wording draws, and never as digits after a point. The same holds in the other number slots:
`There is 1/3 of Ω_flour.` for a stock amount and
`"the speech" resonates with me to degree 1/3, evaluative.` for a degree.

**A fraction with no exact decimal is refused, not decimalised.** Asking for the decimal form of `1/3`, `3/7`,
`22/7`, `1/6` or `5/9` raises `Refusal` with the code `LOSSY_CONVERSION_REFUSED`. Each keeps its `p/q` text.

**`1/4` and `0.25` are one quantity.** Both parse, both are the same content after normalization, and the
canonical text of either is `0.25`. `2/8` is the same again. `half`, `0.5` and `1/2` are also one content, so the
base's number word and the new fraction form meet exactly.

**REFUSE and CLOSE each have their own sentence.** `I will not do that: boundary violation.` parses to
`turn=REFUSE` with `reason="boundary violation"`; `That closes the turn.` parses to `turn=CLOSE`; `That closes
Ω_tea.` parses to `turn=CLOSE` with `topic="Ω_tea"`. All three round-trip, both accept the `I checked:` and
`You said:` evidence prefixes, and all six turn types render as six different sentences that each read back as
themselves. `OPEN`, `MIRROR`, `EMPATHIZE`, `PLAN` and `REPAIR` still have no form and still raise.

## One place where the instruction and the reference implementation disagree

The task said a fraction "whose denominator is not a power of two" must never be silently turned into a decimal.
Taken literally that would refuse to write `1/5` as `0.2`, while the base already accepts `0.2` written as a
decimal — so the same quantity would be legal one way and refused the other, and the round trip would break.

The reference implementation at `language_v2/numbers.py` uses a wider test: a decimal exists exactly when the
reduced denominator is `2^a · 5^b` and nothing else. That is the rule implemented here, and it makes `1/3` refused
(`LOSSY_CONVERSION_REFUSED`) exactly as the task requires while keeping `0.25`, `0.2` and `1/4` consistent one
decimal and one fraction at a time. The test the task asked for — a non-dyadic fraction is refused rather than
decimalised — passes under either reading, because `1/3` is both non-dyadic and non-terminating. The difference
shows only on values such as `1/5`, and there the wider rule is the one that keeps one quantity as one content.
