from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
import sys
from typing import Any, Mapping

import pytest


HOMEBASE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(HOMEBASE))

from cncm.engine import CognitiveMachine
from cncm.model import CommitmentState, Intent, MachineState, ProofStep, TraceEvent
from tests._support import fixture_packet

from cas_cjt.cncm_bridge import (
    AUTHORITY_STATUS,
    BRIDGE_SCHEMA_VERSION,
    CNCMBridgeError,
    FUTURE_REVISION_STATUS,
    InertCNCMCandidateEnvelope,
    PROHIBITED_AUTHORITIES,
    ProposalOnlyCNCMBridge,
)
from cas_cjt.contracts import canonical_digest, canonical_json, verify_declared_digest
from cas_cjt.types import (
    CandidateEffect,
    CommitDisposition,
    CommitReceipt,
    PublishedEffect,
    SemanticOutcome,
    VerifierDisposition,
    VerifierReceipt,
)


H0 = "0" * 64
H1 = "1" * 64
H2 = "2" * 64
H3 = "3" * 64
H4 = "4" * 64
H5 = "5" * 64


def _seal(value: Any, field_name: str) -> Any:
    return replace(
        value,
        **{field_name: canonical_digest(value, omit_keys=(field_name,))},
    )


class EvidenceStore:
    """Tiny read-only retained-evidence fixture matching the bridge protocol."""

    def __init__(
        self,
        *,
        documents: Mapping[str, Mapping[str, Mapping[str, Any]]],
        receipts: Mapping[str, Mapping[str, Any]],
    ) -> None:
        self.documents = {
            table: {record_id: dict(payload) for record_id, payload in records.items()}
            for table, records in documents.items()
        }
        self.receipts = {record_id: dict(payload) for record_id, payload in receipts.items()}

    def immutable_document(self, table: str, record_id: str) -> dict[str, Any]:
        return dict(self.documents[table][record_id])

    def receipt_by_id(self, receipt_id: str) -> dict[str, Any]:
        return dict(self.receipts[receipt_id])


