"""Candidate-only CUDA binding updates; importing this file does not import torch.

The launcher must separately prove AWS identity. Neither the enable flag nor
CUDA proves provider identity. No native runtime or accepted weights are loaded.
State digests below hash exact tensor bytes, not serialized checkpoint files.
"""
from dataclasses import asdict
from copy import deepcopy
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import platform
import re

SCHEMA = "cas-teaching-binding-cuda/1"


def require(condition, reason):
    if not condition:
        raise ValueError("TEACHING_GPU:" + reason)


def canonical_sha256(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                             allow_nan=False).encode("utf-8")).hexdigest()


def execution_guard():
    require(platform.system() == "Linux", "LINUX_WORKER_REQUIRED")
    require(os.environ.get("CAS_META2_RUN_TEACHING_CYCLE") == "1", "EXPLICIT_ENABLE_REQUIRED")


def _cuda():
    execution_guard()
    import torch
    require(torch.cuda.is_available(), "CUDA_REQUIRED_NO_CPU_FALLBACK")
    require(torch.cuda.device_count() == 1, "EXACTLY_ONE_VISIBLE_GPU_REQUIRED")
    device = torch.device("cuda:0")
    require("T4" not in torch.cuda.get_device_name(device).upper(), "T4_NOT_ADMITTED")
    return torch, device


def _sources():
    root = Path(__file__).resolve().parents[1]
    paths = (Path(__file__).resolve(), Path(__file__).with_name("data.py"),
             Path(__file__).with_name("controller.py"),
             root / "policy.py", root / "features_v2.py", root / "codec.py")
    return {str(path.relative_to(root)): sha256(path.read_bytes()).hexdigest() for path in paths}


def validate_training_plan(cases):
    """Return canonical allowed records and plan hashes without model imports."""
    from .data import TRAIN_CONTEXTS, TRAIN_TAGS, make_cycle
    require(type(cases) is list and 1 <= len(cases) <= 4096, "TRAINING_CASES_REQUIRED")
    registry, families, copied = {}, set(), deepcopy(cases)
    for case in copied:
        require(type(case) is dict and case.get("split") == "train", "TRAINING_CASE_REQUIRED")
        # make_cycle independently checks exact formal fields, family and target.
        first = make_cycle(case)
        require(case["family_id"] not in families, "DUPLICATE_TRAINING_FAMILY")
        families.add(case["family_id"])
        require(case["context"] in TRAIN_CONTEXTS
                and all(row["tag"] in TRAIN_TAGS for row in case["observations"]),
                "NONTRAIN_CONTEXT_OR_NAMES")
        for curriculum in ("aligned", "ordinary"):
            for assistance in ("full", "faded", "none"):
                for record in (first if curriculum == "aligned" and assistance == "full"
                               else make_cycle(case, assistance, curriculum)):
                    registry[canonical_sha256(record)] = record
    copied.sort(key=lambda case: case["family_id"])
    return registry, {"training_cases_sha256": canonical_sha256(copied),
                      "record_registry_sha256": canonical_sha256(sorted(registry))}


def validate_records(records, registry):
    """Check teaching metadata before any forward; only train may update weights."""
    from ..codec import validate_public
    require(type(records) is list and 1 <= len(records) <= 256, "BATCH_SIZE_INVALID")
    for record in records:
        require(type(record) is dict and record.get("split") == "train", "TRAIN_RECORD_REQUIRED")
        require("public" in record and "target_binding" in record, "RECORD_FIELDS_MISSING")
        validate_public(record["public"])
        target = record["target_binding"]
        require(type(target) is int and target in (0, 1, 2), "BINDING_TARGET_INVALID")
        record_hash = canonical_sha256(record)
        require(record_hash in registry and registry[record_hash] == record, "RECORD_OUTSIDE_TRAINING_PLAN")
    return [record["public"] for record in records], [record["target_binding"] for record in records]


