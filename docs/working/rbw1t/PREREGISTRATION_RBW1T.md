# PREREGISTRATION — RB-W1T, the sealed test of the wide recipe brain (RB-W1)

Written 2026-10-19 (Pacific) by the RB-W1T builder session (Claude), BEFORE any package code. Order (coordinator's
build order, relaying the owner's RB-W1 line of work): build and seal the test of RB-W1 (PR #380, merged as `015d340d`
on `claude/project-thread-pmbzd6`: `helm_brain_wide.py`, `helm_wide_turn.py`, `test_helm_brain_wide.py`, switch
`WIDE_BRAIN` default OFF; spec sheet §7.83). BUILD AND SEAL ONLY: no AWS run and no spend. The run waits for the
owner's approval (pre-approval line `WIDE TEST at 1 USD`, section 13) bound to the final package hash, and an operator launch.

**Claude is not the research governor.** This page picks no verdict. Every word after a run comes only from the
frozen reader program `rbw1t/merge_rbw1t.py` reading the raw host results, the custodian's keys, the frozen thresholds
and the hard gates. A hard gate that fails is a FAILURE, never "PASS with caveats". The thresholds below are the
builder's PROPOSED values; the owner's sign line accepts or rejects the whole package.

**Status of this packet: to be SEALED, NOT LAUNCHED.** No AWS, no spend, no exam seed exists until the owner signs.

## 0. Plain words

RB-W1 is a second, wider recipe brain built beside HELM's licensed one. It learns a recipe the same way the licensed
brain does: you tell it about one batch you really made, and which ingredient ran out first; from that it learns
exactly how much of that one ingredient one unit of the product needs. It never learns from a written recipe. It was
only unit-tested. This test asks four questions on real cookbook recipes that other people wrote:

1. **Does it learn?** Given one witnessed batch per ingredient (that ingredient at the amount the book lists, every
   other ingredient at twice its amount, so exactly that one runs out), does it learn every amount exactly?
2. **Does it answer right, and only then?** Given fresh amounts on hand, does it say how much can be made and what runs
   out first, exactly; and does it ask (never guess) when it has not learned enough?
3. **Is the learning what does the work?** The same brain with learning switched off must fall to the level of a
   program that always asks.
4. **Does it harm anything?** With the switch OFF, HELM must behave byte for byte as before on the English-64 and
   Faces-64 exams; with the switch ON, it may lose at most 2 items on each of them.

Words. **Key** = the right answer worked out from the source text by a fixed written rule, never by running HELM.
**UNDETERMINED** (the third key value) = the rule cannot settle the answer from the source; such items are not scored.
**RIGHT** = HELM did what the key says. **WRONG** = HELM committed to something the key contradicts. **ASKS** = HELM
asked instead of answering; on an answerable item this is honest but not helpful, never WRONG.

## 1. What is tested

- **The build:** HELM's live files at commit `015d340d` (the RB-W1 merge), cut with `git show` (never the working tree)
  into the package as `helm_now/`, the same file set wave 3 cut (wave 3's `cut_sources.py` list) plus
  `helm_brain_wide.py`, `helm_wide_turn.py`, `test_helm_brain_wide.py`, `test_helm_english_in_stock_frame.py`.
- **The base:** the same file set at `d4488f2a` (the parent of the RB-W1 merge; the only difference is RB-W1's six
  files) as `helm_base/`. Used only for the switch-OFF identity check.
- **The licensed brain:** the wave-1 v3 package `HELM_R1_W1_20261015` (zip `31f97d67...`, freeze `8c55c413...`),
  shipped beside the package, unchanged.
- **The harness:** wave 3's live harness (`r1w3.live_w3`: `make_loop_class`, `build_loop`, `run_item`, `import_helm`,
  `is_asking`, the agentic stub) and wave 3b's English-64 / Faces-64 tools (`r1w3b.live64.check_items`,
  `r1w3b.switches_w3b.settings`, `r1w3b.common_w3b.w3_import`), imported from their SEALED packages after their
  freeze checks (wave 3 v3 `152bca2a...` / `bd06f324...`, wave 3b `a4f82556...` / `a6d9dbc7...`), never edited.

