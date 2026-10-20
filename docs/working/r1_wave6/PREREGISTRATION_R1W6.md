# PREREGISTRATION_R1W6 — HELM-R1 wave 6, the "PAIR WAVE": the wide recipe brain tested alongside HELM's other parts

Written 2026-10-19 (Pacific) by the wave-6 builder session (Claude), BEFORE any wave-6 code. The pre-code copy is
`PREREGISTRATION_R1W6.precode.md` (its sha256 in `PREREGISTRATION_R1W6.precode.sha256`). Every later change is a
numbered deviation in section 14, never a silent edit. One scored attempt plus at most one plumbing retry. A miss on
any row is a finding. **NOT LAUNCHED. No ledger hold. No spend.** Claim ceiling now `SYNTHETIC_ONLY`; if earned, the
ceiling of section 12.

Claude is not the research governor. The status word comes only from the frozen reader program (raw counts, frozen
thresholds, controls, hard gates). A failed hard gate is a FAILURE, never "PASS with caveats". The thresholds below
are the builder's PROPOSED values; the owner's line accepts or rejects the whole sealed package.

## 0. What the owner ordered, plainly

The coordinator's build order (relaying the owner's line of work after RB-W1T v3, job c47): build and seal HELM-R1
wave 6, the "PAIR WAVE": the wave-5 brain and switches PLUS the switch `WIDE_BRAIN` (licensed reader first; the wide
path only where the licensed one cannot bind), with EYE_SCAN (wave 4) and EYE_PAIRING (wave 5) available. Nothing
paid runs until the owner's word. The expected word is **`PAIR WAVE at 1 USD`** (section 13).

Why now. RB-W1T v3 (job c47, spec sheet 7.89) read `WIDE_BRAIN_EARNED_KEEP`: on 128 real recipes the wide brain fully
learned 92 of 96, gave 0 wrong answers and left HELM unchanged with its switch OFF. That made it a **candidate** main
brain, "pending a wave with the switches (a pair-word wave against the other parts)". It also carried a caution:
on 19 of the 23 recipes whose source does not settle the answer, the wide brain still gave a number. Wave 6 is that
pair wave, and it adds a mark for the caution.

Plain words used below. **Key** = the right answer, worked out from the source by a fixed written rule, never by
running HELM. **UNDETERMINED key** = the rule cannot settle the answer from the source. **ASK** = HELM asks instead of
answering; on an answerable item this is honest but not helpful, never WRONG. **Pair word** = how two parts work
together, read from four arms (both on, each off, both off) by wave 3's frozen rule.

## 1. Gate answer

HELM ability advanced: a brain that learns real recipes (open vocabulary, exact fractions, up to 10 ingredients)
working INSIDE HELM next to its other parts (cube store, English reader, triad, voice, the Unity Eye's self-scan and
its pairing drive loop). Before: the wide brain was tested alone on real recipes (c47) and its OFF switch was checked
on two exam families. After: the same brain with every wave-5 part on, on the wave-5 exam families (no harm), on a
fresh real-recipe exam (learning, safety, honesty, and the new caution), on a fresh conversation exam where real
recipes are taught in multi-turn English, and in the drive-loop world with one item kind that needs the wide brain;
six pair words. Controls lacking the mechanism: FULL (WIDE off), ALWAYS_ASK (no brain), the wide brain with learning
disabled, the wide brain without the new caution rule. What it will not show: anything about real kitchens, typed
English in general, or the transformer.

## 2. What is under test

- **HELM's code:** the merged live code on `claude/project-thread-pmbzd6` (`helm_brain_wide.py`, `helm_wide_turn.py`
  — WIDE_BRAIN switch, PRs #380/#389/#392; reader v1.1 with STOCK_FRAME, PR #378; lexicon_v3, PR #386; chat fixes,
  PR #384). It is reused from the sealed RB-W1T v3 package (`helm_now/`, cut at `65b86282`), NOT cut again. A build
  check (`build/check_cut_w6.py`) proves that every file of that cut is byte-identical to the thread head at the time
  of sealing (`git show <head>:<path>`), and records the head commit.
- **The brain and switches of wave 5:** the licensed wave-1 recipe brain (v3, `31f97d67…`), wave 3's live harness and
  switch adapters (ENGLISH_IN, VOICE, TRIAD, CUBE_STORE; wave 3 v3 `152bca2a…`), wave 3's cascade (CASCADE; in the
  drive-loop jobs only), wave 3b's English-64 / Faces-64 generator (`a4f82556…`), wave 4's EYE_SCAN session harness
  (`4bd0d740…`), wave 5's EYE_PAIRING drive loop, jobs and world generator (`b6598687…`), wave 2's work pool
  (`21ad185d…`), RB-W1T v3's exam frame, draw, mapping, keys and scoring (`3a8ae37e…`). Each is shipped BESIDE the
  package, checked by its freeze before import, and never edited.
