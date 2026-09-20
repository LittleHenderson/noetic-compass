"""The four-condition face-grounding pilot: teaching, batching, evaluation, envelope.

One candidate learning path, injected dependencies, no torch import here. What this
module adds over the checked-component pilot, and why each addition exists:

* **batching** - the plan's update counts presuppose minibatches of 8 independent
  query episodes. ``batch_step`` performs exactly **one** optimizer step per batch
  and returns the per-episode scores and losses of the *forward computation it
  actually used*, so the recorded scores come from the correction's own pass, not
  from a later call that merely shares an argmax;
* **per-episode rows, always kept** - expected and selected answers, both
  categories, the three scores, the loss, the delivered slot order, the batch
  index and the optimizer-update index. Attempt 007's report discarded exactly
  these, and its paired comparison could not be reconstructed afterwards;
* **four conditions from the two plans** - the loop with stable cues, the loop
  with one neutral cue, the same events in mixed order with stable cues, and the
  mixed-order neutral control - matched by construction: identical events,
  identical starting weights, identical schedule lengths, separate optimizer
  states and checkpoints;
* **explicit incompleteness** - if the stopping limit is reached before the
  planned exposure, the run reports ``TEACHING_INCOMPLETE`` with the counts it
  reached, and never presents a partial allocation as the declared schedule.
"""
from __future__ import annotations

import time
from collections import OrderedDict

from .graph import canonical, digest, require
from . import face_corpus as corpus
from . import face_evaluation as evaluation
from . import face_roles as roles
from . import face_schedule as schedule
from . import face_tasks as tasks
from . import trainer

SCHEMA = "cas.cube-face-experiment/0.1"
RESULT_SCHEMA = "cas.cube-face-result/1"

STATUS_COMPLETE = "TEACHING_COMPLETE"
STATUS_INCOMPLETE = "TEACHING_INCOMPLETE"


# --------------------------------------------------------------------------
# episode compilation from scheduled events
# --------------------------------------------------------------------------

def compile_event(event, built=None):
    """Compile one scheduled event into a public record and a private target."""
    built = corpus.families() if built is None else built
    families = corpus.family_index(built)
    family = families[event["family_id"]]
    supports = [families[family_id] for family_id in (event.get("support_ids") or ())]
    episode = tasks.compile_episode(
        family, event["face"], event["profile"],
        arm=event.get("arm", "stable"),
        supports=supports,
        offset=event.get("offset", 0),
        group=event.get("group"),
        built=built)
    episode["event"] = dict(event)
    return episode


def compile_events(events, built=None, limit=None):
    """Compile a condition's events lazily, in order, optionally truncated."""
    chosen = events if limit is None else events[:limit]
    return [compile_event(event, built=built) for event in chosen]


def episode_task(episode, arm="cas"):
    """The training-shaped task the learner consumes, from the public record."""
    return {"record_id": episode["public_record"]["record_id"],
            "op": episode["public_record"]["op"],
            "task_profile": episode["public_record"]["task_profile"],
            "face_role": episode["public_record"]["face_role"],
            "family_id": episode["public_record"]["family_id"],
            "public": episode["public"],
            "encoded_options": episode["encoded_options"],
            "encoded_correct_index": episode["encoded_correct_index"],
            "correct": episode["public_record"]["correct"],
            "arm": arm}


# --------------------------------------------------------------------------
# the bounded batching path
# --------------------------------------------------------------------------

def batch_step(learner, tasks_in_batch):
    """One optimizer step for a batch of independent query episodes.

    The loss is the mean of the episodes' cross-entropies, so a batch of eight is
    **one** update, not eight. The per-episode scores and losses returned here are
    the ones this pass computed and back-propagated - the recording path never
    takes an independent later forward call.

    It reaches the candidate learner's own ``forward`` and ``optimizer`` and adds
    no head, no parameter and no readout: the same three-choice scoring the
    accepted path uses.
    """
    torch = learner.torch
    require(tasks_in_batch, "FACE_BATCH_EMPTY")
    losses, scores_by_episode = [], []
    learner.optimizer.zero_grad(set_to_none=True)
    for task in tasks_in_batch:
        position = learner._position(task)
        scores = learner.forward(position)
        correct = learner.tasks[position]["encoded_correct_index"]
        loss = torch.nn.functional.cross_entropy(
            scores.unsqueeze(0),
            torch.tensor([correct], device=learner.device))
        losses.append(loss)
        scores_by_episode.append({
            "scores": [round(float(value.detach()), 6) for value in scores],
            "loss": float(loss.detach()),
            "correct_index": int(correct),
            "selected_index": int(torch.argmax(scores).item()),
            "selected": task["encoded_options"][int(torch.argmax(scores).item())],
            "option_count": int(scores.shape[0])})
    total = sum(losses) / len(losses)
    total.backward()
    learner.optimizer.step()
    return {"batch_size": len(tasks_in_batch), "optimizer_steps": 1,
            "mean_loss": float(total.detach()), "episodes": scores_by_episode}