## 2. The exam frame (public, pinned)

- **Recipes:** X-REAL's pinned recipe frames `FRAME_R_PG.jsonl` (sha256 `c983e065bc1783ea9a4807612edafe8168ebb8c09b56a264dfea5ca53cb3aa5e`)
  and `FRAME_R_WB.jsonl` (`6a0d7cc12d0133991bf44c666ecae80ff1239760d0fcbd9aad62b11842563ddc`), 13,686 recipes, built by
  X-REAL's frozen `frames.py` from the pinned Project Gutenberg cookery eBooks and the English Wikibooks Cookbook dump
  20261001 (`FRAMES_PINNED.json` and `SOURCES_PINNED.json` of the sealed X-REAL package `a9b4c954...`; X-REAL's reader
  row I1 recomputed them from the sources at c42). Licences as X-REAL recorded (PG public domain in the USA; Wikibooks
  CC BY-SA 4.0 with page id + revision id + dump date). The source files never go to AWS.
- **Exam frame** = every frame recipe with **2 to 10 ingredient lines, every line parsed** by X-REAL's frozen line
  grammar (`all_parsed`), minus the exclusions:
  - **X-REAL used:** the 64 R-ASIS + 64 R-REBOUND recipes of X-REAL (c42), by id (the 128 ids read from c42's host
    records, prefix `RA:`/`RB:` removed; pinned as `EXCLUDE_XREAL_USED.json`);
  - **builder practice:** every recipe of this builder's published practice draws (section 13), by id;
  - **same text:** any recipe whose normalized line list (lower case, runs of non-word characters except `/` -> one
    space, lines sorted) equals that of an excluded recipe.
  Measured on the public frame before exclusions: 7,595 recipes in the 2-10, all-parsed set.
- **Strata.** Ingredient count: `C23` (2-3 lines), `C46` (4-6), `C710` (7-10). Quantity form, from each line's parsed
  QTY text (frozen rule): a line is **MIXED** if its QTY is `n a/b`, `n` followed by a vulgar fraction, or a decimal
  above 1 that is not whole; **FRACTION** if its QTY is `a/b`, a vulgar fraction alone, or a decimal below 1; else
  **INTEGER** (digits, number words, "a"/"an", whole decimals). A recipe is MIXED if any line is MIXED, else FRACTION
  if any line is FRACTION, else INTEGER. Thirds are allowed in every stratum. Frame counts before exclusions:

  | | INTEGER | FRACTION | MIXED |
  |---|---|---|---|
  | C23 | 1,120 | 724 (81 with a third) | 189 (14) |
  | C46 | 923 | 1,986 (273) | 409 (72) |
  | C710 | 258 | 1,420 (224) | 566 (158) |

- **Quotas (128):** 14 per cell, plus 1 more in each of the two largest cells (C46 FRACTION, C710 FRACTION): 15. A cell
  with fewer free recipes than its quota gives all of them and the shortfall is recorded (no padding from other cells).

## 3. The draw (custodian, blind to the builder)

- rank(recipe) = sha256(`"RBW1T:" + cell + ":" + str(seed) + ":" + frame id`) as hex; the lowest ranks in each cell
  are taken, in rank order, skipping a recipe whose normalized line list equals one already taken (`DUPLICATE_TEXT`,
  recorded). Item id = `"RW:" + frame id`.
- **Fresh amounts (the pantry).** A frozen set of ten multipliers `M = 1/3, 1/2, 2/3, 3/4, 4/3, 3/2, 5/2, 3, 7/2, 4`
  (none equal to 1 or 2, so no pantry amount repeats a lesson amount). For each item the ten are put in the order of
  sha256(`"RBW1T:M:" + str(seed) + ":" + frame id + ":" + m`) and line i takes the i-th. The multipliers of one recipe
  are therefore all different, so exactly one ingredient runs out first.

