"""Deterministic custody checks; fixtures are not authorization for execution."""
import copy
from datetime import datetime, timedelta, timezone

import pytest

import q4_conversation_authorization as auth
from q4_checkpoint import canonical, digest


@pytest.fixture
def record(tmp_path):
    # Synthetic plan only: no model, source data, device use, or real job.
    plan = {"task": "T14_R1_G_ENGINEERING_SMOKE", "device": "cuda:0", "max_updates": 2,
            "max_wall_seconds": 30, "resume": False, "source_pins": {"fixture": "TEST_ONLY"}}
    value = {"schema": auth.SCHEMA, "plan_sha256": digest(canonical(plan)),
             "provenance": {"source_role": "user", "source": "CURRENT_CODEX_CONVERSATION",
                 "source_reference": "SYNTHETIC_TEST_FIXTURE_NOT_EXECUTABLE_PERMISSION",
                 "recorded_by": "CODEX_AGENT_TRANSCRIPTION",
                 "captured_at_utc": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
                 "user_quote": auth.USER_AUTHORIZATION_QUOTE,
                 "user_quote_sha256": digest(auth.USER_AUTHORIZATION_QUOTE.encode("utf-8"))},
             "execution_scope": {"task": plan["task"], "device": plan["device"], "max_updates": 2,
                                 "max_wall_seconds": 30, "no_retries": True}}
    return plan, value, tmp_path / "TEST_ONLY_transcription.json"


def write_record(record):
    plan, value, path = record
    raw = canonical(value) + b"\n"
    path.write_bytes(raw)
    return plan, path, digest(raw)


def test_valid_record_returns_integrity_receipt_without_identity_claim(record):
    args = write_record(record)
    receipt = auth.verify_conversation_authorization(*args)
    assert receipt == {"mode": "EXPLICIT_USER_CONVERSATION", "record_sha256": args[2],
                       "plan_sha256": digest(canonical(record[0])),
                       "user_quote_sha256": record[1]["provenance"]["user_quote_sha256"],
                       "identity_verification": "LIVE_CONVERSATION_NOT_CRYPTOGRAPHIC"}


def test_record_hash_is_raw_and_detects_changed_bytes(record):
    plan, path, expected = write_record(record)
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(auth.ConversationAuthorizationError, match="record SHA-256 mismatch"):
        auth.verify_conversation_authorization(plan, path, expected)


@pytest.mark.parametrize("fingerprint", [None, "", "F" * 64, "0" * 63, "0" * 65, "0" * 64])
def test_missing_malformed_or_wrong_external_record_digest_is_refused(record, fingerprint):
    plan, path, _ = write_record(record)
    with pytest.raises(auth.ConversationAuthorizationError):
        auth.verify_conversation_authorization(plan, path, fingerprint)


def test_missing_record_is_refused(record):
    plan, _, path = record
    with pytest.raises(auth.ConversationAuthorizationError, match="UNAVAILABLE"):
        auth.verify_conversation_authorization(plan, path, "0" * 64)


@pytest.mark.parametrize("key,value", [("device", "cuda:1"), ("max_updates", 3),
                                      ("max_wall_seconds", 31), ("source_pins", {"fixture": "CHANGED"})])
def test_any_bound_plan_change_is_refused(record, key, value):
    plan, path, expected = write_record(record)
    changed = copy.deepcopy(plan)
    changed[key] = value
    with pytest.raises(auth.ConversationAuthorizationError, match="plan SHA-256 mismatch"):
        auth.verify_conversation_authorization(changed, path, expected)


@pytest.mark.parametrize("key,value", [("source_role", "assistant"), ("source", "LOCAL_FILE"),
    ("recorded_by", "OWNER_SIGNED"), ("source_reference", " "), ("source_reference", 9),
    ("user_quote", "APPROVED"), ("user_quote_sha256", "0" * 64)])
def test_resealed_record_with_false_provenance_is_refused(record, key, value):
    record[1]["provenance"][key] = value
    with pytest.raises(auth.ConversationAuthorizationError):
        auth.verify_conversation_authorization(*write_record(record))


def test_quote_and_its_digest_cannot_both_be_replaced(record):
    record[1]["provenance"]["user_quote"] = "This text is not a live instruction."
    record[1]["provenance"]["user_quote_sha256"] = digest(record[1]["provenance"]["user_quote"].encode())
    with pytest.raises(auth.ConversationAuthorizationError, match="quote differs"):
        auth.verify_conversation_authorization(*write_record(record))


@pytest.mark.parametrize("timestamp", [None, 20260922, "invalid", "2026-01-01T00:00:00",
                                      "9999-01-01T00:00:00+00:00"])
def test_missing_timezone_malformed_and_future_capture_times_are_refused(record, timestamp):
    record[1]["provenance"]["captured_at_utc"] = timestamp
    with pytest.raises(auth.ConversationAuthorizationError, match="capture timestamp"):
        auth.verify_conversation_authorization(*write_record(record))


@pytest.mark.parametrize("section", [None, "provenance", "execution_scope"])
@pytest.mark.parametrize("change", ["extra", "missing", "not_object"])
def test_exact_record_schema_required(record, section, change):
    value = record[1] if section is None else record[1][section]
    if change == "extra":
        value["signature_base64"] = "MUST_NOT_IMPLY_SIGNATURE"
    elif change == "missing":
        del value[next(iter(value))]
    elif section is None:
        record = (record[0], [], record[2])
    else:
        record[1][section] = []
    with pytest.raises(auth.ConversationAuthorizationError):
        auth.verify_conversation_authorization(*write_record(record))


@pytest.mark.parametrize("key,value", [("task", "ANOTHER_JOB"), ("device", "cpu"),
    ("max_updates", 3), ("max_updates", True), ("max_updates", 2.0),
    ("max_wall_seconds", 31), ("no_retries", False), ("no_retries", 1)])
def test_resealed_record_cannot_change_execution_scope(record, key, value):
    record[1]["execution_scope"][key] = value
    with pytest.raises(auth.ConversationAuthorizationError):
        auth.verify_conversation_authorization(*write_record(record))


@pytest.mark.parametrize("key,value", [("max_updates", 129), ("max_wall_seconds", 1801),
                                      ("max_updates", 0), ("device", "cpu"), ("resume", True)])
def test_record_cannot_expand_hard_work_limits_even_with_new_plan_digest(record, key, value):
    record[0][key] = value
    if key in record[1]["execution_scope"]:
        record[1]["execution_scope"][key] = value
    record[1]["plan_sha256"] = digest(canonical(record[0]))
    with pytest.raises(auth.ConversationAuthorizationError):
        auth.verify_conversation_authorization(*write_record(record))


@pytest.mark.parametrize("raw", [b'{"schema":1,"schema":2}', b'{"schema":NaN}',
                               b'{"schema":1e999}', b'\xff', b'{"schema":"\\ud800"}'])
def test_strict_json_rejects_ambiguous_or_unsupported_bytes(record, raw):
    plan, _, path = record
    path.write_bytes(raw)
    with pytest.raises(auth.ConversationAuthorizationError, match="malformed JSON"):
        auth.verify_conversation_authorization(plan, path, digest(raw))


def test_record_read_is_bounded(record):
    plan, _, path = record
    raw = b" " * (auth.MAX_RECORD_BYTES + 1)
    path.write_bytes(raw)
    with pytest.raises(auth.ConversationAuthorizationError, match="byte limit"):
        auth.verify_conversation_authorization(plan, path, digest(raw))
