# U1c — cost and sizing

Status: DESIGN ONLY. Every number below is either read from a named file or computed by a stated formula. No AWS call was made. Prices were not re-checked live; the launch preflight re-reads the AWS Pricing API. Actual billing stays PENDING, as for every job.

**In one line:** expected about 0.36 USD in total (range 0.27-0.57): build tests 0.06-0.13 plus the scored run 0.21-0.44; proposed caps 1.00 USD (build tests) and 4.00 USD (run).

---

## §1 What U1b actually used (laptop, 2026-10-15)

### §1.1 Whole run
| Item | Value | Source |
|---|---|---|
| Driver start / last part end | 2026-10-16T00:46:06.73Z / 03:16:10.70Z | `runs/DRIVER_LOG.txt` (reader brief) |
| Driver elapsed | 9,003.99 s, of which 4,680 s waiting for other laptop drivers | same |
| Supervisor wall, 21 parts | 4,245.3304 s (sum of `END.json` `elapsed_wall_seconds`) | reader brief; AWS brief |
| Worker wall | 4,228.659 s (sum of `SUMMARY.json`) | reader brief; spec §7.40 |
| Worker CPU | 4,001.015625 s (`END.json`) | AWS brief |
| Unit tests re-run in every part | 1,017.3 CPU-s = 25.4% of worker CPU | reader brief |
| Peak memory | 157,773,824 bytes = 150.46 MiB (part P04), a 200 ms poll | reader brief |
| Queue-part memory | mostly 112.4-115.4 MiB | reader brief |

### §1.2 Per part (read today from `SUMMARY.json`)
| Part | Units | Worker wall s | Tests CPU s |
|---|---|---|---|
| P01 | W01 | 69.991 | 38.266 |
| P02 | CAL | 62.913 | 41.0 |
| P18 | QUEUE | 222.218 | 29.844 |
| P21 | QUEUE | 105.314 | 28.625 |
`END.json` elapsed (reader brief): P01 70.6, P02 63.4, queue parts 220.7-225.0, P21 105.7.

### §1.3 The uncontended stretch (my read today of `runs/U1B_MSI_P14..P21/RESULTS_U1.json` and `SUMMARY.json`)
The laptop was shared and contended early in U1b's run (draws 100-106 took 4.672-5.474 s per item against 2.059-2.935 for draws 107-119; P03's test CPU was 79.4 s against 28.625 s in P21). So I measured the later parts:

| Part | Items | Item wall sum s | Worker wall s | Non-item s | Tests CPU s |
|---|---|---|---|---|---|
| P14 | 68 | 178.787 | 220.082 | 41.295 | 39.0 |
| P15 | 66 | 183.332 | 220.841 | 37.509 | 35.812 |
| P16 | 66 | 183.989 | 222.175 | 38.186 | 37.188 |
| P17 | 72 | 181.019 | 223.167 | 42.148 | 40.328 |
| P18 | 91 | 191.74 | 222.218 | 30.478 | 29.844 |
| P19 | 90 | 189.605 | 220.607 | 31.002 | 30.031 |
| P20 | 89 | 190.644 | 221.093 | 30.449 | 29.516 |
| P21 | 40 | 76.103 | 105.314 | 29.211 | 28.625 |

Task B item wall means over P14-P21 (seconds per item): A0 1.8844 (78 items), A1 2.7335 (78), A2 2.7742 (78), A3 2.7708 (78), A4 2.6782 (78), A5 1.8724 (84), A6 2.0197 (84); **all scored Task B items 2.3809 (558)**. Replay items (in P21): A0 1.5369 (12), A4 2.3527 (12).

Note for the record: an earlier draft said the replay items on draws 100-101 "ran in U1b's contended stretch". They ran in P21, the last and uncontended part. That reason for dropping Design 3's speed check was wrong; the speed check is now host-only anyway (§3.4).

### §1.4 Calibration worlds (read today from `runs/U1B_MSI_P02/CALIBRATION.json`)
Task B (A4): 3.159, 2.949, 3.017, 3.582, 3.262, 3.084 s (mean 3.1755). Dialogue (A4): 0.239, 0.252, 0.215, 0.19, 0.212, 0.206, 0.199, 0.207 s (mean 0.215). P02's test CPU (41.0 s) suggests these ran somewhat contended, so they err on the slow side.

### §1.5 Host speed
- `k` = how many times slower the host is than the laptop. Never measured for this code (spec line 1429 on the thread-head copy: "the host-to-laptop speed ratio was never measured").
- The only recorded ratio for this code family is RB-I1c c36: "speed ratio r 1.2427", host `i-095837cafccfe06f6`, m6i.8xlarge, 16 pinned workers (spec §7.65, line 2234 of the thread-head copy). Its direction and whether it carries to one m6i.xlarge core are not stated there. I use it only as a prior.

