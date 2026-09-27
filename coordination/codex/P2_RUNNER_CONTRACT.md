# Existing-runner boundary

run_p2_checks.py is executable source; its tests are NOT_RUN. APPROVED_RUNNERS is
empty because no Q1 custodian, grant or existing runner was identified. The entry
point is python coordination/codex/run_p2_checks.py, only on an admitted AWS runner.
No venue/grant/source override flags are accepted. Do not execute it on MSI as a
test, install dependencies, provision/start a service or edit protected controls.

Enrollment requires independently verified custodian/grant evidence and a
reviewed source change. A caller's JSON, environment or matching hashes cannot
populate the registry. The enrolled custodian must already provide a dedicated
unprivileged EC2 systemd service, a root-controlled /run/helm-q1/p2/grant.json,
root-owned immutable source and a separate result directory. Root control and
enrollment are separate requirements: JSON alone never grants admission. The
grant binds boot, service invocation, source, expiry, finite limits and actual
capacity/isolation records. A compromised root operator or arbitrary malicious
Python executing in-process is outside this payload boundary.

The launcher reads actual DMI instance identity, UID, MainPID/invocation, cgroup
membership and existing controls. It requires one exclusive CPU, exactly 512 MiB
aggregate memory, no swap/HugeTLB allocation, whole-group OOM behavior, at most
32 processes and no delegated child groups. Service runtime plus kill grace must
fit within 60 seconds; process-tree SIGKILL, no restart/stop hooks, no notification
extension and controls that the runner cannot alter are required. Unsupported
platform/properties refuse. No controls are created or modified by this program.

The existing external service bounds all descendants even if Python exits. The
launcher additionally cleans only its admitted, initially empty Q1 cgroup using
PID handles and membership checks. The actual installed kernel/systemd and
custodian's capacity/isolation records still need independent verification;
source code does not prove an existing instance is feasible or authorized.

Before dispatch, it verifies HEAD, cleanliness and every tracked file's bytes
against the Git tree; symlinks/submodules are refused and SHA256 hashes recorded.
It invokes the five required commands serially with a sanitized environment and
preserves stdout/stderr, exit codes, timings and timeout status. Each output
stream has a 1 MiB ceiling; hitting it marks the packet incomplete. A preexisting
receipt prevents an automatic retry.

receipt.json starts as STARTED_INCOMPLETE and is updated atomically before and
after each command. A killed process can leave that partial record and raw logs,
never a fabricated success. Failure, control/source drift, leaked children or
missing/truncated results stop the packet. COMMANDS_PASSED_NOT_ACCEPTANCE is only
a command result, not independent acceptance or a provider execution receipt.

Authored methods are counted from source. Actual executed/failure/error/skip
counts come from unittest summaries. Collection stays null because the required
CLI does not report it separately; incomplete/ambiguous counts stay null. When
available, memory.peak and cpu.stat provide cgroup-wide measurements. Missing
metrics and reconciled monetary cost stay null; no RSS/VRAM measurements are
invented. The requested limit is not reported as measured memory consumption.

Official mechanism references read during implementation:

- https://docs.kernel.org/admin-guide/cgroup-v2.html
- https://github.com/systemd/systemd/blob/main/man/systemd.service.xml
- https://github.com/systemd/systemd/blob/main/man/systemd.kill.xml

These document mechanisms, not current account authority or live free capacity.
