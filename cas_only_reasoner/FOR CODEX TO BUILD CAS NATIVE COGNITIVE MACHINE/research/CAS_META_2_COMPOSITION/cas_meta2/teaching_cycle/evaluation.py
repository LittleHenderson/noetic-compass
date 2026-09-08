"""Teacher-only, byte-bound scoring; never import this module on the student.

All public predictions and checkpoint identities are admitted before any private
target file is opened. Hashes bind bytes, not their truth or provider provenance.
Selected float32 input bytes are calculated here; native execution and retention
are deliberately not measured. No model, native runtime or provider is imported.
"""
from copy import deepcopy
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import re
import stat
import struct

from ..codec import canonical_sha256, validate_public
from .lesson_contract import recover_binding

ARMS = ("cas.aligned", "cas.ordinary", "generic.aligned", "generic.ordinary")
PHASES = ("untrained", "trained")
SPLITS = ("test_fresh", "test_context", "test_names")
COUNT = 64
PREDICTION_NAMES = {f"{arm}.{phase}.{split}.json" for arm in ARMS for phase in PHASES for split in SPLITS}
JSON_LIMIT = 32 * 1024**2
CHECKPOINT_LIMIT = 64 * 1024**2
SPLIT_MEANING = {
    "test_fresh": "Fresh numeric instances of familiar forms, tags and contexts.",
    "test_context": "Unseen irrelevant context combinations made from known words.",
    "test_names": "Unseen color-plus-shape tag combinations made from known words.",
}


