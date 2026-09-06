"""Resolve a stored learned candidate into a bounded repeated-call parent.

This prepares a reuse experiment, not learned composition or activation. The
saved program is renamed structurally, never inlined, retrained or rewritten.
"""
from copy import deepcopy

from . import learned_package as packages
from . import learning_evidence as evidence
from .learned_store import LearnedCandidateStore


class LinkError(ValueError):
    pass


def require(condition, code):
    if not condition:
        raise LinkError(code)


def retrieve_for_reuse(path, *, expected_digest, call_count=2, return_call=0,
                       max_expanded_runs=256, **trust_inputs):
    """Retrieve with fresh evidence checks, then prepare explicit CALLs.

    All calls receive the same original observation reference. The selected
    call's exact returned Effect remains the parent result, even if later
    calls also execute. Runtime identities and actual outputs need AWS tests.
    """
    require(type(call_count) is int and 1 <= call_count <= 4, "REUSE_CALL_COUNT_INVALID")
    require(type(return_call) is int and 0 <= return_call < call_count, "REUSE_RETURN_CALL_INVALID")
    require(type(max_expanded_runs) is int and 1 <= max_expanded_runs <= 256, "REUSE_COMPUTE_CEILING_INVALID")
    retrieved = LearnedCandidateStore(path).retrieve(expected_digest, **trust_inputs)
    package = retrieved["package"]
    original = package["program"]
    order = [original["entry"], *sorted(name for name in original["procedures"] if name != original["entry"])]
    with packages._pure_dependencies() as (ir, codec, topology):
        names = [name for name in codec.PROCEDURE_NAMES if name != "main"]
        require(len(order) <= len(names), "REUSE_PARENT_PROCEDURE_CAPACITY")
        mapping = dict(zip(order, names))
        children = {}
        for old in order:
            child = deepcopy(original["procedures"][old])
            for step in child["steps"]:
                if step["kind"] == "CALL":
                    step["procedure"] = mapping[step["procedure"]]
            children[mapping[old]] = child
        parent = {"input": "arg", "allowed_cjts": list(package["required_cjts"]),
            "steps": [{"kind": "CALL", "procedure": mapping[original["entry"]],
                       "input": "arg", "output": "v" + str(index)} for index in range(call_count)],
            "return": "v" + str(return_call)}
        program = {"schema": original["schema"], "entry": "main", "procedures": {"main": parent, **children}}
        action = {"program": program, "binding": package["binding"]}
        bounds = ir.validate_program(program)
        codec.validate_action(action)
        require(bounds["expanded_run_count"] <= max_expanded_runs, "REUSE_COMPUTE_CEILING_EXCEEDED")
        source_plan = topology.check_native_topology(original)
        linked_plan = topology.check_native_topology(program)
        width = len(source_plan["runs"])
        expected_edges = [{"cjt_id": row["cjt_id"],
            "input_node": -1 if row["input_node"] == -1 else copy * width + row["input_node"]}
            for copy in range(call_count) for row in source_plan["runs"]]
        actual_edges = [{key: row[key] for key in ("cjt_id", "input_node")} for row in linked_plan["runs"]]
        expected_return = return_call * width + source_plan["return_node"]
        require(actual_edges == expected_edges and linked_plan["return_node"] == expected_return,
                "REUSE_DEPENDENCY_OR_RETURN_CHANGED")
    body = {"schema": "cas-meta3-learned-link/0.1", "status": "PREPARED_FOR_REUSE_TEST",
        "package_sha256": expected_digest, "source_program_sha256": evidence.digest(original),
        "source_handoff_sha256": retrieved["handoff"]["receipt_sha256"],
        "storage_receipt_sha256": retrieved["storage_receipt"]["receipt_sha256"],
        "linked_action_sha256": evidence.digest(action), "procedure_mapping": mapping,
        "package_address": "package:" + expected_digest + "/" + original["entry"],
        "call_sites": [{"functional_address": "entry:main/steps/" + str(index),
                        "procedure": mapping[original["entry"]], "call_ordinal": index}
                       for index in range(call_count)],
        "call_count": call_count, "return_call": return_call,
        "expected_native_edges": expected_edges, "expected_return_node": expected_return,
        "max_expanded_runs": max_expanded_runs, "derived_bounds": bounds,
        "qualification_status": "UNQUALIFIED", "promotion_granted": False,
        "native_execution_performed": False, "learning_performed": False,
        "boundary": "Deterministic reuse-test preparation. Runtime Effect identities, new-input outcomes and learned parent composition remain unproven."}
    return {"action": action, "link_receipt": {**body, "receipt_sha256": evidence.digest(body)}}
