"""Pure linker checks with FIXTURE_ONLY identities, never GPU qualification.

Synthetic compatibility digests below do not identify a measured model. These
tests exercise data, scope, package storage and the pinned pure action checker.
They neither construct nor execute a native model.
"""
from __future__ import annotations

import ast
import builtins
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sys

import pytest

from cas_meta3 import linker
from cas_meta3.registry import (
    BASELINE_SHA, IR_SCHEMA, META2_SOURCE_SHA, PACKAGE_SCHEMA,
    ProcedureRegistry, canonical_package, package_digest,
)


pytestmark = pytest.mark.not_gpu
FIXTURE_BOUNDARY = "FIXTURE_ONLY_UNQUALIFIED_METADATA_NOT_A_MEASURED_MODEL"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def digest(value):
    return sha256(canonical(value)).hexdigest()


def fixture_hash(label):
    return sha256((FIXTURE_BOUNDARY + ":" + label).encode("ascii")).hexdigest()


def make_package(entry="fixture_saved_b"):
    """An authored B-only fixture, not a procedure learned by any model."""
    program = {"schema": IR_SCHEMA, "entry": entry, "procedures": {
        entry: {"input": "arg", "allowed_cjts": ["B"], "steps": [
            {"kind": "RUN", "cjt_id": "B", "input": "arg", "output": "v0"},
        ], "return": "v0"},
    }}
    compatibility = {
        "baseline_sha": BASELINE_SHA, "meta2_source_sha": META2_SOURCE_SHA,
        "ir_schema": IR_SCHEMA,
        **{name: fixture_hash(name) for name in (
            "native_schema_sha256", "model_digest", "parameter_bytes_sha256",
            "software_digest", "topology_sha256")},
        "operation_contracts": {"^6": fixture_hash("operation-6")},
        "decoder_contracts": {name: fixture_hash("decoder-" + name) for name in ("A", "B")},
    }
    return {
        "schema": PACKAGE_SCHEMA, "kind": "UNARY_CJT_PROCEDURE", "program": program,
        "io": {port: {"kind": "ACCEPTED_EFFECT", "producer_cjt_id": producer,
                      "dtype": "float32", "shape": [1, 2, 4]}
               for port, producer in (("input", "A"), ("output", "B"))},
        "required_cjts": ["B"], "compatibility": compatibility,
        "provenance": {"source_program_sha256": digest(program),
                       "source_receipt_sha256": None, "parent_package_sha256": None},
    }


def options(package, *, permitted_cjts=("A", "B")):
    return {"expected_digest": package_digest(package),
            "trusted_compatibility": deepcopy(package["compatibility"]),
            "permitted_cjts": permitted_cjts}


@pytest.fixture(autouse=True)
def no_neural_imports(monkeypatch):
    """Fail loudly if a pure test accidentally reaches model work."""
    blocked = ("torch", "numpy", "casformer", "cas_cjt", "cas_meta1",
               "cas_meta2.policy", "cas_meta2.train", "cas_meta2.campaign")
    before = set(sys.modules)
    original = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if any(name == prefix or name.startswith(prefix + ".") for prefix in blocked):
            raise AssertionError("PURE_LINKER_TEST_ATTEMPTED_NEURAL_IMPORT:" + name)
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    yield
    added = set(sys.modules) - before
    assert not {name for name in added if any(
        name == prefix or name.startswith(prefix + ".") for prefix in blocked)}


def test_fixed_parent_uses_two_real_calls_and_returns_first_child():
    package = make_package()
    linked = linker.link_demonstration(package, **options(package))
    program = linked["program"]
    assert program["entry"] == "main"
    assert set(program["procedures"]) == {"main", "p0"}
    assert program["procedures"]["main"] == {
        "input": "arg", "allowed_cjts": ["A", "B"], "steps": [
            {"kind": "RUN", "cjt_id": "A", "input": "arg", "output": "v0"},
            {"kind": "CALL", "procedure": "p0", "input": "v0", "output": "v1"},
            {"kind": "CALL", "procedure": "p0", "input": "v0", "output": "v2"},
        ], "return": "v1",
    }
    assert program["procedures"]["p0"] == package["program"]["procedures"]["fixture_saved_b"]
    from cas_meta2.ir import validate_program
    stats = validate_program(program)
    assert (stats["procedure_count"], stats["instruction_count"],
            stats["expanded_instruction_count"], stats["expanded_run_count"],
            stats["max_call_depth"]) == (2, 4, 5, 3, 2)


