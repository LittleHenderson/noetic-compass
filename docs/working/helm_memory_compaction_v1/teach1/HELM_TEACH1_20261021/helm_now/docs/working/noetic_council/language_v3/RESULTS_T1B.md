# LM-T1b results: nested Noetics and set meta-logic (run LM_T1B_MSI_ONCE, 2026-10-14 about 9:38 PM Pacific)

Why: the owner's addition (verbatim) "oh shit i almost for got about Noetic Fractals nested noetics, as well as
meta-logic CAS they both are saved locally in various books and files". LM-T1 was already frozen and scored, so this
is a separate test with its own freeze (`FROZEN_T1B.json`). Grammar: CCE v0.1b = v0.1 (unchanged `cce.py`) plus
`GRAMMAR_CCE_v0_1b_ADDENDUM.md` (`cce_v01b.py`).

**Compiler used:** the newest one, read-only:
`C:\Users\wakil\Documents\Codex\2026-10-08\task-4\cas-online\dist\compiler\api\notation\compiler.py`, sha256
`464fd4adfae90a35ba54aa794829da1fe713b9b9cccd68b630ecccfdfbca2f56` (6,415 lines, with the `cas.nesting/0.2` block).
CCE follows its syntax: `Φ⟨8:8:9⟩` and `∘` rings (first written = innermost, last = governing), typed sets,
`∈ ∉ ⊂ ⊆ ⊃ ⊇`, `∪ ∩ ∖`, Pullback, Product, CoverOf, PartitionOf, `|X| = n`, `let`. No dotted X.Y.Z form is emitted.

Run: sign line `APPROVE lm_t1b, source db2d4f40, LOCAL_CPU_ONCE on MSI, 300 s cap, no spend.` Wall 2.66 s, peak
48,087,040 bytes (about 46 MiB), sockets blocked, spend 0. Unit tests 37 of 37 passed before scoring.

Program reading (`runs/LM_T1B_MSI_ONCE/READING.json`): **LM-T1b core = PASS.**

| | Mark | Exact result |
|---|---|---|
| 🟩 | B1 nested Noetics, depth 1-5 x 10 Noetics (50 cells, 2 probes each) | **50 of 50 COVERED**; round trip 100 of 100; compiler sequence check 100 of 100 |
| 🟩 | B2 meta-logic, 15 operators x 8 set kinds | 120 cells, all 120 accepted by the compiler; **120 of 120 COVERED** |
| 🟩 | B3 16 added hand-set items (same independent writer, frozen on receipt) | **16 of 16**: nested 8 of 8, meta-logic 8 of 8 (includes the depth-6 refusal and the unknown-set refusal) |
| 🟩 | B4 compiler identity (CAS of the read-back content compiles to the same result) | 286 of 286 parts |
| 🟩 | B5 no damage to LM-T1 inputs | recipes 576 of 576; LM-T1 hand set 64 of 64 |
| 🟨 | B6 held-out book examples (`Programming_in_CAS_Corrected_Examples_2026-10-11.txt`, 67 cases) | **52 of 60** accepted cases exact (state/expression 30, recipe 10, meta-logic 6, nested 6). 8 FORM gaps: 4 bare set literals as a whole statement, 1 emergent result `(… ) = …`, 1 `RPM(...)`, 1 set-function call as a statement, 1 set holding a state in a non-set slot. 7 rejected cases: the compiler rejects all 7, so no content exists to say |
| 🟩 | B7 recipe grammar, new compiler vs bridge v2 on 576 seeds | **0 disagreements** |

Disclosures: section D of the addendum (CAS expressions) was written after the hand-set writer finished, so the hand
set does not exercise it. The builder saw the first 8 example cases while checking the file format. B6 compares the
compiler's result with display labels removed (`name`, `message`): `NoeticCluster{…}` and `NoeticSet{…}` are the
same set to the compiler, and CCE does not keep the constructor spelling. Truth of a meta statement is the
compiler's job; CCE carries FORM only, and "I cannot tell" must come from the dialogue layer (the compilers are
two-valued). The meaning of nesting (book open questions N1-N13) is not settled by CCE.
