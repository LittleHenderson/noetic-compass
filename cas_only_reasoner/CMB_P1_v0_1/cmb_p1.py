"""CMB-P1 -- Phase Separation Repair Bench. Mechanisms.

Frozen design: CMB_P1_PREREGISTRATION.md v0.1.
Authorized by owner ruling 2026-09-02 (R4).

The world construction, propagation primitives and compute-law guards are IMPORTED UNCHANGED
from CMB-P0 (`cmb_p0.py`), so the two benches are directly comparable and the repairs are the
only thing that differs.

GPU only. Fail closed. No CPU fallback branch.
"""
import math
import sys

import torch

_here = __import__("os").path.dirname(__import__("os").path.abspath(__file__))
_p0 = __import__("os").path.join(_here, "..", "CMB_P0_v0_1")
sys.path.insert(0, _p0 if __import__("os").path.isdir(_p0) else _here)
import cmb_p0 as P0                                   # noqa: E402
from cmb_p0 import (DELTA, DEPTH, GAMMA, KC_PHASE, N_NODES, PHASE_SUBSTEPS,  # noqa: E402
                    QUERIES_PER_WORLD, assert_cuda, bounded_topk, build_world, gen,
                    propagate_scalar, require_cuda)

# ---------------------------------------------------------------- frozen parameters

MERGE_RAD = 0.15                   # two chains count as merged within this phase separation
MERGE_FRACTION_MAX = 0.15          # absolute ceiling on merges / C(K,2)
MERGE_VS_P2_SLACK = 0.05           # AND must not exceed P2's merge fraction by more than this
MARGIN = 0.02
CONTAM_MARGIN = 0.05
WIN_FRACTION = 0.70
GATE_HEADROOM_TOP1 = 0.90
GATE_ORACLE_TOP1 = 0.60
CAPACITY_TOP1 = 0.50

PRIMARY_K = (2, 3)                 # owner R3: K=1 sanity, K=4 diagnostic only
SANITY_K = 1
DIAGNOSTIC_K = 4

# P7 signed coupling. beta/s0 are frozen on dev by a SAFETY rule (smallest repulsion that
# clears the merge threshold), never by whichever value maximises top-1.
# The global-threshold form w = tanh(beta*(S - s0)) was BROKEN: reach-similarity on real
# edges is small in absolute terms (same-chain mean 0.145, cross-chain 0.028), so a single
# global s0 made almost every edge repulsive and P7 scored 0.0104 -- below chance, and worse
# than its own shuffled control. A broken repair arm manufactures a false "this repair does
# not work" finding, so the form was replaced rather than the number nudged.
#
# RELATIVE form: judge each edge against THAT NODE'S OWN neighbourhood, so the sign is
# scale-free. A node attracts its most-similar neighbours and repels its least-similar ones.
P7_BETA = 10.0
# Frozen at the CONVERGED budget (200 substeps), not the flattering one. Freezing on a
# transient is the error this project refused to make in CMB-P0, and the same standard
# applies here. Registered rule: the SMALLEST repulsion clearing merge_fraction <= 0.15 while
# staying above P0. Measured at 200 substeps:
#   qtl 0.60 -> mfrac 0.465/0.352  accuracy +0.164/+0.305   merging FAILS
#   qtl 0.70 -> mfrac 0.234/0.249  accuracy +0.223/+0.250   merging FAILS
#   qtl 0.80 -> mfrac 0.188/0.109  accuracy +0.102/+0.016   CLOSEST -- K=2 merging and
#                                                           K=3 accuracy both narrowly miss
#   qtl 0.90 -> mfrac 0.027/0.076  accuracy -0.203/-0.223   accuracy COLLAPSES
# NO SETTING PASSES BOTH. The trade is monotone with no window. P7 is registered at its
# closest setting so the bench reports that failure honestly rather than hiding it behind a
# value that is merely broken.
P7_QUANTILE = 0.80
P7_REACH_DEPTH = 2                 # reach-cosine separates same/cross chain at AUC ~0.87

