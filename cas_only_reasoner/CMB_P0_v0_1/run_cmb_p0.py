"""CMB-P0 runner -- six arms, math audit, gates, deterministic status.

Frozen design: CMB_P0_PREREGISTRATION.md v0.1.
GPU only. Fail closed. No CPU fallback branch exists.
"""
import hashlib
import json
import math
import sys
import time

import torch

import cmb_p0 as P
from cmb_p0 import (ARMS, DELTA, DEPTH, DEV_WORLDS, D_CONTENT, EPS_REC, B_COUPLE,
                    GAMMA, GATE_HEADROOM_TOP1, GATE_ORACLE_TOP1, HELDOUT_WORLDS,
                    K_SETTINGS, L_CHAIN, MARGIN, N_NODES, QUERIES_PER_WORLD, TOPK,
                    WIN_FRACTION, assert_cuda, build_queries, build_world,
                    cluster_by_phase, gen, gpu_identity, infer_clusters,
                    propagate_phase, propagate_scalar, propagate_two_state, require_cuda)


# ---------------------------------------------------------------- the six arms


def arm_scores(name, world, q, cache):
    """Return (scores over N nodes per query, assignment-or-None). Every tensor on CUDA."""
    W, A, deg = world["W"], world["A"], world["deg"]
    k = world["k_chains"]
    Q = QUERIES_PER_WORLD
    seeds = q["seeds"]
    ar = torch.arange(Q, device=P.DEV)

    if name == "P0_SCALAR":
        return assert_cuda(propagate_scalar(seeds, W), "P0.scores"), None

    if name == "P1_ORACLE_CHAIN_TAG":
        # ORACLE: handed the true chain membership. Upper bound, never a method.
        ch = torch.zeros((Q, k, N_NODES), device=P.DEV, dtype=P.DT)
        for ci in range(k):
            ch[:, ci, world["chains"][ci][: L_CHAIN - 1]] = 1.0
        ch[ar, q["target"], q["cue"]] += 1.0
        out = propagate_scalar(ch.reshape(Q * k, N_NODES), W).reshape(Q, k, N_NODES)
        return assert_cuda(out[ar, q["target"]], "P1.scores"), "ORACLE"

    if name == "P2_INFERRED_CHAIN_TAG":
        nodes, cluster = cache["clusters"]
        ch = torch.zeros((Q, k, N_NODES), device=P.DEV, dtype=P.DT)
        for gi in range(k):
            members = nodes[cluster[nodes] == gi]
            if members.numel():
                ch[:, gi, members] = 1.0
        cue_group = cluster[q["cue"]].clamp_min(0)
        ch[ar, cue_group, q["cue"]] += 1.0
        out = propagate_scalar(ch.reshape(Q * k, N_NODES), W).reshape(Q, k, N_NODES)
        return assert_cuda(out[ar, cue_group], "P2.scores"), cluster

    if name == "P3_GENERIC_TWO_STATE":
        a, _r = propagate_two_state(seeds, W)
        return assert_cuda(a, "P3.scores"), None

    if name in ("P4_PHASE_OSCILLATOR", "P5_PHASE_SHUFFLED"):
        a, th = cache["phase"]
        if name == "P5_PHASE_SHUFFLED":
            # identical dynamics, identical amplitudes; ONLY the phase-to-node assignment
            # is destroyed at readout. If P4 ~ P5, phase carries no chain information.
            perm = torch.randperm(N_NODES, generator=gen(world["key"] + "|p5"), device=P.DEV)
            th = th[:, perm]
        cue_phase = th[torch.arange(Q, device=P.DEV), q["cue"]].unsqueeze(1)
        coh = torch.cos(th - cue_phase).clamp_min(0.0)
        assign = None
        if name == "P4_PHASE_OSCILLATOR":
            nodes = (q["seeds"][0] > 0).nonzero(as_tuple=True)[0]
            assign = cluster_by_phase(th[0], nodes, k)
        return assert_cuda(a * coh, f"{name}.scores"), assign

    raise ValueError(name)


# ---------------------------------------------------------------- metrics


def score_world(world, q, scores):
    """Paired metrics for one arm on one world. All arms see identical worlds and queries."""
    Q = QUERIES_PER_WORLD
    ar = torch.arange(Q, device=P.DEV)
    finite = bool(torch.isfinite(scores).all().item())
    s = scores.clone()
    s[q["seeds"] > 0] = -1e18                       # the answer cannot be a seed
    gold_score = s[ar, q["gold"]].unsqueeze(1)
    rank = (s > gold_score).sum(dim=1)              # 0 == top-1
    top1 = (rank == 0).double().mean().item()
    rec5 = (rank < TOPK).double().mean().item()

    top = torch.topk(s, TOPK, dim=1).indices
    lab = world["chain_of"][top]                    # (Q, TOPK)
    tgt = q["target"].unsqueeze(1)
    other = ((lab >= 0) & (lab != tgt)).double().mean().item()
    return {"top1": top1, "recall_at_5": rec5, "cross_chain_contamination": other,
            "runtime_finite": finite}


