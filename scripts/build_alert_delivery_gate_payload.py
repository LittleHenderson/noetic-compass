#!/usr/bin/env python3
"""Convert one secret-safe non-disruptive drill artifact into gate evidence.

The source artifact and resulting payload remain non-authoritative and
``OPEN``.  This collector does not publish either one.  Only the independently
authorized owner-bound publication route may place the payload at the
production ``alert_delivery`` authority endpoint.
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
SAFE_ARTIFACT_SCHEMA = "cas_alert_delivery_drill_safe_receipts.v1"
DRILL_EVENT_SCHEMA = "cas_alert_delivery_drill_event.v1"
DRILL_REQUEST_SCHEMA = "cas_alert_delivery_drill_adapter_request.v1"
DRILL_KIND = "non_disruptive_p1_alert_delivery_drill"
DRILL_SOURCE = "github_actions_alert_delivery_drill"
DRILL_NOTICE = "DRILL ONLY - no CAS runtime outage is being asserted"
ACK_WINDOW_SECONDS = 600
MAX_CLOCK_SKEW_SECONDS = 300
REPOSITORY = "LittleHenderson/noetic-compass"
PRODUCTION_API_ORIGIN = "https://cas-harness-customer-api.onrender.com"
PRODUCTION_SERVICE_ID = "srv-d9bijbjtqb8s73cn4n20"
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


def _canonical_sha256(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _expected_event_payload(drill: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": DRILL_EVENT_SCHEMA,
        "event_kind": DRILL_KIND,
        "event_id_sha256": drill["event_id_sha256"],
        "severity": "P1",
        "classification": "exercise",
        "runtime_outage": False,
        "source": DRILL_SOURCE,
        "emitted_at_utc": drill["emitted_at_utc"],
        "repository": REPOSITORY,
        "run_id": drill["run_id"],
        "run_attempt": drill["run_attempt"],
        "notice": DRILL_NOTICE,
    }


def _expected_request_sha256(
    drill: Mapping[str, Any],
    *,
    action: str,
    destination_role: str,
    reason: str | None = None,
    observed_at_utc: str | None = None,
) -> str:
    payload: dict[str, Any] = {
        "schema_version": DRILL_REQUEST_SCHEMA,
        "action": action,
        "destination_role": destination_role,
        "event": _expected_event_payload(drill),
    }
    if observed_at_utc is not None:
        payload["observation"] = {
            "observed_at_utc": observed_at_utc,
            "ack_window_seconds": ACK_WINDOW_SECONDS,
        }
    if reason is not None:
        payload["reason"] = reason
    return _canonical_sha256(payload)


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
            "authority_published",
            "customer_production_status",
            "provider_mode",
            "drill",
            "deliveries",
            "acknowledgement",
            "secondary_escalation",
            "provider_receipts_sha256",
            "outcome",
            "errors",
        },
        "provider artifact",
    )
    if artifact.get("schema_version") != SAFE_ARTIFACT_SCHEMA:
        raise EvidenceError("provider artifact schema is not the non-disruptive drill schema")
    if (
        artifact.get("claim_status") != "OPEN"
        or artifact.get("authority_published") is not False
        or artifact.get("customer_production_status") != "OPEN"
    ):
        raise EvidenceError("source provider artifact must remain unpublished and OPEN")
    if artifact.get("provider_mode") != "webhook_v1":
        raise EvidenceError("provider artifact was not produced by webhook_v1")
    if artifact.get("errors") != []:
        raise EvidenceError("provider artifact contains errors")
    if artifact.get("outcome") != "non_disruptive_drill_complete":
        raise EvidenceError("provider artifact outcome is not a completed drill")

    drill = _exact_keys(
        artifact.get("drill"),
        {
            "event_schema",
            "event_kind",
            "event_id_sha256",
            "severity",
            "classification",
            "runtime_outage",
            "runtime_incident_mutated",
            "emitted_at_utc",
            "observed_at_utc",
            "repository",
            "run_id",
            "run_attempt",
        },
        "drill",
    )
    if (
        drill.get("event_schema") != DRILL_EVENT_SCHEMA
        or drill.get("event_kind") != DRILL_KIND
        or drill.get("classification") != "exercise"
        or drill.get("runtime_outage") is not False
        or drill.get("runtime_incident_mutated") is not False
    ):
        raise EvidenceError("drill identity is confused with a runtime incident")
    event_id = _sha256(drill.get("event_id_sha256"), "event id")
    if drill.get("severity") != "P1":
        raise EvidenceError("drill severity is not P1")
    if drill.get("repository") != REPOSITORY:
        raise EvidenceError("drill repository is invalid")
    emitted = _timestamp(drill.get("emitted_at_utc"), "drill emission")
    observed = _timestamp(drill.get("observed_at_utc"), "drill observation")
    if emitted > observed:
        raise EvidenceError("drill observation precedes emission")
    for field in ("run_id", "run_attempt"):
        value = drill.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise EvidenceError(f"drill {field} is invalid")
    expected_event_id = hashlib.sha256(
        (
            f"{REPOSITORY}:{DRILL_KIND}:{drill['run_id']}:{drill['run_attempt']}"
        ).encode("utf-8")
    ).hexdigest()
    if event_id != expected_event_id:
        raise EvidenceError("drill event id is not bound to the run identity")

    deliveries = _exact_keys(
        artifact.get("deliveries"),
        {"incident_channel", "primary_on_call"},
        "deliveries",
    )

    def delivery(role: str) -> tuple[Mapping[str, Any], datetime]:
        receipt = _exact_keys(
            deliveries.get(role),
            {
                "destination_role",
                "status",
                "requested_at_utc",
                "delivered_at_utc",
                "request_sha256",
                "receipt_id_sha256",
                "response_sha256",
            },
            f"{role} delivery",
        )
        if receipt.get("destination_role") != role or receipt.get("status") != "delivered":
            raise EvidenceError(f"{role} delivery is invalid")
        requested_at = _timestamp(
            receipt.get("requested_at_utc"), f"{role} request"
        )
        delivered_at = _timestamp(
            receipt.get("delivered_at_utc"), f"{role} delivery"
        )
        if not emitted <= requested_at <= observed:
            raise EvidenceError(f"{role} request is outside the drill observation")
        if not (
            requested_at - timedelta(seconds=MAX_CLOCK_SKEW_SECONDS)
            <= delivered_at
            <= requested_at + timedelta(seconds=MAX_CLOCK_SKEW_SECONDS)
        ):
            raise EvidenceError(f"{role} delivery clock is implausible")
        for field in ("request_sha256", "receipt_id_sha256", "response_sha256"):
            _sha256(receipt.get(field), f"{role} {field}")
        expected_request = _expected_request_sha256(
            drill,
            action="deliver",
            destination_role=role,
            reason="non_disruptive_p1_drill",
        )
        if receipt.get("request_sha256") != expected_request:
            raise EvidenceError(f"{role} request digest is not event-bound")
        return receipt, delivered_at

    incident, incident_delivered = delivery("incident_channel")
    primary, primary_delivered = delivery("primary_on_call")

    acknowledgement = _exact_keys(
        artifact.get("acknowledgement"),
        {
            "status",
            "requested_at_utc",
            "checked_at_utc",
            "request_sha256",
            "receipt_id_sha256",
            "response_sha256",
            "acknowledged_at_utc",
            "actor_role",
            "actor_type",
            "actor_id_sha256",
            "synthetic",
            "latency_seconds",
        },
        "acknowledgement",
    )
    if (
        acknowledgement.get("status") != "acknowledged"
        or acknowledgement.get("actor_role") != "incident_commander"
        or acknowledgement.get("actor_type") != "human"
        or acknowledgement.get("synthetic") is not False
    ):
        raise EvidenceError("incident-commander acknowledgement is invalid")
    acknowledgement_requested = _timestamp(
        acknowledgement.get("requested_at_utc"), "ack request"
    )
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
    if not emitted <= acknowledgement_requested <= observed:
        raise EvidenceError("ack request is outside the drill observation")
    if not (
        acknowledgement_requested - timedelta(seconds=MAX_CLOCK_SKEW_SECONDS)
        <= checked
        <= acknowledgement_requested + timedelta(seconds=MAX_CLOCK_SKEW_SECONDS)
    ):
        raise EvidenceError("acknowledgement readback clock is implausible")
    _sha256(acknowledgement.get("actor_id_sha256"), "acknowledgement actor")
    _sha256(acknowledgement.get("request_sha256"), "acknowledgement request")
    _sha256(acknowledgement.get("receipt_id_sha256"), "acknowledgement receipt")
    _sha256(acknowledgement.get("response_sha256"), "acknowledgement response")
    expected_ack_request = _expected_request_sha256(
        drill,
        action="check_acknowledgement",
        destination_role="primary_on_call",
        observed_at_utc=acknowledgement["requested_at_utc"],
    )
    if acknowledgement.get("request_sha256") != expected_ack_request:
        raise EvidenceError("acknowledgement request digest is not event-bound")

    secondary = _exact_keys(
        artifact.get("secondary_escalation"),
        {
            "destination_role",
            "status",
            "requested_at_utc",
            "delivered_at_utc",
            "request_sha256",
            "receipt_id_sha256",
            "response_sha256",
            "trigger_reason",
        },
        "secondary escalation",
    )
    if (
        secondary.get("destination_role") != "secondary_on_call"
        or secondary.get("status") != "delivered"
        or secondary.get("trigger_reason") != "explicit_non_disruptive_drill"
    ):
        raise EvidenceError("secondary drill delivery is invalid")
    secondary_requested = _timestamp(
        secondary.get("requested_at_utc"), "secondary request"
    )
    secondary_delivered = _timestamp(
        secondary.get("delivered_at_utc"), "secondary delivery"
    )
    _sha256(secondary.get("request_sha256"), "secondary request")
    _sha256(secondary.get("receipt_id_sha256"), "secondary receipt id")
    _sha256(secondary.get("response_sha256"), "secondary response")
    if not acknowledgement_requested <= secondary_requested <= observed:
        raise EvidenceError("secondary request is outside the verified drill sequence")
    if not (
        secondary_requested - timedelta(seconds=MAX_CLOCK_SKEW_SECONDS)
        <= secondary_delivered
        <= secondary_requested + timedelta(seconds=MAX_CLOCK_SKEW_SECONDS)
    ):
        raise EvidenceError("secondary delivery clock is implausible")
    expected_secondary_request = _expected_request_sha256(
        drill,
        action="escalate",
        destination_role="secondary_on_call",
        reason="explicit_non_disruptive_drill",
    )
    if secondary.get("request_sha256") != expected_secondary_request:
        raise EvidenceError("secondary request digest is not event-bound")

    if any(
        value < emitted
        for value in (
            incident_delivered,
            primary_delivered,
            acknowledged,
            secondary_delivered,
        )
    ):
        raise EvidenceError("a delivery or acknowledgement precedes emission")
    if any(
        value > observed
        for value in (
            incident_delivered,
            primary_delivered,
            checked,
            secondary_delivered,
        )
    ):
        raise EvidenceError("a provider receipt follows the final observation")
    if secondary_delivered < acknowledged:
        raise EvidenceError("secondary drill delivery precedes the verified acknowledgement")

    expected_receipts_sha256 = _canonical_sha256(
        {
            "deliveries": deliveries,
            "acknowledgement": acknowledgement,
            "secondary_escalation": secondary,
        }
    )
    if artifact.get("provider_receipts_sha256") != expected_receipts_sha256:
        raise EvidenceError("provider receipt set was tampered")

    if not SHA1_RE.fullmatch(master_head_sha):
        raise EvidenceError("master HEAD is not a lowercase Git SHA-1")
    if not DEPLOY_ID_RE.fullmatch(deploy_id):
        raise EvidenceError("deploy id is invalid")
    _sha256(artifact_sha256, "provider artifact digest")

    emitted_text = _timestamp_text(drill["emitted_at_utc"], "drill emission")
    observed_text = _timestamp_text(drill["observed_at_utc"], "drill observation")
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
            "source": "cas-alert-delivery-drill",
        },
        "deliveries": [
            {
                "destination_role": "incident_channel",
                "status": "delivered",
                "delivered_at_utc": _timestamp_text(
                    incident["delivered_at_utc"], "incident-channel delivery"
                ),
                "receipt_sha256": incident["response_sha256"],
            },
            {
                "destination_role": "primary_on_call",
                "status": "delivered",
                "delivered_at_utc": _timestamp_text(
                    primary["delivered_at_utc"], "primary delivery"
                ),
                "receipt_sha256": primary["response_sha256"],
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
            "receipt_sha256": secondary["response_sha256"],
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
