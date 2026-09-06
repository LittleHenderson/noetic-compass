"""Pure evaluation plumbing checks; no native or neural execution."""
import ast
from copy import deepcopy
from contextlib import contextmanager
import importlib.abc
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


@contextmanager
def protected_imports():
    class Guard(importlib.abc.MetaPathFinder):
        def find_spec(self, name, path=None, target=None):
            if name.split(".")[0] in {"torch", "casformer", "cas_cjt", "boto3", "tensorflow", "jax", "cupy"}:
                raise AssertionError("NEURAL_PROVIDER_IMPORT:"+name)
    previous = list(sys.meta_path)
    sys.meta_path.insert(0, Guard())
    try:
        yield
    finally:
        sys.meta_path[:] = previous


with protected_imports():
    from cas_meta2.contrast_v7 import native_evaluation as n
    from cas_meta2.contrast_v7 import evaluation as old
    from cas_meta2.contrast_recovery_v6 import core


def cases(count):
    result = []
    for index in range(count):
        arms = {}
        for arm in n.ARMS:
            arms[arm] = {"arm":arm,"case_index":index,"execution_status":"EXECUTED",
                "model_rejection":False,"partial_work":None,
                "verification": {"task_correct":True,"procedure_correct":True,"binding_correct":True,
                    "dependency_correct":True,"actual_output_correct":True,"trace_valid":True,
                    "native_runs":3,"reserved_policy_units":216}}
        result.append({"case_index":index,"task_id":"task-"+str(index),"arms":arms})
    return result


