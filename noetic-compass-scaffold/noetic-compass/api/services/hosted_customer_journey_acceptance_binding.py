"""Private source binding for hosted-customer-journey acceptance evidence.

Public gate documents contain tenant-scoped keyed subjects, never raw tenant or
account identifiers.  This store binds those exact canonical public bytes to a
private selector and re-reads the active account plus the finalized durable
audit before publication and whenever an active authority revision is served.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
import hashlib
import hmac
import json
import re
from typing import Any, Protocol

from api.services.accounts.models import Account
from api.services.customer_production_pseudonyms import (
    ACCOUNT_DOMAIN,
    HOSTED_JOURNEY_CONTENT_BINDING_DOMAIN,
    HOSTED_JOURNEY_TRACE_DOMAIN,
    TENANT_DOMAIN,
    CustomerProductionPseudonymizer,
    validate_public_pseudonym_metadata,
)
from api.services.production.state_substrate import (
    LedgerRecord,
    StateStore,
    VersionConflict,
)


SCHEMA_VERSION = "cas_harness_hosted_customer_journey_source_binding.v1"
SELECTOR_SCHEMA_VERSION = "cas_harness_hosted_customer_journey_acceptance_selector.v1"
BINDING_TENANT_ID = "cas-harness-customer-production-hosted-journey-bindings"
BINDING_KIND = "customer_production_hosted_journey_source_binding"
AUDIT_KIND = "cas_audit_session"
AUDIT_SOURCE = "cas_harness.audit_session"
_EVIDENCE_SCHEMA = "cas_harness_customer_production_gate_evidence.v3"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SELECTOR_KEYS = frozenset(
    {"schema_version", "gate", "tenant_id", "account_id", "audit_id"}
)
_RECORD_KEYS = frozenset(
    {
        "schema_version",
        "evidence_sha256",
        "tenant_id",
        "account_id",
        "audit_id",
        "audit_ledger_version",
        "audit_source",
        "audit_trace_id",
        "audit_parent_ids",
        "audit_payload_sha256",
        "audit_envelope_sha256",
        "pseudonym_key_id",
        "content_binding_hmac",
        "bound_at_utc",
    }
)


class HostedCustomerJourneySourceBindingError(RuntimeError):
    """Base hosted-journey source-binding error."""


class HostedCustomerJourneySourceBindingInvalid(
    HostedCustomerJourneySourceBindingError
):
    """Evidence or its private selector does not match authoritative state."""


class HostedCustomerJourneySourceBindingUnavailable(
    HostedCustomerJourneySourceBindingError
):
    """Durable state or a retained pseudonym key cannot be verified."""


class HostedJourneyAccountSource(Protocol):
    def get_account_by_id(self, account_id: str) -> Account | None: ...


class HostedCustomerJourneyAcceptanceSourceBindingStore:
    """Persist and revalidate evidence-to-account/audit private bindings."""

    def __init__(
        self,
        store: StateStore,
        *,
        accounts: HostedJourneyAccountSource,
        pseudonymizer: CustomerProductionPseudonymizer,
    ) -> None:
        if not callable(getattr(accounts, "get_account_by_id", None)):
            raise ValueError("account store is required")
        if not isinstance(pseudonymizer, CustomerProductionPseudonymizer):
            raise ValueError("customer-production pseudonymizer is required")
        self._store = store
        self._accounts = accounts
        self._pseudonymizer = pseudonymizer

    def create(
        self,
        evidence: Mapping[str, Any],
        *,
        selector: Mapping[str, Any],
        now: datetime | None = None,
    ) -> str:
        canonical = _canonical_json_bytes(evidence)
        evidence_sha256 = hashlib.sha256(canonical).hexdigest()
        tenant_id, account_id, audit_id = _validate_selector(selector)
        account, audit, key_id = self._assert_authoritative_source(
            evidence,
            tenant_id=tenant_id,
            account_id=account_id,
            audit_id=audit_id,
        )
        stamp = _utc_now(now)
        payload: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "evidence_sha256": evidence_sha256,
            "tenant_id": tenant_id,
            "account_id": account_id,
            "audit_id": audit_id,
            "audit_ledger_version": audit.version,
            "audit_source": audit.source,
            "audit_trace_id": audit.trace_id,
            "audit_parent_ids": list(audit.parent_ids),
            "audit_payload_sha256": _mapping_sha256(audit.payload),
            "audit_envelope_sha256": _ledger_envelope_sha256(audit),
            "pseudonym_key_id": key_id,
            "content_binding_hmac": self._content_binding_hmac(
                evidence_sha256=evidence_sha256,
                tenant_id=tenant_id,
                account_id=account_id,
                audit=audit,
                pseudonym_key_id=key_id,
            ),
            "bound_at_utc": _format_utc(stamp),
        }
        record = LedgerRecord.new(
            tenant_id=BINDING_TENANT_ID,
            kind=BINDING_KIND,
            record_id=_record_id(evidence_sha256),
            payload=payload,
            source="hosted_customer_journey_acceptance_source_binding",
            trace_id=evidence_sha256,
            now=stamp,
        )
        try:
            stored = self._store.put(record, expected_version=0)
        except VersionConflict:
            try:
                existing = self._store.get(
                    BINDING_TENANT_ID, BINDING_KIND, _record_id(evidence_sha256)
                )
            except Exception as exc:
                raise HostedCustomerJourneySourceBindingUnavailable(
                    "hosted journey source binding store is unavailable"
                ) from exc
            existing_payload = _validate_record(existing, evidence_sha256)
            if any(
                existing_payload.get(key) != value
                for key, value in payload.items()
                if key != "bound_at_utc"
            ):
                raise HostedCustomerJourneySourceBindingUnavailable(
                    "hosted journey source binding conflicted"
                )
            stored = existing
        except Exception as exc:
            raise HostedCustomerJourneySourceBindingUnavailable(
                "hosted journey source binding persistence failed"
            ) from exc
        if stored is None or stored.version != 1:
            raise HostedCustomerJourneySourceBindingUnavailable(
                "hosted journey source binding version is invalid"
            )
        self.assert_matches(evidence, evidence_sha256=evidence_sha256)
        return evidence_sha256

    def assert_matches(
        self, evidence: Mapping[str, Any], *, evidence_sha256: str
    ) -> None:
        if (
            not isinstance(evidence_sha256, str)
            or _SHA256_RE.fullmatch(evidence_sha256) is None
            or hashlib.sha256(_canonical_json_bytes(evidence)).hexdigest()
            != evidence_sha256
        ):
            raise HostedCustomerJourneySourceBindingInvalid(
                "hosted journey evidence digest is invalid"
            )
        try:
            record = self._store.get(
                BINDING_TENANT_ID, BINDING_KIND, _record_id(evidence_sha256)
            )
        except Exception as exc:
            raise HostedCustomerJourneySourceBindingUnavailable(
                "hosted journey source binding store is unavailable"
            ) from exc
        payload = _validate_record(record, evidence_sha256)
        tenant_id = str(payload["tenant_id"])
        account_id = str(payload["account_id"])
        audit_id = str(payload["audit_id"])
        account, audit, key_id = self._assert_authoritative_source(
            evidence,
            tenant_id=tenant_id,
            account_id=account_id,
            audit_id=audit_id,
        )
        if (
            account.account_id != account_id
            or audit.version != payload["audit_ledger_version"]
            or audit.source != payload["audit_source"]
            or audit.trace_id != payload["audit_trace_id"]
            or list(audit.parent_ids) != payload["audit_parent_ids"]
            or _mapping_sha256(audit.payload) != payload["audit_payload_sha256"]
            or _ledger_envelope_sha256(audit)
            != payload["audit_envelope_sha256"]
            or key_id != payload["pseudonym_key_id"]
        ):
            raise HostedCustomerJourneySourceBindingInvalid(
                "hosted journey source binding is stale or cross-wired"
            )
        expected_hmac = self._content_binding_hmac(
            evidence_sha256=evidence_sha256,
            tenant_id=tenant_id,
            account_id=account_id,
            audit=audit,
            pseudonym_key_id=key_id,
        )
        if not hmac.compare_digest(
            str(payload["content_binding_hmac"]), expected_hmac
        ):
            raise HostedCustomerJourneySourceBindingUnavailable(
                "hosted journey source binding integrity is invalid"
            )

    def _assert_authoritative_source(
        self,
        evidence: Mapping[str, Any],
        *,
        tenant_id: str,
        account_id: str,
        audit_id: str,
    ) -> tuple[Account, LedgerRecord, str]:
        if evidence.get("schema_version") != _EVIDENCE_SCHEMA or evidence.get(
            "gate"
        ) != "hosted_customer_journey":
            raise HostedCustomerJourneySourceBindingInvalid(
                "hosted journey evidence schema is invalid"
            )
        if _contains_key(
            evidence,
            {
                "tenant_subject_sha256",
                "account_subject_sha256",
                "trace_id_sha256",
            },
        ):
            raise HostedCustomerJourneySourceBindingInvalid(
                "legacy unkeyed hosted journey identity hashes are forbidden"
            )
        try:
            key_id = validate_public_pseudonym_metadata(
                evidence, available_key_ids=self._pseudonymizer.key_ids
            )
        except ValueError as exc:
            raise HostedCustomerJourneySourceBindingUnavailable(
                "hosted journey pseudonym verification key is unavailable"
            ) from exc
        try:
            account = self._accounts.get_account_by_id(account_id)
            audit = self._store.get(tenant_id, AUDIT_KIND, audit_id)
        except Exception as exc:
            raise HostedCustomerJourneySourceBindingUnavailable(
                "hosted journey authoritative source is unavailable"
            ) from exc
        if (
            account is None
            or not account.is_active
            or account.account_id != account_id
            or account.tenant_id != tenant_id
            or audit is None
            or audit.version <= 0
            or audit.tenant_id != tenant_id
            or audit.kind != AUDIT_KIND
            or audit.record_id != audit_id
            or audit.source != AUDIT_SOURCE
            or audit.trace_id != audit_id
            or audit.parent_ids != (account_id,)
            or audit.created_at.tzinfo is None
            or audit.created_at.utcoffset() is None
            or audit.updated_at.tzinfo is None
            or audit.updated_at.utcoffset() is None
            or audit.created_at > audit.updated_at
            or not isinstance(audit.payload, Mapping)
            or audit.payload.get("_account_id") != account_id
            or audit.payload.get("audit_id") != audit_id
            or audit.payload.get("status") != "COMPLETE"
            or audit.payload.get("provider_run_phase") != "FINALIZED"
        ):
            raise HostedCustomerJourneySourceBindingInvalid(
                "hosted journey source is not one active account and finalized audit"
            )
        trace_id = audit.payload.get("evidence_packet_trace_id")
        if not isinstance(trace_id, str) or not trace_id:
            raise HostedCustomerJourneySourceBindingInvalid(
                "hosted journey finalized audit trace is absent"
            )
        if _contains_raw_value(evidence, {tenant_id, account_id, trace_id}):
            raise HostedCustomerJourneySourceBindingInvalid(
                "hosted journey public evidence exposes a private source identifier"
            )
        audit_public = evidence.get("audit")
        packet = evidence.get("packet_download")
        if not isinstance(audit_public, Mapping) or not isinstance(packet, Mapping):
            raise HostedCustomerJourneySourceBindingInvalid(
                "hosted journey public audit facts are absent"
            )
        if (
            audit_public.get("audit_id") != audit_id
            or packet.get("audit_id") != audit_id
            or audit_public.get("terminal_status") != "completed"
            or audit_public.get("verdict") != audit.payload.get("verdict")
            or audit_public.get("model_id") != audit.payload.get("model_id")
            or audit_public.get("mode") != audit.payload.get("audit_mode")
            or _canonical_timestamp(audit_public.get("completed_at_utc"))
            != _canonical_timestamp(audit.payload.get("updated_at"))
        ):
            raise HostedCustomerJourneySourceBindingInvalid(
                "hosted journey public facts do not match the finalized audit"
            )
        for field, domain, raw_value in (
            ("tenant_subject", TENANT_DOMAIN, tenant_id),
            ("account_subject", ACCOUNT_DOMAIN, account_id),
            ("trace_subject", HOSTED_JOURNEY_TRACE_DOMAIN, trace_id),
        ):
            try:
                self._pseudonymizer.assert_subject(
                    evidence.get(field),
                    domain=domain,
                    tenant_scope=tenant_id,
                    value=raw_value,
                    key_id=key_id,
                )
            except ValueError as exc:
                raise HostedCustomerJourneySourceBindingInvalid(
                    f"hosted journey {field} does not match the authoritative source"
                ) from exc
        return account, audit, key_id

    def _content_binding_hmac(
        self,
        *,
        evidence_sha256: str,
        tenant_id: str,
        account_id: str,
        audit: LedgerRecord,
        pseudonym_key_id: str,
    ) -> str:
        value = _canonical_json_bytes(
            {
                "evidence_sha256": evidence_sha256,
                "tenant_id": tenant_id,
                "account_id": account_id,
                "audit_id": audit.record_id,
                "audit_ledger_version": audit.version,
                "audit_source": audit.source,
                "audit_trace_id": audit.trace_id,
                "audit_parent_ids": list(audit.parent_ids),
                "audit_payload_sha256": _mapping_sha256(audit.payload),
                "audit_envelope_sha256": _ledger_envelope_sha256(audit),
                "evidence_packet_trace_id": audit.payload.get(
                    "evidence_packet_trace_id"
                ),
                "pseudonym_key_id": pseudonym_key_id,
            }
        ).decode("ascii")
        return self._pseudonymizer.subject(
            domain=HOSTED_JOURNEY_CONTENT_BINDING_DOMAIN,
            tenant_scope=tenant_id,
            value=value,
            key_id=pseudonym_key_id,
        )


def _validate_selector(selector: Mapping[str, Any]) -> tuple[str, str, str]:
    if (
        not isinstance(selector, Mapping)
        or set(selector) != _SELECTOR_KEYS
        or selector.get("schema_version") != SELECTOR_SCHEMA_VERSION
        or selector.get("gate") != "hosted_customer_journey"
    ):
        raise HostedCustomerJourneySourceBindingInvalid(
            "hosted journey private selector is invalid"
        )
    values = tuple(selector.get(key) for key in ("tenant_id", "account_id", "audit_id"))
    if any(not isinstance(value, str) or not value for value in values):
        raise HostedCustomerJourneySourceBindingInvalid(
            "hosted journey private selector is invalid"
        )
    return str(values[0]), str(values[1]), str(values[2])


def _validate_record(
    record: LedgerRecord | None, evidence_sha256: str
) -> Mapping[str, Any]:
    if (
        record is None
        or record.version != 1
        or record.tenant_id != BINDING_TENANT_ID
        or record.kind != BINDING_KIND
        or record.record_id != _record_id(evidence_sha256)
        or record.parent_ids
        or record.source != "hosted_customer_journey_acceptance_source_binding"
        or record.trace_id != evidence_sha256
        or not isinstance(record.payload, Mapping)
        or set(record.payload) != _RECORD_KEYS
        or record.payload.get("schema_version") != SCHEMA_VERSION
        or record.payload.get("evidence_sha256") != evidence_sha256
        or not isinstance(record.payload.get("audit_ledger_version"), int)
        or isinstance(record.payload.get("audit_ledger_version"), bool)
        or int(record.payload.get("audit_ledger_version", 0)) <= 0
        or any(
            not isinstance(record.payload.get(key), str)
            or not record.payload.get(key)
            for key in (
                "tenant_id",
                "account_id",
                "audit_id",
                "audit_source",
                "audit_trace_id",
                "pseudonym_key_id",
                "content_binding_hmac",
            )
        )
        or not isinstance(record.payload.get("audit_parent_ids"), list)
        or len(record.payload.get("audit_parent_ids", [])) != 1
        or any(
            not isinstance(value, str) or not value
            for value in record.payload.get("audit_parent_ids", [])
        )
        or any(
            _SHA256_RE.fullmatch(str(record.payload.get(key) or "")) is None
            for key in ("audit_payload_sha256", "audit_envelope_sha256")
        )
    ):
        raise HostedCustomerJourneySourceBindingUnavailable(
            "hosted journey source binding integrity is invalid"
        )
    _canonical_timestamp(record.payload.get("bound_at_utc"))
    return record.payload


def _record_id(evidence_sha256: str) -> str:
    return f"hosted-journey-source-{evidence_sha256}"


def _mapping_sha256(value: Mapping[str, object]) -> str:
    return hashlib.sha256(_canonical_json_bytes(value)).hexdigest()


def _ledger_envelope_sha256(record: LedgerRecord) -> str:
    return _mapping_sha256(
        {
            "tenant_id": record.tenant_id,
            "kind": record.kind,
            "record_id": record.record_id,
            "version": record.version,
            "created_at": _ledger_timestamp(record.created_at),
            "updated_at": _ledger_timestamp(record.updated_at),
            "parent_ids": list(record.parent_ids),
            "source": record.source,
            "trace_id": record.trace_id,
            "payload": dict(record.payload),
        }
    )


def _ledger_timestamp(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise HostedCustomerJourneySourceBindingInvalid(
            "hosted journey audit envelope timestamp is invalid"
        )
    return value.astimezone(UTC).isoformat(timespec="microseconds")


def _contains_key(value: object, forbidden: set[str]) -> bool:
    if isinstance(value, Mapping):
        return any(
            key in forbidden or _contains_key(child, forbidden)
            for key, child in value.items()
        )
    if isinstance(value, (list, tuple)):
        return any(_contains_key(child, forbidden) for child in value)
    return False


def _contains_raw_value(value: object, forbidden: set[str]) -> bool:
    if isinstance(value, Mapping):
        return any(
            any(raw in str(key) for raw in forbidden)
            or _contains_raw_value(child, forbidden)
            for key, child in value.items()
        )
    if isinstance(value, (list, tuple)):
        return any(_contains_raw_value(child, forbidden) for child in value)
    return isinstance(value, str) and any(raw in value for raw in forbidden)


def _canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError) as exc:
        raise HostedCustomerJourneySourceBindingInvalid(
            "hosted journey evidence is not strict canonical JSON"
        ) from exc


def _utc_now(value: datetime | None = None) -> datetime:
    stamp = datetime.now(UTC) if value is None else value
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise HostedCustomerJourneySourceBindingInvalid(
            "hosted journey binding time must be timezone-aware"
        )
    return stamp.astimezone(UTC).replace(microsecond=0)


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _canonical_timestamp(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise HostedCustomerJourneySourceBindingInvalid(
            "hosted journey source timestamp is invalid"
        )
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HostedCustomerJourneySourceBindingInvalid(
            "hosted journey source timestamp is invalid"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise HostedCustomerJourneySourceBindingInvalid(
            "hosted journey source timestamp is invalid"
        )
    return _format_utc(parsed)


__all__ = [
    "AUDIT_KIND",
    "AUDIT_SOURCE",
    "BINDING_KIND",
    "BINDING_TENANT_ID",
    "HostedCustomerJourneyAcceptanceSourceBindingStore",
    "HostedCustomerJourneySourceBindingError",
    "HostedCustomerJourneySourceBindingInvalid",
    "HostedCustomerJourneySourceBindingUnavailable",
    "SELECTOR_SCHEMA_VERSION",
    "SCHEMA_VERSION",
]
