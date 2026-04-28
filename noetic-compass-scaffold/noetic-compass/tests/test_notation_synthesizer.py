"""Tests for the real-time CAS notation synthesizer."""

import pytest

from api.notation.compiler import compile_expression
from api.pipeline.notation_synthesizer import (
    SynthesizedNotation,
    synthesize_notation,
    _pick_significant_operators,
    _pick_significant_domains,
    _pick_significant_drives,
    _pick_flagged_inversions,
    _build_expression,
    _detect_set_operation_vocabulary,
    _detect_membership_vocabulary,
    _detect_subset_vocabulary,
    _resolve_meta_set_operand,
    _construct_meta_logic_assertion,
    _try_meta_logic_emission,
)


# ---------------------------------------------------------------------------
# Helpers — default pipeline output for a "typical" assessment
# ---------------------------------------------------------------------------

def _default_kwargs(**overrides):
    base = dict(
        operator_scores=[0.6, 0.7, 0.5, 0.8, 0.4, 0.9, 0.3, 0.7, 0.6, 0.5],
        raw_scores_0_to_10=[6.0, 7.0, 5.0, 8.0, 4.0, 9.0, 3.0, 7.0, 6.0, 5.0],
        domain_averages=[0.7, 0.6, 0.5, 0.4],
        drive_chains=[
            [0.8, 0.7, 0.6],  # F1 — full chain passes
            [0.9, 0.8, 0.7],  # F2 — full chain passes
            [0.3, 0.2, 0.1],  # F3 — fails
            [0.6, 0.5, 0.4],  # F4 — partial
            [0.7, 0.6, 0.5],  # F5 — full chain passes
            [0.4, 0.3, 0.2],  # F6 — fails
            [0.8, 0.7, 0.6],  # F7 — full chain passes
        ],
        a0_score=0.75,
        rpm_completeness=0.65,
        inversion_axis_scores=[0.8, 0.3, 0.9, 0.7, 0.4, 0.6, 0.5],
        fractal_sequence=[5, 3, 1, 7, 0],
        fractal_classification="stabilizing",
    )
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Component extraction tests
# ---------------------------------------------------------------------------

class TestPickSignificantOperators:
    def test_selects_above_threshold(self):
        raw = [6.0, 7.0, 4.0, 8.0, 3.0, 9.0, 2.0, 7.0, 5.0, 5.0]
        result = _pick_significant_operators(raw)
        # CO-5 (9.0), CO-3 (8.0), CO-1 (7.0), CO-7 (7.0) — top 4
        assert result == [5, 3, 1, 7]

    def test_caps_at_max(self):
        raw = [10.0] * 10
        result = _pick_significant_operators(raw)
        assert len(result) <= 4

    def test_empty_when_all_below(self):
        raw = [2.0, 3.0, 4.0, 1.0, 0.0, 4.9, 3.5, 2.1, 1.0, 0.5]
        result = _pick_significant_operators(raw)
        assert result == []


class TestPickSignificantDomains:
    def test_selects_above_threshold(self):
        result = _pick_significant_domains([0.7, 0.6, 0.5, 0.4])
        assert result == ["P", "C", "E"]

    def test_all_strong(self):
        result = _pick_significant_domains([0.8, 0.7, 0.6, 0.5])
        assert result == ["P", "C", "E", "O"]

    def test_none_significant(self):
        result = _pick_significant_domains([0.1, 0.2, 0.3, 0.4])
        assert result == []


class TestPickSignificantDrives:
    def test_separates_rpm_and_plain(self):
        drive_chains = [
            [0.8, 0.7, 0.6],  # F1 — all pass → RPM
            [0.3, 0.2, 0.1],  # F2 — all fail → neither
            [0.7, 0.6, 0.4],  # F3 — D+W pass, P fails → plain
            [0.8, 0.7, 0.6],  # F4 — all pass → RPM
            [0.1, 0.1, 0.1],  # F5 — all fail
            [0.1, 0.1, 0.1],  # F6 — all fail
            [0.1, 0.1, 0.1],  # F7 — all fail
        ]
        rpm, plain = _pick_significant_drives(drive_chains, a0_score=0.7)
        assert 0 in rpm  # F1
        assert 3 in rpm  # F4
        assert 2 in plain  # F3 — active but incomplete chain


class TestPickFlaggedInversions:
    def test_flags_low_resistance(self):
        scores = [0.8, 0.3, 0.9, 0.7, 0.4, 0.6, 0.5]
        result = _pick_flagged_inversions(scores)
        assert "W" in result  # 0.3
        assert "S" in result  # 0.4