def _batches(items, size):
    for start in range(0, len(items), size):
        yield items[start:start + size]


# --------------------------------------------------------------------------
# running one condition
# --------------------------------------------------------------------------

def run_condition(*, run_id, episodes, framework, model, learner_factory,
                  checkpoint_writer, checkpoint_verifier,
                  batch_size=schedule.BATCH_SIZE, wall_clock=None,
                  max_wall_seconds=None, observer=None, learner=None):
    """Teach one condition: batched updates, per-episode rows, verified checkpoint.

    The episodes are compiled once by the caller, so the learner can be indexed
    over exactly the condition's own teaching set and the panel's cue-free items
    then travel the on-demand path. The learner may be supplied, so the caller can
    measure the panel *before* any update on the very same learner and framework;
    re-building one afterwards would measure a trained framework and report it as
    the starting point.
    """
    require(model is framework.module, "FACE_MODEL_FRAMEWORK_MISMATCH")
    clock = wall_clock or time.monotonic
    deadline = clock() + (max_wall_seconds or float("inf"))
    if learner is None:
        learner = learner_factory(framework=framework, model=model, tasks=[
            episode_task(episode) for episode in episodes])
    scope = trainer.scope_parameters(framework, model)
    before = trainer.parameter_snapshot(framework, model)
    rows, batch_index, update_index = [], 0, 0
    stopped_on_limit = False
    for batch in _batches(episodes, batch_size):
        if clock() >= deadline:
            stopped_on_limit = True
            break
        identity_before = learner.checkpoint_identity()
        outcome = batch_step(learner, [episode_task(episode) for episode in batch])
        update_index += outcome["optimizer_steps"]
        identity_after = learner.checkpoint_identity()
        for episode, scored in zip(batch, outcome["episodes"]):
            row = _row(episode, scored, batch_index=batch_index,
                       update_index=update_index,
                       identity_before=identity_before,
                       identity_after=identity_after)
            rows.append(row)
            if observer is not None:
                observer(row)
        batch_index += 1
    after = trainer.parameter_snapshot(framework, model)
    containment = trainer.containment_report(before, after, scope["allowed"])
    require(containment["contained"], "FACE_CONTAINMENT_VIOLATION")
    identity = learner.checkpoint_identity()
    saved = checkpoint_writer(learner, identity)
    verified = bool(checkpoint_verifier(saved, identity))
    require(verified, "FACE_CHECKPOINT_NOT_VERIFIED")
    planned = len(episodes)
    delivered = len(rows)
    return {
        "run_id": run_id, "planned_episodes": planned,
        "delivered_episodes": delivered,
        "planned_updates": planned // batch_size,
        "actual_optimizer_updates": update_index,
        "batches": batch_index, "batch_size": batch_size,
        "status": (STATUS_INCOMPLETE if (stopped_on_limit or delivered < planned)
                   else STATUS_COMPLETE),
        "stopping_reason": ("stopping limit reached with the remainder untaught"
                            if stopped_on_limit else
                            ("complete" if delivered == planned
                             else "fewer episodes than planned")),
        "scope_allowed": sorted(scope["allowed"]),
        "containment": containment,
        "checkpoint": {"identity": identity, "saved": saved, "verified": verified},
        "rows": rows,
        "scores_recorded_from_the_correction_pass": True,
        "automatic_retries": 0,
    }


