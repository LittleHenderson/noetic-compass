"""Measure and emit the guardian LIVE timing-evidence document.

Gate 1, item 1. `RUNBOOK.md` section 6 requires empirical timing evidence from a
version- and hash-locked **preproduction** deployment before LIVE. This module
collects that evidence and emits the exact document the runtime validator will
accept, or it fails closed.

Two hard rules, both taken from the runtime rather than from prose:

1. **Never invent or self-attest a hash.** `TimingValidationEvidenceSha256` is
   the SHA-256 of the canonical document bytes this module emits. It is printed,
   never guessed. If measurement did not happen, no document is produced.
2. **Fail closed.** If any observed value exceeds its bound, or a required
   scenario was not exercised, this module raises `TimingEvidenceNoGo` and exits
   non-zero. LIVE is then `NO_GO`. There is no override flag, by design.

Collection is **read-only**: `logs:FilterLogEvents` and `cloudformation:
DescribeStacks`. This module never invokes a Lambda, never mutates a schedule,
never contacts the provider, and never loads a model.

The bounds and the field set below are mirrored from
`infra/runpod_guardian_live_candidate/src/guardian_runtime.py`. `verify_contract_
against_runtime()` re-reads that module and raises if the mirror has drifted, so
a runtime change cannot silently invalidate evidence produced here.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import re
import sys
from collections.abc import Iterable, Mapping, Sequence
from typing import Any, Final

SCHEMA_VERSION: Final = "cas_aws_runpod_guardian_timing_evidence.v1"

# Mirrored from guardian_runtime._TIMING_EVIDENCE_FIELDS. Exact set equality is
# enforced by the runtime validator, so a missing or extra key is a hard reject.
TIMING_EVIDENCE_FIELDS: Final = frozenset(
    {
        "schema_version",
        "aws_account_id",
        "aws_region",
        "stack_id",
        "core_lock_sha256",
        "runtime_zip_sha256",
        "measured_at_utc",
        "measurement_count",
        "measurement_kind",
        "scheduled_recovery_cadence_seconds",
        "recovery_retry_maximum_attempts",
        "recovery_event_maximum_age_seconds",
        "tested_consecutive_missed_ticks",
        "observed_recovery_gap_milliseconds",
        "observed_worker_startup_milliseconds",
        "observed_provider_stop_execution_milliseconds",
        "required_stop_lead_seconds",
        "source_evidence_manifest_sha256",
    }
)

# Mirrored from guardian_runtime._verify_timing_evidence observed_acceptance_bounds.
OBSERVED_BOUNDS_MILLISECONDS: Final = {
    "observed_recovery_gap_milliseconds": 180_000,
    "observed_worker_startup_milliseconds": 8_000,
    "observed_provider_stop_execution_milliseconds": 8_000,
}

MEASUREMENT_KIND: Final = "EMPIRICAL_NON_GUARANTEE"
SCHEDULED_RECOVERY_CADENCE_SECONDS: Final = 60
RECOVERY_RETRY_MAXIMUM_ATTEMPTS: Final = 2
RECOVERY_EVENT_MAXIMUM_AGE_SECONDS: Final = 60
REQUIRED_STOP_LEAD_SECONDS: Final = 300
MINIMUM_CONSECUTIVE_MISSED_TICKS: Final = 1
MINIMUM_MEASUREMENT_COUNT: Final = 1

_SHA256_RE: Final = re.compile(r"[0-9a-f]{64}")
_ACCOUNT_RE: Final = re.compile(r"\d{12}")

# CloudWatch Logs emits one REPORT line per Lambda invocation. "Init Duration"
# appears only on a cold start, which is exactly the worker-startup measurement.
_REPORT_RE: Final = re.compile(
    r"REPORT RequestId: (?P<request_id>[0-9a-f-]+)\s+"
    r"Duration: (?P<duration>[0-9.]+) ms\s+"
    r"Billed Duration: (?P<billed>[0-9]+) ms"
    r"(?:.*?Init Duration: (?P<init>[0-9.]+) ms)?",
    re.S,
)


class TimingEvidenceNoGo(RuntimeError):
    """Raised when evidence does not clear a gate. LIVE is NO_GO. No override."""


def canonical_bytes(value: Any) -> bytes:
    """Byte-identical to guardian_runtime._binding_canonical.

    The runtime re-serializes the parsed document and compares it to the raw
    bytes, so any deviation here is rejected as TIMING_EVIDENCE_SCHEMA_INVALID.
    """
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def sha256_hex(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def verify_contract_against_runtime(runtime_module: Any) -> None:
    """Raise if this module's mirrored contract has drifted from the runtime."""
    drift: list[str] = []
    if runtime_module.TIMING_EVIDENCE_SCHEMA != SCHEMA_VERSION:
        drift.append(
            f"schema_version {runtime_module.TIMING_EVIDENCE_SCHEMA!r} != {SCHEMA_VERSION!r}"
        )
    if set(runtime_module._TIMING_EVIDENCE_FIELDS) != set(TIMING_EVIDENCE_FIELDS):
        missing = set(runtime_module._TIMING_EVIDENCE_FIELDS) - set(TIMING_EVIDENCE_FIELDS)
        extra = set(TIMING_EVIDENCE_FIELDS) - set(runtime_module._TIMING_EVIDENCE_FIELDS)
        drift.append(f"field set drift; missing={sorted(missing)} extra={sorted(extra)}")
    if runtime_module.LIVE_STOP_LEAD_SECONDS != REQUIRED_STOP_LEAD_SECONDS:
        drift.append(
            f"stop lead {runtime_module.LIVE_STOP_LEAD_SECONDS} != {REQUIRED_STOP_LEAD_SECONDS}"
        )
    if canonical_bytes({"b": 1, "a": "é"}) != runtime_module._binding_canonical(
        {"b": 1, "a": "é"}
    ):
        drift.append("canonical serialization drift")
    if drift:
        raise TimingEvidenceNoGo("RUNTIME_CONTRACT_DRIFT: " + "; ".join(drift))


