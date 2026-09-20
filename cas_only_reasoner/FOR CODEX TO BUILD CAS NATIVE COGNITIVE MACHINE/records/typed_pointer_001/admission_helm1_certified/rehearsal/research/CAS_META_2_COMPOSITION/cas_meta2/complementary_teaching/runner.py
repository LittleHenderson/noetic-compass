"""Real CUDA-only opt-in course, unchanged registered recurrent learner/core.

Heavy libraries are acquired only after config/data/checkpoint validation. Pure
tests exercise the compiler/executor without importing torch or loading models.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import random
import time

from . import IMPLEMENTATION_ID, PROFILE_ID
from .course import (CONDITIONS, SEEDS, TARGET_FIELDS, compile_complementary_course,
                     digest, public_identity, require, run_complementary_course, task_index)
from .data import validate_manifest

SCHEMA = "cas.complementary-result/0.1"
CHECKPOINT_SCHEMA = "cas.complementary-checkpoint/0.1"
DATA_PATH = "records/complementary_teaching_001/preparation_20260916/data_manifest.json"
INITIAL_PATH = ("records/recurrent_cjt_001/receipt_cas-meta2-rdcjt-20260912152001-abf38e1e/"
                "rescued_evidence/results/artifacts/checkpoint_recurrent.pt")
MAX_WALL_SECONDS = 3000
MAX_STORAGE_BYTES = 1024 ** 3
MAX_GPU_MEMORY_BYTES = 20 * 1024 ** 3


def file_sha(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
    path.write_bytes(raw)
    return {"name": path.name, "bytes": len(raw), "sha256": sha256(raw).hexdigest()}


def public_task(task):
    return {key: deepcopy(value) for key, value in task.items() if key not in TARGET_FIELDS}


def _state_digest(torch, value):
    if torch.is_tensor(value):
        return {"shape": list(value.shape), "dtype": str(value.dtype),
                "sha256": sha256(value.detach().cpu().numpy().tobytes()).hexdigest()}
    if isinstance(value, dict):
        return {str(key): _state_digest(torch, item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_state_digest(torch, item) for item in value]
    return value


def _rng(torch):
    return {"python": random.getstate(), "cpu": torch.get_rng_state(),
            "cuda": torch.cuda.get_rng_state_all()}


def _restore_rng(torch, state):
    random.setstate(state["python"])
    torch.set_rng_state(state["cpu"].cpu())
    torch.cuda.set_rng_state_all([value.cpu() for value in state["cuda"]])


def guarded_evaluate(learner, panels):
    """Seal every prediction before evaluator-only target access; zero updates."""
    torch = learner.torch
    state = _rng(torch)
    depth, training = learner.depth, learner.module.training
    weights = learner.checkpoint_identity()
    optimizer = digest(_state_digest(torch, learner.optimizer.state_dict()))
    counters = (learner.transformation_calls, learner.questions_answered)
    started = time.monotonic()
    sealed = {}
    learner.set_depth(8)
    learner.module.eval()
    try:
        with torch.no_grad():
            for name, tasks in panels.items():
                sealed[name] = []
                for task in tasks:
                    public = public_task(task)
                    if public["record_id"] in learner._index:
                        scores = learner.forward(learner._position(public))
                    else:
                        _, slots = learner.framework.encoder["encode"](public["public"])
                        value = learner.value_at_depth(public=public["public"])
                        zero = torch.zeros_like(value)
                        scores = torch.stack([torch.dot(value, learner._sum(ids) if ids else zero)
                                              for ids in learner._content_ids(slots)])
                    require(bool(torch.isfinite(scores).all()), "COMPLEMENTARY_EVAL_NONFINITE")
                    selected = int(torch.argmax(scores).item())
                    sealed[name].append({"record_id": task["record_id"],
                        "family_id": task["family_id"], "op": task["op"],
                        "semantic_question_id": task.get("semantic_question_id", task["record_id"]),
                        "public_input_sha256": public_identity(task), "scores": [float(v) for v in scores],
                        "selected_index": selected, "prediction": public["encoded_options"][selected]})
                    for key in ("canonical_record_id", "perspective_pair_kind", "perspective_view",
                                "perspective_pair_id", "query_arguments", "perspective", "audit_face"):
                        if key in task:
                            sealed[name][-1][key] = deepcopy(task[key])
        seal = digest(sealed)
        # This join is deliberately outside/below the entire prediction loop.
        for name, rows in sealed.items():
            for row, task in zip(rows, panels[name]):
                row.update({"expected": task["correct"], "correct": row["prediction"] == task["correct"]})
        require(learner.checkpoint_identity() == weights, "COMPLEMENTARY_MONITOR_WEIGHT_MUTATION")
        require(digest(_state_digest(torch, learner.optimizer.state_dict())) == optimizer,
                "COMPLEMENTARY_MONITOR_OPTIMIZER_MUTATION")
        return {"prediction_seal_sha256": seal, "rows": sealed, "weight_identity": weights,
                "optimizer_updates": 0, "depth": 8,
                "actual_core_calls": learner.transformation_calls - counters[0],
                "actual_questions": learner.questions_answered - counters[1],
                "elapsed_seconds": time.monotonic() - started}
    finally:
        learner.set_depth(depth)
        learner.module.train(training)
        learner.transformation_calls, learner.questions_answered = counters
        _restore_rng(torch, state)


def batch_step(learner, tasks):
    """Same inherited forward/readout/AdamW, explicit teacher-release boundary.

