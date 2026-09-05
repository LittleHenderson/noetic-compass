"""Version gates and frozen semantic-check parity; no native neural execution."""
import ast
from copy import deepcopy
import json
from pathlib import Path

import pytest

from tools import audit_stored_packet as old
from tools import audit_stored_packet_v2 as current
from test_stored_packet import inspection, write


def function_tree(module, name):
    tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
    return next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name)


@pytest.mark.parametrize("name", ["protected_schema", "validate_all_traces", "_edges", "_native",
    "reference_verdict", "candidate_verdict", "compare_verdict", "audit_full", "_test_mapping"])
def test_native_answer_and_trace_checks_are_unchanged(name):
    assert ast.dump(function_tree(old, name)) == ast.dump(function_tree(current, name))


def example(tmp_path):
    extracted = tmp_path / "extracted"
    write(extracted / "mock-only.json", {"not_native_evidence": True})
    path = inspection(tmp_path, extracted)
    return extracted, path


def upgrade(path):
    receipt = json.loads(path.read_bytes())
    receipt["schema"] = "cas-meta2-packet-inspection/2"
    receipt["status"] = "CAS_META_2_V2_PACKET_SMOKE_EVIDENCE_VERIFIED"
    receipt["experiment"] = {"profile": "learning_v2", "entrypoint": "cas_meta2.campaign_v2",
        "spec_path": "research/CAS_META_2_COMPOSITION/EXPERIMENT_V2.json", "spec_sha256": "d" * 64}
    write(path, receipt)
    return receipt


def test_old_inspection_cannot_be_used_for_new_protocol(tmp_path):
    _, path = example(tmp_path)
    with pytest.raises(current.StoredPacketInvalid, match="SUCCESSFUL_FULL_INSPECTION_REQUIRED"):
        current.Extracted(path)


def test_new_inspection_inventory_can_be_rechecked(tmp_path):
    extracted, path = example(tmp_path)
    upgrade(path)
    packet = current.Extracted(path)
    assert packet.mode == "smoke" and len(packet.inventory) == 1
    assert packet.json("mock-only.json") == {"not_native_evidence": True}
    packet.verify_all()
    # This is inventory verification only, deliberately not audit_packet success.
    (extracted / "mock-only.json").write_text("{}", encoding="utf-8")
    with pytest.raises(current.StoredPacketInvalid, match="EXTRACTED_MEMBER_CHANGED"):
        packet.verify_all()


@pytest.mark.parametrize("key,value", [("profile", "default"), ("entrypoint", "cas_meta2.campaign"),
    ("spec_path", "../EXPERIMENT_V2.json"), ("spec_sha256", "bad")])
def test_wrong_experiment_cannot_pass_inventory_gate(tmp_path, key, value):
    _, path = example(tmp_path)
    receipt = upgrade(path)
    receipt["experiment"][key] = value
    write(path, receipt)
    with pytest.raises(current.StoredPacketInvalid, match="V2_EXPERIMENT_BINDING_REQUIRED"):
        current.Extracted(path)


def test_grouping_helpers_are_part_of_audit_code_identity():
    source = Path(current.__file__).read_text(encoding="utf-8")
    assert '"curriculum_v2", "features_v2", "selection_v2"' in source
    assert 'validate_dataset(document)' in source
    assert '"EXPERIMENT_V2.json"' in source
    assert '"checkpoint_loading_performed": False' in source


@pytest.fixture(scope="module")
def checked_dataset():
    from cas_meta2.curriculum_v2 import generate_dataset
    return generate_dataset(seed=982341)


def dataset_packet(dataset):
    from hashlib import sha256
    partitions = {"train.json": dataset["splits"]["train"],
                  "validation.json": dataset["splits"]["validation"],
                  "test_private.json": dataset["splits"]["test"],
                  "test_public.json": [task["public"] for task in dataset["splits"]["test"]]}
    data = {current.BASE + "dataset/" + name: deepcopy(value) for name, value in partitions.items()}
    manifest = deepcopy(dataset["manifest"])
    manifest["sha256"] = {name: sha256(current.canonical(value) + b"\n").hexdigest()
                          for name, value in partitions.items()}
    data[current.BASE + "dataset/dataset_manifest.json"] = manifest

    class MockPacket:
        # Pure recorded-JSON fixture, not a native execution or packet inspection.
        def json(self, name):
            return deepcopy(data[name])

        def same_hash(self, name, expected):
            assert sha256(current.canonical(data[name]) + b"\n").hexdigest() == expected

    return MockPacket(), data