def assignment_metrics(world, q, assign):
    """Chain-assignment accuracy and false chain merges, by best permutation match."""
    k = world["k_chains"]
    if assign is None:
        return {"chain_assignment_accuracy": None, "false_chain_merges": None}
    if isinstance(assign, str):                     # ORACLE
        return {"chain_assignment_accuracy": 1.0, "false_chain_merges": 0,
                "oracle": True}
    majority, correct, total = {}, 0, 0
    for ci in range(k):
        nodes = world["chains"][ci][: L_CHAIN - 1]
        nodes = nodes[world["chain_of"][nodes] == ci]      # drop shared/ambiguous nodes
        if not nodes.numel():
            continue
        g = assign[nodes]
        g = g[g >= 0]
        if not g.numel():
            continue
        m = int(torch.mode(g).values.item())
        majority[ci] = m
        correct += int((g == m).sum().item())
        total += int(g.numel())
    merges = 0
    vals = list(majority.items())
    for i in range(len(vals)):
        for j in range(i + 1, len(vals)):
            if vals[i][1] == vals[j][1]:
                merges += 1
    return {"chain_assignment_accuracy": (correct / total) if total else None,
            "false_chain_merges": merges}


# ---------------------------------------------------------------- math audit (analytic)


def math_audit():
    """Exact spectrum of the two-state block operator, with no numerical eigensolver on a
    non-symmetric matrix.

    All four blocks of M are polynomials in W, so they commute. For each eigenvalue mu of W,
    M contributes the two eigenvalues of the 2x2 block

        B(mu) = [[ (1-d) + g*mu , -b ], [ e , 1-e ]]

    which are exact roots of a quadratic. W = D^-1 A is similar to the symmetric
    D^-1/2 A D^-1/2, so mu is real -- computed with eigvalsh, which is supported on CUDA.
    """
    w = build_world(0, 3)
    A, deg = w["A"], w["deg"]
    dm = deg.rsqrt()
    S = dm.unsqueeze(1) * A * dm.unsqueeze(0)
    S = 0.5 * (S + S.T)
    mu = torch.linalg.eigvalsh(S)                   # real spectrum of W
    assert_cuda(mu, "math_audit.mu")

    one_state = (1.0 - DELTA) + GAMMA * mu          # the CURRENT engine's operator
    tr = one_state + (1.0 - EPS_REC)
    det = one_state * (1.0 - EPS_REC) + B_COUPLE * EPS_REC
    disc = (tr * tr - 4.0 * det).to(torch.complex128)
    root = torch.sqrt(disc)
    lam = torch.cat([(tr + root) / 2.0, (tr - root) / 2.0])

    absl = lam.abs()
    arg = lam.angle().abs()
    rho = float(absl.max().item())
    alpha = -torch.log(absl.clamp_min(1e-300))
    osc = arg > 1e-12
    decaying = alpha > 1e-12                        # alpha <= 0 means the mode GROWS
    q_vals = torch.where(osc & decaying, arg / (2.0 * alpha), torch.zeros_like(arg))
    # Q is reported for the dominant DECAYING oscillatory mode. A growing mode has no Q:
    # reporting one would silently hide an instability behind a finite-looking number.
    eligible = osc & decaying
    n_growing = int((~decaying).sum().item())
    idx = int(torch.argmax(torch.where(eligible, absl, torch.full_like(absl, -1.0))).item())

    tau = -1.0 / math.log(1.0 - DELTA)              # owner's correction, NOT 1/delta
    n_osc = int(osc.sum().item())
    return {
        "block_operator": {
            "form": "M = [[(1-delta)I + gamma*W, -b*I], [eps*I, (1-eps)I]]",
            "delta": DELTA, "gamma": GAMMA, "b": B_COUPLE, "eps": EPS_REC,
            "shape": [2 * N_NODES, 2 * N_NODES],
            "method": "exact 2x2 block reduction (all blocks are polynomials in W)",
        },
        "one_state_operator_max_abs_imag": 0.0,
        "one_state_note": "(1-delta)I + gamma*W has a purely real spectrum by construction; "
                          "this reproduces the design document's max|Im|=0 finding.",
        "two_state_max_abs_imag": float(lam.imag.abs().max().item()),
        "n_complex_modes": n_osc,
        "n_growing_modes": n_growing,
        "n_modes_total": int(lam.numel()),
        "spectral_radius": rho,
        "stability_margin": 1.0 - rho,
        "stable": bool(rho < 1.0),
        "stability_note": "describes the TWO-STATE BLOCK OPERATOR used by "
                          "P3_GENERIC_TWO_STATE. It does NOT describe P4_PHASE_OSCILLATOR, "
                          "whose phase dynamics are nonlinear (Kuramoto); P4 safety is "
                          "judged by its own runtime finiteness, contamination and merges.",
        "pulse_width_tau_waves": tau,
        "pulse_width_formula": "tau = -1/ln(1-delta)   (NOT 1/delta)",
        "q_formula": "Q = omega_d / (2*alpha); omega_d = |arg lambda| rad/wave; "
                     "alpha = -ln|lambda| nepers/wave; dimensionless; per named mode",
        "dominant_oscillatory_mode": {
            "index": idx,
            "abs_lambda": float(absl[idx].item()),
            "re": float(lam.real[idx].item()),
            "im": float(lam.imag[idx].item()),
            "omega_d_rad_per_wave": float(arg[idx].item()),
            "alpha_nepers_per_wave": float(alpha[idx].item()),
            "period_waves": float(2 * math.pi / arg[idx].item()) if arg[idx] > 1e-12 else None,
            "Q": float(q_vals[idx].item()),
        },
        "Q_status": "Q_UNDEFINED_REAL_SPECTRUM" if n_osc == 0 else "DERIVED_TELEMETRY_ONLY",
        "eigenvalue_sample_first_12": [[float(lam.real[i].item()), float(lam.imag[i].item())]
                                       for i in range(min(12, lam.numel()))],
    }


