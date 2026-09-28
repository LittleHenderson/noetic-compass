"""Pure-Python tests for the L2 driver's torch-free parts (no torch, no checkpoint, no learner). The "parent copy" is
a TEST DOUBLE: a small file of arbitrary bytes whose sha256 the driver must verify. Nothing here restores anything."""
import hashlib
import json
import pathlib
import sys

import pytest

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import migrate_real_parent as mrp  # noqa: E402

DIGEST = "ab" * 32
NAMES = ("left.weight", "world_head.0.weight", "world_head.3.bias")


def refused(code):
    return pytest.raises(mrp.DriverRefused, match="^" + code)


def _parent(tmp_path, content=b"\x00\x01" * 2048):
    directory = tmp_path / "parent_copy_dir"
    directory.mkdir(exist_ok=True)  # helpers may be called twice in one test
    path = directory / "parent_copy.pt"
    if not path.exists():
        path.write_bytes(content)
    return path, hashlib.sha256(content).hexdigest()


def _args(tmp_path, **overrides):
    path, sha = _parent(tmp_path)
    args = dict(parent_copy_path=path, expected_sha256=sha, expected_run_identity_digest=DIGEST,
                expected_learnable_names=NAMES, out_dir=tmp_path / "out" / "grown", device="cuda:0")
    args.update(overrides)
    return args


def test_preflight_accepts_a_matching_copy_and_returns_its_identity(tmp_path):
    parent = mrp.preflight(**_args(tmp_path))
    assert parent["sha256"] == _args(tmp_path)["expected_sha256"] and parent["bytes"] == 4096
    assert parent["learnable_names"] == sorted(NAMES) and parent["learnable_names_count"] == 3
    assert parent["path"].endswith("parent_copy.pt")


def test_preflight_refuses_a_copy_whose_bytes_differ_from_the_declared_parent(tmp_path):
    args = _args(tmp_path, expected_sha256="cd" * 32)
    with refused("PARENT_COPY_SHA_MISMATCH"):
        mrp.preflight(**args)


def test_preflight_refuses_missing_file_bad_identity_and_cpu(tmp_path):
    with refused("PARENT_COPY_NOT_A_FILE"):
        mrp.preflight(**_args(tmp_path, parent_copy_path=tmp_path / "nothing.pt"))
    with refused("IDENTITY_FIELD_INVALID: expected_run_identity_digest"):
        mrp.preflight(**_args(tmp_path, expected_run_identity_digest="short"))
    with refused("IDENTITY_FIELD_INVALID: expected_learnable_names"):
        mrp.preflight(**_args(tmp_path, expected_learnable_names=()))
    with refused("IDENTITY_FIELD_INVALID: expected_learnable_names"):
        mrp.preflight(**_args(tmp_path, expected_learnable_names=("a", "a")))
    with refused("GPU_REQUIRED"):
        mrp.preflight(**_args(tmp_path, device="cpu"))
    with refused("IDENTITY_FIELD_INVALID: init_seed"):
        mrp.preflight(**_args(tmp_path), init_seed=None)


def test_preflight_refuses_an_output_directory_that_exists_or_is_nested_with_the_parent(tmp_path):
    path, sha = _parent(tmp_path)
    existing = tmp_path / "already"
    existing.mkdir()
    with refused("OUTPUT_DIR_NOT_FRESH"):
        mrp.preflight(**_args(tmp_path, out_dir=existing))
    with refused("OUTPUT_DIR_NESTED_WITH_PARENT"):
        mrp.preflight(**_args(tmp_path, out_dir=path.parent / "grown"))  # beside the parent copy
    with refused("OUTPUT_DIR_NESTED_WITH_PARENT"):
        mrp.preflight(**_args(tmp_path, out_dir=path.parent / "sub" / "grown"))  # deeper inside the parent's directory
    with refused("OUTPUT_DIR_NOT_FRESH"):
        mrp.preflight(**_args(tmp_path, out_dir=path.parent.parent))  # an ancestor always exists: refused as not fresh first


