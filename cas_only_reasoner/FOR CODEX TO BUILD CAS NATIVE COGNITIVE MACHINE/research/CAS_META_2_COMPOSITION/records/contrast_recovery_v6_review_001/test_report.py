"""Synthetic, in-memory report checks; no current task or packet reads."""
from copy import deepcopy
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest

spec = importlib.util.spec_from_file_location("pure_recovery_report", Path(__file__).with_name("report.py"))
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)


def require(value, message):
    if not value:
        raise ValueError(message)


C = SimpleNamespace(require=require, ARMS=report.ARM_NAMES, FIELDS=report.METRIC_FIELDS,
                    FAILURE="POST_ADMISSION_RUNTIME_FAILURE")


class Differences:
    def __init__(self):
        self.normalizations = 0
        self.comparisons = 0

    def normalize(self, events):
        self.normalizations += 1
        return deepcopy(events)

    def first_difference(self, actual, expected):
        self.comparisons += 1
        if actual == expected:
            return None
        return {"categories": ["input_binding_difference"],
                "candidate": deepcopy(actual), "successful_rule": deepcopy(expected)}


def fixtures():
    target = {"binding": 0, "program": {"procedures": {
        "entry": {"steps": [{"kind": "CALL", "input": "arg", "procedure": "child"}]},
        "child": {"steps": [{"kind": "RUN", "input": "arg", "cjt_id": "CJT-A"}]}}}}
    native = {"cjt_id": "CJT-A", "input_node": {"value": 1},
              "input_sha256": "a" * 64, "output_sha256": "b" * 64}
    tasks, predictions, cases = [], [], []
    for i in range(72):
        side = ("same_depth", "wording_shift", "deeper_calls")[i % 3]
        task = {"task_id": "synthetic-" + str(i), "public": {"fixture_only": True},
                "target": deepcopy(target), "contrast_side": side,
                "provenance": {"depth": 4 if side == "deeper_calls" else 3,
                               "evaluation_group": "test"}}
        prediction = {"task_id": task["task_id"], "actions": {a: deepcopy(target) for a in C.ARMS}}
        arms = {}
        for arm in C.ARMS:
            arms[arm] = {"case_index": i, "arm": arm, "action": deepcopy(target),
                "execution_status": "EXECUTED", "model_rejection": False, "partial_work": None,
                "verification": {**dict.fromkeys(C.FIELDS, True), "repair_required": False,
                                 "repair_success": None, "native_runs": 1, "reserved_policy_units": 72},
                "rows": [deepcopy(native)], "composition_events": [{"kind": "RUN", "input": "arg"}],
                "complete_trace": True, "return_node": {"value": 2}}
        tasks.append(task)
        predictions.append(prediction)
        cases.append({"case_index": i, "task_id": task["task_id"], "arms": arms,
                      "reference": {"rows": [deepcopy(native)]},
                      "reference_verification": {"task_correct": True}})
    return tasks, predictions, cases