- **The one new piece of brain behaviour (built in this package, not in HELM's files): the UNSETTLED_ASK rule.**
  When the wide path is about to answer "how much X can we make?", it first looks at the ingredient names of X in
  the wide brain. If two of them end in the same head word (the last word, folded for plurals by RB-W1T's frozen
  `head_norm`; for example "butter" and "melted butter"), the source does not settle how much of that ingredient one
  batch needs (one pool or two?), so the brain ASKS which is meant and writes nothing (status
  `CLARIFY_WIDE_UNSETTLED_SAME_NAME`, a plain-English question). It is installed for the duration of a unit by
  wrapping `helm_wide_turn._wide_question` (restored after; a test proves the restore and that HELM's file is
  untouched). A static test proves the rule exists and fires. Disclosure: this rule mirrors the structural condition
  of X-REAL's frozen key rule K-R (two lines sharing a HEAD makes K-R UNDETERMINED); it is written from the public key
  rule, never from any exam item, and it reads the brain's own names, not the key's HEADs. Zero amounts are already
  refused by the wide brain (`REFUSED_ZERO_REQUIREMENT`).
- **Arm FULL+WIDE (the candidate) = WIDE on + UNSETTLED_ASK on.** Arm `FULL+WIDE_NOASK` = WIDE on without the rule =
  exactly the c47 build (reported, so the owner sees what the rule changes).

## 3. Switches

| Switch | ON | OFF |
|---|---|---|
| WIDE (new here) | `HELM_WIDE_BRAIN=1` for the unit (HELM's own switch): licensed path first, the wide book only where the licensed path cannot bind; plus UNSETTLED_ASK | the switch unset: the wide modules are never imported |
| EYE_SCAN (wave 4) | the U3 Eye on the live path: trigger FULL, REPORT_AND_WHISPER, wave 4's receiver | off |
| EYE_PAIRING (wave 5) | the Eye's learned 7 x 7 pairing + count-ratio attention in the idle drive loop (wave 5's candidate, Q5/Q6 as accepted at c40) | wave 3's DRIVE_LOOP (seeded random pairing) |
| CUBE_STORE, ENGLISH_IN, TRIAD, VOICE | wave 3's live adapters, unchanged | wave 3's off adapters |
| CASCADE | drive-loop jobs only (wave 5's K1 kind) | — (not toggled in wave 6) |

ENGLISH_IN switches the licensed English reader and the faces reader exactly as wave 3's adapter does; the wide
reader belongs to WIDE and is not touched by ENGLISH_IN (deviation D-W6-2; the pair word will show whether this
matters).

## 4. The exams (all fresh ones drawn blind by a separate custodian; the builder sees hashes and counts only)

### 4.1 X6_E64 and X6_F64 — the wave-5 live families at wave-5 sizes (no harm, pair words)
Wave 3b's sealed generator `r1w3b.gen64` (64 items each, the ladder), two fresh seeds. Text rule = wave 3b's
(R1W3-A1 + T3b), forbidden set = wave 5's (packaged strings, wave 3 / 3b / 5 fixtures, X1, X2, X3 language files)
PLUS X4's and X5's English-64 / Faces-64 (spent at c39 / c40), each pinned by sha256, PLUS wave 6's practice
fixtures. A text hit steps the seed slot by program (s <- s + 1 inside the band), recorded.

### 4.2 X6_PAIR — wave 5's drive-loop world at wave-5 size (no harm, Eye-pairing gates)
Wave 5's generator `r1w5.gen_x5pair.make_life` over RB-I3's World (byte-identical), unchanged job map (K1 PLANT /
CASCADE, K2 STALE / CUBE_STORE, K3 NOTE / ENGLISH_IN, K4 FACE / TRIAD, K5-K7 none). Families A_STATIONARY, B_DRIFT,
C_NULL, 3 lives each, plus 4 backlog lives for the live exams' EYE_PAIRING arms (LIVE_E64, LIVE_F64, LIVE_CONV,
LIVE_REAL). No wave-5 job runs through HELM's live loop, so WIDE has no code path here; the family is run for the
owner's no-harm mark and for the Eye-pairing hard gates with WIDE on.

### 4.3 X6_PAIRW — the same world with one kind bound to the wide brain (pair words with the drive loop)
Family A_STATIONARY, 3 lives, RB-I3's World, with ONE change to the job map: kind K7's job is **REAL** (instead of
RB-I3's ratio job): a real recipe from the custodian's PAIRW pool (section 4.6) is taught to a FRESH live loop with the
arm's switches by RB-W1T's lesson scheme (one "We made 1 N from ... and ran out of X." per ingredient), given fresh
amounts ("We have ..."), and asked "How much N can we make?". The job's answer = the yield and the recipe line of the
limiting ingredient (mapped by RB-W1T's A-W-1 rule through the brain's own lesson records); the key = X-REAL's K-R on
the source lines and the pantry lines. With WIDE off the licensed brain asks, so K7 is unsolvable; every other kind is
wave 5's. So WIDE, CUBE_STORE, ENGLISH_IN and TRIAD each own one kind (about 1/7 of items).

### 4.4 X6_REAL — 128 real recipes (learning, safety, honesty, caution)
RB-W1T v3's exam exactly (frame = X-REAL's pinned recipe frames `FRAME_R_PG.jsonl` `c983e065…` and `FRAME_R_WB.jsonl`
`6a0d7cc1…`, 2-10 lines all parsed; strata C23 / C46 / C710 x INTEGER / FRACTION / MIXED; quotas 14 / 15; frozen
multipliers; the mapping; K-R keys; representability), drawn by RB-W1T's own `draw` with a fresh seed, excluding by
id and by equal text: X-REAL's 128 used recipes, the c46 exam's 128, the c47 exam's 128 (ids from the custodian's
sealed handoff `RBW1T_V3_SEALED_20261020T025737Z.json`, field `drawn_frame_ids_sorted`, ids only), RB-W1T's two
published practice draws (`PRACTICE_DRAW_RBW1T.json`, `PRACTICE_DRAW_V2.json`), and wave 6's own published practice
pools (section 9). The REAL draw is made first; the CONV and PAIRW pools are drawn after it and exclude it.

### 4.5 X6_CONV — real recipes taught through English in multi-turn dialogue (64 dialogues)
New generator `r1w6/gen_conv.py` (standard library only; keys from written rules). Each dialogue holds ONE real recipe
from the custodian's CONV pool, taught by RB-W1T's lesson sentences as English setup turns, with a small-talk turn
between teaching and the scored turns; then the family's turns. The families follow wave 3b's English-64 and Faces-64
(same family names with prefix R / S, same rungs, about half the keys ASK so pair words have room); phrasings, faces
pools and question forms are imported from the sealed wave-3 / 3b generators where they exist; the bodies are
re-stated because wave 3b's bodies use the toy recipe table and structured teaching (D-W6-3). Frozen composition:

