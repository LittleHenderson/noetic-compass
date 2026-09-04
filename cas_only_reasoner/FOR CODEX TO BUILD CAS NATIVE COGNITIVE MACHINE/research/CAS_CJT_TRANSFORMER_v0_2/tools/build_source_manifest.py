"""Build the deterministic CAS Neural CJT v0.2 source manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "SOURCE_MANIFEST.json"
MANIFEST_FILENAME = DEFAULT_OUTPUT.name
TOP_LEVEL_FILES = {
    "API_CONTRACTS.md",
    "ARCHITECTURE.md",
    "BUILD_CONTRACT.md",
    "CNCM_INTEGRATION_BOUNDARY.md",
    "EQUATIONS.md",
    "MEMORY_RESEARCH_PLAN.md",
    "OPERATION_EXPANSION.md",
    "README.md",
    "ROADMAP.md",
    "pyproject.toml",
    "pytest.ini",
}
SOURCE_DIRECTORIES = {"cas_cjt", "examples", "tests", "tools"}
IGNORED_DIRECTORY_NAMES = {
    ".pytest_cache",
    "__pycache__",
    "build",
    "dist",
}
IGNORED_SUFFIXES = {".pyc", ".pyo"}
CLAIM_BOUNDARY = (
    "One local prototype satisfying the owner's 15-behavior definition of the "
    "first complete neural CJT; not the complete CAS-native Transformer, CNCM brain, "
    "general reasoning system, AGI, or production system; no claim that CAS improves "
    "learning or reasoning."
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _is_ignored(relative: Path) -> bool:
    if relative.as_posix() == MANIFEST_FILENAME:
        return True
    if relative.suffix.casefold() in IGNORED_SUFFIXES:
        return True
    return any(
        part.casefold() in IGNORED_DIRECTORY_NAMES
        or part.casefold().endswith(".egg-info")
        for part in relative.parts[:-1]
    )


def source_paths(root: Path = ROOT) -> list[Path]:
    paths: list[Path] = []
    for name in sorted(TOP_LEVEL_FILES):
        path = root / name
        if not path.is_file():
            raise FileNotFoundError(f"required manifest source is missing: {name}")
        paths.append(path)

    for directory_name in sorted(SOURCE_DIRECTORIES):
        directory = root / directory_name
        if not directory.is_dir():
            raise FileNotFoundError(
                f"required manifest source directory is missing: {directory_name}"
            )
        for path in directory.rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(root)
            if _is_ignored(relative):
                continue
            paths.append(path)

    return sorted(set(paths), key=lambda item: item.relative_to(root).as_posix())


def build_manifest(root: Path = ROOT) -> dict[str, object]:
    entries = [
        {
            "path": path.relative_to(root).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for path in source_paths(root)
    ]
    canonical_entries = json.dumps(
        entries, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("ascii")
    return {
        "schema_version": "cas.neural-cjt.source-manifest/0.2",
        "status": "LOCAL_NEURAL_CJT_MECHANISM_PROTOTYPE_SOURCE_SET",
        "package_version": "0.2.0",
        "claim_boundary": CLAIM_BOUNDARY,
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
