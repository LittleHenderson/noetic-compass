"""CAS Harness tenant-isolation seam (workstream 06, design-stage scaffold).

Import-isolated: nothing here is wired into the live FastAPI app, the auth
middleware, or the fleet executor. It exists so the blueprint in
``docs/working/production_readiness/06_tenant_isolation.md`` has a concrete seam
the team can build against, and so the cross-tenant fail-closed contract is
expressed as runnable code + a test rather than prose.

Honesty rule for this module (see ``production/__init__.py:9-12``):
    The in-memory stubs below prove EXACTLY ONE thing honestly --- *logical*
    partitioning within a single process (a tenant-B context cannot reach a
    tenant-A value or key *here*). They DO NOT provide, and MUST NOT claim,
    at-rest encryption, cross-host durability, or KMS-backed key isolation.
    ``InMemoryTenantKeyProvider.supports_kms()`` returns ``False`` precisely so
    that no ``*_KEY_KMS_BACKED`` / ``*_ENCRYPTED_AT_REST`` status may ever be
    emitted from this backend. A stub is a stub.

Fail-closed is the spine of this module: on ANY ambiguity --- a missing/empty
tenant id, or a record whose owning tenant is ``None`` --- the guard RAISES.
It never "defaults to a shared tenant" and never "allows and logs".
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
from typing import Generic, Protocol, TypeVar, runtime_checkable

T = TypeVar("T")


# --------------------------------------------------------------------------- #
# Errors --- every one of these is a FAIL-CLOSED outcome.                      #
# --------------------------------------------------------------------------- #
class TenantResolutionError(ValueError):
    """The acting tenant could not be resolved (missing/empty/untrusted).

    Deny on ambiguity; never default to a shared tenant.
    """


class CrossTenantAccessError(PermissionError):
    """A context for tenant A touched data owned by tenant B.

    The HTTP layer maps this to **404** (not 403): do not even confirm that the
    foreign id exists.
    """


class QuotaError(PermissionError):
    """A tenant exceeded a :class:`QuotaPolicy` limit (HTTP 429).

    Carries the charged tenant so the refusal is attributable (billing 08 /
    audit 09).
    """

    def __init__(self, tenant_id: str, limit_name: str, limit: int | float, observed: int | float):
        self.tenant_id = tenant_id
        self.limit_name = limit_name
        self.limit = limit
        self.observed = observed
        super().__init__(
            f"tenant {tenant_id!r} exceeded {limit_name} (limit={limit}, observed={observed})"
        )


# --------------------------------------------------------------------------- #
# TenantContext --- derived ONCE at the edge, threaded down.                   #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class TenantContext:
    """The resolved acting tenant for one request.

    Built once in auth middleware (where ``request.state.user`` /
    ``request.state.api_key`` are set today --- ``api/middleware/auth.py:78-79``)
    and passed down; never re-derived ad hoc deeper in the stack.
    """

    tenant_id: str
    principal: str

    def __post_init__(self) -> None:
        if not self.tenant_id or not self.tenant_id.strip():
            # Fail closed: a blank tenant is not a tenant.
            raise TenantResolutionError("TenantContext requires a non-empty tenant_id")
        if not self.principal or not self.principal.strip():
            raise TenantResolutionError("TenantContext requires a non-empty principal")


# --------------------------------------------------------------------------- #
# IsolationGuard --- the single chokepoint before touching tenant data.       #
# --------------------------------------------------------------------------- #
class IsolationGuard:
    """Assert that a context may touch data owned by ``owner_tenant_id``.

    This is intentionally a tiny, boring, *un-overridable* function: it is the
    one place the cross-tenant boundary is enforced, so it must be impossible to
    accidentally weaken. Fail-closed on ambiguity.
    """

    @staticmethod
    def assert_same_tenant(ctx: TenantContext, owner_tenant_id: str | None) -> None:
        if owner_tenant_id is None or not str(owner_tenant_id).strip():
            # Ambiguous ownership is a denial, not a pass. An object that cannot
            # name its owning tenant is unreachable by everyone.
            raise CrossTenantAccessError(
                "object has no owning tenant_id; refusing access (fail-closed)"
            )
        if not hmac.compare_digest(str(ctx.tenant_id), str(owner_tenant_id)):
            raise CrossTenantAccessError(
                "cross-tenant access denied"  # deliberately does not echo the foreign id
            )


# --------------------------------------------------------------------------- #
# TenantScopedStore --- the tenant is PART OF the key.                         #
# --------------------------------------------------------------------------- #
@runtime_checkable
class TenantScopedStore(Protocol[T]):
    """Key/value store where a read for tenant A cannot return tenant B's value.

    The production replacement for process-global dicts like
    ``_DISTRIBUTED_AUDITS`` (``cas_harness_distributed_audits.py:158``). Note
    there is no un-scoped ``get(key)`` --- every method takes a
    :class:`TenantContext`, so the tenant is structurally part of every lookup.
    """

    def put(self, ctx: TenantContext, key: str, value: T) -> None: ...

    def get(self, ctx: TenantContext, key: str) -> T | None: ...

    def list_for_tenant(self, ctx: TenantContext) -> list[T]: ...

    def delete(self, ctx: TenantContext, key: str) -> bool: ...


class InMemoryTenantScopedStore(Generic[T]):
    """Labeled in-memory :class:`TenantScopedStore` stub --- logical isolation only.

    For tests and design. The backing dict is keyed by ``(tenant_id, key)`` so a
    tenant-B context **cannot construct** a lookup that returns a tenant-A value:
    isolation is by key construction, not by a guard the caller could forget. It
    provides NO durability and NO at-rest encryption and never claims them.
    Vanishes on process exit --- which is exactly why a real, tenant-partitioned
    backend is required for production (blueprint section 3, Phase B).
    """

    def __init__(self) -> None:
        # Composite key (tenant_id, key). There is deliberately no flat {key: value}
        # surface that an un-scoped accessor could reach.
        self._data: dict[tuple[str, str], T] = {}

    def put(self, ctx: TenantContext, key: str, value: T) -> None:
        self._data[(ctx.tenant_id, key)] = value

    def get(self, ctx: TenantContext, key: str) -> T | None:
        # Only this tenant's partition is addressable. A foreign key simply is
        # not present under this tenant --- returns None, never the other tenant's
        # value, and never signals that the id exists elsewhere.
        return self._data.get((ctx.tenant_id, key))

    def list_for_tenant(self, ctx: TenantContext) -> list[T]:
        return [value for (tenant_id, _key), value in self._data.items() if tenant_id == ctx.tenant_id]

    def delete(self, ctx: TenantContext, key: str) -> bool:
        return self._data.pop((ctx.tenant_id, key), None) is not None

    # Test/diagnostic only --- NOT part of the Protocol. Proves the boundary is
    # real by exposing the global count the per-tenant views never reveal.
    def _total_entries_all_tenants(self) -> int:
        return len(self._data)


# --------------------------------------------------------------------------- #
# TenantKeyProvider --- per-tenant data key for the gate-8 harvest bytes.      #
# --------------------------------------------------------------------------- #
class TenantKeyProvider(Protocol):
    """Per-tenant data-key provider (02 stores ciphertext; 07 retains it; 06 owns the key).

    Real backend: a per-tenant data key wrapped by a KMS root (envelope
    encryption). STUBS MUST NOT CLAIM CRYPTOGRAPHIC ISOLATION (see module docstring).
    """

    def data_key(self, ctx: TenantContext) -> bytes: ...

    def wrap(self, ctx: TenantContext, plaintext: bytes) -> bytes: ...

    def unwrap(self, ctx: TenantContext, ciphertext: bytes) -> bytes: ...

    def supports_kms(self) -> bool: ...


class InMemoryTenantKeyProvider:
    """Labeled stub key provider --- derivation/labeling ONLY, NOT cryptography.

    ``wrap``/``unwrap`` apply a per-tenant XOR keystream so that bytes written
    under tenant A's key are not readable with tenant B's key *in this process* ---
    enough to demonstrate the per-tenant key boundary and the fail-closed
    contract in a test. This is **obfuscation, not encryption**:
    ``supports_kms()`` returns ``False`` precisely so the honest-status layer can
    never emit a ``*_KEY_KMS_BACKED`` / ``*_ENCRYPTED_AT_REST`` claim from it.
    Production flip = a real KMS/HSM-backed provider.
    """

    def __init__(self, root_secret: bytes = b"DESIGN-STUB-ROOT-NOT-A-REAL-KEY") -> None:
        self._root_secret = root_secret

    def data_key(self, ctx: TenantContext) -> bytes:
        # Deterministic per-tenant derivation from the root. A real provider
        # would fetch a wrapped data key and unwrap it via KMS.
        return hashlib.sha256(self._root_secret + b"|" + ctx.tenant_id.encode("utf-8")).digest()

    def _keystream(self, key: bytes, length: int) -> bytes:
        out = bytearray()
        counter = 0
        while len(out) < length:
            block = hashlib.sha256(key + counter.to_bytes(8, "big")).digest()
            out.extend(block)
            counter += 1
        return bytes(out[:length])

    def wrap(self, ctx: TenantContext, plaintext: bytes) -> bytes:
        key = self.data_key(ctx)  # raises via TenantContext if ctx is malformed
        stream = self._keystream(key, len(plaintext))
        return bytes(p ^ s for p, s in zip(plaintext, stream))

    def unwrap(self, ctx: TenantContext, ciphertext: bytes) -> bytes:
        # Symmetric XOR. With the wrong tenant's key this returns garbage, which
        # is the point: a foreign key cannot recover plaintext. (A real provider
        # would additionally AEAD-authenticate and RAISE on wrong key.)
        return self.wrap(ctx, ciphertext)

    def supports_kms(self) -> bool:
        return False  # honest: this stub is not KMS-backed and is not encryption.


# --------------------------------------------------------------------------- #
# QuotaPolicy --- per-tenant limits on the EXPENSIVE axis.                     #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class QuotaPolicy:
    """Per-tenant limits on fleet consumption, not just HTTP rpm. 0 == unlimited."""

    tenant_id: str
    max_concurrent_audits: int = 0
    max_worker_fanout: int = 0
    gpu_hours_per_month: float = 0.0
    bytes_stored: int = 0
    requests_per_minute: int = 0

    def check_concurrent_audits(self, observed: int) -> None:
        if self.max_concurrent_audits and observed >= self.max_concurrent_audits:
            raise QuotaError(self.tenant_id, "max_concurrent_audits", self.max_concurrent_audits, observed)

    def check_worker_fanout(self, observed: int) -> None:
        if self.max_worker_fanout and observed > self.max_worker_fanout:
            raise QuotaError(self.tenant_id, "max_worker_fanout", self.max_worker_fanout, observed)
