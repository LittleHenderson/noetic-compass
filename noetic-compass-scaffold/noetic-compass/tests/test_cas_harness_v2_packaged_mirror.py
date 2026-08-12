"""Fail-closed checks for the Docker-context CAS Harness v2 package mirror.

``src/cas_harness_v2`` remains canonical.  The application-local package exists
only because the production Docker context cannot read that repository-root
source tree.  Any source-file addition, removal, or byte drift must therefore
break this test until the mirror and its provenance record are updated together.
"""

from __future__ import annotations

import ast
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from api.services.cas_harness_v2_packaging import (
    HarnessV2PackagingError,
    PACKAGED_KERNEL_FILES,
    verify_packaged_harness_v2_kernel,
)


APP_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = APP_ROOT.parents[1]
CANONICAL_PACKAGE = REPOSITORY_ROOT / "src" / "cas_harness_v2"
PACKAGED_MIRROR = APP_ROOT / "cas_harness_v2"
PROVENANCE_PATH = PACKAGED_MIRROR / "PACKAGING_PROVENANCE.json"
PROVENANCE_SCHEMA = "cas_harness_v2.packaged_mirror_provenance.v1"
IGNORED_PARTS = {"__pycache__"}
IGNORED_SUFFIXES = {".pyc", ".pyo"}
PACKAGED_KERNEL_FILE_COUNT = 41
PACKAGED_KERNEL_EXPORT_COUNT = 1_242
PACKAGED_KERNEL_SOURCE_BYTES = 2_551_834
COMPARISON_MODULE_EXPORT_COUNTS = {
    "comparison_model_protocol": 58,
    "comparison_adapters": 12,
    "comparison_shared_protocol": 40,
    "comparison_shared_runner": 10,
    "comparison_prompt_injection_layers": 80,
    "surface_meaning_preservation": 45,
    "comparison_departure_metrics": 63,
    "comparison_steering_protocol": 53,
    "comparison_steering_effects": 34,
    "comparison_execution_boundary": 17,
    "universal_probe_contract": 108,
    "distributed_probe_contract": 60,
    "jspace_shadow_contract": 74,
    "historical_evidence_import": 21,
}
AMBIGUOUS_EXPORT_ALIASES = {
    ("comparison_prompt_injection_layers", "TOKEN_SCOPES"):
        "PROMPT_INJECTION_TOKEN_SCOPES",
    ("universal_probe_contract", "TOKEN_SCOPES"):
        "UNIVERSAL_PROBE_TOKEN_SCOPES",
    ("universal_probe_contract", "DTYPES"): "UNIVERSAL_PROBE_DTYPES",
    ("jspace_shadow_contract", "DTYPES"): "JSPACE_DTYPES",
}
AMBIGUOUS_RAW_EXPORTS = frozenset({"DTYPES", "TOKEN_SCOPES"})
RUNTIME_ACTIVATION_EXPORTS = (
    "STAGEC_RUNTIME_ACTIVATION_ERROR_CODES",
    "STAGEC_RUNTIME_ACTIVATION_INDETERMINATE",
    "STAGEC_RUNTIME_CONTROL_BOUNDARY",
    "STAGEC_RUNTIME_GATE_5_STATUS",
    "STAGEC_RUNTIME_INVALIDATION_REASONS",
    "STAGEC_RUNTIME_PERMIT_INDETERMINATE",
    "STAGEC_RUNTIME_PERMIT_INVALIDATED",
    "STAGEC_RUNTIME_PERMIT_REDEEMED",
    "STAGEC_RUNTIME_PERMIT_UNREDEEMED",
    "STAGEC_RUNTIME_PREPARED",
    "STAGEC_RUNTIME_PROJECT_STATUS",
    "STAGEC_RUNTIME_ROWS_ENABLED",
    "STAGEC_RUNTIME_SERIALIZED_AUTHORITY",
    "STAGEC_RUNTIME_STAGE_C_STATUS",
    "STAGEC_RUNTIME_STARTUP_CANARY",
    "StageCRuntimeActivationBackend",
    "StageCRuntimeActivationError",
    "ActivatedDiagnosticAttemptConsumption",
    "ActivatedDiagnosticPhaseCoordinator",
    "StageCRuntimeAmbiguousClaimTerminalObservation",
    "StageCRuntimeAttemptClaimExpectation",
    "StageCRuntimeAttemptClaimObservation",
    "StageCRuntimeAttemptInvalidationExpectation",
    "StageCRuntimeAttemptInvalidationObservation",
    "StageCRuntimeDispatchPermit",
    "StageCRuntimeIssuerAuthorizationObservation",
    "StageCRuntimeModelCaptureTarget",
    "StageCRuntimePhaseActivation",
    "StageCRuntimePhaseActivationExpectation",
    "StageCRuntimePhaseActivationObservation",
    "StageCRuntimePreparation",
    "StageCRuntimeStorageObservation",
    "StageCRuntimeWorkerLeaseObservation",
    "UnavailableStageCRuntimeActivationBackend",
    "activate_stagec_runtime_phase",
    "build_stagec_runtime_model_capture_target",
    "invalidate_stagec_runtime_attempt_claim",
    "mark_stagec_runtime_attempt_indeterminate",
    "prepare_stagec_runtime_activation",
    "redeem_stagec_runtime_dispatch_permit",
    "require_stagec_runtime_startup_canary",
    "stagec_runtime_dispatch_permit_state",
    "stagec_runtime_phase_state",
    "stagec_runtime_preparation_state",
)
STAGEC_EXTENSION_MODULE_EXPORT_COUNTS = {
    "diagnostic_stagec_historical_source_inventory": 14,
    "diagnostic_stagec_corpus_authoring_scaffold": 20,
    "diagnostic_stagec_runpod_authorization_v2": 44,
    "stagec_runpod_readonly_preflight": 47,
    "stagec_runpod_runner": 23,
}
STAGEC_EXTENSION_ALLOWED_EQUAL_COLLISIONS = frozenset(
    {
        "STAGEC_RUNPOD_MAXIMUM_AGGREGATE_SPEND_MICROUSD",
        "STAGEC_RUNPOD_POD_ID",
        "STAGEC_RUNPOD_POD_NAME",
    }
)


