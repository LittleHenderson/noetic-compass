"""Synthetic orchestration only. The fake learner is a rule, not a neural model."""
import ast
from hashlib import sha256
import json
from pathlib import Path

import pytest

from cas_meta2.codec import canonical_sha256
from cas_meta2.teaching_cycle import journal, runner
from cas_meta2.teaching_cycle.controller import Allocation
from cas_meta2.teaching_cycle.data import build_dataset
from cas_meta2.teaching_cycle.guided_application import recover_binding

SOURCE = "1" * 64


class FakeLearner:
    execution_mode = "simulated"

    def __init__(self, run_id, cases, *, family="cas", clock=None, fail_at=None, gradients=True):
        self.run_id, self.family, self.counter = run_id, family, 0
        self.training_sha = canonical_sha256(sorted(cases, key=lambda c: c["family_id"]))
        self.clock, self.fail_at, self.gradients = clock, fail_at, gradients
        self.orders, self.restore_calls = [], 0

    def state_identity(self):
        return {"run_id": self.run_id, "checkpoint_sha256": canonical_sha256([self.family, self.counter]),
                "scope_names": ["binding_query.weight"], "training_cases_sha256": self.training_sha,
                "record_registry_sha256": "2" * 64}

    def teach(self, records):
        before = self.state_identity()["checkpoint_sha256"]
        self.counter += 1
        if self.clock is not None:
            self.clock[0] += 1
        if self.counter == self.fail_at:
            raise RuntimeError("synthetic learner interruption after attempted update")
        self.orders.append([(r["family_id"], r["stage_index"]) for r in records])
        return {"run_id": self.run_id, "execution_mode": "simulated",
            "scope_sha256": canonical_sha256(["binding_query.weight"]),
            "training_cases_sha256": self.training_sha, "before_checkpoint_sha256": before,
            "after_checkpoint_sha256": self.state_identity()["checkpoint_sha256"],
            "optimizer_steps": 1, "batch_size": len(records), "loss": .5,
            "input_sha256": canonical_sha256([r["public"] for r in records]),
            "target_sha256": canonical_sha256([r["target_binding"] for r in records]),
            "gradient_parameter_names": ["binding_query.weight"] if self.gradients else [],
            "changed_parameter_names": ["binding_query.weight"], "provider_identity_proved": False}

    def predict(self, publics):
        return [recover_binding(public) for public in publics]

    def save_checkpoint(self, path):
        payload = json.dumps({"counter": self.counter, "run_id": self.run_id, "family": self.family}).encode()
        with path.open("xb") as stream:
            stream.write(payload)
        return {"path": str(path), "sha256": sha256(payload).hexdigest(), "tensor_execution": False}

    def restore_checkpoint(self, path, digest):
        payload = Path(path).read_bytes()
        assert sha256(payload).hexdigest() == digest
        state = json.loads(payload)
        assert state["run_id"] == self.run_id and state["family"] == self.family
        self.counter = state["counter"]
        self.restore_calls += 1


@pytest.fixture
def plan(monkeypatch):
    # Durability/link walking is exercised in journal tests. These isolated
    # synthetic directories test orchestration without repeated OneDrive walks.
    monkeypatch.setattr(journal.os, "fsync", lambda descriptor: None)
    monkeypatch.setattr(journal, "_safe_path", lambda path: None)
    monkeypatch.setattr(runner, "_safe_path", lambda path: None)
    dataset = build_dataset()
    train = dataset["splits"]["train"][:4]
    dev = dataset["splits"]["development"][:2]
    allocation = Allocation(minimum_full_cycles=16, maximum_cycles=32, development_interval=4,
        consistent_checks=1, readiness_accuracy=.9, minimum_unique_families=4,
        minimum_cycles_per_family=4, development_cases_count=2)
    return train, dev, allocation


def session(tmp_path, plan, learner=None, name="session", **kwargs):
    train, dev, allocation = plan
    learner = learner or FakeLearner("test-session", train)
    return runner.TrainingSession(learner, train, dev, "aligned", tmp_path / name,
        SOURCE, allocation, execution_mode="simulated", **kwargs)


def test_full_four_arm_allocation_keeps_early_readiness_from_stopping(tmp_path, plan):
    train, dev, allocation = plan
    learners = {arm: FakeLearner(arm, train, family=arm.split(".")[0]) for arm in runner.ARMS}
    report = runner.run_campaign(learners, train, dev, tmp_path / "campaign", SOURCE, 120,
                                 allocation=allocation, batch_size=2)
    assert report["all_allocations_finished"] is True
    assert report["held_out_opened"] is False
    assert [learner.counter for learner in learners.values()] == [112] * 4
    assert all(learner.orders == learners["cas.aligned"].orders for learner in learners.values())
    for arm in report["arms"].values():
        assert arm["exposure"]["status"] == "SIMULATED_ONLY_NOT_DELIVERED"
        assert arm["exposure"]["verified_neural_cycles"] == 0
        assert arm["observed_teaching_examples"] == 32 * 7
        assert arm["selected_checkpoint"]["transaction"] == 5  # Earliest eligible epoch 4.
        assert [row["attempted"] for row in arm["development_curve"]] == [0, 0, 0, 2, 2, 2, 2, 2]
        assert arm["native_execution"] == "UNEXECUTED"


