"""CMB-RP0 -- selective replay and catastrophic forgetting (owner items 5 and 6).

Frozen design: CMB_RP0_PREREGISTRATION.md v0.1 + AMENDMENT A1 + AMENDMENT A2.
Builder: Claude. Auditor: a different model. Conflict of interest declared in prereg section 0.

WHAT THIS TESTS. Retrieval is recoverable -- a wrong memory shown to a user can be dismissed.
REPLAY IS NOT: a forgery mixed into a training batch is written into the weights. So this is
the case the two-tier verifier was built for, and the poisoning condition is the sharpest test
in the lane.

WHAT IT DOES NOT TEST. Measured in A1.1: topic is 100% separable from the semantic vector
(480/480) and the trajectory carries NO topic information (17/480, exactly chance). So this
bench tests the CMB as a replay SELECTOR. It says nothing about CAS geometry as a feature.

GPU-only for the neural work, fail closed. Local 4070 is smoke/dev and records no measurement.
"""
import hashlib
import json
import os
import random
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

VERSION = "cmb_rp0_v0.1"

# NEW worlds. RGM-0.1 used 0-19, RGM-0.2 used 500-511; asserted disjoint at runtime.
WORLDS = tuple(range(700, 712))
LEGACY = {20260901 + 1000 * w for w in list(range(0, 20)) + list(range(500, 512))}
SEEDS = (0, 1, 2)
N_TASKS = 3
REPLAY_K = 32
STEPS = 300
BATCH = 64
HIDDEN = 64
LR = 1e-3
MARGIN = 0.02
WIN_FRACTION = 0.70
POISON_PER_PAST_TOPIC = 6
QUERIES_PER = 8            # CMB query budget per new-task topic (A2.7)

ARMS = ("NO_REPLAY", "RANDOM", "SEMANTIC_DIVERSE", "SEMANTIC_TO_NEW", "DEGREE_FILTER",
        "CMB_AUTHORIZED", "CMB_RETRIEVED", "ORACLE_BALANCED")
FROZEN_NAMES = ("N_TASKS", "REPLAY_K", "STEPS", "BATCH", "HIDDEN", "LR", "MARGIN",
                "WIN_FRACTION", "POISON_PER_PAST_TOPIC", "QUERIES_PER")

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
    """AMENDMENT A2. Three construction rules, each fixing a way this test could have been
    silently invalid:

      A2.1  Poison is built BEFORE assign_generic_geometry and is given a real context vector
            and real symmetric links. A forgery with context=None or an empty link list is
            structurally distinguishable, and the verifier would then reject it for a
            BOOKKEEPING reason rather than by its mechanism -- a fake win.
      A2.2  Poison is EXCLUDED from the training stream but INCLUDED in the replay pool. It is
            an item sitting in memory, eligible for recall, that the model never legitimately
            learned. Excluded from the pool, the safety test would be vacuous.
      A2.3  Pool membership follows the topic the forgery IMPERSONATES, not its wrong label, so
            a forgery is stored alongside the memory it is pretending to be.
      A2.4  The link graph is rebuilt by the corpus's OWN rule over the full store. My first
            construction gave each forgery its source's whole link set, making poison nodes
            HUBS (mean degree 12.55 against 7.42). Linking only the forgeries then left them
            with no INCOMING edges (4.00 against 6.79) -- the same giveaway, reversed.
      A2.5  A GAP REMAINS AND IS NOT REMOVABLE: 4.89 against 6.67. A forgery of one memory is
            close to that one memory, so it earns fewer edges than a real memory sitting in a
            cluster. That is a property of the attack, not a bug, and it cannot be tuned away
            without faking the graph. So it gets a COMPETITOR instead: the DEGREE_FILTER arm
            uses that statistic and nothing else. If it keeps poison out as well as the
            verifier does, the verifier's safety result is not licensed.
    """
    seed = 20260901 + 1000 * w
    assert seed not in LEGACY, f"world seed {seed} was used by an earlier bench"
    K.SEED = seed
    rng = random.Random(770000 + w)
    memories, _tvecs, marginals = K.build_corpus()

    poison_ids, src_topic = set(), {}
    if poisoned:
        tall = sorted({m["topic"] for m in memories.values()})
        g0 = [set(tall[i::N_TASKS]) for i in range(N_TASKS)]
        past_topics = sorted(g0[0] | g0[1])
        for t in past_topics:
            src = [i for i in sorted(memories) if memories[i]["topic"] == t][:POISON_PER_PAST_TOPIC]
            for j, mid in enumerate(src):
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
                    K._normalize([m["context"][d] + rng.gauss(0, 0.05)   # A2.1: real context
                                  for d in range(K.CTX_DIM)]))
                poison_ids.add(pid)
                src_topic[pid] = t                                        # A2.3

        # A2.4: rebuild the WHOLE link graph by the corpus's own rule over the full store --
        # 3 trajectory-nearest + 1 random, then symmetrised. Linking only the forgeries left
        # them with no INCOMING edges (degree 4.00 against 6.79), which is just as much of a
        # giveaway as making them hubs. This is what the store would look like if those items
        # had been present when it was built.
        ids = sorted(memories)
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

    K.assign_generic_geometry(memories, marginals)             # A2.1: poison included
    topics = sorted({m["topic"] for m in memories.values()})
    groups = [set(topics[i::N_TASKS]) for i in range(N_TASKS)]
    deg = lambda ids: (sum(len(memories[i]["links"]) for i in ids) / len(ids)) if ids else 0.0
    construct = {"mean_degree_poison": deg(sorted(poison_ids)),
                 "mean_degree_real": deg([i for i in sorted(memories) if i not in poison_ids])}
    return memories, topics, groups, poison_ids, src_topic, construct


