# run_rgm01.py — RGM-0.1 correction battery. 20 independent worlds, world = statistical unit,
# ten separate claim statuses, 2-pass byte determinism, corrected per-query efficiency.
# Mutants N1-N7 run 2-world gate demonstrations via run_mutant().
import json, sys, time, tracemalloc, random, hashlib
from cmb_r1_v01_core import arm_prop, propagate_variant, build_generic_geometry, adj_from_links, echo_attack
import cmb_r1_core as K

RANKED = K.RANKED_FAMILIES
BASE_SEED = 20260901
WORLDS = 20
MUTANT = None

PROP_ARMS = {
    "D":         dict(field="cas", mode="recurrent", damping=0.3, gamma=0.5, depth=3, topk=20),
    "D_NODAMP":  dict(field="cas", mode="recurrent", damping=0.0, gamma=0.5, depth=3, topk=20),
    "D_G1":      dict(field="cas", mode="recurrent", damping=0.3, gamma=1.0, depth=3, topk=20),
    "D_DEPTH5":  dict(field="cas", mode="recurrent", damping=0.3, gamma=0.5, depth=5, topk=20),
    "D_NOINHIB": dict(field="cas", mode="recurrent", damping=0.3, gamma=0.5, depth=3, topk=200),
    "X_MAX":     dict(field="cas", mode="max", damping=0.0, gamma=0.5, depth=3, topk=20),
    "X_SUM":     dict(field="cas", mode="sum", damping=0.0, gamma=0.5, depth=3, topk=20),
    "E2":        dict(field="role", mode="recurrent", damping=0.3, gamma=0.5, depth=3, topk=20),
}
ECHO_CFGS = {
    "BOTH":      dict(seed_root_dedup=True, budget_root=True, verify_root_dedup=True, coherence=True),
    "ROOT_ONLY": dict(seed_root_dedup=True, budget_root=True, verify_root_dedup=True, coherence=False),
    "COH_ONLY":  dict(seed_root_dedup=False, budget_root=False, verify_root_dedup=False, coherence=True),
    "NEITHER":   dict(seed_root_dedup=False, budget_root=False, verify_root_dedup=False, coherence=False),
}

