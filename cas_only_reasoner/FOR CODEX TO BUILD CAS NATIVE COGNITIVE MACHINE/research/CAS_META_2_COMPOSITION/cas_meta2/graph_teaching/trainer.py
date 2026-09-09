"""Targeted ^6 specialist training mode for the graph-first candidate.

Trains the registered decompose module (contract
``cas.cjt.operation.^6.decompose/0.2``) on the whole-part graph lessons,
keeping ONLY the ``operator.^6`` plasticity group trainable. Every answer
comes from the deterministic checker; the graph never contains an answer edge.

Pure phase: this module imports nothing heavy at module level. The real
torch/cas_cjt path is built lazily inside ``real_framework()`` and is
GPU-fail-closed; the pure tests inject fakes and never reach it.

Frozen budget (declared here, enforced by the AWS authority when a run is
authorized): learning_rate 0.003, max_optimizer_steps 64,
max_wall_seconds 600.0.
"""
from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass
from hashlib import sha256

from . import lessons, reference
from .graph import canonical, digest, require
from .real_framework import (TARGET_CONTRACT_ID, TARGET_PLASTICITY_ROLE)

MODE_SCHEMA = "cas-meta2-graph-teaching-training/1"
CONDITION_KIND = "prompt_framing_only"  # not a CASformer-vs-generic architecture comparison

FROZEN_LEARNING_RATE = 0.003
FROZEN_MAX_OPTIMIZER_STEPS = 64
FROZEN_MAX_WALL_SECONDS = 600.0
TOTAL_ARMS = 2  # cas + generic; budget below is PER ARM

WHOLE_PART_OPS = frozenset(lessons.WHOLE_PART_OPS)
TRAIN_SPLITS = ("train", "practice")
SEALED_SPLITS = ("validation", "test")


@dataclass(frozen=True)
class TrainingBudget:
    learning_rate: float = FROZEN_LEARNING_RATE
    max_optimizer_steps: int = FROZEN_MAX_OPTIMIZER_STEPS
    max_wall_seconds: float = FROZEN_MAX_WALL_SECONDS

    def validate(self):
        require(self.learning_rate == FROZEN_LEARNING_RATE, "BUDGET_LEARNING_RATE_FROZEN")
        require(self.max_optimizer_steps == FROZEN_MAX_OPTIMIZER_STEPS,
                "BUDGET_MAX_OPTIMIZER_STEPS_FROZEN")
        require(self.max_wall_seconds == FROZEN_MAX_WALL_SECONDS,
                "BUDGET_MAX_WALL_SECONDS_FROZEN")
        return self


def training_records(seed):
    """Train + practice, whole-part ops only. Sealed splits are NEVER read."""
    dataset = lessons.build_dataset(seed=seed)
    records = []
    for split in TRAIN_SPLITS:
        for record in dataset[split]:
            if record["family"] == "whole_part" and record["op"] in WHOLE_PART_OPS:
                records.append(record)
    require(records, "TRAINING_RECORDS_REQUIRED")
    return records


def select_target(framework):
    """Return (registration, contract) for the decompose operation."""
    registrations = list(framework.operation_registrations)
    matches = [r for r in registrations if r.contract_id == TARGET_CONTRACT_ID]
    require(len(matches) == 1, "TARGET_CONTRACT_NOT_UNIQUE")
    contract = framework.contract_for(matches[0].contract_id)
    require(TARGET_PLASTICITY_ROLE in contract.plasticity_groups,
            "TARGET_PLASTICITY_ROLE_NOT_ADMITTED")
    return matches[0], contract


def scope_parameters(framework, model):
    """Freeze everything except the admit-listed operator.^6 group."""
    _registration, contract = select_target(framework)
    allowed = set(framework.resolve_plasticity_groups(
        model, TARGET_PLASTICITY_ROLE, contract))
    require(allowed, "PLASTICITY_ALLOWLIST_EMPTY")
    names = []
    for name, parameter in model.named_parameters():
        parameter.requires_grad_(name in allowed)
        names.append(name)
    frozen = [name for name in names if name not in allowed]
    return {"allowed": sorted(allowed), "frozen": sorted(frozen),
            "contract_id": TARGET_CONTRACT_ID, "role": TARGET_PLASTICITY_ROLE}