## 4. The mapping (source item -> the turns HELM is given)

For recipe A with parsed lines `raw_1..raw_k` (each stripped), values `q_1..q_k`, and title noun `N` (X-REAL's: the
last letter-word of the title, parenthetical parts removed, lower case):

1. **k lesson turns** (X-REAL v2 scheme, A-XR-15, its own code `mapping.lesson_lines` / `surplus_line`):
   `"We made 1 {N} from {L_j} and ran out of {name_j}."` where `L_j` = the k lines joined `", "` with `" and "` before
   the last, line j as written and every other line with its leading quantity replaced by 2 x its value (X-REAL's
   `frac_text`, e.g. `3/2`). `name_j` = line j's **name phrase**: its MODIFIERS and HEAD as the frozen grammar reads them,
   lower case, joined by single spaces (deviation D-W-1).
2. **one stock turn** `"We have {LP}."` where `LP` = the k lines joined the same way, each with its leading quantity
   replaced by `m_i x q_i` (same renderer).
3. **one question** `"How much {N} can we make?"` (X-REAL's P2).

The only numbers not copied from the source are the doubled lesson amounts and the pantry amounts; both are exact
products of a source number and a frozen factor, re-derived by the receiver's checker. Every arm gets the same turns.

## 5. Keys (custodian computes them from source spans only; the key code imports nothing of HELM's)

- **Answer key** = X-REAL's frozen K-R (`xreal.keys.key_r`, vendored byte for byte) on (A's lines, the pantry lines):
  `ANSWER` with `y = min_i(x_i / q_i)` as an exact fraction and the limiting HEAD; `UNDETERMINED` if a line is
  unparsed, two lines share a HEAD, or an amount is zero; `ASK` if a pantry line is missing or its unit differs (cannot
  happen by construction; kept for safety). A key limiting HEAD is **scored** only if its normalized form
  (`head_norm`: lower case, `ies`->`y`, `oes`->`o`, `ches/shes/xes/sses`->drop `es`, final `s` dropped unless `ss/us/is`;
  frozen) is unique among the recipe's lines; else the value alone is scored (`limiting_scored: false`).
- **Lesson keys** = for each line j: `q_j` (exact) and `head_norm(HEAD_j)`.
- **Representable** (the denominator of mark K1) = the recipe-shape survey's own rule at its "k = 10, top-20 units,
  exact fractions" point, computed with the survey's line classifier (`recipe_shape_survey_v1/scripts/survey.py`
  `classify_line`, vendored byte for byte, sha256 `89e4a6be...`): at most 10 lines, every line's quantity form is
  integer, decimal, simple fraction or mixed, and every line's unit is "count (no unit)" or one of the survey's top 20
  units (cup, teaspoon, tablespoon, pound, pint, quart, ounce, gram, can, clove, slice, gill, milliliter, pinch,
  package, bunch, square, saltspoon, teacup, kilogram). Representable is about the quantities only; it says nothing
  about whether HELM's reader can read the words around them.

## 6. Arms

| Arm | What | Where |
|---|---|---|
| `LICENSED` | HELM at `015d340d`, switch OFF, wave 3's FULL settings (English in, voice, triad, cube store), the licensed wave-1 brain. The yardstick. | main exam |
| `WIDE` | HELM at `015d340d`, switch ON (`HELMEndToEndLoop(wide_brain=True)` with a fresh `WideRecipeBook` per item), same harness class, no triad wrapper (the triad wraps only the licensed brain) | main exam, no-harm |
| `WIDE_REPLAY` | WIDE run again | main exam (hard gate) |
| `WIDE_NO_LEARNING` | WIDE with learning disabled: a harness subclass whose `witness` writes a refusal record (`REFUSED_LEARNING_DISABLED_CONTROL`) and changes nothing; its learned digest must stay the empty brain's after every lesson | main exam (control) |
| `ALWAYS_ASK` | no HELM: every turn asks, nothing is written, nothing is answered (the mechanism-free baseline) | main exam |
| `OFF_NOW` / `OFF_NOW_REPLAY` | wave 3b's FULL arm with HELM at `015d340d`, switch OFF | no-harm |
| `OFF_BASE` | the same with HELM at `d4488f2a` | no-harm |

