from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "build_alert_delivery_gate_payload.py"
SPEC = importlib.util.spec_from_file_location("alert_delivery_gate_builder", MODULE_PATH)
assert SPEC and SPEC.loader
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


def _digest(seed: str) -> str:
    import hashlib

    return hashlib.sha256(seed.encode("ascii")).hexdigest()


def _artifact() -> dict:
    return {
        "schema_version": builder.SAFE_ARTIFACT_SCHEMA,
        "claim_status": "OPEN",
        "provider_mode": "webhook_v1",
        "lifecycle": "failing",
        "provider_obligation_required": True,
        "secondary_drill_requested": True,
        "provider_obligation_satisfied": True,
        "event": {
            "event_id_sha256": _digest("event"),
            "severity": "P1",
            "emitted_at_utc": "2026-07-14T11:40:00Z",
            "observed_at_utc": "2026-07-14T11:55:00Z",
            "run_id": 123,
            "issue_number": 154,
            "normalized_results": {
                "api": "failure",
                "worker": "success",
                "blueprint": "success",
                "aggregate": "failure",
            },
        },
        "incident_channel": {
            "destination_role": "incident_channel",
            "provider": "github",
            "status": "present",
            "issue_url_sha256": _digest("issue-url"),
        },
        "primary_on_call": {
            "destination_role": "primary_on_call",
            "status": "delivered",
            "delivered_at_utc": "2026-07-14T11:41:00Z",
            "receipt_id_sha256": _digest("primary-receipt"),
            "response_sha256": _digest("primary-response"),
        },
        "acknowledgement": {
            "status": "acknowledged",
            "checked_at_utc": "2026-07-14T11:50:00Z",
            "receipt_id_sha256": _digest("ack-receipt"),
            "response_sha256": _digest("ack-response"),
            "acknowledged_at_utc": "2026-07-14T11:43:00Z",
            "actor_role": "incident_commander",
            "latency_seconds": 180,
        },
        "secondary_escalation": {
            "destination_role": "secondary_on_call",
            "status": "delivered",
            "delivered_at_utc": "2026-07-14T11:51:00Z",
            "receipt_id_sha256": _digest("secondary-receipt"),
            "response_sha256": _digest("secondary-response"),
            "trigger_reason": "explicit_secondary_escalation_drill",
        },
        "outcome": "primary_delivered_acknowledged_secondary_drill_escalated",
        "errors": [],
    }


class AlertDeliveryGateBuilderTests(unittest.TestCase):
    def test_builds_exact_gate_shape_from_independent_receipts(self) -> None:
        payload = builder.build_payload(
            _artifact(),
            artifact_sha256=_digest("artifact-bytes"),
            master_head_sha="1" * 40,
            deploy_id="dep-d9b7ssh9rddc738q7om0",
        )

        self.assertEqual(payload["gate"], "alert_delivery")
        self.assertEqual(payload["artifact_uri"], builder.AUTHORITY_URI)
        self.assertEqual(
            {delivery["destination_role"] for delivery in payload["deliveries"]},
            {"incident_channel", "primary_on_call"},
        )
        self.assertEqual(payload["acknowledgement"]["latency_seconds"], 180)
        self.assertTrue(payload["escalation"]["triggered"])
        self.assertTrue(payload["escalation"]["delivered"])
        self.assertNotIn("response_sha256", str(payload))

    def test_rejects_normal_ack_suppression_artifact(self) -> None:
        artifact = _artifact()
        artifact["secondary_drill_requested"] = False
        artifact["secondary_escalation"] = {
            "status": "not_triggered",
            "reason": "acknowledgement_verified_within_600_seconds",
        }
        artifact["outcome"] = "primary_delivered_acknowledgement_verified"

        with self.assertRaisesRegex(builder.EvidenceError, "secondary_drill_requested"):
            builder.build_payload(
                artifact,
                artifact_sha256=_digest("artifact-bytes"),
                master_head_sha="1" * 40,
                deploy_id="dep-d9b7ssh9rddc738q7om0",
            )

    def test_rejects_wrong_actor_latency_or_secondary_reason(self) -> None:
        mutations = []
        wrong_actor = copy.deepcopy(_artifact())
        wrong_actor["acknowledgement"]["actor_role"] = "operator"
        mutations.append(wrong_actor)
        wrong_latency = copy.deepcopy(_artifact())
        wrong_latency["acknowledgement"]["latency_seconds"] = 181
        mutations.append(wrong_latency)
        wrong_reason = copy.deepcopy(_artifact())
        wrong_reason["secondary_escalation"]["trigger_reason"] = (
            "unacknowledged_after_600_seconds"
        )
        mutations.append(wrong_reason)

        for artifact in mutations:
            with self.subTest(artifact=artifact):
                with self.assertRaises(builder.EvidenceError):
                    builder.build_payload(
                        artifact,
                        artifact_sha256=_digest("artifact-bytes"),
                        master_head_sha="1" * 40,
                        deploy_id="dep-d9b7ssh9rddc738q7om0",
                    )


if __name__ == "__main__":
    unittest.main()
