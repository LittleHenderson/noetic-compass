#!/usr/bin/env python3
"""Verify the Project Coherence Gate 5 research-control candidate.

This verifier is deliberately non-promotional.  A PASS proves only the exact
repository identities, regression receipts, preserved negative evidence, and
OPEN boundaries encoded below.  It cannot close Gate 5, authenticate an
experiment, license a claim, authorize disclosure, or establish product
readiness.
"""

from __future__ import annotations

import sys

if __name__ == "__main__" and not sys.flags.isolated:
    raise SystemExit(
        "Authoritative Gate 5 verification requires isolated Python; run "
        "`python -I -B scripts/verify_project_coherence_gate5.py`."
    )
if __name__ != "__main__" and (
    not sys.flags.safe_path or not sys.flags.ignore_environment
):
    raise SystemExit(
        "Imported Gate 5 verification controls require `python -E -P` or isolated mode."
    )

import ast
from dataclasses import dataclass
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import stat
import subprocess
import tarfile
import tempfile
from types import MappingProxyType
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
FILESYSTEM_ANCHOR = Path(ROOT.anchor)
PROJECT_COHERENCE_DIR = ROOT / "docs" / "working" / "project_coherence"
GATE5_DIR = PROJECT_COHERENCE_DIR / "gate5"
MANIFEST_PATH = GATE5_DIR / "GATE5_ARTIFACT_MANIFEST_v0.1.json"
REVIEW_MATRIX_PATH = GATE5_DIR / "GATE5_REVIEW_MATRIX_v0.1.json"
ADVERSARIAL_REVIEW_PATH = GATE5_DIR / "GATE5_ADVERSARIAL_REVIEW_v0.1.md"
CLAIM_LEDGER_PATH = PROJECT_COHERENCE_DIR / "CLAIM_LEDGER_v0.1.json"
GATE4_MANIFEST_PATH = (
    PROJECT_COHERENCE_DIR / "gate4" / "GATE4_ARTIFACT_MANIFEST_v0.1.json"
)
HISTORY_MANIFEST_PATH = (
    GATE5_DIR / "history" / "HISTORICAL_HARNESS_V1_V4_CURRENT_TREE_SHA256.json"
)
HISTORY_INVENTORY_PATH = (
    GATE5_DIR / "history" / "HISTORICAL_HARNESS_V1_V4_RECOVERY_INVENTORY.md"
)
MODEL_DEPENDENCY_BINDING_PATH = (
    GATE5_DIR / "GATE5_MODEL_AND_DEPENDENCY_BINDING_v0.1.json"
)
HISTORICAL_MODEL_DEPENDENCY_BINDING_SHA256 = (
    "A24F27AE6678A8EAAECA5E516805F94F394B416054AB5BCDAA68B687B0B79E2B"
)
CANDIDATE_RECEIPT_PATH = (
    GATE5_DIR / "GATE5_DEPENDENCY_AND_CONTAINER_CANDIDATE_RECEIPT_v0.2.json"
)
RAW_BUILD_SECURITY_RECEIPT_PATH = (
    GATE5_DIR / "GATE5_RAW_BUILD_AND_SECURITY_EVIDENCE_RECEIPT_v0.1.json"
)
ENGINEERING_EXECUTION_RECONCILIATION_PATH = (
    GATE5_DIR / "GATE5_ENGINEERING_EXECUTION_RECONCILIATION_v0.1.json"
)
HISTORICAL_CAPABILITY_RECONCILIATION_PATH = (
    GATE5_DIR / "history" / "HISTORICAL_CAPABILITY_EVIDENCE_RECONCILIATION_v0.1.json"
)
SHADOW_SCANNER_SOURCE_COMMIT = "75898e8efde0564587f8b9f114eac2f96f256a6a"
RAW_EVIDENCE_DIR = (
    GATE5_DIR / "evidence" / "raw" / "candidate_v0.2_20260805"
)
RUNNER_LOCK_PATH = (
    GATE5_DIR / "GATE5_LOCAL_WINDOWS_TEST_RUNNER_LOCK_v0.1.json"
)
SAME_RUN_PYTEST_RUNNER_PATH = ROOT / "scripts" / "run_project_coherence_gate5_pytest.py"
RUNNER_LOCK_BUILDER_PATH = (
    ROOT / "scripts" / "build_project_coherence_gate5_runner_lock.py"
)

SHA256_UPPER_RE = re.compile(r"^[A-F0-9]{64}$")
SHA256_LOWER_RE = re.compile(r"^[a-f0-9]{64}$")
OCI_SHA256_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
WINDOWS_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:[/\\]")
BOUNDARY_RE = re.compile(r"^\[([A-Z0-9-]+)\] ")
TEST_ID_CANONICALIZATION = (
    "SAME-PROCESS EXECUTED-NODE SHA-256 over ordinal-sorted unique pytest node "
    "IDs normalized only to POSIX slashes, encoded UTF-8 as one ID plus LF per "
    "line; collection, start, finish, and all-pass outcomes are bound in one "
    "local subprocess receipt"
)

WORKER_ROOT_REL = "noetic-compass-scaffold/noetic-compass/live-trace-worker"
WORKER_ROOT = ROOT / WORKER_ROOT_REL
API_ROOT_REL = "noetic-compass-scaffold/noetic-compass"

# These are the exact launcher/API entrypoints and tests for the cross-process
# identity receipt.  Their complete in-repository API runtime dependency and
# resource surface is bound separately below so the receipt is source-closed
# even when an import is dynamic or a module reads a non-Python resource.
EXACT_API_LAUNCHER_SURFACE = {
    f"{API_ROOT_REL}/api/routes/cas_harness_audit.py",
    f"{API_ROOT_REL}/api/services/cas_harness_fleet_executor.py",
    f"{API_ROOT_REL}/scripts/prepare_large_model_eval.py",
    f"{API_ROOT_REL}/scripts/test_prepare_large_model_eval.py",
    f"{API_ROOT_REL}/tests/test_cas_harness_fleet_executor.py",
    f"{API_ROOT_REL}/tests/test_cas_harness_fleet_executor_contract.py",
    f"{API_ROOT_REL}/tests/test_cas_harness_v2_worker_bridge.py",
    f"{API_ROOT_REL}/tests/test_cas_harness_v2_run_lifecycle.py",
    f"{API_ROOT_REL}/tests/test_cas_harness_v2_lifecycle_service.py",
    f"{API_ROOT_REL}/tests/test_cas_harness_v2_worker_protocol_routes.py",
    f"{API_ROOT_REL}/tests/test_cas_harness_v2_packaged_mirror.py",
    f"{API_ROOT_REL}/tests/test_cas_harness_v2_fleet_snapshot_loader.py",
    f"{API_ROOT_REL}/tests/test_cas_harness_v2_route_envelopes.py",
    f"{API_ROOT_REL}/tests/test_cas_harness_v2_run_context.py",
    f"{API_ROOT_REL}/tests/test_cas_harness_v2_worker_protocol_adapter.py",
    f"{API_ROOT_REL}/tests/test_cas_harness_v2_reconciliation_report.py",
    f"{API_ROOT_REL}/tests/object_lock_test_support.py",
    f"{API_ROOT_REL}/tests/test_fleet_service_auth.py",
    f"{API_ROOT_REL}/tests/test_evidence_packet_object_store.py",
    f"{API_ROOT_REL}/tests/test_state_ledger_operational_enable.py",
    f"{API_ROOT_REL}/tests/test_state_substrate_sqlite.py",
    f"{API_ROOT_REL}/tests/test_state_substrate_live_migration.py",
}
API_RUNTIME_SURFACE_DIR = f"{API_ROOT_REL}/api"

REQUIRED_CONTROL_ARTIFACTS = {
    ".gitattributes",
    "docs/working/project_coherence/CHANGELOG.md",
    "docs/working/project_coherence/CLAIM_LEDGER_v0.1.json",
    "docs/working/project_coherence/PROJECT_COHERENCE_MASTER_CHARTER_v0.1.md",
    "docs/working/project_coherence/OPEN_VS_HELD_BOUNDARY_v0.1.md",
    "docs/working/project_coherence/gate4/GATE4_ARTIFACT_MANIFEST_v0.1.json",
    "docs/working/project_coherence/gate5/README.md",
    "docs/working/project_coherence/gate5/HARNESS_V2_PREREGISTRATION_AND_EVIDENCE_PACKET_V2_SPEC_v0.1.md",
    "docs/working/project_coherence/gate5/GATE5_WORKER_PROTOCOL_BINDING_v0.1.md",
    "docs/working/project_coherence/gate5/GATE5_REVIEW_MATRIX_v0.1.json",
    "docs/working/project_coherence/gate5/GATE5_ADVERSARIAL_REVIEW_v0.1.md",
    "docs/working/project_coherence/gate5/GATE5_MODEL_AND_DEPENDENCY_BINDING_v0.1.json",
    "docs/working/project_coherence/gate5/GATE5_DEPENDENCY_AND_CONTAINER_CANDIDATE_RECEIPT_v0.2.json",
    "docs/working/project_coherence/gate5/GATE5_RAW_BUILD_AND_SECURITY_EVIDENCE_RECEIPT_v0.1.json",
    "docs/working/project_coherence/gate5/GATE5_ENGINEERING_EXECUTION_RECONCILIATION_v0.1.json",
    "docs/working/project_coherence/gate5/history/HISTORICAL_CAPABILITY_EVIDENCE_RECONCILIATION_v0.1.json",
    "docs/working/project_coherence/gate5/GATE5_LOCAL_WINDOWS_TEST_RUNNER_LOCK_v0.1.json",
    "docs/working/project_coherence/gate5/history/HISTORICAL_HARNESS_V1_V4_CURRENT_TREE_SHA256.json",
    "docs/working/project_coherence/gate5/history/HISTORICAL_HARNESS_V1_V4_RECOVERY_INVENTORY.md",
    "scripts/verify_project_coherence_gate5.py",
    "scripts/build_project_coherence_gate5_manifest.py",
    "scripts/build_project_coherence_gate5_runner_lock.py",
    "scripts/run_project_coherence_gate5_pytest.py",
    "scripts/run_project_coherence_gate5_local_gpu_canary.py",
    "scripts/run_project_coherence_gate5_joined_local_gpu_smoke.py",
    "tests/model_smoke/test_gate5_local_gpu_canary.py",
    "tests/model_smoke/test_gate5_joined_local_gpu_smoke.py",
    "docs/working/cas_harness_instruction_integrity_spec.md",
    "docs/working/cas_harness_research_only_steering_plan.md",
    f"{API_ROOT_REL}/api/routes/evidence.py",
    f"{API_ROOT_REL}/api/services/cas_harness_instruction_integrity.py",
    f"{API_ROOT_REL}/api/services/cas_harness_instruction_integrity_benchmark.py",
    f"{API_ROOT_REL}/scenarios/instruction_integrity_benchmark_v0.json",
    f"{API_ROOT_REL}/scenarios/instruction_integrity_heldout_v0.json",
    f"{API_ROOT_REL}/scripts/run_instruction_integrity_benchmark.py",
    f"{API_ROOT_REL}/tests/test_cas_harness_instruction_integrity.py",
    f"{API_ROOT_REL}/tests/test_cas_harness_instruction_integrity_benchmark.py",
    f"{API_ROOT_REL}/tests/test_evidence_routes.py",
    f"{WORKER_ROOT_REL}/Dockerfile",
    f"{WORKER_ROOT_REL}/.dockerignore",
    f"{WORKER_ROOT_REL}/requirements.in",
    f"{WORKER_ROOT_REL}/requirements.txt",
    f"{API_ROOT_REL}/Dockerfile.api",
    "noetic-compass-scaffold/noetic-compass/pyproject.toml",
}

# Every regular file under these admitted roots can affect the verified
# kernels or worker regressions and therefore must be hash-bound.  This is
# deliberately broader than ``*.py`` so a future resource, extension, archive,
# or configuration file cannot appear outside the manifest.
EXACT_ALL_FILE_SURFACE_DIRS = (
    "src/cas_harness_v2",
    "src/cas_core_v8",
    "tests/cas_harness_v2",
    f"{API_ROOT_REL}/cas_harness_v2",
    f"{WORKER_ROOT_REL}/app",
    f"{WORKER_ROOT_REL}/scripts",
    f"{WORKER_ROOT_REL}/tests",
)
EXACT_PYTHON_SURFACE_DIRS = EXACT_ALL_FILE_SURFACE_DIRS
EXACT_DATA_SURFACES = (
    (f"{WORKER_ROOT_REL}/scenarios", "*.json"),
    (f"{WORKER_ROOT_REL}/scripts", "*.sh"),
)

# Python can import sourceless bytecode, native extensions, and archives.  None
# are admitted on the repository-local Gate 5 execution surfaces.  The
# authoritative verifier rejects them before launching either pytest process.
FORBIDDEN_EXECUTABLE_SHADOW_SUFFIXES = {
    ".dll",
    ".egg",
    ".pyc",
    ".pyd",
    ".pyo",
    ".so",
    ".zip",
}
EXECUTABLE_SHADOW_SCAN_DIRS = tuple(
    dict.fromkeys(
        (
            *EXACT_ALL_FILE_SURFACE_DIRS,
            API_ROOT_REL,
            API_RUNTIME_SURFACE_DIR,
            f"{API_ROOT_REL}/tests",
            f"{API_ROOT_REL}/scripts",
            "docs/working/project_coherence/gate5",
            "scripts",
            "tests",
        )
    )
)

# Pytest discovers configuration and conftest files in the target directories
# and every ancestor up to its rootdir.  Bind every filename that can alter the
# two admitted collection/execution paths, including candidates that do not yet
# exist (a future addition then changes the required surface and fails closed).
PYTEST_ENVIRONMENT_DIRS = (
    ".",
    "tests",
    "tests/cas_harness_v2",
    "noetic-compass-scaffold",
    "noetic-compass-scaffold/noetic-compass",
    f"{API_ROOT_REL}/tests",
    f"{API_ROOT_REL}/scripts",
    WORKER_ROOT_REL,
    f"{WORKER_ROOT_REL}/tests",
)
PYTEST_ENVIRONMENT_FILENAMES = (
    "conftest.py",
    "pytest.ini",
    ".pytest.ini",
    "pyproject.toml",
    "tox.ini",
    "setup.cfg",
    "__init__.py",
)
PYTEST_ENVIRONMENT_CANDIDATE_PATHS = {
    filename if directory == "." else f"{directory}/{filename}"
    for directory in PYTEST_ENVIRONMENT_DIRS
    for filename in PYTEST_ENVIRONMENT_FILENAMES
}
PYTEST_ISOLATION_ENV = {
    "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
    "PYTEST_ADDOPTS": "",
    "PYTEST_PLUGINS": "",
}
PYTEST_REMOVED_ENV = ("PYTHONPATH", "PYTHONHOME")
SUBPROCESS_ENV_ALLOWLIST = {
    "APPDATA",
    "COMSPEC",
    "HOME",
    "LOCALAPPDATA",
    "PATH",
    "PATHEXT",
    "SYSTEMDRIVE",
    "SYSTEMROOT",
    "TEMP",
    "TMP",
    "USERPROFILE",
    "WINDIR",
}
GIT_SAFE_DIRECTORY = ROOT.resolve().as_posix()

REQUIRED_BOUNDARY_TEXT = {
    "G5-OPEN-GATE4": "Gate 4 remains OPEN and cannot be promoted by dependency verification.",
    "G5-OPEN-TRUSTED-TIME": "No independently trusted time source binds ordering.",
    "G5-OPEN-TRUST-ROOT": "No non-caller-selected identity or signing trust root exists.",
    "G5-OPEN-WORM": "The existing Object-Lock packet repository does not yet bind the complete v2 preregistration, authorization, outcome-access, terminal, and packet order under independent authority.",
    "G5-OPEN-NONCE-REPLAY": "Bounded callback and run-nonce replay controls do not establish authenticated restart-, replica-, or host-loss-resistant rejection.",
    "G5-OPEN-ONE-USE": "Same-host atomic one-use v2 authorization and consumption are tested, but live independently authenticated multi-host durability is not established.",
    "G5-OPEN-SELECTIVE-REPORTING": "Configured-scope reconciliation cannot establish an exhaustive cross-host registry or prove off-registry execution absence.",
    "G5-OPEN-AUTHENTICATED-EXECUTION": "No independently authenticated execution receipt exists.",
    "G5-OPEN-HERMETICITY": "The OS, toolchain, dependencies, inputs, and runtime are not hermetically attested.",
    "G5-OPEN-SEMANTIC-VALIDATION": "Artifact hashes do not establish semantic correctness.",
    "G5-OPEN-DEPENDENCY-SECURITY": "The Transformers and container security hold remains open.",
    "G5-OPEN-LIVE-EXPERIMENT": "No authorized exact-revision Harness v2 experiment has started.",
    "G5-OPEN-REAL-INDEPENDENCE": "Declared roles do not prove real identity, affiliation, or independence.",
    "G5-OPEN-GPU-NUMERICS": "GPU, autocast, compiled-hook, and multi-device numerics are unverified.",
    "G5-OPEN-MATCHED-CONTROLS": "Required matched controls and falsifiers have not run under v2.",
    "G5-OPEN-INDEPENDENT-NUMERICAL-AUDIT": "No independent numerical audit has agreed with a live v2 run.",
    "G5-OPEN-REPLICATION": "No held-out independent replication has been completed.",
    "G5-OPEN-PEER-REVIEW": "External specialist peer review remains outstanding.",
    "G5-OPEN-CLAIM-REVIEW": "Exact claim-language review remains outstanding.",
    "G5-OPEN-DOWNSTREAM-AUTHORITY": "Downstream systems have not proved that packet data cannot mint authority.",
    "G5-OPEN-PRODUCT-READINESS": "Product, security, operations, billing, privacy, and compliance readiness remain separate open gates.",
    "G5-OPEN-DISCLOSURE": "Owner and qualified legal, patent, privacy, and disclosure authorization are absent.",
}
REQUIRED_OPEN_BOUNDARY_IDS = set(REQUIRED_BOUNDARY_TEXT)

BOUNDARY_CRITERION_BINDINGS = {
    "G5-OPEN-GATE4": {"G5-INTEGRATION-002"},
    "G5-OPEN-TRUSTED-TIME": {"G5-TRUST-001"},
    "G5-OPEN-TRUST-ROOT": {"G5-TRUST-005"},
    "G5-OPEN-WORM": {"G5-TRUST-002"},
    "G5-OPEN-NONCE-REPLAY": {"G5-TRUST-003"},
    "G5-OPEN-ONE-USE": {"G5-TRUST-003"},
    "G5-OPEN-SELECTIVE-REPORTING": {"G5-TRUST-004"},
    "G5-OPEN-AUTHENTICATED-EXECUTION": {"G5-TRUST-005"},
    "G5-OPEN-HERMETICITY": {"G5-ENGINEERING-002"},
    "G5-OPEN-SEMANTIC-VALIDATION": {
        "G5-ENGINEERING-005",
        "G5-SCIENCE-002",
        "G5-SCIENCE-006",
    },
    "G5-OPEN-DEPENDENCY-SECURITY": {"G5-ENGINEERING-003"},
    "G5-OPEN-LIVE-EXPERIMENT": {"G5-SCIENCE-001"},
    "G5-OPEN-REAL-INDEPENDENCE": {"G5-TRUST-006", "G5-SCIENCE-007"},
    "G5-OPEN-GPU-NUMERICS": {"G5-SCIENCE-009"},
    "G5-OPEN-MATCHED-CONTROLS": {"G5-SCIENCE-003"},
    "G5-OPEN-INDEPENDENT-NUMERICAL-AUDIT": {"G5-SCIENCE-004"},
    "G5-OPEN-REPLICATION": {"G5-SCIENCE-005"},
    "G5-OPEN-PEER-REVIEW": {"G5-SCIENCE-008"},
    "G5-OPEN-CLAIM-REVIEW": {"G5-SCIENCE-008"},
    "G5-OPEN-DOWNSTREAM-AUTHORITY": {"G5-ENGINEERING-006"},
    "G5-OPEN-PRODUCT-READINESS": {"G5-GOV-001"},
    "G5-OPEN-DISCLOSURE": {"G5-GOV-002"},
}

REQUIRED_IMPLEMENTED_CRITERION_IDS = {
    *(f"G5-KERNEL-{index:03d}" for index in range(1, 16)),
    "G5-WORKER-001",
    "G5-WORKER-002",
    "G5-WORKER-003",
    "G5-HISTORY-001",
    "G5-INTEGRATION-001",
    "G5-ENGINEERING-004",
    "G5-ENGINEERING-007",
    "G5-ENGINEERING-008",
    "G5-ENGINEERING-009",
}
REQUIRED_NEGATIVE_CRITERION_IDS = {"G5-HISTORY-002"}

OPEN_REVIEW_DISPOSITIONS = {
    "OPEN_ENGINEERING",
    "OPEN_SECURITY",
    "OPEN_GOVERNANCE",
    "OPEN_EXTERNAL_VALIDATION",
}
REVIEW_DISPOSITIONS = OPEN_REVIEW_DISPOSITIONS | {
    "IMPLEMENTED_AND_REGRESSION_TESTED",
    "IMPLEMENTED_AND_HASH_VERIFIED",
    "PRESERVED_NEGATIVE_EVIDENCE",
}

REQUIRED_TEST_SUITES: dict[str, dict[str, Any]] = {
    "Harness v2 kernel and history": {
        "working_directory": ".",
        "targets": ["tests/cas_harness_v2"],
        "pytest_plugins": [],
        "repo_import_roots": ["src", "tests/cas_harness_v2"],
        "expected_tests": 155,
        "expected_subtests": 106,
        "expected_test_ids_sha256": (
            "CF033F2E7F519AAD6738D596A694728FD4173CFA12DD8A8FE094823215D4CF8A"
        ),
    },
    "Live trace worker complete": {
        "working_directory": WORKER_ROOT_REL,
        "targets": ["tests"],
        "pytest_plugins": ["pytest_asyncio.plugin"],
        "repo_import_roots": [f"{WORKER_ROOT_REL}/scripts", API_ROOT_REL],
        "expected_tests": 391,
        "expected_subtests": 0,
        "expected_test_ids_sha256": (
            "FD8367B867CB6589CC50424D7A1CECABC56BF85331BB4FD87B844E7FD3004580"
        ),
    },
    "Live trace worker numeric red team": {
        "working_directory": WORKER_ROOT_REL,
        "targets": ["tests/test_eraser_numeric_redteam.py"],
        "pytest_plugins": ["pytest_asyncio.plugin"],
        "repo_import_roots": [],
        "expected_tests": 32,
        "expected_subtests": 0,
        "expected_test_ids_sha256": (
            "12602041756F20D1AFD402FA56968660839E5EB1098438BA84C69BFF8DE7050B"
        ),
    },
    "API, fleet state, and launcher identity": {
        "working_directory": API_ROOT_REL,
        "targets": [
            "scripts/test_prepare_large_model_eval.py",
            "tests/test_cas_harness_fleet_executor.py",
            "tests/test_cas_harness_fleet_executor_contract.py",
            "tests/test_state_ledger_operational_enable.py",
            "tests/test_state_substrate_live_migration.py",
        ],
        "pytest_plugins": ["pytest_asyncio.plugin"],
        "repo_import_roots": [f"{API_ROOT_REL}/scripts"],
        "expected_tests": 78,
        "expected_subtests": 0,
        "expected_test_ids_sha256": (
            "603DEBF7DF9AC7B5A69543C3736F4CD38692D3330690A7559A6F9DE6F0E2AF77"
        ),
    },
    "Durable fleet callback and Object-Lock repository seams": {
        "working_directory": API_ROOT_REL,
        "targets": [
            "tests/test_fleet_service_auth.py",
            "tests/test_evidence_packet_object_store.py",
        ],
        "pytest_plugins": ["pytest_asyncio.plugin"],
        "repo_import_roots": [],
        "expected_tests": 38,
        "expected_subtests": 0,
        "expected_test_ids_sha256": (
            "D3EAF533FEDB5B03168200AA399AC53A6E2A6F22874EBABEAECEFB227400778D"
        ),
    },
    "Harness v2 worker terminal bridge": {
        "working_directory": API_ROOT_REL,
        "targets": ["tests/test_cas_harness_v2_worker_bridge.py"],
        "pytest_plugins": ["pytest_asyncio.plugin"],
        "repo_import_roots": ["src", "tests/cas_harness_v2"],
        "expected_tests": 17,
        "expected_subtests": 0,
        "expected_test_ids_sha256": (
            "FA6C985CD6CAA734034E006BB4BAF6BE9D02269D7312BEE7355E9C3833759C51"
        ),
    },
    "Harness v2 prospective lifecycle, SQLite, and dark route": {
        "working_directory": API_ROOT_REL,
        "targets": [
            "tests/test_state_substrate_sqlite.py",
            "tests/test_cas_harness_v2_run_lifecycle.py",
            "tests/test_cas_harness_v2_lifecycle_service.py",
            "tests/test_cas_harness_v2_worker_protocol_routes.py",
        ],
        "pytest_plugins": [],
        "repo_import_roots": [
            "src",
            "tests/cas_harness_v2",
            f"{API_ROOT_REL}/tests",
        ],
        "expected_tests": 134,
        "expected_subtests": 0,
        "expected_test_ids_sha256": (
            "67F7507579749E11E27714E8513F6909E26A503A8DD18112CC402207D9735940"
        ),
    },
    "Harness v2 admitted adapter and bounded reconciliation": {
        "working_directory": API_ROOT_REL,
        "targets": [
            "tests/test_cas_harness_v2_packaged_mirror.py",
            "tests/test_cas_harness_v2_fleet_snapshot_loader.py",
            "tests/test_cas_harness_v2_route_envelopes.py",
            "tests/test_cas_harness_v2_run_context.py",
            "tests/test_cas_harness_v2_worker_protocol_adapter.py",
            "tests/test_cas_harness_v2_reconciliation_report.py",
        ],
        "pytest_plugins": [],
        "repo_import_roots": [
            "src",
            "tests/cas_harness_v2",
            f"{API_ROOT_REL}/tests",
        ],
        "expected_tests": 98,
        "expected_subtests": 0,
        "expected_test_ids_sha256": (
            "65352B8B59CB654E449BA4A1CE8459D7109CC5B21E33F64AEAB6E2EA6EEB3C19"
        ),
    },
    "Gate 5 retained local GPU and joined evidence": {
        "working_directory": ".",
        "targets": [
            "tests/model_smoke/test_gate5_local_gpu_canary.py",
            "tests/model_smoke/test_gate5_joined_local_gpu_smoke.py",
        ],
        "pytest_plugins": [],
        "repo_import_roots": ["src", API_ROOT_REL],
        "expected_tests": 27,
        "expected_subtests": 0,
        "expected_test_ids_sha256": (
            "DC0C0ED22E0F158F014277B9D3CD26AD21D6A8FCDFBE1E76A67D09406975C952"
        ),
    },
    "Instruction-integrity shadow scanner": {
        "working_directory": API_ROOT_REL,
        "targets": [
            "tests/test_cas_harness_instruction_integrity.py",
            "tests/test_cas_harness_instruction_integrity_benchmark.py",
        ],
        "pytest_plugins": [],
        "repo_import_roots": [],
        "expected_tests": 12,
        "expected_subtests": 0,
        "expected_test_ids_sha256": (
            "822FD7113370AC9BB6C2DAFAF0BC33507A199860FA8F47F7C1DE35E880ABEDEE"
        ),
    },
}

# This receipt predates later Gate 5 test-suite expansion.  Keep it immutable
# and self-contained so editing today's REQUIRED_TEST_SUITES cannot rewrite or
# invalidate evidence already issued for the dependency/container candidate.
HISTORICAL_DEPENDENCY_CONTAINER_CANDIDATE_TEST_RECEIPT = MappingProxyType(
    {
        "live_trace_worker_complete": MappingProxyType(
            {
                "passed": 364,
                "failed": 0,
                "total": 364,
                "test_ids_sha256": (
                    "94566203B3E0FF79B3224C1C5A073698CA99D3C08BC1119A9082E42AF4B178BD"
                ),
            }
        ),
        "api_launcher_fleet_state": MappingProxyType(
            {
                "passed": 76,
                "failed": 0,
                "total": 76,
                "test_ids_sha256": (
                    "1ED1E9E3AFA2EDA6881463EE5284DD4902AB94C0246B80D2937066480AC42921"
                ),
                "targets": (
                    "noetic-compass-scaffold/noetic-compass/scripts/"
                    "test_prepare_large_model_eval.py",
                    "noetic-compass-scaffold/noetic-compass/tests/"
                    "test_cas_harness_fleet_executor.py",
                    "noetic-compass-scaffold/noetic-compass/tests/"
                    "test_cas_harness_fleet_executor_contract.py",
                    "noetic-compass-scaffold/noetic-compass/tests/"
                    "test_state_ledger_operational_enable.py",
                    "noetic-compass-scaffold/noetic-compass/tests/"
                    "test_state_substrate_live_migration.py",
                ),
            }
        ),
        "receipt_scope": (
            "LOCAL_UNATTESTED_HOST_REGRESSION / SEPARATE COLLECT-ONLY NODE-ID "
            "DIGEST / ACTUAL EXECUTED IDS NOT RECEIPTED / NOT GPU EXECUTION / "
            "NOT SCIENTIFIC EVIDENCE"
        ),
    }
)


def _historical_dependency_container_candidate_test_receipt() -> dict[str, Any]:
    """Return the JSON-shaped copy used to verify the historical receipt."""

    worker = HISTORICAL_DEPENDENCY_CONTAINER_CANDIDATE_TEST_RECEIPT[
        "live_trace_worker_complete"
    ]
    api = HISTORICAL_DEPENDENCY_CONTAINER_CANDIDATE_TEST_RECEIPT[
        "api_launcher_fleet_state"
    ]
    return {
        "live_trace_worker_complete": dict(worker),
        "api_launcher_fleet_state": {
            **dict(api),
            "targets": list(api["targets"]),
        },
        "receipt_scope": HISTORICAL_DEPENDENCY_CONTAINER_CANDIDATE_TEST_RECEIPT[
            "receipt_scope"
        ],
    }

# These subset receipts keep the historical recovery, active research-control,
# and strict worker-protocol kernels independently visible inside the complete
# Harness-v2 suite.
REQUIRED_SUBSUITE_DIGESTS = {
    "historical recovery": {
        "targets": ["tests/cas_harness_v2/test_historical_v1_v4_recovery.py"],
        "pytest_plugins": [],
        "expected_tests": 4,
        "expected_test_ids_sha256": (
            "B3A239A9579A0DDBADFD2231AF5454250949BFA34BF7124D9305DA0972513340"
        ),
    },
    "active research-control kernel": {
        "targets": [
            "tests/cas_harness_v2/test_research_control_kernel.py",
            "tests/cas_harness_v2/test_research_control_redteam.py",
        ],
        "pytest_plugins": [],
        "expected_tests": 94,
        "expected_test_ids_sha256": (
            "E170E51F83B8DEA3B43537737961580E21E08C14DE9DFE5A3809FB7B2EEA0952"
        ),
    },
    "worker protocol kernel": {
        "targets": ["tests/cas_harness_v2/test_worker_protocol.py"],
        "pytest_plugins": [],
        "expected_tests": 35,
        "expected_subtests": 45,
        "expected_test_ids_sha256": (
            "73C14349373376F49C380A84E8629C82167B5BF0F73415A45F197D99DE97F807"
        ),
    },
}

REQUIRED_CLAIM_IDS = {
    "CLM-PROJECTOR-LATENT-CAPACITY",
    "CLM-HARNESS16-CURRENT-READINESS",
}

MODEL_BINDING = {
    "model_id": "EleutherAI/pythia-160m",
    "revision": "50f5173d932e8e61f858120bcb800b97af589f46",
    "weights_filename": "model.safetensors",
    "weights_sha256": (
        "29d2e457a664e41c12c735f20a36dc0956a665f614a54ce5db21a32e75965270"
    ),
    "weights_bytes": 374_998_696,
    "identity_scope": "WEIGHTS_FILE_IDENTITY_ONLY",
    "execution_authentication": "NOT_ESTABLISHED",
}

SECURITY_HOLD = {
    "status": "HELD",
    "reason_id": "G5-SEC-TRANSFORMERS-CVE-2026-4372",
    "affected_requirement": "transformers==4.46.3",
    "advisory_id": "CVE-2026-4372",
    "ghsa_id": "GHSA-29pf-2h5f-8g72",
    "minimum_fixed_version": "5.3.0",
    "live_execution_authorized": False,
}

