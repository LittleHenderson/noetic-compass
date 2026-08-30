"""owner_gated_promotion.py -- the ONLY path from candidate labels to gold labels.

PHASE 0C (hardened after adversarial audit). A deterministic labeling engine may issue
RESOURCE_RULE_DERIVED. It may NOT promote its own output to RESOURCE_GOLD. Promotion
happens here, and only when EVERY one of these verifies:

    1. the OWNER KEY IDENTITY: the supplied key file's SHA-256 must equal the fingerprint
       pinned in the committed OWNER_KEY_FINGERPRINT.json. While the fingerprint is the
       placeholder OWNER_TO_SET, promotion is impossible (KEY_NOT_PINNED). An agent
       generating its own key + signing its own approval is refused because its key's
       digest does not match the pinned owner fingerprint. (Trust model: the fingerprint
       is a committed artifact - changing it is a visible git diff the owner reviews.)
    2. an owner-signed approval record (HMAC-SHA256 over the canonical record, keyed by
       the owner-held secret) whose signature verifies under that pinned key;
    3. the approval's decision is APPROVE;
    4. the candidate dataset digest in the approval matches the candidate file on disk;
    5. the rule-table digest in the approval matches the current rule table;
    6. the source manifest digest matches, and the manifest attests protected results
       are NOT opened;
    7. an audit receipt whose digest the approval names, whose result is PASS under the
       sequential gate (0 major errors -> PASS; 1-2 -> REPAIR_AND_RESAMPLE; 3+ -> REJECT),
       and which ATTESTS that every mapping rule in the rule table was reviewed
       (rules_reviewed: {rule_id: true, ...} covering all rule ids);
    8. per-packet PROVENANCE: each packet's provenance.rule_table_digest must equal the
       verified rule table digest, and each RESOURCE_RULE_DERIVED packet's
       provenance.frozen_resource_digest must match an owner-frozen,
       claim_bearing_eligible resource entry in the manifest (a dev-surrogate or
       unfrozen OWNER_TO_FREEZE resource can never yield gold);
    9. for CONSTRUCTION_CANDIDATE packets: a real generator manifest file whose SHA-256
       equals the approval's generator_manifest_digest (no silent substitution).

On success it emits a NEW immutable promoted dataset (refuses to overwrite) AND registers
that dataset's SHA-256 in the committed PROMOTED_REGISTRY.json. The ingest guard
(label_common.load_packets) refuses any gold-bearing file whose digest is not in that
registry, so a hand-forged internally-consistent gold file cannot be ingested.

Refusal codes:
    OWNER_APPROVAL_REQUIRED       -- missing/unreadable approval record, key, or fingerprint file
    KEY_NOT_PINNED                -- fingerprint is the placeholder, or key digest != pinned
    UNSIGNED_APPROVAL             -- missing or invalid signature under the pinned key
    APPROVAL_NOT_APPROVE          -- decision field is not APPROVE
    WRONG_DIGEST                  -- candidate dataset (or generator manifest) digest mismatch
    RULE_TABLE_CHANGED            -- rule-table digest mismatch
    SOURCE_RESOURCE_CHANGED       -- source manifest digest mismatch
    POST_PROTECTED_MODIFICATION   -- manifest says protected results were opened
    FAILED_AUDIT                  -- receipt missing/mismatched/not PASS/rules not all reviewed
    PROVENANCE_MISMATCH           -- packet provenance does not bind to the verified artifacts
    GENERATOR_MANIFEST_REQUIRED   -- construction promotion without a verified generator manifest
    FIXTURE_NOT_PROMOTABLE        -- CONTROLLED_TEMPLATE_FIXTURE / shared-lookup provenance
    NOT_PROMOTABLE                -- MODEL_PROPOSED / WEAK_LABEL / ABSTAIN / already-gold
    OUTPUT_EXISTS                 -- promoted output path already exists (immutability)

OWNER_CORRECTED note: it is DEFINED as a gold authority but NOT yet creatable by any
implemented program - PROMOTION_MAP has no entry for it and make_packet refuses it
(fail-closed). A correction path must be added here, with its own owner-signed record,
before OWNER_CORRECTED can exist.

CPU-only, deterministic, no network, no model calls.
"""
from __future__ import annotations

import hashlib
import hmac as hmac_mod
from pathlib import Path

import label_common as LC

