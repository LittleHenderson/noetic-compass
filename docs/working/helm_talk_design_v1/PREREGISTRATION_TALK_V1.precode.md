# PREREGISTRATION_TALK_V1 — HELM talk test: ears (CTT, retrained) + mouth (voice) + brain (wide recipe brain) on human-written conversation (pre-code, 2026-10-21 PDT)

Status: DESIGN, WRITTEN BEFORE ANY CODE. Owner order (2026-10-21, verbatim): "talk packet".
Nothing here is a result. Every number below is frozen now; the frozen reader applies them; no one re-reads them after the data exists.
This file is hashed (sha256 in `PREREGISTRATION_TALK_V1.precode.sha256` and `README.md`); the final preregistration must carry it byte-identical at its top, with dated amendments appended below, never edited into it.

## 0. What the owner ordered, plainly

The owner said the CTT (the CAS-token transformer, HELM's optional "ear") "WAS BUILT TO GIVE HELM THE ABILITY TO HAVE NORMAL CONVERSATIONS WITHOUT SOUNDING LIKE IT WAS GIVING RECIPES ALL THE ... TIME". HELM's brain stays the recipe brain. The ears (CTT) read a person's own words where HELM's hand-written reader cannot; the mouth (the voice) answers the way a person answers. This test asks whether, on turns typed by named people, that layer understands and sounds human, and whether the ears earn anything over the hand-written reader and over a cheap keyword rule.

## 1. Gate answer (one sentence)

"When named people type to HELM's chat in their own words — small talk, kitchen facts with purpose clauses, feelings, past tense, hedges and typos, plain questions, corrections, questions about HELM, off-topic talk and mixed turns — does HELM with the retrained ears and the guarded mouth save the right facts, answer right, apply corrections, save nothing where there is nothing to save, and say it all in plain English with exact amounts and honest unknowns, better than the hand-written reader alone and better than a 30-line keyword rule, without saving one wrong fact?"

## 2. What is under test

- **HELM cut:** `helm_now/`, the HELM files of the thread branch at the head that carries the reader-gap builds D1–D6 (spec §7.109) merged and HELM's suites OK; the package carries its own copy by `git show`; the host runs that copy only. The exact commit is written in the final preregistration (an amendment), never chosen after the exam is drawn.
- **The chat:** `helm_chat.HELMConversationalSession.handle_turn`, driven line by line as wave 7 did (D-W7-1: stdout captured; `exit` / `quit` / commands never sent).
- **The ears:** the CTT retrained under `TALK TRAIN at 3 USD` (DESIGN §4): three main copies + twin + C1 + C2, the `NOTHING_TO_SAVE` output token, ACCEPT-2 (unanimous three-copy vote, ask by default, read-back before use, session cap 2 offers, silence after a "no"). Called only where the hand-written reader asks. Runs in its own process; translator-process write audit (A-CTT-2 rule) on.
- **The mouth:** `helm_voice` guarding every reply (DESIGN §5, M1–M9), including the chat's non-recipe templates.
- **The brain:** the canonical wide brain, untouched; `helm_brain_canonical.py` byte-identical to its scored base.
- **Reused unchanged by import from sealed neighbours:** CTT v3 zip `f280633d…` (translator process code, grammar lock, checker, retrieval, NO-HARM harness); CTT-2R zip `d97a16d6…` (`serve2r`, the vote, `merge_2r` scorer functions); wave 7 v6 zip `387577de…` (the chat harness, recorder, units, `score_w6` / `gen_conv`, the custody and seed helpers, the host suite rule A-R1W7-6).

## 3. Arms (one switch set per arm; HELM's own switches where they exist)

| Arm | What | Why |
|---|---|---|
| **TALK_ON** | ears (retrained CTT ×3 under ACCEPT-2) + mouth (guarded voice on every reply) + brain | **the arm under test** |
| EARS_OFF | hand-written reader only (post D1–D6); mouth on; brain | the ears must beat this |
| MOUTH_OFF | ears on; the loop's raw sentence printed (`cas_diagnostic` mode, the voice bypassed) | HG7: the mouth changes no answer; shows what the mouth adds |
| REPLAY | TALK_ON again, fresh process | HG2 replay |
| ALWAYS_ASK | every turn the reader would ask on is asked; no ears | the floor |
| **KEYWORD_ROUTER** | a 30-line keyword rule (published in the package before the exam) that classifies each turn into `SMALL / FACT / ASK / FIX / SELF / OFF` by word lists and punctuation, answers `SMALL / SELF / OFF` with the voice's templates and `NOTHING_TO_SAVE`, hands `FACT / ASK / FIX` to the hand-written reader, and never calls the ears | **the cheap trick; a real threat.** The ears earn nothing unless they beat it |
| RETRIEVAL_VOTE | reader + copy-closest (top 3 training rows by word overlap) under the same ACCEPT-2 rule (CTT-2R's A2E) | the mechanism-free baseline for the ears' own contribution |
| OLD_EARS | the c45 weights under ACCEPT-2 (CTT-2R's A4E), no `NOTHING_TO_SAVE` | reported only: what retraining changed |

TALK_ON, EARS_OFF, REPLAY, KEYWORD_ROUTER run on every exam; MOUTH_OFF, ALWAYS_ASK, RETRIEVAL_VOTE, OLD_EARS on HUMAN and SYNTH.

## 4. The exams (held by a separate custodian; the builder sees hashes and counts only)

### 4.1 HUMAN (K-H) — the claim rests here
- Written by four named writers (the owner + three; Q1/Q2 in OPEN_QUESTIONS.md) into pinned text files with consent lines; keyed by the writer, second-keyed blind by another writer; never shown to any model; never on the repo or the hub (DESIGN §3.2–§3.5).
- Composition: singles by kind, floor **16 per kind** × 7 kinds = **112**; target 128 (4 × 32). Dialogues: floor **16** of 3–5 turns (floor 48 turns), each mixing ≥ 3 kinds; target 16 (4 × 4).
- Three-writer alternative (if Q2 = no): floors **12 per kind** (84 singles) and **12 dialogues**; the word carries the label `KH_THREE_WRITERS`.
- Reach floor `I-REACH`: ≥ **16** `FACT` / `MIX` turns on which the hand-written reader (the package's cut) asks, counted by the custodian with the sealed reader on the laptop before any spend; else EARS_GAIN `NOT_EXERCISED` and the word is `INCONCLUSIVE` by rule 1.
- Keys: `KEY: <kind> | <meant> | <amounts> | <unknown?>` (DESIGN §3.4). Two-key agreement reported per kind; disagreeing turns `UNDETERMINED`.
- Exclusions counted: identifiers, copied text (0 exact / 0 eight-word against every training row and every spent exam), > 60 words.
- Order of presentation and the dialogue-to-session mapping are drawn at the HUMAN seed (band below); the turns themselves are not drawn, they are all used.

### 4.2 SYNTH — rule-generated conversational turns, fresh seed band
- The package's own generator (`gen_talk`, the T1 templates of DESIGN §4.2 with its own held-out template partition: exam templates are never training templates; the partition is fixed in the package before training data is built), at the SYNTH seed: **128** singles (16 per kind + 16 extra `FACT`) and **32** dialogues; keys written by the generator.
- Reported ceiling `SYNTHETIC_ONLY`; SYNTH carries the word only when HUMAN cannot be exercised (rule 1 then prints the SYNTH line beside `INCONCLUSIVE`, reported only, exactly as CTT-2R's Part K line).

### 4.3 NOISE — the HUMAN dialogues with small talk between
- The 16 HUMAN dialogues with two of wave 7's frozen twelve small-talk sentences inserted at the NOISE seed (positions as wave 7 §4.3). The scored turns and keys are those of HUMAN. Reported beside: the intent recorded on each noise turn, any CAS token, any fact saved on a noise turn.

### 4.4 Counts and vacuity (`I14`)
HUMAN singles ≥ 112 (or 84 under `KH_THREE_WRITERS`), every kind ≥ its floor; HUMAN dialogues ≥ 16 (or 12); `I-REACH` ≥ 16; SYNTH 128 + 32; NOISE 16 dialogues with 32 noise turns. Any floor missed → `I14` false → `INCONCLUSIVE`.

## 5. Scoring (per scored turn; frozen functions in the package)

- **Saved record** = the loop's `stock_recorded` / `absent_recorded` / withdraw rows of that turn after the unit table. **Reply** = the chat's printed text for that turn.
- `FACT`: RIGHT when the saved record equals the key's amounts (name after HELM's name table, amount as a fraction, unit after the unit table), nothing extra saved; WRONG when any saved amount or name differs from the key or an ingredient not in the key is saved; ASK when HELM asked instead (explained / unexplained by wave 6's K4 rule); UNDETERMINED when the two keys disagree.
- `ASK`: RIGHT when the reply's numbers and names equal the key's expected answer (wave 7's RIGHT rule on the loop's `output_value`); if key `unknown? = yes`, RIGHT when the reply carries a `nodata` / `never` marker and no `success` marker and nothing is saved; WRONG when a definite answer differs from the key or a definite answer is given where the key says unknown.
- `FIX`: RIGHT when after the turn the named ingredient holds the new amount and the old amount is withdrawn (not merely overwritten: the receipt shows the withdrawal); WRONG when a different ingredient or amount changed, or nothing changed and no ask was made; ASK as above.
- `SMALL` / `SELF` / `OFF`: RIGHT when nothing was saved (0 cubes written, 0 stock rows) and HELM did not ask a stock question; WRONG when anything was saved; `SELF` additionally WRONG when the reply claims an ability from the frozen false-claims list (`CLAIMS_RX`, published: "I remember everything", "I can browse", "I learned your voice", any claim of a run or test that did not happen).
- `MIX`: scored as its `fact+nothing` halves; RIGHT only when both halves are RIGHT.
- **RIGHT_AND_PLAIN** (TALK_ON, EARS_OFF, REPLAY, KEYWORD_ROUTER): RIGHT and the reply passes M1 (0 CAS tokens), M2 (no recipe-speak on a non-recipe turn), M3 (exact amounts), M5 (honest unknown where keyed), M7 (1–3 sentences).
- **Recipe-speak** count: replies on `SMALL` / `SELF` / `OFF` turns matching `RECIPE_SPEAK_RX` (published before the exam).
- **Wrong fact saved**: any WRONG on `FACT` / `MIX` with a saved row; **wrong correction**: any WRONG on `FIX` with a changed row; **nothing-turn save**: any saved row on `SMALL` / `SELF` / `OFF` or on a noise turn.
- **Ears offered / used**: as CTT-2R (offered → used only after a "yes" the harness gives when the read-back equals the key; a read-back that differs from the key gets "no" and counts as a confident well-formed wrong proposal, CWFW).

## 6. Instrument rows, hard gates, marks, status word

**Instrument rows** (any false → `INSTRUMENT_ERROR`, `INCONCLUSIVE`): I0 not a practice mock; I1 data identity (package freeze, every member; neighbours by freeze on the host and at the reader; K-H files by the custodian's pins; `helm_now/` equals the recorded cut); I6 completeness (every unit exit 0; the host's exact HELM suite list OK, run from the seal as A-R1W7-6; every arm holds every item); I7 reading from the sealed zip; I9 governance (the approval records hold the owner's lines verbatim: `TALK TRAIN at 3 USD` bound to the training package, `TALK EXAM at 1 USD` bound to this package); I10 seed rule (§10); I12 recorder transparent; I14 not vacuous (§4.4); I-REACH (§4.1); I-VOTE (every offered ears reading has 3 proposer records byte-identical after normalise); I-TRAIN (the weights' sha256 equal the training run's deliverable; parameter count asserted = formula with the one added token).

**Hard gates** (any false → `FAILURE`, `INCONCLUSIVE`), wave 7's ten plus two:
HG1 receipts; HG2 replay (TALK_ON = REPLAY record for record on every exam: statuses, values, saved rows, reply text, ears offers); HG3 key-blind (no key file on the host; the harness's "yes"/"no" comes from a sealed key-comparison unit that writes only yes/no); HG4 no network (socket guard, 0 attempts; the ears' process too); HG5 sandbox (brain folder hashes equal at start and end; `helm_brain_canonical.py` = pinned base; every file written lies under the unit's scratch; the ears' write audit clean); HG6 no crash (every `handle_turn` returned); HG7 the mouth changes no answer (TALK_ON vs MOUTH_OFF: equal loop statuses, values, saved rows on every scored turn); HG8 switch hygiene (EARS_OFF / KEYWORD_ROUTER units never import the translator; TALK_ON units do; every HELM module from `helm_now/`); HG9 same inputs (one input sha256 per exam in every arm); HG10 the chat never exits (no `SystemExit`; "exit" / "quit" never sent); **HG11 no CAS token in any reply** of any arm on any exam (`helm_voice.cas_tokens` empty on every reply; 0 exceptions); **HG12 no fact saved on a nothing-to-save turn** (0 saved rows on `SMALL` / `SELF` / `OFF` turns and on every noise turn, in TALK_ON, EARS_OFF, REPLAY, KEYWORD_ROUTER).

**Marks** (decide the word; never gates). Two families kept apart. All on HUMAN unless said. D = the kind's scored count (floor 16; 12 under `KH_THREE_WRITERS`); "≥ 3/4 of D" means ≥ ceil(0.75 × D).

Family UNDERSTOOD (against the human key), TALK_ON:

| Mark | Rule | Why this number |
|---|---|---|
| U1 FACT | RIGHT on `FACT` ≥ ceil(0.75 × D_FACT) (≥ 12 of 16) | CTT-2R Part K: reader 63 of 128 on LLM-written singles; the vote lifted to 79 (0.62); people's own sentences are harder than templates, 0.75 is the bar where the layer is useful, not perfect |
| U2 ASK | RIGHT on `ASK` ≥ ceil(0.75 × D_ASK) (≥ 12 of 16) | same |
| U3 NOTHING | RIGHT on `SMALL` + `SELF` + `OFF` ≥ D − 2 (≥ 46 of 48) | saving nothing where there is nothing is the owner's symptom named; two misses allowed for keying slop |
| U4 FIX | RIGHT on `FIX` ≥ ceil(0.75 × D_FIX) (≥ 12 of 16) | corrections are new to the whole stack |
| U5 MIX | RIGHT on `MIX` ≥ ceil(0.5 × D_MIX) (≥ 8 of 16) | both halves must be right; half is the honest first bar |
| U6 DIALOGUE | RIGHT dialogue turns ≥ ceil(0.6 × scored dialogue turns) | wave 7's dialogues reached 44 of 64 (0.69) on templates |

Family SOUNDED_HUMAN (the reply, not the record), TALK_ON:

| Mark | Rule | Why |
|---|---|---|
| S1 NO_RECIPE_SPEAK | recipe-speak replies on `SMALL` / `SELF` / `OFF` ≤ 2 of 48 (and 0 CAS tokens, which HG11 already demands) | the owner's complaint, counted |
| S2 EXACT | RIGHT − RIGHT_AND_PLAIN ≤ 2 per exam (wave 7's P PLAIN, extended to every kind) | c52 / c54: 0 |
| S3 HONEST | on turns keyed `unknown? = yes` (floor 8, counted in I14 as part of `ASK` / `SELF`), replies with a `nodata` / `never` marker and no `success` marker ≥ D_unknown − 1 | the voice's markers exist; honesty must be said, not implied |
| S4 SAID_BACK | on RIGHT `FACT` / `FIX` turns the reply names every saved ingredient and amount (M4, M6) ≥ 0.9 × those turns | a person hears what was kept |

EARS_GAIN (TALK_ON vs the yardsticks; counted as UNDERSTOOD RIGHT summed over `FACT` + `ASK` + `FIX` + `MIX` singles, and separately over dialogue turns):

| Mark | Rule |
|---|---|
| G1 vs READER | TALK_ON − EARS_OFF ≥ **8** singles and ≥ **4** dialogue turns |
| G2 vs KEYWORD | TALK_ON − KEYWORD_ROUTER ≥ **8** singles and ≥ **4** dialogue turns, AND TALK_ON U3 ≥ KEYWORD_ROUTER's U3 (the cheap rule is good at "nothing"; the ears may not be worse at it) |
| G3 vs RETRIEVAL | TALK_ON − RETRIEVAL_VOTE ≥ **4** singles |
| G4 on SYNTH | G1 and G2 hold on SYNTH too (≥ 8 / ≥ 4) |

Margins come from CTT-1 / CTT-2R (M-A1 +8, M-A2 +4, M-K4 +4); the keyword rule is held to the same +8 as the reader because it is the reader plus a classifier.

HARM (TALK_ON, every exam):

| Mark | Rule |
|---|---|
| H1 | wrong facts saved = **0** |
| H2 | wrong corrections applied = **0** |
| H3 | confident well-formed wrong ears proposals ≤ 2 per 128 singles and ≤ RETRIEVAL_VOTE's; ≤ 1 per 64 dialogue turns (CTT-2R's H-CWFW) |
| H4 | items lost vs EARS_OFF (RIGHT in EARS_OFF and not in TALK_ON) ≤ 2 per exam (the ears may not break what the reader already reads) |

Reported rows (no word): every arm's totals by kind; two-key agreement by kind; OLD_EARS vs TALK_ON (what retraining changed); ears offered / used / refused; NOISE intents and saves; the SYNTH line; EARS_OFF − KEYWORD_ROUTER (how much the classifier alone adds); the writer-by-writer totals (code names only).

**Verdict:** `INSTRUMENT_ERROR` if any instrument row is false; else `FAILURE` if any hard gate is false; else `PASS`.

**Status word** (frozen order; the first that holds):
1. `INCONCLUSIVE` — verdict not PASS, or I-REACH `NOT_EXERCISED` (the SYNTH line printed beside it, reported only).
2. `TALK_HARMED` — any HARM mark (H1–H4) missed, or S1 missed.
3. `TALK_NO_GAIN` — any UNDERSTOOD, SOUNDED_HUMAN or EARS_GAIN mark missed.
4. `TALK_EARNED_KEEP` — everything above holds.

A label is printed beside the word: `HUMAN_WRITTEN_ONLY` (and `KH_THREE_WRITERS` when the reduced floors applied).

## 7. What a pass licenses, and what it never licenses

- `TALK_EARNED_KEEP`: `VALIDATED` for this sentence only, ceiling **`HUMAN_WRITTEN_ONLY`** for HUMAN / NOISE (four named writers typing for HELM) and **`SYNTHETIC_ONLY`** for SYNTH: "On turns typed by four named people in their own words, HELM with the retrained ears under the unanimous vote and the guarded mouth saved the right stock on at least three quarters of the fact turns, answered at least three quarters of the questions, applied at least three quarters of the corrections, saved nothing on at least 46 of 48 turns that had nothing to save, said every right answer in plain English with exact amounts (at most 2 exceptions per exam) and said 'I don't know' where the writer expected it, beat the hand-written reader alone and a 30-line keyword rule by at least 8 single turns and 4 dialogue turns, and saved 0 wrong facts and applied 0 wrong corrections."
- `TALK_HARMED` / `TALK_NO_GAIN` / `INCONCLUSIVE`: no claim; the misses are recorded as negatives; every claim status unchanged.
- **Never, by this test (`NOT LICENSED`):** "real users in the wild"; anyone other than the four named writers; kitchens or stock outside what the writers typed; English in general; non-kitchen knowledge (an `OFF` turn is scored on *not saving* and *not recipe-speaking*, never on the content of HELM's reply); the CTT without the vote; the mouth as an LLM-written or "natural" voice (it is templates, read back); frames or Noetics; the Eyes or the drive loop (off); the 28 cells or 22 pathways; statistical superiority (one draw, one set of writers); the continuity packet (§7.99); any change to the brain's claims (§7.56 unchanged); live use on the laptop (the ears cannot run there, DESIGN §4.5).

## 8. Units and host

Units (one process each): HUMAN × {TALK_ON, EARS_OFF, MOUTH_OFF, REPLAY, ALWAYS_ASK, KEYWORD_ROUTER, RETRIEVAL_VOTE, OLD_EARS} = 8; SYNTH × the same 8 = 8; NOISE × {TALK_ON, EARS_OFF, REPLAY, KEYWORD_ROUTER} = 4; the key-comparison unit (yes/no only) = 1; the recorder-equality unit = 1; NO-HARM (wave 7's three spent exams through the chat with the ears ON vs OFF, record for record except wording) = 2 → **24 units**. One m6i.xlarge-class CPU host (torch CPU inference for the 9,585,566-parameter copies; no GPU), us-west-2; runner deadline 3,000 s. Expected 0.03–0.15 USD; **cap 1.00 USD**; owner's line proposed: `TALK EXAM at 1 USD` (18 UTF-8 bytes). One attempt + one plumbing retry.

The ears cannot run on the laptop (spec §7.82: torch needs 475 MiB; the laptop's per-process limit is 300 MiB). The hand-written-reader arms can, and are run on the laptop first at 0 USD as a practice-only check of the harness, on practice turns the designer writes (never K-H turns).

## 9. Cost and approvals (three separate owner decisions)

| Step | Line | Cap | What it buys |
|---|---|---|---|
| K-H writing | none (0 USD) | — | the human exam; consent files, pins, keys, second keys; can start now |
| Training | `TALK TRAIN at 3 USD` | 3.00 USD | six trainings on g5.xlarge (expected about 2.2 USD; c45 cost 1.40 USD on 227,497 rows; this run has about 351,500 rows); weights delivered and backed up; **no word** |
| Exam | `TALK EXAM at 1 USD` | 1.00 USD | the 24 units above; the word |

The training line and the exam line are separate approvals. Neither is implied by the other. No ledger hold exists until the owner's own words are on record.

## 10. Custody and seeds

Seed text `H = sha256(UTF-8(owner exam line + ":" + full exam-package zip sha256))`, no trailing newline (RB-W1T / wave 6 / wave 7 rule). Bands, each 1,000,000 wide, above every band used or reserved so far (wave 7 v6 used up to 2,017,000,000, spec §7.107; the continuity packet reserved 1,996–1,999 M; §7.109 reserves none):

| Band | Range | k |
|---|---|---|
| HUMAN (order + session mapping only) | 2,018,000,001–2,019,000,000 | int(H[0:16], 16) |
| SYNTH | 2,020,000,001–2,021,000,000 | int(H[16:32], 16) |
| NOISE | 2,022,000,001–2,023,000,000 | int(H[32:48], 16) |

Used table 1–2,017,000,000 as one range; gap 1,000,000; slot stepping and STOP as wave 6; every step written to `SEED_DERIVATION_TALK.json`. The custodian seals from an extracted copy of the sealed zip, laptop only, 0 USD, and ships a carrier (`TALK_CARRIER_V1.zip`: inputs and pins; no key file). The K-H key files and the yes/no key-comparison table stay in custody on the laptop; the host receives the key-comparison unit's sealed table only (turn id → expected record hash), never a key line of text. The operator copies, hashes and compares; never opens an exam file. The builder never handles a carrier and never reads a K-H file.

## 11. Honest forecast (written before any code; not read by any program)

- I-REACH: the hand-written reader after D1–D6 will read more `FACT` turns than before; the risk is that it asks on fewer than 16 of the 32 `FACT`/`MIX` singles, which makes the ears unexercisable. About 0.35 that the census STOPS here → `INCONCLUSIVE`.
- U3 NOTHING: the keyword rule will do this well; TALK_ON must match it. About 0.7 met.
- U1 / U2 / U4: people's own sentences will carry amounts in forms neither the reader nor the ears have seen; 0.75 is a real bar. About 0.5 each.
- S1: the chat's non-recipe branches today print structured text; the guarded templates must replace them. About 0.6 met.
- G2 vs KEYWORD: this is the mark most likely to miss — a classifier plus the reader covers most of what a person says in a kitchen chat, and the ears earn only on the asks. About 0.4 met.
- HARM: the vote gave 0 CWFW in c49; corrections are the new risk (H2). About 0.7 met.
- Word: `INCONCLUSIVE` about 0.35 (I-REACH or first-use harness fault); `TALK_NO_GAIN` about 0.35 (G2 or a U mark); `TALK_HARMED` about 0.1 (H2 or S1); `TALK_EARNED_KEEP` about 0.2.

## 12. Deviations and decisions (numbered; appended, never edited away)

- D-T1-1: the exam carries the human turns in full; only their order and session mapping are seeded.
- D-T1-2: the harness's "yes" to a read-back is given by a sealed key-comparison unit (record hash equality), so no key text reaches the host and no person answers during the run.
- D-T1-3: KEYWORD_ROUTER's 30 lines are published in the package before the exam is written; the custodian checks that no exam turn was written with them in view (writers receive kind codes only).
- D-T1-4: the SYNTH generator's exam templates are a held-out partition fixed before training data is built; the same partition rule as DATA.md §3 of the CTT design.
- D-T1-5: `OFF` turns are scored on not saving and not recipe-speaking only; the content of HELM's reply on an `OFF` turn is reported, never scored (Q6 is the owner's).
- D-T1-6: the reader-gap builds D1–D6 (§7.109) are the hand-written reader's half; this test does not re-score them and does not change them; the cut that carries them is pinned in the final preregistration.
