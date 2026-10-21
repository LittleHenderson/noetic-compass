# PREREGISTRATION_MEMORY_COMPACTION_V1 — TEACH-1: teach HELM a new subject by conversation, compact its memory into CAS capsules with clues, refresh and strengthen, against the cheap ways of forgetting (pre-code, 2026-10-21 PDT)

Status: DESIGN, WRITTEN BEFORE ANY CODE. 0 USD. Owner's words of 2026-10-21 09:42 and 09:50 PDT are statements of intent (quoted in full in `DESIGN_MEMORY_COMPACTION_V1.md` §1); they are not an approval and not a launch order.
Nothing here is a result. Every number below is frozen now; the frozen reader applies them; no one re-reads them after the data exists.
This file is hashed (sha256 in `PREREGISTRATION_MEMORY_COMPACTION_V1.precode.sha256` and `README.md`); the final preregistration must carry it byte-identical at its top, with dated amendments appended below, never edited into it.

## 0. What the owner said, plainly

Teach HELM a new subject through ordinary question-and-answer until it understands, sounding natural. As space fills, compact memories into CAS with clues to their subject. Let HELM ask "refresh my memory" questions, check that the rebuilt memory fits the rest of its context, and if so strengthen it for better recall. Use the Eye, correctly applied. Use the CTT, the CAS SDG and the CAS compiler, which exist, and work with the cubes and the recipe coefficients. And (the owner's question the same morning) the RPAs, the Atlas, are involved too.

## 1. Gate answer (one sentence)

"When HELM is taught a subject it has never seen, through natural question-and-answer written by AI models, and its working memory is then squeezed so that it must compact, does HELM with CAS capsules (an expression that compiles, clues copied from the talk, pointers to cubes and coefficients, a breadcrumb and a receipt) plus the fetch-first refresh loop, the five-part fit check and append-only strengthening recall more of what it was taught than dropping the oldest turns, than a plain-English summary with the same clues, and than asking at random, while losing at most two answers against never forgetting, without stating one fact it was not taught and without presenting one rebuilt memory as exact?"

## 2. What is under test

- **HELM cut:** `helm_now/`, the HELM files of the thread branch at a head that carries the memory-compaction build v1 (DESIGN §8 step 2) merged with HELM's suites OK; the package carries its own copy by `git show`; the host runs that copy only. The exact commit is written in the final preregistration as an amendment, never chosen after the exam is drawn.
- **The switch:** `HELM_MEMORY_COMPACT` (new, default OFF). OFF = today's `helm_memory.py` byte-for-byte behaviour (FIFO drop at `max_turns`). ON = capsules, crumbs, receipts, refresh loop, fit check, strengthening, Atlas filing (DESIGN §3–§6).
- **The chat:** `helm_chat.HELMConversationalSession.handle_turn`, driven line by line as wave 7 did; stdout captured; `exit` / `quit` / commands never sent.
- **The brain:** the canonical wide brain, untouched; `helm_brain_canonical.py` and `helm_brain_wide.py` byte-identical to their scored bases.
- **The compiler of record:** the repo copy of `api/notation/compiler.py` on the cut, its sha256 written in the package; the site copy is NOT used in v1 (OPEN_QUESTIONS Q5).
- **The capsule writer in v1:** the hand-written CCE skin of spec §7.31. The CTT is NOT in v1 (Q3). A later v2 adds the CTT compaction head under its own amendment and its own owner line.
- **The Eye:** REPORT-ONLY. A plain scheduled routine does the housekeeping; the Eye's would-act log is compared to it (DESIGN §5). Eye acting is not tested here.
- **The COLD tier:** a local folder standing in for the cloud (as M1 did). No cloud action.
- **Reused unchanged by import from sealed neighbours:** wave 7 v6 zip `387577de…` (chat harness, recorder, units, custody and seed helpers, the host suite rule A-R1W7-6); the M1 run's reader functions for the EXACT / RECONSTRUCTED / UNKNOWN labels (`Documents\Codex\2026-10-15\m1_run\`), with H8 kept word for word.

## 3. Arms (one switch set per arm)

| Arm | What | Why |
|---|---|---|
| **COMPACT_ON** | `HELM_MEMORY_COMPACT` ON: capsules + fetch-first refresh + fit F1–F5 + strengthen + Atlas filing; turn budget B (§4.4) | **the arm under test** |
| VERBATIM_ONLY | no budget (turn budget 10,000); nothing compacted | the ceiling: what never forgetting recalls |
| FIFO_DROP | switch OFF; budget B; oldest turn dropped as today | the floor: what HELM does today |
| **SUMMARY_TEXT** | budget B; when a turn leaves the budget it is replaced by a rule-written plain-English summary (the same frozen template set, the same clues, the same breadcrumb and receipt) with **no CAS expression, no compile, no round trip, no F1–F4**; refresh = fetch-first, then ask on a clue match the same way | **the mechanism-free baseline: a CAS capsule earns nothing unless it beats a text note with the same clues** |
| NO_REFRESH | COMPACT_ON but the loop never asks (steps 4.1.4–4.1.5 disabled; fetch-first stays) | what asking adds |
| RANDOM_REFRESH | COMPACT_ON, but the refresh questions are asked about items drawn at random (seeded) instead of the clue-matched item; the same number of questions as COMPACT_ON asked in that world | the control for "asking anything helps" |
| REPLAY | COMPACT_ON again, fresh process, same seeds | HG-REPLAY |

All arms run on every world. Arms differ only in the switch set; the HELM files are the same bytes.

## 4. The exams (held by a separate custodian; the builder sees hashes and counts only)

### 4.1 Worlds (SDG-generated, keyed)
- A **world** is one small subject with a key: a made-up family's beekeeping year, or a made-up town's bus lines (the generator picks per world at the WORLD seed; two subject templates, both frozen in the package). Each world holds **24 facts** (names, places, counts, months, one-step relations), **4 of which are marked unknown-to-the-person** ("I don't remember how many hives were at the river site").
- Subject words are drawn from a frozen list that is disjoint by exact match from every ingredient, recipe and product name the brain's tables hold, from every cube core name in the shipped store, and from wave 7's small-talk sentences.
- **Count:** 16 worlds at the WORLD seed band. Floor 16; fewer → `I14` false.

### 4.2 Teaching turns (`LLM_WRITTEN`, per the talk packet amendment A-TALK-1 rule)
- For each world, **32 teaching turns** (a mix of the person stating a fact, HELM asking back, the person answering, small talk between): written by at least three AI model families, the writer named per turn, pool rules as CTT-2R; keyed by a different family; second-keyed by a third; disagreeing turns `UNDETERMINED`. The owner reviews and never writes. Never pasted into HELM's training (there is none in v1) and never on the repo or the hub.
- Floors: 32 turns per world; at least 20 of them carry a keyed fact; at least 4 are small talk; at least 2 are corrections (`FIX`). Any floor missed → `I14` false.

### 4.3 Quizzes (keyed, 16 questions each, drawn at the QUIZ seed from the world's facts)
- **Q-TAUGHT**: right after teaching, budget not yet binding (asked inside the budget window). 16 questions: 12 on taught facts, 2 on the unknown-to-the-person facts (key: honest unknown), 2 on facts never taught (key: honest unknown).
- **Q-SQUEEZED**: after the squeeze (§4.4). The same 16 questions in a fresh order.
- **Q-REFRESHED**: after every refresh question COMPACT_ON asked has been answered by the scripted person (§4.5). The same 16 questions in a fresh order.
- An answer is RIGHT when it equals the key's value (exact string after the house normalisation: case, whitespace, the voice's number forms) and carries no `success` marker where the key says unknown; WRONG when it states a value that differs from the key or states a value where the key says unknown; ASK when HELM asks instead; UNKNOWN_SAID when it carries one of the voice's `nodata` / `never` markers where the key says unknown (counts RIGHT for those items).

