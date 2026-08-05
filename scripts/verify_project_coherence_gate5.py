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
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
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

SHA256_UPPER_RE = re.compile(r"^[A-F0-9]{64}$")
SHA256_LOWER_RE = re.compile(r"^[a-f0-9]{64}$")
OCI_SHA256_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
WINDOWS_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:[/\\]")
BOUNDARY_RE = re.compile(r"^\[([A-Z0-9-]+)\] ")
TEST_ID_CANONICALIZATION = (
    "COLLECT-ONLY SHA-256 over sorted unique pytest node IDs normalized to POSIX "
    "slashes, encoded UTF-8 as one ID plus LF per line; actual executed-node-ID "
    "digest is NOT RECEIPTED"
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
    f"{API_ROOT_REL}/tests/test_state_ledger_operational_enable.py",
    f"{API_ROOT_REL}/tests/test_state_substrate_live_migration.py",
}
API_RUNTIME_SURFACE_DIR = f"{API_ROOT_REL}/api"

REQUIRED_CONTROL_ARTIFACTS = {
    ".gitattributes",
    "docs/working/project_coherence/CLAIM_LEDGER_v0.1.json",
    "docs/working/project_coherence/PROJECT_COHERENCE_MASTER_CHARTER_v0.1.md",
    "docs/working/project_coherence/OPEN_VS_HELD_BOUNDARY_v0.1.md",
    "docs/working/project_coherence/gate4/GATE4_ARTIFACT_MANIFEST_v0.1.json",
    "docs/working/project_coherence/gate5/README.md",
    "docs/working/project_coherence/gate5/HARNESS_V2_PREREGISTRATION_AND_EVIDENCE_PACKET_V2_SPEC_v0.1.md",
    "docs/working/project_coherence/gate5/GATE5_REVIEW_MATRIX_v0.1.json",
    "docs/working/project_coherence/gate5/GATE5_ADVERSARIAL_REVIEW_v0.1.md",
    "docs/working/project_coherence/gate5/GATE5_MODEL_AND_DEPENDENCY_BINDING_v0.1.json",
    "docs/working/project_coherence/gate5/GATE5_DEPENDENCY_AND_CONTAINER_CANDIDATE_RECEIPT_v0.2.json",
    "docs/working/project_coherence/gate5/history/HISTORICAL_HARNESS_V1_V4_CURRENT_TREE_SHA256.json",
    "docs/working/project_coherence/gate5/history/HISTORICAL_HARNESS_V1_V4_RECOVERY_INVENTORY.md",
    "scripts/verify_project_coherence_gate5.py",
    "scripts/build_project_coherence_gate5_manifest.py",
    f"{WORKER_ROOT_REL}/Dockerfile",
    f"{WORKER_ROOT_REL}/.dockerignore",
    f"{WORKER_ROOT_REL}/requirements.in",
    f"{WORKER_ROOT_REL}/requirements.txt",
    "noetic-compass-scaffold/noetic-compass/pyproject.toml",
}