def phase_sync_report(world, q, a, th):
    """Kuramoto order parameter -- the real diagnostic for the NONLINEAR phase system.

    The block-operator spectrum above does not describe P4: its phase dynamics are
    nonlinear, and its phase-DIFFERENCE Jacobian is a weighted graph Laplacian with a real
    spectrum. Synchronisation, not rotation, is what P4 claims. This measures that directly.
    """
    k = world["k_chains"]
    within, centers = [], []
    for ci in range(k):
        nodes = world["chains"][ci][: L_CHAIN - 1]
        nodes = nodes[world["chain_of"][nodes] == ci]
        if not nodes.numel():
            continue
        z = torch.exp(1j * th[:, nodes].to(torch.complex128)).mean(dim=1)
        within.append(float(z.abs().mean().item()))
        centers.append(z.mean())
    sep = []
    for i in range(len(centers)):
        for j in range(i + 1, len(centers)):
            d = abs(float((centers[i] / centers[i].abs().clamp_min(1e-12)).angle().item()
                          - (centers[j] / centers[j].abs().clamp_min(1e-12)).angle().item()))
            sep.append(min(d, 2 * math.pi - d))
    return {"within_chain_order_parameter": within,
            "mean_within_chain_order": (sum(within) / len(within)) if within else None,
            "cross_chain_phase_separation_rad": sep,
            "mean_cross_chain_separation_rad": (sum(sep) / len(sep)) if sep else None}


# ---------------------------------------------------------------- run


def run_world(world_id, k):
    w = build_world(world_id, k)
    q = build_queries(w)
    cache = {"clusters": infer_clusters(w, q, k)}
    th0 = (torch.rand((QUERIES_PER_WORLD, N_NODES), generator=gen(w["key"] + "|phase0"),
                      device=P.DEV, dtype=P.DT) * 2 - 1) * math.pi
    cache["phase"] = propagate_phase(q["seeds"], th0, w["A"], w["deg"], w["W"])

    out = {"world_id": world_id, "k_chains": k, "arms": {}}
    for name in ARMS:
        t0 = time.perf_counter()
        scores, assign = arm_scores(name, w, q, cache)
        torch.cuda.synchronize()
        m = score_world(w, q, scores)
        m.update(assignment_metrics(w, q, assign))
        m["_wall_s"] = round(time.perf_counter() - t0, 4)     # volatile, excluded from hash
        m["device"] = str(scores.device)
        out["arms"][name] = m
    out["phase_sync"] = phase_sync_report(w, q, *cache["phase"])
    return out


