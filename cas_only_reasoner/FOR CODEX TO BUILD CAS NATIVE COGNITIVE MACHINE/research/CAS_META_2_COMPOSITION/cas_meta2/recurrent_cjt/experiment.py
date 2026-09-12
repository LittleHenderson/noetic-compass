"""CAS_RDCJT_001 step four: the two matched arms and the fixed-weight depth sweep.

What this module is for
-----------------------
``recurrence.py`` holds the arithmetic, ``learner.py`` binds it to the real
``GraphLearner``, and ``course.py`` drives the variable-depth CFC course. This
module is the experiment those three exist to serve: train ONE-PASS and RECURRENT
from the SAME initial weights on the SAME course, then read the recurrent
checkpoint at every declared depth with its weights frozen.

The comparison this module is built to protect
----------------------------------------------
Two things could explain a difference between the arms, and only one of them is
the hypothesis:

* the recurrence - the thing under test;
* anything else - different starting weights, a different course, a different
  panel, a different readout, extra trainable capacity.

So the second list is closed off mechanically rather than promised in prose:

* ``require_matched_initialization`` compares parameter digests and fails the run
  closed on a mismatch, exactly as ``face_experiment.launch`` does;
* both arms take the same ``framework_factory`` seed, the same compiled episodes
  and the same panel items;
* the recurrent learner adds no trainable matrices - it reuses the registered
  module - and ``arm_parameter_counts`` records both counts so the claim is
  checkable rather than asserted;
* depth one is the existing computation literally, which is what makes the
  one-pass arm a MATCHED control rather than a different model.

What this module refuses to do
------------------------------
* It never lets a checker pick the depth. ``recurrence.select_best_depth``
  raises, and nothing here works around it. The answer at depth eight is the
  answer at depth eight.
* It never reports a single pooled accuracy for the sweep. ``two_way_tally``
  reports gains AND losses per depth, because a net-zero depth that gains two
  questions and loses two is not the same result as a depth that changed nothing,
  and a pooled mean hides exactly that.
* It never treats the examined CFC panel as a fresh test. ``panel_provenance``
  carries whether the items were examined during teaching, and the envelope
  refuses ``fresh_family_panel`` unless the caller supplies one.

No torch import, no AWS, no network. Every heavy dependency is injected, so the
tests drive this whole flow with recording stand-ins and the deployed worker
passes the real ones.
"""
from __future__ import annotations

from collections import OrderedDict

from . import course as cs
from . import recurrence as rc

SCHEMA = "cas.recurrent-cjt-experiment/0.1"
RESULT_SCHEMA = "cas.recurrent-cjt-result/1"

#: The two arms. Order is fixed so the report and the comparison cannot disagree.
ARMS = ("one_pass", "recurrent")

#: The one-pass arm trains at depth one for every round; the recurrent arm takes
#: the declared variable-depth schedule. Both see the same rounds.
ONE_PASS_DEPTH = 1

#: Reported, never inferred: what the sweep compares against.
BASELINE_LABEL = "R1"
PRIMARY_LABEL = "R8"

STATUS_DELIVERED = "RECURRENT_EXPERIMENT_DELIVERED"
STATUS_FAILED = "RECURRENT_EXPERIMENT_FAILED"


def require(condition, code):
    if not condition:
        raise ValueError(code)


# --------------------------------------------------------------------------
# the plan, compiled before anything heavy happens
# --------------------------------------------------------------------------

