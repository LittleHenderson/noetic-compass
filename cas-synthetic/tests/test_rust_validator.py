"""Integration tests for rust_validator against the vendored cas_engine wheel."""

from __future__ import annotations

import pytest

from cas_synthetic.validation import RustValidator, RustValidatorUnavailable
from cas_synthetic.generator import V77RuleFourGenerator


@pytest.fixture
def rust() -> RustValidator:
    try:
        return RustValidator()
    except RustValidatorUnavailable as exc:
        pytest.skip(f"Rust engine unavailable: {exc}")


class TestRustValidator:
    def test_importable(self, rust: RustValidator):
        assert rust.cas_engine is not None
        assert hasattr(rust.cas_engine, "validate_same_noetic_cross_product_batch")

    def test_empty_batch(self, rust: RustValidator):
        assert rust.evaluate_rule_four([]) == []
        assert rust.evaluate_named_emergent([]) == []

    def test_non_applicable_expression(self, rust: RustValidator):
        ex = {"cas_expression": "^0^P_{F1}"}  # no cross product
        results = rust.evaluate_rule_four([ex])
        assert len(results) == 1
        assert results[0]["applicable"] is False
        assert results[0]["is_valid"] is True
        assert results[0]["distance"] == 0.0

    def test_violation_detected(self, rust: RustValidator):
        ex = {"cas_expression": "^3^P|A_{F1} x ^3^P|f_{F1}"}
        results = rust.evaluate_rule_four([ex])
        assert results[0]["applicable"] is True
        assert results[0]["is_valid"] is False
        assert results[0]["distance"] > 0

    def test_valid_emergent_recognized(self, rust: RustValidator):
        ex = {
            "cas_expression": "(^3^P|A x ^3^P|f x ^3^P|T) = ^3^P|Omega_refusal"
        }
        results = rust.evaluate_rule_four([ex])
        assert results[0]["applicable"] is True
        assert results[0]["is_valid"] is True
        assert results[0]["distance"] == 0.0

    def test_different_noetics_not_applicable(self, rust: RustValidator):
        """Rule 4 applies only to same-Noetic cross products."""
        ex = {"cas_expression": "^2^P|A x ^3^P|f"}
        results = rust.evaluate_rule_four([ex])
        assert results[0]["applicable"] is False

    def test_named_emergent_verify_valid(self, rust: RustValidator):
        ex = {
            "cas_expression": "(^3^P|A x ^3^P|f x ^3^P|T) = ^3^P|Omega_refusal",
            "register_labels": [
                {"position": 0, "register": "A"},
                {"position": 1, "register": "f"},
                {"position": 2, "register": "T"},
            ],
            "omega_labels": [{"position": 0, "omega_name": "Omega_refusal"}],
        }
        results = rust.evaluate_named_emergent([ex])
        assert results[0]["applicable"] is True
        assert results[0]["is_valid"] is True

    def test_batch_mixed(self, rust: RustValidator):
        examples = [
            {"cas_expression": "^0^P_{F1}"},                              # n/a
            {"cas_expression": "^3^P|A_{F1} x ^3^P|f_{F1}"},              # violation
            {"cas_expression": "(^1|A x ^1|E) = ^1|Omega_presence"},      # valid
        ]
        results = rust.evaluate_rule_four(examples)
        assert results[0]["applicable"] is False
        assert results[1]["applicable"] is True and not results[1]["is_valid"]
        assert results[2]["applicable"] is True and results[2]["is_valid"]

    def test_v77_rule_four_generator_flow(self, rust: RustValidator):
        """Violations from V77RuleFourGenerator actually fail Rust Rule 4."""
        gen = V77RuleFourGenerator(seed=42)
        examples = [ex.to_dict() for ex in gen.iter_examples(80)]
        results = rust.evaluate_rule_four(examples)
        violations_agree = 0
        violations_total = 0
        for ex, rf in zip(examples, results):
            if not ex["_meta"]["is_valid"]:
                violations_total += 1
                if rf["applicable"] and not rf["is_valid"]:
                    violations_agree += 1
        assert violations_total > 0, "generator produced no violations"
        # Every generator-declared violation must be detected by the Rust engine
        assert violations_agree == violations_total
