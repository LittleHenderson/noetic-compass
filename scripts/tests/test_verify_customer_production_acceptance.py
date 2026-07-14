from __future__ import annotations

import base64
import copy
import hashlib
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from scripts import verify_customer_production_acceptance as verifier


ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / verifier.DEFAULT_MANIFEST
NOW = datetime(2026, 7, 14, 12, 0, 0, tzinfo=timezone.utc)
GENERATED = "2026-07-14T12:00:00Z"
EVENT = "2026-07-14T11:30:00Z"
OBSERVED = "2026-07-14T11:50:00Z"
ISSUED = "2026-07-14T11:55:00Z"
EXPIRES = "2026-07-15T12:00:00Z"
MASTER_SHA = "a" * 40
DEPLOY_ID = "dep-publicacceptance001"
TEST_ISSUER = "customer-production-test-issuer"
TEST_KEY_ID = "test-rs256-2026"

# Test-only RSA-2048 key. The private exponent never appears in production
# configuration or evidence; it exists solely to exercise signature checks.
RSA_N = 25760228789150642169916057451538058318920739210407384024217329640306040111734935426879868020512449142562284384088410137468738262304165883924278774077605468942153022885189482684928051866484899960798041188519979062770148484630024868272532192357343527736355621196774917648414530129944413368339663552119072520219782671763421789156139577562948849412029277776560469279696675118427050507984570807586812023426671574666066647840374542353361555341460227285823878961714171062976845327002993641388897390645204311991458755540039531645268510963437277410341867291546780766819997569325046926602147425171558745491706788093278145819061
RSA_E = 65537
RSA_D = 869948675825681047081293226034402056462018799417644119987167627850028888678110774578358299836720906736286005051858854338048506325353542923774509006015843022051973357044808620358225289431888930500881405320534105324870395861992501025438788390296940091284146033748296175982322334102865143163064533877466732614793469895664641260228453535216845439592859761491108425798445473388501954128632620544434103716302271794600306053657591624246633785807469025223213684029980322034475137648243279230230462672972154220588656216429020479616453736685632987882679157638522820905306154521994643849814313550757305047314447821385533552425


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _canonical(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sign(value: dict) -> str:
    digest_info = verifier.RSA_SHA256_DIGEST_INFO_PREFIX + hashlib.sha256(_canonical(value)).digest()
    key_size = (RSA_N.bit_length() + 7) // 8
    padding_size = key_size - len(digest_info) - 3
    encoded = b"\x00\x01" + (b"\xff" * padding_size) + b"\x00" + digest_info
    signature = pow(int.from_bytes(encoded, "big"), RSA_D, RSA_N).to_bytes(key_size, "big")
    return base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")


def _checked_in_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


SUBJECT_URIS = {
    "runtime_worm": f"{verifier.PRODUCTION_API_ORIGIN}/internal/acceptance/runtime-worm",
    "root_ci_protected_deploy": f"{verifier.GITHUB_API_ORIGIN}/repos/{verifier.REPOSITORY}/actions/runs/30000000001",
    "hosted_customer_journey": f"{verifier.PRODUCTION_API_ORIGIN}/internal/acceptance/customer-journey",
    "accounts_billing": f"{verifier.PRODUCTION_API_ORIGIN}/internal/acceptance/accounts-billing",
    "legal_publication_approval": (
        f"{verifier.PRODUCTION_API_ORIGIN}/internal/acceptance/"
        "legal-publication-approval"
    ),
    "support_crm": f"{verifier.PRODUCTION_API_ORIGIN}/internal/acceptance/support-crm",
    "incident_tabletop": f"{verifier.PRODUCTION_API_ORIGIN}/internal/acceptance/incident-tabletop",
    "alert_delivery": f"{verifier.PRODUCTION_API_ORIGIN}/internal/acceptance/alert-delivery",
    "claim_honesty": f"{verifier.PRODUCTION_API_ORIGIN}/internal/acceptance/claim-honesty",
    "release_decision": f"{verifier.PRODUCTION_API_ORIGIN}/internal/acceptance/release-decision",
}

CRITICAL_TIMESTAMP_PATHS: dict[str, list[tuple[str | int, ...]]] = {
    "runtime_worm": [
        ("deployment", "deployed_at_utc"),
        ("readiness", "verified_at_utc"),
        ("worker", "verified_at_utc"),
        ("worm", "written_at_utc"),
        ("worm", "verified_at_utc"),
    ],
    "root_ci_protected_deploy": [
        ("branch_protection", "observed_at_utc"),
        ("checks", 0, "completed_at_utc"),
        ("checks", 1, "completed_at_utc"),
        ("checks", 2, "completed_at_utc"),
        ("deployment", "deployed_at_utc"),
    ],
    "hosted_customer_journey": [
        ("audit", "completed_at_utc"),
        ("packet_download", "downloaded_at_utc"),
        ("share", "created_at_utc"),
        ("share", "fetched_at_utc"),
        ("share", "revoked_at_utc"),
        ("tenant_isolation", "verified_at_utc"),
    ],
    "accounts_billing": [
        ("account_session", "verified_at_utc"),
        ("quota", "verified_at_utc"),
        ("billing", "paid_at_utc"),
    ],
    "legal_publication_approval": [
        *(("documents", index, field) for index in range(3) for field in ("published_at_utc", "verified_at_utc")),
        *(("approvals", index, "approved_at_utc") for index in range(3)),
    ],
    "support_crm": [
        ("support_ticket", "resolved_at_utc"),
        ("crm_lead", "verified_at_utc"),
        ("consent", "recorded_at_utc"),
    ],
    "incident_tabletop": [
        ("incident", "closed_at_utc"),
        ("tabletop", "completed_at_utc"),
    ],
    "alert_delivery": [
        ("alert", "emitted_at_utc"),
        ("deliveries", 0, "delivered_at_utc"),
        ("deliveries", 1, "delivered_at_utc"),
        ("acknowledgement", "acknowledged_at_utc"),
        ("escalation", "delivered_at_utc"),
    ],
    "claim_honesty": [
        *(("scanned_surfaces", index, "verified_at_utc") for index in range(6)),
        *(("approvals", index, "approved_at_utc") for index in range(3)),
    ],
}


def _set_nested(value: dict, path: tuple[str | int, ...], replacement: object) -> None:
    current: object = value
    for part in path[:-1]:
        current = current[part]  # type: ignore[index]
    current[path[-1]] = replacement  # type: ignore[index]


class SignedBundle:
    def __init__(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.root = Path(self._temporary.name)
        self.counter = 0
        self.trusted_issuers = {
            (TEST_ISSUER, TEST_KEY_ID): {
                "n": RSA_N,
                "e": RSA_E,
                "allowed_subjects": frozenset(SUBJECT_URIS.items()),
                "valid_from": datetime(2026, 1, 1, tzinfo=timezone.utc),
                "valid_until": datetime(2027, 1, 1, tzinfo=timezone.utc),
            }
        }

    def close(self) -> None:
        self._temporary.cleanup()

    def receipt(
        self,
        gate: str,
        evidence: dict,
        *,
        issued: str = ISSUED,
        expires: str = EXPIRES,
        issuer: str = TEST_ISSUER,
        key_id: str = TEST_KEY_ID,
        subject_uri: str | None = None,
        sign: bool = True,
    ) -> dict:
        self.counter += 1
        subject_uri = subject_uri or SUBJECT_URIS[gate]
        subject_hash = _digest(f"subject-{gate}-{self.counter}")
        evidence["artifact_uri"] = subject_uri
        evidence["artifact_sha256"] = subject_hash
        unsigned = {
            "schema_version": verifier.RECEIPT_SCHEMA_VERSION,
            "issuer": issuer,
            "key_id": key_id,
            "gate": gate,
            "environment": "public-production",
            "repository": verifier.REPOSITORY,
            "master_head_sha": MASTER_SHA,
            "deploy_id": DEPLOY_ID,
            "issued_at_utc": issued,
            "expires_at_utc": expires,
            "subject_uri": subject_uri,
            "subject_sha256": subject_hash,
            "evidence": evidence,
        }
        document = dict(unsigned)
        document["signature_base64url"] = _sign(unsigned) if sign else "invalid-signature"
        filename = f"{gate}-{self.counter}.json"
        raw = json.dumps(document, indent=2, sort_keys=True).encode("utf-8") + b"\n"
        (self.root / filename).write_bytes(raw)
        return {
            "uri": f"repo://{filename}",
            "sha256": hashlib.sha256(raw).hexdigest(),
            "authority": {
                "mode": "signed_receipt",
                "issuer": issuer,
                "key_id": key_id,
            },
        }


def _common(gate: str, *, event: str = EVENT, observed: str = OBSERVED) -> dict:
    return {
        "schema_version": verifier.EVIDENCE_SCHEMA_VERSION,
        "gate": gate,
        "environment": "public-production",
        "repository": verifier.REPOSITORY,
        "master_head_sha": MASTER_SHA,
        "deploy_id": DEPLOY_ID,
        "event_at_utc": event,
        "observed_at_utc": observed,
        "artifact_uri": "filled-by-signed-receipt",
        "artifact_sha256": "0" * 64,
    }


def _approval(role: str, prefix: str) -> dict:
    return {
        "role": role,
        "approval_artifact_uri": f"{verifier.PRODUCTION_API_ORIGIN}/internal/approvals/{prefix}-{role}",
        "approval_sha256": _digest(f"{prefix}-{role}"),
        "approved_at_utc": "2026-07-14T11:45:00Z",
    }


def _gate_payloads() -> dict[str, dict]:
    runtime = _common("runtime_worm")
    runtime.update(
        {
            "api_base_url": verifier.PRODUCTION_API_ORIGIN,
            "deployment": {
                "service_id": verifier.PRODUCTION_SERVICE_ID,
                "service_name": verifier.PRODUCTION_SERVICE_NAME,
                "service_type": "web_service",
                "branch": "master",
                "deploy_id": DEPLOY_ID,
                "commit_sha": MASTER_SHA,
                "status": "live",
                "deployed_at_utc": "2026-07-14T11:31:00Z",
            },
            "readiness": {
                "path": "/health/ready",
                "http_status": 200,
                "ready": True,
                "status": "ok",
                "authority": "verified",
                "verified_at_utc": "2026-07-14T11:48:00Z",
            },
            "worker": {
                "path": "/atlas/live/health/realmode",
                "http_status": 200,
                "verdict": verifier.EXPECTED_REALMODE_VERDICT,
                "is_real_model": True,
                "fake_runtime_env": False,
                "model_loaded": True,
                "load_error": None,
                "manifest_is_real_model": True,
                "model_id": verifier.EXPECTED_MODEL_ID,
                "worker_id": "m2-real-pythia",
                "verified_at_utc": "2026-07-14T11:48:00Z",
            },
            "worm": {
                "status": "ok",
                "authority": "verified",
                "configured_retention_days": 31,
                "write_verified": True,
                "readback_verified": True,
                "object_lock_mode": "GOVERNANCE",
                "probe_id": "worm-probe-20260714-001",
                "object_key_sha256": _digest("worm-object"),
                "version_id_sha256": _digest("worm-version"),
                "written_at_utc": "2026-07-14T11:30:00Z",
                "verified_at_utc": "2026-07-14T11:48:00Z",
                "retention_until_utc": "2026-08-15T11:30:00Z",
                "receipt_sha256": _digest("worm-receipt"),
            },
        }
    )

    ci = _common("root_ci_protected_deploy")
    ci.update(
        {
            "github_repository": {
                "id": verifier.REPOSITORY_ID,
                "node_id": verifier.REPOSITORY_NODE_ID,
                "full_name": verifier.REPOSITORY,
                "html_url": verifier.REPOSITORY_URL,
                "api_url": verifier.REPOSITORY_API_URL,
            },
            "branch": "master",
            "workflow_directory": ".github/workflows",
            "misplaced_workflow_count": 0,
            "github_app": dict(verifier.GITHUB_ACTIONS_APP),
            "branch_protection": {
                "strict": True,
                "required_checks": list(verifier.REQUIRED_CHECKS),
                "source": "github-api",
                "observed_at_utc": "2026-07-14T11:49:00Z",
            },
            "checks": [],
            "deployment": {
                "provider": "Render",
                "service_id": verifier.PRODUCTION_SERVICE_ID,
                "service_name": verifier.PRODUCTION_SERVICE_NAME,
                "service_type": "web_service",
                "repository": verifier.REPOSITORY_URL,
                "branch": "master",
                "deploy_id": DEPLOY_ID,
                "status": "live",
                "commit_sha": MASTER_SHA,
                "auto_deploy_trigger": "checksPass",
                "health_check_path": "/health",
                "deployed_at_utc": "2026-07-14T11:42:00Z",
            },
        }
    )
    for index, name in enumerate(verifier.REQUIRED_CHECKS, start=1):
        contract = verifier.WORKFLOW_CONTRACTS[name]
        run_id = 30000000000 + index
        check_run_id = 40000000000 + index
        ci["checks"].append(
            {
                "name": name,
                **contract,
                "run_id": run_id,
                "run_attempt": 1,
                "event": "push",
                "status": "completed",
                "conclusion": "success",
                "head_branch": "master",
                "head_sha": MASTER_SHA,
                "check_run_id": check_run_id,
                "check_suite_id": 50000000000 + index,
                "app_id": verifier.GITHUB_ACTIONS_APP["id"],
                "app_node_id": verifier.GITHUB_ACTIONS_APP["node_id"],
                "app_slug": verifier.GITHUB_ACTIONS_APP["slug"],
                "details_url": f"{verifier.REPOSITORY_URL}/actions/runs/{run_id}/job/{check_run_id}",
                "completed_at_utc": "2026-07-14T11:40:00Z",
            }
        )

    customer = _common("hosted_customer_journey")
    customer.update(
        {
            "app_url": f"{verifier.PRODUCTION_APP_ORIGIN}/audit-console",
            "api_base_url": verifier.PRODUCTION_API_ORIGIN,
            "service_id": verifier.PRODUCTION_SERVICE_ID,
            "customer_lane": "public-customer",
            "tenant_subject_sha256": _digest("tenant"),
            "account_subject_sha256": _digest("account"),
            "audit": {
                "audit_id": "cas-audit-0123456789abcdef",
                "create_http_status": 201,
                "terminal_status": "completed",
                "verdict": "FLAG_FOR_HUMAN_REVIEW",
                "model_id": verifier.EXPECTED_MODEL_ID,
                "mode": "BALANCED",
                "completed_at_utc": "2026-07-14T11:40:00Z",
            },
            "packet_download": {
                "audit_id": "cas-audit-0123456789abcdef",
                "http_status": 200,
                "content_type": "application/json",
                "packet_sha256": _digest("packet"),
                "verification_overall": "all_match",
                "worm_receipt_bound": True,
                "downloaded_at_utc": "2026-07-14T11:42:00Z",
            },
            "share": {
                "create_http_status": 201,
                "anonymous_fetch_http_status": 200,
                "scope": "read_only",
                "share_token_sha256": _digest("share"),
                "created_at_utc": "2026-07-14T11:43:00Z",
                "fetched_at_utc": "2026-07-14T11:44:00Z",
                "expires_at_utc": "2026-07-15T11:43:00Z",
                "revoke_http_status": 204,
                "revoked_at_utc": "2026-07-14T11:45:00Z",
                "revoked_fetch_http_status": 410,
            },
            "tenant_isolation": {
                "foreign_audit_http_status": 404,
                "foreign_packet_http_status": 404,
                "verified_at_utc": "2026-07-14T11:46:00Z",
            },
        }
    )

    accounts = _common("accounts_billing")
    accounts.update(
        {
            "api_base_url": verifier.PRODUCTION_API_ORIGIN,
            "service_id": verifier.PRODUCTION_SERVICE_ID,
            "customer_lane": "public-customer",
            "tenant_subject_sha256": _digest("billing-tenant"),
            "account_session": {
                "invite_redeem_http_status": 201,
                "login_http_status": 200,
                "logout_http_status": 204,
                "revoked_session_http_status": 401,
                "durable_session_restart_verified": True,
                "disabled_account_http_status": 403,
                "cross_tenant_http_status": 404,
                "verified_at_utc": "2026-07-14T11:45:00Z",
            },
            "quota": {
                "monthly_limit": 2,
                "usage_at_limit": 2,
                "overflow_http_status": 429,
                "overflow_error": "audit_quota_exceeded",
                "idempotent_retry_non_double_consuming": True,
                "adjacent_month_isolated": True,
                "shared_postgres_restart_verified": True,
                "verified_at_utc": "2026-07-14T11:45:00Z",
            },
            "billing": {
                "provider": "stripe",
                "mode": "live",
                "currency": "USD",
                "checkout_status": "complete",
                "subscription_status": "active",
                "invoice_status": "paid",
                "receipt_download_http_status": 200,
                "webhook_signature_verified": True,
                "entitlement_status": "active",
                "meter_to_invoice_reconciled": True,
                "provider_customer_id_sha256": _digest("customer-id"),
                "provider_subscription_id_sha256": _digest("subscription-id"),
                "invoice_id_sha256": _digest("invoice-id"),
                "paid_at_utc": "2026-07-14T11:44:00Z",
            },
        }
    )

    legal_hashes = {kind: _digest(f"legal-{kind}") for kind in verifier.LEGAL_DOCUMENT_KINDS}
    legal = _common("legal_publication_approval")
    legal.update(
        {
            "public_base_url": verifier.LANDING_ORIGIN,
            "documents": [
                {
                    "kind": kind,
                    "url": f"{verifier.LANDING_ORIGIN}/{kind}",
                    "http_status": 200,
                    "content_sha256": legal_hashes[kind],
                    "published_at_utc": "2026-07-14T11:30:00Z",
                    "verified_at_utc": "2026-07-14T11:45:00Z",
                }
                for kind in sorted(verifier.LEGAL_DOCUMENT_KINDS)
            ],
            "approvals": [_approval(role, "legal") for role in sorted(verifier.LEGAL_APPROVER_ROLES)],
            "claim_status_vocabulary": list(verifier.CLAIM_STATUS_VOCABULARY),
        }
    )

    support = _common("support_crm")
    support.update(
        {
            "public_support_url": f"{verifier.LANDING_ORIGIN}/contact",
            "api_base_url": verifier.PRODUCTION_API_ORIGIN,
            "service_id": verifier.PRODUCTION_SERVICE_ID,
            "support_ticket": {
                "ticket_id_sha256": _digest("ticket"),
                "create_http_status": 202,
                "persisted": True,
                "routed": True,
                "acknowledged": True,
                "first_response_minutes": 8,
                "sla_minutes": 30,
                "resolution_recorded": True,
                "resolved_at_utc": "2026-07-14T11:44:00Z",
            },
            "crm_lead": {
                "system": "production-crm",
                "lead_id_sha256": _digest("lead"),
                "persisted": True,
                "readback_verified": True,
                "deduplicated": True,
                "owner_assigned": True,
                "lifecycle_stage": "qualified",
                "verified_at_utc": "2026-07-14T11:45:00Z",
            },
            "consent": {
                "capture_consent_recorded": True,
                "source_attribution_recorded": True,
                "privacy_notice_linked": True,
                "recorded_at_utc": "2026-07-14T11:42:00Z",
            },
        }
    )

    incident = _common("incident_tabletop")
    incident.update(
        {
            "api_base_url": verifier.PRODUCTION_API_ORIGIN,
            "service_id": verifier.PRODUCTION_SERVICE_ID,
            "incident": {
                "record_id": "IR-2026-07-13-001",
                "status": "CLOSED",
                "closed_at_utc": "2026-07-14T11:35:00Z",
                "open_actions": 0,
                "postmortem_uri": f"{verifier.PRODUCTION_API_ORIGIN}/internal/postmortems/IR-2026-07-13-001",
                "postmortem_sha256": _digest("postmortem"),
                "credential_rotation_complete": True,
                "recovery_verified": True,
            },
            "tabletop": {
                "tabletop_id": "tabletop-20260714-001",
                "completed_at_utc": "2026-07-14T11:40:00Z",
                "participant_roles": sorted(verifier.TABLETOP_ROLES),
                "scenarios": sorted(verifier.TABLETOP_SCENARIOS),
                "open_actions": 0,
                "evidence_uri": f"{verifier.PRODUCTION_API_ORIGIN}/internal/tabletops/tabletop-20260714-001",
                "evidence_sha256": _digest("tabletop"),
            },
        }
    )

    alert = _common("alert_delivery")
    alert.update(
        {
            "api_base_url": verifier.PRODUCTION_API_ORIGIN,
            "service_id": verifier.PRODUCTION_SERVICE_ID,
            "alert": {
                "alert_id_sha256": _digest("alert"),
                "severity": "P1",
                "emitted_at_utc": "2026-07-14T11:40:00Z",
                "source": "production-readiness-monitor",
            },
            "deliveries": [
                {
                    "destination_role": role,
                    "status": "delivered",
                    "delivered_at_utc": f"2026-07-14T11:4{index}:00Z",
                    "receipt_sha256": _digest(f"delivery-{role}"),
                }
                for index, role in enumerate(sorted(verifier.ALERT_DESTINATIONS), start=1)
            ],
            "acknowledgement": {
                "status": "acknowledged",
                "acknowledged_at_utc": "2026-07-14T11:43:00Z",
                "actor_role": "incident_commander",
                "latency_seconds": 180,
            },
            "escalation": {
                "triggered": True,
                "delivered": True,
                "destination_role": "secondary_on_call",
                "receipt_sha256": _digest("escalation"),
                "delivered_at_utc": "2026-07-14T11:44:00Z",
            },
        }
    )

    honesty = _common("claim_honesty")
    surface_hashes = {
        "product_app": _digest("product-app"),
        "audit_console": _digest("audit-console"),
        "landing": _digest("landing"),
        **legal_hashes,
    }
    urls = {
        "product_app": verifier.PRODUCTION_APP_ORIGIN,
        "audit_console": f"{verifier.PRODUCTION_APP_ORIGIN}/audit-console",
        "landing": verifier.LANDING_ORIGIN,
        "legal": f"{verifier.LANDING_ORIGIN}/legal",
        "privacy": f"{verifier.LANDING_ORIGIN}/privacy",
        "terms": f"{verifier.LANDING_ORIGIN}/terms",
    }
    honesty.update(
        {
            "scanned_surfaces": [
                {
                    "kind": kind,
                    "url": urls[kind],
                    "http_status": 200,
                    "content_sha256": surface_hashes[kind],
                    "verified_at_utc": "2026-07-14T11:47:00Z",
                }
                for kind in sorted(verifier.CLAIM_SURFACE_KINDS)
            ],
            "scan": {
                "misleading_claim_count": 0,
                "unsupported_compliance_claim_count": 0,
                "unsupported_universality_claim_count": 0,
                "status_vocabulary_exact": True,
            },
            "boundaries": {
                "research_scope_disclosed": True,
                "research_accept_not_product_accept": True,
                "worm_retention_not_verdict_upgrade": True,
                "flag_for_human_review_not_accept": True,
                "compliance_certification_claims_absent": True,
                "rendered_product_status": "ACCEPT",
            },
            "approvals": [_approval(role, "claim") for role in sorted(verifier.CLAIM_APPROVER_ROLES)],
        }
    )
    return {
        "runtime_worm": runtime,
        "root_ci_protected_deploy": ci,
        "hosted_customer_journey": customer,
        "accounts_billing": accounts,
        "legal_publication_approval": legal,
        "support_crm": support,
        "incident_tabletop": incident,
        "alert_delivery": alert,
        "claim_honesty": honesty,
    }


def _accepting_manifest(
    bundle: SignedBundle,
    *,
    mutate_payloads=None,
    receipt_options: dict[str, dict] | None = None,
) -> dict:
    payloads = _gate_payloads()
    if mutate_payloads:
        mutate_payloads(payloads)
    receipt_options = receipt_options or {}
    manifest = _checked_in_manifest()
    manifest["generated_at_utc"] = GENERATED
    manifest["required_gates"] = {
        gate: {
            "status": "present",
            "evidence": bundle.receipt(
                gate, payloads[gate], **receipt_options.get(gate, {})
            ),
        }
        for gate in verifier.REQUIRED_GATES
    }
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
            "decision_record_uri": f"{verifier.PRODUCTION_API_ORIGIN}/internal/acceptance/release-record",
            "decision_record_sha256": _digest("release-record"),
        }
    )
    manifest["product"] = {
        "name": "CAS Harness",
        "environment": "public-production",
        "status": "ACCEPT",
        "status_reason": "All authoritative public-production gates and release approvals passed.",
        "release_decision": {
            "status": "ACCEPT",
            "evidence": bundle.receipt(
                "release_decision",
                release,
                issued="2026-07-14T11:59:00Z",
                **receipt_options.get("release_decision", {}),
            ),
        },
    }
    return manifest


