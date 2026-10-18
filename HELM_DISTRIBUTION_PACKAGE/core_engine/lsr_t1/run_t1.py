"""LSR-T1 run: arms x families, exact scoring, and every mark read by this program (never by prose).

Arms (FROZEN.json "arms"): A0_SINGLE, B1_CHUNK16, A1_LSR_X2, A2_LSR_X4, A3_LSR_P4 (parallel production,
ADMITTED_BY_OWNER_20261014), B2_RANDOM_X4 seeds 11/29/47.
"""
import json
import random
import time
from fractions import Fraction
from pathlib import Path

from lacunarity_machine.universe import Universe, Cell
from lacunarity_machine.ledger import Ledger
from lacunarity_machine.readers import deterministic_read
from sdg_bridge_v2 import parse_recipe, bind_table

from . import engine as E
from . import families as F

HERE = Path(__file__).resolve().parent
TOL_ABS, TOL_REL = Fraction(1, 50), Fraction(1, 20)
BRIDGE_FROZEN = Path(r"C:\Users\wakil\Documents\Codex\CAS-Recipe-Network-Comparison-20261011\sdg_bridge_v2\FROZEN.json")


def fz():
    return json.loads((HERE / "FROZEN.json").read_text("utf-8"))


def fs(fr):
    fr = Fraction(fr)
    return "%d/%d" % (fr.numerator, fr.denominator)


def hit(yhat, y):
    return abs(yhat - y) <= max(TOL_ABS, TOL_REL * y)


# ------------------------------------------------------------------ A0 via bridge v2 bind_table
def bridge_seed_coefficients(ds, columns, cells):
    b = json.loads(BRIDGE_FROZEN.read_text("utf-8"))["fix3_binder"]
    rows = [{"recipe_id": r["rid"], "values": list(r["x"]), "y": r["y"], "confirmed": True} for r in ds["train"]]
    bmap = {c: {"cell": cells[c], "role": "prerequisite",
                "semantic_basis": "NONE: operator-declared label for a form test"} for c in columns}
    out = bind_table(columns, rows, bmap, omega_for=lambda rid: "lsr_%s_%02d" % (ds["family"], rid),
                     params={k: b[k] for k in ("rel_tol", "abs_tol", "floor")})
    coefs = {}
    for rid, rec in out["recipes"].items():
        if rec["coefficients_exact"] and not rec["problems"]:
            coefs[int(rid)] = [Fraction(v) for v in rec["coefficients_exact"]]
        else:
            coefs[int(rid)] = None
    summary = {"status": out["status"], "pooled_residual_score_text": out.get("pooled_residual_score_text"),
               "shape_reasons": out.get("shape_reasons")}
    return coefs, summary


# ------------------------------------------------------------------ one Omega, one arm
def machine_check(row_ledger, run):
    """lacunarity_machine_v1 deterministic_read must agree with the loop's own row states at the HALT."""
    rep = deterministic_read(row_ledger.universe, row_ledger.ledger, Fraction(1), "read")
    machine = {r["cell"][4:]: r["state"] for r in rep["rows"]}
    loop = run.final_read.row_states
    agree = all(machine[k] == v for k, v in loop.items())
    carried = sorted((rid, machine[rid]) for rid in run.halt.lacunae)
    return agree, carried, rep["state_counts"]


def score(mem, rows):
    hits, nmae = 0, Fraction(0)
    for r in rows:
        yhat = E.predict(mem, r, exact=True)
        hits += hit(yhat, r.yF)
        nmae += abs(yhat - r.yF) / max(Fraction(1), abs(r.yF))
    return hits, nmae


