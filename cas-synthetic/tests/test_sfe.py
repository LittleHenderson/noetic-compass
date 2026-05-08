"""Regression tests for the SFE (Structural Fingerprint Extractor).

Built 2026-05-08 after the user caught a false positive on commit
2ad9ab2 (the loose SFE that pre-dated this fix accepted ``^1^P -> ^4^P``
rendered with the second operand as ``operational arena``). This test
file pins that exact regression plus the per-occurrence binding cases
that the clause-level fix has to handle.

Coverage:
- The audit-cited false positive (the load-bearing test).
- Symmetric good case (same source, correct rendering must accept).
- CRO single-noetic-multiple-registers (must accept — clause-level
  domain binding plus set-level register binding).
- Cross-clause domain swaps (must reject).
- Drive→outcome confusion (must reject).
- Recipe coefficient drops (must reject).
- Cluster member counts (must accept matching, reject mismatched).
- Fractal k-sequence (must accept ordered renders).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).resolve().parents[2]
_SFE_PATH = _REPO_ROOT / "cas-synthetic" / "scripts" / "sfe.py"


def _load_sfe():
    name = "sfe_under_test"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _SFE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def sfe():
    return _load_sfe()


# ---------------------------------------------------------------------------
# THE REGRESSION (load-bearing)
# ---------------------------------------------------------------------------


def test_regression_caret1_P_arrow_caret4_P_rejects_when_second_operand_swapped_to_O(sfe):
    """The exact false positive caught by the user.

    Source has both operands in the principled domain. English mistakenly
    renders the second as 'operational arena'. The loose SFE pre-2ad9ab2
    accepted this because noetics-set {1, 4} and domains-set {P, O} both
    looked correct in isolation. Clause-level binding catches it now:
    ``leads to`` splits the English; clause 2 has ^4 paired with O, not P.
    """
    src = "^1^P -> ^4^P"
    bad = (
        "Paying attention to something in the principled arena "
        "leads to it resonating deeply in the operational arena."
    )
    result = sfe.validate_sfe_round_trip(source_cas=src, english=bad)
    assert not result["passed"], (
        "Loose SFE regression: ^1^P -> ^4^P with second operand swapped "
        "to ^O must NOT pass. Got: " + result["reason"]
    )
    # The diff should specifically name the missing (P, 4) binding
    diff = result["detail"]["diff"]
    assert "domains_missing" in diff, f"Expected domains_missing in diff, got {diff}"


def test_caret1_P_arrow_caret4_P_accepts_when_both_operands_principled(sfe):
    """Symmetric good case — same source, correct rendering must accept.
    Confirms the regression fix doesn't over-reject."""
    src = "^1^P -> ^4^P"
    good = (
        "Paying attention to something in the principled arena "
        "leads to it resonating deeply in the principled arena."
    )
    result = sfe.validate_sfe_round_trip(source_cas=src, english=good)
    assert result["passed"], (
        "Correct rendering of ^1^P -> ^4^P (both ^P) must pass. Got: "
        + result["reason"]
    )


# ---------------------------------------------------------------------------
# CRO single-noetic-multiple-registers (relaxed register binding)
# ---------------------------------------------------------------------------


def test_cro_one_noetic_mention_with_multiple_registers_accepts(sfe):
    """The CRO pattern: source has the SAME noetic in N register slots.
    English correctly says noetic+domain ONCE then lists registers. The
    fix uses set-level register binding so this passes."""
    src = "(^4^P|f × ^4^P|T) = ^4^P|Ω_integration"
    eng = (
        "When something resonates and strikes a chord in a foundational "
        "way, expressed both through felt emotion and through transcendent "
        "strategic conviction, those two modes fuse into the outcome "
        "called integration."
    )
    result = sfe.validate_sfe_round_trip(source_cas=src, english=eng)
    assert result["passed"], (
        "CRO with one ^4 mention spanning two registers must pass. Got: "
        + result["reason"]
    )