def compile_plan(config):
    """Validate the config and return the frozen plan.

    Compiled first and separately so a bad configuration fails on the instance in
    seconds, before a framework is built or a single parameter is allocated.
    """
    require(isinstance(config, dict), "RECURRENT_CONFIG_REQUIRED")
    require(config.get("schema") == "cas.recurrent-cjt-config/1",
            "RECURRENT_CONFIG_SCHEMA")
    for key in ("job", "seed", "learning_rate", "max_wall_seconds"):
        require(key in config, "RECURRENT_CONFIG_FIELD:" + key)
    depths = tuple(config.get("round_depths") or rc.ROUND_DEPTH_SCHEDULE)
    for depth in depths:
        require(depth in rc.DEPTHS, "RECURRENT_ROUND_DEPTH:" + str(depth))
    labels = tuple(config.get("evaluation_depths") or rc.EVALUATION_DEPTHS)
    for label in labels:
        require(label in rc.EVALUATION_DEPTHS, "RECURRENT_EVAL_LABEL:" + str(label))
    require(BASELINE_LABEL in labels,
            "RECURRENT_SWEEP_NEEDS_THE_ONE_PASS_BASELINE")
    require(PRIMARY_LABEL in labels, "RECURRENT_SWEEP_NEEDS_THE_PRIMARY_DEPTH")
    plan = cs.course_plan(depths=depths)
    cost = rc.course_cost(depths=depths)
    return {
        "schema": SCHEMA,
        "job": config["job"],
        "seed": int(config["seed"]),
        "arms": list(ARMS),
        "round_depths": list(depths),
        "evaluation_depths": list(labels),
        "one_pass_depth": ONE_PASS_DEPTH,
        "course": plan,
        "declared_cost": cost,
        "learning_rate": config["learning_rate"],
        "max_wall_seconds": float(config["max_wall_seconds"]),
        "optimizer_updates_per_arm": plan["updates"],
        "teaching_decisions_per_arm": plan["decisions"],
        "boundary": (
            "derived planning counts, not measured GPU work; equal teaching "
            "exposure is not equal training compute, and eight internal passes "
            "are eight sample passes and ONE optimizer update"),
    }


# --------------------------------------------------------------------------
# the matched start, enforced rather than promised
# --------------------------------------------------------------------------

def snapshot_digest(snapshot):
    """A stable digest for one arm's starting weights.

    Accepts the mapping ``trainer.parameter_snapshot`` returns, or a string that a
    caller has already digested. Sorting the items makes the digest independent of
    dictionary order, which is the same rule ``face_experiment.launch`` follows.
    """
    if isinstance(snapshot, str):
        return snapshot
    require(hasattr(snapshot, "items"), "RECURRENT_SNAPSHOT_NOT_A_MAPPING")
    # rc.digest canonicalises internally; passing rc.canonical(...) into it would
    # hand json.dumps a bytes object and raise TypeError. One encode, not two.
    return rc.digest(sorted(snapshot.items()))


def require_matched_initialization(snapshots):
    """Both arms must start from the same weights, or the run fails closed.

    A difference between the arms is only attributable to the recurrence if the
    starting point was identical. This mirrors
    ``face_experiment.launch``'s FACE_INITIAL_WEIGHTS_NOT_MATCHED check, for the
    same reason and with the same consequence.
    """
    require(isinstance(snapshots, dict) and len(snapshots) >= 2,
            "RECURRENT_SNAPSHOTS_REQUIRED")
    # Compared as DIGESTS, not as raw snapshots. trainer.parameter_snapshot returns
    # a mapping of parameter name to value, and a mapping is not hashable, so
    # set(snapshots.values()) would have raised TypeError on the real path while the
    # tests passed on strings. Digest first, compare after.
    distinct = sorted(set(snapshot_digest(value) for value in snapshots.values()))
    require(len(distinct) == 1,
            "RECURRENT_INITIAL_WEIGHTS_NOT_MATCHED:" + ",".join(sorted(snapshots)))
    return distinct[0]


def arm_parameter_counts(learners):
    """The trainable-parameter count per arm.

    The whole interpretation rests on the recurrent arm adding no capacity. That
    is a claim about the model, so it is measured here and carried in the
    envelope, not left in a docstring.
    """
    counts = OrderedDict()
    for arm, learner in learners.items():
        module = getattr(learner, "module", None)
        require(module is not None, "RECURRENT_ARM_HAS_NO_MODULE:" + str(arm))
        counts[arm] = sum(1 for _ in module.named_parameters())
    return counts


# --------------------------------------------------------------------------
# one arm
# --------------------------------------------------------------------------

