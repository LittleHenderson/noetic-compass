# CTT-2R PREREGISTRATION — the acceptance rule ACCEPT-2 on the EXISTING c45 weights ("RULE FIRST")

Written 2026-10-19 (Pacific; UTC inside records) by the CTT-2R builder (a Claude session), BEFORE any code of this
packet exists. The sha256 of this file as first written is kept beside it (`PREREGISTRATION_CTT2R.precode.sha256`).
Any later change is a dated amendment at the end; nothing above an amendment is edited.

Claude is not the research governor. This file freezes a test. It changes no claim status. Claim status of the
CAS-token translator stays **`ENGINEERED-NOT-VALIDATED`** until a frozen program reads a result.

## 0. Status, authority, money

- **Owner's word (verbatim, pinned bytes):** `CTT RULE TEST at 1.50 USD` (25 UTF-8 bytes). Source:
  `Documents\Codex\2026-10-18\OWNER_APPROVALS_20261018.md`, the line beginning
  `## Owner words (2026-10-19 night, verbatim): ""CTT RULE TEST at 1.50 USD";`. The approval record quotes these
  bytes BY PROGRAM (`ctt2r/seed_rule_2r.py line`), never by hand.
- **Cap 1.50 USD** for the paid run (one small AWS GPU instance), **one attempt + one plumbing retry**. Pre-approved;
  it launches after a blind custodian draw, without a re-paste. A change of scope or cap needs a new owner word.