A fresh loop and a fresh brain per item in every arm. Items are independent.

## 7. The no-harm part (NH)

Four files, run by wave 3's `run_item` exactly as wave 3b runs English-64 / Faces-64:
`E64_PRACTICE_W5.json` (`43ddd755...`) and `F64_PRACTICE_W5.json` (`358df496...`), wave 5's published practice
fixtures (copied into the package); `ENGLISH64_X5.json` (`1eb17c91...`) and `FACES64_X5.json` (`2c7cac21...`), the
licensed brain's spent live exams (scored at c40, reproduced at c42), shipped in the existing carrier
`X5SPENT_CARRIER_V1.zip` (`653372b4...`). The builder never opens the two spent files; they run only on the host.
For the WIDE arm the harness swaps wave 3's `build_loop` for a wide one for the duration of the run and restores it
(a test proves the restore); wave 3's file is not edited.

## 8. Scoring

**Main exam, the question turn** (key ANSWER): the arm answered (status `SUCCESS_EVALUATED`) with value = y exactly
and, when the limiting HEAD is scored, a limiting name whose last word has `head_norm` = the key's -> **RIGHT**;
answered otherwise -> **WRONG**; any other status -> **ASKS** (UNDETERMINED score, never WRONG). Key UNDETERMINED ->
not scored (answers on such items are counted as "commitments on unsettled items" and reported).

**Main exam, lessons (WIDE arms):** lesson j is **LEARNED** if it was admitted (`WITNESS_ADMITTED`), the admitted
ingredient name's last word has `head_norm` = `head_norm(HEAD_j)`, and the brain's final coefficient for that
ingredient, said in the unit it was taught in, equals `q_j` exactly; **WRONG** if admitted otherwise; else
**NOT_LEARNED**. A recipe is **FULLY LEARNED** if every lesson is LEARNED.

**Unexplained ask:** an item whose key is ANSWER, every lesson LEARNED, the stock turn recorded (`STOCK_RECORDED`),
and the question not answered.

**NH:** wave 3's `score_turn` verbatim, as wave 3b. An item is **lost** by WIDE if it is RIGHT in `OFF_NOW` and not
RIGHT in `WIDE`. Identity = every record of `OFF_NOW` equals `OFF_BASE`'s as canonical JSON bytes (sorted keys).

## 9. Instrument rows and hard gates

**Instrument rows** (any false -> `INSTRUMENT_ERROR`): I1 data identity (package freeze and members; the two frames by
sha256; the draw, the mapping and the keys recomputed by the reader from the pinned frames and the seed equal the
sealed inputs and keys; the NH files by sha256); I6 completeness (every unit exit 0 and every arm holds every item;
carried test suites OK on the host); I7 the reading is run from an extracted copy of the sealed zip; I9 governance (the
approval record holds the owner's line verbatim and binds this zip and freeze); I10 seed rule (seed text = owner line +
":" + zip sha256; band; used table; `overlap_check: PASS`); I14 vacuity (at least 16 items that are both representable
and ANSWER-keyed; else the reading is `INSTRUMENT_ERROR` with reason `VACUOUS`).

**Hard gates** (any false -> `FAILURE`): HR replay (WIDE = WIDE_REPLAY and OFF_NOW = OFF_NOW_REPLAY, record for
record); HC control (WIDE_NO_LEARNING: learned digest equal to the empty brain's after every lesson of every item,
0 WRONG, RIGHT equal to ALWAYS_ASK's); HP parameter audit (after every WIDE item, the only numbers in the brain's
learned state are its coefficients, one per (recipe, ingredient) on a support at most; the 9 unit factors equal their
pinned exact values; the brain object holds only its four named attributes); HSW switch hygiene (in every OFF unit the
modules `helm_brain_wide` and `helm_wide_turn` are never imported); HK key-blind (no key file on the host); HN no
network (each unit installs a socket guard; 0 attempts); HS sandbox (the wave-1 brain folder hashes the same at host
start and end); HB baselines on the same inputs (input sha256 equal in every arm).

