"""Retrospective endpoint containment comparison from the RETAINED checkpoints.

Owner-directed (2026-09-10). GRAPH6_CURRICULUM_002 attempt 004's registered
execution gate asked that "only the operation:^6 parameter group may change; the
containment report must name any forbidden change". That digest-level containment
report was NOT produced by the segmented training path, and an argument from the
optimizer's construction is not evidence. This tool recovers what the retained
state files can answer, using NOTHING but the Python standard library: no torch,
no GPU, no neural execution, no network.

HOW IT WORKS
A ``torch.save`` file is a ZIP archive: ``data.pkl`` (the object graph) plus raw
little-endian storage buffers under ``data/<n>``. The object graph is unpickled
with stand-ins for the torch classes, so each stored tensor keeps its parameter
NAME, dtype, shape, stride and storage offset. Every component's bytes are then
hashed from the raw buffer.

WHAT THIS ESTABLISHES (and what it does not)
Establishes: which STORED components are byte-identical and which changed between
the retained endpoints (initial / 64 / 256 updates) of each learner.
Does NOT establish: the history between endpoints (no intermediate state was
saved), the behaviour of components that were never saved, or optimizer values
for parameters absent from the file. It is labelled a RETROSPECTIVE ENDPOINT
COMPARISON throughout and must never be reported as the registered containment
report.
"""
from __future__ import annotations

import argparse
import io
import json
import pickle
import sys
import zipfile
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "cas-graph-training-retrospective-containment/1"
CHECKPOINT_PROTOCOL = ("control", "varied")
CHECKPOINT_STEPS = (0, 64, 256)
BOUNDARY = ("RETROSPECTIVE ENDPOINT COMPARISON ONLY: it compares components STORED "
            "in the retained checkpoints. It is not the registered digest-level "
            "containment report, it cannot show when a change happened between "
            "endpoints, and it says nothing about components that were never saved.")


class StorageRef:
    """A torch storage: identified by its key inside the archive."""

    def __init__(self, key, location=None, numel=None):
        self.key = key
        self.location = location
        self.numel = numel

    def __repr__(self):  # pragma: no cover - debugging aid
        return "StorageRef(%r)" % (self.key,)


class TensorRef:
    """A stored tensor: name-free descriptor resolved against a storage."""

    def __init__(self, storage, offset, size, stride, requires_grad=None):
        self.storage = storage
        self.offset = offset
        self.size = tuple(size) if isinstance(size, (list, tuple)) else (size,)
        self.stride = tuple(stride) if isinstance(stride, (list, tuple)) else (stride,)
        self.requires_grad = requires_grad

    @property
    def numel(self):
        total = 1
        for dimension in self.size:
            total *= dimension
        return total


class _Stub:
    """Stand-in for any torch class the payload mentions."""

    def __init__(self, module, name):
        self.module = module
        self.name = name

    def __call__(self, *arguments, **keywords):
        return self

    def __repr__(self):  # pragma: no cover - debugging aid
        return "%s.%s" % (self.module, self.name)


class _Mapping(dict):
    """dict subclass that can also receive a pickle BUILD state."""

    def __setstate__(self, state):  # pragma: no cover - defensive
        if isinstance(state, dict):
            self.update(state)


class CheckpointReader(pickle.Unpickler):
    def __init__(self, stream):
        super().__init__(stream, encoding="utf-8")
        self.storage_classes = set()

    def persistent_load(self, pid):
        # ('storage', storage_type, key, location, numel) in torch >= 1.6
        if isinstance(pid, tuple) and len(pid) >= 3:
            storage_type = pid[1]
            if hasattr(storage_type, "name"):
                self.storage_classes.add(storage_type.name)
            return StorageRef(pid[2], pid[3] if len(pid) > 3 else None,
                              pid[4] if len(pid) > 4 else None)
        raise pickle.UnpicklingError("UNEXPECTED_PERSISTENT_ID")

    def find_class(self, module, name):
        if module == "collections" and name == "OrderedDict":
            return _Mapping
        if module == "torch._utils" and name == "_rebuild_tensor_v2":
            return lambda storage, offset, size, stride, requires_grad=False, hooks=None: (
                TensorRef(storage, offset, size, stride, requires_grad))
        if module == "builtins" and name == "set":
            return set
        if module == "torch" and name.endswith("Storage"):
            return _Stub(module, name)
        return _Stub(module, name)


def component_bytes(archive, tensor):
    """Raw little-endian bytes of one stored tensor, from its storage buffer."""
    key = "data/%s" % tensor.storage.key
    member = next((name for name in archive.namelist() if name.endswith(key)), None)
    if member is None:
        return None
    raw = archive.read(member)
    start = tensor.offset * 4          # float32 payloads in this run
    end = start + tensor.numel * 4
    if tensors_are_contiguous(tensor):
        return raw[start:end]
    return None                        # non-contiguous: not resolved by this tool


def tensors_are_contiguous(tensor):
    expected = 1
    for size, stride in zip(reversed(tensor.size), reversed(tensor.stride)):
        if stride != expected and size > 1:
            return False
        expected *= size
    return True


