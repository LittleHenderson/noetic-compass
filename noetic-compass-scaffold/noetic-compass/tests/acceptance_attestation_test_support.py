"""Real in-memory human-attestation fixtures for acceptance-authority tests."""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from datetime import datetime
import hashlib
from typing import Any

from api.services.human_attestations import (
    ATTESTATION_ACCOUNT_ROLE,
    HumanAttestation,
    HumanAttestationStore,
    canonical_evidence_binding_sha256,
)
from api.services.production.state_substrate import StateStore


_ROLE_ACCOUNT_IDS = {
    role: f"acct-{index:032x}"
    for index, role in enumerate(sorted(ATTESTATION_ACCOUNT_ROLE), start=1)
}
_PSEUDONYM_KEY_ID = "hatk_89abcdef0123456789abcdef01234567"
_PSEUDONYM_KEYRING = {
    _PSEUDONYM_KEY_ID: hashlib.sha256(
        b"cas-acceptance-attestation-test-key-v2"
    ).digest()
}


def _parse_utc(value: object) -> datetime:
    if not isinstance(value, str):
        raise AssertionError("test evidence timestamp must be a string")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _reference(record: HumanAttestation, role: str) -> dict[str, str]:
    return {
        "role": role,
        "attestation_artifact_uri": record.uri,
        "attestation_sha256": record.sha256,
        "attested_at_utc": str(record.payload["attested_at_utc"]),
    }


def human_attestation_store(
    state_store: StateStore,
    *,
    primary_tenant_id: str = "primary",
) -> HumanAttestationStore:
    """Build the production store with a stable test-only v2 keyring."""

    return HumanAttestationStore(
        state_store,
        primary_tenant_id=primary_tenant_id,
        pseudonym_keyring=_PSEUDONYM_KEYRING,
        active_pseudonym_key_id=_PSEUDONYM_KEY_ID,
    )


def materialize_human_attestations(
    state_store: StateStore,
    evidence: MutableMapping[str, Any],
    *,
    primary_tenant_id: str = "primary",
    attested_at_overrides: Mapping[tuple[str, str], datetime] | None = None,
) -> HumanAttestationStore:
    """Replace placeholder references with real content-addressed records.

    This helper deliberately uses the production ``HumanAttestationStore`` and
    distinct synthetic test account identities. It is not an authority bypass:
    publish/load still dereference the exact records and their revocation rows.
    These in-memory fixtures do not prove natural identity, distinct people, or
    professional qualifications and must never be used as production evidence.
    """

    gate = str(evidence.get("gate") or "")
    if gate not in {
        "legal_publication_approval",
        "claim_honesty",
        "incident_tabletop",
        "release_decision",
    }:
        raise AssertionError(f"{gate!r} is not a human-attested gate")
    master_head_sha = str(evidence.get("master_head_sha") or "")
    deploy_id = str(evidence.get("deploy_id") or "")
    binding = canonical_evidence_binding_sha256(gate, evidence)
    attestations = human_attestation_store(
        state_store, primary_tenant_id=primary_tenant_id
    )
    overrides = attested_at_overrides or {}

    def create(
        *,
        purpose: str,
        role: str,
        at: datetime,
        supports: list[Mapping[str, Any]] | None = None,
    ) -> HumanAttestation:
        attested_at = overrides.get((purpose, role), at)
        return attestations.create(
            actor_tenant_id=primary_tenant_id,
            actor_account_id=_ROLE_ACCOUNT_IDS[role],
            actor_account_role=ATTESTATION_ACCOUNT_ROLE[role],
            purpose=purpose,
            gate=gate,
            attestation_role=role,
            master_head_sha=master_head_sha,
            deploy_id=deploy_id,
            evidence_binding_sha256=binding,
            supporting_attestations=supports,
            now=attested_at,
        )

    if gate in {"legal_publication_approval", "claim_honesty"}:
        approvals = evidence.get("approvals")
        if not isinstance(approvals, list):
            raise AssertionError("test approval evidence must be a list")
        purpose = (
            "legal_approval"
            if gate == "legal_publication_approval"
            else "claim_approval"
        )
        for approval in approvals:
            if not isinstance(approval, MutableMapping):
                raise AssertionError("test approval must be mutable")
            role = str(approval.get("role") or "")
            record = create(
                purpose=purpose,
                role=role,
                at=_parse_utc(approval.get("approved_at_utc")),
            )
            approval["approval_artifact_uri"] = record.uri
            approval["approval_sha256"] = record.sha256
            approval["approved_at_utc"] = record.payload["attested_at_utc"]
        return attestations

    if gate == "incident_tabletop":
        observed = _parse_utc(evidence.get("observed_at_utc"))
        closure = {
            role: create(purpose="incident_closure", role=role, at=observed)
            for role in ("incident_commander", "operations", "security")
        }
        postmortem = create(
            purpose="incident_postmortem",
            role="incident_commander",
            at=observed,
            supports=[
                _reference(record, role) for role, record in closure.items()
            ],
        )
        participants = {
            role: create(purpose="tabletop_completion", role=role, at=observed)
            for role in (
                "incident_commander",
                "legal",
                "operations",
                "security",
                "support",
            )
        }
        tabletop_record = create(
            purpose="tabletop_evidence",
            role="incident_commander",
            at=observed,
            supports=[
                _reference(record, role) for role, record in participants.items()
            ],
        )
        incident = evidence.get("incident")
        tabletop = evidence.get("tabletop")
        if not isinstance(incident, MutableMapping) or not isinstance(
            tabletop, MutableMapping
        ):
            raise AssertionError("test incident/tabletop evidence must be mutable")
        incident["postmortem_uri"] = postmortem.uri
        incident["postmortem_sha256"] = postmortem.sha256
        tabletop["evidence_uri"] = tabletop_record.uri
        tabletop["evidence_sha256"] = tabletop_record.sha256
        return attestations

    approved = _parse_utc(evidence.get("approved_at_utc"))
    roles = evidence.get("approver_roles")
    if not isinstance(roles, list):
        raise AssertionError("test release approver_roles must be a list")
    approvals = {
        str(role): create(
            purpose="release_approval", role=str(role), at=approved
        )
        for role in roles
    }
    decision = create(
        purpose="release_decision_record",
        role="product_owner",
        at=approved,
        supports=[_reference(record, role) for role, record in approvals.items()],
    )
    evidence["decision_record_uri"] = decision.uri
    evidence["decision_record_sha256"] = decision.sha256
    return attestations


__all__ = ["human_attestation_store", "materialize_human_attestations"]
