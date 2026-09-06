"""Synthetic data-only contract tests; no learning or native evidence claimed."""
from copy import deepcopy
from hashlib import sha256
import ast
import json
import os
from pathlib import Path
import subprocess
import sys
from types import ModuleType

import pytest

from cas_meta3 import learned_package as p


def h(label):
    return sha256(("SYNTHETIC TEST IDENTITY:" + label).encode()).hexdigest()


def program():
    return {"schema": p.IR_SCHEMA, "entry": "main", "procedures": {
        "main": {"input": "arg", "allowed_cjts": ["A", "B", "C"], "steps": [
            {"kind": "RUN", "cjt_id": "A", "input": "arg", "output": "v0"},
            {"kind": "CALL", "procedure": "p0", "input": "v0", "output": "v1"},
            {"kind": "CALL", "procedure": "p0", "input": "v0", "output": "v2"},
            {"kind": "RUN", "cjt_id": "C", "input": "v2", "output": "v3"}], "return": "v1"},
        "p0": {"input": "arg", "allowed_cjts": ["B"], "steps": [
            {"kind": "RUN", "cjt_id": "B", "input": "arg", "output": "v0"}], "return": "v0"}}}


def fixture():
    body = program()
    return {"schema": p.PACKAGE_SCHEMA, "kind": p.PACKAGE_KIND, "program": body, "binding": 1,
        "io": {"input": {"kind": "OBSERVATION_SLOT", "slot": 1, "dtype": "float32", "shape": [1, 2, 4]},
               "output": {"kind": "ACCEPTED_EFFECT", "producer_cjt_id": "B", "dtype": "float32", "shape": [1, 2, 4]}},
        "required_cjts": ["A", "B", "C"], "compatibility": {
            "baseline_sha": p.BASELINE_SHA, "meta2_source_sha": p.META2_SOURCE_SHA, "ir_schema": p.IR_SCHEMA,
            **{name: h(name) for name in ("native_schema_sha256", "model_digest", "parameter_bytes_sha256", "software_digest", "topology_sha256")},
            "operation_contracts": {"^6": h("operation")}, "decoder_contracts": {name: h("decoder" + name) for name in p.CJT_IDS}},
        "provenance": {"source_program_sha256": p.package_digest(body), "policy_source_sha256": h("writer-map"),
            "policy_checkpoint_sha256": h("checkpoint"), "producer_source_sha": p.META2_SOURCE_SHA,
            "producer_evidence_sha256": h("evidence"), "verification_status": "UNVERIFIED"},
        "lineage": {"version": 1, "parent_package_sha256": None}, "memory_requirements": [],
        "qualification_status": "UNQUALIFIED"}


def arguments(value):
    return {"expected_digest": p.package_digest(value), "trusted_compatibility": deepcopy(value["compatibility"]),
            "permitted_cjts": p.CJT_IDS, "expected_parent_digest": None, "expected_version": 1}


def admit(value):
    return p.validate_package(value, **arguments(value))


def rehash_program(value):
    value["provenance"]["source_program_sha256"] = p.package_digest(value["program"])


def test_pins_match_actual_frozen_git_objects_without_neural_import():
    assert p.verify_dependency_git() == {**p.dependency_receipt(), "verified_against_git": True}
    assert "torch" not in sys.modules and "boto3" not in sys.modules


def test_full_nested_repeated_call_returns_selected_earlier_effect():
    value = fixture()
    receipt = p.admission_receipt(value, **arguments(value))
    contract = receipt["program_contract"]
    assert contract["bounds"]["procedure_count"] == 2
    assert contract["bounds"]["expanded_run_count"] == 4
    assert contract["bounds"]["max_call_depth"] == 2
    assert contract["return_node"] == 1 and contract["output_producer_cjt_id"] == "B"
    assert contract["required_cjts"] == ["A", "B", "C"]
    assert receipt["status"] == "DATA_ONLY_ADMITTED" and receipt["qualification_status"] == "UNQUALIFIED"
    for key in ("provenance_verified", "parent_evidence_verified", "learning_success_established", "execution_performed", "promotion_granted"):
        assert receipt[key] is False
    assert receipt["receipt_sha256"] == p.package_digest({key: item for key, item in receipt.items() if key != "receipt_sha256"})


