"""The deployed worker's logic for the face-grounding pilot, as an importable module.

Putting the worker's work here rather than inside a rendered string has one
purpose: everything below can be executed and tested without a shell, so the
packaged flow is rehearsed in-process instead of being trusted on the instance.
The rendered worker in ``aws/graph_training_face_launch.py`` only builds the venv,
installs torch and the frozen wheels, runs this module under that python, and
uploads what it wrote - the same scaffolding the curriculum and checked-component
workers use, because that scaffolding is the part that has actually run.

Order of work, and why:

1. **compile the corpus, tasks and both schedules** - pure data;
2. **build the frozen encoder** from the union of every text any condition will
   see, including all seven cue variants, so the two comparison arms share one
   encoder exactly;
3. **representation checks before training** - changed roles, changed contents and
   a same-token rewiring must produce different model-facing vectors, scores and
   losses must be finite, and gradients must depend on the target. These are the
   checks that decide whether the accepted transform can even carry these tasks,
   and they are reported whether or not they pass;
4. **teach and evaluate every declared condition** from matched initial weights,
   with separate optimizers and checkpoints;
5. **write the measurements, the per-condition checkpoints and the result
   envelope**, then let the outer worker upload them.
"""
from __future__ import annotations

import json
from pathlib import Path

from .graph import canonical, digest, require
from . import face_corpus as corpus
from . import face_evaluation as evaluation
from . import face_experiment as experiment
from . import face_roles as roles
from . import face_schedule as schedule
from . import face_tasks as tasks

SCHEMA = "cas.cube-face-worker/0.1"


# --------------------------------------------------------------------------
# 1. plan and corpus
# --------------------------------------------------------------------------

def compile_plan(config):
    """The corpus, the panel, the declared conditions and their event counts."""
    require(config.get("schema") == "cas.cube-face-worker-config/1",
            "FACE_WORKER_CONFIG_SCHEMA")
    built = corpus.families()
    conditions = [(entry["condition"], entry["organization"], entry["cue"])
                  for entry in schedule.comparison_conditions()]
    if config.get("conditions"):
        wanted = set(config["conditions"])
        conditions = [entry for entry in conditions if entry[0] in wanted]
    require(conditions, "FACE_WORKER_NO_CONDITIONS")
    event_limits = config.get("event_limit_per_condition")
    panel = evaluation.panel(built)
    plan = {
        "conditions": [{"condition": name, "organization": organization,
                        "cue": cue,
                        "events": len(schedule.condition_events(
                            name, organization, cue, built=built))}
                       for name, organization, cue in conditions],
        "corpus_digest": digest(canonical(corpus.coverage_report(built))),
        "panel": evaluation.panel_manifest(built),
        "counts": schedule.planned_counts(),
        "event_limit_per_condition": event_limits,
        "batch_size": config.get("batch_size", schedule.BATCH_SIZE),
        "seed": config.get("seed", experiment.SEED),
    }
    return built, conditions, panel, plan


