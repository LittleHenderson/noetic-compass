"""Pure qualification control flow; all execution/auditing operations are injected.

Tests use fake operations. The AWS driver alone may supply native operations,
enforce a hard process deadline, and establish model/source/provider identity.
This module never imports neural libraries, connects to SQLite, or calls AWS.
"""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import stat
import time

from . import child_curriculum_v8 as curriculum
from .executor import digest

SCHEMA = "cas-meta2-one-child-qualification/8"
FLAGS = ("task_correct", "procedure_correct", "binding_correct",
         "dependency_correct", "actual_output_correct", "trace_valid")
COMBINATIONS = ("B_C", "B_CR", "R_C", "R_CR")
MAX_SECONDS = 1800
MAX_OUTPUT_BYTES = 512 * 1024**2
BOUNDARY = ("Qualification of four declared development requests with injected operations. "
    "Not training, learning, held-out generalization, CAS-specific advantage, or active-caller restoration. "
    "Local fake-operation results establish only control flow. The driver must prove actual AWS execution.")


def require(condition, code):
    if not condition:
        raise ValueError(code)


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def byte_hash(raw):
    return sha256(raw).hexdigest()


def hash_string(value):
    return type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def safe_path(path):
    path = Path(path).absolute()
    require(".." not in path.parts and not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
        for p in (path, *path.parents)), "QUALIFICATION_PATH_LINK_OR_ESCAPE")
    return path


def output_bytes(output):
    total = 0
    pending = [safe_path(output)]
    while pending:
        with os.scandir(pending.pop()) as entries:
            for entry in entries:
                # DirEntry's cached Windows metadata omits the hard-link count.
                # Query the path directly, once, while refusing reparse points.
                info = os.stat(entry.path, follow_symlinks=False)
                require(not stat.S_ISLNK(info.st_mode)
                        and not (getattr(info, "st_file_attributes", 0)
                                 & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)),
                        "QUALIFICATION_PATH_LINK_OR_ESCAPE")
                if stat.S_ISREG(info.st_mode):
                    require(info.st_nlink == 1, "QUALIFICATION_OUTPUT_HARDLINK")
                    total += info.st_size
                else:
                    require(stat.S_ISDIR(info.st_mode), "QUALIFICATION_SPECIAL_OUTPUT")
                    pending.append(entry.path)
    return total


def action_plan(action):
    """Read only this fixed four-RUN / one-CALL panel; no semantic equivalence."""
    require(type(action) is dict and type(action.get("binding")) is int and action["binding"] == 0,
            "QUALIFICATION_BINDING_ZERO_REQUIRED")
    program = action["program"]
    parent = program["procedures"][program["entry"]]
    steps = parent["steps"]
    require(len(steps) == 5 and [s.get("kind") for s in steps] == ["RUN"] * 4 + ["CALL"]
            and [s.get("cjt_id") for s in steps[:4]] == ["A", "B", "C", "R"],
            "QUALIFICATION_FIXED_PARENT_REQUIRED")
    require([s["input"] for s in steps[:4]] == [parent["input"], *[s["output"] for s in steps[:3]]],
            "QUALIFICATION_FIXED_PRELUDE_DEPENDENCIES")
    call = steps[4]
    require(parent["return"] == call["output"], "QUALIFICATION_PARENT_MUST_RETURN_CHILD")
    require(set(program["procedures"]) == {program["entry"], call["procedure"]}, "QUALIFICATION_SELECTED_CHILD_ONLY")
    child = program["procedures"][call["procedure"]]
    sequence = [s.get("cjt_id") for s in child["steps"]]
    require(sequence in (["C"], ["C", "R"]) and all(s["kind"] == "RUN" for s in child["steps"])
            and child["return"] == child["steps"][-1]["output"]
            and [s["input"] for s in child["steps"]] == [child["input"], *[s["output"] for s in child["steps"][:-1]]],
            "QUALIFICATION_CHILD_SEQUENCE_OR_RETURN")
    positions = [index for index in (1, 3) if steps[index]["output"] == call["input"]]
    require(len(positions) == 1, "QUALIFICATION_INPUT_MUST_BE_B_OR_R")
    source = positions[0]
    edges = [{"cjt_id": name, "input_node": index - 1} for index, name in enumerate(("A", "B", "C", "R"))]
    edges.append({"cjt_id": "C", "input_node": source})
    if len(sequence) == 2:
        edges.append({"cjt_id": "R", "input_node": 4})
    return {"combination": ("B" if source == 1 else "R") + "_" + "".join(sequence),
        "expected_ticks": len(edges), "edges": edges, "return_node": len(edges) - 1,
        "prelude": deepcopy(steps[:4]), "parent_return": parent["return"], "binding": 0}


