"""Read-only JSON/byte summary of one delivered typed-course worker run.

No project imports, checkpoint decoding, numerical libraries or provider calls.
Verifies retained byte and join consistency, not the semantic checker's truth.
"""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path


def require(value, message):
    if not value:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def sha(path):
    digest = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load(path):
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= 64 * 1024 ** 2, "unsafe/missing JSON file")
    return json.loads(path.read_bytes())


def summary(artifacts, *, job, source_sha):
    artifacts = Path(artifacts).resolve(strict=True)
    manifest = load(artifacts / "manifest.json")
    entries = manifest["artifacts"]
    require(type(entries) is list and 0 < len(entries) <= 400, "artifact count")
    names = [row["name"] for row in entries]
    require(len(names) == len(set(names)), "duplicate artifact")
    pins = {}
    for row in entries:
        name = row["name"]
        require(type(name) is str and name == Path(name).name and not any(c in name for c in "/\\:"), "unsafe name")
        path = artifacts / name
        require(path.is_file() and not path.is_symlink() and type(row["bytes"]) is int
                and 0 <= row["bytes"] <= 64 * 1024 ** 2 and path.stat().st_size == row["bytes"], "artifact bytes: " + name)
        require(sha(path) == row["sha256"], "artifact digest: " + name)
        pins[name] = row
    def read(name):
        require(name in pins, "unbound artifact: " + name)
        return load(artifacts / name)
    report = read("worker_report.json")
    require(report["job"] == job and report["source_sha"] == source_sha, "worker job/source identity")
    result = {"schema": "typed-course-read-only-summary/0.1", "job": job, "source_sha": source_sha,
        "worker_status": report["status"], "artifact_count": len(entries),
        "artifact_bytes_verified": sum(row["bytes"] for row in entries),
        "manifest_sha256": sha(artifacts / "manifest.json"), "worker_report_sha256": pins["worker_report.json"]["sha256"],
        "elapsed_seconds": report.get("elapsed_seconds"), "phase": report.get("phase"),
        "failure": report.get("failure"), "partial_main": report.get("partial_main"),
        "completed_main_updates": report.get("completed_main_updates", 0),
        "boundary": "Exposed training-set accuracy change and recorded same-process mechanics; no held-out or matched learning advantage. JSON/byte joins checked without running the semantic checker or decoding checkpoints."}
    if report["status"] != "COMPLETE_EXPOSED_TYPED_COURSE_AND_SAME_PROCESS_RELOAD_OBSERVED":
        result["completed_work_phases"] = report.get("completed_work_phases", [])
        return result
    require(len(entries) == 344 and report["checkpoint_reload_verified"] is True, "success artifact/reload contract")
    require(report["learning_advantage_established"] is False, "claim boundary")
    phases, scored = {}, {}
    for phase in ("initial", "final"):
        seal_name = phase + "_predictions.json"
        seal = read(seal_name)
        rows = seal["predictions"]
        require(seal["phase"] == phase and len(rows) == 564, "full prediction count")
        require(len({row["record_id"] for row in rows}) == 564, "unique predictions")
        phases[phase] = {row["record_id"]: row for row in rows}
        for row in rows:
            require(row["prediction_id"] == "typed-prediction-" + sha256(canonical({k: v for k, v in row.items() if k != "prediction_id"})).hexdigest(), "prediction digest")
        score = read(phase + "_scoring.json")
        require(score["phase"] == phase and score["public_seal"] == pins[seal_name], "score seal binding")
        require(len(score["rows"]) == 564 and [r["record_id"] for r in score["rows"]] == list(phases[phase]), "score registry")
        for row in score["rows"]:
            require(type(row["correct"]) is bool and row["prediction_id"] == phases[phase][row["record_id"]]["prediction_id"], "score prediction binding")
        require(score["correct"] == sum(row["correct"] for row in score["rows"]) and score["total"] == 564, "score totals")
        scored[phase] = {row["record_id"]: row for row in score["rows"]}
    require(list(scored["initial"]) == list(scored["final"]), "phase registry match")
    metrics = {}
    for key, before in scored["initial"].items():
        after = scored["final"][key]
        require(all(before[field] == after[field] for field in ("query_id", "source_digest", "kind", "target_digest", "checker_profile_digest")), "same target across phases")
        row = metrics.setdefault(before["kind"], Counter())
        row["total"] += 1
        row["initial_correct"] += before["correct"]
        row["final_correct"] += after["correct"]
        row["gained"] += not before["correct"] and after["correct"]
        row["lost"] += before["correct"] and not after["correct"]
        row["unchanged_correct"] += before["correct"] and after["correct"]
        row["unchanged_incorrect"] += not before["correct"] and not after["correct"]
    result["by_kind"] = {kind: dict(counts) for kind, counts in sorted(metrics.items())}
    result["overall"] = {name: sum(row[name] for row in metrics.values()) for name in next(iter(metrics.values()))}
    for row in [result["overall"], *result["by_kind"].values()]:
        row["initial_accuracy"] = row["initial_correct"] / row["total"]
        row["final_accuracy"] = row["final_correct"] / row["total"]
        row["net_correct_change"] = row["final_correct"] - row["initial_correct"]
    main = report["main_training_delta"]
    require(main["optimizer_updates"] == main["backward_calls"] == 160 and main["prediction_calls"] == 1152
            and main["slot_forwards"] == 4613 and main["core_forward_calls"] == main["sample_core_passes"] == 17178, "main counts")
    updates = []
    for cursor in range(160):
        row = read("update_%03d.json" % cursor)
        require(row["cursor_committed"] == row["model_revision"] == cursor + 1, "main update cursor")
        require(row["public_seal_sha256"] == pins["batch_%03d.json" % cursor]["sha256"], "main update seal")
        updates.append(row)
    result["main_training_delta"] = main
    result["training_gradient_squared_norm_range"] = [min(row["gradient_squared_norm"] for row in updates), max(row["gradient_squared_norm"] for row in updates)]
    work = report["global_actual_work"]
    require(work["historical_restored_counters_counted_again"] is False, "restored history double count")
    summed = {key: sum(row["delta"][key] for row in work["phases"]) for key in work["totals"]}
    require(summed == work["totals"] and summed["optimizer_updates"] == summed["backward_calls"] == 162, "global counters")
    result["global_actual_work"] = work
    replay = read("replay_report.json")
    require([r["phase"] for r in replay["reloads"]] == ["initial", "final"] and len(replay["replays"]) == 2, "reload/replay count")
    for row in replay["reloads"]:
        phase = row["phase"]
        checkpoint = read(phase + "_checkpoint.json")
        require(checkpoint["sha256"] == pins[phase + ".pt"]["sha256"] == row["checkpoint_sha256"], "checkpoint pin")
        require(all(value == checkpoint["metadata"][field] for field, value in row["exact_state"].items()), "reload state identity")
        preds = read(phase + "_reload_predictions.json")["predictions"]
        require(len(preds) == len(row["kinds"]) == 8 and all(p == phases[phase][p["record_id"]] for p in preds), "reload exact predictions")
    final = read("final_checkpoint.json")
    for row in replay["replays"]:
        number = row["branch"]
        require(number in (1, 2) and row["restored_cursor"] == 159 and row["committed_cursor"] == 160
                and row["delta"]["optimizer_updates"] == row["delta"]["backward_calls"] == 1, "replay counter")
        require(all(value == final["metadata"][field] for field, value in row["exact_state"].items()), "replay final state")
        require(pins["replay_%d_batch.json" % number]["sha256"] == pins["batch_159.json"]["sha256"], "replay preupdate bytes")
        preds = read("replay_%d_predictions.json" % number)["predictions"]
        require(len(preds) == 8 and all(p == phases["final"][p["record_id"]] for p in preds), "replay final predictions")
    result["recorded_checkpoint_exactness"] = {"restores": 2, "last_update_replay_branches": 2,
        "model_optimizer_rng_encoder_state_hashes_joined": True, "representative_predictions_per_restore": 8,
        "checkpoints_decoded_by_summary_helper": False, "scope": "same process on same worker"}
    result["peak_cuda_allocated_bytes"] = report["peak_cuda_allocated_bytes"]
    result["peak_cuda_reserved_bytes"] = report["peak_cuda_reserved_bytes"]
    result["encoding_checks"] = read("encoding_checks.json")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--job", required=True)
    parser.add_argument("--source-sha", required=True)
    args = parser.parse_args()
    print(json.dumps(summary(args.artifacts, job=args.job, source_sha=args.source_sha),
                     indent=2, sort_keys=True, allow_nan=False))
