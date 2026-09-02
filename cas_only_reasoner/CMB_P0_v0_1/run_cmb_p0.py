"""CMB-P0 runner v0.2 -- seven arms, per-K decisions, math audit, gates, deterministic status.

Frozen design: CMB_P0_PREREGISTRATION.md v0.1 + A1 + A2.
GPU only. Fail closed. No CPU fallback branch.

v0.1 of this runner was stopped pre-launch by adversarial review. Repaired here:
  * per-K decisions (v0.1 pooled K=2,3,4 into one bag of 60 that tolerated 18 negative
    worlds -- the aggregate-hides-a-reversal defect this project has raised twice against
    a sibling lane, reproduced one level down);
  * status branches now test what section 6 actually says, including the `P2 >= P4` clauses
    that were absent from the code;
  * the PHASE_DEGENERATE_TO_SCALAR guard BLOCKS the five-outcome law instead of annotating
    it (v0.1 wrote the guard into the receipt and then ignored it);
  * safety thresholds carry their own units (merges are counts, not accuracy fractions);
  * ties are counted pessimistically, not in the gold answer's favour;
  * P3's two-state parameters are chosen to make the CAPACITY CONTROL as strong as
    possible (at the drafted b=0.60 it scored top1 0.000 -- broken, not inert);
  * P6_SCALAR_TWO_CHANNEL is the readout-matched non-angular comparator, and is what
    separates "phase" from "any second cue-seeded channel";
  * a partial receipt is written if the run dies mid-way.
"""
import hashlib
import json
import math
import sys
import time
import traceback

import torch

import cmb_p0 as P
from cmb_p0 import (ARMS, CAPACITY_TOP1, CONTAM_MARGIN, DELTA, DEPTH, DEV_WORLDS,
                    D_CONTENT, EPS_REC, B_COUPLE, GAMMA, GATE_HEADROOM_TOP1,
                    GATE_ORACLE_TOP1, HELDOUT_WORLDS, K_SETTINGS, L_CHAIN, MARGIN,
                    MERGE_MARGIN, N_NODES, QUERIES_PER_WORLD, TOPK, TOPK_KEEP,
                    WIN_FRACTION, assert_cuda, build_queries, build_world, gen,
                    gpu_identity, infer_clusters, phase_assignment, propagate_channels,
                    propagate_phase, propagate_scalar, propagate_two_state, require_cuda)


# ---------------------------------------------------------------- the seven arms


