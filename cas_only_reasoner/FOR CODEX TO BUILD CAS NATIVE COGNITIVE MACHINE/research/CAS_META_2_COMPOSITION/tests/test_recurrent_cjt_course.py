"""Pure tests for the recurrent CJT course (CAS_RDCJT_001 step three).

No torch, no GPU, no model, no AWS. The course is a schedule over events and batches,
so it is exercised exactly: the declared 16 rounds, the 896 decisions, the 128 batches,
the 128 updates, the four-rounds-per-depth coverage, the binding to the schedule that
already exists, and the two conditions that differ only in depth.
"""
import pytest

from cas_meta2.recurrent_cjt import course as co
from cas_meta2.recurrent_cjt import recurrence as rc


class StubLearner:
    def __init__(self):
        self.depths = []

    def set_depth(self, depth):
        self.depths.append(depth)
        return depth


class StubBatchStep:
    """Records what it was asked to do, and charges the accounting on the batch.

    The charging is modelled here rather than in ``run_course`` because the deployed
    batch step owns it: ``learner.recurrent_batch_step`` calls ``charge`` and
    ``update`` once per batch, and a course that charged a second time would double
    count every pass.
    """

    def __init__(self, *, steps_per_batch=1, accounting=None):
        self.calls = []
        self.steps_per_batch = steps_per_batch
        self.accounting = accounting

    def __call__(self, learner, batch):
        self.calls.append({"depth": learner.depths[-1], "size": len(batch),
                           "phase": batch[0][1] if batch else None})
        if self.accounting is not None:
            self.accounting.charge(depth=learner.depths[-1], samples=len(batch))
            self.accounting.update()
        return {"optimizer_steps": self.steps_per_batch, "mean_loss": 0.25,
                "batch_size": len(batch), "depth": learner.depths[-1]}


def stub_tasks(round_index):
    return {phase: [(round_index, phase, position) for position in range(decisions)]
            for phase, decisions, _updates in rc.ROUND_PHASES}


# --------------------------------------------------------------------------
# the declared shape
# --------------------------------------------------------------------------

def test_the_course_is_the_declared_sixteen_rounds():
    plan = co.course_plan()
    assert plan["round_count"] == 16
    assert plan["decisions"] == 896
    assert plan["batches"] == 128
    assert plan["updates"] == 128
    assert plan["depth_coverage"] == {1: 4, 2: 4, 4: 4, 8: 4}
    assert plan["depths"] == list(rc.ROUND_DEPTH_SCHEDULE)
    for entry in plan["rounds"]:
        assert entry["decisions"] == 56
        assert entry["batches"] == 8
        assert entry["updates"] == 8, (
            "8 updates per round is derived from the declared batch structure "
            "[8,8,8,4]/[8,4]/[8]/[8], not copied")
    assert plan["maintenance"]["status"] == "DECLARED_CHOICE_FILLING_A_DECLARED_GAP"


def test_a_one_pass_course_has_the_same_shape_as_the_recurrent_one():
    recurrent = co.course_plan()
    one_pass = co.course_plan(depths=(1,) * 16)
    for field in ("round_count", "decisions", "batches", "updates"):
        assert one_pass[field] == recurrent[field], (
            "the conditions must be matched on %s" % field)
    assert one_pass["depths"] == [1] * 16
    assert one_pass["depth_coverage"] == {1: 16}
    assert set(recurrent["depths"]) == {1, 2, 4, 8}


def test_an_undeclared_course_depth_is_refused():
    with pytest.raises(ValueError) as error:
        co.round_plan(0, depth=3)
    assert "COURSE_DEPTH_NOT_DECLARED" in str(error.value)
    with pytest.raises(ValueError):
        co.round_plan(16)


# --------------------------------------------------------------------------
# the binding to the schedule that already exists
# --------------------------------------------------------------------------

def test_the_course_agrees_with_the_schedule_that_already_exists():
    binding = co.schedule_binding()
    assert binding["all_agree"] is True
    assert binding["by_movement"] == {"WITHIN_CUBE": 28, "ACROSS_FACE": 12,
                                      "RETURN_TO_CUBE": 8}
    assert binding["scheduled_events"] == 48
    assert binding["maintenance_stream"].startswith(
        "the schedule has no maintenance event generator")


