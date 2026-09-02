"""CMB-P2 -- P8+P9 Controlled Confirmation. One shot.

Frozen design: CMB_P2_PREREGISTRATION.md v0.1. Owner directive 2026-09-02.
Parent commit: 99909e8c79b9283412826fd7658956794247b777 (final CMB-P1 result).

Mechanisms are IMPORTED UNCHANGED from CMB-P0 and CMB-P1. Nothing new is built: this run
exists to give the exploratory P8+P9 combination the two controls it lacked.

GPU only. Fail closed. No CPU fallback branch.

Lesson applied from CMB-P1's first launch, which finished every GPU computation and then lost
all of it to `TypeError: Object of type module is not JSON serializable`:
  * raw results are FLUSHED TO DISK before the receipt is built;
  * frozen_params is built from an explicit whitelist, never `dir()` (note `"P0".isupper()`
    is True, because `0` is uncased -- that is what serialised a module last time);
  * the whole main() path including JSON writing is smoke-tested before launch.
"""
import hashlib
import json
import math
import os
import sys
import time
import traceback

import torch

_HERE = os.path.dirname(os.path.abspath(__file__))
for _rel in ("../CMB_P0_v0_1", "../CMB_P1_v0_1"):
    _d = os.path.join(_HERE, _rel)
    sys.path.insert(0, _d if os.path.isdir(_d) else _HERE)
import cmb_p0 as P0                                              # noqa: E402
import cmb_p1 as P1                                              # noqa: E402
from cmb_p0 import (N_NODES, QUERIES_PER_WORLD, TOPK, build_queries,  # noqa: E402
                    gen, gpu_identity, propagate_channels, propagate_scalar,
                    propagate_two_state, require_cuda)

# ---------------------------------------------------------------- frozen parameters

# NEW, UNTOUCHED worlds. CMB-P0/P1 used ids 0-25; those revealed the promising combination
# and are excluded. A different id yields a different world key and therefore a fresh seed.
DEV_WORLDS = tuple(range(500, 506))
# MOVED 2026-09-02: a verifying agent read worlds 506-512 during the pre-launch review, so
# that range is burned. The freeze sentence "no held-out world has been read" must stay true.
HELDOUT_WORLDS = tuple(range(536, 566))          # 30 worlds, untouched
# 0-25 used by CMB-P0/P1; 500-512 touched during CMB-P2 dev and pre-launch review.
EXCLUDED_WORLDS = tuple(range(0, 26)) + tuple(range(500, 513))

K_SETTINGS = (1, 2, 3, 4)
PRIMARY_K = (2, 3)
FULL_BUDGET = 200                                # the registered propagation budget
DIAG_BUDGET = 10                                 # reported only, decides nothing
SUBSTEP_BUDGETS = (DIAG_BUDGET, FULL_BUDGET)

MARGIN = 0.02
WIN_FRACTION = 0.70
MERGE_MAX = 0.15
CONTAM_MARGIN = 0.05
GATE_HEADROOM_TOP1 = 0.90
GATE_ORACLE_TOP1 = 0.60
GATE_DISTINCT_Q_MIN = 20                         # distinct query rows per world

ARMS = ("P0_SCALAR", "P1_ORACLE_GATE", "P2_INFERRED_TAG", "P3_GENERIC_TWO_STATE",
        "P6_SCALAR_TWO_CHANNEL", "B_PHASE_FREE_CONTENT",
        "P8_ONLY", "P9_ONLY",
        "P8P9_EXACT", "P8P9_PHASE_SHUFFLED", "P8P9_RANDOM_FREQUENCY")

# Explicit whitelist. NEVER dir()-based -- that is what serialised a module in CMB-P1.
FROZEN_PARAM_NAMES = ("MARGIN", "WIN_FRACTION", "MERGE_MAX", "CONTAM_MARGIN",
                      "GATE_HEADROOM_TOP1", "GATE_ORACLE_TOP1", "GATE_DISTINCT_Q_MIN",
                      "FULL_BUDGET", "DIAG_BUDGET")
