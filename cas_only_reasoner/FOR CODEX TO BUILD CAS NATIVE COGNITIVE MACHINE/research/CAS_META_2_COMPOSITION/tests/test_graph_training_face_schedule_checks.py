"""The owner's pre-signature checks, as tests.

Four conditions in one job, the selected schedule stated exactly, and batching that
differs at the *update-batch level* rather than merely reordering examples inside
identical batches. Pure: no torch, no provider, no reservation.
"""
from collections import Counter

import pytest

from aws import graph_training_face_launch as fl
from cas_meta2.graph_teaching import face_schedule as schedule


def _batches(events, size=schedule.BATCH_SIZE):
    """Ordered batch memberships: order *inside* a batch is irrelevant."""
    return [frozenset(schedule.event_key(event) for event in events[index:index + size])
            for index in range(0, len(events), size)]


def test_loop_and_mixed_order_differ_at_the_update_batch_level():
    """A different event log is not enough; the batches themselves must differ."""
    loop = schedule.cfc_events()
    mixed = schedule.mixed_order(loop)
    loop_batches, mixed_batches = _batches(loop), _batches(mixed)
    assert len(loop_batches) == len(mixed_batches) == 576
    identical = sum(1 for first, second in zip(loop_batches, mixed_batches)
                    if first == second)
    assert identical == 0, "the organizations must not share whole update batches"
    assert not (set(loop_batches) & set(mixed_batches)), \
        "no batch may coincide anywhere between the organizations"


def test_the_two_organizations_keep_the_identical_teaching_event_multiset():
    loop = schedule.cfc_events()
    mixed = schedule.mixed_order(loop)
    assert Counter(schedule.event_key(event) for event in loop) == \
        Counter(schedule.event_key(event) for event in mixed)
    # supports travel with their event and are never redistributed
    loop_supports = Counter()
    mixed_supports = Counter()
    for event in loop:
        for support in event.get("support_ids") or ():
            loop_supports[(schedule.event_key(event), support)] += 1
    for event in mixed:
        for support in event.get("support_ids") or ():
            mixed_supports[(schedule.event_key(event), support)] += 1
    assert loop_supports == mixed_supports


def test_the_loop_orders_within_before_across_before_return_every_round():
    """The loop must give earlier phases a chance to affect later ones."""
    for round_index in (0, 5, 41):
        sequence = [event["movement"] for event in schedule.cfc_round_events(round_index)]
        assert len(sequence) == 48
        last_within = max(index for index, name in enumerate(sequence)
                          if name == "WITHIN_CUBE")
        first_across = sequence.index("ACROSS_FACE")
        last_across = max(index for index, name in enumerate(sequence)
                          if name == "ACROSS_FACE")
        first_return = sequence.index("RETURN_TO_CUBE")
        assert last_within < first_across, "within-cube work must precede across-face"
        assert last_across < first_return, "across-face work must precede the return"
        counts = Counter(sequence)
        assert counts == {"WITHIN_CUBE": 28, "ACROSS_FACE": 12,
                          "RETURN_TO_CUBE": 8}


def test_weights_and_optimizer_state_persist_across_a_whole_condition():
    """One learner per condition: the phases are not separate trainings."""
    import ast
    from pathlib import Path
    from cas_meta2.graph_teaching import face_experiment as fx

    source = Path(fx.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    function = next(node for node in ast.walk(tree)
                    if isinstance(node, ast.FunctionDef)
                    and node.name == "run_condition_with_evaluation")
    segment = ast.get_source_segment(source, function)
    assert segment.count("learner_factory(") == 1, \
        "a condition must build exactly one learner so state persists"
    assert "learner=learner" in segment, \
        "the teaching run must receive that same learner"
    training = next(node for node in ast.walk(tree)
                    if isinstance(node, ast.FunctionDef)
                    and node.name == "run_condition")
    training_source = ast.get_source_segment(source, training)
    for forbidden in ("optim.Adam", "optim.SGD", "optimizer =", "optimizer="):
        assert forbidden not in training_source, \
            "the runner must never build an optimizer mid-condition"
    assert "for batch in _batches(episodes, batch_size)" in training_source
    assert training_source.index("learner = learner_factory") < \
        training_source.index("for batch in _batches")


def test_the_selected_schedule_is_the_cfc_loop_and_says_so():
    facts = fl.schedule_facts()
    assert facts["selected_schedule"] == "CFC_LOOP"
    assert facts["events_per_condition"] == 4608
    assert facts["movements_per_condition"] == {"WITHIN_CUBE": 2688,
                                                "ACROSS_FACE": 1152,
                                                "RETURN_TO_CUBE": 768}
    assert facts["completed_rounds_per_condition"] == 96
    assert facts["worked_support_exposures_per_condition"] == 6912
    assert facts["optimizer_updates_per_condition"] == 576
    assert facts["total_optimizer_updates"] == 2304
    assert facts["grounding_schedule_not_run"]["updates_at_declared_batch"] == 1152
    assert "not what this job runs" in \
        facts["grounding_schedule_not_run"]["note"]
    assert "9,216-query" in fl.DESIGN["schedule_scope"]


def test_the_declared_wall_clock_fits_inside_the_reservation():
    bounds = fl.validate_bounds()
    assert bounds["fits"] is True
    assert bounds["total_ceiling_seconds"] == (
        bounds["per_condition_seconds"] * len(fl.FROZEN_CONDITIONS)
        + bounds["install_allowance_seconds"])
    assert bounds["total_ceiling_seconds"] <= bounds["instance_ceiling_seconds"]
    with pytest.raises(ValueError) as error:
        fl.validate_bounds({"instance_seconds_max": 3600})
    assert "FACE_DESIGN_WALL_CLOCK_EXCEEDS_RESERVATION" in str(error.value)


def test_the_four_conditions_are_distinct_and_separate():
    assert len(set(fl.FROZEN_CONDITIONS)) == 4
    assert set(fl.FROZEN_ORGANIZATION.values()) == {"CFC_LOOP", "MIXED_ORDER"}
    assert set(fl.FROZEN_CUES.values()) == {"stable", "neutral"}
    for condition in fl.FROZEN_CONDITIONS:
        assert condition in fl.FROZEN_ORGANIZATION
        assert condition in fl.FROZEN_CUES
    # the two cue arms differ only by the cue, and the two organizations only by
    # the batch composition: nothing else distinguishes them
    assert fl.DESIGN["events_per_condition"] == fl.FROZEN_EVENTS_PER_CONDITION


def test_the_request_states_the_single_initialization_limitation():
    plan = fl.plan_only()
    assert plan["status"] == "PLAN_ONLY_NOT_EXECUTED"
    assert plan["reservation_created"] is False
    assert plan["provider_calls"] == 0
    assert plan["schedule_facts"]["total_optimizer_updates"] == 2304
    assert plan["bounds"]["fits"] is True
    assert "not_included" in plan["experiment"]
