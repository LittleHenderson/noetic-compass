"""Independent synthetic orchestration checks; never models, AWS or task generation."""
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import importlib.abc
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "records/contrast_v7_orchestration_review_001"


@contextmanager
def imports():
    class Guard(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if fullname.split(".")[0] in {"torch", "casformer", "cas_cjt", "cas_meta",
                                          "tensorflow", "jax", "cupy", "boto3", "botocore"}:
                raise AssertionError("PURE_ORCHESTRATION_IMPORT_REFUSED:" + fullname)
    hooks, paths = list(sys.meta_path), list(sys.path)
    sys.meta_path.insert(0, Guard())
    sys.path.insert(0, str(ROOT))
    try:
        yield
    finally:
        sys.meta_path[:], sys.path[:] = hooks, paths


with imports():
    from cas_meta2.contrast_v7 import campaign as q, gpu_preflight as gpu
    from cas_meta2 import campaign_v3 as frozen


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json.dumps(value, sort_keys=True, separators=(",", ":")).encode() + b"\n")


def process(path, command, *, pid=12345):
    path.parent.mkdir(parents=True, exist_ok=True)
    for name in ("stdout", "stderr"):
        (path.parent / (name + ".txt")).write_bytes(b"")
    now = datetime.now(timezone.utc)
    row = {"schema": "cas-meta2-campaign-subprocess/3", "command": command,
           "completed": True, "returncode": 0, "timed_out": False, "pid": pid,
           "new_process_group": True, "automatic_retry": False,
           "started_utc": (now - timedelta(seconds=3)).isoformat(),
           "finished_utc": (now - timedelta(seconds=2)).isoformat(), "wall_seconds": 1.0,
           "stdout_sha256": sha256(b"").hexdigest(), "stderr_sha256": sha256(b"").hexdigest(),
           "synthetic_test_receipt": True}
    write(path, row)
    return row


def native_smoke():
    arms = ("cas_untrained", "cas_trained", "generic_untrained", "generic_trained", "rule")
    row = {"total": 9, "task_correct": 9, "all_cases_in_denominator": True,
           "compute_complete": True, "post_admission_runtime_failures": 0}
    return {"schema": "cas-meta2-prototype-native-evaluation/7", "completed": True,
            "cases": 9, "reference_cases": 9, "arm_verdicts": 45, "learning_accepted": False,
            "results": {arm: deepcopy(row) for arm in arms},
            "groups": {name: {arm: {"total": count} for arm in arms} for name, count in
                       (("depth_3", 6), ("depth_4", 3), ("same_depth", 3),
                        ("wording_shift", 3), ("deeper_calls", 3))}}


class OrchestrationTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(imports())
        scratch = RECORD / "scratch"
        scratch.mkdir(parents=True, exist_ok=True)
        self.output = Path(tempfile.mkdtemp(prefix="test-", dir=scratch))
        self.job = "cas-meta2-20000101000000-00000001"
        self.source = {"synthetic_source": "1" * 64}
        self.baseline = {"synthetic_baseline": True}
        self.spec = deepcopy(q.profile.FIXED_SPEC)
        self.enterContext(patch.object(q.t, "source_identity", return_value=self.source))

    def gpu_fixture(self):
        root = self.output
        process(root / "processes/gpu_gate/process_receipt.json", q.gpu_command(root))
        (root / "gpu_test.xml").write_text(
            '<testsuites><testsuite tests="1" failures="0" errors="0" skipped="0">'
            '<testcase classname="tests.test_contrast_v7_train_gpu" name="' + gpu.GPU_TEST
            + '"/></testsuite></testsuites>', encoding="utf-8")
        write(root / "initial_identity.json", {"source_sha256": self.source, "baseline": self.baseline})
        self.smoke_path = root / "gpu_tmp/current/gpu_smoke_receipt.json"
        self.native_path = self.smoke_path.parent / "native_evaluation/native_receipt.json"
        self.native = native_smoke()
        write(self.native_path, self.native)
        self.smoke = {"schema": gpu.SCHEMA, "status": "V7_KNOWN_FIXTURE_CUDA_FULL_PIPELINE_SMOKE_PASSED",
            "completed": True, "job": self.job, "native_evaluation_completed": True,
            "source_sha256": self.source, "baseline": self.baseline, "splits": gpu.EXPECTED_SPLITS,
            "optimizer_steps": {"cas": 22, "generic": 22}, "prepare_exit_before_training": True,
            "learning_accepted": False, "task_generation": False,
            "training_gate": {"private_test_labels_opened": False},
            "fixture": {"source_pins_sha256": self.spec["source_pins_sha256"],
                        "public_loader_sha256": self.spec["public_loader_sha256"]},
            "changed_weights": {family: {"all_loaded_on_cuda": True, "changed_count": 1}
                                for family in ("cas", "generic")},
            "native_receipt": deepcopy(self.native),
            "native_receipt_sha256": q.checks.file_hash(self.native_path)}
        write(self.smoke_path, self.smoke)

    def test_valid_synthetic_gpu_gate_has_one_test_nine_cases_45_arms(self):
        self.gpu_fixture()
        result = q.check_gpu_phase(self.output, job=self.job, spec=self.spec)
        self.assertEqual((result["tests"], result["native_cases"], result["native_arm_verdicts"]), (1, 9, 45))

    def test_embedded_and_stored_native_receipts_must_agree(self):
        self.gpu_fixture()
        changed = deepcopy(self.native)
        changed["cases"] = 8
        write(self.native_path, changed)
        self.smoke["native_receipt_sha256"] = q.checks.file_hash(self.native_path)
        write(self.smoke_path, self.smoke)
        with self.assertRaisesRegex(ValueError, "V7_GPU_NATIVE"):
            q.check_gpu_phase(self.output, job=self.job, spec=self.spec)

    def test_gpu_gate_requires_current_job_source_and_baseline(self):
        for field, value in (("job", "other"), ("source_sha256", {"wrong": "source"}),
                             ("baseline", {"wrong": "baseline"})):
            with self.subTest(field=field):
                self.gpu_fixture()
                self.smoke[field] = value
                write(self.smoke_path, self.smoke)
                with self.assertRaisesRegex(ValueError, "V7_CURRENT_FULL_GPU"):
                    q.check_gpu_phase(self.output, job=self.job, spec=self.spec)

    def test_gpu_gate_rejects_wrong_test_skips_and_wrong_command(self):
        for mutation in ("name", "skip", "command"):
            with self.subTest(mutation=mutation):
                self.gpu_fixture()
                if mutation == "command":
                    path = self.output / "processes/gpu_gate/process_receipt.json"
                    row = q.checks.read(path)
                    row["command"][-1] = "different.xml"
                    write(path, row)
                else:
                    path = self.output / "gpu_test.xml"
                    raw = path.read_text()
                    raw = raw.replace(gpu.GPU_TEST, "wrong_test") if mutation == "name" else raw.replace(
                        "/></testsuite>", "><skipped/></testcase></testsuite>")
                    path.write_text(raw)
                with self.assertRaises(ValueError):
                    q.check_gpu_phase(self.output, job=self.job, spec=self.spec)

    def test_gpu_gate_requires_exactly_one_smoke_and_full_native_counts(self):
        self.gpu_fixture()
        duplicate = self.output / "gpu_tmp/other/gpu_smoke_receipt.json"
        write(duplicate, self.smoke)
        with self.assertRaisesRegex(ValueError, "ONE_CURRENT_GPU"):
            q.check_gpu_phase(self.output, job=self.job, spec=self.spec)

    def test_gpu_gate_rejects_native_case_or_arm_coverage_loss(self):
        for field, value in (("cases", 8), ("arm_verdicts", 44)):
            with self.subTest(field=field):
                self.gpu_fixture()
                self.native[field] = value
                self.smoke["native_receipt"] = deepcopy(self.native)
                write(self.native_path, self.native)
                self.smoke["native_receipt_sha256"] = q.checks.file_hash(self.native_path)
                write(self.smoke_path, self.smoke)
                with self.assertRaisesRegex(ValueError, "FULL_CASE_COVERAGE"):
                    q.check_gpu_phase(self.output, job=self.job, spec=self.spec)

    def harness(self, *, durations=None, fail_phase=None, corrupt_assembly=False,
                drift=None, setup_overhead=0, collection_failure=False, exit_mutation=None):
        """Only scheduling is real here; receipts and gate outcomes are synthetic."""
        spec = deepcopy(self.spec)
        spec.update(max_wall_seconds=6900, gpu_gate_max_seconds=450,
                    dataset_max_seconds=180, native_max_seconds=2700)
        spec["training"]["max_seconds"] = 3300
        self.spec = spec
        events, elapsed, processes = [], [1000.0], {}
        source = {"campaign": "synthetic"}
        experiment = {"profile": "synthetic", "spec_sha256": "3" * 64}
        baseline_calls = [0]
        training_config = SimpleNamespace(max_seconds=3300)
        duration = {"gpu_gate": 10, "dataset": 10, "training": 100, "evaluate": 10}
        duration.update(durations or {})
        self.enterContext(patch.object(q, "experiment_identity", return_value=(spec, experiment)))
        self.enterContext(patch.object(q.profile, "require_execution_ready", return_value=None))
        self.enterContext(patch.object(q.profile, "validate_prototype_spec", return_value=spec))
        self.enterContext(patch.object(q, "configurations", return_value=(None, training_config)))
        self.enterContext(patch.object(q.t, "require_request", return_value=None))
        self.enterContext(patch.object(q, "source_identity", return_value=source))
        if drift == "source":
            self.enterContext(patch.object(q.t, "source_identity", side_effect=lambda:
                {"changed": "source"} if any(e[0] == "process" and e[1] == "evaluate" for e in events)
                else self.source))
        self.enterContext(patch.object(q, "checked_inputs", return_value=frozenset({"synthetic"})))
        self.enterContext(patch.object(q, "prepare_configuration_files", return_value=None))
        self.enterContext(patch.object(gpu, "NATIVE_GATE_READY", True))
        self.enterContext(patch.object(frozen, "_new_output", side_effect=lambda path: Path(path)))
        self.enterContext(patch.object(q, "time", SimpleNamespace(monotonic=lambda: elapsed[0])))
        timers = []
        signals = SimpleNamespace(SIGALRM=14, ITIMER_REAL=0, getsignal=lambda value: "original",
            signal=lambda *args: timers.append(("signal", args)),
            setitimer=lambda *args: timers.append(("timer", args)))
        self.enterContext(patch.object(q, "signal", signals))
        self.enterContext(patch.object(q.c, "write", side_effect=AssertionError("NO_TASK_GENERATION")))
        self.enterContext(patch.object(q.t, "run", side_effect=AssertionError("NO_MODEL_TRAINING")))

        def baseline():
            baseline_calls[0] += 1
            return {"changed": True} if drift == "baseline" and baseline_calls[0] > 1 else self.baseline

        self.enterContext(patch.object(frozen, "_baseline_identity", side_effect=baseline))
        gate_calls = []

        def check_gpu(*args, **kwargs):
            events.append(("gpu_gate_checked",))
            if drift == "gpu" and len([e for e in events if e[0] == "gpu_gate_checked"]) > 1:
                return {"changed": True}
            return {"tests": 1, "native_cases": 9, "native_arm_verdicts": 45}

        self.enterContext(patch.object(q, "check_gpu_phase", side_effect=check_gpu))

        def check_training(*args, **kwargs):
            gate_calls.append((args, kwargs))
            events.append(("training_gate_checked",))
            if drift == "training_gate" and len(gate_calls) > 1:
                return {"changed": True}
            return {"schema": "synthetic_training_gate", "private_test_labels_opened": False}

        self.enterContext(patch.object(q.checks, "check_training", side_effect=check_training))

        def assembly(pid):
            write(self.output / "dataset/manifest.json", {"synthetic": "counts-only"})
            splits = q.expected_splits(spec)
            if corrupt_assembly:
                splits["train"]["tasks"] = 640
            return {"schema": q.SCHEMA, "completed": True, "job": self.job, "pid": pid,
                "actual_splits": splits, "optimizer_steps_per_family": 11200,
                "imported_train_examples": 256,
                "manifest_sha256": q.checks.file_hash(self.output / "dataset/manifest.json"),
                "source_pins_sha256": spec["source_pins_sha256"],
                "public_loader_sha256": spec["public_loader_sha256"],
                "exclusion_inventory_sha256": spec["exclusion_inventory_sha256"],
                "exclusion_count": spec["exclusion_count"], "original_tasks_sha256": spec["original_tasks_sha256"],
                "original_training_only": True, "all_original_graphs_remain_in_fresh_exclusions": True,
                "training_started": False, "neural_execution": False, "source_sha256": source}

        def launch(command, directory, deadline, *, environment):
            name = Path(directory).name
            events.append(("process", name, list(command), deadline, elapsed[0]))
            self.assertLessEqual(deadline, 7870)
            elapsed[0] += duration[name]
            if fail_phase == name:
                raise RuntimeError("SYNTHETIC_PHASE_FAILURE:" + name)
            row = process(Path(directory) / "process_receipt.json", list(command),
                          pid=20000 + len(processes))
            # Ordered historical timestamps for the unchanged exit checker.
            stamp = datetime.now(timezone.utc) - timedelta(seconds=100)
            start = stamp + timedelta(seconds=2 * len(processes))
            row.update(started_utc=start.isoformat(), finished_utc=(start + timedelta(seconds=1)).isoformat())
            if name == "training" and exit_mutation == "same_training_pid":
                row["pid"] = processes["dataset"]["pid"]
            if name == "training" and exit_mutation == "training_before_dataset_exit":
                row.update(started_utc=stamp.isoformat(), finished_utc=(stamp + timedelta(seconds=1)).isoformat())
            write(Path(directory) / "process_receipt.json", row)
            processes[name] = row
            if name == "dataset":
                assembled = assembly(row["pid"])
                if exit_mutation == "wrong_dataset_pid":
                    assembled["pid"] = row["pid"] + 99
                write(self.output / "dataset_assembly_receipt.json", assembled)
                elapsed[0] += setup_overhead
            return row

        self.enterContext(patch.object(frozen, "_run_process", side_effect=launch))

        def native_output(output, count):
            events.append(("native_checked", count))
            return {"cases": count, "arm_verdicts": count * 5}

        self.enterContext(patch.object(q, "check_native_output", side_effect=native_output))

        def collection(output):
            events.append(("collected",))
            if collection_failure:
                raise OSError("SYNTHETIC_COLLECTION_FAILURE")

        self.enterContext(patch.object(frozen, "_final_payload_index", side_effect=collection))
        return events, timers, gate_calls, processes

    def test_phase_sequence_exact_commands_and_actual_counts_before_training(self):
        events, timers, gates, processes = self.harness()
        result = q.run(self.output, job=self.job)
        self.assertTrue(result["completed"])
        calls = [e for e in events if e[0] == "process"]
        self.assertEqual([e[1] for e in calls], ["gpu_gate", "dataset", "training", "evaluate"])
        self.assertEqual(calls[0][2], q.gpu_command(self.output))
        self.assertEqual(calls[1][2], q.dataset_command(self.output, self.job, "dataset"))
        self.assertEqual(calls[2][2], q.training_command(self.output, self.job, self.spec))
        self.assertEqual(calls[3][2], q.dataset_command(self.output, self.job, "evaluate"))
        self.assertEqual(result["actual_splits"], q.expected_splits(self.spec))
        self.assertEqual([result["actual_splits"][name]["tasks"] for name in ("train", "validation", "test")],
                         [896, 96, 72])
        self.assertEqual(len(gates), 2)
        self.assertEqual(gates[0][1]["expected_source"], self.source)
        self.assertEqual(gates[0][1]["expected_baseline"], self.baseline)
        self.assertEqual(gates[0][0][2], self.output / "trainer_input")
        self.assertEqual(events[-1], ("collected",))
        self.assertIn(("timer", (0, 0)), timers)
        self.assertFalse(result["learning_accepted"])
        self.assertFalse(result["release_accepted"])
        self.assertTrue(result["training_attempted"])
        self.assertTrue(result["training_performed"])

    def test_wrong_actual_assembly_count_stops_before_training(self):
        events, _, _, _ = self.harness(corrupt_assembly=True)
        result = q.run(self.output, job=self.job)
        self.assertFalse(result["completed"])
        self.assertIn("ACTUAL_ASSEMBLY_RECEIPT", result["failure"]["message"])
        self.assertEqual([e[1] for e in events if e[0] == "process"], ["gpu_gate", "dataset"])
        self.assertEqual(events[-1], ("collected",))
        self.assertFalse(result["training_attempted"])
        self.assertFalse(result["training_performed"])

    def test_phase_deadlines_fit_registered_time_allocation(self):
        events, _, _, _ = self.harness(durations={"gpu_gate": 450, "dataset": 180}, setup_overhead=150)
        result = q.run(self.output, job=self.job)
        self.assertTrue(result["completed"])
        calls = [e for e in events if e[0] == "process"]
        self.assertEqual([e[3] - e[4] for e in calls], [450, 180, 3315, 2715])

    def test_setup_overhead_past_780_seconds_stops_before_training(self):
        events, _, _, _ = self.harness(durations={"gpu_gate": 450, "dataset": 180}, setup_overhead=151)
        result = q.run(self.output, job=self.job)
        self.assertFalse(result["completed"])
        self.assertIn("INSUFFICIENT_TRAIN_AND_NATIVE", result["failure"]["message"])
        self.assertEqual([e[1] for e in events if e[0] == "process"], ["gpu_gate", "dataset"])

    def test_failed_gpu_process_does_not_start_dataset(self):
        events, _, _, _ = self.harness(fail_phase="gpu_gate")
        result = q.run(self.output, job=self.job)
        self.assertFalse(result["completed"])
        self.assertEqual([e[1] for e in events if e[0] == "process"], ["gpu_gate"])
        self.assertEqual(events[-1], ("collected",))

    def test_failed_dataset_process_does_not_start_training(self):
        events, _, _, _ = self.harness(fail_phase="dataset")
        result = q.run(self.output, job=self.job)
        self.assertFalse(result["completed"])
        self.assertEqual([e[1] for e in events if e[0] == "process"], ["gpu_gate", "dataset"])
        self.assertEqual(events[-1], ("collected",))

    def test_failed_training_process_does_not_start_evaluation(self):
        events, _, gates, _ = self.harness(fail_phase="training")
        result = q.run(self.output, job=self.job)
        self.assertFalse(result["completed"])
        self.assertEqual([e[1] for e in events if e[0] == "process"], ["gpu_gate", "dataset", "training"])
        self.assertEqual(gates, [])
        self.assertEqual(events[-1], ("collected",))
        self.assertTrue((self.output / "campaign_receipt.json").is_file())
        self.assertTrue(result["training_attempted"])
        self.assertIsNone(result["training_performed"])

    def test_wrong_dataset_child_identity_stops_before_training(self):
        events, _, _, _ = self.harness(exit_mutation="wrong_dataset_pid")
        result = q.run(self.output, job=self.job)
        self.assertFalse(result["completed"])
        self.assertIn("DATASET_CHILD_EXIT_REQUIRED", result["failure"]["message"])
        self.assertEqual([e[1] for e in events if e[0] == "process"], ["gpu_gate", "dataset"])

    def test_reused_training_pid_cannot_satisfy_separate_child_exit(self):
        events, _, _, _ = self.harness(exit_mutation="same_training_pid")
        result = q.run(self.output, job=self.job)
        self.assertFalse(result["completed"])
        self.assertIn("DATASET_EXIT_BEFORE_TRAINING", result["failure"]["message"])
        self.assertFalse(any(e[0] == "process" and e[1] == "evaluate" for e in events))

    def test_training_start_cannot_precede_dataset_exit(self):
        events, _, _, _ = self.harness(exit_mutation="training_before_dataset_exit")
        result = q.run(self.output, job=self.job)
        self.assertFalse(result["completed"])
        self.assertIn("DATASET_EXIT_BEFORE_TRAINING", result["failure"]["message"])
        self.assertFalse(any(e[0] == "process" and e[1] == "evaluate" for e in events))

    def test_final_source_drift_stops_completion(self):
        self.harness(drift="source")
        result = q.run(self.output, job=self.job)
        self.assertFalse(result["completed"])
        self.assertIn("SOURCE_IDENTITY_CHANGED", result["failure"]["message"])

    def test_failed_evaluation_process_does_not_read_native_result(self):
        events, _, _, _ = self.harness(fail_phase="evaluate")
        result = q.run(self.output, job=self.job)
        self.assertFalse(result["completed"])
        self.assertFalse(any(e[0] == "native_checked" for e in events))
        self.assertEqual(events[-1], ("collected",))

    def test_final_baseline_drift_blocks_completion(self):
        self.harness(drift="baseline")
        result = q.run(self.output, job=self.job)
        self.assertFalse(result["completed"])
        self.assertIn("BOUND_STATE_CHANGED", result["failure"]["message"])

    def test_training_gate_is_recomputed_before_final_completion(self):
        _, _, gates, _ = self.harness(drift="training_gate")
        result = q.run(self.output, job=self.job)
        self.assertFalse(result["completed"])
        self.assertEqual(len(gates), 2)
        self.assertIn("BOUND_STATE_CHANGED", result["failure"]["message"])

    def test_changed_final_gpu_gate_blocks_completion(self):
        self.harness(drift="gpu")
        result = q.run(self.output, job=self.job)
        self.assertFalse(result["completed"])
        self.assertIn("BOUND_STATE_CHANGED", result["failure"]["message"])

    def test_collection_failure_overrides_otherwise_successful_record(self):
        self.harness(collection_failure=True)
        with self.assertRaisesRegex(OSError, "SYNTHETIC_COLLECTION_FAILURE"):
            q.run(self.output, job=self.job)
        receipt = q.checks.read(self.output / "campaign_receipt.json")
        self.assertFalse(receipt["completed"])
        self.assertEqual(receipt["stage"], "collection")


if __name__ == "__main__":
    unittest.main(verbosity=2)