FROZEN_P1_NAMES = ("P8_OMEGA", "P8_SPECTRAL_INDEX", "MERGE_RAD", "P2_CONTENT_WEIGHT",
                   "B_GATE_CONTENT_S0", "P7_REACH_DEPTH")


# ---------------------------------------------------------------- one world


def score_world(world, q, scores):
    ar = torch.arange(QUERIES_PER_WORLD, device=P0.DEV)
    finite = bool(torch.isfinite(scores).all().item())
    s = scores.clone()
    s[q["seeds"] > 0] = -1e18
    gold = s[ar, q["gold"]].unsqueeze(1)
    rank = (s > gold).sum(dim=1) + (s == gold).sum(dim=1) - 1     # ties count pessimistically
    top = torch.topk(s, TOPK, dim=1).indices
    lab = world["chain_of"][top]
    active = q["active_mask"].gather(1, lab.clamp_min(0))
    return {"top1": (rank == 0).double().mean().item(),
            "recall_at_5": (rank < TOPK).double().mean().item(),
            "cross_chain_contamination":
                ((lab >= 0) & (lab != q["target"].unsqueeze(1)) & active).double().mean().item(),
            "runtime_finite": finite}


def run_world(world_id, k, substeps):
    assert world_id not in EXCLUDED_WORLDS, f"world {world_id} belongs to CMB-P0/P1"
    w = P1.build_world_p1(world_id, k)
    q = build_queries(w)
    ar = torch.arange(QUERIES_PER_WORLD, device=P0.DEV)
    out = {"world_id": world_id, "k_chains": k, "substeps": substeps, "arms": {}}

    def put(name, scores, mfrac=None, gord=None):
        m = score_world(w, q, scores)
        m["merge_fraction"] = mfrac
        m["global_order_parameter"] = gord
        m["device"] = str(scores.device)
        out["arms"][name] = m

    # ---- non-phase arms ----------------------------------------------------------
    scal = propagate_scalar(q["seeds"], w["W"])
    put("P0_SCALAR", scal)

    ch = w["memb"].unsqueeze(0) * q["active_mask"].unsqueeze(-1).to(P0.DT)
    ch[ar, q["target"], q["cue"]] += 1.0
    put("P1_ORACLE_GATE", propagate_channels(ch, w["W"])[ar, q["target"]])

    cluster = P1.infer_clusters_v2(w)
    onehot = torch.zeros((w["pool"], N_NODES), device=P0.DEV, dtype=P0.DT)
    valid = cluster >= 0
    onehot[cluster[valid], valid.nonzero(as_tuple=True)[0]] = 1.0
    ch2 = onehot.unsqueeze(0) * (q["seeds"] > 0).unsqueeze(1).to(P0.DT)
    grp = cluster[q["cue"]].clamp_min(0)
    ch2[ar, grp, q["cue"]] += 1.0
    put("P2_INFERRED_TAG", propagate_channels(ch2, w["W"])[ar, grp],
        mfrac=cluster_merge_fraction(cluster, w, q))

    a3, _ = propagate_two_state(q["seeds"], w["W"])
    put("P3_GENERIC_TWO_STATE", a3)

    cue_seed = torch.zeros_like(q["seeds"])
    cue_seed[ar, q["cue"]] = 1.0
    put("P6_SCALAR_TWO_CHANNEL", scal * propagate_scalar(cue_seed, w["W"]).clamp_min(0.0))

    C = w["content"] @ w["content"].T
    put("B_PHASE_FREE_CONTENT",
        scal * torch.sign(C[q["cue"]] - P1.B_GATE_CONTENT_S0).clamp_min(0.0))

    # ---- three phase runs; every P8P9 variant shares the spectral run ------------
    def phase(omega_kind):
        om = None if omega_kind == "ZERO" else P1.omega_field(w, omega_kind)
        a, th, coh, pair = P1.run_phase_acc(w, q, omega=om, substeps=substeps)
        ef, _ = P1.merge_fraction_from_pairs(P1.endpoint_pair_coherence(th, q, w), q, w)
        tf, _ = P1.merge_fraction_from_pairs(pair, q, w)
        z = (a.to(torch.complex128) * torch.exp(1j * th.to(torch.complex128))).sum(1)
        go = float((z.abs() / a.sum(1).clamp_min(1e-12)).clamp(0, 1).mean().item())
        return a, th, coh, ef, tf, go

    a_s, th_s, coh_s, ef_s, tf_s, go_s = phase("SPECTRAL")
    end_s = torch.cos(th_s - th_s[ar, q["cue"]].unsqueeze(1))
    put("P8_ONLY", a_s * end_s.clamp_min(0), ef_s, go_s)
    put("P8P9_EXACT", a_s * coh_s.clamp_min(0), tf_s, go_s)
    # phase correspondence destroyed; the CUE'S OWN phase is kept as the reference
    perm = torch.randperm(N_NODES, generator=gen(w["key"] + "|p2shuf"), device=P0.DEV)
    put("P8P9_PHASE_SHUFFLED", a_s * coh_s[:, perm].clamp_min(0), tf_s, go_s)
    del th_s, coh_s, end_s

    a_z, th_z, coh_z, ef_z, tf_z, go_z = phase("ZERO")
    put("P9_ONLY", a_z * coh_z.clamp_min(0), tf_z, go_z)
    del th_z, coh_z

    a_r, th_r, coh_r, ef_r, tf_r, go_r = phase("OMEGA_RANDOM")
    put("P8P9_RANDOM_FREQUENCY", a_r * coh_r.clamp_min(0), tf_r, go_r)
    del th_r, coh_r
    return out


