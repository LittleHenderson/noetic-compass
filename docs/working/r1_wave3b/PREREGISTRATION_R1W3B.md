# PREREGISTRATION_R1W3B — HELM-R1 wave 3b: the roomier exam (English-64, Faces-64) for the four unreadable pairs

Written 2026-10-19 (Pacific) by the wave-3b builder session (Claude) on the owner's ruling. Frozen when sealed
(`HELM_R1_W3B_20261019/FROZEN_R1W3B.json`, sha256 `90d4468d2dd3df64f0b20bf2b71aa716ff515492daf80fe899e37709997e6de8`).
One scored attempt plus at most one plumbing retry. A FAIL on any row is a finding. **NOT LAUNCHED. No ledger hold
placed. No spend.**

Sealed package: `HELM_R1_W3B_20261019_SOURCE_R1W3B.zip`, sha256
`a4f82556bf0fc26de5635a7c81ec8f5053951d4c64a3906c8e5dd474e3814d26` (82,393 bytes, 27 members + the freeze);
`PACKAGE_FREEZE.json` sha256 `a6d9dbc78d3f720941c5a358be9a4d514617f8de226811c55938f807833dfbba`; resealed
byte-identical. Source cut: thread `claude/project-thread-pmbzd6` at `2c6cf95234c8fb10800d2e808198fe611b79e2b1`
(PR #359 merge, wave 3 scored). HELM's own code is NOT cut again: it is the wave-3 v3 package's `helm/`, by reference.

## 0. What the owner ordered, plainly

Owner ruling, verbatim (`Documents\Codex\2026-10-18\OWNER_APPROVALS_20261018.md`, 2026-10-19 morning block; file
sha256 at this reading `c1166b90...`): "roomier exam" so the 4 unreadable pairs can be read [yes, cheap]. The
coordinator's record of it: "build the English-side exams with enough room (English-64 / Faces-64) so the 4
CEILING_NOT_READABLE pairs can be read; cheap AWS run after a sign line."

The four pairs wave 3 (job c37, spec sheet 7.69) could not read:

| Pair | c37 exam | L_a | L_b | L_ab | E_sum | Room | Why not readable |
|---|---|---|---|---|---|---|---|
| CUBE_STORE x ENGLISH_IN | X2_E16 | 12 | 3 | 12 | 15 | 16 | 15 > 16 - 2 |
| ENGLISH_IN x TRIAD | X2_F16 | 8 | 8 | 8 | 16 | 12 | 16 > 12 - 2 |
| ENGLISH_IN x VOICE | X2_E16 / X2_F16 | 12 / 8 | 7 / 8 | 16 / 12 | 19 / 16 | 16 / 12 | both over |
| TRIAD x VOICE | X2_F16 | 8 | 8 | 12 | 16 | 12 | 16 > 12 - 2 |

## 1. Gate answer

HELM ability advanced: COOPERATION between parts, for the four pairs whose word wave 3 could not read. Before: four
`CEILING_NOT_READABLE` words (c37). After: one frozen word each (SYNERGY / ADDITIVE / INTERFERENCE, or again
CEILING_NOT_READABLE if there is still no room), on two fresh, larger, harder exams. Control that lacks the mechanism:
the same brain with one part of the pair off, and with both off, everything else equal. What it will not show:
anything outside synthetic worlds; any new word for a single part (the part words stay c37's).

## 2. Why "4 times the items" alone would not have helped (the arithmetic)

The pair rule (wave 3's, unchanged) reads a pair only if the two single losses fit inside FULL's score with a margin:
`E = L(a) + L(b) <= M(FULL) - margin`. Every quantity grows with the exam. If English-64 were simply four copies of
English-16's mix, ENGLISH_IN x VOICE would give E about 76 against M(FULL) about 64: still unreadable. The losses are
too large because almost every English-16 item needs BOTH the English reader and the voice. Room needs items that
survive each single part off. So wave 3b keeps wave 3's families but changes their counts and adds a difficulty
ladder whose harder rungs are items where the right reply is to ASK. Those survive one part off and are lost only when
both are off, so they also give the joint loss room to show.

## 3. The exams (frozen; `r1w3b/gen64.py COMPOSITION`)

**Families as before.** Every family item is built by the body of wave 3's own generator (r1w3/gen_live.py, sealed
in 152bca2a), factored into one function per family with the same random draws in the same order, using wave 3's
pools, recipes, units and follow-up questions imported from the sealed package. Test
`test_families_reproduce_wave3`: called in wave 3's order and counts, they give wave 3's `e16(seed)` / `f16(seed)`
items exactly (5 seeds each).

**The difficulty ladder** (every key from a written rule, never from running HELM):

| Rung | Meaning | Key |
|---|---|---|
| PLAIN | the family item exactly as wave 3 builds it | the family's |
| TWO_INGREDIENT | English: the least-stocked ingredient is NOT the one that runs out. Faces: wave 3's two-faces family, lexicon phrasings | ANSWER |
| UNKNOWN_INGREDIENT | the stock sentence also names one ingredient the brain does not know (honey, cinnamon, oats, rice, cocoa, vanilla, raisins, nutmeg), same turn as the question | ASK (reader rules 2 and 3) |
| UNIT_CHANGE | setup states the stock in the usual units; the turn gives one ingredient in another unit, with the question | ASK (reader rule 5) |
| FACE_STATED | Faces: the face in a phrasing the faces lexicon holds | ANSWER |
| FACE_IMPLIED | Faces: the face in a paraphrase, one with a cue word and one without, per family | ANSWER |

On Faces-64 the UNKNOWN_INGREDIENT and UNIT_CHANGE rungs keep the family's face (stated). English-64 states no face
(the triad has no pair there).

**English-64** (`helm.r1w3b.english64/1`): G1 PLAIN 4, G1 TWO_INGREDIENT 4, G1 UNKNOWN_INGREDIENT 8, G1 UNIT_CHANGE 8,
G2 8, G3 4, G4 8, G5 8, G6 8, G7 4. ANSWER 16, ASK 32, LEARN 8, READ 8.

**Faces-64** (`helm.r1w3b.faces64/1`): H1 and H2 each FACE_STATED 6, FACE_IMPLIED 2 (one PC, one PN), UNKNOWN_INGREDIENT
8, UNIT_CHANGE 8; H3 4, H4 4, H5 2, H6 TWO_INGREDIENT 4, H7 2. ANSWER 24, ASK 40.

## 4. Arms, units, seeds, text rule

4.1 **Arms** (`r1w3b/switches_w3b.py`; settings are wave 3's own `live_settings`): English-64: FULL, FULL_REPLAY,
-ENGLISH_IN, -VOICE, -CUBE_STORE, -ENGLISH_IN-VOICE, -ENGLISH_IN-CUBE_STORE (7). Faces-64: FULL, FULL_REPLAY,
-ENGLISH_IN, -TRIAD, -VOICE, -ENGLISH_IN-TRIAD, -ENGLISH_IN-VOICE, -TRIAD-VOICE (8). Nothing else.

4.2 **Reproduction units (instrument I3, "same brain")**: FULL on the spent X2 English-16 and Faces-16 files
(`205054b2...`, `69202c0b...`), run by wave 3's own `r1w3.live_w3` command exactly as c37 ran it. Every item's turn
statuses, values, limiting ingredient, writes, learned digest, score and plain flag must equal c37's FULL records
(`R1_W3_HOST.json` `e2bf6d4c...`). 17 host units in all (c37: 106).

4.3 **Text rule: A1 carried + T3b** (`r1w3b/text_rule_w3b.py`). Wave 3's overlap rule, with R1W3-A1's follow-up strip,
extended to the generator's other enumerated template turns: the 6 store questions, the 8 question forms (2 forms x
4 products) and the greeting "Hi again.". If an item has nothing left, its setup English and checked lines (its
stock, numbers included) are checked instead. Why: measured on the packaged strings and fixtures, 3 of the 6 store
questions are already forbidden, and all 6 once wave 3b's fixtures are added (5 of 8 question forms); with 8 store-read
items no seed could ever pass (test `test_text_rule_t3b`). This is the same trap A1 fixed, found by the builder before
any X3 seed exists. Forbidden set: wave 3's (packaged strings, faces lexicon, wave 3's fixtures) + wave 3b's fixtures +
X1's English-16 + X2's English-16 and Faces-16 (each pinned by sha256 in the checker).

4.4 **X3 seed rule** (`r1w3b/seed_rule_x3.py`, `x3_contract/SEED_RULE_X3.md`). Seed source = sha256 of the owner's
R1W3b line bytes. Bands shifted +20,000,000 from X2-v2's: E64 1,838,000,001 to 1,839,000,000 (k4); F64 1,840,000,001
to 1,841,000,000 (k1). Used table = X0's own table + every fresh range of all six earlier derivations (X0, X1, X2-v1
attempt 1, X2-v1, X2-v2 before its text step, X2-v2), each pinned by sha256. Gap 1,000,000; s <- s + 1 inside the
band; no free slot = STOP. Builder's check on a dummy line with the six real derivations: `overlap_check: PASS`, both
parts in band. The builder never sees X3: a separate custodian builds it on the laptop (0 USD) and the receiver's
check `r1w3b.check_x3_format` must print `all_pass: true` before the seal.

