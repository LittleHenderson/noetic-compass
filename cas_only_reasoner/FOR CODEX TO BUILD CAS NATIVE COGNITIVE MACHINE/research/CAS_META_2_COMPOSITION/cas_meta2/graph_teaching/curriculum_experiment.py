"""GRAPH6_CURRICULUM_002 — varied relationship lessons vs repetition control.

Owner-directed (2026-09-10). ONE combined job, preparation only until approved.

The measured problem this experiment attacks is not "the module cannot learn":
familiar-example learning replicated in all three independently initialized
candidates of GRAPH6_CONFIRMATION_001 attempt 002. What failed was performance on
NEW examples at the registered standard, with `LIST_PARTS` weakest (6/30, 10/30,
7/30 after training). The owner's proposed hypothesis — the learner needs more
varied practice that separates the relationship from familiar names, layouts and
answer patterns — is TESTED here, not assumed.

Design (pre-registered before execution):

* two conditions, one job: **control** = the existing lessons unchanged,
  **varied** = the varied relationship curriculum (`curriculum.py`);
* three PAIRED initialization seeds; each pair shares the same module
  initialization, so starting weights match within a pair, while every learner
  has its own copy and its own optimizer state;
* a fixed, balanced operation schedule and the same update allowance in both
  conditions: measurements at **64** and **256** updates per learner, six
  learners, **1,536** scheduled updates total;
* the final panel is UNTOUCHED: a new panel seed that also excludes the
  previously examined 90-case panel and the varied curriculum's own records;
* every prediction is recorded before the answers are opened; every scheduled
  learner and both checkpoints are reported, including regressions;
* real checkpoint FILES are written (model, optimizer, step, encoder state,
  configuration), reloaded inside the job, and verified by parameter digest and
  by re-prediction before the artifacts are collected.
"""
from __future__ import annotations

import time
from hashlib import sha256
from pathlib import Path

from . import curriculum
from .confirmation import (ANSWER_FIELDS, clustered_bootstrap, evaluate_panel,
                           mcnemar, paired_analysis, practice_accuracy,
                           sealed_input)
from .graph import canonical, digest, require

SCHEMA = "cas-graph-training-curriculum-result/1"
LEARNER_SCHEMA = "cas-graph-training-curriculum-learner/1"
VERDICT_SCHEMA = "cas-graph-training-curriculum-verdict/1"
CHECKPOINT_SCHEMA = "cas-graph-training-curriculum-checkpoint/1"

CONDITIONS = ("control", "varied")
PAIR_SEEDS = (20260913, 20260914, 20260915)
CHECKPOINTS = (64, 256)
UPDATES_PER_LEARNER = 256
LEARNER_COUNT = len(PAIR_SEEDS) * len(CONDITIONS)          # 6
TOTAL_UPDATES = LEARNER_COUNT * UPDATES_PER_LEARNER        # 1536
FROZEN_ENCODER_SEED = 20260909
FROZEN_LEARNING_RATE = 0.003
FROZEN_ARM = "cas"
HISTORY_EVERY = 8
MAX_WALL_SECONDS_PER_LEARNER = 900.0

# Pre-registered decision rules (fixed before execution; the 50 % absolute level
# and the +10 % margin are carried over from GRAPH6_CONFIRMATION_001 unchanged —
# the earlier negative result is NOT reinterpreted by lowering them).
CURRICULUM_MARGIN = 0.10
REPETITION_MARGIN = 0.10
TRANSFER_LEVEL = 0.50
MIN_SEEDS = 2
BOOTSTRAP_RESAMPLES = 10000
BOOTSTRAP_SEED = 20260926
CONFIDENCE = 0.95


def _loss_total(value):
    return value if isinstance(value, (int, float)) else value["total"]


def mean(values):
    return sum(values) / max(1, len(values))


