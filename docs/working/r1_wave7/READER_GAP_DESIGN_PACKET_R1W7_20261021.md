# READER-GAP DESIGN PACKET — HELM-R1 wave 7, the wide reader and the faces (2026-10-21; hashed before any code)

Plain English. This packet is written BEFORE any code, per the owner's order ("design hashed before code"). Its sha256 is
recorded in the spec sheet. Claim states: **MEASURED** (a program read it from a frozen file or ran on the author's own
sentences), **PROPOSED** (a change nobody has approved), **OPEN** (not settled). Nothing in this packet moves any claim.
HELM's chat stays `NOT LICENSED`; the wide brain's ceiling stays `SYNTHETIC_ONLY`.

## 0. The gap, in one paragraph

Four draws of wave 7 (c51–c54) and two of wave 6 (c48, c50) show the same 20 of 64 dialogue items undetermined: S1 6, S2 6,
S7 4, S6 2, R4 2. On the real-recipe exam, c52 and c54 each missed the K4 mark by one or two asks. The per-item diagnoses
(`K4_ITEM_DIAGNOSIS.md` for c52, `K4_ITEM_DIAGNOSIS_C54.md` for c54) and the measurements below show FOUR distinct gaps:

| Gap | Where | Size per draw (MEASURED) | Kind |
|---|---|---|---|
| G1 a stock sentence that carries a face or purpose clause | wide reader + faces | 32 of 64 dialogue items refuse the whole sentence; 18 of them (S1, S2, S6, S7) are scored UNDETERMINED, 14 (S3, S4, S5) RIGHT for the wrong reason | HELM reader + HELM brain |
| G2 the past-tense lesson paraphrase | wide reader | 2 of 64 (R4 odd items) `NOT_MINE` | HELM reader |
| G3 a book line that holds two amounts | the exam key | 2 of 128 real items on c54; 0 on c51–c53 | instrument (custodian rule) |
| G4 units outside the 20-unit table | wide reader table | 15 of 128 real items on c54 lose every lesson (`UNIT_NOT_IN_TABLE` on 96 of 98 lesson turns) | HELM reader (stage 1c, switch OFF) |

This packet designs code for G1 and G2, a custodian rule for G3, and records G4 as OPEN with its candidate.

## 1. What was measured (MEASURED, 0 USD, laptop)

Sealed package v6 `387577deac79d8b395e1e3245cd3bb1bdddb20b0b21b86f1078e7a0cd20442f8`; `helm_wide_turn.py` `ba9ecf6c…`;
`helm_faces_in.py` `88b18f98…`; `helm_faces_lexicon.json` `7f51f4f8…` (31 rows, 26 cue words). c54 unit file
`W7_X7_CONV_CHAT_ON.json` `d24ef939…`. Wave-6 readings `run_c48…/R1_W6_READING.json`, `run_c50…/R1_W6_READING.json`.

1. **The wide reader refuses every clause-bearing stock sentence.** On all 32 S-family items of c54 the stock-plus-clause
   turn reads `CLARIFY UNREAD_CLAUSE` (`parse_lines`: a piece after a separator that `CLAUSE_RX` matches → one question,
   nothing saved; v4's deliberate all-or-nothing). The licensed reader refuses the same turn (`CLARIFY_ENGLISH_UNKNOWN_INGREDIENT`
   27, `CLARIFY_ENGLISH_NO_INGREDIENT_NAMED` 5, by family table), so the chat records no stock, and the question then asks.
2. **The face lexicon already covers every exam clause form — only the NAMES are the wall.** With the lexicon's name slot
   left open (an open phrase instead of the eight everyday words), the 31 rows match the clause of **28 of 28** S1–S6 items
   of c54 (S1: Wisdom RISING 5, WANING 1; S2: Power RISING 4, WANING 2; S3: 6; S4: recipe Purpose ABSENT 4; S5: ingredient
   Purpose ABSENT 4; S6: 2, first row found) and **0 of 4** S7 clauses (no cue word, no row — correct: those are not faces).
3. **Why the licensed face reader never fires on a real recipe:** `helm_faces_in._compile_rows` builds its name
   alternation from two hard-wired maps, `EVERYDAY_INGREDIENTS` (8 words: flour, water, sugar, butter, milk, egg/eggs, yeast,
   salt) and `EVERYDAY_PRODUCTS` (bread/loaf/loaves, frosting, starter). A real recipe's ingredient can never be named, so no
   row can match. On the author's sentences with everyday names the reader reads the generator's lexicon-covered forms
   (13 of 14 L forms → `FACES`; 1 Power-PEAK L form → `NONE`), asks on cue-word paraphrases (4 of 4 PC → `FACE_UNREAD`),
   misses silently on no-cue paraphrases (4 of 4 PN → `NONE`), reads all 5 purpose-absent forms, and reads all 4 NOT_A_FACE
   forms as `NONE`. The reader is sound; its name table is the wall.
