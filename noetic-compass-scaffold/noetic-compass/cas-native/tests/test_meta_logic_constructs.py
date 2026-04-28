"""CAS meta-logic construct integration tests."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from api.notation import compile_expression

from cas_native.data.expression_generator import CASExpressionGenerator
from cas_native.model.meta_logic_constructs import (
    CASConstructKind,
    CONSTRUCT_VOCABULARY,
    EXPRESSION_KIND_LABELS,
    META_LOGIC_EXEMPLARS,
    classify_expression,
    construct_tokens,
)
from cas_native.model.type_constraints import (
    validate_cluster_members,
    validate_meta_logic_expression_kind,
    validate_pullback_as_finite_meet,
)
from cas_native.training.config import TrainingConfig
from cas_native.training.data_pipeline import CASDataset, cas_collate_fn, validate_cas_item
from cas_native.validation import BridgeConfig, RustValidationBridge, StructuralPattern, structural_hash


def test_construct_vocabulary_covers_admitted_examples():
    assert "NoeticCluster" in CONSTRUCT_VOCABULARY
    assert "Pullback" in CONSTRUCT_VOCABULARY
    assert "pullback_finite_meet" in EXPRESSION_KIND_LABELS

    cases = {
        "NoeticSet{^2, ^7}": CASConstructKind.NOETIC_SET,
        "NoeticCluster{^2, ^7}": CASConstructKind.NOETIC_CLUSTER,
        "StateSet{^2^P, ^7^O}": CASConstructKind.STATE_SET,
        "StateCluster{^2^P, ^7^O}": CASConstructKind.STATE_CLUSTER,
        "StateVariantSet{^3^P_{F2}|A, ^2^C|f}": CASConstructKind.STATE_VARIANT_SET,
        "StateVariantCluster{^3^P_{F2}|A, ^2^C|f}": CASConstructKind.STATE_VARIANT_CLUSTER,
        "RelationSet{^5^P -> ^5^C, ^5^C -> ^5^E}": CASConstructKind.RELATION_SET,
        "RelationCluster{^5^P -> ^5^C, ^5^C -> ^5^E}": CASConstructKind.RELATION_CLUSTER,
        "DriveSet{F2, F3}": CASConstructKind.DRIVE_SET,
        "DomainSet{P, C}": CASConstructKind.DOMAIN_SET,
        "RegisterSet{A, f}": CASConstructKind.REGISTER_SET,
        "FoundationSet{Foundation_1, Foundation_7}": CASConstructKind.FOUNDATION_SET,
        "SubFoundationSet{F1|A, F2|f}": CASConstructKind.SUBFOUNDATION_SET,
        "NoeticCluster{^2, ^7} ∩ NoeticCluster{^7}": CASConstructKind.SET_OPERATION,
        "^2 ∈ Noetics": CASConstructKind.TYPED_MEMBERSHIP,
        "NoeticCluster{^2, ^7} ⊆ Noetics": CASConstructKind.TYPED_SUBSET,
        "Coordinate{^2, P, F2, A}": CASConstructKind.COORDINATE,
        "<^2, P, F2, A>": CASConstructKind.COORDINATE,
        "Product(Noetics, Domains)": CASConstructKind.PRODUCT,
        "Pullback(NoeticCluster{^2, ^7}, NoeticCluster{^7, ^8})": CASConstructKind.PULLBACK_FINITE_MEET,
        "CoverOf(SubFoundations, Foundation_1, Foundation_2, Foundation_3, Foundation_4, Foundation_5, Foundation_6, Foundation_7)": CASConstructKind.COVER,
        "PartitionOf(SubFoundations, Foundation_1, Foundation_2, Foundation_3, Foundation_4, Foundation_5, Foundation_6, Foundation_7)": CASConstructKind.PARTITION,
    }
    for expression, expected in cases.items():
        assert classify_expression(expression) is expected
        assert construct_tokens(expression)


def test_meta_logic_generator_exposes_exemplars():
    gen = CASExpressionGenerator(lambda expr: SimpleNamespace(valid=True), seed=3)
    expr = gen.generate_expression("meta_logic")
    assert expr in META_LOGIC_EXEMPLARS


def test_all_meta_logic_exemplars_compile():
    for expression in META_LOGIC_EXEMPLARS:
        artifact = compile_expression(expression)
        assert artifact.valid, expression


def test_dataset_construct_metadata_is_collated():
    dataset = CASDataset(
        [
            {
                "prompt": "p",
                "response": "r",
                "cas_expression": "Pullback(NoeticCluster{^2, ^7}, NoeticCluster{^7, ^8})",
            }
        ],
        max_length=8,
    )
    item = dataset[0]
    assert item["construct_metadata"]["expression_kind"] == "pullback_finite_meet"
    batch = cas_collate_fn([item])
    assert batch["construct_metadata"][0]["construct_tokens"] == ["Pullback"]


def test_validate_cas_item_checks_expression_kind():
    assert validate_cas_item(
        {
            "cas_expression": "Pullback(NoeticCluster{^2, ^7}, NoeticCluster{^7, ^8})",
            "construct_metadata": {"expression_kind": "pullback_finite_meet"},
        }
    )
    assert not validate_cas_item(
        {
            "cas_expression": "Pullback(NoeticCluster{^2, ^7}, NoeticCluster{^7, ^8})",
            "construct_metadata": {"expression_kind": "product"},
        }
    )


def test_type_constraints_keep_pullback_finite_meet_only():
    assert validate_pullback_as_finite_meet("Pullback(NoeticCluster{^2, ^7}, NoeticCluster{^7, ^8})")
    assert validate_meta_logic_expression_kind("Product(Noetics, Domains)", "product")
    assert validate_cluster_members("Noetics", [2, 7])
    assert not validate_cluster_members("Noetics", [2, 11])


def test_structural_hash_includes_construct_metadata():
    a = StructuralPattern(expression_kind="product", construct_tokens=("Product",))
    b = StructuralPattern(expression_kind="pullback_finite_meet", construct_tokens=("Pullback",))
    assert structural_hash(a) != structural_hash(b)


def test_training_config_accepts_meta_logic_mix_zero():
    cfg = TrainingConfig.from_dict(
        {"v2_hyperparameters": {"data_mix_meta_logic": 0.0}}
    )
    assert cfg.v2_hyperparameters.data_mix_meta_logic == pytest.approx(0.0)


def test_compiler_pass_through_can_return_diagram():
    class Artifact:
        valid = True
        errors = []

        def diagram(self):
            return {"kind": "cas_diagram", "nodes": []}

    bridge = RustValidationBridge(
        config=BridgeConfig(
            rust_engine=SimpleNamespace(__version__="test"),
            compile_expression=lambda _expr: Artifact(),
        )
    )
    result = bridge.validate_compiler_expression_batch(
        ["Pullback(NoeticCluster{^2, ^7}, NoeticCluster{^7, ^8})"],
        include_diagram=True,
    )[0]
    assert result.valid is True
    assert result.expression_kind == "pullback_finite_meet"
    assert result.diagram == {"kind": "cas_diagram", "nodes": []}
