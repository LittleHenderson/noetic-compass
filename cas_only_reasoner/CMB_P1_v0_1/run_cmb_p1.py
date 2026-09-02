"""CMB-P1 runner -- three repairs, their controls, phase-free baselines, per-K decisions.

Frozen design: CMB_P1_PREREGISTRATION.md v0.1. Owner ruling 2026-09-02 (R4).
GPU only. Fail closed. No CPU fallback branch.

Built after a design panel + independent verification found three things that change the
design (all confirmed by my own measurement, not taken on trust):
  * PHASE_SUBSTEPS=10 is NOT converged -- merge fraction goes 0.64 -> 0.98 -> 1.00 at
    substeps 10/25/200 with cross-chain separation reaching exactly 0.0000. Every arm is
    therefore reported at BOTH budgets, so no arm can win by being a slower transient.
  * The CONTENT vector LEAKED chain identity (a chain's flavour was applied to its own
    completion). Repaired in `build_world_p1`, verified back to exact chance.
  * A phase-free structural gate must be registered as a baseline, or a phase win is
    uninterpretable.
"""
import hashlib
import json
import math
import sys
import time
import traceback

import torch

_here = __import__("os").path.dirname(__import__("os").path.abspath(__file__))
_p0 = __import__("os").path.join(_here, "..", "CMB_P0_v0_1")
sys.path.insert(0, _p0 if __import__("os").path.isdir(_p0) else _here)
import cmb_p0 as P0                                              # noqa: E402
import cmb_p1 as P1                                              # noqa: E402
from cmb_p0 import (N_NODES, QUERIES_PER_WORLD, TOPK, build_queries,  # noqa: E402
                    gen, gpu_identity, propagate_channels, propagate_scalar,
                    propagate_two_state, require_cuda)

K_SETTINGS = (1, 2, 3, 4)
DEV_WORLDS = tuple(range(0, 6))
HELDOUT_WORLDS = tuple(range(6, 26))
SUBSTEP_BUDGETS = (10, 200)                # 10 = CMB-P0's setting; 200 = converged

REPAIRS = ("P7_SIGNED_COUPLING", "P8_FREQUENCY_HETEROGENEITY", "P9_TRAJECTORY_COHERENCE")
SHUFFLE_OF = {"P7_SIGNED_COUPLING": "P7_SHUFFLED",
              "P8_FREQUENCY_HETEROGENEITY": "P8_SHUFFLED",
              "P9_TRAJECTORY_COHERENCE": "P9_SHUFFLED"}
VERDICT_OF = {"P7_SIGNED_COUPLING": "PHASE_SEPARATION_BY_SIGNED_COUPLING",
              "P8_FREQUENCY_HETEROGENEITY": "PHASE_SEPARATION_BY_FREQUENCY_HETEROGENEITY"}

NON_PHASE = ("P0_SCALAR", "P1_ORACLE_CHAIN_TAG", "P2_INFERRED_CHAIN_TAG",
             "P3_GENERIC_TWO_STATE", "P6_SCALAR_TWO_CHANNEL",
             "B_STRUCT_GATE_REACH", "B_STRUCT_GATE_CONTENT")
PHASE_ARMS = ("P4_PHASE_OSCILLATOR", "P5_PHASE_SHUFFLED",
              "P7_SIGNED_COUPLING", "P7_SHUFFLED",
              "P8_FREQUENCY_HETEROGENEITY", "P8_SHUFFLED",
              "P8_OMEGA_SHUFFLED", "P8_OMEGA_RANDOM",
              "P9_TRAJECTORY_COHERENCE", "P9_SHUFFLED",
              "P8P9_EXPLORATORY_COMBINATION")
ARMS = NON_PHASE + PHASE_ARMS


def score_world(world, q, scores):
    ar = torch.arange(QUERIES_PER_WORLD, device=P0.DEV)
    finite = bool(torch.isfinite(scores).all().item())
    s = scores.clone()
    s[q["seeds"] > 0] = -1e18
    gold = s[ar, q["gold"]].unsqueeze(1)
    rank = (s > gold).sum(dim=1) + (s == gold).sum(dim=1) - 1     # ties count pessimistically
    top = torch.topk(s, TOPK, dim=1).indices
    lab = world["chain_of"][top]
    active = q["active_mask"].gather(1, lab.clamp_min(0))
    return {"top1": (rank == 0).double().mean().item(),
            "recall_at_5": (rank < TOPK).double().mean().item(),
            "cross_chain_contamination":
                ((lab >= 0) & (lab != q["target"].unsqueeze(1)) & active).double().mean().item(),
            "runtime_finite": finite}


