"""Platform-only, crash-safe provisioning of a new tenant's first owner.

Customer account roles never call this service through normal RBAC. The HTTP edge that invokes
it is protected by a separate server-side platform credential. The workflow reserves one
deterministic record per tenant before exposing an account and can resume after any individual
ledger write. The caller supplies and retains the owner credential; only its digest is stored.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Mapping, Optional, TYPE_CHECKING

from api.services.crm.models import normalize_email
from api.services.production.state_substrate import LedgerRecord, VersionConflict

from .credentials import (
    CREDENTIAL_VERSION,
    credential_matches,
    hash_account_credential,
    validate_account_credential,
)
from .models import ACCOUNT_KIND, Account

if TYPE_CHECKING:
    from .store import AccountStore


TENANT_PROVISIONING_KIND = "platform_tenant_provisioning"
TENANT_PROVISIONING_RECEIPT_KIND = "platform_tenant_provisioning_receipt"
TENANT_PROVISIONING_SCHEMA_VERSION = "cas_accounts.tenant_provisioning.v1"
TENANT_PROVISIONING_RECEIPT_SCHEMA_VERSION = (
    "cas_accounts.tenant_provisioning_receipt.v1"
)
_TENANT_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{1,62}$")


class TenantProvisioningError(RuntimeError):
    """Fail-closed platform provisioning error with a server-side reason code."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


@dataclass(frozen=True)
class TenantProvisioningResult:
    provisioning_id: str
    receipt_id: str
    account: Account
    completed_at: str


def provision_tenant_owner(
    store: "AccountStore",
    *,
    tenant_id: str,
    email_or_username: str,
    api_credential: str,
    display_name: Optional[str] = None,
    request_id: Optional[str] = None,
) -> TenantProvisioningResult:
    """Reserve and materialize exactly one first owner for a previously empty tenant."""
    tenant = _normalize_tenant_id(tenant_id)
    email = normalize_email(email_or_username)
    try:
        validate_account_credential(api_credential)
    except ValueError as exc:
        raise TenantProvisioningError("invalid_owner_credential") from exc
    if not email:
        raise TenantProvisioningError("invalid_owner_identity")

    provisioning_id = _provisioning_id(tenant)
    marker = store._store.get(
        store._tenant, TENANT_PROVISIONING_KIND, provisioning_id
    )
    if marker is None:
        if _tenant_has_accounts(store, tenant):
            raise TenantProvisioningError("tenant_already_exists")
        now = datetime.now(UTC).isoformat()
        account = Account(
            account_id=_owner_account_id(tenant, email),
            email_or_username=email,
            role="owner",
            tenant_id=tenant,
            display_name=(
                display_name.strip()
                if display_name is not None and display_name.strip()
                else None
            ),
            credential_hash=hash_account_credential(
                api_credential, pepper=store._credential_pepper
            ),
            credential_version=CREDENTIAL_VERSION,
            credential_issued_at=now,
            created_at=now,
            updated_at=now,
        )
        reservation: dict[str, Any] = {
            "schema_version": TENANT_PROVISIONING_SCHEMA_VERSION,
            "status": "reserved",
            "provisioning_id": provisioning_id,
            "tenant_id": tenant,
            "email_or_username": email,
            "account": account.to_payload(),
            "reserved_at": now,
            "authority": "platform_provisioning",
            "platform_request_id": (request_id or "").strip() or None,
        }
        candidate = LedgerRecord.new(
            tenant_id=store._tenant,
            kind=TENANT_PROVISIONING_KIND,
            record_id=provisioning_id,
            payload=reservation,
            source="accounts.platform_provision_tenant",
            trace_id=provisioning_id,
        )
        try:
            marker = store._store.put(candidate, expected_version=0)
            store._fail_after("after_tenant_provisioning_reservation_write")
        except VersionConflict:
            marker = store._store.get(
                store._tenant, TENANT_PROVISIONING_KIND, provisioning_id
            )
            if marker is None:
                raise TenantProvisioningError("provisioning_race_lost")

    payload = marker.payload
    _assert_same_request(
        payload,
        tenant=tenant,
        email=email,
        api_credential=api_credential,
        pepper=store._credential_pepper,
    )
    if payload.get("status") == "completed":
        return _completed_result(store, payload, api_credential)
    if payload.get("status") != "reserved":
        raise TenantProvisioningError("corrupt_provisioning")
    return _materialize_owner(store, marker, payload, api_credential)


