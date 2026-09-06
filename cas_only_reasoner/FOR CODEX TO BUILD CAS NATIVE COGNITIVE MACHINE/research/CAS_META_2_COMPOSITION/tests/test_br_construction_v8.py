"""Pure simulated control flow only: no models, real native stores or providers."""
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
import importlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace as NS

import pytest

from cas_meta2 import br_construction_v8 as b

JOB = "cas-meta2-20260906150000-1234abcd"


def plan():
    return {"schema": b.PLAN_SCHEMA, "job": JOB, "launch_enabled": True,
        "max_seconds": 600, "max_cost_usd": "4.00", "prelude_policy_units": 32768,
        "arm_policy_units": 8192, "binding": 0, "prelude": ["A", "B", "C", "R"],
        "arm_cjt": "C", "arm_expected_symbol": "L2", "seed": 7, "training": False,
        "native_execution": True, "max_image_bytes": 67108864,
        "source_sha": "a"*40, "instance_id": "i-" + "b"*17,
        "source_archive": {"sha256": "c"*64}, "source_manifest": {"sha256": "d"*64}}


def test_import_is_inert_and_plan_has_no_training():
    before = set(sys.modules)
    importlib.reload(b)
    assert not {"torch", "cas_cjt", "casformer", "boto3", "botocore"}.intersection(
        n.split(".")[0] for n in set(sys.modules) - before)
    assert b.validate_plan(plan(), JOB)["training"] is False


@pytest.mark.parametrize("field,value", [
    ("max_seconds", 601), ("max_seconds", True), ("max_cost_usd", "4.01"),
    ("prelude_policy_units", 32769), ("arm_policy_units", 8193), ("binding", 1),
    ("binding", False), ("prelude", ["A", "B", "C", "R", "C"]),
    ("arm_cjt", "R"), ("arm_expected_symbol", "L0"), ("seed", 8),
    ("training", True), ("native_execution", False), ("max_image_bytes", 67108865),
    ("source_sha", None), ("instance_id", 4), ("launch_enabled", 1),
])
def test_scope_change_refused(field, value):
    value_plan = plan()
    value_plan[field] = value
    with pytest.raises(b.ConstructionRefused):
        b.validate_plan(value_plan, JOB)


@pytest.mark.parametrize("platform,enable,job", [
    ("win32", "1", JOB), ("linux", "0", JOB), ("linux", "1", "wrong")])
def test_local_or_unbound_run_refused_before_import_or_files(tmp_path, monkeypatch, platform, enable, job):
    monkeypatch.setattr(b.sys, "platform", platform)
    monkeypatch.setenv("CAS_META2_RUN_BR_CONSTRUCTION", enable)
    monkeypatch.setenv("CAS_META2_AWS_JOB_ID", job)
    monkeypatch.setattr(b, "check_sources", lambda _: pytest.fail("source check reached before admission"))
    with pytest.raises(b.ConstructionRefused, match="BR_AWS_LINUX_EXPLICIT_JOB_REQUIRED"):
        b.run(tmp_path / "must_not_exist", job=JOB, plan_path="absent", plan_sha256="a"*64)
    assert list(tmp_path.iterdir()) == []


def test_existing_neural_import_refused(monkeypatch):
    monkeypatch.setattr(b.sys, "platform", "linux")
    monkeypatch.setenv("CAS_META2_RUN_BR_CONSTRUCTION", "1")
    monkeypatch.setenv("CAS_META2_AWS_JOB_ID", JOB)
    # A marker only, never a neural-library import.
    monkeypatch.setitem(sys.modules, "torch.synthetic_marker", NS())
    with pytest.raises(b.ConstructionRefused, match="BR_NEURAL_IMPORT_BEFORE_ADMISSION"):
        b.require_cloud_request(JOB)


def test_new_output_rejects_existing_outside_and_root(tmp_path, monkeypatch):
    monkeypatch.setattr(b, "ROOT", tmp_path)
    runs = tmp_path / "runs"
    runs.mkdir()
    existing = runs / "exists"
    existing.mkdir()
    for path in (runs, existing, tmp_path / "elsewhere", runs / ".." / "escape"):
        with pytest.raises(b.ConstructionRefused):
            b.new_output(path)
    assert b.new_output(runs / "new") == runs / "new"


