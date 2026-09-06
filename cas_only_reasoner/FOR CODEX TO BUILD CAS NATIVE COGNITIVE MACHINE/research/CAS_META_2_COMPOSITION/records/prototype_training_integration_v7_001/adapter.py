"""Exact train-only prototype import, prepared separately from frozen v6.

Parent-only API: validation reads the existing private test file to check split
boundaries. Do not use this as a neural trainer loader. No generation or model
execution is provided. A later versioned public-only loader is still required.
"""
from __future__ import annotations
import argparse
from collections import Counter
from copy import deepcopy
from dataclasses import asdict
from hashlib import sha256
import importlib
import importlib.abc
import importlib.util
import io
import json
from pathlib import Path
import re
import struct
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FROZEN_SOURCE = "acbb266fbcdb6efcd69808f6f0f9b7b1e36b7ed0"
TASKS_SHA256 = "ed6bb0978d34b549917e1ea1b846091f103577936f846bc01db152b19ddbac46"
PROTOTYPE = "records/contrast_curriculum_v6_probe_001"
SCHEMA = "cas-meta2-prototype-training-integration/7"
HELDOUT = ("validation.json", "test_public.json", "test_private.json")
FILES = ("train.json", *HELDOUT, "base_train.json", "base_manifest.json",
         "training_imports.json", "tokenizer.json")
FROZEN_FILES = (
    "cas_meta2/__init__.py", "cas_meta2/ir.py", "cas_meta2/codec.py",
    "cas_meta2/curriculum.py", "cas_meta2/curriculum_v2.py", "cas_meta2/curriculum_v3.py",
    "cas_meta2/features_v2.py", "cas_meta2/exclusions_v3.json",
    "cas_meta2/development_exclusions_v3.json", "cas_meta2/contrast_v6/__init__.py",
    "cas_meta2/contrast_v6/curriculum.py", "cas_meta2/contrast_v6/data.py",
    *(PROTOTYPE + "/" + name for name in ("tasks.json", "receipt.json", "build.py", "verify.py")),
)
FORBIDDEN = frozenset(("torch", "tensorflow", "jax", "cupy", "casformer", "cas_cjt", "boto3", "botocore"))
MAX_BYTES = 32 * 1024 * 1024


class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in FORBIDDEN:
            raise RuntimeError("LOCAL_NEURAL_OR_PROVIDER_IMPORT_FORBIDDEN:" + fullname)
        return None


def require(value, reason):
    if not value:
        raise ValueError(reason)


def digest(raw):
    return sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "DUPLICATE_JSON_KEY")
            result[key] = value
        return result
    def constant(value):
        raise ValueError("NONFINITE_JSON_CONSTANT:" + value)
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


def no_links(path):
    path = Path(path).absolute()
    require(not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
                    for p in (path, *path.parents)), "LINK_PATH_REFUSED")
    return path


def read(path):
    path = no_links(path)
    require(path.is_file() and path.stat().st_size <= MAX_BYTES, "INPUT_FILE_BOUND")
    with path.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    require(len(raw) <= MAX_BYTES, "INPUT_FILE_BOUND")
    return raw


def directory(path, names):
    path = no_links(path)
    require(path.is_dir() and {p.name for p in path.iterdir()} == set(names), "DIRECTORY_CONTENTS_INVALID")
    for name in names:
        require(no_links(path / name).is_file(), "REGULAR_FILE_REQUIRED")
    return path


