"""CMB-RP0 -- selective replay and catastrophic forgetting (owner items 5 and 6).

Frozen design: CMB_RP0_PREREGISTRATION.md v0.1 + A1 + A2 + A3.
Builder: Claude. Auditor: a different model. Conflict of interest declared in prereg section 0.

WHAT THIS TESTS. Retrieval is recoverable -- a wrong memory shown to a user can be dismissed.
REPLAY IS NOT: a forgery mixed into a training batch is written into the weights.

WHAT IT DOES NOT TEST.
  * Topic is 100% separable from the semantic vector (480/480) and the trajectory carries NO
    topic information (17/480, chance). So this tests the CMB as a replay SELECTOR and says
    NOTHING about CAS geometry as a feature.  (A1.1)
  * Forgetting here is CLASS-INCREMENTAL: the shared softmax stops naming classes it has not
    seen recently. Task-masked forgetting is ~0.0024 -- the representation is NOT destroyed.
    Claims must say "restores accuracy on earlier classes", never "prevents representational
    forgetting".  (A3.10)
  * Class coverage of the replay set predicts forgetting at rank correlation -0.9017. The
    capability comparison is therefore largely a COVERAGE measurement, and the two-tier
    verifier is not a coverage mechanism.  (A3.10)
  * The capability half is UNDERPOWERED BY CONSTRUCTION: between-world sd ~0.108 against
    registered headroom 0.045. A tie is ABSENCE OF POWER, not evidence of equivalence.  (A3.5)

GPU-only for the neural work, fail closed. Local 4070 is smoke/dev and records no measurement.
"""
import hashlib
import json
import os
import random
import statistics
import sys
import time
import traceback

import torch
import torch.nn as nn

_HERE = os.path.dirname(os.path.abspath(__file__))
for _rel in ("../CMB_R1_v0.1", "../CMB_R1_v0.2"):
    _d = os.path.join(_HERE, _rel)
    sys.path.insert(0, _d if os.path.isdir(_d) else _HERE)
import cmb_r1_core as K                                          # noqa: E402
import cmb_r1_v02_core as V2                                     # noqa: E402

VERSION = "cmb_rp0_v0.2"

# 9 worlds, disjoint from 0-19 and 500-511. Set from MEASUREMENT, not from a guess:
# 146.3 s per world pair on the 4070 (64.4 CLEAN + 81.8 POISONED), x1.4 for the T4 host's
# slower vCPU on Python-bound work = 205 s/world. $0.40 at $0.526/hr = 45.6 min billable.
#     9 worlds -> 35.7 min, $0.313, 4.3 min inside the 40-min in-instance timer
#    10 worlds -> 39.1 min, $0.343, 0.9 min margin -- too tight, any variance overruns
#    12 worlds -> 46.0 min, $0.403 -- OVER the frozen ceiling
# Nine it is. Raw is flushed after every world, so even a timeout preserves what finished.
WORLDS = tuple(range(700, 709))
LEGACY = {20260901 + 1000 * w for w in list(range(0, 20)) + list(range(500, 512))}
SEEDS = (0, 1)              # within-world seed sd 0.007-0.033 vs between-world 0.108 (A3.5)
N_DRAWS = 3                 # replay draws per stochastic arm per world (B4)
# 3, not the reviewer's 5, and the reason is measured rather than asserted. A world pair costs
# 194.2 s at 5 draws, 161.5 s at 3, 130.4 s at 2 on the 4070; times the 1.4x T4 host penalty,
# nine worlds plus boot come to 45.8 / 38.9 / 32.4 min, i.e. $0.401 / $0.341 / $0.284. Five
# draws BREACHES the frozen $0.40 ceiling. Three is defensible on the review's own variance
# decomposition: within-world sd is 0.0066-0.0328 against a between-world sd of 0.108, so
# averaging 3 draws x 2 seeds already puts the within-world residual far below the term that
# actually limits the test. Worlds buy power here; draws do not.
N_TASKS = 3
REPLAY_K = 32
STEPS = 300
BATCH = 64
HIDDEN = 64
LR = 1e-3
MARGIN = 0.02               # provisional; the RUN measures a null and reports both (A3.5)
POISON_MARGIN = 1.0         # forgeries; set BEFORE seeing retention (A3.2)
# OWNER RULING 2026-09-02: promotion requires the mechanism to beat CLASS_BALANCED as well,
# and to preserve the old task and still learn the new one. Floors registered before the run.
PRESERVE_FRAC = 0.80        # acc on task-0 classes at the end, as a fraction of its own peak
LEARN_FLOOR = 0.80          # acc on the FINAL task's classes at the end
REQUIRED_BEAT = ("RANDOM", "SEMANTIC_DIVERSE", "CLASS_BALANCED", "DEGREE_FILTER")
WIN_FRACTION = 0.70         # descriptive only now; the test is a paired permutation (A3.5)
N_PERM = 10000
POISON_PER_PAST_TOPIC = 6
QUERIES_PER = 8

