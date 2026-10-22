# PREREGISTRATION — HELM-R1 X-REAL, the first exam built from material outside our own generators

Written 2026-10-19 (Pacific) by the X-REAL builder session (Claude), BEFORE any package code. Implements the design
`Documents\Codex\2026-10-19\x_real_design_v1\` (SOURCES.md, DESIGN_X_REAL.md, TEST_PLAN_X_REAL.md, OPEN_QUESTIONS.md;
owner picks Q1-Q8 = as proposed, owner word "FETCH X-REAL", `OWNER_APPROVALS_20261018.md`). Where this page and the
design disagree, this page says so in section 12 (deviations) and gives the reason.

**Claude is not the research governor.** This page picks no verdict. Every word after a run comes only from the
frozen reader program `xreal/merge_xreal.py` reading the raw results, the frozen thresholds and the hard gates.
A hard gate that fails is a FAILURE, never "PASS with caveats". Every threshold below is the designer's PROPOSED value,
carried unchanged; the owner's sign line accepts or rejects the whole package.

**Status of this packet: SEALED, NOT LAUNCHED.** No AWS, no spend, no seed exists until the owner signs.

## 0. Plain words

X-REAL asks four questions with text other people wrote:

1. **Part S (128 real sentences).** When a real everyday sentence about food reaches HELM, does HELM write only what
   the sentence says, ask when it should, and answer in plain English?
2. **Part R-ASIS (64 real recipes, HELM as it is).** How many real recipes can the licensed brain hold at all, and does
   it stay honest about the rest?
3. **Part R-REBOUND (64 real 2- and 3-ingredient recipes, renamed).** If the brain's fixed recipe shapes are renamed
   to the recipe's own ingredients, does its arithmetic (how much you can make, and what runs out first) hold on real
   amounts and real units?
4. **Part F (192 restart worlds).** After a restart, when HELM's saved files were damaged in a way real systems get
   damaged, does the Unity Eye's scan catch it, fail safe, or let a wrong answer through, and does it beat a plain
   file checksum?

Words. **Key** = the right answer, worked out from the source text by a fixed written rule, never by running HELM.
**UNDETERMINED** (the third key value) = the rule cannot settle the right answer from the source; such items are not
scored. **WRONG** = HELM committed to something the source contradicts. **RIGHT** = HELM did what the key says.
Asking when it could have answered is UNDETERMINED (honest, not helpful), never WRONG (owner pick Q2 = a).

## 1. Sources (fetched and pinned 2026-10-19, `SOURCES_PINNED.json`, inside the sealed package)

| ID | Source | State |
|---|---|---|
| A1 | Project Gutenberg English cookery eBooks: catalog `pg_catalog.csv` + 281 eBooks, one request each | PINNED (280 in the frame; eBook 1979 excluded: its header says "COPYRIGHTED Project Gutenberg eBook", licence not as SOURCES.md says) |
| A1-practice | PG eBook 10136, Mrs Beeton, *The Book of Household Management* (in the catalog frame) | PINNED, builder practice only, excluded from every exam frame |
| A2 | English Wikibooks dump 20261001, `enwikibooks-20261001-pages-articles.xml.bz2`, Wikimedia sha1 checked | PINNED (CC BY-SA 4.0; files stay internal; attribution = page id + revision id + dump date per item) |
| B1 | Tatoeba English export `eng_sentences.tsv.bz2` | PINNED (licence recorded as CC BY 2.0 FR for every sentence, see D-XR-3) |
| B2 | Google Taskmaster, commit `d92cb6af3005f1dc09c39e75e7daf4a04905e00b`, TM-1 `self-dialogs.json`, `woz-dialogs.json`, splits; TM-2 `food-ordering.json`, `restaurant-search.json` | PINNED (CC BY 4.0, read from the two READMEs) |
| B3 | USDA FoodData Central SR Legacy food list | **SKIPPED**: SOURCES.md gives no exact URL; the build order allows only exact URLs (D-XR-2) |
| ftfy | one pinned `ftfy` release (only to choose wrong-codec pairs) | **SKIPPED**: no exact URL; the three code pages SOURCES.md itself names are used (D-XR-4) |
| B1-CC0 | Tatoeba CC0 export | **SKIPPED**: no exact URL (D-XR-3) |

Downloaded files are untrusted data: never executed, read only by package code run with `python -I`, from scripts
outside the source folders. The source files never go to AWS; the host receives only the custodian's sealed exam
(inputs) carrier.

## 2. Frames, strata and partitions (frozen code: `xreal/frames.py`; counts pinned in `FRAMES_PINNED.json`)

**Personal-data filter (all sentence and turn frames).** Drop a text with: an e-mail pattern; a URL (`http`, `www.`);
an `@handle`; a run of 7 or more digits (spaces, dots and dashes between digits allowed); a street address
(a number + `Street|St|Ave|Avenue|Road|Rd|Blvd|Boulevard|Lane|Ln|Drive|Dr`); a Taskmaster turn with a segment
annotation containing `phone`, `address`, `customer`, or `.name.person`. Counts recorded.

**Food words.** B3 is skipped, so the food list is HELM's own everyday words (`helm_english_in.EVERYDAY_INGREDIENTS`
and `EVERYDAY_PRODUCTS` keys, copied and pinned by the sha256 of `helm_english_in.py`): flour, water, sugar, butter,
milk, egg, eggs, yeast, salt, bread, breads, loaf, loaves, frosting, starter, starters, meringue, meringues. Whole-word,
case-insensitive match. (Consequence, stated: Part S sentences all mention at least one of HELM's own words; they
still often mention other foods.)

**Part S frame** = (B1 English sentences) + (B2 USER turns of TM-1 dialogs whose `instruction_id` starts with
`pizza-ordering` or `coffee-ordering`, and of every TM-2 `food-ordering` and `restaurant-search` dialog), after the
personal-data filter, holding at least one food word, minus the practice partitions. Item id: `tatoeba:<id>`,
`tm1:<conversation_id>:<index>`, `tm2:<file stem>:<conversation_id>:<index>`.
**Strata** (first match wins, on the text as written, case-insensitive):
S1 QUANTITY (a digit, a vulgar fraction ½ ⅓ ¼ ⅔ ¾ ⅛, or a number word one..twelve, AND a food word);
S2 ABSENCE ("out of", "ran out", "run out", "no more", "none left", "all gone", "used up", "any left" AND a food word);
S3 QUESTION (ends with "?" after trailing spaces AND a food word); S4 OTHER (the rest). 32 per stratum; if a stratum
holds fewer, all of it and the shortfall is recorded (no padding).
**Practice partitions (never in an exam frame):** Tatoeba sentences whose id ends in 7; TM-1 dialogs listed in
`TM-1-2019/train-dev-test/dev.csv` (TM-2 has no dev split; recorded).

**Recipe frames.** A1: the 280 licensed eBooks except 10136; A2: `Cookbook:` pages (namespace 102 or title prefix
`Cookbook:`) with an Ingredients heading. One recipe = title + ingredient lines.
- *PG splitter (frozen):* text between the `*** START OF` and `*** END OF` lines; lines split at `\n` (a trailing `\r`
  is not part of the line). An **ingredient line** starts with a QTY (section 3), the QTY is not followed directly by
  `.` or `)`, the line has at most 60 characters and at most 10 words. A line holding two QTY starts separated by 3 or
  more spaces is two ingredient lines (two-column lists). A **block** = 2 or more consecutive ingredient lines. Its
  **title** = the nearest non-blank line above the block (at most 3 lines up), not an ingredient line, at most 10
  words, holding a letter. No title = no recipe. *Beeton style:* a paragraph (lines up to a blank line) starting with
  `INGREDIENTS` (any case) followed by `.`, `:` or `.—`; the text after that mark is split at `;` and `,` into lines;
  title as above, from the paragraph's first line. A piece that crosses a line break is two source sub-spans joined by
  one space.
- *Wikibooks splitter (frozen):* the wikitext of each `Cookbook:` page's latest revision; the bullet lines (`*`) under a
  heading whose text is `Ingredients` (any `=` level, any case) up to the next heading. A line's text is its **display
  text**: `[[A|B]]` -> the bytes of B; `[[NS:A]]` -> the bytes of A after the last `:`; `''`/`'''` and `{{...}}`
  templates dropped. A line holding an XML entity (`&...;`) after this is UNPARSED. Spans are byte offsets into the
  decompressed XML stream. Title = page title without `Cookbook:`.
- **Title noun N** = the last letter-word of the title, parenthetical parts removed, lower-cased.
- Item id: `pg:<eBook>@<byte offset of the title line>`; `wb:<page id>:<revision id>`.

**R-REBOUND frame** = recipes of A1+A2 with exactly 2 or 3 ingredient lines, every line parsed, all HEADs distinct, N
not equal to any HEAD. **R-ASIS frame** = all A1+A2 recipes. **Practice:** recipes of eBook 10136 only.

## 3. Ingredient-line and quantity grammar (frozen, OUR_CONVENTION, used by keys, mapping and splitter alike)

`QTY [UNIT[.]] [of] [MODIFIERS] HEAD [, trailing note | ( ... ]`
- **QTY:** integer; decimal; `a/b`; `n a/b`; a Unicode vulgar fraction ½ ⅓ ¼ ⅔ ¾ ⅛ alone or right after an integer;
  a number word one..twelve; "a"/"an" directly before a UNIT word (= 1).
- **UNIT:** the keys of HELM's `UNIT_FORMS` (copied and pinned) plus `cake`, `cakes`, `teacupful`, `teacupfuls`,
  `saltspoon`, `saltspoons`. Never converted. Two unit words are the same unit iff `UNIT_FORMS` maps them to the same
  form (the reader's own plural/alias table; the six old-book words map to themselves without the final `s`).
- **Name phrase** = the run of letter-words (letters, `'`, `-`, any script) after QTY [UNIT] [of], ending at a comma,
  a parenthesis, a digit, end of line, or a STOP word (and, or, but, for, in, on, at, to, with, from, into, the, a,
  an, left, that, which, if, as, per, each). **HEAD** = its last word, lower-cased, spelling kept. MODIFIERS = the
  words before HEAD.
- A line that does not fit is **UNPARSED**; it is never repaired.

## 4. Fixed mappings (source item -> HELM input; `xreal/mapping.py`)

Constant strings (the only added text): `P0 = "Hi again."`, `P1 = "What do we have on hand?"` (one of wave 3's six
packaged G6 store questions, chosen now), `P2 = "How much {N} can we make?"`, and the M-R frame words "We made 1",
"from", "and", "and ran out of", "We have", ",", ".". Joining spaces between sub-spans are ASCII spaces.
- **M-S:** turns = [the sentence with leading/trailing whitespace stripped, byte for byte; P1]. Empty brain.
- **M-R:** for recipe A (lines raw_1..raw_k, HEADs h_1..h_k, noun N) and its pair B: k teaching turns
  `"We made 1 {N} from {L} and ran out of {h_j}."` where L = raw_1 for k = 1, else `", ".join(raw_1..raw_{k-1}) +
  " and " + raw_k`; then the stock turn `"We have {LB}."` with LB the same join over B's lines whose HEAD is one of
  A's HEADs (in B's order); then P2 with N. **B** = the lowest-rank recipe (same part, same seed) other than A that
  shares at least one HEAD with A; no such B -> the item is skipped (reason `NO_PAIR`, recorded) and the next rank
  taken. Raw lines are the ingredient lines with surrounding whitespace removed.
- **REBIND (R-REBOUND only, OUR_CONVENTION):** k = 2 -> cells 0,1 (the Bread shape) named `h.capitalize()` for A's two
  HEADs, product 0 named `N.capitalize()`; k = 3 -> cells 4,5,6 (the Starter shape), product 2. Other cells are named
  `Unused0..Unused7` at their own index, other products `UnusedP0..UnusedP3`. The English reader's and the faces
  reader's word tables hold exactly {HEAD: Name} and {N: Name} for that item, swapped in by the harness and restored
  after the item (a test proves they are restored). The Eye's sandbox brain gets the same binding. No HELM file edited.

## 5. Keys (custodian computes from source spans only; `xreal/keys.py` imports nothing of HELM's)

### 5.1 K-S (Part S), design section 4.1, with these frozen readings
Clauses: split at `,`, `;`, ` and `, ` but `. A clause with no cue of its own that begins with a QTY span continues the
previous clause's kind (a list: "we have 2 eggs and 3 cups of milk"). Checks per clause, in this order:
1. **Question** (the sentence ends with `?`): contributes nothing.
2. **Non-stock cue** (need(s), want(s), add, use, put, mix, stir, beat, take, bring, like, love, hate, prefer, eat,
   drink, cook, bake, make, order, will, would, should, could, might, may, if, maybe, perhaps, going to, let's, can i
   get, i'd like; whole words, and `'ll` / `'d` count as will / would): contributes nothing.
3. **Change cue** (bought, got, picked up, used — not "used up" —, ate, drank, made, baked, more, extra, another, left
   over): UNDETERMINED.
4. **Possession** (have, has, 've got, there is, there are, there's, we've): a negation (not, n't, no, never, none,
   without) -> UNDETERMINED; an approximation word (about, around, roughly, approximately, nearly, almost, over, under,
   at least, at most) before a QTY -> asks; a vague quantity (some, a little, a lot, plenty, a few, several, enough)
   -> asks; each `QTY [UNIT] [of] MODIFIERS HEAD` span: HEAD one of the 8 (flour, water, sugar, butter, milk, egg/eggs,
   yeast, salt) with only neutral modifiers (`ADJECTIVES_SKIPPED`, pinned) -> FACT(name, QTY as said, UNIT as said);
   HEAD outside the 8 -> asks; a non-neutral modifier on one of the 8 -> UNDETERMINED; one of the 8 in two different
   units -> UNDETERMINED; one of the 8 named in the clause outside any span -> UNDETERMINED.
5. **Absence** ("out of", "ran out of", "no more", "none left", "all gone", "used up") + one of the 8 -> ABSENT fact;
   + another word -> asks.
6. Anything else: contributes nothing.
Sentence key: any UNDETERMINED clause -> **UNDETERMINED**; else asking mixed with FACTs -> UNDETERMINED; else only
asking -> **ASK**; else FACTs -> **FACTS(F)**; else **EMPTY**.

### 5.2 K-R (Parts R), design section 4.2 verbatim, plus: two A lines with the same HEAD -> UNDETERMINED.
Pantry = B's lines whose HEAD is one of A's HEADs. Any A line UNPARSED, or two such B lines with the same HEAD ->
UNDETERMINED; a HEAD of A without a B line -> **ASK**; a B line's unit differs from A's line unit (section 3 rule)
-> **ASK**; else **ANSWER** y = min_i(x_i / q_i) as an exact fraction, limiting = the HEAD at the minimum (REBOUND: the
bound name `HEAD.capitalize()`; ASIS: HELM's name for that HEAD if it has one, else the HEAD); a tie -> value scored,
limiting UNDETERMINED. Key numbers are exact fraction strings, never floats.

### 5.3 Second key (two-key agreement)
Key rule B (`xreal/keys_b.py`) is written by a SEPARATE agent session that is given only design sections 4.1-4.2,
SOURCES.md section 1 grammar and this section 5 text, and is told not to read any HELM code or this package's other
modules. The custodian computes both keys. Items where A and B disagree become UNDETERMINED (listed). Agreement below
90% of items -> INSTRUMENT_ERROR (row I2).

### 5.4 Part F probe key
The world's probe key is its session's own key on the undamaged session: S sessions -> READ of the FACTS' stock facts
(scored by wave 3's `read_ok`); R-REBOUND sessions -> the K-R key. A session is **F-eligible** only if that key is
determined (S: FACTS with at least one stock fact; R: ANSWER or ASK). The custodian ships the eligibility flag (not
the key) with the inputs (D-XR-9).

## 6. Arms, rivals and the restart harness

| Arm | What | Parts |
|---|---|---|
| `FULL` | wave 3b's brain in wave 4's session harness, Eye off | S, R-ASIS, R-REBOUND, F (= NO_SCAN) |
| `FULL+EYE_SCAN` | wave 4's candidate (periodic + self + owner triggers, report AND whisper) | S, R-ASIS, R-REBOUND, F (candidate) |
| `FULL+EYE_SCAN_REPLAY` | same, run again | S, R-ASIS, R-REBOUND, F (H11) |
| `-ENGLISH_IN` | reader off | S |
| `-VOICE` | old adapter text | S, R-ASIS, R-REBOUND (H8) |
| `EYE_SCAN_REPORT_ONLY` | Eye reports, no whisper | F |
| `CHECKLIST` | wave 4's after-every-write re-read, no Eye | F |
| `WATCHDOG` | no Eye; sha256 of every saved file kept outside the state; at reload a mismatch becomes whispers through wave 4's same Gate and receiver | F |
| `B-ASK` | always asks, never writes, never answers (no HELM) | S, R-ASIS, R-REBOUND |
| `B-KEYCALC` | writes every `number [unit] word` span whose word is one of the 8 (R-REBOUND: the item's bound words) as stock; learns q/1 from every teaching span; answers min(x/a) ignoring units (no HELM) | S, R-ASIS, R-REBOUND |
| `B-ECHO` | replies with the user's own sentence (no HELM; plainness reference) | S |

EYE_PAIRING (wave 5) is OFF: it acts only on its own backlog world, which X-REAL has not.

**Restart harness (Part F, `xreal/restart.py`, OUR_CONVENTION, new code, edits no HELM file).**
- **Save point** = a snapshot after a session step. Files (each HELM's own serializer, UTF-8, `\n` line ends):
  `store.json` = the loop's `_canon(CubeStore.to_dict())`; `triad_records.json`, `triad_receipts.json` =
  `TriadTable.save()`; `witness.jsonl` = one `_canon(row)` per `witness_log` row; `trace.jsonl` = one `_canon(record)`
  per trace record (all sessions' loops in order). Save point 0 = before the first step; one save point after every step.
- **Reload** (HELM's own loaders): `CubeStore.from_dict(json.loads(text))`; `TriadTable.load(records, receipts)`;
  witness rows re-taught in order through `CanonicalRecipeBrain.witness` on a fresh brain (same binding); trace lines
  `json.loads` one by one. A new loop (wave 3's `build_loop`, shared = the reloaded brain and store) starts the
  second session; its working stock, units and topic are empty (HELM's real restart behaviour: they are session
  memory). The world's trace for the Eye = [the reloaded trace as one segment, the new loop's trace].
- Then `P0`, one idle window (80 Eye ticks; the Eye scans, whispers are offered), then the probe (P1 for S sessions, P2
  for R-REBOUND sessions). Any exception during reload or a scan -> `FAILED_LOUD` (recorded with its type).

**Fault kinds (16 worlds each) + 64 clean worlds = 192; `xreal/planter_xr.py`; choices from the XF seed only.**

| Kind | Applied to the final save point's files | Eligible session |
|---|---|---|
| T1 TAIL_LOST_CONSISTENT | every file replaced by the save point at the start of the k-th last write-bearing step (k = 1 + seed mod min(3, W-1), W = write-bearing steps) — the lost tail of the trace, witness log and store together | W >= 2 |
| T2 TORN_RECORD | one file (seeded among files of 2+ bytes) cut at a seeded byte offset strictly inside it | all |
| E1 MOJIBAKE | one file holding non-ASCII bytes: its UTF-8 text decoded as windows-1252 / latin-1 / mac-roman (seeded; undecodable bytes kept as `\x` escapes is never used: cp1252 holes fall back to latin-1 for that byte) and re-encoded as UTF-8 | a state file holds non-ASCII |
| E2a BOM_ADDED | `EF BB BF` prepended to one JSON/JSONL file (seeded) | all |
| E2b CRLF_ENDINGS (benign) | one JSONL file with 1+ lines rewritten with `\r\n` | all |
| D1 DUPLICATE_LINE | one seeded line of a JSONL file with 1+ lines written twice | all |
| S1 STALE_ROLLBACK | every file replaced by the save point after the previous write-bearing step (the Eye's log and the watchdog's list stay current) | W >= 2 |
| C1 CLOCK_RESET (benign) | no file change; after reload P0 and the probe take ticks 1 and 2 (repeating earlier ticks) | all |

A **write-bearing step** = a step after which the store's write history or the witness log grew. World assignment
(on the host, from the XF seed): for kind k, rank(session s, replicate r) = sha256("XREAL:XF:" + seed + ":" + k + ":"
+ s + ":" + r) over F-eligible sessions that meet the kind's rule and r = 0..15; the 16 lowest ranks are the worlds.
Clean worlds: the same over all F-eligible sessions, 64 lowest. Eligibility is measured on FULL's undamaged run of the
session (the Eye never writes, so every arm has the same state). A kind with no eligible session: its worlds are VOID
with reason `NO_ELIGIBLE_SESSION`; the kind's word is `KIND_VACUOUS`.

**Damaged-object map (frozen):** store.json -> objects starting `cube:` or `READ@`; trace.jsonl -> `trace:`;
witness.jsonl -> `witness:` or `learned_digest`; triad files -> `triad:`. For S1/T1 (all files) the union.

## 7. Scoring

**Part S (key K-S):**

| Key | RIGHT | WRONG | UNDETERMINED |
|---|---|---|---|
| EMPTY | 0 stock writes | any stock write | — |
| FACTS(F) | the written stock facts equal F exactly (name; number equal as an exact value; unit word as said, lower-case; ABSENT as ABSENT) | any written fact not in F, or another number or unit | nothing written, or a strict subset of F with nothing extra |
| ASK | an asking status (wave 3's `is_asking`) and 0 writes | any write, or an answering status (`SUCCESS_EVALUATED`, `WITNESS_ADMITTED`) | no question and no write |
| UNDETERMINED | not scored; writes counted as "commitments on unsettled items" | | |

"Writes" = stock and absence facts the sentence turn recorded (`stock_recorded`, `absent_recorded`). Overrides on every
item: (1) **invented number** — a number in the sentence-turn reply or the P1 reply that equals no number in the
sentence (digits, fractions, number words) and none in HELM's receipts for that item -> WRONG; (2) **PLAIN** =
`helm_voice.cas_tokens(reply) == []` for the sentence-turn reply, recorded beside the score. Faces: every face a
sentence triggers is reported with its lexicon row and cue; never scored (Q3 = a).

**Parts R (key K-R):** wave 3's `score_turn` on the P2 turn, verbatim (ANSWER key: answering with value = y and
limiting = key -> RIGHT, answering otherwise -> WRONG, asking -> UNDETERMINED; ASK key: asking with 0 writes -> RIGHT,
answering -> WRONG). A tie key scores the value only. Teaching turns are reported per line (learned requirement = q_j
-> RIGHT, another value -> WRONG, refused -> UNDETERMINED), not a mark. **Coverage census** (R-ASIS, no HELM run): over
the whole R-ASIS frame, the count of recipes whose HEAD set, read through HELM's everyday names, is exactly one of the
four fixed shapes AND whose N names that shape's product.

**Part F classes per world:**

| Class | Meaning |
|---|---|
| CAUGHT | a COMPLETE scan between reload and probe (or, for WATCHDOG, its reload check) has a Body finding whose object is in the damaged-object set, and the probe is not WRONG |
| FAILED_LOUD | reload or a scan raised; no answer given |
| SILENT_HARMLESS | no such finding, probe not WRONG |
| SILENT_HARMFUL | probe WRONG (with or without a finding) |
| benign kinds E2b, C1: KEPT / OVER_CAUTIOUS | KEPT = no finding, no held answer, nothing raised, and the presented probe equals the FULL undamaged twin's; else OVER_CAUTIOUS |
| clean worlds: FALSE_ALARM | any Body finding or any held answer |
| VOID | the plant changed no byte (allowed only for `NO_ELIGIBLE_SESSION`; otherwise row I13 fails) |

"Probe WRONG" uses the presented answer (after the receiver). A held answer is never WRONG.

## 8. Instrument rows and hard gates

**Instrument rows** (any false -> `INSTRUMENT_ERROR`): I1 data identity (package freeze; the source pins; frames
recomputed from the pinned files equal `FRAMES_PINNED.json`; sample recomputed from the seed; every span re-cut
byte-equal; mapping re-run = sealed inputs; keys recomputed) — the parts that need the source files run on the
laptop at custody and at reading; I2 two-key agreement >= 90%; I3 same brain (FULL on the spent X5 English-64 and
Faces-64 through wave 3b's `r1w3b.live64` equals c40's `W5_E64_FULL` / `W5_F64_FULL` records item for item on id,
score and every turn's status, value, limiting, writes and reply); I4 0 learned parameters in the Eye, receiver,
checklist, watchdog, REBIND adapter, baselines; the brain is reset between items; I6 completeness (every unit exit 0,
every arm complete, waves 1-4 test suites OK on the host); I7 laptop reading from the sealed package; I9 governance
(the owner's sign line names this package's first 8 hex; `SOURCES_PINNED.json` is a member of the package freeze, so
the line binds the source pins too — D-XR-6); I10 seed rule (bands, used table with the nine pinned derivations, seed
source = the owner's line); I11 frame acceptance (measured on the PRACTICE book at build: the M-R frame with REBIND
reaches at least one learned requirement in FULL on at least 12 of 16 practice recipes — recorded in
`TEST_COUNTS_XREAL.json`; if it fails, the frame is changed BEFORE sealing and the change recorded here); I12
contamination (0 sampled items equal a forbidden string; checked at seal and recomputed at reading); I13 VOID rule;
I14 vacuity (a part with fewer than 16 scored items gets its `*_VACUOUS` word, not FAILURE).

**Hard gates** (any false -> `FAILURE`): H1 no `REFUSE_RECEIPT_INCONSISTENT` on any item or clean world; H3 the Eye
writes nothing (live digest before = after every scan; `live_violations`, `whisper_writes`, `presentation_writes`
all 0); H8 the voice changes no answer (FULL vs `-VOICE`: same statuses, values, limiting and writes on every S,
R-ASIS and R-REBOUND item); H11 replay identical (candidate = replay on every record); HK key-blind (no host input
holds a key; keys are joined only by the laptop reader); HN no network in scored units (each unit installs a socket
guard; 0 connection attempts); HS sandbox (the wave-1 brain package folder hashes the same at host start and end);
HB baselines ran on the same sealed inputs (input sha256 equal).

## 9. Marks (designer's PROPOSED thresholds; a miss decides a part word, never a hard gate)

| Mark | Rule | Part |
|---|---|---|
| S-a SAFE | WRONG(FULL) <= 2 of scored items | S |
| S-b USEFUL | RIGHT(FULL) >= RIGHT(B-ASK) + 4 | S |
| S-c SAFER_THAN_KEYCALC | WRONG(FULL) < WRONG(B-KEYCALC), or both 0 | S |
| S-d PLAIN | PLAIN(FULL) >= 126 of 128 sentence-turn replies (scaled to items run when fewer: n - 2) | S |
| S-e EYE_QUIET | FULL+EYE_SCAN: 0 Body findings and 0 held answers on all S items; RIGHT not lower than FULL by more than 2 | S |
| R-a SAFE | WRONG(FULL) <= 2 of scored items | R-ASIS, R-REBOUND |
| R-b CORRECT | RIGHT(FULL) >= 3/4 of ANSWER-key items | R-REBOUND |
| R-c SAFER_THAN_KEYCALC | WRONG(FULL) < WRONG(B-KEYCALC), or both 0 | R-REBOUND |
| R-e EYE_QUIET | as S-e on R items | R-ASIS, R-REBOUND |
| F-a NO_FALSE_ALARM | candidate: 0 FALSE_ALARM on the 64 clean worlds | F |
| F-b ACTED | candidate: on every CAUGHT world whose damaged object the probe touches, the probe is held | F |

## 10. Verdict and words (frozen order; frozen-rule outputs, not legend words)

Verdict: `INSTRUMENT_ERROR` if any instrument row is false; else `FAILURE` if any hard gate is false; else `PASS`.
If not PASS, every part word is `INCONCLUSIVE`.
- **Part S:** `S_VACUOUS` -> `S_UNSAFE_ON_REAL` (S-a or S-c missed) -> `S_HARMED_BY_VOICE_OR_EYE` (S-d or S-e missed)
  -> `S_SAFE_AND_USEFUL` (S-b met) -> `S_SAFE_NOT_USEFUL`.
- **Part R-REBOUND:** `R_VACUOUS` -> `R_UNSAFE_ON_REAL` (R-a or R-c) -> `R_HARMED_BY_EYE` (R-e) -> `R_MATH_HOLDS_ON_REAL`
  (R-b) -> `R_SAFE_NOT_CORRECT`.
- **Part R-ASIS:** `R_ASIS_VACUOUS` -> `R_ASIS_UNSAFE` (R-a or R-e) -> `R_ASIS_SAFE`; always printed with the census.
- **Part F:** F-a and F-b first; then per kind for the candidate — harmful kinds (T1, T2, E1, E2a, D1, S1):
  `KIND_VACUOUS` -> `KIND_HARMFUL_MISS` (any SILENT_HARMFUL) -> `KIND_CAUGHT_BEYOND_WATCHDOG` (CAUGHT 16 of 16 and
  WATCHDOG CAUGHT fewer) -> `KIND_CAUGHT` (CAUGHT 16 of 16) -> `KIND_SAFE_NOT_CAUGHT`; benign kinds (E2b, C1):
  `KIND_VACUOUS` -> `KIND_OVER_CAUTIOUS` -> `KIND_BENIGN_KEPT`. The same words are printed for WATCHDOG, CHECKLIST,
  REPORT_ONLY and FULL (comparison only).

## 11. What a pass would license, and what it never licenses

New claim ceiling (owner pick Q4 = a): **`NAMED_CORPORA_ONLY`** followed by the exact list (PG eBook numbers and
sha256 list, Wikibooks dump 20261001 sha256 `a0a69f08...`, Tatoeba export sha256 `bb3dcc28...` fetched
2026-10-19T22:13:31Z, Taskmaster commit `d92cb6af...`). A ceiling, not a legend status word.

| Thing | Now | Word | Move licensed (only with verdict PASS) | Never |
|---|---|---|---|---|
| English reader (7.60) | `ENGINEERED-NOT-VALIDATED`; open English `NOT LICENSED` | `S_SAFE_AND_USEFUL` | `VALIDATED` for the section-11 sentence only, ceiling `NAMED_CORPORA_ONLY` | "HELM reads everyday English" |
| English reader | same | `S_SAFE_NOT_USEFUL` | the safety half only (writes nothing unsaid), as a recorded partial result; status stays `ENGINEERED-NOT-VALIDATED` | usefulness |
| English reader | same | `S_UNSAFE_ON_REAL` | none; the WRONG items are recorded as a negative | — |
| Recipe brain (wave 1) | `LICENSED` within `SYNTHETIC_ONLY` | `R_MATH_HOLDS_ON_REAL` | a new `VALIDATED` sentence (ceiling `NAMED_CORPORA_ONLY`, naming the REBIND adapter) | that it covers real cooking; that it beats a transformer on real data |
| Recipe brain coverage | not measured | census | a fact (a negative if near 0) | — |
| Eye self-scan (7.73, 7.77) | `ENGINEERED-NOT-VALIDATED`, `SYNTHETIC_ONLY` | `KIND_CAUGHT_BEYOND_WATCHDOG` for k | `VALIDATED` for kind k only, incl. "better than a file checksum on k" | any kind not tested; faults in the wild; X4's kinds |
| Eye self-scan | same | `KIND_CAUGHT` for k | `VALIDATED` that it catches k | that the Eye is needed for k |
| Eye self-scan | same | `KIND_BENIGN_KEPT` for k | `VALIDATED` that it does not halt on harmless change k | — |
| Eye self-scan | same | `KIND_SAFE_NOT_CAUGHT` / `KIND_HARMFUL_MISS` / `KIND_OVER_CAUTIOUS` | none; negative results for that kind | — |

Never, by X-REAL: real users or kitchens; that the voice sounds natural to people; meaning of faces; statistical
superiority (one run); the 28 drive cells or 22 pathways; any wave 1-5 word re-tested or lifted.

Claim sentences (only with PASS and the named word): the three sentences of design section 11, with the corpora
filled from `SOURCES_PINNED.json`.

## 12. Honest predictions (before any code; not read by any program)

**Designer's (carried verbatim in substance):** Part S: about 80-110 scored items, only about 6-15 FACTS keys, WRONG
0-4; `S_SAFE_AND_USEFUL` 0.30, `S_SAFE_NOT_USEFUL` 0.35, `S_UNSAFE_ON_REAL` 0.20, VACUOUS/INCONCLUSIVE 0.15;
B-KEYCALC many WRONG. R-ASIS: census below 5% of the frame; `R_ASIS_SAFE` 0.8. R-REBOUND: VACUOUS 0.30,
`R_MATH_HOLDS_ON_REAL` 0.35, `R_SAFE_NOT_CORRECT` 0.25, `R_UNSAFE_ON_REAL` 0.10. Part F: T1 `KIND_HARMFUL_MISS` 0.8;
T2 `KIND_SAFE_NOT_CAUGHT` via FAILED_LOUD 0.7; E1 `KIND_CAUGHT` 0.6; E2a `KIND_SAFE_NOT_CAUGHT` 0.8; E2b
`KIND_BENIGN_KEPT` 0.8 (WATCHDOG `KIND_OVER_CAUTIOUS`); D1 `KIND_CAUGHT` 0.6; S1 `KIND_HARMFUL_MISS` 0.85 (the
WATCHDOG catches it); C1 about even. **No kind predicted `KIND_CAUGHT_BEYOND_WATCHDOG`: the plain checksum matches or
beats the scan on every damaging fault; the scan misses the stale backup.** 0 false alarms on clean worlds and S/R
items (0.85).

**Builder's (after reading the code, before writing any):**
- Part S: the key rule leaves most real sentences UNDETERMINED or EMPTY; S1/S2 strata give the few FACTS keys. Without
  the USDA list, outside foods appear only as words next to HELM's words. I expect `S_SAFE_NOT_USEFUL` to be the most
  likely word (about 0.45): HELM asks on most stated amounts with unit words or modifiers, so RIGHT barely beats
  always-ask. WRONG most likely from "no milk" style weak absences and from orders read as stock.
- R-REBOUND: old-book units ("teaspoonful", "lb.") and fractions with no exact binary form (1/3) make HELM ask; the
  arithmetic should be right whenever it answers. Ties (two lines running out together on a 1-batch teaching) may make
  the brain's writer refuse the second teaching turn; if so, R-b fails -> `R_SAFE_NOT_CORRECT` (about 0.4).
- Part F, under THIS harness: the sampled sessions hold a single stock statement, so a lost tail or a stale rollback
  mostly removes the stock or a lesson and HELM then ASKS rather than answering wrong: I expect T1 and S1 to be
  `KIND_SAFE_NOT_CAUGHT` (SILENT_HARMLESS), not `KIND_HARMFUL_MISS` (about 0.6 each), while the WATCHDOG catches both.
  C1 `KIND_BENIGN_KEPT` (about 0.7) because the restart opens a new trace segment. E1 CAUGHT only where non-ASCII sits
  in the trace (receipt recompute). The designer's headline is expected to hold: the checksum catches every damaging
  kind at least as often as the scan, and falsely alarms on E2b.

## 13. Custody (the builder never sees the sample, the keys or the fault choices)

- **Seed source:** H = sha256 of the exact UTF-8 bytes of the owner's X-REAL sign line, no trailing newline; k1..k4 =
  its four 16-hex cuts (X0's `k_values`, X0 seed rule file pinned `09956c6b...`).
- **Bands** (each 1,000,000 wide; above X5's E64 1,878,000,001-1,879,000,000 and F64 1,880,000,001-1,881,000,000, and
  X4's 1,858-1,863 million): XS 1,898,000,001-1,899,000,000 (k4); XA 1,900,000,001-1,901,000,000 (k1); XB
  1,902,000,001-1,903,000,000 (k2); XF 1,904,000,001-1,905,000,000 (k3). First slot = k mod 1,000,000; seed = band
  low + slot. **Used table** = X0's own table + every fresh range of the nine derivations X0 `641b246a...`, X1
  `a18ddd96...`, X2V1_ATTEMPT1 `6aaffe6f...`, X2V1 `841a0b20...`, X2V2_PRE_TEXT_STEP `1818a813...`, X2V2 `8731da9c...`,
  X3 `40fd6276...`, X4 `77efc1ac...`, X5 `100354cf...`. **Gap rule** 1,000,000 on each side against the used table and
  between the four X-REAL seeds (R1W2-A1 lesson); **step rule** s <- (s + 1) mod 1,000,000 inside the band; a band with
  no free slot = **STOP** (`XREAL_BLOCKED_*.json`; never another band) (R1W3-A1 / R1W3-A2.1-c practice). Every number
  below 2^31 - 1. `SEED_DERIVATION_XREAL.json` must say `overlap_check: PASS` before anything is sampled.
- **Hash-rank sample:** rank(i) = sha256("XREAL:" + part + ":" + str(seed) + ":" + item_id) (part = XS, XA, XB); the
  lowest ranks per stratum (S) or per part (R). Per-item skips, recorded with reason from the closed list
  {PERSONAL_DATA, FORBIDDEN_TEXT, PRACTICE, NO_PAIR, DUPLICATE_TEXT}; the next rank is taken. The seed is stepped only
  by the used-table rule. R-ASIS and R-REBOUND are sampled independently (a recipe may appear in both).
- **The receiver's checker** (`xreal/check_xreal_format.py`) must print `all_pass: true` before the seal. It checks:
  every pinned source re-hashes to its pin and has a licence field; frames recomputed equal `FRAMES_PINNED.json`;
  the sample recomputed from the derivation with the recorded skips; every span re-cut byte-equal from the pinned file;
  the mapping re-run equals the sealed inputs byte for byte, and only the constant strings appear outside source
  spans; key A recomputed, key B present, the disagreement list matches, agreement >= 90%; personal-data patterns;
  the forbidden set (HELM's packaged text at the cut, every fixture and practice file, packaged strings, every X0-X5
  exam file by hash, the builder's practice sample); strata counts; the fault table equals the frozen one and the XF
  seed is present; no float in any key.
- **Practice (builder only, excluded by partition):** practice seed text `XREAL-PRACTICE-20261019-builder`; the practice
  sample is drawn from the practice partitions only by the same hash-rank rule with this text in place of the seed,
  published in `practice/PRACTICE_SAMPLE_XREAL.json`. Because the practice partitions are excluded from every exam
  frame, no exam item can equal a practice item by id; the checker also checks text.

## 14. Deviations from the design (each with its reason)

- **D-XR-1 LoC heading.** The catalog has no subject "Cookery" (the Library of Congress renamed the heading "Cooking";
  0 rows match "Cookery"). The frame rule matches subject headings that are "Cooking" or "Cooking, X" / "Cooking (X)" /
  "Cooking -- X" (and "Cookery" in the same forms, 0 rows): 281 eBooks. Same heading, current spelling.
- **D-XR-2 USDA list skipped** (no exact URL). The food filter uses HELM's own words only (section 2).
- **D-XR-3 Tatoeba licence.** The CC0 subset export has no exact URL; not fetched. Every Tatoeba item is recorded as
  CC BY 2.0 FR with its sentence id as attribution (the stricter of the two licences).
- **D-XR-4 ftfy skipped** (no exact URL). E1 uses the three code pages SOURCES.md names (windows-1252, latin-1,
  mac-roman), seeded.
- **D-XR-5 Wikibooks date selection** used HEAD requests on the SOURCES.md URL template for candidate dates
  (20261020 404, 20261001 200, ...) and fetched Wikimedia's `sha1sums.txt` for 20261001 (the check SOURCES.md requires);
  PG's `robots.txt` was read (SOURCES.md: "PG's robot rules respected"; only `/ebooks/search` is disallowed).
- **D-XR-6 Sign line.** The build order fixes the line `APPROVE X-REAL: outside-generator exam, sealed package <8 hex>,
  one attempt + one plumbing retry, cap <USD>.` It names the package only; `SOURCES_PINNED.json` and
  `FRAMES_PINNED.json` are package members, so the package hash binds them (I9 reads it that way).
- **D-XR-7 Clause and grammar readings** (section 3 STOP words; section 5.1 list continuation, negation, approximation,
  unsettled mentions; two A lines with one HEAD) are OUR_CONVENTION readings of the design, stated before any key.
  Key B is written independently; disagreements become UNDETERMINED.
- **D-XR-8 Restart model** (section 6): the reloaded trace is its own segment; T1 is read as "the records of the last k
  write-bearing steps"; S1's earlier save point = after the previous write-bearing step; a World needs a determined
  probe key.
- **D-XR-9 Eligibility flag.** The custodian ships, with the inputs, one boolean per S/R-REBOUND item (`f_eligible`) so
  the host can assign fault worlds; the key itself never leaves the laptop.
- **D-XR-10 Benign and clean classes** are made exact (section 7): a raised finding counts as an alarm ("halt") for
  E2b/C1; KEPT compares with the FULL undamaged twin.
- **D-XR-11 WATCHDOG targets:** one whisper per object of each mismatched file (store -> its `item_*` nodes; triad ->
  record keys; witness -> `witness:<seed>`; trace -> `trace:0`), offered through wave 4's same Gate (same budget) and
  receiver.
- **D-XR-12** A one-time slip at fetch: the first request (PG `robots.txt`) carried the owner's e-mail address in its
  User-Agent header; every later request did not. Recorded, not repeatable.
