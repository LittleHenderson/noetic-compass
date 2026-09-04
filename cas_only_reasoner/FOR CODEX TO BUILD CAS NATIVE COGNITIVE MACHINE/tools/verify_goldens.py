"""Verify retained goldens against their hashes and a fresh deterministic run."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
import sys
from typing import Any, Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from cncm.canonical import canonical_json
from cncm.engine import CognitiveMachine
from cncm.math_api import find_math_counterexample
from cncm.math_engine import solve_linear_equation
from cncm.math_kernel import check_math_step
from cncm.math_model import (
    MATH_CHECKER_VERSION,
    MATH_THEORY_ID,
    MathClaim,
    MathClaimStatus,
    MathStepOperation,
    MathStepProposal,
    Provenance,
)
from cncm.math_parser import parse_math_statement
from cncm.model import ProblemPacket, RUNTIME_VERSION, TerminalStatus
from cncm.verification import verify_bundle


FIXTURE_NAME = re.compile(r"^[A-Za-z0-9_-]+$")
GOLDEN_MANIFEST_VERSION = "cncm.golden-manifest/0.2"
MATH_GOLDEN_VERSION = "cncm.math-golden/0.1"
DETERMINISM_INPUTS = [
    "problem_packet",
    "initial_episodic_memory",
    "runtime_version",
    "seed",
    "scheduler_policy",
]
MATH_DETERMINISM_INPUTS = [
    "math_fixture_definition",
    "runtime_version",
    "math_checker_version",
    "math_theory_id",
]
EXPECTED_RRK_FIXTURES = {
    "branch_rollback",
    "contradiction",
    "deduction",
    "memory_recall",
    "missing_information",
    "rpm_failure",
    "rpm_recursion",
    "transitive_reasoning",
}
EXPECTED_MATH_STATUS = {
    "algebra": "EXECUTABLE",
    "arithmetic": "EXECUTABLE",
    "contradiction": "EXECUTABLE",
    "counterexamples": "EXECUTABLE",
    "recursive_learning": "CONTRACT_ONLY",
    "transitive_relations": "EXECUTABLE",
}


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def encoded(value: Any) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    ).encode("utf-8")


def validate_math_fixture(document: Mapping[str, Any], category: str) -> None:
    required = {
        "schema_version",
        "fixture_id",
        "category",
        "operation",
        "input",
        "expected",
        "runtime_status",
    }
    if set(document) != required:
        raise ValueError(f"{category}: math fixture fields do not match the frozen shape")
    if document.get("schema_version") != "cncm.math-fixture/0.1":
        raise ValueError(f"{category}: math fixture schema_version mismatch")
    if document.get("category") != category:
        raise ValueError(f"{category}: math fixture category does not match its directory")
    if document.get("runtime_status") != EXPECTED_MATH_STATUS.get(category):
        raise ValueError(f"{category}: math fixture runtime_status mismatch")
    for field in ("fixture_id", "operation"):
        if not isinstance(document.get(field), str) or not document[field]:
            raise ValueError(f"{category}: {field} must be a nonempty string")
    if not isinstance(document.get("input"), Mapping):
        raise ValueError(f"{category}: input must be an object")
    if not isinstance(document.get("expected"), Mapping):
        raise ValueError(f"{category}: expected must be an object")


def validate_math_expectation(
    document: Mapping[str, Any],
    output: Mapping[str, Any],
) -> None:
    expected = document["expected"]
    operation = document["operation"]
    if operation == "solve_linear":
        if output.get("terminal_status") != expected.get("terminal_status"):
            raise ValueError(f"{document['fixture_id']}: terminal status differs from fixture")
        if output.get("solution") != expected.get("solution"):
            raise ValueError(f"{document['fixture_id']}: solution differs from fixture")
        minimum = expected.get("minimum_checked_steps", 0)
        if len(output.get("checked_steps", ())) < minimum:
            raise ValueError(f"{document['fixture_id']}: too few checked steps")
    elif operation == "counterexample":
        if output.get("status") != expected.get("status"):
            raise ValueError(f"{document['fixture_id']}: status differs from fixture")
        if output.get("assignment") != expected.get("assignment"):
            raise ValueError(f"{document['fixture_id']}: assignment differs from fixture")
    elif operation == "check_transitive_equal":
        if output.get("accepted") != expected.get("accepted"):
            raise ValueError(f"{document['fixture_id']}: acceptance differs from fixture")


def execute_math_fixture(document: Mapping[str, Any]) -> dict[str, Any]:
    if document.get("runtime_status") != "EXECUTABLE":
        raise ValueError("only EXECUTABLE math fixtures may be executed")
    fixture_input = document["input"]
    operation = document["operation"]
    if operation == "solve_linear":
        output = solve_linear_equation(
            fixture_input["notation"],
            fixture_input["variable"],
        ).to_dict()
    elif operation == "counterexample":
        output = find_math_counterexample(
            fixture_input["notation"],
            fixture_input["bounds"],
            max_assignments=fixture_input["max_assignments"],
        ).to_dict()
    elif operation == "check_transitive_equal":
        variables = tuple(fixture_input["variables"])
        claims = tuple(
            MathClaim.create(
                statement=parse_math_statement(item, declared_variables=variables),
                status=MathClaimStatus.GIVEN,
                provenance=(Provenance("fixture", document["fixture_id"]),),
            )
            for item in fixture_input["premises"]
        )
        proposal = MathStepProposal.create(
            operation=MathStepOperation.TRANSITIVE_EQUAL,
            premise_claim_ids=(claims[0].claim_id, claims[1].claim_id),
            proposed_conclusion=parse_math_statement(
                fixture_input["conclusion"],
                declared_variables=variables,
            ),
        )
        output = check_math_step(proposal, claims).to_dict()
    else:
        raise ValueError(f"unsupported executable math operation: {operation}")
    validate_math_expectation(document, output)
    return output


def expected_math_artifact(
    document: Mapping[str, Any],
    *,
    fixture_sha256: str,
    source_spec_sha256: str,
) -> dict[str, Any]:
    base = {
        "schema_version": MATH_GOLDEN_VERSION,
        "source_spec_sha256": source_spec_sha256,
        "fixture_sha256": fixture_sha256,
        "fixture_definition": dict(document),
    }
    if document["runtime_status"] == "CONTRACT_ONLY":
        return {**base, "contract_only": True}
    return {**base, "output": execute_math_fixture(document)}


def main() -> int:
    errors: list[str] = []
    golden_root = PROJECT_ROOT / "golden"
    manifest_path = golden_root / "manifest.json"
    try:
        manifest = load_json(manifest_path)
    except (OSError, ValueError, TypeError) as exc:
        print(canonical_json({"valid": False, "errors": [f"manifest: {exc}"]}))
        return 1

    if manifest.get("schema_version") != GOLDEN_MANIFEST_VERSION:
        errors.append("manifest schema_version mismatch")
    if manifest.get("runtime_version") != RUNTIME_VERSION:
        errors.append("manifest runtime_version mismatch")
    if manifest.get("determinism_inputs") != DETERMINISM_INPUTS:
        errors.append("manifest determinism_inputs mismatch")
    if manifest.get("math_determinism_inputs") != MATH_DETERMINISM_INPUTS:
        errors.append("manifest math_determinism_inputs mismatch")
    if manifest.get("math_contract") != {
        "checker_version": MATH_CHECKER_VERSION,
        "theory_id": MATH_THEORY_ID,
    }:
        errors.append("manifest math_contract mismatch")

    source = manifest.get("source_spec", {})
    if not isinstance(source, dict):
        source = {}
        errors.append("source spec must be an object")
    source_path = (PROJECT_ROOT / str(source.get("path", ""))).resolve()
    expected_source = (PROJECT_ROOT / "cas_reasoner.txt").resolve()
    source_sha = ""
    if source_path != expected_source:
        errors.append("source spec path escaped the frozen source location")
    else:
        try:
            source_bytes = source_path.read_bytes()
            source_sha = sha256(source_bytes).hexdigest()
            if len(source_bytes) != source.get("bytes"):
                errors.append("source spec byte count mismatch")
            if source_sha != source.get("sha256"):
                errors.append("source spec SHA-256 mismatch")
        except OSError as exc:
            errors.append(f"source spec: {exc}")

    entries = manifest.get("entries")
    if not isinstance(entries, list):
        entries = []
        errors.append("manifest entries must be a list")
    actual_fixtures = {
        path.parent.name for path in (PROJECT_ROOT / "fixtures").glob("*/problem.json")
    }
    if actual_fixtures != EXPECTED_RRK_FIXTURES:
        errors.append("current RRK fixture set differs from the frozen eight")
    retained_fixture_list = [
        entry.get("fixture") for entry in entries if isinstance(entry, dict)
    ]
    retained_fixtures = set(retained_fixture_list)
    if len(retained_fixture_list) != len(retained_fixtures):
        errors.append("manifest contains duplicate fixture entries")
    if retained_fixtures != actual_fixtures:
        errors.append("manifest fixture set differs from the current fixture set")
    for directory in ("expected_traces", "expected_final_states", "evidence"):
        retained_names = {path.stem for path in (golden_root / directory).glob("*.json")}
        if retained_names != actual_fixtures:
            errors.append(f"{directory} artifact set differs from the current fixture set")
    expected_failure_names = {
        entry.get("fixture")
        for entry in entries
        if isinstance(entry, dict) and entry.get("terminal_status") != TerminalStatus.CONCLUDED.value
    }
    retained_failure_names = {
        path.stem for path in (golden_root / "expected_failures").glob("*.json")
    }
    if retained_failure_names != expected_failure_names:
        errors.append("expected_failures artifact set differs from non-concluded fixtures")

    for entry in entries:
        if not isinstance(entry, dict):
            errors.append("manifest entry is not an object")
            continue
        fixture = entry.get("fixture")
        if not isinstance(fixture, str) or not FIXTURE_NAME.fullmatch(fixture):
            errors.append(f"unsafe fixture identifier: {fixture!r}")
            continue
        problem_path = PROJECT_ROOT / "fixtures" / fixture / "problem.json"
        artifact_paths = {
            "trace_sha256": golden_root / "expected_traces" / f"{fixture}.json",
            "final_state_sha256": golden_root / "expected_final_states" / f"{fixture}.json",
            "evidence_sha256": golden_root / "evidence" / f"{fixture}.json",
        }
        try:
            if file_sha256(problem_path) != entry.get("problem_sha256"):
                errors.append(f"{fixture}: problem hash mismatch")
            for field, path in artifact_paths.items():
                if file_sha256(path) != entry.get(field):
                    errors.append(f"{fixture}: {field} mismatch")
            problem = ProblemPacket.from_dict(load_json(problem_path))
            result = CognitiveMachine().run(problem)
            retained_trace = load_json(artifact_paths["trace_sha256"])
            retained_state = load_json(artifact_paths["final_state_sha256"])
            retained_evidence = load_json(artifact_paths["evidence_sha256"])
            if retained_trace != [event.to_dict() for event in result.trace]:
                errors.append(f"{fixture}: fresh trace differs from retained trace")
            if retained_state != result.final_state.to_dict():
                errors.append(f"{fixture}: fresh final state differs from retained state")
            if retained_evidence != result.evidence:
                errors.append(f"{fixture}: fresh evidence differs from retained evidence")
            verification = verify_bundle(result.to_dict())
            if not verification.valid:
                errors.append(f"{fixture}: fresh bundle verification failed")
            if result.terminal_status.value != entry.get("terminal_status"):
                errors.append(f"{fixture}: terminal status mismatch")
            if result.final_state.state_hash != entry.get("final_state_hash"):
                errors.append(f"{fixture}: final state identity mismatch")
            if result.final_state.trace_head != entry.get("trace_head"):
                errors.append(f"{fixture}: trace head mismatch")
            if result.evidence["evidence_digest"] != entry.get("evidence_digest"):
                errors.append(f"{fixture}: evidence identity mismatch")
            failure_hash = entry.get("expected_failure_sha256")
            if result.terminal_status is TerminalStatus.CONCLUDED:
                if failure_hash is not None:
                    errors.append(f"{fixture}: concluded run retained a failure hash")
            else:
                failure_path = golden_root / "expected_failures" / f"{fixture}.json"
                if file_sha256(failure_path) != failure_hash:
                    errors.append(f"{fixture}: expected failure hash mismatch")
                expected_failure = {
                    "schema_version": "cncm.expected-failure/0.1",
                    "fixture": fixture,
                    "terminal_status": result.terminal_status.value,
                    "lacunae": list(result.final_state.global_workspace.lacunae),
                    "diagnostics": list(result.final_state.global_workspace.diagnostics),
                    "final_state_hash": result.final_state.state_hash,
                    "trace_head": result.final_state.trace_head,
                }
                if load_json(failure_path) != expected_failure:
                    errors.append(f"{fixture}: expected failure artifact mismatch")
        except (OSError, KeyError, TypeError, ValueError) as exc:
            errors.append(f"{fixture}: {type(exc).__name__}: {exc}")

    math_entries = manifest.get("math_entries")
    if not isinstance(math_entries, list):
        math_entries = []
        errors.append("manifest math_entries must be a list")
    actual_math_paths = {
        path.parent.name: path
        for path in (PROJECT_ROOT / "fixtures" / "math").glob("*/case.json")
    }
    actual_math_fixtures = set(actual_math_paths)
    if actual_math_fixtures != set(EXPECTED_MATH_STATUS):
        errors.append("current math fixture set differs from the frozen six")
    retained_math_list = [
        entry.get("fixture") for entry in math_entries if isinstance(entry, dict)
    ]
    retained_math_fixtures = set(retained_math_list)
    if len(retained_math_list) != len(retained_math_fixtures):
        errors.append("manifest contains duplicate math fixture entries")
    if retained_math_fixtures != actual_math_fixtures:
        errors.append("manifest math fixture set differs from the current fixture set")
    retained_math_artifacts = {
        path.stem for path in (golden_root / "math").glob("*.json")
    }
    if retained_math_artifacts != actual_math_fixtures:
        errors.append("math golden artifact set differs from the current fixture set")

    math_entry_fields = {
        "fixture",
        "fixture_id",
        "operation",
        "runtime_status",
        "case_path",
        "case_sha256",
        "source_spec_sha256",
        "artifact_path",
        "artifact_sha256",
        "output_sha256",
    }
    for entry in math_entries:
        if not isinstance(entry, dict):
            errors.append("manifest math entry is not an object")
            continue
        if set(entry) != math_entry_fields:
            errors.append(f"{entry.get('fixture')}: math manifest fields mismatch")
            continue
        fixture = entry.get("fixture")
        if not isinstance(fixture, str) or not FIXTURE_NAME.fullmatch(fixture):
            errors.append(f"unsafe math fixture identifier: {fixture!r}")
            continue
        case_path = PROJECT_ROOT / "fixtures" / "math" / fixture / "case.json"
        artifact_path = golden_root / "math" / f"{fixture}.json"
        try:
            expected_case_relative = case_path.relative_to(PROJECT_ROOT).as_posix()
            expected_artifact_relative = artifact_path.relative_to(golden_root).as_posix()
            if entry["case_path"] != expected_case_relative:
                errors.append(f"{fixture}: case path mismatch")
            if entry["artifact_path"] != expected_artifact_relative:
                errors.append(f"{fixture}: artifact path mismatch")
            case_sha = file_sha256(case_path)
            if entry["case_sha256"] != case_sha:
                errors.append(f"{fixture}: case hash mismatch")
            if entry["source_spec_sha256"] != source_sha:
                errors.append(f"{fixture}: source spec binding mismatch")
            document = load_json(case_path)
            if not isinstance(document, Mapping):
                raise ValueError("math fixture must contain one object")
            validate_math_fixture(document, fixture)
            if entry["fixture_id"] != document["fixture_id"]:
                errors.append(f"{fixture}: fixture_id mismatch")
            if entry["operation"] != document["operation"]:
                errors.append(f"{fixture}: operation mismatch")
            if entry["runtime_status"] != document["runtime_status"]:
                errors.append(f"{fixture}: runtime_status mismatch")
            if file_sha256(artifact_path) != entry["artifact_sha256"]:
                errors.append(f"{fixture}: math artifact hash mismatch")
            retained_artifact = load_json(artifact_path)
            fresh_artifact = expected_math_artifact(
                document,
                fixture_sha256=case_sha,
                source_spec_sha256=source_sha,
            )
            if retained_artifact != fresh_artifact:
                errors.append(f"{fixture}: fresh math output differs from retained artifact")
            if document["runtime_status"] == "EXECUTABLE":
                output_sha = sha256(encoded(fresh_artifact["output"])).hexdigest()
                if entry["output_sha256"] != output_sha:
                    errors.append(f"{fixture}: math output hash mismatch")
                if "contract_only" in retained_artifact:
                    errors.append(f"{fixture}: executable artifact marked contract-only")
            else:
                if entry["output_sha256"] is not None:
                    errors.append(f"{fixture}: contract-only fixture retained an output hash")
                if retained_artifact.get("contract_only") is not True:
                    errors.append(f"{fixture}: contract-only marker missing")
                if "output" in retained_artifact:
                    errors.append(f"{fixture}: contract-only fixture retained executable output")
        except (OSError, KeyError, TypeError, ValueError) as exc:
            errors.append(f"{fixture}: {type(exc).__name__}: {exc}")

    report = {
        "schema_version": "cncm.golden-verification/0.2",
        "valid": not errors,
        "fixture_count": len(entries) + len(math_entries),
        "rrk_fixture_count": len(entries),
        "math_fixture_count": len(math_entries),
        "math_executable_count": sum(
            isinstance(entry, dict) and entry.get("runtime_status") == "EXECUTABLE"
            for entry in math_entries
        ),
        "math_contract_only_count": sum(
            isinstance(entry, dict) and entry.get("runtime_status") == "CONTRACT_ONLY"
            for entry in math_entries
        ),
        "manifest_sha256": file_sha256(manifest_path),
        "errors": errors,
    }
    print(canonical_json(report))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
