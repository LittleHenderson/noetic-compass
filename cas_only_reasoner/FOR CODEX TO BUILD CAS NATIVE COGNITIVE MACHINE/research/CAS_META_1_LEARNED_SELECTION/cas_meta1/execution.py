"""Pilot-owned CUDA bridge, real execution, and private task verification.

The accepted runtime has no device option. Its codecs, SQLite store and exact
integer planner remain host services. This NEW bridge transports materialized
controls and repeats parameter-free routing on CUDA before any neural forward.
It does not edit frozen modules, replace a plan, train the native CJTs, or turn
the authored repair fixture into general prerequisite discovery.
"""

from __future__ import annotations

from dataclasses import fields, is_dataclass, replace
from hashlib import sha256
import importlib
import json
import math
from pathlib import Path
import sqlite3
import struct
from types import SimpleNamespace
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROGRAM_FILES = ("0_single_a.json", "1_nested_ab.json", "2_repair_chain.json")
WORKFLOWS = (("A",), ("A", "B"), ("A", "B", "C", "R", "C"))
FINAL_SYMBOLS = ("L1", "L3", "L2")
MAX_CASE_BYTES = 16 * 1024 * 1024
BOUNDARY = ("Fixed-weight authored procedure selection and observation binding. "
            "Repair is an authored fixture, not general prerequisite inference. "
            "The CUDA bridge is new pilot code, not a previously accepted GPU runtime.")


class ExecutionInfrastructureError(RuntimeError):
    """Abort the pilot: CUDA or a protected identity/plan is not trustworthy."""


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def _hash_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _write(path: Path, value: Any) -> None:
    path.write_bytes(_canonical(value) + b"\n")


def validate_action(public: Any, action: Any) -> str | None:
    """Data-only validation; invalid actions never initialize neural modules."""
    if type(action) is not dict or set(action) != {"procedure", "binding"}:
        return "INVALID_ACTION_FIELDS"
    if any(type(action[k]) is not int or not 0 <= action[k] <= 2
           for k in ("procedure", "binding")):
        return "ACTION_OUT_OF_RANGE"
    if type(public) is not dict or set(public) != {"problem", "observations"}:
        return "INVALID_PUBLIC_FIELDS"
    if type(public["problem"]) is not str or not 1 <= len(public["problem"]) <= 4096:
        return "INVALID_PROBLEM"
    observations = public["observations"]
    if type(observations) is not list or len(observations) != 3:
        return "INVALID_OBSERVATIONS"
    slots, tags, payloads = set(), set(), set()
    for row in observations:
        if type(row) is not dict or set(row) != {"slot", "tag", "values"}:
            return "INVALID_OBSERVATION_FIELDS"
        if type(row["slot"]) is not int or row["slot"] not in (0, 1, 2):
            return "INVALID_SLOT"
        if type(row["tag"]) is not str or not 1 <= len(row["tag"]) <= 128:
            return "INVALID_TAG"
        values = row["values"]
        if (type(values) is not list or len(values) != 8
                or any(type(v) not in (int, float) or not math.isfinite(v)
                       or abs(v) > 2 for v in values)):
            return "INVALID_VALUES"
        slots.add(row["slot"])
        tags.add(row["tag"])
        payloads.add(struct.pack("<8f", *values))
    if slots != {0, 1, 2} or len(tags) != 3 or len(payloads) != 3:
        return "AMBIGUOUS_OBSERVATIONS"
    return None


def _rejection(code: str, action: Any, *, exception: Exception | None = None) -> dict:
    return {
        "status": "REJECTED", "failure": {"code": code,
            "type": None if exception is None else type(exception).__name__,
            "message": code if exception is None else str(exception)[:1000]},
        "selected_action": ({key: action.get(key) if type(action.get(key)) is int else None
                             for key in ("procedure", "binding")}
                            if type(action) is dict else None),
        "reserved_policy_units": None, "repair_count": 0,
        "trace_valid": False, "fixed_weights": False,
        "frozen_model_digest_before": None, "frozen_model_digest_after": None,
        "frozen_parameter_bytes_sha256_before": None,
        "frozen_parameter_bytes_sha256_after": None,
        "claim_boundary": BOUNDARY,
    }


