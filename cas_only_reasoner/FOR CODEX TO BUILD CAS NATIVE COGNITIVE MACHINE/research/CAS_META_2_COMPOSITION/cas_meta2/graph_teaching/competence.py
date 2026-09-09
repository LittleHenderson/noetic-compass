"""One complete, correctly instrumented competence run (owner-directed).

A SINGLE targeted ^6 learner, cas framing only — first show that one
specialist can learn the relationship at all; the two-framing comparison is
postponed. ONE bounded job runs the whole fixed sequence; there is no
separate launch between stages:

  STAGE 1 (zero optimizer steps): relationship-preservation check (same-token
  rewiring vs connection-list reordering — input and module-output
  differences; declared tolerance: rewire > 10x reorder) and the
  forward/backward sanity (finite losses, nonzero gradients). Failure stops
  the job with the preserved numbers.
  STAGE 2: bounded training on the familiar (train+practice) examples with a
  learning curve (history every 8 steps) and the digest containment report.
  STAGE 3 (only if the registered fit criterion is met): sealed
  fresh-example evaluation with predictions recorded before answers, and the
  familiar-example accuracy, reported separately.

The deliverable is exactly one of the three registered outcomes
(LEARNED_AND_TRANSFERRED / LEARNED_NO_TRANSFER / DID_NOT_FIT), computed by a
deterministic rule from the recorded numbers — no prose judgement.
"""
from __future__ import annotations

from .graph import Graph, require

SCHEMA = "cas-graph-training-competence-result/1"
FIT_MARGIN = 0.02          # mean before-loss - mean after-loss must exceed this
TRANSFER_THRESHOLD = 6     # sealed combined correct of 12 (chance expectation 4)
HISTORY_EVERY = 8
REWIRE_TOLERANCE = 10.0    # rewire difference must exceed 10x the reorder baseline


def mean(values):
    return sum(values) / max(1, len(values))


def _loss_total(value):
    """Per-op losses are {"total": float} dicts in the real trainer; accept
    plain floats as well (test fakes)."""
    return value if isinstance(value, (int, float)) else value["total"]


def fit_criterion(before_loss, after_loss):
    margin = (mean([_loss_total(value) for value in before_loss.values()])
              - mean([_loss_total(value) for value in after_loss.values()]))
    return {"met": margin > FIT_MARGIN, "margin": margin,
            "threshold": FIT_MARGIN,
            "rule": "mean(after) < mean(before) - 0.02"}


def outcome(criterion_met, stage3_ran, sealed_total_correct):
    if not stage3_ran:
        return "DID_NOT_FIT"
    if sealed_total_correct >= TRANSFER_THRESHOLD:
        return "LEARNED_AND_TRANSFERRED"
    return "LEARNED_NO_TRANSFER"


def stage1_passes(relationship_check, sanity):
    """The registered stage-1 gate: the same-token rewiring must produce a
    distinguishable module INPUT beyond the reorder baseline (the owner's
    table — inputs, not outputs). Output differences are REPORTED without
    gating. The forward/backward sanity must show finite losses with nonzero
    gradients."""
    for row in relationship_check:
        reorder = row["connection_list_reorder"]["input_difference"]
        rewire = row["connector_rewire_same_tokens"]["input_difference"]
        if not rewire > REWIRE_TOLERANCE * max(reorder, 1e-9):
            return False
    return (all(float(loss) == float(loss) for loss in sanity["per_target_loss"])
            and max(sanity["per_target_max_gradient_norm"]) > 0.0)


def _partial_result(run_id, arm, stage1, outcome_label):
    return {"schema": SCHEMA, "run_id": run_id, "arm": arm,
            "stage1": stage1, "stage2": None, "fit_criterion": None,
            "stage3": None, "outcome": outcome_label,
            "claims": {"specialist_claimed": False,
                       "sealed_splits_read": False,
                       "answer_edges_present": False,
                       "two_arm_comparison_claimed": False}}


def _difference(torch, a, b):
    """Norm of a - b via norms and dot (no tensor subtraction needed)."""
    norm_a = float(torch.linalg.vector_norm(a).item())
    norm_b = float(torch.linalg.vector_norm(b).item())
    dot = float(torch.dot(a, b).item())
    return max(0.0, norm_a ** 2 + norm_b ** 2 - 2 * dot) ** 0.5


