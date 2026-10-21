"""Builder tool (NOT sealed): compare two practice input folders (v6 practice vs a v7 practice draw): inputs byte-equal,
keys equal except `representable`, the MULTI_QTY-tagged items counted (ids only, counts only; practice data, never an exam).

    python -X utf8 -B -I compare_practice_keys.py <practice dir A (v6)> <practice dir B (v7)> [<out json>]
"""
import hashlib
import json
import sys
from pathlib import Path

A, B = Path(sys.argv[1]), Path(sys.argv[2])


def load(p):
    d = json.loads(Path(p).read_text(encoding="utf-8"))
    return d["keys"] if isinstance(d, dict) and "keys" in d else d


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


ka, kb = load(A / "exam" / "KEYS_REAL_X7.json"), load(B / "exam" / "KEYS_REAL_X7.json")
rep = lambda k: bool(k["representable"]["representable"])
mq = [i for i, k in enumerate(kb) if any("MULTI_QTY" in w for w in k["representable"].get("why_not", []))]
kind_field = next((f for f in ("kind", "key_kind", "answer_kind", "status") if f in ka[0]), None)
out = {"items": len(ka), "v6_representable": sum(rep(k) for k in ka), "v7_representable": sum(rep(k) for k in kb),
       "multi_qty_items": len(mq), "multi_qty_item_ids": [kb[i].get("frame_id") or kb[i].get("id") for i in mq],
       "multi_qty_lines_per_item": [sum(1 for w in kb[i]["representable"]["why_not"] if "MULTI_QTY" in w) for i in mq],
       "tagged_items_were_representable_in_v6": sum(1 for i in mq if rep(ka[i])),
       "key_fields": sorted(ka[0].keys()), "kind_field": kind_field,
       "tagged_items_kind_in_v6": [ka[i].get(kind_field) for i in mq] if kind_field else None,
       "tagged_items_have_answer_in_v6": [ka[i].get("answer") is not None for i in mq],
       "tagged_items_why_not_v6": [ka[i]["representable"].get("why_not") for i in mq],
       "tagged_items_why_not_v7": [kb[i]["representable"].get("why_not") for i in mq],
       "all_other_key_fields_equal": all({k: v for k, v in ka[i].items() if k != "representable"} ==
                                        {k: v for k, v in kb[i].items() if k != "representable"} for i in range(len(ka))),
       "untagged_items_representable_equal": all(rep(ka[i]) == rep(kb[i]) for i in range(len(ka)) if i not in mq),
       "inputs_sha256_equal": {n: sha(A / "exam" / n) == sha(B / "exam" / n)
                               for n in ("INPUTS_REAL_X7.json", "INPUTS_CONV_X7.json", "INPUTS_NOISE_X7.json", "KEYS_CONV_X7.json", "POOLS_X7.json")},
       "carrier_sha256_equal": {n: sha(A / "carrier" / "x7" / n) == sha(B / "carrier" / "x7" / n)
                                for n in ("INPUTS_REAL_X7.json", "INPUTS_CONV_X7.json", "INPUTS_NOISE_X7.json")}}
if len(sys.argv) > 3:
    Path(sys.argv[3]).write_bytes((json.dumps(out, indent=1, sort_keys=True) + "\n").encode("utf-8"))
print(json.dumps(out, indent=1, sort_keys=True))
