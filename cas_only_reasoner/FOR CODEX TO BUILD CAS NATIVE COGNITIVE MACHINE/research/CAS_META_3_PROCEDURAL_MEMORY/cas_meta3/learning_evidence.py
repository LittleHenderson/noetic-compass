"""Bind a candidate action to already trusted learning-audit bytes, without execution.

Expected receipt digests are caller trust anchors, not values obtained from the
candidate package. This reader does not authenticate a provider, rerun audits,
load checkpoints, grant qualification, activate a skill or prove retention.
It only decides whether a saved, correct learned action may enter reuse tests.
"""
from copy import deepcopy
from hashlib import sha256
import json
import math
import re

SCHEMA = "cas-meta3-learning-evidence/0.1"
BASELINE = "0917267b1354e5d036263eaa6ba9a7197eafb776"
BASE = "cloud_job/campaign/"
PILOT = "research/CAS_META_2_COMPOSITION/"
ARMS = ("cas_untrained", "cas_trained", "generic_untrained", "generic_trained", "rule")
FIELDS = ("task_correct", "procedure_correct", "binding_correct", "dependency_correct", "actual_output_correct", "trace_valid")
MAX_BYTES = 16 * 1024 * 1024
MAX_INDEX_MEMBERS = 65536
# Each index row has one object plus three values. Leave room for the
# enclosing index fields; the tree guard must admit its own member limit.
MAX_TREE_NODES = 4 * MAX_INDEX_MEMBERS + 64
POLICY_FILES = ("train_v3.py", "policy_v3.py", "features_v3.py", "grammar_v3.py", "selection_v3.py",
    "loss_v3.py", "policy.py", "features_v2.py", "codec.py", "ir.py", "curriculum_v3.py",
    "exclusions_v3.json", "development_exclusions_v3.json", "gpu_preflight_v3.py")


class LearningEvidenceError(ValueError):
    pass


def require(condition, code):
    if not condition:
        raise LearningEvidenceError(code)


def digest_bytes(raw):
    require(type(raw) is bytes and 0 < len(raw) <= MAX_BYTES, "BOUNDED_RAW_EVIDENCE_REQUIRED")
    return sha256(raw).hexdigest()


def _hash(value, size=64):
    require(type(value) is str and re.fullmatch(r"[a-f0-9]{" + str(size) + "}", value), "INVALID_EXPECTED_IDENTITY")


def _tree(value):
    # Do not silently coerce tuples, subclasses, integer keys or nonfinite data.
    stack, count = [(value, 0)], 0
    while stack:
        item, depth = stack.pop()
        count += 1
        require(count <= MAX_TREE_NODES and depth <= 48, "EVIDENCE_TREE_CEILING")
        if type(item) is dict:
            require(all(type(k) is str for k in item), "EVIDENCE_KEY_TYPE")
            stack.extend((v, depth + 1) for v in item.values())
        elif type(item) is list:
            stack.extend((v, depth + 1) for v in item)
        else:
            require(type(item) in (str, int, float, bool, type(None)), "EVIDENCE_VALUE_TYPE")
            require(type(item) is not float or math.isfinite(item), "NONFINITE_EVIDENCE")


def canonical(value):
    _tree(value)
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")
    require(len(raw) <= MAX_BYTES, "EVIDENCE_BYTE_CEILING")
    return raw


def digest(value):
    return sha256(canonical(value)).hexdigest()


def _json(raw):
    digest_bytes(raw)
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "DUPLICATE_EVIDENCE_FIELD")
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(LearningEvidenceError("NONFINITE_EVIDENCE")))
    _tree(value)
    return value


def _trusted(raw, expected):
    _hash(expected)
    require(digest_bytes(raw) == expected, "TRUSTED_RECEIPT_DIGEST_MISMATCH")
    return _json(raw)


def _integer(value, low=0, high=2**63-1):
    return type(value) is int and low <= value <= high


