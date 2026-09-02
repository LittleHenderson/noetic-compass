"""RGM-0.2 runner -- items 1-4. Items 5-6 are NOT built (gated on admission safety passing).

Frozen design: RGM_02_PREREGISTRATION.md v0.1. Owner directive 2026-09-02.
Builder: Claude. Auditor: a different model. Conflict of interest declared in prereg section 0.

  item 1  false near-match admission        -> two-tier verifier, relative + consistency
  item 2  retrieved vs authorized           -> two tiers, ambiguity DOWNGRADES
  item 3  keep the matched control matched  -> D and E get the IDENTICAL new verifier
  item 4  new independent memory worlds     -> disjoint seeds + a mechanism-free gate FIRST

CPU by design: this bench is string similarity and small graph algebra, with no neural
inference, so the GPU-only compute law does not apply. It says so in the receipt.
"""
import hashlib
import json
import os
import random
import sys
import time
import traceback

_HERE = os.path.dirname(os.path.abspath(__file__))
for _rel in ("../CMB_R1_v0.1", "../SHORTCUT_GATE_v0_1"):
    _d = os.path.join(_HERE, _rel)
    sys.path.insert(0, _d if os.path.isdir(_d) else _HERE)
sys.path.insert(0, _HERE)
import cmb_r1_core as K                                              # noqa: E402
import cmb_r1_v02_core as V2                                         # noqa: E402
from cmb_r1_v01_core import arm_prop, build_generic_geometry, adj_from_links, echo_attack  # noqa: E402

VERSION = "rgm_0_2_v0.1"

# ---- item 4: NEW independent worlds. RGM-0/0.1 used w = 0..19 -> K.SEED 20260901..20279901.
# These are disjoint by construction and are asserted so at runtime.
WORLDS = tuple(range(500, 512))                 # 12 new worlds
LEGACY_SEEDS = {20260901 + 1000 * w for w in range(0, 20)}
BASE_SEED = 20260901
RANKED = K.RANKED_FAMILIES
ATTACKS_PER_WORLD = 10

# D and E differ ONLY in the geometry field and its link graph. Everything else is identical.
ARM_CFG = dict(mode="recurrent", damping=0.3, gamma=0.5, depth=3, topk=20)


# ---------------------------------------------------------------- item 4: the gate


def mechanism_free_gate(memories, queries, adj):
    """A mechanism-free baseline adapted to THIS bench.

    The five-depth shortcut gate assumes a cue NODE and ranks graph neighbours of it. These
    queries carry vectors, not a cue node, so one-hop / two-hop have no referent here. The
    depths that DO apply are carried over, and two bench-native ones are added. Stated
    plainly because the gate's own README says: if a mechanism can see a depth the gate does
    not measure, add that depth BEFORE running the mechanism.

      semantic_only   rank by cos(q_sem, memory.semantic) -- no geometry, no propagation
      popularity      rank by graph degree, IDENTICAL for every query: uses no query
                      information at all. Anything it scores is answerable without reading
                      the question.
      answer_set      is the target SET recoverable from the graph alone (degree fingerprint)?
    """
    deg = {mid: len(adj.get(mid, ())) for mid in memories}
    pop_rank = sorted(deg, key=lambda m: (-deg[m], m))
    out, all_targets = {}, set()
    for fam in RANKED:
        sem_mrr, pop_mrr, n = 0.0, 0.0, 0
        for q in queries.get(fam, []):
            all_targets |= set(q["targets"])
            sem = sorted(((mid, K._cos(q["q_sem"], m["semantic"]))
                          for mid, m in memories.items()), key=lambda x: (-x[1], x[0]))
            sem_mrr += K.score_ranked_family(sem, q)["mrr"]
            pop_mrr += K.score_ranked_family([(m, 0.0) for m in pop_rank], q)["mrr"]
            n += 1
        if n:
            out[fam] = {"semantic_only_mrr": sem_mrr / n, "popularity_mrr": pop_mrr / n, "n": n}
    degs = sorted({deg[m] for m in all_targets}) if all_targets else []
    exact = False
    for d in degs:
        pred = {m for m in memories if deg[m] == d}
        if pred == all_targets:
            exact = True
            break
    out["answer_set_recoverable_from_graph"] = bool(exact)
    out["n_targets"] = len(all_targets)
    return out


# ---------------------------------------------------------------- one world


