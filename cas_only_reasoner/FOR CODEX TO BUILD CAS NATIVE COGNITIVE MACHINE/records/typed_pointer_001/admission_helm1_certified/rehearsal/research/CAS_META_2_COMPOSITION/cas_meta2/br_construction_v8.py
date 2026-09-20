"""AWS-only same-state B/R component construction; no neural training.

The ordinary A-B-C-R prelude must really accept. Both copies are restored with
the accepted open_native API. Only the committed input reference changes.
This module is inert on import and its tests use no models or real databases.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import re
import sys
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "cas-meta2-br-construction/8"
PLAN_SCHEMA = "cas-meta2-br-construction-plan/8"
PRELUDE = ("A", "B", "C", "R")
EXPECTED = {"A": "L1", "B": "L3", "C": "L2", "R": "L1"}
ARM_LIMITS = {"policy_units": 8192, "max_native_ticks": 1}
BOUNDARY = ("Same-state native component intervention, not learned input selection, "
            "task-conditioned correctness, full-program continuation, or generalization.")


class ConstructionRefused(ValueError):
    pass


def require(condition, code):
    if not condition:
        raise ConstructionRefused(code)


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def file_hash(path):
    with Path(path).open("rb") as stream:
        return __import__("hashlib").file_digest(stream, "sha256").hexdigest()


def write_new(path, value):
    with Path(path).open("xb") as stream:
        stream.write(canonical(value))
        stream.flush()
        os.fsync(stream.fileno())


def validate_plan(plan, job):
    require(type(plan) is dict and plan.get("schema") == PLAN_SCHEMA
            and plan.get("job") == job and plan.get("launch_enabled") is True,
            "BR_REGISTERED_ENABLED_PLAN_REQUIRED")
    require(type(job) is str and re.fullmatch(r"cas-meta2-[0-9]{14}-[0-9a-f]{8}", job),
            "BR_JOB_ID_REQUIRED")
    exact = {"max_seconds": 600, "max_cost_usd": "4.00",
             "prelude_policy_units": 32768, "arm_policy_units": 8192,
             "binding": 0, "prelude": list(PRELUDE), "arm_cjt": "C",
             "arm_expected_symbol": "L2", "seed": 7, "training": False,
             "native_execution": True, "max_image_bytes": 64 * 1024**2}
    require(all(type(plan.get(k)) is type(v) and plan[k] == v for k, v in exact.items()),
            "BR_CONSTRUCTION_SCOPE_CHANGED")
    require(type(plan.get("source_sha")) is str and type(plan.get("instance_id")) is str
            and re.fullmatch("[0-9a-f]{40}", plan["source_sha"])
            and re.fullmatch("i-[0-9a-f]{17}", plan["instance_id"]),
            "BR_SOURCE_INSTANCE_ID_REQUIRED")
    return plan


def require_cloud_request(job):
    require(sys.platform == "linux"
            and os.environ.get("CAS_META2_RUN_BR_CONSTRUCTION") == "1"
            and os.environ.get("CAS_META2_AWS_JOB_ID") == job,
            "BR_AWS_LINUX_EXPLICIT_JOB_REQUIRED")
    require(not {"torch", "casformer", "cas_cjt", "tensorflow", "jax"}.intersection(
        name.split(".")[0] for name in sys.modules), "BR_NEURAL_IMPORT_BEFORE_ADMISSION")


def new_output(path):
    path = Path(path).absolute()
    require(not path.exists() and ".." not in path.parts
            and path.resolve().is_relative_to((ROOT / "runs").resolve())
            and path.resolve() != (ROOT / "runs").resolve()
            and not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
                        for p in (path, *path.parents)), "BR_NEW_RUN_DIRECTORY_REQUIRED")
    return path


def check_sources(plan):
    from aws.br_package_v8 import inspect_archive, verify_extracted
    manifest = inspect_archive(plan["source_archive"]["path"],
        expected_sha256=plan["source_archive"]["sha256"],
        expected_source_sha=plan["source_sha"],
        expected_manifest_sha256=plan["source_manifest"]["sha256"])
    package = Path(plan["source_manifest"]["path"]).absolute().parent
    require(Path(plan["source_manifest"]["path"]).name == "br_source_manifest.json",
            "BR_ROOT_MANIFEST_REQUIRED")
    verify_extracted(package, manifest, imported_paths=(Path(__file__),))
    return manifest


def charge_plan(plan, spent, maximum):
    require(type(spent) is int and type(maximum) is int and 0 <= spent <= maximum,
            "BR_INVALID_POLICY_ALLOWANCE")
    require(type(plan) is dict and type(plan.get("units")) is int and plan["units"] >= 0,
            "BR_INVALID_PLAN_CHARGE")
    require(spent + plan["units"] <= maximum, "BR_COMPONENT_POLICY_BUDGET_EXHAUSTED")
    return spent + plan["units"]


def execute_sequence(backend, cjt_ids, initial_reference, *, maximum, deadline, record):
    """Direct adapter calls only; stop at the first refusal without substitution."""
    current = deepcopy(initial_reference)
    spent, results = 0, []
    for cjt_id in cjt_ids:
        require(time.monotonic() < deadline, "BR_WORKER_DEADLINE")
        plan = backend.prepare(cjt_id, current)
        spent = charge_plan(plan, spent, maximum)
        record("PLAN_ADMITTED", cjt_id=cjt_id, input_reference=current,
               plan=plan, accumulated_policy_units=spent)
        result = backend.execute(cjt_id, current, plan)
        results.append({"cjt_id": cjt_id, "input_reference": deepcopy(current),
                        "plan": plan, "result": result})
        current = result["reference"]
        record("ORDINARY_NATIVE_RESULT", **results[-1])
        require(time.monotonic() < deadline, "BR_WORKER_DEADLINE")
    return results, spent


def restored_backend(public, database, output, device):
    """Called only inside run() after live EC2 and CUDA admission."""
    from .native import NativeBackend, _frozen

    class RestoredBackend(NativeBackend):
        def __init__(self):
            self.bridge, self.f = _frozen()
            self.device = self.bridge._cuda(self.f, device)
            self.public = deepcopy(public)
            from .executor import digest
            self.public_digest = digest(public)
            self.direct = True
            self.output = Path(output)
            self.native = None
            self.handles = []
            self.kernel_records = []
            self.input_artifacts = {}
            self._prepared = None
            self.before_sources = self.bridge._source_snapshot()
            try:
                from cas_meta.fixture import open_native
                with self.f.torch.random.fork_rng(devices=[self.device.index]):
                    self.native = open_native(database)
                self.before_model = self.bridge._model_identity(self.native, self.f)
                self.native.network.to(device=self.device).eval()
                self.native.network.requires_grad_(False)
                self.audit, self.handles = self.bridge._gpu_forward_guards(
                    self.native.network, self.f.torch, self.device)
                self.native.materializer = self.bridge._CudaMaterializer(
                    self.native.materializer, self.f, self.device)
                require(self.bridge._model_identity(self.native, self.f) == self.before_model,
                        "BR_RESTORE_DEVICE_MOVE_CHANGED_WEIGHTS")
            except BaseException:
                for handle in self.handles:
                    handle.remove()
                if self.native is not None:
                    self.native.close()
                raise
    return RestoredBackend()


def numeric_settings(torch):
    return {"seed": 7, "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
            "cudnn_benchmark": torch.backends.cudnn.benchmark,
            "cudnn_deterministic": torch.backends.cudnn.deterministic,
            "matmul_allow_tf32": torch.backends.cuda.matmul.allow_tf32,
            "cudnn_allow_tf32": torch.backends.cudnn.allow_tf32,
            "cublas_workspace_config": os.environ.get("CUBLAS_WORKSPACE_CONFIG"),
            "torch": str(torch.__version__), "cuda": str(torch.version.cuda)}


def collect_witness(backend, effect_ids):
    from cas_cjt.control import RouteSettings
    from cas_cjt.runtime import _model_config_wire
    n = backend.native
    snapshot = n.coordinator.restore_and_verify()
    for trace in snapshot.traces:
        backend.f.validate_contract(trace)
    model = n.store.model_version_record(snapshot.state["model_digest"])
    effects = {name: n.store.immutable_document("published_effects", effect_ids[name])
               for name in ("B", "R")}
    receipts = {effect["commit_receipt_id"]: n.store.receipt_by_id(effect["commit_receipt_id"])
                for effect in effects.values()}
    transitions = [n.store.reconstruct_transition(t["trace_id"]) for t in snapshot.traces]
    recovery = {"head": asdict(snapshot.head), "state": snapshot.state,
                "traces": list(snapshot.traces)}
    references = set()
    def visit(value):
        if isinstance(value, dict):
            if type(value.get("artifact_id")) is str:
                references.add(value["artifact_id"])
            for child in value.values():
                visit(child)
        elif isinstance(value, (list, tuple)):
            for child in value:
                visit(child)
    visit([recovery, transitions, effects, model])
    artifacts = {}
    for artifact_id in sorted(references):
        artifact = n.store.load_artifact(artifact_id)
        artifact.verify()
        item = asdict(artifact)
        item["payload_hex"] = item.pop("payload").hex()
        artifacts[artifact_id] = item
    return {"recovery": recovery, "transitions": transitions,
        "next_tick": n.store.next_tick(), "published_effects": effects,
        "receipts": receipts, "artifacts": artifacts, "model_version_record": model,
        "external": {"source_files_sha256": backend.before_sources,
            "config": _model_config_wire(n.network.config),
            "network": n.network.topology_manifest(),
            "decoder_manifests": {k: v.contract.to_dict() for k, v in n.decoders.items()},
            "operation_contracts": {k: v.to_dict() for k, v in n.contracts.items()},
            "goal_context": dict(backend.f.GOAL_CONTEXT),
            "route_settings": RouteSettings().to_dict(), "expected_symbol": "L2",
            "permissions": ["C"], "available_limits": dict(ARM_LIMITS),
            "numeric_settings": numeric_settings(backend.f.torch),
            "runtime_identity": backend.identity()},
        "ownership": {"mode": "DIRECT_NATIVE", "active_outer_executor": None,
                      "suspended_outer_call": False, "outer_frames": []}}


def effect_output(backend, effect_id):
    from cas_cjt.state import tensor_ref_from_mapping
    n = backend.native
    effect = n.store.immutable_document("published_effects", effect_id)
    artifact = n.store.load_artifact(effect["content_ref"]["artifact_id"])
    artifact.verify()
    tensor = backend.f.decode_tensor(tensor_ref_from_mapping(effect["content_ref"]), artifact)
    tensor = tensor.to(device=backend.device)
    require(bool(backend.f.torch.isfinite(tensor).all()), "BR_NONFINITE_OUTPUT")
    decoded = n.decoders[effect["producer_cjt_id"]].decode(tensor)
    require(decoded == effect["content"], "BR_REDECODED_CONTENT_MISMATCH")
    return {"effect": effect, "artifact": artifact.public_descriptor(),
            "payload_sha256": sha256(artifact.payload).hexdigest(),
            "values": tensor.detach().cpu().tolist(), "decoded_content": decoded}


def compare_outputs(left, right):
    def flatten(value):
        if type(value) is list:
            children = [flatten(child) for child in value]
            require(children and all(c[0] == children[0][0] for c in children),
                    "BR_RECTANGULAR_NONEMPTY_OUTPUT_REQUIRED")
            return (len(children), *children[0][0]), [v for _, values in children for v in values]
        require(type(value) in (int, float) and math.isfinite(value), "BR_FINITE_NUMERIC_OUTPUT_REQUIRED")
        return (), [value]
    shape_a, a = flatten(left["values"])
    shape_b, b = flatten(right["values"])
    require(shape_a == shape_b and shape_a and a, "BR_OUTPUT_GEOMETRY_CHANGED")
    difference = max(abs(x-y) for x, y in zip(a, b))
    require(math.isfinite(difference), "BR_NONFINITE_OUTPUT_DIFFERENCE")
    return {"numeric_values_equal": a == b,
            "shape": list(shape_a), "max_absolute_difference": difference,
            "decoded_content_equal": left["decoded_content"] == right["decoded_content"],
            "payload_bytes_equal": left["payload_sha256"] == right["payload_sha256"],
            "intervention": "Whole committed reference: payload, meaning, producer, provenance and publication age.",
            "task_relevance_established": False, "whole_task_verifier_executed": False}


def run(output, *, job, plan_path, plan_sha256):
    require_cloud_request(job)
    from .diagnostic_v8.gpu import read_pinned, reservation_binding, ec2_identity
    plan = validate_plan(read_pinned(plan_path, plan_sha256), job)
    source = check_sources(plan)
    reservation = reservation_binding(plan)
    identity = ec2_identity(plan)
    output = new_output(output)
    deadline = time.monotonic() + plan["max_seconds"]
    os.environ.update(CUBLAS_WORKSPACE_CONFIG=":4096:8", OMP_NUM_THREADS="1",
                      MKL_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1")
    output.mkdir(parents=True, exist_ok=False)
    result = {"schema": SCHEMA, "job": job, "source_sha": plan["source_sha"],
        "source_archive_sha256": plan["source_archive"]["sha256"],
        "source_manifest_sha256": plan["source_manifest"]["sha256"],
        "plan_sha256": plan_sha256, "reservation": reservation,
        "environment": {"ec2": identity, "python": sys.version, "executable": sys.executable},
        "status": "STARTED", "boundary": BOUNDARY, "training": False,
        "native_execution": True, "prelude": [], "arms": {},
        "task_conditioned_correctness": None, "events": [], "cleanup_errors": []}
    def record(event, **fields):
        result["events"].append({"event": event, "utc": datetime.now(timezone.utc).isoformat(), **deepcopy(fields)})
        # A progress record is replaced only within this new, exclusively owned run.
        (output / "progress.json").write_bytes(canonical(result))
    active = []
    try:
        from .native import NativeBackend, _frozen
        from .child_scaffold_v8 import development_scaffold
        from .br_snapshot_v8 import copy_closed_snapshot, _verified_image
        from .br_witness_v8 import validate_before_state_pair
        bridge, f = _frozen()
        device = bridge._cuda(f, "cuda")
        torch = f.torch
        require(str(torch.__version__) == "2.11.0+cu128" and torch.version.cuda == "12.8"
                and torch.cuda.device_count() == 1
                and "RTX PRO 4500" in torch.cuda.get_device_name(device).upper(),
                "BR_REGISTERED_CUDA_REQUIRED")
        torch.set_num_threads(1)
        torch.manual_seed(7)
        torch.cuda.manual_seed_all(7)
        torch.use_deterministic_algorithms(True)
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        result["environment"].update(gpu=torch.cuda.get_device_name(device),
                                    numeric_settings=numeric_settings(torch))
        public = development_scaffold()["public"]
        write_new(output / "public.json", public)
        record("ADMITTED_CLOUD_SETUP_COMPLETE")
        prelude_dir = output / "prelude"
        prelude_dir.mkdir()
        backend = NativeBackend(public, prelude_dir, "cuda", direct=True)
        active.append(backend)
        rows, units = execute_sequence(backend, PRELUDE, backend.input_reference(0),
            maximum=plan["prelude_policy_units"], deadline=deadline, record=record)
        result.update(prelude=rows, prelude_policy_units=units)
        effects = {row["cjt_id"]: row["result"]["reference"]["effect_id"] for row in rows}
        before = collect_witness(backend, effects)
        require(len(before["recovery"]["traces"]) == 4 and before["next_tick"] == 5,
                "BR_ORDINARY_PRELUDE_COUNT_MISMATCH")
        checked = validate_before_state_pair(before, before)
        write_new(output / "preclose_witness.json", before)
        write_new(output / "preclose_witness_check.json", checked)
        require(checked["ok"], "BR_PRELUDE_NOT_QUIESCENT_OR_COMPLETE:" + json.dumps(checked["reasons"]))
        result["prelude_gpu_audit"] = deepcopy(backend.audit)
        require(backend.audit["calls"] > 0, "BR_NO_PRELUDE_GPU_FORWARD")
        backend.close()
        active.remove(backend)
        record("PRELUDE_CLOSED", native_connections_owned=1, native_connections_remaining=0,
               outer_executors_created=0)
        database = prelude_dir / "native.db"
        original_sha = file_hash(database)
        snapshot = copy_closed_snapshot(database, original_sha, output / "copies",
            owned_output_root=output, source_closed_self_contained=True,
            max_bytes=plan["max_image_bytes"])
        result["snapshot"] = snapshot
        arms = {}
        # Open and compare BOTH before-states before either arm may execute.
        for arm in ("B", "R"):
            arm_dir = output / ("arm_" + arm)
            arm_dir.mkdir()
            arms[arm] = restored_backend(public, output / "copies" / (arm + ".sqlite"),
                                         arm_dir, "cuda")
            active.append(arms[arm])
            witness = collect_witness(arms[arm], effects)
            check = validate_before_state_pair(before, witness)
            write_new(arm_dir / "before_witness.json", witness)
            write_new(arm_dir / "before_witness_check.json", check)
            require(check["ok"], "BR_RESTORED_STATE_MISMATCH:" + arm + ":" + json.dumps(check["reasons"]))
        record("BOTH_RESTORED_STATES_MATCH_PRELUDE")
        for arm in ("B", "R"):
            backend = arms[arm]
            selected = backend._effect_reference(effects[arm])
            arm_rows, arm_units = execute_sequence(backend, ("C",), selected,
                maximum=plan["arm_policy_units"], deadline=deadline, record=record)
            arm_result = arm_rows[0]["result"]
            observed = effect_output(backend, arm_result["reference"]["effect_id"])
            after = backend.native.coordinator.restore_and_verify()
            require(len(after.traces) == 5 and backend.native.store.next_tick() == 6,
                    "BR_ARM_TICK_COUNT_CHANGED")
            for trace in after.traces:
                f.validate_contract(trace)
            arm_record = {"status": "ACCEPTED", "selected_effect_id": effects[arm],
                "input_producer": arm, "rows": arm_rows, "policy_units": arm_units,
                "output": observed, "after_recovery": {"head": asdict(after.head),
                    "state": after.state, "traces": list(after.traces)},
                "gpu_forward_audit": deepcopy(backend.audit),
                "runtime_identity_after": backend.identity(),
                "same_fixed_expectation": "L2", "remaining_policy_units": 8192-arm_units}
            require(backend.audit["calls"] > 0, "BR_NO_ARM_GPU_FORWARD")
            write_new(output / ("arm_" + arm) / "result.json", arm_record)
            result["arms"][arm] = arm_record
            backend.close()
            active.remove(backend)
        result["contrast"] = compare_outputs(result["arms"]["B"]["output"], result["arms"]["R"]["output"])
        _verified_image(output / "copies/master.sqlite", original_sha, plan["max_image_bytes"])
        _verified_image(database, original_sha, plan["max_image_bytes"])
        require(time.monotonic() < deadline, "BR_WORKER_DEADLINE")
        result["status"] = "BR_COMPONENT_EXECUTED"
    except BaseException as error:
        result.update(status="BR_CONSTRUCTION_REFUSED_OR_FAILED",
                      failure={"type": type(error).__name__, "message": str(error)})
        record("CONSTRUCTION_STOPPED", **result["failure"])
    finally:
        for backend in reversed(active):
            try:
                # Preserve native failure traces/state before closing, when available.
                path = backend.output / "failure_native_history.json"
                write_new(path, {"head": backend.head(),
                    "state": backend.native.store.load_state(),
                    "traces": list(backend.native.store.trace_events())})
            except Exception as error:
                result["cleanup_errors"].append("FAILURE_HISTORY:" + str(error))
            try:
                backend.close()
            except Exception as error:
                result["cleanup_errors"].append("BACKEND_CLOSE:" + str(error))
        result["postchecks"] = {}
        for name, read, expected in (("source", lambda: check_sources(plan), source),
                                    ("reservation", lambda: reservation_binding(plan), reservation)):
            try:
                require(read() == expected, "BR_POSTCHECK_CHANGED:" + name)
                result["postchecks"][name] = {"ok": True}
            except Exception as error:
                result["postchecks"][name] = {"ok": False, "type": type(error).__name__,
                                            "message": str(error)}
                result["cleanup_errors"].append("POSTCHECK:" + name + ":" + str(error))
        if result["cleanup_errors"]:
            result["status"] = "BR_CONSTRUCTION_REFUSED_OR_FAILED"
        result["finished_utc"] = datetime.now(timezone.utc).isoformat()
        result["files_sha256"] = {p.relative_to(output).as_posix(): file_hash(p)
            for p in sorted(output.rglob("*")) if p.is_file()}
        write_new(output / "construction_receipt.json", result)
    return result


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--output", required=True)
    parser.add_argument("--job", required=True)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--plan-sha256", required=True)
    args = parser.parse_args(argv)
    result = run(args.output, job=args.job, plan_path=args.plan, plan_sha256=args.plan_sha256)
    print(json.dumps({"status": result["status"], "job": result["job"], "boundary": BOUNDARY}))
    return 0 if result["status"] == "BR_COMPONENT_EXECUTED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