def source_identity(root=ROOT):
    """Compare every imported frozen helper/input with binary Git objects first."""
    root = no_links(root).resolve()
    repo = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=root,
        check=True, capture_output=True, text=True, timeout=30).stdout.strip()).resolve()
    names = [(root / name).relative_to(repo).as_posix() for name in FROZEN_FILES]
    result = subprocess.run(["git", "-C", str(repo), "cat-file", "--batch"],
        input="".join(FROZEN_SOURCE + ":" + name + "\n" for name in names).encode(),
        check=True, capture_output=True, timeout=60)
    stream, files = io.BytesIO(result.stdout), {}
    for relative, name in zip(FROZEN_FILES, names, strict=True):
        header = stream.readline().decode().strip().split()
        require(len(header) == 3 and header[1] == "blob", "FROZEN_GIT_OBJECT_MISSING:" + relative)
        raw = stream.read(int(header[2]))
        require(len(raw) == int(header[2]) and stream.read(1) == b"\n", "INVALID_GIT_BLOB_RESPONSE")
        observed = read(root / relative)
        require(observed == raw, "FROZEN_SOURCE_BYTES_CHANGED:" + relative)
        files[relative] = digest(raw)
    require(stream.read() == b"", "TRAILING_GIT_BLOB_RESPONSE")
    require(files[PROTOTYPE + "/tasks.json"] == TASKS_SHA256, "ORIGINAL_PROTOTYPE_PIN_MISMATCH")
    return {"frozen_source_sha": FROZEN_SOURCE, "frozen_files_sha256": files,
            "adapter_sha256": digest(read(Path(__file__))), "adapter_schema": SCHEMA}


def _file_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


class Context:
    def __init__(self, root=ROOT):
        self.root = Path(root).resolve()
        require(not any(n.split(".")[0] in FORBIDDEN for n in sys.modules),
                "PRELOADED_NEURAL_OR_PROVIDER_MODULE_REFUSED")
        self.source = source_identity(self.root)
        sys.meta_path.insert(0, Guard())
        for name, module in tuple(sys.modules.items()):
            if name == "cas_meta2" or name.startswith("cas_meta2."):
                expected = self.root / ("cas_meta2/__init__.py" if name == "cas_meta2"
                                       else name.replace(".", "/") + ".py")
                if name == "cas_meta2.contrast_v6":
                    expected = self.root / "cas_meta2/contrast_v6/__init__.py"
                require(getattr(module, "__file__", None) is not None
                        and Path(module.__file__).resolve() == expected.resolve(),
                        "UNTRUSTED_PRELOADED_SOURCE:" + name)
        sys.path.insert(0, str(self.root))
        self.c = importlib.import_module("cas_meta2.contrast_v6.curriculum")
        self.d = importlib.import_module("cas_meta2.contrast_v6.data")
        self.builder = _file_module(self.root / PROTOTYPE / "build.py", "pinned_prototype_builder_v7")
        self.verifier = _file_module(self.root / PROTOTYPE / "verify.py", "pinned_prototype_verifier_v7")
        self.assert_unchanged()

    def assert_unchanged(self):
        require(source_identity(self.root) == self.source, "SOURCE_CHANGED_DURING_OPERATION")


