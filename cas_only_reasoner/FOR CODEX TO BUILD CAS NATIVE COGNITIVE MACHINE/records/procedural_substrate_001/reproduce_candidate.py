"""Reproduce a checked candidate in a fresh process; no native installation."""
import argparse
from fractions import Fraction
from hashlib import sha256
from itertools import permutations, product
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from cncm.canonical import canonical_json, digest
from cncm.procedural_qualification import (check_procedure_call, policy_document,
    qualify_procedure, select_finite_candidate, verify_checked_call, verify_qualification)
from cncm.procedural_substrate import ProcedureArtifact, execute_procedure, make_candidate


def require(condition, message):
    if not condition:
        raise ValueError(message)


def identities():
    paths = ["cncm/canonical.py", "cncm/model.py", "cncm/math_model.py",
        "cncm/math_parser.py", "cncm/math_normalize.py", "cncm/math_kernel.py",
        "cncm/procedural_substrate.py", "cncm/procedural_qualification.py",
        "records/procedural_substrate_001/reproduce_candidate.py"]
    return [{"path": name, "bytes": len((ROOT / name).read_bytes()),
             "sha256": sha256((ROOT / name).read_bytes()).hexdigest()} for name in paths]


def fraction_crosscheck():
    values = ("0", "2", "-3", "1/7")
    rows = []
    for order in permutations(("a", "b", "c")):
        for operation in ("ADD_EXACT", "SUBTRACT_EXACT"):
            artifact = make_candidate(order, operation)
            success = zero_division = 0
            for supplied in product(values, repeat=3):
                inputs = dict(zip(("a", "b", "c"), supplied, strict=True))
                left, right, divisor = (Fraction(inputs[key]) for key in order)
                actual = execute_procedure(artifact, inputs)
                if not divisor:
                    require(actual.status == "DIVISION_BY_ZERO", "ZERO_DIVISOR_NOT_REFUSED")
                    zero_division += 1
                else:
                    expected = (left + right if operation == "ADD_EXACT" else left - right) / divisor
                    require(actual.status == "SUCCESS" and Fraction(actual.output) == expected,
                            "INDEPENDENT_FRACTION_MISMATCH")
                    success += 1
            rows.append({"artifact_sha256": artifact.artifact_sha256,
                         "success": success, "zero_division": zero_division})
    return {"cases": sum(row["success"] + row["zero_division"] for row in rows),
            "candidates": rows, "reference": "Python standard-library fractions.Fraction"}


def produce():
    artifact, selection = select_finite_candidate()
    require(artifact is not None, "NO_UNIQUE_DEVELOPMENT_CANDIDATE")
    qualification = qualify_procedure(artifact)
    require(qualification["status"] == "ENGINEERING_PANEL_PASSED", "QUALIFICATION_FAILED")
    calls = [check_procedure_call(artifact, inputs, call_id=f"example-call-{i}",
             branch_id="example-parent") for i, inputs in enumerate((
             {"a": "3", "b": "5", "c": "26"}, {"a": "-4", "b": "7", "c": "13"}))]
    require([row["execution"]["outputs"] for row in calls] == [{"x": "7"}, {"x": "-3/2"}],
            "EXAMPLE_MISMATCH")
    return {"schema": "cncm.procedural-substrate-reproduction/0.1",
            "source_files": identities(), "policy": policy_document(),
            "artifact": artifact.to_dict(), "selection": selection,
            "qualification": qualification, "calls": calls,
            "independent_arithmetic": fraction_crosscheck(),
            "native_installation": False, "suspended_parent_resume": False,
            "claim_boundary": "Candidate byte reuse/checking only; no kernel journal or installed skill."}


def replay(bundle):
    require(bundle["source_files"] == identities(), "SOURCE_IDENTITY_MISMATCH")
    artifact = ProcedureArtifact.from_dict(bundle["artifact"])
    require(bundle["policy"] == policy_document(), "POLICY_MISMATCH")
    require(verify_qualification(artifact, bundle["qualification"]), "QUALIFICATION_REPLAY_FAILED")
    for i, inputs in enumerate(({"a": "3", "b": "5", "c": "26"},
                                {"a": "-4", "b": "7", "c": "13"})):
        require(verify_checked_call(artifact, inputs, bundle["calls"][i],
                    call_id=f"example-call-{i}", branch_id="example-parent"), "CALL_REPLAY_FAILED")
    # Compare every field, including selection, counters and all refusal results.
    require(canonical_json(produce()) == canonical_json(bundle), "FULL_REPRODUCTION_MISMATCH")
    return {"schema": "cncm.procedural-substrate-fresh-process-replay/0.1",
            "status": "REPRODUCED", "bundle_digest": digest(bundle),
            "source_files": identities(), "selected_artifact_sha256": artifact.artifact_sha256,
            "native_installation": False, "kernel_recovery": False,
            "claim_boundary": bundle["claim_boundary"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = replay(json.loads(Path(args.replay).read_bytes())) if args.replay else produce()
    output = Path(args.output).resolve()
    require(output.is_relative_to(ROOT), "OUTPUT_OUTSIDE_HOMEBASE")
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"path": str(output), "bytes": output.stat().st_size,
                      "sha256": sha256(output.read_bytes()).hexdigest(),
                      "status": result.get("status", "CANDIDATE_REPRODUCED")}))


if __name__ == "__main__":
    main()
