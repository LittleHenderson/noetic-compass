"""Small training-fit mode for the teaching campaign's binding task.

Question answered (design-only until a separate owner-authorized launch):
    "Can the CAS/generic binding learning path acquire the compact task on
     short task-only inputs?"

What this mode does:
  * draws 24 balanced known binding examples (8 per binding slot) from the
    frozen teaching families (reusing ``teaching_cycle.data.build_dataset``);
  * renders SHORT task-only inputs with no explanatory guidance (reusing
    ``teaching_cycle.lesson_contract.make_public``); the training answer is
    supplied separately as the supervised target, never hidden in the question;
  * runs ACTUAL optimizer updates per family through the identity-checked
    backward/step contract already proven in ``teaching_cycle/gpu_adapter.py``
    (``optimizer.zero_grad`` -> cross-entropy loss -> ``loss.backward()`` ->
    identity re-check -> ``optimizer.step()``, with before/after state-identity
    hashes);
  * records loss and accuracy BEFORE and AFTER the updates, per family, plus
    the optimizer step count and the before/after state-identity hash.

No real tensor library is imported at module scope. The real ``torch`` module is
reached only through :func:`import_torch` (which tests monkeypatch) and the real
launch path ``gpu_adapter._cuda``. Forward-only measurement is never reported as
training fit: the mode separates a measurement pass (no optimizer) from a
training pass (optimizer updates), and it only reports ``OPTIMIZER_UPDATES_PERFORMED``
when the before/after state hash actually changed and steps advanced.
"""

from __future__ import annotations

from hashlib import sha256
import math
import re
import time

from ..codec import canonical_sha256, validate_public

SCHEMA = "cas-teaching-binding-fit-training/1"
FAMILIES = ("cas", "generic_attention")
ADAPTER_FAMILY = {"cas": "cas", "generic_attention": "generic"}
BINDING_SLOTS = (0, 1, 2)
CASES_PER_SLOT = 8
TOTAL_CASES = 24

# Budget declaration points. These are frozen by the run's OWNER_AUTHORIZATION
# before launch; they are passed as parameters with strict bounds below.
DEFAULT_MAX_OPTIMIZER_STEPS = 48
DEFAULT_MAX_WALL_SECONDS = 600.0

BOUNDARY = (
    "Small training-fit check on 24 balanced known training cases only. Actual optimizer "
    "updates per family through the identity-checked backward/step path. Loss and accuracy "
    "are recorded before and after; forward-only measurement is never reported as training "
    "fit. No final evaluation target is read. No generalization, native admission, repair, "
    "caller-return, or composition claim."
)

_GUIDANCE_MARKERS = ("Worked", "Hint", "parcel", "Read the request", "Rule", "guide")


def require(condition, code):
    if not condition:
        raise ValueError("BINDING_FIT:" + code)


def import_torch():
    """The mode's only torch-import seam. Tests monkeypatch this to return a fake."""
    import torch  # noqa: PLC0415 - deliberately deferred, never at module scope
    return torch


def validate_budget(max_optimizer_steps, max_wall_seconds):
    """Strict bounds on the two budget declaration points."""
    require(type(max_optimizer_steps) is int and max_optimizer_steps >= 1,
            "OPTIMIZER_STEP_BUDGET_INVALID")
    require(type(max_wall_seconds) in (int, float)
            and math.isfinite(max_wall_seconds) and max_wall_seconds > 0,
            "WALL_BUDGET_INVALID")


def build_balanced_cases(seed=20260908):
    """24 balanced known training cases: 8 per binding slot, train split only."""
    from ..teaching_cycle import data
    train = data.build_dataset(seed)["splits"]["train"]
    by_slot = {slot: [c for c in train if c["target_binding"] == slot] for slot in BINDING_SLOTS}
    cases = []
    for slot in BINDING_SLOTS:
        chosen = sorted(by_slot[slot], key=lambda c: c["family_id"])[:CASES_PER_SLOT]
        require(len(chosen) == CASES_PER_SLOT, "INSUFFICIENT_TRAINING_CASES")
        cases.extend(chosen)
    cases.sort(key=lambda c: c["family_id"])
    validate_balanced_cases(cases, seed=seed)
    return cases


def validate_balanced_cases(cases, *, seed=20260908):
    """Refuse empty, unbalanced, non-train, or unknown-family case selections."""
    require(type(cases) is list and len(cases) == TOTAL_CASES, "CASE_COUNT_INVALID")
    from ..teaching_cycle import data, lesson_contract as lesson
    known = {c["family_id"] for c in data.build_dataset(seed)["splits"]["train"]}
    seen = set()
    balance = {slot: 0 for slot in BINDING_SLOTS}
    for case in cases:
        require(type(case) is dict, "CASE_INVALID")
        require(case.get("split") == "train", "NON_TRAIN_CASE_REJECTED")
        lesson._case_check(case)
        require(case["family_id"] in known, "UNKNOWN_FAMILY_REJECTED")
        require(case["family_id"] not in seen, "DUPLICATE_FAMILY")
        seen.add(case["family_id"])
        balance[case["target_binding"]] += 1
    require(balance == {slot: CASES_PER_SLOT for slot in BINDING_SLOTS}, "BINDING_BALANCE_INVALID")
    return cases


