"""Separate train/validation and private evaluation files; JSON and bytes only."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import stat

from . import data

SCHEMA = "cas-meta2-condition-skill-dataset/9"
FILES = ("train.json", "validation.json", "test_instances.public.json",
         "test_instances.targets.json", "test_direction_pair.public.json",
         "test_direction_pair.targets.json")
EXPECTED_COUNTS = {"train": 1536, "validation": 384, "test_instances": 384,
                   "test_direction_pair": 384}
MAX_FILE_BYTES = 16 * 1024**2
ROOT = Path(__file__).resolve().parents[2]


def require(condition, code):
    if not condition:
        raise ValueError(code)


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def decoded(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "DUPLICATE_JSON_KEY")
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda _: require(False, "NONFINITE_JSON"))


def safe(path):
    result = Path(path).absolute()
    require(".." not in result.parts and not any(p.is_symlink() or
        getattr(p, "is_junction", lambda: False)() for p in (result, *result.parents)),
        "BUNDLE_PATH_LINK_OR_TRAVERSAL")
    return result


def read_bytes(path):
    path = safe(path)
    info = path.stat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
            and info.st_size <= MAX_FILE_BYTES, "BUNDLE_REGULAR_FILE_BOUND")
    raw = path.read_bytes()
    require(len(raw) == info.st_size, "BUNDLE_CHANGED_DURING_READ")
    return raw


def write_new(path, value):
    raw = encoded(value)
    require(len(raw) <= MAX_FILE_BYTES, "BUNDLE_OUTPUT_BOUND")
    with safe(path).open("xb") as stream:
        stream.write(raw)
    return {"bytes": len(raw), "sha256": sha256(raw).hexdigest()}


def build(output, *, seed=9):
    output = safe(output)
    require(output.is_relative_to(ROOT / "records") and not output.exists()
            and output.parent.is_dir(), "FRESH_SCOPED_DATASET_DIRECTORY_REQUIRED")
    require(type(seed) is int and seed == 9, "FIXED_CURRICULUM_SEED_REQUIRED")
    curriculum = data.build_curriculum(seed=seed)
    report = data.validate_curriculum(curriculum)
    counts = {key: len(value) for key, value in curriculum.items()}
    require(counts == EXPECTED_COUNTS, "DECLARED_SPLIT_COUNTS_CHANGED")
    contents = {"train.json": curriculum["train"], "validation.json": curriculum["validation"]}
    for split in ("test_instances", "test_direction_pair"):
        contents[split + ".public.json"] = [task["public"] for task in curriculum[split]]
        contents[split + ".targets.json"] = [
            {"task_id": task["public"]["task_id"], "target": task["target"],
             "provenance": task["provenance"]} for task in curriculum[split]]
    require(set(contents) == set(FILES), "DATASET_FILES_CHANGED")
    output.mkdir()
    identities = {name: write_new(output / name, contents[name]) for name in FILES}
    manifest = {"schema": SCHEMA, "seed": seed, "counts": counts,
        "files": identities, "construction_validation": report,
        "data_source_sha256": sha256(read_bytes(Path(data.__file__))).hexdigest(),
        "bundle_source_sha256": sha256(read_bytes(__file__)).hexdigest(),
        "claims": {"data_constructed_and_checked": True, "learning_measured": False,
                   "runtime_admission": False, "new_noetic_semantics": False,
                   "natural_language_understanding": False},
        "evaluation_targets": {
            "test_instances": "New threshold/margin families with direction pairs seen during training.",
            "test_direction_pair": "New families and the withheld at_most/at_least pair; not unseen programs.",
            "controls": "Evaluation-only transformations; never implicit training augmentation."},
        "target_rule": "bit1 = first-slot comparison; bit2 = second-slot comparison; class = 2*bit1+bit2",
        "training_visibility": ["train.json", "validation.json"],
        "test_target_read_boundary": "Only after both candidate checkpoint choices and test predictions are saved."}
    write_new(output / "manifest.json", manifest)
    return {"path": str(output), "manifest_sha256": sha256(read_bytes(output / "manifest.json")).hexdigest(),
            "counts": counts, "learning_measured": False}


def inspect_structure(dataset):
    """Validate the manifest declaration and builder-source pins only.

    This reads manifest.json and hashes the two builder source files. It never
    reads, hashes, or opens any partition file, so calling it cannot leak
    private test targets into a learner.
    """
    dataset = safe(dataset)
    require(dataset.is_dir(), "DATASET_DIRECTORY_REQUIRED")
    raw = read_bytes(dataset / "manifest.json")
    pin = sha256(raw).hexdigest()
    manifest = decoded(raw)
    require(manifest.get("schema") == SCHEMA and type(manifest.get("seed")) is int
            and manifest["seed"] == 9 and manifest.get("counts") == EXPECTED_COUNTS,
            "DATASET_DECLARATION_CHANGED")
    require(set(manifest.get("files", {})) == set(FILES), "DATASET_FILE_COVERAGE")
    require(manifest.get("data_source_sha256") == sha256(read_bytes(Path(data.__file__))).hexdigest()
            and manifest.get("bundle_source_sha256") == sha256(read_bytes(__file__)).hexdigest(),
            "DATASET_BUILDER_SOURCE_CHANGED")
    return manifest, pin


def inspect(dataset, *, expected_manifest_sha256=None):
    """Hash every file, but do not parse any task or target file.

    Hash-reading private files is byte integrity only and must never be used as
    the boundary that proves targets stayed unopened. Learners use
    inspect_structure and keep private-file reads outside their pre-seal stage.
    """
    manifest, pin = inspect_structure(dataset)
    require(expected_manifest_sha256 is None or pin == expected_manifest_sha256,
            "DATASET_MANIFEST_CHANGED")
    for name, item in manifest["files"].items():
        payload = read_bytes(dataset / name)
        require(type(item) is dict and set(item) == {"bytes", "sha256"}
                and type(item["bytes"]) is int and len(payload) == item["bytes"]
                and sha256(payload).hexdigest() == item["sha256"], "DATASET_FILE_CHANGED:" + name)
    return manifest, pin


def read_partitions(dataset, names, expected_manifest_sha256=None):
    """Parse only explicitly requested partitions; unrequested files stay unread.

    Only the manifest declaration and builder-source pins are checked beyond the
    requested files. A learner that requests only train/validation therefore
    never reads private test target bytes before its sealed boundary. Unrequested
    partition integrity is checked when those files are actually requested.
    """
    require(type(names) in (list, tuple) and names and len(set(names)) == len(names)
            and set(names).issubset(FILES), "EXPLICIT_DATASET_PARTITIONS_REQUIRED")
    manifest, pin = inspect_structure(dataset)
    require(expected_manifest_sha256 is None or pin == expected_manifest_sha256,
            "DATASET_MANIFEST_CHANGED")
    partitions = {}
    for name in names:
        payload = read_bytes(safe(dataset) / name)
        require(sha256(payload).hexdigest() == manifest["files"][name]["sha256"],
                "PARTITION_CHANGED_AFTER_INSPECTION")
        rows = decoded(payload)
        split = name.split(".")[0]
        require(type(rows) is list and len(rows) == EXPECTED_COUNTS[split], "PARTITION_COUNT_CHANGED")
        seen = set()
        for row in rows:
            if name in ("train.json", "validation.json"):
                data.validate_task(row)
                require(row["provenance"]["split"] == split, "TRAINING_PARTITION_MISPLACED")
                task_id = row["public"]["task_id"]
            elif name.endswith(".public.json"):
                data.validate_public(row)
                task_id = row["task_id"]
            else:
                require(type(row) is dict and set(row) == {"task_id", "target", "provenance"}
                        and row["provenance"]["split"] == split, "PRIVATE_TARGET_ROW_CHANGED")
                target = row["target"]
                require(type(target) is dict and set(target) == {"class_index", "symbol", "bits"}
                        and type(target["class_index"]) is int and 0 <= target["class_index"] <= 3
                        and target["symbol"] == "L" + str(target["class_index"])
                        and type(target["bits"]) is list and len(target["bits"]) == 2
                        and all(type(bit) is int and bit in (0, 1) for bit in target["bits"])
                        and target["bits"] == [target["class_index"] // 2, target["class_index"] % 2],
                        "PRIVATE_TARGET_SHAPE_CHANGED")
                task_id = row["task_id"]
            require(type(task_id) is str and task_id not in seen, "DUPLICATE_PARTITION_TASK")
            seen.add(task_id)
        partitions[name] = rows
    return {"manifest": manifest, "manifest_sha256": pin, "partitions": partitions}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output")
    args = parser.parse_args()
    print(json.dumps(build(args.output), sort_keys=True))


if __name__ == "__main__":
    main()
