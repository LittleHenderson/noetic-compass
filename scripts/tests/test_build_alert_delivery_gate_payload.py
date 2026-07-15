from __future__ import annotations

import copy
from datetime import datetime, timezone
import hashlib
import importlib.util
from pathlib import Path
import sys
import unittest

from scripts import deliver_alert_delivery_drill as delivery


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "build_alert_delivery_gate_payload.py"
SPEC = importlib.util.spec_from_file_location("alert_delivery_gate_builder", MODULE_PATH)
assert SPEC and SPEC.loader
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)

VERIFIER_PATH = ROOT / "scripts" / "verify_customer_production_acceptance.py"
VERIFIER_SPEC = importlib.util.spec_from_file_location(
    "customer_production_acceptance_verifier_for_alert_builder", VERIFIER_PATH
)
assert VERIFIER_SPEC and VERIFIER_SPEC.loader
verifier = importlib.util.module_from_spec(VERIFIER_SPEC)
sys.modules[VERIFIER_SPEC.name] = verifier
VERIFIER_SPEC.loader.exec_module(verifier)


def _digest(seed: str) -> str:
    return hashlib.sha256(seed.encode("ascii")).hexdigest()


def _artifact() -> dict:
    drill = {
        "event_schema": builder.DRILL_EVENT_SCHEMA,
        "event_kind": builder.DRILL_KIND,
        "event_id_sha256": hashlib.sha256(
            f"{builder.REPOSITORY}:{builder.DRILL_KIND}:123:1".encode("utf-8")
        ).hexdigest(),
        "severity": "P1",
        "classification": "exercise",
        "runtime_outage": False,
        "runtime_incident_mutated": False,
        "emitted_at_utc": "2026-07-14T11:40:00Z",
        "observed_at_utc": "2026-07-14T11:52:00Z",
        "repository": builder.REPOSITORY,
        "run_id": 123,
        "run_attempt": 1,
    }
    incident = {
        "destination_role": "incident_channel",
        "status": "delivered",
        "requested_at_utc": "2026-07-14T11:40:30Z",
        "delivered_at_utc": "2026-07-14T11:41:00Z",
        "request_sha256": builder._expected_request_sha256(
            drill,
            action="deliver",
            destination_role="incident_channel",
            reason="non_disruptive_p1_drill",
        ),
        "receipt_id_sha256": _digest("incident-receipt"),
        "response_sha256": _digest("incident-response"),
    }
    primary = {
        "destination_role": "primary_on_call",
        "status": "delivered",
        "requested_at_utc": "2026-07-14T11:40:40Z",
        "delivered_at_utc": "2026-07-14T11:41:10Z",
        "request_sha256": builder._expected_request_sha256(
            drill,
            action="deliver",
            destination_role="primary_on_call",
            reason="non_disruptive_p1_drill",
        ),
        "receipt_id_sha256": _digest("primary-receipt"),
        "response_sha256": _digest("primary-response"),
    }
    acknowledgement = {
        "status": "acknowledged",
        "requested_at_utc": "2026-07-14T11:49:30Z",
        "checked_at_utc": "2026-07-14T11:50:00Z",
        "request_sha256": builder._expected_request_sha256(
            drill,
            action="check_acknowledgement",
            destination_role="primary_on_call",
            observed_at_utc="2026-07-14T11:49:30Z",
        ),
        "receipt_id_sha256": _digest("ack-receipt"),
        "response_sha256": _digest("ack-response"),
        "acknowledged_at_utc": "2026-07-14T11:43:00Z",
        "actor_role": "incident_commander",
        "actor_type": "human",
        "synthetic": False,
        "latency_seconds": 180,
    }
    secondary = {
        "destination_role": "secondary_on_call",
        "status": "delivered",
        "requested_at_utc": "2026-07-14T11:50:10Z",
        "delivered_at_utc": "2026-07-14T11:51:00Z",
        "request_sha256": builder._expected_request_sha256(
            drill,
            action="escalate",
            destination_role="secondary_on_call",
            reason="explicit_non_disruptive_drill",
        ),
        "receipt_id_sha256": _digest("secondary-receipt"),
        "response_sha256": _digest("secondary-response"),
        "trigger_reason": "explicit_non_disruptive_drill",
    }
    artifact = {
        "schema_version": builder.SAFE_ARTIFACT_SCHEMA,
        "claim_status": "OPEN",
        "authority_published": False,
        "customer_production_status": "OPEN",
        "provider_mode": "webhook_v1",
        "drill": drill,
        "deliveries": {
            "incident_channel": incident,
            "primary_on_call": primary,
        },
        "acknowledgement": acknowledgement,
        "secondary_escalation": secondary,
        "provider_receipts_sha256": "",
        "outcome": "non_disruptive_drill_complete",
        "errors": [],
    }
    artifact["provider_receipts_sha256"] = builder._canonical_sha256(
        {
            "deliveries": artifact["deliveries"],
            "acknowledgement": acknowledgement,
            "secondary_escalation": secondary,
        }
    )
    return artifact


