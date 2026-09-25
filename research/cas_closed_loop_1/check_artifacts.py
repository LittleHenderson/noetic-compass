"""Verify exact retained bytes locally or in a committed recovery tree."""
from hashlib import sha256
import argparse
import json
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent


def verify(root=HERE, *, git_ref=None):
    root = Path(root).resolve()
    if git_ref is not None and re.fullmatch(r"HEAD|[0-9a-f]{40}", git_ref) is None:
        raise ValueError("EXACT_GIT_REF_REQUIRED")
    def read(relative):
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("UNSAFE_ARTIFACT_PATH")
        if git_ref is None:
            return (root / path).read_bytes()
        return subprocess.check_output(["git", "show", git_ref + ":research/cas_closed_loop_1/" + path.as_posix()], cwd=root)
    artifacts = json.loads(read("evidence/ARTIFACT_MANIFEST.json"))
    source = json.loads(read("RUN_MANIFEST.json"))
    bindings = json.loads(read("SOURCE_BINDINGS.json"))
    producer = json.loads(read("HISTORICAL_PRODUCER.json"))
    if (producer.get("schema") != "cas.closed-loop.historical-producer/1"
            or producer.get("source_commit") != "8f55cc3a462e438bcf706d7b64ddf9171d218039"):
        raise ValueError("HISTORICAL_PRODUCER_IDENTITY")
    snapshots = producer["implementation_files"]
    if len(snapshots) != len(source["implementation_files"]):
        raise ValueError("HISTORICAL_PRODUCER_FILES")
    indexed = {row["path"]: row for row in snapshots}
    if len(indexed) != len(snapshots) or set(indexed) != {row["path"] for row in source["implementation_files"]}:
        raise ValueError("HISTORICAL_PRODUCER_FILES")
    rows = [("evidence/" + row["path"], row) for row in artifacts["files"]]
    for row in source["implementation_files"]:
        snapshot = indexed[row["path"]]
        if (snapshot["sha256"] != row["sha256"]
                or snapshot["snapshot"] != "provenance/producer_8f55cc3a/" + row["path"] + ".txt"):
            raise ValueError("HISTORICAL_PRODUCER_BINDING")
        rows.append((snapshot["snapshot"], snapshot))
    rows += [("provenance/" + row["source"].rsplit("/", 1)[-1] + ".txt", row) for row in bindings["handoff"]]
    for name, row in rows:
        raw = read(name)
        if sha256(raw).hexdigest() != row["sha256"] or ("bytes" in row and len(raw) != row["bytes"]):
            raise ValueError("ARTIFACT_BYTES_DIFFER:" + name)
    return {"status": "EXACT_BYTES_VERIFIED", "files": len(rows), "git_ref": git_ref,
            "historical_producer_commit": producer["source_commit"],
            "boundary": "Retained evidence and its original producer bytes only; current source acceptance is separate."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--git-ref")
    args = parser.parse_args()
    print(json.dumps(verify(git_ref=args.git_ref)))
