"""Pure tests for the frozen condition-skill v9 resource plan and request.

No AWS, network, tensor, database, or provider work occurs. These tests lock
the plan bytes against the executable owner phase-approval record.
"""
from copy import deepcopy

import pytest

from aws import condition_skill_v9_resource_plan as plan


def valid_request():
    return {
        "schema": plan.REQUEST_SCHEMA,
        "job": "cas-meta2-20260907143000-abcdef01",
        "source_sha": "a" * 40,
        "archive_sha256": "b" * 64,
        "manifest_sha256": "c" * 64,
        "dataset_manifest_sha256": plan.DATASET_MANIFEST_SHA256,
        "seed": 7,
        "training": True,
        "native_execution": False,
        "automatic_retries": 0,
        "reservation_usd": "4.00",
        "launch_authorized": False,
        "new_reservation": False,
    }


def test_plan_matches_executable_approval_record():
    frozen = plan.scope()
    assert frozen["account"] == "807562639912"
    assert frozen["region"] == "us-west-2"
    assert frozen["ami"] == "ami-0fbbd0facbc9e3cff"
    assert frozen["instance_type"] == "g7.2xlarge"
    assert frozen["instance_count"] == 1
    assert frozen["gpu_name_contains"] == "RTX PRO 4500"
    assert frozen["t4_rejected"] is True
    assert frozen["visible_gpu_count"] == 1
    assert frozen["torch_version"] == "2.11.0+cu128"
    assert frozen["cuda_version"] == "12.8"
    assert frozen["on_demand_rate_ceiling_usd"] == "2.52"
    assert frozen["worker_seconds_max"] == 600
    assert frozen["trainer_output_bytes_max"] == 32 * 1024**2
    assert frozen["instance_seconds_max"] == 3600
    assert frozen["guest_shutdown_seconds"] == 3400
    assert frozen["cloud_schedule_seconds"] == 3480
    assert frozen["automatic_retries"] == 0
    assert frozen["reservation_usd"] == "4.00"
    assert frozen["seed"] == 7
    assert frozen["training"] is True
    assert frozen["native_execution"] is False
    assert frozen["max_native_calls"] == 0
    assert frozen["ebs"] == {"size_gib": 75, "iops": 3000, "throughput_mib_s": 125,
                             "encrypted": True, "delete_on_termination": True}
    assert frozen["network"] == {"inbound_rules": 0, "egress_tcp_443_only": True}
    assert frozen["budget"]["campaign_cap_usd"] == "400.00"
    assert frozen["budget"]["task_scope"] == "condition_skill_v9"
    assert frozen["budget"]["campaign_scope"] == "cas-meta2-composition-campaign"


def test_plan_scope_returns_fresh_and_unchanged():
    first = plan.scope()
    second = plan.scope()
    assert first == second == plan.RESOURCE_PLAN
    assert first is plan.RESOURCE_PLAN


def test_valid_request_is_accepted_and_returned():
    request = valid_request()
    assert plan.validate_launch_request(request) is request


@pytest.mark.parametrize("mutate,reason", [
    (lambda r: r.update(schema="cas-meta2-other/1"), "CONDITION_SKILL_V9_REQUEST_SCHEMA"),
    (lambda r: r.update(job="cas-meta2-1-abcdef01"), "CONDITION_SKILL_V9_REQUEST_JOB"),
    (lambda r: r.update(source_sha="zz"), "CONDITION_SKILL_V9_REQUEST_SOURCE_SHA"),
    (lambda r: r.update(archive_sha256="zz"), "CONDITION_SKILL_V9_REQUEST_HASH"),
    (lambda r: r.update(manifest_sha256="zz"), "CONDITION_SKILL_V9_REQUEST_HASH"),
    (lambda r: r.update(dataset_manifest_sha256="d" * 64),
     "CONDITION_SKILL_V9_REQUEST_DATASET_MANIFEST"),
    (lambda r: r.update(seed=8), "CONDITION_SKILL_V9_REQUEST_SEED"),
    (lambda r: r.update(training=False), "CONDITION_SKILL_V9_REQUEST_SCOPE"),
    (lambda r: r.update(native_execution=True), "CONDITION_SKILL_V9_REQUEST_SCOPE"),
    (lambda r: r.update(automatic_retries=1), "CONDITION_SKILL_V9_REQUEST_NO_RETRIES"),
    (lambda r: r.update(reservation_usd="5.00"), "CONDITION_SKILL_V9_REQUEST_RESERVATION"),
    (lambda r: r.update(launch_authorized=True), "CONDITION_SKILL_V9_REQUEST_INERT"),
    (lambda r: r.update(new_reservation=True), "CONDITION_SKILL_V9_REQUEST_INERT"),
    (lambda r: r.pop("job"), "CONDITION_SKILL_V9_REQUEST_FIELDS"),
    (lambda r: r.update(extra=1), "CONDITION_SKILL_V9_REQUEST_FIELDS"),
])
def test_request_rejects_every_mutation(mutate, reason):
    request = valid_request()
    mutate(request)
    with pytest.raises(ValueError, match=reason):
        plan.validate_launch_request(request)


def test_request_rejects_non_dict_and_empty():
    with pytest.raises(ValueError, match="CONDITION_SKILL_V9_REQUEST_SCHEMA"):
        plan.validate_launch_request([])
    with pytest.raises(ValueError, match="CONDITION_SKILL_V9_REQUEST_SCHEMA"):
        plan.validate_launch_request({})


def test_plan_module_imports_no_neural_or_provider_library():
    import sys
    assert not {"torch", "numpy", "boto3", "botocore", "sqlite3", "casformer", "cas_cjt"}.intersection(sys.modules)