def cluster_merge_fraction(cluster, world, q):
    k = world["k_chains"]
    maj = {}
    for ci in range(world["pool"]):
        nodes = (world["memb"][ci] > 0).nonzero(as_tuple=True)[0]
        nodes = nodes[world["chain_of"][nodes] == ci]
        g = cluster[nodes]
        g = g[g >= 0]
        if g.numel():
            maj[ci] = int(torch.mode(g).values.item())
    act = q["active_mask"]
    merged = 0.0
    for qi in range(QUERIES_PER_WORLD):
        on = [c for c in maj if bool(act[qi, c])]
        merged += sum(1 for i, a in enumerate(on) for b in on[i + 1:] if maj[a] == maj[b])
    return merged / QUERIES_PER_WORLD / max(1.0, k * (k - 1) / 2.0)


# ---------------------------------------------------------------- construct validity


def construct_validity():
    """The checks the directive requires BEFORE AWS spend. Dev worlds only."""
    rep = {}
    for k in PRIMARY_K:
        hop_hit = hop_tot = con_hit = con_tot = 0
        distinct = []
        for wid in DEV_WORLDS:
            w = P1.build_world_p1(wid, k)
            q = build_queries(w)
            distinct.append(int(torch.unique(q["seeds"], dim=0).shape[0]))
            # vectorised: one host sync per world instead of one per query
            rows = w["A"][q["cue"]].clone()
            rows[q["seeds"] > 0] = -1.0
            hop_hit += int((rows.argmax(dim=1) == q["gold"]).sum().item())
            hop_tot += QUERIES_PER_WORLD
            C = w["content"][w["cues"]] @ w["content"][w["completions"]].T
            con_hit += int((C.argmax(dim=1) == torch.arange(w["pool"], device=P0.DEV))
                           .sum().item())
            con_tot += w["pool"]
        pool = k + P0.POOL_EXTRA
        rep[k] = {
            "one_hop_argmax_is_gold": hop_hit / hop_tot,
            "one_hop_chance": 1.0 / pool,
            "content_argmax_is_gold": con_hit / con_tot,
            "content_chance": 1.0 / pool,
            "distinct_query_rows_min": min(distinct),
            "gate_no_one_hop": bool(hop_hit / hop_tot <= 1.5 / pool),
            "gate_no_content_leak": bool(con_hit / con_tot <= 1.5 / pool),
            "gate_distinct_q": bool(min(distinct) >= GATE_DISTINCT_Q_MIN),
        }
    return rep


