"""Zero-update readout of the four delivered CFC-pilot checkpoints.

Attempt 004 trained all four conditions and then lost its own readout: the
``measurements.json`` object - per-face breakdowns, per-question rows, before/after
pairing, baselines and the milestone report - was uploaded but never declared as an
artefact, so verified collection kept only the four checkpoints and cleanup deleted
the bucket. This module recovers that detail from the checkpoints that survived.

What makes the recovery a measurement rather than a re-run:

* **no optimizer is ever stepped.** The panel is answered by forward passes only.
  The module never calls the training path, and it *measures* the claim: the
  module's parameter digest is taken before and after each condition's readout and
  must be unchanged, so "zero updates" is a reading, not an assertion;
* **the weights are the delivered ones, by digest.** Each checkpoint file's sha256
  is bound in the job's authority, and after loading, the live module's own
  parameter digest must equal the identity recorded inside the checkpoint;
* **the arithmetic is checked against the delivered result.** The recomputed
  per-layer totals must equal the totals attempt 004 published. If they do not, the
  readout reports a mismatch and the recovery is a failure, not a result.

What it deliberately does not do:

* it does not retrain, and it does not write to any checkpoint;
* it does not claim the before readings are the run's own before readings. Those
  came from an initial state whose digest was in the lost payload, so the initial
  state here is *reconstructed* from the recorded seeds and is labelled as such;
* it does not present the 216-question panel as 216 independent questions: the
  panel is 192 held-out questions plus 24 diagnostics, and the 192 are views of 16
  base families.
"""
from __future__ import annotations

import json
from collections import OrderedDict
from pathlib import Path

from .graph import canonical, digest, require
from . import face_corpus as corpus
from . import face_evaluation as evaluation
from . import face_experiment as experiment
from . import face_schedule as schedule
from . import face_worker as worker

SCHEMA = "cas.cube-face-readout/0.1"
RESULT_SCHEMA = "cas.cube-face-readout-result/1"
CHECKPOINT_SCHEMA = "cas.cube-face-checkpoint/1"
MANIFEST_SCHEMA = "cas.cube-face-artifact-manifest/1"

STATUS_COMPLETE = "READOUT_COMPLETE"
STATUS_FAILED = "READOUT_FAILED"

#: The paired comparisons the recovery must answer. The delivered envelope could
#: not carry these: a paired test needs the per-question rows, and the rows were in
#: the lost payload.
DECLARED_PAIRS = (
    ("cfc_stable_cues", "mixed_order_stable_cues",
     "CFC loop versus mixed order, both with stable cues"),
    ("cfc_neutral_cue", "mixed_order_neutral_cue",
     "CFC loop versus mixed order, both with the neutral cue"),
    ("cfc_stable_cues", "cfc_neutral_cue",
     "stable cue versus neutral cue, both in the CFC loop"),
    ("mixed_order_stable_cues", "mixed_order_neutral_cue",
     "stable cue versus neutral cue, both in mixed order"),
)

#: The panels, named so a reader cannot mistake one for the other.
PANEL_NOTE = ("192 primary questions (96 recognition + 96 application) plus 24 "
              "diagnostics; the 192 primary questions are views of 16 held-out "
              "families, not 192 independent families")


# --------------------------------------------------------------------------
# 1. plan
# --------------------------------------------------------------------------

def compile_plan(config):
    """The corpus, the panel, the four declared conditions and their checkpoints."""
    require(config.get("schema") == "cas.cube-face-readout-config/1",
            "READOUT_CONFIG_SCHEMA")
    built = corpus.families()
    declared = config.get("conditions")
    require(type(declared) is dict and declared, "READOUT_CONFIG_CONDITIONS")
    registered = {entry["condition"]: entry
                  for entry in schedule.comparison_conditions()}
    conditions = []
    for name in config.get("condition_order") or sorted(declared):
        require(name in registered, "READOUT_CONDITION_UNKNOWN:" + str(name))
        spec = declared[name]
        require(type(spec) is dict, "READOUT_CONDITION_SPEC:" + name)
        require(spec.get("checkpoint"), "READOUT_CHECKPOINT_NAME_REQUIRED:" + name)
        require(type(spec.get("sha256")) is str and len(spec["sha256"]) == 64,
                "READOUT_CHECKPOINT_SHA_REQUIRED:" + name)
        conditions.append({"condition": name,
                           "organization": registered[name]["organization"],
                           "cue": registered[name]["cue"],
                           "checkpoint": spec["checkpoint"],
                           "sha256": spec["sha256"]})
    panel = evaluation.panel(built)
    checkpoint_dir = config.get("checkpoint_dir")
    require(type(checkpoint_dir) is str and checkpoint_dir,
            "READOUT_CHECKPOINT_DIR_REQUIRED")
    plan = {"conditions": conditions,
            "checkpoint_dir": checkpoint_dir,
            "corpus_digest": digest(canonical(corpus.coverage_report(built))),
            "panel": evaluation.panel_manifest(built),
            "panel_note": PANEL_NOTE,
            "seed": config.get("seed", experiment.SEED),
            "encoder_seed": config.get("encoder_seed", 20260909),
            "learning_rate": config.get("learning_rate", 0.003),
            "optimizer_updates": 0,
            "training": False,
            "expected_totals": config.get("expected_totals") or {},
            "lost_measurements_sha256": config.get("lost_measurements_sha256"),
            "declared_pairs": [{"first": first, "second": second, "question": why}
                               for first, second, why in DECLARED_PAIRS]}
    require(len(conditions) == len(config.get("condition_order") or declared),
            "READOUT_CONDITION_COUNT")
    return built, conditions, panel, plan