def test_graceful_midcycle_stop_restores_exact_cursor_and_history(tmp_path, plan, monkeypatch):
    train, _, _ = plan
    clock = [0]
    monkeypatch.setattr(runner.time, "monotonic", lambda: clock[0])
    learner = FakeLearner("test-session", train, clock=clock)
    first = session(tmp_path, plan, learner)
    first.advance_epoch(batch_size=2, stop_at=3)
    assert first.cursor == {"epoch": 0, "batch": 0, "stage": 3}
    restarted = FakeLearner("test-session", train)
    second = session(tmp_path, plan, restarted)
    assert restarted.counter == 3 and restarted.restore_calls == 1
    assert second.cursor == first.cursor
    assert second.ledger.report() == first.ledger.report()
    second.advance_epoch(batch_size=2)
    assert restarted.counter == 14
    assert second.cursor == {"epoch": 1, "batch": 0, "stage": 0}


def test_crash_tail_rejected_before_loading_previous_checkpoint(tmp_path, plan):
    train, _, _ = plan
    first = session(tmp_path, plan, FakeLearner("test-session", train, fail_at=3))
    with pytest.raises(RuntimeError, match="synthetic learner interruption"):
        first.advance_epoch(batch_size=2)
    assert first.learner.counter == 3
    report = first.report()
    assert report["last_checkpoint"]["state_sha256"] == report["initial_checkpoint"]["state_sha256"]
    assert report["uncommitted_recorded_optimizer_steps"] == 2
    restarted = FakeLearner("test-session", train)
    with pytest.raises(runner.SessionError, match="UNCOMMITTED_TEACHING_TAIL"):
        session(tmp_path, plan, restarted)
    assert restarted.restore_calls == 0 and restarted.counter == 0


def test_gradient_path_failure_is_incomplete_not_an_early_stop(tmp_path, plan):
    train, _, _ = plan
    current = session(tmp_path, plan, FakeLearner("test-session", train, gradients=False))
    for _ in range(8):
        current.advance_epoch(batch_size=2)
    report = current.report()
    assert report["allocation_finished"] is True
    assert report["observed_optimizer_steps"] == 112
    assert report["selected_checkpoint"] is None
    assert all(row["reason"] == "BINDING_GRADIENT_DELIVERY_INCOMPLETE"
               for row in report["development_curve"][3:])
    assert current.ledger.assistance() == "full"


def test_source_change_and_batch_size_change_are_rejected(tmp_path, plan):
    first = session(tmp_path, plan)
    first.advance_epoch(batch_size=2)
    with pytest.raises(runner.SessionError, match="BOUND_BATCH_SIZE_CHANGED"):
        first.advance_epoch(batch_size=1)
    train, dev, allocation = plan
    with pytest.raises(journal.JournalError, match="IDENTITY_MISMATCH"):
        runner.TrainingSession(FakeLearner("test-session", train), train, dev, "aligned",
            tmp_path / "session", "3" * 64, allocation, execution_mode="simulated")


def test_changed_committed_event_is_not_accepted_on_restart(tmp_path, plan):
    first = session(tmp_path, plan)
    first.advance_epoch(batch_size=2)
    with (first.events / "step-00000001.result.json").open("ab") as stream:
        stream.write(b"changed")
    with pytest.raises(journal.JournalError):
        session(tmp_path, plan)


def test_event_byte_cap_rejects_before_learner_update(tmp_path, plan, monkeypatch):
    current = session(tmp_path, plan)
    monkeypatch.setattr(runner, "EVENT_TOTAL_BYTE_LIMIT", 1)
    with pytest.raises(runner.SessionError, match="EVENT_TOTAL_BYTE_LIMIT"):
        current.advance_epoch(batch_size=2)
    assert current.learner.counter == 0
    assert list(current.events.iterdir()) == []


def test_module_has_no_tensor_provider_database_or_dataset_import():
    tree = ast.parse(Path(runner.__file__).read_text(encoding="utf-8"))
    forbidden = {"torch", "numpy", "sqlite3", "boto3", "botocore", "casformer", "cas_cjt", "data"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert not {name.name.split(".")[0] for name in node.names} & forbidden
        if isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] not in forbidden