def shuffle_informativeness():
    """Is the phase-shuffle control INFORMATIVE, or does it collapse no matter what?

    A control that always fails proves nothing. This measures the shuffle gap against three
    phase fields of increasing structure, INCLUDING the no-information limit where every phase
    is identical. In that limit cos(delta theta) = 1 everywhere, so shuffling is an exact
    no-op and the control must TIE P0 rather than fall below it.

    DEV worlds only. Persisted in the receipt so the killer control's validity is documented
    in the artifact, not merely asserted.
    """
    rows = []
    for k in PRIMARY_K:
        for label, kind, forced in (("no_structure_limit", "ZERO", True),
                                    ("zero_omega_converged", "ZERO", False),
                                    ("spectral_omega_the_arm", "SPECTRAL", False)):
            p0v, un, sh = [], [], []
            for wid in DEV_WORLDS:
                w = P1.build_world_p1(wid, k)
                q = build_queries(w)
                p0v.append(score_world(w, q, propagate_scalar(q["seeds"], w["W"]))["top1"])
                om = None if kind == "ZERO" else P1.omega_field(w, kind)
                a, th, coh, _pair = P1.run_phase_acc(w, q, omega=om, substeps=FULL_BUDGET)
                if forced:
                    coh = torch.ones_like(coh)
                perm = torch.randperm(N_NODES, generator=gen(w["key"] + "|p2shuf"),
                                      device=P0.DEV)
                un.append(score_world(w, q, a * coh.clamp_min(0))["top1"])
                sh.append(score_world(w, q, a * coh[:, perm].clamp_min(0))["top1"])
            m = lambda x: sum(x) / len(x)
            rows.append({"k": k, "field": label, "p0": m(p0v), "unshuffled": m(un),
                         "shuffled": m(sh), "gap": m(un) - m(sh)})
    return {"note": "the no_structure_limit row must show gap ~0 -- shuffling a uniform phase "
                    "field is an exact no-op, so the control is not a foregone conclusion",
            "rows": rows}


# ---------------------------------------------------------------- statistics


def paired(rs, a, b, key="top1", margin=MARGIN):
    d = [r["arms"][a][key] - r["arms"][b][key] for r in rs
         if r["arms"][a].get(key) is not None and r["arms"][b].get(key) is not None]
    if len(d) < 5:
        return {"mean_delta": None, "worlds_positive": 0, "n": len(d), "win": False}
    mean = sum(d) / len(d)
    pos = sum(1 for x in d if x > 0)
    return {"mean_delta": mean, "worlds_positive": pos, "n": len(d),
            "win": bool(mean > margin and pos >= WIN_FRACTION * len(d))}


def mean_of(rs, arm, key):
    v = [r["arms"][arm][key] for r in rs if r["arms"][arm].get(key) is not None]
    return (sum(v) / len(v)) if v else None


