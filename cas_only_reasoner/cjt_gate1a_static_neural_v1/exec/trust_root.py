"""trust_root.py -- the STRUCTURAL owner trust root (GATE 1A.2 section 3).

The production verifier reads the owner public key from exactly one fixed path:
    trust/OWNER_PUBLIC_KEY_PIN.json
There is NO parameter for caller-supplied key bytes, NO CLI flag, NO environment
variable, and NO acceptance of a key that exists only inside the approval being
verified. Until the owner pins a real key (a later owner-controlled commit),
production verification fails closed with OWNER_KEY_NOT_PINNED.

SYNTHETIC_CONFORMANCE mode reads only tests/fixtures/TEST_OWNER_PUBLIC_KEY_PIN.json,
whose key id is prefixed TEST- and whose non_claim_bearing flag is true; the
production path refuses any TEST- key id or non_claim_bearing pin, so the test
key can never enter production and nothing it verifies can ever be claim-bearing.
"""
from __future__ import annotations

import json
from pathlib import Path

PRODUCTION_PIN_RELPATH = Path("trust") / "OWNER_PUBLIC_KEY_PIN.json"
TEST_PIN_RELPATH = Path("tests") / "fixtures" / "TEST_OWNER_PUBLIC_KEY_PIN.json"
MODES = ("PRODUCTION", "SYNTHETIC_CONFORMANCE")


class OwnerKeyNotPinned(RuntimeError):
    pass


class TrustRootViolation(RuntimeError):
    pass


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _is_hex64(s) -> bool:
    return isinstance(s, str) and len(s) == 64 and \
        all(c in "0123456789abcdef" for c in s)


def load_trust_root(package_root, mode: str):
    """Return (key_id, public_key_hex) for the given mode, or raise.

    Deliberately takes NO key material: the trust root is the file system path,
    nothing else. (test_caller_cannot_substitute_public_key asserts this
    signature has no key parameter.)"""
    if mode not in MODES:
        raise TrustRootViolation(f"unknown trust mode {mode!r}")
    package_root = Path(package_root).resolve()
    if mode == "PRODUCTION":
        pin_path = package_root / PRODUCTION_PIN_RELPATH
        if not pin_path.is_file():
            raise OwnerKeyNotPinned(
                "OWNER_KEY_NOT_PINNED: trust/OWNER_PUBLIC_KEY_PIN.json is absent; "
                "the owner has not pinned a key -- nothing can be verified as "
                "owner-approved")
        pin = _load_json(pin_path)
        if pin.get("status") == "OWNER_KEY_NOT_YET_PINNED" or pin.get("TEMPLATE"):
            raise OwnerKeyNotPinned(
                "OWNER_KEY_NOT_PINNED: the pin file is the placeholder template")
        key_id = pin.get("key_id", "")
        pub = pin.get("owner_ed25519_public_key_hex", "")
        if pin.get("pin_id") != "OWNER_PUBLIC_KEY_PIN" or not _is_hex64(pub):
            raise OwnerKeyNotPinned(
                "OWNER_KEY_NOT_PINNED: the pin file is malformed or incomplete")
        if not isinstance(key_id, str) or key_id.startswith("TEST-") \
                or pin.get("non_claim_bearing") is not False:
            raise TrustRootViolation(
                "TRUST_ROOT_VIOLATION: a TEST/non-claim-bearing key can never "
                "enter production mode")
        return key_id, pub
    # SYNTHETIC_CONFORMANCE
    pin_path = package_root / TEST_PIN_RELPATH
    if not pin_path.is_file():
        raise TrustRootViolation("test fixture pin absent")
    pin = _load_json(pin_path)
    key_id = pin.get("key_id", "")
    pub = pin.get("owner_ed25519_public_key_hex", "")
    if not key_id.startswith("TEST-") or pin.get("non_claim_bearing") is not True \
            or not _is_hex64(pub):
        raise TrustRootViolation(
            "TRUST_ROOT_VIOLATION: the synthetic pin must be a TEST- key with "
            "non_claim_bearing true")
    return key_id, pub
