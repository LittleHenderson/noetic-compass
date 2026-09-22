"""Independent tests of explicit-scale CAS-Ohm arithmetic, without an app runtime.

Book basis: CAS_PCBA_Engineer/Chapter_05_Resistors.md lines 29-57 (raw SHA256
105ef2f963bcf679ae4b96724505e4512f553a127afb63da7e95f2ba998e28b1).
The helper's declared ratio scale is an implementation convention. It does not
silently select the incompatible Guide, Appendix I, or Grimoire profiles.
"""

from decimal import ROUND_DOWN, ROUND_UP, localcontext
from fractions import Fraction
import importlib.util
import json
from pathlib import Path
import sys

import pytest


# Load only this dependency-free numeric helper. Importing api.notation would
# also initialize the compiler and optional engine, irrelevant to this suite.
_HELPER_PATH = Path(__file__).resolve().parents[1] / "api" / "notation" / "cas_ohm.py"
_SPEC = importlib.util.spec_from_file_location("_cas_ohm_numeric_under_test", _HELPER_PATH)
ohm = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = ohm
_SPEC.loader.exec_module(ohm)


@pytest.fixture
def scale():
    return ohm.make_scale("illustrative-design", "declared-drive", "declared-attention")


def quantity(scale, kind, value, origin="design", reference="independent fixture"):
    return ohm.make_quantity(kind, value, scale, origin, reference)


def exact(record):
    return Fraction(int(record["exact_value"]["numerator"]),
                    int(record["exact_value"]["denominator"]))


def error(code, operation, *args):
    with pytest.raises(ohm.CasOhmError) as caught:
        operation(*args)
    assert caught.value.code == code
    return caught.value


def assert_calculation(result, kind, expected, operation):
    record = result.to_dict()
    assert result.value == expected
    assert exact(record) == expected
    assert record["quantity"] == kind
    assert record["origin"] == "calculated"
    assert record["operation"] == operation
    assert len(record["inputs"]) == 2
    assert record["numeric_representation"] == "exact_rational"
    assert record["measurement_status"] == "NO_MEASUREMENT_PERFORMED"
    assert record["observation_status"] == "NOT_AN_OBSERVATION"
    assert record["control_status"] == "NOT_CONNECTED"
    assert record["semantic_outcome"] == "NOT_ASSESSED"
    assert len(record["record_sha256"]) == 64
    json.dumps(record, allow_nan=False)
    return record


def test_requested_twelve_drive_example_and_local_constraint_change(scale):
    drive = quantity(scale, "drive", 12)
    baseline = ohm.attention_flow(drive, quantity(scale, "constraint", 4))
    changed = ohm.attention_flow(drive, quantity(scale, "constraint", 6))
    assert_calculation(baseline, "attention", Fraction(3), "attention_flow")
    assert_calculation(changed, "attention", Fraction(2), "attention_flow")
    assert drive.value == 12


def test_required_drive_is_attention_times_constraint(scale):
    result = ohm.required_drive(quantity(scale, "attention", 3),
                                quantity(scale, "constraint", 4))
    assert_calculation(result, "drive", Fraction(12), "required_drive")


def test_effective_constraint_is_inverse_ratio_not_causal_diagnosis(scale):
    result = ohm.effective_constraint(
        quantity(scale, "drive", 12),
        quantity(scale, "attention", 3, "supplied_observation", "provided run A"),
    )
    record = assert_calculation(result, "constraint", Fraction(4), "effective_constraint")
    assert "INVERSE_RATIO_NOT_CAUSAL_IDENTIFICATION" in record["notes"]


def test_all_three_operations_preserve_exact_high_precision(scale):
    drive = quantity(scale, "drive", "1.0000000000000001")
    resistance = quantity(scale, "constraint", "0.99999999999999994")
    flow = ohm.attention_flow(drive, resistance)
    expected = Fraction("1.0000000000000001") / Fraction("0.99999999999999994")
    assert_calculation(flow, "attention", expected, "attention_flow")
    assert ohm.required_drive(flow, resistance).value == drive.value
    assert ohm.effective_constraint(drive, flow).value == resistance.value


def test_repeating_decimal_keeps_exact_rational_and_marks_display_rounding(scale):
    result = ohm.attention_flow(quantity(scale, "drive", 1),
                                quantity(scale, "constraint", 3))
    record = assert_calculation(result, "attention", Fraction(1, 3), "attention_flow")
    assert record["decimal_is_rounded"] is True
    assert record["exact_value"] == {"numerator": "1", "denominator": "3"}