## 10. Marks (PROPOSED; a miss decides the word, never a gate)

| Mark | Rule | Why this number |
|---|---|---|
| K1 LEARNS | FULLY LEARNED on at least 90% (ceil) of the items that are representable and ANSWER-keyed | X-REAL's practice (I11 v2): with the licensed brain on lines its reader could read, 15 of 16 recipes (93.75%) were fully learned and 30 of 30 amounts exact; the one miss was "1/3 pint", which exact fractions remove. The survey puts 69.38% of real recipes in the representable set. 90% leaves one recipe in ten for reader misses. |
| K3 SAFE | 0 WRONG question answers and 0 WRONG lessons in WIDE | the arithmetic is exact; any wrong answer means a wrong binding of a name or an amount, which this brain must never commit. X-REAL's FULL had 0 wrong recipe answers. |
| K4 HONEST | 0 unexplained asks in WIDE | "asks only where UNDETERMINED or unlearned" |
| NH-OFF | OFF_NOW = OFF_BASE byte for byte on all four NH files | RB-W1's own claim (OFF changes nothing) |
| NH-ON | WIDE loses at most 2 items on each of the four NH files | the waves' no-harm margin (waves 4 and 5: at most 2 of 64) |

Reported, never marks: RIGHT / WRONG / ASKS for every arm; LICENSED vs WIDE; per stratum; answer rate on representable
items; the commitments on unsettled items; plain-English replies (`helm_voice.cas_tokens == []`); OFF_NOW vs c40's
records on the I3 fields (id, score, status, value, limiting, writes, reply) when the c40 files are supplied.

## 11. Verdict and status word (frozen order)

Verdict: `INSTRUMENT_ERROR` if any instrument row is false; else `FAILURE` if any hard gate is false; else `PASS`.
Status word, the first that holds in this frozen order:
1. `WIDE_BRAIN_EARNED_KEEP` — verdict PASS and K1, K3, K4, NH-OFF, NH-ON all met.
2. `WIDE_BRAIN_HARMED` — verdict PASS and K3, NH-OFF or NH-ON missed.
3. `WIDE_LEARNING_DID_NOT_EARN_KEEP` — verdict PASS and K1 or K4 missed.
4. `INCONCLUSIVE` — verdict not PASS.

## 12. What a pass licenses, and what it never licenses

- `WIDE_BRAIN_EARNED_KEEP`: the wide brain becomes **HELM's canonical-brain candidate** with ceiling
  `NAMED_CORPORA_ONLY` (the X-REAL corpus list), status `VALIDATED` for this sentence only: "On 128 real recipes drawn
  blind from the named corpora, taught by one witnessed run-out batch per ingredient, the wide brain learned every
  amount exactly on at least 90% of the representable recipes, gave 0 wrong answers, asked only where the source did
  not settle the answer or a lesson was not learned, and with its switch OFF left HELM byte-identical." It stays a
  candidate pending a wave with the switches (a pair-word wave against the other parts). The licensed brain keeps its
  license and stays canonical until then.
- `WIDE_BRAIN_HARMED` / `WIDE_LEARNING_DID_NOT_EARN_KEEP`: no move; the misses are recorded as negatives; the wide brain
  stays `ENGINEERED-NOT-VALIDATED`.
- **Never, by this test:** real kitchens or real cooks; typed English (every turn is a fixed template around source
  text, never typed by a person); anything about the transformer (CTT or any other); coverage of real cooking beyond the
  measured counts; that the wide brain is better than the licensed brain outside these items; the 28 drive cells or 22
  pathways; statistical claims (one run).