def test_smoke_dataset_reconstruction_accepts_matching_public_partition(checked_dataset):
    packet, data = dataset_packet(checked_dataset)
    result = current._dataset(packet)
    assert result == data[current.BASE + "dataset/dataset_manifest.json"]
    assert result["counts"] == {"train": 768, "validation": 48, "test": 72}


@pytest.mark.parametrize("change", ["problem", "observation", "missing_task", "order"])
def test_smoke_dataset_reconstruction_rejects_rehashed_public_mismatch(checked_dataset, change):
    from hashlib import sha256
    packet, data = dataset_packet(checked_dataset)
    public = data[current.BASE + "dataset/test_public.json"]
    if change == "problem":
        public[0]["problem"] += " Altered public wording."
    elif change == "observation":
        public[0]["observations"][0]["values"][0] += 0.5
    elif change == "missing_task":
        public.pop()
    else:
        public[0], public[1] = public[1], public[0]
    # Keep the partition byte hash internally consistent: the new semantic
    # mapping check, not the existing hash gate, must catch the mismatch.
    data[current.BASE + "dataset/dataset_manifest.json"]["sha256"]["test_public.json"] = (
        sha256(current.canonical(public) + b"\n").hexdigest())
    with pytest.raises(current.StoredPacketInvalid, match="V2_DATASET_TEST_PUBLIC_PRIVATE_MAPPING_MISMATCH"):
        current._dataset(packet)


def group_fixture():
    from cas_meta2.campaign_v2 import aggregate_cases
    tasks, cases, full_cases = [], [], []
    names = ("same_depth", "wording_shift", "deeper_calls")
    for index in range(72):
        tasks.append({"provenance": {"evaluation_group": names[index % 3]}})
        arms, derived = {}, {}
        for arm in current.ARMS:
            correct = arm == "rule"
            verdict = {key: correct for key in current.FIELDS}
            verdict.update(native_runs=3 if correct else 0, reserved_policy_units=72 if correct else 0,
                           repair_required=False, repair_success=None)
            arms[arm] = {"verification": verdict, "model_rejection": not correct,
                         "execution_status": "EXECUTED" if correct else "REJECTED", "wall_seconds": 0.0}
            derived[arm] = {**verdict, "model_rejection": not correct}
        cases.append({"case_index": index, "arms": arms})
        full_cases.append({"case_index": index, "arms": derived})
    indices = {name: list(range(offset, 72, 3)) for offset, name in enumerate(names)}
    groups = {name: aggregate_cases([{**cases[position], "case_index": index}
                                    for index, position in enumerate(positions)], 24)
              for name, positions in indices.items()}
    data = {current.BASE + "dataset/test_private.json": tasks,
            current.BASE + "evaluation_groups.json": {"schema": "cas-meta2-group-results/2",
                "groups": groups, "group_case_indices": indices},
            current.BASE + "campaign_receipt.json": {"evaluation_groups": deepcopy(groups)}}
    class MockPacket:
        def json(self, name):
            return deepcopy(data[name])
    return MockPacket(), {"cases": full_cases}, data


def test_group_recount_uses_all_native_derived_verdicts():
    packet, full, _ = group_fixture()
    result = current.audit_evaluation_groups(packet, full)
    for group in result["metrics"].values():
        assert group["rule"]["task_correct"] == 24
        assert group["cas_trained"]["task_correct"] == 0
        assert group["cas_trained"]["model_rejection"] == 24


@pytest.mark.parametrize("key,value", [("task_correct", 1), ("native_runs", 4),
    ("task_accuracy", True), ("model_rejections", 0), ("total", 23), ("repair_success", 1)])
def test_group_summary_cannot_change_audited_outcomes(key, value):
    packet, full, data = group_fixture()
    for location in (data[current.BASE + "evaluation_groups.json"]["groups"],
                     data[current.BASE + "campaign_receipt.json"]["evaluation_groups"]):
        location["same_depth"]["cas_trained"][key] = value
    with pytest.raises(current.StoredPacketInvalid):
        current.audit_evaluation_groups(packet, full)


def test_group_membership_cannot_change_after_audit():
    packet, full, data = group_fixture()
    data[current.BASE + "evaluation_groups.json"]["group_case_indices"]["same_depth"][0] = 1
    with pytest.raises(current.StoredPacketInvalid, match="GROUP_MEMBERSHIP_MISMATCH"):
        current.audit_evaluation_groups(packet, full)
