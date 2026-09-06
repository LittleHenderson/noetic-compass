"""Synthetic trusted-receipt fixtures only; never GPU or actual learning evidence."""
from copy import deepcopy
from hashlib import sha256
import json

import pytest

from cas_meta3 import learning_evidence as evidence


def raw(value):
    return json.dumps(value, sort_keys=True, indent=2).encode()


def h(value):
    return sha256(value).hexdigest()


def action():
    return {"binding": 0, "program": {"schema": "cas-meta2-program/0.1", "entry": "main", "procedures": {
        "main": {"input": "arg", "allowed_cjts": ["A", "B", "C"], "steps": [
            {"kind": "RUN", "cjt_id": "A", "input": "arg", "output": "v0"},
            {"kind": "CALL", "procedure": "p0", "input": "v0", "output": "v1"}], "return": "v1"},
        "p0": {"input": "arg", "allowed_cjts": ["B", "C"], "steps": [
            {"kind": "RUN", "cjt_id": "B", "input": "arg", "output": "v0"},
            {"kind": "RUN", "cjt_id": "C", "input": "v0", "output": "v1"}], "return": "v1"}}}}


class Fixture:
    """Fictional audit hashes are explicitly trusted only inside these tests."""
    def __init__(self):
        self.action, self.source = action(), "c" * 40
        self.policy = {name: h(("synthetic source:" + name).encode()) for name in evidence.POLICY_FILES}
        self.predictions, self.cases = [], []
        for index in range(72):
            arms, actions = {}, {}
            for arm in evidence.ARMS:
                correct = arm == "rule" or (arm == "cas_trained" and index < 2) or (arm == "generic_trained" and index == 0)
                arms[arm] = {**{key: correct for key in evidence.FIELDS}, "model_rejection": not correct,
                    "native_runs": 3 if correct else 0, "reserved_policy_units": 15 if correct else 0}
                actions[arm] = deepcopy(self.action) if correct else {"fixture_model_rejection": True}
            self.cases.append({"case_index": index, "arms": arms,
                "reference": {**{key: True for key in evidence.FIELDS}, "native_runs": 3, "reserved_policy_units": 15}})
            self.predictions.append({"case_index": index, "public_sha256": h(str(index).encode()), "actions": actions})
        self.checkpoints = {}
        self.files = {}
        for family in ("cas", "generic"):
            name = evidence.BASE + "candidate_" + family + "_best.pt"
            content = ("THIS IS NOT A MODEL: " + family).encode()
            self.files[name] = content
            self.checkpoints[family] = {"selected": {"schema": "cas-meta2-candidate-checkpoint/3",
                "family": family, "epoch": 1, "optimizer_steps": 192, "policy_source_sha256": self.policy.copy(),
                "sha256": h(content), "bytes": len(content), "path": "/fake/" + name}}
        self.manifest = {"source_sha": self.source, "baseline_sha": evidence.BASELINE,
            "fixture_only": True, "files_sha256": {evidence.PILOT + "cas_meta2/" + key: value for key, value in self.policy.items()}}
        experiment = {"profile": "learning_v3", "entrypoint": "cas_meta2.campaign_v3"}
        self.inspection = {"schema": "cas-meta2-packet-inspection/3", "fixture_only": True,
            "status": "CAS_META_2_V3_PACKET_FULL_EVIDENCE_VERIFIED", "issues": [],
            "completed_run_evidence_verified": True, "archive_safety_and_all_included_bytes_checked": True,
            "original_full_index_verified": True, "source_sha": self.source,
            "source_manifest": self.manifest, "packet_sha256": "a" * 64, "experiment": experiment,
            "checks": {"full_evaluation": {"checkpoint_sha256": {
                name.removeprefix(evidence.BASE): h(value) for name, value in self.files.items()}}}}
        self.audit = {"schema": "cas-meta2-stored-packet-audit/3", "fixture_only": True,
            "status": "CAS_META_2_V3_STORED_FULL_AUDIT_PASSED", "completed": True, "errors": [],
            "all_extracted_files_unchanged_before_after": True, "source_sha": self.source,
            "published_schema": {"baseline_sha": evidence.BASELINE}, "packet_sha256": "a" * 64,
            "experiment": deepcopy(experiment), "completed_stages": ["inspection_inputs", "published_schema",
                "all_stored_trace_schemas", "smoke_stored_semantics", "full_sealed_stored_semantics", "paired_group_semantics"],
            "full": {"reference_runs": 72, "arm_choices": 360, "cases": self.cases}}

    def inputs(self, *, mutate_index=None, mutate_metrics=None, mutate_bound=None):
        totals = {arm: {"total": 72, **{key: sum(row["arms"][arm][key] for row in self.cases)
            for key in (*evidence.FIELDS, "native_runs", "reserved_policy_units", "model_rejection")}} for arm in evidence.ARMS}
        self.audit["full"]["metrics"] = totals
        self.inspection["checks"]["full_evaluation"]["metrics"] = {
            arm: {**{key: values[key] for key in ("total", *evidence.FIELDS, "native_runs")},
                "model_rejections": values["model_rejection"], "task_accuracy": values["task_correct"] / 72}
            for arm, values in totals.items()}
        if mutate_metrics:
            mutate_metrics(self.inspection, self.audit)
        predictions = b"\n".join(evidence.canonical(row) for row in self.predictions) + b"\n"
        checkpoints = raw(self.checkpoints)
        files = {**self.files, evidence.BASE + "predictions.jsonl": predictions, evidence.BASE + "checkpoints.json": checkpoints}
        index = {"schema": "cas-meta2-full-packet-index/1", "packet_sha256": "a" * 64,
            "entries": [{"path": name, "bytes": len(value), "sha256": h(value)} for name, value in files.items()]}
        if mutate_index:
            mutate_index(index)
        index_bytes = raw(index)
        for document in (self.inspection, self.audit):
            document["full_member_index_sha256"] = h(index_bytes)
        self.inspection["member_files"] = self.audit["member_files_reverified"] = len(index["entries"])
        self.inspection["source_manifest_sha256"] = evidence.digest(self.manifest)
        if mutate_bound:
            mutate_bound(self.inspection, self.audit)
        inspection_bytes = raw(self.inspection)
        self.audit["inspection_receipt_sha256"] = h(inspection_bytes)
        audit_bytes = raw(self.audit)
        return dict(inspection_bytes=inspection_bytes, expected_inspection_sha256=h(inspection_bytes),
            stored_audit_bytes=audit_bytes, expected_stored_audit_sha256=h(audit_bytes),
            index_bytes=index_bytes, predictions_bytes=predictions, checkpoints_bytes=checkpoints,
            trusted_source_sha=self.source, arm="cas_trained", case_index=0, expected_action=deepcopy(self.action))


