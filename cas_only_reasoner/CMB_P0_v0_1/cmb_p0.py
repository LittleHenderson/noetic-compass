"""CMB-P0 -- Multi-Chain Phase Necessity Bench. HARNESS v0.2.

Frozen design: CMB_P0_PREREGISTRATION.md v0.1 + AMENDMENT A1 + AMENDMENT A2.
Read A2 before changing anything here: v0.1 of this harness was STOPPED PRE-LAUNCH by its
own adversarial review, with three defects confirmed by measurement:

  C1  the gold answer was the unique non-seed weight-1.0 neighbour of the cue, so
      `argmax_j A[cue,j]` returned it in 1152/1152 dev queries. One edge weight solved the
      bench. It measured one-hop adjacency, not chain separation.
  C2  the 64 "queries" per world were only k DISTINCT queries (measured: 2/64, 3/64, 4/64),
      replicated 16-32x. Deterministic arms could only take k+1 accuracy values.
  C5  channel arms received k x the top-k budget and per-channel renormalisation, so
      "tags beat phase" partly measured "more channels".

Compute law (owner): one remote AWS GPU instance; ALL substantive numerical operations on
CUDA; fail closed on silent CPU fallback. Clustering is done on-device (v0.1 ran it in a
host Python loop, which was an arm's decisive computation running on CPU).

Determinism: float64, TF32 disabled, SHA-256 seeding. Volatile fields are excluded from the
determinism hash.
"""
import hashlib
import math
import os

import torch

# ---------------------------------------------------------------- frozen parameters

N_NODES = 800
D_CONTENT = 32
L_CHAIN = 6
POOL_EXTRA = 4                     # chains built per world BEYOND the k active ones
QUERIES_PER_WORLD = 64
K_SETTINGS = (1, 2, 3, 4)          # K=1 is SINGLE_CHAIN (sanity); 2,3,4 are MULTI_CHAIN
DEV_WORLDS = tuple(range(0, 6))
HELDOUT_WORLDS = tuple(range(6, 26))

DELTA = 0.30                       # damping        (RGM engine value, not retuned)
GAMMA = 0.50                       # coupling       (RGM engine value, not retuned)
DEPTH = 4                          # propagation waves
TOPK = 5                           # recall@k and contamination budget
TOPK_KEEP = 48                     # BoundedTopK survivors per query, SHARED across arms

# Two-state parameters. Stability is settled analytically over mu(W) in [-1,1], which
# covers every graph this bench can build, so that part of the freeze is graph-independent.
# Among the stable-and-oscillatory settings, the one chosen is the one that makes P3 -- the
# CAPACITY CONTROL -- as STRONG as possible on dev. That direction is deliberate: P3 is a
# competitor to the phase hypothesis, so strengthening it makes a phase win harder, never
# easier. Tuning P4 up would be the biased direction and is not done.
#   b=0.80, eps=0.25 -> rho 1.0488  UNSTABLE (grows; Q undefined, alpha < 0)
#   b=0.60, eps=0.70 -> rho 0.8832  stable but P3 top1 = 0.000 -- the oscillation scrambles
#                                   retrieval outright; a control scoring below chance would
#                                   have guaranteed "P4 beats P3"
#   b=0.40, eps=0.60 -> rho 0.8485  P3 top1 0.328
#   b=0.30, eps=0.50 -> rho 0.8660  P3 top1 0.346   <- CHOSEN
#   b=0.20, eps=0.40 -> rho 1.0000  marginal, rejected
B_COUPLE = 0.30
EPS_REC = 0.50

# Propagation depth used to build the reach vectors that P2 clusters on. Swept on dev:
# depth 1/2/3/4 -> purity 0.781 / 0.787 / 0.752 / 0.724. Chosen to maximise P2's accuracy,
# again the conservative direction (P2 competes with P4).
REACH_DEPTH = 2

KC_PHASE = 1.20                    # Kuramoto coupling strength
# Phase updates per amplitude wave. FROZEN AT A CONVERGED VALUE, deliberately.
# Dev sweep (worlds 0-5, k=2,3,4): within-chain order / cross-chain separation / P4 top1
#     4x1  -> 0.6418 / 1.0795 / 0.567     not locked
#     4x4  -> 0.9418 / 0.4537 / 0.755     TRANSIENT -- best for P4
#     4x10 -> 0.9995 / 0.0618 / 0.710     converged
#    20x10 -> 1.0000 / 0.0000 / 0.470     fully globally synchronised
# Freezing at the 4x4 transient would be choosing the stopping time that flatters the
# hypothesis. A stopping time is not a mechanism. Frozen at the converged value.
PHASE_SUBSTEPS = 10

