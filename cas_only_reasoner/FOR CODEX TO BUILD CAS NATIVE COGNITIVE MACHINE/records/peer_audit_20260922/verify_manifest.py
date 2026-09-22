"""Write or verify raw audit-artifact hashes; this is not an acceptance check."""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "AUDIT_MANIFEST.json"


def inventory():
    return [
        {
            "path": path.relative_to(HERE).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        for path in sorted(HERE.rglob("*"))
        if path.is_file() and path != MANIFEST and "__pycache__" not in path.parts
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    observed = inventory()
    if args.write:
        document = {
            "schema": "cas.peer-audit.artifact-manifest/1.0",
            "audited_source_commit": "626cc84b574e60217a103b72d2f09388d7aa5e34",
            "parallel_feature_source_commit": "eb9985566bd11a89f485d627186ef0efa7177f02",
            "scope": "Raw artifact integrity only. Not scientific acceptance or proof of model execution.",
            "excluded": ["AUDIT_MANIFEST.json", "__pycache__ directories"],
            "files": observed,
        }
        MANIFEST.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    expected = json.loads(MANIFEST.read_text(encoding="utf-8"))["files"]
    if observed != expected:
        by_path = {row["path"]: row for row in expected}
        actual = {row["path"]: row for row in observed}
        differing = sorted(key for key in by_path.keys() | actual.keys()
                           if by_path.get(key) != actual.get(key))
        raise SystemExit("Integrity mismatch: " + ", ".join(differing))
    print(json.dumps({"integrity": "PASS", "files": len(observed),
                      "bytes": sum(row["bytes"] for row in observed)}))


if __name__ == "__main__":
    main()