def _duplicate_rejecting_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_provenance() -> dict[str, Any]:
    value = json.loads(
        PROVENANCE_PATH.read_text(encoding="utf-8"),
        object_pairs_hook=_duplicate_rejecting_object,
        parse_constant=lambda value: (_ for _ in ()).throw(
            ValueError(f"non-finite JSON number: {value}")
        ),
    )
    assert type(value) is dict
    return value


def _package_files(root: Path, *, omit_provenance: bool = False) -> dict[str, Path]:
    files: dict[str, Path] = {}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in IGNORED_PARTS for part in relative.parts):
            continue
        if path.suffix in IGNORED_SUFFIXES:
            continue
        if omit_provenance and relative.as_posix() == PROVENANCE_PATH.name:
            continue
        files[relative.as_posix()] = path
    return files


def test_packaged_mirror_is_exactly_the_canonical_source_tree() -> None:
    canonical = _package_files(CANONICAL_PACKAGE)
    packaged = _package_files(PACKAGED_MIRROR, omit_provenance=True)

    assert canonical, "canonical cas_harness_v2 package is missing or empty"
    assert len(canonical) == PACKAGED_KERNEL_FILE_COUNT
    assert set(canonical) == set(PACKAGED_KERNEL_FILES)
    assert sum(path.stat().st_size for path in canonical.values()) == (
        PACKAGED_KERNEL_SOURCE_BYTES
    )
    assert set(packaged) == set(canonical), (
        "packaged cas_harness_v2 file set drifted: "
        f"missing={sorted(set(canonical) - set(packaged))}, "
        f"extra={sorted(set(packaged) - set(canonical))}"
    )
    for relative, source_path in canonical.items():
        assert packaged[relative].read_bytes() == source_path.read_bytes(), (
            f"packaged cas_harness_v2 bytes drifted for {relative}"
        )