def checkpoint_path(root, directory, name):
    """Where the package carries a delivered checkpoint.

    The package preserves repository-relative paths, so the directory is the one
    the delivered receipt recorded, not a convention invented here.
    """
    return Path(root) / directory / name


# --------------------------------------------------------------------------
# 2. the checkpoint, verified before it is used
# --------------------------------------------------------------------------

def sha256_file(path):
    import hashlib
    accumulator = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            accumulator.update(block)
    return accumulator.hexdigest()


def load_verified(*, torch, path, expected_sha256, condition):
    """Load one checkpoint and prove it is the delivered artefact.

    The file hash is bound by the job's authority, and the digest recorded inside
    the checkpoint is recomputed from the stored tensors, so a truncated, swapped
    or edited file fails closed instead of contributing quietly to the readout.
    """
    path = Path(path)
    require(path.is_file(), "READOUT_CHECKPOINT_MISSING:" + str(path))
    actual = sha256_file(path)
    require(actual == expected_sha256,
            "READOUT_CHECKPOINT_HASH:%s:%s!=%s"
            % (condition, actual, expected_sha256))
    loaded = torch.load(str(path), map_location="cpu", weights_only=True)
    require(type(loaded) is dict and loaded.get("schema") == CHECKPOINT_SCHEMA,
            "READOUT_CHECKPOINT_SCHEMA:" + condition)
    require(loaded.get("condition") == condition,
            "READOUT_CHECKPOINT_CONDITION:%s:%s"
            % (condition, loaded.get("condition")))
    order = list(loaded.get("parameter_order") or ())
    require(order, "READOUT_CHECKPOINT_PARAMETER_ORDER:" + condition)
    identity = loaded.get("identity")
    require(type(identity) is str and len(identity) == 64,
            "READOUT_CHECKPOINT_IDENTITY:" + condition)
    recomputed = worker._state_digest(loaded["state"], order)
    require(recomputed == identity,
            "READOUT_CHECKPOINT_IDENTITY_MISMATCH:%s:%s!=%s"
            % (condition, recomputed, identity))
    return {"path": str(path), "sha256": actual, "identity": identity,
            "parameter_order": order, "state": loaded["state"],
            "bytes": path.stat().st_size}


# --------------------------------------------------------------------------
# 3. the panel, compiled once
# --------------------------------------------------------------------------

def panel_entries(built, panel):
    """The compiled panel, and the tasks the learner must hold to answer it."""
    entries, tasks = [], []
    for item in panel:
        entry = (evaluation.diagnostic_item(item, built=built)
                 if item["kind"] in evaluation.DIAGNOSTIC_KINDS
                 else evaluation.compile_panel_item(item, built=built))
        entries.append((item, entry))
        tasks.append(experiment.episode_task(entry["episode"]))
    require(len(tasks) == len(panel), "READOUT_PANEL_INCOMPLETE")
    return entries, tasks


def layer_baselines(entries):
    """Constant-rule baselines per layer, from the compiled panel."""
    grouped = OrderedDict()
    for item, entry in entries:
        grouped.setdefault(item["layer"], []).append(entry)
    return OrderedDict((layer, evaluation.baselines(values))
                       for layer, values in grouped.items())


# --------------------------------------------------------------------------
# 4. one condition, zero updates
# --------------------------------------------------------------------------

