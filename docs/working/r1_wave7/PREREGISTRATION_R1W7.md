# PREREGISTRATION_R1W7 — HELM-R1 wave 7, the "CHAT WAVE": HELM's live chat with the canonical wide brain on, scored on fresh sealed exams (pre-code, 2026-10-20 PDT)

Status: DESIGN, WRITTEN BEFORE ANY CODE. Owner order (2026-10-20, verbatim): "the live chat with the wide brain tested for real".
Nothing here is a result. Every number below is frozen now; the frozen reader applies them; no one re-reads them after the data exists.

## 0. What the owner ordered, plainly

On 2026-10-20 the owner ruled "YES TO WIDE BRAIN: Wide brain becomes HELM's canonical brain" (SPEC §7.56) and then ordered the
code to run it by default in the live loop and the chat (PR #414, thread head `974fe36c`). The wide brain earned its standing in
sealed tests that drove HELM's loop directly (RB-W1T c47, §7.89; the pair wave c50, §7.96). **No sealed test has ever driven HELM
through the chat window** (`helm_chat.py`: the memory, the intent routing, the everyday-English voice, the session log). This wave
does that, with the wide brain on by default as the code now runs, against fresh exams drawn blind by a custodian.

## 1. Gate answer

"When a person types to HELM's chat, with the canonical wide brain on, does HELM learn real recipes, answer right, ask where it
should, say it plainly, and stay unbroken by ordinary small talk, as well as the loop did when driven directly?"

## 2. What is under test

- **HELM cut:** `helm_now/`, the HELM files of thread branch `claude/project-thread-pmbzd6` at head `974fe36c` (PR #414 merged:
  wide brain ON by default; reader v5; `helm_brain_canonical.py` byte-identical to its scored base `d4488f2a`). The package carries
  its own copy; the host runs that copy and nothing else of HELM.
- **The chat:** `helm_chat.HELMConversationalSession(mode, session_id)` and its `handle_turn(text)`. The harness drives it exactly
  as a person would: one fresh session per dialogue or recipe, one `handle_turn` per line, replies captured from standard output
  (the chat prints; it does not return). `HELM_SESSION_DIR` points inside the unit's scratch so the chat's session log never
  leaves the sandbox. The harness never calls the loop directly in a CHAT arm and never patches `helm_chat`.
- **Recording:** the harness records, per turn, the chat's own memory record (`memory.turns[-1]`: intent, gate code, receipt
  hash, reply) and the loop result the chat used (`session.loop.process_turn` is wrapped by a thin recorder that stores the
  returned dict unchanged and passes it through). The recorder changes no input and no output; a test proves the wrapped and
  unwrapped loop give byte-identical results on practice turns.