def _runtime_rejection(exc: Exception, action: Any) -> dict:
    code = getattr(exc, "code", "RUNTIME_EXECUTION_REJECTED")
    if code == "NATIVE_PLAN_MISMATCH":
        raise ExecutionInfrastructureError("NATIVE_PLAN_MISMATCH") from exc
    return _rejection(code, action, exception=exc)


def _verify_protected_identity(verify_baseline, verify_installed_wheels) -> None:
    for name, check in (("BASELINE", verify_baseline),
                        ("INSTALLED_WHEELS", verify_installed_wheels)):
        try:
            check()
        except Exception as exc:
            raise ExecutionInfrastructureError(
                f"FROZEN_{name}_IDENTITY_CHECK_FAILED:{exc}") from exc


def _frozen() -> SimpleNamespace:
    # The parent bootstrap adds only the unpublished cas_meta source package.
    # casformer and cas_cjt must come from the accepted, byte-checked wheels.
    from .baseline import verify_baseline, verify_installed_wheels
    _verify_protected_identity(verify_baseline, verify_installed_wheels)
    import torch
    from cas_meta.compiler import compile_program
    from cas_meta.executor import Executor
    from cas_meta.fixture import create_native, GOAL_CONTEXT
    from cas_meta.demo import semantic_projection
    from cas_cjt import validate_contract
    from cas_cjt.artifacts import StoredArtifact, decode_tensor
    from cas_cjt.checkpoint import encode_module_checkpoint
    from cas_cjt.readiness import DWPProfile
    from cas_cjt.routing import (CASOhmRouter, ComputePolicy, NativeComputeInputs,
                                RouteInputs, realized_flow_tensors)
    return SimpleNamespace(**locals())


def _source_snapshot() -> dict[str, str]:
    result = {}
    try:
        for name in ("casformer", "cas_cjt", "cas_meta"):
            module = importlib.import_module(name)
            package = Path(module.__file__).resolve().parent
            for path in sorted(package.rglob("*.py")):
                result[f"{name}/{path.relative_to(package).as_posix()}"] = _hash_file(path)
    except Exception as exc:
        raise ExecutionInfrastructureError("FROZEN_MODULE_SOURCE_IDENTITY_UNAVAILABLE") from exc
    return result


def _cuda(frozen: SimpleNamespace, requested: str):
    torch = frozen.torch
    if not isinstance(requested, str) or not requested.startswith("cuda"):
        raise ExecutionInfrastructureError("CUDA_REQUIRED_NO_CPU_FALLBACK")
    try:
        device = torch.device(requested)
    except (ValueError, RuntimeError) as exc:
        raise ExecutionInfrastructureError("INVALID_CUDA_DEVICE") from exc
    if device.type != "cuda" or not torch.cuda.is_available():
        raise ExecutionInfrastructureError("CUDA_UNAVAILABLE_NO_CPU_FALLBACK")
    index = torch.cuda.current_device() if device.index is None else device.index
    if not 0 <= index < torch.cuda.device_count():
        raise ExecutionInfrastructureError("CUDA_DEVICE_UNAVAILABLE")
    return torch.device("cuda", index)


def _move(value, device, torch):
    if isinstance(value, torch.Tensor):
        return value.to(device=device)
    if is_dataclass(value):
        return replace(value, **{f.name: _move(getattr(value, f.name), device, torch)
                                  for f in fields(value)})
    if isinstance(value, tuple):
        return tuple(_move(x, device, torch) for x in value)
    if isinstance(value, list):
        return [_move(x, device, torch) for x in value]
    if type(value) is dict:
        return {k: _move(v, device, torch) for k, v in value.items()}
    return value