---

## §2 The AWS plan (Option A, proposed)

- **Instance:** one m6i.xlarge (4 vCPU = 2 physical cores x 2 threads, 16 GiB), us-west-2, on demand, AMI `ami-0dddfa1ffa6b87af7` (Ubuntu 24.04.5, Python 3.12.3; c56 `host_info.txt`), 40 GiB gp3 root deleted on terminate, IMDSv2, no inbound rules, data only through presigned URLs. Run-proven with the current kit on c48-c56; 63 recorded preflights. Controller price bound 0.20; shape check 4 vCPU / 16,384 MiB.
- **CPU only.** The code is pure standard-library Python and `rb.no_torch` blocks torch and numpy. There is no neural work, so the GPU-first rule does not apply, and the owner's 2026-10-18 "no more GPU for now" is respected.
- **Kit:** copy c56's run-proven scripts by find-and-replace (the `make_c56_kit.py` pattern), with the timer chain of PREREG TIME-1..TIME-9, `systemd-run` scope `AllowedCPUs=0-3`, `MemoryMax=14G`, one extra presigned PUT URL for lane A's archive, and the regenerated `job_supervisor.py` (`LAUNCH_WINDOW_SECONDS` 14,400; the run-proven copy `3b2337ca…` hard-codes 6,660 at line 31).
- **Lanes:** lane U on one physical core; lane P (PREFIX-722) then lane A (A7) on the other. Lane U's queue waits until G_PORT has passed on lane P's 722 items.
- **Memory:** at most 3 workers at a time, each about 151 MiB at U1b's peak; far under 14 GiB.
- **Deliverable:** lane U runs folder about 24 MB uncompressed (U1b's was 24,186,272 bytes) plus lane P's prefix and lane A; zipped size to be measured in BT-A. Limits: 64 MiB per file, 256 MiB per deliverable; the worker fails rather than skip a file.
- **Laptop:** controller and watchdog only (up to the 240-minute window, expected about 75 minutes), the outer reader, and the `merge_u1.py` replay (done on this laptop on 2026-10-21 over the same data size in 0.654 s). No brain code runs on the laptop. Free memory when I checked today: 1,262,984 KB (the owner's 2026-09-23 snapshot was 354 MB of 16 GB).

---

## §3 The arithmetic

### §3.1 Constants (sources in §1)
- Task B item: 2.3809 s at k = 1 (P14-P21 mean). Dialogue item: 0.215 s (CAL dialogue mean). A7 Task B item: 2.7708 s (A3's mean; A7 runs A3's autonomic tier).
- Non-item time per queue part: 30.3 s (mean of P18-P21: 30.478, 31.002, 30.449, 29.211). A7 parts: 35 s (my estimate: 18 tests plus A7's own tests).
- Queue part wall: 222 s (U1b's queue parts ran 220.7-225.0 s: the 220 s no-new-world mark plus the last item).
- W01 + CAL: 134 s at k = 1 (U1b P01 70.6 + P02 63.4, measured contended, so cautious).
- Fixed host overhead: 310 s = boot 105 (c56: launched 18:35:50Z, BOOT 18:37:35Z) + unpack 5 + setup checks 40 (my estimate) + close stage 120 (my estimate) + upload and cleanup 40. P00 plumbing part: 70 s x k.
- Rate: m6i.xlarge all-in 0.2013835616438356 USD/h = 0.0000559398782344 USD/s (0.192 list from `aws-c56-a1-preflight.json` + 40 GB gp3 + public IPv4; `CLEANUP_PROOF_R1W7V9_C56.json`). Cautious rate 0.46 USD/h (`RUN_LIMITS_R1W7.json`; `CONSERVATIVE_USD_PER_HOUR` in `aws_control_c56.py`), shown, not charged.

### §3.2 Model U (measured uncontended rates; my central model)
- Lane U item work: `I_U = 864 x 2.3809 + 680 x 0.215 = 2,203.2976 s` at k = 1 (864 = 840 + 24 replay Task B; 680 = 672 + 8 replay dialogue).
- Lane P prefix item work: `I_P = 42 x 2.3809 + 680 x 0.215 = 246.1978 s`.
- A7 item work: `I_A = 132 x 2.7708 + 100 x 0.215 = 387.2456 s` (232 items).
- Usable item time per part: `u = 220 - 30.3·k`. Queue parts `n = ceil(I·k / u)`.
- Lane U wall `= 134·k + n_U x 222`. Gate delay `= max(0, n_P x 222 - 134·k)` (lane U waits for lane P's prefix).
- Lane U end from T0 `= 5 + 204·k + laneU + delay` (204·k = P00 70·k + PORT-EARLY 134·k).
- Host seconds `= 310 + 204·k + laneU + delay`. In the default plan A7 runs on lane P's core during lane U's queue and adds no host time.

**Worked example, k = 1:** `n_U = ceil(2,203.2976 / 189.7) = 12`; lane U = 134 + 12 x 222 = 2,798 s; `n_P = ceil(246.1978 / 189.7) = 2`, delay = 444 - 134 = 310 s; end from T0 = 5 + 204 + 2,798 + 310 = 3,317 s; host = 310 + 204 + 2,798 + 310 = 3,622 s; list = 3,622 x 0.2013835616438356 / 3600 = 0.202614 USD, charged 0.21; cautious 3,622 x 0.46 / 3600 = 0.462811, i.e. 0.47.

### §3.3 Model C (the first draft's contended model, kept as a slow bracket)
Lane U `= 134·k + 222 x 2,932·k / (220 - 51.4·k)` (2,932 s = U1b's non-test item CPU; 51.4 s = contended per-part overhead).

### §3.4 The speed check (host only; PREREG RUN-9)
The run uses none of the laptop numbers above to decide. At the end of PORT-EARLY it projects lane U's end from the host's own CAL item walls and test times, and stops before any fresh world if the projection is later than T0 + 12,000 s. The tables below only size the window and the cap.

### §3.5 Option A results (default: PREFIX-722, A7 in parallel)
| Case | n_U | Lane U wall s | Gate delay s | Lane U end from T0 s | Host s | List USD | Charged | Cautious |
|---|---|---|---|---|---|---|---|---|
| Model U, k = 1 | 12 | 2,798 | 310 | 3,317 | 3,622 | 0.202614 | 0.21 | 0.47 |
| Model U, k = 1.2427 (prior) | 16 | 3,718.5 | 277.5 | 4,254.5 | 4,559.5 | 0.255058 | 0.26 | 0.59 |
| Model U, k = 1.5 | 19 | 4,419 | 465 | 5,195 | 5,500 | 0.307669 | 0.31 | 0.71 |
| Model U, k = 2 | 28 | 6,484 | 620 | 7,517 | 7,822 | 0.437562 | 0.44 | 1.00 |
| Model U, k = 2.5 | 39 | 8,993 | 775 | 10,283 | 10,588 | 0.592291 | 0.60 | 1.36 |
| Model U, k = 2.75 (edge) | 45 | 10,358.5 | 741.5 | 11,666 | 11,971 | 0.669656 | 0.67 | 1.53 |
| Model U, k = 2.8 | 46 | — | — | 12,120 > 12,000: speed STOP | 761 | 0.042581 | 0.05 | 0.10 |
| Model C, k = 1 | — | 3,994.6 | 310 | 4,513.6 | 4,818.6 | 0.269554 | 0.27 | 0.62 |
| Model C, k = 1.5 | — | 7,033.4 | 465 | 7,809.4 | 8,114.4 | 0.453921 | 0.46 | 1.04 |
| Model C, k = 1.9 | — | 10,363.5 | 411.4 | 11,167.5 | 11,472.5 | 0.641768 | 0.65 | 1.47 |
| Model C, k = 2 | — | 11,375.6 | 620 | 12,408.6 > 12,000: speed STOP | — | — | — | — |
| G_PORT_EARLY fails, k = 1 | — | — | — | — | 394 | 0.022040 | 0.03 | 0.06 |
| Full 240-minute window | — | — | — | — | 14,400 | 0.805534 | 0.81 | 1.84 |

**Owner option FULL lane P (all 1,544 of U1b's items), A7 after lane P:** k = 1: 4,288 s, list 0.239870, charged 0.24 (cautious 0.55); k = 1.2427: 5,225.5 s, 0.292314, 0.30 (0.67); k = 2: 9,154 s, 0.512074, 0.52 (1.17).

**180-minute window variant:** force 180 min, backstop T0 + 176 min, stage deadline T0 + 10,200 s, work cutoff T0 + 9,300 s, speed STOP above T0 + 8,400 s. Model U then fits up to about k = 2.15; Model C up to about k = 1.6. Cap 3.00 (2 x 0.46 x 3 = 2.76).

---

## §4 Cautious upper bound and the proposed cap
- One attempt at the full 240-minute window: list 0.805534 (charged 0.81); at the cautious rate 0.46 x 4 = 1.84.
- One scored attempt plus one plumbing retry (the house rule): list usage 1.611068, charged 1.62; cautious 3.68.
- **Proposed run cap: 4.00 USD** (3.68 rounded up). The kit's preflight check `2 x conservative <= cap` passes.
- **Proposed build-test cap: 1.00 USD** (§5).
- Both are proposed, not approved. They are holds; each is released at closeout and replaced by the list charge.

---

## §5 Build-test jobs (before the seal; PREREG ATT-6)
| Job | Purpose | Force window | Hold (2 x 0.46 x window) | Expected host s (my estimate) | Expected charged |
|---|---|---|---|---|---|
| BT-A | interpreter identity, 18 tests, P00 through the new supervisor, layout, blocker, open-audit allow-list, memory-kill and G_MEM_EQUIV trip test, instance-id permit, timestamp format, regenerated `job_supervisor.py` and timer chain, two-process determinism on fixture worlds, U1b reference item table (from a read-only copy of U1b's `runs/`, never parsed on the laptop), zipped deliverable size | 30 min | 0.46 | about 900 | 0.06 (list 0.050346) |
| BT-B | A7 tests, A7 behaviour test, A7 metric equivalence on fixture items | 20 min | 0.31 (0.306667) | about 600 | 0.04 (list 0.033564) |
| BT-C | one re-test after a fix (only if needed) | 10 min | 0.16 (0.153333) | about 400 | 0.03 (list 0.022376) |
Sum of `2 x 0.46 x window` = 0.92 <= 1.00. Expected 0.06 (BT-A only) to 0.13 (all three). Any further job needs a new owner line. Build tests never build a scored U1c world.

---

## §6 Sizing options compared (all at the prior k = 1.2427, Model U)
| Option | Layout | Host s | List USD | Charged | Cautious | Lane U fits up to | Window / cap | Notes |
|---|---|---|---|---|---|---|---|---|
| **A (proposed)** | m6i.xlarge; lane U on one core; lane P prefix then A7 on the other; lane U queue gated on the prefix | 4,559.5 | 0.255058 | 0.26 | 0.59 | k about 2.75 (Model U), 1.9 (Model C) | 240 min / 4.00 | current run-proven kit; shortest laptop exposure |
| B | m6i.large (2 vCPU = 1 core); prefix, then lane U, then A7, in sequence | 5,392 | 0.157842 (all-in 0.1053835616438356/h) | 0.16 | 0.69 | k about 2.7; A7 dropped above about k 2.3 | 240 min / 4.00 | cheapest; c46/c47 controller config; laptop up about 14 min longer |
| C | m6i.xlarge; full lane P (1,544) first, then lane U, then A7 | 8,500 | 0.475491 | 0.48 | 1.09 | k about 1.85 | 240 min / 4.00 | port fully proven before any fresh world; needs Q4 = FULL |
Not used: m6i.8xlarge sharding (changes U1b's run plan; roughly doubles cost); t3.medium (burstable credits distort the time guards).

---

## §7 Ledger state and the effect of holds
- **Now** (`C:\Users\wakil\Documents\Codex\AWS_COMBINED_ALLOCATION_CURRENT.json`, sha256 `81f0b6f61715249a4f175f9aa2d66b31a61bf29fecce44582c75fa96197390dd`, re-hashed today; unchanged since c56 closeout; utc `2026-10-21T18:41:27.829920+00:00`): combined 113.34, unreserved 86.66, ceiling 200.00.
- **During a build test:** one hold at a time; largest is BT-A 0.46, so combined at most 113.80 + earlier build charges.
- **During the scored run:** hold 4.00. Combined about 117.40-117.47 (113.34 + expected build charges 0.06-0.13 + 4.00); unreserved about 82.53-82.60.
- **After closeout, expected:** 113.34 + 0.27..0.57 = about 113.61..113.91.
- **Worst case at list charging** (every job and attempt uses its whole window): build tests 2 x 0.11 + 2 x 0.07 + 2 x 0.04 = 0.44 (BT-A 1,800 s = 0.100692; BT-B 1,200 s = 0.067128; BT-C 600 s = 0.033564) + run 1.62 = 2.06, so 115.40.
- **Hold-bound ceiling** (if every cap were fully used): 113.34 + 1.00 + 4.00 = 118.34; unreserved 81.66.
- **What a hold does:** it lowers "unreserved" by the hold amount while held, so other jobs cannot spend that money. At closeout the hold is released and the list charge is added: `after = before - hold + charge`.
- The ledger is shared with other operators. Every hold re-reads the pointer and matches its sha256 immediately before writing.

---

## §8 Charge rules
- House basis (`closeout_c56.py`): all-in rate x host seconds from the launch intent to the cleanup receipt, rounded up to the cent per attempt. The cautious figure is shown, not charged.
- **New closeout rule for a dead laptop:** if the controller dies and cleanup runs late, the charge runs to the instance's own termination time read from `describe_instances`, capped at the OS backstop (T0 + 14,160 s), not to the late cleanup receipt. Without this rule a 10-hour-late cleanup would record 2.01 list, and `assert charge <= HOLD` could block closeout with the 4.00 hold stuck in the shared ledger.
- S3 requests and transfer are not priced separately (the preflight adds 0.005).
