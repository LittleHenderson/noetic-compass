"""Builder tool (NOT sealed): confirm by program that every ask status the v8 cut's wide reader can emit counts as an ask under
the frozen ask rule the wave-7 reader uses (RB-W1T's `keys_rbw1t.is_asking`, reached through wave 6's `score_real`), that the v8
reader files are byte-identical to v7's (the reader's rules do not change), and which wide statuses the v7.1 fix added or
removed against the v7 cut (read from the code of both cuts: the `CLARIFY_WIDE_<code>` f-string takes the face reader's clarify
codes and the wide reader's own codes; both are listed from the source by regular expression).

    python -X utf8 -B -I check_ask_prefix_v8.py <v8 package dir> <v7 extract package dir> <deps dir> [<out json>]
"""
import hashlib
import importlib
import json
import re
import sys
from pathlib import Path

pkg, v7, deps = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve(), Path(sys.argv[3]).resolve()
sys.path.insert(0, str(deps / "HELM_RBW1T_20261019"))
K = importlib.import_module("rbw1t.keys_rbw1t")
V7_LIST = ["CLARIFY_WIDE_PURPOSE_ABSENT", "CLARIFY_WIDE_INGREDIENT_PURPOSE_ABSENT", "CLARIFY_WIDE_FACE_UNREAD",
           "CLARIFY_WIDE_FACE_NEGATED", "CLARIFY_WIDE_FACE_WHICH_INGREDIENT", "CLARIFY_WIDE_FACE_REFUSED", "CLARIFY_WIDE_FACE_UNKNOWN"]


def statuses(root):
    wt = (root / "helm_now" / "helm_wide_turn.py").read_text(encoding="utf-8")
    fi = (root / "helm_now" / "helm_faces_in.py").read_text(encoding="utf-8")
    literal = set(re.findall(r"CLARIFY_WIDE_[A-Z_]+", wt))
    face_codes = set(re.findall(r'"code":\s*"([A-Z_]+)"', fi)) | set(re.findall(r"code=\"([A-Z_]+)\"", fi))
    wide_codes = set(re.findall(r'"code":\s*"([A-Z_]+)"', wt)) | set(re.findall(r"code=\"([A-Z_]+)\"", wt))
    composed = {"CLARIFY_WIDE_" + c for c in (face_codes | wide_codes)}
    return {"literal_in_wide_turn": sorted(literal), "face_reader_codes": sorted(face_codes), "wide_reader_codes": sorted(wide_codes),
            "all_possible": sorted(literal | composed)}


sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
s8, s7 = statuses(pkg), statuses(v7)
all8 = [s for s in s8["all_possible"] if s != "CLARIFY_WIDE_"]
out = {"asking_prefix": list(K.ASKING_PREFIX), "asking_exact": list(K.ASKING_EXACT),
       "v8_cut_statuses": s8, "v7_cut_statuses": s7,
       "added_by_v7_1": sorted(set(s8["all_possible"]) - set(s7["all_possible"])),
       "removed_by_v7_1": sorted(set(s7["all_possible"]) - set(s8["all_possible"])),
       "every_v8_wide_status_is_an_ask": {s: K.is_asking(s) for s in all8},
       "v7_list_of_seven_are_asks": {s: K.is_asking(s) for s in V7_LIST},
       "non_ask_controls": {s: K.is_asking(s) for s in ("INVENTORY_RECORDED", "STOCK_RECORDED", "COMMITTED", "LEARNED")},
       "reader_files_byte_identical_v7_v8": {f: sha(pkg / "r1w7" / f) == sha(v7 / "r1w7" / f) for f in ("score_w7.py", "merge_r1w7.py")},
       "reader_sha256_v8": {f: sha(pkg / "r1w7" / f) for f in ("score_w7.py", "merge_r1w7.py")}}
out["all_new_statuses_count_as_asks"] = all(out["every_v8_wide_status_is_an_ask"].values()) and all(out["v7_list_of_seven_are_asks"].values())
if len(sys.argv) > 4:
    Path(sys.argv[4]).write_bytes((json.dumps(out, indent=1, sort_keys=True) + "\n").encode("utf-8"))
print(json.dumps(out, indent=1, sort_keys=True))
assert out["all_new_statuses_count_as_asks"] and all(out["reader_files_byte_identical_v7_v8"].values())
assert not any(out["non_ask_controls"].values())
