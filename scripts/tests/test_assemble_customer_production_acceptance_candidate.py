from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
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

import assemble_customer_production_acceptance_candidate as assembler
import test_verify_customer_production_acceptance as verifier_test
import verify_customer_production_acceptance as acceptance


NOW = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
MASTER_SHA = "d" * 40
DEPLOY_ID = "dep-candidatehostile001"
RECEIPT_HASH = hashlib.sha256(b"root receipt").hexdigest()


def _authority_document(
    gate: str,
    *,
    master_head: str = MASTER_SHA,
    deploy_id: str = DEPLOY_ID,
    event: datetime | None = None,
    observed: datetime | None = None,
) -> bytes:
    uri = assembler._exact_live_endpoint(gate)
    event = event or (NOW - timedelta(minutes=10))
    observed = observed or (NOW - timedelta(minutes=5))
    document = {
        "schema_version": acceptance.EVIDENCE_SCHEMA_VERSION,
        "gate": gate,
        "environment": "public-production",
        "repository": acceptance.REPOSITORY,
        "master_head_sha": master_head,
        "deploy_id": deploy_id,
        "event_at_utc": assembler._utc_seconds(event),
        "observed_at_utc": assembler._utc_seconds(observed),
        "artifact_uri": uri,
        "artifact_sha256": hashlib.sha256(f"artifact:{gate}".encode()).hexdigest(),
    }
    return json.dumps(document, sort_keys=True).encode("utf-8")


def _receipt_document(**overrides) -> dict:
    issued = NOW - timedelta(minutes=20)
    expires = issued + timedelta(minutes=acceptance.ROOT_CI_RECEIPT_TTL_MINUTES)
    subject_uri = (
        f"{acceptance.REPOSITORY_URL}/releases/download/"
        "customer-production-evidence/root-ci-protected-deploy.json"
    )
    subject_hash = hashlib.sha256(b"subject").hexdigest()
    document = {
        "schema_version": acceptance.RECEIPT_SCHEMA_VERSION,
        "issuer": "github-customer-production",
        "key_id": "gh-env-2026-07-14-01",
        "gate": assembler.ROOT_CI_GATE,
        "environment": "public-production",
        "repository": acceptance.REPOSITORY,
        "master_head_sha": MASTER_SHA,
        "deploy_id": DEPLOY_ID,
        "issued_at_utc": assembler._utc_seconds(issued),
        "expires_at_utc": assembler._utc_seconds(expires),
        "subject_uri": subject_uri,
        "subject_sha256": subject_hash,
        "evidence": {
            "root_ci_schema_version": acceptance.ROOT_CI_SCHEMA_VERSION,
            "master_head_sha": MASTER_SHA,
            "deploy_id": DEPLOY_ID,
            "artifact_uri": subject_uri,
            "artifact_sha256": subject_hash,
        },
        "signature_base64url": "test-only-placeholder",
    }
    document.update(overrides)
    return document


