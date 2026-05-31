from __future__ import annotations

import pytest

from api.services.cas_harness_harvest import (
    HARVEST_SCHEMA_VERSION,
    capture_live_audit_harvest,
    harvest_corpus_path,
    iter_harvest_records,
)


@pytest.fixture(autouse=True)
def _isolated_harvest_store(tmp_path, monkeypatch):
    monkeypatch.setenv("CAS_HARNESS_HARVEST_STORE_DIR", str(tmp_path))
    yield


def _packet(*, is_real_model, trace_id="cas-live-abc-0001"):
    model = {"model_key": "EleutherAI/pythia-160m", "runtime": "atlas_live_worker"}
    if is_real_model is not None:
        model["manifest"] = {"is_real_model": is_real_model}
    return {
        "schema_version": "cas_harness_evidence_packet_v1",
        "trace_id": trace_id,
        "model": model,
        "input": {
            "text": "Audit this.",
            "audit_id": "cas-audit-xyz",
            "audit_mode": "BALANCED",
            "selected_modules": ["active_trace"],
        },
        "output": {"text": " Hello world", "token_count": 2, "tokens": []},
        "readout": {
            "status": "present",
            "axis": "live_trace_worker",
            "label": "hosted_open_weight_trace",
            "confidence": 0.75,
            "cover_class_count": 1,
        },
        "provenance": {
            "method_label": "cas_harness_live_worker_v1",
            "code_commit_sha": "deadbeef",
            "source_reports": ["atlas_live_worker_sessions_dump"],
        },
    }


def test_real_model_harvest_is_not_demo_fallback():
    record = capture_live_audit_harvest(_packet(is_real_model=True))
    assert record["schema_version"] == HARVEST_SCHEMA_VERSION
    assert record["model"]["is_real_model"] is True
    assert record["model_io_is_demo_fallback"] is False
    assert record["output"]["text"] == " Hello world"
    # Foreign-output retention policy is stamped explicitly so a future
    # re-enable of the ban can filter these rows back out.
    assert record["policy"]["foreign_output_retained"] is True
    assert record["policy"]["answer_side_rule"] == "ablated"


def test_absent_is_real_model_is_conservatively_demo_fallback():
    record = capture_live_audit_harvest(_packet(is_real_model=None))
    assert record["model"]["is_real_model"] is None
    assert record["model_io_is_demo_fallback"] is True


def test_false_is_real_model_is_demo_fallback():
    record = capture_live_audit_harvest(_packet(is_real_model=False))
    assert record["model_io_is_demo_fallback"] is True


def test_harvest_appends_jsonl_joinable_on_trace_id():
    capture_live_audit_harvest(_packet(is_real_model=True, trace_id="cas-live-a-1"))
    capture_live_audit_harvest(
        _packet(is_real_model=True, trace_id="cas-live-b-2"),
        verdict="FLAG_FOR_HUMAN_REVIEW",
        confidence=0.0,
        verdict_status="evidence_gated",
    )

    records = list(iter_harvest_records())
    assert [r["trace_id"] for r in records] == ["cas-live-a-1", "cas-live-b-2"]
    # Join key is explicit and points at the SDG native_nl.v1 corpus.
    assert all(r["join"] == {"key": "trace_id", "pairs_with": "native_nl.v1"} for r in records)
    # trace_id and evidence_packet_trace_id agree so the verdict + SDG row both
    # join back to the same harvested signal.
    assert records[1]["evidence_packet_trace_id"] == "cas-live-b-2"
    assert records[1]["verdict"] == {
        "verdict": "FLAG_FOR_HUMAN_REVIEW",
        "confidence": 0.0,
        "status": "evidence_gated",
    }
    assert records[0]["verdict"]["status"] == "pending_verdict_gate"


def test_corpus_path_under_configured_store(tmp_path):
    capture_live_audit_harvest(_packet(is_real_model=True))
    assert harvest_corpus_path() == tmp_path / "harvest.jsonl"
    assert harvest_corpus_path().exists()