def test_supports_all_existing_cjts_and_topology_edges():
    value = fixture()
    main = value["program"]["procedures"]["main"]
    main["allowed_cjts"].append("R")
    main["steps"].append({"kind": "RUN", "cjt_id": "R", "input": "v3", "output": "v4"})
    main["steps"].append({"kind": "RUN", "cjt_id": "C", "input": "v4", "output": "v5"})
    main["return"] = "v5"
    value["required_cjts"].append("R")
    value["io"]["output"]["producer_cjt_id"] = "C"
    rehash_program(value)
    assert admit(value) == value


def test_unused_declared_scope_is_still_required_permission():
    value = fixture()
    value["program"]["procedures"]["main"]["allowed_cjts"].append("R")
    value["required_cjts"].append("R")
    rehash_program(value)
    args = arguments(value)
    args["permitted_cjts"] = ["A", "B", "C"]
    with pytest.raises(p.PackageError, match="CALLER_CJT_SCOPE_DENIED"):
        p.validate_package(value, **args)
    receipt = p.admission_receipt(value, **arguments(value))
    assert "R" in receipt["program_contract"]["required_cjts"]
    assert "R" not in receipt["program_contract"]["executed_cjts"]


def test_canonical_json_roundtrip_is_detached_and_source_order_insensitive():
    value = fixture()
    raw = json.dumps(value, indent=2).encode()
    result = p.validate_package(raw, **arguments(value))
    assert result == value and result is not value
    result["program"]["procedures"]["main"]["return"] = "v3"
    assert value["program"]["procedures"]["main"]["return"] == "v1"
    assert p.package_digest(raw) == p.package_digest(value)


def test_explicit_parent_version_is_content_bound_but_unverified():
    value = fixture()
    original = p.canonical_package(value)
    parent = p.package_digest(value)
    child = deepcopy(value)
    child["lineage"] = {"version": 2, "parent_package_sha256": parent}
    args = {**arguments(child), "expected_version": 2, "expected_parent_digest": parent}
    assert p.validate_package(child, **args) == child
    assert p.canonical_package(value) == original
    assert p.package_digest(child) != parent
    assert p.admission_receipt(child, **args)["parent_evidence_verified"] is False


@pytest.mark.parametrize("edit", [
    lambda v: v.update(qualification_status="QUALIFIED"),
    lambda v: v.update(kind="PYTHON_MODULE"),
    lambda v: v.update(schema="cas-meta3-procedure-package/0.1"),
    lambda v: v.update(promoted=True),
    lambda v: v.update(memory_requirements=[{"scope": "episodic"}]),
    lambda v: v["provenance"].update(verification_status="VERIFIED"),
    lambda v: v["provenance"].update(qualification_receipt_sha256=h("forged-qualification")),
    lambda v: v["provenance"].update(source_program_sha256=h("wrong-program")),
    lambda v: v["provenance"].update(policy_source_sha256=None),
    lambda v: v["provenance"].update(policy_checkpoint_sha256="z" * 64),
    lambda v: v["provenance"].update(producer_source_sha="1" * 64),
    lambda v: v["provenance"].update(producer_evidence_sha256=""),
    lambda v: v.update(required_cjts=["A", "B"]),
    lambda v: v.update(required_cjts=["C", "B", "A"]),
    lambda v: v.update(required_cjts=["A", "B", "C", "C"]),
    lambda v: v.update(binding=True),
    lambda v: v.update(binding=3),
    lambda v: v["io"]["input"].update(slot=0),
    lambda v: v["io"]["input"].update(kind="NATIVE_CAUSE_REFERENCE"),
    lambda v: v["io"]["output"].update(producer_cjt_id="C"),
    lambda v: v["io"]["output"].update(shape=[True, 2, 4]),
    lambda v: v["io"]["output"].update(shape=[1.0, 2, 4]),
    lambda v: v["io"]["output"].update(dtype="float64"),
    lambda v: v["lineage"].update(version=True),
])
def test_invalid_claim_or_contract_rejected(edit):
    value = fixture()
    edit(value)
    with pytest.raises(p.PackageError):
        admit(value)


@pytest.mark.parametrize("field", ["native_schema_sha256", "model_digest", "parameter_bytes_sha256", "software_digest", "topology_sha256"])
def test_each_exact_trusted_identity_must_match(field):
    value = fixture()
    args = arguments(value)
    args["trusted_compatibility"][field] = h("wrong" + field)
    with pytest.raises(p.PackageError, match="CALLER_COMPATIBILITY_MISMATCH"):
        p.validate_package(value, **args)


