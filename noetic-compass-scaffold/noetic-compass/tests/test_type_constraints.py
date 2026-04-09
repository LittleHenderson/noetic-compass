"""Tests for CAS-Native type constraints (pure validation, no PyTorch required)."""

import importlib
import sys
from pathlib import Path

# Import type_constraints directly to avoid torch-dependent model/__init__.py
_cas_native_root = Path(__file__).resolve().parent.parent / "cas-native"
_tc_path = _cas_native_root / "model" / "type_constraints.py"
spec = importlib.util.spec_from_file_location("type_constraints", _tc_path)
_tc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_tc)

validate_operator_output = _tc.validate_operator_output
validate_involution_roundtrip = _tc.validate_involution_roundtrip
validate_domain_descent = _tc.validate_domain_descent
validate_rpm_chain = _tc.validate_rpm_chain
validate_fractal_type = _tc.validate_fractal_type


class TestOperatorValidation:
    def test_co0_identity_valid(self):
        assert validate_operator_output(0, 0.5, 0.5) is True

    def test_co0_identity_invalid(self):
        assert validate_operator_output(0, 0.5, 0.8) is False

    def test_non_identity_in_range(self):
        assert validate_operator_output(3, 0.5, 0.7) is True

    def test_non_identity_out_of_range(self):
        assert validate_operator_output(3, 0.5, 1.5) is False


class TestInvolutionRoundtrip:
    def test_co2_co3_roundtrip_valid(self):
        assert validate_involution_roundtrip(2, 3, 0.5, 0.5) is True

    def test_co2_co3_roundtrip_invalid(self):
        assert validate_involution_roundtrip(2, 3, 0.5, 0.9) is False

    def test_non_pair_always_valid(self):
        assert validate_involution_roundtrip(1, 4, 0.5, 0.9) is True


class TestDomainDescent:
    def test_valid_descent(self):
        assert validate_domain_descent(0.8, 0.7, 0.6, 0.5) is True

    def test_operational_exceeds_principled(self):
        assert validate_domain_descent(0.3, 0.5, 0.6, 0.9) is False

    def test_equal_valid(self):
        assert validate_domain_descent(0.5, 0.5, 0.5, 0.5) is True


class TestRpmChain:
    def test_valid_chain(self):
        assert validate_rpm_chain(0.8, 0.7, 0.6) is True

    def test_power_without_wisdom(self):
        assert validate_rpm_chain(0.8, 0.3, 0.7) is False

    def test_wisdom_without_desire(self):
        assert validate_rpm_chain(0.3, 0.7, 0.6) is False

    def test_all_below_threshold(self):
        assert validate_rpm_chain(0.2, 0.3, 0.4) is True

    def test_only_desire(self):
        assert validate_rpm_chain(0.8, 0.3, 0.2) is True


class TestFractalType:
    def test_valid(self):
        assert validate_fractal_type([1, 4, 7]) is True

    def test_empty(self):
        assert validate_fractal_type([]) is False

    def test_out_of_range(self):
        assert validate_fractal_type([1, 15, 3]) is False

    def test_identity(self):
        assert validate_fractal_type([0]) is True