def read_condition(*, condition_spec, built, panel, tasks, encoder, torch, device,
                   config, loaded, framework_factory, learner_factory):
    """Answer the frozen panel from the delivered weights, and update nothing."""
    condition = condition_spec["condition"]
    framework, model = framework_factory(torch, device, encoder, config)
    learner = learner_factory(torch, framework, model, tasks, device,
                              config.get("learning_rate", 0.003))
    learner.condition_tag = condition

    order = [name for name, _ in learner.module.named_parameters()]
    require(order == loaded["parameter_order"],
            "READOUT_PARAMETER_ORDER_CHANGED:%s" % condition)
    rebuilt_identity = worker._state_digest(learner.module.state_dict(), order)

    before_rows = experiment.evaluate_panel(learner=learner, items=panel,
                                            built=built, phase="before")
    after_evaluation_identity = worker._state_digest(
        learner.module.state_dict(), order)
    require(after_evaluation_identity == rebuilt_identity,
            "READOUT_UPDATED_DURING_BEFORE:%s" % condition)

    learner.module.load_state_dict(loaded["state"])
    trained_identity = worker._state_digest(learner.module.state_dict(), order)
    require(trained_identity == loaded["identity"],
            "READOUT_LOADED_IDENTITY:%s:%s!=%s"
            % (condition, trained_identity, loaded["identity"]))

    after_rows = experiment.evaluate_panel(learner=learner, items=panel,
                                           built=built, phase="after")
    final_identity = worker._state_digest(learner.module.state_dict(), order)
    require(final_identity == trained_identity,
            "READOUT_UPDATED_DURING_AFTER:%s" % condition)

    after_by_layer = experiment.layers_from_rows(after_rows)
    before_by_layer = experiment.layers_from_rows(before_rows)
    layers = evaluation.evaluate(after_by_layer, before_rows=before_by_layer,
                                 built=built)
    return {
        "condition": condition,
        "organization": condition_spec["organization"],
        "cue": condition_spec["cue"],
        "checkpoint": {"name": condition_spec["checkpoint"],
                       "sha256": loaded["sha256"], "bytes": loaded["bytes"],
                       "identity": loaded["identity"],
                       "identity_recomputed_in_place": trained_identity,
                       "parameter_count": len(order)},
        "optimizer_updates": 0,
        "parameter_digest_rebuilt_initial": rebuilt_identity,
        "parameter_digest_trained": trained_identity,
        "parameter_digest_after_readout": final_identity,
        # The load is supposed to change the weights; what must not change them is
        # the readout itself, so the digest is compared across the evaluation, not
        # across the load.
        "parameters_unchanged_by_readout": final_identity == trained_identity,
        "before_rows": before_rows,
        "after_rows": after_rows,
        "layers": layers,
        "totals": totals(layers),
        "milestone": evaluation.milestone_report(layers),
        "boundary": {
            "before_readings": ("from a deterministically reconstructed initial "
                                "state, not verifiable against a retained digest: "
                                "the run's initial-weight digest was in the lost "
                                "payload"),
            "after_readings": ("from the delivered checkpoint, identified by file "
                               "hash and by the parameter digest recorded inside "
                               "it"),
            "no_optimizer_step": True,
            "zero_updates_measured_as": ("the parameter digest after loading the "
                                         "checkpoint equals the digest after the "
                                         "last panel pass"),
        },
    }


def totals(layers):
    """The delivered envelope's shape: per-layer correct and total."""
    return OrderedDict(
        (layer, {"correct": values["correct"], "total": values["questions"],
                 "accuracy": values["accuracy"]})
        for layer, values in layers["layers"].items())


def reproduction_check(readouts, plan):
    """Do the recomputed totals equal the totals attempt 004 published?

    This is the readout's own gate. A mismatch means the recovery has not
    reproduced the delivered measurement, and the run must say so rather than
    present the new numbers as the old ones.
    """
    expected = plan.get("expected_totals") or {}
    require(expected, "READOUT_EXPECTED_TOTALS_REQUIRED")
    mismatches, checked = [], 0
    for condition, payload in readouts.items():
        published = expected.get(condition) or {}
        require(published, "READOUT_EXPECTED_TOTALS_MISSING:" + condition)
        for layer, wanted in published.items():
            got = payload["totals"].get(layer)
            checked += 1
            if got is None or got["correct"] != wanted["correct"] \
                    or got["total"] != wanted["total"]:
                mismatches.append({"condition": condition, "layer": layer,
                                   "recomputed": got, "published": wanted})
    return {"checked": checked, "mismatches": mismatches,
            "reproduced": not mismatches,
            "gate": ("a mismatch is a failed recovery, not a result: it would mean "
                     "the checkpoint or the path no longer re-derives the numbers "
                     "attempt 004 published")}


