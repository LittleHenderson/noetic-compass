# HELM-ANALOGY-REPAIR-1 acceptance item 1 on the T4: run log

Label: `CLAUDE_BUILT_CLAUDE_CHECKED` (temporary takeover, 2026-09-23).

## Attempt 1: INCOMPLETE (probe file missing from the bundle)

- **Machine.** `i-0b2a1761317398ba4`, g4dn.2xlarge, us-west-2. Launched 2026-09-23T23:35:08Z.
- **Source.** Original `20208c92`; repaired R = `ceab6c49f611303f39addfaa3553d81d6f902811`; Claude tools at
  `b5a4d525`. Bundle 2326 files, 29772718 bytes, sha256 `d3e92aad8f48f7242c935d9821a3d170cfe696c196f6c6a011a4574bfdd7cd51`.
- **Ended.** Watch ended 2026-09-24T00:18:51Z, 43.7 minutes after launch. Termination confirmed. No volume of this
  job remains.
- **Cost.** Upper bound $0.5596 against a $3.00 ceiling.
- **The program's verdict** (`read_results.py`): `item1_verdict: INCOMPLETE`.

What was measured (all 9 models: final, fresh and initial, seeds 20260917, 20260918, 20260919):

| Check | Result |
|---|---|
| stage 0: pytest | exit 0 (38 passed) |
| stage 0: frozen read-only check (A4.2) | exit 0 |
| control (frozen `20208c92`) digest equals the retained T4 reference | 9 of 9 |
| switch-OFF (R) digest equals control | 9 of 9 |
| switch-OFF parameter count | 174303 on all 9 |
| switch-OFF tensor names and shapes equal control | 9 of 9 |
| OFF probes (3) and fresh-ON probe (1) | **all 4 crashed** |

**Why the probes crashed.** Each probe finished its measurements, then hashed its preregistration file, which it
expects in its own folder:
`FileNotFoundError: ... /root/helm_t4/pkg/claude/PREREG_ANALOGY_WIRING_PROBE_v0_2.md`. The launcher had not put
that file in the bundle. No probe verdict exists, so the program cannot return `OFF_PRESERVED_ON_T4`.

**Fix (launch.py, same commit as this log):**
- the preregistration is bundled beside the probe;
- the launcher now refuses to build a bundle when a bundled tool reads a file beside itself (`HERE / "<name>"`)
  that is not bundled.

A search of the three bundled tools found no other file read from beside them.

**Files.** Everything from attempt 1 is in `attempt1/`: the launch record, watch log and record, results, and the
reading. A byte copy is at `D:/tksCAS-archive/analogy_repair_t4_attempt1_20260923/`, with 32 sha256 lines in
`D:/tksCAS-archive/analogy_repair_t4_attempt1_20260923.sha256`, checked after the copy.

## Attempt 2

Same R, same models, same limits ($3.00 ceiling). The only change is the bundle fix above.
- **Launched.** `i-030e5665bcad36f69`, g4dn.2xlarge, us-west-2a, bundle 2327 files, sha256 prefix `70360bc7e3f7ab0a`.
  It destroys itself within 153 minutes.
- **Money.** Attempt 1's upper bound ($0.5596) plus attempt 2's worst case ($2.05) is $2.61, inside the one $3.00
  ceiling for this job.