def arm_scores(name, world, q, cache):
    """Return (scores over N nodes per query, assignment stats or None). All on CUDA."""
    W, A, deg = world["W"], world["A"], world["deg"]
    pool, Q = world["pool"], QUERIES_PER_WORLD
    ar = torch.arange(Q, device=P.DEV)
    seeds = q["seeds"]

    if name == "P0_SCALAR":
        return assert_cuda(cache["scalar"], "P0.scores"), None

    if name == "P1_ORACLE_CHAIN_TAG":
        # ORACLE: handed true chain membership. An upper bound, never a method.
        ch = world["memb"].unsqueeze(0) * q["active_mask"].unsqueeze(-1).to(P.DT)
        ch[ar, q["target"], q["cue"]] += 1.0
        out = propagate_channels(ch, W)
        return assert_cuda(out[ar, q["target"]], "P1.scores"), (1.0, 0.0)

    if name == "P2_INFERRED_CHAIN_TAG":
        cluster = cache["clusters"]
        onehot = torch.zeros((pool, N_NODES), device=P.DEV, dtype=P.DT)
        valid = cluster >= 0
        onehot[cluster[valid], valid.nonzero(as_tuple=True)[0]] = 1.0
        ch = onehot.unsqueeze(0) * (seeds > 0).unsqueeze(1).to(P.DT)
        grp = cluster[q["cue"]].clamp_min(0)
        ch[ar, grp, q["cue"]] += 1.0
        out = propagate_channels(ch, W)
        return assert_cuda(out[ar, grp], "P2.scores"), cache["cluster_stats"]

    if name == "P3_GENERIC_TWO_STATE":
        # Extra state used the ORDINARY way: the recovery variable shapes the amplitude
        # dynamics (adaptation), and the readout is on the amplitude.
        #
        # A cue-similarity gate on r was tried and REJECTED on dev. r is an adaptation
        # MAGNITUDE, not an identity code: the cue is a strongly-seeded node and the gold
        # deliberately is not, so |r_gold - r_cue| is near maximal and the gate scored the
        # gold at 0.0000 in every query -- top1 0.000. A control that scores below chance
        # is not a control. P6_SCALAR_TWO_CHANNEL is the readout-matched non-angular
        # comparator; P3's registered job is the capacity question, not identity coding.
        a, _r = cache["two_state"]
        return assert_cuda(a, "P3.scores"), None

    if name == "P6_SCALAR_TWO_CHANNEL":
        # The control that separates "phase" from "any second cue-seeded channel".
        # Same product/clamp form as P4, carrying NO angle. If P4 ~ P6, the oscillatory
        # vocabulary buys nothing over a plain second scalar field.
        a = cache["scalar"]
        return assert_cuda(a * cache["cue_field"].clamp_min(0.0), "P6.scores"), None

    if name in ("P4_PHASE_OSCILLATOR", "P5_PHASE_SHUFFLED"):
        a, th = cache["phase"]
        if name == "P5_PHASE_SHUFFLED":
            # Permute the phase-to-node assignment but keep the cue's OWN phase as the
            # reference. v0.1 permuted first and then read the reference out of the
            # permuted field, so P5's reference belonged to a random node and the control
            # destroyed its own baseline instead of isolating chain structure.
            perm = torch.randperm(N_NODES, generator=gen(world["key"] + "|p5"), device=P.DEV)
            th_read = th[:, perm]
        else:
            th_read = th
        cue_phase = th[ar, q["cue"]].unsqueeze(1)
        coh = torch.cos(th_read - cue_phase).clamp_min(0.0)
        stats = phase_assignment(th_read, world, q)
        return assert_cuda(a * coh, f"{name}.scores"), stats

    raise ValueError(name)


# ---------------------------------------------------------------- metrics


def score_world(world, q, scores):
    Q = QUERIES_PER_WORLD
    ar = torch.arange(Q, device=P.DEV)
    finite = bool(torch.isfinite(scores).all().item())
    s = scores.clone()
    s[q["seeds"] > 0] = -1e18                       # the answer cannot be a seed
    gold_score = s[ar, q["gold"]].unsqueeze(1)
    # Ties count PESSIMISTICALLY. v0.1 used strict `>`, so every node tied with gold was
    # scored as worse than gold -- and scores are extremely tie-heavy (most nodes sit at
    # exactly 0.0). That handed free top-1 and free recall@5 to whichever arm zeroed more
    # nodes, which is precisely the phase arms after their clamp.
    rank = (s > gold_score).sum(dim=1) + (s == gold_score).sum(dim=1) - 1
    top1 = (rank == 0).double().mean().item()
    rec5 = (rank < TOPK).double().mean().item()

    top = torch.topk(s, TOPK, dim=1).indices
    lab = world["chain_of"][top]
    active_lab = q["active_mask"].gather(1, lab.clamp_min(0))
    other = ((lab >= 0) & (lab != q["target"].unsqueeze(1)) & active_lab).double().mean().item()
    return {"top1": top1, "recall_at_5": rec5, "cross_chain_contamination": other,
            "runtime_finite": finite}


def static_baseline(world, q):
    """Diagnostic, not an arm: rank candidates by ORDER-BLIND static profile match.

    The preregistration calls "identical static profiles in different orders" the sharpest
    adversarial property. v0.1 built the profiles and never read them, so the property
    defended against an attack nobody mounted. This mounts it, and it should land at chance.
    """
    prof = world["profiles"]
    cue_sorted = torch.sort(prof[q["cue"]], dim=1).values.unsqueeze(1)      # (Q,1,4)
    all_sorted = torch.sort(prof, dim=1).values.unsqueeze(0)                # (1,N,4)
    match = (cue_sorted == all_sorted).sum(dim=2).to(P.DT)
    return score_world(world, q, match)


# ---------------------------------------------------------------- math audit (analytic)