@pytest.mark.parametrize("arm,correct", [("cas_trained", 2), ("generic_trained", 1)])
def test_complete_synthetic_binding_is_only_eligible_not_qualified(arm, correct):
    inputs = Fixture().inputs()
    inputs["arm"] = arm
    before = deepcopy(inputs)
    result = evidence.bind_learning_evidence(**inputs)
    assert inputs == before
    assert result["status"] == "ELIGIBLE_FOR_REUSE_EVALUATION"
    assert result["trained_correct"] == result["observed_correct_gain"] == correct
    assert result["untrained_correct"] == 0 and result["denominator"] == 72
    assert result["qualification_status"] == "UNQUALIFIED"
    assert not any(result[key] for key in ("promotion_granted", "fresh_native_reuse_tested", "retention_tested",
        "rollback_tested", "neural_execution_performed", "checkpoint_loading_performed"))
    body = {key: value for key, value in result.items() if key != "receipt_sha256"}
    assert result["receipt_sha256"] == evidence.digest(body)
    assert result["source_program_sha256"] == evidence.digest(action()["program"])


@pytest.mark.parametrize("key", ["inspection_bytes", "stored_audit_bytes", "index_bytes", "predictions_bytes", "checkpoints_bytes"])
def test_any_changed_raw_input_fails_its_external_or_indexed_digest(key):
    values = Fixture().inputs()
    values[key] += b" "
    with pytest.raises(evidence.LearningEvidenceError):
        evidence.bind_learning_evidence(**values)