def featurize(memories, topics):
    mids = sorted(memories)
    X = torch.tensor([list(memories[i]["semantic"]) + list(K.profile_of(memories[i]["trajectory"]))
                      for i in mids], dtype=torch.float32, device=DEV)
    Y = torch.tensor([topics.index(memories[i]["topic"]) for i in mids],
                     dtype=torch.long, device=DEV)
    S = torch.tensor([list(memories[i]["semantic"]) for i in mids],
                     dtype=torch.float32, device=DEV)
    S = S / S.norm(dim=1, keepdim=True).clamp_min(1e-9)
    return mids, X, Y, S


# ---------------------------------------------------------------- replay selectors


def select(arm, W, t, past):
    """Return REPLAY_K pool indices to replay, plus how many were genuinely supplied.

    CACHED per (arm, task). Selection depends on the world and the arm, never on the training
    seed, so recomputing it for each of the three seeds tripled the cost of the CMB arms --
    and the CMB arms re-run graph propagation once per topic of the new task.
    """
    ck = (arm, t)
    if ck in W["sel_cache"]:
        return W["sel_cache"][ck]
    out = _select(arm, W, t, past)
    W["sel_cache"][ck] = out
    return out


def _select(arm, W, t, past):
    if arm == "NO_REPLAY" or t == 0 or past.numel() == 0:
        return torch.empty(0, dtype=torch.long, device=DEV), 0
    g = torch.Generator(device=DEV).manual_seed(1000 * t + (hash(arm) % 100000))
    S, Y = W["S"], W["Y"]

    if arm == "RANDOM":
        sel = past[torch.randperm(past.numel(), generator=g, device=DEV)[:REPLAY_K]]

    elif arm == "SEMANTIC_TO_NEW":                      # documented straw man (A1.3)
        q = S[W["idx"][t]].mean(0, keepdim=True)
        q = q / q.norm().clamp_min(1e-9)
        sel = past[(S[past] @ q.T).squeeze(1).topk(min(REPLAY_K, past.numel())).indices]

    elif arm == "SEMANTIC_DIVERSE":                     # strongest mechanism-free baseline
        pool = S[past]
        chosen = [0]
        d = (1.0 - pool @ pool[0]).clone()
        d[0] = -1.0
        while len(chosen) < min(REPLAY_K, past.numel()):
            nxt = int(torch.argmax(d))
            chosen.append(nxt)
            d = torch.minimum(d, 1.0 - pool @ pool[nxt])
            d[nxt] = -1.0
        sel = past[torch.tensor(chosen, device=DEV)]

    elif arm in ("CMB_AUTHORIZED", "CMB_RETRIEVED"):
        # A2.6. The store at task t holds tasks 0..t-1 and NOTHING ELSE -- the new task's
        # items have not been stored yet. My first version queried the FULL store with a
        # new-task memory, and the verifier correctly returned that same memory (best
        # coherence 1.0000, a self-match); I then discarded it for not being a past item, so
        # the authorized tier came back EMPTY on all 64 slots and the arm was numerically
        # identical to NO_REPLAY. The verifier was right and the harness was wrong.
        # A2.7. Queried at the arm's BEST setting, not a handicapped one: up to QUERIES_PER
        # examples per new-task topic, round-robin across topics, stopping as soon as the
        # budget is filled. One query per topic supplied only ~19 of 32 slots, and judging a
        # selector at a setting that starves it proves nothing about the selector.
        sub, sub_adj = W["substore"][t]
        byt = {tp: [i for i in W["mids"] if W["memories"][i]["topic"] == tp][:QUERIES_PER]
               for tp in sorted(W["groups"][t])}
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

    elif arm == "DEGREE_FILTER":
        # MECHANISM-FREE COMPETITOR ON THE SAFETY AXIS (A2.5). A one-item forgery is close to
        # exactly one memory, so it ends up with fewer edges than a real memory (measured
        # 4.89 against 6.67). This arm exploits ONLY that: keep the past items whose degree is
        # at or above the pool median, then sample at random. No query, no semantics, no CAS.
        # If it excludes poison as well as the verifier does, the verifier's safety result is
        # NOT licensed -- the win would belong to a graph statistic, not to the mechanism.
        deg = W["deg"][past]
        keep = past[deg >= deg.median()]
        keep = keep if keep.numel() else past
        sel = keep[torch.randperm(keep.numel(), generator=g, device=DEV)[:REPLAY_K]]

    elif arm == "ORACLE_BALANCED":                      # ceiling, never a method
        # A2.7: round-robin over classes until the budget is FULL. A fixed per-class quota of
        # REPLAY_K // n_classes left 10 of 32 slots empty and let SEMANTIC_DIVERSE beat the
        # "ceiling", which would have made the precondition gate meaningless.
        byc = {}
        for i in past.tolist():
            byc.setdefault(int(Y[i]), []).append(i)
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
    # EQUAL-VOLUME RULE (A1.5): an arm that replays fewer items is a different experiment, not
    # a better selector. Underfill is RECORDED and topped up from the arm's own selection, so
    # the comparison is about SELECTION, not VOLUME.
    if 0 < supplied < REPLAY_K:
        sel = torch.cat([sel, sel[torch.randint(0, supplied, (REPLAY_K - supplied,),
                                                generator=g, device=DEV)]])
    return sel, supplied