## 13. Custody (the builder never sees the exam draw, the keys or the multipliers)

- **Approval and seed source (coordinator instruction 2026-10-19, before any code).** The owner pre-approved this test
  with the verbatim line `WIDE TEST at 1 USD` (recorded in `Documents\Codex\2026-10-18\OWNER_APPROVALS_20261018.md`,
  "Owner pre-approval (2026-10-19, verbatim)"; the coordinator's executable mapping there: cap 1.00 USD, one attempt +
  one plumbing retry, on this package). So no sign request is written: `APPROVAL_RECORD_RBW1T.md` (+ `.json`) quotes
  the line verbatim, records its UTF-8 byte length and sha256 (computed by program) and the final zip and freeze
  sha256. **Seed source:** H = sha256 of the UTF-8 bytes of (`WIDE TEST at 1 USD` + ":" + the full sha256 of the final
  sealed zip, 64 lower-case hex), no trailing newline. No seed can be known before the zip bytes are final. (The sign
  line `APPROVE RB-W1T: wide brain test, sealed package <8 hex>, ...` named in the build order is NOT used.)
- **Band** RW 1,950,000,001-1,951,000,000 (one band, 1,000,000 wide): above every band used or reserved so far — X4
  1,858-1,863 M, X5 1,878-1,881 M, X-REAL 1,898,000,001-1,905,000,000, CTT CW/CD/CM 1,920-1,925 M and LW-S/LW-D
  1,926-1,929 M (from RTR-1's preregistration and A-RTR-1; CTT's custody folder is not opened), RTR-1's reservation RS
  1,940,000,001-1,941,000,000. k = int(H[0:16], 16); first slot = k mod 1,000,000; seed = 1,950,000,001 + slot.
  **Used table** = those ranges as whole ranges, plus 1-1,881,000,000 as one whole range (every X0-X5 derivation lies
  below it). Gap rule 1,000,000 on each side; step rule s <- (s + 1) mod 1,000,000 inside the band; a band with no free
  slot = STOP (`RBW1T_BLOCKED_SEED.json`, never another band). Every number below 2^31 - 1.
  `SEED_DERIVATION_RBW1T.json` must say `overlap_check: PASS` before anything is drawn.
- **Practice (builder only, published):** practice seed text `RBW1T-PRACTICE-20261019-builder-published` stands in for
  the seed (the same rank formula with this text in place of `str(seed)`); the practice draw is published in the
  package (`practice/`) and every recipe in it is excluded from the exam frame by id and by text.
- The custodian is a separate session that runs only the sealed package's `rbw1t/custody_rbw1t.py` on the laptop,
  writes the exam into `rbw1t_custody/exam/` (which the builder never opens), and hands over hashes only. The host
  carrier holds the inputs and the pins only; the keys stay on the laptop.

## 14. Honest predictions (written before any code; not read by any program)

- **Learning (K1):** the wide reader is strict ("all or nothing" per sentence). Old-book lines carry notes after commas
  that are not in its note list ("chopped fine", "cut in pieces"), parentheses with second numbers ("1 can (16 oz)"),
  glued metric units ("250g"), and units outside its table (dessertspoonful, wineglass, stick). Any one of those in any
  line makes every lesson of that recipe a question, so a recipe with 7-10 lines is fully learned only if all its lines
  are clean. I expect FULLY LEARNED on roughly 40-70% of representable items: **K1 missed (about 0.75)**.
- **Safety (K3):** when it answers, the arithmetic is exact; a wrong answer needs a silent mis-binding. I expect 0 WRONG
  (about 0.8).