def run_arm(arm, rows, seed_recipe, lib, deadline, rng=None):
    train, valid = rows["train"], rows["validation"]
    rl = E.RowLedger(Universe, Cell, Ledger, rows["omega"], train)
    t0 = time.process_time()
    if arm["kind"] == "single":
        run = E.static_read(E.Memory(rows["omega"], [seed_recipe] if seed_recipe else [], E.SINGLE), train, rl)
    elif arm["kind"] == "chunk":
        recs = []
        for j in range(0, len(train), arm["chunk"]):
            r = E.witnessed_ratio_min(frozenset(range(len(train[0].xf))), train[j:j + arm["chunk"]], bounds=False)
            if r is not None:
                recs.append(r)
        run = E.static_read(E.Memory(rows["omega"], recs, E.EXCLUSIVE), train, rl)
        run.admissions = len(recs)
    else:
        run = E.run_omega(rows["omega"], train, valid, seed_recipe, arm["a_max"], arm["allow_pooled"], lib,
                          rng=rng, deadline=deadline, row_ledger=rl)
    cpu = time.process_time() - t0
    agree, carried, _ = machine_check(rl, run)
    mem = run.memory
    held_hits, held_nmae = score(mem, rows["heldout"])
    train5 = sum(hit(E.predict(mem, r, exact=True), r.yF) for r in train)
    cells = fz()["declared_cells"]
    rendering = E.render_memory(mem, cells)
    texts = rendering["recipes"]
    parsed_ok = all(parse_recipe(t)["accepted"] for t in texts)
    times_free = all("×" not in s for s in texts + [rendering["co_presence"], rendering["declaration"]])
    corrupted_carried = sum(1 for rid in run.halt.lacunae if rid in rows["corrupted"])
    return {
        "omega": rows["omega"], "halt": run.halt.status, "lacunae_count": len(run.halt.lacunae),
        "lacunae": [[rid, st] for rid, st in carried], "halt_diagnostics": run.halt.diagnostics,
        "machine_agrees_with_loop": agree, "admissions": run.admissions, "recipes": len(mem.recipes),
        "readout": mem.readout, "eta": fs(mem.eta), "capacity": None if mem.capacity is None else fs(mem.capacity),
        "cycles": run.cycles, "proposals_tried": run.proposals_tried, "refusals": run.refusals,
        "admitted_sources": run.admitted_sources, "events": run.events,
        "train_explained_tau": fs(run.final_read.explained_fraction), "train_explained_5pct": [train5, len(train)],
        "heldout_hits": held_hits, "heldout_n": len(rows["heldout"]), "heldout_nmae_sum": fs(held_nmae),
        "recipe_texts": texts, "co_presence": rendering["co_presence"], "declaration": rendering["declaration"],
        "bridge_v2_parses_all": parsed_ok, "no_times_operator": times_free,
        "corrupted_among_carried": corrupted_carried, "corrupted_in_train": len(rows["corrupted"]),
        "cpu_seconds": round(cpu, 4)}


# ------------------------------------------------------------------ whole run
def run_all(deadline, progress=None):
    frozen = fz()
    shape = F.shape_library_counts()
    lib = E.ShapeLibrary(shape["by_prerequisite_count"], shape["seed_file_sha256"])
    arms = frozen["arms"]
    out = {"shape_library": shape, "families": {}, "binder_today": {}}
    for fi, key in enumerate(frozen["family_order"]):
        t_fam = time.time()
        ds = F.build(key)
        coefs, bsum = bridge_seed_coefficients(ds, ["x0", "x1", "x2", "x3"], frozen["declared_cells_by_column"])
        out["binder_today"][key] = bsum
        fam = {"dataset_sha256": ds["sha256"], "arms": {a["id"]: [] for a in arms}}
        for rid in range(F.RECIPES):
            rows = F.omega_rows(ds, rid)
            rows["omega"] = "%s_%02d" % (key, rid)
            seed = None
            if coefs[rid] is not None:
                seed = E.make_recipe(range(4), {i: coefs[rid][i] for i in range(4)})
                check = E.witnessed_ratio_min(frozenset(range(4)), rows["train"], bounds=False)
                if check != seed:
                    raise AssertionError("bridge v2 bind_table and witnessed_ratio_min disagree: " + rows["omega"])
            for a in arms:
                rng = None
                if a["kind"] == "random":
                    rng = random.Random(a["seed"] * 1000003 + fi * 1009 + rid)
                fam["arms"][a["id"]].append(run_arm(a, rows, seed, lib, deadline, rng))
        if key == "b":
            out["claim3_direct_check_b"] = claim3_direct(ds, coefs)
        out["families"][key] = fam
        if progress:
            progress({"family": key, "wall_seconds": round(time.time() - t_fam, 3)})
    out["summary"] = summarize(out, arms)
    out["marks"] = marks(out["summary"], out, arms)
    return out


