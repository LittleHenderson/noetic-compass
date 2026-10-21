# PREREGISTRATION_CONTINUITY_V1 — a thread must survive an interruption and resume by return address (pre-code, 2026-10-20 PDT)

Status: DESIGN, WRITTEN BEFORE ANY CODE. Owner order (2026-10-20): "continuity packet". Owner's idea (2026-10-15): "LIKE INTERRUPTING A PERSON WHILE THEY DEEP IN THOUGHT OR ASKING SOMEONE TO THINK ABOUT SOMETHING". Owner ruling: "RPA IS ATLAS".
Nothing here is a result. Every number below is frozen now; the frozen reader applies them; no one re-reads them after the data exists. Claim status of every mechanism stays `ENGINEERED-NOT-VALIDATED` until the reader says otherwise.

## 0. What is being asked, plainly

HELM is given a question it cannot finish in one line (it has to ask for one missing amount, or the gate sends it to repair). That unfinished thought is a thread. Before the thought is finished, a person types something else. Does HELM (a) answer the new line exactly as it would have with no thread open, (b) put the thought down without doing any thought work while answering, and (c) pick the thought back up at the exact station it left, by its return address, and finish it right, with nothing in its brain changed by the interruption except what the new line itself wrote?

Design the path is in `DESIGN_CONTINUITY_V1.md` (same folder). The cheap baseline below is meant to be a real threat: if saving the last claimed line of chat and starting over resumes as well as the path does, the path earns nothing and the status word says so.

## 1. Gate answer (one sentence)

"With the continuity switch on, does an open thread survive a chat interruption and resume by its return address to the right station with the right answer and an unchanged brain, while the conversation never waits on it, better than throwing the thread away or restarting from the last saved line?"

## 2. What is under test

- **HELM cut:** the HELM files of thread branch `claude/project-thread-pmbzd6` at the commit that lands the build of `DESIGN_CONTINUITY_V1.md` section 4 (`helm_continuity.py`, the hooks in `helm_end_to_end_loop.py` and `helm_chat.py`), after the wave 7 reading is on the spec sheet (sequencing rule, DESIGN section 5). The package carries its own copy (`helm_now/`, by `git show`); every file's sha256 is listed in `contract/HELM_CUT_CONT1.json`.
- **The switch:** `HELM_CONTINUITY` (default OFF). CONT_ON sets it to `1`; every other arm leaves it unset.
- **The chat:** `helm_chat.HELMConversationalSession(mode, session_id)` driven through `handle_turn(text)` one line at a time, replies captured from standard output, `HELM_SESSION_DIR` inside the unit's scratch (wave 7's harness pattern, D-W7-1 / D-W7-4). The harness never patches `helm_chat`. In every arm the wide brain is as shipped (ON); Q3 in `OPEN_QUESTIONS.md` is the owner's say on running a second pass with it OFF.
- **Station driving:** a thread's stations between lines are driven by the harness through `ThreadBook.idle_tick()` (one crossing per call, test-only), so the interruption lands between two named stations. The chat itself has no idle advance in v1.
- **Reused, unchanged, by import from sealed neighbours:** wave 6 v3's custody and seed-rule helpers; wave 7's chat recorder and its transparency test (I12); wave 1 v3's licensed brain (the loop loads it).

## 3. Arms

| Arm | What | Why |
|---|---|---|
| **CONT_ON** | the switch on: the thread is cut at the line, suspended by `ReturnStack.suspend`, resumed by the exact six-field address after the reply | **the arm under test** |
| RESTART_BLANK | the switch on, but on every interruption the thread is cancelled (`ReturnStack.cancel`) and nothing is resumed; a later line that re-asks starts a fresh turn | the mechanism-free floor: "throw the thought away" |
| RESTART_LAST_LINE | the switch on, but no station record and no address: on interruption the harness keeps only the text of the **last line the loop claimed** (`wants_turn` true) before the interruption; after the reply it feeds that line to `process_turn` again as a fresh turn | the cheap threat: "start over from the last thing you were asked" |
| CONT_OFF | the switch unset: today's live loop and chat, no thread book | the conversation yardstick: CONT_ON's chat replies must equal these |
| CONT_ON_REPLAY | CONT_ON again, fresh process | HG2 replay |
| CONT_ON_NOINT | CONT_ON on the same worlds with the interrupting lines removed (the slot line follows the opening directly) | the reference answer and the reference brain digest for marks PLACE, DIGEST and ANSWER |