HERE = Path(__file__).resolve().parent
DEFAULT_FINGERPRINT_PATH = HERE / "OWNER_KEY_FINGERPRINT.json"
DEFAULT_REGISTRY_PATH = HERE / "PROMOTED_REGISTRY.json"

PROMOTION_MAP = {
    "RESOURCE_RULE_DERIVED": "RESOURCE_GOLD",
    "CONSTRUCTION_CANDIDATE": "CONSTRUCTION_GOLD",
}

SEQUENTIAL_GATE = {
    # major_errors -> outcome
    0: "PASS",
    1: "REPAIR_AND_RESAMPLE",
    2: "REPAIR_AND_RESAMPLE",
    # >= 3 -> REJECT
}


class PromotionRefused(Exception):
    """Raised with a NAMED reason code as the first word of the message."""

    def __init__(self, code: str, detail: str = ""):
        self.code = code
        super().__init__(f"{code}: {detail}" if detail else code)


def _hmac_sign(record_without_signature: dict, key_bytes: bytes) -> str:
    payload = LC.canonical_json(record_without_signature).encode("utf-8")
    return hmac_mod.new(key_bytes, payload, hashlib.sha256).hexdigest()


def sign_approval(record: dict, key_file) -> dict:
    """Owner-side helper: sign an approval record with the owner-held key file.

    The production key file lives OUTSIDE the agent's environment; only its SHA-256
    fingerprint is committed (OWNER_KEY_FINGERPRINT.json). Signing with any other key
    produces a record the promotion program refuses (KEY_NOT_PINNED).
    """
    key = Path(key_file).read_bytes()
    unsigned = {k: v for k, v in record.items() if k != "signature"}
    return {**unsigned, "signature": _hmac_sign(unsigned, key)}


def audit_gate_outcome(major_errors: int) -> str:
    """Sequential owner-audit gate: 0 -> PASS; 1-2 -> REPAIR_AND_RESAMPLE; 3+ -> REJECT."""
    if major_errors < 0:
        raise ValueError("major_errors must be >= 0")
    return SEQUENTIAL_GATE.get(major_errors, "REJECT")


def _eligible_resource_digests(manifest: dict) -> set:
    """Collect sha256 digests of manifest resources that are owner-frozen AND eligible.

    An entry is eligible iff it has a REAL digest (not the OWNER_TO_FREEZE placeholder)
    and claim_bearing_eligible is true. Walks nested resource dicts.
    """
    out = set()

    def walk(node):
        if isinstance(node, dict):
            sha = node.get("sha256")
            if isinstance(sha, str) and sha and sha != "OWNER_TO_FREEZE":
                if node.get("claim_bearing_eligible") is True:
                    out.add(sha)
            for v in node.values():
                walk(v)

    walk(manifest.get("resources", {}))
    return out


def register_promoted(out_path, approval_digest: str, registry_path=None):
    """Append the promoted dataset's digest to the committed registry (write-once entries)."""
    registry_path = Path(registry_path or DEFAULT_REGISTRY_PATH)
    if registry_path.exists():
        registry = LC.load_json(registry_path)
    else:
        registry = {"note": "Registry of owner-approved promoted datasets. The ingest guard "
                            "(label_common.load_packets) refuses gold-bearing files not listed "
                            "here. Committed: edits are visible git diffs for owner review.",
                    "promoted": {}}
    digest = LC.sha256_file(out_path)
    registry["promoted"][digest] = {
        "path": str(out_path),
        "owner_approval_digest": approval_digest,
    }
    LC.write_json(registry_path, registry)
    return digest


