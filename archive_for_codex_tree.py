"""Archive the FOR-CODEX tree to S3 (deduplicated documentary subset).

Excludes worktrees, test scratch, LFS caches, node_modules, __pycache__ and nested .git. Deduplicates by SHA-256 so the
three identical 695.7 MB source bundles are uploaded once. Writes a manifest locally and to S3.

    python archive_for_codex_tree.py [--dry-run]
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import boto3
from botocore.config import Config

ROOT = Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
BUCKET = "cas-harness-runpod-92754088"
PREFIX = "bridge-control-20260822/for-codex-tree-20261025/"
BAD = ("_worktrees", "_tmp", "_test_runs", "github-lfs-cache", "node_modules", "__pycache__", ".git")
s3 = boto3.client("s3", region_name="us-west-2", config=Config(retries={"max_attempts": 5}))


def collect():
    files = []
    for dirpath, dirs, names in os.walk(ROOT):
        rel = Path(dirpath).relative_to(ROOT).as_posix()
        if any(b in rel.split("/") for b in BAD):
            dirs[:] = []
            continue
        for n in names:
            p = Path(dirpath) / n
            try:
                files.append((p, p.stat().st_size))
            except OSError:
                continue
    return files


def sha(p: Path, limit_chunk=1 << 20) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(limit_chunk), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    dry = "--dry-run" in sys.argv
    files = collect()
    total = sum(s for _p, s in files)
    print(f"candidates={len(files)} bytes={total} ({total/1024**3:.2f} GiB)", flush=True)
    if dry:
        return 0

    unique, seen = [], {}
    t0 = time.time()
    for i, (p, s) in enumerate(files, start=1):
        h = sha(p)
        if h in seen:
            seen[h]["duplicates"].append(p.relative_to(ROOT).as_posix())
            continue
        entry = {"path": p.relative_to(ROOT).as_posix(), "bytes": s, "sha256": h, "duplicates": []}
        seen[h] = entry
        unique.append(entry)
        if i % 2000 == 0:
            print(f"hashed {i}/{len(files)} unique={len(unique)} elapsed={time.time()-t0:.0f}s", flush=True)
    utotal = sum(e["bytes"] for e in unique)
    print(f"unique={len(unique)} bytes={utotal} ({utotal/1024**3:.2f} GiB)", flush=True)

    def upload(entry):
        p = ROOT / entry["path"]
        key = PREFIX + entry["path"]
        for attempt in range(3):
            try:
                s3.upload_file(str(p), BUCKET, key)
                return True
            except Exception:
                time.sleep(2 * (attempt + 1))
        return False

    ok = 0
    failed = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        for i, (entry, good) in enumerate(zip(unique, ex.map(upload, unique)), start=1):
            if good:
                ok += 1
            else:
                failed.append(entry["path"])
            if i % 100 == 0:
                print(f"uploaded {i}/{len(unique)} ok={ok} elapsed={time.time()-t0:.0f}s", flush=True)
    manifest = {"root": str(ROOT), "bucket": BUCKET, "prefix": PREFIX, "candidates": len(files),
                "unique_files": len(unique), "unique_bytes": utotal, "uploaded_ok": ok,
                "failed": failed, "entries": unique}
    out = Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS\docs\working\FOR_CODEX_TREE_S3_MANIFEST_20261025.json")
    out.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    s3.upload_file(str(out), BUCKET, PREFIX + "_MANIFEST.json")
    print(json.dumps({"unique": len(unique), "uploaded_ok": ok, "failed": len(failed),
                      "elapsed_s": round(time.time()-t0, 1), "manifest": str(out)}), flush=True)
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
