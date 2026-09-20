"""One practice-study job: ten passes over the course, five whole worlds held back. CUDA worker only.

Owner-approved 2026-09-18 ("Practice test"). The same machine and the same random start as the matched
study, per model seed. The question this job answers: with more practice, do the neurons get better at
questions about worlds they have NEVER practised on? Held-back questions are scored before training, after
pass 1 and after passes 2, 4, 6, 8 and 10; no held-back record, and no record that mentions a held world
anywhere or whose correct answers name one, ever enters a training batch, including the interference interval.

Adapted from `typed_matched_worker`. Differences, each deliberate:
- ten passes (`practice_contract.practice_schedule`) instead of one; the practice learner subclass carries
  the owner-approved update ceiling, everything else is the registered learner;
- per-update seal and update records go to one JSONL log per pass (the artifact contract allows at most 500
  files). Every seal is still durably written and read back BEFORE its targets are derived;
- EVERY file this worker places under ``results/`` is complete before its final name exists. The live
  evidence publisher uploads each new name once, create-only, and skips only ``*.partial``/``*.tmp``; a file
  that grew or was still being written after its first upload would make the final upload fail with
  ``EVIDENCE_DIGEST_CONFLICT`` (found by the pre-flight review, 2026-09-18). So pass logs grow in the
  staging directory outside ``results/`` and are moved in whole, and every other file is written as
  ``<name>.partial`` and renamed;
- this worker's own deadline (`practice_contract.WORKER_DEADLINE_SECONDS`) replaces the matched study's
  3,300 s one. Shared helpers from `typed_course_worker` that check the matched deadline are called with a
  fresh start time, and this worker's deadline is checked around them.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import os
from pathlib import Path
import time

from cas_meta2.typed_teaching import practice_contract as contract
from . import typed_course_worker as base
from . import typed_matched_worker as matched

CANDIDATE = contract.CANDIDATE
CONFIG_SCHEMA = contract.CONFIG_SCHEMA
RESULT_SCHEMA = "cncm.typed-practice-worker-result/0.1"
FAILURE_SCHEMA = "cncm.typed-practice-failure/0.1"
SUCCESS_STATUS = "COMPLETE_TYPED_PRACTICE_ARM"
BOUNDARY = contract.DESIGN["boundary"]
PASSES = contract.PASSES
CHECKPOINTS = contract.PASS_CHECKPOINTS
FULL = contract.FULL_COURSE_CHECKPOINTS
HELD_ONLY = tuple(n for n in CHECKPOINTS if n not in FULL)
CHECKPOINT_NAMES = ("initial", "pass_01", "prelast", "final", "retained")
EVALUATIONS = (tuple("course_p%02d" % n for n in FULL) + tuple("heldback_p%02d" % n for n in HELD_ONLY)
               + tuple("development_p%02d" % n for n in CHECKPOINTS) + ("retention_before", "retention_after"))
EXPECTED_ARTIFACTS = (
    tuple("pass_%02d_%s.jsonl" % (n, kind) for n in range(1, PASSES + 1) for kind in ("batches", "updates"))
    + ("interference_batches.jsonl", "interference_updates.jsonl")
    + tuple(phase + suffix for phase in EVALUATIONS for suffix in ("_predictions.json", "_scoring.json"))
    + tuple(name + suffix for name in CHECKPOINT_NAMES for suffix in (".pt", "_checkpoint.json"))
    + tuple(name + "_reload_predictions.json" for name in ("initial", "final", "retained"))
    + tuple("replay_%d_%s" % (n, s) for n in (1, 2) for s in ("batch.json", "update.json", "predictions.json"))
    + ("replay_report.json", "encoding_checks.json", "installed_sources.json", "loaded_sources.json",
       "protocol_material.json", "worker_report.json", "measurements.json"))
canonical, require = contract.canonical, contract.require


def _deadline(started):
    require(time.monotonic() - started < contract.WORKER_DEADLINE_SECONDS, "PRACTICE_DEADLINE_EXCEEDED")


def _publish_bytes(path, raw):
    """Create-only and whole: write ``<name>.partial`` (skipped by the publisher), fsync, then rename."""
    path = Path(path)
    partial = path.with_name(path.name + ".partial")
    require(type(raw) is bytes and not path.exists() and not path.is_symlink() and not partial.exists(),
            "PUBLISH_DESTINATION")
    with partial.open("xb") as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    require(not path.exists(), "PUBLISH_DESTINATION")
    os.replace(partial, path)
    require(path.read_bytes() == raw, "PUBLISH_READBACK")
    return {"name": path.name, "bytes": len(raw), "sha256": sha256(raw).hexdigest()}


def _publish(path, value):
    return _publish_bytes(path, canonical(value))


def _move_in(staged, path):
    """Move a completed staging file to its final name under results/, create-only."""
    staged, path = Path(staged), Path(path)
    require(staged.is_file() and not staged.is_symlink() and not path.exists(), "MOVE_IN_DESTINATION")
    raw = staged.read_bytes()
    os.replace(staged, path)
    require(path.read_bytes() == raw, "MOVE_IN_READBACK")
    return {"name": path.name, "bytes": len(raw), "sha256": sha256(raw).hexdigest()}


def _seal_predictions(path, predictions, *, phase, expected_ids):
    require([p["record_id"] for p in predictions] == expected_ids, "PREDICTION_REGISTRY_ORDER")
    return _publish(path, {"schema": "cncm.typed-course-prediction-seal/0.1", "phase": phase,
                           "predictions": predictions})


def _append(path, raw):
    """Append one complete line, durably, to a log that lives OUTSIDE results/ until it is complete."""
    require(type(raw) is bytes and raw.endswith(b"\n") and raw.count(b"\n") == 1 and not Path(path).is_symlink(),
            "APPEND_LINE")
    with Path(path).open("ab") as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())


def _stage_and_train(learner, batch, packets, seal_path, *, started):
    """Seal the batch's public predictions durably, read back, THEN derive targets and update."""
    _deadline(started)
    require(batch["cursor"] in (None, learner.cursor), "PRACTICE_BATCH_CURSOR")
    selected = [packets[key] for key in batch["record_ids"]]
    staged = learner.stage_batch(selected, batch["depth"], cursor=learner.cursor,
                                 occurrence_ids=batch["occurrence_ids"])
    pin = base._write_bytes(seal_path, staged["bytes"])
    require(pin["sha256"] == staged["sha256"], "STAGED_SEAL_DIGEST")
    from cas_meta2.typed_teaching import checker
    targets = [checker.derive_target(p["source"], p["record"]["query"]) for p in selected]
    update = learner.train_sealed_batch(seal_path, expected_sha256=pin["sha256"], target_receipts=targets)
    require(update["gradient_squared_norm"] > 0, "ZERO_TRAINING_GRADIENT")
    update["correction_identities"] = [{"record_id": key, "target_digest": target["target_digest"]}
                                       for key, target in zip(batch["record_ids"], targets)]
    return staged["bytes"], update