# ID_ORDER is registered permanently: it is the zero-information rule that reproduced the
# "ceiling" exactly before the A3.1 repair (32/32 set overlap at both task steps).
ARMS = ("NO_REPLAY", "ID_ORDER", "RANDOM", "SEMANTIC_DIVERSE", "SEMANTIC_TO_NEW",
        "DEGREE_FILTER", "CMB_AUTHORIZED", "CMB_RETRIEVED",
        "CLASS_BALANCED", "CLASS_BALANCED_POOL")
STOCHASTIC = ("RANDOM", "DEGREE_FILTER")
# CLASS_BALANCED_POOL is mechanism-free (it reads only the label stored on each memory) and
# is the FAIR safety competitor -- see A5.
MECHANISM_FREE = ("ID_ORDER", "RANDOM", "SEMANTIC_DIVERSE", "SEMANTIC_TO_NEW", "DEGREE_FILTER",
                  "CLASS_BALANCED_POOL")
ARM_SEED = {a: i for i, a in enumerate(ARMS)}       # NOT hash(): hash() is per-process (B7)
FROZEN_NAMES = ("N_TASKS", "REPLAY_K", "STEPS", "BATCH", "HIDDEN", "LR", "MARGIN",
                "POISON_MARGIN", "PRESERVE_FRAC", "LEARN_FLOOR", "WIN_FRACTION",
                "N_PERM", "N_DRAWS", "REQUIRED_BEAT", "MECHANISM_FREE", "STOCHASTIC",
                "POISON_PER_PAST_TOPIC", "QUERIES_PER")

DEV = None


def require_cuda():
    global DEV
    if not torch.cuda.is_available():
        raise RuntimeError("GPU_REQUIRED: neural workload, no CPU fallback branch exists.")
    torch.backends.cuda.matmul.allow_tf32 = False
    DEV = torch.device("cuda:0")
    return DEV


# ---------------------------------------------------------------- world + poison


def build_world(w, poisoned):
    """AMENDMENT A2 (construction) + A3.1/A3.3/A3.9 (order and split).

      A2.1  poison gets a real context vector and real links -- a forgery with context=None is
            excluded by a MISSING FIELD, not by the mechanism.
      A2.2  poison is EXCLUDED from the training stream but INCLUDED in the replay pool.
      A2.3  pool membership follows the topic the forgery IMPERSONATES.
      A2.4  the link graph is rebuilt by the corpus's own rule over the full store.
      A2.5  the residual degree gap (4.89 vs 6.67) is a property of the attack; it gets the
            DEGREE_FILTER competitor rather than a patch.
      A3.1  MEMORY ORDER IS SHUFFLED PER WORLD. `build_corpus` sets topic = i % 32 and
            memory_id = "m%04d" % i, so SORTING THE IDS IS A CLASS ROUND-ROBIN: "take the 32
            lowest-index past memories" selected the IDENTICAL 32-item set as the arm I had
            registered as "ceiling, never a method" -- 32/32 overlap at both task steps, with
            no query, no labels, no semantics and no CAS. Verified by index arithmetic, no
            seeds involved. The poison source draw and the CMB query draw took the lowest ids
            too, identically in every world. All three now draw from the world's own RNG.
      A3.9  THE TASK SPLIT IS DRAWN PER WORLD. It was topics[i::3] over sorted topics, i.e. the
            constant (i mod 32) mod 3 in all 12 worlds, so the worlds differed only in
            semantic centroids and trajectories.
    """
    seed = 20260901 + 1000 * w
    assert seed not in LEGACY, f"world seed {seed} was used by an earlier bench"
    K.SEED = seed
    rng = random.Random(770000 + w)
    memories, _tvecs, marginals = K.build_corpus()

    topics = sorted({m["topic"] for m in memories.values()})
    shuffled = topics[:]
    rng.shuffle(shuffled)                                              # A3.9
    groups = [set(shuffled[i::N_TASKS]) for i in range(N_TASKS)]

    poison_ids, src_topic = set(), {}
    if poisoned:
        past_topics = sorted(groups[0] | groups[1])
        for t in past_topics:
            cand = [i for i in sorted(memories) if memories[i]["topic"] == t]
            rng.shuffle(cand)                                          # A3.1
            for j, mid in enumerate(cand[:POISON_PER_PAST_TOPIC]):
                m = memories[mid]
                ftraj = list(m["trajectory"])
                p = rng.randrange(len(ftraj))
                ftraj[p] = (ftraj[p] + 1) % 10                 # lev-1: almost the same
                wrong = past_topics[(past_topics.index(t) + 1) % len(past_topics)]
                pid = f"poison_{t}_{j}"
                memories[pid] = K._mk_memory(
                    pid,
                    K._normalize([m["semantic"][d] + rng.gauss(0, 0.03) for d in range(K.SEM_DIM)]),
                    ftraj, f"root_poison_{w}_{t}_{j}", f"src_poison_{w}", wrong, "BASE", "WRONG",
                    K._normalize([m["context"][d] + rng.gauss(0, 0.05)
                                  for d in range(K.CTX_DIM)]))
                poison_ids.add(pid)
                src_topic[pid] = t

        ids = sorted(memories)                                         # A2.4
        for a in ids:
            near = sorted(((K.traj_sim(memories[a]["trajectory"], memories[b]["trajectory"]), b)
                           for b in ids if b != a), key=lambda x: (-x[0], x[1]))
            links = {b for _s, b in near[:3]} | {rng.choice(ids)}
            links.discard(a)
            memories[a]["links"] = sorted(links)
        for a in ids:
            for b in list(memories[a]["links"]):
                if a not in memories[b]["links"]:
                    memories[b]["links"] = sorted(memories[b]["links"] + [a])

    K.assign_generic_geometry(memories, marginals)
    order = sorted(memories)
    rng.shuffle(order)                                                 # A3.1: mids order
    deg = lambda ids: (sum(len(memories[i]["links"]) for i in ids) / len(ids)) if ids else 0.0
    construct = {"mean_degree_poison": deg(sorted(poison_ids)),
                 "mean_degree_real": deg([i for i in sorted(memories) if i not in poison_ids])}
    return memories, order, topics, groups, poison_ids, src_topic, construct


