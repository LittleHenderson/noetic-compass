"""Tests for Shape 2 transition record writer."""

from __future__ import annotations

import json
from pathlib import Path

from cas_synthetic.generator.cas_transformer import CASTransformerTurnGenerator
from cas_synthetic.schemas.shape2 import (
    SHAPE2_SCHEMA_VERSION,
    Shape2RecordWriter,
)


def _fixture_path(name: str) -> Path:
    return Path(__file__).with_name(name)


def test_shape2_writer_converts_accepted_turn_record_to_training_tuple():
    turn = next(CASTransformerTurnGenerator(seed=7).iter_records(1))
    output = _fixture_path("_shape2_writer_fixture.jsonl")
    writer = Shape2RecordWriter(output)

    try:
        record = writer.write_from_turn(turn)

        assert record.validate() == []
        assert record.prompt == turn.prompt
        assert record.rendered_response == turn.response
        assert record.rf_score == 1.0
        assert record.accepted_candidate_id == f"{turn.id}:accepted"
        assert record.pre_state["trace_node_count"] == len(turn.trace)
        assert record.validation_artifact["record_valid"] is True
        assert record.validation_artifact["recovery"]["passed"] is True
        assert record.recovered_trace["passed"] is True
        assert record.provenance["source_record_id"] == turn.id

        lines = output.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1
        payload = json.loads(lines[0])
        assert payload["schema_version"] == SHAPE2_SCHEMA_VERSION
        assert payload["candidates"][0]["accepted"] is True
        assert payload["accepted_transition"]["cas_expression"] == turn.cas_expression
        diagram = payload["accepted_transition"]["diagram"]
        assert diagram["kind"] == "cas_diagram"
        assert diagram["schema_version"] == "1.0"
        assert diagram["available"] is True
        assert diagram["nodes"] or diagram["edges"] or diagram["containers"]
        summary = payload["accepted_transition"]["diagram_summary"]
        assert summary["available"] is True
        assert summary["schema_version"] == "1.0"
        assert summary["node_count"] == len(diagram["nodes"])
        assert summary["edge_count"] == len(diagram["edges"])
        assert summary["container_count"] == len(diagram["containers"])
        assert len(summary["graph_hash"]) == 64
        assert payload["perturbations"]
    finally:
        if output.exists():
            output.unlink()


def test_shape2_record_rejects_missing_accepted_candidate():
    turn = next(CASTransformerTurnGenerator(seed=7).iter_records(1))
    record = Shape2RecordWriter("unused.jsonl").from_turn_record(turn)
    bad_record = type(record)(
        id=record.id,
        prompt=record.prompt,
        pre_state=record.pre_state,
        candidates=record.candidates,
        accepted_candidate_id="missing",
        accepted_transition=record.accepted_transition,
        validation_artifact=record.validation_artifact,
        rendered_response=record.rendered_response,
        recovered_trace=record.recovered_trace,
        rf_score=record.rf_score,
        perturbations=record.perturbations,
        provenance=record.provenance,
    )

    errors = bad_record.validate()

    assert any("is not present in candidates" in error for error in errors)


def test_shape2_writer_writes_many_records():
    turns = list(CASTransformerTurnGenerator(seed=11).iter_records(3))
    output = _fixture_path("_shape2_writer_many_fixture.jsonl")
    writer = Shape2RecordWriter(output)

    try:
        records = writer.write_many_from_turns(turns)

        assert len(records) == 3
        assert all(record.rf_score == 1.0 for record in records)
        assert len(output.read_text(encoding="utf-8").splitlines()) == 3
    finally:
        if output.exists():
            output.unlink()
