"""test_trust_root.py -- the section-3 owner-trust-root tests (GATE 1A.2).

The production verifier reads only trust/OWNER_PUBLIC_KEY_PIN.json; there is no
caller key parameter anywhere; the template refuses; TEST- keys can never enter
production; test mode is permanently non-claim-bearing.
"""
from __future__ import annotations

import inspect
import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
sys.path.insert(0, str(PKG))
sys.path.insert(0, str(HERE))
from exec.trust_root import (OwnerKeyNotPinned, TrustRootViolation,  # noqa: E402
                             load_trust_root)


def clone_pkg_min(tmp: Path) -> Path:
    """A minimal package copy carrying only the trust/test fixture layout."""
    root = tmp / "pkg"
    (root / "trust").mkdir(parents=True)
    (root / "tests" / "fixtures").mkdir(parents=True)
    shutil.copy(PKG / "trust" / "OWNER_PUBLIC_KEY_PIN_TEMPLATE.json",
                root / "trust" / "OWNER_PUBLIC_KEY_PIN_TEMPLATE.json")
    shutil.copy(PKG / "tests" / "fixtures" / "TEST_OWNER_PUBLIC_KEY_PIN.json",
                root / "tests" / "fixtures" / "TEST_OWNER_PUBLIC_KEY_PIN.json")
    return root


def test_production_verifier_refuses_missing_owner_pin():
    with tempfile.TemporaryDirectory() as tmp:
        root = clone_pkg_min(Path(tmp))
        try:
            load_trust_root(root, "PRODUCTION")
            raise AssertionError("missing pin accepted")
        except OwnerKeyNotPinned as exc:
            assert "OWNER_KEY_NOT_PINNED" in str(exc)
    print("PASS test_production_verifier_refuses_missing_owner_pin")


def test_production_verifier_refuses_placeholder_owner_pin():
    with tempfile.TemporaryDirectory() as tmp:
        root = clone_pkg_min(Path(tmp))
        shutil.copy(root / "trust" / "OWNER_PUBLIC_KEY_PIN_TEMPLATE.json",
                    root / "trust" / "OWNER_PUBLIC_KEY_PIN.json")
        try:
            load_trust_root(root, "PRODUCTION")
            raise AssertionError("template pin accepted")
        except OwnerKeyNotPinned:
            pass
    print("PASS test_production_verifier_refuses_placeholder_owner_pin")


def test_caller_cannot_substitute_public_key():
    sig = inspect.signature(load_trust_root)
    assert list(sig.parameters) == ["package_root", "mode"], \
        "trust root loader must take NO key material"
    try:
        load_trust_root(PKG, "PRODUCTION", pinned_pubkey_hex="ff" * 32)  # type: ignore
        raise AssertionError("a key parameter was accepted")
    except TypeError:
        pass
    import verify_phase_approval as vpa
    for fn in (vpa.verify_execution, vpa.verify_container_prep):
        params = list(inspect.signature(fn).parameters)
        assert not any("pubkey" in p or "public_key" in p for p in params), \
            f"{fn.__name__} exposes a key parameter"
    src = (HERE / "verify_phase_approval.py").read_text(encoding="utf-8")
    # the docstring NAMES the banned flag while banning it; what must not exist
    # is a definition or a read of it
    assert 'add_argument("--pinned-pubkey-hex"' not in src \
        and "add_argument('--pinned-pubkey-hex'" not in src \
        and "pinned_pubkey_hex" not in src, \
        "the banned CLI flag is actually defined or read"
    print("PASS test_caller_cannot_substitute_public_key")


def test_nonowner_signature_refused():
    """A record signed by a key that is NOT the trust-root pin is refused even
    when the record embeds its own (matching) public key."""
    with tempfile.TemporaryDirectory() as tmp:
        root = clone_pkg_min(Path(tmp))
        from cryptography.hazmat.primitives.asymmetric.ed25519 import \
            Ed25519PrivateKey
        rogue = Ed25519PrivateKey.generate()
        # synthetic mode: pin is the TEST fixture; rogue key id matches, key doesn't
        record = {"owner_key_id": "TEST-GATE1A2-CONFORMANCE-KEY-v1",
                  "ed25519_signature": ""}
        from verify_phase_approval import canonical_signing_bytes
        record["ed25519_signature"] = rogue.sign(
            canonical_signing_bytes(record)).hex()
        import verify_phase_approval as vpa
        try:
            vpa._verify_signature(record, root, "SYNTHETIC_CONFORMANCE")
            raise AssertionError("rogue signature verified")
        except vpa.ApprovalInvalid:
            pass
    print("PASS test_nonowner_signature_refused")


def test_test_key_cannot_enter_production_mode():
    with tempfile.TemporaryDirectory() as tmp:
        root = clone_pkg_min(Path(tmp))
        fixture = json.loads(
            (root / "tests" / "fixtures" / "TEST_OWNER_PUBLIC_KEY_PIN.json")
            .read_text(encoding="utf-8"))
        (root / "trust" / "OWNER_PUBLIC_KEY_PIN.json").write_text(
            json.dumps(fixture), encoding="utf-8")     # plant the TEST pin
        try:
            load_trust_root(root, "PRODUCTION")
            raise AssertionError("a TEST- key entered production")
        except (TrustRootViolation, OwnerKeyNotPinned):
            pass
    print("PASS test_test_key_cannot_enter_production_mode")


def test_test_mode_is_permanently_non_claim_bearing():
    """The synthetic pin must be non_claim_bearing, and the status program
    refuses a TEST- key outside conformance mode (proven in the status suite);
    here: a synthetic pin edited to claim-bearing is refused outright."""
    with tempfile.TemporaryDirectory() as tmp:
        root = clone_pkg_min(Path(tmp))
        p = root / "tests" / "fixtures" / "TEST_OWNER_PUBLIC_KEY_PIN.json"
        fixture = json.loads(p.read_text(encoding="utf-8"))
        key_id, pub = load_trust_root(root, "SYNTHETIC_CONFORMANCE")
        assert key_id.startswith("TEST-")
        fixture["non_claim_bearing"] = False
        p.write_text(json.dumps(fixture), encoding="utf-8")
        try:
            load_trust_root(root, "SYNTHETIC_CONFORMANCE")
            raise AssertionError("claim-bearing synthetic pin accepted")
        except TrustRootViolation:
            pass
    print("PASS test_test_mode_is_permanently_non_claim_bearing")


def main():
    test_production_verifier_refuses_missing_owner_pin()
    test_production_verifier_refuses_placeholder_owner_pin()
    test_caller_cannot_substitute_public_key()
    test_nonowner_signature_refused()
    test_test_key_cannot_enter_production_mode()
    test_test_mode_is_permanently_non_claim_bearing()
    print("ALL TRUST-ROOT TESTS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