class NativeV7Tests(unittest.TestCase):
    def test_original_72_case_counts_match_frozen_recovery(self):
        data = cases(72)
        original, current = core.aggregate_cases(data), n.aggregate_cases(data, 72)
        for arm in n.ARMS:
            self.assertEqual({k:v for k,v in original[arm].items() if k != "boundary"},
                             {k:v for k,v in current[arm].items() if k != "boundary"})

    def test_diagnostic_nine_cases_keep_all_denominators(self):
        result = n.aggregate_cases(cases(9), 9)
        for arm in n.ARMS:
            self.assertEqual(result[arm]["total"], 9)
            self.assertEqual(result[arm]["task_correct"], 9)
            self.assertEqual(result[arm]["task_accuracy"], 1)
            self.assertEqual(result[arm]["committed_native_runs_lower_bound"], 27)

    def test_incomplete_duplicate_and_wrong_arm_attribution_fail(self):
        for count in (0, 73, True):
            with self.assertRaises(ValueError):
                n.aggregate_cases(cases(9), count)
        for mutation in ("missing","duplicate","wrong_arm"):
            rows = cases(9)
            if mutation == "missing": rows.pop()
            elif mutation == "duplicate": rows[8] = deepcopy(rows[0])
            else: rows[8]["arms"]["rule"]["case_index"] = 0
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                n.aggregate_cases(rows,9)

    def test_post_start_failure_is_incorrect_not_model_rejection(self):
        rows = cases(9)
        failure = rows[4]["arms"]["cas_trained"]
        failure.update(execution_status=core.FAILURE, partial_work={
            "compute_complete":False,"failed_tick_compute":None,
            "committed_native_runs":7,"committed_reserved_policy_units":504})
        failure["verification"] = {"task_correct":False, "procedure_correct":None,"binding_correct":None,
            "dependency_correct":None,"actual_output_correct":False,"trace_valid":False}
        before=deepcopy(rows)
        result=n.aggregate_cases(rows,9)["cas_trained"]
        self.assertEqual(result["total"],9)
        self.assertEqual(result["task_correct"],8)
        self.assertEqual(result["post_admission_runtime_failures"],1)
        self.assertEqual(result["model_rejections"],0)
        self.assertFalse(result["compute_complete"])
        self.assertEqual(result["committed_native_runs_lower_bound"],31)
        self.assertEqual(rows,before)

    def test_grouping_uses_original_task_depths_and_recounts_each_group(self):
        rows=cases(9)
        tasks=[{"task_id":"task-"+str(i),"provenance":{"depth":3 if i%3 != 2 else 4},
                "contrast_side":("same_depth","wording_shift","deeper_calls")[i%3]} for i in range(9)]
        original=deepcopy(rows)
        groups=n.grouped_results(rows,tasks)
        self.assertEqual(groups["depth_3"]["rule"]["total"],6)
        self.assertEqual(groups["depth_4"]["rule"]["total"],3)
        for name in ("same_depth","wording_shift","deeper_calls"):
            self.assertEqual(groups[name]["cas_trained"]["total"],3)
        self.assertEqual(rows,original)

    def test_grouping_rejects_wrong_task_binding(self):
        rows=cases(1)
        with self.assertRaises(ValueError):
            n.grouped_results(rows,[{"task_id":"wrong","provenance":{"depth":3},"contrast_side":"same_depth"}])

    def test_sealing_and_private_opening_function_is_the_unchanged_one(self):
        self.assertIs(n.prepare,old.prepare)

    def test_worker_uses_frozen_per_arm_executor_without_editing_actions(self):
        class Ops:
            expected_source={"source":"pin"}
            expected_baseline={"accepted":"pin"}
            helpers={"helper":"pin"}
            environment={"device":"cuda"}
            def assert_identity(self): pass
        action={"untouched":"saved"}
        task={"task_id":"example"}
        result={"case_index":0}
        with patch.object(n,"_WORKER",Ops()), patch.object(n.core,"evaluate_case",return_value=result) as evaluate,                 patch.object(n.t,"write_new"):
            returned=n.case_worker((0,task,action,"/tmp/probe"))
        self.assertIs(returned,result)
        self.assertEqual(evaluate.call_args.args[1:3],(task,action))
        self.assertIs(evaluate.call_args.args[1],task)
        self.assertIs(evaluate.call_args.args[2],action)

    def test_local_evaluation_refuses_before_data_or_pool(self):
        with patch.object(n.t.sys,"platform","win32"), patch.object(n.checks,"check_training",side_effect=AssertionError("data")):
            with self.assertRaisesRegex(ValueError,"AWS_LINUX"):
                n.evaluate(None,None,None,None,None,expected_command=[],job="unused",
                    expected_manifest_sha256="",expected_loader_sha256="",curriculum_seed=1,
                    curriculum_config=None,excluded=frozenset(),config=n.t.TrainingConfig(),
                    expected_source={},expected_baseline={},pins=None,expected_pins_sha256="")

    def test_identity_changes_stay_fatal_without_native_calls(self):
        operations=n.Operations.__new__(n.Operations)
        operations.expected_source={"source":"one"}
        operations.expected_baseline={"baseline":"one"}
        operations.helpers={"helper":"one"}
        with patch.object(n.t,"source_identity",return_value={"source":"two"}):
            with self.assertRaisesRegex(ValueError,"SOURCE_CHANGED"):
                operations.assert_identity()

    def test_spawn_workers_and_parent_gate_precede_evaluation(self):
        tree=ast.parse((ROOT/"cas_meta2/contrast_v7/native_evaluation.py").read_text())
        function=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=="evaluate")
        calls=[(x.lineno,ast.unparse(x.func),x) for x in ast.walk(function) if isinstance(x,ast.Call)]
        positions={name:min(line for line,call,_ in calls if call==name)
                   for name in ("checks.check_training","prepare","cold_validation","ProcessPoolExecutor")}
        self.assertLess(positions["checks.check_training"],positions["prepare"])
        self.assertLess(positions["prepare"],positions["cold_validation"])
        self.assertLess(positions["cold_validation"],positions["ProcessPoolExecutor"])
        contexts=[node for _,name,node in calls if name=="multiprocessing.get_context"]
        self.assertEqual([node.args[0].value for node in contexts],["spawn"])
        self.assertNotIn("_case_worker",ast.unparse(tree))

    def test_private_parent_guards_are_confined_to_an_exited_child(self):
        tree=ast.parse((ROOT/"cas_meta2/contrast_v7/native_evaluation.py").read_text())
        functions={node.name:node for node in tree.body if isinstance(node,ast.FunctionDef)}
        cold_calls=[(node.lineno,ast.unparse(node.func)) for node in ast.walk(functions["cold_validation"])
                    if isinstance(node,ast.Call)]
        process=next(line for line,name in cold_calls if name=="_run_process")
        exit_check=next(line for line,name in cold_calls if name=="checks.process_exit")
        readback=next(line for line,name in cold_calls if name=="checks.read")
        self.assertLess(process,exit_check)
        self.assertLess(exit_check,readback)
        for name in ("evaluate","cold_validation"):
            self.assertNotIn("parent.validate_bundle",ast.unparse(functions[name]))
        self.assertIn("parent.validate_bundle",ast.unparse(functions["validate_private_child"]))

    def test_import_protection_does_not_leak_between_tests(self):
        before=list(sys.meta_path)
        try:
            with protected_imports():
                raise LookupError("exit")
        except LookupError:
            pass
        self.assertEqual(sys.meta_path,before)


if __name__=="__main__": unittest.main()