@pytest.mark.parametrize("charge,spent,maximum", [
    (True, 0, 10), (-1, 0, 10), (1.0, 0, 10), (float("nan"), 0, 10),
    (11, 0, 10), (1, True, 10), (1, -1, 10), (1, 0, False)])
def test_invalid_or_excessive_plan_charge_refused(charge, spent, maximum):
    with pytest.raises(b.ConstructionRefused):
        b.charge_plan({"units": charge}, spent, maximum)


def test_charge_exact_ceiling_allowed():
    assert b.charge_plan({"units": 8}, 2, 10) == 10


def test_prelude_stops_on_first_refusal_without_repair_substitute(monkeypatch):
    calls = []
    def prepare(cjt, reference):
        calls.append(("prepare", cjt))
        return {"units": 2}
    def execute(cjt, reference, charge):
        calls.append(("execute", cjt))
        if cjt == "C":
            raise ValueError("synthetic ordinary C refusal")
        return {"reference": {"kind": "effect", "effect_id": cjt}}
    events = []
    monkeypatch.setattr(b.time, "monotonic", lambda: 1)
    with pytest.raises(ValueError, match="ordinary C refusal"):
        b.execute_sequence(NS(prepare=prepare, execute=execute), b.PRELUDE, {"kind": "observation"},
            maximum=8, deadline=2, record=lambda *args, **kw: events.append((args, kw)))
    assert calls == [(op, cjt) for cjt in ("A", "B", "C") for op in ("prepare", "execute")]
    assert [row[1]["cjt_id"] for row in events if row[0] == ("ORDINARY_NATIVE_RESULT",)] == ["A", "B"]


def test_plan_budget_refuses_before_execution(monkeypatch):
    monkeypatch.setattr(b.time, "monotonic", lambda: 1)
    backend = NS(prepare=lambda *_: {"units": 9}, execute=lambda *_: pytest.fail("overspend executed"))
    with pytest.raises(b.ConstructionRefused, match="BUDGET_EXHAUSTED"):
        b.execute_sequence(backend, ("C",), {}, maximum=8, deadline=2, record=lambda *a, **k: None)


def test_expired_deadline_refuses_before_prepare(monkeypatch):
    monkeypatch.setattr(b.time, "monotonic", lambda: 2)
    backend = NS(prepare=lambda *_: pytest.fail("expired plan prepared"))
    with pytest.raises(b.ConstructionRefused, match="DEADLINE"):
        b.execute_sequence(backend, ("C",), {}, maximum=8, deadline=2, record=lambda *a, **k: None)


def observed(values, content="L2", payload="a"*64):
    return {"values": values, "decoded_content": {"symbol": content}, "payload_sha256": payload}


def test_numeric_difference_is_not_claimed_as_task_correctness():
    result = b.compare_outputs(observed([[1.0, 2.0]]), observed([[1.0, 2.5]], payload="b"*64))
    assert result["numeric_values_equal"] is False
    assert result["max_absolute_difference"] == .5
    assert result["decoded_content_equal"] is True
    assert result["task_relevance_established"] is False
    assert result["whole_task_verifier_executed"] is False
    assert result["shape"] == [1, 2]


@pytest.mark.parametrize("left,right", [
    ([[1, 2]], [1, 2]), ([[1], [2, 3]], [[1], [2, 3]]), ([], []), (1, 1),
    ([True], [1]), ([float("nan")], [0]), ([float("inf")], [0]),
    (["1"], [1]), ([1e308], [-1e308])])
def test_malformed_numeric_contrast_refused(left, right):
    with pytest.raises(b.ConstructionRefused):
        b.compare_outputs(observed(left), observed(right))


@dataclass
class SyntheticHead:
    state_version: int