def short_public(case):
    """Short task-only input; no explanatory guidance and no answer inside the question."""
    from ..teaching_cycle import lesson_contract as lesson
    lesson._case_check(case)
    require(case["split"] == "train", "NON_TRAIN_CASE_REJECTED")
    public = lesson.make_public(case)
    require("BIND" not in public["problem"], "ANSWER_IN_PRESENTATION")
    for marker in _GUIDANCE_MARKERS:
        require(marker not in public["problem"], "GUIDANCE_IN_PRESENTATION")
    return public


def build_records(cases):
    """Training records: short public + separate supervised target, never an answer in the public."""
    validate_balanced_cases(cases)
    records = [{"family_id": case["family_id"], "split": "train",
                "public": short_public(case), "target_binding": case["target_binding"]}
               for case in cases]
    validate_records(records)
    return records


def validate_records(records):
    """Refuse empty, wrong-shape, answer-bearing, or non-training records."""
    require(type(records) is list and len(records) == TOTAL_CASES, "RECORD_COUNT_INVALID")
    seen = set()
    balance = {slot: 0 for slot in BINDING_SLOTS}
    for record in records:
        require(type(record) is dict and set(record) == {"family_id", "split", "public", "target_binding"},
                "RECORD_FIELDS_INVALID")
        require(record["split"] == "train", "NON_TRAIN_RECORD_REJECTED")
        require(type(record["family_id"]) is str and bool(record["family_id"])
                and record["family_id"] not in seen, "FAMILY_INVALID")
        seen.add(record["family_id"])
        target = record["target_binding"]
        require(type(target) is int and target in BINDING_SLOTS, "TARGET_INVALID")
        validate_public(record["public"])
        require("BIND" not in record["public"]["problem"], "ANSWER_IN_PRESENTATION")
        for marker in _GUIDANCE_MARKERS:
            require(marker not in record["public"]["problem"], "GUIDANCE_IN_PRESENTATION")
        balance[target] += 1
    require(balance == {slot: CASES_PER_SLOT for slot in BINDING_SLOTS}, "BINDING_BALANCE_INVALID")
    return records


def state_identity_manifest(torch, model):
    """Byte-exact model-state digest, mirroring ``gpu_adapter.BindingLearner._snapshot``.

    Plain (non-tensor) state entries hash through ``canonical_sha256`` so injected
    fakes exercise the same before/after identity check as real tensor state.
    """
    manifest = {}
    for name, value in sorted(model.state_dict().items()):
        if hasattr(value, "detach") and hasattr(value, "contiguous") and hasattr(value, "shape"):
            raw = value.detach().contiguous().reshape(-1)
            storage = getattr(raw, "untyped_storage", None)
            payload = bytes(storage()) if storage is not None else repr(raw).encode("utf-8")
            manifest[name] = {"dtype": str(getattr(value, "dtype", "?")),
                              "shape": list(value.shape), "sha256": sha256(payload).hexdigest()}
        else:
            manifest[name] = canonical_sha256(value)
    return canonical_sha256(manifest)


