"""Regenerate deterministic fixture traces, states, evidence, and manifest."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Any, Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

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


GOLDEN_MANIFEST_VERSION = "cncm.golden-manifest/0.2"
MATH_GOLDEN_VERSION = "cncm.math-golden/0.1"
EXPECTED_RRK_FIXTURES = (
    "branch_rollback",
    "contradiction",
    "deduction",
    "memory_recall",
    "missing_information",
    "rpm_failure",
    "rpm_recursion",
    "transitive_reasoning",
)
EXPECTED_MATH_STATUS = {
    "algebra": "EXECUTABLE",
    "arithmetic": "EXECUTABLE",
    "contradiction": "EXECUTABLE",
    "counterexamples": "EXECUTABLE",
    "recursive_learning": "CONTRACT_ONLY",
    "transitive_relations": "EXECUTABLE",
}
MATH_DETERMINISM_INPUTS = [
    "math_fixture_definition",
    "runtime_version",
    "math_checker_version",
    "math_theory_id",
]


def encoded(value) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode("utf-8")


def write_json(path: Path, value) -> str:
    payload = encoded(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return sha256(payload).hexdigest()


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
    expected_status = EXPECTED_MATH_STATUS.get(category)
    if expected_status is None:
        raise ValueError(f"unexpected math fixture category: {category}")
    if document.get("runtime_status") != expected_status:
        raise ValueError(f"{category}: math fixture runtime_status mismatch")
    for field in ("fixture_id", "operation"):
        if not isinstance(document.get(field), str) or not document[field]:
            raise ValueError(f"{category}: {field} must be a nonempty string")
    if not isinstance(document.get("input"), Mapping):
        raise ValueError(f"{category}: input must be an object")
    if not isinstance(document.get("expected"), Mapping):
        raise ValueError(f"{category}: expected must be an object")


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


def math_golden_artifact(
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
    fixtures_root = PROJECT_ROOT / "fixtures"
    golden_root = PROJECT_ROOT / "golden"
    source_path = PROJECT_ROOT / "cas_reasoner.txt"
    source_bytes = source_path.read_bytes()
    source_sha = sha256(source_bytes).hexdigest()
    problem_paths = sorted(fixtures_root.glob("*/problem.json"))
    problem_names = tuple(path.parent.name for path in problem_paths)
    if problem_names != EXPECTED_RRK_FIXTURES:
        raise ValueError(f"RRK fixture set differs from the frozen set: {problem_names!r}")
    entries = []
    for problem_path in problem_paths:
        fixture_name = problem_path.parent.name
        document = json.loads(problem_path.read_text(encoding="utf-8"))
        problem = ProblemPacket.from_dict(document)
        result = CognitiveMachine().run(problem)
        trace_path = golden_root / "expected_traces" / f"{fixture_name}.json"
        state_path = golden_root / "expected_final_states" / f"{fixture_name}.json"
        evidence_path = golden_root / "evidence" / f"{fixture_name}.json"
        trace_sha = write_json(trace_path, [item.to_dict() for item in result.trace])
        state_sha = write_json(state_path, result.final_state.to_dict())
        evidence_sha = write_json(evidence_path, result.evidence)
        failure_sha = None
        if result.terminal_status is not TerminalStatus.CONCLUDED:
            failure_path = golden_root / "expected_failures" / f"{fixture_name}.json"
            failure_sha = write_json(
                failure_path,
                {
                    "schema_version": "cncm.expected-failure/0.1",
                    "fixture": fixture_name,
                    "terminal_status": result.terminal_status.value,
                    "lacunae": list(result.final_state.global_workspace.lacunae),
                    "diagnostics": list(result.final_state.global_workspace.diagnostics),
                    "final_state_hash": result.final_state.state_hash,
                    "trace_head": result.final_state.trace_head,
                },
            )
        entries.append(
            {
                "fixture": fixture_name,
                "problem_sha256": sha256(problem_path.read_bytes()).hexdigest(),
                "terminal_status": result.terminal_status.value,
                "trace_sha256": trace_sha,
                "final_state_sha256": state_sha,
                "evidence_sha256": evidence_sha,
                "expected_failure_sha256": failure_sha,
                "final_state_hash": result.final_state.state_hash,
                "trace_head": result.final_state.trace_head,
                "evidence_digest": result.evidence["evidence_digest"],
            }
        )
    math_paths = sorted((fixtures_root / "math").glob("*/case.json"))
    math_categories = tuple(path.parent.name for path in math_paths)
    if math_categories != tuple(sorted(EXPECTED_MATH_STATUS)):
        raise ValueError(
            f"math fixture set differs from the frozen set: {math_categories!r}"
        )
    math_entries = []
    for case_path in math_paths:
        category = case_path.parent.name
        document = json.loads(case_path.read_text(encoding="utf-8"))
        if not isinstance(document, Mapping):
            raise ValueError(f"{category}: math fixture must be one object")
        validate_math_fixture(document, category)
        case_sha = sha256(case_path.read_bytes()).hexdigest()
        artifact = math_golden_artifact(
            document,
            fixture_sha256=case_sha,
            source_spec_sha256=source_sha,
        )
        artifact_relative = Path("math") / f"{category}.json"
        artifact_sha = write_json(golden_root / artifact_relative, artifact)
        output_sha = (
            sha256(encoded(artifact["output"])).hexdigest()
            if document["runtime_status"] == "EXECUTABLE"
            else None
        )
        math_entries.append(
            {
                "fixture": category,
                "fixture_id": document["fixture_id"],
                "operation": document["operation"],
                "runtime_status": document["runtime_status"],
                "case_path": case_path.relative_to(PROJECT_ROOT).as_posix(),
                "case_sha256": case_sha,
                "source_spec_sha256": source_sha,
                "artifact_path": artifact_relative.as_posix(),
                "artifact_sha256": artifact_sha,
                "output_sha256": output_sha,
            }
        )
    manifest = {
        "schema_version": GOLDEN_MANIFEST_VERSION,
        "runtime_version": RUNTIME_VERSION,
        "source_spec": {
            "path": "cas_reasoner.txt",
            "bytes": len(source_bytes),
            "sha256": source_sha,
        },
        "determinism_inputs": [
            "problem_packet",
            "initial_episodic_memory",
            "runtime_version",
            "seed",
            "scheduler_policy",
        ],
        "math_contract": {
            "checker_version": MATH_CHECKER_VERSION,
            "theory_id": MATH_THEORY_ID,
        },
        "math_determinism_inputs": MATH_DETERMINISM_INPUTS,
        "entries": entries,
        "math_entries": math_entries,
    }
    manifest_path = golden_root / "manifest.json"
    manifest_sha = write_json(manifest_path, manifest)
    print(
        json.dumps(
            {
                "generated": len(entries),
                "math_generated": len(math_entries),
                "math_executable": sum(
                    entry["runtime_status"] == "EXECUTABLE" for entry in math_entries
                ),
                "math_contract_only": sum(
                    entry["runtime_status"] == "CONTRACT_ONLY"
                    for entry in math_entries
                ),
                "manifest": str(manifest_path),
                "manifest_sha256": manifest_sha,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