def parse_report_lines(messages: Iterable[str]) -> list[dict[str, Any]]:
    """Extract one record per Lambda REPORT line.

    Returns duration and, when the invocation was a cold start, init duration.
    Milliseconds are rounded up, so a measurement is never reported as faster
    than it was.
    """
    records: list[dict[str, Any]] = []
    for message in messages:
        match = _REPORT_RE.search(message)
        if match is None:
            continue
        init = match.group("init")
        records.append(
            {
                "request_id": match.group("request_id"),
                "duration_milliseconds": _ceil_ms(match.group("duration")),
                "init_duration_milliseconds": None if init is None else _ceil_ms(init),
            }
        )
    return records


def _ceil_ms(text: str) -> int:
    value = float(text)
    whole = int(value)
    return whole if float(whole) == value else whole + 1


def maximum_gap_milliseconds(timestamps_milliseconds: Sequence[int]) -> int:
    """Largest observed gap between consecutive scheduled recovery ticks.

    A single tick has no gap to measure, so fewer than two samples fails closed
    rather than reporting a flattering zero.
    """
    if len(timestamps_milliseconds) < 2:
        raise TimingEvidenceNoGo(
            "RECOVERY_GAP_SAMPLE_INSUFFICIENT: at least two recovery ticks are "
            f"required to measure a gap; got {len(timestamps_milliseconds)}"
        )
    ordered = sorted(timestamps_milliseconds)
    return max(second - first for first, second in zip(ordered, ordered[1:]))


def consecutive_missed_ticks(
    timestamps_milliseconds: Sequence[int],
    *,
    cadence_seconds: int = SCHEDULED_RECOVERY_CADENCE_SECONDS,
) -> int:
    """Most consecutive scheduled ticks that produced no invocation.

    EventBridge is best-effort, so this counts what was observed. It is evidence,
    never a service guarantee.
    """
    if len(timestamps_milliseconds) < 2:
        return 0
    cadence_ms = cadence_seconds * 1000
    ordered = sorted(timestamps_milliseconds)
    worst = 0
    for first, second in zip(ordered, ordered[1:]):
        missed = (second - first) // cadence_ms - 1
        worst = max(worst, int(missed))
    return worst


def build_source_manifest(
    *,
    recovery_records: Sequence[Mapping[str, Any]],
    worker_startup_records: Sequence[Mapping[str, Any]],
    stop_records: Sequence[Mapping[str, Any]],
    recovery_tick_timestamps_milliseconds: Sequence[int],
    window_start_utc: str,
    window_end_utc: str,
    log_groups: Mapping[str, str],
) -> dict[str, Any]:
    """The raw measurement record the evidence document points at by hash."""
    return {
        "collection_method": "read_only_cloudwatch_logs_filter_log_events",
        "log_groups": dict(log_groups),
        "window_start_utc": window_start_utc,
        "window_end_utc": window_end_utc,
        "recovery_tick_timestamps_milliseconds": sorted(
            int(value) for value in recovery_tick_timestamps_milliseconds
        ),
        "recovery_records": [dict(record) for record in recovery_records],
        "worker_startup_records": [dict(record) for record in worker_startup_records],
        "provider_stop_records": [dict(record) for record in stop_records],
    }


