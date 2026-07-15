from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest

from scripts import build_alert_delivery_gate_payload as builder


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "deliver_alert_delivery_drill.py"
SPEC = importlib.util.spec_from_file_location("alert_delivery_drill", MODULE_PATH)
assert SPEC and SPEC.loader
drill = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = drill
SPEC.loader.exec_module(drill)


UTC = timezone.utc
EMITTED = datetime(2026, 7, 15, 12, 0, tzinfo=UTC)


def _endpoint(role: str) -> drill.hardened.Endpoint:
    return drill.hardened.Endpoint(
        url=f"https://alerts.example.com/{role}", token=f"token-for-{role}-0123456789"
    )


def _config() -> drill.DrillProviderConfig:
    return drill.DrillProviderConfig(
        mode=drill.MODE_WEBHOOK_V1,
        incident=_endpoint("incident"),
        primary=_endpoint("primary"),
        acknowledgement=_endpoint("ack"),
        secondary=_endpoint("secondary"),
    )


def _event() -> drill.DrillEvent:
    return drill.DrillEvent(
        repository="LittleHenderson/noetic-compass",
        run_id=123,
        run_attempt=2,
        emitted_at=EMITTED,
    )


def _body(payload: dict) -> drill.hardened.TransportResponse:
    return drill.hardened.TransportResponse(
        status=200,
        body=json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        ),
    )


def _delivery_response(
    event: drill.DrillEvent,
    *,
    action: str,
    role: str,
    delivered_at: datetime,
    receipt_id: str,
) -> drill.hardened.TransportResponse:
    return _body(
        {
            "schema_version": drill.RECEIPT_SCHEMA,
            "event_schema": drill.EVENT_SCHEMA,
            "action": action,
            "event_id_sha256": event.event_id_sha256,
            "destination_role": role,
            "status": "delivered",
            "delivered_at_utc": drill.hardened._format_utc(delivered_at),
            "receipt_id": receipt_id,
        }
    )


def _ack_response(
    event: drill.DrillEvent,
    *,
    checked_at: datetime,
    acknowledged_at: datetime | None,
    actor_role: str | None = "incident_commander",
    actor_type: str | None = "human",
    actor_id: str | None = "commander@example.com",
    synthetic: bool = False,
) -> drill.hardened.TransportResponse:
    acknowledged = acknowledged_at is not None
    return _body(
        {
            "schema_version": drill.RECEIPT_SCHEMA,
            "event_schema": drill.EVENT_SCHEMA,
            "action": "check_acknowledgement",
            "event_id_sha256": event.event_id_sha256,
            "status": "acknowledged" if acknowledged else "unacknowledged",
            "checked_at_utc": drill.hardened._format_utc(checked_at),
            "acknowledged_at_utc": (
                drill.hardened._format_utc(acknowledged_at)
                if acknowledged_at
                else None
            ),
            "actor_role": actor_role if acknowledged else None,
            "actor_type": actor_type if acknowledged else None,
            "actor_id": actor_id if acknowledged else None,
            "synthetic": synthetic,
            "receipt_id": "ack-receipt-123",
        }
    )


class _Clock:
    def __init__(self, *values: datetime) -> None:
        self.values = list(values)
        self.last = values[-1]

    def __call__(self) -> datetime:
        if self.values:
            self.last = self.values.pop(0)
        return self.last


