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
