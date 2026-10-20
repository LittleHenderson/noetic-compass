"""Score one MAIN arm output on the builder's practice draw v2 with the sealed package's own scoring code
(rbw1t.merge_rbw1t.score_main / rbw1t.keys_rbw1t), and tally HELM's refusal codes the way RUN_RESULT_RBW1T_C46 did.
Also reads every lesson turn with the wide reader of <helm dir> alone (no brain) to show the reader's own code.

    python -X utf8 -I -B score_practice.py <package dir> <helm dir> <PRACTICE_DRAW_V2.json> <arm json> <out json>
"""
import collections
import importlib.util
import json
import sys
from pathlib import Path

PKG, HELM, DRAW, ARM, OUT = (Path(x).resolve() for x in sys.argv[1:6])
sys.path.insert(0, str(PKG))
from rbw1t import common_rbw1t as C    # noqa: E402
from rbw1t import merge_rbw1t as M     # noqa: E402


def load_reader(folder):
    sys.path.insert(0, str(folder))
    spec = importlib.util.spec_from_file_location("helm_wide_turn", folder / "helm_wide_turn.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["helm_wide_turn"] = mod
    spec.loader.exec_module(mod)
    return mod


def main():
    draw = json.loads(DRAW.read_text(encoding="utf-8"))
    arm = json.loads(ARM.read_text(encoding="utf-8"))
    keys = {k["id"]: k for k in draw["keys"]}
    cells = {it["id"]: it["cell"] for it in draw["items"]}
    items = {it["id"]: it for it in draw["items"]}
    sc = M.score_main(arm, keys, cells)
    T = load_reader(HELM)
    lesson_codes, first_miss, stock_codes, q_codes, reader_codes = (collections.Counter() for _ in range(5))
    reader_first = collections.Counter()
    missed_rep = []
    for r in arm["records"]:
        it = items[r["id"]]
        miss = [ls for ls in r["lessons"] if not ls["admitted"]]
        for ls in miss:
            lesson_codes[ls["status"]] += 1
        if miss:
            first_miss[miss[0]["status"]] += 1
        stock_codes[r["stock_status"]] += 1
        q_codes[r["question"]["status"]] += 1
        rc_item = []
        for j, (t, ls) in enumerate(zip(it["turns"][:it["n_lessons"]], r["lessons"])):
            if ls["admitted"]:
                continue
            rd = T.read_wide(t)
            code = rd["status"] if rd["status"] != "CLARIFY" else "READER_" + rd["clarify"]["code"]
            if rd["status"] == "WITNESS":
                code = "READ_OK_THEN_" + ls["status"]
            reader_codes[code] += 1
            rc_item.append(code)
        if rc_item:
            reader_first[rc_item[0]] += 1
        p = sc["per_item"][r["id"]]
        if p["rep"] and not p["full"]:
            missed_rep.append({"id": r["id"], "cell": it["cell"], "noun": it["noun"], "n": it["n_lines"],
                               "lesson_status": [ls["status"] for ls in r["lessons"]],
                               "reader_codes": rc_item, "q": r["question"]["status"]})
    by_stratum = {c: v for c, v in sorted(sc["by_cell"].items())}
    out = {"schema": "helm.rbw1.practice-v2-score/1", "arm": arm["arm"], "helm_dir": str(HELM),
           "arm_sha256": C.sha256_file(ARM), "totals": sc["totals"], "by_cell": by_stratum,
           "lesson_not_learned_codes": dict(lesson_codes), "first_miss_codes": dict(first_miss),
           "stock_codes": dict(stock_codes), "question_codes": dict(q_codes),
           "wide_reader_codes_on_not_learned_lessons": dict(reader_codes),
           "wide_reader_first_miss": dict(reader_first),
           "recipes_with_a_miss": sum(first_miss.values()), "missed_representable": missed_rep,
           "audit_all_ok": all(r.get("audit", {}).get("ok", True) for r in arm["records"])}
    C.write_json(OUT, out)
    t = sc["totals"]
    print(json.dumps({"fully_learned_rep": [t["fully_learned_rep"], t["rep_answer"]], "RIGHT": t["RIGHT"],
                      "WRONG": t["WRONG"], "ASKS": t["ASKS"], "lessons": [t["lessons_LEARNED"], t["lessons_WRONG"],
                                                                         t["lessons_NOT_LEARNED"]],
                      "unexplained": t["unexplained_asks"], "commit_unsettled": t["commitments_on_unsettled"],
                      "first_miss": dict(first_miss), "lesson_codes": dict(lesson_codes),
                      "reader_codes": dict(reader_codes), "reader_first": dict(reader_first),
                      "stock": dict(stock_codes), "question": dict(q_codes), "audit_all_ok": out["audit_all_ok"],
                      "by_cell": {c: [v["fully_learned_rep"], v["rep_answer"], v["RIGHT"], v["WRONG"]]
                                  for c, v in by_stratum.items()}}, indent=1))


if __name__ == "__main__":
    main()
