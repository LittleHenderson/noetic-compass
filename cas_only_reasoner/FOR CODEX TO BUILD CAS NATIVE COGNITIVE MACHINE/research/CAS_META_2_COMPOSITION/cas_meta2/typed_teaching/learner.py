"""Worker-only typed learner; importing this module performs no numeric work.

Prediction receives only public packets. Private correction is admitted only
after a caller-created file exactly seals the retained batch predictions.
CUDA/source/gradient/reload acceptance must be measured on an authorized worker.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import random
import re
import time

from . import course, slots, source

PREDICTION_SCHEMA = "cas.typed-teaching-prediction/0.1"
BATCH_SCHEMA = "cas.typed-teaching-staged-batch/0.1"
CHECKPOINT_SCHEMA = "cas.typed-teaching-checkpoint/0.1"
require, digest, canonical = source.require, source.digest, source.canonical
PARAMETERS = ("left.weight", "merge.weight", "right.weight")
PARAMETER_SHAPES = {"left.weight": (64, 64), "right.weight": (64, 64), "merge.weight": (64, 128)}


def profile():
    paths = [Path(__file__), Path(__file__).with_name("loss_plan.py"),
             Path(__file__).parents[1] / "recurrent_cjt/recurrence.py",
             Path(__file__).parents[1] / "graph_teaching/trainer.py",
             Path(__file__).parents[1] / "graph_teaching/real_framework.py",
             Path(__file__).parents[1] / "teaching_cycle/gpu_adapter.py"]
    body = {"schema": "cas.typed-teaching-learner-profile/0.1",
        "files": [{"path": path.relative_to(Path(__file__).parents[2]).as_posix(),
                   "sha256": sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size} for path in paths],
        "slots_profile": slots.profile(), "core_width": 64, "readout_rows": 90,
        "recurrence": "same registered core via recurrence.run_passes; fresh zero state per slot; no detach or depth selection",
        "readout": "unnormalized dot product of final core vector and frozen unit readout row; no learned head",
        "training_loss": "raw field mean, task mean, batch mean; log-alphabet normalization for reporting only",
        "identity_boundary": "ON_DISK_BYTES; LOADED_SOURCE_WHEEL_AND_PROVIDER_ATTESTATION_REQUIRED_FROM_WORKER",
        "status": "WORKER_IMPLEMENTATION_NUMERIC_ACCEPTANCE_PENDING"}
    return {**body, "profile_digest": digest(body)}


def state_identity(torch, value):
    """Typed exact tensor-byte identity, ignoring device for CPU serialization."""
    def walk(node):
        if torch.is_tensor(node):
            require(not node.is_sparse, "TYPED_STATE_SPARSE")
            raw = bytes(node.detach().contiguous().reshape(-1).view(torch.uint8).cpu().tolist())
            return {"type": "tensor", "dtype": str(node.dtype), "shape": list(node.shape), "sha256": sha256(raw).hexdigest()}
        if type(node) is dict:
            require(all(type(k) in (str, int) for k in node), "TYPED_STATE_KEY")
            return {"type": "dict", "items": [[type(k).__name__, k, walk(node[k])] for k in sorted(node, key=lambda k: (type(k).__name__, str(k)))]}
        if type(node) in (list, tuple): return {"type": type(node).__name__, "items": [walk(v) for v in node]}
        require(type(node) in (str, int, float, bool, type(None))
                and (type(node) is not float or math.isfinite(node)), "TYPED_STATE_SCALAR")
        return {"type": type(node).__name__, "value": node}
    return digest(walk(value))


def _cpu(torch, value):
    if torch.is_tensor(value): return value.detach().cpu().clone()
    if type(value) is dict: return {k: _cpu(torch, v) for k, v in value.items()}
    if type(value) is list: return [_cpu(torch, v) for v in value]
    if type(value) is tuple: return tuple(_cpu(torch, v) for v in value)
    return deepcopy(value)


class TypedCourseLearner:
    def __init__(self, torch, framework, encoder, *, optimizer_config, run_context, limits, device):
        # The inherited explicit Linux-worker gate is configuration, not authority.
        from ..teaching_cycle.gpu_adapter import execution_guard
        execution_guard()
        require(re.fullmatch(r"cuda(?::[0-9]+)?", str(device)) is not None and torch.cuda.is_available(), "TYPED_LEARNER_CUDA_REQUIRED")
        from ..graph_teaching.trainer import scope_parameters
        self.torch, self.framework, self.module, self.encoder = torch, framework, framework.module, encoder
        self.device = torch.device("cuda", torch.cuda.current_device()) if str(device) == "cuda" else torch.device(device)
        self.scope = scope_parameters(framework, self.module)
        require(self.scope == {"allowed": list(PARAMETERS), "frozen": [],
            "contract_id": "cas.cjt.operation.^6.decompose/0.2", "role": "operation:^6"}, "TYPED_LEARNER_REGISTERED_SCOPE")
        parameters = dict(self.module.named_parameters())
        require(set(parameters) == set(PARAMETERS) and all(tuple(p.shape) == PARAMETER_SHAPES[name] and p.device == self.device
                    and p.dtype == torch.float32 and p.requires_grad for name, p in parameters.items()), "TYPED_LEARNER_PARAMETER_SHAPE")
        require(type(optimizer_config) is dict and set(optimizer_config) == {"learning_rate", "weight_decay", "betas", "eps"}, "TYPED_OPTIMIZER_FIELDS")
        require(type(optimizer_config["betas"]) is list and len(optimizer_config["betas"]) == 2, "TYPED_OPTIMIZER_BETAS")
        values = [optimizer_config["learning_rate"], optimizer_config["weight_decay"], optimizer_config["eps"], *optimizer_config["betas"]]
        require(all(type(x) in (int, float) and math.isfinite(x) for x in values)
                and 0 < values[0] <= 1 and 0 <= values[1] <= 1 and 0 < values[2] <= 1
                and all(0 <= x < 1 for x in values[3:]), "TYPED_OPTIMIZER_RANGE")
        require(type(limits) is dict and set(limits) == {"max_updates", "max_core_calls", "max_wall_seconds"}
                and type(limits["max_updates"]) is int and 0 < limits["max_updates"] <= 176
                and type(limits["max_core_calls"]) is int and 0 < limits["max_core_calls"] <= 1000000
                and type(limits["max_wall_seconds"]) in (int, float) and 0 < limits["max_wall_seconds"] <= 3600, "TYPED_LEARNER_LIMITS")
        require(type(run_context) is dict and set(run_context) == {"run_id", "course_sha256", "condition", "source_seed"}
                and type(run_context["run_id"]) is str and re.fullmatch(r"[A-Za-z0-9_-]{1,128}", run_context["run_id"])
                and type(run_context["course_sha256"]) is str and re.fullmatch("[0-9a-f]{64}", run_context["course_sha256"])
                and run_context["condition"] in ("ALT_COMPONENT_WHOLE", "MIXED_SAME_ITEMS", "ORDINARY_DEPENDENCY_GRAPH")
                and type(run_context["source_seed"]) is int and run_context["source_seed"] in (101, 202, 303), "TYPED_LEARNER_RUN_CONTEXT")
        encoder.verify_frozen()
        require(tuple(encoder.readout_rows.shape) == (90, 64) and encoder.readout_rows.device == self.device
                and encoder.readout_rows.dtype == torch.float32 and not encoder.readout_rows.requires_grad
                and encoder.symbol_to_index == {symbol: i for i, symbol in enumerate(slots.SYMBOLS)}, "TYPED_LEARNER_READOUT")
        self.optimizer_config, self.limits = deepcopy(optimizer_config), deepcopy(limits)
        self.optimizer = torch.optim.AdamW([parameters[name] for name in PARAMETERS], lr=optimizer_config["learning_rate"],
            weight_decay=optimizer_config["weight_decay"], betas=tuple(optimizer_config["betas"]), eps=optimizer_config["eps"],
            foreach=False, fused=False, capturable=False)
        self.run_identity = {"context": deepcopy(run_context), "learner_profile": profile(), "encoder_identity": deepcopy(encoder.identity),
            "initial_model_identity": state_identity(torch, dict(self.module.state_dict())), "scope": deepcopy(self.scope),
            "optimizer_config": deepcopy(optimizer_config), "limits": deepcopy(limits)}
        self.run_identity_digest = digest(self.run_identity)
        self.cursor = self.model_revision = 0
        self.counters = {key: 0 for key in ("core_forward_attempts", "core_forward_calls", "sample_core_passes", "slot_forwards",
            "prediction_calls", "staged_batches", "backward_attempts", "backward_calls", "optimizer_step_attempts", "optimizer_updates", "private_loss_plan_calls")}
        self._pending, self.failed = None, False
        self._started, self._elapsed_before = time.monotonic(), 0.0

    def _elapsed(self): return self._elapsed_before + time.monotonic() - self._started

    def _budget(self):
        require(not self.failed and self._elapsed() <= self.limits["max_wall_seconds"], "TYPED_LEARNER_FAILED_OR_WALL_BUDGET")

    def _forward(self, packet, depth):
        from ..recurrent_cjt import recurrence
        self._budget()
        require(type(depth) is int and depth in (1, 2, 4, 8), "TYPED_LEARNER_DEPTH")
        plan = slots.compile_slots(packet)
        require(self.counters["core_forward_attempts"] + len(plan["slots"]) * depth <= self.limits["max_core_calls"], "TYPED_LEARNER_FORWARD_BUDGET")
        torch, tensors = self.torch, {}
        self.encoder.verify_frozen()
        def rms(values):
            require(all(torch.is_tensor(v) for v in values), "TYPED_LEARNER_DETACHED_RECURRENCE")
            vector = torch.stack(list(values))
            return torch.sqrt(torch.mean(vector * vector))
        def core(incoming):
            self._budget()
            self.counters["core_forward_attempts"] += 1
            result = self.module(torch.stack(list(incoming)).unsqueeze(0))[0]
            self.counters["core_forward_calls"] += 1
            self.counters["sample_core_passes"] += 1
            require(tuple(result.shape) == (64,) and bool(torch.isfinite(result).all().item()), "TYPED_LEARNER_CORE_OUTPUT")
            return result
        for slot in plan["slots"]:
            encoded = self.encoder.encode_slot(packet, plan, slot)
            require(tuple(encoded.shape) == (64,) and encoded.device == self.device and encoded.dtype == torch.float32
                    and not encoded.requires_grad and bool(torch.isfinite(encoded).all().item()), "TYPED_LEARNER_ENCODED_SLOT")
            final = recurrence.run_passes(encoded, core, depth=depth, state=None, rms_fn=rms, cast=lambda x: x,
                zeros=lambda count: torch.zeros(count, dtype=encoded.dtype, device=encoded.device))
            vector = torch.stack(list(final))
            indexes = [self.encoder.symbol_to_index[symbol] for symbol in slot["symbols"]]
            logits = self.encoder.readout_rows[indexes] @ vector
            require(bool(torch.isfinite(logits).all().item()), "TYPED_LEARNER_LOGITS_NONFINITE")
            tensors[slot["slot_id"]] = logits
            self.counters["slot_forwards"] += 1
        scores = {row["slot_id"]: {symbol: float(tensors[row["slot_id"]][i].detach().cpu().item())
                                  for i, symbol in enumerate(row["symbols"])} for row in plan["slots"]}
        decisions = slots.score_decisions(packet, scores)
        body = {"schema": PREDICTION_SCHEMA, "record_id": plan["record_id"], "packet_digest": plan["packet_digest"],
                "slot_plan_digest": plan["plan_digest"], "depth": depth, "model_revision": self.model_revision,
                "run_context_digest": self.run_identity_digest, "encoder_identity_digest": digest(self.encoder.identity),
                "scores": scores, "decisions": decisions, "answer": slots.assemble_answer(packet, decisions)}
        self.counters["prediction_calls"] += 1
        return {**body, "prediction_id": "typed-prediction-" + digest(body)}, plan, tensors

    def predict(self, packet, depth):
        """Public-only inference; no target argument, private import or repair."""
        require(self._pending is None, "TYPED_LEARNER_PENDING_BATCH")
        self.module.eval()
        with self.torch.no_grad(): prediction, _, _ = self._forward(packet, depth)
        return prediction

    def stage_batch(self, packets, depth, *, cursor, occurrence_ids):
        """Retain autograd, return public bytes for the caller to durably seal."""
        self._budget()
        require(self._pending is None and type(cursor) is int and cursor == self.cursor
                and self.counters["optimizer_updates"] < self.limits["max_updates"], "TYPED_LEARNER_BATCH_CURSOR_OR_BUDGET")
        require(type(packets) is list and 0 < len(packets) <= 8 and type(occurrence_ids) is list
                and len(occurrence_ids) == len(packets) and len(set(occurrence_ids)) == len(occurrence_ids)
                and all(type(v) is str and re.fullmatch(r"typed-occurrence-[0-9a-f]{64}", v) for v in occurrence_ids), "TYPED_LEARNER_BATCH_SHAPE")
        snapshots = [course.validate_model_packet(packet) for packet in packets]
        self.encoder.verify_frozen()
        self.module.train()
        self.optimizer.zero_grad(set_to_none=True)
        results = [self._forward(packet, depth) for packet in snapshots]
        body = {"schema": BATCH_SCHEMA, "cursor": cursor, "model_revision": self.model_revision,
                "run_identity_digest": self.run_identity_digest, "occurrence_ids": deepcopy(occurrence_ids),
                "predictions": [result[0] for result in results]}
        public = {**body, "batch_id": "typed-batch-" + digest(body)}
        raw = (canonical(public) + "\n").encode()
        self._pending = {"packets": snapshots, "results": results, "public": public, "raw": raw,
                         "model_identity": state_identity(self.torch, dict(self.module.state_dict()))}
        self.counters["staged_batches"] += 1
        return {"public": deepcopy(public), "bytes": raw, "sha256": sha256(raw).hexdigest()}

    def _tensor_loss(self, plan, loss, tensors):
        torch = self.torch
        by_id = {s["slot_id"]: s for s in plan["slots"]}
        fields, reports = [], []
        for field in loss["fields"]:
            if field["kind"] == "joint_correspondence":
                mode = torch.log_softmax(tensors[plan["slots"][0]["slot_id"]], dim=0)
                candidates = plan["correspondence_candidates"]
                if len(candidates) == 1:
                    term = mode.sum() * 0
                else:
                    node_alias = {n["ref"]: n["alias"] for w in plan["aliases"]["worlds"] for n in w["nodes"]}
                    row_by_source = {s["coordinates"][0]: s for s in plan["slots"][1:]}
                    sums = []
                    for candidate in candidates[1:]:
                        selected = []
                        for pair in candidate["value"]["pairs"]:
                            row = row_by_source[pair["source"]]
                            selected.append(tensors[row["slot_id"]][row["symbols"].index(node_alias[pair["target"]])])
                        sums.append(torch.stack(selected).sum())
                    mapping = torch.stack(sums)
                    joint = torch.cat((mode[0].reshape(1), mode[1] + mapping - torch.logsumexp(mapping, dim=0)))
                    indices = [i for i, c in enumerate(candidates) if c["candidate_id"] in field["valid_candidate_ids"]]
                    term = -torch.logsumexp(joint[indices], dim=0)
            else:
                terms = []
                for key in field["slot_ids"]:
                    logits, row = tensors[key], by_id[key]
                    indices = [row["symbols"].index(symbol) for symbol in field["targets"][key]]
                    terms.append(torch.logsumexp(logits, dim=0) - torch.logsumexp(logits[indices], dim=0))
                term = torch.stack(terms).mean()
            require(term.requires_grad and bool(torch.isfinite(term).item()), "TYPED_LEARNER_LOSS_DETACHED_OR_NONFINITE")
            fields.append(term)
            raw, size = float(term.detach().cpu().item()), field["public_alphabet_size"]
            reports.append({"field": field["field"], "raw_loss": raw, "normalized_loss": raw / math.log(size) if size > 1 else 0.0,
                            "public_alphabet_size": size, "slot_count": len(field["slot_ids"]), "forced": size == 1})
        return torch.stack(fields).mean(), {"fields": reports,
            "raw_task_loss": sum(r["raw_loss"] for r in reports) / len(reports),
            "normalized_task_loss": sum(r["normalized_loss"] for r in reports) / len(reports)}

    def train_sealed_batch(self, path, *, expected_sha256, target_receipts):
        """Read the exact durable public seal BEFORE accessing private targets."""
        self._budget()
        require(self._pending is not None, "TYPED_LEARNER_NO_PENDING_BATCH")
        seal = Path(path)
        require(seal.is_file() and not seal.is_symlink() and seal.stat().st_size <= 16 * 1024 * 1024, "TYPED_LEARNER_SEAL_PATH")
        raw = seal.read_bytes()
        require(type(expected_sha256) is str and sha256(raw).hexdigest() == expected_sha256
                and raw == self._pending["raw"], "TYPED_LEARNER_SEAL_MISMATCH")
        require(state_identity(self.torch, dict(self.module.state_dict())) == self._pending["model_identity"], "TYPED_LEARNER_MODEL_CHANGED_AFTER_PREDICTION")
        self.encoder.verify_frozen()
        # No target object has been iterated or validated before this point.
        from . import loss_plan
        require(type(target_receipts) is list and len(target_receipts) == len(self._pending["packets"]), "TYPED_LEARNER_TARGET_COUNT")
        tasks, reports, loss_ids = [], [], []
        try:
            for packet, (prediction, plan, tensors), target in zip(self._pending["packets"], self._pending["results"], target_receipts):
                prediction_raw = (canonical(prediction) + "\n").encode()
                self.counters["private_loss_plan_calls"] += 1
                loss = loss_plan.compile_loss_plan(packet, target, sealed_prediction_bytes=prediction_raw,
                                                   expected_prediction_sha256=sha256(prediction_raw).hexdigest())
                task, report = self._tensor_loss(plan, loss, tensors)
                # Compare retained published scalars with the same normalized loss contract.
                scalar = loss_plan.scalar_report(packet, loss, prediction["scores"])
                require(math.isclose(report["raw_task_loss"], scalar["raw_task_loss"], rel_tol=2e-5, abs_tol=2e-5), "TYPED_LEARNER_SCALAR_TENSOR_LOSS_MISMATCH")
                report.update({"record_id": plan["record_id"], "loss_plan_digest": loss["loss_plan_digest"],
                               "admissible_answer_count": loss["admissible_answer_count"]})
                tasks.append(task); reports.append(report); loss_ids.append(loss["loss_plan_digest"])
            self._budget()
            total = self.torch.stack(tasks).mean()
            self.counters["backward_attempts"] += 1
            total.backward()
            self.counters["backward_calls"] += 1
            parameters = dict(self.module.named_parameters())
            require(all(p.grad is not None and bool(self.torch.isfinite(p.grad).all().item()) for p in parameters.values()), "TYPED_LEARNER_GRADIENTS")
            gradient_squared = sum(float((p.grad.detach() * p.grad.detach()).sum().cpu().item()) for p in parameters.values())
            require(math.isfinite(gradient_squared), "TYPED_LEARNER_GRADIENT_NORM_NONFINITE")
            self._budget()
            self.counters["optimizer_step_attempts"] += 1
            self.optimizer.step()
            self.counters["optimizer_updates"] += 1
            require(all(bool(self.torch.isfinite(p).all().item()) for p in parameters.values()), "TYPED_LEARNER_PARAMETERS_NONFINITE")
            self.encoder.verify_frozen()
            self.cursor += 1; self.model_revision += 1
            result = {"schema": "cas.typed-teaching-update/0.1", "batch_id": self._pending["public"]["batch_id"],
                "public_seal_sha256": expected_sha256, "cursor_committed": self.cursor, "model_revision": self.model_revision,
                "tasks": reports, "raw_batch_loss": sum(r["raw_task_loss"] for r in reports) / len(reports),
                "normalized_batch_loss": sum(r["normalized_task_loss"] for r in reports) / len(reports),
                "training_uses": "raw_batch_loss", "gradient_squared_norm": gradient_squared,
                "loss_plan_digests": loss_ids, "counters": deepcopy(self.counters)}
            self._pending = None
            return result
        except Exception:
            self.failed = True
            self._pending = None
            raise

    def export_checkpoint(self, path):
        require(self._pending is None and not self.failed, "TYPED_CHECKPOINT_UNCOMMITTED_OR_FAILED")
        self.encoder.verify_frozen()
        torch = self.torch
        model = _cpu(torch, dict(self.module.state_dict()))
        optimizer = _cpu(torch, self.optimizer.state_dict())
        encoder = self.encoder.export_state()
        rng = {"torch_cpu": torch.get_rng_state().clone(), "torch_cuda": [v.clone() for v in torch.cuda.get_rng_state_all()],
               "python": random.getstate()}
        metadata = {"run_identity": deepcopy(self.run_identity), "run_identity_digest": self.run_identity_digest,
            "model_revision": self.model_revision, "cursor": self.cursor, "counters": deepcopy(self.counters),
            "elapsed_seconds": self._elapsed(), "training_mode": self.module.training,
            "model_state_identity": state_identity(torch, model), "optimizer_state_identity": state_identity(torch, optimizer),
            "encoder_state_identity": state_identity(torch, encoder), "rng_state_identity": state_identity(torch, rng)}
        payload = {"schema": CHECKPOINT_SCHEMA, "metadata": metadata, "model_state": model,
                   "optimizer_state": optimizer, "encoder_state": encoder, "rng_state": rng}
        destination = Path(path)
        require(destination.parent.is_dir(), "TYPED_CHECKPOINT_PARENT")
        with destination.open("xb") as stream:
            torch.save(payload, stream); stream.flush(); os.fsync(stream.fileno())
        raw = destination.read_bytes()
        return {"path": str(destination.resolve()), "sha256": sha256(raw).hexdigest(), "bytes": len(raw),
                "run_identity_digest": self.run_identity_digest, "metadata": metadata}

    @classmethod
    def restore_checkpoint(cls, torch, framework, *, path, expected_sha256, expected_run_identity_digest, device):
        from ..teaching_cycle.gpu_adapter import execution_guard
        execution_guard()
        require(re.fullmatch(r"cuda(?::[0-9]+)?", str(device)) is not None and torch.cuda.is_available(), "TYPED_LEARNER_CUDA_REQUIRED")
        target = Path(path)
        require(target.is_file() and not target.is_symlink() and 0 < target.stat().st_size <= 256 * 1024 * 1024, "TYPED_CHECKPOINT_FILE_BOUND")
        raw = target.read_bytes()
        require(type(expected_sha256) is str and sha256(raw).hexdigest() == expected_sha256, "TYPED_CHECKPOINT_SHA")
        import io
        payload = torch.load(io.BytesIO(raw), map_location="cpu", weights_only=True)
        require(type(payload) is dict and set(payload) == {"schema", "metadata", "model_state", "optimizer_state", "encoder_state", "rng_state"}
                and payload["schema"] == CHECKPOINT_SCHEMA, "TYPED_CHECKPOINT_FIELDS")
        metadata = payload["metadata"]
        require(type(metadata) is dict and set(metadata) == {"run_identity", "run_identity_digest", "model_revision", "cursor", "counters",
            "elapsed_seconds", "training_mode", "model_state_identity", "optimizer_state_identity", "encoder_state_identity", "rng_state_identity"}, "TYPED_CHECKPOINT_METADATA")
        identity = metadata["run_identity"]
        require(digest(identity) == metadata["run_identity_digest"] == expected_run_identity_digest
                and canonical(identity["learner_profile"]) == canonical(profile()), "TYPED_CHECKPOINT_RUN_IDENTITY")
        for field in ("model", "optimizer", "encoder", "rng"):
            require(state_identity(torch, payload[field + "_state"]) == metadata[field + "_state_identity"], "TYPED_CHECKPOINT_STATE_DIGEST:" + field)
        from .encoder import restore_frozen_typed_encoder
        encoder = restore_frozen_typed_encoder(torch, payload["encoder_state"], expected_identity=identity["encoder_identity"], device=device)
        framework.module.load_state_dict(payload["model_state"], strict=True)
        restored = cls(torch, framework, encoder, optimizer_config=identity["optimizer_config"], run_context=identity["context"], limits=identity["limits"], device=device)
        restored.optimizer.load_state_dict(payload["optimizer_state"])
        require(state_identity(torch, dict(restored.module.state_dict())) == metadata["model_state_identity"]
                and state_identity(torch, restored.optimizer.state_dict()) == metadata["optimizer_state_identity"], "TYPED_CHECKPOINT_RESTORED_VALUES")
        require(type(metadata["cursor"]) is int and type(metadata["model_revision"]) is int
                and 0 <= metadata["cursor"] == metadata["model_revision"] <= restored.limits["max_updates"], "TYPED_CHECKPOINT_CURSOR")
        require(type(metadata["counters"]) is dict and set(metadata["counters"]) == set(restored.counters)
                and all(type(v) is int and v >= 0 for v in metadata["counters"].values())
                and metadata["counters"]["optimizer_updates"] == metadata["cursor"], "TYPED_CHECKPOINT_COUNTERS")
        require(type(metadata["elapsed_seconds"]) in (int, float) and math.isfinite(metadata["elapsed_seconds"])
                and 0 <= metadata["elapsed_seconds"] <= restored.limits["max_wall_seconds"]
                and type(metadata["training_mode"]) is bool, "TYPED_CHECKPOINT_RUNTIME_METADATA")
        restored.run_identity, restored.run_identity_digest = deepcopy(identity), expected_run_identity_digest
        restored.cursor, restored.model_revision, restored.counters = metadata["cursor"], metadata["model_revision"], deepcopy(metadata["counters"])
        restored._elapsed_before, restored._started = metadata["elapsed_seconds"], time.monotonic()
        restored.module.train(metadata["training_mode"])
        rng = payload["rng_state"]
        require(type(rng) is dict and set(rng) == {"torch_cpu", "torch_cuda", "python"}, "TYPED_CHECKPOINT_RNG_FIELDS")
        torch.set_rng_state(rng["torch_cpu"]); torch.cuda.set_rng_state_all(rng["torch_cuda"]); random.setstate(rng["python"])
        current_rng = {"torch_cpu": torch.get_rng_state(), "torch_cuda": torch.cuda.get_rng_state_all(), "python": random.getstate()}
        require(state_identity(torch, current_rng) == metadata["rng_state_identity"], "TYPED_CHECKPOINT_RNG_VALUES")
        encoder.verify_frozen()
        return restored