# Every regular file under these admitted roots can affect the verified
# kernels or worker regressions and therefore must be hash-bound.  This is
# deliberately broader than ``*.py`` so a future resource, extension, archive,
# or configuration file cannot appear outside the manifest.
EXACT_ALL_FILE_SURFACE_DIRS = (
    "src/cas_harness_v2",
    "tests/cas_harness_v2",
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

REQUIRED_BOUNDARY_TEXT = {
    "G5-OPEN-GATE4": "Gate 4 remains OPEN and cannot be promoted by dependency verification.",
    "G5-OPEN-TRUSTED-TIME": "No independently trusted time source binds ordering.",
    "G5-OPEN-TRUST-ROOT": "No non-caller-selected identity or signing trust root exists.",
    "G5-OPEN-WORM": "No durable append-only or WORM authority binds the v2 chain.",
    "G5-OPEN-NONCE-REPLAY": "Authenticated nonce issuance and replay rejection are absent.",
    "G5-OPEN-ONE-USE": "Atomic one-use run authorization and consumption are absent.",
    "G5-OPEN-SELECTIVE-REPORTING": "No complete cross-run registry prevents selective reporting.",
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
        "expected_tests": 113,
        "expected_subtests": 61,
        "expected_test_ids_sha256": (
            "FD31E05BDFE62A44B4FC7D1556A2CA498115FF8E0A65C3F16160FA4D0C2FA294"
        ),
    },
    "Live trace worker complete": {
        "working_directory": WORKER_ROOT_REL,
        "targets": ["tests"],
        "pytest_plugins": ["pytest_asyncio.plugin"],
        "expected_tests": 364,
        "expected_subtests": 0,
        "expected_test_ids_sha256": (
            "94566203B3E0FF79B3224C1C5A073698CA99D3C08BC1119A9082E42AF4B178BD"
        ),
    },
    "Live trace worker numeric red team": {
        "working_directory": WORKER_ROOT_REL,
        "targets": ["tests/test_eraser_numeric_redteam.py"],
        "pytest_plugins": ["pytest_asyncio.plugin"],
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
        "expected_tests": 76,
        "expected_subtests": 0,
        "expected_test_ids_sha256": (
            "1ED1E9E3AFA2EDA6881463EE5284DD4902AB94C0246B80D2937066480AC42921"
        ),
    },
}

# These subset receipts make the four historical recovery tests and the 94
# active-kernel tests independently visible instead of hiding them in 98.
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
    "direct_local_image_scan": "INCOMPLETE / PENDING",
    "external_evidence_retention": "SELF_REPORTED_LOCAL_OBSERVATION / RAW_NOT_RETAINED",
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


def load_json(path: Path) -> Any:
    require(path.is_file(), f"missing JSON artifact: {path}")
    try:
        return json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object
        )
    except VerificationError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise VerificationError(f"cannot parse {path}: {exc}") from exc


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


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
    """Collect the complete API source/resource tree used by the 76-test receipt."""
    return _collect_surface(API_RUNTIME_SURFACE_DIR, "*")


