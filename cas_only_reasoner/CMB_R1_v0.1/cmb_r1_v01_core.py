# cmb_r1_v01_core.py — RGM-0.1 machinery (owner-authorized correction round; spec
# CMB_R1_SPEC_RGM01_v0_1.md frozen before first run). Mechanism name (binding):
# BOUNDED_ACTIVATION_PROPAGATION. Reuses the frozen v0.1 primitives; adds propagation
# variants, real generic role geometry, split echo configs, and per-query efficiency counts.
import os, sys, time, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cmb_r1_core as K

ROLE = {0: 4, 1: 4, 4: 4, 5: 4, 7: 4, 2: 1, 3: 1, 6: 2, 8: 0, 9: 3}  # TRIGGER/ASSESS/DECOMPOSE/OUTCOME/STATE

def role_traj(traj):
    return [ROLE[o] for o in traj]

def build_generic_geometry(memories, rng):
    """Real generic geometry: coherent 5-role event coarsening (many-to-one — deliberately
    loses the 2-vs-3 CAS distinction). Query maps by the same coarsening. Links rebuilt by
    role-trajectory similarity with the SAME top-3 + 1-random symmetrized procedure."""
    for m in memories.values():
        rt = role_traj(m["trajectory"])
        m["role_trajectory"] = rt
        m["role_profile"] = K.profile_of(rt)
    ids = sorted(memories)
    links = {}
    for a in ids:
        best = [(K.traj_sim(memories[a]["role_trajectory"], memories[b]["role_trajectory"]), b)
                for b in ids if b != a]
        best.sort(key=lambda x: (-x[0], x[1]))
        ls = set(b for _, b in best[:3])
        ls.add(rng.choice(ids))
        ls.discard(a)
        links[a] = sorted(ls)
    for a in ids:
        for b in links[a]:
            if a not in links[b] and b != a:
                links[b] = sorted(links[b] + [a])
    return links

def adj_from_links(links):
    adj = {}
    for mid, ls in links.items():
        adj[mid] = [(l, 1.0 / len(ls)) for l in sorted(ls)] if ls else []
    return adj

def propagate_variant(adj, seed_scores, memories, mode, depth, damping, gamma, topk, root_aware):
    """mode: 'recurrent' a'=(1-d)a+gWa (v0.1 engine) | 'max' best-first max expansion |
    'sum' additive message passing (no persistence decay; seeds keep their seed baseline).
    Identical seeds/graph/depth/budget semantics across variants."""
    a = dict(seed_scores)
    activated = set(seed_scores)
    edge_evals, steps = 0, 0
    for _ in range(depth):
        cand = {}
        for mid, amp in a.items():
            for nb, w in adj.get(mid, []):
                edge_evals += 1
                msg = gamma * w * amp
                if mode == "max":
                    if msg > cand.get(nb, -1e18):
                        cand[nb] = msg
                else:
                    cand[nb] = cand.get(nb, 0.0) + msg
        if mode == "recurrent":
            new = {mid: (1.0 - damping) * amp for mid, amp in a.items()}
            for nb, v in cand.items():
                new[nb] = new.get(nb, 0.0) + v
        else:
            new = dict(cand)
            for mid, amp in seed_scores.items():
                if mid in new:
                    new[mid] = max(new[mid], amp) if mode == "max" else new[mid] + amp
                else:
                    new[mid] = amp
        items = sorted(new.items(), key=lambda x: (-x[1], x[0]))
        if root_aware and memories is not None:
            kept, seen = [], set()
            for mid, v in items:
                r = memories[mid]["provenance_root_id"]
                if r in seen:
                    continue
                seen.add(r)
                kept.append((mid, v))
                if len(kept) >= topk:
                    break
            a = dict(kept)
        else:
            a = dict(items[:topk])
        activated |= set(a)
        steps += 1
    return a, activated, edge_evals, steps