- **Reused, unchanged, by import from sealed neighbours:** wave 6 v3 (`HELM_R1_W6_20261019`, freeze `da1ec4d2…`): `gen_conv`
  (dialogue generator, pools, `score_item`), `score_w6`, the custody and seed-rule helpers; RB-W1T v3 (`HELM_RBW1T_20261019`,
  freeze `04eef886…`): `exam_rbw1t` / `keys_rbw1t` (the real-recipe frame, draw, mapping and K-R keys), `pool_rbw1t`; wave 3 v3
  and wave 3b (phrase pools gen_conv imports); wave 1 v3 (the licensed brain the chat's loop loads).

## 3. Arms (the chat's switch is HELM's own: `HELM_WIDE_BRAIN`)

| Arm | What | Why |
|---|---|---|
| **CHAT_ON** | the chat as shipped: switch unset = wide brain on (canonical) | **the arm under test** |
| CHAT_OFF | the chat with `HELM_WIDE_BRAIN=0`: the licensed reference brain alone | the yardstick HELM had before the ruling |
| CHAT_ON_REPLAY | CHAT_ON again, fresh process | HG2 replay |
| CHAT_DIAG | CHAT_ON in `mode="cas_diagnostic"` (the voice is bypassed; the loop's own sentence is printed) | HG7: the voice changes no answer |
| LOOP_ON | wave 6's harness path: the same turns through `HELMEndToEndLoop.process_turn` with the wide brain on, no chat layer | NH-CHAT: the chat layer costs nothing |
| ALWAYS_ASK | wave 6's mechanism-free baseline (every question asked) | the floor on X7_REAL |

CHAT arms run on every exam; LOOP_ON on X7_CONV and X7_REAL; ALWAYS_ASK on X7_REAL. X7_NOISE has only CHAT_ON and CHAT_OFF
(the loop has no small talk).

## 4. The exams (drawn blind by a separate custodian; the builder sees hashes and counts only)

### 4.1 X7_REAL — 128 real recipes taught through the chat
RB-W1T's frozen frame, draw rules, name mapping and K-R keys (`exam_rbw1t`, `keys_rbw1t`, D-W6 unchanged), seed text
`str(REAL seed)`; excluded by id and equal text: X-REAL's 128, c46's 128, c47's 128, X6's 128 REAL ids, X6v3's 128 REAL ids,
both RB-W1T practice draws, wave 6's practice pools, wave 7's practice pool (section 9). Each recipe is one chat session: the
lesson sentences (RB-W1T's), then the stock sentence, then "How much {N} can we make?". Keys stay on the laptop.

### 4.2 X7_CONV — 64 dialogues, wave 6's generator at a fresh seed
`gen_conv.build(pool, str(CONV seed))` with gen_conv's frozen COMPOSITION (ANSWER 30, ASK 30, LEARN 4; fifteen families R1–R7,
S1–S7). CONV pool: `gen_conv.draw_pool` at the CONV seed, excluding everything 4.1 excludes AND the X7_REAL draw AND X6's and
X6v3's CONV and PAIRW pools. Each dialogue is one chat session; every line is one `handle_turn`.

### 4.3 X7_NOISE — the same 64 dialogues with small talk between
The X7_CONV items unchanged, with two noise turns inserted per dialogue by the custodian's program at the NOISE seed: one
after the teaching turns (before the scored turns) and one between the stock turn and the question turn where both exist,
else after the first scored turn. Noise sentences come from this frozen list of twelve (the custodian's program picks two,
distinct, per dialogue):

1. "Hello there!"  2. "My grandfather kept bees in the south of France."  3. "Remember that I prefer short answers."
4. "I'm feeling tired today."  5. "Tell me a joke."  6. "What do you know about me so far?"  7. "What did we just do?"
8. "I live in Oakland and I like hiking."  9. "Thanks, that's helpful."  10. "How are you?"
11. "Do you remember what I said about my answers?"  12. "I love this recipe book."

The scored turns and their keys are those of the X7_CONV item. Reported beside them: for each noise turn, the intent the chat
recorded (expected: not a recipe intent) and whether the reply contains any CAS token.

### 4.4 Counts and vacuity
X7_REAL 128 (key counts recorded by the custodian; at least 16 representable and ANSWER-keyed, else I14 fails);
X7_CONV 64 (every family present); X7_NOISE 64 (128 noise turns).

## 5. Scoring (per scored turn; the frozen functions of the neighbours)

- X7_CONV / X7_NOISE: `gen_conv.score_item(ns, key, record)` on the loop record the chat used -> RIGHT / WRONG / UNDETERMINED;
  LEARN keys as wave 6.
- X7_REAL: RB-W1T's rules through wave 6's `score_real` (fully learned, RIGHT, WRONG, asks, lessons learned / wrong / not
  learned, unexplained asks, caution items), on the loop records of the recipe's session.
- **RIGHT_AND_PLAIN** (the chat's reply, not the loop's sentence): RIGHT and the reply has 0 CAS tokens (`helm_voice.cas_tokens`)
  and quotes the yield exactly as the loop's `output_value` (same number, same fraction form or the same value in the voice's
  mixed-number form; a test fixes the comparison). Applies to CHAT_ON, CHAT_OFF, CHAT_ON_REPLAY; for CHAT_DIAG and LOOP_ON
  plainness is not scored (reported only).
- **Routing** (X7_NOISE): a scored turn is MISROUTED when the chat's recorded intent is not `RECIPE_FOUNDATION_LOOP` or
  `INVENTORY_DECLARATION`; a noise turn is MISROUTED when its recorded intent IS one of those two.
- **Lost** (item by item, as wave 6): RIGHT_AND_PLAIN in the base arm and not in the candidate arm (X7_CONV); RIGHT in
  LOOP_ON and not RIGHT in CHAT_ON (NH-CHAT uses RIGHT, since LOOP_ON has no chat reply).

## 6. Instrument rows, hard gates, marks, status word

**Instrument rows** (any false -> `INSTRUMENT_ERROR`, `INCONCLUSIVE`): I0 not a practice mock; I1 data identity (this package's
freeze and every member; neighbours by freeze on the host and at the reader; the X7 files by the custodian's pins; the receiver's
check all_pass; `helm_now/` equals the recorded cut: every file's sha256 as listed in `contract/HELM_CUT_R1W7.json`);
I6 completeness (every unit exit 0; every carried suite OK on the host; every arm holds every item); I7 reading from the sealed
zip; I9 governance (the approval record holds the owner's line verbatim with its pinned bytes and binds this zip and freeze);
I10 seed rule (section 10); I12 the recorder is transparent (the practice equality test ran on the host and passed);
I14 not vacuous (4.4).

**Hard gates** (any false -> `FAILURE`, `INCONCLUSIVE`):
HG1 receipts (every saved cube in every chat turn carries a receipt hash, the chat's recorded receipt hash equals the loop's,
and 0 `REFUSE_RECEIPT_INCONSISTENT` turns);
HG2 replay (CHAT_ON = CHAT_ON_REPLAY record for record on every exam: loop statuses, values, limiting names, cubes written,
reply text);
HG3 key-blind (no X7 key file on the host);
HG4 no network (socket guard in every unit, 0 attempts);
HG5 sandbox (the wave-1 brain folder hashes the same at host start and end; `helm_now/helm_brain_canonical.py` equals its
pinned base bytes; every file the chat wrote lies under the unit's scratch);
HG6 no crash (every `handle_turn` in every arm returned without an exception; the harness catches none);
HG7 the voice changes no answer (CHAT_ON vs CHAT_DIAG: equal loop statuses, values and limiting names on every scored turn of
every exam);
HG8 switch hygiene (CHAT_OFF units never import `helm_brain_wide` / `helm_wide_turn`; CHAT_ON units do; every HELM module
comes from `helm_now/`);
HG9 same inputs (one input sha256 per exam in every arm);
HG10 the chat never exits (no `SystemExit` in any unit; "exit" / "quit" never sent).

**Marks** (decide the word; never gates):

| Mark | Rule | Why |
|---|---|---|
| NH-CHAT | items lost by CHAT_ON vs LOOP_ON (RIGHT, item by item) <= 2 on X7_CONV and <= 2 on X7_REAL | the chat layer must cost nothing |
| K1 LEARNS | X7_REAL CHAT_ON: fully learned on >= ceil(9/10 x D) items, D = representable and ANSWER-keyed | c47 / c50's bar |
| K3 SAFE | CHAT_ON: 0 WRONG answers and 0 WRONG lessons on X7_REAL, X7_CONV and X7_NOISE | c47 / c50: 0 and 0 |
| K4 HONEST | X7_REAL CHAT_ON: 0 unexplained asks (wave 6's rule, UNSETTLED_ASK firings on such items count) | c50: 0 |
| P PLAIN | CHAT_ON on X7_CONV and X7_REAL: RIGHT - RIGHT_AND_PLAIN <= 2 per exam (a right answer not said plainly is a loss) | the owner's vision: everyday English, no CAS to people |
| N NOISE | X7_NOISE CHAT_ON: items lost vs X7_CONV CHAT_ON (RIGHT_AND_PLAIN) <= 2 AND misrouted scored turns = 0 | small talk must not break a recipe turn |

Reported rows (no word): CHAT_OFF totals on every exam (the before-the-ruling yardstick) and CHAT_ON - CHAT_OFF per exam;
misrouted noise turns and noise replies with CAS tokens; X7_REAL per stratum; the c47 / c50 comparison; every arm's totals.

**Verdict:** `INSTRUMENT_ERROR` if any instrument row is false; else `FAILURE` if any hard gate is false; else `PASS`.

**Status word** (frozen order; the first that holds):
1. `INCONCLUSIVE` — verdict not PASS.
2. `CHAT_WAVE_HARMED` — NH-CHAT, K3 or N missed.
3. `CHAT_WAVE_NO_GAIN` — K1, K4 or P missed.
4. `CHAT_WAVE_EARNED_KEEP` — everything above holds.

## 7. What a pass licenses, and what it never licenses

- `CHAT_WAVE_EARNED_KEEP`: status `VALIDATED` for this sentence only, ceiling `NAMED_CORPORA_ONLY` (the X-REAL corpus list) for
  the real recipes + `SYNTHETIC_ONLY` for the dialogue and small-talk sentences (every one a fixed template): "Typed into HELM's
  live chat line by line, with the canonical wide brain on by default, on a fresh blind draw HELM learned >= 90% of the
  representable real recipes with 0 wrong answers and 0 wrong lessons, asked 0 times without a reason, said every right answer in
  plain English (at most 2 exceptions per exam), lost at most 2 items against the loop driven directly, and lost at most 2 items
  when ordinary small talk was mixed into the dialogue." The canonical pointer (§7.56) is unchanged by any word of this wave.
- `CHAT_WAVE_HARMED` / `CHAT_WAVE_NO_GAIN` / `INCONCLUSIVE`: no claim about the chat; the misses are recorded as negatives;
  the canonical pointer is unchanged (a ruling is not undone by a test; the owner reads the negatives).
- **Never, by this wave:** typed English by real people (every turn is a template around source text or a frozen sentence);
  real kitchens or cooks; anything about CTT or any transformer; the Eyes or the drive loop (not switched on here); the 28 drive
  cells or 22 pathways; statistical superiority (one run, one draw); "better than the licensed brain" outside these items.

## 8. Units and host

Units (one process each, wave 6's `units_w6` pattern): X7_REAL x {CHAT_ON, CHAT_OFF, CHAT_ON_REPLAY, CHAT_DIAG, LOOP_ON,
ALWAYS_ASK} = 6; X7_CONV x {CHAT_ON, CHAT_OFF, CHAT_ON_REPLAY, CHAT_DIAG, LOOP_ON} = 5; X7_NOISE x {CHAT_ON, CHAT_OFF} = 2;
plus the recorder equality test unit = **14 units**. One m6i.xlarge-class CPU host (the kit's 2-CPU / 14 GiB slice), the c21
image, us-west-2; no GPU; runner deadline 2,400 s; stage limit 3,000 s. Expected 0.02–0.10 USD; **cap 1.00 USD**; one attempt
+ one plumbing retry (only if no unit of the scored pool started). Owner's line to sign, proposed: `CHAT WAVE at 1 USD`.

## 9. Builder's practice (facts, never a claim)

The builder may run every unit on a PRACTICE draw only: wave 6's published practice pools and RB-W1T's practice draw v2
(`practice_mock: true` in every record; the reader refuses a practice record as an instrument problem). Practice counts are
published in `TEST_RECORD_R1W7.md` with the forecast of section 11; they decide nothing.

## 10. Custody and seeds

Seed text `H = sha256(UTF-8(owner line + ":" + full zip sha256))`, no trailing newline (RB-W1T / wave 6 rule). Bands, each
1,000,000 wide, above every band used or reserved so far (wave 6 v3 used up to 1,989,000,000):

| Band | Range | k |
|---|---|---|
| REAL | 1,990,000,001–1,991,000,000 | int(H[0:16], 16) |
| CONV | 1,992,000,001–1,993,000,000 | int(H[16:32], 16) |
| NOISE | 1,994,000,001–1,995,000,000 | int(H[32:48], 16) |

Used table 1–1,989,000,000 as one range; gap 1,000,000; slot stepping and STOP as wave 6; every step written to
`SEED_DERIVATION_X7.json`. The custodian runs `r1w7.custody_w7 seal` from an extracted copy of the sealed zip, laptop only,
0 USD, and ships a carrier `X7_CARRIER_V1.zip` (top folder `x7`: `INPUTS_REAL_X7.json`, `INPUTS_CONV_X7.json`,
`INPUTS_NOISE_X7.json`, `X7_PINS.json`; no key file). Keys, samples, pools and the derivation stay in `x7_custody/exam/` on the
laptop. The operator copies, hashes and compares; never opens an exam file. The builder never handles a carrier.

## 11. Honest predictions (written before any code; not read by any program)

- X7_REAL CHAT_ON: fully learned 88–94 of about 94 representable; RIGHT 90–96; WRONG 0; unexplained asks 0–1 (reader v5's
  relative-amount forms); K4 about 0.75 met.
- NH-CHAT: the chat routes a recipe sentence to the loop only when `loop.wants_turn` says so; a lesson sentence the reader does
  not claim would be lost to a non-recipe intent. Expected 0–2 lost on X7_CONV, 0–1 on X7_REAL; about 0.7 met.
- P PLAIN: the voice renders the loop receipt; CAS tokens expected 0; exact-amount quoting is the risk (mixed numbers): about
  0.6 met.
- N NOISE: the chat's intent patterns ("remember what I said", "what did we just do") are keyword-based; a recipe turn that
  happens to contain such words would misroute. Expected misrouted 0–1 — so this is the mark most likely to miss: about 0.5 met.
- Word: `CHAT_WAVE_EARNED_KEEP` about 0.3; `CHAT_WAVE_HARMED` about 0.35 (N or NH-CHAT); `CHAT_WAVE_NO_GAIN` about 0.2 (P);
  `INCONCLUSIVE` about 0.15 (a harness or custody fault on first use of a chat harness).

## 12. Deviations and decisions (numbered; appended, never edited away)

- D-W7-1: the chat is driven through `handle_turn` with stdout captured; `exit` / `quit` / `help` / `dials` / `history` / `mode`
  commands are never sent (they are not conversation).
- D-W7-2: CHAT_OFF uses `HELM_WIDE_BRAIN=0` (the shipped off-word), not a code change.
- D-W7-3: NH-CHAT compares RIGHT, not RIGHT_AND_PLAIN, because LOOP_ON has no chat reply; plainness is P's job.
- D-W7-4: the recorder wraps `session.loop.process_turn` by attribute assignment on the instance after construction; it stores
  the result dict (deep-copied) and returns the original object. I12 proves transparency on practice turns on the host.
- D-W7-5: the noise list is frozen above; the custodian's program chooses two distinct sentences and the two positions per
  dialogue from the NOISE seed; no person chooses.

## 13. Amendment A-R1W7-1 (builder's findings, written AFTER the code and BEFORE the seal; 2026-10-20)

Nothing above this line changed: every arm, exam, instrument row, hard gate, mark, status word, seed band and exam size
is as the precode fixed it (`PREREGISTRATION_R1W7.precode.md`, sha256
`efe94ed635f08ceab01e6268bd92832181f8164926717e4e8e035767d5a6d982`). This section adds what the builder found while
making the design run, numbered on from D-W7-5. Where the text above could be read two ways, the deviation says which
way the frozen reader reads it. The reader (`r1w7/merge_r1w7.py`) implements the rows exactly as numbered above.

**Deviations and decisions (continued).**

- D-W7-6 (LOOP_ON = the loop as shipped). LOOP_ON uses wave 6's harness with wave 6's `FULL+WIDE_NOASK` spec: the wide
  brain on, wave 6's UNSETTLED_ASK rule NOT installed. Reason: the chat as shipped carries no UNSETTLED_ASK rule (that rule
  was wave 6's own per-unit wrapper, never merged into HELM), so installing it in LOOP_ON alone would make NH-CHAT compare
  the chat against something HELM does not ship. Both arms therefore run the same HELM code; the only difference is the
  chat layer. The reader still counts the status `CLARIFY_WIDE_UNSETTLED_SAME_NAME` wherever it appears (it did not, on
  practice: 0 firings).
- D-W7-7 (what "quotes the yield exactly" means). The reply quotes the loop's `output_value` when one of the numbers it
  states equals the value exactly: a fraction (`1/3`), a mixed number (`1 1/2`), an integer, a decimal only when it is
  exactly the value (`0.5` for 1/2 yes; `0.33` for 1/3 no), or the same value in number words (`half`, `two thirds`, `one
  and a half`). A turn with no `output_value` (an ask) has nothing to quote and the clause holds. The comparison is
  `score_w7.quotes_yield`, fixed by `tests_r1w7/test_units_w7.py::Plainness`. Why the strict reading: the voice says
  `about 0.33 units` for a third; a rounded number is not the yield, and the owner's vision is a right answer said plainly,
  not approximately.
- D-W7-8 (HG2 replay on X7_REAL and X7_CONV). Section 3 gives X7_NOISE only CHAT_ON and CHAT_OFF, so HG2's "every exam" is
  read as every exam that has a replay arm: X7_REAL and X7_CONV. The projection compared record for record is every turn's
  loop status, value, limiting name, cubes written, reply text and intent.
- D-W7-9 (K4 counts the strict asks). "Wave 6's rule, UNSETTLED_ASK firings on such items count" is read as RB-W1T's
  `unexplained_ask` without wave 6's D-W6-12 exemption (the strict count `unexplained_asks_strict`); the D-W6-12 count is
  reported beside it. A question turn the chat did not route to the loop (its recorded intent is not a recipe intent) has
  status `NOT_ROUTED_TO_LOOP:<intent>`, which RB-W1T's `score_question` reads as an ask; on a fully learned recipe with the
  stock recorded that is an unexplained ask. The person typed a recipe question and got no recipe answer and no reason.
- D-W7-10 (R7's `new_session` marker inside one chat session). Section 4.2 fixes one chat session per dialogue; wave 6's
  generator marks two R7 dialogues with a `new_session` setup entry (wave 3's meaning: a second loop on the same brain and
  store). In a CHAT arm the marker starts no new session and sends no line; it is recorded as a turn of kind `new_session`
  with status `CHAT_SESSION_CONTINUES`. In LOOP_ON it keeps wave 3's meaning. The two R7 items are scored like every other
  item and their ids appear in the lost lists if they are lost.
- D-W7-11 (isolated python). Every process is `python -X utf8 -B -I <script> ...` (the owner's rule). In isolated mode
  nothing is on `sys.path` (no PYTHONPATH, no current folder), so every entry point is a script that puts its own package
  on the path (`r1w7/units_w7.py`, `r1w7/merge_r1w7.py`, `r1w7/custody_w7.py`, `r1w7/check_w7.py`, `r1w7/approval_w7.py`,
  `tests_r1w7/run_tests.py`, `tests_r1w7/test_run_w7.py`); `-m r1w7....` is not used. The host runner sets no PYTHONPATH.
- D-W7-12 (the cut). `helm_now/` holds 161 files: wave 6 v3's 159-file list plus the two `test_helm_*.py` files new at
  the commit (`test_helm_agentic_planner.py`, `test_helm_memory.py`). `helm_ui/` and `helm_hub/` are not cut, so the chat's
  session log has no default home inside the package; `HELM_SESSION_DIR` is set into the unit scratch before any HELM
  import (section 2). The three pytest-style HELM test files (`test_helm_chat_nuance.py`, `test_helm_memory.py`,
  `test_helm_agentic_planner.py`) are carried but are not unittest suites; the host runs the same eight unittest files
  wave 6 ran. `helm_brain_canonical.py` at the commit equals its scored base `d4488f2a` byte for byte (sha256
  `24df53c9...`), pinned in `common_w7.HELM_BRAIN_CANONICAL_BASE` and checked by the runner, the units' setup and the reader.
- D-W7-13 (the chat's own tool engine). The chat constructs `AgenticExecutionEngine(workspace_root=HERE)` with HERE =
  `helm_now/`; a turn routed to its agentic path could write there. The harness does not patch this (section 2 forbids
  patching `helm_chat`); instead every unit records the sha256 of every file under `helm_now/` before and after
  (`helm_now_files_changed`, must be empty: HG5), moves the temp folder into the unit scratch (`TMPDIR`/`TEMP`/`TMP` and
  `tempfile.tempdir`), and records that every session log lies under the scratch. On practice no unit changed a file.
- D-W7-14 (a record the chat never reached the loop with). When `handle_turn` records a non-recipe intent for a dialogue
  line, the harness writes a log row `NOT_ROUTED_TO_LOOP:<intent>` (never admitted, nothing written) in that line's place,
  so the lesson rows stay aligned with the key's lines and RB-W1T's scoring functions apply unchanged. Noise turns are
  recorded in `noise_turns`, outside the aligned log.
- D-W7-15 (the recorder unit's practice turns). Unit 14 runs on `tests_r1w7/fixtures/RECORDER_PRACTICE_TURNS.json`: six
  dialogues of the builder's practice draw (wave 6's published practice pool; `practice_mock: true`), one per family in
  draw order. It proves three things per dialogue: a wrapped and an unwrapped session give the same chat memory record
  turn for turn; two wrapped sessions give byte-identical recorded loop results; every stored copy equals the dict the
  chat received. I12 reads `all_equal` from that unit.
- D-W7-16 (the owner line is proposed, not signed). `CHAT WAVE at 1 USD` (18 UTF-8 bytes) is pinned in the code as the
  PROPOSED line. No approval record exists and no custodian seal was run; `approval_w7.py record` is run only after the
  owner signs, and needs `--source` naming where the words are recorded.

**Builder's practice (facts about practice data only; nothing here is a result).** Practice inputs = RB-W1T's practice
draw v2 (128 recipes) and wave 6's published practice conversation pool (64 dialogues at the practice seed text
`R1W7-PRACTICE-CONV:777701`; noise at `R1W7-PRACTICE-NOISE:777702`), both excluded from the exam by id and text. 14 units,
one process at a time, 63.6 s in all; every unit exit 0; 0 crashes; 0 network attempts; 0 receipt problems; replay and
diagnostic projections equal; the recorder transparent on 6 of 6 dialogues. Reader on practice: `INSTRUMENT_ERROR` /
`INCONCLUSIVE` (practice mock, no approval, no sealed zip: as designed).

| Practice number | CHAT_ON | CHAT_OFF | LOOP_ON |
|---|---|---|---|
| X7_REAL RIGHT / WRONG / asks (128 items, 106 representable ANSWER keys, 15 UNDETERMINED keys) | 90 / 0 / 23 | 0 / 0 / 113 | 100 / 0 / 13 |
| X7_REAL fully learned of 106 (K1 bar 96) | 97 | 0 | 99 |
| X7_REAL lessons learned / wrong / not learned (of 670) | 578 / 0 / 92 | 0 / 0 / 670 | 573 / 0 / 97 |
| X7_REAL unexplained asks (K4, strict) | **8** | 0 | 0 |
| X7_REAL RIGHT_AND_PLAIN (P: RIGHT minus it must be <= 2) | 35 (**55 not plain**) | 0 | 38 (reported only) |
| X7_REAL question turns the chat did not route to the loop | 10 | 10 | 0 |
| X7_CONV RIGHT / WRONG / UNDETERMINED | 36 / **1** / 27 | 28 / 0 / 36 | 36 / 1 / 27 |
| X7_CONV RIGHT_AND_PLAIN | 34 (2 not plain) | 28 | 34 (reported only) |
| X7_NOISE RIGHT / WRONG / RIGHT_AND_PLAIN | 36 / 1 / 34 | 28 / 0 / 28 | - |
| NH-CHAT items lost by CHAT_ON vs LOOP_ON (RIGHT): X7_CONV / X7_REAL | 2 / **13** | | |
| N: items lost X7_NOISE vs X7_CONV (RIGHT_AND_PLAIN) / misrouted scored turns / misrouted noise turns | 0 / **10** / 0 | | |
| noise replies with a CAS token (128 noise turns) | 0 | 0 | |

Marks on practice: K1 met (97 >= 96); NH-CHAT missed (13 lost on X7_REAL); K3 missed (1 WRONG on X7_CONV, the same item
WRONG in LOOP_ON: a LEARN item, `CV22:pg:65706@84183`, HELM's reading of the lesson, not the chat's); K4 missed (8); P missed
(55 on X7_REAL); N missed (10 misrouted scored turns, all of them also misrouted without noise). Word on practice, had the
instruments held: `CHAT_WAVE_HARMED`.

**What the practice numbers say about the chat (observations, not tuning; nothing was changed in response).**
1. The chat routes a line to the loop only when `loop.wants_turn` says so, and `wants_turn` is the LICENSED English
   reader alone. Lines the licensed reader does not claim (`How much eggs can we make?` where "eggs" is a licensed
   ingredient name; `How much consomme can we make?` with its accent; `How much fish-balls ...`; wave 3b's question forms
   `Could you tell me how much X that makes?`; some lesson sentences) fall through to the chat's general reply ("I don't
   have verified data on that") and never reach the wide path, which in LOOP_ON reads them. That is every one of the 13
   REAL items and both CONV items lost, and all 8 unexplained asks and all 10 misrouted scored turns. Section 11 forecast
   this mechanism; the practice count (13) is far above the forecast (0-1).
2. The voice says a wide answer as `exactly 0.5 units` or `about 0.33 units`: a decimal with no dish name. Thirds, two
   thirds, 4/3 and the like are rounded, so they do not quote the yield (55 of 90 right REAL answers; 2 of 36 CONV). Halves,
   quarters and integers do.
3. On every one of the 110 STOCK_RECORDED turns in CHAT_ON the voice replied "That's outside what I know, so I'd rather not
   make something up" although the stock was recorded (the loop's own sentence, in CHAT_DIAG, says what was recorded). The
   stock turn is not scored; this is a reported row (`stock_recorded_but_reply_says_dont_know`).
4. The chat's lesson replies contain a Python list in the text (`Got it, now I know ['egg'] per batch of scone.`); no CAS
   token, so plain by the frozen rule, but not everyday English. Reported, not scored.
5. The twelve noise sentences were routed to non-recipe intents 128 of 128 times, with 0 CAS tokens; `Remember that I prefer
   short answers.` sets the chat's concise flag, which shortens later replies in that dialogue (part of the test, as frozen).

**Forecast after practice (not read by any program).** `CHAT_WAVE_HARMED` about 0.8 (NH-CHAT and N both missed on
practice by wide margins; K3's one WRONG depends on the draw); `CHAT_WAVE_NO_GAIN` about 0.02 (it needs NH-CHAT, K3 and N
all to hold); `CHAT_WAVE_EARNED_KEEP` about 0.01 (P alone would need thirds to vanish from the draw); `INCONCLUSIVE` about
0.17 (first host use of a chat harness; a custody or plumbing fault). The section 11 forecast stands as written; this one
replaces nothing, it is added beside it.

## 14. Amendment A-R1W7-2 (v2, written BEFORE the v2 reseal; coordinator decision FIX FIRST, as wave 6's A-R1W6-1; 2026-10-20)

**Why.** The v1 package (zip `5107b9c64407431a4804481259384e9bac86c1c07f8ec154f9319db1fbeb6db1`, freeze `eaf782e9…`) was never
launched and no exam was drawn from it. Its practice run (section 13) showed three defects in HELM's chat, not in the
test: the chat's gate dropped lines only the wide reader claims; the voice rounded yields ("about 0.33") and answered
a recorded stock with "That's outside what I know"; lesson replies printed a Python list. The coordinator decided FIX
FIRST: fix HELM, then reseal and test the fixed build. **v1 is `VOID_SUPERSEDED_BY_V2`** (kept beside the v2 zip as
`v1_void_HELM_R1_W7_20261020_SOURCE_R1W7_5107b9c6.zip`); it must never be shipped or scored.

**What changed in HELM (commit `1b0c6d62285313d98dca4cb2b11f3b3396abfdc1`, branch
`claude/helm-r1w7-chat-wave-packet-20261020`, PR #416 to the thread branch; built on `974fe36c`).** Against the v1 cut
exactly five of the 161 cut files differ: `helm_end_to_end_loop.py`, `helm_chat.py`, `helm_voice.py`,
`test_helm_wide_alongside.py`, `test_helm_brain_wide.py`. (1) `helm_end_to_end_loop.wants_turn` consults
`helm_wide_turn.read_wide` when the switch is on, so every line the wide reader claims reaches the loop. (2)
`helm_chat._speak` says a wide-path turn with the wide path's own sentence through the voice guard (exact amounts, the
dish name, "Noted: we have …"). (3) `helm_voice.say_amount` says kitchen fractions (denominator up to 16) exactly
("exactly 1/3", "exactly 1 1/3") and keeps "about" only for long decimals; mixed numbers parse; the lesson receipt
never prints a Python list. Three new tests in `test_helm_wide_alongside.py` (class E); the voice pin in
`test_helm_brain_wide.py` follows the new wording; HELM's suites Ran 197 OK on the fixed branch (194 in the eight
unittest files this package runs). `helm_brain_canonical.py` is byte-identical to its scored base `d4488f2a`
(`24df53c9…`). `build/CUT_CHECK_W7.json`: 161 of 161 files equal to `git show 1b0c6d62`.

**What changed in this package (labels and pins only).** `common_w7.HELM_CUT_COMMIT` = `1b0c6d62…`,
`PACKAGE_VERSION` = `v2`; `contract/HELM_CUT_R1W7.json` and `helm_now/SOURCE_CUT.json` re-cut; the runner's
`HELM_CUT_COMMIT`; `FROZEN_R1W7.json` (commit, branch, version); README, RUN_LIMITS and the stage note name v2. Two
recording additions, written after the v2 practice run showed them necessary and tuned to nothing: D-W7-17 and D-W7-18
below. **Unchanged:** every mark, threshold, arm, status word, seed band, exam size, instrument row and hard gate; the
twelve noise sentences; the neighbours; the practice pools; the owner line (still proposed, unsigned).

- D-W7-17 (I12 strips wall-clock fields). The loop's tool receipts carry `receipt_id` (a millisecond stamp),
  `elapsed_ms` and `timestamp_utc`, so two runs of the same turns are never byte-identical when the loop's own tool
  engine runs. The recorder unit now reports the raw byte comparison and the differing paths, and I12's
  "byte-identical" test compares the recorded loop results with those wall-clock keys removed. The other two proofs
  (wrapped = unwrapped chat memory record, turn for turn; every stored copy equals the dict the chat received) are
  unchanged and are the ones the recorder's transparency rests on.
- D-W7-18 (the loop's tool engine is reported). On the v2 practice run one dialogue line (`CV14`, the stock sentence
  "We have 6 C-peaches, sliced but we've run out of c-sugar.") was claimed by neither reader; HELM's loop then handed it
  to its own agentic engine (`helm_end_to_end_loop._not_checked_turn` -> `decompose_goal` / `execute_dag`), which ran
  the shell command `"<python>" --version` in `helm_now/` (status `AGENTIC_PLAN_EXECUTED`; one step
  `step_1_run_verification`, tool `execute_command`; the word "run" in "run out" is the trigger). Wave 3's harness
  stubbed this engine ("outside the circuit; refuses in the exam"); the chat as shipped does not. The harness does not
  patch it (section 2). Every record now carries `agentic_turns` (goal, tools, side effects) and every unit
  `agentic_tool_turns`; the reader reports them per exam and arm. No file changed and nothing left the scratch on
  practice (HG5 held). This is a HELM finding for a later round, not a tune: a recipe sentence should never start a
  shell command.

**v2 practice (same practice draw as v1; facts, not claims; 14 units, 66.2 s, every unit exit 0, 0 crashes).**

| Practice number, CHAT_ON unless said | v1 (`974fe36c`) | v2 (`1b0c6d62`) |
|---|---|---|
| X7_REAL RIGHT / WRONG / asks | 90 / 0 / 23 | **103 / 0 / 10** |
| X7_REAL fully learned of 106 (K1 bar 96) | 97 | 102 |
| X7_REAL unexplained asks (K4) | 8 | **0** |
| X7_REAL RIGHT_AND_PLAIN (P) | 35 | **103** (0 not plain) |
| X7_REAL question turns not routed to the loop | 10 | 0 |
| X7_REAL LOOP_ON RIGHT (unchanged code path) | 100 | 100 |
| NH-CHAT lost vs LOOP_ON: X7_CONV / X7_REAL | 2 / 13 | **0 / 0** (gained 2 / 3) |
| X7_CONV RIGHT / WRONG / UNDETERMINED / RIGHT_AND_PLAIN | 36 / 1 / 27 / 34 | 38 / 1 / 25 / **38** |
| X7_NOISE RIGHT / WRONG / RIGHT_AND_PLAIN; items lost to noise | 36 / 1 / 34; 0 | 38 / 1 / 38; 0 |
| misrouted scored turns (N; must be 0) / misrouted noise turns / noise replies with CAS | 10 / 0 / 0 | **5** / 0 / 0 |
| stock turns recorded but the reply said "outside what I know" | 110 of 110 | **0** of 115 |
| CHAT_OFF (yardstick) X7_REAL RIGHT; X7_CONV RIGHT | 0; 28 | 0; 28 |

Marks on practice (v2): K1, K4, P, NH-CHAT met; **K3 missed** (1 WRONG LEARN item on X7_CONV, `CV22:pg:65706@84183`,
WRONG in LOOP_ON too: the wide reader learns "1 cup of dry beans or whole pea" where the key's line reads otherwise;
HELM's lesson reading, equal with or without the chat); **N missed** (5 misrouted scored turns, all also misrouted
without noise: the four wave-3b question forms "Could you tell me how much X that makes?" / "How much X do we have the
makings of?" and "Hi again. How much eclair can we make?", which neither reader claims, so the chat answers them as
general questions or a greeting). Word on practice, had the instruments held: `CHAT_WAVE_HARMED` (by N and K3).

**Other v2 observations (facts).** The chat (CHAT_ON) answers 3 REAL items RIGHT that LOOP_ON (wave 3's loop build with
the triad wrapper) asks on, in v1 and v2 alike (`RW:pg:38193@134740`, `RW:pg:42450@482967`, `RW:pg:65061@548598`); the
cause was not investigated (no exam-side tuning). Faces dialogues (S1, S2, S6, S7: 18 items) stay UNDETERMINED in every
chat arm and in LOOP_ON on this practice draw. Replies now read "With what's on hand we can make 1/2 scone. Flour runs out
first, so it sets the limit." and "Noted: we have 2 cups of flour, 2 2/3 cups of milk, and 3/4 egg."

**Forecast after v2 practice (not read by any program).** `CHAT_WAVE_HARMED` about 0.6 (N needs 0 misrouted scored
turns; the question forms are 4 of 64 dialogues by construction, so N misses on every draw unless HELM reads them;
K3's one WRONG lesson depends on the draw); `CHAT_WAVE_EARNED_KEEP` about 0.1; `CHAT_WAVE_NO_GAIN` about 0.1;
`INCONCLUSIVE` about 0.2. The section 11 and section 13 forecasts stand as written.

## 15. Amendment A-R1W7-3 (v3, written BEFORE the v3 reseal; coordinator decision FIX FIRST, round 2; 2026-10-20)

**Why.** The v2 package (zip `7e7fa0665c74bf59aad890ca6a3cdbfeec2c9d47ea95432c9b0811e7c046b52d`, freeze `8275b5ea…`) was never
launched and no exam was drawn from it. Its practice run (section 14) showed four more HELM defects, none in the test:
a kitchen sentence neither reader claimed started the loop's tool engine and a shell command; wave 3b's question
forms and a greeting prefix were not read; an "X or Y" ingredient line was learned under a made-up name; "but we've
run out of X" was taken as stock. The coordinator decided FIX FIRST again. **v2 is `VOID_SUPERSEDED_BY_V3`** (kept as
`v2_void_HELM_R1_W7_20261020_SOURCE_R1W7_7e7fa066.zip`); it must never be shipped or scored.

**What changed in HELM (commit `dfc7158d0aba3cca7b0a1ccd1e1c2c8a74e36cf6`, branch
`claude/helm-r1w7-chat-wave-packet-20261020`, PR #416, now 2 commits on `974fe36c`).** Against the v2 cut exactly
four of the 161 cut files differ: `helm_end_to_end_loop.py`, `helm_chat.py`, `helm_wide_turn.py`,
`test_helm_wide_alongside.py` (the fifth changed file of the commit, `CHANGELOG.md`, is not in the cut). (1) The loop's
not-checked branch never calls the tool engine when the wide reader claims the sentence; its keywords match whole words
only and kitchen talk never counts; the chat's own software-goal trigger has the same rules and knows the wide brain's
ingredient names. (2) The wide reader claims "Could you tell me how much X that makes?" / "How much X do we have the
makings of?" and strips a leading "Hi again." / "Hello there!". (3) An "X or Y" ingredient line binds X (the K-R head
rule) and keeps "or Y" as a note of the line. (4) "…, but we've run out of X" is a reader question (code
`ABSENT_STATED`), never stock under a made-up name. Four new tests in `test_helm_wide_alongside.py` class F (one fails if
any shell command runs on a kitchen sentence); HELM's suites Ran 201 OK on the branch. `helm_brain_canonical.py` is
byte-identical to its scored base `d4488f2a` (`24df53c9…`). `build/CUT_CHECK_W7.json`: 161 of 161 equal to
`git show dfc7158d`.

**What changed in this package.** Pins and labels only (`common_w7.HELM_CUT_COMMIT` = `dfc7158d…`, `PACKAGE_VERSION`
= `v3`; the cut record; the runner's pin; FROZEN; README, RUN_LIMITS, stage note) and one reported row, D-W7-19.
**Unchanged:** every mark, threshold, arm, status word, seed band, exam size, instrument row and hard gate; the noise
sentences; the neighbours; the practice pools; the owner line (still proposed, unsigned).

- D-W7-19 (tool-engine turns reported). The reader reports, per chat unit, the number of turns on which the loop's tool
  engine ran (`reported.tool_engine_turns.per_unit`) and whether it is 0 in every chat unit; the recorder unit's count
  is included. It is a reported row, not a gate (the frozen gates were not extended). LOOP_ON and ALWAYS_ASK run through
  wave 3's harness, whose loop build stubs the engine, so there is nothing to count there. On the v3 practice run: 0 in
  every chat unit (v2: 1 turn in each of X7_CONV CHAT_ON / CHAT_ON_REPLAY / CHAT_DIAG and X7_NOISE CHAT_ON).

**v3 practice (same practice draw as v1 and v2; facts, not claims; 14 units, 63.3 s, every unit exit 0, 0 crashes).**

| Practice number, CHAT_ON unless said | v1 (`974fe36c`) | v2 (`1b0c6d62`) | v3 (`dfc7158d`) |
|---|---|---|---|
| X7_REAL RIGHT / WRONG / asks | 90 / 0 / 23 | 103 / 0 / 10 | 103 / 0 / 10 |
| X7_REAL fully learned of 106 (K1 bar 96) | 97 | 102 | 102 |
| X7_REAL unexplained asks (K4) | 8 | 0 | 0 |
| X7_REAL RIGHT_AND_PLAIN (P) | 35 | 103 | 103 |
| X7_REAL LOOP_ON RIGHT (unchanged code path) | 100 | 100 | 100 |
| NH-CHAT lost vs LOOP_ON: X7_CONV / X7_REAL | 2 / 13 | 0 / 0 | 0 / 0 (gained 2 / 3) |
| X7_CONV RIGHT / WRONG / UNDETERMINED / RIGHT_AND_PLAIN | 36 / 1 / 27 / 34 | 38 / 1 / 25 / 38 | **43 / 0 / 21 / 43** |
| X7_CONV LOOP_ON RIGHT / WRONG | 36 / 1 | 36 / 1 | 41 / 0 |
| X7_NOISE RIGHT / WRONG / RIGHT_AND_PLAIN; items lost to noise | 36 / 1 / 34; 0 | 38 / 1 / 38; 0 | 43 / 0 / 43; 0 |
| misrouted scored turns (N) / misrouted noise turns / noise replies with CAS | 10 / 0 / 0 | 5 / 0 / 0 | **0** / 0 / 0 |
| tool-engine turns in chat units (D-W7-19) | not recorded | 4 | **0** |
| stock turns recorded but reply said "outside what I know" | 110 of 110 | 0 of 115 | 0 of 115 |
| CHAT_OFF (yardstick) X7_REAL RIGHT; X7_CONV RIGHT | 0; 28 | 0; 28 | 0; 28 |

Marks on practice (v3): **every mark met** (K1 102 >= 96; K3 0 and 0; K4 0; P 0 not plain on both exams; NH-CHAT 0 lost;
N 0 lost, 0 misrouted). Word on practice, had the instruments held: `CHAT_WAVE_EARNED_KEEP`. This is a practice fact
about a draw the builder has seen; it decides nothing.

**Other v3 observations (facts; nothing tuned).** The 21 X7_CONV items not RIGHT in CHAT_ON are all UNDETERMINED: the
18 faces dialogues (S1, S2, S6, S7: the wide path asks for the stock it was just given, in the chat and in LOOP_ON
alike), 2 of the 4 R4 witness-in-English items (`CV23`, `CV25`), and 1 R7 item (`CV31`, whose stock sentence the loop
does not hold at the question). `CV22`, WRONG in v1 and v2, is now a learned lesson ("one soup needs 1 cup of dry bean")
and RIGHT. The limiting name of an "X or Y" line is said with the note in it ("Or chicken bouillon runs out first",
`CV18`), scored RIGHT by the K-R head. X7_REAL: 10 recipes are asked as `CLARIFY_ENGLISH_UNKNOWN_PRODUCT` (not fully
learned, so explained), 2 `UNDETERMINED_CLARIFY`, 1 `CLARIFY_NOT_CCE`; 25 of 128 not RIGHT in CHAT_ON, 15 of them
UNDETERMINED keys (not scored). Two wrapped runs of every recorder dialogue are byte-identical even before the
wall-clock strip (D-W7-17 now has nothing to strip on practice).

**Forecast after v3 practice (not read by any program).** `CHAT_WAVE_EARNED_KEEP` about 0.45 (every mark holds on the
practice draw; a fresh draw can hold a lesson form the reader learns wrongly (K3), a question form it does not claim (N),
or a yield said in a form the quoting rule does not read (P)); `CHAT_WAVE_HARMED` about 0.2 (K3 or N on one item);
`CHAT_WAVE_NO_GAIN` about 0.15 (P or K4 on one item); `INCONCLUSIVE` about 0.2 (first host run of a chat harness; a
custody or plumbing fault). The section 11, 13 and 14 forecasts stand as written.

## 16. Amendment A-R1W7-4 (v4, written BEFORE the v4 reseal; owner order 2026-10-20 "want the chat test rerun with the reader repaired"; 2026-10-20)

**Why.** The v3 package (zip `5063baba8be9ba807e7905d5f86732cb1a535ff5a533e67c79f5cbe16edbc6a9`, freeze `2366e85d…`,
HELM cut `dfc7158d`) ran on the host as job c51 (`RUN_RESULT_R1W7_C51.md`; reading `R1_W7_READING.json` sha256
`8f2f76468fef11e4d755083d2581578e04466e0d028a92848c8019ad945a5d4d`). The frozen reader said verdict `FAILURE`, word
`INCONCLUSIVE`: every instrument row true, all six marks true, 9 of 10 hard gates true, **HG5 (sandbox) false**. HG5 read
false because of a defect in the v3 reader and the v3 recorder unit's record, not because of HELM and not because of any
sandbox breach: HG5's row `helm_now_files_changed` demands a list from every one of the 14 units; the recorder-equality
unit (`W7_RECORDER_EQUALITY`) never wrote the field (`chat_harness.run_recorder_equality` built its record without it;
only the chat and loop units hashed `helm_now/` before and after), so the reader saw `None`, and `None == []` is false. The
v3 fixture (`tests_r1w7/fixture_run.py`) gave its synthetic recorder unit `"helm_now_files_changed": []` by hand, so every
planted-failure test of HG5 passed while the real gate could never hold; the v3 practice reading also read HG5 false, hidden
under `INSTRUMENT_ERROR` on the practice mock. A second plumbing defect: `kit/STAGE_R1W7.json` carried `"pythonpath": []`,
which the run-proven supervisor refuses (`PLAN_INVALID:r1w7_host_run:pythonpath`; c51 attempt 1 died before any stage);
the v3 kit test even asserted the empty list; the operator fixed it in the job plan only (D-OP-C51-1, attempt 2). Line 4
of this document forbids re-reading c51's data with a repaired reader; the c51 word stands. The owner ordered the rerun.
**v3 is `VOID_SUPERSEDED_BY_V4`** for any further run (its c51 record stands as written; nothing from c51 is licensed).

**What changed in this package (v4). Exactly these, nothing else.**

1. **The recorder unit writes `helm_now_files_changed`** (belt). `chat_harness.run_recorder_equality` hashes `helm_now/`
   before and after exactly as the chat and loop units do (`common_w7.tree_listing`) and writes the sorted list of
   changed paths. Its record is now built by one function, `chat_harness.recorder_doc`, which the real unit and the test
   fixture both call, so the fixture carries the field only because the real code writes it.
2. **The reader names and refuses a missing list** (braces). `merge_r1w7.hard_gates` HG5 now lists
   `units_missing_helm_now_files_changed` (every unit whose record has no list), `units_with_the_list` and `units_planned`
   (14), and HG5 holds only if that missing list is empty AND every list is empty AND the wave-1 tree hash is unchanged
   AND `helm_brain_canonical.py` equals its base AND every chat unit's session log sits under its scratch. A unit that
   does not write the list is still a failure, so no unit can dodge the gate. Reader string
   `r1w7.merge_r1w7 v2 (2026-10-20, A-R1W7-4: ...)`. The exact diff is in `READER_FIX_DIFF_V4.md` beside the zip.
3. **Three HG5 tests** (`tests_r1w7/test_units_w7.py`): on the clean fixture all 14 units carry `[]` and HG5 reads **true**
   (`units_with_the_list` 14 of 14); plant `HG5c` (the recorder unit lacks the field, the c51 shape) reads HG5 **false**
   and names `W7_RECORDER_EQUALITY`; plant `HG5d` (the recorder unit lists `helm_chat.py` as changed) reads HG5 **false**.
   The real recorder unit's test asserts `helm_now_files_changed == []` on practice turns.
4. **The stage plan:** `kit/STAGE_R1W7.json` `pythonpath` = `["HELM_R1_W7_20261020"]`, exactly what c51 attempt 2 ran
   (D-OP-C51-1; `run_c51_r1w7_20261020/payload_c51/execution/job_plan.json`). Every process is `python -X utf8 -B -I`, so
   `-I` ignores the PYTHONPATH the supervisor exports; the entry matters only to the supervisor's own plan rule. New
   `kit/stage_check_w7.py` (not a byte copy) runs the run-proven `plan_check` and refuses an empty `pythonpath` or an
   entry that is not a folder under the source root; `kit/plan_check.py` and `kit/job_supervisor.py` stay byte copies
   (`84257a23…`, `3b2337ca…`). The kit test runs the supervisor's own `validate_plan` on the sealed stage (passes) and on
   the stage with an empty list (`PLAN_INVALID:r1w7_host_run:pythonpath`).
5. **Exclusions:** `contract/EXCLUDE_R1W7_PRIOR_USED.json` gains block `X7_c51` = lists `X7_c51_real` (X7's 128 REAL ids)
   and `X7_c51_conv` (X7's 64 CONV pool ids), read by program from the custodian's seal record
   `x7_custody/X7_SEALED_20261021T024717Z.json` (ids only; no input, key or exam file opened; file sha256 in `sources`).
   **From v4 every list applies to BOTH pools** (`custody_w7.REAL_EXCLUDE_LISTS` = all 16 lists; `CONV_EXTRA_LISTS` = `()`).
   Reason: c51's custodian flagged 3 of X7's 128 REAL ids that also sat in X6's / X6v3's CONV lists (`pg:65501@21017`,
   `pg:6912@731078` in `x6_conv`; `pg:49958@479072` in `x6v3_conv`): no violation of the v3 contract (sections 4.1-4.2
   applied those lists to the conversation pool only), but a recipe seen in any earlier exam or pool should never be
   drawn again in either pool. Distinct excluded ids over all 16 lists: 1,466 (v3: 1,277 over 14). The practice pool rule
   (`practice_real_exclusions`, `practice_conv_exclusions`) is unchanged, so the builder's practice draw is the same as v1-v3.
6. **Seed bands** (section 10 superseded): REAL 2,000,000,001-2,001,000,000; CONV 2,002,000,001-2,003,000,000; NOISE
   2,004,000,001-2,005,000,000 (each 1,000,000 wide; all below INT32_MAX 2,147,483,647). Used table 1-1,999,000,000 as one
   range (wave 6 v3 up to 1,989,000,000; v3 / c51's bands 1,990,000,001-1,995,000,000 are spent by the X7 draw; the
   continuity packet proposes 1,996,000,001-1,999,000,000, reserved here so the two never collide); gap 1,000,000; slot
   stepping and STOP as before. v4 needs fresh bands because the seed rule's used table must cover every band a sealed
   exam was drawn from, and X7 was drawn from v3's bands.
7. **The owner's line** (section 8 superseded): **`CHAT WAVE 2 at 1 USD`** (20 UTF-8 bytes; the v3 line `CHAT WAVE at 1 USD`
   (18 bytes) was consumed by c51's approval record `f28543bc…` and must never bind a second zip). Seed text
   `H = sha256(UTF-8("CHAT WAVE 2 at 1 USD" + ":" + <v4 zip sha256, 64 lower-case hex>))`, no trailing newline; the exam seed
   is derived from the owner's line and the v4 zip, so nothing is drawn until the owner writes that line. Cap 1.00 USD;
   one attempt + one plumbing retry; expected about 0.02 USD.
8. Labels: `PACKAGE_VERSION` = `v4`; `RUN_LIMITS_R1W7.json` `package_version`; the stage note; README; FROZEN re-derived
   from the constants (the kit test checks they agree).

**Unchanged (checked by the tests and the freeze):** HELM under test, commit `dfc7158d0aba3cca7b0a1ccd1e1c2c8a74e36cf6`
(`helm_now/` byte-identical to v3: every one of the 161 cut files + `SOURCE_CUT.json` hashes to v3's freeze;
`helm_brain_canonical.py` = base `d4488f2a` `24df53c9…`); every mark, threshold, arm, status word, exam size, instrument
row, the other nine hard gates and HG5's other four rows; the noise sentences; the five neighbours by freeze; the practice
pools; the scoring functions; the units and their commands (the recorder unit's command line is the same; only its record
gained one field).

**What this amendment does not do.** It does not re-read c51. It does not launch. It does not draw an exam. It licenses
nothing. The v4 forecast is the v3 forecast (section 15): on c51's exam every mark held as a fact; a fresh draw can still
miss one.