def paired_report(readouts):
    """The paired comparisons the delivered envelope could not carry."""
    report = OrderedDict()
    by_layer = OrderedDict()
    for condition, payload in readouts.items():
        for layer, rows in experiment.layers_from_rows(payload["after_rows"]).items():
            by_layer.setdefault(layer, OrderedDict())[condition] = rows
    for first, second, why in DECLARED_PAIRS:
        for layer, per_condition in by_layer.items():
            if first not in per_condition or second not in per_condition:
                continue
            entry = evaluation.between_conditions(
                {layer: per_condition[first]}, {layer: per_condition[second]})[layer]
            report["%s|%s|%s" % (layer, first, second)] = dict(
                entry, first=first, second=second, layer=layer, question=why)
    return report


# --------------------------------------------------------------------------
# 5. the whole readout
# --------------------------------------------------------------------------

def _default_framework_factory(torch, device, encoder, config):
    """The same construction the training worker used, so the rebuild is faithful.

    The seeding sits here rather than in ``read_condition`` because this is the
    factory the training run seeded with; a stub factory in a rehearsal therefore
    needs no torch at all.
    """
    from . import real_framework as rf
    torch.manual_seed(config.get("seed", experiment.SEED))
    framework = rf.build_graph_training_framework(
        torch, device, seed=config.get("encoder_seed", 20260909), encoder=encoder)
    return framework, framework.build_decompose_model(
        seed=config.get("seed", experiment.SEED))


def _default_learner_factory(torch, framework, model, tasks, device, learning_rate):
    from .real_framework import GraphLearner
    return GraphLearner(torch, framework, tasks, device, learning_rate)


def read_all(config, *, torch, device, built, conditions, panel, plan, root,
             framework_factory=None, learner_factory=None):
    """Every declared condition, each verified and each read with zero updates."""
    framework_factory = framework_factory or _default_framework_factory
    learner_factory = learner_factory or _default_learner_factory
    entries, tasks = panel_entries(built, panel)
    per_layer = OrderedDict()
    for item, _ in entries:
        per_layer[item["layer"]] = per_layer.get(item["layer"], 0) + 1
    conditions_specs = [{"condition": entry["condition"],
                         "organization": entry["organization"], "cue": entry["cue"],
                         "checkpoint": entry["checkpoint"],
                         "sha256": entry["sha256"]}
                        for entry in conditions]
    # One encoder for every condition, fitted on the union of every public record
    # any of them sees - the same rule the training worker used, so the readout's
    # model-facing vectors are the ones the run's evaluation used.
    corpus_bundle = worker.public_corpus(
        built, panel, [(entry["condition"], entry["organization"], entry["cue"])
                       for entry in conditions])
    from . import real_framework as rf
    encoder = rf.build_encoder(torch, corpus_bundle["publics"], d_model=64,
                              seed=config.get("encoder_seed", 20260909),
                              device=device)
    readouts = OrderedDict()
    for spec in conditions_specs:
        loaded = load_verified(
            torch=torch,
            path=checkpoint_path(root, plan["checkpoint_dir"],
                                 spec["checkpoint"]),
            expected_sha256=spec["sha256"], condition=spec["condition"])
        readouts[spec["condition"]] = read_condition(
            condition_spec=spec, built=built, panel=panel, tasks=tasks,
            encoder=encoder, torch=torch, device=device, config=config,
            loaded=loaded, framework_factory=framework_factory,
            learner_factory=learner_factory)
    return {
        "schema": SCHEMA,
        "conditions": conditions_specs,
        "condition_order": list(readouts),
        "readouts": readouts,
        "baselines": layer_baselines(entries),
        "paired": paired_report(readouts),
        "reproduction": reproduction_check(readouts, plan),
        "optimizer_updates": 0,
        "optimizer_steps_taken": 0,
        "training_performed": False,
        "panel": {"items": len(entries), "by_layer": dict(per_layer),
                  "note": PANEL_NOTE},
        "boundary": {
            "no_optimizer_step": True,
            "zero_updates_measured": all(
                payload["parameters_unchanged_by_readout"]
                for payload in readouts.values()),
            "scores_from_evaluation_pass": True,
            "automatic_retries": 0,
            "seven_stage_neural_cycles": 0,
            "lost_measurements_sha256": plan.get("lost_measurements_sha256"),
        },
    }


# --------------------------------------------------------------------------
# 6. delivery
# --------------------------------------------------------------------------

