"""label_common.py -- shared, deterministic helpers for LABEL PHASE 0B/0C.

No neural workload. No network. No model calls. Pure-CPU deterministic utilities:
tokenization/matching, SHA-256 digests, YAML/JSON IO, and the enforced authority model.

PHASE 0C AUTHORITY REPAIR (owner directive, 2026-08-30):
The Phase 0B code confused deterministic derivation with audited scientific authority --
the engine's output became claim-bearing the moment a keyword rule fired. That is fixed.

Authority flow now:

    RESOURCE_RULE_DERIVED   --owner audit + signed promotion-->   RESOURCE_GOLD
    CONSTRUCTION_CANDIDATE  --generator audit + signed promotion--> CONSTRUCTION_GOLD

- The deterministic engine emits RESOURCE_RULE_DERIVED. NEVER gold. A deterministic
  keyword filter freezes a judgment; it does not validate the judgment.
- The template generator emits CONTROLLED_TEMPLATE_FIXTURE (its round-trip checker shares
  the generator's verb table -- circular -- so it is a pipeline fixture, never evaluation
  data). The future CAS-trace generator (CAS_TRACE_GOLD_SPEC_v1.md) emits
  CONSTRUCTION_CANDIDATE.
- Gold authorities (CONSTRUCTION_GOLD, RESOURCE_GOLD, OWNER_CORRECTED) can be created ONLY
  by owner_gated_promotion.py, which verifies an owner-signed approval record, an audit
  receipt, and matching digests. make_packet REFUSES to construct gold packets.
- claim_bearing is DERIVED, four conditions, all required:
      authority in GOLD_AUTHORITIES
      AND audit_state == "OWNER_APPROVED"
      AND every required approval digest is present
      AND phase_approval_valid is True
  Model consensus grants no authority at any step.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path

import yaml

ENGINE_VERSION = "label_phase0c.v1"

# ---- authority model (frozen here on purpose; nothing else may widen it) ----
GOLD_AUTHORITIES = ("CONSTRUCTION_GOLD", "RESOURCE_GOLD", "OWNER_CORRECTED")
CANDIDATE_AUTHORITIES = ("CONSTRUCTION_CANDIDATE", "RESOURCE_RULE_DERIVED")
FIXTURE_AUTHORITIES = ("CONTROLLED_TEMPLATE_FIXTURE",)  # retired circular generator output
NEVER_PROMOTABLE = ("MODEL_PROPOSED", "WEAK_LABEL", "ABSTAIN") + FIXTURE_AUTHORITIES
ALL_AUTHORITIES = GOLD_AUTHORITIES + CANDIDATE_AUTHORITIES + NEVER_PROMOTABLE
# make_packet may construct everything EXCEPT gold; gold is promotion-only.
CONSTRUCTIBLE_AUTHORITIES = CANDIDATE_AUTHORITIES + NEVER_PROMOTABLE

AUDIT_STATES = ("UNAUDITED", "GENERATOR_APPROVED", "OWNER_APPROVED")
CAS_CLASSES = ("^2", "^3", "^6", "^8")
ABSTAIN_REASONS = ("no_rule", "multiple_rules", "source_conflict", "unverifiable_source", "ambiguous")

APPROVAL_FIELDS = (
    "audit_state",
    "approval_manifest_digest",
    "owner_approval_digest",
    "resource_manifest_digest",
    "generator_manifest_digest",
    "phase_approval_valid",
)


# ----------------------------------------------------------------------------- text
def normalize_text(text: str) -> str:
    """Lowercase, Unicode NFKD, every non-alphanumeric run -> single space, collapse."""
    if text is None:
        return ""
    t = unicodedata.normalize("NFKD", str(text)).lower()
    t = re.sub(r"[^0-9a-z]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def term_matches(term: str, normalized_text: str) -> bool:
    """Whole-word / whole-phrase match of a (possibly multi-word) term in normalized text."""
    nterm = normalize_text(term)
    if not nterm:
        return False
    return re.search(r"(?<![0-9a-z])" + re.escape(nterm) + r"(?![0-9a-z])", normalized_text) is not None


def any_term_matches(terms, normalized_text: str):
    """Return the sorted list of terms that match (deterministic order)."""
    hits = [t for t in terms if term_matches(t, normalized_text)]
    return sorted(set(hits))


# ----------------------------------------------------------------------------- digests / io
def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def sha256_file_normalized(path) -> str:
    """Digest of a text file with line endings normalized to LF (stable across CRLF checkouts)."""
    text = Path(path).read_text(encoding="utf-8")
    return sha256_bytes(text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8"))


def canonical_json(obj) -> str:
    """Stable JSON: sorted keys, no ambiguous whitespace, ensure_ascii for byte-stability."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=True, separators=(",", ":"))


def sha256_obj(obj) -> str:
    return sha256_bytes(canonical_json(obj).encode("utf-8"))


def load_yaml(path):
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


# ----------------------------------------------------------------------------- claim_bearing
def derive_claim_bearing(packet: dict) -> bool:
    """The ONLY definition of claim-bearing. Four conditions, all required.

    Deterministic derivation (a rule fired) is NOT audited authority (the owner approved).
    """
    if packet.get("authority") not in GOLD_AUTHORITIES:
        return False
    if packet.get("audit_state") != "OWNER_APPROVED":
        return False
    if not packet.get("approval_manifest_digest") or not packet.get("owner_approval_digest"):
        return False
    # the source-side digest must be present for the matching gold kind
    if packet.get("authority") == "RESOURCE_GOLD" and not packet.get("resource_manifest_digest"):
        return False
    if packet.get("authority") == "CONSTRUCTION_GOLD" and not packet.get("generator_manifest_digest"):
        return False
    if packet.get("phase_approval_valid") is not True:
        return False
    return True


