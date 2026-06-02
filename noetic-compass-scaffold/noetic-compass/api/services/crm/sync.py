"""External-CRM sync seam — the only place a lead can earn the word ``synced``.

This is the boundary between "captured on our side" and "landed in the external CRM of record"
(Airtable / HubSpot / …). It mirrors the honesty discipline of
``api/services/production/billing.py``'s ``PaymentProvider``: the seam is an ABC the real
integrations implement, and the shipped default is a **stub that advertises its own no-op** — it
never moves a lead into an external system and never claims it did.

The load-bearing rule (from :mod:`.models`)
-------------------------------------------
Only a real provider that actually wrote to the external CRM may return a
:class:`~api.services.crm.models.CRMSyncResult` with ``synced=True`` — and that result structurally
*must* carry a real ``external_id`` and ``is_real=True`` (``CRMSyncResult.__post_init__`` refuses
anything less). The :class:`NullCRMProvider` therefore **cannot** produce a synced landing even by
mistake: it returns ``synced=False, is_real=False``. So a deployment running the dark default leaves
every lead at ``captured`` → ``sync_pending`` ("attempted, nothing left the building"), which is the
honest state when no external CRM is wired.

Why the factory fails loud
--------------------------
:func:`build_crm_provider` returns the null provider for the default ``crm_provider="null"``. If an
operator asks for ``"airtable"`` or ``"hubspot"`` — providers we have **not** built yet — it raises
rather than silently handing back a stub. Silently falling back to a no-op while the operator
believes leads are syncing to HubSpot is the exact declared-vs-verified violation this seam exists
to prevent: it would look like sync works while no lead ever lands. A loud startup failure the
operator can see and fix is the honest outcome (same discipline as ``install_state_ledger``).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from api.services.crm.models import CRMSyncResult, Lead, _now_iso


class CRMConfigError(ValueError):
    """Raised when the CRM is configured to use a provider that is not available/implemented.

    Asking for a real external CRM we have not built yet must fail loudly at construction, never
    degrade to a silent no-op that looks like a working sync.
    """


class CRMSyncProvider(ABC):
    """The seam a real external-CRM integration implements.

    A concrete provider's :meth:`sync_lead` does the real network write to Airtable/HubSpot/… and
    returns a :class:`CRMSyncResult` carrying the external record id on success. ``provider_name``
    and ``is_real`` let the orchestrating service annotate a *failed* attempt honestly (real
    provider that errored → ``sync_failed``) without having to know the concrete type — see
    :meth:`~api.services.crm.service.CRMService.capture`.
    """

    #: Stable identifier of this provider ("null" | "airtable" | "hubspot" | …).
    provider_name: str = "abstract"

    #: Whether this provider actually talks to an external CRM. The null stub sets this False so a
    #: failure on it maps to ``sync_pending`` (a no-op cannot "fail"), while a real provider's
    #: failure maps to ``sync_failed``.
    is_real: bool = False

    @abstractmethod
    def sync_lead(self, lead: Lead) -> CRMSyncResult:
        """Attempt to land ``lead`` in the external CRM and report the honest outcome."""
        ...


class NullCRMProvider(CRMSyncProvider):
    """The dark default. Never contacts an external CRM; never claims a landing.

    This is the CRM analog of ``billing.py``'s ``StubPaymentProvider``: it exists so lead capture
    works end-to-end (and is unit-testable) with zero external configuration, and it is structurally
    incapable of dishonesty — it returns ``synced=False, is_real=False`` with no ``external_id``, so
    the lead settles at ``sync_pending``. A deployment that wants leads to actually reach an external
    CRM must configure a real provider; until then, the honest posture is "captured locally, nothing
    synced", and that is exactly what this returns.
    """

    provider_name = "null"
    is_real = False

    def sync_lead(self, lead: Lead) -> CRMSyncResult:
        return CRMSyncResult(
            provider=self.provider_name,
            synced=False,
            is_real=False,
            external_id=None,
            synced_at=_now_iso(),
            note=(
                "null CRM provider: lead captured locally, no external CRM configured, so nothing "
                "was synced. Configure NC_CRM_PROVIDER (airtable|hubspot) with credentials to land "
                "leads in an external CRM of record."
            ),
        )


def build_crm_provider(settings) -> CRMSyncProvider:
    """Construct the configured sync provider, or fail loud for one we have not built.

    * ``"null"`` (the default) → :class:`NullCRMProvider`: dark, no external landing, honest.
    * ``"airtable"`` / ``"hubspot"`` → :class:`CRMConfigError`. The seam is declared but the real
      integration is not implemented; refusing here keeps an operator from believing leads are
      syncing when no provider exists to sync them. When these are built, they slot in *here* and
      nowhere else changes.

    Any other value is an outright misconfiguration and also raises.
    """
    provider = (getattr(settings, "crm_provider", "null") or "null").strip().lower()
    if provider == "null":
        return NullCRMProvider()
    if provider in ("airtable", "hubspot"):
        raise CRMConfigError(
            f"CRM provider {provider!r} is declared but not yet implemented. The sync seam exists "
            f"(api/services/crm/sync.py) but no real {provider} integration has been built, so it "
            f"cannot land leads. Refusing to start with a provider that would silently sync "
            f"nothing. Use NC_CRM_PROVIDER=null (capture-only) until the integration ships."
        )
    raise CRMConfigError(
        f"unknown CRM provider {provider!r}; valid values are 'null' (default, capture-only), "
        f"'airtable', or 'hubspot' (the latter two not yet implemented)."
    )