class CandidateAssemblerTests(unittest.TestCase):
    def test_exact_live_authority_set_has_eight_gates_plus_release(self) -> None:
        self.assertEqual(len(assembler.LIVE_GATES), 8)
        self.assertEqual(len(assembler.LIVE_AUTHORITIES), 9)
        self.assertNotIn(assembler.ROOT_CI_GATE, assembler.LIVE_AUTHORITIES)
        self.assertEqual(assembler.LIVE_AUTHORITIES[-1], "release_decision")
        for gate in assembler.LIVE_AUTHORITIES:
            uri = assembler._exact_live_endpoint(gate)
            self.assertEqual(
                uri,
                acceptance.LIVE_AUTHORITY_ENDPOINTS[gate][assembler.LIVE_ISSUER],
            )

    def test_collect_hashes_exact_authority_bytes(self) -> None:
        raw_by_gate = {
            gate: _authority_document(gate) for gate in assembler.LIVE_AUTHORITIES
        }

        def fetch(gate: str, uri: str) -> bytes:
            self.assertEqual(uri, assembler._exact_live_endpoint(gate))
            return raw_by_gate[gate]

        collected = assembler._collect_live_authorities(
            expected_master_head=MASTER_SHA,
            expected_deploy_id=DEPLOY_ID,
            verification_time=NOW,
            fetcher=fetch,
        )
        self.assertEqual(set(collected), set(assembler.LIVE_AUTHORITIES))
        for gate, authority in collected.items():
            self.assertEqual(authority.raw, raw_by_gate[gate])
            self.assertEqual(authority.sha256, hashlib.sha256(raw_by_gate[gate]).hexdigest())

    def test_non_200_live_authority_fails_without_body_disclosure(self) -> None:
        error = acceptance.ManifestLoadError(
            "live evidence returned HTTP 503; response body suppressed"
        )
        with patch.object(acceptance, "_fetch_https", side_effect=error):
            with self.assertRaisesRegex(
                assembler.AssemblyError, "HTTP 503; response body suppressed"
            ):
                assembler._fetch_live_authority(
                    "runtime_worm",
                    assembler._exact_live_endpoint("runtime_worm"),
                )

    def test_stale_live_authority_fails_before_manifest_assembly(self) -> None:
        raw = _authority_document(
            "runtime_worm",
            event=NOW - timedelta(minutes=31),
            observed=NOW - timedelta(minutes=1),
        )
        document = assembler._strict_document(raw, "stale runtime authority")
        with self.assertRaisesRegex(assembler.AssemblyError, "event is stale"):
            assembler._require_exact_identity(
                document,
                gate="runtime_worm",
                uri=assembler._exact_live_endpoint("runtime_worm"),
                expected_master_head=MASTER_SHA,
                expected_deploy_id=DEPLOY_ID,
                verification_time=NOW,
            )

    def test_live_master_and_deploy_mismatches_fail_closed(self) -> None:
        wrong_master = assembler._strict_document(
            _authority_document("accounts_billing", master_head="e" * 40),
            "wrong master",
        )
        with self.assertRaisesRegex(assembler.AssemblyError, "master_head_sha"):
            assembler._require_exact_identity(
                wrong_master,
                gate="accounts_billing",
                uri=assembler._exact_live_endpoint("accounts_billing"),
                expected_master_head=MASTER_SHA,
                expected_deploy_id=DEPLOY_ID,
                verification_time=NOW,
            )

        wrong_deploy = assembler._strict_document(
            _authority_document("accounts_billing", deploy_id="dep-wrong"),
            "wrong deploy",
        )
        with self.assertRaisesRegex(assembler.AssemblyError, "deploy_id"):
            assembler._require_exact_identity(
                wrong_deploy,
                gate="accounts_billing",
                uri=assembler._exact_live_endpoint("accounts_billing"),
                expected_master_head=MASTER_SHA,
                expected_deploy_id=DEPLOY_ID,
                verification_time=NOW,
            )

    def test_receipt_identity_and_expiry_mismatches_fail_closed(self) -> None:
        wrong_deploy = _receipt_document(deploy_id="dep-wrong")
        with self.assertRaisesRegex(assembler.AssemblyError, "deploy_id"):
            assembler._preflight_receipt_identity(
                wrong_deploy,
                expected_master_head=MASTER_SHA,
                expected_deploy_id=DEPLOY_ID,
                verification_time=NOW,
            )

        expired = _receipt_document(
            expires_at_utc=assembler._utc_seconds(NOW - timedelta(seconds=1))
        )
        with self.assertRaisesRegex(assembler.AssemblyError, "expired"):
            assembler._preflight_receipt_identity(
                expired,
                expected_master_head=MASTER_SHA,
                expected_deploy_id=DEPLOY_ID,
                verification_time=NOW,
            )

        wrong_ttl = _receipt_document(
            expires_at_utc=assembler._utc_seconds(NOW + timedelta(minutes=101))
        )
        with self.assertRaisesRegex(assembler.AssemblyError, "exactly 120 minutes"):
            assembler._preflight_receipt_identity(
                wrong_ttl,
                expected_master_head=MASTER_SHA,
                expected_deploy_id=DEPLOY_ID,
                verification_time=NOW,
            )

        wrong_schema = _receipt_document()
        wrong_schema["evidence"]["root_ci_schema_version"] = "legacy-root-ci"
        with self.assertRaisesRegex(assembler.AssemblyError, "schema marker"):
            assembler._preflight_receipt_identity(
                wrong_schema,
                expected_master_head=MASTER_SHA,
                expected_deploy_id=DEPLOY_ID,
                verification_time=NOW,
            )

    def test_external_receipt_hash_pin_is_checked_before_signature(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "receipt.json"
            path.write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(assembler.AssemblyError, "external SHA-256 pin"):
                assembler._load_pinned_root_receipt(
                    receipt_path=path,
                    expected_receipt_sha256="0" * 64,
                    expected_master_head=MASTER_SHA,
                    expected_deploy_id=DEPLOY_ID,
                    verification_time=NOW,
                    repo_root=ROOT,
                )

    def test_pinned_receipt_signature_and_complete_root_gate_are_reverified(self) -> None:
        bundle = verifier_test.SignedBundle()
        try:
            payload = verifier_test._gate_payloads()[assembler.ROOT_CI_GATE]
            reference = bundle.receipt(assembler.ROOT_CI_GATE, payload)
            receipt_path = bundle.root / reference["uri"].removeprefix("repo://")
            with patch.object(
                assembler.acceptance,
                "_load_trusted_issuer_registry",
                return_value=(bundle.trusted_issuers, "f" * 64),
            ):
                pinned = assembler._load_pinned_root_receipt(
                    receipt_path=receipt_path,
                    expected_receipt_sha256=reference["sha256"],
                    expected_master_head=verifier_test.MASTER_SHA,
                    expected_deploy_id=verifier_test.DEPLOY_ID,
                    verification_time=verifier_test.NOW,
                    repo_root=ROOT,
                )
            self.assertEqual(pinned.sha256, reference["sha256"])
            self.assertEqual(pinned.issuer, verifier_test.TEST_ISSUER)

            tampered = json.loads(receipt_path.read_text(encoding="utf-8"))
            tampered["evidence"]["misplaced_workflow_count"] = 1
            tampered_raw = json.dumps(tampered, sort_keys=True).encode("utf-8")
            receipt_path.write_bytes(tampered_raw)
            with patch.object(
                assembler.acceptance,
                "_load_trusted_issuer_registry",
                return_value=(bundle.trusted_issuers, "f" * 64),
            ):
                with self.assertRaisesRegex(
                    assembler.AssemblyError, "authoritative validation"
                ):
                    assembler._load_pinned_root_receipt(
                        receipt_path=receipt_path,
                        expected_receipt_sha256=hashlib.sha256(tampered_raw).hexdigest(),
                        expected_master_head=verifier_test.MASTER_SHA,
                        expected_deploy_id=verifier_test.DEPLOY_ID,
                        verification_time=verifier_test.NOW,
                        repo_root=ROOT,
                    )
        finally:
            bundle.close()

    def test_candidate_manifest_uses_signed_root_and_only_exact_live_references(self) -> None:
        template = assembler._load_open_template(ROOT)
        receipt = assembler.PinnedReceipt(
            raw=b"root receipt",
            sha256=RECEIPT_HASH,
            issuer="github-customer-production",
            key_id="gh-env-2026-07-14-01",
        )
        authorities = {
            gate: assembler.LiveAuthority(
                gate=gate,
                uri=assembler._exact_live_endpoint(gate),
                raw=_authority_document(gate),
                sha256=hashlib.sha256(_authority_document(gate)).hexdigest(),
            )
            for gate in assembler.LIVE_AUTHORITIES
        }
        manifest = assembler._build_candidate_manifest(
            template=template,
            generated_at=NOW,
            receipt=receipt,
            authorities=authorities,
        )
        self.assertEqual(manifest["product"]["status"], "ACCEPT")
        self.assertEqual(
            set(manifest["required_gates"]), set(acceptance.REQUIRED_GATES)
        )
        root = manifest["required_gates"][assembler.ROOT_CI_GATE]["evidence"]
        self.assertEqual(root["sha256"], RECEIPT_HASH)
        self.assertEqual(root["authority"]["mode"], "signed_receipt")
        for gate in assembler.LIVE_GATES:
            reference = manifest["required_gates"][gate]["evidence"]
            self.assertEqual(reference["uri"], assembler._exact_live_endpoint(gate))
            self.assertEqual(reference["authority"]["mode"], "live_https")
        release = manifest["product"]["release_decision"]["evidence"]
        self.assertEqual(
            release["uri"], assembler._exact_live_endpoint("release_decision")
        )

    def test_built_candidate_passes_existing_verifier_with_live_authorities(self) -> None:
        bundle = verifier_test.SignedBundle()
        try:
            source_manifest = verifier_test._accepting_manifest(bundle)
            root_reference = source_manifest["required_gates"][
                assembler.ROOT_CI_GATE
            ]["evidence"]
            root_source = bundle.root / root_reference["uri"].removeprefix(
                "repo://"
            )
            root_raw = root_source.read_bytes()
            root_target = bundle.root / "receipts/root-ci-protected-deploy.json"
            root_target.parent.mkdir(parents=True)
            root_target.write_bytes(root_raw)
            receipt = assembler.PinnedReceipt(
                raw=root_raw,
                sha256=root_reference["sha256"],
                issuer=verifier_test.TEST_ISSUER,
                key_id=verifier_test.TEST_KEY_ID,
            )

            live_documents: dict[str, bytes] = {}
            authorities: dict[str, assembler.LiveAuthority] = {}
            for gate in assembler.LIVE_AUTHORITIES:
                if gate == "release_decision":
                    reference = source_manifest["product"]["release_decision"][
                        "evidence"
                    ]
                else:
                    reference = source_manifest["required_gates"][gate]["evidence"]
                receipt_path = bundle.root / reference["uri"].removeprefix("repo://")
                evidence = json.loads(receipt_path.read_text(encoding="utf-8"))[
                    "evidence"
                ]
                raw = (
                    json.dumps(evidence, indent=2, sort_keys=True).encode("utf-8")
                    + b"\n"
                )
                uri = assembler._exact_live_endpoint(gate)
                live_documents[uri] = raw
                authorities[gate] = assembler.LiveAuthority(
                    gate=gate,
                    uri=uri,
                    raw=raw,
                    sha256=hashlib.sha256(raw).hexdigest(),
                )

            candidate = assembler._build_candidate_manifest(
                template=assembler._load_open_template(ROOT),
                generated_at=verifier_test.NOW,
                receipt=receipt,
                authorities=authorities,
            )

            def fetch(uri: str, _allowed_origins) -> bytes:
                return live_documents[uri]

            with patch.object(acceptance, "_fetch_https", side_effect=fetch):
                report = acceptance.verify_manifest(
                    candidate,
                    repo_root=ROOT,
                    evidence_root=bundle.root,
                    verification_time=verifier_test.NOW,
                    expected_master_head=verifier_test.MASTER_SHA,
                    expected_deploy_id=verifier_test.DEPLOY_ID,
                    repository_commit=verifier_test.MASTER_SHA,
                    live=True,
                    trusted_issuers=bundle.trusted_issuers,
                    registry_sha256="f" * 64,
                )
            self.assertEqual(report["result"], "ACCEPT", report["errors"])
            self.assertTrue(report["accepted"])
            self.assertEqual(
                set(report["authorities"]), set(acceptance.AUTHORITY_GATES)
            )
        finally:
            bundle.close()

    def test_live_verifier_sha_rejection_is_terminal_and_uses_live_mode(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "candidate"
            manifest = root / "manifest.json"
            manifest.write_text("{}\n", encoding="utf-8")

            def rejected(command, **kwargs):
                self.assertIn("--live", command)
                self.assertNotIn("--validate-only", command)
                report_path = Path(command[command.index("--report-path") + 1])
                report_path.parent.mkdir(parents=True, exist_ok=True)
                report_path.write_text(
                    json.dumps(
                        {
                            "result": "INVALID",
                            "accepted": False,
                            "errors": ["live evidence sha256 does not match"],
                        }
                    ),
                    encoding="utf-8",
                )
                return subprocess.CompletedProcess(command, 1, "", "")

            with patch.object(assembler.subprocess, "run", side_effect=rejected):
                with self.assertRaisesRegex(
                    assembler.AssemblyError,
                    "live evidence sha256 does not match",
                ):
                    assembler._run_verifier(
                        repo_root=ROOT,
                        manifest_path=manifest,
                        evidence_root=root,
                        output_dir=output,
                        expected_master_head=MASTER_SHA,
                        expected_deploy_id=DEPLOY_ID,
                    )

    def test_partial_candidate_is_removed_after_verifier_rejection(self) -> None:
        receipt = assembler.PinnedReceipt(
            raw=b"root receipt",
            sha256=RECEIPT_HASH,
            issuer="github-customer-production",
            key_id="gh-env-2026-07-14-01",
        )
        authorities = {
            gate: assembler.LiveAuthority(
                gate=gate,
                uri=assembler._exact_live_endpoint(gate),
                raw=_authority_document(gate),
                sha256=hashlib.sha256(_authority_document(gate)).hexdigest(),
            )
            for gate in assembler.LIVE_AUTHORITIES
        }

        def reject_after_partial_output(**kwargs):
            output = kwargs["output_dir"]
            output.mkdir(parents=True)
            (output / "unverified-partial.json").write_text("{}", encoding="utf-8")
            raise assembler.AssemblyError("live response SHA changed")

        with tempfile.TemporaryDirectory() as directory, patch.object(
            assembler.acceptance,
            "_repository_commit",
            return_value=MASTER_SHA,
        ), patch.object(
            assembler,
            "_load_pinned_root_receipt",
            return_value=receipt,
        ), patch.object(
            assembler,
            "_collect_live_authorities",
            return_value=authorities,
        ), patch.object(
            assembler,
            "_run_verifier",
            side_effect=reject_after_partial_output,
        ):
            output = Path(directory) / "candidate"
            with self.assertRaisesRegex(assembler.AssemblyError, "SHA changed"):
                assembler.assemble_candidate(
                    repo_root=ROOT,
                    receipt_path=Path(directory) / "receipt.json",
                    receipt_sha256=RECEIPT_HASH,
                    expected_master_head=MASTER_SHA,
                    expected_deploy_id=DEPLOY_ID,
                    output_dir=output,
                    now=NOW,
                )
            self.assertFalse(output.exists())

    def test_output_must_be_ephemeral_and_outside_repository(self) -> None:
        self.assertFalse(assembler._outside_repository(ROOT / ".candidate", ROOT))
        with tempfile.TemporaryDirectory() as directory:
            self.assertTrue(
                assembler._outside_repository(Path(directory) / "candidate", ROOT)
            )

    def test_wrong_checked_out_commit_fails_before_receipt_or_network(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "candidate"
            with patch.object(
                assembler.acceptance,
                "_repository_commit",
                return_value="e" * 40,
            ), patch.object(
                assembler,
                "_load_pinned_root_receipt",
            ) as receipt_loader, patch.object(
                assembler,
                "_collect_live_authorities",
            ) as collector:
                with self.assertRaisesRegex(
                    assembler.AssemblyError, "checked-out repository commit"
                ):
                    assembler.assemble_candidate(
                        repo_root=ROOT,
                        receipt_path=Path(directory) / "receipt.json",
                        receipt_sha256="0" * 64,
                        expected_master_head=MASTER_SHA,
                        expected_deploy_id=DEPLOY_ID,
                        output_dir=output,
                        now=NOW,
                    )
                receipt_loader.assert_not_called()
                collector.assert_not_called()
                self.assertFalse(output.exists())

    def test_candidate_workflow_cannot_publish_or_dispatch_final_accept(self) -> None:
        workflow = (ROOT / ".github/workflows/customer-production-candidate.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("assemble_customer_production_acceptance_candidate.py", workflow)
        self.assertIn("root_ci_receipt_sha256:", workflow)
        self.assertIn("actions/upload-artifact@", workflow)
        self.assertNotIn("publish_customer_production_acceptance_authority", workflow)
        self.assertNotIn("gh workflow run", workflow)
        self.assertNotIn("repository_dispatch", workflow)
        self.assertNotIn("CUSTOMER_PRODUCTION_SIGNING_KEY_PEM", workflow)

        source = (
            ROOT / "scripts/assemble_customer_production_acceptance_candidate.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("publish_customer_production_acceptance_authority", source)
        self.assertNotIn('method="POST"', source)
        self.assertNotIn("CUSTOMER_PRODUCTION_SIGNING_KEY_PEM", source)
        self.assertIn("acceptance._fetch_https", source)


if __name__ == "__main__":
    unittest.main()