def featurize(memories, mids, topics):
    X = torch.tensor([list(memories[i]["semantic"]) + list(K.profile_of(memories[i]["trajectory"]))
                      for i in mids], dtype=torch.float32, device=DEV)
    Y = torch.tensor([topics.index(memories[i]["topic"]) for i in mids],
                     dtype=torch.long, device=DEV)
    S = torch.tensor([list(memories[i]["semantic"]) for i in mids],
                     dtype=torch.float32, device=DEV)
    return X, Y, S / S.norm(dim=1, keepdim=True).clamp_min(1e-9)


# ---------------------------------------------------------------- replay selectors


def select(arm, W, t, draw=0):
    ck = (arm, t, draw if arm in STOCHASTIC else 0)
    if ck not in W["sel_cache"]:
        W["sel_cache"][ck] = _select(arm, W, t, W["pools"][t], draw)
    return W["sel_cache"][ck]


def _select(arm, W, t, past, draw):
    if arm == "NO_REPLAY" or t == 0 or past.numel() == 0:
        return torch.empty(0, dtype=torch.long, device=DEV), 0
    # B7: fixed per-arm integer, never hash() -- hash() is randomised per process, so the
    # stochastic arms drew different items on every run while the receipt claimed determinism.
    # B4: the WORLD is in the seed. Without it the pools are pure topic arithmetic, identical
    # in every world, and RANDOM drew the SAME 32 items in all 12 -- the win-fraction test
    # would then have treated 12 copies of one draw as 12 independent draws.
    g = torch.Generator(device=DEV).manual_seed(
        1_000_000 * W["world"] + 1000 * t + 10 * ARM_SEED[arm] + draw)
    S, Y = W["S"], W["Y"]

    if arm == "ID_ORDER":
        sel = past[:REPLAY_K]                                  # zero information (A3.1)

    elif arm == "RANDOM":
        sel = past[torch.randperm(past.numel(), generator=g, device=DEV)[:REPLAY_K]]

    elif arm == "SEMANTIC_TO_NEW":                             # documented straw man (A1.3)
        q = S[W["idx"][t]].mean(0, keepdim=True)
        q = q / q.norm().clamp_min(1e-9)
        sel = past[(S[past] @ q.T).squeeze(1).topk(min(REPLAY_K, past.numel())).indices]

    elif arm == "SEMANTIC_DIVERSE":                            # strongest mechanism-free
        pool = S[past]
        start = int(torch.randint(0, past.numel(), (1,), generator=g, device=DEV))
        chosen = [start]
        d = (1.0 - pool @ pool[start]).clone()
        d[start] = -1.0
        while len(chosen) < min(REPLAY_K, past.numel()):
            nxt = int(torch.argmax(d))
            chosen.append(nxt)
            d = torch.minimum(d, 1.0 - pool @ pool[nxt])
            d[nxt] = -1.0
        sel = past[torch.tensor(chosen, device=DEV)]

    elif arm == "DEGREE_FILTER":            # mechanism-free competitor on safety (A2.5)
        deg = W["deg"][past]
        keep = past[deg >= deg.median()]
        keep = keep if keep.numel() else past
        sel = keep[torch.randperm(keep.numel(), generator=g, device=DEV)[:REPLAY_K]]

    elif arm in ("CMB_AUTHORIZED", "CMB_RETRIEVED"):
        # A2.6: the store at task t holds tasks 0..t-1 only. A2.7/A3.1: queries are drawn from
        # the world's RNG, not taken as the lowest ids of each new-task topic.
        sub, sub_adj = W["substore"][t]
        byt = {}
        for tp in sorted(W["groups"][t]):
            ex = [i for i in W["mids"] if W["memories"][i]["topic"] == tp]
            random.Random(90000 + W["world"] * 31 + tp).shuffle(ex)
            byt[tp] = ex[:QUERIES_PER]
        pool, seen = [], set()
        for r in range(QUERIES_PER):
            for tp in sorted(byt):
                if len(pool) >= REPLAY_K or r >= len(byt[tp]):
                    continue
                src = W["memories"][byt[tp][r]]
                q = {"q_sem": src["semantic"], "q_traj": list(src["trajectory"]),
                     "targets": [], "distractors": [], "q_ctx": src["context"]}
                ranked, _a, _b = K.arm_d(sub, sub_adj, q)
                ret, auth, _d = V2.verify_two_tier(sub, q, ranked)
                for mid, _sc in (auth if arm == "CMB_AUTHORIZED" else ret):
                    j = W["pos"][mid]
                    if j not in seen:
                        seen.add(j)
                        pool.append(j)
        sel = torch.tensor(pool[:REPLAY_K], dtype=torch.long, device=DEV)

    elif arm in ("CLASS_BALANCED", "CLASS_BALANCED_POOL"):
        # RENAMED from ORACLE_BALANCED (A3.1). It uses only labels already stored on the
        # memories, so it is a DEPLOYABLE ONE-LINE METHOD, not an oracle, and the mechanism is
        # required to beat it. A3.3: built from the TRUE past training indices only -- drawing
        # from the pool let forgeries carrying a wrong label form eleven classes whose only
        # members were forgeries, and the "ceiling" then ingested 16 of 32 forgeries, more than
        # any other arm.
        # A3.1b: pick a RANDOM member of each class, not the first in store order. Taking the
        # first left this arm 21-25 of 32 identical to ID_ORDER even after the order shuffle,
        # because both then prefer early-in-order items. Class BALANCE is the mechanism; WHICH
        # member is drawn must not be an order artefact.
        # A5. TWO arms, because one cannot honestly play both roles:
        #   CLASS_BALANCED       draws from the true past TRAINING stream -- poison-free by
        #                        construction. CAPABILITY competitor only. In CLEAN worlds this
        #                        pool is IDENTICAL to everyone else's, so the capability
        #                        comparison the owner requires is fair. Its POISONED row is NOT
        #                        a safety result and must never be read as one.
        #   CLASS_BALANCED_POOL  draws from the SAME replay pool as every other arm, balancing
        #                        on the label STORED on each memory. Forgeries carry a wrong
        #                        label, so they are eligible and it gets fooled -- which is what
        #                        a deployable label-balanced method actually does. This is the
        #                        FAIR safety competitor.
        # The A3.3 repair moved this arm to the training stream to stop the "ceiling" ingesting
        # 16 of 32 forgeries. That fixed the reference row and quietly handed the arm a
        # poison-free pool, i.e. a safety oracle -- the repair manufacturing the next problem,
        # which is how three of the four earlier shortcuts in this lane were born.
        source = torch.cat(W["idx"][:t]).tolist() if arm == "CLASS_BALANCED" else past.tolist()
        byc = {}
        for i in source:
            byc.setdefault(int(Y[i]), []).append(i)
        cbr = random.Random(51000 + W["world"] * 17 + t + (7 if arm.endswith("POOL") else 0))
        for c in byc:
            cbr.shuffle(byc[c])
        out, r = [], 0
        while len(out) < REPLAY_K and any(len(v) > r for v in byc.values()):
            for c in sorted(byc):
                if len(out) < REPLAY_K and len(byc[c]) > r:
                    out.append(byc[c][r])
            r += 1
        sel = torch.tensor(out[:REPLAY_K], dtype=torch.long, device=DEV)
    else:
        raise ValueError(arm)

    supplied = int(sel.numel())
    # EQUAL-VOLUME RULE (A1.5): an arm that replays fewer items is a different experiment.
    if 0 < supplied < REPLAY_K:
        sel = torch.cat([sel, sel[torch.randint(0, supplied, (REPLAY_K - supplied,),
                                                generator=g, device=DEV)]])
    return sel, supplied


