#!/usr/bin/env python3
"""Deliver a production runtime alert through an optional webhook adapter.

GitHub Issues remains the always-on incident channel.  This script adds a
second, independently configured primary-on-call destination and, after the
ten-minute acknowledgement window, a secondary-on-call escalation.  The
adapter is deliberately dark unless ``CAS_ALERT_PROVIDER_MODE=webhook_v1``.

Provider responses are treated as untrusted input.  A delivery is recorded
only when an exact, event-bound receipt validates.  Raw response bodies,
provider URLs, bearer tokens, and receipt identifiers are never printed or
written to the safe receipt artifact.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import sys
import tempfile
from typing import Any, Callable, Mapping, Sequence
from urllib import error, parse, request


MODE_DISABLED = "disabled"
MODE_WEBHOOK_V1 = "webhook_v1"
LIFECYCLE_FAILING = "failing"
LIFECYCLE_RECOVERY_PENDING = "recovery_pending"
EVENT_SCHEMA = "cas_runtime_alert_event.v1"
OBSERVATION_SCHEMA = "cas_runtime_alert_observation.v1"
REQUEST_SCHEMA = "cas_runtime_alert_adapter_request.v1"
RECEIPT_SCHEMA = "cas_runtime_alert_provider_receipt.v1"
SAFE_ARTIFACT_SCHEMA = "cas_runtime_alert_safe_receipts.v2"
ACK_WINDOW_SECONDS = 600
MAX_CLOCK_SKEW_SECONDS = 300
MAX_RESPONSE_BYTES = 65_536
DEFAULT_TIMEOUT_SECONDS = 15.0
RESULT_VALUES = frozenset({"success", "failure", "cancelled", "skipped"})
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}$")
RECEIPT_ID_RE = re.compile(r"^[^\x00-\x1f\x7f]{1,512}$")
BLOCKED_HOST_SUFFIXES = (".local", ".localhost", ".internal", ".home.arpa")


class AlertDeliveryError(RuntimeError):
    """Base error carrying only a normalized, secret-safe reason code."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class ConfigurationError(AlertDeliveryError):
    """Provider configuration is incomplete or unsafe."""


class ProviderTransportError(AlertDeliveryError):
    """The provider request did not return one bounded HTTP 200 response."""


class ProviderReceiptError(AlertDeliveryError):
    """The provider response could not prove the requested operation."""


@dataclass(frozen=True)
class Endpoint:
    url: str
    token: str


@dataclass(frozen=True)
class ProviderConfig:
    mode: str
    primary: Endpoint | None = None
    acknowledgement: Endpoint | None = None
    secondary: Endpoint | None = None


@dataclass(frozen=True)
class TransportResponse:
    status: int
    body: bytes


Transport = Callable[[Endpoint, Mapping[str, Any], str], TransportResponse]


@dataclass(frozen=True)
class AlertEvent:
    repository: str
    run_id: int
    issue_number: int
    emitted_at: datetime
    observed_at: datetime
    results: Mapping[str, str]

    @property
    def event_id_sha256(self) -> str:
        material = (
            f"{self.repository}:production-runtime-alert-issue:{self.issue_number}"
        ).encode("utf-8")
        return hashlib.sha256(material).hexdigest()

    @property
    def run_url(self) -> str:
        return f"https://github.com/{self.repository}/actions/runs/{self.run_id}"

    @property
    def issue_url(self) -> str:
        return f"https://github.com/{self.repository}/issues/{self.issue_number}"

    def provider_payload(self) -> dict[str, Any]:
        """Return the incident-stable provider event used for paging writes."""

        return {
            "schema_version": EVENT_SCHEMA,
            "event_id_sha256": self.event_id_sha256,
            "severity": "P1",
            "source": "github_actions_production_runtime_monitor",
            "emitted_at_utc": _format_utc(self.emitted_at),
            "incident_channel": {
                "destination_role": "incident_channel",
                "provider": "github",
                "repository": self.repository,
                "issue_number": self.issue_number,
                "issue_url": self.issue_url,
            },
        }

    def observation_payload(self) -> dict[str, Any]:
        """Return the current run observation used only for ACK readback."""

        return {
            "schema_version": OBSERVATION_SCHEMA,
            "observed_at_utc": _format_utc(self.observed_at),
            "run": {
                "repository": self.repository,
                "run_id": self.run_id,
                "run_url": self.run_url,
                "results": dict(self.results),
            },
        }


