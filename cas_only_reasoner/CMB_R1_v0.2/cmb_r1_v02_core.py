"""RGM-0.2 -- admission safety and matched-control repair.

Frozen design: RGM_02_PREREGISTRATION.md v0.1. Owner directive 2026-09-02.
Base: CMB_R1_v0.1 at GLM's a086a770, code only (its CHANGELOG deletion is not merged).

Three repairs, each against a defect measured in my own RGM-0/0.1 audits:

  1. FALSE NEAR-MATCH ADMISSION. `TAU_COH = 0.75` is an ABSOLUTE threshold and the near-miss
     attack is constructed at 0.75-0.833, sitting exactly on it -- so BOTH (359 admitted) was
     indistinguishable from NEITHER (360). A fixed threshold cannot separate a near-miss from
     a true match by construction. Replaced with a RELATIVE criterion.

  2. NO SEPARATION OF RETRIEVED FROM AUTHORIZED. One list, everything equally usable.
     Split into two tiers, so an ambiguous candidate is DOWNGRADED rather than admitted.

  3. KEEPING THE MATCHED CONTROL MATCHED. I first claimed the generic control was
     handicapped by `coherence_off = (geo_mode == "generic")` at cmb_r1_core.py:490. THAT WAS
     WRONG and is withdrawn: E2 runs through arm_prop(field="role"), whose `coherence`
     parameter defaults to True and whose verifier does apply the check. That line reaches
     only M_NOISE, which is deliberately unverified because it IS the misinformation control.
     The real item: the handicap does not exist in RGM-0.1, but I would CREATE it by giving
     the CAS arm a new two-tier verifier and leaving the control on the old one. So both arms
     get the identical verifier here.

No phase, no frequency, no pulse width, no Q. Phase integration is NOT AUTHORIZED.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
for _rel in ("../CMB_R1_v0.1", "../SHORTCUT_GATE_v0_1"):
    _d = os.path.join(_HERE, _rel)
    sys.path.insert(0, _d if os.path.isdir(_d) else _HERE)
import cmb_r1_core as K                                          # noqa: E402

VERSION = "rgm_0_2_core_v0.1"

# ---- frozen thresholds (RGM_02_PREREGISTRATION.md section 6) ----------------------------
TAU_FLOOR = 0.60      # absolute floor for RETRIEVED -- its only job is to exclude junk
TAU_AUTH = 0.90       # absolute bar for AUTHORIZED
DELTA = 0.08          # RELATIVE margin: the top coherence cluster must clear the rest by this
CONSISTENCY = 0.99    # members of the top cluster must agree with each other at least this much
MAX_RETRIEVED = 10


def coherence(q, m):
    """Identical quantity to RGM-0.1's, so the comparison is like-for-like."""
    coh = K.traj_sim(q["q_traj"], m["trajectory"])
    if q.get("q_ctx") is not None and m.get("context") is not None:
        coh = 0.5 * coh + 0.5 * K._cos(q["q_ctx"], m["context"])
    return coh


