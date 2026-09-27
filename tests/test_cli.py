import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from helm_quantum.admission import ROOT
from coordination.codex import run_p2_checks as p2


class CliTest(unittest.TestCase):
    def command(self, *args):
        return subprocess.run([sys.executable, "-m", "helm_quantum", *args], cwd=ROOT,
                              text=True, capture_output=True, timeout=10, check=False)

    def test_actual_first_command_fresh_process(self):
        result = self.command("inventory", "--read-only")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(json.loads(result.stdout)["q0_complete"])

    def test_real_validate_boundary(self):
        result = self.command("validate", "--fixture", "q1-mod4")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertTrue(data["verification"]["accepted"])
        self.assertFalse(data["host_integrated"])
        self.assertFalse(data["verification"]["retained"])

    def test_real_negative_baseline(self):
        result = self.command("baseline", "--mode", "disabled", "--target", "parity")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "UNSAT_PROVED")

    def test_compare_and_sampling(self):
        result = self.command("compare", "--fixture", "q1-mod4", "--offline")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(set(json.loads(result.stdout)), {"exhaustive", "structured", "uniform"})

    def test_submit_refuses_without_reading_files(self):
        result = self.command("submit", "--request", "does-not-exist.json", "--authorization", "fake")
        self.assertEqual(result.returncode, 2)
        self.assertIn("SUBMISSION_REFUSED", json.loads(result.stderr)["reason"])

    def test_compile_reports_missing_compiler(self):
        result = self.command("compile", "--fixture", "q1-mod4", "--backend", "local")
        self.assertEqual(result.returncode, 2)
        self.assertIn("COMPILER_NOT_INTEGRATED", json.loads(result.stderr)["reason"])

    def test_invalid_program_cannot_pass_cli(self):
        result = self.command("verify-program", "--program", "4", "1", "0")
        self.assertEqual(result.returncode, 2)

    def test_no_implicit_cloud_fallback(self):
        result = self.command("estimate")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(json.loads(result.stdout)["submission_allowed"])


class FakeP2Runner:
    """Fake admission/execution for regression tests; never selected by the CLI."""
    def __init__(self, output, fail=None):
        self.source = ROOT
        self.output = output
        self.source_identity = {"commit": "FAKE_TEST_ONLY"}
        self.control_evidence = {"kind": "FAKE_TEST_ONLY"}
        self.grant = {"kind": "FAKE_TEST_ONLY_NOT_AUTHORITY"}
        self.fail = fail
        self.calls = []
        self.checks = 0

    def check(self):
        self.checks += 1
        if self.fail == "drift" and self.checks == 3:
            raise p2.Refused("process-tree controls changed")

    def verify_source(self):
        return {"commit": "CHANGED"} if self.fail == "source" else self.source_identity

    def measurements(self):
        return {"aggregate_memory_peak_bytes": p2.MEMORY_BYTES + 1 if self.fail == "memory" else None,
                "cgroup_cpu_usage_usec": None}

    def cleanup(self):
        return self.fail != "cleanup"

    def run(self, name, args):
        self.calls.append((name, args))
        stdout, stderr = self.output / f"{name}.stdout.txt", self.output / f"{name}.stderr.txt"
        stdout.write_text('{"fake":true}\n', encoding="utf-8")
        stderr.write_text("Ran 3 tests in 0.001s\n\nOK\n" if name in ("helpers", "builder") else "",
                          encoding="utf-8")
        return {"command": ["FAKE_PYTHON", *args], "exit_code": 1 if self.fail == name else 0,
                "timed_out": self.fail == "timeout", "elapsed_seconds": 0.001,
                "descendants_gone": True, "stdout": str(stdout), "stderr": str(stderr),
                "log_limit_reached": self.fail == "output"}