All six arms run on every world. One process per (arm, family) pair.

## 4. The exam (drawn blind by a separate custodian; the builder sees hashes and counts only)

### 4.1 Worlds

Synthetic worlds only, built by the custodian's program from the two seeds below, with the recipe brain's own synthetic world generator (wave 3 / wave 6 families, `gen_conv`-style templates) so that every right answer is known. Each world is one chat session with this shape:

1. **Teaching lines** (0 to 3): recipe lessons in the frozen template forms the licensed reader claims.
2. **Opening line** (`t0`): a question or request that today ends `WAIT_FOR_USER` with a named slot (a missing stock amount) or opens a repair at the gate. This opens the thread. The thread's remaining work is 2 or 3 stations.
3. **Interruption** (`t0+1` to `t0+k`, k drawn from {1, 2, 3}): the lines of the family below.
4. **Slot line** (`t0+k+1`): the line that fills the named slot ("There is 4 cups of flour." in the frozen form) or, for a repair thread, the line the child needs.
5. **Nothing more.** The thread's answer, if any, is what HELM says after the slot line. No re-ask of the opening question is ever sent (a re-ask would hand the baselines the answer).

### 4.2 Families (16 worlds each; 64 worlds)

| Family | Interrupting lines | What it tests | Expected honest outcome for the baselines |
|---|---|---|---|
| F-A SMALL_TALK | 1 to 3 small-talk lines from wave 7's frozen list of twelve | the plain cut and resume | RESTART_LAST_LINE's last claimed line is the opening line itself, so it restarts the thought from S0 and reaches the same answer: **a tie on ANSWER is expected here** |
| F-B UNRELATED_STOCK | 1 to 3 stock lines about ingredients the thread does **not** cite (the Bias version moves; no cited fact changes) | resume with a newer Bias that is not stale | RESTART_LAST_LINE restarts from its last claimed line, which is now the unrelated stock line, not the opening: it reaches no answer |
| F-C CITED_STOCK | 1 stock line that changes an amount the thread **cites** | the stale rule: the thread must go DIRTY and restart, never resume | a resume here is a hard-gate failure (HG7); RESTART_LAST_LINE re-runs the stock line and reaches no answer |
| F-D TWO_THREADS | a second opening line (a second thread, a different product) then 1 small-talk line, then the first thread's slot line, then the second's | two open threads told apart by address alone | RESTART_LAST_LINE holds one line, so one thread is lost |

Interruption station: for each world the interruption lands after station `S_i` with `i` drawn uniformly from the thread's crossed stations {1, ..., n-1} (never at S0, never after the last station), from the INTERRUPT seed. The custodian records the drawn station per world in `X_CONT_PINS.json`.

### 4.3 Counts and vacuity

64 worlds (16 per family, 4 families); every world's thread has 2 or 3 remaining stations at the interruption; I14 fails if any family has fewer than 16 worlds or if fewer than 48 worlds have a known right answer under CONT_ON_NOINT.

## 5. Scoring (per world; the frozen reader)

- **RESUMED**: the thread's record reaches state FINISHED after the slot line (any arm). In RESTART_BLANK this is 0 by construction (a cancelled thread never finishes); reported.
- **RIGHT_PLACE**: the stations crossed after the resume equal the thread's `remaining_work` at suspend, in order, with no earlier station re-crossed and none skipped, and the resume's address equals the suspend's address field for field. Scored for CONT_ON and CONT_ON_REPLAY only; the baselines have no address (reported as NOT_APPLICABLE).
- **ANSWER_RIGHT**: HELM's reply after the slot line has the same loop status, output value and limiting-reagent name as CONT_ON_NOINT's reply to the same world. Scored in every arm.
- **DIGEST_SAME**: the brain digest (sha256 of the recipe book bytes plus the canonical JSON of the stock) at the end of the world equals CONT_ON_NOINT's end digest for the same world **after** the interrupting lines' own writes are applied to the reference (the reference arm replays those lines after its answer so both ends hold the same facts). Scored in every arm.
- **CONV_SAME**: for every interrupting line, CONT_ON's chat reply text and recorded intent equal CONT_OFF's for the same line in the same world. Scored for CONT_ON.
- **CUT_CLEAN**: the number of trace rows carrying a `thread_id` with a tick inside any interrupting line's window `[tick_in, tick_reply]` is 0, summed over the world. Scored for CONT_ON. (The window is the chat turn's own; every crossing carries its tick; so a missing cut shows as a count above 0. This check can fail.)
- **WORK**: the number of station crossings written after the first interruption until the thread's answer (or the end of the world). Reported for every arm; used by the margin in section 6.