def make_packet(packet_id, authority, cas_label, provenance, **kw):
    """Construct a NON-GOLD packet. Gold authorities are REFUSED here.

    Only owner_gated_promotion.promote() may create CONSTRUCTION_GOLD / RESOURCE_GOLD /
    OWNER_CORRECTED packets, and only with a verified owner-signed approval. This function
    always produces claim_bearing = False (derived -- a candidate/fixture/abstain packet can
    never satisfy derive_claim_bearing).
    """
    if authority in GOLD_AUTHORITIES:
        raise ValueError(
            f"make_packet refuses gold authority {authority!r}: gold exists only via "
            "owner_gated_promotion with a verified owner-signed approval"
        )
    if authority not in CONSTRUCTIBLE_AUTHORITIES:
        raise ValueError(f"unknown authority {authority!r}")
    if cas_label is not None and cas_label not in CAS_CLASSES:
        raise ValueError(f"unknown cas_label {cas_label!r}")
    # candidate/fixture authorities require a class; ABSTAIN must not smuggle one in
    if authority in CANDIDATE_AUTHORITIES + FIXTURE_AUTHORITIES and cas_label is None:
        raise ValueError(f"{authority} requires a non-null cas_label")
    if authority == "ABSTAIN" and cas_label is not None:
        raise ValueError("ABSTAIN must have cas_label = null")

    packet = {
        "packet_id": packet_id,
        "authority": authority,
        "cas_label": cas_label,
        "audit_state": "UNAUDITED",
        "approval_manifest_digest": None,
        "owner_approval_digest": None,
        "resource_manifest_digest": None,
        "generator_manifest_digest": None,
        "phase_approval_valid": False,
        "sense": kw.get("sense"),
        "construction": kw.get("construction"),
        "fired_rules": kw.get("fired_rules", []),
        "blocked_rules": kw.get("blocked_rules", []),
        "abstain_reason": kw.get("abstain_reason"),
        "evidence": kw.get("evidence"),
        "surface": kw.get("surface"),
        "provenance": provenance,
    }
    packet["claim_bearing"] = derive_claim_bearing(packet)  # always False here
    assert packet["claim_bearing"] is False
    return packet


def validate_packet(packet: dict) -> dict:
    """Re-derive and ENFORCE the claim_bearing invariant on a packet from ANY source.

    A packet read back from disk (or hand-authored, or emitted by a model) has not passed
    through make_packet/promote. This guard recomputes claim_bearing from the packet's
    authority + audit + digest + approval fields and rejects any mismatch, so a file with a
    forged claim_bearing flag can never be ingested as truth.
    """
    auth = packet.get("authority")
    if auth not in ALL_AUTHORITIES:
        raise ValueError(f"unknown authority {auth!r}")
    if packet.get("audit_state", "UNAUDITED") not in AUDIT_STATES:
        raise ValueError(f"unknown audit_state {packet.get('audit_state')!r}")
    expected = derive_claim_bearing(packet)
    if bool(packet.get("claim_bearing")) != expected:
        raise ValueError(
            f"claim_bearing {packet.get('claim_bearing')!r} != derived {expected} "
            f"for authority {auth!r} / audit_state {packet.get('audit_state')!r}"
        )
    lbl = packet.get("cas_label")
    if lbl is not None and lbl not in CAS_CLASSES:
        raise ValueError(f"unknown cas_label {lbl!r}")
    if auth in GOLD_AUTHORITIES + CANDIDATE_AUTHORITIES + FIXTURE_AUTHORITIES and lbl is None:
        raise ValueError(f"{auth} requires a non-null cas_label")
    if auth == "ABSTAIN" and lbl is not None:
        raise ValueError("ABSTAIN must have cas_label = null")
    return packet


def load_packets(path, registry_path=None):
    """Load a packets JSON from disk AND enforce the claim_bearing invariant on every one.

    GOLD REGISTRY GUARD (Phase 0C hardening): a hand-authored packet can be made
    internally CONSISTENT (gold authority + OWNER_APPROVED + fake digests +
    phase_approval_valid), so per-packet consistency alone cannot stop a forgery. Any file
    containing a gold-authority packet must therefore be REGISTERED: its SHA-256 must
    appear in PROMOTED_REGISTRY.json, which only owner_gated_promotion.promote() writes
    (after verifying the owner-signed approval). An unregistered gold-bearing file raises
    UNREGISTERED_GOLD_DATASET. The registry is a committed artifact - edits to it are
    visible git diffs for owner review.
    """
    packets = load_json(path)
    for i, p in enumerate(packets):
        try:
            validate_packet(p)
        except ValueError as e:
            raise ValueError(f"packet {i} ({p.get('packet_id')}) failed ingest guard: {e}") from e

    if any(p.get("authority") in GOLD_AUTHORITIES for p in packets):
        reg_path = Path(registry_path) if registry_path else (Path(__file__).resolve().parent / "PROMOTED_REGISTRY.json")
        file_digest = sha256_file(path)
        registered = set()
        if reg_path.exists():
            registered = set((load_json(reg_path).get("promoted") or {}).keys())
        if file_digest not in registered:
            raise ValueError(
                f"UNREGISTERED_GOLD_DATASET: {path} contains gold-authority packets but its "
                f"sha256 {file_digest[:12]}... is not in the promoted registry "
                f"({reg_path}); only owner_gated_promotion may register gold datasets")
    return packets