@pytest.mark.parametrize("key,value", [("arm", "rule"), ("arm", "cas_untrained"), ("arm", "generic_untrained"),
    ("arm", []), ("case_index", True), ("case_index", -1), ("case_index", 72),
    ("minimum_correct_gain", 0), ("minimum_correct_gain", True), ("minimum_correct_gain", 73),
    ("minimum_correct_gain", 3), ("trusted_source_sha", "d" * 40)])
def test_caller_scope_and_positive_gain_are_enforced(key, value):
    inputs = Fixture().inputs()
    inputs[key] = value
    with pytest.raises(evidence.LearningEvidenceError):
        evidence.bind_learning_evidence(**inputs)


@pytest.mark.parametrize("document,key,value", [
    ("inspection", "status", "CAS_META_2_V3_PACKET_REJECTED"),
    ("inspection", "completed_run_evidence_verified", False),
    ("inspection", "original_full_index_verified", False),
    ("inspection", "issues", ["fixture failure"]),
    ("audit", "status", "CAS_META_2_V2_STORED_RESULTS_CHECKED_FULL_ACCEPTANCE_BLOCKED"),
    ("audit", "completed", False), ("audit", "errors", [{"failure": "fixture"}]),
    ("audit", "all_extracted_files_unchanged_before_after", False),
    ("audit", "completed_stages", []), ("audit", "packet_sha256", "b" * 64)])
def test_partial_or_old_audits_cannot_be_promoted(document, key, value):
    fixture = Fixture()
    getattr(fixture, document)[key] = value
    with pytest.raises(evidence.LearningEvidenceError):
        evidence.bind_learning_evidence(**fixture.inputs())


@pytest.mark.parametrize("fault", ["denominator", "omitted_case", "duplicate_case", "wrong_arm", "bool_verdict",
    "conjunction", "negative_compute", "rejected_correct", "false_reference"])
def test_full_native_cases_are_recounted_not_trusted_as_summary(fault):
    fixture = Fixture()
    case = fixture.cases[0]
    row = case["arms"]["cas_trained"]
    if fault == "denominator":
        fixture.audit["full"]["reference_runs"] = 71
    elif fault == "omitted_case":
        fixture.cases.pop()
    elif fault == "duplicate_case":
        fixture.cases[1]["case_index"] = 0
    elif fault == "wrong_arm":
        case["arms"]["extra"] = deepcopy(row)
    elif fault == "bool_verdict":
        row["task_correct"] = 1
    elif fault == "conjunction":
        row["actual_output_correct"] = False
    elif fault == "negative_compute":
        row["native_runs"] = -1
    elif fault == "rejected_correct":
        row["model_rejection"] = True
    else:
        case["reference"]["task_correct"] = False
    with pytest.raises(evidence.LearningEvidenceError):
        evidence.bind_learning_evidence(**fixture.inputs())


def test_good_overall_gain_does_not_make_wrong_selected_case_eligible():
    fixture = Fixture()
    inputs = fixture.inputs()
    inputs.update(case_index=3, expected_action=fixture.predictions[3]["actions"]["cas_trained"])
    with pytest.raises(evidence.LearningEvidenceError, match="SELECTED_LEARNED_TASK"):
        evidence.bind_learning_evidence(**inputs)


def test_correct_action_without_paired_learning_gain_is_refused():
    fixture = Fixture()
    for case in fixture.cases[:2]:
        case["arms"]["cas_untrained"] = deepcopy(case["arms"]["cas_trained"])
    with pytest.raises(evidence.LearningEvidenceError, match="POSITIVE_HELDOUT"):
        evidence.bind_learning_evidence(**fixture.inputs())


