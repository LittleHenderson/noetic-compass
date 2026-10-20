"""Builder tool (NOT in the sealed package): failure classes of the wide READER on the published practice draw,
before (RB-W1 v1 reader at 015d340d + v1 ran-out names) and after (v2 reader at the package's helm_now + v2 names).

    python -X utf8 -B diag_classes_rbw1t.py <package dir> <v1 reader dir> <out json>

Lesson level: each lesson turn is read alone by `read_wide`; a lesson is READABLE if the reading is a witnessed batch
whose ran-out name is in the batch. Classes (the coordinator's list): ingredient-name binding (ran-out name not in the
batch; no name), quantity form / line splitting (no amount), unit (unit not in the table), duplicate ingredient (same
ingredient twice), product-name binding (no product). Pure reading; no brain, no loop.
"""
import collections
import importlib.util
import json
import sys
from pathlib import Path

PKG, V1, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
sys.path.insert(0, str(PKG))
from rbw1t import exam_rbw1t as X   # noqa: E402

CLASS = {"RAN_OUT_NOT_IN_BATCH": "name binding: ran-out name not in the batch",
         "NO_NAME": "name binding: no ingredient name", "NO_AMOUNT": "line splitting / quantity: no amount",
         "UNIT_NOT_IN_TABLE": "unit not in the 20-unit table", "SAME_INGREDIENT_TWICE": "duplicate ingredient",
         "NO_PRODUCT": "product-name binding", "AMOUNT_IS_A_RANGE": "range", "AMOUNT_APPROXIMATE": "approximate"}


def load_reader(folder):
    for n in ("helm_brain_wide", "helm_wide_turn"):
        sys.modules.pop(n, None)
    sys.path.insert(0, str(folder))
    spec = importlib.util.spec_from_file_location("helm_wide_turn", Path(folder) / "helm_wide_turn.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["helm_wide_turn"] = mod
    spec.loader.exec_module(mod)
    sys.path.remove(str(folder))
    return mod


def turns_v1(it):
    r = {"noun": it["noun"], "lines": [{"raw": x, "parsed": X.G.parse_line(x)} for x in it["raw_lines"]]}
    raw = it["raw_lines"]
    return [X.C.TEACH.format(N=it["noun"], L=X.XM.join_lines(X.XM.lesson_lines(raw, j)), H=X.name_phrase(ln["parsed"]))
            for j, ln in enumerate(r["lines"])]


def classify(T, items, keys, version):
    cls, full_rep, rep = collections.Counter(), 0, 0
    for it in items:
        lessons = turns_v1(it) if version == "v1" else it["turns"][:it["n_lessons"]]
        ok_all = True
        for t in lessons:
            r = T.read_wide(t)
            if r["status"] == "WITNESS":
                w = r["witness"]
                if w["ran_out"] and all(n in w["stock"] for n in w["ran_out"]) and len(w["ran_out"]) == 1:
                    cls["READABLE"] += 1
                    continue
                c = "RAN_OUT_NOT_IN_BATCH"
            else:
                c = (r.get("clarify") or {}).get("code") or r["status"]
            cls[c] += 1
            ok_all = False
        k = keys[it["id"]]
        if k["representable"]["representable"] and k["answer"]["key"] == "ANSWER":
            rep += 1
            full_rep += 1 if ok_all else 0
    return {"lesson_classes": dict(cls), "lessons": sum(cls.values()),
            "recipes_all_lessons_readable_of_representable_answerable": [full_rep, rep]}


def main():
    pr = json.loads((PKG / "practice" / "PRACTICE_DRAW_RBW1T.json").read_text(encoding="utf-8"))
    keys = {k["id"]: k for k in pr["keys"]}
    v1 = classify(load_reader(V1), pr["items"], keys, "v1")
    v2 = classify(load_reader(PKG / "helm_now"), pr["items"], keys, "v2")
    out = {"schema": "helm.rbw1t.reader-classes/1", "practice_seed_text": pr["seed_text"], "class_names": CLASS,
           "before_v1": v1, "after_v2": v2,
           "true_limits_left": ["UNIT_NOT_IN_TABLE (dash, sprig, box, stick, cake: outside the survey's top-20 table)",
                                "NO_AMOUNT left = alternatives ('or a ham-bone', 'superfine sugar, powdered sugar, or "
                                "granulated sugar') and vague amounts ('a little mace mixed')",
                                "SAME_INGREDIENT_TWICE (the same ingredient on two lines; the key is UNDETERMINED too)"]}
    OUT.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="ascii", newline="\n")
    print(json.dumps({"before": v1, "after": v2}, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
