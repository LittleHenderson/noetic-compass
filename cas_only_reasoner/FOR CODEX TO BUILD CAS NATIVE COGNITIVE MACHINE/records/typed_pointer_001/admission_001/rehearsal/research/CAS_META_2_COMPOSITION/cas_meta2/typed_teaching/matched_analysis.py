"""Frozen descriptive endpoints and evidence joins; never imports a learner/checker.

Input files must be collected from the bounded provider lifecycle. This module
checks their recorded identities; it does not replace provider/source attestation.
"""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from . import matched_contract as contract, source

require = contract.require
CHECKPOINTS = (0, 40, 80, 120, 160)
STATE_KEYS = tuple(k + "_state_identity" for k in ("model", "optimizer", "encoder", "rng"))


def accuracy(rows):
    require(bool(rows) and all(type(r["correct"]) is bool for r in rows), "METRIC_ROWS")
    count = sum(r["correct"] for r in rows)
    return {"correct": count, "total": len(rows), "accuracy": count / len(rows)}


def transitions(before, after):
    require(before.keys() == after.keys() and bool(before), "METRIC_PANEL_JOIN")
    require(all(before[k]["kind"] == after[k]["kind"] and before[k]["target_digest"] == after[k]["target_digest"]
        for k in before), "METRIC_TARGET_JOIN")
    pre, post = accuracy(list(before.values())), accuracy(list(after.values()))
    retained = sum(before[k]["correct"] and after[k]["correct"] for k in before)
    lost = pre["correct"] - retained
    gained = post["correct"] - retained
    return {"before": pre, "after": post, "accuracy_change": post["accuracy"] - pre["accuracy"],
        "retained_correct": retained, "lost": lost, "gained": gained,
        "still_incorrect": len(before) - retained - lost - gained,
        "fraction_baseline_correct_retained": retained / pre["correct"] if pre["correct"] else None}


def transition_panel(before, after, *, retention=False):
    result = transitions(before, after)
    result["by_kind"] = {kind: transitions({k: v for k, v in before.items() if v["kind"] == kind},
        {k: v for k, v in after.items() if v["kind"] == kind}) for kind in sorted({r["kind"] for r in before.values()})}
    if retention:
        result["eligible"] = 2 * result["before"]["correct"] >= result["before"]["total"]
        result["status"] = "RETENTION_ASSESSED" if result["eligible"] else "RETENTION_UNASSESSED"
    return result


def family_score(rows, families):
    ids = [key for f in families for key in f["record_ids"]]
    require(len(families) == 6 and len(ids) == len(set(ids)) and set(ids) == set(rows), "FAMILY_PANEL_JOIN")
    values = []
    for family in families:
        selected = [rows[key] for key in family["record_ids"]]
        parts = [r for r in selected if r["kind"] == "parts"]
        reach = [r for r in selected if r["kind"] == "reach"]
        require(len(parts) == 1 and len(reach) == len(selected) - 1 and bool(reach), "FAMILY_KINDS")
        a, b = accuracy(parts), accuracy(reach)
        values.append({"world_id": family["world_id"], "parts": a, "reach": b,
            "balanced_accuracy": (a["accuracy"] + b["accuracy"]) / 2})
    return {"family_balanced_accuracy": sum(r["balanced_accuracy"] for r in values) / 6,
        "families": values, "raw": accuracy(list(rows.values())),
        "by_kind": {kind: accuracy([r for r in rows.values() if r["kind"] == kind]) for kind in ("parts", "reach")}}


def speed_auc(curve):
    require(set(curve) == set(CHECKPOINTS) and all(type(v) in (int, float) and 0 <= v <= 1 for v in curve.values()), "SPEED_CURVE")
    return (curve[0] + 2*curve[40] + 2*curve[80] + 2*curve[120] + curve[160]) / 8


def join_scoring(prediction_raw, score, packets, *, phase):
    seal = json.loads(prediction_raw)
    pin = score["public_seal"]
    require(pin == {"name": phase + "_predictions.json", "bytes": len(prediction_raw),
        "sha256": sha256(prediction_raw).hexdigest()}, "SCORING_SEAL_PIN")
    require(seal["phase"] == score["phase"] == phase, "SCORING_PHASE")
    predictions, rows = seal["predictions"], score["rows"]
    require([p["record_id"] for p in predictions] == [r["record_id"] for r in rows] == list(packets), "SCORING_PANEL_ORDER")
    for prediction, row in zip(predictions, rows):
        packet = packets[row["record_id"]]
        query = packet["record"]["query"]
        require(row["prediction_id"] == prediction["prediction_id"]
            == "typed-prediction-" + source.digest({k: v for k, v in prediction.items() if k != "prediction_id"}), "PREDICTION_ID")
        require(row["answer_digest"] == source.digest(prediction["answer"]), "SCORING_ANSWER")
        require(prediction["packet_digest"] == source.digest(packet), "SCORING_PACKET")
        require(all(row[k] == query[k] for k in ("kind", "query_id", "source_digest", "rule")), "SCORING_QUERY")
        require(row["check_digest"] == source.digest({k: v for k, v in row.items()
            if k not in ("record_id", "prediction_id", "check_digest")}), "CHECK_ID")
    measured = accuracy(rows)
    require(score["correct"] == measured["correct"] and score["total"] == measured["total"], "SCORING_TOTALS")
    return {row["record_id"]: row for row in rows}


