"""CMB-P0 -- Multi-Chain Phase Necessity Bench.

Frozen design: CMB_P0_PREREGISTRATION.md v0.1. Read it before changing anything here.

Compute law (owner, 2026-09-01): no experimental workload on local CPU; one remote AWS GPU
instance; ALL substantive numerical operations on CUDA; fail closed on silent CPU fallback.
Every arm asserts device type at its boundary and raises GPU_REQUIRED otherwise. There is no
CPU fallback branch in this file -- by construction, not by policy.

Determinism: float64 throughout, TF32 disabled, seeds derived by SHA-256 from string keys.
Volatile fields (cuda_time_ms, peak_vram_bytes, wall_s) are EXCLUDED from the determinism
hash -- the exact defect found in RGM-0.1's raw two-pass hash.
"""
import hashlib
import json
import math
import time

import torch

# ---------------------------------------------------------------- frozen parameters

N_NODES = 800
D_CONTENT = 32
L_CHAIN = 6
QUERIES_PER_WORLD = 64
K_SETTINGS = (1, 2, 3, 4)          # K=1 is the SINGLE_CHAIN group; 2,3,4 are MULTI_CHAIN
DEV_WORLDS = tuple(range(0, 6))
HELDOUT_WORLDS = tuple(range(6, 26))

DELTA = 0.30                       # damping
GAMMA = 0.50                       # coupling
DEPTH = 4                          # propagation waves
TOPK = 5                           # recall@k and contamination budget
# Two-state parameters, FROZEN ON DEV by analytic stability, not by trial on results.
# For any row-normalised W, mu(W) lies in [-1,1]. Sweeping mu over that whole interval:
#   b=0.80, eps=0.25  ->  rho = 1.0488   UNSTABLE (state grows; Q undefined, alpha < 0)
#   b=0.60, eps=0.70  ->  rho = 0.8832   margin 0.1168, Q = 2.239, period 11.29 waves
# The chosen pair is stable for EVERY graph this bench can build, so the freeze is
# graph-independent rather than fitted to any world. delta and gamma are NOT touched --
# they stay at the RGM engine's values so the comparison to the current engine is honest.
B_COUPLE = 0.60                    # two-state: a <- -b*r
EPS_REC = 0.70                     # two-state: recovery rate
KC_PHASE = 1.20                    # Kuramoto coupling strength
MARGIN = 0.02                      # status-law margin on top-1
WIN_FRACTION = 0.70                # a win must hold in >=70% of held-out multi-chain worlds
GATE_HEADROOM_TOP1 = 0.90          # P0 above this => no gap to measure
GATE_ORACLE_TOP1 = 0.60            # P1 below this => task ill-posed / instrument broken

ARMS = ("P0_SCALAR", "P1_ORACLE_CHAIN_TAG", "P2_INFERRED_CHAIN_TAG",
        "P3_GENERIC_TWO_STATE", "P4_PHASE_OSCILLATOR", "P5_PHASE_SHUFFLED")

DEV = None                         # set by require_cuda()
DT = torch.float64


# ---------------------------------------------------------------- compute law

class GpuRequired(RuntimeError):
    pass


def require_cuda():
    """Fail closed. No CPU fallback exists anywhere in this module."""
    global DEV
    if not torch.cuda.is_available():
        raise GpuRequired("GPU_REQUIRED: torch.cuda.is_available() is False. "
                          "CMB-P0 does not run on CPU. No fallback branch exists.")
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    DEV = torch.device("cuda:0")
    return DEV


def assert_cuda(t, where):
    if not isinstance(t, torch.Tensor):
        raise GpuRequired(f"GPU_REQUIRED: {where} is not a tensor ({type(t).__name__}).")
    if t.device.type != "cuda":
        raise GpuRequired(f"GPU_REQUIRED: {where} is on '{t.device.type}', not cuda. "
                          "Silent CPU fallback detected; aborting.")
    return t