def _index(document):
    require(document["schema"] == "cas-meta2-full-packet-index/1", "FULL_INDEX_SCHEMA_REQUIRED")
    entries = document["entries"]
    require(type(entries) is list and 0 < len(entries) <= MAX_INDEX_MEMBERS, "FULL_INDEX_COUNT_INVALID")
    result, aliases, total = {}, set(), 0
    for row in entries:
        require(type(row) is dict and set(row) == {"path", "bytes", "sha256"}, "INDEX_FIELDS_INVALID")
        name = row["path"]
        require(type(name) is str and name and len(name) <= 4096 and ":" not in name and "\\" not in name
            and all(part not in ("", ".", "..") for part in name.split("/")), "INDEX_PATH_INVALID")
        require(name.casefold() not in aliases and _integer(row["bytes"]), "INDEX_ALIAS_OR_SIZE_INVALID")
        _hash(row["sha256"])
        aliases.add(name.casefold())
        result[name] = row
        total += row["bytes"]
    require(total <= 2 * 1024**3, "INDEX_EXPANSION_CEILING")
    return result


def _indexed(raw, name, inventory):
    require(name in inventory and len(raw) == inventory[name]["bytes"]
        and digest_bytes(raw) == inventory[name]["sha256"], "INDEXED_INPUT_CHANGED:" + name)
    return _json(raw)


def _recount(full, outer):
    require(full["reference_runs"] == 72 and full["arm_choices"] == 360
        and type(full["cases"]) is list and len(full["cases"]) == 72, "FULL_NATIVE_COVERAGE_REQUIRED")
    totals = {arm: {"total": 72, **{key: 0 for key in (*FIELDS, "native_runs", "reserved_policy_units", "model_rejection")}} for arm in ARMS}
    for index, case in enumerate(full["cases"]):
        require(type(case["case_index"]) is int and case["case_index"] == index
            and set(case["arms"]) == set(ARMS), "NATIVE_CASE_ORDER_OR_ARM_COVERAGE")
        require(all(case["reference"][key] is True for key in FIELDS), "FAILED_PRIVATE_REFERENCE")
        for arm, row in case["arms"].items():
            require(all(type(row[key]) is bool for key in (*FIELDS, "model_rejection")), "VERDICT_BOOLEAN_REQUIRED")
            require(row["task_correct"] is all(row[key] for key in FIELDS[1:]), "VERDICT_CONJUNCTION_MISMATCH")
            require(_integer(row["native_runs"]) and _integer(row["reserved_policy_units"]), "COMPUTE_COUNT_INVALID")
            if row["model_rejection"]:
                require(not any(row[k] for k in FIELDS) and row["native_runs"] == row["reserved_policy_units"] == 0,
                    "REJECTION_CANNOT_BE_CORRECT_OR_EXECUTED")
            else:
                require(row["trace_valid"] and row["native_runs"] > 0 and row["reserved_policy_units"] > 0,
                    "EXECUTED_RESULT_REQUIRES_NATIVE_EVIDENCE")
            for key in (*FIELDS, "native_runs", "reserved_policy_units", "model_rejection"):
                totals[arm][key] += row[key]
    require(set(full["metrics"]) == set(outer) == set(ARMS), "AGGREGATE_ARM_COVERAGE")
    for arm, counted in totals.items():
        saved, inspected = full["metrics"][arm], outer[arm]
        require(set(saved) == set(counted) and all(type(saved[key]) is int and saved[key] == value
            for key, value in counted.items()), "STORED_AGGREGATE_RECOUNT_MISMATCH")
        require(all(type(inspected[key]) is int and inspected[key] == counted[key] for key in ("total", *FIELDS, "native_runs"))
            and type(inspected["model_rejections"]) is int and inspected["model_rejections"] == counted["model_rejection"]
            and type(inspected["task_accuracy"]) in (int, float)
            and inspected["task_accuracy"] == counted["task_correct"] / 72, "INSPECTED_AGGREGATE_RECOUNT_MISMATCH")
    return totals


