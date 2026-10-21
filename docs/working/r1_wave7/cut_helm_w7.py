"""Builder tool (NOT sealed): cut HELM's code under test into the package as helm_now/ (wave 7, the CHAT WAVE).

    python -X utf8 -B -I cut_helm_w7.py <repo> <commit> <package dir> <wave-6 package dir>

File list = wave 6 v3's helm_now/SOURCE_CUT.json list (159 files) + every other `helm_*.py` / `test_helm_*.py` at the
commit (test_helm_agentic_planner.py, test_helm_memory.py). `helm_ui/` and `helm_hub/` are NOT cut (the chat's
session log must have no default home inside the package; HELM_SESSION_DIR points into the unit scratch). Every file
is read by `git show <commit>:<path>` (never the working tree). Writes helm_now/SOURCE_CUT.json and
contract/HELM_CUT_R1W7.json (same rows; the commit; the pinned base of helm_brain_canonical.py).
"""
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

repo, ref, pkg, w6 = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4])
BASE_CANONICAL_COMMIT = "d4488f2a4a32992f6d8f80f24ea8cefe045ac9d7"      # RB-W1T's scored base of helm_brain_canonical.py


def git(*args, binary=False):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=True)
    return r.stdout if binary else r.stdout.decode("utf-8").strip()


commit = git("rev-parse", ref)
w6_cut = json.loads((w6 / "helm_now" / "SOURCE_CUT.json").read_text(encoding="utf-8"))
tree = git("ls-tree", "-r", "--name-only", commit).splitlines()
extra = [p for p in tree if "/" not in p and (p.startswith("helm_") or p.startswith("test_helm_")) and p.endswith(".py")]
files = sorted(set(w6_cut["files"]) | set(extra))
missing = [f for f in files if f not in set(tree)]
if missing:
    raise SystemExit("files of the wave-6 list missing at the commit: %r" % missing)
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
       "rule": "git show <commit>:<path> for every file (never the working tree); list = wave 6 v3's cut (159 files) "
               "+ every helm_*.py / test_helm_*.py at the commit; helm_ui/ and helm_hub/ are not cut",
       "helm_brain_canonical_base": {"commit": BASE_CANONICAL_COMMIT, "sha256": base,
                                     "equal_to_cut": base == rows["helm_brain_canonical.py"]["sha256"]},
       "not_cut": ["helm_ui/", "helm_hub/"]}
data = (json.dumps(doc, indent=1, sort_keys=True) + "\n").encode("ascii")
(out / "SOURCE_CUT.json").write_bytes(data)
(pkg / "contract").mkdir(exist_ok=True)
(pkg / "contract" / "HELM_CUT_R1W7.json").write_bytes(data)
print(json.dumps({"commit": commit, "files": len(rows), "added_vs_w6": sorted(set(files) - set(w6_cut["files"])),
                  "canonical_base_equal": doc["helm_brain_canonical_base"]["equal_to_cut"],
                  "cut_sha256": hashlib.sha256(data).hexdigest()}))
