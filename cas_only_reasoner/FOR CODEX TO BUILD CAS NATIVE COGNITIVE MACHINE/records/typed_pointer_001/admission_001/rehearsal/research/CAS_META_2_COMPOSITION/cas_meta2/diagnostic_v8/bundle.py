"""Pure, development-only custody for the saved V7 prefix diagnostic.

Copy checkpoint bytes, never deserialize them. No model, runtime, provider,
private final task, or final prediction file is opened. The upstream manifest
contains historical final-file digests, not their contents. They remain opaque.
"""
from collections import Counter
from hashlib import sha256
import argparse
import json
import os
from pathlib import Path, PurePosixPath
import re

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "cas-meta2-development-diagnostic-bundle/8"
JOB = "cas-meta2-20260906094002-39762c47"
SOURCE_SHA = "42f9164754312f12850d9b8789c062fa7fb8069f"
SOURCE_ARCHIVE_SHA = "f9bed05bd582e0796e2c4e78ff0f5174e5e1b6a3f447e5c3eab56ad002d473f9"
PACKET_SHA = "f28603b7aab07d7d75a06cfa52fb5b802689b8896001fa9f572971c9140c9799"
EXTRACTION_SHA = "9bf40771df6dd7f67189d402d6bcfd8e05bd8cd997b71a6825fff21da105ae98"
MAX_BYTES = 32 * 1024 * 1024
MEMBER_BASE = "cloud_job/campaign/"
# Bundle destination -> exact upstream member, byte length, externally pinned SHA.
INPUTS = {
    "metadata/registration.json": ("training/registration.json", 17848, "37b77f856dc3ec5cffce0a3598cae8342dd543c22d031dd66f5622f83e614108"),
    "metadata/training_receipt.json": ("training/training_receipt.json", 90257, "594b585036af61a30e0bb8248faae9053a15809c048313b5f5336f5a55db7099"),
    "metadata/source_manifest.json": ("trainer_input/manifest.json", 5306, "1de691b0b2a4ea70b91288e9c78f49f058fdfaaa973de86c2051e79fb89c5c8c"),
    "validation.json": ("trainer_input/validation.json", 243342, "b1935fd487ec8f0039e0472649040b2b66fe64dfd7a88a0921c580ad6637791d"),
    "tokenizer.json": ("trainer_input/tokenizer.json", 4948, "f041a1ba24e9db97c83c022e304d47996e77ca457f1389722189e95b8c79a4c5"),
    "saved_development/cas_initial.json": ("training/cas_development_epoch_0000.json", 37100, "f36b1aa23378170563d4c8328a36c4a911e416d0afe112eed7d65c7f7d4decb3"),
    "saved_development/cas_selected.json": ("training/cas_development_epoch_0200.json", 101859, "202ac11d89ddc0ddfba299a40c20ca3609a5bec2859b65880cdee2674bf3d08a"),
    "saved_development/generic_initial.json": ("training/generic_development_epoch_0000.json", 36628, "dbf2967ee1a22baf0ab600ad1680651ec3c61075df4b8ed6893c94b27d5ae14d"),
    "saved_development/generic_selected.json": ("training/generic_development_epoch_0180.json", 95576, "42717174558bd646b8fc287f3c13b3eb3925de6a9d0cffe57de37ded7bb956c4"),
    "checkpoints/cas_initial.pt": ("training/cas_initial_epoch_0000.pt", 1117577, "ad8c80bf3d3ed7111e118957066ac3f0ec0509681fa2aa00e44d1592403b43fd"),
    "checkpoints/cas_selected.pt": ("training/cas_selected_epoch_0200.pt", 2666977, "bf709539d8a462fe73909553659ad046305e75428a15d80e83124bc28ee84b46"),
    "checkpoints/generic_initial.pt": ("training/generic_initial_epoch_0000.pt", 1104425, "20669d0470a583ab172bbb06451c0b6bcbbf190ea10b3e725e7a73c5c046b051"),
    "checkpoints/generic_selected.pt": ("training/generic_selected_epoch_0180.pt", 2626593, "53e2acdd4635d843210a7aa0a5b194e395f57c0b7f71ca59b1a64dbeae4ca532"),
}
TRAIN = ("trainer_input/train.json", 2477712, "111dfe5f332983a95ca1fa8ce3bc4df44e445586d7de145abd12598023761605")
PROBE_CANONICAL_SHA = "a8ed95bde1dec38679fe46d0d20d3598cfd3c89215b6ef4535bc6949e7213245"
VALIDATION_CANONICAL_SHA = "3a8211160692192858a747a66857f80fb5876d4575d0819a01449486f1f463fa"
ARMS = ("cas_initial", "cas_selected", "generic_initial", "generic_selected")
SOURCE_FILES = (
    "cas_meta2/__init__.py", "cas_meta2/codec.py", "cas_meta2/ir.py",
    "cas_meta2/features_v2.py", "cas_meta2/features_v3.py", "cas_meta2/grammar_v3.py",
    "cas_meta2/selection_v2.py", "cas_meta2/selection_v3.py", "cas_meta2/policy.py",
    "cas_meta2/policy_v3.py", "cas_meta2/train_v3.py", "cas_meta2/loss_v3.py",
    "cas_meta2/contrast_v7/train.py", "requirements-gpu.txt",
)
ROLE_NAMES = ("observation_binding", "call_target", "call_input", "run_input",
              "parent_return", "child_return")