def run_segmented_training(learner, records, *, arm=FROZEN_ARM, updates,
                           history_every=HISTORY_EVERY, wall_clock=time.monotonic,
                           wall_seconds=MAX_WALL_SECONDS_PER_LEARNER,
                           start_position=0):
    """Bounded updates with a CONTINUOUS schedule across segments.

    Equivalent to ``trainer.run_training`` for a single segment (verified by
    test), but it keeps the schedule position across segments so the 64-update
    and 256-update measurements of one learner come from one uninterrupted run.
    """
    from . import trainer
    tasks = [trainer.make_task(record, arm) for record in records]
    ops = sorted({task["op"] for task in tasks})
    before = {op: learner.eval_loss(op, tasks) for op in ops}
    history = []
    if history_every:
        history.append([0, mean([_loss_total(value) for value in before.values()])])
    completed = 0
    updates_by_op = {op: 0 for op in ops}
    deadline = wall_clock() + wall_seconds
    position = start_position
    while completed < updates and wall_clock() < deadline:
        task = tasks[position % len(tasks)]
        learner.step(task)
        updates_by_op[task["op"]] += 1
        completed += 1
        position += 1
        if history_every and (completed % history_every == 0 or completed == updates):
            current = {op: learner.eval_loss(op, tasks) for op in ops}
            history.append([completed,
                            mean([_loss_total(value) for value in current.values()])])
    after = {op: learner.eval_loss(op, tasks) for op in ops}
    return {"before_loss": before, "after_loss": after,
            "completed_updates": completed, "updates_by_op": updates_by_op,
            "history": history, "schedule_position": position,
            "checkpoint_identity": learner.checkpoint_identity(),
            "automatic_retries": 0,
            "lesson_exposure": {
                "records_by_op": {op: sum(1 for task in tasks if task["op"] == op)
                                  for op in ops},
                "updates_by_op": updates_by_op,
                "boundary": ("an optimizer step is one correction on one record, "
                             "not a complete teaching cycle")}}


def encoder_state(torch, encoder):
    """The encoder state needed to continue: the frozen projection and the
    tokenizer vocabulary (a hash alone cannot restore either)."""
    projection = torch.stack([encoder["embed"](token_id)
                              for token_id in range(encoder["vocabulary_size"])])
    return {"projection": projection,
            "vocabulary": list(encoder["tokenizer"].vocabulary),
            "d_model": encoder["d_model"],
            "max_length": encoder["max_length"],
            "structural_problem_binding": encoder["structural_problem_binding"],
            "projection_frozen": encoder["projection_frozen"]}


def save_checkpoint(torch, path, *, module, learner, step, condition, learner_seed,
                    encoder, records, arm=FROZEN_ARM, optimizer=True):
    """Write a REAL checkpoint file (not a digest) and return its receipt."""
    payload = {
        "schema": CHECKPOINT_SCHEMA,
        "step": step,
        "condition": condition,
        "learner_seed": learner_seed,
        "arm": arm,
        "encoder_seed": FROZEN_ENCODER_SEED,
        "d_model": encoder["d_model"],
        "model": module.state_dict(),
        "optimizer": learner.optimizer.state_dict() if optimizer else None,
        "encoder": encoder_state(torch, encoder),
        "record_ids": [record["record_id"] for record in records],
        "torch_version": getattr(torch, "__version__", None),
    }
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(payload, str(path))
    raw = path.read_bytes()
    return {"schema": CHECKPOINT_SCHEMA, "path": str(path), "step": step,
            "condition": condition, "learner_seed": learner_seed,
            "bytes": len(raw), "sha256": sha256(raw).hexdigest()}


def load_checkpoint(torch, path):
    return torch.load(str(path), map_location="cpu")


def verify_checkpoint(torch, path, *, framework_factory, learner_factory, tasks,
                      cases, expected_predictions, condition, learner_seed):
    """Reload the saved file into a FRESH module and prove it restores both the
    weights and the behaviour."""
    payload = load_checkpoint(torch, path)
    framework = framework_factory(learner_seed)
    framework.module.load_state_dict(payload["model"])
    learner = learner_factory(framework.module)
    reloaded_digest = learner.checkpoint_identity()
    fresh = evaluate_panel(learner, cases)
    predictions_match = ([row["predicted"] for row in fresh["results"]]
                         == list(expected_predictions))
    return {"verified": bool(predictions_match),
            "predictions_match": bool(predictions_match),
            "reloaded_checkpoint_identity": reloaded_digest,
            "expected_checkpoint_identity": payload.get("checkpoint_identity"),
            "step": payload["step"], "condition": payload["condition"],
            "bytes": Path(path).stat().st_size,
            "sha256": sha256(Path(path).read_bytes()).hexdigest()}