def _train_logged(learner, batch, packets, staging, batches_log, updates_log, *, started):
    """One update whose seal and record are appended to the staging logs; the staging seal is then removed."""
    seal_path = staging / "seal.json"
    require(not seal_path.exists(), "STAGING_SEAL_EXISTS")
    raw, update = _stage_and_train(learner, batch, packets, seal_path, started=started)
    _append(batches_log, raw)
    _append(updates_log, canonical(update))
    seal_path.unlink()
    return raw, update


def _evaluate(learner, packets, phase_name, artifacts, *, started, progress, work):
    _deadline(started)
    state = base._state(learner.torch, learner)
    counters = deepcopy(learner.counters)
    began = time.monotonic()
    progress(phase_name + "_predictions", completed_packets=0, total_packets=len(packets))
    rows = []
    for packet in packets.values():
        _deadline(started)
        rows.append(learner.predict(packet, 8))
        if len(rows) % 50 == 0 or len(rows) == len(packets):
            progress(phase_name + "_predictions", completed_packets=len(rows), total_packets=len(packets))
    path = artifacts / (phase_name + "_predictions.json")
    pin = _seal_predictions(path, rows, phase=phase_name, expected_ids=list(packets))
    # Durable public bytes precede every evaluation target. The shared scorer's own deadline is the
    # matched study's; it is handed a fresh start and this worker's deadline is checked around it.
    scored = base._score_seal(path, pin, packets, started=time.monotonic(), progress=progress)
    _deadline(started)
    scored["boundary"] = BOUNDARY
    _publish(artifacts / (phase_name + "_scoring.json"), scored)
    require(state == base._state(learner.torch, learner), "EVALUATION_CHANGED_LEARNED_STATE")
    delta = base.counter_delta(learner.counters, counters)
    require(delta["optimizer_updates"] == delta["backward_calls"] == 0, "EVALUATION_UPDATED_MODEL")
    work.append({"phase": phase_name, "delta": delta, "elapsed_seconds": time.monotonic() - began})
    return {row["record_id"]: row for row in rows}, scored


