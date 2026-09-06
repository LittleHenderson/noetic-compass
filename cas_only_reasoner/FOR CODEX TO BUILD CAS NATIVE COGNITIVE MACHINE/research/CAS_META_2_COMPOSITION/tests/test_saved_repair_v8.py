"""Pure control-flow tests. Fake results are not native or learning evidence."""
from contextlib import nullcontext
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
from types import SimpleNamespace, ModuleType
import ast
import sys
from pathlib import Path

import pytest
from cas_meta2 import saved_repair_v8 as core


def small_plan():
    wire = {key: [[1]] for key in ("route_quanta", "reasoning_step_quanta",
        "branch_quanta", "memory_read_quanta", "diagnostic_probe_quanta")}
    return {"compute_plan": wire, "plan_digest": core.digest(wire), "policy_units": 5}


class FakeOps:
    evidence_kind = "SIMULATED_NO_NATIVE_EXECUTION"

    def __init__(self, *, fail=None, fault=None):
        self.fail, self.fault = fail, fault
        self.calls, self.count, self.finalized = [], 0, False
        self.traces = [{"tick": i, "trace_digest": pin} for i, pin in enumerate(core.TRACE_DIGESTS, 1)]
        self.snapshots = 0

    def snapshot(self):
        self.snapshots += 1
        traces = deepcopy(self.traces)
        if self.snapshots > 1 and self.fault == "old_trace":
            traces[0]["trace_digest"] = "changed"
        head = {**core.HEAD, "state_version": 6 + len(traces) - 6}
        if self.snapshots == 1 and self.fault == "head":
            head["model_digest"] = "changed"
        return {"head": head, "traces": traces, "integrity": self.fault != "integrity",
            "identity": {"model": {"model_digest": core.HEAD["model_digest"]}}}

    def reconstruct(self):
        if self.fault == "reconstruction":
            raise ValueError("SIMULATED_RECONSTRUCTION_FAILURE")
        return {"full_frame_match": True, "frame": {"frame_digest": core.FRAME_DIGEST,
            "repair_id": core.REPAIR_ID}, "subgoal": {"cause_id": core.SUBGOAL_ID, "tick": 7},
            "pre_bias_version": 1}

    def plan(self, cjt):
        value = small_plan()
        if self.fault == "plan":
            value["policy_units"] += 1
        return value

    def forward_calls(self):
        return self.count

    def execute(self, cjt, expected, resume_id, plan):
        self.calls.append((cjt, expected, resume_id))
        if self.fault != "no_forward":
            self.count += 11  # Module hook entries, not 11 independent model calls.
        if self.fail == cjt:
            raise ValueError("SIMULATED_PRECOMMIT_FAILURE:" + cjt)
        tick = 7 if cjt == "C" else 8
        effect = {"producer_cjt_id": cjt, "tick": tick, "published_effect_id": "sim-" + cjt,
            "content_ref": {"sha256": "bound-output"}}
        self.traces.append({"tick": tick, "trace_digest": "SIMULATED",
            "verifier_receipts": [{"disposition": "ACCEPT"}],
            "published_effect_ids": [effect["published_effect_id"]], "compute_plan": plan["compute_plan"]})
        return {"tick": tick, "cjt_id": cjt, "accepted": True,
            "verifier_receipt": {"disposition": "ACCEPT"},
            "candidate_effect": {"content": {"symbol": expected}},
            **deepcopy(plan), "published_effect": effect, "output_sha256": "bound-output",
            "commit_receipt": {"published_effect_ids": [effect["published_effect_id"]]}}

    def resume_cause(self, child):
        assert child["cjt_id"] == "C"
        return {"SIMULATED": True, "parent_context_retained": True}

    def closure(self, child, resumed):
        assert child["cjt_id"] == "C" and resumed["cjt_id"] == "R"
        return {"verified": self.fault != "closure", "full_task_return_proven": False}

    def finalize(self):
        self.finalized = True
        return {"weights_unchanged": self.fault != "weights", "sources_unchanged": True,
            "protected_identities_unchanged": True, "errors": [],
            "gpu_forward_audit": {"calls": self.count, "counter_kind": "module_forward_pre_hook_entries"}}