def test_cro_three_register_fusion_accepts(sfe):
    """Three-register CRO — (^N^D|R1 × ^N^D|R2 × ^N^D|R3) = ^N^D|Ω_X."""
    src = "(^7^E|T × ^7^E|A × ^7^E|f) = ^7^E|Ω_honesty"
    eng = (
        "Practice and muscle memory in evaluative judgment expressed "
        "through transcendent strategic perspective, analytical reasoning, "
        "and felt emotion — those three modes fusing into the outcome "
        "called honesty."
    )
    result = sfe.validate_sfe_round_trip(source_cas=src, english=eng)
    assert result["passed"], (
        "Three-register CRO must pass. Got: " + result["reason"]
    )


# ---------------------------------------------------------------------------
# Drive→outcome confusion (must reject)
# ---------------------------------------------------------------------------


def test_drive_rendered_as_outcome_called_X_rejects(sfe):
    """When source has a drive subscript ``_{Fk}`` but no Ω target, the
    English MUST NOT use 'outcome called <drive_name>' framing. This is
    the structural-shape-without-content failure mode."""
    src = "^2^O_{F2} + ^3^O_{F6}"
    eng = (
        "A positive pull toward the outcome called wisdom, combined "
        "with a negative push away from the outcome called structure."
    )
    result = sfe.validate_sfe_round_trip(source_cas=src, english=eng)
    assert not result["passed"], (
        "Drive→outcome confusion (F2/F6 rendered as 'outcome called X') "
        "must reject. Got: " + result["reason"]
    )


# ---------------------------------------------------------------------------
# Recipe coefficient + Ω stem preservation
# ---------------------------------------------------------------------------


def test_recipe_with_all_elements_preserved_accepts(sfe):
    src = "Theta(Omega_judgment_07) = 0.7*^7^O + 1.5*^4^P -> Omega_judgment_07"
    eng = (
        "To produce the outcome called judgment_07, take 0.7 of "
        "muscle memory in operational behavior and add 1.5 of "
        "something that struck a chord in the principled arena — "
        "together these inputs yield judgment_07."
    )
    result = sfe.validate_sfe_round_trip(source_cas=src, english=eng)
    assert result["passed"], (
        "Recipe with all elements preserved must pass. Got: "
        + result["reason"]
    )


def test_recipe_with_dropped_coefficient_rejects(sfe):
    src = "Theta(Omega_judgment_07) = 0.7*^7^O + 1.5*^4^P -> Omega_judgment_07"
    eng = (
        "To produce the outcome called judgment_07, take some "
        "muscle memory in operational behavior and add 1.5 of "
        "something that struck a chord in the principled arena."
    )
    result = sfe.validate_sfe_round_trip(source_cas=src, english=eng)
    assert not result["passed"], (
        "Recipe with dropped 0.7 coefficient must reject. Got: "
        + result["reason"]
    )
    diff = result["detail"]["diff"]
    assert "coefficients_missing" in diff


def test_recipe_with_swapped_noetic_3_to_5_rejects(sfe):
    """The audit-cited recipe ^3 → ^5 swap pattern."""
    src = "Theta(Omega_x) = 0.5*^3^E -> Omega_x"
    # Model rendered ^3 as "who-you-are" (which is ^5 alias)
    eng = "To produce the outcome called x, take 0.5 of who you are in evaluative judgment."
    result = sfe.validate_sfe_round_trip(source_cas=src, english=eng)
    assert not result["passed"], (
        "Recipe with ^3 rendered as ^5 alias must reject. Got: "
        + result["reason"]
    )


# ---------------------------------------------------------------------------
# Cluster member preservation
# ---------------------------------------------------------------------------


def test_noetic_cluster_with_all_members_accepts(sfe):
    src = "NoeticCluster{^1, ^3, ^4}"
    eng = "A cluster of three operations: paying attention, an aversion, and something that struck a chord."
    result = sfe.validate_sfe_round_trip(source_cas=src, english=eng)
    assert result["passed"], (
        "NoeticCluster with all 3 members rendered must pass. Got: "
        + result["reason"]
    )


