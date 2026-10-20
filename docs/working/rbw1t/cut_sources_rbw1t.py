"""Builder tool (NOT in the sealed package): cut HELM's live sources twice, with `git show <commit>:<path>` (never the
working tree): helm_now/ at the RB-W1 merge 015d340d and helm_base/ at its parent d4488f2a. File list = wave 3's
cut_sources.py list (TOP + council DIRS + vendor_ext) plus the RB-W1 files (now only) and the stock-frame test.

    python -B cut_sources_rbw1t.py <git worktree> <package dir>
"""
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

# cuts: helm_now = 015d340d (RB-W1 merge), helm_base = d4488f2a (its parent)
TOP = ["helm_brain_canonical.py", "helm_triad.py", "helm_english_in.py", "helm_voice.py", "helm_end_to_end_loop.py",
       "helm_chat.py", "helm_memory.py", "helm_agentic_executor.py", "tks_meta_valve_controller.py",
       "helm_brain_22x40.py", "helm_creativity_dial.py", "phrasebook.json", "tks_meta_valve_weights_v0_4.json",
       "test_helm_end_to_end_loop.py", "test_helm_english_in.py", "test_helm_voice.py", "test_helm_triad.py",
       "test_helm_chat_nuance.py", "helm_faces_in.py", "helm_faces_lexicon.json", "test_helm_faces_in.py",
       "cas-synthetic/data/l4_split/real_dev_unparseables_99.jsonl", "test_helm_english_in_stock_frame.py"]
NOW_ONLY = ["helm_brain_wide.py", "helm_wide_turn.py", "test_helm_brain_wide.py"]
COUNCIL = "docs/working/noetic_council"
DIRS = {"the_loop_v3": None, "repair_performer": None, "cube_store": None, "faculties_v2": None,
        "language_v3": ("runs/",), "return_address": None}
EXT = [(r"C:\Users\wakil\Documents\Codex\CAS-Recipe-Network-Comparison-20261011", "sdg_bridge"),
       (r"C:\Users\wakil\Documents\Codex\CAS-Recipe-Network-Comparison-20261011", "sdg_bridge_v2"),
       (r"C:\Users\wakil\Documents\Codex\2026-10-14\lacunarity_machine_v1", "lacunarity_machine")]


def git(wt, *args, binary=False):
    out = subprocess.run(["git", "-C", str(wt), *args], capture_output=True, check=True)
    return out.stdout if binary else out.stdout.decode("utf-8")


def sha(b):
    return hashlib.sha256(b).hexdigest()


def cut(wt, pkg, name, rev):
    commit = git(wt, "rev-parse", rev + "^{commit}").strip()
    dest = pkg / name
    if dest.exists():
        shutil.rmtree(dest)
    files = list(TOP) + (NOW_ONLY if name == "helm_now" else [])
    for d, skip in DIRS.items():
        for f in git(wt, "ls-tree", "-r", "--name-only", commit, f"{COUNCIL}/{d}/").splitlines():
            rel = f[len(COUNCIL) + len(d) + 2:]
            if skip and any(rel.startswith(s) for s in skip):
                continue
            if "__pycache__" in f or f.endswith(".pyc"):
                continue
            files.append(f)
    rec = {"schema": "helm.rbw1t.source-cut/1", "thread_branch": "claude/project-thread-pmbzd6", "commit": commit,
           "rule": "every file read with git show <commit>:<path> (never the working tree)", "files": {},
           "vendor_ext": {}}
    for f in files:
        raw = git(wt, "show", f"{commit}:{f}", binary=True)
        out = dest / f
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(raw)
        rec["files"][f] = {"sha256": sha(raw), "bytes": len(raw)}
    for root, nm in EXT:
        src = Path(root) / nm
        for p in sorted(src.rglob("*.py")):
            if "__pycache__" in p.parts:
                continue
            rel = p.relative_to(src.parent).as_posix()
            raw = p.read_bytes()
            out = dest / "helm_vendor_ext" / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(raw)
            rec["vendor_ext"]["helm_vendor_ext/" + rel] = {"sha256": sha(raw), "bytes": len(raw)}
    data = (json.dumps(rec, indent=1, sort_keys=True) + "\n").encode("ascii")
    (dest / "SOURCE_CUT.json").write_bytes(data)
    return {"cut": name, "commit": commit, "files": len(rec["files"]), "vendor_ext": len(rec["vendor_ext"]),
            "source_cut_sha256": sha(data)}


def main():
    wt, pkg = Path(sys.argv[1]), Path(sys.argv[2])
    out = [cut(wt, pkg, "helm_now", "015d340d"), cut(wt, pkg, "helm_base", "d4488f2a")]
    assert out[0]["commit"].startswith("015d340d") and out[1]["commit"].startswith("d4488f2a"), out
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