def _split_score(scored, sides):
    """{side: {correct, total}} for the named record sets."""
    out = {name: {"correct": 0, "total": 0} for name in sides}
    for row in scored["rows"]:
        for name, members in sides.items():
            if row["record_id"] in members:
                out[name]["total"] += 1
                out[name]["correct"] += 1 if row["correct"] else 0
    return out


def expected_main_delta(stats):
    updates, presentations = stats["main_updates"], stats["presentations"]
    return {"slot_forwards": stats["presentation_slots"], "core_forward_calls": stats["planned_slot_core_passes"],
            "core_forward_attempts": stats["planned_slot_core_passes"],
            "sample_core_passes": stats["planned_slot_core_passes"], "prediction_calls": presentations,
            "staged_batches": updates, "private_loss_plan_calls": presentations, "backward_attempts": updates,
            "backward_calls": updates, "optimizer_step_attempts": updates, "optimizer_updates": updates}


def deliver(results, artifacts, report, *, failed):
    artifacts = Path(artifacts)
    artifacts.mkdir(parents=True, exist_ok=True)
    if not failed:
        require(set(EXPECTED_ARTIFACTS) - {"worker_report.json", "measurements.json"}
                <= {p.name for p in artifacts.iterdir()}, "PRACTICE_REQUIRED_ARTIFACTS")
    _publish(artifacts / "worker_report.json", report)
    summary = {key: report.get(key) for key in ("job", "source_sha", "status", "runtime", "elapsed_seconds",
        "condition", "model_seed", "failure", "main_training_delta", "interference_delta", "global_actual_work",
        "checkpoint_reload_verified", "scores", "development_scores", "retention_scores", "pass_summaries",
        "initial_model_identity")}
    summary.update(learning_on_held_back_established=False, boundary=BOUNDARY)
    _publish(artifacts / "measurements.json", summary)
    entries = []
    for path in sorted(artifacts.iterdir()):
        if path.name.endswith(".partial"):
            continue
        require(path.is_file() and not path.is_symlink() and path.stat().st_size <= 64 * 1024 ** 2, "ARTIFACT_BOUND")
        raw = path.read_bytes()
        entries.append({"name": path.name, "bytes": len(raw), "sha256": sha256(raw).hexdigest()})
    require(len(entries) <= 500, "ARTIFACT_COUNT")
    _publish(artifacts / "manifest.json", {"artifacts": entries})
    result = {"schema": RESULT_SCHEMA, "job": report["job"], "artifacts": entries,
              "status": "TYPED_PRACTICE_FAILED" if failed else "TYPED_PRACTICE_DELIVERED",
              "summary": summary, "failure": report.get("failure"), "boundary": BOUNDARY}
    pin = _publish(Path(results) / "result.json", result)
    _publish_bytes(Path(results) / "result.json.sha256", (pin["sha256"] + "\n").encode("ascii"))
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
    staging = results.parent / "practice_staging"
    require(not staging.exists(), "FRESH_STAGING_DIRECTORY")
    staging.mkdir()
    report = {"schema": "cncm.typed-practice-worker-report/0.1", "candidate": CANDIDATE,
              "job": config["job"], "source_sha": config["source_sha"], "inputs": config["inputs"], "design": design,
              "condition": design["condition"], "model_seed": design["model_seed"], "boundary": BOUNDARY,
              "learning_on_held_back_established": False, "phase": "admitted"}
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
        held, trained, excluded = contract.split(frozen)
        require(held == design["held_back_record_ids"] and excluded == design["excluded_record_ids"], "HOLDOUT_IDENTITY")
        held_set, trained_set, excluded_set = set(held), set(trained), set(excluded)
        held_worlds = set(contract.held_worlds(frozen))
        held_packets = {key: packets[key] for key in packets if key in held_set}
        development_packets = contract.development_packets(development)
        retention_packets = dict(contract.retention_packets(frozen))
        retention_held = {key for key, packet in retention_packets.items()
                          if packet["record"]["source_world_id"] in held_worlds}
        batches, stats = contract.practice_schedule(frozen)
        require(canonical(stats) == canonical(design["schedule"]), "PRACTICE_SCHEDULE_IDENTITY")
        require(all(key in trained_set for b in batches for key in b["record_ids"]), "UNTRAINABLE_IN_TRAINING")
        interference = contract.interference_batches(frozen)
        require(all(key in trained_set for b in interference for key in b["record_ids"]), "UNTRAINABLE_IN_INTERFERENCE")
        representatives = base._representatives(packets)
        _publish(artifacts / "protocol_material.json", {"schedule": {"batches": batches, "stats": stats},
            "held_worlds": sorted(held_worlds), "held_back_record_ids": held, "trained_record_ids": trained,
            "excluded_record_ids": excluded, "interference_batches": interference,
            "development": development, "retention_record_ids": list(retention_packets),
            "retention_held_world_record_ids": sorted(retention_held),
            "retention_packet_digests": {key: sha256(canonical(value)).hexdigest()
                                         for key, value in retention_packets.items()}})

        from cas_meta2.typed_teaching.encoder import build_frozen_typed_encoder
        from cas_meta2.typed_teaching.practice_learner import PracticeCourseLearner
        phase("fresh_initialization")
        updates_total = stats["main_updates"] + contract.INTERFERENCE_UPDATES
        main = PracticeCourseLearner(torch, matched._framework(torch, device, design["model_seed"]),
            build_frozen_typed_encoder(torch, tokenizer, seed=design["encoder_seed"], d_model=64, device=device),
            optimizer_config=design["optimizer_config"],
            run_context={"run_id": config["job"], "course_sha256": contract.MATERIAL[contract.COURSE_PATH]["sha256"],
                         "condition": design["condition"], "source_seed": design["source_seed"]},
            limits={"max_updates": updates_total, "max_core_calls": contract.MAX_CORE_CALLS,
                    "max_wall_seconds": contract.WORKER_DEADLINE_SECONDS}, device=device)
        report["initial_model_identity"] = main.run_identity["initial_model_identity"]
        checkpoint_pins, predictions = {}, {}

        def checkpoint(name):
            phase(name + "_checkpoint", completed_updates=main.cursor)
            pin = main.export_checkpoint(staging / (name + ".pt"))
            _move_in(staging / (name + ".pt"), artifacts / (name + ".pt"))
            checkpoint_pins[name] = {**pin, "path": str(artifacts / (name + ".pt"))}
            _publish(artifacts / (name + "_checkpoint.json"), checkpoint_pins[name])

        checkpoint("initial")
        encoding = {"initial": base._encoding_checks(torch, main.encoder, packets, representatives,
            started=time.monotonic(), all_packets=True, progress=phase, phase="initial_encoding")}
        _deadline(started)
        report["scores"], report["development_scores"] = {}, []
        sides = {"held_back": held_set, "trained": trained_set, "excluded": excluded_set}

        def evaluate_at(number):
            if number in FULL:
                name = "course_p%02d" % number
                predictions[name], scored = _evaluate(main, packets, name, artifacts, started=started,
                                                      progress=phase, work=work)
                report["scores"][name] = {"correct": scored["correct"], "total": scored["total"],
                                          **_split_score(scored, sides)}
            else:
                name = "heldback_p%02d" % number
                _, scored = _evaluate(main, held_packets, name, artifacts, started=started, progress=phase, work=work)
                report["scores"][name] = {"correct": scored["correct"], "total": scored["total"],
                                          "held_back": {"correct": scored["correct"], "total": scored["total"]}}
            name = "development_p%02d" % number
            _, scored = _evaluate(main, development_packets, name, artifacts, started=started, progress=phase, work=work)
            report["development_scores"].append({"pass": number, "cursor": main.cursor,
                                                 "correct": scored["correct"], "total": scored["total"]})

        evaluate_at(0)
        main_deltas, report["pass_summaries"] = [], []
        last_seal = None
        for number in range(1, PASSES + 1):
            names = ("pass_%02d_batches.jsonl" % number, "pass_%02d_updates.jsonl" % number)
            batches_log, updates_log = staging / names[0], staging / names[1]
            batches_log.touch(exist_ok=False); updates_log.touch(exist_ok=False)
            losses, gradients = [], []
            for batch in (b for b in batches if b["pass"] == number):
                if batch["cursor"] == stats["main_updates"] - 1:
                    checkpoint("prelast")
                before = deepcopy(main.counters)
                last_seal, update = _train_logged(main, batch, packets, staging, batches_log, updates_log,
                                                  started=started)
                main_deltas.append(base.counter_delta(main.counters, before))
                losses.append(update["raw_batch_loss"]); gradients.append(update["gradient_squared_norm"])
                report["completed_main_updates"] = main.cursor
                if main.cursor % 10 == 0:
                    phase("main_training", completed_main_updates=main.cursor, total_main_updates=stats["main_updates"],
                          current_pass=number)
            _move_in(batches_log, artifacts / names[0])
            _move_in(updates_log, artifacts / names[1])
            report["pass_summaries"].append({"pass": number, "updates": len(losses), "cursor_end": main.cursor,
                "mean_raw_batch_loss": sum(losses) / len(losses), "first_raw_batch_loss": losses[0],
                "last_raw_batch_loss": losses[-1], "mean_gradient_squared_norm": sum(gradients) / len(gradients)})
            if number < PASSES:
                base._partial_checkpoint(main, results, main.cursor)
            if number == 1:
                checkpoint("pass_01")
            if number == PASSES:
                checkpoint("final")
            if number in CHECKPOINTS:
                evaluate_at(number)
        require(main.cursor == stats["main_updates"] and not any(staging.iterdir()), "PRACTICE_MAIN_INCOMPLETE")
        report["main_training_delta"] = matched._sum_deltas(main_deltas)
        require(canonical(report["main_training_delta"]) == canonical(expected_main_delta(stats)), "MAIN_TRAINING_COUNTERS")
        work.append({"phase": "main_training", "delta": report["main_training_delta"]})
        require(checkpoint_pins["initial"]["metadata"]["model_state_identity"]
                != checkpoint_pins["final"]["metadata"]["model_state_identity"], "TRAINABLE_CORE_UNCHANGED")

        retention_sides = {"held_world": retention_held, "trained_world": set(retention_packets) - retention_held}
        _, before_score = _evaluate(main, retention_packets, "retention_before", artifacts, started=started,
                                    progress=phase, work=work)
        interference_deltas = []
        names = ("interference_batches.jsonl", "interference_updates.jsonl")
        batches_log, updates_log = staging / names[0], staging / names[1]
        batches_log.touch(exist_ok=False); updates_log.touch(exist_ok=False)
        for batch in interference:
            before = deepcopy(main.counters)
            _train_logged(main, batch, packets, staging, batches_log, updates_log, started=started)
            interference_deltas.append(base.counter_delta(main.counters, before))
            phase("interference_training", completed_updates=main.cursor, total_updates=updates_total)
        _move_in(batches_log, artifacts / names[0])
        _move_in(updates_log, artifacts / names[1])
        report["interference_delta"] = matched._sum_deltas(interference_deltas)
        require(report["interference_delta"]["optimizer_updates"] == contract.INTERFERENCE_UPDATES
                and report["interference_delta"]["prediction_calls"]
                == contract.INTERFERENCE_UPDATES * contract.INTERFERENCE_BATCH, "INTERFERENCE_COUNTS")
        work.append({"phase": "interference_training", "delta": report["interference_delta"]})
        checkpoint("retained")
        retained_predictions, after_score = _evaluate(main, retention_packets, "retention_after", artifacts,
                                                      started=started, progress=phase, work=work)
        report["retention_scores"] = {"before": {k: before_score[k] for k in ("correct", "total")},
            "after": {k: after_score[k] for k in ("correct", "total")},
            "before_by_side": _split_score(before_score, retention_sides),
            "after_by_side": _split_score(after_score, retention_sides),
            "starting_competence_met": 2 * before_score["correct"] >= before_score["total"]}
        encoding["final"] = base._encoding_checks(torch, main.encoder, packets, representatives,
            started=time.monotonic(), all_packets=False, progress=phase, phase="final_encoding")
        _deadline(started)
        _publish(artifacts / "encoding_checks.json", encoding)

        reloads, replays = [], []
        final_name = "course_p%02d" % PASSES
        for name, expected_name in (("initial", "course_p00"), ("final", final_name), ("retained", None)):
            _deadline(started)
            phase(name + "_reconstruction")
            pin = checkpoint_pins[name]
            restored = PracticeCourseLearner.restore_checkpoint(torch, matched._framework(torch, device, design["model_seed"]),
                path=artifacts / (name + ".pt"), expected_sha256=pin["sha256"],
                expected_run_identity_digest=main.run_identity_digest, device=device)
            exact = base._check_state(torch, restored, pin)
            before = deepcopy(restored.counters)
            selected = list(retention_packets)[:8] if name == "retained" else list(representatives.values())
            source_packets = retention_packets if name == "retained" else packets
            expected = retained_predictions if name == "retained" else predictions[expected_name]
            rows = [restored.predict(source_packets[key], 8) for key in selected]
            require(all(canonical(row) == canonical(expected[row["record_id"]]) for row in rows), "RELOAD_PREDICTION_MISMATCH")
            _seal_predictions(artifacts / (name + "_reload_predictions.json"), rows, phase=name + "_reload",
                              expected_ids=selected)
            delta = base.counter_delta(restored.counters, before)
            work.append({"phase": name + "_reload", "delta": delta})
            reloads.append({"phase": name, "checkpoint_sha256": pin["sha256"], "exact_state": exact,
                            "prediction_ids": selected, "delta": delta})
            del restored
        for branch in (1, 2):
            _deadline(started)
            phase("replay_%d" % branch)
            pin = checkpoint_pins["prelast"]
            restored = PracticeCourseLearner.restore_checkpoint(torch, matched._framework(torch, device, design["model_seed"]),
                path=artifacts / "prelast.pt", expected_sha256=pin["sha256"],
                expected_run_identity_digest=main.run_identity_digest, device=device)
            base._check_state(torch, restored, pin)
            before = deepcopy(restored.counters)
            staged_seal = staging / ("replay_%d_batch.json" % branch)
            raw, update = _stage_and_train(restored, batches[-1], packets, staged_seal, started=started)
            require(raw == last_seal, "REPLAY_PREUPDATE_MISMATCH")
            _move_in(staged_seal, artifacts / ("replay_%d_batch.json" % branch))
            _publish(artifacts / ("replay_%d_update.json" % branch), update)
            exact = base._check_state(torch, restored, checkpoint_pins["final"])
            rows = [restored.predict(packets[key], 8) for key in representatives.values()]
            require(all(canonical(row) == canonical(predictions[final_name][row["record_id"]]) for row in rows),
                    "REPLAY_FINAL_MISMATCH")
            _seal_predictions(artifacts / ("replay_%d_predictions.json" % branch), rows, phase="replay_%d" % branch,
                              expected_ids=list(representatives.values()))
            delta = base.counter_delta(restored.counters, before)
            require(delta["optimizer_updates"] == delta["backward_calls"] == 1, "REPLAY_COUNTS")
            work.append({"phase": "replay_%d" % branch, "delta": delta})
            replays.append({"branch": branch, "restored_cursor": stats["main_updates"] - 1,
                            "committed_cursor": restored.cursor, "exact_state": exact, "delta": delta})
            del restored
        _publish(artifacts / "replay_report.json", {"reloads": reloads, "replays": replays,
                                                     "boundary": "Same-process same-worker reconstruction only."})
        totals = matched._sum_deltas([row["delta"] for row in work])
        expected_updates = stats["main_updates"] + contract.INTERFERENCE_UPDATES + contract.REPLAY_UPDATES
        require(totals["optimizer_updates"] == totals["backward_calls"] == expected_updates, "GLOBAL_UPDATE_COUNTS")
        report["global_actual_work"] = {"phases": work, "totals": totals,
            "historical_restored_counters_counted_again": False,
            "main_presentations": stats["presentations"],
            "interference_presentations": contract.INTERFERENCE_UPDATES * contract.INTERFERENCE_BATCH,
            "encoder_main_counters": main.encoder.work_counters()}
        phase("final_source_verification")
        require(canonical(contract.input_inventory(root)) == canonical(config["inputs"]), "SOURCES_CHANGED")
        packages_after = verify_worker_packages(root)
        require(packages_before["source_files"] == packages_after["source_files"], "WHEEL_SOURCES_CHANGED")
        _publish(artifacts / "installed_sources.json", {"before": packages_before, "after": packages_after})
        _publish(artifacts / "loaded_sources.json", {"before": loaded_before, "after": attestor.snapshot()})
        _deadline(started)
        report.update(status=SUCCESS_STATUS, checkpoint_reload_verified=True,
                      peak_cuda_allocated_bytes=int(torch.cuda.max_memory_allocated(device)),
                      peak_cuda_reserved_bytes=int(torch.cuda.max_memory_reserved(device)),
                      elapsed_seconds=time.monotonic() - started)
        phase("delivery", main_updates=stats["main_updates"], global_updates=expected_updates)
        return deliver(results, artifacts, report, failed=False)
    except Exception as error:
        # Keep whatever was still in staging (a partly written pass log, a replay seal): move it into
        # artifacts under a name that marks it as a failure leftover, so the publisher uploads it.
        salvaged = []
        try:
            if staging.exists():
                for leftover in sorted(staging.iterdir()):
                    if leftover.is_file() and leftover.stat().st_size > 0:
                        _move_in(leftover, artifacts / ("failed_" + leftover.name))
                        salvaged.append(leftover.name)
        except Exception as salvage_error:                      # noqa: BLE001 - never mask the failure
            report["staging_salvage_failure"] = type(salvage_error).__name__
        report["staging_salvaged"] = salvaged
        report.update(status="TYPED_PRACTICE_FAILED", elapsed_seconds=time.monotonic() - started,
                      failure={"schema": FAILURE_SCHEMA, "type": type(error).__name__, "detail": str(error)[:1000]},
                      completed_work_phases=work)
        if main is not None:
            report["partial_main"] = {"cursor": main.cursor, "model_revision": main.model_revision,
                                      "counters": deepcopy(main.counters), "learner_failed": main.failed}
        if progress is not None:
            try:
                progress.emit("failed/" + report["phase"], completed_updates=0 if main is None else main.cursor)
            except Exception as progress_error:
                report["progress_write_failure"] = type(progress_error).__name__
        deliver(results, artifacts, report, failed=True)
        raise
