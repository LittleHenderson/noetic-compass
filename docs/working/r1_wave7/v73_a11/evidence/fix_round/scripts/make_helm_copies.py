"""make_helm_copies.py <fix2 dir> -- three scratch HELM copies for the fix round (never the worktree, never the sealed tree):
  helm_v72   = the sealed v9 helm_now, checked byte-equal to the v9 zip members (reader v7.2)
  helm_v73r  = helm_v72 with ONLY helm_wide_turn.py, test_helm_reader_gap.py, test_helm_cas_address.py from the worktree
  helm_wt    = every HELM cut file (contract/HELM_CUT_R1W7.json's 167 paths) at its WORKTREE version, plus
               helm_memory_compact.py and test_helm_memory_compact.py (branch head's compaction pair), for the all-HELM-test run
Prints one JSON summary. Standard library only."""
import hashlib
import json
import shutil
import sys
import zipfile
from pathlib import Path

ZIP = Path(r"C:\Users\wakil\Documents\Codex\2026-10-20\r1_wave7\build_v9\HELM_R1_W7_20261020_SOURCE_R1W7_v9.zip")
ZIP_SHA = "ad3fb98cd3254963263929747791d151949c2f50923672e4bcbf3fc14490942c"
TOP = "HELM_R1_W7_20261020/"
WT = Path(r"C:\tmp\helm-ctt2r-c49-read")
SWAP = ("helm_wide_turn.py", "test_helm_reader_gap.py", "test_helm_cas_address.py")
EXTRA = ("helm_memory_compact.py", "test_helm_memory_compact.py")


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main(fix2):
    fix2 = Path(fix2)
    zb = ZIP.read_bytes()
    assert sha(zb) == ZIP_SHA, "zip sha mismatch"
    z = zipfile.ZipFile(ZIP)
    members = {n[len(TOP) + len("helm_now/"):]: z.read(n) for n in z.namelist()
               if n.startswith(TOP + "helm_now/") and not n.endswith("/")}
    cut = json.loads(z.read(TOP + "contract/HELM_CUT_R1W7.json"))
    out = {"zip_sha256": ZIP_SHA, "helm_now_members": len(members), "cut_files": len(cut["files"])}
    for label in ("helm_v72", "helm_v73r", "helm_wt"):
        d = fix2 / label
        if d.exists():
            shutil.rmtree(d)
    for label in ("helm_v72", "helm_v73r"):
        d = fix2 / label
        for rel, b in members.items():
            p = d / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b)
    swapped = {}
    for rel in SWAP:
        b = (WT / rel).read_bytes()
        (fix2 / "helm_v73r" / rel).write_bytes(b)
        swapped[rel] = {"v9": sha(members[rel]), "worktree": sha(b)}
    out["helm_v73r_swapped"] = swapped
    d = fix2 / "helm_wt"
    differ = []
    for rel in cut["files"]:
        b = (WT / rel).read_bytes()
        p = d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b)
        if b != members.get(rel):
            differ.append(rel)
    for rel in EXTRA:
        (d / rel).write_bytes((WT / rel).read_bytes())
    out["helm_wt_differs_from_v9_cut"] = sorted(differ)
    out["helm_wt_extra"] = list(EXTRA)
    print(json.dumps(out, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