def launch(*, run_id, torch, framework, records, device, learning_rate,
           max_optimizer_steps, max_wall_seconds, seed=20260909,
           history_every=HISTORY_EVERY):
    require(type(run_id) is str and run_id, "RUN_ID_REQUIRED")
    require(framework is not None and torch is not None, "FRAMEWORK_REQUIRED")
    from . import adapter, diagnostic, lessons, trainer
    from .real_framework import GraphLearner

    arm = "cas"
    tasks = [adapter.public_records(record, arm) for record in records]
    learner = GraphLearner(torch, framework, tasks, device, learning_rate)

    # ---- STAGE 1a: relationship preservation (rewire vs reorder) ----------
    relationship_check = []
    for record in [row for row in records if row["op"] == "LIST_PARTS"][:2]:
        baseline_public = adapter.public_records(record, arm)["public"]
        baseline_vector = framework.encoder["encode_problem"](baseline_public)
        baseline_output = framework.module(baseline_vector.unsqueeze(0))[0]
        differences = {}
        for edit_kind, edited_graph in diagnostic._graph_edits(record):
            if edit_kind not in ("connector_rewire_same_tokens",
                                 "connection_list_reorder"):
                continue
            public = {
                "problem": lessons._render_prompt(
                    record["op"], Graph.from_record(edited_graph),
                    record["question"], arm)[:8192],
                "observations": baseline_public["observations"]}
            vector = framework.encoder["encode_problem"](public)
            output = framework.module(vector.unsqueeze(0))[0]
            differences[edit_kind] = {
                "input_difference": _difference(torch, baseline_vector, vector),
                "output_difference": _difference(torch, baseline_output, output)}
        relationship_check.append({"record_id": record["record_id"],
                                   **differences})

    # ---- STAGE 1b: forward/backward sanity (zero optimizer steps) ---------
    gradient_rows = diagnostic.measure_gradient_test(learner, 0)
    sanity = {"record_id": tasks[0]["record_id"],
              "per_target_loss": [row["loss"] for row in gradient_rows["results"]],
              "per_target_max_gradient_norm": [
                  max(row["gradient_norms"].values()) for row in gradient_rows["results"]]}
    stage1 = {"relationship_check": relationship_check,
              "forward_backward": sanity}
    if not stage1_passes(relationship_check, sanity):
        # Preserve the measured numbers and STOP — the owner's rule: failure
        # stops the job; nothing is trained on a representation that fails
        # the input-level distinguishability gate.
        return _partial_result(run_id, arm, stage1, "STAGE1_CHECK_FAILED")

    # ---- STAGE 2: bounded training on the familiar examples ---------------
    def learner_factory(model, arm=arm, learning_rate=learning_rate):
        return GraphLearner(torch, framework, tasks, device, learning_rate)

    training = trainer.launch(
        run_id=run_id + ".train", arm=arm, seed=seed, framework=framework,
        model=framework.module, learner_factory=learner_factory,
        learning_rate=learning_rate, max_optimizer_steps=max_optimizer_steps,
        max_wall_seconds=max_wall_seconds, history_every=history_every)

    # ---- familiar-example accuracy (training records themselves) ----------
    familiar = {"attempted": 0, "correct": 0, "predictions": []}
    for task in tasks:
        predicted = learner.predict(task)
        correct = task["encoded_options"][task["encoded_correct_index"]]
        familiar["attempted"] += 1
        familiar["correct"] += int(predicted == correct)
        familiar["predictions"].append({"record_id": task["record_id"],
                                        "op": task["op"], "predicted": predicted,
                                        "correct": correct})

    # ---- STAGE 3: fresh examples, only if the fit criterion is met --------
    criterion = fit_criterion(training["training"]["before_loss"],
                              training["training"]["after_loss"])
    if criterion["met"]:
        sealed = trainer.evaluate_sealed(learner, seed=seed, arm=arm)
        sealed_total_correct = sum(bucket["correct"]
                                   for bucket in sealed["per_split_op"].values())
        sealed_total_attempted = sum(bucket["attempted"]
                                     for bucket in sealed["per_split_op"].values())
        stage3 = {"ran": True, "sealed": sealed, "familiar": familiar,
                  "sealed_total_correct": sealed_total_correct,
                  "sealed_total_attempted": sealed_total_attempted}
    else:
        stage3 = {"ran": False, "skipped_reason": "FIT_CRITERION_NOT_MET",
                  "familiar": familiar, "sealed_total_correct": None,
                  "sealed_total_attempted": None}
        sealed_total_correct = 0

    result_outcome = outcome(criterion["met"], stage3["ran"], sealed_total_correct)
    return {"schema": SCHEMA, "run_id": run_id, "arm": arm,
            "stage1": stage1,
            "stage2": training,
            "fit_criterion": criterion,
            "stage3": stage3,
            "outcome": result_outcome,
            "claims": {"specialist_claimed": False,
                       "sealed_splits_read": False,
                       "answer_edges_present": False,
                       "two_arm_comparison_claimed": False}}
