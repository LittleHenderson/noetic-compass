# AWS job: the HSET-2 sealed build (`CLAUDE_BUILT_CLAUDE_CHECKED`, NOT LAUNCHED)

**What it is.** One CPU machine runs `../hset2/hset2_build.py` with the real salts. It builds the HSET-2 cells of
`../EVALUATION_DESIGN_v0_4.md` with Amendment A1, and prints everything section 7 lists before any model is read.
No model is loaded, trained or run.

**Who runs it.** The coordinator, only. The builder (Claude, temporary takeover while Codex is away) wrote it and did
not run it.

**Authority it relies on.** The owner's AWS order ("use aws as there is only 354 mb of 16 gbs locally"), the standing
run authorization (`docs/OWNER_RUN_AUTHORIZATION_20260922.md`), and design s9 step 3 ("An AWS CPU job, with a
throwaway-salt smoke stage first. Ceiling $1.00."). This file adds no new authority.

## Limits

| Limit | Value |
|---|---|
| Machine | ONE `c7i.2xlarge`: 8 vCPU, 16 GiB, CPU only, us-west-2, on-demand, $0.357/hour |
| Image | Canonical Ubuntu 24.04 (the SSM parameter in `launch.py`), Python 3.14 through `uv` |
| Disk | 20 GB gp3, deleted with the machine |
| In-machine timer | 90 minutes, then the operating system powers off at 93. The machine is destroyed on shutdown |
| Client deadline | 100 minutes after launch. `watch.py` terminates the machine and retries until AWS confirms it is gone |
| Pool timer | `hset2_build.POOL_TOTAL_SECONDS` = 3,600 s for all packet evaluation |
| Worst-case cost | (0.357 machine + 0.005 public address + 20 x 0.08 / 730 disk) = $0.36419 per hour; x 100/60 hours = **$0.6070** at the client deadline. Without the watcher, the power-off at 93 minutes bounds it at $0.5645 |
| Ceiling | **$1.00** (design s9). `launch.py` refuses to launch if the worst case is not below it |
| Expected run | about 15 to 20 minutes, about $0.09 to $0.12 (15/60 or 20/60 hours x $0.36419; estimate below) |
| Credentials on the machine | none. Presigned links only: one download (the bundle) and three uploads (progress, public results, sealed results) |
| Automatic retries | none. The launcher refuses to run twice (`launch_record.json`) |
| Left behind | nothing on AWS but the S3 objects under `helm-integration/hset2-build-<stamp>/` in the existing private bucket. No key pair, role, Elastic IP or snapshot |

**Runtime estimate.** Measured on the laptop, one process, throwaway salts (see `../hset2/BUILDER_REPORT_HSET2.md`):
a reach, parts or edge-account packet about 0.6 s; an analogy packet about 0.47 s; a correspondence packet about
0.1 s. The full build has about 5,300 to 5,540 packets (about 4,100 to 4,300 single-world, about 1,150 bank packets):
about 2,900 CPU-seconds, so about 6 to 8 minutes on 8 vCPU. Add setup (about 3 minutes), the stage-0 check, the
smoke run (about 3 minutes), the build's start-up (about 1 to 2 minutes) and the serial re-measurement of the trained
answer states (158 frozen-checker targets, about 1 to 2 minutes): about 15 to 20 minutes in all. The 90-minute timer
leaves more than 4 times that.

## What runs, in order

1. **Every bundled file** is checked against `anchors.json` (raw sha256), before anything runs.
2. **Stage-0 check.** `hset2_stage0_public.py --check` recomputes the committed public stage-0 files from the pinned
   fixture file. Any difference stops the job.
3. **Smoke.** `hset2_build.py --throwaway-seed tiny-9 --limit-foci 2`: the whole builder at tiny size with throwaway
   salts derived from a public string. No salt file is read. Its outputs are never uploaded.
4. **The build.** `hset2_build.py` with both real salts and `--expect-test5-shapes-digest`. Before building anything it
   refuses unless:
   - each salt's sha256 equals its committed pin (`hset2_build.HSET1A_SALT_SHA256`, `hset2_build.HSET2_SALT_SHA256`);
   - checker v2, slots v2 and the frozen checker report their accepted profile digests;
   - the larger-question route's source pins hold, and `evaluate_gates.py` has its pinned LF sha256 (A1 D4);
   - the rebuilt training bank equals the trained course's bank;
   - stage 0, recomputed, is byte-identical to the committed files (A1 D1);
   - TEST_NEW_5 reproduces HSET-1A's public `test_shapes_digest`, and no `PUBLIC_EXCLUDED` class is in it;
   - the trained course's analogy and correspondence answer states, re-measured with the frozen checker, equal the
     pinned record (`TRAINED_BANK_STATES`: 70 MATCH, 88 MAPPING).

## Before launch (the coordinator; each step is required, and the launcher refuses without it)

1. **A fresh review** of `hset2_build.py`, including the new packet code (design s9 step 1, s5.3).
2. **The HSET-2 salt.** Make 32 random bytes, written as 64 lowercase hex characters, in
   `D:/tksCAS-archive/hset2_sealed_20260924/salt.hex` (outside every repository). Commit its sha256 as
   `HSET2_SALT_SHA256` in `../hset2/hset2_build.py` and push, **before** the build (design s3 step 6, s9 step 2).
   If another folder date is used, change `ARCHIVE_HSET2` in `launch.py` in the same commit.
3. **The TEST_NEW_5 check.** Copy HSET-1A's public `test_shapes_digest` (from its build summary) into
   `EXPECTED_TEST5_SHAPES_DIGEST` in `launch.py`, and commit.
4. `python launch.py --dry-run` (uploads and launches nothing), then `python launch.py`, then `python watch.py`.

## Custody

- **The two salts** go up inside the bundle. The sealed results come back through their own link.
- **`watch.py`** writes the sealed tarball and its file only to a new run folder under
  `D:/tksCAS-archive/hset2_sealed_20260924/run_<stamp>/`. It never overwrites, never writes a file named `salt.hex`,
  and refuses a destination inside a git work tree.
- **Public results** (`results/`) hold TEST numbers only as totals and list digests. `HSET2_CELLS_PUBLIC.json` holds
  every DEV item; by the tiny runs' size per item it will be roughly 10 to 20 MB. Whether to commit it is the
  coordinator's call.
- **The honest limit.** The bundle (with both salts) and the sealed tarball stay in the private bucket. Anyone who can
  read that bucket, or the machine's startup script while its links are valid (4 hours), could rebuild TEST_NEW_5 and
  TEST_NEW_6. Codex can already read the archive disk. So the label `EVALUATION_NOT_INDEPENDENT_OF_THE_PROJECT` stays.
- Claude deletes no data. Removing the S3 objects is the owner's decision.

## Cleanup

- The machine destroys itself on shutdown; the disk goes with it.
- `watch.py` confirms the machine is gone and writes `watch_record.json` with the measured time and the cost bound.
- Nothing else is created.
