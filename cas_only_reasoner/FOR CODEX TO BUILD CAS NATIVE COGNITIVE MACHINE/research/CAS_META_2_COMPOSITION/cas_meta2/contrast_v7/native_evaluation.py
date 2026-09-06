"""V7 candidate evaluation with unchanged executor and narrow failure containment.

Preparation until the separately frozen recovery's real GPU checks and the
production-v7 end-to-end GPU gate are accepted by a source-bound campaign.
"""
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
import json
import multiprocessing
from pathlib import Path
import os
import sys
import time

from ..contrast_v6 import curriculum as c
from . import data as d, train as t, checks, parent
from .evaluation import prepare
from ..contrast_recovery_v6 import core
from ..contrast_recovery_v6.core import ARMS, FAILURE, require
from ..campaign_v3 import _baseline_identity, _output_bytes, _write

ROOT = Path(__file__).resolve().parents[2]
RECOVERY_MANIFEST = "cas_meta2/contrast_recovery_v6/source_manifest.json"
RECOVERY_MANIFEST_SHA256 = "897c6a72c7411676c4ad80ac9734b3dbe7a7ac169951f58d2ab2fd6d387ecb37"
_WORKER = None


def recovery_identity():
    raw = d.read(ROOT/RECOVERY_MANIFEST)
    c.require(d.digest(raw) == RECOVERY_MANIFEST_SHA256, "V7_RECOVERY_HELPERS_MANIFEST_CHANGED")
    document = d.decode(raw)
    expected = document["files_sha256"]
    c.require(type(expected) is dict and len(expected) == 8, "V7_RECOVERY_HELPERS_COVERAGE")
    for name, pin in expected.items():
        c.require(d.digest(d.read(ROOT/name)) == pin, "V7_RECOVERY_HELPER_CHANGED:"+name)
    return expected


class Operations:
    def __init__(self, job, config, expected_source, expected_baseline):
        t.require_request(job, config)
        self.expected_source, self.expected_baseline = expected_source, expected_baseline
        self.helpers = recovery_identity()
        self.assert_identity()
        from .. import native
        from ..campaign_v3 import admission_error
        from ..train_v3 import setup_cuda, environment_identity
        from ..contrast_recovery_v6.runtime import partial_work
        torch, device = setup_cuda()
        c.require("T4" not in torch.cuda.get_device_name(device).upper(), "T4_NOT_AUTHORIZED")
        from cas_cjt.runtime import RuntimeContractError
        self.runtime_contract_error = RuntimeContractError
        self.native, self.device = native, str(device)
        self.environment = environment_identity(device)
        self.admission_error = admission_error
        self.verify_task = native.verify_task
        self.verify_reference_task = native.verify_reference_task
        self.partial_work = partial_work

    def assert_identity(self):
        c.require(t.source_identity() == self.expected_source, "V7_NATIVE_SOURCE_CHANGED")
        c.require(_baseline_identity() == self.expected_baseline, "V7_NATIVE_BASELINE_CHANGED")
        c.require(recovery_identity() == self.helpers, "V7_NATIVE_RECOVERY_HELPERS_CHANGED")

    def reference_task(self, task, directory):
        return self.native.reference_task(task, directory, device=self.device)

    def execute_task(self, public, action, directory):
        return self.native.execute_task(public, action, directory, device=self.device)


def worker_init(job, config, expected_source, expected_baseline):
    global _WORKER
    _WORKER = Operations(job, config, expected_source, expected_baseline)


def case_worker(arguments):
    index, task, actions, output = arguments
    c.require(_WORKER is not None, "V7_NATIVE_WORKER_NOT_INITIALIZED")
    directory = Path(output)/"evaluation"/f"case_{index:04d}"
    result = core.evaluate_case(index, task, actions, directory, _WORKER)
    _WORKER.assert_identity()
    t.write_new(directory/"worker_identity.json", {
        "pid": os.getpid(), "environment": _WORKER.environment,
        "source_sha256": _WORKER.expected_source, "baseline": _WORKER.expected_baseline,
        "recovery_helpers_sha256": _WORKER.helpers})
    return result


