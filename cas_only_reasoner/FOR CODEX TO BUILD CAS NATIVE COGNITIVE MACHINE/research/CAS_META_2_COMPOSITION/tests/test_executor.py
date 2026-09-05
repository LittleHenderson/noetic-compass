"""Pure mocked-backend control tests. These are NOT native-CJT evidence."""

from copy import deepcopy

import pytest

from cas_meta2.executor import CompositionError, CompositionExecutor, ExecutionLimits, digest
from cas_meta2.ir import IRValidationError, SCHEMA


pytestmark = pytest.mark.not_gpu


def nested_program():
    return {"schema": SCHEMA, "entry": "main", "procedures": {
        "main": {"input": "arg", "allowed_cjts": ["A", "B", "C"], "steps": [
            {"kind": "RUN", "cjt_id": "A", "input": "arg", "output": "v0"},
            {"kind": "CALL", "procedure": "p0", "input": "v0", "output": "v1"},
            {"kind": "RUN", "cjt_id": "A", "input": "arg", "output": "v2"},
            {"kind": "CALL", "procedure": "p0", "input": "v0", "output": "v3"}], "return": "v1"},
        "p0": {"input": "arg", "allowed_cjts": ["B", "C"], "steps": [
            {"kind": "RUN", "cjt_id": "B", "input": "arg", "output": "v0"},
            {"kind": "CALL", "procedure": "p1", "input": "v0", "output": "v1"}], "return": "v1"},
        "p1": {"input": "arg", "allowed_cjts": ["C"], "steps": [
            {"kind": "RUN", "cjt_id": "C", "input": "arg", "output": "v0"}], "return": "v0"}}}


class MockBackend:
    """No arrays, models, tensors or native code; IDs describe fake Effects."""

    def __init__(self):
        self._identity = {"model_digest": "model-v1", "source_digest": "source-v1", "contracts": "contracts-v1"}
        self._head = {"revision": 0, "digest": digest("mock-genesis")}
        self.references = {f"input:{i}": {"kind": "input", "id": f"input:{i}", "sha256": digest(["input", i])}
                           for i in range(3)}
        self.receipts, self.executions = {}, []
        self.prepare_hook = None
        self.fail_after_write = False
        self.units = 7
        self.return_input = False
        self.forge_output = False
        self.forge_receipt = False

    def identity(self):
        return deepcopy(self._identity)

    def head(self):
        return deepcopy(self._head)

    def input_reference(self, binding):
        return deepcopy(self.references[f"input:{binding}"])

    def validate_reference(self, reference):
        if type(reference) is not dict or reference.get("id") not in self.references:
            raise CompositionError("MOCK_MISSING_REFERENCE")
        if reference != self.references[reference["id"]]:
            raise CompositionError("MOCK_FORGED_REFERENCE")

    def prepare(self, cjt, reference):
        self.validate_reference(reference)
        if cjt not in ("A", "B", "C"):
            raise CompositionError("MOCK_SCOPE_DENIED")
        plan = {"units": self.units, "plan_digest": digest([cjt, reference, self._head])}
        if self.prepare_hook:
            self.prepare_hook(self)
        return plan

    def execute(self, cjt, reference, plan):
        self.validate_reference(reference)
        index = len(self.executions)
        self.executions.append({"cjt": cjt, "input": deepcopy(reference), "plan": deepcopy(plan)})
        effect = {"kind": "effect", "id": f"effect:{index}", "sha256": digest([cjt, reference, index])}
        self.references[effect["id"]] = deepcopy(effect)
        receipt = {"receipt_id": f"receipt:{index}", "trace_id": f"trace:{index}",
                   "published_effect_ids": [effect["id"]], "units": plan["units"], "plan_digest": plan["plan_digest"]}
        self.receipts[receipt["receipt_id"]] = deepcopy(receipt)
        self._head = {"revision": index + 1, "digest": digest(receipt)}
        if self.fail_after_write:
            raise CompositionError("MOCK_FAILED_AFTER_WRITE")
        if self.return_input:
            effect = self.input_reference(0)
        if self.forge_output:
            effect["sha256"] = "wrong"
        if self.forge_receipt:
            receipt["trace_id"] = "invented"
        return {"reference": effect, "native_receipt": receipt}

    def validate_receipt(self, receipt, reference):
        if type(receipt) is not dict or receipt.get("receipt_id") not in self.receipts:
            raise CompositionError("MOCK_MISSING_RECEIPT")
        if (receipt != self.receipts[receipt["receipt_id"]]
                or receipt["published_effect_ids"] != [reference["id"]]):
            raise CompositionError("MOCK_FORGED_RECEIPT")


