"""Tests for the executable CAS notation compiler."""

from pathlib import Path
import shutil
import uuid

from api.notation.compiler import compile_expression, compile_file


def _local_tmp_dir() -> Path:
    base = Path("_tmp_lang_tests").resolve()
    base.mkdir(exist_ok=True)
    path = base / f"cas_lang_{uuid.uuid4().hex}"
    path.mkdir()
    return path


def test_compile_transition_expression():
    artifact = compile_expression("(CO-2^C_{F2} * CO-4^C_{F2}) -> CO-5^E_{F4}")
    assert artifact.valid
    assert artifact.type_info is not None
    assert artifact.type_info.kind.value == "relation"
    assert artifact.result is not None
    result = artifact.to_dict()["result"]
    assert result["kind"] == "relation"
    assert result["relation"] == "dependency"
    assert result["domain_descent_ok"] is True
    assert result["admissible"] is True
    opcodes = [ins.opcode for ins in artifact.bytecode]
    assert opcodes == ["PUSH_STATE", "PUSH_STATE", "TIMES", "PUSH_STATE", "ARROW"]


def test_invalid_domain_descent_rejected():
    artifact = compile_expression("CO-5^E_{F4} -> CO-2^C_{F2}")
    assert not artifact.valid
    assert artifact.error is not None
    assert "domain descent violated" in artifact.error


def test_invalid_operator_range_rejected():
    artifact = compile_expression("CO-11^P_{F1}")
    assert not artifact.valid
    assert artifact.error is not None
    assert "operator index must be 0-9" in artifact.error


def test_rpm_drive_expression_executes():
    artifact = compile_expression("RPM(F5)")
    assert artifact.valid
    result = artifact.to_dict()["result"]
    assert result["kind"] == "rpm"
    assert result["drive"] == "F5"
    assert result["completeness"] == 1.0


def test_fractal_expression_executes():
    artifact = compile_expression("Phi<2:5:8:3:9>")
    assert artifact.valid
    result = artifact.to_dict()["result"]
    assert result["kind"] == "fractal"
    assert result["sequence"] == [2, 5, 8, 3, 9]
    assert result["composed_operator"].startswith("CO-")


def test_co0_transition_uses_admissibility_rule():
    artifact = compile_expression("CO-0^P -> CO-0^C")
    assert artifact.valid
    result = artifact.to_dict()["result"]
    assert result["kind"] == "relation"
    assert result["domain_descent_ok"] is True
    assert result["admissible"] is False


def test_shorthand_state_reference_executes():
    artifact = compile_expression("P3 -> C3")
    assert artifact.valid
    result = artifact.to_dict()["result"]
    assert result["kind"] == "relation"
    assert result["source"]["dominant_state"] == "P3"
    assert result["target"]["dominant_state"] == "C3"


def test_circ_builds_fractal_sequence():
    artifact = compile_expression("CO-8^C ∘ CO-3^C")
    assert artifact.valid
    result = artifact.to_dict()["result"]
    assert result["kind"] == "fractal"
    assert result["sequence"] == [8, 3]
    assert result["domain"] == "C"


def test_multi_statement_program_executes():
    artifact = compile_expression("P0 -> C0; RPM(F5); Phi<2:5:8:3:9>")
    assert artifact.valid
    result = artifact.to_dict()["result"]
    assert result["kind"] == "program"
    assert len(result["results"]) == 3
    assert result["results"][0]["kind"] == "relation"
    assert result["results"][1]["kind"] == "rpm"
    assert result["final_result"]["kind"] == "fractal"


def test_let_binding_and_function_call_execute():
    artifact = compile_expression(
        "let start = CO-2^C_{F2}; fn bridge(x, y) = x -> y; bridge(start, CO-5^E_{F4})"
    )
    assert artifact.valid
    result = artifact.to_dict()["result"]
    assert result["kind"] == "program"
    assert result["results"][0]["kind"] == "binding"
    assert result["results"][1]["kind"] == "function"
    assert result["final_result"]["kind"] == "relation"