# ---------------------------------------------------------------- training


def train_arm(arm, W, seed, draw=0):
    idx, Y, X = W["idx"], W["Y"], W["X"]
    torch.manual_seed(seed)
    net = nn.Sequential(nn.Linear(X.shape[1], HIDDEN), nn.ReLU(),
                        nn.Linear(HIDDEN, len(W["topics"]))).to(DEV)
    opt = torch.optim.Adam(net.parameters(), lr=LR)
    a1, ingested, underfill, covered = None, 0, 0, set()
    for t in range(N_TASKS):
        rep, supplied = select(arm, W, t, draw)
        if t and arm != "NO_REPLAY":
            underfill += max(0, REPLAY_K - supplied)
            uniq = set(rep.tolist())
            ingested += sum(1 for i in uniq if i in W["poison_idx"])
            covered |= {int(Y[i]) for i in uniq if i not in W["poison_idx"]}
        for _ in range(STEPS):
            b = idx[t][torch.randint(0, idx[t].numel(), (BATCH,), device=DEV)]
            if rep.numel():
                b = torch.cat([b, rep[torch.randint(0, rep.numel(), (REPLAY_K,), device=DEV)]])
            opt.zero_grad()
            nn.functional.cross_entropy(net(X[b]), Y[b]).backward()
            opt.step()
        if t == 0:
            with torch.no_grad():
                a1 = float((net(X[idx[0]]).argmax(1) == Y[idx[0]]).double().mean())
    with torch.no_grad():
        logits = net(X[idx[0]])
        end1 = float((logits.argmax(1) == Y[idx[0]]).double().mean())
        # A3.10: score restricted to task-0 classes. Unmasked forgetting is a class-incremental
        # naming effect; masked forgetting shows whether the REPRESENTATION survived.
        keep = sorted({int(Y[i]) for i in idx[0].tolist()})
        km = torch.tensor(keep, device=DEV)
        masked = float((km[logits[:, km].argmax(1)] == Y[idx[0]]).double().mean())
        last = idx[N_TASKS - 1]
        acc_last = float((net(X[last]).argmax(1) == Y[last]).double().mean())
        seen = torch.cat(idx)
        alla = float((net(X[seen]).argmax(1) == Y[seen]).double().mean())
    return {"acc_T1_after_T1": a1, "acc_T1_end": end1, "forgetting": a1 - end1,
            "acc_Tlast_end": acc_last,
            "masked_acc_T1_end": masked, "final_avg_acc": alla,
            "past_classes_covered": len(covered),
            "poison_ingested": ingested,
            "poison_rate": ingested / max(1, REPLAY_K * (N_TASKS - 1)),
            "underfilled": underfill}


