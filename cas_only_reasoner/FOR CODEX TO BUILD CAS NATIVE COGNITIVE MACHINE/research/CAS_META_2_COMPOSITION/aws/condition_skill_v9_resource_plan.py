"""Frozen resource plan and launch-request contract for condition_skill_v9.

Pure module: no AWS, boto3, tensor, database, or provider imports. Every value
matches the executable owner phase-approval record and the preregistered
protocol. Building or validating a plan never authorizes or starts a run.
"""
from __future__ import annotations

import re

SCHEMA = "cas-meta2-condition-skill-v9-resource-plan/9"
REQUEST_SCHEMA = "cas-meta2-condition-skill-v9-launch-request/9"
EXPERIMENT = {"profile": "condition_skill_v9", "entrypoint": "cas_meta2.condition_skill_v9.train"}
DATASET_MANIFEST_SHA256 = "6b19020c4653aa535919f4af092020ad3650855bf7f58c6b550169af3d5468dd"
JOB_PATTERN = r"cas-meta2-\d{14}-[a-f0-9]{8}"

RESOURCE_PLAN = {
    "schema": SCHEMA,
    "experiment": EXPERIMENT,
    "account": "807562639912",
    "region": "us-west-2",
    "ami": "ami-0fbbd0facbc9e3cff",
    "instance_type": "g7.2xlarge",
    "instance_count": 1,
    "gpu_name_contains": "RTX PRO 4500",
    "t4_rejected": True,
    "visible_gpu_count": 1,
    "torch_version": "2.11.0+cu128",
    "cuda_version": "12.8",
    "python_versions": ["3.11", "3.12"],
    "on_demand_rate_ceiling_usd": "2.52",
    "worker_seconds_max": 600,
    "trainer_output_bytes_max": 32 * 1024**2,
    "instance_seconds_max": 3600,
    "guest_shutdown_seconds": 3400,
    "cloud_schedule_seconds": 3480,
    "automatic_retries": 0,
    "reservation_usd": "4.00",
    "seed": 7,
    "training": True,
    "native_execution": False,
    "max_native_calls": 0,
    "dataset_manifest_sha256": DATASET_MANIFEST_SHA256,
    "ebs": {"size_gib": 75, "iops": 3000, "throughput_mib_s": 125,
            "encrypted": True, "delete_on_termination": True},
    "network": {"inbound_rules": 0, "egress_tcp_443_only": True},
    "budget": {
        "campaign_cap_usd": "400.00",
        "campaign_ledger_revision": 16,
        "campaign_reserved_usd": "98.00",
        "campaign_unreserved_usd": "302.00",
        "task_scope": "condition_skill_v9",
        "campaign_scope": "cas-meta2-composition-campaign",
    },
    "evidence_boundary": ("The learner reads only train/validation before sealing; private "
                          "targets are opened only after the blind prediction receipt is hash-bound."),
}


def require(condition, code):
    if not condition:
        raise ValueError(code)


def scope():
    """Return the frozen plan. Plan output is not an authorization."""
    return RESOURCE_PLAN


def validate_launch_request(request):
    """Strict request shape; the request itself must remain inert.

    A valid request names the job, exact source/archive identities, and the
    frozen run scope, and keeps launch_authorized and new_reservation false.
    Separate standing authority carries the actual authorization.
    """
    require(type(request) is dict and request.get("schema") == REQUEST_SCHEMA,
            "CONDITION_SKILL_V9_REQUEST_SCHEMA")
    require(set(request) == {
        "schema", "job", "source_sha", "archive_sha256", "manifest_sha256",
        "dataset_manifest_sha256", "seed", "training", "native_execution",
        "automatic_retries", "reservation_usd", "launch_authorized",
        "new_reservation"}, "CONDITION_SKILL_V9_REQUEST_FIELDS")
    require(type(request["job"]) is str
            and re.fullmatch(JOB_PATTERN, request["job"]) is not None,
            "CONDITION_SKILL_V9_REQUEST_JOB")
    require(type(request["source_sha"]) is str
            and re.fullmatch(r"[a-f0-9]{40}", request["source_sha"]) is not None,
            "CONDITION_SKILL_V9_REQUEST_SOURCE_SHA")
    for key in ("archive_sha256", "manifest_sha256", "dataset_manifest_sha256"):
        require(type(request[key]) is str
                and re.fullmatch(r"[a-f0-9]{64}", request[key]) is not None,
                "CONDITION_SKILL_V9_REQUEST_HASH:" + key)
    require(request["dataset_manifest_sha256"] == DATASET_MANIFEST_SHA256,
            "CONDITION_SKILL_V9_REQUEST_DATASET_MANIFEST")
    require(request["seed"] == RESOURCE_PLAN["seed"], "CONDITION_SKILL_V9_REQUEST_SEED")
    require(request["training"] is True and request["native_execution"] is False,
            "CONDITION_SKILL_V9_REQUEST_SCOPE")
    require(request["automatic_retries"] == 0, "CONDITION_SKILL_V9_REQUEST_NO_RETRIES")
    require(request["reservation_usd"] == RESOURCE_PLAN["reservation_usd"],
            "CONDITION_SKILL_V9_REQUEST_RESERVATION")
    require(request["launch_authorized"] is False and request["new_reservation"] is False,
            "CONDITION_SKILL_V9_REQUEST_INERT")
    return request