def drive(ops):
    records = {}
    def record(name, value):
        assert name not in records
        records[name] = deepcopy(value)
    return core._drive(ops, record), records


def test_fake_two_call_success_is_not_full_task_or_learning():
    ops = FakeOps()
    result, records = drive(ops)
    assert result["status"] == "REPAIR_RESUMED" and result["repaired"] is True
    assert result["evidence_kind"] == "SIMULATED_NO_NATIVE_EXECUTION"
    assert result["native_call_attempts"] == result["returned_native_calls"] == 2
    assert result["completed_new_ticks"] == result["accepted_new_ticks"] == 2
    assert result["attempted_policy_units"] == result["committed_policy_units"] == 10
    assert ops.calls == [("C", "L2", None), ("R", "L1", core.REPAIR_ID)]
    assert result["claim_boundary"]["outer_caller_stack_restored"] is False
    assert result["claim_boundary"]["learning_proven"] is False
    assert records["attempt_07.json"]["returned"] is False
    assert records["attempt_07_finished.json"]["returned"] is True
    assert ops.finalized


@pytest.mark.parametrize("failed,attempted,committed", [("C", 1, 0), ("R", 2, 1)])
def test_precommit_failure_keeps_attempts_distinct_from_ticks(failed, attempted, committed):
    ops = FakeOps(fail=failed)
    result, records = drive(ops)
    assert result["status"] == "REPAIR_REFUSED" and not result["repaired"]
    assert len(ops.calls) == result["native_call_attempts"] == attempted
    assert result["returned_native_calls"] == result["completed_new_ticks"] == committed
    assert result["attempted_policy_units"] == attempted * 5
    assert result["committed_policy_units"] == committed * 5
    assert result["gpu_forward_audit"]["calls"] == attempted * 11
    assert result["failures"][0]["stage"] == "native_" + failed
    assert records["attempt_%02d_finished.json" % (7 if failed == "C" else 8)]["error"]
    assert ops.finalized


@pytest.mark.parametrize("fault", ["head", "integrity", "reconstruction", "plan", "old_trace",
    "no_forward", "closure", "weights"])
def test_fake_faults_never_become_success(fault):
    ops = FakeOps(fault=fault)
    result, _ = drive(ops)
    assert result["status"] == "REPAIR_REFUSED"
    assert result["failures"] and ops.finalized
    if fault in ("head", "integrity", "reconstruction", "plan"):
        assert not ops.calls


def test_deadline_stops_before_any_attempt():
    ops, times = FakeOps(), iter((0, 601, 602))
    result = core._drive(ops, lambda *a: None, clock=lambda: next(times))
    assert result["status"] == "REPAIR_REFUSED" and not ops.calls
    assert result["failures"][0]["message"] == "SAVED_REPAIR_DEADLINE"
    assert ops.finalized


@pytest.mark.parametrize("value", [True, -1, 1.0, "1", None, [1, False]])
def test_policy_units_require_nonnegative_integers(value):
    with pytest.raises(core.SavedRepairError):
        core._integer_sum(value)


def test_raw_payload_and_bound_artifact_hashes_are_different():
    payload = b"SIMULATED_OPAQUE_BYTES"
    raw_hash = sha256(payload).hexdigest()
    bound_hash = sha256(b"metadata-header\n" + payload).hexdigest()
    calls = []
    artifact = SimpleNamespace(artifact_id="sim-artifact", sha256=bound_hash, payload=payload,
        verify=lambda: calls.append("metadata-and-payload-verified"))
    result = core._artifact_evidence(artifact, {"artifact_id": "sim-artifact", "sha256": bound_hash})
    assert result == {"artifact_sha256": bound_hash, "payload_sha256": raw_hash, "payload_bytes": len(payload)}
    assert bound_hash != raw_hash and len(calls) == 1
    with pytest.raises(core.SavedRepairError, match="IDENTITY_MISMATCH"):
        core._artifact_evidence(artifact, {"artifact_id": "sim-artifact", "sha256": raw_hash})