# The v0.1 record above is deliberately retained as adverse historical
# evidence.  These values describe only the successor v0.2 engineering
# candidate; they do not release G5-ENGINEERING-003 or authorize execution.
CANDIDATE_SOURCE_COMMIT = "4bff437dbcf6d0d38046e63d2aee823e8f316711"
CANDIDATE_BUILD_REF = "vz8s61131470ab8uivga0qcdq"
CANDIDATE_OCI_DIGESTS = {
    "oci_image_index_digest": (
        "sha256:3d747b379938a5148e4a028ff8ba2f242847b17e8842f19f0d2c204b3fe9a95c"
    ),
    "platform_manifest_digest": (
        "sha256:60bf92b327ebec84887c659313a97a6369a24fd5d8eb00a012544fcafd26ba27"
    ),
    "image_config_digest": (
        "sha256:966db6e2e05366be99129af5c866a8f7efbf01b04145c49ef431785fdc1432ed"
    ),
}
CANDIDATE_BUILD_INPUTS: dict[str, dict[str, Any]] = {
    "dockerfile": {
        "path": f"{WORKER_ROOT_REL}/Dockerfile",
        "sha256": "CCCE6B3227EF6CABE996ECA1F1E2803B0DEEB0852A9BAAD6D0896C4E1E8356C3",
        "line_count": 143,
        "bytes": 7_971,
    },
    "dockerignore": {
        "path": f"{WORKER_ROOT_REL}/.dockerignore",
        "sha256": "5C7BD9443DB6A5017CD350BF93C09C9B6F21A6ACFF7A6B9B586495236021A47F",
        "line_count": 40,
        "bytes": 687,
    },
    "requirements_lock": {
        "path": f"{WORKER_ROOT_REL}/requirements.txt",
        "package_count": 73,
        "sha256": "37CC64DF8317481F024661C573D4146FA31D27E692C69F311EEB2FF84B793401",
        "line_count": 1_291,
        "bytes": 95_788,
        "hash_policy": "EXACT_PACKAGE_ARTIFACT_HASHES / NO_DEPENDENCY_TRAVERSAL",
    },
    "requirements_input": {
        "path": f"{WORKER_ROOT_REL}/requirements.in",
        "sha256": "7C33774EFC66F7F385BCE0A0C471739DC4932649BAB4004C3046CEF1E7CB2232",
        "line_count": 26,
        "bytes": 942,
    },
    "application_tree": {
        "path": f"{WORKER_ROOT_REL}/app",
        "file_count": 24,
        "bytes": 266_912,
        "tree_sha256": "B6E02418E1E0E934CCD0DE5BFA93146C8A650023D3E60C819115D7D48D726DC7",
        "serialization": (
            "ORDINAL-SORTED BUILD-CONTEXT-RELATIVE POSIX PATH + NUL + DECIMAL "
            "BYTE COUNT + NUL + UPPERCASE FILE SHA256 + LF"
        ),
        "source_commit": CANDIDATE_SOURCE_COMMIT,
        "source_commit_tree_matched": True,
    },
}
CURRENT_SECURITY_HOLD = {
    "status": "HELD",
    "criterion_disposition": "OPEN_SECURITY",
    "reason_id": "G5-SEC-CANDIDATE-SCAN-FINDINGS-OPEN",
    "historical_adverse_binding": (
        "docs/working/project_coherence/gate5/"
        "GATE5_MODEL_AND_DEPENDENCY_BINDING_v0.1.json"
    ),
    "candidate_receipt": (
        "docs/working/project_coherence/gate5/"
        "GATE5_DEPENDENCY_AND_CONTAINER_CANDIDATE_RECEIPT_v0.2.json"
    ),
    "raw_build_security_evidence_receipt": (
        "docs/working/project_coherence/gate5/"
        "GATE5_RAW_BUILD_AND_SECURITY_EVIDENCE_RECEIPT_v0.1.json"
    ),
    "source_commit": CANDIDATE_SOURCE_COMMIT,
    "oci_image_index_digest": CANDIDATE_OCI_DIGESTS["oci_image_index_digest"],
    "platform_manifest_digest": CANDIDATE_OCI_DIGESTS["platform_manifest_digest"],
    "requirements_lock_sha256": CANDIDATE_BUILD_INPUTS["requirements_lock"][
        "sha256"
    ],
    "requirements_lock_package_count": 73,
    "candidate_transformers_requirement": "transformers==5.14.1",
    "container_digest_bound": True,
    "bounded_candidate_revalidation": "HOST_AND_CONTAINER_PREFLIGHT_ONLY",
    "full_lock_security_audit_passed": False,
    "sbom_full_image_package_scan": "COMPLETED_WITH_FINDINGS / 7",
    "sbom_scan_severity_counts": {
        "critical": 0,
        "high": 0,
        "medium": 3,
        "low": 4,
    },
    "direct_local_image_scan": "COMPLETED_WITH_FINDINGS / 7 / RAW SARIF RETAINED",
    "vendor_security_triage": "6 VENDOR-CONFIRMED VULNERABLE OR DEFERRED / 1 SCANNER-VENDOR CONFLICT",
    "external_evidence_retention": (
        "RAW BUILDKIT/OCI/SPDX/SLSA/DIRECT SCOUT REPORTS RETAINED / "
        "LOCAL SELF-OBSERVED / NOT INDEPENDENTLY ATTESTED"
    ),
    "engineering_preflight_execution_status": "COMPLETED_CPU_ONLY_NONEXPERIMENTAL",
    "live_execution_authorized": False,
}


class VerificationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def require_exact_keys(
    value: dict[str, Any], expected: set[str], *, label: str
) -> None:
    actual = set(value)
    require(
        actual == expected,
        f"{label}: object schema differs from v0.1: "
        f"missing={sorted(expected - actual)} extra={sorted(actual - expected)}",
    )


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise VerificationError(f"duplicate JSON key: {key!r}")
        value[key] = item
    return value


@dataclass(frozen=True)
class PathIdentity:
    device: int
    inode: int
    mode_type: int
    link_count: int
    byte_count: int
    mtime_ns: int
    ctime_ns: int
    file_attributes: int | None
    reparse_tag: int | None


@dataclass(frozen=True)
class StructuralPathIdentity:
    """Stable identity fields for an observed path component.

    Directory byte counts and timestamps legitimately change when unrelated
    children are created or removed.  They are metadata, not object identity,
    so ancestry checks bind the filesystem object and alias/reparse state while
    the leaf file retains the complete ``PathIdentity`` below.
    """

    device: int
    inode: int
    mode_type: int
    link_count: int
    file_attributes: int | None
    reparse_tag: int | None


@dataclass(frozen=True)
class FileObservation:
    sha256: str
    byte_count: int
    identity: PathIdentity
    component_identities: tuple[tuple[str, StructuralPathIdentity], ...]


def _path_identity(value: os.stat_result) -> PathIdentity:
    return PathIdentity(
        device=int(value.st_dev),
        inode=int(value.st_ino),
        mode_type=int(stat.S_IFMT(value.st_mode)),
        link_count=int(value.st_nlink),
        byte_count=int(value.st_size),
        mtime_ns=int(value.st_mtime_ns),
        ctime_ns=int(value.st_ctime_ns),
        file_attributes=(
            None
            if not hasattr(value, "st_file_attributes")
            else int(value.st_file_attributes)
        ),
        reparse_tag=(
            None if not hasattr(value, "st_reparse_tag") else int(value.st_reparse_tag)
        ),
    )


def _structural_path_identity(identity: PathIdentity) -> StructuralPathIdentity:
    return StructuralPathIdentity(
        device=identity.device,
        inode=identity.inode,
        mode_type=identity.mode_type,
        link_count=identity.link_count,
        file_attributes=identity.file_attributes,
        reparse_tag=identity.reparse_tag,
    )


def _is_reparse(identity: PathIdentity) -> bool:
    reparse_attribute = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(
        (identity.file_attributes is not None and identity.file_attributes & reparse_attribute)
        or (identity.reparse_tag not in (None, 0))
    )


def _component_identities(
    path: Path, *, anchor: Path
) -> tuple[tuple[str, StructuralPathIdentity], ...]:
    absolute_anchor = Path(os.path.abspath(anchor))
    absolute_path = Path(os.path.abspath(path))
    try:
        relative = absolute_path.relative_to(absolute_anchor)
    except ValueError as exc:
        raise VerificationError(f"path escapes its observation anchor: {path}") from exc
    require(relative.parts, f"observation target may not equal its directory anchor: {path}")

    records: list[tuple[str, StructuralPathIdentity]] = []
    current = absolute_anchor
    components = (".", *relative.parts)
    for index, component in enumerate(components):
        if component != ".":
            current = current / component
        try:
            identity = _path_identity(current.lstat())
        except OSError as exc:
            raise VerificationError(f"cannot lstat observed path component {current}: {exc}") from exc
        require(not current.is_symlink(), f"observed path contains a symlink: {current}")
        require(not _is_reparse(identity), f"observed path contains a reparse point: {current}")
        is_leaf = index == len(components) - 1
        if is_leaf:
            require(
                identity.mode_type == stat.S_IFREG,
                f"observed leaf is not a regular file: {current}",
            )
            require(
                identity.link_count == 1,
                f"observed leaf has aliases (st_nlink={identity.link_count}): {current}",
            )
        else:
            require(
                identity.mode_type == stat.S_IFDIR,
                f"observed ancestor is not a directory: {current}",
            )
        records.append((str(current), _structural_path_identity(identity)))
    return tuple(records)


def _same_open_file(path_identity: PathIdentity, handle_identity: PathIdentity) -> bool:
    common_matches = (
        path_identity.device,
        path_identity.inode,
        path_identity.mode_type,
        path_identity.link_count,
        path_identity.byte_count,
        path_identity.mtime_ns,
    ) == (
        handle_identity.device,
        handle_identity.inode,
        handle_identity.mode_type,
        handle_identity.link_count,
        handle_identity.byte_count,
        handle_identity.mtime_ns,
    )
    if not common_matches:
        return False
    if os.name == "nt":
        # CPython's Windows ``fstat`` currently reports ``st_ctime_ns`` as the
        # last-write time, while ``lstat`` reports the filesystem change time.
        # They cannot be compared across APIs.  File ID/device plus the other
        # stable fields bind the handle to the pathname; the before/after
        # pathname observations independently retain and compare the real
        # change time.
        return (
            path_identity.file_attributes == handle_identity.file_attributes
            and path_identity.reparse_tag == handle_identity.reparse_tag
        )
    return path_identity.ctime_ns == handle_identity.ctime_ns


def _observe_regular_file(
    path: Path, *, anchor: Path | None = None, collect_bytes: bool = False
) -> tuple[FileObservation, bytes | None]:
    absolute_path = Path(os.path.abspath(path))
    observation_anchor = (
        Path(os.path.abspath(anchor)) if anchor is not None else absolute_path.parent
    )
    before_components = _component_identities(absolute_path, anchor=observation_anchor)
    before_leaf = _path_identity(absolute_path.lstat())
    require(
        before_leaf.mode_type == stat.S_IFREG
        and before_leaf.link_count == 1
        and not _is_reparse(before_leaf),
        f"observed leaf changed before open or is aliased: {absolute_path}",
    )
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(absolute_path, flags)
    except OSError as exc:
        raise VerificationError(f"cannot open observed file {absolute_path}: {exc}") from exc
    digest = hashlib.sha256()
    chunks: list[bytes] | None = [] if collect_bytes else None
    byte_count = 0
    try:
        opened_before = _path_identity(os.fstat(descriptor))
        require(
            opened_before.mode_type == stat.S_IFREG and opened_before.link_count == 1,
            f"opened handle is not a unique regular file: {absolute_path}",
        )
        require(
            _same_open_file(before_leaf, opened_before),
            f"pathname and opened handle identity differ: {absolute_path}",
        )
        while True:
            block = os.read(descriptor, 1024 * 1024)
            if not block:
                break
            digest.update(block)
            byte_count += len(block)
            if chunks is not None:
                chunks.append(block)
        opened_after = _path_identity(os.fstat(descriptor))
    finally:
        os.close(descriptor)
    require(
        opened_after == opened_before,
        f"opened file identity changed while reading: {absolute_path}",
    )
    require(
        byte_count == opened_after.byte_count,
        f"opened file byte count differs from fstat: {absolute_path}",
    )
    after_components = _component_identities(absolute_path, anchor=observation_anchor)
    require(
        after_components == before_components,
        f"path or ancestor identity changed while reading: {absolute_path}",
    )
    observation = FileObservation(
        sha256=digest.hexdigest().upper(),
        byte_count=byte_count,
        identity=opened_after,
        component_identities=after_components,
    )
    return observation, None if chunks is None else b"".join(chunks)


def observe_regular_file(path: Path, *, anchor: Path | None = None) -> FileObservation:
    observation, _ = _observe_regular_file(path, anchor=anchor, collect_bytes=False)
    return observation


def read_stable_bytes(path: Path, *, anchor: Path | None = None) -> bytes:
    _, payload = _observe_regular_file(path, anchor=anchor, collect_bytes=True)
    require(payload is not None, f"stable read did not retain bytes: {path}")
    return payload


def read_stable_text(
    path: Path, *, anchor: Path | None = None, encoding: str = "utf-8"
) -> str:
    effective_anchor = (
        FILESYSTEM_ANCHOR
        if anchor is None and path.is_absolute() and ROOT in path.parents
        else anchor
    )
    try:
        return read_stable_bytes(path, anchor=effective_anchor).decode(encoding)
    except UnicodeError as exc:
        raise VerificationError(f"cannot decode stable text file {path}: {exc}") from exc


def load_json(path: Path, *, anchor: Path | None = None) -> Any:
    try:
        payload = read_stable_bytes(
            path,
            anchor=(
                FILESYSTEM_ANCHOR
                if anchor is None and path.is_absolute() and ROOT in path.parents
                else anchor
            ),
        )
        return json.loads(payload.decode("utf-8"), object_pairs_hook=_unique_object)
    except VerificationError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise VerificationError(f"cannot parse {path}: {exc}") from exc


def sha256_file(path: Path, *, anchor: Path | None = None) -> str:
    if anchor is None and path.is_absolute() and ROOT in path.parents:
        anchor = FILESYSTEM_ANCHOR
    return observe_regular_file(path, anchor=anchor).sha256


def sha256_bytes(payload: bytes) -> str:
    require(type(payload) is bytes, "SHA-256 payload must be exact bytes")
    return hashlib.sha256(payload).hexdigest().upper()


def canonical_repo_path(raw_path: Any, *, label: str) -> str:
    require(isinstance(raw_path, str) and raw_path, f"{label}: path is missing")
    require("\\" not in raw_path, f"{label}: path must use POSIX slashes")
    require(
        not WINDOWS_ABSOLUTE_RE.match(raw_path),
        f"{label}: path must be repository-relative",
    )
    pure = PurePosixPath(raw_path)
    require(not pure.is_absolute(), f"{label}: path must be repository-relative")
    require(
        raw_path == pure.as_posix() and "." not in pure.parts and ".." not in pure.parts,
        f"{label}: path is not canonical or traverses directories",
    )
    resolved = (ROOT / Path(*pure.parts)).resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise VerificationError(f"{label}: path resolves outside repository") from exc
    return raw_path


def verify_governance_header(value: dict[str, Any], *, label: str) -> None:
    require(
        value.get("document_status") == "DRAFT / OPEN / NOT FROZEN",
        f"{label}: document is not explicitly draft/open/unfrozen",
    )
    require(value.get("gate5_status") == "OPEN", f"{label}: Gate 5 is not OPEN")
    require(
        value.get("gate_decision") == "KEEP_OPEN",
        f"{label}: candidate attempts to close Gate 5",
    )
    require(
        value.get("experimental_execution_status") == "NOT_STARTED",
        f"{label}: experimental execution status was promoted",
    )
    require(
        type(value.get("admission_ring")) is int and value["admission_ring"] == 4,
        f"{label}: escaped Ring 4 or used a non-integer ring",
    )
    require(
        value.get("license_status") == "NOT LICENSED",
        f"{label}: claims a licensed status",
    )
    require(
        value.get("disclosure_status") == "HELD",
        f"{label}: disclosure is not HELD",
    )
    require(
        value.get("public_disclosure_authorized") is False,
        f"{label}: public disclosure was authorized",
    )
    require(value.get("canon_effect") == "NONE", f"{label}: claims canon effect")
    require(
        value.get("product_claim_effect") == "NONE",
        f"{label}: claims product-claim effect",
    )


def _collect_surface(directory: str, pattern: str) -> set[str]:
    root = ROOT / directory
    require(root.is_dir(), f"missing required surface directory: {directory}")
    return {
        path.relative_to(ROOT).as_posix()
        for path in root.rglob(pattern)
        if path.is_file() and "__pycache__" not in path.parts
    }


def collect_gate5_control_surface() -> set[str]:
    """Collect every Gate 5 control artifact except the non-self-hashing manifest."""
    require(GATE5_DIR.is_dir(), "Gate 5 control directory is missing")
    return {
        path.relative_to(ROOT).as_posix()
        for path in GATE5_DIR.rglob("*")
        if path.is_file()
        and path != MANIFEST_PATH
        and "__pycache__" not in path.parts
    }


def collect_pytest_environment_surface() -> set[str]:
    """Collect the existing files from the complete pytest discovery surface."""
    return {
        raw_path
        for raw_path in PYTEST_ENVIRONMENT_CANDIDATE_PATHS
        if (ROOT / Path(*PurePosixPath(raw_path).parts)).is_file()
    }


def collect_api_runtime_surface() -> set[str]:
    """Collect the complete current API source/resource tree admitted by Gate 5."""
    return _collect_surface(API_RUNTIME_SURFACE_DIR, "*")


def verify_no_executable_shadow_artifacts() -> int:
    """Reject repository aliases and unbound executable shadows."""
    scanned: set[str] = set()
    violations: set[str] = set()
    for directory in EXECUTABLE_SHADOW_SCAN_DIRS:
        root = ROOT / directory
        require(root.is_dir(), f"missing executable-shadow scan directory: {directory}")
        root_identity = _path_identity(root.lstat())
        require(
            root_identity.mode_type == stat.S_IFDIR
            and not root.is_symlink()
            and not _is_reparse(root_identity),
            f"executable-shadow scan root is a symlink/reparse alias: {directory}",
        )
        for path in root.rglob("*"):
            raw_path = path.relative_to(ROOT).as_posix()
            scanned.add(raw_path)
            try:
                identity = _path_identity(path.lstat())
            except OSError as exc:
                raise VerificationError(
                    f"cannot lstat executable-shadow path {raw_path}: {exc}"
                ) from exc
            if path.is_symlink() or _is_reparse(identity):
                violations.add(raw_path)
            elif "__pycache__" in path.parts:
                violations.add(raw_path)
            elif (
                identity.mode_type == stat.S_IFREG
                and path.suffix.casefold() in FORBIDDEN_EXECUTABLE_SHADOW_SUFFIXES
            ):
                violations.add(raw_path)
    require(
        not violations,
        "forbidden executable cache/native/archive shadow exists on an admitted "
        f"Gate 5 surface: {sorted(violations)}",
    )
    return len(scanned)


def artifact_role(path: str) -> str:
    """Return the only role admitted for a path in the v0.1 manifest."""
    if path in PYTEST_ENVIRONMENT_CANDIDATE_PATHS:
        return "gate5_pytest_environment_control"
    if path in EXACT_API_LAUNCHER_SURFACE:
        if path.endswith("prepare_large_model_eval.py") and "/scripts/test_" not in path:
            return "gate5_launcher_source"
        if "/api/" in path:
            return "gate5_api_identity_source"
        return "gate5_api_launcher_test"
    if path.startswith(API_RUNTIME_SURFACE_DIR + "/"):
        return "gate5_api_runtime_dependency"
    if path.startswith("src/cas_harness_v2/"):
        return "gate5_control_kernel_source"
    if path.startswith("src/cas_core_v8/"):
        return "gate5_bound_cas_core_dependency"
    if path.startswith(f"{API_ROOT_REL}/cas_harness_v2/"):
        return "gate5_packaged_control_kernel_mirror"
    if path.startswith("tests/cas_harness_v2/"):
        return "gate5_control_kernel_test"
    if "/live-trace-worker/app/" in path:
        return "gate5_worker_source"
    if "/live-trace-worker/tests/" in path:
        return "gate5_worker_test"
    if "/live-trace-worker/scripts/" in path:
        return "gate5_worker_support"
    if "/live-trace-worker/scenarios/" in path:
        return "gate5_worker_fixture"
    if path.endswith(
        (
            "Dockerfile",
            "Dockerfile.api",
            ".dockerignore",
            "requirements.in",
            "requirements.txt",
            "pyproject.toml",
        )
    ):
        return "gate5_environment_control"
    if path.endswith(".py") and path.startswith("scripts/"):
        return "gate5_verification_control"
    if "/gate4/" in path or path.endswith("CLAIM_LEDGER_v0.1.json"):
        return "gate5_bound_dependency"
    return "gate5_control_artifact"


