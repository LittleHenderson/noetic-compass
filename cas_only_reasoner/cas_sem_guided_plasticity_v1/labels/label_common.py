"""label_common.py -- shared, deterministic helpers for LABEL PHASE 0B.

No neural workload. No network. No model calls. Pure-CPU deterministic utilities:
tokenization/matching, SHA-256 digests, YAML/JSON IO, and the ONE enforced invariant
that a label packet is claim-bearing iff its authority is a gold authority.

This module is the single definition of:
  - how a rule term matches a gloss (so the engine and the tests agree exactly);
  - which authorities are claim-bearing (so nothing else can quietly widen it).
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path

import yaml

ENGINE_VERSION = "label_phase0b.v1"

# The ONLY authorities that may carry a claim-bearing label. Frozen here on purpose.
CLAIM_BEARING_AUTHORITIES = ("CONSTRUCTION_GOLD", "RESOURCE_GOLD", "OWNER_CORRECTED")
ALL_AUTHORITIES = (
    "CONSTRUCTION_GOLD",
    "RESOURCE_GOLD",
    "MODEL_PROPOSED",
    "WEAK_LABEL",
    "ABSTAIN",
    "OWNER_CORRECTED",
)
CAS_CLASSES = ("^2", "^3", "^6", "^8")
ABSTAIN_REASONS = ("no_rule", "multiple_rules", "source_conflict", "unverifiable_source", "ambiguous")


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


# ----------------------------------------------------------------------------- packet
def is_claim_bearing(authority: str) -> bool:
    return authority in CLAIM_BEARING_AUTHORITIES


def make_packet(packet_id, authority, cas_label, provenance, **kw):
    """Construct a packet with the claim_bearing invariant ENFORCED, not passed in.

    Raises ValueError on any inconsistent combination, so a bad label can never be
    serialized as claim-bearing.
    """
    if authority not in ALL_AUTHORITIES:
        raise ValueError(f"unknown authority {authority!r}")
    if cas_label is not None and cas_label not in CAS_CLASSES:
        raise ValueError(f"unknown cas_label {cas_label!r}")

    claim_bearing = is_claim_bearing(authority)

    # Gold authority requires an actual class; ABSTAIN/MODEL_PROPOSED must not smuggle one
    # in as if it were established truth.
    if authority in ("CONSTRUCTION_GOLD", "RESOURCE_GOLD", "OWNER_CORRECTED") and cas_label is None:
        raise ValueError(f"{authority} requires a non-null cas_label")
    if authority == "ABSTAIN" and cas_label is not None:
        raise ValueError("ABSTAIN must have cas_label = null")

    packet = {
        "packet_id": packet_id,
        "authority": authority,
        "cas_label": cas_label,
        "claim_bearing": claim_bearing,
        "sense": kw.get("sense"),
        "construction": kw.get("construction"),
        "fired_rules": kw.get("fired_rules", []),
        "blocked_rules": kw.get("blocked_rules", []),
        "abstain_reason": kw.get("abstain_reason"),
        "evidence": kw.get("evidence"),
        "surface": kw.get("surface"),
        "provenance": provenance,
    }
    return packet


def validate_packet(packet: dict) -> dict:
    """Re-derive and ENFORCE the claim_bearing invariant on a packet from ANY source.

    make_packet enforces the invariant at construction time, but a packet read back from
    disk (or hand-authored, or emitted by a model) has not passed through make_packet. This
    guard recomputes claim_bearing from authority and rejects any mismatch, so a file with
    authority=MODEL_PROPOSED and claim_bearing=true can never be ingested as truth.

    Returns the packet if consistent; raises ValueError otherwise.
    """
    auth = packet.get("authority")
    if auth not in ALL_AUTHORITIES:
        raise ValueError(f"unknown authority {auth!r}")
    expected = is_claim_bearing(auth)
    if bool(packet.get("claim_bearing")) != expected:
        raise ValueError(
            f"claim_bearing {packet.get('claim_bearing')!r} != derived {expected} for authority {auth!r}"
        )
    lbl = packet.get("cas_label")
    if lbl is not None and lbl not in CAS_CLASSES:
        raise ValueError(f"unknown cas_label {lbl!r}")
    if auth in ("CONSTRUCTION_GOLD", "RESOURCE_GOLD", "OWNER_CORRECTED") and lbl is None:
        raise ValueError(f"{auth} requires a non-null cas_label")
    if auth == "ABSTAIN" and lbl is not None:
        raise ValueError("ABSTAIN must have cas_label = null")
    return packet


def load_packets(path):
    """Load a packets JSON from disk AND enforce the claim_bearing invariant on every one."""
    packets = load_json(path)
    for i, p in enumerate(packets):
        try:
            validate_packet(p)
        except ValueError as e:
            raise ValueError(f"packet {i} ({p.get('packet_id')}) failed ingest guard: {e}") from e
    return packets