def paired(results, arm_a, arm_b, key="top1"):
    """Paired per-world difference. All arms saw identical worlds and queries."""
    d = [r["arms"][arm_a][key] - r["arms"][arm_b][key] for r in results
         if r["arms"][arm_a].get(key) is not None and r["arms"][arm_b].get(key) is not None]
    if not d:
        return {"mean_delta": None, "worlds_positive": 0, "n": 0, "win": False}
    mean = sum(d) / len(d)
    pos = sum(1 for x in d if x > 0)
    return {"mean_delta": mean, "worlds_positive": pos, "n": len(d),
            "win": bool(mean > MARGIN and pos >= WIN_FRACTION * len(d))}


def emit_status(multi, audit):
    """Deterministic status. Gates first; the five-outcome law only runs if both pass."""
    p0 = sum(r["arms"]["P0_SCALAR"]["top1"] for r in multi) / len(multi)
    p1 = sum(r["arms"]["P1_ORACLE_CHAIN_TAG"]["top1"] for r in multi) / len(multi)
    if p0 >= GATE_HEADROOM_TOP1:
        return {"status": "STATUS_NOT_EMITTED", "reason": "NO_MULTICHAIN_GAP",
                "p0_top1": p0, "escalate_to_owner": True}
    if p1 < GATE_ORACLE_TOP1:
        return {"status": "STATUS_NOT_EMITTED", "reason": "INSTRUMENT_OR_TASK_ILL_POSED",
                "p1_oracle_top1": p1, "escalate_to_owner": True}

    cmp = {f"{a}_vs_{b}": paired(multi, a, b)
           for a, b in [("P3_GENERIC_TWO_STATE", "P0_SCALAR"),
                        ("P4_PHASE_OSCILLATOR", "P0_SCALAR"),
                        ("P4_PHASE_OSCILLATOR", "P3_GENERIC_TWO_STATE"),
                        ("P4_PHASE_OSCILLATOR", "P5_PHASE_SHUFFLED"),
                        ("P4_PHASE_OSCILLATOR", "P2_INFERRED_CHAIN_TAG"),
                        ("P2_INFERRED_CHAIN_TAG", "P0_SCALAR")]}
    contam = paired(multi, "P4_PHASE_OSCILLATOR", "P0_SCALAR",
                    "cross_chain_contamination")
    merges = paired(multi, "P4_PHASE_OSCILLATOR", "P2_INFERRED_CHAIN_TAG",
                    "false_chain_merges")

    # P4 safety is judged on P4's OWN behaviour. audit["stable"] describes the two-state
    # block operator, which is P3's engine -- P4's phase dynamics are nonlinear and that
    # spectrum does not govern them. Conflating the two would blame P4 for P3's operator.
    p4_nonfinite = any(not r["arms"]["P4_PHASE_OSCILLATOR"]["runtime_finite"] for r in multi)
    p3_ineligible = not audit["stable"]
    unsafe = (p4_nonfinite
              or (contam["mean_delta"] or 0) > MARGIN
              or (merges["mean_delta"] or 0) > MARGIN)
    reason = None
    if unsafe:
        st = "PHASE_MEMORY_UNSAFE"                       # overrides every other outcome
    elif p3_ineligible:
        # The capacity control's own operator grows without bound, so "P4 beat P3" and
        # "P3 beat P0" are both uninterpretable. Emit nothing; escalate.
        st, reason = "STATUS_NOT_EMITTED", "P3_OPERATOR_UNSTABLE"
    elif (cmp["P4_PHASE_OSCILLATOR_vs_P0_SCALAR"]["win"]
          and cmp["P4_PHASE_OSCILLATOR_vs_P3_GENERIC_TWO_STATE"]["win"]
          and cmp["P4_PHASE_OSCILLATOR_vs_P5_PHASE_SHUFFLED"]["win"]):
        st = ("PHASE_MULTICHAIN_SIGNAL"
              if cmp["P4_PHASE_OSCILLATOR_vs_P2_INFERRED_CHAIN_TAG"]["win"]
              else "PHASE_CODING_WORKS_TAGS_PREFERRED")
    elif cmp["P3_GENERIC_TWO_STATE_vs_P0_SCALAR"]["win"]:
        st = "EXTRA_STATE_CAPACITY_SUPPORTED"
    elif cmp["P2_INFERRED_CHAIN_TAG_vs_P0_SCALAR"]["win"]:
        st = "EXPLICIT_CHAIN_TAGS_PREFERRED"
    else:
        st, reason = "STATUS_NOT_EMITTED", "NO_ARM_WINS"
    return {"status": st, "reason": reason, "comparisons": cmp,
            "contamination_p4_minus_p0": contam, "false_merges_p4_minus_p2": merges,
            "p4_runtime_nonfinite": p4_nonfinite, "p3_operator_unstable": p3_ineligible,
            "p0_top1": p0, "p1_oracle_top1": p1,
            "escalate_to_owner": st == "STATUS_NOT_EMITTED"}