# P8 frequency heterogeneity. OMEGA frozen on dev by the same safety rule.
# Frozen at the converged budget by the same rule. Measured at 200 substeps:
#   omega 0.40 -> mfrac 0.309/0.328  FAILS
#   omega 0.80 -> mfrac 0.148/0.116  accuracy +0.063/+0.129  PASSES  <- smallest that passes
#   omega 1.60 -> mfrac 0.070/0.069  accuracy -0.051/+0.113  K=2 accuracy fails
P8_OMEGA = 0.80
P8_SPECTRAL_INDEX = 2              # which low Laplacian eigenvector supplies the coordinate

# P2 content upgrade: the CMB-P0 preregistration always specified "link graph + content";
# the implementation used only the link graph, handicapping the tag arm against its own spec.
P2_CONTENT_WEIGHT = 0.50

# Phase-free baselines. Registered because a design panel warned -- and my own measurement
# confirmed -- that a one-line structural gate can beat the oscillator. Without these a
# "phase wins" verdict is uninterpretable: it might just be reading the world's wiring.
#     score_j = a_scalar_j * clamp_min(sign(sim[cue, j] - s0), 0)
B_GATE_REACH_S0 = 0.05
B_GATE_CONTENT_S0 = 0.30


# ---------------------------------------------------------------- structural quantities


def reach_similarity(world, depth=P7_REACH_DEPTH):
    """Cosine between propagated reach vectors, for ALL nodes. Structural, label-free."""
    eye = torch.eye(N_NODES, device=P0.DEV, dtype=P0.DT)
    r = propagate_scalar(eye, world["W"], depth=depth)
    r = r / r.norm(dim=1, keepdim=True).clamp_min(1e-12)
    return assert_cuda(r @ r.T, "reach_similarity")


def spectral_coordinate(world, index=P8_SPECTRAL_INDEX):
    """A low eigenvector of the normalised Laplacian -- a SMOOTH structural coordinate.

    Smoothness is the whole point: nearby nodes get similar values, so a chain can still lock
    internally, while distinct chains land at different frequencies. It is not the gold label
    and it is not the inferred cluster.
    """
    A, deg = world["A"], world["deg"]
    dm = deg.rsqrt()
    S = dm.unsqueeze(1) * A * dm.unsqueeze(0)
    S = 0.5 * (S + S.T)
    _, V = torch.linalg.eigh(S)
    v = V[:, -index]
    return assert_cuda(v / v.abs().amax().clamp_min(1e-12), "spectral_coordinate")


def omega_field(world, kind):
    """P8's natural-frequency field. SPECTRAL is the arm; the others are its controls."""
    v = spectral_coordinate(world)
    if kind == "ZERO":
        return torch.zeros_like(v)
    if kind == "SPECTRAL":
        return P8_OMEGA * v
    if kind == "OMEGA_SHUFFLED":            # same value distribution, structure destroyed
        p = torch.randperm(N_NODES, generator=gen(world["key"] + "|omshuf"), device=P0.DEV)
        return P8_OMEGA * v[p]
    if kind == "OMEGA_RANDOM":              # matched spread, no structure at all
        r = torch.rand(N_NODES, generator=gen(world["key"] + "|omrand"),
                       device=P0.DEV, dtype=P0.DT) * 2 - 1
        return P8_OMEGA * r * (v.std() / r.std().clamp_min(1e-12))
    raise ValueError(kind)


def signed_coupling(world, beta=None, quantile=None):
    """P7: attract where the structure says 'same chain', repel where it says 'different'.

        w_ij = tanh( beta * (S_ij - ref_i) ),   ref_i = quantile of S over node i's OWN edges

    Raw adjacency carries NO same/cross-chain signal here (measured AUC 0.4956/0.5214/0.5240)
    because the cross-chain links are deliberately strong, so the sign must come from
    second-order structure -- which does carry it (reach cosine AUC ~0.87).
    """
    beta = P7_BETA if beta is None else beta
    quantile = P7_QUANTILE if quantile is None else quantile
    S = reach_similarity(world)
    A = world["A"]
    masked = torch.where(A > 0, S, torch.full_like(S, float("nan")))
    ref = torch.nan_to_num(torch.nanquantile(masked, quantile, dim=1, keepdim=True), nan=0.0)
    return assert_cuda(A * torch.tanh(beta * (S - ref)), "signed_coupling")


