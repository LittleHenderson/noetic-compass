from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
TESTS = Path(__file__).resolve().parent
for path in (SCRIPTS, TESTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import test_verify_customer_production_acceptance as acceptance_test
import verify_pinned_root_ci_receipt as verifier


NOW = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)


def _write_checksum(path: Path, digest: str) -> None:
    path.write_text(
        f"{digest}  {verifier.CHECKSUM_SUBJECT}\n",
        encoding="ascii",
        newline="\n",
    )


def _pinned_with_expiry(expires: datetime) -> verifier.candidate.PinnedReceipt:
    raw = json.dumps(
        {
            "expires_at_utc": expires.astimezone(timezone.utc)
            .replace(microsecond=0)
            .strftime("%Y-%m-%dT%H:%M:%SZ")
        },
        sort_keys=True,
    ).encode("utf-8")
    return verifier.candidate.PinnedReceipt(
        raw=raw,
        sha256=hashlib.sha256(raw).hexdigest(),
        issuer="test-issuer",
        key_id="test-key",
    )


def _git(repo_root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo_root), *arguments],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _initialize_security_repo(repo_root: Path) -> str:
    _git(repo_root, "init")
    _git(repo_root, "config", "user.name", "CAS Receipt Test")
    _git(repo_root, "config", "user.email", "cas-receipt-test@example.invalid")
    _git(repo_root, "config", "core.autocrlf", "false")
    for repository_path in verifier.SECURITY_CRITICAL_REPOSITORY_PATHS:
        target = repo_root / repository_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            f"tracked test content for {repository_path}\n",
            encoding="utf-8",
            newline="\n",
        )
    _git(repo_root, "add", "--all")
    _git(repo_root, "commit", "-m", "security fixture")
    return _git(repo_root, "rev-parse", "HEAD")


