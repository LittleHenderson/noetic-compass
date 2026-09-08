"""Pure admission and command-bound checks; never execute guest commands."""
import pytest
from pathlib import Path

from aws import teaching_cycle_bootstrap as subject


def arguments():
    job = "cas-meta2-teaching-20260908000000-12345678"
    return dict(bucket=job + "-807562639912", job=job, source_sha256="a" * 64,
                driver_sha256="b" * 64, config_sha256="c" * 64, deadline_unix=1788840000)


def test_bootstrap_pins_inputs_before_install_and_keeps_extraction_separate():
    script = subject.render_bootstrap(**arguments())
    assert len(script.encode()) <= 16384
    assert script.index("PERMIT_READY") < script.index("-m pip install")
    assert "test \"$PERMIT_READY\" -eq 1" in script
    assert script.count("AWS_MAX_ATTEMPTS=1") == 1
    assert "seq 1 64" in script
    assert "--no-deps ./casformer_reference" in script
    assert "extractall" not in script and "ROOT/bundle" not in script
    assert "--root \"$BASE/job\"" in script
    assert "--bootstrap-evidence \"$BASE/bootstrap\"" in script
    assert subject.WHEEL_SHA256 in script
    assert "--config-sha256 " + "c" * 64 in script
    assert "DEADLINE=1788840000" in script
    assert "INSTALL_DEADLINE" in script and "totalleft" in script
    assert "shutdown -h now" in script
    assert "--retries 0" in script
    embedded = script.split("<<'PYBOOT'\n", 1)[1].split("\nPYBOOT", 1)[0]
    compile(embedded, "bootstrap-wheel-only-staging", "exec")  # Syntax only.


@pytest.mark.parametrize("key,value", [("job", "cas-meta2-20260907155404-80e827c9"),
    ("job", "$(whoami)"), ("bucket", "other-bucket"), ("deadline_unix", True),
    ("deadline_unix", 0), ("source_sha256", "a"), ("config_sha256", None),
    ("driver_sha256", "a;cmd")])
def test_bad_or_old_scope_rejected(key, value):
    data = arguments()
    data[key] = value
    with pytest.raises(ValueError):
        subject.render_bootstrap(**data)


def test_real_frozen_bundle_passes_standalone_guest_admission(tmp_path):
    from aws.teaching_cycle_remote import extract_training, MEMBERS
    from aws.teaching_cycle_plan import FROZEN_BINDINGS
    root = Path(__file__).resolve().parents[1]
    output = tmp_path / "bundle"
    manifest = extract_training(root / "records/teaching_cycle_001/bundle_002/training.zip", output, FROZEN_BINDINGS)
    assert manifest["source_sha256"] == FROZEN_BINDINGS["source_sha256"]
    assert {path.relative_to(output).as_posix() for path in output.rglob("*") if path.is_file()} == MEMBERS
    assert not (output / "cas_meta2/teaching_cycle/evaluation.py").exists()
    assert not (output / "evaluator_private").exists()
