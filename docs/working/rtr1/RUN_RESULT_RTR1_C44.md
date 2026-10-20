# RTR-1 "RE-TEST READER", job c44 (2026-10-19 Pacific): verdict `PASS`; reader v1.1 `S_SAFE_NOT_USEFUL`, reader v1.0 (control, same draw) `S_UNSAFE_ON_REAL`; fix word `FIX_REMOVED_HARM`

Status: REAL run. Every word below comes from a program, not from prose: `RTR_READING.json` (sha256
`6a28751ff7eb5e1257e7f5cf644329cf03e947059c730cdcac4d970ee4684378`) was written by the frozen reader `rtr/merge_rtr.py`,
run in isolated mode (`rtr_contract/xrun.py`) from a fresh extract of the sealed zip (27 of 27 members re-hashed, 0 bad).
Verdict **PASS** = every instrument row true and every hard gate true. V11's word then decides what may move
(PREREGISTRATION section 8), ceiling **`NAMED_CORPORA_ONLY`**. Merge input `MERGE_INPUT_RTR.json` sha256
`ce970834c018cc28c858d02b78b4a1770932c61c94ed1398ce9cfdb5408e93d1`.

**Said plainly first.**
- HELM read 128 NEW real food sentences (never used by X-REAL or CTT), drawn blind by the custodian.
- The fixed reader (v1.1) wrote **0** wrong stock facts. The old reader (v1.0), on the same 128 sentences, wrote **11**
  wrong ones. The frozen limit is 2. So the fix removed the harm on this draw 🟩.
- The fixed reader was right 115 times; always-ask was right 114 times. "Useful" needs 4 more than always-ask (118).
  So v1.1 is safe but not more useful than always asking 🟧. Its word is `S_SAFE_NOT_USEFUL`.
- The old reader on X-REAL's old 128 gave byte-for-byte the same answers as in c42 (128 of 128 equal). So the control
  really is the c42 reader 🟩.
- The draw had only 1 sentence with real stock facts in it (key FACTS) and 4 that should be asked. So this run says
  almost nothing about whether v1.1 still writes TRUE facts well (lost true writes: 0 of 1) 🟨.

## The reading

- **Verdict `PASS`.** Instrument rows all true: I1 package and neighbours, I1 sample and keys recomputed, I2 two-key
  agreement (128/128), I-READER (12 loaded HELM modules per unit, 0 bad, 0 missing, on V11, V11 replay, V10 and the
  control), I-CTRL same old reader as c42 (128 items, 0 differ), I6 completeness, I7 reading from the sealed package,
  I9 governance, I10 seed rule, I12 contamination recomputed.
- **Hard gates all true:** H-OVERLAP (0 shared id hash and 0 shared text hash with the X-REAL 128 and with the CTT 128),
  H1 no receipt-inconsistent, H11 V11 replay identical, HK key-blind, HN no network, HS sandbox (wave-1 brain folder
  `65795c8c…` at start = end), HB same inputs.
- **Words:** V11 **`S_SAFE_NOT_USEFUL`** 🟧; V10 **`S_UNSAFE_ON_REAL`** 🟥 (a recorded negative, never deleted);
  fix word **`FIX_REMOVED_HARM`** 🟩.

| Mark | V11 (fixed reader) | V10 (old reader, control) |
|---|---|---|
| S-a SAFE (WRONG ≤ 2) | true (0) | **false** (11) |
| S-b USEFUL (RIGHT ≥ B-ASK + 4 = 118) | **false** (115) | **false** (104) |
| S-c SAFER_THAN_KEYCALC (WRONG < 6) | true | **false** |
| S-d PLAIN | true (128/128) | true (128/128) |
| S-e EYE_QUIET | `NOT_EXERCISED` (no Eye arm, D-RTR-1) | `NOT_EXERCISED` |

## Counts per arm (128 items; 13 not scored because the two keys say UNDETERMINED; 115 scored)

| Arm | RIGHT | WRONG | UNDETERMINED | asks |
|---|---|---|---|---|
| **V11 (reader v1.1)** | **115** | **0** | 0 | 114 |
| V11 replay | identical record for record (H11) | | | |
| **V10 (reader v1.0, control)** | **104** | **11** | 0 | 110 |
| B-ASK (always asks) | 114 | 0 | 1 | 128 |
| B-KEYCALC (keyword reader) | 104 | 6 | 5 | 0 |
| B-ECHO (reference only) | 110 | 0 | 5 | 0 |

