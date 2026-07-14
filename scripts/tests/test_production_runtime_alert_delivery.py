from __future__ import annotations

from datetime import datetime, timedelta, timezone
from contextlib import redirect_stderr
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "deliver_production_runtime_alert.py"
SPEC = importlib.util.spec_from_file_location("runtime_alert_delivery", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
delivery = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = delivery
SPEC.loader.exec_module(delivery)


NOW = datetime(2026, 7, 14, 18, 0, 0, tzinfo=timezone.utc)


def _endpoint(name: str) -> object:
    return delivery.Endpoint(
        url=f"https://{name}.alerts.example.test/v1/events",
        token=f"{name}-token-0123456789",
    )


def _config() -> object:
    return delivery.ProviderConfig(
        mode=delivery.MODE_WEBHOOK_V1,
        primary=_endpoint("primary"),
        acknowledgement=_endpoint("ack"),
        secondary=_endpoint("secondary"),
    )


def _event(
    *, age_seconds: int = 30, run_id: int = 1234, aggregate_result: str = "failure"
) -> object:
    component_result = "success" if aggregate_result == "success" else "failure"
    return delivery.AlertEvent(
        repository="LittleHenderson/noetic-compass",
        run_id=run_id,
        issue_number=154,
        emitted_at=NOW - timedelta(seconds=age_seconds),
        observed_at=NOW,
        results={
            "api": component_result,
            "worker": "success",
            "blueprint": "success",
            "aggregate": aggregate_result,
        },
    )


def _response(document: dict[str, object]) -> object:
    return delivery.TransportResponse(
        status=200,
        body=json.dumps(document, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        ),
    )


def _delivery_document(
    event: object,
    *,
    action: str = "deliver",
    role: str = "primary_on_call",
    receipt_id: str = "provider-receipt-123",
    delivered_at: datetime | None = None,
) -> dict[str, object]:
    timestamp = delivered_at or event.observed_at
    return {
        "schema_version": delivery.RECEIPT_SCHEMA,
        "action": action,
        "event_id_sha256": event.event_id_sha256,
        "destination_role": role,
        "status": "delivered",
        "delivered_at_utc": delivery._format_utc(timestamp),
        "receipt_id": receipt_id,
    }


def _ack_document(
    event: object,
    *,
    status: str,
    acknowledged_at: datetime | None = None,
    actor_role: str | None = None,
    receipt_id: str = "ack-receipt-456",
) -> dict[str, object]:
    return {
        "schema_version": delivery.RECEIPT_SCHEMA,
        "action": "check_acknowledgement",
        "event_id_sha256": event.event_id_sha256,
        "status": status,
        "checked_at_utc": delivery._format_utc(event.observed_at),
        "acknowledged_at_utc": (
            delivery._format_utc(acknowledged_at)
            if acknowledged_at is not None
            else None
        ),
        "actor_role": actor_role,
        "receipt_id": receipt_id,
    }


class QueueTransport:
    def __init__(self, responses: list[object]) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[object, dict[str, object], str]] = []

    def __call__(
        self, endpoint: object, payload: dict[str, object], idempotency_key: str
    ) -> object:
        self.calls.append((endpoint, payload, idempotency_key))
        if not self.responses:
            raise AssertionError("unexpected provider call")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class ProviderConfigurationTests(unittest.TestCase):
    def test_disabled_mode_does_not_read_or_validate_provider_secrets(self) -> None:
        config = delivery.load_provider_config(
            "",
            {
                "CAS_ALERT_PRIMARY_WEBHOOK_URL": "http://127.0.0.1/secret",
                "CAS_ALERT_PRIMARY_WEBHOOK_TOKEN": "short",
            },
        )
        self.assertEqual(config.mode, delivery.MODE_DISABLED)
        self.assertIsNone(config.primary)

    def test_enabled_mode_requires_all_three_authenticated_endpoints(self) -> None:
        with self.assertRaises(delivery.ConfigurationError) as caught:
            delivery.load_provider_config(delivery.MODE_WEBHOOK_V1, {})
        self.assertEqual(caught.exception.code, "primary_configuration_incomplete")

    def test_mode_is_exact_and_does_not_normalize_drift_to_disabled(self) -> None:
        for value in ("DISABLED", " disabled ", "WEBHOOK_V1"):
            with self.subTest(value=value), self.assertRaises(
                delivery.ConfigurationError
            ) as caught:
                delivery.load_provider_config(value, {})
            self.assertEqual(caught.exception.code, "provider_mode_invalid")

    def test_enabled_mode_loads_complete_configuration(self) -> None:
        env: dict[str, str] = {}
        for prefix in ("PRIMARY", "ACK", "SECONDARY"):
            env[f"CAS_ALERT_{prefix}_WEBHOOK_URL"] = (
                f"https://{prefix.lower()}.alerts.example.com/v1/events"
            )
            env[f"CAS_ALERT_{prefix}_WEBHOOK_TOKEN"] = (
                f"{prefix.lower()}-secret-0123456789"
            )
        config = delivery.load_provider_config(delivery.MODE_WEBHOOK_V1, env)
        self.assertEqual(config.mode, delivery.MODE_WEBHOOK_V1)
        self.assertEqual(config.primary.url, env["CAS_ALERT_PRIMARY_WEBHOOK_URL"])

    def test_unsafe_webhook_urls_fail_closed(self) -> None:
        unsafe = (
            "http://alerts.example.com/v1",
            "https://user:pass@alerts.example.com/v1",
            "https://127.0.0.1/v1",
            "https://169.254.169.254/v1",
            "https://alerts.local/v1",
            "https://alerts.example.com:8443/v1",
            "https://alerts.example.com/v1?token=secret",
        )
        for value in unsafe:
            with self.subTest(value=value), self.assertRaises(
                delivery.ConfigurationError
            ):
                delivery._validated_https_url(value, name="primary")

    def test_tokens_with_control_characters_fail_closed(self) -> None:
        for value in (
            "short",
            "valid-length-token\nheader",
            " leading-whitespace-token",
            "unicode-token-0123456789-\u2603",
            "x" * 4097,
        ):
            with self.subTest(value=value[:20]), self.assertRaises(
                delivery.ConfigurationError
            ):
                delivery._validated_token(value, name="primary")