def parameter_snapshot(framework, model):
    """Digest of every parameter; containment compares snapshots."""
    snapshot = {}
    for name, parameter in model.named_parameters():
        snapshot[name] = sha256(framework.tensor_bytes(parameter)).hexdigest()
    return snapshot


def containment_report(before, after, allowed):
    """Permitted updates only: no digest outside the allowlist may change."""
    changed = sorted(name for name in before if before[name] != after[name])
    permitted = sorted(set(changed) & set(allowed))
    forbidden = sorted(set(changed) - set(allowed))
    return {"contained": not forbidden, "permitted_changes": permitted,
            "forbidden_changes": forbidden, "total_changed": len(changed)}


def make_task(record, arm):
    """One structured prediction task; the answer comes from the record's
    checker-derived 'correct' field, never from the graph itself."""
    require(arm in ("cas", "generic"), "ARM_UNKNOWN")
    return {"record_id": record["record_id"], "op": record["op"],
            "graph": record["graph"], "question": record["question"],
            "options": record["options"], "correct": record["correct"],
            "prompt": record["framings"][arm],
            "reference": record["reference"]}


def run_training(learner, records, arm, budget, wall_clock=time.monotonic):
    """Bounded updates with before/after per-op losses and lesson exposure.

    Lesson exposure reports how many records and how many updates each
    operation actually received — an optimizer step is NOT a complete
    teaching cycle, and the report says so explicitly.
    """
    tasks = [make_task(record, arm) for record in records]
    ops = sorted({task["op"] for task in tasks})
    before = {op: learner.eval_loss(op, tasks) for op in ops}
    completed = 0
    updates_by_op = {op: 0 for op in ops}
    deadline = wall_clock() + budget.max_wall_seconds
    while completed < budget.max_optimizer_steps and wall_clock() < deadline:
        task = tasks[completed % len(tasks)]
        learner.step(task)
        updates_by_op[task["op"]] += 1
        completed += 1
    after = {op: learner.eval_loss(op, tasks) for op in ops}
    exposure = {"records_by_op": {op: sum(1 for task in tasks if task["op"] == op)
                                  for op in ops},
                "updates_by_op": updates_by_op,
                "boundary": ("An optimizer step is a single correction on one "
                             "record, not a complete teaching cycle.")}
    return {"before_loss": before, "after_loss": after,
            "completed_updates": completed, "lesson_exposure": exposure,
            "checkpoint_identity": learner.checkpoint_identity(),
            "automatic_retries": 0}


def real_framework():
    """Lazy, GPU-fail-closed construction for the AWS path only.

    Imports torch through the teaching gpu_adapter (CUDA required, exactly one
    visible GPU), fits the frozen public tokenizer on the lesson prompts, and
    builds the candidate decompose module through
    ``real_framework.build_graph_training_framework``. Fails closed with an
    explicit code at every missing piece — never a silent fallback.
    """
    from ..teaching_cycle import gpu_adapter  # noqa: F401  (imports torch)
    from .adapter import public_records
    from .real_framework import build_encoder, build_graph_training_framework
    torch, device = gpu_adapter._cuda()
    records = training_records(20260909)
    publics = [public_records(record, arm)["public"]
               for record in records for arm in ("cas", "generic")]
    encoder = build_encoder(torch, publics, d_model=64, seed=20260909,
                            device=device)
    framework = build_graph_training_framework(torch, device, seed=20260909,
                                               encoder=encoder)
    return framework, records


