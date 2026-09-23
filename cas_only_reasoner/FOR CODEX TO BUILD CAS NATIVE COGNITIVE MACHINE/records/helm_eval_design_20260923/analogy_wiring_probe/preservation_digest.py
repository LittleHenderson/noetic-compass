"""Preservation digest (Claude, independent checker). Rules: PREREG_ANALOGY_WIRING_PROBE_v0_2.md, "Preservation".

For every one of the 564 registry records and EVERY slot, the float32 logits Helm produces are written as
IEEE-754 bit patterns (hex), digested per record, and digested overall. A repaired container with its switch OFF
must reproduce the unchanged source's overall digest bit for bit, model by model. Forward passes only.

    python -B preservation_digest.py --model LABEL:SEED[:CHECKPOINT] [--model ...] --out FILE.json
        [--container-kwargs JSON] [--package-root DIR]
"""
import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
HERE = pathlib.Path(__file__).resolve().parent
DEFAULT_PACKAGE = HERE.parents[2]
MAX_START_C, STOP_C, MIN_FREE_MIB, WALL_SECONDS = 75, 80, 2048, 3600  # amendment A1: 3600


def gpu_telemetry():
    out = subprocess.run(["nvidia-smi", "--query-gpu=uuid,temperature.gpu,memory.free,utilization.gpu",
                          "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=20)
    uuid, temp, free, util = [v.strip() for v in out.stdout.strip().splitlines()[0].split(",")]
    return {"uuid": uuid, "temperature_c": int(temp), "memory_free_mib": int(free), "utilization_percent": int(util)}


def lf_sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", action="append", required=True)
    ap.add_argument("--container-kwargs", default="{}")
    ap.add_argument("--package-root", default=str(DEFAULT_PACKAGE))
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    if len(args.model) > 3:
        print("AT_MOST_3_MODELS_PER_INVOCATION"); sys.exit(6)
    started = time.monotonic()
    import torch
    if not torch.cuda.is_available():
        print("GPU_REQUIRED"); sys.exit(2)
    torch.use_deterministic_algorithms(True, warn_only=True)
    torch.backends.cudnn.deterministic, torch.backends.cudnn.benchmark = True, False
    admission = gpu_telemetry()
    if admission["temperature_c"] > MAX_START_C or admission["memory_free_mib"] < MIN_FREE_MIB:
        print("GPU_UNAVAILABLE", admission); sys.exit(3)
    device = torch.device("cuda", 0)
    package = pathlib.Path(args.package_root).resolve()
    sys.dont_write_bytecode = True
    for p in (package, package / "research" / "CAS_META_2_COMPOSITION"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    from cas_meta2.typed_teaching import pointer_contract as contract, pointer_inputs, pointer_learner as PL, slots
    from cncm.typed_matched_worker import _framework
    t0 = time.monotonic()
    frozen = contract.load_material(package)[0]
    packets = dict(contract.public_packets(frozen))
    load_seconds = time.monotonic() - t0
    tagger = PL.role_tagger(str(package))
    ids = sorted(packets)
    prepared = {}
    for rid in ids:
        packet = packets[rid]
        plan = slots.compile_slots(packet)
        reading = pointer_inputs.read_packet(packet)
        indicators = tagger.indicators(packet) if reading["query"]["kind_name"] == "role_set" else [0] * PL.CLAUSE_COUNT
        prepared[rid] = (plan, reading, indicators)
    kwargs = json.loads(args.container_kwargs)
    results = []
    for spec in args.model:
        label, seed, *ck = spec.split(":", 2)
        framework = _framework(torch, device, int(seed))
        model = PL._build_container(torch, framework, device, **kwargs)
        sha = None
        if ck:
            import io
            raw = pathlib.Path(ck[0]).read_bytes(); sha = hashlib.sha256(raw).hexdigest()
            model.load_state_dict(torch.load(io.BytesIO(raw), map_location="cpu", weights_only=True)["model_state"], strict=True)
        model.eval()
        state = model.state_dict()
        per_record = {}
        with torch.no_grad():
            for k, rid in enumerate(ids):
                if time.monotonic() - started > WALL_SECONDS:
                    print("WALL_LIMIT_REACHED"); sys.exit(4)
                if k % 50 == 0 and gpu_telemetry()["temperature_c"] >= STOP_C:
                    print("GPU_TEMPERATURE_STOP"); sys.exit(5)
                plan, reading, indicators = prepared[rid]
                reading = dict(reading); reading["_device"] = device
                rows = PL.GraphForward(torch, model, reading, device).head_logits(plan, indicators)
                bits = {sid: ["%08x" % (v & 0xFFFFFFFF) for v in t.detach().float().contiguous().view(torch.int32).cpu().tolist()]
                        for sid, t in rows.items()}
                per_record[rid] = hashlib.sha256(json.dumps(bits, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        overall = hashlib.sha256("\n".join("%s %s" % (r, per_record[r]) for r in ids).encode()).hexdigest()
        results.append({"label": label, "init_seed": int(seed), "checkpoint": ck[0] if ck else None,
                        "checkpoint_sha256": sha, "records": len(ids), "overall_digest": overall,
                        "parameter_count": sum(int(p.numel()) for p in model.parameters()),
                        "state_keys_shapes_digest": hashlib.sha256(json.dumps(
                            sorted((k, list(v.shape)) for k, v in state.items())).encode()).hexdigest(),
                        "per_record": per_record})
        print(json.dumps({"label": label, "overall_digest": overall, "records": len(ids)}))
        write_out(args, results, package, frozen, load_seconds, admission, torch, started, final=False)
    write_out(args, results, package, frozen, load_seconds, admission, torch, started, final=True)


def write_out(args, results, package, frozen, load_seconds, admission, torch, started, final):
    src = ["research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/" + f for f in
           ("pointer_learner.py", "pointer_inputs.py", "slots.py", "pointer_contract.py")] + ["cncm/typed_matched_worker.py"]
    out = {"schema": "claude.helm-preservation-digest/0.1", "complete": final, "results": results, "package_root": str(package),
           "source_sha256_lf": {f: lf_sha(package / f) for f in src}, "course_digest": frozen["course_digest"],
           "tool_sha256_lf": lf_sha(__file__), "material_load_seconds": load_seconds,
           "gpu": {"admission": admission, "end": gpu_telemetry()}, "torch": torch.__version__,
           "wall_seconds": time.monotonic() - started,
           "work": "forward passes only under torch.no_grad(); no optimizer, no update, no checkpoint written"}
    with open(args.out, "w", encoding="utf-8", newline="") as handle:
        handle.write(json.dumps(out, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