def check_original_records(tasks, receipt, ctx):
    """Frozen parser, program checks, pair checks, and independent leaf comparison."""
    c = ctx.c
    require(type(tasks) is list and len(tasks) == 256, "EXACT_256_ORIGINAL_TASKS_REQUIRED")
    require(type(receipt) is dict and receipt["task_count"] == 256 and receipt["pair_count"] == 128
            and receipt["tasks_sha256"] == TASKS_SHA256 and len(receipt["pairs"]) == 128,
            "ORIGINAL_PAIR_RECEIPT_INVALID")
    by_id = {t["task_id"]: t for t in tasks}
    require(len(by_id) == 256, "ORIGINAL_TASK_IDS_DUPLICATED")
    counts, used, graphs, payload_owner = Counter(), set(), set(), {}
    for pair in receipt["pairs"]:
        require(len(pair["task_ids"]) == 2 and not used.intersection(pair["task_ids"]),
                "ORIGINAL_PAIR_COVERAGE_INVALID")
        used.update(pair["task_ids"])
        require(all(name in by_id for name in pair["task_ids"]), "ORIGINAL_PAIR_MEMBER_MISSING")
        left, right = [by_id[name] for name in pair["task_ids"]]
        require(left["public"]["observations"] == right["public"]["observations"]
                and left["target"]["binding"] == right["target"]["binding"],
                "ORIGINAL_PAIR_CONTEXT_CHANGED")
        require(left["public"]["problem"] != right["public"]["problem"], "PUBLIC_CONTRAST_MISSING")
        for side, task in (("left", left), ("right", right)):
            require(set(task) == {"task_id", "public", "target", "provenance", "contrast"},
                    "ORIGINAL_FIELDS_CHANGED")
            require(task["contrast"] == {"pair_id": pair["pair_id"], "family": pair["family"], "side": side},
                    "ORIGINAL_PAIR_IDENTITY_CHANGED")
            require(c.parse_problem(task["public"]) == task["target"], "ORIGINAL_PUBLIC_BINDING_MISMATCH")
            stats = c.validate_program(task["target"]["program"])
            require(stats["max_call_depth"] == pair["depth"] and stats["procedure_count"] == 4
                    and stats["expanded_run_count"] <= 15, "ORIGINAL_PROGRAM_STRUCTURE_CHANGED")
            c.action_to_tokens(task["target"], max_length=256)
            signature = c.graph_signature(task["target"]["program"])
            require(signature not in graphs, "ORIGINAL_GRAPH_DUPLICATED")
            graphs.add(signature)
            provenance = task["provenance"]
            require(provenance["graph_signature"] == signature and provenance["depth"] == pair["depth"]
                    and provenance["evaluation_group"] == "diagnostic_training_probe"
                    and provenance["triplet_id"] is None, "ORIGINAL_PROVENANCE_CHANGED")
            tag = next(o["tag"] for o in task["public"]["observations"] if o["slot"] == task["target"]["binding"])
            require(c.wording.render_problem(task["target"]["program"], tag,
                        tuple(provenance["wording_combination"]),
                        definition_order=provenance["definition_order"]) == task["public"]["problem"],
                    "ORIGINAL_PUBLIC_RENDER_MISMATCH")
            for observation in task["public"]["observations"]:
                payload = struct.pack("<8f", *observation["values"])
                require(payload not in payload_owner or payload_owner[payload] == pair["pair_id"],
                        "ORIGINAL_OBSERVATION_REUSED_ACROSS_PAIRS")
                payload_owner[payload] = pair["pair_id"]
        location = ctx.builder.validate_pair(left["target"]["program"], right["target"]["program"],
                                             pair["family"], pair["depth"])
        a, b = [ctx.verifier.leaves(t["target"]["program"]) for t in (left, right)]
        require(set(a) == set(b), "ORIGINAL_TARGET_SHAPE_CHANGED")
        changed = [path for path in a if a[path] != b[path]]
        require(changed == [tuple(pair["changed_target_path"])] == [tuple(location)],
                "ORIGINAL_PAIR_DECISION_CHANGED")
        counts[str(pair["depth"]) + "/" + pair["family"]] += 1
    require(used == set(by_id), "ORIGINAL_PAIR_COVERAGE_INVALID")
    require(counts == {"2/step_input": 32, "2/call_target": 32, "3/step_input": 32, "3/call_target": 32},
            "ORIGINAL_PAIR_COUNTS_CHANGED")
    require(sorted(graphs) == receipt["exposed_graph_signatures"], "ORIGINAL_GRAPH_INVENTORY_CHANGED")
    return {"tasks": 256, "pairs": 128, "pair_counts": dict(counts),
            "depths": {"2": 128, "3": 128}, "public_meaning_checked": True}


def original(ctx, raw=None):
    raw = read(ctx.root / PROTOTYPE / "tasks.json") if raw is None else raw
    require(type(raw) is bytes and digest(raw) == TASKS_SHA256, "ORIGINAL_PROTOTYPE_BYTES_CHANGED")
    tasks = decode(raw)
    receipt = decode(read(ctx.root / PROTOTYPE / "receipt.json"))
    report = check_original_records(tasks, receipt, ctx)
    return tasks, receipt, report


def reject_reserved(seed):
    require(type(seed) is int and 0 <= seed < 2**63, "EXPLICIT_BASE_SEED_REQUIRED")
    require(seed != 2026092601, "LIVE_V6_REGISTERED_DATASET_REFUSED")