class BindingFitLearner:
    """One family's identity-checked learner; reuses the ``gpu_adapter`` step contract.

    ``train`` performs the exact sequence proven in ``gpu_adapter.BindingLearner.teach``:
    zero_grad -> forward -> cross-entropy -> backward -> identity re-check -> step,
    with before/after state-identity hashes. ``evaluate`` is a forward-only
    measurement (no optimizer) and is never reported as training fit.
    """

    def __init__(self, torch, model, tokenizer, optimizer, *, family, run_id,
                 state_hasher=None, device=None):
        if torch is None:
            torch = import_torch()
        require(torch is not None, "TORCH_REQUIRED")
        require(family in FAMILIES, "FAMILY_INVALID")
        require(type(run_id) is str and bool(run_id), "RUN_ID_INVALID")
        require(callable(model), "MODEL_REQUIRED")
        require(callable(getattr(model, "state_dict", None)), "MODEL_STATE_OBSERVER_REQUIRED")
        require(callable(getattr(model, "train", None)) and callable(getattr(model, "eval", None)),
                "MODEL_MODE_REQUIRED")
        require(callable(getattr(tokenizer, "encode_public", None)), "TOKENIZER_REQUIRED")
        require(callable(getattr(optimizer, "zero_grad", None)), "OPTIMIZER_REQUIRED")
        require(callable(getattr(optimizer, "step", None)), "OPTIMIZER_REQUIRED")
        self.torch, self.model, self.tokenizer, self.optimizer = torch, model, tokenizer, optimizer
        self.family, self.run_id, self.device = family, run_id, device
        self.steps = 0
        self._state_hasher = state_hasher if state_hasher is not None else (
            lambda m: state_identity_manifest(self.torch, m))
        require(callable(self._state_hasher), "STATE_OBSERVER_REQUIRED")

    def _state_hash(self):
        return self._state_hasher(self.model)

    def state_identity(self):
        return {"run_id": self.run_id, "family": self.family,
                "checkpoint_sha256": self._state_hash(), "optimizer_steps": self.steps}

    def _encode(self, publics):
        encoded = [self.tokenizer.encode_public(public) for public in publics]
        ids = self.torch.tensor([row["ids"] for row in encoded], dtype=self.torch.long)
        values = self.torch.tensor([row["values"] for row in encoded], dtype=self.torch.float32)
        return {"ids": ids, "values": values}

    def _forward(self, publics):
        require(type(publics) is list and 1 <= len(publics) <= TOTAL_CASES, "BATCH_SIZE_INVALID")
        for public in publics:
            validate_public(public)
        output = self.model(self._encode(publics))
        require(type(output) is dict and "binding_logits" in output, "LOGITS_REQUIRED")
        logits = output["binding_logits"]
        require(tuple(logits.shape) == (len(publics), 3), "BINDING_LOGITS_GEOMETRY_INVALID")
        return logits

    def _loss_and_accuracy(self, publics, targets):
        logits = self._forward(publics)
        labels = self.torch.tensor(targets, dtype=self.torch.long)
        loss = self.torch.nn.functional.cross_entropy(logits, labels)
        require(bool(self.torch.isfinite(loss)), "NONFINITE_LOSS")
        rows = logits.tolist()
        predictions = [max(range(3), key=lambda index: rows[row][index]) for row in range(len(rows))]
        correct = sum(1 for prediction, target in zip(predictions, targets) if prediction == target)
        return float(loss.item()), correct / len(targets)

    def evaluate(self, records):
        """Forward-only loss/accuracy measurement; no optimizer, never reported as fit."""
        publics = [record["public"] for record in records]
        targets = [record["target_binding"] for record in records]
        self.model.eval()
        with self.torch.no_grad():
            loss, accuracy = self._loss_and_accuracy(publics, targets)
        return {"loss": loss, "accuracy": accuracy}

    def train(self, records):
        """One identity-checked optimizer step, mirroring ``gpu_adapter``'s ``teach``."""
        publics = [record["public"] for record in records]
        targets = [record["target_binding"] for record in records]
        self.model.train()
        before = self._state_hash()
        self.optimizer.zero_grad(set_to_none=True)
        logits = self._forward(publics)
        labels = self.torch.tensor(targets, dtype=self.torch.long)
        loss = self.torch.nn.functional.cross_entropy(logits, labels)
        require(bool(self.torch.isfinite(loss)), "NONFINITE_LOSS")
        loss.backward()
        require(self._state_hash() == before, "STATE_CHANGED_BEFORE_STEP")
        self.optimizer.step()
        after = self._state_hash()
        self.steps += 1
        return {"family": self.family, "run_id": self.run_id,
                "loss": float(loss.item()), "optimizer_steps": 1,
                "cumulative_optimizer_steps": self.steps,
                "before_checkpoint_sha256": before, "after_checkpoint_sha256": after,
                "state_changed": after != before}


