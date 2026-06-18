"""PCBA component syntax integration with the real CAS compiler."""

from cas_forex.pcba_compiler import (
    compile_pcba_component_expression,
    pcba_compiler_integration_passes,
)


COMPILER_CHECKABLE_PCBA = [
    "Resistor< ^8^C_{F2}|A, R=50 >",
    "OpAmp< non_inverting=^8^C_{F2}|A, inverting=^6^E_{F6}|A, output=^9^C_{F2}|A, open_loop_gain=10000 >",
    "Oscillator< Phi< ^8^C|A, ^3^O|E, ^9^E|f, ^0^P|T >, frequency=0.0000116 >",
    "Trace< ^2^P -> ^2^C >",
    "Via< layer=P, to_layer=C, transition=^2^P->^2^C >",
]


def test_pcba_compiler_integration_compiles_embedded_cas_expressions():
    for expression in COMPILER_CHECKABLE_PCBA:
        report = compile_pcba_component_expression(expression)
        assert report.compiler_available
        assert report.checked_count > 0
        assert report.valid, report.model_dump()
        assert all(check.valid for check in report.checked_expressions)


def test_pcba_compiler_integration_batch_passes_for_checkable_subset():
    assert pcba_compiler_integration_passes(COMPILER_CHECKABLE_PCBA)


def test_pcba_compiler_integration_rejects_invalid_embedded_cas():
    report = compile_pcba_component_expression("Resistor< ^2^Z_{F2}|A, R=50 >")

    assert report.checked_count == 1
    assert not report.valid
    assert not report.checked_expressions[0].valid


def test_pcba_shorthand_only_components_remain_diagnostic_not_production_syntax():
    report = compile_pcba_component_expression("Diode< ^P -> ^C >")

    assert report.checked_count == 0
    assert not report.valid
    assert report.skipped_shorthand == ["^C", "^P"]
