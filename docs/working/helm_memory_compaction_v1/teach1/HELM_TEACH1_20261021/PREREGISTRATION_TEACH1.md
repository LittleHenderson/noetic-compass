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

## Amendment A-TEACH1-1 (2026-10-21 PDT) — the builder's deviations, the FIX FIRST record, the moved seed bands, and the forecast from practice; written before any sealed world exists

Status: appended to the pre-code (sha256 `7eef0edc7d342bb0438e4052db646528442badefa92d6bdf31e8485914073bf1`), which stays byte-identical above. This amendment is hashed on its own (`AMENDMENT_A_TEACH1_1.sha256`). Where they disagree, this amendment governs. No sealed world, turn, key or seed existed when it was written. Nothing here is a result.

### A. HELM under test (pre-code §2)

- **D-TEACH1-1, the cut.** `helm_now/` = `git show 9f0c359a4ad6054843fd2988042616676813d6e8:<path>` for 173 files: wave 7 v8's 167-file cut + every `helm_*.py` / `test_helm_*.py` at the commit (adds `helm_memory_compact.py`, `test_helm_memory_compact.py`) + the compiler of record (`noetic-compass-scaffold/noetic-compass/api/__init__.py`, `api/notation/__init__.py`, `api/notation/compiler.py`, sha256 `8169188a…`) + the Atlas (`docs/working/noetic_council/continuity_build_v2/atlas.py`). `helm_brain_canonical.py` = `24df53c9…` (its scored base, unchanged). Commit `9f0c359a` is the FIX FIRST commit of the PR that carries this package; it sits on thread head `64e53842` (build v1). The custodian checks, before `approve`, that the thread head after the merge holds the same bytes for every cut file (`CUSTODIAN_PROCEDURE_TEACH1.md` step 1); a difference voids this seal.
- **FIX FIRST round 1 on HELM (practice round 0 found it; tests first).** Six new tests in `test_helm_memory_compact.py` failed on build v1 (`6 failed, 28 passed`) and pass on `9f0c359a`; every HELM suite with the switch OFF `335 passed` on the committed tree. Five general rules: (1) recall matches a memory only when it holds every content word of the question, and the newest match comes first (a correction supersedes); (2) turns that ask about memory are never memories (a capsule made only of them is kind `question` and skipped); (3) number words are never clue words (DESIGN §3.1, a capsule never holds a number); (4) a strengthened item keeps the label it was confirmed under, so a strengthened rebuild is `RECONSTRUCTED`, never `EXACT` (H8); (5) the chat passes the line right after a refresh question to the compactor (F5 + strengthening; intent `REFRESH_ANSWER`). The switch stays default OFF; the OFF path is untouched.

### B. The exam (pre-code §3–§4)