def run_world(w, condition):
    memories, mids, topics, groups, poison_ids, src_topic, construct = build_world(
        w, condition == "POISONED")
    X, Y, S = featurize(memories, mids, topics)
    pos = {m: i for i, m in enumerate(mids)}
    poison_idx = {pos[p] for p in poison_ids}
    idx = [torch.tensor([i for i in range(len(mids)) if topics[int(Y[i])] in g
                         and i not in poison_idx], device=DEV) for g in groups]
    tof = {}
    for i, m in enumerate(mids):
        tp = src_topic[m] if m in src_topic else memories[m]["topic"]
        for gi, g in enumerate(groups):
            if tp in g:
                tof[i] = gi
    pools = [torch.tensor([i for i in range(len(mids)) if tof.get(i, 99) < t],
                          dtype=torch.long, device=DEV) for t in range(N_TASKS)]
    substore = {}
    for t in range(1, N_TASKS):
        keep = {mids[i] for i in pools[t].tolist()}
        sub = {k: dict(memories[k]) for k in keep}
        for k in sub:
            sub[k]["links"] = [l for l in sub[k]["links"] if l in keep]
        substore[t] = (sub, K.build_adjacency(sub))
    W = {"world": w, "memories": memories, "adj": K.build_adjacency(memories), "mids": mids,
         "pos": pos, "deg": torch.tensor([float(len(memories[m]["links"])) for m in mids],
                                         device=DEV),
         "X": X, "Y": Y, "S": S, "idx": idx, "pools": pools, "groups": groups,
         "topics": topics, "poison_idx": poison_idx, "sel_cache": {}, "substore": substore}

    out = {"world": w, "condition": condition, "n_poison": len(poison_idx),
           "pool_sizes": [int(p.numel()) for p in pools], "construct": construct, "arms": {}}
    for arm in ARMS:
        draws = range(N_DRAWS) if arm in STOCHASTIC else (0,)
        runs = [train_arm(arm, W, s, d) for d in draws for s in SEEDS]
        agg = {k: sum(r[k] for r in runs) / len(runs) for k in runs[0]}
        agg["n_runs"] = len(runs)
        agg["forgetting_sd"] = statistics.pstdev([r["forgetting"] for r in runs])
        out["arms"][arm] = agg
    return out


# ---------------------------------------------------------------- status


