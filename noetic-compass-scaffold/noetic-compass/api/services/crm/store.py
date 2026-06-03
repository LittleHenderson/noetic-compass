"""Lead persistence seam — where a captured lead becomes durable to *us*.

This is the storage half of the CAPTURED-vs-SYNCED honesty rule in :mod:`.models`. ``captured``
means "durably persisted on our side" — and that durability claim is only as honest as the store
behind it. So this module ships two backends and is loud about the difference:

* :class:`InMemoryLeadStore` — the dark, non-durable default. Holds leads in a dict that vanishes
  on process exit. It proves the contract for tests and lets the app boot with zero config, but it
  is **not** durable and never pretends to be. A lead captured into it is gone on restart — which,
  for a revenue record of record, is exactly the loss we refuse to hide.
* :class:`JsonlFileLeadStore` — an append-only JSON-lines file. Real single-host durability: every
  saved lead version is appended and fsync'd, and a restarted process replays the file so the leads
  it captured before the restart come back. This is what a deployment that actually wants to keep
  its leads configures (``NC_CRM_LEAD_STORE_PATH``). It is honestly single-host — one file on one
  disk — not a replicated multi-host database; that is a later backend swap behind the same seam.

Append-only is deliberate. A :class:`~api.services.crm.models.Lead` is immutable and versioned: a
sync attempt produces a *new* version (``with_sync_result`` bumps ``version``), it never mutates the
old one. So the honest on-disk shape is an event log — one line per saved version — and the latest
version per ``lead_id`` wins on replay. Nothing is ever overwritten or deleted, so the lineage of a
lead (capture → sync attempt → …) is recoverable from the file itself. Show your work.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Protocol, runtime_checkable

from api.services.crm.models import Lead, normalize_email


@runtime_checkable
class LeadStore(Protocol):
    """The seam every lead backend implements; the service depends on this, not a concrete store.

    ``save`` is an upsert-by-``lead_id`` that keeps the highest ``version`` (a lead's later, more
    annotated version supersedes its earlier one; a stale write never clobbers a newer record).
    ``find_by_email`` exists for lineage: a repeat submission from the same address is linked back
    to its predecessor (see :meth:`~api.services.crm.service.CRMService.capture`).
    """

    def save(self, lead: Lead) -> Lead: ...

    def get(self, lead_id: str) -> Lead | None: ...

    def list_all(self) -> list[Lead]: ...

    def find_by_email(self, email: str) -> list[Lead]: ...

    def update_pipeline_status(self, lead_id: str, pipeline_status: str) -> Lead | None: ...


def _supersedes(incoming: Lead, existing: Lead | None) -> bool:
    """True if ``incoming`` is a write we should keep over ``existing``.

    Keep the incoming write unless it would move a lead *backwards* in version — a strictly lower
    version for the same ``lead_id`` is a stale/replayed write and is ignored, so a captured lead
    is never silently rolled back to a less-synced state. Equal version overwrites (idempotent
    re-save of the same version is harmless and keeps replay simple).
    """
    if existing is None:
        return True
    return incoming.version >= existing.version


class InMemoryLeadStore:
    """Non-durable, in-memory ``LeadStore`` — the dark default. Honest about its own forgetting.

    Backed by a plain dict keyed by ``lead_id``, holding the latest version of each lead. It is
    thread-safe (the app may touch it from worker threads) but it is **not durable**: every lead it
    holds is lost on process exit. That is acceptable only for tests and for a deployment that has
    not yet configured a real store — and it is why a production deployment that means to keep its
    leads must set ``NC_CRM_LEAD_STORE_PATH`` to get :class:`JsonlFileLeadStore`. This store never
    advertises durability it does not have.
    """

    def __init__(self) -> None:
        self._by_id: dict[str, Lead] = {}
        self._lock = threading.Lock()

    def save(self, lead: Lead) -> Lead:
        with self._lock:
            existing = self._by_id.get(lead.lead_id)
            if _supersedes(lead, existing):
                self._by_id[lead.lead_id] = lead
                return lead
            # A stale lower-version write: keep the newer record we already hold, return it so the
            # caller sees the authoritative state rather than its own rejected write.
            return existing  # type: ignore[return-value]

    def get(self, lead_id: str) -> Lead | None:
        with self._lock:
            return self._by_id.get(lead_id)

    def list_all(self) -> list[Lead]:
        with self._lock:
            leads = list(self._by_id.values())
        # Newest first — the sales view wants the freshest submissions on top.
        return sorted(leads, key=lambda lead: lead.created_at, reverse=True)

    def find_by_email(self, email: str) -> list[Lead]:
        target = normalize_email(email)
        with self._lock:
            matches = [lead for lead in self._by_id.values() if lead.email == target]
        return sorted(matches, key=lambda lead: lead.created_at)

    def update_pipeline_status(self, lead_id: str, pipeline_status: str) -> Lead | None:
        """Atomically move one lead through the sales pipeline."""
        with self._lock:
            lead = self._by_id.get(lead_id)
            if lead is None:
                return None
            updated = lead.with_pipeline_status(pipeline_status)
            if updated is lead:
                return lead
            self._by_id[lead_id] = updated
            return updated


class JsonlFileLeadStore:
    """Durable, append-only JSON-lines ``LeadStore`` — single-host real persistence.

    Each :meth:`save` appends one line (``Lead.to_dict()`` as JSON) and flushes+fsyncs it to disk,
    so a lead survives process restart: :meth:`__init__` replays the whole file and rebuilds the
    in-memory index, latest version per ``lead_id`` winning. The append-only log *is* the lineage —
    capture (v1) and each sync annotation (v2…) are distinct lines, recoverable after the fact.

    Honest scope: this is durability on **one host's one disk**. It survives the process dying and
    restarting; it does **not** survive that disk being lost, and it is not a replicated store two
    app instances can safely share. (On an ephemeral host — e.g. Render free-tier ``/tmp`` — the
    file is wiped on redeploy; that is a property of the host, not a durability this store can
    promise away.) Swapping in a real database is a backend change behind the unchanged
    :class:`LeadStore` seam — the service above never knows the difference.
    """

    def __init__(self, path: str | os.PathLike[str]) -> None:
        self._path = Path(path)
        self._lock = threading.Lock()
        self._by_id: dict[str, Lead] = {}
        self._load()

    def _load(self) -> None:
        """Replay the append-only file into the index. Latest version per lead_id wins.

        A missing file is the empty store (a deployment's first boot). A malformed line is skipped
        rather than crashing the whole replay — one corrupt append must not make every prior lead
        unreadable; losing a record loudly-by-omission beats losing all of them by raising.
        """
        if not self._path.exists():
            return
        with self._path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    lead = Lead.from_dict(data)
                except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                    # Skip an unreadable line; the rest of the log is still authoritative.
                    continue
                existing = self._by_id.get(lead.lead_id)
                if _supersedes(lead, existing):
                    self._by_id[lead.lead_id] = lead

    def save(self, lead: Lead) -> Lead:
        with self._lock:
            existing = self._by_id.get(lead.lead_id)
            if not _supersedes(lead, existing):
                # Stale lower-version write: do not append it (the log must not record a rollback)
                # and return the newer record we already hold.
                return existing  # type: ignore[return-value]
            self._append(lead)
            self._by_id[lead.lead_id] = lead
            return lead

    def _append(self, lead: Lead) -> None:
        """Append one lead version as a JSON line, flushed + fsync'd so it survives a restart.

        The parent directory is created on demand so a configured-but-not-yet-existing path
        (e.g. ``./var/crm/leads.jsonl`` on first boot) just works. fsync is what makes the
        durability claim honest rather than buffered-and-hopeful.
        """
        self._path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(lead.to_dict(), ensure_ascii=False, sort_keys=True)
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    def get(self, lead_id: str) -> Lead | None:
        with self._lock:
            return self._by_id.get(lead_id)

    def list_all(self) -> list[Lead]:
        with self._lock:
            leads = list(self._by_id.values())
        return sorted(leads, key=lambda lead: lead.created_at, reverse=True)

    def find_by_email(self, email: str) -> list[Lead]:
        target = normalize_email(email)
        with self._lock:
            matches = [lead for lead in self._by_id.values() if lead.email == target]
        return sorted(matches, key=lambda lead: lead.created_at)

    def update_pipeline_status(self, lead_id: str, pipeline_status: str) -> Lead | None:
        """Atomically move one lead through the sales pipeline and append the new version."""
        with self._lock:
            lead = self._by_id.get(lead_id)
            if lead is None:
                return None
            updated = lead.with_pipeline_status(pipeline_status)
            if updated is lead:
                return lead
            self._append(updated)
            self._by_id[lead_id] = updated
            return updated