def test_a_schedule_that_drifts_is_caught_rather_than_reported(monkeypatch):
    from cas_meta2.graph_teaching import face_schedule as schedule
    original = schedule.cfc_round_events

    def drifted(round_index, built=None):
        return [event for event in original(round_index, built=built)
                if not (event["movement"] == "ACROSS_FACE"
                        and event.get("decision") == "content_comparison")]

    monkeypatch.setattr(schedule, "cfc_round_events", drifted)
    binding = co.schedule_binding()
    assert binding["all_agree"] is False
    assert binding["agreement"]["ACROSS_FACE"] == {"scheduled": 6, "declared": 12,
                                                   "agrees": False}
    assert binding["agreement"]["WITHIN_CUBE"]["agrees"] is True


def test_the_maintenance_source_is_declared_and_recorded():
    # the same cohort's previous visit, and round zero replays itself rather than
    # reaching outside the course
    assert co.maintenance_round(0) == 0
    assert co.maintenance_round(5) == 0
    assert co.maintenance_round(6) == 0
    assert co.maintenance_round(7) == 1
    assert co.maintenance_round(15) == 9
    with pytest.raises(ValueError):
        co.maintenance_round(-1)
    note = co.MAINTENANCE_NOTE
    assert note["declared"] == {"decisions_per_round": 8, "batches": [8],
                                "updates_per_round": 1}
    assert "not WHICH decisions" in note["source"]
    assert "conditional" in note["consequence"]


# --------------------------------------------------------------------------
# running it
# --------------------------------------------------------------------------

def test_the_course_runs_the_declared_batches_and_nothing_else():
    learner = StubLearner()
    step = StubBatchStep()
    result = co.run_course(learner=learner, batch_step=step,
                           tasks_for_round=stub_tasks)
    report = result["report"]
    assert report["matches_declaration"] is True
    assert report["mismatches"] == []
    assert report["delivered"] == {"decisions": 896, "batches": 128, "updates": 128,
                                   "rounds": 16,
                                   "rounds_present": list(range(16))}
    assert report["declared"] == report["delivered"]
    assert report["missing_rounds"] == []
    assert len(step.calls) == 128
    assert sum(call["size"] for call in step.calls) == 896
    assert learner.depths == list(rc.ROUND_DEPTH_SCHEDULE), (
        "each round ran at its scheduled depth")
    assert report["depths_delivered"] == list(rc.ROUND_DEPTH_SCHEDULE)
    # every round is 8 updates, whatever its depth
    per_round = {index: entry["updates"]
                 for index, entry in report["by_round"].items()}
    assert set(per_round.values()) == {8}
    assert report["boundary"]["equal_updates_across_conditions"].startswith("8 per round")
    assert "3.75" in report["boundary"]["unequal_compute_across_conditions"]


def test_the_one_pass_condition_runs_the_same_batches_at_depth_one():
    learner = StubLearner()
    step = StubBatchStep()
    result = co.run_course(learner=learner, batch_step=step,
                           tasks_for_round=stub_tasks, depths=(1,) * 16)
    assert result["report"]["matches_declaration"] is True
    assert result["report"]["delivered"]["updates"] == 128
    assert result["report"]["delivered"]["decisions"] == 896
    assert set(learner.depths) == {1}
    assert {call["depth"] for call in step.calls} == {1}
    assert len(step.calls) == 128, (
        "the depths differ between conditions; the course does not")


def test_the_course_charges_every_pass_to_the_accounting_it_is_given():
    accounting = rc.Accounting()
    learner = StubLearner()
    step = StubBatchStep(accounting=accounting)
    co.run_course(learner=learner, batch_step=step, tasks_for_round=stub_tasks,
                  accounting=accounting)
    report = accounting.report()
    assert report["optimizer_updates"] == 128
    assert report["sample_level_core_passes"] == 3360
    assert report["mean_depth"] == 3.75
    assert report["batched_core_forward_calls"] == 480