class EvaluationError(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise EvaluationError("TEACHING_EVALUATION:" + reason)


def _pin(value):
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None and value != "0" * 64


def _encode(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def _safe(path):
    path = Path(path).absolute()
    require(not any(item.is_symlink() or getattr(item, "is_junction", lambda: False)()
                    for item in (path, *path.parents)), "LINK_PATH_REJECTED")
    return path


class _Reader:
    def __init__(self, callback=None):
        self.callback = callback or (lambda path: path.read_bytes())
        self.identities = {}

    def raw(self, path, maximum=JSON_LIMIT):
        path = _safe(path)
        info = path.stat()
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and 0 < info.st_size <= maximum,
                "FILE_TYPE_OR_BYTE_BOUND:" + path.name)
        raw = self.callback(path)
        require(type(raw) is bytes and len(raw) == info.st_size and path.stat().st_size == info.st_size,
                "FILE_CHANGED_OR_READER_INVALID:" + path.name)
        self.identities[str(path)] = {"sha256": sha256(raw).hexdigest(), "bytes": len(raw)}
        return raw

    def json(self, path, expected=None, declared_bytes=None, maximum=JSON_LIMIT):
        raw = self.raw(path, maximum)
        if expected is not None:
            require(_pin(expected) and sha256(raw).hexdigest() == expected, "FILE_HASH_MISMATCH:" + Path(path).name)
        if declared_bytes is not None:
            require(type(declared_bytes) is int and len(raw) == declared_bytes,
                    "FILE_SIZE_MISMATCH:" + Path(path).name)
        def pairs(items):
            result = {}
            for key, value in items:
                require(key not in result, "DUPLICATE_JSON_KEY")
                result[key] = value
            return result
        try:
            value = json.loads(raw, object_pairs_hook=pairs,
                               parse_constant=lambda _: require(False, "NONFINITE_JSON"))
            _encode(value)
        except (UnicodeError, json.JSONDecodeError, OverflowError, ValueError) as error:
            if isinstance(error, EvaluationError):
                raise
            raise EvaluationError("TEACHING_EVALUATION:INVALID_FINITE_JSON") from error
        return value


def _declaration(value):
    require(type(value) is dict and _pin(value.get("sha256")) and type(value.get("bytes")) is int
            and 0 < value["bytes"] <= JSON_LIMIT, "ARTIFACT_DECLARATION_INVALID")


def _public_packet(material_root, material_pin, reader):
    root = _safe(material_root)
    manifest = reader.json(root / "preparation_receipt.json", material_pin)
    require(type(manifest) is dict and manifest.get("schema") == "cas-teaching-preparation/1"
            and manifest.get("status") == "PREPARED_NOT_TRAINED" and _pin(manifest.get("dataset_sha256")),
            "MATERIAL_IDENTITY_INVALID")
    require(type(manifest.get("counts")) is dict and
            all(manifest["counts"].get(split) == COUNT for split in SPLITS), "MATERIAL_COUNTS_INVALID")
    require(type(manifest.get("artifacts")) is dict, "MATERIAL_ARTIFACTS_INVALID")
    public_sets = {}
    for split in SPLITS:
        for directory in ("evaluation_public", "evaluator_private"):
            _declaration(manifest["artifacts"].get(f"{directory}/{split}.json"))
        declaration = manifest["artifacts"][f"evaluation_public/{split}.json"]
        rows = reader.json(root / "evaluation_public" / f"{split}.json",
                           declaration["sha256"], declaration["bytes"])
        require(type(rows) is list and len(rows) == COUNT, "PUBLIC_COUNT_INVALID")
        for public in rows:
            validate_public(public)
            require("Worked" not in public["problem"] and "BIND" not in public["problem"],
                    "FINAL_PUBLIC_HAS_TEACHING_ANSWER")
            require(len({row["tag"] for row in public["observations"]}) == 3, "PUBLIC_TAGS_NOT_UNIQUE")
            recover_binding(public)
            for row in public["observations"]:
                _float_bytes(row["values"])
        require(len({canonical_sha256(row) for row in rows}) == COUNT, "DUPLICATE_PUBLIC_INSTANCE")
        public_sets[split] = rows
    return manifest, public_sets


def _float_bytes(values):
    require(type(values) is list and len(values) == 8 and
            all(type(value) in (int, float) and math.isfinite(value) for value in values),
            "EIGHT_FINITE_VALUES_REQUIRED")
    try:
        raw = struct.pack("<8f", *values)
    except (OverflowError, struct.error) as error:
        raise EvaluationError("TEACHING_EVALUATION:FLOAT32_VALUE_OUT_OF_RANGE") from error
    require(all(math.isfinite(value) for value in struct.unpack("<8f", raw)), "FLOAT32_VALUE_OUT_OF_RANGE")
    return raw


def _source_files(reader, source_root, source_pins):
    require((source_root is None) == (source_pins is None), "SOURCE_FILES_REQUIRE_ROOT_AND_PINS")
    if source_root is None:
        return {"status": "EXTERNAL_SOURCE_IDENTITY_ONLY_NO_SOURCE_FILES_CHECKED"}
    require(type(source_pins) is dict and 0 < len(source_pins) <= 256, "SOURCE_PINS_INVALID")
    root = _safe(source_root)
    for name, expected in source_pins.items():
        require(type(name) is str and re.fullmatch(r"[A-Za-z0-9_./-]+", name) is not None
                and not name.startswith("/") and all(part not in ("", ".", "..") for part in name.split("/"))
                and _pin(expected), "SOURCE_PATH_OR_PIN_INVALID")
        require(sha256(reader.raw(root / name)).hexdigest() == expected, "SOURCE_FILE_MISMATCH:" + name)
    return {"status": "SUPPLIED_SOURCE_FILE_PINS_CHECKED", "file_count": len(source_pins),
            "pins_sha256": canonical_sha256(source_pins)}


def _reference(reference):
    require(type(reference) is dict and set(reference) ==
            {"path", "sha256", "state_sha256", "transaction", "receipt_sha256"}, "CHECKPOINT_REFERENCE_INVALID")
    require(type(reference["path"]) is str and re.split(r"[/\\]", reference["path"])[-1] == "candidate.pt"
            and type(reference["transaction"]) is int and 1 <= reference["transaction"] <= 100
            and all(_pin(reference[key]) for key in ("sha256", "state_sha256", "receipt_sha256")),
            "CHECKPOINT_REFERENCE_IDENTITY_INVALID")


def _checkpoint_chain(reader, campaign_root, arm, report, source_pin):
    root = _safe(Path(campaign_root) / arm / "journal")
    anchor = reader.json(root / "journal.json", maximum=65536)
    identity = anchor.get("identity") if type(anchor) is dict else None
    require(type(identity) is dict and identity.get("source_sha256") == source_pin
            and identity.get("curriculum") == arm.split(".")[1]
            and identity.get("schema") == "cas-teaching-session/1", "JOURNAL_SOURCE_IDENTITY_MISMATCH")
    identity_hash = sha256(_encode(identity)).hexdigest()
    require(anchor.get("schema") == "cas-teaching-checkpoint-journal/1"
            and anchor.get("run_id") == report["run_id"] and anchor.get("identity_sha256") == identity_hash,
            "JOURNAL_IDENTITY_MISMATCH")
    entries, incomplete, retained_bytes = {}, [], 0
    for entry in root.iterdir():
        _safe(entry)
        if entry.name == "journal.json":
            continue
        match = re.fullmatch(r"txn-([0-9]{8})", entry.name)
        require(entry.is_dir() and (match is not None or entry.name.startswith(".staging-")),
                "JOURNAL_INVENTORY_INVALID")
        if match:
            require({child.name for child in entry.iterdir()} == {"candidate.pt", "metadata.json", "receipt.json"},
                    "CHECKPOINT_INVENTORY_INVALID")
            entries[int(match[1])] = entry
        else:
            incomplete.append(entry.name)
        for child in entry.iterdir():
            _safe(child)
            info = child.stat()
            require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, "JOURNAL_FILE_TYPE_INVALID")
            retained_bytes += info.st_size
        require(retained_bytes <= 512 * 1024**2, "JOURNAL_RETAINED_BYTE_LIMIT")
    require(sorted(entries) == list(range(1, len(entries) + 1)) and 1 <= len(entries) <= 100,
            "JOURNAL_CHAIN_GAP_OR_BOUND")
    refs = {phase: report[key] for phase, key in
            (("untrained", "initial_checkpoint"), ("trained", "selected_checkpoint"))}
    require(refs["untrained"]["transaction"] == 1 and refs["trained"]["transaction"] > 1,
            "CHECKPOINT_PHASE_INVALID")
    previous, verified = None, {}
    # Validate every committed transaction, not only a favorable selected entry.
    for sequence in sorted(entries):
        directory = entries[sequence]
        receipt = reader.json(directory / "receipt.json", maximum=65536)
        metadata = reader.json(directory / "metadata.json")
        checkpoint_hash = sha256(reader.raw(directory / "candidate.pt", CHECKPOINT_LIMIT)).hexdigest()
        receipt_hash = reader.identities[str(directory / "receipt.json")]["sha256"]
        metadata_identity = reader.identities[str(directory / "metadata.json")]
        checkpoint_identity = reader.identities[str(directory / "candidate.pt")]
        require(type(receipt) is dict and type(metadata) is dict and all(receipt.get(key) == value for key, value in {
            "schema": "cas-teaching-checkpoint-journal/1", "run_id": report["run_id"],
            "identity_sha256": identity_hash, "sequence": sequence, "previous_receipt_sha256": previous,
            "checkpoint_filename": "candidate.pt", "checkpoint_sha256": checkpoint_hash,
            "checkpoint_bytes": checkpoint_identity["bytes"], "metadata_filename": "metadata.json",
            "metadata_sha256": metadata_identity["sha256"], "metadata_bytes": metadata_identity["bytes"],
            "candidate_only": True, "neural_execution_by_journal": False}.items()), "CHECKPOINT_CHAIN_MISMATCH")
        require(metadata.get("schema") == "cas-teaching-session/1" and metadata.get("identity") == identity
                and _pin(metadata.get("model_state_sha256")) and type(receipt.get("writer_receipt")) is dict
                and receipt["writer_receipt"].get("sha256") == checkpoint_hash, "CHECKPOINT_METADATA_MISMATCH")
        for phase, reference in refs.items():
            if reference["transaction"] == sequence:
                require(reference["receipt_sha256"] == receipt_hash and reference["sha256"] == checkpoint_hash
                        and reference["state_sha256"] == metadata["model_state_sha256"], "CHECKPOINT_REFERENCE_MISMATCH")
                verified[phase] = {**reference, "local_path": str(directory / "candidate.pt")}
        previous = receipt_hash
    require(set(verified) == set(PHASES), "CHECKPOINT_TRANSACTION_MISSING")
    return {"phases": verified, "committed_transactions_checked": len(entries),
            "incomplete_staging": sorted(incomplete), "identity_sha256": identity_hash,
            "declared_execution_mode": identity.get("execution_mode", "UNDECLARED"),
            "state_digest_boundary": "State digest matched to metadata; checkpoint tensors were not deserialized."}


