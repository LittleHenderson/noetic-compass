"""Verify caller-pinned, downloaded smoke evidence using standard-library data reads.

Never imports project, model, numerical or provider modules; never decodes a
checkpoint. Run only after the caller supplies the actual lifecycle result pin.
This checks recorded execution evidence, not an independent numerical rerun.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from io import BytesIO
import json
import math
from pathlib import Path, PurePosixPath
import re
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
RECORDS = Path(__file__).resolve().parent
PACKAGE_RECORDS = ROOT / "research/CAS_META_2_COMPOSITION/records/ingestion_smoke_001"
CANDIDATE = "CNCM_ORDERED_INGESTION_SMOKE_001"
PREFIX = "cncm-ordered-ingestion-smoke-"
BOUNDS = {"training": True, "optimizer_updates_max": 64, "max_wall_seconds": 1200,
          "jobs": 1, "automatic_retries": 0, "reservation_usd": "7.00",
          "instance_type": "g7.2xlarge", "region": "us-west-2"}
ARTIFACTS = {"origin.pt", "initial.pt", "final.pt", "initial_checkpoint.json", "final_checkpoint.json",
             "before_predictions.json", "after_predictions.json", "initial_reload_predictions.json",
             "final_reload_predictions.json", "receipt.json", "installed_sources.json",
             "worker_report.json", "measurements.json"}
SMOKE_SCHEMA = "cncm.rpa-learning-smoke/0.2"
MECHANICAL = "MECHANICAL_SMOKE_AND_RELOAD_OBSERVED"
SEAL_SCHEMA = "cncm.rpa-public-predictions/0.1"
IDENTITY = {"job", "source_sha", "archive_sha256", "manifest_sha256"}
METADATA_FIELDS = {"schema_version", "kind", "seed", "model_context", "tokenizer", "ordered_profile",
    "scope", "parameter_names", "training_requests", "source_binding", "prepared_ids", "legacy_input_ids",
    "optimizer_class", "learning_rate", "model_identity", "optimizer_identity", "projection_identity"}
SOURCE_CONTEXT_FIELDS = {"source_file_sha256", "source_bundle_digest", "source_receipt_digest", "source_namespace",
    "source_context_id", "base_current_state_id", "rendering_schema", "source_authorship_authenticated", "world_truth_established"}


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False) + "\n").encode()


def digest(raw):
    return sha256(raw).hexdigest()


def same(left, right, reason):
    require(canonical(left) == canonical(right), reason)


def closed(value, keys, reason):
    require(type(value) is dict and set(value) == set(keys), reason)


def integer(value, low, high, reason):
    require(type(value) is int and low <= value <= high, reason)


def hex64(value):
    require(type(value) is str and re.fullmatch(r"[a-f0-9]{64}", value), "SHA256_FORMAT")


def safe_relative(value):
    require(type(value) is str and 0 < len(value) <= 1024, "PATH_TYPE_OR_LENGTH")
    path = PurePosixPath(value)
    require(not path.is_absolute() and path.as_posix() == value and path.parts
            and not any(p in {".", ".."} or p.endswith((".", " ")) for p in path.parts)
            and not any(c in value for c in "\\:\x00"), "UNSAFE_RELATIVE_PATH")
    return value


def parse(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "DUPLICATE_JSON_KEY")
            result[key] = value
        return result
    def constant(value):
        raise ValueError("NONFINITE_JSON:" + value)
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


class Audit:
    def __init__(self):
        self.files = {}
        self.checks = []

    def raw(self, path, maximum=64 * 1024**2):
        path = Path(path).absolute()
        require(path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(ROOT), "LOCAL_FILE_SCOPE")
        require(path.stat().st_size <= maximum, "LOCAL_FILE_BOUND")
        raw = path.read_bytes()
        pin = {"path": str(path), "bytes": len(raw), "sha256": digest(raw)}
        if str(path) in self.files:
            same(pin, self.files[str(path)], "INPUT_CHANGED_DURING_VERIFICATION")
        self.files[str(path)] = pin
        return raw

    def json(self, path):
        return parse(self.raw(path, 16 * 1024**2))

    def pin(self, path, expected):
        hex64(expected)
        raw = self.raw(path)
        require(digest(raw) == expected, "CALLER_OR_PARENT_PIN_MISMATCH:" + Path(path).name)
        return raw

    def done(self, name):
        self.checks.append(name)


def held_inputs(audit, result, directory):
    request, authority = result["request"], result["authority"]
    closed(request, IDENTITY | {"schema", "launch_authorized"}, "REQUEST_FIELDS")
    closed(authority, IDENTITY | set(BOUNDS) | {"schema", "candidate", "owner_authorization_sha256",
           "inputs_sha256", "design_sha256", "evidence_contract_sha256", "worker_config"}, "AUTHORITY_FIELDS")
    require(request["schema"] == PREFIX + "request/1" and request["launch_authorized"] is False,
            "REQUEST_SCHEMA_OR_INERT_FLAG")
    require(authority["schema"] == PREFIX + "authority/1" and authority["candidate"] == CANDIDATE,
            "AUTHORITY_SCHEMA")
    require(re.fullmatch(r"cas-meta2-ingestionsmoke-\d{14}-[0-9a-f]{8}", request["job"])
            and re.fullmatch(r"[0-9a-f]{40}", request["source_sha"]), "REQUEST_IDENTITIES")
    for key in IDENTITY:
        same(request[key], authority[key], "AUTHORITY_IDENTITY:" + key)
    for key, value in BOUNDS.items():
        same(authority[key], value, "AUTHORITY_BOUND:" + key)
    intent = audit.json(directory / "intent.json")
    same(intent["request"], request, "INTENT_REQUEST")
    same(intent["authority"], authority, "INTENT_AUTHORITY")
    matches = []
    for path in RECORDS.glob("*/request.json"):
        if canonical(parse(path.read_bytes())) == canonical(request):
            matches.append(path.parent)
    require(len(matches) == 1, "UNIQUE_HELD_PREPARATION_REQUIRED")
    preparation = matches[0]
    prep = audit.json(preparation / "receipt.json")
    require(prep["status"] == "BOUND_FOR_ONE_REVIEWED_RUN_NO_RESERVATION", "HELD_PREPARATION_STATUS")
    for key in IDENTITY:
        same(prep[key], request[key], "PREPARATION_IDENTITY:" + key)
    pins = {row["path"]: row for row in prep["files"]}
    require(len(pins) == len(prep["files"]), "PREPARATION_DUPLICATE_FILE")
    for name, expected in (("request.json", request), ("authority.json", authority)):
        raw = audit.pin(preparation / name, pins[name]["sha256"])
        require(type(pins[name]["bytes"]) is int and len(raw) == pins[name]["bytes"], "HELD_FILE_SIZE")
        same(parse(raw), expected, "HELD_FILE_BODY")
    owner = parse(audit.pin(preparation / "OWNER_AUTHORIZATION.json", authority["owner_authorization_sha256"]))
    require(owner["schema"] == PREFIX + "owner/1" and owner["candidate"] == CANDIDATE,
            "OWNER_SCOPE")
    same(owner["bounds"], BOUNDS, "OWNER_BOUNDS")
    for key in IDENTITY:
        same(owner[key], request[key], "OWNER_IDENTITY:" + key)
    config = authority["worker_config"]
    closed(config, {"schema", "candidate", "job", "region", "source_sha", "training", "optimizer_updates_max",
                   "seed", "max_wall_seconds", "execution_design", "inputs", "inputs_sha256", "material"}, "CONFIG_FIELDS")
    require(config["schema"] == PREFIX + "config/1" and config["candidate"] == CANDIDATE, "CONFIG_SCHEMA")
    same({k: config[k] for k in ("job", "source_sha")}, {k: request[k] for k in ("job", "source_sha")}, "CONFIG_IDENTITY")
    for key in ("training", "optimizer_updates_max", "max_wall_seconds", "region"):
        same(config[key], BOUNDS[key], "CONFIG_BOUND")
    integer(config["seed"], 20260916, 20260916, "CONFIG_SEED")
    same(owner["design"], config["execution_design"], "OWNER_CONFIG_DESIGN")
    require(digest(canonical(config["execution_design"])) == authority["design_sha256"], "DESIGN_DIGEST")
    require(digest(canonical(config["inputs"])) == config["inputs_sha256"] == authority["inputs_sha256"]
            == owner["inputs_sha256"], "INPUT_DIGEST")
    material = config["material"]
    closed(material, {"document_sha256", "training_requests", "prediction_requests", "boundary"}, "MATERIAL_FIELDS")
    hex64(material["document_sha256"])
    require(len(material["training_requests"]) == 3 and len(material["prediction_requests"]) == 6,
            "HELD_MATERIAL_COUNTS")
    same(material["prediction_requests"][::2], material["training_requests"], "HELD_TRAINING_SUBSET")
    contract = audit.json(directory / "evidence_contract.json")
    require(digest(canonical(contract)) == authority["evidence_contract_sha256"]
            == owner["evidence_contract_sha256"], "EVIDENCE_CONTRACT_PIN")
    package_matches = [p for p in PACKAGE_RECORDS.glob("*/receipt.json")
                       if digest(p.read_bytes()) == prep["package_receipt_sha256"]]
    require(len(package_matches) == 1, "UNIQUE_PINNED_PACKAGE_RECEIPT_REQUIRED")
    package = audit.json(package_matches[0])
    for key in ("source_sha", "archive_sha256", "manifest_sha256"):
        same(package[key], request[key], "PACKAGE_IDENTITY:" + key)
    audit.done("held_request_authority_owner_and_package_bindings")
    return config, contract, package


def source_package(audit, package, config):
    raw = audit.pin(package["archive"], package["archive_sha256"])
    require(type(package["archive_bytes"]) is int and len(raw) == package["archive_bytes"], "ARCHIVE_SIZE")
    with ZipFile(BytesIO(raw)) as archive:
        infos = archive.infolist()
        names = [safe_relative(row.filename) for row in infos]
        require(len(names) == len(set(names)) == package["member_count"] <= 2000, "ARCHIVE_MEMBERS")
        require(sum(row.file_size for row in infos) <= 96 * 1024**2, "EXPANDED_ARCHIVE_BOUND")
        require(all(not row.is_dir() and row.file_size <= 4 * 1024**2 for row in infos), "ARCHIVE_MEMBER_BOUND")
        members = {name: archive.read(name) for name in names}
    manifest_name = "graph6_curriculum_source_manifest.json"
    require(digest(members[manifest_name]) == package["manifest_sha256"], "ARCHIVE_MANIFEST_PIN")
    manifest = parse(members[manifest_name])
    same(manifest, package["manifest"], "ARCHIVE_MANIFEST_RECEIPT")
    require(set(members) == set(manifest["members"]) | {manifest_name}
            and set(manifest["files_sha256"]) == set(manifest["files_bytes"]) == set(manifest["members"]), "ARCHIVE_COVERAGE")
    for name in manifest["members"]:
        require(type(manifest["files_bytes"][name]) is int and len(members[name]) == manifest["files_bytes"][name]
                and digest(members[name]) == manifest["files_sha256"][name], "ARCHIVE_MEMBER_PIN:" + name)
    same(manifest["inputs"], config["inputs"], "MANIFEST_INPUTS")
    for key, value in config["execution_design"].items():
        same(manifest[key], value, "MANIFEST_DESIGN:" + key)
    paths = []
    for row in config["inputs"]:
        closed(row, {"path", "bytes", "sha256"}, "INPUT_ROW_FIELDS")
        name = safe_relative(row["path"]); paths.append(name)
        require(type(row["bytes"]) is int and len(members[name]) == row["bytes"]
                and digest(members[name]) == row["sha256"], "INPUT_ARCHIVE_PIN")
        require(audit.raw(ROOT / name) == members[name], "LOCAL_FROZEN_INPUT_CHANGED:" + name)
    require(paths == sorted(set(paths)), "INPUT_ORDER_OR_DUPLICATE")
    audit.done("all_source_archive_members_and_frozen_inputs")
    return members, manifest


def collected_files(audit, result, directory, contract):
    collection = result["collected"]
    inventory = audit.json(directory / "collected_inventory.json")
    require(inventory["job"] == result["job"] and inventory["failures"] == [], "COLLECTION_FAILURES")
    rows = inventory["files"]
    require(type(inventory["file_count"]) is int and len(rows) == inventory["file_count"], "COLLECTION_COUNT")
    names, local = [], {}
    for row in rows:
        name = safe_relative(row["relative_path"]); names.append(name)
        raw = audit.pin(directory / "collected" / name, row["sha256"])
        require(type(row["bytes"]) is int and len(raw) == row["bytes"], "RECEIVED_SIZE:" + name)
        local[name] = raw
    require(len(names) == len(set(names)), "DUPLICATE_RECEIVED_PATH")
    actual = {p.relative_to(directory / "collected").as_posix()
              for p in (directory / "collected").rglob("*") if p.is_file()}
    require(actual == set(names), "UNRECORDED_OR_MISSING_RECEIVED_FILE")
    required = {"results/result.json", "results/result.json.sha256", "results/artifacts/manifest.json"}
    required |= {"results/artifacts/" + name for name in ARTIFACTS}
    require({r["key"] for r in contract["required"]} == required
            and all(r["required"] is True for r in contract["required"]), "REQUIRED_CONTRACT_COVERAGE")
    receiver = audit.json(directory / "receiver_receipt.json")
    same(receiver, collection["receiver_receipt"], "RECEIVER_COPY")
    require(receiver["job"] == result["job"] and receiver["issued_by"] == "receiver", "RECEIVER_IDENTITY")
    require(receiver["receipt_sha256"] == digest(canonical({k: v for k, v in receiver.items() if k != "receipt_sha256"})), "RECEIVER_SEAL")
    identity = [{k: r[k] for k in ("relative_path", "bytes", "sha256")} for r in sorted(rows, key=lambda r: r["relative_path"])]
    require(receiver["inventory_sha256"] == digest(canonical(identity)), "RECEIVER_INVENTORY_BINDING")
    require(receiver["contract_sha256"] == digest(canonical(contract)), "RECEIVER_CONTRACT_BINDING")
    require(required <= set(local), "REQUIRED_FILES_MISSING")
    require(local["results/result.json.sha256"] == (digest(local["results/result.json"]) + "\n").encode(), "RESULT_SIDECAR")
    envelope = parse(local["results/result.json"])
    manifest = parse(local["results/artifacts/manifest.json"])
    closed(manifest, {"artifacts"}, "ARTIFACT_MANIFEST_FIELDS")
    same(manifest["artifacts"], envelope["artifacts"], "ENVELOPE_MANIFEST_JOIN")
    artifacts = {}
    for row in manifest["artifacts"]:
        closed(row, {"name", "bytes", "sha256"}, "ARTIFACT_MANIFEST_ROW")
        name = safe_relative(row["name"])
        require("/" not in name and name not in artifacts, "ARTIFACT_NAME_OR_DUPLICATE")
        raw = local["results/artifacts/" + name]
        require(type(row["bytes"]) is int and len(raw) == row["bytes"] and digest(raw) == row["sha256"], "ARTIFACT_PIN:" + name)
        artifacts[name] = raw
    require(set(artifacts) == ARTIFACTS, "SUCCESS_ARTIFACT_SET_OR_FAILURE_ARTIFACT")
    require({n.removeprefix("results/artifacts/") for n in local if n.startswith("results/artifacts/")}
            == ARTIFACTS | {"manifest.json"}, "UNDECLARED_ARTIFACT")
    require(receiver["collection"] == "COMPLETE_VERIFIED" and not receiver["failures"], "RECEIVER_PARTIAL")
    audit.done("received_inventory_sidecar_manifest_and_independent_receiver")
    return envelope, artifacts


def remote_pin(receipt, name, artifacts):
    closed(receipt, {"path", "bytes", "sha256"}, "REMOTE_PIN_FIELDS")
    require(type(receipt["path"]) is str and PurePosixPath(receipt["path"]).is_absolute()
            and PurePosixPath(receipt["path"]).name == name, "REMOTE_ARTIFACT_NAME")
    integer(receipt["bytes"], 1, 64 * 1024**2, "REMOTE_PIN_SIZE_TYPE")
    require(len(artifacts[name]) == receipt["bytes"] and digest(artifacts[name]) == receipt["sha256"], "REMOTE_ARTIFACT_PIN:" + name)


def seal(receipt, name, artifacts):
    remote_pin(receipt, name, artifacts)
    body = parse(artifacts[name])
    require(canonical(body) == artifacts[name], "PREDICTION_CANONICAL")
    closed(body, {"schema_version", "predictions", "answer_access", "scores"}, "PREDICTION_FIELDS")
    require(body["schema_version"] == SEAL_SCHEMA and body["answer_access"] == "NO_TARGET_ARGUMENT_OR_TEACHER_CALL"
            and body["scores"] == "UNAVAILABLE_TARGET_READING_LEGACY_SCORES_NOT_CALLED", "PREDICTION_CONTRACT")
    require(type(body["predictions"]) is list and len(body["predictions"]) == 6, "PREDICTION_ROWS")
    ids = []
    for row in body["predictions"]:
        closed(row, {"record_id", "public_input_digest", "encoded_options", "selected_index"}, "PREDICTION_ROW")
        require(re.fullmatch(r"rpa-learning-input-[0-9a-f]{64}", row["record_id"]), "PREDICTION_ID")
        hex64(row["public_input_digest"]); ids.append(row["record_id"])
        require(type(row["encoded_options"]) is list and len(row["encoded_options"]) == 3
                and len({canonical(x) for x in row["encoded_options"]}) == 3, "PREDICTION_OPTIONS")
        integer(row["selected_index"], 0, 2, "PREDICTION_SELECTION")
    require(len(set(ids)) == 6, "DUPLICATE_PREDICTION_ID")
    return body


def package_provenance(artifacts, members, manifest):
    expected = []
    for path in sorted(manifest["wheels"]):
        package = "cas_cjt" if "cas_neural_cjt" in path else "casformer"
        with ZipFile(BytesIO(members[path])) as wheel:
            for name in sorted(wheel.namelist()):
                if name.startswith(package + "/") and name.endswith((".py", ".json")):
                    raw = wheel.read(name)
                    expected.append({"wheel": PurePosixPath(path).name, "path": name, "bytes": len(raw), "sha256": digest(raw)})
    installed = parse(artifacts["installed_sources.json"])
    closed(installed, {"before", "after"}, "INSTALLED_SOURCES_FIELDS")
    by_path = {row["path"]: row for row in expected}
    for phase in ("before", "after"):
        record = installed[phase]
        closed(record, {"status", "source_files", "loaded_modules"}, "PROVENANCE_FIELDS")
        require(record["status"] == "INSTALLED_AND_LOADED_SOURCES_MATCH_PINNED_WHEELS", "PROVENANCE_STATUS")
        same(sorted(record["source_files"], key=lambda r: (r["wheel"], r["path"])),
             sorted(expected, key=lambda r: (r["wheel"], r["path"])), "INSTALLED_WHEEL_BYTES")
        modules = []
        for row in record["loaded_modules"]:
            closed(row, {"module", "source", "sha256"}, "LOADED_SOURCE_ROW")
            require(row["source"] in by_path and row["sha256"] == by_path[row["source"]]["sha256"], "LOADED_SOURCE_PIN")
            module_path = row["module"].replace(".", "/")
            require(row["source"] in {module_path + ".py", module_path + "/__init__.py"}, "MODULE_SOURCE_BINDING")
            modules.append(row["module"])
        require(len(modules) == len(set(modules)), "DUPLICATE_LOADED_MODULE")
        if phase == "after":
            require({"cas_cjt.neural", "cas_cjt.state", "casformer"} <= set(modules), "EXPECTED_MODULES_NOT_LOADED")


def prediction_training_joins(config, training, before, scoring):
    """Join fixed request order, training subset and unchanged teacher targets."""
    same(training["record_ids"], [row["record_id"] for row in before["predictions"]][::2],
         "TRAINING_SEALED_ID_SUBSET")
    expected_operations = [row["operation"] for row in config["material"]["prediction_requests"]]
    for phase in ("before", "after"):
        same([row["operation"] for row in scoring[phase]["rows"]], expected_operations,
             "SCORE_HELD_OPERATION_ORDER:" + phase)
    target_keys = ("record_id", "operation", "correct_index")
    same([{key: row[key] for key in target_keys} for row in scoring["before"]["rows"]],
         [{key: row[key] for key in target_keys} for row in scoring["after"]["rows"]],
         "SCORE_PHASE_TARGET_IDENTITY")


def measured_evidence(audit, result, config, envelope, artifacts, members, manifest):
    report, smoke, measurements = (parse(artifacts[name]) for name in ("worker_report.json", "receipt.json", "measurements.json"))
    require(envelope["schema"] == PREFIX + "result/1" and envelope["status"] == "INGESTION_SMOKE_DELIVERED"
            and envelope["failure"] is None, "WORKER_DELIVERY_FAILED")
    require(envelope["job"] == report["job"] == result["job"] and report["source_sha"] == config["source_sha"], "WORKER_JOB_SOURCE")
    require(report["status"] == smoke["status"] == MECHANICAL and smoke["schema_version"] == SMOKE_SCHEMA,
            "SMOKE_STATUS_OR_SCHEMA")
    require("failure" not in report and "failure" not in smoke, "FAILED_WORKER_REPORT")
    for value in (report, smoke, measurements):
        require(value["learning_improvement_established"] is False, "UNSUPPORTED_LEARNING_CLAIM")
    for key in ("inputs", "material", "execution_design"):
        same(report[key], config[key], "WORKER_PROVENANCE:" + key)
    summary = {key: report.get(key) for key in ("job", "source_sha", "status", "runtime", "elapsed_seconds", "failure",
               "optimizer_updates", "checkpoint_reload_verified", "forward_calls")}
    summary["learning_improvement_established"] = False
    same(summary, envelope["summary"], "ENVELOPE_SUMMARY")
    same(summary, measurements, "MEASUREMENTS_REPORT")
    require(report["checkpoint_reload_verified"] is True and smoke["checkpoint_reload_verified"] is True
            and smoke["frozen_encoder_unchanged"] is True, "RELOAD_OR_ENCODER_FLAG")
    integer(smoke["seed"], config["seed"], config["seed"], "SMOKE_SEED")
    runtime = report["runtime"]
    require(re.fullmatch(r"cuda(?::\d+)?", runtime["device"]) and runtime["torch_version"] == "2.11.0+cu128"
            and runtime["cuda_version"] == "12.8" and "RTX PRO 4500" in runtime["gpu_name"], "REPORTED_CUDA_RUNTIME")
    for value in (report["elapsed_seconds"], smoke["elapsed_seconds"]):
        require(type(value) in (int, float) and math.isfinite(value) and 0 < value < 1200, "EXECUTION_TIME_BOUND")
    training = smoke["training"]
    updates = training["training"]["completed_updates"]
    integer(updates, 1, 64, "ACTUAL_UPDATE_BOUND")
    same(updates, report["optimizer_updates"], "UPDATE_REPORT_JOIN")
    exposure = training["training"]["lesson_exposure"]
    operations = {"LIST_PARTS", "FIND_SHARED_PART", "REACHED_VIA"}
    require(set(exposure["records_by_op"]) == set(exposure["updates_by_op"]) == operations, "TRAINING_OPERATIONS")
    for op in operations:
        integer(exposure["records_by_op"][op], 1, 1, "TRAINING_RECORD_COUNT")
        integer(exposure["updates_by_op"][op], 0, 64, "OPERATION_UPDATE_COUNT")
    require(sum(exposure["updates_by_op"].values()) == updates, "UPDATE_EXPOSURE_SUM")
    same(training["training"]["automatic_retries"], 0, "TRAINING_RETRIES")
    containment = training["containment"]
    changed = sorted(k for k in training["parameter_before"] if training["parameter_before"][k] != training["parameter_after"][k])
    require(set(training["parameter_before"]) == set(training["parameter_after"]) and changed, "PARAMETER_CHANGE_REQUIRED")
    require(containment["contained"] is True and containment["forbidden_changes"] == []
            and containment["permitted_changes"] == changed and containment["total_changed"] == len(changed)
            and set(changed) <= set(training["scope"]["allowed"]), "PARAMETER_CONTAINMENT")
    checkpoints = smoke["checkpoints"]
    remote_pin(checkpoints["origin"], "origin.pt", artifacts)
    initial, final = (parse(artifacts[name + "_checkpoint.json"]) for name in ("initial", "final"))
    for name, record in (("initial", initial), ("final", final)):
        closed(record, {"checkpoint", "metadata"}, "CHECKPOINT_RECORD_FIELDS")
        same(record, checkpoints[name], "CHECKPOINT_RECEIPT_JOIN")
        remote_pin(record["checkpoint"], name + ".pt", artifacts)
        metadata = record["metadata"]
        closed(metadata, METADATA_FIELDS, "CHECKPOINT_METADATA_FIELDS")
        require(metadata["schema_version"] == SMOKE_SCHEMA and metadata["kind"] == name.upper(), "CHECKPOINT_KIND")
        same(metadata["training_requests"], config["material"]["training_requests"], "CHECKPOINT_TRAINING_REQUESTS")
        same(metadata["scope"], training["scope"], "CHECKPOINT_TRAINING_SCOPE")
        same(metadata["ordered_profile"], smoke["ordered_profile"], "CHECKPOINT_ORDERED_PROFILE")
        same(metadata["seed"], config["seed"], "CHECKPOINT_SEED")
        require(metadata["model_context"] == {"model_id": "candidate-cas-decompose-ordered-v1",
                "checkpoint_sha256": checkpoints["origin"]["sha256"]}, "RUN_INITIAL_CHECKPOINT_BINDING")
        source = metadata["source_binding"]
        closed(source, SOURCE_CONTEXT_FIELDS, "COMMON_SOURCE_CONTEXT_FIELDS")
        fixture_name = "research/CAS_META_2_COMPOSITION/records/teaching_cycle_001/graph_first_candidate_001/training_mode_001/cube_node_001/Cube_Node_Example_v0.1.json"
        fixture = parse(members[fixture_name])
        require(source["source_file_sha256"] == digest(members[fixture_name])
                and source["source_bundle_digest"] == "b3df2633ec6a49c6ad81d1572334ac00bcd123d09672d7a53a05979fc70b2c16"
                and source["source_namespace"] == "EXPOSED_ENGINEERING_FIXTURE"
                and source["source_context_id"] == fixture["context"]["context_id"]
                and source["rendering_schema"] == "cncm.cube-contains-node-rel/0.1"
                and source["source_authorship_authenticated"] is False
                and source["world_truth_established"] is False, "CHECKPOINT_SOURCE_CONTEXT")
        hex64(source["source_receipt_digest"])
        for key, pattern in (("prepared_ids", r"rpa-prepared-[0-9a-f]{64}"),
                             ("legacy_input_ids", r"cube-input-[0-9a-f]{64}")):
            values = metadata[key]
            require(type(values) is list and len(values) == len(set(values)) == 3
                    and all(type(v) is str and re.fullmatch(pattern, v) for v in values), "CHECKPOINT_ORDERED_IDENTITIES")
        require(metadata["optimizer_class"] == "torch.optim.adamw.AdamW"
                and type(metadata["learning_rate"]) is float and metadata["learning_rate"] == 0.003,
                "CHECKPOINT_OPTIMIZER_CONTRACT")
        require(metadata["tokenizer"]["fit_split"] == "train_only", "TOKENIZER_FIT_SCOPE")
        integer(metadata["tokenizer"]["max_length"], 1024, 1024, "TOKENIZER_LENGTH")
        integer(metadata["tokenizer"]["fitted_examples"], 3, 3, "TOKENIZER_TRAINING_EXAMPLES")
        for field in ("model_identity", "optimizer_identity", "projection_identity"):
            hex64(metadata[field])
    stable = set(initial["metadata"]) - {"kind", "model_identity", "optimizer_identity"}
    same({k: initial["metadata"][k] for k in stable}, {k: final["metadata"][k] for k in stable}, "FROZEN_CHECKPOINT_METADATA")
    require(initial["metadata"]["model_identity"] != final["metadata"]["model_identity"], "MODEL_IDENTITY_UNCHANGED")
    for phase in ("initial", "final"):
        reload = smoke["reload"][phase]
        require(reload["model_optimizer_projection_values_exact"] is True
                and reload["values"]["model_optimizer_projection_cache_exact"] is True,
                "RELOAD_EXACT_FLAGS")
        integer(reload["values"]["public_vectors_checked"], 6, 6, "RELOAD_VECTOR_COUNT")
        for cache in (reload["cache"], smoke["original"][phase + "_cache"]):
            require(cache["bitwise_equal"] is True, "CACHE_EQUALITY_FLAG")
            integer(cache["numeric_cache_rows_checked"], 3, 3, "CACHE_ROW_COUNT")
        for paths in (reload["paths"], smoke["original"][phase + "_paths"]):
            for key, expected in (("public_rows_checked", 6), ("cached_rows", 3), ("on_demand_rows", 3)):
                integer(paths[key], expected, expected, "PUBLIC_PATH_COUNT")
            require(paths["exact_cached_and_direct_tensors"] is True and paths["public_predictions_match_direct"] is True,
                    "PUBLIC_PATH_FLAGS")
    before = seal(smoke["predictions"]["before"], "before_predictions.json", artifacts)
    after = seal(smoke["predictions"]["after"], "after_predictions.json", artifacts)
    for phase, original in (("initial", "before"), ("final", "after")):
        seal(smoke["reload"][phase]["prediction_seal"], phase + "_reload_predictions.json", artifacts)
        require(artifacts[original + "_predictions.json"] == artifacts[phase + "_reload_predictions.json"], "RELOAD_PREDICTION_BYTES")
    same([{k: v for k, v in row.items() if k != "selected_index"} for row in before["predictions"]],
         [{k: v for k, v in row.items() if k != "selected_index"} for row in after["predictions"]], "PUBLIC_PREDICTION_INPUTS_CHANGED")
    for phase, body in (("before", before), ("after", after)):
        score = smoke["scoring"][phase]
        require(score["prediction_seal_sha256"] == digest(artifacts[phase + "_predictions.json"]), "SCORE_SEAL_PIN")
        require(len(score["rows"]) == score["total"] == 6, "SCORING_ROW_COUNT")
        for prediction, row in zip(body["predictions"], score["rows"]):
            require(row["record_id"] == prediction["record_id"] and row["selected_index"] == prediction["selected_index"], "SCORE_PREDICTION_JOIN")
            integer(row["correct_index"], 0, 2, "SCORING_TARGET_INDEX")
            require(row["correct"] is (row["selected_index"] == row["correct_index"]), "SCORING_CORRECT_FLAG")
        integer(score["correct"], 0, 6, "SCORING_CORRECT_COUNT")
        require(score["correct"] == sum(row["correct"] for row in score["rows"]), "SCORING_TOTAL")
    prediction_training_joins(config, training, before, smoke["scoring"])
    counters = smoke["forward_calls"]
    closed(counters, {"original", "initial_reload", "final_reload", "total"}, "FORWARD_COUNTER_FIELDS")
    for count in counters.values():
        integer(count, 1, 1000000, "FORWARD_CALL_COUNT")
    require(counters["total"] == sum(counters[k] for k in ("original", "initial_reload", "final_reload")), "FORWARD_CALL_SUM")
    same(counters, report["forward_calls"], "FORWARD_REPORT_JOIN")
    package_provenance(artifacts, members, manifest)
    audit.done("worker_status_updates_four_prediction_seals_checkpoint_bytes_reload_flags_and_installed_sources")
    return {"optimizer_updates": updates, "prediction_rows_per_seal": 6, "prediction_seals": 4,
            "checkpoint_bytes_checked_without_decoding": 3, "forward_calls": counters,
            "recorded_before_correct": smoke["scoring"]["before"]["correct"],
            "recorded_after_correct": smoke["scoring"]["after"]["correct"], "runtime": runtime}


def verify(result_path, expected, output):
    result_path, output = Path(result_path).absolute(), Path(output).absolute()
    require(output.resolve().is_relative_to(RECORDS) and not output.exists() and output.parent.is_dir(), "NEW_OUTPUT_REQUIRED")
    output.mkdir()
    audit = Audit()
    report = {"schema": "cncm-ingestion-delivered-verification/1", "status": "FAILED_OR_PARTIAL", "accepted": False,
              "learning_improvement_established": False, "helper_sha256": digest(Path(__file__).read_bytes()),
              "caller_result_sha256": expected, "numeric_or_checkpoint_decoder_calls": 0, "provider_calls": 0,
              "boundary": "Caller-pinned local evidence integrity and reported mechanical smoke only. No independent numerical rerun, authentication, held-out learning, budget settlement, or live provider-cleanup claim."}
    try:
        result = parse(audit.pin(result_path, expected))
        report["lifecycle_status"] = result.get("status")
        report["job"] = result.get("job")
        directory = result_path.parent
        require(Path(result["receipt_dir"]).resolve() == directory.resolve(), "LIFECYCLE_DIRECTORY_BINDING")
        config, contract, package = held_inputs(audit, result, directory)
        report["source_sha"] = config["source_sha"]
        report["archive_sha256"] = package["archive_sha256"]
        members, manifest = source_package(audit, package, config)
        envelope, artifacts = collected_files(audit, result, directory, contract)
        report["measurements"] = measured_evidence(audit, result, config, envelope, artifacts, members, manifest)
        require(result["status"] == "AWS_CANDIDATE_FINISHED"
                and result["outcome"]["worker_status"] == "REMOTE_FINISHED", "LIFECYCLE_FAILED_OR_PARTIAL")
        audit.done("lifecycle_and_worker_success_agree")
        for row in list(audit.files.values()):
            audit.pin(row["path"], row["sha256"])
        require(digest(Path(__file__).read_bytes()) == report["helper_sha256"], "VERIFIER_SOURCE_CHANGED")
        report.update(status="RECORDED_MECHANICAL_EVIDENCE_VERIFIED", accepted=True)
    except Exception as error:
        report["failure"] = {"type": type(error).__name__, "detail": str(error)[:1000]}
    report["checks_completed"] = audit.checks
    report["inputs"] = sorted(audit.files.values(), key=lambda row: row["path"])
    raw = canonical(report)
    with (output / "receipt.json").open("xb") as stream:
        stream.write(raw)
    require((output / "receipt.json").read_bytes() == raw, "RECEIPT_WRITE_READBACK")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lifecycle-result", required=True)
    parser.add_argument("--lifecycle-result-sha256", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    report = verify(args.lifecycle_result, args.lifecycle_result_sha256, args.output)
    print(json.dumps({k: report.get(k) for k in ("status", "accepted", "job", "failure")}))
    return 0 if report["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