def paired(rs, a, b, key):
    """Lower `key` is better. Positive delta means arm `a` forgets less than arm `b`."""
    d = [rs[w]["arms"][b][key] - rs[w]["arms"][a][key] for w in rs]
    if len(d) < 5:
        return {"mean_delta": None, "sd": None, "worlds_positive": 0, "n": len(d),
                "p_perm": None, "win": False}
    m = sum(d) / len(d)
    p = K.paired_permutation(d, random.Random(4242))
    return {"mean_delta": m, "sd": statistics.pstdev(d),
            "worlds_positive": sum(1 for x in d if x > 0), "n": len(d), "p_perm": p,
            # A3.5: the test is the permutation p-value on the paired deltas, not the
            # win fraction. Between-world sd (~0.108) is FIVE TIMES the margin, and the
            # win-fraction rule had a floor near 0.076 that more worlds cannot lower.
            "win": bool(m > MARGIN and p < 0.05)}


def summarize(clean, poisoned):
    C = {w["world"]: w for w in clean}
    P = {w["world"]: w for w in poisoned}

    def mean(D, a, k):
        return sum(d["arms"][a][k] for d in D.values()) / len(D)

    gates = {"no_replay_forgetting": mean(C, "NO_REPLAY", "forgetting"),
             "class_balanced_forgetting": mean(C, "CLASS_BALANCED", "forgetting"),
             "id_order_forgetting": mean(C, "ID_ORDER", "forgetting")}
    gates["forgetting_exists"] = gates["no_replay_forgetting"] > 0.10
    gates["replay_helps"] = (gates["class_balanced_forgetting"]
                             < gates["no_replay_forgetting"] - MARGIN)
    # A3.1: if the zero-information rule reaches the class-balanced arm or the mechanism, the
    # comparison is not measuring what it claims and NO status may be emitted.
    gates["id_order_not_equivalent"] = (
        abs(gates["id_order_forgetting"] - gates["class_balanced_forgetting"]) > MARGIN
        and abs(gates["id_order_forgetting"]
                - mean(C, "CMB_AUTHORIZED", "forgetting")) > MARGIN)

    cap = {b: paired(C, "CMB_AUTHORIZED", b, "forgetting")
           for b in ARMS if b != "CMB_AUTHORIZED"}
    keys = (("poison_ingested", "poison_ingested"), ("poison_rate", "poison_rate"),
            ("underfilled", "underfilled"), ("forgetting_under_poison", "forgetting"),
            ("final_acc_under_poison", "final_avg_acc"),
            ("classes_covered_under_poison", "past_classes_covered"))
    saf = {k: {a: mean(P, a, v) for a in ARMS} for k, v in keys}
    coverage = {a: mean(C, a, "past_classes_covered") for a in ARMS}

    auth_empty = mean(C, "CMB_AUTHORIZED", "underfilled") >= REPLAY_K * 0.9 * (N_TASKS - 1)

    # ---- capability (A3.6: one law, and it is the law the code executes) ----
    best_mf = min(mean(C, b, "forgetting") for b in MECHANISM_FREE)
    best_mf_arm = min(MECHANISM_FREE, key=lambda b: mean(C, b, "forgetting"))
    if not (gates["forgetting_exists"] and gates["replay_helps"]
            and gates["id_order_not_equivalent"]):
        cap_status, cap_reason = "STATUS_NOT_EMITTED", "PRECONDITION_FAILED"
    elif auth_empty:
        cap_status, cap_reason = ("STATUS_NOT_EMITTED",
                                  "AUTHORIZED tier effectively EMPTY -- that is NO_REPLAY")
    elif all(cap[b]["win"] for b in MECHANISM_FREE):
        cap_status, cap_reason = "CMB_REPLAY_REDUCES_FORGETTING", None
    elif cap["NO_REPLAY"]["win"]:
        cap_status = "CMB_REPLAY_BEATS_NO_REPLAY_ONLY"
        cap_reason = f"loses to or ties the best mechanism-free arm ({best_mf_arm} {best_mf:.4f})"
    else:
        cap_status, cap_reason = "CMB_REPLAY_NO_BENEFIT", "does not beat NO_REPLAY"

    # ---- safety (A3.2: the registered section-11 falsifier is now EXECUTABLE) ----
    pi, fp = saf["poison_ingested"], saf["forgetting_under_poison"]
    # CLASS_BALANCED is EXCLUDED from every safety comparison: its pool is poison-free by
    # construction (A5). CLASS_BALANCED_POOL is the fair label-balanced safety competitor and
    # IS in MECHANISM_FREE.
    two_tier_gap = pi["CMB_RETRIEVED"] - pi["CMB_AUTHORIZED"]
    best_base = min(pi[b] for b in MECHANISM_FREE)
    best_base_arm = min(MECHANISM_FREE, key=lambda b: pi[b])
    if auth_empty:
        saf_status = "AUTHORIZATION_NO_POISON_BENEFIT"
        saf_reason = "AUTHORIZED tier was effectively EMPTY -- that is NO_REPLAY, not a defence"
    elif two_tier_gap <= POISON_MARGIN:
        saf_status = "TWO_TIER_GATE_EARNS_NOTHING"
        saf_reason = (f"AUTHORIZED {pi['CMB_AUTHORIZED']:.2f} vs RETRIEVED "
                      f"{pi['CMB_RETRIEVED']:.2f} -- the retrieval floor did the work and the "
                      f"second tier, the whole subject of this bench, added nothing")
    elif (pi["CMB_AUTHORIZED"] < best_base - POISON_MARGIN
          and fp["CMB_AUTHORIZED"] < fp["RANDOM"] - MARGIN):
        saf_status, saf_reason = "AUTHORIZATION_PREVENTS_POISONING", None
    else:
        saf_status = "AUTHORIZATION_NO_POISON_BENEFIT"
        saf_reason = (f"ingested {pi['CMB_AUTHORIZED']:.2f} vs best mechanism-free "
                      f"{best_base_arm} {best_base:.2f}; forgetting {fp['CMB_AUTHORIZED']:.4f} "
                      f"vs RANDOM {fp['RANDOM']:.4f}")

    # ---- OWNER PROMOTION LAW (ruling 2026-09-02) --------------------------------------
    # Stricter than the capability status above and BINDING for promotion. Eight conditions,
    # every one executable. "No result may promote unless CMB_AUTHORIZED: admits less poison
    # than CMB_RETRIEVED; beats RANDOM; beats SEMANTIC_DIVERSE; beats CLASS_BALANCED; beats
    # DEGREE_FILTER; preserves old-task performance; still learns the new task; clears the
    # frozen world-level uncertainty law."
    peak = mean(C, "CMB_AUTHORIZED", "acc_T1_after_T1")
    kept = mean(C, "CMB_AUTHORIZED", "acc_T1_end")
    preserve_ratio = kept / peak if peak > 0 else 0.0
    acc_new = mean(C, "CMB_AUTHORIZED", "acc_Tlast_end")
    promo = {
        "admits_less_poison_than_RETRIEVED": bool(two_tier_gap > POISON_MARGIN),
        "beats_RANDOM": bool(cap["RANDOM"]["win"]),
        "beats_SEMANTIC_DIVERSE": bool(cap["SEMANTIC_DIVERSE"]["win"]),
        "beats_CLASS_BALANCED": bool(cap["CLASS_BALANCED"]["win"]),
        "beats_DEGREE_FILTER": bool(cap["DEGREE_FILTER"]["win"]),
        "preserves_old_task": bool(preserve_ratio >= PRESERVE_FRAC),
        "learns_new_task": bool(acc_new >= LEARN_FLOOR),
        "clears_uncertainty_law": bool(
            all(cap[b]["p_perm"] is not None and cap[b]["p_perm"] < 0.05
                for b in REQUIRED_BEAT)),
    }
    failed = [k for k, v in promo.items() if not v]
    promotion = {"conditions": promo, "failed": failed,
                 "status": "PROMOTABLE" if not failed else "NOT_PROMOTABLE",
                 "preserve_ratio": preserve_ratio, "acc_new_task": acc_new,
                 "note": ("Owner ruling 2026-09-02. ALL EIGHT must hold. This law is BINDING "
                          "for promotion and is stricter than the capability status.")}

    return {"promotion": promotion,
            "gates": gates, "capability": cap, "capability_status": cap_status,
            "capability_reason": cap_reason, "best_mechanism_free": [best_mf_arm, best_mf],
            "safety": saf, "safety_status": saf_status, "safety_reason": saf_reason,
            "two_tier_poison_gap": two_tier_gap, "coverage_clean": coverage,
            "clean_forgetting": {a: mean(C, a, "forgetting") for a in ARMS},
            "clean_masked_acc": {a: mean(C, a, "masked_acc_T1_end") for a in ARMS},
            "clean_final_acc": {a: mean(C, a, "final_avg_acc") for a in ARMS},
            "clean_forgetting_sd": {a: mean(C, a, "forgetting_sd") for a in ARMS},
            "clean_underfilled": {a: mean(C, a, "underfilled") for a in ARMS},
            "power_note": ("Between-world sd on the paired delta is ~0.108 against a registered "
                           "headroom of 0.045. No affordable world count resolves the "
                           "capability question: a tie is ABSENCE OF POWER, not equivalence. "
                           "The safety half is a COUNT and is the load-bearing measurement."),
            "coverage_note": ("Class coverage of the replay set predicts forgetting at rank "
                              "correlation -0.9017, and the two-tier verifier is not a "
                              "coverage mechanism.")}