def _admit(prediction_root, material_root, campaign_summary_path, campaign_root, *,
           expected_seal_sha256, expected_campaign_sha256, expected_material_sha256,
           expected_source_sha256, expected_bundle_manifest_sha256, reader,
           source_root=None, source_pins=None):
    require(all(_pin(pin) for pin in (expected_seal_sha256, expected_campaign_sha256,
            expected_material_sha256, expected_source_sha256, expected_bundle_manifest_sha256)), "EXTERNAL_PINS_REQUIRED")
    source_files = _source_files(reader, source_root, source_pins)
    material, publics = _public_packet(material_root, expected_material_sha256, reader)
    campaign = reader.json(campaign_summary_path, expected_campaign_sha256)
    require(type(campaign) is dict and campaign.get("schema") == "cas-teaching-four-arm-campaign/1"
            and campaign.get("all_allocations_finished") is True and campaign.get("held_out_opened") is False
            and campaign.get("accepted_weights_updated") is False
            and campaign.get("source_sha256") == expected_source_sha256
            and campaign.get("manifest_sha256") == expected_bundle_manifest_sha256
            and type(campaign.get("arms")) is dict and set(campaign["arms"]) == set(ARMS), "CAMPAIGN_IDENTITY_INVALID")
    run_ids = []
    for arm in ARMS:
        report = campaign["arms"][arm]
        require(type(report) is dict and report.get("allocation_finished") is True
                and report.get("curriculum") == arm.split(".")[1]
                and type(report.get("run_id")) is str and
                re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", report["run_id"]) is not None,
                "CAMPAIGN_ARM_INVALID")
        run_ids.append(report["run_id"])
        _reference(report.get("initial_checkpoint"))
        _reference(report.get("selected_checkpoint"))
    require(len(set(run_ids)) == len(ARMS), "DUPLICATE_ARM_RUN_ID")
    root = _safe(prediction_root)
    inventory = {entry.name for entry in root.iterdir()}
    require(inventory in (PREDICTION_NAMES | {"prediction_seal.json"},
                          PREDICTION_NAMES | {"prediction_seal.json", "worker_identity.json"}), "PREDICTION_INVENTORY_INVALID")
    seal = reader.json(root / "prediction_seal.json", expected_seal_sha256)
    require(type(seal) is dict and seal.get("schema") == "cas-teaching-blind-prediction-seal/1"
            and seal.get("source_sha256") == expected_source_sha256
            and seal.get("private_targets_opened") is False and seal.get("native_execution") == "UNEXECUTED"
            and type(seal.get("artifacts")) is dict and set(seal["artifacts"]) == PREDICTION_NAMES,
            "PREDICTION_SEAL_INVALID")
    predictions, pids = {}, set()
    for arm in ARMS:
        for phase, key in (("untrained", "initial_checkpoint"), ("trained", "selected_checkpoint")):
            for split in SPLITS:
                name = f"{arm}.{phase}.{split}.json"
                declaration = seal["artifacts"][name]
                _declaration(declaration)
                require(type(declaration.get("path")) is str and
                        re.split(r"[/\\]", declaration["path"])[-1] == name, "PREDICTION_ARTIFACT_PATH_MISMATCH")
                document = reader.json(root / name, declaration["sha256"], declaration["bytes"])
                require(type(document) is dict and all(document.get(field) == value for field, value in {
                    "schema": "cas-teaching-blind-predictions/1", "arm": arm, "phase": phase, "split": split,
                    "run_id": campaign["arms"][arm]["run_id"], "source_sha256": expected_source_sha256,
                    "checkpoint": campaign["arms"][arm][key], "public_sha256": canonical_sha256(publics[split]),
                    "private_targets_opened": False}.items()), "PREDICTION_IDENTITY_MISMATCH:" + name)
                values = document.get("predictions")
                require(type(values) is list and len(values) == COUNT
                        and all(type(value) is int and value in (0, 1, 2) for value in values), "PREDICTION_VALUES_INVALID")
                require(type(document.get("pid")) is int and document["pid"] > 0, "PREDICTION_PID_INVALID")
                pids.add(document["pid"])
                predictions[(arm, phase, split)] = values
    require(len(pids) == 1, "PREDICTION_PROCESS_IDENTITY_CHANGED")
    if "worker_identity.json" in inventory:
        worker = reader.json(root / "worker_identity.json")
        require(type(worker) is dict and worker.get("phase") == "predict" and worker.get("pid") in pids
                and worker.get("source_sha256") == expected_source_sha256
                and worker.get("manifest_sha256") == expected_bundle_manifest_sha256, "WORKER_IDENTITY_MISMATCH")
    checkpoints = {arm: _checkpoint_chain(reader, campaign_root, arm, campaign["arms"][arm], expected_source_sha256)
                   for arm in ARMS}
    return material, publics, predictions, checkpoints, source_files