- The writer calls for the new LLM pool (Gemini free tier + DeepSeek) are NOT AWS and not inside the 1.50 USD; the
  owner accepted them under pick Q5 ("NEW LLM POOL", under 0.50 USD; c45's pool cost about 0.015 USD).
- **Design implemented:** `Documents\Codex\2026-10-19\ctt2_design_v1\` (DIAGNOSIS.md, ACCEPTANCE_RULE.md,
  EXAM_DESIGN.md, TRAINING_CHANGES.md, OPEN_QUESTIONS.md), with the owner's accepted picks: **RULE FIRST, BOTH
  KITCHEN AND REAL, ALL THREE AGREE, KITCHEN ONLY NOW, NEW LLM POOL / HUMAN WHEN READY.** This is CTT-2a of
  TRAINING_CHANGES.md: rule only, **no retraining**.
- **The confident-wrong cap is NOT raised.** It stays at most 2 proposed per 128 singles and 0 saved. (The owner asked
  whether raising it would be fine because HELM rejects wrong readings anyway. Coordinator answer, recorded here: no.
  The cap counts plausible wrong readings put in front of the user. The read-back already stops them being saved; the
  cap measures how often the user is shown a wrong reading. The fix is the agreement rule, not a looser cap.)

## 1. The question, in plain words

CTT-1 (job c45) trained a small translator (9,585,566 parameters, three copies trained from three random starts).
On LLM-written kitchen English it read more turns right than HELM's reader alone, but two of the three copies showed
the user too many confident wrong readings (5 and 3; cap 2). The diagnosis found that every wrong single-turn reading
sat on a turn where the three copies did NOT agree.

**CTT-2R asks:** if HELM offers a translator reading only when all three trained copies give the identical reading,
and only asks the user to confirm it (never acts on it before a yes), does the translator then (a) read more turns
right than the reader alone, (b) beat a no-learning "copy the closest training sentence" rival held to the same rule,
and (c) stay under the confident-wrong cap — on NEW kitchen turns AND on real public sentences that state stock which
the reader gives up on?

Nothing is trained. The six c45 models are used exactly as they are (sha256 pinned in section 2).

## 2. What is frozen and reused (never modified)

| Thing | Pin | Use |
|---|---|---|
| CTT v3 package `HELM_CTT_20261019_SOURCE_CTT.zip` | `f280633da498466fe713b33d37fe90db221bc3dbf4ce9fe69538460be82cee31` (freeze `24f89718…`, 51 members) | imported unchanged: translator process code, grammar lock, checker, slots, vocabulary, retrieval, NO-HARM harness, scoring helpers |
| A4-s1 `final.pt` (9.6 M, seed 1) | `db53775be8e46f6234548e5c4f5c1cbd4f7a376b0de06db87aa45b819fbf3a68` | voter 1 |
| A4-s2 `final.pt` | `16aebd0dfb32a5a14a387aa1c1dca9b9bc06e0ad179c4ca1d95566d74fc7f855` | voter 2 |
| A4-s3 `final.pt` | `76abf0195c2c71cccf9b44798e78c4bc3245995b56d446643cbc3e33efe2ceed` | voter 3 |
| A5-s1 `final.pt` (2.5 M twin) | `525898b8812274f1e15daa2ff171c69ce99485970242494039b9b232f6158315` | reported only |
| C1-s1 `final.pt` (shuffled pairs) | `e7028fe7dd584803d7ca931990b385b66fad5544eea3dd90b23a11f435256785` | reported only |
| C2-s1 `final.pt` (random init, never trained) | `d293039bec8e29becfd184cf2770499f3165af4a25e4f5ca2d35cfb2e914aae3` | control voter 1 |
| `vocab.json` | `825b417a62b6df94567fdb686200988b92a058cafefb127561c661c28db1265a` | the vocabulary the weights were trained with |
| `train.jsonl` (227,497 rows) | `d92a070b695a93ee02b49e39c90e876e568650afb4d84d5de4f3987f92511b8b` | the retrieval rival's rows; leakage check |
| `DATA_MANIFEST_CTT.json` | `513d958092ac2b056d9f498310607fa311b6d0797e29db1267cf2fbe2e9ef101` | provenance |
| c45 `NOHARM_OFF.json` | `9b7cec6d8051130e4916e33a623bf22aa6dfb6bc487a62e12d4bdba812adbe93` | the OFF digests the ON run must equal |
| c45 deliverable zip (holds all of the above) | `3a1a71429b603c57a5d25fae942d7e20e4563be6bb923d1e6b02e0766c88e628` | backup at `D:\tksCAS-archive\ctt1_c45_20261020\` (three sha256 passes, c45) |

The weights are on the laptop at `Documents\Codex\2026-10-19\cas_token_transformer\run_c45_ctt1_20261020\a1_unpacked\
c45_out\ctt_out\` and inside the archived deliverable zip; both were re-hashed 2026-10-19 and match the pins.

**Reader.** A0 is **reader v1.1** (PR #378, rule 6 STOCK_FRAME_REQUIRED), the four files pinned by RTR-1:
`helm_english_in.py` `31c8a078…`, `helm_end_to_end_loop.py` `69f1ae55…`, `helm_voice.py` `a47726db…`,
`helm_chat.py` `905c1fc2…` (+ the PR's test file `02c7eef9…`). They are laid over a copy of the sealed wave-3 v3
`helm/` folder (zip `152bca2a…`); every other file must equal the wave-3 freeze. CTT-1's A0 was the v1.0 family
(DIAGNOSIS.md section 5); RTR-1 (c44) measured v1.1 at 115 of 115 scored real sentences right, 0 wrong.

**Which lexicon, and why.** The scored path uses **no Noetic lexicon**. `helm_english_in.read()` reads stock,
absence, topics and batch reports from HELM's own name table and number words; it never looks up a Noetic word. The
branch's newest reader (`v1.2`, commit `a7b1650a`) equals v1.1 plus one added function `noetic_reading()` that loads
lexicon_v3 (switch `HELM_LEXICON_V3`, default ON). `read()` never calls it, so v1.1 and v1.2 read kitchen turns
identically. This test pins v1.1 because RTR-1 sealed and measured exactly those bytes. `HELM_LEXICON_V3` is left
at its default and has no effect here. E-NOTATION (the only CTT part that uses a lexicon, the frozen lexicon_v2) is
not part of CTT-2R. Part R's answer keys use X-REAL's own pinned word lists (`xreal/WORDLISTS.json`), unchanged.

## 3. The acceptance rule ACCEPT-2 (applied to every turn, in this order; the first step that fires decides)

| Step | Rule |
|---|---|
| 0 | **Reader first.** Reader v1.1 reads the turn. If it reads (it would not ask), its reading stands; no model is called. |
| 1 | **Ask by default.** If any later step fails, HELM asks its own question. Nothing is written. |
| 2 | **All three agree.** The three main copies A4-s1, A4-s2, A4-s3 each decode the turn (grammar-locked greedy, frozen). A reading is a candidate only if **all three** produce a reading, **each** passes every check of the frozen checker (grammar, pointers, names, amounts, one story, round trip), and the three checked forms (`cce.normalize`d, from the checker) are **byte-identical**. One silent copy, one failed check or one difference = ask. |
| 3 | **Read back everything.** A candidate is OFFERED, never USED, until the user says yes. This includes topic-only readings ("Just to check: you're asking about bread?"). The read-back quotes every amount and name of the reading verbatim, and the product word for a topic. |
| 4 | **Session cap.** At most 2 model offers per dialogue session. After a user "no" to a model offer, the translator is silent for the rest of that session (the reader still reads). A single turn is a one-turn session. |
| 5 | **Log, never decide.** Per proposal: (a) margin = the smallest gap, over all output steps, between the best and the second-best ALLOWED token log-probability (teacher-forced over the greedy output; logged only); (b) which copies agreed; (c) an evidence-alignment verdict (each stock clause has its amount span and its name span inside one clause of the sentence; each absence clause has a negation cue from a closed list inside the clause of its name); (d) for every wrong reading, a diff class against the key: MISSING_CLAUSE, EXTRA_CLAUSE, WRONG_AMOUNT_BINDING, WRONG_NAME, WRONG_KIND, WRONG_POLARITY, WRONG_CONTEXT_REF. Counts only in the reading. |

Not in the deciding rule (design section 2): the twin as a fourth voter, a 2-of-3 majority, any margin threshold.

**The scripted user.** It says yes to an offered reading only if the reading equals the answer key (the CTT-1 rule).
So no wrong reading is ever saved; the danger count (CWFW) is counted at the offer, BEFORE the read-back, exactly as
in CTT-1.

**Quantity and new-name read-back (ACCEPTANCE_RULE.md, unchanged):** every reading that would write an amount, an
absence or a batch is read back with every amount and name quoted (the checker's own read-back, gate H-READBACK);
a name outside HELM's eight ingredients and four products is never a reading (the checker asks UNKNOWN_INGREDIENT /
UNKNOWN_PRODUCT); a topic-only reading is now read back too (new in ACCEPT-2).

## 4. Arms

| Arm | What | Role |
|---|---|---|
| **A0** | reader v1.1 alone (asks whenever it would ask) | baseline: today's reader |
| A1 | always ask | reported (what silence scores) |
| **A4E** | reader v1.1 first + translator under ACCEPT-2 (three-copy vote A4-s1/s2/s3) | **the arm under test** |
| **A2E** | reader v1.1 first + copy-closest under ACCEPT-2: the 3 training rows with the highest word overlap (Jaccard over lower-case word sets; ties by row id, exactly CTT's order), each copied target re-bound to this sentence's slots and checked; unanimous = all three give the identical checked form | **mechanism-free baseline: no learning at all, same rule** |
| **A4-s1, A4-s2, A4-s3 (as run)** | reader first + each copy alone under the CTT-1 rule (any checked reading goes; writes read back; topics used directly) | **the c45-style control: the translator without the rule** |
| C2E | reader first + three never-trained random initialisations under ACCEPT-2: C2-s1 (c45, pinned) + C2-s2, C2-s3 made on the host from recorded seeds (`seed_of` formula of `ctt_train/train.py`, names `C2-s2`, `C2-s3`), no training step | control: lock + checker + vote with no learning (free; mark M-K3) |
| A5, C1 (as run) | twin; shuffled-pairs control, single model, CTT-1 rule | reported only (continuity with CTT-1) |

Not run: **C1E** (needs two more shuffled trainings; this packet is rule-only, no retraining — design deviation D-2R-1).

## 5. Exams

All three parts are drawn blind by the custodian after the package is sealed, with the seed of section 11. The
builder never sees an exam item, a key or a seed. Answer keys never go to the GPU host (only inputs go); the reader
on the laptop applies them.

### 5.1 Part R — real public sentences, stock-dense (other people wrote them, for other reasons)

- Frame: X-REAL's pinned Part S frame `FRAME_S.jsonl` (`98c2fb8f…`, 15,672 items, practice partition already out).
- Excluded by id and by normalised text, each with its skip reason recorded: `XREAL_USED` (X-REAL's 128,
  `INPUTS_XREAL.json` `37312a31…`), `CTT_USED` (CTT's primary 128, `E_MACHINE_S_CTT.json` `f94250df…`), `RTR_USED`
  (RTR-1's 128, `INPUTS_RTR.json` `c0037bf3…`), `BUILDER_SEEN` (the 3 ids of D-RTR-2), `PERSONAL_DATA` (X-REAL's
  rule), `FORBIDDEN_TEXT` (X-REAL's forbidden list + every string of 16+ characters in this package's tests and
  reader files), `DUPLICATE_TEXT`.
- **Census R0 (custodian, before the draw, no model):** on every eligible item, X-REAL's key A and key B (K-S rule);
  items where they disagree are UNDETERMINED and leave the frame. Then reader v1.1 with the CTT switching rule
  (`would_ask`: status CLARIFY, or NOT_MINE on a sentence the reader itself claims). Counts only are published.
- **Strata and sizes** (rank = sha256("CTT2R:R:" + seed + ":" + id), lowest first, per stratum):

| Stratum | Key | Reader v1.1 | Items |
|---|---|---|---|
| **R1** | FACTS | hands over (would ask) | **48** — the stock-weighted stratum: the only place a reader-first gain can happen |
| R2 | EMPTY | hands over | 48 — "fact from nothing" (kitchen words, no stock of ours) |
| R3 | ASK | any | 16 — a reading here is wrong |
| R4 | FACTS | reads | 16 — reader regression check; no model is called |

  A stratum with too few items takes all it has; the shortfall is recorded. **If R1 has fewer than 24 items, Part R
  is `NOT_EXERCISED`: the custodian STOPS before drawing and tells the coordinator** (widening the frame is a new
  design step; never a silent pad).
- Keys and scoring: X-REAL's K-S table unchanged (FACTS: right only if the written facts equal the key; EMPTY: right
  with 0 writes; ASK: right if asked and nothing written; UNDETERMINED: not scored). Disclosed limit: choosing R1/R2
  by the reader's own behaviour makes A0's Part-R count a design constant (A0 asks on all of R1 and R2).

### 5.2 Part K — kitchen turns from a NEW LLM-written pool (label `LLM_WRITTEN`)

- **The c45 LLM pool is spent** (ACCEPT-2 was chosen after looking at its per-turn classes). It is used for nothing
  here except as an exclusion list: a new pool sentence equal to, or sharing an 8-word run with, any c45 pool sentence
  is not eligible.
- **Writers:** Gemini and DeepSeek through the existing keys (the c45 writer-wrangler recipe,
  `cas_token_transformer\llm_written\README.md`), new calls, fresh plan seeds. The custodian session runs the calls
  and the pool is written straight into a **custodian-only folder** (the c45 pool was not; that is fixed here). The
  builder writes only the program and the brief.
- **Brief:** c45's brief (`BRIEF_VERBATIM.txt`) with two changes: (1) the example phrasing "flour i got 3 cups of"
  is removed (it echoed our noise generator); (2) the trap families below are added. Writers state the facts they
  meant ("intended facts"); they never write HELM's answer (foreign questions OK, foreign answers never).
- **Singles (128):** core 96 — stock 30, absent 12, stock_absent 12, topic 12, stock_topic 12, witness 6,
  ask_unknown_ingredient 5, ask_no_number 4, ask_approximate 3 — keyed by HELM's fixed answer rule from the intended
  facts (`custody/draw_contents.py` gold shapes, as c45); **trap stratum 32** with keys frozen NOW, per family,
  before any writing:

| Trap family (fundamental) | Items | What the person says | Frozen key |
|---|---|---|---|
| T17 someone else's stock (F17) | 6 | an amount that SOMEONE ELSE has ("my sister has 6 eggs") | **EMPTY** (right = nothing written) |
| T16 past or future stock (F16) | 6 | an amount they HAD or WILL have, nothing about now | **ASK** (right = ask, nothing written, nothing answered) |
| T12 reported or unsure (F12) | 5 | an amount only as someone else told them, or as an unsure guess | **ASK** |
| T14 negation scope (F14) | 5 | they are NOT out of an ingredient / never ran out, no amount | **EMPTY** |
| T22 condition (F22) | 4 | "if we had 3 eggs could we make meringues" (nothing about what they have) | **ASK** |
| T15 numbers that are not stock (F15) | 6 | a price, oven heat, a time, a people count, or what a recipe calls for | **EMPTY** |

  Any trap reading that writes is a CWFW (for a model) or READER_WRONG (for the reader). On ASK keys any model
  reading (even a topic) is a CWFW.
- **Dialogues (16):** answer_question 6, add_more 5, out_too 5 (c45's patterns, 3–4 turns each), scored with gold
  history (each turn gets the dialogue records of the earlier turns' keys; no cascade). `add_more` keys use the
  computed total (earlier stock + added), never the writer's total.
- Split per writer: Gemini 48 core + 16 traps + 9 dialogues (answer_question 3, add_more 3, out_too 3); DeepSeek 48
  core + 16 traps + 7 dialogues (3 / 2 / 2). The pool is written about 1.5 times larger; the custodian draws blind
  by hash per (writer, family) cell (rank = sha256("CTT2R:K:" + seed + ":" + unit id)).
- Ineligible units (recorded, never hand-edited): failed the mechanical cleaner; overlap with the c45 pool; a
  near-duplicate (shared 8-word run) of a unit already taken; a key the fixed rule cannot settle (UNDETERMINED).
- Tags (reported only): the c45 deterministic fundamentals tagger (byte copy, pinned) tags each drawn row; the reading
  prints RIGHT / ASKED / CWFW per trap family for A0, A2E, A4E.
- **K-H (human-typed)** is not run in this packet: `HUMAN_EXAM_ABSENT`, status `NOT_RUN`; it fails nothing.

### 5.3 Leakage (host, automatic, counts only)

Every Part R and Part K input is compared with the 227,497 training inputs of c45 (`train.jsonl`, pinned) by CTT's
own rule (`ctt_build/leakage.py`: lower-case whitespace-normalised equality, or any shared 8-word sequence). A turn
that matches is excluded from scoring and counted (training is already done, so the exam turn goes, never a row).

### 5.4 Reachability (instrument row I-REACH; "INCONCLUSIVE instead of NO_GAIN when no gain was possible")

For each scored part, headroom H = scored turns whose key is a record to be read (K-S FACTS; gold ANSWER or WITNESS)
on which A0 asked. If H is below twice the part's A4E − A0 mark, a gain of that size was impossible, so the word
cannot be NO_GAIN: the reading is `INSTRUMENT_ERROR` / `INCONCLUSIVE`. Frozen floors: **Part R H ≥ 12** (mark 6),
**Part K singles H ≥ 16** (mark 8), **Part K dialogue turns H ≥ 8** (mark 4). (c45's primary exam would have failed
this row: H = 1 against a mark of 8.)

## 6. How each turn is scored

- K-S keyed turns (Part R, Part K traps): X-REAL's K-S table through CTT's frozen `classify_key`.
- Gold-record turns (Part K core singles and dialogues): CTT's frozen `classify` (RIGHT if the record HELM would act
  on equals the key after canonical amounts; ASKED if asked; CWFW if a model/retrieval reading is not the key;
  READER_WRONG if the reader's own reading is not the key).
- A vote-arm turn is RIGHT only through an OFFERED reading the scripted user confirms; its CWFW is counted at the
  offer.
- Excluded (leakage) and UNDETERMINED-key turns are NOT_SCORED and counted.

## 7. Hard gates (any one false = `FAILURE`; instrument rows = `INSTRUMENT_ERROR`)

| Gate | Rule |
|---|---|
| H-CWFW | **singles (Part R; Part K singles):** A4E CWFW ≤ 2 AND ≤ A2E's, on EACH part; **dialogue (Part K turns):** A4E CWFW ≤ 1 per 64 turns (cap = max(1, turns // 64)) |
| H-SAVED | 0 wrong model or retrieval readings saved, every arm, every part |
| H-USED | 0 model readings USED without a yes: every vote-passed reading of A4E / A2E / C2E carries a read-back (topic-only included); in the NO-HARM ON run the ACCEPT-2 hook applied 0 readings |
| H-READBACK | every read-back has 0 CAS tokens (`helm_voice.cas_tokens`) and quotes every amount and name (and the product word of a topic) |
| H-WRITE | every translator process (each proposer, the NO-HARM ON process, the smoke) is audit-clean under CTT's A-CTT-2 rule (audit log, null device, own temp folder, torch/CUDA caches allowed; anything under a forbidden root, any socket, any process start = violation) |
| H-NOHARM | the six spent wave exams with the ACCEPT-2 hook ON (three copies voting) give the same digests as c45's OFF record, 6 of 6; OFF re-run here equals c45's OFF, 6 of 6 |
| H-REMOVE | OFF with `helm_cas_translator/` deleted from a copy of the CTT package = OFF, 6 of 6 (re-run) |
| H-SEP | CTT's static separation test on `helm_cas_translator/` passes; this packet's translator-process script imports only stdlib, torch and `helm_cas_translator` |
| H-RT | (a) 0 vote-passed readings fail the round trip; (b) on each part, of each A4 copy's proposals, at least 0.90 are well formed |
| H-LEN | 0 inputs truncated, every part, every proposer |
| H-VOTE (instrument) | each offered A4E / A2E / C2E reading has three proposer records, all READ, byte-identical checked forms; and every turn whose three records are READ and identical is a vote pass (both directions) |
| H-CUSTODY (instrument) | the sealed exam files equal their seal records before and after; the seed recomputed from the approval record equals the seal record's; leakage counts recorded |
| H-NOFOREIGN (instrument) | every weight file equals its c45 pin; the two new C2 inits are made from recorded seeds and their exact parameter count is asserted; no pretrained file in the package or staged |
| I-REACH (instrument) | section 5.4 |

## 8. Marks (A4E is one arm: the three-copy vote; per-copy as-run counts are printed beside it)

| Mark | Rule |
|---|---|
| M-K1 | Part K singles: A4E − A0 ≥ 8 |
| M-K2 | Part K singles: A4E − A2E ≥ 4 |
| M-K3 | Part K singles: A4E − C2E ≥ 8 (the C1E half is NOT_RUN, D-2R-1) |
| M-K4 | Part K dialogue turns: A4E ≥ A0 + 4 |
| M-R1 | Part R: A4E − A0 ≥ 6 |
| M-R2 | Part R: A4E − A2E ≥ 3 |

## 9. Status words and the frozen reading order (CTT-1's four words; no new word)

Verdicts `PASS` / `FAILURE` / `INSTRUMENT_ERROR`; words **`EARS_EARNED_KEEP` / `EARS_NO_GAIN` / `EARS_HARMED` /
`INCONCLUSIVE`**. The frozen reader (`ctt2r/merge_2r.py`, laptop) stops at the first rule that fires:

1. Instrument problem (a pinned file differs, the run is incomplete, a result file is missing, H-VOTE, H-CUSTODY,
   H-NOFOREIGN, I-REACH fails on any part, Part R `NOT_EXERCISED`) → `INSTRUMENT_ERROR`, `INCONCLUSIVE`.
2. Any harm gate fails on any part (H-CWFW, H-SAVED, H-USED, H-NOHARM, H-REMOVE, H-WRITE, H-READBACK, H-SEP) →
   `FAILURE`, `EARS_HARMED`.
3. H-RT or H-LEN fails → `FAILURE`, `EARS_NO_GAIN`.
4. All gates pass; M-K1–M-K4 and M-R1–M-R2 all hold → `PASS`, `EARS_EARNED_KEEP`.
5. All gates pass; a mark missed → `PASS`, `EARS_NO_GAIN`.

A word is licensed only with verdict `PASS`. The runner's exit code is never the verdict. K-H: `NOT_RUN`.
Spec-sheet words: `ENGINEERED-NOT-VALIDATED` stays unless word 4; `VACUOUS` for any part marked `NOT_EXERCISED`.

## 10. Honest predictions (written before any data exists)

- **After-the-fact numbers (they license NOTHING):** applied by hand to c45's per-turn records, unanimity would have
  given LLM_WRITTEN singles **81 right / 0 confident wrong** (A0 72) and dialogue turns **38 right / 1 confident
  wrong** (A0 34; the one is the K2 turn all four models got wrong identically). ACCEPT-2 was chosen after seeing
  those records, on 5 distinct wrong turns. That is why it is tested here on fresh turns, and why those numbers
  cannot confirm it.
- Part K singles: A4E − A0 between +5 and +12; A4E CWFW 0–2 (the trap stratum is the main risk: kitchen names and
  numbers that are not our stock).
- Part K dialogues: A4E − A0 between +2 and +6; CWFW 0–2 (a K2-type correlated error can repeat; cap 1).
- Part R: A4E − A0 between 0 and +4 (c45 had 0 right model readings on public sentences; 0.97% of training rows were
  public English). M-R1 (+6) is the most likely mark to miss.
- A2E (top-3 copy-closest, unanimous): close to A0 on both parts (three neighbours rarely give one identical record).
- C2E: equal to A0 (untrained copies essentially never agree).
- A4 as run (no rule): more right AND more confident wrong than A4E, as in c45.
- NO-HARM: identical (the ACCEPT-2 hook applies nothing without a yes, and the brain's wave loop has no yes).
- Word: `EARS_NO_GAIN` about 0.45 (M-R1 missed); `EARS_HARMED` about 0.2 (trap or K2-type error, or A4E CWFW above
  A2E's); `INCONCLUSIVE` about 0.2 (R1 census below 24, or a reachability floor); `EARS_EARNED_KEEP` about 0.15.

## 11. Custody

### 11.1 Seed source
`H = sha256( UTF-8( "CTT RULE TEST at 1.50 USD" + ":" + <full lower-case sha256 of the final sealed zip> ) )`, no
trailing newline. No seed can be known before the package bytes are final. The custodian computes it; the frozen
reader recomputes it (H-CUSTODY).

### 11.2 Bands (each 1,000,000 wide, above every band used or reserved so far)
Highest so far: RB-W1T RW2 1,952,000,001–1,953,000,000 (spent, c47) and wave 6's reservations E64 1,954 M, F64
1,956 M, REAL 1,958 M, CONV 1,960 M, **PAIRW 1,962,000,001–1,963,000,000** (`r1_wave6/HELM_R1_W6_20261019/r1w6/
common_w6.py`, checked 2026-10-19). So the used table is **1–1,963,000,000 as one whole range** (wave 6's own
convention), gap 1,000,000:

| Band | Range | k |
|---|---|---|
| R (Part R) | 1,964,000,001–1,965,000,000 | int(H[0:16], 16) |
| KS (Part K singles) | 1,966,000,001–1,967,000,000 | int(H[16:32], 16) |
| KD (Part K dialogues) | 1,968,000,001–1,969,000,000 | int(H[32:48], 16) |

First slot = k mod 1,000,000; seed = band low + slot; a hit steps s ← (s + 1) mod 1,000,000 inside the band; no free
slot = STOP (never another band). Every step is written to `SEED_DERIVATION_CTT2R.json`. If the custodian's ledger
shows a band above 1,963 M used after 2026-10-19, the coordinator moves these bands up BEFORE the seed exists.

### 11.3 Hold-out
Exam inputs go to the host by carrier; keys (`KEYS_R_CTT2R.json`, `KEYS_K_CTT2R.json`) and the pool stay in the
custodian folder on the laptop. The operator copies, hashes and compares; never opens, prints or summarises an exam
file. The builder never handles a carrier.

## 12. Compute, limits, cost

One AWS GPU host (`g5.xlarge`, us-west-2; fallback `g4dn.xlarge`), GPU_REQUIRED (the translator process refuses
without CUDA; nothing neural on the laptop). No training. Stages: refusals; reader overlay; preflight (unit tests,
GPU smoke of one translator process with audit); two C2 initialisations (no training step); leakage; decisions on
Parts R and K (11 proposer processes: A4 ×3, A5, C1, C2 ×3, plus retrieval in-process); NO-HARM OFF, OFF-removed, ON
with ACCEPT-2. Expected host time 20–35 minutes; **expected 0.35–0.60 USD**, cautious 0.80; **cap 1.50 USD**; job
wall 90 minutes; instance life 2 hours (self-terminate). One attempt + one plumbing retry (only if no part was scored).

## 13. What a pass would license, and what it would not

Licensed (numbers filled by the frozen reader; ceiling `NAMED_CORPORA_ONLY` for Part R + `LLM_WRITTEN` for Part K):
"On HELM's eight-ingredient, four-recipe kitchen world, with reader v1.1 first, the from-scratch CAS-token
translator (c45 weights, unchanged) whose readings are offered only when three independently trained copies agree,
and only acted on after the user says yes, raised the turns read right from [A0] to [A4E] of 128 LLM-written kitchen
turns and from [A0] to [A4E] on [n] real public sentences (Tatoeba / Taskmaster) of which [n1] state stock the reader
could not read; it beat a no-learning copy-closest rival held to the same rule by [M-K2] and [M-R2]; it offered [n]
confident wrong readings (cap 2 per 128 singles, 1 per 64 dialogue turns), used none without a yes, saved none, and
changed none of the brain's exam results."

NOT licensed: anything about people typing to HELM (only K-H can carry that); English outside the 8 ingredients and
4 recipes; frames or Noetics; the translator without the vote; live use on the laptop (torch does not fit; neural
work never runs on the local CPU); statistical superiority (one draw); any retrained model.

## 14. Deviations from the design (dated; written before code)

- **D-2R-1 (C1E not run).** The design's C1E control needs two more shuffled trainings; the coordinator scoped
  CTT-2R as rule-only, no retraining, with the arms of section 4. M-K3 therefore uses C2E only; C1 is reported as
  run (single model, CTT-1 rule).
- **D-2R-2 (Part R size).** The coordinator's brief names "48 real stock-dense sentences the reader gives up on";
  the design's Part R table has 128 (R1 48 + R2 48 + R3 16 + R4 16). Both are kept: R1 is the 48-item stock-weighted
  stratum that carries the gain; R2–R4 carry the harm and regression checks.
- **D-2R-3 (no keys on the host).** CTT-1 shipped keyed exams to the host. Here the host gets inputs only and
  writes per-turn decisions (proposals, checks, votes); the laptop reader applies the keys, the scripted user and
  the session cap. Same rules, stricter custody.
- **D-2R-4 (NO-HARM reference).** ON runs once, with the three-copy ACCEPT-2 hook, against c45's pinned OFF digests;
  OFF and OFF-removed are re-run. NO-HARM uses the wave packages' own reader (v1.0), because the brain's wave exams
  and their recorded results are pinned to it; the scored ears parts use v1.1.
- **D-2R-5 (margin by teacher forcing).** Tokens come from CTT's frozen greedy decoder unchanged. The margin is
  computed afterwards by feeding the chosen tokens back one row at a time; a flag records whether every chosen
  token was the argmax there. Logged only.
- **D-2R-6 (bands).** The design's bands (1,930–1,937 M) lie below bands already used or reserved since (RTR 1,940 M,
  RB-W1T 1,950–1,953 M, wave 6 up to 1,963 M); section 11.2 moves them above 1,963 M, as the coordinator instructed
  ("above every used band").
