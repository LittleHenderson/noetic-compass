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
from api.services.acceptance_publication_authorizations import (  # noqa: E402
    AcceptancePublicationAuthorizationStore,
)
from api import acceptance_authority_contract as authority_contract  # noqa: E402
from api.services import customer_production_acceptance_authority as authority_service  # noqa: E402
from api.services.production.state_substrate.memory_store import (  # noqa: E402
    InMemoryStateStore,
)
from scripts import verify_customer_production_acceptance as verifier  # noqa: E402
from scripts import build_alert_delivery_gate_payload as alert_builder  # noqa: E402
from scripts import collect_customer_readiness_facts as readiness_collector  # noqa: E402
from scripts import collect_claim_honesty_evidence as claim_collector  # noqa: E402
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
    def test_claim_machine_subject_contract_is_exact_across_all_layers(self) -> None:
        self.assertEqual(
            claim_collector.MACHINE_SUBJECT_SCHEMA_VERSION,
            verifier.CLAIM_MACHINE_SUBJECT_SCHEMA_VERSION,
        )
        self.assertEqual(
            claim_collector.MACHINE_SUBJECT_SCHEMA_VERSION,
            authority_service.CLAIM_MACHINE_SUBJECT_SCHEMA_VERSION,
        )
        self.assertEqual(
            claim_collector.RULESET_VERSION,
            verifier.CLAIM_MACHINE_RULESET_VERSION,
        )
        self.assertEqual(
            claim_collector.RULESET_VERSION,
            authority_service.CLAIM_MACHINE_RULESET_VERSION,
        )
        claim = _gate_payloads()["claim_honesty"]
        self.assertNotIn("rendered_product_status", claim["boundaries"])
        self.assertEqual(
            claim["machine_subject_sha256"],
            claim_collector.machine_subject_sha256(claim["machine_subject"]),
        )

    def test_claim_charset_contract_is_exact_across_all_layers(self) -> None:
        for content_type in (
            "text/html",
            "text/html; charset=",
            "text/html; charset=utf-8; charset=iso-8859-1",
        ):
            with self.subTest(content_type=content_type):
                decoded, error = claim_collector._decode_html(
                    b"<html></html>", content_type
                )
                self.assertIsNone(decoded)
                self.assertEqual(error, "unsupported_charset")
                self.assertFalse(
                    authority_service._claim_html_content_type_is_supported(
                        content_type
                    )
                )
                self.assertFalse(
                    verifier._claim_html_content_type_is_supported(content_type)
                )

        accepted = "Text/HTML; Charset=\"UTF-8\""
        decoded, error = claim_collector._decode_html(
            b"<html></html>", accepted
        )
        self.assertEqual(decoded, "<html></html>")
        self.assertIsNone(error)
        self.assertTrue(
            authority_service._claim_html_content_type_is_supported(accepted)
        )
        self.assertTrue(verifier._claim_html_content_type_is_supported(accepted))

    def test_claim_authority_rejects_circular_status_and_machine_subject_tamper(self) -> None:
        base = _gate_payloads()["claim_honesty"]
        base["master_head_sha"] = MASTER_SHA
        base["deploy_id"] = DEPLOY_ID
        base["artifact_uri"] = verifier.LIVE_AUTHORITY_ENDPOINTS["claim_honesty"][
            "noetic-production-live"
        ]
        base["artifact_sha256"] = base["machine_subject_sha256"]
        canonicalize_acceptance_evidence("claim_honesty", base, now=NOW)

        circular = deepcopy(base)
        circular["boundaries"]["rendered_product_status"] = "ACCEPT"
        with self.assertRaises(AcceptanceAuthorityInvalid):
            canonicalize_acceptance_evidence("claim_honesty", circular, now=NOW)

        tampered = deepcopy(base)
        tampered["machine_subject"]["scanned_surfaces"][0][
            "content_sha256"
        ] = "f" * 64
        with self.assertRaises(AcceptanceAuthorityInvalid):
            canonicalize_acceptance_evidence("claim_honesty", tampered, now=NOW)

        finding = deepcopy(base)
        finding["machine_subject"]["findings"].append(
            {
                "category": "misleading_claim",
                "rule_id": "customer_production_ready",
                "surface_kind": "landing",
                "match_start": 0,
                "match_end": 10,
                "match_sha256": "a" * 64,
            }
        )
        finding["machine_subject_sha256"] = claim_collector.machine_subject_sha256(
            finding["machine_subject"]
        )
        with self.assertRaises(AcceptanceAuthorityInvalid):
            canonicalize_acceptance_evidence("claim_honesty", finding, now=NOW)

    def test_claim_authority_enforces_exact_machine_to_human_chronology(self) -> None:
        def bound_claim() -> dict:
            claim = _gate_payloads()["claim_honesty"]
            claim["artifact_uri"] = verifier.LIVE_AUTHORITY_ENDPOINTS[
                "claim_honesty"
            ]["noetic-production-live"]
            claim["artifact_sha256"] = claim["machine_subject_sha256"]
            return claim

        canonicalize_acceptance_evidence(
            "claim_honesty", bound_claim(), now=NOW
        )

        surface_after_generation = bound_claim()
        surface_after_generation["machine_subject"]["scanned_surfaces"][0][
            "verified_at_utc"
        ] = "2026-07-14T11:49:00Z"
        digest = claim_collector.machine_subject_sha256(
            surface_after_generation["machine_subject"]
        )
        surface_after_generation["machine_subject_sha256"] = digest
        surface_after_generation["artifact_sha256"] = digest
        with self.assertRaises(AcceptanceAuthorityInvalid):
            canonicalize_acceptance_evidence(
                "claim_honesty", surface_after_generation, now=NOW
            )

        approval_before_generation = bound_claim()
        approval_before_generation["approvals"][0]["approved_at_utc"] = (
            "2026-07-14T11:47:00Z"
        )
        with self.assertRaises(AcceptanceAuthorityInvalid):
            canonicalize_acceptance_evidence(
                "claim_honesty", approval_before_generation, now=NOW
            )

        artifact_mismatch = bound_claim()
        artifact_mismatch["artifact_sha256"] = "f" * 64
        with self.assertRaises(AcceptanceAuthorityInvalid):
            canonicalize_acceptance_evidence(
                "claim_honesty", artifact_mismatch, now=NOW
            )

    def test_claim_authority_enforces_collector_charset_types_and_lengths(self) -> None:
        def bound_claim() -> dict:
            claim = _gate_payloads()["claim_honesty"]
            claim["artifact_uri"] = verifier.LIVE_AUTHORITY_ENDPOINTS[
                "claim_honesty"
            ]["noetic-production-live"]
            return claim

        def mutate_and_rebind(mutator) -> dict:
            claim = bound_claim()
            static_surface = next(
                surface
                for surface in claim["machine_subject"]["scanned_surfaces"]
                if surface["kind"] == "landing"
            )
            mutator(claim, static_surface)
            digest = claim_collector.machine_subject_sha256(
                claim["machine_subject"]
            )
            claim["machine_subject_sha256"] = digest
            claim["artifact_sha256"] = digest
            return claim

        cases = {
            "missing charset": lambda _claim, surface: surface.update(
                content_type="text/html"
            ),
            "empty charset": lambda _claim, surface: surface.update(
                content_type="text/html; charset="
            ),
            "conflicting duplicate charset": lambda _claim, surface: surface.update(
                content_type="text/html; charset=utf-8; charset=iso-8859-1"
            ),
            "non-UTF-8 declared charset": lambda _claim, surface: surface.update(
                content_type="text/html; charset=iso-8859-1"
            ),
            "static prerender marker null": lambda _claim, surface: surface.update(
                prerender_contract_matches_requested_route=None
            ),
            "static prerender marker integer": lambda _claim, surface: surface.update(
                prerender_contract_matches_requested_route=0
            ),
            "boolean word count": lambda _claim, surface: surface.update(
                visible_word_count=True
            ),
            "words exceed characters": lambda _claim, surface: surface.update(
                visible_word_count=257
            ),
            "characters exceed bytes": lambda _claim, surface: surface.update(
                visible_text_characters=513
            ),
            "bytes exceed scanner maximum": lambda claim, surface: (
                claim["machine_subject"]["scanner"].update(
                    maximum_response_bytes=511
                ),
                surface.update(byte_length=512),
            ),
        }
        for label, mutator in cases.items():
            with self.subTest(label=label):
                with self.assertRaises(AcceptanceAuthorityInvalid):
                    canonicalize_acceptance_evidence(
                        "claim_honesty",
                        mutate_and_rebind(mutator),
                        now=NOW,
                    )

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
            payload["artifact_sha256"] = (
                payload["machine_subject_sha256"]
                if gate == "claim_honesty"
                else _digest(f"live-authority-{gate}")
            )
            backend = InMemoryStateStore()
            authorization_store = AcceptancePublicationAuthorizationStore(
                backend, primary_tenant_id="primary"
            )
            evidence_sha256 = hashlib.sha256(
                canonicalize_acceptance_evidence(gate, payload, now=NOW)
            ).hexdigest()
            authorization = authorization_store.create(
                actor_tenant_id="primary",
                actor_account_id="acct-" + "a" * 32,
                actor_role="owner",
                gate=gate,
                master_head_sha=MASTER_SHA,
                deploy_id=DEPLOY_ID,
                evidence_sha256=evidence_sha256,
                expected_head_version=0,
                expected_previous_evidence_sha256=None,
                reason="authorized_publication",
                now=NOW,
            )
            store = CustomerProductionAcceptanceAuthorityStore(
                backend,
                publication_authorization_store=authorization_store,
            )
            published = store.publish(
                gate,
                payload,
                expected_head_version=0,
                expected_previous_sha256=None,
                authorization_artifact_uri=authorization.uri,
                authorization_artifact_sha256=authorization.sha256,
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
            payload["artifact_sha256"] = (
                payload["machine_subject_sha256"]
                if gate == "claim_honesty"
                else _digest(f"live-authority-{gate}")
            )

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
