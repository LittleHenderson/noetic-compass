"""CRM lead-capture orchestration — capture first, sync second, never lose a lead.

:class:`CRMService` is the one place the pieces meet: it validates an inbound
:class:`~api.services.crm.models.LeadSubmission`, persists the lead **captured** before any sync is
attempted, then asks the configured :class:`~api.services.crm.sync.CRMSyncProvider` to land it and
records the honest outcome. The ordering is the whole point and is load-bearing:

1. **Capture is durable before sync is tried.** We ``save`` the ``captured`` lead first, so if the
   sync call (or the whole process) dies mid-attempt, the lead is already safely on our side. A
   prospect who submitted is never lost to a flaky external CRM.
2. **Sync only ever *annotates*.** The sync outcome is folded in via ``Lead.with_sync_result`` —
   a new version, never a mutation, never a deletion. A real landing → ``synced`` + ``external_id``;
   a real provider that errored → ``sync_failed`` (recorded, not swallowed); the dark null provider
   → ``sync_pending`` (attempted, nothing landed). The lead survives every one of these.
3. **A provider that raises cannot lose the lead.** If ``sync_lead`` throws, we catch it and still
   produce a ``sync_failed`` annotation off the captured lead — the exception becomes recorded
   evidence, not a dropped record.

Lineage: a repeat submission from the same (normalized) email is linked to its most recent
predecessor via ``parent_ids``, so the second time someone reaches out we can walk back to the
first. Same traceability spine the rest of the platform runs on.
"""

from __future__ import annotations

from api.services.crm.models import (
    CRMSyncResult,
    Lead,
    LeadSubmission,
    _now_iso,
)
from api.services.crm.store import (
    InMemoryLeadStore,
    JsonlFileLeadStore,
    LeadStore,
)
from api.services.crm.sync import CRMSyncProvider, NullCRMProvider, build_crm_provider


class CRMService:
    """Validate → capture (durable) → sync (annotate). The lead is safe after step 2.

    Depends only on the :class:`LeadStore` and :class:`CRMSyncProvider` seams, so swapping the
    in-memory store for a durable file (or the null provider for a real CRM) changes nothing here.
    """

    def __init__(self, store: LeadStore, provider: CRMSyncProvider) -> None:
        self._store = store
        self._provider = provider

    @property
    def store(self) -> LeadStore:
        return self._store

    @property
    def provider(self) -> CRMSyncProvider:
        return self._provider

    def capture(
        self,
        submission: LeadSubmission,
        *,
        source: str,
        trace_id: str | None,
    ) -> Lead:
        """Capture a submission as a durable lead, then attempt sync and annotate the outcome.

        Raises :class:`~api.services.crm.models.LeadValidationError` if the submission is unusable
        (no contactable email) — the caller turns that into a 4xx at the HTTP edge. On success the
        returned lead is the post-sync version: ``synced`` only if a real provider actually landed
        it, otherwise ``sync_pending`` (dark default) or ``sync_failed`` (real provider errored).
        """
        # 1. Validate at the boundary. A junk submission never becomes a stored lead.
        validated = submission.validated()

        # 2. Lineage: link a repeat submission to its most recent predecessor for this email.
        prior = self._store.find_by_email(validated.email)
        parent_ids = (prior[-1].lead_id,) if prior else ()

        # 3. Capture DURABLY before any sync is attempted. This is the safety guarantee.
        captured = Lead.from_submission(
            validated,
            source=source,
            trace_id=trace_id,
            parent_ids=parent_ids,
        )
        self._store.save(captured)

        # 4. Attempt sync. A provider that raises must NOT lose the captured lead — its failure is
        #    recorded as a sync_failed annotation (is_real=True drives that mapping), not swallowed.
        try:
            result = self._provider.sync_lead(captured)
        except Exception as exc:  # noqa: BLE001 — any provider error becomes recorded evidence
            result = CRMSyncResult(
                provider=getattr(self._provider, "provider_name", "unknown"),
                synced=False,
                is_real=getattr(self._provider, "is_real", True),
                external_id=None,
                synced_at=_now_iso(),
                note=f"sync attempt raised {type(exc).__name__}: {exc}",
            )

        # 5. Fold the outcome in as a new version and persist it. Never a mutation of the captured
        #    record — an immutable annotation that preserves the capture → sync lineage.
        annotated = captured.with_sync_result(result)
        return self._store.save(annotated)

    def get_lead(self, lead_id: str) -> Lead | None:
        return self._store.get(lead_id)

    def list_leads(self) -> list[Lead]:
        return self._store.list_all()


def build_lead_store(settings) -> LeadStore:
    """Pick the lead store from config: durable file if a path is set, else in-memory (dark).

    ``NC_CRM_LEAD_STORE_PATH`` set → :class:`JsonlFileLeadStore` (real single-host durability).
    Unset → :class:`InMemoryLeadStore`, which is honest that it forgets on restart. A production
    deployment that means to keep its leads sets the path; an unconfigured one boots and works but
    does not pretend its leads are durable.
    """
    path = (getattr(settings, "crm_lead_store_path", None) or "").strip()
    if path:
        return JsonlFileLeadStore(path)
    return InMemoryLeadStore()


def build_crm_service(settings) -> CRMService:
    """Assemble the CRM service from settings: a lead store + a sync provider.

    Fails loud (via :func:`~api.services.crm.sync.build_crm_provider`) if configured for a provider
    we have not implemented, rather than booting a CRM that would silently sync nothing.
    """
    store = build_lead_store(settings)
    provider = build_crm_provider(settings)
    return CRMService(store, provider)


# Re-exported so callers can build a fully dark, in-memory service in one call (tests, the
# zero-config default) without reaching for the individual pieces.
def build_dark_crm_service() -> CRMService:
    """A fully dark CRM service: in-memory store + null provider. Captures, never syncs."""
    return CRMService(InMemoryLeadStore(), NullCRMProvider())
