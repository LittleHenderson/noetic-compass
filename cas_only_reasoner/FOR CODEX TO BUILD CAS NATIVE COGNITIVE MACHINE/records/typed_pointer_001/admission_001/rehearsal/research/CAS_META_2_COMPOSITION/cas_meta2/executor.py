"""Candidate named-value call stack over an explicit native backend.

This module is tensor-free. A fake backend tests control flow, NOT native CJTs.
Native commits are not rolled back if a later instruction fails. No automatic
retry, dynamic code evaluation, phase-based identity, or model mutation.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import re
from uuid import uuid4

from .ir import Limits as IRLimits, canonical_program, validate_program


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def digest(value):
    return sha256(canonical(value)).hexdigest()


class CompositionError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class ExecutionLimits:
    policy_units: int = 32768
    max_native_runs: int = 256
    max_events: int = 4096

    def __post_init__(self):
        for name, ceiling in (("policy_units", 1_000_000),
                              ("max_native_runs", 4096), ("max_events", 65536)):
            value = getattr(self, name)
            if type(value) is not int or not 1 <= value <= ceiling:
                raise CompositionError("INVALID_EXECUTION_LIMIT")


class CompositionExecutor:
    """Each frame keeps immutable named references to input or accepted Effects.

    Backend contract: identity(), head(), input_reference(binding),
    validate_reference(ref), prepare(cjt,ref)->plan with integer units and
    plan_digest, execute(cjt,ref,plan)->{reference,native_receipt}, and
    validate_receipt(receipt,ref). The backend alone owns native state writes.
    """

    def __init__(self, backend, program, *, binding, chain_id="meta2",
                 limits=None, ir_limits=None):
        if type(binding) is not int or binding not in (0, 1, 2):
            raise CompositionError("INVALID_OBSERVATION_BINDING")
        if type(chain_id) is not str or not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", chain_id):
            raise CompositionError("INVALID_CHAIN_ID")
        self.ir_limits = ir_limits or IRLimits()
        validate_program(program, self.ir_limits)
        self.program = json.loads(canonical_program(program))
        self.backend = backend
        self.limits = limits or ExecutionLimits()
        self.binding = binding
        self.chain_id = chain_id
        self.run_id = uuid4().hex
        self.program_digest = digest(self.program)
        self._identity = deepcopy(backend.identity())
        self._head = deepcopy(backend.head())
        self._events = []
        self._frames = []
        self._spent = 0
        self._runs = 0
        self._failed = False
        self.result_reference = None
        reference = backend.input_reference(binding)
        backend.validate_reference(reference)
        self._push(self.program["entry"], "entry", reference, None)

    @property
    def events(self):
        return deepcopy(self._events)

    @property
    def frames(self):
        return deepcopy(self._frames)

    @property
    def spent(self):
        return self._spent

    @property
    def done(self):
        return not self._frames and self.result_reference is not None and not self._failed

    def _emit(self, kind, **values):
        if len(self._events) >= self.limits.max_events:
            raise CompositionError("EVENT_LIMIT")
        event = {"schema": "cas-meta2-execution-event/0.1",
                 "seq": len(self._events), "chain_id": self.chain_id,
                 "run_id": self.run_id, "program_digest": self.program_digest,
                 "previous": self._events[-1]["digest"] if self._events else None,
                 "kind": kind, **deepcopy(values)}
        event["digest"] = digest(event)
        self._events.append(event)

    def _push(self, procedure, address, reference, return_to):
        proc = self.program["procedures"][procedure]
        frame = {"procedure": procedure, "address": address,
                 "call_id": self.run_id + ":" + address, "pc": 0,
                 "values": {proc["input"]: deepcopy(reference)},
                 "return_to": return_to}
        self._frames.append(frame)
        self._emit("ENTER", address=address, call_id=frame["call_id"],
                   procedure=procedure, input_reference=reference, return_to=return_to)

    def _boundary(self):
        if self._failed:
            raise CompositionError("EXECUTOR_HALTED")
        if self.backend.identity() != self._identity:
            raise CompositionError("RUNTIME_IDENTITY_CHANGED")
        if self.backend.head() != self._head:
            raise CompositionError("NATIVE_HEAD_CHANGED")
        if digest(self.program) != self.program_digest:
            raise CompositionError("PROGRAM_CHANGED")

    def step(self):
        self._boundary()
        if self.done:
            return False
        # Reserve enough evidence room BEFORE any native mutation.
        if len(self._events) + 3 > self.limits.max_events:
            self._failed = True
            raise CompositionError("EVENT_LIMIT")
        try:
            frame = self._frames[-1]
            proc = self.program["procedures"][frame["procedure"]]
            if frame["pc"] == len(proc["steps"]):
                reference = frame["values"][proc["return"]]
                self.backend.validate_reference(reference)
                if reference.get("kind") != "effect":
                    raise CompositionError("RETURN_REQUIRES_ACCEPTED_EFFECT")
                if len(self._frames) > 1:
                    parent = self._frames[-2]
                    if frame["return_to"] != {"address": parent["address"], "pc": parent["pc"],
                                               "output": self.program["procedures"][parent["procedure"]]
                                               ["steps"][parent["pc"]]["output"]}:
                        raise CompositionError("RETURN_ADDRESS_MISMATCH")
                self._emit("RETURN", address=frame["address"], call_id=frame["call_id"],
                           return_name=proc["return"], reference=reference,
                           return_to=frame["return_to"])
                self._frames.pop()
                if self._frames:
                    parent = self._frames[-1]
                    target = frame["return_to"]
                    if target != {"address": parent["address"], "pc": parent["pc"],
                                  "output": self.program["procedures"][parent["procedure"]]
                                  ["steps"][parent["pc"]]["output"]}:
                        raise CompositionError("RETURN_ADDRESS_MISMATCH")
                    parent["values"][target["output"]] = deepcopy(reference)
                    parent["pc"] += 1
                    self._emit("RESUME", address=parent["address"],
                               child_address=frame["address"], pc=parent["pc"])
                else:
                    self.result_reference = deepcopy(reference)
                return True
            step = proc["steps"][frame["pc"]]
            reference = frame["values"][step["input"]]
            self.backend.validate_reference(reference)
            address = frame["address"] + "/" + str(frame["pc"])
            if step["kind"] == "CALL":
                target = {"address": frame["address"], "pc": frame["pc"],
                          "output": step["output"]}
                self._emit("SUSPEND", address=frame["address"], pc=frame["pc"],
                           child_address=address, input_name=step["input"])
                self._push(step["procedure"], address, reference, target)
                return True
            if step["cjt_id"] not in proc["allowed_cjts"]:
                raise CompositionError("CJT_SCOPE_DENIED")
            if self._runs >= self.limits.max_native_runs:
                raise CompositionError("NATIVE_RUN_LIMIT")
            plan = self.backend.prepare(step["cjt_id"], deepcopy(reference))
            # Planning is read-only. Detect a changed model, source, program, or
            # native head before making a reservation or allowing any write.
            self._boundary()
            if (type(plan) is not dict or "units" not in plan
                    or type(plan.get("plan_digest")) is not str
                    or re.fullmatch(r"[0-9a-f]{64}", plan["plan_digest"]) is None):
                raise CompositionError("INVALID_NATIVE_PLAN")
            units = plan["units"]
            if type(units) is not int or units < 1:
                raise CompositionError("INVALID_NATIVE_PLAN_CHARGE")
            if self._spent + units > self.limits.policy_units:
                raise CompositionError("SHARED_POLICY_BUDGET_EXHAUSTED")
            self._spent += units
            self._runs += 1
            self._emit("CHARGE", address=address, units=units,
                       plan_digest=plan["plan_digest"])
            result = self.backend.execute(step["cjt_id"], deepcopy(reference), plan)
            self._head = deepcopy(self.backend.head())
            if self.backend.identity() != self._identity:
                raise CompositionError("RUNTIME_IDENTITY_CHANGED")
            accepted = result["reference"]
            self.backend.validate_reference(accepted)
            if accepted.get("kind") != "effect":
                raise CompositionError("RUN_REQUIRES_ACCEPTED_EFFECT")
            self.backend.validate_receipt(result["native_receipt"], accepted)
            frame["values"][step["output"]] = deepcopy(accepted)
            self._emit("NATIVE", address=address, call_id=frame["call_id"],
                       cjt_id=step["cjt_id"], input_name=step["input"],
                       output_name=step["output"], input_reference=reference,
                       output_reference=accepted, native_receipt=result["native_receipt"])
            frame["pc"] += 1
            return True
        except Exception:
            self._failed = True
            raise

    def run(self):
        while not self.done:
            self.step()
        self.validate_evidence()
        return deepcopy(self.result_reference)

    def validate_evidence(self):
        self._boundary()
        if not self.done:
            raise CompositionError("INCOMPLETE_EVIDENCE")
        previous = None
        charge = 0
        native_runs = 0
        base = {"schema", "seq", "chain_id", "run_id", "program_digest", "previous", "kind", "digest"}
        fields = {
            "ENTER": {"address", "call_id", "procedure", "input_reference", "return_to"},
            "SUSPEND": {"address", "pc", "child_address", "input_name"},
            "CHARGE": {"address", "units", "plan_digest"},
            "NATIVE": {"address", "call_id", "cjt_id", "input_name", "output_name",
                       "input_reference", "output_reference", "native_receipt"},
            "RETURN": {"address", "call_id", "return_name", "reference", "return_to"},
            "RESUME": {"address", "child_address", "pc"},
        }
        if len(self._events) > self.limits.max_events:
            raise CompositionError("EVENT_LIMIT")
        for index, event in enumerate(self._events):
            if (type(event) is not dict or type(event.get("kind")) is not str
                    or event["kind"] not in fields or set(event) != base | fields[event["kind"]]
                    or event["schema"] != "cas-meta2-execution-event/0.1"):
                raise CompositionError("EVENT_SCHEMA_FAILED")
            wire = {key: value for key, value in event.items() if key != "digest"}
            if (type(event["seq"]) is not int or event["seq"] != index or event["previous"] != previous
                    or event["program_digest"] != self.program_digest
                    or event["run_id"] != self.run_id
                    or event["chain_id"] != self.chain_id or digest(wire) != event["digest"]):
                raise CompositionError("EVENT_INTEGRITY_FAILED")
            previous = event["digest"]
            if event["kind"] == "CHARGE":
                if (type(event["units"]) is not int or event["units"] < 1
                        or type(event["plan_digest"]) is not str
                        or re.fullmatch(r"[0-9a-f]{64}", event["plan_digest"]) is None):
                    raise CompositionError("INVALID_NATIVE_PLAN_CHARGE")
                charge += event["units"]
            if event["kind"] == "NATIVE":
                native_runs += 1
                self.backend.validate_reference(event["input_reference"])
                self.backend.validate_reference(event["output_reference"])
                self.backend.validate_receipt(event["native_receipt"], event["output_reference"])
        # Replay the admitted program, not a guessed graph reconstructed from
        # the recorded events. A valid hash chain alone cannot prove execution.
        cursor = 0

        def take(kind, expected):
            nonlocal cursor
            if cursor >= len(self._events):
                raise CompositionError("EVENT_SEQUENCE_MISMATCH")
            event = self._events[cursor]
            cursor += 1
            if event["kind"] != kind or any(event.get(key) != value for key, value in expected.items()):
                raise CompositionError("EVENT_PROGRAM_MISMATCH")
            return event

        def replay(name, address, reference, return_to):
            proc = self.program["procedures"][name]
            call_id = self.run_id + ":" + address
            take("ENTER", {"address": address, "call_id": call_id, "procedure": name,
                           "input_reference": reference, "return_to": return_to})
            self.backend.validate_reference(reference)
            values = {proc["input"]: deepcopy(reference)}
            for pc, step in enumerate(proc["steps"]):
                source = values[step["input"]]
                location = address + "/" + str(pc)
                if step["kind"] == "CALL":
                    take("SUSPEND", {"address": address, "pc": pc, "child_address": location,
                                     "input_name": step["input"]})
                    result = replay(step["procedure"], location, source,
                                    {"address": address, "pc": pc, "output": step["output"]})
                    take("RESUME", {"address": address, "child_address": location, "pc": pc + 1})
                else:
                    reservation = take("CHARGE", {"address": location})
                    native = take("NATIVE", {"address": location, "call_id": call_id,
                                             "cjt_id": step["cjt_id"], "input_name": step["input"],
                                             "output_name": step["output"], "input_reference": source})
                    result = native["output_reference"]
                    receipt = native["native_receipt"]
                    if (result.get("kind") != "effect" or step["cjt_id"] not in proc["allowed_cjts"]
                            or type(receipt) is not dict or type(receipt.get("units")) is not int
                            or receipt["units"] != reservation["units"]
                            or receipt.get("plan_digest") != reservation["plan_digest"]):
                        raise CompositionError("NATIVE_RESERVATION_MISMATCH")
                values[step["output"]] = deepcopy(result)
            result = values[proc["return"]]
            if result.get("kind") != "effect":
                raise CompositionError("RETURN_REQUIRES_ACCEPTED_EFFECT")
            take("RETURN", {"address": address, "call_id": call_id, "return_name": proc["return"],
                            "reference": result, "return_to": return_to})
            return deepcopy(result)

        initial = self.backend.input_reference(self.binding)
        self.backend.validate_reference(initial)
        replayed_result = replay(self.program["entry"], "entry", initial, None)
        if cursor != len(self._events) or replayed_result != self.result_reference:
            raise CompositionError("EVENT_RESULT_MISMATCH")
        if (charge != self._spent or native_runs != self._runs or self._spent > self.limits.policy_units
                or native_runs > self.limits.max_native_runs):
            raise CompositionError("ACCOUNTING_MISMATCH")
        return {"event_count": len(self._events), "native_runs": native_runs,
                "policy_units_reserved": charge,
                "event_head": previous, "runtime_identity": deepcopy(self._identity),
                "native_head": deepcopy(self._head), "complete": self.done,
                "limits": asdict(self.limits)}
