"""Analogy wiring probe v0.2 (Claude, independent checker). Rules: PREREG_ANALOGY_WIRING_PROBE_v0_2.md.

Does changing what Helm is asked to compare (the analogy FOCUS world's graph or domain) change WHICH candidate
worlds Helm favours -- not merely shift every score by the same amount? Forward passes only; no gold answers,
no training, no checkpoint written. Counterfactuals are built at the PACKET level and re-read exactly as the
learner reads them.

    python -B analogy_wiring_probe_v0_2.py --model LABEL:SEED[:CHECKPOINT] [--model ...] --out FILE.json
        [--container-kwargs JSON] [--switch-attr NAME --switch-expect true|false] [--package-root DIR]
"""
import argparse
import copy
import hashlib
import itertools
import json
import os
import pathlib
import statistics
import subprocess
import sys
import time

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
HERE = pathlib.Path(__file__).resolve().parent
DEFAULT_PACKAGE = HERE.parents[2]
TAU, NOISE_MAX, RC_MIN, SHARE_FOCI, LEAK_RATIO = 1e-5, 1e-6, 1e-2, 22, 0.1
WITNESSES = ("typed-input-092dc3b89a0480d462945ca7447bac511c81358714e48059922cd9b469f8a53e",
             "typed-input-0df25be340de7c545d7cdac679233a291d8d134b872c808ff098130afae7171a")
ALTERNATIVES = {  # frozen in the prereg, canonical edge form
    4: [((0, 1), (0, 2), (0, 3)), ((0, 1), (0, 2), (1, 3), (2, 3)), ((0, 1), (1, 2), (2, 3)),
        ((0, 1), (0, 2), (3, 1)), ((0, 1), (0, 2), (1, 3))],
    3: [((0, 1), (1, 2)), ((0, 1), (0, 2)), ((0, 2), (1, 2)), ((0, 1), (0, 2), (1, 2))],
}
MAX_START_C, STOP_C, MIN_FREE_MIB, WALL_SECONDS = 75, 80, 2048, 3600  # amendment A1: 3600


