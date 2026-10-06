"""Verify the isolated finite-context modality-composition proof package."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys


HERE = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[6]
CERTIFICATE_PATH = HERE / "MODALITY_COMPOSITION_CERTIFICATE_v0.1.json"

sys.path.insert(0, str(REPO_ROOT))

from src.noetic_topos2.modality_composition import run_certificate  # noqa: E402


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _execution_summary(result: dict[str, object]) -> dict[str, object]:
    fixtures = result["fixtures"]
    assert isinstance(fixtures, dict)
    return {
        "all_checks_pass": result["all_checks_pass"],
        "fixture_count": result["fixture_count"],
        "all_fixture_checks_pass": all(
            fixture["all_checks_pass"] for fixture in fixtures.values()
        ),
        "symbolic": result["symbolic"],
        "total_nested_sections_checked": sum(
            fixture["nested_sections_checked"] for fixture in fixtures.values()
        ),
        "total_restriction_squares_checked": sum(
            fixture["restriction_squares_checked"] for fixture in fixtures.values()
        ),
        "total_unit_components_checked": sum(
            fixture["unit_components_checked"] for fixture in fixtures.values()
        ),
    }


def main() -> int:
    certificate = json.loads(CERTIFICATE_PATH.read_text(encoding="utf-8"))
    errors: list[str] = []

    if certificate.get("schema_version") != (
        "noetic_topos2.modality_composition_certificate.v0.1"
    ):
        errors.append("unexpected or missing certificate schema version")
    if certificate.get("document_status") != (
        "INTERNAL PROOF CANDIDATE / REVIEW REQUIRED / NOT LICENSED"
    ):
        errors.append("document status does not preserve the internal candidate boundary")
    if certificate.get("scope", {}).get("ambient_category") != "PSh(L,Set)":
        errors.append("ambient scope is not exactly PSh(L,Set)")
    resolution = certificate.get("resolution", {})
    if resolution.get("status") != "INTERNAL PROOF COMPLETE / REVIEW REQUIRED":
        errors.append("finite proof status is not the registered review-required state")
    if resolution.get("result") != "POSITIVE AT FINITE-CONTEXT LEVEL":
        errors.append("finite result is not the registered positive scoped result")
    if resolution.get("strict_equality_disclaimed") is not True:
        errors.append("strict equality must remain disclaimed")
    if resolution.get("independent_peer_review_complete") is not False:
        errors.append("independent peer review may not be asserted")
    if resolution.get("proof_assistant_check_complete") is not False:
        errors.append("proof-assistant completion may not be asserted")

    required_boundaries = {
        "admission_ring": 4,
        "license_status": "NOT LICENSED",
        "disclosure_status": "INTERNAL ONLY",
        "review_state": "UNASSESSED",
    }
    for key, expected in required_boundaries.items():
        if certificate.get(key) != expected:
            errors.append(f"{key}: expected {expected!r}")

    open_obligations = certificate.get("open_obligations", {})
    for obligation in (
        "product_site_lift",
        "observational_topology_interaction",
        "legacy_compatibility",
        "formal_verification",
        "independent_category_theory_review",
    ):
        if open_obligations.get(obligation) != "OPEN":
            errors.append(f"open obligation was not preserved: {obligation}")

    for relative_path, expected_record in certificate.get("artifact_hashes", {}).items():
        path = REPO_ROOT / relative_path
        if not path.is_file():
            errors.append(f"missing artifact: {relative_path}")
            continue
        actual = {"sha256": _sha256(path), "bytes": path.stat().st_size}
        if actual != expected_record:
            errors.append(
                f"artifact hash/size mismatch for {relative_path}: "
                f"expected {expected_record}, got {actual}"
            )

    result = run_certificate()
    summary = _execution_summary(result)
    if summary != certificate.get("expected_execution_summary"):
        errors.append("executable result does not match the registered summary")

    tests = subprocess.run(
        [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests/noetic_topos2_modality_composition",
            "-p",
            "test_*.py",
            "-v",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    test_output = tests.stdout + tests.stderr
    if tests.returncode != 0:
        errors.append("scoped unit tests failed")
    if "Ran 6 tests" not in test_output:
        errors.append("scoped unit-test count is not the registered six")

    if errors:
        print("MODALITY_COMPOSITION_VERIFICATION: FAIL")
        for error in errors:
            print(f"- {error}")
        print(test_output)
        return 1

    print("MODALITY_COMPOSITION_VERIFICATION: PASS")
    print(json.dumps(summary, indent=2, sort_keys=True))
    print("SCOPED_UNIT_TESTS: PASS (6 tests)")
    print("BOUNDARY: PSh(L,Set) only; product-site lift remains OPEN")
    print("ADMISSION: Ring 4 / NOT LICENSED / INTERNAL ONLY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