def strip_volatile(obj):
    if isinstance(obj, dict):
        return {k: strip_volatile(v) for k, v in obj.items()
                if k not in ("_wall_s", "cuda_time_ms", "peak_vram_bytes", "wall_s")}
    if isinstance(obj, list):
        return [strip_volatile(v) for v in obj]
    return obj


def main():
    require_cuda()
    torch.cuda.reset_peak_memory_stats()
    t_start = time.perf_counter()
    ev0, ev1 = torch.cuda.Event(True), torch.cuda.Event(True)
    ev0.record()

    audit = math_audit()
    dev_results, held_results = [], []
    for k in K_SETTINGS:
        for wid in DEV_WORLDS:
            dev_results.append(run_world(wid, k))
        for wid in HELDOUT_WORLDS:
            held_results.append(run_world(wid, k))

    ev1.record()
    torch.cuda.synchronize()

    single = [r for r in held_results if r["k_chains"] == 1]
    multi = [r for r in held_results if r["k_chains"] > 1]
    verdict = emit_status(multi, audit)

    def group(rs):
        return {a: {m: sum(r["arms"][a][m] for r in rs) / len(rs)
                    for m in ("top1", "recall_at_5", "cross_chain_contamination")}
                for a in ARMS} if rs else {}

    receipt = {
        "project": "CMB-P0 Multi-Chain Phase Necessity Bench",
        "preregistration": "CMB_P0_PREREGISTRATION.md v0.1 (frozen)",
        "frozen_params": {"N_NODES": N_NODES, "D_CONTENT": D_CONTENT, "L_CHAIN": L_CHAIN,
                          "QUERIES_PER_WORLD": QUERIES_PER_WORLD, "DELTA": DELTA,
                          "GAMMA": GAMMA, "DEPTH": DEPTH, "TOPK": TOPK,
                          "B_COUPLE": B_COUPLE, "EPS_REC": EPS_REC,
                          "KC_PHASE": P.KC_PHASE, "MARGIN": MARGIN,
                          "WIN_FRACTION": WIN_FRACTION},
        "math_audit": audit,
        "SINGLE_CHAIN_heldout": group(single),
        "MULTI_CHAIN_heldout": group(multi),
        "verdict": verdict,
        "dev_worlds": strip_volatile(dev_results),
        "heldout_worlds": strip_volatile(held_results),
        "compute": dict(gpu_identity(),
                        cuda_time_ms=ev0.elapsed_time(ev1),
                        peak_vram_bytes=int(torch.cuda.max_memory_allocated()),
                        host_wall_s=round(time.perf_counter() - t_start, 2)),
        "claim_note": "No resonance-specific or CAS-specific claim is licensed. "
                      "P1_ORACLE_CHAIN_TAG is an upper bound, never a method.",
    }
    payload = json.dumps(strip_volatile({"a": receipt["heldout_worlds"],
                                         "b": receipt["MULTI_CHAIN_heldout"],
                                         "c": receipt["verdict"]}), sort_keys=True)
    receipt["determinism"] = {
        "content_hash": hashlib.sha256(payload.encode()).hexdigest(),
        "note": "hash EXCLUDES cuda_time_ms, peak_vram_bytes and all wall clocks",
    }
    with open("CMB_P0_RECEIPT.json", "w") as f:
        json.dump(receipt, f, indent=1, sort_keys=True)

    print("STATUS:", json.dumps(verdict["status"]))
    print("REASON:", verdict.get("reason"))
    print("MULTI:", json.dumps({a: round(v["top1"], 4)
                                for a, v in receipt["MULTI_CHAIN_heldout"].items()}))
    print("SINGLE:", json.dumps({a: round(v["top1"], 4)
                                 for a, v in receipt["SINGLE_CHAIN_heldout"].items()}))
    print("SPECTRUM: complex_modes=%d/%d rho=%.4f Q=%.4f tau=%.4f" % (
        audit["n_complex_modes"], audit["n_modes_total"], audit["spectral_radius"],
        audit["dominant_oscillatory_mode"]["Q"], audit["pulse_width_tau_waves"]))
    print("HASH:", receipt["determinism"]["content_hash"][:16])
    print("CUDA_MS: %.1f PEAK_VRAM: %d" % (receipt["compute"]["cuda_time_ms"],
                                           receipt["compute"]["peak_vram_bytes"]))


if __name__ == "__main__":
    sys.exit(main())