# ---------------------------------------------------------------------------
# Expression building tests
# ---------------------------------------------------------------------------

class TestBuildExpression:
    def test_operators_with_domains(self):
        expr = _build_expression(
            operators=[3, 5],
            domains=["P", "C"],
            rpm_drives=[],
            plain_drives=[],
            fractal_sequence=None,
            fractal_classification=None,
        )
        assert "CO-3^P" in expr
        assert "CO-5^P" in expr  # both ops appear in primary domain
        # Domain descent appears as separate statement
        assert "->" in expr

    def test_rpm_drives(self):
        expr = _build_expression(
            operators=[5],
            domains=["C"],
            rpm_drives=[4],
            plain_drives=[],
            fractal_sequence=None,
            fractal_classification=None,
        )
        assert "RPM(F5)" in expr
        assert "CO-5^C" in expr

    def test_plain_drives(self):
        expr = _build_expression(
            operators=[],
            domains=[],
            rpm_drives=[],
            plain_drives=[2],
            fractal_sequence=None,
            fractal_classification=None,
        )
        assert expr == "F3"

    def test_fractal_included_when_non_neutral(self):
        expr = _build_expression(
            operators=[5],
            domains=["C"],
            rpm_drives=[],
            plain_drives=[],
            fractal_sequence=[5, 3, 1],
            fractal_classification="stabilizing",
        )
        assert "Phi<" in expr

    def test_fractal_excluded_when_neutral(self):
        expr = _build_expression(
            operators=[5],
            domains=["C"],
            rpm_drives=[],
            plain_drives=[],
            fractal_sequence=[5, 3, 1],
            fractal_classification="neutral",
        )
        assert "Phi" not in expr

    def test_empty_when_nothing_significant(self):
        expr = _build_expression([], [], [], [], None, None)
        assert expr == ""


# ---------------------------------------------------------------------------
# Full synthesis integration tests
# ---------------------------------------------------------------------------

class TestSynthesizeNotation:
    def test_produces_valid_compiled_notation(self):
        result = synthesize_notation(**_default_kwargs())
        assert isinstance(result, SynthesizedNotation)
        assert result.valid is True
        assert result.source  # non-empty
        assert result.english  # non-empty
        assert result.provenance["compiler_valid"] is True

    def test_includes_dominant_operators(self):
        result = synthesize_notation(**_default_kwargs())
        # CO-5 scored 9.0, CO-3 scored 8.0 — both should appear
        assert "CO-5" in result.source
        assert "CO-3" in result.source

    def test_includes_rpm_for_complete_chains(self):
        result = synthesize_notation(**_default_kwargs())
        # F1 and F2 have complete chains — at least one should have RPM
        assert "RPM(" in result.source

    def test_includes_fractal_for_non_neutral(self):
        result = synthesize_notation(**_default_kwargs(
            fractal_sequence=[5, 3, 1, 7],
            fractal_classification="stabilizing",
        ))
        assert "Phi<" in result.source

    def test_auto_generates_fractal_from_operator_order(self):
        """Even with neutral classification, 3+ operators auto-generate Phi<>."""
        result = synthesize_notation(**_default_kwargs(
            fractal_classification="neutral",
        ))
        # 4 operators above threshold → auto-generated fractal sequence
        assert "Phi<" in result.source

    def test_handles_all_below_threshold(self):
        result = synthesize_notation(**_default_kwargs(
            raw_scores_0_to_10=[2.0, 3.0, 1.0, 4.0, 0.5, 4.9, 1.0, 2.0, 3.0, 1.5],
            domain_averages=[0.1, 0.2, 0.3, 0.1],
            drive_chains=[[0.1, 0.1, 0.1]] * 7,
            a0_score=0.2,
            fractal_classification="neutral",
        ))
        assert result.valid is False
        assert "below significance" in result.provenance.get("reason", "")

    def test_provenance_tracks_components(self):
        result = synthesize_notation(**_default_kwargs())
        prov = result.provenance
        assert "operators_found" in prov
        assert "domains_found" in prov
        assert "rpm_drives" in prov
        assert "compiler_engine" in prov

    def test_deterministic(self):
        """Same inputs produce the same notation every time."""
        kwargs = _default_kwargs()
        r1 = synthesize_notation(**kwargs)
        r2 = synthesize_notation(**kwargs)
        assert r1.source == r2.source
        assert r1.valid == r2.valid

    def test_v75_registers_from_natural_language_compile(self):
        result = synthesize_notation(**_default_kwargs(
            source_text=(
                "Use analytical logic and evidence while honoring affective "
                "feeling and embodied gut response."
            ),
            fractal_classification="neutral",
        ))
        assert result.valid is True
        assert "|A" in result.source
        assert "|f" in result.source
        assert "|E" in result.source
        assert compile_expression(result.source).valid is True

    def test_v76_recipe_with_conditions_from_strong_production_language_compiles(self):
        result = synthesize_notation(**_default_kwargs(
            source_text=(
                "Create an insight recipe from analytical evidence and affective "
                "feeling; deadline support is a catalyst, fatigue is an inhibitor."
            ),
            fractal_classification="neutral",
        ))
        assert result.valid is True
        assert "Theta(Omega_insight)" in result.source
        assert "-> Omega_insight" in result.source
        assert "kappa_deadline" in result.source
        assert "iota_fatigue" in result.source
        assert compile_expression(result.source).valid is True

    def test_v77_register_set_and_copresence_when_modes_cooccur(self):
        result = synthesize_notation(**_default_kwargs(
            source_text=(
                "Synthesize analytical reasoning, affective feeling, and "
                "transcendent purpose into one integrated judgment."
            ),
            fractal_classification="neutral",
        ))
        assert result.valid is True
        assert "|<A,f,T>" in result.source
        assert "|A + " in result.source
        assert "|f + " in result.source
        assert "|T" in result.source
        assert compile_expression(result.source).valid is True


