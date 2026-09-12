"""The two matched arms and the fixed-weight sweep, driven end to end with fakes.

No torch, no GPU, no AWS, no reservation. Every heavy dependency of
``experiment.run`` is injected, so this exercises the REAL control flow - the
matched-start check, the course, the sweep, the two-way tally, the capacity
check and the panel provenance - against recording stand-ins.

What these tests are protecting
-------------------------------
The experiment's whole claim is "the recurrence is the only thing that differs".
Each test below removes one way that claim could be false while the run still
looked successful:

* different starting weights -> ``RECURRENT_INITIAL_WEIGHTS_NOT_MATCHED``
* different trainable capacity -> ``RECURRENT_ARM_CAPACITY_DIFFERS``
* a checker choosing the flattering depth -> ``select_best_depth`` raises
* a pooled sweep average hiding a two-gain/two-loss depth -> gains and losses
  are reported apart
* examined material presented as an independent test -> panel provenance says so
"""
from collections import OrderedDict

import pytest

from cas_meta2.recurrent_cjt import course as cs
from cas_meta2.recurrent_cjt import experiment as ex
from cas_meta2.recurrent_cjt import recurrence as rc


# --------------------------------------------------------------------------
# stand-ins
# --------------------------------------------------------------------------

class FakeParameter:
    def __init__(self, name):
        self.name = name


class FakeModule:
    """Two named parameters, so the capacity check has something real to count."""

    def __init__(self, count=2):
        self._names = ["w%d" % index for index in range(count)]

    def named_parameters(self):
        return [(name, FakeParameter(name)) for name in self._names]


class FakeLearner:
    """Only what run_course and the experiment actually touch."""

    def __init__(self, *, arm, module, accounting=None, answers=None):
        self.arm = arm
        self.module = module
        self.accounting = accounting
        self.depth = 1
        self.reset_each_pass = False
        self.condition_tag = None
        self.depths_seen = []
        self.updates = 0
        self._answers = answers or {}

    def set_depth(self, depth):
        rc.require(depth in rc.DEPTHS, "DEPTH_NOT_DECLARED:" + str(depth))
        self.depth = depth
        self.depths_seen.append(depth)

    def checkpoint_identity(self):
        return "digest-of-" + self.arm


ITEMS = ["item_%02d" % index for index in range(10)]

#: R8 fixes two questions the one-pass answer got wrong and spoils two it got
#: right. Net zero. A pooled average would report "no change"; the two-way tally
#: must report two gained and two lost.
ANSWERS = {
    "R1": {item: index % 2 == 0 for index, item in enumerate(ITEMS)},
    "R2": {item: index % 2 == 0 for index, item in enumerate(ITEMS)},
    "R4": {item: index % 2 == 0 for index, item in enumerate(ITEMS)},
    "R8": {**{item: index % 2 == 0 for index, item in enumerate(ITEMS)},
           "item_01": True, "item_03": True,      # gained
           "item_00": False, "item_02": False},   # lost
    "RESET_8": {item: index % 2 == 0 for index, item in enumerate(ITEMS)},
    "before": {item: False for item in ITEMS},
    "after": {item: index % 2 == 0 for index, item in enumerate(ITEMS)},
}


def evaluate_panel(*, learner, items, built=None, phase):
    table = ANSWERS.get(phase, ANSWERS["after"])
    return [{"item_id": item, "is_correct": bool(table.get(item, False)),
             "phase": phase} for item in items]


def depth_sweep(*, learner, items, evaluate_panel, built=None,
                labels=rc.EVALUATION_DEPTHS):
    before = learner.checkpoint_identity()
    rows = OrderedDict()
    for label in labels:
        rows[label] = evaluate_panel(learner=learner, items=items, built=built,
                                     phase=label)
    after = learner.checkpoint_identity()
    return {"rows": rows, "weights_unchanged": before == after,
            "parameter_digest_before": before, "parameter_digest_after": after,
            "labels": list(rows)}


def tasks_for_round(round_index):
    """Pools of exactly the declared length, so run_course's checks are real."""
    plan = cs.round_plan(round_index)
    return {phase["phase"]: ["task_%d_%s_%d" % (round_index, phase["phase"], n)
                             for n in range(phase["decisions"])]
            for phase in plan["phases"]}