def _build(artifact: dict) -> dict:
    return builder.build_payload(
        artifact,
        artifact_sha256=_digest("artifact-bytes"),
        master_head_sha="1" * 40,
        deploy_id="dep-d9b7ssh9rddc738q7om0",
    )


class AlertDeliveryGateBuilderTests(unittest.TestCase):
    def test_collector_and_builder_share_the_exact_drill_contract(self) -> None:
        self.assertEqual(builder.SAFE_ARTIFACT_SCHEMA, delivery.SAFE_ARTIFACT_SCHEMA)
        self.assertEqual(builder.DRILL_EVENT_SCHEMA, delivery.EVENT_SCHEMA)
        self.assertEqual(builder.DRILL_REQUEST_SCHEMA, delivery.REQUEST_SCHEMA)
        self.assertEqual(builder.DRILL_KIND, delivery.DRILL_KIND)
        artifact = _artifact()
        event = delivery.DrillEvent(
            repository=builder.REPOSITORY,
            run_id=artifact["drill"]["run_id"],
            run_attempt=artifact["drill"]["run_attempt"],
            emitted_at=datetime(2026, 7, 14, 11, 40, tzinfo=timezone.utc),
        )
        request = delivery._request_payload(
            action="deliver",
            destination_role="primary_on_call",
            event=event,
            reason="non_disruptive_p1_drill",
        )
        self.assertEqual(
            builder._expected_request_sha256(
                artifact["drill"],
                action="deliver",
                destination_role="primary_on_call",
                reason="non_disruptive_p1_drill",
            ),
            delivery._canonical_sha256(request),
        )

    def test_production_binding_matches_authoritative_acceptance_contract(self) -> None:
        self.assertEqual(builder.REPOSITORY, verifier.REPOSITORY)
        self.assertEqual(builder.PRODUCTION_API_ORIGIN, verifier.PRODUCTION_API_ORIGIN)
        self.assertEqual(builder.PRODUCTION_SERVICE_ID, verifier.PRODUCTION_SERVICE_ID)
        self.assertEqual(
            builder.AUTHORITY_URI,
            verifier.LIVE_AUTHORITY_ENDPOINTS["alert_delivery"][
                "noetic-production-live"
            ],
        )

    def test_builds_exact_gate_shape_from_non_disruptive_receipts(self) -> None:
        payload = _build(_artifact())

        self.assertEqual(payload["gate"], "alert_delivery")
        self.assertEqual(payload["artifact_uri"], builder.AUTHORITY_URI)
        self.assertEqual(payload["alert"]["source"], "cas-alert-delivery-drill")
        self.assertEqual(
            {delivery["destination_role"] for delivery in payload["deliveries"]},
            {"incident_channel", "primary_on_call"},
        )
        self.assertEqual(payload["acknowledgement"]["latency_seconds"], 180)
        self.assertTrue(payload["escalation"]["triggered"])
        self.assertTrue(payload["escalation"]["delivered"])
        self.assertNotIn("response_sha256", str(payload))
        self.assertNotIn("actor_id_sha256", str(payload))

        context = verifier.ValidationContext(
            repo_root=ROOT,
            evidence_root=ROOT,
            verification_time=datetime(2026, 7, 14, 12, 0, tzinfo=timezone.utc),
            generated_at=datetime(2026, 7, 14, 12, 0, tzinfo=timezone.utc),
            expected_master_head="1" * 40,
            expected_deploy_id="dep-d9b7ssh9rddc738q7om0",
            repository_commit="1" * 40,
            live=True,
            trusted_issuers={},
            registry_sha256="2" * 64,
            authorities={
                "alert_delivery": {
                    "mode": "live_https",
                    "subject_uri": builder.AUTHORITY_URI,
                }
            },
        )
        verifier._validate_alert_delivery(payload, context)
        self.assertEqual(context.errors, [])

    def test_rejects_runtime_incident_or_published_source_artifact(self) -> None:
        mutations = []
        runtime = copy.deepcopy(_artifact())
        runtime["drill"]["runtime_outage"] = True
        mutations.append(runtime)
        mutated = copy.deepcopy(_artifact())
        mutated["drill"]["runtime_incident_mutated"] = True
        mutations.append(mutated)
        published = copy.deepcopy(_artifact())
        published["authority_published"] = True
        mutations.append(published)
        accepted = copy.deepcopy(_artifact())
        accepted["customer_production_status"] = "ACCEPT"
        mutations.append(accepted)

        for artifact in mutations:
            with self.subTest(artifact=artifact):
                with self.assertRaises(builder.EvidenceError):
                    _build(artifact)

    def test_rejects_synthetic_wrong_actor_late_or_wrong_sequence(self) -> None:
        mutations = []
        for field, value in (
            ("synthetic", True),
            ("actor_type", "service"),
            ("actor_role", "operator"),
            ("latency_seconds", 181),
        ):
            artifact = copy.deepcopy(_artifact())
            artifact["acknowledgement"][field] = value
            mutations.append(artifact)
        early_secondary = copy.deepcopy(_artifact())
        early_secondary["secondary_escalation"]["requested_at_utc"] = (
            "2026-07-14T11:49:00Z"
        )
        mutations.append(early_secondary)
        after_observation = copy.deepcopy(_artifact())
        after_observation["secondary_escalation"]["delivered_at_utc"] = (
            "2026-07-14T11:53:00Z"
        )
        mutations.append(after_observation)

        for artifact in mutations:
            with self.subTest(artifact=artifact):
                with self.assertRaises(builder.EvidenceError):
                    _build(artifact)

    def test_rejects_unbound_event_request_or_receipt_set(self) -> None:
        mutations = []
        event = copy.deepcopy(_artifact())
        event["drill"]["event_id_sha256"] = _digest("other-event")
        mutations.append(event)
        request = copy.deepcopy(_artifact())
        request["deliveries"]["primary_on_call"]["request_sha256"] = _digest(
            "other-request"
        )
        request["provider_receipts_sha256"] = builder._canonical_sha256(
            {
                "deliveries": request["deliveries"],
                "acknowledgement": request["acknowledgement"],
                "secondary_escalation": request["secondary_escalation"],
            }
        )
        mutations.append(request)
        receipts = copy.deepcopy(_artifact())
        receipts["provider_receipts_sha256"] = _digest("other-receipt-set")
        mutations.append(receipts)

        for artifact in mutations:
            with self.subTest(artifact=artifact):
                with self.assertRaises(builder.EvidenceError):
                    _build(artifact)

    def test_rejects_duplicate_json_keys(self) -> None:
        with self.assertRaisesRegex(builder.EvidenceError, "duplicate key"):
            builder._json_object_without_duplicates(
                b'{"claim_status":"OPEN","claim_status":"ACCEPT"}'
            )


if __name__ == "__main__":
    unittest.main()