# ---------------------------------------------------------------------------
# Meta-logic trigger vocabulary tests (Track B SDG sprint)
# ---------------------------------------------------------------------------

class TestSetOperationDetection:
    """Trigger-phrase detection for ∪ / ∩ / ∖."""

    @pytest.mark.parametrize("text", [
        "the union of Noetics and Domains",
        "union of ^2 and ^7",
        "combined set of ^2 and ^7",
    ])
    def test_union_phrases_detected(self, text):
        assert _detect_set_operation_vocabulary(text) == "Union"

    @pytest.mark.parametrize("text", [
        "intersection of ^2 and ^7",
        "common to both ^2 and ^7",
        "overlap of ^2 and ^7",
        "what ^2 and ^7 share",
    ])
    def test_intersection_phrases_detected(self, text):
        assert _detect_set_operation_vocabulary(text) == "Intersection"

    @pytest.mark.parametrize("text", [
        "everything in Noetics except ^4",
        "all things in Noetics except ^4",
        "Noetics minus ^4",
        "Noetics excluding ^4",
        "all of Noetics except ^4",
    ])
    def test_difference_phrases_detected(self, text):
        assert _detect_set_operation_vocabulary(text) == "Difference"

    @pytest.mark.parametrize("text", [
        "the labor union met yesterday",
        "credit union announced rates",
        "union jack flag",
        "trade union representative",
    ])
    def test_union_negative_contexts_no_fire(self, text):
        # Trigger detector may fire on the keyword, but emission must not
        assert _try_meta_logic_emission(text) is None

    @pytest.mark.parametrize("text", [
        "street intersection was crowded",
        "busy traffic intersection",
        "lives lived at the intersection of identity",
        "the intersection of his career",
    ])
    def test_intersection_negative_contexts_no_fire(self, text):
        assert _detect_set_operation_vocabulary(text) is None

    @pytest.mark.parametrize("text", [
        "the difference between us",
        "made a difference",
        "world of difference",
    ])
    def test_difference_negative_contexts_no_fire(self, text):
        assert _detect_set_operation_vocabulary(text) is None


class TestMembershipDetection:
    """Trigger-phrase detection for ∈ / ∉ — paired with meta-set."""

    @pytest.mark.parametrize("text", [
        "^2 is a member of Noetics",
        "CO-3 belongs to Noetics",
        "P is in Domains",
        "F2 is in Drives",
    ])
    def test_member_phrases_detected(self, text):
        assert _detect_membership_vocabulary(text) == "Member"

    @pytest.mark.parametrize("text", [
        "^2 is not a member of Noetics",
        "CO-3 doesn't belong to Noetics",
        "^4 isn't in Drives",
    ])
    def test_not_member_phrases_detected(self, text):
        assert _detect_membership_vocabulary(text) == "NotMember"

    @pytest.mark.parametrize("text", [
        "is in trouble",
        "is in love",
        "is in danger",
        "is in stock",
        "is in luck",
    ])
    def test_is_in_negative_contexts_no_fire(self, text):
        # No meta-set in trigger position → must not fire.
        assert _detect_membership_vocabulary(text) is None

    def test_belongs_to_without_meta_set_no_fire(self):
        # "belongs to" without meta-set name → must not fire.
        assert _detect_membership_vocabulary("she belongs to the team") is None


