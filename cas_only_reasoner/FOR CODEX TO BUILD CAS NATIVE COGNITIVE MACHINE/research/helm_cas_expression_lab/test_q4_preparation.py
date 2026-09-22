"""Read-only preparation identity checks. No model or real authorization."""
from pathlib import Path
from types import SimpleNamespace

import pytest

import q4_checkpoint
import q4_runtime_metadata as runtime
import q4_smoke_job as job


@pytest.fixture
def dependencies(tmp_path, monkeypatch):
    root = tmp_path / "auth"
    root.mkdir()
    (root / "package.py").write_text("# synthetic package fixture\n", encoding="utf-8")
    monkeypatch.setattr(runtime, "HOME", tmp_path)
    monkeypatch.setenv(runtime.DEPENDENCY_ENV, str(root))
    monkeypatch.setenv("PYTHONPATH", str(root))
    return root


def test_dependency_identity_binds_path_bytes_and_extra_files(dependencies):
    before = runtime.dependency_manifest()
    assert before["root"] == str(dependencies)
    assert before["files"][0]["path"] == "package.py"
    (dependencies / "package.py").write_text("# changed fixture\n", encoding="utf-8")
    changed = runtime.dependency_manifest()
    assert changed["manifest_sha256"] != before["manifest_sha256"]
    (dependencies / "extra.py").write_text("# extra fixture\n", encoding="utf-8")
    extra = runtime.dependency_manifest()
    assert extra["manifest_sha256"] != changed["manifest_sha256"]
    assert len(extra["files"]) == 2


def test_dependency_directory_without_explicit_binding_is_unassigned(monkeypatch):
    monkeypatch.delenv(runtime.DEPENDENCY_ENV, raising=False)
    assert runtime.dependency_manifest() is None


@pytest.mark.parametrize("pythonpath", ["", "other", "two;paths"])
def test_dependency_search_path_must_match_bound_directory(dependencies, monkeypatch, pythonpath):
    monkeypatch.setenv("PYTHONPATH", pythonpath)
    with pytest.raises(ValueError, match="PYTHONPATH"):
        runtime.dependency_manifest()


def test_external_dependency_directory_is_refused(dependencies, monkeypatch):
    monkeypatch.setattr(runtime, "HOME", dependencies / "different-homebase")
    with pytest.raises(ValueError, match="inside the CNCM homebase"):
        runtime.dependency_manifest()


def test_short_dependency_path_inside_homebase_need_not_be_in_nested_checkout(dependencies, monkeypatch):
    nested_checkout = dependencies.parent / "_worktrees" / "isolated" / "nested-project"
    monkeypatch.setattr(runtime, "PROJECT_ROOT", nested_checkout)
    assert not dependencies.is_relative_to(nested_checkout)
    assert runtime.dependency_manifest()["root"] == str(dependencies)


def test_homebase_is_outer_cncm_boundary_used_by_renderer():
    expected = next((p for p in reversed(runtime.PROJECT_ROOT.parents)
                     if p.name == "FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"), runtime.PROJECT_ROOT)
    assert runtime.HOME == expected


def test_dependency_byte_and_entry_bounds_precede_reading(dependencies, monkeypatch):
    monkeypatch.setattr(runtime, "MAX_DEPENDENCY_FILE_BYTES", 1)
    with pytest.raises(ValueError, match="byte budget"):
        runtime.dependency_manifest()
    monkeypatch.setattr(runtime, "MAX_DEPENDENCY_FILE_BYTES", 1024)
    monkeypatch.setattr(runtime, "MAX_DEPENDENCY_ENTRIES", 0)
    with pytest.raises(ValueError, match="entry bound"):
        runtime.dependency_manifest()


def test_dependency_distribution_must_resolve_from_bound_directory(dependencies, monkeypatch):
    monkeypatch.setattr(runtime.metadata, "version", lambda _: "TEST_ONLY")
    monkeypatch.setattr(runtime, "_torch_build", lambda: {"status": "TEST_ONLY"})
    monkeypatch.setattr(runtime.metadata, "distribution", lambda _: SimpleNamespace(
        version="TEST_ONLY", locate_file=lambda _: dependencies.parent))
    with pytest.raises(ValueError, match="outside bound directory"):
        runtime.environment_metadata()


def test_mutated_auth_dependency_invalidates_prepared_plan(dependencies, monkeypatch, tmp_path):
    monkeypatch.setattr(runtime.metadata, "version", lambda _: "TEST_ONLY")
    monkeypatch.setattr(runtime, "_torch_build", lambda: {"status": "TEST_ONLY"})
    monkeypatch.setattr(runtime.metadata, "distribution", lambda _: SimpleNamespace(
        version="TEST_ONLY", locate_file=lambda _: dependencies))
    plan = job.prepare_plan(data_dir=Path(__file__).parent / "data/q3_v0_7",
        data_version="helm-cas-expression-lab.q3-behaviour-records/0.7",
        output=tmp_path / "never-executed", train_examples=8, dev_examples=2)
    assert job.validate_plan(plan) == plan
    (dependencies / "package.py").write_text("# changed without version bump\n", encoding="utf-8")
    with pytest.raises(job.JobError, match="PLAN_DRIFT"):
        job.validate_plan(plan)
    assert not Path(plan["output"]).exists()


@pytest.mark.parametrize("cuda,status", [(None, "NO_CUDA_BUILD"), ("12.8", "CUDA_BUILD_RUNTIME_UNPROBED")])
def test_torch_build_type_comes_from_bounded_literal_metadata_only(tmp_path, monkeypatch, cuda, status):
    version = tmp_path / "version.py"
    version.write_text("raise RuntimeError('MUST NOT EXECUTE')\n__version__='TEST_ONLY'\ncuda=" + repr(cuda) + "\nhip=None\n", encoding="utf-8")
    monkeypatch.setattr(runtime.metadata, "distribution", lambda _: SimpleNamespace(locate_file=lambda _: version))
    result = runtime._torch_build()
    assert result["status"] == status
    assert result["cuda"] == cuda and result["torch_imported"] is False
    assert len(result["version_source_sha256"]) == 64


def test_unreadable_or_executable_version_metadata_is_not_readiness(tmp_path, monkeypatch):
    version = tmp_path / "version.py"
    version.write_text("__version__='TEST_ONLY'\ncuda=run_something()\nhip=None\n", encoding="utf-8")
    monkeypatch.setattr(runtime.metadata, "distribution", lambda _: SimpleNamespace(locate_file=lambda _: version))
    assert runtime._torch_build()["status"] == "UNVERIFIED_BUILD_METADATA"
    version.unlink()
    assert runtime._torch_build()["status"] == "UNVERIFIED_BUILD_METADATA"


def test_new_identity_helper_is_itself_a_runtime_pin():
    assert "q4_runtime_metadata.py" in q4_checkpoint.RUNTIME_FILES
    assert len(q4_checkpoint.runtime_source_pins()["q4_runtime_metadata.py"]) == 64
