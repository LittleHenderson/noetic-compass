"""Create the canonical deployment-binding document for LIVE activation.

This command is offline and prints one canonical JSON document to stdout.  It
does not call AWS or RunPod and does not accept any credential value.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any


SCHEMA = "cas_aws_runpod_guardian_deployment_binding.v1"
DOMAIN = b"CAS-AWS-RUNPOD-GUARDIAN-DEPLOYMENT-V1\x00"
REGION = "us-west-2"
PROVIDER_HOST = "rest.runpod.io"
PROVIDER_CREATE_ENDPOINT = "https://rest.runpod.io/v1/pods"
GLOBAL_LEDGER_TABLE_PREFIX = "cas-runpod-guardian-global-v1-"
_SHA = re.compile(r"^[0-9a-f]{64}$")
_ACCOUNT = re.compile(r"^[0-9]{12}$")
_ARN = re.compile(r"^arn:aws[a-zA-Z-]*:[a-z0-9-]+:[a-z0-9-]*:[0-9]{0,12}:.+$")

REQUIRED = {
    "aws_account_id",
    "aws_partition",
    "aws_region",
    "stack_id",
    "stack_name",
    "ledger_table_arn",
    "kms_signing_key_arn",
    "state_machine_arn",
    "control_function_arn",
    "observe_function_arn",
    "create_function_arn",
    "stop_function_arn",
    "starter_function_arn",
    "recovery_function_arn",
    "observe_proxy_function_arn",
    "create_proxy_function_arn",
    "stop_proxy_function_arn",
    "provider_secret_arn",
    "provider_account_id",
    "runtime_artifact_bucket",
    "runtime_artifact_key",
    "runtime_artifact_version",
    "runtime_zip_sha256",
    "core_lock_sha256",
    "timing_validation_evidence_sha256",
    "timing_evidence_bucket",
    "timing_evidence_key",
    "timing_evidence_version",
    "core_sha256",
    "runtime_sha256",
    "state_machine_sha256",
    "template_sha256",
}


class BindingError(ValueError):
    pass


def canonical(value: Any) -> bytes:
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


def create_binding(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != REQUIRED:
        raise BindingError("INPUT_KEYSET_MISMATCH")
    if not _ACCOUNT.fullmatch(value.get("aws_account_id", "")):
        raise BindingError("AWS_ACCOUNT_ID_INVALID")
    if value.get("aws_partition") != "aws" or value.get("aws_region") != REGION:
        raise BindingError("AWS_PARTITION_OR_REGION_INVALID")
    if not isinstance(value.get("stack_name"), str) or not value["stack_name"]:
        raise BindingError("STACK_NAME_INVALID")
    account = value["aws_account_id"]
    stack = value["stack_name"]
    partition = value["aws_partition"]
    expected_identities = {
        "ledger_table_arn": (
            f"arn:{partition}:dynamodb:{REGION}:{account}:table/"
            f"{GLOBAL_LEDGER_TABLE_PREFIX}{account}"
        ),
        "state_machine_arn": (
            f"arn:{partition}:states:{REGION}:{account}:stateMachine:"
            f"{stack}-guardian"
        ),
        "control_function_arn": f"arn:{partition}:lambda:{REGION}:{account}:function:{stack}-control",
        "observe_function_arn": f"arn:{partition}:lambda:{REGION}:{account}:function:{stack}-observe",
        "create_function_arn": f"arn:{partition}:lambda:{REGION}:{account}:function:{stack}-create",
        "stop_function_arn": f"arn:{partition}:lambda:{REGION}:{account}:function:{stack}-stop",
        "starter_function_arn": f"arn:{partition}:lambda:{REGION}:{account}:function:{stack}-starter",
        "recovery_function_arn": f"arn:{partition}:lambda:{REGION}:{account}:function:{stack}-recovery",
        "observe_proxy_function_arn": f"arn:{partition}:lambda:{REGION}:{account}:function:{stack}-observe-proxy",
        "create_proxy_function_arn": f"arn:{partition}:lambda:{REGION}:{account}:function:{stack}-create-proxy",
        "stop_proxy_function_arn": f"arn:{partition}:lambda:{REGION}:{account}:function:{stack}-stop-proxy",
    }
    if any(value.get(name) != expected for name, expected in expected_identities.items()):
        raise BindingError("CANONICAL_RESOURCE_IDENTITY_MISMATCH")
    arn_fields = [name for name in REQUIRED if name.endswith("_arn")]
    arn_fields.append("stack_id")
    for name in arn_fields:
        if not isinstance(value.get(name), str) or not _ARN.fullmatch(value[name]):
            raise BindingError(f"{name.upper()}_INVALID")
        if f":{REGION}:" not in value[name]:
            raise BindingError(f"{name.upper()}_REGION_MISMATCH")
        # KMS, Lambda, Step Functions, DynamoDB and Secrets Manager ARNs all
        # bind the same owning account in this deployment.
        if f":{value['aws_account_id']}:" not in value[name]:
            raise BindingError(f"{name.upper()}_ACCOUNT_MISMATCH")
    for name in (
        "runtime_zip_sha256",
        "core_lock_sha256",
        "timing_validation_evidence_sha256",
        "core_sha256",
        "runtime_sha256",
        "state_machine_sha256",
        "template_sha256",
    ):
        if not isinstance(value.get(name), str) or not _SHA.fullmatch(value[name]):
            raise BindingError(f"{name.upper()}_INVALID")
    for name in (
        "provider_account_id",
        "runtime_artifact_bucket",
        "runtime_artifact_key",
        "runtime_artifact_version",
        "timing_evidence_bucket",
        "timing_evidence_key",
        "timing_evidence_version",
    ):
        if not isinstance(value.get(name), str) or not value[name]:
            raise BindingError(f"{name.upper()}_INVALID")
    if value["timing_evidence_bucket"] != value["runtime_artifact_bucket"]:
        raise BindingError("TIMING_EVIDENCE_BUCKET_MISMATCH")
    source = {
        "schema_version": SCHEMA,
        **value,
        "provider_transport": {
            "host": PROVIDER_HOST,
            "create_endpoint": PROVIDER_CREATE_ENDPOINT,
            "tls_port": 443,
            "allowed_provider_operations_by_proxy": {
                "observe_proxy": ["GET", "GUARD", "LIST"],
                "create_proxy": ["CREATE", "GUARD"],
                "stop_proxy": ["GUARD", "STOP"],
            },
            "allowed_proxy_invocation_by_core_lambda": {
                "control": [],
                "observe": ["observe_proxy"],
                "create": ["create_proxy"],
                "stop": ["observe_proxy", "stop_proxy"],
            },
        },
        "activation_contract": {
            "activation_mode": "LIVE",
            "recovery_enabled": True,
            "recovery_schedule_state": "ENABLED",
            "local_launcher_provider_post_allowed": False,
            "provider_create_post_limit": 1,
            "timing_evidence_kind": "EMPIRICAL_NON_GUARANTEE",
            "scheduled_recovery_cadence_seconds": 60,
            "recovery_retry_maximum_attempts": 2,
            "recovery_event_maximum_age_seconds": 60,
            "provider_native_hard_ttl_available": False,
            "required_stop_lead_seconds": 300,
        },
    }
    digest = hashlib.sha256(DOMAIN + canonical(source)).hexdigest()
    result = {**source, "deployment_binding_sha256": digest}
    result["binding_document_sha256"] = hashlib.sha256(canonical(result)).hexdigest()
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    args = parser.parse_args(argv)
    try:
        raw = args.input.read_bytes()
        value = json.loads(raw.decode("utf-8"))
        result = create_binding(value)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, BindingError) as error:
        print(f"FAIL_CLOSED:{type(error).__name__}", file=sys.stderr)
        return 2
    sys.stdout.buffer.write(canonical(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