@pytest.mark.parametrize("edit", [
    lambda v: v.update(baseline_sha="0" * 40),
    lambda v: v.update(meta2_source_sha="0" * 40),
    lambda v: v.update(ir_schema="future"),
    lambda v: v["operation_contracts"].update({"^9": h("new-noetic")}),
    lambda v: v["decoder_contracts"].pop("R"),
    lambda v: v["decoder_contracts"].update(R=None),
])
def test_same_unsupported_trusted_identity_does_not_make_it_supported(edit):
    value = fixture()
    edit(value["compatibility"])
    with pytest.raises(p.PackageError):
        admit(value)


@pytest.mark.parametrize("overrides", [
    {"expected_digest": "0" * 64}, {"expected_digest": None},
    {"expected_version": 2}, {"expected_parent_digest": h("parent")},
    {"expected_version": True}, {"expected_version": 0},
    {"permitted_cjts": ["A"]}, {"permitted_cjts": ["A", "B", "C", "C"]},
    {"permitted_cjts": "ABCR"}, {"permitted_cjts": ["A", "Z"]},
])
def test_external_expectations_cannot_be_inferred_from_package(overrides):
    value = fixture()
    with pytest.raises(p.PackageError):
        p.validate_package(value, **{**arguments(value), **overrides})


@pytest.mark.parametrize("kind", ["cycle", "scope", "unreachable", "bad-edge", "bad-return", "observation-return", "opcode"])
def test_ir_and_native_topology_rejections_are_preserved(kind):
    value = fixture()
    main = value["program"]["procedures"]["main"]
    child = value["program"]["procedures"]["p0"]
    if kind == "cycle":
        child["steps"] = [{"kind": "CALL", "procedure": "p0", "input": "arg", "output": "v0"}]
    elif kind == "scope":
        child["allowed_cjts"].append("R")
    elif kind == "unreachable":
        value["program"]["procedures"]["p1"] = deepcopy(child)
    elif kind == "bad-edge":
        main["steps"][-1]["input"] = "v0"  # A -> C is not an accepted edge.
    elif kind == "bad-return":
        main["return"] = "v31"
    elif kind == "observation-return":
        child["return"] = "arg"  # The call receives an accepted A; still valid.
        main["return"] = "arg"   # The outer program returns an observation: reject.
    else:
        main["steps"][0]["kind"] = "EVAL"
    rehash_program(value)
    with pytest.raises(p.PackageError):
        admit(value)


def test_expanded_program_ceiling_is_checked_before_topology_expansion():
    value = fixture()
    names = ["main"] + ["p" + str(i) for i in range(9)]
    procedures = {}
    for index, name in enumerate(names):
        steps = ([{"kind": "RUN", "cjt_id": "A", "input": "arg", "output": "v0"}]
                 if index == len(names) - 1 else [
                     {"kind": "CALL", "procedure": names[index + 1], "input": "arg", "output": "v0"},
                     {"kind": "CALL", "procedure": names[index + 1], "input": "arg", "output": "v1"}])
        procedures[name] = {"input": "arg", "allowed_cjts": ["A"], "steps": steps, "return": "v0"}
    value["program"]["procedures"] = procedures
    rehash_program(value)
    with pytest.raises(p.PackageError, match="EXPANDED_.*_LIMIT"):
        admit(value)


def test_every_callee_must_return_an_accepted_effect_not_raw_observation():
    value = fixture()
    main = value["program"]["procedures"]["main"]
    main["steps"] = [{"kind": "CALL", "procedure": "p0", "input": "arg", "output": "v0"}]
    main["return"] = "v0"
    value["program"]["procedures"]["p0"]["return"] = "arg"
    rehash_program(value)
    with pytest.raises(p.PackageError, match="ACCEPTED_EFFECT_RESULT_REQUIRED"):
        admit(value)


@pytest.mark.parametrize("raw", [b'{"a":1,"a":2}', b'{"a":{"b":1,"b":2}}', b'{"a":NaN}',
    b'{"a":Infinity}', b'{"a":1e999}', b'[]', b'null', b'{} trailing', b'\xff', b''])
def test_strict_raw_json_rejects_ambiguous_or_nonfinite_data(raw):
    with pytest.raises(p.PackageError):
        p.canonical_package(raw)


@pytest.mark.parametrize("bad", [("tuple",), {"set"}, b"bytes", object(), float("nan"), 2**80, {1: "key"}])
def test_python_coercions_are_not_json_admission(bad):
    with pytest.raises(p.PackageError):
        p.canonical_package({"bad": bad})


