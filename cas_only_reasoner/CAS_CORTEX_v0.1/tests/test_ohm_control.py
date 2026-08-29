"""The CAS-Ohm control plane: the three active equations, I_Q
quantization, overload control, branch allocation with fairness and
child probes, learning-repair records, retrieval decisions, the
two-axis matrix, readiness packets - and permanent tests T3-T8."""

from cortex.ohm_control import (DIAGNOSIS_MATRIX,
                                LANGUAGE_PIPELINE_PROFILE,
                                allocate_branches, classify, design_v,
                                diagnose_r, learning_repair_record,
                                measure_i, overload, overload_by_demand,
                                parallel_health, quantize_iq,
                                readiness, retrieval_decision)
from cortex.router import HybridRouter

import pytest

P = LANGUAGE_PIPELINE_PROFILE


# ------------------------------------------- the three active equations
def test_measure_design_diagnose_are_consistent():
    i = measure_i(v_drive=7.5, r_total=2.5)          # MEASURE
    assert i == 3.0
    assert design_v(i_target=3.0, r_total=2.5) == 7.5  # DESIGN
    assert diagnose_r(v_drive=7.5, i_observed=3.0) == 2.5  # DIAGNOSE


def test_iq_quantization_bands_and_trend():
    q = quantize_iq(3.48, P, previous_i=3.0)
    assert q["band"] == "Q3" and q["trend"] == "↑"
    assert q["display"].startswith("I_Q = 5.80")
    assert quantize_iq(1.0, P)["budget_class"] == "minimum_maintenance"
    assert quantize_iq(5.9, P, previous_i=6.0)["trend"] == "↓"


# --------------------------------------------------- T3: overload split
def test_t3_overload_splits_before_clipping():
    load = overload(raw_demand=9.0, profile=P)       # I_FS = 6
    assert load["lambda"] == 1.5
    assert load["decision"] == "OVERLOAD_SPLIT_REQUIRED"
    assert overload(4.0, P)["decision"] == "NORMAL"
    assert overload(5.0, P)["decision"] == "NEAR_CAPACITY_WARNING"


def test_t3_router_splits_multi_part_input_without_calling_cortex():
    class Bomb:
        def propose(self, sentence):
            raise AssertionError("cortex must not run under overload")

    router = HybridRouter(mode="HYBRID_COMMIT", cortex=Bomb())
    trace = router.turn("the cat is gray and the dog is brown.")
    assert trace["route"] == "overload_control"
    assert trace["answer"]["status"] == "NEEDS_DECOMPOSITION"
    assert trace["ohm_load"]["lambda"] > 1.0
    assert trace["committed"] is False


# --------------------------------------------------- T4: starved verifier
def test_t4_starved_verifier_blocks_commitment():
    """Generation flow healthy, verification below its floor: the
    readiness packet fails and the commitment controller stays shut -
    while certifying ENERGIZATION only, never truth."""
    packet = readiness(P, i_pred=6.0, i_obs=0.6, lambda_value=0.5,
                       effect_type="intended")
    assert packet["ok"] is False
    assert packet["conditions"]["region_active"] is False
    assert packet["certifies"] == "energization only - never truth"
    healthy = readiness(P, i_pred=3.0, i_obs=3.2, lambda_value=0.5,
                        effect_type="intended")
    assert healthy["ok"] is True


# ----------------------------------------------- T5: hidden branch failure
def test_t5_child_probes_prevent_false_pass():
    """The parent aggregate looks healthy; one child is saturated and
    one is starved. Health comes from the CHILD probes."""
    branches = {"A": 6.5, "B": 0.2, "C": 2.0}   # sat + starved + active
    health = parallel_health(branches, P)
    assert health["aggregate_looks_healthy"] is True
    assert health["healthy"] is False
    assert health["unhealthy_children"]["A"]["region"] == "saturated"
    assert health["unhealthy_children"]["B"]["region"] == "cutoff"


def test_branch_allocation_has_a_fairness_floor():
    shares = allocate_branches({"A": 3.0, "B": 2.0, "C": 1.0},
                               P)["shares"]
    assert shares["A"] > shares["B"] > shares["C"]
    assert shares["C"] >= P.fairness_floor * 0.9
    assert abs(sum(shares.values()) - 1.0) < 0.01


# --------------------------------------------------- T6: learning repair
def test_t6_learning_is_measured_resistance_reduction():
    record = learning_repair_record(
        p_cap_before=1.0, p_cap_after=8.0, v_drive=6.0, r_other=4.0,
        profile=P, effect_before="off_axis", effect_after="intended")
    assert record["before"]["region"] == "cutoff"
    assert record["after"]["region"] == "active"
    mechanism = record["mechanism"]
    assert mechanism == {"capability_increased": True,
                         "resistance_fell": True,
                         "entered_active": True,
                         "effect_corrected": True}


# --------------------------------------------------- T7: memory ambiguity
def test_t7_similar_memory_flows_ask_for_a_clue_never_merge():
    decision = retrieval_decision({"M17": 2.8, "M204": 2.7},
                                  {"M17": False, "M204": False}, P)
    assert decision["decision"] == "AMBIGUOUS_ASK_FOR_CLUE"
    assert set(decision["competing"]) == {"M17", "M204"}
    assert "never merged" in decision["note"]


def test_t7_retrieval_family():
    dominant = retrieval_decision({"M17": 3.5, "M204": 1.2},
                                  {"M17": False, "M204": False}, P)
    assert dominant["decision"] == "RETRIEVE"
    assert dominant["retrieved"] == "M17"
    starved = retrieval_decision({"M17": 0.2, "M204": 0.3},
                                 {"M17": False, "M204": False}, P)
    assert starved["decision"] == "NEEDS_MORE_CLUE"
    conflicted = retrieval_decision({"M17": 4.0, "M204": 1.0},
                                    {"M17": True, "M204": False}, P)
    assert conflicted["decision"] == "ANCHOR_CONFLICT_REJECT"
    assert "flow never overrides an anchor" in conflicted["note"]


# ------------------------------------------- T8: confident misunderstanding
def test_t8_active_offaxis_repairs_semantics_never_gain():
    result = classify("active", "off_axis")
    assert result["diagnosis"] == "well-powered misunderstanding"
    assert "NEVER gain" in result["repair_class"]


def test_two_axis_matrix_and_independence():
    assert classify("active", "intended")["diagnosis"] == "healthy"
    assert classify("saturated", "off_axis")["diagnosis"] == \
        "confidently wrong and clipped"
    assert classify("breakdown", "opposite")["diagnosis"] == "inversion"
    # both axes are REQUIRED - the matrix cannot derive one from the other
    with pytest.raises(TypeError):
        classify("active")           # missing the semantic axis
    with pytest.raises(ValueError):
        classify("active", "correct-because-flow-was-healthy")


def test_demand_overload_units():
    assert overload_by_demand(2.0, 1.0)["decision"] == \
        "OVERLOAD_SPLIT_REQUIRED"
    assert overload_by_demand(1.0, 1.0)["decision"] == \
        "NEAR_CAPACITY_WARNING"
    assert overload_by_demand(0.5, 1.0)["decision"] == "NORMAL"


def test_profile_is_versioned_and_digested():
    assert P.mode == "native"
    assert len(P.calibration_digest()) == 16
    assert P.calibration_digest() == P.calibration_digest()