# ---------------------------------------------------------------- training


def train_arm(arm, W, seed):
    idx, pools, Y, X = W["idx"], W["pools"], W["Y"], W["X"]
    torch.manual_seed(seed)
    net = nn.Sequential(nn.Linear(X.shape[1], HIDDEN), nn.ReLU(),
                        nn.Linear(HIDDEN, len(W["topics"]))).to(DEV)
    opt = torch.optim.Adam(net.parameters(), lr=LR)
    a1_after_t1, ingested, underfill = None, 0, 0
    for t in range(N_TASKS):
        rep, supplied = select(arm, W, t, pools[t])
        if t and arm != "NO_REPLAY":
            underfill += max(0, REPLAY_K - supplied)
            ingested += sum(1 for i in set(rep.tolist()) if i in W["poison_idx"])
        for _ in range(STEPS):
            b = idx[t][torch.randint(0, idx[t].numel(), (BATCH,), device=DEV)]
            if rep.numel():
                b = torch.cat([b, rep[torch.randint(0, rep.numel(), (REPLAY_K,), device=DEV)]])
            opt.zero_grad()
            nn.functional.cross_entropy(net(X[b]), Y[b]).backward()
            opt.step()
        if t == 0:
            with torch.no_grad():
                a1_after_t1 = float((net(X[idx[0]]).argmax(1) == Y[idx[0]]).double().mean())
    with torch.no_grad():
        end1 = float((net(X[idx[0]]).argmax(1) == Y[idx[0]]).double().mean())
        seen = torch.cat(idx)
        alla = float((net(X[seen]).argmax(1) == Y[seen]).double().mean())
    return {"acc_T1_after_T1": a1_after_t1, "acc_T1_end": end1,
            "forgetting": a1_after_t1 - end1, "final_avg_acc": alla,
            "poison_ingested": ingested, "poison_rate": ingested / max(1, REPLAY_K),
            "underfilled": underfill}


