"""One predeclared matched-study arm; numerical execution is CUDA-worker only.

Both arms use this source. Scoring never changes schedules or stopping rules.
Final-study tasks are not admitted by this development experiment.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import random
import time

from cas_meta2.typed_teaching import matched_contract as contract
from . import typed_course_worker as base

CANDIDATE = contract.CANDIDATE
CONFIG_SCHEMA = contract.CONFIG_SCHEMA
RESULT_SCHEMA = "cncm.typed-matched-worker-result/0.1"
FAILURE_SCHEMA = "cncm.typed-matched-failure/0.1"
SUCCESS_STATUS = "COMPLETE_TYPED_MATCHED_DEVELOPMENT_ARM"
BOUNDARY = ("One arm of a frozen development curriculum-order comparison; all eight training kinds retained. "
    "Transfer covers parts/reach on six development graph families and changes graph size. "
    "No protected final-study, general CAS architecture, or full-machine claim.")
CHECKPOINTS = (0, 40, 80, 120, 160)
EVALUATIONS = ("initial", "final", "retention_before", "retention_after") + tuple(
    "development_%03d" % n for n in CHECKPOINTS)
EXPECTED_ARTIFACTS = tuple(prefix + suffix for prefix in (
    *("main_%03d_" % n for n in range(160)), *("interference_%03d_" % n for n in range(16)),
    "replay_1_", "replay_2_") for suffix in ("batch.json", "update.json")) + tuple(
    phase + suffix for phase in EVALUATIONS for suffix in ("_predictions.json", "_scoring.json")) + tuple(
    phase + suffix for phase in ("initial", "prelast", "final", "retained")
    for suffix in (".pt", "_checkpoint.json")) + tuple(
    phase + "_reload_predictions.json" for phase in ("initial", "final", "retained")) + (
    "replay_1_predictions.json", "replay_2_predictions.json", "replay_report.json", "encoding_checks.json",
    "installed_sources.json", "loaded_sources.json", "protocol_material.json", "worker_report.json", "measurements.json")
canonical, require = contract.canonical, contract.require
_write, _write_bytes = base._write, base._write_bytes


def _framework(torch, device, seed):
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    random.seed(seed)
    from cas_meta2.graph_teaching.real_framework import build_graph_training_framework
    return build_graph_training_framework(torch, device, seed=seed, encoder={"d_model": 64})


def _sum_deltas(rows):
    require(rows and all(set(row) == set(rows[0]) for row in rows), "DELTA_SUM_FIELDS")
    return {key: sum(row[key] for row in rows) for key in rows[0]}


def _train_step(learner, batch, packets, artifacts, *, prefix, started):
    """Seal before correction, retaining condition-independent target identities."""
    base._deadline(started)
    selected = [packets[key] for key in batch["record_ids"]]
    staged = learner.stage_batch(selected, batch["depth"], cursor=batch["cursor"],
        occurrence_ids=batch["occurrence_ids"])
    path = artifacts / (prefix + "batch.json")
    pin = _write_bytes(path, staged["bytes"])
    require(pin["sha256"] == staged["sha256"], "STAGED_SEAL_DIGEST")
    from cas_meta2.typed_teaching import checker
    targets = [checker.derive_target(p["source"], p["record"]["query"]) for p in selected]
    update = learner.train_sealed_batch(path, expected_sha256=pin["sha256"], target_receipts=targets)
    update["correction_identities"] = [{"record_id": key, "target_digest": target["target_digest"]}
        for key, target in zip(batch["record_ids"], targets)]
    _write(artifacts / (prefix + "update.json"), update)
    return pin, update


def _evaluate(learner, packets, phase_name, artifacts, *, started, progress, work):
    base._deadline(started)
    state = base._state(learner.torch, learner)
    counters = deepcopy(learner.counters)
    began = time.monotonic()
    progress(phase_name + "_predictions", completed_packets=0, total_packets=len(packets))
    rows = []
    for packet in packets.values():
        base._deadline(started)
        rows.append(learner.predict(packet, 8))
        if len(rows) % 50 == 0 or len(rows) == len(packets):
            progress(phase_name + "_predictions", completed_packets=len(rows), total_packets=len(packets))
    path = artifacts / (phase_name + "_predictions.json")
    pin = base._sealed_predictions(path, rows, phase=phase_name, expected_ids=list(packets))
    # Durable public bytes precede all evaluation targets. The worker never adapts
    # its course, optimizer or sample selection to these scores.
    scored = base._score_seal(path, pin, packets, started=started, progress=progress)
    scored["boundary"] = BOUNDARY
    _write(artifacts / (phase_name + "_scoring.json"), scored)
    require(state == base._state(learner.torch, learner), "EVALUATION_CHANGED_LEARNED_STATE")
    delta = base.counter_delta(learner.counters, counters)
    require(delta["optimizer_updates"] == delta["backward_calls"] == 0, "EVALUATION_UPDATED_MODEL")
    work.append({"phase": phase_name, "delta": delta, "elapsed_seconds": time.monotonic() - began})
    return {row["record_id"]: row for row in rows}, scored


def deliver(results, artifacts, report, *, failed):
    artifacts = Path(artifacts)
    artifacts.mkdir(parents=True, exist_ok=True)
    if not failed:
        require(set(EXPECTED_ARTIFACTS) - {"worker_report.json", "measurements.json"}
            <= {p.name for p in artifacts.iterdir()}, "MATCHED_REQUIRED_ARTIFACTS")
    _write(artifacts / "worker_report.json", report)
    summary = {key: report.get(key) for key in ("job", "source_sha", "status", "runtime", "elapsed_seconds",
        "condition", "model_seed", "failure", "main_training_delta", "interference_delta", "global_actual_work",
        "checkpoint_reload_verified", "initial_score", "final_score", "development_scores", "retention_scores")}
    summary.update(learning_advantage_established=False, boundary=BOUNDARY)
    _write(artifacts / "measurements.json", summary)
    entries = []
    for path in sorted(artifacts.iterdir()):
        require(path.is_file() and not path.is_symlink() and path.stat().st_size <= 64 * 1024 ** 2, "ARTIFACT_BOUND")
        raw = path.read_bytes()
        entries.append({"name": path.name, "bytes": len(raw), "sha256": sha256(raw).hexdigest()})
    require(len(entries) <= 500, "ARTIFACT_COUNT")
    _write(artifacts / "manifest.json", {"artifacts": entries})
    result = {"schema": RESULT_SCHEMA, "job": report["job"], "artifacts": entries,
        "status": "TYPED_MATCHED_FAILED" if failed else "TYPED_MATCHED_DELIVERED",
        "summary": summary, "failure": report.get("failure"), "boundary": BOUNDARY}
    pin = _write(Path(results) / "result.json", result)
    _write_bytes(Path(results) / "result.json.sha256", (pin["sha256"] + "\n").encode("ascii"))
    return result


def run(config, root, results, artifacts, attestor=None):
    started = time.monotonic()
    root, results, artifacts = Path(root).resolve(), Path(results).resolve(), Path(artifacts).resolve()
    config = contract.validate_config(config, root)
    frozen, tokenizer, development = contract.load_material(root)
    design = config["design"]
    require(not artifacts.exists() and artifacts.parent == results and not (results / "result.json").exists(),
        "FRESH_RESULT_DIRECTORY")
    results.mkdir(parents=True, exist_ok=True)
    artifacts.mkdir()
    report = {"schema": "cncm.typed-matched-worker-report/0.1", "candidate": CANDIDATE,
        "job": config["job"], "source_sha": config["source_sha"], "inputs": config["inputs"], "design": design,
        "condition": design["condition"], "model_seed": design["model_seed"], "boundary": BOUNDARY,
        "learning_advantage_established": False, "phase": "admitted"}
    main, progress = None, None
    work = []
    def phase(name, **values):
        report["phase"] = name
        return progress.emit(name, **values)
    try:
        progress = base._ProgressWriter(results, started)
        phase("preflight")
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
        phase("public_packet_preparation")
        packets = dict(contract.public_packets(frozen))
        development_packets = contract.development_packets(development)
        retention_packets = dict(contract.retention_packets(frozen))
        batches, schedule_stats = contract.schedule(frozen, design["condition"])
        schedule = {"batches": batches, "stats": schedule_stats}
        interference = contract.interference_batches(frozen)
        representatives = base._representatives(packets)
        _write(artifacts / "protocol_material.json", {"schedule": schedule,
            "interference_batches": interference, "development": development,
            "retention_record_ids": list(retention_packets),
            "retention_packet_digests": {key: sha256(canonical(value)).hexdigest() for key, value in retention_packets.items()}})
        from cas_meta2.typed_teaching.encoder import build_frozen_typed_encoder
        from cas_meta2.typed_teaching.learner import TypedCourseLearner
        phase("fresh_initialization")
        main = TypedCourseLearner(torch, _framework(torch, device, design["model_seed"]),
            build_frozen_typed_encoder(torch, tokenizer, seed=design["encoder_seed"], d_model=64, device=device),
            optimizer_config=design["optimizer_config"],
            run_context={"run_id": config["job"], "course_sha256": contract.MATERIAL[contract.COURSE_PATH]["sha256"],
                "condition": design["condition"], "source_seed": 101},
            limits={"max_updates": 176, "max_core_calls": 200000, "max_wall_seconds": contract.MAX_WALL_SECONDS}, device=device)
        checkpoint_pins, predictions = {}, {}
        def checkpoint(name):
            phase(name + "_checkpoint", completed_updates=main.cursor)
            checkpoint_pins[name] = main.export_checkpoint(artifacts / (name + ".pt"))
            _write(artifacts / (name + "_checkpoint.json"), checkpoint_pins[name])
        checkpoint("initial")
        encoding = {"initial": base._encoding_checks(torch, main.encoder, packets, representatives,
            started=started, all_packets=True, progress=phase, phase="initial_encoding")}
        predictions["initial"], scored = _evaluate(main, packets, "initial", artifacts, started=started, progress=phase, work=work)
        report["initial_score"] = {"correct": scored["correct"], "total": scored["total"]}
        report["development_scores"] = []
        def evaluate_development(cursor):
            _, score = _evaluate(main, development_packets, "development_%03d" % cursor, artifacts,
                started=started, progress=phase, work=work)
            report["development_scores"].append({"cursor": cursor, "correct": score["correct"], "total": score["total"]})
        evaluate_development(0)
        main_deltas = []
        for cursor, batch in enumerate(schedule["batches"]):
            if cursor == 159: checkpoint("prelast")
            before = deepcopy(main.counters)
            _, update = _train_step(main, batch, packets, artifacts, prefix="main_%03d_" % cursor, started=started)
            require(update["gradient_squared_norm"] > 0, "ZERO_TRAINING_GRADIENT")
            main_deltas.append(base.counter_delta(main.counters, before))
            report["completed_main_updates"] = main.cursor
            if main.cursor in range(20, 160, 20): base._partial_checkpoint(main, results, main.cursor)
            if main.cursor % 10 == 0: phase("main_training", completed_main_updates=main.cursor, total_main_updates=160)
            if main.cursor in CHECKPOINTS[1:-1]: evaluate_development(main.cursor)
        report["main_training_delta"] = base.validate_training_delta(_sum_deltas(main_deltas))
        work.append({"phase": "main_training", "delta": report["main_training_delta"]})
        checkpoint("final")
        require(checkpoint_pins["initial"]["metadata"]["model_state_identity"] != checkpoint_pins["final"]["metadata"]["model_state_identity"], "TRAINABLE_CORE_UNCHANGED")
        predictions["final"], scored = _evaluate(main, packets, "final", artifacts, started=started, progress=phase, work=work)
        report["final_score"] = {"correct": scored["correct"], "total": scored["total"]}
        evaluate_development(160)
        _, before_score = _evaluate(main, retention_packets, "retention_before", artifacts, started=started, progress=phase, work=work)
        interference_deltas = []
        for index, batch in enumerate(interference):
            before = deepcopy(main.counters)
            _, update = _train_step(main, batch, packets, artifacts, prefix="interference_%03d_" % index, started=started)
            require(update["gradient_squared_norm"] > 0, "ZERO_INTERFERENCE_GRADIENT")
            interference_deltas.append(base.counter_delta(main.counters, before))
            phase("interference_training", completed_updates=main.cursor, total_updates=176)
        report["interference_delta"] = _sum_deltas(interference_deltas)
        require(report["interference_delta"]["optimizer_updates"] == 16 and report["interference_delta"]["prediction_calls"] == 128, "INTERFERENCE_COUNTS")
        work.append({"phase": "interference_training", "delta": report["interference_delta"]})
        checkpoint("retained")
        retained_predictions, after_score = _evaluate(main, retention_packets, "retention_after", artifacts, started=started, progress=phase, work=work)
        report["retention_scores"] = {"before": {k: before_score[k] for k in ("correct", "total")},
            "after": {k: after_score[k] for k in ("correct", "total")},
            "starting_competence_met": 2 * before_score["correct"] >= before_score["total"]}
        encoding["final"] = base._encoding_checks(torch, main.encoder, packets, representatives,
            started=started, all_packets=False, progress=phase, phase="final_encoding")
        _write(artifacts / "encoding_checks.json", encoding)
        reloads, replays = [], []
        for name in ("initial", "final", "retained"):
            phase(name + "_reconstruction")
            pin = checkpoint_pins[name]
            restored = TypedCourseLearner.restore_checkpoint(torch, _framework(torch, device, design["model_seed"]),
                path=artifacts / (name + ".pt"), expected_sha256=pin["sha256"],
                expected_run_identity_digest=main.run_identity_digest, device=device)
            exact = base._check_state(torch, restored, pin)
            before = deepcopy(restored.counters)
            selected = list(retention_packets)[:8] if name == "retained" else list(representatives.values())
            source_packets = retention_packets if name == "retained" else packets
            expected = retained_predictions if name == "retained" else predictions[name]
            rows = [restored.predict(source_packets[key], 8) for key in selected]
            require(all(canonical(row) == canonical(expected[row["record_id"]]) for row in rows), "RELOAD_PREDICTION_MISMATCH")
            base._sealed_predictions(artifacts / (name + "_reload_predictions.json"), rows, phase=name + "_reload", expected_ids=selected)
            delta = base.counter_delta(restored.counters, before)
            work.append({"phase": name + "_reload", "delta": delta})
            reloads.append({"phase": name, "checkpoint_sha256": pin["sha256"], "exact_state": exact, "prediction_ids": selected, "delta": delta})
            del restored
        for branch in (1, 2):
            phase("replay_%d" % branch)
            pin = checkpoint_pins["prelast"]
            restored = TypedCourseLearner.restore_checkpoint(torch, _framework(torch, device, design["model_seed"]),
                path=artifacts / "prelast.pt", expected_sha256=pin["sha256"], expected_run_identity_digest=main.run_identity_digest, device=device)
            base._check_state(torch, restored, pin)
            before = deepcopy(restored.counters)
            prefix = "replay_%d_" % branch
            seal, update = _train_step(restored, schedule["batches"][-1], packets, artifacts, prefix=prefix, started=started)
            require((artifacts / seal["name"]).read_bytes() == (artifacts / "main_159_batch.json").read_bytes(), "REPLAY_PREUPDATE_MISMATCH")
            exact = base._check_state(torch, restored, checkpoint_pins["final"])
            rows = [restored.predict(packets[key], 8) for key in representatives.values()]
            require(all(canonical(row) == canonical(predictions["final"][row["record_id"]]) for row in rows), "REPLAY_FINAL_MISMATCH")
            base._sealed_predictions(artifacts / (prefix + "predictions.json"), rows, phase=prefix.rstrip("_"), expected_ids=list(representatives.values()))
            delta = base.counter_delta(restored.counters, before)
            require(delta["optimizer_updates"] == delta["backward_calls"] == 1, "REPLAY_COUNTS")
            work.append({"phase": prefix.rstrip("_"), "delta": delta})
            replays.append({"branch": branch, "restored_cursor": 159, "committed_cursor": restored.cursor, "exact_state": exact, "delta": delta})
            del restored
        _write(artifacts / "replay_report.json", {"reloads": reloads, "replays": replays, "boundary": "Same-process same-worker reconstruction only."})
        totals = _sum_deltas([row["delta"] for row in work])
        require(totals["optimizer_updates"] == totals["backward_calls"] == 178, "GLOBAL_UPDATE_COUNTS")
        report["global_actual_work"] = {"phases": work, "totals": totals, "historical_restored_counters_counted_again": False,
            "main_presentations": 1152, "interference_presentations": 128, "additional_replay_presentations": 16,
            "encoder_main_counters": main.encoder.work_counters()}
        phase("final_source_verification")
        require(canonical(contract.input_inventory(root)) == canonical(config["inputs"]), "SOURCES_CHANGED")
        packages_after = verify_worker_packages(root)
        require(packages_before["source_files"] == packages_after["source_files"], "WHEEL_SOURCES_CHANGED")
        _write(artifacts / "installed_sources.json", {"before": packages_before, "after": packages_after})
        _write(artifacts / "loaded_sources.json", {"before": loaded_before, "after": attestor.snapshot()})
        base._deadline(started)
        report.update(status=SUCCESS_STATUS, checkpoint_reload_verified=True,
            peak_cuda_allocated_bytes=int(torch.cuda.max_memory_allocated(device)),
            peak_cuda_reserved_bytes=int(torch.cuda.max_memory_reserved(device)), elapsed_seconds=time.monotonic() - started)
        phase("delivery", main_updates=160, global_updates=178)
        return deliver(results, artifacts, report, failed=False)
    except Exception as error:
        report.update(status="TYPED_MATCHED_FAILED", elapsed_seconds=time.monotonic() - started,
            failure={"schema": FAILURE_SCHEMA, "type": type(error).__name__, "detail": str(error)[:1000]}, completed_work_phases=work)
        if main is not None:
            report["partial_main"] = {"cursor": main.cursor, "model_revision": main.model_revision,
                "counters": deepcopy(main.counters), "learner_failed": main.failed}
        if progress is not None:
            try: progress.emit("failed/" + report["phase"], completed_updates=0 if main is None else main.cursor)
            except Exception as progress_error: report["progress_write_failure"] = type(progress_error).__name__
        deliver(results, artifacts, report, failed=True)
        raise
