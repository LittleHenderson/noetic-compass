"""CMB-R1 / RGM-0 core: deterministic resonant-geometric-memory simulator.

Development-tier, non-claim-bearing. Pure Python, no neural workload, no model loading.
Every random draw flows through random.Random(frozen seed) so runs are byte-reproducible.
Constants mirror CMB_R1_SPEC_v0_1.md. The builder of this lane may not claim independent
verification of its own work; third-party audit required before any RGM-1 step.
"""
import math, random

SEED = 20260901
N_MEMORIES = 1600
N_TOPICS = 32
SEM_DIM = 32
CTX_DIM = 16
NOISE_SIGMA = 0.15
N_OPS = 10
W_SEM = 0.5
W_GEO = 0.5
SEED_K = 25
DEPTH = 3
DAMPING = 0.3
GAMMA = 0.5
TOPK_WAVE = 20
FINAL_CHEAP, FINAL_TRAJ, FINAL_ACT = 0.45, 0.35, 0.20
NOVELTY_TAU = 0.60
TAU_COH = 0.75
MARGIN = 0.010
NONINF = 0.005
N_PERM = 10000
FAMILY_N = {"LOOKALIKE": 40, "ORDER_MATTERS": 40, "CROSS_DOMAIN": 40,
            "PATTERN_COMPLETION": 40, "NOVELTY": 40, "ECHO": 30, "INDEPENDENT_CORROB": 30}
RANKED_FAMILIES = ["LOOKALIKE", "ORDER_MATTERS", "CROSS_DOMAIN", "PATTERN_COMPLETION",
                   "INDEPENDENT_CORROB"]
TRAJ_SENSITIVE = ["ORDER_MATTERS", "CROSS_DOMAIN", "PATTERN_COMPLETION"]
EFFICIENCY_CAP = 0.25

def _rng(seed):
    return random.Random(seed)

def _normalize(v):
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]

def _cos(a, b):
    return sum(x * y for x, y in zip(a, b))

def _levenshtein(s1, s2):
    if s1 == s2:
        return 0
    prev = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1, 1):
        cur = [i]
        for j, c2 in enumerate(s2, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (c1 != c2)))
        prev = cur
    return prev[-1]

def traj_sim(s1, s2):
    if not s1 and not s2:
        return 1.0
    return 1.0 - _levenshtein(s1, s2) / max(len(s1), len(s2))

def traj_sim_order_insensitive(s1, s2):
    """MUTANT M2 ONLY: bag-of-ops similarity, order destroyed."""
    return traj_sim(sorted(s1), sorted(s2))

def profile_of(traj):
    p = [0.0] * N_OPS
    for op in traj:
        p[op] += 1.0
    n = math.sqrt(sum(x * x for x in p)) or 1.0
    return [x / n for x in p]

def profile_cos(p1, p2):
    return sum(x * y for x, y in zip(p1, p2))

def _sample_traj(rng, length):
    start_pool, mid_pool, end_pool = [8, 7, 0], [2, 3, 6, 4], [9, 5]
    traj = []
    for i in range(length):
        if i == 0:
            traj.append(rng.choice(start_pool))
        elif i == length - 1:
            traj.append(rng.choice(end_pool))
        else:
            traj.append(rng.choice(mid_pool))
    return traj

def _mk_memory(mid, sem, traj, root, source, topic, family, answer=None, ctx=None):
    return {"memory_id": mid, "semantic": sem, "trajectory": traj, "profile": profile_of(traj),
            "topic": topic, "provenance_root_id": root, "source_id": source,
            "verification_status": "VERIFIED", "answer_field": answer, "links": [],
            "family": family, "context": ctx, "generic_trajectory": None,
            "generic_profile": None}

