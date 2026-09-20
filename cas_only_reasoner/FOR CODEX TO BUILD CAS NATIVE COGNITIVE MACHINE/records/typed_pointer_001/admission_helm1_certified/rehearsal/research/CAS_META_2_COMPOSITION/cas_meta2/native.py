"""AWS-only native adapter and independent stored-result examination.

The new call stack chooses among named references. Every RUN still enters the
unchanged META-0 single-RUN executor and unchanged v0.2 transaction machinery.
The private reference instead calls v0.2 directly. All neural weights are frozen.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import struct
import sys
import time

from .codec import validate_action, validate_public
from .curriculum import check_native_topology, graph_signature
from .executor import CompositionError, CompositionExecutor, canonical, digest
from .ir import validate_program

ROOT = Path(__file__).resolve().parents[1]
MAX_CASE_BYTES = 64 * 1024 * 1024
EXPECTED = {"A": "L1", "B": "L3", "C": "L2", "R": "L1"}
BOUNDARY = ("Bounded fixed-weight authored-symbol CJT composition. Named values "
            "reference accepted Effects; no skill acquisition or new Noetic meaning. "
            "Every intermediate output is checked against a private native run.")


def _frozen():
    sibling = ROOT.parent / "CAS_META_1_LEARNED_SELECTION"
    if not sibling.is_dir():
        raise RuntimeError("FROZEN_META1_HELPERS_MISSING")
    if str(sibling) not in sys.path:
        sys.path.insert(0, str(sibling))
    from cas_meta1 import execution as bridge
    return bridge, bridge._frozen()


def _write(path, value):
    Path(path).write_bytes(canonical(value) + b"\n")


def admit_action(public, action):
    validate_public(public)
    tags = [row["tag"] for row in public["observations"]]
    values = [row["values"] for row in public["observations"]]
    if len(set(tags)) != 3 or any(abs(v) > 2 for row in values for v in row):
        raise CompositionError("INVALID_OR_AMBIGUOUS_OBSERVATIONS")
    if len({struct.pack("<8f", *row) for row in values}) != 3:
        raise CompositionError("AMBIGUOUS_OBSERVATION_PAYLOADS")
    validate_action(action)
    validate_program(action["program"])
    plan = check_native_topology(action["program"])
    if (not plan["runs"] or plan["return_node"] < 0
            or any(event["kind"] == "RETURN" and event["output_node"] < 0
                   for event in plan["events"])):
        raise CompositionError("ACCEPTED_EFFECT_RESULT_REQUIRED")
    return plan


class NativeBackend:
    """Only construct this backend after admission on an AWS CUDA host."""

    def __init__(self, public, output, device, *, direct=False):
        self.bridge, self.f = _frozen()
        self.device = self.bridge._cuda(self.f, device)
        self.public = deepcopy(public)
        self.public_digest = digest(public)
        self.direct = direct
        self.output = Path(output)
        self.native = None
        self.handles = []
        self.kernel_records = []
        self.input_artifacts = {}
        self._prepared = None
        self.before_sources = self.bridge._source_snapshot()
        try:
            with self.f.torch.random.fork_rng(devices=[self.device.index]):
                self.native = self.f.create_native(output / "native.db")
            self.before_model = self.bridge._model_identity(self.native, self.f)
            self.native.network.to(device=self.device).eval()
            self.native.network.requires_grad_(False)
            self.audit, self.handles = self.bridge._gpu_forward_guards(
                self.native.network, self.f.torch, self.device)
            self.native.materializer = self.bridge._CudaMaterializer(
                self.native.materializer, self.f, self.device)
            if self.bridge._model_identity(self.native, self.f) != self.before_model:
                raise RuntimeError("DEVICE_MOVE_CHANGED_PARAMETER_BYTES")
        except Exception:
            if self.native is not None:
                self.native.close()
            raise

    def identity(self):
        n = self.native
        if self.bridge._source_snapshot() != self.before_sources:
            raise CompositionError("FROZEN_MODULE_SOURCE_CHANGED")
        current = self.bridge._model_identity(n, self.f)
        return {"model": current, "stored_model_digest": n.state.model_digest,
                "software_digest": n.software_digest,
                "topology": n.network.topology_manifest(),
                "contracts": {k: v.contract_digest for k, v in n.contracts.items()},
                "decoders": {k: v.contract.decoder_digest for k, v in n.decoders.items()}}

    def head(self):
        return asdict(self.native.store.head)

    def input_reference(self, binding):
        if type(binding) is not int or binding not in (0, 1, 2):
            raise CompositionError("INVALID_OBSERVATION_BINDING")
        row = next(row for row in self.public["observations"] if row["slot"] == binding)
        return {"kind": "observation", "slot": binding, "public_digest": self.public_digest,
                "payload_sha256": sha256(struct.pack("<8f", *row["values"])).hexdigest()}

    def _effect_reference(self, effect_id):
        document = self.native.store.immutable_document("published_effects", effect_id)
        artifact = self.native.store.load_artifact(document["content_ref"]["artifact_id"])
        artifact.verify()
        if artifact.sha256 != document["content_ref"]["sha256"]:
            raise CompositionError("EFFECT_PAYLOAD_REFERENCE_MISMATCH")
        return {"kind": "effect", "effect_id": effect_id,
                "producer_cjt_id": document["producer_cjt_id"],
                "payload_sha256": sha256(artifact.payload).hexdigest()}

    def validate_reference(self, reference):
        if type(reference) is not dict:
            raise CompositionError("INVALID_VALUE_REFERENCE")
        try:
            if reference.get("kind") == "observation":
                expected = self.input_reference(reference["slot"])
            elif reference.get("kind") == "effect":
                expected = self._effect_reference(reference["effect_id"])
            else:
                raise CompositionError("UNKNOWN_VALUE_REFERENCE")
            if reference != expected:
                raise CompositionError("FORGED_VALUE_REFERENCE")
        except (KeyError, TypeError, ValueError) as exc:
            if isinstance(exc, CompositionError):
                raise
            raise CompositionError("UNRESOLVED_VALUE_REFERENCE") from exc
        return True

    def _cause(self, reference):
        self.validate_reference(reference)
        n, f = self.native, self.f
        if reference["kind"] == "effect":
            return n.cause_from_effect(reference["effect_id"], tick=n.store.next_tick(),
                                       candidate_operation_ids=("^6",),
                                       goal_context=f.GOAL_CONTEXT), ()
        row = next(row for row in self.public["observations"] if row["slot"] == reference["slot"])
        value = f.torch.tensor(row["values"], dtype=f.torch.float32,
                               device=self.device).reshape(1, 2, 4)
        cause, artifact = n.make_input_cause(
            value, tick=n.store.next_tick(),
            content={"task": "cas-meta2-observation", "public_digest": self.public_digest,
                     "binding_slot": reference["slot"], "binding_tag": row["tag"]},
            goal_context=f.GOAL_CONTEXT)
        self.input_artifacts[artifact.artifact_id] = artifact.public_descriptor()
        supplied = () if n.store.has_artifact(artifact.artifact_id, artifact.sha256) else (artifact,)
        return cause, supplied

    def prepare(self, cjt_id, reference):
        from cas_cjt.control import RouteSettings
        if cjt_id not in EXPECTED:
            raise CompositionError("UNKNOWN_CJT")
        cause, supplied = self._cause(reference)
        if cjt_id not in self.native.network.select_candidates(cause):
            raise CompositionError("NATIVE_TOPOLOGY_MISMATCH")
        materialized = self.native.materializer.materialize(
            state=self.native.state, cause=cause, cjt_id=cjt_id,
            settings=RouteSettings(), supplied_artifacts=supplied)
        plan_wire = materialized.routing.compute_plan.to_authoritative_dict()
        units = sum(int(value.sum().item()) for _, value in
                    materialized.routing.compute_plan.integer_fields)
        public_plan = {"units": units, "plan_digest": digest(plan_wire)}
        self._prepared = (cjt_id, deepcopy(reference), public_plan, cause, supplied,
                          self.head(), self.identity())
        return deepcopy(public_plan)

    def execute(self, cjt_id, reference, plan):
        if self._prepared is None or self._prepared[:3] != (cjt_id, reference, plan):
            raise CompositionError("PREPARED_PLAN_MISMATCH")
        _, _, _, cause, supplied, prior_head, prior_identity = self._prepared
        self._prepared = None
        if self.head() != prior_head or self.identity() != prior_identity:
            raise CompositionError("PREPARED_BOUNDARY_CHANGED")
        before_state = self.native.state
        before_traces = len(self.native.store.trace_events())
        with self.f.torch.no_grad():
            if self.direct:
                result = self.native.inference_tick(
                    cause=cause, cjt_id=cjt_id, expected_symbol=EXPECTED[cjt_id],
                    supplied_artifacts=supplied)
                actual_plan = result.materialized.routing.compute_plan.to_authoritative_dict()
                if digest(actual_plan) != plan["plan_digest"]:
                    raise CompositionError("NATIVE_PLAN_MISMATCH")
                if not result.accepted or len(result.commit_receipt.published_effect_ids) != 1:
                    raise CompositionError("NATIVE_RESULT_NOT_RETURNABLE")
                effect_id = result.commit_receipt.published_effect_ids[0]
                receipt_id = result.commit_receipt.receipt_id
            else:
                # This is a new generated wrapper, not an edited accepted program.
                source = {"version": "cas-meta/0.1", "entry": "main", "procedures": {
                    "main": {"input_type": cause.cause_kind.value, "output_type": "EFFECT",
                             "allowed_cjts": [cjt_id],
                             "body": {"kind": "run", "cjt": cjt_id, "operation": "^6",
                                      "expected": EXPECTED[cjt_id]}}}}
                from cas_meta.executor import Limits
                kernel = self.f.Executor(
                    self.native, self.f.compile_program(source), cause, artifacts=supplied,
                    chain_id="meta2-native-step", permitted_cjts=(cjt_id,),
                    limits=Limits(budget=plan["units"], max_depth=2, max_steps=4))
                effect_id = kernel.run()
                charges = [e for e in kernel.events if e["kind"] == "CHARGE"]
                calls = [e for e in kernel.events if e["kind"] == "NATIVE"]
                if len(charges) != 1 or len(calls) != 1 or charges[0]["units"] != plan["units"]:
                    raise CompositionError("NATIVE_PLAN_CHARGE_MISMATCH")
                if charges[0]["plan_digest"] != plan["plan_digest"]:
                    raise CompositionError("NATIVE_PLAN_MISMATCH")
                receipt_id = calls[0]["receipt_id"]
                self.kernel_records.append(kernel.events)
        if len(self.native.store.trace_events()) != before_traces + 1:
            raise CompositionError("UNEXPECTED_NATIVE_TICK_COUNT")
        if self.identity() != prior_identity:
            raise CompositionError("FROZEN_RUNTIME_IDENTITY_CHANGED")
        if any(before_state.by_cjt_id[name] != self.native.state.by_cjt_id[name]
               for name in before_state.by_cjt_id if name != cjt_id):
            raise CompositionError("CROSS_CJT_BIAS_CHANGED")
        reference = self._effect_reference(effect_id)
        receipt = self.native.store.receipt_by_id(receipt_id)
        public_receipt = {"receipt_id": receipt_id, "trace_id": receipt["trace_id"],
                          "published_effect_ids": receipt["published_effect_ids"],
                          "units": plan["units"], "plan_digest": plan["plan_digest"]}
        self.validate_receipt(public_receipt, reference)
        return {"reference": reference, "native_receipt": public_receipt}

    def validate_receipt(self, receipt, reference):
        expected_keys = {"receipt_id", "trace_id", "published_effect_ids", "units", "plan_digest"}
        if type(receipt) is not dict or set(receipt) != expected_keys:
            raise CompositionError("INVALID_NATIVE_RECEIPT")
        stored = self.native.store.receipt_by_id(receipt["receipt_id"])
        if (stored["trace_id"] != receipt["trace_id"]
                or stored["published_effect_ids"] != [reference["effect_id"]]
                or receipt["published_effect_ids"] != [reference["effect_id"]]):
            raise CompositionError("NATIVE_RECEIPT_MISMATCH")
        traces = [t for t in self.native.store.trace_events() if t["trace_id"] == receipt["trace_id"]]
        if len(traces) != 1:
            raise CompositionError("NATIVE_TRACE_MISSING")
        self.f.validate_contract(traces[0])
        plan = traces[0]["compute_plan"]
        def integer_sum(value):
            if type(value) is list:
                return sum(integer_sum(item) for item in value)
            if type(value) is not int or value < 0:
                raise CompositionError("INVALID_STORED_PLAN_CHARGE")
            return value
        units = sum(integer_sum(plan[key]) for key in (
            "route_quanta", "reasoning_step_quanta", "branch_quanta",
            "memory_read_quanta", "diagnostic_probe_quanta"))
        if type(receipt["units"]) is not int or units != receipt["units"] or digest(plan) != receipt["plan_digest"]:
            raise CompositionError("NATIVE_RECEIPT_PLAN_MISMATCH")
        return True

    def close(self):
        for handle in self.handles:
            handle.remove()
        if self.native is None:
            return
        try:
            after = self.bridge._model_identity(self.native, self.f)
            if after != self.before_model:
                raise RuntimeError("FROZEN_NATIVE_PARAMETERS_CHANGED")
        finally:
            self.native.close()
        if self.bridge._source_snapshot() != self.before_sources:
            raise RuntimeError("FROZEN_MODULE_SOURCE_CHANGED")
        self.bridge._verify_protected_identity(self.f.verify_baseline, self.f.verify_installed_wheels)


def _private_execute(backend, program, binding):
    """Independent recursive evaluator: no candidate executor or IR expansion."""
    spent = 0
    def visit(name, argument):
        nonlocal spent
        proc = program["procedures"][name]
        values = {proc["input"]: argument}
        for step in proc["steps"]:
            value = values[step["input"]]
            if step["kind"] == "CALL":
                result = visit(step["procedure"], value)
            else:
                plan = backend.prepare(step["cjt_id"], value)
                spent += plan["units"]
                if spent > 32768:
                    raise CompositionError("REFERENCE_POLICY_BUDGET_EXHAUSTED")
                result = backend.execute(step["cjt_id"], value, plan)["reference"]
            values[step["output"]] = result
        return values[proc["return"]]
    return visit(program["entry"], backend.input_reference(binding)), spent


def _run(public, action, output_dir, device, *, reference):
    admit_action(public, action)
    # CUDA admission precedes directory creation and any model construction.
    bridge, f = _frozen()
    bridge._cuda(f, device)
    output = Path(output_dir).resolve()
    if output == ROOT or not output.is_relative_to(ROOT):
        raise CompositionError("OUTPUT_MUST_BE_INSIDE_CANDIDATE")
    output.mkdir(parents=True, exist_ok=False)
    backend = None
    started = time.monotonic()
    try:
        backend = NativeBackend(public, output, device, direct=reference)
        identity = backend.identity()
        if reference:
            final, spent = _private_execute(backend, action["program"], action["binding"])
            events, execution_receipt = [], None
        else:
            executor = CompositionExecutor(backend, action["program"], binding=action["binding"])
            final = executor.run()
            spent, events, execution_receipt = executor.spent, executor.events, executor.validate_evidence()
        f.torch.cuda.synchronize(backend.device)
        traces = list(backend.native.store.trace_events())
        for trace in traces:
            f.validate_contract(trace)
        if not backend.native.store.verify_integrity():
            raise CompositionError("NATIVE_INTEGRITY_FAILED")
        if backend.audit["calls"] == 0:
            raise RuntimeError("NO_GPU_FORWARD_OBSERVED")
        _write(output / "native_traces.json", traces)
        _write(output / "composition_events.json", events)
        _write(output / "native_kernel_events.json", backend.kernel_records)
        result = {"status": "EXECUTED", "reference": reference, "selected_action": deepcopy(action),
                  "public_digest": digest(public), "final_reference": final,
                  "native_trace_count": len(traces), "reserved_policy_units": spent,
                  "gpu_forward_audit": backend.audit,
                  "runtime_identity": identity, "runtime_identity_after": backend.identity(),
                  "execution_receipt": execution_receipt, "trace_valid": True, "integrity": True,
                  "fixed_weights": True, "output_dir": str(output),
                  "native_database": str(output / "native.db"), "claim_boundary": BOUNDARY,
                  "wall_seconds": time.monotonic() - started}
    except Exception as exc:
        _write(output / "failure.json", {"status": "INFRASTRUCTURE_FAILURE",
                                        "type": type(exc).__name__, "message": str(exc)})
        raise
    finally:
        if backend is not None:
            backend.close()
    result["evidence_sha256"] = {p.name: sha256(p.read_bytes()).hexdigest()
                                for p in sorted(output.iterdir()) if p.is_file()}
    if sum(p.stat().st_size for p in output.iterdir() if p.is_file()) > MAX_CASE_BYTES:
        raise RuntimeError("CASE_ARTIFACT_CEILING_EXCEEDED")
    _write(output / "result.json", result)
    return result


def execute_task(public, action, output_dir, device="cuda"):
    return _run(public, action, output_dir, device, reference=False)


def reference_task(task, output_dir, device="cuda"):
    # This entrypoint belongs to the private evaluator AFTER predictions seal.
    return _run(task["public"], task["target"], output_dir, device, reference=True)


def _stored(result, public, *, expected_action=None, allow_private_reference=False):
    """Examine actual SQLite records and tensor bytes; never decode a tensor."""
    output = Path(result["output_dir"]).resolve()
    if output == ROOT or not output.is_relative_to(ROOT):
        raise ValueError("STORED_EVIDENCE_OUTSIDE_CANDIDATE")
    for name, expected in result["evidence_sha256"].items():
        if Path(name).name != name or sha256((output / name).read_bytes()).hexdigest() != expected:
            raise ValueError("STORED_EVIDENCE_HASH_MISMATCH")
    if result["native_database"] != str(output / "native.db"):
        raise ValueError("NATIVE_DATABASE_PATH_MISMATCH")
    conn = sqlite3.connect((output / "native.db").as_uri() + "?mode=ro&immutable=1", uri=True)
    def document(table, key):
        if table not in ("causes", "published_effects"):
            raise ValueError("UNSUPPORTED_TABLE")
        row = conn.execute("SELECT payload_sha256,payload_json FROM " + table + " WHERE record_id=?",
                           (key,)).fetchone()
        if row is None or sha256(row[1].encode("utf-8")).hexdigest() != row[0]:
            raise ValueError("DOCUMENT_HASH_MISMATCH")
        return json.loads(row[1])
    def payload(ref):
        row = conn.execute("SELECT artifact_id,sha256,kind,media_type,encoding,metadata_json,payload FROM artifacts WHERE artifact_id=?",
                           (ref["artifact_id"],)).fetchone()
        if row is None:
            raise ValueError("MISSING_TENSOR_ARTIFACT")
        from cas_cjt.artifacts import StoredArtifact
        artifact = StoredArtifact(*row)
        artifact.verify()  # Checks metadata AND bytes; this performs no tensor work.
        if (artifact.sha256 != ref["sha256"] or artifact.byte_length != ref["byte_length"]
                or ref["dtype"] != "float32" or ref["shape"] != [1, 2, 4]):
            raise ValueError("PAYLOAD_REFERENCE_MISMATCH")
        return artifact.payload
    try:
        from cas_cjt import validate_contract
        traces = []
        for expected, raw in conn.execute("SELECT payload_sha256,payload_json FROM trace_events ORDER BY sequence"):
            if sha256(raw.encode("utf-8")).hexdigest() != expected:
                raise ValueError("TRACE_HASH_MISMATCH")
            trace = json.loads(raw)
            validate_contract(trace)
            model_digest = result["runtime_identity"]["model"]["model_digest"]
            if (trace["pre_model_digest"] != model_digest or trace["post_model_digest"] != model_digest
                    or trace["software_digest"] != result["runtime_identity"]["software_digest"]):
                raise ValueError("STORED_FROZEN_IDENTITY_MISMATCH")
            traces.append(trace)
        rows, produced = [], {}
        for trace in traces:
            cause = document("causes", trace["cause_id"])
            ids = trace["published_effect_ids"]
            if len(ids) != 1:
                raise ValueError("EXPECTED_ONE_ACCEPTED_EFFECT")
            effect = document("published_effects", ids[0])
            if cause["parent_effect_id"] is None:
                source = -1
            else:
                if cause["parent_effect_id"] not in produced:
                    raise ValueError("UNKNOWN_OR_FUTURE_EFFECT_PARENT")
                source = produced[cause["parent_effect_id"]]
            rows.append({"cjt_id": effect["producer_cjt_id"], "input_node": source,
                         "input_sha256": sha256(payload(cause["content_ref"])).hexdigest(),
                         "output_sha256": sha256(payload(effect["content_ref"])).hexdigest()})
            produced[ids[0]] = len(rows) - 1
        final = result["final_reference"]
        if final["effect_id"] not in produced:
            raise ValueError("UNACCEPTED_FINAL_EFFECT")
        final_effect = document("published_effects", final["effect_id"])
        if (final["kind"] != "effect" or final["producer_cjt_id"] != final_effect["producer_cjt_id"]
                or final["payload_sha256"] != sha256(payload(final_effect["content_ref"])).hexdigest()):
            raise ValueError("FORGED_FINAL_EFFECT_REFERENCE")
        from .stored import verify_stored_composition
        audit = verify_stored_composition(result, public, traces=traces,
                                          expected_action=expected_action,
                                          allow_private_reference=allow_private_reference)
        if (audit["rows"] != rows or audit["return_node"] != produced[final["effect_id"]]
                or audit["final_output_sha256"] != final["payload_sha256"]):
            raise ValueError("STORED_AUDIT_DISAGREEMENT")
        return audit
    finally:
        conn.close()


def verify_reference_task(task, reference):
    """Check the private direct run against its gold procedure and public input.

    This is reference integrity/structure validation, not a measured candidate
    result. Only this caller explicitly authorizes the no-call-tree exception.
    """
    if reference.get("status") != "EXECUTED" or reference.get("reference") is not True:
        raise ValueError("PRIVATE_NATIVE_REFERENCE_REQUIRED")
    expected, public = task["target"], task["public"]
    admit_action(public, expected)
    if (reference["selected_action"] != expected or reference["public_digest"] != digest(public)
            or reference["runtime_identity"] != reference["runtime_identity_after"]):
        raise ValueError("PRIVATE_REFERENCE_OR_FROZEN_IDENTITY_MISMATCH")
    private = _stored(reference, public, expected_action=expected, allow_private_reference=True)
    structure = check_native_topology(expected["program"])
    expected_edges = [{"cjt_id": row["cjt_id"], "input_node": row["input_node"]}
                      for row in structure["runs"]]
    actual_edges = [{key: row[key] for key in ("cjt_id", "input_node")} for row in private["rows"]]
    if actual_edges != expected_edges or private["return_node"] != structure["return_node"]:
        raise ValueError("PRIVATE_REFERENCE_STRUCTURE_MISMATCH")
    observation = next(row for row in public["observations"] if row["slot"] == expected["binding"])
    input_sha = sha256(struct.pack("<8f", *observation["values"])).hexdigest()
    if any(row["input_node"] == -1 and row["input_sha256"] != input_sha for row in private["rows"]):
        raise ValueError("PRIVATE_REFERENCE_INPUT_MISMATCH")
    return {"task_correct": True, "procedure_correct": True, "binding_correct": True,
            "dependency_correct": True, "actual_output_correct": True, "trace_valid": True,
            "repair_success": None, "repair_required": False, "native_runs": private["trace_count"],
            "reserved_policy_units": private["reserved_policy_units"],
            "stored_call_tree_verified": False, "stored_audit_method": private["audit_method"],
            "verdict_kind": "PRIVATE_NATIVE_REFERENCE_CHECK", "candidate_task_evaluation": False,
            "claim_boundary": "Private reference integrity, procedure and input checks only; no candidate learning result."}


def verify_task(task, result, reference):
    """Correct program/dependencies AND all actual output bytes must match."""
    verdict = {"task_correct": False, "procedure_correct": False, "binding_correct": False,
               "dependency_correct": False, "actual_output_correct": False,
               "trace_valid": False, "repair_success": None, "repair_required": False}
    if result.get("status") != "EXECUTED":
        verdict["failure"] = "PREDICTED_PROGRAM_REJECTED"
        return verdict
    if result.get("reference") is not False:
        raise ValueError("CANDIDATE_MUST_NOT_BE_PRIVATE_REFERENCE")
    if reference.get("status") != "EXECUTED" or not reference.get("reference"):
        raise ValueError("PRIVATE_NATIVE_REFERENCE_REQUIRED")
    expected = task["target"]
    action = result["selected_action"]
    admit_action(task["public"], action)
    if (reference["selected_action"] != expected
            or reference["public_digest"] != digest(task["public"])
            or reference["runtime_identity"] != reference["runtime_identity_after"]
            or result["runtime_identity"] != result["runtime_identity_after"]
            or reference["runtime_identity"] != result["runtime_identity"]):
        raise ValueError("PRIVATE_REFERENCE_OR_FROZEN_IDENTITY_MISMATCH")
    if result["public_digest"] != digest(task["public"]):
        raise ValueError("PUBLIC_DIGEST_MISMATCH")
    actual = _stored(result, task["public"])
    private = _stored(reference, task["public"], expected_action=expected,
                      allow_private_reference=True)
    structure = check_native_topology(expected["program"])
    expected_edges = [{"cjt_id": row["cjt_id"], "input_node": row["input_node"]}
                      for row in structure["runs"]]
    private_edges = [{key: row[key] for key in ("cjt_id", "input_node")} for row in private["rows"]]
    if private_edges != expected_edges or private["return_node"] != structure["return_node"]:
        raise ValueError("PRIVATE_REFERENCE_STRUCTURE_MISMATCH")
    observation = next(row for row in task["public"]["observations"] if row["slot"] == expected["binding"])
    input_sha = sha256(struct.pack("<8f", *observation["values"])).hexdigest()
    if any(row["input_node"] == -1 and row["input_sha256"] != input_sha for row in private["rows"]):
        raise ValueError("PRIVATE_REFERENCE_INPUT_MISMATCH")
    verdict.update(
        procedure_correct=graph_signature(action["program"]) == graph_signature(expected["program"]),
        binding_correct=action["binding"] == expected["binding"],
        dependency_correct=([{key: row[key] for key in ("cjt_id", "input_node")}
                             for row in actual["rows"]] == private_edges
                            and actual["return_node"] == private["return_node"]),
        actual_output_correct=(actual["rows"] == private["rows"]
                               and actual["final_output_sha256"] == private["final_output_sha256"]),
        trace_valid=True, native_runs=actual["trace_count"],
        reserved_policy_units=actual["reserved_policy_units"],
        stored_call_tree_verified=actual["stored_call_tree_verified"],
        stored_audit_method=actual["audit_method"])
    verdict["task_correct"] = all(verdict[k] for k in (
        "procedure_correct", "binding_correct", "dependency_correct", "actual_output_correct", "trace_valid"))
    return verdict
