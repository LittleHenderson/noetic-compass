"""Tests for schema_validator against data_format.md."""

from __future__ import annotations

import pytest

from cas_synthetic.validation import (
    SchemaValidator,
    SchemaValidationError,
    validate_example_schema,
)


class TestSchemaValidator:
    def test_minimal_valid_example(self):
        ex = {"prompt": "p", "response": "r"}
        assert SchemaValidator(strict=False).validate(ex) == []

    def test_missing_prompt_fails(self):
        v = SchemaValidator(strict=False)
        errs = v.validate({"response": "r"})
        assert any("prompt" in e for e in errs)

    def test_missing_response_fails(self):
        errs = SchemaValidator(strict=False).validate({"prompt": "p"})
        assert any("response" in e for e in errs)

    def test_strict_raises_on_missing(self):
        with pytest.raises(SchemaValidationError):
            SchemaValidator(strict=True).validate({"prompt": "p"})

    def test_valid_register_label(self):
        ex = {
            "prompt": "p", "response": "r",
            "register_labels": [{"position": 0, "register": "A"}],
        }
        assert validate_example_schema(ex) == []

    def test_invalid_register_uppercase_F_fails(self):
        ex = {
            "prompt": "p", "response": "r",
            "register_labels": [{"position": 0, "register": "F"}],  # should be lowercase f
        }
        errs = validate_example_schema(ex)
        assert any("register" in e.lower() for e in errs)

    def test_lowercase_f_allowed(self):
        ex = {
            "prompt": "p", "response": "r",
            "register_labels": [{"position": 0, "register": "f"}],
        }
        assert validate_example_schema(ex) == []

    def test_omega_label_requires_name(self):
        ex = {
            "prompt": "p", "response": "r",
            "omega_labels": [{"position": 0, "omega_name": ""}],
        }
        errs = validate_example_schema(ex)
        assert errs

    def test_production_target_prereq_state_id_out_of_range(self):
        ex = {
            "prompt": "p", "response": "r",
            "production_target": {
                "prereqs": [[41, 1.0]],
                "observed_yield": 1.0,
            },
        }
        errs = validate_example_schema(ex)
        assert any("state_id" in e for e in errs)

    def test_production_target_negative_coefficient_fails(self):
        ex = {
            "prompt": "p", "response": "r",
            "production_target": {
                "prereqs": [[3, -1.0]],
                "observed_yield": 1.0,
            },
        }
        errs = validate_example_schema(ex)
        assert any("coefficient" in e for e in errs)

    def test_production_target_negative_yield_fails(self):
        ex = {
            "prompt": "p", "response": "r",
            "production_target": {
                "prereqs": [[3, 1.0]],
                "observed_yield": -0.1,
            },
        }
        errs = validate_example_schema(ex)
        assert any("observed_yield" in e for e in errs)

    def test_operator_scores_length(self):
        ex = {
            "prompt": "p", "response": "r",
            "scores": {"operator_scores": [0.0] * 9},  # should be 10
        }
        errs = validate_example_schema(ex)
        assert any("operator_scores" in e for e in errs)

    def test_domain_scores_length(self):
        ex = {
            "prompt": "p", "response": "r",
            "scores": {"domain_scores": [0.0] * 3},  # should be 4
        }
        errs = validate_example_schema(ex)
        assert any("domain_scores" in e for e in errs)