class RuntimeAlertDeliveryTests(unittest.TestCase):
    def test_disabled_mode_makes_no_provider_calls(self) -> None:
        transport = QueueTransport([])
        artifact, succeeded = delivery.deliver_alert(
            config=delivery.ProviderConfig(mode=delivery.MODE_DISABLED),
            event=_event(),
            transport=transport,
        )
        self.assertTrue(succeeded)
        self.assertEqual(transport.calls, [])
        self.assertEqual(artifact["outcome"], "provider_disabled")
        self.assertEqual(artifact["claim_status"], "OPEN")
        self.assertEqual(artifact["incident_channel"]["status"], "present")

    def test_persisted_obligation_rejects_removed_provider_configuration(self) -> None:
        event = _event(age_seconds=900, aggregate_result="success")
        transport = QueueTransport([])
        artifact, succeeded = delivery.deliver_alert(
            config=delivery.ProviderConfig(mode=delivery.MODE_DISABLED),
            event=event,
            lifecycle=delivery.LIFECYCLE_RECOVERY_PENDING,
            provider_obligation_required=True,
            transport=transport,
        )
        self.assertFalse(succeeded)
        self.assertEqual(transport.calls, [])
        self.assertFalse(artifact["provider_obligation_satisfied"])
        self.assertEqual(artifact["outcome"], "configuration_error")
        self.assertEqual(
            artifact["errors"],
            ["provider_configuration_removed_with_open_obligation"],
        )

    def test_enabled_recovery_before_600_seconds_leaves_obligation_open(self) -> None:
        event = _event(age_seconds=599, aggregate_result="success")
        transport = QueueTransport([])
        artifact, succeeded = delivery.deliver_alert(
            config=_config(),
            event=event,
            lifecycle=delivery.LIFECYCLE_RECOVERY_PENDING,
            transport=transport,
        )
        self.assertTrue(succeeded)
        self.assertEqual(transport.calls, [])
        self.assertFalse(artifact["provider_obligation_satisfied"])
        self.assertEqual(
            artifact["outcome"], "recovery_waiting_for_acknowledgement_window"
        )
        self.assertEqual(
            artifact["primary_on_call"]["reason"],
            "primary_delivery_not_replayed_during_recovery",
        )

    def test_enabled_recovery_closes_obligation_after_verified_ack(self) -> None:
        event = _event(age_seconds=900, aggregate_result="success")
        transport = QueueTransport(
            [
                _response(
                    _ack_document(
                        event,
                        status="acknowledged",
                        acknowledged_at=event.emitted_at + timedelta(seconds=300),
                        actor_role="incident_commander",
                    )
                )
            ]
        )
        artifact, succeeded = delivery.deliver_alert(
            config=_config(),
            event=event,
            lifecycle=delivery.LIFECYCLE_RECOVERY_PENDING,
            transport=transport,
        )
        self.assertTrue(succeeded)
        self.assertEqual(len(transport.calls), 1)
        self.assertEqual(
            transport.calls[0][1]["action"], "check_acknowledgement"
        )
        self.assertTrue(artifact["provider_obligation_satisfied"])
        self.assertEqual(
            artifact["outcome"],
            "recovery_acknowledgement_verified_before_closure",
        )

    def test_enabled_recovery_escalates_unacknowledged_incident_before_closure(
        self,
    ) -> None:
        event = _event(age_seconds=900, aggregate_result="success")
        transport = QueueTransport(
            [
                _response(_ack_document(event, status="unacknowledged")),
                _response(
                    _delivery_document(
                        event, action="escalate", role="secondary_on_call"
                    )
                ),
            ]
        )
        artifact, succeeded = delivery.deliver_alert(
            config=_config(),
            event=event,
            lifecycle=delivery.LIFECYCLE_RECOVERY_PENDING,
            transport=transport,
        )
        self.assertTrue(succeeded)
        self.assertEqual([call[1]["action"] for call in transport.calls], [
            "check_acknowledgement",
            "escalate",
        ])
        self.assertTrue(artifact["provider_obligation_satisfied"])
        self.assertEqual(
            artifact["outcome"],
            "recovery_secondary_escalation_verified_before_closure",
        )

    def test_enabled_recovery_secondary_failure_keeps_obligation_open(self) -> None:
        event = _event(age_seconds=900, aggregate_result="success")
        transport = QueueTransport(
            [
                _response(_ack_document(event, status="unacknowledged")),
                delivery.ProviderTransportError("provider_unreachable"),
            ]
        )
        artifact, succeeded = delivery.deliver_alert(
            config=_config(),
            event=event,
            lifecycle=delivery.LIFECYCLE_RECOVERY_PENDING,
            transport=transport,
        )
        self.assertFalse(succeeded)
        self.assertFalse(artifact["provider_obligation_satisfied"])
        self.assertEqual(artifact["outcome"], "secondary_escalation_unavailable")

    def test_primary_delivery_waits_while_ack_window_is_open(self) -> None:
        event = _event(age_seconds=599)
        receipt_id = "raw-primary-receipt-should-be-hashed"
        transport = QueueTransport(
            [_response(_delivery_document(event, receipt_id=receipt_id))]
        )
        artifact, succeeded = delivery.deliver_alert(
            config=_config(), event=event, transport=transport
        )
        self.assertTrue(succeeded)
        self.assertEqual(len(transport.calls), 1)
        self.assertEqual(
            transport.calls[0][1]["destination_role"], "primary_on_call"
        )
        self.assertEqual(artifact["primary_on_call"]["status"], "delivered")
        self.assertNotIn(receipt_id, json.dumps(artifact))
        self.assertEqual(
            artifact["acknowledgement"]["status"],
            "awaiting_provider_receipt",
        )
        self.assertEqual(
            artifact["secondary_escalation"]["status"], "not_triggered"
        )
        self.assertFalse(artifact["provider_obligation_satisfied"])

    def test_verified_incident_commander_ack_suppresses_escalation(self) -> None:
        event = _event(age_seconds=900)
        acknowledged_at = event.emitted_at + timedelta(seconds=300)
        transport = QueueTransport(
            [
                _response(_delivery_document(event)),
                _response(
                    _ack_document(
                        event,
                        status="acknowledged",
                        acknowledged_at=acknowledged_at,
                        actor_role="incident_commander",
                    )
                ),
            ]
        )
        artifact, succeeded = delivery.deliver_alert(
            config=_config(), event=event, transport=transport
        )
        self.assertTrue(succeeded)
        self.assertEqual(len(transport.calls), 2)
        self.assertEqual(artifact["acknowledgement"]["status"], "acknowledged")
        self.assertEqual(artifact["acknowledgement"]["latency_seconds"], 300)
        self.assertEqual(
            artifact["secondary_escalation"]["reason"],
            "acknowledgement_verified_within_600_seconds",
        )
        self.assertTrue(artifact["provider_obligation_satisfied"])

    def test_exact_600_second_boundary_queries_acknowledgement(self) -> None:
        event = _event(age_seconds=600)
        transport = QueueTransport(
            [
                _response(_delivery_document(event)),
                _response(
                    _ack_document(
                        event,
                        status="acknowledged",
                        acknowledged_at=event.emitted_at + timedelta(seconds=120),
                        actor_role="incident_commander",
                    )
                ),
            ]
        )
        artifact, succeeded = delivery.deliver_alert(
            config=_config(), event=event, transport=transport
        )
        self.assertTrue(succeeded)
        self.assertEqual(len(transport.calls), 2)
        self.assertEqual(artifact["acknowledgement"]["status"], "acknowledged")

    def test_unacknowledged_incident_escalates_to_secondary(self) -> None:
        event = _event(age_seconds=901)
        transport = QueueTransport(
            [
                _response(_delivery_document(event)),
                _response(_ack_document(event, status="unacknowledged")),
                _response(
                    _delivery_document(
                        event,
                        action="escalate",
                        role="secondary_on_call",
                        receipt_id="secondary-receipt-789",
                    )
                ),
            ]
        )
        artifact, succeeded = delivery.deliver_alert(
            config=_config(), event=event, transport=transport
        )
        self.assertTrue(succeeded)
        self.assertEqual(len(transport.calls), 3)
        self.assertEqual(
            transport.calls[2][1]["reason"],
            "on_call_acknowledgement_unverified",
        )
        self.assertEqual(
            artifact["secondary_escalation"]["trigger_reason"],
            "unacknowledged_after_600_seconds",
        )
        self.assertEqual(
            artifact["secondary_escalation"]["status"], "delivered"
        )
        self.assertEqual(
            artifact["secondary_escalation"]["destination_role"],
            "secondary_on_call",
        )
        self.assertTrue(artifact["provider_obligation_satisfied"])

    def test_malformed_ack_receipt_escalates_without_fabricating_ack(self) -> None:
        event = _event(age_seconds=901)
        malformed = _ack_document(
            event,
            status="acknowledged",
            acknowledged_at=event.emitted_at + timedelta(seconds=100),
            actor_role="random_user",
        )
        transport = QueueTransport(
            [
                _response(_delivery_document(event)),
                _response(malformed),
                _response(
                    _delivery_document(
                        event,
                        action="escalate",
                        role="secondary_on_call",
                    )
                ),
            ]
        )
        artifact, succeeded = delivery.deliver_alert(
            config=_config(), event=event, transport=transport
        )
        self.assertTrue(succeeded)
        self.assertEqual(artifact["acknowledgement"]["status"], "unavailable")
        self.assertEqual(
            artifact["acknowledgement"]["reason"],
            "acknowledgement_actor_role_unverified",
        )
        self.assertNotIn("acknowledged_at_utc", artifact["acknowledgement"])
        self.assertEqual(
            artifact["secondary_escalation"]["trigger_reason"],
            "acknowledgement_unverified_after_600_seconds",
        )

    def test_unavailable_ack_provider_escalates_without_fabricating_ack(self) -> None:
        event = _event(age_seconds=901)
        transport = QueueTransport(
            [
                _response(_delivery_document(event)),
                delivery.ProviderTransportError("provider_unreachable"),
                _response(
                    _delivery_document(
                        event, action="escalate", role="secondary_on_call"
                    )
                ),
            ]
        )
        artifact, succeeded = delivery.deliver_alert(
            config=_config(), event=event, transport=transport
        )
        self.assertTrue(succeeded)
        self.assertEqual(
            artifact["acknowledgement"],
            {"status": "unavailable", "reason": "provider_unreachable"},
        )
        self.assertEqual(
            artifact["secondary_escalation"]["trigger_reason"],
            "acknowledgement_unverified_after_600_seconds",
        )

    def test_late_ack_receipt_escalates_and_is_not_claimed(self) -> None:
        event = _event(age_seconds=901)
        transport = QueueTransport(
            [
                _response(_delivery_document(event)),
                _response(
                    _ack_document(
                        event,
                        status="acknowledged",
                        acknowledged_at=event.emitted_at + timedelta(seconds=601),
                        actor_role="incident_commander",
                    )
                ),
                _response(
                    _delivery_document(
                        event, action="escalate", role="secondary_on_call"
                    )
                ),
            ]
        )
        artifact, succeeded = delivery.deliver_alert(
            config=_config(), event=event, transport=transport
        )
        self.assertTrue(succeeded)
        self.assertEqual(
            artifact["acknowledgement"]["reason"], "acknowledgement_late"
        )
        self.assertEqual(
            artifact["secondary_escalation"]["status"], "delivered"
        )

    def test_fractional_second_over_ack_limit_is_late(self) -> None:
        event = _event(age_seconds=901)
        late = _ack_document(
            event,
            status="acknowledged",
            acknowledged_at=event.emitted_at + timedelta(seconds=600),
            actor_role="incident_commander",
        )
        late["acknowledged_at_utc"] = (
            event.emitted_at + timedelta(seconds=600, milliseconds=1)
        ).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        transport = QueueTransport(
            [
                _response(_delivery_document(event)),
                _response(late),
                _response(
                    _delivery_document(
                        event, action="escalate", role="secondary_on_call"
                    )
                ),
            ]
        )
        artifact, succeeded = delivery.deliver_alert(
            config=_config(), event=event, transport=transport
        )
        self.assertTrue(succeeded)
        self.assertEqual(
            artifact["acknowledgement"]["reason"], "acknowledgement_late"
        )

    def test_wrong_event_primary_receipt_attempts_fallback_but_fails_dual_delivery(
        self,
    ) -> None:
        event = _event(age_seconds=30)
        wrong = _delivery_document(event)
        wrong["event_id_sha256"] = "0" * 64
        transport = QueueTransport(
            [
                _response(wrong),
                _response(
                    _delivery_document(
                        event, action="escalate", role="secondary_on_call"
                    )
                ),
            ]
        )
        artifact, succeeded = delivery.deliver_alert(
            config=_config(), event=event, transport=transport
        )
        self.assertFalse(succeeded)
        self.assertEqual(artifact["primary_on_call"]["status"], "unavailable")
        self.assertEqual(
            artifact["primary_on_call"]["reason"],
            "delivery_receipt_event_mismatch",
        )
        self.assertEqual(
            artifact["secondary_escalation"]["status"], "delivered"
        )
        self.assertEqual(
            artifact["outcome"], "primary_unavailable_secondary_delivered"
        )

    def test_missing_secondary_receipt_fails_the_delivery_job(self) -> None:
        event = _event(age_seconds=901)
        transport = QueueTransport(
            [
                _response(_delivery_document(event)),
                _response(_ack_document(event, status="unacknowledged")),
                delivery.ProviderTransportError("provider_unreachable"),
            ]
        )
        artifact, succeeded = delivery.deliver_alert(
            config=_config(), event=event, transport=transport
        )
        self.assertFalse(succeeded)
        self.assertEqual(
            artifact["secondary_escalation"]["status"], "unavailable"
        )
        self.assertEqual(
            artifact["outcome"], "secondary_escalation_unavailable"
        )

    def test_delivery_timestamp_before_emission_is_rejected(self) -> None:
        event = _event(age_seconds=30)
        primary = _delivery_document(
            event, delivered_at=event.emitted_at - timedelta(seconds=1)
        )
        transport = QueueTransport(
            [
                _response(primary),
                _response(
                    _delivery_document(
                        event, action="escalate", role="secondary_on_call"
                    )
                ),
            ]
        )
        artifact, succeeded = delivery.deliver_alert(
            config=_config(), event=event, transport=transport
        )
        self.assertFalse(succeeded)
        self.assertEqual(
            artifact["primary_on_call"]["reason"],
            "delivery_receipt_precedes_emission",
        )

    def test_incident_idempotent_primary_receipt_can_be_reused_on_retry(self) -> None:
        event = _event(age_seconds=901)
        primary = _delivery_document(
            event, delivered_at=event.observed_at - timedelta(seconds=301)
        )
        transport = QueueTransport(
            [
                _response(primary),
                _response(
                    _ack_document(
                        event,
                        status="acknowledged",
                        acknowledged_at=event.emitted_at + timedelta(seconds=300),
                        actor_role="incident_commander",
                    )
                ),
            ]
        )
        artifact, succeeded = delivery.deliver_alert(
            config=_config(), event=event, transport=transport
        )
        self.assertTrue(succeeded)
        self.assertEqual(
            artifact["primary_on_call"]["status"],
            "delivered",
        )

    def test_stable_event_id_is_bound_to_incident_not_monitor_retry(self) -> None:
        first = _event(run_id=100)
        retry = _event(run_id=101)
        self.assertEqual(first.event_id_sha256, retry.event_id_sha256)
        self.assertEqual(first.provider_payload(), retry.provider_payload())
        self.assertNotEqual(first.run_url, retry.run_url)

    def test_primary_idempotency_is_incident_stable_but_ack_queries_are_fresh(
        self,
    ) -> None:
        first = _event(run_id=100)
        retry = _event(run_id=101)
        first_payload = delivery._request_payload(
            action="deliver", destination_role="primary_on_call", event=first
        )
        retry_payload = delivery._request_payload(
            action="deliver", destination_role="primary_on_call", event=retry
        )
        self.assertEqual(first_payload, retry_payload)
        self.assertEqual(
            delivery._idempotency_key(first_payload),
            delivery._idempotency_key(retry_payload),
        )
        first_ack = delivery._request_payload(
            action="check_acknowledgement",
            destination_role="primary_on_call",
            event=first,
            include_observation=True,
        )
        retry_ack = delivery._request_payload(
            action="check_acknowledgement",
            destination_role="primary_on_call",
            event=retry,
            include_observation=True,
        )
        self.assertNotEqual(
            delivery._idempotency_key(first_ack),
            delivery._idempotency_key(retry_ack),
        )