def verify_manifest(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    expected_top_level_keys = {
        "schema_version",
        "document_status",
        "gate5_status",
        "gate_decision",
        "experimental_execution_status",
        "admission_ring",
        "license_status",
        "disclosure_status",
        "public_disclosure_authorized",
        "canon_effect",
        "product_claim_effect",
        "manifest_self_hash",
        "generated_by",
        "artifact_count",
        "artifacts",
        "required_open_boundaries",
        "model_binding",
        "dependency_security_hold",
        "test_suites",
    }
    require_exact_keys(manifest, expected_top_level_keys, label="Gate 5 manifest")
    require(
        manifest.get("schema_version")
        == "project_coherence.gate5_artifact_manifest.v0.1",
        "unexpected Gate 5 manifest schema",
    )
    verify_governance_header(manifest, label="Gate 5 manifest")
    require(manifest.get("manifest_self_hash") is None, "manifest hashes itself")
    require(
        manifest.get("generated_by")
        == "scripts/build_project_coherence_gate5_manifest.py",
        "manifest generator identity drifted",
    )

    artifacts = manifest.get("artifacts")
    require(isinstance(artifacts, list) and artifacts, "manifest has no artifacts")
    records: dict[str, dict[str, Any]] = {}
    casefold_paths: set[str] = set()
    artifact_paths: list[str] = []
    for index, record in enumerate(artifacts):
        require(isinstance(record, dict), f"artifact {index} is not an object")
        require_exact_keys(
            record,
            {"path", "sha256", "bytes", "role"},
            label=f"artifact {index}",
        )
        raw_path = canonical_repo_path(record.get("path"), label=f"artifact {index}")
        require(
            raw_path.casefold() not in casefold_paths,
            f"duplicate artifact path under case-folding: {raw_path}",
        )
        casefold_paths.add(raw_path.casefold())
        expected_hash = record.get("sha256")
        expected_bytes = record.get("bytes")
        require(
            isinstance(expected_hash, str) and SHA256_UPPER_RE.fullmatch(expected_hash),
            f"artifact {raw_path}: invalid uppercase SHA-256",
        )
        require(
            isinstance(expected_bytes, int)
            and not isinstance(expected_bytes, bool)
            and expected_bytes >= 0,
            f"artifact {raw_path}: invalid byte count",
        )
        require(
            record.get("role") == artifact_role(raw_path),
            f"artifact {raw_path}: role differs from the path-bound v0.1 role",
        )
        path = ROOT / Path(*PurePosixPath(raw_path).parts)
        observation = observe_regular_file(path, anchor=FILESYSTEM_ANCHOR)
        require(
            observation.byte_count == expected_bytes,
            f"artifact byte drift: {raw_path}",
        )
        require(
            observation.sha256 == expected_hash,
            f"artifact hash drift: {raw_path}",
        )
        records[raw_path] = record
        artifact_paths.append(raw_path)

    require(
        artifact_paths == sorted(artifact_paths),
        "manifest artifact records are not ordinal-sorted",
    )
    require(
        isinstance(manifest.get("artifact_count"), int)
        and not isinstance(manifest.get("artifact_count"), bool)
        and manifest["artifact_count"] == len(artifacts),
        "manifest artifact_count differs from its exact artifact list",
    )

    manifest_rel = MANIFEST_PATH.relative_to(ROOT).as_posix()
    require(manifest_rel not in records, "manifest must not hash itself")
    require(
        REQUIRED_CONTROL_ARTIFACTS <= set(records),
        "manifest omits required Gate 5 controls: "
        f"{sorted(REQUIRED_CONTROL_ARTIFACTS - set(records))}",
    )

    required_surface = (
        set(REQUIRED_CONTROL_ARTIFACTS)
        | set(EXACT_API_LAUNCHER_SURFACE)
        | collect_api_runtime_surface()
        | collect_gate5_control_surface()
        | collect_pytest_environment_surface()
    )
    required_all_files: set[str] = set()
    for directory in EXACT_ALL_FILE_SURFACE_DIRS:
        required_all_files.update(_collect_surface(directory, "*"))
    required_surface.update(required_all_files)
    bound_all_files = {
        path
        for path in records
        if any(path.startswith(directory + "/") for directory in EXACT_ALL_FILE_SURFACE_DIRS)
    }
    require(
        bound_all_files == required_all_files,
        "manifest does not exactly bind every regular file in the admitted Gate 5 roots: "
        f"missing={sorted(required_all_files - bound_all_files)} "
        f"extra={sorted(bound_all_files - required_all_files)}",
    )
    required_python = {path for path in required_all_files if path.endswith(".py")}
    bound_python = {
        path
        for path in records
        if path.endswith(".py")
        and any(path.startswith(directory + "/") for directory in EXACT_ALL_FILE_SURFACE_DIRS)
    }
    require(
        bound_python == required_python,
        "manifest does not exactly bind the Gate 5 Python surface: "
        f"missing={sorted(required_python - bound_python)} "
        f"extra={sorted(bound_python - required_python)}",
    )

    for directory, pattern in EXACT_DATA_SURFACES:
        actual = _collect_surface(directory, pattern)
        required_surface.update(actual)
        bound = {
            path
            for path in records
            if path.startswith(directory + "/")
            and Path(path).match(f"{directory}/{pattern}")
        }
        require(
            bound == actual,
            f"manifest does not exactly bind {directory}/{pattern}: "
            f"missing={sorted(actual - bound)} extra={sorted(bound - actual)}",
        )
    require(
        set(records) == required_surface,
        "manifest artifact list differs from the exact Gate 5 surface: "
        f"missing={sorted(required_surface - set(records))} "
        f"extra={sorted(set(records) - required_surface)}",
    )

    boundaries = manifest.get("required_open_boundaries")
    require(
        isinstance(boundaries, list)
        and boundaries
        and all(isinstance(item, str) and item for item in boundaries),
        "manifest open-boundary list is missing or malformed",
    )
    boundary_ids: list[str] = []
    for boundary in boundaries:
        match = BOUNDARY_RE.match(boundary)
        require(match is not None, f"open boundary has no stable ID: {boundary!r}")
        boundary_ids.append(match.group(1))
    require(
        len(boundary_ids) == len(set(boundary_ids)),
        "manifest has duplicate open-boundary IDs",
    )
    require(
        set(boundary_ids) == REQUIRED_OPEN_BOUNDARY_IDS,
        "manifest open-boundary IDs differ from the required closure surface: "
        f"missing={sorted(REQUIRED_OPEN_BOUNDARY_IDS - set(boundary_ids))} "
        f"extra={sorted(set(boundary_ids) - REQUIRED_OPEN_BOUNDARY_IDS)}",
    )
    expected_boundaries = [
        f"[{boundary_id}] {REQUIRED_BOUNDARY_TEXT[boundary_id]}"
        for boundary_id in sorted(REQUIRED_BOUNDARY_TEXT)
    ]
    require(
        boundaries == expected_boundaries,
        "manifest open-boundary text or ordinal order differs from v0.1",
    )

    model_binding = manifest.get("model_binding")
    require(isinstance(model_binding, dict), "manifest model binding is missing")
    require(model_binding == MODEL_BINDING, "Pythia model/weights binding drifted")
    require(
        type(model_binding.get("weights_bytes")) is int,
        "manifest model weights byte count must be an exact integer",
    )

    security_hold = manifest.get("dependency_security_hold")
    require(isinstance(security_hold, dict), "dependency security hold is missing")
    require(
        security_hold == CURRENT_SECURITY_HOLD,
        "successor dependency-security hold summary drifted",
    )
    require(
        security_hold.get("criterion_disposition") == "OPEN_SECURITY"
        and security_hold.get("status") == "HELD",
        "current manifest removed the OPEN_SECURITY / HELD boundary",
    )
    require(
        security_hold.get("full_lock_security_audit_passed") is False
        and security_hold.get("sbom_full_image_package_scan")
        == "COMPLETED_WITH_FINDINGS / 7"
        and security_hold.get("direct_local_image_scan")
        == "COMPLETED_WITH_FINDINGS / 7 / RAW SARIF RETAINED"
        and security_hold.get("vendor_security_triage")
        == "6 VENDOR-CONFIRMED VULNERABLE OR DEFERRED / 1 SCANNER-VENDOR CONFLICT"
        and security_hold.get("live_execution_authorized") is False,
        "manifest falsely promotes the bounded candidate to a security or execution PASS",
    )

    suites = manifest.get("test_suites")
    require(isinstance(suites, list), "manifest test_suites is not a list")
    expected_suite_keys = {
        "name",
        "working_directory",
        "targets",
        "pytest_plugins",
        "repo_import_roots",
        "expected_tests",
        "expected_subtests",
        "expected_test_ids_sha256",
        "test_id_canonicalization",
    }
    require(
        all(isinstance(suite, dict) and set(suite) == expected_suite_keys for suite in suites),
        "manifest test-suite record schema differs from v0.1",
    )
    suite_names = [suite["name"] for suite in suites]
    require(
        suite_names == list(REQUIRED_TEST_SUITES),
        "manifest test-suite names or order differ from the required Gate 5 suites",
    )
    return records


def verify_gate4_dependency(
    gate5_artifacts: dict[str, dict[str, Any]],
) -> tuple[int, str]:
    gate4 = load_json(GATE4_MANIFEST_PATH)
    require(isinstance(gate4, dict), "Gate 4 manifest root is not an object")
    require_exact_keys(
        gate4,
        {
            "schema_version",
            "document_status",
            "gate4_status",
            "gate_decision",
            "admission_ring",
            "license_status",
            "disclosure_status",
            "public_disclosure_authorized",
            "canon_effect",
            "product_claim_effect",
            "manifest_self_hash",
            "artifacts",
            "external_source_bindings",
            "test_suites",
            "required_open_boundaries",
        },
        label="Gate 4 dependency manifest",
    )
    require(gate4.get("gate4_status") == "OPEN", "Gate 4 dependency is not OPEN")
    require(
        gate4.get("gate_decision") == "KEEP_OPEN",
        "Gate 4 dependency claims closure",
    )
    require(
        type(gate4.get("admission_ring")) is int and gate4["admission_ring"] == 4,
        "Gate 4 dependency escaped Ring 4 or used a non-integer ring",
    )
    require(
        gate4.get("license_status") == "NOT LICENSED",
        "Gate 4 dependency licensed claims",
    )
    require(gate4.get("disclosure_status") == "HELD", "Gate 4 disclosure is not held")

    gate4_artifacts = gate4.get("artifacts")
    require(isinstance(gate4_artifacts, list), "Gate 4 manifest has no artifacts")
    gate4_by_path = {
        record.get("path"): record
        for record in gate4_artifacts
        if isinstance(record, dict) and isinstance(record.get("path"), str)
    }
    ledger_rel = CLAIM_LEDGER_PATH.relative_to(ROOT).as_posix()
    gate4_ledger = gate4_by_path.get(ledger_rel)
    gate5_ledger = gate5_artifacts.get(ledger_rel)
    require(isinstance(gate4_ledger, dict), "Gate 4 does not bind the claim ledger")
    require(isinstance(gate5_ledger, dict), "Gate 5 does not bind the claim ledger")
    require(
        gate4_ledger.get("sha256") == gate5_ledger.get("sha256")
        and gate4_ledger.get("bytes") == gate5_ledger.get("bytes"),
        "Gate 4 and Gate 5 bind different claim-ledger bytes",
    )

    # Gate 4 deliberately runs compileall. Redirect those generated bytecode
    # files to a verifier-owned temporary tree so dependency verification cannot
    # mutate the Gate 5 source/evidence surface that is rehashed postflight.
    with tempfile.TemporaryDirectory(prefix="gate5-gate4-pycache-") as raw_temp:
        pycache_prefix = Path(raw_temp) / "pycache"
        pycache_prefix.mkdir()
        stdout, _ = run_command(
            [sys.executable, "-B", "scripts/verify_project_coherence_gate4.py"],
            cwd=ROOT,
            timeout=480,
            extra_env={"PYTHONPYCACHEPREFIX": str(pycache_prefix)},
        )
    require(
        "Project Coherence integrated Gate 4 verification: PASS" in stdout,
        "integrated Gate 4 dependency receipt is missing",
    )
    require(
        "Gate 4 status: OPEN / Ring 4 / NOT LICENSED / HELD / NOT FROZEN"
        in stdout,
        "Gate 4 PASS omitted its non-promotion boundary",
    )
    return len(gate4_artifacts), sha256_file(GATE4_MANIFEST_PATH)


def verify_gate4_artifact_bytes() -> int:
    """Rehash Gate 4's bound records after all Gate 5 subprocesses finish."""
    gate4 = load_json(GATE4_MANIFEST_PATH)
    require(isinstance(gate4, dict), "Gate 4 postflight manifest is malformed")
    artifacts = gate4.get("artifacts")
    require(isinstance(artifacts, list) and artifacts, "Gate 4 postflight has no artifacts")
    seen: set[str] = set()
    for index, record in enumerate(artifacts):
        require(isinstance(record, dict), f"Gate 4 postflight artifact {index} is malformed")
        require_exact_keys(
            record,
            {"path", "sha256", "bytes", "role"},
            label=f"Gate 4 postflight artifact {index}",
        )
        raw_path = canonical_repo_path(
            record.get("path"), label=f"Gate 4 postflight artifact {index}"
        )
        require(raw_path.casefold() not in seen, "Gate 4 postflight has duplicate paths")
        seen.add(raw_path.casefold())
        expected_hash = record.get("sha256")
        expected_bytes = record.get("bytes")
        require(
            isinstance(expected_hash, str) and SHA256_UPPER_RE.fullmatch(expected_hash),
            f"Gate 4 postflight artifact {raw_path}: SHA-256 is malformed",
        )
        require(
            type(expected_bytes) is int and expected_bytes >= 0,
            f"Gate 4 postflight artifact {raw_path}: byte count is malformed",
        )
        path = ROOT / Path(*PurePosixPath(raw_path).parts)
        require(path.is_file(), f"Gate 4 postflight artifact is missing: {raw_path}")
        require(not path.is_symlink(), f"Gate 4 postflight artifact is a symlink: {raw_path}")
        require(
            path.stat().st_size == expected_bytes,
            f"Gate 4 postflight artifact byte drift: {raw_path}",
        )
        require(
            sha256_file(path) == expected_hash,
            f"Gate 4 postflight artifact hash drift: {raw_path}",
        )
    return len(artifacts)


def verify_claim_ledger() -> int:
    ledger = load_json(CLAIM_LEDGER_PATH)
    require(isinstance(ledger, dict), "claim ledger root is not an object")
    require_exact_keys(
        ledger,
        {
            "schema_version",
            "record_schema",
            "document_status",
            "as_of",
            "completeness",
            "records",
        },
        label="claim ledger",
    )
    require(
        ledger.get("schema_version") == "project_coherence_claim_ledger.v0.1",
        "unexpected claim-ledger schema",
    )
    require(
        ledger.get("document_status") == "DRAFT / OPEN / NOT FROZEN",
        "claim ledger is not draft/open/unfrozen",
    )
    records = ledger.get("records")
    require(isinstance(records, list) and records, "claim ledger is empty")
    require(all(isinstance(record, dict) for record in records), "claim record is malformed")
    record_keys = {
        "id",
        "version",
        "title",
        "statement_kind",
        "claim_text",
        "source_refs",
        "scope",
        "controls",
        "falsifier",
        "uncertainty",
        "evidence_packets",
        "review_state",
        "product_claim_status",
        "admission_ring",
        "disclosure_status",
        "theorem_refs",
        "reviewers",
        "last_reviewed_at",
        "notes",
    }
    for index, record in enumerate(records):
        require_exact_keys(record, record_keys, label=f"claim record {index}")
        scope = record.get("scope")
        require(isinstance(scope, dict), f"claim record {index}: scope is malformed")
        require_exact_keys(
            scope,
            {"population", "models", "architectures", "contexts", "time_window"},
            label=f"claim record {index} scope",
        )
    ids = [record.get("id") for record in records]
    require(
        all(isinstance(claim_id, str) and claim_id for claim_id in ids),
        "claim ledger contains an invalid claim ID",
    )
    require(len(ids) == len(set(ids)), "claim ledger has duplicate IDs")
    require(REQUIRED_CLAIM_IDS <= set(ids), "required Gate 5 claim records are absent")
    require(
        all(
            type(record.get("admission_ring")) is int
            and record["admission_ring"] == 4
            for record in records
        ),
        "a claim escaped Ring 4",
    )
    require(
        all(record.get("product_claim_status") == "NOT LICENSED" for record in records),
        "a claim is no longer NOT LICENSED",
    )
    require(
        all(
            record.get("disclosure_status") in {"HELD", "FLAG_FOR_HUMAN_REVIEW"}
            for record in records
        ),
        "a claim escaped held/human-review disclosure control",
    )
    by_id = {record["id"]: record for record in records}
    require(
        all(by_id[claim_id].get("disclosure_status") == "HELD" for claim_id in REQUIRED_CLAIM_IDS),
        "a required Gate 5 claim is no longer HELD",
    )
    return len(records)


def verify_history() -> tuple[int, int, str]:
    history = load_json(HISTORY_MANIFEST_PATH)
    require(isinstance(history, dict), "historical manifest root is not an object")
    require_exact_keys(
        history,
        {
            "schema_version",
            "generated_at_utc",
            "current_head",
            "source_revision",
            "source_relationship",
            "recovery_scope",
            "collision_preflight",
            "current_tree",
            "frozen_binding_verification",
            "model_free_static_test_run",
            "supplemental_v1_worker_test_run",
            "claim_and_gate_status_change",
            "files",
        },
        label="historical manifest",
    )
    require(
        history.get("schema_version")
        == "cas_harness_historical_recovery_current_tree_sha256.v1",
        "unexpected historical recovery schema",
    )
    require(
        history.get("source_revision")
        == "d9c1879762233855cd5974676b8179b1e4e75d16",
        "historical recovery source revision drifted",
    )
    require(
        history.get("claim_and_gate_status_change") == "NONE",
        "historical recovery claims a gate or claim-status effect",
    )
    collision = history.get("collision_preflight")
    require(isinstance(collision, dict), "historical collision preflight is missing")
    require_exact_keys(
        collision,
        {
            "source_target_count",
            "absent_before_restore",
            "byte_identical_before_restore",
            "divergent_before_restore",
            "worktree_deletions_before_restore",
            "path_type_conflicts_before_restore",
            "extras_in_closed_directories_before_restore",
        },
        label="historical collision preflight",
    )
    for field, expected in {
        "source_target_count": 537,
        "absent_before_restore": 537,
        "byte_identical_before_restore": 0,
        "divergent_before_restore": 0,
        "worktree_deletions_before_restore": 0,
        "path_type_conflicts_before_restore": 0,
        "extras_in_closed_directories_before_restore": 0,
    }.items():
        require(
            type(collision.get(field)) is int and collision[field] == expected,
            f"historical collision-preflight count {field!r} drifted",
        )
    files = history.get("files")
    require(isinstance(files, list) and len(files) == 537, "history must bind 537 files")
    paths: list[str] = []
    canonical_lines: list[bytes] = []
    total_bytes = 0
    for index, record in enumerate(files):
        require(isinstance(record, dict), f"historical file {index} is malformed")
        require_exact_keys(
            record,
            {
                "path",
                "source_mode",
                "source_git_blob_sha1",
                "current_git_blob_sha1",
                "byte_count",
                "sha256",
                "exact_source_bytes",
            },
            label=f"historical file {index}",
        )
        raw_path = canonical_repo_path(record.get("path"), label=f"historical file {index}")
        expected_bytes = record.get("byte_count")
        expected_hash = record.get("sha256")
        require(
            isinstance(expected_bytes, int)
            and not isinstance(expected_bytes, bool)
            and expected_bytes >= 0,
            f"historical file {raw_path}: invalid byte count",
        )
        require(
            isinstance(expected_hash, str) and SHA256_LOWER_RE.fullmatch(expected_hash),
            f"historical file {raw_path}: invalid lowercase SHA-256",
        )
        require(record.get("exact_source_bytes") is True, f"{raw_path}: not exact source bytes")
        path = ROOT / Path(*PurePosixPath(raw_path).parts)
        require(path.is_file(), f"historical file is missing: {raw_path}")
        require(not path.is_symlink(), f"historical file may not be a symlink: {raw_path}")
        payload_bytes = path.stat().st_size
        require(payload_bytes == expected_bytes, f"historical byte drift: {raw_path}")
        require(sha256_file(path).lower() == expected_hash, f"historical hash drift: {raw_path}")
        paths.append(raw_path)
        total_bytes += payload_bytes
        canonical_lines.append(
            f"{raw_path}\0{payload_bytes}\0{expected_hash}\n".encode("utf-8")
        )
    require(paths == sorted(paths), "historical file paths are not ordinal-sorted")
    require(
        len(paths) == len({path.casefold() for path in paths}),
        "historical manifest has duplicate paths",
    )

    scope = history.get("recovery_scope")
    require(isinstance(scope, list) and scope, "historical recovery scope is missing")
    actual_scope_files: set[str] = set()
    for index, item in enumerate(scope):
        raw_scope = canonical_repo_path(item, label=f"historical recovery scope {index}")
        scope_path = ROOT / Path(*PurePosixPath(raw_scope).parts)
        require(scope_path.exists(), f"historical recovery scope is missing: {raw_scope}")
        if scope_path.is_file():
            actual_scope_files.add(raw_scope)
        else:
            actual_scope_files.update(
                path.relative_to(ROOT).as_posix()
                for path in scope_path.rglob("*")
                if path.is_file() and "__pycache__" not in path.parts
            )
    require(
        actual_scope_files == set(paths),
        "historical recovery closed scope differs from its manifest: "
        f"missing={sorted(actual_scope_files - set(paths))} "
        f"extra={sorted(set(paths) - actual_scope_files)}",
    )

    current = history.get("current_tree")
    require(isinstance(current, dict), "historical current_tree is missing")
    require_exact_keys(
        current,
        {
            "file_count",
            "total_byte_count",
            "exact_source_file_count",
            "source_byte_mismatch_count",
            "inventory_sha256",
            "inventory_canonicalization",
        },
        label="historical current_tree",
    )
    require(
        type(current.get("file_count")) is int and current["file_count"] == 537,
        "historical file count drifted or used a non-integer count",
    )
    require(
        type(current.get("total_byte_count")) is int
        and current["total_byte_count"] == total_bytes == 95_945_579,
        "historical total byte count drifted",
    )
    require(
        type(current.get("exact_source_file_count")) is int
        and current["exact_source_file_count"] == 537
        and type(current.get("source_byte_mismatch_count")) is int
        and current["source_byte_mismatch_count"] == 0,
        "historical exact-source count or mismatch count drifted",
    )
    inventory_digest = sha256_bytes(b"".join(canonical_lines)).lower()
    require(
        current.get("inventory_sha256")
        == inventory_digest
        == "361f8867a1b8983c383b4f4fe6d8d485e5dbbc80ee4f75e4b5d08b4e5f144f5f",
        "historical inventory digest drifted",
    )

    frozen = history.get("frozen_binding_verification")
    require(isinstance(frozen, dict), "historical frozen-binding record is missing")
    require_exact_keys(
        frozen,
        {
            "record_checks",
            "matched_record_checks",
            "mismatched_record_checks",
            "v3_raw_logits_count",
            "v3_raw_logits_total_byte_count",
            "v3_raw_logits_hash_mismatches",
            "terminal_binding_classification",
            "mismatch",
        },
        label="historical frozen-binding record",
    )
    for field, expected in {
        "record_checks": 48,
        "matched_record_checks": 47,
        "mismatched_record_checks": 1,
        "v3_raw_logits_count": 472,
        "v3_raw_logits_total_byte_count": 94_973_952,
        "v3_raw_logits_hash_mismatches": 0,
    }.items():
        require(
            type(frozen.get(field)) is int and frozen[field] == expected,
            f"historical frozen-binding count {field!r} drifted",
        )
    require(
        frozen.get("terminal_binding_classification")
        == "HISTORICALLY_INCONSISTENT / NOT_INDEPENDENTLY_BYTE_CLOSED / FAIL_CLOSED",
        "known V3 LF/CRLF inconsistency was erased or reclassified",
    )
    mismatch = frozen.get("mismatch")
    require(isinstance(mismatch, dict), "historical V3 mismatch record is absent")
    require_exact_keys(
        mismatch,
        {
            "path",
            "committed_source",
            "terminal_manifest_expectation",
            "deterministic_lf_to_crlf_reproduction",
            "disposition",
        },
        label="historical V3 mismatch",
    )
    mismatch_nested_keys = {
        "committed_source": {"byte_count", "sha256", "git_blob_sha1", "line_ending"},
        "terminal_manifest_expectation": {"byte_count", "sha256", "line_ending"},
        "deterministic_lf_to_crlf_reproduction": {
            "byte_count",
            "sha256",
            "matches_manifest",
        },
    }
    for field, expected_keys in mismatch_nested_keys.items():
        nested = mismatch.get(field)
        require(isinstance(nested, dict), f"historical V3 mismatch {field} is malformed")
        require_exact_keys(nested, expected_keys, label=f"historical V3 mismatch {field}")
    require(
        mismatch.get("committed_source", {}).get("sha256")
        == "141e910385bcbda3494dd6ddca7a933d6dad9b7a1b37ef192de6497811b207bd",
        "historical V3 LF digest drifted",
    )
    require(
        mismatch.get("terminal_manifest_expectation", {}).get("sha256")
        == "bb9d68c06b86a69b3507b579761356d0d9db8c9396d6268c8255b63aedead90e",
        "historical V3 CRLF expectation drifted",
    )

    static_run = history.get("model_free_static_test_run")
    require(isinstance(static_run, dict), "historical model-free red receipt is absent")
    require_exact_keys(
        static_run,
        {
            "command",
            "result",
            "failed_tests",
            "model_loads",
            "v4_execution_runs",
            "network_calls",
            "receipt_or_nonce_actions",
            "note",
        },
        label="historical model-free receipt",
    )
    require(static_run.get("result") == "43 passed, 4 failed in 28.99s", "historical 43/4 receipt drifted")
    failures = static_run.get("failed_tests")
    require(isinstance(failures, list) and len(failures) == 4, "historical four failures were not preserved")
    for index, failure in enumerate(failures):
        require(isinstance(failure, dict), f"historical failure {index} is malformed")
        require_exact_keys(
            failure,
            {"test", "classification", "detail"},
            label=f"historical failure {index}",
        )
    require(
        {failure.get("classification") for failure in failures if isinstance(failure, dict)}
        == {
            "RECOVERY_SCOPE_DEPENDENCY_ABSENT",
            "KNOWN_STALE_POST_RUN_ASSERTION",
            "HISTORICAL_RESULT_BYTE_BINDING_INCONSISTENCY",
        },
        "historical failure classifications drifted",
    )
    supplemental = history.get("supplemental_v1_worker_test_run")
    require(isinstance(supplemental, dict), "supplemental V1 red receipt is absent")
    require_exact_keys(
        supplemental,
        {
            "command",
            "result",
            "classification",
            "detail",
            "model_loads",
            "network_calls",
            "live_worker_calls",
            "paid_compute_calls",
        },
        label="supplemental V1 receipt",
    )
    require(supplemental.get("result") == "31 failed in 1.39s", "historical V1 31-failure receipt drifted")
    require(
        supplemental.get("classification") == "HISTORICAL_FIXTURE_DEPENDENCIES_ABSENT",
        "historical V1 dependency failure was erased",
    )

    inventory_text = read_stable_text(HISTORY_INVENTORY_PATH)
    for marker in (
        "361f8867a1b8983c383b4f4fe6d8d485e5dbbc80ee4f75e4b5d08b4e5f144f5f",
        "HISTORICALLY_INCONSISTENT",
        "ZeroNetworkGuard",
        "CompatibleZeroNetworkGuard",
        "31 failed",
    ):
        require(marker in inventory_text, f"historical inventory omits marker {marker!r}")
    return len(files), total_bytes, inventory_digest


def verify_engineering_execution_reconciliation(
    manifest_artifacts: dict[str, dict[str, Any]],
) -> None:
    receipt = load_json(ENGINEERING_EXECUTION_RECONCILIATION_PATH)
    require(isinstance(receipt, dict), "engineering-execution reconciliation is missing")
    require_exact_keys(
        receipt,
        {
            "schema_version",
            "document_status",
            "gate5_status",
            "gate_decision",
            "experimental_execution_status",
            "admission_ring",
            "license_status",
            "disclosure_status",
            "public_disclosure_authorized",
            "product_route_authorized",
            "canon_effect",
            "product_claim_effect",
            "classification",
            "local_gpu_canary",
            "joined_controller_worker",
            "provider_accounting",
            "claim_boundary",
        },
        label="engineering-execution reconciliation",
    )
    require(
        receipt.get("schema_version")
        == "project_coherence.gate5_engineering_execution_reconciliation.v0.1",
        "unexpected engineering-execution reconciliation schema",
    )
    verify_governance_header(receipt, label="engineering-execution reconciliation")
    require(
        receipt.get("product_route_authorized") is False,
        "engineering-execution reconciliation authorizes a product route",
    )
    require(
        receipt.get("classification")
        == "CANONICAL INGESTION OF RETAINED LOCAL ENGINEERING EVIDENCE / NOT SCIENTIFIC ADMISSION",
        "engineering-execution reconciliation promotes retained mechanics",
    )

    def _verify_bound_runtime_receipt(
        record: Any,
        *,
        label: str,
        expected_keys: set[str],
        expected_values: dict[str, Any],
    ) -> dict[str, Any]:
        require(isinstance(record, dict), f"{label} binding is missing")
        require_exact_keys(record, expected_keys, label=f"{label} binding")
        for field, expected in expected_values.items():
            require(record.get(field) == expected, f"{label} field {field!r} drifted")
        raw_path = canonical_repo_path(record.get("runtime_receipt"), label=label)
        require(raw_path in manifest_artifacts, f"{label} is not hash-bound by Gate 5")
        path = ROOT / Path(*PurePosixPath(raw_path).parts)
        observation = observe_regular_file(path, anchor=FILESYSTEM_ANCHOR)
        require(
            observation.sha256.lower() == record.get("runtime_receipt_sha256")
            and observation.byte_count == record.get("runtime_receipt_bytes"),
            f"{label} byte binding drifted",
        )
        payload = load_json(path)
        require(isinstance(payload, dict), f"{label} payload is not an object")
        require(
            payload.get("run_id") == record.get("run_id")
            and payload.get("status") == record.get("status"),
            f"{label} payload identity/status drifted",
        )
        return payload

    local = receipt.get("local_gpu_canary")
    require(isinstance(local, dict), "local GPU canary reconciliation is missing")
    require_exact_keys(local, {"predecessor", "successor"}, label="local GPU canary")
    local_predecessor = _verify_bound_runtime_receipt(
        local.get("predecessor"),
        label="local GPU predecessor",
        expected_keys={
            "run_id",
            "runtime_receipt",
            "runtime_receipt_sha256",
            "runtime_receipt_bytes",
            "status",
            "classification",
        },
        expected_values={
            "run_id": "gate5-pythia-canary-20260807T032759Z-bd28ae7e5a85",
            "runtime_receipt_sha256": "476b509b74af27049099611c4b1a6f4d31e64c5f000cb5119e0befb893e673b6",
            "runtime_receipt_bytes": 5057,
            "status": "ENGINEERING GPU CANARY TERMINAL / FAIL_CLOSED",
            "classification": "RETAINED INFRASTRUCTURE STARTUP FAILURE",
        },
    )
    require(
        local_predecessor.get("experiment_status_effect")
        == "LOCAL_CANARY_EXECUTED / GATE5 SCIENTIFIC EXPERIMENT REMAINS NOT_STARTED",
        "local GPU predecessor promotes scientific execution",
    )
    local_successor = _verify_bound_runtime_receipt(
        local.get("successor"),
        label="local GPU successor",
        expected_keys={
            "run_id",
            "runtime_receipt",
            "runtime_receipt_sha256",
            "runtime_receipt_bytes",
            "status",
            "arms_completed",
            "model_id",
            "model_revision",
            "runtime_dtype",
            "hardware",
            "mechanics_observed",
            "prompt_injection_detector_status",
            "steering_efficacy_status",
            "replication_status",
        },
        expected_values={
            "run_id": "gate5-pythia-canary-20260807T035947Z-9f81c34de1b6",
            "runtime_receipt_sha256": "a31064b998dd63366c00501afffb32e4fae044f79449f25d6719feb1a293f8ac",
            "runtime_receipt_bytes": 50746,
            "status": "ENGINEERING GPU CANARY COMPLETE / MECHANICAL PASS",
            "arms_completed": 6,
            "model_id": "EleutherAI/pythia-160m",
            "model_revision": "50f5173d932e8e61f858120bcb800b97af589f46",
            "runtime_dtype": "torch.bfloat16",
            "hardware": "NVIDIA GeForce RTX 4070 Laptop GPU",
            "prompt_injection_detector_status": "NOT VALIDATED / OBSERVED HEURISTIC DISCRIMINATION 0.0",
            "steering_efficacy_status": "NOT ESTABLISHED / STRUCTURALLY_VALID FALSE / OUTPUT DELTA UNATTRIBUTED",
            "replication_status": "POST-FAILURE ADAPTED / NOT INDEPENDENTLY REPLICATED",
        },
    )
    require(
        local.get("successor", {}).get("mechanics_observed")
        == [
            "REAL MODEL LOAD",
            "ACTIVATION CAPTURE",
            "HOOK FIRING",
            "ACTIVATION CHANGE",
            "ABLATION AND MATCHED-CONTROL EXECUTION",
            "HASH-BOUND TERMINAL RECEIPT",
        ]
        and len(local_successor.get("arm_summaries", [])) == 6
        and local_successor.get("mechanical_assessment", {}).get("status") == "PASS"
        and local_successor.get("experiment_status_effect")
        == "LOCAL_CANARY_EXECUTED / GATE5 SCIENTIFIC EXPERIMENT REMAINS NOT_STARTED",
        "local GPU successor mechanics receipt drifted or promotes efficacy",
    )

    joined = receipt.get("joined_controller_worker")
    require(isinstance(joined, dict), "joined execution reconciliation is missing")
    require_exact_keys(joined, {"predecessor", "successor"}, label="joined execution")
    joined_predecessor = _verify_bound_runtime_receipt(
        joined.get("predecessor"),
        label="joined predecessor",
        expected_keys={
            "run_id",
            "runtime_receipt",
            "runtime_receipt_sha256",
            "runtime_receipt_bytes",
            "status",
            "failure_phase",
            "model_invocation_count",
        },
        expected_values={
            "run_id": "gate5-joined-20260807T061801Z-dae9471700c1",
            "runtime_receipt_sha256": "67f69744a6a89a7cd30c6769e2d2cdf1d840e7bb79002fdc8450ce99675b29f9",
            "runtime_receipt_bytes": 2258,
            "status": "FAIL_CLOSED",
            "failure_phase": "PRE-MODEL NETWORK-NONE VERIFIER",
            "model_invocation_count": 0,
        },
    )
    require(
        joined_predecessor.get("model_invocation_count") == 0
        and joined_predecessor.get("packet_status") == "NOT CREATED",
        "joined predecessor negative evidence drifted",
    )
    joined_successor = _verify_bound_runtime_receipt(
        joined.get("successor"),
        label="joined successor",
        expected_keys={
            "run_id",
            "runtime_receipt",
            "runtime_receipt_sha256",
            "runtime_receipt_bytes",
            "status",
            "model_invocation_count",
            "reconciled",
            "packet_status",
            "scientific_efficacy",
            "transport",
            "storage_authority",
            "route_status",
        },
        expected_values={
            "run_id": "gate5-joined-20260807T063024Z-5f22d298b5db",
            "runtime_receipt_sha256": "e926723814539814b981978aa013f28cadd46f635fab57f43eab5b0488648bbd",
            "runtime_receipt_bytes": 3607,
            "status": "SUCCESS_NO_PACKET_RECORDED",
            "model_invocation_count": 1,
            "reconciled": True,
            "packet_status": "NOT CREATED",
            "scientific_efficacy": "NOT ESTABLISHED",
            "transport": "DOCKER_EXEC_LOOPBACK / NETWORK_NONE / LOCAL_ONLY",
            "storage_authority": "LOCAL SINGLE-HOST / NOT WORM / NON-PRODUCTION",
            "route_status": "NON-ADMITTED LOCAL ENGINEERING ROUTE",
        },
    )
    joined_result = joined_successor.get("joined_result")
    require(
        joined_successor.get("model_invocation_count") == 1
        and joined_successor.get("packet_status") == "NOT CREATED"
        and joined_successor.get("scientific_efficacy") == "NOT ESTABLISHED"
        and isinstance(joined_result, dict)
        and joined_result.get("reconciled") is True
        and joined_result.get("status") == "SUCCESS_NO_PACKET_RECORDED",
        "joined successor mechanics receipt drifted or promotes science",
    )

    accounting = receipt.get("provider_accounting")
    require(
        accounting
        == {
            "runpod_used": False,
            "provider_calls": 0,
            "known_spend_usd": "0.00",
            "reported_available_balance_usd": "107.00",
            "balance_evidence_class": "USER REPORTED / PROVIDER LEDGER NOT INSPECTED",
        },
        "engineering-execution provider accounting drifted",
    )
    boundary = receipt.get("claim_boundary")
    require(
        isinstance(boundary, str)
        and "NO PROMPT-INJECTION DETECTION CLAIM" in boundary
        and "NO STEERING EFFICACY CLAIM" in boundary
        and "NO EVIDENCE PACKET" in boundary
        and "EXPERIMENT NOT_STARTED" in boundary
        and "GATE 5 OPEN" in boundary
        and "NOT LICENSED" in boundary
        and "HELD" in boundary,
        "engineering-execution claim boundary is incomplete",
    )


def verify_historical_capability_reconciliation(
    manifest_artifacts: dict[str, dict[str, Any]],
) -> None:
    inventory = load_json(HISTORICAL_CAPABILITY_RECONCILIATION_PATH)
    require(isinstance(inventory, dict), "historical capability inventory is missing")
    require_exact_keys(
        inventory,
        {
            "schema_version",
            "document_status",
            "gate5_status",
            "gate_decision",
            "experimental_execution_status",
            "admission_ring",
            "license_status",
            "disclosure_status",
            "public_disclosure_authorized",
            "product_route_authorized",
            "canon_effect",
            "product_claim_effect",
            "classification",
            "purpose",
            "source_verification",
            "instruction_integrity_shadow_scanner",
            "qwen_prompt_injection_v6_negative",
            "pythia_steering_v6_negative",
            "promotion_and_rerun_policy",
            "claim_boundary",
        },
        label="historical capability inventory",
    )
    require(
        inventory.get("schema_version")
        == "project_coherence.gate5_historical_capability_evidence_reconciliation.v0.1",
        "historical capability inventory schema drifted",
    )
    verify_governance_header(inventory, label="historical capability inventory")
    require(
        inventory.get("classification")
        == "COMPACT SOURCE-BOUND HISTORICAL CAPABILITY INVENTORY / NEGATIVE AND SHADOW EVIDENCE / NOT SCIENTIFIC ADMISSION",
        "historical capability inventory classification promotes evidence",
    )
    require(
        inventory.get("product_route_authorized") is False
        and inventory.get("purpose")
        == "Bind the recovered instruction-integrity shadow scanner and the retained Qwen prompt-injection and Pythia steering negative results to exact Git objects without promoting any scientific, capability, product, license, or rerun claim.",
        "historical capability inventory authorizes a product route or changes purpose",
    )
    inventory_path = HISTORICAL_CAPABILITY_RECONCILIATION_PATH.relative_to(ROOT).as_posix()
    require(
        inventory_path in manifest_artifacts,
        "historical capability inventory is not bound by the Gate 5 manifest",
    )
    source_verification = inventory.get("source_verification")
    require(
        source_verification
        == {
            "method": [
                "git rev-parse <commit>^{commit}",
                "git rev-parse <commit>:<path>",
                "git cat-file -s <blob_oid>",
            ],
            "all_listed_commits_resolved": True,
            "all_listed_blob_oids_and_byte_counts_resolved": True,
            "large_historical_blobs_copied_into_gate5": False,
            "binding_style": "COMMIT + PATH + GIT BLOB OID + BLOB BYTE COUNT",
        },
        "historical capability source-verification contract drifted",
    )

    def _git_stdout(arguments: list[str], *, label: str) -> str:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=ROOT,
            env=_subprocess_environment(),
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )
        require(
            completed.returncode == 0,
            f"{label} is unavailable: {completed.stderr.strip()}",
        )
        return completed.stdout.strip()

    def _verify_commit(commit: Any, *, expected: str, label: str) -> str:
        require(commit == expected, f"{label} commit identity drifted")
        resolved = _git_stdout(
            ["rev-parse", "--verify", f"{expected}^{{commit}}"],
            label=f"{label} commit",
        )
        require(resolved == expected, f"{label} commit does not resolve exactly")
        return expected

    def _verify_artifacts(
        artifacts: Any,
        *,
        commit: str,
        expected: dict[str, dict[str, Any]],
        label: str,
    ) -> None:
        require(isinstance(artifacts, list), f"{label} artifacts are missing")
        require(len(artifacts) == len(expected), f"{label} artifact count drifted")
        observed: dict[str, dict[str, Any]] = {}
        for index, artifact in enumerate(artifacts):
            require(isinstance(artifact, dict), f"{label} artifact {index} is malformed")
            expected_keys = {"path", "git_blob_oid", "blob_byte_count"}
            if "role" in expected[next(iter(expected))]:
                expected_keys.add("role")
            require_exact_keys(
                artifact,
                expected_keys,
                label=f"{label} artifact {index}",
            )
            path = artifact.get("path")
            require(isinstance(path, str) and path in expected, f"{label} path drifted")
            require(path not in observed, f"{label} duplicates artifact path {path!r}")
            expected_record = expected[path]
            require(
                artifact.get("git_blob_oid") == expected_record["git_blob_oid"]
                and artifact.get("blob_byte_count") == expected_record["blob_byte_count"],
                f"{label} declared blob binding drifted for {path}",
            )
            if "role" in expected_record:
                require(artifact.get("role") == expected_record["role"], f"{label} role drifted")
            resolved_blob = _git_stdout(
                ["rev-parse", f"{commit}:{path}"],
                label=f"{label} blob {path}",
            )
            require(
                resolved_blob == expected_record["git_blob_oid"],
                f"{label} Git blob OID drifted for {path}",
            )
            resolved_bytes = _git_stdout(
                ["cat-file", "-s", resolved_blob],
                label=f"{label} byte count {path}",
            )
            require(
                resolved_bytes == str(expected_record["blob_byte_count"]),
                f"{label} Git blob byte count drifted for {path}",
            )
            observed[path] = artifact
        require(set(observed) == set(expected), f"{label} artifact set drifted")

    scanner = inventory.get("instruction_integrity_shadow_scanner")
    require(isinstance(scanner, dict), "historical shadow-scanner evidence is missing")
    require_exact_keys(
        scanner,
        {
            "evidence_class",
            "origin_commit",
            "origin_commit_subject",
            "reconciled_commit",
            "reconciled_commit_subject",
            "artifacts",
            "development_benchmark",
            "heldout_evaluation",
            "operating_invariants",
            "observed_scope",
            "limitations",
            "capability_status",
        },
        label="historical shadow-scanner evidence",
    )
    _verify_commit(
        scanner.get("origin_commit"),
        expected="63f598d14bb4f7201d6dff6f72a5ab59ba93c6c7",
        label="shadow-scanner origin",
    )
    scanner_commit = _verify_commit(
        scanner.get("reconciled_commit"),
        expected=SHADOW_SCANNER_SOURCE_COMMIT,
        label="shadow-scanner reconciliation",
    )
    require(
        scanner.get("evidence_class")
        == "DETERMINISTIC SHADOW FIXTURE EVIDENCE ONLY"
        and scanner.get("origin_commit_subject")
        == "feat: add shadow instruction integrity evidence"
        and scanner.get("reconciled_commit_subject")
        == "feat(harness): reconcile shadow instruction integrity"
        and scanner.get("observed_scope")
        == "The exact deterministic scanner revision passed the exact 15-case development fixture and separately identified 12-case held-out fixture."
        and scanner.get("limitations")
        == [
            "Fixture performance is evidence only for the exact frozen cases and exact scanner revision.",
            "The scanner is a small declared-pattern screen, not a general model-internal prompt-injection detector.",
            "The held-out scaffold is small and is not independent external validation.",
            "No provider, network, model, paid, live-worker, blocking, rewriting, suppression, removal, or acceptance path is exercised.",
            "The results do not establish generalization, production defense, prevention, safety, readiness, or prompt-injection detection efficacy on a model.",
        ],
        "shadow-scanner evidence wording drifted or promotes capability",
    )
    scanner_artifacts = {
        "docs/working/cas_harness_instruction_integrity_spec.md": {
            "git_blob_oid": "9dd800f4dcccdb95568590761fa309c6e3b0e7e9",
            "blob_byte_count": 3532,
        },
        f"{API_ROOT_REL}/api/services/cas_harness_instruction_integrity.py": {
            "git_blob_oid": "aba3c590adbecea471d692194cf7b05b1ea2e981",
            "blob_byte_count": 14432,
        },
        f"{API_ROOT_REL}/api/services/cas_harness_instruction_integrity_benchmark.py": {
            "git_blob_oid": "a5eae6e856e0c7206c1dc73efa852f4f09346e2c",
            "blob_byte_count": 10806,
        },
        f"{API_ROOT_REL}/scenarios/instruction_integrity_benchmark_v0.json": {
            "git_blob_oid": "5c37b9cf1da0feaaf6410681dde0efe44d16bd1b",
            "blob_byte_count": 6905,
        },
        f"{API_ROOT_REL}/scenarios/instruction_integrity_heldout_v0.json": {
            "git_blob_oid": "70aa22e236bbf8da40516a481e81da0878d9ca16",
            "blob_byte_count": 4232,
        },
        f"{API_ROOT_REL}/scripts/run_instruction_integrity_benchmark.py": {
            "git_blob_oid": "b58a122c70d1290f4fd3eef3221a832cca167ccd",
            "blob_byte_count": 1184,
        },
        f"{API_ROOT_REL}/tests/test_cas_harness_instruction_integrity.py": {
            "git_blob_oid": "2db080015d0124a8a40f9bfbc6d01aa5fd442775",
            "blob_byte_count": 5340,
        },
        f"{API_ROOT_REL}/tests/test_cas_harness_instruction_integrity_benchmark.py": {
            "git_blob_oid": "42609aabf449d464d6f1ea91b8a21432bcbc4345",
            "blob_byte_count": 3690,
        },
    }
    _verify_artifacts(
        scanner.get("artifacts"),
        commit=scanner_commit,
        expected=scanner_artifacts,
        label="shadow-scanner",
    )
    scanner_comparison = subprocess.run(
        ["git", "diff", "--quiet", scanner_commit, "--", *scanner_artifacts],
        cwd=ROOT,
        env=_subprocess_environment(),
        capture_output=True,
        check=False,
    )
    require(
        scanner_comparison.returncode == 0,
        "current shadow-scanner files differ from their reconciled source commit",
    )
    require(
        scanner.get("development_benchmark")
        == {
            "suite_id": "instruction_integrity_shadow_v0_20260610",
            "evaluation_role": "development_benchmark",
            "suite_sha256": "3a7dbb45b723fc9acd46c51dbc618db8a6c247d0f864f75efcd7ae56b3e13fb1",
            "cases_run": 15,
            "passed": 15,
            "failed": 0,
            "case_counts_by_lane": {"clean": 4, "control": 5, "injected": 6},
            "passed_by_lane": {"clean": 4, "control": 5, "injected": 6},
            "injected_recall": 1.0,
            "benign_false_positive_rate": 0.0,
            "overall_pass": True,
        }
        and scanner.get("heldout_evaluation")
        == {
            "suite_id": "instruction_integrity_heldout_shadow_v0_20260729",
            "evaluation_role": "held_out_evaluation",
            "suite_sha256": "7d5df4cf55254353f03cdc042372182777a19c1fa06fd6bfbf0f03311a8c1819",
            "cases_run": 12,
            "passed": 12,
            "failed": 0,
            "case_counts_by_lane": {"clean": 2, "control": 5, "injected": 5},
            "passed_by_lane": {"clean": 2, "control": 5, "injected": 5},
            "injected_recall": 1.0,
            "benign_false_positive_rate": 0.0,
            "overall_pass": True,
            "training_data": False,
        },
        "shadow-scanner benchmark evidence drifted",
    )
    require(
        scanner.get("operating_invariants")
        == {
            "mode": "shadow",
            "verdict_effect": "none_shadow_only",
            "automatic_action": "none",
            "live_blocking": False,
            "auto_removal": False,
            "automatic_accept": False,
            "flag_meaning": "FLAG_FOR_HUMAN_REVIEW IS REVIEW-ROUTING METADATA, NOT ACCEPT OR A FINAL VERDICT",
        }
        and scanner.get("capability_status")
        == "SHADOW FIXTURE SCREEN PRESENT / GENERAL PROMPT-INJECTION DETECTION NOT ESTABLISHED",
        "shadow-scanner operating boundary drifted",
    )

    qwen = inventory.get("qwen_prompt_injection_v6_negative")
    require(isinstance(qwen, dict), "historical Qwen V6 evidence is missing")
    require_exact_keys(
        qwen,
        {
            "evidence_class",
            "evidence_commit",
            "model_id",
            "runtime_dtype",
            "artifacts",
            "data_readiness_gate",
            "default_w0_gate",
            "exploratory_valid_sized_risk_split",
            "claim_status",
            "scientific_disposition",
            "limitations",
            "reuse_policy",
        },
        label="historical Qwen V6 evidence",
    )
    qwen_commit = _verify_commit(
        qwen.get("evidence_commit"),
        expected="6a35633a4ed58402edf1c6558ec1f00258a9ee44",
        label="Qwen V6 evidence",
    )
    require(
        qwen.get("evidence_class") == "RETAINED MATCHED-PROMPT W0 NEGATIVE RESULT"
        and qwen.get("limitations")
        == [
            "The READY_FOR_W0_CAPTURE data gate authorizes capture only; it licenses no detector, prevention, removal, reversal, interception, or causal claim.",
            "Repeated exact prompts share a deterministic W0 vector in ordinary inference, so mixed outcomes do not establish sample-specific stochastic branch prediction.",
            "The best valid-sized layer tied the text control and failed the frozen gates.",
            "No layer passed the all-layer exploratory scan.",
            "Do not run or infer causal steering or ablation from this W0 result.",
        ],
        "historical Qwen V6 boundary wording drifted",
    )
    qwen_artifacts = {
        f"{API_ROOT_REL}/docs/working/qwen_v6_matched_prespeech_w0_result_20260615.md": {
            "role": "result_summary",
            "git_blob_oid": "edfc10baa507cae615e3ae42b2755c07432fedb2",
            "blob_byte_count": 4357,
        },
        f"{API_ROOT_REL}/docs/working/qwen_v6_matched_prespeech_eval_seed00_47_v2_20260615/layer_28_exploratory_threshold_low0125_high030_full.json": {
            "role": "best_full_control_layer_report",
            "git_blob_oid": "a4e1f65f651cc47a405936e4053c280507297b5f",
            "blob_byte_count": 4517,
        },
        f"{API_ROOT_REL}/docs/working/qwen_v6_matched_chain_break_combined_gate_seed00_47_v2_20260615/combined_gate_manifest.json": {
            "role": "combined_data_gate_manifest",
            "git_blob_oid": "5ae0ba84996604b0adc52c75485a6dd435d5abc0",
            "blob_byte_count": 3531,
        },
        f"{API_ROOT_REL}/docs/working/qwen_v6_matched_chain_break_combined_gate_seed00_47_v2_20260615/combined_matched_screen_report.json": {
            "role": "combined_data_screen_report",
            "git_blob_oid": "0c0e31a931fd21d6088530a35112e7e2c2c8b8f4",
            "blob_byte_count": 3663,
        },
    }
    _verify_artifacts(
        qwen.get("artifacts"), commit=qwen_commit, expected=qwen_artifacts, label="Qwen V6"
    )
    require(
        qwen.get("model_id") == "Qwen/Qwen2.5-1.5B-Instruct"
        and qwen.get("runtime_dtype") == "float16"
        and qwen.get("data_readiness_gate")
        == {
            "status": "READY_FOR_W0_CAPTURE",
            "row_count": 1312,
            "chain_status_distribution": {"BROKEN": 306, "INTACT": 1006},
            "payload_classes": 5,
            "mixed_exact_prompt_groups": 40,
            "meaning": "DATA READINESS ONLY / NOT A DETECTION OR PRODUCT CLAIM",
        }
        and qwen.get("default_w0_gate")
        == {
            "status": "BLOCKED",
            "high_break_risk_groups": 7,
            "low_break_risk_groups": 7,
            "required_groups_per_risk_class": 10,
            "floor_result": "7 / 7 OBSERVED VS 10 / 10 REQUIRED",
        }
        and qwen.get("exploratory_valid_sized_risk_split")
        == {
            "layers_scanned": 29,
            "layers_passed": 0,
            "best_full_control_layer": 28,
            "status": "FAIL",
            "risk_hidden_balanced_accuracy": 0.809091,
            "risk_text_hash_balanced_accuracy": 0.809091,
            "hidden_minus_text_balanced_accuracy": 0.0,
            "within_payload_permutation_p": 0.008991,
        }
        and qwen.get("claim_status") == "OPEN / NOT LICENSED"
        and qwen.get("scientific_disposition")
        == "NEGATIVE RESULT / INTERNAL W0 PROMPT-INJECTION DETECTOR NOT ESTABLISHED"
        and qwen.get("reuse_policy")
        == "NEGATIVE CONTROL EVIDENCE ONLY / DO NOT PROMOTE / DO NOT USE AS A STEERING TARGET / NO RERUN AUTHORIZED OR IMPLIED",
        "historical Qwen V6 negative result drifted or was promoted",
    )

    pythia = inventory.get("pythia_steering_v6_negative")
    require(isinstance(pythia, dict), "historical Pythia V6 evidence is missing")
    require_exact_keys(
        pythia,
        {
            "evidence_class",
            "evidence_commit",
            "execution_source_commit",
            "run_id",
            "request_count",
            "artifacts",
            "terminal_status",
            "audit_status",
            "audit_numeric_contract_exact_agreement",
            "scientific_readout",
            "failed_scientific_and_control_gates",
            "claim_status",
            "scientific_disposition",
            "limitations",
            "reuse_policy",
        },
        label="historical Pythia V6 evidence",
    )
    pythia_commit = _verify_commit(
        pythia.get("evidence_commit"),
        expected="0d1d7aa94afd04cbb88681f905f9a9618c3cb621",
        label="Pythia V6 evidence",
    )
    require(
        pythia.get("evidence_class")
        == "RETAINED LAYER-SPECIFICITY STEERING NEGATIVE RESULT"
        and pythia.get("claim_status") == "RESEARCH_ONLY / NO DECISION AUTHORITY"
        and pythia.get("limitations")
        == [
            "Exact executor-auditor numeric agreement validates the retained calculation and artifact path, not the scientific hypothesis.",
            "The common readout was at chance and the target-layer dose response ran in the wrong direction.",
            "Off-target layers, same-norm random directions, and wrong-axis controls were too large.",
            "The run establishes no live steering, safety steering, prompt-injection detection, blocking, removal, prevention, or product capability.",
            "The terminal evidence is NON_REUSABLE / NO RETRY and cannot be converted into a positive claim by reinterpretation.",
        ],
        "historical Pythia V6 boundary wording drifted or promotes authority",
    )
    _verify_commit(
        pythia.get("execution_source_commit"),
        expected="acfed1a32fc197fd88b62df96c97abf07a59ecca",
        label="Pythia V6 execution source",
    )
    pythia_base = (
        "docs/working/research_intervention_pythia160m_v6_execution/runs/"
        "pythia160m-riv6-20260729173650e26e483ed6fae22ba30a"
    )
    pythia_artifacts = {
        f"{pythia_base}/result.json": {
            "role": "execution_result",
            "git_blob_oid": "0bf792ab4855fe6df9b9735b8d78d3bb94ab9f9f",
            "blob_byte_count": 2539956,
        },
        f"{pythia_base}/independent_audit.json": {
            "role": "independent_audit",
            "git_blob_oid": "b0b061ea0ec0c70d130229baeeaa9d529a13279c",
            "blob_byte_count": 2611,
        },
        f"{pythia_base}/TERMINAL_EVIDENCE_MANIFEST.json": {
            "role": "terminal_evidence_manifest",
            "git_blob_oid": "0ff9d017b6346f56dfbaa3e1cca862d4447018d8",
            "blob_byte_count": 4769,
        },
    }
    _verify_artifacts(
        pythia.get("artifacts"),
        commit=pythia_commit,
        expected=pythia_artifacts,
        label="Pythia V6",
    )
    require(
        pythia.get("run_id") == "pythia160m-riv6-20260729173650e26e483ed6fae22ba30a"
        and pythia.get("request_count") == 1536
        and pythia.get("terminal_status")
        == "FAIL_CLOSED / SCIENTIFIC_AND_CONTROL_GATES_FAILED / NON_REUSABLE / NO RETRY"
        and pythia.get("audit_status") == "FAIL_CLOSED"
        and pythia.get("audit_numeric_contract_exact_agreement") is True
        and pythia.get("scientific_readout")
        == {
            "common_readout_balanced_accuracy": 0.5,
            "target_layer_spearman_rho": -1.0,
            "off_target_to_target_point_ratio_by_sign": {
                "-0.5": 4.232726531704558,
                "0.5": 6.304563809268991,
            },
            "same_norm_random_direction_ratio_by_sign": {
                "-0.5": 2.5700177404408064,
                "0.5": 3.9739944811979195,
            },
            "wrong_axis_ratio_by_sign": {
                "-0.5": 2.587795696333962,
                "0.5": 3.9048408945255755,
            },
        }
        and pythia.get("failed_scientific_and_control_gates")
        == [
            "common_readout_validity",
            "target_layer_dose_response",
            "layer_specificity",
            "non_layer_controls",
        ]
        and pythia.get("scientific_disposition")
        == "NEGATIVE RESULT / STEERING CAPABILITY NOT ESTABLISHED"
        and pythia.get("reuse_policy")
        == "NON_REUSABLE / NO RETRY / NEGATIVE CONTROL EVIDENCE ONLY / NO RERUN AUTHORIZED OR IMPLIED",
        "historical Pythia V6 negative result drifted or was promoted",
    )

    require(
        inventory.get("promotion_and_rerun_policy")
        == {
            "scientific_promotion": "PROHIBITED",
            "capability_promotion": "PROHIBITED",
            "product_promotion": "PROHIBITED",
            "license_promotion": "PROHIBITED",
            "gate_promotion": "PROHIBITED",
            "rerun_inference": "PROHIBITED",
            "binding_rule": (
                "No item in this inventory authorizes, requests, predicts, or implies a rerun. "
                "Any future experiment requires a separately frozen protocol, explicit authorization, "
                "matched controls, new execution evidence, and independent review. A future run must "
                "not rewrite or reinterpret these retained negative results."
            ),
        },
        "historical capability promotion/rerun policy drifted",
    )
    boundary = inventory.get("claim_boundary")
    require(
        isinstance(boundary, str)
        and "NO GENERAL PROMPT-INJECTION DETECTION CLAIM" in boundary
        and "NO STEERING CAPABILITY CLAIM" in boundary
        and "NO PRODUCT VALIDATION" in boundary
        and "NO ACCEPT" in boundary
        and "EXPERIMENT NOT_STARTED" in boundary
        and "NO RERUN AUTHORIZED OR IMPLIED" in boundary,
        "historical capability claim boundary is incomplete",
    )


