"""Complete exposed typed course worker. Importing this file does no numeric work.

CUDA is obtained only after pure source/config/material admission. This is a
same-process engineering check, not a controlled learning-advantage experiment.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import random
import time

from cas_meta2.typed_teaching import worker_contract as contract

CANDIDATE = contract.CANDIDATE
CONFIG_SCHEMA = contract.CONFIG_SCHEMA
RESULT_SCHEMA = "cncm.typed-course-worker-result/0.1"
FAILURE_SCHEMA = "cncm.typed-course-failure/0.1"
SUCCESS_STATUS = "COMPLETE_EXPOSED_TYPED_COURSE_AND_SAME_PROCESS_RELOAD_OBSERVED"
EXPECTED_ARTIFACTS = tuple("batch_%03d.json" % n for n in range(160)) + tuple(
    "update_%03d.json" % n for n in range(160)) + (
    "initial.pt", "prelast.pt", "final.pt", "initial_checkpoint.json",
    "prelast_checkpoint.json", "final_checkpoint.json", "initial_predictions.json",
    "final_predictions.json", "initial_scoring.json", "final_scoring.json",
    "initial_reload_predictions.json", "final_reload_predictions.json",
    "replay_1_batch.json", "replay_2_batch.json", "replay_1_update.json", "replay_2_update.json",
    "replay_1_predictions.json", "replay_2_predictions.json", "replay_report.json",
    "encoding_checks.json", "installed_sources.json", "loaded_sources.json",
    "worker_report.json", "measurements.json")
BOUNDARY = ("Complete exposed training material; same-process checkpoint reconstruction and replay. "
            "No held-out result, matched learning advantage, cross-device replay, or native-memory promotion claim.")
canonical, require = contract.canonical, contract.require


def _write_bytes(path, raw):
    path = Path(path)
    require(type(raw) is bytes and not path.is_symlink(), "OUTPUT_BYTES")
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    require(path.read_bytes() == raw, "OUTPUT_READBACK")
    return {"name": path.name, "bytes": len(raw), "sha256": sha256(raw).hexdigest()}


def _write(path, value):
    return _write_bytes(path, canonical(value))


def counter_delta(after, before):
    require(type(after) is dict and type(before) is dict and set(after) == set(before), "COUNTER_FIELDS")
    require(all(type(after[k]) is int and type(before[k]) is int and after[k] >= before[k] >= 0
                for k in after), "COUNTER_VALUES")
    return {k: after[k] - before[k] for k in after}


def validate_training_delta(delta):
    expected = {"slot_forwards": 4613, "core_forward_calls": 17178,
        "core_forward_attempts": 17178, "sample_core_passes": 17178,
        "prediction_calls": 1152, "staged_batches": 160, "private_loss_plan_calls": 1152,
        "backward_attempts": 160, "backward_calls": 160,
        "optimizer_step_attempts": 160, "optimizer_updates": 160}
    require(canonical(delta) == canonical(expected), "MAIN_TRAINING_COUNTERS")
    return deepcopy(expected)


def _deadline(started):
    require(time.monotonic() - started < contract.MAX_WALL_SECONDS, "DEADLINE_EXCEEDED")


def _progress(phase, started, **values):
    print(json.dumps({"typed_course_phase": phase, "elapsed_seconds": round(time.monotonic() - started, 2),
                      **values}, sort_keys=True, allow_nan=False), flush=True)


def _sealed_predictions(path, predictions, *, phase, expected_ids):
    require([p["record_id"] for p in predictions] == expected_ids, "PREDICTION_REGISTRY_ORDER")
    return _write(path, {"schema": "cncm.typed-course-prediction-seal/0.1",
                        "phase": phase, "predictions": predictions})


def _score_seal(path, pin, packets, *, started):
    """Only this post-readback path imports the private semantic checker."""
    raw = Path(path).read_bytes()
    require(len(raw) == pin["bytes"] and sha256(raw).hexdigest() == pin["sha256"], "SCORING_SEAL_CHANGED")
    seal = json.loads(raw)
    require([p["record_id"] for p in seal["predictions"]] == list(packets), "SCORING_REGISTRY_ORDER")
    from cas_meta2.typed_teaching import checker
    rows = []
    for prediction in seal["predictions"]:
        _deadline(started)
        packet = packets[prediction["record_id"]]
        checked = checker.check_answer(packet["source"], packet["record"]["query"], prediction["answer"])
        rows.append({"record_id": prediction["record_id"], "prediction_id": prediction["prediction_id"], **checked})
    return {"schema": "cncm.typed-course-private-scoring/0.1", "public_seal": pin,
            "phase": seal["phase"], "rows": rows, "correct": sum(r["correct"] for r in rows),
            "total": len(rows), "boundary": BOUNDARY}


def _train_step(learner, batch, packets, artifacts, *, prefix, started):
    _deadline(started)
    selected = [packets[key] for key in batch["record_ids"]]
    staged = learner.stage_batch(selected, batch["depth"], cursor=batch["cursor"],
                                 occurrence_ids=batch["occurrence_ids"])
    path = artifacts / (prefix + "batch.json")
    pin = _write_bytes(path, staged["bytes"])
    require(pin["sha256"] == staged["sha256"], "STAGED_SEAL_DIGEST")
    # The exact file is durable before targets are derived or passed to learner.
    from cas_meta2.typed_teaching import checker
    targets = [checker.derive_target(p["source"], p["record"]["query"]) for p in selected]
    result = learner.train_sealed_batch(path, expected_sha256=pin["sha256"], target_receipts=targets)
    _write(artifacts / (prefix + "update.json"), result)
    return pin, result


def _fresh_framework(torch, device):
    # The inherited builder's seed argument does not initialize torch's RNG.
    torch.manual_seed(contract.MODEL_SEED)
    torch.cuda.manual_seed_all(contract.MODEL_SEED)
    random.seed(contract.MODEL_SEED)
    from cas_meta2.graph_teaching.real_framework import build_graph_training_framework
    return build_graph_training_framework(torch, device, seed=contract.MODEL_SEED, encoder={"d_model": 64})


def _rng(torch):
    return {"torch_cpu": torch.get_rng_state(), "torch_cuda": torch.cuda.get_rng_state_all(),
            "python": random.getstate()}


def _state(torch, learner):
    from cas_meta2.typed_teaching.learner import state_identity
    return {"model_state_identity": state_identity(torch, dict(learner.module.state_dict())),
            "optimizer_state_identity": state_identity(torch, learner.optimizer.state_dict()),
            "rng_state_identity": state_identity(torch, _rng(torch)),
            "encoder_state_identity": state_identity(torch, learner.encoder.export_state())}


def _check_state(torch, learner, checkpoint):
    actual = _state(torch, learner)
    require(all(actual[k] == checkpoint["metadata"][k] for k in actual), "RESTORED_STATE_MISMATCH")
    return actual


def _representatives(packets):
    result = {}
    for key, packet in packets.items():
        result.setdefault(packet["record"]["query"]["kind"], key)
    require(set(result) == {"role_set", "definition", "context", "analogy", "correspondence",
                           "parts", "edge_account", "reach"}, "EIGHT_KIND_COVERAGE")
    return {kind: result[kind] for kind in sorted(result)}


def _encoding_checks(torch, encoder, packets, representatives, *, started, all_packets):
    from cas_meta2.typed_teaching import slots
    before = encoder.work_counters()
    norms, rows = [], []
    keys = list(packets) if all_packets else list(representatives.values())
    for key in keys:
        _deadline(started)
        vector = encoder.encode_packet(packets[key])
        require(tuple(vector.shape) == (64,) and bool(torch.isfinite(vector).all().item()), "PACKET_ENCODE_NONFINITE")
        norm = float(torch.linalg.vector_norm(vector).item())
        require(math.isfinite(norm) and abs(norm - 1.0) <= 2e-5, "PACKET_UNIT_NORM")
        norms.append(norm)
    for kind, key in representatives.items():
        _deadline(started)
        packet = packets[key]
        cached = encoder.encode_packet(packet)
        direct = encoder.encode_packet(packet, use_cache=False)
        require(torch.equal(cached, direct), "PACKET_CACHE_DIRECT_MISMATCH")
        plan = slots.compile_slots(packet)
        # One explicitly recorded slot per kind; every task's other slots execute
        # in the full initial/final prediction runs and training course.
        slot = plan["slots"][0]
        cached_slot = encoder.encode_slot(packet, plan, slot)
        direct_slot = encoder.encode_slot(packet, plan, slot, use_cache=False)
        require(torch.equal(cached_slot, direct_slot) and bool(torch.isfinite(direct_slot).all().item()),
                "SLOT_CACHE_DIRECT_MISMATCH")
        norm = float(torch.linalg.vector_norm(direct_slot).item())
        require(math.isfinite(norm) and abs(norm - 1.0) <= 2e-5, "SLOT_UNIT_NORM")
        rows.append({"kind": kind, "record_id": key, "slot_id": slot["slot_id"],
                     "packet_exact": True, "slot_exact": True, "slot_norm": norm})
    readout = encoder.readout_rows
    require(bool(torch.isfinite(readout).all().item()) and int(torch.unique(readout, dim=0).shape[0]) == 90,
            "READOUT_NONFINITE_OR_DUPLICATE")
    require(bool((torch.abs(torch.linalg.vector_norm(readout, dim=1) - 1.0) <= 2e-5).all().item()), "READOUT_UNIT_NORM")
    return {"finite_unit_packet_count": len(keys), "packet_norm_range": [min(norms), max(norms)],
            "representatives": rows, "readout_distinct_unit_rows": 90,
            "frozen_identity": encoder.verify_frozen(), "counters_before": before,
            "counters_after": encoder.work_counters()}


def deliver(results, artifacts, report, *, failed):
    results, artifacts = Path(results), Path(artifacts)
    artifacts.mkdir(parents=True, exist_ok=True)
    if not failed:
        require(set(EXPECTED_ARTIFACTS) - {"worker_report.json", "measurements.json"}
                <= {p.name for p in artifacts.iterdir()}, "REQUIRED_ARTIFACTS")
    _write(artifacts / "worker_report.json", report)
    summary = {key: report.get(key) for key in ("job", "source_sha", "status", "runtime", "elapsed_seconds",
        "failure", "main_training_delta", "global_actual_work", "checkpoint_reload_verified", "initial_score", "final_score")}
    summary.update(learning_advantage_established=False, boundary=BOUNDARY)
    _write(artifacts / "measurements.json", summary)
    entries = []
    for path in sorted(artifacts.iterdir()):
        require(path.is_file() and not path.is_symlink() and path.stat().st_size <= 64 * 1024 ** 2, "FLAT_ARTIFACT_BOUND")
        raw = path.read_bytes()
        entries.append({"name": path.name, "bytes": len(raw), "sha256": sha256(raw).hexdigest()})
    require(len(entries) <= 400, "ARTIFACT_COUNT_BOUND")
    _write(artifacts / "manifest.json", {"artifacts": entries})
    result = {"schema": RESULT_SCHEMA, "job": report["job"], "artifacts": entries,
              "status": "TYPED_COURSE_FAILED" if failed else "TYPED_COURSE_DELIVERED",
              "summary": summary, "failure": report.get("failure"), "boundary": BOUNDARY}
    pin = _write(results / "result.json", result)
    _write_bytes(results / "result.json.sha256", (pin["sha256"] + "\n").encode("ascii"))
    return result


def run(config, root, results, artifacts, attestor=None):
    """Run only on an admitted CUDA worker; retain every completed phase on failure."""
    started = time.monotonic()
    root, results, artifacts = Path(root).resolve(), Path(results).resolve(), Path(artifacts).resolve()
    config = contract.validate_config(config, root)
    frozen, tokenizer, schedule = contract.load_material(root)
    require(not artifacts.exists() and artifacts.parent == results and not (results / "result.json").exists(),
            "FRESH_RESULT_DIRECTORY")
    results.mkdir(parents=True, exist_ok=True)
    artifacts.mkdir()
    report = {"schema": "cncm.typed-course-worker-report/0.1", "candidate": CANDIDATE,
              "job": config["job"], "source_sha": config["source_sha"], "inputs": config["inputs"],
              "design": config["design"], "schedule": schedule, "boundary": BOUNDARY,
              "learning_advantage_established": False, "phase": "admitted"}
    main = None
    measured = []
    try:
        # Must be first numerical capability call; Windows refusal is delivered.
        _progress("preflight", started)
        # Set before importing torch/creating its CUDA context; deterministic
        # cuBLAS otherwise refuses matrix operations on this CUDA runtime.
        os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
        from cas_meta2.teaching_cycle.gpu_adapter import _cuda
        torch, device = _cuda()
        torch.cuda.reset_peak_memory_stats(device)
        require(attestor is not None and callable(getattr(attestor, "snapshot", None)), "SOURCE_ATTESTOR_REQUIRED")
        loaded_before = attestor.snapshot()
        from .rpa_learning_worker import verify_worker_packages
        packages_before = verify_worker_packages(root)
        report["runtime"] = {"device": str(device), "torch_version": str(torch.__version__),
            "cuda_version": torch.version.cuda, "gpu_name": torch.cuda.get_device_name(device)}
        require(report["runtime"]["torch_version"] == "2.11.0+cu128" and report["runtime"]["cuda_version"] == "12.8"
                and "RTX PRO 4500" in report["runtime"]["gpu_name"], "RUNTIME_MISMATCH")
        torch.use_deterministic_algorithms(True)
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        _progress("public_packet_preparation", started)
        packets = dict(contract.public_packets(frozen))
        representatives = _representatives(packets)
        _deadline(started)
        from cas_meta2.typed_teaching.encoder import build_frozen_typed_encoder
        from cas_meta2.typed_teaching.learner import TypedCourseLearner
        framework = _fresh_framework(torch, device)
        encoder = build_frozen_typed_encoder(torch, tokenizer, seed=contract.ENCODER_SEED, d_model=64, device=device)
        main = TypedCourseLearner(torch, framework, encoder, optimizer_config=contract.DESIGN["optimizer_config"],
            run_context={"run_id": config["job"], "course_sha256": contract.MATERIAL[contract.COURSE_PATH]["sha256"],
                         "condition": contract.DESIGN["condition"], "source_seed": 101},
            limits={"max_updates": 160, "max_core_calls": 100000, "max_wall_seconds": contract.MAX_WALL_SECONDS}, device=device)
        initial = main.export_checkpoint(artifacts / "initial.pt")
        _write(artifacts / "initial_checkpoint.json", initial)
        report["phase"] = "encoding_checks"
        _progress(report["phase"], started)
        encoding = {"initial": _encoding_checks(torch, encoder, packets, representatives, started=started, all_packets=True)}
        predictions = {}
        checkpoint_pins = {"initial": initial}
        for phase in ("initial", "final"):
            report["phase"] = phase + "_predictions"
            _progress(report["phase"], started)
            baseline = deepcopy(main.counters)
            rows = []
            for packet in packets.values():
                _deadline(started)
                rows.append(main.predict(packet, 8))
            measured.append({"phase": phase + "_predictions", "delta": counter_delta(main.counters, baseline)})
            pin = _sealed_predictions(artifacts / (phase + "_predictions.json"), rows, phase=phase, expected_ids=list(packets))
            predictions[phase] = {row["record_id"]: row for row in rows}
            # All 564 predictions exist durably before this phase's scoring.
            scored = _score_seal(artifacts / pin["name"], pin, packets, started=started)
            _write(artifacts / (phase + "_scoring.json"), scored)
            report[phase + "_score"] = {"correct": scored["correct"], "total": scored["total"]}
            if phase == "initial":
                report["phase"] = "main_training"
                _progress(report["phase"], started)
                before_training = deepcopy(main.counters)
                for batch in frozen["batches"]:
                    _deadline(started)
                    cursor = batch["cursor"]
                    if cursor == 159:
                        checkpoint_pins["prelast"] = main.export_checkpoint(artifacts / "prelast.pt")
                        _write(artifacts / "prelast_checkpoint.json", checkpoint_pins["prelast"])
                    # Use canonical public batch filenames; update receipts remain
                    # separate so an interrupted course cannot lose completed work.
                    selected = [packets[key] for key in batch["record_ids"]]
                    staged = main.stage_batch(selected, batch["depth"], cursor=cursor, occurrence_ids=batch["occurrence_ids"])
                    path = artifacts / ("batch_%03d.json" % cursor)
                    seal = _write_bytes(path, staged["bytes"])
                    require(seal["sha256"] == staged["sha256"], "MAIN_STAGE_SEAL")
                    from cas_meta2.typed_teaching import checker
                    targets = [checker.derive_target(p["source"], p["record"]["query"]) for p in selected]
                    update = main.train_sealed_batch(path, expected_sha256=seal["sha256"], target_receipts=targets)
                    _write(artifacts / ("update_%03d.json" % cursor), update)
                    require(update["gradient_squared_norm"] > 0, "ZERO_TRAINING_GRADIENT")
                    report["completed_main_updates"] = main.cursor
                    if main.cursor % 10 == 0:
                        _progress("main_training", started, cursor=main.cursor,
                                  raw_batch_loss=update["raw_batch_loss"])
                training_delta = counter_delta(main.counters, before_training)
                report["main_training_delta"] = validate_training_delta(training_delta)
                measured.append({"phase": "main_training", "delta": training_delta})
                checkpoint_pins["final"] = main.export_checkpoint(artifacts / "final.pt")
                _write(artifacts / "final_checkpoint.json", checkpoint_pins["final"])
                require(initial["metadata"]["model_state_identity"] != checkpoint_pins["final"]["metadata"]["model_state_identity"],
                        "TRAINABLE_CORE_UNCHANGED")
        encoding["final"] = _encoding_checks(torch, encoder, packets, representatives, started=started, all_packets=False)
        _write(artifacts / "encoding_checks.json", encoding)
        report["phase"] = "independent_checkpoint_reconstruction"
        _progress(report["phase"], started)
        reload_reports = []
        for phase in ("initial", "final"):
            _deadline(started)
            checkpoint = checkpoint_pins[phase]
            restored = TypedCourseLearner.restore_checkpoint(torch, _fresh_framework(torch, device),
                path=artifacts / (phase + ".pt"), expected_sha256=checkpoint["sha256"],
                expected_run_identity_digest=main.run_identity_digest, device=device)
            state = _check_state(torch, restored, checkpoint)
            baseline = deepcopy(restored.counters)
            rows = [restored.predict(packets[key], 8) for key in representatives.values()]
            require(all(canonical(row) == canonical(predictions[phase][row["record_id"]]) for row in rows), "RELOAD_PREDICTION_MISMATCH")
            _sealed_predictions(artifacts / (phase + "_reload_predictions.json"), rows, phase=phase + "_reload",
                                expected_ids=list(representatives.values()))
            delta = counter_delta(restored.counters, baseline)
            measured.append({"phase": phase + "_reload", "delta": delta})
            reload_reports.append({"phase": phase, "checkpoint_sha256": checkpoint["sha256"],
                                   "exact_state": state, "kinds": representatives, "exact_predictions": True, "delta": delta})
            del restored
        report["phase"] = "independent_last_update_replays"
        _progress(report["phase"], started)
        replay_reports = []
        for branch in (1, 2):
            _deadline(started)
            checkpoint = checkpoint_pins["prelast"]
            restored = TypedCourseLearner.restore_checkpoint(torch, _fresh_framework(torch, device),
                path=artifacts / "prelast.pt", expected_sha256=checkpoint["sha256"],
                expected_run_identity_digest=main.run_identity_digest, device=device)
            _check_state(torch, restored, checkpoint)
            baseline = deepcopy(restored.counters)
            prefix = "replay_%d_" % branch
            seal, update = _train_step(restored, frozen["batches"][-1], packets, artifacts, prefix=prefix, started=started)
            require((artifacts / seal["name"]).read_bytes() == (artifacts / "batch_159.json").read_bytes(), "REPLAY_PREUPDATE_PREDICTION_MISMATCH")
            state = _check_state(torch, restored, checkpoint_pins["final"])
            rows = [restored.predict(packets[key], 8) for key in representatives.values()]
            require(all(canonical(row) == canonical(predictions["final"][row["record_id"]]) for row in rows), "REPLAY_POSTUPDATE_PREDICTION_MISMATCH")
            _sealed_predictions(artifacts / (prefix + "predictions.json"), rows, phase=prefix.rstrip("_"),
                                expected_ids=list(representatives.values()))
            delta = counter_delta(restored.counters, baseline)
            require(delta["optimizer_updates"] == delta["backward_calls"] == delta["staged_batches"] == 1, "REPLAY_UPDATE_COUNT")
            measured.append({"phase": prefix.rstrip("_"), "delta": delta})
            replay_reports.append({"branch": branch, "restored_cursor": 159, "committed_cursor": restored.cursor,
                "exact_state": state, "exact_preupdate_predictions": True, "exact_postupdate_predictions": True,
                "additional_presentations": len(frozen["batches"][-1]["record_ids"]), "delta": delta})
            del restored
        _write(artifacts / "replay_report.json", {"schema": "cncm.typed-course-reload/0.1", "reloads": reload_reports,
            "replays": replay_reports, "boundary": "Independent same-process restores; no cross-device or fresh-process numeric claim."})
        totals = {key: sum(row["delta"][key] for row in measured) for key in main.counters}
        require(totals["optimizer_updates"] == 162 and totals["backward_calls"] == 162
                and totals["optimizer_step_attempts"] == 162, "GLOBAL_UPDATE_COUNTS")
        report["global_actual_work"] = {"phases": measured, "totals": totals,
            "main_presentations": 1152, "additional_replay_presentations": 2 * len(frozen["batches"][-1]["record_ids"]),
            "historical_restored_counters_counted_again": False, "encoder_main_counters": encoder.work_counters()}
        require(canonical(contract.input_inventory(root)) == canonical(config["inputs"]), "SOURCES_CHANGED")
        packages_after = verify_worker_packages(root)
        require(packages_before["source_files"] == packages_after["source_files"], "WHEEL_SOURCES_CHANGED")
        _write(artifacts / "installed_sources.json", {"before": packages_before, "after": packages_after})
        _write(artifacts / "loaded_sources.json", {"before": loaded_before, "after": attestor.snapshot()})
        _deadline(started)
        report.update(status=SUCCESS_STATUS, phase="complete", checkpoint_reload_verified=True,
                      peak_cuda_allocated_bytes=int(torch.cuda.max_memory_allocated(device)),
                      peak_cuda_reserved_bytes=int(torch.cuda.max_memory_reserved(device)),
                      elapsed_seconds=time.monotonic() - started)
        _progress("complete", started, main_updates=160, global_updates=162)
        return deliver(results, artifacts, report, failed=False)
    except Exception as error:
        report.update(status="TYPED_COURSE_FAILED", elapsed_seconds=time.monotonic() - started,
            failure={"schema": FAILURE_SCHEMA, "type": type(error).__name__, "detail": str(error)[:1000]},
            completed_work_phases=measured)
        if main is not None:
            report["partial_main"] = {"cursor": main.cursor, "model_revision": main.model_revision,
                                      "counters": deepcopy(main.counters), "learner_failed": main.failed}
        deliver(results, artifacts, report, failed=True)
        raise