def test_terminating_decimal_reports_exact_display(scale):
    result = ohm.attention_flow(quantity(scale, "drive", 1),
                                quantity(scale, "constraint", 8))
    record = result.to_dict()
    assert record["value"] == "0.125"
    assert record["decimal_is_rounded"] is False


@pytest.mark.parametrize("value", [
    None, True, False, float("nan"), float("inf"), float("-inf"),
    -1, -0.5, "-0.00001", "NaN", "Infinity", "-Infinity", "1e3",
    "", " ", " 1", "1 ", "1/3", "one", "^8^C_{F2}|A", [], {}, object(),
])
def test_invalid_or_missing_numeric_values_fail_explicitly(scale, value):
    error("OHM_NUMBER", quantity, scale, "drive", value)


@pytest.mark.parametrize("kind", ["drive", "attention", "constraint"])
def test_zero_is_an_explicit_nonnegative_quantity_not_missing(scale, kind):
    result = quantity(scale, kind, "0")
    assert result.value == 0
    assert result.to_dict()["input_literal"] == "0"


@pytest.mark.parametrize("drive", [0, 12])
def test_flow_refuses_zero_constraint_including_zero_over_zero(scale, drive):
    error("OHM_ZERO_CONSTRAINT", ohm.attention_flow,
          quantity(scale, "drive", drive), quantity(scale, "constraint", 0))


@pytest.mark.parametrize("drive", [0, 12])
def test_inverse_ratio_refuses_zero_attention_including_zero_over_zero(scale, drive):
    error("OHM_ZERO_ATTENTION", ohm.effective_constraint,
          quantity(scale, "drive", drive), quantity(scale, "attention", 0))


def test_tiny_positive_denominator_is_not_replaced_by_epsilon(scale):
    tiny = "0." + "0" * 499 + "1"
    result = ohm.attention_flow(quantity(scale, "drive", 1),
                                quantity(scale, "constraint", tiny))
    assert result.value == 10 ** 500
    assert exact(result.to_dict()) == 10 ** 500


@pytest.mark.parametrize("attention,resistance", [(0, 4), (3, 0), (0, 0)])
def test_required_drive_preserves_zero_factor_degeneracy(scale, attention, resistance):
    result = ohm.required_drive(quantity(scale, "attention", attention),
                                quantity(scale, "constraint", resistance))
    record = assert_calculation(result, "drive", Fraction(0), "required_drive")
    assert "ZERO_FACTOR_DEGENERATE_DESIGN" in record["notes"]


def test_zero_drive_positive_observed_flow_is_explicit_degenerate_inverse(scale):
    result = ohm.effective_constraint(quantity(scale, "drive", 0),
                                      quantity(scale, "attention", 3))
    record = assert_calculation(result, "constraint", Fraction(0), "effective_constraint")
    assert "ZERO_CONSTRAINT_DEGENERATE_RATIO" in record["notes"]


def test_zero_drive_positive_constraint_has_zero_flow(scale):
    result = ohm.attention_flow(quantity(scale, "drive", 0),
                                quantity(scale, "constraint", 3))
    assert_calculation(result, "attention", Fraction(0), "attention_flow")


@pytest.mark.parametrize("other_scale", [
    ("illustrative-design", "different-drive", "declared-attention"),
    ("illustrative-design", "declared-drive", "different-attention"),
    ("another-design", "declared-drive", "declared-attention"),
])
def test_full_scale_descriptor_must_match_not_only_identifier(scale, other_scale):
    other = ohm.make_scale(*other_scale)
    error("OHM_SCALE_MISMATCH", ohm.attention_flow,
          quantity(scale, "drive", 12), quantity(other, "constraint", 4))


def test_equal_independently_declared_scales_are_compatible(scale):
    other = ohm.make_scale("illustrative-design", "declared-drive", "declared-attention")
    assert other is not scale
    result = ohm.attention_flow(quantity(scale, "drive", 12),
                                quantity(other, "constraint", 4))
    assert result.value == 3
    assert scale.to_dict() == other.to_dict()


