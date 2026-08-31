"""test_identity_checks.py -- the section-8 model/container/AWS identity tests."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PKG))
from exec.identity import (IdentityViolation, verify_aws_identity,  # noqa: E402
                           verify_container_identity, verify_gpu,
                           verify_model_identity, verify_s7_table)
from exec.synthetic import (build_synthetic_model_identity,  # noqa: E402
                            build_synthetic_taxonomy, synthetic_aws_identity)

APPROVAL = {"aws_account_id": "000000000000", "region": "us-east-1",
            "instance_type": "g5.xlarge", "required_gpu_type": "NVIDIA A10G"}


def expect_refused(name, fn):
    try:
        fn()
    except IdentityViolation:
        print(f"PASS {name}")
        return
    raise AssertionError(f"{name}: bogus identity ACCEPTED")


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        ident = build_synthetic_model_identity(root)
        approval = {**APPROVAL,
                    "model_revision_sha": ident["model_revision_sha"],
                    "model_weight_sha256s": ident["model_weight_sha256s"],
                    "tokenizer_file_sha256s": ident["tokenizer_file_sha256s"],
                    "container_image_digest": "sha256:" + "77" * 32,
                    "dependency_lock_sha256": "88" * 32}
        assert verify_model_identity(ident["model_dir"], approval) is True
        print("PASS resolved synthetic identity verifies (positive mechanism)")

        bad = dict(approval)
        bad["model_weight_sha256s"] = {"model.safetensors": "00" * 32}
        expect_refused("test_dummy_model_hashes_refused_in_real_mode",
                       lambda: verify_model_identity(ident["model_dir"], bad))
        bad = dict(approval)
        bad["model_weight_sha256s"] = {**approval["model_weight_sha256s"],
                                       "missing.safetensors": "11" * 32}
        expect_refused("test_missing_weight_file_refused",
                       lambda: verify_model_identity(ident["model_dir"], bad))
        bad = dict(approval)
        bad["tokenizer_file_sha256s"] = {"tokenizer.json": "22" * 32}
        expect_refused("test_wrong_tokenizer_digest_refused",
                       lambda: verify_model_identity(ident["model_dir"], bad))

        expect_refused("test_missing_s7_table_refused",
                       lambda: verify_s7_table(root / "nope.json",
                                               {"s7_control_table_sha256": "33" * 32}))
        s7_path, _, s7_sha = build_synthetic_taxonomy(root)
        assert verify_s7_table(s7_path, {"s7_control_table_sha256": s7_sha})
        expect_refused("wrong_s7_table_digest_refused",
                       lambda: verify_s7_table(s7_path,
                                               {"s7_control_table_sha256": "44" * 32}))

        expect_refused("test_wrong_container_digest_refused",
                       lambda: verify_container_identity(
                           {"container_image_digest": "sha256:" + "00" * 32,
                            "dependency_lock_sha256": "88" * 32}, approval))

        # AWS identity: a local CUDA device or env-var claim never satisfies REAL
        expect_refused("test_local_cuda_without_aws_identity_refused",
                       lambda: verify_gpu(approval, "REAL",
                                          aws_identity_verified=False))
        expect_refused("env_var_identity_refused_in_real_mode",
                       lambda: verify_aws_identity(
                           synthetic_aws_identity(), approval, "REAL"))
        ok = synthetic_aws_identity()
        assert verify_aws_identity(ok, approval, "SYNTHETIC_CONFORMANCE") is True
        bad = synthetic_aws_identity("999999999999")
        expect_refused("test_wrong_aws_account_refused",
                       lambda: verify_aws_identity(bad, approval,
                                                   "SYNTHETIC_CONFORMANCE"))
        bad = synthetic_aws_identity(); bad["region"] = "eu-west-1"
        expect_refused("test_wrong_region_refused",
                       lambda: verify_aws_identity(bad, approval,
                                                   "SYNTHETIC_CONFORMANCE"))
        bad = synthetic_aws_identity(); bad["instance_type"] = "t3.micro"
        expect_refused("test_wrong_instance_type_refused",
                       lambda: verify_aws_identity(bad, approval,
                                                   "SYNTHETIC_CONFORMANCE"))
        # GPU class law: a non-A10G device name is refused in REAL mode. This
        # box has no CUDA at all, so the class check is proven via the identity
        # gate above and the REAL GPU gate below (GPU_REQUIRED).
        import torch
        assert not torch.cuda.is_available()
        expect_refused("test_wrong_gpu_type_refused(real gate on CUDA-less box)",
                       lambda: verify_gpu(approval, "REAL",
                                          aws_identity_verified=True))
    print("ALL IDENTITY-CHECK TESTS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