def run_world(w):
    seed = BASE_SEED + 1000 * w
    assert seed not in LEGACY_SEEDS, f"world seed {seed} was used by RGM-0/0.1"
    K.SEED = seed
    rng = random.Random(900000 + w)
    memories, topics, marginals = K.build_corpus()
    queries = K.build_queries(memories, topics)
    K.assign_generic_geometry(memories, marginals)
    role_links = build_generic_geometry(memories, rng)
    adj_cas = K.build_adjacency(memories)
    adj_role = adj_from_links(role_links)
    res = {"world": w, "seed": seed, "arms": {}, "echo": {}}

    # ---- item 4: the gate runs BEFORE any arm is scored ----------------------------
    res["mechanism_free_gate"] = mechanism_free_gate(memories, queries, adj_cas)

    # ---- item 3: D and E, IDENTICAL verifier, differing only in geometry -----------
    for arm, field, adj in (("D_FULL_CAS", "cas", adj_cas),
                            ("E_GENERIC_GEOMETRY", "role", adj_role)):
        by_fam = {}
        for fam in RANKED:
            r_mrr = a_mrr = r_top1 = a_top1 = 0.0
            n_auth_empty = 0
            qs = queries.get(fam, [])
            for q in qs:
                ranked, _v01, _met = arm_prop(memories, adj, q, field=field, **ARM_CFG)
                retrieved, authorized, _d = V2.verify_two_tier(memories, q, ranked)
                sr = K.score_ranked_family(retrieved, q)
                sa = K.score_ranked_family(authorized, q)
                r_mrr += sr["mrr"]; a_mrr += sa["mrr"]
                r_top1 += sr["top1"]; a_top1 += sa["top1"]
                n_auth_empty += int(not authorized)
            n = max(len(qs), 1)
            by_fam[fam] = {"retrieved_mrr": r_mrr / n, "authorized_mrr": a_mrr / n,
                           "retrieved_top1": r_top1 / n, "authorized_top1": a_top1 / n,
                           "authorized_empty_rate": n_auth_empty / n, "n": len(qs)}
        res["arms"][arm] = by_fam

    # ---- items 1-2: the three echo attacks, old admission vs two-tier ---------------
    for kind, base in (("near_miss", 900), ("overlap", 950)):
        acc = {k: 0 for k in ("v01_false", "v01_true", "ret_false", "ret_true",
                              "auth_false", "auth_true", "n", "auth_empty")}
        for k in range(ATTACKS_PER_WORLD):
            q = echo_attack(memories, rng, base + k, kind)
            TRUE, FALSE = set(q["targets"]), set(q["distractors"])
            ranked, v01, _m = K.arm_d(memories, adj_cas, q)
            retrieved, authorized, _d = V2.verify_two_tier(memories, q, ranked)
            for mid, _ in v01:
                acc["v01_false"] += mid in FALSE; acc["v01_true"] += mid in TRUE
            for mid, _ in retrieved:
                acc["ret_false"] += mid in FALSE; acc["ret_true"] += mid in TRUE
            for mid, _ in authorized:
                acc["auth_false"] += mid in FALSE; acc["auth_true"] += mid in TRUE
            acc["auth_empty"] += int(not any(m in TRUE or m in FALSE for m, _ in authorized))
            acc["n"] += 1
        res["echo"][kind] = acc

    # classic ECHO family, from the corpus itself
    acc = {k: 0 for k in ("v01_false", "v01_true", "ret_false", "ret_true",
                          "auth_false", "auth_true", "n", "auth_empty")}
    for q in queries.get("ECHO", []):
        TRUE, FALSE = set(q["targets"]), set(q["distractors"])
        ranked, v01, _m = K.arm_d(memories, adj_cas, q)
        retrieved, authorized, _d = V2.verify_two_tier(memories, q, ranked)
        for mid, _ in v01:
            acc["v01_false"] += mid in FALSE; acc["v01_true"] += mid in TRUE
        for mid, _ in retrieved:
            acc["ret_false"] += mid in FALSE; acc["ret_true"] += mid in TRUE
        for mid, _ in authorized:
            acc["auth_false"] += mid in FALSE; acc["auth_true"] += mid in TRUE
        acc["auth_empty"] += int(not any(m in TRUE or m in FALSE for m, _ in authorized))
        acc["n"] += 1
    res["echo"]["classic"] = acc
    return res


# ---------------------------------------------------------------- aggregate + status


