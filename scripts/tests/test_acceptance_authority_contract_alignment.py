"""Keep the production route schema aligned with the canonical verifier fixtures."""

from __future__ import annotations

import sys
import unittest
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = ROOT / "noetic-compass-scaffold" / "noetic-compass"
sys.path.insert(0, str(APP_ROOT))

from api.services.customer_production_acceptance_authority import (  # noqa: E402
    AcceptanceAuthorityInvalid,
    CustomerProductionAcceptanceAuthorityStore,
    canonicalize_acceptance_evidence,
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
                expected_previous_sha256=None,
                authorization_artifact_uri=(
                    f"{verifier.PRODUCTION_API_ORIGIN}/internal/"
                    "acceptance-authorizations/alignment-test"
                ),
                authorization_artifact_sha256=_digest(
                    "alignment-test-authorization"
                ),
                operation_reason="authorized_publication",
                now=NOW,
            )
            loaded = store.load(gate, now=NOW)
            self.assertEqual(loaded.sha256, published.sha256)
            self.assertEqual(loaded.gate, gate)

    def test_live_route_rejects_verifier_forbidden_origins_and_private_canary_case(self) -> None:
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
        for gate, payload in payloads.items():
            if gate == "root_ci_protected_deploy":
                continue
            payload["master_head_sha"] = MASTER_SHA
            payload["deploy_id"] = DEPLOY_ID
            payload["artifact_uri"] = verifier.LIVE_AUTHORITY_ENDPOINTS[gate][
                "noetic-production-live"
            ]
            payload["artifact_sha256"] = _digest(f"live-authority-{gate}")

        cases: list[tuple[str, dict]] = []
        legal = deepcopy(payloads["legal_publication_approval"])
        legal["approvals"][0]["approval_artifact_uri"] = (  # type: ignore[index]
            "https://atlas.noeticcompass.com/approvals/legal"
        )
        cases.append(("legal_publication_approval", legal))

        incident = deepcopy(payloads["incident_tabletop"])
        incident["incident"]["postmortem_uri"] = (  # type: ignore[index]
            "https://cascompass.ai/postmortems/incident"
        )
        cases.append(("incident_tabletop", incident))

        tabletop = deepcopy(payloads["incident_tabletop"])
        tabletop["tabletop"]["evidence_uri"] = (  # type: ignore[index]
            "https://atlas.noeticcompass.com/tabletops/proof"
        )
        cases.append(("incident_tabletop", tabletop))

        claim = deepcopy(payloads["claim_honesty"])
        claim["approvals"][0]["approval_artifact_uri"] = (  # type: ignore[index]
            "https://atlas.noeticcompass.com/approvals/claim"
        )
        cases.append(("claim_honesty", claim))

        decision = deepcopy(payloads["release_decision"])
        decision["decision_record_uri"] = "https://cascompass.ai/release/decision"
        cases.append(("release_decision", decision))

        mixed_case_canary = deepcopy(payloads["legal_publication_approval"])
        mixed_case_canary["approvals"][0]["approval_artifact_uri"] = (  # type: ignore[index]
            f"{verifier.PRODUCTION_API_ORIGIN}/approvals/ACCOUNTS-CANARY"
        )
        cases.append(("legal_publication_approval", mixed_case_canary))

        for gate, payload in cases:
            with self.subTest(gate=gate):
                with self.assertRaises(AcceptanceAuthorityInvalid):
                    canonicalize_acceptance_evidence(gate, payload, now=NOW)

    def test_support_crm_runtime_rejects_unbound_provider_and_consent_evidence(self) -> None:
        support = _gate_payloads()["support_crm"]
        support["master_head_sha"] = MASTER_SHA
        support["deploy_id"] = DEPLOY_ID
        support["artifact_uri"] = verifier.LIVE_AUTHORITY_ENDPOINTS["support_crm"][
            "noetic-production-live"
        ]
        support["artifact_sha256"] = _digest("live-authority-support-crm")
        cases = (
            lambda payload: payload["crm_lead"].update(provider="hubspot"),
            lambda payload: payload["crm_lead"].update(
                adapter_response_digest=_digest("unprefixed")
            ),
            lambda payload: payload["crm_lead"].update(
                airtable_record_id_sha256=""
            ),
            lambda payload: payload["consent"].update(consent_to_contact=False),
            lambda payload: payload["consent"].update(
                privacy_notice_version="privacy version with spaces"
            ),
            lambda payload: payload["consent"].update(
                recorded_at_utc="2026-07-14T11:46:00Z"
            ),
        )
        for mutate in cases:
            payload = deepcopy(support)
            mutate(payload)
            with self.assertRaises(AcceptanceAuthorityInvalid):
                canonicalize_acceptance_evidence("support_crm", payload, now=NOW)


if __name__ == "__main__":
    unittest.main()
