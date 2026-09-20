"""Second learning protocol: lossless text and generated-validation selection.

Only training and validation labels are opened here. Held-out private labels
are hashed as bytes, never parsed. Both encoders see the same training batches
and use identical optimization and validation-only checkpoint selection.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import platform
import random
import sys
import time

os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import torch
from torch.nn import functional as F

from .codec import (ACTION_VOCABULARY, PAD_ID,
                    canonical_sha256, validate_action, validate_public)
from .features_v2 import LosslessPublicTokenizer
from .selection_v2 import generated_metrics, selection_key
from .policy import (PolicyConfig, build_matched_policies, encode_batch,
                     encode_targets, parameter_count, predict_public, require_cuda)


ARMS = ("cas_untrained", "cas_trained", "generic_untrained", "generic_trained", "rule")
_CUDA_CONTEXT = None


class CampaignDeadline(RuntimeError):
    pass


@dataclass(frozen=True)
class TrainingConfig:
    seed: int = 7
    epochs: int = 100
    batch_size: int = 16
    prediction_batch_size: int = 16
    learning_rate: float = 0.001
    weight_decay: float = 0.01
    gradient_clip: float = 1.0
    max_training_seconds: int = 3300
    validation_generation_interval: int = 5
    policy: PolicyConfig = field(default_factory=lambda: PolicyConfig(max_length=1024, max_action_length=256))

    def validate(self):
        self.policy.validate()
        if type(self.seed) is not int or not 0 <= self.seed < 2**63:
            raise ValueError("TRAINING_SEED_INVALID")
        for name, bound in (("epochs", 200), ("batch_size", 64),
                            ("prediction_batch_size", 64), ("max_training_seconds", 5400),
                            ("validation_generation_interval", 20)):
            value = getattr(self, name)
            if type(value) is not int or not 1 <= value <= bound:
                raise ValueError("TRAINING_BOUND_INVALID:" + name)
        for name, upper in (("learning_rate", 0.01), ("weight_decay", 1.0), ("gradient_clip", 100.0)):
            value = getattr(self, name)
            if type(value) not in (int, float) or not math.isfinite(value) or not 0 < value <= upper:
                raise ValueError("TRAINING_SCALAR_INVALID:" + name)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n",
                         encoding="utf-8")
    os.replace(temporary, path)


def file_hash(path):
    digest = sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require_time(deadline):
    if time.monotonic() >= deadline:
        raise CampaignDeadline("CAMPAIGN_WALL_DEADLINE_REACHED")


def setup_cuda(seed=7):
    global _CUDA_CONTEXT
    if _CUDA_CONTEXT is not None:
        return _CUDA_CONTEXT
    device = require_cuda("cuda")
    torch.set_num_threads(1)
    random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    _CUDA_CONTEXT = (torch, device)
    return _CUDA_CONTEXT


def environment_identity(device):
    require_cuda(device)
    properties = torch.cuda.get_device_properties(device)
    return {
        "python": sys.version, "executable": sys.executable, "platform": platform.platform(),
        "torch": str(torch.__version__), "cuda_runtime": torch.version.cuda,
        "cuda_device": str(device), "cuda_device_name": torch.cuda.get_device_name(device),
        "cuda_total_memory": properties.total_memory,
        "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
        "tf32_matmul": torch.backends.cuda.matmul.allow_tf32,
        "tf32_cudnn": torch.backends.cudnn.allow_tf32, "torch_cpu_threads": torch.get_num_threads(),
        "utc": datetime.now(timezone.utc).isoformat(),
        "argv": sys.argv,
        "provider_boundary": "CUDA observed here; AWS identity and spend are bound by the separate launcher receipt.",
    }


def _checkpoint(path, model, optimizer, tokenizer, config, *, family, epoch, steps, validation):
    require_cuda(next(model.parameters()).device)
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp")
    payload = {
        "schema": "cas-meta2-candidate-checkpoint/2", "family": family,
        "epoch": epoch, "optimizer_steps": steps, "validation": validation,
        "config": asdict(config), "tokenizer": tokenizer.to_dict(),
        "tokenizer_digest": tokenizer.digest, "action_vocabulary": list(ACTION_VOCABULARY),
        "action_vocabulary_sha256": canonical_sha256(list(ACTION_VOCABULARY)),
        "state_dict": model.state_dict(), "optimizer_state_dict": optimizer.state_dict(),
        "scope": "New candidate encoder, decoder and binding pointer only; no accepted executor weights.",
    }
    torch.save(payload, temporary)
    os.replace(temporary, path)
    return {"schema": "cas-meta2-candidate-checkpoint/2",
            "path": str(path), "sha256": file_hash(path), "bytes": path.stat().st_size,
            "epoch": epoch, "optimizer_steps": steps, "validation": validation}


def _load_checkpoint(model, record, tokenizer, device):
    require_cuda(device)
    if file_hash(record["path"]) != record["sha256"]:
        raise RuntimeError("CANDIDATE_CHECKPOINT_DIGEST_MISMATCH")
    payload = torch.load(record["path"], map_location=device, weights_only=True)
    if record.get("schema") != "cas-meta2-candidate-checkpoint/2" or payload.get("schema") != record["schema"]:
        raise RuntimeError("CHECKPOINT_FORMAT_MISMATCH")
    if payload["tokenizer_digest"] != tokenizer.digest:
        raise RuntimeError("CHECKPOINT_TOKENIZER_MISMATCH")
    if payload["action_vocabulary"] != list(ACTION_VOCABULARY):
        raise RuntimeError("CHECKPOINT_ACTION_VOCABULARY_MISMATCH")
    model.load_state_dict(payload["state_dict"], strict=True)
    if any(value.device.type != "cuda" for value in model.parameters()):
        raise RuntimeError("CHECKPOINT_LOADED_OUTSIDE_CUDA")


@torch.no_grad()
def _validation_loss(model, tasks, tokenizer, config, device, deadline):
    require_cuda(device)
    model.eval()
    loss_sum, token_count, token_correct = 0.0, 0, 0
    for offset in range(0, len(tasks), config.batch_size):
        require_time(deadline)
        batch_tasks = tasks[offset:offset + config.batch_size]
        batch = encode_batch([task["public"] for task in batch_tasks], tokenizer, device=device)
        target = encode_targets([task["target"] for task in batch_tasks], device=device,
                                max_length=config.policy.max_action_length)
        logits = model(batch, target["decoder_input_ids"])["token_logits"]
        loss = F.cross_entropy(logits.flatten(0, 1), target["target_ids"].flatten(),
                               ignore_index=PAD_ID, reduction="sum")
        if not bool(torch.isfinite(loss)):
            raise RuntimeError("VALIDATION_LOSS_NONFINITE")
        loss_sum += float(loss.item())
        token_count += int(target["valid"].sum().item())
        token_correct += int(((logits.argmax(-1) == target["target_ids"]) & target["valid"]).sum().item())
    if token_count == 0:
        raise RuntimeError("VALIDATION_TOKEN_DENOMINATOR_EMPTY")
    return {"token_cross_entropy": loss_sum / token_count, "tokens": token_count,
            "teacher_forced_token_correct": token_correct,
            "teacher_forced_token_accuracy": token_correct / token_count,
            "boundary": "Teacher-forced validation metric; not open-generation task correctness."}


def _validation_generation(model, tasks, tokenizer, config, device, deadline):
    actions = []
    for offset in range(0, len(tasks), config.prediction_batch_size):
        require_time(deadline)
        publics = [task["public"] for task in tasks[offset:offset + config.prediction_batch_size]]
        actions.extend(predict_public(model, tokenizer, publics, device=device,
                                      batch_size=config.prediction_batch_size))
        require_time(deadline)
    return actions


def classification_metrics(actions, tasks):
    if len(actions) != len(tasks):
        raise RuntimeError("CLASSIFICATION_DENOMINATOR_MISMATCH")
    graph, binding, joint, valid = 0, 0, 0, 0
    for action, task in zip(actions, tasks, strict=True):
        try:
            validate_action(action)
        except ValueError:
            continue
        valid += 1
        correct_graph = canonical_sha256(action["program"]) == canonical_sha256(task["target"]["program"])
        correct_binding = action["binding"] == task["target"]["binding"]
        graph += correct_graph
        binding += correct_binding
        joint += correct_graph and correct_binding
    return {"total": len(tasks), "valid_programs": valid, "graph_correct": graph,
            "binding_correct": binding, "joint_correct": joint,
            "joint_accuracy": joint / len(tasks) if tasks else None,
            "all_cases_in_denominator": True}


def _predict_chunks(model, tokenizer, publics, config, device, deadline, output, arm):
    require_cuda(device)
    result = []
    started = time.monotonic()
    for offset in range(0, len(publics), config.prediction_batch_size):
        require_time(deadline)
        result.extend(predict_public(model, tokenizer, publics[offset:offset + config.prediction_batch_size],
                                     device=device, batch_size=config.prediction_batch_size))
        write_json(Path(output) / (arm + "_predictions_partial.json"),
                   {"sealed": False, "completed": len(result), "total": len(publics), "actions": result})
        print(json.dumps({"stage": "public_prediction", "arm": arm, "completed": len(result),
                          "total": len(publics)}), flush=True)
    torch.cuda.synchronize(device)
    return result, {"wall_seconds": time.monotonic() - started, "examples": len(publics),
                    "device": str(device)}


def train_and_seal(data, output, config, deadline):
    """Train both candidates and seal all test predictions; never open test gold."""
    config.validate()
    _, device = setup_cuda(config.seed)
    data, output = Path(data), Path(output)
    require_time(deadline)
    manifest = read_json(data / "dataset_manifest.json")
    expected_files = ("train.json", "validation.json", "test_public.json", "test_private.json")
    hashes = {name: file_hash(data / name) for name in expected_files}
    if any(manifest["sha256"].get(name) != digest for name, digest in hashes.items()):
        raise RuntimeError("DATASET_MANIFEST_DIGEST_MISMATCH")
    train_tasks = read_json(data / "train.json")
    validation_tasks = read_json(data / "validation.json")
    test_public = read_json(data / "test_public.json")
    if not train_tasks or not validation_tasks or not test_public:
        raise RuntimeError("EMPTY_DATASET_PARTITION")
    for task in train_tasks + validation_tasks:
        validate_public(task["public"])
        validate_action(task["target"])
    for public in test_public:
        validate_public(public)
    tokenizer = LosslessPublicTokenizer.fit_train([task["public"] for task in train_tasks],
                                          max_length=config.policy.max_length)
    for task in train_tasks + validation_tasks:
        tokenizer.check_round_trip(task["public"])
    for public in test_public:
        tokenizer.check_round_trip(public)
    write_json(output / "tokenizer.json", tokenizer.to_dict())
    preregistration = {
        "schema": "cas-meta2-learning-preregistration/2", "config": asdict(config), "arms": list(ARMS),
        "dataset_sha256": hashes, "train_examples": len(train_tasks),
        "validation_examples": len(validation_tasks), "test_examples": len(test_public),
        "selection_rule": "Maximize freely generated validation joint correctness, then program correctness, then binding correctness, then minimize token cross-entropy; earliest checked epoch wins exact ties.",
        "selection_boundary": "Exact program/binding validation, not native answer correctness. Final held-out answers still require the unchanged native verifier.",
        "generation_schedule": "Epoch 1, every configured interval, and the final requested epoch. Other epochs are not eligible.",
        "input_encoding": "Training-only lexical vocabulary plus exact UTF-8 fallback; no UNK or silent truncation.",
        "training_rule": "Paired CAS/generic minibatches; identical examples, ordering, AdamW settings and step count.",
        "time_rule": "Stop between completed paired epochs when the declared training allocation is exhausted; retain actual counts.",
        "test_gold_rule": "Test private labels are not parsed until every arm prediction is sealed.",
        "no_promotion": ["CAS-specific advantage", "general reasoning", "complete Noetics", "production readiness"],
    }
    write_json(output / "training_preregistration.json", preregistration)
    cas, generic, matching = build_matched_policies(tokenizer, config.policy, seed=config.seed, device=device)
    models = {"cas": cas, "generic": generic}
    optimizers = {name: torch.optim.AdamW(model.parameters(), lr=config.learning_rate,
                                        weight_decay=config.weight_decay)
                  for name, model in models.items()}
    write_json(output / "parameter_matching.json", matching)
    checkpoints = {name: {} for name in models}
    history = []
    steps = {name: 0 for name in models}
    connected = {name: set() for name in models}
    compute_seconds = {name: 0.0 for name in models}
    completed_epochs = 0
    training_started = time.monotonic()
    training_deadline = min(deadline - 120.0, training_started + config.max_training_seconds)
    last_epoch_seconds = 0.0
    stop_reason = "REQUESTED_EPOCHS_COMPLETED"
    last_validation = {name: None for name in models}
    active_records = {}
    try:
        for family, model in models.items():
            require_time(deadline)
            validation = _validation_loss(model, validation_tasks, tokenizer, config, device, deadline)
            initial_actions = _validation_generation(model, validation_tasks, tokenizer, config, device, deadline)
            validation["generation"] = generated_metrics(initial_actions, validation_tasks)
            write_json(output / "validation_predictions" / f"{family}_epoch_0000.json",
                       {"epoch": 0, "actions": initial_actions, "metrics": validation["generation"],
                        "split": "validation", "test_gold_access": False})
            last_validation[family] = validation
            checkpoints[family]["initial"] = _checkpoint(
                output / f"candidate_{family}_initial.pt", model, optimizers[family], tokenizer, config,
                family=family, epoch=0, steps=0, validation=validation)
        write_json(output / "checkpoints.json", checkpoints)
        for epoch in range(1, config.epochs + 1):
            require_time(deadline)
            reserve = max(10.0, last_epoch_seconds * 1.25)
            if epoch > 1 and time.monotonic() + reserve >= training_deadline:
                stop_reason = "BOUNDED_TRAINING_ALLOCATION_REACHED"
                break
            epoch_started = time.monotonic()
            order = list(range(len(train_tasks)))
            random.Random(config.seed + epoch).shuffle(order)
            losses = {name: 0.0 for name in models}
            tokens_seen = {name: 0 for name in models}
            for offset in range(0, len(order), config.batch_size):
                require_time(deadline)
                batch_tasks = [train_tasks[index] for index in order[offset:offset + config.batch_size]]
                public_batch = encode_batch([task["public"] for task in batch_tasks], tokenizer, device=device)
                target = encode_targets([task["target"] for task in batch_tasks], device=device,
                                        max_length=config.policy.max_action_length)
                # Never time-stop between the two arms of a paired batch.
                for family, model in models.items():
                    model.train()
                    optimizer = optimizers[family]
                    torch.cuda.synchronize(device)
                    step_started = time.monotonic()
                    optimizer.zero_grad(set_to_none=True)
                    logits = model(public_batch, target["decoder_input_ids"])["token_logits"]
                    loss = F.cross_entropy(logits.flatten(0, 1), target["target_ids"].flatten(),
                                           ignore_index=PAD_ID)
                    if not bool(torch.isfinite(loss)):
                        raise RuntimeError("TRAINING_LOSS_NONFINITE:" + family)
                    loss.backward()
                    for name, value in model.named_parameters():
                        if value.requires_grad and value.grad is not None:
                            if not bool(torch.isfinite(value.grad).all()):
                                raise RuntimeError("TRAINING_GRADIENT_NONFINITE:" + family + ":" + name)
                            if bool(value.grad.abs().sum() > 0):
                                connected[family].add(name)
                    torch.nn.utils.clip_grad_norm_(model.parameters(), config.gradient_clip, error_if_nonfinite=True)
                    optimizer.step()
                    torch.cuda.synchronize(device)
                    compute_seconds[family] += time.monotonic() - step_started
                    steps[family] += 1
                    count = int(target["valid"].sum().item())
                    losses[family] += float(loss.detach().item()) * count
                    tokens_seen[family] += count
            if steps["cas"] != steps["generic"]:
                raise RuntimeError("MATCHED_OPTIMIZER_STEPS_DIFFER")
            epoch_record = {"epoch": epoch, "optimizer_steps": dict(steps), "families": {}}
            for family, model in models.items():
                validation = _validation_loss(model, validation_tasks, tokenizer, config, device, deadline)
                last_validation[family] = validation
                best = checkpoints[family].get("selected")
                generation_checked = (epoch == 1 or epoch % config.validation_generation_interval == 0
                                      or epoch == config.epochs)
                if generation_checked:
                    require_time(deadline)
                    actions = _validation_generation(model, validation_tasks, tokenizer, config, device, deadline)
                    validation["generation"] = generated_metrics(actions, validation_tasks)
                    write_json(output / "validation_predictions" / f"{family}_epoch_{epoch:04d}.json",
                               {"epoch": epoch, "actions": actions, "metrics": validation["generation"],
                                "split": "validation", "test_gold_access": False})
                selected = generation_checked and (best is None or
                    selection_key(validation) > selection_key(best["validation"]))
                if selected:
                    checkpoints[family]["selected"] = _checkpoint(
                        output / f"candidate_{family}_best.pt", model, optimizers[family], tokenizer, config,
                        family=family, epoch=epoch, steps=steps[family], validation=validation)
                checkpoints[family]["last"] = _checkpoint(
                    output / f"candidate_{family}_last.pt", model, optimizers[family], tokenizer, config,
                    family=family, epoch=epoch, steps=steps[family], validation=validation)
                expected_names = {name for name, value in model.named_parameters() if value.requires_grad}
                missing = sorted(expected_names - connected[family])
                if missing:
                    raise RuntimeError("DISCONNECTED_TRAINABLE_PARAMETERS:" + family + ":" + ",".join(missing))
                active_records[family] = {
                    "all_parameter_tensors_connected": True, "parameter_tensor_names": sorted(connected[family]),
                    "trainable_parameters": parameter_count(model),
                    "connected_trainable_parameters": sum(value.numel() for name, value in model.named_parameters()
                                                          if value.requires_grad and name in connected[family]),
                    "gradient_observation": "Finite nonzero gradient observed during at least one paired training batch.",
                }
                epoch_record["families"][family] = {
                    "training_token_cross_entropy": losses[family] / tokens_seen[family],
                    "training_tokens": tokens_seen[family], "validation": validation, "selected": selected,
                }
            completed_epochs = epoch
            last_epoch_seconds = time.monotonic() - epoch_started
            epoch_record["wall_seconds"] = last_epoch_seconds
            history.append(epoch_record)
            write_json(output / "training_history.json", history)
            write_json(output / "checkpoints.json", checkpoints)
            write_json(output / "gradient_connectivity.json", active_records)
            print(json.dumps({"stage": "paired_training", "epoch": epoch, "target_epochs": config.epochs,
                              "optimizer_steps_each": steps["cas"],
                              "cas_validation_loss": last_validation["cas"]["token_cross_entropy"],
                              "generic_validation_loss": last_validation["generic"]["token_cross_entropy"],
                              "cas_generated_validation": last_validation["cas"].get("generation"),
                              "generic_generated_validation": last_validation["generic"].get("generation")}), flush=True)
        if not completed_epochs or any("selected" not in checkpoints[family] for family in models):
            raise CampaignDeadline("NO_COMPLETED_PAIRED_TRAINING_EPOCH")
    except BaseException:
        # Keep the newest recoverable weights even if a deadline or fault occurs
        # in the middle of the next epoch. This never marks the run complete.
        for family, model in models.items():
            try:
                checkpoints[family]["interrupted"] = _checkpoint(
                    output / f"candidate_{family}_interrupted.pt", model, optimizers[family], tokenizer, config,
                    family=family, epoch=completed_epochs, steps=steps[family], validation=None)
            except Exception as error:
                checkpoints[family]["interrupted_save_failure"] = str(error)[:1024]
        write_json(output / "checkpoints_partial.json", checkpoints)
        raise
    training_record = {
        "requested_epochs": config.epochs, "completed_epochs": completed_epochs,
        "optimizer_steps": dict(steps), "stop_reason": stop_reason,
        "learning_conditions_matched": steps["cas"] == steps["generic"],
        "active_parameters": active_records, "parameter_matching": matching, "checkpoints": checkpoints,
        "training_step_wall_seconds": compute_seconds,
        "paired_training_wall_seconds": time.monotonic() - training_started,
        "selection_rule": preregistration["selection_rule"],
    }
    write_json(output / "training_receipt.json", training_record)
    predictions, timing = {}, {}
    for arm in ARMS:
        require_time(deadline)
        if arm == "rule":
            from .curriculum import parse_problem
            started = time.monotonic()
            predictions[arm] = [parse_problem(public) for public in test_public]
            timing[arm] = {"wall_seconds": time.monotonic() - started, "device": "pure public-input parser"}
        else:
            family = "cas" if arm.startswith("cas") else "generic"
            state = "initial" if arm.endswith("untrained") else "selected"
            _load_checkpoint(models[family], checkpoints[family][state], tokenizer, device)
            predictions[arm], timing[arm] = _predict_chunks(
                models[family], tokenizer, test_public, config, device, deadline, output, arm)
        if len(predictions[arm]) != len(test_public):
            raise RuntimeError("PREDICTION_DENOMINATOR_MISMATCH")
    prediction_path = output / "predictions.jsonl"
    temporary = prediction_path.with_name(prediction_path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        for index, public in enumerate(test_public):
            row = {"case_index": index, "public_sha256": canonical_sha256(public),
                   "actions": {arm: predictions[arm][index] for arm in ARMS}}
            stream.write(json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, prediction_path)
    seal = {
        "schema": "cas-meta2-prediction-seal/1", "sha256": file_hash(prediction_path),
        "sealed_utc": datetime.now(timezone.utc).isoformat(), "arms": list(ARMS),
        "test_examples": len(test_public), "prediction_count": len(test_public) * len(ARMS),
        "test_public_sha256": hashes["test_public.json"],
        "test_private_sha256": hashes["test_private.json"], "test_private_labels_loaded": False,
        "tokenizer_digest": tokenizer.digest, "selection_timing": timing,
    }
    write_json(output / "predictions_seal.json", seal)
    del cas, generic, models, optimizers
    torch.cuda.empty_cache()
    return {"training": training_record, "seal": seal, "prediction_path": str(prediction_path),
            "dataset_sha256": hashes, "test_examples": len(test_public)}