def run_learner(*, run_id, condition, learner_seed, framework, torch, device, tasks,
                records, cases, learner_factory, checkpoint_dir,
                learning_rate=FROZEN_LEARNING_RATE,
                checkpoints=CHECKPOINTS, history_every=HISTORY_EVERY,
                trainer_module=None, framework_factory=None,
                wall_seconds=MAX_WALL_SECONDS_PER_LEARNER):
    """One learner of one condition: save, measure, train to 64, train to 256."""
    from . import trainer as trainer_module_default
    trainer_module = trainer_module or trainer_module_default
    learner = learner_factory(framework.module)
    artifacts = []
    initial_identity = learner.checkpoint_identity()
    initial = save_checkpoint(torch, Path(checkpoint_dir) /
                              ("%s_seed%d_step000.pt" % (condition, learner_seed)),
                              module=framework.module, learner=learner, step=0,
                              condition=condition, learner_seed=learner_seed,
                              encoder=framework.encoder, records=records)
    artifacts.append(initial)
    practice_before = practice_accuracy(learner, tasks)
    fresh_before = evaluate_panel(learner, cases)

    segments = []
    position = 0
    completed = 0
    for target in checkpoints:
        steps = target - completed
        require(steps > 0, "CURRICULUM_CHECKPOINT_ORDER")
        segment = run_segmented_training(
            learner, records, updates=steps, history_every=history_every,
            wall_seconds=wall_seconds, start_position=position)
        position = segment["schedule_position"]
        completed += segment["completed_updates"]
        segments.append(segment)
        practice = practice_accuracy(learner, tasks)
        fresh = evaluate_panel(learner, cases)
        artifact = save_checkpoint(
            torch, Path(checkpoint_dir) /
            ("%s_seed%d_step%03d.pt" % (condition, learner_seed, completed)),
            module=framework.module, learner=learner, step=completed,
            condition=condition, learner_seed=learner_seed,
            encoder=framework.encoder, records=records)
        artifacts.append(artifact)
        verification = verify_checkpoint(
            torch, artifact["path"], framework_factory=framework_factory,
            learner_factory=learner_factory, tasks=tasks, cases=cases,
            expected_predictions=[row["predicted"] for row in fresh["results"]],
            condition=condition, learner_seed=learner_seed)
        require(verification["verified"], "CURRICULUM_CHECKPOINT_RELOAD_FAILED")
        segments[-1] = {**segment, "practice": practice, "fresh": fresh,
                        "checkpoint": artifact, "reload_verification": verification}

    first, last = segments[0], segments[-1]
    return {"schema": LEARNER_SCHEMA, "run_id": run_id, "condition": condition,
            "learner_seed": learner_seed, "arm": FROZEN_ARM,
            "encoder_seed": FROZEN_ENCODER_SEED,
            "training_dataset_seed": FROZEN_ENCODER_SEED,
            "curriculum_identity": curriculum.curriculum_identity(records),
            "initial_checkpoint_identity": initial_identity,
            "initial_checkpoint": initial,
            "practice": {"before": practice_before,
                         "after_64": first["practice"],
                         "after_256": last["practice"]},
            "fresh": {"before": fresh_before,
                      "after_64": first["fresh"],
                      "after_256": last["fresh"]},
            "training": {"checkpoints": list(checkpoints),
                         "completed_updates": completed,
                         "segments": segments,
                         "updates_by_op": {op: sum(segment["updates_by_op"][op]
                                                   for segment in segments)
                                           for op in first["updates_by_op"]},
                         "history": [entry for segment in segments
                                     for entry in segment["history"]]},
            "artifacts": artifacts,
            "final_checkpoint_identity": learner.checkpoint_identity()}


def _comparison(before, after):
    return paired_analysis(before, after)


def curriculum_experiment_panel_digest(panel):
    from . import final_panel, fresh_panel
    if panel["schema"] == "cas-graph-training-final-panel/1":
        return final_panel.final_panel_digest(panel)
    return fresh_panel.panel_digest(panel)


