"""Materialize only manifest-listed public source blobs from local Git objects.

No fetch, model invocation, protected fixtures, or edits to upstream worktrees.
"""
from hashlib import sha256
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def prepare():
    manifest = json.loads((HERE / "SOURCE_BINDINGS.json").read_text())
    destination = HERE / "_runtime"
    for row in manifest["files"]:
        relative = Path(row["destination"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("UNSAFE_SOURCE_DESTINATION")
        raw = subprocess.check_output(
            ["git", "show", manifest["runtime_commit"] + ":" + row["source"]], cwd=REPO)
        if len(raw) != row["bytes"] or sha256(raw).hexdigest() != row["sha256"]:
            raise ValueError("SOURCE_IDENTITY_MISMATCH: " + row["source"])
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    print(json.dumps({"status": "MATERIALIZED_PINNED_PUBLIC_SOURCE", "files": len(manifest["files"]),
                      "runtime_commit": manifest["runtime_commit"]}))


if __name__ == "__main__":
    prepare()