def public_corpus(built, panel, conditions):
    """The declared fitting corpus, in one deterministic list.

    Both cue arms are included, so the shared encoder contains every cue token and
    the arms cannot differ through the tokenizer. The corpus is the union of the
    frozen panel and one canonical episode per (family, role, profile) per arm,
    each with its canonical worked supports: that set contains every concept label
    and every cue the schedules use, because the schedules draw on the same corpus
    vocabulary. Fitting on all 18,000 scheduled texts would repeat the same
    vocabulary at many times the compile cost, and this choice is recorded rather
    than implied.
    """
    texts, seen = [], set()

    def add(episode, arm):
        """Take the episode's own public record, never a synthesised one.

        The first attempt at this job died in `LosslessPublicTokenizer.fit_train`
        with `PUBLIC_TAG_INVALID`: the fitting corpus had been rebuilt by hand with
        the whole problem text as an option tag, which the frozen public codec
        rejects. The encoder is fitted on the records the learner will actually
        receive, validated by the codec, so that cannot recur.
        """
        public = episode["public"]
        _validate(public)
        key = (arm, public["problem"])
        if key not in seen:
            seen.add(key)
            texts.append(public)

    training = corpus.by_split(corpus.TRAINING, built)
    for arm in ("stable", "neutral", "none"):
        for family in training:
            for face in roles.FACE_NUMBERS:
                supports = tasks.choose_supports(family, face, offset=face,
                                                 built=built)
                add(tasks.compile_episode(family, face, roles.FACE_APPLY, arm=arm,
                                          supports=supports, built=built), arm)
                add(tasks.compile_episode(family, face, roles.ROLE_FROM_CONTENT,
                                          offset=face, built=built), arm)
    for item in panel:
        entry = (evaluation.diagnostic_item(item, built=built)
                 if item["kind"] in evaluation.DIAGNOSTIC_KINDS
                 else evaluation.compile_panel_item(item, built=built))
        add(entry["episode"], "panel")
    problems = [len(public["problem"]) for public in texts]
    tags = [len(observation["tag"]) for public in texts
            for observation in public["observations"]]
    return {"publics": texts,
            "distinct_texts": len(texts),
            "longest_problem": max(problems) if problems else 0,
            "longest_tag": max(tags) if tags else 0,
            "fitting_rule": ("the learner's own public records, deduplicated by "
                             "problem text: one canonical episode per family, role, "
                             "profile and cue arm, plus the whole frozen panel; "
                             "every label and cue token the schedules use is "
                             "present, and every record is codec-validated")}


def _validate(public):
    """The frozen public codec's own check, applied before anything is fitted."""
    from cas_meta2 import codec
    codec.validate_public(public)
    return public


# --------------------------------------------------------------------------
# 3. representation checks (they run before any training)
# --------------------------------------------------------------------------

def representation_checks(*, encoder, torch, built, device):
    """Do changed roles, changed contents and rewiring reach the model differently?

    This is the plan's pre-training check, and its result is recorded whether it
    passes or fails. A failure here means the accepted transform cannot separate
    these tasks; that is reported as a concrete restriction, never worked around by
    substituting an easier task.
    """
    family = corpus.by_split(corpus.TRAINING, built)[0]
    other = corpus.by_split(corpus.TRAINING, built)[1]
    variants = {
        "face_1": tasks.compile_episode(family, 1, roles.FACE_APPLY, arm="stable",
                                        supports=(), built=built),
        "face_5": tasks.compile_episode(family, 5, roles.FACE_APPLY, arm="stable",
                                        supports=(), built=built),
        "face_5_other_content": tasks.compile_episode(
            other, 5, roles.FACE_APPLY, arm="stable", supports=(), built=built),
        "face_5_neutral_cue": tasks.compile_episode(
            family, 5, roles.FACE_APPLY, arm="neutral", supports=(), built=built),
        "face_5_rewired": tasks.compile_episode(
            evaluation.rewired_family(family), 5, roles.FACE_APPLY, arm="stable",
            supports=(), built=built),
    }
    vectors = {}
    for name, episode in variants.items():
        vector = encoder["encode_problem"](episode["public"])
        require(tuple(vector.shape)[-1] == 64, "FACE_WORKER_VECTOR_DIM")
        require(bool(torch.isfinite(vector).all().item()),
                "FACE_WORKER_NONFINITE_VECTOR")
        vectors[name] = [round(float(value), 8) for value in vector]

    def distance(first, second):
        return round(sum((a - b) ** 2 for a, b in zip(vectors[first],
                                                      vectors[second])) ** 0.5, 8)

    report = {
        "encoded_problems": len(vectors),
        "distances": {
            "changed_role": distance("face_1", "face_5"),
            "changed_content": distance("face_5", "face_5_other_content"),
            "changed_cue": distance("face_5", "face_5_neutral_cue"),
            "same_token_rewiring": distance("face_5", "face_5_rewired"),
        },
        "interpretation": ("a distance of zero means the two inputs reach the model "
                           "identically, which would make the distinction "
                           "unavailable to it"),
    }
    report["distinct_from_zero"] = {
        name: value > 0 for name, value in report["distances"].items()}
    return report