## 6. Instrument rows, hard gates, marks, status word

**Instrument rows** (any false -> `INSTRUMENT_ERROR`, `INCONCLUSIVE`): I0 not a practice mock; I1 data identity (this package's freeze and every member; `helm_now/` equals `contract/HELM_CUT_CONT1.json`; the world files by the custodian's pins); I6 completeness (every unit exit 0; every carried suite OK; every arm holds every world); I7 reading from the sealed zip; I9 governance (the approval record holds the owner's line verbatim and binds this zip and freeze); I10 seed rule (section 10); I12 the recorder is transparent (wave 7's equality test, run here); I14 not vacuous (4.3).

**Hard gates** (any false -> `FAILURE`, `INCONCLUSIVE`):
- HG1 receipts: every thread's receipt chain verifies (each sha256 covers the previous entry; the first carries 64 zeros); every saved cube in every arm carries a receipt hash.
- HG2 replay: CONT_ON = CONT_ON_REPLAY record for record (thread records, loop statuses, values, reply text).
- HG3 key-blind: no world key file on the host.
- HG4 no network: socket guard in every unit, 0 attempts.
- HG5 sandbox: the licensed brain folder hashes the same at start and end; `helm_brain_canonical.py` equals its pinned base bytes; every file written lies under the unit's scratch.
- HG6 no crash: every `handle_turn` and every `idle_tick` returned without an exception in every arm.
- HG7 the stale rule: in family F-C, 0 threads resumed in CONT_ON; 16 of 16 marked DIRTY with the ancestor chain invalidated; 0 facts written by a dirty thread.
- HG8 switch hygiene: CONT_OFF units never import `helm_continuity`; CONT_ON units do; the OFF fixture's receipt hash equals the pinned pre-change sha256; ON and OFF receipt hashes equal on the same fixture.
- HG9 same inputs: one input sha256 per family per arm.
- HG10 exactness: 0 resumes accepted on an inexact address, a cancelled or finished thread, an older Bias, or a root shortcut (the harness sends one planted attempt of each kind per family; each must be refused with its named code).
- HG11 no thread write: 0 cube writes between a thread's opening and its finish other than those the gate makes on finishing (a thread never writes a fact while open).

**Marks** (decide the word; never gates; every number frozen):

| Mark | Rule | Why |
|---|---|---|
| CUT | CONT_ON: CUT_CLEAN = 0 on 64 of 64 worlds | the conversation never waits on the thread |
| CONV | CONT_ON: CONV_SAME on every interrupting line of 64 of 64 worlds | the thread book changes no reply to the person |
| DIGEST | CONT_ON: DIGEST_SAME on 64 of 64 | the brain's digests unchanged by the interruption |
| PLACE | CONT_ON: RIGHT_PLACE on >= 46 of the 48 worlds in F-A, F-B, F-D (F-C must not resume) | resumed to the right place, by address |
| RESUME | CONT_ON: RESUMED on >= 46 of 48 (F-A, F-B, F-D) | resumed at all |
| ANSWER | CONT_ON: ANSWER_RIGHT on >= 46 of 48 (F-A, F-B, F-D) and on >= 14 of 16 in F-C (the dirty restart must still answer right once the slot line lands) | finished right |
| THREAT | CONT_ON ANSWER_RIGHT (all 64) minus RESTART_LAST_LINE ANSWER_RIGHT (all 64) >= 12, **and** CONT_ON WORK total <= RESTART_LAST_LINE WORK total minus 32 | the cheap baseline must be beaten on answers and on wasted work, else the path earns nothing |