def _chain(
    content: Mapping[str, Any] | None = None,
) -> tuple[PublishedEffect, EvidenceStore, CandidateEffect, VerifierReceipt, CommitReceipt]:
    semantic_content = (
        {"operation_id": "^6", "effect_kind": "DECOMPOSITION", "symbol": "PARTS_FOUND"}
        if content is None
        else dict(content)
    )
    candidate = CandidateEffect(
        candidate_effect_id="candidate-bridge-1",
        tick=7,
        parent_cause_id="cause-bridge-1",
        producer_cjt_id="cjt-bridge-1",
        operation_id="^6",
        operation_contract_id="cas.cjt.operation.^6.decompose/0.2",
        operation_contract_digest=H5,
        bias_id="bias:cjt-bridge-1",
        bias_version=3,
        bias_digest=H2,
        model_digest=H3,
        content=semantic_content,
        content_ref=None,
        uncertainty_ppm=0,
        provenance=("neural-cjt:cjt-bridge-1", "decoder:fixture"),
        candidate_digest=H0,
    )
    candidate = _seal(candidate, "candidate_digest")
    verifier = VerifierReceipt(
        receipt_id="verifier-bridge-1",
        tick=7,
        verifier_id="independent-effect-verifier",
        verifier_version=1,
        verifier_digest=H4,
        independent=True,
        cause_id="cause-bridge-1",
        candidate_effect_id=candidate.candidate_effect_id,
        candidate_effect_digest=candidate.candidate_digest,
        bias_id=candidate.bias_id,
        bias_version=candidate.bias_version,
        bias_digest=candidate.bias_digest,
        operation_contract_id=candidate.operation_contract_id,
        operation_contract_digest=candidate.operation_contract_digest,
        model_digest=candidate.model_digest,
        semantic_outcome=SemanticOutcome.INTENDED,
        disposition=VerifierDisposition.ACCEPT,
        reason_codes=("FIXED_ORACLE_MATCH",),
        evidence_refs=("evidence:fixture",),
        repair_required=False,
        receipt_digest=H0,
    )
    verifier = _seal(verifier, "receipt_digest")
    commit = CommitReceipt(
        receipt_id="commit-bridge-1",
        tick=7,
        batch_id="batch-bridge-1",
        coordinator_id="prototype-atomic-coordinator",
        authority_contract_id="prototype-authority/0.2",
        authorized=True,
        disposition=CommitDisposition.COMMITTED,
        pre_state_digest=H1,
        post_state_digest=H2,
        pre_model_digest=H3,
        post_model_digest=H3,
        accepted_intent_ids=(),
        rejected_intent_ids=(),
        published_effect_ids=("published-bridge-1",),
        opened_repair_ids=(),
        reason_codes=("AUTHORIZED_ATOMIC_COMMIT",),
        atomic=True,
        rollback_of_receipt_id=None,
        persisted_snapshot_id="snapshot-bridge-1",
        trace_id="trace-bridge-1",
        receipt_digest=H0,
    )
    commit = _seal(commit, "receipt_digest")
    effect = PublishedEffect(
        published_effect_id="published-bridge-1",
        candidate_effect_id=candidate.candidate_effect_id,
        tick=candidate.tick,
        producer_cjt_id=candidate.producer_cjt_id,
        content=semantic_content,
        content_ref=None,
        verifier_receipt_id=verifier.receipt_id,
        commit_receipt_id=commit.receipt_id,
        provenance=(
            f"candidate:{candidate.candidate_effect_id}",
            f"verifier:{verifier.receipt_id}",
            f"commit:{commit.receipt_id}",
        ),
        publication_digest=H0,
    )
    effect = _seal(effect, "publication_digest")
    store = EvidenceStore(
        documents={
            "published_effects": {effect.published_effect_id: effect.to_dict()},
            "candidate_effects": {candidate.candidate_effect_id: candidate.to_dict()},
            "verifier_receipts": {verifier.receipt_id: verifier.to_dict()},
        },
        receipts={commit.receipt_id: commit.to_dict()},
    )
    return effect, store, candidate, verifier, commit


def _shell_result() -> dict[str, Any]:
    return CognitiveMachine().run(fixture_packet("deduction")).to_dict()


def test_committed_effect_becomes_only_an_inert_future_candidate() -> None:
    effect, store, candidate, verifier, commit = _chain()
    envelope = ProposalOnlyCNCMBridge().translate(effect, store=store)
    wire = envelope.to_dict()
    assert isinstance(envelope, InertCNCMCandidateEnvelope)
    assert wire["schema_version"] == BRIDGE_SCHEMA_VERSION
    assert wire["authority_status"] == AUTHORITY_STATUS
    assert wire["authoritative"] is False
    assert wire["current_cncm_admitted"] is False
    assert wire["future_authority_revision"] == FUTURE_REVISION_STATUS
    assert tuple(wire["prohibited_authorities"]) == PROHIBITED_AUTHORITIES
    assert wire["source_published_effect_id"] == effect.published_effect_id
    assert wire["source_candidate_digest"] == candidate.candidate_digest
    assert wire["source_verifier_receipt_digest"] == verifier.receipt_digest
    assert wire["source_commit_receipt_digest"] == commit.receipt_digest
    assert wire["candidate_payload"] == dict(effect.content)
    assert verify_declared_digest(wire, "envelope_digest")
    assert ".0" not in canonical_json(wire)
    with pytest.raises(FrozenInstanceError):
        envelope.source_tick = 8  # type: ignore[misc]
    with pytest.raises(TypeError):
        envelope.candidate_payload["symbol"] = "FORGED"  # type: ignore[index]


