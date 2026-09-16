"""Build the CAS_RDCJT_001 source package from a commit, plus request+authority.

Reads bytes from GIT, not the working tree, so the archive and the declared
source_sha describe the same bytes. Writes nothing inside the repository.
"""

import hashlib
import json
import sys
from pathlib import Path

WORKTREE = Path(
    r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner"
    r"\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\meta1")
COMPOSITION = (WORKTREE / "cas_only_reasoner" /
               "FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE" /
               "research" / "CAS_META_2_COMPOSITION")
sys.path.insert(0, str(COMPOSITION))

OUT = COMPOSITION / "records" / "recurrent_cjt_001" / "rdcjt_package_004"
SOURCE_SHA = sys.argv[1] if len(sys.argv) > 1 else None


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    from aws import recurrent_cjt_launch as L

    if SOURCE_SHA is None:
        raise SystemExit("usage: build_launch_inputs.py <source_sha>")

    # The builder requires ``output`` NOT to exist and its parent TO exist. It
    # treats ``output`` as a new directory and writes ``source.zip`` inside it,
    # matching rdcjt_package_001..003. Do not pre-create it.
    receipt = L.build_recurrent_package(OUT, source_sha=SOURCE_SHA)
    print(json.dumps({
        "archive": receipt.get("archive"),
        "archive_sha256": receipt.get("archive_sha256"),
        "archive_bytes": receipt.get("archive_bytes"),
        "source_sha": receipt.get("source_sha"),
        "manifest_sha256": receipt.get("manifest_sha256"),
        "member_count": receipt.get("member_count"),
    }, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
