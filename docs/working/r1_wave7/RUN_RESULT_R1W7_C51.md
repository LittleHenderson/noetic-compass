# RUN RESULT — job c51, HELM-R1 wave 7 "CHAT WAVE" (sealed package v3, exam X7)

**The frozen reader's words:** verdict **`FAILURE`**, status word **`INCONCLUSIVE`** (`R1_W7_READING.json` sha256 `8f2f76468fef11e4d755083d2581578e04466e0d028a92848c8019ad945a5d4d`,
reader `r1w7.merge_r1w7 v1 (2026-10-20)` run from a fresh extract of the sealed zip `5063baba…` on the laptop, 2026-10-20 ~8:05 PM PDT).
A failed hard gate is a FAILURE. Nothing from this run is licensed. The chat's claim status is unchanged: **NOT LICENSED**.

## Said plainly

The chat test ran on one AWS machine, twice. The first try died in plumbing before any test or unit ran (the sealed stage plan's
empty `pythonpath` list is refused by the run-proven supervisor; operator fix D-OP-C51-1 in the job plan only). The second try
ran everything: HELM's own suites (201 OK), the wave-7 suites (31 OK), all 14 units (14 of 14 exit 0, 15.89 s). The frozen reader
then read every instrument row true, **every one of the six marks true**, and 9 of the 10 hard gates true. **HG5 (the sandbox gate)
read false**, so the verdict is `FAILURE` and the word is `INCONCLUSIVE`.

**Why HG5 read false (found after the reading, by inspection; it changes no word):** HG5's row `helm_now_files_changed` demands a list
from every one of the 14 units and requires each list to be empty. Thirteen units write that list, and all thirteen are empty. The
fourteenth, the recorder-equality unit (`W7_RECORDER_EQUALITY`), never writes the field at all (`r1w7/units_w7.py` recorder command;
`chat_harness.py` writes it only for chat arms and loop arms), so the reader sees `None`, and `None == []` is false. The package's
own test fixture (`tests_r1w7/fixture_run.py` line 261) gives the synthetic recorder unit `"helm_now_files_changed": []`, so every
planted-failure test of HG5 passed while the real gate can never hold. The other three HG5 rows all show no breach: the wave-1 brain
folder hash is the same at start and end (`65795c8c…`), `helm_brain_canonical.py` equals its base, and every chat unit's session
log sits under its own scratch. The practice reading (`dry_run/run5_v3_from_seal`) also read HG5 false, hidden behind
`INSTRUMENT_ERROR` on the practice mock, so the builder never saw HG5 hold. **This is a defect of the frozen reader and the recorder
unit's record, not of HELM, and not a sandbox breach.** The preregistration (line 4: "no one re-reads them after the data exists")
forbids re-reading this data with a repaired reader; the word stands.

## The two attempts (controller `aws_control_c51.py`, run-proven kit by substitution)

| | Attempt 1 | Attempt 2 (plumbing retry, same hold, same zip, same carrier) |
|---|---|---|
| Payload | `c51-payload.a1_PLAN_INVALID.zip` sha256 `7268c6f1…` (1,136 members) | `c51-payload.zip` sha256 `ed3072f5…` (1,136 members; only `execution/job_plan.json` and `payload_inventory.json` differ: stage `pythonpath` = `["HELM_R1_W7_20261020"]`, D-OP-C51-1) |
| Instance | `i-05ec6cdce28860185`, m6i.xlarge, us-west-2, launched 02:55:10Z, terminated 02:56:34Z | `i-0a89f8a7d01f46ace`, m6i.xlarge, us-west-2, launched 03:00:24Z, terminated 03:02:41Z |
| Host result | `SUPERVISOR_NONZERO`, exit 1: `ValueError: PLAN_INVALID:r1w7_host_run:pythonpath` before any stage; 0 units started; deliverable 1,819 bytes (`a98b8140…`) | `SUPERVISOR_ALL_STAGES_PASS`; deliverable 973,273 bytes (`1180e0b5…`); `R1_W7_HOST.json` `525156dc…`; `RUN_RECORD.json` `4cd0184d…` |
| Cleanup | controller `PRESERVED_AND_PREFIX_PURGE_VERIFIED` (`1a608ab7…`); independent `VERIFIED` (`9d37ff53…`); direct look: terminated, 0 volumes, 0 objects (`7cd0d712…`) | controller `PRESERVED_AND_PREFIX_PURGE_VERIFIED` (`3c3f3ab0…`); independent `VERIFIED` (`fe585f97…`); direct look: terminated, 0 volumes, 0 objects (`ddd59e0c…`) |
| Billable basis | 107.262583 s → 0.006 USD raw, 0.01 rounded up | 160.151385 s → 0.008959 USD raw, 0.01 rounded up |
| Note | the controller's first `launch 1` call refused itself (`WATCHDOG_NOT_READY`: the watch process must run first); no AWS call was made; logs kept as `launch_a1_refused_no_watchdog.*` | one transient `CONTROL_ERROR` at 03:00:24Z (`InvalidInstanceID.NotFound` on the first describe right after `run_instances`); the controller continued and every later step succeeded |