def summarize(worlds):
    def esum(kind, key):
        return sum(w["echo"][kind][key] for w in worlds)

    echo = {kind: {k: esum(kind, k) for k in worlds[0]["echo"][kind]}
            for kind in ("near_miss", "overlap", "classic")}

    # item 3: D - E per family, on BOTH tiers, un-pooled
    geo = {}
    for fam in RANKED:
        for tier in ("retrieved_mrr", "authorized_mrr"):
            d = [w["arms"]["D_FULL_CAS"][fam][tier] for w in worlds]
            e = [w["arms"]["E_GENERIC_GEOMETRY"][fam][tier] for w in worlds]
            delta = [a - b for a, b in zip(d, e)]
            geo.setdefault(tier, {})[fam] = {
                "D": sum(d) / len(d), "E": sum(e) / len(e),
                "delta": sum(delta) / len(delta),
                "worlds_positive": sum(1 for x in delta if x > 0), "n": len(delta)}

    # drop-one robustness: the defect my audit raised against RGM-0.1's resonance gate was a
    # pooled headline that one family dominated. Do not repeat it.
    drop_one = {}
    for tier in ("retrieved_mrr", "authorized_mrr"):
        per_fam = [geo[tier][f]["delta"] for f in RANKED]
        overall = sum(per_fam) / len(per_fam)
        worst = min((sum(x for i, x in enumerate(per_fam) if i != j) / (len(per_fam) - 1))
                    for j in range(len(per_fam)))
        drop_one[tier] = {"all_families": overall, "worst_drop_one": worst,
                          "survives_drop_one": bool(worst > 0)}

    gate = {}
    for fam in RANKED:
        sem = [w["mechanism_free_gate"][fam]["semantic_only_mrr"] for w in worlds
               if fam in w["mechanism_free_gate"]]
        pop = [w["mechanism_free_gate"][fam]["popularity_mrr"] for w in worlds
               if fam in w["mechanism_free_gate"]]
        if sem:
            gate[fam] = {"semantic_only_mrr": sum(sem) / len(sem),
                         "popularity_mrr": sum(pop) / len(pop),
                         "D_authorized_mrr": geo["authorized_mrr"][fam]["D"],
                         "D_beats_semantic_only":
                             bool(geo["authorized_mrr"][fam]["D"] > sum(sem) / len(sem))}
    gate["answer_set_recoverable_any_world"] = any(
        w["mechanism_free_gate"]["answer_set_recoverable_from_graph"] for w in worlds)

    # ---- status ------------------------------------------------------------------
    nm = echo["near_miss"]
    admission_repaired = (nm["auth_false"] == 0 and nm["auth_true"] > 0
                          and echo["classic"]["auth_false"] == 0
                          and echo["overlap"]["auth_false"] == 0)
    gate_clean = (not gate["answer_set_recoverable_any_world"]
                  and all(gate[f]["popularity_mrr"] < 0.10 for f in RANKED if f in gate))

    if not gate_clean:
        status = "STATUS_NOT_EMITTED"
        reason = "MECHANISM_FREE_GATE_FAILED"
    elif admission_repaired:
        status, reason = "ADMISSION_SAFETY_REPAIRED", None
    else:
        status, reason = "ADMISSION_SAFETY_NOT_REPAIRED", (
            f"near-miss still reaches AUTHORIZED: {nm['auth_false']} false authorized")

    # RENAMED by owner ratification 2026-09-02, on GLM audit finding 2.
    # The old name, GENERIC_GEOMETRY_ADVANTAGE_SUPPORTED, was DIRECTION-AMBIGUOUS: it is a
    # drop-one aggregate of D minus E, and it survived only because TWO families win big while
    # THREE lose small. Read alone it says "CAS geometry beats the generic control", which is
    # false on 3 of the 5 families measured. The new name states the direction.
    #   old -> new  (mapping preserved so the committed receipt, which GLM reproduced
    #                byte-identically, remains readable and is NOT rewritten)
    #   GENERIC_GEOMETRY_ADVANTAGE_SUPPORTED     -> CAS_GEOMETRY_HELPS_COMPOSITION_AND_CORROBORATION_ONLY
    #   GENERIC_GEOMETRY_ADVANTAGE_NOT_SUPPORTED -> CAS_GEOMETRY_NO_ADVANTAGE_OVER_GENERIC_CONTROL
    geo_status = ("CAS_GEOMETRY_HELPS_COMPOSITION_AND_CORROBORATION_ONLY"
                  if drop_one["authorized_mrr"]["survives_drop_one"]
                  else "CAS_GEOMETRY_NO_ADVANTAGE_OVER_GENERIC_CONTROL")

    return {"echo": echo, "geometry_by_family": geo, "geometry_drop_one": drop_one,
            "mechanism_free_gate": gate, "status": status, "reason": reason,
            "generic_geometry_status": geo_status,
            # Owner ruling 2026-09-02: the rename is ratified but MUST REMAIN BENCH-SCOPED.
            # "only" means "among the five RGM-0.2 families tested"; it must never be read as
            # "CAS geometry can only ever help those two functions anywhere".
            "status_scope": "RGM-0.2_SYNTHETIC_BENCHMARK_FAMILIES",
            "universal_geometry_superiority": False,
            "generic_geometry_status_legacy_name": (
                "GENERIC_GEOMETRY_ADVANTAGE_SUPPORTED"
                if drop_one["authorized_mrr"]["survives_drop_one"]
                else "GENERIC_GEOMETRY_ADVANTAGE_NOT_SUPPORTED"),
            "items_5_6": "NOT BUILT -- gated on admission safety passing",
            "escalate_to_owner": status == "STATUS_NOT_EMITTED"}


