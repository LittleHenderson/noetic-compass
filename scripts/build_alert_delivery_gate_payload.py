#!/usr/bin/env python3
"""Convert one secret-safe provider drill artifact into strict gate evidence.

The runtime monitor artifact remains non-authoritative and ``OPEN``.  This
collector does not publish it.  It revalidates the exact machine receipts and
produces the canonical payload that an independently authorized publisher may
place at the production ``alert_delivery`` authority endpoint.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Mapping, Sequence


EVIDENCE_SCHEMA_VERSION = "cas_harness_customer_production_gate_evidence.v2"
SAFE_ARTIFACT_SCHEMA = "cas_runtime_alert_safe_receipts.v2"
REPOSITORY = "LittleHenderson/noetic-compass"
PRODUCTION_API_ORIGIN = "https://noetic-compass-api.onrender.com"
PRODUCTION_SERVICE_ID = "srv-d82ph683kofs73d210e0"
AUTHORITY_URI = f"{PRODUCTION_API_ORIGIN}/internal/acceptance/alert-delivery"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
DEPLOY_ID_RE = re.compile(r"^dep-[a-z0-9]{20}$")


class EvidenceError(ValueError):
    """The provider artifact cannot honestly support alert-delivery evidence."""


def _json_object_without_duplicates(raw: bytes) -> Mapping[str, Any]:
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise EvidenceError("provider artifact is not UTF-8") from exc

    def object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise EvidenceError("provider artifact contains a duplicate key")
            result[key] = value
        return result

    try:
        document = json.loads(text, object_pairs_hook=object_pairs)
    except EvidenceError:
        raise
    except json.JSONDecodeError as exc:
        raise EvidenceError("provider artifact is not JSON") from exc
    if not isinstance(document, Mapping):
        raise EvidenceError("provider artifact must be one JSON object")
    return document


def _exact_keys(value: Any, expected: set[str], name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != expected:
        raise EvidenceError(f"{name} fields are invalid")
    return value


def _sha256(value: Any, name: str) -> str:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise EvidenceError(f"{name} is not a SHA-256 digest")
    return value


def _timestamp(value: Any, name: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise EvidenceError(f"{name} is not canonical UTC")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise EvidenceError(f"{name} is not a timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise EvidenceError(f"{name} is not UTC")
    if parsed.microsecond:
        raise EvidenceError(f"{name} must use whole seconds")
    canonical = parsed.astimezone(UTC).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )
    if value != canonical:
        raise EvidenceError(f"{name} is not canonical UTC")
    return parsed.astimezone(UTC)


def _timestamp_text(value: Any, name: str) -> str:
    parsed = _timestamp(value, name)
    return parsed.isoformat(timespec="seconds").replace("+00:00", "Z")


def build_payload(
    artifact: Mapping[str, Any],
    *,
    artifact_sha256: str,
    master_head_sha: str,
    deploy_id: str,
) -> dict[str, Any]:
    _exact_keys(
        artifact,
        {
            "schema_version",
            "claim_status",
            "provider_mode",
            "lifecycle",
            "provider_obligation_required",
            "secondary_drill_requested",
            "provider_obligation_satisfied",
            "event",
            "incident_channel",
            "primary_on_call",
            "acknowledgement",
            "secondary_escalation",
            "outcome",
            "errors",
        },
        "provider artifact",
    )
    if artifact.get("schema_version") != SAFE_ARTIFACT_SCHEMA:
        raise EvidenceError("provider artifact schema is not the drill schema")
    if artifact.get("claim_status") != "OPEN":
        raise EvidenceError("source provider artifact must remain OPEN")
    if artifact.get("provider_mode") != "webhook_v1":
        raise EvidenceError("provider artifact was not produced by webhook_v1")
    if artifact.get("lifecycle") != "failing":
        raise EvidenceError("provider drill must be captured during a failing incident")
    for field in (
        "provider_obligation_required",
        "secondary_drill_requested",
        "provider_obligation_satisfied",
    ):
        if artifact.get(field) is not True:
            raise EvidenceError(f"provider artifact {field} must be true")
    if artifact.get("errors") != []:
        raise EvidenceError("provider artifact contains errors")
    if artifact.get("outcome") != (
        "primary_delivered_acknowledged_secondary_drill_escalated"
    ):
        raise EvidenceError("provider artifact outcome is not a completed drill")

    event = _exact_keys(
        artifact.get("event"),
        {
            "event_id_sha256",
            "severity",
            "emitted_at_utc",
            "observed_at_utc",
            "run_id",
            "issue_number",
            "normalized_results",
        },
        "event",
    )
    event_id = _sha256(event.get("event_id_sha256"), "event id")
    if event.get("severity") != "P1":
        raise EvidenceError("event severity is not P1")
    emitted = _timestamp(event.get("emitted_at_utc"), "event emission")
    observed = _timestamp(event.get("observed_at_utc"), "event observation")
    if emitted > observed:
        raise EvidenceError("event observation precedes emission")
    if not isinstance(event.get("run_id"), int) or event["run_id"] <= 0:
        raise EvidenceError("event run id is invalid")
    if not isinstance(event.get("issue_number"), int) or event["issue_number"] <= 0:
        raise EvidenceError("event issue number is invalid")
    results = _exact_keys(
        event.get("normalized_results"),
        {"api", "worker", "blueprint", "aggregate"},
        "normalized results",
    )
    if any(value not in {"success", "failure", "cancelled", "skipped"} for value in results.values()):
        raise EvidenceError("normalized monitor result is invalid")

    incident = _exact_keys(
        artifact.get("incident_channel"),
        {"destination_role", "provider", "status", "issue_url_sha256"},
        "incident channel",
    )
    if (
        incident.get("destination_role") != "incident_channel"
        or incident.get("provider") != "github"
        or incident.get("status") != "present"
    ):
        raise EvidenceError("GitHub incident-channel delivery is invalid")
    incident_receipt = _sha256(
        incident.get("issue_url_sha256"), "incident-channel receipt"
    )

    primary = _exact_keys(
        artifact.get("primary_on_call"),
        {
            "destination_role",
            "status",
            "delivered_at_utc",
            "receipt_id_sha256",
            "response_sha256",
        },
        "primary delivery",
    )
    if (
        primary.get("destination_role") != "primary_on_call"
        or primary.get("status") != "delivered"
    ):
        raise EvidenceError("primary delivery is invalid")
    primary_delivered = _timestamp(primary.get("delivered_at_utc"), "primary delivery")
    primary_receipt = _sha256(primary.get("receipt_id_sha256"), "primary receipt")
    _sha256(primary.get("response_sha256"), "primary response")

    acknowledgement = _exact_keys(
        artifact.get("acknowledgement"),
        {
            "status",
            "checked_at_utc",
            "receipt_id_sha256",
            "response_sha256",
            "acknowledged_at_utc",
            "actor_role",
            "latency_seconds",
        },
        "acknowledgement",
    )
    if (
        acknowledgement.get("status") != "acknowledged"
        or acknowledgement.get("actor_role") != "incident_commander"
    ):
        raise EvidenceError("incident-commander acknowledgement is invalid")
    checked = _timestamp(acknowledgement.get("checked_at_utc"), "ack check")
    acknowledged = _timestamp(
        acknowledgement.get("acknowledged_at_utc"), "acknowledgement"
    )
    latency = acknowledgement.get("latency_seconds")
    if (
        not isinstance(latency, int)
        or isinstance(latency, bool)
        or latency < 0
        or latency > 600
        or latency != int((acknowledged - emitted).total_seconds())
    ):
        raise EvidenceError("acknowledgement latency is invalid")
    if acknowledged > checked:
        raise EvidenceError("acknowledgement follows its readback")
    _sha256(acknowledgement.get("receipt_id_sha256"), "acknowledgement receipt")
    _sha256(acknowledgement.get("response_sha256"), "acknowledgement response")

    secondary = _exact_keys(
        artifact.get("secondary_escalation"),
        {
            "destination_role",
            "status",
            "delivered_at_utc",
            "receipt_id_sha256",
            "response_sha256",
            "trigger_reason",
        },
        "secondary escalation",
    )
    if (
        secondary.get("destination_role") != "secondary_on_call"
        or secondary.get("status") != "delivered"
        or secondary.get("trigger_reason") != "explicit_secondary_escalation_drill"
    ):
        raise EvidenceError("secondary drill delivery is invalid")
    secondary_delivered = _timestamp(
        secondary.get("delivered_at_utc"), "secondary delivery"
    )
    secondary_receipt = _sha256(
        secondary.get("receipt_id_sha256"), "secondary receipt"
    )
    _sha256(secondary.get("response_sha256"), "secondary response")

    if any(value < emitted for value in (primary_delivered, acknowledged, secondary_delivered)):
        raise EvidenceError("a delivery or acknowledgement precedes emission")
    if any(value > observed + timedelta(seconds=300) for value in (primary_delivered, checked, secondary_delivered)):
        raise EvidenceError("a provider receipt is implausibly after observation")
    if secondary_delivered < acknowledged:
        raise EvidenceError("secondary drill delivery precedes the verified acknowledgement")

    if not SHA1_RE.fullmatch(master_head_sha):
        raise EvidenceError("master HEAD is not a lowercase Git SHA-1")
    if not DEPLOY_ID_RE.fullmatch(deploy_id):
        raise EvidenceError("deploy id is invalid")
    _sha256(artifact_sha256, "provider artifact digest")

    emitted_text = _timestamp_text(event["emitted_at_utc"], "event emission")
    observed_text = _timestamp_text(event["observed_at_utc"], "event observation")
    return {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "gate": "alert_delivery",
        "environment": "public-production",
        "repository": REPOSITORY,
        "master_head_sha": master_head_sha,
        "deploy_id": deploy_id,
        "event_at_utc": emitted_text,
        "observed_at_utc": observed_text,
        "artifact_uri": AUTHORITY_URI,
        "artifact_sha256": artifact_sha256,
        "api_base_url": PRODUCTION_API_ORIGIN,
        "service_id": PRODUCTION_SERVICE_ID,
        "alert": {
            "alert_id_sha256": event_id,
            "severity": "P1",
            "emitted_at_utc": emitted_text,
            "source": "cas-production-runtime-monitor",
        },
        "deliveries": [
            {
                "destination_role": "incident_channel",
                "status": "delivered",
                "delivered_at_utc": emitted_text,
                "receipt_sha256": incident_receipt,
            },
            {
                "destination_role": "primary_on_call",
                "status": "delivered",
                "delivered_at_utc": _timestamp_text(
                    primary["delivered_at_utc"], "primary delivery"
                ),
                "receipt_sha256": primary_receipt,
            },
        ],
        "acknowledgement": {
            "status": "acknowledged",
            "acknowledged_at_utc": _timestamp_text(
                acknowledgement["acknowledged_at_utc"], "acknowledgement"
            ),
            "actor_role": "incident_commander",
            "latency_seconds": latency,
        },
        "escalation": {
            "triggered": True,
            "delivered": True,
            "destination_role": "secondary_on_call",
            "receipt_sha256": secondary_receipt,
            "delivered_at_utc": _timestamp_text(
                secondary["delivered_at_utc"], "secondary delivery"
            ),
        },
    }


def _write(path: Path, payload: Mapping[str, Any]) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    body = (
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("ascii")
    fd, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    try:
        try:
            os.fchmod(fd, 0o600)
        except (AttributeError, OSError):
            pass
        with os.fdopen(fd, "wb") as handle:
            handle.write(body)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build strict alert-delivery acceptance evidence from a safe drill artifact."
    )
    parser.add_argument("--provider-artifact", required=True, type=Path)
    parser.add_argument("--master-head-sha", required=True)
    parser.add_argument("--deploy-id", required=True)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        raw = args.provider_artifact.read_bytes()
        document = _json_object_without_duplicates(raw)
        payload = build_payload(
            document,
            artifact_sha256=hashlib.sha256(raw).hexdigest(),
            master_head_sha=args.master_head_sha,
            deploy_id=args.deploy_id,
        )
        _write(args.output, payload)
    except (EvidenceError, OSError) as exc:
        print(f"alert-delivery evidence unavailable: {exc}")
        return 1
    print(f"alert-delivery evidence written: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
