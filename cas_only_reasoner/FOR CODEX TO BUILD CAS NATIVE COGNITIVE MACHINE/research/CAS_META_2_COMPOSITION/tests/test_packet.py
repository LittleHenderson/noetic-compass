"""Synthetic byte-only packet fixtures. No fixture represents a neural run."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import stat
import sys
import xml.etree.ElementTree as ET
import zipfile

import pytest

pytestmark = pytest.mark.not_gpu
MODULE = Path(__file__).resolve().parents[1] / "tools" / "inspect_cloud_packet.py"
spec = importlib.util.spec_from_file_location("meta2_packet_inspector", MODULE)
inspector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inspector)
SOURCE = "1" * 40
ARCHIVE = "2" * 64
JOB = "cas-meta2-synthetic-byte-fixture"
B = inspector.BASE


def raw(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def program(kind="plain"):
    def proc(steps):
        return {"input": "arg", "allowed_cjts": ["A", "B", "C"], "steps": steps, "return": steps[-1]["output"]}
    run = {"kind": "RUN", "cjt_id": "A", "input": "arg", "output": "v0"}
    procedures = {"main": proc([run])}
    if kind == "deep":
        procedures = {
            "main": proc([{"kind": "CALL", "procedure": "p0", "input": "arg", "output": "v0"}]),
            "p0": proc([{"kind": "CALL", "procedure": "p1", "input": "arg", "output": "v0"}]),
            "p1": proc([run]),
        }
    elif kind == "named":
        procedures = {"main": proc([
            run,
            {"kind": "RUN", "cjt_id": "B", "input": "v0", "output": "v1"},
            {"kind": "RUN", "cjt_id": "B", "input": "v0", "output": "v2"},
            {"kind": "RUN", "cjt_id": "C", "input": "v1", "output": "v3"},
        ])}
    return {"schema": "cas-meta2-program/0.1", "entry": "main", "procedures": procedures}


def verdict(correct=True, runs=1):
    out = {key: correct for key in inspector.VERDICT_FIELDS}
    out.update(repair_required=False, repair_success=None)
    if correct:
        out.update(native_runs=runs, reserved_policy_units=runs * 100)
    return out


def native(payload, folder, action, reference, public_digest="3" * 64):
    count = inspector._program_stats(action["program"])["expanded_run_count"]
    content = {"native.db": b"SYNTHETIC BYTE FIXTURE, NOT A DATABASE",
               "native_traces.json": raw([{"synthetic": True, "index": i} for i in range(count)]),
               "composition_events.json": b"[]", "native_kernel_events.json": b"[]"}
    for name, value in content.items():
        payload[folder + "/" + name] = value
    out = "/synthetic/runs/" + folder
    result = {"status": "EXECUTED", "reference": reference, "selected_action": action,
              "public_digest": public_digest, "native_trace_count": count,
              "reserved_policy_units": count * 100, "gpu_forward_audit": {"calls": count, "device": "cuda:0"},
              "runtime_identity": {"synthetic": True}, "runtime_identity_after": {"synthetic": True},
              "trace_valid": True, "integrity": True, "fixed_weights": True,
              "output_dir": out, "native_database": out + "/native.db",
              "evidence_sha256": {name: inspector.sha(value) for name, value in content.items()}}
    payload[folder + "/result.json"] = raw(result)
    return result


def smoke_fixture():
    payload = {}
    source_map = {"cas_meta2/synthetic.py": "4" * 64, "pyproject.toml": "5" * 64}
    wheel1, wheel2 = "6" * 64, "7" * 64
    manifest = {"source_sha": SOURCE, "baseline_sha": inspector.BASELINE_SHA, "pilot_dir": "research/CAS_META_2_COMPOSITION",
                "protected_baseline_files": 316, "wheel_paths": ["frozen/one.whl", "frozen/two.whl"],
                "files_sha256": {"research/CAS_META_2_COMPOSITION/" + name: value for name, value in source_map.items()}}
    manifest["files_sha256"].update({"frozen/one.whl": wheel1, "frozen/two.whl": wheel2})
    baseline = {"source": {"baseline_sha": inspector.BASELINE_SHA, "files_verified": 316},
                "installed_wheels": {"casformer": {"wheel_sha256": wheel1, "package_files_verified": 1},
                                     "cas_cjt": {"wheel_sha256": wheel2, "package_files_verified": 1}}}
    rows = []
    for name, kind in (("training_anchor", "plain"), ("nested_depth", "deep"), ("named_earlier_value", "named")):
        action = {"program": program(kind), "binding": 0}
        folder = B + "smoke/" + name
        ref = native(payload, folder + "/reference", action, True)
        result = native(payload, folder + "/execution", action, False)
        checked = verdict(runs=ref["native_trace_count"])
        for filename, value in (("reference_result.json", ref), ("execution_result.json", result),
                                ("reference_verdict.json", checked), ("verification.json", checked)):
            payload[folder + "/" + filename] = raw(value)
        rows.append({"fixture": name, "program_sha256": inspector.sha(inspector.canonical(action["program"])),
                     "structure": inspector._program_stats(action["program"]), "reference": checked, "verification": checked})
    smoke = {"status": "CAS_META_2_NATIVE_SMOKE_COMPLETED", "completed": True, "cases": rows, "case_count": 3}
    payload[B + "smoke_receipt.json"] = raw(smoke)
    campaign = {"status": "CAS_META_2_AWS_SMOKE_COMPLETED", "completed": True, "smoke": smoke,
                "evaluation_completed": False, "training_performed": False,
                "source": source_map, "baseline_before": baseline, "baseline_after": baseline}
    payload[B + "campaign_receipt.json"] = raw(campaign)
    for family, names in inspector.GPU_CASES.items():
        prefix = "cloud_job/gpu_" + family
        payload[prefix + "_receipt.json"] = raw({"passed": 4, "tests": 4, "failures": 0, "errors": 0, "skipped": 0})
        root = ET.Element("testsuites")
        suite = ET.SubElement(root, "testsuite", tests="4", failures="0", errors="0", skipped="0")
        for name in names:
            ET.SubElement(suite, "testcase", name=name)
        payload[prefix + "_tests.xml"] = ET.tostring(root)
        payload[prefix + "_tests.log"] = b"synthetic raw log"
        test = "tests/test_execution_contract.py" if family == "contract" else "tests/test_policy_gpu.py"
        payload[prefix + "_command.json"] = raw(["python", "-m", "pytest", "-m", "gpu", test])
    payload["cloud_job/runtime.json"] = raw({"cuda_matmul_passed": True, "torch": "2.11.0+cu128", "cuda": "12.8",
                                           "gpu": "SYNTHETIC RTX PRO 4500 Blackwell"})
    payload[B + "environment.json"] = raw({"torch": "2.11.0+cu128", "cuda_runtime": "12.8",
        "cuda_device_name": "SYNTHETIC RTX PRO 4500 Blackwell", "deterministic_algorithms": True,
        "tf32_matmul": False, "tf32_cudnn": False, "torch_cpu_threads": 1})
    for name in ("pip_freeze.txt", "torch_install.json", "dependency_install.json", "frozen_wheel_install.json", "command.json"):
        payload["cloud_job/" + name] = b"[]"
    job = {"job": JOB, "source_sha": SOURCE, "baseline_sha": inspector.BASELINE_SHA,
           "archive_sha256": ARCHIVE, "returncode": 0, "smoke_only": True}
    payload["cloud_job/job.json"] = raw(job)
    return payload, manifest, job


def full_fixture():
    payload, manifest, job = smoke_fixture()
    job["smoke_only"] = False
    payload["cloud_job/job.json"] = raw(job)
    campaign = json.loads(payload[B + "campaign_receipt.json"])
    campaign.update(status="CAS_META_2_AWS_CAMPAIGN_COMPLETED", evaluation_completed=True,
                    all_test_cases_evaluated_per_arm=72, reference_cases=72, arm_verdicts=360)
    action = {"program": program(), "binding": 0}
    publics = [{"problem": "synthetic_" + str(i), "observations": []} for i in range(72)]
    private = [{"public": public, "target": action, "task_id": str(i)} for i, public in enumerate(publics)]
    train = [{"public": {"problem": "train_" + str(i), "observations": []}, "target": action} for i in range(256)]
    data = {"train.json": train, "validation.json": train[:48], "test_public.json": publics, "test_private.json": private}
    dataset_manifest = {"sha256": {}}
    for name, value in data.items():
        payload[B + "dataset/" + name] = raw(value)
        dataset_manifest["sha256"][name] = inspector.sha(raw(value))
    payload[B + "dataset/dataset_manifest.json"] = raw(dataset_manifest)
    rejected = {"status": "REJECTED", "reason": "synthetic invalid generation"}
    predictions = [{"case_index": i, "public_sha256": inspector.sha(inspector.canonical(public)),
                    "actions": {arm: action if arm == "rule" else rejected for arm in inspector.ARMS}}
                   for i, public in enumerate(publics)]
    prediction_bytes = b"".join(raw(row) + b"\n" for row in predictions)
    payload[B + "predictions.jsonl"] = prediction_bytes
    tokenizer = {"fit_split": "train_only", "fitted_examples": 256,
                 "fitted_public_sha256": inspector.sha(inspector.canonical([task["public"] for task in train]))}
    payload[B + "tokenizer.json"] = raw(tokenizer)
    seal = {"test_private_labels_loaded": False, "arms": list(inspector.ARMS), "test_examples": 72, "prediction_count": 360,
            "sha256": inspector.sha(prediction_bytes), "test_public_sha256": dataset_manifest["sha256"]["test_public.json"],
            "test_private_sha256": dataset_manifest["sha256"]["test_private.json"],
            "sealed_utc": "2026-09-05T12:00:00+00:00", "tokenizer_digest": inspector.sha(inspector.canonical(tokenizer))}
    payload[B + "predictions_seal.json"] = raw(seal)
    payload[B + "test_gold_opening_receipt.json"] = raw({
        "opened_utc": "2026-09-05T12:00:01+00:00", "prediction_sha256_before_opening": seal["sha256"],
        "test_private_sha256": seal["test_private_sha256"]})
    checkpoints = {}
    for family in ("cas", "generic"):
        checkpoints[family] = {}
        for state, suffix in (("initial", "initial"), ("selected", "best"), ("last", "last")):
            name = f"candidate_{family}_{suffix}.pt"
            content = ("SYNTHETIC CHECKPOINT BYTES " + name).encode()
            payload[B + name] = content
            checkpoints[family][state] = {"path": "/synthetic/" + name, "sha256": inspector.sha(content),
                "bytes": len(content), "optimizer_steps": 0 if state == "initial" else 16, "epoch": 0 if state == "initial" else 1}
    matching = {"cas_trainable_parameters": 1000, "generic_trainable_parameters": 1000, "relative_difference": 0.0}
    gradients = {family: {"all_parameter_tensors_connected": True, "trainable_parameters": 1000,
                         "connected_trainable_parameters": 1000} for family in ("cas", "generic")}
    training = {"checkpoints": checkpoints, "completed_epochs": 1, "requested_epochs": 1,
                "optimizer_steps": {"cas": 16, "generic": 16}, "learning_conditions_matched": True,
                "parameter_matching": matching, "active_parameters": gradients}
    for name, value in (("training_receipt.json", training), ("checkpoints.json", checkpoints),
                        ("parameter_matching.json", matching), ("gradient_connectivity.json", gradients)):
        payload[B + name] = raw(value)
    payload[B + "training_preregistration.json"] = raw({"config": {"seed": 7, "epochs": 1, "batch_size": 16},
        "train_examples": 256, "validation_examples": 48, "test_examples": 72,
        "arms": list(inspector.ARMS), "dataset_sha256": dataset_manifest["sha256"]})
    payload[B + "training_history.json"] = raw([{"epoch": 1, "families": {
        family: {"validation": {"token_cross_entropy": 0.5}} for family in ("cas", "generic")}}])
    cases = []
    for index in range(72):
        folder = B + f"evaluation/case_{index:04d}"
        public_hash = predictions[index]["public_sha256"]
        reference = native(payload, folder + "/reference", action, True, public_hash)
        payload[folder + "/reference_result.json"] = raw(reference)
        payload[folder + "/reference_verdict.json"] = raw(verdict())
        rows = {}
        for arm in inspector.ARMS:
            arm_folder = folder + "/" + arm
            invalid = arm != "rule"
            result = ({"status": "REJECTED", "action": rejected} if invalid
                      else native(payload, arm_folder + "/native", action, False, public_hash))
            checked = verdict(not invalid)
            row = {"case_index": index, "arm": arm, "action": predictions[index]["actions"][arm],
                   "verification": checked, "model_rejection": invalid, "execution_status": result["status"]}
            payload[arm_folder + "/execution_result.json"] = raw(result)
            payload[arm_folder + "/verification.json"] = raw(checked)
            payload[arm_folder + "/case_receipt.json"] = raw(row)
            rows[arm] = row
        case = {"case_index": index, "arms": rows, "reference_verification": verdict()}
        payload[folder + "/case_receipt.json"] = raw(case)
        cases.append(case)
    results = {}
    for arm in inspector.ARMS:
        correct = 72 if arm == "rule" else 0
        results[arm] = {"total": 72, "all_cases_in_denominator": True,
                       **{field: correct for field in inspector.VERDICT_FIELDS},
                       "model_rejections": 72 - correct, "native_executed": correct,
                       "native_runs": correct, "reserved_policy_units": correct * 100,
                       "task_accuracy": correct / 72, "repair_required_total": 0, "repair_success": None}
    payload[B + "evaluation_results.json"] = raw({"results": results, "cases": cases})
    campaign.update(training=training, prediction_seal=seal, results=results,
                    cas_task_accuracy_gain=0.0, generic_task_accuracy_gain=0.0)
    payload[B + "campaign_receipt.json"] = raw(campaign)
    payload[B + "payload_sha256.json"] = raw({name.removeprefix(B): inspector.sha(value)
        for name, value in payload.items() if name.startswith(B)})
    return payload, manifest, job


def pack(path, payload, job, *, omit=None, mutate_collection=None):
    original = [{"path": name, "bytes": len(value), "sha256": inspector.sha(value)} for name, value in sorted(payload.items())]
    selected = {name: value for name, value in payload.items() if name != omit}
    record = {**job, "partial_evidence": omit is not None, "original_file_count": len(payload),
              "included_full_file_count": len(selected), "omitted_full_file_count": len(payload) - len(selected),
              "original_bytes": sum(len(value) for value in payload.values()),
              "original_file_index_sha256": inspector.sha(b"".join(inspector.canonical(row) + b"\n" for row in original)),
              "index_entries": original[:1000], "index_entries_omitted": max(0, len(original) - 1000)}
    if omit:
        record["returncode"] = 1
    if mutate_collection:
        mutate_collection(record)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, value in selected.items():
            archive.writestr(name, value)
        archive.writestr(inspector.COLLECTION, raw(record))
    return inspector.file_hash(path)


@pytest.fixture
def work(tmp_path, monkeypatch):
    monkeypatch.setattr(inspector, "ROOT", tmp_path)
    records = tmp_path / "records"
    records.mkdir()
    return records


def inspect(work, payload, manifest, job, *, omit=None, mutate_collection=None, extract=False):
    packet = work / "packet.zip"
    digest = pack(packet, payload, job, omit=omit, mutate_collection=mutate_collection)
    return inspector.inspect_packet(packet, expected_sha256=digest, source_sha=SOURCE, job=JOB,
        output=work / "inspection", source_manifest=manifest, source_archive_sha256=ARCHIVE,
        extract=work / "packet_extracted" if extract else None)


def test_complete_smoke_is_byte_verified_without_neural_claim(work):
    receipt = inspect(work, *smoke_fixture(), extract=True)
    assert receipt["status"] == "CAS_META_2_PACKET_SMOKE_EVIDENCE_VERIFIED"
    assert receipt["completed_run_evidence_verified"]
    assert receipt["original_full_index_verified"]
    assert receipt["extraction"]["all_member_bytes_verified_after_write"]
    assert not receipt["stored_semantic_reverification_performed"]
    assert not receipt["checkpoint_loading_performed"]
    index = Path(receipt["full_member_index"])
    assert inspector.file_hash(index) == receipt["full_member_index_sha256"]


def test_full_packet_recounts_all_360_results_and_six_opaque_checkpoints(work):
    receipt = inspect(work, *full_fixture())
    assert receipt["status"] == "CAS_META_2_PACKET_FULL_EVIDENCE_VERIFIED"
    checked = receipt["checks"]["full_evaluation"]
    assert checked["arm_verdicts"] == 360 and len(checked["checkpoint_sha256"]) == 6
    assert checked["metrics"]["cas_trained"]["total"] == 72
    assert checked["metrics"]["cas_trained"]["task_correct"] == 0
    assert checked["metrics"]["rule"]["task_correct"] == 72
    assert not checked["checkpoint_contents_loaded"]


def test_failed_run_preserves_all_logs_without_pass_claim(work):
    payload, manifest, job = smoke_fixture()
    job["returncode"] = 1
    payload["cloud_job/job.json"] = raw(job)
    payload["cloud_job/remote_failure.json"] = raw({"message": "synthetic GPU test failure"})
    receipt = inspect(work, payload, manifest, job)
    assert receipt["status"] == "CAS_META_2_PACKET_FAILED_RUN"
    assert not receipt["completed_run_evidence_verified"]
    assert receipt["original_full_index_verified"]


def test_partial_packet_keeps_included_evidence_and_reports_missing_files(work):
    payload, manifest, job = smoke_fixture()
    receipt = inspect(work, payload, manifest, job, omit="cloud_job/gpu_policy_tests.log", extract=True)
    assert receipt["status"] == "CAS_META_2_PACKET_PARTIAL_EVIDENCE"
    assert receipt["collection"]["omitted_full_file_count"] == 1
    assert not receipt["original_full_index_verified"]
    assert not receipt["completed_run_evidence_verified"]


@pytest.mark.parametrize("mutation", [
    lambda p: p.__setitem__("cloud_job/gpu_policy_receipt.json", raw({"passed": 3, "tests": 4, "failures": 1, "errors": 0, "skipped": 0})),
    lambda p: p.__setitem__("cloud_job/gpu_contract_tests.xml", b'<testsuites><testsuite tests="4" failures="0" errors="0" skipped="0"/></testsuites>'),
    lambda p: p.__setitem__("cloud_job/runtime.json", raw({"cuda_matmul_passed": True, "torch": "2.11.0+cu128", "cuda": "12.8", "gpu": "T4"})),
    lambda p: p.pop(B + "smoke/training_anchor/reference/native.db"),
    lambda p: p.__setitem__(B + "smoke/training_anchor/execution/native_traces.json", b"[]"),
    lambda p: p.__setitem__(B + "candidate_cas_initial.pt", b"unexpected"),
])
def test_fake_success_fails_evidence_checks(work, mutation):
    payload, manifest, job = smoke_fixture()
    mutation(payload)
    receipt = inspect(work, payload, manifest, job)
    assert receipt["status"] == "CAS_META_2_PACKET_EVIDENCE_MISMATCH"
    assert not receipt["completed_run_evidence_verified"] and receipt["issues"]


def test_independent_source_manifest_is_not_optional_for_completion(work):
    payload, _, job = smoke_fixture()
    receipt = inspect(work, payload, None, job)
    assert "source_binding:INDEPENDENT_SOURCE_MANIFEST_REQUIRED" in receipt["issues"]


def test_full_original_index_is_checked_beyond_prefix(work):
    payload = {f"many/file_{i:04d}.txt": str(i).encode() for i in range(1200)}
    _, manifest, job = smoke_fixture()
    job["returncode"] = 1
    with pytest.raises(inspector.PacketInvalid, match="COMPLETE_ORIGINAL_INDEX_DIGEST"):
        inspect(work, payload, manifest, job, mutate_collection=lambda record: record.update(original_file_index_sha256="0" * 64))


@pytest.mark.parametrize("name", ["../outside", "/absolute", "x/../../a", "a\\b", "C:evil", "a//b",
                                 "a/./b", "nul.txt", "folder/COM1", "trailing.", "trailing ", "x:stream", "x?y"])
def test_unsafe_windows_and_traversal_names_rejected(name):
    with pytest.raises(inspector.PacketInvalid):
        inspector.safe_name(name)


@pytest.mark.parametrize("names", [["a.txt", "a.txt"], ["a.txt", "A.TXT"], ["a", "a/child"]])
def test_duplicate_case_alias_and_file_directory_collisions_rejected(work, names):
    packet = work / "unsafe.zip"
    with zipfile.ZipFile(packet, "w") as archive:
        for name in names:
            archive.writestr(name, b"x")
    with zipfile.ZipFile(packet) as archive, pytest.raises(inspector.PacketInvalid):
        inspector._safe_infos(archive)


def test_symlink_and_resource_limits_rejected(work, monkeypatch):
    packet = work / "unsafe.zip"
    info = zipfile.ZipInfo("link")
    info.create_system = 3
    info.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(packet, "w") as archive:
        archive.writestr(info, b"target")
    with zipfile.ZipFile(packet) as archive, pytest.raises(inspector.PacketInvalid, match="SYMLINK"):
        inspector._safe_infos(archive)
    with zipfile.ZipFile(packet, "w") as archive:
        archive.writestr("large", b"12345")
    monkeypatch.setattr(inspector, "MAX_EXPANDED", 4)
    with zipfile.ZipFile(packet) as archive, pytest.raises(inspector.PacketInvalid, match="EXPANDED"):
        inspector._safe_infos(archive)


@pytest.mark.parametrize("value", [b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e999}', b'{"x":Infinity}'])
def test_duplicate_and_nonfinite_json_rejected(value):
    with pytest.raises(inspector.PacketInvalid):
        inspector.json_bytes(value)


def test_hash_mismatch_and_outside_extraction_fail_before_writes(work):
    payload, manifest, job = smoke_fixture()
    packet = work / "packet.zip"
    digest = pack(packet, payload, job)
    with pytest.raises(inspector.PacketInvalid, match="PACKET_SHA256"):
        inspector.inspect_packet(packet, expected_sha256="0" * 64, source_sha=SOURCE, job=JOB, output=work / "audit")
    assert not (work / "audit").exists()
    with pytest.raises(inspector.PacketInvalid, match="OUTSIDE"):
        inspector.inspect_packet(packet, expected_sha256=digest, source_sha=SOURCE, job=JOB,
                                 output=work / "audit", extract=work.parent / "outside_extracted")
    assert not (work.parent / "outside_extracted").exists()


def test_existing_output_is_never_overwritten(work):
    payload, manifest, job = smoke_fixture()
    (work / "inspection").mkdir()
    (work / "inspection" / "keep.txt").write_bytes(b"keep")
    with pytest.raises(inspector.PacketInvalid, match="MUST_BE_NEW"):
        inspect(work, payload, manifest, job)
    assert (work / "inspection" / "keep.txt").read_bytes() == b"keep"


def test_inspector_has_no_torch_or_checkpoint_deserializer():
    import ast
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    imported = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    imported |= {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    assert not imported.intersection({"torch", "pickle", "numpy", "cas_meta2.policy", "cas_meta2.train"})
    assert "torch" not in sys.modules