@pytest.fixture
def simulation(tmp_path, monkeypatch):
    """Replace native execution and cloud gates with explicitly synthetic fakes."""
    from cas_meta2.diagnostic_v8 import gpu
    from cas_meta2 import br_snapshot_v8, br_witness_v8
    events, backends = [], []
    options = {"setup_failure": False, "prelude_failure": False,
               "mismatch": None, "source_changed": False}
    monkeypatch.setattr(b, "ROOT", tmp_path)
    monkeypatch.setattr(b, "require_cloud_request", lambda _: events.append("synthetic_admission"))
    monkeypatch.setattr(gpu, "read_pinned", lambda *_: plan())
    monkeypatch.setattr(gpu, "reservation_binding", lambda _: {"synthetic": "reservation"})
    monkeypatch.setattr(gpu, "ec2_identity", lambda _: {"synthetic": "ec2"})
    source_calls = []
    def source_check(_):
        source_calls.append(True)
        if len(source_calls) > 1 and options["source_changed"]:
            raise ValueError("synthetic source mutation")
        return {"synthetic": "source"}
    monkeypatch.setattr(b, "check_sources", source_check)
    noop = lambda *_: None
    torch = NS(__version__="2.11.0+cu128", version=NS(cuda="12.8"),
        cuda=NS(device_count=lambda: 1, get_device_name=lambda _: "Synthetic RTX PRO 4500",
                manual_seed_all=noop), set_num_threads=noop, manual_seed=noop,
        use_deterministic_algorithms=noop, are_deterministic_algorithms_enabled=lambda: True,
        backends=NS(cudnn=NS(benchmark=False, deterministic=True, allow_tf32=False),
                    cuda=NS(matmul=NS(allow_tf32=False))))
    f = NS(torch=torch, validate_contract=lambda _: None)
    def frozen():
        if options["setup_failure"]:
            raise RuntimeError("synthetic missing published wheel")
        return NS(_cuda=lambda *_: "synthetic_cuda"), f

    class SyntheticBackend:
        def __init__(self, public, output, device, *, direct=True, arm=None):
            assert direct is True
            self.output, self.arm = Path(output), arm
            self.count = 4 if arm else 0
            self.audit = {"calls": 0}
            self.f = f
            self.closed = False
            self.native = NS(store=NS(next_tick=lambda: self.count+1, load_state=lambda: {"synthetic": True},
                trace_events=lambda: [{"synthetic": i} for i in range(self.count)]),
                coordinator=NS(restore_and_verify=lambda: NS(head=SyntheticHead(self.count),
                    state={"synthetic": True}, traces=[{"synthetic": i} for i in range(self.count)])))
            if arm is None:
                (self.output / "native.db").write_bytes(b"Opaque synthetic bytes; not a database.")
            backends.append(self)
            events.append("open:" + (arm or "prelude"))
        def input_reference(self, binding):
            assert binding == 0
            return {"kind": "observation", "slot": binding}
        def prepare(self, cjt, reference):
            return {"units": 5, "plan_digest": "synthetic"}
        def execute(self, cjt, reference, charge):
            events.append("execute:" + (self.arm or "prelude") + ":" + cjt)
            self.count += 1
            self.audit["calls"] += 1
            if self.arm is None and options["prelude_failure"] and cjt == "C":
                raise ValueError("synthetic ordinary C refusal with trace retained")
            return {"reference": {"kind": "effect", "effect_id": cjt + str(self.count)},
                    "native_receipt": {"synthetic": True}}
        def _effect_reference(self, key):
            return {"kind": "effect", "effect_id": key}
        def head(self):
            return {"synthetic": self.count}
        def identity(self):
            return {"synthetic": "frozen"}
        def close(self):
            self.closed = True
            events.append("close:" + (self.arm or "prelude"))

    monkeypatch.setitem(sys.modules, "cas_meta2.native", NS(NativeBackend=SyntheticBackend, _frozen=frozen))
    monkeypatch.setattr(b, "restored_backend", lambda public, database, output, device:
        SyntheticBackend(public, output, device, arm=Path(database).stem))
    def witness(backend, effects):
        events.append("witness:" + (backend.arm or "prelude"))
        return {"recovery": {"traces": [0]*4}, "next_tick": 5,
                "synthetic_mismatch": backend.arm if backend.arm == options["mismatch"] else None}
    monkeypatch.setattr(b, "collect_witness", witness)
    monkeypatch.setattr(br_witness_v8, "validate_before_state_pair", lambda left, right:
        {"ok": left == right, "reasons": [] if left == right else ["synthetic mismatch"]})
    def copy_image(source, expected, destination, **kw):
        assert all(backend.closed for backend in backends)
        assert kw["source_closed_self_contained"] is True
        destination.mkdir()
        for name in ("master.sqlite", "B.sqlite", "R.sqlite"):
            (destination / name).write_bytes(Path(source).read_bytes())
        events.append("copy_closed")
        return {"synthetic": True}
    monkeypatch.setattr(br_snapshot_v8, "copy_closed_snapshot", copy_image)
    monkeypatch.setattr(br_snapshot_v8, "_verified_image", lambda *args: events.append("verify_closed_image"))
    monkeypatch.setattr(b, "effect_output", lambda backend, _: observed([[1., 2. if backend.arm == "B" else 3.]]))
    return NS(output=tmp_path / "runs" / "synthetic", events=events, backends=backends,
              options=options, source_calls=source_calls,
              run=lambda: b.run(tmp_path / "runs" / "synthetic", job=JOB, plan_path="synthetic",
                                plan_sha256="e"*64))