def emit_status(held, cv):
    E = "P8P9_EXACT"
    sel = lambda k: [r for r in held if r["k_chains"] == k and r["substeps"] == FULL_BUDGET]

    gates = {k: {"p0_top1": mean_of(sel(k), "P0_SCALAR", "top1"),
                 "p1_oracle_top1": mean_of(sel(k), "P1_ORACLE_GATE", "top1")}
             for k in PRIMARY_K}
    gate_fail = None
    for k in PRIMARY_K:
        if gates[k]["p0_top1"] >= GATE_HEADROOM_TOP1:
            gate_fail = "NO_MULTICHAIN_GAP"
        elif gates[k]["p1_oracle_top1"] < GATE_ORACLE_TOP1:
            gate_fail = "INSTRUMENT_OR_TASK_ILL_POSED"
        elif not (cv[k]["gate_no_one_hop"] and cv[k]["gate_no_content_leak"]
                  and cv[k]["gate_distinct_q"]):
            gate_fail = "CONSTRUCT_VALIDITY_FAILED"

    # --- the nine registered criteria, at the FULL budget, at both primary K -----
    c = {}
    c["1_beats_P0"] = all(paired(sel(k), E, "P0_SCALAR")["win"] for k in PRIMARY_K)
    c["2_beats_P2"] = all(paired(sel(k), E, "P2_INFERRED_TAG")["win"] for k in PRIMARY_K)
    c["3_beats_P3_and_P6"] = all(paired(sel(k), E, x)["win"] for k in PRIMARY_K
                                 for x in ("P3_GENERIC_TWO_STATE", "P6_SCALAR_TWO_CHANNEL"))
    c["4_beats_P8_ONLY"] = all(paired(sel(k), E, "P8_ONLY")["win"] for k in PRIMARY_K)
    c["5_beats_P9_ONLY"] = all(paired(sel(k), E, "P9_ONLY")["win"] for k in PRIMARY_K)
    c["6_beats_phase_free"] = all(paired(sel(k), E, "B_PHASE_FREE_CONTENT")["win"]
                                  for k in PRIMARY_K)
    c["7_merge_below_ceiling"] = all(
        (mean_of(sel(k), E, "merge_fraction") is not None
         and mean_of(sel(k), E, "merge_fraction") <= MERGE_MAX) for k in PRIMARY_K)
    c["8_stable_at_full_budget"] = all(
        all(r["arms"][E]["runtime_finite"] for r in sel(k)) for k in PRIMARY_K)
    c["9_no_extra_contamination"] = all(
        (mean_of(sel(k), E, "cross_chain_contamination")
         - mean_of(sel(k), "P0_SCALAR", "cross_chain_contamination")) <= CONTAM_MARGIN
        for k in PRIMARY_K)
    law_clear = all(c.values())

    # --- the two killer controls -------------------------------------------------
    shuffle_kills = all(mean_of(sel(k), "P8P9_PHASE_SHUFFLED", "top1")
                        < mean_of(sel(k), "P0_SCALAR", "top1") for k in PRIMARY_K)
    beats_random_freq = all(paired(sel(k), E, "P8P9_RANDOM_FREQUENCY")["win"]
                            for k in PRIMARY_K)

    if gate_fail:
        st, reason = "STATUS_NOT_EMITTED", gate_fail
    elif not c["7_merge_below_ceiling"]:
        st, reason = "PHASE_MEMORY_UNSAFE", "merging exceeds the safety ceiling"
    elif not law_clear:
        st, reason = "PHASE_REPAIR_NOT_CONFIRMED", "the combination did not clear the full law"
    elif not shuffle_kills:
        st, reason = "COMBINATION_NOT_PHASE_DEPENDENT", "phase shuffling preserved the result"
    elif not beats_random_freq:
        st, reason = ("GENERIC_DESYNCHRONIZATION_PLUS_PHASE_HISTORY_SIGNAL",
                      "random frequency approximately matches the structural assignment")
    else:
        st, reason = "PHASE_HISTORY_FREQUENCY_SPREAD_SIGNAL", None

    comps = {k: {f"{E}_vs_{b}": paired(sel(k), E, b) for b in
                 ("P0_SCALAR", "P2_INFERRED_TAG", "P3_GENERIC_TWO_STATE",
                  "P6_SCALAR_TWO_CHANNEL", "B_PHASE_FREE_CONTENT", "P8_ONLY", "P9_ONLY",
                  "P8P9_RANDOM_FREQUENCY", "P8P9_PHASE_SHUFFLED")} for k in PRIMARY_K}

    return {"status": st, "reason": reason, "criteria": c, "law_cleared": law_clear,
            "killer_controls": {"phase_shuffle_destroys_advantage": shuffle_kills,
                                "beats_random_frequency": beats_random_freq},
            "comparisons_per_k": comps, "gates": gates, "construct_validity": cv,
            "decided_at_substeps": FULL_BUDGET,
            "escalate_to_owner": st == "STATUS_NOT_EMITTED"}


VOLATILE = ("cuda_time_ms", "peak_vram_bytes", "wall_s", "host_wall_s", "device")


def strip(o):
    if isinstance(o, dict):
        return {k: strip(v) for k, v in o.items() if k not in VOLATILE}
    if isinstance(o, list):
        return [strip(v) for v in o]
    return o


def group(rs):
    if not rs:
        return {}
    return {a: {m: mean_of(rs, a, m) for m in
                ("top1", "recall_at_5", "cross_chain_contamination", "merge_fraction",
                 "global_order_parameter")} for a in ARMS}