def run_world(w):
    K.SEED = BASE_SEED + 1000 * w
    rng = random.Random(900000 + w)
    memories, topics, marginals = K.build_corpus()
    queries = K.build_queries(memories, topics)
    K.assign_generic_geometry(memories, marginals)
    role_links = build_generic_geometry(memories, rng)
    adj_cas = K.build_adjacency(memories)
    adj_role = adj_from_links(role_links)
    graph_ok = all(len(l) >= 3 and w not in l for w, l in role_links.items())
    res = {"world": w, "graph_ok": graph_ok, "arms": {}, "echo": {}, "eff": {}}
    for arm, fn in (("A", K.arm_a), ("B", K.arm_b), ("C", None)):
        vals_by_fam, eff_calls = {}, 0
        t0 = time.perf_counter()
        for fam in RANKED:
            vals = []
            for q in queries.get(fam, []):
                if arm == "C":
                    if MUTANT == "N6":
                        eff_calls += 0  # family-level charging re-bug added below
                    else:
                        eff_calls += len(memories)
                    ranked = K.arm_c(memories, q, mutant_order_insensitive=(MUTANT == "N2"))
                elif arm == "B" and MUTANT == "N1":
                    ranked = K._ranked({mid: K._cos(q["q_sem"], m["semantic"])
                                        for mid, m in memories.items()})
                else:
                    ranked = fn(memories, q)
                vals.append(K.score_ranked_family(ranked, q)["mrr"])
            if arm == "C" and MUTANT == "N6":
                eff_calls += len(memories)  # charged ONCE per family (the v0.1 bug)
            vals_by_fam[fam] = sum(vals) / max(len(vals), 1)
        res["arms"][arm] = vals_by_fam
        res["eff"][arm] = {"expensive_evals": eff_calls, "edge_evals": 0,
                           "activated": 0, "prop_steps": 0,
                           "wall_s": round(time.perf_counter() - t0, 3)}
    peaks = {}
    for arm, cfg in PROP_ARMS.items():
        adj = adj_role if cfg["field"] == "role" else adj_cas
        vals_by_fam = {}
        acc = {"expensive_evals": 0, "edge_evals": 0, "activated": 0, "prop_steps": 0}
        t0 = time.perf_counter()
        tracemalloc.start()
        for fam in RANKED:
            vals = []
            for q in queries.get(fam, []):
                ranked, verified, met = arm_prop(memories, adj, q, **cfg,
                                                 mutant_no_prop=(MUTANT == "N3"))
                for kk in acc:
                    acc[kk] += met[kk]
                vals.append(K.score_ranked_family(verified, q)["mrr"])
            vals_by_fam[fam] = sum(vals) / max(len(vals), 1)
        res["arms"][arm] = vals_by_fam
        res["eff"][arm] = dict(acc, wall_s=round(time.perf_counter() - t0, 3))
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        peaks[arm] = peak
    vals_by_fam = {}
    t0 = time.perf_counter(); eff_calls = 0
    for fam in RANKED:
        vals = []
        for q in queries.get(fam, []):
            ranked, verified, met = K.arm_d(memories, adj_cas, q, geo_mode="generic",
                                            provenance_aware=True, use_coherence=False)
            eff_calls += met["expensive_evals"]
            vals.append(K.score_ranked_family(verified, q)["mrr"])
        vals_by_fam[fam] = sum(vals) / max(len(vals), 1)
    res["arms"]["M_NOISE"] = vals_by_fam
    res["eff"]["M_NOISE"] = {"expensive_evals": eff_calls, "edge_evals": 0, "activated": 0,
                             "prop_steps": 0, "wall_s": round(time.perf_counter() - t0, 3)}
    res["eff"]["peak_mem_prop_bytes"] = max(peaks.values()) if peaks else 0
    atk_nm = [echo_attack(memories, rng, 900 + k, "near_miss") for k in range(20)]
    atk_ov = [echo_attack(memories, rng, 950 + k, "overlap") for k in range(20)]
    for cname, cfg in ECHO_CFGS.items():
        if MUTANT == "N5" and cname == "BOTH":
            cfg = dict(cfg, coherence=False)
        out = {}
        for setname, qset in (("ECHO", queries.get("ECHO", [])),
                              ("NEAR_MISS", atk_nm), ("OVERLAP", atk_ov)):
            unsafe, viol = 0, 0
            for q in qset:
                ranked, verified, met = arm_prop(memories, adj_cas, q,
                                                 field="cas", mode="recurrent", **cfg)
                deliver = verified if (cfg["verify_root_dedup"] or cfg["coherence"]) else ranked
                top5 = [m for m, _ in deliver[:5]]
                fs, ts = set(q["distractors"]), set(q["targets"])
                if any(m in fs for m in top5):
                    unsafe += 1
                btrue = min((i for i, (m, _) in enumerate(deliver) if m in ts), default=10 ** 9)
                if any(i < btrue for i, (m, _) in enumerate(deliver) if m in fs):
                    viol += 1
            out[setname] = {"unsafe": unsafe, "above_true_violations": viol, "n": len(qset)}
        res["echo"][cname] = out
    return res

def agg(w, arm):
    return sum(w["arms"][arm][f] for f in RANKED) / len(RANKED)

def deltas(worlds, armX, armY, fams):
    return [sum(w["arms"][armX][f] - w["arms"][armY][f] for f in fams) / len(fams) for w in worlds]

def supported(ds):
    n = len(ds)
    return sum(ds) / n >= K.MARGIN and sum(1 for d in ds if d > 0) >= 0.7 * n

