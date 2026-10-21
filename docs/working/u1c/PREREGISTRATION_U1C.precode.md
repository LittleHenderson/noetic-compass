# PREREGISTRATION — U1c (pre-code)

Status: PROPOSED. Binding only after the owner's own typed line names this file's sha256 and the cap.

- Written 2026-10-21, before any U1c code, number or world exists. DESIGN ONLY: nothing frozen, built or run; AWS not called; 0 USD spent; nothing written to git.
- This file fixes the reading before any code. `FROZEN_U1C.precode.json` will be a field-by-field transcription of it, made only after the owner answers `OPEN_QUESTIONS_U1C.md`. Items marked `[OWNER Qn]` hold the recommended answer and change only if the owner answers otherwise; after any change, the final file's sha256 is the one the owner names.
- Every rule has an ID. Every rule is written so a program can check it. Canonical JSON everywhere: `CANON(o) = json.dumps(o, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")`. `SHA(b)` = sha256 hex, lowercase.
- Claude is not the research governor. Nothing here is approved by being written.

---

## §P1 Question
- **Q-MAIN.** With U1b's science code and reader byte-identical and only the worlds changed, does `merge_u1.py` again give `test_verdict` READ with `status_why.EYE_EARNED_KEEP` true and `status_why.CONCERT_EARNED_KEEP` true? Decides the main word (§P10 WO).
- **Q-SIDE** `[OWNER Q7]`. Does A7 (§P4) fix as many planted faults as A4 with no more clean-world interventions? Decides only the A7 word (§P10 WA). Never changes a main word.
- **Q-PORT.** Does the Linux host reproduce U1b's outputs on U1b's own inputs within the port scope (`[OWNER Q4]`, default PREFIX-722)? Instrument check only.

## §P2 Precedence
- **PREC-1.** U1b `FROZEN.json` (sha256 `349644c6e3a8fc196fb74155413338bcb736a9a2f0d55c3458f6868193af045c`) governs constants and the 18 code tests only.
- **PREC-2.** `FROZEN_U1C.precode.json` governs worlds, authorization, replay rule, lanes, gates, words, thresholds new to U1c, attempts and claims.
- **PREC-3.** Where U1b `FROZEN.json` `arms.replay` ("draws 0-1 ... seed 11") disagrees with `PLAN.json` `replay`, the `PLAN.json` rule governs (it is what the code follows).