class P2LauncherTest(unittest.TestCase):
    def controls(self):
        properties = {"MainPID": "123", "ActiveState": "active", "SubState": "running", "Type": "exec",
                      "KillMode": "control-group", "SendSIGKILL": "yes", "Delegate": "no",
                      "NoNewPrivileges": "yes", "ProtectControlGroups": "yes", "PrivateMounts": "yes",
                      "CapabilityBoundingSet": "", "RestrictNamespaces": "yes", "PrivateUsers": "no",
                      "Restart": "no", "RuntimeRandomizedExtraUSec": "0", "RuntimeMaxUSec": "58s",
                      "ExecStop": "", "ExecStopPost": "", "NotifyAccess": "none", "FinalKillSignal": "9",
                      "TimeoutStopFailureMode": "kill", "OnFailure": "", "OnSuccess": "",
                      "FailureAction": "none", "SuccessAction": "none",
                      "TimeoutStopUSec": "1s", "ActiveEnterTimestampMonotonic": "1000000"}
        controls = {"cgroup.type": "domain", "memory.max": str(p2.MEMORY_BYTES), "memory.swap.max": "0",
                    "memory.oom.group": "1", "cpu.max": "100000 100000", "cpuset.cpus.effective": "2",
                    "cpuset.cpus.exclusive.effective": "2", "cpuset.cpus.partition": "isolated",
                    "pids.max": "32", "hugetlb.2MB.max": "0"}
        return properties, controls

    def test_no_enrollment_refuses_before_files_or_subprocess(self):
        with (patch.object(p2, "APPROVED_RUNNERS", ()), patch.object(p2, "read_grant") as grant,
              patch.object(p2.subprocess, "run") as command):
            with self.assertRaisesRegex(p2.Refused, "NO_ENROLLED_RUNNER"):
                p2.admit_current_runner()
        grant.assert_not_called()
        command.assert_not_called()

    def test_venue_env_and_caller_json_cannot_enroll(self):
        with patch.dict(p2.os.environ, {"Q1_RUNNER": "aws", "Q1_ADMITTED": "1", "AWS_INSTANCE_ID": "fake"}), \
             patch.object(p2, "APPROVED_RUNNERS", ()), \
             patch.object(p2, "read_grant", return_value={"approved": True}):
            with self.assertRaises(p2.Refused):
                p2.admit_current_runner()

    def test_aggregate_cpu_memory_swap_and_pid_bounds(self):
        properties, controls = self.controls()
        self.assertEqual(p2.validate_controls(properties, controls, pid=123, now_us=2_000_000), 59)
        for name, value in (("memory.max", "max"), ("memory.max", str(p2.MEMORY_BYTES + 1)),
                            ("memory.swap.max", "1"), ("memory.oom.group", "0"),
                            ("cpu.max", "200000 100000"), ("cpuset.cpus.effective", "0-3"),
                            ("cpuset.cpus.exclusive.effective", ""), ("pids.max", "max"),
                            ("hugetlb.2MB.max", "max")):
            with self.subTest(name=name, value=value), self.assertRaises(p2.Refused):
                p2.validate_controls(properties, {**controls, name: value}, pid=123, now_us=2_000_000)

    def test_process_tree_watchdog_not_parent_only_timeout(self):
        properties, controls = self.controls()
        for name, value in (("KillMode", "process"), ("Delegate", "yes"), ("MainPID", "999"),
                            ("SendSIGKILL", "no"), ("NoNewPrivileges", "no"),
                            ("RuntimeMaxUSec", "infinity"), ("RuntimeMaxUSec", "60s"),
                            ("TimeoutStopUSec", "5s"), ("Restart", "always"),
                            ("RuntimeRandomizedExtraUSec", "1s"), ("ProtectControlGroups", "no")):
            with self.subTest(name=name), self.assertRaises(p2.Refused):
                p2.validate_controls({**properties, name: value}, controls, pid=123, now_us=2_000_000)

    def test_custodian_grant_is_bound_to_enrolled_identity_and_fresh_invocation(self):
        pin = p2.RunnerPin("i-fixture", "123456789012", "fixture-custodian", "fixture-grant", "q1.service", 1001)
        grant = {"schema": "helm-q1-custodian-grant/1", **vars(pin), "invocation_id": "a" * 32,
                 "boot_id": "12345678-1234-1234-1234-123456789012", "source_commit": "b" * 40,
                 "source_root": "/opt/fixture", "output_root": "/var/lib/fixture/result",
                 "issued_unix_ns": 0, "expires_unix_ns": 60_000_000_000,
                 "free_capacity_record": "fixture-capacity", "incumbent_isolation_record": "fixture-isolation",
                 "cpu_count": 1, "memory_bytes": p2.MEMORY_BYTES, "wall_seconds": 60,
                 "cloud_usd": "0.00", "packets": 1, "tasks": 0, "shots": 0}
        context = {"invocation": grant["invocation_id"], "boot_id": grant["boot_id"], "now_ns": 1}
        p2.validate_grant(grant, pin, **context)
        for key, value in (("custodian", "caller"), ("instance_id", "i-other"), ("uid", True),
                           ("invocation_id", "c" * 32), ("expires_unix_ns", 0),
                           ("issued_unix_ns", True), ("source_commit", "caller-hash"),
                           ("cpu_count", 2), ("packets", 2), ("cloud_usd", "1.00"),
                           ("free_capacity_record", ""), ("approved", True)):
            with self.subTest(key=key), self.assertRaises(p2.Refused):
                p2.validate_grant({**grant, key: value}, pin, **context)

    def test_source_hash_mismatch_refuses_even_with_matching_head_label(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "source.py").write_text("changed", encoding="utf-8")
            runner = p2.LinuxRunner.__new__(p2.LinuxRunner)
            runner.source = root
            runner.grant = {"source_commit": "a" * 40}
            def fake_git(*args):
                if args[0] == "rev-parse":
                    return b"a" * 40 + b"\n"
                if args[0] == "status":
                    return b""
                return b"100644 blob " + b"b" * 40 + b"\tsource.py\0"
            runner.git = fake_git
            with patch.object(p2, "protected"), self.assertRaisesRegex(p2.Refused, "source bytes differ"):
                runner.verify_source()

    def test_expired_service_and_empty_durations_refuse(self):
        properties, controls = self.controls()
        with self.assertRaises(p2.Refused):
            p2.validate_controls(properties, controls, pid=123, now_us=60_000_000)
        for value in ("", "infinity", "-1s", "1day"):
            with self.assertRaises(p2.Refused):
                p2.duration_us(value)

    def test_success_receipt_uses_exact_five_commands_and_raw_logs(self):
        with tempfile.TemporaryDirectory() as directory:
            runner = FakeP2Runner(Path(directory))
            receipt = p2.run_packet(runner)
            self.assertEqual(receipt["status"], "COMMANDS_PASSED_NOT_ACCEPTANCE")
            self.assertFalse(receipt["acceptance"])
            self.assertEqual(runner.calls, [(name, args) for name, args, _ in p2.COMMANDS])
            for row in receipt["commands"]:
                self.assertTrue(Path(row["stdout"]).is_file())
                self.assertTrue(Path(row["stderr"]).is_file())
            self.assertEqual(receipt["commands"][-1]["counts"]["executed"], 3)
            self.assertIsNone(receipt["commands"][-1]["counts"]["collected"])
            self.assertIsNone(receipt["resource_after"]["aggregate_memory_peak_bytes"])

    def test_command_failure_stops_serial_packet(self):
        with tempfile.TemporaryDirectory() as directory:
            runner = FakeP2Runner(Path(directory), "baseline")
            receipt = p2.run_packet(runner)
            self.assertEqual(receipt["status"], "FAILED_OR_INCOMPLETE")
            self.assertEqual([name for name, _ in runner.calls], ["inventory", "baseline"])

    def test_timeout_output_limit_and_descendant_leaks_cannot_pass(self):
        for failure in ("timeout", "output", "cleanup", "memory"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                receipt = p2.run_packet(FakeP2Runner(Path(directory), failure))
                self.assertEqual(receipt["status"], "FAILED_OR_INCOMPLETE")

    def test_control_drift_prevents_next_command(self):
        with tempfile.TemporaryDirectory() as directory:
            runner = FakeP2Runner(Path(directory), "drift")
            receipt = p2.run_packet(runner)
            self.assertEqual(len(runner.calls), 1)
            self.assertEqual(receipt["status"], "FAILED_OR_INCOMPLETE")

    def test_source_change_cannot_get_success_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            receipt = p2.run_packet(FakeP2Runner(Path(directory), "source"))
            self.assertEqual(receipt["status"], "FAILED_OR_INCOMPLETE")

    def test_existing_receipt_is_not_overwritten_or_retried(self):
        with tempfile.TemporaryDirectory() as directory:
            runner = FakeP2Runner(Path(directory))
            path = runner.output / "receipt.json"
            path.write_text("previous incomplete packet", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                p2.run_packet(runner)
            self.assertEqual(path.read_text(), "previous incomplete packet")
            self.assertEqual(runner.calls, [])

    def test_partial_unittest_output_does_not_invent_counts(self):
        counts = p2.unittest_counts("test_first ... ok\ntest_second ... ")
        self.assertIsNone(counts["executed"])
        self.assertIsNone(counts["passed"])
        counts = p2.unittest_counts("Ran 3 tests in 0.1s\n\nFAILED (failures=2, errors=1)\n")
        self.assertEqual(counts["executed"], 3)
        self.assertEqual(counts["failed"], 2)
        self.assertEqual(counts["errors"], 1)
        self.assertIsNone(counts["passed"])

    def test_real_launcher_cli_refuses_without_runner(self):
        result = subprocess.run([sys.executable, str(ROOT / "coordination/codex/run_p2_checks.py")],
                                cwd=ROOT, text=True, capture_output=True, timeout=10, check=False)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "NOT_RUN_REFUSED")
        self.assertEqual(json.loads(result.stdout)["commands_started"], 0)
