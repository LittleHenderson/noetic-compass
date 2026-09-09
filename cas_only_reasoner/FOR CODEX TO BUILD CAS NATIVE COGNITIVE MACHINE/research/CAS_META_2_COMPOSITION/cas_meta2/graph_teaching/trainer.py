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

MODE_SCHEMA = "cas-meta2-graph-teaching-training/1"
TARGET_CONTRACT_ID = "cas.cjt.operation.^6.decompose/0.2"
TARGET_PLASTICITY_ROLE = "operator.^6"

FROZEN_LEARNING_RATE = 0.003
FROZEN_MAX_OPTIMIZER_STEPS = 64
FROZEN_MAX_WALL_SECONDS = 600.0

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
    """Bounded updates with before/after per-op losses. Never reads sealed splits."""
    tasks = [make_task(record, arm) for record in records]
    ops = sorted({task["op"] for task in tasks})
    before = {op: learner.eval_loss(op, tasks) for op in ops}
    completed = 0
    deadline = wall_clock() + budget.max_wall_seconds
    while completed < budget.max_optimizer_steps and wall_clock() < deadline:
        learner.step(tasks[completed % len(tasks)])
        completed += 1
    after = {op: learner.eval_loss(op, tasks) for op in ops}
    return {"before_loss": before, "after_loss": after,
            "completed_updates": completed,
            "checkpoint_identity": learner.checkpoint_identity(),
            "automatic_retries": 0}


def real_framework():
    """Lazy, GPU-fail-closed construction for the AWS path only.

    Imports torch through the teaching gpu_adapter (CUDA required, exactly one
    visible GPU) and the cas_cjt governed-learning machinery. The
    ``build_graph_training_framework`` hook is the authorized next build step
    (see the AWS authorization request); until it exists this fails closed
    with an explicit code, never with a silent fallback.
    """
    from ..teaching_cycle import gpu_adapter  # noqa: F401  (imports torch)
    torch, device = gpu_adapter._cuda()
    require(hasattr(gpu_adapter, "build_graph_training_framework"),
            "GRAPH_TRAINING_FRAMEWORK_HOOK_NOT_BUILT")
    return gpu_adapter.build_graph_training_framework(torch=torch, device=device)


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
        framework = real_framework()
        model = framework.build_decompose_model(seed=seed)
    require(learner_factory is not None, "LEARNER_FACTORY_REQUIRED")
    records = training_records(seed)
    before = parameter_snapshot(framework, model)
    scope = scope_parameters(framework, model)
    learner = learner_factory(model, arm=arm, learning_rate=budget.learning_rate)
    training = run_training(learner, records, arm, budget)
    after = parameter_snapshot(framework, model)
    report = {"schema": MODE_SCHEMA, "run_id": run_id, "arm": arm, "seed": seed,
              "target": {"contract_id": TARGET_CONTRACT_ID,
                         "plasticity_role": TARGET_PLASTICITY_ROLE},
              "scope": scope, "containment": containment_report(before, after,
                                                                scope["allowed"]),
              "training": training, "budget": {
                  "learning_rate": budget.learning_rate,
                  "max_optimizer_steps": budget.max_optimizer_steps,
                  "max_wall_seconds": budget.max_wall_seconds},
              "claims": {"specialist_claimed": False,
                         "sealed_splits_read": False,
                         "answer_edges_present": False}}
    return report


def evaluate_sealed(learner, seed=20260909, splits=SEALED_SPLITS):
    """Post-training evaluator: reads ONLY the sealed validation/test splits."""
    dataset = lessons.build_dataset(seed=seed)
    metrics = {}
    for split in splits:
        for record in dataset[split]:
            if record["family"] != "whole_part" or record["op"] not in WHOLE_PART_OPS:
                continue
            task = make_task(record, arm="generic")
            correct = learner.predict(task) == task["correct"]
            key = (split, task["op"])
            bucket = metrics.setdefault(key, {"attempted": 0, "correct": 0})
            bucket["attempted"] += 1
            if correct:
                bucket["correct"] += 1
    return {"per_split_op": metrics,
            "boundary": "post-training sealed-split evaluation only",
            "training_path_never_reads_sealed": True}
