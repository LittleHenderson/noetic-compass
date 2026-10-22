# U1c: a fresh-world retest of the Unity Eye's ACTING (design packet)

Status: DESIGN ONLY. Every choice below is PROPOSED, not approved. Nothing is frozen, built or run.
AWS was not called. 0 USD was spent. Nothing was written to git. Written 2026-10-21.
Companion files in this folder: `PREREGISTRATION_U1C.precode.md` (the rules a program will check),
`COST_AND_SIZING_U1C.md`, `OPEN_QUESTIONS_U1C.md`, `REVIEW_LOG_U1C.md`.

---

## §0 Said plainly first

**What U1c asks.**
- U1b ran on the laptop on 2026-10-15. It tested whether the Unity Eye helps the recipe brain fix faults that were planted on purpose.
- The Unity Eye is a small watcher beside the brain. It can whisper suggestions to the brain. It can also run a few automatic repair routines (the "autonomic tier": repairs that need no permission, like a reflex).
- U1b's frozen reading program (`merge_u1.py`) printed READ with two "keep" words: `EYE_EARNED_KEEP` and `CONCERT_EARNED_KEEP`.
- U1c asks one question: if only the practice worlds change, does the same program print the same two words again?

**Why this is worth asking after U1b.**
- A "seed" is the starting number that decides which practice worlds get made.
- U1b's seeds were picked by hand by the builder (Claude): Task B draws 100-119, calibration draw 200, dialogue seeds 131, 137, 139, calibration seed 149.
- U1b's three rule changes were also chosen after U1's numbers had been seen.
- So U1b's result could be a lucky pick. U1c tests that on worlds that nobody on the build side can choose.
- U1c can also add one fair rival, called A7 (if you say yes). A7 runs the eye's own automatic repair routines on the eye's own timing, plus one fixed "please re-fit this junction" message. It has no eye readings, no reading-driven whispers and no "concert" (the eye and brain knowing about each other).
- U1b's own frozen rules admit its only rule-based rival (A6, a checklist) was handicapped twice: it has no voice, and it has no budget. A7 removes both handicaps.

**What changes.**
1. The worlds. They come from a secret word list that you choose and lock in before any code exists, plus the fingerprint of the sealed package.
   - A fingerprint (a "sha256") is a 64-character code computed from a file or a text. Any change gives a different code.
   - You first give only the fingerprint of your secret. You show the secret itself after the package is sealed. This is called "commit-then-reveal".
   - After that, nobody can steer the worlds. Not Claude (who never sees the secret in time). Not you (you are locked in before the package exists).
2. The computer. U1c runs on one AWS Linux machine instead of the laptop. Moving a program to a different system is a "port". A port can change answers through tiny rounding differences.
   - So U1c first re-runs a slice of U1b's own inputs (the first 722 of U1b's 1,544 items, covering all 7 arms) and checks every answer comes out identical.
   - Only then does any scored work on fresh worlds start.
3. The rival A7, if you say yes. It is read by its own program and can never change the main word.

**What stays the same.**
- The brain (RB2c), the eye, the seven arms A0-A6, the six planted faults, every threshold, the 39 hard gates and the reader `merge_u1.py`.
- A "hard gate" is a pass/fail check that must hold, or the run is not usable.
- 114 files stay byte-for-byte equal to U1b's.

**What a pass would mean.**
- The reader prints `U1C_REPLICATES_U1B`. U1b's two keep words were not a lucky pick of worlds.
- It does NOT mean the eye beats a fair rule. Only A7 can show that.
- If A7 also reads `EYE_BEATS_A7` or `EYE_TIES_A7_FEWER_INTERRUPTIONS`, the eye's readings added something a plain rule could not. My forecast says that is unlikely (about 0.15).

**What a fail would mean.**
- The port check fails: U1c stops before any fresh world is scored, at about 0.03 USD. It says nothing about the eye. It records that U1b's program does not reproduce on Linux.
- The eye harms answers on fresh worlds: a FAILURE of the eye's acting, kept beside U1b.
- The words change: U1b's words depended on its worlds. Kept as a negative.
- A7 matches the eye (`A7_SUFFICES`): the eye's edge in U1b came from its voice and timing, not its sight. This is the outcome I think most likely.
- U1's record (§7.38) and U1b's record (§7.40) are never rewritten.

**Cost in one line.** Expected about 0.36 USD in total (range 0.27-0.57), under holds of 1.00 USD (build tests) and 4.00 USD (the run); nothing is spent until you type the lines.

**What I need from you before anything is frozen.** Your answers in `OPEN_QUESTIONS_U1C.md`. U1c cannot be frozen until you answer Q2 (the secret commitment) and Q5 (how strict the port check is).

---

## §1 Claim states in this packet

| State | What it covers here |
|---|---|
| Real (read from files today) | U1b's hashes and counts; `merge_u1.py`, `run_u1.py`, `arms.py`, `brain.py`, `eye.py` line facts; U1b's per-part times; the item-time means I measured from P14-P21 (§16); the ledger pointer. |
| Estimated | Every AWS time and cost. Host speed `k` (how many times slower the host is than the laptop) has never been measured for this code (spec line 1429 on the thread-head copy). |
| Accepted | Nothing. No owner answer yet. |
| Open | Every item in `OPEN_QUESTIONS_U1C.md`. |
| NOT LICENSED | The Eye's ACTING (spec §7.38). Unchanged by this packet. |
| FLAG_FOR_HUMAN_REVIEW | U1 and U1b gave identical clean-world interventions on disjoint worlds: A4 1,816 and A6 10,152 (spec §7.40). U1c reports whether this happens a third time. |

---

## §2 The question

**MAIN QUESTION (decides the main word).** If only the worlds change, does U1b's result come back?
- Instrument byte-identical: RB2c brain, eye, arms A0-A6, 6 planted faults, every threshold, 39 inner hard gates, reader `merge_u1.py`.
- New: Task B draws and dialogue seeds, computed by a pinned program from the owner's committed secret and the sealed zip's sha256.
- Reference: U1b `runs/MERGED_READING.json`, sha256 `d00189a185d5110d97fc815d7b77afd01775e0e6332ed93e51c063ba7aa41a88` (re-hashed today). It reads `test_verdict` READ; `status_why` = {EYE_EARNED_KEEP true, CONCERT_EARNED_KEEP true, CHECKLIST_SUFFICES false, EYE_TIES_CHECKLIST_FEWER_INTERRUPTIONS false}; 39 of 39 hard gates true.

**SIDE QUESTION (only if the owner says yes; can never change the main word).** Does a plain rule with no eye readings do as well as the concert eye A4? The rule is A7 (§4.3, §11).

**INSTRUMENT CHECK (not science).** Does the Linux host reproduce U1b's own outputs on U1b's own inputs? If not, nothing from the fresh worlds is read.

---

## §3 What changes and what stays

### §3.A Science: only the worlds change
- Five values in lane U's `PLAN.json` come from the seed rule: `subset.draw_start`, `subset.cal_draw_start`, `subset.seeds`, `subset.cal_seed`, `replay.dl_seed`.
- All other plan values stay U1b's: `n_draws` 20, `draw_scan_max` 60, `cal_scan_max` 20, `cal_dialogues` 4, `replay.arms` [A0, A4], `tb_first_scored_draws` 2, `dl_worlds` [0, 1], `expected_thresholds`, `start_new_world_cutoff_s_before_guard` 60.
- Checked today by reading the code:
  - `run_u1.py` line 47 reads `PLAN.json` from its own folder unless the environment variable `U1_PLAN_PATH` is set. The supervisor clears that variable for every part, and gate G_WORLDS_USED checks it (§7.2).
  - `merge_u1.py` lines 147-149 read `subset` and `replay` from the folder's `PLAN.json`; line 159 takes the draws from W01's own record; line 219 checks only `len(draws) == subset["n_draws"]`.
  - So fresh worlds flow in with no science code change.
- **114 rows stay byte-identical** to U1b's `SOURCE_MANIFEST.json` (sha256 `ecba90709b58b2294ecad6fe0e2e5bf8077ca072c6fddf526774417443271640`, 121 rows):
  - 13 U1B rows: `__init__.py`, `consts.py`, `brain.py`, `brain_d.py`, `eye.py`, `faults.py`, `arms.py`, `run_u1.py`, `merge_u1.py`, `test_u1.py`, `static_check.py`, `FROZEN.json`, `FROZEN.precode.json`.
  - All 101 dependency rows (LM-T4 7, RB-I1 5, LM-T1 9, LM-T2 3, lacunarity 5, RB2c rb 11, rb2 14, vendor 8, sdg_source 1, PACKAGE_FREEZE 1, c25_reference 1, sdg_bridge_v2 10, fair_data_experiment_v2_sdg 12, design packet 12, site compiler 1, seeds.jsonl 1).
