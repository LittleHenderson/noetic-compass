from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
TESTS = Path(__file__).resolve().parent
for path in (SCRIPTS, TESTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

import sign_root_ci_protected_deploy_receipt as signer
import test_collect_root_ci_protected_deploy_facts as collector_test
import verify_customer_production_acceptance as acceptance


NOW = collector_test.NOW


def _ephemeral_key():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode("ascii")
    numbers = private_key.public_key().public_numbers()
    authority = {
        "n": numbers.n,
        "e": numbers.e,
        "allowed_subjects": frozenset(
            {("root_ci_protected_deploy", signer.SUBJECT_URI)}
        ),
        "valid_from": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "valid_until": datetime(2027, 1, 1, tzinfo=timezone.utc),
    }
    return private_key, pem, authority


def _draft_payload() -> dict:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        transport, _ = collector_test._fixture(root)
        return collector_test._collect(root, transport)


def _subject_bytes(payload: dict) -> bytes:
    return (
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")


class ReceiptSignerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.private_key, cls.pem, cls.authority = _ephemeral_key()

    def _trusted(self, authority=None):
        return {
            (signer.ISSUER, signer.KEY_ID): authority or deepcopy(self.authority)
        }

    def _sign(self, **overrides):
        payload = overrides.pop("payload", _draft_payload())
        options = {
            "payload": payload,
            "subject_bytes": _subject_bytes(payload),
            "expected_master_head": collector_test.MASTER_SHA,
            "expected_deploy_id": collector_test.DEPLOY_ID,
            "private_key_pem": self.pem,
            "trusted_issuers": self._trusted(),
            "now": NOW,
            "expiry_minutes": 120,
        }
        options.update(overrides)
        return signer.sign_root_ci_protected_deploy_receipt(**options)

    def test_ephemeral_key_receipt_passes_production_receipt_and_gate_validation(self) -> None:
        payload = _draft_payload()
        subject = _subject_bytes(payload)
        receipt = self._sign(payload=payload, subject_bytes=subject)
        self.assertEqual(receipt["schema_version"], acceptance.RECEIPT_SCHEMA_VERSION)
        self.assertEqual(receipt["issuer"], signer.ISSUER)
        self.assertEqual(receipt["key_id"], signer.KEY_ID)
        self.assertEqual(receipt["gate"], "root_ci_protected_deploy")
        self.assertEqual(receipt["subject_uri"], signer.SUBJECT_URI)
        self.assertEqual(receipt["subject_sha256"], hashlib.sha256(subject).hexdigest())
        self.assertEqual(receipt["evidence"]["artifact_uri"], signer.SUBJECT_URI)
        self.assertEqual(
            receipt["evidence"]["artifact_sha256"], receipt["subject_sha256"]
        )
        rendered = json.dumps(receipt, sort_keys=True)
        self.assertNotIn("PRIVATE KEY", rendered)

        context = acceptance.ValidationContext(
            repo_root=ROOT,
            evidence_root=ROOT,
            verification_time=NOW,
            generated_at=NOW,
            expected_master_head=collector_test.MASTER_SHA,
            expected_deploy_id=collector_test.DEPLOY_ID,
            repository_commit=collector_test.MASTER_SHA,
            live=False,
            trusted_issuers=self._trusted(),
            registry_sha256="0" * 64,
        )
        evidence = acceptance._validate_receipt(
            receipt,
            gate="root_ci_protected_deploy",
            issuer_name=signer.ISSUER,
            key_id=signer.KEY_ID,
            context=context,
            path="$.receipt",
        )
        self.assertIsNotNone(evidence)
        assert evidence is not None
        acceptance._validate_root_ci(evidence, context)
        self.assertEqual(context.errors, [])

    def test_private_key_must_match_pinned_ephemeral_public_key(self) -> None:
        _, other_pem, _ = _ephemeral_key()
        with self.assertRaisesRegex(signer.SigningError, "does not match"):
            self._sign(private_key_pem=other_pem)

    def test_exact_subject_grant_and_validity_window_are_required(self) -> None:
        no_grant = deepcopy(self.authority)
        no_grant["allowed_subjects"] = frozenset(
            {("root_ci_protected_deploy", acceptance.REPOSITORY_URL)}
        )
        with self.assertRaisesRegex(signer.SigningError, "exact root-CI subject"):
            self._sign(trusted_issuers=self._trusted(no_grant))

        expired = deepcopy(self.authority)
        expired["valid_until"] = datetime(2026, 7, 14, 7, 59, tzinfo=timezone.utc)
        with self.assertRaisesRegex(signer.SigningError, "validity window"):
            self._sign(trusted_issuers=self._trusted(expired))

    def test_invalid_payload_is_rejected_before_signing(self) -> None:
        payload = _draft_payload()
        payload["deployment"]["auto_deploy_trigger"] = "commit"
        with self.assertRaisesRegex(signer.SigningError, "production validation"):
            self._sign(payload=payload)

    def test_receipt_ttl_is_fixed_at_120_minutes(self) -> None:
        for expiry in (119, 121, 1440):
            with self.subTest(expiry=expiry), self.assertRaisesRegex(
                signer.SigningError, "exactly 120 minutes"
            ):
                self._sign(expiry_minutes=expiry)

    def test_protected_signing_workflow_pins_the_same_120_minute_ttl(self) -> None:
        workflow = (ROOT / ".github/workflows/customer-production-evidence.yml").read_text(
            encoding="utf-8"
        )
        self.assertEqual(signer.DEFAULT_EXPIRY_MINUTES, 120)
        self.assertIn("--expiry-minutes 120", workflow)
        self.assertNotIn("--expiry-minutes \"$", workflow)

    def test_subject_must_be_the_same_canonical_raw_facts_document(self) -> None:
        payload = _draft_payload()
        other = deepcopy(payload)
        other["deploy_id"] = "dep-other"
        with self.assertRaisesRegex(signer.SigningError, "does not match"):
            self._sign(payload=payload, subject_bytes=_subject_bytes(other))

        noncanonical = json.dumps(payload, sort_keys=True).encode("utf-8")
        with self.assertRaisesRegex(signer.SigningError, "canonical collector"):
            self._sign(payload=payload, subject_bytes=noncanonical)

    def test_receipt_tampering_breaks_signature(self) -> None:
        receipt = self._sign()
        receipt["evidence"]["deployment"]["status"] = "failed"
        context = acceptance.ValidationContext(
            repo_root=ROOT,
            evidence_root=ROOT,
            verification_time=NOW,
            generated_at=NOW,
            expected_master_head=collector_test.MASTER_SHA,
            expected_deploy_id=collector_test.DEPLOY_ID,
            repository_commit=collector_test.MASTER_SHA,
            live=False,
            trusted_issuers=self._trusted(),
            registry_sha256="0" * 64,
        )
        acceptance._validate_receipt(
            receipt,
            gate="root_ci_protected_deploy",
            issuer_name=signer.ISSUER,
            key_id=signer.KEY_ID,
            context=context,
            path="$.receipt",
        )
        self.assertTrue(
            any("signature verification failed" in error for error in context.errors)
        )

    def test_key_parse_failure_never_echoes_key_material(self) -> None:
        key_material = "-----BEGIN PRIVATE KEY-----\nprivate-secret-value\n-----END PRIVATE KEY-----"
        with self.assertRaises(signer.SigningError) as exc_info:
            self._sign(private_key_pem=key_material)
        self.assertNotIn("private-secret-value", str(exc_info.exception))


if __name__ == "__main__":
    unittest.main()
