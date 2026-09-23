"""Analogy wiring probe (Claude, independent checker). Rules: PREREG_ANALOGY_WIRING_PROBE.md in this folder.

Question: does changing the arrangement Helm is asked to compare (the analogy FOCUS world) change the scores
Helm gives the OTHER candidate worlds? This is a wiring check, forward passes only. It does not read gold
answers, does not train, and never writes a checkpoint.

Usage (run from the CNCM package root, with the GPU venv):
    python -B records/helm_eval_design_20260923/analogy_wiring_probe/analogy_wiring_probe.py \
        --model h2_init_20260917:20260917 --out <file.json>
    python -B ...analogy_wiring_probe.py \
        --model h2_final_20260918:20260918:records/typed_pointer_001/receipt_20260918/checkpoints/final.pt --out <file.json>
    --container-kwargs '{"...": ...}'   passes keyword arguments to `_build_container` (for a repaired
                                         container that exposes its switch that way; empty = unchanged call)
    --package-root <dir>                 the CNCM package whose Helm source is probed (default: this package)
"""
import argparse
import copy
import hashlib
import itertools
import json
import pathlib
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
DEFAULT_PACKAGE = HERE.parents[2]
TAU_ZERO, TAU_PRESENT, PRESENT_SHARE = 1e-6, 1e-4, 0.90
WITNESSES = ("typed-input-092dc3b89a0480d462945ca7447bac511c81358714e48059922cd9b469f8a53e",
             "typed-input-0df25be340de7c545d7cdac679233a291d8d134b872c808ff098130afae7171a")
MAX_START_C, STOP_C, MIN_FREE_MIB, WALL_SECONDS = 75, 80, 2048, 900