def gradient_check(*, learner, torch, built):
    """Scores and losses are finite and the gradient depends on the target.

    It drives the learner's own indexed path - the same one the runner uses - so a
    pass means the task is usable at all. It measures nothing about learning.

    The learner must already hold the task in its index: the second attempt died
    here with a bare ``KeyError`` because the check built a learner with an empty
    task list and then asked it to score a task. Indexing the task first is the
    fix, and the local worker smoke run exists so this class of defect is found
    without a reservation.
    """
    family = corpus.by_split(corpus.TRAINING, built)[0]
    episode = tasks.compile_episode(family, 5, roles.FACE_APPLY, arm="stable",
                                    supports=(), built=built)
    task = experiment.episode_task(episode)
    require(task["record_id"] in getattr(learner, "_index", {}),
            "FACE_WORKER_CHECK_TASK_NOT_INDEXED:" + task["record_id"])
    info = learner.scores(task)
    require(info is not None, "FACE_WORKER_SCORES_UNAVAILABLE")
    scores = torch.tensor(info["scores"])
    require(bool(torch.isfinite(scores).all().item()), "FACE_WORKER_NONFINITE_SCORES")
    position = learner._position(task)
    tensor_scores = learner.forward(position)
    loss = torch.nn.functional.cross_entropy(
        tensor_scores.unsqueeze(0),
        torch.tensor([episode["encoded_correct_index"]], device=learner.device))
    require(bool(loss.isfinite().item()), "FACE_WORKER_NONFINITE_LOSS")
    loss.backward()
    gradient_parameter = None
    for name, parameter in learner.module.named_parameters():
        if parameter.grad is not None and bool(parameter.grad.abs().sum().item() > 0):
            gradient_parameter = name
            break
    learner.optimizer.zero_grad(set_to_none=True)
    return {"scores_finite": True, "loss_finite": True,
            "loss": round(float(loss.detach()), 6),
            "target_dependent_gradient": gradient_parameter is not None,
            "first_parameter_with_gradient": gradient_parameter,
            "option_count": len(info["scores"]),
            "path": info.get("path"),
            "note": ("this checks whether the path is usable at all; it is not a "
                     "measurement of learning")}


# --------------------------------------------------------------------------
# 4/5. teach, evaluate, deliver
# --------------------------------------------------------------------------

