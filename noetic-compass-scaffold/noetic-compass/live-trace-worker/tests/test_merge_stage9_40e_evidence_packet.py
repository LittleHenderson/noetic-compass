from __future__ import annotations

import hashlib
import importlib.util
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "merge_stage9_40e_evidence_packet.py"
)
SPEC = importlib.util.spec_from_file_location("merge_stage9_40e_evidence_packet", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
merge_stage9_40e_evidence_packet = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(merge_stage9_40e_evidence_packet)


def _write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def _readout_fixture() -> dict:
    return {
        "schema_version": "test_only_future_admitted_readout.v1",
        "status": "packet_ready_evaluation_completed",
        "created_at": "2026-05-27T00:00:00+00:00",
        "trace_id": "trace-stage9-40e",
        "run_id": "run-stage9-40e",
        "model_id": "EleutherAI/gpt-neox-20b",
        "model_family": "gpt_neox",
        "parameter_scale": "20B",
        "dataset": "D:/archive/gpt_neox_20b_augmented_400_layers_0_43.npz",
        "metadata_path": "D:/archive/gpt_neox_20b_augmented_400_layers_0_43.metadata.json",
        "best_layer": {"layer": 31, "test_acc": 0.95625, "test_macro_f1": 0.95},
        "controls": {
            "confirmed_text": {"test_acc": 0.49241071},
            "text_hash_centroid": {"test_acc": 0.5},
            "shuffled_label_hidden_best_layer": {"mean_test_acc": 0.02619},
            "compact_gloss_v0": {"status": "blocked_text_only", "text_only_acc": 1.0},
        },
        "artifacts": [
            {
                "artifact_id": "activation_dataset_npz",
                "artifact_type": "40e_activation_dataset_npz",
                "content_sha256": "a" * 64,
                "byte_count": 123,
                "storage_uri": "D:/archive/dataset.npz",
            }
        ],
        "provenance": {
            "source_pr": 102,
            "method_label": "S9-40E-ORIGINAL-BASELINE-READOUT",
        },
        "hashes": {"weights_sha": "b" * 64},
    }


def _admit_test_only_schema(monkeypatch) -> None:
    monkeypatch.setattr(
        merge_stage9_40e_evidence_packet,
        "ADMITTED_READOUT_SCHEMAS",
        frozenset({"test_only_future_admitted_readout.v1"}),
    )


def test_readout_only_packet_is_review_flag_and_never_final_verdict(tmp_path, monkeypatch):
    _admit_test_only_schema(monkeypatch)
    readout = _write_json(tmp_path / "readout.json", _readout_fixture())

    packet = merge_stage9_40e_evidence_packet.build_packet(
        readout_report=readout,
        generated_at=datetime(2026, 5, 27, tzinfo=UTC),
    )

    assert packet["schema_version"] == "cas_harness_stage9_40e_evidence_packet.v1"
    assert packet["trace_id"] == "trace-stage9-40e"
    assert packet["run_id"] == "run-stage9-40e"
    assert packet["verdict"] == "FLAG_FOR_HUMAN_REVIEW"
    assert packet["verdict"] not in {"ACCEPT", "SUPPRESS"}
    assert packet["tier_statuses"] == {
        "model": "present",
        "readout": "present",
        "baseline": "present",
        "causal": "missing",
        "control": "missing",
        "output_bridge": "missing",
        "verifier": "missing",
    }
    assert packet["causal_proof"]["blocking_reason"] == (
        "subspace_ablation report was not supplied"
    )
    assert packet["control_proof"]["blocking_reason"] == (
        "cover_discovery report was not supplied"
    )
    assert packet["output_bridge_proof"]["blocking_reason"] == (
        "output_bridge report was not supplied"
    )


def test_packet_includes_exact_corrected_baseline_fields(tmp_path, monkeypatch):
    _admit_test_only_schema(monkeypatch)
    readout = _write_json(tmp_path / "readout.json", _readout_fixture())

    packet = merge_stage9_40e_evidence_packet.build_packet(readout_report=readout)
    baseline = packet["baseline_proof"]

    assert baseline["method_label"] == "S9-40E-ORIGINAL-BASELINE-READOUT"
    assert baseline["hidden_probe_test_acc"] == 0.95625
    assert baseline["hidden_probe_test_acc_pct"] == 95.625
    assert baseline["confirmed_text_test_acc"] == 0.49241071
    assert baseline["confirmed_text_test_acc_pct"] == 49.241071
    assert baseline["text_hash_test_acc"] == 0.5
    assert baseline["text_hash_test_acc_pct"] == 50.0
    assert baseline["shuffled_label_hidden_mean_test_acc"] == 0.02619
    assert baseline["shuffled_label_hidden_mean_test_acc_pct"] == 2.619
    assert baseline["compact_gloss_v0"]["status"] == "blocked_text_only"
    assert baseline["compact_gloss_v0"]["text_only_acc_pct"] == 100.0
    assert set(baseline["source_field_checks"].values()) == {
        "matches_corrected_baseline"
    }


def test_packet_preserves_input_hashes_and_provenance(tmp_path, monkeypatch):
    _admit_test_only_schema(monkeypatch)
    readout_payload = _readout_fixture()
    readout = _write_json(tmp_path / "readout.json", readout_payload)

    packet = merge_stage9_40e_evidence_packet.build_packet(readout_report=readout)
    source_report = packet["readout_proof"]["source_report"]

    assert source_report["content_sha256"] == hashlib.sha256(readout.read_bytes()).hexdigest()
    assert packet["readout_proof"]["source_fields"]["artifacts"] == readout_payload["artifacts"]
    assert packet["readout_proof"]["source_fields"]["hashes"] == readout_payload["hashes"]
    assert packet["readout_proof"]["source_fields"]["provenance"] == readout_payload["provenance"]
    assert packet["model_proof"]["model_weight_hash"] == "b" * 64
    assert packet["provenance"]["input_count"] == 1


def test_optional_reports_remain_unverified_without_tier_validators(tmp_path, monkeypatch):
    _admit_test_only_schema(monkeypatch)
    readout = _write_json(tmp_path / "readout.json", _readout_fixture())
    ablation = _write_json(
        tmp_path / "ablation.json",
        {
            "schema_version": "stage9_40e_ablation.v0",
            "status": "completed",
            "method_label": "subspace-ablation-fixture",
            "run_id": "ablation-run",
            "artifacts": [{"artifact_id": "ablation", "content_sha256": "c" * 64}],
            "provenance": {"worker": "fixture"},
        },
    )
    cover = _write_json(
        tmp_path / "cover.json",
        {
            "schema_version": "stage9_40e_cover.v0",
            "status": "completed",
            "method_label": "cover-discovery-fixture",
            "run_id": "cover-run",
            "hashes": {"cover_sha": "d" * 64},
        },
    )
    bridge = _write_json(
        tmp_path / "bridge.json",
        {
            "schema_version": "stage9_40e_bridge.v0",
            "status": "completed",
            "method_label": "bridge-fixture",
            "run_id": "bridge-run",
            "provenance": {"bridge": "fixture"},
        },
    )

    packet = merge_stage9_40e_evidence_packet.build_packet(
        readout_report=readout,
        ablation_report=ablation,
        cover_report=cover,
        bridge_report=bridge,
    )

    assert packet["tier_statuses"]["causal"] == "unverified"
    assert packet["tier_statuses"]["control"] == "unverified"
    assert packet["tier_statuses"]["output_bridge"] == "unverified"
    assert packet["tier_statuses"]["verifier"] == "missing"
    assert packet["causal_proof"]["source_fields"] is None
    assert "no distinct strict schema" in packet["control_proof"]["blocking_reason"]
    assert packet["output_bridge_proof"]["summary"]["run_id"] == "bridge-run"
    assert packet["provenance"]["input_count"] == 4
    assert packet["verdict"] == "FLAG_FOR_HUMAN_REVIEW"


def test_writes_json_and_markdown_packet(tmp_path, monkeypatch):
    _admit_test_only_schema(monkeypatch)
    readout = _write_json(tmp_path / "readout.json", _readout_fixture())
    output_json = tmp_path / "packet.json"
    output_md = tmp_path / "packet.md"
    packet = merge_stage9_40e_evidence_packet.build_packet(readout_report=readout)

    merge_stage9_40e_evidence_packet.write_packet(packet, output_json, output_md)

    written = json.loads(output_json.read_text(encoding="utf-8"))
    markdown = output_md.read_text(encoding="utf-8")
    assert written["verdict"] == "FLAG_FOR_HUMAN_REVIEW"
    assert "Verdict: `FLAG_FOR_HUMAN_REVIEW`" in markdown
    assert "| Causal proof | missing |" in markdown
    assert "95.625%" in markdown
    assert "49.241071%" in markdown


def test_intermediate_v2_readout_schema_is_rejected(tmp_path):
    payload = _readout_fixture()
    payload["schema_version"] = "cas_harness_40_element_probe_eval.v2"
    readout = _write_json(tmp_path / "readout-v2.json", payload)

    with pytest.raises(SystemExit, match="unsupported/unadmitted readout schema"):
        merge_stage9_40e_evidence_packet.build_packet(readout_report=readout)


def test_v3_readout_must_carry_packet_eligible_binding(tmp_path):
    payload = _readout_fixture()
    payload["schema_version"] = "cas_harness_40_element_probe_eval.v3"
    payload["status"] = "diagnostic_completed_not_packet_ready"
    payload["readiness_gate"] = {
        "packet_ready": False,
        "registered_artifact_binding": {
            "status": "BLOCKED",
            "packet_eligibility": "NOT_PACKET_ELIGIBLE",
        },
    }
    readout = _write_json(tmp_path / "readout-v3.json", payload)

    with pytest.raises(SystemExit, match="known but not admitted"):
        merge_stage9_40e_evidence_packet.build_packet(readout_report=readout)


@pytest.mark.parametrize(
    "payload",
    [
        {"schema_version": "cas_harness_40_element_probe_eval.v3", "status": "packet_ready_evaluation_completed"},
        {"schema_version": "cas_harness_40_element_probe_eval.v1"},
        {},
    ],
)
def test_no_current_or_empty_readout_is_admitted(tmp_path, payload):
    readout = _write_json(tmp_path / "claimed.json", payload)

    with pytest.raises(SystemExit, match="not admitted|unadmitted"):
        merge_stage9_40e_evidence_packet.build_packet(readout_report=readout)


@pytest.mark.parametrize(
    "raw",
    [
        b'{"schema_version":"x","schema_version":"y"}',
        b'{"schema_version":"x","metric":NaN}',
        b'{"schema_version":"x","metric":Infinity}',
        b'{"schema_version":"x","metric":-Infinity}',
    ],
)
def test_duplicate_keys_and_nonfinite_numbers_are_rejected(tmp_path, raw):
    report = tmp_path / "invalid.json"
    report.write_bytes(raw)

    with pytest.raises(SystemExit, match="not valid JSON"):
        merge_stage9_40e_evidence_packet._load_json_snapshot(report)


def test_optional_stub_is_unverified_not_present(tmp_path):
    stub = _write_json(
        tmp_path / "optional.json",
        {"schema_version": "anything", "status": "completed"},
    )

    proof, artifact = merge_stage9_40e_evidence_packet._make_optional_proof(
        tier_name="subspace_ablation",
        report_path=stub,
        artifact_id="stub",
        artifact_type="stub",
    )

    assert proof["status"] == "unverified"
    assert proof["source_fields"] is None
    assert artifact is not None


def test_json_parse_and_artifact_hash_use_same_immutable_snapshot(tmp_path):
    report = _write_json(tmp_path / "report.json", {"schema_version": "original"})
    original = report.read_bytes()

    payload, snapshot = merge_stage9_40e_evidence_packet._load_json_snapshot(
        report,
        after_read_hook=lambda: report.write_text(
            '{"schema_version":"swapped"}', encoding="utf-8"
        ),
    )
    artifact = merge_stage9_40e_evidence_packet._report_artifact(
        report,
        "report",
        "test",
        snapshot,
    )

    assert payload["schema_version"] == "original"
    assert snapshot == original
    assert artifact["content_sha256"] == hashlib.sha256(original).hexdigest()
    assert artifact["content_sha256"] != hashlib.sha256(report.read_bytes()).hexdigest()