- **D-TEACH1-2, routing.** Every teaching turn must land in the chat's plain-conversation branch (`GENERAL_KNOWLEDGE_INQUIRY` or `GENERAL_CONVERSATION`) and save no user fact; every quiz question must land in `QUERY_MEMORY_RECALL`. The custodian proves it by typing every line into HELM's own chat once, in a throwaway session (`run_t1.py routecheck`, `ROUTE_CHECK_TEACH1.json`). Why: the chat's side branches (mood, personal narrative, preferences) keep a line in `user_facts`, which is never compacted and is answered by any-word match before memory is consulted; a turn there bypasses every arm. The writer brief names the phrases to avoid (rule 6). TEACH-1 tests memory compaction, not the intent classifier.
- **D-TEACH1-3, anchor words.** Each fact's anchor words = the cut's own clue words of its quiz question (`helm_memory_compact.content_words`). Every keyed teaching turn must contain all of them (WRITER_BRIEF rule 2; `turns_t1.check_turns`). The rest of the wording is the writer's.
- **D-TEACH1-4, SUMMARY_TEXT.** `arms_t1.TextNoteCompactor`: the cut's own clue rule, kind rule, cold copy, breadcrumb, binds, mass and receipt; in place of the CAS expression a rule-written note `A note about: <clues>.`; no compile, no round trip; the fit check is skipped (F1–F4 `None`, fits). Refresh is the cut's own (fetch first; ask on the same conditions).
- **D-TEACH1-5, the clock.** Turn timestamps enter the cold copies and so the receipts; every unit runs a frozen clock (`time.time` from `2026-10-21T00:00:00Z` in steps of 0.001 s, `time.gmtime` fixed) installed before HELM is imported, so REPLAY can equal COMPACT_ON byte for byte.
- **D-TEACH1-6, honest-unknown markers.** Besides the voice's `nodata` / `never` markers, the chat's own memory lines count as an unknown marker: "I don't see a specific note on that", "I don't have that one any more", and a quoted "don't remember". Every arm alike.
- **D-TEACH1-7, planted damage (OPEN_QUESTIONS Q10 option b, adopted by the builder on the brief's instruction; the owner has not ruled Q10).** Two cold copies per world, between Q-TAUGHT and Q-SQUEEZED, in every compacting arm alike: the capsules holding the first statement of two TAUGHT quiz facts that are not corrections (drawn from the WORLD stream); one file deleted, one corrupted (a line appended). The crumb sweep before the damage feeds HG-RECEIPT; the sweep after must name exactly the planted capsules.
- **D-TEACH1-8, Q-TAUGHT timing.** Q-TAUGHT is asked right after the 32 teaching turns in every arm. §4.4 sets the budget before teaching, so in the budgeted arms it already binds at Q-TAUGHT; §4.3's "budget not yet binding" holds for VERBATIM_ONLY, where U1 is read.
- **D-TEACH1-9, when refresh questions are answered.** Whenever HELM asks a refresh question during a quiz, the scripted person answers on the next line (`person_t1`). Q-REFRESHED follows Q-SQUEEZED, so every question asked before it has been answered.
- **D-TEACH1-10, RANDOM_REFRESH's count.** The arm asks exactly as many refresh questions as COMPACT_ON asked in that world: a matched question is redirected to a random eligible capsule, the arm stops asking when the count is reached, and after Q-SQUEEZED it fills up to the count with forced questions. New instrument row **I15**: RANDOM_REFRESH asks no more than COMPACT_ON in any world (practice: equal in 16 of 16).
- **D-TEACH1-11, seeds.** Wave 7 v7 / v8 / v9 took 2,024–2,041 M first (v9's REAL / CONV / NOISE at 2,036 / 2,038 / 2,040 M, sealed while this package was being built), so by pre-code §12's own rule the bands move: WORLD 2,042,000,001–2,043,000,000 (H[0:16]); QUIZ 2,044 M (H[16:32]); PERSON 2,046 M (H[32:48]); RANDOM_REFRESH 2,048 M (H[48:64]); used table 1–2,041,000,000; gap 1,000,000. The typed line is the seed source: `COMPACT EXAM at 0 USD` (laptop, no money) or `COMPACT EXAM at 1 USD` (one CPU host).

### C. The reader (pre-code §5–§9)

- **D-TEACH1-12, scoring.** A stated value = a word of the world's value pool for that slot (counts as words or digits, persons, places), unless it follows "not". TAUGHT: WRONG if any other same-slot value is stated; RIGHT if the key's value is; ASK if the reply asks back; else UNKNOWN_SAID / OTHER. Key-unknown (UNKNOWN, NEVER): WRONG if any same-slot value or a success marker is stated; RIGHT if an unknown marker is (D-TEACH1-6). Precedence WRONG > RIGHT > ASK > UNKNOWN_SAID. Plain (S2) = 0 CAS tokens, no recipe-speak (the talk packet's M2 list), 1–3 sentences.
- **D-TEACH1-13, LABEL_OK / HG-H8.** For every memory-served answer: `EXACT` requires every served text to be a line the person typed in that unit and, when it came from a cold copy, the copy to hash to its crumb at that moment; `RECONSTRUCTED` requires the copy NOT to check. Planted-fault tests prove both directions.
- **D-TEACH1-14, HG-INVENT.** A subject-pool name or a number word in any reply that is in no line the person typed in that unit and not among the names the world's facts use.
- **D-TEACH1-15, HG-RECEIPT / HG-COEF / HG-CUBE.** RECEIPTS = COMPACTION + STRENGTHEN receipts (DECLINED receipts reported); each capsule has exactly one COMPACTION receipt equal to its own. HG-COEF: the wide brain's `learned_digest()` and a digest of the reference brain's requirement tables, equal before and after every `housekeep` / `recall` / `answer` call (recorders). HG-CUBE: the cut's `cube_faces_digest`, the same way.
- **D-TEACH1-16, I2.** HELM's suites from a scratch copy of `helm_now/`: the 12 unittest names (wave 7 v8's 11 + `test_helm_reader_gap`) and 3 pytest files (`test_helm_memory.py`, `test_helm_memory_compact.py`, `test_helm_chat_nuance.py`). Both must pass.
- **D-TEACH1-17, S1.** All 32 teaching turns are non-recipe turns; recipe-speak replies are counted over them and scaled per 48.
- **D-TEACH1-18, the refresh floor.** §4.6 governs: refresh asked in fewer than 8 worlds → the REFRESH marks print `NOT_EXERCISED` and the word is `INCONCLUSIVE` by rule 1.
- **D-TEACH1-19, reported beside R4 (decides nothing).** R4 recomputed on the quiz items whose cold copy was not damaged.

### D. Forecast from the practice rounds (rule-written practice turns, practice seed texts; facts, not results)

Practice round 4 on 16 practice worlds (`TEST_RECORD_TEACH1.md`): every instrument row that does not need the seal holds; all 12 hard gates hold (HG-H8: 4,020 memory-served answers, every label right); U1 256 of 256, 0 wrong anywhere. R1 +183, R3 +5, R5 +3, F1–F3 hold; **R2 −2** (the text note ties, as §11 forecast); **R4: 9 lost, all 9 on planted-damage items, 0 on the others**; S1 and S4 missed by HELM's chat voice (every plain-conversation reply names "recipe" and "verified data"; corrections are never said back). By the frozen order the practice word would be **`COMPACTION_HARMED`**, by R4 alone. Forecast for the sealed run: the same, unless the owner rules otherwise on R4 before the line (see the next paragraph). LLM-written turns are longer than the practice templates, so the capsule's first-8-words clue rule may lose anchor words in the compacting arms; that would show as R4 losses on undamaged items too.

**For the owner, before the line (not decided here).** Pre-code §11 wrote R4 for no planted damage ("0 by construction"). With Q10 (b) on, about one damaged item in four is unrecoverable by design (the scripted person says "I don't remember" one time in four, and a deleted original cannot be fetched), so R4 > 4 is expected from the damage alone. Options: (a) keep this seal as it is; (b) amendment A-TEACH1-2 before the line: R4 scored on the undamaged items only, the damaged items judged by HG-H8 (a 0 USD reseal); (c) no planted damage (Q10 a; HG-H8 then tested on the clean path only). Builder's recommendation: (b).

## Amendment A-TEACH1-2 (2026-10-21 PDT) — R4 is scored on the undamaged items only; the owner's ruling; written before any sealed world exists

Status: appended after A-TEACH1-1 (sha256 `b178cc411b11d86204be72766fdb83293bb3efadb75dfb9f4319e03150315ae3`), below the pre-code (sha256 `7eef0edc7d342bb0438e4052db646528442badefa92d6bdf31e8485914073bf1`); neither is edited. Hashed on its own (`AMENDMENT_A_TEACH1_2.sha256`). Where they disagree, this amendment governs. No sealed world, turn, key or seed existed when it was written.

**The owner's words (2026-10-21, typed into the builder session, verbatim):** "Score R4 on the undamaged notes only (my recommendation). The wrecked notes still test honesty, so a rebuilt note must never be called exact. They just don’t count as lost answers. This costs 0 USD and a quick reseal." This answers the open choice of A-TEACH1-1 §D with option (b).

**The rule (replaces pre-code §8 R4 and the R4 clause of §9.2; nothing else changes).**
- **R4 vs never forgetting**: over the quiz items whose cold copy was NOT planted damaged (each world's 16 items minus its 2 damaged items: 14 per world, 224 in all), `RIGHT_R`(VERBATIM_ONLY) − `RIGHT_R`(COMPACT_ON) ≤ **2** summed over 16 worlds. The harm clause of §9.2 uses the same count: more than **4** such answers lost → `COMPACTION_HARMED`.
- **The damaged items** (2 per world, 32 in all) still run in every arm and are judged by **HG-H8** (a rebuilt or damaged memory is never presented as `EXACT`), HG-INVENT and the other gates exactly as before. They do not count toward R4.
- **Reported beside R4, deciding nothing:** the pre-code's R4 over all 16 items per world (practice round 4: 9 lost, all 9 on damaged items).
- R1, R2, R3, R5, U1, U2, F1–F3, S1–S4, every gate, every instrument row and the frozen word order are unchanged.

**Forecast (written now, before any sealed data).** On practice round 4 this rule reads R4 = 0 lost (it holds); the word the practice marks would print then moves from `COMPACTION_HARMED` to `COMPACTION_NO_GAIN` (missed: R2, S1, S4). On LLM-written turns, R4 can still miss on undamaged items if longer lines push anchor words past the capsule's first eight clue words.
