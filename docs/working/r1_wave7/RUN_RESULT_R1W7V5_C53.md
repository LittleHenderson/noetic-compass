# RUN RESULT — job c53, HELM-R1 wave 7 v5 "CHAT WAVE" third round (sealed package v5, fresh exam)

**The frozen reader's words:** verdict **`INSTRUMENT_ERROR`**, status word **`INCONCLUSIVE`** (`R1_W7_READING.json` sha256 `c0362a6b72260a7dd6c703daa1545119f57732bcbe1d69688917c02efc23b4fe`,
reader of the sealed v5 zip `4b54a077…` run from a fresh extract on the laptop, 2026-10-20 ~11:12 PM PDT). Failing instrument row:
**I6 completeness, part `suites_ok` false** — HELM's own unit-test suites on the host ran 236 tests and 1 failed. Every other I6 part true
(14 of 14 units exit 0, deadline not hit, the frozen unit list, every unit file present, every arm every item). Every other instrument
row true. **All 10 hard gates true** (HG5: 14 of 14 lists present, 0 missing). **All six marks true as facts**, K4 included: 0 unexplained
asks — the round-3 fix removed the ask that cost c52 its word. Under the frozen order an instrument row false reads `INCONCLUSIVE`.
**Nothing is licensed; the chat stays `NOT LICENSED`.**

## Said plainly

HELM's chat did everything the wave asks on this fresh exam: 99 of 101 scorable real recipes right with 0 wrong, 100 of 101 fully learned,
0 asks without a reason, 43 of 64 dialogues right with 0 wrong, nothing lost to the loop driven directly or to small talk, every right
answer plain, no shell command. The sandbox gate held. But one of HELM's own unit tests failed on the machine, and the pre-registered rule
says the run's data counts only if HELM's suites pass there. The test that failed is a byte pin from PR #417: with the receipt-address
switch off, the loop's records must hash to a value recorded on the laptop. On the laptop that test passes on the very same sealed code
(Windows, Python 3.14) and on the thread head's code; on the machine (Ubuntu, Python 3.12.3) the records hashed differently. So the pin
depends on the environment, not on the round-3 fix. The test had never run on a host before: the c51 and c52 cuts predate PR #417, and
the v5 cut rule pulled it into the host's suite list for the first time; the builder's seal record ran "HELM's 8 unittest files", the host
ran 10 (236 tests). **A failed instrument row is `INSTRUMENT_ERROR`; the word stands.**

## The run