FILES = frozenset((*INPUTS, "train_probe.json", "metadata/extraction_receipt.json"))
BOUNDARY = {
    "development_only": True, "private_final_files_included": False,
    "final_public_files_included": False, "checkpoint_deserialization": False,
    "neural_execution": False, "native_execution": False, "provider_execution": False,
    "new_tasks_generated": False, "learning_result": False,
    "assisted_prefixes_are_task_success": False,
    "historical_test_digests_are_opaque_metadata": True,
}
EXPECTED_DEPTH_COUNTS = {
    "train_probe": {
        "1": (8, 352, (8, 0, 0, 64, 8, 0)),
        "2": (8, 824, (8, 32, 32, 90, 8, 24)),
        "3": (8, 808, (8, 32, 32, 86, 8, 24)),
    },
    "validation": {
        "1": (32, 1448, (32, 0, 0, 266, 32, 0)),
        "2": (32, 3144, (32, 128, 128, 322, 32, 96)),
        "3": (32, 3152, (32, 128, 128, 324, 32, 96)),
    },
}


class BundleError(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise BundleError(reason)


def canonical(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, OverflowError) as error:
        raise BundleError("NONCANONICAL_JSON") from error


def decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "DUPLICATE_JSON_KEY")
            result[key] = value
        return result
    def constant(value):
        raise BundleError("NONFINITE_JSON:" + value)
    try:
        value = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
        canonical(value)  # Reject overflow such as 1e999 as well as NaN literals.
        return value
    except (UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise BundleError("INVALID_JSON") from error


def digest(raw):
    return sha256(raw).hexdigest()


def no_links(path):
    path = Path(path).absolute()
    require(not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
                    for p in (path, *path.parents)), "LINK_REFUSED")
    return path


def read(path):
    path = no_links(path)
    require(path.is_file() and path.stat().st_size <= MAX_BYTES, "FILE_BOUND")
    with path.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    require(len(raw) <= MAX_BYTES, "FILE_BOUND")
    return raw


def relative_path(name):
    require(type(name) is str and name and "\\" not in name and ":" not in name,
            "RELATIVE_PATH_REQUIRED")
    path = PurePosixPath(name)
    require(not path.is_absolute() and path.as_posix() == name
            and all(part not in (".", "..") for part in path.parts), "RELATIVE_PATH_REQUIRED")
    return name


def checked_child(directory, name):
    relative_path(name)
    root = no_links(directory)
    path = no_links(root / name)
    require(path.resolve().is_relative_to(root.resolve()), "PATH_ESCAPE")
    return path


def checked_sources(registration):
    pins = registration["source_sha256"]
    result = {}
    for name in SOURCE_FILES:
        expected = pins[name]
        require(digest(read(ROOT / name)) == expected, "SOURCE_CHANGED:" + name)
        result[name] = expected
    return result


def _apis():
    # Imported only after callers check their source bytes, except the standalone
    # pure counting helper. No policy/model module is imported through this path.
    from ..codec import action_to_tokens, validate_public
    from ..features_v2 import LosslessPublicTokenizer
    from ..features_v3 import encode_public_with_spans
    from ..grammar_v3 import GrammarState
    from ..ir import validate_program
    from ..selection_v3 import target_token_roles
    return action_to_tokens, validate_public, LosslessPublicTokenizer, encode_public_with_spans, GrammarState, validate_program, target_token_roles


