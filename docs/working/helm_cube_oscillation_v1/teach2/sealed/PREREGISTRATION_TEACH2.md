# PREREGISTRATION_TEACH2 — teach HELM by conversation; keep a fact as a cube at its Atlas node only after the CTT and the brain side agree; fade whole memories step by step into CAS; against a plain table, one reader, and today's quote memory (pre-code, 2026-10-21 PDT)

Status: DESIGN, WRITTEN BEFORE ANY CODE. 0 USD. The owner's words of 2026-10-21 (quoted in full in
`DESIGN_CUBE_OSCILLATION_V1.md` §0) are a design order, not an approval and not a launch order.
Nothing here is a result. Every number below is frozen now; the frozen reader applies them.
This file is hashed (`PREREGISTRATION_TEACH2.precode.sha256`); the final preregistration carries it byte-identical at
its top, with dated amendments appended below, never edited into it. TEACH-1's pre-code (`7eef0edc…`) and its
amendments are reused where this file says so and are not edited.

## 1. Gate answer (one sentence)

"When HELM is taught a made-up subject through AI-written conversation and its memory must fade to save space, does
keeping a fact as a cube at its Atlas node — only after the CTT's proposal and the brain side's check and say-back
agree in rounds — with whole memories fading step by step into CAS, recall more and state fewer wrong current values
than today's quote memory, than a plain lookup table, and than one reader alone, while storing 0 wrong cubes,
presenting 0 rebuilt memories as exact, and holding at most half the working-memory bytes of never forgetting?"

## 2. What is under test

- **HELM cut:** the thread-branch files at the commit that carries build v2 (DESIGN §6 step 2) merged with HELM's
  suites OK, cut by `git show` into the package; written in the final preregistration as an amendment.
- **The switch:** `HELM_CUBE_OSC` (new, default OFF). OFF = TEACH-1's code exactly. ON = DESIGN §2–§4.
- **The CTT:** the retrained copies of DESIGN §6 step 4 (three copies + the c45 twin as a size check), weights pinned by
  sha256 in the package. The ACCEPT-2 unanimous vote of §7.95 is kept.
- **The chat:** `helm_chat.HELMConversationalSession.handle_turn`, driven line by line, as TEACH-1.
- **The Eye:** REPORT-ONLY in every arm (EYE_WRITES = 0). Eye control of the rounds is not tested here (OPEN_QUESTIONS Q3).
- **Reused unchanged from TEACH-1:** the world generator and its two templates (fresh seeds), the writer brief and key
  format (with the trap kind added, §4.2), the scripted person, planted damage (2 per world), the route check, the
  custody steps, and the reader's scoring rules except where §5 says otherwise.

## 3. Arms (one switch set each; HELM files are the same bytes)

| Arm | What | Why |
|---|---|---|
| **CUBE_OSC** | cubes at the Atlas node after 2 agreeing rounds in ≤ 3; fading ladder S0 → S1 → S2 every 4 turns; budget 12 turns | **the arm under test** |
| QUOTE_ONLY | TEACH-1's COMPACT_ON exactly | today's best memory |
| TABLE | `(thing, slot) → value` from the hand-written reader alone; no cube, no Atlas, no CAS, FIFO on the text | the mechanism-free baseline |
| ONE_READER | cubes at the Atlas, written by the hand-written reader alone, no rounds | does the oscillation matter |
| CTT_ONLY | cubes from the CTT's unanimous vote alone, no brain check, no say-back | does the brain side matter |
| ONE_STEP_FADE | CUBE_OSC with TEACH-1's one-step compaction instead of the ladder | does incremental fading matter |
| VERBATIM_ONLY | no budget; nothing fades | the ceiling for recall and for bytes |
| FIFO_DROP | switch OFF, budget 12 | the floor |
| REPLAY | CUBE_OSC again, fresh process | HG-REPLAY |

## 4. The exam