def _targets(material_root, material, publics, reader):
    result, families = {}, set()
    for split in SPLITS:
        declaration = material["artifacts"][f"evaluator_private/{split}.json"]
        rows = reader.json(Path(material_root) / "evaluator_private" / f"{split}.json",
                           declaration["sha256"], declaration["bytes"])
        require(type(rows) is list and len(rows) == COUNT, "PRIVATE_COUNT_INVALID")
        for public, target in zip(publics[split], rows):
            require(type(target) is dict and set(target) == {"family_id", "binding", "selected_values"}
                    and _pin(target["family_id"]) and type(target["binding"]) is int
                    and target["binding"] in (0, 1, 2), "PRIVATE_TARGET_INVALID")
            requested = re.findall(r"Requested source: ([a-z]+ [a-z]+)\.", public["problem"])[0]
            family = canonical_sha256({"fixed_child": "A", "requested_tag": requested,
                                        "observations": public["observations"]})
            require(family == target["family_id"] and family not in families, "PRIVATE_FAMILY_MISMATCH_OR_OVERLAP")
            families.add(family)
            require(recover_binding(public) == target["binding"], "PRIVATE_TARGET_DISAGREES_WITH_PUBLIC")
            selected = next(row["values"] for row in public["observations"] if row["slot"] == target["binding"])
            require(selected == target["selected_values"] and _float_bytes(selected) == _float_bytes(target["selected_values"]),
                    "PRIVATE_SELECTED_VALUES_MISMATCH")
        result[split] = rows
    return result