class PinnedRootCiReceiptVerifierTests(unittest.TestCase):
    def test_checksum_must_name_the_exact_signed_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "root-ci-protected-deploy.sha256"
            path.write_text(
                f"{'0' * 64}  receipts/another-file.json\n",
                encoding="ascii",
            )
            with self.assertRaisesRegex(
                verifier.ReceiptVerificationError, "exact signed receipt"
            ):
                verifier._read_checksum(path)

    def test_checkout_must_match_the_expected_protected_master(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            _initialize_security_repo(repo_root)
            with self.assertRaisesRegex(
                verifier.ReceiptVerificationError, "checked-out commit"
            ):
                verifier._verify_security_critical_checkout(
                    repo_root, "e" * 40
                )

    def test_git_subprocess_sanitizes_overrides_and_disables_replacements(self) -> None:
        hostile_environment = {
            name: f"hostile-{name.lower()}"
            for name in verifier.DANGEROUS_GIT_ENVIRONMENT
        } | {
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "core.hooksPath",
            "GIT_CONFIG_VALUE_0": "/hostile/hooks",
        }
        completed = subprocess.CompletedProcess(
            args=["git"], returncode=0, stdout=b"", stderr=b""
        )
        with (
            patch.dict(os.environ, hostile_environment, clear=False),
            patch.object(verifier.subprocess, "run", return_value=completed) as run,
        ):
            verifier._git_stdout(Path("repository"), "status")
        command = run.call_args.args[0]
        environment = run.call_args.kwargs["env"]
        self.assertEqual(
            command[:4], ["git", "-c", "core.hooksPath=/dev/null", "-C"]
        )
        for name in hostile_environment:
            self.assertNotIn(name, environment)
        self.assertEqual(environment["GIT_NO_REPLACE_OBJECTS"], "1")

    def test_replacement_refs_fail_closed_before_commit_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            head = _initialize_security_repo(repo_root)
            target = next(
                repo_root / path
                for path in verifier.SECURITY_CRITICAL_REPOSITORY_PATHS
                if path.endswith("verify_pinned_root_ci_receipt.py")
            )
            target.write_text("hostile replacement\n", encoding="utf-8")
            _git(repo_root, "add", "--all")
            _git(repo_root, "commit", "-m", "hostile replacement")
            hostile_head = _git(repo_root, "rev-parse", "HEAD")
            _git(repo_root, "switch", "--detach", head)
            _git(
                repo_root,
                "update-ref",
                f"refs/replace/{head}",
                hostile_head,
            )
            with self.assertRaisesRegex(
                verifier.ReceiptVerificationError, "forbidden replacement refs"
            ):
                verifier._verify_security_critical_checkout(repo_root, head)

    def test_legacy_grafts_fail_closed_before_commit_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            head = _initialize_security_repo(repo_root)
            grafts_path = Path(
                _git(repo_root, "rev-parse", "--git-path", "info/grafts")
            )
            if not grafts_path.is_absolute():
                grafts_path = repo_root / grafts_path
            grafts_path.parent.mkdir(parents=True, exist_ok=True)
            grafts_path.write_text(f"{head}\n", encoding="ascii", newline="\n")
            with self.assertRaisesRegex(
                verifier.ReceiptVerificationError, "forbidden legacy grafts"
            ):
                verifier._verify_security_critical_checkout(repo_root, head)

    def test_artifact_checksum_must_match_the_external_pin(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            checksum = Path(directory) / "root-ci-protected-deploy.sha256"
            _write_checksum(checksum, "1" * 64)
            with patch.object(
                verifier, "_verify_security_critical_checkout", return_value=None
            ):
                with self.assertRaisesRegex(
                    verifier.ReceiptVerificationError, "external root-CI receipt pin"
                ):
                    verifier.verify_pinned_root_ci_receipt(
                        receipt_path=Path(directory) / "missing-receipt.json",
                        checksum_path=checksum,
                        expected_receipt_sha256="2" * 64,
                        expected_master_head="e" * 40,
                        expected_deploy_id="dep-currentbinding001",
                    )

    def test_checkout_is_revalidated_after_receipt_verification(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            checksum = Path(directory) / "root-ci-protected-deploy.sha256"
            pinned = _pinned_with_expiry(NOW + timedelta(hours=1))
            _write_checksum(checksum, pinned.sha256)
            changed = verifier.ReceiptVerificationError(
                "security-critical checkout changed during verification"
            )
            with (
                patch.object(
                    verifier,
                    "_verify_security_critical_checkout",
                    side_effect=[None, changed],
                ),
                patch.object(
                    verifier.candidate,
                    "_load_pinned_root_receipt",
                    return_value=pinned,
                ),
            ):
                with self.assertRaisesRegex(
                    verifier.ReceiptVerificationError, "changed during"
                ):
                    verifier.verify_pinned_root_ci_receipt(
                        receipt_path=Path(directory) / "receipt.json",
                        checksum_path=checksum,
                        expected_receipt_sha256=pinned.sha256,
                        expected_master_head="e" * 40,
                        expected_deploy_id="dep-currentbinding001",
                        verification_time=NOW,
                    )

    def test_minimum_validity_cannot_be_weakened_below_workflow_window(self) -> None:
        receipt = _pinned_with_expiry(NOW + timedelta(hours=1))
        with self.assertRaisesRegex(
            verifier.ReceiptVerificationError, "20-minute workflow window"
        ):
            verifier._require_remaining_validity(
                receipt,
                verification_time=NOW,
                minimum_remaining_seconds=verifier.WORKFLOW_WINDOW_SECONDS - 1,
            )

    def test_exact_validity_boundary_and_insufficient_margin_fail_closed(self) -> None:
        for remaining_seconds in (
            verifier.WORKFLOW_WINDOW_SECONDS,
            verifier.WORKFLOW_WINDOW_SECONDS - 1,
        ):
            with self.subTest(remaining_seconds=remaining_seconds):
                receipt = _pinned_with_expiry(
                    NOW + timedelta(seconds=remaining_seconds)
                )
                with self.assertRaisesRegex(
                    verifier.ReceiptVerificationError, "strictly more than 1200"
                ):
                    verifier._require_remaining_validity(
                        receipt,
                        verification_time=NOW,
                        minimum_remaining_seconds=verifier.WORKFLOW_WINDOW_SECONDS,
                    )

    def test_validity_margin_requires_at_least_one_second_beyond_window(self) -> None:
        receipt = _pinned_with_expiry(
            NOW + timedelta(seconds=verifier.WORKFLOW_WINDOW_SECONDS + 1)
        )
        verifier._require_remaining_validity(
            receipt,
            verification_time=NOW,
            minimum_remaining_seconds=verifier.WORKFLOW_WINDOW_SECONDS,
        )

    def test_full_verifier_rejects_the_exact_remaining_validity_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            receipt = _pinned_with_expiry(
                NOW + timedelta(seconds=verifier.WORKFLOW_WINDOW_SECONDS)
            )
            checksum = Path(directory) / "root-ci-protected-deploy.sha256"
            _write_checksum(checksum, receipt.sha256)
            with (
                patch.object(
                    verifier, "_verify_security_critical_checkout", return_value=None
                ),
                patch.object(
                    verifier.candidate,
                    "_load_pinned_root_receipt",
                    return_value=receipt,
                ),
            ):
                with self.assertRaisesRegex(
                    verifier.ReceiptVerificationError, "strictly more than 1200"
                ):
                    verifier.verify_pinned_root_ci_receipt(
                        receipt_path=Path(directory) / "receipt.json",
                        checksum_path=checksum,
                        expected_receipt_sha256=receipt.sha256,
                        expected_master_head="e" * 40,
                        expected_deploy_id="dep-currentbinding001",
                        verification_time=NOW,
                    )

    def test_clean_security_critical_checkout_is_exactly_head_bound(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            head = _initialize_security_repo(repo_root)
            verifier._verify_security_critical_checkout(repo_root, head)

    def test_dirty_registry_verifier_and_delivery_script_fail_closed(self) -> None:
        hostile_paths = (
            ".production/customer-production-trusted-issuers.json",
            "scripts/verify_pinned_root_ci_receipt.py",
            "scripts/deliver_alert_delivery_drill.py",
        )
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            head = _initialize_security_repo(repo_root)
            for repository_path in hostile_paths:
                with self.subTest(repository_path=repository_path):
                    target = repo_root / repository_path
                    target.write_text("hostile working-tree replacement\n", encoding="utf-8")
                    with self.assertRaisesRegex(
                        verifier.ReceiptVerificationError,
                        re.escape(repository_path),
                    ):
                        verifier._verify_security_critical_checkout(repo_root, head)
                    _git(repo_root, "restore", "--", repository_path)

    def test_untracked_checkout_content_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo_root = Path(directory)
            head = _initialize_security_repo(repo_root)
            (repo_root / "untracked-shadow.py").write_text(
                "hostile shadow\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(
                verifier.ReceiptVerificationError, "tracked or untracked changes"
            ):
                verifier._verify_security_critical_checkout(repo_root, head)

    def test_signature_freshness_and_complete_root_contract_are_reverified(self) -> None:
        bundle = acceptance_test.SignedBundle()
        try:
            payload = acceptance_test._gate_payloads()[verifier.candidate.ROOT_CI_GATE]
            reference = bundle.receipt(verifier.candidate.ROOT_CI_GATE, payload)
            receipt_path = bundle.root / reference["uri"].removeprefix("repo://")
            checksum_path = bundle.root / "root-ci-protected-deploy.sha256"
            _write_checksum(checksum_path, reference["sha256"])

            with (
                patch.object(
                    verifier, "_verify_security_critical_checkout", return_value=None
                ),
                patch.object(
                    verifier.candidate.acceptance,
                    "_load_trusted_issuer_registry",
                    return_value=(bundle.trusted_issuers, "f" * 64),
                ),
            ):
                pinned = verifier.verify_pinned_root_ci_receipt(
                    receipt_path=receipt_path,
                    checksum_path=checksum_path,
                    expected_receipt_sha256=reference["sha256"],
                    expected_master_head=acceptance_test.MASTER_SHA,
                    expected_deploy_id=acceptance_test.DEPLOY_ID,
                    verification_time=acceptance_test.NOW,
                )
            self.assertEqual(pinned.sha256, reference["sha256"])

            tampered = json.loads(receipt_path.read_text(encoding="utf-8"))
            signature = tampered["signature_base64url"]
            tampered["signature_base64url"] = (
                ("A" if signature[0] != "A" else "B") + signature[1:]
            )
            tampered_raw = (
                json.dumps(tampered, indent=2, sort_keys=True).encode("utf-8") + b"\n"
            )
            receipt_path.write_bytes(tampered_raw)
            tampered_hash = hashlib.sha256(tampered_raw).hexdigest()
            _write_checksum(checksum_path, tampered_hash)
            with (
                patch.object(
                    verifier, "_verify_security_critical_checkout", return_value=None
                ),
                patch.object(
                    verifier.candidate.acceptance,
                    "_load_trusted_issuer_registry",
                    return_value=(bundle.trusted_issuers, "f" * 64),
                ),
            ):
                with self.assertRaisesRegex(
                    verifier.ReceiptVerificationError, "authoritative validation"
                ):
                    verifier.verify_pinned_root_ci_receipt(
                        receipt_path=receipt_path,
                        checksum_path=checksum_path,
                        expected_receipt_sha256=tampered_hash,
                        expected_master_head=acceptance_test.MASTER_SHA,
                        expected_deploy_id=acceptance_test.DEPLOY_ID,
                        verification_time=acceptance_test.NOW,
                    )
        finally:
            bundle.close()


if __name__ == "__main__":
    unittest.main()