# ---------------------------------------------------------------- phase dynamics


def run_phase(world, q, coupling=None, omega=None, keep_trajectory=True):
    """One phase run. Returns (final amplitude, full phase trajectory).

    `coupling` defaults to the plain link graph (P4/P8 behaviour); P7 passes the signed
    matrix. `omega` defaults to zero (P4/P7); P8 passes its frequency field.
    """
    A = world["A"] if coupling is None else coupling
    deg, W = world["deg"], world["W"]
    om = torch.zeros(N_NODES, device=P0.DEV, dtype=P0.DT) if omega is None else omega
    th = (torch.rand((QUERIES_PER_WORLD, N_NODES), generator=gen(world["key"] + "|phase0"),
                     device=P0.DEV, dtype=P0.DT) * 2 - 1) * math.pi
    a = q["seeds"]
    TH = []
    for _ in range(DEPTH):
        for _ in range(PHASE_SUBSTEPS):
            S = (a * torch.sin(th)) @ A.T
            C = (a * torch.cos(th)) @ A.T
            th = th + om.unsqueeze(0) + (KC_PHASE / deg.unsqueeze(0)) * (
                torch.cos(th) * S - torch.sin(th) * C)
            if keep_trajectory:
                TH.append(torch.remainder(th + math.pi, 2 * math.pi) - math.pi)
        a = bounded_topk((1.0 - DELTA) * a + GAMMA * (a @ W.T))
    th = torch.remainder(th + math.pi, 2 * math.pi) - math.pi
    return assert_cuda(a, "run_phase.a"), (torch.stack(TH) if keep_trajectory
                                           else th.unsqueeze(0))


def run_phase_acc(world, q, coupling=None, omega=None, substeps=None):
    """Phase run with O(1) memory: accumulates the running means the readouts need instead of
    storing the whole trajectory.

    Storing frames costs ~327 MB at 200 substeps, so the convergence check the design panel
    demanded would not fit alongside several arms. This returns everything both readouts use:
      a          final amplitude
      th_end     final phase field (the endpoint readout)
      coh_mean   time-mean of cos(theta_j - theta_cue)          (the trajectory readout)
      pair_mean  time-mean of cos(psi_A - psi_B) per chain pair (trajectory merge fraction)
    """
    A = world["A"] if coupling is None else coupling
    deg, W = world["deg"], world["W"]
    nsub = PHASE_SUBSTEPS if substeps is None else substeps
    om = torch.zeros(N_NODES, device=P0.DEV, dtype=P0.DT) if omega is None else omega
    th = (torch.rand((QUERIES_PER_WORLD, N_NODES), generator=gen(world["key"] + "|phase0"),
                     device=P0.DEV, dtype=P0.DT) * 2 - 1) * math.pi
    a = q["seeds"]
    ar = torch.arange(QUERIES_PER_WORLD, device=P0.DEV)
    memb = world["memb"].unsqueeze(0) * q["active_mask"].unsqueeze(-1).to(P0.DT)
    cnt = memb.sum(dim=2).clamp_min(1e-12)
    coh_sum = torch.zeros((QUERIES_PER_WORLD, N_NODES), device=P0.DEV, dtype=P0.DT)
    pair_sum = torch.zeros((QUERIES_PER_WORLD, world["pool"], world["pool"]),
                           device=P0.DEV, dtype=P0.DT)
    n = 0
    for _ in range(DEPTH):
        for _ in range(nsub):
            S = (a * torch.sin(th)) @ A.T
            C = (a * torch.cos(th)) @ A.T
            th = th + om.unsqueeze(0) + (KC_PHASE / deg.unsqueeze(0)) * (
                torch.cos(th) * S - torch.sin(th) * C)
            thw = torch.remainder(th + math.pi, 2 * math.pi) - math.pi
            coh_sum += torch.cos(thw - thw[ar, q["cue"]].unsqueeze(1))
            z = torch.exp(1j * thw.to(torch.complex128)).unsqueeze(1)
            ang = ((z * memb.to(torch.complex128)).sum(2) / cnt).angle()
            pair_sum += torch.cos(ang.unsqueeze(2) - ang.unsqueeze(1))
            n += 1
        a = bounded_topk((1.0 - DELTA) * a + GAMMA * (a @ W.T))
    thw = torch.remainder(th + math.pi, 2 * math.pi) - math.pi
    return (assert_cuda(a, "run_phase_acc.a"), thw, coh_sum / n, pair_sum / n)