def batch_step(learner, batch):
    """Charges the learner's ledger exactly as recurrent_batch_step does."""
    learner.updates += 1
    if learner.accounting is not None:
        learner.accounting.charge(depth=learner.depth, samples=len(batch))
        learner.accounting.update()
    return {"optimizer_steps": 1, "mean_loss": 0.5, "batch_size": len(batch),
            "depth": learner.depth}


def config(**overrides):
    base = {"schema": "cas.recurrent-cjt-config/1", "job": "rdcjt-test",
            "seed": 20260912, "learning_rate": 0.003, "max_wall_seconds": 1200.0}
    base.update(overrides)
    return base


def harness(*, module_counts=(2, 2), snapshots=("same", "same")):
    modules = {arm: FakeModule(count)
               for arm, count in zip(ex.ARMS, module_counts)}
    snaps = dict(zip(ex.ARMS, snapshots))
    order = []

    def framework_factory(seed):
        arm = ex.ARMS[len(order)]
        order.append(arm)
        return ({"seed": seed, "arm": arm}, {"arm": arm})

    def factory_for(arm):
        def make(*, framework, model, accounting=None, arm=arm):
            return FakeLearner(arm=arm, module=modules[arm], accounting=accounting)
        return make

    def parameter_snapshot(framework, model):
        # a MAPPING, exactly what trainer.parameter_snapshot returns - the shape
        # that would have broken a set() over raw snapshots
        return {"layer.weight": snaps[framework["arm"]], "layer.bias": "b"}

    return {
        "framework_factory": framework_factory,
        "learner_factories": {arm: factory_for(arm) for arm in ex.ARMS},
        "batch_steps": {arm: batch_step for arm in ex.ARMS},
        "evaluate_panel": evaluate_panel,
        "panel_items": ITEMS,
        "depth_sweep": depth_sweep,
        "parameter_snapshot": parameter_snapshot,
        "tasks_for_round": tasks_for_round,
    }


def run(**overrides):
    kwargs = harness(**{k: v for k, v in overrides.items()
                        if k in ("module_counts", "snapshots")})
    kwargs.update({k: v for k, v in overrides.items()
                   if k not in ("module_counts", "snapshots")})
    return ex.run(config(), **kwargs)


# --------------------------------------------------------------------------
# the plan
# --------------------------------------------------------------------------

def test_the_plan_declares_the_same_course_for_both_arms():
    plan = ex.compile_plan(config())
    assert plan["arms"] == ["one_pass", "recurrent"]
    assert plan["teaching_decisions_per_arm"] == 896
    assert plan["optimizer_updates_per_arm"] == 128
    assert plan["round_depths"] == list(rc.ROUND_DEPTH_SCHEDULE)
    assert plan["one_pass_depth"] == 1


def test_a_sweep_without_the_one_pass_baseline_is_refused_at_plan_time():
    with pytest.raises(ValueError) as caught:
        ex.compile_plan(config(evaluation_depths=("R2", "R4", "R8")))
    assert "RECURRENT_SWEEP_NEEDS_THE_ONE_PASS_BASELINE" in str(caught.value)


def test_an_undeclared_round_depth_is_refused():
    with pytest.raises(ValueError) as caught:
        ex.compile_plan(config(round_depths=(1, 3)))
    assert "RECURRENT_ROUND_DEPTH:3" in str(caught.value)


# --------------------------------------------------------------------------
# the matched start
# --------------------------------------------------------------------------

def test_both_arms_run_and_the_envelope_is_delivered():
    report = run()
    assert report["status"] == ex.STATUS_DELIVERED
    assert report["matched_initial_weights"] is True
    assert sorted(report["arms"]) == ["one_pass", "recurrent"]


def test_different_starting_weights_fail_the_run_closed():
    """A difference between the arms is only the recurrence if the start matched."""
    with pytest.raises(ValueError) as caught:
        run(snapshots=("start-a", "start-b"))
    assert "RECURRENT_INITIAL_WEIGHTS_NOT_MATCHED" in str(caught.value)


def test_extra_capacity_in_the_recurrent_arm_fails_the_run_closed():
    """If the arms differ in trainable parameters, capacity is a rival explanation."""
    with pytest.raises(ValueError) as caught:
        run(module_counts=(2, 3))
    assert "RECURRENT_ARM_CAPACITY_DIFFERS" in str(caught.value)