def run_arm(*, arm, framework, model, learner_factory, batch_step, evaluate_panel,
            items, tasks_for_round=None, depths=None, built=None,
            accounting=None, observer=None):
    """Measure the panel, teach the course, measure it again.

    The BEFORE rows come from this same learner before its first update, which is
    the only way they describe a starting point rather than a trained one.
    """
    require(arm in ARMS, "RECURRENT_ARM_UNKNOWN:" + str(arm))
    # The ledger goes to the LEARNER, because that is what charges it:
    # recurrent_batch_step falls back to learner.accounting when no ledger is
    # passed, so an accounting object handed only to run_course would stay at zero
    # and report a $0 compute bill for a real run.
    learner = learner_factory(framework=framework, model=model, arm=arm,
                              accounting=accounting)
    learner.condition_tag = arm
    before = list(evaluate_panel(learner=learner, items=items, built=built,
                                 phase="before"))
    outcome = cs.run_course(learner=learner, batch_step=batch_step,
                            tasks_for_round=tasks_for_round, depths=depths,
                            accounting=accounting, observer=observer)
    after = list(evaluate_panel(learner=learner, items=items, built=built,
                                phase="after"))
    return {"arm": arm, "learner": learner,
            "rows": outcome["rows"], "course_report": outcome["report"],
            "evaluation": {"before": before, "after": after}}


# --------------------------------------------------------------------------
# the sweep, with the weights frozen
# --------------------------------------------------------------------------

def sweep_comparison(sweep, *, correctness=None):
    """R8 against R1 on the SAME weights, reported as gains and losses.

    Reads ``sweep["rows"]`` - the shape ``learner.depth_sweep`` actually returns -
    rather than a convenience map that does not exist. ``correctness`` is injected
    so the tests do not have to import the tensor module; the deployed path passes
    ``learner.correctness_by_question``.

    A single pooled difference is refused on purpose: a depth that gains two
    questions and loses two is not a depth that changed nothing, and that is
    exactly the distinction a pooled mean destroys.
    """
    require(isinstance(sweep, dict), "RECURRENT_SWEEP_REQUIRED")
    rows = sweep.get("rows")
    require(isinstance(rows, dict) and rows, "RECURRENT_SWEEP_HAS_NO_ROWS")
    if correctness is None:
        from .learner import correctness_by_question as correctness
    by_label = OrderedDict((label, dict(correctness(payload)))
                           for label, payload in rows.items())
    require(BASELINE_LABEL in by_label, "RECURRENT_SWEEP_MISSING_BASELINE")
    require(PRIMARY_LABEL in by_label, "RECURRENT_SWEEP_MISSING_PRIMARY")
    # the tally is keyed by DEPTH, which is what two_way_tally consumes; RESET_8 is
    # a mechanism check on the same depth as R8 and is excluded so it cannot appear
    # as a second reading of depth eight
    from .learner import depth_and_reset
    carried = {depth_and_reset(label)[0]: values
               for label, values in by_label.items() if label != "RESET_8"}
    tally = rc.two_way_tally(carried)
    baseline = by_label[BASELINE_LABEL]
    primary = by_label[PRIMARY_LABEL]
    total = len(baseline)
    require(total > 0, "RECURRENT_SWEEP_EMPTY_PANEL")
    gained = sorted(item for item, ok in primary.items()
                    if ok and not baseline.get(item, False))
    lost = sorted(item for item, ok in baseline.items()
                  if ok and not primary.get(item, False))
    reset = by_label.get("RESET_8")
    return {
        "baseline_label": BASELINE_LABEL,
        "primary_label": PRIMARY_LABEL,
        "panel_items": total,
        "baseline_correct": sum(1 for ok in baseline.values() if ok),
        "primary_correct": sum(1 for ok in primary.values() if ok),
        "gained_items": gained,
        "lost_items": lost,
        "gained": len(gained),
        "lost": len(lost),
        "net": len(gained) - len(lost),
        "per_depth": tally,
        "reset_matches_one_pass": (None if reset is None else reset == baseline),
        "weights_unchanged": bool(sweep.get("weights_unchanged")),
        "interpretation": (
            "net is a bookkeeping total, not a result: a depth that gains two and "
            "loses two is not a depth that changed nothing, and both numbers are "
            "reported for every depth"),
    }


def panel_provenance(*, items, examined_during_teaching, fresh_family_panel=None):
    """State plainly what the panel is, because the answer changes the claim.

    The delivered rewired ``direct_inventory`` rows are EXAMINED material. They can
    measure a depth effect on material the learner was taught against; they cannot
    be reported as an independent application test. A fresh family panel does not
    exist for this candidate yet, so this returns that fact rather than letting a
    reader assume otherwise.
    """
    return {
        "panel_item_count": len(list(items)),
        "examined_during_teaching": bool(examined_during_teaching),
        "fresh_family_panel_supplied": fresh_family_panel is not None,
        "fresh_family_panel_items": (len(list(fresh_family_panel))
                                     if fresh_family_panel is not None else 0),
        "what_this_panel_can_support": (
            "a depth effect on examined material"
            if examined_during_teaching else
            "an application measurement on unexamined material"),
        "what_this_panel_cannot_support": (
            "an independent application claim: these items were examined during "
            "teaching, so a gain here is not evidence of transfer"
            if examined_during_teaching else None),
    }


