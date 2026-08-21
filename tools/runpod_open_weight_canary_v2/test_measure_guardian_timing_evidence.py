"""Offline tests for the Gate 1 timing-evidence harness.

No test imports boto3, opens a socket, contacts AWS or RunPod, or creates a paid
resource. The AWS Logs surface is a fake.

The load-bearing test is `test_emitted_document_passes_the_real_runtime_validator`.
It feeds this harness's output into the runtime's own `_verify_timing_evidence`,
so the harness cannot drift into producing a document only it would accept.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import hashlib
import json
import sys

import pytest

HERE = Path(__file__).resolve()
REPO = HERE.parents[2]
TOOLS = REPO / "tools" / "runpod_open_weight_canary_v2"
SRC = REPO / "infra" / "runpod_guardian_live_candidate" / "src"
for path in (TOOLS, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import aws_production_guardian_core as guardian  # noqa: E402
import guardian_runtime as runtime  # noqa: E402
import measure_guardian_timing_evidence as harness  # noqa: E402


ACCOUNT = "123456789012"
REGION = "us-west-2"
STACK_ID = "arn:aws:cloudformation:us-west-2:123456789012:stack/guardian/uuid"
CORE_LOCK = "c" * 64
RUNTIME_ZIP = "1" * 64
BASE = datetime(2026, 8, 21, 1, 0, 0, tzinfo=timezone.utc)


def _manifest():
    return harness.build_source_manifest(
        recovery_records=[{"request_id": "r1", "duration_milliseconds": 400}],
        worker_startup_records=[
            {"request_id": "r1", "init_duration_milliseconds": 6_200}
        ],
        stop_records=[{"request_id": "s1", "duration_milliseconds": 5_100}],
        recovery_tick_timestamps_milliseconds=[0, 60_000, 240_000],
        window_start_utc=guardian.iso_utc(BASE),
        window_end_utc=guardian.iso_utc(BASE + timedelta(minutes=30)),
        log_groups={"recovery": "/aws/lambda/recovery", "stop": "/aws/lambda/stop"},
    )


def _evidence(**overrides):
    payload = {
        "aws_account_id": ACCOUNT,
        "aws_region": REGION,
        "stack_id": STACK_ID,
        "core_lock_sha256": CORE_LOCK,
        "runtime_zip_sha256": RUNTIME_ZIP,
        "measured_at_utc": guardian.iso_utc(BASE),
        "observed_recovery_gap_milliseconds": 180_000,
        "observed_worker_startup_milliseconds": 6_200,
        "observed_provider_stop_execution_milliseconds": 5_100,
        "tested_consecutive_missed_ticks": 2,
        "measurement_count": 25,
    }
    payload.update(overrides)
    return harness.build_timing_evidence(source_manifest=_manifest(), **payload)


# --- the contract mirror -----------------------------------------------------


def test_mirrored_contract_matches_the_runtime():
    harness.verify_contract_against_runtime(runtime)


def test_contract_drift_is_detected(monkeypatch):
    monkeypatch.setattr(runtime, "LIVE_STOP_LEAD_SECONDS", 299)
    with pytest.raises(harness.TimingEvidenceNoGo, match="RUNTIME_CONTRACT_DRIFT"):
        harness.verify_contract_against_runtime(runtime)


def test_canonical_bytes_match_the_runtime_serializer():
    value = {"z": 1, "a": "é", "n": [1, 2]}
    assert harness.canonical_bytes(value) == runtime._binding_canonical(value)


# --- the load-bearing round trip ---------------------------------------------


def test_emitted_document_passes_the_real_runtime_validator():
    document, raw, digest = _evidence()
    binding = {
        "aws_account_id": ACCOUNT,
        "aws_region": REGION,
        "stack_id": STACK_ID,
        "core_lock_sha256": CORE_LOCK,
        "runtime_zip_sha256": RUNTIME_ZIP,
    }
    # No exception means the runtime accepts exactly what this harness emitted.
    runtime._verify_timing_evidence(
        raw, binding, {"TIMING_VALIDATION_EVIDENCE_SHA256": digest}
    )
    assert set(document) == set(runtime._TIMING_EVIDENCE_FIELDS)
    assert digest == hashlib.sha256(raw).hexdigest()


def test_runtime_rejects_the_document_under_a_wrong_declared_hash():
    _, raw, _ = _evidence()
    binding = {
        "aws_account_id": ACCOUNT,
        "aws_region": REGION,
        "stack_id": STACK_ID,
        "core_lock_sha256": CORE_LOCK,
        "runtime_zip_sha256": RUNTIME_ZIP,
    }
    with pytest.raises(runtime.ActivationError, match="TIMING_EVIDENCE_OBJECT_HASH_MISMATCH"):
        runtime._verify_timing_evidence(
            raw, binding, {"TIMING_VALIDATION_EVIDENCE_SHA256": "f" * 64}
        )


def test_manifest_hash_in_the_document_matches_the_manifest_bytes():
    document, _, _ = _evidence()
    expected = hashlib.sha256(harness.canonical_bytes(_manifest())).hexdigest()
    assert document["source_evidence_manifest_sha256"] == expected


# --- fail-closed behaviour ---------------------------------------------------


@pytest.mark.parametrize(
    "field,value",
    [
        ("observed_recovery_gap_milliseconds", 180_001),
        ("observed_worker_startup_milliseconds", 8_001),
        ("observed_provider_stop_execution_milliseconds", 8_001),
    ],
)
def test_one_millisecond_over_a_bound_is_no_go(field, value):
    with pytest.raises(harness.TimingEvidenceNoGo, match="LIVE_NO_GO"):
        _evidence(**{field: value})


@pytest.mark.parametrize(
    "field,bound",
    [
        ("observed_recovery_gap_milliseconds", 180_000),
        ("observed_worker_startup_milliseconds", 8_000),
        ("observed_provider_stop_execution_milliseconds", 8_000),
    ],
)
def test_exactly_on_the_bound_is_accepted(field, bound):
    document, _, _ = _evidence(**{field: bound})
    assert document[field] == bound


def test_zero_missed_ticks_is_no_go():
    with pytest.raises(harness.TimingEvidenceNoGo, match="consecutive missed-tick"):
        _evidence(tested_consecutive_missed_ticks=0)


def test_all_zero_placeholder_hash_is_no_go():
    with pytest.raises(harness.TimingEvidenceNoGo, match="all-zero placeholder"):
        _evidence(core_lock_sha256="0" * 64)


def test_negative_observation_is_no_go():
    with pytest.raises(harness.TimingEvidenceNoGo, match="outside"):
        _evidence(observed_worker_startup_milliseconds=-1)


# --- zero is the absence of a measurement, not a measurement -----------------
#
# FOUND LIVE 2026-08-21. With a real recovery gap and worker startup in hand but
# the STOP path unreachable under INERT, the harness emitted a fully valid,
# hashable document carrying observed_provider_stop_execution_milliseconds = 0.
# The runtime accepts 0 <= value <= maximum, so that document would have passed
# every downstream check and could have activated LIVE.


@pytest.mark.parametrize("field", [
    "observed_recovery_gap_milliseconds",
    "observed_worker_startup_milliseconds",
    "observed_provider_stop_execution_milliseconds",
])
def test_zero_is_refused_for_every_observed_measurement(field):
    with pytest.raises(harness.TimingEvidenceNoGo, match="not a measurement"):
        _evidence(**{field: 0})


def test_the_exact_live_case_that_slipped_through_is_now_refused():
    # Real gap, real startup, unmeasured STOP -- the combination that produced a
    # signable document with a fabricated number in it.
    with pytest.raises(harness.TimingEvidenceNoGo, match="no document may be produced"):
        _evidence(
            observed_recovery_gap_milliseconds=125424,
            observed_worker_startup_milliseconds=190,
            observed_provider_stop_execution_milliseconds=0,
            tested_consecutive_missed_ticks=1,
            measurement_count=18)


def test_one_millisecond_is_accepted_so_the_floor_is_zero_not_a_range():
    doc, _, _ = _evidence(observed_worker_startup_milliseconds=1)
    assert doc["observed_worker_startup_milliseconds"] == 1


def test_boolean_is_not_accepted_as_an_integer():
    # bool is a subclass of int; the runtime uses `type(x) is not int`, so this
    # harness must reject it the same way rather than emitting True as 1.
    with pytest.raises(harness.TimingEvidenceNoGo, match="must be an int"):
        _evidence(measurement_count=True)


def test_zero_measurement_count_is_no_go():
    with pytest.raises(harness.TimingEvidenceNoGo, match="measurement_count"):
        _evidence(measurement_count=0)


def test_wrong_region_is_no_go():
    with pytest.raises(harness.TimingEvidenceNoGo, match="us-west-2"):
        _evidence(aws_region="us-east-1")


def test_unparseable_timestamp_is_no_go():
    with pytest.raises(harness.TimingEvidenceNoGo, match="measured_at_utc"):
        _evidence(measured_at_utc="2026-08-21 01:00:00")


def test_every_failure_is_reported_not_just_the_first():
    with pytest.raises(harness.TimingEvidenceNoGo) as caught:
        _evidence(aws_region="eu-west-1", measurement_count=0)
    message = str(caught.value)
    assert "us-west-2" in message and "measurement_count" in message


# --- measurement primitives --------------------------------------------------


def test_report_line_parsing_separates_cold_start_from_warm():
    warm = (
        "REPORT RequestId: 11111111-1111-1111-1111-111111111111\t"
        "Duration: 12.34 ms\tBilled Duration: 13 ms\tMemory Size: 256 MB\t"
        "Max Memory Used: 90 MB\t\n"
    )
    cold = (
        "REPORT RequestId: 22222222-2222-2222-2222-222222222222\t"
        "Duration: 400.10 ms\tBilled Duration: 401 ms\tMemory Size: 256 MB\t"
        "Max Memory Used: 95 MB\tInit Duration: 6199.50 ms\t\n"
    )
    records = harness.parse_report_lines([warm, cold, "not a report line"])
    assert len(records) == 2
    assert records[0]["init_duration_milliseconds"] is None
    assert records[0]["duration_milliseconds"] == 13  # 12.34 rounded UP
    assert records[1]["init_duration_milliseconds"] == 6_200  # 6199.50 rounded UP


def test_durations_round_up_so_a_measurement_is_never_flattered():
    records = harness.parse_report_lines(
        ["REPORT RequestId: a-b\tDuration: 7999.01 ms\tBilled Duration: 8000 ms"]
    )
    assert records[0]["duration_milliseconds"] == 8_000


def test_maximum_gap_needs_two_samples():
    with pytest.raises(harness.TimingEvidenceNoGo, match="SAMPLE_INSUFFICIENT"):
        harness.maximum_gap_milliseconds([1_000])


def test_maximum_gap_is_order_independent():
    assert harness.maximum_gap_milliseconds([240_000, 0, 60_000]) == 180_000


def test_consecutive_missed_ticks_counts_the_worst_run():
    # ticks at 0s, 60s, then a jump to 240s = two missed 60s ticks.
    assert harness.consecutive_missed_ticks([0, 60_000, 240_000]) == 2
    assert harness.consecutive_missed_ticks([0, 60_000, 120_000]) == 0
    assert harness.consecutive_missed_ticks([0]) == 0


def test_stop_lead_headroom_is_reported_in_whole_seconds():
    headroom = harness.stop_lead_headroom_seconds(
        observed_recovery_gap_milliseconds=180_000,
        observed_worker_startup_milliseconds=6_200,
        observed_provider_stop_execution_milliseconds=5_100,
    )
    # 191_300 ms rounds UP to 192 s; 300 - 192 = 108 s remaining.
    assert headroom == 108


def test_stop_lead_headroom_can_go_negative_rather_than_clamping():
    headroom = harness.stop_lead_headroom_seconds(
        observed_recovery_gap_milliseconds=180_000,
        observed_worker_startup_milliseconds=8_000,
        observed_provider_stop_execution_milliseconds=8_000,
    )
    assert headroom == 104
    worse = harness.stop_lead_headroom_seconds(
        observed_recovery_gap_milliseconds=400_000,
        observed_worker_startup_milliseconds=0,
        observed_provider_stop_execution_milliseconds=0,
    )
    assert worse == -100


# --- read-only collection against a fake Logs client -------------------------


class _FakeLogs:
    """Paginating CloudWatch Logs fake. Records calls; performs no I/O."""

    def __init__(self, pages):
        self._pages = pages
        self.calls = []

    def filter_log_events(self, **kwargs):
        self.calls.append(kwargs)
        return self._pages[len(self.calls) - 1]


def test_collection_follows_pagination_and_is_read_only():
    pages = [
        {
            "events": [
                {"message": "REPORT RequestId: a\tDuration: 1.0 ms\tBilled Duration: 1 ms",
                 "timestamp": 0}
            ],
            "nextToken": "page-2",
        },
        {
            "events": [
                {"message": "REPORT RequestId: b\tDuration: 2.0 ms\tBilled Duration: 2 ms",
                 "timestamp": 60_000}
            ]
        },
    ]
    client = _FakeLogs(pages)
    records, timestamps = harness.collect_report_records(
        client, log_group="/aws/lambda/recovery", start_milliseconds=0, end_milliseconds=1
    )
    assert len(records) == 2
    assert timestamps == [0, 60_000]
    assert len(client.calls) == 2
    assert client.calls[1]["nextToken"] == "page-2"
    assert all(call["filterPattern"] == "REPORT" for call in client.calls)


def test_cli_writes_both_documents_and_prints_the_hash(tmp_path, capsys):
    payload = {
        "source_manifest": {
            "recovery_records": [{"request_id": "r1", "duration_milliseconds": 400}],
            "worker_startup_records": [
                {"request_id": "r1", "init_duration_milliseconds": 6_200}
            ],
            "stop_records": [{"request_id": "s1", "duration_milliseconds": 5_100}],
            "recovery_tick_timestamps_milliseconds": [0, 60_000, 240_000],
            "window_start_utc": guardian.iso_utc(BASE),
            "window_end_utc": guardian.iso_utc(BASE + timedelta(minutes=30)),
            "log_groups": {"recovery": "/aws/lambda/recovery"},
        },
        "evidence": {
            "aws_account_id": ACCOUNT,
            "aws_region": REGION,
            "stack_id": STACK_ID,
            "core_lock_sha256": CORE_LOCK,
            "runtime_zip_sha256": RUNTIME_ZIP,
            "measured_at_utc": guardian.iso_utc(BASE),
            "observed_recovery_gap_milliseconds": 180_000,
            "observed_worker_startup_milliseconds": 6_200,
            "observed_provider_stop_execution_milliseconds": 5_100,
            "tested_consecutive_missed_ticks": 2,
            "measurement_count": 25,
        },
    }
    measurements = tmp_path / "measurements.json"
    measurements.write_text(json.dumps(payload), encoding="utf-8")
    document = tmp_path / "timing-evidence.json"
    manifest = tmp_path / "manifest.json"

    assert harness._main(
        [
            "--measurements-json", str(measurements),
            "--out-document", str(document),
            "--out-manifest", str(manifest),
        ]
    ) == 0

    raw = document.read_bytes()
    printed = capsys.readouterr().out
    assert hashlib.sha256(raw).hexdigest() in printed
    assert "evidence, not authority" in printed
    assert json.loads(raw)["schema_version"] == runtime.TIMING_EVIDENCE_SCHEMA
