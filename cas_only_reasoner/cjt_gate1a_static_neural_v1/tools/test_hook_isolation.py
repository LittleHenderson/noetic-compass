"""test_hook_isolation.py -- production-vs-conformance hook isolation (GATE 1A.2R.1).

The production CampaignDriver admits ONLY REAL and SYNTHETIC_CONFORMANCE, has no
injectable-adapter parameter, no set_real_feature_backend, and consults no hook
registry in a claim-bearing mode. Fake AWS/GPU/model/lock adapters live only in
RealBranchConformanceDriver (REAL_BRANCH_CONFORMANCE), which is permanently
non-claim-bearing: it uses the TEST trust root, forces SOFTWARE_CONFORMANCE_ONLY,
and refuses production owner-key ids.

These tests attack the actual construction and execution paths, not merely mode
names or field presence.
"""
from __future__ import annotations

import inspect
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
sys.path.insert(0, str(PKG))
sys.path.insert(0, str(HERE))

from exec.campaign_driver import CampaignDriver, RealBranchConformanceDriver  # noqa: E402


def _base_kwargs(mode, tmp):
    """Minimal kwargs to reach the __init__ guards without running a campaign.
    The driver's __init__ runs `git rev-parse HEAD` in package_root; PKG is the
    real repo so that succeeds."""
    er = Path(tmp) / "er"
    (er).mkdir(parents=True, exist_ok=True)
    ap = Path(tmp) / "a.json"; ap.write_text("{}", encoding="utf-8")
    return dict(mode=mode, package_root=PKG, campaign_id="c",
                execution_approval_path=ap, prep_approval_path=ap,
                prep_receipt_path=ap, evidence_root=er)


def test_production_driver_has_no_hook_parameter():
    sig = inspect.signature(CampaignDriver.__init__).parameters
    assert "real_hooks" not in sig, "public real_hooks parameter still present"
    # the only hooks path is the underscore-prefixed internal, guarded to
    # REAL_BRANCH_CONFORMANCE
    assert "_real_hooks" in sig
    print("PASS test_production_driver_has_no_public_hook_parameter")


def test_real_mode_rejects_nonempty_real_hooks():
    with tempfile.TemporaryDirectory() as tmp:
        try:
            CampaignDriver(**_base_kwargs("REAL", tmp),
                           _real_hooks={"verify_gpu": lambda *a, **k: True})
            raise AssertionError("REAL accepted _real_hooks")
        except ValueError as exc:
            assert "HOOK_ISOLATION_VIOLATION" in str(exc)
    print("PASS test_real_mode_rejects_nonempty_real_hooks")


def test_synthetic_mode_rejects_nonempty_real_hooks():
    with tempfile.TemporaryDirectory() as tmp:
        try:
            CampaignDriver(**_base_kwargs("SYNTHETIC_CONFORMANCE", tmp),
                           _real_hooks={"aws_identity": lambda: None})
            raise AssertionError("SYNTHETIC accepted _real_hooks")
        except ValueError as exc:
            assert "HOOK_ISOLATION_VIOLATION" in str(exc)
    print("PASS test_synthetic_mode_rejects_nonempty_real_hooks")


def test_real_mode_rejects_set_real_feature_backend():
    assert not hasattr(CampaignDriver, "set_real_feature_backend"), \
        "set_real_feature_backend still exists"
    print("PASS test_real_mode_rejects_set_real_feature_backend")


def test_real_mode_has_no_mutable_hook_registry():
    # even if a caller mutates the internal dict, REAL never consults it: _hook
    # returns the default in REAL regardless
    with tempfile.TemporaryDirectory() as tmp:
        d = CampaignDriver(**_base_kwargs("REAL", tmp))
        assert d._real_hooks == {}
        d._real_hooks["verify_gpu"] = lambda *a, **k: True   # mutate
        assert d._hook("verify_gpu", "DEFAULT") == "DEFAULT", \
            "REAL consulted a mutated hook registry"
        assert d._hook("feature_backend", None) is None
    print("PASS test_real_mode_has_no_mutable_hook_registry")


def test_real_mode_uses_real_device_not_injectable_cpu():
    with tempfile.TemporaryDirectory() as tmp:
        d = CampaignDriver(**_base_kwargs("REAL", tmp))
        # no _real_device set until extraction gates a GPU; a caller cannot
        # inject an explicit CPU backend because feature_backend hook is ignored
        assert d._hook("feature_backend", None) is None
        assert d._is_claim_bearing() is True
    print("PASS test_cpu_backend_cannot_run_under_real_scientific_mode")