class TestSubsetDetection:
    """Trigger-phrase detection for ⊂ / ⊆ / ⊃ / ⊇."""

    @pytest.mark.parametrize("text", [
        "NoeticCluster{^2, ^7} is a subset of Noetics",
        "is contained in Noetics",
        "^2 is part of Noetics",
    ])
    def test_subset_phrases_detected(self, text):
        assert _detect_subset_vocabulary(text) == "Subset"

    @pytest.mark.parametrize("text", [
        "^4 is at most Noetics",
        "NoeticCluster{^2} is a subset of or equals Noetics",
    ])
    def test_subseteq_phrases_detected(self, text):
        assert _detect_subset_vocabulary(text) == "SubsetEq"

    @pytest.mark.parametrize("text", [
        "Noetics contains ^2 and ^7",
        "Noetics includes ^4",
    ])
    def test_superset_phrases_detected(self, text):
        assert _detect_subset_vocabulary(text) == "Superset"

    @pytest.mark.parametrize("text", [
        "Noetics contains or equals NoeticCluster{^2}",
    ])
    def test_superseteq_phrases_detected(self, text):
        assert _detect_subset_vocabulary(text) == "SupersetEq"

    @pytest.mark.parametrize("text", [
        "this contains nuts",
        "package contains gluten",
        "bottle contains alcohol",
    ])
    def test_contains_negative_contexts_no_fire(self, text):
        # Detector may fire (no meta-set), but emission must not
        assert _try_meta_logic_emission(text) is None


class TestMetaSetOperandResolution:
    """`_resolve_meta_set_operand` returns canonical names or None."""

    def test_canonical_meta_set_names(self):
        assert _resolve_meta_set_operand("Noetics") == "Noetics"
        assert _resolve_meta_set_operand("Domains") == "Domains"
        assert _resolve_meta_set_operand("States") == "States"
        assert _resolve_meta_set_operand("Drives") == "Drives"
        assert _resolve_meta_set_operand("Foundations") == "Foundations"

    def test_canonical_handles_articles_and_punctuation(self):
        assert _resolve_meta_set_operand("the Noetics") == "Noetics"
        assert _resolve_meta_set_operand("Noetics.") == "Noetics"

    def test_singular_noetic_ref(self):
        assert _resolve_meta_set_operand("^2") == "^2"
        assert _resolve_meta_set_operand("CO-3") == "^3"

    def test_singular_state_ref(self):
        assert _resolve_meta_set_operand("^2^P") == "^2^P"

    def test_singular_domain_code(self):
        assert _resolve_meta_set_operand("P") == "P"
        assert _resolve_meta_set_operand("E") == "E"

    def test_singular_drive_ref(self):
        assert _resolve_meta_set_operand("F2") == "F2"

    def test_foundation_ref(self):
        assert _resolve_meta_set_operand("Foundation_1") == "Foundation_1"

    def test_multiple_noetics_become_cluster(self):
        # The order is preserved
        assert _resolve_meta_set_operand("^2 and ^7") == "NoeticCluster{^2, ^7}"

    def test_unresolvable_returns_none(self):
        assert _resolve_meta_set_operand("a vague noun") is None
        assert _resolve_meta_set_operand("") is None
        assert _resolve_meta_set_operand("distractions") is None