class _CudaMaterializer:
    """Transport adapter; accepted integer plan and manifest remain unchanged."""

    def __init__(self, inner, frozen, device):
        self.inner, self.frozen, self.device = inner, frozen, device

    def materialize(self, **arguments):
        f, torch, device = self.frozen, self.frozen.torch, self.device
        cpu = self.inner.materialize(**arguments)  # No neural module forward.
        out = _move(cpu, device, torch)
        x, control, manifest = out.cause_tensor, out.control, out.binding_manifest
        native_wire, policy_wire = manifest["native_compute"], manifest["compute_policy"]
        native = f.NativeComputeInputs(
            drive_units=torch.tensor(native_wire["drive_units"], dtype=torch.int64, device=device),
            resistance_units=torch.tensor(native_wire["resistance_units"], dtype=torch.int64, device=device),
            canonical_route_ids=tuple(native_wire["canonical_route_ids"]),
            flow_scale_units=native_wire["flow_scale_units"],
        )
        policy = f.ComputePolicy(**{field.name: policy_wire[field.name]
                                   for field in fields(f.ComputePolicy)})
        semantic = torch.matmul(x, x.transpose(-2, -1)) / math.sqrt(x.shape[-1])
        semantic = semantic.unsqueeze(1).expand(-1, self.inner.network.config.num_heads,
                                               -1, -1).contiguous()
        masks = {key: torch.tensor(value, dtype=torch.bool, device=device)
                 for key, value in manifest["hard_masks"].items()}
        cfg = self.inner.network.config
        routing = f.CASOhmRouter(policy).route(f.RouteInputs(
            semantic_scores=semantic, drive=control.drive,
            resistance_capability=control.resistance_capability,
            resistance_context=control.resistance_context,
            resistance_resource=control.resistance_resource,
            resistance_memory=control.resistance_policy,
            prior_region_multiplier=control.region_multiplier,
            topology_mask=masks["topology_mask"], permission_mask=masks["permission_mask"],
            quarantine_mask=masks["quarantine_mask"], budget_mask=masks["budget_mask"],
            readiness=f.DWPProfile.from_state(out.bias.rpm.readiness, semantic),
            native_compute=native, reference_drive=cfg.reference_drive,
            reference_resistance=cfg.reference_resistance,
            minimum_total_resistance=cfg.minimum_total_resistance,
        ))
        if routing.compute_plan.to_authoritative_dict() != cpu.routing.compute_plan.to_authoritative_dict():
            raise ExecutionInfrastructureError("CUDA_BRIDGE_NATIVE_PLAN_MISMATCH")
        if not torch.equal(routing.effective_mask.cpu(), cpu.routing.effective_mask):
            raise ExecutionInfrastructureError("CUDA_BRIDGE_ROUTE_ADMISSION_MISMATCH")
        current, total, allocation, conducting = f.realized_flow_tensors(
            routing.current, routing.effective_mask, native.canonical_route_ids)
        if not torch.equal(conducting.cpu(), cpu.conducting_query_mask):
            raise ExecutionInfrastructureError("CUDA_BRIDGE_CONDUCTION_MISMATCH")
        return replace(out, routing=routing,
                       control=replace(control, topology_mask=routing.effective_mask,
                                       permission_mask=routing.effective_mask),
                       current_microunits=current, total_current_microunits=total,
                       flow_allocation_ppm=allocation, conducting_query_mask=conducting)


def _gpu_forward_guards(network, torch, device):
    audit = {"calls": 0, "device": str(device)}

    def tensors(value):
        if isinstance(value, torch.Tensor):
            yield value
        elif is_dataclass(value):
            for field in fields(value):
                yield from tensors(getattr(value, field.name))
        elif isinstance(value, dict):
            for item in value.values():
                yield from tensors(item)
        elif isinstance(value, (tuple, list)):
            for item in value:
                yield from tensors(item)

    def before(module, args, kwargs):
        for value in (*module.parameters(recurse=False), *module.buffers(recurse=False),
                      *tensors(args), *tensors(kwargs)):
            if value.device != device:
                raise ExecutionInfrastructureError("CPU_OR_WRONG_DEVICE_NEURAL_FORWARD")
        audit["calls"] += 1

    handles = [module.register_forward_pre_hook(before, with_kwargs=True)
               for module in network.modules()]
    return audit, handles


def _model_identity(native, frozen):
    try:
        checkpoint = frozen.encode_module_checkpoint(native.network)
        return {"model_digest": checkpoint.model_digest,
                "parameter_bytes_sha256": sha256(checkpoint.artifact.payload).hexdigest()}
    except Exception as exc:
        raise ExecutionInfrastructureError("FROZEN_NATIVE_PARAMETER_IDENTITY_UNAVAILABLE") from exc