def aggregate_cases(cases, total_expected=72):
    require(type(total_expected) is int and 1 <= total_expected <= 72, 'RECOVERY_FIXED_DENOMINATOR')
    require(type(cases) is list and len(cases) == total_expected and all(type(c.get('case_index')) is int for c in cases)
            and sorted(c['case_index'] for c in cases) == list(range(total_expected)), 'RECOVERY_CASE_COVERAGE')
    for case in cases:
        require(type(case.get('arms')) is dict and set(case['arms']) == set(ARMS), 'RECOVERY_ARM_COVERAGE')
        for arm, row in case['arms'].items():
            require(row['arm'] == arm and type(row['case_index']) is int
                    and row['case_index'] == case['case_index'], 'RECOVERY_ARM_ATTRIBUTION')
            require(row['execution_status'] in ('EXECUTED', 'REJECTED', FAILURE), 'RECOVERY_STATUS_UNKNOWN')
            require(row['model_rejection'] is (row['execution_status'] == 'REJECTED'), 'RECOVERY_REJECTION_ATTRIBUTION')
            if row['execution_status'] == FAILURE:
                require(row['verification'].get('task_correct') is False and row.get('partial_work') is not None,
                        'RECOVERY_RUNTIME_FAILURE_REPORTED_SUCCESS')
                partial = row['partial_work']
                require(type(partial) is dict and partial.get('compute_complete') is False
                        and partial.get('failed_tick_compute') is None
                        and all(type(partial.get(k)) is int and partial[k] >= 0 for k in
                                ('committed_native_runs', 'committed_reserved_policy_units')),
                        'RECOVERY_PARTIAL_WORK_INVALID')
    results = {}
    fields = ('task_correct', 'procedure_correct', 'binding_correct', 'dependency_correct',
              'actual_output_correct', 'trace_valid')
    for arm in ARMS:
        rows = [case['arms'][arm] for case in cases]
        failures = [row for row in rows if row['execution_status'] == FAILURE]
        counts = {key: sum(row['verification'].get(key) is True for row in rows) for key in fields}
        results[arm] = {'total': total_expected, **counts, 'task_accuracy': counts['task_correct']/total_expected,
            'model_rejections': sum(row['model_rejection'] is True for row in rows),
            'post_admission_runtime_failures': len(failures),
            'native_executed': sum(row['execution_status'] == 'EXECUTED' for row in rows),
            'committed_native_runs_lower_bound': sum(
                row['partial_work']['committed_native_runs'] if row['partial_work'] is not None
                else row['verification'].get('native_runs', 0) for row in rows),
            'reserved_policy_units_lower_bound': sum(
                row['partial_work']['committed_reserved_policy_units'] if row['partial_work'] is not None
                else row['verification'].get('reserved_policy_units', 0) for row in rows),
            'compute_complete': not failures, 'all_cases_in_denominator': True,
            'boundary': 'Verified successes out of all declared cases. Runtime failures are not admission rejections; '
                        'their uncommitted failed-tick compute and unverified component metrics remain unknown.'}
    return results



def grouped_results(cases, tasks):
    c.require(len(cases) == len(tasks) and cases, "V7_GROUP_CASE_COVERAGE")
    groups = {}
    for index, (case, task) in enumerate(zip(cases, tasks, strict=True)):
        c.require(case["case_index"] == index and case["task_id"] == task["task_id"], "V7_GROUP_CASE_IDENTITY")
        for name in ("depth_"+str(task["provenance"]["depth"]), task["contrast_side"]):
            groups.setdefault(name, []).append(case)
    return {name: aggregate_cases([{**row, "case_index": i,
        "arms": {arm: {**value, "case_index": i} for arm, value in row["arms"].items()}}
        for i, row in enumerate(rows)], len(rows)) for name, rows in groups.items()}