def test_constraint_units_are_explicit_ratio_and_calibration_is_unverified(scale):
    descriptor = scale.to_dict()
    assert descriptor["constraint_unit"] == "(declared-drive)/(declared-attention)"
    assert descriptor["status"] == "USER_DECLARED_COHERENT_RATIO_SCALE"
    assert descriptor["calibration_status"] == "NOT_VERIFIED"
    assert len(descriptor["descriptor_sha256"]) == 64


def test_no_implicit_guide_range_clipping_or_domain_drop(scale):
    # Guide's V<=10 and Grimoire's I<=1 are not this explicit ratio convention.
    result = ohm.attention_flow(quantity(scale, "drive", 12),
                                quantity(scale, "constraint", 4))
    assert result.value == 3
    high = ohm.required_drive(quantity(scale, "attention", 100),
                              quantity(scale, "constraint", 1000))
    assert high.value == 100000


@pytest.mark.parametrize("field", [0, 1, 2])
@pytest.mark.parametrize("invalid", [None, True, 3, "", "   ", "\n", "bad\x00unit", "x" * 129])
def test_missing_invalid_scale_metadata_is_rejected(field, invalid):
    fields = ["id", "drive", "attention"]
    fields[field] = invalid
    error("OHM_METADATA", ohm.make_scale, *fields)


@pytest.mark.parametrize("reference", [None, False, "", "   ", "line\nbreak", "x" * 257])
def test_quantity_requires_a_valid_provenance_reference(scale, reference):
    error("OHM_METADATA", quantity, scale, "drive", 1, "design", reference)


@pytest.mark.parametrize("origin", [None, "", "measured", "instrumented", "calculated", 4])
def test_input_cannot_claim_an_unimplemented_or_calculated_origin(scale, origin):
    error("OHM_ORIGIN", quantity, scale, "drive", 1, origin, "reference")


@pytest.mark.parametrize("kind", ["current", "V", "", None, [], {}])
def test_unknown_quantity_kind_is_rejected(scale, kind):
    error("OHM_KIND", quantity, scale, kind, 1)


@pytest.mark.parametrize("bad_scale", [None, {}, "scale-id", 1])
def test_quantity_cannot_omit_the_complete_scale(bad_scale):
    error("OHM_SCALE", ohm.make_quantity, "drive", 1, bad_scale, "design", "reference")


@pytest.mark.parametrize("operation,kinds", [
    (ohm.attention_flow, ("attention", "constraint")),
    (ohm.attention_flow, ("constraint", "drive")),
    (ohm.required_drive, ("drive", "constraint")),
    (ohm.effective_constraint, ("drive", "constraint")),
])
def test_operation_checks_ordered_quantity_roles(scale, operation, kinds):
    error("OHM_KIND", operation,
          quantity(scale, kinds[0], 2), quantity(scale, kinds[1], 3))


@pytest.mark.parametrize("bad", [None, 0, 3.0, "12", {}, []])
def test_operations_do_not_accept_untyped_or_missing_operands(scale, bad):
    error("OHM_KIND", ohm.attention_flow, bad, quantity(scale, "constraint", 4))


def test_supplied_observations_remain_unverified_inside_calculated_lineage(scale):
    drive = quantity(scale, "drive", "12", "supplied_observation", "caller trace 7")
    constraint = quantity(scale, "constraint", "4", "design", "design specification 2")
    record = ohm.attention_flow(drive, constraint).to_dict()
    assert record["origin"] == "calculated"
    observed, designed = record["inputs"]
    assert observed["origin"] == "supplied_observation"
    assert observed["reference"] == "caller trace 7"
    assert observed["observation_status"] == "CALLER_SUPPLIED_UNVERIFIED"
    assert observed["measurement_status"] == "NO_MEASUREMENT_PERFORMED"
    assert designed["origin"] == "design"
    assert designed["reference"] == "design specification 2"
    assert record["measurement_status"] == "NO_MEASUREMENT_PERFORMED"
    assert record["semantic_outcome"] == "NOT_ASSESSED"


def test_reference_and_origin_change_record_identity_without_changing_arithmetic(scale):
    first = quantity(scale, "drive", 12, "design", "design one")
    same = quantity(scale, "drive", 12, "design", "design one")
    other = quantity(scale, "drive", 12, "design", "design two")
    observed = quantity(scale, "drive", 12, "supplied_observation", "design one")
    assert first.to_dict() == same.to_dict()
    assert len({q.to_dict()["record_sha256"] for q in (first, other, observed)}) == 3
    assert first.value == other.value == observed.value