@pytest.mark.parametrize("fault", ["binding", "program", "checkpoint_family", "checkpoint_source", "checkpoint_epoch", "checkpoint_digest"])
def test_selected_action_and_checkpoint_identity_are_bound(fault):
    fixture = Fixture()
    selected = fixture.checkpoints["cas"]["selected"]
    if fault == "checkpoint_family": selected["family"] = "generic"
    if fault == "checkpoint_source": selected["policy_source_sha256"] = {}
    if fault == "checkpoint_epoch": selected["epoch"] = 0
    if fault == "checkpoint_digest": selected["sha256"] = "b" * 64
    inputs = fixture.inputs()
    if fault == "binding": inputs["expected_action"]["binding"] = 1
    if fault == "program": inputs["expected_action"]["program"]["procedures"]["main"]["return"] = "v0"
    with pytest.raises(evidence.LearningEvidenceError):
        evidence.bind_learning_evidence(**inputs)


@pytest.mark.parametrize("fault", ["duplicate", "case_alias", "parent_path", "absolute_path", "negative_bytes", "bad_sha"])
def test_index_aliases_paths_and_types_are_checked(fault):
    def mutate(index):
        row = index["entries"][0]
        if fault == "duplicate": index["entries"].append(deepcopy(row))
        if fault == "case_alias": index["entries"].append({**row, "path": row["path"].upper()})
        if fault == "parent_path": row["path"] = "../bad"
        if fault == "absolute_path": row["path"] = "/bad"
        if fault == "negative_bytes": row["bytes"] = -1
        if fault == "bad_sha": row["sha256"] = "g" * 64
    with pytest.raises(evidence.LearningEvidenceError):
        evidence.bind_learning_evidence(**Fixture().inputs(mutate_index=mutate))


@pytest.mark.parametrize("raw_input", [b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e999}', b'[]', b'null'])
def test_bad_json_and_non_object_receipts_fail_closed(raw_input):
    inputs = Fixture().inputs()
    inputs.update(inspection_bytes=raw_input, expected_inspection_sha256=h(raw_input))
    with pytest.raises(evidence.LearningEvidenceError):
        evidence.bind_learning_evidence(**inputs)


def test_aggregate_recount_rejects_self_reported_extra_success():
    def mutate(inspection, audit):
        audit["full"]["metrics"]["cas_trained"]["task_correct"] += 1
    with pytest.raises(evidence.LearningEvidenceError, match="AGGREGATE_RECOUNT"):
        evidence.bind_learning_evidence(**Fixture().inputs(mutate_metrics=mutate))


def test_raw_anchor_must_be_external_not_taken_from_modified_receipt():
    inputs = Fixture().inputs()
    inputs["expected_stored_audit_sha256"] = "0" * 64
    with pytest.raises(evidence.LearningEvidenceError, match="TRUSTED_RECEIPT_DIGEST"):
        evidence.bind_learning_evidence(**inputs)


def test_pure_module_imports_no_model_provider_or_storage_dependency():
    import ast
    from pathlib import Path
    tree = ast.parse(Path(evidence.__file__).read_text())
    roots = {node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    roots |= {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    assert roots <= {"copy", "hashlib", "json", "math", "re"}


@pytest.mark.parametrize("count", [65535, 65536])
def test_declared_maximum_index_fits_the_json_tree_guard(count):
    document = {"schema": "cas-meta2-full-packet-index/1", "packet_sha256": "a" * 64,
        "entries": [{"path": "cloud_job/fixture_" + str(i), "bytes": 1, "sha256": "b" * 64}
                    for i in range(count)]}
    payload = raw(document)
    assert len(payload) < evidence.MAX_BYTES
    parsed = evidence._json(payload)
    assert len(evidence._index(parsed)) == count


def test_tree_size_guard_still_rejects_data_above_its_ceiling():
    payload = raw([None] * evidence.MAX_TREE_NODES)
    with pytest.raises(evidence.LearningEvidenceError, match="EVIDENCE_TREE_CEILING"):
        evidence._json(payload)
