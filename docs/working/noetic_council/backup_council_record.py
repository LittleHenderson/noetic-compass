"""Back up the council's own machinery and its working record, with three confirmations each.

WHY THIS EXISTS
---------------
Everything the council knows lives in a LANDING ZONE — `Documents\\Codex\\2026-10-16\\` — which is not
a repository and has no history. Wave 1's run was backed up, but the machinery that produced the
R1-RT design, the thirteen seat reports, the loop journal, and the engine candidates were not.

The repository now holds the PORTABLE artifacts: the ten seat definitions, the loop, the three
targets, the frozen conversion rules, the verifiers, and the design documents. What it does not hold
is the working record — who said what, on which turn, and what the engine candidates were. This
copies that record out of the landing zone.

THE THREE CONFIRMATIONS, PER TREE
---------------------------------
1. source-side: every file hashed where it sits;
2. destination-side: every file hashed where it now sits, re-read from disk;
3. a whole-tree digest over the sorted (relative path, bytes, sha256) list, computed twice — once
   from the source enumeration and once from the destination — and compared.

A mismatch, a missing file or an extra file fails the script. The manifest is written last, and only
if all three agree.

Usage:
    C:\\Python314\\python.exe -B backup_council_record.py [--dest <dir>]
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from typing import Any, Dict, List

LANDING = r"C:\Users\wakil\Documents\Codex\2026-10-16"
DEFAULT_DEST = r"D:\tksCAS-archive\noetic_council_20261016"

TREES = [
    ("noetic_loop", os.path.join(LANDING, "noetic_loop")),
    ("rpm_council_work", os.path.join(LANDING, "rpm_council_work")),
    ("rpm_council_original", os.path.join(LANDING, "rpm_council")),
]

#: Files whose presence is the point. Their hashes go in the manifest by name.
KEY_FILES = [
    "noetic_loop/council_loop.py",
    "noetic_loop/run_loop_helm_r1_rt.py",
    "noetic_loop/target_helm_r1_rt.py",
    "noetic_loop/verify_r1_rt_rules.py",
    "noetic_loop/verify_route_d_case_passing.py",
    "noetic_loop/prepare_route_d_patch.py",
    "noetic_loop/journal/LOOP_JOURNAL.jsonl",
    "rpm_council_work/H_c8/engine.py",
    "rpm_council_work/G_c6/engine.py",
]


def sha(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _walk_pruned(root: str):
    """Walk a tree, PRUNING reparse points (junctions and symlinks) instead of following them.

    Measured reason: `rpm_council_work/E_c5/rpm_council` is a **directory junction pointing at
    `E_c5`** — its own parent. `shutil.copytree` follows it, nesting `rpm_council` forever until
    the Windows path limit is hit, and it left 121 directories in the archive before failing.
    `os.walk` does not follow directory symlinks by default on POSIX but does traverse junctions
    on Windows, so the pruning is explicit.

    Yields (dirpath, filenames) with every visitable directory, skipping the reparse points.
    """
    for base, dirs, files in os.walk(root):
        keep = []
        for d in dirs:
            path = os.path.join(base, d)
            try:
                is_link = os.path.islink(path)
                attrs = os.stat(path, follow_symlinks=False).st_file_attributes
                is_reparse = bool(attrs & 0x400)  # FILE_ATTRIBUTE_REPARSE_POINT
            except OSError:
                is_link, is_reparse = True, True
            if is_link or is_reparse:
                continue  # pruned: recorded in the manifest, never copied
            keep.append(d)
        dirs[:] = keep
        yield base, files


def enumerate_tree(root: str) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for base, files in _walk_pruned(root):
        for name in sorted(files):
            path = os.path.join(base, name)
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            if name.endswith(".pyc") or "__pycache__" in rel:
                # Byte-code caches are regenerable and would only add noise to the manifest.
                continue
            try:
                out[rel] = {"bytes": os.path.getsize(path), "sha256": sha(path)}
            except OSError:
                out[rel] = {"bytes": -1, "sha256": "UNREADABLE"}
    return out


def copy_tree(src: str, dst: str) -> int:
    """Copy a tree, pruning reparse points. Returns the count of pruned links."""
    pruned = 0
    os.makedirs(dst, exist_ok=True)
    for base, files in _walk_pruned(src):
        rel = os.path.relpath(base, src)
        target_dir = dst if rel == "." else os.path.join(dst, rel)
        os.makedirs(target_dir, exist_ok=True)
        for name in files:
            if name.endswith(".pyc"):
                continue
            shutil.copy2(os.path.join(base, name), os.path.join(target_dir, name))
        # count what was pruned at this level, for the report
        for d in os.listdir(base):
            p = os.path.join(base, d)
            if not os.path.isdir(p):
                continue
            try:
                is_link = os.path.islink(p)
                attrs = os.stat(p, follow_symlinks=False).st_file_attributes
                is_reparse = bool(attrs & 0x400)
            except OSError:
                is_link, is_reparse = False, False
            if is_link or is_reparse:
                pruned += 1
    return pruned


def tree_digest(entries: Dict[str, Dict[str, Any]]) -> str:
    h = hashlib.sha256()
    for rel in sorted(entries):
        e = entries[rel]
        h.update(("%s\0%d\0%s\n" % (rel, e["bytes"], e["sha256"])).encode("utf-8"))
    return h.hexdigest()


def main() -> int:
    dest_root = DEFAULT_DEST
    if "--dest" in sys.argv:
        dest_root = sys.argv[sys.argv.index("--dest") + 1]

    pruned_total = 0
    for name, src in TREES:
        if os.path.isdir(src):
            dst = os.path.join(dest_root, name)
            if os.path.isdir(dst):
                shutil.rmtree(dst, ignore_errors=True)
            pruned_total += copy_tree(src, dst)

    manifest: Dict[str, Any] = {
        "schema": "noetic-council.backup-manifest/1",
        "purpose": ("the council's machinery, its seat reports and its loop journal, copied out of "
                    "the landing zone so the methodology has a durable copy"),
        "archive_root": dest_root,
        "method": ("three confirmations per tree: source hashes, destination hashes re-read from "
                   "disk, and one whole-tree digest computed independently from each side"),
        "trees": {},
        "key_files": {},
        "problems": [],
    }
    problems: List[str] = []

    for name, src in TREES:
        dst = os.path.join(dest_root, name)
        if not os.path.isdir(src):
            problems.append("SOURCE MISSING: %s" % src)
            continue
        if not os.path.isdir(dst):
            problems.append("DESTINATION MISSING: %s" % dst)
            continue
        src_entries = enumerate_tree(src)
        dst_entries = enumerate_tree(dst)
        src_digest, dst_digest = tree_digest(src_entries), tree_digest(dst_entries)
        missing = sorted(set(src_entries) - set(dst_entries))
        extra = sorted(set(dst_entries) - set(src_entries))
        differing = sorted(r for r in set(src_entries) & set(dst_entries)
                           if src_entries[r] != dst_entries[r])
        ok = not (missing or extra or differing) and src_digest == dst_digest
        for label, items in (("missing at destination", missing),
                             ("extra at destination", extra), ("differing", differing)):
            if items:
                problems.append("%s: %d %s: %s" % (name, len(items), label, items[:4]))
        if src_digest != dst_digest:
            problems.append("%s: whole-tree digests disagree" % name)
        manifest["trees"][name] = {
            "source": src, "destination": dst, "files": len(src_entries),
            "bytes": sum(e["bytes"] for e in src_entries.values() if e["bytes"] >= 0),
            "confirm1_source_digest": src_digest,
            "confirm2_destination_digest": dst_digest,
            "confirm3_digests_agree": src_digest == dst_digest,
            "ok": ok,
            "entries": src_entries,
        }
        print("%-22s %5d files %11d bytes  %s"
              % (name, len(src_entries),
                 sum(e["bytes"] for e in src_entries.values() if e["bytes"] >= 0),
                 "OK" if ok else "PROBLEM"))

    for rel in KEY_FILES:
        tree, sub = rel.split("/", 1)
        entry = (manifest["trees"].get(tree) or {}).get("entries", {}).get(sub)
        manifest["key_files"][rel] = entry
        print("  key: %-52s %s" % (rel, (entry or {}).get("sha256", "MISSING")[:24]))
        if entry is None:
            problems.append("KEY FILE NOT BACKED UP: %s" % rel)

    manifest["problems"] = problems
    manifest["ok"] = not problems
    manifest["reparse_points_pruned"] = pruned_total
    manifest["pruning_note"] = (
        "Reparse points (junctions and symlinks) are PRUNED, never followed. At least one exists "
        "in this tree — `rpm_council_work/E_c5/rpm_council` is a junction pointing at its own "
        "parent `E_c5` — and following it nests forever until the Windows path limit fails the "
        "copy. Pruned links are therefore NOT in this backup, and the count above says how many.")

    if problems:
        print()
        print("PROBLEMS, so no manifest was written:")
        for p in problems:
            print("  - %s" % p)
        return 1

    os.makedirs(dest_root, exist_ok=True)
    path = os.path.join(dest_root, "BACKUP_MANIFEST_NOETIC_COUNCIL.json")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print()
    print("WROTE %s" % path)
    print("sha256 %s" % sha(path))
    print("ALL THREE CONFIRMATIONS AGREE on every tree.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
