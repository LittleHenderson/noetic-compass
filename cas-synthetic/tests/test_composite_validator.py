"""Tests for composite validator."""

from __future__ import annotations

from cas_synthetic.validation import CompositeValidator


class TestCompositeValidator:
    def test_empty_example_is_ok(self):
        v = CompositeValidator()
        assert v.validate({"prompt": "p", "response": "r"}).ok

    def test_register_labels_match_expression(self):
        v = CompositeValidator()
        ex = {
            "prompt": "p", "response": "r",
            "cas_expression": "^3^P|A_{F1} + ^3^P|f_{F1}",
            "register_labels": [
                {"position": 0, "register": "A"},
                {"position": 1, "register": "f"},
            ],
        }
        assert v.validate(ex).ok

    def test_register_label_missing_from_expression_flagged(self):
        v = CompositeValidator()
        ex = {
            "prompt": "p", "response": "r",
            "cas_expression": "^3^P|A_{F1}",
            "register_labels": [{"position": 0, "register": "T"}],  # not in expr
        }
        r = v.validate(ex)
        assert not r.ok
        assert any("T" in i for i in r.issues)

    def test_admitted_omega_name_passes(self):
        v = CompositeValidator()
        ex = {
            "prompt": "p", "response": "r",
            "omega_labels": [{"position": 0, "omega_name": "Omega_presence"}],
        }
        assert v.validate(ex).ok

    def test_unadmitted_omega_name_flagged(self):
        v = CompositeValidator()
        ex = {
            "prompt": "p", "response": "r",
            "omega_labels": [{"position": 0, "omega_name": "Omega_UNKNOWN"}],
        }
        r = v.validate(ex)
        assert not r.ok
        assert any("not admitted" in i for i in r.issues)

    def test_state_id_out_of_range_flagged(self):
        v = CompositeValidator()
        ex = {
            "prompt": "p", "response": "r",
            "production_target": {
                "prereqs": [[99, 1.0]],
                "observed_yield": 1.0,
            },
        }
        r = v.validate(ex)
        assert not r.ok

    def test_violation_metadata_without_distance_flagged(self):
        v = CompositeValidator()
        ex = {
            "prompt": "p", "response": "r",
            "_meta": {"is_valid": False, "distance_to_valid": 0.0, "violation_type": None},
        }
        r = v.validate(ex)
        assert not r.ok
        assert any("is_valid=false" in i for i in r.issues)

    def test_rust_disagreement_flagged(self):
        v = CompositeValidator()
        ex = {
            "prompt": "p", "response": "r",
            "_meta": {"is_valid": True, "distance_to_valid": 0.0, "violation_type": None},
        }
        rf = {"applicable": True, "is_valid": False, "distance": 1.0, "rust_kind": "violation"}
        r = v.validate(ex, rust_rule_four=rf)
        assert not r.ok
        assert any("disagrees" in i for i in r.issues)