def test_float_input_reports_its_lossy_input_route_while_text_preserves_literal(scale):
    floating = quantity(scale, "drive", 0.1).to_dict()
    textual = quantity(scale, "drive", "0.10000000000000000001").to_dict()
    assert floating["numeric_representation"] == "binary_float_via_shortest_decimal"
    assert floating["input_literal"] == "0.1"
    assert textual["numeric_representation"] == "exact_decimal_text"
    assert textual["input_literal"] == "0.10000000000000000001"
    assert exact(textual) == Fraction("0.10000000000000000001")
    assert exact(floating) != exact(textual)


def test_returned_report_mutation_does_not_change_immutable_quantity(scale):
    result = ohm.attention_flow(quantity(scale, "drive", 12),
                                quantity(scale, "constraint", 4))
    original = result.to_dict()
    edited = result.to_dict()
    edited["inputs"][0]["reference"] = "tampered"
    edited["scale"]["drive_unit"] = "tampered"
    assert result.to_dict() == original


def test_numeric_input_budget_is_explicit(scale):
    error("OHM_LIMIT", quantity, scale, "drive", "1" * 513)
    error("OHM_LIMIT", quantity, scale, "drive", 1 << 4096)


def test_numeric_result_budget_stops_growth_before_serialization(scale):
    value = 1 << 3000
    attention = quantity(scale, "attention", value)
    constraint = quantity(scale, "constraint", value)
    error("OHM_LIMIT", ohm.required_drive, attention, constraint)


def test_lineage_depth_is_bounded_through_normal_operations(scale):
    constraint = quantity(scale, "constraint", 1)
    result = quantity(scale, "drive", 1)
    for _ in range(15):
        result = (ohm.attention_flow(result, constraint) if result.quantity == "drive"
                  else ohm.required_drive(result, constraint))
    assert result.depth == 16
    operation = ohm.attention_flow if result.quantity == "drive" else ohm.required_drive
    error("OHM_LIMIT", operation, result, constraint)


def test_lineage_node_budget_also_limits_wide_shared_derivations(scale):
    drive = quantity(scale, "drive", 1)
    constraint = quantity(scale, "constraint", 1)
    for _ in range(4):
        attention = ohm.attention_flow(drive, constraint)
        old_drive = drive
        drive = ohm.required_drive(attention, constraint)
        constraint = ohm.effective_constraint(old_drive, attention)
    assert drive.depth < 16 and constraint.depth < 16
    assert drive.node_count == constraint.node_count == 161
    error("OHM_LIMIT", ohm.attention_flow, drive, constraint)


def test_decimal_display_and_record_hash_do_not_depend_on_ambient_rounding(scale):
    result = ohm.attention_flow(quantity(scale, "drive", 1),
                                quantity(scale, "constraint", 3))
    with localcontext() as context:
        context.rounding = ROUND_DOWN
        down = result.to_dict()
    with localcontext() as context:
        context.rounding = ROUND_UP
        up = result.to_dict()
    assert down == up


def test_decimal_display_does_not_inherit_host_exponent_or_precision_limits(scale):
    result = ohm.attention_flow(quantity(scale, "drive", 1000),
                                quantity(scale, "constraint", 1))
    baseline = result.to_dict()
    with localcontext() as context:
        context.prec = 2
        context.Emax = 2
        context.Emin = -2
        assert result.to_dict() == baseline


def _derived_fields(scale):
    return {
        "quantity": "attention", "value": Fraction(3), "scale": scale,
        "origin": "calculated", "reference": ohm.VERSION + ":attention_flow",
        "representation": "exact_rational", "operation": "attention_flow",
        "inputs": (quantity(scale, "drive", 12), quantity(scale, "constraint", 4)),
    }


@pytest.mark.parametrize("field,value", [
    ("value", Fraction(99)), ("quantity", "drive"),
    ("representation", "integer"), ("literal", "3"),
    ("operation", "unimplemented_operation"), ("inputs", []),
    ("inputs", (None, None)), ("notes", ["mutable note"]),
])
def test_direct_calculated_construction_cannot_forge_derivation(scale, field, value):
    fields = _derived_fields(scale)
    fields[field] = value
    with pytest.raises(ohm.CasOhmError) as caught:
        ohm.OhmQuantity(**fields)
    assert caught.value.code == "OHM_PROVENANCE"