def _new_case_dir(output_dir) -> Path:
    path = Path(output_dir).resolve()
    if path == ROOT or not path.is_relative_to(ROOT):
        raise ExecutionInfrastructureError("OUTPUT_MUST_BE_INSIDE_NEW_PILOT")
    path.mkdir(parents=True, exist_ok=False)
    return path


def _input(native, public, binding, frozen, device):
    observation = next(row for row in public["observations"] if row["slot"] == binding)
    value = frozen.torch.tensor(observation["values"], dtype=frozen.torch.float32,
                                device=device).reshape(1, 2, 4)
    cause, artifact = native.make_input_cause(
        value, tick=native.store.next_tick(),
        content={"task": "cas-meta-1-observation", "public_digest": sha256(_canonical(public)).hexdigest(),
                 "binding_slot": binding, "binding_tag": observation["tag"]},
        goal_context=frozen.GOAL_CONTEXT,
    )
    return cause, artifact


def _workflow(traces):
    # cjt_ids lists the WHOLE network, not the executor chosen for this tick.
    producers = []
    for trace in traces:
        candidates = trace["candidate_effects"]
        if len(candidates) != 1:
            raise ValueError("EXPECTED_SINGLE_NATIVE_CANDIDATE")
        producers.append(candidates[0]["producer_cjt_id"])
    return producers


def _direct_reference(native, cause, artifact, procedure, frozen):
    """Private oracle path. No program templates, compiler or Executor used here."""
    results = []

    def cascade(effect_id):
        return native.cause_from_effect(effect_id, tick=native.store.next_tick(),
                                        candidate_operation_ids=("^6",),
                                        goal_context=frozen.GOAL_CONTEXT)

    a = native.inference_tick(cause=cause, cjt_id="A", expected_symbol="L1",
                              supplied_artifacts=(artifact,))
    results.append(a)
    if procedure == 0:
        return results
    b = native.inference_tick(cause=cascade(a.commit_receipt.published_effect_ids[0]),
                              cjt_id="B", expected_symbol="L3")
    results.append(b)
    if procedure == 1:
        return results
    rejected = native.inference_tick(cause=cascade(b.commit_receipt.published_effect_ids[0]),
                                     cjt_id="C", expected_symbol="L0", opposite_symbol="L2")
    results.append(rejected)
    if rejected.repair_subgoal is None or rejected.repair_frame is None:
        raise ValueError("REFERENCE_AUTHORED_REPAIR_DID_NOT_OPEN")
    repaired = native.inference_tick(cause=rejected.repair_subgoal, cjt_id="R", expected_symbol="L1")
    results.append(repaired)
    resumed = native.inference_tick(cause=cascade(repaired.commit_receipt.published_effect_ids[0]),
                                    cjt_id="C", expected_symbol="L2",
                                    resume_repair_id=rejected.repair_frame.repair_id)
    results.append(resumed)
    if resumed.repair_outcome is None:
        raise ValueError("REFERENCE_REPAIR_DID_NOT_CLOSE")
    return results


