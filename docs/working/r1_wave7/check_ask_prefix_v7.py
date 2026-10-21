"""Builder tool (NOT sealed): confirm by program that the reader-gap cut's new wide statuses count as asks under the frozen
ask rule the wave-7 reader uses (RB-W1T's `keys_rbw1t.is_asking`, reached through wave 6's `score_real`), and that the v7
reader files are byte-identical to v6's (the reader's rules do not change).

    python -X utf8 -B -I check_ask_prefix_v7.py <v7 package dir> <v6 extract package dir> <deps dir> [<out json>]
"""
import hashlib
import importlib
import json
import sys
from pathlib import Path

pkg, v6, deps = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve(), Path(sys.argv[3]).resolve()
sys.path.insert(0, str(deps / "HELM_RBW1T_20261019"))
K = importlib.import_module("rbw1t.keys_rbw1t")
NEW = ["CLARIFY_WIDE_PURPOSE_ABSENT", "CLARIFY_WIDE_INGREDIENT_PURPOSE_ABSENT", "CLARIFY_WIDE_FACE_UNREAD",
       "CLARIFY_WIDE_FACE_NEGATED", "CLARIFY_WIDE_FACE_WHICH_INGREDIENT", "CLARIFY_WIDE_FACE_REFUSED", "CLARIFY_WIDE_FACE_UNKNOWN"]
src = (pkg / "helm_now" / "helm_wide_turn.py").read_text(encoding="utf-8") + (pkg / "helm_now" / "helm_faces_in.py").read_text(encoding="utf-8")
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
out = {"asking_prefix": list(K.ASKING_PREFIX), "asking_exact": list(K.ASKING_EXACT),
       "new_statuses_are_asks": {s: K.is_asking(s) for s in NEW},
       "new_statuses_named_in_the_cut": {s: (s in src) for s in NEW},
       "non_ask_controls": {s: K.is_asking(s) for s in ("INVENTORY_RECORDED", "STOCK_RECORDED", "COMMITTED", "LEARNED")},
       "reader_files_byte_identical_v6_v7": {f: sha(pkg / "r1w7" / f) == sha(v6 / "r1w7" / f) for f in ("score_w7.py", "merge_r1w7.py")},
       "reader_sha256_v7": {f: sha(pkg / "r1w7" / f) for f in ("score_w7.py", "merge_r1w7.py")}}
out["all_new_statuses_count_as_asks"] = all(out["new_statuses_are_asks"].values())
if len(sys.argv) > 4:
    Path(sys.argv[4]).write_bytes((json.dumps(out, indent=1, sort_keys=True) + "\n").encode("utf-8"))
print(json.dumps(out, indent=1, sort_keys=True))
assert out["all_new_statuses_count_as_asks"] and all(out["reader_files_byte_identical_v6_v7"].values())
assert not any(out["non_ask_controls"].values())
