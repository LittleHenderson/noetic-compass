"""Shared StateStore-backed CRM lead persistence and JSONL cutover."""

from __future__ import annotations

from datetime import datetime
from typing import Mapping

from api.services.crm.models import (
    CRM_SCHEMA_VERSION,
    LEGACY_CRM_SCHEMA_VERSION,
    VALID_PIPELINE_STATUSES,
    Lead,
    CRMSyncResult,
    normalize_email,
)
from api.services.production.state_substrate import StateStore
from api.services.revisioned_contact_store import (
    RevisionedContactStateStore,
    RevisionedContactStoreError,
    canonical_json,
    migrate_jsonl_once,
    read_strict_jsonl,
)


CRM_LEAD_JSONL_MIGRATION_ID = "crm_leads_jsonl_v1"

_SYNC_STATUSES = frozenset({"captured", "sync_pending", "synced", "sync_failed"})
_LEGACY_FIELDS = frozenset(
    {
        "lead_id",
        "email",
        "created_at",
        "updated_at",
        "version",
        "source",
        "trace_id",
        "parent_ids",
        "name",
        "organization",
        "message",
        "interest",
        "metadata",
        "sync_status",
        "pipeline_status",
        "external_id",
        "schema_version",
    }
)
_CURRENT_FIELDS = frozenset(Lead.__dataclass_fields__)
_IMMUTABLE_FIELDS = (
    "lead_id",
    "email",
    "created_at",
    "source",
    "trace_id",
    "parent_ids",
    "name",
    "organization",
    "message",
    "interest",
    "metadata",
    "consent_to_contact",
    "privacy_notice_url",
    "privacy_notice_version",
    "privacy_notice_content_sha256",
    "privacy_notice_publication_status",
    "consent_recorded_at_utc",
    "consent_schema_version",
    "schema_version",
)


