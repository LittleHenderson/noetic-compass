"""Independent pure tests for the narrow v6 post-admission recovery boundary.

Only fake task dictionaries and fake operations are used. No saved campaign
inputs, models, native runtimes, provider clients, or SQLite databases are read.
"""
from __future__ import annotations

import copy
import importlib.abc
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class NoModelsProvidersOrNative(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if (fullname.split(".")[0] in {
                "torch", "tensorflow", "jax", "cupy", "casformer", "cas_cjt",
                "boto3", "botocore", "cas_meta"} or
                fullname == "cas_meta2.native"):
            raise RuntimeError("PURE_RECOVERY_TEST_IMPORT_FORBIDDEN:" + fullname)


_paths_before, _hooks_before = list(sys.path), list(sys.meta_path)
try:
    sys.path.insert(0, str(ROOT))
    sys.meta_path.insert(0, NoModelsProvidersOrNative())
    from cas_meta2.contrast_recovery_v6 import core
finally:
    sys.path[:], sys.meta_path[:] = _paths_before, _hooks_before


class GuardedTestCase(unittest.TestCase):
    def setUp(self):
        original = list(sys.meta_path)
        self.addCleanup(lambda: sys.meta_path.__setitem__(slice(None), original))
        sys.meta_path.insert(0, NoModelsProvidersOrNative())

ARMS = ("cas_untrained", "cas_trained", "generic_untrained",
        "generic_trained", "rule")
ALLOWED_MESSAGE = "repair cannot open without a durable distinct ^6 round trip"


class ExactRuntimeError(RuntimeError):
    pass


class RuntimeErrorSubclass(ExactRuntimeError):
    pass


def fake_task():
    return {
        "task_id": "fake-task-only",
        "public": {"problem": "fake public problem", "observations": [
            {"slot": "fake-observation", "values": [1, 2, 3]}]},
        "target": {"private_only": "MUST_NOT_REACH_CANDIDATE",
                   "program": {"gold": "private"}, "binding": "private-binding"},
        "provenance": {"depth": 3},
    }


def fake_actions():
    return {arm: {"tag": arm, "program": {"nested": ["original"]},
                  "binding": "fake-observation"} for arm in ARMS}


def fake_verdict(correct=True):
    return {
        "task_correct": correct, "procedure_correct": correct,
        "binding_correct": correct, "dependency_correct": correct,
        "actual_output_correct": correct, "trace_valid": correct,
        "native_runs": 2, "reserved_policy_units": 7,
        "repair_required": False, "repair_success": None,
        "supplied_verifier_marker": "CHECKED_BY_FAKE_VERIFIER",
    }


class FakeOps:
    runtime_contract_error = ExactRuntimeError

    def __init__(self):
        self.events = []
        self.errors = {}
        self.reject = {}
        self.correct = {arm: True for arm in ARMS}
        self.execute_mutates = False
        self.admission_mutates = False
        self.reference_result = {"status": "EXECUTED", "reference": True}
        self.reference_verdict = fake_verdict()
        self.execution_status = "EXECUTED"
        self.public_seen = []
        self.action_seen = []
        self.partial_result = {
            "committed_native_runs": 1,
            "committed_reserved_policy_units": 3,
            "compute_complete": False,
            "failed_tick_compute": None,
        }

    def fail_if_requested(self, stage, arm=None):
        error = self.errors.get((stage, arm), self.errors.get(stage))
        if error is not None:
            raise error

    def assert_identity(self):
        self.events.append(("identity", None))
        self.fail_if_requested("identity")

    def reference_task(self, task, path):
        self.events.append(("reference", None))
        self.fail_if_requested("reference")
        return copy.deepcopy(self.reference_result)

    def verify_reference_task(self, task, result):
        self.events.append(("verify_reference", None))
        self.fail_if_requested("verify_reference")
        return copy.deepcopy(self.reference_verdict)

    def admission_error(self, action, public):
        arm = action["tag"]
        self.events.append(("admission", arm))
        self.fail_if_requested("admission", arm)
        if self.admission_mutates:
            action["program"]["nested"].append("admission mutation")
            public["observations"][0]["values"].append(99)
        return self.reject.get(arm)

    def execute_task(self, public, action, path):
        arm = action["tag"]
        self.events.append(("execute", arm))
        self.public_seen.append(copy.deepcopy(public))
        self.action_seen.append(copy.deepcopy(action))
        if self.execute_mutates:
            action["program"]["nested"].append("execution mutation")
            public["observations"][0]["values"].append(88)
        self.fail_if_requested("execute", arm)
        return {"status": self.execution_status, "reference": False,
                "selected_action": copy.deepcopy(action), "fake_arm": arm}

    def verify_task(self, task, result, reference):
        arm = result.get("fake_arm", result.get("action", {}).get("tag"))
        self.events.append(("verify", arm))
        self.fail_if_requested("verify", arm)
        return fake_verdict(self.correct.get(arm, False))

    def partial_work(self, path):
        self.events.append(("partial", Path(path).parent.name))
        self.fail_if_requested("partial")
        return copy.deepcopy(self.partial_result)


class RecoveryCoreTests(GuardedTestCase):
    def setUp(self):
        super().setUp()
        self.temp = tempfile.TemporaryDirectory(prefix="recovery-core-test-",
                                                dir=ROOT / "records")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.assertEqual(self.root.parent, (ROOT / "records").resolve())
        self.task = fake_task()
        self.actions = fake_actions()
        self.ops = FakeOps()

    def run_case(self, index=0, name="case"):
        return core.evaluate_case(index, self.task, self.actions,
                                  self.root / name, self.ops)

    def test_five_arms_are_the_declared_comparison(self):
        self.assertEqual(tuple(core.ARMS), ARMS)

    def test_successful_candidate_uses_supplied_verifier(self):
        row = self.run_case()
        self.assertEqual(set(row["arms"]), set(ARMS))
        self.assertEqual([arm for event, arm in self.ops.events if event == "verify"], list(ARMS))
        for arm in ARMS:
            with self.subTest(arm=arm):
                self.assertTrue(row["arms"][arm]["verification"]["task_correct"])
                self.assertEqual(row["arms"][arm]["verification"]["supplied_verifier_marker"],
                                 "CHECKED_BY_FAKE_VERIFIER")

    def test_candidate_receives_public_data_not_private_gold(self):
        self.run_case()
        self.assertEqual(len(self.ops.public_seen), len(ARMS))
        for public in self.ops.public_seen:
            self.assertEqual(public, self.task["public"])
            self.assertNotIn("MUST_NOT_REACH_CANDIDATE", json.dumps(public))

    def test_execution_cannot_mutate_callers_or_other_arms(self):
        task_before, actions_before = copy.deepcopy(self.task), copy.deepcopy(self.actions)
        self.ops.execute_mutates = True
        row = self.run_case()
        self.assertEqual(self.task, task_before)
        self.assertEqual(self.actions, actions_before)
        self.assertEqual(self.ops.public_seen, [task_before["public"]] * len(ARMS))
        for arm, received in zip(ARMS, self.ops.action_seen, strict=True):
            self.assertEqual(received, actions_before[arm])
            self.assertEqual(row["arms"][arm]["action"], actions_before[arm])

    def test_reference_exact_runtime_exception_is_fatal(self):
        error = ExactRuntimeError(ALLOWED_MESSAGE)
        self.ops.errors["reference"] = error
        with self.assertRaises(ExactRuntimeError) as seen:
            self.run_case()
        self.assertIs(seen.exception, error)
        self.assertFalse(any(event == "execute" for event, _ in self.ops.events))

    def test_bad_reference_verdict_is_fatal_before_candidates(self):
        self.ops.reference_verdict["task_correct"] = False
        with self.assertRaises(ValueError):
            self.run_case()
        self.assertFalse(any(event == "execute" for event, _ in self.ops.events))

    def test_bad_reference_status_is_fatal_before_candidates(self):
        self.ops.reference_result["status"] = "REJECTED"
        with self.assertRaises(ValueError):
            self.run_case()
        self.assertFalse(any(event == "execute" for event, _ in self.ops.events))

    def test_exact_exception_from_admission_is_not_contained(self):
        error = ExactRuntimeError(ALLOWED_MESSAGE)
        self.ops.errors[("admission", ARMS[0])] = error
        with self.assertRaises(ExactRuntimeError) as seen:
            self.run_case()
        self.assertIs(seen.exception, error)
        self.assertFalse(any(event == "execute" for event, _ in self.ops.events))

    def test_exact_exception_from_verifier_is_not_contained(self):
        error = ExactRuntimeError(ALLOWED_MESSAGE)
        self.ops.errors[("verify", ARMS[0])] = error
        with self.assertRaises(ExactRuntimeError) as seen:
            self.run_case()
        self.assertIs(seen.exception, error)
        self.assertEqual([arm for event, arm in self.ops.events if event == "execute"], [ARMS[0]])



    def test_exact_candidate_error_is_contained_and_other_arms_continue(self):
        self.ops.errors[("execute", ARMS[0])] = ExactRuntimeError(ALLOWED_MESSAGE)
        row = self.run_case()
        bad = row["arms"][ARMS[0]]
        self.assertEqual(bad["execution_status"], "POST_ADMISSION_RUNTIME_FAILURE")
        self.assertIs(bad["model_rejection"], False)
        self.assertIs(bad["verification"]["task_correct"], False)
        self.assertIs(bad["verification"]["actual_output_correct"], False)
        self.assertIs(bad["verification"]["trace_valid"], False)
        self.assertIs(bad["verification"]["repair_success"], False)
        self.assertIsNone(bad["verification"]["procedure_correct"])
        self.assertIsNone(bad["verification"]["binding_correct"])
        self.assertIsNone(bad["verification"]["dependency_correct"])
        self.assertEqual(bad["failure"], {
            "type": "ExactRuntimeError", "module": ExactRuntimeError.__module__,
            "message": ALLOWED_MESSAGE})
        self.assertEqual(bad["partial_work"], self.ops.partial_result)
        self.assertEqual([arm for event, arm in self.ops.events if event == "execute"], list(ARMS))
        self.assertEqual([arm for event, arm in self.ops.events if event == "verify"], list(ARMS[1:]))
        for arm in ARMS[1:]:
            self.assertTrue(row["arms"][arm]["verification"]["task_correct"])

    def test_same_boundary_applies_to_all_five_arms(self):
        for arm in ARMS:
            with self.subTest(arm=arm):
                self.ops = FakeOps()
                self.ops.errors[("execute", arm)] = ExactRuntimeError(ALLOWED_MESSAGE)
                row = self.run_case(name=arm)
                self.assertEqual(len(row["arms"]), 5)
                self.assertEqual(row["arms"][arm]["execution_status"], "POST_ADMISSION_RUNTIME_FAILURE")
                self.assertNotIn(("verify", arm), self.ops.events)

    def test_all_five_runtime_failures_remain_five_attempts(self):
        self.ops.errors["execute"] = ExactRuntimeError(ALLOWED_MESSAGE)
        row = self.run_case()
        self.assertEqual(len(row["arms"]), 5)
        self.assertEqual([arm for event, arm in self.ops.events if event == "execute"], list(ARMS))
        self.assertFalse(any(event == "verify" for event, _ in self.ops.events))
        self.assertEqual(sum(event == "partial" for event, _ in self.ops.events), 5)
        self.assertTrue(all(not item["verification"]["task_correct"] for item in row["arms"].values()))

    def test_runtime_subclasses_wrong_classes_and_wrong_messages_are_fatal(self):
        errors = (
            RuntimeErrorSubclass(ALLOWED_MESSAGE), RuntimeError(ALLOWED_MESSAGE),
            ValueError(ALLOWED_MESSAGE), ExactRuntimeError(ALLOWED_MESSAGE + "."),
            ExactRuntimeError("different failure"), MemoryError("out of memory"),
            SystemExit("fatal termination"),
        )
        for index, error in enumerate(errors):
            with self.subTest(type=type(error).__name__, message=str(error)):
                self.ops = FakeOps()
                self.ops.errors[("execute", ARMS[0])] = error
                with self.assertRaises(type(error)) as seen:
                    self.run_case(name="fatal-" + str(index))
                self.assertIs(seen.exception, error)
                self.assertFalse(any(event in ("partial", "verify") for event, _ in self.ops.events))

    def test_reference_verifier_exact_runtime_exception_is_fatal(self):
        error = ExactRuntimeError(ALLOWED_MESSAGE)
        self.ops.errors["verify_reference"] = error
        with self.assertRaises(ExactRuntimeError) as seen:
            self.run_case()
        self.assertIs(seen.exception, error)
        self.assertFalse(any(event == "execute" for event, _ in self.ops.events))

    def test_initial_identity_error_is_fatal(self):
        error = ExactRuntimeError(ALLOWED_MESSAGE)
        self.ops.errors["identity"] = error
        with self.assertRaises(ExactRuntimeError) as seen:
            self.run_case()
        self.assertIs(seen.exception, error)
        self.assertFalse(any(event == "reference" for event, _ in self.ops.events))

    def test_identity_error_after_failed_execution_is_fatal(self):
        failure = ExactRuntimeError(ALLOWED_MESSAGE)
        identity_error = RuntimeError("identity bytes changed")
        self.ops.errors[("execute", ARMS[0])] = failure
        def identity():
            if any(event == "execute" for event, _ in self.ops.events):
                raise identity_error
        self.ops.assert_identity = identity
        with self.assertRaises(RuntimeError) as seen:
            self.run_case()
        self.assertIs(seen.exception, identity_error)
        self.assertFalse(any(event == "partial" for event, _ in self.ops.events))

    def test_partial_work_error_is_fatal_not_a_zero_compute_result(self):
        error = RuntimeError("partial store unreadable")
        self.ops.errors["execute"] = ExactRuntimeError(ALLOWED_MESSAGE)
        self.ops.errors["partial"] = error
        with self.assertRaises(RuntimeError) as seen:
            self.run_case()
        self.assertIs(seen.exception, error)
        self.assertFalse((self.root / "case/case_receipt.json").exists())

    def test_partial_work_shape_cannot_claim_complete_or_negative_compute(self):
        changes = (
            {"committed_native_runs": -1}, {"committed_native_runs": True},
            {"committed_reserved_policy_units": -1},
            {"committed_reserved_policy_units": 1.5},
            {"compute_complete": True}, {"failed_tick_compute": 0},
        )
        for index, change in enumerate(changes):
            with self.subTest(change=change):
                self.ops = FakeOps()
                self.ops.errors["execute"] = ExactRuntimeError(ALLOWED_MESSAGE)
                self.ops.partial_result.update(change)
                with self.assertRaisesRegex(ValueError, "RECOVERY_PARTIAL_WORK_INVALID"):
                    self.run_case(name="partial-" + str(index))

    def test_unrecognized_native_return_is_fatal(self):
        self.ops.execution_status = "REJECTED"
        with self.assertRaisesRegex(ValueError, "RECOVERY_UNRECOGNIZED_NATIVE_RESULT"):
            self.run_case()
        self.assertFalse(any(event == "verify" for event, _ in self.ops.events))

    def test_admission_rejection_is_distinct_and_still_uses_verifier(self):
        self.ops.reject[ARMS[0]] = {"code": "FAKE_ADMISSION_REJECTION"}
        self.ops.correct[ARMS[0]] = False
        row = self.run_case()["arms"][ARMS[0]]
        self.assertEqual(row["execution_status"], "REJECTED")
        self.assertIs(row["model_rejection"], True)
        self.assertIs(row["verification"]["task_correct"], False)
        self.assertIsNone(row["partial_work"])
        self.assertNotIn(("execute", ARMS[0]), self.ops.events)
        self.assertIn(("verify", ARMS[0]), self.ops.events)

    def test_admission_rejection_cannot_be_reported_correct(self):
        self.ops.reject[ARMS[0]] = {"code": "FAKE_ADMISSION_REJECTION"}
        with self.assertRaisesRegex(ValueError, "RECOVERY_REJECTION_REPORTED_CORRECT"):
            self.run_case()

    def test_admission_callback_cannot_mutate_inputs_or_execution(self):
        task_before, actions_before = copy.deepcopy(self.task), copy.deepcopy(self.actions)
        self.ops.admission_mutates = True
        self.run_case()
        self.assertEqual(self.task, task_before)
        self.assertEqual(self.actions, actions_before)
        self.assertEqual(self.ops.public_seen, [task_before["public"]] * 5)
        self.assertEqual(self.ops.action_seen, list(actions_before.values()))

    def test_reference_and_verifier_callbacks_cannot_mutate_inputs(self):
        task_before, actions_before = copy.deepcopy(self.task), copy.deepcopy(self.actions)
        original_reference = self.ops.reference_task
        original_verify_reference = self.ops.verify_reference_task
        original_verify = self.ops.verify_task
        def reference(task, path):
            result = original_reference(task, path)
            task["target"]["program"]["gold"] = "mutated"
            return result
        def verify_reference(task, result):
            verdict = original_verify_reference(task, result)
            task["target"]["program"]["gold"] = "mutated again"
            result["status"] = "mutated reference"
            return verdict
        def verify(task, result, reference):
            verdict = original_verify(task, result, reference)
            task["public"]["observations"][0]["values"].append(444)
            result["selected_action"]["program"]["nested"].append("verifier mutation")
            reference["status"] = "mutated by candidate verifier"
            return verdict
        self.ops.reference_task = reference
        self.ops.verify_reference_task = verify_reference
        self.ops.verify_task = verify
        row = self.run_case()
        self.assertEqual(self.task, task_before)
        self.assertEqual(self.actions, actions_before)
        self.assertTrue(all(item["verification"]["task_correct"] for item in row["arms"].values()))

    def test_wrong_verifier_result_is_not_overridden_by_executed_status(self):
        self.ops.correct[ARMS[0]] = False
        row = self.run_case()["arms"][ARMS[0]]
        self.assertEqual(row["execution_status"], "EXECUTED")
        self.assertIs(row["verification"]["task_correct"], False)

    def test_case_writes_readable_new_receipts_and_refuses_overwrite(self):
        row = self.run_case()
        self.assertEqual(json.loads((self.root / "case/case_receipt.json").read_bytes()), row)
        for arm in ARMS:
            self.assertEqual(json.loads((self.root / "case" / arm / "case_receipt.json").read_bytes()),
                             row["arms"][arm])
        with self.assertRaisesRegex(ValueError, "RECOVERY_NEW_CASE_REQUIRED"):
            self.run_case()
        self.assertEqual(json.loads((self.root / "case/case_receipt.json").read_bytes()), row)

    def test_missing_extra_and_boolean_case_inputs_are_rejected(self):
        for index, invalid in enumerate((-1, 72, True, 0.0, None)):
            with self.subTest(case_index=invalid):
                with self.assertRaisesRegex(ValueError, "RECOVERY_CASE_INDEX"):
                    self.run_case(index=invalid, name="index-" + str(index))
        for name in ("missing", "extra"):
            with self.subTest(arms=name):
                self.actions = fake_actions()
                if name == "missing":
                    self.actions.pop(ARMS[-1])
                else:
                    self.actions["extra"] = copy.deepcopy(self.actions[ARMS[0]])
                with self.assertRaisesRegex(ValueError, "RECOVERY_ARM_COVERAGE"):
                    self.run_case(name=name)

    def test_module_imports_remain_pure(self):
        # Other collected tests may legitimately preload the pure native
        # adapter. Check this module's imports in a genuinely fresh process.
        probe = r'''
import importlib.abc, json, pathlib, sys
root = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root))
forbidden = {'torch','casformer','cas_cjt','tensorflow','jax','cupy','boto3','botocore','cas_meta'}
def blocked(name):
    return name.split('.')[0] in forbidden or name in (
        'cas_meta2.native', 'cas_meta2.contrast_recovery_v6.runtime')
attempts = []
class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if blocked(fullname):
            attempts.append(fullname)
            raise AssertionError('FRESH_CORE_FORBIDDEN_IMPORT:' + fullname)
sys.meta_path.insert(0, Guard())
def audit(event, args):
    if event in ('subprocess.Popen', 'os.system', 'socket.connect', 'socket.bind'):
        raise AssertionError('FRESH_IMPORT_SIDE_EFFECT_FORBIDDEN:' + event)
sys.addaudithook(audit)
before = set(sys.modules)
before_forbidden = sorted(name for name in before if blocked(name))
assert before_forbidden == []
hooks, paths = list(sys.meta_path), list(sys.path)
from cas_meta2.contrast_recovery_v6 import core
after = set(sys.modules)
assert pathlib.Path(core.__file__).resolve() == root/'cas_meta2/contrast_recovery_v6/core.py'
assert list(sys.meta_path) == hooks and list(sys.path) == paths
after_forbidden = sorted(name for name in after if blocked(name))
assert after_forbidden == [] and attempts == []
print(json.dumps({'fresh_isolated_process': True, 'site_disabled': bool(sys.flags.no_site),
    'before_forbidden': before_forbidden, 'after_forbidden': after_forbidden,
    'attempted_forbidden_imports': attempts, 'new_modules': sorted(after-before),
    'source_file': str(pathlib.Path(core.__file__).resolve()), 'hook_and_path_unchanged': True}))
'''
        command = [sys.executable, '-I', '-S', '-B', '-c', probe, str(ROOT)]
        child = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(child.returncode, 0, child.stdout + child.stderr)
        footprint = json.loads(child.stdout)
        self.assertTrue(footprint['fresh_isolated_process'] and footprint['site_disabled'])
        self.assertEqual(footprint['before_forbidden'], [])
        self.assertEqual(footprint['after_forbidden'], [])
        self.assertEqual(footprint['attempted_forbidden_imports'], [])
        self.assertIn('cas_meta2.contrast_recovery_v6.core', footprint['new_modules'])
        print('CORE_IMPORT_FOOTPRINT ' + child.stdout.strip())


def aggregation_cases():
    """Seventy-two fake receipt rows, not generated or saved problem graphs."""
    cases = []
    for index in range(72):
        rows = {}
        for arm in ARMS:
            rows[arm] = {"case_index": index, "arm": arm, "action": {"fake": arm},
                         "execution_status": "EXECUTED", "failure": None,
                         "verification": fake_verdict(), "model_rejection": False,
                         "wall_seconds": 0.0, "evidence_directory": "FAKE_ONLY",
                         "partial_work": None}
        cases.append({"case_index": index, "task_id": "fake-" + str(index),
                      "arms": rows, "reference_verification": fake_verdict(),
                      "reference_wall_seconds": 0.0, "case_wall_seconds": 0.0})
    return cases


def set_fake_runtime_failure(row):
    row.update(execution_status="POST_ADMISSION_RUNTIME_FAILURE",
               model_rejection=False, failure={"type": "ExactRuntimeError",
                                               "message": ALLOWED_MESSAGE})
    row["verification"] = {
        "task_correct": False, "procedure_correct": None, "binding_correct": None,
        "dependency_correct": None, "actual_output_correct": False, "trace_valid": False,
        "repair_required": True, "repair_success": False,
        "failure": "POST_ADMISSION_RUNTIME_FAILURE"}
    row["partial_work"] = {"committed_native_runs": 1,
                           "committed_reserved_policy_units": 3,
                           "compute_complete": False, "failed_tick_compute": None}


class RecoveryAggregationTests(GuardedTestCase):
    def test_all_72_cases_and_five_arms_counted(self):
        result = core.aggregate_cases(aggregation_cases())
        self.assertEqual(set(result), set(ARMS))
        for arm in ARMS:
            with self.subTest(arm=arm):
                self.assertEqual(result[arm]["total"], 72)
                self.assertEqual(result[arm]["task_correct"], 72)
                self.assertEqual(result[arm]["task_accuracy"], 1.0)
                self.assertEqual(result[arm]["native_executed"], 72)
                self.assertEqual(result[arm]["committed_native_runs_lower_bound"], 144)
                self.assertEqual(result[arm]["reserved_policy_units_lower_bound"], 504)
                self.assertIs(result[arm]["compute_complete"], True)
                self.assertIs(result[arm]["all_cases_in_denominator"], True)

    def test_runtime_failure_is_not_dropped_or_called_model_rejection(self):
        cases = aggregation_cases()
        set_fake_runtime_failure(cases[0]["arms"][ARMS[0]])
        result = core.aggregate_cases(cases)
        arm = result[ARMS[0]]
        self.assertEqual(arm["total"], 72)
        self.assertEqual(arm["task_correct"], 71)
        self.assertEqual(arm["task_accuracy"], 71 / 72)
        self.assertEqual(arm["post_admission_runtime_failures"], 1)
        self.assertEqual(arm["model_rejections"], 0)
        self.assertEqual(arm["native_executed"], 71)
        self.assertEqual(arm["committed_native_runs_lower_bound"], 143)
        self.assertEqual(arm["reserved_policy_units_lower_bound"], 500)
        self.assertIs(arm["compute_complete"], False)
        self.assertTrue(all(result[name]["compute_complete"] for name in ARMS[1:]))

    def test_all_runtime_failures_are_72_failed_attempts_per_arm(self):
        cases = aggregation_cases()
        for case in cases:
            for row in case["arms"].values():
                set_fake_runtime_failure(row)
        result = core.aggregate_cases(cases)
        for arm in ARMS:
            self.assertEqual(result[arm]["total"], 72)
            self.assertEqual(result[arm]["task_correct"], 0)
            self.assertEqual(result[arm]["post_admission_runtime_failures"], 72)
            self.assertEqual(result[arm]["model_rejections"], 0)
            self.assertEqual(result[arm]["committed_native_runs_lower_bound"], 72)
            self.assertIs(result[arm]["compute_complete"], False)

    def test_denominator_cannot_shrink_expand_or_use_boolean(self):
        for denominator in (0, 1, 71, 73, True, 72.0, None):
            with self.subTest(denominator=denominator):
                with self.assertRaisesRegex(ValueError, "RECOVERY_FIXED_DENOMINATOR"):
                    core.aggregate_cases(aggregation_cases(), total_expected=denominator)

    def test_missing_extra_duplicate_and_wrong_index_cases_are_rejected(self):
        for mutation in ("missing", "extra", "duplicate", "wrong_index", "boolean_index"):
            with self.subTest(mutation=mutation):
                cases = aggregation_cases()
                if mutation == "missing":
                    cases.pop()
                elif mutation == "extra":
                    cases.append(copy.deepcopy(cases[0]))
                elif mutation == "duplicate":
                    cases[-1] = copy.deepcopy(cases[0])
                elif mutation == "wrong_index":
                    cases[-1]["case_index"] = 72
                else:
                    cases[0]["case_index"] = False
                with self.assertRaisesRegex(ValueError, "RECOVERY_CASE_COVERAGE"):
                    core.aggregate_cases(cases)

    def test_each_case_requires_all_five_exact_arm_names(self):
        for mutation in ("missing", "extra"):
            with self.subTest(mutation=mutation):
                cases = aggregation_cases()
                if mutation == "missing":
                    cases[0]["arms"].pop(ARMS[-1])
                else:
                    cases[0]["arms"]["extra"] = copy.deepcopy(cases[0]["arms"][ARMS[0]])
                with self.assertRaisesRegex(ValueError, "RECOVERY_ARM_COVERAGE"):
                    core.aggregate_cases(cases)

    def test_arm_rows_cannot_be_misattributed(self):
        for key, value in (("arm", ARMS[1]), ("case_index", 1), ("case_index", False)):
            with self.subTest(key=key, value=value):
                cases = aggregation_cases()
                cases[0]["arms"][ARMS[0]][key] = value
                with self.assertRaisesRegex(ValueError, "RECOVERY_ARM_ATTRIBUTION"):
                    core.aggregate_cases(cases)

    def test_unknown_status_and_wrong_rejection_flags_are_rejected(self):
        for status, flag in (("UNKNOWN", False), ("EXECUTED", True),
                             ("REJECTED", False), ("POST_ADMISSION_RUNTIME_FAILURE", True)):
            with self.subTest(status=status, flag=flag):
                cases = aggregation_cases()
                row = cases[0]["arms"][ARMS[0]]
                row.update(execution_status=status, model_rejection=flag)
                with self.assertRaises(ValueError):
                    core.aggregate_cases(cases)

    def test_runtime_failure_cannot_claim_success_or_omit_partial_work(self):
        for change in ("success", "missing_partial"):
            with self.subTest(change=change):
                cases = aggregation_cases()
                row = cases[0]["arms"][ARMS[0]]
                set_fake_runtime_failure(row)
                if change == "success":
                    row["verification"]["task_correct"] = True
                else:
                    row["partial_work"] = None
                with self.assertRaises(ValueError):
                    core.aggregate_cases(cases)

    def test_aggregate_rechecks_partial_work_counts_and_unknown_compute(self):
        for change in ({"committed_native_runs": -1}, {"committed_native_runs": True},
                       {"committed_reserved_policy_units": -1},
                       {"compute_complete": True}, {"failed_tick_compute": 0}):
            with self.subTest(change=change):
                cases = aggregation_cases()
                row = cases[0]["arms"][ARMS[0]]
                set_fake_runtime_failure(row)
                row["partial_work"].update(change)
                with self.assertRaises(ValueError):
                    core.aggregate_cases(cases)


if __name__ == "__main__":
    unittest.main(verbosity=2)