def _run(public, action, output_dir, device, *, reference):
    invalid = validate_action(public, action)
    if invalid:
        return _rejection(invalid, action)
    f = _frozen()
    cuda = _cuda(f, device)  # Fail before output or module initialization on CPU-only hosts.
    before_sources = _source_snapshot()
    output = _new_case_dir(output_dir)
    native, handles, executor, artifact, result = None, [], None, None, None
    prior_model, final_model, audit = None, None, {"calls": 0, "device": str(cuda)}
    try:
        # Preserve fixed CPU-seeded initial bytes, then move BEFORE any forward.
        # This block is reached only on an admitted CUDA host, never in local tests.
        with f.torch.random.fork_rng(devices=[cuda.index]):
            native = f.create_native(output / "native.db")
        prior_model = _model_identity(native, f)
        native.network.to(device=cuda).eval()
        native.network.requires_grad_(False)
        if _model_identity(native, f) != prior_model:
            raise ExecutionInfrastructureError("DEVICE_MOVE_CHANGED_PARAMETER_BYTES")
        audit, handles = _gpu_forward_guards(native.network, f.torch, cuda)
        native.materializer = _CudaMaterializer(native.materializer, f, cuda)
        cause, artifact = _input(native, public, action["binding"], f, cuda)
        with f.torch.no_grad():
            if reference:
                ticks = _direct_reference(native, cause, artifact, action["procedure"], f)
                reserved = sum(sum(int(v.sum().item()) for _, v in
                                   t.materialized.routing.compute_plan.integer_fields) for t in ticks)
                meta_events = []
            else:
                program_path = ROOT / "programs" / PROGRAM_FILES[action["procedure"]]
                program = f.compile_program(program_path.read_text(encoding="utf-8"))
                executor = f.Executor(native, program, cause, artifacts=(artifact,),
                                      chain_id="meta1-task")
                executor.run()
                executor.validate_evidence()
                reserved, meta_events = executor.spent, executor.events
        f.torch.cuda.synchronize(cuda)
        traces = list(native.store.trace_events())
        for trace in traces:
            f.validate_contract(trace)
        projection = f.semantic_projection(native)
        effects = [effect for step in projection for effect in step["published_effects"]]
        if not effects:
            raise ValueError("NO_PUBLISHED_RESULT")
        final_effect = effects[-1]
        final_artifact = native.store.load_artifact(final_effect["content_ref"]["artifact_id"])
        output_values = f.decode_tensor(final_effect["content_ref"], final_artifact).reshape(-1).tolist()
        final_model = _model_identity(native, f)
        if final_model != prior_model or final_model["model_digest"] != native.state.model_digest:
            raise ExecutionInfrastructureError("FROZEN_NATIVE_PARAMETERS_CHANGED")
        if audit["calls"] == 0:
            raise ExecutionInfrastructureError("NO_GPU_NEURAL_FORWARD_OBSERVED")
        if not native.store.verify_integrity():
            raise ValueError("NATIVE_INTEGRITY_INVALID")
        _write(output / "native_traces.json", traces)
        _write(output / "meta_events.json", meta_events)
        _write(output / "semantic_projection.json", projection)
        _write(output / "published_effects.json", effects)
        result = {
            "status": "EXECUTED", "failure": None, "reference": reference,
            "selected_action": dict(action), "public_digest": sha256(_canonical(public)).hexdigest(),
            "input_artifact": artifact.public_descriptor(),
            "input_tensor_bytes_sha256": sha256(artifact.payload).hexdigest(),
            "final_effect": final_effect,
            "output_tensor_values": output_values,
            "output_tensor_bytes_sha256": sha256(final_artifact.payload).hexdigest(),
            "native_workflow": _workflow(traces),
            "native_trace_count": len(traces), "accepted_effect_count": len(effects),
            "repair_count": sum(len(p["repair_frames"]) for p in projection),
            "repair_outcome_count": sum(len(p["repair_outcomes"]) for p in projection),
            "repair_closed": not native.state.by_cjt_id["C"].rpm.open_repair_ids,
            "meta_events": meta_events, "reserved_policy_units": reserved,
            "budget_ceiling": 512, "trace_valid": True, "integrity": True,
            "fixed_weights": True, "gpu_forward_audit": audit,
            "frozen_model_digest_before": prior_model["model_digest"],
            "frozen_model_digest_after": final_model["model_digest"],
            "frozen_parameter_bytes_sha256_before": prior_model["parameter_bytes_sha256"],
            "frozen_parameter_bytes_sha256_after": final_model["parameter_bytes_sha256"],
            "semantic_projection_digest": sha256(_canonical(projection)).hexdigest(),
            "claim_boundary": BOUNDARY,
        }
    except ExecutionInfrastructureError:
        raise
    except Exception as exc:
        result = _runtime_rejection(exc, action)
        if executor is not None:
            result["reserved_policy_units"] = executor.spent
            result["meta_events"] = executor.events
        if native is not None:
            _write(output / "rejected_native_traces.json", list(native.store.trace_events()))
        if prior_model is not None:
            result["frozen_model_digest_before"] = prior_model["model_digest"]
            result["frozen_parameter_bytes_sha256_before"] = prior_model["parameter_bytes_sha256"]
    finally:
        for handle in handles:
            handle.remove()
        if native is not None:
            try:
                after = _model_identity(native, f)
            finally:
                native.close()
            if prior_model is not None and after != prior_model:
                raise ExecutionInfrastructureError("FROZEN_NATIVE_PARAMETERS_CHANGED")
        if _source_snapshot() != before_sources:
            raise ExecutionInfrastructureError("FROZEN_MODULE_SOURCE_CHANGED")
        _verify_protected_identity(f.verify_baseline, f.verify_installed_wheels)
    assert result is not None
    result["output_dir"] = str(output)
    result["native_database"] = str(output / "native.db")
    result["semantic_projection_path"] = str(output / "semantic_projection.json")
    result["protected_sources_unchanged"] = True
    result["evidence_sha256"] = {p.name: _hash_file(p) for p in sorted(output.iterdir()) if p.is_file()}
    if sum(p.stat().st_size for p in output.iterdir() if p.is_file()) > MAX_CASE_BYTES:
        raise ExecutionInfrastructureError("PER_TASK_DISK_CEILING_EXCEEDED")
    _write(output / "result.json", result)
    return result