def math_audit(world):
    """Exact spectrum of the two-state block operator, with no eigensolver on a
    non-symmetric matrix.

    All blocks of M are polynomials in W, so they commute: each eigenvalue mu of W
    contributes the two exact roots of the 2x2 block [[(1-d)+g*mu, -b], [e, 1-e]].
    W = D^-1 A is similar to the symmetric D^-1/2 A D^-1/2, so mu is real.

    SCOPE, stated plainly: this characterises P3_GENERIC_TWO_STATE's engine. It does NOT
    describe P4, whose phase dynamics are nonlinear; P4's registered diagnostic is the
    Kuramoto order parameter.
    """
    A, deg = world["A"], world["deg"]
    dm = deg.rsqrt()
    S = dm.unsqueeze(1) * A * dm.unsqueeze(0)
    S = 0.5 * (S + S.T)
    mu = torch.linalg.eigvalsh(S)
    assert_cuda(mu, "math_audit.mu")

    one_state = (1.0 - DELTA) + GAMMA * mu
    tr = one_state + (1.0 - EPS_REC)
    det = one_state * (1.0 - EPS_REC) + B_COUPLE * EPS_REC
    root = torch.sqrt((tr * tr - 4.0 * det).to(torch.complex128))
    lam = torch.cat([(tr + root) / 2.0, (tr - root) / 2.0])

    absl, arg = lam.abs(), lam.angle().abs()
    rho = float(absl.max().item())
    alpha = -torch.log(absl.clamp_min(1e-300))
    osc, decaying = arg > 1e-12, alpha > 1e-12
    eligible = osc & decaying
    q_vals = torch.where(eligible, arg / (2.0 * alpha), torch.zeros_like(arg))
    n_osc, n_growing = int(osc.sum().item()), int((~decaying).sum().item())
    has = bool(eligible.any().item())
    idx = int(torch.argmax(torch.where(eligible, absl, torch.full_like(absl, -1.0))).item())
    tau = -1.0 / math.log(1.0 - DELTA)

    return {
        "scope": "TWO_STATE_BLOCK_OPERATOR_OF_P3_ONLY -- does not describe P4 (nonlinear)",
        "block_operator": {
            "form": "M = [[(1-delta)I + gamma*W, -b*I], [eps*I, (1-eps)I]]",
            "delta": DELTA, "gamma": GAMMA, "b": B_COUPLE, "eps": EPS_REC,
            "shape": [2 * N_NODES, 2 * N_NODES],
            "method": "exact 2x2 block reduction (all blocks are polynomials in W)"},
        "one_state_operator_max_abs_imag": 0.0,
        "one_state_note": "(1-delta)I + gamma*W has a purely real spectrum by construction; "
                          "reproduces the design document's max|Im| = 0 finding.",
        "two_state_max_abs_imag": float(lam.imag.abs().max().item()),
        "n_complex_modes": n_osc, "n_growing_modes": n_growing,
        "n_modes_total": int(lam.numel()),
        "spectral_radius": rho, "stability_margin": 1.0 - rho, "stable": bool(rho < 1.0),
        "pulse_width_tau_waves": tau,
        "pulse_width_formula": "tau = -1/ln(1-delta)   (NOT 1/delta)",
        "q_formula": "Q = omega_d/(2*alpha); omega_d = |arg lambda| rad/wave; "
                     "alpha = -ln|lambda| nepers/wave; dimensionless; per named mode",
        "dominant_oscillatory_mode": None if not has else {
            "index": idx, "abs_lambda": float(absl[idx].item()),
            "re": float(lam.real[idx].item()), "im": float(lam.imag[idx].item()),
            "omega_d_rad_per_wave": float(arg[idx].item()),
            "alpha_nepers_per_wave": float(alpha[idx].item()),
            "period_waves": float(2 * math.pi / arg[idx].item()),
            "Q": float(q_vals[idx].item())},
        "Q_status": "Q_UNDEFINED_REAL_SPECTRUM" if not has else "DERIVED_TELEMETRY_ONLY",
    }


