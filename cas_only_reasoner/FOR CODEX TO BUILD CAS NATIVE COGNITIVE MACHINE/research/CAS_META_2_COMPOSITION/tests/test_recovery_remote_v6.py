"""Pure checks. This file never loads a model or contacts a provider."""
import ast
from contextlib import contextmanager
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/"aws/recovery_remote_v6.py"
spec = importlib.util.spec_from_file_location("recovery_remote_pure_test", SOURCE)
remote = importlib.util.module_from_spec(spec)
spec.loader.exec_module(remote)
JOB = "cas-meta2-20260906090000-12345678"
ENV = {"CAS_META2_RUN_CONTRAST_RECOVERY": "1", "CAS_META2_RUN_GPU_TESTS": "1",
       "CAS_META2_AWS_JOB_ID": JOB, "CAS_META1_AWS_JOB_ID": JOB}


class RecoveryRemoteTests(unittest.TestCase):
    def test_explicit_aws_request_has_exact_time_bound(self):
        with patch.object(remote.sys, "platform", "linux"), patch.dict(os.environ, ENV, clear=True):
            remote.require_request(JOB, True, 2800)
            remote.require_request(JOB, True, 3000)
            for seconds in (2799, 3001, True, 3000.0):
                with self.assertRaises(ValueError):
                    remote.require_request(JOB, True, seconds)

    def test_local_or_disabled_request_fails_before_dynamic_import_and_output(self):
        args = SimpleNamespace(job=JOB, enable_native_evaluation=False, max_seconds=3000)
        original = __import__
        def protected(name, *a, **kw):
            if name.startswith(("cas_meta2", "torch", "boto", "botocore", "cas_meta", "cas_cjt")):
                raise AssertionError("unexpected task import")
            return original(name, *a, **kw)
        with patch("builtins.__import__", side_effect=protected), patch.object(remote.sys, "platform", "win32"):
            with self.assertRaisesRegex(ValueError, "AWS_LINUX"):
                remote.run(args)

    def test_wrong_job_and_missing_enable_are_refused(self):
        with patch.object(remote.sys, "platform", "linux"), patch.dict(os.environ, ENV, clear=True):
            for job in ("cas-meta2-20260906064703-c0d74ffa", "", JOB+"suffix"):
                with self.assertRaises(ValueError):
                    remote.require_request(job, True, 3000)
            for key in ENV:
                with patch.dict(os.environ, {key: ""}):
                    with self.assertRaises(ValueError):
                        remote.require_request(JOB, True, 3000)

    def test_gpu_command_runs_only_exact_new_file_with_alias_free_output(self):
        command = remote.gpu_command(Path("/tmp/retained"), "/python")
        self.assertEqual(command[:6], ["/python", "-B", "-m", "pytest", "-m", "gpu"])
        self.assertEqual([x for x in command if x.endswith(".py")],
                         ["tests/test_contrast_recovery_v6_gpu.py"])
        self.assertIn("cas_meta2.pytest_no_aliases_v4", command)
        self.assertEqual(command[command.index("--basetemp")+1], str(Path("/tmp/retained/gpu_scratch")))
        self.assertNotIn("--lf", command)

    def fixture_xml(self, path):
        root = ET.Element("testsuites")
        suite = ET.SubElement(root, "testsuite", tests="2", failures="0", errors="0", skipped="0")
        for name in remote.GPU_TESTS:
            ET.SubElement(suite, "testcase", classname="tests.test_contrast_recovery_v6_gpu", name=name)
        ET.ElementTree(root).write(path)
        return root

    def test_exact_two_successful_gpu_cases_required(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)/"tests.xml"
            self.fixture_xml(path)
            self.assertEqual(remote.validate_xml(path)["passed"], 2)

    def test_partial_skipped_duplicate_or_renamed_gpu_tests_cannot_pass(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)/"tests.xml"
            for change in ("failed", "skipped", "duplicate", "name", "class", "count", "missing", "error"):
                root = self.fixture_xml(path)
                suite = root.find("testsuite")
                cases = list(root.iter("testcase"))
                if change == "failed": ET.SubElement(cases[0], "failure")
                elif change == "skipped": ET.SubElement(cases[0], "skipped")
                elif change == "duplicate": cases[1].set("name", cases[0].get("name"))
                elif change == "name": cases[0].set("name", "other")
                elif change == "class": cases[0].set("classname", "unrelated")
                elif change == "count": suite.set("tests", "1")
                elif change == "missing": suite.remove(cases[0])
                elif change == "error": ET.SubElement(suite, "error")
                ET.ElementTree(root).write(path)
                with self.subTest(change=change), self.assertRaises(ValueError):
                    remote.validate_xml(path)

    def test_native_command_preserves_external_pins_and_has_no_training_switch(self):
        args = SimpleNamespace(admission=Path("/admission"), admission_sha256="a"*64,
            recovery_manifest=Path("/manifest"), recovery_manifest_sha256="b"*64,
            inputs=Path("/inputs"), packet=Path("/packet"), output=Path("/output"), job=JOB)
        command = remote.native_command(args, Path("/gate"), "c"*64, "/python")
        self.assertEqual(command[:4], ["/python", "-B", "-m", "cas_meta2.contrast_recovery_v6"])
        self.assertEqual(command[command.index("--max-seconds")+1], "2400")
        self.assertIn("--enable-native-evaluation", command)
        for option, value in (("--admission-sha256","a"*64), ("--recovery-manifest-sha256","b"*64),
                              ("--gpu-gate-sha256","c"*64), ("--packet",str(Path("/packet")))):
            self.assertEqual(command[command.index(option)+1], value)
        self.assertFalse(any("train" in token or "epoch" in token for token in command))

    def test_output_records_are_exclusive(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)/"receipt.json"
            remote.write_new(path, {"unchanged": True})
            before = path.read_bytes()
            with self.assertRaises(FileExistsError):
                remote.write_new(path, {"unchanged": False})
            self.assertEqual(path.read_bytes(), before)

    def test_source_has_no_model_or_provider_imports(self):
        tree = ast.parse(SOURCE.read_text())
        names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import): names.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom): names.append(node.module or "")
        self.assertFalse(any(name.split(".")[0] in ("torch", "numpy", "boto3", "botocore",
                                                    "cas_cjt", "casformer") for name in names))

    def test_gate_process_finishes_before_receipt_and_native_execution(self):
        tree = ast.parse(SOURCE.read_text())
        run = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run")
        calls = [(n.lineno, ast.unparse(n.func)) for n in ast.walk(run) if isinstance(n, ast.Call)]
        process = sorted(line for line, name in calls if name == "_run_process")
        gate = next(line for line, name in calls if name == "b.check_gpu_gate")
        xml = next(line for line, name in calls if name == "validate_xml")
        self.assertEqual(len(process), 2)
        self.assertLess(process[0], xml)
        self.assertLess(xml, gate)
        self.assertLess(gate, process[1])
        request = next(line for line, name in calls if name == "require_request")
        dynamic_import = min(n.lineno for n in ast.walk(run) if isinstance(n, ast.ImportFrom))
        self.assertLess(request, dynamic_import)

    def test_inputs_are_rechecked_after_native_run_and_failure_is_not_hidden(self):
        tree = ast.parse(SOURCE.read_text())
        run = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run")
        calls = [(n.lineno, ast.unparse(n.func)) for n in ast.walk(run) if isinstance(n, ast.Call)]
        loads = sorted(line for line, name in calls if name == "b.load_inputs")
        processes = sorted(line for line, name in calls if name == "_run_process")
        self.assertEqual(len(loads), 2)
        self.assertLess(loads[0], processes[0])
        self.assertGreater(loads[1], processes[1])
        handlers = [n for n in ast.walk(run) if isinstance(n, ast.ExceptHandler)]
        self.assertEqual(len(handlers), 1)
        self.assertTrue(any(isinstance(n, ast.Raise) and n.exc is None for n in ast.walk(handlers[0])))


if __name__ == "__main__":
    unittest.main()

