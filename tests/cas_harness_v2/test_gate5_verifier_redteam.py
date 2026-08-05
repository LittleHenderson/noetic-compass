from __future__ import annotations

import ast
import copy
import importlib.util
import json
from pathlib import Path
import sys
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

    def test_manifest_rejects_float_governance_and_suite_counts(self) -> None:
        forged_ring = copy.deepcopy(self.manifest)
        forged_ring["admission_ring"] = 4.0
        with self.assertRaises(self.verifier.VerificationError):
            self.verifier.verify_manifest(forged_ring)

        forged_suite = copy.deepcopy(self.manifest)
        forged_suite["test_suites"][0]["expected_subtests"] = 50.0
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
        stdout, _ = self.verifier.run_command(
            [
                sys.executable,
                "-c",
                (
                    "import json, os; print(json.dumps({"
                    "'autoload': os.environ.get('PYTEST_DISABLE_PLUGIN_AUTOLOAD'),"
                    "'addopts': os.environ.get('PYTEST_ADDOPTS'),"
                    "'plugins': os.environ.get('PYTEST_PLUGINS'),"
                    "'pythonpath': 'PYTHONPATH' in os.environ,"
                    "'pythonhome': 'PYTHONHOME' in os.environ}))"
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
            },
        )

    def test_main_retains_post_subprocess_rehashes(self) -> None:
        tree = ast.parse(VERIFIER_PATH.read_bytes(), filename=VERIFIER_PATH.as_posix())
        main = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "main"
        )
        calls = {
            node.func.id
            for node in ast.walk(main)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        self.assertTrue(
            {
                "verify_manifest",
                "verify_history",
                "verify_gate4_artifact_bytes",
            }
            <= calls
        )


if __name__ == "__main__":
    unittest.main()
