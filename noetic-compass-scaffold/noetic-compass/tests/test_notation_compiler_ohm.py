"""CAS-Ohm through the real compiler and isolated offline package population.

Pure arithmetic only. No model, server, network, calibration, or Rust execution.
"""
from __future__ import annotations

import importlib.util
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import types
import uuid

import pytest

from api.notation import compiler


REPO = Path(__file__).resolve().parents[3]
SCALE = 'ohm_scale("example-v1", "declared-drive", "declared-attention")'


def quantity(kind, value, *, scale=SCALE, origin="design", reference="example:input"):
    return f'ohm_{kind}({value}, {scale}, "{origin}", "{reference}")'


V = quantity("drive", '"12"')
I = quantity("attention", '"3"')
R = quantity("constraint", '"4"')
FLOW = f"ohm_flow({V}, {R})"


def good(source):
    result = compiler.compile_expression(source)
    assert result.valid, result.error
    return result


@pytest.mark.parametrize("source,kind,value,operation", [
    (FLOW, "attention", "3", "attention_flow"),
    (f"ohm_required_drive({I}, {R})", "drive", "12", "required_drive"),
    (f"ohm_effective_constraint({V}, {I})", "constraint", "4", "effective_constraint"),
])
def test_real_expression_uses_typed_call_pipeline(source, kind, value, operation):
    artifact = good(source)
    assert artifact.type_info.kind.value == f"ohm_{kind}"
    data = artifact.to_dict()
    result = data["result"]
    assert result["kind"] == "cas_ohm_quantity"
    assert result["quantity"] == kind
    assert result["value"] == value
    assert result["exact_value"] == {"numerator": value, "denominator": "1"}
    assert result["origin"] == "calculated"
    assert result["operation"] == operation
    assert result["scale"]["id"] == "example-v1"
    assert result["measurement_status"] == "NO_MEASUREMENT_PERFORMED"
    assert result["control_status"] == "NOT_CONNECTED"
    assert len(result["inputs"]) == 2
    assert all(item["reference"] == "example:input" for item in result["inputs"])
    assert data["ast"]["node"] == "CallExpr"
    assert data["bytecode"][-1] == {"opcode": "CALL", "arg": {"name": source.split("(", 1)[0], "argc": 2}}
    json.dumps(data, allow_nan=False)


def test_quantity_strings_remain_exact_and_observation_is_only_supplied():
    raw = "1.00000000000000000001"
    data = good(quantity("attention", json.dumps(raw), origin="supplied_observation", reference="observation:fixture")).to_dict()["result"]
    assert data["input_literal"] == raw
    assert data["numeric_representation"] == "exact_decimal_text"
    assert data["observation_status"] == "CALLER_SUPPLIED_UNVERIFIED"
    assert data["exact_value"] == {"numerator": "100000000000000000001", "denominator": "100000000000000000000"}


def test_numeric_inputs_are_explicit_about_float_representation():
    integer = good(quantity("drive", "12")).to_dict()["result"]
    decimal = good(quantity("drive", "0.1")).to_dict()["result"]
    assert integer["numeric_representation"] == "integer"
    assert decimal["numeric_representation"] == "binary_float_via_shortest_decimal"


def test_huge_numeric_token_returns_an_invalid_artifact():
    artifact = compiler.compile_expression(quantity("drive", "9" * 5000))
    assert not artifact.valid
    assert "numeric literal" in artifact.error
    assert artifact.to_dict()["result"] is None


def test_quantity_types_cannot_claim_ignored_cas_domain_constraints():
    artifact = compiler.compile_expression(f"let potential: ohm_drive[C] = {V}; potential")
    assert not artifact.valid
    assert "declared scales" in artifact.error


def test_typed_functions_bindings_and_reuse_keep_quantity_contracts():
    source = (
        f"let scale: ohm_scale = {SCALE}; "
        'let potential: ohm_drive = ohm_drive("12", scale, "design", "v"); '
        'let resistance: ohm_constraint = ohm_constraint("4", scale, "design", "r"); '
        "fn flow(v: ohm_drive, r: ohm_constraint): ohm_attention = ohm_flow(v, r); "
        "flow(potential, resistance)"
    )
    data = good(source).to_dict()["result"]
    assert data["final_result"]["quantity"] == "attention"
    assert data["final_result"]["value"] == "3"