def test_the_one_pass_course_charges_896_passes_and_128_updates():
    accounting = rc.Accounting()
    learner = StubLearner()
    step = StubBatchStep(accounting=accounting)
    co.run_course(learner=learner, batch_step=step, tasks_for_round=stub_tasks,
                  depths=(1,) * 16, accounting=accounting)
    report = accounting.report()
    assert report["optimizer_updates"] == 128
    assert report["sample_level_core_passes"] == 896
    assert report["mean_depth"] == 1.0, (
        "the matched condition is one pass per decision at every round")


def test_a_short_phase_is_refused_rather_than_taught_partially():
    learner = StubLearner()
    step = StubBatchStep()

    def short_tasks(round_index):
        supplied = stub_tasks(round_index)
        supplied["ACROSS_FACE"] = supplied["ACROSS_FACE"][:-1]
        return supplied

    with pytest.raises(ValueError) as error:
        co.run_course(learner=learner, batch_step=step, tasks_for_round=short_tasks)
    assert "COURSE_PHASE_LENGTH:ACROSS_FACE:11!=12" in str(error.value)


def test_a_batch_that_reports_two_updates_is_refused():
    learner = StubLearner()
    step = StubBatchStep(steps_per_batch=2)
    with pytest.raises(ValueError) as error:
        co.run_course(learner=learner, batch_step=step, tasks_for_round=stub_tasks)
    assert "COURSE_BATCH_MORE_THAN_ONE_UPDATE" in str(error.value)


def test_a_delivered_shortfall_is_reported_as_a_mismatch_not_as_a_match():
    """A whole missing round must fail the report, not vanish from it."""
    learner = StubLearner()
    step = StubBatchStep()
    result = co.run_course(learner=learner, batch_step=step,
                           tasks_for_round=stub_tasks)
    rows = [row for row in result["rows"] if row["round"] != 3]
    report = co.course_report(rows, plan=result["plan"])
    assert report["matches_declaration"] is False
    assert report["missing_rounds"] == [3]
    assert {"round": 3, "field": "round_delivered", "delivered": "absent",
            "declared": 56} in report["mismatches"]
    assert report["delivered"]["rounds"] == 15
    assert report["declared"]["rounds"] == 16
    assert report["declared"]["rounds_present"] == list(range(16))
    assert 3 not in report["delivered"]["rounds_present"]


def test_a_short_phase_inside_a_delivered_round_is_named():
    """Completeness is checked per phase, not only per round."""
    learner = StubLearner()
    step = StubBatchStep()
    result = co.run_course(learner=learner, batch_step=step,
                           tasks_for_round=stub_tasks)
    rows = [row for row in result["rows"]
            if not (row["round"] == 2 and row["phase"] == "ACROSS_FACE")]
    report = co.course_report(rows, plan=result["plan"])
    assert report["matches_declaration"] is False
    assert report["missing_rounds"] == []
    named = [entry for entry in report["mismatches"]
             if entry["field"] == "phase:ACROSS_FACE" and entry["round"] == 2]
    assert len(named) == 1
    assert named[0]["delivered"]["decisions"] == 0
    assert named[0]["declared"] == {"decisions": 12, "batches": 2}


# --------------------------------------------------------------------------
# what exists and what does not
# --------------------------------------------------------------------------

def test_the_readiness_report_states_the_absent_items_and_spends_nothing():
    ready = co.readiness_report()
    assert ready["status"] == "RECURRENT_CJT_READY_NEURAL_UNTESTED"
    assert set(ready["absent"]) == {
        "fresh_family_panel_for_the_recurrent_test",
        "packaged_worker_and_entrypoint_for_the_recurrent_candidate",
        "repository_frozen_digests_for_this_candidate",
        "neural_execution",
        "costed_execution_request"}
    assert ready["budget"]["reserved"] == "$375.00"
    assert ready["budget"]["free"] == "$25.00"
    assert "None of it is a measurement of learning" in ready["boundary"]
    assert ready["implemented"]["course_bound_to_the_existing_schedule"].endswith(
        "schedule_binding")
    assert ready[
        "declared_choices_filling_declared_gaps"]["maintenance_event_source"] == (
        "DECLARED_CHOICE_FILLING_A_DECLARED_GAP")
