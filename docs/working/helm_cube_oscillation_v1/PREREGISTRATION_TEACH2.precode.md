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
