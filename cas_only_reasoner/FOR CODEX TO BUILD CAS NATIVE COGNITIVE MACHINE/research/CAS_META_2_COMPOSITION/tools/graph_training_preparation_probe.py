"""Connected preparation-path probe for the graph-first ^6 candidate.

Runs the COMPLETE non-neural preparation sequence FROM THE EXPORTED PACKAGE:

    permitted training/practice graph records
        -> adapter.public_records (frozen public records)
        -> cas_meta2.codec.validate_public (frozen validator, inside)
        -> features_v2.LosslessPublicTokenizer.fit_train (tokenizer fitting)
        -> tokenizer.encode_public (actual encoded output)

Both framing conditions (cas, generic) and all three operations are covered.
No neural model is created, no AWS call is made, and no sealed split is read.
Writes byte-verifiable evidence plus a sha256 receipt.

Usage:
    python -B tools/graph_training_preparation_probe.py <package_zip> <evidence_dir>
"""
import json
import sys
import tempfile
import zipfile
from hashlib import sha256
from pathlib import Path


def digest(raw):
    return sha256(raw).hexdigest()


def main(argv):
    package_zip, evidence_dir = Path(argv[1]), Path(argv[2])
    evidence_dir.mkdir(parents=True, exist_ok=True)
    extracted = Path(tempfile.mkdtemp(prefix="graph_prep_probe_"))
    with zipfile.ZipFile(package_zip) as archive:
        archive.extractall(extracted)
    sys.path.insert(0, str(extracted / "research/CAS_META_2_COMPOSITION"))

    from cas_meta2.graph_teaching import trainer, adapter  # noqa: E402
    from cas_meta2.features_v2 import LosslessPublicTokenizer  # noqa: E402
    from cas_meta2.graph_teaching.graph import Graph  # noqa: E402

    records = trainer.training_records(20260909)
    per_arm_op = {}
    position_distribution = {}
    pad_usage = 0
    all_publics = []
    examples = {}
    for arm in ("cas", "generic"):
        arm_tasks = [adapter.public_records(record, arm) for record in records]
        for task in arm_tasks:
            per_arm_op.setdefault(arm, {}).setdefault(task["op"], 0)
            per_arm_op[arm][task["op"]] += 1
            position_distribution[task["encoded_correct_index"]] = (
                position_distribution.get(task["encoded_correct_index"], 0) + 1)
            pad_usage += task["encoded_options"].count("none_of_the_above")
            all_publics.append(task["public"])
            if task["op"] not in examples:
                examples[task["op"]] = {
                    "op": task["op"], "arm": arm,
                    "graph": task["public"]["problem"].split("\n")[0],
                    "question": task["public"]["problem"].split("Choose one option.")[0],
                    "public_choices": task["encoded_options"],
                    "separate_target": task["correct"],
                    "correct_slot": task["encoded_correct_index"]}

    tokenizer = LosslessPublicTokenizer.fit_train(all_publics, max_length=1024)
    encoded_counts = 0
    max_sequence = 0
    for public in all_publics:
        encoded = tokenizer.encode_public(public)
        encoded_counts += 1
        max_sequence = max(max_sequence, len(encoded["ids"]))

    # target-independence: fix the public exercise, swap the private target
    base = next(record for record in records if len(record["options"]) == 3)
    a = dict(base)
    a["correct"] = base["options"][1]
    b = dict(base)
    b["correct"] = base["options"][2]
    task_a = adapter.public_records(a, arm="generic")
    task_b = adapter.public_records(b, arm="generic")
    target_independent = task_a["public"] == task_b["public"]

    # graph facts remain in the model's input
    sample = next(record for record in records if record["op"] == "LIST_PARTS")
    sample_task = adapter.public_records(sample, arm="generic")
    graph_facts_in_input = (Graph.from_record(sample["graph"]).render().rstrip()
                            in sample_task["public"]["problem"])

    evidence = {
        "schema": "cas-graph-training-preparation-evidence/1",
        "connected_path": ["training_records", "public_records",
                           "validate_public", "fit_train", "encode_public"],
        "package": {"source_sha": None, "archive_sha256": digest(package_zip.read_bytes()),
                    "archive_bytes": package_zip.stat().st_size},
        "per_arm_op": per_arm_op,
        "tokenizer": {"fit_examples": tokenizer.fitted_examples,
                      "vocabulary_size": len(tokenizer.vocabulary),
                      "encoded_records": encoded_counts,
                      "max_encoded_sequence_length": max_sequence},
        "correct_position_distribution": position_distribution,
        "target_independence": {"swapped_target_encoded_inputs_identical":
                                target_independent},
        "graph_facts_in_problem_input": graph_facts_in_input,
        "padding": {"pad_token": "none_of_the_above", "usage_count": pad_usage},
        "choice_meanings": {
            "LIST_PARTS": "one COMPLETE sorted list of direct constituents",
            "FIND_SHARED_PART": "ONE shared constituent or 'none'",
            "REACHED_VIA": "the COMPLETE reach label (direct | via:<constituent> | absent)",
        },
        "example_per_op": examples,
        "boundary": {"aws_calls": 0, "model_execution": False,
                     "protected_splits_read": False, "neural_modules_created": False},
    }
    raw = (json.dumps(evidence, sort_keys=True, indent=2) + "\n").encode("utf-8")
    (evidence_dir / "preparation_evidence.json").write_bytes(raw)
    receipt = {"schema": "cas-graph-training-preparation-receipt/1",
               "file": "preparation_evidence.json", "bytes": len(raw),
               "sha256": digest(raw)}
    (evidence_dir / "receipt.json").write_bytes(
        (json.dumps(receipt, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    print(json.dumps({"status": "PREPARATION_PATH_COMPLETE",
                      "per_arm_op": per_arm_op,
                      "position_distribution": position_distribution,
                      "target_independent": target_independent,
                      "graph_facts_in_input": graph_facts_in_input,
                      "encoded_records": encoded_counts,
                      "evidence_sha256": receipt["sha256"]}, sort_keys=True))


if __name__ == "__main__":
    main(sys.argv)