- **7 rows are replaced or dropped:** `worker.py` (minimal edit, §3.B.2), `supervisor.ps1` and `run_all_parts.ps1` (dropped; replaced by new Python files), `PLAN.json` (derived), `OWNER_APPROVAL_EVIDENCE.md` and `.template.md` (U1c's own), `C:\Python314\python.exe` (dropped; host interpreter identity recorded instead).
- **Added rows** are a frozen list (PREREG GO-5). Nothing else may be added after the seal.
- The run-folder prefix `U1B_MSI_` stays (`run_u1.py` line 34, `merge_u1.py` line 33). Renaming it would change the reader's bytes. Disclosed: on U1c this prefix does not mean the laptop. Each part's records carry the real host's instance id.
- U1c's own rules go in a new `FROZEN_U1C.precode.json` (a field-by-field transcription of `PREREGISTRATION_U1C.precode.md`), written before any U1c code. U1b's `FROZEN.json` stays byte-identical because `test_u1.test_frozen_constants_equal_FROZEN_json` reads it.
- **Precedence** (PREREG PREC-1..3): U1b's `FROZEN.json` governs constants and the 18 code tests only. `FROZEN_U1C.precode.json` governs worlds, authorization, replay rule, gates and words. U1b's `FROZEN.json` `arms.replay` text ("draws 0-1 ... seed 11") is a known erratum; U1c states the rule the code follows (`PLAN.json` replay).

### §3.B Runner: ported to Linux (not science; must pass the port check)
1. **New supervisor and driver** (`u1c_supervisor.py`, `u1c_driver.py`, standard-library Python). The per-part contract stays U1b's:
   - 300 s hard wall including preflight; worker guard `min(start + 280 s, deadline - 10 s)`; no new world within 60 s of the guard;
   - worker killed above 300 MiB resident memory (314,572,800 bytes; `VmRSS` polled every 200 ms);
   - single-use run folder; permit consumed once; the 18 unit tests run first in every part;
   - `END.json` and `SUMMARY.json` carry the fields `merge_u1.py` reads, with UTC times written in one fixed-width format, `datetime.isoformat(timespec="microseconds")` with `+00:00` (`merge_u1.py` line 214 compares these as strings).
   - Same stop rules. Dropped laptop-only checks: `COMPUTERNAME` 'MSI', the 150 MB free-RAM gate, the wait for other laptop drivers.
2. **`worker.py` minimal edit** (the diff is pinned in the seal addendum, PREREG ADD-10):
   - environment word `AWS_CPU_ONCE`;
   - the hostname check becomes an instance-id check: the permit's instance id must equal `/var/lib/cloud/data/instance-id` (read from disk; sockets stay blocked);
   - the sign-line check becomes a check of the approval record's sha256;
   - manifest `SOURCE_MANIFEST_U1C.json`;
   - installs an `open()` audit hook (`sys.addaudithook`) that logs every open with its mode;
   - records at part end: whether `U1_PLAN_PATH` was present, and the file of every loaded module (for G_MODULES).
   - Socket blocking, the test run and the `U1B_MSI_` run id stay as they are.
3. **Interpreter (owner question Q6).** Proposed: the host's system Python `/usr/bin/python3.12` (CPython 3.12.3 on Ubuntu 24.04.5) with `-I -B -u`. Not `/opt/pytorch/bin/python`: that venv holds torch and numpy, and `lm_t4/__init__.py` appends its paths after site-packages, so a site package with the same top-level name (PyPI has a package named `rb`) could win. G_MODULES catches any such shadowing. The interpreter identity (path, realpath, `sys.version`, `platform.libc_ver()`) is taken from a build-test job record, never from the laptop.
4. **Paths: zero bytes change in any dependency.** The host recreates U1b's hard-coded Windows path strings as literal folder names under one layout root, pinned by `LAYOUT_U1C.json`. This covers `RB2C`, `D14`, `CMP` and the `2026-10-15` path in `lm_t4/__init__.py`, `COMPILER_ROOT` in `lm_t1/cas_ast.py`, `ENGLISH_DIR` in `lm_t1/scoring.py`, and `SEED_FILE` in `sdg_source.py`. The two unpinned site-compiler `__init__` files (0 bytes and 142 bytes) get pinned rows. `sdg_source.COMPILER_FILE` (noetic-compass-scaffold) is not shipped; G_OPENED requires it never to be opened.
5. **Part cap** rises from 40 to 120 (`PLAN.json` `parts`, `order`, `max_parts`). It only gives room for a slower host.
6. **Memory half of A_THROTTLE is inert on Linux.** Verified today: `eye.working_set_bytes()` catches the missing `ctypes.windll` (eye.py lines 38-51) and returns None, and line 488 tests `ws is not None and ...`. Only the time half (30 s before the guard) remains. `eye.py` stays byte-identical. G_MEM_EQUIV stands in for the memory half.
7. **Lanes.** A "lane" is one queue of parts run one at a time on one processor core.
   - Lane P (PORT) re-runs U1b's own worlds to prove the port. Not scored.
   - Lane U (U1C) runs the fresh worlds. Scored.
   - Lane A (A7, only if chosen) runs the rival on lane U's fresh worlds. Read on its own.
   - Each lane has its own package copy and runs folder. A scratch copy runs the plumbing part P00 and is never merged.
8. **Added code only** (new files): supervisor, driver, seed rule, port comparator, speed check, outer reader `u1c_reader.py`, and, if chosen, `arm_a7.py`, `run_a7.py`, `merge_a7.py`, `test_a7.py`. `arms.py`, `eye.py` and `merge_u1.py` are untouched.

### §3.C Custody
- **Commit-then-reveal seeds** (§5.3). The owner commits before code; reveals after the seal.
- A **separate custodian session** builds `USED_TABLE_U1C.json`, runs the pre-seal text scan and freezes the allowed Task B slot list. It also writes its own seed derivation from the frozen text alone, without reading the builder's `u1c_seed_rule.py`. Disclosed: the custodian is a Claude session, not a person (owner question Q3).
- A **sealed-zip register** lists every sealed zip, void ones included, with its UTC time.
- The owner's **run line is typed directly** in the operator's session, never relayed by another agent. It must contain the first 8 hex characters of the zip sha256 and the cap (PREREG SEC-3..SEC-6).
- U1c's own `RESULTS.md` carries predictions against outcome, the runtime and the disclosures. No file under U1b's or U1's folders is edited; gate G_U1B_UNTOUCHED checks this.

### §3.D Two-file freeze and no amendment after the line
- `FROZEN_U1C.precode.json` is written before any code.
- `SEAL_ADDENDUM_U1C.json` is filled after the build tests and hashed into the zip. It may fill only the values listed in PREREG §P15, each from a named input that is never a U1c result (no fresh world exists before the run line).
- After the owner types the run line, nothing may change. Any change to the zip, the addendum, the approval record or the derived plan voids the attempt. The void attempt is recorded as a FAILURE of that attempt.

---

## §4 Arms

### §4.1 Main lanes P and U: U1b's arms, identical in code, order and count
Sources: U1b `FROZEN.json` arms; `eye.py`; `arms.py`.
- **A0_NO_EYE.** RB2c brain with the rb_i1 drive loop, its faculties and reflexes. No eye. A0 on the clean copy of a world is the answer key for WORSE_THAN_NO_EYE.
- **A1_REPORT_ONLY.** The eye logs what it would do; applies nothing.
- **A2_WHISPER_ONLY.** One-way whispers at fixed volume 1/4. No autonomic tier.
- **A3_ONE_WAY.** Whispers plus the autonomic tier (A_SWEEP, A_ROLLBACK, A_QUARANTINE (+LIFT), A_REVISIT, A_BALANCE, A_SEAM, A_STALL, A_THROTTLE), volume 1/4.
- **A4_CONCERT (under test).** Whispers, the autonomic tier and mutual awareness. The brain may decline with a logged reason (brain.py line 461 logs reasons only when `ctx.concert` is true; arms.py lines 163 and 297 set it true for A4 only). The brain asks the eye for a second look. Volume learned only in CAL, then frozen (U1b: 1/2).
- **A5_RANDOM_WHISPER (control).** A4's CAL rate and soft/strong mix, random targets; generator seeded from `sha256('U1:A5:' + world_id)`. Not bound by G_CLEAN; checked by G_CONTROLS.
- **A6_CHECKLIST.** The same autonomic routines after every admitted write (eye.py `Checklist.after_write`, lines 762-822). No voice, so it cannot fix F_MISALIGNED.
- **A0_REPLAY, A4_REPLAY.** Second fresh runs for G_REPLAY: first 2 scored Task B draws (CLEAN + 5 faults = 24 items) and worlds 0-1 of the first scored dialogue seed (CLEAN + F_SEAM = 8 items).
- **Untaught twin.** One per Task B world. Not an arm.
- **Size per lane:** 1,544 items = 840 Task B + 672 dialogue + 24 replay Task B + 8 replay dialogue. Per arm: 148 plantings (5 Task B faults x 20 + F_SEAM x 48) and 68 clean worlds (20 Task B + 48 dialogue).

### §4.2 Lane P scope (owner question Q4)
- **PREFIX-722 (proposed default).** Lane P runs U1b's W01, CAL and its queue until at least the first 722 items of U1b's own queue order are done. U1b's order (`run_u1.planned_worlds`, lines 187-209) is: dialogues by arm, seed, world (672 items, all 7 arms), replay dialogues (8), then Task B by draw then arm. So the first 722 items = all 672 scored dialogue items + 8 replay dialogue items + draw 100 for all 7 arms (42 items). The driver stops launching lane P parts once `queue_remaining <= 822` (1,544 - 722).
- **FULL (option).** All 1,544 items. Also merges lane P and checks a reading-level projection.
- **NONE (option).** No lane P. The port is then unproven, and the licensed sentence drops every port claim.
- Any lane P option re-runs part of U1b's inputs. A memory note says U1b is never re-run. Lane P makes no reading of record and nothing from it is merged with U1b. Still, it is the owner's call.

### §4.3 Side lane A: A7_MATCHED_RULE (owner question Q7)
Settled today by reading U1b's code, so it can be frozen before any A7 code exists (PREREG A7-1..A7-14):
- **What it is.** A new class `A7Rule` in `arm_a7.py`. It subclasses `eye.UnityEye` in mode `ONE_WAY` with volume 1/4 and `learn=False`. It overrides one method, `issue_whispers`. Everything else is the eye's own unchanged code (`eye.py` byte-identical).
- **Its routines and timing = the eye's autonomic tier.** I read every trigger today. Each one reads brain-state fields, not the eye's Θ(Ω_unity) recipe:
  - idle-thought sweep every C_SWEEP = 64 ticks: `sig["idle"]` (eye.py lines 151, 225);
  - urgent sweep after a continuity failure: `sig["learned"] != sig["chain_learned"]` or a new chain link with `break` (eye.py lines 173-200);
  - quarantine of a misaligned junction: `UnityEye.misaligned(brain)`, a static check of `brain.misaligned_window` (eye.py lines 207-210, 251-252), the same check A6 uses (line 789);
  - rollback on a failed memory check: `sig["memory"]` (lines 212-219);
  - seam restore: `sig["point_ok"]` (lines 230-237); balance: `brain.pair_history` (lines 483-485); throttle: deadline (lines 486-490).
  - `rec["sig"]` is built by the brain itself (brain.py line 382). So the "fairness rule" is settled: A7 keeps both the 64-tick cadence and the continuity trigger.
- **Its voice = one scripted message, no reading.** At each stage end, for Task B worlds, for each junction `k` in `sorted(set(UnityEye.misaligned(brain)) | set(brain.brain.quarantine))`, while the stage's STRONG budget allows (2 per stage): one STRONG whisper `{action "REFIT", obj k, drive "F7", reason "x3_stations_aligned", volume "1/4", station "S4", object "junction:k", value "SCRIPTED"}` through the same ConcertLedger channel.
  - The reason label must name an Ω_unity ingredient, or the channel refuses it with GATE (brain.py lines 472-476). `x3_stations_aligned` is the label the eye itself uses for this whisper (eye.py line 518). For A7 it is a fixed tag, not a reading.
  - No dialogue whispers and no soft whispers.
  - Repeats at each stage end while the condition holds, exactly as the one-way eye A3 does. A7 runs with `ctx.concert` false (arm label "A7"), so the brain sends no requests and its declines are unlogged (brain.py line 461). It therefore cannot see decline reasons. A3 works the same way and fixed 20 of 20 F_MISALIGNED in U1b.
- **Budget** = the eye's own per-stage budget (2 STRONG + 4 SOFT + 1 autonomic corrective action), enforced by the inherited code.
- **Volume 1/4** (FROZEN start value; A2/A3's fixed value), so A7 takes nothing from the eye's calibration. (Alternative for the owner: lane U's CAL volume.)
- **The eye's reading is still computed by the inherited `stage_end` code, but nothing in A7 reads it.** A static gate (GA-11) checks `arm_a7.py` never touches `x`, ingredients, readout, events, rows, candidates, suppress or volume bookkeeping.
- **Plainly:** A7 is A3 with its reading-driven voice replaced by a scripted re-fit. It answers: does the eye's sight, plus concert, add anything over the same involuntary routines and a fixed voice?
- **Runner.** `run_a7.py` holds copies of `arms.run_tb` and `arms.run_dl` with one pinned difference: the eye object is `A7Rule(...)` for arm "A7". Gate GA-9 checks the diff.
- **Worlds.** Lane U's fresh worlds, read-only and sha-checked against lane U's P01 record: 20 draws x (CLEAN + 5 faults) = 120 Task B items + 48 dialogues x (CLEAN + F_SEAM) = 96 dialogue items + A7_REPLAY (first 2 scored draws x 6 = 12 Task B + seed s1 worlds 0-1 x 2 = 4 dialogue) = **232 items** (one arm's replay is 16, not 32).
- **Folders.** Own package copy, own runs folder, run prefix `U1C_A7_`. Never inside lane P or lane U. Never read by `merge_u1.py`.
- **Behaviour test** (fixture worlds, never scored): with a planted F_MISALIGNED, A7 quarantines the junction, sends at least one STRONG REFIT with reason `x3_stations_aligned` at volume 1/4 within budget, and the junction ends re-fit (`wiring[k*] == k*`, not quarantined).
- **Independent review** before the seal by a session that did not write A7 (a Claude session; disclosed). A7 is never redesigned after any lane U result exists.

---

## §5 Worlds and seeds

### §5.1 Lane U (scored, fresh)
- **Task B:** `rb2.worlds_b.draw(d, true_book)`. Keep the first 20 draws `d >= D0` that pass `worlds_b.check_draw`, scanning `D0..D0+59` (U1b's rule, `run_u1._scan`, lines 51-62). Fewer than 20 passing draws fails W01, so G_INSTRUMENT fails. No rescan.
- **Task B calibration:** the first passing `d` in `C0..C0+19`.
- **Band:** `d = 750..4,829`, 68 windows of 60 draws. Draw `d` uses world seeds `10,000,001 + 200,000·d` .. `10,175,000 + 200,000·d`, each fed as `random.Random(17,000,041 + seed)`. Over the band: world seeds 160,000,001..975,975,000; stream arguments 177,000,042..992,975,041. Above X0's "largest known below 160,000,000"; above RB-W's 40,000,001 + d x 1,000,000 region (d up to 79); below GB-FRESH's 1,000,000,001.
- **Dialogues:** `score_t2.dialogues(pool, s)` for 3 scored seeds x 16 worlds = 48; calibration seed `s_cal`, worlds 0-3. Band `s = 1,000..9,999` (the largest dialogue seed used so far is 868).
- **Three derived integer families per dialogue seed** (lm_t2 `t2.py` lines 132, 199, 473), for `d < 16`, `t < 100`: `F1 = s·1000 + d`, `F2 = s·100000 + d·100 + t`, `F3 = s·7919 + d`. Each must miss the used table and U1c's own Task B blocks (seed and stream space), and all U1c families must be pairwise disjoint.
- **Unchanged from U1b:** the generator check (draws 0-1 against RB2c `c25_reference/C25_TASKB_WORLDS.json`, never scored); tracker thresholds recomputed on LM-T2 seed 5 and required to equal seam 0.841069956, tone 1.227592661, drift 0.984979914; fault keys from `d` (F_RECEIPT d mod 4; F_FADED (d+1) mod 4; F_MISALIGNED (d+2) mod 4 to its PARTNER; F_FIXATION F3 pinned to 1/64; F_MEMORY (d+3) mod 4; F_SEAM turn 6); every fault planted at keyed thought 256. A5's random streams are new because world ids are new.
- **Balance note (reported, not gated):** with 20 consecutive passing draws each fault object gets exactly 5 plantings, as in U1b. A skipped draw can make it 4-6.

### §5.2 Lane P (not scored)
U1b's own worlds: draws 100-119, calibration draw 200, seeds 131/137/139, calibration seed 149. U1b's `PLAN.json` subset, replay and version unchanged; only `parts`, `order`, `max_parts` (120) and the `note` text change. References (read-only, re-hashed today):
- P01 `WORLDS_B.json` `c0dd501f892ea81e8cc1cab342d3d8a1296c4521a402c99aedb8b744ed508684`; `DIALOGUES.json` `8cb7bd959efe7a239e3f77228e954a3ec1dba4b776d56e996b63c59157344210`; `KEYS.json` `649459adc7fc0d0f4bd698995b27626b6818779326e1c0c0011b70cc542b9758`; `THRESHOLDS.json` `c545dca2ecd19206cf98d87c03a76d212a08ca55d4700c412cefcf8540bde55c`.
- P02 `CALIBRATION.json` `3cbd94dad9abf7f7e80115affc7da81bb2daa4c89e594cc0afea19d3fd978d02` (2,551 bytes, 0 CR, 0 LF). Its canonical JSON with every `log[*].wall` removed has sha256 `b919c5b6944120cd04cced6c077f38942d2a3091b4d99f5a5552ab2506795989` (2,117 bytes). I computed this today.

### §5.3 The seed rule: commit-then-reveal (owner question Q2)
Why not "owner line + zip hash" alone: the default line is guessable, so the builder could make many candidate zips (one changed byte in a template file), compute the seeds for each, and register only the one it likes. The register only lists zips the builder calls sealed. Conversely, if the owner saw Z first, the owner could try many private words. Commit-then-reveal blocks both.
1. **Before any code:** the owner chooses a secret `S` of at least 4 random words (letters and digits only, single spaces, at least 20 characters). The owner computes `C = sha256(ASCII(S))` privately (on a phone, or with the paste block in `OPEN_QUESTIONS_U1C.md`, in a window Claude does not read) and types only `C`. `C` is pinned in the precode freeze. `S` is never typed in chat, never stored on the laptop's disk, never typed in Claude's terminal panel until the reveal.
2. **Custodian:** `USED_TABLE_U1C.json`, the text scan, the allowed slot list `A` (sorted ascending, length `N`, out of 68).
3. **Build, build tests, seal:** zip sha256 `Z` registered with UTC time.
4. **Owner sees** `Z`, the precode sha256, the seal addendum sha256 and the cost. Then types the run line `L` (contains `Z[:8]` and the cap) and reveals `S`.
5. **Derivation** (pinned program, standard library):
   - `H = sha256(ASCII(S) + b":" + ASCII(Z))` as 64 lowercase hex. `L` is not in `H`: after seeing `Z`, the owner could otherwise vary the wording of `L` to steer seeds. `L` is bound separately in the approval record.
   - `k1 = int(H[0:16],16)`, `k2 = int(H[16:32],16)`, `k3 = int(H[32:48],16)`, `k4 = int(H[48:64],16)`.
   - Task B window: `i = k1 mod N`; `D0 = 750 + 60·A[i]`.
   - Calibration window: `j = k2 mod (N-1)`; if `j >= i` then `j = j + 1`; `C0 = 750 + 60·A[j]`; scan `C0..C0+19`.
   - Dialogue seeds: `s1 = 1000 + (k3 mod 9000)`; `s2 = 1000 + ((k3 div 9000) mod 9000)`; `s3 = 1000 + ((k3 div 81,000,000) mod 9000)`; `s_cal = 1000 + (k4 mod 9000)`.
   - Moves (frozen, PREREG SEED-7, SEED-8): a window with a remaining conflict moves to the next index of `A`, wrapping from the last to the first; the calibration window skips index `i`; after `N-1` moves with no clear slot, INSTRUMENT_ERROR before any world is built. A dialogue seed that is used, repeats an earlier U1c seed, or whose families conflict, moves up by 1 inside 1,000..9,999 (9,999 wraps to 1,000), in the order s1, s2, s3, s_cal; after 9,000 moves, INSTRUMENT_ERROR. Every move is logged.
6. **Outputs:** lane U `PLAN.json` and `SEED_DERIVATION_U1C.json` as canonical bytes with no time, host, path or interpreter fields. Computed three times (custodian's independent derivation on the laptop; host before lane U's P01; laptop reader). All three must be byte-equal (G_SEED).
7. **If the owner declines commit-then-reveal:** fallback `H = sha256(UTF-8(NFC(L).strip()) + b":" + ASCII(Z))`. Then the design says plainly that the builder-picked-worlds gap is NOT closed, and the licensed sentence drops "not computable by the builder" (PREREG LIC-3).
8. **Honest limit.** Claude runs on this laptop and could in principle read files or a terminal. The protection rests on `S` never being on the laptop before the reveal. A promise not to look is not a mechanism; keeping `S` off the laptop is.

### §5.4 Excluded (any overlap refused)
Sources: X0 custodian `SEED_RULE_FRESH_W1.md` §4; `SEED_DERIVATION_X2.json`; U1/U1b `PLAN.json` and `FROZEN.json`; spec sections cited by the reader brief; plus a fresh custodian scan.
- **Task B draw indices:** 0-20; 100-159; 200-219; the X0 band 5,950-7,929 (holds X0 6,550-6,609, X1 7,760-7,819, X2-v1 5,970-6,029, X2-v2 7,410-7,469).
- **Seed and stream ranges of other generators:** fixture region 5,000,001 + d x 200,000; RB2's first generator 221,001-275,000 + d x 100,000 (d 0-19); depth rows rb_c4 BASES 9,000,000 / 9,400,000 / 9,800,000 and DEV_BASES 7,000,000 / 7,400,000 / 7,800,000, each plus up to 216,000; X0 depth 1,656,000,000-1,657,199,999; X1 depth 1,724,000,000-1,725,999,999; X2-v1 depth 1,718,000,000-1,719,999,999; X2-v2 depth 1,660,000,000-1,661,999,999; RB-G8 depth base 5,400,000 (span read by the custodian); rb_w F1 draws 40,000,001 + d x 1,000,000 for d 0-79 and 3,000-3,019, fixture 60,000,001 + d x 1,000,000; date-style seeds 2,026,100,000-2,026,101,999; GB-FRESH from 1,000,000,001; CCE-FRESH 1,800,000,001-1,801,000,000; `SEED_DERIVATION_X2.json`'s 109 ranges and 6 draw windows; the X3-X7, X-REAL and c50-c56 derivations (not yet read for Task B or dialogue use; the custodian reads them).
- **Dialogue seeds:** 3, 5, 7, 11, 29, 47, 53, 59, 67, 97, 98, 99, 101, 131, 137, 139, 149, 202, 303, 312, 579, 868.
- **Margin:** slots are struck if any used range, widened by 1,000,000 on both sides in seed space and in stream space, meets the slot's world-seed or stream block.
- **Second net (text scan), limited:** the custodian streams a frozen list of generator, seed-derivation and frozen-config files on the laptop (per-file cap 5,000,000 bytes) and strikes any slot with an integer literal within 1,000,000 of its blocks. It returns only the struck slot indices. It never reads a sealed package that has not launched. The 2026-10-19 memory note lists X-REAL v2 zip `a9b4c954` as sealed and not launched; spec §7.81 records an X-REAL run (c42). The custodian settles which packages are sealed and unlaunched at scan time and lists them in the freeze. The Codex tree is never uploaded.
- **Burned seeds:** every seed set derived from any revealed secret is listed in `SEEDS_BURNED_U1C.json` and joins the used table for later tests.

---

## §6 Part structure, lanes, stages and the timer chain

### §6.1 Host stages (one m6i.xlarge; owner question Q13)
- **S0 setup (not scored):** verify the payload inventory; record interpreter identity, `lscpu`, `/sys` thread siblings, glibc version; build the literal-path layout; run the plumbing part P00 on fixture worlds in a scratch package copy (never merged; no P00 folder may exist in a lane's runs folder); G_HOST checks.
- **S1 PORT-EARLY:** lane P runs P01 (W01) and P02 (CAL) on U1b's worlds. G_PORT_EARLY compares the four W01 files byte for byte and CAL by its canonical projection. Then the speed check (§6.3). A mismatch stops the run before any fresh world exists.
- **S2 lanes,** each pinned with `sched_setaffinity` to its own physical core from `/sys` topology:
  - lane P continues its queue to its scope (default PREFIX-722);
  - lane U runs the G_SEED recheck, P01 (W01) and P02 (CAL) on fresh worlds, then **waits**: its first queue part P03 starts only after G_PORT has passed on lane P's prefix. So no scored arm item on a fresh world runs before the port is proven on 722 items;
  - lane A starts on lane P's core once lane P has stopped and lane U's P01 exists.
  - If no pair of non-sibling CPUs exists, lanes run one after another and the speed check accounts for it.
- **S3 close:** G_PORT final (FULL scope only); `merge_u1.py` on lane U twice (byte-identical required); lane U deliverable zipped and uploaded first; then `merge_a7.py` and lane A's archive on its own upload URL.

### §6.2 The timer chain (frozen numbers; PREREG TIME-1..TIME-9)
`T0` = worker start (on c56 it came 105 s after launch: launched 18:35:50Z, worker BOOT 18:37:35Z).
- Controller force cutoff `F` = launch + 240 min.
- OS shutdown backstop = `T0` + 236 min (14,160 s); about launch + 237.75 min, so before `F`.
- Supervisor stage deadline = `T0` + 13,800 s; worker timeout 13,860 s.
- Work cutoff `W` = `T0` + 12,900 s. No new part in any lane after `T0` + 12,600 s.
- Speed-check STOP if lane U's projected end is later than `T0` + 12,000 s.
- No new A7 part after `T0` + 12,000 s. Lane U's packaging never waits for lane A.
- Packaging reserve for lane U: `W` to `T0` + 13,800 s (900 s).
- Presigned URLs valid at least 16,200 s from signing. Preflight also checks that the AWS credentials outlive 16,200 s (temporary STS/SSO keys would kill the URLs early).
- `job_supervisor.py` is regenerated with `LAUNCH_WINDOW_SECONDS` 14,400 (the run-proven copy, sha256 `3b2337ca75b189287c4591ed44671e308d37ef92d043f7bebb37ede77e6a1b01`, hard-codes 6,660 at line 31 and refuses a farther deadline at line 317). The regenerated file is no longer the run-proven one; a build-test job runs it, and its new sha256 goes in the seal addendum.
- A static preflight check confirms every timer in the generated kit matches this chain.

### §6.3 Speed check (host measurements only; PREREG RUN-9)
Runs at the end of S1, before any fresh world. All inputs come from the host:
- `s_tb` = mean of lane P's host CAL `log[*].wall` over the 6 Task B worlds; `s_dl` = mean over the 8 dialogue worlds. (These are A4 runs; A4 is among the slower arms, so this errs on the slow side.)
- `t_test` = max(host P01 `tests.cpu_seconds`, host P02 `tests.cpu_seconds`); `t_w` = host P01 + P02 `wall_seconds_worker`.
- Lane U item work `I_U = 864·s_tb + 680·s_dl`; lane P prefix work `I_P = 42·s_tb + 680·s_dl`.
- Usable item time per queue part `u = 220 - t_test - 3`; if `u <= 30`, STOP.
- Part wall bound `b = 220 + 2·max(host CAL Task B walls) + 5`.
- Projected lane U end = now + max(`t_w`, `ceil(I_P/u)·b`) + `ceil(I_U/u)·b`.
- If that is later than `T0` + 12,000 s: shed work in the frozen order (§6.4).
- The laptop numbers are not used as denominators. The earlier draft divided by U1b's P01 test CPU but wrote 28.6 s, which is P21's value (28.625); P01's was 38.266. That ratio is gone.

### §6.4 Shedding order when time is short (owner question Q11)
1. Cut lane P from FULL to PREFIX-722 (no effect under the default scope).
2. Drop A7 (`A7_NOT_RUN`).
3. STOP before any lane U world. Main word `U1C_INCONCLUSIVE` by G_WINDOW. This goes back to the owner; it does not trigger an automatic retry, because a retry on the same instance type measures the same speed.

The order is reversed from the first draft, which dropped A7 first. A7 is the only fair rival; lane P beyond the prefix is an instrument extra.

---

## §7 Hard gates

Rule: a failed hard gate is a FAILURE. It is never a pass with caveats.

### §7.1 Inner gates: U1b's 39, unchanged
`merge_u1.py` (byte-identical) computes them on lane U: 4 global (G_INSTRUMENT with its six clauses, G_TESTS 18/18, G_REPLAY, G_CONTROLS bound `E + 3·sqrt(V)`), G_UNVERIFIED / G_BYPASS / G_NO_NEW_KNOWLEDGE for each of A0-A6 (21), G_EYE_NEVER_WRITES / G_BUDGET for each of A1-A4 (8), G_CLEAN for A0, A1, A2, A3, A4, A6 (6). Attribution unchanged (`merge_u1.py` lines 489-500).

### §7.2 Outer gates: 16, new (exact predicates in PREREG §P9)
Computed by `u1c_reader.py` and checked first. Any failure gives `U1C_INCONCLUSIVE`; lane U's numbers are then archived but not read or quoted.
1. **G_CUSTODY** — zip, precode, addendum, approval record and payload hashes match; the run line's normalized bytes, byte count and sha256 match; the line contains `Z[:8]` and the cap; capture field is DIRECT_OWNER_MESSAGE; `Z` was registered before `L`.
2. **G_SEED** — `sha256(S) == C`; `S` meets the format rule; `H` recomputes; plan and seed derivation byte-equal three ways; the zip register is complete; attempt and zip counts within limits.
3. **G_FRESH** — windows inside the band, disjoint, on allowed slots, clear of the used table with margin; dialogue seeds inside 1,000-9,999, unused, distinct, families clear; all U1c families pairwise disjoint.
4. **G_WORLDS_USED** (new) — W01's recorded draws are 20 ascending values inside `D0..D0+59`, and draws plus recorded skips cover `D0..last draw` exactly; calibration draw inside `C0..C0+19` with recorded skips covering `C0..cal draw - 1`; dialogue seeds and calibration seed equal the derived plan; every lane U part's `RESULTS_U1.json` `subset` equals the derived subset; no lane U part ran with `U1_PLAN_PATH` set.
5. **G_SAME_CODE** — the 114 rows byte-identical; replaced or dropped rows exactly the frozen 7; added rows exactly the frozen list; `worker.py` diff equals the pinned diff.
6. **G_NO_PATCH** (new) — a static scan of every added or replaced Python file refuses: assignment to an attribute of an imported module or imported class; `setattr`/`delattr` on them; writes to `sys.modules`; `importlib.reload`; and, in runner files, any read of PLAN keys `version`, `subset` or `replay` other than copying PLAN bytes. Subclassing in `arm_a7.py` and `sys.addaudithook` in `worker.py` are explicitly allowed.
7. **G_HOST** — interpreter identity equals the seal addendum value; `import ctypes` works; torch and numpy blocked after `import rb`; P00 completed 18/18 in the scratch copy; instance id equals the controller's launch record.
8. **G_MODULES** (new) — every loaded module's file is under the frozen interpreter's standard library or under the lane's own package copy or the layout root; every `u1b_unity_eye.*` module comes from the lane's own copy.
9. **G_PORT_EARLY** — four W01 files byte-equal to U1b's; CALIBRATION canonical projection equal (§12.2); the listed CAL scalar fields equal.
10. **G_PORT** — every lane P item in scope equals U1b's item under the frozen exclusion list (zero tolerance); in FULL scope also the reading-level keep-list projection; the reference table's per-source sha256 values match the archive.
11. **G_MEM_EQUIV** — per counted part in lanes P and U: `ru_maxrss` from `os.wait4` on that part's worker (KiB on Linux) x 1024 < 262,144,000 bytes; no part killed at 300 MiB. Disclosed: this measures something different from U1b's `PeakWorkingSet64` polled every 200 ms.
12. **G_OPENED** — read-mode opens under the layout root are manifest rows (sha-checked by the supervisor), files in the lane's own runs folder, or members of a frozen non-manifest list each checked by its own pin (`PLAN.json` by the approval-record sha256; `LAYOUT_U1C.json` by the addendum; the permit by its run id); write-mode opens only under the lane's runs folder; `sdg_source.COMPILER_FILE` never opened in any mode.
13. **G_LANE** — over lanes P and U only: package copies differ only in `PLAN.json`; separate runs folders; no world of one appears in the other; no P00 folder in either runs folder.
14. **G_WINDOW** — lane U's deliverable uploaded before `T0` + 13,800 s and the speed check said GO.
15. **G_U1B_UNTOUCHED** (new) — before the seal and after the download, every file under `2026-10-15\u1b_unity_eye`, `2026-10-15\u1_unity_eye` and `2026-10-21\u1b` hashes equal to the 2026-10-21 records (the verification JSON and the archive's three-sha manifests at `D:\tksCAS-archive\u1b_unity_eye_20261015\` (268 files) and `D:\tksCAS-archive\u1_unity_eye_20261015\` (277 files)); the unpack log shows create-only writes and no target under those folders.
16. **G_READER_REPLAY** (new) — the host's two merges are byte-identical; the laptop's replay of the sealed `merge_u1.py` over the downloaded lane U runs folder gives the same canonical JSON sha256 as the host's. Canonical, not raw bytes: `merge_u1.py` line 528 writes in text mode, so Windows writes CRLF (U1b's own reading has 2,248 CRLF) and Linux writes LF. The 2026-10-21 verification already replayed this reader on this laptop over 24,186,272 bytes in 0.654 s.

**Count:** 39 inner + 16 outer = 55 hard gates. If the owner picks lane P scope NONE, G_PORT_EARLY and G_PORT are recorded NOT_RUN (not failed) and the licensed sentence drops the port claim; the count is then 53.

### §7.3 Side lane A7 gates (never among the 55)
GA-1 G_TESTS_A7; GA-2 G_UNVERIFIED_A7; GA-3 G_BYPASS_A7; GA-4 G_NO_NEW_KNOWLEDGE_A7; GA-5 G_EYE_NEVER_WRITES_A7; GA-6 G_BUDGET_A7; GA-7 G_REPLAY_A7 (16 items); GA-8 G_A7_BEHAVIOUR; GA-9 G_A7_COPY (pinned diff of the copied run functions); GA-10 G_A7_METRIC_EQUIV (`merge_a7.py`'s FIX, FALSE and WORSE functions reproduce `merge_u1.py`'s numbers exactly on lane U's A3, A4 and A6 items); GA-11 G_A7_NO_READING (static); GA-12 G_LANE_A7; GA-13 G_MEM_A7 and G_OPENED_A7. Any failure gives `A7_NOT_READ`. None touches a main gate or word.

---

## §8 Status words and rules

### §8.1 Inner words (unchanged; `merge_u1.py` lines 489-517)
1. INCONCLUSIVE (`test_verdict` INSTRUMENT_PROBLEM): G_INSTRUMENT, G_TESTS, G_REPLAY or G_CONTROLS fails, or a per-arm gate of A0, A5 or A6 fails.
2. EYE_HARMFUL: otherwise, a per-arm gate of A1-A4 fails, or an eye arm has (clean-world worse + faulted-world WORSE_THAN_NO_EYE) > 0.
3. Otherwise READ, adding each true word: EYE_EARNED_KEEP = FIX(A4) > FIX(A6) and FALSE(A4) < FALSE(A6) and A4 never worse and 0 unverified writes; CONCERT_EARNED_KEEP = FALSE(A4) < FALSE(A3) and FIX(A4) >= FIX(A3); CHECKLIST_SUFFICES = FIX(A6) >= FIX(A4) and FALSE(A6) <= FALSE(A4); EYE_TIES_CHECKLIST_FEWER_INTERRUPTIONS (reported); NO_EYE_WORD if none of the first three.
Definitions unchanged: FIX over 148 plantings (VOID excluded; healthy end state AND answers restored to the same arm's CLEAN run); FALSE = interventions on the 68 clean worlds; WORSE_THAN_NO_EYE against A0's clean answers where correct; DETECT within K_DETECT = 128 ticks.

### §8.2 Outer words (new; `u1c_reader.py`; first true wins)
1. `U1C_INCONCLUSIVE` — any outer gate false, or inner `test_verdict` INSTRUMENT_PROBLEM.
2. `U1C_EYE_HARMFUL` — inner `test_verdict` EYE_HARMFUL. Counts as not replicated.
3. `U1C_REPLICATES_U1B` — READ with EYE_EARNED_KEEP and CONCERT_EARNED_KEEP both true. (Both true forces CHECKLIST_SUFFICES and EYE_TIES_... false, because FIX(A4) > FIX(A6); so this is the same as all four `status_why` flags equal to U1b's.)
4. `U1C_EYE_KEEP_NOT_REPLICATED` — READ, CONCERT_EARNED_KEEP true, EYE_EARNED_KEEP false.
5. `U1C_CONCERT_KEEP_NOT_REPLICATED` — READ, EYE_EARNED_KEEP true, CONCERT_EARNED_KEEP false.
6. `U1C_DOES_NOT_REPLICATE_U1B` — READ with neither keep word.
The reader always prints the list of flipped `status_why` keys, and a REVERSAL flag when CHECKLIST_SUFFICES is true (the checklist matched or beat the eye). The first draft's single "PARTLY" word could hide such a reversal, so it is replaced by key-named words.

### §8.3 A7 words (`merge_a7.py`; first true wins)
F = FIX, C = FALSE, on the same 148 plantings and 68 clean worlds.
1. `A7_NOT_RUN` — the owner left A7 out, or shedding dropped it.
2. `A7_NOT_READ` — an A7 gate failed, or the main word is not one of words 3-6 of §8.2.
3. `A7_HARMFUL` — A7 gave any clean-world answer worse than A0's (the G_CLEAN comparison, including the 16/16 clause) or any faulted-world WORSE_THAN_NO_EYE > 0. The rival is held to the same "never worse than no eye" rule as the eye.
4. `EYE_BEATS_A7` — F(A4) > F(A7) and C(A4) <= C(A7).
5. `EYE_FIXES_MORE_THAN_A7_AT_HIGHER_COST` — F(A4) > F(A7) and C(A4) > C(A7).
6. `EYE_TIES_A7_FEWER_INTERRUPTIONS` — F(A4) == F(A7) and C(A4) < C(A7).
7. `A7_SUFFICES` — F(A7) >= F(A4) and C(A7) <= C(A4).
8. `A7_FIXES_MORE_AT_HIGHER_COST` — F(A7) > F(A4) and C(A7) > C(A4).
Words 4-8 cover every (F, C) outcome with no overlap. No A7 word changes an inner or outer word.

### §8.4 Report-only (no word depends on these)
Side-by-side table against U1b (FIX, FALSE, WORSE per arm; detect/fix/mean ticks per fault; G_CONTROLS detected/E/bound; v_frozen; A5 rate; DECLINES; escalations; requests; A5_CONTROL_COST); the FLAG check FALSE(A4) == 1,816 and FALSE(A6) == 10,152; measured host speed; the PORT tier (§12.5); A7 versus A3 (same autonomic tier, different voice).

All words above are test-reader words, not spec-legend claim words. A claim status comes only from the mapping the owner freezes (§13.4).

---

## §9 Thresholds
- **Unchanged:** every U1b value (`consts.py` sha256 `d53578a269bb2d7a125106c46ea698ac0f9ce63c0fb0b8e03aafeadb11ce29a1`, byte-identical; `test_u1` checks them against `FROZEN.json`). Time: tick, thought = 7 ticks, stage = 16 ticks. Faults: T_PLANT 256, K_DETECT 128, SEAM_TURN 6, FIX_PIN 1/64, PARTNER {0:1, 1:0, 2:3, 3:2}, VOID <= 10%. Autonomic: C_SWEEP 64, Q_MIN 2 in W_Q 64, BAL_STAGES 2, N_STALL 64, THROTTLE_MARGIN_S 30, THROTTLE_WS_BYTES 262,144,000, QUARANTINE_STUCK 256. Whispers: R = 31/32, SOFT bonus v·R/16, STRONG bonus v·R, W_ACC 16, budget 2 STRONG + 4 SOFT + 1 autonomic per stage. Volume: start 1/4, step 1/16, range [1/16, 1]. Brain: REFIT_EVERY 64, REVISIT 2 per 16 ticks, ALLOWANCE 1. Tracker: seam 0.841069956, tone 1.227592661, drift 0.984979914. Teaching 512 keyed ticks. G_CONTROLS bound E + 3·sqrt(V). Per part: 300 s wall, 280 s guard, 60 s no-new-world cutoff, 300 MiB kill.
- **U1c's own (proposed):** part cap 120; G_PORT tolerance zero with the frozen exclusion list (items: must contain `wall`; CAL: must contain `log[*].wall`; additions only from the two-process build test, §12.4); canonical JSON = `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")`; G_MEM_EQUIV limit 262,144,000 bytes; bands (Task B d 750-4,829, dialogue 1,000-9,999); margin 1,000,000; timer chain (§6.2); speed rule (§6.3); A7 volume 1/4.

---

## §10 Replication rule versus U1b
- The rule is a program (`u1c_reader.py`), never prose (§8.2).
- Judged on words only. FIX, FALSE and WORSE counts are shown side by side, unscored. Reason: U1b's FIX margin 148 vs 128 is exactly the 20 F_MISALIGNED plantings A6 cannot fix, and FALSE 1,816 vs 10,152 looks set by the world schedule, so count margins would add little. Whether to also require count margins is owner question Q9.
- U1b and U1c are never pooled. §7.38 and §7.40 stand whatever U1c shows.
- Lane P and A7 are not part of replication.

---

## §11 Mechanism-free baseline
- **In the main lanes** U1c keeps U1b's comparators unchanged: A0 (no eye; the answer key), A5 (a chance control, not a baseline; U1b: detected 2 against E 1.3160 and bound 4.6412), A6 (a rule baseline handicapped twice by design: no voice, so 0/20 F_MISALIGNED; no budget, so 10,152 clean interventions against A4's 1,816; U1b `FROZEN.json` `checklist_A6.honest_dumb_baseline_warning`). So EYE_EARNED_KEEP over A6 measures "voice plus fewer interruptions", not "the eye's readings beat the cheapest rule".
- **The house rule** says to register a mechanism-free baseline and beat the cheapest method without the mechanism. A7 (§4.3) is that rival. It is proposed as the default (owner question Q7), not as an extra.
- **Left out:** the first draft's other rival (A6 plus a re-fit, after every write). It would tie on FIX and lose on interruptions by construction, so it carries little information.

---

## §12 Port-equivalence check

### §12.1 Why
Some code uses math functions whose last bit can differ between Windows UCRT and Linux glibc: `t2.py` line 71 (`math.asin`, rounded to 9 places), `rb_i1/drives.py` (asin, acos, sin, log), `rb2/mlp.py`. RB-I1b failed on Linux for this reason; spec §7.65 records that families a and c differed in the last bit of pow/exp/log/cos results between Windows and Linux (glibc 2.39, Python 3.12.3).

### §12.2 G_PORT_EARLY (before any fresh world)
- `WORLDS_B.json`, `DIALOGUES.json`, `KEYS.json`, `THRESHOLDS.json`: sha256 equal to U1b's. `run_u1._write` (line 39-42) writes sorted-key JSON with `write_bytes`, so equal values give equal bytes on any system.
- `CALIBRATION.json`: canonical JSON with the frozen CAL exclusion list removed must equal U1b's (with only `log[*].wall` removed: `b919c5b6944120cd04cced6c077f38942d2a3091b4d99f5a5552ab2506795989`). Plus explicit equality of `v_frozen` "1/2", `a5_rate` "171/1846", `a5_p_soft` "170/171", `whispers` 171, `soft` 170, `stages` 1846, `fallback_used` false, `throttle_fired` 0.
- The first draft required CALIBRATION.json to be byte-identical. That fails on every host: it stores 14 clock times (`arms.py` lines 377 and 388; values 3.159, 2.949, 3.017, 3.582, 3.262, 3.084, 0.239, 0.252, 0.215, 0.19, 0.212, 0.206, 0.199, 0.207, read today).

### §12.3 G_PORT (zero tolerance)
- Items matched by `run_u1.item_key` and compared as canonical JSON with the frozen item exclusion list removed. I checked today: the only time field in an item record is `wall` (`arms.py` lines 213 and 337); `eye.summary()` (eye.py lines 723-732) holds counts only.
- PREFIX scope: lane P's items must include the first 722 keys of U1b's queue order. FULL scope: all 1,544.
- FULL scope only: lane P's `MERGED_READING` keep-list projection {test_verdict, status_words, status_why, hard_gates, marks} must hash to `a8335073c29b1295318925ca0c4cb3dd0ca22ecf4e309640e7d4714e8b1c9473` (computed today from `d00189a1…`; `marks` holds no part names, `wall` or `seconds` fields).
- Why not the first draft's reading hash: I recomputed today. Dropping `parts` plus `w01.seconds`, `w01.unit_wall`, `cal.seconds`, `cal.unit_wall` gives `f70641bb9b01ca64154f643dbe1329a5fbfef246f9e103483d59f7ce9d098dce`; keeping `parts` and dropping only time fields gives `ad0b5da8254f93d9039b87c88bc62f30fa5dcc99ac71af611714be2ee193d9cd`. `parts` records how items split across parts (U1b: P03 356, P04 336, ...), which depends on host speed, so any hash over it fails by construction.
- **When it is computed:** on the host, before lane U's first queue part (PREFIX) and again before lane U's merge (FULL). If it fails, lane U's queue never starts (PREFIX) or lane U is not merged (FULL); lane U's raw parts ship only as a sealed archive identified by its sha256 and are not unpacked.
- **Reference table:** built in a build-test job on AWS from a read-only copy of U1b's `runs/` (24,186,272 bytes), never on the laptop. It records the sha256 of every U1b source file it read; G_PORT checks those against the archive's three-sha confirmations before comparing any item.

### §12.4 Proving zero tolerance can pass before the seal
Build test BT-A runs the same fixture worlds (W01, CAL and one queue part) in two fresh processes on the host and compares whole canonical items and CAL. Every field that differs goes into the frozen exclusion list in the seal addendum, with the record that shows the difference. Under `-I` Python's string hash seed stays random per process, so a field built by walking a set could differ. If any field that G_REPLAY reads differs (answers_sha256, link count, ledger sha256), U1c cannot be sealed: that would be a determinism defect in U1b's own code, flagged FLAG_FOR_HUMAN_REVIEW, and the owner decides. The exclusion lists cannot change after the run line.

### §12.5 Diagnosis tiers (report only)
PORT_EXACT (everything equal under the exclusion list) / PORT_ANSWERS_EQUAL (answers equal, some ledger or other field differs) / PORT_DIFFERS. Only PORT_EXACT passes (owner question Q5 must be answered before the freeze). Lane P's own replay items are reported beside G_PORT: if lane P matches itself but not U1b, the cause is the platform; if lane P does not match itself, the cause is nondeterminism.

---

## §13 What a pass licenses, what a fail means

### §13.1 A pass
A pass means `u1c_reader.py` prints `U1C_REPLICATES_U1B`: all outer gates true and the inner reading READ with both keep words.

The bounded sentence is chosen by the reader from the recorded port scope (PREREG LIC-2):
- **FULL:** "On fresh synthetic worlds whose seeds came from the owner's committed secret and the sealed package hash, with U1b's science code and reader byte-identical, on one AWS Linux host where the port reproduced all 1,544 of U1b's items (with the memory half of A_THROTTLE inert on Linux and G_MEM_EQUIV in its place), U1b's frozen reader again gave READ with EYE_EARNED_KEEP and CONCERT_EARNED_KEEP: the concert eye fixed more planted faults than an after-every-write checklist with fewer clean-world interventions, fixed as many as one-way whispers plus the autonomic tier with fewer interventions, gave no keyed answer worse than no eye, and made 0 unverified writes."
- **PREFIX:** the same, with "where the port reproduced U1b's world, key, threshold and calibration files and the first N of U1b's items in U1b's queue order (all 7 arms on every scored dialogue and on draw 100)", N taken from the record.
- **NONE:** the same, with "(the port to Linux was not checked against U1b's own outputs)".
- If commit-then-reveal was not used, "whose seeds came from the owner's committed secret" becomes "whose seeds came from the owner's line and the sealed package hash (the builder could compute them before the seal)".

**Its limits.** Ceiling SYNTHETIC_ONLY. RB2c only; U1b's six planted fault types only; one run. It tests whether U1b's words survive fresh worlds not picked by the builder. The instrument changes U1b chose after seeing U1's numbers are kept, not tested. U1b's authority record (an operator-composed sign line) is unchanged.

### §13.2 What each failure means
- G_PORT_EARLY fails: the port changes a world, key, threshold or calibration file. Stops before any fresh world, at about 0.03 USD. Nothing about the eye is learned; the record gains a portability negative. Next step is the owner's (Q12).
- G_PORT fails: the port changes an item answer on U1b's own inputs. Lane U's queue never starts (PREFIX) or is not merged (FULL). Same meaning.
- Speed STOP: `U1C_INCONCLUSIVE` by G_WINDOW, before any fresh world. Back to the owner (no automatic retry).
- Any other outer gate fails: `U1C_INCONCLUSIVE`, an instrument or custody problem; nothing is read.
- Inner INCONCLUSIVE: no eye word; U1b stays one READ that was not replicated.
- `U1C_EYE_HARMFUL`: a FAILURE of the eye's acting on fresh worlds; kept beside U1b; U1b's keep words recorded as not replicated; any later acting proposal must address it.
- `U1C_EYE_KEEP_NOT_REPLICATED`, `U1C_CONCERT_KEEP_NOT_REPLICATED`, `U1C_DOES_NOT_REPLICATE_U1B`: U1b's words depended on its worlds; the flipped keys are named and kept as a negative.
- `A7_SUFFICES`: not a failure of the replication. It is the strongest negative for the eye's sight: U1b's edge over A6 came from voice and schedule, as U1b's own freeze warned. Under the proposed mapping it blocks any move of Eye ACTING off NOT LICENSED.
- `A7_HARMFUL`: the rival harmed answers; it does not count against the eye. `A7_NOT_READ`: an instrument problem, not evidence either way.
- Every outcome is kept. Negatives are never deleted. Money spent and cleanup (verified three ways) are recorded either way.

### §13.3 NOT LICENSED, whatever U1c shows
Real data or real use; the canonical wide brain RB-W1, the live loop or the chat; the HELM-level involuntary duties (restart check, Atlas rebuild, checkpoints, hard stops); unknown faults; "better than a checklist" in general; statistical superiority; any pooling of U1b and U1c; the decline-with-reason and escalation paths if DECLINES stays vacuous (U1b: '0/0'; 0 escalations); Linux-Windows equivalence beyond the items compared; consciousness or awareness; any change to a later word (no later word rests on U1b's keep words; later sections reuse only the ConcertLedger class, the constants and the design idea).

### §13.4 Claim status (the owner decides; frozen before code; Q8)
Proposal:
- `U1C_REPLICATES_U1B` with A7 `A7_NOT_RUN`, `A7_NOT_READ`, `A7_HARMFUL`, `A7_SUFFICES`, `A7_FIXES_MORE_AT_HIGHER_COST` or `EYE_FIXES_MORE_THAN_A7_AT_HIGHER_COST`: the bounded sentence carries ENGINEERED-NOT-VALIDATED (the planted-fault precedent: §7.73, §7.74, §7.77, §7.78). Without a fair rival the keep words over A6 are close to built in, so VALIDATED would claim more than the test shows.
- `U1C_REPLICATES_U1B` with A7 `EYE_BEATS_A7` or `EYE_TIES_A7_FEWER_INTERRUPTIONS`: VALIDATED is on offer for the bounded sentence (the legend: "passed its own pre-registered criterion against matched controls"), still SYNTHETIC_ONLY.
- Eye ACTING moves off NOT LICENSED only in that second case, and only to the bounded sentence. In every other case it stays NOT LICENSED.
- Recorded in the next free spec section when the result lands (7.120 was free on 2026-10-21; 7.119 is reserved for c56), in the same commit as the result, beside §7.38 and §7.40.

---

## §14 Forecast
Builder's forecasts (Claude's). Report-only; they go into the precode freeze before any code. Not the owner's. No coordinator forecasts relayed; the owner and coordinator may add their own (Q17).
- **Port and clock:** P(G_PORT_EARLY holds) 0.75 (CAL now exercises the drive math on 14 worlds); P(G_PORT on the prefix | early holds) 0.90; P(the run fits the window | port holds) 0.90 (my measured-rate model fits up to k about 2.75; the contended model up to about 1.9; the only recorded host/laptop ratio for this code family is r 1.2427, spec §7.65, measured on m6i.8xlarge).
- **Reading, given the port holds and the run completes:** `U1C_REPLICATES_U1B` 0.80; inner INCONCLUSIVE 0.10; `U1C_EYE_HARMFUL` 0.05; a NOT_REPLICATED word 0.05. End to end about 0.75 x 0.90 x 0.90 x 0.80 = 0.486. The most likely non-replication is INCONCLUSIVE from the port or the clock, not an eye negative.
- **Counts if READ:** v_frozen 1/2 (0.85); FIX A3 = A4 = 148 (0.85); A6 = 128 with F_MISALIGNED 0/20 (0.90); A2 = 60 (0.80); A0 = A1 = 0; A5 about 10-25; WORSE 0 for A1-A4 (0.85), A6 > 0 all F_MISALIGNED (0.85); FALSE order A6 > A3 > A4 (0.90); FALSE(A4) = 1,816 and FALSE(A6) = 10,152 again (0.60); G_CONTROLS holds (0.90); DECLINES vacuous again (0.75).
- **A7 (given the main word is READ):** `A7_SUFFICES` 0.65; `EYE_BEATS_A7` or `EYE_TIES_A7_FEWER_INTERRUPTIONS` 0.15; `EYE_FIXES_MORE_THAN_A7_AT_HIGHER_COST` 0.05; `A7_HARMFUL` 0.05; `A7_NOT_READ` 0.10. Why: A7 shares A3's autonomic tier exactly; A3 fixed all 148 in U1b; A2's re-fit whispers at volume 1/4 fixed 20/20 F_MISALIGNED; on clean worlds A7 should spend about A3's 1,200 sweeps and no whispers, while A4 spent 588 soft whispers plus 1,228 sweeps. FIX(A7) = 148 (0.75); FALSE(A7) between 1,100 and 1,300 (0.70).
- **Honest summary:** replication is likely. The eye's keep over a fair plain rule is where it is most at risk.

---

## §15 Risks
1. **Float drift between Windows and Linux** (§12.1). PORT-EARLY catches world/key/threshold/calibration drift for about 0.03 USD; the prefix catches item drift before any scored fresh-world item. A port pass on U1b's inputs is a strong sample, not a proof for every fresh world.
2. **Host speed unmeasured.** Mitigated by the host-only speed rule and the shedding order. A speed STOP goes back to the owner.
3. **Literal-path layout.** `Path.parent` of a single literal name is '.', so some path handling could land in the wrong place. G_OPENED, G_MODULES and G_PORT would catch it. Fallback: edited copies under a new freeze (Q12).
4. **Python 3.12.3 has never run this code.** Build tests run the 18 tests and P00 before the seal.
5. **Commit-then-reveal depends on the owner keeping S off the laptop** (§5.3 item 8).
6. **The derived plan is pinned through the payload and approval record, not the sealed zip.** New custody plumbing; G_SEED and G_WORLDS_USED check it.
7. **Lane P re-runs U1b inputs** against the memory note "never re-run U1b" (Q4).
8. **Presigned URLs or credentials expiring** before the window ends (preflight check, §6.2).
9. **The laptop must run the controller for up to 4 hours** with the owner's snapshot of 354 MB free of 16 GB (2026-09-23; 1,262,984 KB free when I checked today). If it dies, the host's backstop terminates it, and a manual cleanup run follows. Closeout then charges up to the instance's own termination time from `describe_instances`, capped at the OS backstop, not up to the late cleanup receipt.
10. **Two lanes on two physical cores** may land on hyperthread siblings; the driver pins from `/sys` topology or runs lanes in sequence.
11. **A7 is new code.** Its fairness is settled by reading U1b's code; a broken A7 gives `A7_NOT_READ`; it is never redesigned after results.
12. **U1b weaknesses that replication does not fix:** faults with signatures the eye is built to check; A6 cannot fix F_MISALIGNED by construction; FALSE counts look set by the schedule; DECLINES vacuous and 0 escalations; one-sided low-power G_CONTROLS; v_frozen set by the calibration order; one run.
13. **The `U1B_MSI_` prefix** inside byte-identical code can mislead a reader (disclosed; G_U1B_UNTOUCHED and the marker file `LANE_P_NOT_A_READING_OF_RECORD.txt` keep lane P apart from U1b's record).
14. **Shared AWS ledger.** Every hold re-reads the pointer sha256 immediately before writing.
15. **Dialogue families cross other regions** (F1 crosses the depth rows 7,000,000-10,016,000; F3 crosses them for s about 884-1,265; F2 crosses U1c's own Task B band), so some seed moves are expected; they are logged by rule.
16. **The deliverable.** The c56 worker skips any file over 64 MiB when zipping and the controller reads the deliverable into memory (reviewer's reading of `worker_c56.sh` and `aws_control_c56.py`; not re-read by me). The U1c worker lists skipped files and fails if any exist; the controller streams the download to disk; BT-A measures the zipped size of a U1b-sized runs folder.

---

## §16 Sources read for this packet (2026-10-21, read-only)
- `C:\Users\wakil\Documents\Codex\2026-10-15\u1b_unity_eye\`: `PLAN.json`; `run_u1.py` lines 25-60, 60-239; `merge_u1.py` lines 145-229 and 484-533; `arms.py` (grep: lines 161-213, 295-337, 362-388); `brain.py` lines 380-519 and grep; `eye.py` lines 30-69, 72-127, 128-249, 249-334, 454-499, 500-639, 720-742, 743-842; `consts.py` (grep); `runs/MERGED_READING.json` (hashed and parsed: top-level keys, projections); `runs/U1B_MSI_P02/CALIBRATION.json`; `runs/U1B_MSI_P01, P02, P18, P21/SUMMARY.json`; `runs/U1B_MSI_P14..P21/RESULTS_U1.json` (item `wall` means; see `COST_AND_SIZING_U1C.md` §1).
- `C:\Users\wakil\Documents\Codex\2026-10-20\r1_wave7\approval_v9\pkg\HELM_R1_W7_20261020\kit\job_supervisor.py` (grep lines 6, 31, 317); `build_payload_c52.py` line 85 (grep).
- `C:\Users\wakil\Documents\Codex\AWS_COMBINED_ALLOCATION_CURRENT.json` (hashed; four fields).
- Spec sheet thread-head copy `...\scratchpad\spec_sheet_thread_head.md` lines 1429 and 2226-2237.
- Everything else is from the workflow's reader brief, the three draft designs, the judge's notes and the reviewers' findings, as cited in `REVIEW_LOG_U1C.md`.
