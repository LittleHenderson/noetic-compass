# AWS job: HSET-1A Stage 1 cells, plus the D-1 acceptance tests of checker version 2

**Authority.**
- The owner said in chat on 2026-09-23: "build the Stage 1 cells on aws".
- Earlier the same day: "use aws", and "use aws as there is only 354 mb of 16 gbs locally".
- The D-1 acceptance is Claude's assigned checker role (`_handoffs/HELM_NEXT_PHASE_20260923/COORDINATION_CLAUDE.md`).
- This is standing run authorization under `docs/OWNER_RUN_AUTHORIZATION_20260922.md`.

**Runner:** Claude (evaluation designer, sealed-test custodian and independent checker). Codex does not run this job.

| Limit | Value |
|---|---|
| Machine | ONE `c7i.2xlarge`: 8 vCPU, 16 GiB, CPU only, us-west-2, on-demand |
| Price | $0.357/hour |
| Image | Canonical Ubuntu 24.04 (the SSM parameter in `launch.py`) |
| Disk | 20 GB gp3, deleted with the machine |
| In-machine timer | 120 minutes, then the operating system powers off at 123. The machine is destroyed on shutdown |
| Client deadline | 130 minutes after launch. `watch.py` terminates the machine and retries until AWS confirms it is gone |
| Worst-case cost | 130/60 x (0.357 + 0.005 public address + 0.0022 disk) = **$0.79**, if `watch.py` is running. Without the watcher, the in-machine timers bound it at 123 minutes. **Ceiling $1.50** |
| Credentials on the machine | **none**. Presigned links only: one download (the bundle) and three uploads (progress, public results, sealed results) |
| Left behind | nothing: no key pair, role, Elastic IP or snapshot. The S3 objects sit in the existing bucket under `helm-integration/hset1a-build-*` |
| Work | non-neural only. No model, no GPU, no training. Nothing is written back to any repository |
| Automatic retries | none. The launcher refuses to run twice (`launch_record.json`) |

**What runs, in order.**
1. **`frozen_profiles.py`** on the original tree (Helm 2.0 source `20208c92`). It records the frozen checker's and
   slot compiler's profile digests.
2. **`hset1a_build.py`** on the original tree. It builds the Stage 1 cells to `BUILD_SPEC_v0_1.md`, scores every
   comparator with the frozen checker, and prints each cell's bar, effective n and power.
3. **`d1_acceptance_run.py`** on Codex's checker-v2 tree (`7f85af1e`). It runs tests A1 to A6, plus an extra
   cross-check: v2 on every Stage 1 packet.

**Custody limits, stated plainly (review 2026-09-23, finding 4).**
- The bundle, which holds the salt, and the sealed tarball stay in the private bucket
  `cas-harness-runpod-92754088`, under `helm-integration/hset1a-build-<stamp>/`.
- For 4 hours the bundle's download link also sits in the machine's startup script.
- So anyone who can read that bucket, or the instance's startup script in that window, could rebuild TEST_NEW_5.
  That is the owner's account, which Codex can also use.
- This adds no new kind of reader. Codex can already read `D:/tksCAS-archive`. It is why the design keeps the label
  `EVALUATION_NOT_INDEPENDENT_OF_THE_PROJECT`.
- Claude does not delete the S3 objects: no permanent deletion. Removing them is the owner's decision.

**Custody of the secret test.**
- The salt goes up inside the bundle, and the sealed results come back through their own link.
- `watch.py` writes the sealed tarball and its file **only** to a new run folder under
  `D:/tksCAS-archive/hset1a_sealed_20260923/run_<stamp>/`. It never overwrites, and it never writes a file
  named `salt.hex`.
- The public results (`results/`) hold TEST numbers only as totals and digests.

**What the bundle holds.** It is built from git objects, not working files. See the `launch.py` docstring.
