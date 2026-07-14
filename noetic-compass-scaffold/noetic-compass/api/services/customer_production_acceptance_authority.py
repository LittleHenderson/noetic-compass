"""Durable, fail-closed authority documents for customer-production gates.

This service is a read model over the existing :class:`StateStore` substrate.
It stores immutable, content-addressed revisions plus a version-checked head for
each allowlisted gate.  ``SqliteStateStore`` and ``PostgresStateStore`` therefore
use the same contract.  An optional immutable backend can put the exact canonical
JSON bytes behind the existing S3 Object-Lock seam; when a head names WORM bytes,
the service refuses to fall back to an inline copy.

There is intentionally no HTTP write route.  A collector/publisher must first
obtain independent evidence (including any human approval artifacts), validate
it against the canonical acceptance verifier, and then call :meth:`publish`
inside an authenticated operational process.  This module never manufactures a
receipt, approval, or successful value from live application state.

The public route returns only the evidence document.  StateStore metadata,
Object-Lock version IDs, and operational errors stay server-side.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import json
import re
from typing import Any, Protocol
from urllib.parse import parse_qs, unquote, urlparse

from api.acceptance_authority_contract import (
    ACCEPTANCE_AUTHORITY_PATH_BY_GATE,
    PRODUCTION_API_ORIGIN,
    acceptance_authority_url,
)
from api.services.production.state_substrate import (
    LedgerRecord,
    StateStore,
    VersionConflict,
)
from api.services.production.worm_writes import RetentionPolicy
from api.services.cas_harness_retention_disclosure import (
    revalidate_object_lock_verification,
)


EVIDENCE_SCHEMA_VERSION = "cas_harness_customer_production_gate_evidence.v2"
RECORD_SCHEMA_VERSION = "cas_harness_acceptance_authority_revision.v2"
HEAD_SCHEMA_VERSION = "cas_harness_acceptance_authority_head.v3"
OPERATION_SCHEMA_VERSION = "cas_harness_acceptance_authority_operation.v1"
REPOSITORY = "LittleHenderson/noetic-compass"
ENVIRONMENT = "public-production"
PRODUCTION_APP_ORIGIN = "https://atlas.noeticcompass.com"
LANDING_ORIGIN = "https://cascompass.ai"
PRODUCTION_SERVICE_ID = "srv-d82ph683kofs73d210e0"
PRODUCTION_SERVICE_NAME = "noetic-compass-api"
EXPECTED_MODEL_ID = "EleutherAI/pythia-160m"
EXPECTED_REALMODE_VERDICT = "REAL_PYTHIA_WEIGHTS_LOADED"

AUTHORITY_TENANT_ID = "cas-harness-customer-production"
REVISION_KIND = "customer_production_acceptance_authority_revision"
HEAD_KIND = "customer_production_acceptance_authority_head"
OPERATION_KIND = "customer_production_acceptance_authority_operation"
MAX_EVIDENCE_BYTES = 2_000_000

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_DEPLOY_ID_RE = re.compile(r"^dep-[A-Za-z0-9]+$")
_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_AUDIT_ID_RE = re.compile(r"^cas-audit-[0-9a-f]{16}$")
_PROBE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,127}$")
_INCIDENT_ID_RE = re.compile(r"^IR-\d{4}-\d{2}-\d{2}-\d{3}$")

_RESEARCH_VERDICTS = frozenset({"ACCEPT", "FLAG_FOR_HUMAN_REVIEW", "SUPPRESS"})
_LEGAL_DOCUMENT_KINDS = frozenset({"legal", "privacy", "terms"})
_LEGAL_APPROVER_ROLES = frozenset(
    {"legal_counsel", "privacy_owner", "product_owner"}
)
_CLAIM_SURFACE_KINDS = frozenset(
    {"product_app", "audit_console", "landing", "legal", "privacy", "terms"}
)
_CLAIM_APPROVER_ROLES = frozenset(
    {"legal_owner", "product_owner", "research_owner"}
)
_TABLETOP_ROLES = frozenset(
    {"incident_commander", "legal", "operations", "security", "support"}
)
_TABLETOP_SCENARIOS = frozenset(
    {
        "account_compromise",
        "billing_webhook_failure",
        "data_subject_request",
        "worker_outage",
        "worm_authentication_failure",
    }
)
_ALERT_DESTINATIONS = frozenset({"incident_channel", "primary_on_call"})
_RELEASE_APPROVER_ROLES = frozenset(
    {"legal_owner", "operations_owner", "product_owner", "security_owner"}
)
_CLAIM_STATUS_VOCABULARY = [
    "ACCEPT",
    "FLAG_FOR_HUMAN_REVIEW",
    "LICENSED",
    "NOT LICENSED",
    "OPEN",
    "present",
    "unavailable",
]

_FRESHNESS_MINUTES = {
    "runtime_worm": 30,
    "hosted_customer_journey": 4320,
    "accounts_billing": 4320,
    "legal_publication_approval": 43200,
    "support_crm": 4320,
    "incident_tabletop": 129600,
    "alert_delivery": 1440,
    "claim_honesty": 1440,
}

_COMMON_FIELDS = frozenset(
    {
        "schema_version",
        "gate",
        "environment",
        "repository",
        "master_head_sha",
        "deploy_id",
        "event_at_utc",
        "observed_at_utc",
        "artifact_uri",
        "artifact_sha256",
    }
)

_EXTRA_FIELDS: dict[str, frozenset[str]] = {
    "runtime_worm": frozenset(
        {"api_base_url", "deployment", "readiness", "worker", "worm"}
    ),
    "hosted_customer_journey": frozenset(
        {
            "app_url",
            "api_base_url",
            "service_id",
            "customer_lane",
            "tenant_subject_sha256",
            "account_subject_sha256",
            "audit",
            "packet_download",
            "share",
            "tenant_isolation",
        }
    ),
    "accounts_billing": frozenset(
        {
            "api_base_url",
            "service_id",
            "customer_lane",
            "tenant_subject_sha256",
            "account_session",
            "quota",
            "billing",
        }
    ),
    "legal_publication_approval": frozenset(
        {"public_base_url", "documents", "approvals", "claim_status_vocabulary"}
    ),
    "support_crm": frozenset(
        {
            "public_support_url",
            "api_base_url",
            "service_id",
            "support_ticket",
            "crm_lead",
            "consent",
        }
    ),
    "incident_tabletop": frozenset(
        {"api_base_url", "service_id", "incident", "tabletop"}
    ),
    "alert_delivery": frozenset(
        {
            "api_base_url",
            "service_id",
            "alert",
            "deliveries",
            "acknowledgement",
            "escalation",
        }
    ),
    "claim_honesty": frozenset(
        {"scanned_surfaces", "scan", "boundaries", "approvals"}
    ),
    "release_decision": frozenset(
        {
            "status",
            "approved_at_utc",
            "approver_roles",
            "decision_record_uri",
            "decision_record_sha256",
        }
    ),
}

# Exact mapping-valued fields.  Values below these objects must be JSON scalars,
# except for the explicitly allowlisted scalar lists in ``_NESTED_LIST_FIELDS``.
_OBJECT_FIELDS: dict[str, dict[str, frozenset[str]]] = {
    "runtime_worm": {
        "deployment": frozenset(
            {
                "service_id",
                "service_name",
                "service_type",
                "branch",
                "deploy_id",
                "commit_sha",
                "status",
                "deployed_at_utc",
            }
        ),
        "readiness": frozenset(
            {"path", "http_status", "ready", "status", "authority", "verified_at_utc"}
        ),
        "worker": frozenset(
            {
                "path",
                "http_status",
                "verdict",
                "is_real_model",
                "fake_runtime_env",
                "model_loaded",
                "load_error",
                "manifest_is_real_model",
                "model_id",
                "worker_id",
                "verified_at_utc",
            }
        ),
        "worm": frozenset(
            {
                "status",
                "authority",
                "configured_retention_days",
                "write_verified",
                "readback_verified",
                "object_lock_mode",
                "probe_id",
                "object_key_sha256",
                "version_id_sha256",
                "written_at_utc",
                "verified_at_utc",
                "retention_until_utc",
                "receipt_sha256",
            }
        ),
    },
    "hosted_customer_journey": {
        "audit": frozenset(
            {
                "audit_id",
                "create_http_status",
                "terminal_status",
                "verdict",
                "model_id",
                "mode",
                "completed_at_utc",
            }
        ),
        "packet_download": frozenset(
            {
                "audit_id",
                "http_status",
                "content_type",
                "packet_sha256",
                "verification_overall",
                "worm_receipt_bound",
                "downloaded_at_utc",
            }
        ),
        "share": frozenset(
            {
                "create_http_status",
                "anonymous_fetch_http_status",
                "scope",
                "share_token_sha256",
                "created_at_utc",
                "fetched_at_utc",
                "expires_at_utc",
                "revoke_http_status",
                "revoked_at_utc",
                "revoked_fetch_http_status",
            }
        ),
        "tenant_isolation": frozenset(
            {"foreign_audit_http_status", "foreign_packet_http_status", "verified_at_utc"}
        ),
    },
    "accounts_billing": {
        "account_session": frozenset(
            {
                "invite_redeem_http_status",
                "login_http_status",
                "logout_http_status",
                "revoked_session_http_status",
                "durable_session_restart_verified",
                "disabled_account_http_status",
                "cross_tenant_http_status",
                "verified_at_utc",
            }
        ),
        "quota": frozenset(
            {
                "monthly_limit",
                "usage_at_limit",
                "overflow_http_status",
                "overflow_error",
                "idempotent_retry_non_double_consuming",
                "adjacent_month_isolated",
                "shared_postgres_restart_verified",
                "verified_at_utc",
            }
        ),
        "billing": frozenset(
            {
                "provider",
                "mode",
                "currency",
                "checkout_status",
                "subscription_status",
                "invoice_status",
                "receipt_download_http_status",
                "webhook_signature_verified",
                "entitlement_status",
                "meter_to_invoice_reconciled",
                "provider_customer_id_sha256",
                "provider_subscription_id_sha256",
                "invoice_id_sha256",
                "paid_at_utc",
            }
        ),
    },
    "support_crm": {
        "support_ticket": frozenset(
            {
                "ticket_id_sha256",
                "create_http_status",
                "persisted",
                "routed",
                "acknowledged",
                "first_response_minutes",
                "sla_minutes",
                "resolution_recorded",
                "resolved_at_utc",
            }
        ),
        "crm_lead": frozenset(
            {
                "system",
                "lead_id_sha256",
                "persisted",
                "readback_verified",
                "deduplicated",
                "owner_assigned",
                "lifecycle_stage",
                "verified_at_utc",
            }
        ),
        "consent": frozenset(
            {
                "capture_consent_recorded",
                "source_attribution_recorded",
                "privacy_notice_linked",
                "recorded_at_utc",
            }
        ),
    },
    "incident_tabletop": {
        "incident": frozenset(
            {
                "record_id",
                "status",
                "closed_at_utc",
                "open_actions",
                "postmortem_uri",
                "postmortem_sha256",
                "credential_rotation_complete",
                "recovery_verified",
            }
        ),
        "tabletop": frozenset(
            {
                "tabletop_id",
                "completed_at_utc",
                "participant_roles",
                "scenarios",
                "open_actions",
                "evidence_uri",
                "evidence_sha256",
            }
        ),
    },
    "alert_delivery": {
        "alert": frozenset(
            {"alert_id_sha256", "severity", "emitted_at_utc", "source"}
        ),
        "acknowledgement": frozenset(
            {"status", "acknowledged_at_utc", "actor_role", "latency_seconds"}
        ),
        "escalation": frozenset(
            {
                "triggered",
                "delivered",
                "destination_role",
                "receipt_sha256",
                "delivered_at_utc",
            }
        ),
    },
    "claim_honesty": {
        "scan": frozenset(
            {
                "misleading_claim_count",
                "unsupported_compliance_claim_count",
                "unsupported_universality_claim_count",
                "status_vocabulary_exact",
            }
        ),
        "boundaries": frozenset(
            {
                "research_scope_disclosed",
                "research_accept_not_product_accept",
                "worm_retention_not_verdict_upgrade",
                "flag_for_human_review_not_accept",
                "compliance_certification_claims_absent",
                "rendered_product_status",
            }
        ),
    },
}

_LIST_OBJECT_FIELDS: dict[str, dict[str, frozenset[str]]] = {
    "legal_publication_approval": {
        "documents": frozenset(
            {
                "kind",
                "url",
                "http_status",
                "content_sha256",
                "published_at_utc",
                "verified_at_utc",
            }
        ),
        "approvals": frozenset(
            {"role", "approval_artifact_uri", "approval_sha256", "approved_at_utc"}
        ),
    },
    "alert_delivery": {
        "deliveries": frozenset(
            {"destination_role", "status", "delivered_at_utc", "receipt_sha256"}
        )
    },
    "claim_honesty": {
        "scanned_surfaces": frozenset(
            {"kind", "url", "http_status", "content_sha256", "verified_at_utc"}
        ),
        "approvals": frozenset(
            {"role", "approval_artifact_uri", "approval_sha256", "approved_at_utc"}
        ),
    },
}

_TOP_LEVEL_LIST_FIELDS: dict[str, frozenset[str]] = {
    "legal_publication_approval": frozenset({"claim_status_vocabulary"}),
    "release_decision": frozenset({"approver_roles"}),
}
_NESTED_LIST_FIELDS: dict[tuple[str, str], frozenset[str]] = {
    ("incident_tabletop", "tabletop"): frozenset({"participant_roles", "scenarios"})
}

_PROHIBITED_SECRET_FIELDS = frozenset(
    {
        "access_key",
        "api_key",
        "authorization",
        "bearer_token",
        "card_number",
        "client_secret",
        "cookie",
        "credential",
        "cvv",
        "password",
        "private_key",
        "secret",
        "secret_access_key",
        "session_cookie",
        "share_token",
        "token",
        "webhook_secret",
    }
)
_PROHIBITED_PII_FIELDS = frozenset(
    {
        "address",
        "customer_email",
        "email",
        "full_name",
        "ip_address",
        "name",
        "phone",
        "postal_address",
        "user_email",
    }
)
_SUSPICIOUS_PATTERNS = {
    "AWS access key": re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    "GitHub token": re.compile(
        r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"
    ),
    "JWT": re.compile(
        r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"
    ),
    "bearer credential": re.compile(
        r"(?i)Authorization\s*:\s*Bearer\s+[A-Za-z0-9._~-]{12,}"
    ),
    "Stripe secret": re.compile(
        r"\b(?:sk_(?:live|test)_[A-Za-z0-9]{12,}|whsec_[A-Za-z0-9]{12,})\b"
    ),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "email address": re.compile(
        r"(?i)(?<![A-Za-z0-9._%+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
    ),
}

_ALLOWED_URL_ORIGINS = frozenset(
    {
        PRODUCTION_API_ORIGIN,
        "https://atlas.noeticcompass.com",
        "https://cascompass.ai",
    }
)

_REVISION_KEYS = frozenset(
    {
        "schema_version",
        "gate",
        "evidence_sha256",
        "byte_length",
        "persisted_at_utc",
        "evidence_json",
        "storage",
    }
)
_STORAGE_KEYS = frozenset(
    {
        "mode",
        "object_key",
        "object_url",
        "version_id",
        "retain_until_utc",
        "receipt_sha256",
        "receipt_verification",
        "lock_mode",
        "retention_days",
    }
)
_HEAD_KEYS = frozenset(
    {
        "schema_version",
        "gate",
        "revision_record_id",
        "evidence_sha256",
        "active",
        "changed_at_utc",
        "operation_record_id",
        "operation_sha256",
    }
)
_OPERATION_KEYS = frozenset(
    {
        "schema_version",
        "gate",
        "action",
        "changed_at_utc",
        "previous",
        "next",
        "authorization",
    }
)
_OPERATION_PREVIOUS_KEYS = frozenset(
    {"head_version", "evidence_sha256", "active", "operation_record_id"}
)
_OPERATION_NEXT_KEYS = frozenset(
    {"head_version", "evidence_sha256", "active"}
)
_OPERATION_AUTHORIZATION_KEYS = frozenset(
    {"artifact_uri", "artifact_sha256", "reason"}
)
_PUBLISH_OPERATION_REASONS = frozenset({"authorized_publication"})
_DEACTIVATE_OPERATION_REASONS = frozenset(
    {
        "approval_withdrawn",
        "evidence_expired",
        "incident_response",
        "operator_safety_action",
    }
)
_API_ONLY_ORIGINS = frozenset({PRODUCTION_API_ORIGIN})
_API_LANDING_ORIGINS = frozenset({PRODUCTION_API_ORIGIN, LANDING_ORIGIN})


class ImmutableAcceptanceEvidenceBackend(Protocol):
    """Subset implemented by the existing S3 Object-Lock packet backend."""

    def assert_ready(self, *, expected: RetentionPolicy) -> None: ...

    def object_url(self, key: str, *, version_id: str | None = None) -> str: ...

    def put_immutable(
        self,
        *,
        key: str,
        body: bytes,
        content_hash: str,
        policy: RetentionPolicy,
    ) -> Any: ...

    def get_immutable(self, *, key: str, version_id: str) -> bytes: ...


class AcceptanceAuthorityError(RuntimeError):
    """Base class for authority persistence failures."""


class AcceptanceAuthorityNotFound(AcceptanceAuthorityError):
    """No active evidence revision exists for the requested gate."""


class AcceptanceAuthorityInvalid(AcceptanceAuthorityError):
    """Evidence is unsafe, malformed, stale, or outside the transport contract."""


class AcceptanceAuthorityUnavailable(AcceptanceAuthorityError):
    """A persisted head/revision/blob cannot be read with integrity."""


class AcceptanceAuthorityConflict(AcceptanceAuthorityError):
    """The publisher did not hold the current version of the gate head."""


@dataclass(frozen=True, slots=True)
class AcceptanceEvidenceDocument:
    gate: str
    sha256: str
    body: bytes


@dataclass(frozen=True, slots=True)
class PublishedAcceptanceEvidence:
    gate: str
    sha256: str
    head_version: int
    storage_mode: str
    operation_record_id: str
    operation_sha256: str


@dataclass(frozen=True, slots=True)
class DeactivatedAcceptanceEvidence:
    gate: str
    sha256: str
    head_version: int
    already_inactive: bool
    operation_record_id: str
    operation_sha256: str


@dataclass(frozen=True, slots=True)
class AcceptanceAuthorityHead:
    gate: str
    sha256: str
    head_version: int
    active: bool
    operation_record_id: str
    operation_sha256: str


class CustomerProductionAcceptanceAuthorityStore:
    """Content-addressed revisions and CAS-updated heads over ``StateStore``."""

    def __init__(
        self,
        store: StateStore,
        *,
        immutable_backend: ImmutableAcceptanceEvidenceBackend | None = None,
        retention_policy: RetentionPolicy | None = None,
    ) -> None:
        if (immutable_backend is None) != (retention_policy is None):
            raise ValueError(
                "immutable_backend and retention_policy must be configured together"
            )
        self._store = store
        self._immutable_backend = immutable_backend
        self._retention_policy = retention_policy

    def current_head(self, gate: str) -> AcceptanceAuthorityHead | None:
        """Return the validated active-or-tombstoned head, or ``None``."""

        _require_gate(gate)
        try:
            head = self._store.get(
                AUTHORITY_TENANT_ID, HEAD_KIND, _head_record_id(gate)
            )
        except Exception as exc:
            raise AcceptanceAuthorityUnavailable(
                "acceptance authority state store is unavailable"
            ) from exc
        if head is None:
            return None
        payload = _validate_head(head.payload, gate)
        operation_record_id = str(payload["operation_record_id"])
        operation_sha256 = str(payload["operation_sha256"])
        operation = self._operation_payload(
            gate,
            operation_record_id,
            operation_sha256,
        )
        _validate_head_operation_binding(
            payload,
            operation,
            head_version=head.version,
        )
        if (
            head.source != "customer_production_acceptance_authority"
            or head.trace_id != payload["evidence_sha256"]
            or head.parent_ids
            != (str(payload["revision_record_id"]), operation_record_id)
        ):
            raise AcceptanceAuthorityUnavailable(
                "acceptance authority head traceability is invalid"
            )
        self._validate_operation_chain(
            gate=gate,
            operation_record_id=operation_record_id,
            operation=operation,
            head_version=head.version,
        )
        return AcceptanceAuthorityHead(
            gate=gate,
            sha256=str(payload["evidence_sha256"]),
            head_version=head.version,
            active=bool(payload["active"]),
            operation_record_id=operation_record_id,
            operation_sha256=operation_sha256,
        )

    def current_head_version(self, gate: str) -> int:
        """Return 0 for an absent head, otherwise its validated StateStore version."""

        head = self.current_head(gate)
        return 0 if head is None else head.head_version

    def _operation_payload(
        self,
        gate: str,
        operation_record_id: str,
        expected_digest: str,
    ) -> Mapping[str, Any]:
        try:
            operation = self._store.get(
                AUTHORITY_TENANT_ID,
                OPERATION_KIND,
                operation_record_id,
            )
        except Exception as exc:
            raise AcceptanceAuthorityUnavailable(
                "acceptance authority operation store is unavailable"
            ) from exc
        if operation is None:
            raise AcceptanceAuthorityUnavailable(
                "acceptance authority operation record is missing"
            )
        payload = _validate_operation(
            operation.payload,
            gate=gate,
            operation_record_id=operation_record_id,
            expected_digest=expected_digest,
        )
        previous = payload["previous"]
        assert isinstance(previous, Mapping)
        expected_parents = (
            ()
            if previous["operation_record_id"] is None
            else (str(previous["operation_record_id"]),)
        )
        if (
            operation.version != 1
            or operation.source != "customer_production_acceptance_authority"
            or operation.trace_id != expected_digest
            or operation.parent_ids != expected_parents
        ):
            raise AcceptanceAuthorityUnavailable(
                "acceptance authority operation traceability is invalid"
            )
        return payload

    def _validate_operation_chain(
        self,
        *,
        gate: str,
        operation_record_id: str,
        operation: Mapping[str, Any],
        head_version: int,
    ) -> None:
        """Validate every bound predecessor exactly once back to version zero."""

        if head_version < 1:
            raise AcceptanceAuthorityUnavailable(
                "acceptance authority head version is invalid"
            )
        seen = {operation_record_id}
        cursor = operation
        expected_next_version = head_version
        for _ in range(head_version):
            next_head = cursor["next"]
            previous = cursor["previous"]
            assert isinstance(next_head, Mapping)
            assert isinstance(previous, Mapping)
            if next_head["head_version"] != expected_next_version:
                raise AcceptanceAuthorityUnavailable(
                    "acceptance authority operation chain version is invalid"
                )
            if expected_next_version == 1:
                if (
                    previous["head_version"] != 0
                    or previous["operation_record_id"] is not None
                ):
                    raise AcceptanceAuthorityUnavailable(
                        "acceptance authority operation chain root is invalid"
                    )
                return

            previous_record_id = str(previous["operation_record_id"])
            if previous_record_id in seen:
                raise AcceptanceAuthorityUnavailable(
                    "acceptance authority operation chain contains a cycle"
                )
            seen.add(previous_record_id)
            previous_digest = _operation_digest_from_record_id(
                gate, previous_record_id
            )
            prior_operation = self._operation_payload(
                gate,
                previous_record_id,
                previous_digest,
            )
            prior_next = prior_operation["next"]
            assert isinstance(prior_next, Mapping)
            if (
                prior_next["head_version"] != previous["head_version"]
                or prior_next["evidence_sha256"]
                != previous["evidence_sha256"]
                or prior_next["active"] is not previous["active"]
            ):
                raise AcceptanceAuthorityUnavailable(
                    "acceptance authority operation chain is invalid"
                )
            cursor = prior_operation
            expected_next_version -= 1

        raise AcceptanceAuthorityUnavailable(
            "acceptance authority operation chain is incomplete"
        )

    def _append_operation(
        self,
        *,
        gate: str,
        action: str,
        current_head: AcceptanceAuthorityHead | None,
        next_sha256: str,
        next_active: bool,
        authorization_artifact_uri: str,
        authorization_artifact_sha256: str,
        operation_reason: str,
        now: datetime,
    ) -> tuple[str, str]:
        _validate_operation_authorization(
            action=action,
            artifact_uri=authorization_artifact_uri,
            artifact_sha256=authorization_artifact_sha256,
            reason=operation_reason,
        )
        previous_version = 0 if current_head is None else current_head.head_version
        payload = {
            "schema_version": OPERATION_SCHEMA_VERSION,
            "gate": gate,
            "action": action,
            "changed_at_utc": _format_utc(now),
            "previous": {
                "head_version": previous_version,
                "evidence_sha256": (
                    None if current_head is None else current_head.sha256
                ),
                "active": None if current_head is None else current_head.active,
                "operation_record_id": (
                    None
                    if current_head is None
                    else current_head.operation_record_id
                ),
            },
            "next": {
                "head_version": previous_version + 1,
                "evidence_sha256": next_sha256,
                "active": next_active,
            },
            "authorization": {
                "artifact_uri": authorization_artifact_uri,
                "artifact_sha256": authorization_artifact_sha256,
                "reason": operation_reason,
            },
        }
        canonical = _canonical_json_bytes(payload)
        digest = hashlib.sha256(canonical).hexdigest()
        record_id = _operation_record_id(gate, digest)
        operation = LedgerRecord.new(
            tenant_id=AUTHORITY_TENANT_ID,
            kind=OPERATION_KIND,
            record_id=record_id,
            payload=payload,
            parent_ids=(
                ()
                if current_head is None
                else (current_head.operation_record_id,)
            ),
            source="customer_production_acceptance_authority",
            trace_id=digest,
            now=now,
        )
        try:
            stored = self._store.put(operation, expected_version=0)
        except VersionConflict:
            existing = self._operation_payload(gate, record_id, digest)
            if _canonical_json_bytes(existing) != canonical:
                raise AcceptanceAuthorityUnavailable(
                    "content-addressed acceptance operation conflicted"
                )
        except Exception as exc:
            raise AcceptanceAuthorityUnavailable(
                "acceptance authority operation persistence failed"
            ) from exc
        else:
            if stored.version != 1:
                raise AcceptanceAuthorityUnavailable(
                    "acceptance authority operation version is invalid"
                )
            _validate_operation(
                stored.payload,
                gate=gate,
                operation_record_id=record_id,
                expected_digest=digest,
            )
        return record_id, digest

    def _revision_payload(
        self,
        gate: str,
        revision_id: str,
        digest: str,
        *,
        required: bool,
    ) -> Mapping[str, Any] | None:
        try:
            revision = self._store.get(
                AUTHORITY_TENANT_ID, REVISION_KIND, revision_id
            )
        except Exception as exc:
            raise AcceptanceAuthorityUnavailable(
                "acceptance authority revision store is unavailable"
            ) from exc
        if revision is None:
            if required:
                raise AcceptanceAuthorityUnavailable(
                    "active acceptance revision is missing"
                )
            return None
        payload = _validate_revision(
            revision.payload,
            gate=gate,
            revision_id=revision_id,
            expected_digest=digest,
        )
        if (
            revision.version != 1
            or revision.source != "customer_production_acceptance_authority"
            or revision.trace_id != digest
            or revision.parent_ids != ()
        ):
            raise AcceptanceAuthorityUnavailable(
                "acceptance authority revision traceability is invalid"
            )
        return payload

    def _revision_body(self, payload: Mapping[str, Any]) -> bytes:
        storage = payload["storage"]
        assert isinstance(storage, Mapping)
        if storage["mode"] == "state_store":
            evidence_json = payload["evidence_json"]
            if not isinstance(evidence_json, str):
                raise AcceptanceAuthorityUnavailable(
                    "inline acceptance evidence bytes are unavailable"
                )
            try:
                return evidence_json.encode("ascii")
            except UnicodeEncodeError as exc:
                raise AcceptanceAuthorityUnavailable(
                    "inline acceptance evidence is not canonical ASCII JSON"
                ) from exc

        if self._immutable_backend is None:
            raise AcceptanceAuthorityUnavailable(
                "active acceptance evidence requires its immutable backend"
            )
        key = storage.get("object_key")
        version_id = storage.get("version_id")
        if not isinstance(key, str) or not isinstance(version_id, str):
            raise AcceptanceAuthorityUnavailable(
                "immutable acceptance evidence pointer is invalid"
            )
        try:
            return self._immutable_backend.get_immutable(
                key=key, version_id=version_id
            )
        except Exception as exc:
            raise AcceptanceAuthorityUnavailable(
                "immutable acceptance evidence re-read failed"
            ) from exc

    def _assert_revision_storage_policy(
        self,
        payload: Mapping[str, Any],
        *,
        now: datetime,
        check_backend_readiness: bool = True,
    ) -> None:
        storage = payload["storage"]
        assert isinstance(storage, Mapping)
        expected_mode = (
            "worm" if self._immutable_backend is not None else "state_store"
        )
        if storage["mode"] != expected_mode:
            raise AcceptanceAuthorityUnavailable(
                "acceptance revision storage does not match the current "
                "immutable policy"
            )
        if expected_mode == "state_store":
            return

        assert self._immutable_backend is not None
        assert self._retention_policy is not None
        verification_payload = storage.get("receipt_verification")
        if not isinstance(verification_payload, Mapping):
            raise AcceptanceAuthorityUnavailable(
                "immutable acceptance receipt verification is unavailable"
            )
        expected = verification_payload.get("expected")
        if not isinstance(expected, Mapping):
            raise AcceptanceAuthorityUnavailable(
                "immutable acceptance receipt expectation is unavailable"
            )
        object_key = str(storage.get("object_key"))
        version_id = str(storage.get("version_id"))
        try:
            canonical_object_url = self._immutable_backend.object_url(
                object_key,
                version_id=version_id,
            )
        except Exception as exc:
            raise AcceptanceAuthorityUnavailable(
                "immutable acceptance object identity is unavailable"
            ) from exc
        if canonical_object_url != storage.get("object_url"):
            raise AcceptanceAuthorityUnavailable(
                "immutable acceptance object URL is not canonical"
            )
        receipt_bucket, receipt_key, receipt_version = _parse_s3_object_url(
            canonical_object_url
        )
        if (
            storage.get("lock_mode") != self._retention_policy.mode
            or storage.get("retention_days")
            != self._retention_policy.retention_days
            or expected.get("mode") != self._retention_policy.mode
            or expected.get("retention_days")
            != self._retention_policy.retention_days
            or expected.get("content_sha256") != payload["evidence_sha256"]
            or expected.get("bucket") != receipt_bucket
            or expected.get("key") != receipt_key
            or expected.get("version_id") != receipt_version
            or receipt_version != version_id
        ):
            raise AcceptanceAuthorityUnavailable(
                "immutable acceptance receipt does not match the current policy"
            )
        if _parse_iso_utc_unavailable(
            expected.get("retain_until"), "receipt retention timestamp"
        ) != _parse_utc_unavailable(
            storage.get("retain_until_utc"), "WORM retention timestamp"
        ):
            raise AcceptanceAuthorityUnavailable(
                "immutable acceptance receipt retention is inconsistent"
            )
        if check_backend_readiness:
            try:
                self._immutable_backend.assert_ready(expected=self._retention_policy)
            except Exception as exc:
                raise AcceptanceAuthorityUnavailable(
                    "immutable acceptance backend readiness failed"
                ) from exc
        verification = revalidate_object_lock_verification(
            verification_payload,
            expected=expected,
            evaluated_at=now,
        )
        if verification is None or not verification.verified:
            raise AcceptanceAuthorityUnavailable(
                "immutable acceptance receipt revalidation failed"
            )

    @staticmethod
    def _verify_revision_bytes(
        payload: Mapping[str, Any], body: bytes, *, expected: bytes | None = None
    ) -> None:
        expected_length = payload["byte_length"]
        expected_hash = str(payload["evidence_sha256"])
        if not isinstance(expected_length, int) or len(body) != expected_length:
            raise AcceptanceAuthorityUnavailable(
                "acceptance evidence byte length does not match its durable revision"
            )
        if hashlib.sha256(body).hexdigest() != expected_hash:
            raise AcceptanceAuthorityUnavailable(
                "acceptance evidence bytes do not match their durable revision"
            )
        if expected is not None and body != expected:
            raise AcceptanceAuthorityUnavailable(
                "content-addressed acceptance revision bytes conflicted"
            )

    def publish(
        self,
        gate: str,
        evidence: Mapping[str, Any],
        *,
        expected_head_version: int,
        expected_previous_sha256: str | None,
        authorization_artifact_uri: str,
        authorization_artifact_sha256: str,
        operation_reason: str,
        now: datetime | None = None,
    ) -> PublishedAcceptanceEvidence:
        """Persist one independently collected evidence document.

        This method does not collect or infer evidence.  Callers must supply the
        complete canonical verifier payload and the exact head version they
        previously read.  That compare-and-swap requirement prevents a stale
        publisher from silently replacing another collector's revision.
        """

        _require_gate(gate)
        if (
            not isinstance(expected_head_version, int)
            or isinstance(expected_head_version, bool)
            or expected_head_version < 0
        ):
            raise ValueError("expected_head_version must be a non-negative integer")
        if expected_head_version == 0:
            if expected_previous_sha256 is not None:
                raise ValueError(
                    "expected_previous_sha256 must be absent for an absent head"
                )
        elif not _is_sha256(expected_previous_sha256):
            raise ValueError(
                "expected_previous_sha256 is required for an existing head"
            )
        current_head = self.current_head(gate)
        if expected_head_version == 0:
            if current_head is not None:
                raise AcceptanceAuthorityConflict(
                    "acceptance authority head changed; re-read before publishing"
                )
        elif (
            current_head is None
            or current_head.head_version != expected_head_version
            or current_head.sha256 != expected_previous_sha256
        ):
            raise AcceptanceAuthorityConflict(
                "acceptance authority head changed; re-read before publishing"
            )
        _validate_operation_authorization(
            action="publish",
            artifact_uri=authorization_artifact_uri,
            artifact_sha256=authorization_artifact_sha256,
            reason=operation_reason,
        )
        stamp = _utc_now(now)
        canonical = canonicalize_acceptance_evidence(
            gate, evidence, now=stamp
        )
        digest = hashlib.sha256(canonical).hexdigest()
        revision_id = _revision_record_id(gate, digest)
        revision_payload = self._revision_payload(
            gate, revision_id, digest, required=False
        )
        if revision_payload is not None:
            storage = revision_payload["storage"]
            assert isinstance(storage, Mapping)
            self._assert_revision_storage_policy(revision_payload, now=stamp)
            body = self._revision_body(revision_payload)
            self._verify_revision_bytes(revision_payload, body, expected=canonical)
        else:
            evidence_json: str | None
            if self._immutable_backend is None:
                evidence_json = canonical.decode("ascii")
                storage = {
                    "mode": "state_store",
                    "object_key": None,
                    "object_url": None,
                    "version_id": None,
                    "retain_until_utc": None,
                    "receipt_sha256": None,
                    "receipt_verification": None,
                    "lock_mode": None,
                    "retention_days": None,
                }
            else:
                assert self._retention_policy is not None
                key = f"customer-production-authority/{gate}/{digest}.json"
                try:
                    self._immutable_backend.assert_ready(
                        expected=self._retention_policy
                    )
                    receipt = self._immutable_backend.put_immutable(
                        key=key,
                        body=canonical,
                        content_hash=digest,
                        policy=self._retention_policy,
                    )
                except Exception as exc:
                    raise AcceptanceAuthorityUnavailable(
                        "immutable acceptance evidence write failed"
                    ) from exc
                if not bool(getattr(receipt, "is_verifiable", lambda: False)()):
                    raise AcceptanceAuthorityUnavailable(
                        "immutable acceptance evidence write lacked a verified receipt"
                    )
                verification = getattr(
                    receipt, "validated_verification", lambda: None
                )()
                if verification is None or not bool(
                    getattr(verification, "verified", False)
                ):
                    raise AcceptanceAuthorityUnavailable(
                        "immutable acceptance evidence receipt is invalid"
                    )
                verification_payload = verification.to_dict()
                receipt_body = _canonical_json_bytes(verification_payload)
                evidence_json = None
                storage = {
                    "mode": "worm",
                    "object_key": key,
                    "object_url": str(receipt.object_url),
                    "version_id": str(receipt.version_id),
                    "retain_until_utc": _format_utc(receipt.retain_until),
                    "receipt_sha256": hashlib.sha256(receipt_body).hexdigest(),
                    "receipt_verification": verification_payload,
                    "lock_mode": self._retention_policy.mode,
                    "retention_days": self._retention_policy.retention_days,
                }

            revision_payload = {
                "schema_version": RECORD_SCHEMA_VERSION,
                "gate": gate,
                "evidence_sha256": digest,
                "byte_length": len(canonical),
                "persisted_at_utc": _format_utc(stamp),
                "evidence_json": evidence_json,
                "storage": storage,
            }
            self._assert_revision_storage_policy(
                revision_payload,
                now=stamp,
                check_backend_readiness=False,
            )
            revision = LedgerRecord.new(
                tenant_id=AUTHORITY_TENANT_ID,
                kind=REVISION_KIND,
                record_id=revision_id,
                payload=revision_payload,
                source="customer_production_acceptance_authority",
                trace_id=digest,
                now=stamp,
            )
            try:
                self._store.put(revision, expected_version=0)
            except VersionConflict:
                # Another publisher may have stored these exact content-addressed
                # bytes after our initial read. Re-read and compare the bytes,
                # not its call-time persistence timestamp or WORM version.
                revision_payload = self._revision_payload(
                    gate, revision_id, digest, required=True
                )
                assert revision_payload is not None
                storage = revision_payload["storage"]
                assert isinstance(storage, Mapping)
                self._assert_revision_storage_policy(
                    revision_payload, now=stamp
                )
                body = self._revision_body(revision_payload)
                self._verify_revision_bytes(
                    revision_payload, body, expected=canonical
                )
            except Exception as exc:
                raise AcceptanceAuthorityUnavailable(
                    "acceptance revision persistence failed"
                ) from exc

        operation_record_id, operation_sha256 = self._append_operation(
            gate=gate,
            action="publish",
            current_head=current_head,
            next_sha256=digest,
            next_active=True,
            authorization_artifact_uri=authorization_artifact_uri,
            authorization_artifact_sha256=authorization_artifact_sha256,
            operation_reason=operation_reason,
            now=stamp,
        )
        head_payload = {
            "schema_version": HEAD_SCHEMA_VERSION,
            "gate": gate,
            "revision_record_id": revision_id,
            "evidence_sha256": digest,
            "active": True,
            "changed_at_utc": _format_utc(stamp),
            "operation_record_id": operation_record_id,
            "operation_sha256": operation_sha256,
        }
        head = LedgerRecord.new(
            tenant_id=AUTHORITY_TENANT_ID,
            kind=HEAD_KIND,
            record_id=_head_record_id(gate),
            payload=head_payload,
            parent_ids=(revision_id, operation_record_id),
            source="customer_production_acceptance_authority",
            trace_id=digest,
            now=stamp,
        )
        try:
            stored_head = self._store.put(
                head, expected_version=expected_head_version
            )
        except VersionConflict as exc:
            raise AcceptanceAuthorityConflict(
                "acceptance authority head changed; re-read before publishing"
            ) from exc
        except Exception as exc:
            raise AcceptanceAuthorityUnavailable(
                "acceptance authority head persistence failed"
            ) from exc
        return PublishedAcceptanceEvidence(
            gate=gate,
            sha256=digest,
            head_version=stored_head.version,
            storage_mode=str(storage["mode"]),
            operation_record_id=operation_record_id,
            operation_sha256=operation_sha256,
        )

    def deactivate(
        self,
        gate: str,
        *,
        expected_head_version: int,
        expected_evidence_sha256: str,
        authorization_artifact_uri: str,
        authorization_artifact_sha256: str,
        operation_reason: str,
        now: datetime | None = None,
    ) -> DeactivatedAcceptanceEvidence:
        """CAS-tombstone an active head while retaining its immutable revision."""

        _require_gate(gate)
        if (
            not isinstance(expected_head_version, int)
            or isinstance(expected_head_version, bool)
            or expected_head_version <= 0
        ):
            raise ValueError("expected_head_version must be a positive integer")
        if not _is_sha256(expected_evidence_sha256):
            raise ValueError("expected_evidence_sha256 must be a SHA-256 digest")
        _validate_operation_authorization(
            action="deactivate",
            artifact_uri=authorization_artifact_uri,
            artifact_sha256=authorization_artifact_sha256,
            reason=operation_reason,
        )
        current = self.current_head(gate)
        if (
            current is None
            or current.head_version != expected_head_version
            or current.sha256 != expected_evidence_sha256
        ):
            raise AcceptanceAuthorityConflict(
                "acceptance authority head changed; re-read before deactivation"
            )
        if not current.active:
            return DeactivatedAcceptanceEvidence(
                gate=gate,
                sha256=current.sha256,
                head_version=current.head_version,
                already_inactive=True,
                operation_record_id=current.operation_record_id,
                operation_sha256=current.operation_sha256,
            )

        stamp = _utc_now(now)
        operation_record_id, operation_sha256 = self._append_operation(
            gate=gate,
            action="deactivate",
            current_head=current,
            next_sha256=current.sha256,
            next_active=False,
            authorization_artifact_uri=authorization_artifact_uri,
            authorization_artifact_sha256=authorization_artifact_sha256,
            operation_reason=operation_reason,
            now=stamp,
        )
        payload = {
            "schema_version": HEAD_SCHEMA_VERSION,
            "gate": gate,
            "revision_record_id": _revision_record_id(gate, current.sha256),
            "evidence_sha256": current.sha256,
            "active": False,
            "changed_at_utc": _format_utc(stamp),
            "operation_record_id": operation_record_id,
            "operation_sha256": operation_sha256,
        }
        tombstone = LedgerRecord.new(
            tenant_id=AUTHORITY_TENANT_ID,
            kind=HEAD_KIND,
            record_id=_head_record_id(gate),
            payload=payload,
            parent_ids=(
                _revision_record_id(gate, current.sha256),
                operation_record_id,
            ),
            source="customer_production_acceptance_authority",
            trace_id=current.sha256,
            now=stamp,
        )
        try:
            stored = self._store.put(
                tombstone, expected_version=expected_head_version
            )
        except VersionConflict as exc:
            raise AcceptanceAuthorityConflict(
                "acceptance authority head changed; re-read before deactivation"
            ) from exc
        except Exception as exc:
            raise AcceptanceAuthorityUnavailable(
                "acceptance authority deactivation failed"
            ) from exc
        return DeactivatedAcceptanceEvidence(
            gate=gate,
            sha256=current.sha256,
            head_version=stored.version,
            already_inactive=False,
            operation_record_id=operation_record_id,
            operation_sha256=operation_sha256,
        )

    def load(
        self, gate: str, *, now: datetime | None = None
    ) -> AcceptanceEvidenceDocument:
        """Load and revalidate the exact active bytes for ``gate``."""

        _require_gate(gate)
        stamp = _utc_now(now)
        head = self.current_head(gate)
        if head is None:
            raise AcceptanceAuthorityNotFound("acceptance evidence is absent")
        if head.active is not True:
            raise AcceptanceAuthorityNotFound("acceptance evidence is inactive")
        revision_id = _revision_record_id(gate, head.sha256)
        expected_hash = head.sha256
        payload = self._revision_payload(
            gate, revision_id, expected_hash, required=True
        )
        assert payload is not None
        self._assert_revision_storage_policy(payload, now=stamp)
        body = self._revision_body(payload)
        self._verify_revision_bytes(payload, body)
        try:
            document = json.loads(body.decode("ascii"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AcceptanceAuthorityUnavailable(
                "acceptance evidence is not canonical JSON"
            ) from exc
        if not isinstance(document, Mapping):
            raise AcceptanceAuthorityUnavailable(
                "acceptance evidence root is not an object"
            )
        canonical = _validated_canonical_evidence(document, gate=gate, now=stamp)
        if canonical != body:
            raise AcceptanceAuthorityUnavailable(
                "acceptance evidence bytes are not canonical"
            )
        return AcceptanceEvidenceDocument(
            gate=gate, sha256=expected_hash, body=body
        )


def canonicalize_acceptance_evidence(
    gate: str,
    evidence: Mapping[str, Any],
    *,
    now: datetime | None = None,
) -> bytes:
    """Validate one authority document and return its exact canonical bytes.

    Operational publishers use this public seam to hash and pin the bytes before
    they open a production StateStore connection.  It intentionally applies the
    same structural, freshness, public-production, secret/PII, and gate-semantic
    checks used by :meth:`CustomerProductionAcceptanceAuthorityStore.publish` and
    :meth:`CustomerProductionAcceptanceAuthorityStore.load`.
    """

    _require_gate(gate)
    return _validated_canonical_evidence(evidence, gate=gate, now=_utc_now(now))


def _validated_canonical_evidence(
    evidence: Mapping[str, Any], *, gate: str, now: datetime
) -> bytes:
    _validate_structure(evidence, gate)
    if evidence.get("schema_version") != EVIDENCE_SCHEMA_VERSION:
        raise AcceptanceAuthorityInvalid("unexpected evidence schema version")
    if evidence.get("gate") != gate:
        raise AcceptanceAuthorityInvalid("evidence gate does not match route")
    if evidence.get("environment") != ENVIRONMENT:
        raise AcceptanceAuthorityInvalid("evidence is not public-production")
    if evidence.get("repository") != REPOSITORY:
        raise AcceptanceAuthorityInvalid("evidence repository is not canonical")
    if not _is_sha1(evidence.get("master_head_sha")):
        raise AcceptanceAuthorityInvalid("master_head_sha is invalid")
    deploy_id = evidence.get("deploy_id")
    if not isinstance(deploy_id, str) or _DEPLOY_ID_RE.fullmatch(deploy_id) is None:
        raise AcceptanceAuthorityInvalid("deploy_id is invalid")
    expected_uri = acceptance_authority_url(gate)
    if evidence.get("artifact_uri") != expected_uri:
        raise AcceptanceAuthorityInvalid(
            "artifact_uri does not match the exact gate authority endpoint"
        )
    if not _is_sha256(evidence.get("artifact_sha256")):
        raise AcceptanceAuthorityInvalid("artifact_sha256 is invalid")

    event = _parse_utc(evidence.get("event_at_utc"), "event_at_utc")
    observed = _parse_utc(evidence.get("observed_at_utc"), "observed_at_utc")
    if event > observed:
        raise AcceptanceAuthorityInvalid("event_at_utc is after observed_at_utc")
    if event > now or observed > now:
        raise AcceptanceAuthorityInvalid("evidence timestamp is in the future")
    freshness = _FRESHNESS_MINUTES.get(gate)
    if freshness is not None:
        maximum_age = timedelta(minutes=freshness)
        if now - event > maximum_age or now - observed > maximum_age:
            raise AcceptanceAuthorityInvalid("acceptance evidence is stale")

    _validate_gate_semantics(
        evidence,
        gate=gate,
        event=event,
        observed=observed,
        now=now,
    )
    _scan_safe_values(evidence)
    serialized = json.dumps(evidence, sort_keys=True).lower()
    if "srv-d9akoolaeets73bp3e7g" in serialized or "accounts-canary" in serialized:
        raise AcceptanceAuthorityInvalid(
            "private-canary evidence cannot be public authority"
        )
    canonical = _canonical_json_bytes(evidence)
    if len(canonical) > MAX_EVIDENCE_BYTES:
        raise AcceptanceAuthorityInvalid("acceptance evidence exceeds size limit")
    return canonical


def _validate_structure(evidence: Mapping[str, Any], gate: str) -> None:
    expected = _COMMON_FIELDS | _EXTRA_FIELDS[gate]
    if set(evidence) != expected:
        raise AcceptanceAuthorityInvalid(
            "acceptance evidence top-level fields do not match the gate schema"
        )
    object_specs = _OBJECT_FIELDS.get(gate, {})
    list_specs = _LIST_OBJECT_FIELDS.get(gate, {})
    top_lists = _TOP_LEVEL_LIST_FIELDS.get(gate, frozenset())
    structured = set(object_specs) | set(list_specs) | set(top_lists)

    for field, expected_keys in object_specs.items():
        value = evidence.get(field)
        if not isinstance(value, Mapping) or set(value) != expected_keys:
            raise AcceptanceAuthorityInvalid(
                f"{field} does not match its exact object schema"
            )
        nested_lists = _NESTED_LIST_FIELDS.get((gate, field), frozenset())
        for child_key, child in value.items():
            if child_key in nested_lists:
                _require_scalar_list(child, f"{field}.{child_key}")
            elif not _is_json_scalar(child):
                raise AcceptanceAuthorityInvalid(
                    f"{field}.{child_key} must be a JSON scalar"
                )

    for field, expected_keys in list_specs.items():
        value = evidence.get(field)
        if not isinstance(value, list):
            raise AcceptanceAuthorityInvalid(f"{field} must be an array")
        for index, child in enumerate(value):
            if not isinstance(child, Mapping) or set(child) != expected_keys:
                raise AcceptanceAuthorityInvalid(
                    f"{field}[{index}] does not match its exact object schema"
                )
            if any(not _is_json_scalar(item) for item in child.values()):
                raise AcceptanceAuthorityInvalid(
                    f"{field}[{index}] values must be JSON scalars"
                )

    for field in top_lists:
        _require_scalar_list(evidence.get(field), field)

    for field, value in evidence.items():
        if field not in structured and not _is_json_scalar(value):
            raise AcceptanceAuthorityInvalid(f"{field} must be a JSON scalar")


def _require_scalar_list(value: Any, path: str) -> None:
    if not isinstance(value, list) or any(not _is_json_scalar(item) for item in value):
        raise AcceptanceAuthorityInvalid(f"{path} must be an array of JSON scalars")


def _is_json_scalar(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def _validate_gate_semantics(
    evidence: Mapping[str, Any],
    *,
    gate: str,
    event: datetime,
    observed: datetime,
    now: datetime,
) -> None:
    if gate == "runtime_worm":
        _validate_runtime_worm_semantics(evidence, event, observed, now)
    elif gate == "hosted_customer_journey":
        _validate_customer_journey_semantics(evidence, event, observed, now)
    elif gate == "accounts_billing":
        _validate_accounts_billing_semantics(evidence, event, observed, now)
    elif gate == "legal_publication_approval":
        _validate_legal_semantics(evidence, event, observed, now)
    elif gate == "support_crm":
        _validate_support_crm_semantics(evidence, event, observed, now)
    elif gate == "incident_tabletop":
        _validate_incident_tabletop_semantics(evidence, event, observed, now)
    elif gate == "alert_delivery":
        _validate_alert_delivery_semantics(evidence, event, observed, now)
    elif gate == "claim_honesty":
        _validate_claim_honesty_semantics(evidence, event, observed, now)
    elif gate == "release_decision":
        _validate_release_decision_semantics(evidence, event, observed, now)
    else:  # pragma: no cover - guarded by _require_gate
        raise AcceptanceAuthorityInvalid("unsupported acceptance authority gate")


def _validate_runtime_worm_semantics(
    evidence: Mapping[str, Any],
    event: datetime,
    observed: datetime,
    now: datetime,
) -> None:
    _equal(evidence, "api_base_url", PRODUCTION_API_ORIGIN)
    deployment = _object(evidence, "deployment")
    for field, expected in {
        "service_id": PRODUCTION_SERVICE_ID,
        "service_name": PRODUCTION_SERVICE_NAME,
        "service_type": "web_service",
        "branch": "master",
        "deploy_id": evidence["deploy_id"],
        "commit_sha": evidence["master_head_sha"],
        "status": "live",
    }.items():
        _equal(deployment, field, expected, "deployment")
    _proof_time(
        deployment["deployed_at_utc"],
        "runtime_worm",
        event,
        observed,
        now,
        "deployment.deployed_at_utc",
    )

    readiness = _object(evidence, "readiness")
    for field, expected in {
        "path": "/health/ready",
        "http_status": 200,
        "ready": True,
        "status": "ok",
        "authority": "verified",
    }.items():
        _equal(readiness, field, expected, "readiness")
    _proof_time(
        readiness["verified_at_utc"],
        "runtime_worm",
        event,
        observed,
        now,
        "readiness.verified_at_utc",
    )

    worker = _object(evidence, "worker")
    for field, expected in {
        "path": "/atlas/live/health/realmode",
        "http_status": 200,
        "verdict": EXPECTED_REALMODE_VERDICT,
        "is_real_model": True,
        "fake_runtime_env": False,
        "model_loaded": True,
        "load_error": None,
        "manifest_is_real_model": True,
        "model_id": EXPECTED_MODEL_ID,
    }.items():
        _equal(worker, field, expected, "worker")
    _nonempty(worker["worker_id"], "worker.worker_id")
    _proof_time(
        worker["verified_at_utc"],
        "runtime_worm",
        event,
        observed,
        now,
        "worker.verified_at_utc",
    )

    worm = _object(evidence, "worm")
    for field, expected in {
        "status": "ok",
        "authority": "verified",
        "write_verified": True,
        "readback_verified": True,
    }.items():
        _equal(worm, field, expected, "worm")
    configured_days = _positive_int(
        worm["configured_retention_days"], "worm.configured_retention_days"
    )
    if configured_days < 31:
        raise AcceptanceAuthorityInvalid(
            "worm.configured_retention_days must be at least 31"
        )
    if worm["object_lock_mode"] not in {"GOVERNANCE", "COMPLIANCE"}:
        raise AcceptanceAuthorityInvalid("worm.object_lock_mode is invalid")
    probe_id = worm["probe_id"]
    if not isinstance(probe_id, str) or _PROBE_ID_RE.fullmatch(probe_id) is None:
        raise AcceptanceAuthorityInvalid("worm.probe_id is invalid")
    for field in ("object_key_sha256", "version_id_sha256", "receipt_sha256"):
        _sha_value(worm[field], f"worm.{field}")
    written = _proof_time(
        worm["written_at_utc"],
        "runtime_worm",
        event,
        observed,
        now,
        "worm.written_at_utc",
    )
    verified = _proof_time(
        worm["verified_at_utc"],
        "runtime_worm",
        event,
        observed,
        now,
        "worm.verified_at_utc",
    )
    if written > verified:
        raise AcceptanceAuthorityInvalid("worm verification precedes its write")
    retention = _parse_utc(worm["retention_until_utc"], "worm.retention_until_utc")
    if retention - written < timedelta(days=configured_days):
        raise AcceptanceAuthorityInvalid("worm retention window is too short")
    if retention - now < timedelta(days=30):
        raise AcceptanceAuthorityInvalid("worm retention has less than 30 days remaining")


def _validate_customer_journey_semantics(
    evidence: Mapping[str, Any],
    event: datetime,
    observed: datetime,
    now: datetime,
) -> None:
    for field, expected in {
        "app_url": f"{PRODUCTION_APP_ORIGIN}/audit-console",
        "api_base_url": PRODUCTION_API_ORIGIN,
        "service_id": PRODUCTION_SERVICE_ID,
        "customer_lane": "public-customer",
    }.items():
        _equal(evidence, field, expected)
    _sha_value(evidence["tenant_subject_sha256"], "tenant_subject_sha256")
    _sha_value(evidence["account_subject_sha256"], "account_subject_sha256")

    audit = _object(evidence, "audit")
    audit_id = audit["audit_id"]
    if not isinstance(audit_id, str) or _AUDIT_ID_RE.fullmatch(audit_id) is None:
        raise AcceptanceAuthorityInvalid("audit.audit_id is invalid")
    if audit["create_http_status"] not in {200, 201}:
        raise AcceptanceAuthorityInvalid("audit.create_http_status is invalid")
    _equal(audit, "terminal_status", "completed", "audit")
    if audit["verdict"] not in _RESEARCH_VERDICTS:
        raise AcceptanceAuthorityInvalid("audit.verdict is invalid")
    _nonempty(audit["model_id"], "audit.model_id")
    _nonempty(audit["mode"], "audit.mode")
    _proof_time(
        audit["completed_at_utc"],
        "hosted_customer_journey",
        event,
        observed,
        now,
        "audit.completed_at_utc",
    )

    packet = _object(evidence, "packet_download")
    for field, expected in {
        "audit_id": audit_id,
        "http_status": 200,
        "content_type": "application/json",
        "verification_overall": "all_match",
        "worm_receipt_bound": True,
    }.items():
        _equal(packet, field, expected, "packet_download")
    _sha_value(packet["packet_sha256"], "packet_download.packet_sha256")
    _proof_time(
        packet["downloaded_at_utc"],
        "hosted_customer_journey",
        event,
        observed,
        now,
        "packet_download.downloaded_at_utc",
    )

    share = _object(evidence, "share")
    if share["create_http_status"] not in {200, 201}:
        raise AcceptanceAuthorityInvalid("share.create_http_status is invalid")
    for field, expected in {
        "anonymous_fetch_http_status": 200,
        "scope": "read_only",
    }.items():
        _equal(share, field, expected, "share")
    _sha_value(share["share_token_sha256"], "share.share_token_sha256")
    created = _proof_time(
        share["created_at_utc"],
        "hosted_customer_journey",
        event,
        observed,
        now,
        "share.created_at_utc",
    )
    fetched = _proof_time(
        share["fetched_at_utc"],
        "hosted_customer_journey",
        event,
        observed,
        now,
        "share.fetched_at_utc",
    )
    revoked = _proof_time(
        share["revoked_at_utc"],
        "hosted_customer_journey",
        event,
        observed,
        now,
        "share.revoked_at_utc",
    )
    expires = _parse_utc(share["expires_at_utc"], "share.expires_at_utc")
    if not created <= fetched <= revoked:
        raise AcceptanceAuthorityInvalid("share lifecycle timestamps are out of order")
    if expires <= created:
        raise AcceptanceAuthorityInvalid("share expiry must follow creation")
    if share["revoke_http_status"] not in {200, 204}:
        raise AcceptanceAuthorityInvalid("share.revoke_http_status is invalid")
    if share["revoked_fetch_http_status"] not in {404, 410}:
        raise AcceptanceAuthorityInvalid("share.revoked_fetch_http_status is invalid")

    isolation = _object(evidence, "tenant_isolation")
    _equal(isolation, "foreign_audit_http_status", 404, "tenant_isolation")
    _equal(isolation, "foreign_packet_http_status", 404, "tenant_isolation")
    _proof_time(
        isolation["verified_at_utc"],
        "hosted_customer_journey",
        event,
        observed,
        now,
        "tenant_isolation.verified_at_utc",
    )


def _validate_accounts_billing_semantics(
    evidence: Mapping[str, Any],
    event: datetime,
    observed: datetime,
    now: datetime,
) -> None:
    for field, expected in {
        "api_base_url": PRODUCTION_API_ORIGIN,
        "service_id": PRODUCTION_SERVICE_ID,
        "customer_lane": "public-customer",
    }.items():
        _equal(evidence, field, expected)
    _sha_value(evidence["tenant_subject_sha256"], "tenant_subject_sha256")

    session = _object(evidence, "account_session")
    if session["invite_redeem_http_status"] not in {200, 201}:
        raise AcceptanceAuthorityInvalid("account_session invite status is invalid")
    if session["logout_http_status"] not in {200, 204}:
        raise AcceptanceAuthorityInvalid("account_session logout status is invalid")
    for field, expected in {
        "login_http_status": 200,
        "revoked_session_http_status": 401,
        "durable_session_restart_verified": True,
        "disabled_account_http_status": 403,
        "cross_tenant_http_status": 404,
    }.items():
        _equal(session, field, expected, "account_session")
    _proof_time(
        session["verified_at_utc"],
        "accounts_billing",
        event,
        observed,
        now,
        "account_session.verified_at_utc",
    )

    quota = _object(evidence, "quota")
    limit = _positive_int(quota["monthly_limit"], "quota.monthly_limit")
    usage = _positive_int(quota["usage_at_limit"], "quota.usage_at_limit")
    if limit != usage:
        raise AcceptanceAuthorityInvalid("quota usage does not equal its limit")
    for field, expected in {
        "overflow_http_status": 429,
        "overflow_error": "audit_quota_exceeded",
        "idempotent_retry_non_double_consuming": True,
        "adjacent_month_isolated": True,
        "shared_postgres_restart_verified": True,
    }.items():
        _equal(quota, field, expected, "quota")
    _proof_time(
        quota["verified_at_utc"],
        "accounts_billing",
        event,
        observed,
        now,
        "quota.verified_at_utc",
    )

    billing = _object(evidence, "billing")
    for field, expected in {
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
    }.items():
        _equal(billing, field, expected, "billing")
    for field in (
        "provider_customer_id_sha256",
        "provider_subscription_id_sha256",
        "invoice_id_sha256",
    ):
        _sha_value(billing[field], f"billing.{field}")
    _proof_time(
        billing["paid_at_utc"],
        "accounts_billing",
        event,
        observed,
        now,
        "billing.paid_at_utc",
    )


def _validate_legal_semantics(
    evidence: Mapping[str, Any],
    event: datetime,
    observed: datetime,
    now: datetime,
) -> None:
    _equal(evidence, "public_base_url", LANDING_ORIGIN)
    documents = _mapping_list_by_key(
        evidence["documents"], "kind", _LEGAL_DOCUMENT_KINDS, "documents"
    )
    for kind, document in documents.items():
        _equal(document, "url", f"{LANDING_ORIGIN}/{kind}", f"documents[{kind}]")
        _equal(document, "http_status", 200, f"documents[{kind}]")
        _sha_value(document["content_sha256"], f"documents[{kind}].content_sha256")
        published = _proof_time(
            document["published_at_utc"],
            "legal_publication_approval",
            event,
            observed,
            now,
            f"documents[{kind}].published_at_utc",
        )
        verified = _proof_time(
            document["verified_at_utc"],
            "legal_publication_approval",
            event,
            observed,
            now,
            f"documents[{kind}].verified_at_utc",
        )
        if published > verified:
            raise AcceptanceAuthorityInvalid(f"documents[{kind}] verification precedes publication")
    approvals = _mapping_list_by_key(
        evidence["approvals"], "role", _LEGAL_APPROVER_ROLES, "approvals"
    )
    for role, approval in approvals.items():
        _validate_public_https_url(
            str(approval["approval_artifact_uri"]),
            f"approvals[{role}].approval_artifact_uri",
            allowed_origins=_API_LANDING_ORIGINS,
        )
        _sha_value(approval["approval_sha256"], f"approvals[{role}].approval_sha256")
        _proof_time(
            approval["approved_at_utc"],
            "legal_publication_approval",
            event,
            observed,
            now,
            f"approvals[{role}].approved_at_utc",
        )
    if evidence["claim_status_vocabulary"] != _CLAIM_STATUS_VOCABULARY:
        raise AcceptanceAuthorityInvalid("claim_status_vocabulary is not exact")


def _validate_support_crm_semantics(
    evidence: Mapping[str, Any],
    event: datetime,
    observed: datetime,
    now: datetime,
) -> None:
    _equal(evidence, "public_support_url", f"{LANDING_ORIGIN}/contact")
    _equal(evidence, "api_base_url", PRODUCTION_API_ORIGIN)
    _equal(evidence, "service_id", PRODUCTION_SERVICE_ID)
    ticket = _object(evidence, "support_ticket")
    _sha_value(ticket["ticket_id_sha256"], "support_ticket.ticket_id_sha256")
    if ticket["create_http_status"] not in {200, 201, 202}:
        raise AcceptanceAuthorityInvalid("support_ticket create status is invalid")
    for field in ("persisted", "routed", "acknowledged", "resolution_recorded"):
        _equal(ticket, field, True, "support_ticket")
    first_response = _nonnegative_int(
        ticket["first_response_minutes"], "support_ticket.first_response_minutes"
    )
    sla = _positive_int(ticket["sla_minutes"], "support_ticket.sla_minutes")
    if first_response > sla:
        raise AcceptanceAuthorityInvalid("support_ticket first response exceeded SLA")
    _proof_time(
        ticket["resolved_at_utc"],
        "support_crm",
        event,
        observed,
        now,
        "support_ticket.resolved_at_utc",
    )
    lead = _object(evidence, "crm_lead")
    _nonempty(lead["system"], "crm_lead.system")
    _sha_value(lead["lead_id_sha256"], "crm_lead.lead_id_sha256")
    for field in ("persisted", "readback_verified", "deduplicated", "owner_assigned"):
        _equal(lead, field, True, "crm_lead")
    _nonempty(lead["lifecycle_stage"], "crm_lead.lifecycle_stage")
    _proof_time(
        lead["verified_at_utc"],
        "support_crm",
        event,
        observed,
        now,
        "crm_lead.verified_at_utc",
    )
    consent = _object(evidence, "consent")
    for field in (
        "capture_consent_recorded",
        "source_attribution_recorded",
        "privacy_notice_linked",
    ):
        _equal(consent, field, True, "consent")
    _proof_time(
        consent["recorded_at_utc"],
        "support_crm",
        event,
        observed,
        now,
        "consent.recorded_at_utc",
    )


def _validate_incident_tabletop_semantics(
    evidence: Mapping[str, Any],
    event: datetime,
    observed: datetime,
    now: datetime,
) -> None:
    _equal(evidence, "api_base_url", PRODUCTION_API_ORIGIN)
    _equal(evidence, "service_id", PRODUCTION_SERVICE_ID)
    incident = _object(evidence, "incident")
    record_id = incident["record_id"]
    if not isinstance(record_id, str) or _INCIDENT_ID_RE.fullmatch(record_id) is None:
        raise AcceptanceAuthorityInvalid("incident.record_id is invalid")
    _equal(incident, "status", "CLOSED", "incident")
    _proof_time(
        incident["closed_at_utc"],
        "incident_tabletop",
        event,
        observed,
        now,
        "incident.closed_at_utc",
    )
    _equal(incident, "open_actions", 0, "incident")
    _validate_public_https_url(
        str(incident["postmortem_uri"]),
        "incident.postmortem_uri",
        allowed_origins=_API_ONLY_ORIGINS,
    )
    _sha_value(incident["postmortem_sha256"], "incident.postmortem_sha256")
    _equal(incident, "credential_rotation_complete", True, "incident")
    _equal(incident, "recovery_verified", True, "incident")

    tabletop = _object(evidence, "tabletop")
    tabletop_id = tabletop["tabletop_id"]
    if not isinstance(tabletop_id, str) or _PROBE_ID_RE.fullmatch(tabletop_id) is None:
        raise AcceptanceAuthorityInvalid("tabletop.tabletop_id is invalid")
    _proof_time(
        tabletop["completed_at_utc"],
        "incident_tabletop",
        event,
        observed,
        now,
        "tabletop.completed_at_utc",
    )
    _exact_string_set(tabletop["participant_roles"], _TABLETOP_ROLES, "tabletop.participant_roles")
    _exact_string_set(tabletop["scenarios"], _TABLETOP_SCENARIOS, "tabletop.scenarios")
    _equal(tabletop, "open_actions", 0, "tabletop")
    _validate_public_https_url(
        str(tabletop["evidence_uri"]),
        "tabletop.evidence_uri",
        allowed_origins=_API_ONLY_ORIGINS,
    )
    _sha_value(tabletop["evidence_sha256"], "tabletop.evidence_sha256")


def _validate_alert_delivery_semantics(
    evidence: Mapping[str, Any],
    event: datetime,
    observed: datetime,
    now: datetime,
) -> None:
    _equal(evidence, "api_base_url", PRODUCTION_API_ORIGIN)
    _equal(evidence, "service_id", PRODUCTION_SERVICE_ID)
    alert = _object(evidence, "alert")
    _sha_value(alert["alert_id_sha256"], "alert.alert_id_sha256")
    _equal(alert, "severity", "P1", "alert")
    emitted = _proof_time(
        alert["emitted_at_utc"],
        "alert_delivery",
        event,
        observed,
        now,
        "alert.emitted_at_utc",
    )
    _nonempty(alert["source"], "alert.source")
    deliveries = _mapping_list_by_key(
        evidence["deliveries"],
        "destination_role",
        _ALERT_DESTINATIONS,
        "deliveries",
    )
    for role, delivery in deliveries.items():
        _equal(delivery, "status", "delivered", f"deliveries[{role}]")
        delivered = _proof_time(
            delivery["delivered_at_utc"],
            "alert_delivery",
            event,
            observed,
            now,
            f"deliveries[{role}].delivered_at_utc",
        )
        if delivered < emitted:
            raise AcceptanceAuthorityInvalid(f"deliveries[{role}] precedes alert emission")
        _sha_value(delivery["receipt_sha256"], f"deliveries[{role}].receipt_sha256")

    acknowledgement = _object(evidence, "acknowledgement")
    _equal(acknowledgement, "status", "acknowledged", "acknowledgement")
    acknowledged = _proof_time(
        acknowledgement["acknowledged_at_utc"],
        "alert_delivery",
        event,
        observed,
        now,
        "acknowledgement.acknowledged_at_utc",
    )
    _equal(
        acknowledgement,
        "actor_role",
        "incident_commander",
        "acknowledgement",
    )
    latency = _nonnegative_int(
        acknowledgement["latency_seconds"], "acknowledgement.latency_seconds"
    )
    actual_latency = int((acknowledged - emitted).total_seconds())
    if acknowledged < emitted or latency != actual_latency or latency > 600:
        raise AcceptanceAuthorityInvalid("alert acknowledgement latency is invalid")

    escalation = _object(evidence, "escalation")
    for field, expected in {
        "triggered": True,
        "delivered": True,
        "destination_role": "secondary_on_call",
    }.items():
        _equal(escalation, field, expected, "escalation")
    _sha_value(escalation["receipt_sha256"], "escalation.receipt_sha256")
    escalated = _proof_time(
        escalation["delivered_at_utc"],
        "alert_delivery",
        event,
        observed,
        now,
        "escalation.delivered_at_utc",
    )
    if escalated < emitted:
        raise AcceptanceAuthorityInvalid("alert escalation precedes emission")


def _validate_claim_honesty_semantics(
    evidence: Mapping[str, Any],
    event: datetime,
    observed: datetime,
    now: datetime,
) -> None:
    surfaces = _mapping_list_by_key(
        evidence["scanned_surfaces"], "kind", _CLAIM_SURFACE_KINDS, "scanned_surfaces"
    )
    expected_urls = {
        "product_app": PRODUCTION_APP_ORIGIN,
        "audit_console": f"{PRODUCTION_APP_ORIGIN}/audit-console",
        "landing": LANDING_ORIGIN,
        "legal": f"{LANDING_ORIGIN}/legal",
        "privacy": f"{LANDING_ORIGIN}/privacy",
        "terms": f"{LANDING_ORIGIN}/terms",
    }
    for kind, surface in surfaces.items():
        _equal(surface, "url", expected_urls[kind], f"scanned_surfaces[{kind}]")
        _equal(surface, "http_status", 200, f"scanned_surfaces[{kind}]")
        _sha_value(surface["content_sha256"], f"scanned_surfaces[{kind}].content_sha256")
        _proof_time(
            surface["verified_at_utc"],
            "claim_honesty",
            event,
            observed,
            now,
            f"scanned_surfaces[{kind}].verified_at_utc",
        )
    scan = _object(evidence, "scan")
    for field in (
        "misleading_claim_count",
        "unsupported_compliance_claim_count",
        "unsupported_universality_claim_count",
    ):
        _equal(scan, field, 0, "scan")
    _equal(scan, "status_vocabulary_exact", True, "scan")
    boundaries = _object(evidence, "boundaries")
    for field in (
        "research_scope_disclosed",
        "research_accept_not_product_accept",
        "worm_retention_not_verdict_upgrade",
        "flag_for_human_review_not_accept",
        "compliance_certification_claims_absent",
    ):
        _equal(boundaries, field, True, "boundaries")
    if boundaries["rendered_product_status"] not in {"OPEN", "ACCEPT"}:
        raise AcceptanceAuthorityInvalid("boundaries.rendered_product_status is invalid")
    approvals = _mapping_list_by_key(
        evidence["approvals"], "role", _CLAIM_APPROVER_ROLES, "approvals"
    )
    for role, approval in approvals.items():
        _validate_public_https_url(
            str(approval["approval_artifact_uri"]),
            f"approvals[{role}].approval_artifact_uri",
            allowed_origins=_API_LANDING_ORIGINS,
        )
        _sha_value(approval["approval_sha256"], f"approvals[{role}].approval_sha256")
        _proof_time(
            approval["approved_at_utc"],
            "claim_honesty",
            event,
            observed,
            now,
            f"approvals[{role}].approved_at_utc",
        )


def _validate_release_decision_semantics(
    evidence: Mapping[str, Any],
    event: datetime,
    observed: datetime,
    now: datetime,
) -> None:
    _equal(evidence, "status", "ACCEPT")
    approved = _proof_time(
        evidence["approved_at_utc"],
        "release_decision",
        event,
        observed,
        now,
        "approved_at_utc",
    )
    if approved > observed:  # explicit for readability; _proof_time already checks
        raise AcceptanceAuthorityInvalid("release approval follows observation")
    _exact_string_set(
        evidence["approver_roles"], _RELEASE_APPROVER_ROLES, "approver_roles"
    )
    _validate_public_https_url(
        str(evidence["decision_record_uri"]),
        "decision_record_uri",
        allowed_origins=_API_ONLY_ORIGINS,
    )
    _sha_value(evidence["decision_record_sha256"], "decision_record_sha256")


def _object(parent: Mapping[str, Any], field: str) -> Mapping[str, Any]:
    value = parent[field]
    if not isinstance(value, Mapping):  # structure validation should have caught this
        raise AcceptanceAuthorityInvalid(f"{field} must be an object")
    return value


def _equal(
    parent: Mapping[str, Any], field: str, expected: Any, prefix: str = ""
) -> None:
    actual = parent[field]
    matches = actual == expected
    if isinstance(expected, bool):
        matches = actual is expected
    elif isinstance(expected, int):
        matches = isinstance(actual, int) and not isinstance(actual, bool) and actual == expected
    if not matches:
        path = f"{prefix}.{field}" if prefix else field
        raise AcceptanceAuthorityInvalid(f"{path} does not match the gate contract")


def _mapping_list_by_key(
    value: Any, key: str, expected: frozenset[str], path: str
) -> dict[str, Mapping[str, Any]]:
    if not isinstance(value, list):
        raise AcceptanceAuthorityInvalid(f"{path} must be an array")
    result: dict[str, Mapping[str, Any]] = {}
    for item in value:
        if not isinstance(item, Mapping) or not isinstance(item.get(key), str):
            raise AcceptanceAuthorityInvalid(f"{path} contains an invalid item")
        identity = str(item[key])
        if identity in result:
            raise AcceptanceAuthorityInvalid(f"{path} contains a duplicate {key}")
        result[identity] = item
    if set(result) != expected:
        raise AcceptanceAuthorityInvalid(f"{path} identities are not exact")
    return result


def _exact_string_set(value: Any, expected: frozenset[str], path: str) -> None:
    if (
        not isinstance(value, list)
        or any(not isinstance(item, str) for item in value)
        or len(value) != len(set(value))
        or set(value) != expected
    ):
        raise AcceptanceAuthorityInvalid(f"{path} is not the exact required set")


def _proof_time(
    value: Any,
    gate: str,
    event: datetime,
    observed: datetime,
    now: datetime,
    path: str,
) -> datetime:
    parsed = _parse_utc(value, path)
    if parsed < event or parsed > observed or parsed > now:
        raise AcceptanceAuthorityInvalid(f"{path} is outside the evidence window")
    freshness = _FRESHNESS_MINUTES.get(gate)
    if freshness is not None and now - parsed > timedelta(minutes=freshness):
        raise AcceptanceAuthorityInvalid(f"{path} is stale")
    return parsed


def _sha_value(value: Any, path: str) -> str:
    if not _is_sha256(value):
        raise AcceptanceAuthorityInvalid(f"{path} is not a SHA-256 digest")
    return str(value)


def _nonempty(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AcceptanceAuthorityInvalid(f"{path} must be non-empty")
    return value


def _positive_int(value: Any, path: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise AcceptanceAuthorityInvalid(f"{path} must be a positive integer")
    return value


def _nonnegative_int(value: Any, path: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise AcceptanceAuthorityInvalid(f"{path} must be a non-negative integer")
    return value


def _scan_safe_values(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            field = str(key).lower()
            if field in _PROHIBITED_SECRET_FIELDS:
                raise AcceptanceAuthorityInvalid(
                    f"{path}.{key} is a prohibited raw-secret field"
                )
            if field in _PROHIBITED_PII_FIELDS:
                raise AcceptanceAuthorityInvalid(
                    f"{path}.{key} is a prohibited PII field"
                )
            if isinstance(child, str) and (
                field.endswith("_uri")
                or field.endswith("_url")
                or field in {"url", "artifact_uri"}
            ):
                _validate_public_https_url(child, f"{path}.{key}")
            _scan_safe_values(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _scan_safe_values(child, f"{path}[{index}]")
    elif isinstance(value, str):
        for label, pattern in _SUSPICIOUS_PATTERNS.items():
            if pattern.search(value):
                raise AcceptanceAuthorityInvalid(
                    f"{path} contains prohibited {label} material"
                )


def _validate_public_https_url(
    value: str,
    path: str,
    *,
    allowed_origins: frozenset[str] = _ALLOWED_URL_ORIGINS,
) -> None:
    try:
        parsed = urlparse(value)
        port = parsed.port
    except ValueError as exc:
        raise AcceptanceAuthorityInvalid(f"{path} must be a clean HTTPS URL") from exc
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or port not in {None, 443}
    ):
        raise AcceptanceAuthorityInvalid(f"{path} must be a clean HTTPS URL")
    port_suffix = f":{port}" if port is not None else ""
    origin = f"https://{parsed.hostname.lower()}{port_suffix}"
    if origin not in allowed_origins:
        raise AcceptanceAuthorityInvalid(f"{path} origin is not allowlisted")
    decoded_path = unquote(parsed.path)
    if decoded_path != parsed.path:
        raise AcceptanceAuthorityInvalid(f"{path} must not use encoded path material")
    if any(part == ".." for part in decoded_path.split("/")):
        raise AcceptanceAuthorityInvalid(f"{path} contains path traversal")


def _parse_s3_object_url(value: Any) -> tuple[str, str, str]:
    if not isinstance(value, str):
        raise AcceptanceAuthorityUnavailable(
            "immutable acceptance object URL is invalid"
        )
    try:
        parsed = urlparse(value)
        port = parsed.port
        query = parse_qs(
            parsed.query,
            keep_blank_values=True,
            strict_parsing=True,
        )
    except ValueError as exc:
        raise AcceptanceAuthorityUnavailable(
            "immutable acceptance object URL is invalid"
        ) from exc
    decoded_path = unquote(parsed.path)
    versions = query.get("versionId", [])
    if (
        parsed.scheme != "s3"
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
        or parsed.fragment
        or not parsed.path.startswith("/")
        or decoded_path != parsed.path
        or not decoded_path.lstrip("/")
        or set(query) != {"versionId"}
        or len(versions) != 1
        or not versions[0]
    ):
        raise AcceptanceAuthorityUnavailable(
            "immutable acceptance object URL is invalid"
        )
    return parsed.netloc, decoded_path.lstrip("/"), versions[0]


def _validate_operation_authorization(
    *, action: str, artifact_uri: Any, artifact_sha256: Any, reason: Any
) -> None:
    if action == "publish":
        allowed_reasons = _PUBLISH_OPERATION_REASONS
    elif action == "deactivate":
        allowed_reasons = _DEACTIVATE_OPERATION_REASONS
    else:
        raise AcceptanceAuthorityInvalid("authority operation action is invalid")
    if reason not in allowed_reasons:
        raise AcceptanceAuthorityInvalid("authority operation reason is invalid")
    if not isinstance(artifact_uri, str):
        raise AcceptanceAuthorityInvalid(
            "authority operation artifact URI is invalid"
        )
    _validate_public_https_url(
        artifact_uri,
        "authority operation authorization.artifact_uri",
        allowed_origins=_API_LANDING_ORIGINS,
    )
    if not _is_sha256(artifact_sha256):
        raise AcceptanceAuthorityInvalid(
            "authority operation artifact digest is invalid"
        )


def _validate_operation(
    payload: Mapping[str, Any],
    *,
    gate: str,
    operation_record_id: str,
    expected_digest: str,
) -> Mapping[str, Any]:
    if set(payload) != _OPERATION_KEYS:
        raise AcceptanceAuthorityUnavailable(
            "acceptance authority operation schema is invalid"
        )
    if (
        payload.get("schema_version") != OPERATION_SCHEMA_VERSION
        or payload.get("gate") != gate
    ):
        raise AcceptanceAuthorityUnavailable(
            "acceptance authority operation identity is invalid"
        )
    try:
        canonical = _canonical_json_bytes(payload)
    except AcceptanceAuthorityInvalid as exc:
        raise AcceptanceAuthorityUnavailable(
            "acceptance authority operation encoding is invalid"
        ) from exc
    digest = hashlib.sha256(canonical).hexdigest()
    if (
        digest != expected_digest
        or operation_record_id != _operation_record_id(gate, digest)
    ):
        raise AcceptanceAuthorityUnavailable(
            "acceptance authority operation digest is invalid"
        )
    action = payload.get("action")
    _parse_utc_unavailable(payload.get("changed_at_utc"), "operation timestamp")
    previous = payload.get("previous")
    next_head = payload.get("next")
    authorization = payload.get("authorization")
    if not isinstance(previous, Mapping) or set(previous) != _OPERATION_PREVIOUS_KEYS:
        raise AcceptanceAuthorityUnavailable(
            "acceptance authority previous-operation schema is invalid"
        )
    if not isinstance(next_head, Mapping) or set(next_head) != _OPERATION_NEXT_KEYS:
        raise AcceptanceAuthorityUnavailable(
            "acceptance authority next-operation schema is invalid"
        )
    if (
        not isinstance(authorization, Mapping)
        or set(authorization) != _OPERATION_AUTHORIZATION_KEYS
    ):
        raise AcceptanceAuthorityUnavailable(
            "acceptance authority authorization schema is invalid"
        )
    try:
        _validate_operation_authorization(
            action=str(action),
            artifact_uri=authorization.get("artifact_uri"),
            artifact_sha256=authorization.get("artifact_sha256"),
            reason=authorization.get("reason"),
        )
    except AcceptanceAuthorityInvalid as exc:
        raise AcceptanceAuthorityUnavailable(str(exc)) from exc

    previous_version = previous.get("head_version")
    next_version = next_head.get("head_version")
    if (
        not isinstance(previous_version, int)
        or isinstance(previous_version, bool)
        or previous_version < 0
        or not isinstance(next_version, int)
        or isinstance(next_version, bool)
        or next_version != previous_version + 1
    ):
        raise AcceptanceAuthorityUnavailable(
            "acceptance authority operation versions are invalid"
        )
    previous_sha = previous.get("evidence_sha256")
    previous_active = previous.get("active")
    previous_operation_id = previous.get("operation_record_id")
    if previous_version == 0:
        if any(
            value is not None
            for value in (previous_sha, previous_active, previous_operation_id)
        ):
            raise AcceptanceAuthorityUnavailable(
                "initial acceptance operation predecessor is invalid"
            )
    elif (
        not _is_sha256(previous_sha)
        or not isinstance(previous_active, bool)
        or not isinstance(previous_operation_id, str)
    ):
        raise AcceptanceAuthorityUnavailable(
            "acceptance operation predecessor is invalid"
        )
    else:
        _operation_digest_from_record_id(gate, previous_operation_id)

    next_sha = next_head.get("evidence_sha256")
    next_active = next_head.get("active")
    if not _is_sha256(next_sha) or not isinstance(next_active, bool):
        raise AcceptanceAuthorityUnavailable(
            "acceptance authority operation target is invalid"
        )
    if (action == "publish" and next_active is not True) or (
        action == "deactivate" and next_active is not False
    ):
        raise AcceptanceAuthorityUnavailable(
            "acceptance authority operation action is inconsistent"
        )
    return payload


def _validate_head_operation_binding(
    head: Mapping[str, Any],
    operation: Mapping[str, Any],
    *,
    head_version: int,
) -> None:
    next_head = operation["next"]
    assert isinstance(next_head, Mapping)
    if (
        next_head["head_version"] != head_version
        or next_head["evidence_sha256"] != head["evidence_sha256"]
        or next_head["active"] is not head["active"]
        or operation["changed_at_utc"] != head["changed_at_utc"]
    ):
        raise AcceptanceAuthorityUnavailable(
            "acceptance authority head operation binding is invalid"
        )


def _validate_head(payload: Mapping[str, Any], gate: str) -> Mapping[str, Any]:
    if set(payload) != _HEAD_KEYS:
        raise AcceptanceAuthorityUnavailable("acceptance authority head schema is invalid")
    if payload.get("schema_version") != HEAD_SCHEMA_VERSION or payload.get("gate") != gate:
        raise AcceptanceAuthorityUnavailable("acceptance authority head identity is invalid")
    digest = payload.get("evidence_sha256")
    if not _is_sha256(digest):
        raise AcceptanceAuthorityUnavailable("acceptance authority head digest is invalid")
    if payload.get("revision_record_id") != _revision_record_id(gate, str(digest)):
        raise AcceptanceAuthorityUnavailable("acceptance authority head pointer is invalid")
    if not isinstance(payload.get("active"), bool):
        raise AcceptanceAuthorityUnavailable("acceptance authority head state is invalid")
    _parse_utc_unavailable(payload.get("changed_at_utc"), "head timestamp")
    operation_digest = payload.get("operation_sha256")
    operation_record_id = payload.get("operation_record_id")
    if (
        not _is_sha256(operation_digest)
        or not isinstance(operation_record_id, str)
        or operation_record_id
        != _operation_record_id(gate, str(operation_digest))
    ):
        raise AcceptanceAuthorityUnavailable(
            "acceptance authority head operation pointer is invalid"
        )
    return payload


def _validate_revision(
    payload: Mapping[str, Any],
    *,
    gate: str,
    revision_id: str,
    expected_digest: str,
) -> Mapping[str, Any]:
    if set(payload) != _REVISION_KEYS:
        raise AcceptanceAuthorityUnavailable("acceptance authority revision schema is invalid")
    if payload.get("schema_version") != RECORD_SCHEMA_VERSION or payload.get("gate") != gate:
        raise AcceptanceAuthorityUnavailable("acceptance authority revision identity is invalid")
    digest = payload.get("evidence_sha256")
    if (
        not _is_sha256(digest)
        or digest != expected_digest
        or revision_id != _revision_record_id(gate, str(digest))
    ):
        raise AcceptanceAuthorityUnavailable("acceptance authority revision digest is invalid")
    byte_length = payload.get("byte_length")
    if (
        not isinstance(byte_length, int)
        or isinstance(byte_length, bool)
        or byte_length < 2
        or byte_length > MAX_EVIDENCE_BYTES
    ):
        raise AcceptanceAuthorityUnavailable("acceptance authority byte length is invalid")
    _parse_utc_unavailable(payload.get("persisted_at_utc"), "revision timestamp")
    storage = payload.get("storage")
    if not isinstance(storage, Mapping) or set(storage) != _STORAGE_KEYS:
        raise AcceptanceAuthorityUnavailable("acceptance authority storage schema is invalid")
    mode = storage.get("mode")
    if mode == "state_store":
        if not isinstance(payload.get("evidence_json"), str) or any(
            storage.get(field) is not None for field in _STORAGE_KEYS - {"mode"}
        ):
            raise AcceptanceAuthorityUnavailable("inline acceptance storage is invalid")
    elif mode == "worm":
        if payload.get("evidence_json") is not None:
            raise AcceptanceAuthorityUnavailable("WORM acceptance storage has an inline fallback")
        required_text = (
            "object_key",
            "object_url",
            "version_id",
            "retain_until_utc",
            "receipt_sha256",
        )
        if any(not isinstance(storage.get(field), str) or not storage.get(field) for field in required_text):
            raise AcceptanceAuthorityUnavailable("WORM acceptance storage pointer is invalid")
        if storage.get("object_key") != f"customer-production-authority/{gate}/{digest}.json":
            raise AcceptanceAuthorityUnavailable("WORM acceptance object key is invalid")
        if not _is_sha256(storage.get("receipt_sha256")):
            raise AcceptanceAuthorityUnavailable("WORM acceptance receipt digest is invalid")
        receipt_verification = storage.get("receipt_verification")
        if not isinstance(receipt_verification, Mapping):
            raise AcceptanceAuthorityUnavailable(
                "WORM acceptance receipt verification is invalid"
            )
        try:
            receipt_body = _canonical_json_bytes(receipt_verification)
        except AcceptanceAuthorityInvalid as exc:
            raise AcceptanceAuthorityUnavailable(
                "WORM acceptance receipt verification is invalid"
            ) from exc
        if hashlib.sha256(receipt_body).hexdigest() != storage.get(
            "receipt_sha256"
        ):
            raise AcceptanceAuthorityUnavailable(
                "WORM acceptance receipt hash is invalid"
            )
        if storage.get("lock_mode") not in {"GOVERNANCE", "COMPLIANCE"}:
            raise AcceptanceAuthorityUnavailable(
                "WORM acceptance lock mode is invalid"
            )
        retention_days = storage.get("retention_days")
        if (
            not isinstance(retention_days, int)
            or isinstance(retention_days, bool)
            or retention_days < 1
        ):
            raise AcceptanceAuthorityUnavailable(
                "WORM acceptance retention policy is invalid"
            )
        _parse_utc_unavailable(storage.get("retain_until_utc"), "WORM retention timestamp")
    else:
        raise AcceptanceAuthorityUnavailable("acceptance authority storage mode is invalid")
    return payload


def _require_gate(gate: str) -> None:
    if gate not in ACCEPTANCE_AUTHORITY_PATH_BY_GATE:
        raise ValueError(f"gate {gate!r} has no live acceptance authority")


def _head_record_id(gate: str) -> str:
    return f"customer-production-authority-head-{gate.replace('_', '-')}"


def _revision_record_id(gate: str, digest: str) -> str:
    return f"customer-production-authority-{gate.replace('_', '-')}-{digest}"


def _operation_record_id(gate: str, digest: str) -> str:
    return (
        "customer-production-authority-operation-"
        f"{gate.replace('_', '-')}-{digest}"
    )


def _operation_digest_from_record_id(gate: str, record_id: str) -> str:
    prefix = (
        "customer-production-authority-operation-"
        f"{gate.replace('_', '-')}-"
    )
    if not record_id.startswith(prefix):
        raise AcceptanceAuthorityUnavailable(
            "acceptance authority operation pointer is invalid"
        )
    digest = record_id[len(prefix) :]
    if not _is_sha256(digest) or record_id != _operation_record_id(gate, digest):
        raise AcceptanceAuthorityUnavailable(
            "acceptance authority operation pointer is invalid"
        )
    return digest


def _canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError) as exc:
        raise AcceptanceAuthorityInvalid(
            "acceptance evidence is not finite JSON"
        ) from exc


def _parse_utc(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or _UTC_RE.fullmatch(value) is None:
        raise AcceptanceAuthorityInvalid(f"{field} must be whole-second UTC")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError as exc:
        raise AcceptanceAuthorityInvalid(f"{field} is invalid") from exc
    return parsed


def _parse_utc_unavailable(value: Any, label: str) -> datetime:
    try:
        return _parse_utc(value, label)
    except AcceptanceAuthorityInvalid as exc:
        raise AcceptanceAuthorityUnavailable(str(exc)) from exc


def _parse_iso_utc_unavailable(value: Any, label: str) -> datetime:
    if not isinstance(value, str):
        raise AcceptanceAuthorityUnavailable(f"{label} is invalid")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AcceptanceAuthorityUnavailable(f"{label} is invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise AcceptanceAuthorityUnavailable(f"{label} is invalid")
    return parsed.astimezone(UTC).replace(microsecond=0)


def _utc_now(value: datetime | None) -> datetime:
    stamp = value or datetime.now(UTC)
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    return stamp.astimezone(UTC).replace(microsecond=0)


def _format_utc(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and _SHA256_RE.fullmatch(value) is not None


def _is_sha1(value: Any) -> bool:
    return isinstance(value, str) and _SHA1_RE.fullmatch(value) is not None


__all__ = [
    "AcceptanceAuthorityConflict",
    "AcceptanceAuthorityError",
    "AcceptanceAuthorityHead",
    "AcceptanceAuthorityInvalid",
    "AcceptanceAuthorityNotFound",
    "AcceptanceAuthorityUnavailable",
    "AcceptanceEvidenceDocument",
    "canonicalize_acceptance_evidence",
    "CustomerProductionAcceptanceAuthorityStore",
    "DeactivatedAcceptanceEvidence",
    "PublishedAcceptanceEvidence",
]
