from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from decimal import Decimal
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import cas_core_v8.compatibility as compatibility_module

from cas_core_v8 import (
    CAS_V77_COMPILER_CANONICAL_LF_SHA256,
    CAS_V77_COMPILER_RAW_CRLF_SHA256,
    CompatibilityError,
    CompilerIdentityPolicy,
    LegacyDiagnosticCode,
    LegacySourceEnvelope,
    PYTHON_ONLY_ENGINE_PROFILE,
    bridge_legacy_fractal,
    canonical_json_sha256,
    compile_legacy_expression,
)
from tks_v8_core import FiniteArrow, FiniteObject


COMPILER = (
    ROOT
    / "noetic-compass-scaffold"
    / "noetic-compass"
    / "api"
    / "notation"
    / "compiler.py"
)


class CompatibilityCompilerTests(unittest.TestCase):
    def test_frozen_compiler_runs_only_as_bound_python_legacy_profile(self) -> None:
        result = compile_legacy_expression(
            LegacySourceEnvelope.bind("C1 -> E2"), compiler_path=COMPILER
        )
        self.assertTrue(result.legacy_artifact["valid"])
        self.assertEqual(result.legacy_artifact["engine"], "python")
        self.assertEqual(result.engine_profile, PYTHON_ONLY_ENGINE_PROFILE)
        self.assertEqual(
            result.compiler_identity.canonical_lf_sha256,
            CAS_V77_COMPILER_CANONICAL_LF_SHA256,
        )
        self.assertEqual(
            canonical_json_sha256(result.legacy_artifact),
            result.legacy_artifact_sha256,
        )
        self.assertEqual(len(canonical_json_sha256(result.to_dict())), 64)
        self.assertEqual(result.boundary.to_dict()["status"], "OPEN")
        self.assertEqual(result.v8_semantic_translation, None)
        self.assertEqual(
            result.execution_profile_sha256,
            result.execution_profile.profile_sha256,
        )
        self.assertTrue(result.execution_profile.fresh_process)
        self.assertFalse(result.execution_profile.parent_sys_modules_inherited)
        self.assertTrue(result.execution_profile.isolated_mode)
        self.assertTrue(result.execution_profile.ignore_environment)
        self.assertTrue(result.execution_profile.safe_path)
        self.assertTrue(result.execution_profile.no_site)
        self.assertTrue(result.execution_profile.no_user_site)
        self.assertTrue(result.execution_profile.dont_write_bytecode)
        self.assertFalse(result.execution_profile.os_sandboxed)
        self.assertFalse(
            result.execution_profile.host_os_dependencies_content_addressed
        )
        self.assertTrue(result.execution_profile.import_search_paths)
        self.assertTrue(
            all(
                Path(path).is_absolute()
                for path in result.execution_profile.import_search_paths
            )
        )
        self.assertGreater(len(result.execution_profile.dependencies), 0)
        dependency_names = {
            dependency.module_name
            for dependency in result.execution_profile.dependencies
        }
        self.assertNotIn("platform", dependency_names)
        self.assertNotIn("_wmi", dependency_names)
        self.assertNotIn("subprocess", dependency_names)
        self.assertIn(
            LegacyDiagnosticCode.LEGACY_COMPATIBILITY_PROFILE,
            result.diagnostics,
        )

    def test_unstructured_worker_exit_is_exactly_reported_and_not_retried(
        self,
    ) -> None:
        failed = subprocess.CompletedProcess(
            args=(sys.executable,),
            returncode=1,
            stdout=b"",
            stderr=b"",
        )
        with (
            patch.object(
                compatibility_module.subprocess, "run", return_value=failed
            ) as worker,
            self.assertRaisesRegex(
                CompatibilityError,
                r'E-COMPAT-WORKER-EXIT: .*"returncode":1.*'
                r'"stderr_bytes":0.*"stdout_bytes":0',
            ),
        ):
            compile_legacy_expression(
                LegacySourceEnvelope.bind("C1"), compiler_path=COMPILER
            )
        self.assertEqual(worker.call_count, 1)

    def test_profile_mismatch_reports_only_bounded_hashes_and_keyed_paths(
        self,
    ) -> None:
        first_payload = {
            "runtime": {
                "environment": [
                    {"name": "COMSPEC", "value": "first-sensitive-value"}
                ]
            },
            "dependencies": [
                {
                    "module_name": "json",
                    "origin_kind": "FILE",
                    "path": "first-sensitive-path",
                    "identity": {"raw_sha256": "1" * 64},
                }
            ],
        }
        replay_payload = {
            "runtime": {
                "environment": [
                    {"name": "COMSPEC", "value": "replay-sensitive-value"}
                ]
            },
            "dependencies": [
                {
                    "module_name": "json",
                    "origin_kind": "FILE",
                    "path": "replay-sensitive-path",
                    "identity": {"raw_sha256": "1" * 64},
                },
                {
                    "module_name": "subprocess",
                    "origin_kind": "FILE",
                    "path": "another-sensitive-path",
                    "identity": {"raw_sha256": "2" * 64},
                },
            ],
        }
        first = SimpleNamespace(
            profile_sha256="A" * 64,
            payload_without_digest=lambda: first_payload,
        )
        replay = SimpleNamespace(
            profile_sha256="B" * 64,
            payload_without_digest=lambda: replay_payload,
        )

        diagnostic = compatibility_module._profile_mismatch_diagnostic(
            first, replay
        )

        self.assertIn('"first_profile_sha256":"' + "A" * 64 + '"', diagnostic)
        self.assertIn('"replay_profile_sha256":"' + "B" * 64 + '"', diagnostic)
        self.assertIn(
            '$.dependencies[\\"module_name=subprocess\\"]', diagnostic
        )
        self.assertIn(
            '$.runtime.environment[\\"name=COMSPEC\\"].value_sha256',
            diagnostic,
        )
        self.assertNotIn("sensitive", diagnostic)
        self.assertLessEqual(
            len(json.loads(diagnostic)["difference_paths"]),
            compatibility_module.PROFILE_DIFFERENCE_PATH_LIMIT,
        )

    def test_concurrent_worker_launches_are_serialized_and_profiled(self) -> None:
        def compile_once(_: int):
            return compile_legacy_expression(
                LegacySourceEnvelope.bind("C1"), compiler_path=COMPILER
            )

        with ThreadPoolExecutor(max_workers=8) as executor:
            results = tuple(executor.map(compile_once, range(8)))

        first = results[0]
        expected_environment = compatibility_module._worker_environment()
        expected_runtime = compatibility_module._runtime_identity(
            expected_environment
        )
        self.assertTrue(
            all(
                result.legacy_artifact_sha256 == first.legacy_artifact_sha256
                and result.execution_profile == first.execution_profile
                and (
                    result.execution_profile.implementation,
                    result.execution_profile.version,
                    result.execution_profile.platform_name,
                    result.execution_profile.machine,
                )
                == expected_runtime
                and {
                    item.name: item.value
                    for item in result.execution_profile.environment
                }
                == expected_environment
                for result in results
            )
        )
        launch = first.execution_profile.to_dict()["runtime"]["worker_launch"]
        self.assertEqual(
            launch["policy"], compatibility_module.WORKER_LAUNCH_POLICY
        )
        self.assertTrue(Path(launch["lock_path"]).is_absolute())
        self.assertEqual(
            launch["lock_timeout_seconds"],
            compatibility_module.WORKER_LAUNCH_LOCK_TIMEOUT_SECONDS,
        )
        self.assertEqual(
            launch["poll_milliseconds"],
            compatibility_module.WORKER_LAUNCH_POLL_MILLISECONDS,
        )
        self.assertEqual(
            launch["post_release_yield_milliseconds"],
            compatibility_module.WORKER_LAUNCH_POST_RELEASE_YIELD_MILLISECONDS,
        )
        if os.name == "nt":
            self.assertEqual(
                expected_environment.get("PROCESSOR_ARCHITECTURE"),
                os.environ.get("PROCESSOR_ARCHITECTURE"),
            )
            self.assertEqual(
                expected_environment.get("PROCESSOR_ARCHITEW6432"),
                os.environ.get("PROCESSOR_ARCHITEW6432"),
            )

    def test_runtime_is_sampled_before_compiler_code_can_mutate_platform_cache(
        self,
    ) -> None:
        compiler_source = b"""\
import platform

class Artifact:
    def to_dict(self):
        return {"engine": "python"}

def lex(source):
    return ()

def compile_expression(source):
    platform._uname_cache = platform.uname_result(
        "mutated-system", "mutated-node", "mutated-release",
        "mutated-version", "compiler-mutated-machine"
    )
    return Artifact()
"""
        artifact, profile = compatibility_module._run_isolated_worker(
            compiler_source=compiler_source,
            compiler_identity=compatibility_module.ArtifactIdentity.from_bytes(
                compiler_source
            ),
            source="C1",
            source_sha256=compatibility_module.sha256_hex(b"C1"),
        )

        self.assertEqual(artifact, {"engine": "python"})
        self.assertEqual(profile.machine, compatibility_module._runtime_identity()[3])
        self.assertNotEqual(profile.machine, "compiler-mutated-machine")

    def test_source_hash_mismatch_fails_before_compilation(self) -> None:
        envelope = LegacySourceEnvelope(
            source="C1",
            declared_version="CAS v7.7",
            syntax_profile="cas-v7.7",
            source_sha256="0" * 64,
        )
        with self.assertRaisesRegex(CompatibilityError, "E-COMPAT-SOURCE-HASH"):
            compile_legacy_expression(envelope, compiler_path=COMPILER)

    def test_unknown_source_version_is_rejected(self) -> None:
        envelope = LegacySourceEnvelope.bind(
            "C1", declared_version="CAS v9 fictional"
        )
        with self.assertRaisesRegex(CompatibilityError, "E-COMPAT-VERSION"):
            compile_legacy_expression(envelope, compiler_path=COMPILER)

    def test_compiler_policy_override_is_not_a_public_input(self) -> None:
        untrusted = replace(
            CompilerIdentityPolicy.cas_v77(), source_id="SRC-CALLER-INVENTED"
        )
        with self.assertRaises(TypeError):
            compile_legacy_expression(
                LegacySourceEnvelope.bind("C1"),
                compiler_path=COMPILER,
                policy=untrusted,
            )

        class PolicyVariant(CompilerIdentityPolicy):
            def __eq__(self, other: object) -> bool:
                return True

        trusted = CompilerIdentityPolicy.cas_v77()
        with self.assertRaisesRegex(CompatibilityError, "subclasses"):
            PolicyVariant(
                source_id=trusted.source_id,
                accepted_versions=trusted.accepted_versions,
                accepted_syntax_profiles=trusted.accepted_syntax_profiles,
                raw_sha256_variants=trusted.raw_sha256_variants,
                canonical_lf_sha256=trusted.canonical_lf_sha256,
            )

    def test_legacy_fractal_is_not_silently_typed(self) -> None:
        result = compile_legacy_expression(
            LegacySourceEnvelope.bind("Phi<1:2>"), compiler_path=COMPILER
        )
        self.assertIn(
            LegacyDiagnosticCode.UNTYPED_FRACTAL_REQUIRES_BRIDGE,
            result.diagnostics,
        )
        self.assertEqual(result.v8_semantic_translation, None)

    def test_unbound_use_import_is_rejected_before_evaluation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            dependency = Path(temp_dir) / "mutable.cas"
            dependency.write_text("export let x = C1", encoding="utf-8")
            source = f'use "{dependency.as_posix()}"; x'
            with self.assertRaisesRegex(CompatibilityError, "UNBOUND-IMPORT"):
                compile_legacy_expression(
                    LegacySourceEnvelope.bind(source), compiler_path=COMPILER
                )

    def test_parent_module_injection_cannot_change_fresh_worker_result(self) -> None:
        baseline = compile_legacy_expression(
            LegacySourceEnvelope.bind("C1 * C2"), compiler_path=COMPILER
        )
        sentinel = object()
        prior_engine = sys.modules.get("cas_engine", sentinel)
        prior_math = sys.modules.get("math", sentinel)
        sys.modules["cas_engine"] = SimpleNamespace(
            multiply_cognitive_states=lambda *args: (9, 3, 7)
        )
        sys.modules["math"] = SimpleNamespace(
            isfinite=lambda value: False,
            isnan=lambda value: True,
        )
        try:
            result = compile_legacy_expression(
                LegacySourceEnvelope.bind("C1 * C2"), compiler_path=COMPILER
            )
        finally:
            if prior_engine is sentinel:
                sys.modules.pop("cas_engine", None)
            else:
                sys.modules["cas_engine"] = prior_engine
            if prior_math is sentinel:
                sys.modules.pop("math", None)
            else:
                sys.modules["math"] = prior_math
        self.assertEqual(result.legacy_artifact["result"]["dominant_state"], "C3")
        self.assertEqual(result.legacy_artifact["engine"], "python")
        self.assertEqual(
            result.legacy_artifact_sha256, baseline.legacy_artifact_sha256
        )
        self.assertEqual(
            result.execution_profile_sha256, baseline.execution_profile_sha256
        )

    def test_legacy_source_rejects_control_and_format_characters(self) -> None:
        for source in ("C1\nC2", "C1\u200d"):
            with self.subTest(source=repr(source)), self.assertRaisesRegex(
                CompatibilityError, "E-COMPAT-TEXT"
            ):
                LegacySourceEnvelope.bind(source)

    def test_legacy_artifact_is_immutable_and_uses_exact_numbers(self) -> None:
        result = compile_legacy_expression(
            LegacySourceEnvelope.bind("C1"), compiler_path=COMPILER
        )
        weight = next(iter(result.legacy_artifact["result"]["states"].values()))
        self.assertIsInstance(weight, Decimal)
        with self.assertRaises(TypeError):
            result.legacy_artifact["valid"] = False  # type: ignore[index]
        with self.assertRaises(TypeError):
            result.legacy_artifact["result"]["states"]["11"] = Decimal("0")  # type: ignore[index]

    def test_crlf_compiler_copy_at_path_with_spaces_is_the_same_content(self) -> None:
        normalized = COMPILER.read_bytes().replace(b"\r\n", b"\n")
        crlf_bytes = normalized.replace(b"\n", b"\r\n")
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "compiler path with spaces.py"
            path.write_bytes(crlf_bytes)
            result = compile_legacy_expression(
                LegacySourceEnvelope.bind("C1"), compiler_path=path
            )
        self.assertEqual(
            result.compiler_identity.raw_sha256,
            CAS_V77_COMPILER_RAW_CRLF_SHA256,
        )
        self.assertEqual(
            result.compiler_identity.canonical_lf_sha256,
            CAS_V77_COMPILER_CANONICAL_LF_SHA256,
        )

    def test_explicit_fractal_bridge_accepts_a_composable_catalog(self) -> None:
        x = FiniteObject("X", (0, 1))
        y = FiniteObject("Y", ("a", "b"))
        z = FiniteObject("Z", (False, True))
        first = FiniteArrow("nu1", x, y, (0, 1))
        second = FiniteArrow("nu2", y, z, (1, 0))
        path = bridge_legacy_fractal((1, 2), arrow_catalog={1: first, 2: second})
        self.assertEqual(path.source, x)
        self.assertEqual(path.target, z)
        self.assertEqual(path.composite().mapping, (1, 0))

    def test_explicit_fractal_bridge_rejects_missing_and_ill_typed_steps(self) -> None:
        x = FiniteObject("X", (0, 1))
        y = FiniteObject("Y", ("a", "b"))
        z = FiniteObject("Z", (False, True))
        first = FiniteArrow("nu1", x, y, (0, 1))
        wrong = FiniteArrow("nu2", z, x, (0, 1))
        with self.assertRaisesRegex(CompatibilityError, "UNMAPPED"):
            bridge_legacy_fractal((1, 2), arrow_catalog={1: first})
        with self.assertRaisesRegex(CompatibilityError, "FRACTAL-TYPE"):
            bridge_legacy_fractal((1, 2), arrow_catalog={1: first, 2: wrong})


if __name__ == "__main__":
    unittest.main()