def merge_fraction_from_pairs(pair_coh, q, world):
    """Merged chain pairs / C(K,2) from an already-computed pairwise coherence matrix."""
    pair = q["active_mask"].unsqueeze(2) & q["active_mask"].unsqueeze(1)
    pair = pair & ~torch.eye(world["pool"], dtype=torch.bool, device=P0.DEV).unsqueeze(0)
    merged = ((pair_coh > math.cos(MERGE_RAD)) & pair).sum().double() / (2.0 * QUERIES_PER_WORLD)
    k = world["k_chains"]
    return float((merged / max(1.0, k * (k - 1) / 2.0)).item()), float(merged.item())


def endpoint_pair_coherence(th_end, q, world):
    memb = world["memb"].unsqueeze(0) * q["active_mask"].unsqueeze(-1).to(P0.DT)
    z = torch.exp(1j * th_end.to(torch.complex128)).unsqueeze(1)
    ang = ((z * memb.to(torch.complex128)).sum(2) / memb.sum(2).clamp_min(1e-12)).angle()
    return torch.cos(ang.unsqueeze(2) - ang.unsqueeze(1))


def phase_readout(TH, a, q, world, mode, shuffle=False):
    """Score nodes by phase coherence with the cue.

    mode 'endpoint'   -- the last frame only (CMB-P0's readout)
    mode 'trajectory' -- the unweighted mean over the whole history (P9). No free parameter.

    `shuffle` destroys phase-to-node correspondence but keeps the CUE'S OWN phase as the
    reference, so the control isolates chain structure instead of destroying its own baseline
    (the defect repaired in CMB-P0's P5).
    """
    T = TH if mode == "trajectory" else TH[-1:]
    ref = TH[-1:] if mode != "trajectory" else TH
    if shuffle:
        perm = torch.randperm(N_NODES, generator=gen(world["key"] + "|readshuf"), device=P0.DEV)
        T = T[:, :, perm]
    cue = ref.gather(2, q["cue"].view(1, -1, 1).expand(ref.shape[0], -1, 1))
    coh = torch.cos(T - cue).mean(0)
    return assert_cuda(a * coh.clamp_min(0.0), "phase_readout")


def merge_fraction(TH, q, world, mode):
    """The owner's normalised metric: merged chain pairs / C(K,2).

    Computed from the SAME phase evidence the arm reads -- endpoint arms from the endpoint,
    trajectory arms from the trajectory -- because an arm's chain grouping is whatever its own
    readout implies. The endpoint value is also reported separately for every arm so both
    views are visible and neither can hide behind the other.
    """
    T = TH if mode == "trajectory" else TH[-1:]
    memb = world["memb"].unsqueeze(0) * q["active_mask"].unsqueeze(-1).to(P0.DT)
    cnt = memb.sum(dim=2)
    z = torch.exp(1j * T.to(torch.complex128))
    ctr = (z.unsqueeze(2) * memb.to(torch.complex128).unsqueeze(0)).sum(3) / \
        cnt.clamp_min(1e-12).unsqueeze(0)
    ang = ctr.angle()
    coh = torch.cos(ang.unsqueeze(3) - ang.unsqueeze(2)).mean(0)      # (Q, pool, pool)
    pair = q["active_mask"].unsqueeze(2) & q["active_mask"].unsqueeze(1)
    pair = pair & ~torch.eye(world["pool"], dtype=torch.bool, device=P0.DEV).unsqueeze(0)
    merged = ((coh > math.cos(MERGE_RAD)) & pair).sum().double() / (2.0 * QUERIES_PER_WORLD)
    k = world["k_chains"]
    denom = max(1.0, k * (k - 1) / 2.0)
    return float((merged / denom).item()), float(merged.item())