def decision_counts(tasks):
    """Count static reference decisions, not expanded runtime calls or scores."""
    action_to_tokens, validate_public, _, _, GrammarState, validate_program, roles_for = _apis()
    require(type(tasks) is list and tasks, "TASK_LIST_REQUIRED")
    groups = {}
    ids = set()
    for task in tasks:
        require(type(task) is dict and {"task_id", "public", "target"} <= set(task), "TASK_FIELDS")
        ident = task["task_id"]
        require(type(ident) is str and ident not in ids, "TASK_ID_DUPLICATE_OR_INVALID")
        ids.add(ident)
        validate_public(task["public"])
        target = task["target"]
        depth = str(validate_program(target["program"])["max_call_depth"])
        require(depth in ("1", "2", "3"), "DEVELOPMENT_DEPTH_INVALID")
        row = groups.setdefault(depth, {"tasks": 0, "next_tokens": 0,
            "roles": dict.fromkeys(ROLE_NAMES, 0), "all_token_roles": {},
            "nonsingleton_roles": dict.fromkeys(ROLE_NAMES, 0),
            "complete_grammar_paths": 0})
        tokens = action_to_tokens(target, max_length=256)
        labels = roles_for(target, max_length=256)
        require(len(tokens) == len(labels), "TOKEN_ROLE_ALIGNMENT")
        state = GrammarState(max_length=256)
        for index, (token, role) in enumerate(zip(tokens, labels)):
            allowed = state.allowed_tokens()
            require(token in allowed, "REFERENCE_TOKEN_NOT_ALLOWED")
            meaningful = None
            if role in ("observation_binding", "call_target"):
                meaningful = role
            elif role == "step_input":
                meaningful = "call_input" if state._machine.step["kind"] == "CALL" else "run_input"
            elif role == "return_value":
                meaningful = "parent_return" if state._machine.current == "main" else "child_return"
            if meaningful:
                row["roles"][meaningful] += 1
                row["nonsingleton_roles"][meaningful] += int(len(allowed) >= 2)
            if index:
                row["all_token_roles"][role] = row["all_token_roles"].get(role, 0) + 1
            state = state.advance(token)
        require(state.complete and state.to_action() == target, "REFERENCE_NOT_COMPLETE")
        row["tasks"] += 1
        row["next_tokens"] += len(tokens) - 1
        row["complete_grammar_paths"] += 1
    overall = {"tasks": len(tasks), "next_tokens": sum(row["next_tokens"] for row in groups.values()),
        "roles": {name: sum(row["roles"][name] for row in groups.values()) for name in ROLE_NAMES}}
    overall["selected_role_opportunities"] = sum(overall["roles"].values())
    return {"overall": overall, "by_depth": groups}


def _checked_counts(split, tasks):
    result = decision_counts(tasks)
    require(set(result["by_depth"]) == set(EXPECTED_DEPTH_COUNTS[split]), "DEPTH_COVERAGE")
    for depth, (count, tokens, roles) in EXPECTED_DEPTH_COUNTS[split].items():
        row = result["by_depth"][depth]
        require(row["tasks"] == count and row["next_tokens"] == tokens
                and row["roles"] == dict(zip(ROLE_NAMES, roles)), "COHORT_DENOMINATOR_CHANGED")
    return result


def _extract_identity(raw):
    require(digest(raw) == EXTRACTION_SHA, "EXTRACTION_RECEIPT_CHANGED")
    receipt = decode(raw)
    require(receipt["status"] == "FAILED_RUN_ALL_PACKET_BYTES_VERIFIED"
            and receipt["job"] == JOB and receipt["source_sha"] == SOURCE_SHA, "EXTRACTION_IDENTITY")
    return receipt