def test_intersection_of_clusters_accepts(sfe):
    """Set-operation between clusters — meta-logic operator ∩."""
    src = "NoeticCluster{^0, ^5, ^9} ∩ NoeticCluster{^0, ^4}"
    eng = (
        "An intersection of groups: group 1 contains a thought, "
        "identity shaped by experience, and something that just clicked; "
        "group 2 contains a thought and something that struck a chord."
    )
    result = sfe.validate_sfe_round_trip(source_cas=src, english=eng)
    assert result["passed"], (
        "NoeticCluster intersection rendered as 'intersection of groups' "
        "must pass. Got: " + result["reason"]
    )


# ---------------------------------------------------------------------------
# Variable name preservation
# ---------------------------------------------------------------------------


def test_let_binding_variable_name_verbatim_accepts(sfe):
    src = "let stageA0_5 = ^0^P; let stageW_5 = ^7^C; stageA0_5 -> stageW_5"
    eng = (
        "Stage definitions: stageA0_5 names a thought in a foundational "
        "frame; stageW_5 names muscle memory in cognitive thinking. "
        "The chain says stageA0_5 leads to stageW_5."
    )
    result = sfe.validate_sfe_round_trip(source_cas=src, english=eng)
    assert result["passed"], (
        "Let binding with both variable names verbatim must pass. Got: "
        + result["reason"]
    )


def test_let_binding_variable_name_dropped_rejects(sfe):
    src = "let stageA0_5 = ^0^P; let stageW_5 = ^7^C; stageA0_5 -> stageW_5"
    eng = (
        "A foundational thought leads to muscle memory in cognitive thinking."
    )
    result = sfe.validate_sfe_round_trip(source_cas=src, english=eng)
    assert not result["passed"], (
        "Let binding with both variable names dropped must reject. Got: "
        + result["reason"]
    )


# ---------------------------------------------------------------------------
# Fractal k-sequence
# ---------------------------------------------------------------------------


def test_fractal_sequence_with_all_k_values_rendered_accepts(sfe):
    src = "Phi<2:6:8>"
    eng = (
        "A fractal sequence where being drawn to something, then "
        "breaking it down, then something that triggered a memory."
    )
    result = sfe.validate_sfe_round_trip(source_cas=src, english=eng)
    assert result["passed"], (
        "Fractal Phi<2:6:8> rendered with ^2/^6/^8 aliases must pass. "
        + "Got: " + result["reason"]
    )


# ---------------------------------------------------------------------------
# CO-N composition
# ---------------------------------------------------------------------------


def test_co_n_composition_misrender_rejects(sfe):
    """CO-9 ∘ CO-7 with both operators rendered as ^4 aliases must
    reject (Agent 3's audit case)."""
    src = "CO-9 ∘ CO-7"
    eng = (
        "A composition where something that struck a chord in the "
        "operational arena is then integrated with something that hit "
        "hard in the evaluative arena."
    )
    result = sfe.validate_sfe_round_trip(source_cas=src, english=eng)
    assert not result["passed"], (
        "CO-N composition with both operators mis-rendered as ^4 aliases "
        "must reject. Got: " + result["reason"]
    )


# ---------------------------------------------------------------------------
# Subset (meta-logic ⊂) — proper-vs-non-proper distinction collapses
# ---------------------------------------------------------------------------


def test_subset_relation_accepts_either_proper_form(sfe):
    src = "NoeticCluster{^1, ^6, ^8} ⊂ Noetics"
    eng = (
        "A subset relation where the group containing paying attention, "
        "breaking down an idea, and something that triggered a memory "
        "sits inside the complete basic-pattern set."
    )
    result = sfe.validate_sfe_round_trip(source_cas=src, english=eng)
    assert result["passed"], (
        "Subset relation rendered as 'subset relation ... sits inside' "
        "must pass (English doesn't distinguish proper-vs-non-proper). "
        "Got: " + result["reason"]
    )