def gpu_identity():
    i = torch.cuda.current_device()
    p = torch.cuda.get_device_properties(i)
    return {
        "gpu_name": torch.cuda.get_device_name(i),
        "gpu_uuid": str(getattr(p, "uuid", "unavailable")),
        "gpu_total_mem_bytes": int(p.total_memory),
        "gpu_capability": f"{p.major}.{p.minor}",
        "torch_version": torch.__version__,
        "cuda_runtime": torch.version.cuda,
        "cudnn_version": torch.backends.cudnn.version(),
        "tf32_matmul_allowed": bool(torch.backends.cuda.matmul.allow_tf32),
        "dtype": str(DT),
    }


# ---------------------------------------------------------------- deterministic seeding

def hseed(key: str) -> int:
    return int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "big") % (2 ** 63 - 1)


def gen(key: str) -> torch.Generator:
    g = torch.Generator(device=DEV)
    g.manual_seed(hseed(key))
    return g


# ---------------------------------------------------------------- world construction


def build_world(world_id: int, k_chains: int):
    """One independently seeded world. See preregistration section 3.

    Adversarial by construction: simultaneous chains, shared intermediate nodes,
    misleading cross-chain links, content-similar distractors, and gold/distractor pairs
    whose static profiles are permutations of one another. Chain identity appears in NO
    node feature -- only in `chain_of`, which is handed to P1_ORACLE alone.
    """
    key = f"CMBP0|w{world_id}|k{k_chains}"
    g = gen(key)

    # -- chain membership. Chains are disjoint paths EXCEPT for deliberately shared
    #    intermediates, which are what make the separation problem real.
    perm = torch.randperm(N_NODES, generator=g, device=DEV)
    chains = []
    cursor = 0
    for _ in range(k_chains):
        chains.append(perm[cursor:cursor + L_CHAIN].clone())
        cursor += L_CHAIN

    shared = []
    if k_chains >= 2:
        # every pair of chains shares one intermediate node (position 2)
        for a in range(k_chains - 1):
            node = chains[a][2].item()
            chains[a + 1][2] = node
            shared.append(node)

    chain_of = torch.full((N_NODES,), -1, dtype=torch.long, device=DEV)
    for ci, c in enumerate(chains):
        chain_of[c] = ci
    for node in shared:                       # shared nodes belong to no single chain
        chain_of[node] = -2

    # -- content embeddings; each chain's nodes share a weak chain-flavoured direction,
    #    and every chain's COMPLETION is pulled toward every cue, so content similarity
    #    cannot separate the completions.
    content = torch.randn((N_NODES, D_CONTENT), generator=g, device=DEV, dtype=DT)
    flavour = torch.randn((k_chains, D_CONTENT), generator=g, device=DEV, dtype=DT)
    for ci, c in enumerate(chains):
        content[c] += 0.60 * flavour[ci]
    completions = torch.stack([c[L_CHAIN - 1] for c in chains])
    cues = torch.stack([c[L_CHAIN - 2] for c in chains])
    common = content[cues].mean(dim=0)
    content[completions] += 0.90 * common     # all completions look alike to the cues
    content = content / content.norm(dim=1, keepdim=True).clamp_min(1e-12)

    # -- static profiles: 4 feature ids per node. The gold completion and each rival
    #    completion carry the SAME MULTISET in a DIFFERENT ORDER, so any order-blind
    #    static readout ties them exactly.
    profiles = torch.randint(0, 12, (N_NODES, 4), generator=g, device=DEV)
    base_profile = profiles[completions[0]].clone()
    for ci in range(k_chains):
        roll = torch.roll(base_profile, shifts=ci + 1)
        profiles[completions[ci]] = roll

    # -- link graph
    A = torch.zeros((N_NODES, N_NODES), device=DEV, dtype=DT)

    def link(u, v, w=1.0):
        A[u, v] = w
        A[v, u] = w

    for c in chains:                                  # intra-chain path edges
        for i in range(L_CHAIN - 1):
            link(c[i].item(), c[i + 1].item(), 1.0)
        for i in range(L_CHAIN - 2):                  # skip edges, so paths are not brittle
            link(c[i].item(), c[i + 2].item(), 0.55)

    # misleading cross-chain links: they connect chains at NON-shared positions and are
    # strong enough to leak activation between chains.
    n_cross = 3 * k_chains
    if k_chains >= 2:
        for t in range(n_cross):
            ca, cb = t % k_chains, (t + 1) % k_chains
            ia = int(torch.randint(0, L_CHAIN - 1, (1,), generator=g, device=DEV).item())
            ib = int(torch.randint(0, L_CHAIN - 1, (1,), generator=g, device=DEV).item())
            link(chains[ca][ia].item(), chains[cb][ib].item(), 0.75)

    # background graph: every node gets a few random edges (distractor mass)
    deg_bg = 6
    src = torch.arange(N_NODES, device=DEV).repeat_interleave(deg_bg)
    dst = torch.randint(0, N_NODES, (N_NODES * deg_bg,), generator=g, device=DEV)
    A[src, dst] = torch.maximum(A[src, dst], torch.full_like(A[src, dst], 0.30))
    A[dst, src] = torch.maximum(A[dst, src], torch.full_like(A[dst, src], 0.30))
    A.fill_diagonal_(0.0)

    # content-similar distractors wired to each cue -- defeats nearest-neighbour retrieval
    sim = content @ content[cues].T                       # (N, k)
    for ci in range(k_chains):
        s = sim[:, ci].clone()
        s[chains[ci]] = -2.0
        top = torch.topk(s, 4).indices
        for d in top.tolist():
            link(cues[ci].item(), d, 0.60)

    deg = A.sum(dim=1).clamp_min(1e-12)
    W = A / deg.unsqueeze(1)                              # W = D^-1 A
    assert_cuda(W, "world.W")

    return {
        "world_id": world_id, "k_chains": k_chains, "key": key,
        "A": A, "W": W, "deg": deg, "content": content, "profiles": profiles,
        "chains": chains, "chain_of": chain_of,
        "completions": completions, "cues": cues, "shared": shared,
    }


