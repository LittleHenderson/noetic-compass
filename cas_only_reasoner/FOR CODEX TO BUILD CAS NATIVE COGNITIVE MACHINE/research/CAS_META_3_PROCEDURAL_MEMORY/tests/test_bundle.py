"""Committed source and upstream-byte tests; no dataset generation or AWS calls."""
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import subprocess
from unittest.mock import patch
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("meta3_bundle_tested", ROOT / "tools/build_launch_bundle.py")
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)
frozen = builder.frozen
LAUNCH_SPEC = importlib.util.spec_from_file_location("meta3_bundle_launch_tested", ROOT / "aws/launch.py")
launch = importlib.util.module_from_spec(LAUNCH_SPEC)
LAUNCH_SPEC.loader.exec_module(launch)


@pytest.fixture(scope="module")
def committed_inputs():
    repo, prefix = frozen.git_context()
    upstream = frozen.git_members(repo, prefix, frozen.UPSTREAM_SHA, frozen.UPSTREAM_PACKAGES)
    members = dict(upstream)
    for name in frozen.REQUIRED:
        if name.startswith(frozen.PILOT + "/"):
            path = ROOT / name.removeprefix(frozen.PILOT + "/")
            members[name] = path.read_bytes()
    # New META3 files are test fixture bytes, never advertised as a real commit.
    return members, upstream


def manifest(inputs):
    members, upstream = inputs
    return builder.make_manifest(members, "b" * 40, upstream)


def archive_file(path, members, document):
    with zipfile.ZipFile(path, "x", zipfile.ZIP_DEFLATED) as archive:
        for name, raw in sorted(members.items()):
            archive.writestr(name, raw)
        archive.writestr("launch_manifest.json", json.dumps(document, sort_keys=True))
    return path


def test_manifest_pins_one_entrypoint_all_sources_and_no_budget_records(committed_inputs):
    result = manifest(committed_inputs)
    assert result["schema"] == "cas-meta3-launch/1"
    assert result["entrypoint"] == "cas_meta3.native_demo"
    assert result["upstream_sha"] == "410bce98307a5644db51928459b73391c7066b72"
    assert result["dependency_lock"] == frozen.META2 + "/requirements-gpu.txt"
    assert result["wheel_paths"] == frozen.WHEELS
    assert result["qualification_status"] == "UNQUALIFIED" and result["learning_performed"] is False
    assert frozen.PILOT + "/tools/audit_native_demo.py" in result["files_sha256"]
    assert len(result["upstream_files_sha256"]) > 316
    assert not any("/records/" in name and name.startswith((frozen.PILOT + "/", frozen.META2 + "/", frozen.META1 + "/"))
                   for name in result["files_sha256"])


@pytest.mark.parametrize("package", ["CAS_META_1_LEARNED_SELECTION", "CAS_META_2_COMPOSITION", "CAS_META_3_PROCEDURAL_MEMORY"])
@pytest.mark.parametrize("directory", ["records", "runs", "__pycache__", ".pytest_cache"])
def test_historical_experimental_data_never_becomes_source(package, directory):
    assert builder.include_member("research/" + package + "/" + directory + "/anything.json") is False


def test_upstream_helpers_match_actual_410bce_git_bytes():
    repo, prefix = frozen.git_context()
    for name, expected in frozen.PINNED_FILES.items():
        key = prefix + "CAS_META_2_COMPOSITION/" + name
        raw = subprocess.check_output(["git", "show", frozen.UPSTREAM_SHA + ":" + key], cwd=repo)
        assert sha256(raw).hexdigest() == expected


def test_frozen_upstream_change_and_missing_demo_are_rejected(committed_inputs):
    members, upstream = committed_inputs
    changed = dict(members)
    changed[frozen.META2 + "/cas_meta2/native.py"] += b"\n# altered"
    with pytest.raises(ValueError, match="FROZEN_UPSTREAM_SOURCE_CHANGED"):
        builder.make_manifest(changed, "b" * 40, upstream)
    for name in (frozen.PILOT + "/cas_meta3/native_demo.py", frozen.PILOT + "/tools/audit_native_demo.py"):
        missing = dict(members)
        missing.pop(name)
        with pytest.raises(ValueError, match="META3_DEMO_SOURCE_NOT_READY"):
            builder.make_manifest(missing, "b" * 40, upstream)


def test_archive_validation_accepts_complete_byte_fixture(committed_inputs, tmp_path):
    members, _ = committed_inputs
    document = manifest(committed_inputs)
    path = archive_file(tmp_path / "source.zip", members, document)
    result = launch.validate_archive(path, sha256(path.read_bytes()).hexdigest(), "b" * 40,
                                     json.loads(launch.PLAN_FILE.read_bytes()))
    assert result == document
    # Byte-shape validation alone does not establish the claimed source commit.
    with patch.object(launch.frozen, "git_members", return_value={}):
        with pytest.raises(launch.LaunchRefused, match="ARCHIVE_DOES_NOT_MATCH_REAL_SOURCE_COMMIT"):
            launch.verify_launcher_identity(document)


@pytest.mark.parametrize("key,value", [("entrypoint", "cas_meta2.campaign"), ("upstream_sha", "c" * 40),
                                      ("learning_performed", True), ("qualification_status", "QUALIFIED")])
def test_archive_cannot_route_other_code_or_promote_claim(committed_inputs, tmp_path, key, value):
    members, _ = committed_inputs
    document = manifest(committed_inputs)
    document[key] = value
    path = archive_file(tmp_path / "changed.zip", members, document)
    with pytest.raises(launch.LaunchRefused):
        launch.validate_archive(path, sha256(path.read_bytes()).hexdigest(), "b" * 40,
                                 json.loads(launch.PLAN_FILE.read_bytes()))


def test_missing_or_extra_upstream_coverage_rejected(committed_inputs):
    members, upstream = committed_inputs
    narrowed = dict(upstream)
    narrowed.pop(next(iter(narrowed)))
    with pytest.raises(ValueError, match="FROZEN_UPSTREAM_SOURCE_CHANGED"):
        builder.make_manifest(members, "b" * 40, narrowed)


def test_builder_has_no_arbitrary_profile_or_command_flag():
    source = Path(builder.__file__).read_text()
    assert "--experiment-profile" not in source and "--entrypoint" not in source
    assert "git_members(repo, prefix, head)" in source
    assert "UNTRACKED_SOURCE_MUST_BE_COMMITTED_FIRST" in source
    assert "TRACKED_SOURCE_CHANGES_MUST_BE_COMMITTED_FIRST" in source
    assert 'zipfile.ZipFile(output, "x"' in source


def test_existing_or_external_output_is_rejected_without_writes(tmp_path):
    with pytest.raises(ValueError, match="NEW_OUTPUT_INSIDE_META3_REQUIRED"):
        builder.build(tmp_path / "not-in-meta3.zip")
    assert not (tmp_path / "not-in-meta3.zip").exists()


def test_unsafe_source_paths_are_rejected():
    for name in ("../escape", "research/CAS_META_3_PROCEDURAL_MEMORY/a/../b",
                 "research/CAS_META_3_PROCEDURAL_MEMORY/a:b",
                 "research/UNRELATED/a.py"):
        with pytest.raises(ValueError):
            builder.include_member(name)
