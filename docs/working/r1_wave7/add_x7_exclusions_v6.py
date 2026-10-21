"""Builder tool (NOT sealed): add X7v5's ids (job c53) to contract/EXCLUDE_R1W7_PRIOR_USED.json as block X7v5_c53 (A-R1W7-6).

    python -X utf8 -B -I add_x7_exclusions_v6.py <v6 package dir> <X7_SEALED json (custodian's seal record of X7v5; ids only)>

Reads ONLY the two sorted id lists from the custodian's seal record (keys real_drawn_frame_ids_sorted / conv_pool_ids_sorted,
the v5 custodian's names; never an input or key file). Every list applies to both pools (the A-R1W7-4 rule, kept).
"""
import hashlib
import json
import sys
from pathlib import Path

pkg, sealed = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
if "exam" in sealed.parts or sealed.name.startswith("KEYS_") or sealed.name.startswith("INPUTS_"):
    raise SystemExit("REFUSED: never read an exam file: " + str(sealed))
raw = sealed.read_bytes()
x = json.loads(raw.decode("utf-8"))
real = sorted(set(x["real_drawn_frame_ids_sorted"]))
conv = sorted(set(x["conv_pool_ids_sorted"]))
if len(real) != 128 or len(conv) != 64:
    raise SystemExit(f"unexpected X7v5 counts {len(real)} / {len(conv)}")
if x.get("job") != "c53" or x.get("package_version") != "v5":
    raise SystemExit("not the c53 / v5 seal record")
path = pkg / "contract" / "EXCLUDE_R1W7_PRIOR_USED.json"
doc = json.loads(path.read_text(encoding="utf-8"))
if "X7v5_c53_real" in doc["lists"]:
    raise SystemExit("already added")
old_lists = sorted(doc["lists"])
overlap = {k: sorted(set(real) & set(v)) for k, v in doc["lists"].items() if set(real) & set(v)}
overlap_conv = {k: sorted(set(conv) & set(v)) for k, v in doc["lists"].items() if set(conv) & set(v)}
doc["lists"]["X7v5_c53_real"] = real
doc["lists"]["X7v5_c53_conv"] = conv
src = {"file": sealed.name, "folder": "<r1_wave7>/x7v5_custody", "sha256": hashlib.sha256(raw).hexdigest()}
doc["sources"]["X7v5_c53_real"] = dict(src, count=128, what="X7v5's 128 REAL ids (job c53; the custodian's seal record, ids only)")
doc["sources"]["X7v5_c53_conv"] = dict(src, count=64, what="X7v5's 64 CONV pool ids (job c53; the custodian's seal record, ids only)")
doc["blocks"]["X7v5_c53"] = {"lists": ["X7v5_c53_real", "X7v5_c53_conv"], "added": "v6 (A-R1W7-6), 2026-10-21",
                             "why": "job c53 drew and ran X7v5 from the v5 package; its ids can never be drawn again",
                             "real_ids_already_in_an_older_list": overlap, "conv_ids_already_in_an_older_list": overlap_conv}
all_lists = sorted(doc["lists"])
distinct = sorted({i for v in doc["lists"].values() for i in v})
doc["real_draw_excludes"] = {"lists": all_lists + ["+ practice/PRACTICE_POOLS_W7.json"], "distinct_ids": len(distinct),
                             "rule": "A-R1W7-4 (kept in A-R1W7-5 and A-R1W7-6): EVERY list applies to the REAL draw"}
doc["conv_pool_excludes"] = {"lists": ["everything the REAL draw excludes", "the X7 REAL draw of this package"], "extra_distinct_ids": 0,
                             "rule": "A-R1W7-4 (kept in A-R1W7-5 and A-R1W7-6): no list is conversation-pool-only"}
doc["counts"] = {k: len(v) for k, v in doc["lists"].items()}
doc["what"] = ("every recipe frame id excluded from the X7 draws of this package (PREREGISTRATION_R1W7.md sections 4.1-4.2 as amended "
               "by A-R1W7-4, A-R1W7-5 and A-R1W7-6: every list applies to both pools), ids only, read by program from the named sources; "
               "wave 7's own practice pool is practice/PRACTICE_POOLS_W7.json")
data = (json.dumps(doc, indent=1, sort_keys=True) + "\n").encode("ascii")
path.write_bytes(data)
print(json.dumps({"lists_before": len(old_lists), "lists_after": len(all_lists), "counts": doc["counts"], "distinct_all": len(distinct),
                  "real_overlap_with_older_lists": overlap, "conv_overlap_with_older_lists": overlap_conv,
                  "sha256": hashlib.sha256(data).hexdigest()}, indent=1))