def build_queries(world):
    """Q queries per world. Every query activates EVERY chain simultaneously; the cue is a
    NODE, never a chain label. The gold answer is the cued chain's own completion."""
    k = world["k_chains"]
    g = gen(world["key"] + "|queries")
    tgt = torch.randint(0, k, (QUERIES_PER_WORLD,), generator=g, device=DEV)

    seeds = torch.zeros((QUERIES_PER_WORLD, N_NODES), device=DEV, dtype=DT)
    seed_chain = torch.full((QUERIES_PER_WORLD, N_NODES), -1, dtype=torch.long, device=DEV)
    for ci in range(k):
        nodes = world["chains"][ci][: L_CHAIN - 1]        # everything except the completion
        seeds[:, nodes] = 1.0
        seed_chain[:, nodes] = ci
    for node in world["shared"]:
        seed_chain[:, node] = -2

    cue = world["cues"][tgt]                              # (Q,) the node we are "at"
    gold = world["completions"][tgt]                      # (Q,) the answer
    seeds[torch.arange(QUERIES_PER_WORLD, device=DEV), cue] += 1.0   # cue is emphasised
    assert_cuda(seeds, "queries.seeds")
    return {"target": tgt, "seeds": seeds, "seed_chain": seed_chain, "cue": cue, "gold": gold}


# ---------------------------------------------------------------- propagation primitives


def bounded_topk(a, k=48):
    """BoundedTopK: keep the k largest per row, zero the rest, renormalise to unit max."""
    if a.shape[-1] <= k:
        kept = a
    else:
        thresh = torch.topk(a, k, dim=-1).values[..., -1:].detach()
        kept = torch.where(a >= thresh, a, torch.zeros_like(a))
    m = kept.abs().amax(dim=-1, keepdim=True).clamp_min(1e-12)
    return kept / m


def propagate_scalar(a0, W, depth=DEPTH):
    a = a0
    for _ in range(depth):
        a = bounded_topk((1.0 - DELTA) * a + GAMMA * (a @ W.T))
    return a