def main(worlds=WORLDS, out="CMB_RP0_RECEIPT.json"):
    require_cuda()
    if os.environ.get("PYTHONHASHSEED") != "0":
        print("WARNING: PYTHONHASHSEED != 0; arm seeds are fixed integers so this does not "
              "affect selection, but string hashing elsewhere is not pinned.", flush=True)
    t0 = time.perf_counter()
    clean, poisoned = [], []
    try:
        for w in worlds:
            clean.append(run_world(w, "CLEAN"))
            poisoned.append(run_world(w, "POISONED"))
            with open("CMB_RP0_RAW.json", "w") as f:
                json.dump({"clean": clean, "poisoned": poisoned}, f)
            print(f"  world {w} done ({time.perf_counter()-t0:.0f}s)", flush=True)
        print("RAW FLUSHED", flush=True)
        summ = summarize(clean, poisoned)
    except Exception:
        with open(out, "w") as f:
            json.dump({"FAILED": True, "traceback": traceback.format_exc(),
                       "partial_clean": clean, "partial_poisoned": poisoned}, f, indent=1)
        traceback.print_exc()
        return 2

    p = torch.cuda.get_device_properties(0)
    receipt = {"project": "CMB-RP0 selective replay and catastrophic forgetting",
               "version": VERSION,
               "preregistration": "CMB_RP0_PREREGISTRATION.md v0.1 + A1 + A2 + A3",
               "builder": "Claude", "auditor": "a different model, named by the owner",
               "worlds": list(worlds), "seeds": list(SEEDS), "arms": list(ARMS),
               "frozen_params": {n: globals()[n] for n in FROZEN_NAMES},
               "summary": summ, "clean": clean, "poisoned": poisoned,
               "compute": {"gpu": torch.cuda.get_device_name(0), "cuda": torch.version.cuda,
                           "torch": torch.__version__, "capability": f"{p.major}.{p.minor}",
                           "pythonhashseed": os.environ.get("PYTHONHASHSEED"),
                           "peak_vram_bytes": int(torch.cuda.max_memory_allocated()),
                           "wall_s": round(time.perf_counter() - t0, 2),
                           "scale_note": ("The learner is a ~4.8k-parameter MLP. The GPU does a "
                                          "fraction of a second of arithmetic across the whole "
                                          "run; the instance is rented for Python interpreter "
                                          "overhead, not for compute. GPU usage here is NOT "
                                          "evidence of scale.")},
               "claim_note": ("Tests the CMB as a replay SELECTOR only -- topic is 100% "
                              "separable from the semantic vector and the trajectory carries no "
                              "topic information, so this says NOTHING about CAS geometry as a "
                              "feature. Forgetting is class-incremental (masked forgetting "
                              "~0.0024): say 'restores accuracy on earlier classes', never "
                              "'prevents representational forgetting'.")}
    receipt["determinism"] = {"content_hash": hashlib.sha256(
        json.dumps(summ, sort_keys=True).encode()).hexdigest()}
    with open(out, "w") as f:
        json.dump(receipt, f, indent=1, sort_keys=True)

    s = summ
    print(f"\nCAPABILITY: {s['capability_status']}  | {s['capability_reason']}")
    print(f"SAFETY    : {s['safety_status']}  | {s['safety_reason']}")
    g = s["gates"]
    print(f"\ngates: forgetting_exists={g['forgetting_exists']} ({g['no_replay_forgetting']:.4f})"
          f"  replay_helps={g['replay_helps']} ({g['class_balanced_forgetting']:.4f})"
          f"  id_order_not_equivalent={g['id_order_not_equivalent']} "
          f"({g['id_order_forgetting']:.4f})")
    print(f"\n{'arm':>17}{'forget':>9}{'sd':>8}{'maskAcc':>9}{'final':>8}{'cover':>7}"
          f"{'fill':>6}{'poisIn':>8}{'poisFgt':>9}")
    for a in ARMS:
        print(f"{a:>17}{s['clean_forgetting'][a]:>9.4f}{s['clean_forgetting_sd'][a]:>8.4f}"
              f"{s['clean_masked_acc'][a]:>9.4f}{s['clean_final_acc'][a]:>8.4f}"
              f"{s['coverage_clean'][a]:>7.1f}{s['clean_underfilled'][a]:>6.0f}"
              f"{s['safety']['poison_ingested'][a]:>8.2f}"
              f"{s['safety']['forgetting_under_poison'][a]:>9.4f}")
    print(f"\ntwo-tier poison gap (RETRIEVED - AUTHORIZED): {s['two_tier_poison_gap']:+.2f} "
          f"(needs > {POISON_MARGIN})")
    print("\nCMB_AUTHORIZED forgets less than:")
    for k, v in s["capability"].items():
        if v["mean_delta"] is not None:
            print(f"   {k:>17}  delta {v['mean_delta']:+.4f}  sd {v['sd']:.4f}  "
                  f"{v['worlds_positive']}/{v['n']}  p={v['p_perm']:.4f}  win={v['win']}")
    print("\nHASH:", receipt["determinism"]["content_hash"][:16],
          f" wall {receipt['compute']['wall_s']}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