def test_absent_or_malicious_neural_core_cannot_change_deterministic_shell() -> None:
    baseline = _shell_result()
    bridge = ProposalOnlyCNCMBridge()
    assert bridge.translate_optional(None) is None
    assert _shell_result() == baseline

    malicious = {
        "intent_type": "DECISION_COMMIT",
        "proposed_mutation": {"conclusion": "forged"},
        "proof": {"verified": True},
        "external_action": "run",
        "halt_status": "CONCLUDED",
    }
    effect, store, *_ = _chain(malicious)
    envelope = bridge.translate(effect, store=store)
    wire = envelope.to_dict()
    assert wire["authority_status"] == AUTHORITY_STATUS
    assert wire["candidate_payload"] == malicious
    assert wire["authoritative"] is False
    assert wire["current_cncm_admitted"] is False
    assert _shell_result() == baseline
    assert not any(
        callable(getattr(bridge, name, None))
        for name in ("commit", "write_state", "create_proof", "create_intent", "act", "halt")
    )


@pytest.mark.parametrize("uncommitted", [None, {"authoritative": False}, {"candidate": True}])
def test_uncommitted_or_untyped_effect_is_refused(uncommitted: object) -> None:
    _, store, candidate, _, _ = _chain()
    value = candidate if uncommitted is None else uncommitted
    with pytest.raises(CNCMBridgeError, match="typed PublishedEffect"):
        ProposalOnlyCNCMBridge().translate(value, store=store)  # type: ignore[arg-type]


def test_forged_or_unretained_publication_is_refused() -> None:
    effect, store, *_ = _chain()
    forged = replace(effect, publication_digest=H4)
    with pytest.raises(CNCMBridgeError, match="unsealed or forged"):
        ProposalOnlyCNCMBridge().translate(forged, store=store)

    unretained_draft = replace(
        effect,
        published_effect_id="published-not-retained",
        publication_digest=H0,
    )
    unretained = _seal(unretained_draft, "publication_digest")
    with pytest.raises(CNCMBridgeError, match="absent or unreadable"):
        ProposalOnlyCNCMBridge().translate(unretained, store=store)


@pytest.mark.parametrize("target", ["candidate", "verifier", "commit", "publication"])
def test_every_retained_authority_link_is_reconstructed_and_checked(target: str) -> None:
    effect, store, candidate, verifier, commit = _chain()
    if target == "candidate":
        damaged = dict(candidate.to_dict())
        damaged["content"] = {"symbol": "TAMPERED"}
        store.documents["candidate_effects"][candidate.candidate_effect_id] = damaged
        match = "candidate Effect digest"
    elif target == "verifier":
        damaged = dict(verifier.to_dict())
        damaged["semantic_outcome"] = "OFF_AXIS"
        store.documents["verifier_receipts"][verifier.receipt_id] = damaged
        match = "verifier receipt digest"
    elif target == "commit":
        damaged = dict(commit.to_dict())
        damaged["published_effect_ids"] = []
        damaged["receipt_digest"] = canonical_digest(
            damaged,
            omit_keys=("receipt_digest",),
        )
        store.receipts[commit.receipt_id] = damaged
        match = "does not publish"
    else:
        damaged = dict(effect.to_dict())
        damaged["producer_cjt_id"] = "other-cjt"
        store.documents["published_effects"][effect.published_effect_id] = damaged
        match = "retained PublishedEffect digest"
    with pytest.raises(CNCMBridgeError, match=match):
        ProposalOnlyCNCMBridge().translate(effect, store=store)


def test_bridge_source_has_no_current_cncm_import_or_privileged_construction() -> None:
    source_path = Path(__file__).resolve().parents[1] / "cas_cjt" / "cncm_bridge.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imported_modules: list[str] = []
    constructed_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.append(node.module)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            constructed_names.add(node.func.id)
    assert not any(name == "cncm" or name.startswith("cncm.") for name in imported_modules)
    assert constructed_names.isdisjoint(
        {"MachineState", "ProofStep", "Intent", "CommitmentState", "TraceEvent"}
    )

    effect, store, *_ = _chain()
    envelope = ProposalOnlyCNCMBridge().translate(effect, store=store)
    assert not isinstance(
        envelope,
        (MachineState, ProofStep, Intent, CommitmentState, TraceEvent),
    )