def _parse_timestamp(raw: str, *, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RevisionedContactStoreError(
            f"CRM JSONL {field} is not a timestamp"
        ) from exc
    if parsed.tzinfo is None:
        raise RevisionedContactStoreError(
            f"CRM JSONL {field} has no timezone"
        )
    return parsed


def _legacy_projection(lead: Lead) -> dict[str, object]:
    payload = lead.to_dict()
    return {field: payload[field] for field in _LEGACY_FIELDS}


def _parse_strict_lead(payload: Mapping[str, object], line_number: int) -> Lead:
    schema = payload.get("schema_version")
    expected_fields = (
        _LEGACY_FIELDS if schema == LEGACY_CRM_SCHEMA_VERSION else _CURRENT_FIELDS
    )
    if schema not in {LEGACY_CRM_SCHEMA_VERSION, CRM_SCHEMA_VERSION}:
        raise RevisionedContactStoreError(
            f"CRM JSONL line {line_number} has an unsupported schema"
        )
    if set(payload) != expected_fields:
        raise RevisionedContactStoreError(
            f"CRM JSONL line {line_number} fields do not match {schema}"
        )
    if type(payload.get("version")) is not int or int(payload["version"]) < 1:
        raise RevisionedContactStoreError(
            f"CRM JSONL line {line_number} version is not a positive strict integer"
        )
    try:
        lead = Lead.from_dict(payload)
    except (KeyError, TypeError, ValueError) as exc:
        raise RevisionedContactStoreError(
            f"CRM JSONL line {line_number} cannot be decoded"
        ) from exc
    projection = (
        _legacy_projection(lead)
        if schema == LEGACY_CRM_SCHEMA_VERSION
        else lead.to_dict()
    )
    if canonical_json(projection) != canonical_json(dict(payload)):
        raise RevisionedContactStoreError(
            f"CRM JSONL line {line_number} is not canonically encoded"
        )
    if lead.email != normalize_email(lead.email):
        raise RevisionedContactStoreError(
            f"CRM JSONL line {line_number} email is not normalized"
        )
    if lead.sync_status not in _SYNC_STATUSES:
        raise RevisionedContactStoreError(
            f"CRM JSONL line {line_number} sync status is invalid"
        )
    if lead.pipeline_status not in VALID_PIPELINE_STATUSES:
        raise RevisionedContactStoreError(
            f"CRM JSONL line {line_number} pipeline status is invalid"
        )
    if lead.sync_status == "synced" and not lead.external_id:
        raise RevisionedContactStoreError(
            f"CRM JSONL line {line_number} claims synced without an external id"
        )
    created = _parse_timestamp(lead.created_at, field="created_at")
    updated = _parse_timestamp(lead.updated_at, field="updated_at")
    if updated < created:
        raise RevisionedContactStoreError(
            f"CRM JSONL line {line_number} updated_at precedes created_at"
        )
    return lead


def _validate_lead_transition(current: Lead | None, candidate: Lead) -> None:
    if current is None:
        if candidate.version != 1:
            raise RevisionedContactStoreError(
                "CRM lead history must begin with domain revision 1"
            )
        return
    if candidate.version != current.version + 1:
        raise RevisionedContactStoreError(
            "CRM lead revisions must increase exactly once per transition"
        )
    if any(
        getattr(current, field) != getattr(candidate, field)
        for field in _IMMUTABLE_FIELDS
    ):
        raise RevisionedContactStoreError(
            "CRM lead revision changed immutable capture or consent fields"
        )
    if _parse_timestamp(candidate.updated_at, field="updated_at") < _parse_timestamp(
        current.updated_at, field="updated_at"
    ):
        raise RevisionedContactStoreError(
            "CRM lead revision moved updated_at backwards"
        )


class StateStoreLeadStore:
    """CRM ``LeadStore`` backed by the lifespan-owned shared StateStore."""

    def __init__(self, store: StateStore) -> None:
        self._records = RevisionedContactStateStore[
            Lead
        ](
            store,
            domain="crm_lead",
            encode=Lead.to_dict,
            decode=Lead.from_dict,
            item_id=lambda lead: lead.lead_id,
            item_version=lambda lead: lead.version,
            sort_key=lambda lead: lead.created_at,
            transition_validator=_validate_lead_transition,
        )

    @property
    def state_store(self) -> StateStore:
        return self._records.state_store

    def save(self, lead: Lead) -> Lead:
        return self._records.save(lead)

    def get(self, lead_id: str) -> Lead | None:
        return self._records.get(lead_id)

    def list_all(self) -> list[Lead]:
        return self._records.list_all()

    def find_by_email(self, email: str) -> list[Lead]:
        target = normalize_email(email)
        return sorted(
            [lead for lead in self.list_all() if lead.email == target],
            key=lambda lead: lead.created_at,
        )

    def update_pipeline_status(
        self, lead_id: str, pipeline_status: str
    ) -> Lead | None:
        return self._records.mutate(
            lead_id,
            lambda lead: lead.with_pipeline_status(pipeline_status),
        )

    def record_sync_result(
        self, lead_id: str, result: CRMSyncResult
    ) -> Lead | None:
        return self._records.mutate(
            lead_id,
            lambda lead: lead.with_sync_result(result),
        )

    def list_revisions(self, lead_id: str) -> list[Lead]:
        """Expose immutable domain history for migration/readback verification."""

        return self._records.list_revisions(lead_id)


def migrate_jsonl_leads_once(
    path: str, destination: StateStoreLeadStore
) -> dict[str, object]:
    source = read_strict_jsonl(path, parser=_parse_strict_lead)
    heads: dict[str, Lead] = {}
    for lead in source.items:
        current = heads.get(lead.lead_id)
        if current is None:
            if lead.version != 1:
                raise RevisionedContactStoreError(
                    "CRM JSONL history must begin with domain revision 1"
                )
        elif lead.version == current.version:
            if canonical_json(lead.to_dict()) != canonical_json(current.to_dict()):
                raise RevisionedContactStoreError(
                    "CRM JSONL duplicate revision has different content"
                )
            continue
        elif lead.version != current.version + 1:
            raise RevisionedContactStoreError(
                "CRM JSONL domain revisions must be contiguous"
            )
        _validate_lead_transition(current, lead)
        heads[lead.lead_id] = lead
    return migrate_jsonl_once(
        source,
        destination._records,
        migration_id=CRM_LEAD_JSONL_MIGRATION_ID,
    )
