# RUN RESULT — job c56, HELM-R1 wave 7 v9 "CHAT WAVE" sixth round (sealed package v9, fresh exam, reader v7.2)

## Said plainly first

The sixth round ran once, cleanly, for 0.02 USD. Every instrument row and every hard gate held (verdict `PASS`). Separately, the instrument's scoring code does not do what its own amendment text says (`FLAG_FOR_HUMAN_REVIEW`, end of this paragraph).
The chat got every dialogue right this time: 64 of 64, with 0 wrong and 0 unsure (c55: 62 right, 2 wrong). On the real recipes it got 93
right and 0 wrong, and asked on 15. But two of the six marks failed, so the frozen word is `CHAT_WAVE_HARMED` again. **K3 SAFE failed** on
one wrong lesson: on one recipe the reader tied a "ran out" sentence to the wrong book line, and the brain stored a wrong amount. **K4 HONEST
failed** on one unexplained ask: on one recipe a book line held two amounts, the lessons never taught the second one, and HELM asked. Both
faults appear in exactly the same way in the loop driven directly, with no chat layer, so they come from the wide reader and brain, not the
chat window. ("K3" and "K4" are two of the six marks the frozen reader checks; a "lesson" is one taught amount; an "ask" is HELM saying it
cannot answer without more facts.) **Nothing is licensed. The chat stays `NOT LICENSED`.** One more thing came up: the instrument's own
amendment text (A-R1W7-7, preregistration section 19.1) says an item with a two-amount book line "scores NOT_SCORED", but the code still
scores its question, and that is exactly the item behind the K4 miss. That is a conflict inside the instrument. It is
`FLAG_FOR_HUMAN_REVIEW`, an owner decision. c56's word is not re-scored and stands.

**The frozen reader's words:** verdict **`PASS`** (every instrument row and every hard gate true), status word **`CHAT_WAVE_HARMED`**, reason
`missed: K3_SAFE`, `marks_missed` `["K3_SAFE", "K4_HONEST"]` (`R1_W7_READING.json` sha256
`200a071ecdb6bf9125781fb7c6af66387f0410e85825ddd39d40749bbbd7ff48`, frozen v9 reader `r1w7.merge_r1w7 v2`, run from a fresh extract on the
laptop, 2026-10-21 ~11:39 PDT by file time). The reason names only the first missed mark in the frozen order; the reading lists both.
**Four of six marks true. K3 SAFE false: 0 wrong dialogue answers, 0 wrong noise answers, 0 wrong real-recipe answers, 1 wrong lesson.
K4 HONEST false: 1 unexplained ask (strict rule; the wave-6 rule also reads 1).** Claim ceiling now `SYNTHETIC_ONLY` (unchanged).

## The run