def _measure(publics, targets, predictions):
    rows = []
    for index, (public, target, prediction) in enumerate(zip(publics, targets, predictions)):
        selected = next(row["values"] for row in public["observations"] if row["slot"] == prediction)
        expected_raw, actual_raw = _float_bytes(target["selected_values"]), _float_bytes(selected)
        correct = prediction == target["binding"]
        rows.append({"index": index, "family_id": target["family_id"], "expected_binding": target["binding"],
                     "predicted_binding": prediction, "binding_correct": correct,
                     "calculated_float32_bytes_match": actual_raw == expected_raw,
                     "expected_input_bytes_sha256": sha256(expected_raw).hexdigest(),
                     "calculated_selected_bytes_sha256": sha256(actual_raw).hexdigest(),
                     "first_wrong_decision": None if correct else {"decision_index": 0, "category": "wrong_observation_binding"}})
    return {"binding_correct": sum(row["binding_correct"] for row in rows), "attempted": len(rows),
            "calculated_float32_bytes_correct": sum(row["calculated_float32_bytes_match"] for row in rows),
            "first_error_counts": {"wrong_observation_binding": sum(not row["binding_correct"] for row in rows)},
            "rows": rows}


def _rule_probes(publics):
    irrelevant, relevant = 0, 0
    for public in publics:
        expected = recover_binding(public)
        changed = deepcopy(public)
        changed["problem"] = "In a different setting. " + re.sub(r"^In the [a-z]+ [a-z]+\. ", "", public["problem"])
        changed["observations"].reverse()
        irrelevant += recover_binding(changed) == expected
        alternate = next(row for row in public["observations"] if row["slot"] != expected)
        changed = deepcopy(public)
        changed["problem"] = re.sub(r"Requested source: [a-z]+ [a-z]+\.",
                                     "Requested source: " + alternate["tag"] + ".", changed["problem"])
        relevant += recover_binding(changed) == alternate["slot"]
    return {"attempted_per_probe": len(publics), "irrelevant_context_and_list_order_preserved": irrelevant,
            "changed_requested_source_changed_binding": relevant,
            "boundary": "Pure rule/contract checks only. The neural candidates did not receive these probes."}


