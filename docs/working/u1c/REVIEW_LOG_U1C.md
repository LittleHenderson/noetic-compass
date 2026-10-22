# U1c — review log

Status: DESIGN ONLY. This log records the three draft designs, the judge's scores, and every reviewer problem with its disposition. "Verified today" means I re-checked the reviewer's factual claim against the files on 2026-10-21 (read-only).

## 1. The three designs and the judge's scores
Scale 0-5 per criterion, maximum 35. Criteria: (1) clear question U1b left open; (2) reading decided by a program; (3) seeds new and not builder-chosen; (4) mechanism-free baseline; (5) port shown to change no answer; (6) cost and size; (7) scope.

| Design | (1) | (2) | (3) | (4) | (5) | (6) | (7) | Total |
|---|---|---|---|---|---|---|---|---|
| Design 1: replication-purist, two lanes on AWS CPU (full PORT lane + fresh U1C lane) | 5 | 5 | 4 | 2 | 5 | 4 | 5 | 30 |
| Design 2: 3x size, A7 + A8 rivals inside the instrument, 16 shards on m6i.8xlarge | 4 | 4 | 5 | 5 | 2 | 3 | 2 | 25 |
| Design 3: Part R replication (one lane, sequential), optional firewalled A7, Part W split off as EYE-ACT-1 (spec 7.122, PR #454; named U1d in the first draft) | 5 | 4 | 3 | 3 | 3 | 3 | 5 | 26 |

The judge recommended a synthesis on Design 1 (grafting Design 2's matched-schedule rival, five rival words, custodian, three-family seed check, forecasts; and Design 3's EYE-ACT-1 (spec 7.122) split, firewall, build-test jobs, Python 3.12.3 default, text-scan net, speed check, anchor fallback). This packet starts from that synthesis and applies the reviewer fixes below.

## 2. Reviewer problems and dispositions
Totals: 8 BLOCKER, 29 MAJOR, 28 MINOR. All 8 BLOCKERs are FIXED in the design. One BLOCKER fix (P-B3, seed custody) needs the owner's agreement to commit-then-reveal: U1c cannot be frozen until the owner answers Q2, and if the owner declines, the design says plainly that the builder-picked-worlds gap is not closed (PREREG SEED-1, LIC-3).

Where: `D§` = `DESIGN_U1C.md` section; IDs like `GO-9`, `SEED-7` = `PREREGISTRATION_U1C.precode.md` rules; `C§` = `COST_AND_SIZING_U1C.md`; `Qn` = `OPEN_QUESTIONS_U1C.md`.

### 2.1 Pre-registration lens
| ID | Severity | Problem (short) | Disposition |
|---|---|---|---|
| P-B1 | BLOCKER | G_PORT_EARLY demanded a byte-identical CALIBRATION.json, which holds 14 clock times. | FIXED. Verified today: 14 `wall` values (3.159 ... 0.207), written at arms.py lines 377/388. Four W01 files stay byte-compared; CAL compared as canonical JSON with `log[*].wall` removed (U1b value `b919c5b6…`, computed today) plus 8 named scalars. GO-9, REF-7, D§12.2. Two-process host proof before the seal: D§12.4, ADD-5. |
| P-B2 | BLOCKER | Lane P reading hash fails by construction (`parts`) and "time fields" was undefined. | FIXED. Verified today: dropping `parts` + 4 time fields gives `f70641bb…`; keeping `parts` gives `ad0b5da8…`. G_PORT now decides on item-level equality; FULL scope adds a keep-list projection {test_verdict, status_words, status_why, hard_gates, marks} = `a8335073…`, computed today and written into the precode (not "at the seal"). GO-10, REF-2, D§12.3. |
| P-B3 | BLOCKER | The builder could shop seeds by resealing (guessable line); the owner could shop by private word after seeing Z. | FIXED (owner must agree, Q2). Mandatory commit-then-reveal: owner commits `C = sha256(S)` before code; `H = sha256(S + ":" + Z)`; L not in H. Secret format rule; S kept off the laptop. Fallback stated with LIC-3. SEC-1..SEC-2, SEED-1, GO-2, D§5.3. |
| P-M1 | MAJOR | Zero-tolerance whole-item comparison never shown possible; hash randomisation. | FIXED. BT-A runs identical fixture inputs in two fresh host processes; differing fields join the exclusion list with evidence before the seal; frozen after L; a G_REPLAY-field difference blocks the seal (FLAG_FOR_HUMAN_REVIEW). D§12.4, ADD-4, ADD-5, NOAMEND-3. |
| P-M2 | MAJOR | Gate inputs set after the precode freeze; no amendment rule. | FIXED. Two-file freeze: precode + seal addendum listing every fillable value and its allowed input; pre-L amendments logged and shown; none after L; change after L voids the attempt. D§3.D, §P15, STOP-9. |
| P-M3 | MAJOR | Port-strictness question open until numbers exist; G_PORT known only after lane U merged; unlimited reruns. | FIXED. Q5 must be answered before the freeze (§P17). G_PORT computed on the host before lane U's queue (PREFIX) or merge (FULL); on failure lane U ships only as a sealed archive by sha256. Attempt caps: ≤ 2 launches, ≤ 3 zips; seeds burned and listed. RUN-7, STOP-4, ATT-1..ATT-5, SEED-13. |
| P-M4 | MAJOR | Builder-written runner code could patch science modules; added rows not covered. | FIXED. New G_NO_PATCH static gate; G_SAME_CODE restated as 114 + 7 + frozen added list; worker.py diff pinned; independent review of new files. GO-5, GO-6, ADD-8, ADD-10, A7-13. |
| P-M5 | MAJOR | `U1_PLAN_PATH` could swap the plan; reader never checks draw starts. | FIXED. Verified today: run_u1.py line 47 reads the variable first; merge_u1.py line 159 takes draws from W01 and line 219 checks only the count. New G_WORLDS_USED checks draws, skips, calibration draw, seeds, every part's subset and the variable's absence; the supervisor clears it. GO-4, RUN-3. |
| P-M6 | MAJOR | Side lane A7 not walled off (G_LANE, G_WINDOW, G_MEM, G_OPENED). | FIXED. Lane A: own copy, own runs folder, prefix `U1C_A7_`, read-only sha-checked access to lane U's W01; G_LANE over P and U only; own A7 gates; lane U never waits for lane A; A7 cut-off at T0+12,000 s. RUN-5, RUN-12, RUN-13, GA-12, GA-13, D§4.3. |
| P-M7 | MAJOR | Builder controls A7's strength; fairness branch left to judgement. | FIXED. Settled today by reading code: every inherited trigger reads brain state (eye.py 151, 173-200, 207-219, 225-237, 483-490; brain.py 382). A7 = the eye's own unchanged autonomic code with a scripted re-fit voice, frozen exactly in A7-1..A7-14; behaviour test A7-12; independent review A7-13. |
| P-M8 | MAJOR | A7 judged by a looser rule than A4 (no WORSE clause). | FIXED. `A7_HARMFUL` (clean worse or faulted WORSE > 0) checked before the five comparison words. WA-3, D§8.3. |
| P-M9 | MAJOR | "Line names the zip sha" untrue; "exactly as typed" not programmable; relayed lines. | FIXED. Capture rule: NFC, strip, UTF-8; must contain `Z[:8]` and the cap token; DIRECT_OWNER_MESSAGE only; byte count and sha shown back and confirmed. SEC-3..SEC-6, GO-1. |
| P-M10 | MAJOR | "Closes U1b's two custody gaps" overclaims. | FIXED. Limit text now: tests fresh unpicked worlds; post-U1 instrument choices kept, not tested; U1b's authority record unchanged. LIC-4, D§13.1. |
| P-M11 | MAJOR | Fixed sentence while port scope can shrink; A_THROTTLE omission. | FIXED. Three sentences (FULL / PREFIX with N / NONE) picked by the reader from the recorded scope; A_THROTTLE phrase added. LIC-2, D§13.1. |
| P-M12 | MAJOR | VALIDATED offered even without A7. | FIXED. Proposal: without an A7 win or tie the ceiling is ENGINEERED-NOT-VALIDATED; stated plainly in Q8. LIC-6, LIC-7, D§13.4. |
| P-M13 | MAJOR | Research choices (replication criterion, PARTLY word, outer-gate set, shedding order) presented as defaults. | FIXED. Each is now an owner question with a recommended answer and one-line reason (Q9, Q10, Q11); every default is marked proposed. |
| P-M14 | MAJOR | Lane P outputs could be confused with or overwrite U1b's record. | FIXED. New G_U1B_UNTOUCHED (before/after re-hash against the 2026-10-21 records and archive); create-only unpack that refuses U1b/U1 paths; `LANE_P_NOT_A_READING_OF_RECORD.txt` marker. GO-15, RUN-14. |
| P-M15 | MAJOR | Text scan of the whole Codex tree could read sealed, unlaunched exams. | FIXED. Custodian-only scan of a frozen file list, per-file cap, excluding sealed unlaunched packages (listed in the freeze), returning only struck slot indices; Codex tree never uploaded. SEED-10, ADD-2, D§5.4. |
| P-m1 | MINOR | Default path re-ran all of U1b against the "never re-run" note. | FIXED. Default is PREFIX-722; FULL is an option with its extra cost shown. RUN-4, Q4, C§3.5. |
| P-m2 | MINOR | The three seed derivations are not independent; "separate" custodian overstated. | FIXED. Custodian derives from the frozen text without reading `u1c_seed_rule.py`; disclosed as a Claude session; owner asked (Q3). SEED-11. |
| P-m3 | MINOR | Window-move rule not programmable (wrap, skip). | FIXED. SEED-7. |
| P-m4 | MINOR | No byte-exact PLAN template; stale prose fields. | FIXED. PLAN-1..PLAN-4 (exact replaced keys, new `rule`/`note` text, byte format, BT-A check). |
| P-m5 | MINOR | No precedence between U1b FROZEN.json and U1c's freeze. | FIXED. PREC-1..PREC-3. |
| P-m6 | MINOR | k_hat used 28.6 s labelled as P01's. | FIXED. Verified today: P01 tests CPU 38.266, P21 28.625. Laptop-ratio speed check replaced by a host-only rule. RUN-9, D§6.3. |
| P-m7 | MINOR | ru_maxrss unit and process not frozen. | FIXED. `os.wait4` per worker, KiB x 1024; disclosed metric difference. GO-11. |
| P-m8 | MINOR | Build-test job count unbounded and stated two ways. | FIXED. At most 3 jobs (30/20/10 min), sum 0.92 ≤ 1.00. ATT-6, C§5. |
| P-m9 | MINOR | "Fixes to U1b's record slips" could read as editing U1b's RESULTS.md. | FIXED. Reworded: U1c's own RESULTS.md carries them; no U1b file edited; enforced by G_U1B_UNTOUCHED. D§3.C, GO-15. |
| P-m10 | MINOR | PARTLY can hide a reversal. | FIXED. Key-named words plus flipped-keys list and REVERSAL flag. WO-3..WO-7. |
| P-m11 | MINOR | Retry rule after a speed stop unclear. | FIXED. Same-zip retry only for plumbing; any in-zip change is a new zip with new commitment and seeds; speed STOP goes to the owner. ATT-2, ATT-3, STOP-6. |
| P-m12 | MINOR | Reference table built by builder code could drift. | FIXED. Table records the sha256 of every U1b source it read; G_PORT checks them against the archive first. GO-10, ADD-6. |

### 2.2 Instrument lens
| ID | Severity | Problem (short) | Disposition |
|---|---|---|---|
| I-B1 | BLOCKER | CALIBRATION.json cannot be byte-identical (14 wall values). | FIXED (same as P-B1). |
| I-B2 | BLOCKER | MERGED_READING `parts` table depends on host speed; hash fails after full spend. | FIXED (same as P-B2); time-dependent part-keyed fields excluded by the keep-list. |
| I-B3 | BLOCKER | A7 inside lane P breaks G_LANE and lane P's G_INSTRUMENT / G_PORT. | FIXED. Lane A with prefix `U1C_A7_`, own copy and runs folder; never globbed by `merge_u1.py` (`U1B_MSI_P*`, verified line 47). RUN-5, GA-12. |
| I-M1 | MAJOR | The 32-item anchor cannot be run by U1b's unchanged queue. | FIXED. Verified today (run_u1.py lines 187-209): the anchor is replaced by PREFIX-722 = the first 722 items of U1b's own queue order, covering all 7 arms; the driver stops lane P at `queue_remaining <= 822`; the sentence names N. REF-10, RUN-4, LIC-2. |
| I-M2 | MAJOR | k_hat denominators wrong and from mixed laptop states. | FIXED. Host-only speed rule from the host's own CAL walls and test times; laptop numbers used only for sizing, now from the uncontended P14-P21 stretch I measured today. RUN-9, C§1.3, C§3. |
| I-M3 | MAJOR | Main lanes lack a fair baseline; A7 optional and shed first. | FIXED. Shedding reversed (lane P first, then A7, then STOP); A7 proposed as the house-rule default; no status above ENGINEERED-NOT-VALIDATED without an A7 win or tie. RUN-11, Q7, LIC-6. |
| I-M4 | MAJOR | A7 undefined against brain code (reason gate, concert logging, idle signal, requests, retry). | FIXED. Verified today: brain.py 472-476 (reason must be an ingredient), 461 (reasons logged only under concert), 414 and 672 (requests only under concert); eye.py 151/225 (`sig["idle"]`), 518 (`x3_stations_aligned`). Frozen: A7 in the eye slot via `UnityEye` subclass, `concert` false, reason `x3_stations_aligned`, STRONG/F7/REFIT, volume 1/4, re-sent each stage while misaligned or quarantined within budget. Deviation from the reviewer's "match A4's reason-based retry": with `concert` false reasons are unlogged, so A7 follows A3's one-way repeat pattern, which fixed 20/20 F_MISALIGNED in U1b. Behaviour test A7-12. A7-1..A7-12. |
| I-M5 | MAJOR | `merge_a7` cannot reuse `merge_u1`'s FIX closures; drift risk. | FIXED. G_A7_METRIC_EQUIV: `merge_a7`'s functions must reproduce `merge_u1`'s FIX, FALSE and WORSE on lane U's A3, A4, A6 items exactly. GA-10. |
| I-M6 | MAJOR | G_OPENED fails on legitimate non-manifest files; hook location unspecified. | FIXED. Allow-list (manifest rows, lane runs folder, frozen non-manifest list with pins); writes only in lane runs; hook installed by the replaced worker.py. GO-12, RUN-2(f). |
| I-m1 | MINOR | `U1_PLAN_PATH` leftover after P00; P00 folder merged as extra. | FIXED. Supervisor clears the variable; P00 in a scratch copy; reader checks subsets and absence of P00 folders. RUN-3, RUN-8, GO-4, GO-13. |
| I-m2 | MINOR | Seed program output missing required PLAN keys; stale prose. | FIXED. PLAN-1 (copy U1b's plan and replace named keys only). |
| I-m3 | MINOR | A7 replay miscounted (248). | FIXED. 232 items (16 replay for one arm). A7-10, D§4.3, C§3.2. |
| I-m4 | MINOR | ru_maxrss in KiB; RUSAGE_CHILDREN mixes parts. | FIXED. `os.wait4` on each worker pid. GO-11. |
| I-m5 | MINOR | Mixed timestamp widths can mis-order string comparison (merge_u1.py line 214). | FIXED. Verified line 214. One fixed-width format plus a unit test. RUN-2(h), D§3.B.1. |
| I-m6 | MINOR | Outer reader trusts host gate values; laptop merge feasible. | FIXED. G_READER_REPLAY: the laptop replays `merge_u1.py` (as on 2026-10-21, 0.654 s) and compares canonical JSON (Linux LF vs Windows CRLF; verified line 528 text-mode write and 2,248 CRLF in U1b's file). The 1,544-item port comparison stays on the host with its table hash shipped (disclosed). GO-16. |
| I-m7 | MINOR | "Anchor only" still re-runs U1b; question misleading. | FIXED. Q4 gives FULL / PREFIX / NONE and says that every lane P option re-runs part of U1b. |
| I-m8 | MINOR | Nondeterminism could be misread as port drift. | FIXED. Diagnosis rule: report lane P's own replay next to G_PORT; BT-A two-process check. D§12.5. |

### 2.3 Operations and cost lens
| ID | Severity | Problem (short) | Disposition |
|---|---|---|---|
| O-B1 | BLOCKER | CALIBRATION byte comparison always fails; forecast 0.80 really 0. | FIXED (same as P-B1); forecast recomputed to 0.75 (D§14). |
| O-B2 | BLOCKER | G_OPENED fails on every run (non-manifest PLAN, runs files); c43 precedent. | FIXED. Restated allow-list; exact gate code run in BT-A before the seal. GO-12, C§5. |
| O-M1 | MAJOR | Speed model mixes uncontended k with contended constants; Design 3 drop reason false; r 1.2427 ignored. | FIXED. Model U from today's measured P14-P21 rates and Model C kept as a slow bracket; r 1.2427 cited as a prior (spec §7.65); Design 3 drop reason corrected (verified: replay items ran in P21, uncontended: A0 1.5369, A4 2.3527 s/item); parts rounded up. C§1.3, C§3. |
| O-M2 | MAJOR | Prose rule and f70641bb disagree. | FIXED (with P-B2); both hashes recomputed today and the gate uses a defined keep-list. |
| O-M3 | MAJOR | Long-window timer envelope unproven; pinned job_supervisor refuses deadlines beyond 6,660 s. | FIXED. Verified: LAUNCH_WINDOW_SECONDS 6660 at line 31, refusal at line 317, sha 3b2337ca. One numeric chain TIME-1..TIME-9; regenerated supervisor pinned in ADD-7 and exercised in BT-A; static preflight timer check. D§6.2. |
| O-M4 | MAJOR | ru_maxrss compared raw would always pass. | FIXED. KiB x 1024 per worker; BT-A memory trip test. GO-11, C§5. |
| O-M5 | MAJOR | Machine-bound pins (hostname, interpreter, cross-OS byte equality of seed files). | FIXED. Instance id from cloud-init file and launch record; interpreter identity from BT-A in ADD-3; seed and plan files canonical bytes with no time/host/path fields. RUN-2(c), GO-7, ADD-3, SEED-12, PLAN-1. |
| O-M6 | MAJOR | A7 leaks into G_LANE and G_WINDOW. | FIXED (same as P-M6). |
| O-M7 | MAJOR | P00 location unspecified; would be merged. | FIXED. Scratch copy; never merged; checked. RUN-8, GO-13. |
| O-M8 | MAJOR | 1.00 build-test cap covers only one 60-minute job by the house rule. | FIXED. Three jobs at 30/20/10 min; holds 0.46/0.31/0.16; sum 0.92. ATT-6, C§5. |
| O-m1 | MINOR | `/opt/pytorch/bin/python` venv can shadow U1b module names. | FIXED. `/usr/bin/python3.12 -I -B -u` proposed; G_MODULES checks every module's origin. RUN-2(a), GO-8, Q6. |
| O-m2 | MINOR | A dead laptop inflates the charge and can jam closeout. | FIXED. Charge to the instance's own termination time, capped at the OS backstop. C§8. |
| O-m3 | MINOR | 1.62 mislabelled as list; ledger range omitted retries. | FIXED. 1.62 labelled charged (list usage 1.611068); worst-case ledger 115.40 and hold-bound 118.34 shown. C§4, C§7. |
| O-m4 | MINOR | A speed-STOP retry on the same instance cannot succeed. | FIXED. Speed STOP returns to the owner; no automatic retry. STOP-6. |
| O-m5 | MINOR | Seeds burned before the full port proof is known. | FIXED. Lane U's queue now waits for G_PORT on the 722-item prefix (no scored fresh-world item before the port proof); sequential full-port-first offered as Option C. RUN-7, C§6, Q13. |
| O-m6 | MINOR | Text scan unsized; uploading the Codex tree unsafe. | FIXED. Frozen file list, per-file cap 5,000,000 bytes, streamed by the custodian on the laptop; never uploaded. SEED-10. |
| O-m7 | MINOR | Timestamp format width. | FIXED (same as I-m5). |
| O-m8 | MINOR | Worker silently skips files > 64 MiB; controller reads deliverable into RAM. | FIXED (not re-read by me; the fix is safe either way). Worker lists skipped files and fails; controller streams to disk; BT-A measures zipped size. RUN-12, D§15 item 16. |

## 3. Things I checked today that changed the design beyond the reviewers' fixes
- `sig["idle"]` and the continuity trigger are brain-state fields, so A7 can reuse the eye's own unchanged autonomic code (D§4.3). This removes the open "fairness branch".
- `merge_u1.py` writes its reading in text mode (line 528), so a laptop replay must be compared as canonical JSON, not raw bytes (GO-16).
- Lane U's queue is gated on the 722-item port proof, so no scored fresh-world item runs before the port is shown on all 7 arms (RUN-7). Cost: the gate delay, 277.5 s at the prior (about 0.016 USD).
- A7's volume is proposed at 1/4 (the one-way default), not the eye's learned volume, so A7 takes nothing from the eye (A7-6, Q7).