def launch(*, run_id, arm, seed=20260909, framework=None, model=None,
           learner_factory=None, learning_rate=FROZEN_LEARNING_RATE,
           max_optimizer_steps=FROZEN_MAX_OPTIMIZER_STEPS,
           max_wall_seconds=FROZEN_MAX_WALL_SECONDS):
    """Run the targeted training exactly once; report scope + containment."""
    require(type(run_id) is str and run_id, "RUN_ID_REQUIRED")
    require(arm in ("cas", "generic"), "ARM_UNKNOWN")
    budget = TrainingBudget(learning_rate=learning_rate,
                            max_optimizer_steps=max_optimizer_steps,
                            max_wall_seconds=max_wall_seconds).validate()
    if framework is None or model is None:
        framework, real_records = real_framework()
        model = framework.build_decompose_model(seed=seed)
        records_override = real_records
    else:
        records_override = None
    require(learner_factory is not None, "LEARNER_FACTORY_REQUIRED")
    records = records_override if records_override is not None else training_records(seed)
    before = parameter_snapshot(framework, model)
    scope = scope_parameters(framework, model)
    learner = learner_factory(model, arm=arm, learning_rate=budget.learning_rate)
    training = run_training(learner, records, arm, budget)
    after = parameter_snapshot(framework, model)
    report = {"schema": MODE_SCHEMA, "run_id": run_id,
              "condition": {"arm": arm, "kind": CONDITION_KIND,
                            "note": ("Both conditions share the same graphs, "
                                     "options, and reference answers; only the "
                                     "prompt framing differs. This is not the "
                                     "CASformer-vs-generic-network comparison.")},
              "seed": seed,
              "target": {"contract_id": TARGET_CONTRACT_ID,
                         "plasticity_role": TARGET_PLASTICITY_ROLE},
              "scope": scope, "containment": containment_report(before, after,
                                                                scope["allowed"]),
              "training": training, "budget": {
                  "per_arm": {"learning_rate": budget.learning_rate,
                              "max_optimizer_steps": budget.max_optimizer_steps,
                              "max_wall_seconds": budget.max_wall_seconds},
                  "total": {"arms": TOTAL_ARMS,
                            "optimizer_steps": TOTAL_ARMS * budget.max_optimizer_steps,
                            "wall_seconds": TOTAL_ARMS * budget.max_wall_seconds}},
              "claims": {"specialist_claimed": False,
                         "sealed_splits_read": False,
                         "answer_edges_present": False}}
    return report


def prediction_input(task):
    """Answer-free module input: the prediction is made BEFORE any answer is
    available to the module. The checker may supply corrections during
    teaching, never during inference."""
    return {key: value for key, value in task.items() if key != "correct"}


def evaluate_sealed(learner, seed=20260909, splits=SEALED_SPLITS):
    """Post-training evaluator: reads ONLY the sealed validation/test splits.

    Predictions are recorded (sealed) BEFORE the answers are consulted; each
    sealed prediction record contains no answer field. Tasks are the SAME
    public-record kind the learner consumes (attempt 008's preserved error:
    make_task inputs lacked the learner's 'public' encoding).
    """
    from .adapter import public_records
    dataset = lessons.build_dataset(seed=seed)
    tasks = []
    for split in splits:
        for record in dataset[split]:
            if record["family"] != "whole_part" or record["op"] not in WHOLE_PART_OPS:
                continue
            tasks.append((split, public_records(record, arm="generic")))
    sealed = [{"record_id": task["record_id"], "split": split, "op": task["op"],
               "predicted": learner.predict(prediction_input(task))}
              for split, task in tasks]
    metrics = {}
    for (split, task), prediction in zip(tasks, sealed):
        key = split + ":" + task["op"]  # str key: json-serializable
        bucket = metrics.setdefault(key, {"attempted": 0, "correct": 0})
        bucket["attempted"] += 1
        if prediction["predicted"] == task["correct"]:
            bucket["correct"] += 1
    return {"sealed_predictions": sealed, "per_split_op": metrics,
            "boundary": ("post-training sealed-split evaluation only; predictions "
                         "sealed before answers were consulted"),
            "training_path_never_reads_sealed": True}
