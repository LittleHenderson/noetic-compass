import json
import subprocess
import sys
import unittest

from helm_quantum.admission import ROOT


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
