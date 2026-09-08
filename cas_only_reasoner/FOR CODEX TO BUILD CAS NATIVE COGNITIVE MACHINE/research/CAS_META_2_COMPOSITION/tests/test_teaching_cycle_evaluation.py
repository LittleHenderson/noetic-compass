"""Synthetic byte-packet tests only; these are not model learning results."""
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import struct
import subprocess
import sys

import pytest

from cas_meta2.codec import canonical_sha256
from cas_meta2.teaching_cycle.evaluation import (
    ARMS, PHASES, SPLITS, PREDICTION_NAMES, EvaluationError, score_packet, export_public, _measure,
)

SOURCE = "1" * 64
BUNDLE = "2" * 64


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def write(path, value, raw=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = value if raw else encoded(value)
    path.write_bytes(payload)
    return {"path": str(path), "sha256": sha256(payload).hexdigest(), "bytes": len(payload)}


@pytest.fixture
def packet(tmp_path):
    material, predictions, campaign_root = tmp_path / "material", tmp_path / "predictions", tmp_path / "campaign"
    publics, targets, artifacts = {}, {}, {}
    for split_index, split in enumerate(SPLITS):
        publics[split], targets[split] = [], []
        for index in range(64):
            binding = index % 3
            observations = [{"slot": slot, "tag": tag,
                             "values": [float(1000 * split_index + 10 * index + slot + j / 10) for j in range(8)]}
                            for slot, tag in enumerate(("blue square", "red circle", "green triangle"))]
            tag = observations[binding]["tag"]
            public = {"problem": "In the school workshop. Select the source for child A. Requested source: " + tag + ".",
                      "observations": observations}
            target = {"family_id": canonical_sha256({"fixed_child": "A", "requested_tag": tag,
                                                     "observations": observations}),
                      "binding": binding, "selected_values": observations[binding]["values"]}
            publics[split].append(public)
            targets[split].append(target)
        for directory, rows in (("evaluation_public", publics[split]), ("evaluator_private", targets[split])):
            name = f"{directory}/{split}.json"
            artifacts[name] = {key: value for key, value in write(material / name, rows).items() if key != "path"}
    manifest = {"schema": "cas-teaching-preparation/1", "status": "PREPARED_NOT_TRAINED",
                "dataset_sha256": "3" * 64, "counts": {split: 64 for split in SPLITS}, "artifacts": artifacts}
    manifest_receipt = write(material / "preparation_receipt.json", manifest)
    campaign = {"schema": "cas-teaching-four-arm-campaign/1", "all_allocations_finished": True,
                "held_out_opened": False, "accepted_weights_updated": False,
                "source_sha256": SOURCE, "manifest_sha256": BUNDLE, "arms": {}}
    for arm in ARMS:
        run_id = "synthetic." + arm
        identity = {"schema": "cas-teaching-session/1", "source_sha256": SOURCE,
                    "curriculum": arm.split(".")[1], "execution_mode": "simulated"}
        identity_hash = sha256(encoded(identity)).hexdigest()
        anchor = {"schema": "cas-teaching-checkpoint-journal/1", "run_id": run_id,
                  "identity": identity, "identity_sha256": identity_hash}
        root = campaign_root / arm / "journal"
        write(root / "journal.json", anchor)
        references, previous = [], None
        for sequence in (1, 2):
            directory = root / f"txn-{sequence:08d}"
            checkpoint = write(directory / "candidate.pt", (arm + str(sequence) + " synthetic float32 flag only").encode(), raw=True)
            state_hash = sha256((arm + "state" + str(sequence)).encode()).hexdigest()
            metadata = write(directory / "metadata.json", {"schema": "cas-teaching-session/1",
                             "identity": identity, "model_state_sha256": state_hash})
            receipt = {"schema": "cas-teaching-checkpoint-journal/1", "run_id": run_id,
                       "identity_sha256": identity_hash, "sequence": sequence, "previous_receipt_sha256": previous,
                       "checkpoint_filename": "candidate.pt", "checkpoint_sha256": checkpoint["sha256"],
                       "checkpoint_bytes": checkpoint["bytes"], "metadata_filename": "metadata.json",
                       "metadata_sha256": metadata["sha256"], "metadata_bytes": metadata["bytes"],
                       "candidate_only": True, "neural_execution_by_journal": False,
                       "writer_receipt": {"sha256": checkpoint["sha256"], "synthetic": True}}
            previous = write(directory / "receipt.json", receipt)["sha256"]
            references.append({"path": f"/remote/downloaded/{arm}/journal/txn-{sequence:08d}/candidate.pt",
                               "sha256": checkpoint["sha256"], "state_sha256": state_hash,
                               "transaction": sequence, "receipt_sha256": previous})
        campaign["arms"][arm] = {"run_id": run_id, "curriculum": arm.split(".")[1], "allocation_finished": True,
                                  "initial_checkpoint": references[0], "selected_checkpoint": references[1]}
    campaign_path = tmp_path / "campaign_summary.json"
    campaign_receipt = write(campaign_path, campaign)
    declarations = {}
    for arm in ARMS:
        for phase, key in (("untrained", "initial_checkpoint"), ("trained", "selected_checkpoint")):
            for split in SPLITS:
                name = f"{arm}.{phase}.{split}.json"
                document = {"schema": "cas-teaching-blind-predictions/1", "arm": arm, "phase": phase, "split": split,
                            "run_id": campaign["arms"][arm]["run_id"], "source_sha256": SOURCE,
                            "public_sha256": canonical_sha256(publics[split]),
                            "checkpoint": campaign["arms"][arm][key], "pid": 123,
                            "private_targets_opened": False,
                            "predictions": [0] * 64 if phase == "untrained" else [row["binding"] for row in targets[split]]}
                declarations[name] = write(predictions / name, document)
    seal = {"schema": "cas-teaching-blind-prediction-seal/1", "source_sha256": SOURCE,
            "artifacts": declarations, "private_targets_opened": False, "native_execution": "UNEXECUTED"}
    seal_receipt = write(predictions / "prediction_seal.json", seal)
    return {"prediction_root": predictions, "material_root": material, "campaign_summary_path": campaign_path,
            "campaign_root": campaign_root, "expected_seal_sha256": seal_receipt["sha256"],
            "expected_campaign_sha256": campaign_receipt["sha256"], "expected_material_sha256": manifest_receipt["sha256"],
            "expected_source_sha256": SOURCE, "expected_bundle_manifest_sha256": BUNDLE}


def reseal(packet, name, change):
    root = packet["prediction_root"]
    document = json.loads((root / name).read_bytes())
    change(document)
    receipt = write(root / name, document)
    seal = json.loads((root / "prediction_seal.json").read_bytes())
    seal["artifacts"][name] = receipt
    packet["expected_seal_sha256"] = write(root / "prediction_seal.json", seal)["sha256"]


def guarded_reader(seen, allow_private=False):
    def read(path):
        if "evaluator_private" in path.parts:
            assert allow_private, "PRIVATE_OPENED_BEFORE_PACKET_REJECTION"
            assert PREDICTION_NAMES <= {item.name for item in seen}
            for arm in ARMS:
                assert any(arm in item.parts and "txn-00000002" in item.parts and item.name == "candidate.pt" for item in seen)
        seen.append(path)
        return path.read_bytes()
    return read


def test_complete_synthetic_packet_admitted_before_private_targets(packet):
    seen = []
    result = score_packet(**packet, reader=guarded_reader(seen, True))
    assert result["prediction_files_validated_before_private_reads"] == 24
    assert sum("evaluator_private" in path.parts for path in seen) == 3
    for arm in ARMS:
        for split in SPLITS:
            assert result["comparison"][arm][split] == {"before_correct": 22, "after_correct": 64,
                                                        "attempted_each": 64, "change_correct": 42}
            assert result["rule"][split]["binding_correct"] == 64
            assert result["arms"][arm]["untrained"][split]["first_error_counts"] == {"wrong_observation_binding": 42}
            assert result["rule_public_change_probes"][split]["changed_requested_source_changed_binding"] == 64
    assert result["native_execution"] == result["native_retention"] == "UNEXECUTED"
    assert result["complete_native_task_correctness"] == "UNMEASURED"
    assert result["provider_identity_proved"] is False
    assert result["neural_training_independently_verified"] is False
    assert result["identities"]["checkpoints"]["cas.aligned"]["declared_execution_mode"] == "simulated"
    assert result["unseen_program_combinations_tested"] is False
    assert "packet-reported" in result["boundary"]


@pytest.mark.parametrize("name", sorted(PREDICTION_NAMES))
def test_each_of_24_tampered_predictions_rejected_before_private(packet, name):
    path = packet["prediction_root"] / name
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(EvaluationError, match="FILE_HASH_MISMATCH"):
        score_packet(**packet, reader=guarded_reader([]))


@pytest.mark.parametrize("change,reason", [
    (lambda row: row.update(arm="generic.aligned"), "PREDICTION_IDENTITY_MISMATCH"),
    (lambda row: row.update(phase="untrained"), "PREDICTION_IDENTITY_MISMATCH"),
    (lambda row: row.update(split="test_names"), "PREDICTION_IDENTITY_MISMATCH"),
    (lambda row: row.update(run_id="forged"), "PREDICTION_IDENTITY_MISMATCH"),
    (lambda row: row.update(source_sha256="4" * 64), "PREDICTION_IDENTITY_MISMATCH"),
    (lambda row: row.update(public_sha256="4" * 64), "PREDICTION_IDENTITY_MISMATCH"),
    (lambda row: row.update(private_targets_opened=True), "PREDICTION_IDENTITY_MISMATCH"),
    (lambda row: row["checkpoint"].update(state_sha256="4" * 64), "PREDICTION_IDENTITY_MISMATCH"),
    (lambda row: row.update(predictions=[True] * 64), "PREDICTION_VALUES_INVALID"),
    (lambda row: row.update(predictions=[3] * 64), "PREDICTION_VALUES_INVALID"),
    (lambda row: row.update(predictions=[0] * 63), "PREDICTION_VALUES_INVALID"),
    (lambda row: row.update(pid=124), "PREDICTION_PROCESS_IDENTITY_CHANGED"),
])
def test_resealed_wrong_identities_or_values_rejected_before_private(packet, change, reason):
    reseal(packet, "cas.aligned.trained.test_fresh.json", change)
    with pytest.raises(EvaluationError, match=reason):
        score_packet(**packet, reader=guarded_reader([]))


@pytest.mark.parametrize("field", ["expected_seal_sha256", "expected_campaign_sha256", "expected_material_sha256",
                                  "expected_source_sha256", "expected_bundle_manifest_sha256"])
def test_external_pin_mismatch_rejected_before_private(packet, field):
    packet[field] = "5" * 64
    with pytest.raises(EvaluationError):
        score_packet(**packet, reader=guarded_reader([]))


@pytest.mark.parametrize("kind", ["extra_prediction", "missing_prediction", "public", "old_checkpoint",
                                 "selected_checkpoint", "old_receipt", "metadata", "chain_gap", "seal_inventory"])
def test_other_packet_failures_stop_before_private(packet, kind):
    root = packet["prediction_root"]
    journal = packet["campaign_root"] / "cas.aligned" / "journal"
    if kind == "extra_prediction":
        write(root / "unsealed.json", {})
    elif kind == "missing_prediction":
        (root / sorted(PREDICTION_NAMES)[-1]).rename(root.parent / "removed_prediction.json")
    elif kind == "chain_gap":
        (journal / "txn-00000001").rename(journal / ".staging-interrupted")
    elif kind == "seal_inventory":
        seal = json.loads((root / "prediction_seal.json").read_bytes())
        del seal["artifacts"][sorted(PREDICTION_NAMES)[-1]]
        packet["expected_seal_sha256"] = write(root / "prediction_seal.json", seal)["sha256"]
    else:
        paths = {"public": packet["material_root"] / "evaluation_public/test_fresh.json",
                 "old_checkpoint": journal / "txn-00000001/candidate.pt",
                 "selected_checkpoint": journal / "txn-00000002/candidate.pt",
                 "old_receipt": journal / "txn-00000001/receipt.json",
                 "metadata": journal / "txn-00000002/metadata.json"}
        path = paths[kind]
        path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(EvaluationError):
        score_packet(**packet, reader=guarded_reader([]))


def test_private_target_disagreement_rejected_even_with_resealed_material(packet):
    root = packet["material_root"]
    path = root / "evaluator_private/test_fresh.json"
    rows = json.loads(path.read_bytes())
    rows[0]["binding"] = 1
    updated = write(path, rows)
    manifest = json.loads((root / "preparation_receipt.json").read_bytes())
    manifest["artifacts"]["evaluator_private/test_fresh.json"] = updated
    packet["expected_material_sha256"] = write(root / "preparation_receipt.json", manifest)["sha256"]
    with pytest.raises(EvaluationError, match="PRIVATE_TARGET_DISAGREES_WITH_PUBLIC"):
        score_packet(**packet)


def test_binding_correctness_not_replaced_by_rounded_byte_equality():
    public = {"problem": "Requested source: blue square.", "observations": [
        {"slot": slot, "tag": tag, "values": [1.0 + slot * 1e-9] * 8}
        for slot, tag in enumerate(("blue square", "red circle", "green triangle"))]}
    assert struct.pack("<8f", *public["observations"][0]["values"]) == struct.pack("<8f", *public["observations"][1]["values"])
    measured = _measure([public], [{"binding": 0, "selected_values": [1.0] * 8, "family_id": "6" * 64}], [1])
    assert measured["binding_correct"] == 0 and measured["calculated_float32_bytes_correct"] == 1


def test_export_public_never_opens_private_and_refuses_overwrite(packet, tmp_path):
    seen = []
    path = tmp_path / "public_sets.json"
    receipt = export_public(packet["material_root"], packet["expected_material_sha256"], path,
                            reader=guarded_reader(seen))
    assert receipt["private_targets_opened"] is False
    assert len(seen) == 4
    assert set(json.loads(path.read_bytes())) == set(SPLITS)
    assert receipt["sha256"] == sha256(path.read_bytes()).hexdigest()
    with pytest.raises(FileExistsError):
        export_public(packet["material_root"], packet["expected_material_sha256"], path)


def test_optional_source_files_checked_before_private(packet, tmp_path):
    source = tmp_path / "source"
    receipt = write(source / "code.py", b"# synthetic source\n", raw=True)
    result = score_packet(**packet, source_root=source, source_pins={"code.py": receipt["sha256"]})
    assert result["identities"]["source_files"]["file_count"] == 1
    with pytest.raises(EvaluationError, match="SOURCE_PATH_OR_PIN_INVALID"):
        score_packet(**packet, source_root=source, source_pins={"../code.py": receipt["sha256"]}, reader=guarded_reader([]))


def test_incomplete_staging_reported_but_never_selected(packet):
    root = packet["campaign_root"] / "cas.aligned" / "journal"
    write(root / ".staging-crash/candidate.pt", b"uncommitted synthetic bytes", raw=True)
    result = score_packet(**packet)
    assert result["identities"]["checkpoints"]["cas.aligned"]["incomplete_staging"] == [".staging-crash"]


def test_hardlinked_checkpoint_rejected_before_private(packet, tmp_path):
    checkpoint = packet["campaign_root"] / "cas.aligned/journal/txn-00000001/candidate.pt"
    try:
        os.link(checkpoint, tmp_path / "hardlink.pt")
    except OSError as error:
        pytest.skip("Filesystem does not support this hardlink test: " + str(error))
    with pytest.raises(EvaluationError, match="JOURNAL_FILE_TYPE_INVALID"):
        score_packet(**packet, reader=guarded_reader([]))


def test_cli_export_and_score_use_guarded_pure_paths(packet, tmp_path):
    tool = Path(__file__).resolve().parents[1] / "tools/score_teaching_cycle.py"
    public_path = tmp_path / "combined_public.json"
    command = [sys.executable, "-I", "-B", str(tool), "export-public", "--material-root", str(packet["material_root"]),
               "--material-sha256", packet["expected_material_sha256"], "--output", str(public_path)]
    result = subprocess.run(command, check=True, capture_output=True, text=True, timeout=30)
    receipt = json.loads(result.stdout)
    assert receipt["sha256"] == sha256(public_path.read_bytes()).hexdigest()
    output = tmp_path / "final_score.json"
    command = [sys.executable, "-I", "-B", str(tool), "score", "--output", str(output)]
    fields = {"prediction-root": "prediction_root", "material-root": "material_root",
              "campaign-summary": "campaign_summary_path", "campaign-root": "campaign_root",
              "seal-sha256": "expected_seal_sha256", "campaign-sha256": "expected_campaign_sha256",
              "material-sha256": "expected_material_sha256", "source-sha256": "expected_source_sha256",
              "bundle-manifest-sha256": "expected_bundle_manifest_sha256"}
    for argument, key in fields.items():
        command.extend(["--" + argument, str(packet[key])])
    result = subprocess.run(command, check=True, capture_output=True, text=True, timeout=30)
    receipt = json.loads(result.stdout)
    assert receipt["sha256"] == sha256(output.read_bytes()).hexdigest()
    assert receipt["native_execution"] == "UNEXECUTED"