def test_simulated_sequence_checks_both_before_states_before_either_arm_ticks(simulation):
    result = simulation.run()
    assert result["status"] == "BR_COMPONENT_EXECUTED"
    sequence = simulation.events
    first_arm = sequence.index("execute:B:C")
    assert sequence.index("witness:B") < first_arm
    assert sequence.index("witness:R") < first_arm
    assert sequence.index("close:prelude") < sequence.index("copy_closed") < sequence.index("open:B")
    assert [item for item in sequence if item.startswith("execute:")] == [
        "execute:prelude:A", "execute:prelude:B", "execute:prelude:C", "execute:prelude:R",
        "execute:B:C", "execute:R:C"]
    assert result["arms"]["B"]["remaining_policy_units"] == result["arms"]["R"]["remaining_policy_units"] == 8187
    assert len(simulation.source_calls) == 2
    assert all(backend.closed for backend in simulation.backends)
    assert result["task_conditioned_correctness"] is None
    for relative, expected in result["files_sha256"].items():
        assert sha256((simulation.output / relative).read_bytes()).hexdigest() == expected


@pytest.mark.parametrize("arm", ["B", "R"])
def test_simulated_restore_mismatch_never_executes_either_arm(simulation, arm):
    simulation.options["mismatch"] = arm
    result = simulation.run()
    assert result["status"] == "BR_CONSTRUCTION_REFUSED_OR_FAILED"
    assert not any(item in simulation.events for item in ("execute:B:C", "execute:R:C"))
    assert all(backend.closed for backend in simulation.backends)
    assert all(v["ok"] for v in result["postchecks"].values())


def test_simulated_prelude_refusal_retains_failure_trace_without_copy(simulation):
    simulation.options["prelude_failure"] = True
    result = simulation.run()
    assert result["status"] == "BR_CONSTRUCTION_REFUSED_OR_FAILED"
    assert "copy_closed" not in simulation.events
    assert "execute:prelude:R" not in simulation.events
    history = json.loads((simulation.output / "prelude/failure_native_history.json").read_bytes())
    assert len(history["traces"]) == 3
    assert (simulation.output / "prelude/native.db").is_file()
    assert len(simulation.source_calls) == 2


def test_admitted_simulated_setup_failure_is_receipted(simulation):
    simulation.options["setup_failure"] = True
    result = simulation.run()
    assert result["status"] == "BR_CONSTRUCTION_REFUSED_OR_FAILED"
    assert result["failure"]["message"] == "synthetic missing published wheel"
    assert (simulation.output / "construction_receipt.json").is_file()
    assert not simulation.backends
    assert len(simulation.source_calls) == 2


def test_simulated_failure_still_checks_new_source_identity(simulation):
    simulation.options.update(prelude_failure=True, source_changed=True)
    result = simulation.run()
    assert result["postchecks"]["source"]["ok"] is False
    assert result["postchecks"]["reservation"]["ok"] is True
    assert any(message.startswith("POSTCHECK:source:") for message in result["cleanup_errors"])
    assert result["status"] == "BR_CONSTRUCTION_REFUSED_OR_FAILED"