## §P3 Reference values (all re-hashed 2026-10-21 unless marked)
- **REF-1.** U1b `runs/MERGED_READING.json` SHA `d00189a185d5110d97fc815d7b77afd01775e0e6332ed93e51c063ba7aa41a88`; `test_verdict` "READ"; `status_why` = {"EYE_EARNED_KEEP": true, "CONCERT_EARNED_KEEP": true, "CHECKLIST_SUFFICES": false, "EYE_TIES_CHECKLIST_FEWER_INTERRUPTIONS": false}; 39 hard gates, 0 false.
- **REF-2.** Keep-list projection of REF-1: `SHA(CANON({k: R[k] for k in ["test_verdict","status_words","status_why","hard_gates","marks"]}))` = `a8335073c29b1295318925ca0c4cb3dd0ca22ecf4e309640e7d4714e8b1c9473`.
- **REF-3.** U1b `SOURCE_MANIFEST.json` SHA `ecba90709b58b2294ecad6fe0e2e5bf8077ca072c6fddf526774417443271640` (121 rows; reader brief; re-hashed equal on 2026-10-21 by `U1B_VERIFICATION_20261021`).
- **REF-4.** The 114 kept rows: the 13 U1B rows `__init__.py, consts.py, brain.py, brain_d.py, eye.py, faults.py, arms.py, run_u1.py, merge_u1.py, test_u1.py, static_check.py, FROZEN.json, FROZEN.precode.json` + all 101 non-U1B, non-PYTHON rows of REF-3. The transcription lists each by role, relative path and sha256 from REF-3.
- **REF-5.** Replaced or dropped rows (exactly 7): `worker.py` (replaced), `supervisor.ps1` (dropped), `run_all_parts.ps1` (dropped), `PLAN.json` (replaced per lane), `OWNER_APPROVAL_EVIDENCE.md` (replaced), `OWNER_APPROVAL_EVIDENCE.template.md` (replaced), `C:\Python314\python.exe` (dropped).
- **REF-6.** U1b W01 files: `WORLDS_B.json` `c0dd501f892ea81e8cc1cab342d3d8a1296c4521a402c99aedb8b744ed508684`; `DIALOGUES.json` `8cb7bd959efe7a239e3f77228e954a3ec1dba4b776d56e996b63c59157344210`; `KEYS.json` `649459adc7fc0d0f4bd698995b27626b6818779326e1c0c0011b70cc542b9758`; `THRESHOLDS.json` `c545dca2ecd19206cf98d87c03a76d212a08ca55d4700c412cefcf8540bde55c` (reader brief).
- **REF-7.** U1b `CALIBRATION.json` SHA `3cbd94dad9abf7f7e80115affc7da81bb2daa4c89e594cc0afea19d3fd978d02` (2,551 bytes). `SHA(CANON(CAL with every log[i]["wall"] removed))` = `b919c5b6944120cd04cced6c077f38942d2a3091b4d99f5a5552ab2506795989` (2,117 bytes). Scalars: `v_frozen` "1/2", `a5_rate` "171/1846", `a5_p_soft` "170/171", `whispers` 171, `soft` 170, `stages` 1846, `fallback_used` false, `throttle_fired` 0.
- **REF-8.** U1b `consts.py` SHA `d53578a269bb2d7a125106c46ea698ac0f9ce63c0fb0b8e03aafeadb11ce29a1` (reader brief).
- **REF-9.** U1b PLAN subset: n_draws 20, draw_start 100, draw_scan_max 60, cal_draw_start 200, cal_scan_max 20, seeds [131,137,139], cal_seed 149, cal_dialogues 4; replay arms ["A0","A4"], tb_first_scored_draws 2, dl_seed 131, dl_worlds [0,1]; expected_thresholds drift 0.984979914, seam 0.841069956, tone 1.227592661.
- **REF-10.** PREFIX-722 key set = the first 722 elements of `run_u1.planned_worlds(U1b PLAN, [100..119])` (lines 187-209): 672 scored dialogue keys (arms A0..A6 x seeds 131,137,139 x d 0..15 x {CLEAN, F_SEAM}), 8 replay dialogue keys (A0, A4 x seed 131 x d 0,1 x {CLEAN, F_SEAM}), 42 Task B keys (draw 100 x A0..A6 x {CLEAN, F_RECEIPT, F_FADED, F_MISALIGNED, F_FIXATION, F_MEMORY}).
- **REF-11.** Archive records for G_U1B_UNTOUCHED: `U1B_VERIFICATION_20261021.json`; `D:\tksCAS-archive\u1b_unity_eye_20261015\` (268 files); `D:\tksCAS-archive\u1_unity_eye_20261015\` (277 files) (reader brief, PR #442).
- **REF-12.** Run-proven `job_supervisor.py` SHA `3b2337ca75b189287c4591ed44671e308d37ef92d043f7bebb37ede77e6a1b01` with `LAUNCH_WINDOW_SECONDS = 6660` (line 31) and the window refusal at line 317.
- **REF-13.** Ledger pointer `C:\Users\wakil\Documents\Codex\AWS_COMBINED_ALLOCATION_CURRENT.json` SHA `81f0b6f61715249a4f175f9aa2d66b31a61bf29fecce44582c75fa96197390dd` at utc `2026-10-21T18:41:27.829920+00:00`: combined 113.34, unreserved 86.66, ceiling 200.0. Re-read before every hold.
- **REF-14.** Owner commitment `C` = `<64 lowercase hex, typed by the owner before this freeze>` `[OWNER Q2]`.

## §P4 Arms
- **ARM-1.** Lanes P and U run U1b's arms A0..A6 and replays A0_REPLAY, A4_REPLAY exactly as `arms.py` (byte-identical), in U1b's order and count. Per lane: 1,544 planned items (840 Task B + 672 dialogue + 24 replay Task B + 8 replay dialogue).
- **ARM-2.** Per arm: 148 plantings (5 x 20 Task B + 48 F_SEAM), 68 clean worlds (20 Task B + 48 dialogue).
- **ARM-3.** No arm is added to or removed from lanes P and U.
- **ARM-4.** A7 runs only in lane A, only if `[OWNER Q7]` = yes (recommended yes).

A7 (all values fixed here; none chosen after code):
- **A7-1.** Class `A7Rule(eye.UnityEye)` in new file `arm_a7.py`, constructed as `A7Rule("ONE_WAY", Fraction(1, 4), kind, learn=False, deadline=deadline)`.
- **A7-2.** `A7Rule` overrides exactly one method, `issue_whispers(self, brain, x)`. No other attribute of `UnityEye`, `eye`, `brain` or any imported module is assigned.
- **A7-3.** Override body: if `self.kind != "TB"`: issue nothing. Else for `k` in `sorted(set(UnityEye.misaligned(brain)) | set(brain.brain.quarantine))`: if `self.budget["STRONG"] >= K.BUDGET_STRONG`: stop; else `self.budget["STRONG"] += 1` and append to `brain.ledger` a `"WHISPER"` record with fields `id` ("w%d" % running count), `tick` (brain.tick), `strength` "STRONG", `drive` "F7", `action` "REFIT", `obj` k, `reason` "x3_stations_aligned", `value` "SCRIPTED", `volume` "1/4", `station` "S4", `object` "junction:%d" % k; it also writes the same naming record and `wlog` entry that `eye.py` lines 624 and 627-628 write for an issued whisper, so A7 item records keep the eye arms' format.
- **A7-4.** The argument `x` (the eye's reading) is never read in `arm_a7.py`. Nor are `events`, `rows`, `ingredients`, `readout`, `candidates`, `suppress`, `volume_bookkeeping` or `trouble`, and `wlog` is only written, never read (checked statically, GA-11).
- **A7-5.** The A7 brain context has `concert = False` (arm label "A7"; the rule `concert=(arm == "A4")` of `arms.py` lines 163 and 297 is copied unchanged).
- **A7-6.** Volume fixed at 1/4 `[OWNER Q7: alternative = lane U's CAL v_frozen]`. Never learned.
- **A7-7.** Autonomic tier, timing and budget: inherited unchanged from `eye.UnityEye` (`eye.py` byte-identical): triggers at eye.py lines 151, 173-200, 207-210, 212-219, 225-237, 483-490; execution lines 255-334; budget 2 STRONG + 4 SOFT + 1 autonomic corrective per 16-tick stage.
- **A7-8.** Fairness record: every inherited trigger reads brain-state fields (`rec["sig"]` built by brain.py line 382, `brain.misaligned_window`, `brain.pair_history`, `brain.slots`, `brain.chain`), so A7 keeps both the 64-tick idle cadence and the continuity-failure trigger.
- **A7-9.** `run_a7.py` contains copies of `arms.run_tb` and `arms.run_dl`; `diff(copy, original)` must equal the pinned diff (ADD-9), whose only semantic change constructs `A7Rule(...)` in the `"eye"` hook for arm "A7".
- **A7-10.** Lane A worlds = lane U's W01 files, opened read-only and checked by sha256 against lane U's `P01 RESULTS_U1.json` `units.W01.files`. Items: 120 Task B (20 draws x 6) + 96 dialogue (48 x 2) + A7_REPLAY 16 (first 2 scored draws x 6 Task B + seed s1 worlds 0,1 x 2 dialogue) = 232. Run prefix `U1C_A7_`; own package copy; own runs folder.
- **A7-11.** `merge_a7.py` computes FIX, FALSE and WORSE_THAN_NO_EYE for A7 with the same definitions as `merge_u1.py`, using lane U's A0 clean items as the answer key.
- **A7-12.** Behaviour test (in `test_a7.py`; runs in BT-B and at the start of every A7 part; fixture worlds only): with F_MISALIGNED planted on a fixture Task B world, A7 records A_QUARANTINE of `k*`, sends >= 1 STRONG REFIT whisper with reason "x3_stations_aligned" and volume "1/4" with 0 budget violations, and the world ends with `wiring[k*] == k*` and `k*` not quarantined.
- **A7-13.** Before the seal, a session that did not write A7 reviews `arm_a7.py`, `run_a7.py`, `merge_a7.py`, `test_a7.py`; its notes' sha256 is pinned in ADD-11. (Disclosed: a Claude session.)
- **A7-14.** No A7 file changes after the seal.

## §P5 Order of events
- **EV-0.** Owner answers `OPEN_QUESTIONS_U1C.md` (typed directly).
- **EV-1.** Owner types `U1C COMMIT <C>` (REF-14). Required before EV-2 if `[OWNER Q2]` = commit-then-reveal.
- **EV-2.** `FROZEN_U1C.precode.json` and its `.sha256` written; no U1c code exists yet.
- **EV-3.** Owner's line names the final sha256 of this file and the caps (Q14, Q13).
- **EV-4.** Custodian session: `USED_TABLE_U1C.json`, text scan (SEED-10), allowed slot list `A`, its own independent derivation script written from this file alone (SEED-11).
- **EV-5.** Code written; independent review (A7-13); build-test jobs BT-A, BT-B, BT-C (ATT-6) under the build line.
- **EV-6.** `SEAL_ADDENDUM_U1C.json` filled (§P15); zip sealed; `Z = SHA(zip)` appended to `ZIP_REGISTER_U1C.jsonl` with UTC time.
- **EV-7.** Owner sees `Z`, the precode sha256, the addendum sha256 and the cost; types run line `L` (SEC-3..SEC-6) and reveals `S`.
- **EV-8.** Seeds derived three ways (SEED-12); approval record; payload built containing the sealed zip unchanged plus approval record and derived files; ledger hold; lease; watchdog; preflight; launch.
- **EV-9.** Read on the laptop (`u1c_reader.py`); closeout; three-sha backup; spec row and CHANGELOG in the same commit.

## §P6 Secret, line and seeds
Secret and line capture:
- **SEC-1.** `S` matches regex `^[A-Za-z0-9]+( [A-Za-z0-9]+){3,}$` and `len(S) >= 20`.
- **SEC-2.** `C == SHA(S.encode("ascii"))`. `S` is first typed into the operator session at EV-7, never earlier.
- **SEC-3.** `L_norm = unicodedata.normalize("NFC", L).strip()`; bytes `L_b = L_norm.encode("utf-8")`. The approval record pins `L_b` (base64), `len(L_b)` and `SHA(L_b)`.
- **SEC-4.** `Z[:8]` (lowercase) is a substring of `L_norm.lower()`.
- **SEC-5.** `L_norm` contains the cap token `"<cap> USD"` exactly as the cap is written in the approval record (e.g. `"4 USD"`).
- **SEC-6.** The approval record field `capture` equals `"DIRECT_OWNER_MESSAGE"`: `L` and `S` were typed by the owner in the operator's own session, not relayed by another agent or workflow. The operator showed `len(L_b)` and `SHA(L_b)` back and the record holds the owner's confirming reply.

Derivation:
- **SEED-1.** `H = SHA(S.encode("ascii") + b":" + Z.encode("ascii"))`. Fallback if `[OWNER Q2]` = no commit: `H = SHA(L_b + b":" + Z.encode("ascii"))` and LIC-3 applies.
- **SEED-2.** `k1 = int(H[0:16],16)`, `k2 = int(H[16:32],16)`, `k3 = int(H[32:48],16)`, `k4 = int(H[48:64],16)`.
- **SEED-3.** Slots: slot `q` in 0..67 covers draws `750 + 60q .. 809 + 60q`. `A` = sorted list of allowed slot indices from the custodian (ADD-1), `N = len(A)`; `N >= 2` else INSTRUMENT_ERROR.
- **SEED-4.** `i = k1 mod N`; `D0 = 750 + 60·A[i]`; scored scan `D0 .. D0+59`.
- **SEED-5.** `j = k2 mod (N-1)`; if `j >= i`: `j += 1`; `C0 = 750 + 60·A[j]`; calibration scan `C0 .. C0+19`.
- **SEED-6.** `s1 = 1000 + (k3 mod 9000)`; `s2 = 1000 + ((k3 // 9000) mod 9000)`; `s3 = 1000 + ((k3 // 81000000) mod 9000)`; `s_cal = 1000 + (k4 mod 9000)`.
- **SEED-7.** Window moves: blocks of a window = world seeds `[10000001 + 200000·d0, 10175000 + 200000·d1]` and streams `[27000042 + 200000·d0, 27175041 + 200000·d1]` for its first and last draw `d0, d1`. If the scored window meets a USED_TABLE range widened by 1,000,000: `i = (i+1) mod N`, repeat. Calibration: if it meets a widened used range or the scored window's blocks: `j = (j+1) mod N`, skipping `i`, repeat. After `N-1` moves without a clear slot: INSTRUMENT_ERROR before any world is built.
- **SEED-8.** Dialogue moves, in order s1, s2, s3, s_cal: for seed `s`, families `F1 = {1000s + d}`, `F2 = {100000s + 100d + t}`, `F3 = {7919s + d}` for `d in 0..15`, `t in 0..99`. Move `s -> s+1` (9,999 -> 1,000) while: `s` is in the used dialogue list (REF in DESIGN §5.4); or `s` equals an earlier U1c seed; or any family member lies in any USED_TABLE range (exact, no margin), in either window's seed or stream block, or in an earlier U1c seed's families. After 9,000 moves: INSTRUMENT_ERROR.
- **SEED-9.** Every move is logged in `SEED_DERIVATION_U1C.json` with the range it hit.
- **SEED-10.** Text scan (custodian only, before the seal): streams the frozen file list in ADD-2 (generator, seed-derivation and frozen-config files; per-file cap 5,000,000 bytes); strikes slot `q` if any integer literal lies within 1,000,000 of slot `q`'s world-seed or stream block; never opens a file of a sealed package that has not launched (the list of such packages is pinned in ADD-2); outputs only the struck slot indices.
- **SEED-11.** The custodian's derivation is written from this file alone, without reading `u1c_seed_rule.py`.
- **SEED-12.** Outputs `PLAN.json` (PLAN-1) and `SEED_DERIVATION_U1C.json` = `CANON(dict)` where the dict has exactly the keys `H, k1, k2, k3, k4, A, i, j, D0, C0, s1, s2, s3, s_cal, moves`, written with `write_bytes`, no time, host, path or interpreter field. Computed by (a) the custodian on the laptop, (b) the host before lane U's P01, (c) the laptop reader. All three byte-equal.
- **SEED-13.** Every derived seed set from every revealed `S` is appended to `SEEDS_BURNED_U1C.json`.

## §P7 Plans
- **PLAN-1.** Lane U `PLAN.json` = U1b's `PLAN.json` parsed, with exactly these keys replaced and key order kept: `version` "u1c-plan-1"; `note` (new U1c text); `subset.draw_start` D0; `subset.cal_draw_start` C0; `subset.seeds` [s1, s2, s3]; `subset.cal_seed` s_cal; `subset.rule` (new text naming D0, C0, s1, s2, s3, s_cal and "SEED_RULE_U1C"); `replay.dl_seed` s1; `parts` {"P01": ["W01"], "P02": ["CAL"], "P03".."P120": ["QUEUE"]}; `order` ["P01".."P120"]; `max_parts` 120. Bytes = `json.dumps(obj, indent=1, ensure_ascii=False).encode("utf-8")`, written with `write_bytes`, no trailing newline.
- **PLAN-2.** Lane P `PLAN.json` = U1b's `PLAN.json` with only `note`, `parts`, `order`, `max_parts` changed as in PLAN-1. `version` stays "u1b-plan-1"; `subset` and `replay` unchanged.
- **PLAN-3.** Lane A plan: 232 keys of A7-10, in the order of `run_u1.planned_worlds` with arm list ["A7"] and replay arms ["A7"].
- **PLAN-4.** BT-A runs PLAN-1's program on fixture values and checks W01 accepts the result.

## §P8 Runner contract
- **RUN-1.** Per part: 300 s hard wall including preflight; worker guard `min(start+280, deadline-10)`; no new world within 60 s of the guard; worker killed above 314,572,800 bytes `VmRSS` (poll 200 ms); single-use run folder; permit consumed once; 18 unit tests first (A7 parts: 18 + the A7 tests); `END.json`/`SUMMARY.json` fields as U1b's.
- **RUN-2.** (a) The supervisor starts each worker as `/usr/bin/python3.12 -I -B -u worker.py ...` `[OWNER Q6]`. `worker.py` edits (exactly (b)-(h)): (b) environment word `AWS_CPU_ONCE`; (c) instance-id check: permit `instance_id` == content of `/var/lib/cloud/data/instance-id`; (d) approval-record sha256 check replaces the sign-line check; (e) manifest `SOURCE_MANIFEST_U1C.json`; (f) `sys.addaudithook` logging every `open` (path, mode) to `runs/<part>/OPENED.jsonl`; (g) at part end, record `U1_PLAN_PATH` presence and `{module: __file__}` for every loaded module; (h) UTC times as `datetime.now(timezone.utc).isoformat(timespec="microseconds")`.
- **RUN-3.** The supervisor removes `U1_PLAN_PATH` from the environment of every scored part.
- **RUN-4.** Lane P scope `[OWNER Q4]`: PREFIX-722 (default): the driver launches no further lane P part once lane P's `queue_remaining <= 822`. FULL: lane P runs to `queue_remaining == 0`. NONE: no lane P.
- **RUN-5.** Lanes P, U, A each have their own package copy and runs folder; P and U copies differ only in `PLAN.json`. Lane A uses prefix `U1C_A7_`.
- **RUN-6.** Lane U P01 and P02 start only after G_PORT_EARLY = true and the speed check = GO.
- **RUN-7.** Lane U P03 (first queue part) starts only after G_PORT = true on lane P's items (PREFIX or FULL scope prefix keys). Under NONE, after RUN-6.
- **RUN-8.** P00 (fixture worlds, plumbing) runs in a scratch package copy whose runs folder is never merged.
- **RUN-9.** Speed check at end of S1, host values only: `s_tb` = mean of the 6 Task B `log[*].wall` of lane P's host `CALIBRATION.json`; `s_dl` = mean of the 8 dialogue ones; `t_test = max(P01, P02 tests.cpu_seconds)`; `t_w = P01 + P02 wall_seconds_worker`; `u = 220 - t_test - 3` (if `u <= 30`: STOP); `b = 220 + 2·max(Task B walls) + 5`; `I_U = 864·s_tb + 680·s_dl`; `I_P = 42·s_tb + 680·s_dl` (PREFIX) or `I_U` (FULL); `end_U = now_T0 + max(t_w, ceil(I_P/u)·b) + ceil(I_U/u)·b`. GO if `end_U <= 12000` (seconds from T0), else apply RUN-11.
- **RUN-10.** Pinning: lane U on one physical core, lanes P then A on the other, via `sched_setaffinity` from `/sys/devices/system/cpu/*/topology/thread_siblings_list`. If no two non-sibling CPUs exist, lanes run in the order P(prefix), U, A and RUN-9 uses the summed projection.
- **RUN-11.** Shedding `[OWNER Q11]`: (1) FULL -> PREFIX-722 for lane P; (2) drop A7 (`A7_NOT_RUN`); (3) STOP before lane U P01.
- **RUN-12.** Packaging: lane U deliverable zipped and uploaded before lane A's archive (separate PUT URL); the worker lists any file skipped for size and fails if the list is non-empty; the controller streams downloads to disk.
- **RUN-13.** No new A7 part after T0 + 12,000 s; lane U never waits for lane A.
- **RUN-14.** Unpack on the laptop: create-only, into a folder under `C:\Users\wakil\Documents\Codex\2026-10-21\u1c\`; refuses any target path containing `u1b_unity_eye`, `u1_unity_eye` or `2026-10-21\u1b`; writes `LANE_P_NOT_A_READING_OF_RECORD.txt` beside any lane P `MERGED_READING.json` and pins its sha256.
Timer chain (seconds from T0 = worker start unless stated):
- **TIME-1.** Controller force cutoff `FORCE_MIN = 240` from launch.
- **TIME-2.** OS shutdown backstop `+14,160` (236 min).
- **TIME-3.** Supervisor stage deadline `+13,800`; worker timeout `+13,860`.
- **TIME-4.** Work cutoff `W = +12,900`; no new part in any lane after `+12,600`.
- **TIME-5.** Speed STOP threshold `+12,000`.
- **TIME-6.** No new A7 part after `+12,000`.
- **TIME-7.** Presigned URL expiry `>= 16,200` s from signing; preflight refuses credentials that expire sooner.
- **TIME-8.** Regenerated `job_supervisor.py` with `LAUNCH_WINDOW_SECONDS = 14400`; its sha256 pinned in ADD-7.
- **TIME-9.** A static preflight check reads every timer value in the generated kit and refuses launch unless each equals TIME-1..TIME-8.

## §P9 Hard gates (a false hard gate is a FAILURE; never a pass with caveats)
- **GI.** The 39 inner gates exactly as `merge_u1.py` (byte-identical) computes them on lane U's runs folder with lane U's `PLAN.json`.
Outer gates (computed by `u1c_reader.py`; checked before any inner word is read):
- **GO-1 G_CUSTODY.** `SHA(zip) == Z == approval.zip_sha256`; the zip member `FROZEN_U1C.precode.json` has the SHA named at EV-3; `SEAL_ADDENDUM_U1C.json` SHA equals approval pin; SEC-3..SEC-6 hold; approval record SHA equals the permit pin; payload members equal `payload_inventory.json`; `ZIP_REGISTER` time of `Z` < time of `L`.
- **GO-2 G_SEED.** SEC-1, SEC-2 hold (or the fallback is recorded); `H` recomputes; the three SEED-12 copies byte-equal; `ZIP_REGISTER_U1C.jsonl` lists every sealed zip; ATT-4 counts hold.
- **GO-3 G_FRESH.** `750 <= D0`, `D0+59 <= 4829`, `750 <= C0`, `C0+19 <= 4829`; the two windows' draw ranges disjoint; both slots in `A`; neither window's blocks meet a USED_TABLE range widened by 1,000,000; each of s1, s2, s3, s_cal in 1000..9999, not in the used dialogue list, pairwise distinct; every F1, F2, F3 member clear as in SEED-8; all U1c integer families pairwise disjoint.
- **GO-4 G_WORLDS_USED.** From lane U `P01/RESULTS_U1.json` `units.W01`: `draws` ascending, length 20, all in `D0..D0+59`; `set(draws) | {x["d"] for x in skipped} == set(range(D0, draws[-1]+1))` and the two sets disjoint; `calibration_draw` in `C0..C0+19` and `{x["d"] for x in calibration_skipped} == set(range(C0, calibration_draw))`; `dialogues.seeds == [s1,s2,s3]`; `dialogues.calibration_seed == s_cal`; for every lane U part `CANON(RESULTS_U1.subset) == CANON(PLAN.subset)`; no lane U part recorded `U1_PLAN_PATH` present.
- **GO-5 G_SAME_CODE.** Every REF-4 row present in both lane copies with its REF-3 sha256; the REF-5 rows are exactly the replaced/dropped set; the added rows equal ADD-8 exactly; `diff(worker.py, U1b worker.py)` equals ADD-10.
- **GO-6 G_NO_PATCH.** Static AST scan of every added or replaced `.py` file finds none of: an `Assign`/`AugAssign`/`Delete` target that is an attribute of a name bound by `import` or `from ... import` of a module or class; `setattr`/`delattr` calls whose first argument is such a name; any store, delete or mutating call on `sys.modules`; `importlib.reload`; in `u1c_supervisor.py`, `u1c_driver.py`, `worker.py`: any subscript or `.get` with key `"version"`, `"subset"` or `"replay"` on a parsed plan. Allowed: class definitions subclassing imported classes (`arm_a7.py`), `sys.addaudithook` in `worker.py`.
- **GO-7 G_HOST.** Recorded `{path, realpath, sys.version, platform.libc_ver()}` == ADD-3; `import ctypes` succeeded; after `import rb`, `import torch` and `import numpy` both raised; P00 `SUMMARY.status == "COMPLETED"` with 18/18; instance id == controller launch record.
- **GO-8 G_MODULES.** For every part of lanes P and U, every recorded module file is under the frozen interpreter's `sysconfig` `stdlib` or `platstdlib` paths (including `lib-dynload`), or under the lane's own package copy, or under the layout root; every `u1b_unity_eye.*` module file is under the lane's own copy.
- **GO-9 G_PORT_EARLY.** Lane P P01 `WORLDS_B.json`, `DIALOGUES.json`, `KEYS.json`, `THRESHOLDS.json` SHA equal REF-6; `SHA(CANON(drop(CAL_P, ADD-5))) == SHA(CANON(drop(CAL_U1b, ADD-5)))`; REF-7 scalars equal. Scope NONE: recorded NOT_RUN.
- **GO-10 G_PORT.** The U1b reference table's per-source SHA list (ADD-6) matches REF-11; scope PREFIX: lane P counted item keys ⊇ REF-10; scope FULL: lane P counted keys == all 1,544 planned keys; for every lane P counted item `it`: `CANON(drop(it, ADD-4)) == CANON(drop(ref[item_key(it)], ADD-4))`; FULL only: lane P REF-2-style projection == `a8335073…` (REF-2). Scope NONE: NOT_RUN.
- **GO-11 G_MEM_EQUIV.** For every counted part of lanes P and U: `ru_maxrss` returned by `os.wait4(worker_pid, 0)` (KiB) x 1024 < 262,144,000; no `kill_reason == "MEMORY"`.
- **GO-12 G_OPENED.** In every `OPENED.jsonl` of lanes P and U: each read-mode path under the layout root is a manifest row, or inside the lane's own runs folder, or in the frozen non-manifest list {lane `PLAN.json` (SHA = approval pin), `LAYOUT_U1C.json` (SHA = ADD-12), the part's permit files}; each write-mode path is inside the lane's runs folder; no path equals `sdg_source.COMPILER_FILE`.
- **GO-13 G_LANE.** Over lanes P and U only: package copies equal except `PLAN.json`; runs folders distinct; no lane U planned key appears in lane P's items and none of lane P's in lane U's; no folder named `U1B_MSI_P00` in either runs folder.
- **GO-14 G_WINDOW.** The speed check recorded GO; lane U deliverable PUT completed before T0 + 13,800 s.
- **GO-15 G_U1B_UNTOUCHED.** At EV-6 and after download, every file under `C:\Users\wakil\Documents\Codex\2026-10-15\u1b_unity_eye`, `...\2026-10-15\u1_unity_eye`, `...\2026-10-21\u1b` has the SHA in REF-11 records; the unpack log shows create-only writes and no refused-but-attempted target under those folders.
- **GO-16 G_READER_REPLAY.** The host's two `merge_u1.py` outputs on lane U are byte-identical; `SHA(CANON(json.loads(laptop_replay)))` == `SHA(CANON(json.loads(host_output)))`.
Count: 39 + 16 = 55 (53 under scope NONE, with GO-9 and GO-10 NOT_RUN).

A7 side gates (any false gives `A7_NOT_READ`; never part of the 55):
- **GA-1 G_TESTS_A7** all tests pass in every A7 part. **GA-2 G_UNVERIFIED_A7**, **GA-3 G_BYPASS_A7**, **GA-4 G_NO_NEW_KNOWLEDGE_A7**: as `merge_u1.py` defines them per arm, applied to A7 items. **GA-5 G_EYE_NEVER_WRITES_A7**: `eye_reads_equal` and `eye_rows_equal_events` true in every A7 item. **GA-6 G_BUDGET_A7**: sum of `budget_violations` == 0. **GA-7 G_REPLAY_A7**: 16 replay items equal their first runs (answers_sha256, link count, ledger sha256). **GA-8 G_A7_BEHAVIOUR**: A7-12 passed. **GA-9 G_A7_COPY**: A7-9 diff equal. **GA-10 G_A7_METRIC_EQUIV**: `merge_a7.py`'s functions on lane U's A3, A4, A6 items reproduce lane U `MERGED_READING` `marks.FIX_totals`, `marks.FALSE[arm].total` and `marks.WORSE_THAN_NO_EYE[arm].worse` exactly. **GA-11 G_A7_NO_READING**: A7-4 static check. **GA-12 G_LANE_A7**: lane A copy and runs folder separate; W01 files sha-equal to lane U P01 records. **GA-13 G_MEM_A7 / G_OPENED_A7**: GO-11 and GO-12 applied to lane A.

## §P10 Words (test-reader words, not spec-legend claim words)
- **WI.** Inner words exactly as `merge_u1.py` lines 489-517: `test_verdict` in {"INSTRUMENT_PROBLEM", "EYE_HARMFUL", "READ"}.
Outer words (first true wins):
- **WO-1** `U1C_INCONCLUSIVE`: any GO false (NOT_RUN under scope NONE does not count as false), or `test_verdict == "INSTRUMENT_PROBLEM"`.
- **WO-2** `U1C_EYE_HARMFUL`: `test_verdict == "EYE_HARMFUL"`.
- **WO-3** `U1C_REPLICATES_U1B`: `test_verdict == "READ"` and `status_why.EYE_EARNED_KEEP` and `status_why.CONCERT_EARNED_KEEP`.
- **WO-4** `U1C_EYE_KEEP_NOT_REPLICATED`: READ, CONCERT_EARNED_KEEP true, EYE_EARNED_KEEP false.
- **WO-5** `U1C_CONCERT_KEEP_NOT_REPLICATED`: READ, EYE_EARNED_KEEP true, CONCERT_EARNED_KEEP false.
- **WO-6** `U1C_DOES_NOT_REPLICATE_U1B`: READ, both false.
- **WO-7** Always printed with the word: `flipped = [k for k in REF-1 status_why if status_why[k] != REF-1[k]]` (READ only); `REVERSAL = status_why.CHECKLIST_SUFFICES` (READ only).
A7 words (first true wins; F = FIX, C = FALSE over the same 148 plantings and 68 clean worlds):
- **WA-1** `A7_NOT_RUN`. **WA-2** `A7_NOT_READ`: any GA false, or the main word is WO-1 or WO-2. **WA-3** `A7_HARMFUL`: A7 clean-world worse count (the `merge_u1.py` G_CLEAN comparison against lane U's A0, including the 16/16 clause) + faulted-world WORSE_THAN_NO_EYE > 0. **WA-4** `EYE_BEATS_A7`: F(A4) > F(A7) and C(A4) <= C(A7). **WA-5** `EYE_FIXES_MORE_THAN_A7_AT_HIGHER_COST`: F(A4) > F(A7) and C(A4) > C(A7). **WA-6** `EYE_TIES_A7_FEWER_INTERRUPTIONS`: F(A4) == F(A7) and C(A4) < C(A7). **WA-7** `A7_SUFFICES`: F(A7) >= F(A4) and C(A7) <= C(A4). **WA-8** `A7_FIXES_MORE_AT_HIGHER_COST`: F(A7) > F(A4) and C(A7) > C(A4). **WA-9** No WA word changes a WI or WO word.

## §P11 Thresholds
- **TH-1.** All U1b thresholds unchanged: `consts.py` SHA per REF-8; `test_u1` checks them against U1b `FROZEN.json`.
- **TH-2.** Part cap 120. **TH-3.** G_PORT tolerance zero under ADD-4/ADD-5. **TH-4.** ADD-4 ⊇ {"wall"} (top-level item key); ADD-5 ⊇ {"log[*].wall"}. **TH-5.** G_MEM_EQUIV limit 262,144,000 bytes. **TH-6.** Task B band d 750..4,829 (68 slots of 60); dialogue band 1,000..9,999. **TH-7.** Slot margin 1,000,000 (seed and stream space). **TH-8.** Timer chain TIME-1..TIME-8. **TH-9.** Speed rule RUN-9. **TH-10.** A7 volume 1/4. **TH-11.** Build-test window sum (ATT-6). **TH-12.** Run cap `[OWNER Q13]` 4.00 USD; build-test cap `[OWNER Q14]` 1.00 USD.

## §P12 Replication rule
- **REP-1.** Replication is decided by WO-3..WO-6 only.
- **REP-2.** No FIX, FALSE or WORSE count must match U1b; counts are reported side by side, unscored `[OWNER Q9]`.
- **REP-3.** U1b and U1c are never pooled; §7.38 and §7.40 are not rewritten.
- **REP-4.** Lane P results and A7 words are not part of replication.
- **REP-5.** Report-only FLAG check: `FALSE(A4) == 1816 and FALSE(A6) == 10152` on lane U.

## §P13 Stop rules
- **STOP-1.** G_HOST false at S0: stop; no lane starts; plumbing retry allowed (ATT-2).
- **STOP-2.** G_PORT_EARLY false: stop before lane U P01; word WO-1.
- **STOP-3.** Speed check after shedding still projects `end_U > 12000`: stop before lane U P01; word WO-1 by G_WINDOW.
- **STOP-4.** G_PORT false: lane U P03 never starts (PREFIX) or lane U is not merged (FULL); lane U's runs folder is shipped only as a sealed archive identified by SHA and is not unpacked; word WO-1.
- **STOP-5.** INSTRUMENT_ERROR in SEED-7 or SEED-8: stop before any world; word WO-1.
- **STOP-6.** No automatic retry after STOP-2, STOP-3 or STOP-4; the outcome goes to the owner.
- **STOP-7.** Per lane: U1b's stop rules (a part not COMPLETED; P01/P02 unit check failed; two consecutive queue parts with no progress; part cap reached).
- **STOP-8.** A7 lane stops at TIME-6 or on any A7 part failure; it never stops lanes P or U.
- **STOP-9.** Any change after `L` to the zip, the addendum, the approval record or a derived plan: the attempt is void, recorded as a FAILURE of that attempt.

## §P14 Attempts
- **ATT-1.** One scored attempt per sealed zip.
- **ATT-2.** At most one plumbing retry with the same zip and the same `S` (so the same seeds), only if: attempt 1 cleanup VERIFIED three ways; no lane U QUEUE part started; a `RETRY_DECISION_U1C.md` names the plumbing cause; only controller-side kit files outside the zip changed and TIME-9 passes.
- **ATT-3.** A retry that needs any change inside the zip is a new zip: it needs a new commitment `C'`, a new run line and new seeds; the old seeds are burned (SEED-13).
- **ATT-4.** Totals for U1c across all zips: at most 2 launches (scored attempts plus retries) and at most 3 zips registered in `ZIP_REGISTER_U1C.jsonl` (void ones included).
- **ATT-5.** Every attempt's outcome, cost and burned seeds are reported next to the final result.
- **ATT-6.** Build tests: at most 3 AWS jobs under the build line: BT-A (plumbing, census, two-process determinism, reference table, timer and memory checks; force window 30 min), BT-B (A7 tests and metric equivalence on fixture items; 20 min), BT-C (one re-test after a fix; 10 min). Sum over jobs of `2 x 0.46 x window_hours` = 0.92 <= 1.00. Each job places its own hold before launch.
- **ATT-7.** Build tests never build a U1c scored world and never run lane U.

## §P15 Seal addendum (`SEAL_ADDENDUM_U1C.json`; filled at EV-6; hashed into the zip)
May fill only these values, each from only the named input; none may come from a U1c scored world (none exists before `L`):
- **ADD-1.** Allowed slot list `A` and `USED_TABLE_U1C.json` SHA — from the custodian (EV-4).
- **ADD-2.** The text-scan file list, the sealed-unlaunched exclusions and the struck slots — from the custodian.
- **ADD-3.** Interpreter identity `{path, realpath, sys.version, platform.libc_ver()}` — from the BT-A record.
- **ADD-4.** Item exclusion list (must contain "wall"; may add only keys that differed between BT-A's two host processes on identical fixture inputs, each with its record path) — from BT-A.
- **ADD-5.** CAL exclusion list (must contain "log[*].wall"; same rule) — from BT-A.
- **ADD-6.** U1b reference item table SHA and the SHA of every U1b source file it read — from BT-A.
- **ADD-7.** Regenerated `job_supervisor.py` SHA and the kit timer values (must equal TIME-1..TIME-8) — from the kit build.
- **ADD-8.** The exact added-row list (names fixed in DESIGN §3.B.8 plus `LAYOUT_U1C.json`, `SOURCE_MANIFEST_U1C.json`, the two site-compiler `__init__` rows, `FROZEN_U1C.precode.json`(+`.sha256`), `SEAL_ADDENDUM_U1C.json`, `USED_TABLE_U1C.json`, regenerated `job_supervisor.py`) with SHA — from the sealed tree.
- **ADD-9.** The A7-9 pinned diff — from the sealed tree.
- **ADD-10.** The `worker.py` diff against U1b's `worker.py` — from the sealed tree; must implement exactly RUN-2 (b)-(h).
- **ADD-11.** Independent review notes SHA (A7-13) — from the reviewer session.
- **ADD-12.** `LAYOUT_U1C.json` SHA — from the sealed tree.
- **NOAMEND-1.** Before `L`, any other change to this file's rules is an amendment: listed in the addendum's `amendments` with reason, and shown to the owner with `Z`.
- **NOAMEND-2.** After `L`, no amendment and no second reading. STOP-9 applies.
- **NOAMEND-3.** If BT-A shows any field read by G_REPLAY (answers_sha256, link count, ledger sha256) differing between two host runs on identical inputs: no seal; FLAG_FOR_HUMAN_REVIEW; the owner decides.

## §P16 Claim ceiling and what each word licenses (the mapping is the owner's, `[OWNER Q8]`; proposal below)
- **LIC-1.** Ceiling: SYNTHETIC_ONLY; RB2c only; U1b's six planted fault types only; one run.
- **LIC-2.** Bounded sentence chosen by `u1c_reader.py` from the recorded port scope (FULL / PREFIX with N = number of lane P items compared / NONE), as written in DESIGN §13.1.
- **LIC-3.** If SEED-1's fallback was used, the sentence says the builder could compute the seeds before the seal.
- **LIC-4.** Limits sentence always printed: "It tests whether U1b's words survive fresh worlds not picked by the builder. The instrument changes U1b chose after seeing U1's numbers are kept, not tested. U1b's authority record is unchanged."
- **LIC-5.** WO-1, WO-2, WO-4, WO-5, WO-6: no positive sentence; the outcome is recorded as a negative beside §7.40; WO-2 is a FAILURE of the eye's ACTING on fresh worlds.
- **LIC-6.** WO-3 with WA in {A7_NOT_RUN, A7_NOT_READ, A7_HARMFUL, A7_SUFFICES, A7_FIXES_MORE_AT_HIGHER_COST, EYE_FIXES_MORE_THAN_A7_AT_HIGHER_COST}: the sentence carries ENGINEERED-NOT-VALIDATED; Eye ACTING stays NOT LICENSED.
- **LIC-7.** WO-3 with WA in {EYE_BEATS_A7, EYE_TIES_A7_FEWER_INTERRUPTIONS}: VALIDATED is on offer for the bounded sentence; Eye ACTING may move off NOT LICENSED to that sentence only.
- **LIC-8.** Never licensed by any word: real data or use; RB-W1, the live loop or chat; HELM-level involuntary duties; unknown faults; "better than a checklist" in general; statistical superiority; pooling U1b and U1c; decline-with-reason and escalation paths if DECLINES stays vacuous; Linux-Windows equivalence beyond the items compared; consciousness or awareness; any change to a later word.
- **LIC-9.** Recorded in the next free spec section (7.120 free on 2026-10-21; 7.119 reserved for c56), same commit as the result, beside §7.38 and §7.40. Claim status words only from the spec legend.

## §P17 Must be answered before `FROZEN_U1C.precode.json` is written
Q2 (commit-then-reveal), Q4 (lane P scope), Q5 (port strictness), Q6 (interpreter), Q7 (A7), Q8 (claim mapping), Q9 (replication criterion), Q10 (outer-gate set), Q11 (shedding order), Q13 (instance, window, cap), Q14 (build tests). Recommended answers are written into this file already; any different answer changes this file before its sha256 is named.
