import shutil
import pytest

from research.cas_closed_loop_1.check_artifacts import HERE, verify


def test_retained_exact_evidence_and_producer_bytes():
    assert verify()["files"] == 13


def test_changed_artifact_bytes_are_refused(tmp_path):
    for name in ("evidence/ARTIFACT_MANIFEST.json", "RUN_MANIFEST.json", "SOURCE_BINDINGS.json", "HISTORICAL_PRODUCER.json"):
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(HERE / name, target)
    (tmp_path / "evidence/atlas.json").write_text("{}")
    with pytest.raises(ValueError, match="ARTIFACT_BYTES_DIFFER"):
        verify(tmp_path)


def test_changed_historical_producer_snapshot_is_refused(tmp_path):
    for name in ("evidence", "provenance"):
        shutil.copytree(HERE / name, tmp_path / name)
    for name in ("RUN_MANIFEST.json", "SOURCE_BINDINGS.json", "HISTORICAL_PRODUCER.json"):
        shutil.copyfile(HERE / name, tmp_path / name)
    (tmp_path / "provenance/producer_8f55cc3a/native_step_adapter.py.txt").write_text("changed")
    with pytest.raises(ValueError, match="ARTIFACT_BYTES_DIFFER:provenance/producer_8f55cc3a/native_step_adapter.py.txt"):
        verify(tmp_path)


@pytest.mark.parametrize("ref", ["--output=elsewhere", "HEAD~1:secret"])
def test_ambiguous_git_reference_is_refused(ref):
    with pytest.raises(ValueError, match="EXACT_GIT_REF_REQUIRED"):
        verify(git_ref=ref)