def claim3_direct(ds, coefs):
    """Owner ruling 2026-10-14 ('Yes on parallel prod'): test ARCHITECTURE s.8 claim 3 directly, independent
    of the proposer. For each b Omega: offer POOLED_LINES on ALL training rows, fit by
    witnessed_pool_solve_v0, VERIFY against the A0 seed at the seed's tau (cap 4), score held-out exactly.
    A DIAGNOSTIC of the claim, not an arm; it does not enter any mark."""
    per = []
    hits_all, n_all, admitted = 0, 0, 0
    for rid in range(F.RECIPES):
        rows = F.omega_rows(ds, rid)
        train, valid = rows["train"], rows["validation"]
        seed = E.make_recipe(range(4), {i: coefs[rid][i] for i in range(4)}) if coefs[rid] else None
        mem = E.Memory("b_%02d" % rid, [seed] if seed else [])
        tau_i = E.tau_index_for(mem, train, 0)
        hold0 = sum(1 for r in valid if E.explained(r.yf, E.predict(mem, r), E.TAU_LADDER[tau_i]))
        p = E.Proposal(E.K_LINES, frozenset(range(4)), E.POOLED, E.LOOP_EXTENSION, tuple(r.row_id for r in train),
                       "direct claim-3 check")
        fr = E.fit(mem, p, train)
        vr = E.verify(mem, fr, train, valid, E.TAU_LADDER[tau_i], hold0, 4)
        rec = {"omega": mem.omega, "fit_refusal": fr.refusal, "verify_decision": vr.decision,
               "newly_explained": vr.newly_explained, "broken": vr.broken}
        if fr.candidate is not None:
            cand = fr.candidate
            h, _ = score(cand, rows["heldout"])
            tr = sum(hit(E.predict(cand, r, exact=True), r.yF) for r in train)
            rec.update({"lines": len(cand.recipes), "capacity": None if cand.capacity is None else fs(cand.capacity),
                        "heldout_hits": h, "heldout_n": len(rows["heldout"]), "train_hits_5pct": tr,
                        "train_n": len(train)})
            hits_all += h
            admitted += vr.decision == "ADMIT"
        n_all += len(rows["heldout"])
        per.append(rec)
    return {"per_omega": per, "heldout_accuracy_if_fitted": fs(Fraction(hits_all, n_all)),
            "omegas_verify_admit": admitted,
            "omegas_with_4_lines": sum(1 for r in per if r.get("lines") == 4),
            "omegas_with_capacity_stage": sum(1 for r in per if r.get("capacity") is not None)}


def summarize(out, arms):
    s = {}
    for key, fam in out["families"].items():
        s[key] = {}
        for a in arms:
            runs = fam["arms"][a["id"]]
            n = sum(r["heldout_n"] for r in runs)
            halts = {}
            for r in runs:
                halts[r["halt"]] = halts.get(r["halt"], 0) + 1
            tr = [Fraction(r["train_explained_tau"]) for r in runs]
            s[key][a["id"]] = {
                "heldout_accuracy": Fraction(sum(r["heldout_hits"] for r in runs), n),
                "heldout_nmae": sum(Fraction(r["heldout_nmae_sum"]) for r in runs) / n,
                "train_explained_tau": sum(tr) / len(tr),
                "train_explained_5pct": Fraction(sum(r["train_explained_5pct"][0] for r in runs),
                                                 sum(r["train_explained_5pct"][1] for r in runs)),
                "halts": halts, "admissions": sum(r["admissions"] for r in runs),
                "recipes": sum(r["recipes"] for r in runs),
                "capacity_stages": sum(1 for r in runs if r["capacity"] is not None),
                "eta_terms": sum(1 for r in runs if r["eta"] != "1/1"),
                "readouts": {m: sum(1 for r in runs if r["readout"] == m) for m in (E.SINGLE, E.EXCLUSIVE, E.POOLED)},
                "cpu_seconds": round(sum(r["cpu_seconds"] for r in runs), 3),
                "nonempty_lacunae_on_every_unfinished_halt": all(r["lacunae_count"] > 0 for r in runs
                                                                 if r["halt"] != E.H_COMPLETE),
                "machine_agrees": all(r["machine_agrees_with_loop"] for r in runs),
                "bridge_v2_parses_all": all(r["bridge_v2_parses_all"] for r in runs),
                "no_times_operator": all(r["no_times_operator"] for r in runs),
                "corrupted_among_carried": [sum(r["corrupted_among_carried"] for r in runs),
                                            sum(r["lacunae_count"] for r in runs)],
                "cycle0_zero_admissions_all": all(r["admissions"] == 0 and r["halt"] == E.H_COMPLETE
                                                  and r["cycles"] == 0 for r in runs)}
    return s


def beats(x, y):
    """Project 5 percent rule on panel 1: NMAE_X <= 0.95 NMAE_Y AND accuracy_X >= accuracy_Y + 0.05."""
    return x["heldout_nmae"] <= Fraction(95, 100) * y["heldout_nmae"] and \
        x["heldout_accuracy"] >= y["heldout_accuracy"] + Fraction(5, 100)


def color(fam_s, arm_id):
    if all(v["heldout_accuracy"] < Fraction(1, 10) for v in fam_s.values()):
        return "WHITE"
    if arm_id == "A0_SINGLE":
        return "REFERENCE"
    x, y = fam_s[arm_id], fam_s["A0_SINGLE"]
    if beats(x, y):
        return "GREEN"
    if x["heldout_accuracy"] > y["heldout_accuracy"] and x["heldout_nmae"] < y["heldout_nmae"]:
        return "YELLOW"
    return "RED"


