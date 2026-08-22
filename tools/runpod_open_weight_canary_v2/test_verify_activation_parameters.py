"""Every case here was ACCEPTED by real CloudFormation on 2026-08-21.

The template's Rules section forbids all of them and fired on none of them,
because Rules is a Service Catalog feature that direct CloudFormation ignores.
These tests pin the behaviour of the control that actually runs.
"""

import json
import pathlib

import pytest

import verify_activation_parameters as vap

HERE = pathlib.Path(__file__).resolve().parent
BINDING = (
    HERE.parents[1]
    / "docs"
    / "working"
    / "aws_gate1_evidence_20260821"
    / "timing_evidence"
    / "deployment-binding.PREPROD.json"
)
ZERO = "0" * 64

# The proven-good set, measured from the real binding document.
GOOD = {
    "ActivationMode": "LIVE",
    "CoreLockSha256": "6b71e33d3e98308d8f72903a2643f7b6721511a1b53ac6642601f79a4707f453",
    "RuntimeZipSha256": "487145fa705aea91bf58169e2ea14624fd3ef3b7667b53bf3cb3275418180ad7",
    "LambdaArtifactKey": "runpod-guardian/487145fa/guardian-runtime.zip",
    "LambdaArtifactVersion": "1bzPh8DPxpWRAh9z3FtpMlu4NKnNxNSX",
    "DeploymentBindingSha256": "87f0293105b3b84202d52e7d2cbd209f90dd62634981e4d7ee2ce80ed522bf9d",
    "DeploymentBindingObjectSha256": "92add9c4fca1cb040a5908fa6635842d62c40094d8b8174614528206a7efab85",
    "DeploymentBindingObjectKey": "runpod-guardian/activation/PREPROD/deployment-binding.json",
    "DeploymentBindingObjectVersion": "jeWBLBDaTc213srwVpOLgr5XE916DexO",
    "TimingValidationEvidenceSha256": "59462f7d469c53ae377052b953582d43663a3288977e20ff7c7c85149d962126",
    "TimingEvidenceObjectKey": "runpod-guardian/activation/PREPROD/timing-evidence.json",
    "TimingEvidenceObjectVersion": "OsjCHqefUNq6hbeGT2.TurX8ib09vhkw",
    "ProviderAccountId": "user_38E4xHk5H6yjrzEh4KUse08Ia8U",
    "RecoveryEnabled": "TRUE",
    "RecoveryScheduleState": "ENABLED",
}


def test_the_proven_good_parameter_set_is_submittable():
    assert vap.verify_activation_parameters(GOOD) == []


def test_required_hashes_are_derived_correctly_from_the_real_document():
    raw = BINDING.read_bytes()
    binding, object_hash = vap.required_binding_hashes(raw)
    assert binding == GOOD["DeploymentBindingSha256"]
    assert object_hash == GOOD["DeploymentBindingObjectSha256"]
    assert binding != object_hash
    # The domain-prefixed digest must equal the document's own recorded field.
    assert binding == json.loads(raw)["deployment_binding_sha256"]


def test_good_set_verifies_against_the_real_binding_document():
    assert vap.verify_activation_parameters(GOOD, BINDING.read_bytes()) == []


@pytest.mark.parametrize(
    "override, expected_fragment",
    [
        # === each of these was ACCEPTED by real CloudFormation ===
        ({"CoreLockSha256": ZERO}, "all zeros"),
        ({"TimingValidationEvidenceSha256": ZERO}, "all zeros"),
        ({"ProviderAccountId": "UNBOUND"}, "UNBOUND"),
        ({"RecoveryEnabled": "FALSE"}, "RecoveryEnabled must be TRUE"),
        ({"RecoveryScheduleState": "DISABLED"}, "must be ENABLED"),
        # === the defect the dead Rule was added to catch ===
        (
            {"DeploymentBindingSha256": GOOD["DeploymentBindingObjectSha256"]},
            "can never be equal",
        ),
        # === the NoEcho mask masquerading as a value ===
        ({"DeploymentBindingSha256": "****"}, "NoEcho mask"),
        # === structural nonsense ===
        ({"DeploymentBindingObjectVersion": ""}, "immutable pin"),
        ({"RuntimeZipSha256": "NOTAHASH"}, "64 lowercase hex"),
    ],
)
def test_refuses_every_set_that_cloudformation_accepted(override, expected_fragment):
    parameters = dict(GOOD)
    parameters.update(override)
    failures = vap.verify_activation_parameters(parameters)
    assert failures, f"must refuse {override}"
    assert any(expected_fragment in f for f in failures), failures
    with pytest.raises(vap.ActivationParameterError):
        vap.require_submittable(parameters)


def test_wrong_hash_is_caught_when_the_document_is_supplied():
    parameters = dict(GOOD)
    parameters["DeploymentBindingSha256"] = "b" * 64
    failures = vap.verify_activation_parameters(parameters, BINDING.read_bytes())
    assert any("does not match the binding document" in f for f in failures), failures


def test_inert_sets_are_not_second_guessed():
    parameters = dict(GOOD)
    parameters["ActivationMode"] = "INERT"
    parameters["CoreLockSha256"] = ZERO
    assert vap.verify_activation_parameters(parameters) == []


# ---------------------------------------------------------------------------
# Regression tests for the ABSENT-ActivationMode bypass, fixed 2026-08-22.
#
# Before the fix, verify_activation_parameters() began with
#     if parameters.get("ActivationMode") != "LIVE": return failures
# so an ABSENT key returned PASS. That is a real bypass, not a theoretical one:
# CloudFormation UsePreviousValue omits ParameterValue, so a stack that is
# ALREADY LIVE reaches this check looking INERT and skips every LIVE assertion.
# It was reproduced against this repo's own archived defective parameter set.
# ---------------------------------------------------------------------------

ARCHIVED_DEFECTIVE = (
    HERE.parents[1]
    / "docs"
    / "working"
    / "aws_gate1_evidence_20260821"
    / "timing_evidence"
    / "live_changeset_parameters.PREPROD.json"
)


def _load_archived_defective():
    raw = json.loads(ARCHIVED_DEFECTIVE.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return {p["ParameterKey"]: p.get("ParameterValue", "") for p in raw}
    return raw


def test_absent_activation_mode_is_refused_not_treated_as_inert():
    """The bypass itself: no ActivationMode key must REFUSE, never pass."""
    failures = vap.verify_activation_parameters({})
    assert failures, "an absent ActivationMode must be refused, not silently treated as INERT"
    assert any("ABSENT" in f for f in failures)


def test_archived_defective_parameter_set_is_now_refused():
    """The exact file that exited 0 before the fix, carrying the duplicated-hash defect."""
    params = _load_archived_defective()
    assert "ActivationMode" not in params, "fixture drifted: this file must have no ActivationMode"
    assert params["DeploymentBindingSha256"] == params["DeploymentBindingObjectSha256"], (
        "fixture drifted: this file must carry the duplicated-hash defect"
    )
    failures = vap.verify_activation_parameters(params)
    assert failures, "the archived defective set must be refused after the 2026-08-22 fix"


def test_explicit_inert_still_skips_live_checks():
    """INERT sets are legitimately unvalidated; the fix must not break that."""
    assert vap.verify_activation_parameters({"ActivationMode": "INERT"}) == []


def test_unrecognised_activation_mode_is_refused():
    """Anything that is neither INERT nor LIVE fails closed, including wrong case."""
    for bad in ("live", "Live", "ENABLED", ""):
        failures = vap.verify_activation_parameters({"ActivationMode": bad})
        assert failures, f"ActivationMode {bad!r} must be refused"