class ReceiptParserAndArtifactTests(unittest.TestCase):
    def test_duplicate_json_keys_are_rejected(self) -> None:
        with self.assertRaises(delivery.ProviderReceiptError) as caught:
            delivery._json_object_without_duplicates(b'{"status":"delivered","status":"failed"}')
        self.assertEqual(caught.exception.code, "provider_response_duplicate_key")

    def test_oversized_provider_response_is_rejected(self) -> None:
        with self.assertRaises(delivery.ProviderReceiptError) as caught:
            delivery._json_object_without_duplicates(
                b"{" + b" " * delivery.MAX_RESPONSE_BYTES + b"}"
            )
        self.assertEqual(caught.exception.code, "provider_response_size_invalid")

    def test_redirect_handler_refuses_secret_forwarding(self) -> None:
        handler = delivery._NoRedirectHandler()
        req = delivery.request.Request("https://primary.alerts.example.com/v1")
        with self.assertRaises(delivery.ProviderTransportError) as caught:
            handler.redirect_request(
                req,
                None,
                302,
                "Found",
                {},
                "https://attacker.example.net/steal",
            )
        self.assertEqual(caught.exception.code, "provider_redirect_refused")

    def test_safe_artifact_contains_no_provider_secret_url_or_raw_receipt(self) -> None:
        event = _event(age_seconds=30)
        config = _config()
        receipt_id = "raw-receipt-sensitive-identifier"
        transport = QueueTransport(
            [_response(_delivery_document(event, receipt_id=receipt_id))]
        )
        artifact, succeeded = delivery.deliver_alert(
            config=config, event=event, transport=transport
        )
        self.assertTrue(succeeded)
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "safe.json"
            delivery._write_safe_artifact(path, artifact)
            raw = path.read_text(encoding="utf-8")
            parsed = json.loads(raw)
        self.assertEqual(parsed["claim_status"], "OPEN")
        for forbidden in (
            config.primary.url,
            config.primary.token,
            config.acknowledgement.url,
            config.acknowledgement.token,
            config.secondary.url,
            config.secondary.token,
            receipt_id,
        ):
            self.assertNotIn(forbidden, raw)
        self.assertRegex(
            parsed["primary_on_call"]["receipt_id_sha256"], r"^[0-9a-f]{64}$"
        )

    def test_disabled_cli_preserves_github_only_default(self) -> None:
        emitted = delivery._format_utc(
            datetime.now(timezone.utc) - timedelta(seconds=30)
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "safe.json"
            exit_code = delivery.main(
                [
                    "--mode",
                    delivery.MODE_DISABLED,
                    "--repository",
                    "LittleHenderson/noetic-compass",
                    "--run-id",
                    "1234",
                    "--issue-number",
                    "154",
                    "--emitted-at-utc",
                    emitted,
                    "--api-result",
                    "failure",
                    "--worker-result",
                    "success",
                    "--blueprint-result",
                    "success",
                    "--aggregate-result",
                    "failure",
                    "--output",
                    str(output),
                ]
            )
            artifact = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(exit_code, 0)
        self.assertEqual(artifact["provider_mode"], delivery.MODE_DISABLED)
        self.assertEqual(artifact["outcome"], "provider_disabled")
        self.assertEqual(artifact["incident_channel"]["status"], "present")
        self.assertEqual(artifact["primary_on_call"]["status"], "unavailable")

    def test_configuration_error_stderr_and_artifact_do_not_leak_secrets(self) -> None:
        primary_url = "https://primary.alerts.example.com/v1/events"
        primary_token = "primary-super-secret-token"
        emitted = delivery._format_utc(
            datetime.now(timezone.utc) - timedelta(seconds=30)
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "safe.json"
            stderr = io.StringIO()
            with mock.patch.dict(
                delivery.os.environ,
                {
                    "CAS_ALERT_PRIMARY_WEBHOOK_URL": primary_url,
                    "CAS_ALERT_PRIMARY_WEBHOOK_TOKEN": primary_token,
                },
                clear=True,
            ), redirect_stderr(stderr):
                exit_code = delivery.main(
                    [
                        "--mode",
                        delivery.MODE_WEBHOOK_V1,
                        "--repository",
                        "LittleHenderson/noetic-compass",
                        "--run-id",
                        "1234",
                        "--issue-number",
                        "154",
                        "--emitted-at-utc",
                        emitted,
                        "--api-result",
                        "failure",
                        "--worker-result",
                        "success",
                        "--blueprint-result",
                        "success",
                        "--aggregate-result",
                        "failure",
                        "--output",
                        str(output),
                    ]
                )
            artifact_text = output.read_text(encoding="utf-8")
        self.assertEqual(exit_code, 2)
        combined = stderr.getvalue() + artifact_text
        self.assertNotIn(primary_url, combined)
        self.assertNotIn(primary_token, combined)
        self.assertIn("acknowledgement_configuration_incomplete", combined)

    def test_invalid_event_fails_before_artifact_so_upload_fails_closed(self) -> None:
        emitted = delivery._format_utc(
            datetime.now(timezone.utc) - timedelta(seconds=30)
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "must-not-exist.json"
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                exit_code = delivery.main(
                    [
                        "--mode",
                        delivery.MODE_DISABLED,
                        "--repository",
                        "LittleHenderson/noetic-compass",
                        "--run-id",
                        "1234",
                        "--issue-number",
                        "0",
                        "--emitted-at-utc",
                        emitted,
                        "--api-result",
                        "failure",
                        "--worker-result",
                        "success",
                        "--blueprint-result",
                        "success",
                        "--aggregate-result",
                        "failure",
                        "--output",
                        str(output),
                    ]
                )
            exists = output.exists()
        self.assertEqual(exit_code, 2)
        self.assertFalse(exists)
        self.assertIn("issue_number_invalid", stderr.getvalue())

    def test_unexpected_adapter_error_is_normalized_without_secret_traceback(self) -> None:
        provider_secret = "unexpected-provider-secret-value"
        emitted = delivery._format_utc(
            datetime.now(timezone.utc) - timedelta(seconds=30)
        )
        env: dict[str, str] = {}
        for prefix in ("PRIMARY", "ACK", "SECONDARY"):
            env[f"CAS_ALERT_{prefix}_WEBHOOK_URL"] = (
                f"https://{prefix.lower()}.alerts.example.com/v1/events"
            )
            env[f"CAS_ALERT_{prefix}_WEBHOOK_TOKEN"] = (
                f"{prefix.lower()}-secret-0123456789"
            )
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "safe.json"
            stderr = io.StringIO()
            with mock.patch.dict(delivery.os.environ, env, clear=True), mock.patch.object(
                delivery,
                "deliver_alert",
                side_effect=RuntimeError(provider_secret),
            ), redirect_stderr(stderr):
                exit_code = delivery.main(
                    [
                        "--mode",
                        delivery.MODE_WEBHOOK_V1,
                        "--repository",
                        "LittleHenderson/noetic-compass",
                        "--run-id",
                        "1234",
                        "--issue-number",
                        "154",
                        "--emitted-at-utc",
                        emitted,
                        "--api-result",
                        "failure",
                        "--worker-result",
                        "success",
                        "--blueprint-result",
                        "success",
                        "--aggregate-result",
                        "failure",
                        "--output",
                        str(output),
                    ]
                )
            combined = stderr.getvalue() + output.read_text(encoding="utf-8")
        self.assertEqual(exit_code, 1)
        self.assertNotIn(provider_secret, combined)
        self.assertIn("provider_adapter_internal_error", combined)


if __name__ == "__main__":
    unittest.main()
