"""Bounded Q1 check launcher. No enrolled runner means refusal, including on MSI.

An existing custodian-operated systemd service must already enforce the limits.
This program only reads its controls; it cannot provision, start, or alter them.
Internal dependency seams exist for offline tests, never as CLI admission options.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import signal
import stat
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MEMORY_BYTES = 512 * 1024 * 1024
WALL_SECONDS = 60
LOG_BYTES = 1024 * 1024
GRANT_PATH = Path("/run/helm-q1/p2/grant.json")
ENV = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
       "PYTHONHASHSEED": "0", "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1",
       "GIT_OPTIONAL_LOCKS": "0"}
COMMANDS = (
    ("inventory", ("-m", "helm_quantum", "inventory", "--read-only"), None),
    ("baseline", ("-m", "helm_quantum", "baseline", "--mode", "disabled"), None),
    ("validate", ("-m", "helm_quantum", "validate", "--fixture", "q1-mod4"), None),
    ("helpers", ("-m", "unittest", "discover", "-s", "input_package/original_package/tests", "-v"),
     "input_package/original_package/tests"),
    ("builder", ("-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"), "tests"),
)


class Refused(ValueError):
    pass


def need(condition, reason):
    if not condition:
        raise Refused(reason)


@dataclass(frozen=True)
class RunnerPin:
    instance_id: str
    account_id: str
    custodian: str
    grant_id: str
    unit: str
    uid: int


# Enroll only from independently verified custodian/grant evidence in a reviewed
# source change. No caller file, flag or environment variable can populate this.
APPROVED_RUNNERS: tuple[RunnerPin, ...] = ()


def protected(path: Path, *, regular=True):
    """Root-controlled ancestry, no symlinks, ACL-effective runner write refusal."""
    need(path.is_absolute(), "trusted path must be absolute")
    for item in (*reversed(path.parents), path):
        info = item.lstat()
        need(not stat.S_ISLNK(info.st_mode), f"symlink in trusted path: {item}")
        need(info.st_uid == 0 and not info.st_mode & 0o022 and not os.access(item, os.W_OK),
             f"runner-writable or non-root trusted path: {item}")
    if regular:
        info = path.stat()
        need(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, "trusted file must be regular and unlinked")


def unique_object(pairs):
    value = {}
    for key, item in pairs:
        need(key not in value, "duplicate grant key")
        value[key] = item
    return value


def read_grant():
    protected(GRANT_PATH)
    need(GRANT_PATH.stat().st_size <= 16384, "grant too large")
    return json.loads(GRANT_PATH.read_text(encoding="utf-8"), object_pairs_hook=unique_object,
                      parse_constant=lambda _: (_ for _ in ()).throw(Refused("nonfinite grant number")))


def duration_us(value):
    units = {"us": 1, "ms": 1000, "s": 1_000_000, "min": 60_000_000}
    if value == "0":
        return 0
    total = 0
    for token in value.split():
        match = re.fullmatch(r"([0-9]+)(us|ms|s|min)", token)
        need(match is not None, "unsupported/infinite systemd duration")
        total += int(match[1]) * units[match[2]]
    need(total > 0, "missing systemd duration")
    return total


def validate_controls(properties, controls, *, pid, now_us):
    need(properties.get("MainPID") == str(pid), "launcher is not the service MainPID")
    expected = {"ActiveState": "active", "SubState": "running", "Type": "exec",
                "KillMode": "control-group", "SendSIGKILL": "yes", "Delegate": "no",
                "NoNewPrivileges": "yes", "ProtectControlGroups": "yes",
                "PrivateMounts": "yes", "CapabilityBoundingSet": "",
                "RestrictNamespaces": "yes", "PrivateUsers": "no",
                "Restart": "no", "RuntimeRandomizedExtraUSec": "0",
                "ExecStop": "", "ExecStopPost": "", "NotifyAccess": "none",
                "FinalKillSignal": "9", "TimeoutStopFailureMode": "kill",
                "OnFailure": "", "OnSuccess": "", "FailureAction": "none", "SuccessAction": "none"}
    for key, value in expected.items():
        need(properties.get(key) == value, f"unadmitted service control: {key}")
    runtime = duration_us(properties["RuntimeMaxUSec"])
    stopping = duration_us(properties["TimeoutStopUSec"])
    need(0 < runtime and 0 <= stopping <= 2_000_000 and runtime + stopping <= WALL_SECONDS * 1_000_000,
         "external process-tree deadline exceeds 60 seconds")
    start = int(properties["ActiveEnterTimestampMonotonic"])
    need(0 < start <= now_us < start + runtime, "service deadline expired or not established")
    need(controls["cgroup.type"] == "domain", "non-domain cgroup")
    need(controls["memory.max"] == str(MEMORY_BYTES), "aggregate memory limit must be 512 MiB")
    need(controls["memory.swap.max"] == "0", "swap must be disabled for this cgroup")
    need(controls["memory.oom.group"] == "1", "OOM must stop the whole Q1 cgroup")
    need(re.fullmatch(r"[1-9][0-9]* [1-9][0-9]*", controls["cpu.max"]) is not None, "invalid CPU quota")
    quota, period = controls["cpu.max"].split()
    need(quota.isdigit() and period.isdigit() and 0 < int(quota) <= int(period), "CPU quota exceeds one CPU")
    need(re.fullmatch(r"[0-9]+", controls["cpuset.cpus.effective"]) is not None,
         "exactly one effective CPU required")
    need(controls["cpuset.cpus.partition"] in ("root", "isolated") and
         controls["cpuset.cpus.exclusive.effective"] == controls["cpuset.cpus.effective"],
         "CPU must already be reserved as an exclusive partition")
    need(controls["pids.max"].isdigit() and 1 <= int(controls["pids.max"]) <= 32,
         "finite process-tree PID limit required")
    # HugeTLB allocations are not necessarily charged to memory.max.
    need(all(value == "0" for name, value in controls.items() if name.startswith("hugetlb.")),
         "hugetlb allocations must be disabled")
    return (start + runtime) / 1_000_000


def validate_grant(grant, pin, *, invocation, boot_id, now_ns):
    fields = {"schema", "instance_id", "account_id", "custodian", "grant_id", "unit", "uid",
              "invocation_id", "boot_id", "source_commit", "source_root", "output_root",
              "issued_unix_ns", "expires_unix_ns", "free_capacity_record", "incumbent_isolation_record",
              "cpu_count", "memory_bytes", "wall_seconds", "cloud_usd", "packets", "tasks", "shots"}
    need(type(grant) is dict and set(grant) == fields, "unknown or missing custodian grant fields")
    need(grant["schema"] == "helm-q1-custodian-grant/1", "unknown custodian grant")
    for key in ("instance_id", "account_id", "custodian", "grant_id", "unit", "uid"):
        need(type(grant[key]) is type(getattr(pin, key)) and grant[key] == getattr(pin, key),
             f"grant differs from independently enrolled {key}")
    need(type(invocation) is str and re.fullmatch(r"[0-9a-f]{32}", invocation), "missing live invocation ID")
    need(type(boot_id) is str and re.fullmatch(r"[0-9a-f-]{36}", boot_id), "missing live boot ID")
    need(grant["invocation_id"] == invocation and grant["boot_id"] == boot_id,
         "stale or foreign service invocation")
    for name, expected in (("cpu_count", 1), ("memory_bytes", MEMORY_BYTES), ("wall_seconds", 60),
                           ("packets", 1), ("tasks", 0), ("shots", 0)):
        need(type(grant[name]) is int and grant[name] == expected, f"invalid grant limit: {name}")
    need(grant["cloud_usd"] == "0.00", "no new spending authorized")
    start, end = grant["issued_unix_ns"], grant["expires_unix_ns"]
    need(type(start) is int and type(end) is int and start <= now_ns < end <= start + 60_000_000_000,
         "grant freshness/expiry invalid")
    need(type(grant["source_commit"]) is str and re.fullmatch(r"[0-9a-f]{40}", grant["source_commit"]),
         "exact source commit required")
    for name in ("free_capacity_record", "incumbent_isolation_record"):
        need(type(grant[name]) is str and 0 < len(grant[name]) <= 1024, f"missing custodian {name}")


class LinuxRunner:
    def __init__(self, pin):
        self.pin = pin
        self.python = str(Path(sys.executable).resolve())
        self.grant = read_grant()
        self.source = Path(self.grant["source_root"])
        self.output = Path(self.grant["output_root"])
        protected(Path(self.python))
        protected(Path("/usr/bin/systemctl"))
        protected(Path("/usr/bin/git"))
        protected(self.source, regular=False)
        need(self.source == ROOT, "launcher must be part of the admitted source checkout")
        need(self.output.is_absolute() and self.output.resolve() == self.output and
             self.output != self.source and self.source not in self.output.parents,
             "output must be separate from the source")
        protected(self.output.parent, regular=False)
        need(not self.output.is_symlink() and self.output.is_dir() and
             self.output.stat().st_uid == os.geteuid(), "custodian-provided result directory required")
        self.cgroup = None
        self.deadline = None
        self.check()
        need(self.members() == {os.getpid()}, "runner contains another job/process")
        need(int((self.cgroup / "memory.current").read_text()) < MEMORY_BYTES,
             "no available memory inside dedicated runner")
        self.source_identity = self.verify_source()

    def systemd(self):
        result = subprocess.run(["/usr/bin/systemctl", "show", self.pin.unit, "--no-pager"],
                                env=ENV, capture_output=True, text=True, timeout=2, check=False)
        need(result.returncode == 0, "cannot read existing service controls")
        return dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)

    def check(self):
        properties = self.systemd()
        validate_grant(self.grant, self.pin, invocation=properties.get("InvocationID"),
                       boot_id=Path("/proc/sys/kernel/random/boot_id").read_text().strip(), now_ns=time.time_ns())
        membership = Path("/proc/self/cgroup").read_text().strip()
        group = properties.get("ControlGroup", "")
        need(group.startswith("/system.slice/") and membership == "0::" + group,
             "not in the independently bounded system service")
        need(".." not in Path(group).parts, "invalid cgroup path")
        self.cgroup = Path("/sys/fs/cgroup") / group.lstrip("/")
        protected(self.cgroup, regular=False)
        need(not any(p.is_dir() for p in self.cgroup.iterdir()), "nested/delegated cgroup refused")
        names = ["cgroup.type", "memory.max", "memory.swap.max", "memory.oom.group", "cpu.max",
                 "cpuset.cpus.effective", "cpuset.cpus.exclusive.effective", "cpuset.cpus.partition", "pids.max"]
        names += [p.name for p in self.cgroup.glob("hugetlb.*.max")]
        controls = {}
        for name in names:
            path = self.cgroup / name
            need(not os.access(path, os.W_OK), f"runner can alter {name}")
            controls[name] = path.read_text().strip()
        self.deadline = validate_controls(properties, controls, pid=os.getpid(),
                                          now_us=time.monotonic_ns() // 1000)
        self.control_evidence = {"systemd": {k: properties.get(k) for k in (
            "InvocationID", "MainPID", "ControlGroup", "RuntimeMaxUSec", "TimeoutStopUSec",
            "KillMode", "SendSIGKILL", "Delegate", "NoNewPrivileges", "ProtectControlGroups")},
            "cgroup": controls}
        need(time.monotonic() < self.deadline - 2, "insufficient time for execution and cleanup")

    def git(self, *args):
        result = subprocess.run(["/usr/bin/git", "-c", f"safe.directory={self.source}",
                                 "-c", "core.fsmonitor=false", "-c", "core.hooksPath=/dev/null", *args],
                                cwd=self.source, env=ENV, capture_output=True, timeout=2, check=False)
        need(result.returncode == 0, "source inspection command failed")
        return result.stdout

    def verify_source(self):
        need(self.git("rev-parse", "HEAD").decode().strip() == self.grant["source_commit"], "wrong source commit")
        need(not self.git("status", "--porcelain=v1", "--untracked-files=all"), "source checkout is dirty")
        files = {}
        total = 0
        for item in self.git("ls-tree", "-rz", "--full-tree", "HEAD").split(b"\0"):
            if not item:
                continue
            metadata, raw_path = item.split(b"\t", 1)
            mode, kind, object_id = metadata.split()
            relative = raw_path.decode("utf-8")
            need(mode in (b"100644", b"100755") and kind == b"blob", "symlink/submodule source refused")
            path = self.source / relative
            need(path.resolve().is_relative_to(self.source), "source path escapes checkout")
            protected(path)
            size = path.stat().st_size
            total += size
            need(size <= 1024 * 1024 and total <= 8 * 1024 * 1024, "source inspection exceeds packet bound")
            content = path.read_bytes()
            actual = hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()
            need(actual == object_id.decode(), f"source bytes differ from commit: {relative}")
            files[relative] = hashlib.sha256(content).hexdigest()
        return {"commit": self.grant["source_commit"], "sha256": files}

    def members(self):
        return {int(value) for value in (self.cgroup / "cgroup.procs").read_text().split()}

    def measurements(self):
        result = {"aggregate_memory_peak_bytes": None, "cgroup_cpu_usage_usec": None}
        try:
            result["aggregate_memory_peak_bytes"] = int((self.cgroup / "memory.peak").read_text())
        except (OSError, ValueError):
            pass
        try:
            values = dict(line.split() for line in (self.cgroup / "cpu.stat").read_text().splitlines())
            result["cgroup_cpu_usage_usec"] = int(values["usage_usec"])
        except (OSError, KeyError, ValueError):
            pass
        return result

    def cleanup(self):
        # Only the already-admitted, initially empty Q1 cgroup is eligible.
        for pid in self.members() - {os.getpid()}:
            try:
                fd = os.pidfd_open(pid)
                try:
                    expected = "0::/" + self.cgroup.relative_to("/sys/fs/cgroup").as_posix()
                    if Path(f"/proc/{pid}/cgroup").read_text().strip() == expected:
                        signal.pidfd_send_signal(fd, signal.SIGKILL)
                finally:
                    os.close(fd)
            except (ProcessLookupError, FileNotFoundError):
                pass
        return self.members() == {os.getpid()}

    def run(self, name, args):
        import resource
        def child_limits():
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
            resource.setrlimit(resource.RLIMIT_FSIZE, (LOG_BYTES, LOG_BYTES))
        command = [self.python, *args]
        started = time.monotonic()
        stdout = self.output / f"{name}.stdout.txt"
        stderr = self.output / f"{name}.stderr.txt"
        env = {**ENV, "TMPDIR": str(self.output), "PYTHONPYCACHEPREFIX": str(self.output / "empty-cache")}
        with stdout.open("xb") as out, stderr.open("xb") as err:
            process = subprocess.Popen(command, cwd=self.source, env=env, stdin=subprocess.DEVNULL,
                                       stdout=out, stderr=err, start_new_session=True, preexec_fn=child_limits)
            timeout = False
            try:
                process.wait(timeout=max(0.001, self.deadline - time.monotonic() - 2))
            except subprocess.TimeoutExpired:
                timeout = True
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=max(0.001, self.deadline - time.monotonic()))
        clean = self.cleanup()
        return {"command": command, "exit_code": process.returncode, "timed_out": timeout,
                "elapsed_seconds": time.monotonic() - started, "descendants_gone": clean,
                "stdout": str(stdout), "stderr": str(stderr),
                "log_limit_reached": max(stdout.stat().st_size, stderr.stat().st_size) >= LOG_BYTES}


def admit_current_runner():
    need(bool(APPROVED_RUNNERS), "NO_ENROLLED_RUNNER: missing verified Q1 custodian, grant and enforceable runner")
    need(sys.platform == "linux" and os.geteuid() != 0, "requires an unprivileged admitted Linux service")
    need(hasattr(os, "pidfd_open") and hasattr(signal, "pidfd_send_signal"), "PID-safe descendant cleanup unavailable")
    vendor = Path("/sys/devices/virtual/dmi/id/sys_vendor").read_text().strip()
    instance = Path("/sys/devices/virtual/dmi/id/board_asset_tag").read_text().strip()
    need(vendor == "Amazon EC2", "current machine is not an admitted EC2 runner")
    matches = [p for p in APPROVED_RUNNERS if p.instance_id == instance and p.uid == os.geteuid()]
    need(len(matches) == 1, "machine/user does not match an independently enrolled runner")
    return LinuxRunner(matches[0])


def authored_count(root, directory):
    count = 0
    for path in sorted((root / directory).glob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for cls in (node for node in tree.body if isinstance(node, ast.ClassDef)):
            count += sum(isinstance(node, ast.FunctionDef) and node.name.startswith("test_") for node in cls.body)
    return count


def unittest_counts(text):
    summaries = list(re.finditer(r"^Ran (\d+) tests? in [0-9.]+s$", text, re.MULTILINE))
    finals = list(re.finditer(r"^(OK|FAILED)(?: \(([^\n]*)\))?$", text, re.MULTILINE))
    counts = {"collected": None, "executed": None, "passed": None, "failed": None,
              "errors": None, "skipped": None, "expected_failures": None, "unexpected_successes": None}
    if len(summaries) != 1 or len(finals) != 1:
        return counts
    executed = int(summaries[0][1])
    extras = {key.strip(): value for key, value in re.findall(r"([a-z ]+)=(\d+)", finals[0][2] or "")}
    failed, errors, skipped = (int(extras.get(key, 0)) for key in ("failures", "errors", "skipped"))
    expected, unexpected = (int(extras.get(key, 0)) for key in ("expected failures", "unexpected successes"))
    counts.update(executed=executed, failed=failed, errors=errors, skipped=skipped,
                  expected_failures=expected, unexpected_successes=unexpected)
    if finals[0][1] == "OK" and not failed and not errors and not unexpected:
        counts["passed"] = max(0, executed - skipped - expected)
    return counts


def write_receipt(path, receipt):
    temporary = path.with_suffix(".tmp")
    with temporary.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(receipt, stream, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def run_packet(runner):
    """Internal seam for fake-controller regression tests; not a grant interface."""
    runner.check()
    receipt_path = runner.output / "receipt.json"
    with receipt_path.open("x", encoding="utf-8") as stream:
        stream.write('{"status":"STARTED_INCOMPLETE","acceptance":false}\n')
    receipt = {"schema": "helm-q1-p2-execution/1", "status": "RUNNING", "acceptance": False,
               "source": runner.source_identity, "authority": runner.grant,
               "environment": {"python_version": sys.version, "platform": sys.platform,
                               "python_executable": getattr(runner, "python", None)},
               "controls": runner.control_evidence, "commands": [], "resource_before": runner.measurements(),
               "resource_after": None, "collection_note": "unittest CLI does not separately report collected count",
               "measurement_scope": "dedicated cgroup including launcher and control queries; not per-test RSS",
               "cloud_cost_usd": None, "quantum_tasks": 0, "quantum_shots": 0}
    started = time.monotonic()
    try:
        for name, args, directory in COMMANDS:
            runner.check()
            row = {"name": name, "status": "STARTED_OUTCOME_UNKNOWN"}
            if directory:
                row["authored_methods"] = authored_count(runner.source, directory)
            receipt["commands"].append(row)
            write_receipt(receipt_path, receipt)
            row.update(runner.run(name, args))
            if directory:
                row["counts"] = unittest_counts(Path(row["stderr"]).read_text(encoding="utf-8", errors="replace"))
            okay = (row["exit_code"] == 0 and not row["timed_out"] and row["descendants_gone"]
                    and not row["log_limit_reached"])
            if directory:
                counts = row["counts"]
                okay = (okay and counts["executed"] is not None and counts["executed"] > 0
                        and counts["failed"] == 0 and counts["errors"] == 0
                        and counts["unexpected_successes"] == 0 and counts["passed"] is not None)
            row["status"] = "COMPLETED" if okay else "FAILED_OR_INCOMPLETE"
            write_receipt(receipt_path, receipt)
            if not okay:
                receipt["status"] = "FAILED_OR_INCOMPLETE"
                break
        else:
            runner.check()
            need(runner.verify_source() == runner.source_identity, "source changed during checks")
            receipt["status"] = "COMMANDS_PASSED_NOT_ACCEPTANCE"
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError) as exc:
        receipt["status"] = "FAILED_OR_INCOMPLETE"
        receipt["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        try:
            receipt["descendants_gone"] = runner.cleanup()
            receipt["resource_after"] = runner.measurements()
        except (OSError, ValueError) as exc:
            receipt["descendants_gone"] = None
            receipt["cleanup_or_measurement_error"] = f"{type(exc).__name__}: {exc}"
        receipt["launcher_elapsed_seconds"] = time.monotonic() - started
        peak = (receipt["resource_after"] or {}).get("aggregate_memory_peak_bytes")
        if peak is not None and peak > MEMORY_BYTES:
            receipt["status"] = "FAILED_OR_INCOMPLETE"
            receipt["resource_limit_exceeded"] = "aggregate memory peak"
        if receipt["launcher_elapsed_seconds"] > WALL_SECONDS:
            receipt["status"] = "FAILED_OR_INCOMPLETE"
            receipt["resource_limit_exceeded"] = "wall time"
        if not receipt["descendants_gone"]:
            receipt["status"] = "FAILED_OR_INCOMPLETE"
        write_receipt(receipt_path, receipt)
    return receipt


def main():
    try:
        need(len(sys.argv) == 1, "no venue, grant, control or source override flags are accepted")
        runner = admit_current_runner()
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError) as exc:
        print(json.dumps({"status": "NOT_RUN_REFUSED", "reason": str(exc), "commands_started": 0,
                          "command_scope": "five required packet commands; read-only preflight may have run",
                          "collected": 0, "executed": 0, "passed": 0, "failed": 0, "errors": 0,
                          "skipped": 0, "acceptance": False}))
        return 2
    try:
        receipt = run_packet(runner)
        print(json.dumps({"status": receipt["status"], "receipt": str(runner.output / "receipt.json")}))
        return 0 if receipt["status"] == "COMMANDS_PASSED_NOT_ACCEPTANCE" else 1
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError) as exc:
        print(json.dumps({"status": "ABORTED_OUTCOME_INCOMPLETE", "reason": str(exc),
                          "receipt": str(runner.output / "receipt.json"),
                          "commands_started": None, "acceptance": False}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
