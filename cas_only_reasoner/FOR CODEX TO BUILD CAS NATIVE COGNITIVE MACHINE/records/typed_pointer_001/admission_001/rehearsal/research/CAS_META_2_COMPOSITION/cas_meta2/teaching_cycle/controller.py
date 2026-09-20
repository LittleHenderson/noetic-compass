"""Pure exposure accounting. Receipts are claims, not proof of AWS execution.

The adapter must supply observations from real training. Synthetic tests are
explicitly labelled and never counted as delivered neural teaching.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from dataclasses import asdict, dataclass
import math
import re

from cas_meta2.codec import canonical_sha256


class TeachingError(ValueError):
    pass


def require(condition, code):
    if not condition:
        raise TeachingError(code)


def digest(value):
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


@dataclass(frozen=True)
class Allocation:
    minimum_full_cycles: int = 1024
    maximum_cycles: int = 4096
    development_interval: int = 256
    consistent_checks: int = 3
    readiness_accuracy: float = 0.90
    minimum_unique_families: int = 256
    minimum_cycles_per_family: int = 4
    development_cases_count: int = 64

    def validate(self):
        for value in (self.minimum_full_cycles, self.maximum_cycles,
                      self.development_interval, self.consistent_checks, self.minimum_unique_families,
                      self.minimum_cycles_per_family, self.development_cases_count):
            require(type(value) is int and value > 0, "ALLOCATION_INVALID")
        require(self.maximum_cycles >= self.minimum_full_cycles, "ALLOCATION_INVALID")
        require(type(self.readiness_accuracy) in (int, float)
                and math.isfinite(self.readiness_accuracy)
                and 0 < self.readiness_accuracy <= 1, "READINESS_THRESHOLD_INVALID")


class ExposureLedger:
    """One candidate/arm only; different checkpoints cannot share a ledger.

    Complete means all seven ordered presentations reached an optimizer step.
    It does not mean the skill was learned. Aligned full cycles and ordinary
    seven-presentation blocks have separate names in the report.
    """
    def __init__(self, *, run_id, curriculum, scope_names, initial_checkpoint, train_cases, development_cases,
                 allocation=None, execution_mode="cuda"):
        self.allocation = allocation or Allocation()
        self.allocation.validate()
        from .guided_application import make_cycle, make_public
        require(type(train_cases) is list and len(train_cases) >= self.allocation.minimum_unique_families,
                "TRAINING_VARIETY_ALLOCATION_INVALID")
        self.train_cases = {}
        self.planned = {}
        for case in train_cases:
            require(type(case) is dict and case.get("split") == "train", "TRAINING_CASE_REQUIRED")
            family = case.get("family_id")
            require(type(family) is str and family not in self.train_cases, "TRAINING_FAMILY_DUPLICATE")
            for help_level in ("full", "faded", "none"):
                self.planned[(family, help_level)] = make_cycle(case, help_level, curriculum)
            self.train_cases[family] = deepcopy(case)
        self.training_cases_sha256 = canonical_sha256(sorted(train_cases, key=lambda c: c["family_id"]))
        require(type(development_cases) is list
                and len(development_cases) == self.allocation.development_cases_count,
                "DEVELOPMENT_ALLOCATION_INVALID")
        self.development_cases = deepcopy(development_cases)
        require(all(c.get("split") == "development" for c in development_cases),
                "DEVELOPMENT_CASE_REQUIRED")
        families = [c.get("family_id") for c in development_cases]
        require(len(set(families)) == len(families) and not set(families) & set(self.train_cases),
                "DEVELOPMENT_FAMILY_LEAKAGE")
        self.development_input_sha256 = canonical_sha256([make_public(c) for c in development_cases])
        require(type(run_id) is str and bool(run_id), "RUN_ID_INVALID")
        require(curriculum in ("aligned", "ordinary"), "CURRICULUM_INVALID")
        require(execution_mode in ("cuda", "simulated"), "EXECUTION_MODE_INVALID")
        require(type(scope_names) in (list, tuple) and len(scope_names) > 0
                and all(type(name) is str and name for name in scope_names)
                and len(set(scope_names)) == len(scope_names), "SCOPE_INVALID")
        require(digest(initial_checkpoint), "CHECKPOINT_ID_INVALID")
        self.run_id = run_id
        self.curriculum = curriculum
        self.scope_names = tuple(sorted(scope_names))
        self.scope_sha256 = canonical_sha256(list(self.scope_names))
        self.learning_path = set(self.scope_names) & {
            "binding_query.weight", "binding_key.weight", "token_head.weight", "token_head.bias"}
        require(bool(self.learning_path), "BINDING_LEARNING_PATH_REQUIRED")
        self.initial_checkpoint = initial_checkpoint
        self.checkpoint = initial_checkpoint
        self.execution_mode = execution_mode
        self.cycles = {}
        self.batches = []
        self.development = []

    def record_batch(self, cycle_ids, records, receipt):
        """Validate everything first: a bad batch must not partly advance state."""
        from .guided_application import STAGES
        require(type(records) is list and records and len(records) == len(cycle_ids)
                and len(set(cycle_ids)) == len(cycle_ids), "BATCH_INVALID")
        require(all(type(key) is str and key for key in cycle_ids), "CYCLE_ID_INVALID")
        require(type(receipt) is dict, "RECEIPT_INVALID")
        require(receipt.get("run_id") == self.run_id, "RECEIPT_RUN_MISMATCH")
        require(receipt.get("execution_mode") == self.execution_mode, "RECEIPT_MODE_MISMATCH")
        require(receipt.get("scope_sha256") == self.scope_sha256, "RECEIPT_SCOPE_MISMATCH")
        require(receipt.get("training_cases_sha256") == self.training_cases_sha256,
                "RECEIPT_TRAINING_PLAN_MISMATCH")
        require(receipt.get("before_checkpoint_sha256") == self.checkpoint
                and digest(receipt.get("after_checkpoint_sha256")), "CHECKPOINT_CHAIN_BROKEN")
        require(type(receipt.get("optimizer_steps")) is int
                and receipt["optimizer_steps"] == 1, "OPTIMIZER_STEP_REQUIRED")
        require(type(receipt.get("batch_size")) is int and receipt["batch_size"] == len(records),
                "RECEIPT_BATCH_MISMATCH")
        require(receipt.get("input_sha256") == canonical_sha256([r["public"] for r in records]),
                "DELIVERED_INPUT_MISMATCH")
        require(receipt.get("target_sha256") == canonical_sha256([r["target_binding"] for r in records]),
                "DELIVERED_TARGET_MISMATCH")
        require(type(receipt.get("loss")) in (float, int) and math.isfinite(receipt["loss"]),
                "LOSS_NOT_FINITE")
        for field in ("gradient_parameter_names", "changed_parameter_names"):
            names = receipt.get(field)
            require(type(names) is list and len(set(names)) == len(names)
                    and set(names) <= set(self.scope_names), "PARAMETER_SCOPE_ESCAPE")
        if self.execution_mode == "cuda":
            require(type(receipt.get("device")) is str and receipt["device"].startswith("cuda"),
                    "CUDA_RECEIPT_REQUIRED")
            require(type(receipt.get("gpu_name")) is str and receipt["gpu_name"]
                    and "T4" not in receipt["gpu_name"].upper(), "GPU_NOT_PERMITTED")
        stage_indexes = set()
        pending = {}
        for key, record in zip(cycle_ids, records):
            require(record.get("split") == "train", "HELD_OUT_TEACHING_REJECTED")
            require(record.get("curriculum") == self.curriculum, "CURRICULUM_MISMATCH")
            require(type(record.get("target_binding")) is int
                    and record["target_binding"] in (0, 1, 2), "BINDING_INVALID")
            stage = record.get("stage_index")
            require(type(stage) is int and 0 <= stage < 7, "STAGE_INVALID")
            expected = STAGES[stage] if self.curriculum == "aligned" else f"presentation_{stage + 1}"
            require(record.get("stage") == expected, "STAGE_INVALID")
            help_level = record.get("assistance")
            require(help_level in ("full", "faded", "none"), "ASSISTANCE_INVALID")
            require(help_level == self.assistance(), "ASSISTANCE_PHASE_MISMATCH")
            planned = self.planned.get((record.get("family_id"), help_level))
            require(planned is not None and record == planned[stage], "UNREGISTERED_OR_CHANGED_LESSON")
            prior = self.cycles.get(key)
            if prior is None:
                require(stage == 0, "INCOMPLETE_CYCLE_START")
                require(type(record.get("family_id")) is str and record["family_id"], "FAMILY_INVALID")
                prior = {"family_id": record["family_id"], "stages": [], "assistance": help_level,
                         "gradient_bearing_stages": []}
            require(prior["family_id"] == record.get("family_id")
                    and prior["assistance"] == help_level, "CYCLE_IDENTITY_MISMATCH")
            require(stage == len(prior["stages"]), "STAGE_ORDER_OR_REPLAY")
            stage_indexes.add(stage)
            reached = bool(self.learning_path & set(receipt["gradient_parameter_names"]))
            pending[key] = {**prior, "stages": prior["stages"] + [record["stage"]],
                "gradient_bearing_stages": prior["gradient_bearing_stages"] + [reached]}
        require(len(stage_indexes) == 1, "MIXED_STAGE_BATCH")
        require(len(set(self.cycles) | set(pending)) <= self.allocation.maximum_cycles,
                "TEACHING_ALLOCATION_EXHAUSTED")
        self.cycles.update(pending)
        self.checkpoint = receipt["after_checkpoint_sha256"]
        self.batches.append({"cycle_ids": list(cycle_ids), "receipt": dict(receipt)})

    def complete(self, assistance=None):
        return sum(len(c["stages"]) == 7 and (assistance is None or c["assistance"] == assistance)
                   for c in self.cycles.values())

    def observe_development(self, *, split, predictions, input_sha256, checkpoint_sha256):
        require(split == "development", "FINAL_TEST_FEEDBACK_REJECTED")
        require(checkpoint_sha256 == self.checkpoint, "DEVELOPMENT_CHECKPOINT_MISMATCH")
        require(input_sha256 == self.development_input_sha256, "DEVELOPMENT_INPUT_MISMATCH")
        require(type(predictions) is list and len(predictions) == len(self.development_cases)
                and all(type(p) is int and p in (0, 1, 2) for p in predictions),
                "DEVELOPMENT_PREDICTIONS_INVALID")
        attempted = len(predictions)
        correct = sum(p == c["target_binding"] for p, c in zip(predictions, self.development_cases))
        complete = self.complete()
        previous = self.development[-1]["complete_cycles"] if self.development else 0
        require(complete >= self.allocation.minimum_full_cycles
                and complete - previous >= self.allocation.development_interval,
                "MINIMUM_TEACHING_BEFORE_READINESS")
        require(self._full_variety() >= self.allocation.minimum_unique_families,
                "MINIMUM_TEACHING_VARIETY_BEFORE_READINESS")
        require(self._family_minimum_met(), "MINIMUM_PER_FAMILY_TEACHING_BEFORE_READINESS")
        require(self._gradient_families() == set(self.train_cases), "BINDING_GRADIENT_DELIVERY_INCOMPLETE")
        require(all(len(c["stages"]) == 7 for c in self.cycles.values()), "CYCLE_STILL_OPEN")
        self.development.append({"complete_cycles": complete, "correct": correct,
            "attempted": attempted, "checkpoint_sha256": checkpoint_sha256,
            "input_sha256": input_sha256, "predictions_sha256": canonical_sha256(predictions),
            "assistance": self.assistance(), "readiness_not_mastery": True})

    def _consistent(self, assistance):
        rows = [r for r in self.development if r["assistance"] == assistance]
        needed = self.allocation.consistent_checks
        return len(rows) >= needed and all(
            r["correct"] / r["attempted"] >= self.allocation.readiness_accuracy for r in rows[-needed:])

    def _full_variety(self):
        return len({c["family_id"] for c in self.cycles.values()
                    if len(c["stages"]) == 7 and c["assistance"] == "full"})

    def _full_family_counts(self):
        return Counter(c["family_id"] for c in self.cycles.values()
                       if len(c["stages"]) == 7 and c["assistance"] == "full")

    def _family_minimum_met(self):
        counts = self._full_family_counts()
        return all(counts[f] >= self.allocation.minimum_cycles_per_family for f in self.train_cases)

    def _gradient_families(self):
        return {c["family_id"] for c in self.cycles.values()
                if len(c["stages"]) == 7 and all(c["gradient_bearing_stages"])}

    def assistance(self):
        if (self.complete("full") < self.allocation.minimum_full_cycles
                or self._full_variety() < self.allocation.minimum_unique_families
                or not self._family_minimum_met() or self._gradient_families() != set(self.train_cases)
                or not self._consistent("full")):
            return "full"
        return "none" if self._consistent("faded") else "faded"

    def report(self):
        counts = Counter(s for c in self.cycles.values() for s in c["stages"])
        complete = self.complete()
        if self.execution_mode == "simulated":
            state = "SIMULATED_ONLY_NOT_DELIVERED"
        elif (self.complete("full") < self.allocation.minimum_full_cycles
              or self._full_variety() < self.allocation.minimum_unique_families
              or not self._family_minimum_met() or self._gradient_families() != set(self.train_cases)):
            state = "TEACHING_INCOMPLETE"
        elif self.assistance() == "none" and self._consistent("none"):
            state = "READY_FOR_FINAL_EVALUATION_NOT_MASTERY"
        elif complete >= self.allocation.maximum_cycles:
            state = "ALLOCATION_COMPLETE_READINESS_NOT_ESTABLISHED"
        else:
            state = "TEACHING_IN_PROGRESS"
        return {"schema": "cas-teaching-exposure/1", "status": state,
            "run_id": self.run_id, "curriculum": self.curriculum,
            "execution_mode": self.execution_mode, "provider_identity_proved": False,
            "completed_full_aligned_cycles": complete if self.curriculum == "aligned" else 0,
            "completed_ordinary_blocks": complete if self.curriculum == "ordinary" else 0,
            "full_guidance_blocks": self.complete("full"),
            "full_guidance_unique_families": self._full_variety(),
            "full_guidance_cycles_per_family": dict(self._full_family_counts()),
            "families_in_complete_gradient_bearing_batches": len(self._gradient_families()),
            "training_cases_sha256": self.training_cases_sha256,
            "stage_exposures": dict(counts), "unique_families": len({c["family_id"] for c in self.cycles.values()}),
            "optimizer_steps": len(self.batches), "batches_with_parameter_change": sum(
                bool(b["receipt"]["changed_parameter_names"]) for b in self.batches),
            "claimed_cuda_cycles": complete if self.execution_mode == "cuda" else 0,
            "verified_neural_cycles": 0,
            "assistance": self.assistance(), "allocation": asdict(self.allocation),
            "current_checkpoint_sha256": self.checkpoint,
            "scope_sha256": self.scope_sha256,
            "boundary": "Unverified trainer observations until bound to retained checkpoint and provider evidence; no mastery claim."}