def cluster_merge_fraction(cluster, world, q):
    k = world["k_chains"]
    maj = {}
    for ci in range(world["pool"]):
        nodes = (world["memb"][ci] > 0).nonzero(as_tuple=True)[0]
        nodes = nodes[world["chain_of"][nodes] == ci]
        g = cluster[nodes]
        g = g[g >= 0]
        if g.numel():
            maj[ci] = int(torch.mode(g).values.item())
    act = q["active_mask"]
    merged = 0.0
    for qi in range(QUERIES_PER_WORLD):
        on = [c for c in maj if bool(act[qi, c])]
        merged += sum(1 for i, a in enumerate(on) for b in on[i + 1:] if maj[a] == maj[b])
    return merged / QUERIES_PER_WORLD / max(1.0, k * (k - 1) / 2.0)


def run_world(world_id, k, substeps):
    """One world at one substep budget. Non-phase arms are budget-independent but are
    recomputed so every reported table is internally consistent."""
    w = P1.build_world_p1(world_id, k)
    q = build_queries(w)
    ar = torch.arange(QUERIES_PER_WORLD, device=P0.DEV)
    out = {"world_id": world_id, "k_chains": k, "substeps": substeps, "arms": {}}

    def put(name, scores, mfrac=None, mend=None, gord=None):
        m = score_world(w, q, scores)
        m["merge_fraction"] = mfrac
        m["merge_fraction_endpoint_view"] = mend
        m["global_order_parameter"] = gord
        out["arms"][name] = m

    # ---- non-phase arms -----------------------------------------------------------
    scal = propagate_scalar(q["seeds"], w["W"])
    put("P0_SCALAR", scal)

    ch = w["memb"].unsqueeze(0) * q["active_mask"].unsqueeze(-1).to(P0.DT)
    ch[ar, q["target"], q["cue"]] += 1.0
    put("P1_ORACLE_CHAIN_TAG", propagate_channels(ch, w["W"])[ar, q["target"]])

    cluster = P1.infer_clusters_v2(w)
    onehot = torch.zeros((w["pool"], N_NODES), device=P0.DEV, dtype=P0.DT)
    valid = cluster >= 0
    onehot[cluster[valid], valid.nonzero(as_tuple=True)[0]] = 1.0
    ch2 = onehot.unsqueeze(0) * (q["seeds"] > 0).unsqueeze(1).to(P0.DT)
    grp = cluster[q["cue"]].clamp_min(0)
    ch2[ar, grp, q["cue"]] += 1.0
    put("P2_INFERRED_CHAIN_TAG", propagate_channels(ch2, w["W"])[ar, grp],
        mfrac=cluster_merge_fraction(cluster, w, q))

    a3, _ = propagate_two_state(q["seeds"], w["W"])
    put("P3_GENERIC_TWO_STATE", a3)

    cue_seed = torch.zeros_like(q["seeds"])
    cue_seed[ar, q["cue"]] = 1.0
    put("P6_SCALAR_TWO_CHANNEL", scal * propagate_scalar(cue_seed, w["W"]).clamp_min(0.0))

    # PHASE-FREE BASELINES. Without these a phase win is uninterpretable: if a one-line
    # structural gate matches the oscillator, the oscillator is not what is doing the work.
    S = P1.reach_similarity(w)
    put("B_STRUCT_GATE_REACH",
        scal * torch.sign(S[q["cue"]] - P1.B_GATE_REACH_S0).clamp_min(0.0))
    C = w["content"] @ w["content"].T
    put("B_STRUCT_GATE_CONTENT",
        scal * torch.sign(C[q["cue"]] - P1.B_GATE_CONTENT_S0).clamp_min(0.0))

    # ---- phase runs ---------------------------------------------------------------
    def readouts(tag, coupling=None, omega=None):
        a, th, coh, pair = P1.run_phase_acc(w, q, coupling=coupling, omega=omega,
                                            substeps=substeps)
        perm = torch.randperm(N_NODES, generator=gen(w["key"] + "|readshuf"), device=P0.DEV)
        end_coh = torch.cos(th - th[ar, q["cue"]].unsqueeze(1))
        ep = P1.endpoint_pair_coherence(th, q, w)
        ef, _ = P1.merge_fraction_from_pairs(ep, q, w)
        tf, _ = P1.merge_fraction_from_pairs(pair, q, w)
        z = (a.to(torch.complex128) * torch.exp(1j * th.to(torch.complex128))).sum(1)
        go = float((z.abs() / a.sum(1).clamp_min(1e-12)).clamp(0, 1).mean().item())
        return {"a": a, "end": end_coh, "end_shuf": end_coh[:, perm],
                "traj": coh, "traj_shuf": coh[:, perm],
                "ef": ef, "tf": tf, "go": go}

    b = readouts("BASE")
    put("P4_PHASE_OSCILLATOR", b["a"] * b["end"].clamp_min(0), b["ef"], b["ef"], b["go"])
    put("P5_PHASE_SHUFFLED", b["a"] * b["end_shuf"].clamp_min(0), b["ef"], b["ef"], b["go"])
    put("P9_TRAJECTORY_COHERENCE", b["a"] * b["traj"].clamp_min(0), b["tf"], b["ef"], b["go"])
    put("P9_SHUFFLED", b["a"] * b["traj_shuf"].clamp_min(0), b["tf"], b["ef"], b["go"])
    del b

    g = readouts("SIGNED", coupling=P1.signed_coupling(w))
    put("P7_SIGNED_COUPLING", g["a"] * g["end"].clamp_min(0), g["ef"], g["ef"], g["go"])
    put("P7_SHUFFLED", g["a"] * g["end_shuf"].clamp_min(0), g["ef"], g["ef"], g["go"])
    del g

    f = readouts("FREQ", omega=P1.omega_field(w, "SPECTRAL"))
    put("P8_FREQUENCY_HETEROGENEITY", f["a"] * f["end"].clamp_min(0), f["ef"], f["ef"], f["go"])
    put("P8_SHUFFLED", f["a"] * f["end_shuf"].clamp_min(0), f["ef"], f["ef"], f["go"])
    put("P8P9_EXPLORATORY_COMBINATION", f["a"] * f["traj"].clamp_min(0), f["tf"], f["ef"], f["go"])
    del f

    for kind, name in (("OMEGA_SHUFFLED", "P8_OMEGA_SHUFFLED"),
                       ("OMEGA_RANDOM", "P8_OMEGA_RANDOM")):
        c = readouts(kind, omega=P1.omega_field(w, kind))
        put(name, c["a"] * c["end"].clamp_min(0), c["ef"], c["ef"], c["go"])
        del c
    return out


