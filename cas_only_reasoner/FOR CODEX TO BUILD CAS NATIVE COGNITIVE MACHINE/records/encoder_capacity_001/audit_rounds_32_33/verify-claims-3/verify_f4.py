"""Independent re-measure of auditor finding F4 (round 33 framing). Read-only on repo."""
import json, pathlib, sys
from collections import Counter, defaultdict
from fractions import Fraction as Fr

HOME = pathlib.Path(
    r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner"
    r"\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next"
    r"\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
sys.path.insert(0, str(HOME)); sys.path.insert(0, str(HOME / "research" / "CAS_META_2_COMPOSITION"))
from cas_meta2.typed_teaching import answers, checker, course, slots, worker_contract  # noqa


def pct(a, b):
    return f"{a}/{b} = {100*a/b:.4f}%"


fc, _, _ = worker_contract.load_material(HOME)
R = HOME / "records/typed_matched_001"
runs = sorted(d for d in R.iterdir() if (d / "collected/results/artifacts/final_scoring.json").is_file())
print("runs", [r.name for r in runs])
cache = {}
kind_tot = defaultdict(Counter)
out = defaultdict(Counter)
ties = Counter()
for r in runs:
    A = r / "collected/results/artifacts"
    sc = json.loads((A / "final_scoring.json").read_text(encoding="utf-8"))
    preds = json.loads((A / "final_predictions.json").read_text(encoding="utf-8"))["predictions"]
    rows = {x["record_id"]: x for x in sc["rows"]}
    assert sc["total"] == len(rows)
    out[r.name]["total"] = sc["total"]
    out[r.name]["correct_field"] = sc["correct"]
    out[r.name]["correct_rows"] = sum(1 for x in sc["rows"] if x["correct"])
    for x in sc["rows"]:
        kind_tot[x["kind"]]["q"] += 1
        kind_tot[x["kind"]]["c"] += int(bool(x["correct"]))
    for p in preds:
        rid = p["record_id"]
        kind = rows[rid]["kind"]
        if kind not in ("parts", "definition", "edge_account"):
            continue
        if rid not in cache:
            pk = course.model_packet(fc, rid)
            plan = slots.compile_slots(pk)
            tgt = checker.derive_target(pk["source"], pk["record"]["query"])
            adm = {json.dumps(a["value"], sort_keys=True) for a in tgt["admissible_answers"]}
            cache[rid] = (pk, plan, adm)
        pk, plan, adm = cache[rid]
        q = pk["record"]["query"]
        sc_ = p["scores"]
        focus = [w for w in pk["source"]["worlds"] if w["world_id"] == q["focus_world_id"]]
        assert len(focus) == 1
        focus = focus[0]

        def ok(sel, p=p, pk=pk, adm=adm):
            d = dict(p["decisions"])
            d["selected"] = sel
            try:
                v = slots.assemble_answer(pk, d)["value"]
            except Exception:
                return False
            return json.dumps(v, sort_keys=True) in adm

        ind = {}
        for s in plan["slots"]:
            best = None
            for sym in s["symbols"]:
                if best is None or sc_[s["slot_id"]][sym] > sc_[s["slot_id"]][best]:
                    best = sym
            ind[s["slot_id"]] = best
        out[r.name][kind + "_rec_dec_match"] += int(p["decisions"]["selected"] == ind)
        i_ok = ok(ind)
        out[r.name][kind + "_q"] += 1
        out[r.name][kind + "_ind"] += int(i_ok)
        out[r.name][kind + "_ind_vs_record_agree"] += int(i_ok == bool(rows[rid]["correct"]))
        if kind == "parts":
            whole = q["arguments"]["whole"]
            want = {e["target"] for e in focus["contains"] if e["source"] == whole}
            k = len(want)
            ns = [s for s in plan["slots"] if s["field"] == "node"]
            m = sorted(((sc_[s["slot_id"]]["PRESENT"] - sc_[s["slot_id"]]["ABSENT"]), s["slot_id"]) for s in ns)
            m.reverse()
            if 0 < k < len(m) and m[k - 1][0] == m[k][0]:
                ties["parts"] += 1
            top = {sid for _, sid in m[:k]}
            con = dict(ind)
            rd = dict(ind)
            for s in ns:
                con[s["slot_id"]] = "PRESENT" if s["slot_id"] in top else "ABSENT"
                rd[s["slot_id"]] = "PRESENT" if s["coordinates"][0] in want else "ABSENT"
            out[r.name]["parts_con"] += int(ok(con))
            out[r.name]["parts_reader"] += int(ok(rd))
        elif kind == "edge_account":
            want = {(e["source"], e["target"]) for e in focus["contains"]}
            es = [s for s in plan["slots"] if s["field"] == "edge"]
            k = len(want)
            m = sorted(((sc_[s["slot_id"]]["PRESENT"] - sc_[s["slot_id"]]["ABSENT"]), s["slot_id"]) for s in es)
            m.reverse()
            top = {sid for _, sid in m[:k]}
            con = dict(ind)
            rd = dict(ind)
            for s in es:
                con[s["slot_id"]] = "PRESENT" if s["slot_id"] in top else "ABSENT"
                rd[s["slot_id"]] = "PRESENT" if tuple(s["coordinates"]) in want else "ABSENT"
            out[r.name]["edge_account_con"] += int(ok(con))
            out[r.name]["edge_account_reader"] += int(ok(rd))
        else:
            bf = {s["field"]: s for s in plan["slots"]}
            al = {w["world_id"]: w for w in plan["aliases"]["worlds"]}
            best = None
            for w in pk["source"]["worlds"]:
                aw = al[w["world_id"]]
                walias = {n["ref"]: n["alias"] for n in aw["nodes"]}.get(w["declared_whole"])
                tr = {"whole": walias, "kind_ref": aw["alias"], "function_ref": aw["alias"]}
                if tr["whole"] is None or any(tr[f] not in bf[f]["symbols"] for f in tr):
                    continue
                tot = sum(sc_[bf[f]["slot_id"]][tr[f]] for f in tr)
                if best is None or tot > best[0]:
                    best = (tot, tr, w["world_id"])
            con = dict(ind)
            for f, sym in best[1].items():
                con[bf[f]["slot_id"]] = sym
            out[r.name]["definition_con"] += int(ok(con))
            out[r.name]["definition_con_pick_is_focus"] += int(best[2] == focus["world_id"])
            aw = al[focus["world_id"]]
            tr = {"whole": {n["ref"]: n["alias"] for n in aw["nodes"]}[focus["declared_whole"]],
                  "kind_ref": aw["alias"], "function_ref": aw["alias"]}
            rd = dict(ind)
            for f, sym in tr.items():
                rd[bf[f]["slot_id"]] = sym
            out[r.name]["definition_reader"] += int(ok(rd))
    print(r.name, dict(out[r.name]), flush=True)

print("\n==== RUN TOTALS ====")
tots = [out[r.name]["correct_field"] for r in runs]
print("recorded correct per run:", tots, "rows-count:", [out[r.name]["correct_rows"] for r in runs],
      "sum", sum(tots), "mean", Fr(sum(tots), 6), "->", pct(sum(tots), 6 * 564))
print("\n==== PER-KIND ACCURACY, all six runs, recorded final_scoring ====")
for k, c in sorted(kind_tot.items(), key=lambda kv: -kv[1]["c"] / kv[1]["q"]):
    print(f"  {k:15s} {pct(c['c'], c['q'])}")
print("\n==== ROUND-33 ARMS (my code) ====")
agg = Counter()
for r in runs:
    for key, v in out[r.name].items():
        agg[key] += v
for kind in ("parts", "definition", "edge_account"):
    q = agg[kind + "_q"]
    print(f"{kind}: q={q} independent {pct(agg[kind+'_ind'], q)} | constrained {pct(agg[kind+'_con'], q)} | "
          f"packet_reader {pct(agg[kind+'_reader'], q)} | indep_agrees_recorded {pct(agg[kind+'_ind_vs_record_agree'], q)} | "
          f"recorded_decisions==argmax {pct(agg[kind+'_rec_dec_match'], q)}")
    print("   per run constrained:", [pct(out[r.name][kind + '_con'], out[r.name][kind + '_q']) for r in runs])
    print("   per run independent:", [pct(out[r.name][kind + '_ind'], out[r.name][kind + '_q']) for r in runs])
print("definition constrained picked the focus world:", pct(agg["definition_con_pick_is_focus"], agg["definition_q"]))
print("parts top-k boundary ties:", ties["parts"])
pg = agg["parts_con"] - agg["parts_ind"]
dg = agg["definition_con"] - agg["definition_ind"]
gain = pg + dg
print("\n==== CLAIM 3 ARITHMETIC ====")
print("parts gain/run", Fr(pg, 6), f"{pg/6:.4f}")
print("definition gain/run", Fr(dg, 6), f"{dg/6:.4f}")
print("total gain/run", Fr(gain, 6), f"{gain/6:.4f}")
new_mean = Fr(sum(tots) + gain, 6)
print("new mean", new_mean, f"{float(new_mean):.4f}", f"{100*float(new_mean)/564:.4f}%",
      "old", f"{sum(tots)/6:.4f}", f"{100*sum(tots)/6/564:.4f}%")
per_run_new = [out[r.name]["correct_field"] + (out[r.name]["parts_con"] - out[r.name]["parts_ind"])
               + (out[r.name]["definition_con"] - out[r.name]["definition_ind"]) for r in runs]
print("per-run offline totals:", per_run_new, [f"{100*x/564:.4f}%" for x in per_run_new])
rg = (agg["parts_reader"] - agg["parts_ind"]) + (agg["definition_reader"] - agg["definition_ind"])
print("packet-reader gain/run on parts+definition:", Fr(rg, 6), f"{rg/6:.4f}")
rge = rg + (agg["edge_account_reader"] - agg["edge_account_ind"])
print("packet-reader gain/run on parts+definition+edge_account:", Fr(rge, 6), f"{rge/6:.4f}")
print("fraction of reader headroom (parts+definition) realised by the constraint gain:", pct(gain, rg))