def test_container_subclasses_cycles_depth_nodes_and_bytes_are_bounded():
    class Derived(dict):
        pass
    with pytest.raises(p.PackageError):
        p.canonical_package(Derived(a=1))
    value = {}; value["self"] = value
    with pytest.raises(p.PackageError, match="CYCLIC"):
        p.canonical_package(value)
    value = {}; cursor = value
    for _ in range(p.MAX_TREE_DEPTH + 1):
        cursor["child"] = {}; cursor = cursor["child"]
    with pytest.raises(p.PackageError, match="TREE_CEILING"):
        p.canonical_package(value)
    with pytest.raises(p.PackageError, match="TREE_CEILING"):
        p.canonical_package({"huge": [0] * (p.MAX_CONTAINER_ITEMS + 1)})
    with pytest.raises(p.PackageError, match="BYTE_CEILING"):
        p.canonical_package({str(i): "x" * 16000 for i in range(20)})


def test_wrong_dependency_bytes_rejected_before_any_pinned_execution(monkeypatch):
    original = Path.read_bytes
    def changed(path):
        if path == p.DEPENDENCY_ROOT / "cas_meta2/curriculum.py":
            return b"raise RuntimeError('MUST NOT EXECUTE')"
        return original(path)
    monkeypatch.setattr(Path, "read_bytes", changed)
    with pytest.raises(p.PackageError, match="PINNED_PURE_DEPENDENCY_CHANGED"):
        admit(fixture())
    assert not any(name.startswith(p._NAMESPACE) for name in sys.modules)


def test_preloaded_private_namespace_is_rejected_and_not_removed(monkeypatch):
    fake = ModuleType(p._NAMESPACE + ".ir")
    monkeypatch.setitem(sys.modules, p._NAMESPACE + ".ir", fake)
    with pytest.raises(p.PackageError, match="UNTRUSTED_PRELOADED_PURE_NAMESPACE"):
        admit(fixture())
    assert sys.modules[p._NAMESPACE + ".ir"] is fake


def test_unrelated_cas_meta2_namespace_cannot_replace_checked_dependencies(monkeypatch):
    fake = ModuleType("cas_meta2.ir")
    fake.validate_program = lambda _: pytest.fail("untrusted module was executed")
    monkeypatch.setitem(sys.modules, "cas_meta2.ir", fake)
    assert admit(fixture())["qualification_status"] == "UNQUALIFIED"
    assert sys.modules["cas_meta2.ir"] is fake
    assert not any(name.startswith(p._NAMESPACE) for name in sys.modules)


def test_fresh_process_blocks_neural_provider_imports_and_preserves_fixed_b_files():
    root = Path(__file__).resolve().parents[1]
    protected = [root / "cas_meta3" / name for name in ("registry.py", "linker.py", "native_demo.py", "__init__.py")]
    before = {str(path): sha256(path.read_bytes()).hexdigest() for path in protected}
    code = '''
import importlib.abc,json,sys
class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in {'torch','numpy','boto3','botocore','transformers','tensorflow','jax'}:
            raise RuntimeError('FORBIDDEN_IMPORT:'+fullname)
sys.meta_path.insert(0,Guard())
from cas_meta3.learned_package import validate_package,admission_receipt
r=json.loads(sys.stdin.read())
v=validate_package(r['package'],**r['arguments'])
receipt=admission_receipt(r['package'],**r['arguments'])
print(json.dumps({'qualification':v['qualification_status'],'receipt':receipt,'modules':sorted(sys.modules)}))
'''
    value = fixture()
    env = dict(os.environ)
    env["PYTHONPATH"] = str(root)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run([sys.executable, "-B", "-c", code], input=json.dumps({"package": value, "arguments": arguments(value)}),
                            capture_output=True, text=True, timeout=30, env=env, cwd=root)
    assert result.returncode == 0, result.stderr
    reply = json.loads(result.stdout)
    assert reply["qualification"] == "UNQUALIFIED"
    assert reply["receipt"]["promotion_granted"] is False
    assert not any(name.split('.')[0] in {"torch", "numpy", "boto3", "botocore"} for name in reply["modules"])
    assert before == {str(path): sha256(path.read_bytes()).hexdigest() for path in protected}


def test_module_exposes_no_registry_promotion_or_curriculum_draw():
    tree = ast.parse(Path(p.__file__).read_text())
    called = {node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id
              for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, (ast.Name, ast.Attribute))}
    assert not called.intersection({"generate_dataset", "_construct", "fit_train", "train_and_seal", "execute_task", "learning_tick", "install", "promote"})
    assert not any(hasattr(p, name) for name in ("install", "promote", "qualify", "execute", "rollback"))