**Charge:** 0.02 USD at list price for both attempts (cautious 0.05 USD), against the 1.00 USD hold; ledger 114.23 → 113.25 USD combined,
86.75 USD unreserved under the 200 USD ceiling (`CLEANUP_PROOF_R1W7_C51.json` `12ce9208…`;
`BUDGET_RECONCILIATION_ADDENDUM_CLAUDE_R1W7_C51_20261021T030608Z.json` `8554484f…`).

## The reading (facts, every number exact; `R1_W7_READING.json`)

**Instrument rows (all true):** I0 not a practice mock; I1 data identity; I6 completeness (14 of 14 units exit 0, deadline not hit);
I7 reading from the sealed zip; I9 governance; I10 seed rule; I12 recorder transparent (6 of 6 dialogues: wrapped runs byte-identical,
wrapped equals unwrapped memory); I14 not vacuous.

**Hard gates:** HG1 receipts (0 problems), HG2 replay (REAL and CONV identical), HG3 key-blind (carrier = 3 inputs + pins), HG4 no network
(14 units, 0 attempts), **HG5 sandbox FALSE (see above)**, HG6 no crash (0), HG7 voice changes no answer (REAL and CONV), HG8 switch
hygiene (0 problems), HG9 same inputs (one sha256 per exam), HG10 the chat never exits (0).

**Marks (all six true; recorded as facts, licensed as nothing because the verdict is FAILURE):**

| Mark | Reading |
|---|---|
| K1 LEARNS | fully learned 95 of 97 representable ANSWER-keyed real recipes (bar ceil(0.9 × 97) = 88) |
| K3 SAFE | 0 wrong answers (REAL), 0 wrong lessons, 0 wrong (CONV), 0 wrong (NOISE) |
| K4 HONEST | 0 unexplained asks (strict and wave-6 rule), 0 unrouted scored turns, UNSETTLED_ASK fired 0 |
| NH-CHAT | lost vs LOOP_ON: REAL 0 (CHAT_ON 96 right, LOOP_ON 94; gained `RW:pg:65061@224840`, `RW:pg:69364@87584`), CONV 0 (44 vs 42; gained `CV30`, `CV31`); max 2 |
| P PLAIN | RIGHT_AND_PLAIN = RIGHT on both exams (96 = 96; 44 = 44); 0 not plain |
| N NOISE | lost to small talk 0 (CONV 44 right and plain, NOISE 44); 0 misrouted scored turns; 128 noise turns, 0 misrouted, 0 noise replies with CAS tokens |

