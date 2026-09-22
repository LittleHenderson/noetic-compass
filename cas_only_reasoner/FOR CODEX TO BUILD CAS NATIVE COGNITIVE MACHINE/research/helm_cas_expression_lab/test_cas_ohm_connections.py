"""Prepared connections tested with real compiler/checker, no model or runtime."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cas_ohm_connections as links

SCALE = {"id": "demo-linear", "drive_unit": "declared_drive", "attention_unit": "declared_attention"}
DRIVE = {"value": "12", "scale": SCALE, "origin": "design", "reference": "owner-demo-drive"}
RESISTANCE = {"scale": SCALE, "origin": "design", "reference": "resistor-design-scale"}
BOARD = "board local_board { node a: ^8^C|A; resistor r1: Resistor<a, R=4.00>; }"
SCALE_EXPR = 'ohm_scale("demo-linear", "declared_drive", "declared_attention")'


def expression(operation="ohm_flow", first_kind="drive", second_kind="constraint", first="12", second="4"):
    return (f'{operation}(ohm_{first_kind}("{first}", {SCALE_EXPR}, "design", "first-value"), '
            f'ohm_{second_kind}("{second}", {SCALE_EXPR}, "design", "second-value"))')


def calculated(first="12", second="4"):
    return links.make_synthetic_demo(expression(first=first, second=second), "fixture")["target"]["quantity_report"]


def row(name, parent=None, report=None):
    return {"node_id": name, "parent_id": parent, "quantity_report": calculated() if report is None else report}


def test_actual_checked_resistor_literal_is_used():
    result = links.pcba_resistor_flow(BOARD, "r1", DRIVE, RESISTANCE)
    assert result["pcba_check"]["parse_status"] == result["pcba_check"]["structural_status"] == "PASS"
    assert result["resistance_literal"] == "4.00"
    assert result["quantity_report"]["exact_value"] == {"numerator": "3", "denominator": "1"}
    assert result["quantity_report"]["inputs"][1]["input_literal"] == "4.00"
    assert result["board_source_sha256"] == hashlib.sha256(BOARD.encode()).hexdigest()
    assert result["topology_status"] == "NO_SERIES_PARALLEL_OR_TOTAL_INFERENCE"
    assert result["measurement_status"] == "NO_MEASUREMENT_PERFORMED"
    assert result["helm_status"] == "NOT_TRAINED"


def test_more_than_one_resistor_does_not_infer_series_or_parallel():
    source = BOARD.replace(" }", " node b: ^9^C; resistor r2: Resistor<b,R=6>; }")
    a = links.pcba_resistor_flow(source, "r1", DRIVE, RESISTANCE)
    b = links.pcba_resistor_flow(source, "r2", DRIVE, RESISTANCE)
    assert a["quantity_report"]["value"] == "3"
    assert b["quantity_report"]["value"] == "2"
    assert "total" not in a and "equivalent_resistance" not in a


@pytest.mark.parametrize("source,name", [
    (BOARD, "missing"),
    (BOARD, "a"),
    (BOARD.replace("resistor r1: Resistor<a, R=4.00>", "capacitor r1: Capacitor<a,C=4>"), "r1"),
    (BOARD.replace("node a: ^8^C|A;", ""), "r1"),
    (BOARD.replace("^8^C|A", "^8"), "r1"),
    (BOARD.replace("resistor r1:", "let r1 ="), "r1"),
    (BOARD.replace("resistor r1: Resistor<a, R=4.00>", "gate r1: AND<a,a>"), "r1"),
    (BOARD.replace(" }", " feedback a -> a [beta=.1]; }"), "r1"),
])
def test_unverified_invalid_or_wrong_component_board_refused(source, name):
    with pytest.raises(links.OhmConnectionError):
        links.pcba_resistor_flow(source, name, DRIVE, RESISTANCE)


def test_zero_resistor_refuses_division_even_when_board_shape_passes():
    with pytest.raises(ValueError, match="OHM_ZERO_CONSTRAINT"):
        links.pcba_resistor_flow(BOARD.replace("4.00", "0"), "r1", DRIVE, RESISTANCE)


@pytest.mark.parametrize("declaration", [
    {"origin": "design", "reference": "x"},
    {**RESISTANCE, "value": "1"},
    {**RESISTANCE, "R": "1"},
    {**RESISTANCE, "scale": "infer_from_state"},
    {**RESISTANCE, "scale": {**SCALE, "attention_unit": "other"}},
    {**RESISTANCE, "origin": "measured"},
    {**RESISTANCE, "reference": ""},
])
def test_resistor_units_and_provenance_cannot_be_missing_or_overridden(declaration):
    with pytest.raises(ValueError):
        links.pcba_resistor_flow(BOARD, "r1", DRIVE, declaration)


def test_supplied_observations_stay_unverified():
    drive = {**DRIVE, "origin": "supplied_observation", "reference": "caller-report-12"}
    result = links.pcba_resistor_flow(BOARD, "r1", drive, RESISTANCE)
    assert result["quantity_report"]["inputs"][0]["observation_status"] == "CALLER_SUPPLIED_UNVERIFIED"
    assert result["measurement_status"] == "NO_MEASUREMENT_PERFORMED"


@pytest.mark.parametrize("operation,first_kind,second_kind,a,b,expected", [
    ("ohm_flow", "drive", "constraint", "12", "4", "3"),
    ("ohm_required_drive", "attention", "constraint", "3", "4", "12"),
    ("ohm_effective_constraint", "drive", "attention", "12", "3", "4"),
])
def test_demo_uses_actual_compiler_and_separates_input_and_reference(operation, first_kind, second_kind, a, b, expected):
    source = expression(operation, first_kind, second_kind, a, b)
    result = links.make_synthetic_demo(source, "fixture")
    compiler, _, _ = links._runtime()
    assert result["target"]["quantity_report"] == compiler.compile_expression(source).to_dict()["result"]
    assert result["target"]["quantity_report"]["value"] == expected
    assert result["target"]["status"] == "REFERENCE_CALCULATED_NOT_LEARNED"
    assert set(result["observation"]) == {"schema", "expression", "reference_id", "implementation_sha256_lf", "fixture_status", "record_id"}
    assert result["target"]["observation_id"] == result["observation"]["record_id"]
    assert result["training_status"] == "NOT_RUN"
    assert links.make_synthetic_demo(source, "fixture") == result


def test_demo_content_and_source_id_are_bound():
    first = links.make_synthetic_demo(expression(), "fixture")
    other = links.make_synthetic_demo(expression(second="6"), "fixture")
    renamed = links.make_synthetic_demo(expression(), "another")
    assert len({pair["observation"]["record_id"] for pair in (first, other, renamed)}) == 3
    input_body = {key: value for key, value in first["observation"].items() if key != "record_id"}
    target_body = {key: value for key, value in first["target"].items() if key != "record_id"}
    assert first["observation"]["record_id"] == "ohm-demo-input-" + links._digest(input_body)
    assert first["target"]["record_id"] == "ohm-demo-target-" + links._digest(target_body)
    assert set(input_body["implementation_sha256_lf"]) == {"compiler.py", "cas_ohm.py"}
    changed = deepcopy(input_body)
    changed["implementation_sha256_lf"]["compiler.py"] = "0" * 64
    assert links._digest(changed) != links._digest(input_body)


@pytest.mark.parametrize("source", [
    '^8^C', '1 + 2', 'use "outside.cas";', 'let x = 12; x;',
    'ohm_scale("x", "d", "a")', 'ohm_flow(foo(), foo())',
    'ohm_flow(ohm_drive(1, something, "design", "x"), 2)',
    expression(second="0"), expression(first="NaN"), expression(first="-1"),
    expression().replace('"design"', '"measured"'),
    expression().replace('ohm_constraint', 'ohm_drive'),
    expression() + '; ' + expression(), "x" * (links.MAX_EXPRESSION_BYTES + 1), "\ud800",
])
def test_demo_rejects_other_capabilities_or_invalid_calculations(source):
    with pytest.raises(links.OhmConnectionError):
        links.make_synthetic_demo(source, "fixture")


def test_repeating_decimal_preserves_exact_fraction_in_projection():
    report = calculated("1", "3")
    result = links.project_cas_rpa([row("one", report=report)])
    copied = result["nodes"][0]["quantity_report"]
    assert copied == report
    assert copied["exact_value"] == {"numerator": "1", "denominator": "3"}
    assert copied["decimal_is_rounded"]


def test_projection_keeps_parent_and_children_separate_without_aggregation():
    parent, child_a, child_b = calculated("12", "4"), calculated("40", "2"), calculated("1", "20")
    rows = [row("child_b", "parent", child_b), row("parent", report=parent), row("child_a", "parent", child_a)]
    original = deepcopy(rows)
    projected = links.project_cas_rpa(rows)
    assert rows == original
    assert projected == links.project_cas_rpa(list(reversed(rows)))
    assert projected["roots"] == ["parent"]
    indexed = {item["node_id"]: item for item in projected["nodes"]}
    assert indexed["parent"]["children"] == ["child_a", "child_b"]
    assert indexed["parent"]["quantity_report"]["value"] == "3"
    assert indexed["child_a"]["quantity_report"]["value"] == "20"
    assert indexed["child_b"]["quantity_report"]["value"] == "0.05"
    assert projected["aggregation_status"] == "NONE_NO_TOTAL_INFERRED"
    assert projected["status"] == "PREPARATORY_NOT_INTEGRATED"
    assert projected["authority"] == "NONE"
    indexed["parent"]["quantity_report"]["value"] = "tamper"
    assert rows == original


@pytest.mark.parametrize("shape,code", [
    ([("a", None), ("a", None)], "OHM_RPA_DUPLICATE"),
    ([("a", "a")], "OHM_RPA_CYCLE"),
    ([("a", "b"), ("b", "a")], "OHM_RPA_CYCLE"),
    ([("a", "missing")], "OHM_RPA_PARENT"),
    ([("a", None), ("b", "missing")], "OHM_RPA_PARENT"),
    ([("bad/name", None)], "OHM_CONNECTION_ID"),
])
def test_projection_rejects_bad_parent_structure(shape, code):
    with pytest.raises(links.OhmConnectionError, match=code):
        links.project_cas_rpa([row(name, parent) for name, parent in shape])


@pytest.mark.parametrize("field,value", [
    ("value", "999"), ("exact_value", {"numerator": "999", "denominator": "1"}),
    ("origin", "measured"), ("measurement_status", "MEASURED"),
    ("operation", "required_drive"), ("quantity", "drive"), ("quantity", []),
    ("record_sha256", "0" * 64), ("unit", "volts"), ("notes", ["VERIFIED"]),
])
def test_forged_report_is_rejected_even_after_rehash(field, value):
    report = calculated()
    report[field] = value
    # A new matching hash does not prove the formula or its origin.
    if field != "record_sha256":
        report["record_sha256"] = links._digest({key: item for key, item in report.items() if key != "record_sha256"})
    with pytest.raises(ValueError):
        links.project_cas_rpa([row("a", report=report)])


def test_forged_input_or_scale_does_not_sneak_through_lineage():
    for mutate in (lambda r: r["inputs"][0].update(value="999"),
                   lambda r: r["inputs"][1]["scale"].update(drive_unit="changed"),
                   lambda r: r["inputs"][0].update(observation_status="VERIFIED")):
        report = calculated()
        mutate(report)
        with pytest.raises(ValueError):
            links.project_cas_rpa([row("a", report=report)])


def test_bare_declarations_are_not_projected_as_calculations():
    with pytest.raises(links.OhmConnectionError, match="calculated reports"):
        links.project_cas_rpa([row("a", report=calculated()["inputs"][0])])


def test_projection_bounds_and_cyclic_python_containers():
    report = calculated()
    assert links.project_cas_rpa([row("n" + str(i), "n" + str(i - 1) if i else None, report) for i in range(32)])
    with pytest.raises(links.OhmConnectionError, match="depth exceeds 32"):
        links.project_cas_rpa([row("n" + str(i), "n" + str(i - 1) if i else None, report) for i in range(33)])
    with pytest.raises(links.OhmConnectionError):
        links.project_cas_rpa([row("a", report=report)] * 513)
    with pytest.raises(links.OhmConnectionError):
        links.project_cas_rpa([])
    cyclic = row("a", report=report)
    cyclic["quantity_report"] = cyclic
    with pytest.raises(links.OhmConnectionError, match="Cyclic input"):
        links.project_cas_rpa([cyclic])
    huge = row("a", report=report)
    huge["quantity_report"] = {"padding": "x" * (links.MAX_PROJECTION_BYTES + 1)}
    with pytest.raises(links.OhmConnectionError):
        links.project_cas_rpa([huge])


def test_large_integer_report_replay_ignores_global_int_text_policy():
    _, helper, _ = links._runtime()
    scale = helper.make_scale(**SCALE)
    previous = sys.get_int_max_str_digits()
    try:
        sys.set_int_max_str_digits(640)
        drive = helper.make_quantity("drive", 1 << 3000, scale, "design", "large-drive")
        resistance = helper.make_quantity("constraint", 4, scale, "design", "resistance")
        report = helper.attention_flow(drive, resistance).to_dict()
        result = links.project_cas_rpa([row("large", report=report)])
        assert result["nodes"][0]["quantity_report"] == report
    finally:
        sys.set_int_max_str_digits(previous)


def test_large_keys_and_aggregate_text_rejected_before_json_serialization(monkeypatch):
    def forbidden(value):
        raise AssertionError("oversized object reached JSON serializer")
    monkeypatch.setattr(links, "_json", forbidden)
    for value in ({"k" * 257: None}, {"a" * 100: "x" * 100, "b" * 100: None}):
        with pytest.raises(links.OhmConnectionError, match="aggregate budget"):
            links._bounded_json(value, 256)


def test_source_change_during_calculation_is_not_bound_to_old_identity(monkeypatch):
    compiler, _, original = links._runtime()
    real = compiler.compile_expression
    def changed(source):
        value = real(source)
        monkeypatch.setattr(links, "_source_binding", lambda: {**original, "cas_ohm.py": "0" * 64})
        return value
    monkeypatch.setattr(compiler, "compile_expression", changed)
    with pytest.raises(links.OhmConnectionError, match="changed during calculation"):
        links.make_synthetic_demo(expression(), "fixture")


def test_loaded_helper_receipt_matches_consumed_bytes_and_cached_mismatch_refuses(monkeypatch):
    _, helper, binding = links._runtime()
    assert helper.__cas_ohm_source_sha256_lf__ == binding["cas_ohm.py"]
    monkeypatch.setattr(helper, "__cas_ohm_source_sha256_lf__", "0" * 64)
    with pytest.raises(links.OhmConnectionError, match="Loaded helper bytes"):
        links.make_synthetic_demo(expression(), "fixture")


def test_outputs_are_json_finite_and_no_protected_dataset_imports():
    before = set(sys.modules)
    for result in (links.pcba_resistor_flow(BOARD, "r1", DRIVE, RESISTANCE),
                   links.make_synthetic_demo(expression(), "fixture"),
                   links.project_cas_rpa([row("a")])):
        json.dumps(result, allow_nan=False)
    assert not any(name.startswith(("torch", "cas_forex", "q3_behaviour_records", "q4_")) for name in set(sys.modules) - before)