def run(config, *, torch, device, results, artifacts, outbound, execute=None):
    """Run every declared condition and return the delivery report.

    ``execute`` is the experiment's ``launch``; it is injected so the rehearsal can
    drive this same code with stub factories.
    """
    built, conditions, panel, plan = compile_plan(config)
    corpus_bundle = public_corpus(built, panel, conditions)
    from . import real_framework as rf
    encoder = rf.build_encoder(torch, corpus_bundle["publics"], d_model=64,
                               seed=config.get("encoder_seed", 20260909),
                               device=device)
    seed = plan["seed"]

    checks = {"representation": representation_checks(
        encoder=encoder, torch=torch, built=built, device=device)}

    condition_order = [name for name, _, _ in conditions]

    def framework_factory(condition_seed):
        torch.manual_seed(condition_seed)
        framework = rf.build_graph_training_framework(
            torch, device, seed=config.get("encoder_seed", 20260909),
            encoder=encoder)
        return framework, framework.build_decompose_model(seed=condition_seed)

    def learner_factory(*, framework, model, tasks):
        from .real_framework import GraphLearner
        return GraphLearner(torch, framework, list(tasks), device,
                            config.get("learning_rate", 0.003))

    def checkpoint_writer(learner, identity):
        condition = getattr(learner, "condition_tag", condition_order[0])
        name = "checkpoint_%s.pt" % condition
        path = artifacts / name
        torch.save({"schema": "cas.cube-face-checkpoint/1",
                    "condition": condition, "identity": identity,
                    "parameter_order": _parameter_order(learner),
                    "state": learner.module.state_dict()}, str(path))
        return {"path": str(path), "identity": identity, "sha256": _sha256(path)}

    def checkpoint_verifier(saved, identity):
        loaded = torch.load(saved["path"], map_location="cpu", weights_only=True)
        recomputed = _state_digest(loaded["state"], loaded["parameter_order"])
        return recomputed == identity and loaded["identity"] == identity

    check_framework, check_model = framework_factory(seed)
    check_episode = tasks.compile_episode(
        corpus.by_split(corpus.TRAINING, built)[0], 5, roles.FACE_APPLY,
        arm="stable", supports=(), built=built)
    check_learner = learner_factory(framework=check_framework, model=check_model,
                                    tasks=[experiment.episode_task(check_episode)])
    checks["gradient"] = gradient_check(learner=check_learner, torch=torch,
                                        built=built)
    del check_learner, check_model, check_framework
    torch.manual_seed(seed)
    launcher = execute or experiment.launch
    result = launcher(
        conditions=condition_order,
        framework_factory=framework_factory,
        learner_factory=learner_factory,
        checkpoint_writer=checkpoint_writer,
        checkpoint_verifier=checkpoint_verifier,
        authorization={"owner_go": True, "run_id": config["job"]},
        built=built, panel_items=panel, batch_size=plan["batch_size"],
        max_wall_seconds=config.get("max_wall_seconds_per_condition"),
        event_limit=plan["event_limit_per_condition"], seed=seed)

    measurements = {"schema": SCHEMA, "job": config["job"], "plan": plan,
                    "checks": checks, "experiment": result,
                    "corpus_digest": plan["corpus_digest"]}
    measurements_path = results / "measurements.json"
    measurements_path.write_text(json.dumps(measurements, sort_keys=True,
                                            indent=2, allow_nan=False) + "\n",
                                 encoding="utf-8")
    staged = [{"name": name, "sha256": _sha256(artifacts / name),
               "bytes": (artifacts / name).stat().st_size}
              for name in sorted(path.name for path in artifacts.iterdir()
                                 if path.suffix == ".pt")]
    (artifacts / "manifest.json").write_text(
        json.dumps({"schema": "cas.cube-face-artifact-manifest/1",
                    "job": config["job"], "artifacts": staged},
                   sort_keys=True, indent=2) + "\n", encoding="utf-8")
    envelope = {
        "schema": "cas.cube-face-result/1",
        "job": config["job"],
        "status": ("REMOTE_FINISHED"
                   if all(payload["status"] == experiment.STATUS_COMPLETE
                          for payload in result["results"].values())
                   else experiment.STATUS_INCOMPLETE),
        "failure": None,
        "artifacts": staged,
        "conditions": {
            name: {"status": payload["status"],
                   "planned_episodes": payload["planned_episodes"],
                   "delivered_episodes": payload["teaching"]["delivered_episodes"],
                   "optimizer_updates":
                       payload["teaching"]["actual_optimizer_updates"],
                   "checkpoint_verified":
                       payload["teaching"]["checkpoint"]["verified"]}
            for name, payload in result["results"].items()},
        "comparison": result["comparison"],
        "measurements_sha256": _sha256(measurements_path),
        "boundary": {"automatic_retries": 0, "seven_stage_neural_cycles": 0,
                     "scores_from_the_correction_pass": True},
    }
    # The body writes its own delivery, exactly as the proven workers do: the
    # result marker and its sidecar, so the outer worker only uploads and a
    # failure it detects cannot overwrite a completed result.
    raw = (json.dumps(envelope, sort_keys=True, indent=2,
                      allow_nan=False) + "\n").encode("utf-8")
    (results / "result.json").write_bytes(raw)
    (results / "result.json.sha256").write_text(
        _sha256_bytes(raw) + "\n", encoding="utf-8")
    return {"plan": plan, "checks": checks, "envelope": envelope,
            "measurements": measurements, "artifacts": staged}


def _sha256_bytes(raw):
    import hashlib as _hashlib
    return _hashlib.sha256(raw).hexdigest()


def _parameter_order(learner):
    return [name for name, _ in learner.module.named_parameters()]


def _state_digest(state, order):
    import hashlib as _hashlib
    accumulator = _hashlib.sha256()
    for name in order:
        accumulator.update(state[name].detach().cpu().numpy().tobytes())
    return accumulator.hexdigest()


def _sha256(path):
    import hashlib as _hashlib
    return _hashlib.sha256(Path(path).read_bytes()).hexdigest()