class AlertDeliveryDrillTests(unittest.TestCase):
    def test_configuration_is_all_or_nothing_before_provider_writes(self) -> None:
        env = {
            "CAS_ALERT_DRILL_INCIDENT_WEBHOOK_URL": "https://alerts.example.com/i",
            "CAS_ALERT_DRILL_INCIDENT_WEBHOOK_TOKEN": "i" * 20,
            "CAS_ALERT_DRILL_PRIMARY_WEBHOOK_URL": "https://alerts.example.com/p",
            "CAS_ALERT_DRILL_PRIMARY_WEBHOOK_TOKEN": "p" * 20,
            "CAS_ALERT_DRILL_ACK_WEBHOOK_URL": "https://alerts.example.com/a",
            "CAS_ALERT_DRILL_ACK_WEBHOOK_TOKEN": "a" * 20,
            "CAS_ALERT_DRILL_SECONDARY_WEBHOOK_URL": "https://alerts.example.com/s",
        }
        with self.assertRaisesRegex(
            drill.hardened.ConfigurationError,
            "drill_secondary_configuration_incomplete",
        ):
            drill.load_provider_config(drill.MODE_WEBHOOK_V1, env)

    def test_write_idempotency_is_clock_independent_but_ack_polling_is_not(self) -> None:
        event = _event()
        first = drill._request_payload(
            action="deliver",
            destination_role="primary_on_call",
            event=event,
            reason="non_disruptive_p1_drill",
        )
        second = drill._request_payload(
            action="deliver",
            destination_role="primary_on_call",
            event=event,
            reason="non_disruptive_p1_drill",
        )
        self.assertEqual(
            drill.hardened._idempotency_key(first),
            drill.hardened._idempotency_key(second),
        )
        self.assertNotIn("observation", first)

        ack_one = drill._request_payload(
            action="check_acknowledgement",
            destination_role="primary_on_call",
            event=event,
            observed_at=EMITTED + timedelta(seconds=30),
        )
        ack_two = drill._request_payload(
            action="check_acknowledgement",
            destination_role="primary_on_call",
            event=event,
            observed_at=EMITTED + timedelta(seconds=45),
        )
        self.assertNotEqual(
            drill.hardened._idempotency_key(ack_one),
            drill.hardened._idempotency_key(ack_two),
        )

    def test_success_is_secret_safe_open_and_distinct_from_runtime_incident(self) -> None:
        event = _event()
        calls: list[tuple[str, str]] = []

        def transport(endpoint, payload, idempotency_key):
            del idempotency_key
            calls.append((endpoint.url, str(payload["action"])))
            if endpoint.url.endswith("/incident"):
                return _delivery_response(
                    event,
                    action="deliver",
                    role="incident_channel",
                    delivered_at=EMITTED + timedelta(seconds=12),
                    receipt_id="raw-incident-receipt",
                )
            if endpoint.url.endswith("/primary"):
                return _delivery_response(
                    event,
                    action="deliver",
                    role="primary_on_call",
                    delivered_at=EMITTED + timedelta(seconds=22),
                    receipt_id="raw-primary-receipt",
                )
            if endpoint.url.endswith("/ack"):
                return _ack_response(
                    event,
                    checked_at=EMITTED + timedelta(seconds=60),
                    acknowledged_at=EMITTED + timedelta(seconds=30),
                )
            return _delivery_response(
                event,
                action="escalate",
                role="secondary_on_call",
                delivered_at=EMITTED + timedelta(seconds=72),
                receipt_id="raw-secondary-receipt",
            )

        clock = _Clock(
            EMITTED + timedelta(seconds=5),
            EMITTED + timedelta(seconds=10),
            EMITTED + timedelta(seconds=20),
            EMITTED + timedelta(seconds=60),
            EMITTED + timedelta(seconds=70),
            EMITTED + timedelta(seconds=75),
        )
        artifact, complete = drill.run_drill(
            config=_config(), event=event, transport=transport, clock=clock
        )

        self.assertTrue(complete)
        self.assertEqual(artifact["claim_status"], "OPEN")
        self.assertFalse(artifact["authority_published"])
        self.assertEqual(artifact["customer_production_status"], "OPEN")
        self.assertFalse(artifact["drill"]["runtime_outage"])
        self.assertFalse(artifact["drill"]["runtime_incident_mutated"])
        self.assertEqual(artifact["outcome"], "non_disruptive_drill_complete")
        self.assertEqual(len(calls), 4)
        serialized = json.dumps(artifact, sort_keys=True)
        for secret in (
            "token-for-",
            "alerts.example.com",
            "commander@example.com",
            "raw-primary-receipt",
            "raw-secondary-receipt",
        ):
            self.assertNotIn(secret, serialized)
        expected_receipts_hash = drill._canonical_sha256(
            {
                "deliveries": artifact["deliveries"],
                "acknowledgement": artifact["acknowledgement"],
                "secondary_escalation": artifact["secondary_escalation"],
            }
        )
        self.assertEqual(artifact["provider_receipts_sha256"], expected_receipts_hash)
        payload = builder.build_payload(
            artifact,
            artifact_sha256=hashlib.sha256(
                json.dumps(artifact, sort_keys=True, separators=(",", ":")).encode(
                    "ascii"
                )
            ).hexdigest(),
            master_head_sha="1" * 40,
            deploy_id="dep-d9b7ssh9rddc738q7om0",
        )
        self.assertEqual(payload["gate"], "alert_delivery")
        self.assertEqual(payload["alert"]["alert_id_sha256"], event.event_id_sha256)

    def test_acknowledgement_must_be_named_human_non_synthetic_and_timely(self) -> None:
        event = _event()
        observed = EMITTED + timedelta(seconds=100)
        request = drill._request_payload(
            action="check_acknowledgement",
            destination_role="primary_on_call",
            event=event,
            observed_at=observed,
        )
        cases = (
            {"synthetic": True},
            {"actor_type": "service"},
            {"actor_role": "operator"},
            {"actor_id": "   "},
            {"acknowledged_at": EMITTED + timedelta(seconds=601)},
        )
        for changes in cases:
            kwargs = {
                "checked_at": EMITTED + timedelta(seconds=100),
                "acknowledged_at": EMITTED + timedelta(seconds=30),
            }
            kwargs.update(changes)
            if changes.get("acknowledged_at"):
                kwargs["checked_at"] = changes["acknowledged_at"]
            response = _ack_response(event, **kwargs)
            with self.subTest(changes=changes):
                with self.assertRaises(drill.hardened.ProviderReceiptError):
                    drill._acknowledgement_receipt(
                        response,
                        request_payload=request,
                        event=event,
                        observed_at=observed,
                    )

    def test_stale_delivery_receipt_is_rejected(self) -> None:
        event = _event()
        observed = EMITTED + timedelta(minutes=10)
        response = _delivery_response(
            event,
            action="deliver",
            role="primary_on_call",
            delivered_at=EMITTED + timedelta(seconds=1),
            receipt_id="receipt-1",
        )
        with self.assertRaisesRegex(
            drill.hardened.ProviderReceiptError, "drill_delivery_time_stale"
        ):
            drill._delivery_receipt(
                response,
                request_payload=drill._request_payload(
                    action="deliver",
                    destination_role="primary_on_call",
                    event=event,
                    reason="non_disruptive_p1_drill",
                ),
                event=event,
                observed_at=observed,
                action="deliver",
                destination_role="primary_on_call",
            )

    def test_disabled_mode_performs_no_provider_calls(self) -> None:
        calls = []

        def transport(*args):
            calls.append(args)
            raise AssertionError("transport must not be called")

        artifact, complete = drill.run_drill(
            config=drill.DrillProviderConfig(mode=drill.MODE_DISABLED),
            event=_event(),
            transport=transport,
            clock=_Clock(EMITTED + timedelta(seconds=1)),
        )
        self.assertFalse(complete)
        self.assertEqual(calls, [])
        self.assertEqual(artifact["outcome"], "provider_disabled")
        self.assertIn("drill_provider_disabled", artifact["errors"])

    def test_partial_delivery_cannot_become_complete(self) -> None:
        event = _event()

        def transport(endpoint, payload, idempotency_key):
            del idempotency_key
            if endpoint.url.endswith("/incident"):
                raise drill.hardened.ProviderTransportError("provider_unreachable")
            if endpoint.url.endswith("/primary"):
                return _delivery_response(
                    event,
                    action="deliver",
                    role="primary_on_call",
                    delivered_at=EMITTED + timedelta(seconds=20),
                    receipt_id="primary-receipt",
                )
            self.assertEqual(payload["reason"], "drill_acknowledgement_unverified")
            return _delivery_response(
                event,
                action="escalate",
                role="secondary_on_call",
                delivered_at=EMITTED + timedelta(seconds=35),
                receipt_id="secondary-receipt",
            )

        artifact, complete = drill.run_drill(
            config=_config(),
            event=event,
            transport=transport,
            clock=_Clock(
                EMITTED + timedelta(seconds=5),
                EMITTED + timedelta(seconds=10),
                EMITTED + timedelta(seconds=20),
                EMITTED + timedelta(seconds=30),
                EMITTED + timedelta(seconds=40),
            ),
        )
        self.assertFalse(complete)
        self.assertEqual(artifact["outcome"], "non_disruptive_drill_incomplete")
        self.assertIn("provider_unreachable", artifact["errors"])
        self.assertEqual(
            artifact["secondary_escalation"]["trigger_reason"],
            "drill_acknowledgement_unverified",
        )

    def test_cli_rejects_noncanonical_or_stale_emission_time(self) -> None:
        args = argparse.Namespace(
            repository="LittleHenderson/noetic-compass",
            run_id=1,
            run_attempt=1,
            emitted_at_utc="2026-07-15T12:00:00.000Z",
        )
        with self.assertRaisesRegex(
            drill.hardened.ConfigurationError, "not_canonical"
        ):
            drill._event_from_args(args, now=EMITTED)

        args.emitted_at_utc = "2026-07-15T11:50:00Z"
        with self.assertRaisesRegex(drill.hardened.ConfigurationError, "stale"):
            drill._event_from_args(args, now=EMITTED)


if __name__ == "__main__":
    unittest.main()