def test_the_capacity_claim_is_measured_and_carried():
    report = run()
    counts = report["trainable_parameters_by_arm"]
    assert counts["one_pass"] == counts["recurrent"] == 2


# --------------------------------------------------------------------------
# the course each arm actually ran
# --------------------------------------------------------------------------

def test_the_one_pass_arm_stays_at_depth_one_and_the_other_varies():
    report = run()
    one = report["arms"]["one_pass"]["rows"]
    rec = report["arms"]["recurrent"]["rows"]
    assert {row["depth"] for row in one} == {1}
    assert {row["depth"] for row in rec} == set(rc.DEPTHS)


def test_both_arms_take_the_same_decisions_and_updates():
    report = run()
    for arm in ex.ARMS:
        account = report["arms"][arm]["accounting"]
        assert account["optimizer_updates"] == 128
    one = report["arms"]["one_pass"]["accounting"]
    rec = report["arms"]["recurrent"]["accounting"]
    # same updates, different compute: that is the whole point of reporting both
    assert one["optimizer_updates"] == rec["optimizer_updates"]
    assert rec["sample_level_core_passes"] > one["sample_level_core_passes"]


def test_the_recurrent_arm_costs_three_and_three_quarter_times_the_passes():
    report = run()
    one = report["arms"]["one_pass"]["accounting"]["sample_level_core_passes"]
    rec = report["arms"]["recurrent"]["accounting"]["sample_level_core_passes"]
    assert one == 896
    assert rec == 3360
    assert rec / one == 3.75


# --------------------------------------------------------------------------
# the sweep: gains AND losses
# --------------------------------------------------------------------------

def test_a_net_zero_depth_is_reported_as_two_gained_and_two_lost():
    """The result a single pooled average would have destroyed."""
    report = run()
    comparison = report["sweep_comparison"]
    assert comparison["gained"] == 2
    assert comparison["lost"] == 2
    assert comparison["net"] == 0
    assert comparison["gained_items"] == ["item_01", "item_03"]
    assert comparison["lost_items"] == ["item_00", "item_02"]
    assert comparison["baseline_correct"] == comparison["primary_correct"]


def test_the_reset_check_is_reported_against_the_one_pass_answers():
    report = run()
    assert report["sweep_comparison"]["reset_matches_one_pass"] is True


def test_the_weights_are_reported_as_unmoved_by_the_sweep():
    report = run()
    assert report["sweep_comparison"]["weights_unchanged"] is True


def test_there_is_no_path_that_lets_a_checker_choose_the_depth():
    with pytest.raises(ValueError) as caught:
        rc.select_best_depth(report={"R8": 1.0}, checker=lambda *_: True)
    assert "DEPTH_SELECTION_BY_CHECKER_IS_NOT_A_SUPPORTED_PATH" in str(caught.value)
    report = run()
    assert report["boundary"]["depth_selection_by_checker"].startswith("refused")


def test_a_sweep_missing_the_primary_depth_is_refused():
    sweep = {"rows": OrderedDict([("R1", evaluate_panel(
        learner=None, items=ITEMS, phase="R1"))])}
    with pytest.raises(ValueError) as caught:
        ex.sweep_comparison(sweep, correctness=lambda rows: OrderedDict(
            (row["item_id"], row["is_correct"]) for row in rows))
    assert "RECURRENT_SWEEP_MISSING_PRIMARY" in str(caught.value)


# --------------------------------------------------------------------------
# what the panel can and cannot support
# --------------------------------------------------------------------------

def test_examined_material_is_declared_as_examined():
    report = run()
    panel = report["panel"]
    assert panel["examined_during_teaching"] is True
    assert panel["fresh_family_panel_supplied"] is False
    assert "not evidence of transfer" in panel["what_this_panel_cannot_support"]


def test_a_fresh_panel_is_recorded_when_one_is_supplied():
    report = run(examined_during_teaching=False,
                 fresh_family_panel=["fresh_a", "fresh_b"])
    panel = report["panel"]
    assert panel["examined_during_teaching"] is False
    assert panel["fresh_family_panel_supplied"] is True
    assert panel["fresh_family_panel_items"] == 2
    assert panel["what_this_panel_cannot_support"] is None


def test_the_envelope_states_what_it_does_not_establish():
    report = run()
    note = report["boundary"]["what_this_does_not_establish"]
    assert "nothing here shows that additional passes reason" in note
