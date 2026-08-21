"""Refuse a bad LIVE activation parameter set BEFORE it reaches CloudFormation.

WHY THIS EXISTS
---------------
The guardian template carries a `Rules` section whose assertions look like a
parameter gate: non-zero binding hashes, a bound provider account, recovery
enabled under LIVE. Measured against real CloudFormation on 2026-08-21, **none
of them are enforced**. Change sets were accepted with `CoreLockSha256` all
zeros, `TimingValidationEvidenceSha256` all zeros, `ProviderAccountId=UNBOUND`,
and `RecoveryEnabled=FALSE` under LIVE -- every one explicitly forbidden by the
assertions. `Rules` is a Service Catalog feature; direct CloudFormation ignores
it entirely.

So the template's apparent gate is documentation, not a control. This module is
the control: run it before `create_change_set` and it refuses the parameter set
that the template would have waved through.

It is deliberately dependency-free and offline. It never contacts AWS, never
reads a secret, and never prints a parameter value that is marked NoEcho.
"""

from __future__ import annotations

import hashlib
import json
from typing import Iterable, Mapping

# Domain prefix used by create_deployment_binding.py and by
# guardian_runtime._verify_local_material_binding. Copied byte-exact from
# guardian_runtime.py:57 -- NOT reconstructed from memory. An earlier draft of
# this file guessed the value and its own tests caught the guess.
DEPLOYMENT_BINDING_DOMAIN = b"CAS-AWS-RUNPOD-GUARDIAN-DEPLOYMENT-V1\x00"

_ZERO_SHA256 = "0" * 64
_HASH_PARAMETERS = (
    "CoreLockSha256",
    "RuntimeZipSha256",
    "DeploymentBindingSha256",
    "DeploymentBindingObjectSha256",
    "TimingValidationEvidenceSha256",
)
_NON_EMPTY_PARAMETERS = (
    "LambdaArtifactKey",
    "LambdaArtifactVersion",
    "DeploymentBindingObjectKey",
    "DeploymentBindingObjectVersion",
    "TimingEvidenceObjectKey",
    "TimingEvidenceObjectVersion",
)


class ActivationParameterError(ValueError):
    """Raised when the parameter set must not be submitted."""


def canonical_json_bytes(value: object) -> bytes:
    """Byte-exact canonical form, mirroring guardian_runtime._binding_canonical:
    sorted keys, tight separators, no NaN, UTF-8, with a TRAILING NEWLINE."""
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def required_binding_hashes(binding_document_bytes: bytes) -> tuple[str, str]:
    """Return (DeploymentBindingSha256, DeploymentBindingObjectSha256).

    The first hashes the document source with the two hash fields REMOVED, under
    the domain prefix. The second hashes the raw object bytes, which INCLUDE
    them. They can never be equal for any binding document.
    """
    document = json.loads(binding_document_bytes.decode("utf-8"))
    if not isinstance(document, dict):
        raise ActivationParameterError("binding document must be a JSON object")
    source = {
        key: value
        for key, value in document.items()
        if key not in ("deployment_binding_sha256", "binding_document_sha256")
    }
    binding = hashlib.sha256(
        DEPLOYMENT_BINDING_DOMAIN + canonical_json_bytes(source)
    ).hexdigest()
    object_hash = hashlib.sha256(binding_document_bytes).hexdigest()
    if binding == object_hash:  # pragma: no cover - impossible by construction
        raise ActivationParameterError(
            "internal error: the two required hashes computed equal"
        )
    return binding, object_hash