def run_world(w, condition):
    memories, topics, groups, poison_ids, src_topic, construct = build_world(
        w, condition == "POISONED")
    mids, X, Y, S = featurize(memories, topics)
    pos = {m: i for i, m in enumerate(mids)}
    poison_idx = {pos[p] for p in poison_ids}
    # training stream: real memories only (A2.2)
    idx = [torch.tensor([i for i in range(len(mids)) if topics[int(Y[i])] in g
                         and i not in poison_idx], device=DEV) for g in groups]
    # replay pool at task t: everything stored from EARLIER tasks, poison INCLUDED, placed by
    # the topic it impersonates (A2.2, A2.3)
    tof = {}
    for i, m in enumerate(mids):
        tp = src_topic[m] if m in src_topic else memories[m]["topic"]
        for gi, g in enumerate(groups):
            if tp in g:
                tof[i] = gi
    pools = [torch.tensor([i for i in range(len(mids)) if tof.get(i, 99) < t],
                          dtype=torch.long, device=DEV) for t in range(N_TASKS)]
    # A2.6: the memory store as it stands at the start of each task -- earlier tasks only.
    substore = {}
    for t in range(1, N_TASKS):
        keep = {mids[i] for i in pools[t].tolist()}
        sub = {k: memories[k] for k in keep}
        for k in sub:
            sub[k] = dict(sub[k])
            sub[k]["links"] = [l for l in sub[k]["links"] if l in keep]
        substore[t] = (sub, K.build_adjacency(sub))
    degv = torch.tensor([float(len(memories[m]["links"])) for m in mids], device=DEV)
    W = {"memories": memories, "adj": K.build_adjacency(memories), "mids": mids, "pos": pos,
         "deg": degv,
         "X": X, "Y": Y, "S": S, "idx": idx, "pools": pools, "groups": groups,
         "topics": topics, "poison_idx": poison_idx, "sel_cache": {},
         "substore": substore}
    out = {"world": w, "condition": condition, "n_poison": len(poison_idx),
           "pool_sizes": [int(p.numel()) for p in pools], "construct": construct, "arms": {}}
    for arm in ARMS:
        runs = [train_arm(arm, W, s) for s in SEEDS]
        out["arms"][arm] = {k: sum(r[k] for r in runs) / len(runs) for k in runs[0]}
    return out


# ---------------------------------------------------------------- status


def paired(rs, a, b, key, margin=MARGIN):
    """Lower `key` is better (forgetting). Positive delta means arm `a` forgets less."""
    d = [rs[w]["arms"][b][key] - rs[w]["arms"][a][key] for w in rs]
    if len(d) < 5:
        return {"mean_delta": None, "worlds_positive": 0, "n": len(d), "win": False}
    m, p = sum(d) / len(d), sum(1 for x in d if x > 0)
    return {"mean_delta": m, "worlds_positive": p, "n": len(d),
            "win": bool(m > margin and p >= WIN_FRACTION * len(d))}