MARGIN = 0.02                      # top-1 margin for a win
MERGE_MARGIN = 0.50                # SEPARATE threshold, in MERGE COUNTS (not a fraction)
CONTAM_MARGIN = 0.05               # contamination is quantised in steps of 1/TOPK = 0.2
WIN_FRACTION = 0.70                # a win must hold in >=70% of worlds WITHIN EACH K
GATE_HEADROOM_TOP1 = 0.90
GATE_ORACLE_TOP1 = 0.60
CAPACITY_TOP1 = 0.50               # simultaneous_chain_capacity threshold

ARMS = ("P0_SCALAR", "P1_ORACLE_CHAIN_TAG", "P2_INFERRED_CHAIN_TAG",
        "P3_GENERIC_TWO_STATE", "P4_PHASE_OSCILLATOR", "P5_PHASE_SHUFFLED",
        "P6_SCALAR_TWO_CHANNEL")

DEV = None
DT = torch.float64


# ---------------------------------------------------------------- compute law

class GpuRequired(RuntimeError):
    pass


def require_cuda():
    """Fail closed. No CPU fallback branch exists anywhere in this module."""
    global DEV
    if not torch.cuda.is_available():
        raise GpuRequired("GPU_REQUIRED: torch.cuda.is_available() is False. "
                          "CMB-P0 does not run on CPU. No fallback branch exists.")
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    # House standard, already used by cjt_gate1a_static_neural_v1/exec/train_loop.py and
    # its bootstrap.sh. Omitting it here would be a regression against our own practice.
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    torch.use_deterministic_algorithms(True, warn_only=True)
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
    if DEV is None:
        raise GpuRequired("GPU_REQUIRED: gen() called before require_cuda(); "
                          "torch.Generator(device=None) would silently be a CPU generator.")
    g = torch.Generator(device=DEV)
    g.manual_seed(hseed(key))
    return g


# ---------------------------------------------------------------- world construction