def _materialize_owner(
    store: "AccountStore",
    marker: LedgerRecord,
    payload: Mapping[str, Any],
    api_credential: str,
) -> TenantProvisioningResult:
    reserved = _reserved_account(payload)
    if not credential_matches(
        reserved, api_credential, pepper=store._credential_pepper
    ):
        raise TenantProvisioningError("provisioning_credential_mismatch")

    store._claim_email(
        reserved.email_or_username, account_id=reserved.account_id
    )
    store._fail_after("after_tenant_provisioning_email_write")

    existing = store.get_account_by_id(reserved.account_id)
    if existing is None:
        record = LedgerRecord.new(
            tenant_id=store._tenant,
            kind=ACCOUNT_KIND,
            record_id=reserved.account_id,
            payload=reserved.to_payload(),
            parent_ids=(marker.record_id,),
            source="accounts.platform_provision_tenant",
            trace_id=marker.record_id,
        )
        try:
            store._store.put(record, expected_version=0)
        except VersionConflict:
            existing = store.get_account_by_id(reserved.account_id)
    if existing is not None:
        if not _same_owner(existing, reserved):
            raise TenantProvisioningError("provisioning_account_conflict")
        reserved = existing
    store._fail_after("after_tenant_provisioning_account_write")

    completed = _complete_marker(store, marker.record_id)
    store._fail_after("after_tenant_provisioning_completion_write")
    receipt_id = _ensure_receipt(store, completed, reserved)
    store._fail_after("after_tenant_provisioning_receipt_write")
    return TenantProvisioningResult(
        provisioning_id=marker.record_id,
        receipt_id=receipt_id,
        account=reserved,
        completed_at=str(completed.payload["completed_at"]),
    )


def _complete_marker(store: "AccountStore", provisioning_id: str) -> LedgerRecord:
    for _ in range(12):
        marker = store._store.get(
            store._tenant, TENANT_PROVISIONING_KIND, provisioning_id
        )
        if marker is None:
            raise TenantProvisioningError("corrupt_provisioning")
        if marker.payload.get("status") == "completed":
            return marker
        if marker.payload.get("status") != "reserved":
            raise TenantProvisioningError("corrupt_provisioning")
        completed = dict(marker.payload)
        completed["status"] = "completed"
        completed["completed_at"] = datetime.now(UTC).isoformat()
        try:
            return store._store.put(
                marker.with_payload(completed), expected_version=marker.version
            )
        except VersionConflict:
            continue
    raise TenantProvisioningError("provisioning_race_lost")


def _ensure_receipt(
    store: "AccountStore", marker: LedgerRecord, account: Account
) -> str:
    receipt_id = _receipt_id(marker.record_id)
    completed_at = str(marker.payload.get("completed_at") or "")
    if not completed_at:
        raise TenantProvisioningError("corrupt_provisioning")
    payload = {
        "schema_version": TENANT_PROVISIONING_RECEIPT_SCHEMA_VERSION,
        "status": "completed",
        "provisioning_id": marker.record_id,
        "tenant_id": account.tenant_id,
        "owner_account_id": account.account_id,
        "owner_email_or_username": account.email_or_username,
        "completed_at": completed_at,
        "authority": "platform_provisioning",
        "platform_request_id": marker.payload.get("platform_request_id"),
    }
    receipt = LedgerRecord.new(
        tenant_id=store._tenant,
        kind=TENANT_PROVISIONING_RECEIPT_KIND,
        record_id=receipt_id,
        payload=payload,
        parent_ids=(marker.record_id, account.account_id),
        source="accounts.platform_provision_tenant.receipt",
        trace_id=marker.record_id,
    )
    try:
        store._store.put(receipt, expected_version=0)
    except VersionConflict:
        current = store._store.get(
            store._tenant, TENANT_PROVISIONING_RECEIPT_KIND, receipt_id
        )
        if current is None or dict(current.payload) != payload:
            raise TenantProvisioningError("provisioning_receipt_conflict")
    return receipt_id