def gpu_telemetry():
    out = subprocess.run(["nvidia-smi", "--query-gpu=uuid,temperature.gpu,memory.free,utilization.gpu",
                          "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=20)
    uuid, temp, free, util = [v.strip() for v in out.stdout.strip().splitlines()[0].split(",")]
    return {"uuid": uuid, "temperature_c": int(temp), "memory_free_mib": int(free), "utilization_percent": int(util)}


def lf_sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def canon(n, edges):
    best = None
    for p in itertools.permutations(range(n)):
        key = tuple(sorted((p[a], p[b]) for a, b in edges))
        if best is None or key < best:
            best = key
    return (n, best)


def world_shape(world, node_index):
    idx = node_index(world)
    return canon(len(world["nodes"]), [(idx[e["source"]], idx[e["target"]]) for e in world["contains"]])


def rewire(world, edges, node_index):
    """A copy of `world` whose contains-graph is `edges` (canonical indices), node 0 on the declared whole."""
    idx = node_index(world)
    refs = sorted(idx, key=idx.get)
    whole = world["declared_whole"]
    order = [whole] + [r for r in refs if r != whole]
    new = copy.deepcopy(world)
    new["contains"] = [{"ref": "%s/probe_e%d" % (world["world_id"], k), "source": order[a], "target": order[b]}
                       for k, (a, b) in enumerate(edges)]
    return new


def zscores(scores, X):
    vals = [scores[c] for c in X]
    mu, sd = statistics.fmean(vals), statistics.pstdev(vals)
    sd = sd if sd > 0 else 1.0
    return {c: (scores[c] - mu) / sd for c in X}


def discordant_fraction(a, b, X):
    pairs = list(itertools.combinations(sorted(X), 2))
    bad = sum(1 for i, j in pairs if (a[i] - a[j]) * (b[i] - b[j]) < 0)
    return bad / len(pairs) if pairs else 0.0


def decision(scores):
    """The analogy slot's argmax with NO_MATCH pinned at logit 0; a tie with NO_MATCH counts as NO_MATCH."""
    best = max(scores, key=scores.get)
    return best if scores[best] > 0.0 else "NO_MATCH"


def set_contrast(dz, A, A2):
    if not A or not A2:
        return None
    return abs(statistics.fmean(dz[c] for c in A2) - statistics.fmean(dz[c] for c in A))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", action="append", required=True)
    ap.add_argument("--container-kwargs", default="{}")
    ap.add_argument("--switch-attr", default=None)
    ap.add_argument("--switch-expect", default=None, choices=[None, "true", "false"])
    ap.add_argument("--package-root", default=str(DEFAULT_PACKAGE))
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    require_models = len(args.model)
    if require_models > 3:
        print("AT_MOST_3_MODELS_PER_INVOCATION")
        sys.exit(6)
    started = time.monotonic()

    import torch
    if not torch.cuda.is_available():
        print("GPU_REQUIRED")
        sys.exit(2)
    torch.use_deterministic_algorithms(True, warn_only=True)
    torch.backends.cudnn.deterministic, torch.backends.cudnn.benchmark = True, False
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
    node_index = pointer_inputs._node_index

    t0 = time.monotonic()
    frozen = contract.load_material(package)[0]
    packets = dict(contract.public_packets(frozen))
    load_seconds = time.monotonic() - t0
    analogy_ids = sorted(rid for rid, pk in packets.items() if pk["record"]["query"]["kind"] == "analogy")
    focus_of = {rid: packets[rid]["source"]["focus_world_id"] for rid in analogy_ids}
    rep = {}
    for rid in analogy_ids:
        rep.setdefault(focus_of[rid], rid)
    kwargs = json.loads(args.container_kwargs)

    source_files = ["research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/" + f for f in
                    ("pointer_learner.py", "pointer_inputs.py", "slots.py", "pointer_contract.py")] + ["cncm/typed_matched_worker.py"]
    results = []
    for spec in args.model:
        label, seed, *ck = spec.split(":", 2)
        results.append(probe_one(torch, device, PL, slots, pointer_inputs, _framework, node_index, packets, analogy_ids,
                                 focus_of, rep, kwargs, args, label=label, init_seed=int(seed),
                                 checkpoint=ck[0] if ck else None, started=started))
        write_out(args, results, frozen, package, source_files, load_seconds, admission, torch, started)
    write_out(args, results, frozen, package, source_files, load_seconds, admission, torch, started, final=True)
    for r in results:
        print(json.dumps({k: r[k] for k in ("label", "verdict", "switch", "M0_delta0", "M1z", "M2z", "summary")}))


def write_out(args, results, frozen, package, source_files, load_seconds, admission, torch, started, final=False):
    out = {"complete": final, "schema": "claude.analogy-wiring-probe/0.2", "results": results,
           "rules": {"tau": TAU, "noise_max": NOISE_MAX, "rc_min": RC_MIN, "share_foci_required": SHARE_FOCI,
                     "leak_ratio": LEAK_RATIO, "alternatives": {str(k): v for k, v in ALTERNATIVES.items()},
                     "prereg_sha256_lf": lf_sha(HERE / "PREREG_ANALOGY_WIRING_PROBE_v0_2.md"),
                     "probe_sha256_lf": lf_sha(__file__)},
           "package_root": str(package), "source_sha256_lf": {f: lf_sha(package / f) for f in source_files},
           "course_digest": frozen["course_digest"], "material_load_seconds": load_seconds,
           "determinism": {"CUBLAS_WORKSPACE_CONFIG": os.environ.get("CUBLAS_WORKSPACE_CONFIG"),
                           "deterministic_algorithms": torch.are_deterministic_algorithms_enabled()},
           "gpu": {"admission": admission, "end": gpu_telemetry()}, "torch": torch.__version__,
           "python": sys.version.split()[0], "wall_seconds": time.monotonic() - started,
           "work": "forward passes only under torch.no_grad(); no optimizer, no update, no checkpoint written"}
    with open(args.out, "w", encoding="utf-8", newline="") as handle:
        handle.write(json.dumps(out, indent=1, sort_keys=True))


def probe_one(torch, device, PL, slots, pointer_inputs, _framework, node_index, packets, analogy_ids, focus_of, rep,
              kwargs, args, *, label, init_seed, checkpoint, started):
    framework = _framework(torch, device, init_seed)
    model = PL._build_container(torch, framework, device, **kwargs)
    checkpoint_sha = None
    if checkpoint:
        import io
        raw = pathlib.Path(checkpoint).read_bytes()
        checkpoint_sha = hashlib.sha256(raw).hexdigest()
        payload = torch.load(io.BytesIO(raw), map_location="cpu", weights_only=True)
        model.load_state_dict(payload["model_state"], strict=True)
    model.eval()
    switch = "NOT_A_REPAIRED_CONTAINER"
    if args.switch_attr:
        value = getattr(model, args.switch_attr)
        assert type(value) is bool, "SWITCH_ATTRIBUTE_NOT_BOOL"
        assert args.switch_expect is None or value == (args.switch_expect == "true"), "SWITCH_STATE_MISMATCH"
        switch = value
    parameter_count = sum(int(p.numel()) for p in model.parameters())
    # Amendment A1: `slots.compile_slots` validates the whole source bank and rejects any world whose contains-list
    # was altered (TYPED_SOURCE_WORLD_RECONSTRUCTION), so the slot PLAN is always taken from the unmodified packet.
    # The analogy slot's symbols are the bank's world aliases, which no counterfactual touches. The READING of a
    # counterfactual packet comes from `pointer_inputs.read_packet` -- the learner's own reader -- and every copy of
    # the changed world inside it is asserted consistent.
    base_plan = {rid: slots.compile_slots(packets[rid]) for rid in analogy_ids}
    base_read = {rid: pointer_inputs.read_packet(packets[rid]) for rid in analogy_ids}

    def scores_for(rid, packet, changed_world=None):
        plan = base_plan[rid]
        slot = [s for s in plan["slots"] if s["field"] == "world_id"]
        assert len(slot) == 1, "ANALOGY_SLOT_COUNT"
        if changed_world is None:
            reading = copy.deepcopy(base_read[rid])
        else:
            reading = pointer_inputs.read_packet(packet)
            if changed_world == reading["focus_world_id"]:
                assert reading["focus_world"]["contains"] == reading["worlds"][changed_world]["contains"], "FOCUS_COPIES_DISAGREE"
        reading["_device"] = device
        forward = PL.GraphForward(torch, model, reading, device)
        rows = forward.head_logits(plan, [0] * PL.CLAUSE_COUNT)
        values = rows[slot[0]["slot_id"]].detach().double().cpu().tolist()
        return {PL._world_alias_table_for(reading, sym): v for sym, v in zip(slot[0]["symbols"], values) if sym != "NO_MATCH"}

    def with_world(packet, world_id, new_world):
        p = copy.deepcopy(packet)
        worlds = p["source"]["worlds"]
        worlds[[w["world_id"] for w in worlds].index(world_id)] = new_world
        return p

    delta0, base_s, base_meta = 0.0, {}, {}
    per_focus, top1_changes = {}, 0
    last_temp = None
    with torch.no_grad():
        for k, rid in enumerate(analogy_ids):
            if time.monotonic() - started > WALL_SECONDS:
                print("WALL_LIMIT_REACHED"); sys.exit(4)
            if k % 10 == 0:
                last_temp = gpu_telemetry()["temperature_c"]
                if last_temp >= STOP_C:
                    print("GPU_TEMPERATURE_STOP", last_temp); sys.exit(5)
            s1 = scores_for(rid, packets[rid])
            s2 = scores_for(rid, packets[rid])
            delta0 = max(delta0, max(abs(s1[c] - s2[c]) for c in s1))
            base_s[rid] = s1
        for f, rid in sorted(rep.items()):
            if time.monotonic() - started > WALL_SECONDS:
                print("WALL_LIMIT_REACHED"); sys.exit(4)
            packet = packets[rid]
            worlds = {w["world_id"]: w for w in packet["source"]["worlds"]}
            domain = {w: worlds[w]["declarations"]["domain"] for w in worlds}
            shape = {w: world_shape(worlds[w], node_index) for w in worlds}
            X = [c for c in base_s[rid] if c != f and domain[c] != domain[f]]
            z0 = zscores(base_s[rid], X)
            n = len(worlds[f]["nodes"])
            A = [c for c in X if shape[c] == shape[f]]
            m3, kf, rcs, leaks, m5 = 0.0, 0.0, [], [], []
            for edges in ALTERNATIVES.get(n, []):
                new_shape = canon(n, list(edges))
                if new_shape == shape[f]:
                    continue
                s = scores_for(rid, with_world(packet, f, rewire(worlds[f], edges, node_index)), changed_world=f)
                z = zscores(s, X)
                dz = {c: z[c] - z0[c] for c in X}
                m3 = max(m3, max(abs(v) for v in dz.values()))
                kf = max(kf, discordant_fraction(z0, z, X))
                A2 = [c for c in X if shape[c] == new_shape]
                rc = set_contrast(dz, A, A2)
                if rc is not None:
                    rcs.append(rc)
                m5.append({"new_accepted_empty": not A2,
                           "margin_change": max(s[c] for c in X) - max(base_s[rid][c] for c in X)})
                if decision(s) != decision(base_s[rid]):
                    top1_changes += 1
            # bystander control: the same alternatives applied to one non-focus world of the focus's size
            bystanders = sorted(c for c in X if len(worlds[c]["nodes"]) == n)
            if bystanders:
                b = bystanders[0]
                for edges in ALTERNATIVES.get(n, []):
                    if canon(n, list(edges)) == shape[b]:
                        continue
                    s = scores_for(rid, with_world(packet, b, rewire(worlds[b], edges, node_index)), changed_world=b)
                    z = zscores(s, X)
                    leaks.append(max(abs(z[c] - z0[c]) for c in X if c != b))
            # domain counterfactual
            rc_dom = []
            X_all = [c for c in base_s[rid] if c != f]
            zb_all = zscores(base_s[rid], X_all)
            for other in sorted(set(domain.values()) - {domain[f]}):
                nw = copy.deepcopy(worlds[f]); nw["declarations"]["domain"] = other
                s = scores_for(rid, with_world(packet, f, nw), changed_world=f)
                z = zscores(s, X_all)
                dz = {c: z[c] - zb_all[c] for c in X_all}
                # isomorphs that STOP being answers (they sit in the new focus domain) versus isomorphs that
                # START being answers (they sit in the old focus domain); standardised over ALL non-focus worlds
                now_invalid = [c for c in X_all if shape[c] == shape[f] and domain[c] == other]
                now_valid = [c for c in X_all if shape[c] == shape[f] and domain[c] == domain[f]]
                rc = set_contrast(dz, now_invalid, now_valid)
                if rc is not None:
                    rc_dom.append(rc)
            per_focus[f] = {"record": rid, "nodes": n, "X": len(X), "A": len(A), "M3z": m3, "K": kf,
                            "RC": statistics.fmean(rcs) if rcs else None, "L": max(leaks) if leaks else None,
                            "RC_dom": statistics.fmean(rc_dom) if rc_dom else None, "M5": m5}

    fa, fb = focus_of[WITNESSES[0]], focus_of[WITNESSES[1]]
    wa, wb = base_s[WITNESSES[0]], base_s[WITNESSES[1]]
    dom_all = {w["world_id"]: w["declarations"]["domain"] for w in packets[WITNESSES[0]]["source"]["worlds"]}
    Xw = [c for c in wa if c not in (fa, fb) and dom_all[c] != dom_all[fa] and dom_all[c] != dom_all[fb]]
    za, zb = zscores(wa, Xw), zscores(wb, Xw)
    m1z = max(abs(za[c] - zb[c]) for c in Xw)
    m1k = discordant_fraction(za, zb, Xw)
    # X depends only on the focus DOMAIN (every same-domain world, the focus included, is excluded), so records
    # are compared WITHIN a focus-domain group, where X is the identical set of worlds.
    received = {}
    for rid in analogy_ids:
        f = focus_of[rid]
        worlds = {w["world_id"]: w for w in packets[rid]["source"]["worlds"]}
        fdom = worlds[f]["declarations"]["domain"]
        X = [c for c in base_s[rid] if c != f and worlds[c]["declarations"]["domain"] != fdom]
        for c, v in zscores(base_s[rid], X).items():
            received.setdefault((fdom, c), []).append(v)
    m2z = max(max(v) - min(v) for v in received.values())

    floor = max(1e-3, 100 * delta0)
    foci = list(per_focus.values())
    count = lambda pred: sum(1 for p in foci if pred(p))
    rc_vals = [p["RC"] for p in foci if p["RC"] is not None]
    summary = {
        "foci": len(foci), "K_positive": count(lambda p: p["K"] > 0),
        "M3z_above_floor": count(lambda p: p["M3z"] >= floor),
        "median_RC": statistics.median(rc_vals) if rc_vals else None,
        "bystander_ok": count(lambda p: p["L"] is not None and p["L"] <= LEAK_RATIO * p["M3z"]),
        "RC_dom_ok": count(lambda p: p["RC_dom"] is not None and p["RC_dom"] >= RC_MIN),
        "max_M3z": max(p["M3z"] for p in foci), "max_K": max(p["K"] for p in foci),
        "top1_changes_reported_not_scored": top1_changes, "effect_floor": floor,
    }
    graph_core = (summary["K_positive"] >= SHARE_FOCI and summary["M3z_above_floor"] >= SHARE_FOCI
                  and summary["median_RC"] is not None and summary["median_RC"] >= RC_MIN)
    if delta0 > NOISE_MAX:
        verdict = "INVALID_NONDETERMINISTIC"
    elif m1z <= TAU and m2z <= TAU and all(p["M3z"] <= TAU and p["K"] == 0 for p in foci):
        verdict = "FOCUS_TO_CANDIDATE_DEPENDENCY_ABSENT"
    elif graph_core and summary["bystander_ok"] >= SHARE_FOCI:
        verdict = "PRESENT_GRAPH_AND_DOMAIN" if summary["RC_dom_ok"] >= SHARE_FOCI else "PRESENT_GRAPH"
    elif graph_core:
        verdict = "COUPLED_NOT_COMPARISON"
    else:
        verdict = "MIXED"
    return {"label": label, "verdict": verdict, "switch": switch, "M0_delta0": delta0, "M1z": m1z,
            "M1_kendall_discordant": m1k, "M1_cross_domain_shared": len(Xw), "M2z": m2z, "summary": summary,
            "per_focus": per_focus, "analogy_records": len(analogy_ids),
            "model": {"init_seed": init_seed, "checkpoint": checkpoint, "checkpoint_sha256": checkpoint_sha,
                      "container_kwargs": kwargs, "parameter_count": parameter_count},
            "last_temperature_c": last_temp}


if __name__ == "__main__":
    main()