def test_rollback_record_names_the_exact_parent_and_is_digest_sealed(tmp_path):
    parent = mrp.preflight(**_args(tmp_path))
    rollback = mrp.rollback_record(parent, cursor=2940, model_revision=2940)
    assert rollback["rollback_parent"]["sha256"] == parent["sha256"] and rollback["cursor"] == 2940
    assert rollback["digest"] == mrp._digest(rollback)
    with refused("RESTORED_IDENTITY_MISMATCH"):
        mrp.rollback_record(parent, cursor=2940, model_revision=2941)


def test_record_carries_the_claim_boundary_and_rejects_tampering(tmp_path):
    parent = mrp.preflight(**_args(tmp_path))
    rollback = mrp.rollback_record(parent, cursor=2940, model_revision=2940)
    record = mrp.build_record(parent=parent, rollback=rollback, specialist={"init_seed": 1, "hidden": 16, "enabled": False},
                              plan_digest=DIGEST, mapping_summary={"carried_by_name": 3}, preservation={"parameters_exactly_equal": True,
                              "optimizer_state_exactly_equal": True}, probe=None, grown_files={"grown_state.pt": DIGEST},
                              sidecar_digest=DIGEST, venue=None)
    assert mrp.verify_record(record) is record
    assert record["claim_boundary"]["training_uses_specialist"] is False
    assert record["claim_boundary"]["forward_path_integration"].startswith("NOT_DONE")
    assert record["claim_boundary"]["measured_task_benefit"] == "NO_CLAIM"
    assert record["venue"] == "UNDECLARED" and record["rollback_digest"] == rollback["digest"]
    tampered = json.loads(json.dumps(record))
    tampered["preservation"]["parameters_exactly_equal"] = False
    with refused("RECORD_DIGEST_MISMATCH"):
        mrp.verify_record(tampered)


def test_builder_interfaces_are_the_executing_source_calls():
    b = mrp.EXACT_BUILDER_INTERFACES
    assert b["source_commit"] == "cd5ce96ca0a64e0dbe82562bedf565e1bf66bfc7"
    assert "w.matched._framework(torch, device," in b["framework"]
    assert "build_frozen_typed_encoder(torch, tokenizer, seed=w.contract.DESIGN['encoder_seed'], d_model=64, device=device)" in b["encoder"]
    assert "restore_checkpoint(torch, framework, encoder, path=" in b["loader"] and "expected_learnable_names=" in b["loader"]
    assert set(mrp.LEARNER_INTERFACE) == {"module", "optimizer", "optimizer_config", "cursor", "model_revision", "run_identity_digest"}


def test_driver_refusal_codes_are_a_closed_set():
    with pytest.raises(ValueError, match="UNKNOWN_DRIVER_REFUSAL_CODE:BOGUS"):
        mrp.DriverRefused("BOGUS")
    assert "GPU_REQUIRED" in mrp.DRIVER_REFUSALS and "REAL_PARENT_PRESERVATION_FAILED" in mrp.DRIVER_REFUSALS


def test_run_refuses_before_calling_the_loader_when_the_copy_does_not_match(tmp_path):
    calls = []

    def restore_double(*args, **kwargs):  # TEST DOUBLE loader: must never be reached
        calls.append((args, kwargs))
        raise AssertionError("loader must not be called")

    class TorchDouble:  # TEST DOUBLE: only what preflight needs before torch is really used
        @staticmethod
        def is_tensor(value):
            return False

    args = _args(tmp_path, expected_sha256="ef" * 32)
    with refused("PARENT_COPY_SHA_MISMATCH"):
        mrp.run_real_parent_migration(torch=TorchDouble(), restore=restore_double, framework=object(), encoder=object(), **args)
    assert calls == [] and not (tmp_path / "out").exists()