def read_artifacts(directory):
    from cncm import typed_matched_worker as worker
    directory = Path(directory).resolve(strict=True)
    manifest_raw = (directory / "manifest.json").read_bytes()
    entries = json.loads(manifest_raw)["artifacts"]
    require(len(entries) == len({r["name"] for r in entries}) <= 500, "MANIFEST_DUPLICATE")
    names = {r["name"] for r in entries}
    require(names == set(worker.EXPECTED_ARTIFACTS), "MANIFEST_ARTIFACTS")
    result, pins = {}, {}
    for pin in entries:
        name = pin["name"]
        path = directory / name
        require(Path(name).name == name and path.is_file() and not path.is_symlink()
            and path.stat().st_size <= 64*1024**2, "MANIFEST_PATH")
        raw = path.read_bytes()
        require(pin == {"name": name, "bytes": len(raw), "sha256": sha256(raw).hexdigest()}, "MANIFEST_PIN")
        pins[name] = pin
        if name.endswith(".json"): result[name] = raw
    return result, {"manifest_sha256": sha256(manifest_raw).hexdigest(), "artifacts": pins}


def analyze_arm(directory, root):
    from cncm import typed_matched_worker as worker
    blobs, audit = read_artifacts(directory)
    data = {name: json.loads(raw) for name, raw in blobs.items()}
    report = data["worker_report.json"]
    require(report["status"] == worker.SUCCESS_STATUS and report["checkpoint_reload_verified"] is True, "ARM_INCOMPLETE")
    condition, seed = contract.parse_job(report["job"])
    require(report["condition"] == condition and report["model_seed"] == seed, "ARM_IDENTITY")
    expected = contract.make_config(root, source_sha=report["source_sha"], job=report["job"],
        bucket=report["job"] + "-807562639912", condition=condition, model_seed=seed)
    require(report["design"] == expected["design"] and report["inputs"] == expected["inputs"], "ARM_CONFIG")
    frozen, _, development = contract.load_material(root)
    packets = dict(contract.public_packets(frozen))
    dev = contract.development_packets(development)
    probes = dict(contract.retention_packets(frozen))
    batches, stats = contract.schedule(frozen, condition)
    interference = contract.interference_batches(frozen)
    protocol = data["protocol_material.json"]
    require(protocol["schedule"] == {"batches": batches, "stats": stats}
        and protocol["interference_batches"] == interference and protocol["development"] == development
        and protocol["retention_record_ids"] == list(probes)
        and protocol["retention_packet_digests"] == {k: sha256(contract.canonical(v)).hexdigest() for k, v in probes.items()}, "ARM_PROTOCOL")
    scores = {}
    for phase in worker.EVALUATIONS:
        selected = dev if phase.startswith("development_") else probes if phase.startswith("retention_") else packets
        scores[phase] = join_scoring(blobs[phase + "_predictions.json"], data[phase + "_scoring.json"], selected, phase=phase)
    corrections = []
    for prefix, batch in [("main_%03d_" % i, b) for i, b in enumerate(batches)] + [
            ("interference_%03d_" % i, b) for i, b in enumerate(interference)]:
        seal, update = data[prefix + "batch.json"], data[prefix + "update.json"]
        require([p["record_id"] for p in seal["predictions"]] == batch["record_ids"]
            and seal["occurrence_ids"] == batch["occurrence_ids"] and seal["cursor"] == batch["cursor"], "TRAINING_BATCH_JOIN")
        require(update["public_seal_sha256"] == sha256(blobs[prefix + "batch.json"]).hexdigest()
            and update["batch_id"] == seal["batch_id"] and update["cursor_committed"] == batch["cursor"] + 1, "TRAINING_UPDATE_JOIN")
        rows = update["correction_identities"]
        require([r["record_id"] for r in rows] == batch["record_ids"]
            and all(r["target_digest"] == scores["initial"][r["record_id"]]["target_digest"] for r in rows), "CORRECTION_JOIN")
        corrections.extend((r["record_id"], batch["depth"], r["target_digest"]) for r in rows)
    initial = data["initial_checkpoint.json"]["metadata"]
    require(initial["cursor"] == 0 and all(v == 0 for v in initial["counters"].values()), "INITIAL_STATE_NOT_FRESH")
    for name, cursor in (("initial", 0), ("prelast", 159), ("final", 160), ("retained", 176)):
        pin = data[name + "_checkpoint.json"]
        require(pin["sha256"] == audit["artifacts"][name + ".pt"]["sha256"]
            and pin["bytes"] == audit["artifacts"][name + ".pt"]["bytes"]
            and pin["metadata"]["cursor"] == cursor, "CHECKPOINT_PIN")
    measured = report["global_actual_work"]
    phases = {r["phase"]: r["delta"] for r in measured["phases"]}
    require(len(phases) == len(measured["phases"]) and measured["historical_restored_counters_counted_again"] is False, "WORK_PHASES")
    require(worker._sum_deltas(list(phases.values())) == measured["totals"]
        and measured["totals"]["optimizer_updates"] == measured["totals"]["backward_calls"] == 178, "WORK_TOTALS")
    worker.base.validate_training_delta(phases["main_training"])
    curve = {cursor: family_score(scores["development_%03d" % cursor], development["families"]) for cursor in CHECKPOINTS}
    target_identity = {phase: source.digest([(k, r["target_digest"]) for k, r in rows.items()]) for phase, rows in scores.items()}
    return {"schema": "cncm.typed-matched-arm-analysis/0.1", "job": report["job"], "source_sha": report["source_sha"],
        "condition": condition, "model_seed": seed, "runtime": report["runtime"], "audit": audit,
        "initial_state": {k: initial[k] for k in STATE_KEYS}, "target_identities": target_identity,
        "correction_multiset_digest": source.digest(sorted(corrections)), "work_phases": phases,
        "global_work": measured["totals"], "elapsed_seconds": report["elapsed_seconds"],
        "development_curve": curve, "speed_auc": speed_auc({k: v["family_balanced_accuracy"] for k, v in curve.items()}),
        "transfer": curve[160]["family_balanced_accuracy"],
        "exposed": transition_panel(scores["initial"], scores["final"]),
        "retention": transition_panel(scores["retention_before"], scores["retention_after"], retention=True),
        "boundary": worker.BOUNDARY, "learning_advantage_established": False}