def prepare(tasks):
    """Check formal targets against public parsing and seal every panel action."""
    require(type(tasks) is list and len(tasks) == 4, "QUALIFICATION_FOUR_TASKS_REQUIRED")
    cases = []
    for task in deepcopy(tasks):
        curriculum.validate_task(task)
        require(task["provenance"]["split"] == "qualification", "QUALIFICATION_DEVELOPMENT_TASKS_ONLY")
        parsed = curriculum.parse_problem(deepcopy(task["public"]))
        require(parsed == task["target"], "QUALIFICATION_PUBLIC_FORMAL_TARGET_MISMATCH")
        target_plan = action_plan(parsed)
        candidates = []
        for choice in curriculum.candidate_choices(deepcopy(task["public"])):
            action = curriculum.compile_candidate(deepcopy(task["public"]), deepcopy(choice))
            plan = action_plan(action)
            require(plan["prelude"] == target_plan["prelude"] and plan["parent_return"] == target_plan["parent_return"],
                    "QUALIFICATION_CANDIDATE_PARENT_CHANGED")
            candidates.append({"choice": choice, "action": action, "action_sha256": digest(action), **plan})
        require(tuple(c["combination"] for c in candidates) == COMBINATIONS
                and sum(c["action"] == parsed for c in candidates) == 1, "QUALIFICATION_PANEL_COVERAGE")
        cases.append({"task": task, "public_sha256": digest(task["public"]), "target_sha256": digest(parsed),
            "formal_public_target_checked": True, "target_plan": target_plan, "candidates": candidates})
    require(len({c["task"]["task_id"] for c in cases}) == 4
            and {c["target_plan"]["combination"] for c in cases} == set(COMBINATIONS), "QUALIFICATION_TARGET_COVERAGE")
    require(all(c["task"]["public"]["observations"] == cases[0]["task"]["public"]["observations"]
                and c["target_plan"]["prelude"] == cases[0]["target_plan"]["prelude"] for c in cases),
            "QUALIFICATION_SHARED_DEVELOPMENT_INPUTS_REQUIRED")
    ticks = sum(c["target_plan"]["expected_ticks"] + sum(p["expected_ticks"] for p in c["candidates"]) for c in cases)
    require(ticks == 110, "QUALIFICATION_SCHEDULE_CHANGED")
    return {"schema": SCHEMA, "training": False, "cases": cases,
        "scheduled_execution_count": 20, "scheduled_native_ticks": ticks,
        "sealed_before_private_execution": True, "candidate_count": 16}