def summarize(clean, poisoned):
    C = {w["world"]: w for w in clean}
    P = {w["world"]: w for w in poisoned}

    def mean(D, a, k):
        return sum(d["arms"][a][k] for d in D.values()) / len(D)

    gates = {"no_replay_forgetting": mean(C, "NO_REPLAY", "forgetting"),
             "oracle_forgetting": mean(C, "ORACLE_BALANCED", "forgetting")}
    gates["forgetting_exists"] = gates["no_replay_forgetting"] > 0.10
    gates["oracle_helps"] = gates["oracle_forgetting"] < gates["no_replay_forgetting"] - MARGIN

    cap = {b: paired(C, "CMB_AUTHORIZED", b, "forgetting")
           for b in ("NO_REPLAY", "RANDOM", "SEMANTIC_DIVERSE", "SEMANTIC_TO_NEW",
                     "DEGREE_FILTER", "CMB_RETRIEVED", "ORACLE_BALANCED")}
    saf = {k: {a: mean(P, a, v) for a in ARMS} for k, v in
           (("poison_ingested", "poison_ingested"), ("poison_rate", "poison_rate"),
            ("underfilled", "underfilled"), ("forgetting_under_poison", "forgetting"),
            ("final_acc_under_poison", "final_avg_acc"))}

    # "kept poison out" and "replayed nothing" are DIFFERENT results (A1.5)
    auth_empty = saf["underfilled"]["CMB_AUTHORIZED"] >= REPLAY_K * 0.9 * (N_TASKS - 1)

    if not (gates["forgetting_exists"] and gates["oracle_helps"]):
        cap_status, cap_reason = "STATUS_NOT_EMITTED", "PRECONDITION_FAILED"
    elif cap["RANDOM"]["win"] and cap["SEMANTIC_DIVERSE"]["win"]:
        cap_status, cap_reason = "CMB_REPLAY_REDUCES_FORGETTING", None
    elif cap["NO_REPLAY"]["win"]:
        cap_status, cap_reason = ("CMB_REPLAY_TIES_SEMANTIC",
                                  "beats NO_REPLAY, does not beat the strong baselines")
    else:
        cap_status, cap_reason = "CMB_REPLAY_NO_BENEFIT", "does not beat NO_REPLAY"

    pi = saf["poison_ingested"]
    best_base = min(pi["SEMANTIC_DIVERSE"], pi["SEMANTIC_TO_NEW"], pi["RANDOM"],
                    pi["DEGREE_FILTER"])
    fp = saf["forgetting_under_poison"]
    if auth_empty:
        saf_status = "AUTHORIZATION_NO_POISON_BENEFIT"
        saf_reason = "AUTHORIZED tier was effectively EMPTY -- that is NO_REPLAY, not a defence"
    elif pi["CMB_AUTHORIZED"] < best_base - 0.5 and fp["CMB_AUTHORIZED"] < fp["RANDOM"] - MARGIN:
        saf_status, saf_reason = "AUTHORIZATION_PREVENTS_POISONING", None
    else:
        saf_status = "AUTHORIZATION_NO_POISON_BENEFIT"
        saf_reason = (f"ingested {pi['CMB_AUTHORIZED']:.2f} vs best mechanism-free baseline "
                      f"{best_base:.2f} (DEGREE_FILTER {pi['DEGREE_FILTER']:.2f}); "
                      f"forgetting {fp['CMB_AUTHORIZED']:.4f} vs RANDOM {fp['RANDOM']:.4f}")

    return {"gates": gates, "capability": cap, "capability_status": cap_status,
            "capability_reason": cap_reason, "safety": saf, "safety_status": saf_status,
            "safety_reason": saf_reason,
            "clean_forgetting": {a: mean(C, a, "forgetting") for a in ARMS},
            "clean_final_acc": {a: mean(C, a, "final_avg_acc") for a in ARMS},
            "clean_underfilled": {a: mean(C, a, "underfilled") for a in ARMS}}