def compare_pairs(arms):
    by_key = {(a["model_seed"], a["condition"]): a for a in arms}
    require(len(by_key) == len(arms) == 6 and set(by_key) == {(s, c) for s in contract.MODEL_SEEDS for c in contract.CONDITIONS}, "SIX_PAIRED_ARMS_REQUIRED")
    require(len({a["source_sha"] for a in arms}) == 1, "PAIRED_SOURCE")
    pairs = []
    for seed in contract.MODEL_SEEDS:
        a, m = (by_key[seed, c] for c in contract.CONDITIONS)
        for key in ("initial_state", "runtime", "target_identities", "correction_multiset_digest", "work_phases", "global_work"):
            require(a[key] == m[key], "PAIRED_EQUALITY:" + key)
        require(a["development_curve"][0] == m["development_curve"][0], "PAIRED_INITIAL_PREDICTIONS")
        eligible = a["retention"]["eligible"] and m["retention"]["eligible"]
        pairs.append({"model_seed": seed, "alt_job": a["job"], "mixed_job": m["job"],
            "speed_auc_difference": a["speed_auc"] - m["speed_auc"], "transfer_difference": a["transfer"] - m["transfer"],
            "retention_status": "RETENTION_ASSESSED" if eligible else "RETENTION_UNASSESSED",
            "retained_fraction_difference": a["retention"]["fraction_baseline_correct_retained"] - m["retention"]["fraction_baseline_correct_retained"] if eligible else None})
    return {"schema": "cncm.typed-matched-paired-analysis/0.1", "pairs": pairs,
        "mean_speed_auc_difference": sum(p["speed_auc_difference"] for p in pairs) / 3,
        "mean_transfer_difference": sum(p["transfer_difference"] for p in pairs) / 3,
        "mean_retained_fraction_difference": sum(p["retained_fraction_difference"] for p in pairs) / 3
            if all(p["retention_status"] == "RETENTION_ASSESSED" for p in pairs) else None,
        "learning_advantage_established": False,
        "boundary": "Three paired development estimates conditional on one encoder and curriculum; no final-set or general CAS advantage claim."}