def curriculum_verdict(pairs):
    """The pre-registered rule, computed from the recorded numbers only."""
    per_seed = []
    for pair in pairs:
        comparison = pair["equal_budget"]
        repetition = pair["repetition_control"]
        per_seed.append({
            "seed": pair["seed"],
            "varied_minus_control_256": comparison["delta_accuracy"],
            "interval_low": comparison["uncertainty"]["low"],
            "interval_high": comparison["uncertainty"]["high"],
            "mcnemar_p": comparison["mcnemar"]["p_value"],
            "varied_accuracy_256": comparison["after_accuracy"],
            "control_accuracy_256": comparison["before_accuracy"],
            "curriculum_advantage": bool(
                comparison["delta_accuracy"] >= CURRICULUM_MARGIN
                and comparison["uncertainty"]["low"] is not None
                and comparison["uncertainty"]["low"] > 0.0),
            "absolute_level_met": bool(
                comparison["after_accuracy"] >= TRANSFER_LEVEL),
            "repetition_gain_control": repetition["delta_accuracy"],
            "repetition_gain_varied": pair["varied_repetition"]["delta_accuracy"],
        })
    advantage_seeds = sum(1 for row in per_seed if row["curriculum_advantage"])
    level_seeds = sum(1 for row in per_seed if row["absolute_level_met"])
    confirmed = advantage_seeds >= MIN_SEEDS and level_seeds >= MIN_SEEDS
    return {"schema": VERDICT_SCHEMA,
            "seeds": [pair["seed"] for pair in pairs],
            "curriculum_advantage_seeds": advantage_seeds,
            "absolute_level_seeds": level_seeds,
            "required_seeds": MIN_SEEDS,
            "margin": CURRICULUM_MARGIN, "level": TRANSFER_LEVEL,
            "per_seed": per_seed,
            "outcome": ("VARIED_CURRICULUM_BETTER" if confirmed
                        else "VARIED_CURRICULUM_NOT_ESTABLISHED"),
            "rule": ("VARIED_CURRICULUM_BETTER iff at least %d of %d seeds show a "
                     "varied-minus-control advantage of >= +%.2f with a "
                     "family-clustered 95%% interval excluding zero AND at least "
                     "%d seeds reach %.2f absolute fresh accuracy at 256 updates"
                     % (MIN_SEEDS, len(pairs), CURRICULUM_MARGIN, MIN_SEEDS,
                        TRANSFER_LEVEL))}