@pytest.mark.parametrize("source", [
    f"ohm_flow({R}, {V})", f"ohm_required_drive({V}, {R})", f"ohm_effective_constraint({V}, {R})",
    f"ohm_flow(12, {R})", f"ohm_flow(^8^C, {R})", f"ohm_flow(F2, {R})",
    f"ohm_flow({V})", f"ohm_flow({V}, {R}, {R})", "ohm_flow()",
    'ohm_scale("id", "drive")', 'ohm_scale(1, "drive", "attention")',
    f'ohm_drive("12", "scale", "design", "ref")',
    f'ohm_drive("12", {SCALE}, "design")',
    f'ohm_drive("12", {SCALE}, 2, "ref")',
    f"let v: ohm_attention = {V}; v", f"{V} * {R}", f"{V} / {R}",
    'fn ohm_flow(v,r) = v; 1',
])
def test_wrong_types_or_arity_fail_at_compile_time(source):
    artifact = compiler.compile_expression(source)
    assert not artifact.valid
    assert artifact.error.startswith("typecheck:"), artifact.error


@pytest.mark.parametrize("source,error", [
    (f'ohm_flow({V}, {quantity("constraint", chr(34)+"0"+chr(34))})', "OHM_ZERO_CONSTRAINT"),
    (f'ohm_effective_constraint({V}, {quantity("attention", chr(34)+"0"+chr(34))})', "OHM_ZERO_ATTENTION"),
    (quantity("drive", '"-1"'), "OHM_NUMBER"),
    (quantity("drive", '"NaN"'), "OHM_NUMBER"),
    (quantity("drive", '"Infinity"'), "OHM_NUMBER"),
    (quantity("drive", '"1e3"'), "OHM_NUMBER"),
    (quantity("drive", '""'), "OHM_NUMBER"),
    (quantity("drive", '"1"', origin="calculated"), "OHM_ORIGIN"),
    (quantity("drive", '"1"', reference=""), "OHM_METADATA"),
    ('ohm_scale("", "drive", "attention")', "OHM_METADATA"),
    (quantity("drive", json.dumps("1" * 513)), "OHM_LIMIT"),
])
def test_invalid_inputs_return_artifacts_not_raw_math_exceptions(source, error):
    artifact = compiler.compile_expression(source)
    assert artifact.valid is False
    assert artifact.error.startswith("execution: CAS-Ohm:"), artifact.error
    assert error in artifact.error
    assert artifact.to_dict()["result"] is None


@pytest.mark.parametrize("other", [
    'ohm_scale("different", "declared-drive", "declared-attention")',
    'ohm_scale("example-v1", "different-unit", "declared-attention")',
    'ohm_scale("example-v1", "declared-drive", "different-unit")',
])
def test_complete_scale_descriptor_must_match(other):
    artifact = compiler.compile_expression(f"ohm_flow({V}, {quantity('constraint', '4', scale=other)})")
    assert not artifact.valid
    assert "OHM_SCALE_MISMATCH" in artifact.error


@pytest.mark.parametrize("source", [
    f"fn flow(v,r)=ohm_flow(v,r); flow({R},{V})",
    f'fn build(value,scale,origin,ref)=ohm_drive(value,scale,origin,ref); build(^8^C,{SCALE},"design","ref")',
    f'fn build(value,scale,origin,ref)=ohm_drive(value,scale,origin,ref); build(12,"not-a-scale","design","ref")',
    'fn scale(id,du,au)=ohm_scale(id,du,au); scale(1,"drive","attention")',
])
def test_untyped_functions_cannot_bypass_runtime_quantity_contracts(source):
    artifact = compiler.compile_expression(source)
    assert not artifact.valid
    assert artifact.error.startswith("execution:"), artifact.error


def test_no_rust_operator_is_used_for_ohm_calculation(monkeypatch):
    class ForbiddenEngine:
        def __getattr__(self, name):
            raise AssertionError(f"Rust operation reached: {name}")
    monkeypatch.setattr(compiler, "cas_engine", ForbiddenEngine())
    assert good(FLOW).result.quantity == "attention"


def test_readme_examples_reach_the_claimed_calculation_and_error():
    text = (REPO / "offline-cas/README.md").read_text(encoding="utf-8")
    examples = re.findall(r"```cas\n(.*?)```", text, re.DOTALL)
    assert len(examples) == 2
    assert good(examples[0]).to_dict()["result"]["final_result"]["value"] == "3"
    invalid = compiler.compile_expression(examples[1])
    assert not invalid.valid
    assert "OHM_ZERO_CONSTRAINT" in invalid.error