def build_corpus():
    rng = _rng(SEED)
    topics = [_normalize([rng.gauss(0, 1) for _ in range(SEM_DIM)]) for _ in range(N_TOPICS)]
    memories = {}
    for i in range(N_MEMORIES):
        topic = i % N_TOPICS
        sem = _normalize([topics[topic][d] + rng.gauss(0, NOISE_SIGMA) for d in range(SEM_DIM)])
        traj = _sample_traj(rng, rng.randint(3, 6))
        ctx = _normalize([rng.gauss(0, 1) for _ in range(CTX_DIM)])
        memories["m%04d" % i] = _mk_memory("m%04d" % i, sem, traj, "r%04d" % i,
                                           "s%04d" % (i // 4), topic, "BASE", None, ctx)
    ids = sorted(memories.keys())
    for a in ids:
        best = []
        for b in ids:
            if a != b:
                best.append((traj_sim(memories[a]["trajectory"], memories[b]["trajectory"]), b))
        best.sort(key=lambda x: (-x[0], x[1]))
        links = set(b for _, b in best[:3])
        links.add(rng.choice(ids))
        links.discard(a)
        memories[a]["links"] = sorted(links)
    for a in ids:
        for b in list(memories[a]["links"]):
            if a not in memories[b]["links"] and b != a:
                memories[b]["links"] = sorted(memories[b]["links"] + [a])
    marg = [dict() for _ in range(6)]
    for m in memories.values():
        for pos, op in enumerate(m["trajectory"]):
            marg[pos][op] = marg[pos].get(op, 0) + 1
    marginals = [[op for op, c in sorted(d.items()) for _ in range(c)] for d in marg]
    return memories, topics, marginals

def assign_generic_geometry(memories, marginals):
    """Arm E: lengths and per-position marginals preserved, ordered pair structure destroyed."""
    rng = _rng(SEED + 555)

    def pool_at(pos):
        return marginals[min(pos, len(marginals) - 1)]

    for m in memories.values():
        g = []
        for pos in range(len(m["trajectory"])):
            pool = pool_at(pos)
            g.append(pool[rng.randrange(len(pool))])
        m["generic_trajectory"] = g
        m["generic_profile"] = profile_of(g)
    return memories

def corrupt_corpus(memories):
    """Arm F: permute CAS fields among memories. Corpus-level bag preserved exactly;
    per-memory correspondence destroyed (misinformation, not absence)."""
    rng = _rng(SEED + 777)
    ids = sorted(memories.keys())
    perm = ids[:]
    for _ in range(1000):
        rng.shuffle(perm)
        if not any(p == i for p, i in zip(perm, ids)):
            break
    saved = {i: memories[i]["trajectory"] for i in ids}
    for src, dst in zip(perm, ids):
        memories[dst]["trajectory"] = list(saved[src])
        memories[dst]["profile"] = profile_of(saved[src])
    return memories

def build_queries(memories, topics):
    rng = _rng(SEED + 42)
    ids = sorted(memories.keys())
    queries = {}

    def hard_negatives(qtraj, qtopic, exclude, k=2):
        out = []
        for mid in ids:
            m = memories[mid]
            if mid in exclude or m["topic"] != qtopic:
                continue
            if traj_sim(m["trajectory"], qtraj) < 0.34:
                out.append(mid)
            if len(out) >= k:
                break
        return out

    # F1 LOOKALIKE: semantics identical twins, CAS separates
    fam = []
    for t in ids:
        if len(fam) >= FAMILY_N["LOOKALIKE"]:
            break
        T = memories[t]
        if T["trajectory"][0] != 8:
            continue
        look = None
        for b in ids:
            if (b != t and memories[b]["topic"] == T["topic"] and
                    traj_sim(memories[b]["trajectory"], T["trajectory"]) < 0.34 and
                    profile_cos(T["profile"], memories[b]["profile"]) < 0.9):
                look = b
                break
        if look is None:
            continue
        # SPEC CONTRACT: the lookalike is a TRUE semantic twin — its stored semantic vector is
        # replaced by the target's own vector plus independent tiny noise, so semantic-only
        # retrieval cannot separate them and only the CAS key can.
        qsem = _normalize([T["semantic"][d] + rng.gauss(0, 0.01) for d in range(SEM_DIM)])
        memories[look]["semantic"] = _normalize([T["semantic"][d] + rng.gauss(0, 0.01)
                                                 for d in range(SEM_DIM)])
        negs = hard_negatives(T["trajectory"], T["topic"], {t, look})
        fam.append({"q_sem": qsem, "q_traj": list(T["trajectory"]), "targets": [t],
                    "distractors": [look] + negs, "family": "LOOKALIKE", "q_ctx": None})
    queries["LOOKALIKE"] = fam

    # F2 ORDER_MATTERS: distractor trajectory is a permutation (identical static profile)
    fam = []
    for t in ids:
        if len(fam) >= FAMILY_N["ORDER_MATTERS"]:
            break
        T = memories[t]
        if len(T["trajectory"]) < 4:
            continue
        perm = T["trajectory"][:]
        rng.shuffle(perm)
        if perm == T["trajectory"]:
            continue
        perm_id = None
        for b in ids:
            if b != t and memories[b]["trajectory"] == perm:
                perm_id = b
                break
        if perm_id is None:
            pid = "perm%03d" % len(fam)
            memories[pid] = _mk_memory(pid,
                                       _normalize([T["semantic"][d] + rng.gauss(0, 0.03)
                                                   for d in range(SEM_DIM)]),
                                       perm, "rp%03d" % len(fam), "sp%03d" % len(fam),
                                       T["topic"], "ORDER_MATTERS")
            perm_id = pid
        qsem = _normalize([T["semantic"][d] + rng.gauss(0, 0.05) for d in range(SEM_DIM)])
        negs = hard_negatives(T["trajectory"], T["topic"], {t, perm_id})
        fam.append({"q_sem": qsem, "q_traj": list(T["trajectory"]), "targets": [t],
                    "distractors": [perm_id] + negs, "family": "ORDER_MATTERS", "q_ctx": None})
    queries["ORDER_MATTERS"] = fam

    # F3 CROSS_DOMAIN: target in a distant topic, same full trajectory
    fam = []
    for t in ids:
        if len(fam) >= FAMILY_N["CROSS_DOMAIN"]:
            break
        T = memories[t]
        far = None
        for b in ids:
            if (b != t and memories[b]["topic"] != T["topic"] and
                    _cos(memories[b]["semantic"], T["semantic"]) < 0.45 and
                    memories[b]["trajectory"] == T["trajectory"]):
                far = b
                break
        if far is None:
            continue
        near = [b for b in ids if memories[b]["topic"] == T["topic"] and b != t and
                traj_sim(memories[b]["trajectory"], T["trajectory"]) < 0.5][:2]
        if len(near) < 1:
            continue
        qsem = _normalize([T["semantic"][d] + rng.gauss(0, 0.10) for d in range(SEM_DIM)])
        negs = hard_negatives(T["trajectory"], T["topic"], {t, far} | set(near))
        fam.append({"q_sem": qsem, "q_traj": list(T["trajectory"]), "targets": [t, far],
                    "distractors": near + negs, "family": "CROSS_DOMAIN", "q_ctx": None})
    queries["CROSS_DOMAIN"] = fam

    # F4 PATTERN_COMPLETION (two-topic multihop): fragment holders (topic A, semantically near
    # the query) carry the trajectory prefix; the true completion T sits in topic B (semantically
    # far) and is reachable ONLY through the fragment holders' links. Static ranking cannot
    # surface T; resonance propagation can.
    fam = []
    topic_pairs = [(a, b) for a in range(N_TOPICS) for b in range(N_TOPICS) if a != b]
    for k in range(FAMILY_N["PATTERN_COMPLETION"]):
        t = ids[rng.randrange(len(ids))]
        T = memories[t]
        if len(T["trajectory"]) < 4:
            continue
        prefix = T["trajectory"][:2]
        ta, tb = topic_pairs[k % len(topic_pairs)]
        frag_ids = []
        for j in range(3):
            pid = "frag%d_%d" % (k, j)
            ftraj = prefix + [_sample_traj(rng, 2)[0]]
            sem = _normalize([topics[ta][d] + rng.gauss(0, NOISE_SIGMA) for d in range(SEM_DIM)])
            memories[pid] = _mk_memory(pid, sem, ftraj, "rf%d_%d" % (k, j),
                                       "sf%d_%d" % (k, j), ta, "PATTERN_COMPLETION")
            frag_ids.append(pid)
        qsem = _normalize([topics[ta][d] + rng.gauss(0, 0.05) for d in range(SEM_DIM)])
        qctx = _normalize([rng.gauss(0, 1) for _ in range(CTX_DIM)])
        memories[t]["context"] = qctx[:]
        for f in frag_ids:
            memories[f]["links"] = sorted(set(memories[f]["links"] + [t]))
            memories[t]["links"] = sorted(set(memories[t]["links"] + [f]))
        # distractors: topic-A memories whose trajectories do NOT extend the prefix
        near = [b for b in ids if memories[b]["topic"] == ta and b not in frag_ids and
                memories[b]["trajectory"][:2] != prefix][:3]
        if len(near) < 2:
            continue
        fam.append({"q_sem": qsem, "q_traj": prefix, "targets": [t],
                    "distractors": near, "fragments": frag_ids, "family": "PATTERN_COMPLETION",
                    "q_ctx": qctx})
    queries["PATTERN_COMPLETION"] = fam

    # F5 NOVELTY: unused topic prototype and atypical trajectory pattern; correct behavior is
    # flagging a lacuna.
    fam = []
    attempts = 0
    while len(fam) < FAMILY_N["NOVELTY"] and attempts < 5000:
        attempts += 1
        proto = _normalize([rng.gauss(0, 1) for _ in range(SEM_DIM)])
        clash = max((_cos(proto, m["semantic"]) for m in memories.values()), default=0.0)
        if clash > 0.55:
            continue
        qsem = _normalize([proto[d] + rng.gauss(0, 0.05) for d in range(SEM_DIM)])
        qtraj = [1, 4, 1, 4, 1][:rng.randint(3, 5)]
        fam.append({"q_sem": qsem, "q_traj": qtraj, "targets": [], "distractors": [],
                    "family": "NOVELTY", "q_ctx": None})
    queries["NOVELTY"] = fam

    # F6 ECHO: 20 copies (one provenance root) of a false memory vs 3 independent true memories.
    # The false memory shares the query's topic AND static profile (rotated trajectory) but has
    # the wrong ORDER — the echo defense must be structural (root budget, root dedup, coherence),
    # never status filtering.
    fam = []
    for k in range(FAMILY_N["ECHO"]):
        T = memories[ids[rng.randrange(len(ids))]]
        if len(T["trajectory"]) < 4:
            continue
        true_ids = []
        for j in range(3):
            pid = "echoT%d_%d" % (k, j)
            memories[pid] = _mk_memory(pid,
                                       _normalize([T["semantic"][d] + rng.gauss(0, 0.10)
                                                   for d in range(SEM_DIM)]),
                                       list(T["trajectory"]), "reT%d_%d" % (k, j),
                                       "seT%d_%d" % (k, j), T["topic"], "ECHO", "CORRECT")
            true_ids.append(pid)
        false_sem = _normalize([T["semantic"][d] + rng.gauss(0, 0.03) for d in range(SEM_DIM)])
        wrong = [T["trajectory"][-1]] + T["trajectory"][:-1]
        false_ids = []
        for j in range(20):
            pid = "echoF%d_%d" % (k, j)
            memories[pid] = _mk_memory(pid, false_sem[:], wrong, "reF%d" % k, "seF%d" % k,
                                       T["topic"], "ECHO", "WRONG")
            false_ids.append(pid)
        for grp in (true_ids, false_ids):
            for a in grp:
                memories[a]["links"] = sorted(x for x in grp if x != a)
        qsem = _normalize([T["semantic"][d] + rng.gauss(0, 0.04) for d in range(SEM_DIM)])
        fam.append({"q_sem": qsem, "q_traj": list(T["trajectory"]), "targets": true_ids,
                    "distractors": false_ids, "false_id": false_ids[0], "family": "ECHO",
                    "q_ctx": None})
    queries["ECHO"] = fam

    # F7 INDEPENDENT_CORROB: 4 independent true memories vs one lone high-semantic distractor
    fam = []
    for k in range(FAMILY_N["INDEPENDENT_CORROB"]):
        T = memories[ids[rng.randrange(len(ids))]]
        if len(T["trajectory"]) < 4:
            continue
        true_ids = []
        for j in range(4):
            pid = "corT%d_%d" % (k, j)
            memories[pid] = _mk_memory(pid,
                                       _normalize([T["semantic"][d] + rng.gauss(0, 0.12)
                                                   for d in range(SEM_DIM)]),
                                       list(T["trajectory"]), "rcT%d_%d" % (k, j),
                                       "scT%d_%d" % (k, j), T["topic"],
                                       "INDEPENDENT_CORROB", "CORRECT")
            true_ids.append(pid)
        rot = [T["trajectory"][-1]] + T["trajectory"][:-1]
        lone = "corL%d" % k
        memories[lone] = _mk_memory(lone,
                                    _normalize([T["semantic"][d] + rng.gauss(0, 0.02)
                                                for d in range(SEM_DIM)]),
                                    rot, "rcL%d" % k, "scL%d" % k, T["topic"],
                                    "INDEPENDENT_CORROB", "WRONG")
        for a in true_ids:
            memories[a]["links"] = sorted(x for x in true_ids if x != a)
        qsem = _normalize([T["semantic"][d] + rng.gauss(0, 0.05) for d in range(SEM_DIM)])
        fam.append({"q_sem": qsem, "q_traj": list(T["trajectory"]), "targets": true_ids,
                    "distractors": [lone], "family": "INDEPENDENT_CORROB", "q_ctx": None})
    queries["INDEPENDENT_CORROB"] = fam
    return queries

def build_adjacency(memories):
    adj = {}
    for mid, m in memories.items():
        links = [l for l in m["links"] if l in memories and l != mid]
        if not links:
            adj[mid] = []
            continue
        w = 1.0 / len(links)
        adj[mid] = [(l, w) for l in sorted(links)]
    return adj

# ---------------- retrieval policies ----------------

def _ranked(scores):
    return sorted(scores.items(), key=lambda x: (-x[1], x[0]))

def arm_a(memories, q):
    return _ranked({mid: _cos(q["q_sem"], m["semantic"]) for mid, m in memories.items()})

def arm_b(memories, q):
    qp = profile_of(q["q_traj"])
    return _ranked({mid: W_SEM * _cos(q["q_sem"], m["semantic"]) +
                    W_GEO * profile_cos(qp, m["profile"])
                    for mid, m in memories.items()})

def arm_c(memories, q, mutant_order_insensitive=False):
    sim = traj_sim_order_insensitive if mutant_order_insensitive else traj_sim
    return _ranked({mid: W_SEM * _cos(q["q_sem"], m["semantic"]) +
                    W_GEO * sim(q["q_traj"], m["trajectory"])
                    for mid, m in memories.items()})

def resonate(adj, seed_scores, memories=None, provenance_aware=True):
    """Bounded propagation a' = BoundedTopK[(1-d)a + g W a]. Refractory is structural
    (no self-loops). Provenance-aware: the per-wave budget spends at most one slot per root."""
    a = dict(seed_scores)
    activated = set(seed_scores)
    edge_evals, steps = 0, 0
    for _ in range(DEPTH):
        cand = {}
        for mid, amp in a.items():
            for nb, w in adj.get(mid, []):
                edge_evals += 1
                cand[nb] = cand.get(nb, 0.0) + GAMMA * w * amp
        new = {mid: (1.0 - DAMPING) * amp for mid, amp in a.items()}
        for nb, v in cand.items():
            new[nb] = new.get(nb, 0.0) + v
        items = sorted(new.items(), key=lambda x: (-x[1], x[0]))
        if provenance_aware and memories is not None:
            kept, seen_roots = [], set()
            for mid, v in items:
                r = memories[mid]["provenance_root_id"]
                if r in seen_roots:
                    continue
                seen_roots.add(r)
                kept.append((mid, v))
                if len(kept) >= TOPK_WAVE:
                    break
            a = dict(kept)
        else:
            a = dict(items[:TOPK_WAVE])
        activated |= set(a)
        steps += 1
    return a, activated, edge_evals, steps

def _nz(v, lo, hi):
    return (v - lo) / (hi - lo) if hi > lo else 0.0

def arm_d(memories, adj, q, geo_mode="cas", provenance_aware=True, use_coherence=True,
          mutant_no_propagation=False):
    """Cheap seed -> bounded (root-aware) propagation -> expensive traj re-score on the
    resonant set -> verifier (root dedup + geometric/contextual coherence quarantine)."""
    cheap = {}
    for mid, m in memories.items():
        gpf = m["generic_profile"] if geo_mode == "generic" else m["profile"]
        g = profile_cos(profile_of(q["q_traj"]), gpf)
        cheap[mid] = W_SEM * _cos(q["q_sem"], m["semantic"]) + W_GEO * g
    seeds_all = sorted(cheap.items(), key=lambda x: (-x[1], x[0]))[:SEED_K]
    top_seed_cheap = seeds_all[0][1] if seeds_all else 0.0
    if provenance_aware:
        rep = {}
        for mid, sc in seeds_all:
            r = memories[mid]["provenance_root_id"]
            if r not in rep or sc > rep[r][1]:
                rep[r] = (mid, sc)
        seed_scores = {mid: sc for mid, sc in rep.values()}
    else:
        seed_scores = dict(seeds_all)
    if mutant_no_propagation:
        act, activated, edge_evals, steps = dict(seed_scores), set(seed_scores), 0, 0
    else:
        act, activated, edge_evals, steps = resonate(adj, seed_scores, memories,
                                                     provenance_aware)
    resonant = sorted(activated)
    scored = []
    for mid in resonant:
        m = memories[mid]
        tf = m["generic_trajectory"] if geo_mode == "generic" else m["trajectory"]
        scored.append((mid, traj_sim(q["q_traj"], tf)))
    mx_act = max(act.values()) or 1.0
    cvals = [cheap[mid] for mid in resonant]
    tvals = [s for _, s in scored] or [0.0]
    lo_c, hi_c = min(cvals), max(cvals)
    lo_t, hi_t = min(tvals), max(tvals)
    final = {}
    for mid, tsc in scored:
        final[mid] = (FINAL_CHEAP * _nz(cheap[mid], lo_c, hi_c) +
                      FINAL_TRAJ * _nz(tsc, lo_t, hi_t) +
                      FINAL_ACT * _nz(act.get(mid, 0.0), 0.0, mx_act))
    ranked = _ranked(final)
    coherence_off = (geo_mode == "generic") or not use_coherence
    if provenance_aware:
        seen_roots, verified = set(), []
        for mid, sc in ranked:
            r = memories[mid]["provenance_root_id"]
            if r in seen_roots:
                continue
            if not coherence_off:
                coh_traj = traj_sim(q["q_traj"], memories[mid]["trajectory"])
                if q.get("q_ctx") is not None and memories[mid].get("context") is not None:
                    coh = 0.5 * coh_traj + 0.5 * _cos(q["q_ctx"], memories[mid]["context"])
                else:
                    coh = coh_traj
                if coh < TAU_COH:
                    continue  # geometric/contextual applicability quarantine
            seen_roots.add(r)
            verified.append((mid, sc))
            if len(verified) >= 10:
                break
    else:
        verified = ranked[:10]
    metrics = {"expensive_evals": len(scored), "edge_evals": edge_evals,
               "prop_steps": steps, "activated": len(activated),
               "seeds": len(seed_scores), "top_seed_cheap": top_seed_cheap}
    return ranked, verified, metrics

def arm_h(memories, q, guard_state):
    if guard_state.get("resonant_empty") or guard_state.get("activation_collapsed"):
        guard_state["firings"] = guard_state.get("firings", 0) + 1
    return arm_b(memories, q)

# ---------------- metrics and statistics ----------------

def score_ranked_family(ranked, q):
    targets = set(q["targets"])
    distractors = set(q["distractors"])
    rank_of_target, top1, recall5, false_recall = None, 0, 0, 0
    for i, (mid, _) in enumerate(ranked[:200], 1):
        if mid in targets and rank_of_target is None:
            rank_of_target = i
        if i == 1 and mid in targets:
            top1 = 1
        if i <= 5 and mid in targets:
            recall5 = 1
        if i <= 3 and mid in distractors:
            false_recall = 1
    return {"top1": top1, "recall5": recall5,
            "mrr": (1.0 / rank_of_target) if rank_of_target else 0.0,
            "false_recall": false_recall, "rank_of_target": rank_of_target or 0}

def paired_permutation(deltas, rng):
    n = len(deltas)
    if n == 0:
        return 1.0
    obs = abs(sum(deltas) / n)
    count = 0
    for _ in range(N_PERM):
        s = 0.0
        for d in deltas:
            s += d if rng.random() < 0.5 else -d
        if abs(s / n) >= obs - 1e-12:
            count += 1
    return count / float(N_PERM)