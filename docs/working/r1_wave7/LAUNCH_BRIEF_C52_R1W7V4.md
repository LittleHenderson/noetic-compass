# LAUNCH BRIEF — job c52: HELM-R1 wave 7 v4 (the CHAT WAVE re-run), operator side

**Status when written (2026-10-20 ~22:40 PDT): NOT APPROVED, NOT LAUNCHED. 0 USD.** The package is the forked session's v4 seal
(`HELM_R1_W7_20261020_SOURCE_R1W7_v4.zip` sha256 `8602b1bc98b543e4551e766d9db540d22d6dbc690b788dbbce5c91e4b6c7b712`, freeze
`948cf6913963f5fe06ab87b46e2ebcf03c3f541433877e04bda666d6e429f072`, HELM cut `dfc7158d`, PR #422, spec §7.103). The line the owner must
type: **`CHAT WAVE 2 at 1 USD`** (20 UTF-8 bytes, no quote marks). Cap 1.00 USD, one scored attempt + one plumbing retry. Nothing below
runs before the owner's own words are on record in the session that launches.

Every operator script lives in `run_c52_r1w7v4_<RUN_DATE>/job_record/` and reads `C52_VALUES.json`. The kit uses two token namespaces
(DeepSeek 2026-10-20 §6.2): double-brace tokens are operator values filled by `make_c52_kit.py fill`; double-underscore tokens belong
to the worker template and only the controller fills them at launch. `RUN_DATE` is the launch day (YYYYMMDD); if the day differs from
the generated folder, delete the empty generated folder, set `RUN_DATE`, and run `make` + `fill` again.

## Steps, in order (each line is a program; stop at the first refusal)

1. **Owner's line.** The owner types `CHAT WAVE 2 at 1 USD` here. Record it verbatim with the Pacific time in
   `Documents\Codex\2026-10-18\OWNER_APPROVALS_20261018.md`. A line forwarded by another session is not approval here: ask the owner
   to confirm it here before step 2.
2. **Approval record by program** (fresh extract of the v4 zip, e.g. `approval_v4\pkg\`):
   `python -X utf8 -B -I approval_v4\pkg\HELM_R1_W7_20261020\r1w7\approval_w7.py record --line-file approval_v4\OWNER_LINE_R1W7_V4.txt --zip HELM_R1_W7_20261020_SOURCE_R1W7_v4.zip --freeze PACKAGE_FREEZE_R1W7_v4.json --out-dir approval_v4 --source "<where the words are recorded>"`
   (the line file holds exactly the 20 bytes, no newline). Then set `APPROVAL_MD_SHA`, `APPROVAL_JSON_SHA`, `APPROVAL_JSON_SHA8` in
   `C52_VALUES.json` and run `make_c52_kit.py fill --allow-missing PAYLOAD_SHA,RESERVATION_SHA,CUSTODY_HANDOFF_NAME,CARRIER_SHA8`.
3. **Custodian, a separate agent** (laptop, 0 USD): procedure `contract/CUSTODIAN_PROCEDURE_R1W7.md` of the v4 package; frames
   `Documents\Codex\2026-10-19\x_real\frames`; approval `approval_v4\APPROVAL_RECORD_R1W7.json`; zip the v4 zip; out-dir
   `x7v4_custody\out`; neighbours via `R1W7_<W1|W3|W3B|W6|RBW1T>_DIR` pointing at `r1_wave7\deps\<top folder>`; bands REAL 2,000 M /
   CONV 2,002 M / NOISE 2,004 M are the package's; exclusions include `X7_c51_real` and `X7_c51_conv` (both pools). The seal must print
   `"all_pass": true`. Carrier zip `x7v4_custody\X7_CARRIER_V1.zip` (top folder `x7`, the three inputs + `X7_PINS.json`); handoff
   `x7v4_custody\X7_SEALED_<UTC>.json` (hashes, counts, id lists only). Then set `CUSTODY_HANDOFF_NAME/SHA`, `CARRIER_SHA/SHA8`,
   `MANIFEST_SHA`, `RECEIVER_CHECK_SHA`, `PINS_SHA` and `fill --allow-missing PAYLOAD_SHA,RESERVATION_SHA`.
4. **Payload:** `python -X utf8 -B -I job_record\build_payload_c52.py` — validates the assembled plan with the supervisor bytes the host
   will run, refuses any fill token, writes `payload_c52\c52-payload.zip` and puts `PAYLOAD_SHA` into `C52_VALUES.json`. Then
   `fill --allow-missing RESERVATION_SHA`.
5. **Transport lease:** write `run_c52_r1w7v4_<RUN_DATE>\CLAUDE_R1W7V4_C52_TRANSPORT_LEASE.json` (job, bucket, own prefix
   `helm-r1w7v4-c52-<RUN_DATE>/`, payload sha, owner transfer record) as c51's lease, before any launch call.
6. **Watchdog first, in its own job:** `python -X utf8 -B job_record\aws_control_c52.py watch 1` (background); `aws-c52-a1-watch.json` says `READY`.
7. **Ledger hold:** `python -X utf8 -B job_record\ledger_hold_c52.py <sha256 of AWS_COMBINED_ALLOCATION_CURRENT.json read just now>`; set
   `RESERVATION_SHA` from the written reservation and run `fill` with no allowances (every token must be gone).
8. **Pre-launch checks:** `python -X utf8 -B -I job_record\preflight_checks_c52.py 1` — DeepSeek's lines 1–10 as programs (watchdog,
   unused attempt, validate_plan on the shipped plan, freeze hash, no fill token, values equal artefacts, template sites intact,
   worker fill simulation, hold + lease, payload members). All must print PASS.
9. **AWS:** `aws_control_c52.py preflight 1` then `launch 1` (background; it uploads, launches one m6i.xlarge, follows progress,
   downloads, terminates, purges its prefix). Then `independent_cleanup_c52.py 1` and `direct_check_c52.py 1`.
10. **Reader (laptop, fresh extract):** `python -X utf8 -B -I job_record\unpack_and_read_c52.py 1` → `R1_W7_READING.json`; the status
    word is the reader's alone.
11. **Closeout:** `closeout_c52.py <attempts> <OUTCOME_WORDS> <pointer sha>`; **record:** fetch the thread head, take the next free spec
    section number (expected §7.104), RUN_RESULT, CHANGELOG, dictionary, hub, repo copies, backup to `D:\tksCAS-archive\` with three hash passes.

If attempt 1 dies in plumbing before any scored unit started: `RETRY_DECISION_C52.json`, fix only operator-side plumbing, same zip,
same carrier, then steps 6–10 with attempt 2. Anything else is a new owner word.