def score_packet(prediction_root, material_root, campaign_summary_path, campaign_root, *,
                 expected_seal_sha256, expected_campaign_sha256, expected_material_sha256,
                 expected_source_sha256, expected_bundle_manifest_sha256, reader=None,
                 source_root=None, source_pins=None):
    """Validate the full packet before reading private labels; read-only, fail closed.

    ``reader(Path)->bytes`` is an observable read seam, not an attestation bypass.
    External pins must come from the independently retained launch/receipt record.
    Remote worker paths are labels; local checkpoints use the explicit campaign root.
    """
    reads = _Reader(reader)
    material, publics, predictions, checkpoints, sources = _admit(
        prediction_root, material_root, campaign_summary_path, campaign_root,
        expected_seal_sha256=expected_seal_sha256, expected_campaign_sha256=expected_campaign_sha256,
        expected_material_sha256=expected_material_sha256, expected_source_sha256=expected_source_sha256,
        expected_bundle_manifest_sha256=expected_bundle_manifest_sha256, reader=reads,
        source_root=source_root, source_pins=source_pins)
    # This is the only transition into private target reads. Keep it after _admit.
    preflight_file_count = len(reads.identities)
    targets = _targets(material_root, material, publics, reads)
    arms = {arm: {phase: {split: _measure(publics[split], targets[split], predictions[(arm, phase, split)])
                          for split in SPLITS} for phase in PHASES} for arm in ARMS}
    comparison = {arm: {split: {"before_correct": arms[arm]["untrained"][split]["binding_correct"],
        "after_correct": arms[arm]["trained"][split]["binding_correct"], "attempted_each": COUNT,
        "change_correct": arms[arm]["trained"][split]["binding_correct"] - arms[arm]["untrained"][split]["binding_correct"]}
        for split in SPLITS} for arm in ARMS}
    return {"schema": "cas-teaching-final-score/1", "status": "SEALED_BINDING_PREDICTIONS_SCORED",
            "comparison": comparison, "arms": arms,
            "rule": {split: _measure(publics[split], targets[split], [recover_binding(row) for row in publics[split]]) for split in SPLITS},
            "rule_public_change_probes": {split: _rule_probes(publics[split]) for split in SPLITS},
            "split_meaning": SPLIT_MEANING, "unseen_program_combinations_tested": False,
            "prediction_files_validated_before_private_reads": 24,
            "preflight_files_checked_before_private_reads": preflight_file_count,
            "identities": {"seal_sha256": expected_seal_sha256, "campaign_sha256": expected_campaign_sha256,
                "material_sha256": expected_material_sha256, "dataset_sha256": material["dataset_sha256"],
                "source_sha256": expected_source_sha256, "bundle_manifest_sha256": expected_bundle_manifest_sha256,
                "source_files": sources, "checkpoints": checkpoints, "files": reads.identities},
            "native_execution": "UNEXECUTED", "native_retention": "UNEXECUTED",
            "complete_native_task_correctness": "UNMEASURED", "provider_identity_proved": False,
            "neural_training_independently_verified": False,
            "compute_cost": "INDEPENDENT_PROVIDER_AND_BUDGET_RECEIPTS_REQUIRED",
            "boundary": "Scores describe packet-reported binding predictions. Float32 bytes are calculated, not observed native inputs. Hash and flag checks do not prove CUDA execution, target isolation during the original run, mastery, or CAS-specific advantage."}


def write_fresh_json(path, value):
    path = _safe(path)
    raw = _encode(value)
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return {"path": str(path), "sha256": sha256(raw).hexdigest(), "bytes": len(raw)}


def export_public(material_root, expected_material_sha256, output, *, reader=None):
    """Export the three pinned public splits for the separate prediction command."""
    require(_pin(expected_material_sha256), "EXTERNAL_MATERIAL_PIN_REQUIRED")
    reads = _Reader(reader)
    _, public_sets = _public_packet(material_root, expected_material_sha256, reads)
    receipt = write_fresh_json(output, public_sets)
    return {**receipt, "material_sha256": expected_material_sha256,
            "counts": {split: len(rows) for split, rows in public_sets.items()},
            "private_targets_opened": False, "source_public_files": reads.identities}
