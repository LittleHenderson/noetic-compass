"""Keep the production route schema aligned with the canonical verifier fixtures."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = ROOT / "noetic-compass-scaffold" / "noetic-compass"
sys.path.insert(0, str(APP_ROOT))

from api.services.customer_production_acceptance_authority import (  # noqa: E402
    CustomerProductionAcceptanceAuthorityStore,
)
from api.services.production.state_substrate.memory_store import (  # noqa: E402
    InMemoryStateStore,
)
from scripts import verify_customer_production_acceptance as verifier  # noqa: E402
from scripts.tests.test_verify_customer_production_acceptance import (  # noqa: E402
    DEPLOY_ID,
    MASTER_SHA,
    NOW,
    _common,
    _digest,
    _gate_payloads,
)


class AcceptanceAuthorityContractAlignmentTests(unittest.TestCase):
    def test_every_live_route_accepts_the_verifiers_exact_gate_shape(self) -> None:
        payloads = _gate_payloads()
        release = _common(
            "release_decision",
            event="2026-07-14T11:56:00Z",
            observed="2026-07-14T11:58:00Z",
        )
        release.update(
            {
                "status": "ACCEPT",
                "approved_at_utc": "2026-07-14T11:56:00Z",
                "approver_roles": sorted(verifier.RELEASE_APPROVER_ROLES),
                "decision_record_uri": (
                    f"{verifier.PRODUCTION_API_ORIGIN}/internal/acceptance/release-record"
                ),
                "decision_record_sha256": _digest("release-record"),
            }
        )
        payloads["release_decision"] = release

        live_gates = {
            gate
            for gate, issuers in verifier.LIVE_AUTHORITY_ENDPOINTS.items()
            if issuers
        }
        self.assertEqual(
            live_gates,
            set(payloads) - {"root_ci_protected_deploy"},
        )

        for gate in sorted(live_gates):
            endpoint = verifier.LIVE_AUTHORITY_ENDPOINTS[gate][
                "noetic-production-live"
            ]
            payload = payloads[gate]
            payload["master_head_sha"] = MASTER_SHA
            payload["deploy_id"] = DEPLOY_ID
            payload["artifact_uri"] = endpoint
            payload["artifact_sha256"] = _digest(f"live-authority-{gate}")
            store = CustomerProductionAcceptanceAuthorityStore(InMemoryStateStore())
            published = store.publish(
                gate,
                payload,
                expected_head_version=0,
                now=NOW,
            )
            loaded = store.load(gate, now=NOW)
            self.assertEqual(loaded.sha256, published.sha256)
            self.assertEqual(loaded.gate, gate)


if __name__ == "__main__":
    unittest.main()