def verify_activation_parameters(
    parameters: Mapping[str, str],
    binding_document_bytes: bytes | None = None,
) -> list[str]:
    """Return the list of failures. Empty list means the set may be submitted.

    Only LIVE parameter sets are checked; an INERT set is returned unvalidated
    because the runtime refuses to act on it anyway.
    """
    failures: list[str] = []
    if parameters.get("ActivationMode") != "LIVE":
        return failures

    for name in _HASH_PARAMETERS:
        value = parameters.get(name)
        if value is None:
            failures.append(f"{name} is absent; LIVE requires it")
            continue
        if value == _ZERO_SHA256:
            failures.append(f"{name} is all zeros, which is a placeholder, not a hash")
        elif len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            failures.append(f"{name} is not 64 lowercase hex characters")

    for name in _NON_EMPTY_PARAMETERS:
        if not parameters.get(name):
            failures.append(f"{name} is empty; LIVE requires an immutable pin")

    if parameters.get("ProviderAccountId") in (None, "", "UNBOUND"):
        failures.append("ProviderAccountId is UNBOUND; LIVE requires an exact binding")
    if parameters.get("RecoveryEnabled") != "TRUE":
        failures.append("RecoveryEnabled must be TRUE under LIVE")
    if parameters.get("RecoveryScheduleState") != "ENABLED":
        failures.append("RecoveryScheduleState must be ENABLED under LIVE")

    binding = parameters.get("DeploymentBindingSha256")
    object_hash = parameters.get("DeploymentBindingObjectSha256")

    # The defect the template's dead Rule was meant to catch.
    if binding is not None and binding == object_hash:
        failures.append(
            "DeploymentBindingSha256 equals DeploymentBindingObjectSha256. They "
            "hash different byte strings and can never be equal; one slot holds "
            "the wrong value. All nine Lambdas would fail closed with "
            "LOCAL_MATERIAL_BINDING_DIGEST_MISMATCH at first invocation."
        )

    # A masked value can never be verified, so it can never be submitted.
    for name in ("DeploymentBindingSha256", "DeploymentBindingObjectSha256"):
        if parameters.get(name) == "****":
            failures.append(
                f"{name} is the NoEcho mask, not a value. Supply the real hash; "
                "it cannot be round-tripped out of CloudFormation."
            )

    if binding_document_bytes is not None:
        want_binding, want_object = required_binding_hashes(binding_document_bytes)
        if binding != want_binding:
            failures.append(
                "DeploymentBindingSha256 does not match the binding document "
                f"(expected {want_binding})"
            )
        if object_hash != want_object:
            failures.append(
                "DeploymentBindingObjectSha256 does not match the binding document "
                f"bytes (expected {want_object})"
            )
    return failures


def require_submittable(
    parameters: Mapping[str, str],
    binding_document_bytes: bytes | None = None,
) -> None:
    """Raise unless the parameter set may be submitted to CloudFormation."""
    failures = verify_activation_parameters(parameters, binding_document_bytes)
    if failures:
        joined = "\n  - ".join(failures)
        raise ActivationParameterError(
            f"REFUSED: this LIVE parameter set must not be submitted:\n  - {joined}"
        )


def _parameters_from_cli(pairs: Iterable[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for pair in pairs:
        key, _, value = pair.partition("=")
        out[key] = value
    return out


def main(argv: list[str] | None = None) -> int:
    import argparse
    import pathlib
    import sys

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--parameters-json",
        type=pathlib.Path,
        help="JSON object of ParameterKey -> ParameterValue",
    )
    parser.add_argument(
        "--parameter", action="append", default=[], help="Key=Value (repeatable)"
    )
    parser.add_argument(
        "--binding-document",
        type=pathlib.Path,
        help="the deployment-binding JSON whose bytes were uploaded to S3",
    )
    args = parser.parse_args(argv)

    parameters: dict[str, str] = {}
    if args.parameters_json:
        parameters.update(json.loads(args.parameters_json.read_text("utf-8")))
    parameters.update(_parameters_from_cli(args.parameter))

    document = args.binding_document.read_bytes() if args.binding_document else None
    try:
        require_submittable(parameters, document)
    except ActivationParameterError as error:
        print(str(error), file=sys.stderr)
        return 2
    print("OK: parameter set is submittable")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