def finished():
    backend = MockBackend()
    executor = CompositionExecutor(backend, nested_program(), binding=2)
    executor.run()
    return backend, executor


def reseal(events):
    """Test helper: hashes cannot replace source-semantic validation."""
    previous = None
    for index, event in enumerate(events):
        event["seq"] = index
        event["previous"] = previous
        event["digest"] = digest({key: value for key, value in event.items() if key != "digest"})
        previous = event["digest"]


def test_mock_nested_calls_reuse_earlier_effect_and_return_not_last():
    backend, executor = finished()
    assert [row["cjt"] for row in backend.executions] == ["A", "B", "C", "A", "B", "C"]
    assert backend.executions[1]["input"]["id"] == backend.executions[4]["input"]["id"] == "effect:0"
    assert backend.executions[0]["input"]["id"] == "input:2"
    assert executor.result_reference["id"] == "effect:2"
    assert executor.result_reference["id"] != "effect:5"
    report = executor.validate_evidence()
    assert report["native_runs"] == 6
    assert report["policy_units_reserved"] == 42
    assert report["complete"]
    assert executor.frames == []
    assert executor.step() is False


def test_mock_three_frames_keep_exact_return_positions():
    backend = MockBackend()
    executor = CompositionExecutor(backend, nested_program(), binding=0)
    for _ in range(4):
        executor.step()
    frames = executor.frames
    assert [f["procedure"] for f in frames] == ["main", "p0", "p1"]
    assert [f["pc"] for f in frames] == [1, 1, 0]
    assert frames[-1]["return_to"] == {"address": "entry/1", "pc": 1, "output": "v1"}
    executor.step()  # C
    executor.step()  # return C into its exact B caller
    assert [f["pc"] for f in executor.frames] == [1, 2]
    executor.step()  # return worker into main
    assert executor.frames[0]["pc"] == 2
    assert executor.frames[0]["values"]["v1"]["id"] == "effect:2"


def test_mock_wrong_return_address_halts_before_parent_changes():
    backend = MockBackend()
    executor = CompositionExecutor(backend, nested_program(), binding=0)
    for _ in range(5):
        executor.step()
    executor._frames[-1]["return_to"]["pc"] = 0
    before = deepcopy(executor._frames[:-1])
    with pytest.raises(CompositionError, match="RETURN_ADDRESS_MISMATCH"):
        executor.step()
    assert executor._frames[:-1] == before
    assert len(backend.executions) == 3
    with pytest.raises(CompositionError, match="EXECUTOR_HALTED"):
        executor.step()


@pytest.mark.parametrize("which", ["model_digest", "source_digest", "contracts"])
def test_mock_identity_change_before_step_prevents_writes(which):
    backend = MockBackend()
    executor = CompositionExecutor(backend, nested_program(), binding=0)
    backend._identity[which] = "changed"
    with pytest.raises(CompositionError, match="RUNTIME_IDENTITY_CHANGED"):
        executor.step()
    assert backend.executions == []


def test_mock_head_or_program_change_before_step_prevents_writes():
    for change in ("head", "program"):
        backend = MockBackend()
        executor = CompositionExecutor(backend, nested_program(), binding=0)
        if change == "head":
            backend._head["revision"] = 4
        else:
            executor.program["procedures"]["main"]["steps"][0]["cjt_id"] = "B"
        with pytest.raises(CompositionError, match="NATIVE_HEAD_CHANGED|PROGRAM_CHANGED"):
            executor.step()
        assert backend.executions == []


@pytest.mark.parametrize("change", ["head", "model", "source"])
def test_mock_prepare_must_be_read_only_before_reservation_and_write(change):
    backend = MockBackend()
    executor = CompositionExecutor(backend, nested_program(), binding=0)

    def mutate(value):
        if change == "head":
            value._head["revision"] += 1
        else:
            value._identity[change + "_digest"] = "changed"

    backend.prepare_hook = mutate
    with pytest.raises(CompositionError, match="NATIVE_HEAD_CHANGED|RUNTIME_IDENTITY_CHANGED"):
        executor.step()
    assert executor.spent == 0
    assert backend.executions == []
    assert all(e["kind"] != "CHARGE" for e in executor.events)


