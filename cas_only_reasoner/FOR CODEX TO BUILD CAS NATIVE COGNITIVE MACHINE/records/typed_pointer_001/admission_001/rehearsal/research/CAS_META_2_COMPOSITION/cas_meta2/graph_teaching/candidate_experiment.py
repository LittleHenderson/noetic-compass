"""The two-condition checked-component pilot: one call, both conditions, one probe.

STATUS: implementation and packaging only. `launch` performs no provider call, no
reservation, no launch, and no torch import of its own: the worker calls it with
the real framework, tests call it with stubs.

The frozen design (from `AUTHORIZATION_REQUEST_001.md`):

* conditions `checked_component_teaching` and `final_answer_only`, 64 updates each;
* matched initial weights, separate optimizer states, the same frozen encoder,
  framing and scoring path;
* the control's 64 updates are 22 / 21 / 21 over the three whole-answer questions;
* a common 44-question untaught probe, evaluated after the final checkpoint.

Reporting rules enforced here: predictions are recorded before their correction;
scores are retained or marked `unavailable`; the taught whole-answer questions,
the component questions and the probe are reported **separately**; the probe never
selects a checkpoint, adjusts the curriculum, or extends training.
"""
from __future__ import annotations
import hashlib

from .graph import canonical, digest, require
from . import adapter, candidate_run as cr, cube_node, trainer, verified_training as vtr

RESULT_SCHEMA = "cas-graph-training-candidate-result/1"
CONDITIONS = ("checked_component_teaching", "final_answer_only")
CHECKED = "checked_component_teaching"
CONTROL = "final_answer_only"
UPDATES_PER_CONDITION = 64
SEED = 20260909
ARM = "cas"


def question_groups(records, probe):
    """The three reported groups: taught whole-answer, taught component, probe."""
    whole_answer = [record for record in records
                    if record["cube_verified_teaching"]["task_profile"]
                    == "whole-answer/0.1"]
    component = [record for record in records
                 if record["cube_verified_teaching"]["task_profile"]
                 == "component-route/0.1"]
    require(len(whole_answer) == 3 and len(component) == 5,
            "CANDIDATE_QUESTION_GROUPS")
    return {"taught_whole_answer": whole_answer, "taught_component": component,
            "untaught_probe": list(probe)}


def condition_steps(records, condition):
    """The step list for one condition, from the declared schedules."""
    require(condition in CONDITIONS, "CANDIDATE_CONDITION_UNKNOWN:" + str(condition))
    if condition == CONTROL:
        return cr.control_steps(records)
    return cr.scheduled_steps(records, cr.proposed_schedule())


def evaluate(*, learner, records, arm=ARM, group):
    """One prediction per question, no update, scores retained or unavailable."""
    rows = []
    for record in records:
        task = adapter.public_records(record, arm)
        selected = learner.predict(task)
        rows.append({
            "record_id": record["record_id"],
            "operation": record["op"],
            "category": group,
            "correct": record["correct"],
            "selected": selected,
            "is_correct": canonical(selected) == canonical(record["correct"]),
            "scores_or_logits": _scores(learner, task),
            "assistance_state": "NONE",
        })
    correct = sum(1 for row in rows if row["is_correct"])
    by_operation = {}
    for row in rows:
        bucket = by_operation.setdefault(row["operation"], {"correct": 0, "total": 0})
        bucket["total"] += 1
        bucket["correct"] += 1 if row["is_correct"] else 0
    return {"category": group, "questions": len(rows), "correct": correct,
            "accuracy": (correct / len(rows)) if rows else None,
            "by_operation": by_operation, "rows": rows,
            "missing_measurement_rule": "unavailable, never zero"}


def _scores(learner, task):
    scorer = getattr(learner, "scores", None)
    if callable(scorer):
        value = scorer(task)
        return value if value is not None else "unavailable"
    return "unavailable"


def measure(*, learner, groups, arm=ARM):
    """All three groups in one measurement pass."""
    return {name: evaluate(learner=learner, records=records, arm=arm, group=name)
            for name, records in groups.items()}