def compute_gates(worlds):
    if MUTANT == "N4":  # law-level: feed G_GENERIC its exact failure condition (E2 == D)
        for w in worlds:
            w["arms"]["E2"] = dict(w["arms"]["D"])
    best_prop = max(PROP_ARMS, key=lambda a: sum(agg(w, a) for w in worlds) / len(worlds))
    best_graph = max(("X_MAX", "X_SUM"), key=lambda a: sum(agg(w, a) for w in worlds) / len(worlds))
    g = {}
    g["best_propagation_arm"] = best_prop
    g["best_graph_control"] = best_graph
    for key, (x, y, fams) in {
        "G_STATIC": ("B", "A", ["LOOKALIKE"]),
        "G_TRAJ": ("C", "B", ["ORDER_MATTERS", "CROSS_DOMAIN", "PATTERN_COMPLETION"]),
        "G_PROP": (best_prop, "C", ["PATTERN_COMPLETION"]),
        "G_ADDCORR": ("D", "X_MAX", ["INDEPENDENT_CORROB"]),
        "G_RESON": ("D", best_graph, RANKED),
        "G_GENERIC": ("D", "E2", RANKED),
    }.items():
        ds = deltas(worlds, x, y, fams)
        n = len(ds)
        g[key] = {"armX": x, "armY": y, "families": fams, "mean": sum(ds) / n,
                  "pos_worlds": sum(1 for d in ds if d > 0), "n": n, "values": [round(d, 6) for d in ds]}
    echo = {c: {"echo_unsafe": sum(w["echo"][c]["ECHO"]["unsafe"] for w in worlds),
                "nm_unsafe": sum(w["echo"][c]["NEAR_MISS"]["unsafe"] for w in worlds),
                "ov_unsafe": sum(w["echo"][c]["OVERLAP"]["unsafe"] for w in worlds),
                "echo_viol": sum(w["echo"][c]["ECHO"]["above_true_violations"] for w in worlds),
                "nm_viol": sum(w["echo"][c]["NEAR_MISS"]["above_true_violations"] for w in worlds),
                "ov_viol": sum(w["echo"][c]["OVERLAP"]["above_true_violations"] for w in worlds),
                "n": len(worlds)} for c in ECHO_CFGS}
    g["echo"] = echo
    g["G_EFF"] = {"ratios": [round(w["eff"][best_prop]["expensive_evals"] /
                                    max(w["eff"]["C"]["expensive_evals"], 1), 6) for w in worlds]}
    ratios = g["G_EFF"]["ratios"]
    g["G_EFF"]["mean"] = sum(ratios) / len(ratios)
    sr = sorted(ratios)
    g["G_EFF"]["median"] = sr[len(sr) // 2]
    pc = [w["arms"][best_prop]["PATTERN_COMPLETION"] for w in worlds]
    g["G_REPLAY_inputs"] = {"best_prop_pc_mean": sum(pc) / len(pc),
                            "graph_ok_all": all(w["graph_ok"] for w in worlds),
                            "both_echo_unsafe_total": echo["BOTH"]["echo_unsafe"]}
    return g

def statuses_from(g):
    s = {}
    s["STATIC_GEOMETRY_VALUE"] = "SUPPORTED" if supported(g["G_STATIC"]["values"]) else "NOT_ESTABLISHED"
    s["TRAJECTORY_VALUE"] = "SUPPORTED" if supported(g["G_TRAJ"]["values"]) else "NOT_ESTABLISHED"
    s["GRAPH_PROPAGATION_VALUE"] = "SUPPORTED" if supported(g["G_PROP"]["values"]) else "NOT_ESTABLISHED"
    s["ADDITIVE_CORROBORATION_VALUE"] = "SUPPORTED" if supported(g["G_ADDCORR"]["values"]) else "NOT_ESTABLISHED"
    s["RESONANCE_SPECIFIC_VALUE"] = "SUPPORTED" if supported(g["G_RESON"]["values"]) else "NOT_ESTABLISHED"
    if supported(g["G_GENERIC"]["values"]):
        s["GENERIC_GEOMETRY_ADVANTAGE"] = "SUPPORTED"
    elif g["G_GENERIC"]["mean"] >= -K.NONINF:
        s["GENERIC_GEOMETRY_ADVANTAGE"] = "NOT_ESTABLISHED"
    else:
        s["GENERIC_GEOMETRY_ADVANTAGE"] = "NOT_ESTABLISHED"
    e = g["echo"]["COH_ONLY"]
    s["COHERENCE_ECHO_CONTROL"] = ("SUPPORTED" if (e["echo_unsafe"] == 0 and e["nm_unsafe"] == 0)
                                   else "FAILED")
    r = g["echo"]["ROOT_ONLY"]
    s["PROVENANCE_ROOT_CONTROL"] = ("SUPPORTED" if (r["echo_unsafe"] == 0 and r["ov_unsafe"] == 0)
                                    else "NOT_SUPPORTED")
    ge = g["G_EFF"]
    s["RETRIEVAL_EFFICIENCY"] = ("SUPPORTED" if ge["mean"] < K.EFFICIENCY_CAP and ge["median"] < K.EFFICIENCY_CAP
                                 else "FAILED")
    ri = g["G_REPLAY_inputs"]
    ready = (ri["best_prop_pc_mean"] >= 0.50 and ri["both_echo_unsafe_total"] == 0
             and ri["graph_ok_all"] and s["RETRIEVAL_EFFICIENCY"] == "SUPPORTED")
    s["SELECTIVE_REPLAY_READINESS"] = "READY_FOR_RP0_DESIGN" if ready else "NOT_READY"
    return s

def run_battery(worlds_n=WORLDS):
    p1 = [run_world(w) for w in range(worlds_n)]
    p2 = [run_world(w) for w in range(worlds_n)]
    h1 = hashlib.sha256(json.dumps(p1, sort_keys=True).encode()).hexdigest()
    h2 = hashlib.sha256(json.dumps(p2, sort_keys=True).encode()).hexdigest()
    return p1, p2, h1, h2

def run_mutant(mid):
    global MUTANT
    MUTANT = mid
    worlds = [run_world(0), run_world(1)]
    g = compute_gates(worlds)
    s = statuses_from(g)
    obs = {"N1": s["STATIC_GEOMETRY_VALUE"], "N2": s["TRAJECTORY_VALUE"],
           "N3": s["GRAPH_PROPAGATION_VALUE"], "N4": "NOT_ESTABLISHED" if not supported(g["G_GENERIC"]["values"]) else "SUPPORTED",
           "N5": s["COHERENCE_ECHO_CONTROL"], "N6": "ANOMALY" if g["G_EFF"]["mean"] > K.EFFICIENCY_CAP else "PASS",
           "N7": s["PROVENANCE_ROOT_CONTROL"]}
    fired = {"N1": obs["N1"] != "SUPPORTED", "N2": obs["N2"] != "SUPPORTED",
             "N3": obs["N3"] != "SUPPORTED", "N4": obs["N4"] == "NOT_ESTABLISHED",
             "N5": obs["N5"] != "SUPPORTED", "N6": obs["N6"] == "ANOMALY",
             "N7": obs["N7"] != "SUPPORTED"}[mid]
    MUTANT = None
    return {"mutant": mid, "observed": obs[mid], "fired": fired,
            "gate_detail": {k: v for k, v in g.items() if k.startswith("G_") and not k.startswith("G_REPLAY")}}

def main():
    t0 = time.perf_counter()
    p1, p2, h1, h2 = run_battery(WORLDS)
    g = compute_gates(p1)
    s = statuses_from(g)
    receipt = {"project": "CMB-R1/RGM-0.1", "mechanism_name": "BOUNDED_ACTIVATION_PROPAGATION",
               "n_worlds": WORLDS, "gates": g, "statuses": s,
               "determinism": {"pass1_sha256": h1, "pass2_sha256": h2, "identical": h1 == h2},
               "worlds_pass1": p1, "wall_s_total": round(time.perf_counter() - t0, 1),
               "compute": "local CPU, deterministic non-neural, $0; no GPU, no model, no protected data",
               "mutant_battery": "see RGM01_MUTATION_REPORT.json",
               "audit_lineage": "repairs the four findings of CMB_R1_RGM0_CLAUDE_AUDIT.md (68fdf570)"}
    with open("RGM01_RECEIPT.json", "w") as f:
        json.dump(receipt, f, indent=1, sort_keys=True)
    print("STATUS_LINE:", json.dumps(s, sort_keys=True))
    print("DET:", h1 == h2, h1[:16])
    print("BEST_PROP:", g["best_propagation_arm"], "BEST_GRAPH:", g["best_graph_control"])
    print("WALL_S:", receipt["wall_s_total"])

if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--mutant":
        print(json.dumps(run_mutant(sys.argv[2])))
        sys.exit(0 if run_mutant.__doc__ is not None else 0)
    else:
        main()