@pytest.mark.parametrize("kind", ["missing", "forged"])
def test_mock_missing_and_forged_input_reference_are_rejected(kind):
    backend = MockBackend()
    executor = CompositionExecutor(backend, nested_program(), binding=0)
    if kind == "missing":
        del backend.references["input:0"]
    else:
        executor._frames[0]["values"]["arg"]["sha256"] = "invented"
    with pytest.raises(CompositionError, match="MOCK_MISSING_REFERENCE|MOCK_FORGED_REFERENCE"):
        executor.step()
    assert backend.executions == []


def test_mock_scope_failure_never_reaches_backend():
    backend = MockBackend()
    program = nested_program()
    program["procedures"]["main"]["steps"][0]["cjt_id"] = "R"
    with pytest.raises(IRValidationError, match="CJT_SCOPE_DENIED"):
        CompositionExecutor(backend, program, binding=0)
    assert backend.executions == []


@pytest.mark.parametrize("units", [0, -1, True, 2.5])
def test_mock_invalid_compute_plan_charge_is_rejected_before_writes(units):
    backend = MockBackend()
    backend.units = units
    executor = CompositionExecutor(backend, nested_program(), binding=0)
    with pytest.raises(CompositionError, match="INVALID_NATIVE_PLAN_CHARGE"):
        executor.step()
    assert executor.spent == 0
    assert backend.executions == []


def test_mock_budget_limit_prevents_next_native_write_and_does_not_refund():
    backend = MockBackend()
    executor = CompositionExecutor(backend, nested_program(), binding=0,
                                   limits=ExecutionLimits(policy_units=13))
    executor.step()
    executor.step()
    with pytest.raises(CompositionError, match="SHARED_POLICY_BUDGET_EXHAUSTED"):
        executor.step()
    assert len(backend.executions) == 1
    assert executor.spent == 7


def test_mock_run_limit_and_event_room_are_reserved_before_writes():
    for limits, code in ((ExecutionLimits(max_native_runs=1), "NATIVE_RUN_LIMIT"),
                         (ExecutionLimits(max_events=3), "EVENT_LIMIT")):
        backend = MockBackend()
        executor = CompositionExecutor(backend, nested_program(), binding=0, limits=limits)
        with pytest.raises(CompositionError, match=code):
            executor.run()
        assert len(backend.executions) <= (1 if code == "NATIVE_RUN_LIMIT" else 0)


def test_mock_failure_after_native_write_is_not_rolled_back_or_retried():
    backend = MockBackend()
    backend.fail_after_write = True
    executor = CompositionExecutor(backend, nested_program(), binding=0)
    with pytest.raises(CompositionError, match="MOCK_FAILED_AFTER_WRITE"):
        executor.step()
    assert backend.head()["revision"] == 1
    assert executor.spent == 7
    assert "effect:0" in backend.references
    with pytest.raises(CompositionError, match="EXECUTOR_HALTED"):
        executor.run()
    assert len(backend.executions) == 1


@pytest.mark.parametrize("attribute,code", [("return_input", "RUN_REQUIRES_ACCEPTED_EFFECT"),
                                            ("forge_output", "MOCK_FORGED_REFERENCE"),
                                            ("forge_receipt", "MOCK_FORGED_RECEIPT")])
def test_mock_native_result_must_be_existing_accepted_effect_with_receipt(attribute, code):
    backend = MockBackend()
    setattr(backend, attribute, True)
    executor = CompositionExecutor(backend, nested_program(), binding=0)
    with pytest.raises(CompositionError, match=code):
        executor.step()
    assert len(backend.executions) == 1
    assert executor.spent == 7
    assert executor.frames[0]["pc"] == 0


def test_mock_partial_events_are_not_complete_evidence():
    executor = CompositionExecutor(MockBackend(), nested_program(), binding=0)
    executor.step()
    with pytest.raises(CompositionError, match="INCOMPLETE_EVIDENCE"):
        executor.validate_evidence()


