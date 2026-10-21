# tksCAS — Changelog

Monorepo-level log. Subprojects keep their own changelogs
(`cas-forex/CHANGELOG.md`, `noetic-compass-scaffold/noetic-compass/CHANGELOG.md`,
`book/CAS_PCBA_Engineer/CHANGELOG.md`). This file records cross-cutting campaign milestones.

## 2026-10-20 PDT - "Build both" (owner word): stage 1c of the wide brain (6 widened units with exact programmed factors + NOTE lines; switch WIDE_UNITS_NOTE, default OFF) and the CAS address on every receipt (owner's fix G = stage 1 of the 28-cell packet; switch CAS_ADDRESS, default ON, byte-identical OFF); 13 HELM suites Ran 225, OK (11 suites Ran 194, OK before), 226 after the same-day correction; laptop, 0 USD; ENGINEERED-NOT-VALIDATED; no claim moved

- Build 1, `helm_brain_wide.py` + `helm_wide_turn.py`, behind ONE switch `WIDE_UNITS_NOTE` (`helm_brain_wide.units_note_on()`; environment `HELM_WIDE_UNITS_NOTE` = `1` / `ON` / `TRUE` / `YES` turns it on; default OFF because the existing tests pin the 20-unit table, 9 factors and the NO_AMOUNT / UNIT_NOT_IN_TABLE questions). OFF is reader v5 / brain v1 unchanged: the 20-unit table `UNITS` is not touched, `NAMED_FACTORS` stays 9, every question stays. ON: `UNITS_WIDENED` adds 6 units, each built only from programmed exact factors (`NAMED_FACTORS_WIDENED`, 6 more, 15 in all): liter (ML_PER_L = 1000), deciliter (ML_PER_DL = 100), centiliter (ML_PER_CL = 10) through the existing ML_PER_TSP; gallon (QUART_PER_GALLON = 4 through the US chain: 1 gallon = 16 cups); fluid ounce (TBSP_PER_FLOZ = 2: 1 US fl oz = 6 teaspoons = 29.5735295625 mL exactly; spelled "fluid ounce(s)", "fl oz"); dozen (EACH_PER_DOZEN = 12, a plain-count multiplier). Nothing is learned; the parameter table lists 15 factors ON, 9 OFF.
- NOTE lines (ON): an ingredient with no exact amount ("salt", "pepper to taste", "butter for frying", "1 dash salt", "2 sticks butter", "a pinch of salt", "1 can tomatoes") is a stock entry (None, "") = PRESENT, no amount. The recipe keeps a `notes` list beside its support; notes never enter a coefficient, the yield, the limiting reagent or the memory check; a batch whose ran-out ingredient is a note is refused `REFUSED_RAN_OUT_IS_A_NOTE`; the answer and the lesson say "Salt goes in too, with no set amount, so I didn't count it toward the limit." A unit word with no exact size (`NOTE_UNIT_WORDS`: stick, dash, handful, sprig, box, ... = `OTHER_UNIT_WORDS` minus the widened words; a test pins the partition) makes the line a NOTE line instead of a UNIT_NOT_IN_TABLE question; the first build also read the table's 9 own-count units that way (`OWN_UNITS_AS_NOTES`); the same-day correction below empties that set, so "2 cans tomatoes" stays an exact count of cans ON as OFF. Ranges, approximate amounts, two-part amounts, relative amounts, clauses, absences ("no water"), headings ("For the sauce:") and bare note words ("sifted") stay the questions they were. A bare name after an amount line still stays that line's note, as in v5 ("4 cups flour, 24 eggs and salt" keeps salt as a note of eggs); bare names after a bare name are NOTE lines of their own ("salt and pepper to taste" = two notes). A notes-only stock turn has no number to round-trip: the CCE skin row says so and nothing numeric is saved.
- Census 1 re-run on the laptop (`census_gap_lines.py`, counts only, 2.1 s each; 86,291 lines of 13,686 real recipes): OFF reproduces every count of 7.97 exactly (refused 10,069; `CENSUS_GAP_LINES_RERUN_OFF_20261020.json` e3325f5a...). ON (`CENSUS_GAP_LINES_STAGE1C_ON_20261020.json` afa8ed5c...): refused 10,069 -> 3,654 (11.67% -> 4.23%); read 76,222 -> 82,637 (88.33% -> 95.77%); PG refused 3,030 -> 1,909, WB 7,039 -> 1,745. By family, before -> after: NO_AMOUNT 5,164 -> 291; UNIT_NOT_IN_TABLE 1,662 -> 0; NO_NAME 1,746 -> 1,849 (+103); AMOUNT_IS_A_RANGE 1,305 -> 1,309 (+4); AMOUNT_HAS_TWO_PARTS 119 -> 125 (+6); AMOUNT_APPROXIMATE 26 -> 29 (+3); UNREAD_CLAUSE 30 -> 30; AMOUNT_RELATIVE 17 -> 17; SAME_INGREDIENT_TWICE 0 -> 4 (lines that used to stop early now reach a later check). Recipes with every line read 9,561 -> 11,737; none read 262 -> 30; gap recipes 3,030 -> 1,477; refused lines inside gap recipes 5,445 -> 1,974 (floor 256: still PASS_FLOOR). Honest reading: "read" ON includes NOTE lines, which the brain records as present only. Of the 82,637 lines read ON, 74,574 carry an amount in a sized unit (279 of them in a widened unit: dozen 109, gallon 90, liter 68, deciliter 8, fluid ounce 3, centiliter 1) and 8,042 are NOTE-only lines (8,584 NOTE lines in all: 5,384 with no amount, 1,946 in an own-count unit that OFF read as an exact own count (clove 413, slice 367, can 358, pinch 333, package 164, teacup 157, saltspoon 154; bunch and square 0), 1,254 in 62 distinct unsized unit words). So the real gain in exact amounts is 279 lines; the rest is honest presence. [First build; corrected the same day, see below: the 1,946 own-count lines are exact counts again.]
- Build 2, new module `helm_cas_address.py` (the ONE place the rules live) + 7 lines in `helm_end_to_end_loop.py` (`_emit`, `_finish`); `helm_wide_turn.py` and `helm_brain_canonical.py` never see a tag. Schema `cas_address/1`: foundation F1..F7, domain P/C/E/O, cell of the 28 (e.g. F2C), register T/A/f/E, pathway of the 22 (A0, D1-D7, W1-W7, P1-P7), element of the 40 (e.g. ^8C), and `how` = the rule id per field. Named rules: FND-1 (the record names its Foundation), FND-2 (an item the Unity Eye wrote is F1, the owner's ruling), DOM-1a..e (status / reason word through the census-2 draft table, promoted: refusals P; lessons, answers, readings, plans, questions C; verdicts, receipts, checks E; stock, batches, tools, files O), DOM-2 (item kind), DOM-3 (the loop's stations: CCE skin E, S1 trigger C, S2 Bias O, S3 arrival E, S5 RPM link P, readers C, store cube_write O / eta_eps_receipt E; brain and S6 rows by their word), CELL-1 (both set), REG-1a faces / purpose f, REG-1b a plan or a rule that fired A, REG-1c a stock or batch line E, REG-1d a vision-level item T, PATH-1 (only a planner-named node; none today), ELE-1 (only a Noetic the record already names: the station strings ^8, ^5, ^9 give ^8C, ^5O, ^9E). Everything else `UNTAGGED`, never guessed. Switch `CAS_ADDRESS` (`cas_address_on()`; `HELM_CAS_ADDRESS` = `0` / `OFF` / `FALSE` / `NO` turns it off), default ON since all 194 existing tests pass unchanged with it on.
- What gets the field ON: every trace row (`_emit`), every turn receipt (`_finish`: `result["address"]`), and the recipe receipt and cube receipt the turn carries (shallow copies; the brain's and the store's own objects are not mutated). The receipt hash is computed over the turn's rows with every address stripped, so it is identical ON and OFF (test). Honest limit, exactly census 2's: the live loop names no Foundation, so every loop receipt has foundation UNTAGGED and cell UNTAGGED (the fixture's histogram: 0 of 28 cells); Domain is set on most rows, Register on stock / batch / rule rows, Element on the three Noetic-named stations. The 28-cell Eye (stage 2, EYE_CELLS), the 196-pair table and any exam are NOT built; no Eye in this checkout files backlog items (RB-I3 lives in sealed packages), so `address_for_filed_item` is provided for the filing program and exercised only by its test.
- Tests: `test_helm_units_note.py` (14: OFF unchanged; the 6 units' exact conversions and round trips; cross-kind refusals; the word partition; NOTE lines in the reader, the brain, the live loop; a note can never be what ran out; notes count toward the 10-ingredient limit; parameter accounting: no new learned number) and `test_helm_cas_address.py` (17: canon names and counts 7 / 4 / 4 / 22 / 28 / 40; every rule by name; every record stamped ON; receipt hash identical ON vs OFF; OFF records of a 13-turn fixture hash to the sha256 pinned from the pre-change code at 159c7d2b (56f356ea...); ON with the address stripped hashes to the same; the loop reads no tag). All 13 HELM suites: Ran 225, OK (the triad's `test_15_sealed_package_untouched` reads `git status` on `helm_end_to_end_loop.py`, so it passes only on the committed tree).
- **Correction, same day (second commit; coordinator: the brief was wrong on one point).** The table's 9 own-count units (can, clove, slice, pinch, package, bunch, square, saltspoon, teacup) are EXACT plain counts today ("2 cans tomatoes" teaches 2 cans per unit) and now stay exact when `WIDE_UNITS_NOTE` is ON; `OWN_UNITS_AS_NOTES` is kept as a named set but EMPTY, with a test that it is empty and that "2 cans tomatoes", "a pinch of salt", "2 cloves garlic", "1 package yeast" read as exact own counts ON and OFF. Only words with no exact size outside the table (`NOTE_UNIT_WORDS`: stick, dash, handful, sprig, box, ...) make NOTE lines. Census ON re-run after the correction (`CENSUS_GAP_LINES_STAGE1C_ON_20261020.json` now 29b79f74...; 1.9 s): every refusal count is the same as the first build (refused 3,654; NO_AMOUNT 291; UNIT_NOT_IN_TABLE 0; NO_NAME 1,849; AMOUNT_IS_A_RANGE 1,309; AMOUNT_HAS_TWO_PARTS 125; AMOUNT_APPROXIMATE 29; UNREAD_CLAUSE 30; AMOUNT_RELATIVE 17; SAME_INGREDIENT_TWICE 4; gap recipes 1,477 / 1,974 refused lines), because those 1,946 lines were read either way; what changes is what "read" means: lines with an amount in a sized unit 74,574 -> 76,518; NOTE lines 8,584 -> 6,638 (5,384 with no amount + 1,254 in 62 unsized unit words); NOTE-only lines 8,042 -> 6,100; lines with a note beside an amount 21 -> 19; the 1,946 own-count lines (clove 413, slice 367, can 358, pinch 333, package 164, teacup 157, saltspoon 154) are exact own counts again. The first build's counts above are kept in the record as "first build, corrected same day". Tests after the correction: 13 suites Ran 226, OK.
- Not changed: `helm_brain_canonical.py` (pinned byte-for-byte); any sealed package; any claim status; `helm_voice.py`, `helm_chat._speak`, `helm_end_to_end_loop.wants_turn` (another session's files). Deviation from the census-1 wording: "pinch", "slice", "can", "bunch" were named there as units outside the table, but they are inside the 20-unit table as own-count units; the 1,662 UNIT_NOT_IN_TABLE lines were the `OTHER_UNIT_WORDS` (stick, dozen, liter, gallon, dash, ...). Spec sheet 7.97 follow-up and section 11 row; both packets' README and OPEN_QUESTIONS status lines updated.
## 2026-10-20 PDT - HELM-R1 wave 7 "CHAT WAVE" packet SEALED v3, NOT LAUNCHED (spec sheet 7.98): HELM's live chat with the wide brain on, scored on fresh sealed exams; owner's line to sign "CHAT WAVE at 1 USD"; 0 USD

- Design first, hashed before any code (PREREGISTRATION_R1W7.precode.md efe94ed6...): exams X7_REAL (128 real recipes typed as lessons, stock and a question), X7_CONV (64 dialogues from wave 6's generator at a fresh seed), X7_NOISE (the same 64 with two of twelve frozen small-talk sentences each); arms CHAT_ON (under test), CHAT_OFF, CHAT_ON_REPLAY, CHAT_DIAG, LOOP_ON, ALWAYS_ASK; 14 units; marks NH-CHAT, K1, K3, K4, P PLAIN, N NOISE; words CHAT_WAVE_HARMED / NO_GAIN / INCONCLUSIVE / EARNED_KEEP; bands 1,990 / 1,992 / 1,994 M; cap 1.00 USD.
- Package built from the wave-6 v3 package (generator, scorer, custody tools reused by import): zip 5063baba8be9ba807e7905d5f86732cb1a535ff5a533e67c79f5cbe16edbc6a9 (v3; freeze 2366e85d7a3b73fa0c6cefb94715aa7ba9cfeb6f3b384c4c0ad88d5ed0165da2); HELM cut dfc7158d (161 files by git show); 31 wave-7 tests + 201 HELM tests OK from the sealed extract. v1 (5107b9c6) and v2 (7e7fa066) void, never launched, no exam drawn.
- The builder's PRACTICE runs (practice data only) found five defects in the chat as shipped and both FIX FIRST rounds landed in HELM first (PR #416): practice lost-vs-loop 13 -> 0, unexplained asks 8 -> 0, plain answers 35 -> 103, misrouted turns 10 -> 0, tool-engine turns 4 -> 0 (a kitchen sentence had run a shell command). All six marks met on practice v3. Negatives kept: 18 of 64 faces dialogues UNDETERMINED in chat and loop alike; two R4 lesson forms not admitted; one R7 item loses its stock; an "X or Y" name spoken oddly.
- Nothing scored, no claim, no approval record, no custodian seal, no hold, nothing launched. Next: the owner's line, then the approval record by program, the custodian's blind draw, job c51.
- Files: Documents/Codex/2026-10-20/r1_wave7/ (zip, freeze, TEST_RECORD_R1W7.md, TEST_COUNTS_R1W7.json, build/, dry_run/); copies docs/working/r1_wave7/; launch brief docs/working/r1_wave7/LAUNCH_BRIEF_R1W7_20261020.md.

## 2026-10-20 PDT - FIX FIRST for wave 7, round 2: a kitchen sentence never reaches the tool engine; two more question forms and a greeting are read; "X or Y" lines bind the first name; 0 USD

- Found by the wave-7 builder's SECOND practice run (v2 package, practice data only): (1) "We have 6 C-peaches, sliced but we've run out of c-sugar." reached the loop's tool engine (the word "run") and a shell command ran (python --version) during the practice; (2) neither reader claimed wave 3b's question forms "Could you tell me how much X that makes?" / "How much X do we have the makings of?" nor a leading "Hi again.", so the chat answered them as general knowledge (5 misrouted turns); (3) "1 cup dry beans or whole peas" was learned under the made-up name "dry beans or whole pea" (1 wrong lesson).
- Fixes: the loop's not-checked branch never calls the tool engine when the wide reader claims the sentence, its keywords match whole words only, and kitchen talk ("run out", "we have", units, "pantry", "recipe") never counts as a software goal; the chat's own software-goal trigger gets the same rules and knows the wide brain's ingredient names; the wide reader claims the two question forms, strips a leading greeting, binds the first alternative of "X or Y" and keeps the alternative as a note of the line, and turns "..., but we've run out of X" into a reader question (ABSENT_STATED) instead of a made-up stock name.
- Tests: four new in test_helm_wide_alongside.py (class F), one of which fails if any shell command runs on a kitchen sentence; all HELM suites Ran 201, OK. helm_brain_canonical.py byte-identical. No claim status changed; no sealed package changed. Wave 7 is resealed on this build (v3).
- Builder's slip, recorded: an inline edit turned the regex word boundary into a backspace byte in two lines; caught by the suites, fixed from a script file.

## 2026-10-20 PDT - FIX FIRST for wave 7 (the CHAT WAVE): the chat now hands the wide brain every line the wide reader claims; wide answers are said in the wide path's own exact words; kitchen fractions are said exactly; 0 USD

- Found by the wave-7 builder's PRACTICE run (no sealed exam opened; counts are facts about practice data only): the chat handed a line to the loop only when the LICENSED reader claimed it (helm_end_to_end_loop.wants_turn), so lines only the wide reader handles ("How much consomme can we make?" with its accent, "How much eggs ...", wave 3b's question forms) fell to "I don't have verified data": 13 of 106 real recipes lost against the loop driven directly, 8 unexplained asks, 10 misrouted turns. A wide answer was re-rendered as "about 0.33 units" with no dish name (55 of 90 right answers not said exactly); a recorded stock turn was answered "That's outside what I know"; a lesson reply printed a Python list.
- Fixes: wants_turn consults helm_wide_turn.read_wide when the switch is on; helm_chat._speak says a wide-path turn with the wide path's own sentence through the voice guard (exact amounts, the dish name, "Noted: we have ..."); helm_voice.say_amount says a kitchen fraction (denominator up to 16) exactly ("exactly 1/3", "exactly 1 1/3") and still says "about 8.45" for a long decimal; mixed numbers parse; the lesson receipt never prints a list.
- Tests: three new in test_helm_wide_alongside.py (class E), each failing on the thread head before the fix; test_licensed_files_untouched now pins helm_brain_canonical.py only (helm_voice.py changed on purpose, dated note in the test). All HELM suites: Ran 197, OK.
- Not changed: any claim status; any sealed package; helm_brain_canonical.py (byte-identical). Not scored: the chat on a sealed exam (wave 7 is resealed on this build next).

## 2026-10-20 PDT - Two free censuses for the design packets (spec sheet 7.97; owner: "run both free censuses ... Counts only; STOP at the floors"): census 1 PASS_FLOOR (5,445 refused lines in 3,030 gap recipes, floor 256; reader v5 refuses 11.67% of 86,291 real lines, mostly no-amount / unknown-name / unit-not-in-table / ranges); census 2 STOP_NOT_EXERCISED (0 of 28 cells: no record carries both a Foundation and a Domain); laptop, 0 USD, nothing sealed, no claim changed

- Census 1 (`census_gap_lines.py`, `CENSUS_GAP_LINES.json` 4011c41a...): 13,686 recipes, 86,291 lines; read 76,222, refused 10,069; gap recipes 3,030 with 5,445 refused lines. Codes: NO_AMOUNT 5,164; NO_NAME 1,746; UNIT_NOT_IN_TABLE 1,662; AMOUNT_IS_A_RANGE 1,305; AMOUNT_HAS_TWO_PARTS 119; UNREAD_CLAUSE 30; AMOUNT_APPROXIMATE 26; AMOUNT_RELATIVE 17. Upper bound: key rule and spent exclusions are custodian steps. Reading: the gap is mostly lines no reader can make exact; the ear's expected gain is lower; Q7 added (widen the unit table; a NOTE line for ingredients without an exact amount) before any ear.
- Census 2 (`census_tags_28_cells.py`, `CENSUS_TAGS_28_CELLS.json` 2a8f1b82...): 172,437 receipt-like items over 80 c50 files + 624 RB-I3 files; Foundation-only 101,718 (RB-I3 choice words); Domain-only 70,719 (c50 receipts: C 58,494, O 6,036, E 3,419, P 2,770); both 0. Stage 1 (cas_address/1 written at creation, behind a switch, byte-identical OFF) is the next build; then re-census.
- Files: Documents/Codex/2026-10-20/<packet>/census/; copies docs/working/<packet>/census/.

## 2026-10-20 PDT - Two design packets (owner: "Yes, write both design packets at 0 USD ... Design only, no run"): the recipe-shape proposer ear and receipt tags + the Unity Eye pairing over the 28 cells; DESIGN ONLY, nothing built or run, no claim changed, 0 USD

- helm_recipe_shape_ear_design_v1: the ear (CTT shell, 9,585,566 parameters) proposes only the SHAPE of a recipe sentence (line roles, span pointers into the user's words, which dish) when wide reader v5 would ask; no digits, no names in its vocabulary; three-copy agreement rule and read-back kept from CTT-2R; the brain's receipt and memory check unchanged. Census first (gap stratum floor 256), then build, then seal + owner line. Whole-CAS-expression ear parked: SDG text is a settled negative corpus (spec 10.1) and human CAS labels agree at ^1 only (7.23).
- helm_eye_pairing_28_cells_design_v1: stage 1 = a deterministic CAS address on every receipt and filed item (Foundation, Domain, cell of 28, Register, pathway of 22, element of 40; UNTAGGED never guessed) = the owner's fix G ("redeem 22x40"); stage 2 = the Eye's table over 196 (cell, faculty) pairs with back-off to the 7 x 7 table on untagged items, so it cannot do worse by construction; the 7 x 7 Eye is the baseline to beat; random-tag control; tag census floor 20 of 28 cells. Stages 3 (22 pathways) and 4 (40 elements) named, not designed.
- Files: Documents/Codex/2026-10-20/helm_recipe_shape_ear_design_v1/ and helm_eye_pairing_28_cells_design_v1/ (README, DESIGN, TEST_PLAN, OPEN_QUESTIONS each); copies docs/working/.

## 2026-10-20 PDT - WIDE BRAIN ON BY DEFAULT in the live loop and the chat (owner order after the ruling; spec sheet 7.56 follow-up); HELM suites 194 OK; 0 USD, no paid run

- helm_brain_wide.wide_brain_on(): default ON. Off only when HELM_WIDE_BRAIN is 0 / OFF / FALSE / NO (WIDE_BRAIN_OFF_WORDS) or the loop is built with wide_brain=False. helm_end_to_end_loop.HELMEndToEndLoop() therefore runs HELM's canonical wide brain by default: the licensed path still reads every turn first; the wide book takes only the turns it cannot bind. helm_chat.py builds that loop, so the chat follows. An OFF loop still never imports helm_brain_wide / helm_wide_turn (checked in a fresh process).
- Headers updated in helm_brain_wide.py (switch, claim status VALIDATED for the 7.89 / 7.96 sentences only, canonical since 2026-10-20), helm_wide_turn.py and helm_chat.py. helm_brain_canonical.py is NOT changed: test_licensed_files_untouched pins the licensed loader byte-for-byte to its scored base, and that pin is kept; its header still carries the 2026-10-18 wording.
- Tests: the two tests that pinned OFF are rewritten (default ON; OFF by 0 / OFF in a fresh process), plus a default-loop test and an explicit-False test. All HELM suites on the laptop: Ran 194, OK (baseline before the change: OK).
- Not changed: any claim status; any sealed package (each pins its own HELM cut). Not done: a sealed exam of the live chat with the wide brain on (needs a new owner line with a hash and a cap).
- Dictionary (Canonical brain, Wide brain) and hub (home, architecture, build pages) updated; site rebuilt.

## 2026-10-20 PDT - OWNER RULING: the wide brain is HELM's canonical brain ("YES TO WIDE BRAIN: Wide brain becomes HELM’s canonical brain"); spec sheet 7.56 pointer moved on the 7.96 reading; claim statuses unchanged; 0 USD

- The owner's words (about 3:38 PM Pacific), verbatim, are recorded in Documents/Codex/2026-10-18/OWNER_APPROVALS_20261018.md with the executable mapping: the canonical-brain pointer (spec sheet 7.56) moves to RB-W1 (helm_brain_wide.py + helm_wide_turn.py, reader v5, as cut at fdf68e0c inside the sealed wave-6 v3 package f1b64a5e), on the reading R1_W6_READING.json d6a855f1 (7.96, WIDE_WAVE_EARNED_KEEP).
- Unchanged by the ruling (a ruling is not a result): the wide brain's claim status (VALIDATED for the 7.89 and 7.96 sentences only; NAMED_CORPORA_ONLY + SYNTHETIC_ONLY); the wave-1 brain's LICENSED claim (R1_BEATS_GB3, SYNTHETIC_ONLY), kept as the licensed reference brain; every sealed package (each pins its own HELM cut).
- Engineering that follows, with tests, before any paid run: the live loop and the chat run with the wide brain ON by default (today HELM_WIDE_BRAIN is OFF unless set); the three module headers name the canonical brain; a frozen test is sealed before any new wave.
- Dictionary: Canonical brain, Canonical-brain candidate and Wide brain entries updated; hub: home strip, home text, architecture, model card, roadmap and build pages; site rebuilt.

## 2026-10-20 PDT - HELM-R1 wave 6 v3 (the K4 re-run) SCORED (job c50, spec sheet 7.96): verdict PASS, status word WIDE_WAVE_EARNED_KEEP; the wide brain is now HELM's canonical-brain CANDIDATE ACROSS THE SWITCHES; making it canonical is the owner's decision; 0.02 USD

- Owner pre-approval "FIX K4 at 1 USD" (one re-run after the K4 cause was found and fixed: reader v5, PR #406). Package v3 (zip f1b64a5e, freeze da1ec4d2), fresh custodian exam X6v3 (manifest 49a5d311; spent X6 excluded by id and text). One m6i.xlarge (i-079e316d784f0a821), 2:29-2:33 PM PDT, host run 135 s, one attempt, 0 retries.
- Frozen reader (laptop, fresh extract, 194 / 194 members ok, neighbours by hash): every instrument row and hard gate true; every mark met. Did no harm: 0 items lost on X6_E64, X6_F64, X6_PAIR A/B/C and next to each Eye; 1 lost in conversation (limit 2). X6_REAL FULL+WIDE: fully learned 93 of 94 (bar 85), RIGHT 94, WRONG 0, wrong lessons 0, unexplained asks 0 (K4 met); caution rule answered 0 of 13 same-name recipes (limit 2; literal 3 of 18, reported). Eyes: 0 false alarms, 0 writes; guard trips 0.
- X6_CONV: WIDE arms 37 right / 1 wrong / 26 asks vs FULL 30 / 0 / 34 (the 1 wrong: CV53:pg:42450@58358, right again with the English reader off); without the triad 5 wrong. X6_PAIRW backlog: FULL 23.70%, FULL+WIDE 33.53%, FULL+EYE_PAIRING 52.47%, FULL+WIDE+EYE_PAIRING 68.03%. Pair words READ: WIDE x CUBE_STORE / ENGLISH_IN / TRIAD / EYE_PAIRING all ADDITIVE; WIDE x VOICE and x EYE_SCAN NOT_EXERCISED_BY_CONSTRUCTION.
- Licensed (PREREGISTRATION_R1W6.md section 12, word 5): RB-W1 (reader v5) = HELM's canonical-brain candidate across the switches, VALIDATED for that sentence only, ceiling NAMED_CORPORA_ONLY (real recipes) + SYNTHETIC_ONLY (drive loop, English-64 / Faces-64, conversation). NOT licensed: that it IS the canonical brain (the owner's word); the licensed wave-1 brain keeps its license and stays canonical.
- Negatives kept: 1 conversation item newly wrong under WIDE; 5 wrong with the triad off; 16 of 110 answerable real recipes asked (114 of 662 lessons not learned; reader v5's relative-amount asks); literal caution count 3 of 18 at its would-be limit.
- Operator plumbing disclosed: the c50 scripts carried c48's payload and reservation hashes as placeholders (filled after the build and the hold; originals kept); first launch call refused at LEASE_REQUIRED before any AWS call (lease then written); first closeout call stopped on the placeholder after writing its proof (kept).
- Charge 0.02 USD (list 0.014842; cautious 0.04); ledger 113.21 -> 114.21 (hold) -> 113.23 of 200 (unreserved 86.77); cleanup VERIFIED three ways.
- Files: Documents/Codex/2026-10-19/r1_wave6/run_c50_r1w6v3_20261020/ (RUN_RESULT_R1W6V3_C50.md, R1_W6_READING.json d6a855f1...); copies docs/working/r1_wave6/; backup D:/tksCAS-archive/r1_wave6_c50_20261020/ (three hash passes). Hub: scorecard row 7.96, home status strip, architecture, roadmap and build pages; site rebuilt.

## 2026-10-20 PDT - CTT-2R SCORED (job c49, one g5.xlarge GPU; spec sheet 7.95): frozen reader INSTRUMENT_ERROR, word INCONCLUSIVE by rule 1 (Part R NOT_EXERCISED); no word earned; Part K line EARS_EARNED_KEEP reported only; 0.22 USD

- The sealed CTT-2R package (zip d97a16d6, section 7.92) ran as job c49 on 2026-10-19 10:43-10:51 PM PDT (i-01ee2ab9b0726fe85, g5.xlarge, A10G). No training. 8 of 8 host stages exit 0; GPU smoke 9,585,566 parameters asserted, audit clean; C2-s2 / C2-s3 made from recorded seeds.
- Custodian first, for free: Part R census R1 = 7 stock-stating sentences the reader gives up on (floor 24) in a frame of 15,255, so Part R NOT_EXERCISED by the pre-registered STOP; coordinator ran Part K only (new LLM pool: Gemini + DeepSeek, 128 singles with 32 traps + 16 dialogues / 60 turns; overlap 0 on every rule; amendments CTT2R-A1 / A2 recorded; seed derived before A2, disclosed).
- Frozen reader (laptop, fresh extract, 34 / 34 members ok): verdict INSTRUMENT_ERROR, word INCONCLUSIVE, rule 1, as forecast (about 0.6). Nothing moves; the translator stays ENGINEERED-NOT-VALIDATED.
- Part K line (reported only, never the word): PASS / EARS_EARNED_KEEP. Every harm gate true. Singles RIGHT: reader 63; three-copy agreement rule (A4E) 79, CWFW 0; copy-closest under the same rule 65; untrained under the rule 63; copies without the rule 84 / 82 / 79 with CWFW 0 / 5 / 5. Dialogue turns: reader 27; A4E 40, CWFW 0; without the rule 42 / 43 / 42 with CWFW 2 / 0 / 1. Offered 16 + 13, all read back, used only after a yes; traps: 0 errors added; NO-HARM 6 / 6 identical, applied 0.
- Negatives kept: Part R not exercisable (the design's stock-dense real sentences do not exist in that number; same rarity as USE-1); reader v1.1 itself read 5 of 128 AI-written singles wrongly and saved 3 (FLAG_FOR_HUMAN_REVIEW; a reader defect to diagnose on the spent exam by a builder or the custodian).
- Session gap: the launching session ended after the download and controller cleanup (05:56Z); this session finished the independent and direct cleanup checks, I-checks (15 / 15), seal confirm (unchanged), reading and closeout about 15 h later. One closeout assertion widened for an instance AWS no longer lists (disclosed; original script kept).
- Charge 0.22 USD (list 0.215577; cautious 0.27); ledger 112.99 -> 114.49 (hold) -> 113.21 of 200 (unreserved 86.79); cleanup VERIFIED three ways.
- Files: Documents/Codex/2026-10-19/ctt2r/run_c49_ctt2r_20261020/ (RUN_RESULT_CTT2R_C49.md, CTT2R_READING.json 002ac7fb...); copies docs/working/ctt2r/; backup D:/tksCAS-archive/ctt2r_c49_20261020/ (three hash passes). Hub: scorecard row 7.95, home status strip, build page; site rebuilt.

## 2026-10-20 PDT - HELM-R1 wave 6 RESEALED v3 for the K4 re-run (spec sheet 7.93 follow-up; amendment A-R1W6-2): SEALED, NOT LAUNCHED; owner pre-approved "FIX K4 at 1 USD"; no status changed; 0 USD

- Why: c48 scored v2 as WIDE_WAVE_NO_GAIN (K4: 1 unexplained ask); the cause was a reader defect ("half as much soda" read as a made-up ingredient), fixed by reader v5 (PR #406). The owner pre-approved ONE re-run: cap 1.00 USD, one attempt + one plumbing retry.
- What changed, and only this: HELM cut at thread head fdf68e0c (only helm_wide_turn.py and test_helm_wide_alongside.py differ from v2's cut); owner line "FIX K4 at 1 USD" (15 bytes); seed bands moved to 1,980-1,989 M (above X6, CTT-2R and USE-1's reservation); the spent X6 exam excluded from the fresh draw (128 REAL + 64 CONV + 64 PAIRW ids; X6's two language files join the text rule). Marks, arms, thresholds and exam sizes unchanged.
- Sealed v3 zip f1b64a5edf0df2b152c867f328c71b3df8640a759836108079590e7959c31b47 (freeze da1ec4d2...). Tests from the sealed extract: wave-6 Ran 28 OK, HELM Ran 192 OK, 194/194 members re-hashed.
- Practice dry run v2 -> v3 (practice data only): K4 unexplained asks 0 -> 0; conversation wrong answers 0 -> 0; English-64 / Faces-64 switch ON = OFF 64/64 score for score; REAL fully learned 100 -> 99 of 106 (bar 96), RIGHT 100 -> 99, WRONG 0 -> 0. Negative kept: reader v5 asks on "1 pint cream and same quantity of milk" (a relative form it does not hold); not tuned.
- v2 (72962342...) is VOID_SPENT; X6 is spent; the c48 reading stands. Approval record v3 APPROVAL_RECORD_R1W6.json 4054cfd6... (by program; seed source 430df5a9...).
- Files: Documents/Codex/2026-10-19/r1_wave6/ (PREREGISTRATION_R1W6.md section 17 + D-W6-17, TEST_RECORD_R1W6.md, LAUNCH_BRIEF_R1W6_20261019.md, CUSTODIAN_PROCEDURE_R1W6.md v3); copies docs/working/r1_wave6/; backup D:/tksCAS-archive/r1_wave6_v3_20261020/ (three hash passes). Next: custodian draws X6v3, then the operator runs it.

## 2026-10-19 PDT - USE-1 StackExchange Cooking fetched, pinned and counted (owner word "FETCH STACKEXCHANGE"; spec sheet 7.94): verdict SHORT; USE-1 stops at the census; 0 USD

- Dump: archive.org cooking.stackexchange.com.7z, 87,555,311 bytes, sha256 de98b85f9807a23dfc8c91006f8b59b2149089e94ea9d54676d215ea156a9ac6, sha1 matches the publisher's list; CC BY-SA (4.0 / 3.0 / 2.5 by item date), attribution kept per item.
- Counted with the frozen rules (K-S two keys from the sealed X-REAL zip, reader v1.1, first-person stock shape, no recipe talk, no instructions): 899,195 sentences; 15 first-person stock statements (0.174 per 10,000); reader gives up on 9 (0.104), reads 6 (0.069). "Made / baked" + food 1,139 (13.189 per 10,000), reported only.
- Floor 256 (4 x 64 stock cells): SHORT. With the X-REAL frame, at most 31 stock / 11 reader-gives-up vs the design's STOP rules 32 / 12. No package, no seed, no sign request.
- Next per the owner's picks: the stock stratum goes to human-written sentences; never a looser key; no WildChat.
- Pins: use1/SOURCES_PINNED_C1.json; x_real/SOURCES_PINNED.json created new as an index (sealed pins unchanged, group C1 appended).
- Files: Documents/Codex/2026-10-19/use1/ (COUNT_REPORT_C1.md); copies docs/working/use1/ (counts and ids only); backup D:/tksCAS-archive/use1_20261019/.

## 2026-10-20 PDT - HELM-R1 wave 6 K4 cause found (spec sheet 7.93 follow-up): reader defect, fix built (wide reader v5), NOT re-tested, status unchanged; 0 USD

- Cause: X6_REAL recipe RW:pg:42450@476327 (cake), turn 7. The wide reader read "and half as much soda" as 1/2 (no unit) of a made-up ingredient "as much soda"; it never ran out, so its requirement stayed unlearned (gate G1) and HELM asked. Replayed on the laptop on the sealed v2 code: identical to the host record. UNSETTLED_ASK not involved.
- X6 is spent; KEYS_REAL_X6.json (312fb350...) and INPUTS_REAL_X6.json (7017fabe...) opened after scoring for this diagnosis only.
- Fix: helm_wide_turn.py reader v5 keeps a relative amount ("half as much X", "twice as much X", "as much X", "the same amount of X") as ONE bundled line with the line before it (exact by construction); any form it cannot hold asks AMOUNT_RELATIVE. 5 regression tests on own practice recipes (scones, biscuits) in test_helm_wide_alongside.py. HELM suites Ran 192 OK (was 187); test_helm_chat_nuance / memory / agentic_planner exit 0.
- Status unchanged: WIDE_WAVE_NO_GAIN stands. Re-run needs a new seal v3 on a fresh custodian draw, a new owner word, cap 1 USD.
- Files: Documents/Codex/2026-10-19/r1_wave6/run_c48_r1w6_20261020/DIAGNOSIS_K4.md (+ diagnosis_k4/); copy docs/working/r1_wave6/DIAGNOSIS_K4_C48.md.

## 2026-10-20 PDT - HELM-R1 wave 6 "PAIR WAVE" SCORED (job c48, spec sheet 7.93): verdict PASS, status word WIDE_WAVE_NO_GAIN (K4 missed: 1 unexplained ask); no move; 0.02 USD

- The wide recipe brain switched on with every other HELM part (cube store, English reader, triad, voice, EYE_SCAN, EYE_PAIRING) plus UNSETTLED_ASK, on the custodian-sealed X6 exam (manifest 4d81abff...). One m6i.xlarge (i-06ac5186ff7df015c), 77 of 77 units exit 0, one attempt, 0 retries.
- Did no harm: 0 items lost on X6_E64, X6_F64, X6_PAIR A/B/C, next to each Eye, in conversation (X6_CONV) and on REPRO_X5 (= c40).
- X6_REAL (128 fresh real recipes): FULL+WIDE fully learned 97 of 101 (bar 91), RIGHT 96, WRONG 0, wrong lessons 0; unexplained asks 1 (K4 needs 0; also 1 with the caution rule off). K5 adapted 1 of 12 same-name answered (limit 2); literal 4 of 18 UNDETERMINED (reported).
- X6_CONV: WIDE arms 38 right / 0 wrong / 26 asks vs FULL 30 / 0 / 34; without the triad 7 wrong (reported). X6_PAIRW backlog: FULL 25.16%, FULL+WIDE 35.10%, FULL+EYE_PAIRING 59.94%, FULL+WIDE+EYE_PAIRING 67.42%.
- Pair words (if read) WIDE x CUBE_STORE / ENGLISH_IN / TRIAD / EYE_PAIRING all ADDITIVE; WIDE x VOICE and x EYE_SCAN NOT_EXERCISED_BY_CONSTRUCTION. Eye writes 0, guard trips 0, false alarms 0.
- No move: RB-W1 v3 stays the c47 canonical-brain candidate; the licensed brain stays canonical. Claim ceiling SYNTHETIC_ONLY.
- Reading R1_W6_READING.json 8fa07631ae89db38cae5ea9da84ca6ebebfbeb6b282385eee74021ffb326ad97 (frozen reader from a fresh extract of zip 72962342...). Charge 0.02 USD (cautious 0.04); ledger 112.97 -> 113.97 -> 112.99 of 200; cleanup VERIFIED three ways.
- Files: Documents/Codex/2026-10-19/r1_wave6/run_c48_r1w6_20261020/; copies docs/working/r1_wave6/RUN_RESULT_R1W6_C48.md and R1_W6_READING_C48.json; backup D:/tksCAS-archive/r1_wave6_c48_20261020/.

## 2026-10-20 PDT - HELM Hub: "wave" and "pair wave" defined (owner: "What is a pair wave?"): dictionary entries Wave (HELM-R1 wave) and Pair wave (HELM-R1 wave 6) (454 -> 456); both added to the jargon lint, so every page explains them on first use; scorecard row for 7.91; 21 tests OK; site rebuilt; docs only, no status changed; 0 USD

## 2026-10-19 PDT - CTT-2R packet SEALED, NOT LAUNCHED (spec sheet 7.92): the ACCEPT-2 acceptance rule on the unchanged c45 weights; owner pre-approved "CTT RULE TEST at 1.50 USD"; 0 USD

- Rule: reader v1.1 first; where it would ask, a translator reading is OFFERED only when all three c45 copies give the identical checked reading, read back as a question (topics too), used only after a yes; at most 2 offers per dialogue, silent after a no. Confident-wrong cap stays 2 / 0 saved.
- Arms: A0 reader v1.1, A4E (vote), A2E copy-closest under the same rule (mechanism-free baseline), A4 as run (no rule), C2E (untrained, free); C1E not run (rule-only).
- Exams (custodian, builder blind): Part R 128 real public sentences (R1 = 48 stock-dense the reader gives up on), Part K 128 LLM-written singles (32 trap sentences, keys frozen first) + 16 dialogues from a NEW custodian-only pool; I-REACH turns a no-room part into INCONCLUSIVE.
- Zip d97a16d6683b41037b51d028bcc4776be86ae1db66b117bd2af0126bab6159b6, freeze 7cccf18e..., approval record 37f8c601... (by program); 56 tests OK from the sealed extract.
- Practice census (builder-allowed): R1 likely below 24 on the exam frame, so the custodian census is expected to STOP Part R before any spend; the coordinator chooses widen-frame (new design) or Part K only.
- Files: Documents/Codex/2026-10-19/ctt2r/; copies docs/working/ctt2r/; backup D:/tksCAS-archive/ctt2r_20261019/.

## 2026-10-20 PDT - HELM Hub additions (owner): glossary gains CTT, CTT-1, CTT-2R, the CTT exams and Ears / mouth (dictionary 449 -> 454 entries; CTT added to the jargon lint); new pages build.html (the build, animated: today vs intended, colored by recorded status, still without scripts or with reduced motion) and files.html (every key path with exists check, size and sha256; sealed exams named, never opened; key files by path only); 20 tests OK; site rebuilt; docs only, no status changed; 0 USD

## 2026-10-20 PDT - HELM-R1 wave 6 RESEALED v2 after FIX FIRST (spec sheet 7.91 amendment A-R1W6-1); NOT LAUNCHED; 0 USD

- HELM fixed first (PR #400, merge 221cab70, RB-W1 v4): face / purpose clauses in wide stock sentences asked about; triad faces on wide ingredients respected (ask); restated units converted or asked; stale amounts withdrawn; helm_chat crash on a wide teaching turn fixed (helm_english_in.quantities_said) with a regression test; test_helm_wide_alongside.py 10 tests (9 fail on v3); HELM suites 187 OK.
- Package v2: own HELM cut (helm_now/, 159 files); harness workaround removed; WIDE x VOICE / EYE_SCAN NOT_EXERCISED_BY_CONSTRUCTION; K5 adaptation recorded as A-R1W6-1.
- Zip 729623429832c5fa99141d96876434d9ebed7417055c87173e7a582b3677be0a, freeze 83983cd4..., FROZEN afe9600d...; approval record 5187cb7c... (same pinned line PAIR WAVE at 1 USD, cap 1.00 USD); suites 27 + 187 OK from the sealed extract. v1 f307bdbc VOID (never launched).
- Practice before -> after: conversation wrong answers 23 -> 0 (RIGHT_AND_PLAIN 32 -> 38); English-64 / Faces-64 switch ON = OFF 64/64; real recipes 100/106 learned, 0 wrong; every mark met on practice.

## 2026-10-19 PDT - HELM-R1 wave 6 "PAIR WAVE" packet SEALED, NOT LAUNCHED (spec sheet 7.91); owner pre-approved "PAIR WAVE at 1 USD"; 0 USD

- The wide recipe brain (WIDE_BRAIN switch, licensed reader first) with every wave-5 part on (cube store, English reader, triad, voice, EYE_SCAN, EYE_PAIRING) plus the new UNSETTLED_ASK caution rule (ask when a recipe names one ingredient on two lines).
- Exams (custodian, builder blind): X6_E64 / X6_F64, X6_PAIR, X6_PAIRW (K7 = a real recipe), X6_REAL (128 real recipes), X6_CONV (64 multi-turn dialogues), REPRO_X5; 77 host units; six pair words.
- Zip f307bdbc51210b87d413b5adb834183f3404ce4da5ac6d37ce23873909d7c9e1, freeze 1b8943c6..., FROZEN da00f949...; approval record 271ee619... (by program); suites 25 + 177 OK from the sealed extract.
- Practice dry run (73 units, 287 s): X6_REAL 100/106 learned, 0 wrong, same-name recipes answered 0/8; X6_CONV FULL+WIDE 23 WRONG vs FULL 0 -> forecast WIDE_WAVE_HARMED (mark NH-CONV, D-W6-13).
- FLAG_FOR_HUMAN_REVIEW: helm_english_in.quantities_said raises KeyError on a wide reading; helm_chat._recipe_turn would crash on a wide teaching turn (worked around in the exam harness only).
- Files: Documents/Codex/2026-10-19/r1_wave6/; copies docs/working/r1_wave6/; backup D:/tksCAS-archive/r1_wave6_20261019/.

## 2026-10-19 PDT - HELM Hub: a living, static info site (12 pages + demo copy) generated by `python helm_hub/build_hub.py` from the spec sheet, dictionary, roadmap correction, CHANGELOG, run records and ledger totals; jargon lint, link check, secret scan and page contract all PASS; 13 tests OK; not deployed publicly (owner + IP-attorney decision); docs only, no status changed; laptop, 0 USD

## 2026-10-20 PDT - CTT-1 SCORED (job c45, one g5.xlarge GPU, v3 package; spec sheet 7.90): primary PASS / EARS_NO_GAIN; LLM_WRITTEN pass FAILURE / EARS_HARMED (H-CWFW); 1.40 USD

- The A-CTT-2 fix worked: the GPU smoke test that stopped c43 passed (66 tests OK, translator audit clean); all six models trained (9,585,566 x5 incl. controls, 2,482,718 twin; asserted).
- Primary (E-MACHINE-S, 128 real public sentences, 119 scored): RIGHT reader alone 107, reader + translator 106 / 106 / 105, retrieval 105, shuffled 106, frozen 106. All hard gates true; marks missed -> EARS_NO_GAIN.
- LLM_WRITTEN (gemini-3.5-flash served as gemini-3.6-flash + deepseek-chat; no human, no Claude writer): singles reader 72 -> translator 94 / 87 / 86; dialogues 34 -> 44 / 43 / 39; marks held, but confident well-formed wrong proposals 2 / 5 / 3 vs cap 2 -> FAILURE, EARS_HARMED. Saved wrong 0 in every arm.
- NO-HARM: six old wave exams identical OFF / OFF-removed / ON per seed (6 of 6). Separation and no-foreign gates pass.
- Instance i-0e8770f343f394444, 01:52-03:09 UTC; charge 1.40 (cautious 1.50); ledger 111.55 -> 112.97 / 200 (c46/c47 +0.02 in between); cleanup VERIFIED three ways; backup D:\tksCAS-archive\ctt1_c45_20261020\ (three passes match, weights included).
- Claim status stays ENGINEERED-NOT-VALIDATED. Artifacts: Documents\Codex\2026-10-19\cas_token_transformer\run_c45_ctt1_20261020\RUN_RESULT_CTT1_C45.md.

## 2026-10-20 PDT - RB-W1T v3 SCORED (job c47, AWS; spec sheet 7.89): reader PASS, status word WIDE_BRAIN_EARNED_KEEP; RB-W1 v3 = canonical-brain CANDIDATE (licensed brain stays canonical); 0.01 USD

- Frozen reader rbw1t/merge_rbw1t.py on the c47 host output: RBW1T_READING.json cea8b111...; every instrument row and hard gate true; K1 met (fully learned 92 of 96, bar 87), K3, K4, NH-OFF, NH-ON met.
- WIDE: RIGHT 93, WRONG 0; lessons 576 learned / 0 wrong / 96 not learned (of 672); unexplained asks 0; answered 19 of the 23 UNDETERMINED-keyed recipes (reported only, a caution). LICENSED, ALWAYS_ASK, learning-off control: 0 RIGHT, 0 WRONG.
- No harm: 0 lost on English-64 / Faces-64 (practice and spent X5); OFF = base and ON = OFF 64/64 each.
- Licensed (PREREGISTRATION_RBW1T section 12): RB-W1 v3 is HELM's canonical-brain CANDIDATE, VALIDATED for the section 12 sentence only, ceiling NAMED_CORPORA_ONLY; stays a candidate pending a wave with the switches. The c46 negative (v2 build, 90/110) stands.
- Job: i-05c1537e90f0636d3 m6i.large us-west-2b, 03:00:44 -> 03:03:02 UTC, host 149.46 s, one attempt; own prefix (c45 holds the shared one, never touched). Charge 0.01 USD (cautious 0.02); ledger 119.35 -> 120.35 -> 119.36 of 200; cleanup VERIFIED three ways (controller, independent, direct look).
- Files: Documents/Codex/2026-10-19/rbw1t/run_c47_rbw1t_v3_20261020/ (RUN_RESULT_RBW1T_V3_C47.md); repo copies docs/working/rbw1t/RUN_RESULT_RBW1T_V3_C47.md, RBW1T_READING_C47.json; backup D:/tksCAS-archive/rbw1t_v3_c47_20261020/ (922 files, three hash passes).

## 2026-10-20 PDT - RB-W1T RESEALED as v3 (amendment A-RBW1T-2; spec sheet 7.88 note); SEALED, NOT LAUNCHED; nothing scored; 0 USD

Owner pre-approval (verbatim, pinned 20 bytes, sha256 fd82691e...): "WIDE TEST 2 at 1 USD"; cap 1.00 USD, one attempt + one plumbing retry.

- v3 zip 3a8ae37eb51c18414bfa83a71b9079dd7ec2282bec6ba3952d86ac0454f0e967, freeze 04eef886...; APPROVAL_RECORD_RBW1T.json (v3) 954c7364...; seed source sha256(line + ":" + v3 zip); band RW2 1,952,000,001-1,953,000,000.
- Amendment A-RBW1T-2 written before the reseal: c46 exam SPENT (v2 zip 7c04a408... kept as v2_spent_*); only HELM change = PR #392 merge 65b86282 (three wide files); same preregistration, marks, arms, thresholds.
- Exclusions: X-REAL 128, v2 practice 128, the c46 exam 128 (ids only, from the c46 host output id field; not in the manifest), practice draw v2 128. Practice v2 shares 3 recipes with c46 (noted; c46 is spent).
- Tests from the sealed zip: 0 bad members of 395; RB-W1T 26 OK; HELM 177 OK (1 skipped); plan check PASS. Dry run (practice mock): WIDE 100/106, RIGHT 101, WRONG 0; NH practice 0 lost.
- Custodian next (separate session): CUSTODIAN_PROCEDURE_RBW1T.md v3 -> rbw1t_custody_v3/; then the operator per LAUNCH_BRIEF v3. Backup D:/tksCAS-archive/rbw1t_v3_20261019/ (three hash passes).

## 2026-10-20 PDT - RB-W1 v3 fix built (dish names, line splitting, ran-out binding, ties); NOT re-tested on a sealed exam; status unchanged (spec sheet 7.88 note); 0 USD

- Diagnosis on a NEW published practice draw (seed text RBW1-DISHNAME-FIX-PRACTICE-V2-20261020-builder-published, PRACTICE_DRAW_V2.json 808cfa2f...): the c46 miss label CLARIFY_ENGLISH_UNKNOWN_PRODUCT is the licensed path's code; the wide reader's own codes showed line splitting (no amount, 18 recipes), units (8), names, ran-out names. Failed approach logged: reading HELM's licensed code as the cause of a wide-path miss.
- Practice v2, before -> after: fully learned 84 -> 100 of 106; RIGHT 85 -> 101; WRONG 0 -> 0; lessons 465/0/205 -> 577/0/93; unexplained asks 1 -> 0; no harm practice E64/F64 ON = OFF 64/64 each; parameter audit clean.
- Built: amounts start lines; names from the line's own words; ran-out phrase inside one line; two-part amounts asked; "1 and a half" = 3/2; packet = package; a tie answers the amount; dish-name variants bind; a missing dish name is asked once, then accepted.
- Tests: test_helm_brain_wide 52 (51 pass; 1 pre-existing failure since a7b1650a, skips on the host); test_helm_end_to_end_loop 18 OK. Files: docs/working/rbw1_fix/.

## 2026-10-19 PDT - RB-W1T SCORED (job c46, one m6i.large; spec sheet 7.88): reader PASS; status word WIDE_LEARNING_DID_NOT_EARN_KEEP; RB-W1 stays ENGINEERED-NOT-VALIDATED; 0.01 USD

Owner pre-approval (verbatim, pinned 18 bytes, sha256 75904654...): "WIDE TEST at 1 USD"; cap 1.00 USD, one attempt + one plumbing retry.

- Package 7c04a40855b81c6bfc5c1a44fc4486e112fcc4bf16bc37b1e84d7b457c6b009e (freeze b22690ce...) verified; manifest 9895fd95...; seed source sha256(line + ":" + zip) = 07b27cdd... = the derivation's input_sha256; exam never opened by the operator.
- Host i-024d15d881ce9982e m6i.large, ami-0dddfa1ffa6b87af7, 02:20:18 -> 02:22:25 UTC; host 148.95 s; HELM suites 170 OK (2 skipped), RB-W1T 24 OK, 21 of 21 units exit 0; one attempt, no retry.
- Reading (frozen rbw1t/merge_rbw1t.py, RBW1T_READING.json 698c2faf...): verdict PASS, every row and gate true; marks K1 false (90 < 99), K3, K4, NH-OFF, NH-ON true.
- WIDE: fully learned 90 / 110; RIGHT 89, WRONG 0; lessons 483 learned, 0 wrong, 168 not learned; unexplained asks 0. LICENSED, ALWAYS_ASK, learning-off control: 0 RIGHT, 0 WRONG.
- Weakest cell: 7-10 ingredients, whole-number amounts, 3 of 10. Largest miss by HELM code: dish name not recognised (CLARIFY_ENGLISH_UNKNOWN_PRODUCT) in 22 recipes, every lesson refused. Failed approach logged: the practice-draw reader fixes (product name 2 -> 0 on practice) did not carry over to fresh recipes.
- No harm: 0 items lost on all 4 files; OFF = base 64/64 each; ON records = OFF records 64/64 each.
- Transport: c45 held the shared prefix, so c46 used its own prefix helm-rbw1t-c46-20261020/ with presigned URLs (recorded deviation; no package change).
- Charge 0.01 USD (cautious 0.02); ledger 119.34 -> 120.34 (hold) -> 119.35 of 200; cleanup VERIFIED three ways; backup D:\tksCAS-archive\rbw1t_c46_20261020\ (three hash passes).

## 2026-10-19 PDT - RB-W1T RESEALED as v2 after "FIX FIRST" (spec sheet 7.86 amended; 7.83 follow-up); RB-W1 v2 built (PR #389); nothing scored; 0 USD

Coordinator decision (operational; owner's standing order "retest broken tests without asking"): do not run a sealed test that practice already shows failing on an instrument defect; fix routing and learning, reseal.

- RB-W1 v2 (PR #389, `045548b6`): the WIDE switch extends the licensed path (licensed first; the wide brain only where the licensed path cannot bind and wrote nothing). Reader fixes from failure classes on the published practice draw.
- Practice (published seed, not an exam), v1 -> v2: WIDE right 54 -> 98, wrong 0 -> 0, fully learned 54 -> 99 of 106 (bar 96); switch ON lost 55 -> 0 (E64) and 42 -> 0 (F64); OFF byte-identical to the base; OFF live trace 139/139 identical.
- Per class (660 lessons), before -> after: ran-out name not in batch 122 -> 3; no amount 85 -> 25 (left: alternatives, vague amounts); no name 75 -> 0; unit not in table 37 -> 45 (true limit); duplicate 10 -> 10 (true limit); product name 2 -> 0.
- v2 zip `7c04a40855b81c6bfc5c1a44fc4486e112fcc4bf16bc37b1e84d7b457c6b009e`, freeze `b22690ce...`; approval record `APPROVAL_RECORD_RBW1T.json` `3a223136...` (owner line as pinned, 18 bytes); v1 `b50f4ca4...` void, never launched. Tests from the zip 24/24 + HELM 170 OK.
- Prediction v2: WIDE_BRAIN_EARNED_KEEP about 0.35. Failed approach logged: v1's switch replaced the whole English path (lost 55 and 42 practice items); v2 routes licensed-first.

## 2026-10-19 PDT - lexicon_v3 (live, switch HELM_LEXICON_V3 default ON): bare female/male/negative/positive/vibration/rhythm and the bare-noun tier (idea, thought, mind, attention, practice, repetition, groove, realization) no longer pick a Noetic; frozen ALIAS-WIDE v1 / lexicon_v2 untouched; tests reader 31->37, new lexicon_v3 15/15, loop 18, stock-frame 17, faces 16, voice 22, cube store 21/21, chat script PASS; practice E64 61/0/3, F64 60/2/2 unchanged item by item; spec sheet 7.81 note, no status change; 0 USD

## 2026-10-19 PDT - CTT-1 RESEALED as v3 (amendment A-CTT-2 after c43's preflight stop; spec sheet 7.82 / 7.85 amended): zip f280633d...; NOT LAUNCHED

Coordinator ruling: instrument defect, fix without changing anything scored. Section 18 of PREREGISTRATION_CTT.md was written before the code change.

- c43 stopped because the translator's write-audit counted torch 2.9.1's own opens of /dev/null (x4) and a temp file as forbidden writes.
- v3 audit rule: the audit log, the null device, the process's own temp folder and torch / CUDA caches are allowed; any write under brain, wave packages, store, receipts, exams, data or weights still fails (even inside temp); network calls, process starts and a missing audit still fail. NO-HARM translator audits are now judged too.
- Exam seed: approval record names PACKAGE v3 f280633da498466fe713b33d37fe90db221bc3dbf4ce9fe69538460be82cee31 and EXAM-SEED v2 83bfa752...; the two sealed exams (manifests 12061e67..., be3895ff...) stay valid; reader, runners and custody tools check the seed against the exam-seed hash.
- Tests from the v3 zip: 66 (65 pass on the laptop, 1 host-only torch audit test skipped there). Freeze 24f89718...; cap 8.00 USD (0.21 spent).
- Backup D:/tksCAS-archive/cas_token_transformer_20261019/ re-copied, three sha256 passes MATCH.
## 2026-10-19 PDT - RTR-1 "RE-TEST READER" SCORED (job c44, one t3.medium; spec sheet 7.87): reader PASS; v1.1 S_SAFE_NOT_USEFUL, v1.0 S_UNSAFE_ON_REAL, FIX_REMOVED_HARM; 0.01 USD

Owner order (verbatim, 68 bytes, sha256 b645e4f4...): "RE-TEST READER" (0.03 USD) and "WIDEN THE BRAIN" (0 USD to build)." Only the RE-TEST READER part; cap 0.10 USD, one attempt + one plumbing retry.

- Package e201feb6e5fd4eaf1d9b9060ed100a9db6150257c2d0b64d230ad81c4042f7a8 (freeze 6a622106...) verified; sealed exam manifest 562dd6ab..., amendment RTR-A1 dceedd34... cited; seed source sha256(line + ":" + zip) = 6f9cb0fd... = the derivation's input_sha256.
- Host i-0d443520810f62063 t3.medium, ami-0dddfa1ffa6b87af7, 01:37:04 -> 01:39:02 UTC; host 151.7 s; tests_rtr 29 OK; reader tests on the v1.1 overlay 119 OK (1 skipped); one attempt, no retry.
- Reading (frozen rtr/merge_rtr.py, RTR_READING.json 6a28751f...): verdict PASS, every row and gate true; I-CTRL 128/128 equal to c42.
- V11 RIGHT 115 / WRONG 0 (of 115 scored); V10 104 / 11 (all EMPTY keys); B-ASK 114 / 0; B-KEYCALC 104 / 6. V11 misses S-b USEFUL (115 < 118).
- Licensed: the English reader's Part-S word moves to S_SAFE_NOT_USEFUL (v1.1), safety half only, NAMED_CORPORA_ONLY; legend status stays ENGINEERED-NOT-VALIDATED. Only 1 FACTS item in the draw, so keeping true facts is not tested.
- Transport: c43 held the shared four-key prefix, so c44 used its own prefix helm-rtr1-c44-20261020/, no instance profile, no SSM, four presigned URLs (recorded deviation; no package change).
- Charge 0.01 USD (cautious 0.01); ledger 111.54 -> 111.64 (hold) -> 111.55 of 200; cleanup VERIFIED three ways; backup D:\tksCAS-archive\rtr1_c44_20261020\ (417 files, three hash passes).

## 2026-10-19 PDT - HELM chat: 4 defects found by HELM UI v0 fixed (owner: "Ok I agree with all 3 cards"): bee reply no longer invents "south of France" (repeats only the user's words; hive-walkthrough branch removed too); `dials` reads the real UnityEyeSupervisor.dial or says "not wired"; session log folder made on first write under helm_ui/sessions or $HELM_SESSION_DIR, never the repo root; two "Before X, Y." sentences now plan synthesize -> verify -> git in both planners (prereq_planner plan_graph.py and helm_agentic_executor.py); tests 43 -> 63 pass on the named suites; 0 USD

## 2026-10-19 PDT - RB-W1T (sealed test of the wide brain) packet SEALED, NOT LAUNCHED (spec sheet 7.86); nothing scored; 0 USD

Owner pre-approval (verbatim): "WIDE TEST at 1 USD" (cap 1.00 USD, one attempt + one plumbing retry; coordinator mapping in `OWNER_APPROVALS_20261018.md`).

- What it tests: RB-W1 (PR #380, `015d340d`) on 128 real recipes drawn blind by a custodian from X-REAL's public frames (2-10 parsed lines; 3 ingredient counts x 3 quantity forms; X-REAL's used 128 and the builder's published practice excluded). One witnessed run-out lesson per ingredient (X-REAL v2), fresh amounts on hand, "How much {N} can we make?"; X-REAL's K-R key (three-valued). Arms: licensed brain, WIDE, WIDE replay, WIDE with learning disabled (control), always-ask. No harm: switch OFF byte-identical to `d4488f2a`, switch ON at most 2 lost, on wave-5 practice and spent X5 English-64 / Faces-64.
- Seed = sha256("WIDE TEST at 1 USD" + ":" + zip sha256), band RW 1,950,000,001-1,951,000,000; custodian only.
- Package: zip `b50f4ca42178d4c43e43945267cc980aebd05a10f8e0d932d00e3eabd4495809`, freeze `fadf08f6faf13ebcdb633b7894ebe515838465c52a90c51f6507f2371a28f8b1`; approval record `APPROVAL_RECORD_RBW1T.json` `97fb18ae...`. Tests from the sealed extract: 23/23 RB-W1T, 154 HELM (1 skipped), plan check PASS.
- Practice dry run (published seed, not an exam): WIDE 54 right, 0 wrong, fully learned 54 of 106 (mark needs 90%); switch ON lost 55 of 64 (E64) and 42 of 64 (F64). Prediction: WIDE_BRAIN_HARMED about 0.85. Finding: the switch replaces the whole English path; meeting the no-harm mark needs a routing change (new build, new seal) - owner/coordinator call.
- Failed approach logged: matching the brain's names to the grammar's HEAD word scored right answers WRONG ("boiling water poured upon the flax-seed" has HEAD "upon"); replaced before the seal by mapping names through the brain's own lesson records (amendment A-W-1).
- Not done: wave-1 GB/TB worlds with the switch ON (no cell-index adapter); X-REAL's pair recipes not excluded (ids only in X-REAL custody).

## 2026-10-19 PDT - Noetic drift fix (docs + one docstring; owner: "Ok I agree with all 3 cards"); no behavior or claim change; 0 USD

- `docs/INCIDENT_CATEGORIES.md` + `docs/AI_MISALIGNMENT_INCIDENTS_DATABASE.md`: 15 retired Noetic names replaced with canonical ones; 4 examples reclassified by the Colloquialism Test (hallucination `^3`->`^6` Male with `^8`->`^9` landing; Boundary Failures `^3`->`^6`), 1 re-checked and kept; full list in "Reconciliation notes 2026-10-19". `helm_chat.py` header now names helm_brain_canonical.py (HELM-R1 recipe brain) as HELM's brain and 22x40 / tks28 as demos (AST identical apart from the docstring; test_helm_chat_nuance 5/5, test_helm_english_in 31/31). Not done: HELM_DISTRIBUTION_PACKAGE/helm_chat.py (outside git and outside this agent's worktree).

## 2026-10-19 PDT - CTT-1 LAUNCHED (job c43, one g5.xlarge GPU) and STOPPED by its own GPU smoke test (spec sheet 7.85); primary word INCONCLUSIVE; nothing scored; 0.21 USD

Owner pre-approval (verbatim): "I PRE-APPROVE BOTH OF THE FOLLOWING:   Two sign lines are coming: X-REAL at 1 USD, and the transformer training at 8 USD." Cap 8.00 USD, one attempt + one plumbing retry.

- Package v2 83bfa752cb109383783614fdb9341b9b4c87349baa40c436141927485f92f7ec verified; payload 15c8bfa0...; i-05cd406380131ee45 g5.xlarge (A10G), ami-0dddfa1ffa6b87af7, us-west-2b; 01:19:32 -> 01:25:49 UTC; host 713.8 s.
- Preflight: 0 refusals; host unit tests Ran 58 OK (skipped=1); static separation PASS; no pretrained files; smoke build and 9-step smoke train exit 0 (loss 3.33422); A4 parameter count 9,585,566 asserted. FAILED: translator-process audit saw torch-internal write-opens (/dev/null x4, /tmp/ks37dli5) -> preflight ok false -> runner exit 3.
- Frozen reader: primary INSTRUMENT_ERROR / INCONCLUSIVE (14 missing result files); LLM_WRITTEN pass (staged under the runner's E_HUMAN_W_* names, NAMING_NOTE bf758ce1...) NOT_RUN; real human pass NOT_RUN.
- Classed CODE (a same-zip retry would repeat it); plumbing retry NOT used. Continuing needs a fixed audit rule, a reseal, and a new owner word.
- Failed approach logged: the operator's controller placeholder check matched `torch.__version__` and stopped 0 s after run_instances; fixed and the same attempt re-attached to the same instance (no second launch).
- Charge 0.21 USD (cautious 0.31); ledger 111.33 -> 119.33 (hold) -> 111.54 of 200; cleanup VERIFIED three ways; backup D:\tksCAS-archive\ctt1_c43_20261020\.

## 2026-10-19 PDT - RTR-1 "RE-TEST READER" packet SEALED, NOT LAUNCHED (spec sheet 7.84); nothing scored; 0 USD

Owner order (verbatim): "RE-TEST READER" (0.03 USD). Coordinator mapping: cap 0.10 USD, one attempt + one plumbing retry.

- Question: does the fixed English reader (v1.1, PR #378, rule 6 STOCK_FRAME_REQUIRED) write only what 128 fresh real sentences say? Old reader v1.0 (X-REAL c42's copy) runs on the same draw as a control; rivals always-ask and keyword reader.
- Exam: custodian draw of 128 (32 per stratum) from X-REAL's Part S frame 98c2fb8f..., excluding X-REAL's 128 and CTT's primary 128 (0 overlap gate by id and text hash); X-REAL's key rule K-S (keys A and B) and Part S marks/words unchanged; S-e NOT_EXERCISED.
- Seed: sha256(owner line + ":" + zip sha256); band RS 1,940,000,001-1,941,000,000 above X-REAL and all CTT bands (incl. LLM_WRITTEN LW-S/LW-D).
- Package: HELM_RTR1_20261019_SOURCE_RTR1.zip e201feb6e5fd4eaf1d9b9060ed100a9db6150257c2d0b64d230ad81c4042f7a8, freeze 6a622106...; X-REAL and waves 4/3b/3/1 imported as sealed neighbours, never edited. Reader v1.1 runs from a pinned overlay copy of wave 3's helm/ with only the 4 PR files swapped.
- Tests from the zip: tests_rtr 29/29, reader tests on the overlay 119/119; stage runner exercised locally on mock carriers; mock end-to-end custody -> pool -> reader PASS on practice-partition sentences with patched pins.
- Failed approaches logged: (1) a seed-rule test assumed one used seed inside the band only blocks one slot; with the 1,000,000 gap it blocks the whole band (correct STOP); test rewritten. (2) The first identity check matched the substring '/overlay/helm/'; replaced by the unit's recorded overlay folder.
- Builder exposure recorded: 3 public frame rows printed (excluded as BUILDER_SEEN); no X-REAL or CTT exam file opened.
- Next: custodian draw (needs CTT's primary exam sealed), then one t3.medium run.

## 2026-10-19 PDT - RB-W1 WIDE BRAIN BUILT behind switch WIDE_BRAIN (default OFF), NOT tested on a sealed exam (spec sheet 7.83); claim status ENGINEERED-NOT-VALIDATED; licensed brain unchanged; 0 USD

Owner order (verbatim): "WIDEN THE BRAIN" (0 USD to build). Input: recipe shape survey v1 (1 of 13,686 real recipes fit the licensed brain).

- New `helm_brain_wide.py` (brain, exact numbers, unit table, parameter accounting) and `helm_wide_turn.py` (reader, voice, live-loop turn). Switch in `helm_end_to_end_loop.py`: `HELMEndToEndLoop(wide_brain=True)` or env `HELM_WIDE_BRAIN=1`; OFF never imports the wide modules.
- Stage 1: exact Fractions end to end (thirds, mixed numbers, unicode fractions, number words); floats refused; ranges and "about" asked. Unit table = survey top 20; 9 named exact factors (TSP_PER_TBSP 3, TBSP_PER_CUP 16, CUP_PER_PINT 2, PINT_PER_QUART 2, GILL_PER_PINT 4, ML_PER_TSP 4.92892159375, G_PER_OZ 28.349523125, OZ_PER_LB 16, G_PER_KG 1000); 9 units with no exact standard stay their own count unit; no volume <-> weight.
- Stage 2: open ingredient names, any product name, up to 10 ingredients. A recipe is added only by an admitted witnessed batch; a coefficient only from a batch where that ingredient alone ran out (same rule as the licensed writer: a = stock / made). Strict memory check (0 allowed; the licensed writer allows 1). Unlearned -> UNDETERMINED, the brain asks.
- Tests: `test_helm_brain_wide.py` 35/35 (round trips on 2,112 fractions; unit conversions; 6-ingredient recipe learned exactly in 6 lessons, any order; refusals for nothing-ran-out and two-ran-out; UNDETERMINED on unlearned; parameter table printed, no other learned numbers; live loop ON end to end). Existing suites OFF 119/119. Wave-5 practice tests 14/14 (read-only). OFF live trace 139/139 records identical to d4488f2a.
- Coverage if ON (survey estimate, not measured): 9,495 of 13,686 recipes representable (69.38%); each still needs one run-out lesson per ingredient.
- Failed approach logged: first wiring crashed because the loop's bias digest reads `brain.brain.learned_digest()` (the licensed adapter wraps its brain); fixed with a read-only `brain` property on the wide book.
- Sealed test: needs an owner word with a package hash and a cap.

## 2026-10-19 PDT - CTT-1 RESEALED as v2 (amendment A-CTT-1, spec sheet 7.82 amended): primary word from the machine-side exam; human exam optional later pass; zip 83bfa752...; NOT LAUNCHED

Coordinator decision (operational): the run must not block on human writers. v1 zip 3289755c... VOID_SUPERSEDED_BY_V2 (never launched).

- Primary exam E-MACHINE-S: 128 real sentences (Tatoeba, Taskmaster user turns) from X-REAL's Part S frame, X-REAL's 128 used items excluded, drawn blind by the custodian (custody/draw_machine.py, band CM 1,924,000,001-1,925,000,000, seed from owner line + ":" + zip sha256), keyed by X-REAL's frozen K-S rule. Same gates and thresholds; marks M-A1-M-A3; M-A4 NOT_EXERCISED (no dialogues).
- Human exam E-HUMAN-W: optional, later, same frozen weights (kit/run_ctt_human.py, merge_ctt --pass human), own status line, never changes the primary; HUMAN_EXAM_ABSENT = NOT_RUN, fails nothing.
- What depended on the human exam in v1: M-A1-M-A4, H-CWFW, H-RT(b), H-READBACK, the saved-wrong part of H-WRITE, H-LEN, H-CUSTODY.
- Zip 83bfa752cb109383783614fdb9341b9b4c87349baa40c436141927485f92f7ec, freeze c07654e7...; APPROVAL_RECORD_CTT.md v2 (owner pre-approval line + new hash); cap 8.00 USD, one attempt + one plumbing retry. Tests 58/58 from the zips.
- Flags: governance (owner pick Q7 put the claim on human English; the coordinator moved the primary word; the owner may reverse). Custody slip named: real_heldout_unparseables_98.jsonl (sealed 98, commit ec780a34), first 400 characters of row 1, gold not printed; E-NOTATION reported only.
- Backup D:/tksCAS-archive/cas_token_transformer_20261019/ re-copied, three sha256 passes MATCH.
## 2026-10-19 PDT - English reader stock-frame fix BUILT after X-REAL c42 (spec sheet 7.81 follow-up); NOT re-tested on a sealed exam; no status change

- What broke: on real sentences HELM saved stock facts the sentence never stated (an ingredient word was read as a stock statement).
- Fix (rule 6 `STOCK_FRAME_REQUIRED`, `helm_english_in.py` v1.1): stock or "none on hand" is saved only when a stock frame holds the ingredient ("we have", "there is/are", "our pantry has", "we're out of", "we don't have any", or a plain inventory list). Otherwise HELM asks one question (`NO_STOCK_FRAME`) or, when the sentence is not about our kitchen, says "I don't have anything to save from that. Nothing was saved." (`NOTHING_TO_SAVE`, zero cubes). Frames ride beside the checked form, render back, and the loop re-checks them before writing.
- Built from the failure class only; no sealed exam item opened. Builder-written practice: 56 negatives (old reader wrote on 25, new 0), 47 positives (all still written), 16 ask cases (old wrote on 13, new 0).
- Tests: 102 -> 119 unittest OK (17 new in `test_helm_english_in_stock_frame.py`); chat nuance script 21 PASS lines before and after; wave-5 TestLiveHook OK; practice English-64/Faces-64 (wave 5 and wave 3b) identical counts and records with the new reader swapped in.
- Failed approach logged: the first frame rule missed labeled lists ("Stock check: ...") and dropped 3 practice English-64 answers; fixed with a list-label rule, then counts matched.
- Status: English reader stays ENGINEERED-NOT-VALIDATED; S_UNSAFE_ON_REAL stays. Re-test needs a fresh custodian draw (~0.03 USD) and an owner word.

## 2026-10-19 PDT - CTT-1 CAS-token transformer ("ears first") PACKET SEALED, NOT LAUNCHED (spec sheet 7.82): separate from-scratch translator, reader first, HELM's checker decides; main 9,585,566 / twin 2,482,718 parameters; cap 8.00 USD pre-approved; waits for the human exam

Owner order (verbatim): ""SCORE L4"; I WANT THIS BUILT AND TRAINED I'M LIFTING THE GPU DIRECTIVE:  Documents\Codex\2026-10-19\cas_token_transformer_design_v1\;". Owner pre-approval (verbatim): "I PRE-APPROVE BOTH OF THE FOLLOWING:   Two sign lines are coming: X-REAL at 1 USD, and the transformer training at 8 USD." Bound to the sealed zip by APPROVAL_RECORD_CTT.md (coordinator's custody addition: exam seed = sha256(line + ":" + zip sha256)).

- Package HELM_CTT_20261019_SOURCE_CTT.zip 3289755c154111ce41e44bf4d17f4f6bfa14e0dff1f91d287bd5b6c74a5453ec, freeze 4dd5fe86..., deps carrier fc89054a...; preregistration pre-code copy 05c99a7e... written before any code (sections 0-15 unchanged; 12 dated deviations in section 16).
- What it trains: an encoder-decoder from scratch, 9,585,566 parameters (3 seeds), twin 2,482,718 (deviation: width 128, because the design's width-192 twin would be 4,764,382), shuffled-pairs and frozen-at-init controls. Vocabulary 8,349 = 341 CAS tokens (both compilers' token kinds, meta-logic and fractal nesting tags, tested) + 8,000 English word-pieces built from our own inputs. Copy head points at the user's own numbers and words; no digits or names on the output side.
- Data (built on the host from frozen seeds): 200,000 generated kitchen turns (content first), about 30,000 SDG notation rows, 7 trace rows, about 1,950 Tatoeba practice inputs (input only). Leakage drops against every exam, counts only.
- Tests: E-HUMAN-W (128 turns + 16 dialogues written by the owner and two people, custodian-sealed, builder blind) carries the claim; sealed 98 reported only; NO-HARM on the six spent wave exams OFF / OFF-deleted / ON. Gates include H-CWFW (confident well-formed wrong: <= 2 proposed, 0 saved) and H-LEN (0 truncations), from the Scribe c41 lesson (0 of 98, 21 well-formed wrong, 97 cut).
- Tests from the sealed zips: 50/50 OK on the laptop, no torch. Laptop harness checks: OFF reproduces c40 and c38 (wave 3b's same-brain projection); a fake always-ask proposer leaves every digest equal; a fake topic proposer changes it.
- Could not do: no local GPU smoke (torch alone 475 MiB > 300 MiB per-process limit; free RAM about 750 MB), so the torch code first runs in the AWS preflight. Taskmaster-1 not used (file size vs laptop limit).
- Failed approaches / slips: the design's twin shape did not match its size (fixed by keeping the size); receipt hashes differ across hosts (path inside), so the cross-host same-brain check uses wave 3b's projection; custody slip disclosed: the builder printed the first 400 characters of row 1 of the sealed 98 (English only, no gold) - FLAG_FOR_HUMAN_REVIEW.
- Backup D:/tksCAS-archive/cas_token_transformer_20261019/ (three sha256 passes). Repo copies docs/working/cas_token_transformer/.

## 2026-10-19 PDT - HELM-R1 X-REAL SCORED (job c42, AWS, spec sheet 7.81): reader PASS; S_UNSAFE_ON_REAL (8 wrong writes on real sentences), R-REBOUND R_SAFE_NOT_CORRECT (0 wrong, 3 of 64 answered), R-ASIS R_ASIS_SAFE; Eye scan caught D1 and E1 only, the plain checksum caught more

Owner pre-approval (verbatim): "I PRE-APPROVE BOTH OF THE FOLLOWING:   Two sign lines are coming: X-REAL at 1 USD, and the transformer training at 8 USD." Only the X-REAL line used. Launch operator: Claude Code sub-agent.

- Package a9b4c954... (freeze 67b48541..., 53 of 53 re-hashed); seed source sha256(line + ":" + zip sha256) = 2af8c199... = custodian derivation; manifest 1e535511...; exam files never opened by the operator.
- Job helm-claude-xreal-20261019-c42: one m6i.xlarge i-0decaa7956027896c, 5:06-5:14 PM Pacific, host 462.1 s, pool 23/23 exit 0, host tests 359 OK; one attempt, 0 plumbing retries.
- Reading 79b6ea30...: every instrument row and hard gate true. S FULL 101 RIGHT / 8 WRONG of 109 (B-ASK 102/0, B-KEYCALC 95/5). R-REBOUND 3/0/61 asked of 64 (3 of 3 answers exact). R-ASIS 25/0/13 of 38; census 1 of 13,686.
- Part F: Eye scan CAUGHT D1 16/16, E1 16/16; T1, S1 silent-harmless; T2, E2a failed loud; E2b, C1 kept. Checksum CAUGHT T1, S1, D1, E1 and was over-cautious on E2b. 0 false alarms. No kind beyond the checksum (the designer's headline held).
- Sensitivity (coordinator): without the 4 items also in the published answerability draw, R-REBOUND 3/0/58 of 61 and R-ASIS 25/0/12 of 37; same words. Custodian flag carried forward. Operator flag: F-b ACTED holds vacuously (0 caught worlds touched by the probe).
- Charge 0.03 USD (cautious 0.06; cap 1.00). Ledger 111.30 -> 112.30 (hold) -> 111.33 of 200. Cleanup VERIFIED three ways (proof 314af7ec...). Backup D:/tksCAS-archive/x_real_c42_20261019/.
- Failed approaches: none this run. Negative results recorded: English reader unsafe on real sentences; recipe brain answers almost nothing on real recipes; Eye scan misses tail loss and stale backups a checksum catches.

## 2026-10-19 PDT - HELM-R1 X-REAL RESEALED as v2 (spec sheet 7.79 amended): recipe parts rebuilt so they are not vacuous; zip a9b4c954...; owner pre-approval bound; NOT LAUNCHED

Coordinator decision (operational, not the owner's): do not ship a part known to be vacuous. v1 c275daed (never signed) is VOID_SUPERSEDED_BY_V2.

- Pairing all ingredients: B holds every ingredient of A once, same unit form, from the whole recipe frame (R-REBOUND frame 1,122 of 1,728 eligible).
- One witnessed lesson per ingredient, the others at 2x their listed amount, so one ingredient really runs out first; the brain is not changed. Practice: 15 of 16 recipes every ingredient learned (30/30 exact); the 16th uses 1/3 (not exactly holdable).
- Answerability on the published practice seed text XREAL-ANSWERABILITY-20261019-published-practice-seed: 64 of 64 drawn R-REBOUND items answerable (need 48). R_VACUOUS guard kept. Sentence and fault parts unchanged.
- Owner pre-approval (verbatim): "I PRE-APPROVE BOTH OF THE FOLLOWING:   Two sign lines are coming: X-REAL at 1 USD, and the transformer training at 8 USD." APPROVAL_RECORD_XREAL.md binds it to zip a9b4c9547e7276412a95141d24eb38d7d44ca3d539e8ff095abe727cf4e1c249 (freeze 67b48541...), cap 1.00 USD. Seed source = sha256(line + ":" + full zip sha256).
- Slips recorded in the preregistration: the first download's User-Agent held the owner's e-mail (inline curl helper; later requests neutral; the sealed fetch script is test-checked); a git worktree prune was refused by Windows (nothing deleted).
- Tests from the final seal: 359 OK. Backup D:/tksCAS-archive/x_real_20261019/v2/.
## 2026-10-19 PDT - Scribe L4 (old small English model) SCORED on the sealed 98 (job c41, AWS, spec sheet 7.80): exact 0 of 98 as predicted, CLARIFY 77, and 21 confident answers that pass the real CCE round trip and are all wrong; ENGINEERED-NOT-VALIDATED stays

Owner words (verbatim): "SCORE L4" — mapped by the coordinator to the plan line APPROVE SCORE_SCRIBE_L4_SEALED_98 (approval record 5a35f3ba...). Launch operator: Claude Code sub-agent.

- Plan docs/working/scribe_l4_eval/SCORE_SCRIBE_L4_PLAN.md (18e350f5...) followed as written; sealed package SCRIBE_L4_AWS_GPU_PACKAGE.zip 7179250c... = its PACKAGE_FREEZE.json; laptop adapter tests 6/6 OK.
- Job helm-claude-scribe-l4-score-20261019-c41: one t3.medium i-085092855ef75f1b8 (AL2023, CPU torch 2.14.1+cpu), 4:39-4:41 PM Pacific, host 149.6 s, one attempt, 0 plumbing retries.
- Counts (receipt f283d383...): rows 98; exact_match_gold 0; clarify 77; answer 21; cce_round_trip_ok 21; answered_round_trip_ok_but_not_gold 21; shim_round_trip_ok 16; truncated_over_30_words 97; words 4,899, known 1,571; sealed sha256 unchanged.
- Charge 0.01 USD (cautious 0.01; cap 0.10). Ledger 111.29 -> 111.39 (hold) -> 111.30 of 200. Cleanup VERIFIED three ways (proof 1eec80c6...).
- Failed approaches: none this run. Lesson recorded: a round-trip check alone is not a correctness gate.

## 2026-10-19 PDT - HELM-R1 X-REAL packet SEALED, NOT LAUNCHED (spec sheet 7.79): the first exam from other people's text (real food sentences, real cookbook recipes, real kinds of file damage); nothing scored, no claim

Owner word (verbatim): " "FETCH X-REAL"" (design picks Q1-Q8 accepted; the SOURCES.md downloads allowed). Builder: Claude (X-REAL builder session). 0 USD, laptop only; downloads were the only network use.

- Fetched and pinned (SOURCES_PINNED.json 24cfb0d1...): PG catalog + 281 English "Cooking" eBooks (the LoC heading "Cookery" is now "Cooking"; eBook 1979 excluded, header says COPYRIGHTED); English Wikibooks dump 20261001 (Wikimedia sha1 matched); Tatoeba English export; Google Taskmaster at commit d92cb6af (13 files). SKIPPED with reason: USDA SR Legacy list, ftfy release, Tatoeba CC0 list (no exact URL in SOURCES.md).
- Frames (FRAMES_PINNED.json 0b99ffe2...): 15,672 sentences (S1 1,545 / S2 267 / S3 1,661 / S4 12,199); 10,368 PG + 3,318 Wikibooks recipes (1,728 REBOUND-eligible); practice partitions Beeton (PG 10136), Tatoeba ids ending in 7, Taskmaster TM-1 dev.
- Package HELM_XREAL_20261019_SOURCE_XREAL.zip c275daed5ed26c6759543e8e89ebe2d54d7d750fe8b8f9bc957efe82ffa7bb6e (freeze 7c92a589...): parts S 128 / R-ASIS 64 / R-REBOUND 64 / F 192 restart worlds; key A + key B (separate session, never saw HELM code; practice agreement 204/205); rivals B-ASK, B-KEYCALC, B-ECHO, -ENGLISH_IN, -VOICE, Eye report-only, checklist, WATCHDOG checksum; custodian contract, seed rule (bands XS/XA/XB/XF 1,898-1,905 million; nine pinned derivations), receiver's checker, frozen reader.
- Measured at build (practice and public frames only, not results): the M-R frame teaches only ONE ingredient per real recipe (I11 15/16 reach a lesson, 0/16 every line; exact-amount batches tie and the brain's receipt needs one limiting ingredient), so recipe arithmetic is unreachable with true statements; the designed recipe pairing gives ~0 answerable items (4/400, 0/400), guard A-XR-5 prints R_VACUOUS; census 1 of 13,686 recipes fits a brain shape; practice dry run: FULL wrote 7 wrong facts on 128 practice sentences ("no water on hand" for "Tom pulled Mary out of the water").
- Tests from the sealed extract: 354 OK (X-REAL 97, w1 128, w2 34, w3 41, w3b 23, w4 31). Dry pool 21/21 units exit 0 in 48.66 s; peak memory 32.7-164.0 MiB.
- Proposed cap 1.00 USD; no hold. Sign line: "APPROVE X-REAL: outside-generator exam, sealed package c275daed, one attempt + one plumbing retry, cap $1.00."
- Slip recorded: the first request (PG robots.txt) carried the owner's e-mail in its User-Agent; later requests did not.

## 2026-10-19 PDT - Dictionary expansions from the owner: ASOM = Aligned / Starved / Oversaturated / Misaligned (owner gave three words; Starved is the spec sheet's fourth), SDG = CAS Synthetic Data Generator, CES = Constant Elasticity of Substitution (borrowed economics term, entered via Gemini); docs only, no status changed

## 2026-10-19 PDT - CAS and HELM dictionary: docs/reference/CAS_HELM_DICTIONARY.md, 449 A-Z entries plus a symbols table and a how-to-read-a-result box; canonical Noetic and Clarification text quoted verbatim; no new definition, no status changed

## 2026-10-19 PDT - HELM UI v0 (`helm_ui/`): local page over helm_chat's own turn (record per reply, planner dry run, Eye self-check on a test copy, RB-I3 attention/pairing from the run record, search dials); tools off in the window; 10/10 tests, about 2 s; demo `helm_ui/demo/index.html`; not wired to the live session: Eye, drive loop; Phase A radial display not built

## 2026-10-19 PDT - HELM-R1 wave 5 SCORED (job c40, AWS): frozen reader HARD_GATES_PASS, EYE_PAIRING_EARNED_KEEP; Eye-paired idle loop 70.18% vs random 35.32% / round-robin 33.93% / frozen 38.83%; 0 items lost, 0 calls in conversation, 0 Eye writes; ENGINEERED-NOT-VALIDATED, SYNTHETIC_ONLY (spec sheet 7.78; one m6i.xlarge, 0.03 USD)

Owner sign line (verbatim, sha256 a9dd6ff2...): "APPROVE R1W5: EYE_PAIRING wave, sealed package b6598687, one attempt + one plumbing retry, cap $1.00." Launch operator: Claude Code sub-agent.

- Job helm-claude-r1w5-20261019-c40: one m6i.xlarge i-0a0a23d11e2a94442 (us-west-2, 2-CPU slice, 14 GiB), launched 12:40 PM, terminated 12:48 PM Pacific; host 489.9 s, runner 205.98 s; 41 of 41 units exit 0; tests w1 128, w2 34, w3 41, w3b 23, w5 40, all OK; one scored attempt, 0 plumbing retries; no torch work.
- Ran in parallel with wave 4 (c39): the c40 hold was placed only after c39's ledger closeout, and the shared S3 prefix taken only after c39's independent cleanup VERIFIED.
- Reading R1_W5_READING.json c61dd0c0... (frozen reader from the sealed zip): HARD_GATES_PASS, word EYE_PAIRING_EARNED_KEEP; every instrument row (I1, I3, I4, I6, I7, I9, I10 incl. seed source = owner line, I11-I14) and every hard gate held.
- Family A pooled (1,509 items): candidate 1,059 = 70.18%; random 35.32%; round-robin 33.93%; frozen table 38.83%; wave 3's loop 35.19%. Marks: (a) 0 items lost on both live exams; (b1) +34.8575 and +36.2492 points (mark 20), per life at least +29.0061 (mark 10); (b2) frozen 38.8337 <= 40.3214 and candidate - frozen +31.3453.
- Faculty calls in conversation 0 (violator 206-258 per life); Eye writes 0 (canary refused every life); guard trips 0 (violator 986-1,026). Pair words: EYE_PAIRING x CASCADE / CUBE_STORE / ENGLISH_IN / TRIAD all ADDITIVE.
- Limits kept: drift recovered on 1 of 3 lives (12 sessions); Q5 declines cost 60 items vs no-decline (reported); the Fisher-Rao variant is 2.9158 points below the default.
- Charge 0.03 USD (cautious 0.07); ledger 111.26 -> 112.26 (hold) -> 111.29 of 200. Cleanup VERIFIED three ways (controller, independent check, direct read-only look); proof b3379824.... Backup D:/tksCAS-archive/r1_wave5_c40_20261019/ (three hash passes).
- Small deviation: the X5 custodian's transcription JSON has unescaped Windows backslashes; read tolerantly, never edited.

## 2026-10-19 PDT - HELM-R1 wave 4 SCORED (job c39, AWS): frozen reader PASS, EYE_SCAN_EARNED_KEEP; found 88/88, acted 88/88, 0 items lost, 0 false alarms, 0 Eye writes, 100% traceable; ENGINEERED-NOT-VALIDATED, SYNTHETIC_ONLY (spec sheet 7.77; one m6i.xlarge, 0.04 USD)

Owner sign line (verbatim, sha256 c23e0aa7...): "APPROVE R1W4: EYE_SCAN wave, sealed package 4bd0d740, one attempt + one plumbing retry, cap $1.00." Launch operator: Claude Code sub-agent.

- Job helm-claude-r1w4-20261019-c39: one m6i.xlarge i-0928ef496d024573b (us-west-2, 2-CPU slice, 14 GiB), launched 12:28 PM, terminated 12:37 PM Pacific; host 530.5 s, stage 226.5 s; 70 of 70 units exit 0; one scored attempt, 0 plumbing retries; no torch. Kit claude_jobkit/r1w4kit/ (derived from c38's by exact substitution; diff vs c38 problems []).
- Reading R1_W4_READING.json 2792f55e... (frozen reader from the sealed zip): test_verdict PASS; every instrument row (I1, I3, I4, I6, I7, I9, I10 incl. seed source = owner line) and every hard gate held.
- Marks all met: no harm (0 lost on all 12 exam parts), found 88/88, acted 88/88, false alarms 0, whisper writes 0, traceable 8,723/8,723 fact sentences + 88/88 notices. Checklist found 0; report-only acted 0. Self-trigger only found 0 of 88 (negative kept).
- Pair words: CUBE_STORE x EYE_SCAN INTERFERENCE, ENGLISH_IN x EYE_SCAN ADDITIVE, EYE_SCAN x TRIAD INTERFERENCE, EYE_SCAN x VOICE ADDITIVE.
- Money: charge 0.04 USD (cautious 0.07); ledger hold 1.00 placed (111.22 -> 112.22), closed 112.22 -> 111.26 of 200. Cleanup VERIFIED three ways (controller, independent check, direct read-only look); slot released.
- Run folder Documents/Codex/2026-10-19/r1_wave4/run_c39_r1w4_20261019/ (RUN_RESULT_R1W4_C39.md). Backup D:/tksCAS-archive/r1_wave4_c39_20261019/ (890 files, three sha256 confirms).

## 2026-10-19 PDT - HELM-R1 wave 5 "EYE_PAIRING wave" PACKET SEALED, NOT LAUNCHED: RB-I3's Unity Eye pairing as one idle drive-loop switch on the wave-3b brain, on a custodian-sealed exam; nothing scored, no claim (spec sheet 7.76; laptop, 0 USD)

Owner order (2026-10-19): "“EYE_PAIRING wave”". Builder: Claude Code sub-agent. Build and seal only; nothing launched; no ledger hold.

- Built in Documents/Codex/2026-10-19/r1_wave5/. PREREGISTRATION_R1W5.precode.md 34a7e05e... written before any code; FROZEN_R1W5.json 0cf16b38... from the code's own constants (a test checks code == file).
- Sealed zip HELM_R1_W5_20261019_SOURCE_R1W5.zip b6598687190bc9e41f52695144eeeac5428913ab804f8bec64841093ea825d6c (118,635 bytes, 37 members + freeze); PACKAGE_FREEZE a325ea13...; resealed byte-identical. Neighbours by reference after freeze checks: wave 3b a4f82556, wave 3 v3 152bca2a, wave 2 21ad185d, wave 1 v3 31f97d67. RB-I3's code vendored byte-identical (manifest 9ecfb7e7); U1b's 14-line ConcertLedger as a marked excerpt.
- The switch: EYE_PAIRING = the Eye's learned 7 x 7 table (counts of checked tries) + evidence-weighted count-ratio attention (RB-I3's tie result R1: the Fisher-Rao step runs as a reported variant). FULL = wave 3's DRIVE_LOOP (seeded random pairing).
- Exams: fresh X5 by a custodian from the owner's sign line, builder blind: X5_PAIR (RB-I3's 7-kind world; each kind bound to a brain job needing CASCADE, CUBE_STORE, ENGLISH_IN, TRIAD or none; families A scored, B planted table change reported, C null control), X5_E64 / X5_F64 (no harm), FULL on the spent X3 files (same brain as c38). Seeds: bands X3 + 40,000,000 (wave 4's bands reserved); life seeds hashed from the owner line.
- Marks: no harm <= 2 items; beats random and round-robin >= 20 points pooled and >= 10 per life; frozen table in the rival band (best rival + 5) and >= 20 below the candidate; 0 faculty calls in conversation (cut violator > 0); Eye writes 0; 0 guard trips on clean arms (guard violator > 0). Words: EYE_PAIRING_EARNED_KEEP / EYE_PAIRING_HARMED / LEARNING_DID_NOT_EARN_KEEP / INCONCLUSIVE. Pair words EYE_PAIRING x CASCADE / CUBE_STORE / ENGLISH_IN / TRIAD by wave 3b's rule (margin 1/8 of the denominator).
- Defaults PROPOSED by the coordinator, owner may override before signing: Q5 the brain may decline a weak soft whisper (counted, reported); Q6 guard = CAS Dial System on the drive dials (builder's reading D-W5-1); Q9 drift reported as sessions to recover.
- Tests from the sealed extract: wave 5 32 + 5 (3 AWS-only skipped), wave 3b 18 + 5, wave 3 36 + 5, wave 2 34, wave 1 128, every suite OK. Practice dry run from the sealed extract: 39 units exit 0 (123.6 s; 77 MiB per X5 unit); reader INSTRUMENT_ERROR as designed; every hard gate held; candidate 69.42 vs random 37.01 / round-robin 33.86 / frozen 38.39 (practice numbers, not a result).
- Failed approach logged (practice data, before the seal): the first full practice run failed the null-control row I13 (candidate 6.22 points BELOW the frozen table on the null family) because the Q5 decline rule fires only after the table has learned; the no-decline arm scored +4.79 points on A. Fix D-W5-6: I13 compares the no-decline arm with the frozen table (like for like, +0.89); the candidate's gap is reported; no threshold changed. Also: RB-I3's attention.py is CRLF, so the seal allows CRLF only for the hash-pinned vendored files; U1b's eye.py is CRLF, the excerpt is pinned by its LF hash.
- Sign line for the owner: APPROVE R1W5: EYE_PAIRING wave, sealed package b6598687, one attempt + one plumbing retry, cap $1.00. Cap PROPOSED 1.00 USD (expected about 0.03-0.09). Backup D:/tksCAS-archive/r1_wave5_20261019/ (176 files, three hash passes, 0 mismatches).

## 2026-10-19 PDT - HELM-R1 wave 4 "EYE_SCAN wave" PACKET SEALED, NOT LAUNCHED: the U3 self-scan as one switch on the wave-3b brain, its whisper delivered to the real presentation path; nothing scored, no claim (spec sheet 7.75; laptop, 0 USD)

Owner order (2026-10-19): "“EYE_SCAN wave”". Builder: Claude Code sub-agent. Build and seal only; nothing launched; no ledger hold.

- Built in Documents/Codex/2026-10-19/r1_wave4/. PREREGISTRATION_R1W4.precode.md 411b31e2... written before any code; FROZEN_R1W4.json 1828dc76... from the code's own constants (a test checks code == file).
- Sealed zip HELM_R1_W4_20261019_SOURCE_R1W4.zip 4bd0d740a70852c8d59091494ad88c69ac472f3a0f207a33fc44789b8e3df14c (121,173 bytes, 31 members + freeze); PACKAGE_FREEZE 0d45017c...; resealed byte-identical. Neighbours by reference after freeze checks: wave 3b a4f82556, wave 3 v3 152bca2a, wave 2 21ad185d, wave 1 v3 31f97d67. U3-T1's rules copied with each source file's sha256 pinned.
- New thing tested: the whisper receiver (r1w4/eye_live.py WhisperReceiver) between ExamLoop3.process_turn and helm_chat._speak; when the next answer would use a faulted record it holds the answer back and the real voice (_say_plain) says why; it writes nothing.
- Exams: fresh X4 by a custodian from the owner's sign line (English-64, Faces-64, X3-SELF 152 = 88 planted faults K1-K5 + 64 clean, U3-T1's 11:8); carried Gate B / Task B / CCE / Cascade / Idle on exposed or spent data (no-harm only, Eye as a sidecar); FULL on the spent X3 files (same brain as c38). Depth NOT_IN_WAVE (laptop stage with Windows-pinned sources).
- Marks: no harm <= 2 items on every wave-3b exam; found 88/88; acted 88/88; false alarms 0; whisper writes 0; traceable 100%; self-only reported. Words: EYE_SCAN_EARNED_KEEP / EYE_SCAN_HARMED / EYE_SCAN_NO_EFFECT / INCONCLUSIVE.
- Tests from the sealed extract: 449, every suite OK (3 AWS-only skipped). Practice dry run: 56 units exit 0 (137.8 s; peak 46.9 MiB per unit, 139.5 MiB reader); reader INSTRUMENT_ERROR as designed; practice found 88/88, acted 88/88, 0 false alarms (practice numbers, not a result).
- Failed approaches logged (practice data, before the seal): the wave-2 unit builder needs only the exams whose data it is given (KeyError in the first dry run); an empty lesson count broke a report sentence; a 42 MB host reading was slimmed to 17 MB (compact JSON, full reports for the candidate only, H11 compares without the kept reports).
- Sign line for the owner: APPROVE R1W4: EYE_SCAN wave, sealed package 4bd0d740, one attempt + one plumbing retry, cap $1.00. Cap PROPOSED 1.00 USD (expected about 0.05-0.12). Backup D:/tksCAS-archive/r1_wave4_20261019/ (61 files, three hash passes equal).

## 2026-10-19 PDT - HELM RB-I3 RAN: the Unity Eye pairs and rotates the 7 desires with the 7 faculties; EYE_PAIRING_EARNED_KEEP by the frozen rule, HARD_GATES_PASS; ENGINEERED-NOT-VALIDATED, SYNTHETIC_ONLY (spec sheet 7.74; 103 laptop parts + reader, 0 USD)

Owner order (2026-10-19): ""RB-I3" t". Builder-operator: Claude Code sub-agent. Sign line (operator-composed): APPROVE rb_i3, source 9ecfb7e7, LOCAL_CPU_ONCE on MSI, 300 s cap, no spend.

- Built in Documents/Codex/2026-10-19/rb_i3/ from rb_i3_design_v1; FROZEN.precode 06d95bdb... (incl. designer 70% and builder 60% predictions) written before any code; the 33 tests written before the code they test. Reuse by import, unmodified: wave-3 drive_w3 fr_distance/slerp_step (79def344...) and common_w3; u1b ConcertLedger; wave-1 rb.writer.receipt and rb.common.outcome.
- Exam X3-IDLE: 7 hidden kinds (every faculty is one kind's primary and another's secondary), 1 in 4 mis-filed, 1 in 3 easy, 2 of 7 wells half dead, 32 sessions of 12-20 items, 2 idle ticks per item, 1-3 planted conversation windows per session. Families A (scored), B drift, C null.
- Result (family A, pooled): EYE_PAIRING 1180/1527 = 77.28%; FIXED_TABLE 80.94% (answer key, reported only); RANDOM 37.33%; ROUND_ROBIN 34.64%; NO_LEARN 36.67%; SHUFFLED_FEEDBACK 41.72%; EYE_RATIO 76.56%; NO_DRIVE 17.29%. M1-M6 all pass; M2 95.47%; M4 7/7/7.
- Hard gates all hold: receipts re-derived, 0 mismatches; WRONG 0; replay 3/3 byte-identical; cut 0 in every non-violator part and CUT_VIOLATOR 765/749/708 calls in conversation (the check can now fail); 0 whisper writes, canary caught; I1 null gap 2.81 points.
- Negatives and caveats kept: the Fisher-Rao step ties the plain ratio (+0.72 points; no geometry word); on the null family the Eye is 4.45 points over random (attention learning); designer misses (FIXED 80.94 below 82-86; drift recovered at sessions 22/28/21). Custody deviation: seeds fixed at 11/29/47 by the brief. The brief listed 8 arms; all 11 ran.
- Reading READING.json 71172e80...; RESULTS.md f1129652...; max part 5.94 s, peak 32.5 MiB; backup D:/tksCAS-archive/rb_i3_20261019/ (961 files, three hash passes, 0 mismatches).

## 2026-10-19 PDT - HELM U3-T1 self-scan by the Unity Eye RAN: SELF_SCAN_EARNED_KEEP and WHISPER_EARNED_KEEP by the frozen rule; ENGINEERED-NOT-VALIDATED, SYNTHETIC_ONLY (spec sheet 7.73; 6 laptop parts, 0 USD)

Owner ruling (2026-10-19 morning): the Eye REPORTS AND WHISPERS; "run U3-T1". Builder-operator: Claude Code sub-agent. Sign line (operator-composed): APPROVE u3_t1, source a39c9bd8, LOCAL_CPU_ONCE on MSI, 300 s cap, no spend.

- Built in Documents/Codex/2026-10-19/u3_t1/ from the U3 design packet; FROZEN.precode f6aafe3a... written before any code; FROZEN.json 66afd40b... with pre-run instrument amendments A1-A6 (dev-seed worlds only; no rule changed). Reuse by import, unmodified: u1b ConcertLedger, Lacunarity Machine, thread copies of helm_triad (0d9d0bda...), helm_voice, helm_brain_canonical, cube store, valve; wave-1 brain members (freeze 8c55c413...).
- 368 copies (64 clean, P1-P7 32 each, S1-S5 16 each), 17 arms. Hard gates H1-H9 all hold; tests 18/18 in every part; peak 116.1 MiB; 17:40-17:46 UTC after waiting for RB-G10.
- Candidate FULL/REPORT_AND_WHISPER: body faults 176/176 named with their record; false alarms 0; 20,768/20,768 fact sentences traceable, 0 invented, 0 dropped; Mind exact on 2,336/2,336 scans; P6 32/32 at exactly 1/4; P7 32/32. SELF trigger: 80/80 signal copies, 0/64 clean.
- Baselines: FIXED_CHECKLIST 16/176 (S4 only); RANDOM_SAMPLE_SCAN 148/176 (exact chance E 153.16, within E + 3 sigma).
- Whisper: next presentation on the faulted thing 240/240 (whisper arms) vs 49/240 (report only); 0 whisper writes; 0 whispers on clean copies.
- Negative kept: the self-initiated trigger alone finds 16/176 (silent faults raise no signal). Limits: faults planted knowing the checks; the whisper's receiver is a stand-in presentation policy; no consciousness claim; 0 pathways named by any receipt.
- Failed approaches logged (dev worlds, before the run): file-only tampering was erased by the brain's next save (fixed: plant in place); the first scan ran before any mechanism record and whispered "never used" on clean copies (fixed: mechanism records in block 0); an S2 tie made one answer UNDETERMINED (fixed: redraw until one bottleneck).
- Reading MERGED_READING.json d35a5210...; RESULTS.md 025c5329...; backup D:/tksCAS-archive/u3_t1_20261019/ (125 files, three hash passes, 0 mismatches).

## 2026-10-19 PDT - HELM-R1 WAVE 3b SCORED (job c38, AWS): reader PASS; ENGLISH_IN x VOICE SYNERGY, the other three pairs INTERFERENCE; no pair left unreadable (spec sheet 7.72; 0.03 USD)

Owner line (sha256 b5fc50dc...): "APPROVE R1W3b: roomier English-64 + Faces-64, pairs CUBE_STORExENGLISH_IN/ENGLISH_INxTRIAD/ENGLISH_INxVOICE/TRIADxVOICE, marks PROPOSED as sealed, sealed package a4f82556, one attempt + one plumbing retry, cap $1." Operator: Claude Code sub-agent.

- Ran: one m6i.xlarge (i-0990ebc5ffb9f80ce), 17:29-17:34 UTC, host 353.7 s, stage 119.2 s; 17 of 17 units exit 0; one scored attempt, 0 retries; no torch helper (X3 laptop-only, sealed by a custodian).
- Reading (frozen r1w3b/merge_r1w3b.py, R1_W3B_READING.json 384f3038...): PASS, words licensed, SYNTHETIC_ONLY. I1, I3 (same brain as c37), I4, I6, I7, I9, I10 hold; H1, H8, H11 hold.
- Pair words (M = right and plain, of 64; readable iff L(a)+L(b) <= M(FULL)-8): CUBE_STORE x ENGLISH_IN INTERFERENCE (8 + 27 = 35, both 27); ENGLISH_IN x TRIAD INTERFERENCE (20 + 24 = 44, both 20); ENGLISH_IN x VOICE SYNERGY on both exams (E64 27 + 16 = 43, both 59; F64 20 + 20 = 40, both 60); TRIAD x VOICE INTERFERENCE (24 + 20 = 44, both 28). All readable. The builder's predictions all held.
- FULL: English-64 59 right / 0 wrong / 5 undetermined; Faces-64 60 / 2 / 2. PROPOSED marks both met.
- Charge 0.03 USD (conservative 0.05 shown); ledger 112.19 -> 111.22 of 200. Cleanup VERIFIED (controller, independent, direct). Backup D:/tksCAS-archive/helm_r1w3b_c38_20261019/ (712 files, three confirms).
- Not licensed: anything outside synthetic worlds; any word for a single part; any pair other than the four; statistical superiority (one run). c37's four CEILING_NOT_READABLE words stay on record.

## 2026-10-19 PDT - RB-G10 "harder world" RAN: INCONCLUSIVE (TOO_FEW_VALID_MULTI_KIND_WORLDS), growth claim stays NOT LICENSED (spec sheet 7.71; laptop MSI, 14 parts, 0 USD)

Owner ruling: "harder world" (one more growth run where gaps come in several kinds at once; stop the line if it fails). Builder-operator: Claude Code sub-agent. Frozen before code (FROZEN.precode.json f77176e7...).

- Worlds: three new two-kind worlds (route + leak twice, slot + leak), budget N = planted kinds + 1; regression a2_g8; reported three-kind MASKED; controls `a` and three shuffled. Engine limits recorded before the freeze: vertices cannot share an Omega, eta cannot bind, slots and routes mask each other.
- Arms: CURIOSITY (RB-G9 reader), REFUSAL_COUNT, the new REFUSAL_COUNT_WITH_KIND_GUESS (residual pattern + the same real-rows check), KIND_GUESS_NO_CHECK, RANDOM_KIND x3, NO_GROWTH, ORACLE, leave-one-out answer-key stages.
- Result: the ORACLE equalled the start brain on all three new worlds (4.69, 21.29, 7.03), so no world was valid and the comparison did not happen (VACUOUS). Cause in the stored units: routes and the leak mask each other inside the fitter. Regression reproduced RB-G9; curiosity fired 0 on controls; guardrails all 0. Reported only: the kind-guessing rival grew the leak on RLJ (33.20 vs ORACLE 21.29) where curiosity named nothing.
- Run: manifest e98af208..., MERGED.json 16524cff..., tests 69/69, replay 4/4, 18 of 18 units shared with RB-G9 digest-equal, backup D:/tksCAS-archive/rb_g10_20261019/ (194 files, three hash passes, 0 mismatches). Next step is the owner's decision (verdict INCONCLUSIVE, not FAIL).

## 2026-10-19 PDT - ERRATUM to spec sheet 7.69: the wave-3 idle arm called "round-robin" (107 good) is round-robin plus a fixed table; true round-robin scored 31

Records only. No run, no spend. Checked against `r1w3/drive_w3.py` (sha256 79def344...), `R1_W3_READING.json` (1cc7dba8...) and the sealed `IDLE_X2.json` (f883f8b0...).

- The arm labelled "round-robin" with 107 good is `FIXED_TABLE_RR`: round-robin Foundations plus RB-I's fixed table that gives each kind's home Foundation the one faculty that can solve it (drive_w3.py lines 18-20, 49-52, 159). 137 of the 180 items sit at that home Foundation.
- TRUE round-robin (no table) is the `-DRIVE_LOOP` arm: 31 good, 149 open, 0 wrong. The drive loop (FULL) is also 31 good. Corrected reading: `DRIVE_LOOP` is NEUTRAL against true round-robin; it did not lose to round-robin 107.
- Unchanged: the `DRIVE_LOOP` word NEUTRAL, every number, every gate, every claim status. Only the baseline label is corrected. Originals (spec sheet 7.69 text, RUN_RESULT_R1W3_C37.md, the earlier Change Log row) are kept; the erratum stands beside them (spec sheet 7.69 erratum + Change Log row; `ERRATUM_20261019.md` in the run folder).
- Open questions only (from the DeepSeek-brief compiler; not conclusions): only 4 of 7 faculties can act in drive_w3.py; the "cut in conversation" gate H14 cannot fail for any arm (awake ticks never carry a foundation key, lines 135-137, 175); `DESIGN_R1W3.md`, cited by the code, is missing from disk and from the source zip.

## 2026-10-19 PDT - HELM-R1 WAVE 3b packet sealed, NOT LAUNCHED: the roomier exam for the four unreadable pairs (spec sheet 7.70; laptop, 0 USD)

Owner ruling (2026-10-19 morning): "roomier exam" so the 4 unreadable pairs can be read [yes, cheap]. Builder: Claude Code sub-agent. No launch, no hold, no spend.

- Pairs: CUBE_STORE x ENGLISH_IN, ENGLISH_IN x TRIAD, ENGLISH_IN x VOICE, TRIAD x VOICE (all four c37 CEILING_NOT_READABLE; all four parts EARNED_KEEP in c37).
- Exams: English-64 and Faces-64 from wave 3's own family code (reproduces e16/f16 exactly, 5 seeds) with new counts and a ladder: plain, two-ingredient, unknown ingredient (ASK), unit change (ASK), face stated/implied. English-64: ANSWER 16, ASK 32, LEARN 8, READ 8. Faces-64: ANSWER 24, ASK 40.
- Why not just 4x: the old mix makes both singles lose almost every item, so E grows with the exam (English-16 x 4: E about 76 vs room about 64). ASK items survive one part off and make room.
- Arms 15 + 2 same-brain reruns (FULL on the spent X2 English-16 / Faces-16 must equal c37's records) = 17 host units (c37: 106).
- Readability stated numerically: CEILING_NOT_READABLE iff L(a) + L(b) > M(FULL) - 8 (wave 3's rule, imported verbatim). The coordinator's "only at FULL >= 62/64" wording was not made a rule (it would turn no-room into fake INTERFERENCE); flagged D-B2.
- Text rule T3b: A1 extended to the store questions, question forms and "Hi again." (without it, all 6 store questions are forbidden and no seed can pass). X3 bands = X2-v2 + 20,000,000; used table = six pinned derivations (X0, X1, X2-v1 x2, X2-v2 x2); dummy-line check PASS.
- Marks PROPOSED: English-64 >= 56 right, <= 2 wrong; Faces-64 >= 48 right, <= 4 wrong.
- Sealed zip a4f82556bf0fc26de5635a7c81ec8f5053951d4c64a3906c8e5dd474e3814d26 (82,393 bytes), freeze a6d9dbc7..., FROZEN_R1W3B 90d4468d...; resealed byte-identical; backup D:/tksCAS-archive/helm_r1w3b_packet_20261019/.
- Tests from the sealed zips: 526 run, 519 passed, 7 skipped (AWS-only host tests), 0 failed. Dry run on fixtures: 15 units exit 0 in 19.2 s; reader INSTRUMENT_ERROR as designed; every pair readable on fixtures (slack 8-16).
- Cost PROPOSED: about 0.02-0.06 USD expected, worst about 0.70; cap 1 USD. Sign line in OWNER_SIGN_REQUEST_R1W3B.md.
- Failed approach logged: the first E64 receiver check failed on the store-read items (text rule), which found the T3b trap before any X3 seed existed; a first test case for ADDITIVE used wrong numbers (fixed in the test, not the rule).

## 2026-10-19 PDT - HELM-R1 WAVE 3 SCORED (job c37): reader PASS, words licensed, SYNTHETIC_ONLY (spec sheet 7.69; three m6i.xlarge jobs, 0.08 USD)

Owner v3 sign line (sha256 1606306a...), package v3 152bca2a... (freeze bd06f324...). Launch operator: Claude Code sub-agent. Amendments R1W3-A1 and R1W3-A2 (incl. A2.1-c); coordinator option B after the operator's held note (the reader reads one owner line for I9 and I10, so X2 was rebuilt from the v3 line; X2-v1 VOID_UNUSED).

- Jobs: helper c37a (X2-v1, void, 267.8 s), helper c37b (X2-v2, 289.5 s, I5 OK), scored c37 (i-09b4e033606bbfe96, host 646.8 s, stage 387.8 s, 106 of 106 units, 0 plumbing retries).
- Reading R1_W3_READING.json 1cc7dba8...: PASS; I1-I10 and H1-H14 all hold. Words: 11 EARNED_KEEP; CCE_SKIN NEUTRAL; DRIVE_LOOP NEUTRAL (idle 31 good both ways; round-robin 107). DECOUPLING_EARNED (descents 203 vs 609; good 64 vs 60; fuses on solvable 0 vs 4).
- Pairs: 7 ADDITIVE, 5 INTERFERENCE (every CASCADE pair plus CUBE_STORE x EYE), 0 SYNERGY, 4 CEILING_NOT_READABLE (the English pairs).
- Reported apart: PROPOSED mark FULL_FACES16 false (12 right, 1 wrong, 3 undetermined); skin_form SKIN_FORM_BROKEN.
- Charge 0.08 USD; ledger 111.19 of 200; cleanup VERIFIED for all three jobs; backup D:/tksCAS-archive/helm_r1w3_c37_20261019/ (1,268 files, three hash passes, 0 mismatches).
- Failed approach logged: the windowing script's stale-number check matched "3000" inside a sha256 (false positive); fixed to ignore 64-hex digests.

## 2026-10-19 PDT - RB-G9 curiosity growth, instrument retest RAN: CURIOSITY_DID_NOT_EARN_KEEP, FAIL (spec sheet 7.68; laptop MSI, 8 parts, 0 USD)

Coordinator decisions (instrument fixes): (1) the job check measures a grown copy's real rows; (2) drop the depth family; (3) everything else frozen as RB-G8. Builder-operator: Claude Code sub-agent. Frozen before code (FROZEN.precode.json 69d97e99...).

- IC1: before growing, the unit is fitted on a copy of the brain; it may grow only if the copy newly explains >= 8 rows and 4 x rows >= parameters added (exact Fractions). The old promise J is logged only.
- Fix test: the IC1 tests fail against the RB-G8 reader (K3 named on the promise 199) and pass against the RB-G9 reader (real 22 rows, +320 parameters, refused). One test uses the real RB-G8 a_g8 units.
- IC2: TaskB_d3 not run (no arm reached depth 3 in RB-G8; depth goes to wave 3's cascade exam).
- Marks: M1 TRUE (84/84), M2 FALSE (a_approx 81.25 vs 87.50), M3 TRUE (0 fired on controls; RB-G8: 1), M4 FALSE (scale_leak only), M5 TRUE. Status CURIOSITY_DID_NOT_EARN_KEEP; claim NOT LICENSED.
- Run: manifest ecbea9e6..., MERGED.json 8f471a95..., tests 48/48, replay 4/4, 330 of 332 units digest-equal to RB-G8, backup D:/tksCAS-archive/rb_g9_20261019/ (124 files, three hash passes, 0 mismatches).

## 2026-10-19 PDT - RB-G8 growth at the point of curiosity RAN: GREW_WRONG_KIND, FAIL (spec sheet 7.67; laptop MSI, 9 parts, 0 USD)

Owner words: "Unpark growth; ..." and "WE ADD MORE AT THE POINT OF CURIOSITY THE SECOND FOUNDATION ..." (2026-10-19 early). Builder-operator: Claude Code sub-agent. Frozen before code (FROZEN.precode.json 53ab4508...).

- Design: a CURIOSITY reader on F2 Wisdom points at one gap at a time, reads the five signs and the out-of-sample probes there, names the kind (probe decides, sign ranks), job-checks the new parameters, grows one unit, verifies V1-V8, re-reads. Arms NO_GROWTH, ORACLE, CURIOSITY, REFUSAL_COUNT (RB-G6 REFUSAL_ONLY), RANDOM_KIND x3, LEDGER_G6 (reported).
- Fresh G8 worlds: F1 draws 3000-3019 (K1), a_approx (K3), a2 (K2, new planted route family), scale_leak (K4), TaskB_d3 (K5); controls S2v2, S3v2, a, three shuffled LSR, F1 shuffled.
- Marks: M1 TRUE (85/85), M2 FALSE (a_approx 81.25 vs 87.50; TaskB_d3 39.06 vs 73.05), M3 FALSE (one K3 fired on the `a` control, rolled back by V8), M4 FALSE (scale_leak only), M5 TRUE. Status GREW_WRONG_KIND; claim NOT LICENSED.
- Measured difference from G1-G6: the G6 ledger froze (KNOWLEDGE_MISSING) on a_approx and a2; curiosity grew both. The job check trusted per-cell probes (J 199) that over-promised on `a` (22 rows delivered).
- RB-G7 (approved 2026-10-15 7:20 PM) found NEVER_RAN: no folder, freeze or result.
- Run: manifest 2346ddfe..., MERGED.json 901e1459..., tests 36/36, replay 4/4, backup D:/tksCAS-archive/rb_g8_20261019/ (132 files, sha256 equal).

## 2026-10-19 PDT - HELM-R1 WAVE 3 RESEALED v3: text rule checks the statement only (amendment R1W3-A1; spec sheet 7.66 amended)

Coordinator amendment R1W3-A1 after the X2 custodian's block (text rule unsatisfiable on every seed). Builder: Claude Code sub-agent.

- r1w3/gen_live.py: FOLLOWUPS (the generator's 15 follow-up questions, sha256 14f5cb49...), statement_turns, text_rule_hits on the statement only, followup_tails receipt; check_x2_format.py and the host stage record every stripped tail.
- Three new tests: a repeated statement still fails; a tail-only overlap passes; the list hash. Generator item code unchanged.
- v2 zip 26b0ef7e... (signed) VOID_SUPERSEDED_BY_A1: the owner must re-sign. v3 zip 152bca2a..., freeze bd06f324...; 4 members changed.
- Tests from the v3 seal: 496 passed, 4 AWS-only skipped, 0 failed. Custodian notice RESEAL_NOTICE_V3.md.

## 2026-10-19 PDT - HELM-R1 WAVE 3 RESEALED v2 before signing: cube store read path repaired (spec sheet 7.66 amended)

Coordinator's decision (plumbing defect, owner not yet signed). Builder: Claude Code sub-agent.

- Fixed in docs/working/noetic_council/cube_store: 'What do we have on hand?' no longer goes to FIND_SHARED_PART ('and' inside 'hand'); LIST_PARTS no longer lists an absent part ("None Water"). Two new cases, 19/21 before, 21/21 after.
- v1 zip 2d5b4f0e... VOID_UNSIGNED. v2 zip HELM_R1_W3_20261019_SOURCE_R1W3_v2.zip 26b0ef7e..., freeze a72063f5...; exactly 4 members changed.
- Tests from the v2 seal: 493 passed, 4 AWS-only skipped, 0 failed. Drive-loop rule, FROZEN_R1W3.json and everything else unchanged.
- Owner sign line now names 26b0ef7e.

## 2026-10-19 PDT - HELM-R1 WAVE 3 PACKET SEALED, NOT LAUNCHED (spec sheet 7.66; laptop, 0 USD)

Owner order "wave 3 plan" plus the 2026-10-19 rulings (decoupling-stop adopted, drive loop design, growth unparked). Builder: Claude Code sub-agent.

- Design frozen before code: docs/working/r1_wave3/DESIGN_R1W3.md (27eab7e8, then 2715bebe after amendment D1).
- 13 switches (wave 2's eight + CUBE_STORE, ATLAS, EYE, CASCADE, DRIVE_LOOP RB-I2), swap arm CASCADE_FIXED_CAP; 16 pairs / 18 pair runs; exams E1, E2, X2 (GB, TB, D34 laptop, CCE, English-16 v3, Faces-16, Cascade, Idle).
- New live module helm_faces_in.py + helm_faces_lexicon.json (31 rows, each sourced; 0 learned parameters; 16/16 tests).
- Sealed zip Documents/Codex/2026-10-19/r1_wave3/HELM_R1_W3_20261019_SOURCE_R1W3.zip sha256 2d5b4f0e...; freeze be1b321d...
- Tests from the sealed zip: 491 passed, 4 AWS-only skipped, 0 failed. Dry run on fixtures: 62 units exit 0; reader INSTRUMENT_ERROR as designed.
- Found on fixtures, not fixed: the cube store's read path lists absent items and misroutes "on hand" questions (CUBE_STORE may read HARMFUL).
- NOT_IN_WAVE: RB-I1 faculties design (7.65 clean negative), growth (RB-G8). Proposed cap 3 USD. No hold, no launch.

## 2026-10-19 PDT - HELM RB-I1c FACULTIES RETEST RAN: all hard gates held, status word INCONCLUSIVE (spec sheet 7.65; job c36 on AWS, 0.70 USD)

Owner order "rerun faculties" (cap 2.00 USD set by the coordinator). Builder-operator: Claude Code sub-agent.

- Instrument-only fixes vs RB-I1: level-receipt check before the write with RB-I1's own rule (empty fitter receipt = refusal, nothing written); the ten LSR datasets shipped as hash-checked data (Windows-vs-Linux libm last-bit drift in families a and c reproduced under WSL glibc 2.39 / Python 3.12.3); fresh seeds 312/579/868 with H7's rb_c4 reference recomputed on the host.
- Package Documents/Codex/2026-10-19/rb_i1c/RB_I1C_FACULTIES_20261019_SOURCE.zip sha256 ab4549f0...; FROZEN.json fcaf12c3 written before code.
- Run: one m6i.8xlarge, host 1,617.8 s, r 1.2427, 146 of 146 parts COMPLETED, tests 18/18 and 15/15 per part, data identical to the laptop.
- Reading (MERGED_MARKS.json cb700275...): test_verdict HARD_GATES_PASS; status_words INCONCLUSIVE. H1: 179 nested writes all passing, 2 empty-receipt candidates refused before the write. H7 30/30. H3 109/109.
- No faculty or drive word earned: A3 beat A6 on 0 families; STARVED A1 41/42/45 and A2 76/83/66 vs greedy 36/35/38.
- Ledger: hold 2.00 (110.41 -> 112.41), closed at 0.70 USD (-> 111.11 of 200). Cleanup VERIFIED twice. Backup D:/tksCAS-archive/helm_rb_i1c_c36_20261019/ (1,622 files, three sha256 confirms).
- Disclosure: amendment 'when' times inside the sealed package are wrong by up to ~45 min; content unaffected.

## 2026-10-18 PDT - HELM-R1 WAVE 2 SCORED: reader PASS, one word per part (spec sheet 7.64; jobs c35 + helper c35a on AWS, 0.06 USD)

Owner sign line sha256 6f32266d (package 21ad185d, one attempt + one plumbing retry, cap 5 USD). Launch operator: Claude Code sub-agent.

- Helper c35a (coordinator amendment R1W2-A1): GB3 world() on AWS for the X1 custodian, 236.3 s, identity row 1fb7a1c7 equal, I5 OK; files shipped by path and sha256 only.
- Scored c35: one m6i.xlarge, 2-CPU slice; host 630.7 s, stage 370.6 s; wave 1 carried tests 128 OK, wave 2 tests 38 OK (2 laptop-only skips); 68 of 68 units exit 0; 0 plumbing retries.
- Reader (r1w2/merge_r1w2.py, laptop): R1_W2_READING.json sha256 27f2f504...; test_verdict PASS; I1-I9 and H1-H8 hold.
- Words: RECIPE_MATH, RPM_GATE, LACUNA_CADENCE, RESTART_FALLBACK, ENGLISH_IN, VOICE = EARNED_KEEP; CCE_SKIN = NEUTRAL; TRIAD = NOT_EXERCISED.
- Reported apart: skin_form SKIN_FORM_BROKEN; on X1 Gate B the lookup arm (-RECIPE_MATH) scored 16+16 vs FULL 15+15 (the frozen RECIPE_MATH rule reads Task B only); on depth d3 seed 47 FULL 75 right vs 119 for -RESTART_FALLBACK (median rule still WIN).
- Ledger: hold 5.00 USD placed (110.35 -> 115.35), closed at 0.06 USD (-> 110.41 of 200). Cleanup VERIFIED for both jobs. Backup D:/tksCAS-archive/helm_r1w2_c35_20261018/ (913 files, three sha256 confirms).
- Ops: the c34-g job had left 4 objects in the shared S3 slot and no cleanup record; verified byte-identical to local + archive copies, purged, retroactive record written and labelled.

## 2026-10-18 PDT - HELM-R1 WAVE 2 PACKET SEALED, NOT LAUNCHED: the licensed recipe brain with one part switched off at a time (spec sheet 7.63; laptop, 0 USD; no ledger hold)

Owner words: "wave 2 plan". Builder session (Claude). Nothing ran on AWS; nothing is scored; the owner has not signed.

- Package `Documents/Codex/2026-10-18/r1_wave2/HELM_R1_W2_20261018_SOURCE_R1W2.zip`, sha256 21ad185d885a11c4ee498e31e106c71ca608dc9edea1b201a283347086d58dc5;
  PACKAGE_FREEZE sha256 c8f82a6d652ae6f910021e9d1c19ad7e67bcf29bdacc0613b8eb469d84b29224 (181 members; resealed byte-identical). Runs beside the
  unchanged wave-1 v3 zip (31f97d67..., freeze 8c55c413...).
- Arms: FULL, -RECIPE_MATH, -RPM_GATE, -LACUNA_CADENCE, -RESTART_FALLBACK, -CCE_SKIN, -TRIAD, -ENGLISH_IN, -VOICE,
  T (frozen c21/c27 numbers, not rerun), LUT. No arm needs torch (only X1's Gate B world regeneration does).
- Exams: E1 Gate B c21 worlds, E2 Task B RB2c worlds (both exposed), E3 fresh X1, E4 English-16 (16 plain-English
  turns, 3-valued, PROPOSED mark).
- X0 re-checked with the receiver's checker: originals still fail 3 of 5, conversions pass 5 of 5, and wave 1's own
  rule makes X0 exposed -> X1 required, custodian-sealed from the owner's sign-line hash, receiver check before seal.
- c34-g supervisor defect fixed and tested: outputs declared at r1w2_out/ where the runner keeps them; runner keeps
  .sha256; supervisor records each declared output's sha256 and names misplaced files; plan_check replays c34-g's
  own plan and runner and shows the old pair fails. Correction to 7.47 recorded in 7.63 (not edited): c34-g's runner
  DID write R1_W1_HOST.json.sha256; its copy filter left it behind.
- Governance gap of wave 1 closed by design: instrument row I9 fails unless the approval record names the exact zip
  and freeze that ran; any reseal after signing needs a new sign line.
- Tests (from the extracted sealed zip): 410 passed, 4 skipped (AWS-only host tests), 0 failed: wave 2 units 25 and kit 9; HELM live modules 91 (loop 18, English-in 31, voice 22, triad 15, chat nuance 5); language_v3 87 (lm_t1 26, t1b 11, t1c 5, t1v3 26, lexicon_v2 19); repair_performer 16, the_loop_v3 35, cube_store 19; wave 1's carried unit tests 128. One failure found and fixed before the final seal (the loop's valve-history test needed `tks_meta_valve_weights_v0_4.json` in the cut); the first seal `c6db9556…` is void, never signed.
- Dry run on exposed data (laptop, one unit at a time): 68 units, 68 exit 0, 391.9 s; FULL reproduces c23 and c26 (wave 1's I3) and c34-g's A1 labels on X0; reader verdict on the dry input `INSTRUMENT_ERROR` as designed
- Cost PROPOSED: about 0.25-0.35 USD per attempt, worst case 2.34 USD (X1 + scored + one plumbing retry); cap 5 USD.
- Failed approaches / dead ends: porting wave 1's depth panel to the AWS host was examined and NOT done (its sources
  hard-code Windows paths in rb_c4/casform.py, rb_c4/taskb.py, lsr_t1/run_t1.py); the depth families stay a laptop
  stage as in wave 1. The chat-nuance suite writes math_utils.py and sessions/ into the tree it runs in (seen in the
  worktree; removed; the host run does not run that suite).

## 2026-10-18 PDT - DWP-T2 RAN (Wisdom rule C kept: C_EARNED_KEEP) AND THE TRIAD ADAPTER helm_triad.py BUILT; spec sheet sections 7.61 and 7.62; laptop MSI, 0 USD, ENGINEERED-NOT-VALIDATED, SYNTHETIC_ONLY

Owner words: "drops only by a named event with evidence [C]."; "min; earliest ..."; "Desire is Purpose"; one scale
(Documents/Codex/2026-10-18/OWNER_APPROVALS_20261018.md). Build order relayed by the dispatch coordinator.

- DWP-T2 (Documents/Codex/2026-10-18/dwp_t2/, FROZEN.json sha256 6fbd4f02... written before code): Wisdom rules
  A never drops / B drops like the others / C drops only by a named event with evidence, plus a random drop/no-drop
  baseline, on three planted world families (64 worlds x 16 steps each). Run DWP_T2_MSI_ONCE, sign line
  "APPROVE dwp_t2, source 15e2c4ea, LOCAL_CPU_ONCE on MSI, 300 s cap, no spend.", 2.9442369 s, peak 40,861,696 bytes,
  17/17 tests. Status word C_EARNED_KEEP.
  - (i) rises only: A, B, C identical on every row; 0 false drops.
  - (ii) 192 real decays: avoidable wrong yields A 439, B 0, C 0; A called 0 of 192 drops; C 192/192 with
    UNEXPLAINED_YIELD evidence, 0 rows late. 238 surprise rows (B, C) cannot be avoided by any rule.
  - (iii) 128 tampered reloads: C caught 128/128 (STORAGE_FAULT), 0 wrong, 391 UNDETERMINED; A and B 153 avoidable
    wrong each, 0 caught. 0 false faults on 256 clean reloads.
  - Costs: 4,608 stored face values for every rule; C adds 3,315 receipts and 320 events; 0 learned parameters.
  - Limits: by construction; noise-free worlds; rule A had no reload check (coordinator spec). Says nothing about
    whether real know-how decays.
- Triad adapter: new helm_triad.py (TriadBrain wraps CanonicalRecipeBrain.evaluate/witness; TriadTable stores faces
  with sources, evidence and an append-only receipt log). Default OFF. Sealed package, helm_brain_canonical.py,
  helm_end_to_end_loop.py and helm_chat.py untouched. test_helm_triad.py 15/15 OK: OFF identical 100/100; Peak
  identical 400/400; planted starved ingredient 120/120 and face 120/120; receipts 52/52; Wisdom drop without event
  refused; STORAGE_FAULT / UNEXPLAINED_YIELD / CORRECTION evidence paths pass; reload tamper caught. 0 learned
  parameters; stored-value ceiling 28 (8 x 3 + 4). Existing suites unchanged: loop 18 OK, English-in 31 OK, voice 22
  OK, chat nuance 5 passed. Not wired into the live loop yet (that file belongs to the English-in builder today).
- Spec sheet: 7.60 was taken by the English-in builder (fix H), so these are 7.61 (DWP-T2) and 7.62 (adapter), the
  numbers the task named.
- Failed approaches: none abandoned. Two ResourceWarnings (unclosed file handles in test_14/test_15) fixed before the
  recorded run; no assertion changed.

## 2026-10-18 PDT - FIX H: EVERYDAY ENGLISH IN. Plain stock and recipe sentences now reach the licensed brain through the same checked route (laptop, 0 USD, ENGINEERED-NOT-VALIDATED)

New `helm_english_in.py`: a deterministic reader that restates everyday stock/recipe English in the checked form
(CASContent) and keeps it only if parse(render(C)) == C. "We have 50 flour, 30 sugar and 20 butter", "there's 12 cups
of flour", "we're out of water", "can we bake bread?", "how much bread can we make?", "bake a batch" (the current
subject, else a question), and "we made 5 loaves from 10 flour and 8 water and ran out of flour" (a witnessed batch).
Anything else that needs a guess gets one plain question and writes nothing (22 question codes: unknown ingredient or
product, no number, approximate, what-if, relative, negated, unit switch, conversion, contradiction, which product,
stated recipe, incomplete batch, round trip failed). Units are kept as said and compared, never converted.
- `helm_end_to_end_loop.py`: free English -> reader -> the SAME round trip, gate, brain, store and receipts as a
  checked-form turn; reader questions end as CLARIFY_ENGLISH_<code>, zero writes; new trace station "English in".
  Bug fixed: a said-gone ingredient was glued back from an older stored amount; absences are now gated, written and
  read back, and never re-glued.
- `helm_chat.py` routes inventory statements through the loop; its side parser is gone (and the second one in
  `helm_memory.AnaphoraResolver`). Every everyday reply goes through `helm_voice` (reader questions and stock notes
  included, zero CAS tokens).
- MOOD_FACT_CLASH_CHECK (ENGINEERED-NOT-VALIDATED, reported only; HELM does not understand sarcasm): a 10-word positive
  mood list + a refusal/missing/undetermined receipt -> one plain question; facts unchanged.
- Tests (Windows, Python 3.14.0): new 31 OK; loop 18 OK; voice 22 OK; chat nuance 5 passed (no assertion changed);
  lm_t1 26 / lm_t1b 11 / lm_t1c 5 / lm_t1v3 26 OK; lexicon_v2 19 OK; repair_performer ALL PASS; valve 3 PASS;
  fluency harness output byte-identical; pyflakes clean on new/rewritten files. 3 tests updated (they pinned the
  free-English-refused stopgap): loop test_14, loop test_18, voice chat test.
- New trace docs/working/traces/HELM_LIVE_TRACE_ENGLISH_IN_20261018.jsonl (136 lines) sha256
  678c907611fbcf64924bd22524e6ff5a9e517f2a4316885865a4fe97f6062b87; fix-C trace untouched
  (4f94ccee22ea9829072ebfd59fe7690f56d3f28f49527cf2f39b140283fe6fba). Free-English tick 12 returns brain receipt
  48ee0b4bac4d2567, identical to checked-form tick 7.
- Record: docs/working/traces/RESULTS_ENGLISH_IN_20261018.md; spec sheet 7.60.
- Open gap, stated: a plain number and a unit word are not compared (no unit to disagree with).

## 2026-10-18 PDT - DWP-T1 RECORDED (Purpose / Wisdom / Power per reagent) AND THE EVENING OWNER RULINGS; spec sheet sections 7.58 and 7.59; laptop, 0 USD, ENGINEERED-NOT-VALIDATED

Text only; no tests to run. Source: Documents/Codex/2026-10-18/dwp_t1/RESULTS.md (sha256 00871a28325eeb9233b75fd8583ca1b65a64381988dc2bb034a70b86f9b49a4d).
Run DWP_T1_MSI_ONCE (manifest sha256 1fc46d697b3a057bebdfd541b3f4f1861276ad1d66c30b8d42106a579a68af16), 2.0822454 s,
peak 42,098,688 bytes, 13/13 tests. The frozen rule's word is TRIAD_EARNED_KEEP. Claim status: ENGINEERED-NOT-VALIDATED,
ceiling SYNTHETIC_ONLY. The builder's own caveat, kept: the answer keys use the same rules as the arms, so this shows the
wiring works on planted data, NOT that real reagents carry a triad.

- M1 5,376/5,376 (all six arms). M2 32/32 for A_MIN, A_PROD, A_MIN+B; 0/32 for CONTROL, B_ONLY, RANDOM_FACE.
  M3 640/640 UNDETERMINED on Absent recipes and 0/640 on Peak (B arms); CONTROL/A_MIN/A_PROD 0/640.
  M5 512/512 vs 175/512, margin 65.8203 points (bar 5).
- M4 (report only): MIN vs PRODUCT_BOOK yields differ on 336/512 starved rows and 255/256 mixed rows; a different
  limiting ingredient on 52/256 mixed rows. The two face readings (RPM order vs lowest value) disagree on 94/256
  (A_MIN) and 105/256 (A_PROD) mixed rows; predicted 15-35%. Imbalance factor = max - min (reproduces
  MANUSCRIPT.md:13585-13586).
- OPEN, not decided: attribution by RPM order vs lowest value; MIN vs PRODUCT.
- Owner rulings 2026-10-18 evening (new 7.59), each IN FORCE: Desire is Purpose (HELM canon, secular reading, no book
  says it); one scale 0.25/1.00/0.50/0.00 for all three faces (the books' separate ladders set aside); DWP-T1 ordered;
  the stopped 300 GB machine i-0c3028734c8885542 terminated and volume vol-01cc880a770c10854 gone (about 24 USD a
  month, list-price estimate); the 2.06 USD accepted after the fact (ledger 110.35 of 200.00, no money moved).
- Also fixed: the stale 'numbered 7.50' note under 7.57 (fix E is 7.57).

## 2026-10-18 PDT - FIXES C AND D: the licensed recipe brain is wired into HELM's live loop; the valve is a written rule (laptop, 0 USD, ENGINEERED-NOT-VALIDATED)

`helm_brain_canonical.py` loads the HELM-R1 wave-1 recipe book by path (freeze
8c55c4136e1b24bc322779160ffed666f9eb9ee21512c1972101263a243c039b, 17 member hashes checked, nothing copied).
`helm_end_to_end_loop.py` now runs CCE round trip -> S0..S6 -> real rpm_gate -> real repair performer ->
brain -> store write only after the gate and the read-back receipt. The fill-with-ten shortcut and the
"verified when the checker is missing" shim are gone. A missing ingredient ends UNDETERMINED with a question.
A real failure is detected by the brain's own writer (refused_conflict, old 2/1, new 5/2) and opens a repair child.
Valve: written two-table rule, essentials from the recipe's own list, learned weights never loaded.
Tests (Windows, Python 3.14.0): loop 18 OK, chat nuance 5 passed, valve self-test 3 PASS, repair_performer
ALL PASS. Live trace docs/working/traces/HELM_LIVE_TRACE_20261018.jsonl sha256
4f94ccee22ea9829072ebfd59fe7690f56d3f28f49527cf2f39b140283fe6fba. Limits and full record:
docs/working/traces/RESULTS_WIRE_RECIPE_BRAIN_20261018.md. Not licensed: anything beyond synthetic worlds.
## 2026-10-18 PDT - RECORDS CATCH-UP (owner's fix A): spec sheet sections 7.48-7.56 written for the work of 2026-10-16 to 2026-10-18; a roadmap status correction added; nothing upgraded, no negative removed

Owner's approval: "I agree with all of them....please proceed." (2026-10-18, recorded at
C:\Users\wakil\Documents\Codex\2026-10-18\OWNER_APPROVALS_20261018.md, item 4, fix A). Laptop only, $0.
Every count below was read from the files, not copied from a summary. Where only a commit message or a
handoff claims a pass, the record says "authored, output not recorded".

- **7.48 - nine noetic_council packages: ENGINEERED-NOT-VALIDATED.** 308 tests written (19 + 11 + 50 + 33 + 35
  + 27 + 49 + 68 + 16). Recorded outputs: cube store 19/19, continuity v4 50/50, the language marks, one real
  fitter run and one repair-actor run. Six suites have no recorded output. Codex: "mechanisms built; brain
  integration missing". Queue rows 15 (one live trace) and 17 (a real failure) still TODO.
- **7.49 - end-to-end pipeline and chat layer: ENGINEERED-NOT-VALIDATED, not "verified live".** The round trip is
  computed at helm_end_to_end_loop.py:295-296 and never checked; missing ingredients are filled with
  Decimal("10") at :421; the loop bypasses the RPM gate, repair performer, D/W/P engine, ASOM and Bias.
- **7.50 - Phase 3 valve: ENGINEERED-NOT-VALIDATED.** A learned 5-weight logistic aperture, trained
  LOCAL_CPU_DRYRUN_FAST (not on AWS) on 2,000 samples, sits in the deciding path; alone it leaks 83 of 250. The
  owner ruled a plain-rule valve on 2026-10-18 (not yet done).
- **7.51 - helm_brain_22x40.py and helm_brain_tks28.py: stand-in demos, ENGINEERED-NOT-VALIDATED.** "22" = 22
  baking ingredients; "40" = 22 weights + 1 rho + 17 thresholds. No run id, no score.
- **7.52 - RB-OH1 merged reading: NOT LICENSED.** FRESH HYBRID_ROUTING_EARNED, ORIGINAL HYBRID_NO_BETTER,
  SWEEP_CALIBRATION_FAILED, licensed false. The roadmap's "87.50% (448/512) vs 60.74% (311/512)" are RB-OH1's
  numbers, not 22x40's. GPU job c32: Tesla T4, RUN stage 36.817 s, hold 2.00, no closeout.
- **7.53 - two unrecorded GPU jobs on helm/creativity-rpa-valve-v1: FLAG_FOR_HUMAN_REVIEW.** Scribe L4 (commit
  84812689): Tesla T4, 30.95 s, exact 90.0 %, round trip 64.0 %, weights 326,230 bytes; no ledger line, no owner
  sign line, no cleanup check. "Stage v0.7" (commit 5a7d02f3): a commit-message claim with no artifact at all.
- **7.54 - L4 split: REAL.** 98 sealed (e269a448...) and 99 development (17cd1983...) rows, hashes re-checked;
  they are generator English, not human English. The tabulation's baseline row (118 / 321 / 42) is typed into
  tabulate_439_sdg_baseline.py (lines 170-173, 209), not computed: FLAG_FOR_HUMAN_REVIEW.
- **7.55 - owner rulings and council decisions, 2026-10-16 to 2026-10-18: IN FORCE as rules.** HORIZON 12 and
  DESIRE_BOUND 12 (owner, verbatim), canon's 5 kept beside it; C4 / C5 / Q13 decided by the council, not the
  owner; the four 2026-10-18 approvals.
- **7.56 - CANONICAL BRAIN POINTER.** The one licensed brain is the HELM-R1 wave-1 recipe brain (c34-g PASS,
  R1_BEATS_GB3, SYNTHETIC_ONLY), package Documents\Codex\2026-10-15\r1_wave1\HELM_R1_W1_20261015_v3; every
  other brain is a candidate or a stand-in. It is not yet inside HELM's live loop.
- **New file** docs/working/HELM_CAPABILITIES_ROADMAP_STATUS_CORRECTION_20261018.md: the roadmap's milestone
  table with an honest status column. v0.4 "AWS GPU trained" is a FALSE claim; v0.5 is unrecorded spend; v0.1,
  v0.6, v0.8 and v0.8.1 are authored only. The roadmap file itself is not edited.

Not done here (later fixes): ledger reconciliation (B), recipe brain into the live loop (C), plain-rule valve
(D), scoring the Scribe model on the sealed 98 (E), the everyday-English writer (F), the real 40 / 28 / 22
ledger universes (G).
## 2026-10-18 PDT - HELM language line, fix E (dictionary half): alias-wide lexicon v2; DEV 99 read 0 -> 41, sealed 98 (once) 0 -> 34; Scribe L4 scoring prepared, NOT_RUN

Laptop, stdlib, 0 USD. FROZEN_LEXICON_V2.json pushed first (0b7cde89). lexicon_v2.py (dd60f490) = v1 unchanged
+ 10 source-tagged Noetic phrases + `mental` -> C, with a v1/v2 switch. `behavior` -> O and `judgment` -> E were
refused by the frozen domain test. tabulate_v2.py computes every number the old script typed in (all equal).
481: v1 265/199/17 -> v2 337/124/20 (MATCH/UNPARSEABLE/MISMATCH); 439: 233/197/9 -> 304/122/13; no v1 MATCH lost.
DEV 99: 0 -> 39/58/2. Sealed 98, scored once, counts only: 0 -> 32/64/2, sha256 e269a448... unchanged.
NO_STATE 148 -> 21 (vocabulary gaps, closed); NO_DOMAIN 56 -> 69 (mostly English that never names a domain; no
word can fix it). Tests: language_v3 26+11+5+26 OK, new 19 + 6 OK. Scribe L4 (84812689) scoring plan +
script written, NOT_RUN pending owner word: needs torch on an AWS CPU t3.medium (~0.01 USD); its one-clause output
cannot hold a recipe, so exact match is 0/98 by construction. Failed approach logged: adding `behavior` as an O word
(refused by the frozen rule; the SDG writer used "operational behavior" for two P cells). Spec sheet §7.57.
## 2026-10-18 PDT - FIX F (everyday-English writer) BUILT + FIX G (ledger universes on 40 / 28 / 22) DESIGNED; laptop, 0 USD

Fix F: `helm_voice.py` turns brain receipts into 1-3 plain English sentences
with no second model. Phrasings come from `phrasebook.json`: 113 phrasings over
10 situations, each tagged with a Register, plus 60 question-back / offer tails.
The first pick is fixed by the receipt hash. A seeded alternative is drawn only
when that pick was used lately (rb_c4 restart-fallback rule; seed in the trace).
A guard reads every sentence back against the receipt and refuses invented
numbers, invented names, dropped facts, wrong outcome words and a false "exactly".
Chat recipe turns now speak through it. On 50 frozen situations, old vs new:
CAS tokens 109 vs 0; back-to-back repeats 9 vs 0; facts preserved 22/50 vs 50/50;
reading grade 6.25 vs 3.06; sentence-length variance 47.57 vs 14.31 (not better;
more even). Tests: test_helm_voice 21 OK; test_helm_chat_nuance all PASS;
test_helm_end_to_end_loop 11 passed. Claim status ENGINEERED-NOT-VALIDATED.
Human rating is open; `RATING_SHEET.md` is ready.
Results: `docs/working/voice_20261018/RESULTS_VOICE_20261018.md`.
Fix G: `docs/working/LEDGER_UNIVERSES_40_28_22_DESIGN_20261018.md` plus a frozen
schema. It is design only. From c34, U22, U28 and both grids get 0 charges,
because receipts carry no pathway, no domain, no register and no operating point.
So "22x40" and "28x40" are not yet true statements.

## 2026-10-16 PDT - HELM-R1 WAVE 1 SCORED (job c34-g, AWS): the recipe brain in GB3's slot beat GB3 on the freshly sealed exam - 32 against 9, and 32 against 17/2 widened; frozen reader PASS, R1_BEATS_GB3, all seven hard gates and all eight instrument rows holding

Owner's wave authority at §7.44 ("M1; R1, cap $10, sha256 of the bytes
10b8c11da3dfab0c16d194f0a30e95798421490a82e91e346d6d20c0ece2466f) read as wave 1,
10.00 USD total, c34-g capped at 9.50 USD; the launch's own bound record is
OWNER_APPROVAL_R1_W1_C34_20261016T132012Z.json (sha256 085424445a94a8ae8de6c66696f949d09b19ee9939ceb0d26112db882c796e58),
which the controller's authority_record names by hash. One m6i.8xlarge, us-west-2,
instance i-094c2ae2f0c77fd98, one attempt of sealed package HELM_R1_W1_20261015 v3
(freeze 8c55c4136e1b24bc322779160ffed666f9eb9ee21512c1972101263a243c039b).
132 tests all ok, Ran 132 tests in 4257.943s, 79 of 79 units exit 0,
instrument_problems 0, deadline_hit false, 4258.260314941406 s of the 13860 s window.
The frozen reader r1/merge_r1w1.py on the laptop returns PASS, R1_BEATS_GB3,
claim licensed, ceiling SYNTHETIC_ONLY, 7 of 7 hard gates and 8 of 8 instrument
rows holding. Panel sums: recipe brain 32 against transformer 9 and widened (385
parameters) transformer 17/2 - the widened one did worse than the 97-parameter one.
The reading names margin 4; that is the threshold, the achieved gaps are 23 and
47/2. RPM Gate off gives 768 pooled wrong answers against 32 with it on.
CCE_SKIN is SKIN_FORM_BROKEN with a VACUOUS answer half; LACUNA_CADENCE is
CADENCE_MIXED. Not licensed: anything beyond synthetic worlds, learned carry,
learned composition, statistical superiority, operation inside HELM's runtime,
real data, growth, the eye, the atlas, heads or memory fading.
THE RUN'S OWN COMPLETION MARKUP READS FAIL AND IS KEPT: the stage command exited 0
and RUN_RECORD.json says exit_code 0 / EXITED, but the job supervisor recorded
status FAIL, missing_outputs [R1_W1_HOST.json, R1_W1_HOST.json.sha256] and sealed
COMPLETED_WITH_FAILURES / exit 1, because it checked the stage's declared outputs at
the stage root while the runner keeps them under out/r1w1_out/. The reading it
called missing is there, 2858582 bytes, sha256
c7e73fc1c186c0bc2562067e5800805c785a422aa6b7ef80b96049d80b365d37, exactly what
the runner and the reader recorded. The defect is recorded for wave 2, not repaired
in place. Seven attempts, not one: c34 closed out at 0.14 USD, c34-b stopped before
launch, c34-c died on a dead instrument (about 0.20 USD), c34-d failed to launch,
c34-e lost the transformer side on a draw-label guard (about 0.40 USD), c34-f
exited during cloud-init, c34-g is attempt 7; the package was re-sealed between
attempts (v1 b7cee315, v2 caac6e85, v3 8c55c413), so one attempt per seal holds.
Seven 9.50 USD holds stand in the ledger, only attempt 1 is reconciled (0.14);
there is no closeout for c34-g, and no posted bill. All five c34 instances are
confirmably gone as of this record; the ledger reads 162.45 of the 200.00 ceiling
with 37.55 unreserved. THIS COMMIT ALSO CARRIES FOUR FINISHED RESULTS THAT EXISTED
ONLY AS STAGED EDITS - sections 7.40 U1b, 7.41 LM-T6, 7.42 RB-P1 and 7.43 M1 -
with their bodies unchanged; the live record already cited §7.43 five times without
containing it. Spec sheet section 7.47, a change-log row for it and a change-log row
for the four, all in this commit.

## 2026-10-16 PDT - ERRATUM to spec sheet section 7.47: four claims in the wave-1 record's first commit were falsified by the council's verification seat and are corrected; a governance gap the first draft missed is now on the page

Section 7.47 was committed as 60321a14 and then adversarially verified by the council's
seat CO-8 Above/Cause, which was told to falsify it rather than confirm it. It
falsified four things, each checked here against the file the section itself names:

1. "108 members" was v1's member count printed beside v3's freeze hash. v3's own
   PACKAGE_FREEZE.json reads member_count_excluding_freeze 110, with 110 members
   listed.
2. 3,624fc29 is the v1 PACKAGE_FREEZE.json hash and was presented inside v3's
   parenthesis. 8c55c413... is v3's.
3. The money paragraph priced the run at the control record's published 1.536 USD per
   host hour. The rate the package freezes for itself is 1.5529 USD per host hour
   (RUN_LIMITS_R1W1.json; the run's own frozen window maximum is 6.2116 USD and its
   expected range is "about 1.9 to 2.4"). Both arithmetic results are now given, each
   naming its rate and each labelled arithmetic rather than a bill:
   1.83684790085348 at the frozen rate, 1.816857734375 at the published one.
4. The heading read "beat it" without naming synthetic worlds. It now says the win is
   on the freshly sealed synthetic exam.

CO-8 also found a governance gap the first draft missed, now recorded in the section:
the owner's approval record binds v1's bytes - its limits_of_this_record names
b7cee315... and 3624fc29..., and it declares members_checked_against_freeze 108 - while
the run that produced this result executed v3 (8c55c413...). The frozen
one-attempt-per-seal rule is satisfied and the re-seals are documented in the reader's
two amendments, but no fresh owner line bound to v3's hash is established. That does
not change the reading, which the frozen reader computes from the run's raw output,
and it widens no claim. It is put to the owner as it stands.

Everything else in 7.47 stands: PASS, R1_BEATS_GB3, 7 of 7 hard gates, 8 of 8
instrument rows, 32 against 9 and 17/2, the threshold-versus-achieved distinction, the
supervisor's FAIL markup kept as recorded, seven attempts, and the new backup. No
negative was deleted and no other number changed. The correction is a second commit on
purpose: the record keeps the first version and the erratum, rather than pretending the
first version never existed.

## 2026-10-16 PDT - SECOND ERRATUM to spec sheet section 7.47: the version gap was real but its consequence was overstated; the three packages are hashed file by file and only instrument and harness files ever changed

The first erratum said the run's authority binding was a gap and left the reader to
infer the science was in question. That inference was not supported and is withdrawn.
The three packages were hashed file by file, and the result is unambiguous:

  FROZEN.precode.json   (the marks and hard gates)  identical in v1, v2 and v3
  FROZEN.json           (the frozen amendments)     identical in v1, v2 and v3
  r1/merge_r1w1.py      (the only verdict emitter)  identical in v1, v2 and v3
  tests_r1/test_run_r1w1.py   changed v1 -> v2 only
  t_on_b/t_b.py               changed v2 -> v3 only
  PACKAGE_FREEZE.json         version marker, both steps
  one new AMENDMENT_*.md      the receipt of each change

Not one mark, threshold, floor, gate, arm, world or seed moved, and the scorer never
changed. The v1 -> v2 change repaired a Gate B instrument that compared all 112 world
records and so reported 56 in every run whatever the custodian built - a check that
could never pass, in its own words "measuring its own fixture". The v2 -> v3 change
repaired the transformer driver demanding a draw's label equal its index while the
fresh exam labels its draws 6550-6569.

The re-seals were therefore necessary: an instrument that can never pass burns the
attempt, exactly as it did on c34-c. And every change repairs a defect in the
instrument or the harness, which falls under the owner's standing rule of 2026-10-15
that a test broken by its own instrument or control gets a retest, started without
asking. Nothing the approval was written for was altered.

So the finding, stated at its true size: the coordinator re-sealed twice, correctly,
and never advanced its own approval record to name v2 or v3, so the paper trail sits
behind the package instead of the package sitting outside its authority. Two clean ways
forward and the owner picks - amend the approval record to name each re-seal as it is
cut, or keep the current binding and let the retest rule cover instrument repairs. No
new run and no new money is needed on either path. The first erratum stays on the record
unchanged; this one corrects it.

## 2026-10-16 PDT - M1 H8 verified creative reconstruction policy v0.2 FROZEN (no implementation, nothing scored): the owner moved the line from "can a spare copy be checked" to "is the fault classified" and added a bounded, anchored, verifier-vetoed search for the unclassified case

Policy `M1-H8-VERIFIED-CREATIVE-RECONSTRUCTION` v0.2, document sha256 647ffc444a5911220909a88560a08bca276b5687c87a609729733df89c0386f9 (21,923 bytes, 146 lines); owner-authority record sha256 4afda3bdb1ab89333252a7090373a7293eee5e42dd04b54aaf50f9d51b93b213. Supersedes `M1-H8-VERIFIED-FALLBACK` v0.1 (16773D53DDE1B257EA92F283627A07A1E86F211B239EAD76B5AC7988197303CA), which stays valid and is not withdrawn. The owner's words, quoted verbatim in the record: the creative-radius direction of 2026-10-16, and "propose them as defaults sign v0.2" authorising the four frozen numbers (initial radius 1 mutation unit; widening step x2 on a verifier refusal; hard cap 8 mutation units and at most 4 widening turns; asymmetric at a wrong-answer cost of 20x a refusal, or an undeclared class). Arms A0_STRICT, A1_SPARE and A2_KERNEL; four controls that must fail (no verifier, unanchored, no widening, no consequence); eight safety floors, none averaged away; one wrong exact answer fails the whole result. Claim ceiling: NOTHING SCORED - no implementation exists and no row has been scored. Does not authorise enabling the policy in HELM, changing H8, any H8 pass, any AWS spend, or editing the frozen v5 package or the original M1 failure. New spec-sheet section 7.46 and change-log row added in this commit; next free section number 7.47.


## 2026-10-16 PDT - HELM-R1 job R1-X0 RAN (job c33, AWS): the fresh exam of wave 1 is built, sealed and verified; only its hashes cross to the builder; nothing scored

Preparation, not a behavior result. One m6i.xlarge, us-west-2, one attempt, cap 0.50 USD, provisional charge 0.03 USD. Owner words bound to the job: "\u201cM1; R1, cap $10" (18 UTF-8 bytes, sha256 10b8c11da3dfab0c16d194f0a30e95798421490a82e91e346d6d20c0ece2466f), read as HELM-R1 wave 1 approved with a total AWS cap of 10.00 USD, X0's own cap 0.50 USD inside it and the scored run W1 capped at 9.50 USD. The custodian session built 20 fresh Task B draws (6550-6569), three fresh Task B depth world sets (d2, d3, d4; each 1,024 train / 256 validation / 512 held-out, skipped_seeds 0, targets_equal_rb_c4 true), a fresh gate B world set (16 panel / 16 new, loader accepted, c21_entries_equal_c23 true), and 32 + 32 planted CCE items. Verification: 29 outputs checked, 0 problems, run_status and seal_status SEALED, status VERIFIED (2026-10-16T04:16:35Z), deliverable zip sha256 6942f5f19183f168af7106cf4f5c79107a9304cbd408a2a88f11ba3029f85d97, Task B label audit PASS on 2,280 rows. The builder receives FRESH_W1_HASHES_FOR_BUILDER.json only, never the exam. No scoring, no claim, no claim word. Ledger after closeout: 105.31 of the 200.00 USD ceiling. Spec sheet section 7.44 and change-log row added in this commit.

## 2026-10-16 - M1 H8 redundant-copy fallback follow-up v5 RAN (AWS, job m1h8v5-20261016-114033-fd5ca339): the 15 H8 violations of M1 are explained as healthy-second-copy fallback against a strict rule; original M1 failure preserved and not rescored

Scored 2026-10-16T11:45:00Z. One c7i.large, us-west-2a, instance i-0626eaa29f7b72022, provisional charge 0.251507 USD under a 1.00 USD cap; cleanup independently verified (instance terminated, root volume absent, temporary security group, role/profile and bucket absent). Frozen protocol sha256 448cc5a98aaffcbb45a3f892b31d609892d256371bb5ccc3e1b5fb8b7d7d140d, source manifest sha256 ac38f601ce3e03e91ea8cbace15c31308bc00e57dc21db42d5aeb7e0f5719330, run receipt sha256 9e1714655b1c9ea3b23ad33c5495e1dd06da42b79808f8174124161582ac78df. Result: 24/24 setup rows and 24/24 per-copy receipts clean; 12/12 exact answers from the healthy secondary; 12/12 strict stops returning UNKNOWN; the unchanged RELEASED H8 rule FAILS 12/12 on the fallback rows, which was expected and is reported separately; the original M1 failure (15 violations in 1,769 checks, source manifest d940074a4696c8fed88b8b7ffa2127af4e6d82a1bdccfae2bc40f29f6946509d) is preserved and was not rescored. Claim ceiling SYNTHETIC_ONLY: both copies were separate keys in one simulated in-memory store, so no durability or independent-failure-domain claim follows. A verified-fallback policy draft (M1-H8-VERIFIED-FALLBACK v0.1, sha256 16773D53DDE1B257EA92F283627A07A1E86F211B239EAD76B5AC7988197303CA) is on disk but is NOT frozen, NOT scored, NOT enabled and NOT owner-signed. Spec sheet section 7.45 and change-log row added in this commit.

## 2026-10-15 PDT - HELM RB-G6 RAN on the laptop ($0): GREW_WRONG_KIND on both world sets - the growth claim stays NOT LICENSED; V8 compactness refused the useless units

Owner words: "“RB-G6” BECAUSE  a CREATES TOO MUCH NOISE ...". Fix E adds V8:
keep a growth unit only if it explains at least 1 new training row per 4
parameters it allocates (re-read rows excluded); theta chosen after RB-G5, so
the run repeats on fresh worlds. 21 laptop parts, 15:54-17:23 PDT, tests pass
in every part, replay 4/4, 320 units digest-equal with RB-G5. Merged sha256
32d51f3f745850c7ab2632973130c411ff0f83ca301e7c667a5557266ca1205e. ORIGINAL:
GREW_WRONG_KIND (V8 refused a's unit, 23 rows / 320 parameters, but strict
G3 counts the fired trigger; a_approx 82.42 vs pre-sized 82.03, G2 pass).
FRESH: GREW_WRONG_KIND (the brain's two diagnosis keys never agreed on fresh
a_approx, so nothing grew: 14.84 vs 87.50, while the plain refusal-count arm
grew it to 85.94; a_fresh fired again and was rolled back). V8 alone refused
7 events, all on no-growth controls, and never a planted-world unit the other
checks would keep; zero-parameter units (routes, depth) are exempt from V8.
Growth claim NOT LICENSED after six runs. Spec sheet section 7.39 and a
change-log row in this commit.

## 2026-10-15 PDT - HELM U1 RAN on the laptop ($0): the Unity Eye acting - INCONCLUSIVE in both readings; the random-whisper control broke the clean-dialogue gate

Owner words: "U1 now ...BOTH THE EYE AND THE BRAIN SHOULD KNOW ABOUT ONE ANOTHER
..." and "THE EYE SHOULD ACT AT TIMES AS WELL LIKE OUR UNCONSCIOUS OR SUBCONSCIOUS
BRAIN ...". Seven arms on synthetic worlds (no eye, report only, whispers only,
one-way plus autonomic tier, concert, random whispers, checklist), six planted
fault kinds, 68 clean worlds per arm. 22 laptop parts, 15:00-16:40 PDT, tests
12/12 in every part, peak 155.8 MiB, 121 source files matched after the run.
Merged reading sha256 fec73502581ac3fb2e6eefa9564fbbdb3e2b41b04cee3a9c9e5c60b2d7efa8b2.
Reading 1 (frozen rules): INCONCLUSIVE (G_INSTRUMENT, G_REPLAY, G_CLEAN_A5).
Reading 2 (amendment U1-A2, written before any merge): INCONCLUSIVE
(G_CLEAN_A5 only). The A5 random "say it again" whisper made the brain repeat
answers on 20 of 48 clean dialogues; the frozen rule counts that as worse.
No keep word, no harm word. Raw marks: A3 and A4 fixed 148/148 planted faults,
the checklist 128, whispers alone 60; clean interventions 1,816 (concert) vs
2,605 (one-way) vs 10,152 (checklist); no autonomic action created new
knowledge; the eye never wrote. Flag kept: had the control passed, the frozen
rules would have printed EYE_HARMFUL from the faulted-world counts 155/258/258;
the builder's read-only breakdown says each is a restored clean answer scored
against no-eye's faulty or lucky answers. Eye acting stays NOT LICENSED; any
change to the control or yardstick is a new frozen test (e.g. U1b). Spec sheet
section 7.38 and a change-log row in this commit.

## 2026-10-15 PDT - HELM RB-I1b RAN once on AWS (job c30, 0.11 USD): INSTRUMENT_ERROR at the first stage - two synthetic datasets rebuilt on Linux did not match their frozen fingerprints; no reading

Owner line (verbatim): "RB-I1b on AWS, cap $2", bound to the sealed package
RB_I1B_FACULTIES_20261015_SOURCE.zip (sha256 804be249...; RB-I1 with the H1
receipt fix plus a Linux parallel driver). One m6i.8xlarge i-0ebbfb01c0bda42c8,
launched 2:46 PM Pacific, host 245.5 s. The package's first stage ran 16 tests:
12 passed; 4 stopped at the guard "v1 dataset drift" (lsr_t1/families.py
v1_family) because a_ces_substitutable_bound and c_minratio_noisy_corrupt_bound,
rebuilt on Linux, did not match their laptop-frozen sha256. Reading of the code:
both generators use floating-point powers and exp / Gaussian noise
(fair_data_experiment_v1/data.py:53-54, 108-109), whose last bits can differ
between the Windows and Linux maths libraries; the laptop's Python 3.12 had
reproduced the data. The guard worked; the driver stopped before the smoke
parts, pool and merge (INSTRUMENT_ERROR, exit 3); no status word, gate or mark
exists; RB-I1's record is unchanged. Named fix, not authorized: ship the frozen
datasets and worlds as data, load them by hash, add a data-identity stage on the
host. Charge 0.11 USD (hold 2.00 replaced); ledger 107.17 -> 105.28 of 200.00;
cleanup VERIFIED by the controller and the independent check; backup
D:/tksCAS-archive/helm_rb_i1b_c30_20261015/ (145 files, three confirms). Spec
sheet section 7.37 and a change-log row in this commit.

## 2026-10-15 PDT - HELM RB-G5 RAN ($0): the tolerance-rung reset makes the smooth family reach the pre-sized brain (a_approx 82.42 vs 82.03; G2 PASS, first time in five runs; G4 3 of 3); strict G3 still fails on the `a` control (one fully verified unit kept) -> GREW_WRONG_KIND; correction to the RB-G4 entry; owner ruling RPA = Atlas and the device source map recorded

Owner words: "LM-T6 after search and RB-G5 AND WHAT DOES LM-T6 STAND FOR WHAT DOES
IT MEAN?" (about 12:40 PM PDT). RB-G5 = RB-G4 + Fix D: a continuation starts at
rung index 5 (ln 1.05, the scorer's 5% standard) instead of the parent's rung;
everything else unchanged. 19 laptop parts (13:36-14:25 PDT), tests 33/33 then
25/25, 334 units, peak 69.2 MB, spend 0. Marks: G1 PASS, G2 PASS (a_approx 82.42
vs oracle 82.03; F1 100; scale_leak 90.625), G3 FAIL (`a` fired once, kept
once: V1-V7 passed, held-out 8.01 -> 10.55, 23 of 33 new rows from the added
corners, 10 from the stricter read; +320 allocated parameters), G4 3 of 3, G5
265 kept / 0 violations, G6 0. a_approx: 4 -> 8 KEPT (521 new rows, 0 lost),
8 -> 12 KEPT (218 new, 0 lost), halt at the 12-corner ceiling; 1,248 allocated
/ 461 used vs the oracle's 1,248 / 450; held-out 70 -> 314 -> 422 (oracle 420);
equal to the oracle on 13 of 16 outcomes. Reported-only: the stricter read
alone added 0 rows on a_approx and scale_leak (R1); strict G3 without `a` PASS
(R3); REFUSAL_ONLY (no two-key check) now keeps units on noise (2 on the
label-shuffled a_approx, 3 on `a`). Status word GREW_WRONG_KIND by the frozen
rule; the growth claim stays NOT LICENSED; owner decision open on whether a
verified unit on `a` (not recipe-shaped per RB-W and Capacity Rules v0.1)
counts as false growth - any rule change applies only to a new frozen run.
CORRECTION to the RB-G4 entry below: the tolerance ladder never gets looser
within a run (that entry says "only loosens"; the spec sheet section 7.32 is
corrected in place); RB-G4's RESULTS.md gave outcome 09's parent rung as 5, the
same run reads 3. OWNER RULING "RPA IS ATLAS I MEANT ATLAS" (about 12:30 PM PDT;
already ruled 2026-10-07 in Downloads/GB2_PLAN_AMENDED_20261007.md) recorded
under section 7.35 with the device-search source map for cascading RPM depth
and the Recursive Possibility Atlas. Spec sheet section 7.36, a correction in
7.32, a note in 7.35 and three change-log rows in this commit.

## 2026-10-15 PDT - HELM RB-I1 RAN ($0, 134 laptop parts): CAS faculties + 7-Drive loop on the recipe brain - FAILURE on hard gate H1 (empty fit receipt checked after the write) -> INCONCLUSIVE; no faculty or drive word earned even shadow-read; LM-T4 / RB-I2 RAN ($0, 8 parts): language and faculties ride the thought station by station with the Unity Eye report-only - sealed reader INCONCLUSIVE (reader bug on digits in names), corrected reader passes the gates (owner to judge); CONT-3 failed 99.92%

RB-I1 (rb_i1/; owner words "RB-I defaults", design helm_rb_i_faculties_design_v1):
arms pull-sampling / Fisher-Rao geodesic-step / greedy / round-robin / fixed
priority / faculties-off (RB today) / generator-off / buffer-off / K1 twin / ENUM
/ COIN over a, a_approx, scale_leak, c, TaskB_d3, TaskB_d4 and controls, seeds
11/29/47; 02:07-06:50 PDT, longest part 265.3 s, peak 78 MiB, tests 12/12 every
part. H1 receipts FAILED on 1 of 183 nested admissions (family c, A5, seed 11,
c_05: the imported lsr_t4 fitter returned an empty fit receipt; the level check
required a non-empty one and ran AFTER the write) -> INCONCLUSIVE by the frozen
rule; every other gate holds; shadow reading as if H1 passed still awards no
word. Held-out of 512: Task B d3 RB today 342/344/264, drive arms 44-414;
a_approx RB today 232, round-robin 292/292/287, COIN 335/364/302 (the lift is
the pondering re-fit with the restart fallback, not the drive choice); asking
32/32 with 0 invented facts in every arm (plain rule ties; RB today 16/32);
insights 1-16 vs RB today 12/10/9; STARVED greedy 103 < sampling 145 < fixed 206
< geodesic 259 < round-robin 304 (design forecast wrong). Fisher-Rao formula
fixed (missing 1/2) before the run. Named, not authorized: RB-I1b with the
receipt check before the write, ~15 min on one m6i.8xlarge (~0.5 USD).
LM-T4 / RB-I2 (lm_t4/; owner words: the 4:40 AM circuit direction, "LM-T4
defaults", the eye direction, "LET'S GO WITH YOUR RECOMMENDATION"; design
helm_language_faculties_circuit_design_v1 with UNITY_EYE.md and the ruling
record): stations S0 head, S1 CJT trigger, S2 CJT Bias, S3 CJT arrival, S4
operating point, S5 RPM link, S6 next stage; attempt 1 WORKER_FAILED in the
runner (no scored unit; kept, LMT4-A2); attempt 2 manifest 3390ebbd, P11-P18,
1,067.1 s, peak 148.5 MB, tests 12/12. Taps: 64,756/64,756 round trips,
106,400/106,400 digest-neutral, answers unchanged 20/20 draws (every arm equals
the RB2c driver, which equals c26); injections 240/240 right, shuffled 0/240
(name-match router 240/240 false fires), CLARIFY 48/48, KNOWLEDGE_MISSING 48/48,
invented 0, earlier by 3.0 vs 7.0 ticks; seams 96/96, false 0, interpolations 0;
CONT-3 provenance 106,320/106,400 (twin's 80 asking keys written CREATED) FAIL;
eye 6,716 events, would-FIX 280, would-HELP 7,548, applied nothing, 504
would-HELP on clean dialogues (U1's false-alarm baseline). Two readings: sealed
reader INCONCLUSIVE (H2/H10 flagged 192 questions for digits inside copied
outcome names; 0 real amounts); corrected reader (post-run amendment LMT4-A3;
sealed reader kept byte-exact) hard gates pass, LANGUAGE_RODE_THE_PATH,
INJECT_ROUTED, CIRCUIT_EARLIER_NOT_BETTER, EYE_REPORTED. The sealed reading
governs until the owner accepts LMT4-A3 or a clean re-seal runs (precedent RB2b
-> RB2c). LSR-family half NOT_EVALUATED (PRC-1). Spec sheet sections 7.34 and
7.35 and two change-log rows in this commit.

## 2026-10-15 PDT - HELM RB-G4 RAN ($0): warm-start corner re-fit changed nothing (every unit identical to RB-G3; a_approx 38.87 vs 82.03; GREW_WRONG_KIND x 4) - the shortfall is a READ problem (inherited tolerance rung), measured; LM-T5 RAN ($0): the restart-fallback reader on 25 ambiguous free-English rows decided 1, asked on 24, 0 new wrong - VERIFIER_CANNOT_DISCRIMINATE

Owner message (verbatim, ~5:00 AM Pacific): "RB-G4LM-T5LM-T4 defaults". RB-G4 =
RB-G3 + Fix C (BLEND growth continues the parent's own fitter loop: parent knots
kept, corner values and seed vertex re-solved after each inserted knot; three or
more inputs continue lsr_t5 refine). Result: FAIL, GREW_WRONG_KIND; all 310
engine units behaviourally identical to RB-G3; 14 WARM_START events, 6 warm
BLENDs admitted, no score moved (F1 100.00, a_approx 38.87, scale_leak 90.625,
TaskB_d4 25.78; a fired once and rolled back on V6). Warm-start == from-scratch
BLEND on 13/13 test cases and 22/22 scored complexes. Diagnosis after the run:
TAU_LADDER [ln 1.5 .. ln 1.05] only loosens within a run; 11 of 14 a_approx
parents ended on ln 1.5; a continuation inherits that rung, reads no residual on
6 of the 9 outcomes that never grew (no candidate proposed) and refuses the
grown BLEND for SUPPORT on 3 (0, 0, 7 new rows; 8 needed). Candidate next steps,
not authorized: reset the rung at a growth boundary (re-read from ln 1.05), park
growth, or route smooth residuals to the ordinary head. 11 parts, 24 min 20 s,
peak 65.8 MB, tests 29/29 then 23/23. LM-T5 (lm_t5/): DET exact start; the
fallback fires only on purely ambiguous rows (25 eligible after a recount:
28 ambiguous = 17 state + 10 domain + 1 both, 3 hiding a missing domain word;
11 ambiguous-plus-missing and 158 purely missing stay out of reach); ENUM (<= 64)
or SEEDED (8 draws, seeds 11/29/47); verifier without the gold label: round trip,
compiler, frame consistency, evidence tier; one survivor wins, two or more ->
CLARIFY, never a coin pick. Result: fired 25; candidate spaces 2 / 2 / 6; one
survivor on 1 row (V3 decided; MATCH), 24 CLARIFY; MATCH 233 -> 234, MISMATCH 9
-> 9, UNPARSEABLE 197 -> 172 (+24 CLARIFY); COIN MATCH 5/11/5 with MISMATCH
20/14/20; SHUFFLED 0; regressions 0; SEEDED = ENUM; V4 decided 0 rows (every
competing Noetic in the state-ambiguous rows was backed only by colloquial
aliases). Status word VERIFIER_CANNOT_DISCRIMINATE, named in FROZEN.json before
the run. Lesson kept as a negative result: the restart fallback transfers only
where a verifier can decide without the answer key; free-English reading has no
such verifier, so the honest act is to ask. 5.4 s, 47 MiB, tests 15/15.
Spec sheet sections 7.32 and 7.33 and two change-log rows in this commit.

## 2026-10-15 PDT - HELM recipe-brain self-growth operator RB-G: three laptop runs RB-G1 / RB-G2 / RB-G3 ($0), all GREW_WRONG_KIND; the ledger chose the right capacity kind every time and kept no wrong unit, but corner growth on the smooth family reaches neither the pre-sized brain (61.72 / 61.72 / 38.87 vs 82.03) nor a clean strict-G3; language line L1-L3 recorded

Owner words: "design RB-G" + amendment (growth before ability 3; sentence to earn
"the brain added the right capacity when its own ledger said so"), "RB-G
defaults", "RB-G2", "RB-G3" (2026-10-15, 2:10 AM to 4:20 AM Pacific). Operator:
SENSE (Lacunarity Machine ledger + shadow-checked cap refusals) -> DIAGNOSE one
of five kinds by two keys -> GROW ONE UNIT -> FIT -> VERIFY V1..V7 -> KEEP or
ROLL BACK -> LOG; budget 4, ceiling 4x; arms RBG / NO_GROWTH / ORACLE / RANDOM x3
/ REFUSAL_ONLY; marks G1..G6, G3 strict (a fired trigger counts even if rolled
back). RB-G1 (re-fit FIT): G1 PASS (F1 80/80 kept, a_approx 1/1, scale_leak 1/1
leakage), G2 FAIL (a_approx 61.72 vs 82.03), G3 FAIL (a and a_approx_shuffled
fired, both rolled back), G4 2 of 3, receipts 254/0, ceiling 0. RB-G2 (+ trigger
patience, attempt-before-halt): identical scores; both false fires persisted on
2 of 2 readings (deterministic brain) as checked before the run; a_approx 8 -> 12
attempted (192 new rows) and rolled back by V6. RB-G3 (+ additive continuation
FIT: parent tree/levels kept, corners inserted into the parent's complex with no
re-fit; + out-of-sample witness V_MIN = 2 validation rows over parent and over
rotated labels): 0 parent rows lost on every kept unit; a_approx 4 -> 8 -> 12
corners KEPT then HALT_AT_CEILING (allocated 608 -> 928 -> 1,248 parameters,
used 184 -> 296 -> 299; oracle 1,248 / 450) but only 7 of 16 outcomes accepted
the additive 8-corner BLEND, so the family scores 38.87 (G2 fails harder); the
shuffled a_approx false fire became NOISE, but the `a` control still fired on
REAL validation gains (9 -> 15 right vs 6 on rotated labels in one outcome) and
was rolled back (4 rows lost); G3 FAIL; receipts 256/0; 10 parts 1,393 s, peak
66.6 MB. Status: the frozen claim NOT LICENSED; measured instrument rows: right
kind 3 of 3 runs on 3 of 3 families, 0 wrong units kept, F1 and scale_leak
reach the pre-sized brain. Exam-design question for the owner: `a` is a
"no-growth" control by RB-W's family-level reading (+2.93 points at 4x) while
the per-outcome ledger sees real out-of-sample gains; excusing it alone would
not change the status word (G2 also fails). Candidate next steps, not
authorized: warm-start re-fit for corners, or routing smooth residuals to the
small ordinary head. Also recorded (section 7.31): the CAS language line
L1-L3 of 2026-10-14 (LM-T1 round trip 576/576, hand set 64/64, SDG English 233
of 439; LM-T1b nested 100/100 and meta-logic 120/120 under the newest compiler;
LM-T1c dotted fractals 40/40 under ruling N1; LM-T2 seams 96/96 and 48/48, 0
false seams, 0 invented facts; LM-T2/T2b taught coordinates NOT CALIBRATED,
stopped per "redesign once"; LM-T3 12/12 FORM gaps closed, 0 regressions, 7
wordings accepted by the owner). Translator ENGINEERED-NOT-VALIDATED (form
only); open English / meaning / HELM-level language claims NOT LICENSED; the
skin is not yet wired to the recipe brain; L4 (learned CAS-native parser, AWS
GPU) waits on the owner. Spec sheet sections 7.30 and 7.31 and two change-log
rows in this commit.

## 2026-10-15 PDT - HELM RB3c "T taught with yields" RAN on AWS (job c29): T_y (97 parameters) and T+_y (385 parameters), taught the same single-recipe yields the recipe brain receives, still near chance on Task B (4/4 and 5/4 of 16) against the recipe brain's frozen 16/16; BETTER_THAN_T_B_YIELDS true (margins 24 and 23 of 32); reading YIELDS_NOT_THE_CAUSE; 1.88 USD

Owner request (verbatim, ~2:10 AM Pacific): "T with yields". Owner line (verbatim,
~2:50 AM): "APPROVE RB3c: T taught with yields on Task B, arms
T_y/T+_y/T,T+(frozen c27)/RB-det(frozen c26)/LUT/MLP, marks as preregistered,
sealed package 165cb6fa, one attempt, cap $5.00." The only change from RB3
(c27): T and T+ also trained on the single-recipe yields RB receives, as an
extra training target on the label-free logit direction (mean of the four
answer scores = log yield, weight 1.0) on the single-recipe lesson worlds of
each draw (680 yield rows over 20 draws); no parameters added; test worlds
carry no yield; identical lesson information verified on 20,480 checks and
identical inputs on 4,720 checks, 0 problems. One m6i.8xlarge
i-007c383e71b9539e6, launched 2:30 AM Pacific, command 4,047.7 s (41/41
tests), host 72.5 min; kit as c27, no new limit changes. Medians of 20 draws,
B-chain / B-alt of 16: T_y 4 [3..6] / 4 [2..7] (sum 8); T+_y 5 [3..8] / 4
[2..7] (sum 9); frozen c27 T 4 / 3 (7) and T+ 5 / 4.5 (9.5); RB-det frozen c26
16 / 16 (32); LUT 4 / 4; MLP-B 4 / 4. Reading RB3C_READING.json (sha256
a106c7b1...): overall PASS; reading YIELDS_NOT_THE_CAUSE; BETTER_THAN_T_B_YIELDS
true (RB-det >= 4 above T_y AND T+_y: margins 24 and 23); T_COMPOSES_B_YIELDS
false (neither reached 12/16 on both panels). Change from labels only: T_y +1,
T+_y -0.5. UNDETERMINED 0; errors 0. Teaching refusals: T_y 1,260 of 10,240
ticks, T+_y 555 (c27: T 77, T+ 553), jobs counted complete. The transformer
learned the yields (final median absolute log error T_y 0.31-0.63, T+_y
0.11-0.32) and still did not compose. LICENSED only in the reading's claim
sentence: on synthetic recipe worlds only, the yield feedback was not the cause
of the gap; the programmed composition rule is the remaining difference. NOT
LICENSED: that no other way of giving T the yields would work; recipes beat
transformers in general or at other sizes/tasks/teaching rules; learned
composition by RB; statistical superiority; any non-synthetic claim. Charge
1.88 USD (hold 5.00 replaced); ledger -> 105.17 of 200.00; cleanup VERIFIED by
the controller and the independent check; backup
D:/tksCAS-archive/helm_rb3c_c29_20261015/ (269 files, three confirms, 0
mismatches). This closes the last asymmetry RB3 named: across RB1g2, RB2b,
RB2c, RB3 and RB3c the one difference left between the recipe brain and HELM's
transformer on Task B is the programmed composition rule. Spec sheet section
7.29 and change-log row in this commit.

## 2026-10-15 PDT - HELM RB3 "T on B" RAN on AWS (job c27): the GB3 transformer (T, 97 parameters) and a widened T+ (385 parameters, same programmed board-1 copy as RB) both near chance on Task B; recipe brain frozen 16/16 (32 parameters); BETTER_THAN_T_B true (margins 25 and 22.5 of 32); 1.89 USD

Owner line (verbatim): "both T and T+; APPROVE RB3: T on Task B, arms
T/T+/RB-det(frozen c26)/LUT/MLP, marks as preregistered, sealed package
26a6077f, one attempt, cap $5.00." Launch first blocked by the us-west-2
on-demand vCPU limit (32, 4 in use by nc-customer-app and nc-canary-app); the
owner's "raise the quota" was filed (request a8cb6434..., case 179204819400751)
and granted within 5 minutes (now 64); a 16-CPU fallback seal RB3b (d7ca0f78)
was built and shelved; the 5.00 hold moved back to c27. One m6i.8xlarge
i-0f360701d222bd233, launched 12:22 AM Pacific, command 4,071.4 s, host 72.8
min, 25/25 tests; kit-side limits raised (CPU check 2 -> 32, process limit 128
-> 4096, controller interval 10 -> 20 s), sealed package untouched. Fairness:
T receives byte-for-byte the same 8 numbers per board that RB's decoder reads
(4,720 identical-input checks, 0 problems); T+ also gets RB's programmed copy
of board 1; both taught with GB3's own step, 512 keyed presentations per draw;
stated remaining asymmetry: RB also taught single-recipe yields, T labels
only. Medians of 20 draws, B-chain / B-alt of 16: T 4 [2..5] / 3 [0..7] (sum
7); T+ 5 [3..8] / 4.5 [3..8] (sum 9.5); RB-det frozen c26 16 / 16 (32); LUT
and MLP-B 4 / 4. Reading RB3_READING.json (sha256 320a0d49...): overall PASS;
BETTER_THAN_T_B true (RB-det >= 4 above T AND T+: margins 25 and 22.5);
T_COMPOSES_B false (neither reached 12/16 on any draw). Teaching refusals: T 77
total, T+ 553 total (T+ draw 11 refused 455 of 512). LICENSED only in the
reading's claim_if_pass words (synthetic recipe worlds; Task B; same 20 draws
as c25/c26). NOT LICENSED: recipes beat transformers in general or at other
sizes/tasks/teaching rules; that the composition rule rather than the yield
feedback is the cause; learned composition by RB; statistical superiority; any
non-synthetic claim. Charge 1.89 USD (hold 5.00 consumed); ledger -> 103.29 of
200.00; cleanup VERIFIED by controller and independent check; backup
D:/tksCAS-archive/helm_rb3_c27_20261015/ (249 files, three confirms). With
RB1g2 (table tie), RB2b (T survived scaling) and RB2c (only recipes pass Task
B), this is the first run where the recipe brain beats HELM's actual
transformer on a task the transformer cannot pass. Next named control: teach
T the single-recipe yields too. Spec sheet section 7.28 and change-log row in
this commit.

## 2026-10-15 PDT - CAS Recipe Capacity Rules v0.1 named; RB-W capacity experiment RAN ($0): Limiting-Reagent Rule held 6 of 7; blend law only to ~12 vertices; smooth/noisy laws need an ordinary head; restart fallback (RB-C4) is the one stochastic mechanism that earned its keep

Owner words: "name it and RB-W" (2026-10-15 ~1:40 AM Pacific); vocabulary rule
"PLEASE JUST USE PARAMETERS". The rules: (1) the Limiting-Reagent Rule of
scaling - a recipe brain's capacity is a recipe (slots + routes + vertices +
terms + depth); more parameters help only when each has a real job; scale only
the kind a frozen test shows limiting; (2) the simplex blend law, error ~
1/vertices^2 (lsr_t7 1.997); (3) the guardrails (>= 8 new rows, hold-out incl.
shuffled labels, fewest-nodes-wins with BLEND costed by vertices, eta/epsilon
receipts, depth <= 5, node cap). RB-W (Documents/Codex/2026-10-15/rb_w/,
FROZEN before code, verdicts by program): held-out right of 100 - bigger Task
B 62.5 -> 100 with recipe slots 4 -> 8 (W1 held: 4 slots could hold only 4 of
8 recipes); smooth 2-input 61.7 -> 82.0 with blend vertices; scale_leak 12 ->
89.7 with eta/leakage terms; clean 87.5 unchanged by any kind; noise 0.2
unchanged by any recipe kind but 16.6 with a 4-parameter ordinary head; smooth
4-input 8.0 -> 10.9 at best (nothing binds it; prediction missed). Each kind
moved only its own family; the all-4x arm tied the best single kind (no
memorizing flag); ledger filled where the binding kind grew. W3 FAIL: blend
exponent 0.7053 over 4/8/16/32 vertices (error bottoms at 12 then rises); T7's
1.997 reproduces from the same code -> quadratic only up to a per-family vertex
limit. Boundary: a 223-parameter MLP beats every recipe configuration on smooth
families (81 vs 11; 82.4 vs 82.0) while the recipe brain wins recipe-shaped
laws (100 vs 25; 89.7 vs 31.3). RB-C4 (2026-10-14/rb_c4): positive control 8/8,
all hard gates pass; RESTART_FALLBACK_EARNED_KEEP and RANDOMNESS_EARNED_KEEP on
depth-3/4 compositions (342/344/264 and 266/212/208 of 512 vs 62 and 0 for the
fixed start) - a fit-start win, not a proposal win; grammar
CREATIVITY_DID_NOT_EARN_KEEP; coin twin below; 0 inventions. Across the night,
randomness as a proposer earned keep in 0 of 8 tests. Also recorded: owner
ruling N1 nesting direction "outer last, both . and :"; owner amendment that
recipe-brain self-growth (RB-G) proceeds before roadmap ability 3; owner
direction that depth-3/4 chains are the standing exam for CJT Bias cascades,
RPM chains and RPA depth. Failed approaches logged: RB-C2 and RB-C3 stopped at
their frozen positive control (small-input start rule; order-dependent
consistency check) before the order-free largest-consistent-set fix. Spec sheet
section 7.27 and change-log row in this commit.

## 2026-10-14 PDT - HELM recipe brain RB2c (Task B clean rerun) RAN on AWS (job c26): PASS; RECIPE_COMPOSITION_EARNED true; 0.04 USD

Owner line (verbatim): "option 1 AND APPROVE RB2c: Task B only, reader fix,
arms RB-det/RB-sto/RB-roundrobin/RB-random/LUT/MLP/DIV_TOTAL, marks as
preregistered, sealed package 18d0a2d3, one attempt, cap $0.50." Package
HELM_RECIPE_BRAIN_20261014_RB2C_SOURCE_RB2C.zip sha256 18d0a2d3...1668. Only
change from RB2b: label-only arms answer NOT_APPLICABLE on the sum-of-yields
panel (neither answer nor error; a real crash still voids the task); Task A, T
and RB-H1 not run; new instrument row C25_EQUALITY (c25's 20 Task-B worlds
reproduced exactly, 20/20). One m6i.xlarge us-west-2 i-0644dba9702b30c9b, host
600.6 s, command 288.4 s, 96/96 tests. Task B medians over 20 draws, B-chain /
B-alt: all four RB arms 16/16 [16..16]; LUT 4/4 at its proven floor; DIV_TOTAL
4/6; MLP-B 4/4; smallest-input 4/0 with 160 NOT_APPLICABLE reads and 0 errors
(c25 had 24). Receipts: every admitted write passed on all 20 draws (RB-det
480/480). UNDETERMINED 0 on scored panels. Reading RB2C_READING.json (sha256
25f69e58...): task_b PASS, overall PASS, RECIPE_COMPOSITION_EARNED true by the
preregistered rule (Task B PASS and every no-recipe baseline median < 12).
LICENSED only in the reading's own claim_if_pass words: recipe composition on
synthetic recipe worlds; 4 taught recipes; requirements learned from
single-recipe orders, combined by a programmed MIN / chain / MAX rule; the
composition rule is programmed, the coefficients are learned. NOT LICENSED:
general learned composition, transfer, cooperation, language, better than T
(not run), statistical superiority, any non-synthetic claim. This is the first
exam on the recipe line where only the recipe mechanism passes (RB1g2: lookup
table tied; RB2b Task A: the transformer and a divide-by-total table also
passed). Charge 0.04 USD (list 0.034853); hold 0.50 consumed; ledger 101.86 ->
101.40 of 200.00; cleanup VERIFIED by controller and independent check; slot
released; backup D:/tksCAS-archive/helm_rb2c_c26_20261014/ (199 files, three
confirms). Same-day creativity line ($0): RB-C1 FAILURE (coin twin beat the
seeded draw; shuffled labels +1; ledger non-monotone; 0 inventions); RB-C2 and
RB-C3 stopped at the frozen positive control (multi-route fitter); RB-C4
(order-free consistency + 1e-12 tolerance) in progress. Spec sheet section 7.26
and change-log row in this commit.

## 2026-10-14 PDT - HELM recipe brain RB2b (harder exams A+B) RAN on AWS (job c25): Task A PASS but the transformer passed too (BETTER_THAN_T_A false); Task B INSTRUMENT_ERROR (recipes 16/16, every no-recipe baseline <= 6, reader rule tripped); overall NOT_PASS; 0.26 USD

Owner rulings (verbatim): "both" (harder tasks), "RB2 defaults; yes" (six
defaults; DIV_TOTAL baseline), "RB2b, LM defaults, RB-C defaults, delete them"
(Task-B generator fix), and the sign line "APPROVE RB2b: harder tasks A+B, arms
T(A only, re-taught)/RB-det/RB-sto/RB-roundrobin/RB-random/LUT/MLP/DIV_TOTAL,
marks as preregistered, sealed package dcae7e75, one attempt, cap $2.00."
Package HELM_RECIPE_BRAIN_20261014_RB2B_SOURCE_RB2B.zip sha256 dcae7e75...687d
(100 learned values: 68 + 32; RPM Gate; eta/epsilon receipts; 20 seeded world
draws, marks on the median). One m6i.xlarge us-west-2 i-0b6f208ca7b33389f,
launched 9:25 PM Pacific, command 4,108.6 s, host 72.8 min, 95/96 tests (the
one failure writes the frozen reading). Task A (boards scaled 8-16x past every
taught value): all four RB arms 16/15.5, T re-taught 16/15 (rebuilt identical
to c21), LUT 4/4 at its proven floor, DIV_TOTAL 16/16 (the known hole), MLP
7/7 -> task_a PASS; BETTER_THAN_T_A false (T survived scaling; bar not met).
Task B (4 base recipes taught, held-out chains and best-of-two routes; worlds
kept only where the bottleneck is not the smallest stock): all RB arms 16/16
with receipts 480/480 on 20 of 20 draws; LUT 4/4; DIV_TOTAL 4/6; MLP 4/4;
smallest-input 4/0 (under the <= 8 limit) -> but task_b INSTRUMENT_ERROR,
reason MISSING_OR_ERROR_smallest_input: the reader flags any `errors` on that
heuristic's record and it logged 24, all on the sum-of-yields panel where it can
only emit labels; scored panels had 0 errors. RECIPE_COMPOSITION_EARNED false
(requires Task B PASS); overall NOT_PASS. Claim status: Task A LICENSED only as
the reading's claim_if_pass text (scale-freedom is programmed; DIV_TOTAL also
passes; carry programmed); Task B NOT LICENSED until a clean run; the 16/16 vs
<= 6 separation is recorded as an indication only. Negatives kept: the
transformer passes scaled worlds; divide-by-total passes Task A; MLP fails both.
Charge 0.26 USD (list 0.253551); hold 2.00 consumed; ledger 103.10 -> 101.36 of
200.00; cleanup VERIFIED by controller and independent check; 401 files
hash-verified; backup D:/tksCAS-archive/helm_rb2b_c25_20261014/ (456 files,
three confirms). Same-day laptop results ($0, SYNTHETIC_ONLY) also recorded in
spec sheet section 7.25: language line lm_t1 (CCE <-> CAS round trip 576/576,
blind hand set 64/64, SDG English 233/439 vs 118, nested 50/50, meta-logic
120/120 on the newest compiler 464fd4ad; owner N1 ruling: outer last for both
. and :), lm_t2 (trajectory on the simplex: seams 96/96 and 48/48, 0 false,
drift 24/24, 0 invented facts; taught coordinates failed calibration; one
redesign lm_t2b failed 47/48 -> line stopped), lm_t3 (12/12 fillable grammar
gaps closed, 0 regressions, 6 meaningless gaps refused with a question; 7
wordings accepted by the owner), lsr_t6/t7 (blend harm fixed; blend error
exponent 1.997 vs staircase 0.95). Failed approaches logged: RB2 (first seal)
had a Task B a one-line heuristic could pass (11-14 of 16) and was re-sealed
before launch; the reader's instrument rule counts non-applicable-panel errors
as instrument errors. Spec sheet section 7.25 and change-log row in this commit.

## 2026-10-14 PDT - HELM recipe brain RB1g2 (recipe INSTEAD of the transformer) RAN on AWS (job c23): PASS as frozen; BETTER_THAN_T true by one world; RECIPE_MATH_EARNED false (lookup table tied); 0.03 USD

Owner's goal, restated 2026-10-14: replace the transformer that is HELM's brain
with CAS recipes and do better than it. Owner rulings, verbatim: "Yes to
RB1...$200 aws" (seven preregistration defaults; AWS combined ceiling 200 USD;
record helm_operator_preparation/budget_ceiling_review_20261014_r1/
OWNER_CEILING_RULING_20261014.md), "add the gate; ... not wrong/unable to
determine", "Yes on parallel prod", "Fix A", and the sign line "APPROVE RB1g2:
recipe instead of transformer, arms T/RB-det/RB-sto/RB-roundrobin/RB-random/LUT,
marks as GB3 + gate, sealed package 25cd12c0, one attempt, cap $0.50."
Package HELM_RECIPE_BRAIN_20261014_RB1G2_SOURCE_RB1G2.zip sha256 25cd12c0...b35bf
(68 learned values vs the transformer's 97; no attention; four CAS recipes
answer by theoretical yield; witnessed-ratio writer under GB3's memory check;
RPM Gate returns UNDETERMINED when a prerequisite is absent; refused worlds
marked LACUNA and revisited on a cadence). One m6i.xlarge us-west-2
i-0bcfd3e62ecf052c4, launched 7:02 PM Pacific, host 364.4 s, command 42.0 s,
62 tests OK, GB3 c21's sealed worlds rebuilt with 0 mismatches. Program reading
RB1G2_READING.json: status PASS; rows 0/1/2 true; RB-det panel 1 16/0/0 and new
worlds 16/0/0 (T frozen: 15 and 15; mark 12) so BETTER_THAN_T true by a
one-world count; RECIPE_MATH_EARNED false because the lookup-table arm (same
gate, same policy, no recipe math) also scored 16/16 and 16/16 (sums 32-32);
POLICY_EARNED true (four-key mark after 56 presentations vs 61 round-robin, 67
random); every admitted write passed its eta/epsilon receipt (RB-det 472/472);
0 UNDETERMINED on scored panels. Licensed: content-carrying on 16 synthetic
two-board worlds only; recipe instead of transformer on THIS task only. Not
licensed: recipe math as the source, general replacement, transfer, learned
carry (programmed), statistical superiority. Owner default D-2 applies: the
line moves to a harder task a lookup table cannot pass. Charge 0.03 USD (list
0.021145); 0.50 hold consumed; ledger 101.57 -> 101.10 of 200.00; cleanup
VERIFIED twice. Same-day laptop screens ($0, SYNTHETIC_ONLY): recipe learner
100% on 2- and 3-input SDG recipes vs attention stand-in 2-6%
(fair_data_experiment_v3_bridge2); sdg_bridge_v2 raised SDG coverage 51 -> 576
of 576 and caught seed_recipe_00459; Lacunarity Machine v1 read of c21 (both
readwrite misses on key 2; twin a true lacuna); LSR loop T1-T5: shape recovery
exact (T4), simplex cells = limiting-reagent regions exactly (T5), Thompson
variety earned nothing, smooth-curve blend 0 -> 227/512 short of the 19/20 mark.
Failed approaches logged: LSR T1 proposer never fired (fit never
under-predicts); T2 second route fitted on rows with cut inputs; T5 counted a
blend as one node and let it bully the correct SUM shape (259 wrong on additive
data). Spec sheet section 7.24 and change-log row added in this commit.
Artifacts off-repo under C:/Users/wakil/Documents/Codex/ (gate_b/rb1g2/,
2026-10-14/lsr_t*/, CAS-Recipe-Network-Comparison-20261011/); backup
D:/tksCAS-archive/helm_rb1g2_c23_20261014/.

## 2026-10-07 PDT - Noetics label agreement, attempt 2 (guide v2.1, plan v2.1): run valid; ^1 LABELABLE, ^2-^9 NOT_LABELABLE; 426 passages labeled by both teams

Owner signature 2026-10-06 8:00 PM Pacific ("SIGNED: label-agreement v2.1,
guide 2b6617c15102, plan 657413f77f18, as proposed."); owner record written by
the owner's own paste. Practice tool check on 30 passages: both teams 30/30,
PRACTICE CHECK: PASS. 440 passages written by gemini-2.5-flash, 13 dropped by
the forbidden-word check, 427 sealed (SEAL.json sha256 f7fff437...). Team A:
eleven Claude Sonnet sub-agents, 427/427 labeled, all on the first try. Team B:
deepseek-chat (replies named deepseek-flash), 426/427 labeled; W266 failed
three tries and is left out. Run valid; 426 passages analysed. Entry agreement
E against the signed 0.80 bar: ^1 0.848 (LABELABLE_UNDER_THIS_METHOD); ^2
0.694, ^3 0.569, ^4 0.389, ^5 0.484, ^6 0.458, ^7 0.396, ^8 0.388, ^9 0.321
(NOT_LABELABLE_UNDER_THIS_METHOD). Kappa on presence 0.724 to 0.920, all above
0.60. Same pattern as attempt 1: agreement on which passages hold a Noetic, not
on the entries. Team A transcripts show 0 checker check-mode runs and 0 checker
imports; labelers were started with the Agent tool and one fixed wrapper, not a
workflow script (recorded deviation). Spend: AWS 0; DeepSeek 6,356,893 in /
189,006 out tokens, at most about 2.13 USD of the 4.00 USD cap; Gemini free
tier (24 requests; 7 refused 503, 1 refused 429). Option B can now check these
426 passages under a new, reviewed plan; what follows is the owner's decision.
Failed approach logged: Claude Code auto mode on the laptop refused both the
owner-record write and the Gemini writer run from the operator, so the owner ran
them by paste; a pasted block that ends with "exit" closes the owner's window,
so later blocks were wrapped in "& { ... }" and stop with "return".
Report: cas_only_reasoner/CASALESCENCE_NOETICS_v0_1/label_v21/verdict/VERDICT_REPORT.md
(VERDICT_REPORT.json sha256 f54fe3c08f672c2975d9541cebef05942aa72331326ba17155444fc45d396dff).
Backup D:/tksCAS-archive/casalescence_label_agreement_v21_20261007 (110 files,
three matching checks). Spec sheet section 7.23 and change-log row added in this
commit.
## 2026-10-06 PDT - Option B usefulness test: two free practice builds STOP_DO_NOT_LAUNCH; no GPU job; paused by owner 2026-10-07, pending Noetics label trial v2.1 (guide 2b6617c15102, plan 657413f77f18)

Owner order 2026-10-06 4:12 PM Pacific ("SIGNED: option B status table as
proposed ... run parallel our smartest team of agents"). Development test d1
on made-up data RAN on one m6i.xlarge: PRECHECK_COMPLETE_SELFTEST_PASS,
cleanup VERIFIED, charge 0.09 USD (ledger 97.59 -> 97.68 of 250). Plan 1.0
chain sealed to step 3A: at 12 practice settings 48 role-step candidates, 30
pass the key check, 16 survive the no-passage check, 16 selected against a
floor of 36 (plain-fact 20 of 20). Program decision STOP_DO_NOT_LAUNCH. Plan
1.1 (brief rules, three program-enforced form-check drops, three writer passes,
lowest-pass-first selection; floors and both solver rules unchanged) was
reviewed by two separate sub-agents and rebuilt in the sibling folder
CASALESCENCE_NOETICS_v0_1__PLAN_v1_1, sealed to step 3A: 57 candidates over
36 pairs, 40 pass the key check, 20 survive, 15 selected (plain-fact 35).
Program decision STOP_DO_NOT_LAUNCH again. Reading: the ceiling is structural
(about 36 open pairs, about 50 percent guessability). Spend: AWS 0.09 USD,
DeepSeek 872 calls (127,467 in / 5,236 out tokens), Gemini free tier, GPU 0.
Seal step 7 never written, so no status word applies. Nothing deleted. Record:
cas_only_reasoner/CASALESCENCE_NOETICS_v0_1/optionb/OPTION_B_BUILD_STOPS_20261007.json.
Spec sheet section 7.22 and change-log row added in this commit. Owner decision
2026-10-06 8:00 PM Pacific: Option B PAUSED, pending Noetics label trial v2.1
(guide 2b6617c15102, plan 657413f77f18); resumes only when that trial yields
more labeled passages. Recorded in the stop record's owner_decision block.

## 2026-09-04 - CASformer v0.2 source freeze

- Accepted the GLM execution audit as `CAS_CJT_TRANSFORMER_V0_2_CODE_AUDIT_PARTIAL`.
- Froze the unchanged 50-file v0.2 controlled source set, its source manifest,
  tests, schemas, demo, and wheel-build configuration under
  `cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_CJT_TRANSFORMER_v0_2/`.
- Added the hash-locked CPython 3.14 Windows CPU dependency set and committed
  the frozen 26-file `CASFORMER_v0_1` sibling source required by v0.2.
- Clean wheel installation, pristine-worktree reproduction, blocker attacks,
  and evidence binding remain for a separate evidence commit tied to the
  source-freeze SHA.
- No language capability, general reasoning capability, CAS-specific
  advantage, CNCM brain completion, AGI, or production readiness is claimed.

## 2026-09-02 - CPB-0 DO_NOT_BUILD at $0; the question itself was malformed

Second design retired at zero cost in a row. This one is not "designed badly" - the corpus lacks
the structure the question presupposes.

**The impossibility, measured over three probe worlds.** A payload rule is useful only if it
catches all 36 forgeries and kills 0 honest corroborations. Nothing does, not even the oracle:
`f(topic)` catches 10/36 because the exact-copy forgery inherits the host's payload; per-memory
random catches 36 and kills 60 of 60; hand-written ground truth catches 36 and still kills 35.
Three cases, exhaustive - copied field, fresh field, or the label itself. There is no fourth.

**The sixth shortcut.** Four of six registered statuses were selectable by one line in the corpus
generator, and no gate constrained it - `GATE_LEGIT_CORROBORATION_EXISTS` measures the unrepaired
verifier, which never reads payload, so it passes in every regime.

**Both cheap competitors are dead.** `coherence()` never reads the semantic vector, so an
exact-duplicate check dies at attacker cost zero. `ROOT_NOVELTY` is an insertion-order oracle.

**What actually matters:** a trajectory-only duplicate check kills the attack *and* takes
legitimate corroboration from 444 to 0 - because legitimate corroboration in this corpus IS an
exact trajectory copy. The attack and honest corroboration are the same object in every field the
verifier reads. Corroboration here is content duplication, and treating content duplication as
independent evidence is the defect.

**What I got wrong:** I proposed the payload framing and predicted a one-line fix. Both wrong in
the same direction - I assumed the missing thing was a check when the missing thing is a
representation.

Not redesigned. A cheap mitigation exists and is recorded as a mitigation, never a repair.

## 2026-09-02 - CMB-RP1 DO_NOT_BUILD at $0; the diagnostic is withdrawn

The design was authorized, preregistered, attacked by six lanes the same day, and retired before
anything was built. Every consequential claim re-verified by me before acceptance.

**The curve cannot exist.** `traj_sim` over lengths 3-6 admits only thirteen values; the band
`[0.80, 0.99)` is reachable by exactly two, both at edit distance 1. The verifier's exclusion
rate is a step function of an integer, not a curve. The design's own falsifier fires before a
world runs.

**The diagnostic is misattributed.** On the registered near-miss attack `cond_consistent` fires
0/30, and turning the contradiction band off changes nothing - not one forgery, not one true
memory. The `119 -> 0` headline is the relative margin's work.

**RGM-0.2: numbers stand, explanation withdrawn.** My self-correction came from an adaptive
forgery I built at `0.9375`, which sits inside `DELTA`. True of that attack, not of the one that
produced the headline.

**CMB-RP0: `DEGREE_FILTER` qualified.** Link ties break by ascending `memory_id`. Changing the
forgery prefix from `poison_` to `aaaF` erases the degree signal and inverts its sign. The
verdict is unchanged; one competitor's claim is narrowed.

**Free finding:** an exact copy with a fresh provenance root is authorized 20/20. Corroboration
is judged on the fields the query matches, not on the payload that would be acted upon.

Not redesigned. Total cost `$0`.

## 2026-09-02 - Interlock audited PASS; the last human promise is now a grep

GLM's sixth audit this session, `$0` total across all six. Both named risk points judged sound:
the derived-manifest path takes the pipeline config, not a manifest object, so there is no
manifest-shaped injection parameter anywhere on it; and the residual limit is correctly bounded.

**Its one recommendation is built.** `verify_receipt_clearance.py` is a CI step that fails any
run receipt lacking a bound clearance - the likeliest real failure being a run that simply never
called the gate - and any clearance that does not re-verify against the trigger receipt embedded
in it. `validate_receipt_check.py` proves it on ten receipts: one genuine, nine damaged one
specific way each, all caught.

Built now rather than "the day the first real training launcher exists", so it is audited before
it is needed rather than invented under pressure.

**Still not closed, and said so:** a launcher controlling its own source can lie about everything
consistently. That is impossible in code, and claiming otherwise would be the dressed-up green
row this lane already caught once.

CMB-RP1: technically unblocked, not authorized.

## 2026-09-02 - Trigger PASSED; the interlock is built and the trainer provably stops

Owner ruled the trigger itself PASS at `bc9e89df`, with the alarm bench-tested but not yet wired
to the furnace. It is wired now.

**`T1`'s metric is frozen as a calibration package.** Any future change to it is a
**recalibration event** requiring new population measurements; thresholds may never be carried
across metrics unchanged. `0.80`/`0.99`, the `0/3794` collateral measurement and the `54/108`
forgery-pair measurement were all calibrated with edit distance - swapping the metric leaves the
same digits measuring a different quantity.

**`replay_training_gate.py`** implements the five launcher requirements as a module. The launcher
never writes a manifest: it hands over the config its pipeline emitted and the manifest is
derived from it, so no hand-editable boolean sits anywhere on the path.

**`validate_gate.py` proves it**, and the assertion is not "an exception was raised" but **"the
trainer function never executed"**. All five blocking states: `trainer ran: False`. Clear states:
`trainer ran: True` with the clearance bound into the receipt.

**The limit, stated rather than dressed up:** this defends against mistake, not against a
launcher that deliberately lies about itself. A launcher controlling its own source can skip the
call. An earlier draft of the gate test recorded "a hand-built clearance dict is accepted" as a
*passing* row - a limitation dressed as a success - and that was corrected to a refusal plus an
explicit disclosure.

CMB-RP1 remains blocked.

## 2026-09-02 - External spec-only conformance suite: one real bug, three spec defects

Closes GLM audit finding 1 - the existing suite was the checker validating itself. Eight parties
read only the specification, never the implementation or the existing suite, and predicted state
and exit for 75 fixtures before anything ran. **64 matched, 11 diverged.**

**The real bug:** an unrecognised `--expected-scope` made argparse exit `2` - a code the frozen
ladder does not define, in the same commit whose contract says a launcher must not meet an
undocumented code. Fixed; every invocation error is now `REFUSED`/`10`.

**The finding an author-written suite cannot produce:** three divergences shared one root cause -
`T1`'s similarity metric was never defined. All three authors assumed cosine similarity; the code
uses edit distance. My own fixtures would have used my own metric and never noticed. Now
normative.

**The acknowledgement format was undocumented** - and it is the only path from a blocking state
to exit 0. Now normative, with proof that an ack cannot clear `NECESSARY` or `URGENT`.

**The ladder had no resolution rule.** `T5` true with `T1` fired and `T2` unknown satisfied two
rows at once. Now ordered: `REFUSED` is a precondition gate, not a ladder row; a fired defence
beats an unknown one; `T5` false is `DORMANT` regardless.

**Empty evidence is UNKNOWN, not clear.** Zero measurements is not a measurement of zero.

Three divergences were fixture errors and are recorded as such, including one the author
disclosed unprompted before submitting.

Both suites now run. A future change must keep both green.

## 2026-09-02 - Trigger v0.3: the wiring gap closed, manifests bound to scope and job

The owner found that the `DORMANT` result could not clear CMB-RP1, and was right. A
`PRODUCTION_DEPLOYMENT` manifest reading *no production system feeds training* is true, and
useless as clearance for a development replay job that really does put memories into training.

> "It can truthfully report that the empty production building is safe while the experimental
> workshop next door is actively using the furnace."

The recurring failure class this lane keeps hitting: **the correct field exists, but the
authority path does not read it.**

**Manifests are now scope- and job-bound.** Flag names differ by scope, so one file cannot be
repurposed across the boundary by editing a single field. The launcher declares
`--expected-scope` and `--job-id`, and the checker REFUSES a manifest that does not govern the
job. It also refuses a `derivation: derived_from_pipeline_config` claim with no pipeline config
to verify it, and a declared flag that disagrees with the pipeline. **The pipeline is the fact;
the manifest is a claim about it.**

**`WATCH` is no longer a silent green** - new exit `5`, passing only with an owner
acknowledgement bound to both the job id and the manifest digest.

```
0   DORMANT | CLEAR | WATCH_ACKNOWLEDGED
5   WATCH               needs an owner ack bound to this job
10  WATCH_UNRESOLVED | REFUSED
20  NECESSARY
30  URGENT
```

A machine-readable trigger receipt (`--receipt-out`) can now be bound into the run receipt.

Self-validation 16 -> 25 scenarios, all passing, including the decisive pair: the same
production manifest is REFUSED when a dev job declares its scope, and would have returned
DORMANT without it.

**Stated plainly in the spec:** until a launcher actually calls this, it is a correctly
functioning checker standing beside the machinery, not an interlock inside it.

CMB-RP0 is not retrofitted. **CMB-RP1 may not launch** without its own `DEVELOPMENT_REPLAY`
manifest, derived from its actual pipeline configuration and checked.

## 2026-09-02 - Trigger repaired under owner ruling: four fixes, and a correction to my own wording

**Concept approved, implementation needed four authority/logic fixes.** All applied, and the
self-test now covers 16 scenarios, all passing.

**My wording withdrawn.** I wrote that the admission headline "is a count, not a mean, so it is
not power-limited at all." Too absolute. The counts are exact (`119 -> 0`), but any claim about
future unseen attacks is sample-limited. Rule-of-three 95% upper bounds: `0/119` -> ~2.52%,
`0/3794` -> ~0.08%, `0/358` -> ~0.84%. Corrected to: **the registered attack set was blocked
completely; generalization beyond it remains sample-limited.** "Not a mean" is not "not
sample-limited", and I had run the two together.

**Bench scope bound to the rename.** The status now emits
`status_scope = RGM-0.2_SYNTHETIC_BENCHMARK_FAMILIES` and
`universal_geometry_superiority = false`. "Only" means *among the five families tested*.

**Fix A - direction-free separability.** This was a **documentation** defect, not a code one:
the code always computed `max(AUC, 1-AUC)`, but the spec sentence said "AUC < 0.65", which would
read an AUC of `0.10` - excellent *reverse*-direction separation - as an alarm.

**Fix B - T3 had no authority**, appearing in the condition list and in no decision path. Now on
an explicit ladder where scale escalates `NECESSARY` to `URGENT`. The self-test then exposed a
*second* T3 bug: it read the memory count from the corpus and discarded the manifest, so an
80-memory sample overrode a declared 50,000-memory deployment. Corpus is a sample, manifest
declares the deployment, larger wins.

**Fix C - unknown must stop the machinery.** Exit codes `0` / `10` / `20` / `30`; every nonzero
code blocks a memory-to-training job. If `T5` itself is unknown the state is `WATCH_UNRESOLVED`,
not `DORMANT`.

**Fix D - flag authority.** Production-scoped flags inside an exact-schema manifest with owner
attribution and a config digest. A missing or malformed manifest yields `UNKNOWN`, never
`False`.

**Honesty fix the owner caught:** CMB-RP0 literally put retrieved memories into training, so a
flat `memory_feeds_training: false` was misleading. Recorded separately as
`development_memory_feeds_training = true`. The dormancy now reads honestly: the experimental
bench used memory in training; no deployed system does.

No periodic daemon - event-driven and mandatory at seven named events. CMB-RP0 is not
retrofitted. **CMB-RP1 may not launch unless the trigger is clear or the defence is built.**

## 2026-09-02 - Owner rulings: 12 worlds accepted, geometry status renamed, structural-forgery trigger armed

**12 worlds accepted with the caveat.** The caveat is now a permanent rider on RGM-0.2: the two
winning families are 12/12 and unambiguous; the three losing families are small and
noise-limited and 12 worlds cannot establish their magnitude; and the admission headline
(`119 -> 0`) is a **count, not a mean**, so it is not power-limited. The caveat binds the
geometry comparison, not the admission result - and the admission result is the one that carries
the lane.

**Rename ratified.**

```
GENERIC_GEOMETRY_ADVANTAGE_SUPPORTED     -> CAS_GEOMETRY_HELPS_COMPOSITION_AND_CORROBORATION_ONLY
GENERIC_GEOMETRY_ADVANTAGE_NOT_SUPPORTED -> CAS_GEOMETRY_NO_ADVANTAGE_OVER_GENERIC_CONTROL
```

The code emits the new name and also emits the old one as `generic_geometry_status_legacy_name`.
`RGM02_RECEIPT.json` is **deliberately not rewritten** - GLM reproduced it byte-identically and
that hash is the determinism proof. Editing it to look tidier would destroy the best evidence
the result has.

**Structural-forgery defence: deferred build registered, trigger armed.**

The measured gap: the verifier detects semantic contradiction, a degree check detects structural
anomaly, and **neither covers a forgery that is both semantically consistent and structurally
normal.** Not built and not authorized - deferred under the standing `No automatic second
repair`, because in this lane a repair manufactured the next problem four times and building
straight off the measurement would be the fifth.

Six conditions, three computed and three declared. Firing rule: `NECESSARY = T5 AND (T1 OR T2)`
- memory feeds training, and either the semantic band has collided or the structural signal has
vanished. **`UNKNOWN` is not `NO`**: an unevaluated condition while memory feeds training
escalates to `WATCH_UNRESOLVED` rather than passing silently.

Self-validated across 7 constructed scenarios, all passing - and the validation caught a fault
in my own test fixture, not the checker. Current state `DORMANT`.

It is a checkpoint, not a daemon. It fires because the spec sheet is mandated read-first, and
the checker exits non-zero on `NECESSARY`/`URGENT` so it can gate a pipeline.

## 2026-09-02 - CMB-RP0 audited PASS by GLM; lane CLOSED on an honest negative

Independent audit, $0. GLM verified live: spend inside the frozen cap, `PYTHONHASHSEED=0`
pinned, both code mirrors byte-identical (it re-checked the hashes itself). Three findings,
none status-changing; all three dispositioned.

**The diagnostic worth keeping** - the auditor's third finding, now recorded in both benches
so neither can be read without the other:

The same verifier was measured against two different attacks and gave opposite answers.

| | RGM-0.2 (admission) | CMB-RP0 (replay selection) |
|---|---|---|
| attack | ONE adaptive forgery at `0.9375` | 132 cheap lev-1 forgeries |
| defeated by | **consistency** | **graph degree** |
| verifier | `119 -> 0`, `358` true kept | ingests `5.67`; a degree count ingests `4.41` |
| verdict | **earns itself** | **adds nothing** |

**The two-tier verifier detects semantic contradiction, not structural anomaly.** Where an
attacker must make a forgery *agree* with what it impersonates, it wins by mechanism rather than
threshold. Where forgeries are cheap they stop being ambiguous and start being conspicuous, and
nothing in the verifier looks at that.

These are complementary defences; neither substitutes for the other. Nothing here licenses
building the combination - that is what the two measurements jointly imply, and it would need
its own preregistration and owner authorization.

**The structural weakness was findable only because the mechanism-free competitor was registered
before the run.** Without `DEGREE_FILTER`, CMB-RP0 would have reported the verifier beating
`RANDOM` and `NO_REPLAY` and looked like a modest success.

Also fixed: `make_audit_package.py` was still emitting the pre-launch package after the run
completed. It now detects a receipt and emits the close-out record.

```
CMB-RP0 lane      CLOSED
total spend       $0.2039
claims promoted   NONE
negatives deleted NONE
successor round   NOT started -- owner's standing "No automatic second repair"
```

## 2026-09-02 - CMB-RP0 RAN: the two-tier gate earns nothing as a replay selector ($0.2039)

9 registered worlds on an AWS T4. Owner-authorized development run. Hash `f2fbfd0c97df96f7`.

```
SAFETY      TWO_TIER_GATE_EARNS_NOTHING
CAPABILITY  CMB_REPLAY_BEATS_NO_REPLAY_ONLY
PROMOTION   NOT_PROMOTABLE -- 6 of the owner's 8 conditions fail
```

**The authorization tier is dominated by its own retrieval tier.** `CMB_RETRIEVED` is better on
*both* axes - forgets less (`0.1388` vs `0.1518`) and admits fewer forgeries (`5.33` vs `5.67`).
The thing that beats the mechanism is the tier directly beneath it.

**A filter that counts graph edges is safer than the verifier.** `DEGREE_FILTER` - no query, no
semantics, no CAS - ingested `4.41` forgeries against `5.67`. This settles the A2.8 limit
registered *before* the run, and settles it against the mechanism.

**The registered falsifier fired.** Required gap `> 1.0`; measured `-0.33`, positive in 3 of 9
worlds. Per-world: `-1, 0, -3, 0, -1, +3, +1, +1, -3`.

**Three decisive losses**, each in 0 of 9 worlds at `p = 0.0038` - the floor of a sign-flip test
at n=9: to `SEMANTIC_DIVERSE`, `CLASS_BALANCED`, and `CLASS_BALANCED_POOL`.

**Nine worlds answered the power objection both ways**: enough for the effects that exist
(losses at the permutation floor), not enough for the ties with `RANDOM` and `DEGREE_FILTER` -
which per A3.5 are absence of power, never equivalence.

**A control produced its own finding.** `CLASS_BALANCED_POOL`, added hours before launch, is
near-best at preserving old tasks (`0.0429`) and by far the worst under poisoning (`16.00`).
Label-balanced replay is highly vulnerable to label-forgery.

Does not disturb RGM-0.2, which GLM reproduced byte-identically. That result is about admission;
this one is about replay selection. The verifier is good at what it was built for and adds
nothing here.

## 2026-09-02 — CMB-RP0 built (owner items 5 and 6): six construction faults, one disclosed limit, $0

Selective replay against catastrophic forgetting. Built and dev-verified; **not launched**.

Why it matters: a wrong memory *shown* to a user can be dismissed. A forgery mixed into a
*training batch* is written into the weights. Replay is the case the two-tier verifier exists for.

Six faults, every one found by measuring the bench rather than reasoning about it:

- **A1.1** the task was broken two ways — topic is 100% recoverable from the semantic vector
  (`480/480`) and the trajectory carries no topic information (`17/480`, chance `0.0312`).
  Scope narrowed in writing: this tests the CMB as a **selector**, not CAS geometry as a feature.
- **A1.3** my own mechanism-free baseline was a straw man (`0.6291` forgetting vs `RANDOM`'s
  `0.0964`, covering 4 of 22 classes). Replaced; the straw man is kept as an illustration only.
- **A2.1** forgeries had no context vector, so the verifier would have excluded them by a
  missing field rather than by its mechanism.
- **A2.2** the replay pool *was* the training stream, which excludes poison — no arm could ever
  replay a forgery, so the safety test measured nothing.
- **A2.4** degree gave the forgeries away twice, in opposite directions (`12.55` vs `7.42`, then
  `4.00` vs `6.79`).
- **A2.6** `CMB_AUTHORIZED` returned nothing on all 64 slots. Not the disclosed fail-closed
  behaviour: `0` failures on every condition, best coherence `1.0000`. **The verifier was
  correctly returning the query's own source and my harness threw it away.** Third time this
  lane I have diagnosed a mechanism failure that was mine.

One limit disclosed **before** any run (A2.8): the residual degree gap cannot be removed without
faking the graph, so it gets a competitor instead — a new `DEGREE_FILTER` arm using graph degree
and nothing else, added to the safety law. Stated consequence: this bench cannot cleanly separate
*the verifier works* from *my forgeries happen to be low-degree*.

Nothing is licensed and no result is claimed. Not launched, `$0` spent.

## 2026-09-02 - RGM-0.2: ADMISSION_SAFETY_REPAIRED on 12 new worlds ($0, CPU)

Owner reversed my role: I build RGM-0.2, another model audits. Conflict of interest declared -
I audited RGM-0/0.1 and built on my own findings.

Items 1-2. The lev-1 near-miss attack RGM-0.1 could not stop (119 forgeries admitted over 120
queries) now reaches ZERO authorised memories, while 358 true ones are still authorised. A
two-tier split separates RETRIEVED (may be shown) from AUTHORIZED (may influence reasoning or
learning); forgeries still surface as candidates but cannot be acted on.

Item 3. With the control on the identical verifier the CAS geometry advantage survives
drop-one (+0.0672) - but the generic control BEATS CAS on three of five families. The
advantage is concentrated in fragment composition (+0.4108) and independent corroboration
(+0.3190), and survives only because there are two winners rather than one.

Item 4. The mechanism-free gate passes: no query-independent shortcut, answer set not
recoverable from the graph. But plain semantic retrieval already reaches 0.83-0.94 on three
families; the machinery earns its cost at pattern completion (0.0005 -> 0.4167) and
independent corroboration (0.3117 -> 0.9818), and little else.

Three self-corrections on one verifier, each found by measurement after my reasoning produced
a plausible wrong answer. The load-bearing idea: a forgery's signature is not that it is
different, but that it is almost the same.

Disclosed: it fails closed - under adaptive attack nothing is authorised, true memories
included. Not licensed: any claim that CAS geometry helps retrieval generally.

Items 5-6 not built; they were gated on this result and are now unlocked.


## 2026-09-02 - PHASE LANE CLOSED by owner ruling (CMB-P2 not launched, $0)

CMB-P2 closed as CONSTRUCT_INVALID_TWO_HOP_SHORTCUT. The benchmark contained a two-hop
shortcut, so it never required the system to separate thought chains: a phase-free, label-free
rule scored 0.8255/0.8568 against an oracle handed the true labels at 0.7682/0.6797. The
shortcut was created by the repair for the previous shortcut.

Frozen state. CMB-P0 and CMB-P1 preserved exactly, including PHASE_MEMORY_UNSAFE. P8+P9
preserved as a promising engineering observation, NOT as evidence that phase separates thought
chains. The phase hypothesis remains open - neither proven nor disproven. Phase integration
into CMB-R1 is not authorized. Frequency, pulse width and Q are not added to the main memory
system. No immediate phase-benchmark redesign is authorized.

Registered return condition: phase may return only when an independently designed benchmark
proves that ordinary content, one-hop search, two-hop search, topology and candidate identity
cannot solve the task - measured before any phase arm, and re-measured after any world repair.

Total spend across the whole phase arc: $0.2776.

Next active lane: CMB-R1 / RGM-0.2. The production memory board stays scalar and accountable.


## 2026-09-02 - CMB-P2 STOPPED PRE-LAUNCH: a phase-free rule beats the oracle ($0 spent)

The owner authorized one final controlled confirmation of the P8+P9 combination. Adversarial
review returned DO-NOT-LAUNCH, and the decisive finding verified: **a two-line rule that never
looks at which chains are active beats the arm handed the true chain labels.**

  K=2 / K=3      P0 0.4974/0.3464   ORACLE 0.7682/0.6797
                 B_TWOHOP 0.8255/0.8568   B_TWOHOP x amplitude 0.9661/0.9323

The candidate set falls out of the adjacency matrix (recovered exactly in 6/6 worlds), and
while one hop is flat as intended, two-hop mass identifies the gold at ~2.3x its nearest rival.
I built that shortcut myself in the repair for the previous one: replacing the cue's private
one-hop edge with 0.65-weight edges from the cue's own chain to its completion IS a two-hop
signature.

WITHDRAWN: the claim that the task requires chain separation, and the "% of oracle" framing.
PRESERVED: PHASE_MEMORY_UNSAFE for CMB-P0 and CMB-P1, every measured number, and every
arm-vs-arm comparison - no arm uses the shortcut, so all were equally blind.

Not fixed-and-launched: flattening two-hop mass removes the chain-specific evidence entirely,
so the oracle could not solve the task either. That is a world redesign, which the directive
prohibits. Owner decision.

Also: a verifying agent read held-out worlds 506-512, so the held-out range moved to 536-565.

Verified as NOT defects: the phase-shuffle control is fair and informative - in the
no-information limit shuffling is an exact no-op (gap 0.0000) and the collapse scales with real
structure.

Third label-free shortcut found in this bench family. The standing rule found it again: a win
by mechanism M is uninterpretable until it beats the cheapest method without M.


## 2026-09-02 - CMB-P1 phase repair bench: PHASE_MEMORY_UNSAFE, no repair survives ($0.1135)

Owner-authorized repair bench (R4). Three repairs tested separately: signed coupling,
frequency heterogeneity, and a trajectory readout. **None survives.**

The sharpest result: **at convergence the phase engine is numerically identical to the scalar
engine** - 0.503/0.343/0.251 at K=2/3/4, matching P0 to three decimals, with merge fraction
1.000 at every K. The CMB-P0 numbers were a transient; this is the destination.

P7 genuinely fixes synchronisation (global order 0.218 vs 1.000) but buys attribution by
destroying retrieval. P8 came closest, failing one criterion narrowly. P9 has a global order
parameter identical to P4, confirming it repairs the readout and not the dynamics.

P8's structural claim is NOT supported: shuffling the frequency values across nodes costs only
~0.05, so the benefit is desynchronisation rather than structural coding. The controls carried
for exactly this purpose caught it.

The exploratory P8+P9 combination reaches 90/84/77 percent of oracle accuracy with near-zero
merging, beating the tag arm on both axes - but it carries no verdict by construction, and it
has no shuffle control in this run, so it is an unverified number rather than a result.

A first launch cost $0.14 and returned nothing: it finished all GPU work then crashed writing
the receipt, and the partial-receipt guard was scoped too narrowly to save it. Root cause was
testing run_world() but never main(). Fixed, with an end-to-end test added.

Not licensed: any resonance or CAS-specific claim, any P8P9 claim, anything beyond these
synthetic worlds, or any merge into CMB-R1. Next step is a third-party audit.


## 2026-09-01 - CMB-P0 multi-chain phase bench: PHASE_MEMORY_UNSAFE (AWS GPU, $0.0241)

Owner-authorized side bench. Asked whether phase-coded two-state memory separates
simultaneous overlapping reasoning chains better than a scalar engine, explicit tags, the
same extra state without phase, and its own phase-destroyed control.

**Result: the phase arm beat every control at every K, and was still refused.**
`P4_PHASE_OSCILLATOR` won all five registered comparisons at K=2/3/4 - the pattern for
`PHASE_MULTICHAIN_SIGNAL` - but the pre-registered safety override fired first: it collapses
0.657 / 1.852 / 3.538 distinct chain pairs at K=2/3/4 (3.54 of 6 possible pairs at K=4) in
20/20 worlds, against a threshold of 0.50, versus 0.000 for the oracle. It retrieves better
while losing track of which chain it retrieved from.

Contamination is *not* the defect (P4 is better than P0 at every K). Secondary negatives:
extra state alone buys nothing, and *inferred* tags are worse than no tags while *oracle*
tags are far better - inference, not the tag mechanism, is the bottleneck. GATE_ORACLE
failed at K=4 (0.560 < 0.60), so that stratum is ill-posed; the verdict does not depend on
it and is decisive at K=3.

**The bench was stopped pre-launch by its own adversarial review and rebuilt first, at $0.**
Three reviewers found - and measurement confirmed - that the gold answer was recoverable
from one edge weight in 1152/1152 dev queries, that the 64 queries per world were only 2-4
distinct, and that K=2,3,4 were pooled into one bag tolerating 18 negative worlds (the same
defect this project raised twice against a sibling lane). Eleven further defects were
repaired, two broken control arms were re-frozen upward, and a seventh control arm added.

Not licensed: any resonance-specific or CAS-specific claim, anything beyond these synthetic
worlds, or any merge into CMB-R1. Stopped after the report; next step is independent audit.


## 2026-09-01 (CJT-EX1 RAN, AMENDED) - NO_CJT_EXPERT_SPECIALIZATION_SIGNAL: a PROVEN meaningless partition (E4) ties the CAS partition (E2) at +0.0006, so CAS expert MEANINGS are not load-bearing; the designated killer control E1S DEGENERATED via router collapse and that comparison is VOID; $0.2404 of the $1.20 cap; branch research/cjt-dev-p1-s7d1-fivearm-v1

- Owner amended the protocol after the pre-launch stop and authorized the run: headroom-aware breadth (QB_COMP frozen as saturated; QB_REL + QB_INT eligible), repaired retention (phase 1 QB_INT -> phase 2 QB_COMP with a real-interference gate), E1S anonymous sparse top-1 added as THE killer control, E3 demoted to exploratory, result vocabulary frozen, E4 required to be PROVEN class-independent. 36/36 runs on one self-terminating g4dn.xlarge (i-090962eb9f5dc5129, 27.4 min, instance_runtime_estimate $0.2404 authoritative; harness lower bound $0.2032).
- **ARMS (family C transfer, 597 records, 3 seeds): E0 0.7733 / E1 dense 0.7767 / E1S 0.7655 / E2 CAS 0.7806 / E3 0.7789 / E4 shuffled 0.7800.**
- **THE DECISIVE RESULT - E2 vs E4 = +0.0006 (~0.09 paired se).** E4 was proven class-independent before the run (MI 0.000084 bits over 54,000 train clauses; 0.0030 in-run vs E2's 1.7477) with near-uniform expert load [0.236, 0.250, 0.264, 0.251]. A stable but MEANINGLESS partition of clauses across four experts does exactly as well as the CAS operation partition. Whatever small advantage exists over a learned router comes from having a FIXED assignment, not from the assignment carrying CAS meaning. In the owner's frozen vocabulary this is the substance of CAS_EXPERT_MEANINGS_NOT_LOAD_BEARING; the law did not emit that status only because its test is a strict point-estimate inequality (E4 >= E2) and E4 landed 0.0006 below. Status left exactly as emitted.
- **KILLER CONTROL VOID - E1S ROUTER COLLAPSE.** Measured expert load [0.001, 0.000, 0.999, 0.000]: 99.9% of clauses routed to ONE expert, so E1S was one working expert with three dead ones at a quarter of the active capacity - which is why it scored LOWEST of all six arms. The E2-E1S margin (+0.0151, below the 0.02 threshold anyway) is therefore evidence about four working experts versus one, NOT about CAS routing versus learned routing. Cause: no load-balancing auxiliary loss - the standard MoE failure mode; neither I nor the 56-agent review caught it. E1 dense was also skewed ([0.128, 0.167, 0.122, 0.583]).
- **BREADTH PASSED but is explained away by E4:** both eligible families improved vs E1S with 3/3 seeds - QB_REL paired +0.0204 (52.2% remaining-error reduction, +4.06 answers), QB_INT paired +0.0542 (8.3% error reduction, +10.78 answers). QB_COMP correctly excluded as saturated (E1S 1.0000); E2 actually LOST 0.0303 there.
- **RETENTION: catastrophic forgetting in every condition.** The interference gate PASSED (every arm gained 0.43-0.49 on the new task with 500/500 nonzero-gradient updates and real parameter movement), and retained QB_INT collapsed from ~0.37 to 0.005-0.041 - BELOW that family's 0.0909 chance, i.e. active re-mapping, not mere decay. Forgetting spread across all six arms is 0.343-0.368 against ~0.35 absolute, under 8% of the effect; E0 (single shared expert) and E4 (meaningless routing) tie for the LEAST forgetting. Expert organization gave essentially no memory protection. E3's involution body-sharing did not help (-0.0017): no STRUCTURED_WEIGHT_SHARING_SIGNAL.
- Cumulative spend $2.129 of $30 (7.1%). Protected splits and the sealed C2 half untouched; prohibited terms unused; no claim promoted. Per the standing rule there is no second EX1 repair - whether to re-run E1S with load balancing is an OWNER decision.

## 2026-09-01 (CJT-EX1 BUILT, PRE-LAUNCH REVIEW, NOT LAUNCHED) - 56-agent review found 18 confirmed defects; TWO of the owner's seven success conditions are compromised by DATASET properties, not by the architectures under test; STOPPED BEFORE SPEND pending an owner ruling; $0; branch research/cjt-dev-p1-s7d1-fivearm-v1

- Owner ruling: standalone table/J lane CLOSED; carry J forward as a computational constraint inside experts; next primary experiment = CJT-EX1 Expert Specialization and Transfer Pilot, on AWS GPU. Owner also CORRECTED my earlier wording (adopted): labels are street names, R is the map of how streets connect — labels alone do NOT literally contain R; labels + enough examples let a learner reconstruct it. J remains a legitimate inductive prior; my theorem wording was broader than the mathematics warranted.
- BUILT: five conditions over the A1 recurrent graph executor with its two clause-local scorers replaced by expert banks — E0 SHARED / E1 ANON_MOE (learned soft router) / E2 CAS_EXPERT (hard-routed by true operation class) / E3 CAS_STRUCT (E2 + the canonical ^2<->^3 involution as a COMPUTATIONAL rule: aversion IS attraction with reversed orientation) / E4 SHUFFLED (frozen per-clause hash). Transfer is built into the data (train families A,B verbs 0-5 forms 0-3; eval family C verbs 6-7 form 4, never seen). Prereg frozen (CJT_EX1_PREREGISTRATION.md), cap set at $1.20, projected $0.62.
- **TWO STRUCTURAL BLOCKERS, verified with exact counts, NEITHER about the architectures:** (1) **condition 3 near-unsatisfiable** — on the exact eval split QB_COMP is saturated at 1.0000 so a +0.02 margin is ARITHMETICALLY IMPOSSIBLE there, and QB_REL at 0.97449 would need 78.4% of ALL remaining errors; only QB_INT (0.3777) has room, so "spans >=2 families" reduces to QB_REL AND QB_INT. (2) **condition 6 decided by the generator** — QB_COMP contains ZERO ^3 clauses in all 3000 records (and no family but QB_REL uses ^3), so under hard class routing E2/E3's ^3 expert gets no gradient in retention phase 2 and CANNOT be overwritten; E2/E3 are structurally protected by the clause template, not by expert organization, while E0/E1 are not. Running as specified would spend on a near-certain negative that says nothing about the hypothesis — the same empty-comparison trap the owner praised avoiding when C2 was retired.
- **FIXED BEFORE ANY SPEND (mechanical, unambiguous):** match_capacity returned the FIRST width inside the 1% band while scanning upward, so every CONTROL landed on the low edge while hypothesis arms hit target exactly (E1 was 0.908% BELOW E2) — a bias toward the hypothesis, the dangerous direction; replaced with exact binary search, spread 0.974% -> 0.206%, E1 now +0.138% above target. E3 did NOT implement its registered mechanism (docstrings claimed a shared body; code allocated four independent bodies and tied only the readout) — E3 now genuinely shares the involution body, verified. False docstring claims that E1/E4 are label-blind corrected (every arm receives the class profile via the attention path — they are expert-organization-blind). The E2-vs-E1 sparsity confound (E1 dense 1,442,816 active params/clause vs E2 sparse 360,704) disclosed in code; it biases toward the null, the safe direction.
- One CRITICAL was REFUTED and the refutation is recorded: the claim that hard routing starves E2 was wrong (E4 is also one-expert-per-clause, and E2's per-class training density is 4.0x E4's). Ten further confirmed defects remain, all fixable at $0, and will be fixed before launch. NOT LAUNCHED; cumulative spend unchanged at $1.889/$30.

## 2026-09-01 (J0 BENCH, $0 CPU) - J0_GENUINE_J_DEPENDENT_CASES_EXIST, BUT the owner's "flat labels do not reveal it" gate FAILS and is unsatisfiable for any R-based task; a J track is constructible only as a PRIOR-VS-LEARNED test, never as an identifiability test; branch research/cjt-dev-p1-s7d1-fivearm-v1

- Owner ordered J0: search the ACTUAL CAS rules for cases where M+C leave the answer ambiguous but M+C+J determines it, with counterfactual twins and four deterministic checks. Executed on local CPU, $0.
- **AUTHENTIC CASE FOUND: the ^8/^9 (Above-Cause / Below-Effect) converse pair.** Grounded in the canonical definitions and the CO-8<->CO-9 involution invariant: the two classes describe the SAME edge read in opposite directions. Twins: "algebra evoked botany for mira. chess was evoked by botany for mira." (answer chess) vs "algebra was evoked by botany for mira. chess evoked botany for mira." (answer algebra) — same entities, same class multiset, same M/C, same candidate set, same template. **All four checks pass**: full M+C+J resolves both; twins differ; J removed → both UNRESOLVED; J corrupted → wrong; unrelated J cell → no effect. M cannot do this job (it licenses BOTH directions); C cannot (identical both ways); only the DUAL relation determines it.
- **PRECISE DIAGNOSIS OF THE OLD TASK:** PATH B used ^2,^3,^6,^8 = ONE complete involution pair (^2<->^3) plus TWO half-pairs (^6 without ^5, ^8 without ^9). A half-pair cannot express a converse relation, so no composition had two admissible directions. **Sharper bonus finding:** under canonical edge semantics the task vocabulary DID contain an M-symmetric chainable pair (^6,^8) — but no question family ever queried it. It was the QUESTION DESIGN, not the algebra, that left J with nothing to do.
- **THE BLOCKING RESULT (measured, not asserted):** the owner's condition "flat operation labels do not reveal it" FAILS on the very case found — the twins have distinct (label-sequence, entity-slot) signatures, so a flat-label→answer function provably exists. And this is structural, not a fixable accident: **R = (M,C,J) is a function of the class labels**, so no part of R can ever be INFORMATIONALLY necessary to a learner that already receives exact labels. Any R-based task fails that condition by construction.
- **CONSEQUENCE:** Outcome B as written is not fully satisfiable (7 of 8 conditions are engineerable; the flat-label one is not). What survives is legitimate and testable but different in kind: whether the correct lookup supplied as a FROZEN PRIOR beats LEARNING it (sample efficiency, OOD transfer) — the R-CAS vs R-LEARNED contrast, with T2 as the diagnostic socket. That is a claim about inductive bias and must never be promoted into one about information or specificity. Also NOT established: >=2 J-dependent families (only one converse pair exists canonically — ^2/^3 is valence, ^5/^6 relates different entity types) and baseline headroom. Nothing further built; owner decides. Cumulative spend unchanged at $1.889/$30.

## 2026-09-01 (J-NECESSITY TEST, $0 CPU) - TIER_C_J_NOT_IDENTIFIABLE_ON_CURRENT_TASK (owner Outcome A): removing the entire J plane changes ZERO answers; an M-first solver is invariant across all six registered J conditions; J is CAPABLE but REDUNDANT because M's asymmetry already decides every case; branch research/cjt-dev-p1-s7d1-fivearm-v1

- Owner ruled after C1: run ONE CPU-only $0 J-necessity test before any further spend, six conditions (full M+C+J / J removed / sign flipped / dual swapped / wrong J / unrelated cell), count answer changes. Executed on 9,597 records (9,000 train + the 597 C1 val half; the C2_STRUCTURE_EVAL half NOT read).
- INSTRUMENT: pathb_core.solve() never consults R, so "perturb J and watch the gold" is degenerate (the gold would not move under M or C perturbations either). Built an R-DRIVEN solver that computes answers FROM the table, plus two clause-grammar rules that are observable surface structure and not table content. **Validity gate: reproduces gold 9,597/9,597 (1.0000).** The FIRST attempt scored only 3,196/9,597 and was reported INSTRUMENT_BROKEN rather than used — the defect was diagnostic (result_type IDEA cannot pick between the two idea slots of a ^8 clause). J was given every chance: the solver asks J FIRST, before M.
- **RESULT: J removed → 0 answers changed. M-FIRST control → 0 answers changed in ALL SIX conditions. M intact / J suppressed → 9,597/9,597 correct.** The J-FIRST instrument did change 12,793 answers under sign-flip / dual-swap / wrong-J, but those measure the cost of TRUSTING a wrong J, not the task's need for J — the registered status law decides identifiability from the M-first control and J-removal, explicitly excluding J-first-only changes.
- **CAPABLE BUT REDUNDANT (a distinct finding from useless):** M symmetrized + J available → 9,597/9,597; M symmetrized + J suppressed → 0/9,597. The duality/sign plane is a genuine, *sufficient* alternative route to the execution order; it is simply never the *only* route. ROOT CAUSE: M has 4 derived cells and every queried class pair is asymmetric in M — (^3,^2) licensed but not (^2,^3); (^2,^8) but not (^8,^2); (^2,^6) but not (^6,^2) — so direction is pinned by M alone and J's distinctive content is never consulted.
- CONSEQUENCES per the ruling: C2 must NOT run (its R-CAS vs R-EMPIRICAL contrast differs ONLY on J, which is not identifiable → empty by construction); the present Tier C task closes; the neural network is NOT to blame (T2 demonstrably read the table — authority 3.28x, bridge 0.5717 vs 0.3272, corruption collapse to 0.299 — there was nothing in it the task rewarded); C1 is NOT reinterpreted as a win and remains genuine negative evidence for this table, these transforms, and this task. Recorded (not proposed) for a possible Outcome-B task: J is identifiable only if some family names a class pair SYMMETRIC in M, so order cannot come from M. Retained: LM, recurrent graph executor, operation profiles, clause-entity binder, M/C/J algebra, T0-T4 implementations, control machinery. Cumulative spend unchanged at $1.889/$30.

## 2026-09-01 (TIER C C1 RAN) - NO_TRANSFORM_CONSUMES_STRUCTURE: no transform beat the no-structure baseline (all four slightly NEGATIVE); T2 became heavily dependent on the table and nearly doubled formal-bridge agreement while gaining NOTHING on the task; $0.1808 of the $0.80 cap; branch research/cjt-dev-p1-s7d1-fivearm-v1

- Owner authorized C1 ($0.80 cap, one instance, C2 NOT auto-authorized, "specific" after C1 = TOO EARLY). Ran 15 runs (T0 + T1-T4 x seeds 11/23/47, 1000 updates) on one self-terminating g4dn.xlarge T4 (i-07dfc2821c7032c44, 20.6 min, instance_runtime_estimate $0.1808 authoritative; harness compute_wall_estimate $0.1429 recorded separately as a lower bound). All P0 gates pass; preflight verified dataset digests, BOTH C1 and C2 pid-set digests, and the R_CAS/R_RANDOM digests fail-closed before any GPU work; cache binding verified 9000 + 597 records.
- **RESULT: T0 0.7800 / T1 0.7744 / T2 0.7783 / T3 0.7772 / T4 0.7521** — margins -0.0056 / -0.0017 / -0.0028 / -0.0279, none reaching +0.02, seeds-positive 0/3, 1/3, 1/3, 0/3 (se~0.024). Because T0 already carries the exact one-hot operation labels, C1 answered: **does a relational TABLE add anything ON TOP of exact operation labels? On this task: no.** The negative is NOT an artifact of the saturation-constrained family clause — every OVERALL margin is negative too.
- **PRINCIPAL MECHANISTIC FINDING (T2): consumption without benefit.** T2's structure channel reached 3.28x the base attention score and nearly DOUBLED formal-bridge agreement (0.5717 vs T0's 0.3272), and the trained model is massively table-dependent — removal 0.778→0.672, permutation →0.424, R-RANDOM →0.299 — yet its task margin is -0.0017. Structure consumption and formal-path agreement both improved while accuracy did not. Second time on this task family that the formal path and the answer came apart (in A1 the winning arm had WORSE bridge agreement; here the best-bridge arm gains nothing).
- **HEADROOM (beyond the registered disclosure):** the prereg flagged QB_COMP at ceiling (1.000); the run shows QB_REL is ALSO effectively saturated for the baseline at 0.9745. Real headroom exists only in QB_INT (0.378) and NO transform improved it (T1 -0.0246, T2 -0.0099, T3 exactly 0.0000, T4 -0.0755). The tournament had one genuinely open family and the table did not help it.
- Per-transform: T1's channel ended up carrying zero decision weight (all three ablation falls exactly 0.0000); T3 tolerates losing the table (removal +0.0022) but not being lied to by it (permutation +0.096, R-RANDOM +0.083); T4 is the only clearly harmful transform, costing QB_INT 15.3 answers per seed.
- **C2 CONSEQUENCE:** C2 was to freeze the C1 winner and swap rulebooks through it — there is no winner, so C2 as specified has no socket. Combined with the standing J-necessity blocker (C0 measured R-CAS and R-EMPIRICAL identical on M and C, differing only on J), C2 is now blocked on a DESIGN question, not merely on sign-off. Owner decision. Per the prereg, no second tournament: the negative is recorded and kept. Cumulative program spend $1.889 of $30 (6.3%). Protected splits and the C2_STRUCTURE_EVAL half untouched; prohibited terms unused.

## 2026-09-01 (TIER C C0 BUILT + GATED) - TIER_C_C0_READY_FOR_FOCUSED_REVIEW: frozen relation algebra R=(M,C,J) derived cell-by-cell from the solver + canonical invariants (Aut trivial), two-part non-equivariance proof on per-example trajectories (Test A exact 0.0 all 24 perms x T1-T4; Test B min divergence 0.114-1.160 vs floor 0.001, 2 data seeds), 3455 matched non-isomorphic controls, genuine trace estimator R-EMPIRICAL (M/C converge 16/16 MEASURED, J differs -> the C2 killer contrast isolates the duality/sign prior), QC_VALID diagnostic + R-only probe within bounds, 14-agent adversarial review (1 CRITICAL refuted, 7 CONFIRMED defects all fixed pre-freeze); CPU only, $0; C1/C2 GPU awaits owner sign-off; branch research/cjt-dev-p1-s7d1-fivearm-v1

- Owner ruling "TIER C v0.2 — C0 CONSTRUCTION AUTHORIZED" executed with all binding amendments: R-RANDOM reclassified RELATIONAL_MISINFORMATION_CONTROL (wrong structure = misinformation, the A1 lesson as law); killer controls = R-LEARNED + R-EMPIRICAL; QC_VALID diagnostic-only (excluded from win status/headline/family-removal) with the R-only <= chance+0.05 law (measured: REL .1013/COMP .1227/INT .1173, all within bounds); R=(M,C,J) minimal typed algebra, per-cell source rules, typed UNDEFINED/NO_DUAL, no invented strengths; QB-ORD stays dropped (final for this dataset version); C1 cap $0.80 / C2 cap $0.60, no transfer.
- STRUCTURE: M has exactly 4 derived cells — (^3,^2) REL mind-bridge, (^2,^8) COMP mind-bridge, (^2,^6) INT idea-bridge, (^6,^6) INT part-join — each citing its solve() rule; J carries the CO-2<->CO-3 involution, signs, and the missing-dual asymmetry of ^6/^8. Aut(R_CAS) = {identity} over all 24 perms; the M-only-triviality dependence on the join cell is disclosed with a persisted counterfactual (without it: {id, ^6<->^8}; full R stays trivial via the C plane).
- PROOF v2 (per-example criterion after review hardening): consistent renaming conforms EXACTLY (0.0, all 24 perms, all 4 transforms, plus the no-structure recipe-validity baseline mirroring A1's S-PERM); the class-indexed absorption recipe FAILS against frozen R by 0.114-1.160 per-example divergence on both data seeds (old batch-mean criterion gave only 0.0036-0.0093 — the review attack that curve-fit 5 means to 1e-4 was refuted as an absorption, diverging 1.68 per example and "absorbing" R_RANDOM under identity labels, but the per-example upgrade was adopted anyway).
- ADVERSARIAL REVIEW (TIER_C_C0_REVIEW_FINDINGS.json): CONFIRMED+FIXED before freeze — R_EMPIRICAL's C plane was transcribed not estimated (now a genuine slot/pool-typed estimator; the 16/16 M/C convergence is now a measurement); QC surface over-claim (registered char-level adversary persisted: char-ngram 0.4933 = chance, length-order rule 0.8350 — disclosed; readout = contrast between R-variants); QC pid suffix encoded gold (HashPRNG tag scramble + decorrelation gate); cache verifier missed duplicate pids and never checked model/tokenizer/extraction shas (now 11 violation classes fail closed); mutation battery had hardcoded 7-point entries (now per-point MEASURED/BY_CONSTRUCTION basis, M14 judges via the registered predicate); R_CORRUPTED50 confounded wrongness with 3x density and skipped J sign/dual (v2 cell-transplant law, density-preserving in expectation, all planes corrupted, per-plane counts persisted); runner hardening (full vocabulary schema, G-C0-5 split, byte-deterministic receipt, library versions persisted).
- All 10 gates PASS; receipt + all 13 tier_c artifacts byte-identical across three runs. NEXT: owner's focused review of the C0 package; C1 (transform tournament, 27 runs, cap $0.80) and C2 (7 conditions x 3 seeds, cap $0.60) remain NOT authorized until then. No GPU spend; no protected read; prohibited terms unused.

## 2026-09-01 (PATH-B-A1 CLOSURE + INDEPENDENT AUDIT + TIER C DESIGN) - owner closure ruling executed: component findings separated, one independent 3-auditor raw-result audit of 3bbcd2c1 (ZERO numerical discrepancies; flagged survives-clause concern SUBSTANTIATED with exact residuals), Tier C design v0.1 drafted for owner ruling; $0 spend; branch research/cjt-dev-p1-s7d1-fivearm-v1

- Owner ruling "PATH-B-A1 CLOSURE AND TIER-C TRANSITION": 3bbcd2c1 + NO_PATH_B_OPERATION_SIGNAL PRESERVED; separated findings recorded (cjt_path_b_v2/PATHB_A1_COMPONENT_FINDINGS.json): COMPOSITIONAL_GRAPH_EXECUTOR / EXACT_OPERATION_PROFILE_ADVANTAGE / PROFILE_CONTENT_CAUSAL_DEPENDENCE = SUPPORTED_IN_DEVELOPMENT; MONOTONIC_50_PERCENT_WRONG_LABEL_DOSE = REFUTED; FORMAL_PATH_FAITHFULNESS = UNESTABLISHED. Interpretation corrections adopted: S-ALT50 is a corruption arm; its −0.0033 vs S6 = no useful difference (the anti-informative evidence is the permutation ablation .787→.118); advantage concentrated in QB_REL.
- INDEPENDENT AUDIT (PATHB_A1_INDEPENDENT_AUDIT.json; three parallel auditor agents, raw artifacts only): every mean/std/margin/per-family value/boolean reproduced EXACTLY (population std n=3 confirmed); status-law replay shows NO_PATH_B_OPERATION_SIGNAL was the only reachable status (both failed clauses driven by the single raw fact SALT50 0.742815 < S6 0.746074, gap 0.003259); alt50 corruption rate 0.499736 train / 0.499333 val, balanced, substitutions spread ~1/3; dataset sha256 match manifest exactly; pids all unique/disjoint; ablations eval-only, S6 invariance mathematically forced; governance clean (zero protected-read violations, zero prohibited-term claim-use, cumulative spend independently recomputed $1.708 ≈ stated $1.71, 5.7% of ceiling).
- OWNER'S FLAGGED ITEM SUBSTANTIATED: survives_best_family_removal as coded = strict positivity vs S6 only; removing QB_REL leaves residuals 0.006222 vs S6 (~7 of 1125 answers), 0.001333 vs S0 (~1.5 answers), 0.008000 vs SALT50 — all would fail a 0.02 criterion. Honest as coded, weak as designed. Findings short of discrepancy: P0 gate_s3_profile_grads UNVERIFIABLE (grad log never persisted); cache assertions count-level only + not bound to dataset hash; four PATH B runs lacked standalone receipts → retroactive receipt filed with per-field sources (CLOUD_EXECUTION_RECEIPTS_PATHB_RETROACTIVE.json; A1 instance i-0b479d3ea577e98a7 recovered from the contemporaneous launch record; live sweep 2026-09-01T09:28Z: zero experiment instances, only the owner standby stopped).
- TIER C DESIGN v0.1 drafted (cjt_path_b_v2/TIER_C_DESIGN_v0_1.md), design only, $0: frozen 4×4×F CAS composition structure (solver semantics + involution sign + missing-dual asymmetry), PROOF_OF_NON_EQUIVARIANCE before spend (trivial-automorphism enumeration + pathway pinning + the A1 conformance test required to FAIL + mutants M13/M14), matched generic relational control R_gen (win over BOTH or CAS_SPECIFICITY_NOT_ESTABLISHED), new QC_VALID family, bounded Transform Tournament T0-T4 (27 runs ≈$0.55), attenuation (λ-blend) and misinformation (ρ) as SEPARATE dose axes (21 runs ≈$0.45), formal-path faithfulness as measured outcomes, all four audit corrections as harness laws (persist gate inputs; residual ≥0.01 vs all arms; cache-to-dataset-hash binding; same-commit receipt law). C0 is CPU-$0 and stops at TIER_C_CONSTRUCTION_FAILED; owner-signed approval required before any C1 spend.

## 2026-09-01 (PATH-B-A0 + A1 COMPLETE) - GRAPH_EXECUTOR_EARNED, executor P0 perfect, P1 = NO_PATH_B_OPERATION_SIGNAL on the monotone-dose clause alone; the corrupted-label dose point INVERTED (SALT50 0.7428 < S6 0.7461) — half-wrong labels are anti-informative, not half-informative; branch research/cjt-dev-p1-s7d1-fivearm-v1

- A0 (clean rerun after the pid-collision repair, $0.246): GRAPH_EXECUTOR_EARNED at every layer — bridge recovery 1.000/0.973, second-hop binding 1.000/up to 0.807, full gold-path (no gold bridge) 1.000/up to 0.767 vs uniform 0.104; destructive drops ≥0.30 both controls; earliest passing layer 6 FROZEN (L12's better holdout reported, not selected). Clean PRB-POS max 0.848 < 0.90 → QB-ORD drop confirmed on valid evidence.
- A1 (recurrent clause-entity graph executor, 2 preregistered hops, soft bridge pointer preserved between hops, identical across arms; first launch died on a missing sys.path import, $0.074, preserved as execution fault; relaunch i-0b479d3ea577e98a7, 26.6min, $0.233): **P0 ALL GATES PASS** — memorization 1.000, gold-path 1.000 vs shuffled-path 0.124 (gap 0.876), rewired 0.178 (drop 0.822), bridge top-1 0.922, S3 grads/swap ✓, S6 exactly invariant ✓, params matched ✓. The executor provably executes and depends on the path.
- **P1 (4 arms × 3 seeds × 1000u, L6): S0 0.7553, S3 0.7873, SALT50 0.7428, S6 0.7461** — the compositional task is now largely SOLVED on fully unseen verbs+forms (QB_COMP 1.000, QB_REL 0.86-0.98; QB_INT hard ~0.38). S3 clears S0 by +0.032, S6 by +0.041, SALT50 by +0.044 (all above thresholds and above the 0.019 B-KEY increment); S3's corruption ablation is devastating (true 0.787 → permuted 0.118, uniform 0.394); floor ✓; survives best-family removal ✓. **The single failed clause: monotone dose ordering — SALT50 < S6 overall and in 0/3 families.** Deterministic status NO_PATH_B_OPERATION_SIGNAL per the frozen law, preserved.
- SUBSTANTIVE FINDING (reported, not relitigated): the dose design assumed 50%-corrupted labels are half-informative; measured reality is that half-WRONG labels actively mislead routing (SALT50 ≈ its own uniform ablation 0.739/0.743; S3's permuted 0.118 ≪ uniform 0.394 shows the same asymmetry) — label noise is anti-informative in a routing channel. The exact-profile advantage itself met every margin clause. Mechanism note: S3's formal-bridge top-1 (0.330) is lower than S6's (0.550) despite winning — the profile-equipped executor routes by its own strategy, not the formal trace.
- Per the owner stop law: no second graph-binder repair, no threshold changes, no result-driven family substitution. PATH B closes with the executor earned+working, the task beaten, the exact-label advantage real by margins but the registered dose law honestly failed. Next per the directive: Tier C or the CAS Transform Tournament — owner's move. Cumulative arc GPU ≈ $1.71 of $30. Both protected splits untouched; no claim; prohibited terms unused.

## 2026-08-31 (PATH B P0 RAN) - BINDING_REPAIR_FAILED: the frozen P1.3 clause-local binder is structurally mismatched to the compositional v2 task (gold-routing INVERTED 0.133 vs shuffled 0.258; memorization 0.711); the gates stopped P1 exactly as designed; branch research/cjt-dev-p1-s7d1-fivearm-v1

- PATH B v0.3 CPU stage was fully green (PATHB_GATES_PASS; CHK_M_PASS 11/11; SPERM_EQUIVARIANCE_CONFIRMED 7.15e-07; 12000/1500/1500, 0 exclusions, round-trip 100%; commit 7b5dc11b). P0 then ran on one self-terminating T4 (i-06806594ed90c7648, 28.1min, ~$0.247): L*=12 (layer profile changed vs v1's 18/24 — task-dependent), all four dose arms trained (S0 .2693, S3 .2620, SALT50 .2267, S6 .2460 @100 updates), S6 exactly invariant (Δlogit 0.0000), S3 swap-sensitive (0.128), profile grads real, λ≈0.98-1.0.
- FAILED GATES (the owner return contract's first branch): gate1 memorization 128 = 0.711 < 0.95; gate2 gold-routed 0.133 < shuffled 0.258 — INVERTED: one-hot routing onto the answer-bearing clause DESTROYS the selector context the mixture needs, the cleanest possible mechanistic proof that the clause-local expert binder's core assumption (answer determined within one routable clause) is exactly what PATH B was built to break (v0.2 risk finding #18 realized); prb_pos 0.888 < 0.90 → QB_ORD auto-drop rule fires (owner D3) — though QB_ORD is ironically the ONLY family the head learns well (S0 0.784 vs uniform 0.143), a frozen-rule tension recorded for the owner; transfer floor: only QB_ORD above uniform+0.05 at 100 updates.
- NO P1 ran (correctly gated). NO redesign attempted (owner: "do not construct a third binder"; "endless static redesign PROHIBITED"). The v1-arc result stands untouched; the v2 finding is itself valuable: the architecture that WON the v1 task cannot express the v2 task's compositional binding — the task upgrade did its job. Whether to authorize a PATH-B-specific architecture round, resize the P0 gates (e.g. memorization updates), or bank here is an OWNER decision. Cumulative arc GPU ≈ $1.26 of the $30 ceiling. Protected splits (v1 AND PATH B) untouched; no claim; prohibited terms unused.

## 2026-08-31 (PATH B task design v0.1→v0.2) - operation-graph spec drafted, adversarially reviewed (19/19 findings CONFIRMED incl. the S-PERM equivariance THEOREM), rewritten as v0.2 for owner review; no build, no GPU, $0

- Owner ruled: move to PATH B (no third binder; new protected derivation; 7 bijection-breaking requirements). Drafted PATH_B_TASK_SPEC_v0_1.md (operation graphs, 5 question families, executable CHK gates) then ran a 22-agent adversarial design review: 19 non-MINOR findings, ALL confirmed, 0 refuted (SPEC_V0_1_REVIEW_FINDINGS.json).
- Deepest finding (#7, CRITICAL): with profiles entering only via learned linear W_r, (W_r g)·(P p)=(Pᵀ W_r g)·p — any bijective relabel control (S-PERM) has S3's loss landscape under reparameterization; the planned "identity vs distinguishability" tie is a THEOREM, not an experiment. Flat-label "CAS-specific" is untestable in this architecture; specificity relocates to Tier C (structural geometry, frozen read-in). Also CRITICAL: the answer-key gate was dishonest both directions (real leak = profiles+membership+positions+anchors composite; naive ceiling beatable by type priors) → rebuilt as a TRAINED adversary gated on the per-family PROFILE INCREMENT with a B-MEMBER symbolic reference; MAX_IDEAS=6 vs K≤9 crash; S-ALT bijection certificate contradiction.
- v0.2 folds in all 19: K≤6, 100% non-bijective passages w/ anchor exclusion, per-family gating + per-family uniform references, candidate-order shuffle law, QB-INT anti-counting law + registered surface shortcut, QB-ORD before/after balance + counterfactual CHK-8 + PRB-POS position-probe drop-rule, QB-XOP demoted to dataset property, per-family uniqueness constraints, v1 verbs retired from ALL surfaces, S-PERM demoted to two-sided sanity control, S-ALT as honest Δ.2 dose point, TOTAL interpretation law (incl. SHORTCUT_BOUNDED_SIGNAL and READOUT_UNDERPOWERED_V2 branches), transfer floor-guard, assemble_v2 plumbing, 40 new verbs / 6 forms with stated allocation.
- Owner decision points D1-D5 (Q-B2 reframe, K vs MAX_IDEAS amendment, QB-ORD keep/drop, sizes, protected derivation choice). v1 protected split untouched; nothing builds or runs until v0.2→v0.3 approval.

## 2026-08-31 (cjt-dev-p1.3 FINAL binding-conversion round) - PROMISING_DEV_SIGNAL: clause-local expert binder converts the CAS routing advantage into the arc's first task-level win (S3 0.7340 beats every control by 0.034-0.080; both S3+S0 exceed B0 0.668); all 9 smoke gates passed; branch research/cjt-dev-p1-s7d1-fivearm-v1

- Owner ruling executed verbatim: router/L18/profiles/λ/data/seeds/optimizer frozen; ONLY the binder replaced (pooled passage vector → clause-local answer experts P(c|x)=Σᵢ αᵢ·softmax_c(ℓᵢ,c), per-clause candidate occurrence vectors, absent candidates masked, no gold clause in train/eval). Pre-launch adversarial review caught a gate-validity defect (binding shuffle permuted padded rows = evidence deletion on 74.6% of records) — fixed to per-example live-prefix permutation BEFORE spend (15b79aea).
- P0 smoke: ALL 9 gates passed — memorization 1.000; gold-routed 0.984 vs shuffled 0.266 (+71.9pp; old binder's oracle gain was +3.6pp); binding-shuffle drop 0.781; S3 swap-sensitive; S6 exactly invariant; 0 answers lacking a clause occurrence; params matched (S0 803,712 vs 807,301 = 0.44%).
- P1 (5×3×1000, T4 21.3min $0.187, i-03930a7a062250516): S0 0.6997, S3 0.7340, S6 0.6843, S7H 0.6830, S7D 0.6537. S3−S0 +0.034 (2/3 seeds ≥0.02), S3−S6 +0.050 (2/3), S3−S7H +0.051 (3/3), S3−S7D +0.080 (3/3); no per-type collapse; S3 corruption: permuted 0.414 (wrong labels actively mislead), uniform/zeroed 0.642; S6 exactly invariant; S7-Δ's soft profiles HURT vs uniform (0.654 vs 0.681). Gold-clause hit S3 0.869. λ grew to ~1.13-1.15 on content-bearing arms. → deterministic status PROMISING_DEV_SIGNAL (all 6 owner win conditions).
- FIRST time any arm beats the B0 surface heuristic (S3 0.734, S0 0.700 > 0.668). Calibration caveat: S3 NLL 2.79 > S0 1.88 despite higher accuracy (over-confident when wrong) — reported, not gated. Bounded reading per ruling: task-aligned label advantage on a controlled surface-solvable dev task; "CAS-specific" PROHIBITED; development triage label only. Protected split untouched; no claim promoted; per the ruling this was the FINAL static binder test — no further static redesign. Cumulative arc GPU ≈ $0.83 of the $30 ceiling.

## 2026-08-31 (cjt-dev-p1.2b λ-fix rerun) - routing branch finally TRAINED; S3 routes gold clauses best (47.2%) and is the ONLY content-sensitive arm; final accuracy still NO_DEV_SIGNAL (binding ceiling); frozen-mode P0 honestly FAILED its gradient gate

- Single repair per the owner closure directive (λ init 1.0) + executable P0 gates + adversarial pre-launch review (6 agents; proved S6's routing gradient is mathematically zero by design — uniform profiles are a softmax-invariant shift — S6 exempted from the w_r gate; stale "λ learned from 0" provenance fixed pre-launch). One T4, 20.5min, ~$0.18 (i-0e3bfa3a929f5d6cd); cumulative project GPU ≈ $0.64.
- PRIMARY frozen-candidates config: PILOT_PIPELINE_FAILURE at P0 — S3 w_r grad 1.3e-14 at step 50 (early softmax saturation at L*=24 still starves routing); P1-frozen SKIPPED by the boot script per protocol. A real gate catch, preserved.
- SECONDARY contextual config: P0_SMOKE_OK (all gates; S3 routing grads real 7.9→2.2→0.08; swap Δlogit 0.52). P1 (5×3×1000, L*=18): S0 0.3737, S3 0.3780, S6 0.3630, S7H 0.3590, S7D 0.3617; S3−S0 +0.004, S3−S6 +0.015, S3−S7H +0.019, S3−S7D +0.016 → NO_DEV_SIGNAL (nothing ≥0.02; seed ranges overlap).
- FIRST MECHANISTIC SEPARATION: gold-clause attention hit rate S3 0.472 > S6 0.423 > S0 0.365 > S7H 0.346 > S7D 0.248 — the exact CAS operation profile routes best; and S3 is the ONLY arm whose accuracy declines under profile shuffle/replacement (.378→.365/.355/.356; S6 exactly invariant, verifying the shift-invariance math in vivo; S7H/S7D gain nothing from their true profiles). λ stayed ~0.9-1.0 everywhere.
- BINDING CEILING CONFIRMED: +11pp routing advantage converts to +0.4pp accuracy (matches Diagnostic D's oracle result). Emitted status NO_DEV_SIGNAL; the pattern matches the owner's READOUT_STILL_UNDERPOWERED description (observation, not the emitted status). Train-subset ~0.78 vs val ~0.37 = cross-family generalization gap on top. No protected split, no claim, prohibited terms unused.

## 2026-08-31 (cjt-dev-p1.1 + p1.2: diagnostics + five-arm relaunch RAN) - readout repairs lifted every arm ~0.21→0.37-0.40 on real GPU; five arms statistically indistinguishable → NO_DEV_SIGNAL; λ-init flaw locked routing (documented, not relaunched); branch research/cjt-dev-p1-s7d1-fivearm-v1

- Owner rulings S7Δ.2 ("association is not copying") + P1.2 ("correct the power analysis, diagnose the readout, then run five arms") executed end-to-end. S7-Δ-WN1-V3 ADMITTED under magnitude gates (A_soft*=0.523915<0.75, A_hard*=11/16<14; CAS-free builder, WordNet pin fail-closed, byte-frozen v2 profile reuse, 16-sense audit AUDIT_PASS_NO_SENSE_CORRECTIONS; MC nulls descriptive only). Corrected baselines frozen: chance = candidate-uniform (val 0.12284/2.15307), regime = ABOVE_UNIFORM_LOW_COMPETENCE_READOUT; train/val share ZERO clause verbs.
- CJT-DEV-P1.1 diagnostics (T4, 562.8s, ~$0.154, i-0a7840fe7f1e41f59): machinery healthy (128-ex memorization 1.000); v1 attention COLLAPSED+DEAD (entropy 0.0, gold top-1 23.7%, w_q grad ~1e-17); profile channel INERT (true=uniform=permuted=zeroed) — mechanically explains all v1 ties; gold-clause oracle +0.036; contextual candidates +0.031; in-distribution 0.278 vs cross-family 0.210 (binding-readout generalization is the primary bottleneck; CAS profile helped in-distribution +0.042, ~2.3 SE, evaporates cross-family).
- CJT-DEV-P1.2 five-arm relaunch (T4, 19.8min, ~$0.173, i-07a77393bfa2c7a27): RoutedHead + contextual candidates, L*=18, P0_SMOKE_OK, P1 = 5 arms × 3 seeds × 1000 updates. Mean val acc S0 0.3737, S3 0.3943, S6 0.3990, S7H 0.3810, S7D 0.3753 (all ~3× candidate-uniform; far below B0 0.668). S3−S0 +0.0207, S3−S6 −0.0047, S3−S7H +0.0133, S3−S7D +0.0190 → NO_DEV_SIGNAL; all seed ranges overlap; S6 (uniform) nominally highest.
- λ-INITIALIZATION FINDING (recorded, not relaunched — stop law): λ init 0 makes the routing-query gradient ∝λ=0, a chicken-and-egg lock; routing never engaged; the accuracy doubling came from the profile-independent candidate-grounding repair. S3 uniquely escaped λ=0 in 2/3 seeds (0.055/0.051) — directionally interesting, inside noise, licenses nothing. Fix (λ>0 init or no gate) documented for a future owner-authorized iteration.
- Cumulative GPU spend all three cloud runs: ~$0.46 of the $30 ceiling. No protected split, no claim, prohibited terms unused. Commits 3fb7802b (V3+audit), 91609d94 (diagnostics), this one (five-arm results).

## 2026-08-31 (cjt-dev-p1-s7d1 statistical correction + five-arm rebuild) - S7-H REGISTERED, S7-Δ v2 FAILED its frozen permutation-invariant anti-copy gates; five-arm pilot NOT launched ($0); branch research/cjt-dev-p1-s7d1-fivearm-v1

- Owner ruling CJT-DEV-P1-S7Δ.1 (adopt-with-modifications) executed. Exact-null calibration INDEPENDENTLY RE-VERIFIED by full enumeration of all 63,063,000 balanced partitions before freezing anything: P(V≥0.353553)=0.9000405, P(V≤0.35)=0.0999595, P(A*≤8/16)=0.81205, P(A*≤9/16)=0.94555, attainable-V lattice 0.288675→0.353553→0.408248 — all five matched the ruling exactly. "Missed by 0.0036" language RETIRED (STATISTICAL_CORRECTION_S7.json); 19d9e843 preserved with narrowed interpretation (the protocol failed its gate; nonexistence of an honest semantic control NOT established).
- S7-H REGISTERED (build_s7_h.py → S7_H_WN1.json, sha a93a516c…): the honest primary-lexname partition (V=0.353553, exact-null p=0.90) rehabilitated as the hard control, re-verified from the frozen assignment (balanced 4/4/4/4, χ²=6.0, ≠S3, not a permutation, own A*=7/16 ≤ 9/16). Split type tags adopted: profile_semantics + authority fields.
- S7-Δ v2 rebuilt under ALL Δ.1 laws (build_s7_delta_v2.py): background NMF fit EXCLUDING the 16 target senses (TF-IDF, balancing, and factors all background-only, targets projected after); factor-stability gate PASSES perfectly (median mean-row JS 0.0000 across 5 predetermined random-init fits, Hungarian-aligned); all 4 background-frozen anti-uniform gates PASS; raw+balanced profiles preserved (mean balancing row-L1 0.0369). VERDICT: S7_DELTA_V2_CONSTRUCTION_FAILED — the permutation-invariant anti-copy gates fail: A_hard*=11/16 (>9/16 structural; shuffle-null p95=10, p=0.0109) and A_soft*=0.5239 (>p95=0.4532, p=0.0016); robust to the owner-literal entropy-matched null (diag_s7_delta_v2_nulls.py: p=0.00688/0.00121). Correction 1 caught exactly its target loophole — v1's naive argmax check missed the same 0.52 soft alignment (v1 would fail these gates too).
- Substantive reading (not a claim): the 16 verbs were CHOSEN to instantiate the 4 CAS operations, so any faithful soft semantic representation echoes that grouping; the hard partition survives the same standard only because hard categorization discards most of the alignment information. Semantic-coherence evidence about the VOCABULARY; NOT CAS specificity.
- STOPPED at the failed gate per "PROCEED AFTER THESE BOUNDED CONTROL-INTEGRITY CHECKS" + the research-governance law. No GPU, no AWS call, $0 this round. Owner decision: (a) four arms S0/S3/S6/S7-H without S7-Δ; (b) recalibrate the near-copy gate to copy MAGNITUDE rather than alignment SIGNIFICANCE (the current gate rejects any detectable alignment, in tension with the ruling's own "correlation reported, not contamination"); or (c) close the S7-Δ line.

## 2026-08-31 (cjt-dev-p1 CLOUD GPU pilot COMPLETE) - NO_DEV_SIGNAL: on real Qwen2.5-0.5B (AWS Tesla T4, $0.133) the CAS-coupled head ties the plain, uniform, and WordNet-soft controls at ~0.21 val accuracy; branch research/cjt-dev-gpu-pilot-v1

- Owner amendment CJT-DEV-P1-S7Δ (preserved at commit 354f315c): the hard S7-P partition (FAILED, below) is replaced by a SOFT WordNet semantic simplex control S7_DELTA_WN1. `build_s7_delta.py` gives each of the 16 verb senses a 4-component Δ³ profile (`SEMANTIC_COMPOSITION`) via a frozen 4-factor NMF (nndsvda, random_state 0) over the FULL ~13.7k-verb WordNet 3.0 sense inventory (TF-IDF over lexname/gloss/hypernym/frame features), sense-in-context per verb (CAS never consulted), then gentle global factor-scale equalization. Construction-integrity gates all pass (finite/nonneg/rows sum 1; rank 4; ≠S3; no permutation=S3; hardened-argmax ≠ CAS permutation; no CAS/Qwen input; 4-dim interface). Cramér's-V ≤0.35 is dropped for the soft control; soft CAS-alignment (soft MI 0.244 nats, mean entropy 0.604) is REPORTED after freezing, not optimized. The S7-P FAILED verdict is NOT rewritten.
- Owner directive "no local use cloud aws or runpod": ran the pilot on ONE self-terminating AWS g4dn.xlarge (Tesla T4 16GB, us-west-2a, torch 2.5.1+cu121, AMI ami-0c779ec711a581954). Boot → install → download Qwen → P0 smoke → P1 → upload results → self-terminate in 15.1 min for ~$0.133 (triple-guarded termination: terminate-on-shutdown + 90-min in-instance timer + 55-min client watchdog; far under the $30/2h owner ceiling). is_real_model true; no protected split touched; no claim promoted. The known EC2-GPU-quota 0.0 blocker is us-east-1 ONLY — us-west-2 has 8 vCPUs G/VT quota. AWS account 807562639912, IAM user cas-g5-operator, bucket cas-harness-runpod-92754088.
- P0 smoke: P0_SMOKE_OK (all 4 arms trained, candidate tensors present, losses finite, no CPU fallback, params matched). P1 (S0/S3/S6/S7-Δ × seeds 11/23/47 × 1000 updates, L*=24): mean val acc S0 0.2117, S3 0.2123, S6 0.2140, S7-Δ 0.2113. S3−S0 +0.0007, S3−S6 −0.0017, S3−S7-Δ +0.0010 — none clears +0.02. Verdict NO_DEV_SIGNAL. S3 ties S6 → the profile CONTENT is not load-bearing here.
- HONEST CAVEAT: all four neural arms (~0.21) fall far below the surface baselines (B0 class-blind floor 0.668; B1 surface ceiling 1.000). The comparison is FAIR (every arm shares the readout handicap) but the low absolute ceiling makes this a WEAK/underpowered test — a small profile benefit could be masked near the floor. A stronger-readout follow-up is an OWNER research-design decision, not taken here (stop law honored: committed raw results + CLOUD_EXECUTION_RECEIPT, pushed, stopped; no protected read, no claim, no auto-continue to Gate 1B, no redesign). Prohibited terms (CAS-specific / EMPIRICALLY_SUPPORTED / GATE1B_PASS / CJT_TRANSFORMER_VALIDATED) not used. One EOL note: Windows autocrlf made the S3-bundled S7_DELTA_WN1.json hash c216da05 vs the LF-canonical committed efe61cc1 — byte-identical modulo line endings, science unaffected; a .gitattributes now pins the pilot dir to eol=lf.

## 2026-08-31 (cjt-dev-p1 gpu pilot — S7-P gate) - S7_PILOT_CONSTRUCTION_FAILED: no principled semantic WordNet control of the 16 registered verbs is orthogonal to CAS; pilot stopped BEFORE any GPU use, on branch research/cjt-dev-gpu-pilot-v1

- The owner authorized CJT-DEV-P1, a development-only (non-claim-bearing) static neural GPU pilot: 4 arms (S0 plain / S3 CAS-coupled / S6 uniform-capacity / S7-P independent WordNet control) × 3 seeds × 1000 updates over frozen Qwen2.5-0.5B activations, $30/2h ceiling. The first hard gate — build S7-P — must pass BEFORE any GPU launch, else emit S7_PILOT_CONSTRUCTION_FAILED and stop.
- New separate directory `cas_only_reasoner/cjt_dev_gpu_pilot_v1/` (the frozen Gate 1B package is untouched). `build_s7_pilot.py` constructs S7-P from a pinned WordNet 3.0 snapshot (wordnet.zip SHA-256 `cbda5ea6…`, 10,775,600 bytes, Princeton WordNet 3.0 License) and computes every gate. Verdict recorded in `S7_PILOT_BUILD_RECEIPT.json`.
- RESULT: the gate FAILS. The 16 verbs' CAS classes are semantic operation-types (attract/avert/decompose/trigger) and WordNet organizes verbs semantically, so every CAS-blind semantic WordNet partition correlates with CAS above the ≤0.35 threshold: the repo's own frozen construction_law (verb primary-sense lexname) gives Cramér's V=0.3536 (fails by 0.0036); the hypernym-lexname fallback 0.6124; all no-judgment semantic features ≥0.354. The ONLY passing construction (synset-offset shuffle, V=0.289) is non-semantic and would only be selected because it passes — i.e. manufacturing, which the directive forbids. This confirms the taxonomy manifest's own circularity_disclosure.
- Per the directive + the owner's law ("a hard gate that fails is a FAILURE"; "Claude is NOT the research governor"), the pilot STOPPED before any GPU use. No model loaded, no AWS call, no spend, protected split never touched. The negative result is committed as a load-bearing artifact. Resolving S7-P (structured-random control, threshold change, vocabulary/resource change, or dropping the S3-vs-S7 comparison) is an OWNER governance decision.

## 2026-08-31 (gate 1a.2r.2b watchdog config authority) - config read moved inside the fail-closed boundary + no unsigned REAL default per the third-party recheck of 3ce84531 (R.2A VERIFIED_PASS; surviving MAJOR: malformable config envelope + unsigned-default fallback), on branch research/cjt-gate1a2r2b-config-authority-v1

- Two defects the recheck isolated: (a) `_read_signed_cap` ran OUTSIDE the try/except, so a top-level `[]`/`null`/scalar config raised before the boundary and the watchdog vanished with no marker/burn/termination; (b) a missing/malformed config fell back to an unsigned 2.5h default, loosening the owner-signed 2h cap. Fixed (amendment A17):
  - New exec/watchdog_config.py: dictionary-ONLY exact schema bound to campaign id / package commit / approval digest / owner key id / signed cap; the stale limit MUST equal signed_cap*3600*1.1; arrays/null/scalars/wrong-keys/list-valued-limits/bool/zero/negative/NaN/infinity all refused.
  - REAL mode has NO unsigned default: a missing/malformed config fails closed; only non-claim-bearing conformance modes may use a documented default when the file is absent.
  - watchdog_main reads+validates the config INSIDE the boundary → any failure yields WATCHDOG_INTERNAL_ERROR marker + protected-lock burn + termination request + exit 2.
  - Heartbeat writes are atomic (temp + os.replace); a top-level non-dict heartbeat envelope is WATCHDOG_INVALID_HEARTBEAT (no escaping TypeError).
  - The driver writes the bound config; 9 config-authority + 12 heartbeat + 9 clock tests pass; all suites + synthetic campaign + byte-domain green.
- SCOPE per the owner's directive: config authority ONLY. S7 and the GATE 1A.2S evidence findings remain OPEN. Package NOT owner-signable; owner key stays on HOLD. Neural evidence: 0.

## 2026-08-31 (gate 1a.2r.2a heartbeat fail-closed) - make the REAL heartbeat clock immutable and malformed timestamps fail closed per the third-party recheck of 7e69f8a2 (numeric-future attack CLOSED; surviving MAJOR: mutable _clock + a non-numeric heartbeat crashes the watchdog), on branch research/cjt-gate1a2r2a-heartbeat-failclosed-v1

- The watchdog assumed anything JSON-decodable is a number: `driver._clock = lambda: "not-a-number"` wrote a valid-JSON string heartbeat that the watchdog parsed then compared numerically -> raw TypeError escaped, and watchdog_main didn't catch it, so the timeout process could vanish. Fixed (amendment A16):
  - CLOCK IMMUTABILITY: CampaignDriver._beat() reads time.time() directly in REAL, so post-construction _clock mutation is inert (mirrors _hook()).
  - FAIL-CLOSED VALIDATION: is_valid_timestamp requires a finite, non-bool, non-negative number; beat() refuses invalid values; poll_once validates observed-now + the parsed heartbeat; json.loads rejects NaN/Infinity; a malformed heartbeat (string/list/dict/bool/NaN/inf/negative, or an unparseable non-empty file) emits WATCHDOG_INVALID_HEARTBEAT + terminates + returns False -- no raw TypeError, never fresh.
  - watchdog_main wraps poll in try/except -> WATCHDOG_INTERNAL_ERROR marker + termination request + exit 2 on any error.
  - 12 named heartbeat fail-closed tests pass; all suites + synthetic campaign + byte-domain green.
- SCOPE per the owner's directive: heartbeat fail-closed ONLY. S7 and the GATE 1A.2S evidence findings remain OPEN. Package NOT owner-signable; owner key stays on HOLD. Neural evidence: 0.

## 2026-08-31 (gate 1a.2r.2 production clock isolation) - remove production clock injection and reject future heartbeats per the third-party recheck of e3fcfda0 (hook isolation VERIFIED_CLOSED; surviving MAJOR: injectable production clock), on branch research/cjt-gate1a2r2-clock-isolation-v1

- The clock was the last injectable production adapter: a caller could pass clock=lambda: time.time()+1e9 to REAL, and the separate watchdog read the negative heartbeat age as fresh, suppressing the signed timeout. Fixed (amendment A15):
  - The production CampaignDriver has NO clock parameter. REAL ALWAYS uses time.time; SYNTHETIC_CONFORMANCE uses a fixed replay clock; a fake clock is permitted ONLY in REAL_BRANCH_CONFORMANCE via the subclass. A clock in REAL/SYNTHETIC is a hard CLOCK_ISOLATION_VIOLATION.
  - Watchdog.poll_once distinguishes no-heartbeat / fresh / stale / IMPOSSIBLE-FUTURE: a heartbeat beyond now+5s emits WATCHDOG_FUTURE_HEARTBEAT and terminates, so a future clock can never extend the ceiling.
  - The conformance status proof now EXECUTES the real emit_gate1_status program: REAL_BRANCH_CONFORMANCE → SOFTWARE_CONFORMANCE_ONLY / non_claim_bearing=true; a production-looking owner key under --conformance is refused.
  - 9 named clock-isolation tests pass; hook-isolation, REAL-branch, synthetic-campaign, byte-domain all green.
- SCOPE per the owner's directive: clock isolation ONLY. S7 (i//4 ≡ CAS class order) and the GATE 1A.2S evidence findings remain OPEN. Package NOT owner-signable; owner key stays on HOLD. Neural evidence: 0.

## 2026-08-31 (gate 1a.2r.1 production hook isolation) - structural isolation of production from conformance hooks per the third-party audit of a6d17c63 (F-G1A2R-1: REAL mode accepted fake AWS/GPU/model/lock adapters), on branch research/cjt-gate1a2r1-hook-isolation-v1

- The audit was right that a one-line constructor guard is insufficient: the driver also exposed set_real_feature_backend and a mutable _real_hooks dict. Fixed structurally (amendment A14):
  - The production CampaignDriver admits ONLY REAL + SYNTHETIC_CONFORMANCE, has NO public real_hooks parameter, NO set_real_feature_backend, and its _hook() helper reads the registry ONLY in REAL_BRANCH_CONFORMANCE — so mutating _real_hooks in REAL is inert.
  - A non-empty hook map in REAL or SYNTHETIC_CONFORMANCE is a hard HOOK_ISOLATION_VIOLATION.
  - New third posture REAL_BRANCH_CONFORMANCE, owned by a separate RealBranchConformanceDriver subclass (the only class that admits hooks): runs the REAL code paths with fakes but is PERMANENTLY non-claim-bearing — TEST trust root, SYNTHETIC clock, status --conformance (SOFTWARE_CONFORMANCE_ONLY; production owner keys refused).
  - Mode posture expressed by _is_claim_bearing()/_uses_real_branches()/_trust_mode().
  - 11 named hook-isolation attacks pass; the REAL-branch adapter suite still executes under the new posture.
- SCOPE per the owner's directive: hook isolation ONLY. The S7 independent-taxonomy control defect (the i//4 builder reproduces the CAS class order) and the other GATE 1A.2S findings (complete receipts, final-status finalization, in-status signature verification, burn-receipt binding, provenance replay, salted-manifest typing, complete container prep, verify-before-stage, failed-job cost) remain OPEN. The package is NOT owner-signable. Owner key stays on HOLD. Neural evidence: 0.

## 2026-08-31 (gate 1a.2r real-path executability) - the REAL Gate-1B branch made executable per the owner's independent source audit of fc7ceb48 (verdict: REAL_GATE1B_EXECUTION_PATH_REFUTED — synthetic fixtures hid 14 branch defects), on branch research/cjt-gate1a2r-real-path-v1

- The audit's diagnosis was exact: synthetic conformance substituted working fakes precisely where the REAL branches were broken stubs. ALL 14 findings closed (amendment A13):
  - REAL candidate encoding WIRED (was `cand=None` → `.shape` crash): `extract_split` now returns h/g/cand (context-free frozen input embeddings) in ONE forward pass for all 4 layers; no passage reaches training/scoring with cand=None.
  - Container bootable: `aws` CLI calls (image never installed it) replaced by committed boto3 `exec/stage_main.py`; watchdog no longer terminates before the first heartbeat (startup grace), shares the REAL epoch clock, reads the SIGNED per-job cap from `watchdog_config.json`.
  - AWS protected-lock unified with local (both return `lock_receipt_sha256`, same schema; the REAL success path no longer KeyErrors after burn); ONE outer burn boundary wraps every post-claim step; the watchdog burns an abandoned AWS lock.
  - REAL training implements the frozen schedule: `exec/batching.build_batches` (batch-32, seeded full-corpus, 3000 updates, seed governs data order); the duplicate run is ACTUALLY compared and REFUTES on mismatch; all 29 runs emit complete receipts.
  - Container-prep driver (`exec/container_prep.py`); S7 staged + built; REAL monotonic cost (no invented 0.01h) + whole-remaining-schedule gate; live model allow-list + live PIP_FREEZE hash; salted-manifest digest enforced; status supports 3 OR 5 seeds (read from evidence); evidence chain validated SEMANTICALLY (checkpoint/cache bytes recomputed, receipts parsed, protected-eval receipt written AFTER evaluation); complete failure-evidence upload + S3 path join; CAS mapping-rules + PATH-A binding in the execution approval.
  - NEW `tools/test_real_branch_conformance.py` exercises EVERY REAL adapter with fakes (fake tokenizer/model/embeddings, fake DynamoDB, fake S3, fake clock) — no model, GPU, or AWS; the branches synthetic mode bypassed are now tested directly.
- Full battery green: 12 unit/attack suites + the end-to-end synthetic campaign (13 sabotages, replay-identical, SOFTWARE_CONFORMANCE_ONLY) + byte-domain. Scope held: NO model, NO GPU, NO AWS, NO protected read, NO key, NO signature. Neural evidence: 0.

## 2026-08-31 (gate 1a.2 campaign-authority freeze) - END-TO-END CAMPAIGN AUTHORITY, PROTECTED EVIDENCE, AND SYNTHETIC CONFORMANCE frozen per the owner's Gate 1A.2 directive, on branch research/cjt-gate1a2-execution-authority-v1 from the verified byte-freeze anchor a6140e0c

- CAMPAIGN LIFECYCLE (§1): one typed 18-state machine (`exec/campaign_state.py` + 3 schemas) — every transition binds campaign id, package commit, authorizing approval/receipt digest, and input/output digests in an append-only sha256-chained log; skips/repeats/wrong-campaign refused; failure inside the protected phase must burn before shutdown; synthetic replay is chain-digest-identical.
- TWO-SIGNATURE DETACHED APPROVALS (§2): prep-specific binding law repairs the v2 incoherence (prep never carries artifact_digests and can never authorize training); execution approval v3 binds EVERY resolved identity (model revision + weight/tokenizer file maps, container + dependency-lock digests, taxonomy table, run schedule, prep receipt, seeds, AWS account/instance/GPU, max hourly rate, ceilings) — nothing deferred past the signature; signed approvals are DETACHED files, refused if found inside the tree.
- OWNER TRUST ROOT (§3): production key ONLY from `trust/OWNER_PUBLIC_KEY_PIN.json` (template deliberately invalid: OWNER_KEY_NOT_YET_PINNED); no CLI/env/caller key substitution anywhere; TEST- keys refused in production and permanently non-claim-bearing; owner key NOT generated.
- REAL DRIVER (§4): LAUNCHER_STUB_GUARD REMOVED — `exec/campaign_driver.py` executes the 30-step ordered path; infra recipes frozen (Dockerfile, requirements.lock, bootstrap.sh, terminate-on-shutdown + IMDSv2-required launch template, separate watchdog process).
- FROZEN RUN SCHEDULE (§5): receipt set DERIVED from the signed RUN_SCHEDULE manifest (29 runs: 4 layer-selection + 24 claim-bearing + 1 duplicate), never `len==25`; 12 named refusals proven.
- CALLBACK-FREE PROTECTED EVALUATION (§6): committed prediction path that cannot read answer/seed_trace/raw labels; separate GoldScorer with per-prediction checkpoint provenance; digest-verified checkpoint loading; 7 attacks proven.
- ONE-USE PROTECTED LOCK (§7): atomic O_EXCL local backend + DynamoDB conditional-write AWS backend; burns on success/failure/interruption; 8 concurrent claimants → exactly 1 wins; burned tokens unreusable.
- IDENTITY + AWS CHECKS (§8): IMDSv2+STS real identity; local CUDA never satisfies the gate; model/tokenizer/container/dependency/taxonomy digest verification; 10+ named refusals proven live.
- COST + TERMINATION AUTHORITY (§9): no --hourly-rate anywhere; signed worst-case pre-job gate; overrun ⇒ campaign FAILED; every path (success/failure/timeout) writes receipt + requests termination; watchdog terminates abandoned campaigns.
- EVIDENCE-CHAIN-BOUND RESULTS (§10): RAW_GATE1_RESULTS v2 carries 21 provenance fields; status program v4 validates the chain (receipt-file digests, arm×seed key grids, baseline arithmetic) BEFORE reading any metric; unbound results → EVIDENCE_UNBOUND; conformance/TEST-key mode law makes synthetic status permanently SOFTWARE_CONFORMANCE_ONLY.
- BOTH protected derivations implemented, NEITHER chosen (§11); owner decisions represented as typed unresolved fields that fail the schema (§13).
- SYNTHETIC_CONFORMANCE (§12): the SAME driver runs end-to-end on CPU against a hermetic package copy (clean-tree law honored) — full lifecycle to TERMINATED, replay-identical chain, plus 13 sabotage detections (rogue key, widened prep, tampered approval, schedule binding, missing taxonomy, tampered weights, REAL-on-local refusal, second protected read, unbound results, cost manipulation, callback absence, stub absence, universal termination).
- Compute boundary held: NO model, NO GPU, NO AWS, NO container build, NO protected-set generation beyond the frozen in-memory law, NO key, NO signature, NO claim. Neural evidence: 0.

## 2026-08-31 (gate 1a.1r byte-domain repair) - FROZEN-BYTE REGENERATION AND FRESH-CLONE SELF-BINDING repaired per the owner's ruling on the third-party audit of ff6f40f9 (F-G1A1-1 CONFIRMED: the freeze was REFUTED — the manifest bound bytes that were not the bytes in the commit)

- ROOT CAUSE (owner-confirmed): `tools/generate_construction_gold.py` pinned LF for train/val but wrote `DATASET_MANIFEST_CANDIDATE.json` with the platform default → CRLF working tree (`dff10734…`, the hash PACKAGE_MANIFEST bound) while the committed blob was LF (`c05bf809…`, normalized by autocrlf at the pre-.gitattributes staging). A fresh clone therefore failed verification — the instrument correctly refused the mismatched specimen. SECOND coordinated defect: the frozen manifest embedded `"generation_interpreter": "3.14.0"` while claiming interpreter independence (the 3.11 container would rewrite it). ff6f40f9 preserved in history as the failed-freeze negative fixture.
- REPAIR (amendment A10, one commit): (1) ONE canonical writer `exec/fsio.write_utf8_lf` (UTF-8, LF, every platform) now used by every authoritative generated file — generator, both manifests, unsigned approval, baselines, occurrence audit, raw results; (2) the frozen dataset manifest carries ONLY environment-invariant facts (generator_algorithm `HashPRNG_SHA256_COUNTER_V1`, generator/checker code digests, compatibility claim); the runtime interpreter/OS/invocation live ONLY in `results/generation_runtime_receipt.json` (excluded from the frozen tree); (3) `--output-root` added — Gate 1B regenerates to `results/<campaign>/regenerated_dataset/` and NEVER mutates the frozen tree (AWS manifest step 1 updated); (4) write-free `--check` modes on the generator and build_manifests (fixed-point comparison, nonzero on mismatch, zero writes); (5) permanent suite `tools/test_byte_domain.py` — all 11 owner-named tests: LF law, no-runtime-values, regeneration purity, second-regeneration byte identity, write-free checks, manifest==working-tree, manifest==COMMITTED-BLOB (`git show HEAD:`, CONFIRMED FAILING under ff6f40f9 — the recorded negative fixture), 3.11↔3.14 cross-interpreter byte identity (both interpreters run locally: 3.11.9 and 3.14.0 GENERATOR_CHECK_PASS), fresh-clone self-consistency via disposable sparse worktree, fresh-clone verify_full acceptance, clean-checkout zero-diff regeneration.
- DATASET RECORD CONTENT UNCHANGED: train `8d567a07…`, val `ae009357…`, protected `0c0c2842…` (in-memory only). Same logical dataset; same canonical bytes; same committed bytes — proven separately.
- Scope held: correction and reproducibility ONLY. Gate 1A.2 findings remain OPEN (executable launcher body, coherent container-prep verifier, structural owner-key pin, protected receipt/checkpoint binding, one-use campaign enforcement, cost authority, raw-result provenance). NO model, NO GPU, NO AWS, NO protected read, NO key, NO signature. Neural evidence: 0.

## 2026-08-31 (gate 1a.1 executable freeze) - EXECUTION AUTHORITY, STATUS LAW, CONTROLS, AND COMPLETE NEURAL CODE FREEZE per the owner's Gate 1A independent audit (verdict: GATE1A_DESIGN_CANDIDATE_PARTIAL_PASS, OWNER_SIGNATURE_HOLD)

- OWNER AUDIT of 49664dac accepted the dataset (7000 records independently re-parsed: 0 schema/trace errors, 0 cross-split overlap) but found 7 blocking defects. All closed in one commit on `research/cjt-gate1a-static-neural-v1`, package `cas_only_reasoner/cjt_gate1a_static_neural_v1/` (amendments A1–A9 in AMENDMENT_LOG.md):
  1. APPROVAL VERIFIER MADE LOAD-BEARING (the critical one): the old verifier returned True on a correctly signed record with phase=TOTALLY_WRONG, zero commit, empty digests, cost −999. Rewritten `tools/verify_phase_approval.py`: field law + Ed25519 vs the separately pinned key + commit equality + manifest-key-set equality + EVERY digest recomputed from the tree + untracked-file refusal + identity binding (model revision, weight/tokenizer/container/dependency-lock/taxonomy/status-program digests, protected commitment). The owner's exact bogus record is a PERMANENT failing test; 35/35 adversarial verifier tests pass. Two-signature gate added (OWNER_CONTAINER_PREP_APPROVAL then GATE_1B_EXECUTION v2 schema) so NOTHING is deferred past the execution signature. 24-vs-25 digest gap closed by construction (approval excluded from the manifest it binds).
  2. COMPLETE GATE 1B CODE COMMITTED BEFORE SIGNATURE: `exec/` (13 modules — arms S0–S7 + deterministic capacity matcher, label sources, assembly with gold-isolation + protected-path refusal, span mapping, context-free candidate encoding, activation extraction + digest-pinned cache I/O, training loop 3000-updates-no-early-stop, S0-only layer selection, single-pass protected evaluator, B0/B1, verification-first launcher with cost gates, receipt law), hashed in GATE1B_CODE_MANIFEST.json (26 files). CPU shape proofs ALL PASS: ±1% capacity (S0 w=238, S1 w=14, S2 w=205; S3 ref 951,744 params), S4–S7 state-dict-identical to S3, S4 differs from gold 100%, S5 75.5%, candidate masks, GPU_REQUIRED fires FIRST at every guarded entry (proven live on the CUDA-less box).
  3. STATUS AUTHORITY REPAIRED (THRESHOLDS v3): license requires beating ALL SEVEN controls; the owner's counterexample (S0=S1=S2=1.00, S3=0.80 — wrongly LICENSED by v2) now emits COUPLER_NOT_SUPERIOR_TO_SIMPLER_ARMS and is a permanent fixture; strict evidence validation (RAW_GATE1_RESULTS.schema.json; 16 malformed-evidence rejection fixtures) — no status from bad evidence.
  4. S7 renamed SINGLE_ALTERNATIVE_TAXONOMY (owner PATH A; never SCMPE-v1; cross-family instability disclosed); claim renamed TASK_ALIGNED_LABEL_AUXILIARY_VALUE; "CAS-specific" PROHIBITED on this dataset regardless of result; PATH B (real SCMPE-v1 + non-class-bijective v2 dataset) deferred.
  5. B1 SURFACE CEILING added and measured: full surface parser scores train 6000/6000 = 1.0000, val 1000/1000 = 1.0000 (the task is exactly surface-solvable BY CONSTRUCTION — every neural reading is bounded by this row); B0 floor 0.6445/0.6680 with attract/avert at the distractor-forced coin flip.
  6. Candidate encoding fixed: context-free frozen input-embedding rule (the owner's preferred option); occurrence audit recorded (17.4%/17.9% of answers first occur outside their target clause).
  7. GENERATOR DETERMINISM fixed at the root: random.Random → exec/prng.HashPRNG (pure SHA-256 counter stream, unbiased rejection sampling; byte-identical on every CPython ≥3.8). Dataset regenerated (twice, byte-identical): train `8d567a07…`, val `ae009357…`, protected `0c0c2842…` in-memory only; 7000/7000 round-trips pass. Commit-and-reveal salt option implemented for protected derivation (owner decision open).
- Compute boundary held: NO model load, NO GPU, NO AWS job, NO training, NO protected read, NO claim promotion. Owner's key never generated; nothing signed. Neural evidence: 0.

## 2026-08-31 (gate 0 FROZEN + gate 1a package) - GATE 0 PERMANENTLY FROZEN at 83f57d6f (owner: VERIFIED_PASS via independent cross-model audit); GATE 1A DOCUMENTATION FREEZE delivered on branch research/cjt-gate1a-static-neural-v1

- GATE 0 FROZEN: anchor 83f57d6f724505f2c2c68593b2625c36c3e07a4d; independent audit reproduced 246/246 tests, 26/26 scenarios, 8/8 injections, 22/22 mutations, replay, 9/9 target probes; 0 critical/major surviving. F-04/F-05 (2 nonblocking minors) recorded in `recursive_cjt_rc0/POST_GATE0_BACKLOG.md` — no patch carousel, maintenance-branch only, anchor immutable. Gate 1A AUTHORIZED (docs + freezing only); Gate 1B NOT authorized (needs the owner-signed record).
- GATE 1A PACKAGE `cas_only_reasoner/cjt_gate1a_static_neural_v1/`: all 18 owner-ordered artifacts + PACKAGE_MANIFEST + 5 committed tools + the CANDIDATE dataset. Frozen: CJT-T1 static dual-stream coupler (Qwen2.5-0.5B-Instruct frozen base, revision pinned at container build); four-Noetic restricted slice (^2/^3/^6/^8 — NOT CAS-40); S0–S7 table with S4=per-Idea hash-corrupted labels (review fix: a global permutation is absorbed by W_p and vacuous) and S5=hash-random labels (protected labelable without pre-reading); AdamW 1e-3, 3000 updates, no early stop; seeds 11/23/47 + mandated S0/seed-11 duplicate (25 runs); layer law {6,12,18,24} 1-indexed block outputs, S0-on-validation only; I_total := 1 (CAS-Ohm returns at Gate 2).
- CONSTRUCTION_GOLD candidate corpus generated deterministically (seed 20260831): 6000 train + 1000 val materialized (LF-pinned, one digest per file), 1000 protected generated in-memory, round-trip checked, digested `c1e19462…d70b8`, NEVER written; independent checker proven non-vacuous (wrong-answer/flipped-label/corrupt-clause/reordered-trace all caught); byte-identical regeneration proven. Registered distractor law: 100% of attract/avert items carry a confusable pair (co-occurrence = chance); question mix 2:2:1:1; equal-shape vocab bundles (review fix: collision-rate confound removed).
- INTERNAL ADVERSARIAL REVIEW (3 lenses, 59 findings) drove the honest-ceiling laws now frozen in the package: (a) the CAS stream is informationally redundant given text BY CONSTRUCTION — any S3 gain is an optimization effect, and a registered class-blind surface baseline (B0) must be reported as a floor; (b) S7 CIRCULARITY: the answer function is defined over the CAS classes, so no task-aligned non-CAS control can exist — Claim B's licensed words are downgraded to "task-aligned construction-gold process labels beat matched-capacity and alternative-taxonomy controls" (unqualified "CAS-specific" NOT licensed; owner decides bounded-claim vs v2 dataset); (c) protected secrecy is procedural not technical (public generator) — mitigated by the Gate-1B code-pinning-before-protected law + burned-split law; owner may choose a held salt instead. Status program `tools/emit_gate1_status.py` COMMITTED NOW (not deferred) with all 5 decision branches fixture-proven; approval upgraded to Ed25519 (verifier cannot forge; committed verifier tool); SCMPE 16-row head-verb table + executable fallback; capacity-matching algorithm, candidate encoding, span mapping, and input construction pinned.
- Compute-boundary confirmation: NO model load, NO GPU, NO AWS job, NO hidden-state extraction, NO training, NO protected read, NO claim promotion. Neural evidence: 0. CAS-specific neural advantage: 0.

## 2026-08-31 (cjt rc-0.4e) - EXECUTION-LIFECYCLE AUTHORITY, FINALIZATION ATOMICITY, AND SPLIT CAGING per the owner's independent RC-0.4D audit MERGED with the first third-party AI audit (which independently reproduced the full RC-0.4D battery and found F-01)

- TWO independent audits of ad46418f: the owner's source audit (promotion callable without finalization authority; tick() public; result() pre-final; finalization outside the fault boundary; SPLIT uncaged; child-ID collisions; cutoff relabel-repair) and a third-party AI agent that reproduced 205 tests/26 scenarios/8 injections/15 mutations/replay/manifest in a fresh environment and found F-01 (RuntimeError in the probe escaped run() unsealed with a stranded provisional). All closed per OWNER DIRECTIVE RC-0.4E in `cas_only_reasoner/recursive_cjt_rc0/`:
  1. RUN OWNS THE LIFECYCLE: typed phases NEW→RUNNING→FINALIZING→FINALIZED|FAULTED (seal-bound); tick() requires run()'s private scheduler capability; result() only in terminal phases AND only under a real seal or the honest marker; run() executes once from NEW and refuses non-pristine engines.
  2. PROMOTION IS AN AUTHORITY OPERATION: one-time-claimable lifecycle authority (the engine claims it at construction) + a one-use FinalizationPermit bound to episode/planned-final-digest/exact provisional ledger digest+index sets/state digest/sequence; voiding requires the authority token. The owner's verbatim bypass `tick → promote → result` refuses at all three doors.
  3. FINALIZATION IS ONE GUARDED TRANSACTION (F-01 exact): planned final snapshot (detached, with proposed PUBLISHED rows + final metrics) → permit → atomic promotion → gate trip only after planned==installed digest equality; ANY exception — RuntimeError, MemoryError, mid-promotion sabotage, no carve-outs — yields typed FAULT, terminal VOID of every provisional (voided_from provenance), phase FAULTED, deterministic seal. Nothing stranded between worlds.
  4. SPLIT CAGING (unit = child branch): total/GLOBAL-active/per-expert-Governance ceilings checked before budget; splits registered only for experts with a combined op (fail-closed split_no_combined_op); suspended frames swept into the failed-frame refusal at FINALIZE; the refusal recorded in BOTH evidence surfaces.
  5. GLOBAL CAUSE-ID UNIQUENESS: one used_cause_ids registry (initial+generated), child ids reserved pre-queue with deterministic collision-free allocation + typed ID_COLLISION; seal-bound. A top-level "p.c1" can no longer be captured, cancelled, or judged as p's child.
  6. HONEST CUTOFF: a ready-but-cutoff route stays NON-CONDUCTING under typed CUTOFF_CAUSE_UNRESOLVED (no relabel self-clear, no repairs_completed); real D/W/P blockers still repair; Desire deprioritized exactly once; a failed ASOM repair never retries in the same tick; every dropped cause gets a typed CAUSE_DROPPED disposition.
- INTERNAL ADVERSARIAL ROUND (3 lenses): 1 CRITICAL (both split paths silently dropped the opposite→quarantine / off_axis→repair consequences — now fire on resume and child collection) + 2 MAJOR (pre-run internals laundered into a sealed run — lifecycle guard on every internal + pristine check; dropped causes without disposition) + hardenings, all FIXED and test-locked.
- Mutation inventory frozen as v4 = fifteen v3 laws verbatim + 7 RC-0.4E laws (22 total; v1–v3 preserved). Exact numbers: suites 17+28+23+14+30+22+16+25+30+41 = 246/246 internal; scenarios 26/26; injections 8/8; mutations 22/22 CAUGHT semantically; manifest v4 law OK; replay identical. Status DETERMINISTIC_CONTROLLER_FEEDBACK_GATE0_PASS_PENDING_INDEPENDENT_AUDIT. Gate 0 NOT frozen; Gate 1A NOT begun.

## 2026-08-31 (cjt rc-0.4d) - SCHEMA-COMPLETE CONSTRUCTION, FINAL-PUBLICATION ATOMICITY, AND ASOM DISPATCH per the owner's independent RC-0.4C audit: the enumerated-patch era ends — one schema, one barrier, load-bearing actions, whole-object detachment

- Owner's independent audit of 38635986: verifier fixes CLOSED, but three criticals + one major in `cas_only_reasoner/recursive_cjt_rc0/` — the controller configuration was not preflighted (commit_verdicts=object() published then failed to seal), an unsealed run still held published==1 (the test suite itself asserted it), and ASOM cutoff/breakdown were decorative (present, computed, then HALT). Closed per OWNER DIRECTIVE RC-0.4D, correction-only:
  1. ONE INPUT SCHEMA: `_validated_constructor_config` + `CONSTRUCTOR_SCHEMA_PARAMS` govern EVERY `RC01Engine.__init__` parameter — validated, COPIED into owned state (no caller alias survives), import-time signature-coverage law, and an INITIAL SEALABILITY PROBE: the engine is not returned unless its entire initial state seals to a real 64-hex digest. Owner attacks `commit_verdicts=object()` and `[valid_cause, object()]` rejected at construction; the generalized adversarial matrix attacks every parameter with None/bool/object()/NaN/inf/mutables/malformed.
  2. PUBLICATION ATOMICITY: `PROVISIONAL_PUBLICATION` → prospective final-state canonicalization at the FINALIZE barrier → promotion to `PUBLISHED` (counted only then) → final seal. THE INVARIANT: `seal_digest == UNSEALED_TERMINAL_FAULT` ⇒ `published == 0` and no PUBLISHED ledger row. Failed/faulted runs terminally VOID provisionals (`VOIDED_UNSEALED`, receipts stay consumed). The prior test asserting published==1 on an unsealed run is repaired as ordered.
  3. ASOM DISPATCH LOAD-BEARING: at zero total score the computed actions fire BEFORE the no-ready fallback — breakdown → quarantine transition (`asom_region:breakdown`, excluded from routing); cutoff → typed repair of the ACTUAL blocker (real RPM prereq, Desire-law deprioritization, or a committed region re-assessment), bounded by RepairFrame; hard-masked experts never mutated; RPM FIRST_BLOCK stays a separate axis (all six directive tests).
  4. WHOLE-OBJECT DETACHMENT: `runtime_snapshot()` returns one `copy.deepcopy` of the completed snapshot (fault record included — the owner's alias reproduction is dead); taus and repair_requires are owned immutable/copied values.
  5. FROZEN INVENTORY v3 = the eleven v2 laws verbatim + constructor_schema_bypassed (killed by the SEALABLE poison commit_verdicts=1, which only the schema stops) + final_publication_barrier_removed + asom_zero_score_action_dispatch_removed + snapshot_whole_object_detach_removed; v1/v2 preserved on disk; new pinned digest.
- INTERNAL ADVERSARIAL ROUND (3 lenses, reproduce-not-triage): 2 MAJOR found and FIXED — (a) one Cause naming K ready cutoff experts was requeued and PUBLISHED K times → dispatch requeues AT MOST ONCE (also closes the split-child corollary); (b) a SUBSET states dict deferred failure to a raw mid-run KeyError past a provisional publication → a provided states dict must cover EXACTLY the registered expert set (also kills the states={} ambiguity). Plus: episode_id non-empty; the prospective probe catches only encoder (TypeError, ValueError) so environmental errors become typed FAULTs, not silent voids. Residual recorded: `_compute_final_seal` still swallows all Exception by design (it must never throw).
- New suite `tests/test_rc04d.py` (30). Exact numbers: suites 17+28+23+14+30+22+16+25+30 = 205/205 internal; scenarios 26/26; injections 8/8; mutations 15/15 CAUGHT semantically; manifest v3 law OK; replay identical; all owner attacks and both internal MAJORs reproduced-then-refused. Status DETERMINISTIC_CONTROLLER_FEEDBACK_GATE0_PASS_PENDING_INDEPENDENT_AUDIT. Gate 0 NOT frozen; Gate 1A NOT begun.

## 2026-08-30 (cjt rc-0.4c) - VERIFIER-GATE AND CONFIGURATION-PREFLIGHT PATCH per the owner's independent RC-0.4A audit: the receipt press stops in the sealed room; accepted configs are sealable before the first tick; fault-only hashes are no longer called seals

- Owner's independent audit of 80d2f70e: paperwork ACCEPTED, but two Gate-0 blockers found in `cas_only_reasoner/recursive_cjt_rc0/` (both under-triaged by my internal 5-lens workflow — its probe had even listed verifier.verify as unguarded; recorded honestly in RC04_BACKLOG.md). Correction-only patch, no new architecture:
  1. VERIFIER FINALIZATION GATE (finding 1): `SealedVerifier` now receives the shared `SealGate`; `verify()` refuses with `FinalizedControllerError` BEFORE issuing a receipt or mutating the seal-bound issuance registry. The rc04b test that had itself exercised the hole (calling verify() post-finalization and only checking registration refusal) is repaired. Owner's exact bypass `run(); verifier.verify(...)` reproduced-then-refused: registry unchanged, seal unchanged, result() still valid.
  2. CONFIGURATION PREFLIGHT (finding 2): `_preflight()` validates the COMPLETE verifier configuration at construction — frozen schemas ((str cause_id, str expert_id) 2-tuple keys naming registered experts, bools rejected in identifier positions; verdict vocabulary intended/opposite/off_axis/unassessed; exact-str payloads) — and PRECOMPUTES gold/expected digests, so every ACCEPTED configuration is sealable before one tick executes; no deferred first-time canonicalization at final sealing. Owner's exact poison (`("unused","^2_attract"): object()` never consulted by the real task) now rejected at construction: zero budget spent, zero commits, zero publications (each test-locked).
  3. FAULT-ONLY HASH RETIRED (finding 3): a final-seal failure now yields the literal marker `UNSEALED_TERMINAL_FAULT` — never a digest, never presented as a trace seal; nothing appended to evidence after the failure; underlying exception preserved separately; publication eligibility prohibited (gate tripped). Reachable only via out-of-API injection now that preflight closes every public path.
  4. FROZEN INVENTORY v2: `RC04_REQUIRED_MUTATIONS_v2.json` = the nine v1 entries verbatim + `verifier_finalization_gate_removed` + `verifier_configuration_preflight_removed` (11 laws, required_count 11, new pinned digest); v1 preserved on disk unchanged, nothing replaced or deleted.
- INTERNAL ADVERSARIAL ROUND 2 (same commit, 3 lenses instructed to reproduce rather than triage): 1 CRITICAL + 3 MAJOR found and FIXED — (a) non-finite/non-numeric branch limits were accepted and reproduced the owner's publish-then-unsealable attack via a different constructor arg → every seal-reaching constructor argument now validated (branch limits require_nonneg_int, episode_id require_str, states keys str + registered experts); (b) an unsealed PUBLISHING run still emitted published=1 through result() → result() now raises the typed ControllerFault for an UNSEALED_TERMINAL_FAULT run, and the scenario runner rejects the marker as a seal (64-hex only, marker==marker never reads as identical replay); (c) _finalize_failed_frame was the one split helper without the finalization guard (mutate-then-refuse) → guarded; (d) runtime_snapshot() now returns detached copies, and the tamper tripwire keys on seal_digest alone so flipping the finalized flag is no longer a kill-switch.
- New suite `tests/test_rc04c.py`: 18 directive-named tests + 7 round-2 locks = 25. Exact numbers: suites 17+28+23+14+30+22+16+25 = 175/175 internal; scenarios 26/26; injections 8/8; mutations 11/11 CAUGHT semantically; manifest v2 law OK; replay identical; both owner attacks and the round-2 CRITICAL reproduced-then-refused. Status DETERMINISTIC_CONTROLLER_FEEDBACK_GATE0_PASS_PENDING_INDEPENDENT_AUDIT. Gate 0 NOT frozen; Gate 1A NOT begun.

## 2026-08-30 (cjt rc-0.4a) - FINALIZATION AND EXACT-SNAPSHOT PATCH per the owner's independent RC-0.4 audit: finalization latch, typed snapshots, sealed fault paths, frozen mutation inventory

- Owner's independent RC-0.4 audit: named defects CLOSED but GATE0_FINALITY_AND_SEAL_INTEGRITY_OPEN — three refuted laws (post-finalization immutability, exact typed runtime snapshot, fail-closed exception sealing) + one major (mutation inventory not frozen). Each closed in `cas_only_reasoner/recursive_cjt_rc0/`, no new architecture:
  1. FINALIZATION IS A REAL STATE: `finalized` latch set at run()'s FINALIZE and seal-bound; `run()`/`tick()`/`_repair()`/`_do_split()`/`_publish_or_refuse()` raise typed `FinalizedControllerError` afterwards without mutating; `result()` returns a DETACHED deep copy (mutating the returned evidence cannot reach engine state or move the seal). The prior backlog classification "direct tick = harmless harness misuse" is REMOVED as ordered.
  2. NO PRE-CANONICALIZATION TYPE ERASURE: the owner reproduced int-tick-1 vs string-tick-"1" reopen schedules sealing identically through str() projections; `reopen_schedule`/`invalidation_events`/`invalidations_consumed`/`repair_dependency_graph` now enter the seal as exact typed structures, and construction validates the typed schemas (nonneg int ticks, registered experts, (expert, prereq) tuples) so lookalike strings are rejected before they exist. rc_canonical.py unchanged (the defect was the engine projection, as the owner ruled).
  3. EVERY FAULT PATH SEALS: theta mode validated in cjt_step BEFORE budget spend (the owner's `theta=("UNKNOWN_MODE",)` escape: budget spent then unsealed ValueError — dead); run() gains a fault boundary that records a typed FAULT event, finalizes, seals ONCE, and re-raises typed `ControllerFault` carrying the seal; fault paths cannot publish; atomic rollback proven (verifier-explosion test: zero COMMITs, zero receipts, versions untouched); the budget RuntimeError catch narrowed to the exact BUDGET_EXHAUSTED signal so other RuntimeErrors reach the boundary.
  4. FROZEN MUTATION INVENTORY: `RC04_REQUIRED_MUTATIONS_v1.json` freezes the 9 mutation names/files/laws/tests; its canonical-content digest is PINNED in the generator; the status law now requires the fresh report to match the manifest EXACTLY — a missing, extra, renamed, or re-targeted mutation → GATE0_REFUTED (the owner's proof: deleting 8 of 9 mutations previously still passed).
- Status renamed per the directive: strongest internal status is now DETERMINISTIC_CONTROLLER_FEEDBACK_GATE0_PASS_PENDING_INDEPENDENT_AUDIT — the name itself carries the pending condition. Records corrected: the stale 110/110 changelog figure (see corrected RC-0.4 entry below), backlog test counts, backlog items 6/7 marked FIXED with the owner's rejection of the "harmless misuse" classification recorded.
- INTERNAL PRE-COMMIT ADVERSARIAL AUDIT (RC-0.4B, folded into this same commit): a 5-lens adversarial workflow (internal review, NO authority, per the owner's standing calibration) attacked the RC-0.4A tree before commit and found TWO CRITICALs — exactly the owner's recurring pattern of a field that exists without governing authority. Both FIXED here, test-locked by `tests/test_rc04b.py` (16 tests):
  - CRITICAL: the `finalized` latch guarded only 5 engine methods; sub-objects (coordinator/publication coordinator/budget) and internal helpers still mutated sealed evidence, and `e.seal_digest = e.seal()` could re-sync a forged seal. FIXED: a shared one-way `SealGate` tripped at finalization makes `coord.commit`/`register_verifier_receipt`/`pubcoord.commit_publication/refuse/abstain`/`budget.spend` and every internal mutator refuse with `FinalizedControllerError`; `result()` is self-verifying (recomputes the live seal, raises `ControllerTampered` on divergence). Honest boundary recorded: this closes engine-METHOD mutation; raw attribute rewrites past the API remain out of the same-process capability boundary.
  - CRITICAL: a non-finite float was legal to store but illegal to seal, so `seal()` threw inside the fault handler and a bare ValueError escaped unsealed after an Effect had published. FIXED at the root (`_deeply_immutable`/`require_deeply_immutable` reject NaN/inf, taus validated) plus belt-and-suspenders `_compute_final_seal()` that never lets a bare encoder exception escape (typed SEAL_FAILED fault → ControllerFault).
  - Also: `frame_full` now binds parent-cause evidence; `invalidations_consumed` anti-stringification lock added; three manifest-law robustness fixes (duplicate-entry / malformed-name / independently-sound `emit_status`). Residuals (KeyboardInterrupt out-of-scope, single-threaded re-entrancy TOCTOU, mutation-battery coverage of the new laws) recorded in RC04_BACKLOG.md.
- New suites `tests/test_rc04a.py` (22, directive-named) + `tests/test_rc04b.py` (16, audit-closure locks). Exact numbers: suites 17+28+23+14+30+22+16 = 150/150 internal; scenarios 26/26; injections 8/8; mutations 9/9 CAUGHT semantically; manifest law OK; replay identical. Gate 1A NOT begun; Gate 0 freezes only on the owner's independent PASS.

## 2026-08-30 (cjt rc-0.4) - FINAL MINIMAL GATE-0 CLOSURE per the owner's independent RC-0.3 audit: diagnostic-commit ELIGIBILITY, load-bearing Effect snapshot, exact-type canonicalization, finalize-then-seal, complete runtime snapshot, hardened mutation-status law

- Owner's independent audit downgraded 846f323f to RC03_DETERMINISTIC_CONTROLLER_PARTIAL_PASS / GATE0_REFUTED with 5 criticals; each closed in `cas_only_reasoner/recursive_cjt_rc0/`, no new architecture:
  1. ELIGIBILITY (critical 1): a DiagnosticCommitReceipt is mintable ONLY via a typed EffectCommitContext whose batch CONTAINS the matching semantic RegionRecord (same producer, receipt, verdict) and whose pre-state equals the Effect's embedded Bias snapshot (LAW_DCR_REQUIRES_SEMANTIC_RECORD / LAW_DCR_PRE_STATE_MISMATCH, fail-closed atomic reject). Memory-only and RPM-only commits can never mint one. The owner's exact bypass sequence is now a mutation-locked test that fails on the unauthorized PUBLICATION itself.
  2. EFFECT SNAPSHOT LOAD-BEARING (critical 2): the engine gate now requires effect.tick == step.tick == t, effect.base_bias_version/digest == step snapshot == captured snapshot, and step.authoritative_bias_version == step.base_state_version; false embedded provenance is STEP_METADATA_REJECTED, and the DCR pre-state must equal the Effect's embedded snapshot.
  3. EXACT-TYPE CANONICAL (critical 3): new `sim/rc_canonical.py` — type-tagged encoding (bytes/enum/tuple/frozenset/dict/record), allow_nan=False, frozenset items sorted by encoded bytes (PYTHONHASHSEED-independent, subprocess-tested at seeds 0/1/42), NO untyped fallback; the owner's reproduced collision digest((b"A",)) == digest(("b'A'",)) is dead and test-locked with a 10-pair lookalike battery. rc0_coordinator's default=str removed too.
  4. FINALIZE-THEN-SEAL (critical 4): _seal_and_halt only REQUESTS halt; run()'s FINALIZE step completes all queue/allocation mutations, sets halted, and computes the seal EXACTLY ONCE; result()["trace_digest"] == engine.seal() recomputed at every return (no-ready, hard-mask, and budget halts each test-locked).
  5. COMPLETE SNAPSHOT (critical 5): queues store FULL Cause envelopes (same-id different-payload/evidence seals differently), and the seal now binds the returned publications evidence, taus, rpm/ohm/commit_verdicts flags, branch limits, CAP/SAT/split constants, the candidate-evidence map, and the verifier's gold-table and expected-payload oracles (digest methods on SealedVerifier).
- Mutation-status law (majors 1-2): the generator DELETES any stale report before the audit, accepts only a fresh report from the CURRENT source+test tree with exit 0; CAUGHT now requires the named test to fail with a SEMANTIC AssertionError (the old dcr-is-None AttributeError mutant was rebuilt as an operational bypass that provably publishes). 9 mutations, 9/9 CAUGHT semantically. A crash can never reuse stale evidence (test-locked with a stubbed crashing runner).
- Receipt metadata: phase renamed RC-0.4; commands + test digests include test_rc03/test_rc04/run_mutation_audit.py; --check-only verified WRITE-FREE (mutation audit reports via stdout; report file digest unchanged through a full check-only run); trust boundary recorded verbatim (same-process API capability discipline, NOT cryptographic/hostile-code isolation); RC02_ATTESTATION gains an append-only RC-0.3 binding (846f323f) with the RC-0.4 SHA honestly UNBOUND until follow-up. RC04_BACKLOG.md freezes the 6 noncritical residuals (per-Cause op contract, same-process boundary, matrix default=str display artifact, no CI, self-reference law, direct-tick misuse).
- Exact numbers: suites 17+28+23+14+30 = 112/112 [CORRECTED 2026-08-30 per the owner's RC-0.4A audit: this line was written as "110/110" before the two internal-audit lock tests were added to test_rc04; the committed RC-0.4 receipt and raw report record 112 and 30/30 — internal results, not an independent reproduction]; scenarios 26/26; injections 8/8; mutations 9/9 semantic; fresh-process replay identical; mutated input changes digest. Programmatic status: DETERMINISTIC_CONTROLLER_FEEDBACK_GATE0_PASS — pending the owner-required independent confirmation (recorded as PENDING inside the receipt itself). Gate 1A NOT begun.

## 2026-08-30 (ops) - PROJECT TRAJECTORY GRAPHIC built into the DSH UI: per-project progress from proposed beginning to intended end, hover details, nested accomplishment dropdowns, detours, original goal always in sight

- New system, three parts, all real and verified this session:
  1. DATA: C:\Users\wakil\DSH-Project-Tracker\projects\*.json - one file per project (id, title, originalGoal, proposedBeginning, intendedEnd, milestones with accomplishments and nested sub-accomplishments, detours with from/to anchors + reason, dated log). Status vocabulary: done / active / open / blocked. Honesty rule baked in: seeds mark done ONLY what this session or the 2026-08-29 CHANGELOG entries evidence; the Noetic Compass master-plan skeleton is deliberately all-open pending owner-verified audit.
  2. SERVER: C:\Users\wakil\DSH-Project-Tracker\project_tracker_server.py on 127.0.0.1:8767 (GET /projects, GET /project/<id> with file-mtime updatedAt, CORS). Auto-starts with the PC via Startup tracker-autostart.vbs mirroring the explainer pattern; start_tracker.cmd has the same guard-and-restart loop.
  3. UI: trajectory widget injected into BOTH index.html copies (served runtime dist + deepseek-harness dev source), the same proven injection pattern as the voice tools. Floating compass button (left side, below the mic button) or Alt+T opens the panel: goal banner with computed percent and dates pinned at top (original goal never scrolls away), SVG trajectory from BEGINNING to INTENDED END with time-proportional milestone nodes (green/amber/gray/red), a green progress frontier, dashed blue detour arcs anchored between milestones, a today marker; hover tooltips on nodes and detours; click a row to expand its accomplishments tree (nested sub-accomplishments with check-state icons); Detours section with why + status; project dropdown switches projects; auto-poll every 25 s while open (re-renders only when the data file changes, preserving scroll and expand state) plus a Refresh button.
- Seeded with 3 projects: DSH Voice Tools (4 milestones, 2 real detours from today's fix work), Machine teaching ladder (5 milestones from the 2026-08-29 CHANGELOG, exact numbers preserved: 440/406/403 tests, 24/24 skills, 9 identities, 22 refutations, 10 audit findings), Noetic Compass master plan (5 milestones incl. the 2027-04-13 patent conversion deadline and the v7.5-v7.7 new-matter detour).
- Verified: server up (pid checked), all 3 project files parse and serve, live GUI page at 127.0.0.1:60205 serves the widget (marker present, voice tools v9 intact), widget JS passes node --check. Page refresh required once to load it.
- SAME DAY, owner feedback fix + AI UPDATER (the requested AI in the progress button):
  - LAYOUT FIX (real defect): milestones sharing a date got identical x positions and their labels printed on top of each other (the teaching-ladder project has four 2026-08-29 milestones). Widget v2: milestone labels placed in three collision-avoided lanes below the line with leader ticks; same-day dots stack vertically instead of hiding each other; if a project's dates are too close to scale (or missing, or a single-milestone project), the bar falls back to even spacing with a printed note - works for projects started before or after the function existed.
  - SWITCHING FIX: project dropdown sorted by data-file updatedAt (most recently worked-on project first, so today's project opens by default); stale-response guard so rapid project switches can never render an older project's data; clicking a dot or detour arc opens and scrolls to its card below.
  - AI UPDATER: project_tracker_server.py now exposes POST /update/<id> and POST /update/all. Each project JSON declares its evidence files; the AI receives the current trajectory + head/tail evidence excerpts and rewrites it under enforced honesty rules (never done without evidence; statuses done/active/open/blocked; original goal preserved; detours need from/to milestone ids + reason; log entries appended). The server validates the reply (status vocabulary, ISO dates, id preservation and dedup, size caps), writes a timestamped backup to backups, and returns a computed diff. Provider chain identical to the explainer: Gemini 3.7 Flash first when Google unblocks, Zhipu glm-4.5-flash now, DeepSeek fallback. Panel header gains AI update (current project) and AI all buttons with a live status line.
  - VERIFIED for real: POST /update/dsh-voice-tools ran 105 s on zhipu-glm-4.5-flash, correctly flipped the Gemini milestone open -> blocked, added today's trajectory-tracker milestone (done, evidenced by the CHANGELOG) and a v10 follow-up (open, NOT claimed done), log 2 -> 4, timestamped backup written. First attempt failed on a 150 s Zhipu timeout from over-large evidence excerpts - fixed by capping excerpts (2.2k head + tail per file, 16k total) and raising the AI timeout to 240 s. All 3 project files parse with evidence arrays; live page serves widget v2 with AI buttons; node --check passes.

## 2026-08-30 (ops) - DSH UI EXPLAINER BUTTON FIXED: helper server was dying on DeepSeek 402 (empty balance); explainer bridge switched to Zhipu glm-4.5-flash with DeepSeek kept as automatic fallback

- Symptom: the bulb "Explain selection" button (Alt+E) in the DSH web GUI did nothing useful. Diagnosis: its helper server `C:\Users\wakil\DSH-Voice-Tools\explainer_server.py` (127.0.0.1:8766) returned HTTP 500 `HTTP Error 402: Payment Required` on every call — the `DEEPSEEK_API_KEY` in `C:\Users\wakil\.cas_llm_keys.env` has no balance. Second, separate defect: explain mode silently required read-aloud mode (Alt+V) to also be switched on, so highlighting with only the bulb lit did nothing.
- Fix 1 (server): provider chain — Zhipu `glm-4.5-flash` (`ZHIPU_API_KEY`, `thinking: disabled`) primary, `deepseek-chat` fallback that revives automatically if the DeepSeek balance is topped up. Note recorded: `glm-5.3-flash` always thinks and burned the entire 1200-token budget on hidden reasoning (finish=length, 1199 reasoning tokens, empty content), so it is not usable for this bridge. All provider errors are now chained into the 500 body for future diagnosis.
- Fix 2 (client): the voice-tools script was patched in BOTH copies — dev source `deepseek-harness/apps/web/index.html` and the served runtime copy `runtime/app/node_modules/@deepseek-ai/dsh-web-frontend/dist/index.html` — so explain mode works without read-aloud. Version bumped to v9 (load toast confirms the new script). A page refresh picks it up.
- Verified (real, this session): two end-to-end `POST /explain` calls returned HTTP 200 with plain-English explanations, each with one example and one metaphor.
- Repo hygiene: `C:\Users\wakil\DSH-Voice-Tools\` is not a git repo; the deepseek-harness checkout is the upstream vendor clone (origin deepseek-ai/deepseek-harness) and its voice-tools patch was already an uncommitted local modification — deliberately left uncommitted rather than pushed to the vendor repo.
- SAME DAY, owner follow-up — explainer primary switched to Gemini 3.7 Flash (owner added `GEMINI_API_KEY` as a Windows user environment variable; copied into the keys file with values never displayed, after a line-merge defect from appending to a file with no trailing newline was caught and repaired — all four key lines verified structurally and the Zhipu call re-verified working):
  - LIVE BLOCKER (real, this session): the Gemini key authenticates and can LIST models (`gemini-3.7-flash` exists in the catalog), but EVERY generation call — native `v1beta/models/gemini-3.7-flash:generateContent` and the OpenAI-compatible `v1beta/openai/chat/completions`, across gemini-3.7-flash / 3.6 / 2.5 — returns 403 PERMISSION_DENIED "Your project has been denied access. Please contact support." This is a project-level denial on Google's side; nothing in the local setup can lift it. Owner path: check billing/project status in Google AI Studio or Cloud Console, or create a NEW key under a NEW project (aistudio.google.com/apikey) and replace the `GEMINI_API_KEY` line.
  - Wired regardless: the explainer provider chain is now [gemini-3.7-flash → zhipu-glm-4.5-flash → deepseek-chat] with the Gemini key loaded from os.environ or the keys file. The moment Google unblocks the project or a fresh key is supplied (then the explainer process is restarted — killing the pythonw on port 8766 makes the auto-restart wrapper reload keys), the SAME button speaks with Gemini 3.7 Flash; today's end-to-end call verified HTTP 200 via the Zhipu fallback with the chain order proven in the running module.

## 2026-08-29 (programming) - CCB-P1: the machine CONSTRUCTS AND DEBUGS; a cardinal sandbox escape and six more findings caught by audit and fixed; 440 tests green

- New board CCB-P1 per PROGRAMMING LESSON.txt: sandbox + tracer + walk-down + minimal repair + typed specs + capability-gated student + the twelve-step compiler-and-test acceptance law. All seven CODE-L0..L4 skills TAUGHT LIVE by Bedrock 32B and promoted (read/trace through debug/repair); the compiler remained unmoved by teacher confidence. Live loop demonstrated: renamed-contract synthesis passes the battery; injected defects are localized to step/line/variable and repaired with single-line patches.
- CONV v0.2 Derived Common Ground: three class constructions taught live (grammar at 36); the Milo conversation derives 'yes' from user premises with the full source chain, DERIVED status, no symmetry/transitivity, never laundered to verified.
- ADVERSARIAL AUDIT (16-agent, six lenses, refuter-verified): 10 CONFIRMED findings, ZERO refuted, 7 cardinal. The crown jewel: a full sandbox escape - a generator frame-walk to the real __import__ via a dunder string literal, which wrote a host file through the whole teach() pipeline. Fixed by refusing all attribute access, dunder names/literals, and yield/lambda. Four cardinal CONV correction defects (dropped negation/prohibition, wildcarded coordination tense, committed questions) fixed by making the correction path reuse the tell path's packet-rendering and tense-derivation. A memorizing lookup table that promoted, and corrections that never superseded class facts, both closed. Two more sandbox gaps (str.format dunder, line-not-work step budget, weaker tracer) hardened. Every finding regression-locked; the whole code chain re-taught under the hardened gate. Disclosed residuals: OS-level memory/CPU isolation and an unpredictable external held-out oracle remain the honest limits of a fully in-process, fully-public-seed examiner.
- Sweep exact: 440 local tests, 0 failures, 18 lanes (CCB-P1 22, D1 61, CORTEX 49).

## 2026-08-29 (full math ladder) - MATH-L0 THROUGH L10 COMPLETE: 24 skills taught live; the machine PROVES theorems and DISCOVERS identities under independent verification

- The remaining six levels built and taught live per the owner's continue-to-L10 directive, each entering only where the checker verifies exactly: L5 functions/slope, L6 exact analytic geometry (trig disclosed out of scope), L7 sequences/derivatives/integrals (derivatives graded against independent re-derivation; integrals differentiate back or refuse), L8 matrices/probability/statistics, L9 formal axioms + proof search over the student's own promoted schemas with an independent examiner walk that rejects false-schema steps, L10 conjecture discovery (enumerate -> attack -> prove -> novelty-check; unproved survivors stay CONJECTURE).
- LIVE L10 RESULT: the machine discovered and proved NINE identities novel to its own library - difference of squares, both binomial squares, (a+b)^2+(a-b)^2=2a^2+2b^2, (a+b)^2-(a-b)^2=4ab - and refuted 22 perturbed candidates with exact witnesses. Scope stated exactly: rediscoveries of known mathematics, novel to the student, every claim independently machine-verified.
- CAS-Math IR extended per the goal: the '/' operator (constant divisors exact; variable divisors typed refusal). Anti-smuggling examiners regression-locked. All Bedrock lessons first-attempt after harness fixes; every harness defect this round was ours and is sealed.
- Sweep exact: 406 local tests, 0 failures, 17 lanes. Math skill store 24/24 promoted; Mathematics Learning Ledger live-checks 24/24 PASS.

## 2026-08-29 (mathematics) - THE MATHEMATICS SCHOOL: all ten MATH-L0..L4 skills taught live and promoted; the language bridge speaks exact arithmetic; 403 tests green

- New board CAS_MATH_LADDER_v0.1 per the owner's MATH LESSONS.txt: all ten goal components (packet schema, prerequisite graph with RPM selection, language bridge, L0-L4 curriculum, twelve-step exact acceptance law, seeded SDG + counterexample attack, protected battery, retention with rollback, Mathematics Learning Ledger, CAS-Ohm learning profiles).
- Bedrock qwen3-32B taught the FULL chain live - quantity grounding, counting, comparison, the four operations, fractions, the distribution rule (a metavariable rewrite verified by canonical equality and applied by unification), and linear equations (solutions verified by substitution into the ORIGINAL equation). Every before-probe CANNOT_MISSING_SKILL, every after-probe SOLVED. The student is capability-gated: the exact engine exists, but only promoted skills may be used.
- The Mathematical Language Bridge: three constructions taught live through the unchanged CCB-L1 ladder (grammar at 33). The machine now answers 'what is three plus four?' with 'three plus four is seven.', handles fraction answers exactly ('x is eleven over two'), refuses honestly when unschooled ('i have not learned addition yet.'), and does it all in the same session as conversation.
- The counterexample generator earned its seat: a false rule dies with an exact witness, and a declared 'common mistake' that is actually true is itself a typed defect. Six teacher-harness defects found live were OURS, fixed and sealed - including the honest reversal that equation lessons need conditional examples with solutions (the teacher was right; our identity-only contract was wrong).
- Sweep exact: 403 local tests, 0 failures, 17 lanes (new: MATH-LADDER 15; CORTEX 49).

## 2026-08-29 (CONV v0.1) - THE MACHINE CONVERSES: provenance-grounded dialogue complete, adversarially audited (10 confirmed findings, all fixed and regression-locked)

- New board CCB-D1 (Dialogue and Common-Ground) under the owner's frozen acceptance law: acknowledge only AFTER atomic commit; answer only with the source preserved ('based on what you told me' vs 'the verified record says'); never launder user assertions into verified knowledge (an intent claiming VERIFIED is refused typed); honest unknown otherwise. Three stores never collapse: verified knowledge / session assertions (truth GIVEN, source USER_ASSERTED) / dialogue state.
- The whole goal sequence shipped: tell-then-ask; corrections that supersede never delete; unmarked contradictions that ask; retraction that keeps its own audit trail; wh-questions (what/who) TAUGHT LIVE via Bedrock through the unchanged ladder (grammar at 30 durable constructions) with multi-binding listing; social dialogue acts that write no facts; entity summaries grouped by provenance. CAS-Ohm test points make language failure vs memory-write failure distinguishable on every sealed turn. Owner terminal: CCB_D1_v0.1/chat.py.
- ADVERSARIAL AUDIT (16-agent workflow, six hostile lenses, refuter-verified): 10 findings CONFIRMED - three cardinal (a ghost-commit crash path via stale confirmations; wrapper-masked contradictions whose answers flipped with insertion order; the same crash from the state lens) and seven major (contested records invisible to retraction/summary, immortal pending clarifications, untyped store-fault crashes on two lanes, conflict-blind restricted questions, masqueraded no-target corrections, coordination tense wildcarding, bad -y inflection). ALL fixed by root cause, each locked by a named regression test. Disclosed open limits recorded in the spec sheet.
- Sweep exact: 387 local tests, 0 failures, 16 lanes (new: D1 49). The Learning Ledger now regenerates a live 11-turn conversation transcript on every run.

## 2026-08-28 (curriculum waves B+C) - THE 20-LESSON GOAL QUEUE IS COMPLETE: all 20 durable, grammar at 28 constructions, first live two-model committee, two more defect classes caught and fixed

- Lessons 7-17 all PROMOTED_DURABLY first attempt: cross-sentence pronouns (resolve unique antecedent / name the ambiguity / refuse with no antecedent - certainty never invented), three-clause coordination, or-disjunction (and/or projections distinct), relative clauses, possessives (NPOSS), locatives, comparatives, quantifiers (every/some/no = three distinct meanings, tested), temporal adverbs, why-questions (honest LANGUAGE_UNDERSTOOD_KNOWLEDGE_MISSING - no cause facts), commands with recipients.
- Lessons 18-19 (pure vocabulary, new flow): the examiner is generalization through EXISTING constructions. 'carry' exposed a real defect - the productive -s rule had invented lemma 'carrie' and the runtime committed it; the lesson corrected the analysis and the rule now requires a KNOWN base (unknown verbs refuse honestly). small/large: clean unsupported -> understood.
- Lesson 20: FIRST LIVE MULTI-TEACHER COMMITTEE - proposer qwen3-32B + critic deepseek.v3 (distinct family) with explicit recorded votes; the board validates committee composition and any reject vote blocks typed (3 new tests); the ladder stayed the final examiner. Content: 'must not' prohibition modality, distinct from 'does not' negation and plain assertion (tested).
- SEALED-OUTPUT OVERWRITE BUG found by the ledger's own artifact count: fixed-filename outputs meant each run clobbered the previous sealed episode file. Store history keeps all promotion evidence; lost elicitation transcripts reconstructed and LABELED as reconstruction; per-run filenames now prevent recurrence.
- Machinery: PRON/NPOSS/QUANT/ADV slots, router discourse state, restricted-question per-conjunct kernel verification, projection survival for relative/possession/location/comparison/quantifier/time/prohibition (the never-drop law), behavioral_norms high-impact domain, committee validation, conservative productive morphology.
- Sweep exact: RRK 34 + RLP 45 + M1 34 + L1 32 + SEM 19 + WB 13 + CRQS 35 + T1 20 + OHM 10 + H2H 10 + LTG 11 + SM 8 + G10 8 + CORTEX 48 + A1 11 = 338 local, 0 failures. Canary: 28 family probes.

## 2026-08-28 (curriculum wave A) - goal lessons 1-6 ALL DURABLE via Bedrock 32B; grammar at 16 constructions; three harness defects found live and fixed

- The 20-lesson goal queue is underway. Lessons 1-6 all PROMOTED_DURABLY, one sealed episode each (rejections sealed too): plural subjects (NEW plural agreement law - 'the cat chase the dog.' refuses to parse; plurality survives projection under the polarity never-drop law), past-tense negation, copular adjective questions ('is the gray cat quiet?' -> 'yes, the gray cat is quiet.' with EVERY conjunct kernel-verified before yes), passive negation, past ditransitives (irregular 'gave' taught through the lesson morphology field), and ditransitive questions (honest 'i do not know' on the 4-arg fact the kernel lacks).
- Three harness defects found live, all one genus - the examiner lagging the machine's own accumulated knowledge: the student lexicon missed runtime-promoted words ('bone' broke a regression guard falsely), the field-check morphology missed persisted verb forms ('give' flagged unknown), and defect feedback blamed function words for shape mismatches. All fixed; the ladder's authority unchanged.
- One genuine teacher error caught and corrected by the ladder: surface plural 'cats' written as the agent value instead of the lemma 'cat' - REJECTED_POSITIVE_EXAMPLES, hint sharpened, clean pass after.
- Machinery this wave: NPPL plural slot (+-es plurals), number/modifier projection survival, restricted-question per-conjunct verification, disjunction frame type (for lesson 9), third-clause roles (for lesson 8), targets-file loader. Runtime canary extended to 15 probes covering all 16 construction families.
- Suites: L1 32 + CORTEX 45 + A1 8 green (program totals unchanged at 332 local).

## 2026-08-28 (curriculum round 2) - recipients, adjectives, past questions ALL DURABLE; grammar at 10 constructions; a forgetting bug caught and canaried

- AWS Bedrock 32B taught three more constructions through the unchanged ladder, all PROMOTED_DURABLY: past-tense questions ('did the cat chase the dog?' now ANSWERED), ditransitives with recipients ('the cat gives the bone to the dog.' - the recipient role survives projection; 'bone' entered the runtime lexicon via LEX persistence), and attributive adjectives ('the gray cat chases the brown dog.' - new ADJ slot type; modifiers project as conjoined property assertions, nothing dropped). Grammar: 10 durable constructions (3 seed + 7 live-taught).
- FORGETTING BUG caught before teaching: the round-1 save path wrote raw teacher morph entries over the merged table - on disk 'chased' lost its past reading and the runtime FORGOT active-past while all suites stayed green. Repaired, both save paths fixed to dump the MERGED table, and a runtime CANARY test now probes one sentence per construction family so silent knowledge loss trips CI.
- One test OUTGROWN by learning, updated honestly: the adjective-drop faithfulness case now parses natively, so the cortex-lane test moved to a single-adjective shape outside the native grammar. Elicitation feedback now names unknown words exactly (the 32B burned four retries on 'quick' before this).
- Lane sweep, exact: RRK 34 + RLP 45 + M1 34 + L1 32 + SEM 19 + WB 13 + CRQS 35 + T1 20 + OHM 10 + H2H 10 + LTG 11 + SM 8 + G10 8 + CORTEX 45 + A1 8 = 332 local tests, 0 failures.

## 2026-08-28 (AWS teacher round) - all three lessons DURABLE via Bedrock; the grammar reaches 7 constructions; the ladder caught morphology clobbering

- Per the owner's AWS-first order: the 20B-class teacher escalation used AWS Bedrock (qwen.qwen3-32b-v1:0, us-west-2, pay-per-token; the EC2 quota door was unnecessary). The curriculum harness gained a bedrock backend (CAS_TEACHER_BACKEND=bedrock) - same fields, same validators, same examiner.
- RESULT: questions, commands, coordination ALL PROMOTED_DURABLY - the 32B passed nearly every field on attempt 1 where the local 3B failed entirely (the sealed 3B ceiling stands as the contrast). The runtime grammar now holds 7 durable constructions: 3 seed + 4 live-model-taught. Standout transcript: 'the cat chases the dog and the dog chases the cat.' went from the CAS-Ohm overload split (NEEDS_DECOMPOSITION) to a single native parse keeping BOTH clauses - learning raised capacity exactly as the control doctrine predicts. Questions answer honestly: 'i do not know whether the cat chases the dog.' (language understood, knowledge missing).
- The acceptance law caught two real defects mid-round, both fixed with regression tests: (1) morphology clobbering - the student's MorphTable silently overwrote 'chased'=past with 'chased'=participle, breaking prior grammar; REJECTED_REGRESSION exposed it; teach() now merges, no-ops, or refuses typed; (2) the legacy decoder mangled relation-question English over a correct kernel verdict; the router renders from the frame now.
- The plain-English button is now MECHANICAL per the owner's correction (no UI toggle exists): a UserPromptSubmit hook in .claude/settings.json injects the reminder into context on every prompt. Suites: CCB-L1 32, CORTEX 44, CCB-A1 8, all green.

## 2026-08-28 (curriculum round) - three lessons attempted; the 3B teacher's ceiling found and sealed; plain-English button + compute ladder now standing orders

- Machinery extended for the new lesson types (all suites green): present_3sg verb matching; coordination frames (two events joined, recursive semantics realization); learned question constructions answer through the kernel or return the doctrine's honest LANGUAGE_UNDERSTOOD_KNOWLEDGE_MISSING; coordination projects with both clauses preserved.
- Curriculum round 1 (questions, commands, coordination) - HONEST RESULT: 0/3 promoted. The 3B teacher writes verbs literally instead of as slots, copies placeholders verbatim, and repeats an identical wrong answer after receiving the exact fix four times; seeded-sampling retries did not help. All elicitation logs sealed. This is the teacher-capability boundary, not a ladder failure - the same pipeline promoted negation durably earlier today. Escalation queued per the standing owner authorization: 20B-class teacher on RunPod/AWS (harness-lane record: EC2 G/VT quota was 0.0 - RunPod likely faster); the harness is teacher-agnostic.
- Standing orders written into CLAUDE.md: PLAIN ENGLISH permanent for every output (owner caught repeated drift), and the compute escalation ladder (never CPU; 4070 to ~3B; 20B+ on cloud). Memory records added.
- The machine's knowledge is UNCHANGED this round: 4 durable constructions (3 seed + 1 live-taught negation), and that is exactly what the Learning Ledger shows - it cannot be inflated by attempts.

## 2026-08-28 (learning round) - THE MACHINE LEARNED FROM A LIVE MODEL TEACHER; the Learning Ledger makes it visible

- SCHEMA-CONSTRAINED TEACHING (constrained_teacher.py): field-wise elicitation - one small validated question per field, three typed-feedback attempts each - so packet syntax cannot fail while content stays the teacher's. The 3B corrected its pattern under feedback (VERB:name:base -> VERB:pred:base), authored valid examples/pairs/counterexamples after the counterexample concept was clarified, and its lesson PASSED: full ten-stage ladder with the protected held-out channel -> PROMOTED_PROVISIONALLY -> delayed retention -> PROMOTED_DURABLY -> saved into the runtime grammar store. Disclosed scaffold: the fully-determined semantics field was derived mechanically after the teacher garbled @-syntax 3x (provenance derived_from_teacher_pattern_by_schema_scaffold); every elicitation attempt logged.
- CLEAR LEARNING INDICATORS (owner demand): BEFORE 'the cat does not chase the dog.' -> UNSUPPORTED_LANGUAGE; AFTER -> UNDERSTOOD via native_gram with the correct core; unseen role-swapped negations parse correctly. THE LEARNING LEDGER (learning_ledger.py -> LEARNING_LEDGER.md) derives everything from the stores: 4 durable constructions (3 hand-authored seed + 1 LIVE-MODEL-TAUGHT), 10 words, 2 verb forms, full provenance per rule, every lesson attempt (incl. all rejections) sealed.
- LEDGER-ROUND FIX: reading the ledger's own output exposed that the router's frame projection DROPPED POLARITY (negative == positive downstream - the silently-dropped-content fabrication genus, this time caught internally before any battery). Negative frames now wrap in the legacy negation packet; regression test added. CORTEX 43 + CCB-L1 31 + CCB-A1 8 green.

## 2026-08-28 (live-teacher round) - both teachers examined on GPU; the acceptance law held; feedback integration separates the scales

- Session-restart recovery: the CPU teacher run orphaned by the restart became the standing NEVER-CPU order (memory + enforced in the harness: live_teacher.py refuses CPU). The RTX 4070 + a separate CUDA venv (torch 2.11 cu128) now serve inference: 28-60s per teacher lesson vs 30+ minutes orphaned on CPU. The 3B snapshot's broken partial download (0-byte shard, missing tokenizer) was detected, wiped, and cleanly re-fetched.
- FIRST LIVE TEACHER LESSONS sealed: both Qwen2.5-1.5B and Qwen2.5-3B authored the IDENTICAL malformed slot ('VERB:base') on attempt 1 -> REJECTED_SCHEMA at rung two. Socratic retry (typed defects returned once, examiner unchanged): the 1.5B repeated byte-identically; the 3B repaired the named defect and made a new smaller error ('@VERB:pred') -> still rejected. No defective lesson touched the grammar store; every attempt is a sealed TeachingEpisode. Contributing cause recorded honestly: the teaching prompt's own shorthand seeded the shared mistake - teaching materials are part of the system under test.
- The apprenticeship's first live conclusion: the acceptance ladder is passable (seed lessons promoted durably through it) but neither cached teacher can yet author a schema-valid lesson packet; feedback integration - not first-attempt quality - is where 3B beats 1.5B. Next: stricter lesson-format spec, schema-constrained decoding, or a stronger teacher.

## 2026-08-28 (teaching-architecture round) - the faculty doctrine adopted; CCB-A1 built; never-CPU rule standing

- CAS Teaching Architecture v0.1 adopted (owner directive): fourteen teachable domains, five transfer channels, seven teacher roles as a faculty committee, teaching metrics, the never-autonomous list, the seven-stage order, and the learning-to-learn endgame. The directive's "CCB-T1" label collides with the existing tool board; the teaching board is CCB-A1.
- CCB-A1 built (CAS_APPRENTICE_v0.1, 8 tests green): TeachingEpisode sealing for every outcome; the never-autonomous guard (nine constitutional targets refuse promotion typed, refusals sealed); the faculty-committee rule (high-impact domains reject single-examiner lessons); the stricter world-knowledge protocol (PROPOSED never VERIFIED from a model alone; trusted-source attestation; CONTESTED on mixed evidence; changing facts need current retrieval + validity window; hard boundaries never enter through teaching); teaching metrics.
- OPERATIONAL RULE (owner order, recorded in memory): NEVER CPU for model inference - the first live teacher lesson (1.5B float32 CPU, 30+ min) was orphaned by a session restart. The machine has an RTX 4070 (8GB); a separate CUDA venv was built (main Python untouched); the GPU rerun of the live teacher lesson is the pending artifact. RunPod/AWS credentials confirmed local for anything bigger.

## 2026-08-28 (apprenticeship round) - learnable grammar under the acceptance law; the student outgrows its teacher on taught constructions

- Verified Cognitive Apprenticeship adopted (owner directive): foreign proposals permitted, foreign commitments prohibited; the model is a temporary master teacher; English learned as composable constructions, never sentence templates. Teacher models downloaded with owner approval: Qwen2.5-1.5B (2.9G) + Qwen2.5-3B (4.1G) cached locally.
- CCB-L1 GRAM built (Phase L1+L2): construction schema with typed slots and declarative semantic transformations; frames split truth-conditional CORE from SURFACE voice (the minimal-pair law lives on that split); learnable MorphTable; ambiguity-reporting parser; versioned tamper-refusing GrammarStore; LanguageLessonPacket + the TEN-STAGE acceptance ladder ending in PROMOTED_DURABLY via delayed retention - with the protected held-out channel REQUIRED (no channel, no promotion: the teacher may not examine its own lesson) and teacher confidence informational only (a 0.99-confidence wrong lesson dies identically, tested). 13 new tests; CCB-L1 31 green.
- Seed grammar generated THROUGH the ladder, never hand-inserted: active_past_transitive + passive_past + passive_present all PROMOTED_DURABLY (sealed 703721eb81dfe853, full episode evidence trail); learned morphology travels with the grammar (the live "chas" mis-lemmatization found and fixed by that rule).
- Router Phase L5/L6: the native_gram lane parses taught constructions natively with coverage counters as the teacher-dependence decay metric. PAYOFF DEMONSTRATED: "the dog is chased by the cat." - the sentence the 0.5B cortex read backwards live - now parses natively with CORRECT roles and the cortex is never invoked (Bomb-cortex test). ONE passive rule covers noun pairs never seen in any lesson. Battery v4 sealed 08c55cc9206abff0: paraphrase_statement fabrication -> 0; held-out steady 78.12/12.50.
- Program: CCB-L1 31 + CAS_CORTEX 42 green; lane-wide 320 local + cas-rr 43 = 363, all green. Open: live teacher lesson generation, SDG curriculum, shadow harness, the 0.5B/1.5B/3B scale study (unblocked).

## 2026-08-28 (CAS-Ohm control round) - the attention plane goes ACTIVE: overload control live, permanent tests T1-T8, battery v3 at 12.5 pct fabrication

- CAS-Ohm Native Attention Control Protocol v0.1 adopted (owner directive): from meter to the Attention Engineering and Load-Control Plane - MEASURE/DESIGN/DIAGNOSE/RECURSE, active before/during/after reasoning; readiness packets certify ENERGIZATION never truth; flow region and semantic outcome remain independent axes by law.
- Implemented and wired (cortex/ohm_control.py, 42 CAS_CORTEX tests green): versioned CASOhmBoardProfile with calibration digest; the three active equations; I_Q quantization (Q1-Q4, decimals, trend arrows); LIVE lambda overload control in the router (clause-connector demand vs one-proposition capacity; lambda > 1 -> typed NEEDS_DECOMPOSITION BEFORE the cortex runs); branch allocation with fairness floor; parallel_health child probes (T5 - healthy aggregates never hide failing children); learning-as-resistance-reduction records (T6); CAS-GEM retrieval decisions (T7 - similar flows ask for a clue and never merge; flow never overrides an anchor); the two-axis diagnosis matrix (T8 - active+off-axis repairs semantics, never gain); CASOhmReadiness commitment packets (T4 - a starved verifier blocks commitment).
- BATTERY v3 (sealed b161391a9d9c819f): held-out pass 78.12 pct (from 68.75), fabrication 12.50 pct (from 28.12 in v1, 15.62 in v2), multi_clause 6/6 via split-before-clipping, median latency 2.74s (overload refusals skip inference). Disclosed: v2 had under-credited passes (CONTENT_MISMATCH refusals scored as misses); new recorded limit: indirect-question "if" false-triggers the split (safe over-refusal, 2 paraphrase passes -> honest misses, refinement queued).
- Program: CAS_CORTEX 42 green; lane-wide 307 local + cas-rr 43 = 350, all green.

## 2026-08-28 (Phase 4.3) - battery halves fabrication, replication bundle self-tested, CAS-Ohm attention plane goes native

- PHASE4_BATTERY_v1: 86 deterministic gold-labeled items, 13 categories, content-hash splits, fabrication-is-the-cardinal-sin grading. First run CRASHED the router live (unresolved pronoun raised DiscourseError through the native lane) - fixed typed with a regression. v1 sealed 03ffeb853752322c: held-out pass 68.75%, fabrication 28.12%, every fabrication the same genus (grounded packet silently dropping content or inventing a referent). CONTENT-FAITHFULNESS GATE designed from dev/calibration evidence only (split discipline checked first): R1 no dropped known content, R2 entities must be attested (synonym verbs/properties stay free; feline->cat entity inference correctly refused - new entities come from CCB-L1 acquisition, not cortex guessing). v2 sealed 4a6c21f064272bf7: held-out fabrication HALVED to 15.62%, honest misses up 1->5 (the intended trade), injection 6/6 and unknown-word 10/10 perfect in both runs, determinism TRUE, latency median 4.6s/gen. H2H-v0 smoke stays sealed; recorded limits: verb/property-slot typos, pure tense drops, role reversals.
- REPLICATION_v0.1: the one-command external replication bundle (claim-by-claim form with 16 claims, attestation with conflicts-of-interest, locked expected results incl. the withdrawn-claim records verbatim). Self-test GREEN: 14/14 suites match, qualification derives to exactly CAS-G9 / E5 / A0, both deterministic digests reproduce (bd4a444406b0833c, 94dcd861a43af7d2). Three self-test bugs found and fixed (junit-XML counting, last-match qualification, fact-echo-guard digest drift). The self-run is NOT a replication - it proves the bundle works; E6 still requires an external evaluator.
- CAS-OHM ATTENTION INTEGRATION PROTOCOL v0.1 adopted (owner directive): CAS-Ohm governs FLOW, never truth - R10 narrows to truth/validity/meaning/commitment/permission; three substrates with declared bridges; scheduler allocation with fairness floors; the 15-section protocol persisted. Native v0.1 slice IMPLEMENTED: cortex/attention.py authors CASOhmStageRecords (V_drive, R decomposition, I_pred/I_obs/delta_I, operating region) onto every TurnTrace, COMPUTE-ONLY by test; Experiment A/B slices green (ungrounded word -> R_lexical 8.0, I_obs << I_pred, cutoff; passive role error -> healthy flow + wrong effect = semantic misalignment, disclaimed in-record). Experiments C-F + neural calibration mode open per the protocol's own admission gates.
- CAS-Native simplex located per owner order (embedding/simplex encoders, Fisher-Rao loss, lacunarity gate, geodesic memory) - the natural CAS-GEM capsule-embedding substrate; Codex's ccb-r1-stage5-integration worktree already carries copies (their lane, untouched).
- CAS_CORTEX suite 28 green; program-wide 293 local + cas-rr 43 = 336, all green.

## 2026-08-28 (Phase 4 kickoff) - hybrid cortex wired under the frozen authority contract; CAS-GEM doctrine adopted; CAS-SDG and CAS compiler located

- OWNER RATIFICATIONS RECORDED: the falsification round endorsed as the system working; external-facing wording adopted verbatim (internally held-out validated, no independent external replication, no autonomous deployment authority); Phase 4 GO under the hybrid contract. Baseline FROZEN at 2526360b; work on branch phase4-hybrid-cortex.
- CAS_CORTEX_v0.1 (Phase 4.1+4.2): resident snapshot-pinned Qwen2.5-0.5B adapter with a full model identity receipt (weights fdf756fa7fcbe740; evidence binds to digests, never a cache path); the frozen authority contract EXECUTABLE (eight forbidden intent classes raise typed before state; smuggled effect fields, impersonated provenance, concealed raw output all fail closed); native-first router with three modes (NATIVE_ONLY / CORTEX_DIAGNOSTIC / HYBRID_COMMIT), typed no-answers, sealed TurnTraces. 19 harness tests green.
- LIVE GATES (sealed 9a6c22282bab0d33): Gate 3 semantic equivalence 2/2 (English -> cortex -> packet -> kernel == direct gold packet -> kernel). Gate 4 FAILED FIRST, live: the cortex fabricated well-formed packets around invented words (property(glimmerfor, gray) committed as UNDERSTOOD) - exactly the H2H-predicted failure; CLOSED by the LEXICAL GROUNDING GATE (every cortex atom checked against the learned vocabulary; UNGROUNDED_TERM, nothing committed; the cortex self-report is never trusted alone). Gate 5: role-reversal diverges correctly AND the passive-voice paraphrase failed live at the 0.5B floor (role error relation(chase, dog, cat)) - surfaced and recorded as a cortex-quality limit grounding cannot catch. Gate 8: scrambled packets and the direct-output bypass both rejected.
- CAS-GEM doctrine adopted (cas_only_reasoner/CAS_GEM_DOCTRINE_v0.1.md): reconstructive episodic memory with evidence-labeled reconstruction, anti-confabulation invariants, three-tier storage, seven SDG curriculum levels and seven build gates - sequenced AFTER Phase 4. Owner-ordered searches COMPLETED: the CAS-SDG exists at cas-synthetic/ (twelve generators; Path D Wave 2.5 = 5,268 SFE-certified records) plus docs/working/level3_conversational_sdg_spec.md and gate4_next_board SDG batches; the CAS COMPILER is local at noetic-compass-scaffold/noetic-compass/api/notation/ (compiler, parser, cli, renderer, inversion, turn_admissibility + the proven rpm_compiler_loop_demo.py, commit 81147091) - a concrete integration target for the manifest's "compiler: not integrated".
- Derivability-gate scope expansion (all knowledge entry points) recorded as the first requirement on the D10 path. Phase 4.3 next: expanded held-out battery with protected splits, external replication bundle for E6, CONV qualification, latency work.

## 2026-08-28 (G10 audit round) — the standard held: D10 and E6 REFUTED, honestly given back; machinery NOT REFUTED; every hole closed same-day

- 3-agent adversarial audit of the G10 round. D10 novel-research floor: REFUTED — the discovery flagship x*(y+1)=x*y+x was a disguised input (both sides hand-authored into the search space; the distributive law TAUGHT to the machine as fixture dist_identity + the executable 'distribute' axiom, which the novelty gate never read); CRQS section 4 reserves the floor for research WITH NO KNOWN ANSWER; same genus as the refuted G8 v1. E6: REFUTED — self-commissioned same-session AI auditors are inside the developing party's boundary; the records' own caveat named the unmet requirement; honest tier E5 with the audits as strong supporting evidence. The integration machinery: NOT REFUTED (real process boundaries, zero mocks, self-model downgrade verified by breaking a probe, twelve-board count verified, determinism across six fresh processes) with one boundary recorded: goal completion proves against caller-offered facts.
- Same-day closures, each with a test: discovery.py -> verified identity search v0.2 (false 'generic space' wording replaced with the disclosed truth; one-step taught-axiom derivability gate added — the planted pair is now CAUGHT, theorems 5 -> 2; honesty line says NOT novel research verbatim); grading.py -> D8 with the WITHDRAWN_FLOOR_RECORD in the caveat; evidence.py E6 bar raised (external evaluator outside the developing party's session + claim linkage + artifact, all required; the CNCM's records carry external:false and stay E5); LTG fact-echo guard (no-rules proofs refused by default, allow_direct_fact disclosed in the record; the g_discover leg uses the disclosed path); CNCM_G10 spec written.
- HONEST QUALIFICATION: CAS-G9 / E5 / A0 — design ceiling CAS-G10 (the machinery through G10 is real and audited), demonstrated CAS-G9 stable D9, next target CAS-G10 with the true gap derived by the report itself: a STABLE D10 demonstration under section 4's own reading (genuine research with no known answer) and E6 via genuinely external replication. The G10 level was held for four hours and given back when the audit landed — the standard doing its job.
- Whole program now: kernel 34 + RLP 45 + CCB-M1 34 + CCB-L1 18 + CAS-Sem 19 + workbench 13 + CRQS 35 + CCB-T1 20 + OHM-panel 10 + H2H 10 + LTG 11 + SM 8 + CNCM-G10 8 + cas-rr 43 = 308 tests, all green.

## 2026-08-28 (G10 round) — CAS-G10: the Integrated Cognitive System gate, with every load-bearing claim disclosed

- CAS-SM v0.1 (Self-Model board): capability claims DERIVED from live probes on the real boards + artifact paths — can(x) answers CAN/CANNOT/UNKNOWN typed, a failing probe downgrades the claim, limits are first-class, cannot_list() = [coding, vision], "the self-model does not bluff." 8 tests green.
- CNCM-G10 v0.1 (suite_CAS-G10): the multi-domain long-horizon episode — one persistent goal store, three episodes with REAL process boundaries, seven domains on the real boards (language, self-model routing incl. an honest CANNOT, long-term goals kernel-blocked and resumed, tools + exact math with kernel-earned completion naming its rules, strategy-driven learning, discovery completing on sealed evidence). Completion never fabricated (the unproven case refused typed); pipeline twice = digest-identical (STABLE D10). The D10 grade is DISCLOSED, not asserted: DI band D8 on the nine axes; the novel-research floor lifts it to D10 via the discovery leg with the caveat verbatim (novel to this machine, trivial to human mathematics, exhaustive search at v0.1 scale). 8 tests green.
- CRQS E6 path: >= 2 independent replication records each with evaluator + reproduced + artifact (missing any one of the three does not count — tested); evaluator identity and the caveat (AI evaluators, same codebase, same day; human/organizational replication OPEN) disclosed in the section-10 report. CAS-GΩ guarded as a research designation. CRQS 35 green.
- QUALIFICATION (pre-audit): the assembled CNCM (twelve boards) qualifies CAS-G10 / E6 / A0 — ceiling CAS-G10, demonstrated CAS-G10 stable D10 (grading disclosed), evidence E6 on the G8/G9 independent audit records. Next: CAS-GΩ, a research designation with no gate to clear. RMB NOT RUN. The adversarial audit of this round is queued; the D10 novel-research floor and the E6 basis are the exposed claims and will be recorded either way.
- Whole program now: kernel 34 + RLP 45 + CCB-M1 34 + CCB-L1 18 + CAS-Sem 19 + workbench 13 + CRQS 35 + CCB-T1 20 + OHM-panel 10 + H2H 10 + LTG 10 + SM 8 + CNCM-G10 8 + cas-rr 43 = 307 tests, all green.

## 2026-08-28 (head-to-head + G10-build round 1) — Route A vs Route B settled empirically; discovery, long-term goals

- OWNER-ORDERED CORTEX HEAD-TO-HEAD (CORTEX_H2H_v0.1, sealed at output/h2h_results.json digest db34d2e9d0214df4): Route A (native CCB-L1, no neural weights) vs Route B (Qwen/Qwen2.5-0.5B-Instruct from the LOCAL cache, offline, CPU, greedy — the floor of the doctrine's 1-3B band; TEST-ONLY, nothing enters production). 20 scored items, each run twice, the nine RMB identical conditions attested one by one, one grader, the same kernel judging both routes' packets, few-shot prompt disjoint from every scored item. RESULT per dimension: in-fragment parse A 100% / B 100%; QA through the kernel A 100% / B 25% (B mislabels questions as negation packets); unknown-word honesty A 100% / B 25% (B FABRICATES packets around unknown words 3 of 4 times — fluent error is still error); breadth A 0% (typed refusals) / B 73% mean slot accuracy (real give/eat/visit/believe/praise English the native board cannot touch); both deterministic; A 0.0s vs B 327.8s. READING: neither route wins alone — the result empirically ratifies the HYBRID (cortex proposes breadth, CAS holds the commitment and honesty boundary), exactly the doctrine's architecture. 10 LM-free harness tests green.
- CCB-M1 discovery v0.1: the machine generates, tests, and PROVES identities it was never given — 68-expression generic space, 1309 conjectures, ~1272 falsified with exact witnesses, 5 novel theorems including x*(y+1) = x*y + x, proved by the trusted canonical checker; the novelty gate is variable-name-blind (alpha-normalized canonicals: the fixture's (a+b)-square blocks its (x+y) rediscovery); deterministic; the honesty line travels in the packet (novel to this machine, trivial to human mathematics, discovery-by-exhaustive-search at v0.1 scale). 7 tests; CCB-M1 34 green.
- CAS-LTG v0.1 (Long-Term Goals board): typed transition graph with terminal states, logical episode clock, provenance-bearing progress and history, digest-checked JSON persistence across a REAL process boundary, tampered files refused, and completion EARNED through the unchanged kernel (UNSUPPORTED conditions refuse completion with a typed error). 10 tests green.
- Whole program now: kernel 34 + RLP 45 + CCB-M1 34 + CCB-L1 18 + CAS-Sem 19 + workbench 13 + CRQS 33 + CCB-T1 20 + OHM-panel 10 + H2H 10 + LTG 10 + cas-rr 43 = 289 tests, all green. G10 build continues: self-model board, the multi-domain long-horizon integration suite, the E6 evidence path.

## 2026-08-28 (G9 re-audit round) — G9 independently NOT REFUTED under the standard that killed G8 v1; four weaknesses closed with regressions

- Independent 2-agent adversarial re-audit of the G9 claim and the trajectory STATUS LEDGER: NOT REFUTED on both fronts. Decisive probe: the auditor authored a brand-new lt-winning fault class from scratch (different entities, magnitudes, predicate) and the SelfImprover loop synthesized [lt,eq,gt] — not the fixture-run's [gt,eq,lt] — proving synthesis causally tracks the machine's own sealed evidence (the exact standard G8 v1 failed). Forged-packet ablations: eq-promoted -> [eq,gt,lt], no-promotion -> None. A mismatched held-out yields honest REJECTED with memory unwritten. Stability verified cross-process. Ledger audit: every phase status supported at exactly the claimed strength; all suite counts exact; sever-the-cortex literally true (zero neural/LLM imports or API endpoints anywhere in the lane). One auditor claim was itself WRONG and is corrected on the record: CCB_T1_v0.1 and CAS_OHM_INSTRUMENT_v0.1 were called untracked; both are committed at 650765dd (verified via git ls-files).
- Closed from the audit, each with a regression test (RLP 41 -> 45): fault class now READ from the sealed diagnosis in the exploration packet (was hardcoded at the promote site; diagnosed_faults now sealed into every cycle packet); the versioned and rollback_preserved validation checks now COMPUTED on the real memory machinery (were hardcoded True); the judge digest now covers the ENFORCED R3_PROTECTED constant (declared-list-only hashing was decorative, though fail-safe); diagnosis is tamper-evident (re-seals the packet, refuses mismatches with a typed error). Ledger under-credits fixed: CCB-T1 (20 tests) and the OHM panel (10 tests) got their own rows.
- Recorded caveats on CAS-G9 (spec sheet): one fault class; a 3-guard permutation space (the improvement is exhaustive sandbox search memoized into an ordering); r1_bigger_held_out participates in the promote gate while r1_heavier_structural stays purely evaluative; held-out means hidden from the machine's loop, not from developers; the CRQS engine's E5 gating is permissive — the G9 grade is not inflated by it, but the standard should tighten it (future CRQS work).
- Whole program now: kernel 34 + RLP 45 + CCB-M1 27 + CCB-L1 18 + CAS-Sem 19 + workbench 13 + CRQS 33 + CCB-T1 20 + OHM-panel 10 + cas-rr 43 = 262 tests, all green. Qualification unchanged and now doubly audited: CAS-G9 / E5 / A0.

## 2026-08-28 (trajectory round) — CAS Complete Machine Trajectory Plan v0.1 adopted as the master build plan

- Persisted the owner's ten-phase trajectory (cas_only_reasoner/CAS_MACHINE_TRAJECTORY_v0.1.md): authority freeze -> kernel -> semantics -> reasoning -> memory/RPM/verifier -> language -> governed learning -> controlled evolution -> Foundry -> capability bands; the three ordering rules (trace on day one; verification before broad language; evolution last); the seven decisive experiments; the 20-step integrated v1 episode; CAS-Ohm's instrumentation-only trajectory.
- STATUS LEDGER appended against this lane at commit 0363b69a, every claim with an artifact path: Phases 0-2 CLOSED (CAS-RRK 34 tests, CAS-Sem 19); Phase 3 substantially closed (RPM D6 stable, CCB-M1 verifier 27; five-class memory taxonomy and linear-equation checker OPEN); Phase 4 partial (CCB-L1 18; sever-the-cortex holds by construction — no LLM anywhere in the loop; CCB-D1 and the cortex itself OPEN, cortex BLOCKED on the Route B owner decision); Phases 5-6 closed at v0.1 scale (G8 re-audited NOT REFUTED; G9 earned, its adversarial re-verification queued); Phase 7 partial (workbench + CRQS; editor/composer/chat panes open); Phase 8 machinery real, benchmark NOT RUN.
- Current qualification unchanged: CAS-G9 / E5 / A0 — the design ceiling. CAS-G10 requires long_term_goals + self_model boards, the multi-domain long-horizon suite, and E6 independent replication.

## 2026-08-28 (G9 round) — CAS-G9 earned: the Self-Improving Architect gate, with procedure synthesis from the machine's own evidence

- Built rlp/self_improvement.py — the machine's own G9 loop, production code end to end: (1) SELF-DIAGNOSIS from its own sealed cycle packet (no promotion + budget-starved candidates = typed procedure_budget_failure naming the starved candidates and the evidence digest; a healthy procedure yields NO_PROCEDURAL_FAULT — the machine does not invent work for itself); (2) SANDBOX exploration on copies, parent packages and memory digest-checked untouched; (3) SYNTHESIS of the candidate procedure from the sealed exploration — the promoted mutation's guard moves to the front of the neutral pool, provenance self_improvement:<evidence-digest> — closing the recorded G8 bound (no hand-authored strategy library in this loop); (4) validation under the six-check acceptance law on training AND held-out fault cases; (5) promotion to versioned strategy memory with rollback. The judge (expectations + protected set) is digest-checked identical before and after every cycle.
- The CAS-G9 qualification suite (tests/test_g9_suite.py, 9 tests, all pillars of spec section 11's G9 row): self-diagnosis from sealed evidence with a no-false-positive contrast; sandboxed exploration leaving the parent byte-identical; evidence-derived synthesis (order ['gt','eq','lt'] != the neutral default, derived_from_mutation recorded); promotion + held-out validation + transfer of the self-improved memory to the structural fixture in 1 evaluation; unauthorized descendants rejected (R3 raise + evaluator tampering REJECTED_AS_PROTECTED) with the judge digest unchanged; EXACT parent replay after rollback (grades and final state hashes equal the pre-promotion run; memory rollback restores the parent snapshot); the causal ablation (skip the self-improvement cycle -> the same budgeted repair fails on training AND held-out; run it -> both succeed in 1 evaluation); and the digest-identical double run earning the STABLE D9 flag. RLP suite 41 green.
- REQUALIFICATION: the assembled CNCM now qualifies CAS-G9 / E5 / A0 — the machine has reached its own DESIGN CEILING. Stable D9; no peak above stable remains. Next target CAS-G10, and the derived upgrade names the real gap honestly: build long_term_goals and self_model machinery (new boards, not new test rounds), then the multi-domain long-horizon G10 suite; E5's ceiling is exactly G9, so G10 will also demand E6 independent replication. suite_CAS-G9 is held-out (r1_bigger_held_out validates; r1_heavier_structural transfers). RMB NOT RUN.
- Whole program now: kernel 34 + RLP 41 + CCB-M1 27 + CCB-L1 18 + CAS-Sem 19 + workbench 13 + CRQS 33 + CCB-T1 20 + OHM-panel 10 + cas-rr 43 = 258 tests, all green.

## 2026-08-28 (re-audit round) — independent re-audit: NOT REFUTED; residual bounds recorded and the cheap ones closed

- Independent 2-agent adversarial re-audit of commit 19327ba3: NOT REFUTED on both fronts. The auditor reproduced both ablation legs by hand (neutral pool: BUDGET_EXHAUSTED on eq, no promotion; learned strategy: promotion in exactly 1 evaluation with machine-driven recall provenance), proved the alphabetical pool is genuinely neutral by building a counterfactual eq-class package where eq-first WINS, verified the cross-process retention leg spawns a real fresh interpreter, and confirmed 23+8 manifest counts match actual collection. The RMB honesty gates could not be bypassed on the render path (PASS mathematically impossible while any domain is BELOW; no band verdict without all nine conditions; equivalence refused by name).
- Closed in this round, each with a test: strategy recall now REORDERS the candidate pool instead of replacing it — the audit's counterfactual (a learned gt-first strategy blocking a correct eq-repair in its own fault class) now promotes the residual eq candidate instead of dead-ending (test_g8_learned_strategy_cannot_block_a_correct_eq_repair); RMB attestation requires boolean true, not truthy placeholders; equivalence claims refused even under NOT RUN; band_summary refuses empty domains; manifest demonstration rows now carry resolvable artifact paths; the overstated pool comment fixed. RLP 32, CRQS 33 green.
- Recorded bounds on CAS-G8 (spec sheet, stated wherever the claim is quoted): the strategy space is two hand-authored orders (one evidence-driven binary choice, not synthesis); the causal margin is one guard position under budget=1; retention is package-content across a process boundary, not cross-machine; hidden fixtures remain aspirational (held_out hides from the repair loop, not from developers); the adaptive loop has not run through the full eight-board assembly.
- Whole program now: kernel 34 + RLP 32 + CCB-M1 27 + CCB-L1 18 + CAS-Sem 19 + workbench 13 + CRQS 33 + CCB-T1 20 + OHM-panel 10 + cas-rr 43 = 249 tests, all green.

## 2026-08-28 (G8-repair round) — adversarial audit REFUTED G8 v1; rebuilt to survive its own ablation; Hybrid Machine Doctrine adopted; RMB reference bands implemented

- NEGATIVE RESULT ON THE RECORD: a 3-agent adversarial verification of the adaptive round REFUTED the G8 claim on the standard's own terms. The fatal finding: the "learned" guard order ['gt','lt'] was byte-identical to the hardcoded default in rlp/mutations.propose_repairs, so the causal ablation (no strategy, budget 1) repaired the held-out case identically WITHOUT learning — failing CRQS section 19's own requirement that removing the credited component must degrade the capability. Also found: "delayed retention" was within-process byte-identity true by construction; the transfer fixture was a string rename; StrategyMemory.lookup was never called by production code (test-harness stitching); the 6 G8 tests were double-counted in the manifest (rlp 29 included them); manifest task_id "modus_ponens" did not match the real fixture "modux_ponens". Suites and scrub were confirmed green/clean apart from two utm_source=chatgpt.com URL crumbs in the charter (stripped).
- REPAIR, each item with a test: the default guard pool is now NEUTRAL (eq, gt, lt — alphabetical, no domain knowledge), so the causal-ablation test passes for real: no strategy or an empty memory -> BUDGET_EXHAUSTED, learning is load-bearing. Guard variables are extracted STRUCTURALLY from the guilty rule and conclusion-aligned, so repair generalizes. New transfer target r1_heavier_structural: different predicates and variable names, REVERSED premise order, distractor entity and facts — repaired in one evaluation by the MACHINE's own diagnose->recall->apply loop: CAS_RLP.improve(strategy_memory=...) is production code and records every recall as provenance. Delayed retention now crosses a PROCESS BOUNDARY: the corrected package is persisted, reloaded in a fresh interpreter, digest-identical, all pass. The learner's held-out during learning is non-vacuous (taller trains, bigger held out, heavier stays unseen). Manifest de-double-counted (rlp 23 + suite_CAS-G8 8) and task_id fixed. RLP 31 green; CAS-G8 / E5 / A0 stands on ablation-proof evidence.
- HYBRID MACHINE DOCTRINE adopted as the lane's governing roadmap (cas_only_reasoner/HYBRID_MACHINE_DOCTRINE.md, owner directive 2026-08-28): CAS executive brain + learned neural language cortex; GPT-1/2/3 as engineering reference BANDS reported per dimension, never one-number equivalence; three construction routes with Route B (pretrained cortex) flagged OPEN against the standing no-foreign-models rule pending owner ratification; seven register-bypass tests mandatory before any cortex is credited; ^8-vs-^6/^9 runtime enforcement adopted as a roadmap item.
- RMB reference bands implemented per the doctrine (CRQS_v0.1/crqs/rmb.py + report wiring): named historical bands with citations, per-domain PASS / PARTIAL / BELOW / ABOVE / CAS-specific verdicts each requiring an evidence artifact, the spec-16 identical-conditions gate (nine conditions attested or NO verdict), refusal of single-number equivalence claims, honest NOT RUN default — the CNCM's RMB remains NOT RUN. CRQS 30 green.
- Whole program now: kernel 34 + RLP 31 + CCB-M1 27 + CCB-L1 18 + CAS-Sem 19 + workbench 13 + CRQS 30 + CCB-T1 20 + OHM-panel 10 + cas-rr 43 = 245 tests, all green.

## 2026-08-28 (adaptive round) — CAS-G8 earned: the Adaptive Learner gate; GPT-naming dictates removed

- OWNER DIRECTIVE: removed every GPT-naming prohibition/disclaimer from the project ("Never GPT-1/2/3", "No GPT-equivalence claims", "should never receive GPT-4 level", the enforcing test, the "not in the GPT league / GPT-0-era breadth / anyone quoting is overclaiming" passages) across the charter, CRQS code/spec/README/tests, spec sheet, this changelog's earlier entries, and docs/cas_rr/CAPABILITY_REPORT_V0_1.md. The constructive machinery stays: the RMB fair-comparison protocol, the capability-by-capability reference table, and every hard gate. The cas_only_reasoner lane now contains zero GPT mentions.
- Built the CAS-G8 qualification suite (CAS_RLP_v0.1/tests/test_g8_suite.py) against the REAL machinery, per spec section 11: correction retention (the promoted gt-guard persists; a fresh re-run of the corrected package passes; parent revision retained), delayed retention (the learned content is byte-identical after unrelated intervening kernel work and still passes), structural transfer (the class-level strategy learned once on the taller package repairs the unseen bigger package in ONE evaluation, while the unstrategic order still exhausts the same budget — the strategy is doing the work, not the problem being easy), protected regression (R3 mutations and evaluator tampering still rejected AFTER learning), and the stability run (the whole sequence twice from scratch, digest-identical) that earns the STABLE D8 demonstration flag. RLP suite 23 → 29 green.
- REQUALIFICATION: the assembled CNCM now qualifies CAS-G8 / E5 / A0 — design ceiling CAS-G9, stable D8, peak D9 still gated as not stable, next target CAS-G9 (the G9 suite: self-diagnosis, sandbox, reject-unauthorized, promote, parent replay — plus a stable D9 demonstration). suite_CAS-G8 is held-out (r1_bigger_held_out is the unseen transfer case). RMB NOT RUN.
- Whole program now: kernel 34 + RLP 29 + CCB-M1 27 + CCB-L1 18 + CAS-Sem 19 + workbench 13 + CRQS 21 + CCB-T1 20 + OHM-panel 10 + cas-rr 43 = 234 tests, all green.

## 2026-08-28 (tool round) — CCB-T1 v0.1 clears the strict G7 gate; audit fixes; CAS-Ohm panel

- AUDIT of the qualification-round handoff (uncommitted work found in cas_only_reasoner/): CCB_T1_v0.1 (tool board) and CAS_OHM_INSTRUMENT_v0.1 (instrumentation panel) built but unrecorded; one CRQS test left RED (the section-10 report dropped "Estimated upgrade:" once nothing blocked); the kernel prover change (goal-side variable freedom + two-pass fact selection) load-bearing but COVERED BY NO TEST; a provenance violation raised the WRONG TYPE (ToolUnknown); a tool fault CRASHED the board loop instead of halting typed (the manifest claimed "typed halt, no crash"); a zero-cost useless tool could loop forever; the calculator emitted its comparison fact ONLY in the goal-friendly direction.
- Fixes, each with a test: ToolProvenanceViolation as its own type; every tool fault now a TYPED terminal status of the board (TOOL_PERMISSION_DENIED / TOOL_BUDGET_EXHAUSTED / TOOL_FAILURE / CONTRA_TOOL_RESULT / AMBIGUOUS_TOOL_NEED / TOOL_PROVENANCE_VIOLATION / NO_TOOL_PROGRESS) — never a crash, never a fabricated continuation; a round adding no new fact halts typed; the calculator reports gt/eq/lt SYMMETRICALLY so the caller's goal cannot shape the tool's facts; 6 kernel unification regression tests (kernel 28 → 34); the CRQS report now ALWAYS derives an estimated upgrade from the manifest itself (missing machinery, missing suite, missing stable demonstration, public-not-held-out suites) — never asserts one.
- G7 earned, not asserted: the adversarial variants now include paraphrase (renamed entities), reordered facts and premises, noise + instruction-shaped facts inert as data, and the FALSE goal (1/8 + 1/8: lt reported, NEEDS_INFORMATION, nothing fabricated). CCB-T1: 20 tests green.
- CAS-Ohm Instrumentation Panel v0.1: the paper's restrictions R1–R10 as executable rules (disjoint calibration/validation splits enforced; residuals rank probes, identify no causes; synthetic_mock label travels; R1–R10 printed verbatim in every report). OPTIONAL instrumentation — R10 verified: no reasoning board imports it. 10 tests green.
- REQUALIFICATION: the assembled CNCM now qualifies CAS-G7 / E5 / A0 (design ceiling CAS-G9; next target CAS-G8; peak D9 still gated as not stable). RMB NOT RUN; the G7 suite is public, not held out, and the report says so.
- Whole program now: kernel 34 + RLP 23 + CCB-M1 27 + CCB-L1 18 + CAS-Sem 19 + workbench 13 + CRQS 21 + CCB-T1 20 + OHM-panel 10 + cas-rr 43 = 228 tests, all green.

## 2026-08-28 (qualification round) — CRQS v0.1: the CAS Reasoning Qualification Standard

- Built cas_only_reasoner/CRQS_v0.1/ per the appended standard: the qualification bench that grades any board or Mind on the four questions (how difficult was the test, what level was demonstrated, how strong is the evidence, what to repair next) with five outputs: TDG, CAS-G, Capability Vector, E-Tier, A-Level (RMB optional and always separate).
- TDG: nine difficulty axes 0..4, DI 0..36, D0-D10 banding, and HARD FLOORS (recursion -> at least D6, learning with held-out transfer -> D8, self-modification -> D9, novel research -> D10) so a recursive task can never be mislabeled simple.
- CAS-G0..CAS-G10 + CAS-GΩ (research designation only): strictly sequential - a level requires EVERY lower level. Three levels computed: Design Ceiling (topology), Demonstrated (stable vs peak), Qualified = min(ceiling, demonstrated, evidence ceiling). E-Tiers E0-E6; A-Levels A0-A5 (capability is not permission); seven zero-tolerance hard gates plus performance gates with precision and coverage always paired.
- The twelve-dimension Capability Vector computed from topology + suite evidence, with domain skills reported separately; the 14-signature repair ontology with the mandated ordering (safety first, speed last); the section-10 report format; the 15-step QUALIFY workflow.
- 19 tests green. THE HONEST RESULT IT PRODUCES FOR OUR MACHINE: the assembled CNCM qualifies CAS-G6 / E5 / A0 - the strict G7 tool-use gate is unmet, so the real, held-out-validated adaptive-learning and self-improvement components cannot raise the generation; peak demonstrated D9 is recorded as gated. The report names the exact upgrade: typed tool intents, fault/adversarial variants, resource-exhaustion halting tests, clarification requests. That is the standard working as designed: no topology medals, RMB NOT RUN.
- Whole program now: CRQS 19 + workbench 13 + RLP 23 + CAS-Sem 19 + CCB-L1 18 + CCB-M1 27 + kernel 28 + cas-rr 43 = 190 tests. Remaining: tool use (the G7 gate, charter section 19) and encoders/neural instrumentation last.

## 2026-08-28 (workbench round) — CAS Cognitive Workbench v0.1: the glass-brain interface

- Built cas_only_reasoner/CAS_WORKBENCH_v0.1/ per charter section 3: ten panes (dialogue, goal map, live board, clickable branch tree with the full candidate WHY, RPM stack, memory explorer with typed lacunae, truth and evidence, chained trace timeline, learning dashboard, evolution lab) plus the organ-stack summary - a RENDERER, never a reasoner.
- workbench/generate.py runs all six boards once, deterministically, seals the pane bundle with a digest, and emits workbench_data.json plus a single self-contained glass_brain.html (data inlined; opens in any browser with no server). workbench/app.js is projection-only and passes node --check.
- 13 conformance tests: every pane present and non-empty; trace hashes CHAIN (post of tick N equals pre of tick N+1); the branch tree carries two candidates with the winner's proof path; the RPM pane shows push and return; the truth pane contains VERIFIED and REJECTED; the evolution lab shows PROMOTED and REJECTED; the memory pane carries records and lacunae; regeneration is byte-identical; organ totals sum to the program count.
- Whole program now: workbench 13 + RLP 23 + CAS-Sem 19 + CCB-L1 18 + CCB-M1 27 + kernel 28 + cas-rr 43 = 171 tests. Charter section 3 (workbench interface) DONE. The ONLY remaining roadmap item: encoders/decoders as peripherals and neural instrumentation, last, under the paper's own restrictions.

## 2026-08-28 (procedural round) — RLP ring R1 strategies: procedural learning under budget

- Extended CAS-RLP with procedural learning per the charter's "learned problem-solving routines": repair STRATEGIES (ordered candidate-repair schedules per fault class) promoted under the acceptance law.
- rlp/strategies.py: versioned strategy memory (provisional -> verified, provenance, history, rollback). rlp/procedural.py: the ProceduralLearner - budget-constrained repair runs with evaluation accounting (BUDGET_EXHAUSTED decisions), training + held-out fault cases of the same class, and the full acceptance checklist (budget_success, held_out_gain, no_regression, evaluator_untouched, versioned, rollback_preserved) with sealed decision evidence and deterministic cycles.
- The demonstration: fault class overgeneral_rule has a bounded guard pool; with a repair budget of ONE sandbox evaluation, the unstrategic order (lt first) exhausts the budget and fails, while the learned order s_gt_first repairs BOTH the training case (taller rule) and a held-out case of the same class (the overgeneralized bigger rule) in one evaluation each -> PROMOTED (provenance prior_proof); s_lt_first is REJECTED; unbudgeted default behavior is untouched (regression); rollback restores the parent strategy memory.
- rlp/mutations.propose_repairs now takes the strategy order; CAS_RLP.improve takes guard_order and max_evaluations and seals evaluations_used into the cycle packet. New fixture r1_bigger_held_out (held-out fault case). 10 new tests; RLP suite now 23 green.
- Whole program now: RLP 23 + CAS-Sem 19 + CCB-L1 18 + CCB-M1 27 + kernel 28 + cas-rr 43 = 158 tests. Roadmap item 5 (procedural learning) DONE. Next artifact: the cognitive workbench interface (charter section 3).

## 2026-08-28 (semantic round) — CAS-Sem v0.1: the semantic content and binding layer

- Built cas_only_reasoner/CAS_SEM_v0.1/ per the charter: CAS-Sem separates the CONTENT of thought from the cognitive operation performed on it. The Codex working folder remains strictly untouched.
- The content model: typed entities with identity, property/relation/event ideas with role schemas, references with binding (name/pronoun/description), a transitive timeline, nine truth statuses (GIVEN/ASSUMED/DERIVED/OBSERVED/VERIFIED/CONJECTURED/CONTRADICTED/UNKNOWN/UNDERDETERMINED) with discipline, and provenance (who said it, when, what evidence).
- The six coherence laws, each enforced and each demonstrated by a broken document in the demo: referential integrity (unresolved references are typed errors and CMB ENTITY_MISSING lacunae), temporal consistency (transitive contradiction detection), truth discipline (no VERIFIED AND CONTRADICTED; DERIVED requires a derivation; CONTRADICTED requires the conflict pair), provenance completeness, type discipline, and derivation validity - every DERIVED claim must RE-PROVE through the unchanged CAS-RRK proof kernel.
- The Semantic CMB: queries by entity, truth, and time ordering; typed lacunae; ablation support via a live-registry override on the coherence checker. The lift bridge turns kernel-style propositions into DERIVED claims.
- 19 CAS-Sem tests green. Whole program now: CAS-Sem 19 + CCB-L1 18 + CCB-M1 27 + CAS-RLP 13 + kernel 28 + cas-rr 43 = 148 tests. Charter organ table: CAS-Sem row now DONE v0.1. Next artifacts: procedural learning (RLP ring R1 for proof strategies), then the cognitive workbench interface, encoders last.

## 2026-08-28 (language round) — CCB-L1 v0.1: the English acquisition board, strictly outside the reasoning loop

- Built cas_only_reasoner/CCB_L1_v0.1/ per the charter: English in at the edges, the unchanged CAS-RRK kernel reasons in the middle, English out. No LLM anywhere. The Codex working folder remains strictly untouched.
- The board: a versioned surface lexicon (verified entries never change silently; corrections version with history); CAS-Sem propositions; discourse state with pronoun resolution; a deterministic grammar fragment (copular, transitive, negation, question forms) whose failures are TYPED AND LOCATED ("I did not understand 'flurpy' at word 4 of 'the cat is flurpy.'"); the word-learning loop (detect -> candidate senses -> examples -> held-out -> contrast against grounding facts -> promote under the acceptance law); the one-way kernel grounding bridge (question -> kernel -> typed verdict -> English: CONCLUDED becomes "yes, the cat is gray.", NEEDS_INFORMATION becomes "i do not know whether the dog is gray." - the honest refusal carried into language).
- The eight charter English tests all implemented: round-trip meaning, paraphrase convergence, contrast testing (sense "loud" rejected by antonym conflict with the known fact has(cat, quiet); "gray" promoted), novel composition ("the zorp is flurpy." after learning flurpy on cats/dogs), referential tests ("it" resolves to the last mentioned entity), grounding tests, correction retention, ablation (removing an entry breaks parsing typed and located), plus determinism and rollback.
- 18 CCB-L1 tests green. Whole program now: CCB-L1 18 + CCB-M1 27 + CAS-RLP 13 + kernel 28 + cas-rr 43 = 129 tests. Charter section 13 (English) now DONE v0.1. Next artifacts: CAS-Sem expansion (entities, relations, reference, time, truth, provenance), procedural learning, then encoders/neural instrumentation last.

## 2026-08-28 (math round) — CCB-M1 v0.1: the mathematical learning and proof board

- Built cas_only_reasoner/CCB_M1_v0.1/ per the charter: CAS governs the search, the trusted checker decides validity, exact math everywhere. The Codex working folder was left strictly untouched.
- The board: exact rational arithmetic with a no-float conformance test (1/3 stays 1/3); an expression IR with exact canonical expansion (polynomial identities over rationals decided exactly - sound and complete for that class); the proof checker as SOLE validity authority (step continuity, structural axiom application, exact sample validation of LEARNED procedures, final canonical equality, first-invalid-step walk-down); bounded deterministic proof search with task-level strategy constraints ("prove it by expansion, not by commuting"); an exact counterexample generator (x+y=x*y refuted by (1,1); x^2>x refuted at the boundary x=1; the true square identity survives); a curriculum prerequisite DAG.
- The full mistake-recovery cycle demonstrated: the ruleset holds the incorrect procedure square_sum ((a+b)^2 -> a^2+b^2); the false claim (x+1)^2 = x^2+1 is REJECTED at step 0 by exact sample validation (x=1: 4 != 2); diagnosis names square_sum; the lesson library supplies square_expand; the repaired descendant passes the held-out proof task with regression intact -> PROMOTED under the acceptance law; the corrected proof is VERIFIED; rulesets are versioned and rollback preserved; the cycle is deterministic with sealed decision evidence.
- The eight math authority invariants are executable: no VERIFIED without the checker; repairs never target the checker or benchmarks (REJECTED_AS_PROTECTED); definitions never change silently; the proof kernel is outside autonomous write authority.
- 27 CCB-M1 tests green. Whole program now: CCB-M1 27 + CAS-RLP 13 + kernel 28 + cas-rr 43 = 111 tests. Charter sections 14 (math) and the Trusted Verifiers row now DONE v0.1. Next organ: CCB-L1 (English), strictly outside the reasoning loop.

## 2026-08-28 (evolution round) — CAS-RLP v0.1: the recursive learning and evolution protocol above the kernel

- Built cas_only_reasoner/CAS_RLP_v0.1/ per the charter's improvement loop and four rings, ABOVE the kernel: RLP never modifies the kernel executable - it evolves content (rules, parameters) across versioned descendants and asks the unchanged kernel to judge each one.
- The full cycle in code: diagnose the first failing stage from a sealed trace -> classify the fault -> propose bounded candidate repairs -> fork sandbox descendants -> run regression + held-out suites through the kernel -> apply the acceptance law (gain >= delta_min, no protected regression, authority invariants, deterministic replay, held-out outperformance, evaluator not modified, sealed evidence, rollback preserved) -> promote / quarantine / reject -> preserve rollback.
- Demonstrated end to end (13 tests + run_demo.py): R0 experience records automatically with provenance; R1 promotes a gt-guarded repair of an overgeneralized taller rule (held-out corrected, regression intact) and REJECTS the lt-guarded sibling (it broke the protected regression case); R2 REJECTS a budget-starving parameter change and QUARANTINES a no-gain one; R3 REFUSES mutations of the kernel/sole-writer/proof-checker/benchmarks; evaluator tampering is REJECTED_EVALUATOR_TAMPERING ("a version may not rewrite both its reasoning method and its exam in the same transaction"); rollback restores and re-verifies the parent; every decision seals an evidence packet and the whole cycle is deterministic.
- Charter reconciliation updated: sections 15 (recursive self-improvement), 17 (self-diagnosis), and the section-22 rows for learning/self-diagnosis/safe-improvement now DONE v0.1. Spec sheet.txt updated. Kernel suite still 28 green; RLP suite 13 green.

## 2026-08-28 (kernel round) — CAS-RRK v0.1: the authority-contract reasoning kernel, built from the complete capability charter

- The complete capability charter was appended to cas_only_reasoner/cas_reasoner.txt (24 sections: the CNCM organ table, internal stack, workbench interface, goals/attention/memory/candidates/inference/comparison/RPM/uncertainty/commitment, English, math, recursive self-evolution, the first-convincing-version table). This round delivers the charter's Phase-1 target: the CAS Reasoning Runtime KERNEL with the atomic authority contract.
- Built cas_only_reasoner/CAS_RRK_v0.1/: the four frozen handoff artifacts (AUTHORITY_MANIFEST.yaml, minimal CAS-Sem + inference semantics, 9 machine-readable JSON schemas, 6 golden conformance fixtures), NON_GOALS/OPEN_QUESTIONS/README_HANDOFF, the five spec documents (kernel spec, CAS-Sem MVP, kernel IR with the 12 native reasoning ops, the verbatim authority contract, the 16-row conformance plan), and the Stage-1 Python reference kernel.
- The kernel implements: snapshot-based machine state with canonical hashing; intent-only components (scheduler/branch/RPM/latch/write-back/halting); the transaction coordinator as SOLE writer; STATE COMMIT vs DECISION COMMIT as separate operations; goal-scoped branch isolation with rollback; RPM push/return with parent-identity enforcement; live re-proof of every inference and decision commit (the proof kernel decides validity); sealed per-tick trace events; deterministic replay with identical per-tick state hashes; typed halts incl. BUDGET_EXHAUSTED and LOOP_LIMIT_REACHED.
- 28 kernel tests green: all 16 conformance rows (authority attacks, stack faults, conflict resolution, rollback, budget, loop limit), 6 golden fixtures (modus ponens, transitive, contradiction, missing information, candidate planning, RPM recursion), 6 deterministic replay checks with frozen trace digests. cas-rr suite still 43 green.
- Five load-bearing bugs found and fixed while building (each is a lesson): conflict resolution must key on OPERATION not raw field; match() returning {} is falsy; consumers must never read stale compare reports (control flow re-proves live); a subgoal's commit must be cleared on return or the latch reads it forever; CONCLUDED requires the ROOT goal's own branch.
- Charter reconciliation: docs/cas_only_reasoner... wait, CAS_RRK_v0.1/docs/CAPABILITY_CHARTER_STATUS.md maps all 24 sections to DONE/PARTIAL/ROADMAP; section 22 (first convincing version) is 15/15 demonstrated. spec sheet.txt now holds the project spec. Stage 2+ (shared kernel IR, differential Rust execution, CAS-RLP, CCB-L1 English, CCB-M1 math) is the declared roadmap.

## 2026-08-28 (evaluation round) — CAS-RR capability criterion, ladder test, and R3 verdict

- Developed the executable reasoning-capability criterion (docs/cas_rr/REASONING_CAPABILITY_CRITERION.md): seven quantified difficulty axes (D proof depth, B branching, C constraints, N negations, U uncertainty, M memory, R recursion), a L0-L6 ladder, R0-R4 tiers, and the scoring principle that a typed refusal is the CORRECT answer when an operator does not exist - and that honesty never raises the tier.
- Tested the machine against the ladder (python run.py report): core 9/9 passed (L0 recall through L5 recursive planning), frontier 4/5 refused honestly (native arithmetic, induction, probabilistic, hypothetical). Verdict: capability tier R3 (recursive planner); R4 not attained.
- The test exposed and we fixed the biggest engine gap: FLAT recursion. Subgoals could halt but not descend. Now scans report the exact missing prerequisite token, subgoals carry their resolving action's prerequisites, and any goal may descend - depth-2 nested planning (capability -> knowledge) passes: 7 ticks, full ascend/descend trace, in cas-rr/tasks/battery.py (task_recursive_nested).
- Capability report with the honest reference-model mapping (docs/cas_rr/CAPABILITY_REPORT_V0_1.md): proof-grade symbolic core, deliberately narrow breadth in v0.1; guaranteed deduction/provenance/typed-refusal where reference LLMs confabulate, and zero language/learning/probability where they have all three (each excluded by design, each on the roadmap). Prioritized fixes: hypothesis autonomy, backtracking, arithmetic peripheral, induction operator, uncertainty degrees, procedural learning, encoders, CCDL emit/parse, breakdown semantics, memory ranking.
- Suite now 43 passed; CLI determinism check green on all 12 battery tasks (including the new nested one).

## 2026-08-28 (later) — CAS-RR interaction layer: CLI, reporter, determinism checker, authored-problem example

- CLI: python run.py list / run <task> [--trace] [--full] [--json out.json] / demo / check / repl — the machine is now drivable from the command line; bench reports show status, output, the RPM recursion story (descend/resolve, scans with cached flags showing fresh re-measurement), deduped lacunae, tournament elimination, commitment gates, and the winning proof path.
- cas_rr/report.py (summarize / battery_table / trace_compact / determinism_check) + run.py CLI; INTERACTION.md covers the packet anatomy, a problem-authoring template, and safe poke experiments (eval-gain boot rejection, memory seeding, budget starvation, typed halts).
- examples/custom_kinship.py: a grandparent syllogism the battery has never seen, authored from scratch and solved by the generic machine (CONCLUDED -> grandparent(ada,cy), proof via r_grandparent) — live proof of the encoder boundary and of "one machine, encoded problems".
- 12 new interaction tests; suite now 37 passed. CLI determinism check green for all 11 battery tasks (traces, status, output identical across double runs).

## 2026-08-28 — CAS-RR v0.1: a native CAS reasoning machine (not a harness)

- Built the first executable CAS-native reasoner from the three PCBA sources (CAS PCBA Engineer book, CAS-Ohm 1.0 v0.2 paper, CAS-Ohm Quantification Guide): CJTs with all four regions (cutoff/active/saturation/breakdown), typed biases, gain regimes (candidate 1.5 / evaluation 1.0 constitution-locked / commit 2.0 / learn 0.05), 7 Foundation engines x 28 sub-foundation channels with the Foundation-to-Drive adapter, CMB 40-cell memory with typed lacunae, ^8/^6/^9 reasoning spine (association ≠ deduction), CDAB shared-bias tournament, RPM D→W→P recursion stack (section-retraction; re-measure from scratch after every subgoal), Schmitt commitment with 7 typed halt states, P→C→E→O sequencing with O-last boot ("no action without principle"), low-gain episodic learning (procedural/constitutional layers disabled in v0.1), append-only reasoning provenance packets.
- 25 pytest tests green in cas-rr/: the six-task native battery (transitive inference, constraint satisfaction, fault walk-down, missing-information, recursive planning, memory-dependent) plus negative variants covering all seven halt states, the five load-bearing laws, determinism, candidate invariant, boot order, and both rumination stop gates.
- Source grounding done first: 16/17 load-bearing claims CONFIRMED, 1 PARTIAL (the 7/28/22 ontology lives in the TKS side, not the three PCBA sources; root label is A0/A1 — "A22" appears nowhere; 4 CJT regions, not 3). Honest boundary: deterministic symbolic reasoning with no LLM in the loop; no empirical-generality claim; CAS-Ohm used only as authored design quantities per the paper's own restrictions.
- Artifacts: cas-rr/ (package + tests), docs/cas_rr/CAS_RR_V0_1_SPEC.md (18-chapter operational semantics), docs/cas_rr/CCB_R1_BOARD_SPEC.md (the motherboard), docs/cas_rr/SOURCE_GROUNDING_NOTES.md (verbatim citations).

## 2026-08-22 — Frontier #1 lever RUN (pre-registered, $0): domain axis vs matched Tinbergen taxonomy — INCONCLUSIVE BY DESIGN

- Pre-registered before capture: `PREREG_DOMAIN_VS_TINBERGEN_20260822.md` (sha256 `14ace6dd…`).
- Executed the spec sheet's single most available lever for CAS-specificity: the v4 domain fixture (8 topics × 4 domains) on `pythia-160m-reserialized` (attested engine, CPU, $0), two label arms on the SAME vectors — CAS P/C/E/O vs Tinbergen's four questions (abstractness-aligned primary, positional sensitivity).
- Result: `INCONCLUSIVE BY DESIGN` — nearest-centroid accuracy is invariant under bijective class relabeling, so the arms tie by construction (layer-mean 0.875 = 0.875, best 1.0 = 1.0 at layer 2, identical at all 12 layers, McNemar p = 1.0). The prereg's literal verdict word (`DOMAIN_DOES_NOT_BEAT_GENERIC_ABSTRACTNESS`) is not citable.
- Standing positive: the CAS arm reproduces v4's cross-topic domain decodability (layer-mean 0.875, best 1.0, shuffle 0.259, random-subspace 0.25).
- Frontier #1 remains OPEN; the lever requires the Condition-3 blind-rater instrument or independently-annotated rival labels.
- Artifacts: `docs/working/gate2_closure/cas_specificity/domain_vs_tinbergen_20260822/` (results sha256 `d6b0787d…`). No claim upgraded; no negative hidden.

## 2026-08-19 — WELD v2: a CAS diagnose→correct loop that can actually FAIL (one axis, two criteria)

The Gate-5 WELD build was reviewed at `2be60327` and failed its own review: all four success
criteria were true by construction. `docs/working/gate5_weld/cas_weld_loop_v2.py` +
`WELD_SPEC_V2.md` supersede it (the v1 files are left on disk as the failure record).

- **Scope narrowed on purpose to ONE axis** — `A` (Pathway/RPM chain) on the numeric plane,
  the single detection the review found genuine. Axes N/W/F/E/S/P are declared out of scope.
  J1, J2, the epsilon realizers, the PCBA vocabulary and stage 5 are **absent**, not stubbed.
  v1's criteria (c)/(d1)/(d2) were **deleted**, not repaired — they lived on a lossy
  projection and could not be made falsifiable.
- **Blindness is structural.** `diagnose_blind(obj)` and `localize_blind(obj)` take exactly
  one parameter, asserted via `inspect.signature`; there is no parameter through which an
  axis name, a pre-injection object or a fault record could be passed. No concatenation
  anywhere. Ground truth is read once per case, only to score localization, and every read
  is logged.
- **The chain is proved load-bearing, not asserted.** `repair(obj, targets)` is called with
  `targets is localization.indices`. A built-in tamper check reproduces the v1 defect once:
  driven by the localizer NEG-3 reports `axis A cleared = False`; driven by ground truth it
  reports `True`. The v1 wiring **manufactures a success where v2 reports a failure**, and
  the `PREREGISTRATION_VIOLATED` / exit-1 branch is reachable.
- **The control can match, and its null is stated with its derivation.** Exhaustive sweep of
  all `C(7,k)` same-size interventions with the localized subset **in** the pool. Chance rate
  **1/7 = 0.142857** (k=1) and **1/21 = 0.047619** (k=2), cross-checked empirically over 2000
  seeded random draws (0.1490, 0.0435; all |z| < 1.5). In NEG-3 the same control reports
  `positive_control = False`.
- **No involution identity.** The injector overwrites a stage with a seeded `U(0.05,0.45)`
  draw; the corrector is a constraint solver that never learns the original. `repaired ==
  pre-injection original` is **measured** and comes out False every run (L1 0.10 / 0.20 / 2.25).
- **6 cases, 3 designed to fail, all matched preregistration** → `LOOP_FALSIFIABLE_AND_HELD`,
  exit 0, 18,154 scanner calls, zero GPU/API cost, stable across 5 seeds. NEG-1 surfaces a
  live gap: `detect_pathway_inversion` misses every prerequisite inversion whose unsatisfied
  stage stays above 0.5. ROBUST shows the loop reporting a partial repair as partial
  (`axes ['W'] still fired — OUT OF SCOPE, NOT CORRECTED`).
- **Honest limit, stated in §9 of the spec:** the detector is a transparent hand-written rule
  over disjoint input slices, so every value the loop measures is derivable from the Rust
  source. The gate has **no** chance null and is not scored as identification. The claim is
  only that the chain reports failure when the diagnosis is wrong, never falls back to ground
  truth, never manufactures a correction, and beats a non-zero chance rate a random
  intervention can and does hit. **Nothing here bears on efficacy; no model is loaded.**
- Separate finding, committed on its own: `inversion_gate._DOMAIN_RE` used `` after
  `[PCEO]`, which `_` defeats, so **axis W could never fire on any drive-tagged expression
  in the repo**. Fixed; 7 regression tests (4 fail against the old regex); belief suite
  135 → 142 passing.

## 2026-08-19 — Gate 4 board-CHANGE: 16-conversation pilot RUN. Both claims VACUOUS; kill statistic fires but is not citable.

The pilot spend gate of `PREREG_BOARD_CHANGE_V1.md` was executed under AMENDMENT A1
(generation budget 800 → 4000). Prereg and runner sha256 verified unchanged across data
collection (`immutability_sha256.match = true`). ~429 provider calls; call counts landed
on §15 (224 main-pass labelling + 160 corpus turns + repairs/retries).

- **A1 works.** All four frozen generators now produce usable turns: per-generator median
  chars deepseek 6188 / gemini 4906 / glm 4898 / qwen 14935; zero turns under
  `MIN_TURN_CHARS=200`; zero kept-but-truncated conversations. But
  `GENERATOR_LENGTH_IMBALANCE_FLAG = true` (max/min median ratio **3.0494** > 3.0), driven
  by qwen saturating the new 4000 budget — 14 of 40 qwen turns end without terminal
  punctuation. The length confound flipped direction rather than disappearing.
- **`r̂ = 0.1884`** on 138 analysable pairs / 26 model-initiated changes. Above the `< 0.10`
  hard stop, so the preregistered STOP does not fire. `K_neutral = clamp(ceil(40/(2.98·r̂)),
  60, 120) = 72`.
- **GATE 0 = FAIL** (6 failed, 1 null) → **CLAIM 1 VACUOUS, CLAIM 2 VACUOUS**. Two failures
  are pilot-size arithmetic (analysable pairs 138 < 240; T-USER positive control NULL for
  want of Stratum S). Three are **not**: T-CHANGE Fleiss κ **0.2853** < 0.35 on 142 complete
  cases (inside the preregistered VACUOUS band, above the 0.20 instrument kill);
  B0 share of consensus board labels **0.7325** vs a 0.40 ceiling; T-USER κ **−0.0410**,
  degenerate because Stratum N is continuers-only (P_e = 0.9244).
- **Kill statistic fires:** `surface_change_f1` 0.4000 (S3 length) ≥ `board_change_f1`
  0.2647 → `KILLED = true`. Under §10.1 this is **not evidence and may not be cited**,
  because Gate 0 failed; and §15 forbids reading a pilot VACUOUS as a stop signal.
  Recorded, not claimed.
- Instrument health is good: complete-case coverage 0.981 / 0.986 / 1.000, consensus
  coverage 0.981 / 1.000 / 1.000, residual same-conversation batch collisions **0**,
  CONTROL 4 generator≠labeller violations **0** (computed, not asserted).
- Operational finding for any full run: glm-4.6 as a board reader returned
  `finish_reason=length` on **13 of 40** calls even at `max_tokens=20000`; two repair rounds
  recovered all but 3 items. Two glm conversations initially fell below `MIN_TURNS=6` and
  were re-attempted via the runner's own checkpoint-restart path (no labels existed yet).

Evidence backed up to `D:\tksCAS-archive\gate4_board_change_pilot_20260819\`.
No gate was moved, no threshold relaxed, no prereg file edited.

## 2026-08-17 — Gate 5 AWS package: durable backup + version-controlled regression guard

Two receipts landed for the Gate 5 staging package, both offline and $0.00.

- **Durable backup of the triple-audited GO package.** The frozen one-hour-session
  package `aws_cloudshell_unarmed_20260818` (identity `525365c4…`, archive 89,510 B /
  `a843f37e…`) previously existed only in the Codex build dir plus a volatile Temp
  scratchpad. It is now backed up to `D:\tksCAS-archive\project_coherence_gate5_one_hour_package_20260818\`
  with a `BACKUP_RECEIPT.md` and 3-way sha256 confirms — including a round-trip that
  re-extracts the D: archive and re-verifies all 18 member rows byte-exact.
- **Regression guard brought into git.** New `tools/aws_gate5/known_live_failure_lint.sh`
  encodes the three defect classes that each killed a package generation *live* after
  all static audits passed: C1 PowerShell `Test-Path` bound to a bare `-or` (20260815),
  C2 a script that both requires/pins root and calls `sts assume-role` (20260816, live),
  C3 an STS/role duration knob >3600s illegal for role-chained CloudShell creds
  (20260817, live). Positive-control calibrated: the verdict grid is strictly monotone
  and matches the real failure history — 20260815/16/17 each FAIL on their live class,
  the GO package PASSes all three. It is a floor to run before the full triple audit,
  not a substitute. Transcript committed at `tools/aws_gate5/CALIBRATION_EVIDENCE.txt`.

Statuses unchanged: Gate 5 OPEN / KEEP_OPEN; Stage C DESIGN_ONLY / UNAUTHORIZED;
corpus 0/960. Staging still awaits the owner's fresh `stage AWS now` bound to
`525365c4…`, with paid compute and final deletion as separate confirmations.

## 2026-08-08 — Noetic Topos 2.0 monograph: audit + corrections + adversarial verification (final volume)

Completes the five-volume audit campaign. 11 auditors → 128 findings (11 critical,
60 major, 57 minor); corrections applied by 4 parallel agents; then a 3-agent
ADVERSARIAL VERIFICATION pass over the corrections themselves, which found 19
residual defects, repaired by 3 further agents. 21 agents total on this volume.

Critical mathematical corrections (all independently recomputed in Python before
applying, and again during verification):

- **ch09 RPM-gluing failure count — wrong, found by 5 independent auditors.**
  Remark ch09:rem-other-failures claimed the ACBE witness presheaf separates the
  two topologies at "three of the sixteen contexts", citing a "direct check" that
  "both sides count 2" at triples. Both false. Because no RPM piece of any context
  contains a complete ACBE block, the matching-family set is a SINGLETON at all 16
  contexts; gluing fails wherever alpha(V) >= 1, i.e. at SEVEN contexts (A_0, A_1,
  the four triples at 2-to-1, and Omega at 4-to-1). The volume's own Appendix C
  already stated the correct seven-context result — the book contradicted itself.
- **appB block-completeness table — all four triple rows wrong.** Listed "none" as
  the complete RPM block of every triple; each triple contains exactly one
  (alpha = rho = 1). Contradicted ch07 Table 7.5, Appendix A, and Appendix C.
- **ch04 drafting artifact shipped in the PDF.** Example ch04:ex:bounded contained a
  visible mid-sentence self-correction ("...is not constantly 1? No: s *is*
  constantly 1...") attached to an unretracted false claim that a non-presheaf was
  "separated". Replaced with a correct, verified example.
- **ch05 impossible exercise.** Asked the reader to exhibit a counterexample to an
  invariant the same chapter proves, with a self-contradicting hint. Replaced.

Citation and scholarship: Cech cohomological-obstruction machinery re-attributed
from Abramsky-Brandenburger 2011 (which contains none) to Abramsky-Mansfield-Barbosa
2012, plus the CSL 2015 paradox paper and the 2017 contextual-fraction measure;
Mac Lane-Moerdijk pinpoint corrected (Ch. VII has no associated-sheaf theorem —
it is Ch. III sec. 5-6); canonical topology corrected to *universally*
effective-epimorphic sieves; sieve-axioms definition re-pointed from Stacks Tag
00ZC to 00Z4; per-volume bibliography created (17 cited entries, replacing a
46-entry shared list of which 34 were never cited); AI-assistance disclosure added
to the \thanks block, matching the four sibling volumes.

Defects the verification pass caught in the corrections themselves:

- appD glossary longtable went 85pt -> 433pt overfull, pushing the entire "Where"
  column (the chapter attributions ~30 fixes were correcting) off the printed page.
  Non-wrapping `lll` spec replaced with wrapping `p{}` columns; 433pt -> 0pt,
  confirmed by rendering the page. Same fix applied to ch11's table (420pt -> 0pt).
- 26 double-numbered cross-references left in ch09 ("Theorem 7.\ref{...}" renders
  "Theorem 7.7.12") after a sibling agent normalized the identical pattern in ch08.
  Produces no LaTeX warning, so a clean build does not catch it. Now zero volume-wide.
- Two corrections that introduced new errors: ch05 called the countermodel "finite"
  while ch06 (same pass) says it is infinite; appA's "ten -> nine contexts" change
  fixed a count to match a list that was itself incomplete. Both reverted correctly.

All five volumes rebuild with zero undefined-reference and zero undefined-citation
warnings. PDFs in docs/whitepapers/pdf/ refreshed.

## 2026-08-08 — CAS PCBA 8 monograph: 17-failure-mode audit + corrections (11-agent workflow)

- Same audit protocol as the two sibling volumes, run over
  docs/whitepapers/monograph/cas_pcba8/ (15 files). 117 raw findings,
  ~100 corrections applied.
- Fabricated specificity caught and corrected against the actual source PDF:
  ch11 claimed the CSB's clamp and fuse threshold are "declared thirty lines
  apart" — in the hash-verified book they are on ADJACENT lines (verified on
  PDF pp. 342/608); the unreachability proof's no-amplifier premise is now
  anchored to that fact. ch10's "sixteen reference-listing pages" corrected
  to the fourteen its own page ranges sum to.
- Worked examples reconciled with the volume's own closed enumerations:
  Appendix B's "clean pass" board used units (alpha, fraction) and a signal
  kind (constraint) that do not exist in ch04's closed vocabulary — its clean
  pass would actually fail DRC; ch08's worked run used an illegal
  (activation, dimensionless) pair; ch05's "legal junction" example
  deterministically fires PCBA8-BIAS-001 (E-rank bias under C-rank cause);
  ch04's simplex-rejection example used weights summing to exactly 1 (vacuous);
  ch07's NET-006 scenario was unrealizable under the admissibility table.
- Appendix/glossary reconciliation: appA's check-class table invented a sixth
  class and misassigned BIAS-001/SAF-002/TKS-001 vs ch07's normative five;
  adapter-certificate and trace tables gained their omitted citation-identity
  digest fields; appC's CJT entry imported CAS-Ohm content ch06 never delivers;
  glossary alphabetization fixed; doubled \bottomrule in four longtables.
- Math/notation: "no section of pi exists" corrected (the proposition proves
  no LEFT inverse; sections exist and its own proof exhibits one); machine
  epsilon vs unit roundoff distinguished; 0.25/1e-12 is eleven orders not
  twelve; omega definition unified on d; four "Chapter~\ref{section}" broken
  cross-references fixed; ch10's 28-vs-7 out-of-grammar arithmetic corrected
  to the taxonomy-consistent 19+9+1 accounting.
- Citations: Rao-1945 "was the first" priority claim corrected (Hotelling 1930
  anticipated both ideas); shrinking no longer implicitly attributed to the
  QuickCheck 2000 paper (\cite{claessen} added); "adversarial generation"
  de-attributed from QuickCheck; IEEE 754 flag list completed (division-by-zero);
  PROV-O glosses and Harel's statechart formula properly quoted; targeted/
  coverage-guided PBT (FuzzChick, Hypothesis) added to the stale PBT survey;
  Merkle cited for the hash-chain construction; Mars Climate Orbiter report
  cited for the unit-mixing claim; per-volume 17-entry bibliography replaces
  the padded 46-entry shared list.
- Substance: three sources-silent gaps marked as open documentation items
  (Phase-0 authority matrix digest, Gate-5 spec digest, TKS kernel approved
  constant, SAF-003 cycle cap, the 20 open review criteria's identities);
  ch12's "pinned environment" recomputation step now states the environment
  is NOT bound (hermetic reproduction is open obligation 5); baseline
  disclaimer anchored to its actual copyright-page text (verified in the book
  PDF); warn-fuse post-trip semantics gap declared; gain-bound "declared
  exceptions" phantom mechanism removed (FBK-003 has no exception path);
  conservative-direction misstatements fixed (ch05 reachable-resolution,
  ch06 clamp under-reporting); rival host formalisms (Statecharts, block
  diagrams, Petri nets) named with rejection reasons; F1-F7 drive names
  glossed; SARIF prior art acknowledged for the record format.
- Scholarly practice: AI-assistance disclosure added to \thanks; two QED
  tombstones on design arguments (ch08 determinism, ch05 digest) converted
  to the shared designargument environment.
- Style: ~45 fixes — fivefold "deserve(s) emphasis" cluster, sixfold "deserves
  its own X" template, the worth/deserves family (~48 occurrences), three
  "Every ... of this monograph" openers varied. Classic AI vocabulary clean.
- All five volumes rebuild with zero undefined references/citations; corrected
  PDF copied to docs/whitepapers/pdf/ and Downloads.

## 2026-08-08 — CAS-Ohm 1.0 monograph: 17-failure-mode audit + corrections (11-agent workflow)

- Same audit protocol as CAS Core 8, run over docs/whitepapers/monograph/cas_ohm1/
  (16 chapter files). 122 raw findings, ~110 corrections applied.
- Systematic censoring-rule misstatement fixed at 10 sites: text keyed censoring
  to "zero-compatible predicted response" and/or claimed the residual is
  suppressed, contradicting the defining ch10 rule (observed-side trigger,
  marker OBSERVED_INTERVAL_INCLUDES_ZERO; residual retained, only ratio
  quantities censored). Fixed in ch01, ch03 x2, ch04, ch11, ch12, ch14, appA, appB.
- Arithmetic/count fixes: ch07 ASOM cross-table caption+remark miscounted the
  printed table (6/14/8 -> 3/14/11; 22 -> 25 of 28 cells); "five literatures"
  -> seven (matching ch02's own count); "three sources" -> four (the PCBA book
  is the audit's registered fourth source); "four reasons" -> five; "twice the
  minimum" -> three times; ch10's synthetic fault-mode enumeration reconciled
  with the seven-board catalog used everywhere else incl. the governing v0.2
  paper; a dangling "item eight of the closure experiment list" citation fixed.
- Citation fixes: five Kennedy-O'Hagan over-attributions (preregistration,
  validation trichotomy, split discipline, "the receipt", decorative replay
  cite) corrected or re-attributed; three Zou et al. over-attributions (control
  inventory, sign flips, sweep phenomenology) re-scoped; two Ritz
  over-attributions reworded; VIM wording credited to VIM not GUM; decorative
  Buckingham cite anchored to dimensional homogeneity.
- Close paraphrase: four VIM3 definitions (quantity, measurand, uncertainty,
  traceability) now properly quoted against jcgm.bipm.org wording.
- Stale literature: 2024-2026 steering-reliability results added (Tan et al.
  NeurIPS 2024; Da Silva et al. ACL 2025), SAE feature-steering family +
  AxBench added as fourth construction family, Brynjarsdottir & O'Hagan 2014
  discrepancy-prior result added; preregistration section now cites
  Simmons/Gelman-Loken/Chambers/ICMJE instead of gesturing at "the literature".
- Substance: unexecutable "best memoryless model" evidentiary bar (ch13) made
  executable via frozen baseline family; "preregistered margin" constants
  re-scoped to per-run Gate-5 freeze (ch10 x6); anti-conservative min-confidence
  convention honestly characterized as an upper bound on joint coverage with
  Bonferroni revision flagged (ch08+ch09); gain-composition replay gap declared;
  caller-trust status of component region/linearity declared; five "declared
  X never declared" constants marked sources-silent/open (drift cadence,
  decimal context, resource limits, unit-norm rule, region aggregation);
  provenance-enum gap vs ch02's four families acknowledged; Q10 floor
  divergence marked as candidate choice; half-open-bin "only way" uniqueness
  claim replaced with the real Guide-display argument.
- Appendix/glossary reconciliation: appA scope honestly narrowed, no-diagnosis
  list completed (3 -> 6 regions), profile field table gains splits/instruments/
  dependency-lock/fit-receipt/full-scale rows; glossary calibration-profile,
  censoring, Q4-banding, status-vector, link entries corrected.
- Scholarly practice: AI-assistance disclosure added to \thanks (series-standard
  sentence); three QED tombstones on design arguments converted to the shared
  designargument environment; per-volume bibliography created (was printing ~35
  never-cited shared entries; now 20 entries, all cited).
- Style: 37 fixes — sevenfold verbatim "deserves emphasis" scaffold, ~30-strong
  worth/deserves family, five "Every ..." chapter openers varied. Classic AI
  vocabulary scan clean (delve/tapestry/landscape/paradigm = 0).
- All five volumes rebuilt: zero undefined references, zero undefined citations.
  Corrected PDF copied to docs/whitepapers/pdf/ and Downloads.

## 2026-08-08 — Monograph cross-reference repair (tks_v8, cas_pcba8, cas_ohm1)

- Fixed all 14 pre-existing undefined `\ref` targets that rendered as "??"
  in three volumes: tks_v8 used a `chNN:main` label convention that was
  never defined (`ch01/ch03/ch07:main` → `chNN:chap`, `ch10:main` →
  `ch10:testing`; 9 sites in ch04/ch05/ch06); cas_pcba8's ch05 intro
  pointed at a nonexistent `ch05:sec:boundary` (→ `ch05:sec:invariants`,
  the "Invariants and boundary" closing section); cas_ohm1 referenced
  `ch12:hypotheses`/`ch11:eligibility` where the chapters are labeled
  `hyp:chapter`/`elig:chapter` (4 sites in ch04/ch05).
- All five volumes now build with zero undefined-reference and zero
  undefined-citation warnings; PDFs in `docs/whitepapers/pdf/` refreshed.

## 2026-08-08 — CAS Core 8 monograph: 17-failure-mode audit + corrections (11-agent workflow)

- Ran an 11-agent audit workflow over `docs/whitepapers/monograph/cas_core8/`
  covering the 17 standard AI-writing failure modes (hallucinated citations,
  citation-claim mismatch, data fabrication/reconciliation, stale literature,
  substance, long-range consistency, style tells, scholarly practice,
  figure/equation defects). 98 raw findings; ~60 distinct corrections applied.
- Critical fix: ch04 invalid-boundary table had three arithmetically impossible
  family counts (16/8/2 corrected to 8/12/6; wrong values coincidentally summed
  to the correct 33, masking the error — verified by exhaustive enumeration).
- Appendix A + glossary reconciled to the normative chapters: namespace enum
  7→9 members, link-kind enum 3→4 (IDENTITY exists, guarded to self-links —
  "omission is the mechanism" was factually wrong), digest case lowercase→
  uppercase, phantom "review state" link field replaced with the real
  crosswalk fields (crosswalk_id, source_artifact_sha256, note, boundary),
  decision-model enums replaced with the actual three-member sets, glossary
  "eight-step" list fixed to eight items, wrong chapter title corrected.
- Citation integrity: ch12 claim that RFC 8785 handles "the full JSON value
  space" corrected to I-JSON (contradicted the RFC and the monograph's own
  ch02); per-volume bibliography created (the shared 46-entry list printed 41
  never-cited references against ch02's own "why these five citations"
  argument); bibitem keys `turnertrojans`→`zourepe` and `opre`→`vaswani`
  fixed in the shared bibliography (+ 8 cite updates in cas_ohm1); Buckingham
  title completed; three decorative/misattributed cites fixed or removed.
- Stale literature: in-toto / SLSA / Sigstore added to ch02's supply-chain
  survey and ch12's "against supply-chain attestation practice" contrast —
  the one materially stale area (2021-2025 attestation standardization).
- Substance: ch09's property-based-testing overclaim corrected to match
  ch12's own "no fuzzing campaign" account; ch01 "all five drift mechanisms
  observed" overclaim corrected to the two documented ones; ch11 "(and does)"
  uncertified companion assertion re-scoped; ch12 rejection-coverage claim now
  names its silent third family; ch05 declares uppercase digests, the JCS
  sort-order rationale (as reconstruction), and the bounds' underived status.
- Scholarly practice: AI-assistance disclosure added to the \thanks block;
  Reproducible Builds definition and PROV-O glosses now properly quoted;
  PROV model/ontology conflation fixed; five "Design argument" blocks moved
  off the amsthm proof environment (no more QED tombstone on non-proofs) via
  a new additive `designargument` environment in the shared preamble.
- Style: 19 fixes — the "it is worth X-ing / deserves" metadiscourse tic
  (66 corpus occurrences, worst cluster in ch09) reduced at its 16 worst
  sites; two identical chapter-opening and chapter-closing templates varied.
  Signature-vocabulary scan otherwise clean (delve/tapestry/pivotal etc. = 0).
- All five monograph PDFs rebuilt (shared preamble/bibliography changed);
  corrected `MONOGRAPH_CAS_CORE_8_v0.3.pdf` copied to `docs/whitepapers/pdf/`
  and the user's Downloads copy.

## 2026-08-08 — Project Coherence monographs v0.3 (book-length, ~934 pp total)

- Expanded the five v0.2 research papers into full `amsbook` monographs under
  `docs/whitepapers/monograph/`, each 184-188 pages: Noetic Topos 2.0 (188pp,
  12 chapters + 4 appendices), TKS v8.0 (184pp, 12ch + 3app), CAS Core 8
  (187pp, 12ch + 2app), CAS PCBA 8 (188pp, 12ch + 3app), CAS-Ohm 1.0 (187pp,
  14ch + 2app). PDFs in `pdf/MONOGRAPH_*_v0.3.pdf`.
- Authored via a 20-agent parallel fleet writing body-only chapter sources
  against a shared preamble/bibliography and a strict LaTeX + Ring-4 claim
  contract; ~425,000 words delivered before the fleet hit the session limit,
  with the 4 remaining appendix gaps (NT2 sieve census; PCBA catalogs, worked
  board, glossary) written directly. All 76 chapter files pass the
  `sanitize_chapters.py` ASCII/environment/balance checker.
- Depth added over v0.2: tutorial preliminaries (category theory, sheaves,
  finite-function/spectral math, metrology, dose-response, information
  geometry, hardware-description and verification background); complete proofs
  with the seed papers' ledger proof-statuses preserved; per-item treatment of
  every diagnostic code, source conflict, threat, and registered hypothesis;
  implementation documentation of the src modules; worked examples, exercises,
  and reference appendices. Claim discipline unchanged: Ring 4 / NOT LICENSED
  headers, conjectures labeled, bounded-receipt framing, full open-obligation
  sets, and the 64/037,173 new-matter boundary.

## 2026-08-07 — Project Coherence research papers v0.2 (full-length)

- Superseded the five v0.1 white-paper summaries with full-length amsart
  research papers (`docs/whitepapers/tex/RESEARCH_PAPER_*_v0.2.tex`, builds in
  `pdf/`): TKS v8.0 (10pp), Noetic Topos 2.0 (14pp), CAS Core 8 (8pp),
  CAS PCBA 8 (9pp), CAS-Ohm 1.0 (9pp).
- Depth added from the deep sources: NT2 now carries the complete finite-context
  theory — legacy collapse and subcanonicity countermodel proofs, coverage-basis
  lemma, NT2-1..4 with full proofs, explicit reflector construction with the
  universal-property proof, the commuting modality-composition theorem
  (Lemmas 3.1/3.2/4.1, Theorem 5.1 of the registered proof), and the 23-check
  finite certificate (298 sieves / 168 covering / 3,012 restriction squares).
  TKS v8.0 adds full proofs (norm theorem via fiber-block Gram decomposition,
  factorial idempotence, shortlex pruning soundness) and the 11-row obligation
  ledger. PCBA 8 reproduces the per-board EBNF counterexample table with page
  anchors and formalizes CSB fuse unreachability. CAS-Ohm reproduces all eight
  conflicts at evidence-record granularity with source locators and the
  implemented enum catalogs. Core 8 adds a threat-by-threat analysis mapping
  each historical failure class to its blocking mechanism.
- Claim discipline retained everywhere: ledger proof statuses on theorems,
  conjectures labeled as conjectures, Ring 4 / NOT LICENSED headers,
  bounded-receipt framing, and full open-obligation sets.

## 2026-08-07 — Project Coherence white paper series v0.1 drafted

- Drafted five academic-rigor white papers into `docs/whitepapers/` from the
  Project Coherence Gate 1 / Gate 4 sources in the 2026-08-05 Codex snapshot
  (`project_coherence_model_smoke`): TKS v8.0 (typed finite-function kernel),
  Noetic Topos 2.0 (marked/modal successor site), CAS Core 8 (compatibility and
  evidence kernel), CAS PCBA 8 (adaptive cognitive circuit engineering), and
  CAS-Ohm 1.0 (profile-specific experimental response and calibration model).
- Every paper preserves its source's governing status
  (`DRAFT / OPEN / Ring 4 / NOT LICENSED`), exact SHA-256 source identities,
  bounded-evidence receipts (test/exhaustive-case counts, Lean scope), adverse
  findings (legacy topology collapse, CCDL grammar gap, CSB unreachable fuse,
  eight CAS-Ohm source conflicts), and full open-obligation ledgers. Drafting
  promotes no claim; papers note the 64/037,173 new-matter boundary.
- Index with shared conventions at `docs/whitepapers/README.md`.

## 2026-07-28 — Cognitive Circuit Grimoire accepted digital master

- Built and accepted the canonical 6 × 9 inch, 908-page
  `book/cognitive-circuit-grimoire/Cognitive_Circuit_Grimoire.pdf` digital
  master (2,672,454 bytes; SHA-256
  `99AC4170929C48F82C3D2FA81AABA3798C181EF32B3CDCC4C5E7E2D7C52F923D`).
- Completed the split 24-chapter manuscript, 13 appendices, 112 authored
  figures, and 164 worked exercise answers. Added fail-closed structure,
  cross-reference, answer, figure-inventory, standalone-figure, longtable,
  index, glyph, citation, reference, and layout gates to the publishing path.
- The accepted build reports 0 material layout errors, unresolved references,
  unresolved citations, missing glyphs, or rerun warnings. All fonts are
  embedded/subset, and independent text/front-matter inspection found no stale
  markers or orphaned contents entry.
- Marked the pre-existing HTML, EPUB, cover HTML, and monolithic manuscript as
  legacy previews rather than release artifacts.
- Print-production status remains `OPEN`: 908 pages exceeds KDP's current
  828-page 6 × 9 black-ink, white-paper paperback maximum. Closure requires a
  publishing decision between a validated 10-point single-volume reflow and a
  multi-volume split, followed by cover/spine regeneration.

## 2026-07-27 — Gate 2 campaign: root cause found, instrument rebuilt, S3-1 ALL_ROWS_PASS

- **Judge positive control** (`d755665b`): sixteen nulls explained — harness sound (`T0 28/28`),
  authored scenarios carried NO signal (`T2 p = 0.3011`). The owner's 27-section spec repaired it:
  `0.0429 → 0.9167` on the SAME author model (`59e9044c`), with the `56%` World-name leak
  disclosed post-hoc and the drive axis clean (`84/84`).
- **Small-model runs** (`pythia-160m`): `NOT_LICENSED_LEXICAL` twice (`c599273a`, `db948bf1`) —
  above chance, did not beat char n-grams; `world = 0.0000` fold defect fixed by the owner's
  Latin square; both leakage controls (`C-PERM`, `C-BODY`) passed for the first time.
- **Governance:** `CAS_HARNESS_CURRENT_STATE.json` continuation pointer + HISTORICAL SNAPSHOT
  banners (`bed3fc94`); Gate-2 closure contract frozen before any successor number (`17159fce`);
  84-item lane closed against benchmark fitting.
- **Track A:** `PHASE_A_IDENTIFIABILITY_PASS` (`4714fa1a`) — a registered direction works on
  untouched groups (`+1.2500` vs `0.4167` control envelope); effective `n = 6` and the non-zero
  sham floor disclosed. CJT/J-space Phase B unlocked.
- **Track B pilots:** corpora v1/v2 failed authoring yield (World-label leak `18–56%`; cohort
  confound avoided by full regeneration); realization-grammar pilot v1
  `VOID_APPARATUS_PROMPT_CONTAMINATION` (the prompt printed the forbidden word); S2 silent
  enforcement + E-arm universal target-blind instruction → `0.0094`; confirmatory `R1–R6` with
  full byte-replayability logging — low leakage replicates cross-family (`claude-haiku 0.0063`).
- **Attribution chain, one variable at a time:** thin judge key `joint 0.2222` → full canon on
  identical texts `0.6181` (`S3-0`, `536f6a89`) → motive repair with the rejected close rival
  `0.7569`, the campaign's first joint pass; `P74` (generative vs companionship)
  `0.5833 → 0.9375`. **All 13 mechanical rows green**, including `R6` arms regenerated under the
  repaired prompt (`0.0125` / `0.0187`).
- **v3 budget** from the frozen rule (worst-cell Wilson LCB `0.6990`, rule-of-three family
  rejection, sibling dependence): `13` plans/cell → `P(all 28 cells reach 8 families) = 0.9987`,
  `2,912` candidates.
- **Gate 2 remains OPEN at `0.38`.** Next: `TKS_672_V3` lock under the motive-repaired
  instrument, then the small-model readout ladder on the frozen corpus under
  `GATE_2_SUCCESSOR_CLOSURE_CONTRACT` — final equivalence decision is the owner's.
