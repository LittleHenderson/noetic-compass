"""Build the deterministic source manifest for CASformer v0.1."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "SOURCE_MANIFEST.json"
TOP_LEVEL_FILES = {
    "README.md",
    "SPEC.md",
    "CLAIMS.md",
    "SOURCE_REFERENCES.json",
    "pyproject.toml",
    "pytest.ini",
}
SOURCE_DIRECTORIES = {"casformer", "examples", "tests", "tools"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def source_paths() -> list[Path]:
    paths: list[Path] = []
    for name in sorted(TOP_LEVEL_FILES):
        path = ROOT / name
        if path.is_file():
            paths.append(path)
    for directory_name in sorted(SOURCE_DIRECTORIES):
        directory = ROOT / directory_name
        if not directory.exists():
            continue
        for path in directory.rglob("*"):
            if not path.is_file():
                continue
            if "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
                continue
            paths.append(path)
    return sorted(set(paths), key=lambda item: item.relative_to(ROOT).as_posix())


def build_manifest() -> dict:
    entries = [
        {
            "path": path.relative_to(ROOT).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for path in source_paths()
    ]
    canonical_entries = json.dumps(
        entries, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("ascii")
    return {
        "schema_version": "cas.casformer.source-manifest/0.1",
        "status": "REFERENCE_IMPLEMENTATION_SOURCE_SET",
        "casformer_version": "0.1.0",
        "file_count": len(entries),
        "aggregate_sha256": hashlib.sha256(canonical_entries).hexdigest(),
        "files": entries,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(build_manifest(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(output)


if __name__ == "__main__":
    main()
