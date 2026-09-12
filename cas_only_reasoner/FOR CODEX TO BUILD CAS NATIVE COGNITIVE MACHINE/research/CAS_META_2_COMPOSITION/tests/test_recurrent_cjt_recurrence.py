"""Non-neural tests for the recurrent CJT candidate (CAS_RDCJT_001).

No torch, no GPU, no model, no AWS. The transformation is a plain Python function, so
the recurrence, its arithmetic bounds, the cost accounting and the depth schedule are
all exercised exactly.
"""
import pytest

from cas_meta2.recurrent_cjt import recurrence as rc


def _core(vector):
    """A deterministic stand-in for the shared transformation F_theta."""
    return [0.5 * value + 0.1 * (index + 1) for index, value in enumerate(vector)]


ENCODED = [1.0, -2.0, 3.0, 0.5]


# --------------------------------------------------------------------------
# the declared profile
# --------------------------------------------------------------------------

def test_the_declared_profile_matches_the_directive():
    profile = rc.profile_document()
    assert profile["candidate"] == "CAS_RDCJT_001"
    assert profile["depths"] == [1, 2, 4, 8]
    assert profile["primary_depth"] == 8
    assert profile["lambda"] == 0.5 and profile["epsilon"] == 1e-6
    assert profile["new_trainable_matrices"] == 0
    assert profile["reuses_one_transformation"] is True
    assert profile["reinjects_the_original_input"] is True
    assert profile["optimizer_updates_per_batch"] == 1
    assert profile["depth_selection_by_checker"] is False
    assert profile["evaluation_depths"] == ["R1", "R2", "R4", "R8", "RESET_8"]
    assert len(profile["profile_sha256"]) == 64


def test_every_depth_gets_four_complete_rounds_including_maintenance():
    assert rc.ROUND_DEPTH_SCHEDULE == (1, 2, 4, 8, 2, 4, 8, 1, 4, 8, 1, 2, 8, 1, 2, 4)
    assert rc.depth_coverage() == {1: 4, 2: 4, 4: 4, 8: 4}
    assert rc.depth_for_round(0) == 1 and rc.depth_for_round(15) == 4
    with pytest.raises(ValueError):
        rc.depth_for_round(16)
    # the maintenance phase is part of every round, so its exposure is equal too
    assert sum(updates for _p, _d, updates in rc.ROUND_PHASES) == 8
    assert sum(decisions for _p, decisions, _u in rc.ROUND_PHASES) == 56


# --------------------------------------------------------------------------
# the arithmetic
# --------------------------------------------------------------------------

def test_one_pass_is_exactly_the_current_computation():
    one = rc.run_passes(ENCODED, _core, depth=1)
    assert one == _core(ENCODED)
    # an explicit zero state must reproduce it identically
    two = rc.run_passes(ENCODED, _core, depth=1, state=[0.0] * len(ENCODED))
    assert one == two


def test_more_passes_reinject_the_original_input():
    depth_one = rc.run_passes(ENCODED, _core, depth=1)
    depth_two = rc.run_passes(ENCODED, _core, depth=2)
    depth_four = rc.run_passes(ENCODED, _core, depth=4)
    assert depth_two != depth_one and depth_four != depth_two
    assert len(depth_four) == len(ENCODED)


def test_the_feedback_cannot_exceed_half_the_input_magnitude():
    """The one property the directive claims for lambda = 0.5, tested as arithmetic."""
    state = [10.0, -20.0, 30.0, 5.0]
    carried = rc.feedback(state, ENCODED)
    assert rc.rms(carried) <= rc.LAMBDA * rc.rms(ENCODED) + 1e-9
    # and it holds for a state far larger than the input
    huge = [1e6, -1e6, 1e6, 1e6]
    assert rc.rms(rc.feedback(huge, ENCODED)) <= rc.LAMBDA * rc.rms(ENCODED) + 1e-9
    # a zero state carries nothing
    assert rc.feedback([0.0] * 4, ENCODED) == [0.0] * 4
    with pytest.raises(ValueError):
        rc.feedback([1.0, 2.0], ENCODED)