def main(worlds=WORLDS, out="RGM02_RECEIPT.json"):
    t0 = time.perf_counter()
    ws = []
    try:
        for w in worlds:
            ws.append(run_world(w))
            print(f"  world {w} done ({time.perf_counter()-t0:.0f}s)", flush=True)
        with open("RGM02_RAW.json", "w") as f:           # flush BEFORE the receipt
            json.dump(ws, f)
        print("RAW FLUSHED to RGM02_RAW.json")
        summ = summarize(ws)
    except Exception:
        with open(out, "w") as f:
            json.dump({"FAILED": True, "traceback": traceback.format_exc(),
                       "partial": ws}, f, indent=1)
        traceback.print_exc()
        return 2

    receipt = {
        "project": "RGM-0.2 admission safety and matched-control repair",
        "version": VERSION,
        "preregistration": "RGM_02_PREREGISTRATION.md v0.1",
        "builder": "Claude", "auditor": "a different model, named by the owner",
        "conflict_of_interest": "Claude audited RGM-0/0.1 and built RGM-0.2; see prereg 0",
        "worlds": list(worlds), "n_worlds": len(worlds),
        "legacy_seeds_excluded": sorted(LEGACY_SEEDS),
        "frozen_params": {"TAU_FLOOR": V2.TAU_FLOOR, "TAU_AUTH": V2.TAU_AUTH,
                          "DELTA": V2.DELTA, "CONSISTENCY": V2.CONSISTENCY,
                          "TAU_COH_legacy": K.TAU_COH, "arm_cfg": ARM_CFG,
                          "attacks_per_world": ATTACKS_PER_WORLD},
        "summary": summ, "worlds_raw": ws,
        "compute": {"device": "cpu", "why": "string similarity and small graph algebra; no "
                                            "neural inference, so the GPU-only law does not apply",
                    "wall_s": round(time.perf_counter() - t0, 2)},
        "claim_note": "No CAS-specific or cognition-general claim is licensed. Items 5-6 not built.",
    }
    receipt["determinism"] = {"content_hash": hashlib.sha256(
        json.dumps(summ, sort_keys=True).encode()).hexdigest()}
    with open(out, "w") as f:
        json.dump(receipt, f, indent=1, sort_keys=True)

    s = summ
    print("\nSTATUS:", s["status"], "| REASON:", s["reason"])
    print("GENERIC GEOMETRY:", s["generic_geometry_status"])
    print("\nECHO ADMISSION (all worlds):")
    print(f"{'attack':>12}{'RGM-0.1 false':>15}{'RETRIEVED false':>17}{'AUTHORIZED false':>18}"
          f"{'AUTHORIZED true':>17}")
    for kind in ("classic", "overlap", "near_miss"):
        e = s["echo"][kind]
        print(f"{kind:>12}{e['v01_false']:>15}{e['ret_false']:>17}{e['auth_false']:>18}"
              f"{e['auth_true']:>17}")
    print("\nITEM 3 -- D vs E with the IDENTICAL verifier (authorized tier):")
    print(f"{'family':>22}{'D':>9}{'E':>9}{'delta':>9}{'worlds+':>9}")
    for fam in RANKED:
        g = s["geometry_by_family"]["authorized_mrr"][fam]
        print(f"{fam:>22}{g['D']:>9.4f}{g['E']:>9.4f}{g['delta']:>+9.4f}"
              f"{g['worlds_positive']:>6}/{g['n']}")
    d1 = s["geometry_drop_one"]["authorized_mrr"]
    print(f"  all families {d1['all_families']:+.4f}   worst drop-one {d1['worst_drop_one']:+.4f}"
          f"   survives={d1['survives_drop_one']}")
    print("\nITEM 4 -- mechanism-free gate:")
    print(f"{'family':>22}{'semantic-only':>15}{'popularity':>12}{'D authorized':>14}{'D beats sem':>13}")
    for fam in RANKED:
        g = s["mechanism_free_gate"][fam]
        print(f"{fam:>22}{g['semantic_only_mrr']:>15.4f}{g['popularity_mrr']:>12.4f}"
              f"{g['D_authorized_mrr']:>14.4f}{str(g['D_beats_semantic_only']):>13}")
    print(f"  answer set recoverable from the graph alone: "
          f"{s['mechanism_free_gate']['answer_set_recoverable_any_world']}")
    print("\nHASH:", receipt["determinism"]["content_hash"][:16],
          f" wall {receipt['compute']['wall_s']}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
