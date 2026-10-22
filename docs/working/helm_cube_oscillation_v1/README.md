# HELM cube oscillation v1 — facts become cubes at their Atlas node only after the CTT and the brain side agree; whole memories fade step by step into CAS (design packet, 2026-10-21 PDT)

Status: **BUILD v2 DONE behind `HELM_CUBE_OSC` (default OFF), unit-tested; NOTHING TRAINED, NOTHING RUN, NOTHING SCORED, NOTHING LICENSED. 0 USD.** Spec §7.125 (follow-up 2: `BUILD_V2_RECORD_20261021.md`, incl. the measured finding that fading costs space on short lines; follow-up 3: REWORKED onto the existing Cube Node Schema and cube store, A-TEACH2-4).

**Plainly.** TEACH-1 (§7.121) showed that HELM's memory quotes whole sentences and that the taught facts never became
cubes. This packet designs the owner's answer. A fact is kept as a cube only when two different readers agree: the CTT
proposes a reading, and the brain side checks it and says it back, for up to 3 rounds. The cube lives at the thing's
Atlas node. The person's words stay beside it. Old plain-English memories then fade in steps, every few turns, from
the whole line to a CAS capsule to a small CAS record, which saves space while keeping a way back. The Eye only reports
on the rounds in the first test, because its acting is not licensed. The exam, TEACH-2, must beat today's quote
memory, a plain lookup table, and one reader alone.

| File | What |
|---|---|
| `DESIGN_CUBE_OSCILLATION_V1.md` | the owner's words and the five requirements read from them; the round loop and keep rule; cubes at the Atlas endpoint; the fading ladder S0 → S1 → S2; the cheap rivals; build, training and exam order with prices |
| `PREREGISTRATION_TEACH2.precode.md` | the exam: 9 arms, 16 worlds with trap lines, scoring with a current-value rule, I16–I18, 5 new hard gates, marks C1–C4 and SPACE, the words, the forecast |
| `PREREGISTRATION_TEACH2.precode.sha256` | sha256 **`f7b6183bba5f8a1a241e3c64c8930f6a2c6df06fbe8c5845c0207f6d2a84c855`** (9,873 bytes, LF); not edited after this, amendments appended and hashed apart |
| `OPEN_QUESTIONS.md` | the eight owner decisions, each with a recommendation and its cost; **answered 2026-10-21** |
| `AMENDMENT_A_TEACH2_1.md` (+ `.sha256` `fb2f104d…`) | the owner's rulings, the reported shadow of rounds 4–6, the exam line `CUBE EXAM at 1 USD` |

**Money:** this packet 0 USD. Later, two separate owner lines are proposed: `CUBE TRAIN at 3 USD` (CTT retraining on
the new kind of fact, expected about 2 USD) and `CUBE EXAM at 1 USD` (one CPU host, expected under 0.20 USD).

**Claim states:** every part keeps its status. CTT `ENGINEERED-NOT-VALIDATED`; memory compaction
`ENGINEERED-NOT-VALIDATED` (TEACH-1 `INCONCLUSIVE`); the Eye's acting `NOT LICENSED`; no RPA-crossing claim; everything
new `PROPOSED`.

**2026-10-21, follow-up 4:** size limit (53,370 B) + widening batches + AWS cloud tier for the oldest originals (A-TEACH2-5, A-TEACH2-6; `BUILD_V2_RECORD_20261021.md` §7; live smoke `CLOUD_SMOKE_20261021.json`). Measured negative: memory does not stay under the limit.

**2026-10-22, follow-up 5:** the Eye runs a lean capsule (A-TEACH2-7; `BUILD_V2_RECORD_20261021.md` §8; `LEAN_BYTES_20261022.json`): one capsule 812 → 281 bytes; under the limit at 200 lines and at 53,370 for 2,000 lines; still over at 600 lines.

**2026-10-22, follow-up 6:** the Eye moves old capsules off working memory with a clue index (A-TEACH2-8; `BUILD_V2_RECORD_20261021.md` §9; `OFFLOAD_BYTES_20261022.json`): 300 short lines at 3,000 now under; 600 lines at 4,000 still over (the index grows).

**2026-10-22, follow-up 7:** the Eye folds old index rows, row upon row (A-TEACH2-9; `BUILD_V2_RECORD_20261021.md` §10; `FOLD_BYTES_20261022.json`): 8,000 lines stay under 53,370; a 4,000 limit is below the two-level floor.

**2026-10-22, follow-up 8:** clue words from every line of a batch (A-TEACH2-10; `BUILD_V2_RECORD_20261021.md` §11; `EVERYLINE_BYTES_20261022.json`): at 53,370 for 8,000 lines, reach 1 → 30 of 30, memory under; small limits now go over.

**2026-10-22, follow-up 9:** the deep search reads the cloud's fold records when online (A-TEACH2-11; `BUILD_V2_RECORD_20261021.md` §12; `CLOUDSEARCH_REACH_20261022.json`): reach 1 → 30 of 30; estimated ~10 s per question on the real bucket.

**2026-10-22, follow-up 10:** the cloud search fetches all fold records in one call (A-TEACH2-12; `BUILD_V2_RECORD_20261021.md` §13; live `CLOUD_BATCH_TIMING_20261022.json`): 4.16 → 3.54 s per question on the real bucket.

**2026-10-22, follow-up 11:** remember a 'cloud reachable' yes for 60 s (A-TEACH2-13; `BUILD_V2_RECORD_20261021.md` §14; live `CLOUD_REACH_TIMING_20261022.json`): 3.46 → 2.66 s per cloud question.

**2026-10-22, follow-up 12:** a direct cloud client (A-TEACH2-14; `BUILD_V2_RECORD_20261021.md` §15; live `CLOUD_DIRECT_TIMING_20261022.json`): 2.65 → 0.21 s per cloud question; 77.6 → 4.7 s to build the test chat.