def test_mock_events_and_frames_are_detached():
    executor = CompositionExecutor(MockBackend(), nested_program(), binding=0)
    events, frames = executor.events, executor.frames
    events[0]["procedure"] = "changed"
    frames[0]["values"]["arg"]["id"] = "invented"
    executor.run()
    assert executor.events[0]["procedure"] == "main"


def test_mock_functional_addresses_repeat_but_runtime_ids_do_not():
    _, first = finished()
    _, second = finished()
    assert [e["address"] for e in first.events] == [e["address"] for e in second.events]
    assert first.run_id != second.run_id
    assert first.events[0]["call_id"] != second.events[0]["call_id"]


def test_mock_plain_hash_tampering_rejected():
    _, executor = finished()
    executor._events[0]["procedure"] = "other"
    with pytest.raises(CompositionError, match="EVENT_INTEGRITY_FAILED"):
        executor.validate_evidence()


@pytest.mark.parametrize("change", ["kind", "extra", "address", "procedure", "return", "resume", "input_name", "input_ref", "cjt"])
def test_mock_resealed_events_still_must_match_the_admitted_program(change):
    backend, executor = finished()
    if change == "kind":
        executor._events[0]["kind"] = "INVENTED"
    elif change == "extra":
        executor._events[0]["authority"] = "all"
    elif change in ("address", "procedure"):
        executor._events[0][change] = "wrong"
    elif change == "return":
        executor._events[-1]["reference"] = deepcopy(backend.references["effect:5"])
    elif change == "resume":
        next(e for e in executor._events if e["kind"] == "RESUME")["pc"] = 0
    else:
        native = next(e for e in executor._events if e["kind"] == "NATIVE")
        if change == "input_name":
            native["input_name"] = "v1"
        elif change == "input_ref":
            native["input_reference"] = backend.input_reference(1)
        else:
            native["cjt_id"] = "C"
    reseal(executor._events)
    with pytest.raises(CompositionError, match="EVENT_SCHEMA_FAILED|EVENT_PROGRAM_MISMATCH"):
        executor.validate_evidence()


@pytest.mark.parametrize("field,value", [("units", 8), ("plan_digest", "0" * 64)])
def test_mock_charge_is_bound_to_native_receipt_even_with_resealed_events(field, value):
    _, executor = finished()
    charge = next(e for e in executor._events if e["kind"] == "CHARGE")
    charge[field] = value
    reseal(executor._events)
    with pytest.raises(CompositionError, match="NATIVE_RESERVATION_MISMATCH"):
        executor.validate_evidence()


def test_mock_resealed_reordered_or_omitted_events_are_rejected():
    for change in ("swap", "omit"):
        _, executor = finished()
        if change == "swap":
            executor._events[1], executor._events[2] = executor._events[2], executor._events[1]
        else:
            del executor._events[1]
        reseal(executor._events)
        with pytest.raises(CompositionError, match="EVENT_PROGRAM_MISMATCH"):
            executor.validate_evidence()


def test_mock_result_must_be_the_replayed_selected_return():
    backend, executor = finished()
    executor.result_reference = deepcopy(backend.references["effect:5"])
    with pytest.raises(CompositionError, match="EVENT_RESULT_MISMATCH"):
        executor.validate_evidence()


def test_mock_identity_change_inside_execute_halts_without_accepting_result():
    backend = MockBackend()
    original = backend.execute

    def changed(cjt, reference, plan):
        value = original(cjt, reference, plan)
        backend._identity["model_digest"] = "changed"
        return value

    backend.execute = changed
    executor = CompositionExecutor(backend, nested_program(), binding=0)
    with pytest.raises(CompositionError, match="RUNTIME_IDENTITY_CHANGED"):
        executor.step()
    assert backend.head()["revision"] == 1
    assert executor.frames[0]["pc"] == 0
    assert executor.spent == 7


@pytest.mark.parametrize("binding", [-1, 3, True, "0", None])
def test_mock_invalid_binding_rejected_before_backend_work(binding):
    backend = MockBackend()
    with pytest.raises(CompositionError, match="INVALID_OBSERVATION_BINDING"):
        CompositionExecutor(backend, nested_program(), binding=binding)
    assert backend.executions == []