def test_pinned_ir_plan_preserves_frames_earlier_input_and_selected_return():
    package = make_package()
    linked = linker.link_demonstration(package, **options(package))
    from cas_meta2.ir import expand_program
    events = expand_program(linked["program"])
    assert [event["kind"] for event in events] == [
        "ENTER", "RUN", "ENTER", "RUN", "RETURN", "ENTER", "RUN", "RETURN", "RETURN"]
    children = [event for event in events if event["kind"] == "ENTER"][1:]
    assert [event["procedure"] for event in children] == ["p0", "p0"]
    assert {event["input_ref"] for event in children} == {"entry:main/values/v0"}
    assert {event["parent_frame_address"] for event in children} == {"entry:main"}
    assert children[0]["frame_address"] != children[1]["frame_address"]
    assert [event["call_address"] for event in children] == [
        "entry:main/steps/1", "entry:main/steps/2"]
    assert [site["functional_address"] for site in linked["link_receipt"]["call_sites"]] == [
        event["call_address"] for event in children]
    returns = [event for event in events if event["kind"] == "RETURN"]
    assert [event["output_ref"] for event in returns] == [
        "entry:main/values/v1", "entry:main/values/v2", "$result"]
    assert returns[-1]["input_ref"] == "entry:main/values/v1"
    runs = [event for event in events if event["kind"] == "RUN"]
    assert [event["cjt_id"] for event in runs] == ["A", "B", "B"]
    assert len({event["address"] for event in events}) == len(events)


@pytest.mark.parametrize("entry", ["main", "p0", "saved_procedure_B"])
def test_arbitrary_ir_entry_maps_into_pinned_codec_vocabulary(entry):
    package = make_package(entry)
    linked = linker.link_demonstration(package, **options(package))
    from cas_meta2.codec import action_to_tokens, tokens_to_action, validate_action
    action = {"program": linked["program"], "binding": 0}
    validate_action(action)
    assert tokens_to_action(action_to_tokens(action)) == action
    assert linked["link_receipt"]["procedure_mapping"] == {entry: "p0"}
    assert set(linked["program"]["procedures"]) == {"main", "p0"}


def test_linked_action_passes_pure_native_admission_without_native_access(monkeypatch):
    package = make_package()
    linked = linker.link_demonstration(package, **options(package))
    from cas_meta2 import native

    def forbidden(*args, **kwargs):
        pytest.fail("PURE_ADMISSION_REACHED_NATIVE_MODEL_ACCESS")

    for name in ("_frozen", "NativeBackend", "execute_task", "reference_task"):
        monkeypatch.setattr(native, name, forbidden)
    public = {"problem": "Fixture only: call saved B twice using A, then return the first B.",
              "observations": [
                  {"slot": index, "tag": "fixture_slot_" + str(index),
                   "values": [index / 4 + offset / 32 for offset in range(8)]}
                  for index in range(3)]}
    plan = native.admit_action(public, {"program": linked["program"], "binding": 0})
    assert len(plan["runs"]) == 3
    assert plan["return_node"] == 1


def test_link_receipt_hashes_exact_canonical_bytes_and_claims_only_structure():
    package = make_package()
    kwargs = options(package)
    linked = linker.link_demonstration(package, **kwargs)
    receipt = linked["link_receipt"]
    assert receipt["schema"] == "cas-meta3-procedure-link/0.1"
    assert receipt["package_sha256"] == sha256(canonical_package(package)).hexdigest()
    assert receipt["source_program_sha256"] == digest(package["program"])
    assert receipt["linked_program_sha256"] == digest(linked["program"])
    body = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    assert receipt["receipt_sha256"] == digest(body)
    assert receipt["status"] == "LINKED_NOT_EXECUTED"
    assert receipt["qualification"] == "UNQUALIFIED"
    assert receipt["compatibility"] == kwargs["trusted_compatibility"]
    assert all(receipt[name] is False for name in (
        "native_memory_refs_added", "new_opcodes_added", "native_execution_performed", "learning_performed"))
    assert "separate evidence" in receipt["boundary"]
    changed = deepcopy(body)
    changed["call_sites"][0]["pc"] = 2
    assert digest(changed) != receipt["receipt_sha256"]