| Item | Value |
|---|---|
| Owner's line | `CHAT WAVE 6 at 1 USD` (20 bytes, sha256 `35620d581402bf19942829e85a8c70b15bf4bdaf853f0ff4775e0de597168ccb`). Pre-approval typed in the forked session (`OWNER_APPROVALS_20261018.md`, heading "2026-10-21, evening Pacific, typed in the forked session"); the owner's own confirmation typed in the operator session at 11:27 PDT: "CHAT WAVE 6 at 1 USD, confirmed against v9 zip sha256 ad3fb98cd3254963263929747791d151949c2f50923672e4bcbf3fc14490942c." |
| Approval record | `approval_v9/APPROVAL_RECORD_R1W7.json` sha256 `e9b197da202af0b22e70fd78ee27028f6c9c1fc59f4ced6b47e7d0786ad32195` / `.md` `7778e503…`; recorded 2026-10-21T18:27:20Z; cap 1.00 USD; one attempt + one plumbing retry; seed source `ee4966de…` (= sha256(line + ":" + zip sha256)) |
| Package (forked session, §7.118, PR #449 merged at `5dcbf23c`) | v9 zip `HELM_R1_W7_20261020_SOURCE_R1W7_v9.zip` sha256 `ad3fb98cd3254963263929747791d151949c2f50923672e4bcbf3fc14490942c` (1,022,659 bytes; 203 members + the freeze); freeze `ce9495fa…`; HELM cut `55cda1e2` (the PR #447 merge: reader `RB-W1 v7.2`, face reader v2.2, OFF pin `79e4914a…`; `CUT_CHECK_W7_v9.json` 167 of 167 equal); exclusion block `X7v8_c55`; bands 2,036 / 2,038 / 2,040 M; the seal's host-list run `Ran 280 tests`, `OK (skipped=1)`; practice run11 0 WRONG in every dialogue family, every mark true, 0 numbers moved against v8's run10 (limit: the practice draw holds none of c55's shapes) |
| Operator checks at reading (`OPERATOR_I_CHECKS_C56.json` `aeacd544…`) | 19 named checks true (zip, freeze, approval, owner line bytes and sha256, seed recomputed, approval binds zip and freeze, manifest, carrier pins and zip, sealed handoff, receiver check, carrier holds no key, c47/c50 readings present, host index present, neighbours extracted by hash, freeze members ok) + freeze member count 203 |
| Custodian (separate agent, laptop, 0 USD) | `x7v9_custody/X7_SEALED_20261021T183417Z.json` `5f3c40a7…`; `MANIFEST_X7.json` `1d7b7a68…` (sealed 18:32:07Z); `RECEIVER_CHECK_X7.json` `f84908f0…` (23 of 23); carrier `X7_CARRIER_V1.zip` `91146277…` (40,011 bytes, 4 members); X7_REAL 128 (ANSWER keys 108, representable-and-answer 91, undetermined keys 20 of which 13 same-name), X7_CONV 64 (13 families; ANSWER 30 / ASK 30 / LEARN 4), X7_NOISE 64 + 128 noise turns; overlap with all 24 exclusion lists 0 and 0 (`EXCLUSION_OVERLAP_CHECK_X7v9.json` `7a02bbc6…`, 2,234 distinct ids, block `X7v8_c55` included); `seed_overlap_check` PASS. Seal attempt 1 refused before any output (`PinRefused`: neighbour packages not extracted, `pkg/deps/` absent; step 1 of the custodian procedure was not in the operator's brief); the five neighbour zips were then extracted and re-hashed against their pins; the seal ran once more and printed all_pass true |
| Payload | `make_c56_kit.py` (`4b6e0147…`, derived from `make_c55_kit.py`); `c56-payload.zip` `7d79bef6…` (5,658,372 bytes; 1,145 inventory members plus `payload_inventory.json`, 1,146 zip entries; `validate_plan` True); budget hold reservation `168ec55d…` (113.32 → 114.32 combined, 85.68 unreserved); transport lease written; pre-launch checklist 11 of 11 PASS (`PREFLIGHT_CHECKS_C56_a1.json` `98b49b29…`; checks 1–10 plus 9b); controller preflight cautious upper 0.213096 USD |
| Attempt 1 (the only one) | `i-02cf9b78be48d55b5`, m6i.xlarge, us-west-2b, launched 18:35:49Z (AWS launch time); `SUPERVISOR_ALL_STAGES_PASS`; deliverable 999,469 bytes, sha256 `f9b10c64…`, `DOWNLOADED_AND_VERIFIED` 18:38:27Z; terminated on request (AWS: "User initiated (2026-10-21 18:38:27 GMT)"); `R1_W7_HOST.json` `27903f6f…` (14 of 14 units exit 0 in 19.58 s, no instrument problem); `RUN_RECORD.json` `3038edf0…`; HELM suites (12 files) Ran 280, OK (skipped=2); wave-7 suites Ran 41, OK (skipped=1); cleanup three ways: controller `PRESERVED_AND_PREFIX_PURGE_VERIFIED` (root volume deleted, 4 prefix versions purged, 0 multipart), independent `VERIFIED`, direct read-only (instance terminated, no live instance with the tag, no volume, no prefix version, no delete marker, no multipart upload) |
| Reading | `R1_W7_READING.json` `200a071ecdb6bf9125781fb7c6af66387f0410e85825ddd39d40749bbbd7ff48`; merge input `a709e93f…`; instrument rows all hold; hard gates all hold; verdict `PASS`; word `CHAT_WAVE_HARMED`; claim ceiling now `SYNTHETIC_ONLY` (unchanged) |
| Cost / ledger | 0.02 USD charge (180.650374 s host; list 0.010106; cautious 0.03); hold → charge; ledger 114.32 → 113.34 combined, 86.66 unreserved of 200 (`AWS_COMBINED_ALLOCATION_CURRENT.json` = ledger after `81f0b6f6…`); `CLEANUP_PROOF_R1W7V9_C56.json` `bf71f8f0…`; addendum `BUDGET_RECONCILIATION_ADDENDUM_CLAUDE_R1W7V9_C56_20261021T184127Z.json` `06a17226…` |
| Backup | `D:/tksCAS-archive/r1_wave7_c56_20261021/` 120 files, 15,974,016 bytes, three passes (source sha256; destination re-read, 0 mismatches; whole tree), tree `366b2a20…` |

## The reading (facts, every number exact)

**Instrument rows:** all hold (I0, I1, I6, I7, I9, I10, I12, I14, receiver check, receiver counts). **Hard gates:** all hold (HG1–HG10).

| Mark | Reading |
|---|---|
| K1 LEARNS | fully learned 91 of 91 representable ANSWER-keyed recipes (bar 82) ✓ |
| **K3 SAFE** | **conv_wrong 0, noise_wrong 0, real_wrong_answers 0, real_wrong_lessons 1 → FALSE** |
| **K4 HONEST** | **unexplained asks 1 (strict) / 1 (wave-6 rule); unrouted scored turns 0; unsettled-ask fired 0 → FALSE** |
| NH-CHAT | lost vs LOOP_ON: REAL 0 (93 vs 92, gained 1: `RW:wb:119935:4522469`), CONV 0 (64 vs 61, gained 3) ✓ |
| P PLAIN | RIGHT_AND_PLAIN = RIGHT on both exams (93 = 93; 64 = 64); right-not-plain ids none ✓ |
| N NOISE | lost to small talk 0 (CONV 64, NOISE 64); misrouted scored turns 0; 128 noise turns ✓ |

**Totals, CHAT_ON:** X7_REAL 128: RIGHT 93, WRONG 0, ASKS 15 (1 unexplained), NOT_SCORED 20, RIGHT_AND_PLAIN 93, fully learned 91 of 91, lessons
LEARNED 554 / NOT_LEARNED 128 / WRONG 1 (683 lessons), commitments on undetermined-key items 15 (same-name 9). The question score covers every
ANSWER-keyed item: 93 + 0 + 15 = 108 = the ANSWER keys, while representable-and-answer is 91. X7_CONV 64: RIGHT 64, WRONG 0, UNDETERMINED 0.
X7_NOISE 64 (+128 noise turns): RIGHT 64, WRONG 0, UNDETERMINED 0, misrouted 0, noise replies with CAS tokens 0. Stock turns (REAL):
STOCK_RECORDED 110, INVENTORY_RECORDED 1, CLARIFY_ENGLISH_UNKNOWN_INGREDIENT 12, CLARIFY_ENGLISH_NO_INGREDIENT_NAMED 4, CLARIFY_NOT_CCE 1;
stock recorded but reply says "don't know" 0. Tool-engine turns 0 in every chat unit; agentic turns 0.

**Yardsticks:** CHAT_OFF (the chat with the wide brain switched off, `HELM_WIDE_BRAIN=0`, D-W7-2): REAL RIGHT 0, ASKS 108, NOT_SCORED 20, lessons NOT_LEARNED 683; CONV RIGHT 27, UNDETERMINED 37,
WRONG 0. LOOP_ON: REAL RIGHT 92, ASKS 16, unexplained 1, lessons LEARNED 545 / NOT_LEARNED 137 / WRONG 1; CONV RIGHT 61, WRONG 0,
UNDETERMINED 3. ALWAYS_ASK: ASKS 108, NOT_SCORED 20. CHAT_DIAG = CHAT_ON; REPLAY = CHAT_ON. CHAT_ON minus CHAT_OFF: +37 right on dialogues,
+93 right on real recipes.

**By family, CHAT_ON (the reader's `conv_by_family`):** every family all right: R1 14/14, R2 4/4, R3 4/4, R4 4/4, R5 4/4, R7 2/2, S1 6/6,
S2_POWER_STATED 6/6, S3 6/6, S4 4/4, S5_INGREDIENT_PURPOSE_ABSENT 4/4, S6 2/2, S7 4/4. **`not_right_ids` X7_CONV CHAT_ON: none.** LOOP_ON's 3
undetermined: `CV30:pg:42868@202788`, `CV31:pg:31534@102149` (R7_NEXT_SESSION) and `CV59:pg:70067@84771` (S6_TWO_FACES); the chat got all
three right.

## The two faults (custodian's per-item verdicts and mechanism; frozen functions; names hashed; laptop, 0 USD)

Per-item verdicts `CUSTODIAN_PER_ITEM_VERDICTS_C56.json` `d2f53886…` (script `per_item_verdicts_c56.py` `d474de09…`): for every REAL arm, eight
counts (RIGHT, WRONG, ASKS, NOT_SCORED, lessons LEARNED / NOT_LEARNED / WRONG, unexplained_asks_strict) agree three ways: frozen totals,
item-by-item recount, and the reading. All 9 unit files read matched the host index by its pinned hash. Mechanism files
`CUSTODIAN_SHAPE_FACTS_C56.json` `bfaebc3d…` and `CUSTODIAN_SHAPE_FACTS_C56_MECHANISM.json` `de0817f6…` (scripts `shape_facts_c56.py`
`23cf4c7e…`, `mechanism_c56.py` `cc807b71…`). The two faults sit on two different items (`same_item_behind_both` false).

- **The wrong lesson (K3):** item `RW:pg:65061@573841` (cell C710:MIXED, 7 lessons), lesson index 0, HELM status `WITNESS_ADMITTED`; the same
  lesson is WRONG, with the same name hash and the same learned value, in CHAT_ON, CHAT_DIAG, CHAT_ON_REPLAY and LOOP_ON. The item's key is
  same-name (UNDETERMINED), so its question is NOT_SCORED, but its lessons are scored, so K3 counts it. Mechanism: book line 0 ends with a
  dangling "or" (the first half of an alternative pair); line 1 names the same ingredient in another unit (the two lines' unit words differ). HELM's `parse_line` keeps the "or" as the last word of line 0's name (its alternative rule splits only on "or" with a word after
  it). The ran-out phrase was the bare shared head word. `resolve_ran_out` found no exact name, no unit word to drop, 0 starts-with
  candidates and exactly 1 ends-with candidate, line 1, and bound line 0's running-out to line 1. The own-words step, which would have seen
  2 candidates and left it unbound, was never reached. The brain stored line 1's batch amount as the requirement, in line 1's unit: learned / key =
  7 against line 0's key amount (a cross-unit ratio, because line 0's unit differs), 2 against line 1's own key amount. Knock-ons
  (HELM status words): lesson 1 `TEACH_REFUSED_REFUSED_CONFLICT`; lessons 2 to 6 `TEACH_REFUSED_RECEIPT_FAILED`; all six NOT_LEARNED
  (the brain replay's reasons are `REFUSED_CONFLICT` and `RECEIPT_FAILED`). A replay by program with the dangling "or" removed (nothing re-scored) binds by exact name to line 0. **A reader miss,
  not an honest outcome: a wrong amount really was written into the brain.**
- **The unexplained ask (K4):** item `RW:pg:6912@197664` (cell C23:FRACTION, key ANSWER, 3 lessons all LEARNED, stock `STOCK_RECORDED`),
  HELM status `UNDETERMINED_CLARIFY` in CHAT_ON, CHAT_DIAG, CHAT_ON_REPLAY and LOOP_ON (LOOP_ON has no chat layer, so the ask comes from the
  loop and brain). Mechanism: book line 0 holds two amounts joined by "and" (the frozen MULTI_QTY rule fires on line 0); the key keeps one
  line; the v7.2 split reads 4 lines; the second ingredient of line 0 (hash `08a286`) is never the ran-out ingredient and never taught, so
  the brain's gate reads G1 (1 unlearned), the RPM request has 1 unsatisfied requirement, and the question asks. **Honest in substance: no
  exact yield can be computed.** By the frozen strict rule it counts as unexplained: all four conditions hold (key ANSWER, 3 of 3 lessons LEARNED,
  `STOCK_RECORDED`, question ASKS). K4 reads the strict count, which has no exemption (D-W7-9). The D-W6-12 artifact-caution
  exemption touches only the wave-6-rule count reported beside it, and it would not apply here either (no unsettled-same-name ask;
  `head_artifact` false). This is the c54 shape again.
- **Instrument conflict (`FLAG_FOR_HUMAN_REVIEW`, an owner decision, not a custodian or operator decision):** the item carries the
  A-R1W7-7 tag `line0:MULTI_QTY` (representable = false). Preregistration section 19.1 says such an item "scores `NOT_SCORED`". The code
  (`r1w7/multi_qty_w7.apply`) only sets representable = false and leaves the answer word ANSWER; `score_question` and `unexplained_ask` never
  read representable. So c56's one unexplained ask is an item whose question the amendment's text meant to leave unscored. Section 19.1 also
  says not-representable recipes already score `NOT_SCORED`; on c56 the question score covered all 17 not-representable ANSWER
  keys (15 ASKS, 2 RIGHT), so every one of the 15 asks sits on a not-representable item. Not re-scored here; c56's word stands.
- **Builder's error, on the record (verified by the operator in the frozen code):** amendment A-R1W7-7 and its text in section 19.1
  were written and built by this operator session (§7.111). The text's premise, that not-representable recipes "already" score
  `NOT_SCORED`, is false in the frozen code: `rbw1t.keys_rbw1t.score_question` returns `NOT_SCORED` only when the key's answer word
  is not ANSWER and never reads `representable`; `r1w6.score_w6.score_real` uses it only for K1's bar (`rep_answer`,
  `fully_learned_rep`); the strict K4 count never reads it. So the amendment as built changed only K1's bar, and the "would have
  been `NOT_SCORED`" effects written in §7.111 and section 19.4/19.5 were wrong as stated. The miss is the builder's. Every earlier
  reading stands as read; nothing is re-read.

## What reader v7.2 did on this sealed draw

- Dialogue wrong answers: **0** (c55: 2). X7_CONV CHAT_ON 64 / 0 / 0; X7_NOISE CHAT_ON 64 / 0 / 0; S2_POWER_STATED 6/6 and
  S5_INGREDIENT_PURPOSE_ABSENT 4/4 (the two families c55 missed). This is a fresh draw, so this fact alone does not show which rule caused
  it; whether v7.2's new codes fired on any dialogue item was not counted.
- On the two real-recipe faults, **none of v7.2's rules fired** (custodian mechanism facts): no `FACE_UNKNOWN_*` code on any turn of these two items in any
  arm (real-recipe turns carry no clause); the measure-phrase own-line branch (`VAGUE_AFTER_A` in `starts_line`) decided 0 pieces in
  all 10 lesson sentences of the two items (7 + 3); own words equal said words on every line, so the own-words-only ran-out rule changed nothing. The wrong binding was
  decided earlier, at the ends-with step.
- The v9 cut `55cda1e2` predates PR #448 (memory compaction build v1, merged after it as `64e53842`). **c56 does not exercise the memory
  compaction code.**

## Reported facts, not gates

- **Host test skips.** The host's 12 HELM files: `Ran 280 tests`, `OK (skipped=2)`. Skip 1:
  `test_helm_brain_wide.H_SwitchOff.test_licensed_files_untouched` ("base commit not reachable in this checkout"), the same skip as at the
  seal. Skip 2: `test_helm_english_in.TestRoundTrip.test_borrowed_word_lists` ("lexicon_v2 needs sdg_bridge_v2 on the path
  (language_v3/PROVENANCE.md)"); this test was not skipped at the seal (`TEST_COUNTS_R1W7_v9.json` lists only skip 1, `OK (skipped=1)`).
  Wave-7 suites on the host: `Ran 41`, `OK (skipped=1)` (`tests_r1w7.test_units_w7.Practice.test_practice_draw_rederives_the_published_pools`,
  "neighbours or frames not present (laptop only)"); at the seal `Ran 41`, `OK`. c55's host logs show the same two HELM skips
  (`Ran 273`, `OK (skipped=2)`) and the same wave-7 skip (`Ran 41`, `OK (skipped=1)`), although §7.116 wrote "HELM suites Ran 273
  OK (skipped 1), wave-7 suites Ran 41 OK", `RUN_RESULT_R1W7V8_C55.md` wrote "HELM suites (12 files) Ran 273, OK (skipped 1);
  wave-7 suites Ran 41, OK", and `TEST_COUNTS_R1W7_v9.json` (`c55_host_for_comparison`) records only the HELM list, as
  `skipped=1` (it has no wave-7 entry).
- **Stale labels (text only; the checked values are right):** the controller's purpose string in `aws-c56-a1-control.json` says "HELM cut
  dfc7158d = PR #416" (carried from the template; c55's control has the same text); the run record and the reading's I1 show the real cut
  `55cda1e2`, 167 files. The backup manifest's skip reason names a payload sha256 `26ca58af…`; the c56 payload is `7d79bef6…`. The
  pre-launch log prints "ALL 10 PRE-LAUNCH CHECKS PASS" over 11 listed checks (1–10 plus 9b).
- **One controller read error, no effect:** at 18:35:50.143883Z, 0.096 s after the controller's `LAUNCHED` event (18:35:50.048Z), `DescribeInstances` returned `InvalidInstanceID.NotFound`
  (event `CONTROL_ERROR`); the run went on and every later stage passed.
- **Backup gap:** the backup ran at 18:41:35Z. The three custodian diagnosis files (`CUSTODIAN_PER_ITEM_VERDICTS_C56.json` 18:52:08Z,
  `CUSTODIAN_SHAPE_FACTS_C56.json` 19:06:09Z, `…_MECHANISM.json` 19:06:16Z) were written later and are not yet in the archive.
- **Owner-words heading:** the pre-approval heading reads "evening Pacific", but it comes before the 11:27 PDT confirmation in the same
  file and refers to v9 as "not yet built". Recorded as written.

## Negatives kept

1 wrong lesson of 683 (a real wrong amount stored); 1 unexplained ask by the frozen rule (honest in substance; instrument conflict flagged);
128 of 683 lessons not learned on CHAT_ON (6 of them the knock-ons on `RW:pg:65061@573841`); 15 commitments on undetermined-key items
(same-name 9; D-W7-6); 15 asks on real recipes: 1 unexplained by the strict rule, and the other 14 each have at least one lesson not learned (13 of
them also without the stock recorded), so the strict rule does not count them (0 used the D-W6-12 exemption); LOOP_ON still undetermined on 3 dialogues. §7.116's c55 record
stands.

**Six draws, six readings (facts, not a trend):** c51 `FAILURE` / `INCONCLUSIVE`; c52 `PASS` / `CHAT_WAVE_NO_GAIN` (1 ask); c53 `INSTRUMENT_ERROR` /
`INCONCLUSIVE`; c54 `PASS` / `CHAT_WAVE_NO_GAIN` (2 asks); c55 `PASS` / `CHAT_WAVE_HARMED` (2 wrong, 1 wrong lesson); c56 `PASS` /
`CHAT_WAVE_HARMED` (0 wrong answers,
1 wrong lesson, 1 unexplained ask). REAL right 96 / 91 / 99 / 91 / 93 / 93; unexplained asks 0 / 1 / 0 / 2 / 0 / 1; CONV right 44 / 44 / 43 /
44 / 62 / 64; CONV undetermined 20 / 20 / 21 / 20 / 0 / 0; CONV wrong 0 / 0 / 0 / 0 / 2 / 0. (§7.116's "of 97 / 94 / 101 / 94 / 94" are
representable-and-answer counts; c56's is 91; the question score itself covers every ANSWER key, 108 on c56.)

## Next (PROPOSED only; Claude is not the research governor; nothing here is approved)

1. **FIX FIRST, tests first, 0 USD, laptop** (the custodian's proposed general rules, not built): (a) a line ending in a dangling "or" is an
   alternative that continues on the next line; "or" never stays inside a name; the pair is one ingredient with an alternative, and a batch
   or stock that relies on it asks which one was used; (b) in `resolve_ran_out`, check ambiguity before any one-candidate step that is not
   an exact match: no exact name and the phrase's words in the own words of two or more lines → ask (refuse), never bind by starts-with or
   ends-with; an exact match still binds ("sugar" beside "brown sugar").
2. **The instrument conflict goes to the owner** (`FLAG_FOR_HUMAN_REVIEW`): either make A-R1W7-7 do what section 19.1 says (an ANSWER key
   with representable = false because of MULTI_QTY scores `NOT_SCORED` for its question and is left out of K4's strict count; the
   wider version, every ANSWER key with representable = false, would move 17 c56 items: 15 ASKS and 2 RIGHT), or add a frozen
   exemption to K4's strict count for an ANSWER key tagged `line<i>:MULTI_QTY` (today the strict count has no exemption; D-W6-12
   applies only to the reported wave-6-rule count). Only by the owner's word, as an amendment, for a fresh draw only. Keep scoring lessons on same-name items (K3 should see a wrong
   amount written into the brain).
3. Then a v10 reseal on the forked session's process (an exclusion block for c56's exam ids, fresh bands, a practice run from the seal),
   and a fresh draw only on a line the owner types. No such line exists; nothing here approves one.

**`NOT LICENSED`:** the chat on any exam; "the chat works"; reader v7.2 on any exam (stays `ENGINEERED-NOT-VALIDATED`); §7.98's "what a pass
would license".

## Files

`run_c56_r1w7v9_20261021/` (reading, merge input, operator checks, `CUSTODIAN_PER_ITEM_VERDICTS_C56.json`, `CUSTODIAN_SHAPE_FACTS_C56*.json`,
`deliverable_unpacked_a1/`, `payload_c56/`, `job_record/` with every receipt, `CLAUDE_R1W7V9_C56_TRANSPORT_LEASE.json`, `backup_c56.py`);
`x7v9_custody/` (handoff, manifest, receiver check, carrier, both seal attempts' logs, `diag/`; `out/exam/` laptop-only, never opened by the
operator); `approval_v9/`; `make_c56_kit.py`, `C56_VALUES.json`, `build_payload_c56.py`, `preflight_checks_c56.py`, `unpack_and_read_c56.py`;
`build_v9/` (the forked session's seal).