def _check_payloads(payloads):
    require(set(payloads) == FILES, "BUNDLE_FILE_SET")
    extraction = _extract_identity(payloads["metadata/extraction_receipt.json"])
    for destination, (member, size, expected) in INPUTS.items():
        raw = payloads[destination]
        require(len(raw) == size and digest(raw) == expected, "UPSTREAM_BYTES_CHANGED:" + destination)
        recorded = extraction["inventory"][MEMBER_BASE + member]
        require(recorded["bytes"] == size and recorded["sha256"] == expected, "INVENTORY_IDENTITY:" + destination)
    registration = decode(payloads["metadata/registration.json"])
    receipt = decode(payloads["metadata/training_receipt.json"])
    historical_manifest = decode(payloads["metadata/source_manifest.json"])
    require(registration["schema"] == receipt["schema"] == "cas-meta2-contrast-training/7"
            and registration["job"] == receipt["job"] == JOB and receipt["completed"] is True
            and registration["private_labels_read"] is False and registration["rule_parser_used"] is False
            and registration["probe_used_for_selection"] is False, "TRAINING_IDENTITY")
    source_pins = checked_sources(registration)
    require(receipt["source_sha256"] == registration["source_sha256"]
            and receipt["manifest_sha256"] == registration["data"]["manifest_sha256"]
            == INPUTS["metadata/source_manifest.json"][2], "TRAINING_SOURCE_OR_MANIFEST")
    tokenizer_raw = decode(payloads["tokenizer.json"])
    train_probe = decode(payloads["train_probe.json"])
    validation = decode(payloads["validation.json"])
    require(digest(canonical(train_probe)) == PROBE_CANONICAL_SHA
            and digest(canonical(validation)) == VALIDATION_CANONICAL_SHA, "COHORT_CONTENT_OR_ORDER_CHANGED")
    require([t["task_id"] for t in train_probe] == registration["probe_ids"], "PROBE_SELECTION_CHANGED")
    for name in ("validation.json", "tokenizer.json"):
        require(digest(payloads[name]) == registration["data"]["loaded_sha256"][name]
                == historical_manifest["sha256"][name], "DATASET_INPUT_IDENTITY:" + name)
    _, _, Tokenizer, encode_spans, _, _, _ = _apis()
    tokenizer = Tokenizer.from_dict(tokenizer_raw)
    require(tokenizer.fitted_examples == 896 and tokenizer.max_length == 1024
            and tokenizer.digest == registration["data"]["tokenizer_sha256"]
            == "e85ff923080382dbb8e2296b4107b8cec99c29da5e9309cd247943c3ea832bc3",
            "TOKENIZER_IDENTITY")
    cohorts = {"train_probe": train_probe, "validation": validation}
    counts = {split: _checked_counts(split, tasks) for split, tasks in cohorts.items()}
    for tasks in cohorts.values():
        for task in tasks:
            featured = encode_spans(task["public"], tokenizer)
            require(featured["encoded"] == tokenizer.encode_public(task["public"])
                    and tokenizer.check_round_trip(task["public"]), "PUBLIC_ENCODING_MISMATCH")
    checkpoint_records, saved = {}, {}
    for arm in ARMS:
        family, kind = arm.split("_")
        record = receipt["checkpoints"][family][kind]
        destination = "checkpoints/" + arm + ".pt"
        member, size, expected = INPUTS[destination]
        expected_epoch = 0 if kind == "initial" else (200 if family == "cas" else 180)
        require(record["family"] == family and record["epoch"] == expected_epoch
                and record["optimizer_steps"] == expected_epoch * 56
                and record["path"] == PurePosixPath(member).name
                and record["bytes"] == size and record["sha256"] == expected, "CHECKPOINT_RECORD_CHANGED")
        checkpoint_records[arm] = record
        dev = decode(payloads["saved_development/" + arm + ".json"])
        require(set(dev) == {"validation", "validation_actions", "probe_actions", "probe_metrics", "test_labels_used"}
                and dev["test_labels_used"] is False
                and len(dev["validation_actions"]) == 96 and len(dev["probe_actions"]) == 24
                and dev["validation"] == record["validation"], "DEVELOPMENT_RECORD_CHANGED")
        saved[arm] = dev
    return {"cohorts": cohorts, "counts": counts, "tokenizer": tokenizer_raw,
            "registration": registration, "training_receipt": receipt,
            "source_files_sha256": source_pins, "checkpoint_records": checkpoint_records,
            "saved_development": saved}