def test_package_address_is_stable_and_distinct_from_call_sites_and_runtime_ids():
    package = make_package()
    linked = linker.link_demonstration(package, **options(package))
    repeated = linker.link_demonstration(deepcopy(package), **options(package))
    assert repeated == linked
    receipt = linked["link_receipt"]
    address = "package:" + package_digest(package) + "/fixture_saved_b"
    assert receipt["cognitive_address"] == address
    assert receipt["call_sites"] == [
        {"caller": "main", "pc": 1, "functional_address": "entry:main/steps/1", "procedure": "p0"},
        {"caller": "main", "pc": 2, "functional_address": "entry:main/steps/2", "procedure": "p0"},
    ]
    assert address not in {site["functional_address"] for site in receipt["call_sites"]}
    assert not ({"runtime_id", "call_id", "frame_id", "effect_id", "execution_id"} & set(receipt))
    broader = linker.link_demonstration(package, **options(package, permitted_cjts=("A", "B", "C", "R")))
    assert broader["program"] == linked["program"]
    assert broader["link_receipt"]["cognitive_address"] == address
    assert broader["link_receipt"]["receipt_sha256"] != receipt["receipt_sha256"]
    assert broader["program"]["procedures"]["p0"]["allowed_cjts"] == ["B"]


def test_link_returns_detached_data_and_leaves_original_package_unchanged():
    package = make_package()
    kwargs = options(package)
    original = canonical_package(package)
    expected_kwargs = deepcopy(kwargs)
    linked = linker.link_demonstration(package, **kwargs)
    assert canonical_package(package) == original
    assert kwargs == expected_kwargs
    linked["program"]["procedures"]["p0"]["steps"][0]["cjt_id"] = "R"
    linked["link_receipt"]["compatibility"]["decoder_contracts"]["B"] = "0" * 64
    assert canonical_package(package) == original
    assert kwargs == expected_kwargs


def test_forged_digest_is_rejected_before_dependency_or_native_access(monkeypatch):
    from cas_meta3 import registry
    package = make_package()
    kwargs = options(package)
    kwargs["expected_digest"] = fixture_hash("forged-package-address")
    monkeypatch.setattr(registry, "_ir", lambda: pytest.fail("FORGED_DIGEST_REACHED_IR"))
    with pytest.raises(ValueError, match="EXPECTED_PACKAGE_DIGEST_MISMATCH"):
        linker.link_demonstration(package, **kwargs)


def test_changed_payload_with_original_digest_is_rejected(monkeypatch):
    from cas_meta3 import registry
    package = make_package()
    kwargs = options(package)
    package["provenance"]["source_receipt_sha256"] = fixture_hash("forged-source-receipt")
    monkeypatch.setattr(registry, "_ir", lambda: pytest.fail("CHANGED_PAYLOAD_REACHED_IR"))
    with pytest.raises(ValueError, match="EXPECTED_PACKAGE_DIGEST_MISMATCH"):
        linker.link_demonstration(package, **kwargs)


def test_wrong_compatibility_is_rejected_before_dependency_or_native_access(monkeypatch):
    from cas_meta3 import registry
    package = make_package()
    kwargs = options(package)
    kwargs["trusted_compatibility"]["model_digest"] = fixture_hash("different-model")
    monkeypatch.setattr(registry, "_ir", lambda: pytest.fail("WRONG_COMPATIBILITY_REACHED_IR"))
    with pytest.raises(ValueError, match="CALLER_COMPATIBILITY_MISMATCH"):
        linker.link_demonstration(package, **kwargs)


@pytest.mark.parametrize("scope", [None, [], ["A"], ["B"], "AB", ["A", "B", 1], {"A": True, "B": True}])
def test_denied_parent_scope_stops_before_package_validation(monkeypatch, scope):
    package = make_package()
    kwargs = options(package, permitted_cjts=scope)
    monkeypatch.setattr(linker, "validate_package", lambda *a, **k: pytest.fail("DENIED_PARENT_REACHED_PACKAGE"))
    with pytest.raises(ValueError, match="DEMONSTRATION_PARENT_SCOPE_DENIED"):
        linker.link_demonstration(package, **kwargs)