| Family | Rung | Key | n |
|---|---|---|---|
| R1_STOCK_THEN_ASK | PLAIN | ANSWER | 6 |
| R1_STOCK_THEN_ASK | UNKNOWN_INGREDIENT (the stock also names an ingredient not in the recipe) | ASK | 4 |
| R1_STOCK_THEN_ASK | UNIT_CHANGE (one ingredient restated in a unit of the other kind: volume <-> weight; no exact factor) | ASK | 4 |
| R2_ABSENT_THEN_ASK | PLAIN ("... but we've run out of X") | ASK | 4 |
| R3_QUESTION_FORMS | PLAIN (wave 3b's two other question forms) | ANSWER | 4 |
| R4_WITNESS_IN_ENGLISH | PLAIN (one lesson in an everyday form) | LEARN | 4 |
| R5_MUST_ASK | approximate 2 / what-if 2 | ASK | 4 |
| R7_NEXT_SESSION | PLAIN (a new session on the same store and licensed brain, HELM's own constructor) | ANSWER | 2 |
| S1_WISDOM_STATED | FACE_STATED (lexicon phrasing) | ANSWER (faced stock x stage) | 6 |
| S2_POWER_STATED | FACE_STATED | ANSWER | 6 |
| S3_FACE_UNKNOWN | the face plus an unknown ingredient | ASK | 6 |
| S4_RECIPE_PURPOSE_ABSENT | PLAIN | ASK | 4 |
| S5_INGREDIENT_PURPOSE_ABSENT | PLAIN | ASK | 4 |
| S6_TWO_FACES | TWO_INGREDIENT | ANSWER | 2 |
| S7_NOT_A_FACE | PLAIN | ANSWER (plain yield) | 4 |

ANSWER 30, LEARN 4, ASK 30. Stock amounts are the source amounts times RB-W1T's frozen multipliers (all different, so
one ingredient runs out first). Faced keys use wave 3's stage values (Rising 1/4, Waning 1/2) and are drawn so the
face changes the limiting ingredient or the yield (wave 3's `avoid_raw`). Scoring (section 7) maps the brain's
ingredient names to recipe lines through its own lesson records (RB-W1T A-W-1). The keys stay on the laptop.

### 4.6 The custodian's pools (CONV and PAIRW)
From the same frame, after removing everything section 4.4 excludes AND the REAL draw: recipes with 2-6 lines, every
line parsed, representable (RB-W1T's rule), K-R key ANSWER on the recipe's own lines (all HEADs distinct, no zero
amount), and a title noun that is not one of the licensed brain's four products (bread, frosting, starter, meringue).
CONV pool 64 recipes, PAIRW pool 64 recipes, disjoint, each by hash rank with its own seed. Selection by these rules
reads the public key rule only, never HELM's behaviour.

### 4.7 Spent files (host only, by hash; reported rows, no mark)
X5's English-64 `1eb17c91…` and Faces-64 `2c7cac21…` (scored at c40): FULL and FULL+WIDE on each, read against c40's
FULL records (what changed in HELM's FULL since wave 5) and c47's records (reported).

## 5. Arms and units (79 host units; FROZEN_R1W6.json "units")

| Exam | Arms |
|---|---|
| X6_E64 (14) | FULL, FULL+WIDE, FULL+WIDE_REPLAY, FULL+EYE_SCAN, FULL+WIDE+EYE_SCAN, FULL+EYE_PAIRING, FULL+WIDE+EYE_PAIRING, FULL-X and FULL+WIDE-X for X = CUBE_STORE, ENGLISH_IN, VOICE |
| X6_F64 (14) | the same seven, and FULL-X / FULL+WIDE-X for X = TRIAD, ENGLISH_IN, VOICE |
| X6_CONV (16) | FULL, FULL+WIDE, FULL+WIDE_REPLAY, FULL+WIDE_NOASK, FULL+EYE_SCAN, FULL+WIDE+EYE_SCAN, FULL+EYE_PAIRING, FULL+WIDE+EYE_PAIRING, FULL-X and FULL+WIDE-X for X = CUBE_STORE, ENGLISH_IN, TRIAD, VOICE |
| X6_REAL (8) | FULL (the licensed brain, yardstick), FULL+WIDE, FULL+WIDE_REPLAY, FULL+WIDE_NOASK, WIDE_NO_LEARNING (control), ALWAYS_ASK (mechanism-free baseline), FULL+WIDE+EYE_SCAN, FULL+WIDE+EYE_PAIRING |
| X6_PAIR (12) | A: FULL, FULL+WIDE, FULL+EYE_PAIRING, FULL+WIDE+EYE_PAIRING, FULL+WIDE+EYE_PAIRING_REPLAY, CUT_VIOLATOR+WIDE, GUARD_VIOLATOR+WIDE; B and C: FULL, FULL+WIDE; plus the job map |
| X6_PAIRW (11) | A: FULL, FULL+WIDE, FULL-X and FULL+WIDE-X for X = CUBE_STORE, ENGLISH_IN, TRIAD, FULL+EYE_PAIRING, FULL+WIDE+EYE_PAIRING; plus the job map |
| REPRO_X5 (4) | FULL and FULL+WIDE on the spent X5 English-64 and Faces-64 (reported) |

"FULL" is wave 5's FULL arm (EYE_SCAN off, EYE_PAIRING off) on the merged HELM with WIDE off (D-W6-1). A fresh loop
and fresh brains per item / per job in every arm. The Eye's and the drive loop's random streams are seeded by their
mechanism label (as waves 4 and 5), so a pair comparison differs only in the switched part. WIDE_NO_LEARNING is the
candidate with a wide book whose `witness` refuses and changes nothing (RB-W1T's control class). ALWAYS_ASK asks on
every turn and writes nothing. CUT_VIOLATOR / GUARD_VIOLATOR are wave 5's instrument controls with WIDE on, never
scored.

## 6. Pair words (six; wave 3's `pair_word_exam` and `pair_word`, imported verbatim from the sealed wave-3 reader)

"All on" = the arm with WIDE and X on; L(a) = M(all on) - M(all on without a). Readable on an exam only if
L(WIDE) + L(X) <= M(all on) - margin (margin = 1/8 of the exam's denominator: 8 of 64 on live exams; 1/8 of family A's
items on PAIRW); then SYNERGY if L(both) >= L(WIDE) + L(X) + margin, INTERFERENCE if L(both) <= L(WIDE) + L(X) -
margin, else ADDITIVE. Across exams: INTERFERENCE, then SYNERGY, then ADDITIVE, else CEILING_NOT_READABLE (wave 3's
`pair_word`, as wave 4 used it).

| Pair | Exams | M |
|---|---|---|
| WIDE x CUBE_STORE | X6_E64, X6_CONV, X6_PAIRW | E64 / CONV: RIGHT_AND_PLAIN of 64; PAIRW: resolved items (family A pooled) |
| WIDE x ENGLISH_IN | X6_E64, X6_F64, X6_CONV, X6_PAIRW | same |
| WIDE x TRIAD | X6_F64, X6_CONV, X6_PAIRW | same |
| WIDE x VOICE | X6_E64, X6_F64, X6_CONV | RIGHT_AND_PLAIN |
| WIDE x EYE_SCAN | X6_E64, X6_F64, X6_CONV | RIGHT_AND_PLAIN (all on = FULL+WIDE+EYE_SCAN; -WIDE = FULL+EYE_SCAN; -EYE_SCAN = FULL+WIDE; both off = FULL) |
| WIDE x EYE_PAIRING | X6_E64, X6_F64, X6_CONV, X6_PAIRW | RIGHT_AND_PLAIN; PAIRW resolved |

Reported beside every pair word: `both_active` = the exams where L(WIDE) >= 1 and L(X) >= 1. A word read where one
part does nothing says only that no interaction was possible there; this is stated, not hidden. A pair word is READ
only when this wave's word is `WIDE_WAVE_EARNED_KEEP` and X was EARNED_KEEP before (c37 for the four live parts, c39
EYE_SCAN, c40 EYE_PAIRING — all were); otherwise `PAIR_NOT_READ` with `word_if_read`.

## 7. Scoring

- **X6_E64 / X6_F64:** wave 3's `score_turn` on the scored turn (the presented status for EYE_SCAN arms, as wave 4);
  M = RIGHT_AND_PLAIN (RIGHT and `helm_voice.cas_tokens(reply) == []`). An item is **lost** by WIDE if it is
  RIGHT_AND_PLAIN in the arm without WIDE and not in the arm with WIDE (item by item, RB-W1T's rule).
- **X6_REAL:** RB-W1T's scoring verbatim (`keys_rbw1t.score_question`, `score_lessons`, `unexplained_ask`, A-W-1 name
  mapping): RIGHT / WRONG / ASKS / NOT_SCORED; lessons LEARNED / WRONG / NOT_LEARNED; FULLY LEARNED; unexplained asks;
  **commitments on unsettled items** = items whose key is UNDETERMINED on which the arm answered
  (`SUCCESS_EVALUATED`).
- **X6_CONV:** ANSWER: answered with the exact yield and a limiting name that maps to the key's limiting line ->
  RIGHT; answered otherwise -> WRONG; not answered -> UNDETERMINED. ASK: wave 3's rule (an answer, a teaching write or a
  recorded stock write on the scored turn -> WRONG; asking with no write -> RIGHT; else UNDETERMINED). LEARN: the turn
  admitted a lesson whose ingredient maps to the key's line and whose coefficient, in the unit it was taught in,
  equals the key's amount -> RIGHT; admitted otherwise -> WRONG; else UNDETERMINED. M = RIGHT_AND_PLAIN.
- **X6_PAIR / X6_PAIRW:** wave 5's counting (resolved with a passing receipt; WRONG; UNDETERMINED), family A pooled.

## 8. Instrument rows, hard gates, marks, status word

**Instrument rows** (any false -> verdict `INSTRUMENT_ERROR`, word `INCONCLUSIVE`): I0 not a practice mock; I1 data
identity (this package's freeze and members; every neighbour by freeze, on the host and at the reader; the X6 files by
the custodian's pins; the receiver's check all_pass; the spent X5 files by hash); I4 parameter counts (the Eyes, the
receiver, the triad, the faces reader learn 0; Eye-pairing tables hold whole counts only); I6 completeness (every
unit exit 0; every carried suite OK on the host; every arm holds every item / life); I7 reading from the sealed zip;
I9 governance (the approval record holds the owner's line verbatim with its pinned bytes and binds this zip and
freeze); I10 seed rule (section 10 recomputed from the line and the zip; bands; used table; overlap PASS; text steps
recorded); I11 the cut can fire (CUT_VIOLATOR+WIDE: faculty calls AND attention steps in conversation > 0 on every
life); I12 the guard and the Eye-write canary can fire (GUARD_VIOLATOR+WIDE trips > 0 on every life; canary refused
in every life); I13 job maps (X6_PAIR: wave 5's I14 exactly; X6_PAIRW: with all parts on every non-K7 job gives its
key; with WIDE off every K7 job gives no answer and no other kind changes; with X off exactly X's kind fails on every
item and no non-K7 item of another kind changes; K7 changes under X off are reported); I14 not vacuous (X6_REAL has
>= 16 items both representable and ANSWER-keyed; X6_PAIRW family A has >= 1 K7 item per life).

**Hard gates** (any false -> verdict `FAILURE`, word `INCONCLUSIVE`):
HG1 receipts (no `REFUSE_RECEIPT_INCONSISTENT` turn in any live / REAL / CONV unit; the X6_PAIR and X6_PAIRW
re-checker re-derives every resolution from the item's own data: 0 mismatches);
HG2 no invention in the drive-loop worlds (WRONG = 0 in every X6_PAIR / X6_PAIRW arm);
HG3 replay (FULL+WIDE = FULL+WIDE_REPLAY record for record on X6_E64, X6_F64, X6_CONV, X6_REAL; FULL+WIDE+EYE_PAIRING
= its replay on X6_PAIR A);
HG4 equal budgets (slot lists identical across arms, per life and session);
HG5 the cut (0 faculty calls and 0 attention steps in conversation for every honest EYE_PAIRING arm on every life and
live exam);
HG6 **the Eye writes 0** (EYE_PAIRING: non-brain write attempts 0, the canary excepted; EYE_SCAN: the live digest is
unchanged by every scan and every presentation, whisper writes 0; and, new, the wide book's learned digest and held
stock are unchanged by every scan, whisper and idle drive-loop tick in every WIDE arm);
HG7 no key read by any drive-loop arm, every Eye table all 0/0 at session 0, and every final Eye table rebuilt from
the attempt log (wave 5's H7, H8, H9);
HG8 open simplex (every pull target exact, every coordinate > 0, sum 1);
HG9 **guard trips 0** on every clean EYE_PAIRING arm, life and live exam (wave 5's Q6 guard);
HG10 the WIDE control (X6_REAL WIDE_NO_LEARNING: learned digest = the empty book's after every lesson, 0 WRONG, RIGHT
= ALWAYS_ASK's);
HG11 parameter audit (after every item / job of every WIDE arm, the wide book's only learned numbers are its
coefficients, at most one per (recipe, ingredient) on a support; the 9 unit factors equal their pinned values; the
book holds only its four named attributes);
HG12 switch hygiene (in every WIDE-off unit the wide modules are never imported; in every unit every HELM module comes
from `helm_now/`);
HG13 key-blind (no X6_REAL or X6_CONV key file on the host);
HG14 no network (socket guard in every unit, 0 attempts);
HG15 sandbox (the wave-1 brain folder hashes the same at host start and end);
HG16 same inputs (one input sha256 per exam in every arm);
HG17 the Eye's scan budget and no awake scans (wave 4's H5 and H7) on every EYE_SCAN arm;
HG18 the voice changes no answer (FULL vs FULL-VOICE and FULL+WIDE vs FULL+WIDE-VOICE: equal statuses, values and
limiting names on every scored turn of X6_E64, X6_F64 and X6_CONV).

**Marks** (decide the word; never gates):

| Mark | Rule | Why |
|---|---|---|
| NH no harm | items lost by FULL+WIDE vs FULL <= 2 on X6_E64 and on X6_F64 (RIGHT_AND_PLAIN, item by item); M(FULL) - M(FULL+WIDE) <= 2 resolved items on X6_PAIR A, B and C (pooled per family) | the owner's order; waves 4 / 5 / RB-W1T used 2 |
| NH-EYE no harm next to the Eyes | items lost by FULL+WIDE+EYE_SCAN vs FULL+EYE_SCAN <= 2 on X6_E64 and X6_F64; by FULL+WIDE+EYE_PAIRING vs FULL+EYE_PAIRING <= 2 on X6_E64 and X6_F64, and <= 2 resolved items on X6_PAIR A; on X6_REAL, RIGHT(FULL+WIDE) - RIGHT(FULL+WIDE+EYE_X) <= 2 for each Eye | "tested alongside the other parts": switching an Eye on must not cost the wide brain, nor WIDE cost the Eye |
| QUIET no false alarm | 0 Body findings and 0 admitted whispers in FULL+WIDE+EYE_SCAN on every X6_E64, X6_F64, X6_CONV and X6_REAL item (all clean) | wave 4's mark (c); the wide brain's records must not look like faults to the Eye |
| K1 LEARNS | X6_REAL FULL+WIDE: FULLY LEARNED on >= ceil(9/10 x D) items, D = the items both representable and ANSWER-keyed | c47's bar (87 of 96 there); the owner: "keeps >= the c47 level" |
| K3 SAFE | X6_REAL FULL+WIDE: 0 WRONG answers and 0 WRONG lessons | c47: 0 and 0 |
| K4 HONEST | X6_REAL FULL+WIDE: 0 unexplained asks (an ANSWER-keyed item, every lesson LEARNED, the stock recorded, and the question not answered) — an UNSETTLED_ASK firing on such an item counts | c47: 0; the new rule must fire only where the source is unsettled |
| K5 CAUTION (new) | X6_REAL FULL+WIDE: commitments on UNDETERMINED-keyed items <= floor(U / 5), U = the number of UNDETERMINED-keyed items; readable only if U >= 5 | c47 answered 19 of 23 (83%); the rule should bring it near 0; one in five is left for the brain's names disagreeing with the key's HEADs (for 23 items: at most 4, the owner's example). U < 5 would make the mark say nothing |
| P READABLE | each of the six pair words is not CEILING_NOT_READABLE and not INCOMPLETE | the owner: "pair words readable" |

Eye writes 0 and guard trips 0 are hard gates HG6 and HG9 (as in wave 5).

**Verdict:** `INSTRUMENT_ERROR` if any instrument row is false; else `FAILURE` if any hard gate is false; else `PASS`.

**Status word** (frozen order; the first that holds):
1. `INCONCLUSIVE` — verdict not PASS.
2. `WIDE_WAVE_HARMED` — NH, NH-EYE, QUIET or K3 missed.
3. `WIDE_WAVE_NO_GAIN` — K1 or K4 missed, or K5 readable and over its threshold.
4. `INCONCLUSIVE` — P missed, or K5 not readable (U < 5).
5. `WIDE_WAVE_EARNED_KEEP` — everything above holds.

**Reported rows (no word):** every arm's totals per exam; X6_REAL per stratum and the c47 comparison; FULL+WIDE_NOASK
vs FULL+WIDE (what UNSETTLED_ASK changed: firings, by key class); X6_CONV per family and rung; the Eyes' scans,
findings, whispers and declines; drive-loop resolved per arm, B drift and C null rows as wave 5; REPRO_X5 vs c40's
FULL records (fields id, score, statuses, values, limiting, writes, plain) and vs c47's OFF_NOW totals; the K7 job's
success rate; pair-word numbers and `both_active`.

## 9. Builder's practice (facts, not claims)

The builder runs every unit on PRACTICE data only: E64 / F64 fixtures from wave 3b's generator at practice seeds
outside every band; X6_PAIR / X6_PAIRW worlds from practice seeds; X6_REAL = RB-W1T's published practice draw v2
(seed text `RBW1-DISHNAME-FIX-PRACTICE-V2-20261020-builder-published`, keys computed by the builder from the public
frame; it is excluded from the exam); CONV and PAIRW pools = wave 6's own published practice pools (seed texts
`R1W6-CONVPOOL-PRACTICE-20261019-builder-published` and `R1W6-PAIRWPOOL-PRACTICE-20261019-builder-published`,
excluded from the exam by id and text). Practice numbers go into `TEST_RECORD_R1W6.md`. Nothing in sections 4-8 may
change after the first full practice run except as a numbered deviation.

## 10. Custody and seeds

- **Seed source:** H = sha256 of the UTF-8 bytes of (the owner's line + ":" + the full sha256 of the final sealed zip,
  64 lower-case hex), no trailing newline. Expected line: `PAIR WAVE at 1 USD` (18 UTF-8 bytes). The exact bytes are
  pinned by program (`r1w6/approval_w6.py record`): the coordinator writes the owner's words into a one-line file with
  no newline; if the approvals file shows the line inside the owner's own quote marks, the inner text is the pinned
  form (RB-W1T precedent); the record holds the line, its byte count and sha256, and the zip and freeze sha256.
- **Part seeds:** for each numeric part P in (E64, F64, REAL, CONV, PAIRW): k = int(sha256(H + ":" + P)[0:16], 16);
  first slot = k mod 1,000,000; seed = band low + slot. Bands (each 1,000,000 wide, 1,000,000 apart, all above RW2):
  E64 1,954,000,001-1,955,000,000; F64 1,956,000,001-1,957,000,000; REAL 1,958,000,001-1,959,000,000; CONV
  1,960,000,001-1,961,000,000; PAIRW 1,962,000,001-1,963,000,000. Used table = 1-1,953,000,000 as one whole range
  (every earlier band and derivation lies inside it, RB-W1T's RW2 included). Gap 1,000,000; step s <- (s + 1) mod
  1,000,000 inside the band (overlap, or a text-rule hit for E64 / F64); no free slot = STOP. Every number below
  2^31 - 1.
- **Drive-loop world seeds** (RB-I3's World takes any integer): seed(life) = int(sha256("R1W6-X6PAIR:" + H + ":" +
  life name)[0:16], 16) for the 13 X6_PAIR lives and ("R1W6-X6PAIRW:" ...) for the 3 X6_PAIRW lives; a seed equal to
  an RB-I3 seed, a wave-5 or wave-6 practice seed or another life's seed gets ":step<n>" and is hashed again.
- The custodian is a separate session that runs only the sealed package's programs on the laptop (`r1w6.custody_w6
  seal`), prints hashes and counts only, keeps `exam/` (keys, sample records) on the laptop, and hands over the host
  carrier (inputs and pins only). The builder never sees a seed, an item or a key.

## 11. Predictions (written before any code; not read by any program)

- NH on X6_E64 / X6_F64 / X6_PAIR: met, 0 lost (c47 showed ON = OFF on four such files; PAIR jobs have no WIDE path):
  about 0.9.
- NH-EYE: met (about 0.75). Risk: on X6_REAL / X6_CONV the Eye scans stores that hold the wide path's event records.
- QUIET: about 0.6 — the wide path writes "Stock on hand" and "Witnessed batch" event cubes and keeps its stock in
  memory; the Eye's body checks were built for the licensed records, so a false alarm on CONV or REAL is the main risk
  of this wave.
- K1: about 0.6 (c47 95.83% on a different draw; c46 81.82%). K3: about 0.8. K4: about 0.75 (new risk: the rule firing
  on an ANSWER-keyed recipe). K5: about 0.6 (the rule should catch most shared-head recipes; misses where the
  grammar's HEAD is not the brain's last word).
- X6_CONV, FULL+WIDE: R1 PLAIN about 4 of 6 right; faces families mostly asked or WRONG (the triad wraps only the
  licensed brain; the faces reader knows only the licensed ingredients) — I expect several WRONG on S1/S2/S6
  (reported, no mark); next-session 0 of 2 (the wide book is not kept across sessions).
- X6_PAIRW: K7 job success with WIDE on about 90%; candidate family A resolved about 35% (wave 3's drive loop) and
  about 70% with EYE_PAIRING.
- Pair words: WIDE x EYE_PAIRING readable on PAIRW, ADDITIVE most likely; WIDE x CUBE_STORE / ENGLISH_IN / TRIAD
  readable and ADDITIVE on PAIRW with both parts active (disjoint kinds); WIDE x VOICE readable on CONV, ADDITIVE;
  WIDE x EYE_SCAN readable but with the Eye inactive everywhere (no planted fault in this wave) unless QUIET fails.
- Word: `WIDE_WAVE_EARNED_KEEP` about 0.3; `WIDE_WAVE_HARMED` about 0.3 (QUIET / NH-EYE); `WIDE_WAVE_NO_GAIN` about
  0.25; `INCONCLUSIVE` about 0.15.

## 12. What a pass licenses, and what it never licenses

- `WIDE_WAVE_EARNED_KEEP`: the wide brain becomes **HELM's canonical-brain candidate across the switches**, ceiling
  `NAMED_CORPORA_ONLY` (the X-REAL corpus list) for the real-recipe sentences + `SYNTHETIC_ONLY` for the drive-loop and
  English-64 / Faces-64 / conversation sentences: "With HELM's other parts on (cube store, English reader, triad,
  voice, the Unity Eye's self-scan and pairing), the wide brain cost at most 2 items on every wave-5 exam family, the
  Eyes raised no false alarm on its records and wrote nothing, it learned >= 90% of the representable real recipes
  of a fresh blind draw with 0 wrong, asked where the source left two ingredients with the same name (at most one in
  five such recipes answered), and its six pair words with the other parts were readable." Making it HELM's canonical
  brain stays the owner's decision; the licensed brain keeps its license.
- `WIDE_WAVE_HARMED` / `WIDE_WAVE_NO_GAIN` / `INCONCLUSIVE`: no move; the candidate status from c47 stands as it was
  (a candidate pending a pair wave); the misses are recorded as negatives.
- **Never, by this wave:** real kitchens or real cooks; typed English in general (every turn is a fixed template
  around source text or wave 3's phrasing pools, never typed by a person); anything about the CAS-token transformer
  (CTT) or any transformer; that the faces / triad reach the wide brain (they do not; reported); the 28 drive cells or
  22 pathways; statistical superiority (one run, one draw); "better than the licensed brain" outside these items.

## 13. Run limits and governance (PROPOSED)

One `m6i.xlarge`-class CPU host (2-CPU / 14 GiB slice, the run-proven kit), us-west-2, the c21 image; no GPU, no
torch work; 79 units at 2 workers; runner deadline 2,400 s; **cap 1.00 USD for the scored attempt and at most one
plumbing retry** (only if no scored unit started; same zip, same carriers). Expected about 0.03-0.10 USD. The sign
request names the expected owner word **`PAIR WAVE at 1 USD`** and what it binds (this zip by its sha256, the cap, the
attempts, the seed source). The builder places no ledger hold. **Superseded by D-W6-8:** the owner pre-approved the
wave with exactly that line; no sign request is written; `APPROVAL_RECORD_R1W6.md` (+ `.json`) binds the line and the
final zip.

## 14. Deviations and decisions (numbered; appended, never edited away)

- D-W6-1 "wave-5 FULL (yardstick)" is read as wave 5's FULL arm (EYE_SCAN off, EYE_PAIRING off) on the merged HELM with
  WIDE off; the two Eye switches are added as the order's arm list names them. FULL here differs from c40's FULL by
  the HELM fixes merged since wave 3's cut (reader v1.1, lexicon v3 switch, chat fixes); that difference is reported
  (REPRO_X5), never scored.
- D-W6-2 ENGLISH_IN keeps wave 3's adapter exactly; the wide reader belongs to WIDE (section 3).
- D-W6-3 X6_CONV re-states the English-64 / Faces-64 family bodies for real recipes and English teaching (section 4.5);
  pools and phrasings are imported from the sealed generators.
- D-W6-4 The UNSETTLED_ASK rule is new wave-6 code beside HELM (a wrapper installed per unit), not a change to HELM's
  files. If it earns its keep, moving it into HELM is a separate build.
- D-W6-5 Store reads are not in X6_CONV: the wide path keeps its stock in memory and writes it as one event record,
  which wave 3's store-read questions do not list; a READ family would test the licensed store only.
- D-W6-6 (2026-10-19, after reading RB-W1T's PUBLISHED practice draw v2 keys, before any wave-6 code or exam) **K5
  split.** Of that draw's 15 UNDETERMINED keys, 7 come from X-REAL's line grammar reading a UNIT word as the ingredient
  (lines with a parenthetical aside, e.g. "½ cup (45 g) rolled oats", "¾ cup (180 ml) water": HEAD = "cup" on every
  line, so K-R calls the HEAD "repeated"); there the source DOES settle every amount and a brain that reads the source
  well should answer. The other 8 come from one ingredient name used on two lines ("Graham flour" / "flour", "sugar" /
  "granulated sugar", "milk" / "scalded milk"). Scoring the caution on all UNDETERMINED keys would mark the brain down
  for not copying a key-grammar artifact. So: **K5 CAUTION (the mark) counts only SAME_NAME items** = UNDETERMINED-keyed
  items with two lines whose HEADs are equal and whose HEAD (folded by `head_norm`) is NOT a unit word (frozen list
  `r1w6.common_w6.UNIT_HEADS`: the 20 survey units, their plurals and the abbreviations and metric words of X-REAL's
  grammar). U = the number of SAME_NAME items; mark: commitments <= floor(U / 5); readable only if U >= 5. **K5-ALL**
  (the literal reading: every UNDETERMINED key) is REPORTED beside it, with the artifact items' commitments, and is not a
  mark. Flag for the owner: if he wants the literal reading to decide the word, that is a reseal before launch.
- D-W6-7 (after a probe of wave 5's job map on a practice world with the current HELM, before any wave-6 code) **job
  maps read on the solvable items.** HELM's current English reader (v1.1, STOCK_FRAME rule, PR #378) refuses wave 5's
  NOTE template 2 ("I just counted 12 packets of yeast.": `CLARIFY` / `NO_STOCK_FRAME`); on the practice life 14 of 76
  K3 items (all template 2) fail with every part on. That is a deliberate reader change since wave 5, not an
  instrument fault; those items are unsolvable in every arm. I13 is therefore: with all parts on, record which items'
  jobs give their key (the rest are UNSOLVABLE, counted and reported by kind and template); on the SOLVABLE items, each
  part off fails exactly its own kind and changes nothing else (X6_PAIR), and the X6_PAIRW rules of section 8 hold.
  I13 is false if any item of a kind other than K3-template-2 (X6_PAIR) or K7 (X6_PAIRW) is unsolvable with all parts
  on. The same rule covers K7 recipes the wide brain cannot learn.
- D-W6-8 (coordinator message, 2026-10-19 night) **pre-approval.** The owner pre-approved this wave with the verbatim
  line `PAIR WAVE at 1 USD` (pinned bytes, 18 UTF-8 bytes; `Documents\Codex\2026-10-18\OWNER_APPROVALS_20261018.md`,
  heading "Owner pre-approval + order (2026-10-19 night, verbatim)"): cap 1.00 USD, one attempt + one plumbing retry;
  approval = this line + the sealed zip sha256; seed source = sha256(UTF-8 of the pinned line + ":" + the final zip
  sha256), exactly as section 10. `APPROVAL_RECORD_R1W6.md` / `.json` replace the sign request; the record quotes the
  line by program (bytes and sha256). Nothing else changes.
- D-W6-9 (arithmetic slip) The unit count is **77**, not 79: X6_E64 and X6_F64 have 13 arms each (the seven core arms +
  three parts x two), and REPRO_X5 is 2 arms x 2 files = 4 units. No arm changed.
- D-W6-10 (written before the first practice scoring) **X6_CONV ASK reading.** Wave 3's ASK rule, read for the wide
  path's statuses: an answer (`SUCCESS_EVALUATED`), a lesson admitted (`WITNESS_ADMITTED`) or a stock write
  (`INVENTORY_RECORDED` / `STOCK_RECORDED` with writes > 0) on the scored turn -> WRONG; an asking status by RB-W1T's
  list (wave 3's list + `UNDETERMINED_UNKNOWN_PRODUCT`) with no write -> RIGHT; else UNDETERMINED.
- D-W6-11 (found by the first practice smoke run) **a HELM defect, worked around in the harness only, FLAG_FOR_HUMAN_REVIEW.**
  `helm_english_in.quantities_said` raises `KeyError('stock_words')` on a reading made by the WIDE reader (its witness has
  another shape). Wave 3's `run_item` and wave 4's `Session` call it on every turn (for the voice's memory of the user's
  own words), and so does HELM's live `helm_chat._recipe_turn`: with WIDE on, teaching a batch through HELM's chat
  would crash that turn. The wave-6 harness hands the neighbour harnesses a namespace whose `quantities_said` answers
  `{}` for a wide reading (counted per unit, `quote_bypassed`) and calls HELM's own function otherwise. It changes only
  what the voice may quote back. HELM's file is not changed (inputs are modified by no one here); the fix is a separate
  HELM build.
- D-W6-12 (after the practice run of X6_REAL, RB-W1T's published practice draw v2) **K4 and the key-grammar artifact.**
  The UNSETTLED_ASK rule fired on 1 ANSWER-keyed practice recipe ("100 g icing sugar" and "1 packet (8 g) vanilla
  sugar": the key grammar read "packet" as the second HEAD, so K-R saw no repeat). Same artifact class as D-W6-6, in the
  other direction. K4 now does not count an UNSETTLED_ASK firing on an ANSWER-keyed item whose key has a HEAD that is a
  unit word (`custody_w6.head_artifact`); such firings are REPORTED (`caution_on_artifact_items`), and the strict count
  (every firing on an ANSWER key) is reported as K4-STRICT. A firing on an ANSWER-keyed item with no unit-word HEAD
  still breaks K4. The rule itself was not changed.
- D-W6-13 (after the practice run of X6_CONV; conservative direction) **NH-CONV, a safety mark on the conversation
  part.** On practice, FULL+WIDE committed 23 WRONG answers on X6_CONV where FULL (the licensed brain) committed 0:
  stated faces ignored (S1 6, S2 5, S6 2: the triad wraps only the licensed brain and the faces reader knows only the
  licensed ingredients), absent purposes ignored (S4 3, S5 3), a restated amount in a unit of the other kind ignored
  (R1 UNIT_CHANGE 3), one face plus an unknown ingredient (S3 1). A pass licenses "candidate across the switches"; that
  sentence would be false while the wide brain answers wrongly whenever a person says an ingredient is old. So NH-CONV
  joins the HARMED condition: items lost by FULL+WIDE vs FULL on X6_CONV (RIGHT_AND_PLAIN, item by item) <= 2 AND
  WRONG(FULL+WIDE) - WRONG(FULL) <= 2. Added after seeing practice numbers, in the direction that makes a pass harder;
  flagged for the coordinator. Builder's prediction after practice: `WIDE_WAVE_HARMED` about 0.9 (section 15).
- D-W6-14 (scope of "every carried suite OK", I6) The host runs HELM's own seven suites (on a scratch copy of RB-W1T's
  `helm_now/`, the code under test) and the wave-6 unit and kit tests; the neighbours' own suites are not re-run (each
  ran OK on its own scored host run, c39 / c40 / c47, and every neighbour is checked by its freeze before import).

## 15. Practice run (facts, not claims) and predictions after practice

Written after the full practice dry run (`dry_run/run1/`, 73 units; the 4 REPRO_X5 units need the spent X5 files,
which the builder never opens). Practice data = the builder's published practice inputs (section 9), never an exam.
The reader said `INSTRUMENT_ERROR` as designed (practice mock, no approval, no host instruments, REPRO skipped); every
hard gate that does not depend on those held (HG1-HG12, HG17, HG18).

| Part | Practice result |
|---|---|
| X6_E64 / X6_F64 | FULL = FULL+WIDE = 60 of 64 RIGHT_AND_PLAIN each; 0 items lost (also with EYE_SCAN and EYE_PAIRING) |
| X6_PAIR A / B / C | FULL = FULL+WIDE: 533 / 505 / 645 resolved (WIDE has no code path in these jobs, by construction) |
| X6_REAL FULL+WIDE | 100 of 106 fully learned (bar 96), RIGHT 100, WRONG 0, wrong lessons 0, unexplained asks 0 (strict 1: the vanilla-sugar artifact, D-W6-12); same-name items 8, answered 0 (limit 1); all 15 UNDETERMINED items: answered 5 (the 7 key-grammar artifacts, D-W6-6) |
| X6_REAL FULL+WIDE_NOASK (= c47 build) | RIGHT 101; answered 12 of 15 UNDETERMINED, 6 of 8 same-name |
| X6_CONV | FULL 30 RIGHT_AND_PLAIN, 0 WRONG; FULL+WIDE 32, **23 WRONG**, 10 items lost (D-W6-13) |
| X6_PAIRW A | FULL 332, FULL+WIDE 512, FULL+EYE_PAIRING 856, FULL+WIDE+EYE_PAIRING 1039 resolved of 1517; WRONG 0 everywhere |
| Job maps | X6_PAIR: unsolvable only K3 template 2 (97); X6_PAIRW: K3 template 2 (45) and K7 (17 of 230 recipes the wide brain cannot learn); ENGLISH_IN off changed 6 K7 items (reported) |
| Eyes | 0 Body findings, 0 admitted whispers on every clean item; 0 Eye writes (the wide book never changed during a scan, whisper or idle tick) |
| Pair words (if read) | all six ADDITIVE, readable; both parts active only on X6_PAIRW (CUBE_STORE, TRIAD, EYE_PAIRING), X6_CONV + X6_PAIRW (ENGLISH_IN); WIDE x VOICE and WIDE x EYE_SCAN are readable only where one part does nothing |
| Time | pool 287 s on the laptop at 1 worker (sum of units 264 s; the two job maps 29 s and 26 s) |

**Predictions after practice (not read by any program):** verdict `PASS` about 0.85; NH-CONV missed about 0.9 (the
practice gap is 23 new wrong answers against a limit of 2); so **`WIDE_WAVE_HARMED` about 0.85**, `INCONCLUSIVE` about
0.12, `WIDE_WAVE_NO_GAIN` about 0.02, `WIDE_WAVE_EARNED_KEEP` about 0.01. If NH-CONV is set aside, K1 met about 0.7,
K4 about 0.75, K5 about 0.75. Said plainly for the coordinator: as merged, the wide brain answers wrongly when a person
says an ingredient is old, that a recipe or ingredient is not needed, or restates an amount in another kind of unit,
because the triad, the purpose faces and the unit restatement do not reach the wide path; and HELM's chat would crash
on a wide teaching turn (D-W6-11). Fixing those is a HELM build, not this packet.
- D-W6-15 (seal) **Sealed.** `HELM_R1_W6_20261019_SOURCE_R1W6.zip` sha256
  `f307bdbc51210b87d413b5adb834183f3404ce4da5ac6d37ce23873909d7c9e1` (128,056 bytes, 33 members + the freeze; resealed
  byte-identical); `PACKAGE_FREEZE.json` sha256 `1b8943c6f9b59a0cef4c179125c4c5cc4c45c6f3d4f55980591f139d4a95db6f`;
  `FROZEN_R1W6.json` sha256 `da00f9495c254c3eba494722598589c01ed37453f017f41c4b09b9761e320867`. The package holds the
  preregistration as it stood at the seal (sections 0-15, D-W6-1..14). `APPROVAL_RECORD_R1W6.json` sha256
  `271ee619effaf6cebd430b3ae5326772b25785b12e3f2638915f69fa186e5d1f` (`.md` `6a3e497c…`) binds the owner's pinned line
  (18 bytes, sha256 `003f4051…`) to this zip and freeze; it was written by the sealed program `r1w6/approval_w6.py` and
  also prints the seed-source hash (a hash of two public values; every exam seed is still derived only by the
  custodian's sealed program). NOT LAUNCHED; no exam exists; no ledger hold.
