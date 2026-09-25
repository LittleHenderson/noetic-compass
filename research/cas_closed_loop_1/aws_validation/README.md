# Lane A v2: AWS CPU validation with instance Git preflight

This is a new Codex-owned validation after the owner superseded the earlier
Lane A acceptance. Existing jobs, packages and historical evidence stay intact.
An earlier job cannot satisfy this protocol even if its tests passed.

Root first commits the CAS correctness changes and this operational code.
The builder requires an explicit source SHA equal to new committed HEAD, a
predeclared test count, and the exact current authorization file and SHA256.
Historical runtime remains 8182ad52b4468f18f140837dffee0e7debcfe786.
The declared count must include all current regression cases and is verified
against the final commit. There is no default count. Those cases have not yet
run under this AWS protocol.

## Actual instance preflight

Before acceptance, record each command, stdout, stderr and exit code:

```text
git config core.longpaths true
git cat-file -e 8182ad52b4468f18f140837dffee0e7debcfe786
python3 research/cas_closed_loop_1/check_artifacts.py --git-ref NEW_EXACT_SOURCE
python3 research/cas_closed_loop_1/bootstrap_runtime.py
```

Bootstrap materializes all 108 runtime files from real Git objects on the
instance. Prepopulated runtime files cannot substitute for this step. Source
admission, artifact checks, all declared tests, retained replay, a new witness
and fresh-process replay then run. Any mismatch stops and retains evidence.

A changed adapter is not the producer of the retained historical evidence.
HISTORICAL_PRODUCER.json binds four exact original producer snapshots, which
the unchanged historical RUN_MANIFEST verifies. The fresh source and package
separately bind the amended implementation. No historical receipt is rewritten.
The prospective focused suite now contains 57 cases; AWS execution is pending.

## Explicitly partial public Git objects

A normal connected Git bundle could include protected or unrelated history;
it is not created. The package contains original exact commit objects, only
ancestor trees needed for allowlisted paths, selected public source blobs and
the 108 manifest-authorized runtime blobs. Every object is checked against its
original Git ID, including its type/size header. Loose compression is merely a
storage encoding; commits, trees and blobs are never synthesized or altered.

Ancestor tree metadata includes sibling names. Unrelated descendant objects
and protected blobs are absent. Missing parent history is explicitly shallow.
This is a real partial Git object store, not fake Git, and does not claim a
complete clone, connected history or a full-fsck result. It has no remotes,
alternates, replacements or grafts. Instance lazy fetch and prompts are disabled.
public_git_objects.json inventories all included objects. Required real Git
cat-file/show/check/bootstrap paths resolve or fail closed.

## Git and Python dependencies

Python 3.12 wheels are pinned and installed offline. Exact official Ubuntu git
and git-man packages 1:2.43.0-1ubuntu7.3 are bundled with SHA256/size checks.
Observed public index:
https://archive.ubuntu.com/ubuntu/dists/noble-updates/main/binary-amd64/Packages.xz

If Git is missing or its package version differs, one bounded bootstrap uses
signed official Noble HTTPS repositories for missing OS libraries and installs
the bundled Git packages. Index refresh and install each have a 120-second
limit, APT retries are zero, and installed versions are retained. This does not
assume the AMI already has Git. All setup time stays inside the CPU wall limit.

## Commands

From this directory, only if the exact wheelhouse does not already exist:

```powershell
C:/Python314/python.exe -B package.py --download-wheels --wheelhouse wheelhouse
```

After committing the new source:

```powershell
C:/Python314/python.exe -B package.py --freeze --wheelhouse wheelhouse --source NEW_COMMITTED_SHA --expected-tests FROZEN_CASE_COUNT --authorization-file CURRENT_OWNER_RECORD --authorization-sha256 EXACT_OWNER_RECORD_SHA256
```

Root reviews the new freeze and alone executes:

```powershell
C:/Python314/python.exe -B launch.py --execute --job-directory jobs/NEW_V2_JOB --freeze-sha256 EXACT_NEW_FREEZE_SHA256
```

Only v2 freezes are accepted. One exact-request EC2 DryRunOperation precedes
one paid launch attempt. No launch retry, old marker reuse or automatic restart.
Importing these modules or freezing a package performs no AWS operations.

## Limits, evidence and cleanup

One t3.small, standard credits, encrypted 8 GiB gp3 root, Ubuntu 24.04,
us-west-2a. The all-services maximum is $1 within the $5 engineering pool;
the $0.10 forecast is not a billing receipt. Readiness/pricing reference:
D:/tksCAS-worktrees/codex-cas-closed-loop-1/.coordination/AWS_READINESS_20260925.json

The owner permits this CPU job alongside the explicitly frozen HELM instance
i-0adf52b7fa801e08b, g7.2xlarge, us-west-2, job
cas-meta2-tpntr-20260925151836-b981625f-m-20260918. The global active-instance
check allows only that exact ID, type and region; every other active instance
blocks. Root alone controls the HELM GPU. This CPU launcher never preempts or
modifies it.

The first user-data command schedules termination through OS shutdown at 18
minutes. Worker setup and work have 15 minutes, operator stops by 17 minutes,
and EventBridge independently terminates the tagged VM at 18 minutes subject
to AWS delivery granularity. Outer ceiling: 20 minutes. AWS does not enforce
the dollar envelope automatically; failed cleanup needs operator attention.

Private payload GET and emergency evidence PUT URLs last 25 minutes and are
not printed or persisted in local records. Normal uploads use the standard
SDK and a job-scoped instance role, with no credential files. No inbound
network access; HTTPS egress only. Console evidence redacts bootstrap tokens.

Finally terminate/confirm, collect output and failure evidence, then remove
only this job's resources. Uncertain launches, unverified termination or failed
collection retain dependencies and report the exact blocker. START, PROGRESS
and END use the existing Codex coordination heartbeat. Historical jobs and
receipts remain unchanged.