def build_world(world_id: int, k_chains: int):
    """One independently seeded world.

    A POOL of `k_chains + POOL_EXTRA` chains is wired into the graph. Each query activates a
    RANDOM SUBSET of size k_chains and picks a target within it -- this is the C2 repair:
    v0.1 seeded every chain in every query, so all queries with the same target were
    byte-identical and there were only k distinct queries per world.

    Chain identity appears in NO node feature. It is handed to P1_ORACLE alone.
    """
    key = f"CMBP0v2|w{world_id}|k{k_chains}"
    g = gen(key)
    pool = k_chains + POOL_EXTRA

    perm = torch.randperm(N_NODES, generator=g, device=DEV)
    chains = [perm[i * L_CHAIN:(i + 1) * L_CHAIN].clone() for i in range(pool)]

    # Each ADJACENT PAIR shares a DISTINCT intermediate node. v0.1 donated from a position
    # it had already overwritten, so every chain shared the same single node.
    shared = []
    for a in range(pool - 1):
        pos = 1 + (a % 3)
        node = chains[a][pos].item()
        chains[a + 1][pos] = node
        shared.append(node)

    chain_of = torch.full((N_NODES,), -1, dtype=torch.long, device=DEV)
    for ci, c in enumerate(chains):
        chain_of[c] = ci
    for node in shared:
        chain_of[node] = -2                            # ambiguous: belongs to no one chain

    completions = torch.stack([c[L_CHAIN - 1] for c in chains])
    cues = torch.stack([c[L_CHAIN - 2] for c in chains])

    content = torch.randn((N_NODES, D_CONTENT), generator=g, device=DEV, dtype=DT)
    flavour = torch.randn((pool, D_CONTENT), generator=g, device=DEV, dtype=DT)
    for ci, c in enumerate(chains):
        content[c] += 0.60 * flavour[ci]
    content[completions] += 0.90 * content[cues].mean(dim=0)
    content = content / content.norm(dim=1, keepdim=True).clamp_min(1e-12)

    # Static profiles: gold and every rival completion carry the SAME MULTISET in a
    # DIFFERENT ORDER, so an order-blind static readout ties them exactly. Measured by the
    # B_STATIC diagnostic baseline in the runner.
    profiles = torch.randint(0, 12, (N_NODES, 4), generator=g, device=DEV)
    base_profile = profiles[completions[0]].clone()
    for ci in range(pool):
        profiles[completions[ci]] = torch.roll(base_profile, shifts=ci + 1)

    A = torch.zeros((N_NODES, N_NODES), device=DEV, dtype=DT)

    def link(u, v, w=1.0):
        # take the MAXIMUM, never overwrite: a later weaker pass must not silently
        # downgrade a stronger edge (that would make the graph order-dependent).
        w = max(w, float(A[u, v].item()))
        A[u, v] = w
        A[v, u] = w

    for c in chains:                                   # intra-chain path, EXCLUDING gold
        for i in range(L_CHAIN - 2):
            link(c[i].item(), c[i + 1].item(), 1.0)
        for i in range(L_CHAIN - 3):
            link(c[i].item(), c[i + 2].item(), 0.55)

    # C1 REPAIR. v0.1 gave the cue a private weight-1.0 edge to its OWN completion and
    # nothing else non-seed came close, so one edge weight identified the gold in
    # 1152/1152 dev queries. Now EVERY cue links to EVERY completion at the SAME weight, so
    # one-hop adjacency is uninformative by construction (re-measured: at chance). A
    # completion is tied to its own chain only through that chain's EARLIER nodes, so the
    # answer is recoverable only by knowing which active seeds belong to the cued chain.
    for ci in range(pool):
        comp = completions[ci].item()
        for cj in range(pool):
            link(cues[cj].item(), comp, 1.0)
        for i in range(L_CHAIN - 2):
            link(chains[ci][i].item(), comp, 0.65)

    for t in range(3 * pool):                          # misleading cross-chain links
        ca, cb = t % pool, (t + 1) % pool
        ia = int(torch.randint(0, L_CHAIN - 1, (1,), generator=g, device=DEV).item())
        ib = int(torch.randint(0, L_CHAIN - 1, (1,), generator=g, device=DEV).item())
        link(chains[ca][ia].item(), chains[cb][ib].item(), 0.75)

    deg_bg = 6                                         # background distractor mass
    src = torch.arange(N_NODES, device=DEV).repeat_interleave(deg_bg)
    dst = torch.randint(0, N_NODES, (N_NODES * deg_bg,), generator=g, device=DEV)
    A[src, dst] = torch.maximum(A[src, dst], torch.full_like(A[src, dst], 0.30))
    A[dst, src] = torch.maximum(A[dst, src], torch.full_like(A[dst, src], 0.30))
    A.fill_diagonal_(0.0)

    sim = content @ content[cues].T                    # content-similar distractors
    for ci in range(pool):
        s = sim[:, ci].clone()
        s[chains[ci]] = -2.0
        for d in torch.topk(s, 4).indices.tolist():
            link(cues[ci].item(), d, 0.60)

    deg = A.sum(dim=1).clamp_min(1e-12)
    W = A / deg.unsqueeze(1)
    assert_cuda(W, "world.W")

    # membership: seed positions (everything except the completion) of each pool chain
    memb = torch.zeros((pool, N_NODES), device=DEV, dtype=DT)
    for ci, c in enumerate(chains):
        memb[ci, c[: L_CHAIN - 1]] = 1.0

    return {"world_id": world_id, "k_chains": k_chains, "pool": pool, "key": key,
            "A": A, "W": W, "deg": deg, "content": content, "profiles": profiles,
            "chains": chains, "chain_of": chain_of, "memb": memb,
            "completions": completions, "cues": cues, "shared": shared}


def build_queries(world):
    """Genuinely distinct queries (the C2 repair).

    Each query activates a RANDOM SUBSET of k chains from the pool and cues one of them.
    v0.1 activated every chain in every query, so the only thing that varied was the cue and
    there were only k distinct queries per world (measured 2/64, 3/64, 4/64).
    """
    k, pool = world["k_chains"], world["pool"]
    g = gen(world["key"] + "|queries|v2")
    Q = QUERIES_PER_WORLD

    active = torch.stack([torch.randperm(pool, generator=g, device=DEV)[:k] for _ in range(Q)])
    slot = torch.randint(0, k, (Q,), generator=g, device=DEV)
    ar = torch.arange(Q, device=DEV)
    target = active[ar, slot]                          # which POOL chain is cued

    seeds = world["memb"][active].sum(dim=1)           # (Q, N) union of active chains
    cue = world["cues"][target]
    gold = world["completions"][target]
    seeds[ar, cue] += 1.0                              # the cue is emphasised
    assert_cuda(seeds, "queries.seeds")

    active_mask = torch.zeros((Q, world["pool"]), dtype=torch.bool, device=DEV)
    active_mask[ar.unsqueeze(1), active] = True
    return {"active": active, "active_mask": active_mask, "target": target,
            "seeds": seeds, "cue": cue, "gold": gold}