def verify_no_executable_shadow_artifacts() -> int:
    """Reject unbound bytecode/native/archive shadows before child execution."""
    scanned: set[str] = set()
    violations: set[str] = set()
    for directory in EXECUTABLE_SHADOW_SCAN_DIRS:
        root = ROOT / directory
        require(root.is_dir(), f"missing executable-shadow scan directory: {directory}")
        for path in root.rglob("*"):
            raw_path = path.relative_to(ROOT).as_posix()
            scanned.add(raw_path)
            if "__pycache__" in path.parts:
                violations.add(raw_path)
            elif path.is_file() and path.suffix.casefold() in FORBIDDEN_EXECUTABLE_SHADOW_SUFFIXES:
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
        ("Dockerfile", ".dockerignore", "requirements.in", "requirements.txt", "pyproject.toml")
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
        require(path.is_file(), f"artifact is missing: {raw_path}")
        require(not path.is_symlink(), f"artifact may not be a symlink: {raw_path}")
        require(path.stat().st_size == expected_bytes, f"artifact byte drift: {raw_path}")
        require(sha256_file(path) == expected_hash, f"artifact hash drift: {raw_path}")
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
        == "INCOMPLETE / PENDING"
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

    stdout, _ = run_command(
        [sys.executable, "-B", "scripts/verify_project_coherence_gate4.py"],
        cwd=ROOT,
        timeout=480,
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

    inventory_text = HISTORY_INVENTORY_PATH.read_text(encoding="utf-8")
    for marker in (
        "361f8867a1b8983c383b4f4fe6d8d485e5dbbc80ee4f75e4b5d08b4e5f144f5f",
        "HISTORICALLY_INCONSISTENT",
        "ZeroNetworkGuard",
        "CompatibleZeroNetworkGuard",
        "31 failed",
    ):
        require(marker in inventory_text, f"historical inventory omits marker {marker!r}")
    return len(files), total_bytes, inventory_digest


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
            "cas_harness_v2.outcome_access_event.v1",
            "cas_harness_v2.evidence_packet.v2",
        ],
        "Gate 5 review matrix kernel-schema list drifted",
    )
    require(
        isinstance(matrix.get("review_basis"), str)
        and "No criterion creates ACCEPT, LICENSED, a public route, or a product route."
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
            "worker_checkpoints",
            "api_launcher_fleet_state",
            "successor_dependency_container_candidate",
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
        "current_complete_passed": 364,
        "current_complete_failed": 0,
        "current_complete_total": 364,
        "prior_independently_confirmed_complete_passed": 290,
    }.items():
        require(
            type(worker_receipt.get(field)) is int
            and worker_receipt[field] == expected,
            f"review-matrix worker receipt field {field!r} drifted",
        )
    require(
        worker_receipt.get("test_id_digest_kind")
        == "COLLECT_ONLY_NODE_ID_SET_SHA256 / ACTUAL_EXECUTED_NODE_IDS_NOT_RECEIPTED"
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
    require(
        type(api_receipt.get("passed")) is int
        and api_receipt["passed"] == 76
        and type(api_receipt.get("failed")) is int
        and api_receipt["failed"] == 0
        and type(api_receipt.get("total")) is int
        and api_receipt["total"] == 76
        and api_receipt.get("test_ids_sha256")
        == REQUIRED_TEST_SUITES["API, fleet state, and launcher identity"][
            "expected_test_ids_sha256"
        ].lower()
        and api_receipt.get("independently_reproduced") is False
        and isinstance(api_receipt.get("scope"), str)
        and "LOCAL_UNATTESTED_HOST_REGRESSION" in api_receipt["scope"]
        and "not hermetic worker-to-kernel integration" in api_receipt["scope"],
        "review-matrix API/launcher receipt drifted or overclaims independence",
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
    text = ADVERSARIAL_REVIEW_PATH.read_text(encoding="utf-8")
    for marker in (
        "DRAFT / OPEN / NOT_STARTED / RING 4 / NOT LICENSED / HELD / NOT FROZEN",
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
        "364/364 complete worker",
        "confirmed 290/290 receipt",
        "12602041756f20d1afd402fa56968660839e5eb1098438ba84c69bff8de7050b",
        "94566203b3e0ff79b3224c1c5a073698ca99d3c08bc1119a9082e42af4b178bd",
        "76/76",
        "1ed1e9e3afa2eda6881463ee5284dd4902ab94c0246b80d2937066480ac42921",
        "COMPLETED_WITH_FINDINGS",
        "critical, 0 high, 3 medium, and 4 low findings",
        "INCOMPLETE / PENDING",
        "OPEN_SECURITY",
        "including the final ID",
        "omitting the final LF are superseded",
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
            "Gate 5 status: `OPEN / NOT_STARTED / RING 4 / NOT LICENSED / "
            "HELD / NOT FROZEN`"
        ),
        "docs/working/project_coherence/gate5/"
        "HARNESS_V2_PREREGISTRATION_AND_EVIDENCE_PACKET_V2_SPEC_v0.1.md": (
            "# CAS Harness v2 preregistration and Evidence Packet v2 control kernel\n\n"
            "Status: `DRAFT / OPEN / NOT_STARTED / RESEARCH ONLY / NOT FROZEN`\n\n"
            "Admission and claim boundary: `RING 4 / NOT LICENSED / HELD`"
        ),
        "docs/working/project_coherence/gate5/GATE5_ADVERSARIAL_REVIEW_v0.1.md": (
            "# Gate 5 adversarial review v0.1\n\n"
            "**Status:** `DRAFT / OPEN / NOT_STARTED / RING 4 / NOT LICENSED / "
            "HELD / NOT FROZEN`"
        ),
    }
    for raw_path, header in required_headers.items():
        text = (ROOT / raw_path).read_text(encoding="utf-8")
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
    for raw_path in sorted(manifest_artifacts):
        if not raw_path.startswith("docs/working/project_coherence/gate5/"):
            continue
        if not raw_path.endswith((".md", ".json")):
            continue
        text = (ROOT / Path(*PurePosixPath(raw_path).parts)).read_text(
            encoding="utf-8"
        )
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

    model_loader = (
        WORKER_ROOT / "app" / "runtime" / "model_loader.py"
    ).read_text(encoding="utf-8")
    dockerfile = (WORKER_ROOT / "Dockerfile").read_text(encoding="utf-8")
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


def _require_candidate_file_record(
    key: str, record: Any, *, include_package_fields: bool = False
) -> None:
    expected = CANDIDATE_BUILD_INPUTS[key]
    require(isinstance(record, dict), f"candidate {key} record is missing")
    require_exact_keys(record, set(expected), label=f"candidate {key} record")
    require(record == expected, f"candidate {key} identity drifted")
    raw_path = canonical_repo_path(record.get("path"), label=f"candidate {key}")
    path = ROOT / Path(*PurePosixPath(raw_path).parts)
    require(path.is_file(), f"candidate {key} file is missing")
    require(not path.is_symlink(), f"candidate {key} file may not be a symlink")
    require(
        isinstance(record.get("sha256"), str)
        and SHA256_UPPER_RE.fullmatch(record["sha256"]) is not None
        and sha256_file(path) == record["sha256"],
        f"candidate {key} file hash drifted",
    )
    require(
        type(record.get("bytes")) is int
        and path.stat().st_size == record["bytes"],
        f"candidate {key} byte count drifted",
    )
    text = path.read_text(encoding="utf-8")
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
    app_root = WORKER_ROOT / "app"
    require(app_root.is_dir(), "candidate application tree is missing")
    files = sorted(
        (
            path
            for path in app_root.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
        ),
        key=lambda path: path.relative_to(WORKER_ROOT).as_posix(),
    )
    require(files, "candidate application tree is empty")
    payload = bytearray()
    total_bytes = 0
    for path in files:
        require(not path.is_symlink(), f"candidate application file may not be a symlink: {path}")
        data = path.read_bytes()
        relative = path.relative_to(WORKER_ROOT).as_posix()
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
    build_paths = [
        f"{WORKER_ROOT_REL}/Dockerfile",
        f"{WORKER_ROOT_REL}/.dockerignore",
        f"{WORKER_ROOT_REL}/requirements.txt",
        f"{WORKER_ROOT_REL}/requirements.in",
        f"{WORKER_ROOT_REL}/app",
    ]
    comparison = subprocess.run(
        ["git", "diff", "--quiet", CANDIDATE_SOURCE_COMMIT, "--", *build_paths],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    require(
        comparison.returncode == 0,
        "current worker build context differs from the source commit bound into the OCI image",
    )


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
    dockerfile = (WORKER_ROOT / "Dockerfile").read_text(encoding="utf-8")
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
    requirements = (WORKER_ROOT / "requirements.txt").read_text(encoding="utf-8")
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
    model_loader = (WORKER_ROOT / "app" / "runtime" / "model_loader.py").read_text(encoding="utf-8")
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
        worker_tests
        == {
            "passed": 364,
            "failed": 0,
            "total": 364,
            "test_ids_sha256": REQUIRED_TEST_SUITES["Live trace worker complete"]["expected_test_ids_sha256"],
        },
        "candidate worker test receipt drifted",
    )
    expected_api_targets = [
        f"{API_ROOT_REL}/{target}"
        for target in REQUIRED_TEST_SUITES["API, fleet state, and launcher identity"]["targets"]
    ]
    require(
        api_tests
        == {
            "passed": 76,
            "failed": 0,
            "total": 76,
            "test_ids_sha256": REQUIRED_TEST_SUITES["API, fleet state, and launcher identity"]["expected_test_ids_sha256"],
            "targets": expected_api_targets,
        },
        "candidate API/launcher/state test receipt drifted",
    )
    require(
        tests.get("receipt_scope")
        == (
            "LOCAL_UNATTESTED_HOST_REGRESSION / SEPARATE COLLECT-ONLY NODE-ID DIGEST / "
            "ACTUAL EXECUTED IDS NOT RECEIPTED / NOT GPU EXECUTION / NOT SCIENTIFIC EVIDENCE"
        ),
        "candidate test scope was promoted",
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


def verify_python_syntax(manifest_artifacts: dict[str, dict[str, Any]]) -> int:
    python_paths = sorted(path for path in manifest_artifacts if path.endswith(".py"))
    for raw_path in python_paths:
        path = ROOT / Path(*PurePosixPath(raw_path).parts)
        try:
            # Parse exact bytes so Python's own PEP 263 encoding detection accepts
            # valid UTF-8 BOM and encoding-cookie sources without normalizing them.
            ast.parse(path.read_bytes(), filename=raw_path)
        except (OSError, SyntaxError) as exc:
            raise VerificationError(f"cannot parse bound Python artifact {raw_path}: {exc}") from exc
    return len(python_paths)


def run_command(
    command: list[str],
    *,
    cwd: Path,
    timeout: int,
    extra_env: dict[str, str] | None = None,
    remove_env: Iterable[str] = (),
) -> tuple[str, str]:
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
        }
    )
    if extra_env:
        env.update(extra_env)
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


