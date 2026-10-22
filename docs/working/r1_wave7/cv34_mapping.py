"""Builder tool (NOT sealed): the CV34 limiting-line mapping, by program, through the frozen scorer's own functions.
The key's limiting line is named by a head in one surface form (hyphenated); HELM's wide path names the same ingredient in
another (singular, space). RB-W1T's `keys_rbw1t.line_of` maps HELM's `limiting` name first through HELM's own admitted lesson
records (the record's `ingredient` string, lower-cased, to the lesson line index), and only if no record names it, through the
plural fold of the last word against the key heads. This tool prints what the key names, what HELM names, which rule mapped it,
and the frozen scorer's verdict. Practice item only (the published practice pools); the recipe text is not printed.

    python -X utf8 -B -I cv34_mapping.py <sealed v8 extract pkg> <run10 dir> <practice inputs dir> <out json> [<item prefix>=CV34]
"""
import json
import sys
from pathlib import Path

pkg, run10, prac, out = [Path(a).resolve() for a in sys.argv[1:5]]
prefix = sys.argv[5] if len(sys.argv) > 5 else "CV34"
sys.path.insert(0, str(pkg))
from r1w7 import common_w7 as C  # noqa: E402

ns = C.setup(helm=False)
K = ns.rb.keys_rbw1t
RC = ns.rb.common_rbw1t
keys = json.loads((prac / "exam" / "KEYS_CONV_X7.json").read_text(encoding="utf-8"))["keys"]
res = {"schema": "helm.r1w7.cv34-mapping/1", "items": {}}
for unit in ("W7_X7_CONV_CHAT_ON", "W7_X7_CONV_LOOP_ON", "W7_X7_NOISE_CHAT_ON"):
    doc = json.loads((run10 / "units" / f"{unit}.json").read_text(encoding="utf-8"))
    by_id = {r["id"]: r for r in doc["records"]}
    for key in keys:
        if not key["id"].startswith(prefix):
            continue
        rec = by_id[key["id"]]
        st = rec.get("scored_turn") or {}
        lessons = (rec.get("lesson_records") or [])[:len(key["heads"])]
        lm = K.lesson_map(lessons)
        limiting = st.get("limiting")
        n = str(limiting or "").lower()
        via_records = lm.get(n)
        hn = RC.head_norm(RC.last_word(limiting))
        via_fold = [i for i, h in enumerate(key["heads"]) if h and RC.head_norm(h) == hn]
        mapped = K.line_of(limiting, {"lessons": [{"head": h} for h in key["heads"]]}, lessons)
        res["items"][f"{unit}/{key['id']}"] = {
            "family": key["family"], "expect": key["expect"], "key_yield": key["yield"], "key_limiting_index": key["limiting_index"],
            "key_limiting_head": key["heads"][key["limiting_index"]], "key_heads": key["heads"],
            "helm_status": st.get("status"), "helm_value": st.get("value"), "helm_limiting_name": limiting,
            "helm_lesson_record_ingredients": [r.get("ingredient") for r in lessons],
            "rule_1_lesson_records": {"name_in_records": n in lm, "lines": via_records},
            "rule_2_plural_fold_of_last_word": {"last_word": RC.last_word(limiting), "head_norm": hn,
                                                "key_head_norms": [RC.head_norm(h) for h in key["heads"]], "unique_hit_lines": via_fold},
            "line_of_result": mapped, "mapped_rule": ("lesson records" if n in lm else ("plural fold of the last word" if len(via_fold) == 1 else "none")),
            "limiting_matches_key": mapped == key["limiting_index"],
            "frozen_scorer_verdict": ns.GC.score_item(ns, key, rec)}
out.write_bytes((json.dumps(res, indent=1, sort_keys=True) + "\n").encode("utf-8"))
print(json.dumps(res, indent=1, sort_keys=True))