def arm_prop(memories, adj, q, field="cas", mode="recurrent", damping=K.DAMPING, gamma=K.GAMMA,
             depth=K.DEPTH, topk=K.TOPK_WAVE, seed_root_dedup=True, budget_root=True,
             verify_root_dedup=True, coherence=True, mutant_no_prop=False,
             mutant_order_insensitive=False, mutant_static_zeroed=False):
    """Generalized bounded-activation-propagation arm. field: 'cas'|'role'. Verifier switches
    are INDEPENDENT (v0.1 bundled them — the audit's attribution defect)."""
    traj_f = "role_trajectory" if field == "role" else "trajectory"
    prof_f = "role_profile" if field == "role" else "profile"
    q_key = role_traj(q["q_traj"]) if field == "role" else q["q_traj"]
    qprof = K.profile_of(q_key)
    tsim = K.traj_sim_order_insensitive if mutant_order_insensitive else K.traj_sim
    cheap = {}
    for mid, m in memories.items():
        g = K.profile_cos(qprof, m[prof_f]) if not mutant_static_zeroed else 0.0
        cheap[mid] = K.W_SEM * K._cos(q["q_sem"], m["semantic"]) + K.W_GEO * g
    seeds_all = sorted(cheap.items(), key=lambda x: (-x[1], x[0]))[:K.SEED_K]
    if seed_root_dedup:
        rep = {}
        for mid, sc in seeds_all:
            r = memories[mid]["provenance_root_id"]
            if r not in rep or sc > rep[r][1]:
                rep[r] = (mid, sc)
        seed_scores = {mid: sc for mid, sc in rep.values()}
    else:
        seed_scores = dict(seeds_all)
    if mutant_no_prop:
        act, activated, edge_evals, steps = dict(seed_scores), set(seed_scores), 0, 0
    else:
        act, activated, edge_evals, steps = propagate_variant(
            adj, seed_scores, memories, mode, depth, damping, gamma, topk, budget_root)
    resonant = sorted(activated)
    scored = [(mid, tsim(q_key, memories[mid][traj_f])) for mid in resonant]
    mx_act = max(act.values()) or 1.0
    cvals = [cheap[mid] for mid in resonant] or [0.0]
    tvals = [s for _, s in scored] or [0.0]
    lo_c, hi_c, lo_t, hi_t = min(cvals), max(cvals), min(tvals), max(tvals)
    final = {}
    for mid, tsc in scored:
        final[mid] = (K.FINAL_CHEAP * K._nz(cheap[mid], lo_c, hi_c) +
                      K.FINAL_TRAJ * K._nz(tsc, lo_t, hi_t) +
                      K.FINAL_ACT * K._nz(act.get(mid, 0.0), 0.0, mx_act))
    ranked = K._ranked(final)
    verified = []
    if verify_root_dedup or coherence:
        seen_roots = set()
        for mid, sc in ranked:
            if verify_root_dedup:
                r = memories[mid]["provenance_root_id"]
                if r in seen_roots:
                    continue
            if coherence:
                mkey = memories[mid][traj_f]
                ct = tsim(q_key, mkey)
                if q.get("q_ctx") is not None and memories[mid].get("context") is not None:
                    coh = 0.5 * ct + 0.5 * K._cos(q["q_ctx"], memories[mid]["context"])
                else:
                    coh = ct
                if coh < K.TAU_COH:
                    continue
            if verify_root_dedup:
                seen_roots.add(memories[mid]["provenance_root_id"])
            verified.append((mid, sc))
            if len(verified) >= 10:
                break
    else:
        verified = ranked[:10]
    met = {"expensive_evals": len(scored), "edge_evals": edge_evals,
           "activated": len(activated), "prop_steps": steps}
    return ranked, verified, met

def echo_attack(memories, rng, k, kind):
    """Harder echo attacks. kind: 'near_miss' (copies = adjacent transposition of the true
    trajectory, lev 1 — sits at the TAU_COH boundary) | 'overlap' (2 false roots x 10 copies)."""
    import cmb_r1_core as KK
    ids = sorted(m for m in memories if memories[m]["family"] == "BASE")
    while True:
        T = memories[ids[rng.randrange(len(ids))]]
        if len(T["trajectory"]) >= 4:
            break
    true_ids = []
    for j in range(3):
        pid = "nmT%d_%d" % (k, j) if kind == "near_miss" else "ovT%d_%d" % (k, j)
        memories[pid] = K._mk_memory(pid, K._normalize([T["semantic"][d] + rng.gauss(0, 0.10)
                                  for d in range(K.SEM_DIM)]), list(T["trajectory"]),
                                  "r%sT%d_%d" % (kind[:2], k, j), "s%sT%d_%d" % (kind[:2], k, j),
                                  T["topic"], "ECHO_ATTACK", "CORRECT")
        true_ids.append(pid)
    false_ids, roots = [], ("roF%d_a" % k,) if kind == "near_miss" else ("roF%d_a" % k, "roF%d_b" % k)
    per_root = 20 if kind == "near_miss" else 10
    for ri, root in enumerate(roots):
        for j in range(per_root):
            pid = "%sF%d_%d_%d" % (kind[:2], k, ri, j)
            if kind == "near_miss":
                # ONE substituted operation (lev 1): sim = 1 - 1/len = 0.75..0.833, i.e. AT the
                # TAU_COH boundary. (An adjacent swap is lev 2 — never reaches the boundary.)
                ftraj = list(T["trajectory"])
                i = rng.randrange(len(ftraj))
                ftraj[i] = (ftraj[i] + 1) % 10
            else:
                ftraj = [T["trajectory"][-1]] + T["trajectory"][:-1]
            memories[pid] = K._mk_memory(pid, K._normalize([T["semantic"][d] + rng.gauss(0, 0.03)
                                      for d in range(K.SEM_DIM)]), ftraj, root,
                                      "s%sF%d_%d" % (kind[:2], k, ri), T["topic"],
                                      "ECHO_ATTACK", "WRONG")
            false_ids.append(pid)
    for grp in (true_ids, false_ids):
        for a in grp:
            memories[a]["links"] = sorted(x for x in grp if x != a)
    qsem = K._normalize([T["semantic"][d] + rng.gauss(0, 0.04) for d in range(K.SEM_DIM)])
    return {"q_sem": qsem, "q_traj": list(T["trajectory"]), "targets": true_ids,
            "distractors": false_ids, "false_id": false_ids[0], "family": "ECHO_ATTACK",
            "q_ctx": None}
