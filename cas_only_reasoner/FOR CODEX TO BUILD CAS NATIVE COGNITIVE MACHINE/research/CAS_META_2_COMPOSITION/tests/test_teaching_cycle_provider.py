"""Pure fake-provider checks. No AWS, canonical ledger or neural execution."""
from copy import deepcopy
from hashlib import sha256
import io
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from aws import teaching_cycle_plan as plan
from aws import teaching_cycle_provider as subject

JOB = "cas-meta2-teaching-20260908050000-abcd1234"
INSTANCE = "i-0123456789abcdef0"


class CloudError(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.response = {"Error": {"Code": code}}


class BoundedBody(io.BytesIO):
    def __init__(self, raw, maximum=None):
        super().__init__(raw)
        self.maximum, self.read_sizes = maximum, []

    def read(self, count=-1):
        self.read_sizes.append(count)
        assert count > 0
        if self.maximum:
            assert count <= self.maximum
        return super().read(count)


class Cloud:
    def __init__(self):
        self.calls, self.objects, self.roles, self.profiles = [], {}, {}, {}
        self.instance, self.group, self.schedule, self.bucket, self.lifecycle = None, None, None, False, None
        self.bad_schedule = False
        self.run_error = None
        self.bucket_error = None
        self.bodies = {}

    def client(self, service):
        owner = self
        class Client:
            def __getattr__(self, method):
                return lambda **args: owner.call(service, method, args)
        return Client()

    def call(self, service, method, args):
        self.calls.append((service, method, deepcopy(args)))
        if method == "get_caller_identity":
            return {"Account": "807562639912"}
        if method == "create_bucket":
            if self.bucket_error:
                raise self.bucket_error
            self.bucket = True
        elif method == "put_bucket_lifecycle_configuration":
            self.lifecycle = args["LifecycleConfiguration"]
        elif method == "get_bucket_lifecycle_configuration":
            return self.lifecycle
        elif method == "put_object":
            self.objects[args["Key"]] = args["Body"]
        elif method == "get_object":
            key = args["Key"]
            if key not in self.objects:
                raise CloudError("NoSuchKey")
            body = BoundedBody(self.objects[key], subject.CHUNK if key.endswith(".zip") else None)
            self.bodies[key] = body
            return {"Body": body, "ContentLength": len(self.objects[key])}
        elif method == "list_objects_v2":
            if not self.bucket:
                raise CloudError("NoSuchBucket")
            return {"Contents": [{"Key": key} for key in self.objects], "IsTruncated": False}
        elif method == "delete_objects":
            for item in args["Delete"]["Objects"]:
                self.objects.pop(item["Key"])
        elif method == "delete_bucket":
            assert not self.objects
            self.bucket = False
        elif method == "create_role":
            name = args["RoleName"]
            self.roles[name] = {"Arn": "arn:aws:iam::807562639912:role/" + name, "RoleName": name}
            return {"Role": self.roles[name]}
        elif method == "get_role":
            if args["RoleName"] not in self.roles:
                raise CloudError("NoSuchEntity")
            return {"Role": self.roles[args["RoleName"]]}
        elif method == "delete_role":
            self.roles.pop(args["RoleName"])
        elif method == "create_instance_profile":
            name = args["InstanceProfileName"]
            self.profiles[name] = {"Arn": "arn:aws:iam::807562639912:instance-profile/" + name, "Roles": []}
            return {"InstanceProfile": self.profiles[name]}
        elif method == "get_instance_profile":
            if args["InstanceProfileName"] not in self.profiles:
                raise CloudError("NoSuchEntity")
            return {"InstanceProfile": self.profiles[args["InstanceProfileName"]]}
        elif method == "add_role_to_instance_profile":
            self.profiles[args["InstanceProfileName"]]["Roles"] = [self.roles[args["RoleName"]]]
        elif method == "remove_role_from_instance_profile":
            self.profiles[args["InstanceProfileName"]]["Roles"] = []
        elif method == "delete_instance_profile":
            self.profiles.pop(args["InstanceProfileName"])
        elif method == "describe_vpcs":
            return {"Vpcs": [{"VpcId": "vpc-1"}]}
        elif method == "describe_subnets":
            return {"Subnets": [{"SubnetId": "subnet-1"}]}
        elif method == "create_security_group":
            self.group = {"GroupName": JOB, "GroupId": "sg-1", "Tags": [{"Key": "cas_meta_job", "Value": JOB}]}
            return self.group
        elif method == "describe_security_groups":
            return {"SecurityGroups": [self.group] if self.group else []}
        elif method == "delete_security_group":
            self.group = None
        elif method == "run_instances":
            if self.run_error:
                raise self.run_error
            self.instance = {"InstanceId": INSTANCE, "ClientToken": JOB,
                "Tags": [{"Key": "cas_meta_job", "Value": JOB}], "State": {"Name": "running"}}
            return {"Instances": [self.instance]}
        elif method == "describe_instances":
            return {"Reservations": [{"Instances": [self.instance]}] if self.instance else []}
        elif method == "terminate_instances":
            self.instance["State"]["Name"] = "terminated"
        elif method == "describe_volumes":
            return {"Volumes": []}
        elif method == "create_schedule":
            self.schedule = {**args, "State": "DISABLED" if self.bad_schedule else "ENABLED",
                "Arn": "arn:aws:scheduler:us-west-2:807562639912:schedule/default/" + JOB}
        elif method == "get_schedule":
            if self.schedule is None:
                raise CloudError("ResourceNotFoundException")
            return self.schedule
        elif method == "delete_schedule":
            self.schedule = None
        elif method not in ("put_bucket_tagging", "put_public_access_block", "put_bucket_encryption",
                            "put_role_policy", "delete_role_policy", "revoke_security_group_egress", "authorize_security_group_egress"):
            raise AssertionError((service, method))
        return {}


@pytest.fixture
def setup(tmp_path, monkeypatch):
    cloud, now = Cloud(), [1000.0]
    driver, pricing, ledger = (tmp_path / name for name in ("remote.py", "pricing.json", "ledger.json"))
    driver.write_bytes(b"# fake standalone driver\n")
    pricing.write_bytes(b"{}\n")
    ledger.write_bytes(b"{}\n")
    dependency_map = {"test-only-source": "1" * 64}
    monkeypatch.setattr(subject, "source_dependencies", lambda: dependency_map)
    # Only the private fake ledger above is used by the reused S3-copy helper.
    monkeypatch.setattr(subject.generic.budget, "validate_state", lambda value: value)
    pins = {**{key: "1" * 64 for key in plan.BINDING_FIELDS}, **plan.FROZEN_BINDINGS,
        "provider_source_sha256": sha256(Path(subject.__file__).read_bytes()).hexdigest(),
        "provider_dependencies_sha256": plan.canonical_sha256(dependency_map),
        "guest_driver_sha256": sha256(driver.read_bytes()).hexdigest(),
        "bootstrap_sha256": sha256(Path(subject.bootstrap.__file__).read_bytes()).hexdigest(),
        "pricing_receipt_sha256": sha256(pricing.read_bytes()).hexdigest()}
    request = plan.build_request(job=JOB, bindings=pins, ledger={"revision": 17, "sha256": "2" * 64,
        "cap_usd": "400.00", "reserved_usd": "102.00", "unreserved_usd": "298.00"})
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    public = tmp_path / "public.json"
    public.write_bytes(b'{"test_fresh":[]}\n')
    context = {"request": request, "job": JOB, "run_id": JOB, "bindings": pins,
        "resource_plan": request["resource_plan"], "request_sha256": plan.canonical_sha256(request),
        "receipt_dir": str(evidence), "public_sets_path": str(public), "ledger_path": str(ledger),
        "started_unix": 1000.0, "deadline_unix": 8200.0}
    reservations = []
    def reserve(*args):
        reservations.append(args)
        return {"reservation": {"job": JOB}, "simulated": True}
    def observer(clients):
        account = clients["sts"].get_caller_identity()["Account"]
        return {"read_only": True, "account_id": account, "region": "us-west-2", "instance_type": "g7.2xlarge",
            "conflicting_resources": [], "cost_worksheet": {"rates_usd": {"compute": "2.52"}}}
    provider = subject.TeachingCycleProvider(clients={name: cloud.client(name) for name in ("sts", "s3", "ec2", "iam", "scheduler")},
        source_archive=subject.ROOT / "records/teaching_cycle_001/bundle_002/training.zip", guest_driver=driver,
        pricing_receipt_path=pricing, ledger_path=ledger, clock=lambda: now[0],
        sleeper=lambda seconds: now.__setitem__(0, now[0] + seconds), budget_module=SimpleNamespace(reserve_budget=reserve), observer=observer)
    return provider, context, cloud, reservations, now


def start(setup):
    provider, context, cloud, reservations, now = setup
    provider.preflight(context)
    provider.reserve(context)
    context["launch"] = provider.launch(context)
    return setup


def test_source_pin_refusal_precedes_every_cloud_call(setup):
    provider, context, cloud, _, _ = setup
    context["bindings"]["provider_source_sha256"] = "f" * 64
    context["request"]["bindings"]["provider_source_sha256"] = "f" * 64
    context["request_sha256"] = plan.canonical_sha256(context["request"])
    with pytest.raises(ValueError, match="PROVIDER_SOURCE_PIN"):
        provider.preflight(context)
    assert cloud.calls == []


def test_exact_one_reservation_and_instance_schedule_before_release(setup):
    provider, context, cloud, reservations, _ = start(setup)
    assert len(reservations) == 1
    assert reservations[0][0:4] == (JOB, plan.FROZEN_BINDINGS["source_commit"], plan.FROZEN_BINDINGS["archive_sha256"], "8.00")
    calls = [(method, args) for _, method, args in cloud.calls]
    launched = [args for method, args in calls if method == "run_instances"]
    assert len(launched) == 1
    assert launched[0]["ClientToken"] == JOB
    assert launched[0]["IamInstanceProfile"] == {"Arn": "arn:aws:iam::807562639912:instance-profile/" + JOB + "-worker"}
    assert launched[0]["InstanceType"] == "g7.2xlarge"
    assert launched[0]["BlockDeviceMappings"][0]["Ebs"]["VolumeSize"] == 75
    assert calls.index(next(row for row in calls if row[0] == "get_schedule")) < calls.index(next(row for row in calls if row[0] == "put_object" and row[1]["Key"] == "input/permit.json"))
    config = json.loads(cloud.objects["input/config.json"])
    assert "instance_id" not in config and config["prefix"] == ""
    assert config["bindings"] == context["bindings"] and config["deadline_unix"] == 8200
    permit = json.loads(cloud.objects["input/permit.json"])
    assert permit["instance_id"] == INSTANCE and permit["config_sha256"] == sha256(cloud.objects["input/config.json"]).hexdigest()
    assert "input/public.json" not in cloud.objects
    policies = [json.loads(args["PolicyDocument"]) for method, args in calls
                if method == "put_role_policy" and args["RoleName"] == JOB + "-worker"]
    list_grant = [row for row in policies[0]["Statement"] if row["Action"] == ["s3:ListBucket"]]
    assert list_grant == [{"Effect": "Allow", "Action": ["s3:ListBucket"],
                           "Resource": ["arn:aws:s3:::" + JOB + "-807562639912"]}]
    with pytest.raises(ValueError, match="ONE_RESERVATION"):
        provider.reserve(context)
    with pytest.raises(ValueError, match="ONE_RESERVED_LAUNCH"):
        provider.launch(context)


def test_bad_schedule_cannot_release_worker(setup):
    provider, context, cloud, _, _ = setup
    cloud.bad_schedule = True
    provider.preflight(context)
    provider.reserve(context)
    with pytest.raises(ValueError, match="SCHEDULE_READBACK"):
        provider.launch(context)
    assert "input/permit.json" not in cloud.objects
    assert provider.cleanup(context, True)["instance_state"] == "TERMINATED"


def test_rejected_instance_is_not_retried_or_fabricated_terminated(setup):
    provider, context, cloud, _, _ = setup
    cloud.run_error = CloudError("InvalidParameterValue")
    provider.preflight(context)
    provider.reserve(context)
    with pytest.raises(CloudError):
        provider.launch(context)
    result = provider.cleanup(context, True)
    assert result["compute_closed"] and result["instance_state"] == "REJECTED_NO_INSTANCE_OBSERVED"
    assert result["instance_terminated"] is False
    assert sum(method == "run_instances" for _, method, _ in cloud.calls) == 1


def test_no_effect_cleanup_never_touches_same_named_existing_resources(setup):
    provider, context, cloud, _, _ = setup
    cloud.roles[JOB + "-worker"] = {"existing": True}
    cloud.schedule = {"existing": True}
    result = provider.cleanup(context, True)
    assert result["cleanup_scope"] == "CURRENT_ATTEMPT_ONLY_NO_EFFECTS"
    assert cloud.calls == [] and cloud.schedule == {"existing": True}
    assert result["cloud_copy_retained"] is False


def test_duplicate_budget_refusal_does_not_authorize_cleanup_of_other_attempt(setup):
    provider, context, cloud, _, _ = setup
    provider.preflight(context)
    provider.budget.reserve_budget = lambda *args: (_ for _ in ()).throw(ValueError("DUPLICATE_JOB"))
    with pytest.raises(ValueError, match="DUPLICATE_JOB"):
        provider.reserve(context)
    before = list(cloud.calls)
    provider.cleanup(context, True)
    assert cloud.calls == before


def test_cloud_reservation_failure_cannot_reenter_launch(setup, monkeypatch):
    provider, context, cloud, _, _ = setup
    provider.preflight(context)
    monkeypatch.setattr(provider, "_record_aws_side_reservation", lambda _: {"status": "FAILED"})
    assert provider.reserve(context)["aws_side_reservation"]["status"] == "FAILED"
    with pytest.raises(ValueError, match="ONE_RESERVED_LAUNCH"):
        provider.launch(context)
    assert not any(method == "run_instances" for _, method, _ in cloud.calls)


def test_training_and_partial_receipts_preserve_raw_bytes(setup):
    provider, context, cloud, _, _ = start(setup)
    ready, campaign = b'{ "ready": true }\n', b'{\n "campaign": true\n}\n'
    cloud.objects.update({"results/train_ready.json": ready, "results/train/campaign_summary.json": campaign})
    result = provider.wait_training(context, 20)
    assert result["campaign"]["raw_utf8"].encode() == campaign
    assert result["ready"]["sha256"] == sha256(ready).hexdigest()
    del cloud.objects["results/train_ready.json"]
    cloud.objects["results/complete.json"] = b'{"status":"TEACHING_INCOMPLETE"}\n'
    assert set(provider.wait_training(context, 20)) == {"complete"}


def test_streaming_collection_preserves_marker_and_retains_results(setup, tmp_path):
    provider, context, cloud, _, _ = start(setup)
    raw = b"x" * (subject.CHUNK * 2 + 7)
    artifact = {"key": "results/artifacts.zip", "sha256": sha256(raw).hexdigest(), "bytes": len(raw)}
    marker = b'{ "status": "TEACHING_INCOMPLETE", "artifact": ' + json.dumps(artifact).encode() + b'}\n'
    cloud.objects.update({"results/artifacts.zip": raw, "results/complete.json": marker})
    destination = tmp_path / "collected"
    destination.mkdir()
    result = provider.collect(context, destination, 60)
    assert Path(result["archive"]["path"]).read_bytes() == raw
    assert (destination / "complete.json").read_bytes() == marker
    assert provider.result_downloaded_bytes == len(raw) + len(marker)
    assert max(cloud.bodies["results/artifacts.zip"].read_sizes) <= subject.CHUNK
    cleanup = provider.cleanup(context, False)
    assert cleanup["complete"] and cleanup["compute_closed"] and cleanup["schedules_removed"]
    assert cleanup["cloud_copy_retained"] is True and cleanup["cloud_copy_state"] == "OBSERVED_RETAINED"
    assert "results/artifacts.zip" in cloud.objects and "input/source.zip" not in cloud.objects
    assert provider._durable_results is False


def test_wrong_artifact_digest_keeps_cloud_copy_and_never_retries(setup, tmp_path):
    provider, context, cloud, _, _ = start(setup)
    cloud.objects["results/artifacts.zip"] = b"wrong"
    cloud.objects["results/complete.json"] = subject.canonical({"artifact": {"key": "results/artifacts.zip", "bytes": 5, "sha256": "0" * 64}})
    destination = tmp_path / "collected"
    destination.mkdir()
    with pytest.raises(ValueError, match="ARTIFACT_LOCAL_IDENTITY"):
        provider.collect(context, destination, 60)
    with pytest.raises(ValueError, match="ONE_COLLECTION"):
        provider.collect(context, destination, 60)
    assert provider.cleanup(context, True)["cloud_copy_retained"] is True


def test_failed_polls_count_and_shared_parent_limit_never_resets(setup):
    provider, context, cloud, _, now = start(setup)
    initial = provider.s3_attempts
    with pytest.raises(TimeoutError):
        provider.wait_training(context, 21)
    assert provider.s3_attempts == initial + 5  # Four lifecycle reads and one optional first-update read.
    provider.s3_attempts = 991
    assert provider._get("results/missing.json") is None
    with pytest.raises(ValueError, match="PARENT_S3_ATTEMPT_LIMIT"):
        provider._get("results/missing.json")
    now[0] = context["deadline_unix"] + 1
    with pytest.raises(ValueError, match="SHARED_DEADLINE"):
        provider._get("results/missing.json")


def test_changed_lifetime_is_rejected_and_legacy_paths_disabled(setup):
    provider, context, _, _, _ = setup
    provider.preflight(context)
    context["started_unix"] += 1
    context["deadline_unix"] += 1
    with pytest.raises(ValueError, match="CONTEXT_CHANGED"):
        provider.reserve(context)
    for method in (provider._render_remote, provider._user_data, provider.wait, provider._validate_permit):
        with pytest.raises(ValueError, match="LEGACY_LIFECYCLE_DISABLED"):
            method()


def test_plan_allocates_every_s3_attempt_including_bootstrap():
    caps = plan.resource_plan()["worksheet_limits"]
    assert caps["parent_s3_api_attempts_max"] + caps["guest_s3_api_attempts_max"] + caps["bootstrap_s3_api_attempts_max"] == caps["s3_api_attempts_max"] == 2048


def test_terminal_instance_stops_wait_and_preserves_bootstrap_failure(setup):
    provider, context, cloud, _, now = start(setup)
    cloud.instance["State"]["Name"] = "terminated"
    cloud.objects["results/bootstrap_failure.log"] = b"simulated setup failure\n"
    with pytest.raises(RuntimeError, match="GUEST_EXIT_WITHOUT_COMPLETE:terminated"):
        provider.wait_training(context, 6300)
    assert now[0] == 1000.0
    assert (Path(context["receipt_dir"]) / "bootstrap_failure.log").read_bytes() == b"simulated setup failure\n"
    assert "results/bootstrap_failure.log" in cloud.objects


def test_wait_refuses_an_unrelated_instance_identity(setup):
    provider, context, cloud, _, _ = start(setup)
    cloud.instance["ClientToken"] = "another-job"
    with pytest.raises(ValueError, match="WAIT_INSTANCE_IDENTITY"):
        provider.wait_training(context, 20)


def test_public_upload_follows_parent_verified_training_and_is_one_shot(setup):
    provider, context, cloud, _, _ = setup
    public = Path(context["public_sets_path"]).read_bytes()
    for pins in (context["bindings"], context["request"]["bindings"]):
        pins["public_sets_sha256"] = sha256(public).hexdigest()
    context["request_sha256"] = plan.canonical_sha256(context["request"])
    start(setup)
    with pytest.raises(ValueError, match="ONE_SEALED_PUBLIC_RELEASE"):
        provider.release_public(context, {})
    assert "input/public.json" not in cloud.objects
    context.update(training_ready_sha256="a" * 64, campaign_summary_sha256="b" * 64)
    release = {"job": JOB, "training_ready_sha256": "a" * 64, "campaign_summary_sha256": "b" * 64}
    result = provider.release_public(context, release)
    assert result["public_sha256"] == sha256(public).hexdigest()
    assert cloud.objects["input/public.json"] == public
    with pytest.raises(ValueError, match="ONE_SEALED_PUBLIC_RELEASE"):
        provider.release_public(context, release)


def test_provider_config_and_permit_pass_standalone_guest_contract(setup):
    from aws import teaching_cycle_remote as guest
    provider, _, cloud, _, _ = start(setup)
    raw = cloud.objects["input/config.json"]
    config, permit = json.loads(raw), json.loads(cloud.objects["input/permit.json"])
    assert guest.validate_config(config, sha256(raw).hexdigest(), permit, driver_path=provider.guest_driver_path) == config


def test_source_map_includes_every_declared_current_file_without_importing_them():
    result = subject.source_dependencies()
    assert set(result) == set(subject.DEPENDENCIES)
    assert result["aws/teaching_cycle_provider.py"] == sha256(Path(subject.__file__).read_bytes()).hexdigest()
    assert {"aws/condition_skill_v9_package.py", "cas_meta2/features_v2.py",
            "tools/evaluate_teaching_launch.py", "aws/teaching_cycle_remote.py"}.issubset(result)


def test_json_downloads_share_the_archive_byte_allocation(setup):
    provider, context, cloud, _, _ = start(setup)
    cloud.objects["results/small.json"] = b"{}"
    provider.result_downloaded_bytes = 2684354559
    with pytest.raises(ValueError, match="SHARED_RESULT_DOWNLOAD_BOUND"):
        provider._get("results/small.json")
    assert provider.result_downloaded_bytes == 2684354559
    assert cloud.bodies["results/small.json"].closed


def test_existing_bucket_collision_never_becomes_cleanup_ownership(setup):
    provider, context, cloud, _, _ = setup
    cloud.bucket = True
    cloud.objects["input/source.zip"] = b"pre-existing other attempt"
    cloud.bucket_error = CloudError("BucketAlreadyOwnedByYou")
    provider.preflight(context)
    assert provider.reserve(context)["aws_side_reservation"]["status"] == "FAILED"
    before = list(cloud.calls)
    result = provider.cleanup(context, True)
    assert cloud.calls == before and cloud.objects["input/source.zip"] == b"pre-existing other attempt"
    assert result["cleanup_scope"] == "CURRENT_ATTEMPT_ONLY_NO_EFFECTS"


def first_update(context):
    event_raw = subject.canonical({"sequence": 1, "intent_sha256": "a" * 64, "receipt": {
        "schema": "cas-teaching-binding-cuda/1", "run_id": JOB + ".aligned.cas", "execution_mode": "cuda",
        "optimizer_steps": 1, "cumulative_optimizer_steps": 1, "accepted_weights_updated": False}})
    event = {"key": "train/campaign/cas.aligned/events/step-00000001.result.json", "raw_utf8": event_raw.decode(),
             "sha256": sha256(event_raw).hexdigest(), "bytes": len(event_raw)}
    return {"schema": "cas-teaching-first-update/1", "job": JOB, "run_id": JOB,
        "source_sha256": context["bindings"]["source_sha256"], "manifest_sha256": context["bindings"]["manifest_sha256"],
        "material_sha256": context["bindings"]["material_receipt_sha256"], "request_sha256": context["request_sha256"],
        "arm": "cas.aligned", "event": event, "boundary": "WORKER_REPORTED_NOT_INDEPENDENT_LEARNING_PROOF"}


def test_first_update_is_saved_exactly_and_printed_once_without_releasing_public(setup, capsys):
    provider, context, cloud, _, now = start(setup)
    marker = first_update(context)
    raw = json.dumps(marker, indent=2).encode() + b"\n"
    cloud.objects["results/first_update.json"] = raw
    initial = provider.s3_attempts
    provider._observe_first_update()
    line = json.loads(capsys.readouterr().out)
    assert line["status"] == "WORKER_REPORTED_FIRST_CUDA_UPDATE"
    assert line["event_sha256"] == marker["event"]["sha256"] and line["independent_learning_proof"] is False
    assert (Path(context["receipt_dir"]) / "first_update.json").read_bytes() == raw
    now[0] += 120
    provider._observe_first_update()
    assert capsys.readouterr().out == "" and provider.s3_attempts == initial + 1
    assert provider.result_downloaded_bytes == len(raw)
    assert not provider._public_released and "input/public.json" not in cloud.objects


def test_first_update_poll_interval_is_shared_and_at_least_sixty_seconds(setup):
    provider, _, cloud, _, now = start(setup)
    provider._observe_first_update()
    now[0] += 59
    provider._observe_first_update()
    reads = lambda: [args for _, method, args in cloud.calls if method == "get_object" and args["Key"] == "results/first_update.json"]
    assert len(reads()) == 1
    now[0] += 1
    provider._observe_first_update()
    assert len(reads()) == 2


@pytest.mark.parametrize("fault", ["source", "request", "event_hash", "event_path", "cpu", "run_id", "zero_steps", "bool_steps", "accepted"])
def test_invalid_first_update_does_not_claim_training_or_change_final_gates(setup, capsys, fault):
    provider, context, cloud, _, _ = start(setup)
    marker = first_update(context)
    if fault in ("source", "request"):
        marker["source_sha256" if fault == "source" else "request_sha256"] = "f" * 64
    elif fault == "event_hash":
        marker["event"]["sha256"] = "f" * 64
    elif fault == "event_path":
        marker["event"]["key"] = "train/other/events/step-00000001.result.json"
    else:
        payload = json.loads(marker["event"]["raw_utf8"])
        changed = {"cpu": ("execution_mode", "cpu"), "run_id": ("run_id", JOB + ".ordinary.cas"),
            "zero_steps": ("cumulative_optimizer_steps", 0), "bool_steps": ("optimizer_steps", True),
            "accepted": ("accepted_weights_updated", True)}[fault]
        payload["receipt"][changed[0]] = changed[1]
        raw = subject.canonical(payload)
        marker["event"].update(raw_utf8=raw.decode(), sha256=sha256(raw).hexdigest(), bytes=len(raw))
    cloud.objects["results/first_update.json"] = subject.canonical(marker)
    provider._observe_first_update()
    assert capsys.readouterr().out == ""
    assert not provider._public_released and provider._first_update_finished
    # The optional rejected marker is recorded, but does not stop collection of
    # the independently validated training seal through the ordinary lifecycle.
    cloud.objects["results/train_ready.json"] = b'{"ready":true}\n'
    cloud.objects["results/train/campaign_summary.json"] = b'{"campaign":true}\n'
    assert set(provider.wait_training(context, 20)) == {"ready", "campaign"}


def test_live_ten_decimal_quote_survives_actual_parent_gate_without_changing_raw_data(setup):
    from aws import teaching_cycle_launch as parent
    provider, context, _, reservations, _ = setup
    facts = {"read_only": True, "account_id": "807562639912", "region": "us-west-2", "instance_type": "g7.2xlarge",
        "conflicting_resources": [], "cost_worksheet": {"rates_usd": {"compute": "2.5200000000"},
        "estimated_bound_usd": "6.417097142857142857142857143"}, "raw_prices": {"compute": "untouched raw AWS response"}}
    original = deepcopy(facts)
    provider.observer = lambda _: facts
    result = provider.preflight(context)
    assert result["rate_hourly_usd"] == "2.52" and result["rate_hourly_usd_raw"] == "2.5200000000"
    assert result["cost_worksheet"] == original["cost_worksheet"] and result["raw_prices"] == original["raw_prices"]
    assert facts == original
    parent._preflight(result, context)  # The unchanged strict budget.amount path.
    assert reservations == []


@pytest.mark.parametrize("raw,expected", [("2.5200000000", "2.52"), ("2.52000000", "2.52"),
    ("2.5000000000", "2.5"), ("2.0000000000", "2"), ("2", "2"), ("2.5199999900", "2.51999999")])
def test_hourly_rate_removes_only_insignificant_trailing_zeroes(raw, expected):
    from decimal import Decimal
    assert subject.normalize_hourly_rate(raw, "2.52") == expected
    assert Decimal(raw) == Decimal(expected)


@pytest.mark.parametrize("raw,error", [("2.5200000001", "HOURLY_RATE_ABOVE_CEILING"),
    ("2.5199999999", "HOURLY_RATE_EXACT_PRECISION_UNSUPPORTED"),
    ("2.52000000000000000000000000000000000000000001", "HOURLY_RATE_ABOVE_CEILING"),
    ("0.0000000000", "HOURLY_RATE_INVALID"), ("NaN", "HOURLY_RATE_FORMAT"),
    ("Infinity", "HOURLY_RATE_FORMAT"), ("-2.52", "HOURLY_RATE_FORMAT"), (2.52, "HOURLY_RATE_FORMAT")])
def test_quote_normalization_never_rounds_or_relaxes_the_ceiling(raw, error):
    with pytest.raises(ValueError, match=error):
        subject.normalize_hourly_rate(raw, "2.52")
