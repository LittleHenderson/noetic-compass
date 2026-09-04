from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
_MANIFEST_SPEC = importlib.util.spec_from_file_location(
    "cas_neural_cjt_v02_build_source_manifest",
    ROOT / "tools" / "build_source_manifest.py",
)
assert _MANIFEST_SPEC is not None and _MANIFEST_SPEC.loader is not None
manifest_builder = importlib.util.module_from_spec(_MANIFEST_SPEC)
_MANIFEST_SPEC.loader.exec_module(manifest_builder)


EXPECTED_METADATA = {
    "schema_version": "cas.neural-cjt.source-manifest/0.2",
    "status": "LOCAL_NEURAL_CJT_MECHANISM_PROTOTYPE_SOURCE_SET",
    "package_version": "0.2.0",
    "claim_boundary": (
        "One local prototype satisfying the owner's 15-behavior definition of the "
        "first complete neural CJT; not the complete CAS-native Transformer, CNCM brain, "
        "general reasoning system, AGI, or production system; no claim that CAS improves "
        "learning or reasoning."
    ),
}


def test_checked_manifest_matches_current_source_tree() -> None:
    checked = json.loads(
        (ROOT / manifest_builder.MANIFEST_FILENAME).read_text(encoding="utf-8")
    )
    assert checked == manifest_builder.build_manifest(ROOT)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _make_complete_source_tree(root: Path) -> list[str]:
    intended_paths: list[str] = []
    for name in reversed(sorted(manifest_builder.TOP_LEVEL_FILES)):
        _write(root / name, f"top-level:{name}\n")
        intended_paths.append(name)

    for directory_name in reversed(sorted(manifest_builder.SOURCE_DIRECTORIES)):
        relative = Path(directory_name) / "nested" / "source.txt"
        _write(root / relative, f"source-directory:{directory_name}\n")
        intended_paths.append(relative.as_posix())

    # These are release by-products, caches, or the generated output itself.
    # They must never alter the source-set digest.
    excluded = {
        "SOURCE_MANIFEST.json": "generated manifest\n",
        "cas_cjt/__pycache__/module.pyc": "cached bytecode\n",
        "cas_cjt/.pytest_cache/state.json": "pytest cache\n",
        "examples/build/generated.py": "build output\n",
        "tests/dist/archive.whl": "distribution output\n",
        "tools/cas_neural_cjt.egg-info/PKG-INFO": "package metadata\n",
        "tools/nested/ignored.pyo": "optimized bytecode\n",
    }
    for relative, content in excluded.items():
        _write(root / relative, content)

    return sorted(intended_paths)


def test_manifest_is_deterministic_complete_and_narrow(tmp_path: Path) -> None:
    expected_paths = _make_complete_source_tree(tmp_path)

    first = manifest_builder.build_manifest(tmp_path)
    second = manifest_builder.build_manifest(tmp_path)

    assert first == second
    assert {key: first[key] for key in EXPECTED_METADATA} == EXPECTED_METADATA
    assert set(first) == {
        *EXPECTED_METADATA,
        "file_count",
        "aggregate_sha256",
        "files",
    }

    entries = first["files"]
    paths = [entry["path"] for entry in entries]
    assert paths == sorted(paths)
    assert paths == expected_paths
    assert first["file_count"] == len(expected_paths)

    for entry in entries:
        path = tmp_path / entry["path"]
        content = path.read_bytes()
        assert entry["bytes"] == len(content)
        assert entry["sha256"] == hashlib.sha256(content).hexdigest()

    canonical_entries = json.dumps(
        entries, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("ascii")
    assert first["aggregate_sha256"] == hashlib.sha256(canonical_entries).hexdigest()

    excluded_paths = {
        "SOURCE_MANIFEST.json",
        "cas_cjt/__pycache__/module.pyc",
        "cas_cjt/.pytest_cache/state.json",
        "examples/build/generated.py",
        "tests/dist/archive.whl",
        "tools/cas_neural_cjt.egg-info/PKG-INFO",
        "tools/nested/ignored.pyo",
    }
    assert excluded_paths.isdisjoint(paths)


def test_manifest_digest_changes_only_when_included_source_changes(tmp_path: Path) -> None:
    _make_complete_source_tree(tmp_path)
    original = manifest_builder.build_manifest(tmp_path)

    _write(tmp_path / "dist" / "extra.whl", "new ignored output\n")
    assert manifest_builder.build_manifest(tmp_path) == original

    included_path = tmp_path / sorted(manifest_builder.TOP_LEVEL_FILES)[0]
    included_path.write_text("changed included source\n", encoding="utf-8")
    changed = manifest_builder.build_manifest(tmp_path)
    assert changed["aggregate_sha256"] != original["aggregate_sha256"]
    assert [item["path"] for item in changed["files"]] == [
        item["path"] for item in original["files"]
    ]


@pytest.mark.parametrize(
    ("missing_kind", "missing_name"),
    [
        ("file", sorted(manifest_builder.TOP_LEVEL_FILES)[0]),
        ("directory", sorted(manifest_builder.SOURCE_DIRECTORIES)[0]),
    ],
)
def test_manifest_fails_closed_for_missing_required_inventory(
    tmp_path: Path, missing_kind: str, missing_name: str
) -> None:
    _make_complete_source_tree(tmp_path)
    target = tmp_path / missing_name
    if missing_kind == "file":
        target.unlink()
    else:
        for path in sorted(target.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            else:
                path.rmdir()
        target.rmdir()

    with pytest.raises(FileNotFoundError, match=missing_name):
        manifest_builder.build_manifest(tmp_path)