def _verify(manifest: dict, bundle: SignedBundle, **kwargs) -> dict:
    return verifier.verify_manifest(
        manifest,
        repo_root=ROOT,
        evidence_root=bundle.root,
        verification_time=kwargs.pop("verification_time", NOW),
        expected_master_head=kwargs.pop("expected_master_head", MASTER_SHA),
        expected_deploy_id=kwargs.pop("expected_deploy_id", DEPLOY_ID),
        repository_commit=kwargs.pop("repository_commit", MASTER_SHA),
        trusted_issuers=kwargs.pop("trusted_issuers", bundle.trusted_issuers),
        registry_sha256=kwargs.pop("registry_sha256", _digest("test-registry")),
        **kwargs,
    )


class CheckedInOpenContractTests(unittest.TestCase):
    def test_checked_in_manifest_is_valid_and_truthfully_open(self) -> None:
        report = verifier.verify_manifest(
            _checked_in_manifest(),
            repo_root=ROOT,
            verification_time=NOW,
            repository_commit=MASTER_SHA,
        )
        self.assertEqual(report["result"], "OPEN")
        self.assertFalse(report["accepted"])
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["open_gates"], list(verifier.REQUIRED_GATES))
        for key in (
            "verification_time_utc",
            "manifest_sha256",
            "verifier_sha256",
            "repository_commit",
            "trusted_issuer_registry_sha256",
            "evidence_sha256",
            "subject_sha256",
            "authorities",
        ):
            self.assertIn(key, report)

    def test_research_artifact_hash_is_checkout_newline_invariant(self) -> None:
        lf = b'{\n  "verdict": "ACCEPT"\n}\n'
        crlf = lf.replace(b"\n", b"\r\n")
        self.assertEqual(
            verifier._repository_text_sha256(lf),
            verifier._repository_text_sha256(crlf),
        )

    def test_validate_only_permits_open_but_normal_command_does_not(self) -> None:
        with redirect_stdout(io.StringIO()):
            valid = verifier.main(
                [
                    "--manifest",
                    str(MANIFEST_PATH),
                    "--repo-root",
                    str(ROOT),
                    "--validate-only",
                    "--now",
                    "2026-07-14T12:00:00Z",
                ]
            )
            normal = verifier.main(
                ["--manifest", str(MANIFEST_PATH), "--repo-root", str(ROOT)]
            )
        self.assertEqual(valid, 0)
        self.assertEqual(normal, 1)

    def test_now_is_forbidden_for_normal_acceptance(self) -> None:
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            result = verifier.main(
                [
                    "--manifest",
                    str(MANIFEST_PATH),
                    "--repo-root",
                    str(ROOT),
                    "--now",
                    "2026-07-14T12:00:00Z",
                ]
            )
        self.assertEqual(result, 1)
        self.assertIn("--now is forbidden", stderr.getvalue())

    def test_validate_only_cannot_emit_a_production_acceptance_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "must-not-exist"
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                result = verifier.main(
                    [
                        "--manifest",
                        str(MANIFEST_PATH),
                        "--repo-root",
                        str(ROOT),
                        "--validate-only",
                        "--sanitized-bundle-path",
                        str(output),
                    ]
                )
            self.assertEqual(result, 1)
            self.assertIn("forbidden with --validate-only", stderr.getvalue())
            self.assertFalse(output.exists())

    def test_duplicate_manifest_keys_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "duplicate.json"
            path.write_text('{"schema_version":"one","schema_version":"two"}', encoding="utf-8")
            with self.assertRaises(verifier.ManifestLoadError):
                verifier.load_manifest(path)

    def test_registry_uses_exact_gate_subject_pairs_not_independent_sets(self) -> None:
        key_size = (RSA_N.bit_length() + 7) // 8
        modulus = base64.urlsafe_b64encode(
            RSA_N.to_bytes(key_size, "big")
        ).decode("ascii").rstrip("=")
        issuer = {
            "issuer": TEST_ISSUER,
            "key_id": TEST_KEY_ID,
            "algorithm": "RS256",
            "n_base64url": modulus,
            "e": RSA_E,
            "allowed_subjects": [
                {
                    "gate": "runtime_worm",
                    "uri": SUBJECT_URIS["runtime_worm"],
                }
            ],
            "valid_from_utc": "2026-01-01T00:00:00Z",
            "valid_until_utc": "2027-01-01T00:00:00Z",
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            registry = root / verifier.TRUSTED_ISSUER_REGISTRY
            registry.parent.mkdir(parents=True)
            registry.write_text(
                json.dumps(
                    {
                        "schema_version": verifier.REGISTRY_SCHEMA_VERSION,
                        "issuers": [issuer],
                    }
                ),
                encoding="utf-8",
            )
            loaded, _ = verifier._load_trusted_issuer_registry(root)
            self.assertEqual(
                loaded[(TEST_ISSUER, TEST_KEY_ID)]["allowed_subjects"],
                frozenset({("runtime_worm", SUBJECT_URIS["runtime_worm"])}),
            )

            legacy = dict(issuer)
            legacy.pop("allowed_subjects")
            legacy["allowed_gates"] = ["runtime_worm"]
            legacy["allowed_origins"] = [verifier.PRODUCTION_API_ORIGIN]
            registry.write_text(
                json.dumps(
                    {
                        "schema_version": verifier.REGISTRY_SCHEMA_VERSION,
                        "issuers": [legacy],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(verifier.ManifestLoadError):
                verifier._load_trusted_issuer_registry(root)

    def test_contract_ci_is_separate_from_production_accept(self) -> None:
        errors: list[str] = []
        verifier._validate_workflow_separation(ROOT, errors)
        self.assertEqual(errors, [])
        ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        accept = (ROOT / ".github/workflows/customer-production-accept.yml").read_text(encoding="utf-8")
        self.assertIn("OPEN permitted", ci)
        self.assertIn("--validate-only", ci)
        self.assertNotIn("customer-production-accept", ci.split("  required_gate:", 1)[1])
        self.assertIn("name: customer-production-accept", accept)
        self.assertNotIn("--validate-only", accept)
        accept_job = accept.split("  customer_production_accept:", 1)[1]
        self.assertFalse(
            any(line.startswith("    if:") for line in accept_job.splitlines())
        )
        self.assertIn(
            "Fail closed unless dispatched from protected master in the exact repository",
            accept,
        )
        self.assertIn('test "$DISPATCH_REF" = "refs/heads/master"', accept)
        self.assertIn('test "$DISPATCH_REF_PROTECTED" = "true"', accept)
        self.assertIn('test "$DISPATCH_SHA" = "$EXPECTED_MASTER_HEAD"', accept)
        self.assertIn("--sanitized-bundle-path", accept)
        self.assertIn("path: customer-production-archive", accept)
        self.assertIn("include-hidden-files: true", accept)


class AuthoritativeAcceptanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bundle = SignedBundle()

    def tearDown(self) -> None:
        self.bundle.close()

    def test_complete_signed_public_proof_accepts_and_reports_every_hash(self) -> None:
        manifest = _accepting_manifest(self.bundle)
        report = _verify(manifest, self.bundle)

        self.assertEqual(report["errors"], [])
        self.assertEqual(report["result"], "ACCEPT")
        self.assertTrue(report["accepted"])
        self.assertEqual(set(report["evidence_sha256"]), verifier.AUTHORITY_GATES)
        self.assertEqual(set(report["subject_sha256"]), verifier.AUTHORITY_GATES)
        self.assertEqual(report["repository_commit"], MASTER_SHA)
        self.assertEqual(report["expected_master_head"], MASTER_SHA)
        self.assertEqual(report["expected_deploy_id"], DEPLOY_ID)
        self.assertTrue(all(authority["mode"] == "signed_receipt" for authority in report["authorities"].values()))

    def test_sanitized_archive_contains_only_verified_referenced_documents(self) -> None:
        manifest = _accepting_manifest(self.bundle)
        manifest_raw = json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8") + b"\n"
        resolved_documents: dict[str, bytes] = {}
        registry_raw = (ROOT / verifier.TRUSTED_ISSUER_REGISTRY).read_bytes()
        report = _verify(
            manifest,
            self.bundle,
            manifest_raw=manifest_raw,
            resolved_documents=resolved_documents,
            registry_sha256=hashlib.sha256(registry_raw).hexdigest(),
        )
        (self.bundle.root / "unreferenced-secret.txt").write_text(
            "must never be archived", encoding="utf-8"
        )

        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "sanitized-evidence-bundle"
            verifier._write_sanitized_bundle(
                manifest=manifest,
                manifest_raw=manifest_raw,
                repo_root=ROOT,
                output_root=output,
                resolved_documents=resolved_documents,
                report=report,
            )

            self.assertEqual(
                (output / "customer-production-acceptance.json").read_bytes(),
                manifest_raw,
            )
            self.assertTrue((output / "sanitized-bundle-index.json").is_file())
            self.assertTrue((output / verifier.TRUSTED_ISSUER_REGISTRY).is_file())
            self.assertFalse((output / "unreferenced-secret.txt").exists())
            for gate in verifier.AUTHORITY_GATES:
                reference = (
                    manifest["product"]["release_decision"]["evidence"]
                    if gate == "release_decision"
                    else manifest["required_gates"][gate]["evidence"]
                )
                archived = output / reference["uri"].removeprefix("repo://")
                self.assertTrue(archived.is_file(), gate)
                self.assertEqual(
                    hashlib.sha256(archived.read_bytes()).hexdigest(),
                    report["evidence_sha256"][gate],
                )

    def test_self_attested_https_is_not_authoritative_without_live_verification(self) -> None:
        manifest = _accepting_manifest(self.bundle)
        payload = _gate_payloads()["runtime_worm"]
        raw = json.dumps(payload, sort_keys=True).encode("utf-8")
        manifest["required_gates"]["runtime_worm"]["evidence"] = {
            "uri": SUBJECT_URIS["runtime_worm"],
            "sha256": hashlib.sha256(raw).hexdigest(),
            "authority": {
                "mode": "live_https",
                "issuer": "noetic-production-live",
                "key_id": None,
            },
        }

        report = _verify(manifest, self.bundle, live=False)

        self.assertEqual(report["result"], "INVALID")
        self.assertTrue(any("requires --live" in error for error in report["errors"]))

    def test_allowlisted_live_https_is_dereferenced_and_hash_verified(self) -> None:
        manifest = _accepting_manifest(self.bundle)
        payload = _gate_payloads()["runtime_worm"]
        payload["artifact_uri"] = SUBJECT_URIS["runtime_worm"]
        payload["artifact_sha256"] = _digest("live-runtime-subject")
        raw = json.dumps(payload, sort_keys=True).encode("utf-8")
        manifest["required_gates"]["runtime_worm"]["evidence"] = {
            "uri": SUBJECT_URIS["runtime_worm"],
            "sha256": hashlib.sha256(raw).hexdigest(),
            "authority": {
                "mode": "live_https",
                "issuer": "noetic-production-live",
                "key_id": None,
            },
        }
        with patch.object(verifier, "_fetch_https", return_value=raw) as fetch:
            report = _verify(manifest, self.bundle, live=True)
        self.assertEqual(report["errors"], [])
        self.assertTrue(report["accepted"])
        fetch.assert_called_once()

    def test_legal_live_authority_is_json_api_endpoint_not_html_page(self) -> None:
        manifest = _accepting_manifest(self.bundle)
        payload = _gate_payloads()["legal_publication_approval"]
        self.assertEqual(
            SUBJECT_URIS["legal_publication_approval"],
            (
                f"{verifier.PRODUCTION_API_ORIGIN}/internal/acceptance/"
                "legal-publication-approval"
            ),
        )
        self.assertNotEqual(
            SUBJECT_URIS["legal_publication_approval"],
            f"{verifier.LANDING_ORIGIN}/legal",
        )
        payload["artifact_uri"] = SUBJECT_URIS["legal_publication_approval"]
        payload["artifact_sha256"] = _digest("live-legal-subject")
        raw = json.dumps(payload, sort_keys=True).encode("utf-8")
        manifest["required_gates"]["legal_publication_approval"]["evidence"] = {
            "uri": SUBJECT_URIS["legal_publication_approval"],
            "sha256": hashlib.sha256(raw).hexdigest(),
            "authority": {
                "mode": "live_https",
                "issuer": "noetic-production-live",
                "key_id": None,
            },
        }
        with patch.object(verifier, "_fetch_https", return_value=raw) as fetch:
            report = _verify(manifest, self.bundle, live=True)
        self.assertEqual(report["errors"], [])
        self.assertTrue(report["accepted"])
        fetch.assert_called_once_with(
            SUBJECT_URIS["legal_publication_approval"],
            frozenset({verifier.PRODUCTION_API_ORIGIN}),
        )

    def test_unallowlisted_live_origin_is_rejected_before_fetch(self) -> None:
        manifest = _accepting_manifest(self.bundle)
        manifest["required_gates"]["runtime_worm"]["evidence"] = {
            "uri": "https://attacker.example.test/runtime.json",
            "sha256": _digest("attacker"),
            "authority": {
                "mode": "live_https",
                "issuer": "noetic-production-live",
                "key_id": None,
            },
        }
        with patch.object(verifier, "_fetch_https") as fetch:
            report = _verify(manifest, self.bundle, live=True)
        self.assertEqual(report["result"], "INVALID")
        self.assertTrue(any("exact live issuer endpoint" in error for error in report["errors"]))
        fetch.assert_not_called()

    def test_dereferenced_receipt_hash_mismatch_is_rejected(self) -> None:
        manifest = _accepting_manifest(self.bundle)
        manifest["required_gates"]["runtime_worm"]["evidence"]["sha256"] = "0" * 64
        report = _verify(manifest, self.bundle)
        self.assertEqual(report["result"], "INVALID")
        self.assertTrue(any("dereferenced evidence bytes" in error for error in report["errors"]))

    def test_invalid_signature_and_unknown_issuer_are_rejected(self) -> None:
        invalid_signature = _accepting_manifest(
            self.bundle,
            receipt_options={"runtime_worm": {"sign": False}},
        )
        report = _verify(invalid_signature, self.bundle)
        self.assertTrue(any("signature verification failed" in error for error in report["errors"]))

        other_bundle = SignedBundle()
        try:
            unknown = _accepting_manifest(
                other_bundle,
                receipt_options={"runtime_worm": {"issuer": "unknown-issuer"}},
            )
            report = _verify(unknown, other_bundle)
            self.assertTrue(any("not pinned" in error for error in report["errors"]))
        finally:
            other_bundle.close()

    def test_signed_subject_origin_and_hash_are_bound(self) -> None:
        manifest = _accepting_manifest(
            self.bundle,
            receipt_options={
                "runtime_worm": {
                    "subject_uri": "https://attacker.example.test/runtime"
                }
            },
        )
        report = _verify(manifest, self.bundle)
        self.assertEqual(report["result"], "INVALID")
        self.assertTrue(any("origin is not allowlisted" in error for error in report["errors"]))

    def test_issuer_gate_and_subject_endpoint_are_one_exact_grant(self) -> None:
        crossed_endpoint = (
            f"{verifier.RENDER_API_ORIGIN}/v1/services/"
            f"{verifier.PRODUCTION_SERVICE_ID}/deploys/{DEPLOY_ID}"
        )
        self.bundle.trusted_issuers[(TEST_ISSUER, TEST_KEY_ID)][
            "allowed_subjects"
        ] = frozenset(
            {
                ("runtime_worm", SUBJECT_URIS["runtime_worm"]),
                ("root_ci_protected_deploy", crossed_endpoint),
            }
        )
        manifest = _accepting_manifest(
            self.bundle,
            receipt_options={
                "runtime_worm": {"subject_uri": crossed_endpoint}
            },
        )

        report = _verify(manifest, self.bundle)

        self.assertEqual(report["result"], "INVALID")
        self.assertTrue(
            any("exact issuer gate/subject grant" in error for error in report["errors"])
        )

    def test_live_issuer_cannot_cross_to_another_endpoint_on_allowed_origin(self) -> None:
        crossed_endpoint = (
            f"{verifier.RENDER_API_ORIGIN}/v1/services/"
            f"{verifier.PRODUCTION_SERVICE_ID}/deploys/{DEPLOY_ID}"
        )
        manifest = _accepting_manifest(self.bundle)
        payload = _gate_payloads()["runtime_worm"]
        payload["artifact_uri"] = crossed_endpoint
        payload["artifact_sha256"] = _digest("crossed-live-subject")
        raw = json.dumps(payload, sort_keys=True).encode("utf-8")
        manifest["required_gates"]["runtime_worm"]["evidence"] = {
            "uri": crossed_endpoint,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "authority": {
                "mode": "live_https",
                "issuer": "noetic-production-live",
                "key_id": None,
            },
        }

        with patch.object(verifier, "_fetch_https") as fetch:
            report = _verify(manifest, self.bundle, live=True)

        self.assertEqual(report["result"], "INVALID")
        self.assertTrue(
            any("exact live issuer endpoint" in error for error in report["errors"])
        )
        fetch.assert_not_called()

    def test_duplicate_keys_in_signed_receipt_are_rejected(self) -> None:
        manifest = _accepting_manifest(self.bundle)
        reference = manifest["required_gates"]["runtime_worm"]["evidence"]
        path = self.bundle.root / reference["uri"].removeprefix("repo://")
        text = path.read_text(encoding="utf-8")
        text = text.replace('"issuer":', '"issuer":"duplicate","issuer":', 1)
        path.write_text(text, encoding="utf-8")
        reference["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        report = _verify(manifest, self.bundle)
        self.assertEqual(report["result"], "INVALID")
        self.assertTrue(any("DuplicateJsonKeyError" in error for error in report["errors"]))

    def test_receipt_must_be_current_and_issued_before_manifest(self) -> None:
        expired = _accepting_manifest(
            self.bundle,
            receipt_options={"runtime_worm": {"expires": "2026-07-14T11:59:00Z"}},
        )
        report = _verify(expired, self.bundle)
        self.assertTrue(any("active at verification" in error for error in report["errors"]))

        late_bundle = SignedBundle()
        try:
            late = _accepting_manifest(
                late_bundle,
                receipt_options={"runtime_worm": {"issued": "2026-07-14T12:01:00Z"}},
            )
            report = _verify(late, late_bundle)
            self.assertTrue(any("at or before manifest generation" in error for error in report["errors"]))
            self.assertTrue(
                any(
                    "issued_at_utc" in error and "at or before verification" in error
                    for error in report["errors"]
                )
            )
        finally:
            late_bundle.close()

    def test_receipt_cannot_predate_the_evidence_it_signs(self) -> None:
        manifest = _accepting_manifest(
            self.bundle,
            receipt_options={"runtime_worm": {"issued": "2026-07-14T11:49:00Z"}},
        )

        report = _verify(manifest, self.bundle)

        self.assertEqual(report["result"], "INVALID")
        self.assertTrue(
            any("must be at or after evidence observation" in error for error in report["errors"])
        )

    def test_private_canary_cannot_satisfy_any_public_gate(self) -> None:
        cases = {
            "service_id": lambda payloads: payloads["runtime_worm"]["deployment"].update(
                service_id=verifier.PRIVATE_CANARY_SERVICE_ID
            ),
            "branch": lambda payloads: payloads["root_ci_protected_deploy"]["deployment"].update(
                branch=verifier.PRIVATE_CANARY_BRANCH
            ),
            "lane": lambda payloads: payloads["hosted_customer_journey"].update(
                customer_lane="accounts-canary"
            ),
            "environment": lambda payloads: payloads["accounts_billing"].update(
                environment="private-canary"
            ),
        }
        for label, mutate in cases.items():
            with self.subTest(label=label):
                bundle = SignedBundle()
                try:
                    manifest = _accepting_manifest(bundle, mutate_payloads=mutate)
                    report = _verify(manifest, bundle)
                    self.assertEqual(report["result"], "INVALID")
                    self.assertTrue(
                        any("canary" in error.lower() for error in report["errors"])
                    )
                finally:
                    bundle.close()

    def test_public_app_and_api_origins_are_exact(self) -> None:
        def mutate(payloads):
            payloads["hosted_customer_journey"]["app_url"] = (
                "https://preview.example.test/audit-console"
            )
            payloads["accounts_billing"]["api_base_url"] = (
                "https://canary-api.example.test"
            )

        manifest = _accepting_manifest(self.bundle, mutate_payloads=mutate)
        report = _verify(manifest, self.bundle)
        self.assertEqual(report["result"], "INVALID")
        self.assertTrue(any("app_url" in error for error in report["errors"]))
        self.assertTrue(any("api_base_url" in error for error in report["errors"]))

    def test_github_repository_workflow_and_app_identities_are_pinned(self) -> None:
        mutations = {
            "repository": lambda ci: ci["github_repository"].update(id=1),
            "workflow id": lambda ci: ci["checks"][0].update(workflow_id=1),
            "workflow path": lambda ci: ci["checks"][0].update(
                workflow_path="nested/.github/workflows/ci.yml"
            ),
            "app": lambda ci: ci["checks"][0].update(app_id=1),
            "run event": lambda ci: ci["checks"][0].update(event="pull_request"),
            "run attempt": lambda ci: ci["checks"][0].update(run_attempt=0),
            "details URL": lambda ci: ci["checks"][0].update(
                details_url="https://github.com/other/repo/actions/runs/1/job/1"
            ),
            "same-run wrong job URL": lambda ci: ci["checks"][0].update(
                details_url=(
                    f"{verifier.REPOSITORY_URL}/actions/runs/"
                    f"{ci['checks'][0]['run_id']}/job/99999999999"
                )
            ),
        }
        for label, mutate_ci in mutations.items():
            with self.subTest(label=label):
                bundle = SignedBundle()
                try:
                    manifest = _accepting_manifest(
                        bundle,
                        mutate_payloads=lambda payloads: mutate_ci(
                            payloads["root_ci_protected_deploy"]
                        ),
                    )
                    report = _verify(manifest, bundle)
                    self.assertEqual(report["result"], "INVALID")
                finally:
                    bundle.close()

    def test_commit_and_deploy_are_bound_to_external_inputs_and_checkout(self) -> None:
        manifest = _accepting_manifest(self.bundle)
        wrong_head = _verify(
            manifest, self.bundle, expected_master_head="b" * 40
        )
        self.assertEqual(wrong_head["result"], "INVALID")
        self.assertTrue(
            any("expected master HEAD" in error for error in wrong_head["errors"])
        )

        wrong_deploy = _verify(
            manifest, self.bundle, expected_deploy_id="dep-different"
        )
        self.assertEqual(wrong_deploy["result"], "INVALID")
        self.assertTrue(
            any("production deployment ID" in error for error in wrong_deploy["errors"])
        )

        wrong_checkout = _verify(
            manifest, self.bundle, repository_commit="c" * 40
        )
        self.assertEqual(wrong_checkout["result"], "INVALID")
        self.assertTrue(
            any("exact expected master HEAD" in error for error in wrong_checkout["errors"])
        )

    def test_event_observation_generation_verification_order_is_strict(self) -> None:
        cases = {
            "event after observation": (
                lambda payloads: payloads["runtime_worm"].update(
                    event_at_utc="2026-07-14T11:51:00Z"
                ),
                NOW,
            ),
            "observation after generation": (
                lambda payloads: payloads["runtime_worm"].update(
                    observed_at_utc="2026-07-14T12:01:00Z"
                ),
                NOW,
            ),
            "observation after verification": (
                lambda payloads: payloads["runtime_worm"].update(
                    observed_at_utc="2026-07-14T11:59:00Z"
                ),
                datetime(2026, 7, 14, 11, 58, 0, tzinfo=timezone.utc),
            ),
            "nested event after observation": (
                lambda payloads: payloads["hosted_customer_journey"]["audit"].update(
                    completed_at_utc="2026-07-14T11:51:00Z"
                ),
                NOW,
            ),
        }
        for label, (mutate, verification_time) in cases.items():
            with self.subTest(label=label):
                bundle = SignedBundle()
                try:
                    manifest = _accepting_manifest(bundle, mutate_payloads=mutate)
                    report = _verify(
                        manifest, bundle, verification_time=verification_time
                    )
                    self.assertEqual(report["result"], "INVALID")
                finally:
                    bundle.close()

        manifest = _accepting_manifest(self.bundle)
        manifest["generated_at_utc"] = "2026-07-14T12:01:00Z"
        report = _verify(manifest, self.bundle)
        self.assertTrue(
            any("at or before verification" in error for error in report["errors"])
        )

    def test_stale_gate_event_cannot_be_wrapped_by_fresh_observation(self) -> None:
        def mutate(payloads):
            for gate in verifier.REQUIRED_GATES:
                payloads[gate]["event_at_utc"] = "2020-01-01T00:00:00Z"

        manifest = _accepting_manifest(self.bundle, mutate_payloads=mutate)

        report = _verify(manifest, self.bundle)

        self.assertEqual(report["result"], "INVALID")
        for gate in verifier.REQUIRED_GATES:
            self.assertTrue(
                any(
                    f"required_gates.{gate}" in error
                    and "event_at_utc" in error
                    and "stale" in error
                    for error in report["errors"]
                ),
                gate,
            )

    def test_every_critical_nested_proof_timestamp_is_event_bound_and_fresh(self) -> None:
        def mutate(payloads):
            for gate, paths in CRITICAL_TIMESTAMP_PATHS.items():
                for path in paths:
                    _set_nested(
                        payloads[gate], path, "2020-01-01T00:00:00Z"
                    )

        manifest = _accepting_manifest(self.bundle, mutate_payloads=mutate)

        report = _verify(manifest, self.bundle)

        self.assertEqual(report["result"], "INVALID")
        chronology_errors = [
            error
            for error in report["errors"]
            if "must be at or after the gate event" in error
        ]
        self.assertEqual(
            len(chronology_errors),
            sum(len(paths) for paths in CRITICAL_TIMESTAMP_PATHS.values()),
        )

    def test_alert_chronology_and_reported_latency_bind_actual_clock_delta(self) -> None:
        cases = {
            "claimed latency differs from actual": lambda alert: alert[
                "acknowledgement"
            ].update(latency_seconds=1),
            "actual acknowledgement exceeds ten minutes": lambda alert: (
                alert["alert"].update(emitted_at_utc="2026-07-14T11:30:00Z"),
                alert["acknowledgement"].update(latency_seconds=60),
            ),
            "delivery predates emission": lambda alert: alert["deliveries"][
                0
            ].update(delivered_at_utc="2026-07-14T11:39:00Z"),
            "acknowledgement predates emission": lambda alert: alert[
                "acknowledgement"
            ].update(acknowledged_at_utc="2026-07-14T11:39:00Z"),
            "escalation predates emission": lambda alert: alert[
                "escalation"
            ].update(delivered_at_utc="2026-07-14T11:39:00Z"),
        }
        for label, mutate_alert in cases.items():
            with self.subTest(label=label):
                bundle = SignedBundle()
                try:
                    manifest = _accepting_manifest(
                        bundle,
                        mutate_payloads=lambda payloads: mutate_alert(
                            payloads["alert_delivery"]
                        ),
                    )
                    report = _verify(manifest, bundle)
                    self.assertEqual(report["result"], "INVALID")
                finally:
                    bundle.close()

    def test_release_approval_must_follow_newest_gate_evidence(self) -> None:
        manifest = _accepting_manifest(self.bundle)
        reference = manifest["product"]["release_decision"]["evidence"]
        path = self.bundle.root / reference["uri"].removeprefix("repo://")
        receipt = json.loads(path.read_text(encoding="utf-8"))
        receipt["evidence"]["approved_at_utc"] = "2026-07-14T11:49:00Z"
        unsigned = {
            key: value
            for key, value in receipt.items()
            if key != "signature_base64url"
        }
        receipt["signature_base64url"] = _sign(unsigned)
        raw = json.dumps(receipt, indent=2, sort_keys=True).encode("utf-8") + b"\n"
        path.write_bytes(raw)
        reference["sha256"] = hashlib.sha256(raw).hexdigest()
        report = _verify(manifest, self.bundle)
        self.assertEqual(report["result"], "INVALID")
        self.assertTrue(
            any("newest gate evidence" in error for error in report["errors"])
        )

    def test_worm_must_be_active_and_cover_configured_minimum(self) -> None:
        cases = {
            "configured below minimum": lambda worm: worm.update(
                configured_retention_days=30
            ),
            "receipt shorter than configured": lambda worm: worm.update(
                retention_until_utc="2026-08-13T11:30:00Z"
            ),
            "insufficient remaining window": lambda worm: worm.update(
                retention_until_utc="2026-08-13T12:00:00Z",
                configured_retention_days=30,
            ),
        }
        for label, mutate_worm in cases.items():
            with self.subTest(label=label):
                bundle = SignedBundle()
                try:
                    manifest = _accepting_manifest(
                        bundle,
                        mutate_payloads=lambda payloads: mutate_worm(
                            payloads["runtime_worm"]["worm"]
                        ),
                    )
                    report = _verify(manifest, bundle)
                    self.assertEqual(report["result"], "INVALID")
                finally:
                    bundle.close()

    def test_duplicate_authoritative_receipts_cannot_fill_multiple_gates(self) -> None:
        manifest = _accepting_manifest(self.bundle)
        manifest["required_gates"]["support_crm"]["evidence"] = copy.deepcopy(
            manifest["required_gates"]["accounts_billing"]["evidence"]
        )
        report = _verify(manifest, self.bundle)
        self.assertEqual(report["result"], "INVALID")
        self.assertTrue(
            any("distinct authoritative evidence" in error for error in report["errors"])
        )

    def test_research_accept_artifact_stays_separate(self) -> None:
        manifest = _accepting_manifest(self.bundle)
        manifest["required_gates"]["runtime_worm"]["evidence"]["sha256"] = manifest[
            "claim_boundary"
        ]["research_verdict"]["artifact_sha256"]
        report = _verify(manifest, self.bundle)
        self.assertEqual(report["result"], "INVALID")
        self.assertTrue(
            any("research ACCEPT" in error for error in report["errors"])
        )


if __name__ == "__main__":
    unittest.main()
