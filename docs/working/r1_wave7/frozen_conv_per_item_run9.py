"""Builder tool (NOT sealed): the FROZEN dialogue scorer's own per-item verdicts (wave 6's `score_conv` through the sealed v7
package, `common_w7.setup(helm=False)`) for run9 (v7 cut) and run8 (v6 cut): which items are WRONG / RIGHT / UNDETERMINED in
each, and the items that moved. Practice data only.

    python -X utf8 -B -I frozen_conv_per_item_run9.py <sealed v7 extract pkg> <run9 dir> <run8 dir> <practice inputs dir> <out json>
"""
import json
import sys
from pathlib import Path

pkg, run9, run8, prac, out = [Path(a).resolve() for a in sys.argv[1:6]]
sys.path.insert(0, str(pkg))
from r1w7 import common_w7 as C  # noqa: E402

ns = C.setup(helm=False)
keys = json.loads((prac / "exam" / "KEYS_CONV_X7.json").read_text(encoding="utf-8"))["keys"]
res = {"schema": "helm.r1w7.frozen-conv-per-item/1", "units": {}}
for name in ("W7_X7_CONV_CHAT_ON", "W7_X7_CONV_LOOP_ON", "W7_X7_NOISE_CHAT_ON", "W7_X7_CONV_CHAT_OFF", "W7_X7_CONV_CHAT_ON_REPLAY", "W7_X7_CONV_CHAT_DIAG"):
    row = {}
    for tag, d in (("run9", run9), ("run8", run8)):
        doc = json.loads((d / "units" / f"{name}.json").read_text(encoding="utf-8"))
        s = ns.SC6.score_conv(ns, keys, doc)
        row[tag] = {"totals": s["totals"], "per_item": {p["id"]: p["score"] for p in s["per_item"]},
                    "families": {p["id"]: p["family"] for p in s["per_item"]}}
    moved = {i: {"run8": row["run8"]["per_item"].get(i), "run9": v, "family": row["run9"]["families"][i]}
             for i, v in row["run9"]["per_item"].items() if row["run8"]["per_item"].get(i) != v}
    wrong9 = sorted(i for i, v in row["run9"]["per_item"].items() if v == "WRONG")
    res["units"][name] = {"run9_totals": row["run9"]["totals"], "run8_totals": row["run8"]["totals"],
                          "run9_wrong_items": [(i, row["run9"]["families"][i], row["run8"]["per_item"].get(i)) for i in wrong9],
                          "moved_items": moved,
                          "moved_by_family": {f: sorted({f"{m['run8']}->{m['run9']}" for m in moved.values() if m["family"] == f})
                                              for f in sorted({m["family"] for m in moved.values()})},
                          "moved_counts": {k: sum(1 for m in moved.values() if f"{m['run8']}->{m['run9']}" == k)
                                           for k in sorted({f"{m['run8']}->{m['run9']}" for m in moved.values()})}}
out.write_bytes((json.dumps(res, indent=1, sort_keys=True) + "\n").encode("utf-8"))
print(json.dumps({n: {k: v[k] for k in ("run9_totals", "run8_totals", "run9_wrong_items", "moved_by_family", "moved_counts")}
                  for n, v in res["units"].items()}, indent=1))
