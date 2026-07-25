"""Record the owner's approval of the TKS/CAS semantic authority registry.

Roadmap Gate-2 item 3 requires: "Obtain owner approval for a field-level
semantic authority registry before claim-bearing A/B work"
(CAS_HARNESS_033_TO_100_COMPLETION_ROADMAP_20260722.md:198-199). Item 4 (the
six-arm TKS definition experiment) is blocked until that approval exists in a
form a downstream check can read.

WHY THIS IS A SEPARATE ARTIFACT, NOT A PcbaAuthorityReceipt:
``cas_forex.pcba_authority.PcbaAuthorityReceipt`` is the proven receipt pattern
in this repo (4 signed receipts verify True today), but its ``feature`` field is
typed to ``PcbaProductionFeature`` — a CAS Forex production-readiness enum whose
nine members are all trading/board/compiler features. There is no member for a
semantic authority registry, so ``model_validate`` rejects it. Rather than
mislabel the registry as a trading feature to reuse the class, this module
follows the SAME discipline (identical field names, identical hash rule:
sha256 over sorted-key compact JSON excluding ``receipt_hash``, plus per-artifact
sha256) in the harness domain where it belongs.

WHAT THIS RECEIPT IS AND IS NOT:
It records that the owner gave approval in an interactive session on the stated
date, transcribed by the assistant. It is NOT a cryptographic signature by the
owner, and the ``signature_kind`` field says so explicitly so no later reader can
mistake it for one. It approves the registry as the binding semantic authority
for run bindings; it does NOT license any empirical claim, and it does not assert
that the readiness audit's open findings were resolved — those are carried
verbatim in ``open_findings_at_signing`` so the record stays honest.
"""

from __future__ import annotations

from argparse import ArgumentParser
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

REGISTRY_REL = "docs/working/TKS_CAS_SEMANTIC_SOURCE_REGISTRY_CANDIDATE_20260720.json"

# Carried verbatim from GATE2_ITEM3_REGISTRY_SIGNATURE_READINESS.md so the
# receipt itself records what was still open when approval was given. Signing
# over open findings is the owner's prerogative; hiding them would not be.
OPEN_FINDINGS_AT_SIGNING = [
    "The registry lists 12 known_conflicts that are recorded but not individually resolved; "
    "the signature approves the registry as the binding authority, not the resolution of each conflict.",
    "Acquisition and algebra profiles remain marked `unavailable` per roadmap:202-203 and are NOT "
    "approved by this signature.",
    "The readiness audit (GATE2_ITEM3_REGISTRY_SIGNATURE_READINESS.md) was in a final targeted "
    "correction pass at the time of signing; its remaining defects were line-reference level, not "
    "substantive to the registry's content.",
    "This approval unblocks roadmap item 4 (the six-arm TKS definition A/B) ONLY. It licenses no "
    "empirical claim and grants no verdict.",
]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compute_receipt_hash(receipt: dict[str, Any]) -> str:
    """Same rule as PcbaAuthorityReceipt.compute_hash: sorted-key compact JSON, hash excluded."""
    payload = {k: v for k, v in receipt.items() if k != "receipt_hash"}
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def build_receipt(*, repo_root: Path, operator_id: str, signature: str, signed_at: str) -> dict[str, Any]:
    registry = repo_root / REGISTRY_REL
    if not registry.exists():
        raise FileNotFoundError(f"Registry not found at {registry}")
    receipt: dict[str, Any] = {
        "schema_version": "cas_harness_semantic_authority_signature_receipt.v1",
        "evidence_key": "owner_semantic_authority_registry_approved",
        "feature": "tks_cas_semantic_authority_registry",
        "roadmap_item": "Gate 2 item 3 (CAS_HARNESS_033_TO_100_COMPLETION_ROADMAP_20260722.md:198-199)",
        "unblocks": "Gate 2 item 4 — six-arm TKS definition A/B experiment (roadmap:204-206)",
        "approved": True,
        "operator_id": operator_id,
        "signature_kind": (
            "INTERACTIVE_SESSION_OWNER_APPROVAL_TRANSCRIBED_BY_ASSISTANT — this is a recorded "
            "authorization, NOT a cryptographic signature by the owner and NOT a legal signature."
        ),
        "signed_reason": (
            "Owner approved the field-level semantic authority registry as the binding source of "
            "semantic truth for CAS Harness run bindings, so that claim-bearing A/B work (roadmap "
            "item 4) may proceed. Approval was given explicitly in an interactive session after the "
            "readiness audit was reported, including its open findings."
        ),
        "signature": signature,
        "approves": [
            "The 20 registry sources as the enumerated semantic authorities.",
            "The 8-tier claim_bearing_precedence ordering.",
            "The 25 required_run_bindings as mandatory for claim-bearing runs.",
            "The 7 future_agent_rules as binding on future work.",
        ],
        "does_not_approve": [
            "Resolution of the 12 recorded known_conflicts.",
            "Acquisition and algebra profiles (remain `unavailable` per roadmap:202-203).",
            "Any empirical claim, verdict, or licence.",
        ],
        "open_findings_at_signing": OPEN_FINDINGS_AT_SIGNING,
        "artifact_refs": [REGISTRY_REL],
        "artifact_hashes": {REGISTRY_REL: sha256_file(registry)},
        "created_at": signed_at,
        "receipt_hash": None,
    }
    receipt["receipt_hash"] = compute_receipt_hash(receipt)
    return receipt


def verify_receipt(receipt: dict[str, Any], *, repo_root: Path) -> tuple[bool, list[str]]:
    problems: list[str] = []
    if not receipt.get("approved"):
        problems.append("approved is not True")
    for field in ("operator_id", "signed_reason", "signature"):
        if not receipt.get(field):
            problems.append(f"approved receipt requires {field}")
    stored = receipt.get("receipt_hash")
    if not stored or stored != compute_receipt_hash(receipt):
        problems.append("receipt_hash does not match recomputed hash")
    for ref in receipt.get("artifact_refs", []):
        expected = receipt.get("artifact_hashes", {}).get(ref)
        path = repo_root / ref
        if not expected:
            problems.append(f"no artifact hash recorded for {ref}")
        elif not path.exists():
            problems.append(f"artifact missing: {ref}")
        elif sha256_file(path) != expected:
            problems.append(f"artifact hash mismatch (registry changed since signing): {ref}")
    return (not problems), problems


def main() -> int:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--operator-id", required=True)
    parser.add_argument("--signature", required=True)
    parser.add_argument("--signed-at", default=None)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--verify-only", type=Path, default=None)
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    if args.verify_only:
        receipt = json.loads(args.verify_only.read_text(encoding="utf-8"))
        ok, problems = verify_receipt(receipt, repo_root=repo_root)
        print(f"verify: {ok}")
        for p in problems:
            print(f"  PROBLEM: {p}")
        return 0 if ok else 1

    signed_at = args.signed_at or datetime.now(UTC).isoformat()
    receipt = build_receipt(
        repo_root=repo_root, operator_id=args.operator_id,
        signature=args.signature, signed_at=signed_at,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
    ok, problems = verify_receipt(receipt, repo_root=repo_root)
    print(f"wrote {args.output}")
    print(f"receipt_hash: {receipt['receipt_hash']}")
    print(f"registry sha256: {receipt['artifact_hashes'][REGISTRY_REL]}")
    print(f"verify: {ok}")
    for p in problems:
        print(f"  PROBLEM: {p}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