def propagate_two_state(a0, W, depth=DEPTH):
    """Block operator M = [[(1-d)I + gW, -bI], [eI, (1-e)I]] applied `depth` times."""
    a, r = a0, torch.zeros_like(a0)
    for _ in range(depth):
        a_new = (1.0 - DELTA) * a + GAMMA * (a @ W.T) - B_COUPLE * r
        r_new = EPS_REC * a + (1.0 - EPS_REC) * r
        a, r = bounded_topk(a_new), r_new
    return a, r


def propagate_phase(a0, theta0, A, deg, W, depth=DEPTH):
    """Amplitude as usual; phase by amplitude-weighted Kuramoto coupling on the link graph.

    dtheta_i = (Kc/deg_i) * sum_j A_ij * a_j * sin(theta_j - theta_i)

    No global frequency term is introduced: a single global omega cancels exactly in every
    phase DIFFERENCE, which is all the readout uses. This is the preregistration's
    "frequency is fixed by the registered operator, not a free control".
    """
    a, th = a0, theta0
    for _ in range(depth):
        # sum_j A_ij a_j sin(th_j - th_i) = cos(th_i)*S_i - sin(th_i)*C_i
        S = (a * torch.sin(th)) @ A.T
        C = (a * torch.cos(th)) @ A.T
        coupling = torch.cos(th) * S - torch.sin(th) * C
        th = th + (KC_PHASE / deg.unsqueeze(0)) * coupling
        a = bounded_topk((1.0 - DELTA) * a + GAMMA * (a @ W.T))
    return a, torch.remainder(th + math.pi, 2 * math.pi) - math.pi


# ---------------------------------------------------------------- chain inference


def infer_clusters(world, q, k):
    """Group the active seed nodes into k clusters WITHOUT the gold labels.

    Each distinct seed node is propagated alone; seeds whose reach vectors align are judged
    to belong to the same chain. Average-linkage agglomeration, deterministic.
    Returns (node_ids, cluster_of_node) for the seed set.
    """
    nodes = (q["seeds"][0] > 0).nonzero(as_tuple=True)[0]
    delta = torch.zeros((nodes.numel(), N_NODES), device=DEV, dtype=DT)
    delta[torch.arange(nodes.numel(), device=DEV), nodes] = 1.0
    reach = propagate_scalar(delta, world["W"])
    assert_cuda(reach, "infer_clusters.reach")
    r = reach / reach.norm(dim=1, keepdim=True).clamp_min(1e-12)
    aff = (r @ r.T).cpu()                       # small (|seeds| x |seeds|) linkage on host

    groups = [[i] for i in range(nodes.numel())]
    while len(groups) > k:
        best, bi, bj = -1e18, 0, 1
        for i in range(len(groups)):
            for j in range(i + 1, len(groups)):
                v = float(sum(aff[x, y] for x in groups[i] for y in groups[j])
                          / (len(groups[i]) * len(groups[j])))
                if v > best:
                    best, bi, bj = v, i, j
        groups[bi] = groups[bi] + groups[bj]
        groups.pop(bj)

    cluster = torch.full((N_NODES,), -1, dtype=torch.long, device=DEV)
    for gi, grp in enumerate(groups):
        cluster[nodes[torch.tensor(grp, device=DEV)]] = gi
    return nodes, cluster


def cluster_by_phase(theta, nodes, k):
    """k groups on the circle, deterministic: split the sorted phases at the k largest gaps."""
    th = theta[nodes]
    order = torch.argsort(th)
    sth = th[order]
    gaps = sth[1:] - sth[:-1]                       # k groups need k-1 interior cuts
    n_cut = max(0, min(k - 1, gaps.numel()))
    cuts = set(torch.topk(gaps, n_cut).indices.tolist()) if n_cut else set()
    lab = torch.zeros(nodes.numel(), dtype=torch.long, device=DEV)
    cur = 0
    for i in range(sth.numel()):
        lab[order[i]] = cur
        if cur < k - 1 and i in cuts:
            cur += 1
    out = torch.full((N_NODES,), -1, dtype=torch.long, device=DEV)
    out[nodes] = lab
    return out
