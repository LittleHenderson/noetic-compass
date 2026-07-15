"""Keep the production route schema aligned with the canonical verifier fixtures."""

from __future__ import annotations

import sys
import unittest
import hashlib
import json
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = ROOT / "noetic-compass-scaffold" / "noetic-compass"
sys.path.insert(0, str(APP_ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from api.services.customer_production_acceptance_authority import (  # noqa: E402
    AcceptanceAuthorityInvalid,
    CustomerProductionAcceptanceAuthorityStore,
    canonicalize_acceptance_evidence,
)
from api import acceptance_authority_contract as authority_contract  # noqa: E402
from api.services import customer_production_acceptance_authority as authority_service  # noqa: E402
from api.services.production.state_substrate.memory_store import (  # noqa: E402
    InMemoryStateStore,
)
from scripts import verify_customer_production_acceptance as verifier  # noqa: E402
from scripts import build_alert_delivery_gate_payload as alert_builder  # noqa: E402
from scripts import collect_customer_readiness_facts as readiness_collector  # noqa: E402
from scripts import collect_hosted_customer_journey_evidence as journey_collector  # noqa: E402
from scripts import collect_airtable_crm_acceptance_source as crm_collector  # noqa: E402
from scripts import collect_operational_acceptance_draft as operational_collector  # noqa: E402
from scripts import collect_root_ci_protected_deploy_facts as root_ci_collector  # noqa: E402
from scripts import verify_production_runtime_readiness as runtime_verifier  # noqa: E402
from scripts import verify_render_blueprint_control as blueprint_verifier  # noqa: E402
from scripts.tests.test_verify_customer_production_acceptance import (  # noqa: E402
    DEPLOY_ID,
    MASTER_SHA,
    NOW,
    _common,
    _digest,
    _gate_payloads,
)


class AcceptanceAuthorityContractAlignmentTests(unittest.TestCase):
    def test_customer_provider_identity_is_aligned_across_active_contracts(self) -> None:
        origin = "https://cas-harness-customer-api.onrender.com"
        service_id = "srv-d9bijbjtqb8s73cn4n20"
        service_name = "cas-harness-customer-api"
        disk_id = "dsk-d9bijbjtqb8s73cn4o60"
        disk_name = "cas-harness-customer-support"
        disk_mount = "/var/customer-support"
        lead_path = f"{disk_mount}/leads.jsonl"

        for module in (
            verifier,
            authority_contract,
            authority_service,
            journey_collector,
            crm_collector,
            alert_builder,
            operational_collector,
        ):
            self.assertEqual(module.PRODUCTION_API_ORIGIN, origin)
        for module in (
            verifier,
            authority_service,
            journey_collector,
            crm_collector,
            alert_builder,
            operational_collector,
        ):
            self.assertEqual(module.PRODUCTION_SERVICE_ID, service_id)
        self.assertEqual(runtime_verifier.DEFAULT_API_BASE_URL, origin)
        self.assertEqual(readiness_collector.PRODUCTION_API_ORIGIN, origin)
        self.assertEqual(readiness_collector.PUBLIC_SERVICE_NAME, service_name)
        self.assertEqual(
            readiness_collector.RENDER_PATH.as_posix(), "render.customer.yaml"
        )
        self.assertEqual(root_ci_collector.PRODUCTION_HEALTH_URL, f"{origin}/health")
        self.assertTrue(root_ci_collector.RENDER_SERVICE_URL.endswith(service_id))

        for module in (verifier, authority_service):
            self.assertEqual(module.PRODUCTION_SERVICE_NAME, service_name)
            self.assertEqual(module.CRM_RENDER_DISK_ID, disk_id)
            self.assertEqual(module.CRM_RENDER_DISK_NAME, disk_name)
            self.assertEqual(module.CRM_RENDER_DISK_MOUNT_PATH, disk_mount)
            self.assertEqual(module.CRM_LEAD_STORE_PATH, lead_path)
        self.assertEqual(crm_collector.PRODUCTION_SERVICE_NAME, service_name)
        self.assertEqual(crm_collector.PRODUCTION_DISK_ID, disk_id)
        self.assertEqual(crm_collector.PRODUCTION_DISK_NAME, disk_name)
        self.assertEqual(crm_collector.PRODUCTION_DISK_MOUNT_PATH, disk_mount)
        self.assertEqual(crm_collector.PRODUCTION_LEAD_STORE_PATH, lead_path)

        customer = blueprint_verifier.EXPECTED_CUSTOMER_BLUEPRINT
        self.assertEqual(customer["id"], "exs-d9biqt37uimc73ajh99g")
        self.assertEqual(customer["project"]["id"], "prj-d9biitbtqb8s73cn3le0")
        self.assertEqual(
            customer["providerEnvironment"]["id"],
            "evm-d9biitbtqb8s73cn3leg",
        )
        self.assertEqual(customer["services"][0]["id"], service_id)
        self.assertEqual(customer["services"][0]["url"], origin)
        self.assertEqual(customer["services"][0]["disk"]["id"], disk_id)
        self.assertEqual(
            customer["databases"][0]["id"], "dpg-d9biitbtqb8s73cn3mgg-a"
        )
        self.assertEqual(blueprint_verifier.EXPECTED_PENDING_BLUEPRINTS, [])

        route_contract = json.loads(
            (
                APP_ROOT / "atlas-viewer" / "render-route-rules.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(route_contract["requiredApiBaseUrl"], f"{origin}/atlas")
        self.assertEqual(route_contract["requiredAccountsEnabled"], "true")

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

        def rebind_source(payload: dict, field: str, value: object) -> None:
            payload["crm_source_receipt"][field] = value
            canonical = json.dumps(
                payload["crm_source_receipt"],
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
            payload["crm_lead"]["source_receipt_sha256"] = hashlib.sha256(
                canonical
            ).hexdigest()

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
            lambda payload: rebind_source(
                payload, "airtable_owner_value", "Other Owner"
            ),
            lambda payload: rebind_source(
                payload, "lead_store_path", "/tmp/leads.jsonl"
            ),
            lambda payload: rebind_source(
                payload, "render_deploy_status", "deactivated"
            ),
        )
        for mutate in cases:
            payload = deepcopy(support)
            mutate(payload)
            with self.assertRaises(AcceptanceAuthorityInvalid):
                canonicalize_acceptance_evidence("support_crm", payload, now=NOW)


if __name__ == "__main__":
    unittest.main()