def main(worlds=WORLDS, out="CMB_RP0_RECEIPT.json"):
    require_cuda()
    t0 = time.perf_counter()
    clean, poisoned = [], []
    try:
        for w in worlds:
            clean.append(run_world(w, "CLEAN"))
            poisoned.append(run_world(w, "POISONED"))
            # flush after EVERY world: a run cut off by the timer still leaves the worlds it
            # finished, instead of nothing at all
            with open("CMB_RP0_RAW.json", "w") as f:
                json.dump({"clean": clean, "poisoned": poisoned}, f)
            print(f"  world {w} done ({time.perf_counter()-t0:.0f}s)", flush=True)
        with open("CMB_RP0_RAW.json", "w") as f:
            json.dump({"clean": clean, "poisoned": poisoned}, f)
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
               "preregistration": "CMB_RP0_PREREGISTRATION.md v0.1 + A1 + A2",
               "builder": "Claude", "auditor": "a different model, named by the owner",
               "worlds": list(worlds), "seeds": list(SEEDS),
               "frozen_params": {n: globals()[n] for n in FROZEN_NAMES},
               "summary": summ, "clean": clean, "poisoned": poisoned,
               "compute": {"gpu": torch.cuda.get_device_name(0), "cuda": torch.version.cuda,
                           "torch": torch.__version__, "capability": f"{p.major}.{p.minor}",
                           "peak_vram_bytes": int(torch.cuda.max_memory_allocated()),
                           "wall_s": round(time.perf_counter() - t0, 2)},
               "claim_note": ("Tests the CMB as a replay SELECTOR only. Topic is 100% separable "
                              "from the semantic vector and the trajectory carries no topic "
                              "information, so this says NOTHING about CAS geometry as a "
                              "feature.")}
    receipt["determinism"] = {"content_hash": hashlib.sha256(
        json.dumps(summ, sort_keys=True).encode()).hexdigest()}
    with open(out, "w") as f:
        json.dump(receipt, f, indent=1, sort_keys=True)

    s = summ
    print(f"\nCAPABILITY: {s['capability_status']}  | {s['capability_reason']}")
    print(f"SAFETY    : {s['safety_status']}  | {s['safety_reason']}")
    print(f"\ngates: forgetting_exists={s['gates']['forgetting_exists']} "
          f"(NO_REPLAY {s['gates']['no_replay_forgetting']:.4f})  "
          f"oracle_helps={s['gates']['oracle_helps']} "
          f"(ORACLE {s['gates']['oracle_forgetting']:.4f})")
    print(f"\n{'arm':>18}{'forget CLEAN':>14}{'final acc':>11}{'underfill':>11}"
          f"{'poison in':>11}{'forget POIS':>13}{'acc POIS':>10}")
    for a in ARMS:
        print(f"{a:>18}{s['clean_forgetting'][a]:>14.4f}{s['clean_final_acc'][a]:>11.4f}"
              f"{s['clean_underfilled'][a]:>11.1f}{s['safety']['poison_ingested'][a]:>11.2f}"
              f"{s['safety']['forgetting_under_poison'][a]:>13.4f}"
              f"{s['safety']['final_acc_under_poison'][a]:>10.4f}")
    print("\nCMB_AUTHORIZED forgets less than:")
    for k, v in s["capability"].items():
        if v["mean_delta"] is not None:
            print(f"   {k:>18}  delta {v['mean_delta']:+.4f}  "
                  f"{v['worlds_positive']}/{v['n']}  win={v['win']}")
    print("\nHASH:", receipt["determinism"]["content_hash"][:16],
          f" wall {receipt['compute']['wall_s']}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
