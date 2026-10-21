"""Builder tool (NOT sealed): add X7v6's ids (job c54) to contract/EXCLUDE_R1W7_PRIOR_USED.json as block X7v6_c54 (A-R1W7-8).

    python -X utf8 -B -I add_x7_exclusions_v7.py <v7 package dir> <X7_SEALED json (custodian's seal record of X7v6; ids only)>

Reads ONLY the two sorted id lists from the custodian's seal record (keys real_drawn_frame_ids_sorted / conv_pool_ids_sorted;
never an input or key file). Every list applies to both pools (the A-R1W7-4 rule, kept).
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
    raise SystemExit(f"unexpected X7v6 counts {len(real)} / {len(conv)}")
if x.get("job") != "c54" or x.get("package_version") != "v6":
    raise SystemExit("not the c54 / v6 seal record")
path = pkg / "contract" / "EXCLUDE_R1W7_PRIOR_USED.json"
doc = json.loads(path.read_text(encoding="utf-8"))
if "X7v6_c54_real" in doc["lists"]:
    raise SystemExit("already added")
old_lists = sorted(doc["lists"])
overlap = {k: sorted(set(real) & set(v)) for k, v in doc["lists"].items() if set(real) & set(v)}
overlap_conv = {k: sorted(set(conv) & set(v)) for k, v in doc["lists"].items() if set(conv) & set(v)}
doc["lists"]["X7v6_c54_real"] = real
doc["lists"]["X7v6_c54_conv"] = conv
src = {"file": sealed.name, "folder": "<r1_wave7>/x7v6_custody", "sha256": hashlib.sha256(raw).hexdigest()}
doc["sources"]["X7v6_c54_real"] = dict(src, count=128, what="X7v6's 128 REAL ids (job c54; the custodian's seal record, ids only)")
doc["sources"]["X7v6_c54_conv"] = dict(src, count=64, what="X7v6's 64 CONV pool ids (job c54; the custodian's seal record, ids only)")
doc["blocks"]["X7v6_c54"] = {"lists": ["X7v6_c54_real", "X7v6_c54_conv"], "added": "v7 (A-R1W7-8), 2026-10-21",
                             "why": "job c54 drew and ran X7v6 from the v6 package; its ids can never be drawn again",
                             "real_ids_already_in_an_older_list": overlap, "conv_ids_already_in_an_older_list": overlap_conv}
all_lists = sorted(doc["lists"])
distinct = sorted({i for v in doc["lists"].values() for i in v})
doc["real_draw_excludes"] = {"lists": all_lists + ["+ practice/PRACTICE_POOLS_W7.json"], "distinct_ids": len(distinct),
                             "rule": "A-R1W7-4 (kept in A-R1W7-5, A-R1W7-6 and A-R1W7-8): EVERY list applies to the REAL draw"}
doc["conv_pool_excludes"] = {"lists": ["everything the REAL draw excludes", "the X7 REAL draw of this package"], "extra_distinct_ids": 0,
                             "rule": "A-R1W7-4 (kept in A-R1W7-5, A-R1W7-6 and A-R1W7-8): no list is conversation-pool-only"}
doc["counts"] = {k: len(v) for k, v in doc["lists"].items()}
doc["what"] = ("every recipe frame id excluded from the X7 draws of this package (PREREGISTRATION_R1W7.md sections 4.1-4.2 as amended "
               "by A-R1W7-4, A-R1W7-5, A-R1W7-6 and A-R1W7-8: every list applies to both pools), ids only, read by program from the named "
               "sources; wave 7's own practice pool is practice/PRACTICE_POOLS_W7.json")
data = (json.dumps(doc, indent=1, sort_keys=True) + "\n").encode("ascii")
path.write_bytes(data)
print(json.dumps({"lists_before": len(old_lists), "lists_after": len(all_lists), "counts": doc["counts"], "distinct_all": len(distinct),
                  "real_overlap_with_older_lists": overlap, "conv_overlap_with_older_lists": overlap_conv,
                  "sha256": hashlib.sha256(data).hexdigest()}, indent=1))