def _manifest(payloads, checked):
    cohort_rows = {}
    for split, tasks in checked["cohorts"].items():
        cohort_rows[split] = {
            "count": len(tasks), "ordered_task_ids": [t["task_id"] for t in tasks],
            "task_list_canonical_sha256": digest(canonical(tasks)),
            "source_member": MEMBER_BASE + (TRAIN[0] if split == "train_probe" else INPUTS["validation.json"][0]),
            "source_member_sha256": TRAIN[2] if split == "train_probe" else INPUTS["validation.json"][2],
            "selection_rule": ("Exact registration.probe_ids; first eight sorted task IDs at each training depth."
                               if split == "train_probe" else "Every validation task in original saved order."),
            "decision_counts": checked["counts"][split]}
    return {"schema": SCHEMA, "source_job": JOB, "source_sha": SOURCE_SHA,
        "source_archive_sha256": SOURCE_ARCHIVE_SHA, "packet_sha256": PACKET_SHA,
        "extraction_receipt_sha256": EXTRACTION_SHA,
        "source_registration_sha256": INPUTS["metadata/registration.json"][2],
        "source_training_receipt_sha256": INPUTS["metadata/training_receipt.json"][2],
        "historical_manifest_sha256": INPUTS["metadata/source_manifest.json"][2],
        "source_files_sha256": checked["source_files_sha256"],
        "builder_sha256": digest(read(Path(__file__))),
        "files": {name: {"bytes": len(raw), "sha256": digest(raw)} for name, raw in sorted(payloads.items())},
        "cohorts": cohort_rows, "checkpoint_records": checked["checkpoint_records"],
        "limits": {"input_tokens": 1024, "action_tokens": 256, "prediction_batch_size": 16,
                   "cohort_tasks": 120, "checkpoint_arms": 4, "task_checkpoint_rows": 480,
                   "selected_role_opportunities_per_checkpoint": 2272,
                   "selected_role_checkpoint_rows": 9088, "next_tokens_per_checkpoint": 9728},
        "boundary": BOUNDARY,
        "limitations": ["Nested training probes are call-target contrasts, not a balanced training sample.",
            "Reference decision counts are static serialized sites, not expanded native calls.",
            "Four checkpoints repeat one cohort; they do not create four independent task samples.",
            "The contents of checkpoint tensors have not been loaded or independently inspected.",
            "This validates inputs and references, not a CUDA diagnostic or learned capability."]}


def _directory_files(bundle):
    bundle = no_links(bundle)
    require(bundle.is_dir(), "BUNDLE_DIRECTORY_REQUIRED")
    expected = set(FILES) | {"manifest.json"}
    expected_dirs = {str(parent) for name in expected for parent in PurePosixPath(name).parents if str(parent) != "."}
    found = set()
    for current, directories, files in os.walk(bundle, followlinks=False):
        for name in directories:
            child = no_links(Path(current) / name)
            require(child.relative_to(bundle).as_posix() in expected_dirs, "EXTRA_BUNDLE_DIRECTORY")
        for name in files:
            child = no_links(Path(current) / name)
            require(child.is_file(), "REGULAR_FILE_REQUIRED")
            found.add(child.relative_to(bundle).as_posix())
    require(found == expected, "BUNDLE_FILE_SET")
    return bundle


def validate_bundle(bundle, *, expected_manifest_sha256):
    """Check an independently pinned bundle and return only diagnostic inputs."""
    require(type(expected_manifest_sha256) is str and re.fullmatch("[0-9a-f]{64}", expected_manifest_sha256),
            "EXTERNAL_MANIFEST_PIN_REQUIRED")
    bundle = _directory_files(bundle)
    raw_manifest = read(checked_child(bundle, "manifest.json"))
    require(digest(raw_manifest) == expected_manifest_sha256, "MANIFEST_BYTES_CHANGED")
    manifest = decode(raw_manifest)
    require(type(manifest) is dict and type(manifest.get("files")) is dict, "MANIFEST_FIELDS")
    for name in manifest["files"]:
        relative_path(name)
    require(set(manifest["files"]) == FILES, "MANIFEST_FILE_SET")
    payloads = {name: read(checked_child(bundle, name)) for name in FILES}
    checked = _check_payloads(payloads)
    require(canonical(manifest) == canonical(_manifest(payloads, checked)), "MANIFEST_CONTENT_CHANGED")
    # Re-read all inputs after counting; the worker receives these validated
    # records plus paths, not a silently reopened unverified checkpoint.
    for name, raw in payloads.items():
        require(read(checked_child(bundle, name)) == raw, "BUNDLE_CHANGED_DURING_CHECK")
    require(read(bundle / "manifest.json") == raw_manifest, "MANIFEST_CHANGED_DURING_CHECK")
    return {"manifest": manifest, "manifest_sha256": expected_manifest_sha256,
        "cohorts": checked["cohorts"], "tokenizer": checked["tokenizer"],
        "registration": checked["registration"], "training_receipt": checked["training_receipt"],
        "checkpoints": {arm: {"path": str(checked_child(bundle, "checkpoints/" + arm + ".pt")),
                              "record": checked["checkpoint_records"][arm]} for arm in ARMS},
        "saved_development": checked["saved_development"]}