def condition_report(*, condition, run, pre, post, probe_geometry):
    """Before and after, per group, with the primary measure named.

    Both per-operation breakdowns and both per-question row sets are kept. The
    first completed run (attempt 007) discarded them, so its delivered report
    could not say whether a set was already at a given score before training -
    and for this pilot that matters, because LIST_PARTS (4/5) dominated the
    9/44 probe total. Nothing is summarised away now.
    """
    def delta(name):
        before, after = pre[name], post[name]
        return {"before_correct": before["correct"], "before_total": before["questions"],
                "after_correct": after["correct"], "after_total": after["questions"],
                "before_accuracy": before["accuracy"], "after_accuracy": after["accuracy"],
                "delta_correct": after["correct"] - before["correct"],
                "by_operation_before": before["by_operation"],
                "by_operation_after": after["by_operation"],
                "items_before": before["rows"], "items_after": after["rows"]}

    return {
        "condition": condition,
        "steps": run["completed_steps"],
        "planned_steps": run["planned_steps"],
        "component_corrections": sum(
            1 for row in run["observations"] if row["phase"] == "component-route"),
        "whole_answer_corrections": sum(
            1 for row in run["observations"] if row["phase"] == "whole-answer"),
        "containment": run["containment"],
        "checkpoint": run["checkpoint"],
        "primary_measure": delta("taught_whole_answer"),
        "component_measure": delta("taught_component"),
        "probe_measure": delta("untaught_probe"),
        "predictions": run["observations"],
        "prediction_summary": run["observation_summary"],
        "probe_geometry": probe_geometry,
        "stopping_reason": run["stopping_reason"],
        "automatic_retries": 0,
        "independent_note": ("'independent' means no worked answer was supplied "
                            "during prediction; the taught questions have not "
                            "become unseen questions"),
    }


def launch(*, run_id, records, probe, groups, framework_factory, learner_factory,
           authorization, checkpoint_writer, checkpoint_verifier,
           scorer=None, wall_clock=None, view_id="view_context",
           ordering_mode="declared"):
    """Run both conditions in one call, matched from the same initial weights.

    Injected dependencies only: the caller supplies the framework factory, the
    learner factory, the checkpoint writer and verifier, and the authorization
    record. This function imports no torch and contacts no provider.
    """
    require(isinstance(authorization, dict) and authorization.get("owner_go") is True,
            "CANDIDATE_RUN_NOT_AUTHORIZED")
    require(authorization.get("run_id") == run_id, "CANDIDATE_RUN_ID_MISMATCH")
    probe_geometry = cr.probe_geometry(probe)
    results, snapshots = {}, {}
    for condition in CONDITIONS:
        # ``framework_factory(seed)`` returns (framework, model). Seeding is the
        # caller's job so both conditions start from identical initial weights;
        # the check below proves it rather than assuming it.
        framework, model = framework_factory(SEED)
        require(model is framework.module, "CANDIDATE_MODEL_FRAMEWORK_MISMATCH")
        snapshots[condition] = trainer.parameter_snapshot(framework, model)

        def factory(model, *, arm, records, layout, _fw=framework):
            return learner_factory(framework=_fw, model=model, arm=arm,
                                   records=records, layout=layout)

        def before(learner):
            return measure(learner=learner, groups=groups)

        def after(learner, result):
            return measure(learner=learner, groups=groups)

        run = cr.run_candidate(
            framework=framework, model=model, learner_factory=factory,
            authorization=authorization, view_id=view_id,
            ordering_mode=ordering_mode, arm=ARM,
            steps=condition_steps(records, condition), scorer=scorer,
            checkpoint_writer=checkpoint_writer,
            checkpoint_verifier=checkpoint_verifier, wall_clock=wall_clock,
            before_hook=before, after_hook=after)
        results[condition] = condition_report(
            condition=condition, run=run, pre=run["pre_measurement"],
            post=run["post_measurement"], probe_geometry=probe_geometry)
        results[condition]["learner_index_identity"] = digest(canonical(
            sorted(vtr.learner_index(records, ARM))))

    matched = snapshots[CHECKED] == snapshots[CONTROL]
    require(matched, "CANDIDATE_INITIAL_WEIGHTS_NOT_MATCHED")
    return {
        "schema": RESULT_SCHEMA,
        "run_id": run_id,
        "kind": cr.PROPOSED_SCHEDULE["kind"],
        "ordering_mode": ordering_mode,
        "arm": ARM,
        "seed": SEED,
        "updates_per_condition": UPDATES_PER_CONDITION,
        "conditions": list(CONDITIONS),
        "matched_initial_weights": matched,
        "initial_weight_digest": digest(canonical(sorted(snapshots[CHECKED].items()))),
        "records": len(records),
        "probe_questions": len(probe),
        "probe_geometry": probe_geometry,
        "results": results,
        "comparison": compare(results),
        "counters": {
            "actual_optimizer_updates": sum(r["steps"] for r in results.values()),
            "neural_presentations": sum(r["prediction_summary"]["recorded_predictions"]
                                        for r in results.values()),
            "seven_stage_neural_cycles": 0,
            "automatic_retries": 0,
        },
        "procedure_note": (
            "this pilot measures how to spend a fixed update budget: it does not "
            "isolate adding component instruction at equal final-question practice, "
            "because the control practises the final questions 64 times against 24"),
        "seven_stage_note": (
            "checked component teaching only; definition, analogy, correspondence "
            "and story presentations have no numerical delivery path here"),
    }