def main(dev_worlds=None, held_worlds=None, k_settings=None, budgets=None, out="CMB_P2_RECEIPT.json"):
    require_cuda()
    dev_w = DEV_WORLDS if dev_worlds is None else dev_worlds
    held_w = HELDOUT_WORLDS if held_worlds is None else held_worlds
    ks = K_SETTINGS if k_settings is None else k_settings
    buds = SUBSTEP_BUDGETS if budgets is None else budgets
    t0 = time.perf_counter()
    dev, held = [], []
    try:
        cv = construct_validity()
        shuf = shuffle_informativeness()
        for sub in buds:
            for k in ks:
                for wid in dev_w:
                    dev.append(run_world(wid, k, sub))
                for wid in held_w:
                    held.append(run_world(wid, k, sub))
        # FLUSH RAW RESULTS BEFORE BUILDING THE RECEIPT. CMB-P1's first launch finished all
        # GPU work and then lost it to a serialisation error in receipt construction.
        with open("CMB_P2_RAW.json", "w") as f:
            json.dump({"construct_validity": cv, "shuffle_informativeness": shuf,
                       "dev": strip(dev), "held": strip(held)}, f)
        print("RAW RESULTS FLUSHED to CMB_P2_RAW.json")
        verdict = emit_status(held, cv)
    except Exception:
        with open(out, "w") as f:
            json.dump({"FAILED": True, "traceback": traceback.format_exc(),
                       "partial_dev": strip(dev), "partial_held": strip(held)}, f, indent=1)
        traceback.print_exc()
        print("RUN FAILED -- partial receipt written")
        return 2

    receipt = {
        "project": "CMB-P2 P8+P9 Controlled Confirmation",
        "preregistration": "CMB_P2_PREREGISTRATION.md v0.1",
        "authority": "owner directive 2026-09-02",
        "parent_commit": "99909e8c79b9283412826fd7658956794247b777",
        "worlds": {"dev": list(dev_w), "heldout": list(held_w),
                   "excluded_used_by_p0_p1": list(EXCLUDED_WORLDS)},
        "frozen_params": dict({n: globals()[n] for n in FROZEN_PARAM_NAMES},
                              **{n: getattr(P1, n) for n in FROZEN_P1_NAMES}),
        "heldout_by_substeps_and_k": {
            sub: {k: group([r for r in held if r["k_chains"] == k and r["substeps"] == sub])
                  for k in ks} for sub in buds},
        "verdict": verdict,
        "shuffle_control_informativeness": shuf,
        "dev_worlds": strip(dev),
        "heldout_worlds": strip(held),
        "compute": dict(gpu_identity(),
                        peak_vram_bytes=int(torch.cuda.max_memory_allocated()),
                        host_wall_s=round(time.perf_counter() - t0, 2)),
        "claim_note": ("No CAS-specific, cognition-general, or production-memory claim is "
                       "licensed by any outcome. P1_ORACLE_GATE is a gate, never a method."),
    }
    payload = json.dumps(strip({k: receipt[k] for k in
                                ("frozen_params", "heldout_by_substeps_and_k", "verdict",
                                 "heldout_worlds")}), sort_keys=True)
    receipt["determinism"] = {"content_hash": hashlib.sha256(payload.encode()).hexdigest()}
    with open(out, "w") as f:
        json.dump(receipt, f, indent=1, sort_keys=True)

    v = receipt["verdict"]
    print("STATUS:", v["status"], "| REASON:", v.get("reason"))
    print("LAW CLEARED:", v["law_cleared"], "| KILLER CONTROLS:", v["killer_controls"])
    for name, ok in v["criteria"].items():
        print(f"   {'PASS' if ok else 'FAIL'}  {name}")
    for sub in buds:
        print(f"--- substeps={sub} ---")
        for k in ks:
            g = receipt["heldout_by_substeps_and_k"][sub][k]
            print(f"  K={k}: " + "  ".join(
                f"{a}={g[a]['top1']:.3f}"
                + ("" if g[a]["merge_fraction"] is None else f"/{g[a]['merge_fraction']:.3f}")
                for a in ARMS))
    print("HASH:", receipt["determinism"]["content_hash"][:16])
    return 0


if __name__ == "__main__":
    sys.exit(main())