def execute_task(public: dict, action: dict, output_dir, device: str = "cuda") -> dict:
    """Execute ONLY a public task and proposed action; this path has no gold input."""
    return _run(public, action, output_dir, device, reference=False)


def reference_task(task: dict, output_dir, device: str = "cuda") -> dict:
    """Verifier-private direct native reference, generated after predictions seal."""
    target = task["target"]
    action = {"procedure": target["procedure"], "binding": target["binding"]}
    return _run(task["public"], action, output_dir, device, reference=True)


def _read_record(connection, table: str, record_id: str) -> dict:
    if table not in {"published_effects", "causes"}:
        raise ValueError("UNSUPPORTED_EVIDENCE_TABLE")
    row = connection.execute(f"SELECT payload_sha256,payload_json FROM {table} WHERE record_id=?",
                             (record_id,)).fetchone()
    if row is None or sha256(row[1].encode("utf-8")).hexdigest() != row[0]:
        raise ValueError("STORED_DOCUMENT_HASH_MISMATCH")
    return json.loads(row[1])


def _database_values(result: dict) -> dict:
    """Read actual durable data, not a model's claimed label or result summary."""
    output = Path(result["output_dir"]).resolve()
    if not output.is_relative_to(ROOT):
        raise ValueError("EVIDENCE_OUTSIDE_PILOT")
    for name, expected in result["evidence_sha256"].items():
        path = output / name
        if Path(name).name != name or _hash_file(path) != expected:
            raise ValueError("EVIDENCE_HASH_MISMATCH")
    db = output / "native.db"
    if not db.is_file() or result["native_database"] != str(db):
        raise ValueError("NATIVE_DATABASE_MISSING")
    conn = sqlite3.connect(db.as_uri() + "?mode=ro&immutable=1", uri=True)
    try:
        traces = []
        for raw_hash, payload in conn.execute("SELECT payload_sha256,payload_json FROM trace_events ORDER BY sequence"):
            if sha256(payload.encode("utf-8")).hexdigest() != raw_hash:
                raise ValueError("STORED_TRACE_HASH_MISMATCH")
            traces.append(json.loads(payload))
        if not traces:
            raise ValueError("NO_DURABLE_TRACES")
        from cas_cjt import validate_contract
        for trace in traces:
            validate_contract(trace)
        first = _read_record(conn, "causes", traces[0]["cause_id"])
        final_ids = [effect_id for trace in traces for effect_id in trace["published_effect_ids"]]
        final = _read_record(conn, "published_effects", final_ids[-1])

        def tensor_bytes(reference):
            row = conn.execute("SELECT artifact_id,sha256,kind,media_type,encoding,metadata_json,payload FROM artifacts WHERE artifact_id=?",
                               (reference["artifact_id"],)).fetchone()
            if row is None:
                raise ValueError("MISSING_TENSOR_ARTIFACT")
            from cas_cjt.artifacts import StoredArtifact
            stored = StoredArtifact(*row)
            stored.verify()
            if stored.sha256 != reference["sha256"] or stored.byte_length != reference["byte_length"]:
                raise ValueError("TENSOR_REFERENCE_MISMATCH")
            if reference["dtype"] != "float32" or list(reference["shape"]) != [1, 2, 4]:
                raise ValueError("UNEXPECTED_TENSOR_GEOMETRY")
            return stored.payload

        return {"traces": traces, "first_cause": first, "final_effect": final,
                "input_bytes": tensor_bytes(first["content_ref"]),
                "output_bytes": tensor_bytes(final["content_ref"]),
                "repair_count": conn.execute("SELECT COUNT(*) FROM repair_frames").fetchone()[0],
                "repair_outcome_count": conn.execute("SELECT COUNT(*) FROM repair_outcomes").fetchone()[0]}
    finally:
        conn.close()