def test_resume_preserves_original_context_and_operation_ids():
    calls = []
    ops = core._NativeOps.__new__(core._NativeOps)
    ops.parent_cause = SimpleNamespace(candidate_operation_ids=("^6",),
        goal_context={"original": "parent"})
    cause = SimpleNamespace(to_dict=lambda: {"SIMULATED_CAUSE": True})
    ops.native = SimpleNamespace(cause_from_effect=lambda *a, **k: (calls.append((a, k)) or cause))
    assert ops.resume_cause({"published_effect": {"published_effect_id": "child-effect"}}) == {"SIMULATED_CAUSE": True}
    assert calls == [(("child-effect",), {"tick": 8, "candidate_operation_ids": ("^6",),
        "goal_context": {"original": "parent"}})]


def test_local_run_refused_before_files_or_native_imports(monkeypatch, tmp_path):
    monkeypatch.setattr(core.platform, "system", lambda: "Windows")
    with pytest.raises(core.SavedRepairError, match="AWS_SAVED_REPAIR_ADMISSION_REQUIRED"):
        core.run(tmp_path / "never-created", tmp_path / "never-read")
    assert not (tmp_path / "never-created").exists()
    assert not {"torch", "cas_cjt", "cas_meta"}.intersection(sys.modules)


def test_pure_import_has_no_native_module_dependencies():
    tree = ast.parse(Path(core.__file__).read_text(encoding="utf-8"))
    top = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    names = {n.module.split(".")[0] for n in top if isinstance(n, ast.ImportFrom)}
    names |= {a.name.split(".")[0] for n in top if isinstance(n, ast.Import) for a in n.names}
    assert not names.intersection({"torch", "numpy", "sqlite3", "cas_cjt", "cas_meta"})


def test_readonly_hook_keeps_failed_proposal_without_replacing_output(monkeypatch):
    # All objects below are fake. The hook never calls a neural model or SQLite.
    artifacts = ModuleType("cas_cjt.artifacts")
    native_package = ModuleType("cas_cjt")
    native_package.__path__ = []
    payload = b"FAKE_OUTPUT"
    artifact = SimpleNamespace(sha256="BOUND", payload=payload, metadata={"simulated": True},
        kind="diagnostic-uncommitted-proposal", media_type="SIMULATED", encoding="SIMULATED")
    artifacts.encode_tensor = lambda value, **kw: ({"artifact_id": "SIMULATED", "sha256": "BOUND"}, artifact)
    monkeypatch.setitem(sys.modules, "cas_cjt", native_package)
    monkeypatch.setitem(sys.modules, "cas_cjt.artifacts", artifacts)
    @dataclass
    class Head:
        state_version: int = 6
    removed, hooks, calls = [], [], []
    def register(hook):
        hooks.append(hook)
        return SimpleNamespace(remove=lambda: removed.append(True))
    value = SimpleNamespace(numel=lambda: 8)
    value.detach = lambda: value
    proposal = SimpleNamespace(candidate_effect=value)
    def inference(**kw):
        calls.append(kw)
        assert hooks[0](None, (), proposal) is None
        raise ValueError("SIMULATED_REJECTED_BEFORE_COMMIT")
    ops = core._NativeOps.__new__(core._NativeOps)
    ops.identity = lambda: {"fixed": True}
    ops.pending_cause = SimpleNamespace(tick=7)
    ops.native = SimpleNamespace(store=SimpleNamespace(head=Head()),
        network=SimpleNamespace(node=lambda cjt: SimpleNamespace(register_forward_hook=register)),
        decoders={"C": SimpleNamespace(decode=lambda value: {"symbol": "L0"})},
        inference_tick=inference)
    ops.f = SimpleNamespace(torch=SimpleNamespace(no_grad=nullcontext))
    plan = small_plan()
    ops.prepared = ("C", deepcopy(plan), {"state_version": 6}, {"fixed": True})
    with pytest.raises(ValueError, match="SIMULATED_REJECTED_BEFORE_COMMIT"):
        ops.execute("C", "L2", None, plan)
    observed = ops.proposal_observation()
    assert observed["decoded_content"] == {"symbol": "L0"}
    assert observed["not_a_commit_receipt"] is True
    assert observed["additional_neural_forward"] is False
    assert len(calls) == 1 and removed == [True]
