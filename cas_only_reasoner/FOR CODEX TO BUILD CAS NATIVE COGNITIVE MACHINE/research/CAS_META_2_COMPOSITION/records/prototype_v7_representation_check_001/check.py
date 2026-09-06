"""Read-only v7 representation check of already collected, pinned records.

No generation, neural imports, tensors, runtime execution, or provider access.
Existing private labels are used only for this post-run representation diagnosis.
"""
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import argparse
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SOURCE_SHA = "42f9164754312f12850d9b8789c062fa7fb8069f"
JOB = "cas-meta2-20260906094002-39762c47"
PACKET_SHA = "f28603b7aab07d7d75a06cfa52fb5b802689b8896001fa9f572971c9140c9799"
RECEIPTS = {
    "records/prototype_v7_partial_native_001/run_001/partial_native_receipt.json":
        "bc700054e18dad6de9e2516f441adccdfac0a9ace25a39fd0fce6a0879d37f4f",
    "records/prototype_v7_partial_review_001/extraction_receipt.json":
        "9bf40771df6dd7f67189d402d6bcfd8e05bd8cd997b71a6825fff21da105ae98",
    "records/prototype_v7_training_recount_001/receipt_001.json":
        "452705ca332f9cf8b42c8815c3c08f031ec73ba4fc443a51797679acddc62d76",
}
SOURCE_FILES = (
    "cas_meta2/__init__.py", "cas_meta2/codec.py", "cas_meta2/ir.py",
    "cas_meta2/features_v2.py", "cas_meta2/features_v3.py", "cas_meta2/grammar_v3.py",
    "cas_meta2/policy.py", "cas_meta2/policy_v3.py", "cas_meta2/train_v3.py",
    "cas_meta2/loss_v3.py", "cas_meta2/selection_v2.py", "cas_meta2/selection_v3.py",
    "cas_meta2/contrast_v7/train.py", "cas_meta2/contrast_v7/data.py",
    "records/prototype_training_integration_v7_001/public_data.py",
)
FORBIDDEN = frozenset(("torch", "numpy", "tensorflow", "jax", "onnx", "onnxruntime",
    "transformers", "casformer", "cas_cjt", "cas_meta", "boto3", "botocore"))


def require(value, reason):
    if not value:
        raise ValueError(reason)


def read(path):
    path = Path(path).absolute()
    require(not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
                    for p in (path, *path.parents)), "LINK_REFUSED")
    require(path.is_file() and path.stat().st_size <= 32 * 1024**2, "FILE_BOUND")
    return path.read_bytes()


def digest(raw):
    return sha256(raw).hexdigest()


def pinned(path, expected):
    raw = read(path)
    require(digest(raw) == expected, "PIN_MISMATCH:" + str(path))
    return json.loads(raw)


class PureImports:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in FORBIDDEN:
            raise RuntimeError("FORBIDDEN_IMPORT:" + fullname)


def no_external_execution(event, args):
    if event.startswith(("socket.", "subprocess.", "os.system", "os.spawn", "os.exec")):
        raise RuntimeError("EXTERNAL_EXECUTION_REFUSED:" + event)


