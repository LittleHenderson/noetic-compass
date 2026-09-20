"""Pure orchestration for candidate teaching; the supplied learner owns CUDA.

No held-out cases enter this module. Synthetic learners remain simulated.
Durable intents/results expose crash tails; loading an older checkpoint never
silently replays uncommitted work or reverses its compute cost.
"""
from copy import deepcopy
from dataclasses import asdict
from hashlib import sha256
import math
from pathlib import Path
import random
import re
import time

from ..codec import canonical_sha256
from .controller import Allocation, ExposureLedger, TeachingError
from .guided_application import make_cycle, make_public, validate_cycle
from .journal import (CheckpointJournal, RECEIPT_BYTES, _encode, _hash_file,
                      _read_json, _safe_path, _sync_directory, _write_new)

SCHEMA = "cas-teaching-session/1"
ARMS = ("cas.aligned", "cas.ordinary", "generic.aligned", "generic.ordinary")
EVENT_BYTE_LIMIT = 1024 * 1024
EVENT_TOTAL_BYTE_LIMIT = 64 * 1024 * 1024


class SessionError(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise SessionError("TEACHING_SESSION:" + reason)


def summarize_compute(batches, execution_mode):
    """Aggregate measured CUDA receipts only; missing measurements are not zeros."""
    base = {"schema": "cas-teaching-arm-compute/1", "recorded_steps": len(batches),
            "measured_steps": 0, "status": "UNAVAILABLE", "totals": None,
            "provider_identity_proved": False,
            "boundary": "Receipt measurements require retained CUDA/provider evidence. Position pairs are not FLOPs; "
                        "step time excludes admission, caller journal writes, checkpoint selection and provider overhead."}
    if execution_mode != "cuda" or not batches:
        return {**base, "reason": "SIMULATED_OR_NO_CUDA_STEP_METRICS"}
    accepted = []
    for batch in batches:
        receipt = batch.get("receipt", {})
        metrics = receipt.get("compute_metrics")
        if type(metrics) is not dict or receipt.get("execution_mode") != "cuda":
            continue
        names = ("input_tokens_unpadded", "input_tokens_padded", "input_padding_tokens",
                 "padded_input_length", "padded_attention_position_pairs")
        if (metrics.get("schema") != "cas-teaching-step-compute/1" or metrics.get("status") != "MEASURED_CUDA"
                or not all(type(metrics.get(name)) is int and metrics[name] >= 0 for name in names)):
            continue
        size, length = receipt.get("batch_size"), metrics["padded_input_length"]
        seconds = metrics.get("step_wall_seconds")
        if (type(size) is not int or not 1 <= size <= 256 or not 1 <= length <= 512
                or metrics["input_tokens_padded"] != size * length
                or not size <= metrics["input_tokens_unpadded"] <= metrics["input_tokens_padded"]
                or metrics["input_padding_tokens"] != metrics["input_tokens_padded"] - metrics["input_tokens_unpadded"]
                or metrics["padded_attention_position_pairs"] != size * length * length
                or type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds < 0
                or any(type(metrics.get(name)) is not str or not metrics[name]
                       for name in ("step_wall_boundary", "attention_proxy_boundary"))):
            continue
        accepted.append(metrics)
    base["measured_steps"] = len(accepted)
    if len(accepted) != len(batches):
        return {**base, "reason": "MISSING_OR_INVALID_CUDA_STEP_METRICS"}
    boundaries = {(row["step_wall_boundary"], row["attention_proxy_boundary"]) for row in accepted}
    if len(boundaries) != 1:
        return {**base, "reason": "INCONSISTENT_MEASUREMENT_BOUNDARIES"}
    total_names = ("input_tokens_unpadded", "input_tokens_padded", "input_padding_tokens",
                   "padded_attention_position_pairs", "step_wall_seconds")
    totals = {name: sum(row[name] for row in accepted) for name in total_names}
    if not math.isfinite(totals["step_wall_seconds"]):
        return {**base, "reason": "NONFINITE_CUMULATIVE_STEP_TIME"}
    totals["maximum_padded_input_length"] = max(row["padded_input_length"] for row in accepted)
    return {**base, "status": "MEASURED_CUDA", "totals": totals,
            "step_wall_boundary": accepted[0]["step_wall_boundary"],
            "attention_proxy_boundary": accepted[0]["attention_proxy_boundary"]}


class TrainingSession:
    def __init__(self, learner, train_cases, development_cases, curriculum, root,
                 source_sha256, allocation=None, seed=7, execution_mode="cuda"):
        self.learner, self.allocation = learner, allocation or Allocation()
        self.allocation.validate()
        require(type(seed) is int and 0 <= seed < 2**63, "SEED_INVALID")
        require(type(train_cases) is list and train_cases
                and self.allocation.maximum_cycles % len(train_cases) == 0, "WHOLE_EPOCH_ALLOCATION_REQUIRED")
        self.train_cases = deepcopy(sorted(train_cases, key=lambda c: c["family_id"]))
        self.development_cases = deepcopy(development_cases)
        self.by_family = {case["family_id"]: case for case in self.train_cases}
        self.curriculum, self.seed, self.execution_mode = curriculum, seed, execution_mode
        self.max_epochs = self.allocation.maximum_cycles // len(self.train_cases)
        state = learner.state_identity()
        self.run_id, self.scope_names = state["run_id"], state["scope_names"]
        training_sha = canonical_sha256(self.train_cases)
        require(state.get("training_cases_sha256") == training_sha, "LEARNER_TRAINING_PLAN_MISMATCH")
        self.identity = {"source_sha256": source_sha256, "schema": SCHEMA, "curriculum": curriculum,
            "allocation": asdict(self.allocation), "seed": seed, "execution_mode": execution_mode,
            "training_cases_sha256": training_sha, "development_cases_sha256": canonical_sha256(self.development_cases),
            "scope_sha256": canonical_sha256(sorted(self.scope_names)),
            "record_registry_sha256": state["record_registry_sha256"]}
        self.root = Path(root).absolute()
        _safe_path(self.root)
        require(self.root.parent.is_dir(), "SESSION_PARENT_REQUIRED")
        self.root.mkdir(exist_ok=True)
        require({p.name for p in self.root.iterdir()} <= {"journal", "events"}, "UNEXPECTED_SESSION_FILE")
        self.events = self.root / "events"
        _safe_path(self.events)
        self.events.mkdir(exist_ok=True)
        self.journal = CheckpointJournal(self.root / "journal", self.run_id, self.identity)
        self.cursor = {"epoch": 0, "batch": 0, "stage": 0}
        self.batch_size, self.pending_development = None, False
        self.history, self.event_count, self.best, self.event_bytes = [], 0, None, 0
        self.initial_state = state["checkpoint_sha256"]
        latest = self.journal.latest()
        if latest is None:
            require(not list(self.events.iterdir()) and not self.journal.incomplete_staging,
                    "NO_COMMITTED_SESSION_STATE")
            self.ledger = self._new_ledger(self.initial_state)
            self._save("initial")
        else:
            self._resume(latest)

    def _new_ledger(self, initial):
        return ExposureLedger(run_id=self.run_id, curriculum=self.curriculum, scope_names=self.scope_names,
            initial_checkpoint=initial, train_cases=self.train_cases, development_cases=self.development_cases,
            allocation=self.allocation, execution_mode=self.execution_mode)

    def _order(self, epoch):
        cases = list(self.train_cases)
        random.Random(self.seed + epoch).shuffle(cases)
        return cases

    def _records(self, cursor, assistance):
        require(self.batch_size is not None, "BATCH_SIZE_NOT_BOUND")
        start = cursor["batch"] * self.batch_size
        cases = self._order(cursor["epoch"])[start:start + self.batch_size]
        require(bool(cases) and 0 <= cursor["stage"] < 7, "CURSOR_INVALID")
        records, cycle_ids = [], []
        for case in cases:
            cycle = make_cycle(case, assistance, self.curriculum)
            validate_cycle(case, cycle)
            records.append(cycle[cursor["stage"]])
            cycle_ids.append(f"epoch-{cursor['epoch']:04d}:{case['family_id']}")
        return cycle_ids, records

    def _advance_cursor(self):
        self.cursor["stage"] += 1
        if self.cursor["stage"] == 7:
            self.cursor["stage"] = 0
            self.cursor["batch"] += 1
            if self.cursor["batch"] * self.batch_size >= len(self.train_cases):
                self.cursor = {"epoch": self.cursor["epoch"] + 1, "batch": 0, "stage": 0}
                self.pending_development = True

    def _event_path(self, sequence, kind):
        return self.events / f"step-{sequence:08d}.{kind}.json"

    def _event_write(self, sequence, kind, payload):
        raw = _encode(payload)
        require(len(raw) <= EVENT_BYTE_LIMIT, "EVENT_BYTE_LIMIT")
        require(self.event_bytes + len(raw) <= EVENT_TOTAL_BYTE_LIMIT, "EVENT_TOTAL_BYTE_LIMIT")
        path = self._event_path(sequence, kind)
        _write_new(path, raw)
        _sync_directory(self.events)
        self.event_bytes += len(raw)
        return sha256(raw).hexdigest()

    def _read_step(self, sequence, reference):
        intent, ih = _read_json(self._event_path(sequence, "intent"), EVENT_BYTE_LIMIT)
        result, rh = _read_json(self._event_path(sequence, "result"), EVENT_BYTE_LIMIT)
        require(ih == reference["intent_sha256"] and rh == reference["result_sha256"], "EVENT_DIGEST_MISMATCH")
        require(result["intent_sha256"] == ih and result["sequence"] == sequence, "RESULT_INTENT_MISMATCH")
        require(intent["sequence"] == sequence and intent["run_id"] == self.run_id
                and intent["session_identity_sha256"] == canonical_sha256(self.identity), "EVENT_IDENTITY_MISMATCH")
        return intent, result["receipt"]

    def _verify_tail(self, committed_count):
        actual = set()
        event_bytes = 0
        for path in self.events.iterdir():
            _safe_path(path)
            match = re.fullmatch(r"step-([0-9]{8})\.(intent|result)\.json", path.name)
            require(match is not None and path.is_file(), "UNEXPECTED_EVENT_FILE")
            sequence = int(match[1])
            require(sequence <= committed_count, "UNCOMMITTED_TEACHING_TAIL")
            event_bytes += path.stat().st_size
            actual.add((sequence, match[2]))
        expected = {(sequence, kind) for sequence in range(1, committed_count + 1) for kind in ("intent", "result")}
        require(actual == expected, "COMMITTED_EVENT_HISTORY_INCOMPLETE")
        require(event_bytes <= EVENT_TOTAL_BYTE_LIMIT, "EVENT_TOTAL_BYTE_LIMIT")
        self.event_bytes = event_bytes

    def _resume(self, latest):
        metadata = latest["metadata"]
        require(metadata.get("schema") == SCHEMA and metadata.get("identity") == self.identity,
                "SESSION_IDENTITY_MISMATCH")
        count = metadata.get("event_count")
        require(type(count) is int and count >= 0, "EVENT_COUNT_INVALID")
        self._verify_tail(count)  # Before restoring anything or invoking the learner.
        self.initial_state = metadata["initial_state_sha256"]
        self.ledger = self._new_ledger(self.initial_state)
        self.batch_size = metadata["batch_size"]
        if count:
            require(type(self.batch_size) is int and 1 <= self.batch_size <= 256, "BATCH_SIZE_INVALID")
        for entry in metadata["history"]:
            if entry["kind"] == "batch":
                sequence = self.event_count + 1
                intent, receipt = self._read_step(sequence, entry)
                require(intent["cursor"] == self.cursor, "REPLAY_CURSOR_MISMATCH")
                ids, records = self._records(self.cursor, intent["assistance"])
                require(intent["cycle_ids"] == ids and intent["record_sha256"] == canonical_sha256(records),
                        "REPLAY_LESSON_MISMATCH")
                self.ledger.record_batch(ids, records, receipt)
                self.event_count += 1
                self._advance_cursor()
            elif entry["kind"] == "development":
                require(entry["event_count"] == self.event_count and self.pending_development,
                        "DEVELOPMENT_REPLAY_ORDER_INVALID")
                if entry["eligible"]:
                    self.ledger.observe_development(split="development", predictions=entry["predictions"],
                        input_sha256=entry["input_sha256"], checkpoint_sha256=entry["checkpoint_sha256"])
                    actual = self.ledger.development[-1]
                    require(entry["correct"] == actual["correct"] and entry["attempted"] == actual["attempted"],
                            "DEVELOPMENT_SCORE_MISMATCH")
                self.pending_development = False
            else:
                raise SessionError("TEACHING_SESSION:HISTORY_KIND_INVALID")
            self.history.append(deepcopy(entry))
        require(self.event_count == count and self.cursor == metadata["cursor"]
                and self.pending_development == metadata["pending_development"], "REPLAY_STATE_MISMATCH")
        require(self.ledger.checkpoint == metadata["model_state_sha256"], "LEDGER_MODEL_BINDING_MISMATCH")
        self.best = metadata["best"]
        eligible = [row for row in self.history if row["kind"] == "development" and row["eligible"]]
        if eligible:
            winner = max(eligible, key=lambda row: row["correct"])  # Stable: earliest wins ties.
            require(type(self.best) is dict and all(self.best.get(key) == winner[key]
                    for key in ("correct", "attempted", "epoch"))
                    and self.best.get("state_sha256") == winner["checkpoint_sha256"], "CHECKPOINT_SELECTION_MISMATCH")
            self._reference(self.best["transaction"], self.best["state_sha256"])
        else:
            require(self.best is None, "INELIGIBLE_CHECKPOINT_SELECTED")
        self.learner.restore_checkpoint(latest["checkpoint_path"], latest["checkpoint_sha256"])
        state = self.learner.state_identity()
        require(state["checkpoint_sha256"] == self.ledger.checkpoint and state["run_id"] == self.run_id
                and state["training_cases_sha256"] == self.identity["training_cases_sha256"]
                and state["record_registry_sha256"] == self.identity["record_registry_sha256"],
                "RESTORED_LEARNER_IDENTITY_MISMATCH")

    def _save(self, reason, selected=None):
        self._verify_tail(self.event_count)
        sequence_number = 0
        for entry in self.history:
            if entry["kind"] == "batch":
                sequence_number += 1
                self._read_step(sequence_number, entry)
        state = self.learner.state_identity()
        require(state["checkpoint_sha256"] == self.ledger.checkpoint, "CHECKPOINT_LEDGER_MISMATCH")
        prior = self.journal.latest()
        sequence = 1 if prior is None else prior["receipt"]["sequence"] + 1
        if selected is not None:
            self.best = {"transaction": sequence, "state_sha256": state["checkpoint_sha256"], **selected}
        metadata = {"schema": SCHEMA, "identity": self.identity, "reason": reason,
            "initial_state_sha256": self.initial_state, "model_state_sha256": state["checkpoint_sha256"],
            "cursor": deepcopy(self.cursor), "batch_size": self.batch_size,
            "pending_development": self.pending_development, "event_count": self.event_count,
            "history": self.history, "best": self.best, "exposure": self.ledger.report()}
        return self.journal.commit(metadata, self.learner.save_checkpoint)

    def _teach_one(self):
        assistance = self.ledger.assistance()
        cycle_ids, records = self._records(self.cursor, assistance)
        sequence = self.event_count + 1
        intent = {"schema": SCHEMA, "run_id": self.run_id, "sequence": sequence,
            "session_identity_sha256": canonical_sha256(self.identity), "cursor": deepcopy(self.cursor),
            "assistance": assistance, "cycle_ids": cycle_ids, "record_sha256": canonical_sha256(records),
            "before_checkpoint_sha256": self.ledger.checkpoint}
        ih = self._event_write(sequence, "intent", intent)
        receipt = self.learner.teach(records)
        rh = self._event_write(sequence, "result", {"sequence": sequence, "intent_sha256": ih, "receipt": receipt})
        self.ledger.record_batch(cycle_ids, records, receipt)
        self.history.append({"kind": "batch", "intent_sha256": ih, "result_sha256": rh})
        self.event_count += 1
        self._advance_cursor()

    def _develop(self):
        entry = {"kind": "development", "event_count": self.event_count, "epoch": self.cursor["epoch"],
            "checkpoint_sha256": self.ledger.checkpoint, "eligible": False, "correct": None, "attempted": 0,
            "reason": "MINIMUM_TEACHING_NOT_COMPLETE"}
        selected = None
        if self.ledger.complete() >= self.allocation.minimum_full_cycles:
            publics = [make_public(case) for case in self.development_cases]
            predictions = self.learner.predict(publics)
            require(type(predictions) is list and len(predictions) == len(publics)
                    and all(type(p) is int and p in (0, 1, 2) for p in predictions), "DEVELOPMENT_PREDICTIONS_INVALID")
            entry.update(predictions=predictions, input_sha256=canonical_sha256(publics), attempted=len(publics),
                         correct=sum(p == c["target_binding"] for p, c in zip(predictions, self.development_cases)))
            try:
                self.ledger.observe_development(split="development", predictions=predictions,
                    input_sha256=entry["input_sha256"], checkpoint_sha256=self.ledger.checkpoint)
            except TeachingError as error:
                require(str(error) in {"MINIMUM_TEACHING_BEFORE_READINESS", "MINIMUM_TEACHING_VARIETY_BEFORE_READINESS",
                    "MINIMUM_PER_FAMILY_TEACHING_BEFORE_READINESS", "BINDING_GRADIENT_DELIVERY_INCOMPLETE"},
                    "UNEXPECTED_DEVELOPMENT_REJECTION:" + str(error))
                entry["reason"] = str(error)
            else:
                entry.update(eligible=True, reason="DEVELOPMENT_ONLY_NOT_MASTERY")
                if self.best is None or entry["correct"] > self.best["correct"]:
                    selected = {"correct": entry["correct"], "attempted": entry["attempted"], "epoch": entry["epoch"]}
        self.history.append(entry)
        self.pending_development = False
        return selected

    def advance_epoch(self, batch_size=32, stop_at=None):
        require(type(batch_size) is int and 1 <= batch_size <= 256, "BATCH_SIZE_INVALID")
        require(self.batch_size in (None, batch_size), "BOUND_BATCH_SIZE_CHANGED")
        self.batch_size = batch_size
        require(stop_at is None or type(stop_at) in (int, float) and math.isfinite(stop_at), "DEADLINE_INVALID")
        def stopped():
            return stop_at is not None and time.monotonic() >= stop_at
        if self.pending_development:
            if stopped():
                self._save("graceful_deadline")
                return self.report()
            self._save("epoch", self._develop())
        epoch = self.cursor["epoch"]
        if epoch >= self.max_epochs:
            return self.report()
        while self.cursor["epoch"] == epoch:
            if stopped():
                self._save("graceful_deadline")
                return self.report()
            self._teach_one()
        if stopped():
            self._save("graceful_deadline_development_pending")
        else:
            self._save("epoch", self._develop())
        return self.report()

    def _reference(self, sequence, state_sha):
        require(type(sequence) is int and sequence >= 1, "CHECKPOINT_REFERENCE_INVALID")
        directory = self.journal.root / f"txn-{sequence:08d}"
        receipt, receipt_hash = _read_json(directory / "receipt.json", RECEIPT_BYTES)
        metadata, _ = _read_json(directory / "metadata.json", self.journal.max_metadata_bytes)
        require(metadata["model_state_sha256"] == state_sha, "CHECKPOINT_REFERENCE_STATE_MISMATCH")
        return {"path": str(directory / "candidate.pt"), "sha256": receipt["checkpoint_sha256"],
                "state_sha256": state_sha, "transaction": sequence, "receipt_sha256": receipt_hash}

    def report(self):
        latest = self.journal.latest()
        return {"schema": SCHEMA, "run_id": self.run_id, "curriculum": self.curriculum,
            "execution_mode": self.execution_mode, "cursor": deepcopy(self.cursor), "max_epochs": self.max_epochs,
            "allocation_finished": self.cursor["epoch"] == self.max_epochs and not self.pending_development,
            "exposure": self.ledger.report(), "initial_checkpoint": self._reference(1, self.initial_state),
            "selected_checkpoint": None if self.best is None else self._reference(self.best["transaction"], self.best["state_sha256"]),
            "last_checkpoint": self._reference(latest["receipt"]["sequence"], latest["metadata"]["model_state_sha256"]),
            "committed_cursor": deepcopy(latest["metadata"]["cursor"]),
            "uncommitted_recorded_optimizer_steps": self.event_count - latest["metadata"]["event_count"],
            "development_curve": [deepcopy(row) for row in self.history if row["kind"] == "development"],
            "observed_optimizer_steps": self.event_count,
            "observed_teaching_examples": sum(row["receipt"]["batch_size"] for row in self.ledger.batches),
            "compute_metrics": summarize_compute(self.ledger.batches, self.execution_mode),
            "retained_journal_bytes": latest["retained_bytes"], "incomplete_staging": latest["incomplete_staging"],
            "retained_event_bytes": self.event_bytes, "event_total_byte_limit": EVENT_TOTAL_BYTE_LIMIT,
            "native_execution": "UNEXECUTED", "complete_native_task_correctness": "UNMEASURED",
            "native_input_binding_bytes_checked": False,
            "provider_identity_proved": False, "compute_cost": "OUTER_PROVIDER_RECEIPT_REQUIRED",
            "boundary": "Simulated learners prove orchestration only. CUDA observations require independent retained evidence."}


def run_campaign(learners, train_cases, development_cases, root, source_sha256, deadline_seconds,
                 allocation=None, seed=7, batch_size=32):
    require(type(learners) is dict and set(learners) == set(ARMS), "FOUR_ARMS_REQUIRED")
    require(type(deadline_seconds) in (int, float) and math.isfinite(deadline_seconds)
            and deadline_seconds > 0, "DEADLINE_INVALID")
    stop_at = time.monotonic() + deadline_seconds
    root = Path(root).absolute()
    _safe_path(root)
    require(root.parent.is_dir(), "CAMPAIGN_PARENT_REQUIRED")
    root.mkdir(exist_ok=True)
    sessions = {arm: TrainingSession(learners[arm], train_cases, development_cases, arm.split(".")[1],
        root / arm, source_sha256, allocation, seed,
        execution_mode=getattr(learners[arm], "execution_mode", "cuda")) for arm in ARMS}
    require(len({session.run_id for session in sessions.values()}) == 4, "UNIQUE_ARM_RUN_IDS_REQUIRED")
    for family in ("cas", "generic"):
        require(sessions[family + ".aligned"].initial_state == sessions[family + ".ordinary"].initial_state,
                "CURRICULUM_INITIAL_CHECKPOINTS_NOT_MATCHED")
    while time.monotonic() < stop_at:
        unfinished = [arm for arm in ARMS if sessions[arm].cursor["epoch"] < sessions[arm].max_epochs
                      or sessions[arm].pending_development]
        if not unfinished:
            break
        arm = min(unfinished, key=lambda key: (sessions[key].cursor["epoch"], ARMS.index(key)))
        sessions[arm].advance_epoch(batch_size, stop_at)
    reports = {arm: session.report() for arm, session in sessions.items()}
    return {"schema": "cas-teaching-four-arm-campaign/1", "arms": reports,
        "all_allocations_finished": all(report["allocation_finished"] for report in reports.values()),
        "matched_order": "Same sorted training cases, seed+epoch permutation, batch size and full epoch allocation.",
        "held_out_opened": False, "automatic_retry": False, "accepted_weights_updated": False,
        "boundary": "Training/development only; held-out execution, retention and provider cost are separate."}