def _row(episode, scored, *, batch_index, update_index, identity_before,
         identity_after):
    target = episode["teacher_target"]
    expected = target["correct"]
    selected = scored["selected"]
    return {
        "item_kind": "teaching",
        "task_profile": target["profile"],
        "face": target["face"],
        "family_id": target["family_id"],
        "subtype": target["subtype"],
        "expected_answer": expected,
        "selected_answer": selected,
        "is_correct": canonical(selected) == canonical(expected),
        "scores": scored["scores"], "loss": scored["loss"],
        "selected_index": scored["selected_index"],
        "correct_index_in_delivered_order": scored["correct_index"],
        "option_count": scored["option_count"],
        "assisted": bool(episode["event"].get("assisted")),
        "support_count": len(episode["public_record"]["support_ids"]),
        "cue_visible": episode["public_record"]["face_cue_visible"],
        "batch_index": batch_index, "optimizer_update_index": update_index,
        "checkpoint_before": identity_before,
        "checkpoint_after": identity_after,
        "record_id": episode["public_record"]["record_id"],
    }


# --------------------------------------------------------------------------
# evaluating the frozen panel
# --------------------------------------------------------------------------

def evaluate_panel(*, learner, items, built=None, phase):
    """Answer the frozen panel with no updates, keeping every per-question row."""
    rows = []
    for item in items:
        entry = (evaluation.diagnostic_item(item, built=built)
                 if item["kind"] in evaluation.DIAGNOSTIC_KINDS
                 else evaluation.compile_panel_item(item, built=built))
        episode = entry["episode"]
        task = episode_task(episode)
        info = _score_task(learner, task)
        expected = episode["teacher_target"]["correct"]
        rows.append({
            "item_id": item["item_id"], "layer": item["layer"],
            "kind": item["kind"], "phase": phase,
            "task_profile": episode["teacher_target"]["profile"],
            "face": item["face"], "family_id": item["family_id"],
            "subtype": episode["teacher_target"]["subtype"],
            "expected_answer": expected,
            "selected_answer": info["selected"],
            "is_correct": canonical(info["selected"]) == canonical(expected),
            "scores": info["scores"], "loss": info["loss"],
            "selected_index": info["selected_index"],
            "correct_index_in_delivered_order": info["correct_index"],
            "expectation": entry.get("expectation"),
            "record_id": episode["public_record"]["record_id"],
        })
    return rows


def _score_task(learner, task):
    """Scores for one evaluation item, from one forward pass, no update."""
    torch = learner.torch
    selected = learner.predict(task)
    info = learner.scores(task) if hasattr(learner, "scores") else None
    if info is None:
        position = learner._position(task) if hasattr(learner, "_position") else None
        scores = learner.forward(position) if position is not None else None
        require(scores is not None, "FACE_EVAL_SCORES_UNAVAILABLE")
        index = int(torch.argmax(scores).item())
        info = {"scores": [round(float(value.detach()), 6) for value in scores],
                "loss": None, "correct_index": task.get("encoded_correct_index"),
                "selected_index": index}
    return {"scores": info["scores"], "loss": info.get("loss"),
            "selected": selected, "selected_index": info.get("selected_index"),
            "correct_index": info.get("correct_index")}


def layers_from_rows(rows):
    grouped = OrderedDict()
    for row in rows:
        grouped.setdefault(row["layer"], []).append(row)
    return grouped


# --------------------------------------------------------------------------
# one condition end to end
# --------------------------------------------------------------------------

def run_condition_with_evaluation(*, condition, organization, arm, framework, model,
                                  learner_factory, checkpoint_writer,
                                  checkpoint_verifier, built=None,
                                  batch_size=schedule.BATCH_SIZE, wall_clock=None,
                                  max_wall_seconds=None, panel_items=None,
                                  event_limit=None, observer=None, seed=None):
    """One condition: measure the panel, teach, measure it again.

    The **before** rows come from the same learner and framework measured before
    the first update, which is the only way they describe a starting point rather
    than a trained one.
    """
    events = schedule.condition_events(condition, organization, arm, seed=seed,
                                       built=built)
    if event_limit is not None:
        events = events[:event_limit]
    items = list(panel_items if panel_items is not None else evaluation.panel(built))
    episodes = compile_events(events, built=built)
    tasks_index = [episode_task(episode) for episode in episodes]
    learner = learner_factory(framework=framework, model=model, tasks=tasks_index)
    # the condition tag is what the deployed checkpoint writer names its file by
    learner.condition_tag = condition
    before_rows = evaluate_panel(learner=learner, items=items, built=built,
                                 phase="before")
    teaching = run_condition(
        run_id=condition, episodes=episodes, framework=framework, model=model,
        learner_factory=learner_factory, checkpoint_writer=checkpoint_writer,
        checkpoint_verifier=checkpoint_verifier,
        batch_size=batch_size, wall_clock=wall_clock,
        max_wall_seconds=max_wall_seconds, observer=observer, learner=learner)
    after_rows = evaluate_panel(learner=learner, items=items, built=built,
                                phase="after")
    return {"condition": condition, "organization": organization, "cue": arm,
            "schedule_digest": schedule.schedule_digest(events),
            "planned_episodes": len(events), "teaching": teaching,
            "evaluation": {"before": before_rows, "after": after_rows},
            "layers": evaluation.evaluate(
                layers_from_rows(after_rows),
                before_rows=layers_from_rows(before_rows), built=built),
            "status": teaching["status"]}