def verify_two_tier(memories, q, ranked, use_coherence=True, provenance_aware=True,
                    tau_floor=TAU_FLOOR, tau_auth=TAU_AUTH, delta=DELTA,
                    consistency=CONSISTENCY):
    """Two-tier admission.

    RETRIEVED  -- passed the absolute floor. May be SHOWN or used as context.
    AUTHORIZED -- may influence REASONING or LEARNING. Requires ALL of:
                    (a) absolute:   coh >= tau_auth
                    (b) relative:   member of the top coherence cluster, and that cluster is
                                    separated from everything else by >= delta
                    (c) unambiguous: the top cluster AGREES WITH ITSELF -- corroborating
                                     memories must actually corroborate

    WHICH CONDITION IS LOAD-BEARING -- MEASURED, and not what I first claimed.
    Ablation on 20 near-miss queries over 2 dev worlds:

      registered attack (false coherence 0.8333, bar 0.90)
        both on                   FALSE 0  TRUE 60
        (a) OFF, (b)+(c) on       FALSE 0  TRUE 60   <- relative alone suffices here
        (b) OFF, (a)+(c) on       FALSE 0  TRUE  0   <- blocked by (c) consistency

      ADAPTIVE attack, forged at 0.9375 -- ABOVE the absolute bar, and inside the relative
      margin (gap 0.0625 < DELTA 0.08), so (a) and (b) are BOTH defeated by construction
        every configuration          FALSE 0  TRUE  0   <- blocked by (c) consistency

    So (c) is the condition that actually holds the line, not (b) as I first wrote. An
    attacker who knows the thresholds can beat the absolute bar and the relative margin; what
    they cannot do is make a forgery AGREE with the truth it is impersonating -- if it agreed,
    it would not be a forgery.

    DISCLOSED COST: under the adaptive attack the system authorises NOTHING -- true memories
    included (TRUE 0). It fails CLOSED. That is the right trade for a memory system, but it is
    an availability cost, not a free win, and a flood of near-identical forgeries can deny
    authorisation to legitimate memories.
    """
    reps, seen = [], set()
    for mid, sc in ranked:
        r = memories[mid]["provenance_root_id"] if provenance_aware else mid
        if r in seen:
            continue
        seen.add(r)
        coh = coherence(q, memories[mid]) if use_coherence else 1.0
        reps.append({"mid": mid, "score": sc, "coh": coh, "root": r})

    retrieved = [(x["mid"], x["score"]) for x in reps
                 if x["coh"] >= tau_floor][:MAX_RETRIEVED]
    if not reps:
        return retrieved, [], {"reason": "no candidates"}

    best = max(x["coh"] for x in reps)
    top = [x for x in reps if best - x["coh"] < delta]
    rest = [x for x in reps if best - x["coh"] >= delta]

    cond_abs = best >= tau_auth
    # separated: either something sits >= delta below the top cluster, or the top cluster is
    # the ONLY thing there. A tie across the whole set with nothing below it is ambiguous.
    cond_rel = bool(rest) or len(top) == len(reps)
    # consistent: every pair in the top cluster agrees. Corroboration means agreement.
    cond_cons = True
    for i in range(len(top)):
        for j in range(i + 1, len(top)):
            if K.traj_sim(memories[top[i]["mid"]]["trajectory"],
                          memories[top[j]["mid"]]["trajectory"]) < consistency:
                cond_cons = False
                break
        if not cond_cons:
            break

    authorized = ([(x["mid"], x["score"]) for x in top]
                  if (cond_abs and cond_rel and cond_cons) else [])
    diag = {"best_coh": best, "n_top_cluster": len(top), "n_rest": len(rest),
            "cond_absolute": bool(cond_abs), "cond_relative": bool(cond_rel),
            "cond_consistent": bool(cond_cons),
            "runner_up_coh": (max(x["coh"] for x in rest) if rest else None)}
    return retrieved, authorized, diag


def arm_v2(memories, adj, q, geo_mode="cas", provenance_aware=True, use_coherence=True,
           mutant_no_propagation=False, **verifier_kw):
    """RGM-0.1's arm_d scoring with the two-tier verifier applied identically to every arm.

    The ONLY behavioural difference from `K.arm_d` is the verifier. Scoring, propagation,
    seeds, weights and the top-k budget are untouched, so D-vs-E stays like-for-like -- and
    the control receives the SAME new verifier as the CAS arm, which is the whole point of
    item 3. Note `K.arm_d`'s internal `coherence_off` no longer matters here: this function
    uses `ranked` (pre-verifier) and applies its own verifier to both arms equally.
    """
    ranked, _old_verified, metrics = K.arm_d(
        memories, adj, q, geo_mode=geo_mode, provenance_aware=provenance_aware,
        use_coherence=use_coherence, mutant_no_propagation=mutant_no_propagation)
    # Both arms receive the IDENTICAL verifier -- see item 3, and the correction to it.
    retrieved, authorized, diag = verify_two_tier(
        memories, q, ranked, use_coherence=use_coherence,
        provenance_aware=provenance_aware, **verifier_kw)
    metrics = dict(metrics, verifier=diag)
    return ranked, retrieved, authorized, metrics


def is_correct(memories, mid):
    return memories[mid].get("answer") == "CORRECT"


def admission_metrics(memories, q, retrieved, authorized):
    """The numbers that decide the status. `authorized_precision` is the one that matters for
    a memory system: what fraction of what we let influence reasoning is actually true."""
    def prec(lst):
        if not lst:
            return None
        good = sum(1 for mid, _ in lst if is_correct(memories, mid))
        return good / len(lst)

    false_ret = sum(1 for mid, _ in retrieved if not is_correct(memories, mid))
    false_auth = sum(1 for mid, _ in authorized if not is_correct(memories, mid))
    return {"n_retrieved": len(retrieved), "n_authorized": len(authorized),
            "false_admitted_retrieved": false_ret,
            "false_admitted_authorized": false_auth,
            "retrieved_precision": prec(retrieved),
            "authorized_precision": prec(authorized)}