def check_execution(result, public, action, directory, *, reference, identity):
    require(type(result) is dict and result.get("status") == "EXECUTED"
            and result.get("reference") is reference and result.get("selected_action") == action
            and result.get("public_digest") == digest(public), "QUALIFICATION_EXECUTION_IDENTITY")
    require(Path(result["output_dir"]).resolve() == directory.resolve()
            and Path(result["native_database"]).resolve() == (directory / "native.db").resolve(),
            "QUALIFICATION_EXECUTION_OUTPUT_LOCATION")
    require(all(result.get(k) is True for k in ("trace_valid", "integrity", "fixed_weights"))
            and result["runtime_identity"] == result["runtime_identity_after"], "QUALIFICATION_RUNTIME_NOT_FIXED")
    if identity is not None:
        require(result["runtime_identity"] == identity, "QUALIFICATION_MODEL_OR_RUNTIME_CHANGED")
    require(type(result.get("native_trace_count")) is int and type(result.get("reserved_policy_units")) is int,
            "QUALIFICATION_EXECUTION_COUNTS_REQUIRED")
    return deepcopy(result["runtime_identity"])


def check_audit(audit, result, plan, *, reference):
    require(type(audit) is dict and audit.get("audit_method") == "read-only-sqlite-source-replay/0.1"
            and audit.get("stored_call_tree_verified") is (not reference), "QUALIFICATION_STORED_CALL_TREE_REQUIRED")
    require(audit.get("expected_action_checked") is True, "QUALIFICATION_SEALED_ACTION_AUDIT_REQUIRED")
    require(type(audit.get("trace_count")) is int and audit["trace_count"] == plan["expected_ticks"]
            == result["native_trace_count"] and audit["reserved_policy_units"] == result["reserved_policy_units"],
            "QUALIFICATION_AUDITED_COUNTS")
    require(audit.get("return_node") == plan["return_node"]
            and hash_string(audit.get("final_output_sha256")), "QUALIFICATION_AUDITED_RETURN")
    rows = audit["rows"]
    require(type(rows) is list and len(rows) == audit["trace_count"]
            and [{k: r[k] for k in ("cjt_id", "input_node")} for r in rows] == plan["edges"]
            and all(hash_string(r.get(k)) for r in rows for k in ("input_sha256", "output_sha256")),
            "QUALIFICATION_AUDITED_ROWS")
    require(audit["final_output_sha256"] == rows[plan["return_node"]]["output_sha256"],
            "QUALIFICATION_FINAL_OUTPUT_ROW_DISAGREEMENT")