def global_order(TH, a, q):
    """Does the arm actually stop synchronising, or merely stop depending on it?"""
    z = (a.to(torch.complex128) * torch.exp(1j * TH[-1].to(torch.complex128))).sum(1)
    return float((z.abs() / a.sum(1).clamp_min(1e-12)).clamp(0, 1).mean().item())


# ---------------------------------------------------------------- P2 content upgrade


def infer_clusters_v2(world):
    """P2's grouping, now using the link graph AND content -- as the spec always said.

    Content is the strongest single same/cross-chain signal available (AUC up to 0.8964) and
    the CMB-P0 implementation ignored it, handicapping the tag arm against its own
    specification. Strengthening a competitor is the conservative direction.
    """
    nodes = (world["memb"].sum(dim=0) > 0).nonzero(as_tuple=True)[0]
    delta = torch.zeros((nodes.numel(), N_NODES), device=P0.DEV, dtype=P0.DT)
    delta[torch.arange(nodes.numel(), device=P0.DEV), nodes] = 1.0
    reach = propagate_scalar(delta, world["W"], depth=P7_REACH_DEPTH)
    reach = reach / reach.norm(dim=1, keepdim=True).clamp_min(1e-12)
    c = world["content"][nodes]
    aff = (1.0 - P2_CONTENT_WEIGHT) * (reach @ reach.T) + P2_CONTENT_WEIGHT * (c @ c.T)
    lab = P0.agglomerate(aff, world["pool"])
    cluster = torch.full((N_NODES,), -1, dtype=torch.long, device=P0.DEV)
    cluster[nodes] = lab
    return assert_cuda(cluster, "infer_clusters_v2")


# ---------------------------------------------------------------- world repair


def build_world_p1(world_id, k_chains):
    """CMB-P0's world, with a CONTENT LEAK repaired.

    DEFECT FOUND PRE-LAUNCH (2026-09-02), by verifying a design-panel warning:
    `build_world` adds a per-chain "flavour" vector to EVERY node of a chain -- including
    that chain's completion -- so a completion carried its own chain's content signature.
    Measured on dev worlds: cosine(cue_t, gold_t) = 0.3901 / 0.3485 / 0.3429 at K=2/3/4
    versus 0.1280 / 0.1131 / 0.1017 for rival completions, and a one-line content threshold
    picked the gold 25/36, 25/42, 26/48 times -- roughly 54-69%.

    That makes the CMB-P0 preregistration's claim "chain identity appears in NO node feature"
    FALSE. No CMB-P0 arm read content directly, so its measured comparisons stand; but a
    content-reading arm would have beaten every one of them for the wrong reason -- and the
    P2 content upgrade planned for CMB-P1 would have done exactly that.

    Repair: every completion is given the SAME content (the pool-mean flavour plus the shared
    cue direction), so completions are content-indistinguishable from one another and content
    can no longer say which completion belongs to which cue. Nothing else is touched, so the
    two benches remain comparable on every other axis.
    """
    w = build_world(world_id, k_chains)
    comps = w["completions"]
    shared = w["content"][comps].mean(dim=0, keepdim=True)
    w["content"] = w["content"].clone()
    w["content"][comps] = shared.expand(comps.numel(), -1)
    w["content"] = w["content"] / w["content"].norm(dim=1, keepdim=True).clamp_min(1e-12)
    return w
