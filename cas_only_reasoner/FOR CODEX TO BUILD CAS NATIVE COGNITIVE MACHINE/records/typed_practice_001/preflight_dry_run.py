"""Pre-flight: drive the practice worker end to end with a NON-NEURAL stand-in learner. $0, no torch, no GPU.

Everything the worker does is real -- config validation, the ten-pass schedule, the held-back split, seal
before targets, the per-pass logs, every evaluation, checkpoints, partial checkpoints, reloads, replays,
delivery and the artifact contract -- EXCEPT the neural parts, which are replaced:

- the learner is a deterministic stand-in: its "weights" are a hash chain over the sealed batches, and its
  counters follow the real learner's counting (slots x depth per packet, real `slots.compile_slots` counts);
- torch/CUDA, the frozen encoder, the framework, the source attestor and the wheel check are stand-ins;
- `checker.check_answer` is a fast stand-in (the stand-in answers are not real answers); the real
  `checker.derive_target` is used, memoised by record id.

Then the real gate reader runs on the three dry-run receipts. Expected: integrity I1, I2 and I4 PASS, and
I3 FAILS (the stand-in's start is not the matched study's start), so the label is VOID. Anything else is a
bug found for $0.

    python preflight_dry_run.py SCRATCH_DIR
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import os
import sys
import threading
import time
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for extra in (ROOT, ROOT / 'research/CAS_META_2_COMPOSITION', HERE):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

from cas_meta2.typed_teaching import practice_contract as contract, practice_learner, slots, checker, encoder
from cas_meta2.teaching_cycle import gpu_adapter
from cncm import typed_practice_worker as worker, typed_matched_worker as matched_worker, typed_course_worker as base
from cncm import rpa_learning_worker
import evaluate_gates

COUNTERS = ("core_forward_attempts", "core_forward_calls", "sample_core_passes", "slot_forwards", "prediction_calls",
            "staged_batches", "backward_attempts", "backward_calls", "optimizer_step_attempts", "optimizer_updates",
            "private_loss_plan_calls")


def h(text):
    return sha256(text.encode()).hexdigest()


def enc(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


class StandInLearner:
    slot_counts = {}

    def __init__(self, torch, framework, encoder_, *, optimizer_config, run_context, limits, device):
        self.limits = practice_learner.validate_practice_limits(limits)
        self.torch, self.encoder, self.module = torch, encoder_, SimpleNamespace(training=True)
        self.cursor = self.model_revision = 0
        self.weights = h("start:" + str(run_context["run_id"]))
        self.counters = {k: 0 for k in COUNTERS}
        self.run_identity = {"context": run_context, "limits": self.limits, "initial_model_identity": self.weights}
        self.run_identity_digest = h(enc(self.run_identity))
        self._pending, self.failed = None, False

    def _slots(self, packet):
        key = packet["record"]["record_id"]
        if key not in self.slot_counts:
            self.slot_counts[key] = len(slots.compile_slots(packet)["slots"])
        return self.slot_counts[key]

    def _forward(self, packet, depth):
        n = self._slots(packet)
        for k in ("core_forward_attempts", "core_forward_calls", "sample_core_passes"):
            self.counters[k] += n * depth
        self.counters["slot_forwards"] += n
        self.counters["prediction_calls"] += 1
        key = packet["record"]["record_id"]
        body = {"record_id": key, "depth": depth, "model_revision": self.model_revision,
                "run_context_digest": self.run_identity_digest, "answer": {"stand_in": h(self.weights + key)[:16]}}
        return {**body, "prediction_id": "stand-in-" + h(enc(body))}

    def predict(self, packet, depth):
        assert self._pending is None
        return self._forward(packet, depth)

    def stage_batch(self, packets, depth, *, cursor, occurrence_ids):
        assert self._pending is None and cursor == self.cursor
        assert self.counters["optimizer_updates"] < self.limits["max_updates"]
        public = {"schema": "stand-in-batch", "cursor": cursor, "model_revision": self.model_revision,
                  "run_identity_digest": self.run_identity_digest, "occurrence_ids": list(occurrence_ids),
                  "predictions": [self._forward(p, depth) for p in packets]}
        public["batch_id"] = "stand-in-batch-" + h(enc(public))
        raw = (enc(public) + "\n").encode()
        self._pending = {"raw": raw, "n": len(packets)}
        self.counters["staged_batches"] += 1
        return {"public": public, "bytes": raw, "sha256": sha256(raw).hexdigest()}

    def train_sealed_batch(self, path, *, expected_sha256, target_receipts):
        raw = Path(path).read_bytes()
        assert self._pending is not None and raw == self._pending["raw"] and sha256(raw).hexdigest() == expected_sha256
        assert len(target_receipts) == self._pending["n"] and all("target_digest" in t for t in target_receipts)
        self.counters["private_loss_plan_calls"] += self._pending["n"]
        for k in ("backward_attempts", "backward_calls", "optimizer_step_attempts", "optimizer_updates"):
            self.counters[k] += 1
        self.weights = h(self.weights + sha256(raw).hexdigest())
        self.cursor += 1; self.model_revision += 1; self._pending = None
        return {"schema": "stand-in-update", "cursor_committed": self.cursor, "raw_batch_loss": 1.0 / self.cursor,
                "gradient_squared_norm": 1.0, "counters": dict(self.counters), "tasks": []}

    def state(self):
        return {"model_state_identity": self.weights, "optimizer_state_identity": h("opt" + self.weights),
                "rng_state_identity": h("rng" + self.weights), "encoder_state_identity": "stand-in-encoder"}

    def export_checkpoint(self, path):
        assert self._pending is None
        payload = {"weights": self.weights, "cursor": self.cursor, "model_revision": self.model_revision,
                   "counters": self.counters, "run_identity": self.run_identity,
                   "run_identity_digest": self.run_identity_digest, "limits": self.limits}
        raw = (enc(payload) + "\n").encode()
        with Path(path).open("xb") as stream:
            stream.write(raw)
        metadata = {"run_identity": self.run_identity, "run_identity_digest": self.run_identity_digest,
                    "model_revision": self.model_revision, "cursor": self.cursor, "counters": dict(self.counters),
                    "elapsed_seconds": 0.0, "training_mode": True, **self.state()}
        return {"path": str(Path(path).resolve()), "sha256": sha256(raw).hexdigest(), "bytes": len(raw),
                "run_identity_digest": self.run_identity_digest, "metadata": metadata}

    @classmethod
    def restore_checkpoint(cls, torch, framework, *, path, expected_sha256, expected_run_identity_digest, device):
        raw = Path(path).read_bytes()
        assert sha256(raw).hexdigest() == expected_sha256
        payload = json.loads(raw)
        assert payload["run_identity_digest"] == expected_run_identity_digest
        obj = cls.__new__(cls)
        obj.torch, obj.encoder, obj.module = torch, SimpleNamespace(work_counters=lambda: {}), SimpleNamespace(training=True)
        obj.weights, obj.cursor, obj.model_revision = payload["weights"], payload["cursor"], payload["model_revision"]
        obj.counters, obj.limits = dict(payload["counters"]), dict(payload["limits"])
        obj.run_identity, obj.run_identity_digest = payload["run_identity"], payload["run_identity_digest"]
        obj._pending, obj.failed = None, False
        return obj


def install_stand_ins():
    torch = SimpleNamespace(__version__="2.11.0+cu128", version=SimpleNamespace(cuda="12.8"),
        cuda=SimpleNamespace(reset_peak_memory_stats=lambda d: None, get_device_name=lambda d: "NVIDIA RTX PRO 4500 (stand-in)",
                             max_memory_allocated=lambda d: 0, max_memory_reserved=lambda d: 0),
        use_deterministic_algorithms=lambda flag: None,
        backends=SimpleNamespace(cuda=SimpleNamespace(matmul=SimpleNamespace(allow_tf32=True)),
                                 cudnn=SimpleNamespace(allow_tf32=True)))
    gpu_adapter._cuda = lambda: (torch, "cuda:0")
    rpa_learning_worker.verify_worker_packages = lambda root: {"source_files": ["stand-in"]}
    encoder.build_frozen_typed_encoder = lambda *a, **k: SimpleNamespace(work_counters=lambda: {})
    matched_worker._framework = lambda torch_, device, seed: SimpleNamespace(module=None, seed=seed)
    practice_learner.PracticeCourseLearner = StandInLearner
    base._state = lambda torch_, learner: learner.state()
    base._encoding_checks = lambda *a, **k: {"stand_in": True}
    targets = {}
    real_derive = checker.derive_target
    def derive(source, query):
        key = query["query_id"] + ":" + source["focus_world_id"]
        if key not in targets:
            targets[key] = real_derive(source, query)
        return targets[key]
    checker.derive_target = derive
    checker.check_answer = lambda source, query, answer: {"correct": int(answer["stand_in"][:2], 16) % 3 == 0}


class CreateOnlyPublisher:
    """The live evidence publisher's rule, at $0: each new name under results/ is stored once and never
    replaced; names ending .partial/.tmp are skipped; a stored name whose bytes later differ is a conflict
    (on AWS: EVIDENCE_DIGEST_CONFLICT, which fails the final upload). Scans several times a second."""

    def __init__(self, results):
        self.results, self.store, self.conflicts, self.scans = Path(results), {}, [], 0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)

    def scan(self):
        self.scans += 1
        for path in sorted(self.results.rglob("*")):
            try:
                if not path.is_file() or path.name.endswith((".partial", ".tmp")):
                    continue
                digest = sha256(path.read_bytes()).hexdigest()
            except OSError:
                continue
            key = path.relative_to(self.results).as_posix()
            if key not in self.store:
                self.store[key] = digest
            elif self.store[key] != digest and key not in self.conflicts:
                self.conflicts.append(key)

    def _loop(self):
        while not self._stop.is_set():
            self.scan()
            time.sleep(0.1)

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self._stop.set(); self._thread.join(); self.scan()


WRITE_VIOLATIONS, ACTIVE_RESULTS = [], []


def _write_audit(event, args):
    """Record every write-mode open of a file under an active results/ whose name is not *.partial."""
    if event != "open" or not ACTIVE_RESULTS:
        return
    path, mode, flags = (list(args) + [None, None, None])[:3]
    if not isinstance(path, (str, bytes)) and not hasattr(path, "__fspath__"):
        return
    text = os.fsdecode(os.fspath(path))
    writing = (isinstance(mode, str) and any(c in mode for c in "wxa+")) or (
        mode is None and isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT))
    if writing and text.startswith(ACTIVE_RESULTS[0]) and not text.endswith(".partial"):
        WRITE_VIOLATIONS.append(text)


def main(scratch):
    scratch = Path(scratch).resolve()
    scratch.mkdir(parents=True, exist_ok=False)
    install_stand_ins()
    sys.addaudithook(_write_audit)
    source_sha = "d" * 40
    jobs, timings, publishing = [], {}, {}
    for seed in contract.MODEL_SEEDS:
        job = "cas-meta2-tprac-20260918000000-dddddddd-m-%d" % seed
        receipt = scratch / ("receipt_%d" % seed)
        results = receipt / "collected/results"
        results.mkdir(parents=True)
        config = contract.make_config(ROOT, source_sha=source_sha, job=job, bucket=job + "-807562639912", model_seed=seed)
        began = time.monotonic()
        ACTIVE_RESULTS[:] = [str(results.resolve())]
        before = len(WRITE_VIOLATIONS)
        with CreateOnlyPublisher(results) as publisher:
            result = worker.run(config, ROOT, results, results / "artifacts",
                                attestor=SimpleNamespace(snapshot=lambda: {"stand_in": True}))
        ACTIVE_RESULTS[:] = []
        timings[seed] = round(time.monotonic() - began, 1)
        staging = results.parent / "practice_staging"
        publishing[seed] = {"scans": publisher.scans, "files": len(publisher.store), "conflicts": publisher.conflicts,
                            "direct_writes_under_results": WRITE_VIOLATIONS[before:],
                            "staging_left": sorted(p.name for p in staging.iterdir()) if staging.exists() else [],
                            "partial_left": sorted(str(p.name) for p in results.rglob("*.partial"))}
        assert result["status"] == "TYPED_PRACTICE_DELIVERED", result.get("failure")
        (receipt / "result.json").write_text(json.dumps({"completed_deliverable": True, "cleanup": {"complete": True}}))
        jobs.append({"model_seed": seed, "receipt_dir": str(receipt), "job": job})
        print(json.dumps({"dry_run_seed_delivered": seed, "seconds": timings[seed]}), flush=True)
    study = scratch / "study.json"
    study.write_text(json.dumps({"jobs": jobs}))
    reading = evaluate_gates.evaluate(study)
    failures = reading["gates"]["integrity"]["failures"]
    expected = ["I3:%d" % seed for seed in contract.MODEL_SEEDS]
    clean = all(not row["conflicts"] and row["files"] > 0 and not row["direct_writes_under_results"]
                and not row["staging_left"] and not row["partial_left"] for row in publishing.values())
    verdict = "PREFLIGHT_PASS" if (failures == expected and reading["label"] == "VOID" and clean) else "PREFLIGHT_FAIL"
    summary = {"schema": "cncm.typed-practice-preflight-dry-run/0.2", "verdict": verdict,
               "expected_integrity_failures": expected, "observed_integrity_failures": failures,
               "label_on_stand_in": reading["label"], "worker_seconds_per_seed": timings,
               "create_only_publisher_simulation": publishing,
               "main_updates_per_seed": contract.practice_schedule(contract.load_material(ROOT)[0])[1]["main_updates"],
               "gate_population": {k: reading[k] for k in ("held_questions", "eligible_questions", "shortcut_questions",
                                                            "held_records", "trained_records", "excluded_records")},
               "boundary": "Stand-in learner, torch, encoder, framework, attestor and answer checker. Proves control "
                           "flow, counts, artifacts, logs, reloads, replays, delivery and the gate reader; proves "
                           "nothing about numerics or AWS packaging."}
    print(json.dumps(summary, indent=1), flush=True)
    return summary


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: preflight_dry_run.py SCRATCH_DIR")
    outcome = main(sys.argv[1])
    raise SystemExit(0 if outcome["verdict"] == "PREFLIGHT_PASS" else 1)