def verify_review_matrix(
    manifest_artifacts: dict[str, dict[str, Any]],
) -> tuple[int, int]:
    matrix = load_json(REVIEW_MATRIX_PATH)
    require(isinstance(matrix, dict), "review matrix root is not an object")
    require_exact_keys(
        matrix,
        {
            "schema_version",
            "document_status",
            "gate5_status",
            "experimental_execution_status",
            "gate_decision",
            "admission_ring",
            "license_status",
            "disclosure_status",
            "public_disclosure_authorized",
            "product_route_authorized",
            "canon_effect",
            "product_claim_effect",
            "criterion_count",
            "implemented_or_hash_verified_count",
            "preserved_negative_evidence_count",
            "open_criterion_count",
            "disposition_counts",
            "kernel_schemas",
            "review_basis",
            "receipts",
            "criteria",
        },
        label="Gate 5 review matrix",
    )
    require(
        matrix.get("schema_version") == "project_coherence.gate5_review_matrix.v0.1",
        "unexpected Gate 5 review-matrix schema",
    )
    require(
        matrix.get("document_status") == "DRAFT / OPEN / NOT FROZEN",
        "Gate 5 review matrix is not explicitly draft/open/unfrozen",
    )
    require(matrix.get("gate5_status") == "OPEN", "Gate 5 review matrix closes the gate")
    require(
        matrix.get("experimental_execution_status") == "NOT_STARTED",
        "Gate 5 review matrix promotes experimental execution",
    )
    require(
        matrix.get("gate_decision") == "KEEP_OPEN",
        "Gate 5 review matrix attempts to close the gate",
    )
    require(
        type(matrix.get("admission_ring")) is int and matrix["admission_ring"] == 4,
        "Gate 5 review matrix escaped Ring 4 or used a non-integer ring",
    )
    require(
        matrix.get("license_status") == "NOT LICENSED",
        "Gate 5 review matrix licenses claims",
    )
    require(matrix.get("disclosure_status") == "HELD", "Gate 5 matrix is not HELD")
    require(
        matrix.get("public_disclosure_authorized") is False,
        "Gate 5 matrix authorizes public disclosure",
    )
    require(
        matrix.get("product_route_authorized") is False,
        "Gate 5 matrix authorizes a product route",
    )
    require(matrix.get("canon_effect") == "NONE", "Gate 5 matrix claims canon effect")
    require(
        matrix.get("product_claim_effect") == "NONE",
        "Gate 5 matrix claims product-claim effect",
    )
    require(
        matrix.get("kernel_schemas")
        == [
            "cas_harness_v2.preregistration.v1",
            "cas_harness_v2.preregistration_amendment.v1",
            "cas_harness_v2.worker_authorization.v1",
            "cas_harness_v2.worker_terminal_receipt.v1",
            "cas_harness_v2.outcome_access_event.v1",
            "cas_harness_v2.evidence_packet.v2",
        ],
        "Gate 5 review matrix kernel-schema list drifted",
    )
    require(
        isinstance(matrix.get("review_basis"), str)
        and "No criterion creates ACCEPT, LICENSED, an enabled public route, or a product route."
        in matrix["review_basis"],
        "Gate 5 review basis omits its non-promotion boundary",
    )
    criteria = matrix.get("criteria")
    require(
        isinstance(criteria, list) and len(criteria) >= len(REQUIRED_OPEN_BOUNDARY_IDS),
        "review matrix does not cover the complete Gate 5 boundary surface",
    )
    criterion_ids: list[str] = []
    disposition_counts: dict[str, int] = {}
    criteria_by_id: dict[str, dict[str, Any]] = {}
    implemented_remaining_refs: dict[str, set[str]] = {}
    gate4 = load_json(GATE4_MANIFEST_PATH)
    gate4_artifacts = gate4.get("artifacts") if isinstance(gate4, dict) else None
    require(isinstance(gate4_artifacts, list), "Gate 4 transitive artifacts are unavailable")
    transitive_evidence_paths = {
        record.get("path")
        for record in gate4_artifacts
        if isinstance(record, dict) and isinstance(record.get("path"), str)
    }
    bound_evidence_paths = set(manifest_artifacts) | transitive_evidence_paths
    for index, criterion in enumerate(criteria):
        require(isinstance(criterion, dict), f"criterion {index} is not an object")
        require_exact_keys(
            criterion,
            {
                "id",
                "subsystem",
                "question",
                "acceptance_requirement",
                "observed_result",
                "disposition",
                "evidence_refs",
                "canon_effect",
                "product_claim_effect",
                "remaining_obligation",
            },
            label=f"criterion {index}",
        )
        criterion_id = criterion.get("id")
        require(
            isinstance(criterion_id, str) and re.fullmatch(r"G5-[A-Z0-9-]+", criterion_id),
            f"criterion {index} has an invalid ID",
        )
        criterion_ids.append(criterion_id)
        criteria_by_id[criterion_id] = criterion
        for field in (
            "subsystem",
            "question",
            "acceptance_requirement",
            "observed_result",
        ):
            require(
                isinstance(criterion.get(field), str) and criterion[field].strip(),
                f"{criterion_id}: {field} is missing",
            )
        disposition = criterion.get("disposition")
        require(
            disposition in REVIEW_DISPOSITIONS,
            f"{criterion_id}: invalid disposition {disposition!r}",
        )
        disposition_counts[disposition] = disposition_counts.get(disposition, 0) + 1
        evidence_refs = criterion.get("evidence_refs")
        require(
            isinstance(evidence_refs, list)
            and evidence_refs
            and all(isinstance(ref, str) and ref for ref in evidence_refs),
            f"{criterion_id}: evidence_refs is empty or malformed",
        )
        for evidence_ref in evidence_refs:
            artifact_path = evidence_ref.split("::", 1)[0]
            require(
                artifact_path in bound_evidence_paths
                or any(
                    artifact.startswith(artifact_path.rstrip("/") + "/")
                    for artifact in bound_evidence_paths
                ),
                f"{criterion_id}: evidence is not hash-bound by Gate 5: {evidence_ref}",
            )
        require(
            criterion.get("canon_effect") == "NONE",
            f"{criterion_id}: claims canon effect",
        )
        require(
            criterion.get("product_claim_effect") == "NONE",
            f"{criterion_id}: claims product-claim effect",
        )
        remaining = criterion.get("remaining_obligation")
        if disposition in OPEN_REVIEW_DISPOSITIONS:
            require(
                isinstance(remaining, str) and remaining.strip(),
                f"{criterion_id}: open criterion lacks a closure obligation",
            )
        elif disposition == "PRESERVED_NEGATIVE_EVIDENCE":
            require(
                isinstance(remaining, str) and remaining.strip(),
                f"{criterion_id}: preserved negative evidence lacks a retention obligation",
            )
        else:
            if remaining is not None:
                require(
                    isinstance(remaining, str) and remaining.strip(),
                    f"{criterion_id}: implemented criterion has a malformed scope boundary",
                )
                referenced_ids = set(re.findall(r"G5-[A-Z0-9-]+", remaining))
                require(
                    referenced_ids,
                    f"{criterion_id}: implemented scope boundary does not cite an OPEN criterion",
                )
                implemented_remaining_refs[criterion_id] = referenced_ids
    require(
        len(criterion_ids) == len(set(criterion_ids)),
        "review matrix has duplicate criterion IDs",
    )
    implemented_ids = {
        criterion_id
        for criterion_id, criterion in criteria_by_id.items()
        if criterion.get("disposition")
        in {"IMPLEMENTED_AND_REGRESSION_TESTED", "IMPLEMENTED_AND_HASH_VERIFIED"}
    }
    require(
        REQUIRED_IMPLEMENTED_CRITERION_IDS <= implemented_ids,
        "review matrix omits required implemented controls: "
        f"{sorted(REQUIRED_IMPLEMENTED_CRITERION_IDS - implemented_ids)}",
    )
    negative_ids = {
        criterion_id
        for criterion_id, criterion in criteria_by_id.items()
        if criterion.get("disposition") == "PRESERVED_NEGATIVE_EVIDENCE"
    }
    require(
        REQUIRED_NEGATIVE_CRITERION_IDS <= negative_ids,
        "review matrix omits required preserved negative evidence",
    )
    for criterion_id, referenced_ids in implemented_remaining_refs.items():
        require(
            all(
                referenced_id in criteria_by_id
                and criteria_by_id[referenced_id].get("disposition")
                in OPEN_REVIEW_DISPOSITIONS
                for referenced_id in referenced_ids
            ),
            f"{criterion_id}: implemented scope boundary does not resolve only to OPEN criteria",
        )
    for boundary_id, acceptable_criteria in BOUNDARY_CRITERION_BINDINGS.items():
        matching = [
            criterion_id
            for criterion_id in acceptable_criteria
            if criterion_id in criteria_by_id
            and criteria_by_id[criterion_id].get("disposition")
            in OPEN_REVIEW_DISPOSITIONS
        ]
        require(
            matching,
            f"review matrix does not preserve {boundary_id}; expected one of "
            f"{sorted(acceptable_criteria)} as OPEN",
        )
    security = criteria_by_id.get("G5-ENGINEERING-003")
    require(
        isinstance(security, dict) and security.get("disposition") == "OPEN_SECURITY",
        "dependency-security boundary is not an explicit OPEN_SECURITY hold",
    )

    actual_disposition_counts = {
        disposition: count for disposition, count in sorted(disposition_counts.items())
    }
    require(
        type(matrix.get("criterion_count")) is int
        and matrix["criterion_count"] == len(criteria),
        "review-matrix declared criterion count drifted",
    )
    require(
        type(matrix.get("implemented_or_hash_verified_count")) is int
        and matrix["implemented_or_hash_verified_count"] == len(implemented_ids),
        "review-matrix implemented/hash-verified count drifted",
    )
    require(
        type(matrix.get("preserved_negative_evidence_count")) is int
        and matrix["preserved_negative_evidence_count"] == len(negative_ids),
        "review-matrix preserved-negative count drifted",
    )
    open_count = sum(
        count
        for disposition, count in disposition_counts.items()
        if disposition in OPEN_REVIEW_DISPOSITIONS
    )
    require(
        type(matrix.get("open_criterion_count")) is int
        and matrix["open_criterion_count"] == open_count,
        "review-matrix open count drifted",
    )
    declared_counts = matrix.get("disposition_counts")
    require(
        isinstance(declared_counts, dict)
        and all(type(value) is int for value in declared_counts.values())
        and {key: declared_counts[key] for key in sorted(declared_counts)}
        == actual_disposition_counts,
        "review-matrix disposition counts drifted",
    )

    receipts = matrix.get("receipts")
    require(isinstance(receipts, dict), "review matrix receipts are missing")
    require_exact_keys(
        receipts,
        {
            "kernel_focused",
            "worker_protocol_kernel",
            "worker_protocol_bridge_and_durable_seams",
            "prospective_lifecycle_sqlite_dark_route",
            "admitted_adapter_and_bounded_reconciliation",
            "local_gpu_and_joined_engineering",
            "instruction_integrity_shadow_scanner",
            "worker_checkpoints",
            "api_launcher_fleet_state",
            "successor_dependency_container_candidate",
            "local_test_runner",
            "raw_build_and_security_evidence",
            "historical_recovery",
        },
        label="review matrix receipts",
    )
    kernel_receipt = receipts.get("kernel_focused")
    require(isinstance(kernel_receipt, dict), "kernel receipt is missing")
    require_exact_keys(
        kernel_receipt,
        {"command", "passed_tests", "passed_subtests", "scope"},
        label="review matrix kernel receipt",
    )
    require(
        type(kernel_receipt.get("passed_tests")) is int
        and kernel_receipt["passed_tests"]
        == REQUIRED_TEST_SUITES["Harness v2 kernel and history"]["expected_tests"]
        and type(kernel_receipt.get("passed_subtests")) is int
        and kernel_receipt["passed_subtests"]
        == REQUIRED_TEST_SUITES["Harness v2 kernel and history"]["expected_subtests"],
        "review-matrix Harness v2 receipt drifted",
    )
    protocol_receipt = receipts.get("worker_protocol_kernel")
    require(
        isinstance(protocol_receipt, dict),
        "review-matrix worker-protocol kernel receipt is missing",
    )
    require_exact_keys(
        protocol_receipt,
        {
            "passed_tests",
            "passed_subtests",
            "test_ids_sha256",
            "independently_reproduced",
            "scope",
        },
        label="review-matrix worker-protocol kernel receipt",
    )
    protocol_subset = REQUIRED_SUBSUITE_DIGESTS["worker protocol kernel"]
    require(
        type(protocol_receipt.get("passed_tests")) is int
        and protocol_receipt["passed_tests"] == protocol_subset["expected_tests"]
        and type(protocol_receipt.get("passed_subtests")) is int
        and protocol_receipt["passed_subtests"]
        == protocol_subset["expected_subtests"]
        and protocol_receipt.get("test_ids_sha256")
        == protocol_subset["expected_test_ids_sha256"].lower()
        and protocol_receipt.get("independently_reproduced") is False
        and isinstance(protocol_receipt.get("scope"), str)
        and "LOCAL_UNATTESTED_HOST_REGRESSION" in protocol_receipt["scope"]
        and "no authentication" in protocol_receipt["scope"].lower(),
        "review-matrix worker-protocol kernel receipt drifted or promotes authority",
    )
    worker_receipt = receipts.get("worker_checkpoints")
    require(isinstance(worker_receipt, dict), "worker receipt is missing")
    require_exact_keys(
        worker_receipt,
        {
            "intervention_integrity_adversarial_tests",
            "intervention_integrity_focused_tests",
            "intervention_integrity_complete_tests",
            "weights_identity_complete_tests",
            "latest_numeric_redteam_passed",
            "latest_numeric_redteam_failed",
            "numeric_test_ids_sha256",
            "current_complete_passed",
            "current_complete_failed",
            "current_complete_total",
            "complete_test_ids_sha256",
            "prior_independently_confirmed_complete_passed",
            "prior_independently_confirmed_test_ids_sha256",
            "test_id_digest_kind",
            "node_id_digest_rule",
            "current_candidate_green",
            "receipt_freeze_status",
            "independent_freeze_confirmed",
            "current_complete_green_receipt",
            "scope",
        },
        label="review matrix worker receipt",
    )
    for field, expected in {
        "intervention_integrity_adversarial_tests": 13,
        "intervention_integrity_focused_tests": 76,
        "intervention_integrity_complete_tests": 255,
        "weights_identity_complete_tests": 257,
        "latest_numeric_redteam_passed": 32,
        "latest_numeric_redteam_failed": 0,
        "current_complete_passed": 391,
        "current_complete_failed": 0,
        "current_complete_total": 391,
        "prior_independently_confirmed_complete_passed": 290,
    }.items():
        require(
            type(worker_receipt.get(field)) is int
            and worker_receipt[field] == expected,
            f"review-matrix worker receipt field {field!r} drifted",
        )
    require(
        worker_receipt.get("test_id_digest_kind")
        == "SAME_PROCESS_EXECUTED_NODE_ID_SET_SHA256 / LOCAL_UNATTESTED_HOST_REGRESSION"
        and worker_receipt.get("current_candidate_green") is True,
        "review-matrix worker receipt kind or bounded-green status drifted",
    )
    require(
        worker_receipt.get("numeric_test_ids_sha256")
        == REQUIRED_TEST_SUITES["Live trace worker numeric red team"][
            "expected_test_ids_sha256"
        ].lower()
        and worker_receipt.get("complete_test_ids_sha256")
        == REQUIRED_TEST_SUITES["Live trace worker complete"][
            "expected_test_ids_sha256"
        ].lower(),
        "review-matrix worker node-ID digests differ from verifier-native receipts",
    )
    require(
        worker_receipt.get("receipt_freeze_status")
        == "LOCAL_UNATTESTED_HOST_REGRESSION / NOT INDEPENDENTLY REPRODUCED"
        and worker_receipt.get("independent_freeze_confirmed") is False
        and worker_receipt.get("current_complete_green_receipt") is True,
        "review matrix promotes the locally green successor to independent reproduction",
    )
    require(
        worker_receipt.get("prior_independently_confirmed_test_ids_sha256")
        == "1c8db623fc6507db0b4ce218c3fd60833d514503122cd68fa79644a61db6c635",
        "review matrix erased the prior independently confirmed 290-test checkpoint",
    )
    digest_rule = worker_receipt.get("node_id_digest_rule")
    require(
        isinstance(digest_rule, str)
        and "live-trace-worker/" in digest_rule
        and "Python ordinal" in digest_rule
        and "final" in digest_rule
        and "LF" in digest_rule,
        "review-matrix node-ID digest rule omits prefix/order/final-LF canonicalization",
    )
    api_receipt = receipts.get("api_launcher_fleet_state")
    require(isinstance(api_receipt, dict), "review-matrix API/launcher receipt is missing")
    require_exact_keys(
        api_receipt,
        {"passed", "failed", "total", "test_ids_sha256", "independently_reproduced", "scope"},
        label="review-matrix API/launcher receipt",
    )
    api_suite = REQUIRED_TEST_SUITES["API, fleet state, and launcher identity"]
    require(
        type(api_receipt.get("passed")) is int
        and api_receipt["passed"] == api_suite["expected_tests"]
        and type(api_receipt.get("failed")) is int
        and api_receipt["failed"] == 0
        and type(api_receipt.get("total")) is int
        and api_receipt["total"] == api_suite["expected_tests"]
        and api_receipt.get("test_ids_sha256")
        == api_suite["expected_test_ids_sha256"].lower()
        and api_receipt.get("independently_reproduced") is False
        and isinstance(api_receipt.get("scope"), str)
        and "LOCAL_UNATTESTED_HOST_REGRESSION" in api_receipt["scope"]
        and "not hermetic worker-to-kernel integration" in api_receipt["scope"],
        "review-matrix API/launcher receipt drifted or overclaims independence",
    )
    bridge_receipt = receipts.get("worker_protocol_bridge_and_durable_seams")
    require(
        isinstance(bridge_receipt, dict),
        "review-matrix worker-protocol bridge receipt is missing",
    )
    bridge_scope = bridge_receipt.get("scope")
    require_exact_keys(
        bridge_receipt,
        {
            "bridge_passed",
            "bridge_test_ids_sha256",
            "callback_and_object_lock_seam_passed",
            "callback_and_object_lock_seam_test_ids_sha256",
            "independently_reproduced",
            "scope",
        },
        label="review-matrix worker-protocol bridge receipt",
    )
    bridge_suite = REQUIRED_TEST_SUITES["Harness v2 worker terminal bridge"]
    seam_suite = REQUIRED_TEST_SUITES[
        "Durable fleet callback and Object-Lock repository seams"
    ]
    require(
        type(bridge_receipt.get("bridge_passed")) is int
        and bridge_receipt["bridge_passed"] == bridge_suite["expected_tests"]
        and bridge_receipt.get("bridge_test_ids_sha256")
        == bridge_suite["expected_test_ids_sha256"].lower()
        and type(bridge_receipt.get("callback_and_object_lock_seam_passed")) is int
        and bridge_receipt["callback_and_object_lock_seam_passed"]
        == seam_suite["expected_tests"]
        and bridge_receipt.get("callback_and_object_lock_seam_test_ids_sha256")
        == seam_suite["expected_test_ids_sha256"].lower()
        and bridge_receipt.get("independently_reproduced") is False
        and isinstance(bridge_scope, str)
        and "LOCAL_UNATTESTED_HOST_REGRESSION" in bridge_scope
        and "default-dark" in bridge_scope.lower()
        and "admitted adapter" in bridge_scope.lower()
        and "request-bound" in bridge_scope.lower()
        and "active-lease" in bridge_scope.lower()
        and "no live" in bridge_scope.lower()
        and "scientific" in bridge_scope.lower(),
        "review-matrix worker-protocol bridge receipt drifted or promotes authority",
    )
    lifecycle_receipt = receipts.get("prospective_lifecycle_sqlite_dark_route")
    require(
        isinstance(lifecycle_receipt, dict),
        "review-matrix prospective lifecycle receipt is missing",
    )
    require_exact_keys(
        lifecycle_receipt,
        {
            "passed",
            "failed",
            "total",
            "passed_subtests",
            "test_ids_sha256",
            "route_enabled",
            "packaged_adapter_admitted",
            "independently_reproduced",
            "scope",
        },
        label="review-matrix prospective lifecycle receipt",
    )
    lifecycle_suite = REQUIRED_TEST_SUITES[
        "Harness v2 prospective lifecycle, SQLite, and dark route"
    ]
    lifecycle_scope = lifecycle_receipt.get("scope")
    require(
        type(lifecycle_receipt.get("passed")) is int
        and lifecycle_receipt["passed"] == lifecycle_suite["expected_tests"]
        and type(lifecycle_receipt.get("failed")) is int
        and lifecycle_receipt["failed"] == 0
        and type(lifecycle_receipt.get("total")) is int
        and lifecycle_receipt["total"] == lifecycle_suite["expected_tests"]
        and type(lifecycle_receipt.get("passed_subtests")) is int
        and lifecycle_receipt["passed_subtests"]
        == lifecycle_suite["expected_subtests"]
        and lifecycle_receipt.get("test_ids_sha256")
        == lifecycle_suite["expected_test_ids_sha256"].lower()
        and lifecycle_receipt.get("route_enabled") is False
        and lifecycle_receipt.get("packaged_adapter_admitted") is True
        and lifecycle_receipt.get("independently_reproduced") is False
        and isinstance(lifecycle_scope, str)
        and "LOCAL_UNATTESTED_HOST_REGRESSION" in lifecycle_scope
        and "close/reopen" in lifecycle_scope.lower()
        and "same-file" in lifecycle_scope.lower()
        and "transitively" in lifecycle_scope.lower()
        and "active-lease" in lifecycle_scope.lower()
        and "no live" in lifecycle_scope.lower()
        and "not scientific" in lifecycle_scope.lower(),
        "review-matrix prospective lifecycle receipt drifted or promotes authority",
    )
    adapter_receipt = receipts.get("admitted_adapter_and_bounded_reconciliation")
    require(
        isinstance(adapter_receipt, dict),
        "review-matrix admitted-adapter/reconciliation receipt is missing",
    )
    require_exact_keys(
        adapter_receipt,
        {
            "passed",
            "failed",
            "total",
            "passed_subtests",
            "test_ids_sha256",
            "route_enabled",
            "configured_scope_only",
            "independently_reproduced",
            "scope",
        },
        label="review matrix admitted-adapter/reconciliation receipt",
    )
    adapter_suite = REQUIRED_TEST_SUITES[
        "Harness v2 admitted adapter and bounded reconciliation"
    ]
    adapter_scope = adapter_receipt.get("scope")
    require(
        type(adapter_receipt.get("passed")) is int
        and adapter_receipt["passed"] == adapter_suite["expected_tests"]
        and adapter_receipt.get("failed") == 0
        and adapter_receipt.get("total") == adapter_suite["expected_tests"]
        and adapter_receipt.get("passed_subtests")
        == adapter_suite["expected_subtests"]
        and adapter_receipt.get("test_ids_sha256")
        == adapter_suite["expected_test_ids_sha256"].lower()
        and adapter_receipt.get("route_enabled") is False
        and adapter_receipt.get("configured_scope_only") is True
        and adapter_receipt.get("independently_reproduced") is False
        and isinstance(adapter_scope, str)
        and "LOCAL_UNATTESTED_HOST_REGRESSION" in adapter_scope
        and "configured-scope" in adapter_scope.lower()
        and "off-registry absence" in adapter_scope.lower()
        and "does not establish" in adapter_scope.lower()
        and "provider-backed durability" in adapter_scope.lower()
        and "live execution" in adapter_scope.lower(),
        "review-matrix admitted-adapter/reconciliation receipt drifted or promotes authority",
    )
    engineering_execution_receipt = receipts.get("local_gpu_and_joined_engineering")
    require(
        isinstance(engineering_execution_receipt, dict),
        "review-matrix local GPU/joined engineering receipt is missing",
    )
    require_exact_keys(
        engineering_execution_receipt,
        {
            "receipt",
            "retained_evidence_tests",
            "test_ids_sha256",
            "local_gpu_predecessor_status",
            "local_gpu_successor_status",
            "local_gpu_arms_completed",
            "joined_predecessor_status",
            "joined_predecessor_model_invocations",
            "joined_successor_status",
            "joined_successor_model_invocations",
            "joined_successor_reconciled",
            "packet_status",
            "scientific_efficacy",
            "independently_reproduced",
            "runpod_used",
            "known_spend_usd",
            "scope",
        },
        label="review-matrix local GPU/joined engineering receipt",
    )
    execution_scope = engineering_execution_receipt.get("scope")
    require(
        engineering_execution_receipt
        == {
            "receipt": ENGINEERING_EXECUTION_RECONCILIATION_PATH.relative_to(ROOT).as_posix(),
            "retained_evidence_tests": REQUIRED_TEST_SUITES[
                "Gate 5 retained local GPU and joined evidence"
            ]["expected_tests"],
            "test_ids_sha256": REQUIRED_TEST_SUITES[
                "Gate 5 retained local GPU and joined evidence"
            ]["expected_test_ids_sha256"].lower(),
            "local_gpu_predecessor_status": "ENGINEERING GPU CANARY TERMINAL / FAIL_CLOSED",
            "local_gpu_successor_status": "ENGINEERING GPU CANARY COMPLETE / MECHANICAL PASS",
            "local_gpu_arms_completed": 6,
            "joined_predecessor_status": "FAIL_CLOSED",
            "joined_predecessor_model_invocations": 0,
            "joined_successor_status": "SUCCESS_NO_PACKET_RECORDED",
            "joined_successor_model_invocations": 1,
            "joined_successor_reconciled": True,
            "packet_status": "NOT CREATED",
            "scientific_efficacy": "NOT ESTABLISHED",
            "independently_reproduced": False,
            "runpod_used": False,
            "known_spend_usd": "0.00",
            "scope": execution_scope,
        }
        and isinstance(execution_scope, str)
        and "LOCAL_UNATTESTED_ENGINEERING_EXECUTION" in execution_scope
        and "no validated prompt-injection detector" in execution_scope
        and "no steering efficacy" in execution_scope
        and "no Evidence Packet" in execution_scope
        and "no authenticated scientific execution" in execution_scope,
        "review-matrix local GPU/joined receipt drifted or promotes efficacy",
    )
    shadow_scanner_receipt = receipts.get("instruction_integrity_shadow_scanner")
    require(
        isinstance(shadow_scanner_receipt, dict),
        "review-matrix instruction-integrity shadow-scanner receipt is missing",
    )
    require_exact_keys(
        shadow_scanner_receipt,
        {
            "source_commit",
            "mode",
            "verdict_effect",
            "positive_disposition",
            "development_cases",
            "development_lane_counts",
            "development_injected_recall",
            "development_benign_false_positive_rate",
            "development_suite_sha256",
            "heldout_cases",
            "heldout_lane_counts",
            "heldout_injected_recall",
            "heldout_benign_false_positive_rate",
            "heldout_suite_sha256",
            "regression_tests",
            "test_ids_sha256",
            "independently_reproduced",
            "scope",
        },
        label="review-matrix instruction-integrity shadow-scanner receipt",
    )
    shadow_scope = shadow_scanner_receipt.get("scope")
    require(
        shadow_scanner_receipt
        == {
            "source_commit": SHADOW_SCANNER_SOURCE_COMMIT,
            "mode": "shadow",
            "verdict_effect": "none_shadow_only",
            "positive_disposition": "FLAG_FOR_HUMAN_REVIEW",
            "development_cases": 15,
            "development_lane_counts": {
                "clean": 4,
                "control": 5,
                "injected": 6,
            },
            "development_injected_recall": "1.0",
            "development_benign_false_positive_rate": "0.0",
            "development_suite_sha256": (
                "3a7dbb45b723fc9acd46c51dbc618db8a6c247d0f864f75efcd7ae56b3e13fb1"
            ),
            "heldout_cases": 12,
            "heldout_lane_counts": {
                "clean": 2,
                "control": 5,
                "injected": 5,
            },
            "heldout_injected_recall": "1.0",
            "heldout_benign_false_positive_rate": "0.0",
            "heldout_suite_sha256": (
                "7d5df4cf55254353f03cdc042372182777a19c1fa06fd6bfbf0f03311a8c1819"
            ),
            "regression_tests": REQUIRED_TEST_SUITES[
                "Instruction-integrity shadow scanner"
            ]["expected_tests"],
            "test_ids_sha256": REQUIRED_TEST_SUITES[
                "Instruction-integrity shadow scanner"
            ]["expected_test_ids_sha256"].lower(),
            "independently_reproduced": False,
            "scope": shadow_scope,
        }
        and isinstance(shadow_scope, str)
        and "SHADOW-ONLY" in shadow_scope
        and "FLAG_FOR_HUMAN_REVIEW" in shadow_scope
        and "no blocking" in shadow_scope
        and "do not establish real-world prompt-injection detection" in shadow_scope,
        "review-matrix shadow-scanner receipt drifted or promotes capability",
    )
    candidate_receipt = receipts.get("successor_dependency_container_candidate")
    require(isinstance(candidate_receipt, dict), "review-matrix successor candidate receipt is missing")
    require_exact_keys(
        candidate_receipt,
        {
            "receipt",
            "source_commit",
            "oci_image_index_digest",
            "platform_manifest_digest",
            "dependency_lock_count",
            "transformers_version",
            "sbom_full_image_package_scan_status",
            "sbom_scan_package_count",
            "sbom_scan_vulnerability_count",
            "sbom_scan_severity_counts",
            "direct_local_filesystem_scan_status",
            "gpu_real_forward_status",
            "independently_reproduced",
            "disposition",
            "live_execution_authorized",
            "external_evidence_class",
            "raw_external_evidence_retained",
            "repository_replayable",
        },
        label="review-matrix successor candidate receipt",
    )
    require(
        candidate_receipt
        == {
            "receipt": CANDIDATE_RECEIPT_PATH.relative_to(ROOT).as_posix(),
            "source_commit": CANDIDATE_SOURCE_COMMIT,
            "oci_image_index_digest": CANDIDATE_OCI_DIGESTS[
                "oci_image_index_digest"
            ],
            "platform_manifest_digest": CANDIDATE_OCI_DIGESTS[
                "platform_manifest_digest"
            ],
            "dependency_lock_count": 73,
            "transformers_version": "5.14.1",
            "sbom_full_image_package_scan_status": "COMPLETED_WITH_FINDINGS",
            "sbom_scan_package_count": 190,
            "sbom_scan_vulnerability_count": 7,
            "sbom_scan_severity_counts": {
                "critical": 0,
                "high": 0,
                "medium": 3,
                "low": 4,
            },
            "direct_local_filesystem_scan_status": "INCOMPLETE / PENDING",
            "gpu_real_forward_status": "NOT_STARTED",
            "independently_reproduced": False,
            "disposition": "OPEN_SECURITY",
            "live_execution_authorized": False,
            "external_evidence_class": "SELF_REPORTED_LOCAL_OBSERVATION",
            "raw_external_evidence_retained": False,
            "repository_replayable": False,
        },
        "review-matrix successor candidate identity or OPEN_SECURITY boundary drifted",
    )
    local_runner_receipt = receipts.get("local_test_runner")
    require(isinstance(local_runner_receipt, dict), "local runner receipt is missing")
    require_exact_keys(
        local_runner_receipt,
        {
            "receipt",
            "lock_scope",
            "python_version",
            "pytest_version",
            "interpreter_file_count",
            "runner_distribution_count",
            "runner_file_record_count",
            "startup_pth_file_count",
            "startup_pth_execution",
            "preimport_origin_check",
            "endpoint_module_inventory_limit",
            "same_process_outcome_receipts",
            "same_process_receipt_retention",
            "independently_attested",
            "disposition",
        },
        label="review-matrix local runner receipt",
    )
    require(
        local_runner_receipt
        == {
            "receipt": RUNNER_LOCK_PATH.relative_to(ROOT).as_posix(),
            "lock_scope": (
                "LOCAL_CONTENT_LOCK / SELF-OBSERVED / NOT HERMETIC / "
                "NOT INDEPENDENTLY ATTESTED"
            ),
            "python_version": "3.14.0",
            "pytest_version": "9.0.2",
            "interpreter_file_count": 3,
            "runner_distribution_count": 7,
            "runner_file_record_count": 508,
            "startup_pth_file_count": 3,
            "startup_pth_execution": "DISABLED BY -I -S",
            "preimport_origin_check": (
                "EXACT LOCKED FILE IDENTITY / LOCAL SELF-OBSERVATION"
            ),
            "endpoint_module_inventory_limit": (
                "SURVIVING SYS.MODULES ONLY / TRANSIENT AND EXACT LOADER BYTES OPEN"
            ),
            "same_process_outcome_receipts": True,
            "same_process_receipt_retention": (
                "EPHEMERAL LOCAL SAME-RUN VALIDATION / NOT RETAINED / NO TRUSTED "
                "TIME OR WORM"
            ),
            "independently_attested": False,
            "disposition": "OPEN_ENGINEERING",
        },
        "review-matrix local runner receipt drifted or promotes hermeticity",
    )
    raw_security_receipt = receipts.get("raw_build_and_security_evidence")
    require(isinstance(raw_security_receipt, dict), "raw security receipt is missing")
    require_exact_keys(
        raw_security_receipt,
        {
            "receipt",
            "retained_file_count",
            "original_buildkit_spdx_package_count",
            "direct_scout_spdx_package_count",
            "scout_version",
            "direct_scan_status",
            "finding_count",
            "severity_counts",
            "vendor_confirmed_vulnerable_or_deferred",
            "scanner_vendor_conflict",
            "historical_scout_1_24_raw_report_retained",
            "sarif_to_candidate_execution_binding",
            "vendor_source_payloads_retained",
            "raw_payloads_repository_replayable",
            "complete_tool_execution_replayable",
            "independently_reproduced",
            "independent_trust_root",
            "disposition",
        },
        label="review-matrix raw build/security receipt",
    )
    require(
        raw_security_receipt
        == {
            "receipt": RAW_BUILD_SECURITY_RECEIPT_PATH.relative_to(ROOT).as_posix(),
            "retained_file_count": 10,
            "original_buildkit_spdx_package_count": 199,
            "direct_scout_spdx_package_count": 233,
            "scout_version": "1.21.0",
            "direct_scan_status": "COMPLETED_WITH_FINDINGS",
            "finding_count": 7,
            "severity_counts": {
                "critical": 0,
                "high": 0,
                "medium": 3,
                "low": 4,
            },
            "vendor_confirmed_vulnerable_or_deferred": 6,
            "scanner_vendor_conflict": 1,
            "historical_scout_1_24_raw_report_retained": False,
            "sarif_to_candidate_execution_binding": (
                "OPEN / NOT EMBEDDED / INVOCATION NOT RETAINED"
            ),
            "vendor_source_payloads_retained": False,
            "raw_payloads_repository_replayable": True,
            "complete_tool_execution_replayable": False,
            "independently_reproduced": False,
            "independent_trust_root": False,
            "disposition": "OPEN_SECURITY",
        },
        "review-matrix raw evidence receipt drifted or promotes security",
    )
    historical_receipt = receipts.get("historical_recovery")
    require(isinstance(historical_receipt, dict), "historical receipt is missing")
    require_exact_keys(
        historical_receipt,
        {
            "exact_file_count",
            "total_bytes",
            "inventory_sha256",
            "independent_verifier_passed",
            "model_free_passed",
            "model_free_failed",
            "restored_v1_worker_failed",
        },
        label="review matrix historical receipt",
    )
    require(
        type(historical_receipt.get("exact_file_count")) is int
        and historical_receipt["exact_file_count"] == 537
        and type(historical_receipt.get("total_bytes")) is int
        and historical_receipt["total_bytes"] == 95_945_579
        and historical_receipt.get("inventory_sha256")
        == "361f8867a1b8983c383b4f4fe6d8d485e5dbbc80ee4f75e4b5d08b4e5f144f5f"
        and all(
            type(historical_receipt.get(field)) is int
            and historical_receipt[field] == expected
            for field, expected in {
                "independent_verifier_passed": 4,
                "model_free_passed": 43,
                "model_free_failed": 4,
                "restored_v1_worker_failed": 31,
            }.items()
        ),
        "review-matrix historical receipt drifted or erased negative evidence",
    )
    return len(criteria), len(REQUIRED_OPEN_BOUNDARY_IDS)