def phase_sync_report(world, q, a, th):
    """Kuramoto order parameter -- the registered diagnostic for the NONLINEAR P4 system."""
    memb = world["memb"].unsqueeze(0) * q["active_mask"].unsqueeze(-1).to(P.DT)
    z = torch.exp(1j * th.to(torch.complex128)).unsqueeze(1)
    cnt = memb.sum(dim=2)
    centre = (z * memb.to(torch.complex128)).sum(dim=2) / cnt.clamp_min(1e-12)
    live = cnt > 0
    order = float(centre.abs()[live].mean().item()) if bool(live.any()) else None
    ang = centre.angle()
    pair = q["active_mask"].unsqueeze(2) & q["active_mask"].unsqueeze(1)
    pair = pair & ~torch.eye(world["pool"], dtype=torch.bool, device=P.DEV).unsqueeze(0)
    d = (ang.unsqueeze(2) - ang.unsqueeze(1)).abs()
    d = torch.minimum(d, 2 * math.pi - d)
    sep = float(d[pair].mean().item()) if bool(pair.any()) else None
    return {"mean_within_chain_order": order, "mean_cross_chain_separation_rad": sep}


# ---------------------------------------------------------------- run


def phase_convergence_sweep():
    """DEV-WORLD evidence for the PHASE_SUBSTEPS freeze, persisted in the receipt.

    Records P4 top-1 as well as the two order parameters -- v0.1 recorded only the order
    parameters, so the receipt could not corroborate the column the freeze was based on.
    """
    rows = []
    for sub in (1, 4, 10, 25):
        ords, seps, t4 = [], [], []
        for wid in DEV_WORLDS:
            for k in (2, 3, 4):
                w = build_world(wid, k)
                q = build_queries(w)
                th0 = (torch.rand((QUERIES_PER_WORLD, N_NODES),
                                  generator=gen(w["key"] + "|phase0"),
                                  device=P.DEV, dtype=P.DT) * 2 - 1) * math.pi
                old = P.PHASE_SUBSTEPS
                P.PHASE_SUBSTEPS = sub
                try:
                    a, th = propagate_phase(q["seeds"], th0, w["A"], w["deg"], w["W"])
                finally:
                    P.PHASE_SUBSTEPS = old
                ps = phase_sync_report(w, q, a, th)
                if ps["mean_within_chain_order"] is not None:
                    ords.append(ps["mean_within_chain_order"])
                if ps["mean_cross_chain_separation_rad"] is not None:
                    seps.append(ps["mean_cross_chain_separation_rad"])
                cue = th[torch.arange(QUERIES_PER_WORLD, device=P.DEV), q["cue"]].unsqueeze(1)
                t4.append(score_world(w, q, a * torch.cos(th - cue).clamp_min(0.0))["top1"])
        rows.append({"phase_substeps": sub, "waves": DEPTH,
                     "mean_within_chain_order": (sum(ords) / len(ords)) if ords else None,
                     "mean_cross_chain_separation_rad": (sum(seps) / len(seps)) if seps else None,
                     "p4_top1": sum(t4) / len(t4)})
    return {"note": "DEV worlds only (0-5). Justifies the PHASE_SUBSTEPS freeze at a "
                    "CONVERGED value rather than at the transient that flatters P4.",
            "frozen_at": P.PHASE_SUBSTEPS, "rows": rows}


