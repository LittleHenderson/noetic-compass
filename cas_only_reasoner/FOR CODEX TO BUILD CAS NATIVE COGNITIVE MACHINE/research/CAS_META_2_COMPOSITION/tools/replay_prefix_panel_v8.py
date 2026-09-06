"""Pure integration check of the matcher using saved development actions only."""
import argparse
from collections import Counter
from hashlib import sha256
import importlib.abc
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = {"torch", "casformer", "cas_cjt", "cas_meta", "tensorflow", "jax", "cupy", "boto3", "botocore"}
SOURCES = ("tools/replay_prefix_panel_v8.py", "cas_meta2/diagnostic_v8/__init__.py",
           "cas_meta2/diagnostic_v8/bundle.py", "cas_meta2/diagnostic_v8/sites.py",
           "cas_meta2/__init__.py", "cas_meta2/codec.py", "cas_meta2/ir.py",
           "cas_meta2/features_v2.py", "cas_meta2/features_v3.py", "cas_meta2/grammar_v3.py",
           "cas_meta2/selection_v2.py", "cas_meta2/selection_v3.py")


def source_identity():
    result = {}
    for name in SOURCES:
        path = ROOT / name
        if not path.is_file() or any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
                                    for p in (path, *path.parents)):
            raise ValueError("V8_OFFLINE_REPLAY_SOURCE_MISSING_OR_LINK")
        result[name] = sha256(path.read_bytes()).hexdigest()
    return result


class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in FORBIDDEN:
            raise RuntimeError("V8_OFFLINE_REPLAY_NEURAL_PROVIDER_IMPORT_REFUSED")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if any(name in sys.modules for name in FORBIDDEN):
        raise ValueError("V8_OFFLINE_REPLAY_ALREADY_IMPORTED_NEURAL_PROVIDER")
    before = source_identity()
    sys.meta_path.insert(0, Guard())
    sys.path.insert(0, str(ROOT))
    from cas_meta2.diagnostic_v8.bundle import validate_bundle, ARMS, no_links, canonical, require
    from cas_meta2.diagnostic_v8.sites import compare_sites, extract_sites, ROLES
    from cas_meta2.codec import action_to_ids
    from cas_meta2.ir import validate_program
    output = no_links(args.output)
    require(not output.exists() and output.resolve().is_relative_to(
            (ROOT/"records/child_call_v8_diagnostic_001").resolve()), "V8_NEW_OFFLINE_REPLAY_OUTPUT_REQUIRED")
    loaded = validate_bundle(args.bundle, expected_manifest_sha256=args.manifest_sha256)
    rows, totals = [], {}
    for arm in ARMS:
        for split, tasks in loaded["cohorts"].items():
            saved = loaded["saved_development"][arm]
            actions = saved["probe_actions" if split == "train_probe" else "validation_actions"]
            for task, action in zip(tasks, actions, strict=True):
                reference = action_to_ids(task["target"], max_length=256)
                sites = extract_sites(reference)["sites"]
                ref_counts = Counter(s["role"] for s in sites)
                identity = compare_sites(reference, reference)
                require(identity["totals"]["correct"] == identity["totals"]["scored"] == len(sites)
                        and identity["totals"]["matched"] == len(sites), "V8_IDENTITY_MATCH_CHECK_FAILED")
                rejected = action.get("status") == "REJECTED"
                stream = action.get("token_ids") if rejected else action_to_ids(action, max_length=256)
                comparison = compare_sites(reference, stream)
                require(comparison["totals"]["reference_sites"] == len(sites), "V8_REFERENCE_DENOMINATOR_CHANGED")
                depth = str(validate_program(task["target"]["program"])["max_call_depth"])
                row = {"arm": arm, "cohort": split, "task_id": task["task_id"], "depth": depth,
                       "generated_stream_kind": "SAVED_REJECTED_TOKENS" if rejected else "CANONICAL_COMPLETE_ACTION_NOT_RAW_EMITTED_TOKENS",
                       "termination": comparison["generated"]["termination"],
                       "reference_role_counts": dict(ref_counts), "totals": comparison["totals"],
                       "by_role": comparison["summaries"]}
                rows.append(row)
                key = arm + "/" + split + "/depth_" + depth
                group = totals.setdefault(key, {"tasks": 0, "totals": Counter(),
                                                "by_role": {role: Counter() for role in ROLES}})
                group["tasks"] += 1
                group["totals"].update(row["totals"])
                for role in ROLES:
                    group["by_role"][role].update(row["by_role"][role])
    require(len(rows) == 480 and sum(row["totals"]["reference_sites"] for row in rows) == 9088,
            "V8_PANEL_COVERAGE_CHANGED")
    after = source_identity()
    require(before == after, "V8_OFFLINE_REPLAY_SOURCE_CHANGED")
    receipt = {"schema": "cas-meta2-saved-development-site-replay/8", "rows": rows, "groups": totals,
               "task_checkpoint_rows": 480, "distinct_tasks": 120, "reference_opportunity_rows": 9088,
               "bundle_manifest_sha256": args.manifest_sha256,
               "source_files_sha256": before, "source_after_sha256": after, "source_unchanged": True,
               "command": sys.argv, "python": sys.version, "model_executed": False,
               "boundary": "Stored development actions only. No new scores, model load, native task success or causal inference. Complete actions are canonically serialized, not claimed raw emitted tokens."}
    output.mkdir(parents=True, exist_ok=False)
    raw = canonical(receipt) + b"\n"
    with (output/"receipt.json").open("xb") as stream:
        stream.write(raw)
    print(json.dumps({"receipt": str(output/"receipt.json"), "sha256": sha256(raw).hexdigest(),
                      "task_checkpoint_rows": 480, "reference_opportunity_rows": 9088,
                      "model_executed": False}))


if __name__ == "__main__":
    main()