# ---------------------------------------------------------------- propagation primitives


def bounded_topk(a, keep=TOPK_KEEP, joint_dims=None):
    """Keep the `keep` largest per query, zero the rest, renormalise.

    `joint_dims` makes the budget and the normalisation SHARED across channels -- the C5
    repair. In v0.1 each of k channels kept its own 48 survivors and normalised by its own
    max, so channel arms silently got k x the budget of the scalar arms.
    """
    if joint_dims is None:
        flat, shape = a, None
    else:
        shape = a.shape
        flat = a.reshape(shape[0], -1)                 # (Q, k*N) -- one shared budget
    if flat.shape[-1] > keep:
        # Select by MAGNITUDE, keep the SIGN. v0.1 selected by value and wrote 0.0 into
        # discarded slots, so whenever kept values went negative -- which is exactly what
        # P3's inhibition term produces -- the discarded zeros outranked every kept node,
        # and the strongest inhibition was the first thing thrown away.
        mag = flat.abs()
        thresh = torch.topk(mag, keep, dim=-1).values[..., -1:]
        flat = torch.where(mag >= thresh, flat, torch.zeros_like(flat))
    m = flat.abs().amax(dim=-1, keepdim=True).clamp_min(1e-12)
    flat = flat / m
    return flat if shape is None else flat.reshape(shape)


def propagate_scalar(a0, W, depth=DEPTH):
    a = a0
    for _ in range(depth):
        a = bounded_topk((1.0 - DELTA) * a + GAMMA * (a @ W.T))
    return a


def propagate_channels(ch, W, depth=DEPTH):
    """(Q, C, N) channels sharing ONE top-k budget and ONE normalisation per query."""
    a = ch
    for _ in range(depth):
        a = bounded_topk((1.0 - DELTA) * a + GAMMA * (a @ W.T), joint_dims=True)
    return a


def propagate_two_state(a0, W, depth=DEPTH):
    """Block operator M = [[(1-d)I + gW, -bI], [eI, (1-e)I]]. Returns BOTH states.

    v0.1 threw `r` away at readout, so P3 had a 1-D readout while P4 had a 2-D one and the
    'same state budget' claim in the preregistration was false. The runner now uses both.
    """
    a, r = a0, torch.zeros_like(a0)
    for _ in range(depth):
        a_new = (1.0 - DELTA) * a + GAMMA * (a @ W.T) - B_COUPLE * r
        r_new = EPS_REC * a + (1.0 - EPS_REC) * r
        a, r = bounded_topk(a_new), r_new
    return a, r


def propagate_phase(a0, theta0, A, deg, W, depth=DEPTH):
    """Amplitude as usual; phase by amplitude-weighted Kuramoto coupling on the link graph.

    dtheta_i = (Kc/deg_i) * sum_j A_ij * a_j * sin(theta_j - theta_i)

    No global frequency term: a single global omega cancels exactly in every phase
    DIFFERENCE, which is all the readout uses. This honours the owner's constraint that
    frequency is fixed by the registered operator, not offered as a free control.
    """
    a, th = a0, theta0
    for _ in range(depth):
        for _ in range(PHASE_SUBSTEPS):
            S = (a * torch.sin(th)) @ A.T
            C = (a * torch.cos(th)) @ A.T
            th = th + (KC_PHASE / deg.unsqueeze(0)) * (torch.cos(th) * S - torch.sin(th) * C)
        a = bounded_topk((1.0 - DELTA) * a + GAMMA * (a @ W.T))
    return a, torch.remainder(th + math.pi, 2 * math.pi) - math.pi


# ---------------------------------------------------------------- chain inference