def validate_private_child(request_path, request_sha256, result_path, job):
    """Cold target validation in a disposable process, never in the trainer."""
    t.require_request(job, t.TrainingConfig())
    request_path, result_path = map(d.no_links, (request_path, result_path))
    c.require(request_path.resolve().is_relative_to(ROOT/"runs")
        and result_path.parent == request_path.parent
        and result_path.name == "cold_dataset_validation.json" and not result_path.exists(),
        "V7_NATIVE_NEW_COLD_CHILD_OUTPUT")
    raw = d.read(request_path)
    c.require(d.digest(raw) == request_sha256, "V7_NATIVE_COLD_REQUEST_CHANGED")
    value = d.decode(raw)
    c.require(value["job"] == job and t.source_identity() == value["source_sha256"],
              "V7_NATIVE_COLD_CHILD_IDENTITY")
    report = parent.validate_bundle(value["private_data"], expected_sha256=value["expected_sha256"],
        seed=value["seed"], config=c.Config(**value["config"]).checked(),
        excluded=frozenset(value["excluded"]), pins=value["pins"],
        expected_pins_sha256=value["expected_pins_sha256"],
        expected_loader_sha256=value["expected_loader_sha256"])
    c.require(t.source_identity() == value["source_sha256"]
        and d.digest(d.read(request_path)) == request_sha256, "V7_NATIVE_COLD_CHILD_SOURCE_CHANGED")
    t.write_new(result_path, report)
    return report


def cold_validation(private_data, output, *, job, expected_manifest_sha256, curriculum_seed,
                    curriculum_config, excluded, pins, expected_pins_sha256,
                    expected_loader_sha256, expected_source, deadline):
    """Require a real child exit so permanent parent guards stay out of here."""
    from ..campaign_v3 import _run_process
    output = d.no_links(output)
    request = {"job": job, "private_data": str(private_data), "expected_sha256": expected_manifest_sha256,
        "seed": curriculum_seed, "config": asdict(curriculum_config), "excluded": sorted(excluded),
        "pins": str(pins), "expected_pins_sha256": expected_pins_sha256,
        "expected_loader_sha256": expected_loader_sha256, "source_sha256": expected_source}
    request_path = output/"cold_validation_request.json"
    t.write_new(request_path, request)
    pin = checks.file_hash(request_path)
    code = ("import sys;from cas_meta2.contrast_v7.native_evaluation import validate_private_child;"
            "validate_private_child(sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4])")
    command = [sys.executable, "-B", "-c", code, str(request_path), pin,
               str(output/"cold_dataset_validation.json"), job]
    _run_process(command, output/"cold_validation_process", min(deadline, time.monotonic()+180),
                 environment=dict(os.environ))
    process = checks.process_exit(output/"cold_validation_process/process_receipt.json",
                                  expected_command=command)
    c.require(process["pid"] != os.getpid() and checks.file_hash(request_path) == pin,
              "V7_NATIVE_COLD_CHILD_EXIT_REQUIRED")
    return checks.read(output/"cold_dataset_validation.json")