def test_builtin_function_call_executes():
    artifact = compile_expression("dominant_operator(CO-8^C)")
    assert artifact.valid
    assert artifact.to_dict()["result"] == "CO-8"


def test_typed_binding_rejects_wrong_type():
    artifact = compile_expression('let label: state[C] = "hello"; label')
    assert not artifact.valid
    assert artifact.error is not None
    assert "binding label" in artifact.error


def test_typed_function_contract_executes():
    artifact = compile_expression(
        "fn bridge(x: state[C], y: state[E]): relation = x -> y; bridge(C2, E5)"
    )
    assert artifact.valid
    result = artifact.to_dict()["result"]
    assert result["kind"] == "program"
    assert result["final_result"]["kind"] == "relation"


def test_typed_function_rejects_wrong_domain_argument():
    artifact = compile_expression(
        "fn bridge(x: state[C], y: state[E]): relation = x -> y; bridge(P2, E5)"
    )
    assert not artifact.valid
    assert artifact.error is not None
    assert "function bridge argument 1" in artifact.error


def test_use_statement_imports_module():
    tmp_dir = _local_tmp_dir()
    try:
        helper = tmp_dir / "helper.cas"
        helper.write_text("let base = CO-2^C_{F2}; fn lift(x) = x -> CO-5^E_{F4}", encoding="utf-8")
        main = tmp_dir / "main.cas"
        main.write_text(f'use "{helper.name}"; lift(base)', encoding="utf-8")

        artifact = compile_file(str(main))
        assert artifact.valid
        result = artifact.to_dict()["result"]
        assert result["kind"] == "program"
        assert result["results"][0]["kind"] == "module"
        assert result["final_result"]["kind"] == "relation"
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_cyclic_import_rejected():
    tmp_dir = _local_tmp_dir()
    try:
        a = tmp_dir / "a.cas"
        b = tmp_dir / "b.cas"
        a.write_text(f'use "{b.name}"', encoding="utf-8")
        b.write_text(f'use "{a.name}"', encoding="utf-8")

        artifact = compile_file(str(a))
        assert not artifact.valid
        assert artifact.error is not None
        assert "cyclic import detected" in artifact.error
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_export_limits_imported_surface():
    tmp_dir = _local_tmp_dir()
    try:
        helper = tmp_dir / "helper.cas"
        helper.write_text(
            'export let base: state[C] = CO-2^C_{F2}; fn hidden(x: state[C]): relation = x -> CO-5^E_{F4}',
            encoding="utf-8",
        )
        main = tmp_dir / "main.cas"
        main.write_text(f'use "{helper.name}"; hidden(base)', encoding="utf-8")

        artifact = compile_file(str(main))
        assert not artifact.valid
        assert artifact.error is not None
        assert "undefined function hidden" in artifact.error
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_exported_symbols_survive_cached_reimport():
    tmp_dir = _local_tmp_dir()
    try:
        helper = tmp_dir / "helper.cas"
        helper.write_text(
            'export let base: state[C] = CO-2^C_{F2}; export fn bridge(x: state[C], y: state[E]): relation = x -> y',
            encoding="utf-8",
        )
        artifact = compile_expression(
            f'use "{helper}"; use "{helper}"; bridge(base, E5)'
        )
        assert artifact.valid
        result = artifact.to_dict()["result"]
        assert result["kind"] == "program"
        assert result["results"][0]["kind"] == "module"
        assert result["results"][1]["kind"] == "module"
        assert result["final_result"]["kind"] == "relation"
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_showcase_program_executes():
    artifact = compile_file(str(Path("docs/CAS_SHOWCASE_APP.cas").resolve()))
    assert artifact.valid
    result = artifact.to_dict()["result"]
    assert result["kind"] == "program"
    assert result["results"][0]["kind"] == "module"
    assert result["results"][1]["kind"] == "binding"
    assert result["results"][2]["kind"] == "binding"
    assert result["results"][3]["kind"] == "binding"
    assert result["results"][4]["kind"] == "binding"
    assert result["results"][5]["kind"] == "function"
    assert result["final_result"]["kind"] == "relation"
