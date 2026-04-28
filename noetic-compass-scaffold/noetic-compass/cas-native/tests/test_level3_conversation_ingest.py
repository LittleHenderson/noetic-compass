"""Torch-independent tests for Level 3 conversational ingestion helpers."""

from cas_native.training.level3_conversation_ingest import (
    level3_ingestion_errors,
    score_payload,
    summarize_level3_ingestion,
)


def _level3_record(**overrides):
    record = {
        "id": "l3conv-001",
        "bucket": "v77_omega",
        "cas_expression": "(^1^E_{F3}|A × ^1^E_{F3}|f) = ^1^E|Ω_clarity",
        "user_prompt": "How would CAS explain this named emergent?",
        "assistant_response": "The expression keeps the register integration explicit.",
        "soft_operator_targets": [0.01, 0.91, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01],
        "soft_domain_targets": [0.01, 0.01, 0.97, 0.01],
    }
    record.update(overrides)
    return record


def test_score_payload_maps_level3_soft_targets():
    record = _level3_record()
    scores = score_payload(record)

    assert scores["operator_scores"] == record["soft_operator_targets"]
    assert scores["domain_scores"] == record["soft_domain_targets"]
    assert scores["domain_averages"] == record["soft_domain_targets"]


def test_ingestion_errors_accept_valid_level3_record():
    assert level3_ingestion_errors(_level3_record()) == []


def test_ingestion_errors_reject_missing_soft_targets():
    errors = level3_ingestion_errors(
        _level3_record(soft_operator_targets=[0.5], soft_domain_targets=[1.0])
    )

    assert "operator_scores/soft_operator_targets must be a length-10 list" in errors
    assert "domain_scores/soft_domain_targets must be a length-4 list" in errors


def test_summarize_level3_ingestion_counts_buckets_and_invalid_records():
    summary = summarize_level3_ingestion(
        [
            _level3_record(id="ok"),
            _level3_record(id="bad", user_prompt=""),
        ]
    )

    assert summary["total"] == 2
    assert summary["valid"] == 1
    assert summary["invalid"] == 1
    assert summary["bucket_counts"] == {"v77_omega": 2}