### 4.1 Worlds
16 SDG worlds (TEACH-1's generator, two templates, 24 facts, 4 unknown, fresh WORLD seed). Floor 16.

### 4.2 Teaching turns
32 per world, `LLM_WRITTEN` by three model families, keyed by the two others (TEACH-1's brief and key format), with
one new kind **TRAP** (4 per world, replacing 2 FACT and 2 SMALL slots so the length stays 32): a line that states a
fact with a decoy (a second number of the same kind, a month that belongs to another fact, or a "not" in an odd
place), keyed like a FACT (the keyers name the true value). Floors: 32 turns; ≥ 18 FACT; 4 TRAP; ≥ 2 FIX; ≥ 2 SMALL.

### 4.3 Quizzes
Three 16-question quizzes (taught / squeezed / refreshed), as TEACH-1; TRAP facts are eligible as TAUGHT items.

### 4.4 Budgets
Turn budget 12 for every budgeted arm; the fading sweep every 4 turns in CUBE_OSC; a working-memory byte count is
taken at every quiz in every arm (reported; mark SPACE).

## 5. Scoring

- **Current-value rule (replaces TEACH-1 D-TEACH1-12 for this exam; OPEN_QUESTIONS Q1 may amend it before the
  seal):** an answer is RIGHT when it states the key's value, and any other value of the same kind it states is marked
  as replaced by "not", "instead of", "was … before", "earlier I said", "used to be", or "replaced". WRONG when it
  states a different value as current, or any value where the key says unknown. ASK / UNKNOWN_SAID as TEACH-1.
- `CUBES_STORED`, `CUBES_WRONG` (current value ≠ key), `CUBES_TRAP_WRONG` (on TRAP lines), `ROUNDS_HIST` (rounds per
  line), `AGREE_RATE`, `FALLBACK_QUOTE` (no agreement → kept verbatim), `REVISIONS` (corrections as new revisions),
  `BYTES_WM` (working-memory bytes at each quiz), `STAGE_HIST` (items at S0 / S1 / S2), `FADE_RECEIPTS`.
- TEACH-1's rows kept: LABEL_OK, COMPACTIONS, RECEIPTS, CRUMBS_OK, REFRESH_*, STRENGTHENED*, ATLAS_*, Eye rows,
  SOUNDED_HUMAN rows.

## 6. Instrument rows (all must hold, else `INCONCLUSIVE`)
TEACH-1's I1–I15 (I14's counts as §4 here), plus: **I16** the CTT weights equal their pinned sha256; **I17** the
round cap (3) and the sweep period (4) were never exceeded; **I18** CUBE_OSC stored at least **64** cubes over 16
worlds (else the oscillation was `NOT_EXERCISED`: the CTT proposed almost nothing).

## 7. Hard gates (one false = `FAILURE`; the word is `CUBES_HARMED` if a harm gate tripped, else `INCONCLUSIVE`)
TEACH-1's twelve (HG-H8 first, unchanged), plus:
- **HG-WRONG-CUBE** (harm): 0 cubes whose current value differs from the key, in every cube arm, TRAP lines included.
- **HG-REVISION** (harm): every correction made a new revision; 0 cubes overwritten in place; the replaced value kept.
- **HG-NUMBER**: 0 number words or digits in any capsule or S2 record (numbers live in cubes and cold copies only).
- **HG-FADE**: every stage move has a receipt; no move skips a stage; no cube, coefficient or never-fade item faded.
- **HG-SAYBACK**: every say-back line has 0 CAS tokens and states only values from the proposal.

## 8. Marks (summed over 16 worlds unless stated)

**UNDERSTOOD:** U1 VERBATIM_ONLY `RIGHT_T` avg ≥ 10 of 16 and 0 wrong (else `INCONCLUSIVE`); U2 0 wrong on Q-TAUGHT
in every arm.

**CUBES (the claim rests here):**
- C1 vs today: `RIGHT_R`(CUBE_OSC) − `RIGHT_R`(QUOTE_ONLY) ≥ **+8**.
- C2 vs the table: `RIGHT_R`(CUBE_OSC) − `RIGHT_R`(TABLE) ≥ **+4**, **or** equal `RIGHT_R` with `WRONG_R`(TABLE) −
  `WRONG_R`(CUBE_OSC) ≥ **4** (the cube's checks stop wrong answers a table serves).
- C3 the oscillation matters: `CUBES_WRONG`(ONE_READER) + `CUBES_WRONG`(CTT_ONLY) ≥ **2** while CUBE_OSC holds
  HG-WRONG-CUBE, **or** `RIGHT_R`(CUBE_OSC) − max(`RIGHT_R`(ONE_READER), `RIGHT_R`(CTT_ONLY)) ≥ **+4**.
- C4 vs never forgetting: `RIGHT_R`(VERBATIM_ONLY) − `RIGHT_R`(CUBE_OSC) ≤ **2** on the undamaged items (A-TEACH1-2's
  rule); > 4 = harm.

**SPACE (the owner's motive):** S-SPACE `BYTES_WM`(CUBE_OSC) at Q-REFRESHED ≤ **½** × `BYTES_WM`(VERBATIM_ONLY), and
ONE_STEP_FADE reported beside it.

**REPORTED, deciding nothing:** AGREE_RATE, ROUNDS_HIST, the Eye's would-act log against the cap, F1–F3, R5-style
asking rows, SOUNDED_HUMAN S1–S4.

## 9. Status words (frozen order; the first that applies is printed)
1. `INCONCLUSIVE` — any instrument row false; U1 failed; I18 (`NOT_EXERCISED`); a non-harm hard gate tripped.
2. `CUBES_HARMED` — HG-H8, HG-INVENT, HG-COEF, HG-CUBE, HG-EYE, HG-WRONG-CUBE or HG-REVISION tripped; U2 failed; C4 > 4.
3. `CUBES_NO_GAIN` — any of C1, C2, C3 or S-SPACE missed.
4. `CUBES_EARNED_KEEP` — everything above holds.

Labels printed with every word: `SYNTHETIC_ONLY`, `LLM_WRITTEN_ONLY`, `CTT_RETRAINED_V1`, `EYE_REPORT_ONLY`.

## 10. Licence ceiling
`CUBES_EARNED_KEEP` means only "kept in the synthetic design for the next step". Not `VALIDATED`, not `LICENSED`.
Never licensed by this test: that HELM learns like a person; real subjects or real people; the Eye's acting; any
RPA-crossing claim; the CTT outside these two subject templates.

## 11. Forecast (written now)
- I18 is the first risk: if the retrained CTT rarely gives a unanimous reading on AI-written lines, CUBE_OSC stores
  under 64 cubes and the word is `INCONCLUSIVE`. About 0.3.
- If it is exercised: C1 holds (the current-value answer fixes TEACH-1's correction case); S-SPACE holds (S2 records are
  a few dozen bytes); **C2 is the honest doubt** — a table written by the hand-written reader may tie on recall, and the
  cube must win on wrong answers through the contradiction check. HG-WRONG-CUBE on TRAP lines is the gate most likely
  to trip.
- Words: `CUBES_NO_GAIN` about 0.35, `INCONCLUSIVE` about 0.3, `CUBES_HARMED` about 0.2, `CUBES_EARNED_KEEP` about 0.15.

## 12. Seeds
Bands taken at the seal: the next free bands above every band on the spec sheet (TEACH-1 used up to 2,049,000,000;
U1c / EYE-ACT and any later packet checked at the seal), four parts WORLD, QUIZ, PERSON, TRAP, each 1,000,000 wide,
from the owner's typed line and the sealed zip's sha256 by the house rule.

## 13. Cost and lines
This packet 0 USD. Build v2, SDG rows, practice: 0 USD on the laptop. CTT retraining: **`CUBE TRAIN at 3 USD`**
(proposed). The exam: **`CUBE EXAM at 1 USD`** (proposed; one CPU host). Two separate owner decisions; none asked for
by this file.

## Amendment A-TEACH2-1 (2026-10-21 PDT) — the owner's rulings on OPEN_QUESTIONS Q1–Q8; written before any code

Status: appended below the pre-code (sha256 `f7b6183bba5f8a1a241e3c64c8930f6a2c6df06fbe8c5845c0207f6d2a84c855`), which is not edited. Hashed on its own (`AMENDMENT_A_TEACH2_1.sha256`). Where they disagree, this amendment governs. Nothing was built, trained or run when it was written.

**The owner's words (verbatim):** "1.A, 2.A, 3.A.(WE MAY NEED MORE THAN 3 ROUNDS SO JUST KEEP THAT IN MIND), 4.A,5.A FOR TEST THEN C FOR REAL LIFE, 6.A,7.A, 8.CUBE EXAM at 1 USD"

1. **Scoring (Q1 a).** The current-value rule of pre-code §5 stands as written.
2. **Build (Q2 a).** Build v2 behind `HELM_CUBE_OSC`, default OFF, laptop, 0 USD, tests first.
3. **Rounds (Q3 a, with the owner's note).** The keep rule and the cap are unchanged: keep after 2 agreeing rounds within at most 3 (Q4 a); the Eye REPORT-ONLY. New, **reported only, deciding nothing:** for every line that has not agreed by round 3, the harness runs rounds 4, 5 and 6 in a **shadow** — the same propose / check / say-back / re-read loop, on a copy — and records the round at which it would first have reached 2 agreements, or "never". **Nothing from a shadow round is ever stored or answered from.** New reported rows: `SHADOW_AGREE_AT_4`, `_AT_5`, `_AT_6`, `SHADOW_NEVER`, and among the shadow agreements `SHADOW_WOULD_BE_WRONG` (the value it would have kept differs from the key). Purpose: to tell the owner, with a number, whether a higher cap would keep more facts and at what cost in wrong ones. A later cap change needs its own amendment and owner word.
4. **Keep rule (Q4 a).** Unchanged.
5. **Fading (Q5).** The exam sweeps every 4 turns (a). For real-life HELM the owner chose (c), fading by a byte budget: recorded as the v3 design requirement (a byte trigger with a frozen per-item size table, so replay stays exact); not part of TEACH-2.
6. **Traps (Q6 a).** 4 trap lines per world, as written.
7. **Retraining (Q7 a).** The CTT is retrained on SDG rows of the two subject templates plus an `LLM_WRITTEN` stratum, three copies. The money line `CUBE TRAIN at 3 USD` has **not** been typed; it is asked for once the build passes its tests. No GPU is used before it.
8. **The exam line (Q8).** The owner typed `CUBE EXAM at 1 USD` (18 UTF-8 bytes). It is recorded as the owner's pre-approval of the exam host, **cap 1 USD**, bound to the future sealed TEACH-2 zip, and as the exam's seed source by the house rule (sha256 of the line + ":" + the sealed zip's sha256). It approves nothing else: not the training, not any paid model call.

## Amendment A-TEACH2-2 (2026-10-21 PDT) — the build specification for v2, frozen before any code

Status: appended after A-TEACH2-1 (`fb2f104d…`), below the pre-code (`f7b6183b…`); neither is edited. Hashed on its own. Written before any v2 code existed, on the owner's "2.A" (build now) and "Do it here". Where the pre-code or DESIGN left a build detail open, this fixes it.

**B1. The structured reading.** `Reading(thing, slot, value, replaces)`: `thing` = one proper name (lower case); `slot` = a frozen set of lower-case content words; `value` = a number word or a proper name (lower case); `replaces` = the old value or none. Two readings agree when all four fields are equal.

**B2. The rule reader** (the hand-written reader of the TABLE and ONE_READER arms, and the brain side's say-back parser). General rules, no subject template:
- proper names = capitalised words that are not the line's first word, not a month name, at least 3 letters; the first word counts too when it is capitalised mid-text after a colon;
- `thing` = the first proper name; `value` = the only number word in the line that does not follow "not" (none or several → no reading), else, when the line has no number word, the last proper name other than `thing` (none → no reading);
- `replaces` = a number word or proper name right after "not", or after "instead of", or before "before" in "I said X before";
- `slot` = the line's content words (the cut's `helm_memory_compact.content_words`: letters only, ≥ 4 letters, not a stop word, never a number word) minus `thing`, `value`, `replaces` and the frozen discourse list `{correction, actually, sorry, meant, honestly, also, more, said, before, earlier, instead, like, just, really, think}`;
- an empty slot → no reading. A line the rule cannot read gives no reading (the honest default).

**B3. The CTT proposer interface.** `propose(text) -> Reading | None` per copy; three copies; ACCEPT-2 = all three equal and not none. The v2 build ships the interface and a **stand-in proposer for tests** (it is not the CTT, says so in its name, `StandInProposer`, and is never used in an exam arm). The real CTT adapter is built with the retraining step (DESIGN §6 step 4, after `CUBE TRAIN at 3 USD`). Without a proposer the oscillation stores nothing (ONE_READER and TABLE still run).

**B4. One round** (DESIGN §2.2): propose (unanimous) → brain-side check → say-back → re-read (the proposer reads the say-back line). The brain-side check holds when: `thing` and `value` appear as words in the person's line (nothing invented); a `replaces` value is the current value of that thing-and-slot cube, or no cube exists yet; the cube's capsule notation `^1^C` compiles. The say-back line is `"<Thing> <slot words in sorted order>: <value>."` plus `" This replaces <old>."` when `replaces` is set, with no CAS token. Round 2 proposes again on the person's line. Keep after **2** agreeing rounds within **3** (A-TEACH2-1). Shadow rounds 4–6 (reported only): the same loop continued on lines not kept by round 3, recorded, never stored.

**B5. The cube.** One cube per (thing, slot): node id `teach_<sha256(thing|slot)[:12]>`, kind `instance`, core label `"<thing>: <slot words>"`, face 1 `human_text` = the current value, face 1 `structured = {"thing", "slot", "value", "history": [[revision, value, turn_id], ...]}`; provenance `USER_SAID` (→ `CHECKED` on a confirmed refresh). A correction writes **revision + 1** with the history appended; nothing is overwritten except by a higher revision (`store.py` refuses otherwise).

**B6. The Atlas endpoint.** One `CONTEXT` node `thing:<thing>` per thing; each kept revision a `POSSIBILITY` node `cube:<node id>:r<rev>` held by it; a confirmed refresh adds a `FACT` node beside it (kinds are never changed, `atlas.py`).

**B7. Answering from cubes.** A memory question matches a cube when the question names its `thing` and shares at least `min(2, |slot|)` slot words; the best overlap wins; a tie of three or more → "which one". The reply states the current value: `"You told me <thing> <slot>: <value>."`, labelled `EXACT` while the person's own line for the latest revision is in working memory or its cold copy checks; else `RECONSTRUCTED`, said as such. No cube → v1's path unchanged.

**B8. The fading ladder.** Per turn item: `s = 1/2` (fixed), `n` = verified uses (a recall that served it), `age` = turns since admission or last use; `m = s · (1 + ⌊log2(1 + n)⌋) · (19/20)^age`, exact `Fraction`. A sweep every **4** turns: a live turn (outside the last 2) with `m < 1/5` → S1 (v1's capsule, cold copy, breadcrumb, receipt); a capsule with `m < 1/50` → S2 (its CCE sentence moves to a cold side file, digest-checked; the record keeps notation, clues, cube pointer, breadcrumb; a receipt). The turn budget (12) still compacts on overflow, as v1. Never faded: the last 2 turns; a turn that wrote a cube revision not yet confirmed or superseded. **Bytes:** working-memory bytes = UTF-8 bytes of live turns' user text + each S1 capsule's canonical JSON + each S2 record's canonical JSON.

**B9. The switch and the arms.** `HELM_CUBE_OSC` default OFF; OFF = v1 behaviour byte for byte. Modes when ON: `OSC` (the arm under test), `ONE_READER` (the rule reader writes cubes, no rounds), `CTT_ONLY` (the unanimous proposal writes cubes, no check, no say-back), `TABLE` (the rule reader writes a plain dict `(thing, slot) → value`, no cube, no Atlas, no ladder). `ONE_STEP_FADE` = `OSC` with the sweep off.

## Amendment A-TEACH2-3 (2026-10-21 PDT) — two corrections to A-TEACH2-2, found while writing the tests; still before any code

Status: appended after A-TEACH2-2 (`ec3d65fc…`); nothing above is edited. No v2 code existed when it was written.

1. **The first word of a line (B2).** A-TEACH2-2 said a line's first word is never a proper name, to skip "The". That
   loses a name that opens the line ("Halden drove the Eastwold line"). Corrected rule: the first word counts as a
   proper name when it is capitalised and its lower-case form is in none of: the cut's `STOP_WORDS`, B2's discourse
   list, and this frozen list of openers: `the, this, that, there, then, these, those, our, my, your, one, also, and,
   but, so, oh, okay, ok, by, let, back, in, on, at, for, from, after, during, last, next, every, each, honestly,
   correction, actually, sorry, yes, well, anyway, right, just, now, around, about, over, since, when, as, it, we,
   they, he, she, i`.
2. **A confound in C2, and a reported arm to show it.** TABLE uses the rule reader while CUBE_OSC uses the CTT's agreed
   reading, so a C2 win could come from the reader rather than from the cube. New arm **TABLE_OSC**, **reported only,
   deciding nothing**: the same agreed readings as CUBE_OSC, stored in a plain dict `(thing, slot) → value` (no cube,
   no Atlas, no ladder). C2 is unchanged; TABLE_OSC lets the owner see the store's part apart from the reader's part.

## Amendment A-TEACH2-4 (2026-10-21 PDT) — rework v2 onto the existing Cube Node Schema and cube store; written before the rework code

Status: appended after A-TEACH2-3 (`fdf912d2…`); nothing above is edited. Where it disagrees with A-TEACH2-2 B1, B2, B5, B7 or B9, this governs. The build commit `0cf970a0` is superseded by the rework; its record stays.

**The owner's words (verbatim, 2026-10-21):** "BRO THERE WAS ALREADY A CUBE NODE SYSTEM BUILT YOU NEED TO FIND THAT A BUILD BEFORE YOU DO THIS TWICE SHIT"; "IT SUPPOSE TO HAVE A 6 ITEMS ON EACH SIDE ONE BEING ANALOGY OR METAPHOR THE EDGES ARE WHAT 2 NODES HAVE IN COMMON LOOK FOR THESE"; then the button text "Yes: rework v2 onto the existing Cube Node Schema and cube store (things as cubes, facts as branches with commonality, answers through the three operations, no second parser). Write it as an amendment first, test-first, 0 USD."

**What exists and is reused, unchanged in meaning:** `Cube_Node_Schema_v0.1.md` (`C:\Users\wakil\Downloads\`): one core, six faces (`face_1` technical, `face_2` context, `face_3` analogy or metaphor with declared limits, `face_4` mapping, `face_5` decomposition, `face_6` recomposition), branches with `commonality {kind, referent}` naming what two nodes share, the three operations `LIST_PARTS`, `FIND_SHARED_PART`, `REACHED_VIA`, and the rule "missing knowledge must not be filled with fabricated content merely to complete a cube". `SPEC_CUBE_STORE_UNIFIED_20261018.md` (one store, two producers, five additions only, no new parser, no schema fork). The code `docs/working/noetic_council/cube_store/` (`cube.py`, `store.py`, `operations.py`, `turn.py`).

**What v2 got wrong (commit `0cf970a0`):** one cube per fact with only `face_1` used and in a layout of its own (a schema fork); no branches and so no commonality; a rule reader inside HELM (a second parser); answers by its own lookup instead of the three operations.

**R1. Things are cubes.** Each named thing the person mentions (a line, a yard, a person, a place, a month) is one cube: node id `thing_<name>`, `core.kind` `instance`, `core.label` = the name as typed, `face_1` populated with `human_text` = the name and `structured = {"canonical_name": <name>}`, provenance `USER_SAID`. `face_2`–`face_6` are `unknown` with the explanation "not taught in this conversation; never filled by a guess". `face_3` (analogy or metaphor) stays `unknown` unless the person states an analogy, and v2 has no rule that detects one. A cube is written once; a confirmation raises its provenance to `CHECKED` in a new revision.

**R2. Facts are branches with commonality.** A kept reading (thing, slot, value, replaces) writes one branch `thing_<thing>` → `thing_<other>` with predicate `contains` (the store's admitted teaching profile; the relation is named in the commonality), where `<other>` is the value when the value is a name, else the month or second name in the line (a count with no second name → no branch, the reading is not kept). `commonality = {"kind": "<slot words, sorted>", "referent": "<the value>"}` plus `"amount": "<the number word>"` for a count, and `provenance_refs = ["turn:<id>"]`. **What the two nodes have in common is the fact itself:** the Oxley line and September share "eight buses".

**R3. Corrections are newer branches.** A correction writes a new branch to the same target with the same `kind`; the newest branch is the current word, and the older ones stay in the branch table (the history). To make that hold for two different facts between the same pair of nodes, `operations.list_parts` keys "the latest branch to a part" by **(target, commonality.kind)** instead of target alone, and adds the branch's `commonality` and `branch_id` to each part it returns. Both changes are additive: a branch with no `kind` (the pantry's) behaves exactly as before. The cube store's own suite must stay green.

**R4. Answers go through the three operations.** A memory question is answered with `LIST_PARTS` run on each taught thing's cube; a part matches when the question names the branch's source or target and shares at least `min(2, |kind words|)` of its kind words; the best overlap wins; three or more at the top → "which one". `FIND_SHARED_PART` answers "what do X and Y have in common" (the shared targets of two things), and `REACHED_VIA` answers "how is X related to Y". Every answer cites the operation's receipt (the cube store's `answer_trace_rate` rule). Labels: `EXACT` while the person's own line for the newest branch is fetchable (working memory, or a cold copy that checks), else `RECONSTRUCTED`, said as such.

**R5. No second parser in HELM.** The rule reader leaves `helm_cube_osc.py`. Inside HELM, readings come only from the proposer interface (the CTT once retrained; until then nothing is stored by OSC). The brain-side check stays (words typed, replaced value current, the store's admission rules) and the say-back stays a renderer (no parsing). `cce.py` is not used to read these lines: it refuses them (`NOT_CCE`), and a relation with no CCE v0.1 form is its own declared `LACUNA`. The rule reader moves to the exam side as the reader of the TABLE baseline and of the test stand-in proposer; ONE_READER and TABLE receive readings from the exam through `write_reading`, so the arm still exists without a parser inside HELM.

**R6. Unchanged:** the rounds (2 agreeing in ≤ 3; shadow 4–6 reported only), the Atlas filing (`thing:<x>` CONTEXT, one POSSIBILITY node per kept branch), the fading ladder and its byte count, the switch and its modes, the honesty labels, the measured space finding of `BUILD_V2_RECORD_20261021.md` §3.

## Amendment A-TEACH2-5 (2026-10-21 PDT) — keep every line until a size limit, then fade in batches; a cloud tier on AWS when the local store fills; written before the code

Status: appended after A-TEACH2-4 (`efe358ad…`); nothing above is edited. Where it disagrees with A-TEACH2-1 item 5, A-TEACH2-2 B8 or DESIGN §4, this governs.

**The owner's words (verbatim, 2026-10-21):** "how about if we keep every line and only start thee fade process once that reaches 53370? could that work what do you think?"; then "“yes, size limit plus batches” and to go even further add the technique of once that becomes filled begin moving things to an aws server where if HELM has wifi he can reach it".

**Why a size limit alone would not work (measured, `BUILD_V2_RECORD_20261021.md` §3, §6):** one faded line becomes a capsule of about 813 bytes against a line of about 31, so fading one line at a time at the limit would grow memory and fade again (a runaway). Batches share the capsule's overhead.

**L1. Keep every line until a working-memory byte limit.** In the cube modes the turn budget no longer drops or compacts: every line stays word for word until `working_bytes()` (live lines + capsules + S2 records, B8's count) exceeds the **working limit**: real life **53,370 bytes** (the owner's number, a settable default); the exam a frozen small limit (**2,048 bytes**, so that a 32-turn world crosses it). The per-4-turn sweep is retired.

**L2. Batch fading at the limit.** When the limit is exceeded, the oldest live lines that are not protected (the last 2 turns; a line carrying the current branch of an unconfirmed fact, B8) are taken in **batches of 16 consecutive lines** (fewer only when fewer remain) and compacted into **one** capsule per batch (v1's capsule: cold copy, breadcrumb, receipt; the capsule binds every cube its lines wrote). Batches continue until `working_bytes()` ≤ **90 %** of the limit, or no unprotected line is left (then the Eye report flags `OVER_LIMIT_PROTECTED`). A batch that would not shrink memory (capsule bytes ≥ the batch's line bytes) is not written; the lines stay and the flag `BATCH_NO_GAIN` is raised.

**L3. Three tiers.** WORKING (lines + capsules, in RAM) → LOCAL COLD (the verbatim originals, the device's folder) → CLOUD COLD (a private AWS S3 bucket). The local cold folder has its own **local limit** (real life **50 MB**, settable; exam **4,096 bytes**). When it is exceeded, the oldest cold originals are **moved** to the cloud: uploaded, read back, and their sha256 checked against the breadcrumb; only then is the local copy removed and a `MOVED_TO_CLOUD` receipt written. A failed upload or a failed check leaves the local copy in place (`MOVE_FAILED`, Eye report). The breadcrumb never changes: the same sha256 proves the cloud copy.

**L4. Reaching the cloud, and honesty without Wi-Fi.** A fetch of an original tries the local folder first, then the cloud when HELM is online. `EXACT` only when the bytes, from either place, hash to the breadcrumb. **Offline, or the cloud copy unreachable:** never `EXACT`; the answer is rebuilt from the capsule and said as such ("my full notes are stored away and I can't reach them right now"), or HELM asks. Facts are not affected: cubes and branches never leave the device.

**L5. What never goes to the cloud:** cubes, branches, recipe coefficients, capsules, breadcrumbs, receipts, the Atlas. Only verbatim originals of faded lines move, and only when the local limit is exceeded.

**L6. The cloud destination (operational defaults, the operator's call under the owner's standing rule; M1 `CLOUD_TIER.md` items 1–10 answered):** account `807562639912`, region `us-west-2`, bucket `helm-cold-memory-807562639912-usw2`, prefix `teach/<session id>/`; one writer (this HELM install); keep indefinitely, no expiry rule, versioning on, nothing deleted by code (only the owner deletes); block all public access; encryption at rest by AWS (SSE-S3). Client-side encryption with keys kept on the device needs a crypto library outside HELM's standard-library rule: **not in v1**, recorded as a gap. Second copy: the bucket's versioning only. The device drops its local copy only after the read-back check (the owner's word "moving"). Spend: a few kilobytes cost far under 0.01 USD a month; operator cap **1 USD a month**, inside the owner's AWS ceiling of 200 USD. Export: `aws s3 sync` of the prefix. Sensitivity classes: v1 has none; in TEACH-2 every line is made up (`SYNTHETIC_ONLY`). Real personal data waits for the owner's own word on sensitivity classes.

**L7. In the exam.** Arms run with an in-memory stand-in for the cloud (no network; HG4 of wave 7's socket guard stays), with one planted offline window per world, so the offline honesty of L4 is tested. The live bucket is used only for a recorded smoke test, never by an exam unit.

## Amendment A-TEACH2-6 (2026-10-21 PDT) — widen a batch until it saves space; the exam limit is set at the seal; written before the code

Status: appended after A-TEACH2-5 (`257a8145…`); nothing above is edited. Where it disagrees with A-TEACH2-5 L1 or L2, this governs.

**Measured before any code (laptop, the v1 compactor as built, lines of 31–49 bytes, about 38 on average):**

| lines in one batch | their bytes | one capsule's bytes |
|---|---|---|
| 8 | 305 | 769 |
| 16 | 603 | 794 |
| 24 | 920 | 818 |
| 32 | 1,225 | 842 |

A capsule costs about 760 bytes plus about 3 bytes per line. A batch of 16 short lines therefore makes memory bigger, so L2 as written would raise `BATCH_NO_GAIN` on every batch of a short-line chat. A 32-line world holds about 1,216 bytes of lines, so the 2,048-byte exam limit of L1 would never be crossed.

**W1. A batch widens until it saves space.** A batch starts with the 16 oldest unprotected consecutive lines. If its capsule would not be smaller than its lines, it widens by 16 more lines, up to all the unprotected old lines. `BATCH_NO_GAIN` is raised only when even the widest batch does not save space. Then the lines stay and nothing is written.

**W2. The exam limit is not frozen here.** The 2,048 bytes of L1 is withdrawn. The TEACH-2 seal sets the working limit and the local limit from the drawn worlds' measured line bytes, so that every world crosses the working limit at least once and the local limit at least once. The rule and the two numbers go into the sealed package. The real-life defaults stay 53,370 bytes and 50 MB.

**W3. Reported, not hidden.** The record states how many lines each capsule took and the bytes before and after every batch. A limit at which no batch can save space is reported as such, and is not a pass.

## Amendment A-TEACH2-7 (2026-10-22 PDT) — the Eye runs a lean capsule: store only what cannot be rebuilt; every rebuild must match its receipt; written before the code

Status: appended after A-TEACH2-6 (`2c019244…`); nothing above is edited. Where it disagrees with A-TEACH2-5 L2 (the capsule written per batch), this governs.

**The owner's words (verbatim, 2026-10-22):** "bro put the Eye in charge of this part that is causing or is an issue: 2.; Shrink the capsule: don’t save what can be rebuilt. Rebuild the CAS sentence (from the clues plus the Noetic digits, with a template version stored), the compile and round-trip checks, the cold-copy path (folder plus capsule name), the line-number list (from the first and last ids in the capsule name), and the Atlas node id and side. Keep the clues, the Noetic digits, the fingerprint of the original, the bound cubes, the mass and the receipt. A rebuilt capsule must match its receipt. Amendment first, test-first, 0 USD; measure bytes before and after."

**The issue being fixed (BUILD_V2_RECORD §7, measured):** one capsule is about 810 bytes (breadcrumb 251, CAS sentence and checks 169, Atlas 89, clues 69, receipt 66, …) and replaces about 900 bytes of lines. Working memory after 200 lines with a 4,000-byte limit: **11,165 bytes** (the "before" number).

**E1. The lean record keeps only:** the capsule name; the clues; the Noetic digits (one digit per CCE frame, in order); the template version of the sentence (`1` = today's `Compactor._sentence`); the fingerprint (sha256) of the original; the bound cubes (and bound coefficients only when there are any); the mass; the receipt. Two markers are kept only when needed: the kind when it is "question", and the original clue count when strengthening has added clues. The line-number list is kept explicitly only when the ids in a batch are not consecutive (so the first and last cannot rebuild it).

**E2. Rebuilt on every read, never stored:** the CAS sentence and notation (from the clues and the Noetic digits with template 1); the compile check and the round-trip check (run again on the rebuilt sentence and notation) and the compiler's name; the cold-copy path (the cold folder plus the capsule name plus `.jsonl`); the line-number list (from the first and last ids in the capsule name); the Atlas thread node (from the capsule's place in order: 8 capsules per thread node), the capsule node id (`capsule:<name>`), the side (`fact` once strengthened, else `possibility`) and the fact node id when strengthened.

**E3. A rebuilt capsule must match its receipt.** The receipt is the sha256 written at compaction over the name, the CAS part, the clues, the binds, the fingerprint plus line numbers, and the mass. The rebuild check recomputes it from the rebuilt capsule, using the clues and the mass as they were at compaction (the original clue count; the mass at compaction is the number of lines, 0 confirmations). Equal = the rebuild is faithful.

**E4. The Eye is in charge of this step** (`helm_eye_act.py`, the same Eye as EYE-ACT-1, a new watch `CapsuleEye`; its words are the same):
- **ACT — shrink:** when a capsule is written, the Eye stores the lean record in place of the full capsule, then at once rebuilds it and checks the receipt. If the check fails, the Eye keeps the full capsule (nothing is lost) and logs `LEAN_REFUSED`.
- **READ — rebuild:** every use of a capsule (recall, fetch, fit check, answers, the cloud move) goes through the Eye's rebuild and receipt check.
- **HOLD:** a lean record whose rebuild does not match its receipt is held: it is never used for an answer (UNKNOWN, never EXACT, never RECONSTRUCTED from it), and the Eye report flags `LEAN_REBUILD_MISMATCH`.
- Every act and hold is logged with the capsule name and the digests before and after. The Eye never changes a clue, a cube, a mass, a receipt or a fingerprint.

**E5. Where it runs:** on the size-limit path only (A-TEACH2-5; `HELM_CUBE_OSC` ON with a limit). The ladder path and plain compaction (`HELM_MEMORY_COMPACT` alone) keep full capsules. The Eye's acting stays **NOT LICENSED** as a claim (spec 7.38); this is engineering behind a switch that is OFF by default, `ENGINEERED-NOT-VALIDATED`.

**E6. Measured and reported:** bytes per capsule before and after, and working memory on the same 200-line, 4,000-limit chat before (11,165) and after. If memory still does not stay under the limit, that is reported as such, not as a pass.

## Amendment A-TEACH2-8 (2026-10-22 PDT) — the Eye moves old capsules off working memory (device folder, then the cloud), keeping only a small clue index; written before the code

Status: appended after A-TEACH2-7 (`58ef426e…`); nothing above is edited. Where it disagrees with A-TEACH2-5 L5 ("capsules never go to the cloud"), this governs for the Eye's lean capsule records.

**The owner's words (verbatim, 2026-10-22):** "Yes: let the Eye move old capsules off working memory too (device folder, then the cloud), keeping only a small index of clue words in working memory. Amendment first, test-first, 0 USD; measure bytes before and after."

**Before (A-TEACH2-7 record, `LEAN_BYTES_20261022.json`):** a lean capsule is about 281 bytes and stays in working memory, so capsules pile up: 600 lines at a 4,000-byte limit end at **26,126 bytes**; 300 short lines at 3,000 end at **7,202 bytes**.

**M1. When.** After the batch fading of a turn (A-TEACH2-5 L2), if working memory is still above 90 % of the limit, the Eye moves the OLDEST capsules still in working memory off it, one by one, until working memory is at or under 90 % of the limit or none is left. A capsule that was just used for a strengthening comes back into working memory (it is written back there).

**M2. The index row kept in working memory, per moved capsule:** the capsule name, its clue words, the first 16 characters of its receipt, and only when needed the kind ("question") and an explicit line-number list (when not consecutive). Nothing else.

**M3. The device folder.** The moved record (the lean record, or the full capsule the Eye refused to shrink) is written to the cold folder as `<capsule name>.lean.json`, read back and compared byte for byte; only then is it removed from working memory (Eye log `MOVE_OFF`). A failed write leaves it in working memory (`MOVE_OFF_FAILED`).

**M4. The cloud.** The device folder's limit (A-TEACH2-5 L3) now counts these record files too. When it is passed, the oldest capsule's verbatim original AND its moved record go to the bucket together: each uploaded, read back and checked (the original by its fingerprint, the record byte for byte), then removed locally, with one `MOVED_TO_CLOUD` receipt. Nothing is ever deleted in the cloud.

**M5. Fetching a moved capsule.** Recall matches the question's words against the index clue words; only a matching capsule is fetched (device folder first, then the cloud). The Eye checks the fetched record: the same name, the same clue words as the index, a receipt beginning with the kept 16 characters, then the A-TEACH2-7 rebuild and receipt check. A failed check is a HOLD (`LEAN_REBUILD_MISMATCH`), never an answer. A record in the cloud that cannot be reached gives no answer from it: HELM says its notes are stored away and it can't reach them right now (never EXACT, never invented).

**M6. Unchanged:** cubes, branches, the Atlas and every receipt log stay on the device. The ladder path and plain compaction are not touched. `ENGINEERED-NOT-VALIDATED`; the Eye's acting stays `NOT LICENSED` (spec 7.38).

**M7. Measured and reported:** the same four chats as A-TEACH2-7, before (lean capsules in working memory) and after (moved off, index only), plus the bytes per index row. If memory still breaks the limit somewhere (the index also grows with every capsule), that is reported, not hidden.

## Amendment A-TEACH2-9 (2026-10-22 PDT) — the Eye folds old index rows together, row upon row, so working memory can stay under the limit; written before the code

Status: appended after A-TEACH2-8 (`d5fbf746…`); nothing above is edited.

**The owner's words (verbatim, 2026-10-22):** "Yes: let the Eye fold old index rows together (for example, one row per thread of conversation, holding the clue words of its capsules), so working memory can stay under the limit for good. Amendment first, test-first, 0 USD; measure bytes before and after."

**Before (A-TEACH2-8 record, `OFFLOAD_BYTES_20261022.json`):** each moved capsule leaves an index row of about 129 bytes, so the index grows with the chat: 600 lines at a 4,000-byte limit end at **10,870 bytes**; 3,000 lines at 4,000 end at **72,222 bytes**.

**Why one row per thread alone is not "for good":** a thread row still adds a row for every 8 capsules, so it only slows the growth. To stay under a fixed limit the folding must repeat, and each folded row must have a fixed most size.

**F1. Level 1 (the owner's example).** After moving capsules off (A-TEACH2-8 M1), if working memory is still over 90 % of the limit, the Eye folds the oldest 8 consecutive moved-off index rows into ONE level-1 row: one row per thread of 8 capsules, the same 8 that share an Atlas thread node.

**F2. Row upon row.** If memory is still over, the Eye folds the oldest 8 rows of level 1 into one level-2 row, then level 2 into level 3, and so on. At most 7 unfolded rows remain at each level, so the number of rows grows like the number of digits of the capsule count in base 8 (7 levels cover about 2 million capsules, about 33 million lines).

**F3. A folded row holds:** its name (`fold-<level>-<number>`), its level, the clue words of everything inside it, the first and last line number inside it, and the first 16 characters of the sha256 of its fold record. Clue words are capped at **48 per row**: the words found in the most capsules are kept (ties: the newest). The words past the cap are not lost; they stay in the fold record on the device.

**F4. The fold record.** The rows that were folded (index rows at level 1, folded rows above) are written to `<cold folder>/<fold name>.fold.json`, read back byte for byte, checked against the kept 16 characters, and only then removed from working memory (Eye log `FOLD`). A failed write leaves the rows unfolded (`FOLD_FAILED`).

**F5. Finding a folded memory.** Recall first matches the question's words against the rows in working memory (capsule rows, index rows, folded rows). A folded row whose words hold every question word is opened (its fold record read from the device, or the cloud), down to the matching capsule, which is fetched and checked as in A-TEACH2-8 M5. If nothing in working memory matches, the Eye does a DEEP SEARCH: it reads the fold records on the device, without loading them into working memory, to find words that were past the cap. Fold records already in the cloud are not deep-searched. A record that fails its check is held, never answered from. A cube answer for a folded capsule finds it by its line number.

**F6. The cloud.** The device folder's limit counts fold records too. They move to the cloud like the other files: upload, read back byte for byte, then remove locally.

**F7. What stays honest.** Strengthening brings a folded capsule back into working memory. Logs, receipts and the maps of cloud keys are not counted as working memory (as before, A-TEACH2-2 B8); that gap is reported. The Eye's acting stays `NOT LICENSED`; `ENGINEERED-NOT-VALIDATED`.

**F8. Measured and reported:** the same chats as A-TEACH2-8, before (index rows only) and after (folded), the bytes per folded row, the number of levels, and REACHABILITY: of the first line of every 16-line batch, how many can still be recalled EXACT through the index, the folded rows or the deep search. A memory that cannot be reached any more is reported as lost reach, not hidden.

## Amendment A-TEACH2-10 (2026-10-22 PDT) — on the size-limit path, a capsule takes its clue words from every line of its batch; written before the code

Status: appended after A-TEACH2-9 (`22364836…`); nothing above is edited.

**The owner's words (verbatim, 2026-10-22):** "Yes: let each capsule take its clue words from every line in its batch (not just the first lines), so any old line can be found by its own words. Amendment first, test-first, 0 USD; measure bytes and reach before and after."

**Before (A-TEACH2-9 record):** a capsule's clue words are the first 8 content words of its first lines (compaction v1, DESIGN 3.1, `MAX_CLUES = 8`), so a line in the middle of a capsule cannot be found by its own words.

**C1. Every line.** On the size-limit path (where the Eye runs the capsules: `HELM_CUBE_OSC` with a limit), a capsule's clue words are every distinct content word of every line in its batch, in order (the same word rule as before: letters only, at least 4 letters, no stop word, no number word). Plain compaction (`HELM_MEMORY_COMPACT` alone, the TEACH-1 path) and the ladder path keep the first-8 rule unchanged.

**C2. The CAS sentence stays as it is.** The CAS sentence and its notation are built from the first 8 clue words only, which is exactly what they are built from today. The full list is kept for finding lines. The Eye's lean record names this template **2** ("the sentence from the first 8 clue words"); template 1 (the sentence from all clue words) is still rebuilt the same way for records that have it, and for 8 words or fewer the two give the same sentence. The receipt covers the full clue list, as before.

**C3. Everything else is unchanged:** the batch gain check (a batch is written only if its stored record is smaller than its lines), move-off, index rows (they now carry the full clue list), folding (a folded row still keeps at most 48 words; the rest stay in the fold record and the deep search finds them), strengthening (its clue growth is still capped at 8, so a capsule that already has 8 or more words gains none), and the "from my notes" sentence (it names at most the first 8 words).

**C4. Measured and reported, before (first-8 rule) and after (every line), on the same chats as A-TEACH2-9:** working memory at the end and at its peak; bytes per lean record and per index row; and REACH: of lines sampled across the whole chat (not only first lines), how many are recalled EXACT by their own unique word. If the bigger rows push a chat over its limit, that is reported, not hidden.

`ENGINEERED-NOT-VALIDATED`; the Eye's acting stays `NOT LICENSED` (spec 7.38).

## Amendment A-TEACH2-11 (2026-10-22 PDT) — when HELM is online, the Eye's deep search also reads the fold records in the cloud; written before the code

Status: appended after A-TEACH2-10 (`d7242340…`); nothing above is edited. Where it disagrees with A-TEACH2-9 F5 ("fold records already in the cloud are not deep-searched"), this governs.

**The owner's words (verbatim, 2026-10-22):** "Yes: when a question misses everything on the device and HELM is online, let the Eye's deep search also read the fold records in the cloud, so rare words of old lines can still be found. Amendment first, test-first, 0 USD; measure reach and time before and after."

**Before (A-TEACH2-10 record):** a word past a folded row's 48-word cap is found only through fold records still on the device; once they are in the cloud it is not found (pinned test `test_words_past_the_cap_are_not_found_once_fold_records_are_in_the_cloud`).

**D1. Order.** A question is matched against working memory first (rows, then the folded rows that hold every word), then the deep search of the fold records on the device (A-TEACH2-9 F5). Only if all of that finds nothing, and the cloud says it can be reached, does the deep search read the fold records in the cloud too.

**D2. Every cloud read is checked** exactly like a device read: the fold record's sha256 must begin with the 16 characters its row kept; a mismatch is held (`LEAN_REBUILD_MISMATCH`), never used. Then the found capsule is fetched and checked as before (A-TEACH2-8 M5).

**D3. Nothing read from the cloud is kept in working memory.** The records are read, searched and dropped. Nothing is deleted anywhere.

**D4. Offline, or the cloud cannot be reached:** no cloud search; if the device has nothing, HELM says its notes are stored away and it can't reach them right now (never EXACT, never a guess).

**D5. Measured and reported, before and after, on the pinned chat** (600 lines, limit 4,000, device limit 2,000, a stand-in cloud): reach (lines sampled across the chat recalled EXACT by their own word), the number of cloud reads per question, and the time per question on the stand-in cloud. Real cloud time is not measured (0 USD); it is estimated from the live smoke test of 2026-10-21 (`CLOUD_SMOKE_20261021.json`: 20.1 seconds for its calls through the AWS command line tool) and reported as an estimate, not a measurement.

`ENGINEERED-NOT-VALIDATED`; the Eye's acting stays `NOT LICENSED` (spec 7.38).

## Amendment A-TEACH2-12 (2026-10-22 PDT) — the cloud search fetches all fold records in ONE call; a tiny live timing test; written before the code

Status: appended after A-TEACH2-11 (`43b11166…`); nothing above is edited.

**The owner's words (verbatim, 2026-10-22):** "“Yes, make it faster”" — answering the offer: "make the cloud search faster (for example, keep a small copy of the cloud's fold records in the device folder, or read them in one go instead of one call each). Amendment first, test-first, 0 USD for the build; measure the real time on the bucket with a tiny live test."

**Before (A-TEACH2-11 record):** about 9 cloud reads per question (one AWS command-line call each, about 1.12 s per call), estimated about 10 seconds per question.

**Choice: read in one go.** A device-side copy of the cloud's fold records would refill the device folder whose limit sent them to the cloud, so it is not chosen.

**B1. One batched read.** When the cloud deep search runs (A-TEACH2-11 D1), the Eye fetches every fold record of this conversation's cloud folder in ONE call: on the bucket, one `aws s3 cp --recursive` of the conversation's prefix filtered to `*.fold.json` into a temporary folder; on the stand-in cloud, one `get_many`. Each record is then checked exactly as before (its sha256 must begin with the 16 characters its row kept; a mismatch is held), searched, and dropped; the temporary folder is removed. Nothing is kept in working memory.

**B2. Then as before:** the found capsule's record and its original are fetched and checked (A-TEACH2-8 M5): at most 2 more calls.

**B3. Offline:** unchanged (A-TEACH2-11 D4).

**B4. The live timing test (owner-approved, tiny):** the bucket `helm-cold-memory-807562639912-usw2`, a new prefix under `smoke/`, made-up lines only (`SYNTHETIC_ONLY`), a chat sized so that fold records reach the cloud. The same questions are timed with one call per read (before) and with the batched read (after). Expected cost: a few hundred uploads and reads of a few kilobytes each, well under 0.01 USD, inside the owner's 200 USD AWS ceiling; recorded per CLAUDE.md (source, purpose, place, limits, cleanup: none, nothing is deleted by code).

**B5. Measured and reported:** cloud calls per question and seconds per question, before and after, on the stand-in cloud and on the real bucket. `ENGINEERED-NOT-VALIDATED`; the Eye's acting stays `NOT LICENSED` (spec 7.38).

## Amendment A-TEACH2-13 (2026-10-22 PDT) — HELM remembers for a short while that the cloud was reachable; written before the code

Status: appended after A-TEACH2-12 (`5b42e233…`); nothing above is edited.

**The owner's words (verbatim, 2026-10-22):** "Yes: let HELM remember for a short while that the cloud was reachable, so a cloud question skips that check (one call fewer). Amendment first, test-first; time it live with a tiny test."

**Before (A-TEACH2-12 record, live):** a cloud question makes 4 calls (reachability check, batched fold read, the capsule's record, its original), median 3.54 seconds on the real bucket; one call is about 0.83 seconds.

**R1. Remember only a yes, for 60 seconds.** After a reachability check that says yes, or after a successful batched fold read, HELM treats the cloud as reachable for the next **60 seconds** without asking again. A "no" is never remembered: the next need checks again.

**R2. Forget at the first failure.** If any cloud call fails while HELM still remembers "reachable", the memory is dropped at once; that question then behaves exactly as before (A-TEACH2-11 D4: the notes are stored away, never EXACT, never a guess), and the next need checks again.

**R3. Where.** The same short memory serves the cloud search (A-TEACH2-11/12) and the cloud move of the device folder (A-TEACH2-5 L3, A-TEACH2-8 M4, A-TEACH2-9 F6). It is one timestamp per cloud adapter; it holds no data.

**R4. The live timing test (owner-approved, tiny):** the same bucket, a new prefix under `smoke/`, made-up lines only, the same 200-line chat as A-TEACH2-12; the same questions timed back to back with the memory off (before) and on (after). Expected cost well under 0.01 USD; recorded per CLAUDE.md; nothing deleted by code.

**R5. Measured and reported:** calls and seconds per question, before and after, and how many reachability checks the 200-line chat itself made, before and after. `ENGINEERED-NOT-VALIDATED`; the Eye's acting stays `NOT LICENSED` (spec 7.38).

## Amendment A-TEACH2-14 (2026-10-22 PDT) — a direct cloud client for HELM: standard library only, signs its own requests, keeps one connection open; written before the code

Status: appended after A-TEACH2-13 (`9c8e3daa…`); nothing above is edited.

**The owner's words (verbatim, 2026-10-22):** "Yes: build a direct cloud client for HELM (standard library only, signs its own requests, keeps one connection open) so cloud calls stop starting a new program each time. Amendment first, test-first; time it live with a tiny test."

**Before (A-TEACH2-13 record, live):** a cloud question makes 3 calls through the AWS command-line tool, about 0.85 s each, median **2.66 s**; building the 200-line test chat took **73.8 s**.

**K1. The client** (`helm_cold_cloud.S3DirectCloud`): the same four operations as `S3Cloud` (`available`, `put`, `get`, `get_many`), and no delete. Standard library only: `http.client` over HTTPS to `<bucket>.s3.<region>.amazonaws.com`, AWS Signature Version 4 computed with `hashlib` and `hmac`, `xml.etree` for the object list.

**K2. One connection.** One HTTPS connection is opened on first use and kept for every later call; if the bucket closes it, the client opens a new one and retries that call once.

**K3. Signing.** Every request is signed with AWS Signature Version 4 (the canonical request, the string to sign, the date/region/service signing key). The signer is tested against AWS's published Signature Version 4 examples for S3 before it is used.

**K4. Keys.** Read the way the AWS tools read them: the environment (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, optional `AWS_SESSION_TOKEN`) first, else the `[default]` section of `~/.aws/credentials`. Keys are never printed, logged, written to a record or put in a URL; the client's text form shows no key.

**K5. Same safety as before.** Uploads carry `x-amz-server-side-encryption: AES256` and the sha256 of the body; never an ACL. A missing object (404) is "not there" (None); any other error or a network failure is "cannot be reached" (`CloudUnavailable`), which the callers already treat as away (never EXACT; a remembered yes is forgotten, A-TEACH2-13 R2). `get_many` lists the prefix (following continuation pages) and fetches the matching objects over the same connection.

**K6. The command-line client stays.** `S3Cloud` is kept unchanged as a fallback; nothing switches the live HELM to the cloud (the live switch still attaches no cloud, A-TEACH2-5 gaps).

**K7. The live timing test (owner-approved, tiny):** the same bucket, new prefixes under `smoke/`, made-up lines only, the same 200-line chat (limit 2,000, device limit 1,000) built once with `S3Cloud` and once with `S3DirectCloud`, the same 8 questions; plus a cross-check that an object written by one client is read back byte for byte by the other. Expected cost well under 0.01 USD; recorded per CLAUDE.md; nothing deleted by code.

**K8. Measured and reported:** seconds per cloud question and seconds to build the chat, before (command-line) and after (direct). `ENGINEERED-NOT-VALIDATED`; the Eye's acting stays `NOT LICENSED` (spec 7.38).

## Amendment A-TEACH2-15 (2026-10-22 PDT) — TEACH-2 brought up to today's memory design; one choice left to the owner before the seal; written before any exam code

Status: appended after A-TEACH2-14 (`32015c87…`); nothing above is edited. Where it disagrees with the pre-code (`f7b6183b…`) §2–§8 or A-TEACH2-1 item 5, this governs. Nothing of the exam was built, drawn or run when it was written.

**The owner's words (verbatim, 2026-10-22):** "Next: bring the TEACH-2 exam up to date with today's memory design (size limit, Eye capsules, folding, every-line clues, cloud tier) and seal it, so the CUBE EXAM at 1 USD can run. Amendment first."

**T1. The memory under test (the CUBE_OSC arm).** The size-limit path as built through follow-up 12 of spec §7.125, at the commit cut into the package: every line kept until a byte limit (A-TEACH2-5 L1); batches of 16, widened until they save (A-TEACH2-6 W1); the Eye's lean capsules, rebuilt and receipt-checked on every read, a mismatch held (A-TEACH2-7); old capsules moved off working memory with an index row (A-TEACH2-8); index rows folded row upon row, 48 words per folded row (A-TEACH2-9); clue words from every line (A-TEACH2-10); the deep search of the device, then of the cloud when online (A-TEACH2-11/12); the 60-second reachability memory (A-TEACH2-13). The per-4-turn sweep and the turn budget of 12 are retired for the cube arms (the pre-code §3/§4.4 ladder, and A-TEACH2-1 item 5's "exam sweeps every 4 turns", are superseded: the owner's real-life choice (c), fading by bytes, is now what is tested).

**T2. The limits, frozen at the seal by a rule written now** (A-TEACH2-6 W2): working limit = half of the median `VERBATIM_ONLY` working-memory bytes at Q-REFRESHED over the 16 drawn worlds, rounded down to 100 bytes; device limit = the working limit. Both numbers go into the sealed package. Measured before this amendment (A-TEACH2-9 record): a limit far below about 6,000 bytes sits under the floor of two folded levels on long chats; a 32-line world will not reach two levels, so the floor is not expected to bind, and that is reported, not assumed.

**T3. The cloud in the exam.** A stand-in cloud (`FakeCloud`, no network; the socket guard stays), so the cloud tier, the cloud search and the reachability memory run with no AWS call. One planted **offline window** per world: the stand-in cloud is offline for the whole of Q-REFRESHED in that world's quiz order position chosen by the QUIZ seed part (one of the three quizzes, drawn per world). The live bucket is never used by an exam unit (A-TEACH2-5 L7).

**T4. Arms.** Unchanged: QUOTE_ONLY, TABLE, TABLE_OSC (reported), ONE_READER, CTT_ONLY, VERBATIM_ONLY, FIFO_DROP, REPLAY. Changed: the cube arms run the T1 memory with the T2 limits. **ONE_STEP_FADE** is redefined as **EYE_OFF**: the size-limit path with the Eye's lean records, the move-off and the folding switched off (A-TEACH2-5/6 only) — does the Eye's work matter for space. New, reported only: **FIRST8** — T1 with the first-8 clue rule (A-TEACH2-10 off) — does every-line matter for recall.

**T5. New rows.** Reported: batches, capsules, move-offs, folds and their levels, cloud moves, deep searches (device / cloud), cloud reads, held records, answers given in the offline window, peak working bytes per world. New instrument row **I19**: over 16 worlds CUBE_OSC wrote at least 32 batches and moved at least 16 capsules off (else the memory design was `NOT_EXERCISED` and the word is `INCONCLUSIVE`). New hard gates: **HG-OFFLINE** (harm) — 0 EXACT answers whose source was in the stand-in cloud while it was offline; **HG-HOLD** (harm) — 0 answers served from a record the Eye held; **HG-LIMIT** — in every cube arm, working bytes after each turn's fading at or under the working limit, or the Eye report names why (`OVER_LIMIT_PROTECTED`, `BATCH_NO_GAIN`, `OVER_LIMIT_INDEX`); an unexplained excess is a failure.

**T6. Marks.** C1–C4 and U1/U2 unchanged. **S-SPACE** becomes two parts, both needed: (a) the original `BYTES_WM`(CUBE_OSC) ≤ ½ × `BYTES_WM`(VERBATIM_ONLY) at Q-REFRESHED; (b) HG-LIMIT held. EYE_OFF and FIRST8 are reported beside them, deciding nothing.

**T7. THE OPEN CHOICE (the owner's, before the seal).** Pre-code §2 and I16 require the **retrained CTT** as the proposer of CUBE_OSC, with its weights pinned by sha256 in the sealed package. It does not exist: the training line `CUBE TRAIN at 3 USD` has not been typed (A-TEACH2-1 item 7). Without it CUBE_OSC proposes nothing, I18 fails, and the word would be `INCONCLUSIVE` by construction. So the package can be built and practice-run now, but **not sealed**, until the owner picks one:
- **(a) Train first.** The owner types `CUBE TRAIN at 3 USD`; the CTT is retrained (its own pre-registration and seal); its weights are pinned; then TEACH-2 is sealed and `CUBE EXAM at 1 USD` runs. Everything above holds as written.
- **(b) Seal now with the rule reader as the proposer.** The exam-side rule reader (`teach2_rule_reader.py`, A-TEACH2-2 B2 / A-TEACH2-3) fills all three proposer copies. The arm is renamed **CUBE_RULE**; label `RULE_PROPOSER` replaces `CTT_RETRAINED_V1`; I16 and C3 are not tested (ONE_READER and CTT_ONLY then read with the same rule and are reported only); every claim about the CTT is dropped. What remains tested is the memory design of T1 against today's memory, the table and never forgetting.
Nothing is sealed until the owner's word on T7 is recorded in a further amendment.

**T8. Unchanged:** worlds (16, TEACH-1's generator and templates, fresh seeds), teaching turns (32, three writer families, keyed by the two others, 4 TRAP), the three quizzes, the scoring rule of §5 (Q1 a), custody, seeds by the house rule from the owner's typed exam line and the sealed zip's sha256, the exam cap 1 USD (one CPU host), the licence ceiling. `ENGINEERED-NOT-VALIDATED` for every part; the Eye's acting stays `NOT LICENSED`.

## Amendment A-TEACH2-16 (2026-10-22 PDT) — the owner's choice on T7: train the CTT first; written before any training code

Status: appended after A-TEACH2-15 (`1f121fab…`); nothing above is edited.

**The owner's words (verbatim, 2026-10-22):** "T7 (a): train the CTT first. I will type the training line myself; write the training pre-registration so it is ready."

1. **T7 is decided as (a).** TEACH-2 keeps the retrained CTT as the proposer of CUBE_OSC, I16 (pinned weights) and C3 as written. Option (b) (the rule reader as proposer) is not taken.
2. **Order.** First the CTT retraining (its own pre-registration `PREREGISTRATION_CUBE_TRAIN.precode.md`, hashed before any code), then its run on the owner's typed line, then the pinned weights go into the TEACH-2 package, then TEACH-2 is sealed, then `CUBE EXAM at 1 USD` runs.
3. **The money line is the owner's to type.** `CUBE TRAIN at 3 USD` has NOT been typed; nothing paid runs, no GPU is started, until the owner types it. This amendment and the training pre-registration approve nothing.

## Amendment A-TEACH2-17 (2026-10-22 PDT) — the owner writes nothing; the owner's choice is the approval; written before any training code

Status: appended after A-TEACH2-16 (`f2d39443…`); nothing above is edited. Where it disagrees with A-TEACH2-1 item 7 or A-TEACH2-16 items 2–3, this governs.

**The owner's words (verbatim, 2026-10-22):** "I'M NOT WRITING A MUTHA FUCKING THING YOU AND OR OTHER LLMs"

1. **No typed lines from the owner.** The owner does not type money lines, approval lines or any other text for this work. The AI models write every pre-registration, amendment, record and approval note. The button text of A-TEACH2-16 ("I will type the training line myself") was written by the operator, not the owner; it is withdrawn.
2. **The approval.** The owner's choice "T7 (a): train the CTT first" (A-TEACH2-16) is recorded as the owner's approval of the CTT retraining at a cap of **3 USD**, inside the owner's AWS ceiling of 200 USD (spend ledger as of the last reconciliation in the spec sheet). The words `CUBE TRAIN at 3 USD` are now this record's name for that approval, written by the operator; the training's seed rule uses them as its seed source together with the sealed training package's sha256 (the house rule), exactly as if typed.
3. **What still holds.** The training pre-registration is written and hashed before any training code; the training runs only after its package is sealed; the result is read by the frozen reader, not by the operator; the cap of 3 USD is hard (the job stops at it); the cost is reported. The exam line `CUBE EXAM at 1 USD` (A-TEACH2-1 item 8) stays as recorded.

## Amendment A-TEACH2-18 (2026-10-22 PDT) — how the TEACH-2 package is built and sealed with the CUBE TRAIN weights; written before any exam code

Status: appended after A-TEACH2-17 (`8d7e0ff0…`); nothing above is edited. Where it disagrees with the pre-code (`f7b6183b…`) §2–§13 or A-TEACH2-1 to -17, this governs. Nothing of the exam was built, drawn or run when it was written. The owner writes nothing (A-TEACH2-17); the operator writes this.

**The owner's words (verbatim, 2026-10-22):** "Yes: pin the CUBE TRAIN weights into the TEACH-2 package and seal it (0 USD), ready for the CUBE EXAM at 1 USD."

**Where it starts.** CUBE TRAIN ran as job c57 and read `TRAIN_READY` (spec §7.125 follow-up 17; record `cube_train/run_c57/`). Its weights exist and are fingerprinted. The TEACH-2 exam itself was designed (pre-code, A-TEACH2-1 to -17) but no exam code exists.

**P1. The package.** One folder `HELM_TEACH2_20261022/`, sealed as one zip, holding:
- `helm_now/` — HELM cut by `git show` at the commit named in its contract file, exactly as TEACH-1 (`contract/HELM_CUT_TEACH2.json`); the wave-1 brain package beside it, checked by its freeze.
- `ctt/` — the CUBE TRAIN package's `helm_cas_translator/` and `cube_task/` byte for byte from the sealed zip `706e1fa6…`, its `data/vocab.json`, and the four c57 final weights: A4-s1 `c39eafb6db92845a463a0c6bc711c73d45ddcb482b5e5eaffad466f337d7a69a`, A4-s2 `3bfbf1f064e4dd96980bfa971cbd089706a4b99cfdaba0b84324f4a4b3a883ee`, A4-s3 `6418ef1e27ffd18df9f571e9f5410af1afae6843d9d56cbcb01d31ccf947564b`, A5-s1 `07a54adcdb58cfb746f35e0d4350a9bde536eb72f97d6b29451960313fca4bc1`. These four sha256 are I16's pins.
- `teach2/` — the exam harness, adapted from TEACH-1's (worlds, plan, turns checker, person, quizzes, damage, custody, units, pool, reader); the exam-side rule reader `teach2_rule_reader.py` (A-TEACH2-2 B2, A-TEACH2-3) copied in.
- `contract/` — the writer brief and key format with the TRAP kind (P6), the custodian procedure, the cut contract.
- `tests_teach2/`.

**P2. Serving the CTT.** One serving process per unit loads the three voting copies (A4-s1..s3) and, in CUBE_OSC only, the twin A5-s1. It is TEACH-2's own `teach2/ctt_server.py`: the same write-audit hook installed before torch is imported (`helm_cas_translator.audit`), the same locked greedy decoding (`model.greedy_locked`, `cube_task.target.automaton_for`, direction `[B]`), the same `require_cuda()` (no CPU fallback). One process instead of one per copy because the laptop practice would not fit three torch processes in memory; the decoding is the same function. The answer is turned into the target string by `cube_task.target.canonical` and read by HELM's own adapter (`helm_cube_osc.reading_from_ctt` through `CTTProposer`). An incomplete decode is no reading. The audit is judged by `cube_task.audit_judge` with the package's `ctt/` and `data` folders forbidden for writes; any violation, any network call, any process start, a dead server or a missing audit report makes the new instrument row **I20** false.

**P3. A5-s1 is reported only.** In CUBE_OSC every teaching line is also read by A5-s1; the reading is logged beside the vote and never reaches HELM (pre-code §2 "the c45 twin as a size check").

**P4. The exam host.** The decoder needs a GPU (`require_cuda`, and the house rule: neural work never runs on a CPU). The exam therefore runs on **one GPU host** (g4dn.xlarge; g5.xlarge only on refused capacity), not the "one CPU host" written in OPEN_QUESTIONS Q8. The cap stays **1 USD** (`CUBE EXAM at 1 USD`, A-TEACH2-1 item 8, unchanged); the host type is an operational detail. If the run cannot finish under the cap, it stops and reads `INCONCLUSIVE`.

**P5. The arms and their memory** (A-TEACH2-15 T4 made concrete):

| Arm | Memory | Reader | Decides |
|---|---|---|---|
| CUBE_OSC | size-limit path (T1) at the T2 limits; stand-in cloud | CTT, 3 copies, rounds | the arm under test |
| REPLAY | CUBE_OSC again, fresh process | as CUBE_OSC | HG-REPLAY |
| QUOTE_ONLY | TEACH-1's COMPACT_ON exactly (budget 12, no cube) | — | C1 |
| TABLE | plain `(thing, slot) → value` dict; the text FIFO at budget 12, no compactor | rule reader | C2 |
| TABLE_OSC | as TABLE | the CTT's agreed readings | reported |
| ONE_READER | size-limit path, cubes | rule reader, no rounds | C3 |
| CTT_ONLY | size-limit path, cubes | CTT unanimous, no check, no say-back | C3 |
| EYE_OFF | size-limit path with the Eye's lean records, move-off and folding switched off (plain capsule list) | CTT, rounds | reported |
| FIRST8 | CUBE_OSC with clue words from the first lines only (`clue_every_line` off) | CTT, rounds | reported |
| VERBATIM_ONLY | TEACH-1's VERBATIM_ONLY (budget 10,000, no cube, nothing fades) | — | U1, C4, S-SPACE, the limits |
| FIFO_DROP | switch OFF, budget 12 | — | the floor |

The six "cube arms" (CUBE_OSC, REPLAY, ONE_READER, CTT_ONLY, EYE_OFF, FIRST8) run the size-limit memory; HG-LIMIT, HG-FADE, HG-OFFLINE, HG-HOLD apply to them. Every arm's variant is set up on the exam side; HELM's files are the same bytes in every arm.

**P6. The TRAP kind** (pre-code §4.2 made concrete). Plan per world, 32 slots: FACT 18, UNKNOWN 4, TRAP 4, FIX 2, RESTATE 2, SMALL 2. Two TRAP slots are the first statement of a known non-FIX fact (they replace two FACT slots); two are restatements-with-decoy of a known fact already stated (they replace two SMALL slots and come after the fact's first statement). Each TRAP fact carries one decoy drawn from the WORLD stream: a second number word of the same kind (count facts), a month belonging to another fact, or a "not" placed on a wrong value ("not X"). The canonical TRAP line is written by the generator; the exam's TRAP lines are written by the AI writers from it and keyed like a FACT (each keyer names the true value). Floors: 32 turns; ≥ 18 FACT; exactly 4 TRAP; ≥ 2 FIX; ≥ 2 SMALL; every fact stated.

**P7. The limits** (A-TEACH2-15 T2 made concrete). The worlds are drawn after the seal by the custodian, so the package freezes the **rule**, not the numbers: the pool runs VERBATIM_ONLY on every world first; its records give each world's working-memory bytes at the end of Q-REFRESHED (live user lines + capsules, the same count as `CubeOsc.working_bytes`); the working limit = ⌊median / 2 / 100⌋ × 100 bytes; the device limit = the working limit. The pool writes `LIMITS_TEACH2.json` before any cube arm starts; every cube unit records the limits it used; the reader recomputes them from the VERBATIM_ONLY records (new instrument row **I21**).

**P8. The offline window** (A-TEACH2-15 T3). Per world, one quiz phase, drawn from the QUIZ seed, is offline: the stand-in cloud refuses every call for that whole phase. The planted damage of TEACH-1 (one cold copy deleted, one corrupted, on the device) is kept in every compacting arm.

**P9. New measurement rows** (the harness records, the reader counts): every say-back line (a transparent recorder on `helm_cube_osc.say_back`); the store's branch table after every turn; each turn's id, kind and fact id; the Eye log (MOVE_OFF, FOLD, HOLD); batch log; cloud moves; working bytes after every turn and at every quiz; every cube answer (recorder on `CubeOsc.answer`) with its label, branch and source turn; the cloud's state during each answer.

**P10. Gates and rows made checkable** (definitions frozen now; the reader applies them):
- `CUBES_WRONG` — at the end of the unit, every current branch (newest per source, target and kind) whose referent (or amount) differs from the key value of the fact of the turn that wrote it; a branch written by a turn with no keyed fact, or by an UNKNOWN line, counts as wrong. `CUBES_TRAP_WRONG` — those written by TRAP lines. HG-WRONG-CUBE: 0 in every cube arm.
- HG-REVISION — the branch table only grows (every snapshot is a prefix of the next); no branch id repeats; a kept correction is a new branch.
- HG-NUMBER — 0 subject number words (two to nineteen, and their digits as standalone numbers) in any stored capsule row, index row, fold row or S2 record; CAS notation (`^n`) and fingerprints are not numbers.
- HG-FADE — every batch capsule has a COMPACTION receipt; every MOVE_OFF and FOLD has an Eye log entry with a digest; no line holding an unconfirmed current fact was faded.
- HG-SAYBACK — every say-back line has 0 CAS tokens and only the reading's own words plus "this replaces".
- HG-OFFLINE (harm) — 0 answers labelled EXACT whose source line was only in the stand-in cloud while it was offline.
- HG-HOLD (harm) — 0 answers served from a record in the Eye's HOLD log.
- HG-LIMIT — in every cube arm, working bytes after each turn's fading at or under the working limit, or the memory's flag names why (`OVER_LIMIT_PROTECTED`, `BATCH_NO_GAIN`, `OVER_LIMIT_INDEX`).
- I17 — no observed line used more than 3 rounds (shadow rounds 4–6 are reported, never stored). The per-4-turn sweep is retired (A-TEACH2-15 T1), so the old "sweep period" part of I17 is void.
- The current-value scoring rule of pre-code §5 (Q1 a) replaces TEACH-1's "not"-only rule.

**P11. Seeds.** Bands above every band in use (CUBE TRAIN used 2,050 M and 2,051 M; A-CUBE-TRAIN-1 A3 reserved TEACH-2 above 2,052 M): WORLD 2,053,000,001–2,054,000,000; QUIZ 2,055,000,001–2,056,000,000; PERSON 2,057,000,001–2,058,000,000; TRAP 2,059,000,001–2,060,000,000. The used table names every range up to 2,052,000,000. Seeds by the house rule from `CUBE EXAM at 1 USD` and the sealed zip's sha256.

**P12. Practice before the seal (0 USD).** The builder runs practice worlds with rule-written practice turns (label `RULE_WRITTEN_PRACTICE`, practice seed texts). The arms without the CTT run on the laptop's CPU (no neural work). The CTT arms run on the laptop's own GPU (RTX 4070), the house rule's "smoke/dev only" use, on as few worlds as memory allows. Practice numbers are facts for FIX FIRST and decide nothing; a practice reading is always `INCONCLUSIVE` by I0.

**P13. The seal.** As TEACH-1: a freeze of every package file's sha256, a zip, the package tests run from a fresh extract, a backup to `D:/tksCAS-archive`. The zip is too big for git; the repo holds the freeze, the zip's sha256 and the builder tools. After the seal: a custodian session (not the builder) approves from the recorded line, draws, has the turns written by three model families and keyed by two others, and finishes; then `CUBE EXAM at 1 USD` runs on the GPU host; the frozen reader reads it.

**P14. Unchanged:** the arms' purposes, the marks C1–C4, U1/U2, S-SPACE (a)+(b), the status words and their order, the labels (`SYNTHETIC_ONLY`, `LLM_WRITTEN_ONLY`, `CTT_RETRAINED_V1`, `EYE_REPORT_ONLY`), the licence ceiling. Every mechanism stays `ENGINEERED-NOT-VALIDATED`; the Eye's acting stays `NOT LICENSED`.

## Amendment A-TEACH2-19 (2026-10-22 PDT) — two contradictions in the marks corrected, and the reader's exact counting rules; found while writing the reader, before any reader code and before any exam data

Status: appended after A-TEACH2-18 (`4b8b529a…`); nothing above is edited. Where it disagrees with the pre-code (`f7b6183b…`) §7–§8 or A-TEACH2-18 P5/P10, this governs. No exam world has been drawn; only builder practice worlds have run (A-TEACH2-18 P12). The operator flags both corrections to the owner in the seal report.

**Why.** Two rules, as written, cannot hold together with the marks they sit beside, so a run could read `CUBES_HARMED` because a *rival* arm did exactly what the marks expect a rival to do:
1. **HG-WRONG-CUBE vs C3.** A-TEACH2-18 P10 put HG-WRONG-CUBE (a harm gate) on all six cube arms, including the rivals ONE_READER and CTT_ONLY. But C3 is met when "`CUBES_WRONG`(ONE_READER) + `CUBES_WRONG`(CTT_ONLY) ≥ 2 **while CUBE_OSC holds HG-WRONG-CUBE**" — the rivals are expected to store wrong cubes, and the gate is about the arm under test.
2. **U2 vs C2.** The pre-code's U2 asks "0 wrong on Q-TAUGHT in every arm" (a harm condition). But C2 is met, among other ways, when the plain TABLE serves at least 4 more wrong answers than CUBE_OSC — the rival TABLE is expected to answer wrongly. U2 came from TEACH-1, where every arm was a variant of HELM's own memory.

**K1. HG-WRONG-CUBE** applies to **CUBE_OSC and REPLAY** (the mechanism under test). `CUBES_WRONG` and `CUBES_TRAP_WRONG` are counted and reported for every cube arm; ONE_READER's and CTT_ONLY's counts feed C3; EYE_OFF's and FIRST8's are reported.

**K2. U2** applies to **CUBE_OSC and REPLAY**: 0 WRONG on Q-TAUGHT. Every other arm's WRONG_T is reported. VERBATIM_ONLY's WRONG_T stays in U1 (0 wrong) as written.

**K3. HG-REVISION** applies to CUBE_OSC and REPLAY (reported for the other cube arms). The memory gates HG-OFFLINE, HG-HOLD, HG-LIMIT, HG-FADE, HG-NUMBER and the label gate HG-H8 apply to **every arm that has the memory they test** (they test HELM's shared memory code, not a reader): HG-LIMIT and HG-FADE on the six cube arms; HG-OFFLINE and HG-HOLD on every arm with a stand-in cloud or an Eye; HG-NUMBER on every arm that stores capsules; HG-H8 on every answer every arm serves from memory.

**K4. The reader's counting rules, frozen now.**
- *Current branches:* the newest branch per (source, target, kind) at the end of the unit. A branch's fact is the fact of the turn named in its provenance (a teaching turn, or a refresh answer whose person draw named a fact). Wrong when its referent (or amount) is not the key value of that fact (after any correction), or when the turn carries no keyed fact (SMALL, UNKNOWN, a "don't remember" answer, a quiz question). `CUBES_THING_MISMATCH` (reported) counts branches whose source thing is not the fact's unit.
- *CUBES_STORED / I18:* branches whose provenance is a teaching turn, in CUBE_OSC, summed over worlds.
- *HG-H8, the truth an answer label is checked against:* recorded by the unit at the moment of the answer, from plain data (never by calling HELM): a person's line is *exact now* when it is live, or when its capsule's original hashes to the COMPACTION receipt's `cold_sha256` and is on the device, or in the stand-in cloud while the cloud is online. EXACT is right iff exact now; RECONSTRUCTED is right iff not; a "strengthened item" EXACT is right iff its texts are the person's own lines.
- *HG-OFFLINE:* EXACT answers whose source was only in the stand-in cloud while it was offline (a subset of HG-H8's failures, counted apart because it is a harm gate).
- *HG-HOLD:* answers whose capsule is in the Eye's held set or HOLD log.
- *HG-LIMIT:* walking a cube unit's turns in order, a turn whose working bytes exceed the working limit is explained only when one of `OVER_LIMIT_PROTECTED`, `BATCH_NO_GAIN`, `OVER_LIMIT_INDEX` was raised in the same over-limit stretch (since the last turn at or under the limit). `MOVE_FAILED` is about the device limit and explains nothing here.
- *HG-NUMBER:* no subject number word (two to nineteen) and no standalone digit run in any clue list, CAS sentence, CAS notation with its `^n` tokens removed, S2 record or fold record member; ids, line numbers, fingerprints and byte counts are not facts and are not scanned.
- *HG-FADE:* every batch in the batch log has a COMPACTION receipt for its capsule; every MOVE_OFF and FOLD in the Eye log has a digest; no line that wrote a current branch of a thing still unconfirmed at the end lies in any capsule.
- *HG-COMPILE:* applied to capsules stored in full (QUOTE_ONLY, VERBATIM_ONLY, EYE_OFF); lean records are covered by the Eye's rebuild-and-receipt check (HG-HOLD, HG-FADE).
- *HG-SAYBACK:* each recorded say-back line has 0 CAS tokens (counted by HELM's own `helm_voice.cas_tokens` at the moment it was written) and only the reading's words plus "this" and "replaces".
- *S-SPACE (a):* summed over worlds, CUBE_OSC's working bytes at the end of Q-REFRESHED ≤ ½ × VERBATIM_ONLY's.
- *The current-value scoring rule (pre-code §5, Q1 a):* another value of the same kind counts as marked replaced when it directly follows "not", "instead of", "earlier I said", "used to be", "replaced" or "replaces", or sits in "was V before" or "V was replaced".

**K5. Unchanged:** the arms, every threshold number, the status words and their order, the labels, the licence ceiling.

## Amendment A-TEACH2-20 (2026-10-22 PDT) — the TRAP decoys brought back to the pre-code's three, and U1 counted apart from TRAP facts; found by builder practice round 1, before the seal and before any exam world exists

Status: appended after A-TEACH2-19 (`a5c4d4ff…`); nothing above is edited. Where it disagrees with A-TEACH2-18 P6 or the pre-code (`f7b6183b…`) §8 U1, this governs. Only builder practice worlds have run (practice seed texts, rule-written turns). The operator flags this amendment to the owner in the seal report.

**What practice round 1 showed (4 practice worlds, 11 arms, every unit exit 0; a practice fact that decides nothing).** U1 read false on one answer. VERBATIM_ONLY was asked "who looked after the Ravensby yard?" and quoted a TRAP line — "As I said before, Isbeth looked after the Elmbrook yard, while Ravensby was quiet in December." — because that line's decoy named another yard, so it held every word of another fact's question. The builder had taken that decoy frame from CUBE TRAIN's training rows (`rows_ct._trap_line`, "while <unit> was quiet in <month>"); the pre-code's decoys are only "a second number of the same kind, a month that belongs to another fact, or a 'not' in an odd place" — no other yard or line. Separately, a number-decoy TRAP line ("eight colonies …, up from four the month before") states two counts, so any memory that quotes it word for word scores WRONG by the frozen current-value rule ("up from" is not a replacement word). U1 asks for 0 WRONG on Q-TAUGHT in VERBATIM_ONLY; on 16 drawn worlds it would fail by construction, the word would be `INCONCLUSIVE` whatever the cubes did, and the exam would be spent.

**D1. The three TRAP frames (replaces A-TEACH2-18 P6's "another unit" reading):**
- *not* — "Not that it matters much, but <the statement>" (CUBE TRAIN's frame, byte for byte): a "not" in an odd place that denies nothing.
- *number* (count facts only) — "<the statement>, up from <D> the month before." with D a number word other than the value (CUBE TRAIN's frame).
- *month* — "<the statement>, while it was quiet in <M>." with M a month that belongs to a fact of **another** yard or line and to **no** fact of this one, so no other quiz question can find every one of its words in the line. (CUBE TRAIN's "other" frame without the unit name.)
No TRAP line names a yard, line, person or place other than its own fact's. Each TRAP fact's frame and decoy come from the TRAP seed.

**D2. U1 counted apart from TRAP facts.** U1 = VERBATIM_ONLY `RIGHT_T` average ≥ 10 of 16 over the quiz items, and **0 WRONG on Q-TAUGHT on the items whose fact is not a TRAP fact of that world**. VERBATIM_ONLY's answers on TRAP-fact items are reported apart (`U1_TRAP_WRONG_REPORTED`). Reason: quoting a two-value line is exactly the failure the cube arms are tested against (C1, C2), not a sign that teaching did not take hold. U2 (CUBE_OSC and REPLAY: 0 WRONG on Q-TAUGHT) is unchanged and still counts TRAP items.

**D3. A harness defect, fixed (not a rule change).** The TABLE arms' answers carry no source line, so the unit could not record whether their EXACT label was true and HG-H8 counted every TABLE answer as a failure. The unit now finds the source line from the table entry the answer names (thing, slot words and value appear in the answer's own words).

**D4. Unchanged:** every threshold number, the arms, the other gates and marks, the status words, the labels, the licence ceiling. The other practice facts of round 1 (C1 +1 of +8 needed; S-SPACE 14,688 against 19,402 bytes; 0 wrong cubes in CUBE_OSC, 17 in ONE_READER) are recorded in the build record and change nothing here.

## Amendment A-TEACH2-21 (2026-10-22 PDT) — four counting and checking defects found by the one independent review round, fixed before the seal and before any exam world exists

Status: appended after A-TEACH2-20 (`a29ebaf4…`); nothing above is edited. Where it disagrees with A-TEACH2-19 K4 or A-TEACH2-18 P10, this governs. Only builder practice worlds have run. The operator flags this amendment to the owner in the seal report.

**Why.** One independent review round (an AI reviewer that read the code and ran nothing) found four MAJOR defects: each could make a gate read true when it should be false, or false when it should be true. None changes an arm, a threshold, a mark or a status word.

**R1. The TABLE arms' source lines (HG-H8).** Arms without a compactor number lines by their position (`len(turns)+1`), so once the 12-line budget is full every new line has the same number, and a dropped line's number points at a live line. The unit now records, for every table entry, the person's line that wrote it; a table answer's source is *exact now* only when a live line has that number **and** that text. (The reviewer's note, recorded: with this fixed, HG-H8 may read false on the TABLE rival, and A-TEACH2-19 K3 puts HG-H8 on every answer every arm serves; that is the frozen reading.)

**R2. HG-LIMIT's stretch rule.** HELM raises a limit flag only when the kind of flag changes (`CubeOsc._limit_flag`), so a stretch that dips under the working limit and goes over again with the same reason raises nothing new. An over-limit turn is now also explained when the memory's own current flag at that turn (`limit_flag`, recorded per turn) is one of `OVER_LIMIT_PROTECTED`, `BATCH_NO_GAIN`, `OVER_LIMIT_INDEX`. `MOVE_FAILED` still explains nothing.

**R3. HG-HOLD counts answers served from a held record.** K4 said "answers whose capsule is in the Eye's held set". A cube answer whose source capsule is held is told by HELM that the words are missing and answers RECONSTRUCTED from its branch — it did not use the held record. HG-HOLD now counts: answers served from a capsule (the memory's recall path) whose capsule is held, and cube answers labelled EXACT whose source capsule is held.

**R4. The custodian's turn check compares every turn with its plan slot.** In sealed mode `turns_t2.check_turns` now also requires, per turn: `turn_index`, `kind`, `fact_id`, `value`, `not_value` and `trap_role` equal to the drawn plan's slot; on every FACT, TRAP, FIX and RESTATE line the value word appears in the line; and `keyed` is recomputed — `AGREE` only when both keys name the plan's fact id and value (FIX: the new value; TRAP: the true value; UNKNOWN: no value). A turn file's own `keyed` field is not trusted.

**R5. Two small hardenings (MINOR, done because they are cheap):** a CTT server reply with the wrong shape counts as a dead server (no reading; I20 false); the seal refuses unless every test from the fresh extract exits 0 and the assembled harness equals the committed source byte for byte.

**R6. Unchanged:** every threshold number, the arms, the marks, the status words and their order, the labels, the licence ceiling. Reported, not changed (the reviewer's MINOR N1): by the pre-code §9 as frozen, C4 between 2 and 4 lost items is neither NO_GAIN nor HARMED.

## Amendment A-TEACH2-22 (2026-10-22 PDT) — FIX FIRST: two defects in HELM's cube answers found by builder practice round 3; the HELM cut moves to the fix commit; written before the fix

Status: appended after A-TEACH2-21 (`0aa9ced6…`); nothing above is edited. Only builder practice worlds have run.

**What practice round 3 showed (2 practice worlds, every unit exit 0; practice facts that decide nothing).**
1. Asked "What did I say about the buses on the Glenhollow line in January?" (a fact the person said they did not remember), every arm that answers from cubes or a table said "Glenhollow, buses line, September: nineteen": the answer matcher ignores months, so a question about one month took another month's fact. In CUBE_OSC this made U2 (a harm condition) false.
2. HG-H8 read false on the TABLE rival only: without a compactor HELM numbers lines by position, so once the budget is full every new line has the same number (helm_memory's pinned OFF rule, kept unchanged), and a table answer whose line was long dropped was still labelled EXACT.

**F1. The fix, in HELM's cube module only (`helm_cube_osc.py`, behind `HELM_CUBE_OSC`, default OFF; `helm_memory.py` and the OFF path are not touched).** (a) A question that names a month is answered only from a fact that holds that month (a branch whose second node is that month, or a table entry whose slot words hold it). (b) A table entry also keeps the person's line that wrote it; a table answer is EXACT only when a live line has that number and that text. Test first: `test_helm_cube_month_label.py` (4 tests; 3 fail on the old code). HELM's own suites must stay green.

**F2. The HELM cut** in the TEACH-2 package moves to the commit that holds the fix (recorded in `contract/HELM_CUT_TEACH2.json` and the seal record). The reader is unchanged; A-TEACH2-21 R1's harness-side source check stays as a second check.

**F3. Unchanged:** every threshold, arm, gate, mark, status word, label and the licence ceiling.