def run(config, *, torch, device, results, artifacts, root=None, outbound=None,
        readout=None):
    """Run the readout and write its delivery.

    ``readout`` is the whole-readout function, injected so a rehearsal can drive
    this same flow with stub factories and no torch work.
    """
    built, conditions, panel, plan = compile_plan(config)
    root = Path(root or config.get("root") or Path.cwd())
    readout = readout or read_all
    report = readout(config, torch=torch, device=device, built=built,
                     conditions=conditions, panel=panel, plan=plan, root=root)
    return {"plan": plan, "readout": report, **deliver(
        results=results, artifacts=artifacts, job=config["job"], plan=plan,
        report=report)}


def deliver(*, results, artifacts, job, plan, report):
    """Write the readout, declare every artefact, and write the envelope.

    The measurements payload and the readout both go into the artefact directory
    and are declared, because attempt 004's loss was exactly this: a payload that
    was uploaded but not declared, and therefore deleted with the bucket.
    """
    measurements = {
        "schema": SCHEMA,
        "job": job,
        "plan": plan,
        "reproduction": report["reproduction"],
        "optimizer_updates": 0,
        "boundary": report["boundary"],
        "conditions": {
            condition: {"total_correct":
                        sum(layer["correct"]
                            for layer in payload["totals"].values()),
                        "totals": payload["totals"],
                        "checkpoint": payload["checkpoint"],
                        "parameters_unchanged_by_readout":
                            payload["parameters_unchanged_by_readout"],
                        "milestone": payload["milestone"]}
            for condition, payload in report["readouts"].items()},
        "paired": report["paired"],
        "baselines": report["baselines"],
        "panel": report["panel"],
    }
    measurements["lost_measurements_sha256"] = plan.get("lost_measurements_sha256")
    payload = {"schema": SCHEMA, "job": job,
               "note": ("the full per-question readout; the measurements file is "
                        "its summary, and both are declared so neither can be "
                        "dropped by collection"),
               "readout": report}
    _write(results / "measurements.json", measurements)
    _write(artifacts / "readout.json", payload)
    (artifacts / "measurements.json").write_bytes(
        (results / "measurements.json").read_bytes())
    staged = [{"name": name, "sha256": worker._sha256(artifacts / name),
               "bytes": (artifacts / name).stat().st_size}
              for name in sorted(path.name for path in artifacts.iterdir()
                                 if path.is_file()
                                 and path.name != "manifest.json")]
    (artifacts / "manifest.json").write_text(
        json.dumps({"schema": MANIFEST_SCHEMA, "job": job, "artifacts": staged},
                   sort_keys=True, indent=2) + "\n", encoding="utf-8")
    envelope = {
        "schema": RESULT_SCHEMA,
        "job": job,
        "status": (STATUS_COMPLETE if report["reproduction"]["reproduced"]
                   else STATUS_FAILED),
        "failure": (None if report["reproduction"]["reproduced"] else
                    {"type": "ReproductionMismatch",
                     "message": "READOUT_DOES_NOT_REPRODUCE_THE_DELIVERED_TOTALS"}),
        "artifacts": staged,
        "optimizer_updates": 0,
        "training_performed": False,
        "conditions": {
            condition: {
                "checkpoint_sha256": payload["checkpoint"]["sha256"],
                "checkpoint_identity": payload["checkpoint"]["identity"],
                "parameters_unchanged_by_readout":
                    payload["parameters_unchanged_by_readout"],
                "optimizer_updates": 0,
                "totals": payload["totals"]}
            for condition, payload in report["readouts"].items()},
        "reproduction": report["reproduction"],
        "paired_summary": {
            key: {"only_first_correct": entry["only_first_correct"],
                  "only_second_correct": entry["only_second_correct"],
                  "discordant_pairs": entry["discordant_pairs"]}
            for key, entry in report["paired"].items()},
        "lost_measurements_sha256": plan.get("lost_measurements_sha256"),
        "measurements_sha256": worker._sha256(results / "measurements.json"),
        "boundary": report["boundary"],
    }
    raw = (json.dumps(envelope, sort_keys=True, indent=2,
                      allow_nan=False) + "\n").encode("utf-8")
    (results / "result.json").write_bytes(raw)
    (results / "result.json.sha256").write_text(
        worker._sha256_bytes(raw) + "\n", encoding="utf-8")
    return {"envelope": envelope, "measurements": measurements,
            "artifacts": staged}


def _write(path, document):
    path.write_text(json.dumps(document, sort_keys=True, indent=2,
                               allow_nan=False) + "\n", encoding="utf-8")