def marks(s, out, arms):
    rnd = [a["id"] for a in arms if a["kind"] == "random"]
    clean = [k for k in ("S1", "S2v2", "S3v2") if k in s]
    m = {}
    m["M1_do_nothing"] = all(s[k][a]["cycle0_zero_admissions_all"]
                             and s[k][a]["heldout_accuracy"] == s[k]["A0_SINGLE"]["heldout_accuracy"]
                             for k in clean for a in ("A1_LSR_X2", "A2_LSR_X4", "A3_LSR_P4"))
    a2 = s.get("a2")
    m["M2_exact_substitution_a2"] = bool(a2) and beats(a2["A2_LSR_X4"], a2["A0_SINGLE"]) and \
        a2["A2_LSR_X4"]["halts"].get(E.H_COMPLETE, 0) >= 12
    m["M3_smooth_substitution_a"] = beats(s["a"]["A2_LSR_X4"], s["a"]["A0_SINGLE"])
    m4 = {}
    for k in ("a2", "a"):
        acc = s[k]["A2_LSR_X4"]["heldout_accuracy"]
        m4[k] = {"vs_B1": acc >= s[k]["B1_CHUNK16"]["heldout_accuracy"] + Fraction(5, 100)}
        for r in rnd:
            m4[k]["vs_" + r] = acc >= s[k][r]["heldout_accuracy"] + Fraction(5, 100)
    m["M4_loop_earned_something"] = all(all(v.values()) for v in m4.values())
    m["M4_detail"] = m4
    b = s["b"]
    m["M5_sum_honesty_exclusive"] = all(b[a]["halts"].get(E.H_NOT, 0) >= 12 for a in ("A1_LSR_X2", "A2_LSR_X4"))
    m["M6_pooled_exact"] = b["A3_LSR_P4"]["halts"].get(E.H_COMPLETE, 0) >= 14 and \
        b["A3_LSR_P4"]["heldout_accuracy"] >= Fraction(95, 100)
    m["M7_no_harm_c"] = s["c"]["A2_LSR_X4"]["heldout_accuracy"] >= s["c"]["A0_SINGLE"]["heldout_accuracy"] - \
        Fraction(2, 100) and s["c"]["A2_LSR_X4"]["admissions"] <= 16
    m["M8_mode_discrimination_a2_reported"] = s["a2"]["A3_LSR_P4"]["readouts"].get(E.POOLED, 0) <= 4
    m["M9_carried_lacunae"] = all(v["nonempty_lacunae_on_every_unfinished_halt"] for fam in s.values()
                                  for v in fam.values())
    m["hard_gates"] = {"M1": m["M1_do_nothing"], "M9": m["M9_carried_lacunae"], "M4": m["M4_loop_earned_something"]}
    m["test_verdict"] = "PASS_HARD_GATES" if all(m["hard_gates"].values()) else "FAILURE"
    # frozen loop-status rule (FROZEN.json loop_status_rule)
    if m["M1_do_nothing"] and m["M9_carried_lacunae"] and m["M4_loop_earned_something"]:
        status = "EARNED_ITS_KEEP"
    else:
        verify_did = False
        for k in ("a2", "a"):
            acc = s[k]["A2_LSR_X4"]["heldout_accuracy"]
            if beats(s[k]["A2_LSR_X4"], s[k]["A0_SINGLE"]) and any(
                    s[k][r]["heldout_accuracy"] >= acc - Fraction(5, 100) for r in rnd):
                verify_did = True
        status = "VERIFY_DID_THE_WORK" if (m["M1_do_nothing"] and m["M9_carried_lacunae"] and verify_did) \
            else "INCONCLUSIVE"
    m["loop_status"] = status
    m["additive_b"] = {
        "reading_without_parallel_production": {"rule": "M5", "pass": m["M5_sum_honesty_exclusive"]},
        "reading_with_parallel_production_ADMITTED_BY_OWNER_20261014": {
            "rule": "M5 AND M6", "pass": m["M5_sum_honesty_exclusive"] and m["M6_pooled_exact"],
            "A3_recipes_total": b["A3_LSR_P4"]["recipes"], "A3_capacity_stages": b["A3_LSR_P4"]["capacity_stages"],
            "A3_admissions_total": b["A3_LSR_P4"]["admissions"], "A3_halts": b["A3_LSR_P4"]["halts"]}}
    m["colors"] = {k: {a["id"]: color(s[k], a["id"]) for a in arms} for k in s}
    m["integrity"] = {"machine_agrees_everywhere": all(v["machine_agrees"] for f in s.values() for v in f.values()),
                      "bridge_v2_parses_every_rendered_recipe": all(v["bridge_v2_parses_all"] for f in s.values()
                                                                    for v in f.values()),
                      "no_times_operator_anywhere": all(v["no_times_operator"] for f in s.values() for v in f.values())}
    return m