def gpu_telemetry():
    out = subprocess.run(["nvidia-smi", "--query-gpu=uuid,temperature.gpu,memory.free,utilization.gpu",
                          "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=20)
    uuid, temp, free, util = [v.strip() for v in out.stdout.strip().splitlines()[0].split(",")]
    return {"uuid": uuid, "temperature_c": int(temp), "memory_free_mib": int(free), "utilization_percent": int(util)}


def lf_sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def canon_shape(n, edges):
    best = None
    for p in itertools.permutations(range(n)):
        key = tuple(sorted((p[a], p[b]) for a, b in edges))
        if best is None or key < best:
            best = key
    return (n, best)


def alternative_shapes(bank_worlds):
    """Every distinct contains-shape in the bank, by node count, plus the two other 3-node DAGs (the bank has
    only the 3-chain at size 3, so without them a 3-node focus could not be rewired at all)."""
    shapes = {}
    for w in bank_worlds:
        refs = [x["ref"] for x in w["nodes"]]
        idx = {r: i for i, r in enumerate(refs)}
        s = canon_shape(len(refs), [(idx[c["source"]], idx[c["target"]]) for c in w["contains"]])
        shapes[s] = list(s[1])
    for extra in ([(0, 1), (0, 2)], [(0, 2), (1, 2)]):
        s = canon_shape(3, extra)
        shapes.setdefault(s, list(s[1]))
    by_size = {}
    for (n, key), edges in shapes.items():
        by_size.setdefault(n, []).append(((n, key), edges))
    return by_size


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", action="append", required=True,
                    help="label:init_seed[:checkpoint_path]; repeat to probe several models after ONE course load")
    ap.add_argument("--container-kwargs", default="{}")
    ap.add_argument("--package-root", default=str(DEFAULT_PACKAGE))
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    started = time.monotonic()

    import torch
    if not torch.cuda.is_available():
        print("GPU_REQUIRED")
        sys.exit(2)
    admission = gpu_telemetry()
    if admission["temperature_c"] > MAX_START_C or admission["memory_free_mib"] < MIN_FREE_MIB:
        print("GPU_UNAVAILABLE", admission)
        sys.exit(3)
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
    bank = json.loads((package / "records/typed_course_001/checks_002/public_course.json").read_text(encoding="utf-8"))["bank"]["worlds"]
    alternatives = alternative_shapes(bank)

    kwargs = json.loads(args.container_kwargs)
    analogy_ids = sorted(rid for rid, pk in packets.items() if pk["record"]["query"]["kind"] == "analogy")
    cache = {rid: (slots.compile_slots(packets[rid]), pointer_inputs.read_packet(packets[rid])) for rid in analogy_ids}
    source_files = ["research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/" + f for f in
                    ("pointer_learner.py", "pointer_inputs.py", "slots.py", "pointer_contract.py")] + ["cncm/typed_matched_worker.py"]
    results = []
    for spec in args.model:
        parts = spec.split(":", 2)
        results.append(probe_one(torch, device, PL, _framework, packets, cache, analogy_ids, alternatives, kwargs,
                                 label=parts[0], init_seed=int(parts[1]), checkpoint=parts[2] if len(parts) > 2 else None,
                                 started=started, admission=admission))
    out = {"schema": "claude.analogy-wiring-probe/0.1", "results": results,
           "rules": {"tau_zero": TAU_ZERO, "tau_present": TAU_PRESENT, "present_share": PRESENT_SHARE,
                     "prereg_sha256_lf": lf_sha(HERE / "PREREG_ANALOGY_WIRING_PROBE.md"),
                     "probe_sha256_lf": lf_sha(__file__)},
           "package_root": str(package), "source_sha256_lf": {f: lf_sha(package / f) for f in source_files},
           "course_digest": frozen["course_digest"], "material_load_seconds": load_seconds,
           "gpu": {"admission": admission, "end": gpu_telemetry()},
           "torch": torch.__version__, "python": sys.version.split()[0], "wall_seconds": time.monotonic() - started,
           "work": "forward passes only under torch.no_grad(); no optimizer, no update, no checkpoint written"}
    with open(args.out, "w", encoding="utf-8", newline="") as handle:
        handle.write(json.dumps(out, indent=1, sort_keys=True))
    for r in results:
        print(json.dumps({k: r[k] for k in ("label", "verdict", "M1_witness_max_abs_diff", "M2_max_spread_non_focus",
                                            "M3_max", "M3_share_above_tau_present", "analogy_records")}))


def probe_one(torch, device, PL, _framework, packets, cache, analogy_ids, alternatives, kwargs, *, label, init_seed,
              checkpoint, started, admission):
    framework = _framework(torch, device, init_seed)
    model = PL._build_container(torch, framework, device, **kwargs)
    checkpoint_sha = None
    if checkpoint:
        raw = pathlib.Path(checkpoint).read_bytes()
        checkpoint_sha = hashlib.sha256(raw).hexdigest()
        import io
        payload = torch.load(io.BytesIO(raw), map_location="cpu", weights_only=True)
        model.load_state_dict(payload["model_state"], strict=True)
    model.eval()
    parameter_count = sum(int(p.numel()) for p in model.parameters())

    def analogy_scores(rid, rewire=None):
        plan, reading = cache[rid]
        reading = copy.deepcopy(reading)
        if rewire is not None:
            reading["worlds"][reading["focus_world_id"]]["contains"] = [list(e) for e in rewire]
        reading["_device"] = device
        forward = PL.GraphForward(torch, model, reading, device)
        rows = forward.head_logits(plan, [0] * PL.CLAUSE_COUNT)
        slots_ = [s for s in plan["slots"] if s["field"] == "world_id"]
        assert len(slots_) == 1, "ANALOGY_SLOT_COUNT"
        slot = slots_[0]
        values = rows[slot["slot_id"]].detach().double().cpu().tolist()
        out = {}
        for symbol, value in zip(slot["symbols"], values):
            if symbol != "NO_MATCH":
                out[PL._world_alias_table_for(reading, symbol)] = value
        return reading["focus_world_id"], out, reading

    base = {}
    m3 = {}
    top1_changes = 0
    rewires_total = 0
    focus_self_change = 0.0
    last_temp = admission["temperature_c"]
    with torch.no_grad():
        for n_done, rid in enumerate(analogy_ids):
            if time.monotonic() - started > WALL_SECONDS:
                print("WALL_LIMIT_REACHED")
                sys.exit(4)
            if n_done % 10 == 0:
                last_temp = gpu_telemetry()["temperature_c"]
                if last_temp >= STOP_C:
                    print("GPU_TEMPERATURE_STOP", last_temp)
                    sys.exit(5)
            focus, scores, reading = analogy_scores(rid)
            base[rid] = (focus, scores)
            graph = reading["worlds"][focus]
            n = graph["node_count"]
            own = canon_shape(n, [tuple(e) for e in graph["contains"]])
            whole = next((i for i, node in enumerate(graph["nodes"]) if node.get("is_declared_whole")), 0)
            worst = 0.0
            for shape, edges in alternatives.get(n, []):
                if shape == own:
                    continue
                # a fixed relabelling: the alternative's canonical node 0 goes onto the declared whole, the rest
                # in list order. Any fixed relabelling serves a WIRING probe; it asserts nothing about meaning.
                order = [whole] + [i for i in range(n) if i != whole]
                rewired = [(order[a], order[b]) for a, b in edges]
                _, changed, _ = analogy_scores(rid, rewire=rewired)
                rewires_total += 1
                diffs = [abs(changed[c] - scores[c]) for c in scores if c != focus]
                worst = max(worst, max(diffs))
                focus_self_change = max(focus_self_change, abs(changed[focus] - scores[focus]))
                if max(changed, key=changed.get) != max(scores, key=scores.get):
                    top1_changes += 1
            m3[rid] = worst

    fa, sa = base[WITNESSES[0]]
    fb, sb = base[WITNESSES[1]]
    shared = [c for c in sa if c in sb and c not in (fa, fb)]
    m1 = max(abs(sa[c] - sb[c]) for c in shared)
    received = {}
    for focus, scores in base.values():
        for c, v in scores.items():
            if c != focus:
                received.setdefault(c, []).append(v)
    m2 = max(max(v) - min(v) for v in received.values())
    share_present = sum(1 for v in m3.values() if v > TAU_PRESENT) / len(m3)
    if m1 <= TAU_ZERO and m2 <= TAU_ZERO and all(v <= TAU_ZERO for v in m3.values()):
        verdict = "FOCUS_TO_CANDIDATE_DEPENDENCY_ABSENT"
    elif m1 > TAU_PRESENT and share_present >= PRESENT_SHARE:
        verdict = "FOCUS_TO_CANDIDATE_DEPENDENCY_PRESENT"
    else:
        verdict = "MIXED"

    return {
        "label": label, "verdict": verdict,
        "M1_witness_max_abs_diff": m1, "M1_shared_non_focus_candidates": len(shared),
        "M1_witness_focus_worlds": [fa, fb],
        "M1_witness_top1": [max(sa, key=sa.get), max(sb, key=sb.get)],
        "M2_max_spread_non_focus": m2, "M2_candidates": len(received),
        "M3_max": max(m3.values()), "M3_min": min(m3.values()), "M3_share_above_tau_present": share_present,
        "M3_records": len(m3), "M3_rewires_total": rewires_total,
        "reported_not_scored": {"top1_changes_under_rewire": top1_changes,
                                "focus_candidate_own_max_change": focus_self_change},
        "analogy_records": len(analogy_ids), "distinct_focus_worlds": len({f for f, _ in base.values()}),
        "model": {"init_seed": init_seed, "checkpoint": checkpoint, "checkpoint_sha256": checkpoint_sha,
                  "container_kwargs": kwargs, "parameter_count": parameter_count},
        "last_temperature_c": last_temp,
    }


if __name__ == "__main__":
    main()