# --------------------------------------------------------------------------
# the whole experiment
# --------------------------------------------------------------------------

def run(config, *, framework_factory, learner_factories, batch_steps,
        evaluate_panel, panel_items, depth_sweep, parameter_snapshot,
        checkpoint_writer=None, tasks_for_round=None, built=None,
        examined_during_teaching=True, fresh_family_panel=None, observer=None):
    """Both arms from one matched start, then the sweep. Returns the envelope.

    Every heavy dependency is injected. The deployed worker passes the real
    ``face_experiment.evaluate_panel``, the real learner factories and the real
    ``learner.depth_sweep``; the tests pass recording stand-ins and drive this
    same flow with no torch and no GPU.
    """
    plan = compile_plan(config)
    for arm in ARMS:
        require(arm in learner_factories, "RECURRENT_FACTORY_MISSING:" + arm)
        require(arm in batch_steps, "RECURRENT_BATCH_STEP_MISSING:" + arm)
    items = list(panel_items)
    require(items, "RECURRENT_PANEL_EMPTY")

    accounting = {arm: rc.Accounting() for arm in ARMS}
    snapshots, arms = OrderedDict(), OrderedDict()
    for arm in ARMS:
        framework, model = framework_factory(plan["seed"])
        snapshots[arm] = parameter_snapshot(framework, model)
        depths = ([ONE_PASS_DEPTH] * len(plan["round_depths"])
                  if arm == "one_pass" else plan["round_depths"])
        arms[arm] = run_arm(
            arm=arm, framework=framework, model=model,
            learner_factory=learner_factories[arm], batch_step=batch_steps[arm],
            evaluate_panel=evaluate_panel, items=items,
            tasks_for_round=tasks_for_round, depths=depths, built=built,
            accounting=accounting[arm], observer=observer)
    initial_digest = require_matched_initialization(snapshots)

    recurrent = arms["recurrent"]["learner"]
    sweep = depth_sweep(learner=recurrent, items=items,
                        evaluate_panel=evaluate_panel, built=built,
                        labels=tuple(plan["evaluation_depths"]))
    comparison = sweep_comparison(sweep)

    checkpoints = {}
    if checkpoint_writer is not None:
        for arm in ARMS:
            checkpoints[arm] = checkpoint_writer(arm, arms[arm]["learner"])

    counts = arm_parameter_counts({arm: arms[arm]["learner"] for arm in ARMS})
    require(len(set(counts.values())) == 1,
            "RECURRENT_ARM_CAPACITY_DIFFERS:" + repr(dict(counts)))

    return {
        "schema": RESULT_SCHEMA,
        "status": STATUS_DELIVERED,
        "job": plan["job"],
        "plan": plan,
        "matched_initial_weights": True,
        "initial_weight_digest": initial_digest,
        "trainable_parameters_by_arm": dict(counts),
        "capacity_note": (
            "identical parameter counts: the recurrent arm reuses the registered "
            "module and adds no trainable matrices, so added capacity is not what "
            "separates the arms"),
        "arms": {arm: {"arm": arm,
                       "rows": arms[arm]["rows"],
                       "course_report": arms[arm]["course_report"],
                       "evaluation": arms[arm]["evaluation"],
                       "accounting": accounting[arm].report()}
                 for arm in ARMS},
        "depth_sweep": sweep,
        "sweep_comparison": comparison,
        "panel": panel_provenance(
            items=items, examined_during_teaching=examined_during_teaching,
            fresh_family_panel=fresh_family_panel),
        "checkpoints": checkpoints,
        "boundary": {
            "automatic_retries": 0,
            "depth_selection_by_checker": "refused: select_best_depth raises",
            "pooled_sweep_accuracy": "refused: gains and losses are reported apart",
            "what_this_does_not_establish": (
                "nothing here shows that additional passes reason. It shows "
                "whether the same frozen weights answer differently with more "
                "internal computation, on this panel, at this course size, from "
                "one matched initialization"),
        },
    }
