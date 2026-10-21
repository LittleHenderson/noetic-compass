"""Re-measure the LM-T1 marks from the code in this folder. Prints exact numbers. Makes no claim.

This is NOT a run. A run (`worker.py`) needs a single-use owner permit, blocks sockets and writes receipts to
`runs/`. This tool skips the permit and the socket block, calls the same scoring functions in the same order, and
prints the same numbers so a reader can compare a before and an after on one machine. Nothing here is written to
`runs/` and nothing here may be used as a run record.

Usage, from this folder:
    C:\\Python314\\python.exe -X utf8 -B measure_marks.py
with PYTHONPATH set as recorded in PROVENANCE.md (sdg_bridge_v2 and lacunarity_machine are imported read-only).
"""
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
BRIDGE_ROOT = Path(r"C:\Users\wakil\Documents\Codex\CAS-Recipe-Network-Comparison-20261011")
LACUNA_ROOT = Path(r"C:\Users\wakil\Documents\Codex\2026-10-14\lacunarity_machine_v1")


def main():
    for p in (HERE, LACUNA_ROOT, BRIDGE_ROOT):
        sys.path.insert(0, str(p))
    import cce
    import coverage
    import scoring

    frozen = json.loads((HERE / "FROZEN.json").read_text("utf-8"))
    hs_freeze = json.loads((HERE / "handset" / "HAND_SET_FREEZE.json").read_text("utf-8"))
    hs_raw = (HERE / "handset" / "HAND_SET_v0_1.json").read_bytes()
    hand_set_sha_ok = hashlib.sha256(hs_raw).hexdigest() == hs_freeze["sha256"]
    items = json.loads(hs_raw.decode("utf-8"))["items"]
    out = {"hand_set_sha256_matches_freeze": hand_set_sha_ok, "cce_version": cce.CCE_VERSION}

    recipes = scoring.load_recipes()
    r1 = scoring.m1(recipes)
    out["M1"] = {k: r1[k] for k in ("recipes", "round_trip_ok", "pass")}

    r2 = scoring.m2(recipes)
    out["M2"] = {k: v for k, v in r2.items()}

    r6, _ = coverage.run_main()
    side = coverage.side_universes()
    rows6 = r6["rows"]
    out["M6"] = {
        "n_eligible": r6["n_eligible"],
        "state_counts": r6["state_counts"],
        "covered_without_charge": sum(r["covered_without_charge"] for r in rows6),
        "covered_with_receipt": sum(1 for r in rows6 if r["state"] == "COVERED" and r["receipt_id"]),
        "pass": (r6["n_eligible"] == 2600 and sum(r6["state_counts"].values()) == 2600
                 and not any(r["covered_without_charge"] for r in rows6)
                 and all(r["receipt_id"] for r in rows6 if r["state"] == "COVERED")),
    }
    out["M6_side"] = {name: {"cells": len(u["rows"]), "state_counts": u["state_counts"],
                             "gap_set": u["gap_set"]} for name, u in side.items()}

    back = []
    for r in recipes:
        try:
            back.append(cce.parse(cce.render(r["content"])))
        except Exception:
            back.append(None)
    terms = []
    probe_contents = []
    for f, n in coverage.pairs():
        for d in cce.DOMAINS:
            for rv in coverage.REG_VALUES:
                pc = coverage.probe_content(f, n, d, rv)
                probe_contents.append(pc)
                terms += scoring.walk_terms(pc)
    gold_contents = []
    for it in items:
        if "content" in it["expect"]:
            try:
                cce.canonical(it["expect"]["content"])
                gold_contents.append(it["expect"]["content"])
                terms += scoring.walk_terms(it["expect"]["content"])
            except Exception:
                pass
    r7 = scoring.m7(recipes, back, terms)
    out["M7"] = {k: v for k, v in r7.items() if k != "rows_disagree"}

    lookup = scoring.Lookup([r["content"] for r in recipes] + gold_contents + probe_contents)
    r3 = scoring.m3(items, lookup)
    out["M3"] = {k: v for k, v in r3.items() if k != "rows"}

    excluded = set(frozen["headline_rows"]["excluded_42_seed_ids"])
    eng_rows, total_rows = scoring.load_english(excluded)
    r4 = scoring.m4(eng_rows, lookup)
    r5 = scoring.m5(eng_rows)
    r5b = scoring.m5b(eng_rows)
    r4.pop("rows", None)
    r4["rows_in_files"] = total_rows
    r4["recipe_rows"] = len(eng_rows)
    out["M4"] = r4
    out["M5"] = r5
    out["M5b"] = r5b

    hard = {"M1": r1["pass"], "M2": r2["pass"], "M3": r3["pass"],
            "M5_00459": r5["positive_control_00459_mismatch"], "M5b": r5b["pass"],
            "M6": out["M6"]["pass"], "M7": r7["pass"]}
    out["hard_marks"] = hard
    out["LM_T1_core"] = "PASS" if all(hard.values()) else "FAILURE"
    out["failed_hard_marks"] = [k for k, v in hard.items() if not v]
    print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