def _completed_result(
    store: "AccountStore",
    payload: Mapping[str, Any],
    api_credential: str,
) -> TenantProvisioningResult:
    reserved = _reserved_account(payload)
    if not credential_matches(
        reserved, api_credential, pepper=store._credential_pepper
    ):
        raise TenantProvisioningError("provisioning_credential_mismatch")
    existing = store.get_account_by_id(reserved.account_id)
    if existing is None or not _same_owner(existing, reserved):
        raise TenantProvisioningError("corrupt_provisioning")
    provisioning_id = str(payload.get("provisioning_id") or "")
    completed_at = str(payload.get("completed_at") or "")
    if not provisioning_id or not completed_at:
        raise TenantProvisioningError("corrupt_provisioning")
    marker = store._store.get(
        store._tenant, TENANT_PROVISIONING_KIND, provisioning_id
    )
    if marker is None:
        raise TenantProvisioningError("corrupt_provisioning")
    receipt_id = _ensure_receipt(store, marker, existing)
    return TenantProvisioningResult(
        provisioning_id=provisioning_id,
        receipt_id=receipt_id,
        account=existing,
        completed_at=completed_at,
    )


def _assert_same_request(
    payload: Mapping[str, Any],
    *,
    tenant: str,
    email: str,
    api_credential: str,
    pepper: str,
) -> None:
    if (
        str(payload.get("tenant_id") or "") != tenant
        or str(payload.get("email_or_username") or "") != email
    ):
        raise TenantProvisioningError("tenant_already_reserved")
    reserved = _reserved_account(payload)
    if not credential_matches(
        reserved, api_credential, pepper=pepper
    ):
        raise TenantProvisioningError("provisioning_credential_mismatch")


def _reserved_account(payload: Mapping[str, Any]) -> Account:
    account_payload = payload.get("account")
    if not isinstance(account_payload, Mapping):
        raise TenantProvisioningError("corrupt_provisioning")
    try:
        account = Account.from_payload(account_payload)
    except (KeyError, TypeError, ValueError) as exc:
        raise TenantProvisioningError("corrupt_provisioning") from exc
    if account.role != "owner":
        raise TenantProvisioningError("corrupt_provisioning")
    return account


def _tenant_has_accounts(store: "AccountStore", tenant_id: str) -> bool:
    return any(
        Account.from_payload(record.payload).tenant_id == tenant_id
        for record in store._store.list(store._tenant, ACCOUNT_KIND)
    )


def _same_owner(existing: Account, reserved: Account) -> bool:
    return (
        existing.account_id == reserved.account_id
        and existing.email_or_username == reserved.email_or_username
        and existing.role == "owner"
        and existing.tenant_id == reserved.tenant_id
        and existing.credential_hash == reserved.credential_hash
    )


def _normalize_tenant_id(raw: str) -> str:
    tenant = (raw or "").strip().lower()
    if not _TENANT_ID_PATTERN.fullmatch(tenant):
        raise TenantProvisioningError("invalid_tenant_id")
    return tenant


def _provisioning_id(tenant: str) -> str:
    digest = hashlib.sha256(
        f"platform-tenant-provisioning:{tenant}".encode("utf-8")
    ).hexdigest()[:32]
    return f"tenantprov-{digest}"


def _receipt_id(provisioning_id: str) -> str:
    return f"tenantprovrct-{provisioning_id.removeprefix('tenantprov-')}"


def _owner_account_id(tenant: str, email: str) -> str:
    digest = hashlib.sha256(
        f"platform-tenant-owner:{tenant}:{email}".encode("utf-8")
    ).hexdigest()[:32]
    return f"acct-{digest}"
