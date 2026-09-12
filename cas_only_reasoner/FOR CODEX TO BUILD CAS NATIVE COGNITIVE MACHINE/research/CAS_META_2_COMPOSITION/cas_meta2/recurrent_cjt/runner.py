"""CAS_RDCJT_001: the real connection between the packaged worker and the experiment.

This is the module the instance actually calls. It is the production numerical
path, not a stub: it acquires the GPU, builds the encoder and framework, builds
both arms' learners over the SAME registered module, runs the experiment, writes
every artefact and declares each one.

"A loop that can call only a stub is not completion." So the heavy dependencies
are resolved HERE, from the real modules, and only the seams the tests need are
injectable.

Why the one-pass arm uses the recurrent class pinned to depth one
-----------------------------------------------------------------
It would look tidier to build the one-pass arm from the plain ``GraphLearner``.
It would also be wrong. ``course.run_course`` calls ``set_depth`` on whatever it
is given, and more importantly the two arms must share the readout, the scoring
and the batching down to the last line, or a difference between them could come
from the plumbing rather than the recurrence.

``RecurrentGraphLearner`` at depth one IS the existing computation - not
approximately, bitwise, which
``tests/test_recurrent_cjt_learner.py::test_depth_one_is_the_existing_learner_bitwise``
asserts. So pinning it to depth one gives a matched control that cannot drift
from the recurrent arm in any respect except the number of passes.

GPU, fail closed
----------------
``gpu_adapter._cuda()`` refuses a CPU device. There is no silent CPU fallback:
a neural workload on CPU is prohibited, so this raises rather than quietly
producing a number that took a different path than the one that was authorised.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import experiment as ex
from . import course as cs
from . import learner as ml
from . import recurrence as rc

SCHEMA = "cas.recurrent-cjt-runner/0.1"
ARTIFACT_MANIFEST_SCHEMA = "cas.recurrent-cjt-artifact-manifest/1"
CHECKPOINT_SCHEMA = "cas.recurrent-cjt-checkpoint/1"


def require(condition, code):
    if not condition:
        raise ValueError(code)


def _sha256(path):
    import hashlib
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_json(path, document):
    path.write_text(json.dumps(document, sort_keys=True, indent=2,
                               allow_nan=False) + "\n", encoding="utf-8")
    return path


def _parameter_order(learner):
    return [name for name, _ in learner.module.named_parameters()]


# --------------------------------------------------------------------------
# the deployed seams
# --------------------------------------------------------------------------

def course_task_index(built=None, rounds=None):
    """Every task the course will present, deduplicated, in a stable order.

    The learner is indexed ONCE over all sixteen rounds. Indexing per round would
    give the two arms different position maps whenever a task recurs, and the
    comparison would then differ by bookkeeping rather than by recurrence.
    Deduplication is by ``record_id`` because the same question legitimately
    recurs across rounds - that is what maintenance practice IS.
    """
    # The round NUMBERS come from the plan, not from a guess. This said
    # range(1, 17) and course_plan actually numbers its rounds 0..15, so round 0
    # was never indexed and round 16 never existed: the first batch of the first
    # arm raised KeyError on _position, after $7.00 was spent. Reading the plan
    # cannot drift from what run_course will ask for, because it IS what
    # run_course reads.
    if rounds is None:
        rounds = [entry["round"] for entry in cs.course_plan()["rounds"]]
    index, seen = [], set()
    for round_index in rounds:
        for tasks in cs.default_tasks_for_round(round_index, built=built).values():
            for task in tasks:
                key = task["record_id"]
                if key in seen:
                    continue
                seen.add(key)
                index.append(task)
    require(index, "RDCJT_TASK_INDEX_EMPTY")
    return index


def panel_disjointness(panel, task_index):
    """Measure whether the panel is material the course actually taught.

    This was ASSERTED before it was measured, and the assertion was wrong. The
    readiness report's "the panel is examined material" was true of the readout's
    rewired direct_inventory rows; it is NOT true of the evaluation panel, which
    ``face_evaluation.panel`` draws from ``FINAL_HELD_OUT`` families while
    ``face_schedule.cfc_round_events`` draws from ``TRAINING`` families.

    Measured on the real corpus: the course presents 552 tasks across 24
    families, the panel is 216 items across 16 families, and the two share no
    family and no record id. So a gain on this panel is an application result on
    unexamined material, not practice fit - and saying otherwise understates it.

    The numbers are recomputed here on every run rather than quoted, because a
    corpus or schedule change could make them false without anyone noticing.
    """
    panel_families = {item["family_id"] for item in panel if "family_id" in item}
    course_families = {task["family_id"] for task in task_index
                       if "family_id" in task}
    panel_records = {item.get("record_id") for item in panel}
    course_records = {task.get("record_id") for task in task_index}
    family_overlap = sorted(panel_families & course_families)
    record_overlap = sorted(value for value in (panel_records & course_records)
                            if value is not None)
    disjoint = not family_overlap and not record_overlap
    return {
        "panel_items": len(panel),
        "panel_families": len(panel_families),
        "course_tasks": len(task_index),
        "course_families": len(course_families),
        "shared_families": family_overlap,
        "shared_record_ids": record_overlap,
        "disjoint": disjoint,
        "examined_during_teaching": not disjoint,
        "what_this_licenses": (
            "an application measurement on material this learner was never taught"
            if disjoint else
            "a depth effect on examined material only; not transfer"),
        "what_it_still_does_not_license": (
            "novelty. Earlier jobs measured this same frozen panel, so it is "
            "held out from THIS learner's teaching, not material no run has "
            "ever seen"),
    }


def build_context(config, *, torch, device):
    """Encoder, framework factory, learner factories, batch steps, panel.

    Everything the experiment needs, resolved from the REAL modules. Kept apart
    from :func:`run` so a rehearsal can inspect the wiring without training.

    ``built`` is left as None deliberately: ``face_evaluation.panel`` and
    ``face_schedule.cfc_round_events`` both default it to ``corpus.families()``,
    so passing None uses the same corpus the deployed teaching path uses rather
    than a second one built here.
    """
    from ..graph_teaching import face_evaluation as evaluation
    from ..graph_teaching import face_experiment as fx
    from ..graph_teaching import face_schedule as schedule
    from ..graph_teaching import face_worker as fw
    from ..graph_teaching import real_framework as rf
    from ..graph_teaching import trainer

    built = None
    panel = list(evaluation.panel(built))
    require(panel, "RDCJT_PANEL_EMPTY")

    # Both cue arms, exactly as face_worker does, so the shared encoder contains
    # every cue token and the arms cannot differ through the tokenizer.
    conditions = [(entry["condition"], entry["organization"], entry["cue"])
                  for entry in schedule.comparison_conditions()]
    corpus = fw.public_corpus(built, panel, conditions)
    encoder_seed = int(config.get("encoder_seed", 20260909))
    encoder = rf.build_encoder(torch, corpus["publics"], d_model=64,
                               seed=encoder_seed, device=device)

    tasks_index = course_task_index(built=built)
    disjointness = panel_disjointness(panel, tasks_index)

    def framework_factory(seed):
        torch.manual_seed(int(seed))
        framework = rf.build_graph_training_framework(
            torch, device, seed=encoder_seed, encoder=encoder)
        return framework, framework.build_decompose_model(seed=int(seed))

    def tasks_for_round(round_index):
        return cs.default_tasks_for_round(round_index, built=built)

    def learner_factory(*, framework, model, arm, accounting=None):
        # ONE class for both arms. Depth one is the existing computation bitwise,
        # so the control differs from the treatment in passes and nothing else.
        depth = (ex.ONE_PASS_DEPTH if arm == "one_pass" else rc.PRIMARY_DEPTH)
        return ml.build_recurrent_learner(
            torch, framework, list(tasks_index), device,
            float(config.get("learning_rate", 0.003)),
            depth=depth, accounting=accounting)

    return {
        "built": built,
        "panel": panel,
        "encoder": encoder,
        "corpus_digest": corpus.get("digest"),
        "task_index_size": len(tasks_index),
        "panel_disjointness": disjointness,
        "framework_factory": framework_factory,
        "tasks_for_round": tasks_for_round,
        "learner_factory": learner_factory,
        "evaluate_panel": fx.evaluate_panel,
        "depth_sweep": ml.depth_sweep,
        "parameter_snapshot": trainer.parameter_snapshot,
        # ONE batch step for both arms: the one-pass arm is the same code at
        # depth one, so the batching cannot differ between them either.
        "batch_steps": {arm: ml.recurrent_batch_step for arm in ex.ARMS},
    }


def checkpoint_writer_for(artifacts, *, torch):
    """Write one checkpoint per arm and return its identity and digest."""
    def write(arm, learner):
        path = Path(artifacts) / ("checkpoint_%s.pt" % arm)
        identity = learner.checkpoint_identity()
        torch.save({"schema": CHECKPOINT_SCHEMA, "arm": arm,
                    "identity": identity,
                    "parameter_order": _parameter_order(learner),
                    "state": learner.module.state_dict()}, str(path))
        return {"path": str(path), "arm": arm, "identity": identity,
                "sha256": _sha256(path), "bytes": path.stat().st_size}
    return write


# --------------------------------------------------------------------------
# delivery
# --------------------------------------------------------------------------

def deliver(*, results, artifacts, job, report):
    """Write every payload, DECLARE each one, then the envelope and its sidecar.

    Declaring is the load-bearing part. Attempt 004 uploaded its measurement and
    lost it because the file was never named in the manifest, so verified
    collection kept only what was declared and cleanup deleted the rest. Every
    file written here is named in the manifest before the envelope is written.
    """
    results = Path(results)
    artifacts = Path(artifacts)
    artifacts.mkdir(parents=True, exist_ok=True)

    _write_json(artifacts / "experiment.json", {
        "schema": SCHEMA, "job": job,
        "plan": report["plan"],
        "arms": report["arms"],
        "matched_initial_weights": report["matched_initial_weights"],
        "initial_weight_digest": report["initial_weight_digest"],
        "trainable_parameters_by_arm": report["trainable_parameters_by_arm"],
        "panel": report["panel"],
        "boundary": report["boundary"]})
    _write_json(artifacts / "depth_sweep.json", {
        "schema": SCHEMA, "job": job,
        "depth_sweep": report["depth_sweep"],
        "sweep_comparison": report["sweep_comparison"]})

    staged = [{"name": path.name, "sha256": _sha256(path),
               "bytes": path.stat().st_size}
              for path in sorted(artifacts.iterdir())
              if path.is_file() and path.name != "manifest.json"]
    require(staged, "RDCJT_NO_ARTIFACTS_TO_DECLARE")
    _write_json(artifacts / "manifest.json",
                {"schema": ARTIFACT_MANIFEST_SCHEMA, "job": job,
                 "artifacts": staged})

    envelope = {
        "schema": ex.RESULT_SCHEMA,
        "job": job,
        "status": report["status"],
        "arms": {arm: {"accounting": report["arms"][arm]["accounting"]}
                 for arm in report["arms"]},
        "sweep_comparison": report["sweep_comparison"],
        "matched_initial_weights": report["matched_initial_weights"],
        "trainable_parameters_by_arm": report["trainable_parameters_by_arm"],
        "panel": report["panel"],
        "checkpoints": report.get("checkpoints") or {},
        # Every payload, as the ENTRY SHAPE the collector reads. This was a list
        # of plain strings, and graph_training_curriculum_launch._artifact_name
        # does entry.get("name"), so collection died with
        # AttributeError: 'str' object has no attribute 'get' AFTER the science
        # had finished and uploaded - job cas-meta2-rdcjt-20260912152001-abf38e1e.
        # The envelope must speak the collector's shape, not its own.
        "artifacts": staged,
        "boundary": report["boundary"],
    }
    raw = (json.dumps(envelope, sort_keys=True, indent=2, allow_nan=False)
           + "\n").encode("utf-8")
    (results / "result.json").write_bytes(raw)
    import hashlib
    (results / "result.json.sha256").write_text(
        hashlib.sha256(raw).hexdigest() + "\n", encoding="utf-8")
    return {"status": report["status"], "arms": sorted(report["arms"]),
            "artifacts": [entry["name"] for entry in staged]}


# --------------------------------------------------------------------------
# the entrypoint the packaged worker calls
# --------------------------------------------------------------------------

def run(config, *, results, artifacts, root=None, torch=None, device=None,
        context=None, experiment_run=None):
    """Acquire the GPU, run both arms and the sweep, write the delivery.

    ``torch``/``device``/``context``/``experiment_run`` are injectable so the
    rehearsal drives this same flow with no GPU. The deployed worker passes none
    of them, which is the path that fails closed without CUDA.
    """
    if torch is None or device is None:
        from ..teaching_cycle import gpu_adapter
        torch, device = gpu_adapter._cuda()
    require(str(device) != "cpu", "GPU_REQUIRED")
    context = context or build_context(config, torch=torch, device=device)
    experiment_run = experiment_run or ex.run

    factories = {arm: context["learner_factory"] for arm in ex.ARMS}
    report = experiment_run(
        config,
        framework_factory=context["framework_factory"],
        learner_factories=factories,
        batch_steps=context["batch_steps"],
        evaluate_panel=context["evaluate_panel"],
        panel_items=context["panel"],
        depth_sweep=context["depth_sweep"],
        parameter_snapshot=context["parameter_snapshot"],
        checkpoint_writer=checkpoint_writer_for(artifacts, torch=torch),
        tasks_for_round=context["tasks_for_round"],
        built=context["built"],
        # MEASURED, not assumed. The previous literal True was wrong and
        # understated the result: the panel and the course share no family and no
        # record id on the real corpus.
        examined_during_teaching=context["panel_disjointness"][
            "examined_during_teaching"],
        fresh_family_panel=(context["panel"]
                            if context["panel_disjointness"]["disjoint"]
                            else None))
    return deliver(results=Path(results), artifacts=Path(artifacts),
                   job=config["job"], report=report)