def admit_base(raw, *, expected_sha256, seed, config, excluded, ctx):
    reject_reserved(seed)
    require(set(raw) == {"manifest.json", "train.json", *HELDOUT}, "BASE_FILES_INVALID")
    c, d = ctx.c, ctx.d
    m = d.checked_manifest(raw["manifest.json"], expected_sha256=expected_sha256,
                           seed=seed, config=config, excluded=excluded)
    for name in ("train.json", *HELDOUT):
        require(digest(raw[name]) == m["sha256"][name], "BASE_FILE_DIGEST_MISMATCH:" + name)
    splits = {split: decode(raw[name]) for split, name in
              (("train", "train.json"), ("validation", "validation.json"), ("test", "test_private.json"))}
    report = c.validate({"schema": c.SCHEMA, "seed": seed, "config": asdict(config),
                         "dataset_id": m["dataset_id"], "splits": splits}, excluded=excluded)
    require(canonical(report) == canonical({k: v for k, v in m.items() if k not in {"seed", "config", "sha256"}}),
            "BASE_COLD_MANIFEST_MISMATCH")
    require(canonical(decode(raw["test_public.json"])) == canonical([c.permitted_view(t) for t in splits["test"]]),
            "BASE_PUBLIC_PRIVATE_MAPPING_MISMATCH")
    return m, splits


def check_split_safety(base_splits, originals, ctx):
    graphs = {ctx.c.graph_signature(t["target"]["program"]) for t in originals}
    ids = {t["task_id"] for t in originals}
    payloads = {struct.pack("<8f", *o["values"]) for t in originals for o in t["public"]["observations"]}
    for split in ("validation", "test", "train"):
        for task in base_splits[split]:
            require(task["task_id"] not in ids, "PROTOTYPE_TASK_ID_OVERLAP:" + split)
            require(ctx.c.graph_signature(task["target"]["program"]) not in graphs,
                    "PROTOTYPE_GRAPH_OVERLAP:" + split)
            require(not any(struct.pack("<8f", *o["values"]) in payloads
                            for o in task["public"]["observations"]), "PROTOTYPE_OBSERVATION_OVERLAP:" + split)
    return {"prototype_graph_overlap": False, "prototype_observation_overlap": False,
            "prototype_task_id_overlap": False, "policy": "Exact original records are training-only; no graph-wide exemption."}


def import_map(base_train, originals):
    return {"schema": "cas-meta2-training-import-map/7", "destination_split": "train",
            "source_tasks_sha256": TASKS_SHA256, "original_task_count": 256, "original_pair_count": 128,
            "original_order_preserved": True, "base_prefix_count": len(base_train),
            "records": [{"train_index": len(base_train) + i, "original_index": i,
                "task_id": task["task_id"], "original_record_sha256": digest(canonical(task)),
                "pair_id": task["contrast"]["pair_id"], "side": task["contrast"]["side"],
                "family": task["contrast"]["family"],
                "original_provenance_sha256": digest(canonical(task["provenance"]))}
                for i, task in enumerate(originals)]}


def check_exact_merge(train, base_train, originals, imports):
    require(type(train) is list and len(train) == len(base_train) + 256, "EXACT_APPEND_COUNT_REQUIRED")
    require(canonical(train[:len(base_train)]) == canonical(base_train), "BASE_TRAIN_PREFIX_CHANGED")
    require(canonical(train[len(base_train):]) == canonical(originals), "ORIGINAL_APPEND_CONTENT_OR_ORDER_CHANGED")
    require(canonical(imports) == canonical(import_map(base_train, originals)), "TRAINING_IMPORT_MAP_CHANGED")
    require(imports["destination_split"] == "train", "PROTOTYPE_TRAIN_ONLY_REQUIRED")


