"""A fixed saved-procedure experiment, not a general compiler or runtime.

The existing META2 CALL instruction is preserved. Package resolution happens
before execution; no native memory reference, opcode or permission is added.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json

from .registry import checked_codec, validate_package


def _digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=True, allow_nan=False).encode("ascii")).hexdigest()


def link_demonstration(package, *, expected_digest, trusted_compatibility, permitted_cjts):
    """Link B into a new A→CALL(B)→CALL(B) parent, returning the first B.

    The caller supplies identity and permission expectations. Neither the
    package nor this link receipt can grant execution authority or qualification.
    """
    if (not isinstance(permitted_cjts, (list, tuple, set, frozenset))
            or any(type(value) is not str for value in permitted_cjts)
            or not {"A", "B"}.issubset(set(permitted_cjts))):
        raise ValueError("DEMONSTRATION_PARENT_SCOPE_DENIED")
    checked = validate_package(package, expected_digest=expected_digest,
                               trusted_compatibility=trusted_compatibility,
                               permitted_cjts=permitted_cjts)
    # Validation verifies/imports the pinned, pure META2 IR dependency first.
    from cas_meta2.ir import validate_program
    validate_action = checked_codec().validate_action
    original = deepcopy(checked["program"])
    source_name = original["entry"]
    # p0 is inside the unchanged META2 action codec's declared vocabulary.
    child_name = "p0"
    program = {
        "schema": "cas-meta2-program/0.1", "entry": "main", "procedures": {
            "main": {
                "input": "arg", "allowed_cjts": ["A", "B"], "steps": [
                    {"kind": "RUN", "cjt_id": "A", "input": "arg", "output": "v0"},
                    {"kind": "CALL", "procedure": child_name, "input": "v0", "output": "v1"},
                    {"kind": "CALL", "procedure": child_name, "input": "v0", "output": "v2"},
                ], "return": "v1",
            },
            child_name: deepcopy(original["procedures"][source_name]),
        },
    }
    stats = validate_program(program)
    validate_action({"program": program, "binding": 0})
    if stats["expanded_run_count"] != 3 or stats["max_call_depth"] != 2:
        raise ValueError("FIXED_DEMONSTRATION_STRUCTURE_MISMATCH")
    body = {
        "schema": "cas-meta3-procedure-link/0.1", "package_sha256": expected_digest,
        "source_program_sha256": _digest(original),
        "linked_program_sha256": _digest(program),
        "procedure_mapping": {source_name: child_name},
        "cognitive_address": "package:" + expected_digest + "/" + source_name,
        "call_sites": [
            {"caller": "main", "pc": 1, "functional_address": "entry:main/steps/1", "procedure": child_name},
            {"caller": "main", "pc": 2, "functional_address": "entry:main/steps/2", "procedure": child_name},
        ],
        "granted_cjts": sorted(set(permitted_cjts)), "required_parent_cjts": ["A", "B"],
        "compatibility": deepcopy(trusted_compatibility),
        "status": "LINKED_NOT_EXECUTED", "qualification": "UNQUALIFIED",
        "native_memory_refs_added": False, "new_opcodes_added": False,
        "native_execution_performed": False, "learning_performed": False,
        "boundary": "Structural linking only. Actual native execution, outputs and persistence need separate evidence.",
    }
    return {"program": program, "link_receipt": {**body, "receipt_sha256": _digest(body)}}


def retrieve_and_link(registry, *, expected_digest, trusted_compatibility, permitted_cjts):
    """Resolve a package before the caller constructs the native executor."""
    package = registry.retrieve(expected_digest, trusted_compatibility=trusted_compatibility,
                                permitted_cjts=permitted_cjts)
    return link_demonstration(package, expected_digest=expected_digest,
                              trusted_compatibility=trusted_compatibility,
                              permitted_cjts=permitted_cjts)
