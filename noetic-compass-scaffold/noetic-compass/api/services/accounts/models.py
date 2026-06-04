"""Account + InviteCode value objects -- the identity half of the PAID-user security spine.

This is the FIRST real account entity in the repo. Until now the only ``Account`` was the
import-isolated billing *stub* (``api/services/production/billing.py:91``) which carries only
``id``/``tenant_id``/``status``/``created_at`` -- no email, no role, no login. These dataclasses
extend that field *shape* (same ``tenant_id``/``status``/``created_at`` spine, ``id`` -> the more
explicit ``account_id``) and add the fields a real login needs: ``email_or_username`` (the unique
identity a token is minted against), ``display_name``, ``role``, and ``updated_at``. We do NOT
import the billing stub -- it is a design-stage sketch, not a wired entity (see
``production/__init__.py`` honesty rule).

Persistence note: these objects are stored through the durable ``StateStore`` Protocol as record
``kind``s ``"account"`` and ``"invite"`` (see ``store.py``). The (de)serialization helpers here
translate between the dataclass and the ledger record's opaque ``payload`` mapping. The ledger
envelope (``parent_ids``/``source``/``trace_id``) carries the project's load-bearing object
traceability for free -- every account and invite knows where it came from.

Honesty: nothing here invents capability. An ``Account`` is a durable record of identity + role;
it does not imply billing, a paid plan, or any proof verdict. Quota/billing fields and their
enforcement are a LATER PR (Phase 4) -- deliberately absent so this record cannot be mistaken for
a billing entitlement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal, Mapping, Optional


# Schema versions stamped into the persisted payload so a future migration can tell which shape a
# stored record was written under. Mirrors ``BILLING_SCHEMA_VERSION`` in billing.py.
ACCOUNT_SCHEMA_VERSION = "cas_accounts.account.v1"
INVITE_SCHEMA_VERSION = "cas_accounts.invite.v1"

# Ledger record kinds. The generic ``kind``-keyed ``ledger_records`` table holds these; no new
# store engine or table is introduced (the StateStore is the single persistence seam).
ACCOUNT_KIND = "account"
INVITE_KIND = "invite"
# An auxiliary index record keyed by normalized email. It exists ONLY to make email uniqueness a
# version-checked, fail-closed fact at the storage layer (see store.py): two concurrent redeems
# for the same email race on creating this record at version 0, and exactly one wins.
ACCOUNT_EMAIL_INDEX_KIND = "account_email_index"


# Role vocabulary. Invite-created accounts default to ``member`` (the least-privileged real role);
# the privileged roles are assigned out-of-band (a later RBAC PR governs who may mint them). The
# ordering here is documentation, not a precedence claim -- precedence/RBAC is Phase 5.
Role = Literal["owner", "admin", "member", "support", "operator", "system"]
ROLE_VALUES: tuple[Role, ...] = ("owner", "admin", "member", "support", "operator", "system")
DEFAULT_INVITE_ROLE: Role = "member"

# Account lifecycle. ``active`` may log in; ``disabled`` is locked out at login (the disabled-user
# lockout the spine acceptance gate requires).
AccountStatus = Literal["active", "disabled"]


def _utc_now_iso() -> str:
    """ISO-8601, timezone-aware UTC -- matches the audit-session store's timestamp format."""
    return datetime.now(UTC).isoformat()


def normalize_role(raw: Any) -> Role:
    """Coerce an arbitrary value to a valid :data:`Role`, or raise.

    Used wherever a role enters from a less-trusted edge (e.g. an invite-create request). A role
    that is not in the vocabulary is refused rather than silently downgraded, so a typo cannot
    mint a surprising privilege level.
    """
    if isinstance(raw, str) and raw in ROLE_VALUES:
        return raw  # type: ignore[return-value]
    raise ValueError(
        f"invalid role {raw!r}; must be one of {', '.join(ROLE_VALUES)}"
    )


