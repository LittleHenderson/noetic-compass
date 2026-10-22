"""Builder tool (NOT in the sealed package): cut HELM's code into the package's helm_now/ by `git show`.

    python -X utf8 -B cut_helm_teach1.py --commit <sha>     (run from the repository root)

Rule (pre-code 2, "the package carries its own copy by git show"): `git show <commit>:<path>` for every file, never the
working tree. List = wave 7 v8's cut (167 files, docs/working/r1_wave7/HELM_CUT_R1W7_v8.json, read from the commit) +
every helm_*.py / test_helm_*.py at the commit (adds helm_memory_compact.py and test_helm_memory_compact.py) + the
compactor's three tools: the compiler of record (noetic-compass-scaffold/noetic-compass/api/__init__.py,
api/notation/__init__.py, api/notation/compiler.py) and the Atlas (docs/working/noetic_council/continuity_build_v2/atlas.py);
the CCE skin (language_v3/cce.py) is already in the v8 list. helm_ui/ and helm_hub/ are not cut. Writes
helm_now/SOURCE_CUT.json and contract/HELM_CUT_TEACH1.json (byte-identical), with the pinned files of I3.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE / "HELM_TEACH1_20261021"
V8_CUT = "docs/working/r1_wave7/HELM_CUT_R1W7_v8.json"
TOOLS = ("noetic-compass-scaffold/noetic-compass/api/__init__.py",
         "noetic-compass-scaffold/noetic-compass/api/notation/__init__.py",
         "noetic-compass-scaffold/noetic-compass/api/notation/compiler.py",
         "docs/working/noetic_council/continuity_build_v2/atlas.py")
PINNED = ("helm_brain_canonical.py", "helm_brain_wide.py", "noetic-compass-scaffold/noetic-compass/api/notation/compiler.py",
          "helm_memory.py", "helm_memory_compact.py", "helm_chat.py")


def git(*args: str) -> bytes:
    return subprocess.run(["git", *args], check=True, capture_output=True).stdout


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", required=True)
    a = ap.parse_args()
    commit = git("rev-parse", a.commit).decode().strip()
    v8 = json.loads(git("show", f"{commit}:{V8_CUT}"))
    names = set(v8["files"])
    for p in git("ls-tree", "--name-only", commit).decode().splitlines():
        if (p.startswith("helm_") and p.endswith(".py")) or (p.startswith("test_helm_") and p.endswith(".py")):
            names.add(p)
    names.update(TOOLS)
    hn = PKG / "helm_now"
    if hn.exists():
        for f in sorted(hn.rglob("*"), reverse=True):
            f.unlink() if f.is_file() else f.rmdir()
    files = {}
    for rel in sorted(names):
        raw = git("show", f"{commit}:{rel}")
        dest = hn / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw)
        files[rel] = {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
    doc = {"schema": "helm.teach1.source-cut/1", "commit": commit,
           "rule": "git show <commit>:<path> for every file (never the working tree); list = wave 7 v8's cut (167) + every "
                   "helm_*.py / test_helm_*.py at the commit + the compiler of record (api/__init__.py, api/notation/__init__.py, "
                   "api/notation/compiler.py) + the Atlas (continuity_build_v2/atlas.py); helm_ui/ and helm_hub/ are not cut",
           "files": files, "pinned": {rel: files[rel]["sha256"] for rel in PINNED},
           "not_cut": ["helm_ui/", "helm_hub/"]}
    data = (json.dumps(doc, indent=1, sort_keys=True) + "\n").encode("ascii")
    (hn / "SOURCE_CUT.json").write_bytes(data)
    (PKG / "contract").mkdir(parents=True, exist_ok=True)
    (PKG / "contract" / "HELM_CUT_TEACH1.json").write_bytes(data)
    print(json.dumps({"commit": commit, "files": len(files), "cut_sha256": hashlib.sha256(data).hexdigest(),
                      "pinned": doc["pinned"]}, indent=1))


if __name__ == "__main__":
    main()
