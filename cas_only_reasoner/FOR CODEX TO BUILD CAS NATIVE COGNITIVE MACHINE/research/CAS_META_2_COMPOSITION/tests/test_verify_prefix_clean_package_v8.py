"""Pure preconditions for byte-faithful isolated archive reproduction."""
import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location("verify_prefix_clean_package_v8",
    Path(__file__).resolve().parents[1] / "tools/verify_prefix_clean_package_v8.py")
c = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(c)


def test_exact_published_source_archive():
    mapping = c.inspect_archive(c.RECORDS / "source_001/source.zip")
    assert len(mapping) == 616
    assert mapping[c.PILOT + "/cas_meta2/diagnostic_v8/gpu.py"] == "4d83203d143ecca241e6248449d2cd97541805ce71cfb3333bdcc45d2fd6cf4d"
    assert c.PILOT + "/tools/check_prefix_diagnostic_v8.py" in mapping


@pytest.mark.parametrize("name", ["", "/root", "a/../b", "a//b", "a/./b", "C:/x", "a\\b", "a/"])
def test_unsafe_source_member_refused(name):
    with pytest.raises(ValueError, match="V8_CLEAN_UNSAFE_MEMBER"):
        c.safe_name(name)


def test_duplicate_json_refused():
    with pytest.raises(ValueError, match="V8_CLEAN_DUPLICATE_JSON_KEY"):
        c.decode(b'{"x": 1, "x": 2}')


@pytest.mark.parametrize("raw", [b'{"x": NaN}', b'{"x": Infinity}', b'{"x": 1e999}'])
def test_nonfinite_json_refused(raw):
    with pytest.raises(ValueError):
        c.decode(raw)


def test_wrong_archive_bytes_refused_without_extraction(tmp_path):
    archive = tmp_path / "changed.zip"
    archive.write_bytes(b"not the pinned archive")
    with pytest.raises(ValueError, match="V8_CLEAN_ARCHIVE_CHANGED"):
        c.inspect_archive(archive)


def test_existing_or_outside_output_refused_before_reading_inputs(tmp_path, monkeypatch):
    monkeypatch.setattr(c, "RECORDS", tmp_path)
    for output in (tmp_path, tmp_path.parent / "outside"):
        with pytest.raises(ValueError, match="V8_CLEAN_NEW_IN_SCOPE_OUTPUT_REQUIRED"):
            c.check(output, "absent-source", "absent-extraction")


def test_changed_extracted_source_is_detected(tmp_path):
    (tmp_path / "a.py").write_bytes(b"original")
    expected = c.source_snapshot(tmp_path, {"a.py": ""})
    (tmp_path / "a.py").write_bytes(b"changed")
    assert c.source_snapshot(tmp_path, expected) != expected


def test_parser_preserves_skips_and_subtests():
    assert c.parse_counts("311 passed, 2 skipped, 5 subtests passed in 29.44s\n") == {
        "tests_passed": 311, "subtests_passed": 5, "skipped": 2, "failed": 0, "errors": 0}
    assert c.parse_counts("313 passed, 5 subtests passed in 30.00s\n")["skipped"] == 0
    assert c.parse_counts("No tests ran") is None