def run_qualification(tasks, operations, output, *, max_seconds=MAX_SECONDS,
                      max_output_bytes=MAX_OUTPUT_BYTES, clock=time.monotonic):
    require(type(max_seconds) in (int, float) and math.isfinite(max_seconds) and 0 < max_seconds <= MAX_SECONDS,
            "QUALIFICATION_TIME_BOUND")
    require(type(max_output_bytes) is int and 0 < max_output_bytes <= MAX_OUTPUT_BYTES, "QUALIFICATION_OUTPUT_BOUND")
    output = safe_path(output)
    require(not output.exists() and output.parent.is_dir(), "QUALIFICATION_FRESH_OUTPUT_REQUIRED")
    output.mkdir(exist_ok=False)
    started = clock()
    deadline = started + max_seconds
    result = {"schema": SCHEMA, "status": "REFUSED", "qualified": False, "training": False,
        "started_utc": datetime.now(timezone.utc).isoformat(), "max_seconds": max_seconds,
        "max_output_bytes": max_output_bytes, "scheduled_execution_count": 20, "scheduled_native_ticks": 110,
        "attempted_execution_count": 0, "reported_executed_count": 0, "completed_execution_count": 0,
        "audited_native_ticks": 0, "completed_native_ticks": None, "cases": [], "events": [],
        "evidence_kind": getattr(operations, "evidence_kind", "UNSPECIFIED_INJECTED_OPERATIONS"),
        "hard_timeout_enforced_by_core": False, "boundary": BOUNDARY}
    seal_raw = None
    identity = None

    def bounded_write(path, document):
        raw = encoded(document)
        require(output_bytes(output) + len(raw) <= max_output_bytes, "QUALIFICATION_OUTPUT_LIMIT")
        with safe_path(path).open("xb") as stream:
            stream.write(raw)

    def event(kind, **details):
        record = {"event": kind, "utc": datetime.now(timezone.utc).isoformat(), **details}
        result["events"].append(record)
        folder = output / "events"
        folder.mkdir(exist_ok=True)
        bounded_write(folder / ("%04d.json" % (len(result["events"]) - 1)), record)

    def boundary():
        require(clock() < deadline, "QUALIFICATION_DEADLINE")
        require(output_bytes(output) <= max_output_bytes, "QUALIFICATION_OUTPUT_LIMIT")
        if seal_raw is not None:
            require((output / "candidates_sealed.json").read_bytes() == seal_raw, "QUALIFICATION_SEAL_CHANGED")
        assertion = getattr(operations, "assert_identity", None)
        if assertion is not None:
            assertion()

    def operation(label, fn, *args, **kwargs):
        boundary()
        event("OPERATION_STARTED", operation=label)
        answer = fn(*deepcopy(args), **deepcopy(kwargs))
        boundary()
        event("OPERATION_RETURNED", operation=label)
        return answer

    def execution(case, slot, action, plan, *, reference):
        nonlocal identity
        public, task = case["task"]["public"], case["task"]
        directory = output / ("case_%02d" % case["index"]) / slot
        require(not directory.exists(), "QUALIFICATION_EXECUTION_DIRECTORY_EXISTS")
        record = {"slot": slot, "reference": reference, "status": "NOT_ATTEMPTED",
            "action_sha256": digest(action), "planned_ticks": plan["expected_ticks"]}
        case["executions"].append(record)
        boundary()
        record["status"] = "ATTEMPTED"
        result["attempted_execution_count"] += 1
        event("EXECUTION_ATTEMPTED", case=case["index"], slot=slot)
        if reference:
            actual = operation(slot, operations.reference_task, task, directory)
        else:
            actual = operation(slot, operations.execute_task, public, action, directory)
        record["execution_result"] = deepcopy(actual)
        if type(actual) is dict and actual.get("status") == "EXECUTED":
            result["reported_executed_count"] += 1
        identity = check_execution(actual, public, action, directory, reference=reference, identity=identity)
        stored = operation(slot + "_stored", operations.audit, actual, public,
                           expected_action=action, allow_private_reference=reference)
        record["stored_audit"] = deepcopy(stored)
        check_audit(stored, actual, plan, reference=reference)
        result["completed_execution_count"] += 1
        result["audited_native_ticks"] += stored["trace_count"]
        record["status"] = "EXECUTED_AND_STORED_AUDITED"
        if reference:
            case["prelude_audit_rows"] = deepcopy(stored["rows"][:4])
        require(stored["rows"][:4] == case["prelude_audit_rows"], "QUALIFICATION_FOUR_STEP_PREFIX_DIFFERS")
        if reference:
            verdict = operation(slot + "_verify", operations.verify_reference_task, task, actual)
            record["verification"] = deepcopy(verdict)
            require(all(verdict.get(k) is True for k in FLAGS)
                    and verdict.get("candidate_task_evaluation") is False
                    and verdict.get("verdict_kind") == "PRIVATE_NATIVE_REFERENCE_CHECK"
                    and verdict.get("stored_call_tree_verified") is False, "QUALIFICATION_PRIVATE_REFERENCE_REJECTED")
        else:
            verdict = operation(slot + "_verify", operations.verify_task, task, actual, case["reference_result"])
            record["verification"] = deepcopy(verdict)
            require(verdict.get("trace_valid") is True and verdict.get("binding_correct") is True
                    and verdict.get("stored_call_tree_verified") is True, "QUALIFICATION_CANDIDATE_TRACE_OR_BINDING")
        require(verdict.get("native_runs") == stored["trace_count"]
                and verdict.get("reserved_policy_units") == stored["reserved_policy_units"],
                "QUALIFICATION_VERIFIER_AUDIT_COUNTS_DISAGREE")
        bounded_write(directory.parent / (slot + "_qualification.json"), record)
        return actual, stored, verdict

    try:
        boundary()
        sealed = prepare(tasks)
        seal_raw = encoded(sealed)
        bounded_write(output / "candidates_sealed.json", sealed)
        result["candidate_seal_sha256"] = byte_hash(seal_raw)
        event("ALL_SIXTEEN_CANDIDATES_SEALED_BEFORE_PRIVATE_EXECUTION", candidate_count=16)
        for index, prepared in enumerate(sealed["cases"]):
            case = {"index": index, "task": deepcopy(prepared["task"]), "public_sha256": prepared["public_sha256"],
                "target_combination": prepared["target_plan"]["combination"], "executions": [], "status": "REFUSED"}
            result["cases"].append(case)
            (output / ("case_%02d" % index)).mkdir()
            reference, reference_audit, _ = execution(case, "reference", prepared["task"]["target"],
                                                     prepared["target_plan"], reference=True)
            case["reference_result"] = reference
            candidates = []
            for number, candidate in enumerate(prepared["candidates"]):
                actual, stored, verdict = execution(case, "candidate_%02d" % number, candidate["action"],
                                                    candidate, reference=False)
                candidates.append((candidate, stored, verdict))
            # Evaluate the complete four-cell panel, never substitute a fallback.
            comparisons = []
            for candidate, stored, verdict in candidates:
                target = candidate["action_sha256"] == prepared["target_sha256"]
                final_differs = stored["final_output_sha256"] != reference_audit["final_output_sha256"]
                checks = {"combination": candidate["combination"], "correct_target": target,
                    "task_correct": verdict["task_correct"], "final_output_differs_from_reference": final_differs,
                    "final_output_sha256": stored["final_output_sha256"],
                    "reference_final_output_sha256": reference_audit["final_output_sha256"]}
                comparisons.append(checks)
                case["comparisons"] = comparisons
                if target:
                    require(all(verdict.get(k) is True for k in FLAGS) and stored["rows"] == reference_audit["rows"]
                            and not final_differs, "QUALIFICATION_CORRECT_CANDIDATE_FAILED")
                else:
                    require(verdict.get("task_correct") is False and verdict.get("procedure_correct") is False
                            and verdict.get("dependency_correct") is False
                            and verdict.get("actual_output_correct") is False, "QUALIFICATION_WRONG_CHOICE_NOT_REJECTED")
                    require(final_differs, "QUALIFICATION_WRONG_CHOICE_FINAL_OUTPUT_NOT_DISTINCT")
            case["status"] = "QUALIFIED"
            bounded_write(output / ("case_%02d" % index) / "panel_qualification.json", case)
        require(result["attempted_execution_count"] == result["reported_executed_count"]
                == result["completed_execution_count"] == 20 and result["audited_native_ticks"] == 110,
                "QUALIFICATION_ACTUAL_COVERAGE_INCOMPLETE")
        boundary()
        result.update(status="QUALIFIED", qualified=True, completed_native_ticks=110)
    except Exception as error:
        result["failure"] = {"type": type(error).__name__, "message": str(error)}
        result.update(status="REFUSED", qualified=False)
    result["all_scheduled_executions_completed"] = result["completed_execution_count"] == 20
    result["unattempted_execution_count"] = 20 - result["attempted_execution_count"]
    result["failed_or_unaudited_attempts"] = result["attempted_execution_count"] - result["completed_execution_count"]
    result["finished_utc"] = datetime.now(timezone.utc).isoformat()
    result["wall_seconds"] = clock() - started
    try:
        bounded_write(output / "qualification_receipt.json", result)
    except Exception as error:
        # Native/fake output remains. The AWS outer driver can still receipt this returned refusal.
        result.update(status="REFUSED", qualified=False, receipt_saved=False,
                      receipt_failure={"type": type(error).__name__, "message": str(error)})
    return result
