# HELM-Q1 Packet 2 return

Marker: HELM-Q1-P2-20260927-A. Author: Q1-Codex.
Actual session: 01a0e385-db6e-7a71-beca-f6ef3a6c5e04; worker /root; host MSI.
Workspace: C:/Users/wakil/HELM-Q1/q1-offline-20260927.
Canonical branch: codex/helm-q1-offline-20260927, Codex integration only.
Starting pin: 35236511b2f56bddcb50f06bfc74e3c7e6d2de24.
Implementation pin: 389229c8fd55fced3a302dce4ea0234f78ad379b.
The subsequent publication commit adds this return and hash metadata, with the
same launcher, tests, contracts and classical source bytes.

## Concrete implementation

coordination/codex/run_p2_checks.py now implements admission, source pinning,
existing-process-control verification, serial execution of the five real commands,
raw logs, structured receipts, timing, optional cgroup measurements, timeout/
descendant cleanup and partial-result handling. It has no SDK or provider call,
provisioning command, service start or control write. APPROVED_RUNNERS is empty.

It refuses without an independently enrolled custodian/grant and pre-existing
controls. Venue names, environment flags and caller JSON cannot grant admission.
The proposed envelope is one exclusive CPU, 512 MiB aggregate process-tree memory,
one serial packet, and at most 60 seconds including external termination grace.
Unsupported controls refuse; no host was modified to satisfy them.

Fifteen regression methods were added to tests/test_cli.py, including the actual
launcher CLI boundary, fake-controller runs, grant/identity/expiry forgery,
memory/CPU/whole-tree limits, stale source bytes, controller drift, partial logs,
timeouts, leftover descendants and refusal to overwrite an existing receipt.
These are authored tests, not executed outcomes. run_id/proposal_digest binding
and SearchBudgetExhausted source are unchanged from the starting commit.

Other changed files: README.md, SOURCE_INVENTORY.json, coordination/FILE_LEASES.md,
coordination/codex/HANDOFF.md, P2_ACK.json, P2_CHANNEL.md, P2_COMPILER_BOUNDARY.md,
P2_RUNNER_CONTRACT.md, P2_REQUEST.txt, evidence/TEST_STATUS.json,
evidence/P2_NOT_RUN.json and evidence/SOURCE_HASHES.json. The manager's existing
local CHECKPOINT_20260927_01.md edit remains untouched and unstaged.

## Actual outcomes

| Suite | Authored methods | Collected | Executed | Passed | Failed | Errors | Skipped | NOT_RUN |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Builder, including launcher | 58 | 0 | 0 | 0 | 0 | 0 | 0 | 58 |
| Supplied original helpers | 22 | 0 | 0 | 0 | 0 | 0 | 0 | 22 |

All five required commands are NOT_RUN:

```sh
python -m helm_quantum inventory --read-only
python -m helm_quantum baseline --mode disabled
python -m helm_quantum validate --fixture q1-mod4
python -m unittest discover -s input_package/original_package/tests -v
python -m unittest discover -s tests -p 'test_*.py' -v
```

Launcher command, also NOT_RUN: python coordination/codex/run_p2_checks.py.
Executed lightweight inspection: python coordination/codex/inspect_source.py
--output evidence/SOURCE_HASHES.json. It parsed 21 Python files and counted 58
builder methods without importing project code, collecting or executing tests.
JSON parsing and git diff --check succeeded. No behavioral pass is inferred.

evidence/P2_NOT_RUN.json is the actual author checkpoint, explicitly not an
execution receipt. evidence/SOURCE_HASHES.json contains static identities and
test method names. No test stdout/stderr, resource measurements or execution
receipt exists for P2. An admitted run would write receipt.json and five pairs of
stdout/stderr files to its custodian-provided output directory. Missing metrics,
ambiguous counts and incomplete runs are not converted into successful results.

## Authority and remaining defects

The permitted registry at D:/tksCAS-worktrees/codex-cas-closed-loop-1/.coordination/
helm_rnd_three_lead_v1/REGISTRY.json was read only; SHA256
29ddfca38b0ea12656ae9e92a0413b722deb74597909d50120ee89fe23b104dc.
It identifies historical incumbent jobs/record ownership and reports no active
instance. It contains no Q1 custodian, applicable Q1 grant, current free-capacity
or Q1 process-tree control evidence. Historical instances were not contacted,
borrowed, started or modified. Registry history is not live provider verification.

The launcher is unexecuted and needs independent review, including compatibility
with the actual installed kernel/systemd. No positive runner admission or
OS-enforcement experiment is established. Q0/profile, host interfaces, retained
reuse, compiler, simulator and hardware gates remain open. Quantum tasks, shots,
cloud allocation, new cloud jobs and cloud spend created by this packet are zero.
No cleanup was needed because no job was started. No children or paid wakeups ran.

The corrected reviewer count is 49 cases, 47 reported local passes, 2 NOT_RUN.
It remains REPORTED_NONADMITTED_EXECUTION against earlier source, not acceptance
of current fixes. Old raw reviewer receipts and authorship are preserved.
Actual separate P2 Claude/DeepSeek branches or export locations have not been
returned. P2_CHANNEL.md records this; no acknowledgment is fabricated.

Current usage-limit retrieval did not complete. Earlier account-wide usage is
historical and cannot measure this packet. Model monetary cost is unknown, not
zero. Source work was serial within the 30-minute packet ceiling.

## One next deliverable

An independently verified, source-bound admission artifact from the actual
custodian of an already-authorized AWS Q1 runner: actual instance and grant,
unused capacity, incumbent isolation and existing one-CPU/512-MiB/60-second
process-tree controls. Without that artifact, enrollment stays empty and all
80 authored test methods remain NOT_RUN. No new resource or spending is requested
or authorized by this return.