Reported rows (no word): per-family tables for every arm; RESTART_BLANK totals; RESTART_LAST_LINE's per-family ANSWER_RIGHT (F-A is expected to tie); WORK per arm; the interruption station histogram; CONT_OFF ANSWER_RIGHT (expected near 0: today's loop never re-asks); every refusal code count from HG10; the number of FORM_GAP crossings per station kind (LM-T4's TAP-4 finding carried forward).

**Verdict:** `INSTRUMENT_ERROR` if any instrument row is false; else `FAILURE` if any hard gate is false; else `PASS`.

**Status word** (frozen order; the first that holds):
1. `INCONCLUSIVE` — verdict not PASS.
2. `CONTINUITY_HARMED` — CUT, CONV or DIGEST missed (the path cost the conversation or the brain something).
3. `CONTINUITY_NO_GAIN` — THREAT, PLACE, RESUME or ANSWER missed (the path did not beat starting over, or did not resume to the right place).
4. `CONTINUITY_EARNED_KEEP` — everything above holds.

## 7. What a pass licenses, and what it never licenses

- `CONTINUITY_EARNED_KEEP`: status `VALIDATED` for this sentence only, ceiling `SYNTHETIC_ONLY`: "On fresh blind synthetic chat worlds, with the continuity switch on, HELM's open thought was cut at the line with 0 thought work during the person's turn and no change to any reply, was resumed by its exact return address to the saved station on at least 46 of 48 eligible worlds, finished with the right answer on at least 46 of 48 and after an honest dirty restart on at least 14 of 16, left the brain's digests equal to the uninterrupted run, and beat restarting from the last saved line by at least 12 answers and 32 station crossings." The switch stays default OFF after a pass; turning it on by default is the owner's decision on a later word.
- `CONTINUITY_HARMED` / `CONTINUITY_NO_GAIN` / `INCONCLUSIVE`: no claim; the misses are recorded as negatives; every mechanism stays `ENGINEERED-NOT-VALIDATED`.
- **Never, by this exam** (the `NOT LICENSED` list): that HELM "thinks between lines" (no idle advance exists in v1); that language crossed an Atlas (the anchor is a binding, not language; LM-T4's ruling stands); that the thread understood anything; typed English by real people; real kitchens; the Eyes or the drive loop; the 28 cells or 22 pathways; statistical superiority (one run, one draw); any claim about the wide brain beyond the shipped switch state; any word about wave 7 (§7.98), which is a different exam on a different cut.

## 8. Units, host and cost

- Units: 6 arms x 4 families = 24 units, plus 1 recorder-equality unit = **25 units**, one process each, `python -X utf8 -B -I`.
- **Laptop first, 0 USD.** The thread book, the three packages and the custody tools are standard library; the loop loads the licensed brain (small) and, as shipped, the wide book. Wave 3's parts ran under a 300 MiB per-part limit with a start rule of at least 300 MB free RAM; the loop's wave-3 harness ran on AWS because it had 20 parts of up to 300 s driving thousands of idle ticks, not because one part needed more memory. This exam has 64 short chat sessions per unit. Rule: the builder measures the peak working set of one unit on practice; if every unit's peak is at or under 300 MiB and the laptop reports at least 400 MiB free at start, every unit runs on the laptop in sequence (one at a time), 0 USD.
- **AWS only if the laptop rule fails** (a unit's practice peak above 300 MiB, or the start rule not met on two tries an hour apart): one m6i.xlarge-class CPU host (the kit's 2-CPU / 14 GiB slice), us-west-2, runner deadline 2,400 s, expected 0.02 to 0.10 USD, **cap 1.00 USD**, one attempt + one plumbing retry. Owner's line to sign, proposed: `CONTINUITY at 1 USD` (19 UTF-8 bytes). On the laptop no line is needed beyond the owner's word to seal and run.

## 9. Builder's practice (facts, never a claim)

The builder may run every unit on a PRACTICE draw only (its own seeds, below 1,000,000, `practice_mock: true` in every record; the reader refuses a practice record as an instrument problem). Practice counts go in `TEST_RECORD_CONT1.md` with the forecast of section 11; they decide nothing. A FIX FIRST round on practice is allowed and must be recorded as wave 7's were (§7.98).

## 10. Custody and seeds

Seed text `H = sha256(UTF-8(owner line + ":" + full zip sha256))`, no trailing newline (RB-W1T / wave 6 / wave 7 rule). For a laptop run with no paid line, the owner's word to run (verbatim, as recorded) stands in for the line. Bands, each 1,000,000 wide, above every band used or reserved so far (wave 7 reserved up to 1,995,000,000: REAL 1,990 M, CONV 1,992 M, NOISE 1,994 M):

| Band | Range | k |
|---|---|---|
| WORLDS | 1,996,000,001 to 1,997,000,000 | int(H[0:16], 16) |
| INTERRUPT | 1,998,000,001 to 1,999,000,000 | int(H[16:32], 16) |

Used table 1 to 1,995,000,000 as one range; gap 1,000,000; slot stepping and STOP as wave 6; every step written to `SEED_DERIVATION_X_CONT.json`. The custodian runs `cont1.custody_cont seal` from an extracted copy of the sealed zip, laptop only, 0 USD, and ships a carrier `X_CONT_CARRIER_V1.zip` (top folder `x_cont`: `INPUTS_CONT.json` with the 64 worlds' lines, `X_CONT_PINS.json` with the interruption station per world; no key file). Keys (the right answers under no interruption, the thread's expected remaining work) stay in `x_cont_custody/exam/` on the laptop. The operator copies, hashes and compares; never opens an exam file. The builder never handles a carrier.

## 11. Honest predictions (written before any code; not read by any program)

- CUT: the two hooks are small; the risk is an early `return` in `handle_turn` that skips `after_reply` and leaves a thread WAITING forever (that is not a CUT miss but a RESUME miss). CUT met about 0.8.
- CONV: the thread book touches no reply; met about 0.9. The way it misses: a resumed thread's reply printed during the next person's turn instead of after the slot line.
- DIGEST: met about 0.8; the way it misses: the reference arm's replay of the interrupting lines applies writes in a different order than the live run.
- PLACE / RESUME: the return-address rules are strict and refusals are cheap to trip (a Bias version equal, not newer, after a small-talk line that wrote nothing); the design resumes with `returned_bias_version = current`, which equals the suspended version in F-A. Return-address rule 4 as written refuses `BIAS_EQUAL_NOT_NEWER`; D-C1-3 below decides this before code. Met about 0.6 each.
- THREAT: F-A ties by construction (16 of 16 for both); CONT_ON must win on F-B, F-C and F-D (up to 48 worlds against RESTART_LAST_LINE's near 0 there) to clear 12; the work margin of 32 is cleared if F-B and F-D alone restart 2 or more stations each. Met about 0.65.
- Word: `CONTINUITY_EARNED_KEEP` about 0.35; `CONTINUITY_NO_GAIN` about 0.3 (PLACE or RESUME on the refusal rules); `CONTINUITY_HARMED` about 0.15 (DIGEST order); `INCONCLUSIVE` about 0.2 (first harness of thread records; HG10's planted attempts are new instrument work).

## 12. Deviations and decisions (numbered; appended, never edited away)

- D-C1-1: the chat is driven through `handle_turn` with stdout captured; `exit` / `quit` / `q` / `help` / `dials` / `history` / `mode` are never sent.
- D-C1-2: stations between lines are driven by the harness (`idle_tick`), not by the chat; v1 has no idle advance.
- D-C1-3 (to settle before code, Q4): resume after an interruption that wrote nothing has `returned_bias_version` equal to the suspended version. Either the return-address rule 4 (`BIAS_EQUAL_NOT_NEWER`) is kept and the cut bumps the Bias version by one on suspend (a bookkeeping write, no fact), or an interruption resume is a distinct call that accepts equal. The choice is written here before the seal; the reader applies whichever is written.
- D-C1-4: RESTART_LAST_LINE keeps the last line `wants_turn` claimed, not the last line typed; this is the stronger baseline (it never restarts from small talk).
- D-C1-5: the reference arm CONT_ON_NOINT replays the interrupting lines after its answer so DIGEST compares equal fact sets.
- D-C1-6: the owner line and the laptop-first rule are proposed, not signed (as wave 7's D-W7-16).