def token_and_counts(splits, test_public, ctx):
    c = ctx.c
    train, validation = splits["train"], splits["validation"]
    tokenizer = c.LosslessPublicTokenizer.fit_train([t["public"] for t in train], max_length=1024)
    counts, maxima = {}, {}
    train_tokens = {token for t in train for token in c.action_to_tokens(t["target"], max_length=256)}
    for split, tasks in splits.items():
        depths, max_input, max_action = Counter(), 0, 0
        for task in tasks:
            depths[str(c.validate_program(task["target"]["program"])["max_call_depth"])] += 1
            tokenizer.check_round_trip(task["public"])
            max_input = max(max_input, len(tokenizer.encode_public(task["public"])["ids"]))
            tokens = c.action_to_tokens(task["target"], max_length=256)
            max_action = max(max_action, len(tokens))
            require(set(tokens) <= train_tokens, "UNSEEN_POSITIVE_ACTION_TOKEN:" + split)
        counts[split] = {"tasks": len(tasks), "depths": dict(depths)}
        maxima[split] = {"input_tokens": max_input, "action_tokens": max_action}
    for public in test_public:
        tokenizer.encode_public(public)
    return tokenizer, counts, {"tokenizer_fit_split": "train_only", "fit_examples": len(train),
        "tokenizer_sha256": tokenizer.digest, "input_token_limit": 1024, "action_token_limit": 256,
        "actual_maxima": maxima, "positive_action_token_coverage": True}


def materialize(base_raw, *, expected_sha256, seed, config, excluded, ctx):
    m, base = admit_base(base_raw, expected_sha256=expected_sha256, seed=seed, config=config, excluded=excluded, ctx=ctx)
    originals, original_receipt, original_report = original(ctx)
    safety = check_split_safety(base, originals, ctx)
    train = deepcopy(base["train"] + originals)
    imports = import_map(base["train"], originals)
    check_exact_merge(train, base["train"], originals, imports)
    splits = {"train": train, "validation": base["validation"], "test": base["test"]}
    tokenizer, counts, tokens = token_and_counts(splits, decode(base_raw["test_public.json"]), ctx)
    raw = {"train.json": canonical(train) + b"\n", **{name: base_raw[name] for name in HELDOUT},
           "base_train.json": base_raw["train.json"], "base_manifest.json": base_raw["manifest.json"],
           "training_imports.json": canonical(imports) + b"\n", "tokenizer.json": canonical(tokenizer.to_dict()) + b"\n"}
    identity = {"schema": SCHEMA, "source": ctx.source, "base_manifest_sha256": expected_sha256,
                "base_dataset_id": m["dataset_id"], "prototype_tasks_sha256": TASKS_SHA256}
    manifest = {"schema": SCHEMA, "dataset_id": digest(canonical(identity)), "source": ctx.source,
        "base": {"manifest_sha256": expected_sha256, "dataset_id": m["dataset_id"], "seed": seed,
                 "config": asdict(config), "exclusions_sha256": digest(canonical(sorted(excluded))),
                 "exclusion_count": len(excluded), "splits": m["splits"]},
        "prototype": {**original_report, "source_path": PROTOTYPE + "/tasks.json",
            "tasks_sha256": TASKS_SHA256,
            "receipt_sha256": digest(read(ctx.root / PROTOTYPE / "receipt.json")),
            "allowed_split": "train", "fresh_evaluation": False, "original_provenance_preserved": True},
        "splits": counts, "training_append_count": 256, "pair_members_kept_together": True,
        "heldout_bytes_unchanged": {name: digest(raw[name]) for name in HELDOUT},
        "split_safety": safety, "tokens": tokens,
        "sha256": {name: digest(value) for name, value in raw.items()},
        "neural_execution": False, "native_outcomes_checked": False, "training_performed": False,
        "parent_reads_private_test_targets": True,
        "boundary": "Exact 256 known prototype records appended only to training. Existing held-out bytes unchanged. Parent-only preparation, not a trainer loader, new learning result, or fresh evaluation."}
    return raw, manifest


