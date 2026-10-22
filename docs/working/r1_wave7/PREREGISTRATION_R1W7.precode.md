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
