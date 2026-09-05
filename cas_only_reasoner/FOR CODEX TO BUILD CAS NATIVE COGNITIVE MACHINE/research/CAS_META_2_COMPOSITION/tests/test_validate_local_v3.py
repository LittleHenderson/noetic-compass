"""Pure validator contracts; no child tests, neural work, or provider calls."""
import importlib
import importlib.util
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

PATH = Path(__file__).parents[1] / "tools/validate_local_v3.py"
spec = importlib.util.spec_from_file_location("cas_meta2_pure_validator_v3_tests", PATH)
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def test_timeout_uses_600_seconds_and_preserves_exact_bytes():
    seen = {}
    def runner(command, **kwargs):
        seen.update(kwargs)
        raise subprocess.TimeoutExpired(command, kwargs["timeout"], output=b"partial\xff\n",
                                        stderr=b"warning\x00\n")
    result, stdout, stderr = validator.run_child(["python", "fixture"], {}, runner=runner)
    assert seen["timeout"] == 600 and seen["capture_output"] is True
    assert result["timed_out"] and result["returncode"] is None
    assert result["capture_available"] == {"stdout": True, "stderr": True}
    assert stdout == b"partial\xff\n" and stderr == b"warning\x00\n"


def test_missing_timeout_output_is_not_claimed_available():
    def runner(command, **kwargs):
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])
    result, stdout, stderr = validator.run_child(["python", "fixture"], {}, runner=runner)
    assert result["capture_available"] == {"stdout": False, "stderr": False}
    assert stdout == stderr == b""


@pytest.mark.parametrize("returncode", [0, 1, 2])
def test_completed_child_preserves_exit_code_and_raw_bytes(returncode):
    def runner(command, **kwargs):
        return SimpleNamespace(returncode=returncode, stdout=b"raw\r\n", stderr=b"err")
    result, stdout, stderr = validator.run_child(["python", "fixture"], {}, runner=runner)
    assert result["returncode"] == returncode and result["timed_out"] is False
    assert stdout == b"raw\r\n" and stderr == b"err"


@pytest.mark.parametrize("value", [b"data", "data", None])
def test_capture_types(value):
    assert validator.capture_bytes(value) == (b"" if value is None else b"data")


def test_unexpected_capture_type_is_rejected():
    with pytest.raises(ValueError, match="CAPTURE_TYPE"):
        validator.capture_bytes(3)


@pytest.mark.parametrize("name", sorted(validator.FORBIDDEN_IMPORTS))
def test_neural_and_provider_import_names_refused(name):
    with pytest.raises(RuntimeError, match="IMPORT_FORBIDDEN"):
        validator.NoNeuralOrProviderImports().find_spec(name + ".child")


def test_pure_standard_library_import_is_not_blocked():
    assert validator.NoNeuralOrProviderImports().find_spec("json") is None


def test_real_sdk_exception_import_works_without_live_client_modules(monkeypatch):
    monkeypatch.setattr(sys, "meta_path", [validator.NoNeuralOrProviderImports(), *sys.meta_path])
    from botocore.exceptions import ClientError
    error = ClientError({"Error": {"Code": "NoSuchEntity", "Message": "pure fixture"}}, "DeleteRolePolicy")
    assert error.response["Error"]["Code"] == "NoSuchEntity"
    loaded = {name for name in sys.modules if name == "botocore" or name.startswith("botocore.")}
    assert loaded <= validator.PURE_EXCEPTION_MODULES


@pytest.mark.parametrize("name", ["boto3", "botocore.session", "botocore.client", "botocore.endpoint",
    "botocore.httpsession", "botocore.credentials", "botocore.vendored.requests.sessions"])
def test_actual_live_client_import_attempts_are_refused(monkeypatch, name):
    monkeypatch.setattr(sys, "meta_path", [validator.NoNeuralOrProviderImports(), *sys.meta_path])
    assert name not in sys.modules
    with pytest.raises(RuntimeError, match="IMPORT_FORBIDDEN"):
        importlib.import_module(name)


def test_protected_manifest_is_pinned_before_parsing(monkeypatch):
    assert validator.BASELINE_MANIFEST_SHA256 == "476a8bbdc7a4b07a406e46b246ed417ea1d902e04cfb852ca710de09dcbc59f0"
    monkeypatch.setattr(validator, "file_hash", lambda path: "0" * 64)
    with pytest.raises(ValueError, match="ACCEPTED_PROTECTED_MANIFEST_DIGEST_MISMATCH"):
        validator.protected_snapshot()


def test_record_directory_must_be_new_and_contained(monkeypatch, tmp_path):
    monkeypatch.setattr(validator, "ROOT", tmp_path / "pilot")
    records = validator.ROOT / "records"
    records.mkdir(parents=True)
    output = validator.new_output(records / "new")
    assert output.is_dir()
    with pytest.raises(ValueError, match="NEW_CONTAINED"):
        validator.new_output(output)
    with pytest.raises(ValueError, match="NEW_CONTAINED"):
        validator.new_output(records)
    with pytest.raises(ValueError, match="NEW_CONTAINED"):
        validator.new_output(tmp_path / "elsewhere")


def test_source_snapshot_covers_assets_and_detects_new_source(monkeypatch, tmp_path):
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    for name in ("cas_meta2", "aws", "tools", "tests"):
        (tmp_path / name).mkdir()
    (tmp_path / "cas_meta2/mod.py").write_text("value = 1\n")
    (tmp_path / "cas_meta2/asset.json").write_text("{}\n")
    (tmp_path / "pyproject.toml").write_text("[project]\n")
    before = validator.source_snapshot()
    assert set(before) == {"cas_meta2/mod.py", "cas_meta2/asset.json", "pyproject.toml"}
    (tmp_path / "cas_meta2/new.py").write_text("value = 2\n")
    assert validator.source_snapshot() != before


def test_invalid_python_is_not_silently_hashed(monkeypatch, tmp_path):
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    for name in ("cas_meta2", "aws", "tools", "tests"):
        (tmp_path / name).mkdir()
    (tmp_path / "tools/broken.py").write_text("def broken(\n")
    with pytest.raises(SyntaxError):
        validator.source_snapshot()


def test_junit_absent_is_unknown_not_zero(tmp_path):
    assert validator.junit_counts(tmp_path / "missing.xml") is None


def test_receipt_refuses_overwrite(tmp_path):
    path = tmp_path / "receipt.json"
    validator.save_json(path, {"completed": False})
    with pytest.raises(FileExistsError):
        validator.save_json(path, {"completed": True})
    assert '"completed": false' in path.read_text()