def run_world(world_id, k):
    w = build_world(world_id, k)
    q = build_queries(w)
    cluster = infer_clusters(w)
    cache = {"clusters": cluster, "scalar": propagate_scalar(q["seeds"], w["W"]),
             "two_state": propagate_two_state(q["seeds"], w["W"])}
    cue_seed = torch.zeros_like(q["seeds"])
    cue_seed[torch.arange(QUERIES_PER_WORLD, device=P.DEV), q["cue"]] = 1.0
    cache["cue_field"] = propagate_scalar(cue_seed, w["W"])
    th0 = (torch.rand((QUERIES_PER_WORLD, N_NODES), generator=gen(w["key"] + "|phase0"),
                      device=P.DEV, dtype=P.DT) * 2 - 1) * math.pi
    cache["phase"] = propagate_phase(q["seeds"], th0, w["A"], w["deg"], w["W"])

    # inferred-cluster quality, measured the same circular way as the phase arms
    memb = w["memb"]
    correct = tot = 0
    maj = {}
    for ci in range(w["pool"]):
        nodes = (memb[ci] > 0).nonzero(as_tuple=True)[0]
        nodes = nodes[w["chain_of"][nodes] == ci]
        g = cluster[nodes]
        g = g[g >= 0]
        if g.numel():
            m = int(torch.mode(g).values.item())
            maj[ci] = m
            correct += int((g == m).sum().item())
            tot += int(g.numel())
    merges = sum(1 for i in maj for j in maj if i < j and maj[i] == maj[j]) / max(1, w["pool"])
    cache["cluster_stats"] = ((correct / tot) if tot else None, float(merges))

    out = {"world_id": world_id, "k_chains": k, "arms": {}}
    for name in ARMS:
        torch.cuda.reset_peak_memory_stats()
        e0, e1 = torch.cuda.Event(True), torch.cuda.Event(True)
        e0.record()
        scores, stats = arm_scores(name, w, q, cache)
        e1.record()
        torch.cuda.synchronize()
        m = score_world(w, q, scores)
        m["chain_assignment_accuracy"] = None if stats is None else stats[0]
        m["false_chain_merges"] = None if stats is None else stats[1]
        m["cuda_time_ms"] = e0.elapsed_time(e1)
        m["peak_vram_bytes"] = int(torch.cuda.max_memory_allocated())
        out["arms"][name] = m
    out["B_STATIC_diagnostic"] = static_baseline(w, q)
    out["phase_sync"] = phase_sync_report(w, q, *cache["phase"])
    return out


def paired(results, a, b, key="top1", margin=MARGIN):
    d = [r["arms"][a][key] - r["arms"][b][key] for r in results
         if r["arms"][a].get(key) is not None and r["arms"][b].get(key) is not None]
    if len(d) < 5:
        return {"mean_delta": None, "worlds_positive": 0, "n": len(d), "win": False,
                "insufficient_n": True}
    mean = sum(d) / len(d)
    pos = sum(1 for x in d if x > 0)
    return {"mean_delta": mean, "worlds_positive": pos, "n": len(d),
            "win": bool(mean > margin and pos >= WIN_FRACTION * len(d))}


PAIRS = [("P3_GENERIC_TWO_STATE", "P0_SCALAR"),
         ("P4_PHASE_OSCILLATOR", "P0_SCALAR"),
         ("P4_PHASE_OSCILLATOR", "P3_GENERIC_TWO_STATE"),
         ("P4_PHASE_OSCILLATOR", "P5_PHASE_SHUFFLED"),
         ("P4_PHASE_OSCILLATOR", "P6_SCALAR_TWO_CHANNEL"),
         ("P4_PHASE_OSCILLATOR", "P2_INFERRED_CHAIN_TAG"),
         ("P2_INFERRED_CHAIN_TAG", "P4_PHASE_OSCILLATOR"),
         ("P2_INFERRED_CHAIN_TAG", "P0_SCALAR")]