def verify_adversarial_review() -> None:
    require(ADVERSARIAL_REVIEW_PATH.is_file(), "Gate 5 adversarial review is missing")
    text = read_stable_text(ADVERSARIAL_REVIEW_PATH)
    for marker in (
        "Document status: `DRAFT / OPEN / NOT FROZEN`",
        "Decision status: `OPEN / KEEP_OPEN`",
        "Engineering status: `RING 4 / BOUNDED SOFTWARE CANDIDATE TESTED`",
        "Experimental execution status: `NOT_STARTED`",
        "License / disclosure / canon status: `NOT LICENSED / HELD / NOT FROZEN`",
        "Live / product route status: `unavailable / not authorized`",
        "KEEP GATE 5 OPEN",
        "NOT LICENSED",
        "HELD",
        "caller-declared UTC timestamps",
        "non-caller-selected trust root",
        "WORM",
        "one-use",
        "selective-reporting",
        "hermetic",
        "semantic",
        "CVE-2026-4372",
        "No authorized or admitted live exact-revision experiment",
        "GPU, autocast/mixed-precision, compiled-module",
        "independent numerical",
        "replication",
        "peer review",
        "Product readiness",
        "Public disclosure",
        "RNG-only output drift",
        "NaN and positive/negative infinity",
        "hidden mutable model state",
        "stream abort after every attempted intervention",
        "public-schema forgery of the retired causal-success state",
        "32/32 focused",
        "391/391 complete worker",
        "155 passed tests plus 106 subtests",
        "CF033F2E7F519AAD6738D596A694728FD4173CFA12DD8A8FE094823215D4CF8A",
        "35 tests plus 45 subtests",
        "73C14349373376F49C380A84E8629C82167B5BF0F73415A45F197D99DE97F807",
        "0781bab8",
        "confirmed 290/290 receipt",
        "12602041756f20d1afd402fa56968660839e5eb1098438ba84c69bff8de7050b",
        "94566203b3e0ff79b3224c1c5a073698ca99d3c08bc1119a9082e42af4b178bd",
        "fd8367b867cb6589cc50424d7a1cecabc56bf85331bb4fd87b844e7fd3004580",
        "78/78",
        "603debf7df9ac7b5a69543c3736f4cd38692d3330690a7559a6f9de6f0e2af77",
        "17/17",
        "fa6c985cd6caa734034e006bb4baf6be9d02269d7312bee7355e9c3833759c51",
        "38/38",
        "d3eaf533fedb5b03168200aa399ac53a6e2a6f22874ebabeaecefb227400778d",
        "134/134",
        "67f7507579749e11e27714e8513f6909e26a503a8dd18112cc402207d9735940",
        "98/98",
        "65352b8b59cb654e449ba4a1ce8459d7109cc5b21e33f64aeab6e2ea6eeb3c19",
        "supersede the stale 130/90 receipts",
        "27/27",
        "dc0c0ed22e0f158f014277b9d3cd26ad21d6a8fcdfbe1e76a67d09406975c952",
        "Both reservation entry",
        "points now enter that repair/full-verification loop",
        "retained tenant and event kind",
        "COMPLETED_WITH_FINDINGS",
        "critical, 0 high, 3 medium, and 4 low findings",
        "SARIF does not embed the candidate identity",
        "source-commit Git blobs",
        "6f66eb2b3c37d87aaddfb091a10bdd4737e6e430",
        "508 exact file records",
        "surviving `sys.modules`",
        "lock-byte replacement before parsing",
        "OPEN_SECURITY",
        "including the final ID",
        "Earlier hashes produced by culture-aware sorting",
        "omitting the final LF",
        "extra manifest records",
        "contradictory extra fields",
        "JSON floating-point values",
        "unbound ancestor `conftest.py`",
        "postflight rehash",
        "Gate 5 manifest changed during verification",
        "HISTORICALLY_INCONSISTENT",
        "ZeroNetworkGuard",
        "CompatibleZeroNetworkGuard",
        "43 passed, 4 failed",
        "31 failed",
    ):
        require(marker in text, f"adversarial review omits required marker {marker!r}")


def verify_no_status_promotion_text(
    manifest_artifacts: dict[str, dict[str, Any]],
) -> None:
    """Reject explicit contradictory status conclusions in bound text carriers."""
    required_headers = {
        "docs/working/project_coherence/gate5/README.md": (
            "# Project Coherence Gate 5\n\n"
            "Document status: `DRAFT / OPEN / NOT FROZEN`\n\n"
            "Decision status: `OPEN / KEEP_OPEN`\n\n"
            "Engineering status: `RING 4 / BOUNDED SOFTWARE CANDIDATE TESTED`\n\n"
            "Experimental execution status: `NOT_STARTED`\n\n"
            "License / disclosure / canon status: `NOT LICENSED / HELD / NOT FROZEN`\n\n"
            "Live / product route status: `unavailable / not authorized`"
        ),
        "docs/working/project_coherence/gate5/"
        "HARNESS_V2_PREREGISTRATION_AND_EVIDENCE_PACKET_V2_SPEC_v0.1.md": (
            "# CAS Harness v2 preregistration and Evidence Packet v2 control kernel\n\n"
            "Document status: `DRAFT / OPEN / NOT FROZEN`\n\n"
            "Decision status: `OPEN / KEEP_OPEN`\n\n"
            "Engineering status: `RING 4 / BOUNDED SOFTWARE CANDIDATE TESTED`\n\n"
            "Experimental execution status: `NOT_STARTED`\n\n"
            "License / disclosure / canon status: `NOT LICENSED / HELD / NOT FROZEN`\n\n"
            "Live / product route status: `unavailable / not authorized`"
        ),
        "docs/working/project_coherence/gate5/GATE5_ADVERSARIAL_REVIEW_v0.1.md": (
            "# Gate 5 adversarial review v0.1\n\n"
            "Document status: `DRAFT / OPEN / NOT FROZEN`\n\n"
            "Decision status: `OPEN / KEEP_OPEN`\n\n"
            "Engineering status: `RING 4 / BOUNDED SOFTWARE CANDIDATE TESTED`\n\n"
            "Experimental execution status: `NOT_STARTED`\n\n"
            "License / disclosure / canon status: `NOT LICENSED / HELD / NOT FROZEN`\n\n"
            "Live / product route status: `unavailable / not authorized`"
        ),
    }
    for raw_path, header in required_headers.items():
        text = read_stable_text(ROOT / raw_path)
        require(text.startswith(header), f"{raw_path}: governance header drifted")

    forbidden_patterns = (
        r"\bgate\s*5\s+(?:is\s+)?closed\b",
        r"\bfinal\s+status\s*:\s*(?:gate\s*5\s+)?closed\b",
        r"\bgate5_status\s*[:=]\s*[`\"']?closed\b",
        r"\bgate_decision\s*[:=]\s*[`\"']?(?:close|accept)\b",
        r"\blicense_status\s*[:=]\s*[`\"']?licensed\b",
        r"\bpublic_disclosure_authorized\s*[:=]\s*true\b",
        r"\blive_execution_authorized\s*[:=]\s*true\b",
        r"\bdecision\s*:\s*(?:close|accept)\b",
    )
    negative_context_exemptions = {
        "docs/working/project_coherence/gate5/joined_model_smoke/preregistration.json",
        "docs/working/project_coherence/gate5/joined_model_smoke_v0.2/preregistration.json",
    }
    exact_forbidden_wording = [
        "prompt-injection detection validated",
        "steering efficacy validated",
        "Gate 5 closed",
        "production ready",
        "Evidence Packet created",
    ]
    for raw_path in sorted(manifest_artifacts):
        if not raw_path.startswith("docs/working/project_coherence/gate5/"):
            continue
        if not raw_path.endswith((".md", ".json")):
            continue
        path = ROOT / Path(*PurePosixPath(raw_path).parts)
        text = read_stable_text(path)
        if raw_path in negative_context_exemptions:
            payload = load_json(path)
            require(isinstance(payload, dict), f"{raw_path}: preregistration is malformed")
            permitted_wording = payload.get("permitted_wording")
            require(
                isinstance(permitted_wording, dict)
                and set(permitted_wording) == {"allowed", "claim_ceiling", "forbidden"}
                and permitted_wording.get("claim_ceiling") == "DIAGNOSTIC_ONLY"
                and permitted_wording.get("forbidden") == exact_forbidden_wording,
                f"{raw_path}: negative wording context drifted",
            )
            sanitized_payload = dict(payload)
            sanitized_wording = dict(permitted_wording)
            sanitized_wording["forbidden"] = []
            sanitized_payload["permitted_wording"] = sanitized_wording
            text = json.dumps(sanitized_payload, ensure_ascii=False, sort_keys=True)
        for pattern in forbidden_patterns:
            require(
                re.search(pattern, text, flags=re.IGNORECASE) is None,
                f"{raw_path}: contains an explicit contradictory status promotion",
            )


def verify_model_and_security_bindings() -> None:
    require(
        sha256_file(MODEL_DEPENDENCY_BINDING_PATH)
        == HISTORICAL_MODEL_DEPENDENCY_BINDING_SHA256,
        "historical v0.1 model/dependency adverse binding bytes changed",
    )
    binding = load_json(MODEL_DEPENDENCY_BINDING_PATH)
    require(isinstance(binding, dict), "model/dependency binding root is not an object")
    require_exact_keys(
        binding,
        {
            "schema_version",
            "document_status",
            "gate5_status",
            "gate_decision",
            "admission_ring",
            "license_status",
            "disclosure_status",
            "public_disclosure_authorized",
            "experimental_execution_status",
            "model_binding",
            "container_binding",
            "dependency_security_hold",
            "claim_boundary",
        },
        label="model/dependency binding",
    )
    require(
        binding.get("schema_version")
        == "project_coherence.gate5_model_and_dependency_binding.v0.1",
        "unexpected model/dependency binding schema",
    )
    require(
        binding.get("document_status") == "DRAFT / OPEN / NOT FROZEN",
        "model/dependency binding is not draft/open/unfrozen",
    )
    require(binding.get("gate5_status") == "OPEN", "model binding closes Gate 5")
    require(binding.get("gate_decision") == "KEEP_OPEN", "model binding admits Gate 5")
    require(
        type(binding.get("admission_ring")) is int and binding["admission_ring"] == 4,
        "model binding escaped Ring 4 or used a non-integer ring",
    )
    require(binding.get("license_status") == "NOT LICENSED", "model binding licenses claims")
    require(binding.get("disclosure_status") == "HELD", "model binding is not HELD")
    require(
        binding.get("public_disclosure_authorized") is False,
        "model binding authorizes public disclosure",
    )
    require(
        binding.get("experimental_execution_status") == "NOT_STARTED",
        "model binding promotes experimental execution",
    )
    model_record = binding.get("model_binding")
    require(isinstance(model_record, dict), "model identity record is missing")
    require_exact_keys(
        model_record,
        {
            "repository_id",
            "revision",
            "weights_filename",
            "weights_bytes",
            "weights_sha256",
            "loader_policy",
            "local_cache_byte_verification",
            "in_memory_tensor_identity",
            "artifact_signature_trust_root",
            "execution_receipt",
        },
        label="model identity record",
    )
    require(model_record.get("repository_id") == MODEL_BINDING["model_id"], "model ID drifted")
    require(model_record.get("revision") == MODEL_BINDING["revision"], "model revision drifted")
    require(
        model_record.get("weights_filename") == MODEL_BINDING["weights_filename"],
        "weights filename drifted",
    )
    require(
        type(model_record.get("weights_bytes")) is int
        and model_record["weights_bytes"] == MODEL_BINDING["weights_bytes"],
        "weights bytes drifted or used a non-integer count",
    )
    require(
        model_record.get("weights_sha256") == MODEL_BINDING["weights_sha256"].upper(),
        "weights SHA-256 drifted",
    )
    require(
        model_record.get("loader_policy") == "PINNED_REVISION_AND_WEIGHTS_SHA256",
        "model loader policy drifted",
    )
    require(
        model_record.get("local_cache_byte_verification")
        == "MATCHED_WITHOUT_MODEL_EXECUTION",
        "local weights-file identity receipt drifted",
    )
    require(
        model_record.get("in_memory_tensor_identity") == "NOT_ESTABLISHED"
        and model_record.get("artifact_signature_trust_root") == "NOT_ESTABLISHED"
        and model_record.get("execution_receipt") == "NOT_CREATED",
        "model binding overclaims tensor identity, trust, or execution",
    )
    container = binding.get("container_binding")
    require(isinstance(container, dict), "container binding is missing")
    require_exact_keys(
        container,
        {
            "declared_base_image",
            "base_image_digest",
            "built_container_digest",
            "container_digest_bound",
            "hermeticity_status",
        },
        label="container binding",
    )
    require(
        container.get("declared_base_image")
        == "pytorch/pytorch:2.4.0-cuda12.1-cudnn9-runtime",
        "declared base image drifted",
    )
    require(
        container.get("base_image_digest") is None
        and container.get("built_container_digest") is None
        and container.get("container_digest_bound") is False
        and container.get("hermeticity_status") == "NOT_ESTABLISHED",
        "container blocker was removed or overclaimed",
    )
    security_record = binding.get("dependency_security_hold")
    require(isinstance(security_record, dict), "dependency security record is missing")
    require_exact_keys(
        security_record,
        {
            "status",
            "reason_id",
            "observed_at_date",
            "affected_package",
            "repository_pin",
            "affected_requirement",
            "advisory_id",
            "github_advisory_id",
            "affected_range",
            "minimum_fixed_version_reported",
            "latest_pypi_release_observed",
            "advisory_source",
            "advisory_json_source",
            "fixed_release_source",
            "latest_release_source",
            "patched_environment_revalidated",
            "live_execution_authorized",
            "hold_reason",
            "hold_release_requirements",
        },
        label="dependency security record",
    )
    require(security_record.get("status") == SECURITY_HOLD["status"], "security hold was removed")
    require(
        security_record.get("reason_id") == SECURITY_HOLD["reason_id"],
        "security reason ID drifted",
    )
    require(security_record.get("affected_package") == "transformers", "affected package drifted")
    require(security_record.get("repository_pin") == "4.46.3", "affected package pin drifted")
    require(
        security_record.get("affected_requirement")
        == SECURITY_HOLD["affected_requirement"],
        "affected requirement drifted",
    )
    require(
        security_record.get("advisory_id") == SECURITY_HOLD["advisory_id"]
        and security_record.get("github_advisory_id") == SECURITY_HOLD["ghsa_id"],
        "security advisory identity drifted",
    )
    require(
        security_record.get("minimum_fixed_version_reported")
        == SECURITY_HOLD["minimum_fixed_version"],
        "reported fixed dependency version drifted",
    )
    require(
        security_record.get("observed_at_date") == "2026-08-04"
        and security_record.get("affected_range") == "<5.3.0"
        and security_record.get("latest_pypi_release_observed") == "5.14.1"
        and security_record.get("advisory_source")
        == "https://osv.dev/vulnerability/CVE-2026-4372"
        and security_record.get("advisory_json_source")
        == "https://api.osv.dev/v1/vulns/CVE-2026-4372"
        and security_record.get("fixed_release_source")
        == "https://pypi.org/project/transformers/5.3.0/"
        and security_record.get("latest_release_source")
        == "https://pypi.org/project/transformers/",
        "dependency-security observation identity or source URLs drifted",
    )
    require(
        isinstance(security_record.get("hold_reason"), str)
        and "No live, hosted, or claim-bearing Harness v2 execution is admissible"
        in security_record["hold_reason"]
        and isinstance(security_record.get("hold_release_requirements"), list)
        and len(security_record["hold_release_requirements"]) == 5
        and all(
            isinstance(item, str) and item.strip()
            for item in security_record["hold_release_requirements"]
        ),
        "dependency-security hold rationale or release obligations drifted",
    )
    require(
        security_record.get("patched_environment_revalidated") is False
        and security_record.get("live_execution_authorized") is False,
        "security binding falsely releases the patched-environment/execution hold",
    )
    claim_boundary = binding.get("claim_boundary")
    require(isinstance(claim_boundary, dict), "model/dependency claim boundary is missing")
    require_exact_keys(
        claim_boundary,
        {
            "identity_evidence_effect",
            "scientific_effect",
            "canon_effect",
            "product_claim_effect",
            "license_effect",
            "disclosure_effect",
        },
        label="model/dependency claim boundary",
    )
    require(
        claim_boundary
        == {
            "identity_evidence_effect": "STRUCTURAL_ONLY",
            "scientific_effect": "NONE",
            "canon_effect": "NONE",
            "product_claim_effect": "NONE",
            "license_effect": "NONE",
            "disclosure_effect": "NONE",
        },
        "model/dependency binding claims an unauthorized effect",
    )

    model_loader = read_stable_text(
        WORKER_ROOT / "app" / "runtime" / "model_loader.py"
    )
    dockerfile = read_stable_text(WORKER_ROOT / "Dockerfile")
    for value in (
        MODEL_BINDING["revision"],
        MODEL_BINDING["weights_filename"],
        MODEL_BINDING["weights_sha256"],
        "374_998_696",
    ):
        require(value in model_loader, f"model loader omits exact identity value {value!r}")
    require(
        f"PYTHIA_160M_REVISION={MODEL_BINDING['revision']}" in dockerfile,
        "Dockerfile Pythia revision differs from the exact model binding",
    )


def _require_oci_digest(value: Any, *, label: str) -> None:
    require(
        isinstance(value, str) and OCI_SHA256_RE.fullmatch(value) is not None,
        f"{label}: expected a lowercase sha256 OCI digest",
    )


