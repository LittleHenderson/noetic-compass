"""Post-evaluation, data-only diagnosis of one successfully inspected full run.

Reads saved JSON and hashes two frozen source files. It neither imports project
modules nor loads checkpoints, converts features to tensors, or executes models.
Only a new records directory may receive this tool's own receipt and report.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import platform
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE_SHA = "b5f1718e63a2b5cf72b4b606d513d0524b9226ac"
SOURCE_PINS = {
    "cas_meta2/codec.py": "c6ca7f489f91e4b43225b7ffc4d496490f038c18842266b6d5da05570ca29030",
    "cas_meta2/curriculum.py": "c89a03e2f0c381ec4e9c2f8750fd5f5bf6d4b7836ca790d02e256c1cc334e384",
}
INPUT_NAMES = ("tokenizer.json", "dataset/train.json", "dataset/validation.json",
               "dataset/test_public.json", "dataset/test_private.json", "predictions.jsonl")
CAMPAIGN = "cloud_job/campaign/"
MAX_JSON_BYTES = 8 * 1024 * 1024
SPECIAL = ("[PAD]", "[UNK]", "[CLS]", "[SEP]", "[OBS]", "[VALUES]")
ARMS = ("cas_untrained", "cas_trained", "generic_untrained", "generic_trained", "rule")
BOUNDARY = (
    "Post-evaluation diagnosis, not held-out tuning. Counts establish information loss and distribution shifts; "
    "they do not establish that any one change is sufficient to fix task accuracy. Pre-tensor JSON feature "
    "uniqueness does not guarantee distinct downstream neural tensors. No checkpoint/model/tensor execution, "
    "native execution, restart experiment, or stored-native semantic audit is performed."
)


class DiagnosisError(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise DiagnosisError(reason)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value):
    return sha256(canonical(value)).hexdigest()


def no_links(path):
    for item in (path, *path.parents):
        require(not item.is_symlink() and not getattr(item, "is_junction", lambda: False)(), "LINK_PATH_REFUSED")


def file_bytes(path):
    path = Path(path).absolute()
    no_links(path)
    require(path.is_file() and 0 < path.stat().st_size <= MAX_JSON_BYTES, "INPUT_FILE_OR_SIZE_INVALID")
    raw = path.read_bytes()
    require(0 < len(raw) <= MAX_JSON_BYTES, "INPUT_FILE_OR_SIZE_INVALID")
    return raw


def parse_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "DUPLICATE_JSON_FIELD")
            result[key] = value
        return result
    def invalid_constant(_):
        raise DiagnosisError("NONFINITE_JSON")
    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid_constant)
    except (UnicodeError, ValueError, RecursionError) as error:
        if isinstance(error, DiagnosisError):
            raise
        raise DiagnosisError("INVALID_JSON") from error


def safe_member(name):
    require(type(name) is str and name and "\\" not in name and ":" not in name, "UNSAFE_INDEX_PATH")
    path = PurePosixPath(name)
    require(not path.is_absolute() and all(part not in ("", ".", "..") for part in name.split("/")), "UNSAFE_INDEX_PATH")
    return name


def token_words(text):
    return re.findall(r"\w+|[^\w\s]", text.lower(), flags=re.UNICODE)


def encoded_data(public, vocabulary):
    """Exact frozen codec feature data BEFORE any neural dtype conversion."""
    lookup = {word: index for index, word in enumerate(vocabulary)}
    zero = [0.0] * 8
    rows = [("[CLS]", 0, 0, zero)]
    rows += [(word, 0, 0, zero) for word in token_words(public["problem"])]
    rows.append(("[SEP]", 1, 0, zero))
    for observation in sorted(public["observations"], key=lambda item: item["slot"]):
        slot = observation["slot"] + 1
        rows.append(("[OBS]", 2, slot, zero))
        rows += [(word, 2, slot, zero) for word in token_words(observation["tag"])]
        rows.append(("[VALUES]", 3, slot, [float(value) for value in observation["values"]]))
    return rows, {"ids": [lookup.get(row[0], 1) for row in rows], "kinds": [row[1] for row in rows],
                  "slots": [row[2] for row in rows], "values": [row[3] for row in rows]}


def action_tokens(action):
    """Reproduce frozen canonical token ordering, without importing its module."""
    require(type(action) is dict and set(action) == {"program", "binding"}, "SAVED_ACTION_FIELDS_INVALID")
    require(type(action["binding"]) is int and action["binding"] in (0, 1, 2), "SAVED_BINDING_INVALID")
    program = action["program"]
    require(type(program) is dict and set(program) == {"schema", "entry", "procedures"}
            and program["schema"] == "cas-meta2-program/0.1" and program["entry"] == "main", "SAVED_PROGRAM_INVALID")
    procedures = program["procedures"]
    require(type(procedures) is dict and 1 <= len(procedures) <= 16 and "main" in procedures, "SAVED_PROCEDURES_INVALID")
    tokens = ["[BOS]", f"BIND{action['binding']}"]
    for name in sorted(procedures, key=lambda value: (value != "main", value)):
        procedure = procedures[name]
        require(type(procedure) is dict and set(procedure) == {"input", "allowed_cjts", "steps", "return"}, "SAVED_PROCEDURE_INVALID")
        require(type(procedure["steps"]) is list and 1 <= len(procedure["steps"]) <= 32, "SAVED_STEPS_INVALID")
        tokens += ["PROC", name, "ALLOW", *procedure["allowed_cjts"], "ENDALLOW"]
        for step in procedure["steps"]:
            require(type(step) is dict and step.get("kind") in ("RUN", "CALL"), "SAVED_STEP_INVALID")
            target = "cjt_id" if step["kind"] == "RUN" else "procedure"
            require(set(step) == {"kind", target, "input", "output"}, "SAVED_STEP_FIELDS_INVALID")
            tokens += [step["kind"], step[target], step["input"], step["output"]]
        tokens += ["RETURN", procedure["return"], "ENDPROC"]
    return tokens + ["[EOS]"]


def structure(program):
    procedures = program["procedures"]
    def depth(name, active):
        require(name in procedures and name not in active, "SAVED_CALL_GRAPH_INVALID")
        children = [step["procedure"] for step in procedures[name]["steps"] if step["kind"] == "CALL"]
        return 1 + max([depth(child, active | {name}) for child in children] or [0])
    return {"depth": depth(program["entry"], set()), "procedures": len(procedures),
            "nonmain_calls": sum(step["kind"] == "CALL" for name, proc in procedures.items()
                                 if name != "main" for step in proc["steps"])}


def distribution(tasks, vocabulary, training_targets):
    known = set(vocabulary)
    unknown, structural, target_unknown = Counter(), Counter(), Counter()
    lengths, output_lengths, examples = [], [], []
    problem_groups, feature_groups = defaultdict(list), defaultdict(list)
    depth_counts, procedure_counts = Counter(), Counter()
    counts = Counter()
    for index, task in enumerate(tasks):
        public = task["public"]
        rows, features = encoded_data(public, vocabulary)
        lost = [row[0] for row in rows if row[0] not in known]
        words = token_words(public["problem"])
        names = [word for word in words if re.fullmatch(r"(?:p\d+|v\d+|main|arg)", word) and word not in known]
        unknown.update(lost);structural.update(names)
        counts["cases_with_unknown"] += bool(lost)
        counts["cases_with_unknown_structural_names"] += bool(names)
        counts["cases_with_multiple_unknown_structural_names"] += len(set(names)) > 1
        counts["lexical_tokens"] += sum(row[0] not in SPECIAL for row in rows)
        if names:
            examples.append({"case_index": index, "task_id": task["task_id"], "unknown_names": sorted(set(names)),
                             "all_map_to_token_id": 1})
        tokens = action_tokens(task["target"])
        missing = [word for word in tokens if word not in training_targets]
        target_unknown.update(missing)
        counts["cases_with_unseen_target_tokens"] += bool(missing)
        lengths.append(len(rows));output_lengths.append(len(tokens))
        stats = structure(task["target"]["program"])
        depth_counts[stats["depth"]] += 1;procedure_counts[stats["procedures"]] += 1
        counts["nonmain_call_instructions"] += stats["nonmain_calls"]
        counts["cases_with_nonmain_calls"] += bool(stats["nonmain_calls"])
        problem_groups[digest([word if word in known else "[UNK]" for word in words])].append(index)
        feature_groups[digest(features)].append(index)
    return {"examples": len(tasks), **dict(counts), "encoded_token_rows": sum(lengths),
            "unknown_token_count": sum(unknown.values()), "unknown_share_encoded_rows": sum(unknown.values()) / sum(lengths),
            "unknown_frequency": dict(sorted(unknown.items())), "unknown_structural_frequency": dict(sorted(structural.items())),
            "structural_collision_examples": examples, "input_length_min": min(lengths), "input_length_max": max(lengths),
            "input_length_mean": sum(lengths) / len(lengths), "target_token_count": sum(output_lengths),
            "target_length_min": min(output_lengths), "target_length_max": max(output_lengths),
            "target_length_mean": sum(output_lengths) / len(output_lengths),
            "unseen_target_token_frequency": dict(sorted(target_unknown.items())),
            "depth_counts": {str(key): count for key, count in sorted(depth_counts.items())},
            "procedure_count_histogram": {str(key): count for key, count in sorted(procedure_counts.items())},
            "equal_encoded_problem_token_groups": [group for group in problem_groups.values() if len(group) > 1],
            "equal_complete_pre_tensor_feature_data_groups": [group for group in feature_groups.values() if len(group) > 1],
            "neural_tensor_uniqueness_checked": False}


def prediction_summary(predictions, test_tasks):
    report = {}
    for arm in ARMS:
        rejected, depths, names = Counter(), Counter(), Counter()
        counts = Counter();lengths = []
        for row, task in zip(predictions, test_tasks):
            action = row["actions"][arm]
            if action.get("status") == "REJECTED":
                rejected[action["reason"]] += 1
                continue
            tokens = action_tokens(action)
            stats = structure(action["program"])
            counts["saved_decoded_actions"] += 1
            counts["binding_equal_to_target"] += action["binding"] == task["target"]["binding"]
            counts["program_exactly_equal_to_target"] += action["program"] == task["target"]["program"]
            counts["nonmain_calls"] += stats["nonmain_calls"]
            depths[stats["depth"]] += 1;names.update(action["program"]["procedures"].keys());lengths.append(len(tokens))
        report[arm] = {"cases": len(test_tasks), "saved_decoded_actions": 0, "binding_equal_to_target": 0,
                       "program_exactly_equal_to_target": 0, "nonmain_calls": 0, **dict(counts),
                       "saved_decoder_rejections": dict(sorted(rejected.items())),
                       "predicted_depths": {str(key): count for key, count in sorted(depths.items())},
                       "procedure_names": dict(sorted(names.items())), "action_length_range": [min(lengths), max(lengths)] if lengths else None,
                       "native_admission_or_task_correctness_rechecked": False}
    return report


def diagnose(inspection_path, extracted_path=None):
    inspection_path = Path(inspection_path).absolute()
    inspected_raw = file_bytes(inspection_path)
    inspection = parse_json(inspected_raw)
    require(inspection.get("schema") == "cas-meta2-packet-inspection/1"
            and inspection.get("status") == "CAS_META_2_PACKET_FULL_EVIDENCE_VERIFIED"
            and inspection.get("issues") == [] and inspection.get("source_sha") == SOURCE_SHA
            and all(inspection.get(key) is True for key in ("completed_run_evidence_verified", "original_full_index_verified",
                "archive_safety_and_all_included_bytes_checked")), "SUCCESSFUL_FROZEN_FULL_INSPECTION_REQUIRED")
    collection = inspection["collection"]
    require(collection["returncode"] == 0 and collection["partial_evidence"] is False
            and collection["omitted_full_file_count"] == 0 and collection["smoke_only"] is False, "FULL_COLLECTION_REQUIRED")
    extraction = inspection["extraction"]
    require(extraction.get("all_member_bytes_verified_after_write") is True, "VERIFIED_EXTRACTION_REQUIRED")
    extracted = Path(extracted_path or extraction["path"]).absolute()
    no_links(extracted)
    require(extracted.is_dir() and extracted.resolve() == Path(extraction["path"]).resolve(), "EXTRACTION_PATH_MISMATCH")
    index_path = inspection_path.with_name("full_member_index.json")
    require(index_path.resolve() == Path(inspection["full_member_index"]).resolve(), "INDEX_PATH_MISMATCH")
    index_raw = file_bytes(index_path)
    require(sha256(index_raw).hexdigest() == inspection["full_member_index_sha256"], "INDEX_HASH_MISMATCH")
    index = parse_json(index_raw)
    require(index.get("schema") == "cas-meta2-full-packet-index/1"
            and index.get("packet_sha256") == inspection["packet_sha256"], "INDEX_PACKET_BINDING_MISMATCH")
    inventory = {}
    for row in index["entries"]:
        require(type(row) is dict and set(row) == {"path", "bytes", "sha256"}, "INDEX_ENTRY_INVALID")
        name = safe_member(row["path"])
        require(name.casefold() not in inventory and type(row["bytes"]) is int and row["bytes"] >= 0
                and type(row["sha256"]) is str and re.fullmatch(r"[0-9a-f]{64}", row["sha256"]), "INDEX_ENTRY_INVALID")
        inventory[name.casefold()] = row
    require(len(inventory) == inspection["member_files"] == extraction["files_verified"], "INDEX_COVERAGE_MISMATCH")
    paths = {"inspection": inspection_path, "index": index_path}
    before = {"inspection": sha256(inspected_raw).hexdigest(), "index": sha256(index_raw).hexdigest()}
    documents = {}
    for name in INPUT_NAMES:
        member = CAMPAIGN + name
        require(member.casefold() in inventory, "DIAGNOSTIC_INPUT_NOT_INDEXED:" + name)
        row = inventory[member.casefold()]
        require(row["path"] == member, "INDEX_MEMBER_CASE_MISMATCH")
        path = extracted.joinpath(*member.split("/"))
        raw = file_bytes(path)
        checksum = sha256(raw).hexdigest()
        require(checksum == row["sha256"] and len(raw) == row["bytes"], "BOUND_DIAGNOSTIC_INPUT_CHANGED:" + name)
        paths[name] = path;before[name] = checksum
        documents[name] = [parse_json(line) for line in raw.splitlines()] if name.endswith(".jsonl") else parse_json(raw)
    for name, expected in SOURCE_PINS.items():
        path = ROOT / name
        checksum = sha256(file_bytes(path)).hexdigest()
        require(checksum == expected, "FROZEN_DIAGNOSTIC_SOURCE_CHANGED:" + name)
        paths[name] = path;before[name] = checksum
    tokenizer = documents["tokenizer.json"]
    tasks = {split: documents["dataset/" + filename] for split, filename in
             (("train", "train.json"), ("validation", "validation.json"), ("test", "test_private.json"))}
    train_public = [task["public"] for task in tasks["train"]]
    require(tokenizer.get("schema") == "cas-meta2-public-tokenizer/1" and tokenizer.get("fit_split") == "train_only"
            and tokenizer["fitted_examples"] == len(train_public) and tokenizer["fitted_public_sha256"] == digest(train_public), "TOKENIZER_FIT_BINDING_INVALID")
    words = {row[0] for public in train_public for row in encoded_data(public, SPECIAL)[0]}
    vocabulary = list(SPECIAL) + sorted(words.difference(SPECIAL))
    require(tokenizer["vocabulary"] == vocabulary, "TOKENIZER_TRAIN_VOCABULARY_MISMATCH")
    test_public = documents["dataset/test_public.json"]
    require(test_public == [task["public"] for task in tasks["test"]], "PUBLIC_PRIVATE_TASK_MAPPING_INVALID")
    predictions = documents["predictions.jsonl"]
    require(len(predictions) == len(test_public), "PREDICTION_COUNT_MISMATCH")
    for number, (row, public) in enumerate(zip(predictions, test_public)):
        require(set(row) == {"actions", "case_index", "public_sha256"} and row["case_index"] == number
                and row["public_sha256"] == digest(public) and set(row["actions"]) == set(ARMS), "PREDICTION_PUBLIC_BINDING_INVALID")
    training_targets = Counter(word for task in tasks["train"] for word in action_tokens(task["target"]))
    distributions = {split: distribution(values, vocabulary, training_targets) for split, values in tasks.items()}
    for split, values in tasks.items():
        distributions[split]["targets_longer_than_max_training_target"] = sum(
            len(action_tokens(task["target"])) > distributions["train"]["target_length_max"] for task in values)
        require(distributions[split]["input_length_max"] <= tokenizer["max_length"], "PUBLIC_INPUT_EXCEEDS_TOKENIZER_BOUND")
    predictions_report = prediction_summary(predictions, tasks["test"])
    after = {name: sha256(file_bytes(path)).hexdigest() for name, path in paths.items()}
    require(before == after, "DIAGNOSTIC_INPUT_CHANGED_DURING_READ")
    require(not any(name in sys.modules for name in ("torch", "numpy", "casformer", "cas_cjt")), "FORBIDDEN_MODEL_OR_TENSOR_IMPORT")
    return {"schema": "cas-meta2-saved-data-diagnosis/1", "status": "CAS_META_2_SAVED_DATA_DIAGNOSIS_COMPLETE",
            "source_sha": SOURCE_SHA, "source_binding": "LITERAL_SHA256_PINS_FOR_FROZEN_SOURCE", "git_object_check_run": False,
            "packet_sha256": inspection["packet_sha256"], "inspection_path": str(inspection_path), "extracted_path": str(extracted),
            "input_paths": {name: str(path) for name, path in paths.items()}, "input_sha256_before": before,
            "input_sha256_after": after, "inspected_inputs_unchanged": True, "hash_scope": "Six saved JSON inputs, inspection, index and two source files; not the whole packet",
            "vocabulary_size": len(vocabulary), "tokenizer_fit_and_vocabulary_reconstructed": True,
            "splits": distributions, "predictions": predictions_report,
            "rule_prior_knowledge": "Frozen parser explicitly recognizes all three wording families; neural vocabulary is fitted only on family 0",
            "neural_execution_performed": False, "checkpoint_loading_performed": False, "native_execution_performed": False,
            "heldout_tuning_performed": False, "sufficient_failure_cause_proven": False, "boundary": BOUNDARY}


def short_report(receipt):
    lines = ["# Saved-run data diagnosis", "", "The tokenizer loses test information. This alone is not a proven sufficient cause of failure.", "",
             "| Split | Examples | Unknown / encoded token rows | Share |", "|---|---:|---:|---:|"]
    for split, row in receipt["splits"].items():
        lines.append(f"| {split} | {row['examples']} | {row['unknown_token_count']} / {row['encoded_token_rows']} | {row['unknown_share_encoded_rows']:.2%} |")
    test = receipt["splits"]["test"]
    lines += ["", f"Unknown structural names affect {test['cases_with_unknown_structural_names']} test cases; {test['cases_with_multiple_unknown_structural_names']} contain at least two names mapped to the same unknown marker.",
              f"Test requires {test['nonmain_call_instructions']} calls inside child procedures, across {test['cases_with_nonmain_calls']} cases. Training has {receipt['splits']['train']['nonmain_call_instructions']}.",
              f"Test requires {sum(test['unseen_target_token_frequency'].values())} output-token occurrences never present as positive training targets.", ""]
    for arm in ("cas_trained", "generic_trained"):
        row = receipt["predictions"][arm]
        lines.append(f"- {arm}: {row['saved_decoded_actions']} decoded programs; {row['program_exactly_equal_to_target']} exact target programs; depths {row['predicted_depths']}; {row['nonmain_calls']} child calls.")
    lines += ["", receipt["rule_prior_knowledge"] + ".", "", "Equal complete pre-tensor feature-data groups: " +
              json.dumps({split: row["equal_complete_pre_tensor_feature_data_groups"] for split, row in receipt["splits"].items()}, sort_keys=True) + ". This does not prove distinct neural tensors.",
              "", f"Frozen source: `{receipt['source_sha']}`. Inspected diagnostic inputs were unchanged before/after.", "", BOUNDARY, ""]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inspection", required=True, type=Path)
    parser.add_argument("--extracted", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    receipt = diagnose(args.inspection, args.extracted)
    output = args.output.absolute()
    no_links(output)
    require(output.resolve().is_relative_to((ROOT / "records").resolve()) and output.resolve() != (ROOT / "records").resolve(), "NEW_RECORDS_OUTPUT_REQUIRED")
    require(not output.exists(), "OUTPUT_ALREADY_EXISTS")
    require(not output.resolve().is_relative_to(Path(receipt["extracted_path"]).resolve()), "EXTRACTION_WRITES_FORBIDDEN")
    receipt.update({"utc": datetime.now(timezone.utc).isoformat(), "python": sys.version, "platform": platform.platform(),
                    "command": [sys.executable, *sys.argv], "diagnostic_code_path": str(Path(__file__).resolve()),
                    "diagnostic_code_sha256": sha256(Path(__file__).read_bytes()).hexdigest()})
    report = short_report(receipt).encode("utf-8")
    receipt["report_sha256"] = sha256(report).hexdigest()
    receipt["receipt_sha256"] = digest(receipt)
    output.mkdir(parents=True, exist_ok=False)
    (output / "diagnosis_receipt.json").write_bytes(json.dumps(receipt, sort_keys=True, indent=2, allow_nan=False).encode("utf-8") + b"\n")
    (output / "REPORT.md").write_bytes(report)
    print(json.dumps({"status": receipt["status"], "receipt": str(output / "diagnosis_receipt.json"),
                      "receipt_sha256": receipt["receipt_sha256"]}, sort_keys=True))


if __name__ == "__main__":
    main()