def evaluate(private_data, training_output, process_path, bundle, output, *, expected_command, job,
             expected_manifest_sha256, expected_loader_sha256, curriculum_seed, curriculum_config, excluded, config,
             expected_source, expected_baseline, pins, expected_pins_sha256, max_seconds=2400):
    t.require_request(job, config)
    c.require(type(max_seconds) is int and 60 <= max_seconds <= 3600, "V7_NATIVE_TIME_BOUND")
    started = time.monotonic()
    deadline = started+max_seconds
    helpers = recovery_identity()
    gate_kwargs = dict(expected_command=expected_command, job=job,
        expected_manifest_sha256=expected_manifest_sha256, expected_loader_sha256=expected_loader_sha256,
        curriculum_seed=curriculum_seed, curriculum_config=curriculum_config, excluded=excluded,
        config=config, expected_source=expected_source, expected_baseline=expected_baseline)
    gate = checks.check_training(training_output, process_path, bundle, **gate_kwargs)
    c.require(t.source_identity() == expected_source and _baseline_identity() == expected_baseline,
              "V7_NATIVE_INITIAL_IDENTITY")
    # Reuse the unchanged prepare function. All five arms are sealed before the
    # private target file is opened. No model or rule choices are revised.
    prepared = prepare(private_data, training_output, output, gate=gate)
    output = d.no_links(output)
    manifest, splits = prepared["manifest"], prepared["splits"]
    count = len(splits["test"])
    c.require(count in (9, 72), "V7_NATIVE_REGISTERED_CASE_COUNT")
    report = cold_validation(private_data, output, job=job,
        expected_manifest_sha256=expected_manifest_sha256, curriculum_seed=curriculum_seed,
        curriculum_config=curriculum_config, excluded=excluded, pins=pins,
        expected_pins_sha256=expected_pins_sha256, expected_loader_sha256=expected_loader_sha256,
        expected_source=expected_source, deadline=deadline)
    c.require(report.get("completed") is True and report.get("splits") == manifest["splits"]
              and report.get("manifest_sha256") == expected_manifest_sha256, "V7_NATIVE_COLD_DATASET_CHECK")
    t.write_new(output/"training_parent_gate.json", gate)
    tasks, predictions = splits["test"], prepared["predictions"]
    pool = ProcessPoolExecutor(max_workers=8, mp_context=multiprocessing.get_context("spawn"),
        initializer=worker_init, initargs=(job, config, expected_source, expected_baseline))
    futures, completed, succeeded = [], [], False
    try:
        for index, (task, row) in enumerate(zip(tasks, predictions, strict=True)):
            futures.append(pool.submit(case_worker, (index, task, row["actions"], str(output))))
        for future in as_completed(futures, timeout=max(0.01, deadline-time.monotonic())):
            c.require(time.monotonic() < deadline, "V7_NATIVE_DEADLINE")
            completed.append(future.result())
            _write(output/"progress.json", {"completed": len(completed), "expected": count,
                                            "output_bytes": _output_bytes(output)})
        completed.sort(key=lambda row: row["case_index"])
        results = aggregate_cases(completed, count)
        groups = grouped_results(completed, tasks)
        c.require(results["rule"]["task_correct"] == count, "V7_NATIVE_RULE_CONTROL_FAILURE")
        c.require(checks.file_hash(output/"predictions.jsonl") == prepared["seal"]["sha256"]
            and checks.check_training(training_output, process_path, bundle, **gate_kwargs) == gate
            and checks.file_hash(Path(private_data)/"manifest.json") == expected_manifest_sha256
            and all(checks.file_hash(Path(private_data)/name) == pin
                    for name, pin in manifest["sha256"].items())
            and t.source_identity() == expected_source and _baseline_identity() == expected_baseline
            and recovery_identity() == helpers, "V7_NATIVE_BOUND_INPUTS_CHANGED")
        t.write_new(output/"evaluation_results.json", {"cases": completed, "results": results, "groups": groups})
        receipt = {"schema": "cas-meta2-prototype-native-evaluation/7", "completed": True,
            "cases": count, "reference_cases": count, "arm_verdicts": count*5, "workers": 8,
            "results": results, "groups": groups, "seal": prepared["seal"],
            "wall_seconds": time.monotonic()-started, "learning_accepted": False,
            "recovery_helper_manifest_sha256": RECOVERY_MANIFEST_SHA256,
            "boundary": "Unchanged executor and verifier. Exact known post-start runtime failure counts "
                        "incorrect, never as admission rejection; failed-tick compute stays unknown. "
                        "Matched test variants are not independent program structures. No automatic promotion."}
        t.write_new(output/"native_receipt.json", receipt)
        succeeded = True
        return receipt
    finally:
        if succeeded:
            pool.shutdown(wait=True)
        else:
            processes = list(getattr(pool, "_processes", {}).values())
            for future in futures:
                future.cancel()
            for process in processes:
                if process.is_alive():
                    process.terminate()
            for process in processes:
                process.join(timeout=1)
                if process.is_alive():
                    process.kill()
            pool.shutdown(wait=False, cancel_futures=True)
            t.write_new(output/"evaluation_partial.json", {"completed": False, "cases": completed,
                "expected": count, "automatic_retry": False, "partial_files_retained": True})
