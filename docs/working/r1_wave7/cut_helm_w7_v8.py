"""Builder tool (NOT sealed): cut HELM's code under test into the v8 package as helm_now/ (wave 7, the CHAT WAVE, v8).

    python -X utf8 -B -I cut_helm_w7_v8.py <repo> <commit> <package dir> <v7 package dir>

File list = the v7 cut's list (helm_now/SOURCE_CUT.json of v7, 167 files) + every other `helm_*.py` / `test_helm_*.py` at
the commit (v8: none expected; the v7.1 fix changed four files that were already in the cut); `helm_test_pins.py` named
explicitly (as v6 / v7). `helm_ui/` and `helm_hub/` are NOT cut. Every file is read by `git show <commit>:<path>` (never the
working tree). Writes helm_now/SOURCE_CUT.json and contract/HELM_CUT_R1W7.json (same rows; the commit; the pinned base of
helm_brain_canonical.py).
"""
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

repo, ref, pkg, v7 = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4])
BASE_CANONICAL_COMMIT = "d4488f2a4a32992f6d8f80f24ea8cefe045ac9d7"      # RB-W1T's scored base of helm_brain_canonical.py
NAMED = ["helm_test_pins.py"]


def git(*args, binary=False):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=True)
    return r.stdout if binary else r.stdout.decode("utf-8").strip()


commit = git("rev-parse", ref)
v7_cut = json.loads((v7 / "helm_now" / "SOURCE_CUT.json").read_text(encoding="utf-8"))
tree = git("ls-tree", "-r", "--name-only", commit).splitlines()
extra = [p for p in tree if "/" not in p and (p.startswith("helm_") or p.startswith("test_helm_")) and p.endswith(".py")]
files = sorted(set(v7_cut["files"]) | set(extra) | set(NAMED))
missing = [f for f in files if f not in set(tree)]
if missing:
    raise SystemExit("files of the v7 list missing at the commit: %r" % missing)
out = pkg / "helm_now"
if out.exists():
    shutil.rmtree(out)
rows = {}
for rel in files:
    data = git("show", f"{commit}:{rel}", binary=True)
    p = out / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    rows[rel] = {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
base = hashlib.sha256(git("show", f"{BASE_CANONICAL_COMMIT}:helm_brain_canonical.py", binary=True)).hexdigest()
doc = {"schema": "helm.r1w7.source-cut/1", "commit": commit, "files": rows,
       "rule": "git show <commit>:<path> for every file (never the working tree); list = the v7 cut (167 files, itself the v6 cut's "
               "166 + test_helm_reader_gap.py; v6 = wave 6 v3's 159 + every helm_*.py / test_helm_*.py + helm_test_pins.py named) + "
               "every helm_*.py / test_helm_*.py at the commit (v8: no new file; the v7.1 fix changed four files already in the cut); "
               "helm_ui/ and helm_hub/ are not cut",
       "helm_brain_canonical_base": {"commit": BASE_CANONICAL_COMMIT, "sha256": base,
                                     "equal_to_cut": base == rows["helm_brain_canonical.py"]["sha256"]},
       "not_cut": ["helm_ui/", "helm_hub/"]}
data = (json.dumps(doc, indent=1, sort_keys=True) + "\n").encode("ascii")
(out / "SOURCE_CUT.json").write_bytes(data)
(pkg / "contract").mkdir(exist_ok=True)
(pkg / "contract" / "HELM_CUT_R1W7.json").write_bytes(data)
changed = sorted(k for k in rows if k in v7_cut["files"] and v7_cut["files"][k]["sha256"] != rows[k]["sha256"])
print(json.dumps({"commit": commit, "files": len(rows), "added_vs_v7": sorted(set(files) - set(v7_cut["files"])),
                  "removed_vs_v7": sorted(set(v7_cut["files"]) - set(files)), "changed_vs_v7": changed,
                  "changed_sha256": {k: rows[k]["sha256"] for k in changed},
                  "canonical_base_equal": doc["helm_brain_canonical_base"]["equal_to_cut"],
                  "cut_sha256": hashlib.sha256(data).hexdigest()}, indent=1))