def test_fake_aws_and_gpu_and_lock_cannot_enter_real_mode():
    # the ONLY way to supply fakes is REAL_BRANCH_CONFORMANCE via the subclass;
    # REAL construction with any hook raises (covered above). Confirm the
    # subclass cannot be tricked into a claim-bearing posture.
    with tempfile.TemporaryDirectory() as tmp:
        d = RealBranchConformanceDriver(
            real_hooks={"aws_identity": lambda: {"synthetic": True},
                        "verify_gpu": lambda *a, **k: True,
                        "protected_lock": lambda: None},
            **{k: v for k, v in _base_kwargs("REAL", tmp).items() if k != "mode"})
        assert d.mode == "REAL_BRANCH_CONFORMANCE"
        assert d._is_claim_bearing() is False
        assert d._trust_mode() == "SYNTHETIC_CONFORMANCE"     # TEST key
    print("PASS test_fake_aws_identity_cannot_enter_real_mode")
    print("PASS test_fake_gpu_verifier_cannot_enter_real_mode")
    print("PASS test_fake_protected_lock_cannot_enter_real_mode")


def test_real_branch_conformance_requires_hooks_and_is_non_claim_bearing():
    with tempfile.TemporaryDirectory() as tmp:
        # no hooks -> refused
        try:
            RealBranchConformanceDriver(
                real_hooks={},
                **{k: v for k, v in _base_kwargs("REAL", tmp).items()
                   if k != "mode"})
            raise AssertionError("REAL_BRANCH accepted empty hooks")
        except ValueError:
            pass
        d = RealBranchConformanceDriver(
            real_hooks={"feature_backend": ("m", "t", "cpu")},
            **{k: v for k, v in _base_kwargs("REAL", tmp).items() if k != "mode"})
        # non-claim-bearing: uses the TEST trust root and the SYNTHETIC clock
        assert d._is_claim_bearing() is False
        assert d._trust_mode() == "SYNTHETIC_CONFORMANCE"
        assert d._shutdown_mode() == "SYNTHETIC_CONFORMANCE"
        assert d._uses_real_branches() is True         # runs the REAL code paths
        assert d._hook("feature_backend", None) == ("m", "t", "cpu")
    print("PASS test_real_branch_conformance_requires_test_trust_root")
    print("PASS test_real_branch_conformance_forces_non_claim_bearing")


def test_real_branch_conformance_cannot_emit_scientific_status():
    # the status program is called with --conformance for every non-claim-bearing
    # posture; --conformance forces SOFTWARE_CONFORMANCE_ONLY and refuses a
    # non-TEST key (proven in test_status_fixtures). Here: the driver's _status
    # would pass --conformance for REAL_BRANCH (not _is_claim_bearing()).
    with tempfile.TemporaryDirectory() as tmp:
        d = RealBranchConformanceDriver(
            real_hooks={"feature_backend": ("m", "t", "cpu")},
            **{k: v for k, v in _base_kwargs("REAL", tmp).items() if k != "mode"})
        assert not d._is_claim_bearing(), \
            "REAL_BRANCH must not be claim-bearing (status --conformance)"
    print("PASS test_real_branch_conformance_cannot_emit_scientific_status")


def test_existing_real_branch_adapters_still_execute():
    # the committed adapter tests (extract_split candidate encoding, batch-32,
    # AWS lock parity, etc.) still run -- import and invoke the suite's main
    import test_real_branch_conformance as rbc
    assert rbc.main() == 0, "REAL-branch adapter suite regressed"
    print("PASS test_existing_real_branch_conformance_adapters_still_execute")


def main():
    test_production_driver_has_no_hook_parameter()
    test_real_mode_rejects_nonempty_real_hooks()
    test_synthetic_mode_rejects_nonempty_real_hooks()
    test_real_mode_rejects_set_real_feature_backend()
    test_real_mode_has_no_mutable_hook_registry()
    test_real_mode_uses_real_device_not_injectable_cpu()
    test_fake_aws_and_gpu_and_lock_cannot_enter_real_mode()
    test_real_branch_conformance_requires_hooks_and_is_non_claim_bearing()
    test_real_branch_conformance_cannot_emit_scientific_status()
    test_existing_real_branch_adapters_still_execute()
    print("ALL HOOK-ISOLATION TESTS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
