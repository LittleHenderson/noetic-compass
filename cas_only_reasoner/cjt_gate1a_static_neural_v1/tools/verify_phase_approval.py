"""verify_phase_approval.py -- the COMMITTED Gate 1B approval verifier.

Fails closed: Gate 1B launch code must call verify() and refuse on ANY exception or
False. Uses Ed25519 (asymmetric): this verifier holds only the PUBLIC key and cannot
forge an approval (review fix over the earlier HMAC design).

Usage: python verify_phase_approval.py OWNER_PHASE_APPROVAL_SIGNED.json PINNED_PUBKEY_HEX
Requires: cryptography (present in the Gate 1B container; pinned there).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def canonical_signing_bytes(record: dict) -> bytes:
    unsigned = dict(record)
    unsigned["ed25519_signature"] = ""
    return json.dumps(unsigned, sort_keys=True, ensure_ascii=True,
                      separators=(",", ":")).encode("utf-8")


def verify(record: dict, pinned_public_key_hex: str) -> bool:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    if record.get("record_id") != "OWNER_PHASE_APPROVAL_GATE1B":
        raise ValueError("wrong record_id")
    if record.get("decision") != "APPROVED":
        raise ValueError(f"decision is {record.get('decision')!r}, not APPROVED")
    if record.get("gate0_anchor_sha") != "83f57d6f724505f2c2c68593b2625c36c3e07a4d":
        raise ValueError("wrong Gate 0 anchor")
    key_hex = record.get("owner_ed25519_public_key_hex", "")
    if key_hex != pinned_public_key_hex:
        raise ValueError("in-record public key differs from the PINNED public key")
    sig = bytes.fromhex(record["ed25519_signature"])
    Ed25519PublicKey.from_public_bytes(bytes.fromhex(key_hex)).verify(
        sig, canonical_signing_bytes(record))          # raises InvalidSignature
    return True


def main():
    record = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    try:
        ok = verify(record, sys.argv[2].strip().lower())
    except Exception as exc:  # noqa: BLE001 -- fail closed, name the reason
        print(f"REFUSED: {type(exc).__name__}: {exc}")
        return 1
    print("APPROVAL_VERIFIED" if ok else "REFUSED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