class TestConstructMetaLogicAssertion:
    """Pure-function shape of `_construct_meta_logic_assertion`."""

    def test_set_op_assertions(self):
        assert _construct_meta_logic_assertion(
            "Union", ["NoeticCluster{^2}", "NoeticCluster{^7}"]
        ) == "NoeticCluster{^2} ∪ NoeticCluster{^7}"
        assert _construct_meta_logic_assertion(
            "Intersection", ["NoeticCluster{^2}", "NoeticCluster{^7}"]
        ) == "NoeticCluster{^2} ∩ NoeticCluster{^7}"
        assert _construct_meta_logic_assertion(
            "Difference", ["Noetics", "NoeticCluster{^4}"]
        ) == "Noetics ∖ NoeticCluster{^4}"

    def test_membership_assertions(self):
        assert _construct_meta_logic_assertion("Member", ["^2", "Noetics"]) == "^2 ∈ Noetics"
        assert _construct_meta_logic_assertion("NotMember", ["^2", "Noetics"]) == "^2 ∉ Noetics"

    def test_subset_assertions(self):
        assert _construct_meta_logic_assertion(
            "Subset", ["NoeticCluster{^2}", "Noetics"]
        ) == "NoeticCluster{^2} ⊂ Noetics"
        assert _construct_meta_logic_assertion(
            "SubsetEq", ["NoeticCluster{^2}", "Noetics"]
        ) == "NoeticCluster{^2} ⊆ Noetics"
        assert _construct_meta_logic_assertion(
            "Superset", ["Noetics", "NoeticCluster{^2}"]
        ) == "Noetics ⊃ NoeticCluster{^2}"
        assert _construct_meta_logic_assertion(
            "SupersetEq", ["Noetics", "NoeticCluster{^2}"]
        ) == "Noetics ⊇ NoeticCluster{^2}"

    def test_unknown_operation_returns_empty(self):
        assert _construct_meta_logic_assertion("Bogus", ["a", "b"]) == ""


class TestMetaLogicEmissionHits:
    """Happy-path: prose triggers meta-logic AND operand resolves AND
    the emitted assertion compiles."""

    @pytest.mark.parametrize("text,expected", [
        ("union of ^2 and ^7", "NoeticCluster{^2} ∪ NoeticCluster{^7}"),
        ("combined set of ^2 and ^7", "NoeticCluster{^2} ∪ NoeticCluster{^7}"),
        ("intersection of ^2 and ^7", "NoeticCluster{^2} ∩ NoeticCluster{^7}"),
        ("common to both ^2 and ^7", "NoeticCluster{^2} ∩ NoeticCluster{^7}"),
        ("overlap of ^2 and ^7", "NoeticCluster{^2} ∩ NoeticCluster{^7}"),
        ("what ^2 and ^7 share", "NoeticCluster{^2} ∩ NoeticCluster{^7}"),
        ("everything in Noetics except ^4", "Noetics ∖ NoeticCluster{^4}"),
        ("all things in Noetics except ^4", "Noetics ∖ NoeticCluster{^4}"),
        ("Noetics minus ^4", "Noetics ∖ NoeticCluster{^4}"),
        ("^2 is a member of Noetics", "^2 ∈ Noetics"),
        ("CO-3 belongs to Noetics", "^3 ∈ Noetics"),
        ("P is in Domains", "P ∈ Domains"),
        ("F2 is in Drives", "F2 ∈ Drives"),
        ("Foundation_1 is in Foundations", "Foundation_1 ∈ Foundations"),
        ("^2 is not a member of Noetics", "^2 ∉ Noetics"),
        ("CO-3 doesn't belong to Noetics", "^3 ∉ Noetics"),
        ("NoeticCluster{^2, ^7} is contained in Noetics",
         "NoeticCluster{^2, ^7} ⊂ Noetics"),
        ("NoeticCluster{^2, ^7} is a subset of Noetics",
         "NoeticCluster{^2, ^7} ⊂ Noetics"),
        ("^4 is at most Noetics", "NoeticCluster{^4} ⊆ Noetics"),
        ("Noetics contains ^2 and ^7", "Noetics ⊃ NoeticCluster{^2, ^7}"),
        ("Noetics includes ^4", "Noetics ⊃ NoeticCluster{^4}"),
        ("Noetics contains or equals NoeticCluster{^2}",
         "Noetics ⊇ NoeticCluster{^2}"),
    ])
    def test_emission_matches(self, text, expected):
        emitted = _try_meta_logic_emission(text)
        assert emitted == expected, f"input={text!r} emit={emitted!r}"
        # Each emitted form must compile through the real compiler
        assert compile_expression(emitted).valid


class TestMetaLogicEmissionMisses:
    """No-fire: vague prose, everyday senses, or unresolvable operands."""

    @pytest.mark.parametrize("text", [
        # Negative-fire contexts from spec
        "the labor union met yesterday",
        "credit union announced rates",
        "trade union representative",
        "street intersection was crowded",
        "busy traffic intersection",
        "lives lived at the intersection of identity",
        "the intersection of his career",
        "the difference between us is real",
        "world of difference",
        "this contains nuts",
        "package contains gluten",
        "bottle contains alcohol",
        "is in trouble",
        "is in love",
        "is in danger",
        "is in stock",
        # Unrelated content
        "I think about creativity and rhythm",
        "the team works on a new feature",
        "set the table for dinner",
    ])
    def test_no_emission(self, text):
        assert _try_meta_logic_emission(text) is None

    @pytest.mark.parametrize("text", [
        # Trigger present but operand unresolvable
        "the union of distractions and obligations",
        "common to both apples and oranges",
        "what cats and dogs share",
        "all things in patience except joy",
    ])
    def test_trigger_with_unresolvable_operand_no_emission(self, text):
        assert _try_meta_logic_emission(text) is None

    def test_incompatible_carriers_no_emission(self):
        # Union of bare meta-sets of different carrier kinds → must not emit
        # (compile would fail with "incompatible typed meta-sets").
        assert _try_meta_logic_emission("the union of Noetics and Domains") is None

    def test_empty_or_none_source(self):
        assert _try_meta_logic_emission(None) is None
        assert _try_meta_logic_emission("") is None


