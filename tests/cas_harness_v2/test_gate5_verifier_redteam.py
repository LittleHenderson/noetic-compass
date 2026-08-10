from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[2]
VERIFIER_PATH = ROOT / "scripts" / "verify_project_coherence_gate5.py"
RUNNER_PATH = ROOT / "scripts" / "run_project_coherence_gate5_pytest.py"
RUNNER_LOCK_BUILDER_PATH = (
    ROOT / "scripts" / "build_project_coherence_gate5_runner_lock.py"
)


def _load_verifier():
    spec = importlib.util.spec_from_file_location("gate5_verifier_redteam", VERIFIER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Gate 5 verifier")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class Gate5HistoricalCandidateReceiptIsolationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        # This narrow class deliberately does not verify the mutable Gate 5
        # artifact manifest, so the historical-receipt regression can run while
        # a successor manifest is being rebuilt.
        cls.verifier = _load_verifier()

    def _patched_json(self, target: Path, value: object):
        original = self.verifier.load_json

        def loader(path: Path, *, anchor: Path | None = None):
            if path == target:
                return value
            return original(path, anchor=anchor)

        return patch.object(self.verifier, "load_json", side_effect=loader)

    def test_historical_candidate_receipt_is_immutable_and_decoupled(self) -> None:
        receipt = self.verifier.load_json(self.verifier.CANDIDATE_RECEIPT_PATH)
        current_suites = copy.deepcopy(self.verifier.REQUIRED_TEST_SUITES)
        current_suites["Live trace worker complete"].update(
            expected_tests=999,
            expected_test_ids_sha256="0" * 64,
        )
        current_suites["API, fleet state, and launcher identity"].update(
            targets=["tests/future_successor_suite.py"],
            expected_tests=999,
            expected_test_ids_sha256="1" * 64,
        )
        with patch.object(self.verifier, "REQUIRED_TEST_SUITES", current_suites):
            verified = (
                self.verifier.verify_dependency_and_container_candidate_receipt()
            )
        self.assertEqual(verified["test_receipts"], receipt["test_receipts"])

        historical = (
            self.verifier.HISTORICAL_DEPENDENCY_CONTAINER_CANDIDATE_TEST_RECEIPT
        )
        with self.assertRaises(TypeError):
            historical["api_launcher_fleet_state"]["passed"] = 75
        with self.assertRaises(TypeError):
            historical["api_launcher_fleet_state"]["targets"][0] = (
                "tests/forged.py"
            )

        forged = copy.deepcopy(receipt)
        forged["test_receipts"]["api_launcher_fleet_state"][
            "test_ids_sha256"
        ] = "2" * 64
        with self._patched_json(self.verifier.CANDIDATE_RECEIPT_PATH, forged):
            with self.assertRaises(self.verifier.VerificationError):
                self.verifier.verify_dependency_and_container_candidate_receipt()


class Gate5VerifierRedTeamTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.verifier = _load_verifier()
        cls.runner = _load_module("gate5_runner_redteam", RUNNER_PATH)
        cls.runner_lock_builder = _load_module(
            "gate5_runner_lock_builder_redteam", RUNNER_LOCK_BUILDER_PATH
        )
        cls.manifest = cls.verifier.load_json(cls.verifier.MANIFEST_PATH)
        cls.artifacts = cls.verifier.verify_manifest(cls.manifest)

    def _patched_json(self, target: Path, value: object):
        original = self.verifier.load_json

        def loader(path: Path, *, anchor: Path | None = None):
            if path == target:
                return value
            return original(path, anchor=anchor)

        return patch.object(self.verifier, "load_json", side_effect=loader)

    def test_manifest_rejects_extra_top_level_status(self) -> None:
        forged = copy.deepcopy(self.manifest)
        forged["gate5_closed"] = True
        with self.assertRaises(self.verifier.VerificationError):
            self.verifier.verify_manifest(forged)

    def test_manifest_rejects_count_role_and_boundary_drift(self) -> None:
        forged_count = copy.deepcopy(self.manifest)
        forged_count["artifact_count"] += 1
        with self.assertRaises(self.verifier.VerificationError):
            self.verifier.verify_manifest(forged_count)

        forged_role = copy.deepcopy(self.manifest)
        forged_role["artifacts"][0]["role"] = "independently_accepted"
        with self.assertRaises(self.verifier.VerificationError):
            self.verifier.verify_manifest(forged_role)

        forged_boundary = copy.deepcopy(self.manifest)
        forged_boundary["required_open_boundaries"][0] += " CLOSED"
        with self.assertRaises(self.verifier.VerificationError):
            self.verifier.verify_manifest(forged_boundary)

        surface = self.verifier.collect_api_runtime_surface()
        required = {
            "noetic-compass-scaffold/noetic-compass/api/config.py",
            "noetic-compass-scaffold/noetic-compass/api/middleware/auth.py",
            "noetic-compass-scaffold/noetic-compass/api/services/cas_harness_distributed_audits.py",
            "noetic-compass-scaffold/noetic-compass/api/services/cas_harness_model_provenance.py",
            "noetic-compass-scaffold/noetic-compass/api/services/cas_harness_scale_planner.py",
            "noetic-compass-scaffold/noetic-compass/api/services/production/state_substrate/sqlite_store.py",
            "noetic-compass-scaffold/noetic-compass/api/resources/tks_owner_locked_definitions_20260603.json",
            "noetic-compass-scaffold/noetic-compass/api/state_ledger_bootstrap.py",
        }
        self.assertTrue(required <= surface)
        self.assertGreaterEqual(len(surface), 193)

        artifact_paths = {record["path"] for record in self.manifest["artifacts"]}
        self.assertTrue(surface <= artifact_paths)
        self.assertIn(
            "noetic-compass-scaffold/noetic-compass/tests/conftest.py",
            artifact_paths,
        )
        self.assertIn(
            "noetic-compass-scaffold/noetic-compass/tests/__init__.py",
            artifact_paths,
        )

        omitted = next(iter(required))
        forged = copy.deepcopy(self.manifest)
        forged["artifacts"] = [
            record for record in forged["artifacts"] if record["path"] != omitted
        ]
        forged["artifact_count"] -= 1
        with self.assertRaises(self.verifier.VerificationError):
            self.verifier.verify_manifest(forged)

        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_root = Path(temporary_directory)
            admitted = temporary_root / "admitted"
            cache = admitted / "__pycache__"
            cache.mkdir(parents=True)
            (cache / "unbound.cpython-314.pyc").write_bytes(b"not admitted")
            with (
                patch.object(self.verifier, "ROOT", temporary_root),
                patch.object(
                    self.verifier,
                    "EXECUTABLE_SHADOW_SCAN_DIRS",
                    ("admitted",),
                ),
            ):
                with self.assertRaises(self.verifier.VerificationError):
                    self.verifier.verify_no_executable_shadow_artifacts()

    def test_manifest_rejects_float_governance_and_suite_counts(self) -> None:
        forged_ring = copy.deepcopy(self.manifest)
        forged_ring["admission_ring"] = 4.0
        with self.assertRaises(self.verifier.VerificationError):
            self.verifier.verify_manifest(forged_ring)

        forged_suite = copy.deepcopy(self.manifest)
        forged_suite["test_suites"][0]["expected_subtests"] = 60.0
        with patch.object(
            self.verifier,
            "run_pytest_same_process_receipt",
            side_effect=AssertionError("same-run execution must not start"),
        ):
            with self.assertRaises(self.verifier.VerificationError):
                self.verifier.verify_test_suites(forged_suite, {})

    def test_stable_observer_rejects_hardlink_and_symlink_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "source.json"
            source.write_bytes(b"{}\n")
            alias = root / "alias.json"
            os.link(source, alias)
            with self.assertRaisesRegex(
                self.verifier.VerificationError, "st_nlink|aliases"
            ):
                self.verifier.observe_regular_file(source, anchor=root)

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "source.json"
            source.write_bytes(b"{}\n")
            alias = root / "alias.json"
            try:
                alias.symlink_to(source)
            except OSError as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")
            with self.assertRaisesRegex(
                self.verifier.VerificationError, "symlink|reparse"
            ):
                self.verifier.observe_regular_file(alias, anchor=root)

    def test_stable_observer_detects_same_byte_inode_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            container = root / "container"
            container.mkdir()
            target = container / "artifact.json"
            target.write_bytes(b"same bytes\n")
            before = self.verifier.observe_regular_file(target, anchor=root)

            root_stat = root.stat()
            os.utime(
                root,
                ns=(root_stat.st_atime_ns, root_stat.st_mtime_ns + 1_000_000_000),
            )
            metadata_only = self.verifier.observe_regular_file(target, anchor=root)
            self.assertEqual(before, metadata_only)

            replacement = container / "replacement.json"
            replacement.write_bytes(b"same bytes\n")
            os.replace(replacement, target)
            after = self.verifier.observe_regular_file(target, anchor=root)
            self.assertEqual(before.sha256, after.sha256)
            self.assertEqual(before.byte_count, after.byte_count)
            self.assertNotEqual(before.identity, after.identity)

            ancestor_target = container / "ancestor-bound.json"
            ancestor_target.write_bytes(b"ancestor bytes\n")
            ancestor_before = self.verifier.observe_regular_file(
                ancestor_target, anchor=root
            )
            moved_container = root / "moved-container"
            os.replace(container, moved_container)
            container.mkdir()
            ancestor_target = container / "ancestor-bound.json"
            ancestor_target.write_bytes(b"ancestor bytes\n")
            ancestor_after = self.verifier.observe_regular_file(
                ancestor_target, anchor=root
            )
            self.assertEqual(ancestor_before.sha256, ancestor_after.sha256)
            self.assertNotEqual(
                ancestor_before.component_identities,
                ancestor_after.component_identities,
            )

    def test_stable_observer_rejects_synthetic_reparse_attribute(self) -> None:
        identity = self.verifier.PathIdentity(
            device=1,
            inode=2,
            mode_type=0,
            link_count=1,
            byte_count=0,
            mtime_ns=0,
            ctime_ns=0,
            file_attributes=0x400,
            reparse_tag=0,
        )
        self.assertTrue(self.verifier._is_reparse(identity))

    def test_test_id_digest_rejects_duplicate_or_noncanonical_ids(self) -> None:
        for values in (
            ["test_a.py::test_one", "test_a.py::test_one"],
            ["test_a.py::test_one\nforged"],
            ["tests\\test_a.py::test_one"],
        ):
            with self.assertRaises(self.verifier.VerificationError):
                self.verifier.test_id_digest(values)

    def test_review_matrix_rejects_contradictory_extra_status(self) -> None:
        matrix = self.verifier.load_json(self.verifier.REVIEW_MATRIX_PATH)
        forged = copy.deepcopy(matrix)
        forged["gate5_closed"] = True
        forged["status"] = "ACCEPT"
        forged["live_execution_authorized"] = True
        forged["criteria"][0]["status_override"] = "ACCEPT"
        with self._patched_json(self.verifier.REVIEW_MATRIX_PATH, forged):
            with self.assertRaises(self.verifier.VerificationError):
                self.verifier.verify_review_matrix(self.artifacts)

        forged_external = copy.deepcopy(matrix)
        forged_external["receipts"]["successor_dependency_container_candidate"][
            "repository_replayable"
        ] = True
        with self._patched_json(self.verifier.REVIEW_MATRIX_PATH, forged_external):
            with self.assertRaises(self.verifier.VerificationError):
                self.verifier.verify_review_matrix(self.artifacts)

    def test_model_binding_rejects_extra_status_and_float_bytes(self) -> None:
        binding = self.verifier.load_json(
            self.verifier.MODEL_DEPENDENCY_BINDING_PATH
        )
        forged_extra = copy.deepcopy(binding)
        forged_extra["gate5_closed"] = True
        forged_extra["live_execution_authorized"] = True
        with self._patched_json(
            self.verifier.MODEL_DEPENDENCY_BINDING_PATH, forged_extra
        ):
            with self.assertRaises(self.verifier.VerificationError):
                self.verifier.verify_model_and_security_bindings()

        forged_float = copy.deepcopy(binding)
        forged_float["model_binding"]["weights_bytes"] = 374_998_696.0
        with self._patched_json(
            self.verifier.MODEL_DEPENDENCY_BINDING_PATH, forged_float
        ):
            with self.assertRaises(self.verifier.VerificationError):
                self.verifier.verify_model_and_security_bindings()

    def test_candidate_receipt_rejects_forged_scan_pass(self) -> None:
        receipt = self.verifier.load_json(self.verifier.CANDIDATE_RECEIPT_PATH)
        forged_sbom = copy.deepcopy(receipt)
        sbom_scan = forged_sbom["security_audits"]["sbom_full_image_package_scan"]
        sbom_scan["status"] = "PASS"
        sbom_scan["passed"] = True
        sbom_scan["vulnerable_package_count"] = 0
        sbom_scan["vulnerability_count"] = 0
        sbom_scan["severity_counts"] = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
        }
        sbom_scan["findings"] = []
        with self._patched_json(self.verifier.CANDIDATE_RECEIPT_PATH, forged_sbom):
            with self.assertRaises(self.verifier.VerificationError):
                self.verifier.verify_dependency_and_container_candidate_receipt()

        forged_direct = copy.deepcopy(receipt)
        direct_scan = forged_direct["security_audits"]["full_filesystem_image_scan"]
        direct_scan["status"] = "PASS"
        direct_scan["completed"] = True
        direct_scan["passed"] = True
        direct_scan["finding_count"] = 0
        with self._patched_json(self.verifier.CANDIDATE_RECEIPT_PATH, forged_direct):
            with self.assertRaises(self.verifier.VerificationError):
                self.verifier.verify_dependency_and_container_candidate_receipt()

        forged_retention = copy.deepcopy(receipt)
        forged_retention["external_evidence_retention"]["repository_replayable"] = True
        with self._patched_json(
            self.verifier.CANDIDATE_RECEIPT_PATH, forged_retention
        ):
            with self.assertRaises(self.verifier.VerificationError):
                self.verifier.verify_dependency_and_container_candidate_receipt()

    def test_candidate_receipt_rejects_live_authority_or_acceptance(self) -> None:
        receipt = self.verifier.load_json(self.verifier.CANDIDATE_RECEIPT_PATH)
        for field in ("live_execution_authorized", "candidate_accepted"):
            forged = copy.deepcopy(receipt)
            forged[field] = True
            with self.subTest(field=field):
                with self._patched_json(self.verifier.CANDIDATE_RECEIPT_PATH, forged):
                    with self.assertRaises(self.verifier.VerificationError):
                        self.verifier.verify_dependency_and_container_candidate_receipt()

    def test_raw_evidence_receipt_rejects_security_promotion(self) -> None:
        receipt = self.verifier.load_json(
            self.verifier.RAW_BUILD_SECURITY_RECEIPT_PATH
        )
        forged = copy.deepcopy(receipt)
        forged["security_disposition"] = "PASS"
        forged["live_execution_authorized"] = True
        forged["current_vendor_triage"]["scanner_vendor_conflict_count"] = 0
        with self._patched_json(
            self.verifier.RAW_BUILD_SECURITY_RECEIPT_PATH, forged
        ):
            with self.assertRaises(self.verifier.VerificationError):
                self.verifier.verify_raw_build_and_security_evidence_receipt()

        forged_closure = copy.deepcopy(receipt)
        forged_closure["original_oci_and_attestation_closure"][
            "independent_signature_or_trust_root"
        ] = True
        with self._patched_json(
            self.verifier.RAW_BUILD_SECURITY_RECEIPT_PATH, forged_closure
        ):
            with self.assertRaises(self.verifier.VerificationError):
                self.verifier.verify_raw_build_and_security_evidence_receipt()

        forged_bundle = copy.deepcopy(receipt)
        forged_bundle["buildkit_history_bundle"]["trust_boundary"] = (
            "INDEPENDENTLY ATTESTED / PASS"
        )
        with self._patched_json(
            self.verifier.RAW_BUILD_SECURITY_RECEIPT_PATH, forged_bundle
        ):
            with self.assertRaises(self.verifier.VerificationError):
                self.verifier.verify_raw_build_and_security_evidence_receipt()

        forged_sarif_boundary = copy.deepcopy(receipt)
        forged_sarif_boundary["unresolved_boundaries"][
            "sarif_to_candidate_execution_binding"
        ] = "PASS"
        with self._patched_json(
            self.verifier.RAW_BUILD_SECURITY_RECEIPT_PATH, forged_sarif_boundary
        ):
            with self.assertRaises(self.verifier.VerificationError):
                self.verifier.verify_raw_build_and_security_evidence_receipt()

        forged_nested_status = copy.deepcopy(receipt)
        forged_nested_status["direct_local_image_reports"]["security_pass"] = True
        with self._patched_json(
            self.verifier.RAW_BUILD_SECURITY_RECEIPT_PATH, forged_nested_status
        ):
            with self.assertRaises(self.verifier.VerificationError):
                self.verifier.verify_raw_build_and_security_evidence_receipt()

        direct_spdx = self.verifier.load_json(
            self.verifier.RAW_EVIDENCE_DIR
            / "atlas-live-trace-worker_gate5-candidate-v0.2.scout.spdx.json"
        )
        forged_spdx = copy.deepcopy(direct_spdx)
        root_package = next(
            package
            for package in forged_spdx["packages"]
            if package["SPDXID"] == "SPDXRef-DocumentRoot"
        )
        root_package["externalRefs"][0]["referenceLocator"] = (
            "pkg:oci/atlas-live-trace-worker@sha256:" + "0" * 64
        )
        direct_spdx_path = (
            self.verifier.RAW_EVIDENCE_DIR
            / "atlas-live-trace-worker_gate5-candidate-v0.2.scout.spdx.json"
        )
        with self._patched_json(direct_spdx_path, forged_spdx):
            with self.assertRaises(self.verifier.VerificationError):
                self.verifier.verify_raw_build_and_security_evidence_receipt()

    def test_raw_evidence_receipt_preserves_vendor_scanner_conflict(self) -> None:
        receipt = self.verifier.load_json(
            self.verifier.RAW_BUILD_SECURITY_RECEIPT_PATH
        )
        forged = copy.deepcopy(receipt)
        dpkg = next(
            assessment
            for assessment in forged["current_vendor_triage"]["assessments"]
            if assessment["advisory"] == "CVE-2026-2219"
        )
        dpkg["ubuntu_status"] = "Vulnerable"
        dpkg["disposition"] = "OPEN / VENDOR CONFIRMS VULNERABLE"
        with self._patched_json(
            self.verifier.RAW_BUILD_SECURITY_RECEIPT_PATH, forged
        ):
            with self.assertRaises(self.verifier.VerificationError):
                self.verifier.verify_raw_build_and_security_evidence_receipt()

        forged_other = copy.deepcopy(receipt)
        libgcrypt = next(
            assessment
            for assessment in forged_other["current_vendor_triage"]["assessments"]
            if assessment["advisory"] == "CVE-2024-2236"
        )
        libgcrypt["package"] = "different-package"
        libgcrypt["ubuntu_status"] = "Fixed"
        with self._patched_json(
            self.verifier.RAW_BUILD_SECURITY_RECEIPT_PATH, forged_other
        ):
            with self.assertRaises(self.verifier.VerificationError):
                self.verifier.verify_raw_build_and_security_evidence_receipt()

    def test_candidate_receipt_rejects_source_or_oci_digest_drift(self) -> None:
        receipt = self.verifier.load_json(self.verifier.CANDIDATE_RECEIPT_PATH)
        for field, value in (
            ("source_commit", "0" * 40),
            ("oci_image_index_digest", "sha256:" + "0" * 64),
            ("platform_manifest_digest", "sha256:" + "1" * 64),
        ):
            forged = copy.deepcopy(receipt)
            forged["candidate_identity"][field] = value
            with self.subTest(field=field):
                with self._patched_json(self.verifier.CANDIDATE_RECEIPT_PATH, forged):
                    with self.assertRaises(self.verifier.VerificationError):
                        self.verifier.verify_dependency_and_container_candidate_receipt()

        forged_tree = copy.deepcopy(
            self.verifier.CANDIDATE_BUILD_INPUTS["application_tree"]
        )
        forged_tree["tree_sha256"] = "0" * 64
        with patch.object(
            self.verifier,
            "_candidate_application_tree_record",
            return_value=forged_tree,
        ):
            with self.assertRaises(self.verifier.VerificationError):
                self.verifier.verify_dependency_and_container_candidate_receipt()

    def test_candidate_receipt_rejects_lock_count_or_hash_drift(self) -> None:
        receipt = self.verifier.load_json(self.verifier.CANDIDATE_RECEIPT_PATH)
        forged_count = copy.deepcopy(receipt)
        forged_count["build_control_inputs"]["requirements_lock"]["package_count"] = 74
        with self._patched_json(self.verifier.CANDIDATE_RECEIPT_PATH, forged_count):
            with self.assertRaises(self.verifier.VerificationError):
                self.verifier.verify_dependency_and_container_candidate_receipt()

        forged_hash = copy.deepcopy(receipt)
        forged_hash["build_control_inputs"]["requirements_lock"]["sha256"] = "0" * 64
        with self._patched_json(self.verifier.CANDIDATE_RECEIPT_PATH, forged_hash):
            with self.assertRaises(self.verifier.VerificationError):
                self.verifier.verify_dependency_and_container_candidate_receipt()

    def test_candidate_receipt_rejects_omitted_build_control_input(self) -> None:
        receipt = self.verifier.load_json(self.verifier.CANDIDATE_RECEIPT_PATH)
        for field in (
            "dockerfile",
            "dockerignore",
            "requirements_lock",
            "requirements_input",
            "application_tree",
            "base_images",
        ):
            forged = copy.deepcopy(receipt)
            del forged["build_control_inputs"][field]
            with self.subTest(field=field):
                with self._patched_json(self.verifier.CANDIDATE_RECEIPT_PATH, forged):
                    with self.assertRaises(self.verifier.VerificationError):
                        self.verifier.verify_dependency_and_container_candidate_receipt()

        forged_boundary = copy.deepcopy(receipt)
        del forged_boundary["unresolved_boundaries"][
            "test_runner_hermeticity_and_same_run_node_ids"
        ]
        with self._patched_json(
            self.verifier.CANDIDATE_RECEIPT_PATH, forged_boundary
        ):
            with self.assertRaises(self.verifier.VerificationError):
                self.verifier.verify_dependency_and_container_candidate_receipt()

    def test_claim_ledger_rejects_extra_authority_field(self) -> None:
        ledger = self.verifier.load_json(self.verifier.CLAIM_LEDGER_PATH)
        forged = copy.deepcopy(ledger)
        forged["records"][0]["license_override"] = "LICENSED"
        with self._patched_json(self.verifier.CLAIM_LEDGER_PATH, forged):
            with self.assertRaises(self.verifier.VerificationError):
                self.verifier.verify_claim_ledger()

    def test_history_rejects_extra_gate_status(self) -> None:
        history = self.verifier.load_json(self.verifier.HISTORY_MANIFEST_PATH)
        forged = copy.deepcopy(history)
        forged["gate5_closed"] = True
        with self._patched_json(self.verifier.HISTORY_MANIFEST_PATH, forged):
            with self.assertRaises(self.verifier.VerificationError):
                self.verifier.verify_history()

    def test_markdown_rejects_explicit_contradictory_conclusion(self) -> None:
        original = self.verifier.read_stable_text
        target = self.verifier.ADVERSARIAL_REVIEW_PATH.resolve()

        def reader(path: Path, *args, **kwargs):
            text = original(path, *args, **kwargs)
            if path.resolve() == target:
                return "FINAL STATUS: GATE 5 CLOSED / ACCEPT / LICENSED / PUBLIC\n" + text
            return text

        with patch.object(self.verifier, "read_stable_text", side_effect=reader):
            with self.assertRaises(self.verifier.VerificationError):
                self.verifier.verify_no_status_promotion_text(self.artifacts)

    def test_pytest_discovery_inputs_and_caller_environment_are_controlled(self) -> None:
        surface = self.verifier.collect_pytest_environment_surface()
        self.assertIn(
            "noetic-compass-scaffold/noetic-compass/conftest.py", surface
        )
        self.assertEqual(
            self.verifier.REQUIRED_TEST_SUITES["Live trace worker complete"][
                "pytest_plugins"
            ],
            ["pytest_asyncio.plugin"],
        )
        self.assertEqual(
            self.verifier.REQUIRED_TEST_SUITES[
                "API, fleet state, and launcher identity"
            ]["pytest_plugins"],
            ["pytest_asyncio.plugin"],
        )
        with patch.dict(
            os.environ,
            {
                "GIT_CONFIG_COUNT": "2",
                "GIT_CONFIG_KEY_0": "alias.show",
                "GIT_CONFIG_VALUE_0": "!false",
                "GIT_CONFIG_KEY_1": "safe.directory",
                "GIT_CONFIG_VALUE_1": "*",
            },
        ):
            controlled_environment = self.verifier._subprocess_environment()
        self.assertEqual(controlled_environment["GIT_CONFIG_COUNT"], "1")
        self.assertEqual(controlled_environment["GIT_CONFIG_KEY_0"], "safe.directory")
        self.assertEqual(
            controlled_environment["GIT_CONFIG_VALUE_0"],
            self.verifier.GIT_SAFE_DIRECTORY,
        )
        self.assertNotIn("GIT_CONFIG_KEY_1", controlled_environment)
        self.assertNotIn("GIT_CONFIG_VALUE_1", controlled_environment)

        expected_retained_specs = {
            "SRC-PCBA-ENGINEER-20260726": {
                "registered_path": r"C:\Users\wakil\OneDrive\Desktop\tksCAS\book\CAS_PCBA_Engineer\CAS_PCBA_Engineer.pdf",
                "frozen_sha256": "294320B39FA521EAC086E99E2D9DB913E2B6CFF0754FF82DB1EF966424566274",
                "frozen_bytes": 1_973_407,
                "observed_live_sha256": "F31584E628689115AFBA08C4686A1D07A28BBC2BFAF9103D3505F5177937372A",
                "observed_live_bytes": 2_070_194,
                "git_path": "book/CAS_PCBA_Engineer/CAS_PCBA_Engineer.pdf",
                "blob_oid": "af187b5d85f3ebbf90a802dcfc68b81924ff57ce",
                "blob_sha256": "294320B39FA521EAC086E99E2D9DB913E2B6CFF0754FF82DB1EF966424566274",
                "blob_bytes": 1_973_407,
                "materialization": "RAW_BLOB_IDENTITY",
                "temp_filename": "SRC-PCBA-ENGINEER-20260726.bin",
            },
            "SRC-CAS-OHM-PCBA-APP-I": {
                "registered_path": r"C:\Users\wakil\OneDrive\Desktop\tksCAS\book\CAS_PCBA_Engineer\Appendix_I_CAS_Ohm_Measurement_and_Calibration.md",
                "frozen_sha256": "9FFFAC3E16B43C6D809ECE913FD8C09E40C65F60F3B4BE693F45D35EC4E6AC45",
                "frozen_bytes": 14_998,
                "observed_live_sha256": "5BE5667EB9B37460A7B7C2F9C21CA664582445F54136C0CB0A87CEC6DD98DE60",
                "observed_live_bytes": 21_618,
                "git_path": (
                    "book/CAS_PCBA_Engineer/"
                    "Appendix_I_CAS_Ohm_Measurement_and_Calibration.md"
                ),
                "blob_oid": "fab6c93ba24ebdd13feb396a22d122def3ad3cc1",
                "blob_sha256": "880ED91B164D6A3ECA0C8A47A408F3702FBACBB5AFD750E6E963D7DD5129264C",
                "blob_bytes": 14_655,
                "blob_lf_count": 343,
                "blob_cr_count": 0,
                "materialization": "EXACT_LF_TO_CRLF_343",
                "temp_filename": "SRC-CAS-OHM-PCBA-APP-I.bin",
            },
        }
        self.assertEqual(
            {
                source_id: dict(source_spec)
                for source_id, source_spec in (
                    self.verifier.GATE4_RETAINED_SOURCE_SPECS.items()
                )
            },
            expected_retained_specs,
        )
        self.assertEqual(
            self.verifier.GATE4_RETAINED_GIT_COMMIT,
            "130168b3bd215e2975c8eb88776ed2be3b1c2227",
        )
        self.assertEqual(
            self.verifier.GATE4_RETAINED_SOURCE_BOUNDARY,
            "RETAINED GIT BLOB / LIVE REGISTERED PATH DRIFTED / "
            "LOCAL NONPORTABLE / NO CURRENT-SOURCE EQUIVALENCE",
        )

        hostile_git_environment = {
            "GIT_DIR": r"C:\attacker\objects",
            "GIT_WORK_TREE": r"C:\attacker\tree",
            "GIT_OBJECT_DIRECTORY": r"C:\attacker\objects",
            "GIT_ALTERNATE_OBJECT_DIRECTORIES": r"C:\attacker\alternate",
            "GIT_REPLACE_REF_BASE": "refs/attacker",
            "GIT_CONFIG_PARAMETERS": "'alias.cat-file=!false'",
            "GIT_CONFIG_SYSTEM": r"C:\attacker\system.gitconfig",
            "GIT_CONFIG_GLOBAL": r"C:\attacker\global.gitconfig",
            "GIT_CONFIG_COUNT": "2",
            "GIT_CONFIG_KEY_0": "alias.cat-file",
            "GIT_CONFIG_VALUE_0": "!false",
            "GIT_CONFIG_KEY_1": "safe.directory",
            "GIT_CONFIG_VALUE_1": "*",
        }
        with patch.dict(os.environ, hostile_git_environment), patch.object(
            self.verifier.subprocess,
            "run",
            return_value=SimpleNamespace(
                returncode=0, stdout=b"blob\n", stderr=b""
            ),
        ) as retained_git_run:
            self.assertEqual(
                self.verifier._run_retained_gate4_git(
                    ["cat-file", "-t", "0" * 40], label="red-team probe"
                ),
                b"blob\n",
            )
        retained_command = retained_git_run.call_args.args[0]
        retained_environment = retained_git_run.call_args.kwargs["env"]
        self.assertEqual(
            retained_command,
            [
                str(self.verifier.GATE4_RETAINED_GIT_EXECUTABLE),
                "--no-replace-objects",
                "-C",
                str(self.verifier.GATE4_RETAINED_GIT_REPOSITORY),
                "cat-file",
                "-t",
                "0" * 40,
            ],
        )
        for hostile_name in (
            "GIT_DIR",
            "GIT_WORK_TREE",
            "GIT_OBJECT_DIRECTORY",
            "GIT_ALTERNATE_OBJECT_DIRECTORIES",
            "GIT_REPLACE_REF_BASE",
            "GIT_CONFIG_PARAMETERS",
            "GIT_CONFIG_SYSTEM",
        ):
            with self.subTest(hostile_name=hostile_name):
                self.assertNotIn(hostile_name, retained_environment)
        self.assertEqual(retained_environment["GIT_CONFIG_COUNT"], "1")
        self.assertEqual(retained_environment["GIT_CONFIG_KEY_0"], "safe.directory")
        self.assertEqual(
            retained_environment["GIT_CONFIG_VALUE_0"],
            self.verifier.GATE4_RETAINED_GIT_REPOSITORY.as_posix(),
        )
        self.assertEqual(retained_environment["GIT_CONFIG_GLOBAL"], "NUL")
        self.assertEqual(retained_environment["GIT_CONFIG_NOSYSTEM"], "1")
        self.assertEqual(retained_environment["GIT_NO_LAZY_FETCH"], "1")
        self.assertEqual(retained_environment["GIT_NO_REPLACE_OBJECTS"], "1")
        self.assertEqual(retained_environment["GIT_ALLOW_PROTOCOL"], "file")

        retained_payloads = self.verifier._read_retained_gate4_git_payloads()
        pdf_id = "SRC-PCBA-ENGINEER-20260726"
        appendix_id = "SRC-CAS-OHM-PCBA-APP-I"
        self.assertEqual(
            self.verifier._retained_gate4_materialized_payload(
                pdf_id, retained_payloads[pdf_id]
            ),
            retained_payloads[pdf_id],
        )
        appendix_raw = retained_payloads[appendix_id]
        appendix_materialized = self.verifier._retained_gate4_materialized_payload(
            appendix_id, appendix_raw
        )
        self.assertEqual((appendix_raw.count(b"\n"), appendix_raw.count(b"\r")), (343, 0))
        self.assertEqual(appendix_materialized, appendix_raw.replace(b"\n", b"\r\n"))
        for source_id, payload in retained_payloads.items():
            mutated = payload[:-1] + bytes((payload[-1] ^ 1,))
            with self.subTest(mutated_source_id=source_id):
                with self.assertRaises(self.verifier.VerificationError):
                    self.verifier._retained_gate4_materialized_payload(
                        source_id, mutated
                    )
        with self.assertRaises(self.verifier.VerificationError):
            self.verifier._retained_gate4_materialized_payload(
                appendix_id, appendix_raw.replace(b"\n", b"\r\n", 1)
            )

        replacements = {
            source_spec["registered_path"]: Path(source_spec["temp_filename"])
            for source_spec in expected_retained_specs.values()
        }
        nested_pids = (1001, 1002, 1003)
        nested_lines = [
            f"{nested_pid}\t{registered_path}"
            for nested_pid in nested_pids
            for registered_path in replacements
        ]
        nested_counts, observed_nested_pids = (
            self.verifier._validate_gate4_nested_resolution_receipt(
                nested_lines, replacements, child_pid=999
            )
        )
        self.assertEqual(set(nested_counts.values()), {3})
        self.assertEqual(observed_nested_pids, set(nested_pids))
        malformed_nested_receipts = (
            nested_lines[:-1],
            [*nested_lines[:-1], nested_lines[0]],
            [*nested_lines[:-1], "1003\tC:\\generic-override"],
        )
        for malformed_receipt in malformed_nested_receipts:
            with self.subTest(malformed_receipt=malformed_receipt):
                with self.assertRaises(self.verifier.VerificationError):
                    self.verifier._validate_gate4_nested_resolution_receipt(
                        malformed_receipt, replacements, child_pid=999
                    )
        with self.assertRaises(self.verifier.VerificationError):
            self.verifier._validate_gate4_nested_resolution_receipt(
                nested_lines, replacements, child_pid=nested_pids[0]
            )

        stdout, _ = self.verifier.run_command(
            [
                sys.executable,
                "-I",
                "-S",
                "-B",
                "-c",
                (
                    "import json, os, sys; print(json.dumps({"
                    "'autoload': os.environ.get('PYTEST_DISABLE_PLUGIN_AUTOLOAD'),"
                    "'addopts': os.environ.get('PYTEST_ADDOPTS'),"
                    "'plugins': os.environ.get('PYTEST_PLUGINS'),"
                    "'pythonpath': 'PYTHONPATH' in os.environ,"
                    "'pythonhome': 'PYTHONHOME' in os.environ,"
                    "'coverage_startup': 'COVERAGE_PROCESS_START' in os.environ,"
                    "'safe_path': bool(sys.flags.safe_path),"
                    "'ignore_environment': bool(sys.flags.ignore_environment),"
                    "'isolated': bool(sys.flags.isolated),"
                    "'no_site': bool(sys.flags.no_site),"
                    "'no_user_site': bool(sys.flags.no_user_site),"
                    "'dont_write_bytecode': bool(sys.flags.dont_write_bytecode),"
                    "'site_loaded': 'site' in sys.modules}))"
                ),
            ],
            cwd=ROOT,
            timeout=20,
            extra_env=self.verifier.PYTEST_ISOLATION_ENV,
            remove_env=self.verifier.PYTEST_REMOVED_ENV,
        )
        self.assertEqual(
            json.loads(stdout),
            {
                "autoload": "1",
                "addopts": "",
                "plugins": "",
                "pythonpath": False,
                "pythonhome": False,
                "coverage_startup": False,
                "safe_path": True,
                "ignore_environment": True,
                "isolated": True,
                "no_site": True,
                "no_user_site": True,
                "dont_write_bytecode": True,
                "site_loaded": False,
            },
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary = Path(temporary_directory)
            site_root = temporary / "site-packages"
            locked_package = site_root / "pytest"
            locked_package.mkdir(parents=True)
            locked_file = locked_package / "__init__.py"
            locked_file.write_bytes(b"LOCKED = True\n")
            rogue_file = locked_package / "rogue.py"
            rogue_file.write_bytes(b"ROGUE = True\n")
            locked_bytes = locked_file.read_bytes()
            lock = {
                "admitted_pytest_site_root": str(site_root),
                "python_identity": {"stdlib_root": str(Path(sys.base_prefix) / "Lib")},
                "admitted_runner_distributions": [
                    {
                        "distribution": "pytest",
                        "canonical_distribution": "pytest",
                        "version": "test",
                        "file_count": 1,
                        "byte_count": len(locked_bytes),
                        "tree_sha256": "0" * 64,
                        "files": [
                            {
                                "path": "pytest/__init__.py",
                                "bytes": len(locked_bytes),
                                "sha256": hashlib.sha256(locked_bytes)
                                .hexdigest()
                                .upper(),
                                "owner_distribution": "pytest",
                            }
                        ],
                        "excluded_outside_site_files": [],
                        "tree_digest_rule": "test fixture",
                    }
                ],
            }
            rogue_bytes = rogue_file.read_bytes()
            rogue_record = {
                "path": str(rogue_file),
                "bytes": len(rogue_bytes),
                "sha256": hashlib.sha256(rogue_bytes).hexdigest().upper(),
                "module_names": ["pytest.rogue"],
                "kind": "PYTHON_OR_DATA",
            }
            with self.assertRaisesRegex(
                self.verifier.VerificationError, "masqueraded"
            ):
                self.verifier._validate_loaded_module_records(
                    name="synthetic post-test",
                    records=[rogue_record],
                    lock=lock,
                    admitted_artifact_paths=set(),
                    pre_test=False,
                )

            python_root = temporary / "python-root"
            python_root.mkdir()
            shadow = python_root / "gate5_shadow_probe.py"
            shadow.write_bytes(b"VALUE = 'shadow'\n")
            admitted = site_root / "gate5_shadow_probe.py"
            admitted.write_bytes(b"VALUE = 'locked'\n")
            admitted_bytes = admitted.read_bytes()
            admitted_map = {
                str(admitted).casefold(): {
                    "path": "gate5_shadow_probe.py",
                    "bytes": len(admitted_bytes),
                    "sha256": hashlib.sha256(admitted_bytes).hexdigest().upper(),
                    "owner_distribution": "pytest",
                }
            }
            importlib.invalidate_caches()
            with patch.object(sys, "path", [str(python_root), str(site_root)]):
                with self.assertRaisesRegex(ValueError, "outside its file lock"):
                    self.runner._locked_import_origin(
                        "gate5_shadow_probe",
                        site_root=site_root,
                        locked_files=admitted_map,
                    )
            sys.modules.pop("gate5_shadow_probe", None)

            lock_path = temporary / "runner-lock.json"
            lock_path.write_bytes(b'{"value":"A"}\n')
            stable_bytes = self.runner._read_stable_unique_file(lock_path)
            replacement = temporary / "replacement.json"
            replacement.write_bytes(b'{"value":"B"}\n')
            os.replace(replacement, lock_path)
            self.assertEqual(self.runner._load_unique_json(stable_bytes), {"value": "A"})

        duplicate_distributions = [
            SimpleNamespace(metadata={"Name": "pytest_asyncio"}),
            SimpleNamespace(metadata={"Name": "pytest-asyncio"}),
        ]
        with patch.object(
            self.runner_lock_builder.importlib.metadata,
            "distributions",
            return_value=duplicate_distributions,
        ):
            with self.assertRaisesRegex(RuntimeError, "duplicate normalized"):
                self.runner_lock_builder._distribution_records(Path.cwd())

        runner_tree = ast.parse(RUNNER_PATH.read_bytes(), filename=RUNNER_PATH.as_posix())
        runner_main = next(
            node
            for node in runner_tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "main"
        )
        runner_calls = {
            node.func.id
            for node in ast.walk(runner_main)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        self.assertTrue(
            {"_read_stable_unique_file", "_load_unique_json", "_import_locked_module"}
            <= runner_calls
        )

        verifier_record = {
            "path": str(VERIFIER_PATH.resolve()),
            "bytes": 123,
            "sha256": "A" * 64,
            "module_names": ["gate5_verifier_redteam"],
            "kind": "PYTHON_OR_DATA",
        }
        runner_record = {
            "path": str(RUNNER_PATH.resolve()),
            "bytes": 456,
            "sha256": "B" * 64,
            "module_names": ["gate5_runner_redteam"],
            "kind": "PYTHON_OR_DATA",
        }
        loaded_records = [verifier_record, runner_record]
        normalized = self.verifier._loaded_code_digest(
            name="Harness v2 kernel and history", records=loaded_records
        )
        rewritten_self = copy.deepcopy(loaded_records)
        rewritten_self[0]["bytes"] = 999
        rewritten_self[0]["sha256"] = "C" * 64
        self.assertEqual(
            self.verifier._loaded_code_digest(
                name="Harness v2 kernel and history", records=rewritten_self
            ),
            normalized,
        )
        rewritten_other = copy.deepcopy(loaded_records)
        rewritten_other[1]["sha256"] = "D" * 64
        self.assertNotEqual(
            self.verifier._loaded_code_digest(
                name="Harness v2 kernel and history", records=rewritten_other
            ),
            normalized,
        )
        with self.assertRaisesRegex(
            self.verifier.VerificationError, "exactly one verifier self-record"
        ):
            self.verifier._loaded_code_digest(
                name="Harness v2 kernel and history", records=[runner_record]
            )
        with self.assertRaisesRegex(
            self.verifier.VerificationError, "exactly one verifier self-record"
        ):
            self.verifier._loaded_code_digest(
                name="Harness v2 kernel and history",
                records=[verifier_record, verifier_record, runner_record],
            )
        self.assertEqual(
            self.verifier._loaded_code_digest(
                name="Live trace worker complete", records=loaded_records
            ),
            self.verifier._canonical_json_digest(loaded_records),
        )
        self.assertIn(
            "NORMALIZED-PROJECTION V1",
            self.verifier.CURRENT_HARNESS_LOADED_CODE_DIGEST_RULE,
        )
        self.assertEqual(
            self.verifier.RAW_LOADED_CODE_DIGEST_RULE,
            "CANONICAL VALIDATED LOADED-MODULE RECORDS / RAW RECORDS / NO PROJECTION",
        )

        with tempfile.TemporaryDirectory() as validation_directory:
            validation_site_root = Path(validation_directory) / "site-packages"
            validation_site_root.mkdir()
            validation_lock = {
                "admitted_pytest_site_root": str(validation_site_root),
                "python_identity": {"stdlib_root": str(Path(sys.base_prefix) / "Lib")},
                "admitted_runner_distributions": [],
            }
            verifier_bytes = VERIFIER_PATH.read_bytes()
            exact_verifier_record = {
                "path": str(VERIFIER_PATH.resolve()),
                "bytes": len(verifier_bytes),
                "sha256": hashlib.sha256(verifier_bytes).hexdigest().upper(),
                "module_names": ["gate5_verifier_redteam"],
                "kind": "PYTHON_OR_DATA",
            }
            admitted_verifier_path = (
                VERIFIER_PATH.resolve().relative_to(ROOT).as_posix()
            )
            self.assertEqual(
                self.verifier._validate_loaded_module_records(
                    name="synthetic exact verifier",
                    records=[exact_verifier_record],
                    lock=validation_lock,
                    admitted_artifact_paths={admitted_verifier_path},
                    pre_test=False,
                ),
                [exact_verifier_record],
            )
            for field, forged_value in (("bytes", 0), ("sha256", "F" * 64)):
                forged_verifier_record = copy.deepcopy(exact_verifier_record)
                forged_verifier_record[field] = forged_value
                with self.assertRaisesRegex(
                    self.verifier.VerificationError,
                    "loaded-code identity drifted after the child exited",
                ):
                    self.verifier._validate_loaded_module_records(
                        name=f"synthetic forged verifier {field}",
                        records=[forged_verifier_record],
                        lock=validation_lock,
                        admitted_artifact_paths={admitted_verifier_path},
                        pre_test=False,
                    )

    def test_main_retains_post_subprocess_rehashes(self) -> None:
        tree = ast.parse(VERIFIER_PATH.read_bytes(), filename=VERIFIER_PATH.as_posix())
        main = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "main"
        )
        calls = [
            (node.func.id, node.lineno)
            for node in ast.walk(main)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        ]
        names = {name for name, _ in calls}
        self.assertTrue(
            {
                "verify_manifest",
                "verify_history",
                "verify_gate4_artifact_bytes",
                "verify_no_executable_shadow_artifacts",
                "verify_raw_build_and_security_evidence_receipt",
                "verify_local_test_runner_lock",
                "capture_integrated_file_observations",
                "verify_integrated_file_observations_unchanged",
            }
            <= names
        )
        test_line = next(line for name, line in calls if name == "verify_test_suites")
        manifest_lines = sorted(line for name, line in calls if name == "verify_manifest")
        history_lines = sorted(line for name, line in calls if name == "verify_history")
        gate4_post_lines = sorted(
            line for name, line in calls if name == "verify_gate4_artifact_bytes"
        )
        shadow_lines = sorted(
            line for name, line in calls if name == "verify_no_executable_shadow_artifacts"
        )
        capture_line = next(
            line for name, line in calls if name == "capture_integrated_file_observations"
        )
        identity_post_line = next(
            line
            for name, line in calls
            if name == "verify_integrated_file_observations_unchanged"
        )
        runner_lock_lines = sorted(
            line for name, line in calls if name == "verify_local_test_runner_lock"
        )
        manifest_observation_lines = sorted(
            line for name, line in calls if name == "observe_regular_file"
        )
        self.assertGreaterEqual(len(manifest_lines), 2)
        self.assertGreaterEqual(len(history_lines), 2)
        self.assertGreaterEqual(len(shadow_lines), 2)
        self.assertLess(shadow_lines[0], test_line)
        self.assertGreater(shadow_lines[-1], test_line)
        self.assertLess(capture_line, test_line)
        self.assertGreater(identity_post_line, test_line)
        self.assertGreaterEqual(len(runner_lock_lines), 2)
        self.assertGreaterEqual(len(manifest_observation_lines), 2)
        self.assertLess(manifest_observation_lines[0], test_line)
        self.assertGreater(manifest_observation_lines[-1], test_line)
        self.assertLess(runner_lock_lines[0], test_line)
        self.assertGreater(runner_lock_lines[-1], test_line)
        self.assertLess(manifest_lines[0], test_line)
        self.assertGreater(manifest_lines[-1], test_line)
        self.assertGreater(history_lines[-1], test_line)
        self.assertTrue(gate4_post_lines)
        self.assertGreater(gate4_post_lines[-1], test_line)


if __name__ == "__main__":
    unittest.main()