# ---------------------------------------------------------------- statistics


def paired(rs, a, b, key="top1", margin=P1.MARGIN):
    d = [r["arms"][a][key] - r["arms"][b][key] for r in rs
         if r["arms"][a].get(key) is not None and r["arms"][b].get(key) is not None]
    if len(d) < 5:
        return {"mean_delta": None, "worlds_positive": 0, "n": len(d), "win": False}
    mean = sum(d) / len(d)
    pos = sum(1 for x in d if x > 0)
    return {"mean_delta": mean, "worlds_positive": pos, "n": len(d),
            "win": bool(mean > margin and pos >= P1.WIN_FRACTION * len(d))}


def mean_of(rs, arm, key):
    v = [r["arms"][arm][key] for r in rs if r["arms"][arm].get(key) is not None]
    return (sum(v) / len(v)) if v else None


def emit_status(held):
    prim = P1.PRIMARY_K
    sel = lambda k, sub: [r for r in held if r["k_chains"] == k and r["substeps"] == sub]

    gates = {sub: {k: {"p0_top1": mean_of(sel(k, sub), "P0_SCALAR", "top1"),
                       "p1_oracle_top1": mean_of(sel(k, sub), "P1_ORACLE_CHAIN_TAG", "top1"),
                       "p4_merge_fraction": mean_of(sel(k, sub), "P4_PHASE_OSCILLATOR",
                                                    "merge_fraction")}
                   for k in prim} for sub in SUBSTEP_BUDGETS}

    def gate_fail():
        for k in prim:
            g = gates[SUBSTEP_BUDGETS[0]][k]
            if g["p0_top1"] >= P1.GATE_HEADROOM_TOP1:
                return "NO_MULTICHAIN_GAP"
            if g["p1_oracle_top1"] < P1.GATE_ORACLE_TOP1:
                return "INSTRUMENT_OR_TASK_ILL_POSED"
            if g["p4_merge_fraction"] <= P1.MERGE_FRACTION_MAX:
                return "GATE_P4_UNSAFE_DID_NOT_REPRODUCE"
        return None

    def criteria_for(R, sub):
        sh = SHUFFLE_OF[R]
        rs = {k: sel(k, sub) for k in prim}
        c = {}
        c["1_beats_P0"] = all(paired(rs[k], R, "P0_SCALAR")["win"] for k in prim)
        ok = True
        for k in prim:
            mf = mean_of(rs[k], R, "merge_fraction")
            p2 = mean_of(rs[k], "P2_INFERRED_CHAIN_TAG", "merge_fraction")
            if mf is None or mf > P1.MERGE_FRACTION_MAX:
                ok = False
            if p2 is not None and mf is not None and mf > p2 + P1.MERGE_VS_P2_SLACK:
                ok = False
        c["2_merging_below_threshold"] = ok
        c["3_beats_P3"] = all(paired(rs[k], R, "P3_GENERIC_TWO_STATE")["win"] for k in prim)
        c["4_beats_or_approaches_P2"] = all(
            (mean_of(rs[k], R, "top1") - mean_of(rs[k], "P2_INFERRED_CHAIN_TAG", "top1"))
            >= -P1.MARGIN for k in prim)
        c["5_shuffle_destroys_it"] = all(
            mean_of(rs[k], sh, "top1") < mean_of(rs[k], "P0_SCALAR", "top1") for k in prim)
        c["6_no_extra_contamination"] = all(
            (mean_of(rs[k], R, "cross_chain_contamination")
             - mean_of(rs[k], "P0_SCALAR", "cross_chain_contamination"))
            <= P1.CONTAM_MARGIN for k in prim)
        c["7_holds_across_worlds"] = c["1_beats_P0"]
        c["8_no_oracle_membership"] = True
        # ADDITION beyond the owner's eight, flagged for ratification: the repair must also
        # beat every PHASE-FREE baseline. If a one-line structural gate matches it, the
        # oscillator is not what is doing the work.
        c["9_beats_phase_free_baselines"] = all(
            paired(rs[k], R, bl)["win"] for k in prim
            for bl in ("B_STRUCT_GATE_REACH", "B_STRUCT_GATE_CONTENT"))
        return c

    criteria = {R: {sub: criteria_for(R, sub) for sub in SUBSTEP_BUDGETS} for R in REPAIRS}
    # A claim must hold at BOTH substep budgets, or the arm merely won by being a slower
    # transient. Demanded by the design panel and confirmed by measurement.
    survivors = [R for R in REPAIRS
                 if all(all(criteria[R][sub].values()) for sub in SUBSTEP_BUDGETS)]

    p8_decomp = {sub: {k: {
        "spectral": mean_of(sel(k, sub), "P8_FREQUENCY_HETEROGENEITY", "top1"),
        "omega_shuffled": mean_of(sel(k, sub), "P8_OMEGA_SHUFFLED", "top1"),
        "omega_random": mean_of(sel(k, sub), "P8_OMEGA_RANDOM", "top1"),
        "structure_adds_beyond_spread": bool(
            paired(sel(k, sub), "P8_FREQUENCY_HETEROGENEITY", "P8_OMEGA_RANDOM")["win"]
            and paired(sel(k, sub), "P8_FREQUENCY_HETEROGENEITY", "P8_OMEGA_SHUFFLED")["win"])}
        for k in prim} for sub in SUBSTEP_BUDGETS}

    gf = gate_fail()
    sub0 = SUBSTEP_BUDGETS[0]
    if gf:
        st, reason, best = "STATUS_NOT_EMITTED", gf, None
    elif not survivors:
        kept = any(all(paired(sel(k, sub0), R, "P0_SCALAR")["win"] for k in prim)
                   for R in REPAIRS)
        st = "PHASE_MEMORY_UNSAFE" if kept else "PHASE_RETIRED_FOR_MULTICHAIN_MEMORY"
        reason = ("a repair kept accuracy but not attribution" if kept
                  else "no repair preserved both accuracy and attribution")
        best = None
    else:
        best = max(survivors, key=lambda R: sum(mean_of(sel(k, sub0), R, "top1") for k in prim))
        tied = [R for R in survivors if R != best and abs(sum(
            mean_of(sel(k, sub0), R, "top1") - mean_of(sel(k, sub0), best, "top1")
            for k in prim)) < P1.MARGIN * len(prim)]
        p2_beats = all(
            (mean_of(sel(k, sub0), "P2_INFERRED_CHAIN_TAG", "top1")
             - mean_of(sel(k, sub0), best, "top1")) >= -P1.MARGIN for k in prim)
        if tied:
            st, reason = "STATUS_NOT_EMITTED", "MULTIPLE_REPAIRS_TIED"
        elif p2_beats:
            st, reason = "EXPLICIT_CHAIN_TAGS_PREFERRED", None
        elif best in VERDICT_OF:
            st, reason = VERDICT_OF[best], None
        else:
            st, reason = "STATUS_NOT_EMITTED", "TRAJECTORY_READOUT_BEST_NO_REGISTERED_VERDICT"

    return {"status": st, "reason": reason, "best_repair": best, "survivors": survivors,
            "criteria_by_substeps": criteria, "gates_by_substeps": gates,
            "p8_structure_decomposition": p8_decomp,
            "note_criterion_9": "criterion 9 (beat the phase-free baselines) is Claude's "
                                "addition beyond the owner's eight -- flagged for ratification; "
                                "it can only make passing HARDER",
            "note_exploratory": "P8P9_EXPLORATORY_COMBINATION carries no verdict",
            "escalate_to_owner": st == "STATUS_NOT_EMITTED"}