The old recurrent_batch_step retains predictions after constructing the loss.
This small adapter records argmax from the actual final forward BEFORE looking
up a private target; it leaves the recurrent implementation unchanged.
"""
    torch = learner.torch
    learner.module.train()
    learner.optimizer.zero_grad(set_to_none=True)
    losses, episodes = [], []
    for task in tasks:
        scores = learner.forward(learner._position(task))
        require(bool(torch.isfinite(scores).all()), "COMPLEMENTARY_NONFINITE_SCORE")
        selected = int(torch.argmax(scores).item())
        row = {"scores": [float(value.detach()) for value in scores],
               "selected_index": selected, "selected": task["encoded_options"][selected],
               "option_count": int(scores.shape[0]), "prediction_before_target": True}
        correct = task["encoded_correct_index"]
        loss = torch.nn.functional.cross_entropy(scores.unsqueeze(0),
                      torch.tensor([correct], device=learner.device))
        require(bool(torch.isfinite(loss)), "COMPLEMENTARY_NONFINITE_LOSS")
        row.update({"correct_index": correct, "loss": float(loss.detach())})
        episodes.append(row)
        losses.append(loss)
    total = sum(losses) / len(losses)
    total.backward()
    require(all(parameter.grad is None or bool(torch.isfinite(parameter.grad).all())
                for parameter in learner.module.parameters()), "COMPLEMENTARY_NONFINITE_GRADIENT")
    learner.optimizer.step()
    if learner.accounting is not None:
        learner.accounting.charge(depth=learner.depth, samples=len(tasks))
        learner.accounting.update()
    return {"optimizer_steps": 1, "batch_size": len(tasks), "depth": learner.depth,
            "mean_loss": float(total.detach()), "episodes": episodes}


def numerical_checks(learner, schedule):
    """No optimizer updates. Gradients must reach every one of eight shared passes."""
    torch = learner.torch
    before = learner.checkpoint_identity()
    calls_before = learner.transformation_calls
    rows = []
    for role in ("COMPONENT", "WHOLE"):
        task = next(t for b in schedule["batches"] for t in b["tasks"] if t["teaching_role"] == role)
        outputs = []
        def hook(_module, _inputs, output):
            output.retain_grad()
            outputs.append(output)
        handle = learner.module.register_forward_hook(hook)
        learner.optimizer.zero_grad(set_to_none=True)
        learner.set_depth(8)
        try:
            scores = learner.forward(learner._position(task))
            loss = torch.nn.functional.cross_entropy(scores.unsqueeze(0),
                       torch.tensor([task["encoded_correct_index"]], device=learner.device))
            loss.backward()
            connected = len(outputs) == 8 and all(output.grad is not None
                            and bool(torch.isfinite(output.grad).all())
                            and float(output.grad.abs().sum()) > 0 for output in outputs)
            require(connected, "COMPLEMENTARY_FULL_UNROLL_GRADIENT:" + role)
            rows.append({"role": role, "passes": len(outputs), "connected": connected})
        finally:
            handle.remove()
            learner.optimizer.zero_grad(set_to_none=True)
    from ..recurrent_cjt.learner import state_isolation_check
    with torch.no_grad():
        isolation = state_isolation_check(learner=learner, position=0, other_position=1)
    require(isolation["repeatable"] and isolation["order_independent"], "COMPLEMENTARY_QUESTION_STATE_LEAK")
    require(learner.checkpoint_identity() == before, "COMPLEMENTARY_NUMERICAL_CHECK_MUTATED_WEIGHTS")
    return {"status": "PASS", "optimizer_updates": 0, "rows": rows,
            "state_isolation": isolation, "actual_core_calls": learner.transformation_calls - calls_before}


def checkpoint_save(path, learner, schedule, cursor, rows, data_sha256, *, initial_sha256):
    path = Path(path)
    payload = {"schema": CHECKPOINT_SCHEMA, "model": learner.module.state_dict(),
               "optimizer": learner.optimizer.state_dict(), "rng": _rng(learner.torch),
               "cursor": cursor, "rows": rows, "schedule_sha256": schedule["schedule_sha256"],
               "data_sha256": data_sha256, "initial_sha256": initial_sha256,
               "profile": PROFILE_ID, "depth": learner.depth,
               "encoder": learner.complementary_encoder_state,
               "runtime_binding": learner.complementary_runtime_binding,
               "weight_identity": learner.checkpoint_identity(),
               "global_learning_rate_rule": "constant 0.003 over global committed cursor"}
    temporary = path.with_suffix(".pending")
    learner.torch.save(payload, str(temporary))
    temporary.replace(path)
    return {"name": path.name, "sha256": file_sha(path), "bytes": path.stat().st_size}


def checkpoint_restore(path, learner, schedule, *, data_sha256, initial_sha256):
    payload = learner.torch.load(str(path), map_location=learner.device, weights_only=True)
    for key, expected in {"schema": CHECKPOINT_SCHEMA, "schedule_sha256": schedule["schedule_sha256"],
                          "data_sha256": data_sha256, "initial_sha256": initial_sha256,
                          "profile": PROFILE_ID}.items():
        require(payload.get(key) == expected, "COMPLEMENTARY_RESTORE_IDENTITY:" + key)
    require(len(payload["rows"]) == payload["cursor"], "COMPLEMENTARY_RESTORE_CURSOR")
    require(payload["runtime_binding"] == learner.complementary_runtime_binding,
            "COMPLEMENTARY_RESTORE_RUNTIME_BINDING")
    retained_encoder = payload["encoder"]
    current_encoder = learner.complementary_encoder_state
    require(retained_encoder["vocabulary"] == current_encoder["vocabulary"] and
            learner.torch.equal(retained_encoder["projection"], current_encoder["projection"]),
            "COMPLEMENTARY_RESTORE_ENCODER")
    learner.module.load_state_dict(payload["model"], strict=True)
    learner.optimizer.load_state_dict(payload["optimizer"])
    learner.set_depth(payload["depth"])
    _restore_rng(learner.torch, payload["rng"])
    require(learner.checkpoint_identity() == payload["weight_identity"], "COMPLEMENTARY_RESTORE_WEIGHTS")
    return payload


def resume_complementary_course(*, checkpoint_path, checkpoint_sha256, learner, schedule,
                                data_sha256, initial_sha256, observer=None, checkpoint=None,
                                deadline=None):
    """Explicit recovery from one hash-bound complete bundle, with no duplicate update."""
    require(file_sha(checkpoint_path) == checkpoint_sha256, "COMPLEMENTARY_RESUME_FILE_HASH")
    restored = checkpoint_restore(checkpoint_path, learner, schedule,
        data_sha256=data_sha256, initial_sha256=initial_sha256)
    return run_complementary_course(learner=learner, schedule=schedule, batch_step=batch_step,
        observer=observer, checkpoint=checkpoint, deadline=deadline,
        next_cursor=restored["cursor"], prior_rows=restored["rows"])


def validate_config(config, pilot):
    require(config.get("candidate") == IMPLEMENTATION_ID, "COMPLEMENTARY_OPT_IN_REQUIRED")
    require(config.get("execution_enabled") is True, "COMPLEMENTARY_EXECUTION_DISABLED")
    require(config.get("learning_rate") == 0.003, "COMPLEMENTARY_LEARNING_RATE_FROZEN")
    require(config.get("max_wall_seconds") == MAX_WALL_SECONDS, "COMPLEMENTARY_WALL_FROZEN")
    for field, relative in (("data_file_sha256", DATA_PATH), ("initial_checkpoint_sha256", INITIAL_PATH)):
        require(config.get(field) == file_sha(Path(pilot) / relative), "COMPLEMENTARY_INPUT_HASH:" + field)
    data = validate_manifest(json.loads((Path(pilot) / DATA_PATH).read_bytes()))
    require(config.get("data_sha256") == data["data_sha256"], "COMPLEMENTARY_DATA_IDENTITY")
    return data


def run(config, *, results, artifacts, root=None, public_transform_factory=None, panel_transform=None):
    """Nine independent courses on one authorized GPU job; no local CPU fallback."""
    pilot = Path(root) / "research/CAS_META_2_COMPOSITION" if root else Path(__file__).resolve().parents[2]
    data = validate_config(config, pilot)
    from ..teaching_cycle.gpu_adapter import _cuda
    torch, device = _cuda()
    require(str(device).startswith("cuda"), "COMPLEMENTARY_CUDA_REQUIRED")
    from ..recurrent_cjt.learner import build_recurrent_learner
    from ..graph_teaching import real_framework as rf, trainer, face_worker, face_evaluation
    from ..graph_teaching.curriculum_experiment import encoder_state
    from ..graph_teaching import face_schedule
    from .evaluation import analyze
    started = time.monotonic()
    deadline = started + MAX_WALL_SECONDS
    artifacts = Path(artifacts)
    artifacts.mkdir(parents=True, exist_ok=True)
    conditions = tuple(config.get("comparison_conditions", CONDITIONS))
    require(conditions == CONDITIONS or public_transform_factory is not None,
            "COMPLEMENTARY_CUSTOM_CONDITIONS_REQUIRE_BOUND_TRANSFORM")
    source_conditions = [(x["condition"], x["organization"], x["cue"])
                         for x in face_schedule.comparison_conditions()]
    corpus = face_worker.public_corpus(None, face_evaluation.panel(), source_conditions)
    encoder = rf.build_encoder(torch, corpus["publics"], d_model=64, seed=20260909, device=device)
    retained_encoder = encoder_state(torch, encoder)
    runtime_binding = {"source_sha": config.get("source_sha"), "encoder_corpus_sha256": digest(corpus),
        "recurrence_profile": "cas.cjt.compute.recurrent-depth/0.1", "scoring": "frozen content-only option-sum dot-product",
        "files": {str(path.relative_to(pilot)).replace("\\", "/"): file_sha(path) for path in
            [pilot / "cas_meta2/recurrent_cjt/recurrence.py", pilot / "cas_meta2/recurrent_cjt/learner.py",
             pilot / "cas_meta2/graph_teaching/real_framework.py", pilot / "cas_meta2/features_v2.py"]}}
    initial = torch.load(str(pilot / INITIAL_PATH), map_location=device, weights_only=True)
    require(initial["schema"] == "cas.recurrent-cjt-checkpoint/1" and initial["arm"] == "recurrent",
            "COMPLEMENTARY_INITIAL_CHECKPOINT_SCHEMA")
    development = {k: v for k, v in data["panels"].items() if k.startswith("development_")}
    final = {k: v for k, v in data["panels"].items() if k.startswith("final_")}
    if panel_transform is not None:
        additions = panel_transform(deepcopy(final["final_application"]))
        require(isinstance(additions, dict) and not set(additions) & set(final), "COMPLEMENTARY_EXTRA_PANEL_NAMES")
        final.update(additions)
    report = {"schema": SCHEMA, "job": config["job"], "candidate": IMPLEMENTATION_ID,
              "status": "TEACHING_INCOMPLETE", "courses": [], "data_sha256": data["data_sha256"],
              "initial_sha256": config["initial_checkpoint_sha256"], "encoder_corpus_digest": digest(corpus),
              "condition_labels": list(conditions), "automatic_retries": 0,
              "boundary": "Candidate research only; no accepted-model mutation or general CAS advantage claim."}
    try:
        for seed in SEEDS:
            for condition in conditions:
                require(time.monotonic() < deadline, "COMPLEMENTARY_ROOT_DEADLINE")
                transform = public_transform_factory(condition) if public_transform_factory else None
                parent = CONDITIONS[0] if transform is not None else condition
                schedule = compile_complementary_course(seed, parent, public_transform=transform)
                check_schedule = (schedule if parent == CONDITIONS[0] else
                                  compile_complementary_course(seed, CONDITIONS[0]))
                torch.manual_seed(seed)
                random.seed(seed)
                framework = rf.build_graph_training_framework(torch, device, seed=seed, encoder=encoder)
                framework.module.load_state_dict(initial["state"], strict=True)
                scope = trainer.scope_parameters(framework, framework.module)
                before = trainer.parameter_snapshot(framework, framework.module)
                indexed = {task["record_id"]: public_task(task) for task in
                           task_index(check_schedule) + task_index(schedule)}
                learner = build_recurrent_learner(torch, framework, list(indexed.values()), device, 0.003)
                learner.complementary_encoder_state = retained_encoder
                learner.complementary_runtime_binding = runtime_binding
                require(learner.checkpoint_identity() == initial["identity"], "COMPLEMENTARY_INITIAL_WEIGHTS")
                label = "%s_%d" % (condition, seed)
                numerical = numerical_checks(learner, check_schedule)
                baseline = guarded_evaluate(learner, {key: final[key] for key in
                                           ("final_components", "final_earlier_skills")})
                observations = []
                def save(learner, cursor, rows, _kind):
                    checkpoint_save(artifacts / (label + "_latest.pt"), learner, schedule, cursor, rows,
                                    data["data_sha256"], initial_sha256=config["initial_checkpoint_sha256"])
                current_rows = []
                def observe(learner, point):
                    measured = guarded_evaluate(learner, development)
                    observations.append({**point, **measured})
                    checkpoint_save(artifacts / (label + "_monitor_%03d.pt" % point["cursor"]),
                        learner, schedule, point["cursor"], list(current_rows), data["data_sha256"],
                        initial_sha256=config["initial_checkpoint_sha256"])
                def update_save(learner, cursor, rows, kind):
                    current_rows[:] = rows
                    save(learner, cursor, rows, kind)
                    require(torch.cuda.max_memory_allocated() <= MAX_GPU_MEMORY_BYTES,
                            "COMPLEMENTARY_GPU_MEMORY_BOUND")
                    require(sum(p.stat().st_size for p in artifacts.iterdir() if p.is_file()) <= MAX_STORAGE_BYTES,
                            "COMPLEMENTARY_STORAGE_BOUND")
                training_calls_before = learner.transformation_calls
                outcome = run_complementary_course(learner=learner, schedule=schedule, batch_step=batch_step,
                              observer=observe, checkpoint=update_save, deadline=deadline)
                training_calls_actual = learner.transformation_calls - training_calls_before
                after = guarded_evaluate(learner, final)
                final_path = artifacts / (label + "_final.pt")
                checkpoint_save(final_path, learner, schedule, outcome["next_cursor"], outcome["rows"],
                                data["data_sha256"], initial_sha256=config["initial_checkpoint_sha256"])
                checkpoint_restore(final_path, learner, schedule, data_sha256=data["data_sha256"],
                                   initial_sha256=config["initial_checkpoint_sha256"])
                reloaded = guarded_evaluate(learner, final)
                require(after["rows"] == reloaded["rows"] and
                        after["prediction_seal_sha256"] == reloaded["prediction_seal_sha256"],
                        "COMPLEMENTARY_FINAL_RELOAD_PREDICTIONS")
                contained = trainer.containment_report(before, trainer.parameter_snapshot(framework, framework.module), scope["allowed"])
                require(contained["contained"], "COMPLEMENTARY_PARAMETER_SCOPE")
                course_result = {"condition": condition, "seed": seed, "schedule_sha256": schedule["schedule_sha256"],
                                 "counts": schedule["counts"], "training": outcome, "initial": baseline,
                                 "final": after, "observations": observations, "numerical": numerical,
                                 "containment": contained, "reload_equal": True,
                                 "actual_accounting": {"training_core_calls": training_calls_actual,
                                     "numerical_core_calls": numerical["actual_core_calls"],
                                     "initial_retention_core_calls": baseline["actual_core_calls"],
                                     "monitor_core_calls": sum(row["actual_core_calls"] for row in observations),
                                     "final_core_calls": after["actual_core_calls"],
                                     "reload_core_calls": reloaded["actual_core_calls"]}}
                report["courses"].append(course_result)
                write_json(artifacts / (label + "_course.json"), course_result)
                require(outcome["status"] == "TEACHING_COMPLETE", "COMPLEMENTARY_ROOT_DEADLINE")
                del learner, framework
        report["status"] = "COMPLEMENTARY_MEASURED"
        report["analysis"] = analyze(report) if conditions == CONDITIONS else {"status": "SEPARATE_PERSPECTIVE_ANALYSIS_REQUIRED"}
    except Exception as error:
        report["failure"] = {"type": type(error).__name__, "message": str(error)}
        report["status"] = "TEACHING_INCOMPLETE"
        raise
    finally:
        report["elapsed_seconds"] = time.monotonic() - started
        write_json(artifacts / "complementary_report.json", report)
        entries = [{"name": path.name, "sha256": file_sha(path), "bytes": path.stat().st_size}
                   for path in sorted(artifacts.iterdir()) if path.is_file() and path.name != "manifest.json"]
        write_json(artifacts / "manifest.json", {"schema": SCHEMA, "artifacts": entries})
        envelope = {"schema": SCHEMA, "job": config["job"], "status": report["status"],
                    "artifacts": entries, "courses": len(report["courses"]), "failure": report.get("failure")}
        receipt = write_json(Path(results) / "result.json", envelope)
        (Path(results) / "result.json.sha256").write_text(receipt["sha256"] + "\n", encoding="utf-8")
    return {**envelope, "arms": list(conditions)}