def launch(*, conditions, framework_factory, learner_factory, checkpoint_writer,
           checkpoint_verifier, authorization, built=None, panel_items=None,
           batch_size=schedule.BATCH_SIZE, wall_clock=None,
           max_wall_seconds=None, event_limit=None, seed=None):
    """Run the declared conditions from matched initial weights, one job.

    ``framework_factory(seed)`` returns ``(framework, model)`` and is called once
    per condition with the same seed; the snapshots are compared and a mismatch
    fails the run closed, because a different starting point would confound the
    comparison the conditions are supposed to make.
    """
    require(isinstance(authorization, dict) and authorization.get("owner_go") is True,
            "FACE_RUN_NOT_AUTHORIZED")
    require(authorization.get("run_id"), "FACE_RUN_ID_REQUIRED")
    registered = {entry["condition"]: entry for entry in schedule.comparison_conditions()}
    results, snapshots = OrderedDict(), {}
    for condition in conditions:
        require(condition in registered, "FACE_CONDITION_UNKNOWN:" + str(condition))
        spec = registered[condition]
        framework, model = framework_factory(SEED)
        snapshots[condition] = digest(canonical(sorted(
            trainer.parameter_snapshot(framework, model).items())))
        results[condition] = run_condition_with_evaluation(
            condition=condition, organization=spec["organization"],
            arm=spec["cue"], framework=framework, model=model,
            learner_factory=learner_factory,
            checkpoint_writer=checkpoint_writer,
            checkpoint_verifier=checkpoint_verifier, built=built,
            batch_size=batch_size, wall_clock=wall_clock,
            max_wall_seconds=max_wall_seconds, panel_items=panel_items,
            event_limit=event_limit, seed=seed)
    matched = len(set(snapshots.values())) == 1
    require(matched, "FACE_INITIAL_WEIGHTS_NOT_MATCHED")
    return {
        "schema": RESULT_SCHEMA,
        "run_id": authorization["run_id"],
        "authorization": {"owner_go": True, "run_id": authorization["run_id"]},
        "seed": SEED,
        "conditions": list(conditions),
        "matched_initial_weights": matched,
        "initial_weight_digest": snapshots[conditions[0]],
        "batch_size": batch_size,
        "planned": schedule.planned_counts(),
        "events_per_condition": {
            condition: results[condition]["planned_episodes"]
            for condition in results},
        "results": results,
        "comparison": compare(results),
        "boundary": {
            "automatic_retries": 0,
            "seven_stage_neural_cycles": 0,
            "presentation_note": ("a sweep over six roles is not a completed "
                                  "seven-stage neural cycle and no counter in this "
                                  "result calls it one"),
            "support_note": ("worked supports are counted separately from queries "
                             "and are never counted as optimizer updates"),
        },
    }


#: The single declared initialization seed. One paired initialization is an
#: exploratory pilot, not multi-seed replication.
SEED = 20260912


def compare(results):
    """Per-layer and between-condition comparison, always paired by question."""
    layers = OrderedDict()
    for condition, payload in results.items():
        after = layers_from_rows(payload["evaluation"]["after"])
        for layer, rows in after.items():
            layers.setdefault(layer, OrderedDict())[condition] = rows
    comparison = OrderedDict()
    for layer, per_condition in layers.items():
        names = list(per_condition)
        comparison[layer] = {
            "conditions": names,
            "per_condition": {
                name: {"correct": sum(1 for row in rows if row["is_correct"]),
                       "total": len(rows),
                       "accuracy": (sum(1 for row in rows if row["is_correct"])
                                    / len(rows)) if rows else None}
                for name, rows in per_condition.items()},
        }
        if len(names) == 2:
            comparison[layer]["paired"] = evaluation.between_conditions(
                {layer: per_condition[names[0]]},
                {layer: per_condition[names[1]]})[layer]
    return comparison