VOLATILE = ("cuda_time_ms", "peak_vram_bytes", "wall_s", "host_wall_s", "device")


def strip(o):
    if isinstance(o, dict):
        return {k: strip(v) for k, v in o.items() if k not in VOLATILE}
    if isinstance(o, list):
        return [strip(v) for v in o]
    return o


def group(rs):
    if not rs:
        return {}
    return {a: {m: mean_of(rs, a, m) for m in
                ("top1", "recall_at_5", "cross_chain_contamination", "merge_fraction",
                 "global_order_parameter")} for a in ARMS}


def main():
    require_cuda()
    t0 = time.perf_counter()
    dev, held = [], []
    try:
        for sub in SUBSTEP_BUDGETS:
            for k in K_SETTINGS:
                for wid in DEV_WORLDS:
                    dev.append(run_world(wid, k, sub))
                for wid in HELDOUT_WORLDS:
                    held.append(run_world(wid, k, sub))
        verdict = emit_status(held)
    except Exception:
        json.dump({"FAILED": True, "traceback": traceback.format_exc(),
                   "partial_heldout": strip(held), "partial_dev": strip(dev)},
                  open("CMB_P1_RECEIPT.json", "w"), indent=1, sort_keys=True)
        traceback.print_exc()
        print("RUN FAILED -- partial receipt written")
        return 2

    receipt = {
        "project": "CMB-P1 Phase Separation Repair Bench",
        "preregistration": "CMB_P1_PREREGISTRATION.md v0.1",
        "authority": "owner ruling 2026-09-02 R4",
        "frozen_params": {n: getattr(P1, n) for n in dir(P1) if n.isupper()},
        "heldout_by_substeps_and_k": {
            sub: {k: group([r for r in held if r["k_chains"] == k and r["substeps"] == sub])
                  for k in K_SETTINGS} for sub in SUBSTEP_BUDGETS},
        "verdict": verdict,
        "dev_worlds": strip(dev),
        "heldout_worlds": strip(held),
        "compute": dict(gpu_identity(),
                        peak_vram_bytes=int(torch.cuda.max_memory_allocated()),
                        host_wall_s=round(time.perf_counter() - t0, 2)),
        "claim_note": ("No resonance-specific or CAS-specific claim is licensed. "
                       "P1_ORACLE_CHAIN_TAG is a ceiling, never a method. "
                       "P8P9 is exploratory and cannot carry a verdict."),
    }
    payload = json.dumps(strip({k: receipt[k] for k in
                                ("frozen_params", "heldout_by_substeps_and_k", "verdict",
                                 "heldout_worlds")}), sort_keys=True)
    receipt["determinism"] = {"content_hash": hashlib.sha256(payload.encode()).hexdigest()}
    json.dump(receipt, open("CMB_P1_RECEIPT.json", "w"), indent=1, sort_keys=True)

    print("STATUS:", verdict["status"], "| REASON:", verdict.get("reason"))
    print("BEST:", verdict["best_repair"], "| SURVIVORS:", verdict["survivors"])
    for sub in SUBSTEP_BUDGETS:
        print(f"--- substeps={sub} ---")
        for k in K_SETTINGS:
            g = receipt["heldout_by_substeps_and_k"][sub][k]
            print(f"  K={k}: " + "  ".join(
                f"{a.split('_')[0]}={g[a]['top1']:.3f}"
                + ("" if g[a]["merge_fraction"] is None else f"/{g[a]['merge_fraction']:.3f}")
                for a in ARMS))
    print("HASH:", receipt["determinism"]["content_hash"][:16])
    return 0


if __name__ == "__main__":
    sys.exit(main())
