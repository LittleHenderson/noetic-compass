"""Atomic first-owner bootstrap over the shared versioned ledger."""

from __future__ import annotations

import hashlib
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

BOOTSTRAP_KIND = "account_bootstrap"
BOOTSTRAP_RECORD_ID = "first-owner"


class AccountBootstrapError(RuntimeError):
    pass


def bootstrap_first_owner(
    store: "AccountStore",
    *,
    email_or_username: str,
    tenant_id: str,
    api_credential: str,
    display_name: Optional[str] = None,
) -> Account:
    """Create one owner using a client-held credential that is safe across response crashes."""
    email = normalize_email(email_or_username)
    tenant = tenant_id.strip()
    try:
        validate_account_credential(api_credential)
    except ValueError as exc:
        raise AccountBootstrapError("invalid_bootstrap_credential") from exc
    if not email or not tenant:
        raise AccountBootstrapError("invalid_bootstrap_identity")

    marker = store._store.get(
        store._tenant, BOOTSTRAP_KIND, BOOTSTRAP_RECORD_ID
    )
    if marker is None:
        if store.has_active_owner(tenant_id=tenant):
            raise AccountBootstrapError("already_bootstrapped")
        account_id = _owner_account_id(email, tenant)
        now = datetime.now(UTC).isoformat()
        account = Account(
            account_id=account_id,
            email_or_username=email,
            role="owner",
            tenant_id=tenant,
            display_name=display_name.strip() if display_name and display_name.strip() else None,
            credential_hash=hash_account_credential(
                api_credential, pepper=store._credential_pepper
            ),
            credential_version=CREDENTIAL_VERSION,
            credential_issued_at=now,
            created_at=now,
            updated_at=now,
        )
        reservation: dict[str, Any] = {
            "status": "reserved",
            "email_or_username": email,
            "tenant_id": tenant,
            "account": account.to_payload(),
            "reserved_at": now,
        }
        candidate = LedgerRecord.new(
            tenant_id=store._tenant,
            kind=BOOTSTRAP_KIND,
            record_id=BOOTSTRAP_RECORD_ID,
            payload=reservation,
            source="accounts.bootstrap_owner",
            trace_id=account_id,
        )
        try:
            marker = store._store.put(candidate, expected_version=0)
            store._fail_after("after_bootstrap_reservation_write")
        except VersionConflict:
            marker = store._store.get(
                store._tenant, BOOTSTRAP_KIND, BOOTSTRAP_RECORD_ID
            )
            if marker is None:
                raise AccountBootstrapError("bootstrap_race_lost")
    payload = marker.payload
    if (
        str(payload.get("email_or_username") or "") != email
        or str(payload.get("tenant_id") or "") != tenant
    ):
        raise AccountBootstrapError("already_bootstrapped")
    if payload.get("status") == "completed":
        return _completed_owner(store, payload, api_credential)
    return _materialize_owner(store, marker, payload, api_credential)


def _materialize_owner(
    store: "AccountStore",
    marker: LedgerRecord,
    payload: Mapping[str, Any],
    api_credential: str,
) -> Account:
    account_payload = payload.get("account")
    if not isinstance(account_payload, Mapping):
        raise AccountBootstrapError("corrupt_bootstrap")
    account = Account.from_payload(account_payload)
    if not credential_matches(
        account, api_credential, pepper=store._credential_pepper
    ):
        raise AccountBootstrapError("already_bootstrapped")

    store._claim_email(account.email_or_username, account_id=account.account_id)
    store._fail_after("after_bootstrap_email_write")
    existing = store.get_account_by_id(account.account_id)
    if existing is None:
        record = LedgerRecord.new(
            tenant_id=store._tenant,
            kind=ACCOUNT_KIND,
            record_id=account.account_id,
            payload=account.to_payload(),
            parent_ids=(BOOTSTRAP_RECORD_ID,),
            source="accounts.bootstrap_owner",
            trace_id=account.account_id,
        )
        try:
            store._store.put(record, expected_version=0)
        except VersionConflict:
            existing = store.get_account_by_id(account.account_id)
    if existing is not None:
        if not _same_owner(existing, account):
            raise AccountBootstrapError("bootstrap_account_conflict")
        account = existing
    store._fail_after("after_bootstrap_account_write")

    completed_here = _complete_marker(store, account.account_id)
    store._fail_after("after_bootstrap_completion_write")
    if not completed_here:
        return account
    return account