**Totals, CHAT_ON (the arm under test):** X7_REAL 128 items: RIGHT 96, WRONG 0, ASKS 16, NOT_SCORED 16 (undetermined keys; 7 same-name),
RIGHT_AND_PLAIN 96, fully learned 95 of 97. X7_CONV 64: RIGHT 44, WRONG 0, UNDETERMINED 20, RIGHT_AND_PLAIN 44. X7_NOISE 64 (+128 noise
turns): RIGHT 44, WRONG 0, UNDETERMINED 20. Stock turns on REAL: STOCK_RECORDED 107, CLARIFY_ENGLISH_UNKNOWN_INGREDIENT 14,
CLARIFY_NOT_CCE 3, CLARIFY_ENGLISH_NO_INGREDIENT_NAMED 2, INVENTORY_RECORDED 2; "recorded but reply says outside what I know" 0. Tool-engine
turns: 0 in every chat unit (D-W7-19).

**The yardsticks:** CHAT_OFF (`HELM_WIDE_BRAIN=0`, the licensed brain alone): REAL RIGHT 0 / ASKS 112 / lessons NOT_LEARNED 662; CONV RIGHT 30,
UNDETERMINED 34, misrouted scored turns 8, not routed 6; NOISE RIGHT 30. LOOP_ON (wave 6's harness, loop driven directly): REAL RIGHT 94,
fully learned 93; CONV RIGHT 42, UNDETERMINED 22. CHAT_ON − CHAT_OFF: REAL +96 right, −96 asks; CONV +14 right; NOISE +14 right.
CHAT_DIAG (voice bypassed) = CHAT_ON on every scored answer (HG7). CHAT_ON_REPLAY = CHAT_ON (HG2).

**Negatives on the exam, kept (CHAT_ON, by dialogue family):** S1 WISDOM_STATED 6 of 6 UNDETERMINED; S2 POWER_STATED 6 of 6; S7 NOT_A_FACE
4 of 4; S6 TWO_FACES 2 of 2; R4 WITNESS_IN_ENGLISH 2 of 4 (`CV23`, `CV25`) — 20 of 64 dialogues undetermined, the same families as on
practice, in LOOP_ON too (22). The 16 REAL asks are all explained (K4). CHAT_OFF misroutes 8 scored turns and leaves 6 unrouted: the
licensed reader alone does not carry the chat. Custodian's flag: 3 of the 128 REAL ids also appear in the old X6 / X6v3 CONV lists, which
the contract excludes only from the conversation pool (no violation; recorded for the next exclusion list).

## What would be needed to earn a word

A repaired reader (HG5 reads `helm_now_files_changed` only from units that run HELM, or the recorder unit writes it) and a repaired
fixture, resealed as v4 (same HELM cut `dfc7158d` unless the owner says otherwise), a fresh custodian draw (X7's ids go on the exclusion
list), and a new owner word for one more host run (about 0.02 USD). This record proposes nothing; the owner decides.

## Files

`Documents/Codex/2026-10-20/r1_wave7/run_c51_r1w7_20261020/`: `R1_W7_READING.json` (`8f2f76468fef11e4d755083d2581578e04466e0d028a92848c8019ad945a5d4d`), `MERGE_INPUT_R1W7.json` (`f63d859e…`),
`OPERATOR_I_CHECKS_C51.json` (`80939df4…`, every check true, 194 freeze members), `deliverable_unpacked_a2/`, `payload_c51/`
(both payloads, both plans, both inventories), `job_record/` (controller, worker, ledger hold, closeout, independent check, direct check,
every receipt of both attempts, `RETRY_DECISION_C51.json` `c44d9817…`, `PAYLOAD_SHA_FILL_NOTE_C51.json`, the refused-launch logs),
`CLAUDE_R1W7_C51_TRANSPORT_LEASE.json`, `backup_c51.py`. Custodian: `x7_custody/X7_SEALED_20261021T024717Z.json` (`3f216852…`),
`MANIFEST_X7.json` (`0fc90b02…`), `RECEIVER_CHECK_X7.json` (`78ab76c2…`, 23 of 23 true), carrier `X7_CARRIER_V1.zip` (`51eb15db…`).
Approval: `APPROVAL_RECORD_R1W7.json` (`f28543bc…`) from the owner's line `CHAT WAVE at 1 USD` (18 bytes, sha256 `61c398c1…`).