def collect_pytest_ids(
    *, cwd: Path, targets: list[str], pytest_plugins: list[str]
) -> list[str]:
    plugin_args = [part for plugin in pytest_plugins for part in ("-p", plugin)]
    stdout, stderr = run_command(
        [
            sys.executable,
            "-E",
            "-P",
            "-B",
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "-p",
            "no:cacheprovider",
            *plugin_args,
            *targets,
        ],
        cwd=cwd,
        timeout=240,
        extra_env=PYTEST_ISOLATION_ENV,
        remove_env=PYTEST_REMOVED_ENV,
    )
    transcript = stdout + stderr
    ids = sorted(
        {
            line.strip().replace("\\", "/")
            for line in transcript.splitlines()
            if "::" in line and line.strip() and not line.startswith((" ", "="))
        }
    )
    require(ids, f"pytest collection returned no test IDs for {targets}")
    require(
        all("\r" not in test_id and "\n" not in test_id for test_id in ids),
        "pytest collection returned a multiline test ID",
    )
    return ids


def test_id_digest(test_ids: Iterable[str]) -> str:
    ids = sorted(set(test_ids))
    return sha256_bytes(("\n".join(ids) + "\n").encode("utf-8"))


def verify_test_suites(manifest: dict[str, Any]) -> list[tuple[str, int, int]]:
    suites = manifest.get("test_suites")
    require(isinstance(suites, list), "manifest test_suites is not a list")
    by_name = {
        suite.get("name"): suite
        for suite in suites
        if isinstance(suite, dict) and isinstance(suite.get("name"), str)
    }
    results: list[tuple[str, int, int]] = []
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
        if suite["working_directory"] == ".":
            cwd = ROOT
        else:
            cwd_raw = canonical_repo_path(
                suite["working_directory"], label=f"{name} working directory"
            )
            cwd = ROOT / cwd_raw
        require(cwd.is_dir(), f"{name}: working directory is missing")
        targets = suite["targets"]
        require(
            isinstance(targets, list)
            and targets
            and all(isinstance(target, str) and target for target in targets),
            f"{name}: targets are malformed",
        )
        pytest_plugins = suite["pytest_plugins"]
        require(
            isinstance(pytest_plugins, list)
            and all(
                isinstance(plugin, str) and plugin for plugin in pytest_plugins
            ),
            f"{name}: explicit pytest plugin list is malformed",
        )
        require(
            type(suite["expected_tests"]) is int
            and type(suite["expected_subtests"]) is int,
            f"{name}: expected test counts must be exact integers",
        )
        ids = collect_pytest_ids(
            cwd=cwd,
            targets=targets,
            pytest_plugins=pytest_plugins,
        )
        require(
            len(ids) == suite["expected_tests"],
            f"{name}: collected {len(ids)} tests, expected {suite['expected_tests']}",
        )
        require(
            test_id_digest(ids) == suite["expected_test_ids_sha256"],
            f"{name}: exact pytest node-ID set drifted",
        )
        plugin_args = [
            part for plugin in pytest_plugins for part in ("-p", plugin)
        ]
        stdout, stderr = run_command(
            [
                sys.executable,
                "-E",
                "-P",
                "-B",
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                *plugin_args,
                *targets,
            ],
            cwd=cwd,
            timeout=480,
            extra_env=PYTEST_ISOLATION_ENV,
            remove_env=PYTEST_REMOVED_ENV,
        )
        transcript = stdout + stderr
        expected = suite["expected_tests"]
        subtests = suite["expected_subtests"]
        if subtests:
            summary = re.compile(
                rf"(?m)^{expected} passed, {subtests} subtests passed in [0-9.]+s$"
            )
        else:
            summary = re.compile(rf"(?m)^{expected} passed in [0-9.]+s$")
        require(
            summary.search(transcript) is not None,
            f"{name}: exact all-pass receipt is missing or includes another outcome",
        )
        results.append((name, expected, subtests))

    for name, receipt in REQUIRED_SUBSUITE_DIGESTS.items():
        ids = collect_pytest_ids(
            cwd=ROOT,
            targets=receipt["targets"],
            pytest_plugins=receipt["pytest_plugins"],
        )
        require(
            len(ids) == receipt["expected_tests"],
            f"{name}: collected test count drifted",
        )
        require(
            test_id_digest(ids) == receipt["expected_test_ids_sha256"],
            f"{name}: exact pytest node-ID subset drifted",
        )
    return results