def test_reset_state_is_a_mechanism_check_not_a_second_architecture():
    one_pass = rc.run_passes(ENCODED, _core, depth=1)
    reset_eight = rc.run_passes(ENCODED, _core, depth=8, reset_each_pass=True)
    assert reset_eight == one_pass, (
        "eight computations with the state discarded must reproduce one pass")
    carried_eight = rc.run_passes(ENCODED, _core, depth=8)
    assert carried_eight != one_pass


def test_a_state_is_allocated_per_question_and_never_shared():
    states = rc.per_question_state(3, width=4)
    assert len(states) == 3 and all(len(s) == 4 for s in states)
    states[0][0] = 99.0
    assert states[1][0] == 0.0 and states[2][0] == 0.0
    with pytest.raises(ValueError):
        rc.per_question_state(0, width=4)


def test_an_undeclared_depth_is_refused():
    for depth in (0, 3, 16, 100):
        with pytest.raises(ValueError) as error:
            rc.run_passes(ENCODED, _core, depth=depth)
        assert "DEPTH_NOT_DECLARED" in str(error.value)


# --------------------------------------------------------------------------
# cost accounting, and the two boundaries
# --------------------------------------------------------------------------

def test_the_declared_course_cost_is_derived_and_matches_the_directive():
    cost = rc.course_cost()
    assert cost["one_pass"]["sample_level_core_passes"] == 896
    assert cost["one_pass"]["optimizer_updates"] == 128
    assert cost["one_pass"]["batched_core_forward_calls"] == 128
    assert cost["recurrent"]["sample_level_core_passes"] == 3360
    assert cost["recurrent"]["optimizer_updates"] == 128, (
        "eight passes are eight sample passes and ONE update")
    assert cost["recurrent"]["batched_core_forward_calls"] == 480
    assert cost["recurrent"]["ratio_of_sample_passes"] == 3.75
    assert cost["recurrent"]["optimizer_updates"] == cost["one_pass"]["optimizer_updates"]
    assert cost["declared"]["teaching_decisions"] == 896
    assert cost["declared"]["optimizer_updates"] == 128


def test_accounting_charges_passes_separately_from_updates():
    accounting = rc.Accounting()
    accounting.charge(depth=8, samples=7).update()
    accounting.charge(depth=1, samples=7).update()
    report = accounting.report()
    assert report["sample_level_core_passes"] == 8 * 7 + 7
    assert report["batched_core_forward_calls"] == 9
    assert report["optimizer_updates"] == 2
    assert report["mean_depth"] == 4.5
    assert "not measured GPU work" in report["note"]
    with pytest.raises(ValueError):
        rc.Accounting().charge(depth=3, samples=1)


def test_the_checker_may_not_choose_the_depth():
    with pytest.raises(ValueError) as error:
        rc.select_best_depth({1: "a", 4: "b", 8: "c"})
    assert "DEPTH_SELECTION_BY_CHECKER_IS_NOT_A_SUPPORTED_PATH" in str(error.value)


def test_the_depth_sweep_reports_gains_and_losses_separately():
    """The answer at depth eight is the answer at depth eight, gains and losses both."""
    per_depth = {
        1: {"q1": True, "q2": True, "q3": False, "q4": False},
        4: {"q1": True, "q2": False, "q3": True, "q4": False},
        8: {"q1": False, "q2": False, "q3": True, "q4": True},
    }
    tally = rc.two_way_tally(per_depth)
    assert tally["R4"] == {"gained": ["q3"], "lost": ["q2"], "gained_count": 1,
                           "lost_count": 1, "net": 0, "compared_questions": 4}
    assert tally["R8"]["gained"] == ["q3", "q4"]
    assert tally["R8"]["lost"] == ["q1", "q2"]
    assert tally["R8"]["net"] == 0, (
        "eight passes fixed two questions and spoiled two: a net-zero result that a "
        "single pooled average would have hidden")
    with pytest.raises(ValueError):
        rc.two_way_tally({4: {"q1": True}})