def run_fit(records, learners, *, max_optimizer_steps=DEFAULT_MAX_OPTIMIZER_STEPS,
            max_wall_seconds=DEFAULT_MAX_WALL_SECONDS, wall_clock=time.perf_counter):
    """Pure orchestration over the learner contract; no tensor library here."""
    validate_records(records)
    validate_budget(max_optimizer_steps, max_wall_seconds)
    require(type(learners) is dict and set(learners) == set(FAMILIES), "LEARNERS_REQUIRED")
    started = wall_clock()
    per_family = max_optimizer_steps // len(FAMILIES)
    extra = max_optimizer_steps % len(FAMILIES)
    total_steps = 0
    families = {}
    for index, family in enumerate(FAMILIES):
        learner = learners[family]
        require(learner is not None, "LEARNER_MISSING:" + family)
        for method in ("evaluate", "train", "state_identity"):
            require(callable(getattr(learner, method, None)), "LEARNER_OBSERVER_MISSING:" + method)
        before_state = learner.state_identity()
        before_measure = learner.evaluate(records)
        train_losses = []
        family_steps = 0
        steps_for_this_family = per_family + (1 if index < extra else 0)
        while family_steps < steps_for_this_family:
            if wall_clock() - started >= max_wall_seconds:
                raise ValueError("BINDING_FIT:WALL_BUDGET_EXCEEDED")
            receipt = learner.train(records)
            train_losses.append(receipt["loss"])
            family_steps += 1
            total_steps += 1
        after_state = learner.state_identity()
        after_measure = learner.evaluate(records)
        require(type(after_state.get("optimizer_steps")) is int
                and after_state["optimizer_steps"] == before_state.get("optimizer_steps", 0) + family_steps,
                "STEP_ACCOUNTING_INVALID")
        state_changed = after_state.get("checkpoint_sha256") != before_state.get("checkpoint_sha256")
        training_fit = "OPTIMIZER_UPDATES_PERFORMED" if (state_changed and family_steps > 0) else "FORWARD_ONLY_NOT_FIT"
        families[family] = {
            "family": family,
            "run_id": before_state.get("run_id"),
            "before": {"loss": before_measure["loss"], "accuracy": before_measure["accuracy"],
                       "checkpoint_sha256": before_state.get("checkpoint_sha256"),
                       "optimizer_steps": before_state.get("optimizer_steps")},
            "after": {"loss": after_measure["loss"], "accuracy": after_measure["accuracy"],
                      "checkpoint_sha256": after_state.get("checkpoint_sha256"),
                      "optimizer_steps": after_state.get("optimizer_steps")},
            "optimizer_steps_performed": family_steps,
            "state_changed": state_changed,
            "training_fit": training_fit,
            "train_losses": train_losses,
        }
    wall_seconds = wall_clock() - started
    require(math.isfinite(wall_seconds), "WALL_TIME_INVALID")
    training_updates_performed = all(
        family_report["training_fit"] == "OPTIMIZER_UPDATES_PERFORMED"
        for family_report in families.values())
    return {
        "schema": SCHEMA,
        "status": "TRAINING_FIT_CHECK_COMPLETE",
        "cases": {"count": TOTAL_CASES,
                  "per_slot": {str(slot): CASES_PER_SLOT for slot in BINDING_SLOTS},
                  "split": "train"},
        "training_cases_sha256": canonical_sha256(sorted(
            [{"family_id": r["family_id"], "target_binding": r["target_binding"]} for r in records],
            key=lambda row: row["family_id"])),
        "publics_sha256": canonical_sha256([record["public"] for record in records]),
        "presentation": "short_task_only_no_guidance",
        "families": families,
        "budget": {"max_optimizer_steps": max_optimizer_steps,
                   "max_wall_seconds": max_wall_seconds,
                   "optimizer_steps_used": total_steps,
                   "wall_seconds": wall_seconds},
        "training_updates_performed": training_updates_performed,
        "forward_only_never_reported_as_fit": True,
        "final_targets_read": False,
        "provider_identity_proved": False,
        "boundary": BOUNDARY,
    }


def launch(*, run_id, cases=None, seed=20260908,
           max_optimizer_steps=DEFAULT_MAX_OPTIMIZER_STEPS,
           max_wall_seconds=DEFAULT_MAX_WALL_SECONDS, learning_rate=0.003):
    """Real entry the run executes: build real learners, then run the fit check.

    Reuses the frozen machinery that ``gpu_adapter.build_matched_learners`` uses
    (``gpu_adapter._cuda`` device/guard, ``guided_application.fit_tokenizer``,
    ``policy.build_matched_policies``, ``torch.optim.AdamW``), but assembles the
    mode's short-input ``BindingFitLearner`` around the same identity-checked
    backward/step contract. This function is not exercised by the pure tests.
    """
    require(type(run_id) is str and bool(run_id), "RUN_ID_REQUIRED")
    if cases is None:
        cases = build_balanced_cases(seed)
    validate_balanced_cases(cases, seed=seed)
    records = build_records(cases)
    from ..teaching_cycle import gpu_adapter
    from ..teaching_cycle.guided_application import fit_tokenizer
    tokenizer = fit_tokenizer(cases)
    torch, device = gpu_adapter._cuda()
    from ..policy import PolicyConfig, build_matched_policies
    config = PolicyConfig()
    gpu_adapter.require(config.max_length == tokenizer.max_length, "REGISTERED_TOKENIZER_LENGTH_REQUIRED")
    cas, generic, _matching = build_matched_policies(tokenizer, config, seed=seed, device=device)
    models = {"cas": cas, "generic_attention": generic}
    learners = {}
    for family, model in models.items():
        optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=0.0)
        learners[family] = BindingFitLearner(torch, model, tokenizer, optimizer,
                                             family=family, run_id=f"{run_id}.{family}", device=device)
    return run_fit(records, learners, max_optimizer_steps=max_optimizer_steps,
                   max_wall_seconds=max_wall_seconds)