def test_packaging_provenance_binds_every_canonical_source_byte() -> None:
    provenance = _load_provenance()
    assert set(provenance) == {
        "schema_version",
        "canonical_source_path",
        "packaged_destination_path",
        "copy_policy",
        "source_files",
        "authority_limitations",
    }
    assert provenance["schema_version"] == PROVENANCE_SCHEMA
    assert provenance["canonical_source_path"] == "src/cas_harness_v2"
    assert (
        provenance["packaged_destination_path"]
        == "noetic-compass-scaffold/noetic-compass/cas_harness_v2"
    )
    assert provenance["copy_policy"] == "BYTE_FOR_BYTE_SOURCE_MIRROR"
    authority_limitations = provenance["authority_limitations"]
    assert type(authority_limitations) is dict
    assert authority_limitations == {
        "canonical_source_remains_authoritative": True,
        "deployment_readiness": "NOT ESTABLISHED",
        "license_authority": "NOT GRANTED",
        "schema_fork_permitted": False,
    }
    assert type(authority_limitations["canonical_source_remains_authoritative"]) is bool
    assert type(authority_limitations["schema_fork_permitted"]) is bool
    assert type(authority_limitations["deployment_readiness"]) is str
    assert type(authority_limitations["license_authority"]) is str

    canonical = _package_files(CANONICAL_PACKAGE)
    recorded = provenance["source_files"]
    assert type(recorded) is dict
    assert len(recorded) == PACKAGED_KERNEL_FILE_COUNT
    assert sum(entry["size_bytes"] for entry in recorded.values()) == (
        PACKAGED_KERNEL_SOURCE_BYTES
    )
    assert set(recorded) == set(canonical), (
        "packaging provenance file set drifted: "
        f"missing={sorted(set(canonical) - set(recorded))}, "
        f"extra={sorted(set(recorded) - set(canonical))}"
    )
    for relative, source_path in canonical.items():
        payload = source_path.read_bytes()
        entry = recorded[relative]
        assert type(entry) is dict
        assert set(entry) == {"sha256", "size_bytes"}
        assert type(entry["size_bytes"]) is int
        assert entry["size_bytes"] == len(payload)
        assert type(entry["sha256"]) is str
        assert entry["sha256"] == hashlib.sha256(payload).hexdigest()