def verify_task(task: dict, result: dict, reference: dict) -> dict:
    """Private correctness: input bytes AND actual output/workflow must match."""
    target, reasons = task["target"], []
    selected = result.get("selected_action") or {}
    procedure_correct = selected.get("procedure") == target["procedure"]
    binding_correct = selected.get("binding") == target["binding"]
    repair_required = bool(target["expected"]["repair_required"])
    verdict = {"success": False, "procedure_correct": procedure_correct,
               "binding_correct": binding_correct, "repair_required": repair_required,
               "repair_correct": False, "output_correct": False, "evidence_valid": False,
               "reasons": reasons}
    if result.get("status") != "EXECUTED":
        reasons.append("EXECUTION_REJECTED")
        return verdict
    if reference.get("status") != "EXECUTED" or reference.get("reference") is not True:
        reasons.append("PRIVATE_REFERENCE_UNAVAILABLE")
        return verdict
    try:
        actual, oracle = _database_values(result), _database_values(reference)
        expected = target["expected"]
        goal_observation = next(o for o in task["public"]["observations"] if o["slot"] == target["binding"])
        wanted_bytes = struct.pack("<8f", *goal_observation["values"])
        public_hash = sha256(_canonical(task["public"])).hexdigest()
        binding_correct = (binding_correct and actual["input_bytes"] == wanted_bytes
                           and oracle["input_bytes"] == wanted_bytes
                           and actual["first_cause"]["content"]["binding_slot"] == target["binding"]
                           and actual["first_cause"]["content"]["public_digest"] == public_hash)
        workflow = _workflow(actual["traces"])
        procedure_correct = (procedure_correct and workflow == expected["workflow"]
                             and workflow == _workflow(oracle["traces"]))
        repair_correct = (actual["repair_count"] == int(repair_required)
                          and actual["repair_outcome_count"] == int(repair_required)
                          and result.get("repair_closed") is True)
        output_correct = (actual["output_bytes"] == oracle["output_bytes"]
                          and actual["final_effect"] == oracle["final_effect"]
                          and actual["final_effect"]["content"]["symbol"] == expected["final_symbol"])
        fixed = (result.get("fixed_weights") is True and result.get("protected_sources_unchanged") is True
                 and result.get("frozen_model_digest_before") == result.get("frozen_model_digest_after")
                 == reference.get("frozen_model_digest_after")
                 and result.get("frozen_parameter_bytes_sha256_before")
                 == result.get("frozen_parameter_bytes_sha256_after")
                 == reference.get("frozen_parameter_bytes_sha256_after"))
        budget = result.get("reserved_policy_units") == 72 * len(workflow) <= 512
        evidence_valid = result.get("trace_valid") is True and result.get("integrity") is True and fixed and budget
        verdict.update(procedure_correct=procedure_correct, binding_correct=binding_correct,
                       repair_correct=repair_correct, output_correct=output_correct,
                       evidence_valid=evidence_valid)
        for key in ("procedure_correct", "binding_correct", "repair_correct", "output_correct", "evidence_valid"):
            if not verdict[key]:
                reasons.append(key.upper())
        verdict["success"] = not reasons
    except (KeyError, TypeError, ValueError, OSError, sqlite3.Error) as exc:
        reasons.append("INVALID_DURABLE_EVIDENCE:" + type(exc).__name__)
    return verdict
