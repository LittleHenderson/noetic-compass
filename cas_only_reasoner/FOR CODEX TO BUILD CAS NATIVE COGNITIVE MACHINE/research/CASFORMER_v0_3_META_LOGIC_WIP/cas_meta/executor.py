"""Bounded, single-owner calls over unchanged v0.2 inference transactions.

Native steps commit durably. This is NOT a parent rollback transaction, a
general policy interpreter, a hostile-Python sandbox, or crash-atomic recovery.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, fields
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import tempfile
from uuid import uuid4

from cas_cjt import validate_contract
from cas_cjt.artifacts import canonical_json
from cas_cjt.checkpoint import encode_module_checkpoint
from cas_cjt.control import RouteSettings
from cas_cjt.state import tensor_ref_from_mapping, verify_cause_identity
from cas_cjt.types import CausePacket

from .compiler import Program, compile_program
from .trace import validate_meta_events


class MetaRuntimeError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def digest(value) -> str:
    return sha256(canonical_json(value).encode("ascii")).hexdigest()


def cause_from_wire(value) -> CausePacket:
    validate_contract(value)
    arguments = {field.name: value[field.name] for field in fields(CausePacket)}
    if arguments["content_ref"] is not None:
        arguments["content_ref"] = tensor_ref_from_mapping(arguments["content_ref"])
    cause = CausePacket(**arguments)
    if not verify_cause_identity(cause):
        raise MetaRuntimeError("CAUSE_IDENTITY_MISMATCH")
    return cause


@dataclass(frozen=True)
class Limits:
    budget: int = 512
    max_depth: int = 8
    max_steps: int = 128
    max_input_elements: int = 256

    def __post_init__(self):
        caps = {"budget": 1_000_000, "max_depth": 32,
                "max_steps": 4096, "max_input_elements": 4096}
        for name, cap in caps.items():
            value = getattr(self, name)
            if type(value) is not int or not 1 <= value <= cap:
                raise MetaRuntimeError("INVALID_LIMIT")


@dataclass
class _Frame:
    call_id: str
    procedure: str
    path: str
    parent_id: str | None
    return_pc: int | None
    allowance: int
    cause: dict
    pc: int = 0
    spent: int = 0
    last_effect: str | None = None
    waiting: dict | None = None
    resume_repair_id: str | None = None


class Executor:
    """One owner, one stack, fixed weights, explicit checkpoint boundaries.

    Use `checkpoint`'s returned digest as a separately retained restart receipt.
    There is no automatic retry after a partly completed/failed native call.
    """

    def __init__(self, native, program: Program, cause, *, artifacts=(),
                 chain_id="fixed-chain", permitted_cjts=("A", "B", "C", "R"),
                 limits=Limits()):
        # Recompile immutable source: a manually constructed IR cannot bypass
        # parser admission, type checks, or scope checks.
        admitted = compile_program(program.source_json)
        if admitted != program:
            raise MetaRuntimeError("COMPILED_PROGRAM_MISMATCH")
        if not isinstance(chain_id, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", chain_id):
            raise MetaRuntimeError("INVALID_CHAIN_ID")
        self.native = native
        self.program = admitted
        self.limits = limits
        self.chain_id = chain_id
        self._run_id = uuid4().hex
        self.permitted_cjts = tuple(sorted(set(permitted_cjts)))
        self._artifacts = tuple(artifacts)
        self._events = []
        self._frames = []
        self._counter = 0
        self._steps = 0
        self._failed = False
        self.result_effect_id = None
        self._head = asdict(native.store.head)
        self._binding = self._current_binding()
        self._validate_program_binding()
        entry = admitted.by_name[admitted.entry]
        if cause.cause_kind.value != entry.input_type:
            raise MetaRuntimeError("ENTRY_TYPE_MISMATCH")
        self._validate_cause(cause)
        self._push(entry.name, "entry", cause, limits.budget, None, None)

    @property
    def frames(self):
        return tuple(deepcopy(asdict(frame)) for frame in self._frames)

    @property
    def events(self):
        return deepcopy(self._events)

    @property
    def done(self):
        return not self._frames and self.result_effect_id is not None

    @property
    def spent(self):
        return sum(event["units"] for event in self._events if event["kind"] == "CHARGE")

    def _current_binding(self):
        return {
            "program_digest": self.program.digest,
            "program_version": self.program.version,
            "software_digest": self.native.software_digest,
            "contracts": {k: v.contract_digest for k, v in self.native.contracts.items()},
            "decoders": {k: v.contract.decoder_digest for k, v in self.native.decoders.items()},
            "topology": self.native.network.topology_manifest(),
            "model_digest": self.native.state.model_digest,
            "limits": asdict(self.limits),
            "permitted_cjts": list(self.permitted_cjts),
            "chain_id": self.chain_id,
            "run_id": self._run_id,
        }

    def _validate_program_binding(self):
        allowed = set(self.permitted_cjts)
        if not allowed.issubset(self.native.state.by_cjt_id):
            raise MetaRuntimeError("UNKNOWN_CJT")
        for procedure in self.program.procedures:
            if not set(procedure.allowed_cjts).issubset(allowed):
                raise MetaRuntimeError("CJT_SCOPE_DENIED")
            for step in procedure.steps:
                if step.kind != "run":
                    continue
                contract = self.native.contracts.get(step.operation)
                if (contract is None or contract.ontology_status.value != "CANONICAL_ADMITTED"
                        or self.native.network.spec(step.cjt).operation_id != step.operation):
                    raise MetaRuntimeError("OPERATION_NOT_ADMITTED")
                labels = self.native.decoders[step.cjt].contract.labels
                if any(label is not None and label not in labels
                       for label in (step.expected, step.opposite, step.resume_expected)):
                    raise MetaRuntimeError("UNKNOWN_ORACLE_SYMBOL")

    def _validate_cause(self, cause):
        if len(canonical_json(cause.to_dict()).encode("ascii")) > 65_536:
            raise MetaRuntimeError("CAUSE_SIZE_EXCEEDED")
        if not verify_cause_identity(cause):
            raise MetaRuntimeError("CAUSE_IDENTITY_MISMATCH")
        if cause.memory_refs:
            raise MetaRuntimeError("EXTERNAL_MEMORY_NOT_SUPPORTED")
        if cause.content_ref is None:
            raise MetaRuntimeError("DENSE_INPUT_REQUIRED")
        shape = cause.content_ref.shape
        if (len(shape) != 3 or shape[0] != 1 or shape[1] < 1
                or shape[2] != self.native.network.config.d_model
                or shape[1] * shape[2] > self.limits.max_input_elements):
            raise MetaRuntimeError("INPUT_BOUND_EXCEEDED")
        if cause.tick != self.native.store.next_tick():
            raise MetaRuntimeError("NATIVE_TICK_MISMATCH")

    def _check_boundary(self):
        if self._failed:
            raise MetaRuntimeError("EXECUTOR_HALTED")
        if self._current_binding() != self._binding:
            raise MetaRuntimeError("RUNTIME_BINDING_MISMATCH")
        if asdict(self.native.store.head) != self._head:
            raise MetaRuntimeError("NATIVE_HEAD_MISMATCH")
        if encode_module_checkpoint(self.native.network).model_digest != self._binding["model_digest"]:
            raise MetaRuntimeError("MODEL_CHANGED")
        self._validate_stack()

    def _validate_stack(self):
        seen = set()
        for index, frame in enumerate(self._frames):
            if frame.call_id in seen or frame.procedure not in self.program.by_name:
                raise MetaRuntimeError("FRAME_IDENTITY_MISMATCH")
            seen.add(frame.call_id)
            if not 0 <= frame.spent <= frame.allowance <= self.limits.budget:
                raise MetaRuntimeError("FRAME_BUDGET_MISMATCH")
            proc = self.program.by_name[frame.procedure]
            if not 0 <= frame.pc <= len(proc.steps):
                raise MetaRuntimeError("RETURN_ADDRESS_MISMATCH")
            if index == 0:
                if frame.parent_id is not None or frame.return_pc is not None:
                    raise MetaRuntimeError("CALLER_MISMATCH")
                continue
            parent = self._frames[index - 1]
            waiting = parent.waiting
            if (waiting is None or waiting["child_id"] != frame.call_id
                    or frame.parent_id != parent.call_id
                    or waiting["pc"] != parent.pc or frame.return_pc != parent.pc):
                raise MetaRuntimeError("CALLER_MISMATCH")
            step = self.program.by_name[parent.procedure].steps[parent.pc]
            target = step.procedure if waiting["kind"] == "call" else step.repair
            if target != frame.procedure or step.path != frame.path:
                raise MetaRuntimeError("RETURN_ADDRESS_MISMATCH")
        if self._frames and self._frames[-1].waiting is not None:
            raise MetaRuntimeError("MISSING_CHILD_FRAME")

    def _emit(self, kind, **data):
        event = {"schema": "cas-meta-event/0.1", "seq": len(self._events),
                 "chain_id": self.chain_id, "program_digest": self.program.digest,
                 "kind": kind, "previous": self._events[-1]["digest"] if self._events else None,
                 **data}
        event["digest"] = digest(event)
        self._events.append(event)

    def _push(self, procedure, path, cause, allowance, parent_id, return_pc):
        if len(self._frames) >= self.limits.max_depth:
            raise MetaRuntimeError("CALL_DEPTH_EXCEEDED")
        if self._frames and allowance > self._frames[-1].allowance - self._frames[-1].spent:
            raise MetaRuntimeError("CHILD_ALLOWANCE_EXCEEDED")
        self._counter += 1
        frame = _Frame(f"{self.chain_id}:call:{self._run_id}:{self._counter}", procedure, path,
                       parent_id, return_pc, allowance, cause.to_dict())
        self._frames.append(frame)
        self._emit("ENTER", call_id=frame.call_id, parent_id=parent_id,
                   procedure=procedure, path=path, return_pc=return_pc, allowance=allowance)
        return frame.call_id

    def _charge(self, frame, materialized):
        components = {name: int(value.sum().item())
                      for name, value in materialized.routing.compute_plan.integer_fields}
        units = sum(components.values())
        if any(item.spent + units > item.allowance for item in self._frames):
            raise MetaRuntimeError("SHARED_BUDGET_EXHAUSTED")
        for item in self._frames:
            item.spent += units
        self._emit("CHARGE", call_id=frame.call_id, units=units, components=components,
                   plan_digest=digest(materialized.routing.compute_plan.to_authoritative_dict()))
        return components

    def _effect_cause(self, effect_id, original_cause):
        return self.native.cause_from_effect(
            effect_id, tick=self.native.store.next_tick(),
            candidate_operation_ids=original_cause.candidate_operation_ids,
            goal_context=original_cause.goal_context)

    def step(self):
        self._check_boundary()
        if self.done:
            return False
        if self._steps >= self.limits.max_steps:
            self._failed = True
            raise MetaRuntimeError("META_STEP_LIMIT")
        self._steps += 1
        try:
            self._step()
        except Exception:
            # Native commits and reservations may already exist. Never retry
            # or conceal them as a successful rollback.
            self._failed = True
            raise
        return True

    def _step(self):
        frame = self._frames[-1]
        procedure = self.program.by_name[frame.procedure]
        if frame.pc == len(procedure.steps):
            self._return(frame)
            return
        step = procedure.steps[frame.pc]
        cause = cause_from_wire(frame.cause)
        self._validate_cause(cause)
        if step.kind == "call":
            child_id = self._push(step.procedure, step.path, cause, step.allowance,
                                  frame.call_id, frame.pc)
            frame.waiting = {"child_id": child_id, "pc": frame.pc, "kind": "call"}
            self._emit("SUSPEND", call_id=frame.call_id, child_id=child_id, pc=frame.pc)
            return
        if step.cjt not in procedure.allowed_cjts or step.cjt not in self.permitted_cjts:
            raise MetaRuntimeError("CJT_SCOPE_DENIED")
        contract = self.native.contracts[step.operation]
        if cause.cause_kind not in contract.accepted_cause_kinds:
            raise MetaRuntimeError("OPERATION_INPUT_TYPE_MISMATCH")
        before = self.native.state
        supplied = tuple(a for a in self._artifacts
                         if not self.native.store.has_artifact(a.artifact_id, a.sha256))
        # Planning includes bounded routing/hash work; the ledger is a sum of
        # reserved native policy ceilings, NOT measured FLOPs or wall time.
        materialized = self.native.materializer.materialize(
            state=before, cause=cause, cjt_id=step.cjt,
            settings=RouteSettings(), supplied_artifacts=supplied)
        self._charge(frame, materialized)
        resume_id = frame.resume_repair_id
        result = self.native.inference_tick(
            cause=cause, cjt_id=step.cjt,
            expected_symbol=step.resume_expected if resume_id else step.expected,
            opposite_symbol=None if resume_id else step.opposite,
            resume_repair_id=resume_id, supplied_artifacts=supplied)
        self._head = asdict(self.native.store.head)
        actual_plan = result.materialized.routing.compute_plan.to_authoritative_dict()
        if actual_plan != materialized.routing.compute_plan.to_authoritative_dict():
            raise MetaRuntimeError("NATIVE_PLAN_MISMATCH")
        if self.native.state.model_digest != self._binding["model_digest"]:
            raise MetaRuntimeError("MODEL_CHANGED")
        if any(bias != self.native.state.by_cjt_id[name]
               for name, bias in before.by_cjt_id.items() if name != step.cjt):
            raise MetaRuntimeError("CROSS_CJT_BIAS_CHANGED")
        self._emit("NATIVE", call_id=frame.call_id, path=step.path,
                   cjt_id=step.cjt, tick=result.tick, accepted=result.accepted,
                   receipt_id=result.commit_receipt.receipt_id,
                   trace_id=result.commit_receipt.trace_id,
                   effect_ids=list(result.commit_receipt.published_effect_ids),
                   repair_id=None if result.repair_frame is None else result.repair_frame.repair_id,
                   repair_outcome_id=None if result.repair_outcome is None else result.repair_outcome.outcome_id,
                   head=self._head)
        if result.accepted and len(result.commit_receipt.published_effect_ids) == 1:
            frame.last_effect = result.commit_receipt.published_effect_ids[0]
            frame.cause = self._effect_cause(frame.last_effect, cause).to_dict()
            frame.resume_repair_id = None
            frame.pc += 1
        elif result.repair_subgoal is not None and step.repair and resume_id is None:
            child_id = self._push(step.repair, step.path, result.repair_subgoal,
                                  frame.allowance - frame.spent, frame.call_id, frame.pc)
            frame.waiting = {"child_id": child_id, "pc": frame.pc, "kind": "repair",
                             "repair_id": result.repair_frame.repair_id}
            self._emit("SUSPEND", call_id=frame.call_id, child_id=child_id,
                       pc=frame.pc, repair_id=result.repair_frame.repair_id)
        else:
            raise MetaRuntimeError("NATIVE_RESULT_NOT_RETURNABLE")

    def _return(self, child):
        if child.last_effect is None or child.resume_repair_id:
            raise MetaRuntimeError("UNACCEPTED_RETURN")
        effect = self.native.store.immutable_document("published_effects", child.last_effect)
        child_cause = cause_from_wire(child.cause)
        if child_cause.parent_effect_id != child.last_effect:
            raise MetaRuntimeError("RETURN_EFFECT_MISMATCH")
        if not effect:
            raise MetaRuntimeError("UNACCEPTED_RETURN")
        self._frames.pop()
        self._emit("RETURN", call_id=child.call_id, parent_id=child.parent_id,
                   return_pc=child.return_pc, effect_id=child.last_effect, spent=child.spent)
        if not self._frames:
            self.result_effect_id = child.last_effect
            return
        parent = self._frames[-1]
        waiting = parent.waiting
        if waiting["kind"] == "repair":
            original = cause_from_wire(parent.cause)
            parent.cause = self._effect_cause(child.last_effect, original).to_dict()
            parent.resume_repair_id = waiting["repair_id"]
        else:
            parent.cause = child.cause
            parent.last_effect = child.last_effect
            parent.pc += 1
        parent.waiting = None
        self._emit("RESUME", call_id=parent.call_id, child_id=child.call_id, pc=parent.pc)

    def run(self):
        self._check_boundary()
        while not self.done:
            self.step()
        self.validate_evidence()
        return self.result_effect_id

    def validate_evidence(self):
        self._check_boundary()
        validate_meta_events(self._events)
        previous = None
        for index, event in enumerate(self._events):
            wire = {k: v for k, v in event.items() if k != "digest"}
            if (event["seq"] != index or event["previous"] != previous
                    or digest(wire) != event["digest"]):
                raise MetaRuntimeError("META_TRACE_INVALID")
            previous = event["digest"]
            if event["kind"] == "NATIVE":
                receipt = self.native.store.receipt_by_id(event["receipt_id"])
                if (receipt["trace_id"] != event["trace_id"]
                        or receipt["published_effect_ids"] != event["effect_ids"]):
                    raise MetaRuntimeError("NATIVE_RECEIPT_MISMATCH")
        for trace in self.native.store.trace_events():
            validate_contract(trace)
        if not self.native.store.verify_integrity():
            raise MetaRuntimeError("NATIVE_INTEGRITY_FAILED")
        if self.spent > self.limits.budget:
            raise MetaRuntimeError("SHARED_BUDGET_EXHAUSTED")

    def checkpoint(self, path: Path) -> str:
        self._check_boundary()
        self.validate_evidence()
        # Initial supplied bytes must already have a native durable owner.
        for artifact in self._artifacts:
            if not self.native.store.has_artifact(artifact.artifact_id, artifact.sha256):
                raise MetaRuntimeError("CHECKPOINT_BEFORE_NATIVE_COMMIT")
        value = {"schema": "cas-meta-checkpoint/0.1", "binding": self._binding,
                 "head": self._head, "frames": list(self.frames), "events": self.events,
                 "counter": self._counter, "steps": self._steps,
                 "result_effect_id": self.result_effect_id,
                 "artifact_ids": [a.artifact_id for a in self._artifacts]}
        payload = canonical_json(value).encode("ascii")
        if len(payload) > 16 * 1024 * 1024:
            raise MetaRuntimeError("CHECKPOINT_TOO_LARGE")
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix=".meta-checkpoint-", dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, path)
        finally:
            if os.path.exists(name):
                os.unlink(name)
        return sha256(payload).hexdigest()

    @classmethod
    def restore(cls, native, program, path, *, expected_digest, chain_id,
                permitted_cjts=("A", "B", "C", "R"), limits=Limits()):
        path = Path(path)
        if path.stat().st_size > 16 * 1024 * 1024:
            raise MetaRuntimeError("CHECKPOINT_TOO_LARGE")
        payload = path.read_bytes()
        if sha256(payload).hexdigest() != expected_digest:
            raise MetaRuntimeError("CHECKPOINT_RECEIPT_MISMATCH")
        value = json.loads(payload)
        expected_keys = {"schema", "binding", "head", "frames", "events", "counter",
                         "steps", "result_effect_id", "artifact_ids"}
        if set(value) != expected_keys or value["schema"] != "cas-meta-checkpoint/0.1":
            raise MetaRuntimeError("CHECKPOINT_SCHEMA_MISMATCH")
        admitted = compile_program(program.source_json)
        if admitted != program:
            raise MetaRuntimeError("COMPILED_PROGRAM_MISMATCH")
        executor = cls.__new__(cls)
        executor.native, executor.program = native, admitted
        executor.chain_id, executor.limits = chain_id, limits
        executor.permitted_cjts = tuple(sorted(set(permitted_cjts)))
        executor._binding, executor._head = value["binding"], value["head"]
        executor._run_id = executor._binding["run_id"]
        executor._events, executor._counter = value["events"], value["counter"]
        executor._steps, executor.result_effect_id = value["steps"], value["result_effect_id"]
        executor._frames = [_Frame(**frame) for frame in value["frames"]]
        executor._artifacts = tuple(native.store.load_artifact(key) for key in value["artifact_ids"])
        executor._failed = False
        executor._validate_program_binding()
        executor._check_boundary()
        executor.validate_evidence()
        return executor
