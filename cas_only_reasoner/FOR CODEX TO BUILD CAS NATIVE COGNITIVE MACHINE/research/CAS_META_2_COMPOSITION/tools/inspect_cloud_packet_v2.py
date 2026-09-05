"""Strict byte-only learning-v2 packet inspection; no checkpoint deserialization.

Archive, full-index, extraction and unchanged native-record byte checks reuse
the frozen v1 inspector. This module adds only the separate v2 experiment,
lossless-text, generated-validation-selection and dataset contracts.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import inspect_cloud_packet as legacy
from tools import experiment_profiles as profiles
from cas_meta2.features_v2 import LosslessPublicTokenizer
from cas_meta2.selection_v2 import generated_metrics, selection_key
from cas_meta2.codec import action_to_ids

BASE, BASELINE_SHA = legacy.BASE, legacy.BASELINE_SHA
MAX_EXPANDED, MAX_MEMBERS = legacy.MAX_EXPANDED, legacy.MAX_MEMBERS
MAX_COMPRESSED = legacy.MAX_COMPRESSED
SHA256, SHA1 = legacy.SHA256, legacy.SHA1
file_hash, json_bytes, safe_name = legacy.file_hash, legacy.json_bytes, legacy.safe_name
sha, canonical, require = legacy.sha, legacy.canonical, legacy.require
PacketInvalid, Packet = legacy.PacketInvalid, legacy.Packet
ARMS, VERDICT_FIELDS = legacy.ARMS, legacy.VERDICT_FIELDS
_native, _verdict = legacy._native, legacy._verdict



V2_GPU_CASES = legacy.GPU_CASES["policy"] | {
    "test_preflight_uses_lossless_registered_geometry_and_releases_memory",
    "test_preflight_rejects_missing_authorization_before_model_construction",
}


def _preflight(packet, campaign, manifest, spec, job):
    record = packet.json(BASE + "gpu_preflight_v2.json")
    require(record == campaign.get("gpu_preflight") and record.get("schema") == "cas-meta2-gpu-preflight/2"
            and record.get("status") == "CAS_META_2_V2_GPU_PREFLIGHT_PASSED" and record.get("completed") is True,
            "V2_REAL_GEOMETRY_PREFLIGHT_REQUIRED")
    require(record["source_sha256"] == manifest["files_sha256"][profiles.PILOT + "/cas_meta2/gpu_preflight_v2.py"]
            and record["aws_job_id"] == job, "V2_PREFLIGHT_SOURCE_OR_JOB_MISMATCH")
    require(record["optimizer_updates"] == 0 and record["model_training_performed"] is False
            and record["native_execution_performed"] is False and record["held_out_labels_accessed"] is False,
            "V2_PREFLIGHT_SCOPE_MISMATCH")
    runtime = packet.json("cloud_job/runtime.json")
    require(record["device"] in ("cuda", "cuda:0") and record["gpu_name"] == runtime["gpu"]
            and "RTX PRO 4500" in record["gpu_name"] and "T4" not in record["gpu_name"],
            "V2_PREFLIGHT_CUDA_IDENTITY_MISMATCH")
    require(record["config"] == spec["training"], "V2_PREFLIGHT_REGISTERED_CONFIG_MISMATCH")
    training = packet.json(BASE + "dataset/train.json")
    config = spec["training"]
    tokenizer = LosslessPublicTokenizer.fit_train([task["public"] for task in training],
                                                  max_length=config["policy"]["max_length"])
    lengths = [len(tokenizer.encode_public(task["public"])["ids"]) for task in training]
    actions = [len(action_to_ids(task["target"], max_length=config["policy"]["max_action_length"])) for task in training]
    indices = sorted(range(len(training)), key=lambda index: (-lengths[index], index))[:16]
    geometry = record["geometry"]
    expected = {
        "training_examples": 768, "batch_size": 16,
        "selected_training_indices": indices, "selected_input_lengths": [lengths[index] for index in indices],
        "selected_action_lengths_including_bos_eos": [actions[index] for index in indices],
        "maximum_training_input_tokens": max(lengths),
        "maximum_training_action_tokens_including_bos_eos": max(actions),
        "maximum_selected_action_tokens_including_bos_eos": max(actions[index] for index in indices),
        "configured_input_limit": config["policy"]["max_length"],
        "configured_action_limit": config["policy"]["max_action_length"],
        "tokenizer_digest": tokenizer.digest, "vocabulary_size": len(tokenizer.vocabulary),
        "training_public_sha256": sha(canonical([task["public"] for task in training])),
        "selected_target_sha256": sha(canonical([training[index]["target"] for index in indices])),
        "actual_padded_input_tokens": max(lengths[index] for index in indices),
        "actual_padded_target_tokens_excluding_bos": max(actions[index] for index in indices) - 1,
    }
    require(all(geometry.get(key) == value for key, value in expected.items()), "V2_PREFLIGHT_LONGEST_BATCH_GEOMETRY_MISMATCH")
    matching = record["parameter_matching"]
    counts = (matching["cas_trainable_parameters"], matching["generic_trainable_parameters"])
    require(all(type(value) is int and value > 0 for value in counts), "V2_PREFLIGHT_PARAMETER_COUNTS_INVALID")
    difference = abs(counts[0] - counts[1]) / counts[0]
    require(matching["frozen_candidate_parameter_names"] == [] and difference <= .01
            and math.isclose(matching["relative_difference"], difference, abs_tol=1e-12),
            "V2_PREFLIGHT_PARAMETER_MATCH_MISMATCH")
    common = record["identical_common_initial_parameter_names"]
    require(type(common) is list and common and common == sorted(set(common))
            and all(type(name) is str for name in common), "V2_PREFLIGHT_COMMON_INITIAL_PARAMETERS_MISSING")
    require(set(record["families"]) == {"cas", "generic"}, "V2_PREFLIGHT_FAMILY_COVERAGE")
    for family, value in record["families"].items():
        require(value["all_parameters_cuda"] is True and value["all_buffers_cuda"] is True
                and value["optimizer_updates"] == 0
                and value["all_trainable_parameter_tensors_have_finite_nonzero_gradient"] is True
                and value["missing_or_invalid_gradient_parameter_names"] == [],
                "V2_PREFLIGHT_GRADIENT_OR_DEVICE_FAILURE")
        names = value["finite_nonzero_gradient_parameter_names"]
        require(type(names) is list and names and names == sorted(set(names))
                and set(common) <= set(names), "V2_PREFLIGHT_GRADIENT_NAMES_INCOMPLETE")
        loss = value["diagnostic_token_cross_entropy"]
        require(type(loss) in (int, float) and math.isfinite(loss) and loss >= 0, "V2_PREFLIGHT_LOSS_INVALID")
    gates = record["families"]["cas"]["gate_layers"]
    require(len(gates) == config["policy"]["layers"] and [gate["layer"] for gate in gates] == list(range(len(gates))),
            "V2_PREFLIGHT_GATE_LAYER_COVERAGE")
    per_head_queries = sum(lengths[index] for index in indices)
    for gate in gates:
        heads = gate["active_queries_per_head"]
        require(type(heads) is list and len(heads) == config["policy"]["heads"]
                and all(type(value) is int and 0 < value <= per_head_queries for value in heads),
                "V2_PREFLIGHT_INACTIVE_HEAD")
        require(gate["valid_queries"] == per_head_queries * len(heads)
                and gate["active_queries"] == sum(heads)
                and math.isclose(gate["active_fraction"], sum(heads) / gate["valid_queries"], abs_tol=1e-12)
                and .95 <= gate["active_fraction"] <= 1, "V2_PREFLIGHT_ACTIVE_GATE_REQUIREMENT")
    require(record["families"]["generic"]["gate_layers"] == [], "V2_PREFLIGHT_GENERIC_GATE_CLAIM")
    memory = ("gpu_total_memory_bytes", "cuda_allocated_bytes_before", "cuda_reserved_bytes_before",
              "peak_cuda_allocated_bytes", "peak_cuda_reserved_bytes",
              "cuda_allocated_bytes_after_cleanup", "cuda_reserved_bytes_after_cleanup")
    require(all(type(record[key]) is int and record[key] >= 0 for key in memory), "V2_PREFLIGHT_MEMORY_COUNTS_INVALID")
    require(0 < record["peak_cuda_allocated_bytes"] <= record["peak_cuda_reserved_bytes"] <= record["gpu_total_memory_bytes"]
            and record["cuda_allocated_bytes_after_cleanup"] <= record["cuda_allocated_bytes_before"]
            and record["cuda_reserved_bytes_after_cleanup"] <= record["peak_cuda_reserved_bytes"]
            and "cleanup_failure" not in record, "V2_PREFLIGHT_MEMORY_CLEANUP_UNCONFIRMED")
    return {"training_examples": 768, "longest_batch": 16, "tokenizer_digest": tokenizer.digest,
            "source_sha256": record["source_sha256"], "active_gate_layers": len(gates),
            "peak_cuda_allocated_bytes": record["peak_cuda_allocated_bytes"],
            "boundary": "Recorded CUDA preflight bound to exact source and training geometry; no local tensor/gradient reproduction."}


def _gpu_gate(packet, family):
    if family == 'contract':
        return legacy._gpu_gate(packet, family)
    require(family == 'policy', 'V2_UNKNOWN_GPU_GATE')
    prefix = "cloud_job/gpu_" + family
    receipt = packet.json(prefix + "_receipt.json")
    require(receipt == {"passed": 6, "tests": 6, "failures": 0, "errors": 0, "skipped": 0},
            "GPU_GATE_RECEIPT_NOT_FOUR_PASSED:" + family)
    raw = packet.raw(prefix + "_tests.xml", 2 * 1024**2)
    require(b"<!DOCTYPE" not in raw.upper() and b"<!ENTITY" not in raw.upper(), "XML_DECLARATION_REFUSED")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as error:
        raise PacketInvalid("GPU_GATE_XML_INVALID:" + family) from error
    suites = list(root.iter("testsuite"))
    require(suites and all(not list(suite.iter("testsuite"))[1:] for suite in suites), "NESTED_GPU_TEST_SUITES_REFUSED")
    totals = {field: sum(int(suite.get(field, "0")) for suite in suites)
              for field in ("tests", "failures", "errors", "skipped")}
    cases = list(root.iter("testcase"))
    require(totals == {"tests": 6, "failures": 0, "errors": 0, "skipped": 0}, "GPU_GATE_XML_COUNTS_INVALID:" + family)
    require(len(cases) == 6 and {case.get("name") for case in cases} == V2_GPU_CASES,
            "GPU_GATE_CASE_IDENTITIES_INVALID:" + family)
    require(all(not any(child.tag in ("failure", "error", "skipped") for child in case) for case in cases),
            "GPU_GATE_HIDDEN_CASE_FAILURE:" + family)
    command = packet.json(prefix + "_command.json")
    require(type(command) is list and all(type(word) is str for word in command), "GPU_GATE_COMMAND_INVALID")
    expected = "tests/test_execution_contract.py" if family == "contract" else "tests/test_policy_gpu.py"
    require(expected in command and "tests/test_learning_v2_gpu.py" in command and "gpu" in command and "pytest" in command, "V2_GPU_GATE_COMMAND_MISMATCH")
    require(prefix + "_tests.log" in packet.inventory, "GPU_GATE_RAW_LOG_MISSING")
    return {"passed": 6, "tests": sorted(case.get("name") for case in cases)}

def _experiment_spec(manifest, path=None):
    require(type(manifest) is dict and "experiment" in manifest, "V2_EXPLICIT_MANIFEST_REQUIRED")
    path = Path(path or ROOT / "EXPERIMENT_V2.json").resolve()
    raw = path.read_bytes()
    experiment = profiles.validate_manifest(manifest, lambda name: raw)
    require(experiment is not None, "V2_PROFILE_REQUIRED")
    spec = profiles.validate_v2_spec(raw)
    require(spec["curriculum"]["seed"] == 20260917
            and spec["curriculum"]["counts"] == {"train": 768, "validation": 48, "test": 72},
            "V2_REGISTERED_CURRICULUM_REQUIRED")
    require(spec["training"]["seed"] == 7 and spec["training"]["epochs"] == 100
            and spec["training"]["validation_generation_interval"] == 5,
            "V2_REGISTERED_SELECTION_SCHEDULE_REQUIRED")
    require(spec["evaluation"]["arms"] == list(ARMS), "V2_REGISTERED_FIVE_ARMS_REQUIRED")
    return experiment, spec


def _source_binding(campaign, manifest, source_sha):
    experiment = profiles.validate_manifest(manifest)
    require(experiment is not None and campaign.get("experiment") == experiment, "V2_CAMPAIGN_EXPERIMENT_MISMATCH")
    source = campaign.get("source")
    require(type(source) is dict and source.get("EXPERIMENT_V2.json") == experiment["spec_sha256"],
            "V2_SPEC_SOURCE_BINDING_MISSING")
    # The frozen checker still verifies every top-level Python module and the
    # accepted baseline/wheels. Only the additional, separately checked spec is
    # removed from this detached view; original evidence is never modified.
    view = {**campaign, "source": {key: value for key, value in source.items() if key != "EXPERIMENT_V2.json"}}
    checked = legacy._source_binding(view, manifest, source_sha)
    return {**checked, "source_files_bound": checked["source_files_bound"] + 1, "experiment": experiment}


def _command(packet, experiment, smoke_only):
    argv = packet.json("cloud_job/command.json")
    require(type(argv) is list and all(type(item) is str for item in argv) and len(argv) in (7, 8),
            "V2_CAMPAIGN_COMMAND_INVALID")
    require(argv[1:3] == ["-m", experiment["entrypoint"]] and argv[3] == "--output"
            and argv[4].endswith("/research/CAS_META_2_COMPOSITION/runs/cloud_job/campaign")
            and argv[5] == "--max-wall-seconds" and re.fullmatch(r"[0-9]+", argv[6]) is not None
            and 60 <= int(argv[6]) <= 6600, "V2_ENTRYPOINT_OR_COMMAND_BINDING_MISMATCH")
    require(argv[7:] == (["--smoke-only"] if smoke_only else []), "V2_COMMAND_MODE_MISMATCH")
    return {"entrypoint": argv[2], "max_wall_seconds": int(argv[6]), "smoke_only": smoke_only}


def _dataset(packet, spec):
    manifest = packet.json(BASE + "dataset/dataset_manifest.json")
    require(manifest.get("schema") == "cas-meta2-dataset-manifest/2"
            and manifest.get("seed") == spec["curriculum"]["seed"], "V2_DATASET_SCHEMA_OR_SEED_MISMATCH")
    expected = {"train.json", "validation.json", "test_public.json", "test_private.json"}
    require(type(manifest.get("sha256")) is dict and set(manifest["sha256"]) == expected,
            "V2_DATASET_HASH_COVERAGE_MISMATCH")
    for name, checksum in manifest["sha256"].items():
        packet.same_hash(BASE + "dataset/" + name, checksum)
    counts = spec["curriculum"]["counts"]
    require(manifest.get("counts") == counts, "V2_DATASET_DECLARED_COUNTS_MISMATCH")
    for name, split in (("train.json", "train"), ("validation.json", "validation"), ("test_public.json", "test")):
        values = packet.json(BASE + "dataset/" + name)
        require(type(values) is list and len(values) == counts[split], "V2_DATASET_PARTITION_COUNT_MISMATCH")
    return manifest


def _training_v2(packet, campaign, spec, manifest, seal):
    training = packet.json(BASE + "training_receipt.json")
    require(training == campaign.get("training"), "TRAINING_RECEIPT_COPY_MISMATCH")
    prereg = packet.json(BASE + "training_preregistration.json")
    require(prereg.get("schema") == "cas-meta2-learning-preregistration/2", "V2_PREREGISTRATION_SCHEMA_REQUIRED")
    config, registered = prereg["config"], spec["training"]
    require(type(config) is dict and set(config) == set(registered), "V2_TRAINING_CONFIG_FIELDS_MISMATCH")
    for name, expected in registered.items():
        if name == "max_training_seconds":
            require(type(config[name]) is int and 1 <= config[name] <= expected, "V2_TRAINING_TIME_ALLOCATION_INVALID")
        else:
            require(config[name] == expected, "V2_TRAINING_CONFIG_MISMATCH:" + name)
    require(prereg["train_examples"] == 768 and prereg["validation_examples"] == 48 and prereg["test_examples"] == 72,
            "V2_PREREGISTERED_COUNTS_MISMATCH")
    require(prereg["arms"] == list(ARMS) and prereg["dataset_sha256"] == manifest["sha256"], "V2_PREREGISTERED_INPUT_MISMATCH")
    train = packet.json(BASE + "dataset/train.json")
    validation_tasks = packet.json(BASE + "dataset/validation.json")
    publics = packet.json(BASE + "dataset/test_public.json")
    require(len(train) == 768 and len(validation_tasks) == 48 and len(publics) == 72, "V2_LEARNING_COUNTS_MISMATCH")
    tokenizer_record = packet.json(BASE + "tokenizer.json")
    tokenizer = LosslessPublicTokenizer.from_dict(tokenizer_record)
    rebuilt = LosslessPublicTokenizer.fit_train([task["public"] for task in train], max_length=config["policy"]["max_length"])
    require(tokenizer_record == rebuilt.to_dict() and tokenizer.digest == seal["tokenizer_digest"],
            "V2_TOKENIZER_NOT_EXACTLY_TRAIN_FITTED")
    round_trips = [task["public"] for task in train + validation_tasks] + publics
    for public in round_trips:
        require(tokenizer.check_round_trip(public) is True, "V2_PUBLIC_TEXT_ROUND_TRIP_FAILED")
    checkpoints = packet.json(BASE + "checkpoints.json")
    require(checkpoints == training["checkpoints"] and set(checkpoints) == {"cas", "generic"}, "V2_CHECKPOINT_RECEIPT_MISMATCH")
    complete = training["completed_epochs"]
    require(type(complete) is int and 1 <= complete <= training["requested_epochs"] == registered["epochs"],
            "V2_COMPLETED_EPOCHS_INVALID")
    require(training["learning_conditions_matched"] is True, "V2_MATCHED_LEARNING_REQUIRED")
    steps_per_epoch = math.ceil(768 / config["batch_size"])
    require(training["optimizer_steps"] == {family: complete * steps_per_epoch for family in ("cas", "generic")},
            "V2_OPTIMIZER_STEPS_MISMATCH")
    history = packet.json(BASE + "training_history.json")
    require(type(history) is list and len(history) == complete
            and [row["epoch"] for row in history] == list(range(1, complete + 1)), "V2_HISTORY_COVERAGE_MISMATCH")
    eligible = {epoch for epoch in range(1, complete + 1)
                if epoch == 1 or epoch % registered["validation_generation_interval"] == 0 or epoch == registered["epochs"]}
    expected_files = {BASE + f"validation_predictions/{family}_epoch_{epoch:04d}.json"
                      for family in ("cas", "generic") for epoch in eligible}
    actual_files = {name for name in packet.inventory if name.startswith(BASE + "validation_predictions/")}
    optional_initial = {BASE + f"validation_predictions/{family}_epoch_0000.json" for family in ("cas", "generic")}
    require(expected_files <= actual_files <= expected_files | optional_initial, "V2_VALIDATION_PREDICTION_COVERAGE_MISMATCH")
    checkpoint_digests, selected_epochs = {}, {}
    for family in ("cas", "generic"):
        require(set(checkpoints[family]) == {"initial", "selected", "last"}, "V2_SIX_CHECKPOINTS_REQUIRED")
        best_epoch, best_key = None, None
        for row in history:
            epoch = row["epoch"]
            require(row["optimizer_steps"] == {name: epoch * steps_per_epoch for name in ("cas", "generic")},
                    "V2_EPOCH_STEP_COUNT_MISMATCH")
            require(set(row["families"]) == {"cas", "generic"}, "V2_HISTORY_FAMILY_COVERAGE_MISMATCH")
            family_row = row["families"][family]
            score = family_row["validation"]
            require(type(score["token_cross_entropy"]) in (int, float)
                    and math.isfinite(score["token_cross_entropy"]) and score["token_cross_entropy"] >= 0,
                    "V2_VALIDATION_LOSS_INVALID")
            changed = False
            if epoch in eligible:
                saved = packet.json(BASE + f"validation_predictions/{family}_epoch_{epoch:04d}.json")
                require(saved["epoch"] == epoch and saved["split"] == "validation"
                        and saved["test_gold_access"] is False, "V2_VALIDATION_PREDICTION_ROLE_MISMATCH")
                recomputed = generated_metrics(saved["actions"], validation_tasks)
                require(saved["metrics"] == recomputed == score.get("generation"), "V2_GENERATED_VALIDATION_METRICS_MISMATCH")
                key = selection_key(score)
                changed = best_key is None or key > best_key
                if changed:
                    best_epoch, best_key = epoch, key
            else:
                require("generation" not in score, "V2_INELIGIBLE_GENERATION_RECORDED")
            require(type(family_row["selected"]) is bool and family_row["selected"] is changed,
                    "V2_EPOCH_SELECTION_HISTORY_MISMATCH")
        selected_epochs[family] = best_epoch
        for state, suffix in (("initial", "initial"), ("selected", "best"), ("last", "last")):
            row = checkpoints[family][state]
            name = f"candidate_{family}_{suffix}.pt"
            require(row.get("schema") == "cas-meta2-candidate-checkpoint/2", "V2_DECLARED_CHECKPOINT_SCHEMA_REQUIRED")
            require(type(row["path"]) is str and row["path"].endswith("/" + name), "V2_CHECKPOINT_PATH_MISMATCH")
            packet.same_hash(BASE + name, row["sha256"])
            require(type(row["bytes"]) is int and row["bytes"] > 0
                    and row["bytes"] == packet.inventory[BASE + name]["bytes"], "V2_CHECKPOINT_SIZE_MISMATCH")
            expected_epoch = 0 if state == "initial" else best_epoch if state == "selected" else complete
            require(type(row["epoch"]) is int and row["epoch"] == expected_epoch
                    and type(row["optimizer_steps"]) is int and row["optimizer_steps"] == expected_epoch * steps_per_epoch,
                    "V2_SELECTED_CHECKPOINT_EPOCH_OR_STEPS_MISMATCH")
            if state != "initial":
                require(row["validation"] == history[expected_epoch - 1]["families"][family]["validation"],
                        "V2_CHECKPOINT_VALIDATION_COPY_MISMATCH")
            checkpoint_digests[name] = row["sha256"]
        initial_path = BASE + f"validation_predictions/{family}_epoch_0000.json"
        if initial_path in actual_files:
            saved = packet.json(initial_path)
            require(saved["epoch"] == 0 and saved["split"] == "validation" and saved["test_gold_access"] is False,
                    "V2_INITIAL_VALIDATION_ROLE_MISMATCH")
            derived = generated_metrics(saved["actions"], validation_tasks)
            require(saved["metrics"] == derived == checkpoints[family]["initial"]["validation"]["generation"],
                    "V2_INITIAL_VALIDATION_METRICS_MISMATCH")
    matching = packet.json(BASE + "parameter_matching.json")
    require(matching == training["parameter_matching"], "PARAMETER_MATCHING_RECEIPT_MISMATCH")
    counts = (matching["cas_trainable_parameters"], matching["generic_trainable_parameters"])
    require(all(type(count) is int and count > 0 for count in counts), "PARAMETER_COUNTS_INVALID")
    mismatch = abs(counts[0] - counts[1]) / counts[0]
    require(mismatch <= registered["policy"]["max_parameter_mismatch_fraction"]
            and math.isclose(mismatch, matching["relative_difference"], abs_tol=1e-12), "ACTIVE_PARAMETER_MATCH_INVALID")
    gradients = packet.json(BASE + "gradient_connectivity.json")
    require(gradients == training["active_parameters"], "GRADIENT_RECEIPT_COPY_MISMATCH")
    for family, count in zip(("cas", "generic"), counts, strict=True):
        require(gradients[family]["all_parameter_tensors_connected"] is True
                and gradients[family]["connected_trainable_parameters"] == count
                and gradients[family]["trainable_parameters"] == count, "GRADIENT_CONNECTIVITY_INCOMPLETE")
    return {"checkpoint_sha256": checkpoint_digests, "completed_epochs": complete,
            "selected_epochs": selected_epochs, "eligible_epochs": sorted(eligible),
            "validation_examples_recounted_per_generation": 48, "public_text_round_trips": len(round_trips),
            "checkpoint_contents_loaded": False, "checkpoint_schema_boundary": "Declared JSON format and source-bound writer checked; binary checkpoint payloads were not parsed."}

def _full(packet, campaign, spec):
    _dataset(packet, spec)
    require(campaign.get("evaluation_completed") is True and campaign.get("all_test_cases_evaluated_per_arm") == 72
            and campaign.get("reference_cases") == 72 and campaign.get("arm_verdicts") == 360, "FULL_DENOMINATORS_INVALID")
    seal = packet.json(BASE + "predictions_seal.json")
    require(seal == campaign.get("prediction_seal"), "PREDICTION_SEAL_COPY_MISMATCH")
    require(seal.get("test_private_labels_loaded") is False and set(seal.get("arms", [])) == set(ARMS)
            and seal.get("test_examples") == 72 and seal.get("prediction_count") == 360, "PREDICTION_SEAL_COUNTS_INVALID")
    packet.same_hash(BASE + "predictions.jsonl", seal["sha256"])
    opening = packet.json(BASE + "test_gold_opening_receipt.json")
    require(opening["prediction_sha256_before_opening"] == seal["sha256"]
            and opening["test_private_sha256"] == seal["test_private_sha256"], "GOLD_OPENING_DIGEST_MISMATCH")
    require(datetime.fromisoformat(opening["opened_utc"]) > datetime.fromisoformat(seal["sealed_utc"]),
            "GOLD_OPENED_BEFORE_SEAL")
    manifest = packet.json(BASE + "dataset/dataset_manifest.json")
    for name, digest in manifest["sha256"].items():
        require(name in ("train.json", "validation.json", "test_public.json", "test_private.json"), "DATASET_FILENAME_INVALID")
        packet.same_hash(BASE + "dataset/" + name, digest)
    packet.same_hash(BASE + "dataset/test_public.json", seal["test_public_sha256"])
    packet.same_hash(BASE + "dataset/test_private.json", seal["test_private_sha256"])
    publics = packet.json(BASE + "dataset/test_public.json")
    private = packet.json(BASE + "dataset/test_private.json")
    predictions = [json_bytes(line) for line in packet.raw(BASE + "predictions.jsonl").splitlines()]
    require(len(publics) == len(private) == len(predictions) == 72, "TEST_CASE_MAPPING_COUNT_INVALID")
    for index, (public, task, prediction) in enumerate(zip(publics, private, predictions, strict=True)):
        require(task["public"] == public and prediction.get("case_index") == index
                and prediction.get("public_sha256") == sha(canonical(public))
                and set(prediction.get("actions", {})) == set(ARMS), "TEST_CASE_MAPPING_INVALID")
    training_details = _training_v2(packet, campaign, spec, manifest, seal)
    checkpoint_digests = training_details["checkpoint_sha256"]
    training = packet.json(BASE + "training_receipt.json")
    preflight = packet.json(BASE + "gpu_preflight_v2.json")
    require(preflight["parameter_matching"] == training["parameter_matching"],
            "V2_PREFLIGHT_TRAINING_PARAMETER_MATCH_MISMATCH")
    evaluated = packet.json(BASE + "evaluation_results.json")
    cases = evaluated["cases"]
    require(len(cases) == 72 and sorted(row["case_index"] for row in cases) == list(range(72)), "EVALUATION_CASE_COVERAGE_INVALID")
    rows_by_arm = {arm: [] for arm in ARMS}
    for case in cases:
        index = case["case_index"]
        folder = BASE + f"evaluation/case_{index:04d}"
        require(case == packet.json(folder + "/case_receipt.json"), "EVALUATION_CASE_COPY_MISMATCH")
        reference = packet.json(folder + "/reference_result.json")
        require(reference["selected_action"] == private[index]["target"], "PRIVATE_REFERENCE_TARGET_MISMATCH")
        _native(packet, reference, folder + "/reference", reference=True)
        require(case["reference_verification"] == packet.json(folder + "/reference_verdict.json"), "REFERENCE_VERDICT_COPY_MISMATCH")
        _verdict(case["reference_verification"], correct=True)
        require(set(case["arms"]) == set(ARMS), "EVALUATION_ARM_COVERAGE_INVALID")
        for arm in ARMS:
            row = case["arms"][arm]
            arm_folder = folder + "/" + arm
            require(row == packet.json(arm_folder + "/case_receipt.json"), "ARM_RECEIPT_COPY_MISMATCH")
            require(row["case_index"] == index and row["arm"] == arm
                    and row["action"] == predictions[index]["actions"][arm], "PREDICTION_EXECUTION_ACTION_MISMATCH")
            verdict = row["verification"]
            require(verdict == packet.json(arm_folder + "/verification.json"), "ARM_VERDICT_COPY_MISMATCH")
            _verdict(verdict)
            require(verdict.get("repair_required") is False and verdict.get("repair_success") is None,
                    "UNSUPPORTED_REPAIR_CLAIM_IN_META2_RUN_CALL_PILOT")
            result = packet.json(arm_folder + "/execution_result.json")
            require(result["status"] == row["execution_status"], "EXECUTION_STATUS_MISMATCH")
            if row["model_rejection"] is True:
                require(result["status"] == "REJECTED" and not any(verdict[key] for key in VERDICT_FIELDS),
                        "REJECTED_PROGRAM_COUNTED_CORRECT")
            else:
                require(row["model_rejection"] is False and result["selected_action"] == row["action"], "EXECUTION_ACTION_MISMATCH")
                count = _native(packet, result, arm_folder + "/native", reference=False)
                require(verdict["native_runs"] == count and verdict["reserved_policy_units"] == result["reserved_policy_units"],
                        "NATIVE_COMPUTE_COUNTS_MISMATCH")
            rows_by_arm[arm].append(row)
    metrics = {}
    require(evaluated["results"] == campaign["results"] and set(evaluated["results"]) == set(ARMS), "METRIC_RECEIPT_COPY_MISMATCH")
    for arm, rows in rows_by_arm.items():
        counted = {key: sum(row["verification"][key] for row in rows) for key in VERDICT_FIELDS}
        saved = evaluated["results"][arm]
        require(saved["total"] == 72 and saved["all_cases_in_denominator"] is True, "ARM_DENOMINATOR_INVALID")
        require(all(type(saved[key]) is int for key in VERDICT_FIELDS), "METRIC_COUNTER_TYPE_INVALID")
        require(all(saved[key] == value for key, value in counted.items()), "RECORDED_METRIC_RECOUNT_MISMATCH")
        for key, expected in (
            ("model_rejections", sum(row["model_rejection"] for row in rows)),
            ("native_executed", sum(row["execution_status"] == "EXECUTED" for row in rows)),
            ("native_runs", sum(row["verification"].get("native_runs", 0) for row in rows)),
            ("reserved_policy_units", sum(row["verification"].get("reserved_policy_units", 0) for row in rows)),
        ):
            require(saved[key] == expected, "RECORDED_COMPUTE_RECOUNT_MISMATCH:" + key)
        require(math.isclose(saved["task_accuracy"], counted["task_correct"] / 72, abs_tol=1e-12), "TASK_ACCURACY_MISMATCH")
        require(saved["repair_required_total"] == 0 and saved["repair_success"] is None, "UNSUPPORTED_REPAIR_AGGREGATE")
        metrics[arm] = {"total": 72, **counted, "task_accuracy": counted["task_correct"] / 72,
                        "model_rejections": saved["model_rejections"], "native_runs": saved["native_runs"]}
    for family in ("cas", "generic"):
        gain = metrics[family + "_trained"]["task_accuracy"] - metrics[family + "_untrained"]["task_accuracy"]
        require(math.isclose(campaign[family + "_task_accuracy_gain"], gain, abs_tol=1e-12), "TASK_ACCURACY_GAIN_MISMATCH")
    group_counts = _groups(packet, campaign, private, cases, spec)
    payload = packet.json(BASE + "payload_sha256.json")
    actual_payload = {name.removeprefix(BASE): row["sha256"] for name, row in packet.inventory.items()
                      if name.startswith(BASE) and name != BASE + "payload_sha256.json"}
    require(payload == actual_payload, "CAMPAIGN_PAYLOAD_HASH_COVERAGE_MISMATCH")
    return {"cases": 72, "arm_verdicts": 360, "metrics": metrics,
            "checkpoint_sha256": checkpoint_digests, "checkpoint_contents_loaded": False,
            "completed_epochs": training["completed_epochs"], "learning_v2": training_details, "evaluation_groups": group_counts}


def _groups(packet, campaign, private, cases, spec):
    document = packet.json(BASE + "evaluation_groups.json")
    require(document.get("schema") == "cas-meta2-group-results/2"
            and document.get("groups") == campaign.get("evaluation_groups"), "V2_GROUP_RECEIPT_COPY_MISMATCH")
    expected = spec["curriculum"]["test_groups"]
    require(expected == {"same_depth": 24, "wording_shift": 24, "deeper_calls": 24}, "V2_REGISTERED_GROUPS_MISMATCH")
    indices = {group: [index for index, task in enumerate(private)
                      if task["provenance"]["evaluation_group"] == group] for group in expected}
    require({group: len(rows) for group, rows in indices.items()} == expected
            and sorted(index for rows in indices.values() for index in rows) == list(range(72))
            and document["group_case_indices"] == indices and set(document["groups"]) == set(expected),
            "V2_GROUP_CASE_MAPPING_MISMATCH")
    by_index = {case["case_index"]: case for case in cases}
    for group, members in indices.items():
        saved = document["groups"][group]
        require(set(saved) == set(ARMS), "V2_GROUP_ARM_COVERAGE_MISMATCH")
        for arm in ARMS:
            rows = [by_index[index]["arms"][arm] for index in members]
            counted = {key: sum(row["verification"][key] for row in rows) for key in VERDICT_FIELDS}
            counted.update(model_rejections=sum(row["model_rejection"] for row in rows),
                native_executed=sum(row["execution_status"] == "EXECUTED" for row in rows),
                native_runs=sum(row["verification"].get("native_runs", 0) for row in rows),
                reserved_policy_units=sum(row["verification"].get("reserved_policy_units", 0) for row in rows))
            require(saved[arm]["total"] == len(rows) and saved[arm]["all_cases_in_denominator"] is True
                    and all(type(saved[arm][key]) is int and saved[arm][key] == value for key, value in counted.items())
                    and math.isclose(saved[arm]["task_accuracy"], counted["task_correct"] / len(rows), abs_tol=1e-12)
                    and saved[arm]["repair_required_total"] == 0 and saved[arm]["repair_success"] is None,
                    "V2_GROUP_METRIC_RECOUNT_MISMATCH")
    return expected


def _audit_code_hashes():
    paths = [Path(__file__), Path(legacy.__file__), Path(profiles.__file__),
             ROOT / "cas_meta2/features_v2.py", ROOT / "cas_meta2/selection_v2.py", ROOT / "cas_meta2/codec.py"]
    return {str(path.resolve()): file_hash(path) for path in paths}


def inspect_packet(path, *, expected_sha256, source_sha, job, output, source_manifest=None,
                   source_archive_sha256=None, extract=None, experiment_spec=None):
    if type(source_manifest) is dict:
        wrapper = source_manifest
        source_manifest = wrapper.get("launch_manifest", wrapper.get("manifest", wrapper))
        source_archive_sha256 = source_archive_sha256 or wrapper.get("archive_sha256")
    experiment, spec = _experiment_spec(source_manifest, experiment_spec)
    audit_code = _audit_code_hashes()
    require(type(expected_sha256) is str and SHA256.fullmatch(expected_sha256), "EXPECTED_PACKET_SHA256_REQUIRED")
    require(type(source_sha) is str and SHA1.fullmatch(source_sha), "EXPECTED_SOURCE_SHA_REQUIRED")
    require(type(job) is str and re.fullmatch(r"[A-Za-z0-9._-]{1,160}", job), "EXPECTED_JOB_ID_REQUIRED")
    path = Path(path).resolve()
    require(path.is_file() and 0 < path.stat().st_size <= MAX_COMPRESSED, "COMPRESSED_SIZE_CEILING")
    require(file_hash(path) == expected_sha256, "PACKET_SHA256_MISMATCH")
    output = legacy._new_output(output)
    target = legacy._new_output(extract, extracted=True) if extract is not None else None
    if target is not None:
        require(not output.is_relative_to(target) and not target.is_relative_to(output), "INSPECTION_EXTRACTION_PATH_OVERLAP")
    with zipfile.ZipFile(path) as archive:
        infos, expanded = legacy._safe_infos(archive)
        inventory = []
        for name, info in sorted(infos.items()):
            if info.is_dir():
                continue
            digest, count = hashlib.sha256(), 0
            with archive.open(info) as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    count += len(block)
                    require(count <= info.file_size, "MEMBER_SIZE_EXCEEDS_HEADER")
                    digest.update(block)
            require(count == info.file_size, "MEMBER_SIZE_MISMATCH")
            inventory.append({"path": name, "bytes": count, "sha256": digest.hexdigest()})
        packet = Packet(archive, infos, inventory)
        collection, index_verified = legacy._collection(packet, job, source_sha, source_archive_sha256)
        require(collection.get("experiment") == experiment, "V2_COLLECTION_EXPERIMENT_MISMATCH")
        issues, details = [], {}
        campaign = packet.json(BASE + "campaign_receipt.json") if BASE + "campaign_receipt.json" in packet.inventory else None
        remote_job = packet.json("cloud_job/job.json") if "cloud_job/job.json" in packet.inventory else None
        if remote_job is not None:
            require(all(remote_job.get(key) == collection.get(key) for key in ("job", "source_sha", "baseline_sha", "archive_sha256", "smoke_only", "experiment")),
                    "REMOTE_JOB_COLLECTION_IDENTITY_MISMATCH")
        run_status = "PARTIAL_EVIDENCE" if collection["partial_evidence"] else "FAILED_RUN"
        claimed_complete = collection["returncode"] == 0
        if claimed_complete:
            def check(label, operation):
                try:
                    details[label] = operation()
                except (PacketInvalid, KeyError, IndexError, AttributeError, TypeError, ValueError, OverflowError) as error:
                    issues.append(label + ":" + str(error))
            check("gpu_contract", lambda: legacy._gpu_gate(packet, "contract"))
            check("gpu_policy", lambda: _gpu_gate(packet, "policy"))
            check("environment", lambda: legacy._environment(packet))
            check("source_binding", lambda: _source_binding(campaign, source_manifest, source_sha))
            check("command_binding", lambda: _command(packet, experiment, collection["smoke_only"]))
            check("dataset_v2", lambda: _dataset(packet, spec))
            check("gpu_preflight_v2", lambda: _preflight(packet, campaign, source_manifest, spec, job))
            check("smoke", lambda: legacy._smoke(packet, campaign))
            expected_status = "CAS_META_2_AWS_SMOKE_COMPLETED" if collection["smoke_only"] else "CAS_META_2_AWS_CAMPAIGN_COMPLETED"
            if not isinstance(campaign, dict) or campaign.get("status") != expected_status or campaign.get("completed") is not True:
                issues.append("campaign:COMPLETION_STATUS_MISMATCH")
            elif collection["smoke_only"]:
                if campaign.get("evaluation_completed") is not False or campaign.get("training_performed") is not False:
                    issues.append("campaign:SMOKE_MAKES_LEARNING_CLAIM")
                if any(name.startswith(BASE + "candidate_") and name.endswith(".pt") for name in packet.inventory):
                    issues.append("campaign:SMOKE_HAS_CANDIDATE_CHECKPOINT")
            else:
                check("full_evaluation", lambda: _full(packet, campaign, spec))
            if remote_job is None or remote_job.get("returncode") != 0:
                issues.append("job:SUCCESS_JOB_RECEIPT_MISSING_OR_FAILED")
            if source_archive_sha256 is None:
                issues.append("source_binding:INDEPENDENT_SOURCE_ARCHIVE_SHA256_REQUIRED")
            run_status = "EVIDENCE_MISMATCH" if issues else ("SMOKE_EVIDENCE_VERIFIED" if collection["smoke_only"] else "FULL_EVIDENCE_VERIFIED")
        else:
            for name in ("cloud_job/remote_failure.json", BASE + "campaign_receipt.json"):
                if name in packet.inventory:
                    details[name] = packet.json(name)
        extraction = legacy._extract(packet, target) if target is not None else None
        require(file_hash(path) == expected_sha256, "PACKET_CHANGED_DURING_INSPECTION")
    require(_audit_code_hashes() == audit_code, "V2_AUDIT_CODE_CHANGED_DURING_INSPECTION")
    inventory_document = {"schema": "cas-meta2-full-packet-index/1", "packet_sha256": expected_sha256,
                          "entries": inventory}
    inventory_payload = json.dumps(inventory_document, sort_keys=True, indent=2).encode("utf-8") + b"\n"
    output.mkdir(parents=True, exist_ok=False)
    (output / "full_member_index.json").write_bytes(inventory_payload)
    receipt = {
        "schema": "cas-meta2-packet-inspection/2", "status": "CAS_META_2_V2_PACKET_" + run_status,
        "experiment": experiment,
        "audit_code_sha256": audit_code,
        "packet": str(path), "packet_sha256": expected_sha256, "source_sha": source_sha, "job": job,
        "compressed_bytes": path.stat().st_size, "expanded_bytes": expanded, "member_files": len(inventory),
        "archive_safety_and_all_included_bytes_checked": True, "original_full_index_verified": index_verified,
        "collection": {key: collection[key] for key in ("returncode", "smoke_only", "partial_evidence",
                      "original_file_count", "included_full_file_count", "omitted_full_file_count",
                      "original_file_index_sha256", "archive_sha256")},
        "completed_run_evidence_verified": claimed_complete and not issues,
        "full_member_index": str(output / "full_member_index.json"),
        "full_member_index_sha256": sha(inventory_payload), "issues": issues,
        "checks": details, "extraction": extraction, "utc": datetime.now(timezone.utc).isoformat(),
        "checkpoint_loading_performed": False, "neural_execution_performed": False,
        "stored_semantic_reverification_performed": False,
        "boundary": "V2 byte bindings, lossless public-text round trips and recorded validation/result recount only. Native stored-record semantic rechecking remains a separate gate. No CAS advantage, general reasoning, complete CNCM or hardware claim.",
    }
    (output / "inspection_receipt.json").write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return receipt



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--job", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--source-archive-sha256")
    parser.add_argument("--experiment-spec", type=Path)
    parser.add_argument("--extract", type=Path)
    args = parser.parse_args()
    try:
        wrapper = json_bytes(args.source_manifest.read_bytes())
        manifest = wrapper.get("launch_manifest", wrapper.get("manifest", wrapper))
        archive_sha = args.source_archive_sha256 or wrapper.get("archive_sha256")
        receipt = inspect_packet(args.packet, expected_sha256=args.sha256, source_sha=args.source_sha,
            job=args.job, output=args.output, source_manifest=manifest,
            source_archive_sha256=archive_sha, extract=args.extract, experiment_spec=args.experiment_spec)
    except (PacketInvalid, ValueError, KeyError, OSError, zipfile.BadZipFile) as error:
        print(json.dumps({"status": "CAS_META_2_V2_PACKET_REJECTED", "reason": str(error)}))
        return 2
    print(json.dumps({"status": receipt["status"], "issues": receipt["issues"],
                      "neural_execution_performed": False}, indent=2))
    return 0 if receipt["completed_run_evidence_verified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
