# One prospective AWS CPU validation

This lane validates the public engineering loop at source
`318b22ad01304f80ed0f539420792cc951fe297a`. It does not change CAS semantics,
Helm, historical receipts, protected tests or the historical ledger.
Codex is the runner. Root is the sole AWS operator.

The package contains the committed public lane, all 108 exact runtime rows,
the worker, and pinned Linux CPython 3.12 wheels. The worker installs offline,
checks source and artifact bytes, runs 47 tests, replays the retained witness,
runs a new witness, and replays that witness in a fresh process.

From this directory, local preparation only:

```powershell
C:/Python314/python.exe -B package.py --download-wheels --wheelhouse wheelhouse
C:/Python314/python.exe -B package.py --freeze --wheelhouse wheelhouse
```

Review the generated freeze and its SHA256, package manifest and exact commands
in worker.py. The root operator alone may then execute this one-shot command:

```powershell
C:/Python314/python.exe -B launch.py --execute --job-directory jobs/EXACT_JOB --freeze-sha256 EXACT_FROZEN_SHA256
```

One t3.small, standard CPU credits, encrypted 8 GiB gp3 root, Ubuntu 24.04,
us-west-2a, zero retries, $1 all-services maximum within the $5 engineering
pool. Price/readiness evidence is bound from
`D:/tksCAS-worktrees/codex-cas-closed-loop-1/.coordination/AWS_READINESS_20260925.json`.
The $0.10 forecast includes ample allowance beyond the observed $0.0208/hour
compute rate; it is not a provider billing receipt. Timers bound resources,
not AWS's dollar billing system. Cleanup failures require operator attention.

The first user-data command schedules OS shutdown at 18 minutes; shutdown
behavior is terminate. Worker work is bounded to 15 minutes. The operator
stops by 17 minutes. EventBridge Scheduler independently terminates the exact
tagged instance at 18 minutes (AWS delivery granularity can add up to a minute).
The outer maximum is 20 minutes. Source install/test failure is retained, never
retried. Failed creation is not silently converted to a launch retry.

The fresh private bucket supplies a 25-minute presigned payload GET and narrowly
scoped bootstrap-failure/evidence PUTs. These URLs exist only in the launch user-data
argument; they are never printed or persisted in local execution records.
Worker uploads use the normal SDK and its scoped instance role, with credentials
kept by the SDK in memory. No inbound network access; egress HTTPS only.

The finally path terminates and verifies termination, downloads output bytes
and console evidence, then deletes only resources created for this unique job.
If output collection or termination cannot be verified, dependent cleanup is
held and the exact failure remains in execution.json. No broad deletion,
unrelated process termination or infrastructure reuse occurs.

No cloud execution is performed by package.py or by importing these modules.
The launcher first requires one exact-request EC2 DryRunOperation response.
This permission check is distinct from the single paid launch attempt. It also
posts START/PROGRESS/END to the existing Codex coordination heartbeat, with
active progress at most 90 seconds apart between bounded provider calls.
The launch attempt marker makes the job directory single-use. A different
attempt requires a newly frozen prospective job and authorization; this code
does not grant it.
