"""Materialize a symlink-free HF cache tree for the Qwen overlay build context.

Docker build contexts do not carry the host cache's snapshot symlinks safely, so
every file is copied as real bytes and re-verified after the copy.
"""
import hashlib
import shutil
import sys
from pathlib import Path

REPO_DIR = "models--Qwen--Qwen2.5-0.5B-Instruct"
REVISION = "7ae557604adf67be50417f59c2c2f167def9a775"
if len(sys.argv) != 2:
    raise SystemExit(
        "usage: stage_project_coherence_stageb_model_context.py <build-context-dir>\n"
        "The context holds about 1 GB of model bytes and must stay outside the repository."
    )
CONTEXT = Path(sys.argv[1]).resolve()

EXPECTED = {
    "config.json": (659, "18e18afcaccafade98daf13a54092927904649e1dd4eba8299ab717d5d94ff45"),
    "generation_config.json": (242, "e558847a8b4402616f1273797b015104dc266fe4b520056fca88823ba8f8ebe6"),
    "merges.txt": (1_671_839, "599bab54075088774b1733fde865d5bd747cbcc7a547c5bc12610e874e26f5e3"),
    "model.safetensors": (988_097_824, "fdf756fa7fcbe7404d5c60e26bff1a0c8b8aa1f72ced49e7dd0210fe288fb7fe"),
    "tokenizer.json": (7_031_645, "c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539"),
    "tokenizer_config.json": (7_305, "5b5d4f65d0acd3b2d56a35b56d374a36cbc1c8fa5cf3b3febbbfabf22f359583"),
    "vocab.json": (2_776_833, "ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910"),
}


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    from huggingface_hub import hf_hub_download

    snapshot_dir = CONTEXT / "hf_cache" / "hub" / REPO_DIR / "snapshots" / REVISION
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    refs_dir = CONTEXT / "hf_cache" / "hub" / REPO_DIR / "refs"
    refs_dir.mkdir(parents=True, exist_ok=True)
    (refs_dir / "main").write_text(REVISION, encoding="utf-8")

    failures = []
    for name, (size, digest) in EXPECTED.items():
        source = Path(
            hf_hub_download(
                "Qwen/Qwen2.5-0.5B-Instruct", name, revision=REVISION, local_files_only=True
            )
        ).resolve()
        target = snapshot_dir / name
        if not (target.is_file() and target.stat().st_size == size and sha256_of(target) == digest):
            shutil.copyfile(source, target)
        actual_size = target.stat().st_size
        actual_digest = sha256_of(target)
        if actual_size != size:
            failures.append(f"{name}: staged size {actual_size} != {size}")
        elif actual_digest != digest:
            failures.append(f"{name}: staged sha256 {actual_digest} != {digest}")
        else:
            print(f"  staged {name:24s} {actual_size:>12,}")
        if target.is_symlink():
            failures.append(f"{name}: staged copy is a symlink")

    if failures:
        print("\nFAILURES:")
        for line in failures:
            print("  " + line)
        return 1

    total = sum(p.stat().st_size for p in snapshot_dir.iterdir() if p.is_file())
    print(f"\nCONTEXT: {CONTEXT}")
    print(f"SNAPSHOT: {snapshot_dir}")
    print(f"TOTAL STAGED: {total:,} bytes")
    print("ALL STAGED FILES VERIFIED / NO SYMLINKS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