def promote(candidate_packets_path, approval_record_path, key_file_path,
            rule_table_path, source_manifest_path, audit_receipt_path, out_path,
            fingerprint_path=None, registry_path=None, generator_manifest_path=None):
    """Verify every gate, then emit the immutable promoted dataset. Returns the packets."""
    out_path = Path(out_path)
    if out_path.exists():
        raise PromotionRefused("OUTPUT_EXISTS", f"{out_path} already exists; promoted datasets are immutable")

    # ---- 1) owner key identity (pinned fingerprint) ----
    fp_path = Path(fingerprint_path or DEFAULT_FINGERPRINT_PATH)
    if not fp_path.exists():
        raise PromotionRefused("OWNER_APPROVAL_REQUIRED", "OWNER_KEY_FINGERPRINT.json not found")
    pinned = LC.load_json(fp_path).get("owner_key_sha256")
    if not pinned or pinned == "OWNER_TO_SET":
        raise PromotionRefused("KEY_NOT_PINNED",
                               "the owner has not pinned a signing-key fingerprint; promotion is impossible")
    key_file = Path(key_file_path)
    if not key_file.exists():
        raise PromotionRefused("OWNER_APPROVAL_REQUIRED", "owner signing key file not found (key stays outside the agent env)")
    key_bytes = key_file.read_bytes()
    if LC.sha256_bytes(key_bytes) != pinned:
        raise PromotionRefused("KEY_NOT_PINNED",
                               "supplied key's SHA-256 does not match the pinned owner fingerprint")

    # ---- 2) approval record + signature under the pinned key ----
    try:
        approval = LC.load_json(approval_record_path)
    except Exception as e:  # noqa: BLE001
        raise PromotionRefused("OWNER_APPROVAL_REQUIRED", f"cannot read approval record: {e}") from e
    sig = approval.get("signature")
    if not sig:
        raise PromotionRefused("UNSIGNED_APPROVAL", "approval record carries no signature")
    unsigned = {k: v for k, v in approval.items() if k != "signature"}
    expected_sig = _hmac_sign(unsigned, key_bytes)
    if not hmac_mod.compare_digest(sig, expected_sig):
        raise PromotionRefused("UNSIGNED_APPROVAL", "signature does not verify against the pinned owner key")

    if approval.get("decision") != "APPROVE":
        raise PromotionRefused("APPROVAL_NOT_APPROVE", f"decision is {approval.get('decision')!r}")

    # ---- 3) candidate dataset digest ----
    actual_candidate_digest = LC.sha256_file(candidate_packets_path)
    if approval.get("candidate_dataset_digest") != actual_candidate_digest:
        raise PromotionRefused("WRONG_DIGEST",
                               f"approval names candidate digest {str(approval.get('candidate_dataset_digest'))[:12]}..., "
                               f"file is {actual_candidate_digest[:12]}...")

    # ---- 4) rule table unchanged ----
    actual_rule_digest = LC.sha256_file(rule_table_path)
    if approval.get("rule_table_digest") != actual_rule_digest:
        raise PromotionRefused("RULE_TABLE_CHANGED",
                               "rule table digest differs from the one the owner approved")

    # ---- 5) source manifest unchanged + protected not opened ----
    actual_manifest_digest = LC.sha256_file(source_manifest_path)
    if approval.get("source_manifest_digest") != actual_manifest_digest:
        raise PromotionRefused("SOURCE_RESOURCE_CHANGED",
                               "source manifest digest differs from the one the owner approved")
    manifest = LC.load_json(source_manifest_path)
    if manifest.get("protected_opened") is not False:
        raise PromotionRefused("POST_PROTECTED_MODIFICATION",
                               "manifest does not attest protected_opened == false")
    eligible_digests = _eligible_resource_digests(manifest)

    # ---- 6) audit receipt: gate + full per-rule review attestation ----
    try:
        receipt = LC.load_json(audit_receipt_path)
    except Exception as e:  # noqa: BLE001
        raise PromotionRefused("FAILED_AUDIT", f"cannot read audit receipt: {e}") from e
    actual_receipt_digest = LC.sha256_file(audit_receipt_path)
    if approval.get("audit_receipt_digest") != actual_receipt_digest:
        raise PromotionRefused("FAILED_AUDIT", "audit receipt digest does not match the approval")
    outcome = audit_gate_outcome(int(receipt.get("major_errors", 999)))
    if receipt.get("result") != "PASS" or outcome != "PASS":
        raise PromotionRefused("FAILED_AUDIT",
                               f"audit result={receipt.get('result')!r}, gate outcome={outcome} "
                               f"(major_errors={receipt.get('major_errors')})")
    rule_table = LC.load_yaml(rule_table_path)
    all_rule_ids = {r["id"] for r in rule_table.get("rules", [])}
    reviewed = receipt.get("rules_reviewed") or {}
    not_reviewed = sorted(rid for rid in all_rule_ids if reviewed.get(rid) is not True)
    if not_reviewed:
        raise PromotionRefused("FAILED_AUDIT",
                               f"receipt does not attest review of every mapping rule: missing {not_reviewed}")

    # ---- 7) generator manifest (required iff construction candidates are present) ----
    packets = LC.load_packets(candidate_packets_path)
    has_construction = any(p["authority"] == "CONSTRUCTION_CANDIDATE" for p in packets)
    verified_generator_digest = None
    if has_construction:
        if not generator_manifest_path or not Path(generator_manifest_path).exists():
            raise PromotionRefused("GENERATOR_MANIFEST_REQUIRED",
                                   "construction promotion requires a generator manifest file")
        verified_generator_digest = LC.sha256_file(generator_manifest_path)
        if approval.get("generator_manifest_digest") != verified_generator_digest:
            raise PromotionRefused("WRONG_DIGEST",
                                   "generator manifest digest does not match the approval")

    # ---- 8) per-packet promotion with provenance binding ----
    approval_digest = LC.sha256_file(approval_record_path)
    promoted = []
    for p in packets:
        auth = p["authority"]
        if auth in LC.FIXTURE_AUTHORITIES:
            raise PromotionRefused("FIXTURE_NOT_PROMOTABLE",
                                   f"{p['packet_id']}: CONTROLLED_TEMPLATE_FIXTURE is pipeline fixture only")
        prov = p.get("provenance") or {}
        if prov.get("preservation_check") == "shared_verb_lookup":
            raise PromotionRefused("FIXTURE_NOT_PROMOTABLE",
                                   f"{p['packet_id']}: generator and checker share a class lookup (circular)")
        if auth not in PROMOTION_MAP:
            raise PromotionRefused("NOT_PROMOTABLE",
                                   f"{p['packet_id']}: authority {auth!r} is not promotable")
        # provenance must bind to the artifacts the owner actually approved
        if prov.get("rule_table_digest") != actual_rule_digest:
            raise PromotionRefused("PROVENANCE_MISMATCH",
                                   f"{p['packet_id']}: packet was labeled under a different rule table "
                                   f"({str(prov.get('rule_table_digest'))[:12]}... != {actual_rule_digest[:12]}...)")
        if auth == "RESOURCE_RULE_DERIVED":
            if prov.get("frozen_resource_digest") not in eligible_digests:
                raise PromotionRefused("PROVENANCE_MISMATCH",
                                       f"{p['packet_id']}: source resource is not an owner-frozen, "
                                       "claim_bearing_eligible manifest entry (dev surrogates and "
                                       "OWNER_TO_FREEZE placeholders can never yield gold)")
        gold = dict(p)
        gold["authority"] = PROMOTION_MAP[auth]
        gold["audit_state"] = "OWNER_APPROVED"
        gold["approval_manifest_digest"] = actual_manifest_digest
        gold["owner_approval_digest"] = approval_digest
        if gold["authority"] == "RESOURCE_GOLD":
            gold["resource_manifest_digest"] = actual_manifest_digest
        else:
            gold["generator_manifest_digest"] = verified_generator_digest
        gold["phase_approval_valid"] = True
        gold["claim_bearing"] = LC.derive_claim_bearing(gold)
        if gold["claim_bearing"] is not True:  # defensive: promotion must yield claim-bearing gold
            raise PromotionRefused("NOT_PROMOTABLE", f"{p['packet_id']}: promoted packet failed derivation")
        promoted.append(gold)

    LC.write_json(out_path, promoted)
    register_promoted(out_path, approval_digest, registry_path=registry_path)
    return promoted


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Owner-gated promotion of candidate labels to gold.")
    ap.add_argument("--candidates", required=True)
    ap.add_argument("--approval", required=True)
    ap.add_argument("--key-file", required=True, help="owner-held signing key (outside the agent env)")
    ap.add_argument("--rules", default=str(HERE / "CAS_MAPPING_RULES_v1_CANDIDATE.yaml"))
    ap.add_argument("--manifest", default=str(HERE / "SOURCE_RESOURCE_MANIFEST.json"))
    ap.add_argument("--audit-receipt", required=True)
    ap.add_argument("--generator-manifest", default=None)
    ap.add_argument("--fingerprint", default=str(DEFAULT_FINGERPRINT_PATH))
    ap.add_argument("--registry", default=str(DEFAULT_REGISTRY_PATH))
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    try:
        promoted = promote(args.candidates, args.approval, args.key_file,
                           args.rules, args.manifest, args.audit_receipt, args.out,
                           fingerprint_path=args.fingerprint, registry_path=args.registry,
                           generator_manifest_path=args.generator_manifest)
        print(f"PROMOTED {len(promoted)} packets -> {args.out}")
    except PromotionRefused as e:
        print(f"REFUSED {e}")
        raise SystemExit(2)