def test_packaged_mirror_import_resolves_inside_the_docker_context() -> None:
    probe = "\n".join(
        (
            "import sys",
            "from pathlib import Path",
            f"expected = Path({str(PACKAGED_MIRROR)!r}).resolve()",
            f"sys.path.insert(0, {str(APP_ROOT)!r})",
            "import cas_harness_v2",
            "actual = Path(cas_harness_v2.__file__).resolve().parent",
            "assert actual == expected, f'{actual} != {expected}'",
        )
    )
    completed = subprocess.run(
        [sys.executable, "-I", "-B", "-c", probe],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr


def test_packaged_public_modules_are_exported_exactly(tmp_path: Path) -> None:
    package_tree = ast.parse((CANONICAL_PACKAGE / "__init__.py").read_text())
    runtime_imports = [
        node
        for node in package_tree.body
        if isinstance(node, ast.ImportFrom)
        and node.module == "diagnostic_stagec_runtime_activation"
    ]
    assert len(runtime_imports) == 1
    assert all(
        alias.asname is None and alias.name != "*"
        for alias in runtime_imports[0].names
    )
    assert {alias.name for alias in runtime_imports[0].names} == set(
        RUNTIME_ACTIVATION_EXPORTS
    )
    stagec_extension_imports = [
        node
        for node in package_tree.body
        if isinstance(node, ast.ImportFrom)
        and node.level == 1
        and node.module is None
        and {alias.name for alias in node.names}
        == set(STAGEC_EXTENSION_MODULE_EXPORT_COUNTS)
    ]
    assert len(stagec_extension_imports) == 1
    assert tuple(alias.name for alias in stagec_extension_imports[0].names) == tuple(
        STAGEC_EXTENSION_MODULE_EXPORT_COUNTS
    )
    assert all(
        alias.asname == f"_{alias.name}"
        for alias in stagec_extension_imports[0].names
    )

    snapshot_payload = b'{"external":"candidate-snapshot"}\n'
    snapshot_path = tmp_path / "candidate.json"
    snapshot_path.write_bytes(snapshot_payload)
    probe = "\n".join(
        (
            "import importlib",
            "import sys",
            "from pathlib import Path",
            f"sys.path.insert(0, {str(APP_ROOT)!r})",
            "package = importlib.import_module('cas_harness_v2')",
            "provenance = importlib.import_module(",
            "    'cas_harness_v2.diagnostic_prompt_context_provenance'",
            ")",
            "inventory = importlib.import_module(",
            "    'cas_harness_v2.diagnostic_prompt_context_inventory'",
            ")",
            "prerequisite = importlib.import_module(",
            "    'cas_harness_v2.diagnostic_stagec_prerequisite_admission'",
            ")",
            "external = importlib.import_module(",
            "    'cas_harness_v2.diagnostic_stagec_prerequisite_external_intake'",
            ")",
            "runtime = importlib.import_module(",
            "    'cas_harness_v2.diagnostic_stagec_runtime_activation'",
            ")",
            f"comparison_export_counts = {COMPARISON_MODULE_EXPORT_COUNTS!r}",
            f"ambiguous_export_aliases = {AMBIGUOUS_EXPORT_ALIASES!r}",
            f"ambiguous_raw_exports = {AMBIGUOUS_RAW_EXPORTS!r}",
            f"stagec_extension_export_counts = {STAGEC_EXTENSION_MODULE_EXPORT_COUNTS!r}",
            "stagec_extension_allowed_equal_collisions = (",
            f"    {STAGEC_EXTENSION_ALLOWED_EQUAL_COLLISIONS!r}",
            ")",
            "comparison_modules = {",
            "    name: importlib.import_module(f'cas_harness_v2.{name}')",
            "    for name in comparison_export_counts",
            "}",
            "stagec_extension_modules = {",
            "    name: importlib.import_module(f'cas_harness_v2.{name}')",
            "    for name in stagec_extension_export_counts",
            "}",
            "artifacts = importlib.import_module('cas_harness_v2.artifacts')",
            "assert len(provenance.__all__) == len(set(provenance.__all__)) == 32",
            "assert len(inventory.__all__) == len(set(inventory.__all__)) == 11",
            "assert len(prerequisite.__all__) == len(set(prerequisite.__all__)) == 62",
            "assert len(external.__all__) == len(set(external.__all__)) == 20",
            f"assert tuple(runtime.__all__) == {RUNTIME_ACTIVATION_EXPORTS!r}",
            "assert len(runtime.__all__) == len(set(runtime.__all__)) == 44",
            "assert not [name for name in runtime.__all__ if name.endswith('_SCHEMA')]",
            "assert not [name for name in runtime.__all__ if name.endswith('_MEDIA_TYPE')]",
            f"assert len(package.__all__) == len(set(package.__all__)) == {PACKAGED_KERNEL_EXPORT_COUNT}",
            "assert not (ambiguous_raw_exports & set(package.__all__))",
            "assert not any(hasattr(package, name) for name in ambiguous_raw_exports)",
            "for module_name, module in comparison_modules.items():",
            "    assert len(module.__all__) == len(set(module.__all__))",
            "    assert len(module.__all__) == comparison_export_counts[module_name]",
            "    ordinary_exports = set(module.__all__) - ambiguous_raw_exports",
            "    assert ordinary_exports <= set(package.__all__)",
            "    assert all(",
            "        getattr(package, name) == getattr(module, name)",
            "        for name in ordinary_exports",
            "    )",
            "for (module_name, raw_name), alias in ambiguous_export_aliases.items():",
            "    assert alias in package.__all__",
            "    assert getattr(package, alias) is getattr(",
            "        comparison_modules[module_name], raw_name",
            "    )",
            "assert len([name for name in prerequisite.__all__ if name.endswith('_SCHEMA')]) == 18",
            "assert len([name for name in prerequisite.__all__ if name.endswith('_MEDIA_TYPE')]) == 18",
            "assert len([name for name in external.__all__ if name.endswith('_SCHEMA')]) == 3",
            "assert len([name for name in external.__all__ if name.endswith('_MEDIA_TYPE')]) == 3",
            "for module in (provenance, inventory, prerequisite, external, runtime):",
            "    assert set(module.__all__) <= set(package.__all__)",
            "    assert all(",
            "        getattr(package, name) is getattr(module, name)",
            "        for name in module.__all__",
            "    )",
            "assert {",
            "    name: len(module.__all__)",
            "    for name, module in stagec_extension_modules.items()",
            "} == stagec_extension_export_counts",
            "assert all(",
            "    len(module.__all__) == len(set(module.__all__))",
            "    for module in stagec_extension_modules.values()",
            ")",
            "stagec_extension_owners = {}",
            "for module_name, module in stagec_extension_modules.items():",
            "    for name in module.__all__:",
            "        stagec_extension_owners.setdefault(name, []).append(module_name)",
            "assert {",
            "    name",
            "    for name, owners in stagec_extension_owners.items()",
            "    if len(owners) > 1",
            "} == stagec_extension_allowed_equal_collisions",
            "assert all(",
            "    len(stagec_extension_owners[name]) == 2",
            "    for name in stagec_extension_allowed_equal_collisions",
            ")",
            "for module in stagec_extension_modules.values():",
            "    for name in module.__all__:",
            "        assert name in package.__all__",
            "        if name in stagec_extension_allowed_equal_collisions:",
            "            assert getattr(package, name) == getattr(module, name)",
            "        else:",
            "            assert getattr(package, name) is getattr(module, name)",
            f"payload = {snapshot_payload!r}",
            f"source = Path({str(snapshot_path)!r})",
            "evidence_file = artifacts.EvidenceFile.from_path(",
            "    'packaged-external-candidate-snapshot',",
            "    source,",
            "    maximum_byte_count=len(payload),",
            ")",
            "snapshot = evidence_file.snapshot_bytes(maximum_byte_count=len(payload))",
            "assert snapshot.raw_bytes == payload",
            "assert snapshot.sha256 == evidence_file.sha256",
            "assert snapshot.byte_length == evidence_file.byte_length == len(payload)",
            "assert package.EvidenceFile is artifacts.EvidenceFile",
        )
    )
    completed = subprocess.run(
        [sys.executable, "-I", "-B", "-c", probe],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr


def test_packaged_kernel_verifier_accepts_the_exact_packaged_mirror() -> None:
    expected_provenance_sha256 = hashlib.sha256(
        PROVENANCE_PATH.read_bytes()
    ).hexdigest().upper()

    assert (
        verify_packaged_harness_v2_kernel(PACKAGED_MIRROR)
        == expected_provenance_sha256
    )


@pytest.mark.parametrize(
    ("mutation", "expected_fragment"),
    [
        ("byte_drift", "source file differs from provenance"),
        ("provenance_drift", "provenance authority boundary changed"),
        ("duplicate_provenance_key", "provenance record is invalid"),
        ("extra_python_surface", "Python surface differs from provenance"),
    ],
)
def test_packaged_kernel_verifier_rejects_temporary_copy_mutations(
    tmp_path: Path,
    mutation: str,
    expected_fragment: str,
) -> None:
    package_copy = tmp_path / "cas_harness_v2"
    shutil.copytree(PACKAGED_MIRROR, package_copy)
    provenance_path = package_copy / PROVENANCE_PATH.name

    if mutation == "byte_drift":
        source_path = package_copy / "__init__.py"
        source_path.write_bytes(source_path.read_bytes() + b"# drift\n")
    elif mutation == "provenance_drift":
        provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
        provenance["copy_policy"] = "UNBOUND_COPY"
        provenance_path.write_text(json.dumps(provenance), encoding="utf-8")
    elif mutation == "duplicate_provenance_key":
        raw = provenance_path.read_text(encoding="utf-8")
        duplicate = '"schema_version": "duplicate",\n  "schema_version":'
        provenance_path.write_text(
            raw.replace('"schema_version":', duplicate, 1),
            encoding="utf-8",
        )
    else:
        (package_copy / "unexpected.py").write_text("# extra surface\n", encoding="utf-8")

    with pytest.raises(HarnessV2PackagingError, match=expected_fragment):
        verify_packaged_harness_v2_kernel(package_copy)


def test_api_dockerfile_copies_and_import_probes_the_packaged_mirror() -> None:
    dockerfile = (APP_ROOT / "Dockerfile.api").read_text(encoding="utf-8")
    assert dockerfile.count("COPY cas_harness_v2/ cas_harness_v2/") == 1
    assert dockerfile.count("verify_packaged_harness_v2_kernel()") == 1
    assert dockerfile.count("import cas_harness_v2") == 1
    assert dockerfile.index("verify_packaged_harness_v2_kernel()") < dockerfile.index(
        "import cas_harness_v2"
    )
    assert "Path('/app/cas_harness_v2')" in dockerfile


@pytest.mark.parametrize(
    ("mutation", "expected_fragment"),
    [
        ("missing", "file set drifted"),
        ("extra", "file set drifted"),
        ("changed", "bytes drifted"),
    ],
)
def test_parity_contract_is_fail_closed(
    tmp_path: Path,
    mutation: str,
    expected_fragment: str,
) -> None:
    """Exercise the comparison semantics, not merely the current happy path."""

    source = tmp_path / "source"
    mirror = tmp_path / "mirror"
    source.mkdir()
    mirror.mkdir()
    (source / "module.py").write_bytes(b"canonical\n")
    (mirror / "module.py").write_bytes(b"canonical\n")

    if mutation == "missing":
        (mirror / "module.py").unlink()
    elif mutation == "extra":
        (mirror / "extra.py").write_bytes(b"unexpected\n")
    else:
        (mirror / "module.py").write_bytes(b"changed\n")

    source_files = _package_files(source)
    mirror_files = _package_files(mirror)
    with pytest.raises(AssertionError, match=expected_fragment):
        assert set(mirror_files) == set(source_files), "file set drifted"
        for relative, source_path in source_files.items():
            assert mirror_files[relative].read_bytes() == source_path.read_bytes(), (
                "bytes drifted"
            )