@dataclass(frozen=True)
class Account:
    """A durable identity record -- the entity a JWT is minted against.

    ``account_id`` and ``tenant_id`` are SERVER-DERIVED and stable; a token's account/tenant/role
    claims are read off this record, never off a request body. ``email_or_username`` is the unique
    login identity (already normalized -- lowercased/trimmed -- by the store before persistence).
    """

    account_id: str
    email_or_username: str
    role: Role
    tenant_id: str
    status: AccountStatus = "active"
    display_name: Optional[str] = None
    created_at: str = field(default_factory=_utc_now_iso)
    updated_at: str = field(default_factory=_utc_now_iso)

    @property
    def is_active(self) -> bool:
        return self.status == "active"

    def to_dict(self) -> dict[str, Any]:
        """Public projection. The account record holds no secret, so every field is returned.

        (Contrast the audit-session ``to_dict`` which strips an internal owner key; an account has
        no such hidden field -- identity here IS the public contract.)
        """
        return {
            "account_id": self.account_id,
            "email_or_username": self.email_or_username,
            "role": self.role,
            "tenant_id": self.tenant_id,
            "status": self.status,
            "display_name": self.display_name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def to_payload(self) -> dict[str, Any]:
        """The mapping persisted in a ``kind="account"`` ledger record's ``payload``."""
        payload = self.to_dict()
        payload["schema_version"] = ACCOUNT_SCHEMA_VERSION
        return payload

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "Account":
        """Rebuild an :class:`Account` from a stored ledger payload."""
        return cls(
            account_id=str(payload["account_id"]),
            email_or_username=str(payload["email_or_username"]),
            role=normalize_role(payload["role"]),
            tenant_id=str(payload["tenant_id"]),
            status=_coerce_account_status(payload.get("status", "active")),
            display_name=_opt_str(payload.get("display_name")),
            created_at=str(payload.get("created_at") or _utc_now_iso()),
            updated_at=str(payload.get("updated_at") or _utc_now_iso()),
        )


@dataclass(frozen=True)
class InviteCode:
    """A server-issued, single-or-limited-use credential that redeems into exactly one account.

    The ``code`` is cryptographically random (see ``invites.py``). ``role``/``tenant_id`` are the
    server-side facts a redeemed account inherits -- they are decided at invite-creation time and
    are NOT overridable by the redeeming client. ``target_email`` optionally pins the invite to a
    single address. ``uses``/``max_uses`` are the use-limit counters; ``redeemed_by``/
    ``redeemed_at`` record the FIRST redemption for traceability.
    """

    code: str
    role: Role
    tenant_id: str
    target_email: Optional[str] = None
    expires_at: Optional[str] = None  # ISO-8601 UTC; None == no expiry
    max_uses: int = 1
    uses: int = 0
    redeemed_by: Optional[str] = None  # account_id of the first redeemer
    redeemed_at: Optional[str] = None
    created_at: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "role": self.role,
            "tenant_id": self.tenant_id,
            "target_email": self.target_email,
            "expires_at": self.expires_at,
            "max_uses": self.max_uses,
            "uses": self.uses,
            "redeemed_by": self.redeemed_by,
            "redeemed_at": self.redeemed_at,
            "created_at": self.created_at,
        }

    def to_payload(self) -> dict[str, Any]:
        payload = self.to_dict()
        payload["schema_version"] = INVITE_SCHEMA_VERSION
        return payload

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "InviteCode":
        return cls(
            code=str(payload["code"]),
            role=normalize_role(payload["role"]),
            tenant_id=str(payload["tenant_id"]),
            target_email=_opt_str(payload.get("target_email")),
            expires_at=_opt_str(payload.get("expires_at")),
            max_uses=int(payload.get("max_uses", 1)),
            uses=int(payload.get("uses", 0)),
            redeemed_by=_opt_str(payload.get("redeemed_by")),
            redeemed_at=_opt_str(payload.get("redeemed_at")),
            created_at=str(payload.get("created_at") or _utc_now_iso()),
        )


def _opt_str(value: Any) -> Optional[str]:
    """Coerce to a non-empty string or ``None`` (treat blank/missing as absent)."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _coerce_account_status(raw: Any) -> AccountStatus:
    if raw in ("active", "disabled"):
        return raw  # type: ignore[return-value]
    # An unknown status fails CLOSED to ``disabled`` rather than silently treating an
    # unrecognised value as ``active``: a corrupt/forward-version record must not grant access.
    return "disabled"