def prepare(extraction_root, output):
    """Prepare a new local bundle without overwriting or loading any checkpoint."""
    extraction_root, output = no_links(extraction_root), no_links(output)
    require(extraction_root.is_dir(), "EXTRACTION_DIRECTORY_REQUIRED")
    require(output.resolve().is_relative_to(ROOT.resolve()) and output.resolve() != ROOT.resolve(),
            "OUTPUT_MUST_BE_INSIDE_CANDIDATE")
    require(not output.exists(), "NEW_OUTPUT_REQUIRED")
    extraction_raw = read(extraction_root.parent / "extraction_receipt.json")
    extraction = _extract_identity(extraction_raw)
    payloads = {"metadata/extraction_receipt.json": extraction_raw}
    source_raw = {}
    def member_bytes(spec):
        member, size, expected = spec
        name = MEMBER_BASE + member
        raw = read(checked_child(extraction_root, name))
        require(len(raw) == size and digest(raw) == expected, "SOURCE_MEMBER_CHANGED:" + name)
        inventory = extraction["inventory"][name]
        require(inventory["bytes"] == size and inventory["sha256"] == expected, "SOURCE_INVENTORY_CHANGED")
        source_raw[name] = raw
        return raw
    for destination, spec in INPUTS.items():
        payloads[destination] = member_bytes(spec)
    registration = decode(payloads["metadata/registration.json"])
    checked_sources(registration)
    train = decode(member_bytes(TRAIN))
    require(type(train) is list and len(train) == 896, "TRAIN_COUNT")
    index = {task["task_id"]: task for task in train}
    require(len(index) == 896 and len(registration["probe_ids"]) == 24, "TRAIN_OR_PROBE_ID_COUNT")
    require(all(ident in index for ident in registration["probe_ids"]), "PROBE_ID_MISSING")
    selected = [index[ident] for ident in registration["probe_ids"]]
    _, _, _, _, _, validate_program, _ = _apis()
    reconstructed = [task for depth in (1, 2, 3) for task in sorted(
        [task for task in train if validate_program(task["target"]["program"])["max_call_depth"] == depth],
        key=lambda task: task["task_id"])[:8]]
    require(selected == reconstructed, "PROBE_RULE_MISMATCH")
    payloads["train_probe.json"] = canonical(selected) + b"\n"
    checked = _check_payloads(payloads)
    manifest = _manifest(payloads, checked)
    for name, raw in source_raw.items():
        require(read(checked_child(extraction_root, name)) == raw, "SOURCE_CHANGED_DURING_PREPARATION")
    require(read(extraction_root.parent / "extraction_receipt.json") == extraction_raw, "EXTRACTION_CHANGED")
    output.mkdir(parents=True, exist_ok=False)
    for name, raw in {**payloads, "manifest.json": canonical(manifest) + b"\n"}.items():
        path = checked_child(output, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    manifest_sha = digest(read(output / "manifest.json"))
    validate_bundle(output, expected_manifest_sha256=manifest_sha)
    return {"status": "DEVELOPMENT_ONLY_BUNDLE_PREPARED", "bundle": str(output),
        "manifest_sha256": manifest_sha, "files": len(FILES) + 1,
        "cohorts": {name: row["decision_counts"] for name, row in manifest["cohorts"].items()},
        "boundary": BOUNDARY}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--extraction-root", required=True)
    prep.add_argument("--output", required=True)
    check = sub.add_parser("validate")
    check.add_argument("--bundle", required=True)
    check.add_argument("--manifest-sha256", required=True)
    args = parser.parse_args(argv)
    if args.command == "prepare":
        result = prepare(args.extraction_root, args.output)
    else:
        checked = validate_bundle(args.bundle, expected_manifest_sha256=args.manifest_sha256)
        result = {"status": "DEVELOPMENT_ONLY_BUNDLE_VALIDATED", "manifest_sha256": checked["manifest_sha256"],
            "limits": checked["manifest"]["limits"], "boundary": checked["manifest"]["boundary"]}
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