def _candidate_source_blob_bytes(raw_path: str, *, label: str) -> bytes:
    """Read an exact regular-file blob from the time-indexed candidate commit."""
    canonical_repo_path(raw_path, label=label)
    entry = subprocess.run(
        ["git", "ls-tree", CANDIDATE_SOURCE_COMMIT, "--", raw_path],
        cwd=ROOT,
        env=_subprocess_environment(),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    require(
        entry.returncode == 0 and entry.stdout.strip(),
        f"{label}: source-commit tree entry is unavailable",
    )
    metadata, separator, listed_path = entry.stdout.strip().partition("\t")
    parts = metadata.split()
    require(
        separator == "\t"
        and listed_path == raw_path
        and len(parts) == 3
        and parts[0] in {"100644", "100755"}
        and parts[1] == "blob"
        and re.fullmatch(r"[a-f0-9]{40}", parts[2]) is not None,
        f"{label}: source-commit entry is not an exact regular blob",
    )
    completed = subprocess.run(
        ["git", "cat-file", "blob", parts[2]],
        cwd=ROOT,
        env=_subprocess_environment(),
        capture_output=True,
        check=False,
    )
    require(completed.returncode == 0, f"{label}: source blob is unavailable")
    return completed.stdout


def _require_candidate_file_record(
    key: str, record: Any, *, include_package_fields: bool = False
) -> None:
    expected = CANDIDATE_BUILD_INPUTS[key]
    require(isinstance(record, dict), f"candidate {key} record is missing")
    require_exact_keys(record, set(expected), label=f"candidate {key} record")
    require(record == expected, f"candidate {key} identity drifted")
    raw_path = canonical_repo_path(record.get("path"), label=f"candidate {key}")
    data = _candidate_source_blob_bytes(raw_path, label=f"candidate {key}")
    require(
        isinstance(record.get("sha256"), str)
        and SHA256_UPPER_RE.fullmatch(record["sha256"]) is not None
        and sha256_bytes(data) == record["sha256"],
        f"candidate {key} file hash drifted",
    )
    require(
        type(record.get("bytes")) is int and len(data) == record["bytes"],
        f"candidate {key} byte count drifted",
    )
    try:
        text = data.decode("utf-8")
    except UnicodeError as exc:
        raise VerificationError(f"candidate {key} is not UTF-8 text: {exc}") from exc
    require(
        type(record.get("line_count")) is int
        and len(text.splitlines()) == record["line_count"],
        f"candidate {key} line count drifted",
    )
    if include_package_fields:
        package_heads = [
            line
            for line in text.splitlines()
            if line
            and not line.startswith((" ", "\t", "#"))
        ]
        require(
            type(record.get("package_count")) is int
            and len(package_heads) == record["package_count"],
            "candidate requirements lock package count drifted",
        )


def _candidate_application_tree_record() -> dict[str, Any]:
    app_root = f"{WORKER_ROOT_REL}/app"
    listing = subprocess.run(
        [
            "git",
            "ls-tree",
            "-r",
            "-z",
            "--full-tree",
            CANDIDATE_SOURCE_COMMIT,
            "--",
            app_root,
        ],
        cwd=ROOT,
        env=_subprocess_environment(),
        capture_output=True,
        check=False,
    )
    require(listing.returncode == 0, "candidate application source tree is unavailable")
    files: list[str] = []
    for raw_entry in listing.stdout.split(b"\0"):
        if not raw_entry:
            continue
        metadata, separator, raw_path = raw_entry.partition(b"\t")
        parts = metadata.decode("ascii", errors="strict").split()
        path = raw_path.decode("utf-8", errors="strict")
        require(
            separator == b"\t"
            and len(parts) == 3
            and parts[0] in {"100644", "100755"}
            and parts[1] == "blob"
            and re.fullmatch(r"[a-f0-9]{40}", parts[2]) is not None
            and path.startswith(app_root + "/"),
            "candidate application source tree contains a non-regular entry",
        )
        require("/__pycache__/" not in path, "candidate source tree contains bytecode cache")
        files.append(path)
    files.sort(key=lambda path: PurePosixPath(path).relative_to(WORKER_ROOT_REL).as_posix())
    require(files, "candidate application source tree is empty")
    payload = bytearray()
    total_bytes = 0
    for raw_path in files:
        data = _candidate_source_blob_bytes(raw_path, label="candidate application file")
        relative = PurePosixPath(raw_path).relative_to(WORKER_ROOT_REL).as_posix()
        total_bytes += len(data)
        payload.extend(relative.encode("utf-8"))
        payload.extend(b"\0")
        payload.extend(str(len(data)).encode("ascii"))
        payload.extend(b"\0")
        payload.extend(hashlib.sha256(data).hexdigest().upper().encode("ascii"))
        payload.extend(b"\n")
    return {
        "path": f"{WORKER_ROOT_REL}/app",
        "file_count": len(files),
        "bytes": total_bytes,
        "tree_sha256": hashlib.sha256(payload).hexdigest().upper(),
        "serialization": (
            "ORDINAL-SORTED BUILD-CONTEXT-RELATIVE POSIX PATH + NUL + DECIMAL "
            "BYTE COUNT + NUL + UPPERCASE FILE SHA256 + LF"
        ),
        "source_commit": CANDIDATE_SOURCE_COMMIT,
        "source_commit_tree_matched": True,
    }


def _verify_candidate_source_commit_tree() -> None:
    revision = subprocess.run(
        ["git", "rev-parse", "--verify", f"{CANDIDATE_SOURCE_COMMIT}^{{commit}}"],
        cwd=ROOT,
        env=_subprocess_environment(),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    require(
        revision.returncode == 0
        and revision.stdout.strip() == CANDIDATE_SOURCE_COMMIT,
        "candidate source commit is unavailable or not exact",
    )
    # The OCI receipt is deliberately time-indexed. Current worker bytes may
    # evolve and are bound separately by the Gate 5 manifest; the receipt must
    # continue to verify against its exact source commit rather than silently
    # being reinterpreted as a build of the current tree.


def verify_dependency_and_container_candidate_receipt() -> dict[str, Any]:
    receipt = load_json(CANDIDATE_RECEIPT_PATH)
    require(isinstance(receipt, dict), "candidate receipt root is not an object")
    require_exact_keys(
        receipt,
        {
            "schema_version",
            "document_status",
            "gate5_status",
            "gate_decision",
            "admission_ring",
            "license_status",
            "disclosure_status",
            "public_disclosure_authorized",
            "experimental_execution_status",
            "engineering_preflight_execution_status",
            "security_disposition",
            "live_execution_authorized",
            "candidate_accepted",
            "candidate_identity",
            "build_control_inputs",
            "attestations",
            "external_evidence_retention",
            "dependency_runtime_identity",
            "model_binding",
            "build_and_preflight",
            "runtime_fail_closed_probes",
            "test_receipts",
            "security_audits",
            "unresolved_boundaries",
            "historical_adverse_evidence",
            "claim_boundary",
        },
        label="Gate 5 dependency/container candidate receipt",
    )
    require(
        receipt.get("schema_version")
        == "project_coherence.gate5_dependency_and_container_candidate_receipt.v0.2",
        "unexpected candidate receipt schema",
    )
    for field, expected in {
        "document_status": "DRAFT / OPEN / NOT FROZEN",
        "gate5_status": "OPEN",
        "gate_decision": "KEEP_OPEN",
        "license_status": "NOT LICENSED",
        "disclosure_status": "HELD",
        "experimental_execution_status": "NOT_STARTED",
        "engineering_preflight_execution_status": "COMPLETED_CPU_ONLY_NONEXPERIMENTAL",
        "security_disposition": "OPEN_SECURITY",
    }.items():
        require(receipt.get(field) == expected, f"candidate receipt {field} drifted")
    require(
        type(receipt.get("admission_ring")) is int
        and receipt["admission_ring"] == 4,
        "candidate receipt escaped Ring 4 or used a non-integer ring",
    )
    require(
        receipt.get("public_disclosure_authorized") is False
        and receipt.get("live_execution_authorized") is False
        and receipt.get("candidate_accepted") is False,
        "candidate receipt promotes disclosure, live execution, or acceptance",
    )

    identity = receipt.get("candidate_identity")
    require(isinstance(identity, dict), "candidate OCI identity is missing")
    require_exact_keys(
        identity,
        {
            "source_commit",
            "build_ref",
            "image_tag",
            "platform",
            "oci_image_index_digest",
            "platform_manifest_digest",
            "image_config_digest",
            "image_size_bytes",
            "source_commit_label_matched",
        },
        label="candidate OCI identity",
    )
    require(
        identity.get("source_commit") == CANDIDATE_SOURCE_COMMIT
        and SHA256_LOWER_RE.fullmatch(identity["source_commit"] + "0" * 24) is not None,
        "candidate source commit drifted or is malformed",
    )
    require(identity.get("build_ref") == CANDIDATE_BUILD_REF, "candidate build ref drifted")
    require(
        identity.get("image_tag") == "atlas-live-trace-worker:gate5-candidate-v0.2"
        and identity.get("platform") == "linux/amd64",
        "candidate tag or platform drifted",
    )
    for field, expected in CANDIDATE_OCI_DIGESTS.items():
        _require_oci_digest(identity.get(field), label=f"candidate {field}")
        require(identity[field] == expected, f"candidate {field} drifted")
    require(
        type(identity.get("image_size_bytes")) is int
        and identity["image_size_bytes"] == 4_396_739_765
        and identity.get("source_commit_label_matched") is True,
        "candidate image size or source-label receipt drifted",
    )

    inputs = receipt.get("build_control_inputs")
    require(isinstance(inputs, dict), "candidate build controls are missing")
    require_exact_keys(
        inputs,
        {
            "dockerfile",
            "dockerignore",
            "requirements_lock",
            "requirements_input",
            "application_tree",
            "base_images",
        },
        label="candidate build controls",
    )
    _require_candidate_file_record("dockerfile", inputs.get("dockerfile"))
    _require_candidate_file_record("dockerignore", inputs.get("dockerignore"))
    _require_candidate_file_record(
        "requirements_lock",
        inputs.get("requirements_lock"),
        include_package_fields=True,
    )
    _require_candidate_file_record("requirements_input", inputs.get("requirements_input"))
    application_tree = inputs.get("application_tree")
    require(isinstance(application_tree, dict), "candidate application tree is missing")
    require_exact_keys(
        application_tree,
        set(CANDIDATE_BUILD_INPUTS["application_tree"]),
        label="candidate application tree",
    )
    require(
        application_tree == CANDIDATE_BUILD_INPUTS["application_tree"]
        and application_tree == _candidate_application_tree_record(),
        "candidate application tree differs from the OCI-bound build context",
    )
    _verify_candidate_source_commit_tree()
    bases = inputs.get("base_images")
    require(isinstance(bases, dict), "candidate base-image binding is missing")
    require_exact_keys(bases, {"ubuntu", "python"}, label="candidate base images")
    require(
        bases
        == {
            "ubuntu": {
                "reference": "ubuntu:24.04",
                "digest": "sha256:019e8eb29a85e74d64925745884f2ec79aa27e3feab36353d24656f4d6b89467",
                "snapshot": "20260805T000000Z",
            },
            "python": {
                "reference": "python:3.12.13-slim-bookworm",
                "digest": "sha256:6e13e65c55e33adf203d77ee371cf8bf5d81bd4902ef07565721f46bf44917af",
            },
        },
        "candidate base-image identities drifted",
    )
    try:
        dockerfile = _candidate_source_blob_bytes(
            f"{WORKER_ROOT_REL}/Dockerfile",
            label="candidate Dockerfile",
        ).decode("utf-8")
    except UnicodeError as exc:
        raise VerificationError(f"candidate Dockerfile is not UTF-8: {exc}") from exc
    for base in bases.values():
        _require_oci_digest(base.get("digest"), label="candidate base image")
        require(
            base["reference"] in dockerfile and base["digest"] in dockerfile,
            "candidate base image is not bound by the Dockerfile",
        )
    require("20260805T000000Z" in dockerfile, "Ubuntu snapshot binding drifted")

    attestations = receipt.get("attestations")
    require(isinstance(attestations, dict), "candidate attestations are missing")
    require_exact_keys(
        attestations,
        {
            "attestation_manifest_digest",
            "attestation_config_digest",
            "sbom",
            "slsa_provenance",
            "trust_boundary",
        },
        label="candidate attestations",
    )
    expected_attestation_digests = {
        "attestation_manifest_digest": "sha256:b1db5924ab8ce96927f0164c4626cd5eb0c86cbd3fb35c0387b622dd7ae390d1",
        "attestation_config_digest": "sha256:4592edd32ecc05f0ce5fca43216dea1393293b07245db9582989ed3cb77f5ad7",
    }
    for field, expected in expected_attestation_digests.items():
        _require_oci_digest(attestations.get(field), label=field)
        require(attestations[field] == expected, f"candidate {field} drifted")
    sbom = attestations.get("sbom")
    require(isinstance(sbom, dict), "candidate SBOM identity is missing")
    require_exact_keys(sbom, {"status", "format", "digest", "size_bytes"}, label="candidate SBOM")
    _require_oci_digest(sbom.get("digest"), label="candidate SBOM")
    require(
        sbom.get("status") == "OBSERVED_LOCAL / RAW_BYTES_NOT_RETAINED"
        and sbom.get("format") == "SPDX"
        and sbom.get("digest")
        == "sha256:8d039b378dfc422bae2d7479a06bfa2ac9c94a9a19fe8aa115362a28ec41955e"
        and type(sbom.get("size_bytes")) is int
        and sbom["size_bytes"] == 2_957_946,
        "candidate SBOM receipt drifted",
    )
    provenance = attestations.get("slsa_provenance")
    require(isinstance(provenance, dict), "candidate provenance identity is missing")
    require_exact_keys(
        provenance,
        {
            "status",
            "predicate_type",
            "digest",
            "size_bytes",
            "attachment_digest",
            "independently_trusted",
        },
        label="candidate provenance",
    )
    _require_oci_digest(provenance.get("digest"), label="candidate provenance")
    _require_oci_digest(provenance.get("attachment_digest"), label="provenance attachment")
    require(
        provenance.get("status") == "OBSERVED_LOCAL / RAW_BYTES_NOT_RETAINED"
        and provenance.get("predicate_type") == "https://slsa.dev/provenance/v1"
        and provenance.get("digest")
        == "sha256:f8e3677325d096191bb7ec1d075a34addf4e4733a48d3ae442f63c1bb74a6c6f"
        and type(provenance.get("size_bytes")) is int
        and provenance["size_bytes"] == 45_532
        and provenance.get("attachment_digest")
        == "sha256:36bc87d2b88089eda3958edb5dbcf4cbdd5b5c01e16725e1dbeb49171c23b971"
        and provenance.get("independently_trusted") is False,
        "candidate provenance receipt drifted or claims independent trust",
    )
    require(
        attestations.get("trust_boundary")
        == "SELF-REPORTED LOCAL BUILDKIT OBSERVATION / RAW ATTESTATIONS NOT RETAINED / NO INDEPENDENT TRUST ROOT",
        "candidate attestation trust boundary drifted",
    )

    retention = receipt.get("external_evidence_retention")
    require(
        retention
        == {
            "evidence_class": "SELF_REPORTED_LOCAL_OBSERVATION",
            "raw_build_history_retained": False,
            "raw_sbom_retained": False,
            "raw_slsa_provenance_retained": False,
            "raw_scanner_report_retained": False,
            "repository_replayable": False,
            "remaining_obligation": (
                "Retain and hash-bind raw build inspection, SPDX, SLSA provenance, "
                "and scanner output before treating external-tool observations as "
                "repository-replayable evidence."
            ),
        },
        "candidate external-tool evidence is missing or falsely replayable",
    )

    runtime = receipt.get("dependency_runtime_identity")
    require(isinstance(runtime, dict), "candidate runtime identity is missing")
    require_exact_keys(
        runtime,
        {
            "python_version",
            "transformers_version",
            "torch_version",
            "installed_distribution_count",
            "pip_present",
            "ensurepip_present",
            "runtime_uid",
            "runtime_gid",
        },
        label="candidate runtime identity",
    )
    require(
        runtime.get("python_version") == "3.12.13"
        and runtime.get("transformers_version") == "5.14.1"
        and runtime.get("torch_version") == "2.13.0+cu126"
        and type(runtime.get("installed_distribution_count")) is int
        and runtime["installed_distribution_count"] == 73
        and runtime.get("pip_present") is False
        and runtime.get("ensurepip_present") is False
        and type(runtime.get("runtime_uid")) is int
        and runtime["runtime_uid"] == 10_001
        and type(runtime.get("runtime_gid")) is int
        and runtime["runtime_gid"] == 10_001,
        "candidate dependency/runtime identity drifted",
    )
    requirements = read_stable_text(WORKER_ROOT / "requirements.txt")
    require(
        "transformers==5.14.1 \\" in requirements
        and "torch-2.13.0%2Bcu126-cp312-cp312-manylinux_2_28_x86_64.whl"
        in requirements,
        "candidate Transformers or Torch requirement drifted",
    )

    model = receipt.get("model_binding")
    require(isinstance(model, dict), "candidate model binding is missing")
    require_exact_keys(
        model,
        {
            "repository_id",
            "revision",
            "artifact_policy",
            "artifacts",
            "offline_cpu_load_and_canary",
            "gpu_real_forward",
            "scientific_result_created",
        },
        label="candidate model binding",
    )
    expected_model_artifacts = [
        ("config.json", "76EB275107220E450D31258F792A2EFCBEE109D8B62AE0088260057DEC06362F", 569),
        ("model.safetensors", MODEL_BINDING["weights_sha256"].upper(), MODEL_BINDING["weights_bytes"]),
        ("special_tokens_map.json", "6F50AB5A5A509A1C309D6171F339B196A900DC9C99AD0408FF23BB615FDAE7AD", 99),
        ("tokenizer.json", "C24618A1B3E6A38167BEFF1C72CFFD126C3A66254347304B50547D12C5F25624", 2_113_710),
        ("tokenizer_config.json", "70E38394E494931C6F773BA41E19460DD4436526B852207367F04341B4066D3F", 396),
    ]
    artifacts = model.get("artifacts")
    require(isinstance(artifacts, list), "candidate model artifact list is missing")
    require(
        len(artifacts) == len(expected_model_artifacts),
        "candidate model artifact count drifted",
    )
    for index, (filename, digest, byte_count) in enumerate(expected_model_artifacts):
        artifact = artifacts[index]
        require(isinstance(artifact, dict), f"candidate model artifact {index} is malformed")
        require_exact_keys(artifact, {"filename", "sha256", "bytes"}, label=f"candidate model artifact {index}")
        require(
            artifact.get("filename") == filename
            and artifact.get("sha256") == digest
            and SHA256_UPPER_RE.fullmatch(artifact["sha256"]) is not None
            and type(artifact.get("bytes")) is int
            and artifact["bytes"] == byte_count,
            f"candidate model artifact {filename} drifted",
        )
    require(
        model.get("repository_id") == MODEL_BINDING["model_id"]
        and model.get("revision") == MODEL_BINDING["revision"]
        and model.get("artifact_policy")
        == "EXACT FIVE-FILE SET HASHED BEFORE AND AFTER LOAD"
        and model.get("offline_cpu_load_and_canary") == "PASS"
        and model.get("gpu_real_forward") == "NOT_STARTED"
        and model.get("scientific_result_created") is False,
        "candidate model receipt drifted or claims GPU/scientific execution",
    )
    model_loader = read_stable_text(
        WORKER_ROOT / "app" / "runtime" / "model_loader.py"
    )
    for _, digest, byte_count in expected_model_artifacts:
        require(
            digest.lower() in model_loader and f"{byte_count:_}" in model_loader,
            "candidate model artifact is not bound in the model loader",
        )

    preflight = receipt.get("build_and_preflight")
    require(isinstance(preflight, dict), "candidate build/preflight receipt is missing")
    require_exact_keys(
        preflight,
        {
            "build_status",
            "lock_verification",
            "offline_model_preflight",
            "native_shared_object_count",
            "native_dependency_closure",
            "runtime_no_network_read_only_root",
            "runtime_model_cache",
            "runtime_tmpfs",
        },
        label="candidate build/preflight receipt",
    )
    native = preflight.get("native_dependency_closure")
    require(isinstance(native, dict), "candidate native closure receipt is missing")
    require_exact_keys(
        native,
        {
            "status",
            "allowed_unresolved_soname",
            "allowed_artifact",
            "unexpected_unresolved_dependencies",
        },
        label="candidate native closure",
    )
    require(
        preflight.get("build_status") == "COMPLETED"
        and preflight.get("lock_verification") == "PASS / 73 EXACT DISTRIBUTIONS"
        and preflight.get("offline_model_preflight")
        == "PASS / EXACT PYTHIA ARTIFACT SET"
        and type(preflight.get("native_shared_object_count")) is int
        and preflight["native_shared_object_count"] == 385
        and native
        == {
            "status": "PASS_WITH_EXACT_HOST_DRIVER_SEAM",
            "allowed_unresolved_soname": "libcuda.so.1",
            "allowed_artifact": "torch/lib/libcaffe2_nvrtc.so",
            "unexpected_unresolved_dependencies": 0,
        }
        and preflight.get("runtime_no_network_read_only_root") == "PASS"
        and preflight.get("runtime_model_cache")
        == "EXACT / LOCAL_ONLY / READ_ONLY"
        and preflight.get("runtime_tmpfs")
        == "/tmp:rw,noexec,nosuid,nodev,size=64m",
        "candidate build/preflight evidence drifted",
    )

    probes = receipt.get("runtime_fail_closed_probes")
    require(isinstance(probes, dict), "candidate runtime probes are missing")
    require_exact_keys(
        probes,
        {
            "production_start_without_worker_token",
            "production_start_with_token_without_cuda",
            "production_start_with_token_and_cuda",
        },
        label="candidate runtime probes",
    )
    require(
        probes
        == {
            "production_start_without_worker_token": {
                "status": "PASS / REFUSED_STARTUP",
                "exit_code": 3,
            },
            "production_start_with_token_without_cuda": {
                "status": "PASS / REFUSED_STARTUP",
                "exit_code": 3,
            },
            "production_start_with_token_and_cuda": {
                "status": "NOT_STARTED",
                "exit_code": None,
            },
        },
        "candidate runtime fail-closed probes drifted or claim a GPU start",
    )

    tests = receipt.get("test_receipts")
    require(isinstance(tests, dict), "candidate test receipts are missing")
    require_exact_keys(
        tests,
        {"live_trace_worker_complete", "api_launcher_fleet_state", "receipt_scope"},
        label="candidate test receipts",
    )
    worker_tests = tests.get("live_trace_worker_complete")
    api_tests = tests.get("api_launcher_fleet_state")
    require(isinstance(worker_tests, dict) and isinstance(api_tests, dict), "candidate test receipt is malformed")
    require_exact_keys(worker_tests, {"passed", "failed", "total", "test_ids_sha256"}, label="candidate worker tests")
    require_exact_keys(api_tests, {"passed", "failed", "total", "test_ids_sha256", "targets"}, label="candidate API tests")
    require(
        tests == _historical_dependency_container_candidate_test_receipt(),
        "historical candidate test receipt drifted",
    )

    audits = receipt.get("security_audits")
    require(isinstance(audits, dict), "candidate security audits are missing")
    require_exact_keys(
        audits,
        {
            "python_dependency_audit",
            "torch_osv_query",
            "sbom_full_image_package_scan",
            "full_filesystem_image_scan",
            "scan_summary",
            "security_decision",
        },
        label="candidate security audits",
    )
    python_audit = audits.get("python_dependency_audit")
    require(isinstance(python_audit, dict), "candidate Python dependency audit is missing")
    require_exact_keys(
        python_audit,
        {
            "tool",
            "status",
            "command_scope",
            "successfully_audited_lock_entries",
            "known_vulnerabilities_found",
            "skipped_lock_entries",
            "full_lock_pass",
            "full_image_pass",
        },
        label="candidate Python dependency audit",
    )
    require(
        python_audit.get("tool") == "pip-audit 2.10.1"
        and python_audit.get("status") == "PARTIAL / PASS_WITH_SKIP"
        and python_audit.get("command_scope")
        == "requirements.txt --no-deps --disable-pip --format json"
        and type(python_audit.get("successfully_audited_lock_entries")) is int
        and python_audit["successfully_audited_lock_entries"] == 72
        and type(python_audit.get("known_vulnerabilities_found")) is int
        and python_audit["known_vulnerabilities_found"] == 0
        and python_audit.get("skipped_lock_entries")
        == [
            {
                "package": "torch",
                "version": "2.13.0+cu126",
                "reason": "DIRECT URL REQUIREMENT CANNOT BE PINNED BY PIP-AUDIT",
            }
        ]
        and python_audit.get("full_lock_pass") is False
        and python_audit.get("full_image_pass") is False,
        "candidate Python dependency audit was altered or overstated",
    )
    torch_audit = audits.get("torch_osv_query")
    require(isinstance(torch_audit, dict), "candidate Torch OSV query is missing")
    require_exact_keys(
        torch_audit,
        {
            "source",
            "ecosystem",
            "package",
            "version",
            "status",
            "returned_vulnerability_count",
            "independent_of_pip_audit_skip",
            "full_image_pass",
        },
        label="candidate Torch OSV query",
    )
    require(
        torch_audit
        == {
            "source": "OSV API",
            "ecosystem": "PyPI",
            "package": "torch",
            "version": "2.13.0",
            "status": "COMPLETED / ZERO RETURNED VULNERABILITIES",
            "returned_vulnerability_count": 0,
            "independent_of_pip_audit_skip": True,
            "full_image_pass": False,
        },
        "candidate Torch OSV query was altered or promoted to a full-image PASS",
    )
    sbom_scan = audits.get("sbom_full_image_package_scan")
    require(isinstance(sbom_scan, dict), "candidate SBOM package scan is missing")
    require_exact_keys(
        sbom_scan,
        {
            "tool",
            "evidence_class",
            "raw_report_retained",
            "repository_replayable",
            "input",
            "input_digest",
            "command_profile",
            "target_manifest_digest",
            "platform",
            "observed_at",
            "package_count",
            "vulnerable_package_count",
            "vulnerability_count",
            "status",
            "exit_code",
            "passed",
            "unfiltered_rescan_matched",
            "unspecified_severity_count",
            "severity_counts",
            "findings",
        },
        label="candidate SBOM package scan",
    )
    expected_findings = [
        {
            "severity": "MEDIUM",
            "package": "util-linux",
            "version": "2.39.3-9ubuntu6.5",
            "advisory": "CVE-2026-27456",
            "fix_status": "UNFIXED",
        },
        {
            "severity": "MEDIUM",
            "package": "libp11-kit0",
            "version": "0.25.3-4ubuntu2.1",
            "advisory": "CVE-2026-13757",
            "fix_status": "UNFIXED",
        },
        {
            "severity": "MEDIUM",
            "package": "dpkg",
            "version": "1.22.6ubuntu6.6",
            "advisory": "CVE-2026-2219",
            "fix_status": "UNFIXED",
        },
        {
            "severity": "LOW",
            "package": "zlib1g",
            "version": "1:1.3.dfsg-3.1ubuntu2.1",
            "advisory": "CVE-2026-27171",
            "fix_status": "UNFIXED",
        },
        {
            "severity": "LOW",
            "package": "libgcrypt20",
            "version": "1.10.3-2ubuntu0.1",
            "advisory": "CVE-2024-2236",
            "fix_status": "UNFIXED",
        },
        {
            "severity": "LOW",
            "package": "passwd",
            "version": "1:4.13+dfsg1-4ubuntu3.2",
            "advisory": "CVE-2024-56433",
            "fix_status": "UNFIXED",
        },
        {
            "severity": "LOW",
            "package": "libudev1",
            "version": "255.4-1ubuntu8.16",
            "advisory": "CVE-2026-40228",
            "fix_status": "UNFIXED",
        },
    ]
    _require_oci_digest(sbom_scan.get("input_digest"), label="SBOM scan input")
    _require_oci_digest(
        sbom_scan.get("target_manifest_digest"), label="SBOM scan target"
    )
    require(
        sbom_scan.get("tool") == "Docker Scout 1.24.0"
        and sbom_scan.get("evidence_class") == "SELF_REPORTED_LOCAL_OBSERVATION"
        and sbom_scan.get("raw_report_retained") is False
        and sbom_scan.get("repository_replayable") is False
        and sbom_scan.get("input") == "IN-TOTO SPDX ATTESTATION"
        and sbom_scan.get("input_digest") == sbom["digest"]
        and sbom_scan.get("command_profile")
        == "cves --exit-code --only-severity critical,high,medium,low sbom://"
        and sbom_scan.get("target_manifest_digest")
        == CANDIDATE_OCI_DIGESTS["platform_manifest_digest"]
        and sbom_scan.get("platform") == "linux/amd64"
        and sbom_scan.get("observed_at") == "2026-08-05T22:16:49Z"
        and type(sbom_scan.get("package_count")) is int
        and sbom_scan["package_count"] == 190
        and type(sbom_scan.get("vulnerable_package_count")) is int
        and sbom_scan["vulnerable_package_count"] == 7
        and type(sbom_scan.get("vulnerability_count")) is int
        and sbom_scan["vulnerability_count"] == 7
        and sbom_scan.get("status") == "COMPLETED_WITH_FINDINGS"
        and type(sbom_scan.get("exit_code")) is int
        and sbom_scan["exit_code"] == 2
        and sbom_scan.get("passed") is False
        and sbom_scan.get("unfiltered_rescan_matched") is True
        and type(sbom_scan.get("unspecified_severity_count")) is int
        and sbom_scan["unspecified_severity_count"] == 0
        and sbom_scan.get("severity_counts")
        == {"critical": 0, "high": 0, "medium": 3, "low": 4}
        and sbom_scan.get("findings") == expected_findings,
        "candidate SBOM package scan was altered, zeroed, or promoted to PASS",
    )
    image_scan = audits.get("full_filesystem_image_scan")
    require(isinstance(image_scan, dict), "candidate full-image scan record is missing")
    require_exact_keys(
        image_scan,
        {"tool", "status", "completed", "passed", "finding_count", "observed_result"},
        label="candidate full-image scan",
    )
    require(
        image_scan.get("tool") == "Docker Scout 1.24.0"
        and image_scan.get("status") == "INCOMPLETE / PENDING"
        and image_scan.get("completed") is False
        and image_scan.get("passed") is False
        and image_scan.get("finding_count") is None
        and isinstance(image_scan.get("observed_result"), str)
        and "did not complete" in image_scan["observed_result"]
        and "neither scan supplies a PASS" in image_scan["observed_result"]
        and audits.get("scan_summary")
        == "SBOM FULL-IMAGE PACKAGE SCAN COMPLETED_WITH_FINDINGS / DIRECT LOCAL FILESYSTEM SCAN INCOMPLETE / NO PASS"
        and audits.get("security_decision") == "OPEN_SECURITY",
        "candidate receipt forges or removes the incomplete full-image security scan",
    )

    boundaries = receipt.get("unresolved_boundaries")
    require(
        boundaries
        == {
            "sbom_full_image_package_findings": "OPEN / 3 MEDIUM / 4 LOW / ALL UNFIXED",
            "direct_local_filesystem_image_scan": "PENDING",
            "raw_build_security_evidence_retention": "OPEN",
            "test_runner_hermeticity_and_same_run_node_ids": "OPEN",
            "hardlink_reparse_and_aba_resistance": "OPEN",
            "gpu_real_forward": "NOT_STARTED",
            "independent_clean_reproduction": "OPEN",
            "durable_append_only_worm_anchor": "OPEN",
            "independent_manifest_trust_root": "OPEN",
            "model_artifact_materializer": "OPEN",
            "worker_to_kernel_protocol": "OPEN",
            "licensing": "NOT LICENSED",
            "public_disclosure": "HELD",
        },
        "candidate unresolved-boundary surface drifted",
    )
    historical = receipt.get("historical_adverse_evidence")
    require(
        historical
        == {
            "binding_path": MODEL_DEPENDENCY_BINDING_PATH.relative_to(ROOT).as_posix(),
            "preserved_unchanged": True,
            "historical_transformers_pin": "4.46.3",
            "historical_advisory": "CVE-2026-4372 / GHSA-29pf-2h5f-8g72",
            "interpretation": (
                "The v0.1 binding remains the adverse historical record. This v0.2 "
                "candidate does not rewrite it or close G5-ENGINEERING-003."
            ),
        },
        "candidate receipt erases or rewrites the historical adverse binding",
    )
    claim_boundary = receipt.get("claim_boundary")
    require(
        claim_boundary
        == {
            "integrity_evidence_effect": "STRUCTURAL_CANDIDATE_ONLY",
            "external_evidence_effect": "SELF_REPORTED_LOCAL_OBSERVATION_ONLY",
            "security_effect": "OPEN_SECURITY",
            "scientific_effect": "NONE",
            "canon_effect": "NONE",
            "product_claim_effect": "NONE",
            "license_effect": "NONE",
            "disclosure_effect": "NONE",
        },
        "candidate receipt claims an unauthorized effect",
    )
    return receipt


def verify_raw_build_and_security_evidence_receipt() -> dict[str, Any]:
    receipt = load_json(RAW_BUILD_SECURITY_RECEIPT_PATH)
    require(isinstance(receipt, dict), "raw build/security receipt is not an object")
    require_exact_keys(
        receipt,
        {
            "schema_version",
            "document_status",
            "gate5_status",
            "gate_decision",
            "admission_ring",
            "license_status",
            "disclosure_status",
            "public_disclosure_authorized",
            "experimental_execution_status",
            "security_disposition",
            "live_execution_authorized",
            "candidate_accepted",
            "collection_context",
            "candidate_identity",
            "evidence_files",
            "original_oci_and_attestation_closure",
            "buildkit_history_bundle",
            "direct_local_image_reports",
            "current_vendor_triage",
            "retention_status",
            "unresolved_boundaries",
            "claim_boundary",
        },
        label="Gate 5 raw build/security receipt",
    )
    require(
        receipt.get("schema_version")
        == "project_coherence.gate5_raw_build_and_security_evidence_receipt.v0.1",
        "unexpected raw build/security receipt schema",
    )
    for field, expected in {
        "document_status": "DRAFT / OPEN / NOT FROZEN",
        "gate5_status": "OPEN",
        "gate_decision": "KEEP_OPEN",
        "admission_ring": 4,
        "license_status": "NOT LICENSED",
        "disclosure_status": "HELD",
        "public_disclosure_authorized": False,
        "experimental_execution_status": "NOT_STARTED",
        "security_disposition": "OPEN_SECURITY",
        "live_execution_authorized": False,
        "candidate_accepted": False,
    }.items():
        value = receipt.get(field)
        if field == "admission_ring":
            require(type(value) is int, "raw evidence ring must be an exact integer")
        require(value == expected, f"raw build/security receipt {field} drifted")

    require(
        receipt.get("collection_context")
        == {
            "collection_parent_commit": "a1cd990109e7561dfd03949bf0e1653461c7ae44",
            "candidate_source_commit": CANDIDATE_SOURCE_COMMIT,
            "local_clock_date": "2026-08-05",
            "trusted_time_established": False,
            "collector_class": "LOCAL_SELF_OBSERVED / NOT INDEPENDENTLY ATTESTED",
            "docker_client_version": "29.6.1",
            "docker_engine_version": "29.6.1",
            "docker_cli_binary_sha256": "E768033E4B3F0DC760162F417A80360094644D16CD9FB12AD65C9D97508C076F",
            "buildx_version": "0.35.0-desktop.2",
            "buildx_commit": "b554ce1decd8b509893b1e7c6227eabfb923d094",
            "buildkit_version_from_attestation": "0.31.1",
            "scout_version": "1.21.0",
            "scout_commit": "9ef488e4004aa6924ec709d3c601e0bd761212c7",
            "scout_binary_sha256": "115670A40189EB05571130471BBE0AF7743AC5E86D00BA1B42A0546ECF7E1C83",
            "scanner_database_identity": "NOT EXPOSED OR RETAINED",
        },
        "raw evidence collection context drifted or claims trusted collection",
    )
    require(
        receipt.get("candidate_identity")
        == {
            "build_ref": CANDIDATE_BUILD_REF,
            "image_tag": "atlas-live-trace-worker:gate5-candidate-v0.2",
            "platform": "linux/amd64",
            **CANDIDATE_OCI_DIGESTS,
            "attestation_manifest_digest": "sha256:b1db5924ab8ce96927f0164c4626cd5eb0c86cbd3fb35c0387b622dd7ae390d1",
            "attestation_config_digest": "sha256:4592edd32ecc05f0ce5fca43216dea1393293b07245db9582989ed3cb77f5ad7",
            "image_size_bytes": 4_396_739_765,
            "source_commit_label_matched": True,
        },
        "raw evidence candidate identity drifted",
    )

    expected_files = {
        "G5-RAW-BUILDKIT-HISTORY-EXPORT": (
            "docs/working/project_coherence/gate5/evidence/raw/candidate_v0.2_20260805/vz8s61131470ab8uivga0qcdq.dockerbuild",
            29_058,
            "4E9B23B4CAE00C566AC0BD952F1DDDFF2FCC5811D06F43CA093639369B81E017",
        ),
        "G5-RAW-OCI-INDEX": (
            "docs/working/project_coherence/gate5/evidence/raw/candidate_v0.2_20260805/oci-index.json",
            856,
            "3D747B379938A5148E4A028FF8BA2F242847B17E8842F19F0D2C204B3FE9A95C",
        ),
        "G5-RAW-PLATFORM-MANIFEST": (
            "docs/working/project_coherence/gate5/evidence/raw/candidate_v0.2_20260805/platform-manifest.json",
            3_528,
            "60BF92B327EBEC84887C659313A97A6369A24FD5D8EB00A012544FCAFD26BA27",
        ),
        "G5-RAW-IMAGE-CONFIG": (
            "docs/working/project_coherence/gate5/evidence/raw/candidate_v0.2_20260805/image-config.json",
            11_727,
            "966DB6E2E05366BE99129AF5C866A8F7EFBF01B04145C49EF431785FDC1432ED",
        ),
        "G5-RAW-ATTESTATION-MANIFEST": (
            "docs/working/project_coherence/gate5/evidence/raw/candidate_v0.2_20260805/attestation-manifest.json",
            839,
            "B1DB5924AB8CE96927F0164C4626CD5EB0C86CBD3FB35C0387B622DD7AE390D1",
        ),
        "G5-RAW-ATTESTATION-CONFIG": (
            "docs/working/project_coherence/gate5/evidence/raw/candidate_v0.2_20260805/attestation-config.json",
            241,
            "4592EDD32ECC05F0CE5FCA43216DEA1393293B07245DB9582989ED3CB77F5AD7",
        ),
        "G5-RAW-ORIGINAL-SPDX": (
            "docs/working/project_coherence/gate5/evidence/raw/candidate_v0.2_20260805/sbom.intoto.spdx.json",
            2_957_946,
            "8D039B378DFC422BAE2D7479A06BFA2AC9C94A9A19FE8AA115362A28EC41955E",
        ),
        "G5-RAW-ORIGINAL-SLSA": (
            "docs/working/project_coherence/gate5/evidence/raw/candidate_v0.2_20260805/provenance.intoto.slsa-v1.json",
            45_532,
            "F8E3677325D096191BB7EC1D075A34ADDF4E4733A48D3AE442F63C1BB74A6C6F",
        ),
        "G5-RAW-CURRENT-DIRECT-SBOM": (
            "docs/working/project_coherence/gate5/evidence/raw/candidate_v0.2_20260805/atlas-live-trace-worker_gate5-candidate-v0.2.scout.spdx.json",
            869_291,
            "5434A19BD5DEF2770FE60929F3AF321713080A94D960B1F9EB4401A9EA812F15",
        ),
        "G5-RAW-CURRENT-DIRECT-CVE-SCAN": (
            "docs/working/project_coherence/gate5/evidence/raw/candidate_v0.2_20260805/atlas-live-trace-worker_gate5-candidate-v0.2.scout.cves.exit2.sarif.json",
            38_589,
            "5D152C419DC6207D197C29C934E480B281864DAAF233F662B6AD6A69894E75B1",
        ),
    }
    expected_file_metadata = {
        "G5-RAW-BUILDKIT-HISTORY-EXPORT": {
            "role": "NATIVE_BUILDKIT_HISTORY_OCI_ARCHIVE",
            "media_type": "application/vnd.oci.image.layout.v1.tar",
            "origin": (
                "docker buildx history export --output <path> "
                "vz8s61131470ab8uivga0qcdq"
            ),
            "evidence_class": (
                "ORIGINAL LOCAL BUILDKIT RECORD / RAW BYTES RETAINED"
            ),
        },
        "G5-RAW-OCI-INDEX": {
            "role": "ORIGINAL_OCI_IMAGE_INDEX",
            "media_type": "application/vnd.oci.image.index.v1+json",
            "origin": (
                "docker buildx history inspect attachment vz8s61131470ab8uivga0qcdq "
                "sha256:3d747b379938a5148e4a028ff8ba2f242847b17e8842f19f0d2c204b3fe9a95c"
            ),
            "evidence_class": (
                "ORIGINAL OCI ATTACHMENT / DIGEST-MATCHED RAW BYTES RETAINED"
            ),
        },
        "G5-RAW-PLATFORM-MANIFEST": {
            "role": "ORIGINAL_OCI_PLATFORM_MANIFEST",
            "media_type": "application/vnd.oci.image.manifest.v1+json",
            "origin": (
                "docker buildx history inspect attachment vz8s61131470ab8uivga0qcdq "
                "sha256:60bf92b327ebec84887c659313a97a6369a24fd5d8eb00a012544fcafd26ba27"
            ),
            "evidence_class": (
                "ORIGINAL OCI ATTACHMENT / DIGEST-MATCHED RAW BYTES RETAINED"
            ),
        },
        "G5-RAW-IMAGE-CONFIG": {
            "role": "ORIGINAL_OCI_IMAGE_CONFIG",
            "media_type": "application/vnd.oci.image.config.v1+json",
            "origin": (
                "docker buildx history inspect attachment vz8s61131470ab8uivga0qcdq "
                "sha256:966db6e2e05366be99129af5c866a8f7efbf01b04145c49ef431785fdc1432ed"
            ),
            "evidence_class": (
                "ORIGINAL OCI ATTACHMENT / DIGEST-MATCHED RAW BYTES RETAINED"
            ),
        },
        "G5-RAW-ATTESTATION-MANIFEST": {
            "role": "ORIGINAL_OCI_ATTESTATION_MANIFEST",
            "media_type": "application/vnd.oci.image.manifest.v1+json",
            "origin": (
                "docker buildx history inspect attachment vz8s61131470ab8uivga0qcdq "
                "sha256:b1db5924ab8ce96927f0164c4626cd5eb0c86cbd3fb35c0387b622dd7ae390d1"
            ),
            "evidence_class": (
                "ORIGINAL OCI ATTACHMENT / DIGEST-MATCHED RAW BYTES RETAINED"
            ),
        },
        "G5-RAW-ATTESTATION-CONFIG": {
            "role": "ORIGINAL_OCI_ATTESTATION_CONFIG",
            "media_type": "application/vnd.oci.image.config.v1+json",
            "origin": (
                "docker buildx history inspect attachment vz8s61131470ab8uivga0qcdq "
                "sha256:4592edd32ecc05f0ce5fca43216dea1393293b07245db9582989ed3cb77f5ad7"
            ),
            "evidence_class": (
                "ORIGINAL OCI ATTACHMENT / DIGEST-MATCHED RAW BYTES RETAINED"
            ),
        },
        "G5-RAW-ORIGINAL-SPDX": {
            "role": "ORIGINAL_BUILDKIT_IN_TOTO_SPDX_STATEMENT",
            "media_type": (
                "application/vnd.in-toto+json; predicate=https://spdx.dev/Document"
            ),
            "origin": (
                "docker buildx history inspect attachment vz8s61131470ab8uivga0qcdq "
                "sha256:8d039b378dfc422bae2d7479a06bfa2ac9c94a9a19fe8aa115362a28ec41955e"
            ),
            "evidence_class": (
                "ORIGINAL BUILDKIT ATTESTATION / DIGEST-MATCHED RAW BYTES RETAINED"
            ),
        },
        "G5-RAW-ORIGINAL-SLSA": {
            "role": "ORIGINAL_BUILDKIT_IN_TOTO_SLSA_STATEMENT",
            "media_type": (
                "application/vnd.in-toto+json; predicate=https://slsa.dev/provenance/v1"
            ),
            "origin": (
                "docker buildx history inspect attachment vz8s61131470ab8uivga0qcdq "
                "sha256:f8e3677325d096191bb7ec1d075a34addf4e4733a48d3ae442f63c1bb74a6c6f"
            ),
            "evidence_class": (
                "ORIGINAL BUILDKIT ATTESTATION / DIGEST-MATCHED RAW BYTES RETAINED"
            ),
        },
        "G5-RAW-CURRENT-DIRECT-SBOM": {
            "role": "CURRENT_DIRECT_LOCAL_IMAGE_SPDX_REPORT",
            "media_type": "application/spdx+json",
            "origin": (
                "docker scout sbom --format spdx --output <path> "
                "local://atlas-live-trace-worker:gate5-candidate-v0.2"
            ),
            "evidence_class": (
                "NEW SCOUT 1.21.0 DIRECT LOCAL IMAGE REPORT / RAW REPORT RETAINED"
            ),
        },
        "G5-RAW-CURRENT-DIRECT-CVE-SCAN": {
            "role": "CURRENT_DIRECT_LOCAL_IMAGE_CVE_SARIF_REPORT",
            "media_type": "application/sarif+json",
            "origin": (
                "docker scout cves --exit-code --format sarif --only-severity "
                "critical,high,medium,low --output <path> "
                "local://atlas-live-trace-worker:gate5-candidate-v0.2"
            ),
            "evidence_class": (
                "NEW SCOUT 1.21.0 DIRECT LOCAL IMAGE REPORT / RAW REPORT RETAINED"
            ),
        },
    }
    records = receipt.get("evidence_files")
    require(isinstance(records, list), "raw evidence file index is missing")
    require(len(records) == len(expected_files), "raw evidence file count drifted")
    observed_ids: list[str] = []
    raw_paths: dict[str, Path] = {}
    for index, record in enumerate(records):
        require(isinstance(record, dict), f"raw evidence file {index} is malformed")
        require_exact_keys(
            record,
            {
                "evidence_id",
                "role",
                "path",
                "media_type",
                "bytes",
                "sha256",
                "origin",
                "evidence_class",
            },
            label=f"raw evidence file {index}",
        )
        evidence_id = record.get("evidence_id")
        require(evidence_id in expected_files, f"unknown raw evidence ID: {evidence_id}")
        expected_path, expected_bytes, expected_sha = expected_files[evidence_id]
        require(
            type(record.get("bytes")) is int
            and record
            == {
                "evidence_id": evidence_id,
                **expected_file_metadata[evidence_id],
                "path": expected_path,
                "bytes": expected_bytes,
                "sha256": expected_sha,
            },
            f"raw evidence record {evidence_id} drifted or claims independent trust",
        )
        raw_path = ROOT / canonical_repo_path(expected_path, label=evidence_id)
        observation = observe_regular_file(raw_path, anchor=FILESYSTEM_ANCHOR)
        require(
            observation.byte_count == expected_bytes and observation.sha256 == expected_sha,
            f"raw evidence bytes drifted: {evidence_id}",
        )
        observed_ids.append(evidence_id)
        raw_paths[evidence_id] = raw_path
    require(
        observed_ids == list(expected_files),
        "raw evidence records are not in the frozen evidence-ID order",
    )

    oci_index = load_json(raw_paths["G5-RAW-OCI-INDEX"])
    platform_manifest = load_json(raw_paths["G5-RAW-PLATFORM-MANIFEST"])
    image_config = load_json(raw_paths["G5-RAW-IMAGE-CONFIG"])
    attestation_manifest = load_json(raw_paths["G5-RAW-ATTESTATION-MANIFEST"])
    attestation_config = load_json(raw_paths["G5-RAW-ATTESTATION-CONFIG"])
    require(
        oci_index.get("schemaVersion") == 2
        and oci_index.get("mediaType") == "application/vnd.oci.image.index.v1+json"
        and [entry["digest"] for entry in oci_index.get("manifests", [])]
        == [
            CANDIDATE_OCI_DIGESTS["platform_manifest_digest"],
            "sha256:b1db5924ab8ce96927f0164c4626cd5eb0c86cbd3fb35c0387b622dd7ae390d1",
        ],
        "original OCI index does not close over the platform and attestation manifests",
    )
    require(
        platform_manifest.get("config")
        == {
            "mediaType": "application/vnd.oci.image.config.v1+json",
            "digest": CANDIDATE_OCI_DIGESTS["image_config_digest"],
            "size": 11_727,
        }
        and len(platform_manifest.get("layers", [])) == 17,
        "original platform manifest config/layer closure drifted",
    )
    labels = image_config.get("config", {}).get("Labels", {})
    require(
        image_config.get("architecture") == "amd64"
        and image_config.get("os") == "linux"
        and image_config.get("config", {}).get("User") == "10001:10001"
        and labels.get("org.opencontainers.image.revision") == CANDIDATE_SOURCE_COMMIT,
        "original image config identity drifted",
    )
    require(
        attestation_manifest.get("config")
        == {
            "mediaType": "application/vnd.oci.image.config.v1+json",
            "digest": "sha256:4592edd32ecc05f0ce5fca43216dea1393293b07245db9582989ed3cb77f5ad7",
            "size": 241,
        }
        and [entry["digest"] for entry in attestation_manifest.get("layers", [])]
        == [
            "sha256:8d039b378dfc422bae2d7479a06bfa2ac9c94a9a19fe8aa115362a28ec41955e",
            "sha256:f8e3677325d096191bb7ec1d075a34addf4e4733a48d3ae442f63c1bb74a6c6f",
        ],
        "original attestation manifest closure drifted",
    )
    require(
        attestation_config.get("rootfs", {}).get("diff_ids")
        == [
            "sha256:8d039b378dfc422bae2d7479a06bfa2ac9c94a9a19fe8aa115362a28ec41955e",
            "sha256:f8e3677325d096191bb7ec1d075a34addf4e4733a48d3ae442f63c1bb74a6c6f",
        ],
        "original attestation config does not bind both statement digests",
    )

    original_spdx = load_json(raw_paths["G5-RAW-ORIGINAL-SPDX"])
    require_exact_keys(
        original_spdx,
        {"_type", "predicateType", "subject", "predicate"},
        label="original BuildKit SPDX statement",
    )
    spdx_predicate = original_spdx.get("predicate")
    require(isinstance(spdx_predicate, dict), "original SPDX predicate is missing")
    require(
        original_spdx.get("_type") == "https://in-toto.io/Statement/v1"
        and original_spdx.get("predicateType") == "https://spdx.dev/Document"
        and original_spdx.get("subject")
        == [
            {
                "name": "pkg:docker/atlas-live-trace-worker@gate5-candidate-v0.2?platform=linux%2Famd64",
                "digest": {
                    "sha256": CANDIDATE_OCI_DIGESTS["platform_manifest_digest"].split(":", 1)[1]
                },
            }
        ]
        and spdx_predicate.get("spdxVersion") == "SPDX-2.3"
        and len(spdx_predicate.get("packages", [])) == 199
        and len(spdx_predicate.get("files", [])) == 3_130
        and len(spdx_predicate.get("relationships", [])) == 3_971
        and spdx_predicate.get("creationInfo", {}).get("creators")
        == [
            "Organization: Anchore, Inc",
            "Tool: syft-v1.42.3",
            "Tool: buildkit-v0.31.1",
        ],
        "original BuildKit SPDX content/subject drifted",
    )

    original_slsa = load_json(raw_paths["G5-RAW-ORIGINAL-SLSA"])
    require_exact_keys(
        original_slsa,
        {"_type", "predicateType", "subject", "predicate"},
        label="original BuildKit SLSA statement",
    )
    slsa_predicate = original_slsa.get("predicate")
    require(isinstance(slsa_predicate, dict), "original SLSA predicate is missing")
    build_definition = slsa_predicate.get("buildDefinition", {})
    run_details = slsa_predicate.get("runDetails", {})
    metadata = run_details.get("metadata", {})
    external = build_definition.get("externalParameters", {})
    root_request = external.get("request", {}).get("root", {}).get("request", {})
    require(
        original_slsa.get("_type") == "https://in-toto.io/Statement/v1"
        and original_slsa.get("predicateType") == "https://slsa.dev/provenance/v1"
        and original_slsa.get("subject") == original_spdx.get("subject")
        and build_definition.get("buildType")
        == "https://github.com/moby/buildkit/blob/master/docs/attestations/slsa-definitions.md"
        and len(build_definition.get("resolvedDependencies", [])) == 3
        and root_request.get("args", {}).get("vcs:revision") == CANDIDATE_SOURCE_COMMIT
        and root_request.get("args", {}).get("vcs:source")
        == "https://github.com/LittleHenderson/noetic-compass.git"
        and run_details.get("builder") == {"id": ""}
        and metadata.get("startedOn") == "2026-08-05T21:53:38.606917835Z"
        and metadata.get("finishedOn") == "2026-08-05T21:55:13.232859726Z"
        and metadata.get("buildkit_completeness")
        == {"request": True, "resolvedDependencies": False},
        "original BuildKit SLSA content, source, or adverse trust facts drifted",
    )
    require(
        receipt.get("original_oci_and_attestation_closure")
        == {
            "index_references_platform_and_attestation_manifests": (
                [entry["digest"] for entry in oci_index["manifests"]]
                == [
                    CANDIDATE_OCI_DIGESTS["platform_manifest_digest"],
                    "sha256:b1db5924ab8ce96927f0164c4626cd5eb0c86cbd3fb35c0387b622dd7ae390d1",
                ]
            ),
            "platform_manifest_references_exact_image_config": (
                platform_manifest["config"]["digest"]
                == CANDIDATE_OCI_DIGESTS["image_config_digest"]
            ),
            "attestation_manifest_references_exact_config_and_two_statements": (
                attestation_manifest["config"]["digest"]
                == "sha256:4592edd32ecc05f0ce5fca43216dea1393293b07245db9582989ed3cb77f5ad7"
                and [entry["digest"] for entry in attestation_manifest["layers"]]
                == [
                    "sha256:8d039b378dfc422bae2d7479a06bfa2ac9c94a9a19fe8aa115362a28ec41955e",
                    "sha256:f8e3677325d096191bb7ec1d075a34addf4e4733a48d3ae442f63c1bb74a6c6f",
                ]
            ),
            "attestation_config_diff_ids_match_statement_digests": (
                attestation_config["rootfs"]["diff_ids"]
                == [entry["digest"] for entry in attestation_manifest["layers"]]
            ),
            "image_architecture": image_config["architecture"],
            "image_os": image_config["os"],
            "image_user": image_config["config"]["User"],
            "image_source_revision": labels["org.opencontainers.image.revision"],
            "spdx_predicate_type": original_spdx["predicateType"],
            "spdx_version": spdx_predicate["spdxVersion"],
            "spdx_subject_digest": (
                "sha256:" + original_spdx["subject"][0]["digest"]["sha256"]
            ),
            "spdx_package_records": len(spdx_predicate["packages"]),
            "spdx_file_records": len(spdx_predicate["files"]),
            "spdx_relationship_records": len(spdx_predicate["relationships"]),
            "spdx_creators": spdx_predicate["creationInfo"]["creators"],
            "slsa_predicate_type": original_slsa["predicateType"],
            "slsa_subject_digest": (
                "sha256:" + original_slsa["subject"][0]["digest"]["sha256"]
            ),
            "slsa_build_type": build_definition["buildType"],
            "slsa_builder_id": run_details["builder"]["id"],
            "slsa_resolved_dependency_count": len(
                build_definition["resolvedDependencies"]
            ),
            "slsa_source_revision": root_request["args"]["vcs:revision"],
            "slsa_started_on": metadata["startedOn"],
            "slsa_finished_on": metadata["finishedOn"],
            "slsa_request_complete": metadata["buildkit_completeness"]["request"],
            "slsa_resolved_dependencies_complete": metadata[
                "buildkit_completeness"
            ]["resolvedDependencies"],
            "independent_signature_or_trust_root": False,
        },
        "raw receipt OCI/SPDX/SLSA closure summary is not derived from retained bytes",
    )

    bundle_payload = read_stable_bytes(raw_paths["G5-RAW-BUILDKIT-HISTORY-EXPORT"])
    expected_bundle_members = {
        "blobs": ("dir", 0),
        "blobs/sha256": ("dir", 0),
        "blobs/sha256/0b2b290a282392c00a2c74122716b45609c1be1132300e2727794858db912cb7": ("file", 95_098),
        "blobs/sha256/36bc87d2b88089eda3958edb5dbcf4cbdd5b5c01e16725e1dbeb49171c23b971": ("file", 113_223),
        "blobs/sha256/3d747b379938a5148e4a028ff8ba2f242847b17e8842f19f0d2c204b3fe9a95c": ("file", 856),
        "blobs/sha256/5595d0120176d269bc15ee7030eef2392bd9b7373db290a2c4ac959f33c4be28": ("file", 13_879),
        "blobs/sha256/b0a65a75178d815489cd11cc3a2d89c0e57040e806f78647c81a341738a46305": ("file", 24_374),
        "blobs/sha256/c23dfeeea6a44c6f250fc3c7ea2c572f1664d54e65ec1c96d675007d76b43fdc": ("file", 1_218),
        "index.json": ("file", 241),
        "oci-layout": ("file", 30),
    }
    try:
        archive = tarfile.open(fileobj=io.BytesIO(bundle_payload), mode="r:*")
    except (tarfile.TarError, OSError) as exc:
        raise VerificationError(f"cannot parse native BuildKit history bundle: {exc}") from exc
    with archive:
        members = archive.getmembers()
        require(
            len(members) == len({member.name for member in members}),
            "BuildKit history bundle contains duplicate member names",
        )
        require(
            {member.name for member in members} == set(expected_bundle_members),
            "BuildKit history bundle member surface drifted",
        )
        extracted: dict[str, bytes] = {}
        for member in members:
            pure = PurePosixPath(member.name)
            require(
                not pure.is_absolute() and "." not in pure.parts and ".." not in pure.parts,
                f"BuildKit history bundle member traverses: {member.name}",
            )
            expected_kind, expected_size = expected_bundle_members[member.name]
            require(
                member.size == expected_size
                and ((expected_kind == "dir" and member.isdir()) or (expected_kind == "file" and member.isfile()))
                and not member.issym()
                and not member.islnk()
                and not member.isdev(),
                f"BuildKit history member type/size drifted: {member.name}",
            )
            if member.isfile():
                handle = archive.extractfile(member)
                require(handle is not None, f"cannot read BuildKit history member: {member.name}")
                payload = handle.read()
                extracted[member.name] = payload
                if member.name.startswith("blobs/sha256/"):
                    require(
                        hashlib.sha256(payload).hexdigest() == PurePosixPath(member.name).name,
                        f"BuildKit blob digest differs from its name: {member.name}",
                    )
        bundle_index = json.loads(
            extracted["index.json"].decode("utf-8"), object_pairs_hook=_unique_object
        )
        oci_layout = json.loads(
            extracted["oci-layout"].decode("utf-8"), object_pairs_hook=_unique_object
        )
        require(
            oci_layout == {"imageLayoutVersion": "1.0.0"},
            "BuildKit history bundle OCI layout version drifted",
        )
        require(
            bundle_index.get("manifests")
            == [
                {
                    "mediaType": "application/vnd.oci.image.manifest.v1+json",
                    "digest": "sha256:c23dfeeea6a44c6f250fc3c7ea2c572f1664d54e65ec1c96d675007d76b43fdc",
                    "size": 1_218,
                }
            ],
            "BuildKit bundle index cross-link drifted",
        )
        bundle_manifest = json.loads(
            extracted[
                "blobs/sha256/c23dfeeea6a44c6f250fc3c7ea2c572f1664d54e65ec1c96d675007d76b43fdc"
            ].decode("utf-8"),
            object_pairs_hook=_unique_object,
        )
        require(
            bundle_manifest.get("config", {}).get("digest")
            == "sha256:5595d0120176d269bc15ee7030eef2392bd9b7373db290a2c4ac959f33c4be28"
            and [layer["digest"] for layer in bundle_manifest.get("layers", [])]
            == [
                "sha256:0b2b290a282392c00a2c74122716b45609c1be1132300e2727794858db912cb7",
                "sha256:b0a65a75178d815489cd11cc3a2d89c0e57040e806f78647c81a341738a46305",
                "sha256:36bc87d2b88089eda3958edb5dbcf4cbdd5b5c01e16725e1dbeb49171c23b971",
                CANDIDATE_OCI_DIGESTS["oci_image_index_digest"],
            ],
            "BuildKit bundle manifest cross-link drifted",
        )
        history_record = json.loads(
            extracted[
                "blobs/sha256/5595d0120176d269bc15ee7030eef2392bd9b7373db290a2c4ac959f33c4be28"
            ].decode("utf-8"),
            object_pairs_hook=_unique_object,
        )
        attrs = history_record.get("FrontendAttrs", {})
        require(
            history_record.get("Ref") == CANDIDATE_BUILD_REF
            and attrs.get("vcs:revision") == CANDIDATE_SOURCE_COMMIT
            and attrs.get("vcs:source") == "https://github.com/LittleHenderson/noetic-compass.git"
            and attrs.get("attest:provenance") == "type=provenance,mode=max"
            and attrs.get("attest:sbom") == "type=sbom"
            and history_record.get("DefaultPlatform") == "linux/amd64"
            and history_record.get("numCompletedSteps") == 36
            and history_record.get("numTotalSteps") == 36
            and history_record.get("numCachedSteps") == 18,
            "BuildKit history record identity or completion facts drifted",
        )
        bundle_layers = [layer["digest"] for layer in bundle_manifest["layers"]]
        require(
            receipt.get("buildkit_history_bundle")
            == {
                "oci_layout_version": oci_layout["imageLayoutVersion"],
                "member_count": len(members),
                "regular_file_count": sum(member.isfile() for member in members),
                "history_record_digest": bundle_manifest["config"]["digest"],
                "expanded_provenance_predicate_digest": bundle_layers[2],
                "trace_digest": bundle_layers[0],
                "status_log_digest": bundle_layers[1],
                "build_ref_matched": history_record["Ref"] == CANDIDATE_BUILD_REF,
                "source_commit_matched": (
                    attrs["vcs:revision"] == CANDIDATE_SOURCE_COMMIT
                ),
                "source_repository_matched": (
                    attrs["vcs:source"]
                    == "https://github.com/LittleHenderson/noetic-compass.git"
                ),
                "provenance_requested_mode": attrs["attest:provenance"],
                "sbom_requested_mode": attrs["attest:sbom"],
                "platform": history_record["DefaultPlatform"],
                "completed_steps": history_record["numCompletedSteps"],
                "total_steps": history_record["numTotalSteps"],
                "cached_steps": history_record["numCachedSteps"],
                "trust_boundary": (
                    "LOCAL BUILDKIT CONTENT RECORD / NO INDEPENDENT SIGNER OR "
                    "TRUST ROOT"
                ),
            },
            "raw receipt BuildKit bundle summary is not derived from retained bytes",
        )

    direct_spdx = load_json(raw_paths["G5-RAW-CURRENT-DIRECT-SBOM"])
    direct_packages = direct_spdx.get("packages", [])
    require(
        direct_spdx.get("spdxVersion") == "SPDX-2.3"
        and direct_spdx.get("name") == "atlas-live-trace-worker"
        and isinstance(direct_packages, list)
        and len(direct_packages) == 233
        and direct_spdx.get("creationInfo", {}).get("creators")
        == ["Organization: Docker, Inc", "Tool: docker-scout-1.21.0"],
        "current direct local-image SPDX report drifted",
    )
    root_packages = [
        package
        for package in direct_packages
        if isinstance(package, dict) and package.get("SPDXID") == "SPDXRef-DocumentRoot"
    ]
    require(
        root_packages
        == [
            {
                "name": "atlas-live-trace-worker",
                "SPDXID": "SPDXRef-DocumentRoot",
                "versionInfo": "gate5-candidate-v0.2",
                "supplier": "NOASSERTION",
                "downloadLocation": "NOASSERTION",
                "filesAnalyzed": False,
                "licenseConcluded": "NOASSERTION",
                "licenseDeclared": "NOASSERTION",
                "externalRefs": [
                    {
                        "referenceCategory": "PACKAGE-MANAGER",
                        "referenceType": "purl",
                        "referenceLocator": (
                            "pkg:oci/atlas-live-trace-worker@"
                            "sha256:3d747b379938a5148e4a028ff8ba2f242847b17e8842f19f0d2c204b3fe9a95c"
                            "?repository_url=docker.io&tag=gate5-candidate-v0.2"
                        ),
                    }
                ],
                "primaryPackagePurpose": "CONTAINER",
            }
        ],
        "direct SPDX root package is not bound to the exact candidate index digest/tag",
    )
    direct_spdx_purls = {
        reference["referenceLocator"]
        for package in direct_packages
        if isinstance(package, dict)
        for reference in package.get("externalRefs", [])
        if isinstance(reference, dict)
        and reference.get("referenceType") == "purl"
        and isinstance(reference.get("referenceLocator"), str)
    }
    sarif = load_json(raw_paths["G5-RAW-CURRENT-DIRECT-CVE-SCAN"])
    require(
        sarif.get("version") == "2.1.0"
        and isinstance(sarif.get("runs"), list)
        and len(sarif["runs"]) == 1,
        "current direct local-image SARIF envelope drifted",
    )
    run = sarif["runs"][0]
    driver = run.get("tool", {}).get("driver", {})
    rules = driver.get("rules", [])
    results = run.get("results", [])
    require(
        driver.get("name") == "docker scout"
        and driver.get("version") == "1.21.0"
        and len(rules) == 7
        and len(results) == 7,
        "current direct local-image SARIF tool or finding count drifted",
    )
    parsed_findings = [
        {
            "advisory": rule["id"],
            "severity": rule["properties"]["cvssV3_severity"],
            "purl": rule["properties"]["purls"][0],
            "scanner_fixed_version": rule["properties"]["fixed_version"],
        }
        for rule in rules
    ]
    parsed_severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for finding in parsed_findings:
        severity = finding["severity"].lower()
        require(
            severity in parsed_severity_counts,
            f"SARIF finding has an unexpected severity: {finding['severity']!r}",
        )
        parsed_severity_counts[severity] += 1
    require(
        parsed_severity_counts == {"critical": 0, "high": 0, "medium": 3, "low": 4}
        and all(
            finding["scanner_fixed_version"] == "not fixed"
            for finding in parsed_findings
        ),
        "SARIF severity or scanner fixed-version disposition drifted",
    )
    require(
        all(finding["purl"] in direct_spdx_purls for finding in parsed_findings),
        "SARIF finding package purl is absent from the retained direct SPDX report",
    )
    direct_reports = receipt.get("direct_local_image_reports")
    require(isinstance(direct_reports, dict), "direct local-image report summary is missing")
    require_exact_keys(
        direct_reports,
        {"sbom", "cve_scan", "findings"},
        label="direct local-image report summary",
    )
    require(
        direct_reports.get("findings") == parsed_findings
        and direct_reports.get("sbom")
        == {
            "status": "COMPLETED",
            "tool": "docker scout 1.21.0",
            "created_at": "2026-08-05T23:28:12Z",
            "document_name": "atlas-live-trace-worker",
            "spdx_version": "SPDX-2.3",
            "scanner_indexed_component_count": 232,
            "spdx_package_records_including_root_image": 233,
            "stdout_stderr_retained": False,
        }
        and direct_reports.get("cve_scan")
        == {
            "status": "COMPLETED_WITH_FINDINGS",
            "tool": "docker scout 1.21.0",
            "exit_code": 2,
            "sarif_version": "2.1.0",
            "rule_count": 7,
            "result_count": 7,
            "severity_counts": parsed_severity_counts,
            "scanner_fixed_version_disposition": "ALL SEVEN REPORTED AS NOT FIXED",
            "stdout_stderr_retained": False,
            "scanner_database_identity_retained": False,
            "networklessness_certified": False,
        }
        and all(result.get("kind") == "fail" for result in results)
        and [result.get("ruleId") for result in results]
        == [finding["advisory"] for finding in parsed_findings],
        "direct local-image report summary was zeroed, promoted, or detached from SARIF",
    )

    vendor = receipt.get("current_vendor_triage")
    require(isinstance(vendor, dict), "current vendor triage is missing")
    require_exact_keys(
        vendor,
        {
            "checked_on_local_date",
            "authoritative_source",
            "vendor_vulnerable_or_deferred_count",
            "vendor_marks_exact_scanned_version_fixed_count",
            "scanner_vendor_conflict_count",
            "assessments",
            "security_decision",
        },
        label="current vendor triage",
    )
    vendor_expectations = {
        "CVE-2024-2236": (
            "libgcrypt20",
            "Vulnerable, fix deferred",
            "2025-07-11",
            "OPEN / VENDOR CONFIRMS VULNERABLE",
        ),
        "CVE-2024-56433": (
            "shadow",
            "Vulnerable, fix deferred",
            "2025-07-11",
            "OPEN / VENDOR CONFIRMS VULNERABLE",
        ),
        "CVE-2026-13757": (
            "p11-kit",
            "Vulnerable, fix deferred",
            "2026-07-01",
            "OPEN / VENDOR CONFIRMS VULNERABLE",
        ),
        "CVE-2026-2219": (
            "dpkg",
            "Fixed 1.22.6ubuntu6.6",
            "2026-05-13",
            "OPEN RECONCILIATION / VENDOR MARKS EXACT SCANNED VERSION FIXED",
        ),
        "CVE-2026-27171": (
            "zlib",
            "Vulnerable",
            "2026-06-26",
            "OPEN / VENDOR CONFIRMS VULNERABLE",
        ),
        "CVE-2026-27456": (
            "util-linux",
            "Vulnerable",
            "2026-04-08",
            "OPEN / VENDOR CONFIRMS VULNERABLE",
        ),
        "CVE-2026-40228": (
            "systemd",
            "Vulnerable, fix deferred",
            "2026-06-06",
            "OPEN / VENDOR CONFIRMS VULNERABLE",
        ),
    }
    scanner_packages: dict[str, str] = {}
    purl_prefix = "pkg:deb/ubuntu/"
    for finding in parsed_findings:
        advisory = finding["advisory"]
        purl = finding["purl"]
        require(
            advisory not in scanner_packages
            and isinstance(purl, str)
            and purl.startswith(purl_prefix)
            and "@" in purl,
            "scanner finding has a duplicate advisory or malformed Ubuntu purl",
        )
        scanner_packages[advisory] = purl.split("@", 1)[0][len(purl_prefix) :]
    require(
        set(scanner_packages) == set(vendor_expectations),
        "vendor assessment advisory set is detached from retained SARIF findings",
    )
    expected_assessments = []
    for advisory in sorted(vendor_expectations):
        package, ubuntu_status, last_updated, disposition = vendor_expectations[
            advisory
        ]
        require(
            scanner_packages[advisory] == package,
            f"vendor package does not match retained scanner purl: {advisory}",
        )
        expected_assessments.append(
            {
                "advisory": advisory,
                "package": package,
                "ubuntu_release": "24.04 LTS noble",
                "ubuntu_status": ubuntu_status,
                "source_url": f"https://ubuntu.com/security/{advisory}",
                "source_last_updated": last_updated,
                "disposition": disposition,
            }
        )
    vendor_open_count = sum(
        assessment["disposition"] == "OPEN / VENDOR CONFIRMS VULNERABLE"
        for assessment in expected_assessments
    )
    vendor_fixed_count = sum(
        assessment["ubuntu_status"].startswith("Fixed ")
        for assessment in expected_assessments
    )
    scanner_vendor_conflict_count = sum(
        assessment["disposition"].startswith("OPEN RECONCILIATION")
        for assessment in expected_assessments
    )
    require(
        type(vendor.get("vendor_vulnerable_or_deferred_count")) is int
        and type(vendor.get("vendor_marks_exact_scanned_version_fixed_count")) is int
        and type(vendor.get("scanner_vendor_conflict_count")) is int
        and vendor
        == {
            "checked_on_local_date": "2026-08-05",
            "authoritative_source": "Ubuntu Security CVE records",
            "vendor_vulnerable_or_deferred_count": vendor_open_count,
            "vendor_marks_exact_scanned_version_fixed_count": vendor_fixed_count,
            "scanner_vendor_conflict_count": scanner_vendor_conflict_count,
            "assessments": expected_assessments,
            "security_decision": (
                "OPEN_SECURITY / SIX VENDOR-CONFIRMED VULNERABLE OR DEFERRED / "
                "ONE SCANNER-VENDOR CONFLICT"
            ),
        },
        "vendor triage hides the open findings or scanner/vendor conflict",
    )
    require(
        receipt.get("retention_status")
        == {
            "raw_build_history_retained": True,
            "raw_original_oci_descriptors_retained": True,
            "raw_original_buildkit_spdx_retained": True,
            "raw_original_buildkit_slsa_retained": True,
            "raw_current_direct_sbom_retained": True,
            "raw_current_direct_cve_report_retained": True,
            "raw_payloads_repository_replayable": True,
            "original_scout_1_24_cve_report_retained": False,
            "current_scout_process_stdout_stderr_retained": False,
            "scanner_database_identity_retained": False,
            "vendor_source_payloads_retained": False,
            "trusted_time_established": False,
            "independent_reproduction_completed": False,
            "independent_attestation_trust_root_established": False,
            "complete_tool_execution_replayable": False,
        },
        "raw retention status is incomplete or overstates replay/trust",
    )
    unresolved = receipt.get("unresolved_boundaries")
    require(
        unresolved
        == {
            "direct_local_image_security_findings": (
                "OPEN / 7 SCANNER FINDINGS / 6 VENDOR-CONFIRMED VULNERABLE OR "
                "DEFERRED / 1 VENDOR-SCANNER CONFLICT"
            ),
            "original_scout_1_24_cve_report": "NOT RETAINED",
            "current_scout_process_transcripts": "NOT RETAINED",
            "sarif_to_candidate_execution_binding": (
                "OPEN / NOT EMBEDDED / INVOCATION NOT RETAINED"
            ),
            "vendor_triage_source_snapshot": "NOT RETAINED / LINKS ONLY",
            "scanner_database_identity": "OPEN",
            "networkless_scan_execution": "NOT CERTIFIED",
            "independent_clean_reproduction": "OPEN",
            "independent_attestation_trust_root": "OPEN",
            "trusted_time_and_worm_retention": "OPEN",
            "gpu_real_forward": "NOT_STARTED",
            "gate5_engineering_003": "OPEN_SECURITY",
            "licensing": "NOT LICENSED",
            "public_disclosure": "HELD",
        },
        "raw evidence receipt removed an OPEN security/governance boundary",
    )
    require(
        receipt.get("claim_boundary")
        == {
            "integrity_evidence_effect": "RAW LOCAL PAYLOAD RETENTION AND STRUCTURAL CROSS-LINK VERIFICATION ONLY",
            "external_evidence_effect": "LOCAL SELF-OBSERVED / NOT INDEPENDENTLY ATTESTED",
            "security_effect": "OPEN_SECURITY",
            "scientific_effect": "NONE",
            "canon_effect": "NONE",
            "product_claim_effect": "NONE",
            "license_effect": "NONE",
            "disclosure_effect": "NONE",
        },
        "raw evidence receipt claims unauthorized authority",
    )
    return {
        "retained_files": len(records),
        "original_spdx_packages": len(spdx_predicate["packages"]),
        "direct_spdx_packages": len(direct_spdx["packages"]),
        "scanner_findings": len(results),
        "vendor_confirmed_open": vendor["vendor_vulnerable_or_deferred_count"],
        "vendor_scanner_conflicts": vendor["scanner_vendor_conflict_count"],
    }


def verify_python_syntax(manifest_artifacts: dict[str, dict[str, Any]]) -> int:
    python_paths = sorted(path for path in manifest_artifacts if path.endswith(".py"))
    for raw_path in python_paths:
        path = ROOT / Path(*PurePosixPath(raw_path).parts)
        try:
            # Parse exact bytes so Python's own PEP 263 encoding detection accepts
            # valid UTF-8 BOM and encoding-cookie sources without normalizing them.
            ast.parse(
                read_stable_bytes(path, anchor=FILESYSTEM_ANCHOR),
                filename=raw_path,
            )
        except (OSError, SyntaxError) as exc:
            raise VerificationError(f"cannot parse bound Python artifact {raw_path}: {exc}") from exc
    return len(python_paths)


def _subprocess_environment(
    *, extra_env: dict[str, str] | None = None, remove_env: Iterable[str] = ()
) -> dict[str, str]:
    env = {
        name: value
        for name, value in os.environ.items()
        if name.upper() in SUBPROCESS_ENV_ALLOWLIST
    }
    for name in remove_env:
        env.pop(name, None)
    env.update(
        {
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": "0",
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "TOKENIZERS_PARALLELISM": "false",
            "NO_COLOR": "1",
            # Gate 0 reads historical blobs with Git.  Codex's isolated child
            # may run under a sandbox SID distinct from the worktree owner, so
            # admit only this exact repository without trusting caller-supplied
            # Git configuration or changing the user's global config.
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "safe.directory",
            "GIT_CONFIG_VALUE_0": GIT_SAFE_DIRECTORY,
        }
    )
    if extra_env:
        env.update(extra_env)
    return env


def run_command(
    command: list[str],
    *,
    cwd: Path,
    timeout: int,
    extra_env: dict[str, str] | None = None,
    remove_env: Iterable[str] = (),
) -> tuple[str, str]:
    env = _subprocess_environment(extra_env=extra_env, remove_env=remove_env)
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
        timeout=timeout,
    )
    if completed.returncode != 0:
        raise VerificationError(
            f"command failed ({completed.returncode}) in {cwd}: {' '.join(command)}\n"
            f"{completed.stdout}{completed.stderr}"
        )
    return completed.stdout, completed.stderr


def test_id_digest(test_ids: Iterable[str]) -> str:
    values = list(test_ids)
    require(values, "same-run pytest receipt has no test IDs")
    require(
        all(
            isinstance(test_id, str)
            and test_id
            and "\\" not in test_id
            and not any(marker in test_id for marker in ("\x00", "\r", "\n"))
            for test_id in values
        ),
        "same-run pytest receipt has a noncanonical test ID",
    )
    require(
        len(values) == len(set(values)),
        "same-run pytest receipt contains duplicate test IDs",
    )
    ids = sorted(values)
    return sha256_bytes(("\n".join(ids) + "\n").encode("utf-8"))


def _load_runner_lock_builder() -> Any:
    spec = importlib.util.spec_from_file_location(
        "gate5_runner_lock_builder", RUNNER_LOCK_BUILDER_PATH
    )
    require(spec is not None and spec.loader is not None, "cannot load runner-lock builder")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_local_test_runner_lock() -> dict[str, Any]:
    lock = load_json(RUNNER_LOCK_PATH)
    require(isinstance(lock, dict), "local test-runner lock is not an object")
    require_exact_keys(
        lock,
        {
            "schema_version",
            "document_status",
            "gate5_status",
            "gate_decision",
            "experimental_execution_status",
            "admission_ring",
            "license_status",
            "disclosure_status",
            "public_disclosure_authorized",
            "canon_effect",
            "product_claim_effect",
            "lock_scope",
            "required_child_invocation",
            "python_identity",
            "admitted_pytest_site_root",
            "pytest_version",
            "admitted_runner_distributions",
            "startup_pth_inventory",
            "startup_pth_execution",
            "unbound_runtime_surface",
            "claim_boundary",
        },
        label="Gate 5 local test-runner lock",
    )
    require(
        lock.get("schema_version")
        == "project_coherence.gate5_local_test_runner_lock.v0.1",
        "unexpected local test-runner lock schema",
    )
    verify_governance_header(lock, label="Gate 5 local test-runner lock")
    require(
        lock.get("lock_scope")
        == "LOCAL_CONTENT_LOCK / SELF-OBSERVED / NOT HERMETIC / NOT INDEPENDENTLY ATTESTED"
        and lock.get("required_child_invocation")
        == "python -I -S -B -X pycache_prefix=<fresh-empty-directory>",
        "local test-runner lock overstates its scope or changes invocation",
    )
    require(
        lock.get("unbound_runtime_surface")
        == {
            "stdlib_content": "OPEN",
            "test_import_dependencies_outside_admitted_runner_distributions": "OPEN",
            "distribution_files_absent_from_upstream_record": "OPEN",
            "transient_unloaded_or_dynamic_module_execution": "OPEN",
            "exact_loader_executed_bytecode": "OPEN",
            "unresolved_or_deleted_module_origins": "OPEN",
            "native_dependency_closure": "OPEN",
            "child_process_closure": "OPEN",
            "kernel_and_filesystem_trust": "OPEN",
            "independent_signer_or_trust_root": "OPEN",
        },
        "local test-runner lock hides an unbound execution surface",
    )
    require(
        lock.get("claim_boundary")
        == {
            "same_run_receipt_effect": "LOCAL ENGINEERING REGRESSION ONLY",
            "hermeticity_effect": "NONE",
            "scientific_effect": "NONE",
            "canon_effect": "NONE",
            "product_claim_effect": "NONE",
            "license_effect": "NONE",
            "disclosure_effect": "NONE",
        },
        "local test-runner lock claims unauthorized effect",
    )
    builder = _load_runner_lock_builder()
    expected = builder.build_lock(Path(lock["admitted_pytest_site_root"]))
    require(
        lock == expected,
        "local interpreter, pytest distributions, or disabled .pth inventory drifted",
    )
    interpreter = Path(lock["python_identity"]["interpreter_files"][0]["path"])
    require(
        Path(sys.executable).resolve() == interpreter.resolve(),
        "authoritative verifier is not using the locked local interpreter",
    )
    return lock


def _canonical_json_digest(value: Any) -> str:
    return sha256_bytes(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
    )


def _allowed_loaded_module_anchor(path: Path, lock: dict[str, Any]) -> Path:
    allowed_roots = [
        ROOT.resolve(),
        Path(lock["admitted_pytest_site_root"]).resolve(),
        Path(lock["python_identity"]["stdlib_root"]).resolve().parent,
    ]
    resolved = path.resolve(strict=True)
    for allowed in allowed_roots:
        try:
            resolved.relative_to(allowed)
            return Path(resolved.anchor)
        except ValueError:
            continue
    raise VerificationError(f"pytest loaded code outside the declared local surface: {resolved}")


def _expected_runner_sys_paths(
    lock: dict[str, Any], *, working_directory: Path, repo_import_roots: list[Path]
) -> tuple[list[str], list[str]]:
    python_identity = lock["python_identity"]
    interpreter = Path(python_identity["interpreter_files"][0]["path"])
    python_root = interpreter.parent.resolve(strict=True)
    version_parts = python_identity["version"].split(".")
    require(
        len(version_parts) >= 2
        and all(part.isdecimal() for part in version_parts[:2]),
        "runner-lock Python version is malformed",
    )
    absent_stdlib_zip = python_root / (
        f"python{version_parts[0]}{version_parts[1]}.zip"
    )
    require(
        not absent_stdlib_zip.exists() and not absent_stdlib_zip.is_symlink(),
        "unbound standard-library zip appeared on the runner sys.path",
    )
    startup = [
        str(absent_stdlib_zip),
        str((python_root / "DLLs").resolve(strict=True)),
        str(Path(python_identity["stdlib_root"]).resolve(strict=True)),
        str(python_root),
    ]
    site_root = str(Path(lock["admitted_pytest_site_root"]).resolve(strict=True))
    return startup, [
        str(working_directory.resolve(strict=True)),
        *(str(path.resolve(strict=True)) for path in repo_import_roots),
        *startup,
        site_root,
    ]


def _validate_loaded_module_records(
    *,
    name: str,
    records: Any,
    lock: dict[str, Any],
    admitted_artifact_paths: set[str],
    pre_test: bool,
) -> list[dict[str, Any]]:
    require(isinstance(records, list) and records, f"{name}: loaded-code inventory is missing")
    loaded_paths: set[str] = set()
    root = ROOT.resolve()
    site_root = Path(lock["admitted_pytest_site_root"]).resolve(strict=True)
    admitted_site_files: dict[str, dict[str, Any]] = {}
    admitted_site_namespaces: set[str] = set()
    admitted_distributions: set[str] = set()
    for distribution_index, distribution in enumerate(
        lock["admitted_runner_distributions"]
    ):
        require(
            isinstance(distribution, dict),
            f"{name}: locked runner distribution {distribution_index} is malformed",
        )
        require_exact_keys(
            distribution,
            {
                "distribution",
                "canonical_distribution",
                "version",
                "file_count",
                "byte_count",
                "tree_sha256",
                "files",
                "excluded_outside_site_files",
                "tree_digest_rule",
            },
            label=f"{name} locked runner distribution {distribution_index}",
        )
        files = distribution["files"]
        canonical_distribution = distribution["canonical_distribution"]
        require(
            isinstance(files, list)
            and isinstance(canonical_distribution, str)
            and isinstance(distribution["distribution"], str)
            and canonical_distribution
            and canonical_distribution
            == re.sub(r"[-_.]+", "-", distribution["distribution"]).casefold()
            and canonical_distribution not in admitted_distributions
            and type(distribution["file_count"]) is int
            and distribution["file_count"] == len(files),
            f"{name}: locked runner distribution file inventory is malformed",
        )
        admitted_distributions.add(canonical_distribution)
        excluded_files = distribution["excluded_outside_site_files"]
        require(
            isinstance(excluded_files, list),
            f"{name}: excluded runner entry-point inventory is malformed",
        )
        for excluded_index, excluded_file in enumerate(excluded_files):
            require(
                isinstance(excluded_file, dict),
                f"{name}: excluded runner entry point is malformed",
            )
            require_exact_keys(
                excluded_file,
                {"record_path", "path", "reason"},
                label=(
                    f"{name} excluded runner entry point "
                    f"{distribution_index}:{excluded_index}"
                ),
            )
            require(
                excluded_file["reason"]
                == "SIBLING_SCRIPTS_ENTRY_POINT / NOT EXECUTED",
                f"{name}: excluded runner entry point changed scope",
            )
        for file_index, locked_file in enumerate(files):
            require(
                isinstance(locked_file, dict),
                f"{name}: locked runner file {distribution_index}:{file_index} is malformed",
            )
            require_exact_keys(
                locked_file,
                {"path", "bytes", "sha256", "owner_distribution"},
                label=f"{name} locked runner file {distribution_index}:{file_index}",
            )
            raw_path = locked_file["path"]
            require(
                isinstance(raw_path, str)
                and raw_path
                and "\\" not in raw_path
                and not PurePosixPath(raw_path).is_absolute()
                and all(
                    part not in {"", ".", ".."}
                    for part in PurePosixPath(raw_path).parts
                )
                and locked_file["owner_distribution"] == canonical_distribution
                and type(locked_file["bytes"]) is int
                and locked_file["bytes"] >= 0
                and isinstance(locked_file["sha256"], str)
                and re.fullmatch(r"[0-9A-F]{64}", locked_file["sha256"]) is not None,
                f"{name}: locked runner file path is noncanonical",
            )
            locked_path = site_root.joinpath(*PurePosixPath(raw_path).parts).resolve(
                strict=True
            )
            try:
                locked_path.relative_to(site_root)
            except ValueError as exc:
                raise VerificationError(
                    f"{name}: locked runner file escaped the admitted site root"
                ) from exc
            folded_locked_path = str(locked_path).casefold()
            require(
                folded_locked_path not in admitted_site_files,
                f"{name}: duplicate file across locked runner distributions",
            )
            admitted_site_files[folded_locked_path] = locked_file
            first_part = PurePosixPath(raw_path).parts[0].casefold()
            if not first_part.endswith(".dist-info"):
                admitted_site_namespaces.add(first_part)
    for index, record in enumerate(records):
        require(isinstance(record, dict), f"{name}: loaded-code record {index} is malformed")
        require_exact_keys(
            record,
            {"path", "bytes", "sha256", "module_names", "kind"},
            label=f"{name} loaded-code record {index}",
        )
        path = Path(record["path"])
        anchor = _allowed_loaded_module_anchor(path, lock)
        observation = observe_regular_file(path, anchor=anchor)
        require(
            type(record.get("bytes")) is int
            and record["bytes"] == observation.byte_count
            and record.get("sha256") == observation.sha256
            and isinstance(record.get("module_names"), list)
            and record["module_names"]
            and all(isinstance(module, str) and module for module in record["module_names"])
            and record.get("kind") in {"PYTHON_OR_DATA", "NATIVE"},
            f"{name}: loaded-code identity drifted after the child exited",
        )
        resolved = path.resolve(strict=True)
        folded = str(resolved).casefold()
        require(folded not in loaded_paths, f"{name}: duplicate loaded-code path")
        loaded_paths.add(folded)
        try:
            repo_relative = resolved.relative_to(root).as_posix()
        except ValueError:
            repo_relative = None
        if repo_relative is not None:
            require(
                (
                    repo_relative
                    == SAME_RUN_PYTEST_RUNNER_PATH.relative_to(ROOT).as_posix()
                    if pre_test
                    else repo_relative in admitted_artifact_paths
                ),
                f"{name}: pytest loaded an unbound repository file: {repo_relative}",
            )
        try:
            site_relative = resolved.relative_to(site_root)
        except ValueError:
            site_relative = None
        if site_relative is not None:
            locked_file = admitted_site_files.get(folded)
            if pre_test:
                require(
                    locked_file is not None
                    and locked_file["bytes"] == observation.byte_count
                    and locked_file["sha256"] == observation.sha256,
                    f"{name}: pytest startup loaded an unbound runner file: {resolved}",
                )
            elif locked_file is None:
                require(
                    site_relative.parts[0].casefold()
                    not in admitted_site_namespaces,
                    f"{name}: unbound test dependency masqueraded inside a locked "
                    f"runner namespace: {resolved}",
                )
    return records


def run_pytest_same_process_receipt(
    *,
    name: str,
    suite: dict[str, Any],
    lock: dict[str, Any],
    admitted_artifact_paths: set[str],
) -> dict[str, Any]:
    cwd = (
        ROOT
        if suite["working_directory"] == "."
        else ROOT
        / canonical_repo_path(
            suite["working_directory"], label=f"{name} working directory"
        )
    )
    require(cwd.is_dir(), f"{name}: working directory is missing")
    targets = suite["targets"]
    plugins = suite["pytest_plugins"]
    raw_repo_import_roots = suite["repo_import_roots"]
    require(
        isinstance(targets, list)
        and targets
        and all(isinstance(target, str) and target for target in targets),
        f"{name}: targets are malformed",
    )
    require(
        isinstance(plugins, list)
        and all(isinstance(plugin, str) and plugin for plugin in plugins),
        f"{name}: explicit pytest plugin list is malformed",
    )
    require(
        isinstance(raw_repo_import_roots, list)
        and len(raw_repo_import_roots) == len(set(raw_repo_import_roots))
        and all(isinstance(path, str) and path for path in raw_repo_import_roots),
        f"{name}: repository import-root list is malformed",
    )
    repo_import_roots = [
        ROOT / canonical_repo_path(path, label=f"{name} repository import root")
        for path in raw_repo_import_roots
    ]
    require(
        all(path.is_dir() for path in repo_import_roots),
        f"{name}: a repository import root is missing or not a directory",
    )
    lock_sha256 = sha256_file(RUNNER_LOCK_PATH)
    nonce = secrets.token_hex(32)
    interpreter = lock["python_identity"]["interpreter_files"][0]["path"]
    with tempfile.TemporaryDirectory(prefix="gate5-same-run-pytest-") as raw_temp:
        temporary = Path(raw_temp)
        receipt_path = temporary / "receipt.json"
        pycache_prefix = temporary / "fresh-pycache"
        pycache_prefix.mkdir()
        command = [
            interpreter,
            "-I",
            "-S",
            "-B",
            "-X",
            f"pycache_prefix={pycache_prefix}",
            str(SAME_RUN_PYTEST_RUNNER_PATH),
            "--receipt",
            str(receipt_path),
            "--lock",
            str(RUNNER_LOCK_PATH),
            "--expected-lock-sha256",
            lock_sha256,
            "--suite-name",
            name,
            "--nonce",
            nonce,
            "--expected-parent-pid",
            str(os.getpid()),
            "--working-directory",
            str(cwd.resolve()),
            "--pycache-prefix",
            str(pycache_prefix),
        ]
        for target in targets:
            command.extend(("--target", target))
        for plugin in plugins:
            command.extend(("--plugin", plugin))
        for import_root in repo_import_roots:
            command.extend(("--repo-import-root", str(import_root.resolve())))
        try:
            completed = subprocess.run(
                command,
                cwd=ROOT,
                env=_subprocess_environment(
                    extra_env=PYTEST_ISOLATION_ENV,
                    remove_env=PYTEST_REMOVED_ENV,
                ),
                capture_output=True,
                check=False,
                timeout=600,
            )
        except subprocess.TimeoutExpired as exc:
            raise VerificationError(f"{name}: same-run pytest process timed out") from exc
        require(
            receipt_path.is_file(),
            f"{name}: same-run pytest receipt is missing "
            f"(process={completed.returncode}, "
            f"stdout={completed.stdout.decode('utf-8', errors='replace')!r}, "
            f"stderr={completed.stderr.decode('utf-8', errors='replace')!r})",
        )
        receipt = load_json(receipt_path, anchor=temporary)
        require(isinstance(receipt, dict), f"{name}: same-run pytest receipt is malformed")
        require_exact_keys(
            receipt,
            {
                "schema_version",
                "suite_name",
                "nonce",
                "pid",
                "parent_pid",
                "working_directory",
                "targets",
                "explicit_pytest_plugins",
                "admitted_repo_import_roots",
                "pytest_version",
                "pytest_exit_status",
                "runner_lock_sha256",
                "python_flags",
                "startup_sys_path",
                "locked_import_origin_files",
                "pre_test_loaded_module_files",
                "final_sys_path",
                "pytest_rootdir",
                "pytest_inifile",
                "plugin_inventory",
                "collected_nodeids",
                "started_nodeids",
                "finished_nodeids",
                "ordinary_reports",
                "subtest_reports",
                "collection_errors",
                "internal_errors",
                "deselected_nodeids",
                "warning_count",
                "captured_stdout_sha256",
                "captured_stderr_sha256",
                "loaded_module_files",
                "pycache_prefix_empty_after_run",
            },
            label=f"{name} same-run pytest receipt",
        )
        require(
            receipt.get("schema_version")
            == "project_coherence.gate5_same_run_pytest_receipt.v0.1"
            and receipt.get("suite_name") == name
            and receipt.get("nonce") == nonce
            and type(receipt.get("pid")) is int
            and receipt["pid"] != os.getpid()
            and receipt.get("parent_pid") == os.getpid()
            and receipt.get("working_directory") == str(cwd.resolve())
            and receipt.get("targets") == targets
            and receipt.get("explicit_pytest_plugins") == plugins
            and receipt.get("admitted_repo_import_roots")
            == [str(path.resolve()) for path in repo_import_roots]
            and receipt.get("pytest_version") == lock["pytest_version"]
            and receipt.get("runner_lock_sha256") == lock_sha256,
            f"{name}: receipt identity differs from the launched process",
        )
        require(
            receipt.get("python_flags")
            == {
                "isolated": 1,
                "no_site": 1,
                "no_user_site": 1,
                "safe_path": True,
                "ignore_environment": 1,
                "dont_write_bytecode": 1,
            },
            f"{name}: child Python startup was not -I -S -B",
        )
        require(
            completed.returncode == 0
            and receipt.get("pytest_exit_status") == 0,
            f"{name}: same-run pytest failed (process={completed.returncode}, "
            f"pytest={receipt.get('pytest_exit_status')}, "
            f"stdout={completed.stdout.decode('utf-8', errors='replace')!r}, "
            f"stderr={completed.stderr.decode('utf-8', errors='replace')!r})",
        )
        require(
            completed.stdout == b"" and completed.stderr == b"",
            f"{name}: runner emitted unreceipted process output",
        )
        require(
            receipt.get("pycache_prefix_empty_after_run") is True
            and not any(pycache_prefix.iterdir()),
            f"{name}: fresh bytecode cache prefix was populated",
        )
        collected = receipt.get("collected_nodeids")
        started = receipt.get("started_nodeids")
        finished = receipt.get("finished_nodeids")
        require(
            isinstance(collected, list)
            and collected == started == finished,
            f"{name}: collection/start/finish node-ID sequences differ",
        )
        require(
            len(collected) == suite["expected_tests"],
            f"{name}: executed {len(collected)} tests, expected {suite['expected_tests']}",
        )
        executed_digest = test_id_digest(collected)
        require(
            executed_digest == suite["expected_test_ids_sha256"],
            f"{name}: same-run executed pytest node-ID set drifted",
        )
        require(
            receipt.get("collection_errors") == []
            and receipt.get("internal_errors") == []
            and receipt.get("deselected_nodeids") == [],
            f"{name}: collection, internal, or deselection events occurred",
        )
        ordinary = receipt.get("ordinary_reports")
        require(isinstance(ordinary, list), f"{name}: ordinary outcome ledger is missing")
        phases: dict[str, list[dict[str, Any]]] = {nodeid: [] for nodeid in collected}
        for index, report in enumerate(ordinary):
            require(isinstance(report, dict), f"{name}: ordinary report {index} is malformed")
            require_exact_keys(
                report,
                {"nodeid", "when", "outcome", "wasxfail"},
                label=f"{name} ordinary report {index}",
            )
            require(report.get("nodeid") in phases, f"{name}: report names an unexecuted test")
            phases[report["nodeid"]].append(report)
        for nodeid in collected:
            reports = phases[nodeid]
            require(
                [report["when"] for report in reports] == ["setup", "call", "teardown"]
                and all(report["outcome"] == "passed" for report in reports)
                and all(report["wasxfail"] is False for report in reports),
                f"{name}: {nodeid} lacks an exact setup/call/teardown all-pass outcome",
            )
        subtests = receipt.get("subtest_reports")
        require(isinstance(subtests, list), f"{name}: subtest outcome ledger is missing")
        require(
            len(subtests) == suite["expected_subtests"],
            f"{name}: observed {len(subtests)} subtests, expected {suite['expected_subtests']}",
        )
        for index, report in enumerate(subtests):
            require(isinstance(report, dict), f"{name}: subtest report {index} is malformed")
            require_exact_keys(
                report,
                {"nodeid", "when", "outcome", "wasxfail", "context"},
                label=f"{name} subtest report {index}",
            )
            require(
                report.get("nodeid") in phases
                and report.get("when") == "call"
                and report.get("outcome") == "passed"
                and report.get("wasxfail") is False,
                f"{name}: a subtest was not an exact same-run PASS",
            )
        rootdir = receipt.get("pytest_rootdir")
        require(isinstance(rootdir, str), f"{name}: pytest rootdir is missing")
        try:
            Path(rootdir).resolve().relative_to(ROOT.resolve())
        except ValueError as exc:
            raise VerificationError(f"{name}: pytest rootdir escaped the repository") from exc
        inifile = receipt.get("pytest_inifile")
        if inifile is not None:
            require(isinstance(inifile, str), f"{name}: pytest inifile is malformed")
            try:
                Path(inifile).resolve().relative_to(ROOT.resolve())
            except ValueError as exc:
                raise VerificationError(f"{name}: pytest inifile escaped the repository") from exc
        inventory = receipt.get("plugin_inventory")
        require(isinstance(inventory, list) and inventory, f"{name}: plugin inventory is missing")
        for index, plugin_record in enumerate(inventory):
            require(isinstance(plugin_record, dict), f"{name}: plugin record {index} is malformed")
            require_exact_keys(
                plugin_record,
                {"name", "implementation"},
                label=f"{name} plugin record {index}",
            )
        require(
            any(
                record["implementation"] == "__main__.SameRunReceiptPlugin"
                for record in inventory
            ),
            f"{name}: same-run receipt plugin was not registered",
        )
        for explicit_plugin in plugins:
            require(
                any(record["implementation"] == explicit_plugin for record in inventory),
                f"{name}: explicit plugin {explicit_plugin!r} was not registered",
            )
        expected_startup_sys_path, expected_final_sys_path = _expected_runner_sys_paths(
            lock,
            working_directory=cwd,
            repo_import_roots=repo_import_roots,
        )
        require(
            receipt.get("startup_sys_path") == expected_startup_sys_path
            and receipt.get("final_sys_path") == expected_final_sys_path,
            f"{name}: runner sys.path differs from the exact -I -S admission surface",
        )
        locked_import_origin_files = _validate_loaded_module_records(
            name=f"{name} locked import origin",
            records=receipt.get("locked_import_origin_files"),
            lock=lock,
            admitted_artifact_paths=admitted_artifact_paths,
            pre_test=True,
        )
        expected_origin_modules = ["pytest"]
        for explicit_plugin in plugins:
            top_level = explicit_plugin.split(".", 1)[0]
            if top_level not in expected_origin_modules:
                expected_origin_modules.append(top_level)
            if explicit_plugin not in expected_origin_modules:
                expected_origin_modules.append(explicit_plugin)
        require(
            [record["module_names"] for record in locked_import_origin_files]
            == [[module] for module in expected_origin_modules],
            f"{name}: pytest/plugin import-origin preflight differs from the locked modules",
        )
        pre_test_loaded_files = _validate_loaded_module_records(
            name=f"{name} pre-test",
            records=receipt.get("pre_test_loaded_module_files"),
            lock=lock,
            admitted_artifact_paths=admitted_artifact_paths,
            pre_test=True,
        )
        loaded_files = _validate_loaded_module_records(
            name=name,
            records=receipt.get("loaded_module_files"),
            lock=lock,
            admitted_artifact_paths=admitted_artifact_paths,
            pre_test=False,
        )
        for field in ("captured_stdout_sha256", "captured_stderr_sha256"):
            require(
                isinstance(receipt.get(field), str)
                and SHA256_UPPER_RE.fullmatch(receipt[field]),
                f"{name}: captured transcript digest is malformed",
            )
        require(
            type(receipt.get("warning_count")) is int and receipt["warning_count"] >= 0,
            f"{name}: warning count is malformed",
        )
        return {
            "name": name,
            "tests": len(collected),
            "subtests": len(subtests),
            "executed_node_ids_sha256": executed_digest,
            "ordinary_outcomes_sha256": _canonical_json_digest(ordinary),
            "subtest_outcomes_sha256": _canonical_json_digest(subtests),
            "locked_import_origins_sha256": _canonical_json_digest(
                locked_import_origin_files
            ),
            "pre_test_loaded_code_sha256": _canonical_json_digest(
                pre_test_loaded_files
            ),
            "loaded_code_sha256": _canonical_json_digest(loaded_files),
            "warnings": receipt["warning_count"],
            "collected_nodeids": collected,
            "subtest_reports": subtests,
        }


def verify_test_suites(
    manifest: dict[str, Any], lock: dict[str, Any]
) -> list[dict[str, Any]]:
    suites = manifest.get("test_suites")
    require(isinstance(suites, list), "manifest test_suites is not a list")
    by_name = {
        suite.get("name"): suite
        for suite in suites
        if isinstance(suite, dict) and isinstance(suite.get("name"), str)
    }
    admitted_artifact_paths = {
        record["path"]
        for record in manifest.get("artifacts", [])
        if isinstance(record, dict) and isinstance(record.get("path"), str)
    }
    results: list[dict[str, Any]] = []
    for name, required in REQUIRED_TEST_SUITES.items():
        require(
            isinstance(required["expected_tests"], int)
            and isinstance(required["expected_test_ids_sha256"], str),
            f"{name}: verifier receipt is PENDING_NUMERIC_GREEN_FREEZE",
        )
        suite = by_name.get(name)
        require(isinstance(suite, dict), f"missing test suite {name!r}")
        for field in (
            "working_directory",
            "targets",
            "pytest_plugins",
            "repo_import_roots",
            "expected_tests",
            "expected_subtests",
            "expected_test_ids_sha256",
        ):
            require(
                suite.get(field) == required[field],
                f"{name}: manifest field {field!r} drifted",
            )
        require(
            suite.get("test_id_canonicalization") == TEST_ID_CANONICALIZATION,
            f"{name}: test-ID canonicalization drifted",
        )
        require(
            type(suite["expected_tests"]) is int
            and type(suite["expected_subtests"]) is int,
            f"{name}: expected test counts must be exact integers",
        )
        results.append(
            run_pytest_same_process_receipt(
                name=name,
                suite=suite,
                lock=lock,
                admitted_artifact_paths=admitted_artifact_paths,
            )
        )

    harness_result = next(
        result
        for result in results
        if result["name"] == "Harness v2 kernel and history"
    )
    harness_ids = harness_result["collected_nodeids"]
    for name, receipt in REQUIRED_SUBSUITE_DIGESTS.items():
        target_paths = set(receipt["targets"])
        ids = [
            nodeid
            for nodeid in harness_ids
            if nodeid.split("::", 1)[0] in target_paths
        ]
        require(
            len(ids) == receipt["expected_tests"],
            f"{name}: same-run executed subset count drifted",
        )
        require(
            test_id_digest(ids) == receipt["expected_test_ids_sha256"],
            f"{name}: exact same-run executed pytest node-ID subset drifted",
        )
        if "expected_subtests" in receipt:
            expected_subtests = receipt["expected_subtests"]
            require(
                type(expected_subtests) is int and expected_subtests >= 0,
                f"{name}: expected subtest count is not an exact integer",
            )
            subtests = [
                report
                for report in harness_result["subtest_reports"]
                if report["nodeid"].split("::", 1)[0] in target_paths
            ]
            require(
                len(subtests) == expected_subtests,
                f"{name}: same-run executed subset subtest count drifted",
            )
    return results


def capture_integrated_file_observations(
    manifest_artifacts: dict[str, dict[str, Any]],
) -> dict[str, FileObservation]:
    paths = set(manifest_artifacts)
    gate4 = load_json(GATE4_MANIFEST_PATH)
    history = load_json(HISTORY_MANIFEST_PATH)
    require(
        isinstance(gate4, dict)
        and isinstance(gate4.get("artifacts"), list)
        and isinstance(history, dict)
        and isinstance(history.get("files"), list),
        "cannot assemble integrated identity-observation surface",
    )
    for index, record in enumerate(gate4["artifacts"]):
        require(isinstance(record, dict), f"Gate 4 identity record {index} is malformed")
        paths.add(canonical_repo_path(record.get("path"), label=f"Gate 4 identity {index}"))
    for index, record in enumerate(history["files"]):
        require(isinstance(record, dict), f"history identity record {index} is malformed")
        paths.add(canonical_repo_path(record.get("path"), label=f"history identity {index}"))
    observations: dict[str, FileObservation] = {}
    for raw_path in sorted(paths):
        observations[raw_path] = observe_regular_file(
            ROOT / Path(*PurePosixPath(raw_path).parts), anchor=FILESYSTEM_ANCHOR
        )
    return observations


def verify_integrated_file_observations_unchanged(
    before: dict[str, FileObservation],
) -> None:
    after = {
        raw_path: observe_regular_file(
            ROOT / Path(*PurePosixPath(raw_path).parts), anchor=FILESYSTEM_ANCHOR
        )
        for raw_path in sorted(before)
    }
    require(
        after == before,
        "Gate 5/Gate 4/history file or ancestor identity changed during child execution",
    )


def main() -> int:
    require(MANIFEST_PATH.is_file(), "Gate 5 manifest is missing")
    require(not MANIFEST_PATH.is_symlink(), "Gate 5 manifest may not be a symlink")
    shadow_surface_count = verify_no_executable_shadow_artifacts()
    manifest_observation = observe_regular_file(
        MANIFEST_PATH, anchor=FILESYSTEM_ANCHOR
    )
    initial_manifest_file_sha = manifest_observation.sha256
    manifest = load_json(MANIFEST_PATH)
    require(isinstance(manifest, dict), "Gate 5 manifest root is not an object")
    artifacts = verify_manifest(manifest)
    gate4_artifact_count, gate4_manifest_sha = verify_gate4_dependency(artifacts)
    claim_count = verify_claim_ledger()
    history_count, history_bytes, history_digest = verify_history()
    verify_engineering_execution_reconciliation(artifacts)
    verify_historical_capability_reconciliation(artifacts)
    criterion_count, open_count = verify_review_matrix(artifacts)
    verify_adversarial_review()
    verify_no_status_promotion_text(artifacts)
    verify_model_and_security_bindings()
    verify_dependency_and_container_candidate_receipt()
    raw_evidence_result = verify_raw_build_and_security_evidence_receipt()
    python_count = verify_python_syntax(artifacts)
    runner_lock = verify_local_test_runner_lock()
    integrated_observations = capture_integrated_file_observations(artifacts)
    suite_results = verify_test_suites(manifest, runner_lock)
    require(
        verify_local_test_runner_lock() == runner_lock,
        "local test-runner lock or external runner packages changed during tests",
    )
    verify_integrated_file_observations_unchanged(integrated_observations)
    post_shadow_surface_count = verify_no_executable_shadow_artifacts()
    require(
        post_shadow_surface_count == shadow_surface_count,
        "admitted repository path count changed during executable-shadow postflight",
    )

    # Subprocesses execute bound tests and conftests.  Re-read and rehash the
    # complete current tree before PASS so a test, hook, or concurrent writer
    # cannot leave the repository in a state different from the admitted one.
    post_manifest = load_json(MANIFEST_PATH)
    require(post_manifest == manifest, "Gate 5 manifest changed during verification")
    require(
        observe_regular_file(MANIFEST_PATH, anchor=FILESYSTEM_ANCHOR)
        == manifest_observation,
        "Gate 5 manifest file or ancestor identity changed during verification",
    )
    require(
        sha256_file(MANIFEST_PATH) == initial_manifest_file_sha,
        "Gate 5 manifest bytes changed during verification",
    )
    post_artifacts = verify_manifest(post_manifest)
    require(post_artifacts == artifacts, "Gate 5 artifact records changed during verification")
    require(
        verify_history() == (history_count, history_bytes, history_digest),
        "historical recovery changed during verification",
    )
    require(
        verify_gate4_artifact_bytes() == gate4_artifact_count,
        "Gate 4 artifact surface changed during Gate 5 verification",
    )

    print("Project Coherence integrated Gate 5 verification: PASS")
    print(f"  hash-bound Gate 5 artifacts: {len(artifacts)}")
    print(f"  syntax-checked bound Python artifacts: {python_count}")
    print(
        "  executable-shadow paths scanned before and after tests: "
        f"{shadow_surface_count}"
    )
    print(
        "  Gate 4 dependency: integrated PASS while still OPEN; "
        f"artifacts={gate4_artifact_count}; manifest_sha256={gate4_manifest_sha}"
    )
    print(
        f"  claim records: {claim_count} (all Ring 4 / NOT LICENSED; "
        "Gate 5 claims HELD)"
    )
    print(
        "  historical recovery: "
        f"{history_count} files; {history_bytes} bytes; inventory_sha256={history_digest}"
    )
    print(
        "  test suites: EPHEMERAL LOCAL SAME-RUN VALIDATION / NOT RETAINED / "
        "NO TRUSTED TIME OR WORM"
    )
    for result in suite_results:
        print(
            f"    {result['name']}: tests={result['tests']}; "
            f"subtests={result['subtests']}; "
            f"executed_nodes={result['executed_node_ids_sha256']}; "
            f"ordinary_outcomes={result['ordinary_outcomes_sha256']}; "
            f"subtest_outcomes={result['subtest_outcomes_sha256']}; "
            f"locked_import_origins={result['locked_import_origins_sha256']}; "
            f"pre_test_code={result['pre_test_loaded_code_sha256']}; "
            f"loaded_code={result['loaded_code_sha256']}; "
            f"warnings={result['warnings']}"
        )
    print(
        "  raw build/security evidence: "
        f"files={raw_evidence_result['retained_files']}; "
        f"original_spdx_packages={raw_evidence_result['original_spdx_packages']}; "
        f"direct_spdx_packages={raw_evidence_result['direct_spdx_packages']}; "
        f"scanner_findings={raw_evidence_result['scanner_findings']}; "
        f"vendor_open={raw_evidence_result['vendor_confirmed_open']}; "
        f"scanner_vendor_conflicts={raw_evidence_result['vendor_scanner_conflicts']}"
    )
    print(f"  review criteria: {criterion_count}; required OPEN boundaries: {open_count}")
    print(
        "  postflight: Gate 5, historical, and transitive Gate 4 bytes plus "
        f"same-run file identities rechecked ({len(integrated_observations)} files)"
    )
    print(
        "  dependency security: OPEN_SECURITY / HELD (patched candidate "
        "digest-bound; original BuildKit/OCI/SPDX/SLSA and current direct Scout "
        "report bytes are repository-retained but remain local self-observations; "
        "pip-audit partial 72/73 with Torch skipped; direct image scan "
        "COMPLETED_WITH_FINDINGS: 0 critical / 0 high / 3 medium / 4 low; "
        "Ubuntu currently confirms six vulnerable/deferred records and marks the "
        "exact dpkg version fixed, leaving one scanner/vendor conflict)"
    )
    print("  experimental execution: NOT_STARTED")
    print("  Gate 5 status: OPEN / Ring 4 / NOT LICENSED / HELD / NOT FROZEN")
    print(
        "This PASS proves only exact identities, implemented repository checks, "
        "and preserved negative/open boundaries. It is not an authenticated "
        "experiment, causal or semantic validation, independent audit, replication, "
        "peer review, WORM receipt, claim license, product readiness, or disclosure approval."
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except VerificationError as exc:
        print(f"Project Coherence Gate 5 verification: FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
