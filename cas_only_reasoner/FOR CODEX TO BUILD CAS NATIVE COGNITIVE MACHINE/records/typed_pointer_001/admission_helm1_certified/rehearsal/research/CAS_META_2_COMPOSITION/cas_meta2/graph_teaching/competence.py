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
CONFIRMATION_SCHEMA = "cas-graph-training-confirmation-result/1"
FIT_MARGIN = 0.02          # mean before-loss - mean after-loss must exceed this
TRANSFER_THRESHOLD = 6     # sealed combined correct of 12 (chance expectation 4)
HISTORY_EVERY = 8
REWIRE_TOLERANCE = 10.0    # rewire difference must exceed 10x the reorder baseline

# Predeclared confirmation design (owner-recommended, frozen candidate):
# a small set of independent dataset/initialization seeds, evaluated on NEWLY
# GENERATED examples (fresh dataset seed => fresh sealed panel, excluding the
# previously examined attempt-010 panel).
CONFIRM_SEEDS = (20260910, 20260911, 20260912)
CONFIRM_MIN_SEEDS_FIT = 2        # at least 2 of 3 must meet the fit criterion
CONFIRM_MIN_SEEDS_TRANSFER = 2   # at least 2 of 3 must reach the transfer threshold
# The registered transfer bar is ABSOLUTE (6 correct of 12) and stays the
# primary rule. The frozen lesson generator produces a seed-dependent sealed
# panel size, so the panel-normalized reading — at least half of that seed's
# panel, never below the registered 6 — is ALSO reported for every seed. It is
# a reported number, not a silent reinterpretation: the primary verdict uses
# the registered absolute rule unless the owner authorizes the normalized
# reading before launch.


def panel_normalized_threshold(attempted):
    """Conservative comparable bar: at least half of that seed's sealed panel,
    never below the registered absolute threshold."""
    require(type(attempted) is int and attempted > 0, "PANEL_SIZE_REQUIRED")
    return max(TRANSFER_THRESHOLD, -(-attempted // 2))


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


def _partial_result(run_id, arm, stage1, outcome_label, seed=None):
    return {"schema": SCHEMA, "run_id": run_id, "arm": arm, "seed": seed,
            "stage1": stage1, "stage2": None, "fit_criterion": None,
            "stage3": None, "outcome": outcome_label,
            "claims": {"specialist_claimed": False,
                       "sealed_splits_read": False,
                       "answer_edges_present": False,
                       "two_arm_comparison_claimed": False}}


def _sealed_row(run):
    stage3 = run.get("stage3") or {}
    correct = stage3.get("sealed_total_correct")
    attempted = stage3.get("sealed_total_attempted")
    ran = bool(stage3.get("ran"))
    normalized_bar = (panel_normalized_threshold(attempted)
                      if ran and isinstance(attempted, int) and attempted > 0 else None)
    return {"seed": run["seed"], "outcome": run["outcome"],
            "margin": (run["fit_criterion"] or {}).get("margin"),
            "fit_met": bool((run.get("fit_criterion") or {}).get("met")),
            "sealed_total_correct": correct,
            "sealed_total_attempted": attempted,
            "sealed_ran": ran,
            "registered_threshold": TRANSFER_THRESHOLD,
            "registered_met": bool(ran and (correct or 0) >= TRANSFER_THRESHOLD),
            "panel_normalized_threshold": normalized_bar,
            "panel_normalized_met": bool(ran and normalized_bar is not None
                                         and (correct or 0) >= normalized_bar),
            "chance_expectation": (attempted / 3.0 if isinstance(attempted, int)
                                   and attempted > 0 else None),
            "familiar_correct": (stage3.get("familiar") or {}).get("correct"),
            "familiar_attempted": (stage3.get("familiar") or {}).get("attempted")}


def confirmation_outcome(runs):
    """The registered repeat rule for the confirmation experiment: computed
    deterministically from the per-seed runs. REPLICATED requires at least
    CONFIRM_MIN_SEEDS_FIT seeds meeting the fit criterion AND at least
    CONFIRM_MIN_SEEDS_TRANSFER seeds reaching the sealed transfer threshold
    on the NEWLY generated panel; anything else is NOT_REPLICATED (reported
    with the per-seed numbers).

    Two readings of the transfer bar are reported because the frozen lesson
    generator yields a seed-dependent panel size (observed 11, 11 and 13 for
    the three predeclared seeds versus 12 for the previously examined panel):
    the REGISTERED absolute rule (>= 6) — which decides the primary verdict —
    and the conservative panel-normalized reading (>= half of that seed's
    panel, never below 6). The primary verdict uses the registered rule.
    """
    rows = [_sealed_row(run) for run in runs]
    fit = sum(1 for row in rows if row["fit_met"])
    transferred = sum(1 for row in rows if row["registered_met"])
    transferred_normalized = sum(1 for row in rows if row["panel_normalized_met"])
    replicated = (fit >= CONFIRM_MIN_SEEDS_FIT
                  and transferred >= CONFIRM_MIN_SEEDS_TRANSFER)
    replicated_normalized = (fit >= CONFIRM_MIN_SEEDS_FIT
                             and transferred_normalized >= CONFIRM_MIN_SEEDS_TRANSFER)
    return {"schema": "cas-graph-training-confirmation-outcome/1",
            "seeds": [run["seed"] for run in runs],
            "runs": len(runs),
            "fit_seeds": fit, "transfer_seeds": transferred,
            "transfer_seeds_panel_normalized": transferred_normalized,
            "required_fit_seeds": CONFIRM_MIN_SEEDS_FIT,
            "required_transfer_seeds": CONFIRM_MIN_SEEDS_TRANSFER,
            "transfer_threshold": TRANSFER_THRESHOLD,
            "transfer_rule": "registered absolute: sealed correct >= 6",
            "secondary_rule": ("panel-normalized reading (reported only): "
                               "sealed correct >= max(6, ceil(attempted/2))"),
            "outcome": "REPLICATED" if replicated else "NOT_REPLICATED",
            "outcome_panel_normalized": ("REPLICATED" if replicated_normalized
                                         else "NOT_REPLICATED"),
            "per_seed": rows}


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
        return _partial_result(run_id, arm, stage1, "STAGE1_CHECK_FAILED", seed=seed)

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
    return {"schema": SCHEMA, "run_id": run_id, "arm": arm, "seed": seed,
            "stage1": stage1,
            "stage2": training,
            "fit_criterion": criterion,
            "stage3": stage3,
            "outcome": result_outcome,
            "claims": {"specialist_claimed": False,
                       "sealed_splits_read": False,
                       "answer_edges_present": False,
                       "two_arm_comparison_claimed": False}}