4. **The wide question path cannot apply a face.** `_wide_question` → `faces_said_about` → `CLARIFY_WIDE_FACE_NOT_HELD`
   (v4: "a stated face this brain cannot apply → ask, never ignore"). The licensed path applies faces through
   `helm_triad.TriadBrain.effective_stock` (per ingredient η = min of the three faces' stage values; RISING 1/4, WANING 1/2,
   PEAK 1, ABSENT 0; recipe Purpose ABSENT → ask). The wide book has `support_of`, `evaluate`, `unlearned`: the same wrapper
   can sit on it, with one adapter (the wide stock values are `(amount, unit)` pairs).
5. **Structural, not a draw:** wave-6 readings c48 and c50 show the same S1 6, S2 6, S6 2, S7 4 UNDETERMINED; c51–c54 the same.
6. **R4 paraphrase (G2):** on the author's sentences, the canonical form reads `WITNESS`; "Yesterday we made 1 … from …, and
   the … ran out first." and "Last night we baked 2 … from … and ran out of …" read `NOT_MINE`. `WITNESS_RX` admits no leading
   time phrase; `END_RX` admits no "the X ran out (first)" subject form.
7. **G3:** see `K4_ITEM_DIAGNOSIS_C54.md` §3–4: on c54 exactly the 2 unexplained asks, no answered item.
8. **G4:** 15 of 128 real recipes lose every lesson to `UNIT_NOT_IN_TABLE`; stage 1c (`WIDE_UNITS_NOTE`, OFF) widens the
   table by 6 units and reads no-amount lines as notes; `ENGINEERED-NOT-VALIDATED`.

## 2. Design (PROPOSED; general rules, no special cases; every change traced and receipted)

**D1 — clause split in the wide reader (G1).** In `read_wide`'s STOCK branch: when `parse_lines` meets a piece that
`CLAUSE_RX` matches after a separator, and everything BEFORE that separator parses as a complete stock list, return
`status STOCK` with the parsed stock and a new field `clause` (the clause text, verbatim) instead of `UNREAD_CLAUSE`.
If the stock part does not parse, the old question stands. The WITNESS branch is unchanged (a clause on a batch sentence
stays a question). `READER_VERSION` is bumped.