def fail_row(cases, index=0, arm="cas_trained"):
    row = cases[index]["arms"][arm]
    row.update(execution_status=C.FAILURE, complete_trace=False, composition_events=None)
    row["verification"] = {"task_correct": False, "procedure_correct": None,
        "binding_correct": None, "dependency_correct": None, "actual_output_correct": False,
        "trace_valid": False, "repair_required": True, "repair_success": False}
    row["partial_work"] = {"committed_native_runs": len(row["rows"]),
        "committed_reserved_policy_units": 72, "compute_complete": False,
        "failed_tick_compute": None, "rows": deepcopy(row["rows"])}
    row["next_sealed_run"] = {"cjt_id": "CJT-A", "input": "arg"}
    return row


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.tasks, self.predictions, self.cases = fixtures()
        self.differences = Differences()

    def build(self):
        return report.build_report(self.tasks, self.predictions, self.cases, self.differences, C)

    def test_complete_72_by_five_and_exact_depth_denominators(self):
        result = self.build()
        self.assertEqual((result["case_count"], result["arm_rows"]), (72, 360))
        self.assertEqual(len(result["cases"]), 360)
        for arm in C.ARMS:
            self.assertEqual(result["summaries"]["all"][arm]["correct"], 72)
            self.assertEqual(result["summaries"]["depth_3"][arm]["attempted"], 48)
            self.assertEqual(result["summaries"]["depth_4"][arm]["attempted"], 24)
            self.assertEqual(result["summaries"]["same_depth"][arm]["attempted"], 24)
        self.assertEqual(result["before_after"]["all"]["cas"]["correct_change"], 0)

    def test_missing_task_prediction_or_case_rejected(self):
        for name in ("tasks", "predictions", "cases"):
            with self.subTest(name=name):
                saved = getattr(self, name)
                setattr(self, name, saved[:-1])
                with self.assertRaisesRegex(ValueError, "EXACT_72"):
                    self.build()
                setattr(self, name, saved)

    def test_duplicate_case_and_boolean_index_rejected(self):
        for value in (1, False):
            with self.subTest(value=value):
                self.cases[0]["case_index"] = value
                with self.assertRaisesRegex(ValueError, "CASE_MAPPING"):
                    self.build()

    def test_missing_arm_rejected(self):
        del self.cases[0]["arms"]["generic_trained"]
        with self.assertRaisesRegex(ValueError, "CASE_MAPPING"):
            self.build()

    def test_changed_sealed_action_rejected(self):
        self.cases[0]["arms"]["cas_trained"]["action"]["binding"] = 1
        with self.assertRaisesRegex(ValueError, "ARM_OR_ACTION"):
            self.build()

    def test_wrong_rule_or_reference_rejected(self):
        for which in ("rule", "reference"):
            with self.subTest(which=which):
                self.tasks, self.predictions, self.cases = fixtures()
                verdict = (self.cases[0]["arms"]["rule"]["verification"] if which == "rule"
                           else self.cases[0]["reference_verification"])
                verdict["task_correct"] = False
                with self.assertRaisesRegex(ValueError, "CORRECT_RULE"):
                    self.build()

    def test_failed_task_stays_in_denominator_and_nulls_stay_unknown(self):
        fail_row(self.cases)
        result = self.build()
        summary = result["summaries"]["all"]["cas_trained"]
        self.assertEqual((summary["attempted"], summary["correct"]), (72, 71))
        metric = summary["verifier_metrics"]["binding_correct"]
        self.assertEqual(metric, {"correct": 71, "incorrect": 0, "unknown": 1, "known": 71, "attempted": 72})
        self.assertFalse(summary["compute_complete"])
        self.assertEqual(summary["post_admission_runtime_failures"], 1)
        self.assertEqual(result["before_after"]["all"]["cas"]["correct_change"], -1)
        self.assertEqual(summary["repair"], {"required": 1, "success": 0, "success_unknown": 0})

    def test_partial_matching_short_prefix_has_no_guessed_early_end(self):
        row = fail_row(self.cases)
        row["rows"] = []
        row["partial_work"].update(rows=[], committed_native_runs=0, committed_reserved_policy_units=0)
        result = self.build()
        found = result["cases"][1]
        self.assertIsNone(found["first_committed_run_disagreement"])
        self.assertIsNone(found["committed_prefix"]["failed_tick_cause"])
        self.assertNotIn("first_observed_difference", found)
        self.assertEqual(self.differences.comparisons, 0)
        self.assertNotIn("trajectory_ended_early", repr(result))

    def test_partial_run_disagreement_is_separate_from_complete_trajectory(self):
        row = fail_row(self.cases)
        row["rows"][0]["input_sha256"] = "c" * 64
        row["partial_work"]["rows"] = deepcopy(row["rows"])
        result = self.build()
        found = result["cases"][1]["first_committed_run_disagreement"]
        self.assertEqual(found["committed_run_index"], 0)
        self.assertEqual(found["changed_fields"], ["input_sha256"])
        self.assertEqual(result["summaries"]["all"]["cas_trained"]
                         ["committed_run_first_difference_fields"], {"input_sha256": 1})
        self.assertEqual(self.differences.comparisons, 0)

    def test_successful_rule_is_prefix_reference_not_direct_reference(self):
        row = fail_row(self.cases)
        self.cases[0]["reference"]["rows"][0]["cjt_id"] = "DIRECT-REFERENCE-DIFFERENT"
        self.assertIsNone(self.build()["cases"][1]["first_committed_run_disagreement"])

    def test_complete_unsuccessful_trajectory_calls_supplied_helper(self):
        row = self.cases[0]["arms"]["cas_trained"]
        row["verification"]["task_correct"] = False
        row["composition_events"][0]["input"] = "wrong"
        result = self.build()
        self.assertEqual(self.differences.comparisons, 1)
        self.assertEqual(result["cases"][1]["first_observed_boundary"], "recorded_trajectory_divergence")
        self.assertEqual(result["summaries"]["all"]["cas_trained"]
                         ["complete_trace_first_difference_categories"], {"input_binding_difference": 1})

    def test_no_difference_is_explicitly_unresolved(self):
        self.cases[0]["arms"]["cas_trained"]["verification"]["task_correct"] = False
        self.assertEqual(self.build()["cases"][1]["first_observed_boundary"],
                         "unresolved_no_difference_in_selected_fields")

    def test_rejection_does_not_compare_trajectory(self):
        row = self.cases[0]["arms"]["cas_trained"]
        row.update(execution_status="REJECTED", model_rejection=True, rows=[],
                   composition_events=None, complete_trace=False)
        row["verification"] = {**dict.fromkeys(C.FIELDS, False),
                               "repair_required": False, "repair_success": None}
        result = self.build()
        self.assertEqual(result["cases"][1]["first_observed_boundary"], "pre_execution_rejection")
        self.assertEqual(result["summaries"]["all"]["cas_trained"]["model_rejections"], 1)
        self.assertEqual(self.differences.comparisons, 0)

    def test_post_start_failure_is_not_model_rejection(self):
        row = fail_row(self.cases)
        row["model_rejection"] = True
        with self.assertRaisesRegex(ValueError, "STATUS_CLASSIFICATION"):
            self.build()

    def test_partial_compute_counts_cannot_be_negative_bool_or_complete(self):
        for key, value in (("committed_native_runs", -1), ("committed_native_runs", True),
                           ("committed_reserved_policy_units", -1), ("compute_complete", True),
                           ("failed_tick_compute", 0)):
            with self.subTest(key=key, value=value):
                self.tasks, self.predictions, self.cases = fixtures()
                fail_row(self.cases)["partial_work"][key] = value
                with self.assertRaisesRegex(ValueError, "PARTIAL_BOUNDARY"):
                    self.build()

    def test_partial_rows_or_complete_trace_cannot_be_forged(self):
        for key in ("rows", "complete_trace", "composition_events"):
            with self.subTest(key=key):
                self.tasks, self.predictions, self.cases = fixtures()
                row = fail_row(self.cases)
                row[key] = [] if key != "complete_trace" else True
                with self.assertRaisesRegex(ValueError, "PARTIAL_BOUNDARY"):
                    self.build()

    def test_named_sites_missing_kind_wrong_input_and_child_are_literal(self):
        target = self.tasks[0]["target"]
        action = deepcopy(target)
        action["binding"] = True
        action["program"]["procedures"]["entry"]["steps"][0].update(input="wrong", procedure="wrong")
        result = report.named_site_metrics(action, target)
        self.assertEqual(result["counts"]["observation_binding_correct"], 0)
        self.assertEqual(result["counts"]["named_input_sites_correct"], 1)
        self.assertEqual(result["counts"]["named_child_sites_correct"], 0)
        self.assertEqual([e["field"] for e in result["errors"]], ["input", "child"])
        missing = report.named_site_metrics(None, target)
        self.assertEqual(missing["counts"]["named_input_sites_expected"], 2)
        self.assertEqual(missing["counts"]["named_input_sites_correct"], 0)

    def test_literal_good_binding_remains_good_when_verifier_unknown(self):
        fail_row(self.cases)
        found = self.build()["cases"][1]
        self.assertIsNone(found["verification"]["binding_correct"])
        self.assertEqual(found["named_site_diagnostic"]["counts"]["named_input_sites_correct"], 2)

    def test_inputs_are_not_mutated(self):
        self.cases[0]["arms"]["cas_trained"]["verification"]["task_correct"] = False
        before = deepcopy((self.tasks, self.predictions, self.cases))
        self.build()
        self.assertEqual((self.tasks, self.predictions, self.cases), before)

    def test_wrong_group_distribution_rejected(self):
        self.tasks[0]["contrast_side"] = "wording_shift"
        with self.assertRaisesRegex(ValueError, "GROUP_COUNTS"):
            self.build()

    def test_wrong_evaluation_split_rejected(self):
        self.tasks[0]["provenance"]["evaluation_group"] = "train"
        with self.assertRaisesRegex(ValueError, "SPLIT_IDENTITY"):
            self.build()

    def test_extra_committed_run_has_only_run_disagreement(self):
        expected = self.cases[0]["arms"]["rule"]["rows"]
        found = report.first_committed_run_difference(expected + deepcopy(expected), expected, C)
        self.assertEqual(found["committed_run_index"], 1)
        self.assertIsNone(found["successful_rule"])
        self.assertNotIn("categories", found)


if __name__ == "__main__":
    unittest.main(verbosity=2)
