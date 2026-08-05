from __future__ import annotations

import ast
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
VERIFIER_PATH = ROOT / "scripts" / "verify_project_coherence_gate5.py"


def _load_verifier():
    spec = importlib.util.spec_from_file_location("gate5_verifier_redteam", VERIFIER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Gate 5 verifier")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Gate5VerifierRedTeamTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.verifier = _load_verifier()
        cls.manifest = cls.verifier.load_json(cls.verifier.MANIFEST_PATH)
        cls.artifacts = cls.verifier.verify_manifest(cls.manifest)

    def _patched_json(self, target: Path, value: object):
        original = self.verifier.load_json

        def loader(path: Path):
            if path == target:
                return value
            return original(path)

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
            "collect_pytest_ids",
            side_effect=AssertionError("collection must not run"),
        ):
            with self.assertRaises(self.verifier.VerificationError):
                self.verifier.verify_test_suites(forged_suite)

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
        original = Path.read_text
        target = self.verifier.ADVERSARIAL_REVIEW_PATH.resolve()

        def reader(path: Path, *args, **kwargs):
            text = original(path, *args, **kwargs)
            if path.resolve() == target:
                return "FINAL STATUS: GATE 5 CLOSED / ACCEPT / LICENSED / PUBLIC\n" + text
            return text

        with patch.object(Path, "read_text", new=reader):
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
        stdout, _ = self.verifier.run_command(
            [
                sys.executable,
                "-E",
                "-P",
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
                    "'ignore_environment': bool(sys.flags.ignore_environment)}))"
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
            },
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
            }
            <= names
        )
        test_line = next(line for name, line in calls if name == "verify_test_suites")
        manifest_lines = sorted(line for name, line in calls if name == "verify_manifest")
        history_lines = sorted(line for name, line in calls if name == "verify_history")
        gate4_post_lines = sorted(
            line for name, line in calls if name == "verify_gate4_artifact_bytes"
        )
        shadow_line = next(
            line for name, line in calls if name == "verify_no_executable_shadow_artifacts"
        )
        self.assertGreaterEqual(len(manifest_lines), 2)
        self.assertGreaterEqual(len(history_lines), 2)
        self.assertLess(shadow_line, test_line)
        self.assertLess(manifest_lines[0], test_line)
        self.assertGreater(manifest_lines[-1], test_line)
        self.assertGreater(history_lines[-1], test_line)
        self.assertTrue(gate4_post_lines)
        self.assertGreater(gate4_post_lines[-1], test_line)


if __name__ == "__main__":
    unittest.main()