def build_timing_evidence(
    *,
    aws_account_id: str,
    aws_region: str,
    stack_id: str,
    core_lock_sha256: str,
    runtime_zip_sha256: str,
    measured_at_utc: str,
    source_manifest: Mapping[str, Any],
    observed_recovery_gap_milliseconds: int,
    observed_worker_startup_milliseconds: int,
    observed_provider_stop_execution_milliseconds: int,
    tested_consecutive_missed_ticks: int,
    measurement_count: int,
) -> tuple[dict[str, Any], bytes, str]:
    """Build, check, and canonicalize the document. Fails closed on any breach.

    Returns the document, its canonical bytes, and the SHA-256 that belongs in
    `TimingValidationEvidenceSha256`.
    """
    failures: list[str] = []

    if not _ACCOUNT_RE.fullmatch(aws_account_id):
        failures.append(f"aws_account_id malformed: {aws_account_id!r}")
    if aws_region != "us-west-2":
        failures.append(f"aws_region must be us-west-2, got {aws_region!r}")
    for name, value in (
        ("core_lock_sha256", core_lock_sha256),
        ("runtime_zip_sha256", runtime_zip_sha256),
    ):
        if not _SHA256_RE.fullmatch(value):
            failures.append(f"{name} is not a lowercase SHA-256: {value!r}")
        if value == "0" * 64:
            failures.append(f"{name} is the all-zero placeholder, not a real binding")
    if not stack_id:
        failures.append("stack_id is empty")

    observed = {
        "observed_recovery_gap_milliseconds": observed_recovery_gap_milliseconds,
        "observed_worker_startup_milliseconds": observed_worker_startup_milliseconds,
        "observed_provider_stop_execution_milliseconds": (
            observed_provider_stop_execution_milliseconds
        ),
    }
    for name, value in observed.items():
        bound = OBSERVED_BOUNDS_MILLISECONDS[name]
        if type(value) is not int:
            failures.append(f"{name} must be an int, got {type(value).__name__}")
        elif value == 0:
            # FOUND 2026-08-21, and it is the worst defect this harness had.
            #
            # The runtime validator accepts `0 <= value <= maximum`, so a
            # document reporting 0 ms passes every downstream check, hashes
            # cleanly, and can activate LIVE. But a real measurement of a real
            # operation is NEVER exactly 0 ms. Zero is not a measurement; it is
            # the ABSENCE of one, wearing a measurement's clothes.
            #
            # This was reached live: with a genuine recovery gap and worker
            # startup in hand but the STOP path unreachable under INERT, the
            # harness emitted a fully valid document carrying
            # observed_provider_stop_execution_milliseconds = 0.
            failures.append(
                f"{name} = 0 ms. Zero is not a measurement, it is the absence of "
                "one. A real operation never takes exactly 0 ms, and the runtime "
                "would accept this document, hash and all. If the measurement did "
                "not happen, no document may be produced."
            )
        elif not 1 <= value <= bound:
            failures.append(f"{name} = {value} ms is outside [1, {bound}] ms")

    if type(tested_consecutive_missed_ticks) is not int:
        failures.append("tested_consecutive_missed_ticks must be an int")
    elif tested_consecutive_missed_ticks < MINIMUM_CONSECUTIVE_MISSED_TICKS:
        failures.append(
            "section 6 requires at least one consecutive missed-tick scenario; "
            f"observed {tested_consecutive_missed_ticks}"
        )
    if type(measurement_count) is not int:
        failures.append("measurement_count must be an int")
    elif measurement_count < MINIMUM_MEASUREMENT_COUNT:
        failures.append(f"measurement_count must be >= {MINIMUM_MEASUREMENT_COUNT}")

    try:
        _parse_utc(measured_at_utc)
    except ValueError as error:
        failures.append(f"measured_at_utc unparseable: {error}")

    if failures:
        raise TimingEvidenceNoGo("LIVE_NO_GO: " + "; ".join(failures))

    manifest_bytes = canonical_bytes(dict(source_manifest))
    document = {
        "schema_version": SCHEMA_VERSION,
        "aws_account_id": aws_account_id,
        "aws_region": aws_region,
        "stack_id": stack_id,
        "core_lock_sha256": core_lock_sha256,
        "runtime_zip_sha256": runtime_zip_sha256,
        "measured_at_utc": measured_at_utc,
        "measurement_count": measurement_count,
        "measurement_kind": MEASUREMENT_KIND,
        "scheduled_recovery_cadence_seconds": SCHEDULED_RECOVERY_CADENCE_SECONDS,
        "recovery_retry_maximum_attempts": RECOVERY_RETRY_MAXIMUM_ATTEMPTS,
        "recovery_event_maximum_age_seconds": RECOVERY_EVENT_MAXIMUM_AGE_SECONDS,
        "tested_consecutive_missed_ticks": tested_consecutive_missed_ticks,
        "observed_recovery_gap_milliseconds": observed_recovery_gap_milliseconds,
        "observed_worker_startup_milliseconds": observed_worker_startup_milliseconds,
        "observed_provider_stop_execution_milliseconds": (
            observed_provider_stop_execution_milliseconds
        ),
        "required_stop_lead_seconds": REQUIRED_STOP_LEAD_SECONDS,
        "source_evidence_manifest_sha256": sha256_hex(manifest_bytes),
    }
    if set(document) != set(TIMING_EVIDENCE_FIELDS):
        raise TimingEvidenceNoGo("LIVE_NO_GO: emitted field set does not match the contract")
    raw = canonical_bytes(document)
    return document, raw, sha256_hex(raw)