## 5. Frozen rows

**Instrument rows** (wave 3's, on wave 3b's path; any false: INSTRUMENT_ERROR): I1 data identity (pins given = host;
X3 files by hash; seal record = pins; receiver check all_pass; host format and text checks; X2 language files by hash;
wave-3, wave-2, wave-1 packages by freeze on host and at reader); I3 same brain as c37 (4.2); I4 parameter counts (0
learned for the triad and faces reader, every arm); I6 completeness (run record; wave 3b, wave 3 unit, wave 2 unit and
wave 1's 128 tests OK on the host; every unit exit 0; no deadline; every arm 64 records with setup OK; repro 16 + 16);
I7 laptop reading from the sealed package; I9 governance (approval names this zip and freeze; the sign line carries
`a4f82556`; the controller shipped this zip and the wave-3, wave-2, wave-1 zips; no reseal; supervisor PASS and found
`r1w3b_out/R1_W3B_HOST.json`); I10 X3 band rule (both parts seeded, in band, overlap PASS, used table = the six pinned
derivations, seed source = the owner's R1W3b line). Not on this path: I2, I5, I8 (no T, Gate B or Task B).

**Hard gates** (wave 3's numbering; any false: FAILURE): H1 receipts, English part, every arm; H8 the voice changes no
answer (English-64 by wave 2's projection, Faces-64 by wave 3's); H11 replay (FULL = FULL_REPLAY on both exams).
Not on this path: H2-H7, H9, H10, H12-H14, and H8's "triad at Peak is identity" (no -TRIAD arm on English-64).

**The pair rule** (wave 3's `pair_word_exam` and `pair_word`, imported verbatim from the sealed wave-3 reader). Metric
M = items RIGHT with a PLAIN reply, of 64. L(a) = M(FULL) - M(-a); E = L(a) + L(b); margin = 1/8 of 64 = 8.
**Readability, numerically: CEILING_NOT_READABLE if and only if E > M(FULL) - 8.** Otherwise SYNERGY if
L(ab) >= E + 8; INTERFERENCE if L(ab) <= E - 8; else ADDITIVE. ENGLISH_IN x VOICE runs on both exams: across exams
INTERFERENCE, then SYNERGY, then ADDITIVE, then CEILING (wave 3's order). A pair word is READ only when both parts were
EARNED_KEEP in c37's reading (`1cc7dba8...`): all four parts were. The reader also prints each pair's
`slack_to_ceiling` = (M(FULL) - 8) - E.

On the coordinator's wording "so it cannot be CEILING_NOT_READABLE unless FULL scores >= 62/64": no rule can promise
that, because the ceiling depends on the two single losses, not on FULL alone; and reading a pair whose single losses
overflow the room would turn a measuring limit into a fake INTERFERENCE word. So the rule is kept as wave 3 froze it
and stated numerically above, and the ROOM is built into the exam instead (section 2). On the builder's fixtures the
smallest slack is 8 (section 7). Flagged for the coordinator (deviation D-B2).

**Marks for FULL (PROPOSED, reported; a miss is a finding, never a gate):** English-64 RIGHT >= 56 of 64 with WRONG <= 2;
Faces-64 RIGHT >= 48 of 64 with WRONG <= 4.

**Verdict:** INSTRUMENT_ERROR if any instrument row is false; else FAILURE if any hard gate is false; else PASS. Words
licensed only with PASS and four read pair words.

## 6. Deviations from wave 3 (each a recorded decision)

- D-B1 the family COUNTS change (not the family code) and a ladder is added, so the pairs have room (section 2).
- D-B2 the readability rule is kept verbatim; the coordinator's "only at FULL >= 62/64" wording is not implemented
  (section 5).
- D-B3 text rule T3b extends A1 to the generator's other template turns (4.3).
- D-B4 X3 is laptop-only (no torch helper; no Gate B worlds).
- D-B5 the X2 language files are re-run (FULL only) as a reproduction instrument; the builder never opens them.
- D-B6 builder disclosure: the composition counts were set from the wave-3 16-item fixture behaviour per family (the
  builder's own fixtures, run under every needed arm), then confirmed once on the 64-item fixtures; nothing was changed
  after that run. The fixture run shows the likely words (section 7).

## 7. Builder dry run (fixtures only; facts, not claims) — `TEST_RECORD_R1W3B.md`

15 arm units through wave 2's dispatcher, from the sealed extract, 19.2 s; the reader ran end to end and said
INSTRUMENT_ERROR as designed (no X3, no repro, no approval); hard gates all held on the fixtures.

| Pair (fixture) | L_a | L_b | L_ab | E | Room | Slack | Fixture word |
|---|---|---|---|---|---|---|---|
| CUBE_STORE x ENGLISH_IN, E64 | 28 | 8 | 28 | 36 | 60 | 16 | INTERFERENCE |
| ENGLISH_IN x TRIAD, F64 | 20 | 24 | 20 | 44 | 60 | 8 | INTERFERENCE |
| ENGLISH_IN x VOICE, E64 / F64 | 28 / 20 | 16 / 20 | 60 / 60 | 44 / 40 | 60 / 60 | 8 / 12 | SYNERGY / SYNERGY |
| TRIAD x VOICE, F64 | 24 | 20 | 28 | 44 | 60 | 8 | INTERFERENCE |

FULL on the fixtures: English-64 60 RIGHT / 0 WRONG / 4 UNDETERMINED (4 witness items); Faces-64 60 / 2 / 2 (the two
implied-face paraphrases without a cue word are missed; the two with a cue word ask). Both marks met on the fixtures.

## 8. Builder predictions (before the run; not used by the reader)

All four pairs readable. ENGLISH_IN x VOICE likely SYNERGY: with both off, the old adapter's reply to a sentence it did
not read is not plain, while either part alone keeps it plain (fixture PLAIN: 64 with either off, 4 and 0 with both).
The other three likely INTERFERENCE: the two parts guard the same items, so losing both costs no more than one.

## 9. Cost and limits (PROPOSED) — `RUN_LIMITS_R1W3B.json`

One `m6i.xlarge`, 2-CPU slice, the c21 image, us-west-2; 17 host units (c37: 106); runner deadline 2,400 s; no torch
helper. Expected about 6-8 minutes of host, about 0.02-0.03 USD at list (c37 cost 0.08 for three jobs, 0.04 for its
scored host), about 0.05-0.06 at the conservative rate; at most about 0.35 per attempt; worst case about 0.70 with the
one plumbing retry. **Cap 1 USD, PROPOSED.** Ledger read 2026-10-19: 88.81 of 200.00 unreserved. No hold placed.

## 10. What wave 3b may and may not license

May (only with PASS): "On synthetic worlds only, the same licensed recipe brain and live English path as wave 3 (c37)
were scored on two roomier exams, English-64 and Faces-64, with the two parts of each of four pairs switched off alone
and together and everything else held equal; each read pair's word says whether losing both parts cost more than the
two losses added (SYNERGY), about the same (ADDITIVE) or less (INTERFERENCE), or that the exam still had no room to
tell (CEILING_NOT_READABLE)."

Never: anything outside synthetic worlds; that the voice sounds natural to people; that real reagents carry a triad;
that the faces reader understands English beyond its lexicon; any word for a single part; any pair other than the
four; statistical superiority (one run); operation in real kitchens or on real data. c37's 16 pair words stay on record
unchanged; wave 3b adds words for four of them on new exams.