def compare(results):
    """Both conditions side by side, with the primary measure first."""
    def primary(condition):
        return results[condition]["primary_measure"]
    def probe(condition):
        return results[condition]["probe_measure"]
    return {
        "primary_measure": "independent accuracy on the three taught whole-answer "
                           "questions",
        "checked_component_teaching": primary(CHECKED),
        "final_answer_only": primary(CONTROL),
        "primary_delta_between_conditions":
            primary(CHECKED)["delta_correct"] - primary(CONTROL)["delta_correct"],
        "primary_set_size_warning": (
            "three taught whole-answer questions: one changed answer moves accuracy "
            "by 33.3 percentage points, so no single percentage carries the "
            "conclusion"),
        "component_measure": {"checked_component_teaching":
                              results[CHECKED]["component_measure"],
                              "final_answer_only":
                              results[CONTROL]["component_measure"],
                              "note": "reported separately from the complete question"},
        "probe": {"checked_component_teaching": probe(CHECKED),
                  "final_answer_only": probe(CONTROL),
                  "note": ("common untaught set, within-scene generalisation only, "
                           "never transfer to a new graph arrangement")},
        "assisted_versus_independent": (
            "independent figures are the ones above; assisted performance is never "
            "merged into them"),
    }


def checkpoint_identity(framework, model):
    """Digest of the current parameter bytes, for the checkpoint round trip."""
    return digest(canonical(sorted(trainer.parameter_snapshot(framework, model).items())))


def parameter_order(module):
    """The parameter names, in the order ``checkpoint_identity`` digests them.

    ``GraphLearner.checkpoint_identity`` hashes ``parameter.tobytes()`` for each
    ``(name, parameter)`` of ``module.named_parameters()`` — in that order, with
    the names themselves **not** included. The order is recorded explicitly
    because it is not recoverable from a loaded checkpoint: ``state_dict()``
    order is a different order once a module registers buffers, and it carries
    entries that are not parameters at all.
    """
    return [name for name, _ in module.named_parameters()]


def state_digest(state, order):
    """The learner's own identity rule, applied to a loaded ``state`` mapping.

    A checkpoint round trip must reproduce exactly this rule. Hashing the
    parameter *names* as well, or trusting the mapping's own order, produces a
    digest that can never equal the identity the learner reports, and the whole
    condition then fails closed on ``CANDIDATE_CHECKPOINT_NOT_VERIFIED`` — after
    its entire update budget has been spent.
    """
    require(order, "CANDIDATE_STATE_ORDER_REQUIRED")
    accumulator = hashlib.sha256()
    for name in order:
        require(name in state, "CANDIDATE_STATE_NAME_MISSING:" + str(name))
        accumulator.update(state[name].detach().cpu().numpy().tobytes())
    return accumulator.hexdigest()


def build_inputs(bundle=None, view_id="view_context", ordering_mode="declared"):
    """The frozen inputs: 8 taught records, the 44-question probe, and the groups."""
    if bundle is None:
        bundle = cube_node.load_bundle()
    records = vtr.training_records(bundle, view_id, ordering_mode)
    probe = cr.probe_records(bundle=bundle, records=records, view_id=view_id,
                             ordering_mode=ordering_mode)
    return {"records": records, "probe": probe,
            "groups": question_groups(records, probe)}