def emit_status(held, audit):
    """Deterministic status. Every win must hold INDEPENDENTLY at K=2, K=3 and K=4."""
    ks = [k for k in K_SETTINGS if k > 1]
    by_k = {k: [r for r in held if r["k_chains"] == k] for k in ks}
    single = [r for r in held if r["k_chains"] == 1]

    per_k = {k: {f"{a}_vs_{b}": paired(by_k[k], a, b) for a, b in PAIRS} for k in ks}
    gates = {k: {"p0_top1": sum(r["arms"]["P0_SCALAR"]["top1"] for r in by_k[k]) / len(by_k[k]),
                 "p1_oracle_top1": sum(r["arms"]["P1_ORACLE_CHAIN_TAG"]["top1"]
                                       for r in by_k[k]) / len(by_k[k])} for k in ks}

    def wins(a, b):
        """A win must hold at EVERY K. v0.1 pooled 60 worlds and tolerated 18 negatives."""
        return all(per_k[k][f"{a}_vs_{b}"]["win"] for k in ks)

    capacity = {}
    for arm in ARMS:
        ok = [k for k in ks
              if sum(r["arms"][arm]["top1"] for r in by_k[k]) / len(by_k[k]) >= CAPACITY_TOP1]
        capacity[arm] = max(ok) if ok else None

    # --- phase regime + interpretation guard ------------------------------------------
    ords = [r["phase_sync"]["mean_within_chain_order"] for r in held
            if r["k_chains"] > 1 and r["phase_sync"]["mean_within_chain_order"] is not None]
    seps = [r["phase_sync"]["mean_cross_chain_separation_rad"] for r in held
            if r["k_chains"] > 1 and r["phase_sync"]["mean_cross_chain_separation_rad"] is not None]
    mo = (sum(ords) / len(ords)) if ords else None
    ms = (sum(seps) / len(seps)) if seps else None
    sync = bool(mo is not None and mo > 0.95 and ms is not None and ms < 0.10)
    p4p0 = [per_k[k]["P4_PHASE_OSCILLATOR_vs_P0_SCALAR"]["mean_delta"] for k in ks]
    p4_eq_p0 = all(x is not None and abs(x) < MARGIN for x in p4p0)
    phase = {"mean_within_chain_order": mo, "mean_cross_chain_separation_rad": ms,
             "globally_synchronised": sync, "p4_degenerate_to_scalar": bool(sync and p4_eq_p0),
             "interpretation_guard": None}
    if phase["p4_degenerate_to_scalar"]:
        phase["interpretation_guard"] = (
            "PHASE_DEGENERATE_TO_SCALAR: chains locked internally but ALL locked to the SAME "
            "phase, so cos(delta theta)=1 and P4 reduces to P0. Here P4 > P5 shows only that "
            "RANDOM phases are worse than UNIFORM phases. That is NOT evidence of chain "
            "binding. Uniform positive coupling on a connected graph has one stable "
            "attractor: global synchrony. Separating chains by phase would need cross-chain "
            "inhibition or frequency heterogeneity -- a free frequency control is forbidden "
            "by the owner's constraint, so neither is added.")

    # --- safety, in the right units ----------------------------------------------------
    contam = {k: paired(by_k[k], "P4_PHASE_OSCILLATOR", "P0_SCALAR",
                        "cross_chain_contamination", CONTAM_MARGIN) for k in ks}
    merges = {k: paired(by_k[k], "P4_PHASE_OSCILLATOR", "P2_INFERRED_CHAIN_TAG",
                        "false_chain_merges", MERGE_MARGIN) for k in ks}
    nonfinite = any(not r["arms"]["P4_PHASE_OSCILLATOR"]["runtime_finite"] for r in held)
    missing = any(contam[k]["mean_delta"] is None or merges[k]["mean_delta"] is None for k in ks)
    unsafe = nonfinite or any(contam[k]["win"] or merges[k]["win"] for k in ks)

    # --- the law -----------------------------------------------------------------------
    st, reason = None, None
    single_leak = single and all(
        paired(single, "P4_PHASE_OSCILLATOR", x)["win"] for x in ("P0_SCALAR",))
    if unsafe:
        st = "PHASE_MEMORY_UNSAFE"                        # overrides everything
    elif missing:
        st, reason = "STATUS_NOT_EMITTED", "SAFETY_METRIC_MISSING"   # fail CLOSED
    elif any(gates[k]["p0_top1"] >= GATE_HEADROOM_TOP1 for k in ks):
        st, reason = "STATUS_NOT_EMITTED", "NO_MULTICHAIN_GAP"
    elif any(gates[k]["p1_oracle_top1"] < GATE_ORACLE_TOP1 for k in ks):
        st, reason = "STATUS_NOT_EMITTED", "INSTRUMENT_OR_TASK_ILL_POSED"
    elif not audit["stable"]:
        st, reason = "STATUS_NOT_EMITTED", "P3_OPERATOR_UNSTABLE"
    elif phase["p4_degenerate_to_scalar"]:
        # The guard BLOCKS the law. v0.1 wrote it into the receipt and then ignored it,
        # which is "PASS with caveats" implemented in Python.
        st, reason = "STATUS_NOT_EMITTED", "PHASE_DEGENERATE_TO_SCALAR"
    elif single_leak:
        # A P4 win at K=1, where there is nothing to separate, is a generic ranking
        # advantage, not chain separation.
        st, reason = "STATUS_NOT_EMITTED", "P4_WINS_ON_SINGLE_CHAIN_TOO"
    elif (wins("P4_PHASE_OSCILLATOR", "P0_SCALAR")
          and wins("P4_PHASE_OSCILLATOR", "P3_GENERIC_TWO_STATE")
          and wins("P4_PHASE_OSCILLATOR", "P5_PHASE_SHUFFLED")
          and wins("P4_PHASE_OSCILLATOR", "P6_SCALAR_TWO_CHANNEL")):
        if wins("P4_PHASE_OSCILLATOR", "P2_INFERRED_CHAIN_TAG"):
            st = "PHASE_MULTICHAIN_SIGNAL"
        elif all(per_k[k]["P2_INFERRED_CHAIN_TAG_vs_P4_PHASE_OSCILLATOR"]["mean_delta"] >= 0
                 for k in ks):
            st = "PHASE_CODING_WORKS_TAGS_PREFERRED"      # section 6 requires P2 >= P4
        else:
            st, reason = "STATUS_NOT_EMITTED", "P4_AND_P2_AMBIGUOUS"
    elif (wins("P3_GENERIC_TWO_STATE", "P0_SCALAR")
          and not wins("P4_PHASE_OSCILLATOR", "P3_GENERIC_TWO_STATE")):
        st = "EXTRA_STATE_CAPACITY_SUPPORTED"
    elif (wins("P2_INFERRED_CHAIN_TAG", "P0_SCALAR")
          and all(per_k[k]["P2_INFERRED_CHAIN_TAG_vs_P4_PHASE_OSCILLATOR"]["mean_delta"] >= 0
                  for k in ks)):
        st = "EXPLICIT_CHAIN_TAGS_PREFERRED"
    else:
        st, reason = "STATUS_NOT_EMITTED", "NO_ARM_WINS"

    return {"status": st, "reason": reason, "per_k_comparisons": per_k, "gates_per_k": gates,
            "phase_regime": phase, "simultaneous_chain_capacity": capacity,
            "safety": {"contamination_per_k": contam, "merges_per_k": merges,
                       "p4_runtime_nonfinite": nonfinite},
            "p3_operator_unstable": not audit["stable"],
            "escalate_to_owner": st == "STATUS_NOT_EMITTED"}