def test_retrieve_and_link_resolves_registry_first_with_same_expectations(monkeypatch):
    package = make_package()
    kwargs = options(package)
    events = []

    class SpyRegistry:
        def retrieve(self, expected_digest, **given):
            events.append(("retrieve", expected_digest, deepcopy(given)))
            return deepcopy(package)

    original = linker.link_demonstration

    def recording_link(given_package, **given):
        events.append(("link", deepcopy(given_package), deepcopy(given)))
        return original(given_package, **given)

    monkeypatch.setattr(linker, "link_demonstration", recording_link)
    linked = linker.retrieve_and_link(SpyRegistry(), **kwargs)
    assert [event[0] for event in events] == ["retrieve", "link"]
    assert events[0][1] == kwargs["expected_digest"]
    assert events[0][2] == {key: value for key, value in kwargs.items() if key != "expected_digest"}
    assert events[1][1] == package
    assert events[1][2] == kwargs
    assert linked["link_receipt"]["status"] == "LINKED_NOT_EXECUTED"


def test_failed_registry_resolution_never_calls_linker(monkeypatch):
    package = make_package()

    class MissingRegistry:
        def retrieve(self, *args, **kwargs):
            raise ValueError("FIXTURE_ONLY_REGISTRY_LOOKUP_REJECTED")

    monkeypatch.setattr(linker, "link_demonstration", lambda *a, **k: pytest.fail("FAILED_RETRIEVAL_REACHED_LINKER"))
    with pytest.raises(ValueError, match="FIXTURE_ONLY_REGISTRY_LOOKUP_REJECTED"):
        linker.retrieve_and_link(MissingRegistry(), **options(package))


def test_retrieved_package_is_revalidated_against_caller_digest():
    package = make_package()

    class ForgedRegistry:
        def retrieve(self, *args, **kwargs):
            forged = deepcopy(package)
            forged["provenance"]["source_receipt_sha256"] = fixture_hash("forged-on-retrieval")
            return forged

    with pytest.raises(ValueError, match="EXPECTED_PACKAGE_DIGEST_MISMATCH"):
        linker.retrieve_and_link(ForgedRegistry(), **options(package))


def test_real_registry_reopen_keeps_address_package_and_link_bytes(tmp_path):
    package = make_package()
    kwargs = options(package)
    path = tmp_path / "fixture_only_saved_procedures.sqlite"
    original = canonical_package(package)
    with ProcedureRegistry(path) as registry:
        storage = registry.install(package, **kwargs)
        first = linker.retrieve_and_link(registry, **kwargs)
    stored_bytes = path.read_bytes()
    with ProcedureRegistry(path) as reopened:
        second = linker.retrieve_and_link(reopened, **kwargs)
        retrieved = reopened.retrieve(kwargs["expected_digest"],
                                      trusted_compatibility=kwargs["trusted_compatibility"],
                                      permitted_cjts=kwargs["permitted_cjts"])
    assert second == first
    assert canonical(second) == canonical(first)
    assert canonical_package(retrieved) == original == canonical_package(package)
    assert path.read_bytes() == stored_bytes
    assert storage["storage_status"] == "STORAGE_ONLY"
    assert storage["qualification_status"] == "UNQUALIFIED"
    assert first["link_receipt"]["native_execution_performed"] is False


def test_linker_source_does_not_import_or_construct_native_models():
    tree = ast.parse(Path(linker.__file__).read_text(encoding="utf-8"))
    imports = {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    imports |= {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    assert not any(name.startswith(("torch", "casformer", "cas_cjt", "cas_meta1", "cas_meta2.native")) for name in imports)
    called = {node.func.id for node in ast.walk(tree)
              if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
    assert not ({"eval", "exec", "compile", "NativeBackend", "create_native", "execute_task", "reference_task"} & called)
    assert {"cas_meta2.ir", "registry"} <= imports
    assert "cas_meta2.codec" not in imports
    assert "checked_codec" in called
    assert any(isinstance(node, ast.Assign)
               and any(isinstance(target, ast.Name) and target.id == "validate_action"
                       for target in node.targets)
               and isinstance(node.value, ast.Attribute) and node.value.attr == "validate_action"
               and isinstance(node.value.value, ast.Call)
               and isinstance(node.value.value.func, ast.Name)
               and node.value.value.func.id == "checked_codec"
               for node in ast.walk(tree))
