#!/usr/bin/env python3
"""Run one non-disruptive P1 alert-delivery drill.

This lane is deliberately separate from the production runtime monitor.  It
does not create, label, comment on, reopen, or close a runtime incident.  A
successful run proves four provider facts for one drill identity: delivery to
``incident_channel`` and ``primary_on_call``, a non-synthetic human
``incident_commander`` acknowledgement within 600 seconds, and a forced
``secondary_on_call`` escalation.  The emitted artifact remains secret-safe,
unpublished, and ``OPEN``.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Any, Callable, Mapping, Sequence

try:
    from scripts import deliver_production_runtime_alert as hardened
except ImportError:  # Direct ``python scripts/...`` execution.
    import deliver_production_runtime_alert as hardened


MODE_DISABLED = hardened.MODE_DISABLED
MODE_WEBHOOK_V1 = hardened.MODE_WEBHOOK_V1
DRILL_KIND = "non_disruptive_p1_alert_delivery_drill"
EVENT_SCHEMA = "cas_alert_delivery_drill_event.v1"
REQUEST_SCHEMA = "cas_alert_delivery_drill_adapter_request.v1"
RECEIPT_SCHEMA = "cas_alert_delivery_drill_provider_receipt.v1"
SAFE_ARTIFACT_SCHEMA = "cas_alert_delivery_drill_safe_receipts.v1"
ACK_WINDOW_SECONDS = 600
DEFAULT_POLL_SECONDS = 15.0
MAX_CLOCK_SKEW_SECONDS = hardened.MAX_CLOCK_SKEW_SECONDS
REPOSITORY_RE = hardened.REPOSITORY_RE
ACTOR_ID_RE = re.compile(r"^[^\x00-\x1f\x7f]{1,512}$")


@dataclass(frozen=True)
class DrillProviderConfig:
    mode: str
    incident: hardened.Endpoint | None = None
    primary: hardened.Endpoint | None = None
    acknowledgement: hardened.Endpoint | None = None
    secondary: hardened.Endpoint | None = None


@dataclass(frozen=True)
class DrillEvent:
    repository: str
    run_id: int
    run_attempt: int
    emitted_at: datetime

    @property
    def event_id_sha256(self) -> str:
        material = (
            f"{self.repository}:{DRILL_KIND}:{self.run_id}:{self.run_attempt}"
        ).encode("utf-8")
        return hashlib.sha256(material).hexdigest()

    def provider_payload(self) -> dict[str, Any]:
        return {
            "schema_version": EVENT_SCHEMA,
            "event_kind": DRILL_KIND,
            "event_id_sha256": self.event_id_sha256,
            "severity": "P1",
            "classification": "exercise",
            "runtime_outage": False,
            "source": "github_actions_alert_delivery_drill",
            "emitted_at_utc": hardened._format_utc(self.emitted_at),
            "repository": self.repository,
            "run_id": self.run_id,
            "run_attempt": self.run_attempt,
            "notice": "DRILL ONLY - no CAS runtime outage is being asserted",
        }


Transport = hardened.Transport
Clock = Callable[[], datetime]
Sleeper = Callable[[float], None]


def _now(clock: Clock) -> datetime:
    value = clock()
    if value.tzinfo is None or value.utcoffset() is None:
        raise hardened.ConfigurationError("clock_not_timezone_aware")
    return value.astimezone(timezone.utc)


def _canonical_sha256(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _endpoint(env: Mapping[str, str], prefix: str, label: str) -> hardened.Endpoint:
    url = env.get(f"CAS_ALERT_DRILL_{prefix}_WEBHOOK_URL", "")
    token = env.get(f"CAS_ALERT_DRILL_{prefix}_WEBHOOK_TOKEN", "")
    if not url or not token:
        raise hardened.ConfigurationError(f"drill_{label}_configuration_incomplete")
    return hardened.Endpoint(
        url=hardened._validated_https_url(url, name=f"drill_{label}"),
        token=hardened._validated_token(token, name=f"drill_{label}"),
    )


def load_provider_config(
    mode: str | None, environ: Mapping[str, str] | None = None
) -> DrillProviderConfig:
    env = os.environ if environ is None else environ
    normalized = mode or MODE_DISABLED
    if normalized in {"", MODE_DISABLED}:
        return DrillProviderConfig(mode=MODE_DISABLED)
    if normalized != MODE_WEBHOOK_V1:
        raise hardened.ConfigurationError("drill_provider_mode_invalid")
    # Resolve every endpoint before the first provider write.  In particular,
    # a missing secondary destination cannot leave a partial drill behind.
    return DrillProviderConfig(
        mode=MODE_WEBHOOK_V1,
        incident=_endpoint(env, "INCIDENT", "incident"),
        primary=_endpoint(env, "PRIMARY", "primary"),
        acknowledgement=_endpoint(env, "ACK", "acknowledgement"),
        secondary=_endpoint(env, "SECONDARY", "secondary"),
    )


def _request_payload(
    *,
    action: str,
    destination_role: str,
    event: DrillEvent,
    observed_at: datetime | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": REQUEST_SCHEMA,
        "action": action,
        "destination_role": destination_role,
        "event": event.provider_payload(),
    }
    # Provider writes use clock-independent canonical bytes so a retry with the
    # same drill identity cannot acquire a new idempotency key and page twice.
    # ACK readback is intentionally observation-bound so polling cannot reuse a
    # cached answer from an earlier check.
    if observed_at is not None:
        payload["observation"] = {
            "observed_at_utc": hardened._format_utc(observed_at),
            "ack_window_seconds": ACK_WINDOW_SECONDS,
        }
    if reason is not None:
        payload["reason"] = reason
    return payload


def _receipt_id(value: Any, *, code: str) -> str:
    if (
        not isinstance(value, str)
        or value != value.strip()
        or not hardened.RECEIPT_ID_RE.fullmatch(value)
    ):
        raise hardened.ProviderReceiptError(code)
    return value


def _delivery_receipt(
    response: hardened.TransportResponse,
    *,
    request_payload: Mapping[str, Any],
    event: DrillEvent,
    observed_at: datetime,
    action: str,
    destination_role: str,
) -> dict[str, Any]:
    if response.status != 200:
        raise hardened.ProviderTransportError("provider_http_status_invalid")
    document = hardened._json_object_without_duplicates(response.body)
    hardened._exact_keys(
        document,
        {
            "schema_version",
            "event_schema",
            "action",
            "event_id_sha256",
            "destination_role",
            "status",
            "delivered_at_utc",
            "receipt_id",
        },
        code="drill_delivery_receipt_fields_invalid",
    )
    if document.get("schema_version") != RECEIPT_SCHEMA:
        raise hardened.ProviderReceiptError("drill_delivery_receipt_schema_invalid")
    if document.get("event_schema") != EVENT_SCHEMA:
        raise hardened.ProviderReceiptError("drill_delivery_event_schema_mismatch")
    if document.get("action") != action:
        raise hardened.ProviderReceiptError("drill_delivery_action_mismatch")
    if document.get("event_id_sha256") != event.event_id_sha256:
        raise hardened.ProviderReceiptError("drill_delivery_event_mismatch")
    if document.get("destination_role") != destination_role:
        raise hardened.ProviderReceiptError("drill_delivery_destination_mismatch")
    if document.get("status") != "delivered":
        raise hardened.ProviderReceiptError("drill_delivery_status_not_delivered")
    delivered = hardened._parse_utc(
        document.get("delivered_at_utc"), code="drill_delivery_time_invalid"
    )
    if delivered < event.emitted_at:
        raise hardened.ProviderReceiptError("drill_delivery_precedes_emission")
    if delivered < observed_at - timedelta(seconds=MAX_CLOCK_SKEW_SECONDS):
        raise hardened.ProviderReceiptError("drill_delivery_time_stale")
    if delivered > observed_at + timedelta(seconds=MAX_CLOCK_SKEW_SECONDS):
        raise hardened.ProviderReceiptError("drill_delivery_time_in_future")
    receipt_id = _receipt_id(
        document.get("receipt_id"), code="drill_delivery_receipt_id_invalid"
    )
    return {
        "destination_role": destination_role,
        "status": "delivered",
        "requested_at_utc": hardened._format_utc(observed_at),
        "delivered_at_utc": hardened._format_utc(delivered),
        "request_sha256": _canonical_sha256(request_payload),
        "receipt_id_sha256": hashlib.sha256(receipt_id.encode("utf-8")).hexdigest(),
        "response_sha256": hashlib.sha256(response.body).hexdigest(),
    }


def _acknowledgement_receipt(
    response: hardened.TransportResponse,
    *,
    request_payload: Mapping[str, Any],
    event: DrillEvent,
    observed_at: datetime,
) -> dict[str, Any]:
    if response.status != 200:
        raise hardened.ProviderTransportError("provider_http_status_invalid")
    document = hardened._json_object_without_duplicates(response.body)
    hardened._exact_keys(
        document,
        {
            "schema_version",
            "event_schema",
            "action",
            "event_id_sha256",
            "status",
            "checked_at_utc",
            "acknowledged_at_utc",
            "actor_role",
            "actor_type",
            "actor_id",
            "synthetic",
            "receipt_id",
        },
        code="drill_acknowledgement_receipt_fields_invalid",
    )
    if document.get("schema_version") != RECEIPT_SCHEMA:
        raise hardened.ProviderReceiptError("drill_acknowledgement_schema_invalid")
    if document.get("event_schema") != EVENT_SCHEMA:
        raise hardened.ProviderReceiptError("drill_acknowledgement_event_schema_mismatch")
    if document.get("action") != "check_acknowledgement":
        raise hardened.ProviderReceiptError("drill_acknowledgement_action_mismatch")
    if document.get("event_id_sha256") != event.event_id_sha256:
        raise hardened.ProviderReceiptError("drill_acknowledgement_event_mismatch")
    status = document.get("status")
    if status not in {"acknowledged", "unacknowledged"}:
        raise hardened.ProviderReceiptError("drill_acknowledgement_status_invalid")
    checked = hardened._parse_utc(
        document.get("checked_at_utc"), code="drill_acknowledgement_checked_time_invalid"
    )
    if checked < event.emitted_at:
        raise hardened.ProviderReceiptError("drill_acknowledgement_check_precedes_emission")
    if checked < observed_at - timedelta(seconds=MAX_CLOCK_SKEW_SECONDS):
        raise hardened.ProviderReceiptError("drill_acknowledgement_check_stale")
    if checked > observed_at + timedelta(seconds=MAX_CLOCK_SKEW_SECONDS):
        raise hardened.ProviderReceiptError("drill_acknowledgement_check_time_in_future")
    receipt_id = _receipt_id(
        document.get("receipt_id"), code="drill_acknowledgement_receipt_id_invalid"
    )
    safe: dict[str, Any] = {
        "status": status,
        "requested_at_utc": hardened._format_utc(observed_at),
        "checked_at_utc": hardened._format_utc(checked),
        "request_sha256": _canonical_sha256(request_payload),
        "receipt_id_sha256": hashlib.sha256(receipt_id.encode("utf-8")).hexdigest(),
        "response_sha256": hashlib.sha256(response.body).hexdigest(),
    }
    if status == "unacknowledged":
        if any(
            document.get(field) is not None
            for field in ("acknowledged_at_utc", "actor_role", "actor_type", "actor_id")
        ) or document.get("synthetic") is not False:
            raise hardened.ProviderReceiptError(
                "drill_unacknowledged_receipt_claims_actor"
            )
        return safe

    if document.get("synthetic") is not False:
        raise hardened.ProviderReceiptError("drill_acknowledgement_synthetic")
    if document.get("actor_type") != "human":
        raise hardened.ProviderReceiptError("drill_acknowledgement_actor_not_human")
    if document.get("actor_role") != "incident_commander":
        raise hardened.ProviderReceiptError("drill_acknowledgement_actor_role_unverified")
    actor_id = document.get("actor_id")
    if (
        not isinstance(actor_id, str)
        or actor_id != actor_id.strip()
        or not ACTOR_ID_RE.fullmatch(actor_id)
    ):
        raise hardened.ProviderReceiptError("drill_acknowledgement_actor_id_invalid")
    acknowledged = hardened._parse_utc(
        document.get("acknowledged_at_utc"), code="drill_acknowledgement_time_invalid"
    )
    if acknowledged < event.emitted_at or acknowledged > checked:
        raise hardened.ProviderReceiptError("drill_acknowledgement_time_order_invalid")
    latency_delta = acknowledged - event.emitted_at
    if latency_delta > timedelta(seconds=ACK_WINDOW_SECONDS):
        raise hardened.ProviderReceiptError("drill_acknowledgement_late")
    safe.update(
        {
            "acknowledged_at_utc": hardened._format_utc(acknowledged),
            "actor_role": "incident_commander",
            "actor_type": "human",
            "actor_id_sha256": hashlib.sha256(actor_id.encode("utf-8")).hexdigest(),
            "synthetic": False,
            "latency_seconds": int(latency_delta.total_seconds()),
        }
    )
    return safe


def _safe_base_artifact(
    event: DrillEvent, *, mode: str, observed_at: datetime
) -> dict[str, Any]:
    return {
        "schema_version": SAFE_ARTIFACT_SCHEMA,
        "claim_status": "OPEN",
        "authority_published": False,
        "customer_production_status": "OPEN",
        "provider_mode": mode,
        "drill": {
            "event_schema": EVENT_SCHEMA,
            "event_kind": DRILL_KIND,
            "event_id_sha256": event.event_id_sha256,
            "severity": "P1",
            "classification": "exercise",
            "runtime_outage": False,
            "runtime_incident_mutated": False,
            "emitted_at_utc": hardened._format_utc(event.emitted_at),
            "observed_at_utc": hardened._format_utc(observed_at),
            "repository": event.repository,
            "run_id": event.run_id,
            "run_attempt": event.run_attempt,
        },
        "deliveries": {
            "incident_channel": {"status": "unavailable"},
            "primary_on_call": {"status": "unavailable"},
        },
        "acknowledgement": {"status": "unavailable"},
        "secondary_escalation": {"status": "unavailable"},
        "provider_receipts_sha256": "0" * 64,
        "outcome": "OPEN",
        "errors": [],
    }


def _finalize(
    artifact: dict[str, Any], *, observed_at: datetime, errors: Sequence[str]
) -> None:
    artifact["drill"]["observed_at_utc"] = hardened._format_utc(observed_at)
    artifact["errors"] = list(dict.fromkeys(errors))
    artifact["provider_receipts_sha256"] = _canonical_sha256(
        {
            "deliveries": artifact["deliveries"],
            "acknowledgement": artifact["acknowledgement"],
            "secondary_escalation": artifact["secondary_escalation"],
        }
    )


def run_drill(
    *,
    config: DrillProviderConfig,
    event: DrillEvent,
    transport: Transport = hardened._default_transport,
    clock: Clock = lambda: datetime.now(timezone.utc),
    sleeper: Sleeper = time.sleep,
    poll_seconds: float = DEFAULT_POLL_SECONDS,
) -> tuple[dict[str, Any], bool]:
    observed = _now(clock)
    artifact = _safe_base_artifact(event, mode=config.mode, observed_at=observed)
    errors: list[str] = []
    if config.mode == MODE_DISABLED:
        artifact["outcome"] = "provider_disabled"
        errors.append("drill_provider_disabled")
        _finalize(artifact, observed_at=observed, errors=errors)
        return artifact, False
    if (
        config.mode != MODE_WEBHOOK_V1
        or not config.incident
        or not config.primary
        or not config.acknowledgement
        or not config.secondary
    ):
        artifact["outcome"] = "configuration_error"
        errors.append("drill_provider_configuration_incomplete")
        _finalize(artifact, observed_at=observed, errors=errors)
        return artifact, False
    if poll_seconds <= 0 or poll_seconds > 60:
        artifact["outcome"] = "configuration_error"
        errors.append("drill_poll_interval_invalid")
        _finalize(artifact, observed_at=observed, errors=errors)
        return artifact, False

    for role, endpoint in (
        ("incident_channel", config.incident),
        ("primary_on_call", config.primary),
    ):
        observed = _now(clock)
        payload = _request_payload(
            action="deliver",
            destination_role=role,
            event=event,
            reason="non_disruptive_p1_drill",
        )
        try:
            response = transport(endpoint, payload, hardened._idempotency_key(payload))
            artifact["deliveries"][role] = _delivery_receipt(
                response,
                request_payload=payload,
                event=event,
                observed_at=observed,
                action="deliver",
                destination_role=role,
            )
        except hardened.AlertDeliveryError as exc:
            artifact["deliveries"][role] = {
                "status": "unavailable",
                "reason": exc.code,
            }
            errors.append(exc.code)

    acknowledgement_verified = False
    if not errors:
        deadline = event.emitted_at + timedelta(seconds=ACK_WINDOW_SECONDS)
        while True:
            observed = _now(clock)
            payload = _request_payload(
                action="check_acknowledgement",
                destination_role="primary_on_call",
                event=event,
                observed_at=observed,
            )
            try:
                response = transport(
                    config.acknowledgement,
                    payload,
                    hardened._idempotency_key(payload),
                )
                acknowledgement = _acknowledgement_receipt(
                    response,
                    request_payload=payload,
                    event=event,
                    observed_at=observed,
                )
                artifact["acknowledgement"] = acknowledgement
                if acknowledgement["status"] == "acknowledged":
                    acknowledgement_verified = True
                    break
            except hardened.ProviderReceiptError as exc:
                artifact["acknowledgement"] = {
                    "status": "unavailable",
                    "reason": exc.code,
                }
                errors.append(exc.code)
                break
            except hardened.AlertDeliveryError as exc:
                artifact["acknowledgement"] = {
                    "status": "unavailable",
                    "reason": exc.code,
                }
                if observed >= deadline:
                    errors.append(exc.code)
                    break
            if observed >= deadline:
                errors.append("drill_acknowledgement_deadline_expired")
                break
            remaining = max(0.0, (deadline - observed).total_seconds())
            sleeper(min(poll_seconds, remaining))

    observed = _now(clock)
    escalation_reason = (
        "explicit_non_disruptive_drill"
        if acknowledgement_verified
        else "drill_acknowledgement_unverified"
    )
    escalation_payload = _request_payload(
        action="escalate",
        destination_role="secondary_on_call",
        event=event,
        reason=escalation_reason,
    )
    try:
        response = transport(
            config.secondary,
            escalation_payload,
            hardened._idempotency_key(escalation_payload),
        )
        artifact["secondary_escalation"] = _delivery_receipt(
            response,
            request_payload=escalation_payload,
            event=event,
            observed_at=observed,
            action="escalate",
            destination_role="secondary_on_call",
        )
        artifact["secondary_escalation"]["trigger_reason"] = escalation_reason
    except hardened.AlertDeliveryError as exc:
        artifact["secondary_escalation"] = {
            "status": "unavailable",
            "reason": exc.code,
            "trigger_reason": escalation_reason,
        }
        errors.append(exc.code)

    complete = (
        not errors
        and acknowledgement_verified
        and all(
            artifact["deliveries"][role].get("status") == "delivered"
            for role in ("incident_channel", "primary_on_call")
        )
        and artifact["secondary_escalation"].get("status") == "delivered"
    )
    artifact["outcome"] = (
        "non_disruptive_drill_complete"
        if complete
        else "non_disruptive_drill_incomplete"
    )
    _finalize(artifact, observed_at=_now(clock), errors=errors)
    return artifact, complete


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", default=MODE_DISABLED)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--run-id", required=True, type=int)
    parser.add_argument("--run-attempt", required=True, type=int)
    parser.add_argument("--emitted-at-utc", required=True)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def _event_from_args(args: argparse.Namespace, *, now: datetime) -> DrillEvent:
    if not REPOSITORY_RE.fullmatch(args.repository):
        raise hardened.ConfigurationError("drill_repository_invalid")
    if args.run_id <= 0 or args.run_attempt <= 0:
        raise hardened.ConfigurationError("drill_run_identity_invalid")
    emitted = hardened._parse_cli_utc(args.emitted_at_utc, label="drill_emitted_at_utc")
    if args.emitted_at_utc != hardened._format_utc(emitted):
        raise hardened.ConfigurationError("drill_emitted_at_utc_not_canonical")
    if emitted > now + timedelta(seconds=MAX_CLOCK_SKEW_SECONDS):
        raise hardened.ConfigurationError("drill_emitted_at_utc_in_future")
    if now - emitted > timedelta(seconds=MAX_CLOCK_SKEW_SECONDS):
        raise hardened.ConfigurationError("drill_emitted_at_utc_stale")
    return DrillEvent(
        repository=args.repository,
        run_id=args.run_id,
        run_attempt=args.run_attempt,
        emitted_at=emitted,
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    now = datetime.now(timezone.utc)
    try:
        event = _event_from_args(args, now=now)
    except hardened.ConfigurationError as exc:
        print(f"alert-delivery drill configuration error: {exc.code}", file=sys.stderr)
        return 2
    try:
        config = load_provider_config(args.mode)
    except hardened.ConfigurationError as exc:
        artifact = _safe_base_artifact(event, mode="invalid", observed_at=now)
        artifact["outcome"] = "configuration_error"
        _finalize(artifact, observed_at=now, errors=[exc.code])
        hardened._write_safe_artifact(args.output, artifact)
        print(f"alert-delivery drill configuration error: {exc.code}", file=sys.stderr)
        return 2
    try:
        artifact, complete = run_drill(config=config, event=event)
    except Exception:
        artifact = _safe_base_artifact(event, mode=config.mode, observed_at=now)
        artifact["outcome"] = "internal_error"
        _finalize(
            artifact,
            observed_at=datetime.now(timezone.utc),
            errors=["drill_adapter_internal_error"],
        )
        hardened._write_safe_artifact(args.output, artifact)
        print("alert-delivery drill failed: drill_adapter_internal_error", file=sys.stderr)
        return 1
    hardened._write_safe_artifact(args.output, artifact)
    print(f"Alert-delivery drill outcome: {artifact['outcome']}")
    return 0 if complete else (2 if config.mode == MODE_DISABLED else 1)


if __name__ == "__main__":
    raise SystemExit(main())
