"""Real exited pure child on saved diagnostic bytes; no AWS or model execution."""
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "records/contrast_v7_cold_child_review_001"


class ColdChildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        output = ROOT / "runs" / ("v7cold-" + uuid4().hex[:12])
        assert output.resolve().is_relative_to(ROOT / "runs") and not output.exists()
        command = [sys.executable, "-I", "-B", str(REVIEW / "probe.py"), str(output)]
        environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
                           CUDA_VISIBLE_DEVICES="", CAS_META1_RUN_GPU_TESTS="0", CAS_META2_RUN_GPU_TESTS="0")
        environment.pop("PYTHONPATH", None)
        run = subprocess.run(command, cwd=ROOT, env=environment, capture_output=True, timeout=300)
        cls.output = output
        if output.exists():
            (output / "coordinator.stdout.txt").write_bytes(run.stdout)
            (output / "coordinator.stderr.txt").write_bytes(run.stderr)
            with (output / "coordinator_process.json").open("x", encoding="utf-8") as stream:
                json.dump({"command": command, "cwd": str(ROOT), "returncode": run.returncode,
                    "stdout_sha256": sha256(run.stdout).hexdigest(), "stderr_sha256": sha256(run.stderr).hexdigest(),
                    "fresh_coordinator": True, "actual_aws": False}, stream, sort_keys=True, indent=2)
        if run.returncode:
            raise AssertionError("PURE_COLD_PROBE_FAILED:" + str(output) + "\n"
                                 + run.stderr.decode(errors="replace"))
        cls.receipt = json.loads((output / "probe_receipt.json").read_bytes())
        print("PURE_COLD_CHILD_RETAINED_OUTPUT=" + str(output), flush=True)

    def test_completed_saved_bundle_validation(self):
        r = self.receipt
        self.assertTrue(r["completed"])
        self.assertEqual(r["fixture_seed"], 926603)
        self.assertEqual(r["splits"], {
            "train": {"tasks": 352, "depths": {"1": 32, "2": 160, "3": 160}},
            "validation": {"tasks": 24, "depths": {"1": 8, "2": 8, "3": 8}},
            "test": {"tasks": 9, "depths": {"3": 6, "4": 3}}})

    def test_real_child_exited_before_report_was_consumed(self):
        path = self.output / "evaluation/cold_validation_process/actual_process_receipt.json"
        process = json.loads(path.read_bytes())
        self.assertTrue(process["completed"])
        self.assertEqual(process["returncode"], 0)
        self.assertNotEqual(process["pid"], self.receipt["coordinator_pid"])
        self.assertTrue(process["new_process_group"])
        self.assertTrue(process["pure_test_platform_adapter"])

    def test_private_targets_opened_only_after_seal_in_actual_prepare(self):
        openings = self.receipt["private_opening_order"]
        self.assertTrue(openings)
        self.assertTrue(all(row["sealed_before_open"] for row in openings))
        self.assertTrue(self.receipt["synthetic_training_gate"])
        self.assertTrue(self.receipt["synthetic_neural_predictions"])

    def test_baseline_find_spec_remains_callable_without_importing_models(self):
        self.assertEqual(self.receipt["find_spec_before"], self.receipt["find_spec_after"])
        self.assertEqual(set(self.receipt["find_spec_before"]), {"casformer", "cas_cjt"})
        self.assertTrue(all(self.receipt["find_spec_before"].values()))
        self.assertTrue(self.receipt["coordinator_hooks_and_path_unchanged"])
        wheels = self.receipt["frozen_wheel_file_fixture"]
        self.assertEqual(wheels["verified_before"], wheels["verified_after"])
        self.assertFalse(wheels["installed_environment_changed"])
        self.assertFalse(wheels["package_modules_imported"])

    def test_source_and_all_protected_bytes_unchanged(self):
        self.assertTrue(self.receipt["source_unchanged"])
        self.assertEqual(self.receipt["source_before"], self.receipt["source_after"])
        self.assertEqual(self.receipt["protected_baseline"]["files_verified"], 316)
        self.assertTrue(self.receipt["dataset_files_unchanged"])

    def test_external_manifest_loader_and_source_pin_changes_rejected(self):
        for name in ("wrong_source", "wrong_manifest", "wrong_loader", "wrong_pins"):
            with self.subTest(name=name):
                self.assertIn(name, self.receipt["negative_cases"])
                self.assertFalse(self.receipt["negative_cases"][name]["child_report_exists"])

    def test_curriculum_parameters_and_exclusions_are_bound(self):
        for name in ("wrong_seed", "wrong_config", "wrong_exclusions"):
            with self.subTest(name=name):
                self.assertIn(name, self.receipt["negative_cases"])
                self.assertFalse(self.receipt["negative_cases"][name]["child_report_exists"])

    def test_request_hash_checked_before_child_private_read(self):
        markers = {row["case"]: row for row in self.receipt["child_exit_markers"]}
        self.assertEqual(markers["request_before_child"]["private_reads"], [])
        self.assertFalse(self.receipt["negative_cases"]["request_before_child"]["child_report_exists"])

    def test_initial_source_check_precedes_child_private_reads(self):
        markers = {row["case"]: row for row in self.receipt["child_exit_markers"]}
        self.assertEqual(markers["wrong_source"]["private_reads"], [])

    def test_request_hash_rechecked_after_exit(self):
        found = self.receipt["negative_cases"]["request_after_exit"]
        self.assertIn("V7_NATIVE_COLD_CHILD_EXIT_REQUIRED", found["message"])
        self.assertFalse(found["report_read_after_rejection"])

    def test_failed_exit_receipt_not_accepted(self):
        found = self.receipt["negative_cases"]["bad_exit"]
        self.assertIn("SUCCESSFUL_TRAINING_PROCESS_EXIT_REQUIRED", found["message"])
        self.assertFalse(found["report_read_after_rejection"])

    def test_same_process_identity_not_accepted(self):
        found = self.receipt["negative_cases"]["same_pid"]
        self.assertIn("V7_NATIVE_COLD_CHILD_EXIT_REQUIRED", found["message"])
        self.assertFalse(found["report_read_after_rejection"])

    def test_every_negative_request_stops_before_report_read(self):
        self.assertEqual(len(self.receipt["negative_cases"]), 11)
        self.assertTrue(all(not row["report_read_after_rejection"]
                            for row in self.receipt["negative_cases"].values()))

    def test_no_neural_provider_or_external_actions(self):
        self.assertEqual(self.receipt["state"]["forbidden_attempts"], [])
        self.assertFalse(self.receipt["actual_aws"])
        self.assertFalse(self.receipt["neural_execution"])
        self.assertEqual(len(self.receipt["child_exit_markers"]), 12)
        for row in self.receipt["child_exit_markers"]:
            self.assertEqual(row["forbidden_attempts"], [])
            self.assertEqual(row["neural_or_provider_modules"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