def agglomerate(aff, n_groups):
    """Average-linkage agglomeration, ON DEVICE.

    v0.1 moved the affinity matrix to the host and ran an O(n^3) Python loop -- that is an
    arm's decisive computation, and the compute law permits host CPU only for orchestration,
    file I/O, hashing, monitoring and shutdown. This runs entirely in torch on CUDA.
    """
    assert_cuda(aff, "agglomerate.aff")
    n = aff.shape[0]
    lab = torch.arange(n, device=DEV)
    size = torch.ones(n, device=DEV, dtype=DT)
    alive = torch.ones(n, dtype=torch.bool, device=DEV)
    tot = aff.clone()                                  # summed affinity between clusters
    tot.fill_diagonal_(-float("inf"))
    for _ in range(max(0, n - n_groups)):
        avg = tot / (size.unsqueeze(1) * size.unsqueeze(0)).clamp_min(1e-12)
        avg = torch.where(alive.unsqueeze(1) & alive.unsqueeze(0), avg,
                          torch.full_like(avg, -float("inf")))
        flat = int(torch.argmax(avg).item())
        i, j = flat // n, flat % n
        if i == j:
            break
        lab = torch.where(lab == j, torch.full_like(lab, i), lab)
        tot[i] = tot[i] + tot[j]
        tot[:, i] = tot[:, i] + tot[:, j]
        size[i] = size[i] + size[j]
        alive[j] = False
        tot[i, i] = -float("inf")
    uniq = torch.unique(lab[alive] if alive.any() else lab)
    remap = torch.full((n,), -1, dtype=torch.long, device=DEV)
    for gi, u in enumerate(uniq.tolist()):
        remap[u] = gi
    return remap[lab]


def infer_clusters(world):
    """Group every pool seed node into `pool` chain-like groups, WITHOUT the gold labels.

    Query-independent: each seed node is propagated alone and nodes whose reach vectors
    align are judged to be on the same chain. Structure only -- no chain identity is used.
    """
    nodes = (world["memb"].sum(dim=0) > 0).nonzero(as_tuple=True)[0]
    delta = torch.zeros((nodes.numel(), N_NODES), device=DEV, dtype=DT)
    delta[torch.arange(nodes.numel(), device=DEV), nodes] = 1.0
    reach = propagate_scalar(delta, world["W"], depth=REACH_DEPTH)
    assert_cuda(reach, "infer_clusters.reach")
    r = reach / reach.norm(dim=1, keepdim=True).clamp_min(1e-12)
    lab = agglomerate(r @ r.T, world["pool"])
    cluster = torch.full((N_NODES,), -1, dtype=torch.long, device=DEV)
    cluster[nodes] = lab
    return cluster


def phase_assignment(th, world, q):
    """Circular chain-assignment accuracy and false merges, for ANY phase field.

    Computed for P4 AND P5 (v0.1 computed it for P4 only, from a single query, using a
    gap-cutting rule that ignored the circle and split any chain synchronised near +/-pi).
    """
    Q, pool = th.shape[0], world["pool"]
    memb = world["memb"].unsqueeze(0) * q["active_mask"].unsqueeze(-1).to(DT)  # (Q,pool,N)
    z = torch.exp(1j * th.to(torch.complex128)).unsqueeze(1)                   # (Q,1,N)
    cnt = memb.sum(dim=2).clamp_min(1e-12)
    centre = (z * memb.to(torch.complex128)).sum(dim=2) / cnt                  # (Q,pool)
    ang = centre.angle()                                                       # (Q,pool)
    align = torch.cos(th.unsqueeze(1) - ang.unsqueeze(-1))                     # (Q,pool,N)
    align = torch.where(q["active_mask"].unsqueeze(-1), align,
                        torch.full_like(align, -2.0))
    best = align.argmax(dim=1)                                                 # (Q,N)
    own = memb.argmax(dim=1)
    valid = memb.sum(dim=1) > 0
    acc = ((best == own) & valid).sum().double() / valid.sum().clamp_min(1).double()

    sep = (ang.unsqueeze(2) - ang.unsqueeze(1)).abs()
    sep = torch.minimum(sep, 2 * math.pi - sep)
    pair = q["active_mask"].unsqueeze(2) & q["active_mask"].unsqueeze(1)
    pair = pair & ~torch.eye(pool, dtype=torch.bool, device=DEV).unsqueeze(0)
    merges = ((sep < 0.15) & pair).sum().double() / (2.0 * Q)
    return float(acc.item()), float(merges.item())