def run(output):
    started, tick = datetime.now(timezone.utc).isoformat(), time.monotonic()
    output = Path(output).absolute()
    require(output.parent.resolve() == HERE.resolve() and not output.exists(), "NEW_LOCAL_RUN_DIRECTORY_REQUIRED")
    require(not any(name.split(".")[0] in FORBIDDEN for name in sys.modules), "FORBIDDEN_PRELOADED_MODULE")
    sys.meta_path.insert(0, PureImports())
    sys.addaudithook(no_external_execution)
    evidence = {name: pinned(ROOT / name, expected) for name, expected in RECEIPTS.items()}
    audit, extraction, training = (evidence[name] for name in RECEIPTS)
    require(audit["status"] == "PARTIAL_NATIVE_EVIDENCE_CHECKED"
            and training["status"] == "V7_SAVED_TRAINING_RECOUNT_PASSED"
            and extraction["status"] == "FAILED_RUN_ALL_PACKET_BYTES_VERIFIED", "PRIOR_EVIDENCE_STATUS")
    require(all(item["source_sha"] == SOURCE_SHA and item["job"] == JOB
                for item in (audit, extraction, training)), "RUN_IDENTITY")
    require(audit["packet_sha256"] == training["packet_sha256"] == PACKET_SHA,
            "PACKET_IDENTITY")
    source_pins = {name: audit["source_manifest"]["files_sha256"]["research/CAS_META_2_COMPOSITION/" + name]
                   for name in SOURCE_FILES}
    for name, expected in source_pins.items():
        require(digest(read(ROOT / name)) == expected, "SOURCE_CHANGED:" + name)
    # Only these six checked package modules are imported. Model/trainer files
    # above are byte-checked, never imported.
    sys.path.insert(0, str(ROOT))
    from cas_meta2.codec import (action_to_tokens, tokens_to_action, CJT_NAMES,
                                PROCEDURE_NAMES, VARIABLE_NAMES)
    from cas_meta2.features_v2 import LosslessPublicTokenizer
    from cas_meta2.features_v3 import encode_public_with_spans
    from cas_meta2.grammar_v3 import GrammarState
    from cas_meta2.ir import validate_program
    for name, module in tuple(sys.modules.items()):
        if name == "cas_meta2" or name.startswith("cas_meta2."):
            require(getattr(module, "__file__", None) is not None, "HELPER_PATH_MISSING")
            path = Path(module.__file__).resolve()
            require(path.is_relative_to(ROOT.resolve())
                    and path.relative_to(ROOT.resolve()).as_posix() in SOURCE_FILES,
                    "UNEXPECTED_HELPER_IMPORT:" + name)
    base = ROOT / "records/prototype_v7_partial_review_001/extracted_001"
    inputs = {}
    def load(name):
        member = "cloud_job/campaign/" + name
        record = extraction["inventory"][member]
        path = base / member
        raw = read(path)
        require(len(raw) == record["bytes"] and digest(raw) == record["sha256"], "SAVED_INPUT_CHANGED:" + name)
        inputs[member] = {"path": str(path), "bytes": len(raw), "sha256": record["sha256"]}
        return json.loads(raw)
    tokenizer = LosslessPublicTokenizer.from_dict(load("trainer_input/tokenizer.json"))
    require(tokenizer.max_length == 1024 and tokenizer.fitted_examples == 896, "TOKENIZER_SHAPE")
    symbols = set(PROCEDURE_NAMES + VARIABLE_NAMES + CJT_NAMES)
    results, all_targets, train_tokens, checked_tokens = {}, {}, set(), 0
    for split, filename, expected_count in (("train", "train.json", 896),
            ("validation", "validation.json", 96), ("test", "test_private.json", 72)):
        tasks = load("dataset/" + filename)
        require(len(tasks) == expected_count, "SPLIT_COUNT:" + split)
        require(inputs["cloud_job/campaign/dataset/" + filename]["sha256"]
                == training["dataset"]["sha256"][filename], "TRAINING_DATASET_PIN:" + split)
        lengths, failures, missing_symbols, depths, scopes, targets = [], [], [], Counter(), Counter(), []
        for task in tasks:
            target, public = task["target"], task["public"]
            tokens = action_to_tokens(target, max_length=256)
            require(tokens_to_action(tokens, max_length=256) == target, "CODEC_ROUND_TRIP")
            state = GrammarState(max_length=256)
            for index, token in enumerate(tokens):
                try:
                    state = state.advance(token)
                except Exception as error:
                    failures.append({"task_id": task["task_id"], "token_index": index,
                                     "token": token, "role": state.role, "error": str(error)})
                    break
            require(state.complete and state.to_action() == target, "TARGET_GRAMMAR_NOT_REACHABLE:" + task["task_id"])
            featured = encode_public_with_spans(public, tokenizer)
            require(tokenizer.check_round_trip(public), "TEXT_ROUND_TRIP")
            require(featured["encoded"] == tokenizer.encode_public(public), "SPAN_ENCODING_CHANGED")
            absent = (set(tokens) & symbols) - {item["symbol"] for item in featured["occurrences"]}
            if absent:
                missing_symbols.append({"task_id": task["task_id"], "symbols": sorted(absent)})
            lengths.append((len(featured["encoded"]["ids"]), len(tokens)))
            checked_tokens += len(tokens)
            depths[str(validate_program(target["program"])["max_call_depth"])] += 1
            for procedure in target["program"]["procedures"].values():
                scopes[",".join(procedure["allowed_cjts"])] += 1
            targets.append(set(tokens))
            if split == "train":
                train_tokens.update(tokens)
        all_targets[split] = targets
        results[split] = {"tasks": len(tasks), "depths": dict(depths),
            "input_tokens_min": min(v[0] for v in lengths), "input_tokens_max": max(v[0] for v in lengths),
            "target_tokens_min": min(v[1] for v in lengths), "target_tokens_max": max(v[1] for v in lengths),
            "codec_round_trips": len(tasks), "complete_target_grammar_paths": len(tasks),
            "lossless_public_text_round_trips": len(tasks), "exact_copy_span_encodings": len(tasks),
            "grammar_failures": failures, "missing_required_copy_symbols": missing_symbols,
            "target_scope_orders": dict(scopes)}
    for split in ("validation", "test"):
        results[split]["unseen_positive_target_tokens"] = sorted(set().union(*all_targets[split]) - train_tokens)
        require(not results[split]["unseen_positive_target_tokens"], "UNSEEN_TARGET_TOKEN")
    require(all(not row["grammar_failures"] and not row["missing_required_copy_symbols"]
                for row in results.values()), "REPRESENTATION_CHECK_FAILED")
    for name, expected in source_pins.items():
        require(digest(read(ROOT / name)) == expected, "SOURCE_CHANGED_AT_END:" + name)
    for name, expected in RECEIPTS.items():
        require(digest(read(ROOT / name)) == expected, "RECEIPT_CHANGED_AT_END:" + name)
    for name, record in inputs.items():
        require(digest(read(record["path"])) == record["sha256"], "INPUT_CHANGED_AT_END:" + name)
    require(not any(name.split(".")[0] in FORBIDDEN for name in sys.modules), "FORBIDDEN_IMPORT_AT_END")
    result = {"schema": "cas-meta2-v7-saved-representation-check/1", "status": "SAVED_TARGET_REPRESENTATION_CHECK_PASSED",
        "completed": True, "job": JOB, "source_sha": SOURCE_SHA, "packet_sha256": PACKET_SHA,
        "receipt_pins": RECEIPTS, "source_files_sha256": source_pins, "input_files": inputs,
        "results": results, "total_targets": 1064, "target_token_transitions_checked": checked_tokens,
        "input_token_limit": 1024, "action_token_limit": 256,
        "source_and_inputs_unchanged": True, "neural_imports": False, "tensor_or_checkpoint_loads": False,
        "native_or_provider_execution": False, "new_task_generation": False, "learning_result": False,
        "post_run_private_targets_read": True, "numeric_float32_fidelity_measured": False,
        "text_numeric_boundary": "Exact public text and symbol spans are checked. Eight-float rows are not a proof of downstream float32 fidelity; no tensors were created.",
        "limits": ["Reachability of the correct target does not show that a learned model will select it.",
                   "No numerical logits, gradients, weights, native outputs or root cause were checked.",
                   "The completed prior byte audit supplies packet provenance; this is not another full packet or semantic audit.",
                   "Historical results and the recorded 0/72 CAS native result are unchanged."],
        "command": [sys.executable, *sys.argv], "checker_sha256": digest(read(Path(__file__))),
        "python": sys.version, "started_utc": started, "finished_utc": datetime.now(timezone.utc).isoformat(),
        "wall_seconds": time.monotonic() - tick}
    output.mkdir()
    (output / "receipt.json").write_bytes((json.dumps(result, indent=2, sort_keys=True) + "\n").encode())
    print(json.dumps({"status": result["status"], "total_targets": result["total_targets"],
                     "target_token_transitions_checked": checked_tokens, "results": results,
                     "receipt": str(output / "receipt.json"),
                     "receipt_sha256": digest(read(output / "receipt.json"))}, sort_keys=True))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    run(args.output)