class BindingLearner:
    def __init__(self, model, tokenizer, optimizer, run_id, scope_names=None, *, training_cases):
        require(type(run_id) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", run_id), "RUN_ID_INVALID")
        self._record_registry, self.plan_identity = validate_training_plan(training_cases)
        self.torch, self.device = _cuda()
        from ..policy import CASProgramGenerator, GenericProgramGenerator
        from ..features_v2 import LosslessPublicTokenizer
        require(type(model) in (CASProgramGenerator, GenericProgramGenerator), "EXISTING_CANDIDATE_CLASS_REQUIRED")
        require(type(tokenizer) is LosslessPublicTokenizer, "LOSSLESS_TOKENIZER_REQUIRED")
        require(type(optimizer) is self.torch.optim.AdamW, "STANDARD_ADAMW_REQUIRED")
        self.model, self.tokenizer, self.optimizer, self.run_id = model, tokenizer, optimizer, run_id
        self.scope_names = tuple(sorted(name for name, p in model.named_parameters() if p.requires_grad))
        if scope_names is not None:
            require(type(scope_names) in (list, tuple) and tuple(sorted(scope_names)) == self.scope_names,
                    "DECLARED_SCOPE_MISMATCH")
        require(bool(self.scope_names), "EMPTY_TRAINABLE_SCOPE")
        self.scope_sha256 = canonical_sha256(list(self.scope_names))
        self.source_identity = _sources()
        self.steps = 0
        self._check_scope()

    def _check_scope(self):
        execution_guard()
        params = dict(self.model.named_parameters())
        require(tuple(sorted(name for name, p in params.items() if p.requires_grad)) == self.scope_names,
                "TRAINABLE_SCOPE_CHANGED")
        tensors = list(params.values()) + list(self.model.buffers())
        require(all(t.device == self.device for t in tensors), "CPU_OR_MIXED_MODEL_DEVICE")
        wanted = {id(params[name]) for name in self.scope_names}
        actual = [p for group in self.optimizer.param_groups for p in group["params"]]
        require(len(actual) == len(wanted) and {id(p) for p in actual} == wanted,
                "OPTIMIZER_PARAMETER_SCOPE_MISMATCH")
        for group in self.optimizer.param_groups:
            numbers = [group["lr"], group["eps"], group["weight_decay"], *group["betas"]]
            require(all(type(x) in (int, float) and math.isfinite(x) and x >= 0 for x in numbers)
                    and group["lr"] > 0 and group["eps"] > 0 and all(x < 1 for x in group["betas"]),
                    "OPTIMIZER_HYPERPARAMETERS_INVALID")
        require(_sources() == self.source_identity, "CANDIDATE_SOURCE_CHANGED")
        return params

    def _snapshot(self, state=None):
        torch = self.torch
        manifest = {}
        state = self.model.state_dict() if state is None else state
        for name, tensor in sorted(state.items()):
            require(tensor.device == self.device, "CPU_OR_MIXED_STATE_DEVICE")
            require(bool(torch.isfinite(tensor).all().item()), "NONFINITE_MODEL_STATE")
            # CUDA -> host is serialization only; no numpy or CPU neural work.
            raw = tensor.detach().contiguous().reshape(-1).view(torch.uint8).cpu()
            payload = bytes(raw.untyped_storage())
            require(len(payload) == tensor.numel() * tensor.element_size(), "TENSOR_STORAGE_LENGTH_MISMATCH")
            manifest[name] = {"dtype": str(tensor.dtype), "shape": list(tensor.shape),
                              "sha256": sha256(payload).hexdigest()}
        return canonical_sha256(manifest), manifest

    def _logits(self, publics):
        from ..codec import BINDING_TOKEN_IDS, BOS_ID, validate_public
        from ..policy import encode_batch
        require(type(publics) is list and 1 <= len(publics) <= 256, "BATCH_SIZE_INVALID")
        for public in publics:
            validate_public(public)
        batch = encode_batch(publics, self.tokenizer, device=self.device)
        bos = self.torch.full((len(publics), 1), BOS_ID, dtype=self.torch.long, device=self.device)
        logits = self.model(batch, bos)["token_logits"][:, 0, list(BINDING_TOKEN_IDS)]
        require(tuple(logits.shape) == (len(publics), 3) and logits.device == self.device,
                "BINDING_LOGITS_GEOMETRY_INVALID")
        require(bool(self.torch.isfinite(logits).all().item()), "NONFINITE_LOGITS")
        return logits

    def teach(self, records):
        publics, targets = validate_records(records, self._record_registry)
        params = self._check_scope()
        before, before_manifest = self._snapshot()
        torch = self.torch
        self.model.train()
        self.optimizer.zero_grad(set_to_none=True)
        logits = self._logits(publics)
        labels = torch.tensor(targets, dtype=torch.long, device=self.device)
        loss = torch.nn.functional.cross_entropy(logits, labels)
        require(bool(torch.isfinite(loss).item()), "NONFINITE_LOSS")
        loss.backward()
        gradients = []
        for name in self.scope_names:
            gradient = params[name].grad
            if gradient is not None:
                require(gradient.device == self.device and bool(torch.isfinite(gradient).all().item()),
                        "NONFINITE_OR_NONCUDA_GRADIENT")
                if bool((gradient != 0).any().item()):
                    gradients.append(name)
        # Check the optimizer identity immediately before the only update site.
        self._check_scope()
        self.optimizer.step()
        self.torch.cuda.synchronize(self.device)
        after, after_manifest = self._snapshot()
        require(set(before_manifest) == set(after_manifest), "MODEL_STATE_KEYS_CHANGED")
        changed = sorted(name for name in before_manifest if before_manifest[name] != after_manifest[name])
        require(set(changed).issubset(self.scope_names), "OUT_OF_SCOPE_STATE_CHANGED")
        self.steps += 1
        return {"schema": SCHEMA, "run_id": self.run_id, "execution_mode": "cuda",
                "provider_identity_proved": False, "provider_identity_requirement": "independent launch receipt",
                "device": str(self.device), "gpu_name": torch.cuda.get_device_name(self.device),
                "scope_names": list(self.scope_names), "scope_sha256": self.scope_sha256,
                **self.plan_identity,
                "gradient_parameter_names": gradients, "changed_parameter_names": changed,
                "before_checkpoint_sha256": before, "after_checkpoint_sha256": after,
                "checkpoint_digest_kind": "model_state_tensor_manifest_sha256",
                "input_sha256": canonical_sha256(publics), "target_sha256": canonical_sha256(targets),
                "batch_size": len(records), "optimizer_steps": 1, "cumulative_optimizer_steps": self.steps,
                "loss": float(loss.detach().item()), "accepted_weights_updated": False}

    def predict(self, publics):
        self._check_scope()
        self.model.eval()
        with self.torch.no_grad():
            return self._logits(publics).argmax(-1).tolist()

    def state_identity(self):
        self._check_scope()
        state_sha, _ = self._snapshot()
        return {"run_id": self.run_id, "checkpoint_sha256": state_sha,
                "scope_names": list(self.scope_names), "scope_sha256": self.scope_sha256,
                **self.plan_identity,
                "checkpoint_digest_kind": "model_state_tensor_manifest_sha256"}

    def save_checkpoint(self, path):
        self._check_scope()
        path = Path(path).absolute()
        require(path.suffix == ".pt" and path.parent.is_dir(), "CHECKPOINT_PATH_INVALID")
        require(not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
                        for p in (path, *path.parents)), "CHECKPOINT_LINK_PATH_REJECTED")
        state_sha, _ = self._snapshot()
        payload = {"schema": SCHEMA, "run_id": self.run_id, "steps": self.steps,
                   "family": type(self.model).__name__, "config": asdict(self.model.config),
                   "source_identity": self.source_identity, "scope_names": list(self.scope_names),
                   "plan_identity": self.plan_identity,
                   "tokenizer": self.tokenizer.to_dict(), "tokenizer_digest": self.tokenizer.digest,
                   "model_state_sha256": state_sha, "model": self.model.state_dict(),
                   "optimizer": self.optimizer.state_dict(), "accepted_weights_updated": False}
        with path.open("xb") as stream:  # Never replace accepted or previous candidate files.
            self.torch.save(payload, stream)
        return {"path": str(path), "sha256": sha256(path.read_bytes()).hexdigest(),
                "model_state_sha256": state_sha, "steps": self.steps, "run_id": self.run_id}

    def restore_checkpoint(self, path, expected_sha256):
        self._check_scope()
        path = Path(path)
        require(sha256(path.read_bytes()).hexdigest() == expected_sha256, "CHECKPOINT_FILE_DIGEST_MISMATCH")
        payload = self.torch.load(path, map_location=self.device, weights_only=True)
        require(type(payload) is dict, "CHECKPOINT_OBJECT_REQUIRED")
        expected = {"schema": SCHEMA, "run_id": self.run_id, "family": type(self.model).__name__,
                    "config": asdict(self.model.config), "source_identity": self.source_identity,
                    "plan_identity": self.plan_identity,
                    "scope_names": list(self.scope_names), "tokenizer": self.tokenizer.to_dict(),
                    "tokenizer_digest": self.tokenizer.digest, "accepted_weights_updated": False}
        require(all(payload.get(k) == v for k, v in expected.items()), "CHECKPOINT_IDENTITY_MISMATCH")
        require(type(payload.get("steps")) is int and payload["steps"] >= 0, "CHECKPOINT_STEPS_INVALID")
        current = self.model.state_dict()
        loaded = payload.get("model")
        require(type(loaded) in (dict, type(current)) and set(loaded) == set(current), "CHECKPOINT_MODEL_KEYS_INVALID")
        require(all(self.torch.is_tensor(loaded[k]) and loaded[k].shape == current[k].shape
                    and loaded[k].dtype == current[k].dtype for k in current), "CHECKPOINT_MODEL_GEOMETRY_INVALID")
        require(self._snapshot(loaded)[0] == payload.get("model_state_sha256"), "CHECKPOINT_STATE_DIGEST_MISMATCH")
        self.model.load_state_dict(payload["model"], strict=True)
        self.optimizer.load_state_dict(payload["optimizer"])
        self._check_scope()
        state_sha, _ = self._snapshot()
        require(state_sha == payload["model_state_sha256"], "CHECKPOINT_STATE_DIGEST_MISMATCH")
        self.steps = payload["steps"]
        return {"run_id": self.run_id, "steps": self.steps, "model_state_sha256": state_sha,
                "boundary": "Checkpoint load only; retention and restart predictions still require evaluation."}


def build_matched_learners(training_cases, *, run_id, seed=7, config=None, learning_rate=0.003):
    """Create new matched candidates on an explicitly enabled CUDA worker only."""
    require(type(learning_rate) in (int, float) and math.isfinite(learning_rate) and learning_rate > 0,
            "LEARNING_RATE_INVALID")
    registry, _ = validate_training_plan(training_cases)
    from .data import make_public
    train_publics = [make_public(case) for case in sorted(training_cases, key=lambda row: row["family_id"])]
    train_publics.extend(registry[key]["public"] for key in sorted(registry))
    torch, device = _cuda()
    from ..features_v2 import LosslessPublicTokenizer
    from ..policy import PolicyConfig, build_matched_policies
    config = PolicyConfig() if config is None else config
    tokenizer = LosslessPublicTokenizer.fit_train(train_publics, max_length=config.max_length)
    cas, generic, matching = build_matched_policies(tokenizer, config, seed=seed, device=device)
    learners = {family: BindingLearner(model, tokenizer,
                torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=0.0), run_id,
                training_cases=training_cases)
                for family, model in (("cas", cas), ("generic", generic))}
    return learners, matching