def validate_bundle(path, *, expected_sha256, seed, config, excluded, ctx=None):
    """Parent-only cold verification, including existing private test targets."""
    reject_reserved(seed)
    ctx = ctx or Context()
    path = directory(path, (*FILES, "manifest.json"))
    manifest_raw = read(path / "manifest.json")
    require(type(expected_sha256) is str and re.fullmatch("[0-9a-f]{64}", expected_sha256)
            and digest(manifest_raw) == expected_sha256, "EXTERNAL_V7_MANIFEST_DIGEST_MISMATCH")
    manifest = decode(manifest_raw)
    require(type(manifest) is dict and manifest.get("schema") == SCHEMA, "V7_MANIFEST_SCHEMA_REQUIRED")
    raw = {name: read(path / name) for name in FILES}
    require(manifest.get("sha256") == {name: digest(value) for name, value in raw.items()},
            "V7_FILE_DIGEST_MISMATCH")
    require(manifest.get("source") == ctx.source, "V7_SOURCE_IDENTITY_MISMATCH")
    base_raw = {"manifest.json": raw["base_manifest.json"], "train.json": raw["base_train.json"],
                **{name: raw[name] for name in HELDOUT}}
    base_m = decode(base_raw["manifest.json"])
    for name in HELDOUT:
        require(digest(raw[name]) == base_m["sha256"][name], "HELDOUT_BYTES_CHANGED:" + name)
    originals, _, _ = original(ctx)
    check_exact_merge(decode(raw["train.json"]), decode(raw["base_train.json"]), originals,
                      decode(raw["training_imports.json"]))
    expected_raw, expected = materialize(base_raw, expected_sha256=manifest["base"]["manifest_sha256"],
        seed=seed, config=config, excluded=excluded, ctx=ctx)
    require(raw == expected_raw and canonical(manifest) == canonical(expected), "V7_COLD_RECONCILIATION_MISMATCH")
    ctx.assert_unchanged()
    return {"schema": "cas-meta2-prototype-integration-validation/7", "completed": True,
            "manifest_sha256": expected_sha256, "dataset_id": manifest["dataset_id"],
            "splits": manifest["splits"], "prototype_tasks": 256, "prototype_pairs": 128,
            "heldout_bytes_unchanged": manifest["heldout_bytes_unchanged"],
            "tokenizer_fit_examples": manifest["tokens"]["fit_examples"],
            "parent_reads_private_test_targets": True, "training_performed": False}


def merge(source, output, *, expected_sha256, seed, config, excluded, ctx=None):
    """Append exact originals; no regeneration, filtering, repartitioning or training."""
    reject_reserved(seed)
    ctx = ctx or Context()
    source = directory(source, ("manifest.json", "train.json", *HELDOUT))
    output = no_links(output)
    require(output.resolve().is_relative_to(HERE.resolve()) and output.resolve() != HERE.resolve()
            and not output.exists(), "NEW_V7_RECORD_OUTPUT_REQUIRED")
    raw = {name: read(source / name) for name in ("manifest.json", "train.json", *HELDOUT)}
    contents, manifest = materialize(raw, expected_sha256=expected_sha256, seed=seed,
                                    config=config, excluded=excluded, ctx=ctx)
    ctx.assert_unchanged()
    output.mkdir(parents=True, exist_ok=False)
    for name, payload in {**contents, "manifest.json": canonical(manifest) + b"\n"}.items():
        with (output / name).open("xb") as stream:
            stream.write(payload)
    receipt = validate_bundle(output, expected_sha256=digest(read(output / "manifest.json")),
                              seed=seed, config=config, excluded=excluded, ctx=ctx)
    require(all(read(source / name) == value for name, value in raw.items()), "BASE_INPUT_CHANGED_DURING_MERGE")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("merge", "validate"))
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--config-json", required=True)
    parser.add_argument("--exclusions-json", required=True)
    args = parser.parse_args()
    reject_reserved(args.seed)
    ctx = Context()
    config = ctx.c.Config(**decode(args.config_json.encode())).checked()
    excluded_list = decode(args.exclusions_json.encode())
    require(type(excluded_list) is list and len(excluded_list) == len(set(excluded_list))
            and all(type(value) is str and re.fullmatch("[0-9a-f]{64}", value) for value in excluded_list),
            "EXPLICIT_EXCLUSION_LIST_REQUIRED")
    excluded = frozenset(excluded_list)
    options = dict(expected_sha256=args.manifest_sha256, seed=args.seed, config=config, excluded=excluded, ctx=ctx)
    if args.mode == "merge":
        require(args.output is not None, "EXPLICIT_OUTPUT_REQUIRED")
        result = merge(args.source, args.output, **options)
    else:
        require(args.output is None, "VALIDATE_HAS_NO_OUTPUT")
        result = validate_bundle(args.source, **options)
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