def _load_file(path):
    name = "_isolated_ohm_test_" + uuid.uuid4().hex
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_file_spec_import_loads_its_exact_sibling_and_keeps_global_names(monkeypatch, tmp_path):
    foreign = types.ModuleType("cas_ohm")
    monkeypatch.setitem(sys.modules, "cas_ohm", foreign)
    source = Path(compiler.__file__).resolve()
    shutil.copyfile(source, tmp_path / "compiler.py")
    shutil.copyfile(source.with_name("cas_ohm.py"), tmp_path / "cas_ohm.py")
    isolated = _load_file(tmp_path / "compiler.py")
    assert isolated.compile_expression(FLOW).valid
    helper = isolated._load_cas_ohm()
    assert helper is isolated._load_cas_ohm()
    assert Path(helper.__file__).resolve() == (tmp_path / "cas_ohm.py").resolve()
    assert sys.modules["cas_ohm"] is foreign
    assert isolated.compile_expression(FLOW).to_dict()["result"] == good(FLOW).to_dict()["result"]


@pytest.mark.parametrize("newline", [b"\n", b"\r\n"])
def test_cached_helper_receipt_stays_bound_to_executed_bytes_after_file_change(tmp_path, monkeypatch, newline):
    compiler_path = Path(compiler.__file__).resolve()
    helper_path = tmp_path / "cas_ohm.py"
    normalized = compiler_path.with_name("cas_ohm.py").read_bytes().replace(b"\r\n", b"\n")
    executed = normalized.replace(b"\n", newline)
    shutil.copyfile(compiler_path, tmp_path / "compiler.py")
    helper_path.write_bytes(executed)
    isolated = _load_file(tmp_path / "compiler.py")
    helper = isolated._load_cas_ohm()
    assert helper.__cas_ohm_source_sha256_raw__ == hashlib.sha256(executed).hexdigest()
    assert helper.__cas_ohm_source_sha256_lf__ == hashlib.sha256(normalized).hexdigest()
    assert helper.__cas_ohm_loaded_path__ == str(helper_path.resolve())

    helper_path.write_bytes(b"raise RuntimeError('changed bytes must not execute or describe the cached module')\n")
    original_read = Path.read_bytes
    def forbid_cached_helper_reread(path):
        assert path.resolve() != helper_path.resolve(), "receipt reread the changed helper"
        return original_read(path)
    monkeypatch.setattr(Path, "read_bytes", forbid_cached_helper_reread)

    assert isolated._load_cas_ohm() is helper
    assert isolated.compile_expression(FLOW).to_dict()["result"]["value"] == "3"
    assert helper.__cas_ohm_source_sha256_raw__ == hashlib.sha256(executed).hexdigest()
    assert helper.__cas_ohm_source_sha256_lf__ == hashlib.sha256(normalized).hexdigest()


def test_missing_sibling_fails_closed_without_using_available_other_checkout(tmp_path):
    shutil.copyfile(compiler.__file__, tmp_path / "compiler.py")
    isolated = _load_file(tmp_path / "compiler.py")
    artifact = isolated.compile_expression(FLOW)
    assert not artifact.valid
    assert "sibling helper unavailable" in artifact.error
    assert isolated.compile_expression("^2^C").valid


def test_offline_population_includes_identical_core_and_helper_and_cli_runs(tmp_path):
    builder = _load_file(REPO / "offline-cas/build_offline_package.py")
    package = tmp_path / "package"
    builder._populate(package)
    for filename in ("compiler.py", "cas_ohm.py"):
        assert (package / "api/notation" / filename).read_bytes() == (Path(compiler.__file__).parent / filename).read_bytes()
    isolated = _load_file(package / "api/notation/compiler.py")
    assert isolated.compile_expression(FLOW).to_dict() == good(FLOW).to_dict()
    environment = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    run = subprocess.run([sys.executable, "-B", str(package / "cas.py"), FLOW, "--json", "--no-color", "--no-terminal-diagram"],
                         cwd=package, env=environment, capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert run.returncode == 0, run.stderr
    assert '"quantity": "attention"' in run.stdout
    assert '"measurement_status": "NO_MEASUREMENT_PERFORMED"' in run.stdout
    assert not list(package.glob("*.svg"))
    assert not list(package.glob("*.html"))
