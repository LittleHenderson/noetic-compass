#!/usr/bin/env python3
"""Finalize support/CRM evidence from durable resolved-ticket and CRM sources.

This Render-shell command never creates or advances a ticket lifecycle.  It
requires an already resolved StateStore ticket, the independently collected
Airtable source receipt/OPEN fragment, and owner-only private selectors.  Raw
ticket/lead IDs remain only in the final private selector used by the publisher.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from datetime import UTC, datetime
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.acceptance_authority_contract import PRODUCTION_API_ORIGIN
from api.services.customer_production_acceptance_authority import (
    AcceptanceAuthorityInvalid,
    canonicalize_acceptance_evidence,
)
from api.services.customer_production_pseudonyms import (
    CRM_LEAD_DOMAIN,
    SUPPORT_TICKET_DOMAIN,
    CustomerProductionPseudonymizer,
    parse_customer_production_pseudonym_keyring,
    validate_public_pseudonym_metadata,
)
from api.services.production.state_substrate import StateStore
from api.services.revisioned_contact_store import (
    CONTACT_MIGRATION_KIND,
    CONTACT_MIGRATION_SCHEMA_VERSION,
    CONTACT_STATE_TENANT,
)
from api.services.support_crm_acceptance_binding import (
    PRIVATE_SELECTOR_SCHEMA_VERSION,
)
from api.services.support_public_intake_receipts import (
    HTTP_STATUS_CREATED,
    SupportPublicIntakeReceiptError,
    SupportPublicIntakeReceiptStore,
)
from api.services.support_ticket_state_store import (
    SUPPORT_TICKET_JSONL_MIGRATION_ID,
    StateStoreSupportTicketStore,
)
from api.services.support_tickets import SUPPORT_TICKET_SCHEMA_VERSION, SupportTicket
from scripts.collect_airtable_crm_acceptance_source import (
    FRAGMENT_SCHEMA_VERSION,
    PRIVATE_LEAD_SELECTOR_SCHEMA_VERSION,
    SOURCE_SCHEMA_VERSION,
    _validate_output_pair,
)


EVIDENCE_SCHEMA_VERSION = "cas_harness_customer_production_gate_evidence.v3"
SAFE_ARTIFACT_SCHEMA_VERSION = "cas_harness_support_crm_finalization_receipt.v1"
PRIVATE_TICKET_SELECTOR_SCHEMA_VERSION = (
    "cas_harness_support_ticket_acceptance_selector.v1"
)
REPOSITORY = "LittleHenderson/noetic-compass"
LANDING_ORIGIN = "https://cascompass.ai"
PRODUCTION_SERVICE_ID = "i-0bd0a082507a51ae3"
AUTHORITY_URI = f"{PRODUCTION_API_ORIGIN}/internal/acceptance/support-crm"
_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_DEPLOY_RE = re.compile(r"^dep-[A-Za-z0-9]+$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_MAX_INPUT_BYTES = 2_000_000


class SupportCRMFinalizationFailure(RuntimeError):
    def __init__(self, gate: str, detail: str) -> None:
        self.gate = gate
        super().__init__(f"{gate}: {detail}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise SupportCRMFinalizationFailure("json", "input has a duplicate key")
        result[key] = value
    return result


def _read_json(path: Path, *, private: bool = False) -> Mapping[str, Any]:
    try:
        if private and os.name == "posix" and path.stat().st_mode & 0o077:
            raise SupportCRMFinalizationFailure(
                "private-selector", "private input must be owner-only"
            )
        raw = path.read_bytes()
    except SupportCRMFinalizationFailure:
        raise
    except OSError as exc:
        raise SupportCRMFinalizationFailure("input", "input is unreadable") from exc
    if not raw or len(raw) > _MAX_INPUT_BYTES:
        raise SupportCRMFinalizationFailure("input", "input size is invalid")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
    except SupportCRMFinalizationFailure:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SupportCRMFinalizationFailure("input", "input is not strict JSON") from exc
    if not isinstance(value, Mapping):
        raise SupportCRMFinalizationFailure("input", "input root is not an object")
    return value


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError) as exc:
        raise SupportCRMFinalizationFailure("json", "output is not strict JSON") from exc


def _parse_timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise SupportCRMFinalizationFailure("timestamp", f"{field} is absent")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SupportCRMFinalizationFailure("timestamp", f"{field} is invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SupportCRMFinalizationFailure("timestamp", f"{field} has no timezone")
    return parsed.astimezone(UTC)


def _stamp(value: datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _validate_lead_selector(value: Mapping[str, Any]) -> str:
    if (
        set(value) != {"schema_version", "gate", "crm_lead_id"}
        or value.get("schema_version") != PRIVATE_LEAD_SELECTOR_SCHEMA_VERSION
        or value.get("gate") != "support_crm"
        or not isinstance(value.get("crm_lead_id"), str)
        or not value.get("crm_lead_id")
    ):
        raise SupportCRMFinalizationFailure(
            "private-selector", "private CRM lead selector is invalid"
        )
    return str(value["crm_lead_id"])


def _validate_ticket_selector(value: Mapping[str, Any]) -> str:
    if (
        set(value) != {"schema_version", "gate", "support_ticket_id"}
        or value.get("schema_version") != PRIVATE_TICKET_SELECTOR_SCHEMA_VERSION
        or value.get("gate") != "support_crm"
        or not isinstance(value.get("support_ticket_id"), str)
        or not value.get("support_ticket_id")
    ):
        raise SupportCRMFinalizationFailure(
            "private-selector", "private support-ticket selector is invalid"
        )
    return str(value["support_ticket_id"])


def _assert_support_marker(store: StateStore) -> None:
    marker = store.get(
        CONTACT_STATE_TENANT,
        CONTACT_MIGRATION_KIND,
        SUPPORT_TICKET_JSONL_MIGRATION_ID,
    )
    payload = None if marker is None else marker.payload
    if (
        marker is None
        or marker.version != 1
        or marker.tenant_id != CONTACT_STATE_TENANT
        or marker.kind != CONTACT_MIGRATION_KIND
        or marker.record_id != SUPPORT_TICKET_JSONL_MIGRATION_ID
        or marker.source != "contact_jsonl_migration"
        or marker.trace_id is not None
        or not isinstance(payload, Mapping)
        or payload.get("schema_version") != CONTACT_MIGRATION_SCHEMA_VERSION
        or payload.get("domain") != "support_ticket"
        or type(payload.get("source_present")) is not bool
        or any(
            type(payload.get(field)) is not int or int(payload.get(field, -1)) < 0
            for field in ("line_count", "revision_count", "head_count")
        )
        or any(
            _SHA256_RE.fullmatch(str(payload.get(field) or "")) is None
            for field in ("source_sha256", "records_sha256")
        )
    ):
        raise SupportCRMFinalizationFailure(
            "support-ticket", "support migration marker is absent or invalid"
        )


def _resolved_ticket(
    store: StateStore, *, ticket_id: str, sla_seconds: int
) -> SupportTicket:
    _assert_support_marker(store)
    tickets = StateStoreSupportTicketStore(store)
    head = tickets.get(ticket_id)
    if head is None:
        raise SupportCRMFinalizationFailure("support-ticket", "ticket is absent")
    revisions = [item for item in tickets.list_revisions(ticket_id) if item.version == head.version]
    if len(revisions) != 1 or revisions[0].to_dict() != head.to_dict():
        raise SupportCRMFinalizationFailure(
            "support-ticket", "ticket head and immutable revision diverged"
        )
    ticket = revisions[0]
    if (
        ticket.schema_version != SUPPORT_TICKET_SCHEMA_VERSION
        or ticket.status != "resolved"
        or ticket.owner is None
        or ticket.routed_at_utc is None
        or ticket.acknowledged_at_utc is None
        or ticket.resolved_at_utc is None
        or ticket.resolution_summary is None
        or ticket.acknowledged_within(sla_seconds) is not True
    ):
        raise SupportCRMFinalizationFailure(
            "support-ticket", "ticket is not a resolved within-SLA v2 lifecycle"
        )
    created = _parse_timestamp(ticket.created_at_utc, "ticket.created_at_utc")
    routed = _parse_timestamp(ticket.routed_at_utc, "ticket.routed_at_utc")
    acknowledged = _parse_timestamp(
        ticket.acknowledged_at_utc, "ticket.acknowledged_at_utc"
    )
    resolved = _parse_timestamp(ticket.resolved_at_utc, "ticket.resolved_at_utc")
    if not created <= routed <= acknowledged <= resolved:
        raise SupportCRMFinalizationFailure(
            "support-ticket", "ticket lifecycle timestamps are invalid"
        )
    return ticket


def build(
    *,
    source_receipt: Mapping[str, Any],
    fragment: Mapping[str, Any],
    private_lead_selector: Mapping[str, Any],
    private_ticket_selector: Mapping[str, Any],
    store: StateStore,
    pseudonymizer: CustomerProductionPseudonymizer,
    support_ack_sla_seconds: int,
    now: datetime,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if fragment.get("schema_version") != FRAGMENT_SCHEMA_VERSION:
        raise SupportCRMFinalizationFailure("fragment", "fragment schema is invalid")
    if source_receipt.get("schema_version") != SOURCE_SCHEMA_VERSION:
        raise SupportCRMFinalizationFailure("source", "source schema is invalid")
    try:
        _validate_output_pair(source_receipt, fragment)
        key_id = validate_public_pseudonym_metadata(
            source_receipt, available_key_ids=pseudonymizer.key_ids
        )
    except Exception as exc:
        raise SupportCRMFinalizationFailure(
            "source", "CRM source receipt or pseudonym key is invalid"
        ) from exc
    lead_id = _validate_lead_selector(private_lead_selector)
    ticket_id = _validate_ticket_selector(private_ticket_selector)
    try:
        pseudonymizer.assert_subject(
            source_receipt.get("lead_subject"),
            domain=CRM_LEAD_DOMAIN,
            tenant_scope=CONTACT_STATE_TENANT,
            value=lead_id,
            key_id=key_id,
        )
    except ValueError as exc:
        raise SupportCRMFinalizationFailure(
            "private-selector", "private CRM lead selector is cross-wired"
        ) from exc
    ticket = _resolved_ticket(
        store, ticket_id=ticket_id, sla_seconds=support_ack_sla_seconds
    )
    try:
        intake_receipt = SupportPublicIntakeReceiptStore(
            store, pseudonymizer=pseudonymizer
        ).revalidate(ticket_id)
    except SupportPublicIntakeReceiptError as exc:
        raise SupportCRMFinalizationFailure(
            "support-ticket",
            "durable public-intake receipt is absent or invalid",
        ) from exc
    create_status = intake_receipt.payload.get("http_status")
    if create_status != HTTP_STATUS_CREATED:
        raise SupportCRMFinalizationFailure(
            "support-ticket", "public-intake receipt HTTP status is invalid"
        )
    ticket_subject = pseudonymizer.subject(
        domain=SUPPORT_TICKET_DOMAIN,
        tenant_scope=CONTACT_STATE_TENANT,
        value=ticket_id,
        key_id=key_id,
    )
    created = _parse_timestamp(ticket.created_at_utc, "ticket.created_at_utc")
    acknowledged = _parse_timestamp(
        ticket.acknowledged_at_utc, "ticket.acknowledged_at_utc"
    )
    resolved = _parse_timestamp(ticket.resolved_at_utc, "ticket.resolved_at_utc")
    first_response_minutes = math.ceil((acknowledged - created).total_seconds() / 60)
    sla_minutes = support_ack_sla_seconds // 60
    event = min(
        resolved,
        *(
            _parse_timestamp(source_receipt.get(field), f"source.{field}")
            for field in (
                "render_deploy_finished_at_utc",
                "privacy_notice_verified_at_utc",
                "consent_recorded_at_utc",
                "verified_at_utc",
                "observed_at_utc",
            )
        ),
    )
    observed = now.astimezone(UTC).replace(microsecond=0)
    if observed < resolved:
        raise SupportCRMFinalizationFailure("timestamp", "ticket resolves in the future")
    source_sha = hashlib.sha256(_canonical_bytes(source_receipt)).hexdigest()
    metadata = {
        "pseudonymization_scheme": source_receipt["pseudonymization_scheme"],
        "pseudonym_key_id": key_id,
    }
    safe_artifact = {
        "schema_version": SAFE_ARTIFACT_SCHEMA_VERSION,
        "master_head_sha": source_receipt["master_head_sha"],
        "deploy_id": source_receipt["deploy_id"],
        **metadata,
        "ticket_subject": ticket_subject,
        "ticket_record_version": ticket.version,
        "lead_subject": source_receipt["lead_subject"],
        "airtable_record_subject": source_receipt["airtable_record_subject"],
        "crm_source_receipt_sha256": source_sha,
        "resolved_at_utc": _stamp(resolved),
        "observed_at_utc": _stamp(observed),
    }
    evidence = {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "gate": "support_crm",
        "environment": "public-production",
        "repository": REPOSITORY,
        "master_head_sha": source_receipt["master_head_sha"],
        "deploy_id": source_receipt["deploy_id"],
        "event_at_utc": _stamp(event),
        "observed_at_utc": _stamp(observed),
        "artifact_uri": AUTHORITY_URI,
        "artifact_sha256": hashlib.sha256(_canonical_bytes(safe_artifact)).hexdigest(),
        "public_support_url": f"{LANDING_ORIGIN}/contact",
        "api_base_url": PRODUCTION_API_ORIGIN,
        "service_id": PRODUCTION_SERVICE_ID,
        **metadata,
        "support_ticket": {
            "ticket_subject": ticket_subject,
            "ticket_record_version": ticket.version,
            "create_http_status": create_status,
            "persisted": True,
            "routed": True,
            "acknowledged": True,
            "first_response_minutes": first_response_minutes,
            "sla_minutes": sla_minutes,
            "resolution_recorded": True,
            "resolved_at_utc": _stamp(resolved),
        },
        "crm_lead": dict(fragment["crm_lead"]),
        "consent": dict(fragment["consent"]),
        "crm_source_receipt": dict(source_receipt),
    }
    selector = {
        "schema_version": PRIVATE_SELECTOR_SCHEMA_VERSION,
        "gate": "support_crm",
        "support_ticket_id": ticket_id,
        "crm_lead_id": lead_id,
    }
    rendered = json.dumps([evidence, safe_artifact], sort_keys=True, ensure_ascii=True)
    if any(value and value in rendered for value in (ticket_id, lead_id)):
        raise SupportCRMFinalizationFailure(
            "privacy", "public output contains a private source identifier"
        )
    try:
        canonicalize_acceptance_evidence("support_crm", evidence, now=observed)
    except AcceptanceAuthorityInvalid as exc:
        raise SupportCRMFinalizationFailure(
            "authority", "final evidence does not satisfy the authority contract"
        ) from exc
    return evidence, safe_artifact, selector


def _atomic_write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="wb", delete=False, dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    temporary = Path(handle.name)
    try:
        os.chmod(temporary, 0o600)
        with handle:
            handle.write(_canonical_bytes(value) + b"\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-receipt", required=True, type=Path)
    parser.add_argument("--fragment", required=True, type=Path)
    parser.add_argument("--private-lead-selector", required=True, type=Path)
    parser.add_argument("--private-ticket-selector", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--safe-artifact-output", required=True, type=Path)
    parser.add_argument("--private-source-selector-output", required=True, type=Path)
    return parser


def run(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    store = None
    try:
        output_paths = {
            args.output.resolve(),
            args.safe_artifact_output.resolve(),
            args.private_source_selector_output.resolve(),
        }
        if len(output_paths) != 3:
            raise SupportCRMFinalizationFailure("output", "output paths must differ")
        from api.config import Settings
        from api.state_ledger_bootstrap import _build_state_store

        settings = Settings()
        if (
            settings.crm_lead_store_backend.strip().lower() != "state_store"
            or settings.support_ticket_store_backend.strip().lower() != "state_store"
            or not settings.state_ledger_enabled
            or not settings.state_ledger_read_authority
            or not str(settings.database_url or "").lower().startswith(
                ("postgres://", "postgresql://")
            )
        ):
            raise SupportCRMFinalizationFailure(
                "persistence", "finalization requires shared Postgres contact authority"
            )
        pseudonymizer = CustomerProductionPseudonymizer(
            parse_customer_production_pseudonym_keyring(
                settings.customer_production_pseudonym_keyring_json,
                active_key_id=settings.customer_production_pseudonym_active_key_id,
            ),
            active_key_id=settings.customer_production_pseudonym_active_key_id,
        )
        store = _build_state_store(settings)
        evidence, artifact, selector = build(
            source_receipt=_read_json(args.source_receipt),
            fragment=_read_json(args.fragment),
            private_lead_selector=_read_json(
                args.private_lead_selector, private=True
            ),
            private_ticket_selector=_read_json(
                args.private_ticket_selector, private=True
            ),
            store=store,
            pseudonymizer=pseudonymizer,
            support_ack_sla_seconds=settings.support_ack_sla_seconds,
            now=datetime.now(UTC),
        )
        _atomic_write(args.safe_artifact_output, artifact)
        _atomic_write(args.output, evidence)
        _atomic_write(args.private_source_selector_output, selector)
        print(
            json.dumps(
                {
                    "evidence_sha256": hashlib.sha256(
                        _canonical_bytes(evidence)
                    ).hexdigest(),
                    "gate": "support_crm",
                    "status": "present",
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 0
    except SupportCRMFinalizationFailure as exc:
        print(
            json.dumps(
                {"gate": exc.gate, "status": "OPEN", "error": str(exc)},
                sort_keys=True,
                separators=(",", ":"),
            ),
            file=sys.stderr,
        )
        return 2
    except Exception as exc:  # pragma: no cover - final secret-safe boundary
        print(
            json.dumps(
                {
                    "gate": "finalizer",
                    "status": "OPEN",
                    "error_type": type(exc).__name__,
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
            file=sys.stderr,
        )
        return 3
    finally:
        if store is not None:
            try:
                store.close()
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(run())