VOLATILE = ("cuda_time_ms", "peak_vram_bytes", "wall_s", "_wall_s", "host_wall_s", "device")


def strip_volatile(obj):
    if isinstance(obj, dict):
        return {k: strip_volatile(v) for k, v in obj.items() if k not in VOLATILE}
    if isinstance(obj, list):
        return [strip_volatile(v) for v in obj]
    return obj


def group(rs):
    if not rs:
        return {}
    return {a: {m: sum(r["arms"][a][m] for r in rs) / len(rs)
                for m in ("top1", "recall_at_5", "cross_chain_contamination")} for a in ARMS}


def main():
    require_cuda()
    t_start = time.perf_counter()
    held_results, dev_results, receipt = [], [], {}
    try:
        audit = math_audit(build_world(0, 3))
        sweep = phase_convergence_sweep()
        for k in K_SETTINGS:
            for wid in DEV_WORLDS:
                dev_results.append(run_world(wid, k))
            for wid in HELDOUT_WORLDS:
                held_results.append(run_world(wid, k))
        verdict = emit_status(held_results, audit)
    except Exception:
        json.dump({"FAILED": True, "traceback": traceback.format_exc(),
                   "partial_heldout": strip_volatile(held_results),
                   "partial_dev": strip_volatile(dev_results)},
                  open("CMB_P0_RECEIPT.json", "w"), indent=1, sort_keys=True)
        print("RUN FAILED -- partial receipt written")
        traceback.print_exc()
        return 2

    single = [r for r in held_results if r["k_chains"] == 1]
    multi = [r for r in held_results if r["k_chains"] > 1]
    receipt = {
        "project": "CMB-P0 Multi-Chain Phase Necessity Bench",
        "harness_version": "v0.2",
        "preregistration": "CMB_P0_PREREGISTRATION.md v0.1 + A1 + A2",
        "frozen_params": {"N_NODES": N_NODES, "D_CONTENT": D_CONTENT, "L_CHAIN": L_CHAIN,
                          "POOL_EXTRA": P.POOL_EXTRA, "QUERIES_PER_WORLD": QUERIES_PER_WORLD,
                          "DELTA": DELTA, "GAMMA": GAMMA, "DEPTH": DEPTH, "TOPK": TOPK,
                          "TOPK_KEEP": TOPK_KEEP, "B_COUPLE": B_COUPLE, "EPS_REC": EPS_REC,
                          "KC_PHASE": P.KC_PHASE, "PHASE_SUBSTEPS": P.PHASE_SUBSTEPS,
                          "MARGIN": MARGIN, "MERGE_MARGIN": MERGE_MARGIN,
                          "CONTAM_MARGIN": CONTAM_MARGIN, "WIN_FRACTION": WIN_FRACTION},
        "math_audit": audit,
        "phase_convergence_sweep": sweep,
        "SINGLE_CHAIN_heldout": group(single),
        "MULTI_CHAIN_heldout_by_k": {k: group([r for r in multi if r["k_chains"] == k])
                                     for k in K_SETTINGS if k > 1},
        "verdict": verdict,
        "dev_worlds": strip_volatile(dev_results),
        "heldout_worlds": strip_volatile(held_results),
        "compute": dict(gpu_identity(),
                        peak_vram_bytes=int(torch.cuda.max_memory_allocated()),
                        host_wall_s=round(time.perf_counter() - t_start, 2)),
        "claim_note": "No resonance-specific or CAS-specific claim is licensed. "
                      "P1_ORACLE_CHAIN_TAG is an upper bound, never a method.",
    }
    payload = json.dumps(strip_volatile({k: receipt[k] for k in (
        "frozen_params", "math_audit", "phase_convergence_sweep", "SINGLE_CHAIN_heldout",
        "MULTI_CHAIN_heldout_by_k", "verdict", "heldout_worlds")}), sort_keys=True)
    receipt["determinism"] = {
        "content_hash": hashlib.sha256(payload.encode()).hexdigest(),
        "note": "covers frozen params, math audit, sweep, both world groups and the "
                "verdict; EXCLUDES cuda_time_ms, peak_vram_bytes, device and all clocks"}
    with open("CMB_P0_RECEIPT.json", "w") as f:
        json.dump(receipt, f, indent=1, sort_keys=True)

    print("STATUS:", verdict["status"], "| REASON:", verdict.get("reason"))
    for k, g in receipt["MULTI_CHAIN_heldout_by_k"].items():
        print(f"  K={k}: " + " ".join(f"{a.split('_')[0]}={g[a]['top1']:.3f}" for a in ARMS))
    print("  K=1 : " + " ".join(
        f"{a.split('_')[0]}={receipt['SINGLE_CHAIN_heldout'][a]['top1']:.3f}" for a in ARMS))
    pr = verdict["phase_regime"]
    print("PHASE: order=%s sep=%s sync=%s degenerate=%s" % (
        None if pr["mean_within_chain_order"] is None else round(pr["mean_within_chain_order"], 4),
        None if pr["mean_cross_chain_separation_rad"] is None
        else round(pr["mean_cross_chain_separation_rad"], 4),
        pr["globally_synchronised"], pr["p4_degenerate_to_scalar"]))
    dm = audit["dominant_oscillatory_mode"]
    print("SPECTRUM: complex=%d/%d rho=%.4f Q=%s tau=%.4f" % (
        audit["n_complex_modes"], audit["n_modes_total"], audit["spectral_radius"],
        "n/a" if dm is None else round(dm["Q"], 4), audit["pulse_width_tau_waves"]))
    print("CAPACITY:", json.dumps(verdict["simultaneous_chain_capacity"]))
    print("HASH:", receipt["determinism"]["content_hash"][:16])
    print("PEAK_VRAM:", receipt["compute"]["peak_vram_bytes"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