def stop_lead_headroom_seconds(
    *,
    observed_recovery_gap_milliseconds: int,
    observed_worker_startup_milliseconds: int,
    observed_provider_stop_execution_milliseconds: int,
) -> int:
    """Seconds left inside the 300 s STOP lead after the observed path.

    Reported for review. A non-negative value is necessary, never sufficient:
    section 6 also requires the retry envelope, cold secret retrieval, DNS, TLS,
    and proxy invocation to fit, and those are separate measurements.
    """
    used_ms = (
        observed_recovery_gap_milliseconds
        + observed_worker_startup_milliseconds
        + observed_provider_stop_execution_milliseconds
    )
    return REQUIRED_STOP_LEAD_SECONDS - -(-used_ms // 1000)


def _parse_utc(text: str) -> _dt.datetime:
    if not text.endswith("Z"):
        raise ValueError("timestamp must end with Z")
    return _dt.datetime.fromisoformat(text[:-1]).replace(tzinfo=_dt.timezone.utc)


def collect_report_records(
    logs_client: Any, *, log_group: str, start_milliseconds: int, end_milliseconds: int
) -> tuple[list[dict[str, Any]], list[int]]:
    """Read-only CloudWatch Logs collection. Returns records and tick timestamps."""
    messages: list[str] = []
    timestamps: list[int] = []
    token: str | None = None
    while True:
        kwargs: dict[str, Any] = {
            "logGroupName": log_group,
            "startTime": start_milliseconds,
            "endTime": end_milliseconds,
            "filterPattern": "REPORT",
        }
        if token:
            kwargs["nextToken"] = token
        page = logs_client.filter_log_events(**kwargs)
        for event in page.get("events", []):
            messages.append(event.get("message", ""))
            timestamps.append(int(event.get("timestamp", 0)))
        token = page.get("nextToken")
        if not token:
            break
    return parse_report_lines(messages), timestamps


def _main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Measure guardian LIVE timing evidence from a preproduction "
            "deployment. Read-only. Fails closed; there is no override."
        )
    )
    parser.add_argument("--measurements-json", required=True)
    parser.add_argument("--out-document", required=True)
    parser.add_argument("--out-manifest", required=True)
    args = parser.parse_args(argv)

    with open(args.measurements_json, "rb") as handle:
        payload = json.load(handle)

    manifest = build_source_manifest(**payload["source_manifest"])
    document, raw, digest = build_timing_evidence(
        source_manifest=manifest, **payload["evidence"]
    )
    with open(args.out_manifest, "wb") as handle:
        handle.write(canonical_bytes(manifest))
    with open(args.out_document, "wb") as handle:
        handle.write(raw)

    headroom = stop_lead_headroom_seconds(
        observed_recovery_gap_milliseconds=document["observed_recovery_gap_milliseconds"],
        observed_worker_startup_milliseconds=document["observed_worker_startup_milliseconds"],
        observed_provider_stop_execution_milliseconds=document[
            "observed_provider_stop_execution_milliseconds"
        ],
    )
    print(f"TimingValidationEvidenceSha256 = {digest}")
    print(f"source_evidence_manifest_sha256 = {document['source_evidence_manifest_sha256']}")
    print(f"stop_lead_headroom_seconds = {headroom} (of {REQUIRED_STOP_LEAD_SECONDS})")
    print(
        "REMINDER: this document is evidence, not authority. LIVE still requires "
        "a reviewed change set. EventBridge is best-effort; no number here is a "
        "service guarantee."
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    try:
        raise SystemExit(_main(sys.argv[1:]))
    except TimingEvidenceNoGo as error:
        print(f"{error}", file=sys.stderr)
        raise SystemExit(2) from None