class _NoRedirectHandler(request.HTTPRedirectHandler):
    def redirect_request(  # type: ignore[override]
        self,
        req: request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> request.Request | None:
        raise ProviderTransportError("provider_redirect_refused")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _parse_utc(value: Any, *, code: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ProviderReceiptError(code)
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ProviderReceiptError(code) from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ProviderReceiptError(code)
    return parsed.astimezone(timezone.utc)


def _parse_cli_utc(value: str, *, label: str) -> datetime:
    try:
        return _parse_utc(value, code=f"invalid_{label}")
    except ProviderReceiptError as exc:
        raise ConfigurationError(exc.code) from exc


def _exact_keys(value: Mapping[str, Any], expected: set[str], *, code: str) -> None:
    if set(value) != expected:
        raise ProviderReceiptError(code)


def _json_object_without_duplicates(body: bytes) -> Mapping[str, Any]:
    if not body or len(body) > MAX_RESPONSE_BYTES:
        raise ProviderReceiptError("provider_response_size_invalid")
    try:
        text = body.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ProviderReceiptError("provider_response_not_utf8") from exc

    def object_pairs(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ProviderReceiptError("provider_response_duplicate_key")
            result[key] = value
        return result

    try:
        decoded = json.loads(text, object_pairs_hook=object_pairs)
    except ProviderReceiptError:
        raise
    except (json.JSONDecodeError, TypeError) as exc:
        raise ProviderReceiptError("provider_response_not_json") from exc
    if not isinstance(decoded, Mapping):
        raise ProviderReceiptError("provider_response_not_object")
    return decoded


def _validated_https_url(value: str, *, name: str) -> str:
    if not value or len(value) > 2048 or any(ord(char) < 32 for char in value):
        raise ConfigurationError(f"{name}_url_invalid")
    try:
        value.encode("ascii", errors="strict")
    except UnicodeEncodeError as exc:
        raise ConfigurationError(f"{name}_url_invalid") from exc
    try:
        parsed = parse.urlsplit(value)
        port = parsed.port
    except ValueError as exc:
        raise ConfigurationError(f"{name}_url_invalid") from exc
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or port not in {None, 443}
    ):
        raise ConfigurationError(f"{name}_url_invalid")
    host = parsed.hostname.rstrip(".").lower()
    if host == "localhost" or host.endswith(BLOCKED_HOST_SUFFIXES):
        raise ConfigurationError(f"{name}_url_host_not_public")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        if "." not in host:
            raise ConfigurationError(f"{name}_url_host_not_public")
    else:
        if not address.is_global:
            raise ConfigurationError(f"{name}_url_host_not_public")
    return value


def _validated_token(value: str, *, name: str) -> str:
    try:
        value.encode("ascii", errors="strict")
    except UnicodeEncodeError as exc:
        raise ConfigurationError(f"{name}_token_invalid") from exc
    if (
        not (16 <= len(value) <= 4096)
        or value != value.strip()
        or any(ord(char) < 32 or ord(char) == 127 for char in value)
    ):
        raise ConfigurationError(f"{name}_token_invalid")
    return value


def load_provider_config(
    mode: str | None, environ: Mapping[str, str] | None = None
) -> ProviderConfig:
    env = os.environ if environ is None else environ
    normalized = mode or MODE_DISABLED
    if normalized in {"", MODE_DISABLED}:
        return ProviderConfig(mode=MODE_DISABLED)
    if normalized != MODE_WEBHOOK_V1:
        raise ConfigurationError("provider_mode_invalid")

    def endpoint(prefix: str, label: str) -> Endpoint:
        url = env.get(f"CAS_ALERT_{prefix}_WEBHOOK_URL", "")
        token = env.get(f"CAS_ALERT_{prefix}_WEBHOOK_TOKEN", "")
        if not url or not token:
            raise ConfigurationError(f"{label}_configuration_incomplete")
        return Endpoint(
            url=_validated_https_url(url, name=label),
            token=_validated_token(token, name=label),
        )

    return ProviderConfig(
        mode=MODE_WEBHOOK_V1,
        primary=endpoint("PRIMARY", "primary"),
        acknowledgement=endpoint("ACK", "acknowledgement"),
        secondary=endpoint("SECONDARY", "secondary"),
    )


def _default_transport(
    endpoint: Endpoint, payload: Mapping[str, Any], idempotency_key: str
) -> TransportResponse:
    try:
        encoded = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")
        req = request.Request(
            endpoint.url,
            method="POST",
            data=encoded,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {endpoint.token}",
                "Content-Type": "application/json",
                "Idempotency-Key": idempotency_key,
                "User-Agent": "cas-production-runtime-alert-adapter/1",
            },
        )
        opener = request.build_opener(_NoRedirectHandler())
        with opener.open(req, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
            body = response.read(MAX_RESPONSE_BYTES + 1)
            status = int(response.status)
    except ProviderTransportError:
        raise
    except error.HTTPError as exc:
        if 300 <= int(exc.code) < 400:
            raise ProviderTransportError("provider_redirect_refused") from exc
        raise ProviderTransportError("provider_http_error") from exc
    except (error.URLError, TimeoutError, socket.timeout, OSError) as exc:
        raise ProviderTransportError("provider_unreachable") from exc
    except Exception as exc:
        # Unexpected transport/library exceptions are normalized so a traceback
        # cannot expose a secret URL, header, or provider response.
        raise ProviderTransportError("provider_transport_internal_error") from exc
    if status != 200:
        raise ProviderTransportError("provider_http_status_invalid")
    if len(body) > MAX_RESPONSE_BYTES:
        raise ProviderTransportError("provider_response_too_large")
    return TransportResponse(status=status, body=body)


def _request_payload(
    *,
    action: str,
    destination_role: str,
    event: AlertEvent,
    reason: str | None = None,
    include_observation: bool = False,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": REQUEST_SCHEMA,
        "action": action,
        "destination_role": destination_role,
        "event": event.provider_payload(),
    }
    if reason is not None:
        payload["reason"] = reason
    if include_observation:
        payload["observation"] = event.observation_payload()
    return payload


def _idempotency_key(payload: Mapping[str, Any]) -> str:
    """Bind idempotency to the exact canonical request bytes.

    Delivery and escalation requests contain only the incident-stable event,
    so retries reuse the same bytes and key. ACK readback adds the current run
    observation, so a later query gets a new key instead of a cached answer.
    """

    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _delivery_receipt(
    response: TransportResponse,
    *,
    event: AlertEvent,
    action: str,
    destination_role: str,
) -> dict[str, Any]:
    if response.status != 200:
        raise ProviderTransportError("provider_http_status_invalid")
    document = _json_object_without_duplicates(response.body)
    _exact_keys(
        document,
        {
            "schema_version",
            "action",
            "event_id_sha256",
            "destination_role",
            "status",
            "delivered_at_utc",
            "receipt_id",
        },
        code="delivery_receipt_fields_invalid",
    )
    if document.get("schema_version") != RECEIPT_SCHEMA:
        raise ProviderReceiptError("delivery_receipt_schema_invalid")
    if document.get("action") != action:
        raise ProviderReceiptError("delivery_receipt_action_mismatch")
    if document.get("event_id_sha256") != event.event_id_sha256:
        raise ProviderReceiptError("delivery_receipt_event_mismatch")
    if document.get("destination_role") != destination_role:
        raise ProviderReceiptError("delivery_receipt_destination_mismatch")
    if document.get("status") != "delivered":
        raise ProviderReceiptError("delivery_receipt_status_not_delivered")
    delivered = _parse_utc(
        document.get("delivered_at_utc"), code="delivery_receipt_time_invalid"
    )
    if delivered < event.emitted_at:
        raise ProviderReceiptError("delivery_receipt_precedes_emission")
    if delivered > event.observed_at + timedelta(seconds=MAX_CLOCK_SKEW_SECONDS):
        raise ProviderReceiptError("delivery_receipt_time_in_future")
    receipt_id = document.get("receipt_id")
    if not isinstance(receipt_id, str) or not RECEIPT_ID_RE.fullmatch(receipt_id):
        raise ProviderReceiptError("delivery_receipt_id_invalid")
    return {
        "destination_role": destination_role,
        "status": "delivered",
        "delivered_at_utc": _format_utc(delivered),
        "receipt_id_sha256": _sha256_bytes(receipt_id.encode("utf-8")),
        "response_sha256": _sha256_bytes(response.body),
    }


def _acknowledgement_receipt(
    response: TransportResponse, *, event: AlertEvent
) -> dict[str, Any]:
    if response.status != 200:
        raise ProviderTransportError("provider_http_status_invalid")
    document = _json_object_without_duplicates(response.body)
    _exact_keys(
        document,
        {
            "schema_version",
            "action",
            "event_id_sha256",
            "status",
            "checked_at_utc",
            "acknowledged_at_utc",
            "actor_role",
            "receipt_id",
        },
        code="acknowledgement_receipt_fields_invalid",
    )
    if document.get("schema_version") != RECEIPT_SCHEMA:
        raise ProviderReceiptError("acknowledgement_receipt_schema_invalid")
    if document.get("action") != "check_acknowledgement":
        raise ProviderReceiptError("acknowledgement_receipt_action_mismatch")
    if document.get("event_id_sha256") != event.event_id_sha256:
        raise ProviderReceiptError("acknowledgement_receipt_event_mismatch")
    status = document.get("status")
    if status not in {"acknowledged", "unacknowledged"}:
        raise ProviderReceiptError("acknowledgement_receipt_status_invalid")
    checked = _parse_utc(
        document.get("checked_at_utc"), code="acknowledgement_checked_time_invalid"
    )
    if checked < event.emitted_at:
        raise ProviderReceiptError("acknowledgement_check_precedes_emission")
    if checked < event.emitted_at + timedelta(seconds=ACK_WINDOW_SECONDS):
        raise ProviderReceiptError("acknowledgement_check_before_window_closed")
    if checked < event.observed_at - timedelta(seconds=MAX_CLOCK_SKEW_SECONDS):
        raise ProviderReceiptError("acknowledgement_check_stale_for_observation")
    if checked > event.observed_at + timedelta(seconds=MAX_CLOCK_SKEW_SECONDS):
        raise ProviderReceiptError("acknowledgement_check_time_in_future")
    receipt_id = document.get("receipt_id")
    if not isinstance(receipt_id, str) or not RECEIPT_ID_RE.fullmatch(receipt_id):
        raise ProviderReceiptError("acknowledgement_receipt_id_invalid")

    safe: dict[str, Any] = {
        "status": status,
        "checked_at_utc": _format_utc(checked),
        "receipt_id_sha256": _sha256_bytes(receipt_id.encode("utf-8")),
        "response_sha256": _sha256_bytes(response.body),
    }
    if status == "unacknowledged":
        if document.get("acknowledged_at_utc") is not None or document.get(
            "actor_role"
        ) is not None:
            raise ProviderReceiptError("unacknowledged_receipt_claims_actor")
        return safe

    if document.get("actor_role") != "incident_commander":
        raise ProviderReceiptError("acknowledgement_actor_role_unverified")
    acknowledged = _parse_utc(
        document.get("acknowledged_at_utc"),
        code="acknowledgement_time_invalid",
    )
    if acknowledged < event.emitted_at or acknowledged > checked:
        raise ProviderReceiptError("acknowledgement_time_order_invalid")
    latency_delta = acknowledged - event.emitted_at
    if latency_delta > timedelta(seconds=ACK_WINDOW_SECONDS):
        raise ProviderReceiptError("acknowledgement_late")
    latency = int(latency_delta.total_seconds())
    safe.update(
        {
            "acknowledged_at_utc": _format_utc(acknowledged),
            "actor_role": "incident_commander",
            "latency_seconds": latency,
        }
    )
    return safe


def _safe_base_artifact(
    event: AlertEvent,
    mode: str,
    lifecycle: str = LIFECYCLE_FAILING,
    provider_obligation_required: bool = False,
    force_secondary_drill: bool = False,
) -> dict[str, Any]:
    return {
        "schema_version": SAFE_ARTIFACT_SCHEMA,
        "claim_status": "OPEN",
        "provider_mode": mode,
        "lifecycle": lifecycle,
        "provider_obligation_required": provider_obligation_required,
        "secondary_drill_requested": force_secondary_drill,
        "provider_obligation_satisfied": False,
        "event": {
            "event_id_sha256": event.event_id_sha256,
            "severity": "P1",
            "emitted_at_utc": _format_utc(event.emitted_at),
            "observed_at_utc": _format_utc(event.observed_at),
            "run_id": event.run_id,
            "issue_number": event.issue_number,
            "normalized_results": dict(event.results),
        },
        "incident_channel": {
            "destination_role": "incident_channel",
            "provider": "github",
            "status": "present",
            "issue_url_sha256": _sha256_bytes(event.issue_url.encode("utf-8")),
        },
        "primary_on_call": {"status": "unavailable"},
        "acknowledgement": {"status": "unavailable"},
        "secondary_escalation": {"status": "unavailable"},
        "outcome": "OPEN",
        "errors": [],
    }


def deliver_alert(
    *,
    config: ProviderConfig,
    event: AlertEvent,
    lifecycle: str = LIFECYCLE_FAILING,
    provider_obligation_required: bool = False,
    force_secondary_drill: bool = False,
    transport: Transport = _default_transport,
) -> tuple[dict[str, Any], bool]:
    artifact = _safe_base_artifact(
        event,
        config.mode,
        lifecycle,
        provider_obligation_required,
        force_secondary_drill,
    )
    if lifecycle not in {LIFECYCLE_FAILING, LIFECYCLE_RECOVERY_PENDING}:
        artifact["errors"] = ["lifecycle_invalid"]
        artifact["outcome"] = "configuration_error"
        return artifact, False
    if force_secondary_drill and lifecycle != LIFECYCLE_FAILING:
        artifact["errors"] = ["secondary_drill_requires_failing_lifecycle"]
        artifact["outcome"] = "configuration_error"
        return artifact, False
    if config.mode == MODE_DISABLED:
        if force_secondary_drill:
            artifact["errors"] = ["secondary_drill_requires_provider"]
            artifact["outcome"] = "configuration_error"
            return artifact, False
        if provider_obligation_required:
            artifact["errors"] = [
                "provider_configuration_removed_with_open_obligation"
            ]
            artifact["outcome"] = "configuration_error"
            return artifact, False
        artifact["outcome"] = "provider_disabled"
        return artifact, True
    if not config.primary or not config.acknowledgement or not config.secondary:
        artifact["errors"] = ["provider_configuration_incomplete"]
        artifact["outcome"] = "configuration_error"
        return artifact, False

    primary_error: AlertDeliveryError | None = None
    if lifecycle == LIFECYCLE_FAILING:
        try:
            primary_payload = _request_payload(
                action="deliver",
                destination_role="primary_on_call",
                event=event,
            )
            response = transport(
                config.primary,
                primary_payload,
                _idempotency_key(primary_payload),
            )
            artifact["primary_on_call"] = _delivery_receipt(
                response,
                event=event,
                action="deliver",
                destination_role="primary_on_call",
            )
        except AlertDeliveryError as exc:
            primary_error = exc
            artifact["primary_on_call"] = {
                "status": "unavailable",
                "reason": exc.code,
            }
    else:
        artifact["primary_on_call"] = {
            "status": "unavailable",
            "reason": "primary_delivery_not_replayed_during_recovery",
        }

    incident_age_seconds = max(
        0, int((event.observed_at - event.emitted_at).total_seconds())
    )
    should_escalate = primary_error is not None
    escalation_reason = "primary_delivery_unavailable"

    if primary_error is None and incident_age_seconds < ACK_WINDOW_SECONDS:
        artifact["acknowledgement"] = {
            "status": "awaiting_provider_receipt",
            "window_seconds": ACK_WINDOW_SECONDS,
            "incident_age_seconds": incident_age_seconds,
        }
        artifact["secondary_escalation"] = {
            "status": "not_triggered",
            "reason": "acknowledgement_window_open",
        }
        artifact["outcome"] = (
            "recovery_waiting_for_acknowledgement_window"
            if lifecycle == LIFECYCLE_RECOVERY_PENDING
            else "primary_delivered_waiting_for_acknowledgement"
        )
        return artifact, True

    if primary_error is None:
        try:
            acknowledgement_payload = _request_payload(
                action="check_acknowledgement",
                destination_role="primary_on_call",
                event=event,
                include_observation=True,
            )
            response = transport(
                config.acknowledgement,
                acknowledgement_payload,
                _idempotency_key(acknowledgement_payload),
            )
            acknowledgement = _acknowledgement_receipt(response, event=event)
            artifact["acknowledgement"] = acknowledgement
            if acknowledgement["status"] == "acknowledged":
                if not force_secondary_drill:
                    artifact["secondary_escalation"] = {
                        "status": "not_triggered",
                        "reason": "acknowledgement_verified_within_600_seconds",
                    }
                    artifact["provider_obligation_satisfied"] = True
                    if lifecycle == LIFECYCLE_RECOVERY_PENDING:
                        artifact["outcome"] = (
                            "recovery_acknowledgement_verified_before_closure"
                        )
                    else:
                        artifact["outcome"] = (
                            "primary_delivered_acknowledgement_verified"
                        )
                    return artifact, True
                # A customer-production drill deliberately proves the secondary
                # destination even though the primary incident commander did the
                # right thing.  The safe artifact retains both independent facts;
                # normal production behavior continues to suppress escalation.
                should_escalate = True
                escalation_reason = "explicit_secondary_escalation_drill"
                artifact["secondary_escalation"] = {
                    "status": "pending",
                    "reason": escalation_reason,
                }
            else:
                should_escalate = True
                escalation_reason = "unacknowledged_after_600_seconds"
        except AlertDeliveryError as exc:
            artifact["acknowledgement"] = {
                "status": "unavailable",
                "reason": exc.code,
            }
            should_escalate = True
            escalation_reason = "acknowledgement_unverified_after_600_seconds"

    escalation_error: AlertDeliveryError | None = None
    if should_escalate:
        try:
            escalation_payload = _request_payload(
                action="escalate",
                destination_role="secondary_on_call",
                event=event,
                # Keep the provider page stable even when the local diagnostic
                # reason changes across retries. The safe artifact retains the
                # exact trigger reason for this run.
                reason=(
                    "customer_production_secondary_escalation_drill"
                    if escalation_reason == "explicit_secondary_escalation_drill"
                    else "on_call_acknowledgement_unverified"
                ),
            )
            response = transport(
                config.secondary,
                escalation_payload,
                _idempotency_key(escalation_payload),
            )
            artifact["secondary_escalation"] = _delivery_receipt(
                response,
                event=event,
                action="escalate",
                destination_role="secondary_on_call",
            )
            artifact["secondary_escalation"]["trigger_reason"] = escalation_reason
        except AlertDeliveryError as exc:
            escalation_error = exc
            artifact["secondary_escalation"] = {
                "status": "unavailable",
                "reason": exc.code,
                "trigger_reason": escalation_reason,
            }

    errors = [
        exc.code for exc in (primary_error, escalation_error) if exc is not None
    ]
    artifact["errors"] = errors
    if primary_error is not None:
        artifact["outcome"] = (
            "primary_unavailable_secondary_delivered"
            if escalation_error is None
            else "primary_and_secondary_unavailable"
        )
        # A fallback page must never be re-labelled as successful dual delivery.
        return artifact, False
    if escalation_error is not None:
        artifact["outcome"] = "secondary_escalation_unavailable"
        return artifact, False
    if escalation_reason == "explicit_secondary_escalation_drill":
        artifact["provider_obligation_satisfied"] = True
        artifact["outcome"] = (
            "recovery_acknowledged_secondary_drill_escalated"
            if lifecycle == LIFECYCLE_RECOVERY_PENDING
            else "primary_delivered_acknowledged_secondary_drill_escalated"
        )
        return artifact, True
    if lifecycle == LIFECYCLE_RECOVERY_PENDING:
        artifact["provider_obligation_satisfied"] = True
        artifact["outcome"] = "recovery_secondary_escalation_verified_before_closure"
    else:
        artifact["provider_obligation_satisfied"] = True
        artifact["outcome"] = "primary_delivered_secondary_escalated"
    return artifact, True


def _write_safe_artifact(path: Path, artifact: Mapping[str, Any]) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (
        json.dumps(artifact, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("utf-8")
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    try:
        try:
            os.fchmod(fd, 0o600)
        except (AttributeError, OSError):
            pass
        with os.fdopen(fd, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Deliver one normalized production runtime alert."
    )
    parser.add_argument("--mode", default=MODE_DISABLED)
    parser.add_argument("--require-provider-obligation", action="store_true")
    parser.add_argument(
        "--force-secondary-drill",
        action="store_true",
        help=(
            "after a verified timely incident-commander acknowledgement, also "
            "deliver to secondary_on_call as an explicit acceptance drill"
        ),
    )
    parser.add_argument(
        "--lifecycle",
        choices=(LIFECYCLE_FAILING, LIFECYCLE_RECOVERY_PENDING),
        default=LIFECYCLE_FAILING,
    )
    parser.add_argument("--repository", required=True)
    parser.add_argument("--run-id", required=True, type=int)
    parser.add_argument("--issue-number", required=True, type=int)
    parser.add_argument("--emitted-at-utc", required=True)
    parser.add_argument("--api-result", required=True)
    parser.add_argument("--worker-result", required=True)
    parser.add_argument("--blueprint-result", required=True)
    parser.add_argument("--aggregate-result", required=True)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def _event_from_args(args: argparse.Namespace, *, now: datetime) -> AlertEvent:
    if not REPOSITORY_RE.fullmatch(args.repository):
        raise ConfigurationError("repository_invalid")
    if args.run_id <= 0:
        raise ConfigurationError("run_id_invalid")
    if args.issue_number <= 0:
        raise ConfigurationError("issue_number_invalid")
    results = {
        "api": args.api_result,
        "worker": args.worker_result,
        "blueprint": args.blueprint_result,
        "aggregate": args.aggregate_result,
    }
    if any(value not in RESULT_VALUES for value in results.values()):
        raise ConfigurationError("monitor_result_invalid")
    if args.lifecycle == LIFECYCLE_FAILING and results["aggregate"] == "success":
        raise ConfigurationError("provider_delivery_requires_failed_aggregate")
    if (
        args.lifecycle == LIFECYCLE_RECOVERY_PENDING
        and results["aggregate"] != "success"
    ):
        raise ConfigurationError("provider_recovery_requires_successful_aggregate")
    emitted = _parse_cli_utc(args.emitted_at_utc, label="emitted_at_utc")
    if emitted > now + timedelta(seconds=MAX_CLOCK_SKEW_SECONDS):
        raise ConfigurationError("emitted_at_utc_in_future")
    return AlertEvent(
        repository=args.repository,
        run_id=args.run_id,
        issue_number=args.issue_number,
        emitted_at=emitted,
        observed_at=now,
        results=results,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    now = datetime.now(timezone.utc)
    try:
        event = _event_from_args(args, now=now)
    except ConfigurationError as exc:
        # No event identifier can be trusted, so do not manufacture a receipt file.
        print(f"runtime alert adapter configuration error: {exc.code}", file=sys.stderr)
        return 2

    try:
        config = load_provider_config(args.mode)
    except ConfigurationError as exc:
        normalized_mode = str(args.mode or MODE_DISABLED)
        safe_mode = (
            normalized_mode
            if normalized_mode in {MODE_DISABLED, MODE_WEBHOOK_V1}
            else "invalid"
        )
        artifact = _safe_base_artifact(
            event,
            safe_mode,
            args.lifecycle,
            args.require_provider_obligation,
            args.force_secondary_drill,
        )
        artifact["outcome"] = "configuration_error"
        artifact["errors"] = [exc.code]
        _write_safe_artifact(args.output, artifact)
        print(f"runtime alert adapter configuration error: {exc.code}", file=sys.stderr)
        return 2

    try:
        artifact, succeeded = deliver_alert(
            config=config,
            event=event,
            lifecycle=args.lifecycle,
            provider_obligation_required=args.require_provider_obligation,
            force_secondary_drill=args.force_secondary_drill,
        )
    except Exception:
        artifact = _safe_base_artifact(
            event,
            config.mode,
            args.lifecycle,
            args.require_provider_obligation,
            args.force_secondary_drill,
        )
        artifact["outcome"] = "internal_error"
        artifact["errors"] = ["provider_adapter_internal_error"]
        _write_safe_artifact(args.output, artifact)
        print("runtime alert adapter failed: provider_adapter_internal_error", file=sys.stderr)
        return 1
    _write_safe_artifact(args.output, artifact)
    if config.mode == MODE_DISABLED:
        print(
            "Optional on-call provider delivery is disabled; GitHub issue delivery remains present."
        )
    else:
        print(f"Runtime alert adapter outcome: {artifact['outcome']}")
    return 0 if succeeded else 1


if __name__ == "__main__":
    raise SystemExit(main())
