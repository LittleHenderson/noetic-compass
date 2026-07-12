"""Crash-safe invite redemption over the versioned StateStore ledger.

A use is reserved on the invite record before the email index or account becomes visible. The
reservation contains only an account credential derivation nonce and hash, never the bearer value.
Every later write is idempotent, so retrying the same (code, identity) repairs an interrupted
redemption without consuming a second use or minting a second credential.
"""

from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any, Mapping, Optional, TYPE_CHECKING

from api.services.crm.models import normalize_email
from api.services.production.state_substrate import LedgerRecord, VersionConflict

from .credentials import (
    CREDENTIAL_VERSION,
    derive_account_credential,
    hash_account_credential,
    new_credential_nonce,
)
from .invites import is_redeemable
from .models import ACCOUNT_KIND, Account, InviteCode, normalize_role

if TYPE_CHECKING:
    from .store import AccountStore

_RESERVATIONS_KEY = "redemption_reservations"
_MAX_CAS_ATTEMPTS = 12


def redeem_invite_crash_safe(
    store: "AccountStore",
    *,
    code: str,
    email_or_username: str,
    display_name: Optional[str] = None,
) -> Account:
    """Reserve an invite use first, then idempotently materialize its account."""
    from .store import InviteRedemptionError

    normalized_email = normalize_email(email_or_username)
    if not normalized_email:
        raise InviteRedemptionError("invalid_identity")
    account_id = _account_id_for(code=code, normalized_email=normalized_email)

    for _ in range(_MAX_CAS_ATTEMPTS):
        invite_record = store._read_invite_record(code)
        if invite_record is None:
            raise InviteRedemptionError("unknown_code")

        reservations = _reservations(invite_record.payload)
        reserved = reservations.get(account_id)
        if reserved is not None:
            return _materialize(store, invite_record.record_id, reserved)

        invite = InviteCode.from_payload(invite_record.payload)
        if not is_redeemable(invite):
            raise InviteRedemptionError("not_redeemable")
        if invite.target_email is not None and invite.target_email != normalized_email:
            raise InviteRedemptionError("email_mismatch")

        now = datetime.now(UTC).isoformat()
        nonce = new_credential_nonce()
        raw_credential = derive_account_credential(
            pepper=store._credential_pepper, nonce=nonce
        )
        account = Account(
            account_id=account_id,
            email_or_username=normalized_email,
            role=normalize_role(invite.role),
            tenant_id=invite.tenant_id,
            status="active",
            display_name=_clean_display_name(display_name),
            credential_hash=hash_account_credential(raw_credential),
            credential_version=CREDENTIAL_VERSION,
            credential_issued_at=now,
            created_at=now,
            updated_at=now,
        )
        reservation: dict[str, Any] = {
            "account_id": account_id,
            "email_or_username": normalized_email,
            "credential_nonce": nonce,
            "account": account.to_payload(),
            "status": "reserved",
            "reserved_at": now,
        }
        next_payload = dict(invite_record.payload)
        next_reservations = dict(reservations)
        next_reservations[account_id] = reservation
        next_payload[_RESERVATIONS_KEY] = next_reservations
        next_payload["uses"] = invite.uses + 1
        next_payload["redeemed_by"] = invite.redeemed_by or account_id
        next_payload["redeemed_at"] = invite.redeemed_at or now
        try:
            store._store.put(
                invite_record.with_payload(next_payload),
                expected_version=invite_record.version,
            )
        except VersionConflict:
            # Another redeemer changed the invite. Re-read: the same identity resumes the
            # winning reservation, while a different identity re-evaluates the remaining limit.
            continue

        store._fail_after("after_invite_reservation_write")
        return _materialize(store, invite_record.record_id, reservation)

    raise InviteRedemptionError("race_lost")


def _materialize(
    store: "AccountStore",
    invite_record_id: str,
    reservation: Mapping[str, Any],
) -> Account:
    """Idempotently finish all writes after the durable invite reservation."""
    from .store import InviteRedemptionError

    account_payload = reservation.get("account")
    if not isinstance(account_payload, Mapping):
        raise InviteRedemptionError("corrupt_reservation")
    account = Account.from_payload(account_payload)
    nonce = str(reservation.get("credential_nonce") or "")
    if not nonce:
        raise InviteRedemptionError("corrupt_reservation")
    raw_credential = derive_account_credential(
        pepper=store._credential_pepper, nonce=nonce
    )
    if hash_account_credential(raw_credential) != account.credential_hash:
        raise InviteRedemptionError("corrupt_reservation")

    store._claim_email(account.email_or_username, account_id=account.account_id)
    store._fail_after("after_email_index_write")

    existing = store.get_account_by_id(account.account_id)
    if existing is None:
        account_record = LedgerRecord.new(
            tenant_id=store._tenant,
            kind=ACCOUNT_KIND,
            record_id=account.account_id,
            payload=account.to_payload(),
            parent_ids=(invite_record_id,),
            source="accounts.redeem_invite",
            trace_id=account.account_id,
        )
        try:
            store._store.put(account_record, expected_version=0)
        except VersionConflict:
            existing = store.get_account_by_id(account.account_id)
    if existing is not None:
        if not _same_reserved_identity(existing, account):
            raise InviteRedemptionError("account_conflict")
        account = existing
    store._fail_after("after_account_write")

    _mark_complete(store, invite_record_id, account.account_id)
    store._fail_after("after_invite_completion_write")
    return replace(account, api_credential=raw_credential)


def _mark_complete(
    store: "AccountStore", invite_record_id: str, account_id: str
) -> None:
    from .store import INVITE_KIND, InviteRedemptionError

    for _ in range(_MAX_CAS_ATTEMPTS):
        current = store._store.get(store._tenant, INVITE_KIND, invite_record_id)
        if current is None:
            raise InviteRedemptionError("corrupt_reservation")
        reservations = _reservations(current.payload)
        reserved = reservations.get(account_id)
        if reserved is None:
            raise InviteRedemptionError("corrupt_reservation")
        if reserved.get("status") == "completed":
            return
        completed = dict(reserved)
        completed["status"] = "completed"
        completed["completed_at"] = datetime.now(UTC).isoformat()
        next_reservations = dict(reservations)
        next_reservations[account_id] = completed
        next_payload = dict(current.payload)
        next_payload[_RESERVATIONS_KEY] = next_reservations
        try:
            store._store.put(
                current.with_payload(next_payload), expected_version=current.version
            )
            return
        except VersionConflict:
            continue
    raise InviteRedemptionError("race_lost")


def _reservations(payload: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    raw = payload.get(_RESERVATIONS_KEY)
    if not isinstance(raw, Mapping):
        return {}
    return {str(key): value for key, value in raw.items() if isinstance(value, Mapping)}


def _same_reserved_identity(existing: Account, reserved: Account) -> bool:
    return (
        existing.account_id == reserved.account_id
        and existing.email_or_username == reserved.email_or_username
        and existing.role == reserved.role
        and existing.tenant_id == reserved.tenant_id
        and existing.credential_hash == reserved.credential_hash
        and existing.credential_version == reserved.credential_version
    )


def _clean_display_name(raw: Optional[str]) -> Optional[str]:
    if raw is None:
        return None
    return raw.strip() or None


def _account_id_for(*, code: str, normalized_email: str) -> str:
    digest = hashlib.sha256(
        f"account:{code}:{normalized_email}".encode("utf-8")
    ).hexdigest()[:32]
    return f"acct-{digest}"