def main() -> int:
    require(MANIFEST_PATH.is_file(), "Gate 5 manifest is missing")
    require(not MANIFEST_PATH.is_symlink(), "Gate 5 manifest may not be a symlink")
    shadow_surface_count = verify_no_executable_shadow_artifacts()
    initial_manifest_file_sha = sha256_file(MANIFEST_PATH)
    manifest = load_json(MANIFEST_PATH)
    require(isinstance(manifest, dict), "Gate 5 manifest root is not an object")
    artifacts = verify_manifest(manifest)
    gate4_artifact_count, gate4_manifest_sha = verify_gate4_dependency(artifacts)
    claim_count = verify_claim_ledger()
    history_count, history_bytes, history_digest = verify_history()
    criterion_count, open_count = verify_review_matrix(artifacts)
    verify_adversarial_review()
    verify_no_status_promotion_text(artifacts)
    verify_model_and_security_bindings()
    verify_dependency_and_container_candidate_receipt()
    python_count = verify_python_syntax(artifacts)
    suite_results = verify_test_suites(manifest)

    # Subprocesses execute bound tests and conftests.  Re-read and rehash the
    # complete current tree before PASS so a test, hook, or concurrent writer
    # cannot leave the repository in a state different from the admitted one.
    post_manifest = load_json(MANIFEST_PATH)
    require(post_manifest == manifest, "Gate 5 manifest changed during verification")
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
    print(f"  executable-shadow paths scanned before tests: {shadow_surface_count}")
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
        "  test suites: "
        + "; ".join(
            f"{name}={tests}" + (f"+{subtests} subtests" if subtests else "")
            for name, tests, subtests in suite_results
        )
    )
    print(f"  review criteria: {criterion_count}; required OPEN boundaries: {open_count}")
    print("  postflight: Gate 5, historical, and transitive Gate 4 bytes rehashed")
    print(
        "  dependency security: OPEN_SECURITY / HELD (patched candidate "
        "digest-bound; external build/scan observations are self-reported and raw "
        "payloads are not repository-retained; pip-audit partial 72/73 with Torch skipped; SBOM "
        "package scan COMPLETED_WITH_FINDINGS: 0 critical / 0 high / "
        "3 medium / 4 low; direct filesystem scan INCOMPLETE / PENDING)"
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