- **Honest asking (K4):** 0 unexplained asks (about 0.85).
- **NH-OFF:** byte-identical (about 0.9); the only risk is a field that carries a module or version string.
- **NH-ON:** with the switch ON every turn goes to the wide reader, which has no store read ("What do we have on
  hand?"), no absence ("we're out of milk"), no faces, and does not read units such as "sticks of butter". English-64
  and Faces-64 are built from exactly those families, so I expect WIDE to lose far more than 2 items on each file:
  **NH-ON missed (about 0.9)**.
- **Word:** `WIDE_BRAIN_HARMED` about 0.8; `WIDE_LEARNING_DID_NOT_EARN_KEEP` about 0.08; `WIDE_BRAIN_EARNED_KEEP` about
  0.02; `INCONCLUSIVE` about 0.1. LICENSED: about 0 RIGHT and 0 WRONG on the main exam (it knows 8 words and 4 shapes);
  ALWAYS_ASK and WIDE_NO_LEARNING: 0 RIGHT, 0 WRONG.

## 15. Run limits (PROPOSED)

One small CPU instance (no GPU, no torch), one scored attempt + one plumbing retry (only if no scored unit started; same
zip), cap **1.00 USD** for both, cleanup proof (instance and volume terminated, shared prefix purged, independent check
within an hour, a direct read-only look). Expected about 0.03 USD.

## 16. Deviations and readings (OUR_CONVENTION, stated before any code)

- **D-W-1 ran-out name.** X-REAL v2 says "ran out of {HEAD}". The wide brain names an ingredient by its whole name phrase
  ("brown sugar"); with the HEAD alone ("sugar") the wide reader would refuse every lesson whose line has a modifier
  ("ran out of something not in the batch"), which would test the template, not the brain. The ran-out name is
  therefore the line's name phrase (MODIFIERS + HEAD as the frozen grammar reads them). It comes from the source line;
  the same turn goes to every arm. The HEAD-only form is measured on practice and reported as a sensitivity.
- **D-W-2 "the licensed brain's own exams"** is read as the licensed brain's live-loop exams, the spent X5 English-64
  and Faces-64 (c40), because the switch lives in the live loop. The wave-1 brain exams (GB/TB worlds) drive the
  wave-1 brain directly and never pass through the loop; there, OFF identity holds by construction
  (`helm_brain_canonical.py` and the wave-1 package are byte-identical in both cuts; checked), and an ON comparison is
  not run (the wide brain has no adapter for cell-index worlds; recorded as not done).
- **D-W-3 X-REAL's pair recipes.** X-REAL's 64 R-REBOUND items also used a pantry recipe each; their ids are only in
  X-REAL's custody folder, which this builder may not open, so they are not excluded (expected overlap about 1 recipe).
- **D-W-4 the wide arms have no triad wrapper** (`TriadBrain` wraps only the licensed brain): a face statement in
  Faces-64 is read but not held under WIDE. This is part of what NH-ON measures.

## 17. Builder amendments BEFORE the seal (made on the published practice draw only; no exam seed exists)

Precode copy: `PREREGISTRATION_RBW1T.precode.md`, sha256 `c0902a4fb83fd77670085938414ed160b71fd119ba5e8a77e203aab5b45ad424`
(2026-10-20T01:19:14Z), written before any package code. Each amendment below was made after running the code on the
builder's published practice draw (seed text `RBW1T-PRACTICE-20261019-builder-published`, 128 recipes, in the package
under `practice/`, excluded from the exam frame by id and text). No mark, threshold, arm, status word or hard gate was
changed.

- **A-W-1 Name matching through the brain's own lesson records (supersedes the `head_norm` matching of sections 5
  and 8).** On practice, the frozen grammar's HEAD is sometimes not the ingredient word: "1 quart boiling water poured
  upon the flax-seed." has HEAD `upon` (the name phrase stops at the STOP word "the"). Matching the brain's names to
  HEADs would score a right answer as WRONG. Rule now: the key carries the **line index** of the limiting HEAD
  (`limiting_index`); a brain's ingredient name is mapped to the recipe line whose admitted lesson record names it
  (the lesson for line j told the brain "ran out of {name_j}", and the brain's own record says which ingredient it bound
  that to); a name in no lesson record falls back to the unique line whose HEAD has the same `head_norm` as the name's
  last word. **LEARNED** = lesson j admitted, its ingredient named by lesson j alone, and the brain's final coefficient
  in its taught unit equal to `q_j`; an ingredient named by two lessons makes both WRONG (a mis-binding). The limiting
  name is scored whenever the K-R limiting HEAD is unique (always, since K-R already requires distinct HEADs).