def read_checkpoint(path):
    with zipfile.ZipFile(path) as archive:
        pickle_member = next(name for name in archive.namelist()
                             if name.endswith("data.pkl"))
        payload = CheckpointReader(io.BytesIO(archive.read(pickle_member))).load()
        components = {}
        for section in ("model", "encoder"):
            block = payload.get(section) or {}
            if not isinstance(block, dict):
                continue
            for name, tensor in block.items():
                if not isinstance(tensor, TensorRef):
                    continue
                body = component_bytes(archive, tensor)
                components["%s.%s" % (section, name)] = {
                    "sha256": sha256(body).hexdigest() if body is not None else None,
                    "shape": list(tensor.size),
                    "numel": tensor.numel,
                    "resolved": body is not None,
                    "requires_grad": tensor.requires_grad}
        optimizer = payload.get("optimizer") or {}
        state = optimizer.get("state") if isinstance(optimizer, dict) else None
        return {
            "path": str(path),
            "bytes": Path(path).stat().st_size,
            "sha256": sha256(Path(path).read_bytes()).hexdigest(),
            "step": payload.get("step"),
            "condition": payload.get("condition"),
            "learner_seed": payload.get("learner_seed"),
            "encoder_seed": payload.get("encoder_seed"),
            "torch_version": payload.get("torch_version"),
            "vocabulary_size": len(payload.get("encoder", {}).get("vocabulary", []) or []),
            "vocabulary_sha256": sha256(
                json.dumps(payload.get("encoder", {}).get("vocabulary") or [],
                           sort_keys=True).encode()).hexdigest(),
            "record_ids": len(payload.get("record_ids") or []),
            "optimizer_state_entries": len(state) if isinstance(state, dict) else None,
            "components": components,
        }


def compare(first, second):
    names = sorted(set(first["components"]) | set(second["components"]))
    changed, unchanged, unresolved = [], [], []
    for name in names:
        left = first["components"].get(name)
        right = second["components"].get(name)
        if left is None or right is None or not left["resolved"] or not right["resolved"]:
            unresolved.append(name)
        elif left["sha256"] != right["sha256"]:
            changed.append({"component": name, "shape": right["shape"]})
        else:
            unchanged.append(name)
    return {"changed": changed, "unchanged": unchanged, "unresolved": unresolved}


def build_report(checkpoint_dir):
    checkpoints = {}
    for condition in CHECKPOINT_PROTOCOL:
        for step in CHECKPOINT_STEPS:
            for seed in (20260913, 20260914, 20260915):
                name = "%s_seed%d_step%03d.pt" % (condition, seed, step)
                path = Path(checkpoint_dir) / name
                if path.is_file():
                    checkpoints[(condition, seed, step)] = read_checkpoint(path)
    learners = []
    for condition in CHECKPOINT_PROTOCOL:
        for seed in (20260913, 20260914, 20260915):
            initial = checkpoints.get((condition, seed, 0))
            at64 = checkpoints.get((condition, seed, 64))
            at256 = checkpoints.get((condition, seed, 256))
            if not all((initial, at64, at256)):
                continue
            learners.append({
                "condition": condition, "learner_seed": seed,
                "initial_vs_64": compare(initial, at64),
                "initial_vs_256": compare(initial, at256),
                "64_vs_256": compare(at64, at256),
                "encoder_projection_unchanged_across_endpoints":
                    (initial["components"].get("encoder.projection", {}).get("sha256")
                     == at256["components"].get("encoder.projection", {}).get("sha256")),
                "vocabulary_unchanged":
                    initial["vocabulary_sha256"] == at256["vocabulary_sha256"],
                "optimizer_state_entries": {str(step): checkpoints[(condition, seed, step)]
                                            ["optimizer_state_entries"]
                                            for step in CHECKPOINT_STEPS},
                "checkpoint_sha256": {str(step): checkpoints[(condition, seed, step)]["sha256"]
                                      for step in CHECKPOINT_STEPS},
            })
    stored_components = sorted({name for entry in checkpoints.values()
                                for name in entry["components"]})
    projections = sorted({entry["components"].get("encoder.projection", {}).get("sha256")
                          for entry in checkpoints.values()})
    vocabularies = sorted({entry["vocabulary_sha256"] for entry in checkpoints.values()})
    model_components = [name for name in stored_components
                        if name.startswith("model.")]
    moved = sorted({item["component"]
                    for learner in learners
                    for item in learner["initial_vs_256"]["changed"]})
    still = sorted({name for name in model_components} - set(moved))
    return {
        "schema": SCHEMA,
        "method": ("torch.save zip archive -> pickle object graph with stand-ins for "
                   "torch classes -> per-component sha256 over the raw storage bytes "
                   "(Python standard library only: no torch, no GPU, no neural run)"),
        "checkpoint_dir": str(checkpoint_dir),
        "checkpoints_read": len(checkpoints),
        "learners_compared": len(learners),
        "stored_components": stored_components,
        "encoder_projection_sha256_across_all_checkpoints": projections,
        "vocabulary_sha256_across_all_checkpoints": vocabularies,
        "components_that_changed_by_endpoint_256": moved,
        "stored_model_components_that_did_not_change": still,
        "learners": learners,
        "conclusion": {
            "model_matrices_changed": moved,
            "encoder_projection_frozen_and_identical_everywhere": len(projections) == 1,
            "tokenizer_vocabulary_identical_everywhere": len(vocabularies) == 1,
            "registered_containment_report_status": (
                "STILL MISSING as registered evidence: this tool compares only the "
                "components STORED in the checkpoints. Parameters that were never "
                "saved (for example any parameter outside the checkpointed module "
                "and encoder projection) cannot be compared, and the intermediate "
                "history between endpoints does not exist."),
        },
        "boundary": BOUNDARY,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint-dir", required=True)
    parser.add_argument("--output")
    arguments = parser.parse_args(argv)
    report = build_report(arguments.checkpoint_dir)
    raw = (json.dumps(report, sort_keys=True, indent=2) + "\n").encode("utf-8")
    if arguments.output:
        path = Path(arguments.output).absolute()
        if not path.exists():
            with path.open("xb") as stream:
                stream.write(raw)
    sys.stdout.write(raw.decode("utf-8"))
    sys.stdout.write("sha256: %s\n" % sha256(raw).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
