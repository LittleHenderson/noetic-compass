#!/usr/bin/env python3
"""Verify the isolated Project Coherence Gate 4 research candidate.

This is an identity, structure, regression, and boundary verifier. A PASS is not
canon acceptance, empirical validation, safety certification, claim licensing,
peer review, product readiness, or disclosure approval.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
GATE4_DIR = ROOT / "docs" / "working" / "project_coherence" / "gate4"
MANIFEST_PATH = GATE4_DIR / "GATE4_ARTIFACT_MANIFEST_v0.1.json"
REVIEW_MATRIX_PATH = GATE4_DIR / "GATE4_REVIEW_MATRIX_v0.1.json"
PCBA_COVERAGE_PATH = GATE4_DIR / "PCBA_CCDL_CONSTRUCT_COVERAGE_v0.1.json"
OHM_CONFLICT_PATH = GATE4_DIR / "CAS_OHM_SOURCE_CONFLICT_EVIDENCE_v0.1.json"
SHA256_RE = re.compile(r"^[A-F0-9]{64}$")

PACKAGE_DIRS = (
    "src/cas_core_v8",
    "src/cas_pcba_v8",
    "src/cas_ohm_v1",
    "tests/cas_core_v8",
    "tests/cas_pcba_v8",
    "tests/cas_ohm_v1",
)

AUTHORITY_MATRIX_PATH = (
    ROOT
    / "docs"
    / "working"
    / "project_coherence"
    / "CANONICAL_SOURCE_AUTHORITY_MATRIX_v0.1.json"
)
REQUIRED_SOURCE_IDS = {
    "SRC-ACTIVE-COMPILER-CURRENT",
    "SRC-PCBA-ENGINEER-20260726",
    "SRC-CAS-OHM-GUIDE-01",
    "SRC-CAS-OHM-ADDENDUM-01",
    "SRC-CAS-OHM-PCBA-APP-I",
}
REQUIRED_CONTROL_ARTIFACTS = {
    "docs/working/project_coherence/CLAIM_LEDGER_v0.1.json",
    "docs/working/project_coherence/gate1/GATE1_ARTIFACT_MANIFEST_v0.1.json",
    "docs/working/project_coherence/gate4/README.md",
    "docs/working/project_coherence/gate4/CAS_CORE_V8_CANDIDATE_SPEC_v0.1.md",
    "docs/working/project_coherence/gate4/CAS_PCBA_V8_SOURCE_AUDIT_AND_SPEC_v0.1.md",
    "docs/working/project_coherence/gate4/CAS_OHM_V1_SOURCE_AUDIT_AND_SPEC_v0.1.md",
    "docs/working/project_coherence/gate4/PCBA_CCDL_CONSTRUCT_COVERAGE_v0.1.json",
    "docs/working/project_coherence/gate4/CAS_OHM_SOURCE_CONFLICT_EVIDENCE_v0.1.json",
    "docs/working/project_coherence/gate4/GATE4_REVIEW_MATRIX_v0.1.json",
    "docs/working/project_coherence/gate4/GATE4_ADVERSARIAL_REVIEW_v0.1.md",
    "scripts/verify_project_coherence_gate4.py",
}
REQUIRED_TEST_SUITES = {
    "CAS Core v8": "tests/cas_core_v8",
    "CAS PCBA v8": "tests/cas_pcba_v8",
    "CAS-Ohm v1": "tests/cas_ohm_v1",
}
REQUIRED_BOUNDARY_IDS = {
    "G4-OPEN-CANON",
    "G4-OPEN-MIGRATION",
    "G4-OPEN-HERMETICITY",
    "G4-OPEN-PY-RUST",
    "G4-OPEN-CLAIM-AUTHORITY",
    "G4-OPEN-CCDL-GRAMMAR",
    "G4-OPEN-PCBA-STATEFUL",
    "G4-OPEN-PCBA-CALIBRATION",
    "G4-OPEN-PCBA-SAFETY",
    "G4-OPEN-OHM-EMPIRICAL",
    "G4-OPEN-OHM-UNCERTAINTY",
    "G4-OPEN-PEER-REVIEW",
    "G4-OPEN-HARNESS-INTEGRATION",
    "G4-OPEN-PRODUCT-READINESS",
    "G4-OPEN-DISCLOSURE",
}
REVIEW_DISPOSITIONS = {
    "IMPLEMENTED_AND_REGRESSION_TESTED",
    "BASELINE_DEFECT_QUARANTINED",
    "OPEN_EXTERNAL_VALIDATION",
    "OPEN_FORMALIZATION",
    "OPEN_GOVERNANCE",
    "OPEN_ENGINEERING",
}
OPEN_REVIEW_DISPOSITIONS = {
    "OPEN_EXTERNAL_VALIDATION",
    "OPEN_FORMALIZATION",
    "OPEN_GOVERNANCE",
    "OPEN_ENGINEERING",
}
REVIEW_SUBSYSTEMS = {
    "CAS_CORE_V8",
    "CAS_PCBA_V8",
    "CAS_OHM_V1",
    "CROSS_DOMAIN",
}


class VerificationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def load_json(path: Path) -> Any:
    require(path.is_file(), f"missing JSON artifact: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise VerificationError(f"cannot parse {path}: {exc}") from exc


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def sha256_bytes(payload: bytes) -> str:
    require(isinstance(payload, bytes), "SHA-256 payload must be bytes")
    return hashlib.sha256(payload).hexdigest().upper()


def resolve(raw: str) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else ROOT / path


def verify_manifest(manifest: dict[str, Any]) -> None:
    require(
        manifest.get("schema_version")
        == "project_coherence.gate4_artifact_manifest.v0.1",
        "unexpected Gate 4 manifest schema",
    )
    require(
        manifest.get("document_status") == "DRAFT / OPEN / NOT FROZEN",
        "Gate 4 manifest is not explicitly draft/open/unfrozen",
    )
    require(manifest.get("gate4_status") == "OPEN", "Gate 4 is not OPEN")
    require(
        manifest.get("gate_decision") == "KEEP_OPEN",
        "Gate 4 manifest attempts to admit the candidate",
    )
    require(manifest.get("admission_ring") == 4, "Gate 4 escaped Ring 4")
    require(
        manifest.get("license_status") == "NOT LICENSED",
        "Gate 4 has a licensed status",
    )
    require(
        manifest.get("disclosure_status") == "HELD",
        "Gate 4 is not held/private",
    )
    require(
        manifest.get("public_disclosure_authorized") is False,
        "Gate 4 authorizes public disclosure",
    )
    require(
        manifest.get("canon_effect") == "NONE",
        "Gate 4 manifest claims a canon effect",
    )
    require(
        manifest.get("product_claim_effect") == "NONE",
        "Gate 4 manifest claims a product-claim effect",
    )
    require(manifest.get("manifest_self_hash") is None, "manifest hashes itself")

    artifacts = manifest.get("artifacts")
    require(isinstance(artifacts, list) and artifacts, "manifest has no artifacts")
    paths: list[str] = []
    for index, record in enumerate(artifacts):
        require(isinstance(record, dict), f"artifact {index} is not an object")
        raw_path = record.get("path")
        expected_hash = record.get("sha256")
        expected_bytes = record.get("bytes")
        require(isinstance(raw_path, str) and raw_path, f"artifact {index} has no path")
        require(
            isinstance(expected_hash, str) and SHA256_RE.fullmatch(expected_hash),
            f"artifact {raw_path}: invalid SHA-256",
        )
        require(
            isinstance(expected_bytes, int) and not isinstance(expected_bytes, bool)
            and expected_bytes >= 0,
            f"artifact {raw_path}: invalid byte count",
        )
        role = record.get("role")
        require(isinstance(role, str) and role, f"artifact {raw_path}: role is missing")
        declared_path = Path(raw_path)
        require(not declared_path.is_absolute(), f"artifact path must be repository-relative: {raw_path}")
        require(
            ".." not in declared_path.parts,
            f"artifact path may not traverse outside the repository: {raw_path}",
        )
        path = resolve(raw_path)
        try:
            path.resolve().relative_to(ROOT.resolve())
        except ValueError as exc:
            raise VerificationError(
                f"artifact resolves outside the repository: {raw_path}"
            ) from exc
        require(path.is_file(), f"artifact is missing: {path}")
        require(path.stat().st_size == expected_bytes, f"artifact byte drift: {raw_path}")
        require(sha256_file(path) == expected_hash, f"artifact hash drift: {raw_path}")
        paths.append(Path(raw_path).as_posix())
    require(
        len(paths) == len({path.casefold() for path in paths}),
        "manifest contains duplicate artifact paths",
    )
    require(
        MANIFEST_PATH.relative_to(ROOT).as_posix() not in paths,
        "manifest must not hash itself",
    )
    require(
        REQUIRED_CONTROL_ARTIFACTS <= set(paths),
        "manifest omits required Gate 4 control artifacts: "
        f"{sorted(REQUIRED_CONTROL_ARTIFACTS - set(paths))}",
    )

    bound_python = {
        path
        for path in paths
        if path.endswith(".py") and any(path.startswith(prefix + "/") for prefix in PACKAGE_DIRS)
    }
    actual_python: set[str] = set()
    for directory in PACKAGE_DIRS:
        actual_python.update(
            path.relative_to(ROOT).as_posix()
            for path in (ROOT / directory).rglob("*.py")
            if "__pycache__" not in path.parts
        )
    require(
        bound_python == actual_python,
        "manifest does not exactly bind the Gate 4 package/test Python surface: "
        f"missing={sorted(actual_python - bound_python)} extra={sorted(bound_python - actual_python)}",
    )

    authority = load_json(AUTHORITY_MATRIX_PATH)
    authority_sources = authority.get("sources") if isinstance(authority, dict) else None
    require(isinstance(authority_sources, list), "authority matrix has no source records")
    authority_by_id = {
        record.get("id"): record
        for record in authority_sources
        if isinstance(record, dict) and isinstance(record.get("id"), str)
    }
    require(
        REQUIRED_SOURCE_IDS <= set(authority_by_id),
        "authority matrix omits a required Gate 4 source",
    )

    sources = manifest.get("external_source_bindings")
    require(
        isinstance(sources, list) and len(sources) == len(REQUIRED_SOURCE_IDS),
        "source bindings must contain the five exact registered baselines",
    )
    source_ids: list[str] = []
    for record in sources:
        require(isinstance(record, dict), "source binding is not an object")
        source_id = record.get("source_id")
        raw_path = record.get("path")
        expected_hash = record.get("sha256")
        require(isinstance(source_id, str) and source_id, "source binding lacks source_id")
        require(isinstance(raw_path, str) and raw_path, f"{source_id}: source path missing")
        require(
            isinstance(expected_hash, str) and SHA256_RE.fullmatch(expected_hash),
            f"{source_id}: invalid source hash",
        )
        expected_bytes = record.get("bytes")
        require(
            isinstance(expected_bytes, int)
            and not isinstance(expected_bytes, bool)
            and expected_bytes >= 0,
            f"{source_id}: source byte count missing or invalid",
        )
        registered = authority_by_id.get(source_id)
        require(isinstance(registered, dict), f"{source_id}: source is not registered")
        require(raw_path == registered.get("path"), f"{source_id}: path differs from authority matrix")
        require(
            expected_hash == registered.get("sha256"),
            f"{source_id}: hash differs from authority matrix",
        )
        require(
            expected_bytes == registered.get("bytes"),
            f"{source_id}: byte count differs from authority matrix",
        )
        path = resolve(raw_path)
        require(path.is_file(), f"{source_id}: source is missing: {path}")
        require(sha256_file(path) == expected_hash, f"{source_id}: source hash drift")
        require(path.stat().st_size == expected_bytes, f"{source_id}: source byte drift")
        source_ids.append(source_id)
    require(len(source_ids) == len(set(source_ids)), "duplicate Gate 4 source IDs")
    require(
        set(source_ids) == REQUIRED_SOURCE_IDS,
        "Gate 4 source binding set differs from the registered baseline set",
    )

    boundaries = manifest.get("required_open_boundaries")
    require(
        isinstance(boundaries, list) and len(boundaries) >= len(REQUIRED_BOUNDARY_IDS)
        and all(isinstance(item, str) and item for item in boundaries),
        "Gate 4 open-boundary list is incomplete",
    )
    boundary_ids: list[str] = []
    for boundary in boundaries:
        match = re.match(r"^\[([A-Z0-9-]+)\] ", boundary)
        require(match is not None, f"open boundary has no stable ID: {boundary!r}")
        boundary_ids.append(match.group(1))
    require(len(boundary_ids) == len(set(boundary_ids)), "duplicate Gate 4 boundary IDs")
    require(
        set(boundary_ids) == REQUIRED_BOUNDARY_IDS,
        "Gate 4 open-boundary IDs differ from the required closure surface",
    )


def run_command(command: list[str], *, timeout: int) -> tuple[str, str]:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
    )
    if completed.returncode != 0:
        raise VerificationError(
            f"command failed ({completed.returncode}): {' '.join(command)}\n"
            f"{completed.stdout}{completed.stderr}"
        )
    return completed.stdout, completed.stderr


def verify_review_matrix() -> tuple[int, int]:
    matrix = load_json(REVIEW_MATRIX_PATH)
    require(isinstance(matrix, dict), "Gate 4 review matrix root is not an object")
    require(
        matrix.get("schema_version") == "project_coherence.gate4_review_matrix.v0.1",
        "unexpected Gate 4 review-matrix schema",
    )
    require(
        matrix.get("document_status") == "DRAFT / OPEN / NOT FROZEN",
        "review matrix is not explicitly draft/open/unfrozen",
    )
    require(matrix.get("gate4_status") == "OPEN", "review matrix closes Gate 4")
    require(matrix.get("gate_decision") == "KEEP_OPEN", "review matrix admits Gate 4")
    require(matrix.get("admission_ring") == 4, "review matrix escaped Ring 4")
    require(matrix.get("license_status") == "NOT LICENSED", "review matrix licenses claims")
    require(matrix.get("disclosure_status") == "HELD", "review matrix releases disclosure")
    require(
        matrix.get("public_disclosure_authorized") is False,
        "review matrix authorizes disclosure",
    )

    criteria = matrix.get("criteria")
    require(
        isinstance(criteria, list) and len(criteria) >= 24,
        "review matrix has fewer than 24 cross-domain criteria",
    )
    ids: list[str] = []
    subsystems: set[str] = set()
    open_count = 0
    for index, criterion in enumerate(criteria):
        require(isinstance(criterion, dict), f"review criterion {index} is not an object")
        criterion_id = criterion.get("id")
        subsystem = criterion.get("subsystem")
        disposition = criterion.get("disposition")
        require(
            isinstance(criterion_id, str)
            and re.fullmatch(r"G4-(?:CORE|PCBA|OHM|X)-[0-9]{3}", criterion_id),
            f"criterion {index} has an invalid stable ID",
        )
        require(subsystem in REVIEW_SUBSYSTEMS, f"{criterion_id}: invalid subsystem")
        for field in ("question", "acceptance_requirement", "observed_result"):
            require(
                isinstance(criterion.get(field), str) and criterion[field],
                f"{criterion_id}: {field} is missing",
            )
        require(
            disposition in REVIEW_DISPOSITIONS,
            f"{criterion_id}: invalid disposition {disposition!r}",
        )
        require(
            criterion.get("canon_effect") == "NONE",
            f"{criterion_id}: criterion claims a canon effect",
        )
        require(
            criterion.get("product_claim_effect") == "NONE",
            f"{criterion_id}: criterion claims a product-claim effect",
        )
        evidence_refs = criterion.get("evidence_refs")
        require(
            isinstance(evidence_refs, list)
            and evidence_refs
            and all(isinstance(item, str) and item for item in evidence_refs),
            f"{criterion_id}: evidence references are missing",
        )
        for evidence_ref in evidence_refs:
            declared_evidence = Path(evidence_ref)
            require(
                not declared_evidence.is_absolute() and ".." not in declared_evidence.parts,
                f"{criterion_id}: evidence reference must stay within the repository",
            )
            evidence_path = ROOT / declared_evidence
            require(
                evidence_path.is_file(),
                f"{criterion_id}: evidence artifact is missing: {evidence_ref}",
            )
        obligation = criterion.get("remaining_obligation")
        if disposition in OPEN_REVIEW_DISPOSITIONS:
            open_count += 1
            require(
                isinstance(obligation, str) and obligation,
                f"{criterion_id}: open criterion has no remaining obligation",
            )
        else:
            require(
                obligation is None,
                f"{criterion_id}: closed/quarantined criterion retains an obligation",
            )
        ids.append(criterion_id)
        subsystems.add(subsystem)
    require(len(ids) == len(set(ids)), "review matrix has duplicate criterion IDs")
    require(
        REVIEW_SUBSYSTEMS <= subsystems,
        "review matrix omits a required subsystem",
    )
    require(open_count >= 10, "review matrix understates the open research boundary")
    return len(criteria), open_count


def verify_pcba_coverage_audit() -> tuple[int, int]:
    audit = load_json(PCBA_COVERAGE_PATH)
    require(isinstance(audit, dict), "PCBA construct-coverage root is not an object")
    require(
        audit.get("schema_version")
        == "project_coherence.pcba_ccdl_construct_coverage.v0.1",
        "unexpected PCBA construct-coverage schema",
    )
    require(audit.get("document_status") == "DRAFT / OPEN / NOT FROZEN", "PCBA coverage audit is not open")
    require(audit.get("admission_ring") == 4, "PCBA coverage audit escaped Ring 4")
    require(audit.get("license_status") == "NOT LICENSED", "PCBA coverage audit licenses a claim")
    require(audit.get("disclosure_status") == "HELD", "PCBA coverage audit is not held")
    require(
        audit.get("source_id") == "SRC-PCBA-ENGINEER-20260726"
        and audit.get("source_sha256")
        == "294320B39FA521EAC086E99E2D9DB913E2B6CFF0754FF82DB1EF966424566274",
        "PCBA coverage audit is not bound to the registered engineering source",
    )
    boards = audit.get("reference_boards")
    require(isinstance(boards, list) and len(boards) == 5, "PCBA coverage audit must cover five boards")
    require(all(isinstance(record, dict) for record in boards), "PCBA coverage board record is not an object")
    board_ids = [record.get("board_id") for record in boards]
    require(len(board_ids) == 5 and len(board_ids) == len(set(board_ids)), "PCBA coverage board IDs are invalid")
    direct = sum(record.get("direct_syntactic_counterexample") is True for record in boards)
    bounded_non = sum(record.get("direct_syntactic_counterexample") is False for record in boards)
    require(direct == 4 and bounded_non == 1, "PCBA coverage result counts drifted")
    require(audit.get("direct_counterexample_count") == direct, "PCBA direct-counterexample count drifted")
    require(audit.get("bounded_noncounterexample_count") == bounded_non, "PCBA bounded-noncounterexample count drifted")
    require(
        audit.get("corpus_conclusion")
        == "FORMAL_EBNF_DOES_NOT_COVER_PUBLISHED_FIVE_BOARD_CORPUS",
        "PCBA corpus conclusion drifted",
    )
    return len(boards), direct


def verify_ohm_conflict_audit() -> int:
    audit = load_json(OHM_CONFLICT_PATH)
    require(isinstance(audit, dict), "CAS-Ohm conflict-audit root is not an object")
    require(
        audit.get("schema_version")
        == "project_coherence.cas_ohm_source_conflict_evidence.v0.1",
        "unexpected CAS-Ohm conflict-audit schema",
    )
    require(audit.get("document_status") == "DRAFT / OPEN / NOT FROZEN", "CAS-Ohm conflict audit is not open")
    require(audit.get("gate_effect") == "KEEP_OPEN", "CAS-Ohm conflict audit closes the gate")
    require(audit.get("admission_ring") == 4, "CAS-Ohm conflict audit escaped Ring 4")
    require(audit.get("license_status") == "NOT LICENSED", "CAS-Ohm conflict audit licenses a claim")
    require(audit.get("disclosure_status") == "HELD", "CAS-Ohm conflict audit is not held")
    sources = audit.get("sources")
    require(isinstance(sources, list) and len(sources) == 4, "CAS-Ohm conflict audit source set is incomplete")
    source_ids = {record.get("source_id") for record in sources if isinstance(record, dict)}
    require(
        source_ids
        == {
            "SRC-CAS-OHM-GUIDE-01",
            "SRC-CAS-OHM-ADDENDUM-01",
            "SRC-CAS-OHM-PCBA-APP-I",
            "SRC-PCBA-ENGINEER-20260726",
        },
        "CAS-Ohm conflict audit source IDs drifted",
    )
    conflicts = audit.get("conflicts")
    require(isinstance(conflicts, list) and len(conflicts) == 8, "CAS-Ohm conflict audit must contain eight records")
    require(all(isinstance(record, dict) for record in conflicts), "CAS-Ohm conflict record is not an object")
    conflict_ids = [record.get("id") for record in conflicts]
    require(len(conflict_ids) == 8 and len(conflict_ids) == len(set(conflict_ids)), "CAS-Ohm conflict IDs are invalid")
    require(audit.get("conflict_count") == len(conflicts), "CAS-Ohm conflict count drifted")
    require(
        all(
            isinstance(record.get("evidence"), list)
            and record["evidence"]
            and isinstance(record.get("candidate_rule"), str)
            and record["candidate_rule"]
            for record in conflicts
        ),
        "CAS-Ohm conflict evidence or candidate rule is incomplete",
    )
    return len(conflicts)


def verify_suites(manifest: dict[str, Any]) -> list[tuple[str, int]]:
    suites = manifest.get("test_suites")
    require(isinstance(suites, list) and len(suites) == 3, "expected three Gate 4 test suites")
    results: list[tuple[str, int]] = []
    suite_bindings: dict[str, str] = {}
    for suite in suites:
        require(isinstance(suite, dict), "test-suite record is not an object")
        name = suite.get("name")
        test_dir = suite.get("test_directory")
        expected = suite.get("expected_tests")
        expected_ids_sha256 = suite.get("expected_test_ids_sha256")
        require(isinstance(name, str) and name, "test suite has no name")
        require(isinstance(test_dir, str) and test_dir, f"{name}: test directory missing")
        require(name not in suite_bindings, f"duplicate test-suite name: {name}")
        suite_bindings[name] = Path(test_dir).as_posix()
        require(
            isinstance(expected, int) and not isinstance(expected, bool) and expected > 0,
            f"{name}: expected test count is invalid",
        )
        require(
            isinstance(expected_ids_sha256, str)
            and SHA256_RE.fullmatch(expected_ids_sha256),
            f"{name}: expected test-ID digest is invalid",
        )
        stdout, stderr = run_command(
            [sys.executable, "-X", "dev", "-m", "unittest", "discover", "-s", test_dir, "-v"],
            timeout=180,
        )
        transcript = stdout + stderr
        match = re.search(r"Ran (\d+) tests? in", transcript)
        require(match is not None, f"{name}: unittest count receipt missing")
        actual = int(match.group(1))
        require(actual == expected, f"{name}: ran {actual} tests, expected {expected}")
        require("OK" in transcript, f"{name}: unittest success marker missing")
        test_ids = re.findall(
            r"^[^\r\n]+ \(([^()\r\n]+)\) \.\.\. ok$",
            transcript,
            flags=re.MULTILINE,
        )
        require(
            len(test_ids) == actual and len(test_ids) == len(set(test_ids)),
            f"{name}: exact passing test-ID receipt is incomplete or duplicated",
        )
        actual_ids_sha256 = sha256_bytes(
            ("\n".join(sorted(test_ids)) + "\n").encode("utf-8")
        )
        require(
            actual_ids_sha256 == expected_ids_sha256,
            f"{name}: passing test-ID set drifted",
        )
        results.append((name, actual))
    require(
        suite_bindings == REQUIRED_TEST_SUITES,
        "Gate 4 test-suite bindings differ from the required package suites",
    )
    return results


def verify_claim_boundary() -> int:
    ledger = load_json(
        ROOT / "docs" / "working" / "project_coherence" / "CLAIM_LEDGER_v0.1.json"
    )
    records = ledger.get("records")
    require(isinstance(records, list) and records, "claim ledger is empty")
    ids = [record.get("id") for record in records]
    require(len(ids) == len(set(ids)), "claim ledger has duplicate IDs")
    require(
        all(record.get("admission_ring") == 4 for record in records),
        "a Gate 4 claim escaped Ring 4",
    )
    require(
        all(record.get("product_claim_status") == "NOT LICENSED" for record in records),
        "a claim is no longer NOT LICENSED",
    )
    required = {
        "CLM-CAS-OHM-PHYSICAL-TELEMETRY",
        "CLM-CAS-OHM-LOCAL-RESPONSE",
        "CLM-CAS-OHM-EFFECTIVE-RESISTANCE",
        "CLM-CAS-OHM-GAIN-COMPOSITION",
        "CLM-CAS-OHM-REDUNDANCY",
        "CLM-CAS-OHM-RESIDUAL-LOCALIZATION",
        "CLM-PCBA-COMPILER-CONFORMANCE",
        "CLM-PCBA-CSB-SAFETY-EFFECTIVENESS",
    }
    require(required <= set(ids), "Gate 4 claim-boundary records are incomplete")
    return len(records)


def main() -> int:
    manifest = load_json(MANIFEST_PATH)
    require(isinstance(manifest, dict), "Gate 4 manifest root is not an object")
    verify_manifest(manifest)
    criterion_count, open_criterion_count = verify_review_matrix()
    pcba_board_count, pcba_counterexample_count = verify_pcba_coverage_audit()
    ohm_conflict_count = verify_ohm_conflict_audit()

    gate1_stdout, _ = run_command(
        [sys.executable, "scripts/verify_project_coherence_gate1.py"], timeout=360
    )
    require(
        "Project Coherence integrated Gate 1 verification: PASS" in gate1_stdout,
        "Gate 1 dependency receipt is missing",
    )

    run_command(
        [
            sys.executable,
            "-m",
            "compileall",
            "-q",
            "src/cas_core_v8",
            "src/cas_pcba_v8",
            "src/cas_ohm_v1",
        ],
        timeout=120,
    )
    suite_results = verify_suites(manifest)
    claim_count = verify_claim_boundary()

    artifact_count = len(manifest["artifacts"])
    test_count = sum(count for _, count in suite_results)
    print("Project Coherence integrated Gate 4 verification: PASS")
    print(f"  hash-bound Gate 4 artifacts: {artifact_count}")
    print(
        "  candidate test suites: "
        + "; ".join(f"{name}={count}" for name, count in suite_results)
        + f"; total={test_count}"
    )
    print(f"  claim records: {claim_count} (all Ring 4 / NOT LICENSED)")
    print(
        f"  review criteria: {criterion_count}; explicitly open: {open_criterion_count}"
    )
    print(
        "  PCBA EBNF/reference corpus: "
        f"{pcba_counterexample_count} direct counterexamples across "
        f"{pcba_board_count} audited boards"
    )
    print(f"  CAS-Ohm source conflicts/under-specifications: {ohm_conflict_count}")
    print("  dependency: integrated Gate 1 PASS")
    print("  Gate 4 status: OPEN / Ring 4 / NOT LICENSED / HELD / NOT FROZEN")
    print(
        "This PASS proves only the manifest identities and implemented checks; "
        "it is not canon acceptance, peer review, empirical validation, safety "
        "certification, claim licensing, product readiness, or disclosure approval."
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except VerificationError as exc:
        print(f"Project Coherence Gate 4 verification: FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