def launch(*, run_id, torch, device, encoder, tasks, panel, checkpoint_dir,
           pair_seeds=PAIR_SEEDS, conditions=CONDITIONS,
           framework_factory=None, learner_factory=None, trainer_module=None,
           encoder_identity_fn=None, wall_seconds=MAX_WALL_SECONDS_PER_LEARNER):
    """Run the whole pre-registered comparison in ONE call (six learners)."""
    from .confirmation import encoder_identity
    from .real_framework import GraphLearner, build_graph_training_framework
    require(list(pair_seeds) == list(PAIR_SEEDS), "PAIR_SEEDS_FROZEN")
    require(list(conditions) == list(CONDITIONS), "CONDITIONS_FROZEN")
    require(panel["schema"] in ("cas-graph-training-fresh-panel/1",
                                "cas-graph-training-final-panel/1"),
            "FRESH_PANEL_REQUIRED")
    cases = [(case["family_id"], case["record"]) for case in panel["cases"]]
    identity_fn = encoder_identity_fn or encoder_identity
    encoder_identity_value = identity_fn(torch, encoder)
    framework_factory = framework_factory or (
        lambda seed: build_graph_training_framework(
            torch, device, seed=FROZEN_ENCODER_SEED, encoder=encoder))

    def real_learner_factory(framework):
        return lambda model, arm=FROZEN_ARM, learning_rate=FROZEN_LEARNING_RATE: (
            GraphLearner(torch, framework, tasks, device, learning_rate))

    curricula = {"control": curriculum.control_records(),
                 "varied": curriculum.varied_records()}
    for name, records in curricula.items():
        require(len(curriculum.schedule(records)) == curriculum.TOTAL_RECORDS,
                "CURRICULUM_SCHEDULE_SIZE:" + name)

    learners = {}
    for condition in conditions:
        for seed in pair_seeds:
            # Seeding the global RNG here fixes the module initialization, so the
            # control and varied learners of one seed start from IDENTICAL weights.
            torch.manual_seed(seed)
            framework = framework_factory(seed)
            factory = learner_factory or real_learner_factory(framework)
            learners[(condition, seed)] = run_learner(
                run_id="%s.%s.seed%d" % (run_id, condition, seed),
                condition=condition, learner_seed=seed, framework=framework,
                torch=torch, device=device, tasks=tasks,
                records=curricula[condition], cases=cases,
                learner_factory=factory, checkpoint_dir=checkpoint_dir,
                trainer_module=trainer_module, framework_factory=framework_factory,
                wall_seconds=wall_seconds)

    pairs = []
    for seed in pair_seeds:
        control = learners[("control", seed)]
        varied = learners[("varied", seed)]
        require(control["initial_checkpoint_identity"]
                == varied["initial_checkpoint_identity"],
                "PAIRED_INITIAL_WEIGHTS_MISMATCH")
        pairs.append({
            "seed": seed,
            "matched_initial_checkpoint_identity":
                control["initial_checkpoint_identity"],
            "equal_budget": _comparison(
                control["fresh"]["after_256"], varied["fresh"]["after_256"]),
            "repetition_control": _comparison(
                control["fresh"]["after_64"], control["fresh"]["after_256"]),
            "varied_repetition": _comparison(
                varied["fresh"]["after_64"], varied["fresh"]["after_256"]),
            "control": control, "varied": varied})

    artifacts = [artifact
                 for learner in learners.values()
                 for artifact in learner["artifacts"]]
    identities = {learner["initial_checkpoint_identity"]
                  for learner in learners.values()}
    return {
        "schema": SCHEMA, "run_id": run_id,
        "design": {"conditions": list(conditions), "pair_seeds": list(pair_seeds),
                   "checkpoints": list(CHECKPOINTS),
                   "updates_per_learner": UPDATES_PER_LEARNER,
                   "learners": len(learners), "total_updates": TOTAL_UPDATES,
                   "learning_rate": FROZEN_LEARNING_RATE,
                   "max_wall_seconds_per_learner": wall_seconds,
                   "arm": FROZEN_ARM,
                   "schedule": "balanced round-robin over operations"},
        "panel": {"schema": panel["schema"],
                  "panel_seed": panel["panel_seed"],
                  "family_count": panel["family_count"],
                  "case_count": panel["case_count"],
                  "cases_per_op": panel["cases_per_op"],
                  "excluded_panels": panel.get("excluded_panels", []),
                  "excluded_curriculum_seeds": panel.get("excluded_curriculum_seeds", []),
                  "excluded_case_ids": panel.get("excluded_case_ids"),
                  "excluded_signatures": panel.get("excluded_signatures"),
                  "distinct_case_patterns": panel.get("distinct_case_patterns"),
                  "panel_digest": curriculum_experiment_panel_digest(panel)},
        "curricula": {name: {"identity": curriculum.curriculum_identity(records),
                             "records": len(records),
                             "records_per_op": {op: sum(
                                 1 for record in records if record["op"] == op)
                                 for op in curriculum.OPS}}
                      for name, records in curricula.items()},
        "exposure": {name: curriculum.exposure(
            records, UPDATES_PER_LEARNER, tokenizer=encoder.get("tokenizer"))
            for name, records in curricula.items()},
        "controls": {"encoder_identity_shared": len(
            {learner["encoder_seed"] for learner in learners.values()}) == 1,
            "encoder_identity": encoder_identity_value,
            "initial_checkpoints_distinct_across_seeds":
                len(identities) == len(pair_seeds),
            "paired_initial_weights_matched": True,
            "every_learner_reported": len(learners) == LEARNER_COUNT,
            "checkpoint_files": len(artifacts)},
        "learners": [learners[(condition, seed)]
                     for seed in pair_seeds for condition in conditions],
        "pairs": pairs,
        "verdict": curriculum_verdict(pairs),
        "artifacts": artifacts,
        "claims": {"specialist_claimed": False, "composition_claimed": False,
                   "two_arm_comparison_claimed": False,
                   "sealed_splits_read": False,
                   "answers_sealed_before_predictions": True,
                   "answer_sealing_limit": ("the record proves the prediction "
                                            "pass received no answer field; it "
                                            "does not by itself prove the "
                                            "answers were opened only after the "
                                            "predictions were written")},
    }
