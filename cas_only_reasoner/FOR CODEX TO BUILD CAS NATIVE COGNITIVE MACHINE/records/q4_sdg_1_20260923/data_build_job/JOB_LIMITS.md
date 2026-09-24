# Q4-SDG-1 B-package data build: job limits (written before launch)

Label: `CLAUDE_BUILT_CLAUDE_CHECKED` (temporary takeover). Runner: the Claude coordinator. Not launched.

## What it does

- **Purpose.** Review item A1. Build the B lesson package ONCE with the engine written down, prove it can be rebuilt
  byte for byte, and bring back its digests so the coordinator can pin it before any training.
- **Program.** `research/helm_cas_expression_lab/q4_sdg_curriculum.py` (unchanged) and `q4_ab_prep.py package-digests`,
  at the reviewed source commit given to `launch.py --source-commit`.
- **Stages on the machine (no GPU, no torch, no model):**
  - refuse if the optional Rust engine is importable (the pin must say `python`);
  - build 1: `--build --size 4096 --expect-engine python`, `PYTHONHASHSEED=1`;
  - build 2: the same, `PYTHONHASHSEED=4242`, into another folder;
  - verify build 1: `--verify --unpinned --recompile` (every row recompiled with the pinned compiler);
  - `package-digests`: every file of the two builds compared byte for byte; the proposed pin entry.
- **What comes back to the laptop** (`results/`): `build_digests.json`, `manifest.json` (counts, hashes and statistics;
  no row, no target), the logs, `package_tar_sha256.txt`. No row file comes back.
- **What stays in S3:** `package.tar.gz` (the whole package, row files included), as an archive. The watcher never
  downloads it.

## Then, on the laptop (coordinator)

1. `python watch.py` until it exits (0 = done).
2. `python pin_package.py --check`, then `python pin_package.py --write`. It refuses unless both builds were
   byte-identical, the verify passed, the manifest hashes to the reported digest, and seeds, size and engine equal the
   frozen package in `q4_ab_rules.py`. It writes one entry into `research/helm_cas_expression_lab/Q4_SDG_DATA_PINS.json`.
3. Commit the pin file and this folder's records, by explicit path.

**Known side effect of pinning (open question for Codex/owner).** `test_q4_sdg_curriculum.py::test_pinning_is_required_and_create_only`
expects `NO_PIN_FOR_THIS_DATA_VERSION` from the REAL pin file for its tiny package. Once the real package is pinned,
the same call raises `MANIFEST_NOT_THE_PINNED_ONE` instead, so that existing test fails. The one-line fix (point
`sdg.PINS` at a temporary copy of an empty pin file before the first assertion) is outside this builder's new-files-only
scope. The A-versus-B job itself never runs that test.

## Machine, time and money

| Item | Value |
|---|---|
| Machine | one `c7i.large` (2 vCPU, 4 GiB, no GPU), us-west-2, $0.0893 per hour; 30 GB gp3 disk, deleted on termination |
| Image | Ubuntu 24.04 from the public SSM parameter (recorded in the launch record) |
| Python | 3.14.7 through `uv` (the same interpreter as the T4 jobs), no torch |
| Timers | machine: shutdown at 43 minutes plus an in-machine timer at 40 minutes; the watcher terminates it at 50 minutes |
| Expected | about 10 minutes (two builds, one verify); build time at size 4096 is not measured yet: this job measures it |
| **Worst case** | (0.0893 + 0.005 public address + 30 x 0.08 / 730 disk) x 50 / 60 = **$0.0813** |
| **Ceiling** | **$5.00 for the whole A-versus-B job**, this build included (OWNER_AUTHORITY_AND_DECISIONS_20260924.md) |
| Ceiling arithmetic | $0.0813 (this job, worst case) + $2.1678 (training job, worst case) = **$2.2491 <= $5.00**. `launch.py` refuses otherwise |
| Concurrency | refuses while another data-build machine is running; it is not a GPU machine |
| Retries | none. A second launch is refused while `launch_record.json` exists |

## Custody

- The bundle is built from git objects: the lab's top-level `.py` and `.json`, the pinned compiler, and the public
  Q3 v0.7 data (manifest, baselines, `visible_*.jsonl`).
- Never bundled: any `*_eval.jsonl`, any name containing `sealed`, `hset1a` or `hset1b`. Checked twice in the
  launcher, again on the machine, and again on the way out (the result archive is scrubbed of such names).
- The B package's own `sealed_*` sidecars are written by the build on the machine. `--verify` and `package-digests`
  read them there. They never reach the laptop.

## Cleanup

- The machine terminates itself on shutdown. The watcher confirms `terminated` and checks that no volume tagged with
  the job's name remains.
- S3: bundle, results, progress and package objects stay under `q4-sdg-1/data-build-<stamp>/` in
  `cas-harness-runpod-92754088`. Deleting them is the owner's call.
