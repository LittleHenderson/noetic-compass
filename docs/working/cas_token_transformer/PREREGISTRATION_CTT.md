# CTT-1 PREREGISTRATION — the CAS-token transformer, "ears first"

Written 2026-10-19 (Pacific) by the builder session (Claude), BEFORE any code of this package existed.
A byte copy is kept as `PREREGISTRATION_CTT.precode.md` with its sha256 in `PREREGISTRATION_CTT.precode.sha256`.
Later edits are allowed only in section 16 (deviations found while building), each dated, and never to a threshold,
an arm, a gate, a status word or a prediction.

Design implemented: `Documents\Codex\2026-10-19\cas_token_transformer_design_v1\` (ARCHITECTURE.md, DATA.md,
TEST_PLAN.md, OPEN_QUESTIONS.md). Owner picks accepted as proposed (order "SCORE L4", 2026-10-19): ears first;
9.6 M with a 2.5 M twin; outside English input-only ("strict, templates are ours"); read back before writing;
kitchen turns count; owner + two people write the human test sentences; the old Scribe model is scored separately.

Claude is not the research governor. A failed hard gate is a FAILURE, never "PASS with caveats". The status word is
read by a frozen program (`ctt_score/merge_ctt.py`) from raw result files, never from prose.

---

## 0. Status of this packet

- **NOT LAUNCHED.** Nothing trained, nothing scored, no claim. The translator's claim status is
  `ENGINEERED-NOT-VALIDATED` (spec-sheet legend) and stays so unless the frozen reader returns `PASS`.
- **Approval.** The owner's verbatim pre-approval (2026-10-19, recorded in
  `Documents\Codex\2026-10-18\OWNER_APPROVALS_20261018.md`):
  `I PRE-APPROVE BOTH OF THE FOLLOWING:   Two sign lines are coming: X-REAL at 1 USD, and the transformer training at 8 USD.`
  That line names no package hash. So the approval record for this run is `APPROVAL_RECORD_CTT.md`: it quotes that
  line and names the final sealed zip sha256. Cap 8.00 USD; one attempt + one plumbing retry. Any change of scope,
  package or cap needs a new owner word.
- **What still blocks the paid run:** (1) the custodian-sealed human exam E-HUMAN-W does not exist yet; it needs the
  owner and two other people to write the sentences (section 5.1); (2) the custodian's seal record must be staged.
  The run never starts on a missing or unsealed exam.

## 1. The question, in plain words

Does a small translator model, trained from scratch, sitting BEHIND HELM's hand-written English reader and its
checks, let HELM correctly understand more everyday human English about its kitchen world than the reader alone,
without adding wrong readings and without changing one result of the recipe brain?

## 2. What is built (the separate component)

- **The translator** lives in its own folder `helm_cas_translator/`, runs in its own process, has its own weights
  file and manifest. It reads English (plus a short list of dialogue records) and PROPOSES a CAS record. It never
  decides anything.
- **Hard boundary (owner ruling 2026-10-19).** The translator module imports only the Python standard library and
  torch. It imports no HELM module: not the brain, the cube store, the receipts, the memory, the loop, the reader or
  the voice. It opens no file for writing except its own audit log, and opens no socket. This is checked two ways:
  a static test that reads its source (gate H-SEP) and an audit hook inside the translator process during every
  scored run (gate H-WRITE).
- **The only interface** is a CAS record that crosses the deterministic checker. The checker lives OUTSIDE the
  translator (`ctt_ears/`) and uses HELM's own code unchanged: the reader's labeled name table
  (`helm_english_in.EVERYDAY_INGREDIENTS` / `EVERYDAY_PRODUCTS`), its number rule (`canonical_amount`) and its round
  trip (`helm_english_in._round_trip`, which is `cce.parse(cce.render(C)) == C` after `cce.normalize`).
- **Reader first, model second.** The model is called only when the reader would ask: reader status `CLARIFY`, or
  `NOT_MINE` on a sentence the reader itself claims (it holds a kitchen word but nothing was read). The reader's own
  readings are never overridden.
- **Numbers and names are copied, never generated.** The model's output vocabulary holds no digits for amounts and
  no ingredient or product names. It emits slot pointers (`⟦q1⟧..⟦q16⟧` amounts, `⟦n1⟧..⟦n32⟧` words,
  `⟦c1⟧..⟦c8⟧` dialogue records). A deterministic filler copies the user's own span. A pointer to a span that does
  not exist is a refusal (one question, nothing written).
- **Read back before writing (owner pick Q6).** A model reading that would be WRITTEN (an amount in stock, "we're
  out of", a witnessed batch) is read back to the user in plain words first and written only on a yes. A model
  reading that writes nothing (which product the user asks about) goes ahead.
- **Two sizes.** Main model about 9.6 million parameters; twin about 2.5 million parameters. Exact counts are
  computed by a formula, printed, and asserted against torch's own count on the GPU host before training.
  Every block's job is in `PARAMETER_JOBS_CTT.md` (Capacity Rules v0.1: each parameter has a job).
- **Grammar-locked output.** Decoding can only emit sequences of the target grammar (section 3.3). The checker still
  checks everything afterwards.
- **Not built in this packet:** direction B (the mouth). Owner pick Q1: ears first; B is parked. B's tokens are
  reserved in the vocabulary only.

## 3. Training data (all built on the GPU host from frozen code and frozen seeds)

"Foreign questions OK. Foreign answers never." Other people's English may enter only as INPUT. Every TARGET is made
by our own code: our generator, our reader, our SDG's CAS side.

| ID | Source | Gives | Target from | Designed size |
|---|---|---|---|---|
| D1 | A-world generator (`ctt_build/aworld_gen.py`): content drawn first, everyday English written from it by our templates over a WIDER name pool than the brain's 8 ingredients | input + target | the drawn content (exact by construction) | 160,000 single turns + 40,000 turns with dialogue records = 200,000 |
| D2 | noise layer on D1 (contractions, fillers, typos at a fixed rate, allowed word-order swaps, distractor clauses; hedged and number-dropped negatives) | input only | D1's target unchanged, or the reader's question code for the negatives | 35% of D1 rows carry noise (inside the 200,000) |
| D4 | SDG English descriptions, 3 files, 5,268 rows (sha256 below); English written by an LLM drafter, so INPUT only | input | the row's own `source_cas` (our SDG's CAS side) | each usable row once clean + 5 noised copies |
| D6 | HELM's own live traces of 2026-10-18 (owner's own words) | input | the record HELM's reader produced (CONTENT / CLARIFY / NOT_MINE) | all usable rows (under 1,000) |
| D7 | X-REAL practice partitions ONLY (Tatoeba ids ending in 7; Taskmaster-1 dialogs listed in its dev split, USER turns only), both pinned by X-REAL | input only | the reader's own CLARIFY code or NOT_MINE. Rows the reader READS are dropped (no independent gold; the reader is known to misread some real lines) | capped at 20,000 |

- D3 (fresh SDG generator runs) is not used: D4 already covers every grammar category of the SDG, including
  `meta_logic_relation` (710 rows), `fractal_sequence` (466) and `diagram_export` (417). Section 16 records this.
- D5 (voice phrasebook) is not used: it feeds direction B only, which is parked.
- **Pinned input files:** `wave3_step2_5_english_descriptions_20260508T203848Z.jsonl`
  sha256 `b825b67a3029657f40d128d382448b5f0b55580fc7451bfce8b4a35687a46817` (5,263 rows);
  `..._20260509T002355Z.jsonl` `d814397c4957ce89e6721cfcb2ec3852773976ad7176e25247d98d7d7ef6893e` (4 rows);
  `..._20260509T002541Z.jsonl` `23ac1e36021bec455309bf7ff02d759a7766838eda03faba01cc3b069bec1028` (1 row).
- **Validation (never trained on):** the 99 DEV rows `real_dev_unparseables_99.jsonl`
  (sha256 `17cd198321d242bd74ff789a4b7f8032d499a7ff8534e5b07545b6221930fde0`) for notation; 5% of A-world drawn with a
  separate seed text. Validation loss is logged only. It selects nothing (no early stopping, no checkpoint choice).
- **Mix rule (ratified 2026-05-14):** public-input rows (D7) stay at or below 30% of direction A rows.
- **Training seeds are fixed now,** before any exam seed exists: the seed of every training draw is
  `int(sha256("CTT-TRAIN-<part>-20261019"), 16) mod 2**63`, with `<part>` in {D1, D2, D4, D7, VAL, SPLIT, A4-s1,
  A4-s2, A4-s3, A5-s1, C1-s1, C1-perm, C2-s1}. These numbers sit in no numeric seed band used by any HELM-R1 wave,
  X-REAL or this exam.
- **Exact counts and sha256 of every built file** are written by the host into `DATA_MANIFEST_CTT.json` before
  training. The sizes above are designed targets; a shortfall is recorded, never padded.
- **Vocabulary.** CAS side: every token kind of both compilers (site copy, 6,415 lines, sha256
  `464fd4adfae90a35ba54aa794829da1fe713b9b9cccd68b630ecccfdfbca2f56`; repo copy, 5,813 lines), including the seven
  categories (state literals, drives, registers incl. `|⟨…⟩`, operators, recipes, META-LOGIC, COGNITIVE FRACTALS and
  nesting tags), CAS-Ohm (input side), HELM's record words and the slot pointers. A test fails if any compiler token
  kind or constructor is missing. English side: exactly 8,000 word-pieces learned from scratch on the allowed INPUT
  text only. No borrowed tokenizer, no pretrained weights.

### 3.3 Target grammar (A-world), frozen

```
A-world target := ANSWER item+ | WITNESS Ω_ N MADE Q stock+ RAN_OUT Ω_ N | CLARIFY code arg* | NOT_MINE
item  := STOCK Q · Ω_ R | ABSENT Ω_ R | TOPIC Ω_ R | ADD Q · Ω_ C
stock := STOCK Q · Ω_ N          R := N | C        Q := ⟦q1⟧..⟦q16⟧   N := ⟦n1⟧..⟦n32⟧   C := ⟦c1⟧..⟦c8⟧
code  := one of the reader's own question codes (helm_english_in), e.g. NO_NUMBER, UNKNOWN_INGREDIENT, APPROXIMATE
```
`ADD q · Ω_ c` means "the amount in dialogue record c, plus q". The checker does the sum exactly (fractions, no
rounding) and reads the new total back before anything is written. A-notation targets are CAS expressions in the
compiler's own token language (identifiers and numbers as pointers into the English).

## 4. Model and training (frozen in `FROZEN_CTT.json`)

| | A4 main | A5 twin |
|---|---|---|
| Shape | encoder-decoder, width 256, 4 + 4 layers, 4 heads, feed-forward 1,024 | width 128, 3 + 3 layers, 4 heads, feed-forward 512 |
| Embedding | one table, tied input/output, shared by both sides | same |
| Positions | fixed sinusoids (0 parameters) | same |
| Copy (pointer) head | bilinear copy attention + gate | same |
| Seeds | 3 (A4-s1, A4-s2, A4-s3) | 1 (A5-s1) |

Schedule for every trained arm (no tuning, no rerun to coax a pass): AdamW, learning rate 5e-4, weight decay 0.01,
1,000 warm-up steps then cosine decay to 0, batch 256 pairs, 12 epochs, dropout 0.1, gradient clip 1.0, training
rows longer than 256 input tokens or 128 output tokens dropped and counted (never cut). Exam inputs are never cut
(gate H-LEN). The FINAL checkpoint of each arm is the
one scored. Mixed precision is off (fp32) so a T4 fallback gives the same arithmetic path.

`GPU_REQUIRED`: the trainer refuses to start without CUDA. There is no CPU fallback.

## 5. Exams

### 5.1 E-HUMAN-W — human English about HELM's kitchen world (the claim rests here)

- **Content first.** The custodian's program (`custody/draw_contents.py`, sealed in this package) draws CAS records
  from the exam seed and prints each one in plain words for a writer ("You have 12 cups of flour and no water. Tell
  HELM."). The writer types what they would say. The drawn record is the gold, exact by construction.
- **Size:** 128 single turns + 16 short dialogues of 3 to 5 turns (64 dialogue turns in total).
  Singles: 40 stock statements (1 to 3 ingredients, with and without units), 16 absences, 16 stock + absence,
  16 product questions, 16 stock + product question, 8 witnessed batches, 16 must-ask turns (6 unknown ingredient,
  5 no number said, 5 approximate amount). Dialogues: answers to HELM's own question, "it"/"that" for the product
  in talk, "add N more" to an amount said earlier, "out of that too".
- **Writers (owner pick Q4, "me plus two"):** the owner writes the first 64 singles; person B writes 32 singles and
  8 dialogues; person C writes 32 singles and 8 dialogues. Agents may not write it. **Slot left open:** the writers'
  names are written into the seal record by the custodian; this packet holds only the empty sheets' format.
- **Builder blind:** the builder never sees the sheets, the sentences or the drawn records. The exam is staged to the
  GPU host by the custodian only.

### 5.2 Other exams

| Exam | What | Role |
|---|---|---|
| E-NOTATION | the sealed 98 (`real_heldout_unparseables_98.jsonl`, sha256 `e269a448cf1d087aa6b98436dadfbfdefa60216346f0f886659f0f9d7dd61cfe`), LLM-written SDG English | reported only, labeled "synthetic-source English", scored once, counts only; no word rests on it |
| E-X-REAL-S | X-REAL Part S items | `NOT_EXERCISED` unless X-REAL has run AND the owner allows reuse in writing; slot left open |
| NO-HARM | the spent wave exams: X3 English-64 + Faces-64 (wave 3b), X4 English-64 + Faces-64 (wave 4), X5 English-64 + Faces-64 (wave 5), run through the wave-5 package's loop (FULL arm) with the translator OFF and ON | gate H-NOHARM |

### 5.3 Scribe L4 baseline (A3) — slot FILLED from run c41

The old small English model (`scribe_l4_weights.pt`, commit `84812689`) was scored once on the sealed 98 by another
operator (job c41, spec sheet §7.80; record `Documents\Codex\2026-10-19\scribe_l4_score\run_c41\RUN_RESULT_SCRIBE_L4_C41.md`,
file sha256 `eebbe92d723c8a5c03fa4e747ba39ad718edfd58e2c86b0f325f41c43e8153ac`; receipt
`SCRIBE_L4_SEALED_98_RECEIPT.json` sha256 `f283d38304846ebd62482ae3fbf92739635aa6c24181b2261832127b6cf9d38c`):
**exact match 0 of 98; refused 77 of 98; answered 21 of 98; all 21 answers passed the real round-trip check and all
21 were wrong; 97 of 98 inputs were cut at its 32-token input limit.** No CTT word depends on it.

**Lessons written into this packet's gates (coordinator, 2026-10-19, before any code):**
(a) a round trip proves a record is well formed, not that it is right: the answer key is compared to the PROPOSED
record itself (section 7), never only to "the round trip passed";
(b) "confident, well-formed, wrong" is a counted, named failure class `CONFIDENT_WELL_FORMED_WRONG` with its own
thresholds (gate H-CWFW, section 8): at most 2 proposed on the 128 singles, and 0 SAVED, because HELM reads back
before writing;
(c) the input length must not cut the exam: exam inputs are never truncated, and gate H-LEN asserts 0 truncated exam
inputs on every exam.

## 6. Arms

| Arm | What | Role |
|---|---|---|
| A0 READER | `helm_english_in.read` alone (E-HUMAN-W); lexicon-v2 reader alone (E-NOTATION) | mechanism-free baseline 1: today's template reader |
| A1 ALWAYS-ASK | asks one question every turn | mechanism-free baseline 2 |
| A2 RETRIEVAL | reader first; on a refusal, copy the target of the training row with the highest word overlap (Jaccard over word sets), re-bind its pointers to this sentence's slots, then the SAME checker | mechanism-free baseline 3: no learning |
| A3 SCRIBE | filled from run c41 (5.3); E-NOTATION only | historical small-transformer arm |
| **A4 READER + TRANSLATOR** | reader first; on a refusal, the 9.6 M model proposes; the checker decides; 3 seeds | **the arm under test** |
| A5 READER + TWIN | as A4 with the 2.5 M twin, 1 seed | size check (Capacity Rules) |
| A6 TRANSLATOR ONLY | the 9.6 M model (seed 1) on every turn, no reader first | reported only |
| C1 SHUFFLED | 9.6 M trained on pairs whose targets were shuffled across rows (same schedule, seed 1) | control: no English-to-CAS link learned |
| C2 FROZEN | 9.6 M at its random initial parameters (seed 1), never trained, same grammar lock and checker | control: what lock + checker give with no learning |

## 7. How each turn is scored (E-HUMAN-W)

- **RIGHT:** the gold is a record and the record HELM would act on equals it after `cce.normalize` (for a write:
  after the read-back, where the scripted user answers yes only if the reading equals the gold); OR the gold is a
  must-ask and HELM asked.
- **ASKED:** the gold is a record and HELM asked (or did not read). Nothing written. Never WRONG.
- **WRONG_PROPOSED = `CONFIDENT_WELL_FORMED_WRONG` (the danger count):** a reading passed every deterministic check
  (grammar, pointers, names, round trip) and the PROPOSED record is not the gold (including a reading on a must-ask
  turn). The answer key is compared to the proposed record itself; passing the round trip never makes a turn RIGHT.
  Counted BEFORE the read-back.
- **WRONG_WRITTEN = `CONFIDENT_WELL_FORMED_WRONG` that was SAVED:** a wrong record reached the store. Must be 0.
- Dialogue turns are scored with the dialogue records taken from the GOLD of earlier turns (so one miss does not
  cascade). A pronoun, an answer to HELM's question or "add N more" is RIGHT only if it points at the gold record.
- **E-NOTATION:** MATCH / MISMATCH / UNPARSEABLE by `sdg_bridge_v2` tuple comparison (the lexicon-v2 rule).
  **GUESS:** the lexicon-v2 reader's refusal reasons named a missing Domain or state and the model supplied one; a
  GUESS is never counted as MATCH in the claim-bearing count; the count with GUESS-as-MATCH is printed beside it,
  labeled.

## 8. Hard gates (any one failing = verdict FAILURE)

| Gate | Rule |
|---|---|
| H-RT | (a) zero model readings used that fail the reader's round trip (re-checked by the merge reader from each turn's receipt); (b) on E-HUMAN-W, of A4's proposals (turns where the model answered with a reading, not a question), at least 0.90 are well formed (grammar, pointers that exist, round trip), on EACH of the 3 seeds |
| H-READBACK | every sentence the ears produce (read-backs and questions) has zero CAS tokens by `helm_voice.cas_tokens` and quotes every amount and name of its reading verbatim; on NO-HARM, every reply's `plain` flag is unchanged ON vs OFF |
| H-WRITE | zero writes from a model reading without a yes; zero writes outside the turn path; the translator process (audit hook) opened no file for writing except its own audit log and made no socket call |
| H-CWFW (was H-WRONG) | the named class `CONFIDENT_WELL_FORMED_WRONG`: A4's count on the 128 singles is at most 2 AND at most A2's, on each seed; the SAVED count (WRONG_WRITTEN) is 0 in every arm and every exam. Scribe c41 had 21 of 98 in this class; this gate exists because of it |
| H-LEN | 0 exam inputs truncated, on every exam and every arm (Scribe c41 cut 97 of 98). Exam inputs are fed whole; the model's positions are fixed sinusoids, so there is no position table to run out of. Training rows longer than the training cap are dropped and counted, never cut |
| H-NOHARM | on all six NO-HARM exams, every item comes out identical with the translator OFF and ON in every field except reply wording (status, output value, limiting ingredient, writes, receipt hash, faces held, score, learned digest, stock after, setup statuses). Owner's words: "wave-5 exams identical on/off except wording". Differences are listed with "score better" / "score worse" beside each, but any difference fails the gate |
| H-REMOVE | with the `helm_cas_translator/` folder deleted from a copy of the package, the OFF run reproduces the OFF digests exactly; and the OFF run reproduces each wave's own recorded FULL-arm records (c38, c39, c40) — "same brain" |
| H-SEP | the static separation test passes on the host: the translator imports only stdlib + torch, names no HELM module, store, receipt or approval file, and uses no socket, subprocess or network module |
| H-CUSTODY | the sealed exam's raw and LF-normalized sha256 equal the custodian's seal record before and after; the exam seed recomputed from the approval record equals the seal record's; leakage checks (section 12.4) recorded, and after drops 0 exact and 0 eight-word overlaps remain |
| H-NOFOREIGN | the weights manifest shows random initialisation from a recorded seed; the tokenizer manifest lists only allowed input files; no pretrained file is in the package or staged |

## 9. Marks (thresholds justified from today's reader numbers)

E-HUMAN-W, 128 singles unless said:
- **M-A1:** A4 RIGHT − A0 RIGHT ≥ 8.
- **M-A2:** A4 RIGHT − A2 RIGHT ≥ 4.
- **M-A3:** A4 RIGHT − C1 RIGHT ≥ 8 AND A4 RIGHT − C2 RIGHT ≥ 8.
- **M-A4:** on the 64 dialogue turns, A4 RIGHT ≥ A0 RIGHT + 4.
- A mark holds only if it holds on at least 2 of the 3 A4 seeds.

Why these sizes:
- The reader alone read 59 of 64 on wave 3b's English-64 and 62 of 64 on wave 5's, with 0 wrong (spec §7.72, §7.78).
  Those exams were generated in the reader's own sentence shapes. The step between the two waves was 3 of 64
  (4.7%). A lift of 8 of 128 (6.25%) is larger than that step, so the reader's own wave-to-wave movement cannot
  produce it.
- On sentences written by an LLM rather than by the reader's shapes, the alias-wide reader matched 233 of 439
  (53.1%; spec §7.31). So on human English the reader is expected to sit between 53% and 97%; there is room for 8.
- The wrong cap (≤ 2 of 128, 1.6%) is tight on purpose: the reader made 0 wrong readings on both English-64 exams,
  but X-REAL's builder saw it write "no water" for 7 of 128 real practice lines that only mention water
  (spec §7.79). A model may not add to that.
- M-A2 is smaller (4) because the retrieval rival is the real danger in a world this small (RB-I1's lesson: a plain
  rule ties).

## 10. Status words, verdict and the frozen reading order

Verdict words: `PASS` / `FAILURE` / `INSTRUMENT_ERROR`. Status words, frozen order:
**`EARS_EARNED_KEEP` / `EARS_NO_GAIN` / `EARS_HARMED` / `INCONCLUSIVE`.**

The merge reader applies these rules in this order, and stops at the first that fires:
1. Any instrument problem (a pinned file differs, a run is incomplete, a result file is missing, a seed is missing,
   H-CUSTODY or H-NOFOREIGN fails, the OFF run does not reproduce a wave's own records) → `INSTRUMENT_ERROR`,
   word `INCONCLUSIVE`.
2. H-CWFW, H-NOHARM, H-REMOVE, H-WRITE, H-READBACK or H-SEP fails → `FAILURE`, word `EARS_HARMED`.
3. H-RT or H-LEN fails → `FAILURE`, word `EARS_NO_GAIN`.
4. All hard gates pass and M-A1, M-A2, M-A3 and M-A4 all hold → `PASS`, word `EARS_EARNED_KEEP`.
5. All hard gates pass and a mark is missed → `PASS`, word `EARS_NO_GAIN`.

INCOMPLETE is never a pass. A word is licensed only with verdict `PASS`.

## 11. Honest predictions (written before any data exists)

- A0 reader alone on human English: RIGHT 50–85 of 128, WRONG 0–2.
- A4 vs A0: a modest lift, mostly fillers, typos, contractions, word order, number words above ten: +5 to +20.
  Turns with a missing number or an unknown ingredient stay asked in every arm.
- A4 WRONG_PROPOSED: not zero; 1–4 of 128. Because a round trip checks FORM, not MEANING. This may fail H-CWFW.
- C1 shuffled: many well-formed proposals, RIGHT near A0, WRONG_PROPOSED well above A4.
- C2 frozen: most proposals fail the lock or the checks; it collapses to A0 plus questions.
- A2 retrieval: A4 − A2 between 0 and 12. A tie gives `EARS_NO_GAIN`, and that is a result.
- A5 twin: within 4 RIGHT of A4.
- E-NOTATION: strict MATCH 28–45 of 98 for A4 (lexicon v2 alone: 32); most extra rows land in GUESS. Scribe: 0
  (now measured: 0 of 98, c41).
- NO-HARM: identical on all six exams (reader first; the brain exams were built in the reader's shapes).
  If not identical, the verdict is FAILURE, and the listed differences show whether it was a wiring bug.
- The builder's honest overall forecast: `EARS_NO_GAIN` or `EARS_EARNED_KEEP` are about equally likely;
  `EARS_HARMED` through H-CWFW is the main risk.

## 12. Custody

### 12.1 Exam seed (coordinator's custody addition, 2026-10-19)
`seed_source = sha256( UTF-8( OWNER_LINE + ":" + ZIP_SHA256 ) )`, where OWNER_LINE is the owner's verbatim
pre-approval line in section 0 (exact bytes, including the three spaces after "FOLLOWING:") and ZIP_SHA256 is the full
lowercase hex sha256 of the final sealed zip `HELM_CTT_20261019_SOURCE_CTT.zip`. No seed can be known before the
package bytes are final. The custodian recomputes it; the merge reader recomputes it again (H-CUSTODY).

### 12.2 Bands (each 1,000,000 wide, above every band used so far)
Above X5 (English-64 1,878,000,001–1,879,000,000; Faces-64 1,880,000,001–1,881,000,000), X4 (1,858–1,863 million)
and X-REAL (XS 1,898,000,001–1,899,000,000 … XF 1,904,000,001–1,905,000,000):
- **CW** (E-HUMAN-W singles) 1,920,000,001–1,921,000,000, k = int(seed_source[0:16], 16)
- **CD** (E-HUMAN-W dialogues) 1,922,000,001–1,923,000,000, k = int(seed_source[16:32], 16)
First slot = k mod 1,000,000; seed = band start + slot. A draw that the content checker refuses steps the slot
s ← (s + 1) mod 1,000,000 inside its band; a band with no free slot = STOP (never another band). Every step is
written to `SEED_DERIVATION_CTT.json`.

### 12.3 Hold-out rules
- Builders (any agent) never see the writer sheets, the sentences, the drawn records, the sealed 98 rows or
  E-X-REAL-S. The builder printed ONE item of the spent X3 English-64 file while learning its format for the NO-HARM
  harness (2026-10-19); X3 is spent and is used only for NO-HARM, never as a CTT exam.
- Writers get one neutral instruction and their sheet. They are shown no example sentences and none of the
  generator's templates, so the exam is not primed toward the reader's shapes.
- D6 traces and the 99 DEV rows are exposed; they are never exam material.

### 12.4 Leakage checks (run on the host, automatically, before training; counts only)
1. Exact match: no exam sentence in training (lower-case, whitespace-normalized).
2. Near match: no exam sentence shares an 8-word sequence with any training input. Every hit drops the TRAINING
   row, never the exam row.
3. Content match (E-HUMAN-W): the share of exam records whose exact content also occurs as a training target is
   reported ("new wording of known content" vs "new content"). The world is small; content may recur.
4. The same checks run against the sealed 98 (E-NOTATION) and against the six NO-HARM exam files.
The report holds counts and the sha256 of the dropped-row list only, no text.

### 12.5 Byte traps
Every file is hashed twice, raw bytes and LF-normalized; the receiver checks raw. Files are written `.partial` then
renamed; the publisher refuses to overwrite. JSON numbers in CAS content are strings. UTF-8 everywhere (`-X utf8`);
`⟨ ⟩ ⟦ ⟧ Θ Ω ∘ ×` are checked byte-exact after every copy (CRLF trap of the lexicon-v2 split script).

## 13. Compute, limits and cost

- One AWS GPU instance, `us-west-2`, `g5.xlarge` (1 × A10G 24 GB, about 1.006 USD/hour on demand); fallback
  `g4dn.xlarge` (1 × T4, about 0.526 USD/hour) only if g5 capacity is refused. Price checked on the day.
- Order on the host: preflight (static separation test, unit tests, exact parameter counts asserted against torch,
  a 15-minute-capped GPU smoke of 50 steps on 2,000 pairs) → data build + leakage → training A4 ×3, A5, C1 →
  scoring all arms → NO-HARM → results packed → instance terminated → cleanup verified by a second describe call.
- Caps: **8.00 USD total**; instance life 6 hours (self-terminate); job wall cap 5 hours; one attempt + one plumbing
  retry (a retry only if no model was scored; never with any setting changed).
- Expected: training about 40–90 minutes for the five trained arms; total about 2–4 hours; about 2–4 USD on g5.
- Local laptop: no torch at all (torch alone needs 475 MiB of RAM, measured 2026-10-19, above the 300 MiB
  per-process laptop limit; free RAM was about 754 MB, below the design's 2 GB smoke floor). The GPU smoke therefore
  runs on AWS inside the cap, as the design allows.

## 14. What a PASS would license, and what it would not

Licensed sentence (the frozen reader fills the numbers; nothing wider):
"On HELM's eight-ingredient, four-recipe kitchen world, with English written for this exam by the owner and two named
people, a from-scratch CAS-token translator placed behind HELM's deterministic reader, round-trip check and read-back
raised the turns HELM read correctly from [A0] to [A4] of 128, beat a no-learning retrieval rival by [A4 − A2], added
[n] confident wrong readings (cap 2), wrote nothing without a yes, and changed none of the brain's exam results."
Ceiling named: training on our own generated English + LLM-written SDG English + Tatoeba / Taskmaster practice inputs;
tested on E-HUMAN-W only.

NOT licensed: "HELM is a chatbot about everything" or understands English in general; anything outside the 8 stock
cells and 4 recipe shapes; anything about the sealed 98 beyond "synthetic-source English"; anything about the mouth;
anything about the brain (its claims stay exactly as spec §7.47–§7.79 record them); live use on the laptop.

## 15. Files of this packet

`PREREGISTRATION_CTT.md` (this), its pre-code copy and sha256; `HELM_CTT_20261019/` (code, tests, frozen settings,
custody tools); `HELM_CTT_20261019_SOURCE_CTT.zip`; `PACKAGE_FREEZE_CTT.json`; `TEST_COUNTS_CTT.json`;
`RUN_LIMITS_CTT.json`; `LAUNCH_BRIEF_CTT.md`; `custody/CUSTODIAN_PROCEDURE_CTT.md`; `APPROVAL_RECORD_CTT.md`
(replaces the sign request: it quotes the owner's pre-approval line and names the final zip sha256).

## 16. Deviations from the design, found while building (dated; no threshold, arm, gate or word changed)

All entries 2026-10-19 (Pacific), written after the code existed and before sealing. None changes a threshold, an
arm, a gate, a status word or a prediction.

- **D-CTT-1 Twin shape.** The design named the twin "about 2.5 M: width 192, 3 + 3 layers". With the shared
  8,349-token table that shape is 4,764,382 parameters. The owner accepted the SIZE ("9.6 M with a 2.5 M twin"), so
  the size is kept and the shape changed: width 128, 3 + 3 layers, feed-forward 512 = 2,482,718 parameters. Main
  model as designed: 9,585,566 parameters.
- **D-CTT-2 "Would ask".** Read as: reader status CLARIFY, OR status NOT_MINE on a sentence the reader itself claims
  (`helm_english_in._claimed`: a kitchen word is present but nothing was read). Small talk is never sent to the model.
- **D-CTT-3 Sources not used.** D3 (fresh SDG runs): D4 already covers every SDG category. D5 (phrasebook): mouth
  parked. D7 Taskmaster-1 dev USER turns: loading its 65 MB + 37 MB dialog files exceeds the laptop's per-process
  memory limit; D7 is Tatoeba practice only (2,044 rows extracted, sha256
  `6fe92976f1741aac963b4d922297089bb232ce510d11dbb08420fb070e215f56`, from the X-REAL pin
  `bb3dcc28a8984a26dc466ee14eb53c4210b0dd9bb111b9d686d1efc83ecf091c`).
- **D-CTT-4 Ears scope.** Faces sentences ("the yeast is getting old") and user facts route to their own readers in
  HELM; the translator is trained to answer NOT_MINE on them. E-HUMAN-W draws are limited to stock, absence, product
  questions, witnessed batches, must-ask turns and dialogue references (answers to HELM's question, "add N more",
  "it / that").
- **D-CTT-5 Names.** For a word HELM does not know, the training target is still the structural reading with a
  pointer; HELM's own name table in the checker turns it into a question (UNKNOWN_INGREDIENT / UNKNOWN_PRODUCT). So
  the model learns to point, and the readable table decides (design section 4 item 4).
- **D-CTT-6 Count scope (clarification of section 7, wording already there).** `CONFIDENT_WELL_FORMED_WRONG` counts
  readings PROPOSED by the model (or by the retrieval rival). A wrong reading made by the reader itself (today's
  behaviour, written directly) is counted as READER_WRONG in every arm and reported beside it.
- **D-CTT-7 "Same brain" across hosts.** Receipt hashes carry the brain folder's path. Measured on the laptop
  (0 USD): the OFF run of X5 English-64 matched c40 in every value, but 24 of 64 answer receipt hashes differed. So
  H-REMOVE's cross-host check uses wave 3b's own same-brain projection (status, value, limiting, writes, learned
  digest, score, plain). With it, the laptop OFF run reproduced c40 on X5 English-64 and c38 on X3 Faces-64. Inside
  one host, H-NOHARM still compares receipt hashes, faces held and stock after.
- **D-CTT-8 NO-HARM arms.** Run for each of the three A4 seeds (hard gates hold on each seed); not for A5, C1, C2.
- **D-CTT-9 No local GPU smoke.** torch alone measured 475 MiB of RAM (above the 300 MiB per-process laptop limit);
  free RAM was 744-772 MB (below the design's 2 GB floor). So `model.py`, `train.py` and `serve.py` were checked
  only by reading and by the laptop tests that parse them; they first run in the AWS preflight (50-step smoke, exact
  parameter count, translator audit). A failure there is plumbing: no model scored, one retry allowed.
- **D-CTT-10 Harness checks on the laptop (0 USD, no torch).** NO-HARM ON with a fake "always ask" proposer gave
  the OFF digest exactly; with a fake "topic on the first word" proposer the digest changed (the gate can fail). On
  X5 English-64 the reader handed 34 turn reads to the ears (each must come back as a question for H-NOHARM).
- **D-CTT-11 Custody slip, disclosed (FLAG_FOR_HUMAN_REVIEW).** While checking file shapes, the builder printed the
  first 400 characters of ROW 1 of the sealed 98 (English only; its gold record was not shown). No code uses it; the
  row is excluded from training by file/line and by text; E-NOTATION carries no word. The builder also printed one
  item of the spent X3 English-64 file (format), the first row of the SDG description file (an rpm_chain row, not a
  recipe) and three DEV rows (allowed).
- **D-CTT-12 Scribe L4 slot filled** before any code from run c41 (section 5.3), with the coordinator's three
  lessons written into the gates (H-CWFW, H-LEN, answer key against the proposed record).

## 17. Amendment A-CTT-1 (2026-10-19 PDT, coordinator decision, operational; written BEFORE the reseal)

**Why.** The paid run must not wait for the owner and two other people to write 128 sentences and 16 dialogues.
**What changes, and only this.** Scope, arms, caps, every threshold and every status word stay as written above.

1. **Which parts depended on the human exam (as sealed at zip 3289755c…):** all four marks M-A1, M-A2, M-A3, M-A4;
   hard gates H-CWFW (the 128 singles), H-RT (b) (the proposals' well-formed share), H-READBACK and the saved-wrong
   part of H-WRITE (read on the ears turns), H-LEN (the exam inputs), and H-CUSTODY (the exam seal, its seed and its
   leakage presence). The reader stopped with `INSTRUMENT_ERROR` when the human exam was missing. Not dependent:
   H-NOHARM, H-REMOVE, H-SEP, H-NOFOREIGN, the translator-audit part of H-WRITE, and E-NOTATION.
2. **Primary reading = the MACHINE-SIDE exam E-MACHINE-S**, sealed now by the custodian, blind, seed from
   sha256(owner line + ":" + zip sha256), band CM 1,924,000,001–1,925,000,000 (k = seed_source characters 32–47):
   128 real sentences other people wrote (Tatoeba English, Google Taskmaster USER turns), 32 per stratum
   (quantity, absence, question, other), drawn from X-REAL's pinned Part S frame (`FRAME_S.jsonl`
   `98c2fb8f…`, which already excludes the practice partition CTT trained on), never one of the 128 items X-REAL
   used (`INPUTS_XREAL.json` `37312a31…`) and never an equal text. Answer key = X-REAL's frozen rule K-S
   (`xreal/keys.py` `7ad232a6…`), computed by the custodian from the text alone; scoring = X-REAL's K-S table
   (FACTS: right if the written facts equal the key, wrong if anything extra; ASK: right if HELM asks and writes
   nothing, wrong on a write or an answer; EMPTY: right with 0 writes; UNDETERMINED: not scored). Tool:
   `custody/draw_machine.py`. These are the design's own "public-input sentences" (DATA.md D7 / TEST_PLAN E-X-REAL-S);
   the "SDG-held-out" part is the sealed 98, which stays reported only (unchanged).
3. **The same gates and thresholds are read on E-MACHINE-S:** H-CWFW (≤ 2 proposed of the 128, ≤ A2's, 0 saved),
   H-RT, H-READBACK, H-WRITE, H-LEN, H-CUSTODY (machine-side seal), plus NO-HARM, H-REMOVE, H-SEP, H-NOFOREIGN.
   Marks M-A1, M-A2, M-A3 with the same thresholds on the scored items. **M-A4 needs dialogues; E-MACHINE-S has none,
   so M-A4 is `NOT_EXERCISED` in the primary reading and is read only in the human pass.** The primary word
   `EARS_EARNED_KEEP` therefore needs M-A1–M-A3.
4. **HUMAN_EXAM_ABSENT path.** The primary reading never reads the human exam. Its human line always says
   `NOT_RUN (HUMAN_EXAM_ABSENT)` and fails no gate.
5. **The human exam E-HUMAN-W is an OPTIONAL later pass.** If and when the owner supplies the sentences, the custodian
   seals them (section 12, unchanged; band CW/CD), and `kit/run_ctt_human.py` scores them against the SAME frozen
   weights (sha256 checked against each `WEIGHTS_MANIFEST.json`), with all four marks and the ears gates, read by
   `merge_ctt --pass human` as a SEPARATE reading with its own status line. It pins the primary reading by sha256 and
   never changes it. Because training is already done, exam turns that equal or share an 8-word sequence with a
   training input are left out of the human scoring and counted (the training data is never redone). It runs inside
   the same 8.00 USD cap; it trains nothing.
6. **What a PASS licenses (section 14, narrowed for the primary):** "On HELM's eight-ingredient, four-recipe kitchen
   world, on 128 real sentences other people wrote (Tatoeba and Google Taskmaster, X-REAL's frame, keyed by X-REAL's
   frozen rule), a from-scratch CAS-token translator placed behind HELM's deterministic reader, round-trip check and
   read-back raised the scored sentences HELM handled right from [A0] to [A4], beat a no-learning retrieval rival by
   [A4 − A2], added [n] confident wrong readings (cap 2), wrote nothing without a yes, and changed none of the brain's
   exam results." Nothing about people typing to HELM, dialogues or pronouns is licensed by the primary reading.
7. **Predictions for E-MACHINE-S (written now, before any draw):** most keys will be EMPTY or UNDETERMINED (X-REAL's
   own forecast and c42's result: 109 of 128 scored, few FACTS keys). A0's RIGHT will be high on EMPTY and ASK keys
   and the room for M-A1 (+8) is small: `EARS_NO_GAIN` is the more likely primary word. The reader alone wrote 8 wrong
   facts on X-REAL's 128 (c42); those stay READER_WRONG in every reader-first arm.
8. **`FLAG_FOR_HUMAN_REVIEW` (the builder's honest note on governance).** Owner pick Q7 ("kitchen turns count") put the
   claim on human English typed to HELM. This amendment, made by the coordinator, moves the primary word to
   public-input sentences written for other reasons. The owner may reverse it; until then the human pass is where
   the Q7 claim can be earned.
9. **Custody slip D-CTT-11, named precisely.** The file was
   `cas-synthetic/data/l4_split/real_heldout_unparseables_98.jsonl` (the E-NOTATION exam, "the sealed 98"; sha256
   `e269a448cf1d087aa6b98436dadfbfdefa60216346f0f886659f0f9d7dd61cfe`), read from the builder's worktree of
   `origin/claude/project-thread-pmbzd6` at `2615d8d7`. It was sealed by commit `ec780a34` (2026-10-18, author
   "Little Henderson", "L4 Proposer baseline & anti-circular sealed split: tabulate 439 SDG sentences and seal held-out
   98 rows"; spec §7.53–§7.54). The builder printed the first 400 characters of its FIRST row: the row's id fields and
   the start of its English sentence; the row's gold record was not printed. E-NOTATION stays reported only; it is
   not part of the machine-side primary exam, so the slip touches no word.

