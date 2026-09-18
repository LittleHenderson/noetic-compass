"""verify-signal-3: independent re-measure of edge_account / parts per-bit accuracy vs chance.
Read-only. Pure stdlib + project pure modules. Truth read from focus["contains"] directly and
cross-checked against checker.derive_target. Machine bits read three ways: submitted answer,
decisions.selected, and margin>0."""
from __future__ import annotations
import json, pathlib, sys
from fractions import Fraction

HOME = pathlib.Path(
    r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner"
    r"\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next"
    r"\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
)
sys.path.insert(0, str(HOME))
sys.path.insert(0, str(HOME / "research" / "CAS_META_2_COMPOSITION"))
from cas_meta2.typed_teaching import checker, course, slots, worker_contract  # noqa: E402

R = HOME / "records/typed_matched_001"
KINDS = ("edge_account", "parts")


def pct(f):
    return f"{float(100 * f):.4f}%"


def main():
    frozen, _t, _ = worker_contract.load_material(HOME)
    runs = sorted(d for d in R.iterdir() if d.is_dir() and d.name.startswith("receipt_"))
    cache = {}
    out = {}
    for run in runs:
        preds = json.loads((run / "collected/results/artifacts/final_predictions.json").read_text(encoding="utf-8"))["predictions"]
        acc = {k: dict(q=0, bits=0, tp=0, ans=0, sel=0, mar=0, arg=0, predP=0, mismatch=0, exact=0) for k in KINDS}
        for p in preds:
            rid = p["record_id"]
            if rid not in cache:
                pk = course.model_packet(frozen, rid)
                q = pk["record"]["query"]
                kind = q["kind"]
                if kind not in KINDS:
                    cache[rid] = None
                    continue
                worlds = {w["world_id"]: w for w in pk["source"]["worlds"]}
                focus = worlds[q["focus_world_id"]]
                E = {(e["source"], e["target"]) for e in focus["contains"]}
                if kind == "parts":
                    whole = q["arguments"]["whole"]
                    truthset = {b for a, b in E if a == whole}
                else:
                    truthset = E
                plan = slots.compile_slots(pk)
                field = "edge" if kind == "edge_account" else "node"
                fs = [s for s in plan["slots"] if s["field"] == field]
                keyf = (lambda s: (s["coordinates"][0], s["coordinates"][1])) if kind == "edge_account" else (lambda s: s["coordinates"][0])
                # cross-check with checker
                val = checker.derive_target(pk["source"], q)["admissible_answers"][0]["value"]
                ck = {(r["source"], r["target"]) for r in val["edges"]} if kind == "edge_account" else set(val["nodes"])
                mism = int(ck != truthset)
                # every true member must be a slot
                slotkeys = {keyf(s) for s in fs}
                mism += int(not truthset <= slotkeys)
                cache[rid] = (kind, [(s["slot_id"], keyf(s), keyf(s) in truthset) for s in fs], mism)
            if cache[rid] is None:
                continue
            kind, fs, mism = cache[rid]
            a = acc[kind]
            a["q"] += 1
            a["mismatch"] += mism
            v = p["answer"]["value"]
            sub = {(r["source"], r["target"]) for r in v["edges"]} if kind == "edge_account" else set(v["nodes"])
            sel = p["decisions"].get("selected", {})
            allok = True
            for sid, key, t in fs:
                a["bits"] += 1
                a["tp"] += t
                a["ans"] += (key in sub) == t
                allok &= (key in sub) == t
                a["sel"] += (sel.get(sid) == "PRESENT") == t
                sc = p["scores"][sid]
                m = sc["PRESENT"] - sc["ABSENT"]
                a["mar"] += (m > 0) == t
                a["arg"] += (m >= 0 and not (m == 0 and "ABSENT" < "PRESENT")) == t  # ties -> ABSENT (alphabetical)
                a["predP"] += key in sub
            a["exact"] += allok
        out[run.name] = acc

    lines = []
    for kind in KINDS:
        lines.append(f"=== {kind} (measured by verify-signal-3) ===")
        below = below_mm = 0
        for run, acc in out.items():
            a = acc[kind]
            n = a["bits"]
            p = Fraction(a["tp"], n)
            chance = p * p + (1 - p) * (1 - p)
            qm = Fraction(a["predP"], n)
            mm = p * qm + (1 - p) * (1 - qm)  # marginal-matched chance: machine's own PRESENT rate
            best = max(p, 1 - p)
            r_ans = Fraction(a["ans"], n)
            below += r_ans < chance
            below_mm += r_ans < mm
            lines.append(
                f"{run}: q={a['q']} bits={n} truePRESENT={a['tp']} truth_mismatch={a['mismatch']} | "
                f"answer-bits {a['ans']}/{n}={pct(r_ans)} selected {a['sel']}/{n}={pct(Fraction(a['sel'], n))} "
                f"margin>0 {a['mar']}/{n}={pct(Fraction(a['mar'], n))} argmax {a['arg']}/{n} | "
                f"chance {pct(chance)} best-const {pct(best)} gap-vs-const {float(100*(r_ans-best)):+.4f} | "
                f"machine PRESENT rate {a['predP']}/{n}={pct(qm)} marginal-matched chance {pct(mm)} "
                f"below-mm={r_ans < mm} | exact {a['exact']}/{a['q']}")
        lines.append(f"runs below p^2+(1-p)^2 chance: {below}/6 ; below marginal-matched chance: {below_mm}/6")
    txt = "\n".join(lines)
    print(txt)
    (pathlib.Path(__file__).parent / "verify_bits_output.txt").write_text(txt, encoding="utf-8")


if __name__ == "__main__":
    main()