def _complete_marker(store: "AccountStore", account_id: str) -> bool:
    for _ in range(12):
        marker = store._store.get(
            store._tenant, BOOTSTRAP_KIND, BOOTSTRAP_RECORD_ID
        )
        if marker is None:
            raise AccountBootstrapError("corrupt_bootstrap")
        if marker.payload.get("status") == "completed":
            return False
        completed = dict(marker.payload)
        completed["status"] = "completed"
        completed["completed_at"] = datetime.now(UTC).isoformat()
        completed.pop("credential_nonce", None)
        try:
            store._store.put(
                marker.with_payload(completed), expected_version=marker.version
            )
            return True
        except VersionConflict:
            continue
    raise AccountBootstrapError("bootstrap_race_lost")


def _completed_owner(
    store: "AccountStore", payload: Mapping[str, Any], api_credential: str
) -> Account:
    account_payload = payload.get("account")
    if not isinstance(account_payload, Mapping):
        raise AccountBootstrapError("corrupt_bootstrap")
    reserved = Account.from_payload(account_payload)
    if not credential_matches(
        reserved, api_credential, pepper=store._credential_pepper
    ):
        raise AccountBootstrapError("bootstrap_credential_mismatch")
    existing = store.get_account_by_id(reserved.account_id)
    if existing is None or not _same_owner(existing, reserved):
        raise AccountBootstrapError("corrupt_bootstrap")
    return existing


def _same_owner(existing: Account, reserved: Account) -> bool:
    return (
        existing.account_id == reserved.account_id
        and existing.email_or_username == reserved.email_or_username
        and existing.role == "owner"
        and existing.tenant_id == reserved.tenant_id
        and existing.credential_hash == reserved.credential_hash
    )


def _owner_account_id(email: str, tenant: str) -> str:
    digest = hashlib.sha256(
        f"bootstrap-owner:{tenant}:{email}".encode("utf-8")
    ).hexdigest()[:32]
    return f"acct-{digest}"


def recover_bootstrap_owner(
    store: "AccountStore",
    *,
    email_or_username: str,
    tenant_id: str,
    new_credential: str,
) -> Account:
    """Reset only the completed first-owner record using the still-configured bootstrap gate."""
    email = normalize_email(email_or_username)
    tenant = tenant_id.strip()
    try:
        validate_account_credential(new_credential)
    except ValueError as exc:
        raise AccountBootstrapError("invalid_bootstrap_credential") from exc
    marker = store._store.get(
        store._tenant, BOOTSTRAP_KIND, BOOTSTRAP_RECORD_ID
    )
    if marker is None or marker.payload.get("status") != "completed":
        raise AccountBootstrapError("bootstrap_recovery_unavailable")
    if (
        str(marker.payload.get("email_or_username") or "") != email
        or str(marker.payload.get("tenant_id") or "") != tenant
    ):
        raise AccountBootstrapError("bootstrap_recovery_unavailable")
    account_payload = marker.payload.get("account")
    if not isinstance(account_payload, Mapping):
        raise AccountBootstrapError("corrupt_bootstrap")
    account_id = Account.from_payload(account_payload).account_id
    current = store.get_account_by_id(account_id)
    if current is None or current.role != "owner" or current.tenant_id != tenant:
        raise AccountBootstrapError("bootstrap_recovery_unavailable")
    rotated = store.rotate_account_credential(
        account_id, new_credential=new_credential
    )
    if rotated is None:
        raise AccountBootstrapError("bootstrap_recovery_unavailable")
    return rotated