def test_direct_calculated_construction_checks_result_scale(scale):
    fields = _derived_fields(scale)
    fields["scale"] = ohm.make_scale("other", "other-drive", "other-attention")
    with pytest.raises(ohm.CasOhmError) as caught:
        ohm.OhmQuantity(**fields)
    assert caught.value.code == "OHM_PROVENANCE"


def test_direct_calculated_construction_refuses_zero_denominator(scale):
    fields = _derived_fields(scale)
    fields["inputs"] = (quantity(scale, "drive", 0), quantity(scale, "constraint", 0))
    fields["value"] = Fraction(0)
    with pytest.raises(ohm.CasOhmError) as caught:
        ohm.OhmQuantity(**fields)
    assert caught.value.code == "OHM_PROVENANCE"


def test_direct_input_declaration_cannot_hide_a_calculation(scale):
    fields = _derived_fields(scale)
    fields["origin"] = "design"
    with pytest.raises(ohm.CasOhmError) as caught:
        ohm.OhmQuantity(**fields)
    assert caught.value.code == "OHM_PROVENANCE"


def _input_fields(scale):
    return {
        "quantity": "drive", "value": Fraction(1), "scale": scale,
        "origin": "design", "reference": "independent declared input",
        "representation": "exact_decimal_text", "literal": "1",
    }


@pytest.mark.parametrize("origin", ["design", "supplied_observation"])
def test_direct_declared_input_must_match_its_literal(scale, origin):
    fields = _input_fields(scale)
    fields.update(value=Fraction(2), origin=origin)
    with pytest.raises(ohm.CasOhmError) as caught:
        ohm.OhmQuantity(**fields)
    assert caught.value.code == "OHM_PROVENANCE"


@pytest.mark.parametrize("field,value", [
    ("representation", None), ("representation", []), ("representation", {}),
    ("representation", 1), ("representation", "instrumented"),
    ("literal", None), ("literal", 1), ("literal", 1.0),
    ("literal", True), ("literal", []), ("literal", {}),
    ("notes", ("MEASURED",)),
])
def test_direct_input_metadata_cannot_bypass_factory_validation(scale, field, value):
    fields = _input_fields(scale)
    fields[field] = value
    with pytest.raises(ohm.CasOhmError) as caught:
        ohm.OhmQuantity(**fields)
    assert caught.value.code == "OHM_PROVENANCE"


@pytest.mark.parametrize("representation,literal", [
    ("integer", "01"), ("integer", "+1"), ("integer", "1.0"),
    ("binary_float_via_shortest_decimal", "1.00"),
    ("binary_float_via_shortest_decimal", "1e0"),
    ("binary_float_via_shortest_decimal", " 1.0"),
])
def test_direct_machine_input_literals_must_be_canonical(scale, representation, literal):
    fields = _input_fields(scale)
    fields.update(representation=representation, literal=literal)
    with pytest.raises(ohm.CasOhmError) as caught:
        ohm.OhmQuantity(**fields)
    assert caught.value.code == "OHM_PROVENANCE"


@pytest.mark.parametrize("representation,literal", [
    ("integer", "1"), ("exact_decimal_text", "1.000"),
    ("binary_float_via_shortest_decimal", "1.0"),
])
def test_valid_direct_input_reconstruction_remains_serializable(scale, representation, literal):
    fields = _input_fields(scale)
    fields.update(representation=representation, literal=literal)
    result = ohm.OhmQuantity(**fields).to_dict()
    assert exact(result) == 1
    assert result["input_literal"] == literal
    json.dumps(result, allow_nan=False)


def test_valid_direct_calculated_reconstruction_remains_serializable(scale):
    result = ohm.OhmQuantity(**_derived_fields(scale))
    assert_calculation(result, "attention", Fraction(3), "attention_flow")


@pytest.mark.parametrize("field,value", [
    ("notes", ("MEASURED",)), ("reference", "sensor observation"),
])
def test_direct_result_cannot_change_its_calculation_reference_or_notes(scale, field, value):
    fields = _derived_fields(scale)
    fields[field] = value
    with pytest.raises(ohm.CasOhmError) as caught:
        ohm.OhmQuantity(**fields)
    assert caught.value.code == "OHM_PROVENANCE"