class TestSynthesizeNotationMetaLogicIntegration:
    """End-to-end: synthesize_notation short-circuits to meta-logic when
    prose triggers it; otherwise falls through to v7.4-v7.7 paths."""

    def test_meta_logic_short_circuits_synthesizer(self):
        result = synthesize_notation(**_default_kwargs(
            source_text="^2 is a member of Noetics",
            fractal_classification="neutral",
        ))
        assert result.valid is True
        assert result.source == "^2 ∈ Noetics"
        assert result.provenance.get("meta_logic_emission") is True
        assert compile_expression(result.source).valid

    def test_meta_logic_difference_short_circuits(self):
        result = synthesize_notation(**_default_kwargs(
            source_text="everything in Noetics except ^4",
            fractal_classification="neutral",
        ))
        assert result.valid is True
        assert result.source == "Noetics ∖ NoeticCluster{^4}"
        assert result.provenance.get("meta_logic_emission") is True

    def test_meta_logic_union_short_circuits(self):
        result = synthesize_notation(**_default_kwargs(
            source_text="union of ^2 and ^7",
            fractal_classification="neutral",
        ))
        assert result.valid is True
        assert "∪" in result.source
        assert result.provenance.get("meta_logic_emission") is True

    def test_no_meta_logic_falls_through_to_baseline(self):
        # No meta-logic vocabulary → existing baseline emission still fires
        result = synthesize_notation(**_default_kwargs(
            source_text="creativity and rhythm working together",
            fractal_classification="neutral",
        ))
        assert result.valid is True
        # No meta-logic emission flag
        assert not result.provenance.get("meta_logic_emission")
        # Baseline form is preserved (operator/domain expression structure)
        assert "CO-" in result.source

    def test_v75_register_path_unaffected_by_meta_logic_addition(self):
        # Same prompt as the existing v7.5 test — must continue producing
        # register-tagged output (NOT meta-logic).
        result = synthesize_notation(**_default_kwargs(
            source_text=(
                "Use analytical logic and evidence while honoring affective "
                "feeling and embodied gut response."
            ),
            fractal_classification="neutral",
        ))
        assert result.valid is True
        assert "|A" in result.source
        assert "|f" in result.source
        assert "|E" in result.source
        assert not result.provenance.get("meta_logic_emission")
        assert compile_expression(result.source).valid

    def test_v76_recipe_path_unaffected_by_meta_logic_addition(self):
        result = synthesize_notation(**_default_kwargs(
            source_text=(
                "Create an insight recipe from analytical evidence and affective "
                "feeling; deadline support is a catalyst, fatigue is an inhibitor."
            ),
            fractal_classification="neutral",
        ))
        assert result.valid is True
        assert "Theta(Omega_insight)" in result.source
        assert not result.provenance.get("meta_logic_emission")
        assert compile_expression(result.source).valid

    def test_v77_register_set_path_unaffected_by_meta_logic_addition(self):
        result = synthesize_notation(**_default_kwargs(
            source_text=(
                "Synthesize analytical reasoning, affective feeling, and "
                "transcendent purpose into one integrated judgment."
            ),
            fractal_classification="neutral",
        ))
        assert result.valid is True
        assert "|<A,f,T>" in result.source
        assert not result.provenance.get("meta_logic_emission")
        assert compile_expression(result.source).valid

    def test_negative_fire_falls_through_cleanly(self):
        # "labor union" must NOT short-circuit to meta-logic emission;
        # baseline path runs as if source_text contained no meta-logic.
        result = synthesize_notation(**_default_kwargs(
            source_text="the labor union members met to discuss benefits",
            fractal_classification="neutral",
        ))
        assert result.valid is True
        assert "∪" not in result.source
        assert not result.provenance.get("meta_logic_emission")