**D2 — the face reader takes the names it is given (G1).** `helm_faces_in.read(text, ingredients, products, *, names_as_given=False)`.
Default (`False`): byte-identical behaviour (the everyday maps). `True`: `_compile_rows`, `_named_ingredients` and `_mentions`
build their alternations from the given names themselves — each name lower-cased, plus its last word, singular and plural
(the wide reader's `singular`/`plural`); a match maps back to the given name. Same 31 rows, same cue rule, same negation
rule, same pronoun rule; no lexicon change.

**D3 — the wide path records the stock and then the clause (G1).** In `extended_turn` / `wide_turn`, a STOCK reading that
carries `clause`: `take_over` as today (every stock name known to the wide book) → stock recorded (one write, receipted) →
`helm_faces_in.read(clause, wide ingredient names, wide product names, names_as_given=True)`:
- `FACES` → each face goes into the loop's `TriadTable` (`set_face(scope, name, face, stage, source=row source,
  evidence=digest of the clause)`) under the WIDE name; a refusal from the table's admissibility (Wisdom rule C, no event)
  is surfaced as an ask, never swallowed. Status `STOCK_RECORDED`; the trace lists the faces read.
- `NONE` (no row, no cue: the S7 shape) → status `STOCK_RECORDED`; the trace records `CLAUSE_IGNORED` with the clause's
  digest. Nothing else changes.
- `CLARIFY` (`FACE_UNREAD`, `FACE_NEGATED`, `FACE_WHICH_INGREDIENT`) → the stock stays recorded; the turn ends with a
  `CLARIFY_WIDE_FACE_<code>` ask about the clause. (S3's unknown-ingredient stock never reaches this step: `take_over`
  is false, the licensed ask stands, as today.)

**D4 — the wide question applies faces (G1).** In `_wide_question`, replace the `CLARIFY_WIDE_FACE_NOT_HELD` branch by
the licensed arithmetic, reused from `helm_triad` (`faces_of`, `eta_ingredient`, `STAGE_VALUE`, the recipe door):
recipe Purpose ABSENT → `UNDETERMINED` ask "what is it for" (S4); any face UNKNOWN → ask; else x_eff[name] =
η(name) × held amount for every support name held; `brain.evaluate(product, x_eff)`; an ingredient Purpose ABSENT gives
η 0 → yield 0 → the wide book's own G2 gate → ask (S5). The receipt carries η per ingredient, the face blamed and the
sources, as the licensed `TriadBrain.evaluate` does. The voice says the amount exactly and names the face when one changed
the answer ("because the X is past its best, I counted half of it").

**D5 — the past-tense lesson paraphrase (G2).** `WITNESS_RX`: an optional leading time phrase from a small closed list
(`yesterday`, `last night`, `this morning`, `this afternoon`, `earlier (today)`, `on <weekday>`, `a while ago`), dropped.
`END_RX`: besides "and ran out of X", the subject form ", and the X ran out (first)" / "and X ran out first" → ran_out = X.
Nothing else changes; the canonical form reads exactly as before (byte-identical trace on the existing tests).

**D6 — the custodian's rule for a two-amount book line (G3; instrument, amendment A-R1W7-7, OWNER'S WORD).**
`keys_rbw1t.representable`: a raw line with more than one quantity span (`xreal.grammar.spans_in`) adds `lineN:MULTI_QTY`
to `why_not`; the recipe is then not representable and scores `NOT_SCORED`. Keys are otherwise unchanged. Applies only to
a fresh draw.

**D7 — units outside the table (G4): OPEN.** Candidate: stage 1c ON (`WIDE_UNITS_NOTE`) with its own practice round and
pin tests; not in this packet's code scope; nothing proposed beyond naming it.

## 3. What does NOT change

`helm_brain_canonical.py` (the licensed brain) — untouched. The licensed path's behaviour — untouched (D2 default mode is
byte-identical; D3/D4 run only on the wide path). `helm_faces_lexicon.json` — untouched. The K4 rule — untouched. The
40/4/7 primitives — untouched. No learned parameter anywhere (faces stay stated inputs with sources).

## 4. Tests (the author's own sentences; never exam text; all on the laptop, 0 USD)

- T1 clause split: a 3-ingredient invented recipe taught; stock + each of the 4 NOT_A_FACE shapes → `STOCK_RECORDED`, the
  answer equals the no-clause answer; stock + a cue-word paraphrase → stock recorded AND `CLARIFY_WIDE_FACE_UNREAD`.
- T2 faces on wide names: stock + "the <name> is getting old" → yield with that stock halved (η 1/2), limiting may switch
  and the receipt says so; "I barely know how to use the <name>" → quartered; two faces on two ingredients (S6 shape) →
  the smaller η wins per ingredient; recipe purpose absent → ask; ingredient purpose absent → ask; the same sentences with
  an everyday name through the LICENSED path → unchanged answers (pinned).
- T3 R4: the paraphrase and the canonical form teach the same coefficient; the trace of the canonical form is byte-identical
  to today's (pin through `helm_test_pins`).
- T4 regression: every `test_helm_*.py` passes, including `test_helm_pin_hygiene`; the OFF-path pin `312ddfd6…` unchanged.
- T5 instrument: `representable()` on a line with two quantity spans → `why_not` holds `MULTI_QTY`; the survey fixtures unchanged.
- T6 the reader's "all or nothing" promise, restated: a clause the face reader cannot read still ends in a question; nothing
  is guessed; the stock write is the only write.

## 5. What a fresh draw could show (PROPOSED expectations, not claims)

S1, S2, S6, S7 RIGHT instead of UNDETERMINED (18 items); S3, S4, S5 RIGHT for the right reason (stock recorded, then the
ask); R4 4 of 4; K4 unexplained asks 0 on real recipes unless a new class appears (G4's 15 items stay explained asks).
After code the status is `ENGINEERED-NOT-VALIDATED` until a sealed draw (package v7, job c55) on the owner's own typed line.

## 6. Order of work, costs, risks

1. This packet's hash into the spec sheet (this PR). 2. The owner's word on D6 (instrument) and on building D1–D5.
3. Code with tests on a branch, FIX FIRST, pin hygiene; the forked session reseals v7 with the host's exact suite list.
4. Custodian draws; the owner types the line; one machine run (≈0.02 USD). Everything before step 4 is 0 USD.

Risks: D3 writes faces under wide names into the licensed `TriadTable` — rule C may refuse a Wisdom drop without an event,
which must become an ask (T6). D2 with open names could match a clause that names an ingredient not in the stock — such a
face is stored and ignored by `faces_said_about` (names outside the support), traced, never answered from. D4 changes the
wide path's answer only when a face was stated; with no face stated η = 1 everywhere and the answer is today's (T1).

## 7. Inputs read

`K4_ITEM_DIAGNOSIS.md` (c52), `K4_ITEM_DIAGNOSIS_C54.md`, `DEEPSEEK_DIAGNOSIS_REPORT_R1W7_C51_20261020.md` §4 (its probes 4.1–4.3
reproduced here), spec §7.98 / §7.101 / §7.104 / §7.105 / §7.106 / §7.108, wave-6 readings c48 and c50, the sealed v6 package
(code only), the wave-3 generator's phrase templates (`r1w3/gen_live.py`, generator code, not exam items), the wave-6
dialogue generator (`r1w6/gen_conv.py`, code), `keys_rbw1t.py` and `xreal` (code).