- Keys (custodian, two keys agree 128/128): EMPTY 110, FACTS 1, ASK 4, UNDETERMINED 13.
- By key, V11: EMPTY 110 → 110 RIGHT; FACTS 1 → 1 RIGHT; ASK 4 → 4 RIGHT. V10: EMPTY 110 → 99 RIGHT, **11 WRONG**;
  FACTS 1 → 1 RIGHT; ASK 4 → 4 RIGHT.
- Invented numbers: V11 0, V10 0. Lost true writes (FACTS items RIGHT under V10, not under V11): **0** (of 1).
- Changes V10 → V11: 11 items WRONG → RIGHT; no other change.

## The wrong items (by id; never by content)

Failure class for all 11 V10 wrongs: **EMPTY key, stock written** — the old reader saved stock that the sentence did
not state (the same class as c42's 8). V11: no wrong item.

`S:tatoeba:11677874`, `S:tatoeba:11709644`, `S:tatoeba:11798090`, `S:tatoeba:12115440`, `S:tatoeba:12222364`,
`S:tatoeba:2470773`, `S:tatoeba:2953173`, `S:tatoeba:5160602`, `S:tatoeba:6097394`, `S:tatoeba:6577109`,
`S:tatoeba:7390469`.

## What this licenses, and what it does not

- **Licensed (PREREGISTRATION section 8, V11 word `S_SAFE_NOT_USEFUL`):** the English reader's Part-S word on record
  moves from `S_UNSAFE_ON_REAL` (c42, v1.0) to **`S_SAFE_NOT_USEFUL` (v1.1)** — the safety half only: on these named
  corpora (Tatoeba English export `bb3dcc28…`, Google Taskmaster `d92cb6af…`), reader v1.1 wrote nothing the sentence did
  not say. Ceiling `NAMED_CORPORA_ONLY`. Legend status stays **`ENGINEERED-NOT-VALIDATED`**. The c42 result stays on
  record as v1.0's result.
- **NOT LICENSED:** "the reader is useful" (S-b missed); anything about English typed to HELM by people; "HELM reads
  everyday English"; the recipe brain, the Eye, the voice, the wide brain; real users or kitchens; statistical
  superiority (one run, one draw); anything about v1.1 keeping TRUE stock facts (only 1 FACTS item in this draw).

## Operator checks (beside the reader's own rows)

- **Seed source:** sha256(owner line 68 bytes `b645e4f4…` + ":" + zip sha256 `e201feb6…`) =
  `6f9cb0fdbab9591e115463c832bf5aadffd89bc69ed80bbc6c4cc1e68280b1b7` = the custodian derivation's `input_sha256`;
  derivation `zip_sha256` = the zip; `overlap_check` PASS; derivation sha256 `f8680e90…`.
- **Owner line** re-extracted by program from `OWNER_APPROVALS_20261018.md` (the 2026-10-19 `## Owner order … verbatim):`
  line): 68 bytes, sha256 `b645e4f482e10e3caa1f6e497f304ebc13faf481ff1345b2099c3f1358bc60e4`. Only the RE-TEST READER part was used.
- **Manifest** `MANIFEST_RTR.json` sha256 `562dd6ab317a4ca22aba1c7d7e59809bd320a5ab306f6bce3a5df875b37a8819` (before ship and before the reading).
- **Amendment RTR-A1** cited: the manifest's `rtr_a1.amendment_sha256` = `dceedd340a025fd71b2b61f844b432f2a5c1e69d03dc5f30ac64d4b237a50c64`
  = the file's sha256; seal record: 264 slots stepped, 0 strict-overlap items.
- **Package zip** `e201feb6e5fd4eaf1d9b9060ed100a9db6150257c2d0b64d230ad81c4042f7a8` verified before shipping; carriers by sha256 only:
  `rt` = INPUTS_RTR `c0037bf3…` + RTR_PINS `636e72f1…` (no key file), `xrspent` = INPUTS_XREAL `37312a31…`.
- **The operator never opened, printed or summarised an exam file.** Exam files were copied and hashed as bytes; the
  frozen reader read them and wrote counts and item ids only.

## Job, machine, money

| Job | What | Instance | Launch / end (UTC) | Host s | Charge |
|---|---|---|---|---|---|
| c44 | scored host run, stage `rtr_host_run` PASS | `i-0d443520810f62063` t3.medium, us-west-2, `ami-0dddfa1ffa6b87af7`, 20 GiB gp3 | 01:37:04 / 01:39:02 (terminated); cleanup 01:39:34 | 151.7 | 0.01 |

- **Pacific time:** launched 6:37 PM, terminated 6:39 PM, 2026-10-19.
- **Source:** payload `c44-payload.zip` sha256 `c6b569a2c1e479d6b2fdc167c752d615ce4414513a5d5bd4ab5c0f47dd5982b1` (464 members;
  host re-checked 464 of 464, 0 bad, and 462 source members after the run, 0 changed): sources rtr `e201feb6…`, xreal
  `a9b4c954…`, r1w4 `4bd0d740…`, r1w3b `a4f82556…`, r1w3 v3 `152bca2a…`, w1 v3 `31f97d67…`; carriers above; job plan
  `f850660c…` (`kit/plan_check.py` PASS, supervisor `validate_plan` true); supervisor = the package's `kit/job_supervisor.py` `3b2337ca…`. No corpus shipped.
- **Purpose:** the RTR-1 scored host run per `LAUNCH_BRIEF_RTR.md` step 4.
- **Limits:** cap 0.10 USD (scored + one plumbing retry); force cutoff 34 min; OS shutdown +32 min; runner deadline 1,200 s; stage limit 1,500 s; no automatic retry.
- **Timing:** runner 14.45 s (tests + pool); host tests: `tests_rtr` Ran 29 OK; reader v1.1 tests on the overlay Ran 119 OK (skipped 1).
- **Attempts:** ONE scored attempt; 0 plumbing retries.
- **Transport deviation (recorded, not a package change):** job c43 (CTT-1) held the shared four-key S3 prefix exclusively
  at the same time. So c44 used its own prefix `helm-rtr1-c44-20261020/` in the same bucket, NO instance profile and NO
  SSM: the worker rode in user-data and moved bytes only through four presigned HTTPS URLs. Project tag `HELM-rtr1-c44`.
  The c43 folder, instance, tags and prefix were never touched.
- **Charge:** **0.01 USD** (list price from host time 0.002057 USD, rounded up to the cent; the bill is not posted). Cautious
  figure (adds worst-case t3 CPU-credit surplus): **0.01 USD**. Far under the 0.10 cap. Good.
- **Ledger:** read 111.54 (after c43's closeout). Hold 0.10 placed: 111.54 → 111.64 (reservation
  `BUDGET_RESERVATION_RTR1_C44.json` `6d292dd8…`). Closed 111.64 → **111.55** of 200.00 (unreserved 88.45). Addendum
  `BUDGET_RECONCILIATION_ADDENDUM_CLAUDE_RTR1_C44_20261020T014053Z.json` (`c2013f97…`); ledger after `0dd6485e…`. Both
  writes re-read the shared pointer just before writing (sha256 check) and added one HISTORY line each.
- **Cleanup VERIFIED, confirmed three ways:**
  - controller: terminated, volume `vol-01c15d80ca76b74d9` DELETED, own prefix purged (4 versions) and verified empty (`99144a88…`);
  - independent check: `VERIFIED` at 01:39:47 UTC, within an hour (`6adaab01…`);
  - direct read-only look at 01:39:50 UTC: instance terminated ("User initiated"); no live c44 instance, no volume, no
    prefix version or delete marker, no multipart upload (`c6ccaffb…`).
  Proof `CLEANUP_PROOF_RTR1_C44.json` (`cef9db45…`). No temporary role, profile or bucket was created.
- Benign control note (as at c37-c42): one `InvalidInstanceID.NotFound` right after launch while AWS registered the instance. Nothing failed.

## Files

- Reading `RTR_READING.json` `6a28751f…`; host `deliverable_unpacked_a1/results/rtr_host_run/out/rtr_out/RTR_HOST.json`
  `b2967df904ad9a11b3f40a00e4099bdc1654ca233faeaf64402cc084de3939e9`; deliverable zip `52c85c3fa67978639acf70660fd3fb186b321b0b62281feabee5079985737959`;
  reader logs `reader.stdout.log`, `reader.stderr.log`; job record `job_record/`.
- Controller: `Documents\Codex\2026-10-01\task-2\helm_operator_preparation\controller_claude_rtr1_c44\`.
- Backup: `D:\tksCAS-archive\rtr1_c44_20261020\`.