| Item | Value |
|---|---|
| Owner's line | `CHAT WAVE 3 at 1 USD` (20 bytes, sha256 `2be24e3b…`), typed in the launching session 22:35 PDT before the seal with scope "the v5 seal built from the third chat round order"; `approval_v5/APPROVAL_RECORD_R1W7.json` `82ad99b3…` / `.md` `185570ec…`; seed source `2deb2f5b…` |
| Package | v5 zip `build_v5/HELM_R1_W7_20261020_SOURCE_R1W7_v5.zip` `4b54a077e4b2963301451c6eb78836a32d9797460cd8143d3cf2f9efdc1a7cf8` (980,035 bytes), freeze `8cc543d2…` (198 members), HELM cut `f45a8570` (164 files: the round-3 fix in `helm_wide_turn.py`, a condition amount such as "350 degrees Fahrenheit" in a comma list is a note, never an ingredient; 3 class-G tests), `helm_brain_canonical.py` = base; built by the forked session (PR #425, §7.105); amendment A-R1W7-5; bands REAL 2,006 M / CONV 2,008 M / NOISE 2,010 M; exclusion blocks `X7_c51_*`, `X7v4_c52_*` |
| Operator verification of the seal | zip and freeze hashes match; 198 of 198 members; cut 164 of 164; `validate_plan` True on the stage; `OWNER_LINE` pinned; bands and exclusions as stated; pre-code bytes intact at the head of the preregistration |
| Custodian (separate agent) | `x7v5_custody/X7_SEALED_20261021T060622Z.json` `741b38cf…`; `MANIFEST_X7.json` `619499ab…`; `RECEIVER_CHECK_X7.json` `9792ac8d…` (23 of 23 true); carrier `72fa5b77…`; X7_REAL 128 (ANSWER-keyed 109, representable 101, undetermined keys 19 of which 14 same-name), X7_CONV 64 (13 families; ANSWER 30 / ASK 30 / LEARN 4), X7_NOISE 64 + 128 noise turns; 0 overlap with all 18 exclusion lists incl. both spent exams |
| Payload | `c53-payload.zip` `c11842fb…` (1,140 members), plan validated with the host's supervisor bytes before upload; DeepSeek checklist lines 1–10 as programs all PASS; AWS preflight OK |
| Attempt 1 | `i-05af29e6945329d29`, m6i.xlarge, us-west-2, 06:08:14Z–06:10:42Z; `SUPERVISOR_ALL_STAGES_PASS`; deliverable `4198bd42…` (979,387 bytes); `R1_W7_HOST.json` `842cd7e6…`; `RUN_RECORD.json` `f9cb2dc1…`; wave-7 suites 34 OK (1 skipped); **HELM suites Ran 236, FAILED (failures=1, skipped=2)**; 14 of 14 units exit 0 in 18.63 s; one transient describe error right after launch, recovered; cleanup proven three ways (`a33c467e…`, `55f675e5…`, `d919ecca…`) |
| Reading | `R1_W7_READING.json` `c0362a6b72260a7dd6c703daa1545119f57732bcbe1d69688917c02efc23b4fe`; `MERGE_INPUT_R1W7.json` `fc5f7e47…`; `OPERATOR_I_CHECKS_C53.json` `d4376f1b…` (all true, 198 members); verdict `INSTRUMENT_ERROR`; word `INCONCLUSIVE`; claim ceiling now `SYNTHETIC_ONLY` (unchanged) |
| The failed test | `test_helm_cas_address.C_LoopStamps.test_off_is_byte_identical_to_the_pre_change_code`: `6bf323ad…` != pinned `56f356ea…` ("OFF records differ from the pre-change code (base 159c7d2b)"); laptop (Windows, Python 3.14) from the same sealed `helm_now/`: **OK**; thread head `1d2b390f`: **OK**; host (Ubuntu 24.04, Python 3.12.3): **FAIL** → environment-dependent pin |
| Cost / ledger | 0.02 USD list (180.91 s; cautious 0.03); hold 1.00 consumed → charge; ledger 114.26 → 113.28 combined, 86.72 unreserved of 200; `CLEANUP_PROOF_R1W7V5_C53.json` `787a65c6…`; addendum `…_20261021T061222Z.json` `805a018f…` |
| Backup | `D:/tksCAS-archive/r1_wave7_c53_20261020/` 122 files, three sha256 passes, tree `2a202ea4…` |

## The reading (facts, every number exact; nothing licensed because the verdict is INSTRUMENT_ERROR)

**Instrument rows:** I0, I1, I7, I9, I10, I12, I14 true; **I6 false** (`suites_ok` false; the other five parts true).
**Hard gates (10 of 10 true):** HG1–HG10, HG5 with the wave-1 tree hash equal at start and end, canonical brain equal to base, 14 of 14 units'
lists present and empty, 10 of 10 chat units' session logs under scratch.

| Mark | Reading |
|---|---|
| K1 LEARNS | fully learned 100 of 101 (bar 91) ✓ |
| K3 SAFE | 0 wrong answers, 0 wrong lessons, 0 wrong (CONV), 0 wrong (NOISE) ✓ |
| K4 HONEST | unexplained asks 0 (strict) / 0 (wave-6 rule); unrouted 0; UNSETTLED_ASK fired 0 ✓ |
| NH-CHAT | lost vs LOOP_ON: REAL 0 (99 vs 97; gained `RW:pg:42868@215943`, `RW:pg:49958@589554`), CONV 0 (43 vs 41; gained `CV30`, `CV31`) ✓ |
| P PLAIN | RIGHT_AND_PLAIN = RIGHT (99 = 99; 43 = 43) ✓ |
| N NOISE | lost 0 (CONV 43, NOISE 43); misrouted 0; 128 noise turns ✓ |

**Totals, CHAT_ON:** X7_REAL 128: RIGHT 99, WRONG 0, ASKS 10, NOT_SCORED 19, RIGHT_AND_PLAIN 99, fully learned 100 of 101, lessons NOT_LEARNED
70, commitments on undetermined-key items 14. X7_CONV 64: RIGHT 43, WRONG 0, UNDETERMINED 21. X7_NOISE 64 (+128 noise turns): RIGHT 43,
WRONG 0, UNDETERMINED 21, misrouted 0. Stock turns (REAL): STOCK_RECORDED 114, CLARIFY_ENGLISH_UNKNOWN_INGREDIENT 10,
CLARIFY_ENGLISH_NO_INGREDIENT_NAMED 2, CLARIFY_ENGLISH_NO_STOCK_FRAME 1, INVENTORY_RECORDED 1. Tool-engine turns 0 in every chat unit.

**Yardsticks:** CHAT_OFF: REAL RIGHT 0, ASKS 109, lessons NOT_LEARNED 673, unrouted 3; CONV RIGHT 28, UNDETERMINED 36, misrouted 9, unrouted 8.
LOOP_ON: REAL RIGHT 97, fully learned 98, ASKS 12, unexplained 0, NOT_LEARNED 88; CONV RIGHT 41, UNDETERMINED 23. CHAT_DIAG = CHAT_ON (HG7);
CHAT_ON_REPLAY = CHAT_ON (HG2).

**Negatives kept (CHAT_ON):** 21 of 64 dialogues UNDETERMINED: S1 6, S2 6, S7 4, S6 2, R4 2, R3 1 (the known face/purpose-clause and past-tense
paraphrase gaps, plus one R3 question form this draw); 70 of 673 lesson lines not learned; 14 definite answers on undetermined-key items
(D-W7-6). **The three runs on three draws (facts, not a trend):** REAL right 96 / 91 / 99 of 97 / 94 / 101 scorable; unexplained asks 0 / 1 / 0;
CONV right 44 / 44 / 43; the instrument failed in c51 (reader) and c53 (a HELM test pin on the host), the marks held in all three.

## Files

`Documents/Codex/2026-10-20/r1_wave7/run_c53_r1w7v5_20261020/` (reading, merge input, operator checks, `deliverable_unpacked_a1/` with
`unittest_helm.log`, `payload_c53/`, `job_record/` with every receipt and `PREFLIGHT_CHECKS_C53_a1.json`, `backup_c53.py`);
`x7v5_custody/` (handoff, manifest, receiver check, carrier; `out/exam/` laptop-only); `approval_v5/`; `make_c53_kit.py`, `C53_VALUES.json`;
`build_v5/` (the forked session's seal: zip, freeze, `TEST_RECORD_R1W7.md`, `K4_ITEM_DIAGNOSIS.md`, `AMENDMENT_A_R1W7_5.md`).