def bind_learning_evidence(*, inspection_bytes, expected_inspection_sha256,
        stored_audit_bytes, expected_stored_audit_sha256, index_bytes, predictions_bytes,
        checkpoints_bytes, trusted_source_sha, arm, case_index, expected_action,
        minimum_correct_gain=1):
    """Return provenance eligible for reuse tests, never an activation decision.

The caller must obtain expected receipt digests from its completed source-bound
audits, independently of the package. No file access or neural execution occurs.
One correct selected action and a positive paired held-out count gain are both
required. This is not a statistical-significance or CAS-advantage claim.
"""
    try:
        return _bind(inspection_bytes, expected_inspection_sha256, stored_audit_bytes,
            expected_stored_audit_sha256, index_bytes, predictions_bytes, checkpoints_bytes,
            trusted_source_sha, arm, case_index, expected_action, minimum_correct_gain)
    except LearningEvidenceError:
        raise
    except (KeyError, TypeError, ValueError, IndexError, RecursionError, OverflowError) as error:
        raise LearningEvidenceError("MALFORMED_LEARNING_EVIDENCE:" + type(error).__name__) from error


def _bind(inspection_raw, inspection_sha, audit_raw, audit_sha, index_raw, predictions_raw,
          checkpoints_raw, source, arm, case_index, expected_action, minimum_gain):
    _hash(source, 40)
    require(arm in ("cas_trained", "generic_trained") and type(arm) is str, "TRAINED_ARM_REQUIRED")
    require(_integer(case_index, 0, 71) and _integer(minimum_gain, 1, 72), "REGISTERED_CASE_AND_POSITIVE_GAIN_REQUIRED")
    inspection, audit = _trusted(inspection_raw, inspection_sha), _trusted(audit_raw, audit_sha)
    require(inspection["schema"] == "cas-meta2-packet-inspection/3"
        and inspection["status"] == "CAS_META_2_V3_PACKET_FULL_EVIDENCE_VERIFIED"
        and inspection["issues"] == [] and all(inspection[k] is True for k in
            ("completed_run_evidence_verified", "archive_safety_and_all_included_bytes_checked", "original_full_index_verified")),
        "FULL_SUCCESSFUL_INSPECTION_REQUIRED")
    require(audit["schema"] == "cas-meta2-stored-packet-audit/3"
        and audit["status"] == "CAS_META_2_V3_STORED_FULL_AUDIT_PASSED"
        and audit["completed"] is True and audit["errors"] == []
        and audit["all_extracted_files_unchanged_before_after"] is True, "FULL_STORED_AUDIT_REQUIRED")
    require(audit["inspection_receipt_sha256"] == inspection_sha
        and audit["source_sha"] == inspection["source_sha"] == source, "AUDIT_SOURCE_OR_INSPECTION_BINDING_MISMATCH")
    _hash(inspection["packet_sha256"])
    require(audit["packet_sha256"] == inspection["packet_sha256"], "AUDIT_PACKET_BINDING_MISMATCH")
    experiment = inspection["experiment"]
    require(experiment == audit["experiment"] and experiment["profile"] == "learning_v3"
        and experiment["entrypoint"] == "cas_meta2.campaign_v3", "EXPERIMENT_PROFILE_MISMATCH")
    manifest = inspection["source_manifest"]
    require(digest(manifest) == inspection["source_manifest_sha256"] and manifest["source_sha"] == source
        and manifest["baseline_sha"] == audit["published_schema"]["baseline_sha"] == BASELINE,
        "PROTECTED_SOURCE_MANIFEST_MISMATCH")
    require(set(audit["completed_stages"]) >= {"inspection_inputs", "published_schema", "all_stored_trace_schemas",
        "smoke_stored_semantics", "full_sealed_stored_semantics", "paired_group_semantics"}, "INCOMPLETE_STORED_STAGES")
    index_sha = digest_bytes(index_raw)
    require(index_sha == inspection["full_member_index_sha256"] == audit["full_member_index_sha256"], "FULL_INDEX_BINDING_MISMATCH")
    index_doc = _json(index_raw)
    require(index_doc["packet_sha256"] == inspection["packet_sha256"], "INDEX_PACKET_MISMATCH")
    inventory = _index(index_doc)
    require(len(inventory) == inspection["member_files"] == audit["member_files_reverified"], "INDEX_COVERAGE_MISMATCH")
    prediction_entry = inventory[BASE + "predictions.jsonl"]
    require(len(predictions_raw) == prediction_entry["bytes"] and digest_bytes(predictions_raw) == prediction_entry["sha256"], "SEALED_PREDICTIONS_CHANGED")
    lines = predictions_raw.splitlines()
    require(len(lines) == 72, "ALL_72_PREDICTIONS_REQUIRED")
    predictions = [_json(line) for line in lines]
    for position, row in enumerate(predictions):
        require(type(row) is dict and set(row) == {"case_index", "public_sha256", "actions"}
            and type(row["case_index"]) is int and row["case_index"] == position and set(row["actions"]) == set(ARMS), "SEALED_PREDICTION_MAPPING_MISMATCH")
        _hash(row["public_sha256"])
    require(canonical(predictions[case_index]["actions"][arm]) == canonical(expected_action), "PACKAGE_ACTION_NOT_SEALED_PREDICTION")
    totals = _recount(audit["full"], inspection["checks"]["full_evaluation"]["metrics"])
    parent_arm = arm.removesuffix("trained") + "untrained"
    gain = totals[arm]["task_correct"] - totals[parent_arm]["task_correct"]
    require(gain >= minimum_gain, "POSITIVE_HELDOUT_LEARNING_GAIN_REQUIRED")
    require(audit["full"]["cases"][case_index]["arms"][arm]["task_correct"] is True, "SELECTED_LEARNED_TASK_NOT_CORRECT")
    checkpoints = _indexed(checkpoints_raw, BASE + "checkpoints.json", inventory)
    family = "cas" if arm == "cas_trained" else "generic"
    selected = checkpoints[family]["selected"]
    name = "candidate_" + family + "_best.pt"
    checkpoint_sha = inventory[BASE + name]["sha256"]
    require(selected["schema"] == "cas-meta2-candidate-checkpoint/3" and selected["family"] == family
        and _integer(selected["epoch"], 1, 60) and _integer(selected["optimizer_steps"], 1)
        and selected["sha256"] == checkpoint_sha
        and selected["bytes"] == inventory[BASE + name]["bytes"]
        and inspection["checks"]["full_evaluation"]["checkpoint_sha256"][name] == checkpoint_sha,
        "SELECTED_CHECKPOINT_BINDING_MISMATCH")
    policy = {name: manifest["files_sha256"][PILOT + "cas_meta2/" + name] for name in POLICY_FILES}
    require(selected["policy_source_sha256"] == policy, "POLICY_WRITER_SOURCE_MISMATCH")
    for checksum in policy.values():
        _hash(checksum)
    action = deepcopy(predictions[case_index]["actions"][arm])
    require(type(action) is dict and set(action) == {"program", "binding"} and _integer(action["binding"], 0, 2), "PROGRAM_ACTION_REQUIRED")
    body = {"schema": SCHEMA, "status": "ELIGIBLE_FOR_REUSE_EVALUATION", "producer_source_sha": source,
        "producer_family": family, "arm": arm, "case_index": case_index,
        "public_sha256": predictions[case_index]["public_sha256"], "action": action,
        "action_sha256": digest(action), "source_program_sha256": digest(action["program"]),
        "policy_checkpoint_sha256": checkpoint_sha, "policy_source_sha256": digest(policy),
        "inspection_sha256": inspection_sha, "stored_audit_sha256": audit_sha,
        "full_member_index_sha256": index_sha, "sealed_predictions_sha256": prediction_entry["sha256"],
        "packet_sha256": inspection["packet_sha256"], "trained_correct": totals[arm]["task_correct"],
        "untrained_correct": totals[parent_arm]["task_correct"], "denominator": 72,
        "minimum_correct_gain": minimum_gain, "observed_correct_gain": gain,
        "qualification_status": "UNQUALIFIED", "promotion_granted": False,
        "fresh_native_reuse_tested": False, "retention_tested": False, "rollback_tested": False,
        "neural_execution_performed": False, "checkpoint_loading_performed": False,
        "boundary": "Caller-anchored saved learning evidence only. Reuse, retention, rollback and skill qualification remain separate. No statistical significance, CAS advantage or general-reasoning claim."}
    return {**body, "receipt_sha256": digest(body)}