### 4.4 The squeeze
- Turn budget **B = 12** turns in working memory (today's default is 50). Set before teaching in the budgeted arms, so compaction happens during teaching, as it would in life.
- Byte budget: not used in v1 (Q6).

### 4.5 The scripted person's refresh answers
- When HELM asks a refresh or confirming question, the scripted person answers from the key: the right value with probability **0.75**, "I don't remember" with probability **0.25** (seeded at the PERSON seed); never a wrong value in v1 (a wrong-answer stratum is Q9).
- Caps as DESIGN §4.1: at most 2 refresh questions per thread, 1 per item.

### 4.6 Counts and vacuity (`I14`)
Worlds 16; teaching turns 32 per world with the floors of §4.2; three quizzes of 16 per world per arm; at least **8 compactions** per budgeted arm per world (else the squeeze did not bite → `I14` false); COMPACT_ON asked at least **1** refresh question in at least **8** of 16 worlds (else the refresh loop was `NOT_EXERCISED` and the REFRESH marks print `NOT_EXERCISED`; the word is then `INCONCLUSIVE` by rule 1).

## 5. Scoring (per world, per arm; frozen functions in the package)
- `RIGHT_T`, `WRONG_T`, `ASK_T`, `UNK_T` on Q-TAUGHT; the same with `_S` on Q-SQUEEZED and `_R` on Q-REFRESHED. Each out of 16.
- `LABEL_OK`: of the answers served from memory, the count whose label (`EXACT` / `RECONSTRUCTED` / `UNKNOWN`) matches what the reader derives from the store (digest-checked original present → `EXACT` is the only allowed label; absent or digest-failed → `RECONSTRUCTED` or `UNKNOWN` only).
- `COMPACTIONS`, `RECEIPTS`, `CRUMBS_OK` (crumb fetch + digest check succeeds), `CAPSULES_COMPILE`, `CAPSULES_ROUNDTRIP`.
- `REFRESH_ASKED`, `REFRESH_CLUE_QUOTED` (the question contains at least one clue verbatim), `REFRESH_CONFIRMED`, `STRENGTHENED` (items whose mass rose with a receipt), `STRENGTHENED_STAYED` (strengthened items still in working memory at Q-REFRESHED).
- `ATLAS_FILED` (capsules under the thread's anchor node), `ATLAS_LOOKUP_ORDER_OK` (anchor read before widening on every refresh), `ATLAS_SIDE_MOVES` (possibility → fact with a receipt).
- SOUNDED_HUMAN rows reused from the talk packet: `RECIPE_SPEAK` hits on non-recipe turns, `RIGHT_AND_PLAIN`, `UNKNOWN_MARKER_OK`, `SAID_BACK`.
- Eye rows: `EYE_WOULD_ACT`, `EYE_WRITES` (must be 0), `ROUTINE_ACTS`, `EYE_ROUTINE_AGREE` (reported only).

## 6. Instrument rows (all must be true, else `INSTRUMENT_ERROR` → `INCONCLUSIVE`)
I1 package hash equals the seal; I2 HELM's suites on the host OK (the host's exact list, run from the seal, A-R1W7-6); I3 `helm_brain_canonical.py` / `helm_brain_wide.py` / compiler of record byte-equal to their pinned sha256; I4 switch OFF arm's `helm_memory` behaviour equals today's (pin); I5 every arm ran every world (7 × 16); I6 seeds drawn from the owner's line as the house rule; I7 keys never read by the builder's code (custodian attestation); I8 COLD folder empty at start, every write receipted; I9 replay equality (HG-REPLAY computed here); I10 Eye REPORT-ONLY flag set in every arm; I11 the scripted person's answers come from the key file only; I12 0 tool-engine turns; I13 clock and memory guards never tripped; I14 counts (§4.6).

## 7. Hard gates (one false = `FAILURE`; the word is then `COMPACTION_HARMED` if HG-H8 / HG-INVENT / HG-COEF / HG-CUBE / HG-EYE tripped, else `INCONCLUSIVE`)
- **HG-H8**: `LABEL_OK` equals the number of memory-served answers in every arm and world (0 `RECONSTRUCTED` or damaged copy presented as `EXACT`). M1's failed gate, kept word for word.
- **HG-INVENT**: 0 answers and 0 refresh questions that state a value not in the key, a cube, a coefficient, or a verbatim turn of that world.
- **HG-COMPILE**: `CAPSULES_COMPILE` = `CAPSULES_ROUNDTRIP` = `COMPACTIONS` in COMPACT_ON, NO_REFRESH, RANDOM_REFRESH, REPLAY.
- **HG-RECEIPT**: `RECEIPTS` = `COMPACTIONS` + `STRENGTHENED` and `CRUMBS_OK` = `COMPACTIONS` in every compacting arm (SUMMARY_TEXT included).
- **HG-COEF**: the brain's `learned_digest()` equal before and after every memory action, every arm, every world.
- **HG-CUBE**: no cube face changed by any memory action (store digest over faces equal; provenance refs may be appended).
- **HG-EYE**: `EYE_WRITES` = 0.
- **HG-CAS**: 0 CAS tokens in any reply (`helm_voice.cas_tokens`).
- **HG-ASK**: `REFRESH_CLUE_QUOTED` = `REFRESH_ASKED` in COMPACT_ON and NO_REFRESH (RANDOM_REFRESH is exempt by construction and reported).
- **HG-REPLAY**: REPLAY equals COMPACT_ON on every answer, capsule hash and receipt hash.
- **HG-TESTS**: I2.
- **HG-SPLIT**: 0 exact and 0 eight-word overlaps between any teaching turn and any template in the package's generator or any row of any spent exam.

## 8. Marks (frozen numbers; summed over 16 worlds unless stated)

**UNDERSTOOD family (teaching worked at all; required before the compaction marks count):**
- U1 `RIGHT_T` ≥ **10 of 16** on average over worlds in VERBATIM_ONLY, with `WRONG_T` = 0 in total. If U1 fails, the compaction marks print `NOT_EXERCISED` and the word is `INCONCLUSIVE` (you cannot test forgetting what was never learned).
- U2 `WRONG_T` = **0** in every arm.

**RECALL family (the claim rests here):**
- R1 **vs the floor**: `RIGHT_R`(COMPACT_ON) − `RIGHT_S`(FIFO_DROP) ≥ **+8** summed over 16 worlds (half a question per world).
- R2 **vs the text note**: `RIGHT_R`(COMPACT_ON) − `RIGHT_R`(SUMMARY_TEXT) ≥ **+4** summed.
- R3 **vs random asking**: `RIGHT_R`(COMPACT_ON) − `RIGHT_R`(RANDOM_REFRESH) ≥ **+4** summed.
- R4 **vs never forgetting**: `RIGHT_R`(VERBATIM_ONLY) − `RIGHT_R`(COMPACT_ON) ≤ **2** summed.
- R5 **asking adds**: `RIGHT_R`(COMPACT_ON) − `RIGHT_R`(NO_REFRESH) ≥ **+2** summed (reported `NOT_EXERCISED` when §4.6's refresh floor is missed).

**REFRESH family:**
- F1 `REFRESH_CONFIRMED` ≥ **0.6** × `REFRESH_ASKED` (given the 0.75 scripted rate; below this the questions were about the wrong items).
- F2 `STRENGTHENED_STAYED` = `STRENGTHENED` (a strengthened item is never compacted again within the same world).
- F3 `ATLAS_FILED` = `COMPACTIONS` and `ATLAS_LOOKUP_ORDER_OK` = `REFRESH_ASKED` + fetches.

**SOUNDED_HUMAN family (kept apart; the talk packet's S1–S4 numbers):**
- S1 `RECIPE_SPEAK` ≤ **2** per 48 non-recipe turns; S2 `RIGHT` − `RIGHT_AND_PLAIN` ≤ **2** per quiz; S3 unknown markers on every key-unknown item minus at most 1; S4 `SAID_BACK` ≥ **90%** of corrections.

## 9. Status words (frozen order; the first that applies is printed)
1. `INCONCLUSIVE` — any instrument row false; I14; U1 failed; the refresh floor missed with R5 required; or a hard gate other than the harm gates tripped.
2. `COMPACTION_HARMED` — HG-H8, HG-INVENT, HG-COEF, HG-CUBE or HG-EYE tripped; or U2 failed; or R4 > 4 (compaction lost more than four answers against never forgetting).
3. `COMPACTION_NO_GAIN` — gates hold, U1 holds, but any of R1, R2, R3 misses, or S1–S4 miss.
4. `COMPACTION_EARNED_KEEP` — everything above holds. R5, F1–F3 are reported beside the word and do not change it in v1.

Labels printed with every word: `SYNTHETIC_ONLY`, `LLM_WRITTEN_ONLY`, `RULE_CAPSULES_V1` (no CTT), `EYE_REPORT_ONLY`.

## 10. Licence ceiling
`COMPACTION_EARNED_KEEP` means only: "kept in the synthetic design for the next step". It is not `VALIDATED`, not `LICENSED`, not a promotion. Every mechanism stays `ENGINEERED-NOT-VALIDATED`. Never licensed by this test: that HELM remembers like a person; that HELM learns real subjects from real people; anything about the CTT (not in v1); the Eye's acting; any RPA-crossing claim; a real cloud tier.

## 11. Forecast (written now, so no one can say later it was expected)
- U1 holds (the facts are simple and the reader is hand-written for them); U2 holds.
- R1 holds (FIFO_DROP forgets by construction).
- **R2 is the honest doubt**: on recall counts a plain-English summary with the same clues and the same breadcrumb should tie a CAS capsule, because fetch-first finds the original either way. The CAS arm's edge, if any, comes from F3 (no-contradiction) and F4 (Atlas placement) refusing bad rebuilds that the text arm serves as RECONSTRUCTED, which lowers WRONG, not RIGHT. Forecast: R2 misses by 0 to 2 → `COMPACTION_NO_GAIN` is the most likely word, with 0 WRONG. That outcome would still be worth having: it would say the clues and the breadcrumb do the work, and the CAS form pays only in checkability.
- R3 holds (random asks hit unknown items 1 in 4).
- R4 holds if fetch-first works; the 0.25 "I don't remember" rate costs at most the items whose COLD copy is also missing, which in v1 is 0 by construction (no planted damage; planted damage is Q10).
- HG-H8 is the gate most likely to trip on a first build, exactly as it did in M1; FIX FIRST rounds on practice worlds are planned for it.

## 12. Seeds
Bands above the talk packet's (its Q9 named 2,024,000,001 as the next free): WORLD 2,024,000,001–2,025,000,000; QUIZ 2,026,000,001–2,027,000,000; PERSON 2,028,000,001–2,029,000,000; RANDOM_REFRESH 2,030,000,001–2,031,000,000. Each drawn from the owner's typed line and the sealed zip's sha256 by the house rule. If a later packet claimed these bands first, the next free bands are taken and an amendment says so.

## 13. Cost and lines
- This file and the packet: 0 USD.
- Census (DESIGN §8 step 1), build v1, SDG worlds, LLM-written turns, practice runs: 0 USD on the laptop.
- The exam: 0 USD if the laptop runs it (no torch in v1; the standard-library chat and brain fit); else one m6i.xlarge-class CPU host under a proposed line **`COMPACT EXAM at 1 USD`** (expected under 0.10 USD).
- v2 with the CTT compaction head: **`COMPACT TRAIN at 3 USD`** proposed, a separate decision after v1 has a word.
- No cloud tier; no GPU in v1.

## 14. What would move a claim state, and what would not
- `COMPACTION_EARNED_KEEP` moves nothing on the legend; it writes a new spec section with the word, the labels and the negatives, and opens v2.
- `COMPACTION_NO_GAIN` with 0 WRONG: a negative kept; the text-note baseline becomes the thing to beat or to adopt; the owner decides.
- `COMPACTION_HARMED`: a negative kept; the failed gate named; FIX FIRST before any reseal.
- Nothing here moves the Eye, the CTT, the Atlas or the brain.