- **A-W-2 Practice-mock mode for the dry run.** `custody_rbw1t seal --practice-mock`, `check_rbw1t --practice-mock` and
  the reader's `practice_mock` input draw with the published practice seed text; the reader then sets instrument row
  `I0_not_a_practice_mock` false, so a dry run can never print a real verdict. `pool_rbw1t --dry-practice` skips the two
  spent X5 units (the builder never touches the spent files).
- **A-W-3 A crash is recorded, never hidden.** In the NH runner an item that raises is recorded with score `CRASHED`
  (it is not RIGHT, so it counts as lost if OFF_NOW had it RIGHT); in the main runner a turn that raises gets status
  `CRASHED_<type>` (asks, never an answer). None happened on practice.
- **A-W-4 HELM's own suites run on a scratch copy of `helm_now/`** (they write `sessions/*.jsonl`), so the sealed
  package folder is never written. On practice: 154 tests, OK (1 skipped) — RB-W1's 35 + the six existing suites' 119.
- **A-W-5 The commitments on unsettled items are reported** as `commitments_on_unsettled` (WIDE answered on an item
  whose key is UNDETERMINED; never scored). Practice: 2.

**Practice numbers (builder's published draw; not an exam; reported to make the predictions honest):**

| Arm | RIGHT | WRONG | ASKS | not scored | fully learned / representable answerable |
|---|---|---|---|---|---|
| WIDE (and WIDE_REPLAY, identical) | 54 | 0 | 56 | 18 | 54 / 106 (50.94%) |
| LICENSED | 0 | 0 | 110 | 18 | 0 / 106 |
| WIDE_NO_LEARNING (digest unchanged after all 660 lessons) | 0 | 0 | 110 | 18 | 0 / 106 |
| ALWAYS_ASK | 0 | 0 | 110 | 18 | 0 / 106 |

WIDE lessons: 329 LEARNED, 0 WRONG, 331 NOT_LEARNED (121 "ran out of something not in the batch": the grammar's name
phrase keeps a unit word the wide reader strips, e.g. "cupfuls sugar"; 99 no amount; 86 no name; 42 unit not in the
table; 11 same ingredient twice). 0 unexplained asks. Parameter audit OK on every item.
**D-W-1 sensitivity** (same items, "ran out of {HEAD}", X-REAL v2's form): WIDE RIGHT 15, WRONG 0, fully learned 15 of
106, 1 WRONG lesson. The name-phrase form (as preregistered) stays.
**No harm on the two practice files** (wave-5 practice English-64 / Faces-64): OFF_NOW = OFF_BASE byte for byte, 64 of
64 records each; OFF replay identical; WIDE lost **55 of 64** (E64: RIGHT 61 -> 6) and **42 of 64** (F64: RIGHT 60 ->
18); 0 crashes; the build_loop swap restored.

**Predictions after practice (builder, before any exam; not read by any program):** K1 missed (about 0.95: practice
50.94% against 90%); K3 met (about 0.85); K4 met (about 0.85); NH-OFF met on all four files (about 0.9); NH-ON missed
(about 0.97: with the switch ON, every English-64 / Faces-64 turn goes to the wide reader, which has no store read, no
absence, no faces and no stick/packet units). **Status word: `WIDE_BRAIN_HARMED` about 0.85, `INCONCLUSIVE` about 0.12,
`WIDE_LEARNING_DID_NOT_EARN_KEEP` about 0.02, `WIDE_BRAIN_EARNED_KEEP` below 0.01.** A finding for the owner before any
spend: as built, RB-W1's switch replaces the whole English path, not only the recipe brain; the no-harm mark cannot be
met without a routing change (send only recipe turns to the wide brain), which is a new build and a new seal, not a
change this builder may make.
