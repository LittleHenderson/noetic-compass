"""RGM-0 orchestrator: runs all arms x all families, evaluates the frozen kill laws, and
emits a deterministic status. Status comes ONLY from the program below, never from prose."""
import argparse, copy, hashlib, json, sys
import cmb_r1_core as core

RANKED = core.RANKED_FAMILIES

def run_pipeline(mutant=None):
    memories, topics, marginals = core.build_corpus()
    queries = core.build_queries(memories, topics)
    adj = core.build_adjacency(memories)
    core.assign_generic_geometry(memories, marginals)

    per_query = {}   # (arm, family) -> [per-query metric dicts in family order]
    eff = {}         # (arm,) -> expensive-evaluation totals
    echo = {}        # arm -> {"unsafe": bool, "g_unsafe": bool}
    novelty = {}     # arm -> detection rate
    guard = {"firings": 0, "resonant_empty": False, "activation_collapsed": False}

    memF = copy.deepcopy(memories) if mutant == "M5" else None
    if mutant == "M5":
        pass  # corruption identity: F runs on the pristine corpus
    else:
        memF = copy.deepcopy(memories)
        core.corrupt_corpus(memF)

    def pool_scores(arm, family, scored_list):
        per_query.setdefault((arm, family), []).extend(scored_list)

    # A
    for fam in RANKED:
        out = []
        for q in queries[fam]:
            out.append(core.score_ranked_family(core.arm_a(memories, q), q))
        pool_scores("A", fam, out)
    # B (M1: static geometry carries no information -> B degenerates to A)
    for fam in RANKED:
        out = []
        for q in queries[fam]:
            r = core.arm_a(memories, q) if mutant == "M1" else core.arm_b(memories, q)
            out.append(core.score_ranked_family(r, q))
        pool_scores("B", fam, out)
    # C (M2: order-insensitive trajectory similarity)
    for fam in RANKED:
        out = []
        for q in queries[fam]:
            r = core.arm_c(memories, q, mutant_order_insensitive=(mutant == "M2"))
            out.append(core.score_ranked_family(r, q))
        pool_scores("C", fam, out)
        eff["C"] = eff.get("C", 0) + len(memories)
    # D / E / G via arm_d
    def run_d(arm, mems, geo, aware, coh, no_prop=False, novelty_arm=False):
        for fam in RANKED + ["ECHO", "NOVELTY"]:
            out, exp, out_raw = [], 0, []
            for q in queries.get(fam, []):
                ranked, verified, met = core.arm_d(mems, adj, q, geo_mode=geo,
                                                   provenance_aware=aware,
                                                   use_coherence=coh,
                                                   mutant_no_propagation=no_prop)
                exp += met["expensive_evals"]
                if fam == "NOVELTY":
                    lacuna = (len(verified) == 0) or (met["top_seed_cheap"] < core.NOVELTY_TAU)
                    out.append({"detected": 1 if lacuna else 0})
                    continue
                if fam == "ECHO":
                    top5 = [m for m, _ in (verified if aware else ranked)][:5]
                    unsafe = q["false_id"] in top5
                    out.append({"unsafe": unsafe})
                    continue
                # PRIMARY quality metric = the arm's actual deliverable: the verifier's
                # verified ranking. The raw pre-verifier ranking is kept report-only.
                out.append(core.score_ranked_family(verified if aware else ranked, q))
                out_raw.append(core.score_ranked_family(ranked, q))
            if fam in RANKED:
                pool_scores(arm, fam, out)
                pool_scores(arm + "_RAW", fam, out_raw)
                eff[arm] = eff.get(arm, 0) + exp
            if fam == "ECHO":
                echo[arm] = {"unsafe": any(o["unsafe"] for o in out)}
            if fam == "NOVELTY":
                novelty[arm] = sum(o["detected"] for o in out) / max(len(out), 1)
    run_d("D", memories, "cas", True, True, no_prop=(mutant == "M3"))
    run_d("E", memories, "generic", True, False)
    run_d("G", memories, "cas", False, False)
    if mutant == "M6":  # verifier protections disabled in D itself
        run_d("D6", memories, "cas", False, False)
        echo["D"] = echo["D6"]
    run_d("F", memF, "cas", True, True)
    # H
    for fam in RANKED:
        out = []
        for q in queries[fam]:
            out.append(core.score_ranked_family(core.arm_h(memories, q, guard), q))
        pool_scores("H", fam, out)

    def agg(arm, fams):
        vals = []
        for fam in fams:
            vals.extend(o["mrr"] for o in per_query.get((arm, fam), []))
        return sum(vals) / len(vals) if vals else 0.0

    def fam_delta(arm_x, arm_y, fam):
        xs = per_query.get((arm_x, fam), [])
        ys = per_query.get((arm_y, fam), [])
        n = min(len(xs), len(ys))
        return [xs[i]["mrr"] - ys[i]["mrr"] for i in range(n)]

    def paired(arm_x, arm_y, fams):
        deltas = []
        for fam in fams:
            deltas.extend(fam_delta(arm_x, arm_y, fam))
        mean = sum(deltas) / len(deltas) if deltas else 0.0
        p = core.paired_permutation(deltas, core._rng(core.SEED + 4242)) if deltas else 1.0
        return mean, p, deltas

    results = {}
    for arm in ["A", "B", "C", "D", "E", "F", "G", "H"]:
        results[arm] = {"agg_mrr": agg(arm, RANKED),
                        "per_family": {f: agg(arm, [f]) for f in RANKED}}
    for arm in ["D", "E", "F", "G"]:
        results[arm]["agg_mrr_raw_report_only"] = agg(arm + "_RAW", RANKED)
    if mutant == "M4":
        # LAW-LEVEL MUTANT: feed KL4 its exact failure condition (generic pipeline achieves
        # results identical to the CAS pipeline) and require the gate to fire. Geometry-level
        # identity does NOT imply pipeline identity because arm E's registered verifier
        # asymmetry (spec A4) is itself CAS-specific — so the gate is tested at the law.
        for f in RANKED:
            per_query[("E", f)] = list(per_query.get(("D", f), []))
        results["E"]["agg_mrr"] = results["D"]["agg_mrr"]
        results["E"]["per_family"] = dict(results["D"]["per_family"])
    laws = {}
    m_BA, p_BA, d_BA = paired("B", "A", RANKED)
    laws["KL1_B_vs_A"] = {"delta": m_BA, "p": p_BA, "pass": m_BA >= core.MARGIN}
    m_CB, p_CB, d_CB = paired("C", "B", core.TRAJ_SENSITIVE)
    laws["KL2_C_vs_B_traj"] = {"delta": m_CB, "p": p_CB, "pass": m_CB >= core.MARGIN}
    m_DC, p_DC, d_DC = paired("D", "C", RANKED)
    eff_ratio = eff.get("D", 0) / max(eff.get("C", 1), 1)
    kl3_pass = (m_DC >= core.MARGIN) or (m_DC >= -core.NONINF and eff_ratio < core.EFFICIENCY_CAP)
    laws["KL3_D_vs_C"] = {"delta": m_DC, "p": p_DC, "eff_ratio": eff_ratio, "pass": kl3_pass}
    m_DE, p_DE, d_DE = paired("D", "E", RANKED)
    laws["KL4_generic"] = {"delta": m_DE, "fires": m_DE <= core.NONINF}
    m_DF, p_DF, d_DF = paired("D", "F", RANKED)
    laws["KL5_corruption"] = {"delta": m_DF, "p": p_DF, "pass": m_DF >= core.MARGIN}
    d_safe = not echo.get("D", {}).get("unsafe", True)
    g_unsafe = echo.get("G", {}).get("unsafe", False)
    laws["KL6_echo"] = {"D_safe": d_safe, "G_unsafe": g_unsafe,
                        "provenance_control_required": bool(g_unsafe and d_safe)}
    # KL7 residual: each positive delta must survive dropping its largest family at half margin
    def residual(x_arm, y_arm, fams):
        per = {f: (sum(fam_delta(x_arm, y_arm, f)) / max(len(fam_delta(x_arm, y_arm, f)), 1))
               for f in fams}
        if not per:
            return 0.0, None
        biggest = max(per, key=lambda f: per[f])
        rest = [f for f in fams if f != biggest]
        vals = []
        for f in rest:
            vals.extend(fam_delta(x_arm, y_arm, f))
        return (sum(vals) / len(vals) if vals else 0.0), biggest
    r1, big1 = residual("B", "A", RANKED)
    r2, big2 = residual("C", "B", core.TRAJ_SENSITIVE)
    r5, big5 = residual("D", "F", RANKED)
    laws["KL7_residual"] = {
        "KL1_residual": r1, "KL1_biggest": big1,
        "KL2_residual": r2, "KL2_biggest": big2,
        "KL5_residual": r5, "KL5_biggest": big5,
        "pass": (r1 >= core.MARGIN / 2) and (r2 >= core.MARGIN / 2) and (r5 >= core.MARGIN / 2)}
    novelty_D = novelty.get("D", 0.0)

    fired = None
    if not laws["KL1_B_vs_A"]["pass"]:
        fired = "STATIC_CAS_GEOMETRY_REDUNDANT"
    elif not laws["KL2_C_vs_B_traj"]["pass"]:
        fired = "CAS_TRAJECTORY_VALUE_NOT_DEMONSTRATED"
    elif not laws["KL3_D_vs_C"]["pass"]:
        fired = "RESONANCE_LAYER_ORNAMENTAL"
    elif laws["KL4_generic"]["fires"]:
        fired = "GENERIC_GEOMETRY_SUFFICIENT"
    elif not laws["KL5_corruption"]["pass"]:
        fired = "CAS_GEOMETRY_NOT_LOAD_BEARING"
    elif not d_safe:
        fired = "ECHO_CONTROLS_FAILED"
    elif not laws["KL7_residual"]["pass"]:
        fired = "ONE_FAMILY_RESULT"
    if fired:
        status = "RGM0_FAILED:" + fired
    else:
        positive = (laws["KL1_B_vs_A"]["pass"] and laws["KL2_C_vs_B_traj"]["pass"] and
                    laws["KL3_D_vs_C"]["pass"] and not laws["KL4_generic"]["fires"] and
                    laws["KL5_corruption"]["pass"] and d_safe and
                    laws["KL7_residual"]["pass"] and novelty_D >= 0.90)
        status = "RGM0_RESONANT_MEMORY_SIGNAL" if positive else "RGM0_READY_FOR_NEURAL_REVIEW"
    if mutant == "M6" and echo.get("D", {}).get("unsafe"):
        status = "RGM0_FAILED:ECHO_CONTROLS_FAILED"
    return {"status": status, "laws": laws, "results": results, "echo": echo,
            "novelty": novelty, "efficiency": eff, "guard_firings": guard["firings"],
            "n_memories_final": len(memories)}

def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mutant", default=None)
    args = ap.parse_args()
    runs = [run_pipeline(args.mutant) for _ in range(3)]
    hashes = [hashlib.sha256(canonical({k: v for k, v in r.items()}).encode()).hexdigest()
              for r in runs]
    determinism = len(set(hashes)) == 1
    out = runs[0]
    out["determinism"] = {"triple_run_hashes": hashes, "identical": determinism}
    if not determinism:
        out["status"] = "RGM0_FAILED:DETERMINISM_BROKEN"
    blob = canonical(out)
    print(blob)
    return 0

if __name__ == "__main__":
    sys.exit(main())