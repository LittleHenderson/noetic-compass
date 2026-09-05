"""Synthetic evidence only: these fixtures never run a model or contact AWS."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools import inspect_cloud_packet_v2 as inspector
from tools import experiment_profiles as profiles
from cas_meta2.features_v2 import LosslessPublicTokenizer
from cas_meta2.selection_v2 import generated_metrics
from cas_meta2.codec import action_to_ids

_SPEC = importlib.util.spec_from_file_location("old_packet_fixture_v2", ROOT / "tests/test_packet.py")
fixtures = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(fixtures)
pytestmark = pytest.mark.not_gpu
B = inspector.BASE
raw = fixtures.raw


def public(text):
    return {"problem": text, "observations": [
        {"slot": slot, "tag": "Row " + str(slot), "values": [0.1 * (slot + 1)] * 8}
        for slot in range(3)]}


def dataset():
    action = {"program": fixtures.program(), "binding": 0}
    train = [{"public": public("Train  Text\n"), "target": deepcopy(action)} for _ in range(768)]
    validation = [{"public": public("Validation\tText"), "target": deepcopy(action)} for _ in range(48)]
    publics = [public("Held out β\n" + str(index)) for index in range(72)]
    private = [{"task_id": str(index), "public": value, "target": deepcopy(action),
                "provenance": {"evaluation_group": ("same_depth", "wording_shift", "deeper_calls")[index // 24]}}
               for index, value in enumerate(publics)]
    return {"train.json": train, "validation.json": validation,
            "test_public.json": publics, "test_private.json": private}


def synthetic_preflight(payload, manifest, spec, train):
    tokenizer = LosslessPublicTokenizer.fit_train([task["public"] for task in train], max_length=1024)
    lengths = [len(tokenizer.encode_public(task["public"])["ids"]) for task in train]
    actions = [len(action_to_ids(task["target"])) for task in train]
    indices = sorted(range(768), key=lambda index: (-lengths[index], index))[:16]
    geometry = {"training_examples": 768, "batch_size": 16, "selected_training_indices": indices,
        "selected_input_lengths": [lengths[i] for i in indices],
        "selected_action_lengths_including_bos_eos": [actions[i] for i in indices],
        "maximum_training_input_tokens": max(lengths), "maximum_training_action_tokens_including_bos_eos": max(actions),
        "maximum_selected_action_tokens_including_bos_eos": max(actions[i] for i in indices),
        "configured_input_limit": 1024, "configured_action_limit": 256,
        "tokenizer_digest": tokenizer.digest, "vocabulary_size": len(tokenizer.vocabulary),
        "training_public_sha256": inspector.sha(inspector.canonical([task["public"] for task in train])),
        "selected_target_sha256": inspector.sha(inspector.canonical([train[i]["target"] for i in indices])),
        "actual_padded_input_tokens": max(lengths[i] for i in indices),
        "actual_padded_target_tokens_excluding_bos": max(actions[i] for i in indices) - 1}
    queries = sum(lengths[i] for i in indices)
    gate = lambda layer: {"layer": layer, "valid_queries": queries * 4, "active_queries": queries * 4,
                          "active_queries_per_head": [queries] * 4, "active_fraction": 1.0}
    families = {family: {"all_parameters_cuda": True, "all_buffers_cuda": True,
        "optimizer_updates": 0, "all_trainable_parameter_tensors_have_finite_nonzero_gradient": True,
        "missing_or_invalid_gradient_parameter_names": [], "finite_nonzero_gradient_parameter_names": ["synthetic.weight"],
        "diagnostic_token_cross_entropy": 1.0, "gate_layers": [gate(0), gate(1)] if family == "cas" else []}
        for family in ("cas", "generic")}
    return {"schema": "cas-meta2-gpu-preflight/2", "status": "CAS_META_2_V2_GPU_PREFLIGHT_PASSED", "completed": True,
        "source_sha256": manifest["files_sha256"][profiles.PILOT + "/cas_meta2/gpu_preflight_v2.py"],
        "aws_job_id": fixtures.JOB, "device": "cuda:0", "gpu_name": "SYNTHETIC RTX PRO 4500 Blackwell",
        "optimizer_updates": 0, "model_training_performed": False, "native_execution_performed": False,
        "held_out_labels_accessed": False, "config": deepcopy(spec["training"]), "geometry": geometry,
        "parameter_matching": {"cas_trainable_parameters": 1000, "generic_trainable_parameters": 1000,
                               "frozen_candidate_parameter_names": [], "relative_difference": 0.0},
        "identical_common_initial_parameter_names": ["synthetic.weight"], "families": families,
        "gpu_total_memory_bytes": 1000000, "cuda_allocated_bytes_before": 0, "cuda_reserved_bytes_before": 0,
        "peak_cuda_allocated_bytes": 1000, "peak_cuda_reserved_bytes": 2000,
        "cuda_allocated_bytes_after_cleanup": 0, "cuda_reserved_bytes_after_cleanup": 0}


def fixture(*, full=True):
    payload, manifest, job = fixtures.full_fixture() if full else fixtures.smoke_fixture()
    spec = json.loads((ROOT / "EXPERIMENT_V2.json").read_bytes())
    spec_bytes = raw(spec)
    for name in profiles.V2_LOCAL_FILES:
        manifest["files_sha256"][profiles.PILOT + "/" + name] = "9" * 64
    manifest["files_sha256"][profiles.V2_SPEC] = inspector.sha(spec_bytes)
    experiment = {"profile": "learning_v2", "entrypoint": "cas_meta2.campaign_v2",
                  "spec_path": profiles.V2_SPEC, "spec_sha256": inspector.sha(spec_bytes)}
    manifest["experiment"] = experiment
    campaign = json.loads(payload[B + "campaign_receipt.json"])
    campaign["source"] = {name.removeprefix(profiles.PILOT + "/"): value for name, value in manifest["files_sha256"].items()
        if name.startswith(profiles.PILOT + "/cas_meta2/") and name.endswith(".py")}
    campaign["source"]["pyproject.toml"] = manifest["files_sha256"][profiles.PILOT + "/pyproject.toml"]
    campaign["source"]["EXPERIMENT_V2.json"] = experiment["spec_sha256"]
    campaign["experiment"] = experiment
    job["experiment"] = experiment
    payload["cloud_job/job.json"] = raw(job)
    payload["cloud_job/command.json"] = raw(["/synthetic/python", "-m", "cas_meta2.campaign_v2", "--output",
        "/synthetic/research/CAS_META_2_COMPOSITION/runs/cloud_job/campaign", "--max-wall-seconds", "6600"]
        + ([] if full else ["--smoke-only"]))
    names = inspector.V2_GPU_CASES
    xml = ET.Element("testsuites")
    suite = ET.SubElement(xml, "testsuite", tests="6", failures="0", errors="0", skipped="0")
    for name in names:
        ET.SubElement(suite, "testcase", name=name)
    payload["cloud_job/gpu_policy_tests.xml"] = ET.tostring(xml)
    payload["cloud_job/gpu_policy_receipt.json"] = raw({"passed": 6, "tests": 6, "failures": 0, "errors": 0, "skipped": 0})
    payload["cloud_job/gpu_policy_command.json"] = raw(["python", "-m", "pytest", "-m", "gpu", "tests/test_policy_gpu.py", "tests/test_learning_v2_gpu.py"])
    data = dataset()
    for name, values in data.items():
        payload[B + "dataset/" + name] = raw(values)
    dm = {"schema": "cas-meta2-dataset-manifest/2", "seed": 20260917,
          "counts": {"train": 768, "validation": 48, "test": 72},
          "sha256": {name: inspector.sha(raw(value)) for name, value in data.items()}}
    payload[B + "dataset/dataset_manifest.json"] = raw(dm)
    preflight = synthetic_preflight(payload, manifest, spec, data["train.json"])
    payload[B + "gpu_preflight_v2.json"] = raw(preflight)
    campaign["gpu_preflight"] = preflight
    if full:
        tokenizer = LosslessPublicTokenizer.fit_train([task["public"] for task in data["train.json"]], max_length=1024)
        payload[B + "tokenizer.json"] = raw(tokenizer.to_dict())
        predictions = [json.loads(line) for line in payload[B + "predictions.jsonl"].splitlines()]
        for index, prediction in enumerate(predictions):
            prediction["public_sha256"] = inspector.sha(inspector.canonical(data["test_public.json"][index]))
        payload[B + "predictions.jsonl"] = b"".join(raw(row) + b"\n" for row in predictions)
        seal = json.loads(payload[B + "predictions_seal.json"])
        seal.update(sha256=inspector.sha(payload[B + "predictions.jsonl"]),
                    test_public_sha256=dm["sha256"]["test_public.json"], test_private_sha256=dm["sha256"]["test_private.json"],
                    tokenizer_digest=tokenizer.digest)
        payload[B + "predictions_seal.json"] = raw(seal)
        payload[B + "test_gold_opening_receipt.json"] = raw({"opened_utc": "2026-09-05T12:00:01+00:00",
            "prediction_sha256_before_opening": seal["sha256"], "test_private_sha256": seal["test_private_sha256"]})
        config = deepcopy(spec["training"])
        payload[B + "training_preregistration.json"] = raw({"schema": "cas-meta2-learning-preregistration/2",
            "config": config, "train_examples": 768, "validation_examples": 48, "test_examples": 72,
            "arms": list(inspector.ARMS), "dataset_sha256": dm["sha256"]})
        history = []
        invalid = {"status": "REJECTED", "reason": "synthetic"}
        for epoch in range(1, 6):
            row = {"epoch": epoch, "optimizer_steps": {"cas": epoch * 48, "generic": epoch * 48}, "families": {}}
            for family in ("cas", "generic"):
                validation = {"token_cross_entropy": 1.0 / epoch}
                if epoch in (1, 5):
                    actions = [task["target"] if epoch == 1 and index < 10 else invalid
                               for index, task in enumerate(data["validation.json"])]
                    metrics = generated_metrics(actions, data["validation.json"])
                    validation["generation"] = metrics
                    payload[B + f"validation_predictions/{family}_epoch_{epoch:04d}.json"] = raw({
                        "epoch": epoch, "actions": actions, "metrics": metrics, "split": "validation", "test_gold_access": False})
                row["families"][family] = {"validation": validation, "selected": epoch == 1}
            history.append(row)
        payload[B + "training_history.json"] = raw(history)
        checkpoints = json.loads(payload[B + "checkpoints.json"])
        for family in ("cas", "generic"):
            for state in ("initial", "selected", "last"):
                epoch = {"initial": 0, "selected": 1, "last": 5}[state]
                checkpoints[family][state].update(schema="cas-meta2-candidate-checkpoint/2", epoch=epoch,
                    optimizer_steps=epoch * 48, validation={} if epoch == 0 else history[epoch - 1]["families"][family]["validation"])
        payload[B + "checkpoints.json"] = raw(checkpoints)
        training = json.loads(payload[B + "training_receipt.json"])
        training.update(checkpoints=checkpoints, completed_epochs=5, requested_epochs=100, optimizer_steps={"cas": 240, "generic": 240})
        training["parameter_matching"] = deepcopy(preflight["parameter_matching"])
        payload[B + "parameter_matching.json"] = raw(training["parameter_matching"])
        payload[B + "training_receipt.json"] = raw(training)
        campaign.update(training=training, prediction_seal=seal)
        evaluated = json.loads(payload[B + "evaluation_results.json"])
        groups = {}
        indices = {group: list(range(offset * 24, (offset + 1) * 24))
                   for offset, group in enumerate(("same_depth", "wording_shift", "deeper_calls"))}
        for group in indices:
            groups[group] = {}
            for arm in inspector.ARMS:
                row = deepcopy(evaluated["results"][arm])
                for key in ("total", *inspector.VERDICT_FIELDS, "model_rejections", "native_executed", "native_runs", "reserved_policy_units"):
                    row[key] //= 3
                groups[group][arm] = row
        payload[B + "evaluation_groups.json"] = raw({"schema": "cas-meta2-group-results/2",
            "groups": groups, "group_case_indices": indices})
        campaign["evaluation_groups"] = groups
    payload[B + "campaign_receipt.json"] = raw(campaign)
    refresh(payload)
    return payload, manifest, job, spec_bytes


def refresh(payload):
    if B + "payload_sha256.json" in payload:
        payload[B + "payload_sha256.json"] = raw({name.removeprefix(B): inspector.sha(value)
            for name, value in payload.items() if name.startswith(B) and name != B + "payload_sha256.json"})


class MemoryPacket:
    def __init__(self, payload):
        self.payload = payload
        self.inventory = {name: {"path": name, "bytes": len(value), "sha256": inspector.sha(value)} for name, value in payload.items()}
    def json(self, name):
        return inspector.json_bytes(self.payload[name])
    def raw(self, name, *args):
        return self.payload[name]
    def same_hash(self, name, digest):
        inspector.require(self.inventory[name]["sha256"] == digest, "SYNTHETIC_MEMBER_DIGEST_MISMATCH")


def full_check(payload, spec_bytes):
    return inspector._full(MemoryPacket(payload), json.loads(payload[B + "campaign_receipt.json"]), json.loads(spec_bytes))


def test_v2_full_accepts_measured_zero_learning_without_promoting_success():
    payload, _, _, spec_bytes = fixture()
    report = full_check(payload, spec_bytes)
    assert report["cases"] == 72 and report["arm_verdicts"] == 360
    assert report["metrics"]["cas_trained"]["task_correct"] == 0
    assert report["learning_v2"]["selected_epochs"] == {"cas": 1, "generic": 1}
    assert report["learning_v2"]["public_text_round_trips"] == 888


def test_v2_all_bytes_extraction_and_distinct_receipt(tmp_path, monkeypatch):
    payload, manifest, job, spec_bytes = fixture(full=False)
    archive = tmp_path / "packet.zip"
    fixtures.pack(archive, payload, job)
    spec = tmp_path / "EXPERIMENT_V2.json"
    spec.write_bytes(spec_bytes)
    monkeypatch.setattr(inspector.legacy, "ROOT", tmp_path)
    report = inspector.inspect_packet(archive, expected_sha256=inspector.file_hash(archive), source_sha=fixtures.SOURCE,
        job=fixtures.JOB, output=tmp_path / "records/check", source_manifest=manifest, source_archive_sha256=fixtures.ARCHIVE,
        experiment_spec=spec, extract=tmp_path / "records/packet_extracted")
    assert report["status"] == "CAS_META_2_V2_PACKET_SMOKE_EVIDENCE_VERIFIED", report["issues"]
    assert report["schema"] == "cas-meta2-packet-inspection/2"
    assert report["original_full_index_verified"] is True
    assert report["extraction"]["all_member_bytes_verified_after_write"] is True
    assert report["neural_execution_performed"] is False


def test_v2_complete_packet_with_outer_bundle_receipt_succeeds(tmp_path, monkeypatch):
    payload, manifest, job, spec_bytes = fixture()
    archive = tmp_path / "full.zip"
    fixtures.pack(archive, payload, job)
    spec = tmp_path / "EXPERIMENT_V2.json"; spec.write_bytes(spec_bytes)
    monkeypatch.setattr(inspector.legacy, "ROOT", tmp_path)
    report = inspector.inspect_packet(archive, expected_sha256=inspector.file_hash(archive), source_sha=fixtures.SOURCE,
        job=fixtures.JOB, output=tmp_path / "records/full", source_manifest={"launch_manifest": manifest, "archive_sha256": fixtures.ARCHIVE},
        experiment_spec=spec)
    assert report["status"] == "CAS_META_2_V2_PACKET_FULL_EVIDENCE_VERIFIED", report["issues"]
    assert report["completed_run_evidence_verified"] is True
    assert report["checks"]["full_evaluation"]["metrics"]["cas_trained"]["task_correct"] == 0


def test_v2_source_cannot_pass_v1_inspector():
    payload, manifest, _, _ = fixture(full=False)
    campaign = json.loads(payload[B + "campaign_receipt.json"])
    inspector._source_binding(campaign, manifest, fixtures.SOURCE)
    with pytest.raises(inspector.PacketInvalid, match="CAMPAIGN_SOURCE_HASH_BINDING_MISMATCH"):
        inspector.legacy._source_binding(campaign, manifest, fixtures.SOURCE)


@pytest.mark.parametrize("mutation", ["config", "schema", "steps", "tokenizer", "validation_metrics", "selection", "extra_epoch", "checkpoint_schema"])
def test_v2_training_mismatches_fail_closed(mutation):
    payload, _, _, spec_bytes = fixture()
    if mutation in ("config", "schema"):
        name = B + "training_preregistration.json"
        value = json.loads(payload[name])
        if mutation == "config": value["config"]["learning_rate"] *= 2
        else: value["schema"] = "cas-meta2-learning-preregistration/1"
        payload[name] = raw(value)
    elif mutation == "tokenizer":
        value = json.loads(payload[B + "tokenizer.json"])
        value["fitted_examples"] = 767
        payload[B + "tokenizer.json"] = raw(value)
    elif mutation == "validation_metrics":
        name = B + "validation_predictions/cas_epoch_0001.json"
        value = json.loads(payload[name]); value["metrics"]["joint_correct"] += 1; payload[name] = raw(value)
    elif mutation == "extra_epoch":
        payload[B + "validation_predictions/cas_epoch_0002.json"] = payload[B + "validation_predictions/cas_epoch_0001.json"]
    else:
        training = json.loads(payload[B + "training_receipt.json"])
        if mutation == "steps": training["optimizer_steps"]["cas"] -= 1
        elif mutation == "selection": training["checkpoints"]["cas"]["selected"]["epoch"] = 5
        else: training["checkpoints"]["cas"]["selected"]["schema"] = "cas-meta2-candidate-checkpoint/1"
        payload[B + "training_receipt.json"] = raw(training)
        payload[B + "checkpoints.json"] = raw(training["checkpoints"])
        campaign = json.loads(payload[B + "campaign_receipt.json"]); campaign["training"] = training
        payload[B + "campaign_receipt.json"] = raw(campaign)
    refresh(payload)
    with pytest.raises(ValueError): full_check(payload, spec_bytes)


@pytest.mark.parametrize("mutation", ["wrong_module", "old_gpu_gate", "source", "wrong_batch", "inactive", "gradient", "memory"])
def test_v2_gpu_and_dispatch_mismatches_fail_closed(mutation):
    payload, manifest, job, spec_bytes = fixture(full=False)
    campaign = json.loads(payload[B + "campaign_receipt.json"])
    if mutation == "wrong_module":
        argv = json.loads(payload["cloud_job/command.json"]); argv[2] = "cas_meta2.campaign"
        payload["cloud_job/command.json"] = raw(argv)
        with pytest.raises(ValueError): inspector._command(MemoryPacket(payload), manifest["experiment"], True)
    elif mutation == "old_gpu_gate":
        payload["cloud_job/gpu_policy_receipt.json"] = raw({"passed": 4, "tests": 4, "failures": 0, "errors": 0, "skipped": 0})
        with pytest.raises(ValueError): inspector._gpu_gate(MemoryPacket(payload), "policy")
    else:
        preflight = campaign["gpu_preflight"]
        if mutation == "source": preflight["source_sha256"] = "0" * 64
        elif mutation == "wrong_batch": preflight["geometry"]["selected_training_indices"][-1] = 100
        elif mutation == "inactive": preflight["families"]["cas"]["gate_layers"][0]["active_queries_per_head"][0] = 0
        elif mutation == "gradient": preflight["families"]["cas"]["missing_or_invalid_gradient_parameter_names"] = ["bad"]
        else: preflight["cuda_allocated_bytes_after_cleanup"] = 1
        payload[B + "gpu_preflight_v2.json"] = raw(preflight)
        with pytest.raises(ValueError): inspector._preflight(MemoryPacket(payload), campaign, manifest, json.loads(spec_bytes), job["job"])


def test_v2_requires_explicit_spec_profile(tmp_path):
    _, manifest, _, spec_bytes = fixture(full=False)
    spec = tmp_path / "spec.json"; spec.write_bytes(spec_bytes)
    del manifest["experiment"]
    with pytest.raises(ValueError, match="V2_EXPLICIT_MANIFEST_REQUIRED"):
        inspector._experiment_spec(manifest, spec)


def test_inspection_module_does_not_import_torch_or_training():
    assert "torch" not in sys.modules
    assert "cas_meta2.train_v2" not in sys.modules
