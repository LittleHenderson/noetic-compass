"""Plan by default. Explicit capped execution creates only a new CAS-META-2 job.

Only the explicit contrast_recovery_v6 experiment is allowed.
No torch import or neural work occurs on the client. This launcher has not been
cloud-executed merely because its pure contract tests pass.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import inspect
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import stat
import subprocess
import sys
import time
import tempfile
import uuid
import zipfile
import importlib.util


def verify_cli_source_before_helper_import(source_sha):
    """For paid CLI use, check executable dependencies before their imports."""
    if type(source_sha) is not str or not re.fullmatch(r"[a-f0-9]{40}", source_sha):
        raise ValueError("EXACT_SOURCE_SHA_REQUIRED_BEFORE_HELPER_IMPORT")
    root = Path(__file__).resolve().parents[1]
    repo = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=root, text=True).strip()).resolve()
    resolved = subprocess.check_output(["git", "rev-parse", source_sha + "^{commit}"], cwd=repo, text=True).strip()
    if resolved != source_sha:
        raise ValueError("EXACT_SOURCE_COMMIT_REQUIRED_BEFORE_HELPER_IMPORT")
    checked = {}
    for relative in ("aws/launch_recovery_v6.py", "aws/budget.py", "tools/experiment_profiles_recovery_v6.py",
                     "tools/build_launch_bundle_recovery_v6.py", "aws/launch_recovery_v6_plan.json", "requirements-gpu.txt"):
        path = root / relative
        if not path.is_file() or any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
                                    for p in (path, *path.parents)):
            raise ValueError("PREIMPORT_SOURCE_LINK_OR_FILE_INVALID:" + relative)
        raw = subprocess.check_output(["git", "show", source_sha + ":" + path.relative_to(repo).as_posix()], cwd=repo)
        if path.read_bytes() != raw:
            raise ValueError("PREIMPORT_EXECUTABLE_SOURCE_MISMATCH:" + relative)
        checked[relative] = hashlib.sha256(raw).hexdigest()
    return checked


if __name__ == "__main__":
    _early_parser = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    _early_parser.add_argument("--execute", action="store_true")
    _early_parser.add_argument("--source-sha")
    _early_args, _ = _early_parser.parse_known_args()
    if _early_args.execute:
        try:
            verify_cli_source_before_helper_import(_early_args.source_sha)
        except (ValueError, OSError, subprocess.SubprocessError) as _early_error:
            print(json.dumps({"status": "LAUNCH_REFUSED", "reason": str(_early_error)}))
            raise SystemExit(2)

_BUDGET_PATH = Path(__file__).with_name("budget.py")
_BUDGET_SHA256 = "cb3c78a0dfed166857109710cb8eac79dd337d837c839d558565982084b5a22f"
if (not _BUDGET_PATH.is_file() or _BUDGET_PATH.is_symlink()
        or hashlib.sha256(_BUDGET_PATH.read_bytes()).hexdigest() != _BUDGET_SHA256):
    raise ValueError("PINNED_SHARED_BUDGET_CHANGED_BEFORE_IMPORT")
_BUDGET_SPEC = importlib.util.spec_from_file_location("cas_meta2_campaign_budget", Path(__file__).with_name("budget.py"))
budget = importlib.util.module_from_spec(_BUDGET_SPEC)
_BUDGET_SPEC.loader.exec_module(budget)

PILOT_ROOT = Path(__file__).resolve().parents[1]
_PROFILE_SPEC = importlib.util.spec_from_file_location("cas_meta2_launch_profiles_contrast_v6", PILOT_ROOT / "tools/experiment_profiles_recovery_v6.py")
_PROFILE_IMPORT_SHA256 = hashlib.sha256((PILOT_ROOT / "tools/experiment_profiles_recovery_v6.py").read_bytes()).hexdigest()
profiles = importlib.util.module_from_spec(_PROFILE_SPEC)
_PROFILE_SPEC.loader.exec_module(profiles)
PLAN_FILE = Path(__file__).with_name("launch_recovery_v6_plan.json")
EXECUTION_LOCK_FILE = PILOT_ROOT / "records/aws_campaign_execution_v3.lock"
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
SHA1 = re.compile(r"[0-9a-f]{40}\Z")
ACCEPTED_BASELINE = "0917267b1354e5d036263eaa6ba9a7197eafb776"
ACCEPTED_BASELINE_MANIFEST_SHA256 = "476a8bbdc7a4b07a406e46b246ed417ea1d902e04cfb852ca710de09dcbc59f0"


class LaunchRefused(ValueError):
    pass


def experiment_record(manifest: dict, read_member=None):
    try:
        return profiles.validate_manifest(manifest, read_member)
    except (ValueError, UnicodeError) as exc:
        raise LaunchRefused(str(exc)) from exc


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_relative(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise LaunchRefused("UNSAFE_ARCHIVE_PATH")
    p = PurePosixPath(value)
    if p.is_absolute() or any(x in (".", "..", "") for x in value.split("/")):
        raise LaunchRefused("UNSAFE_ARCHIVE_PATH")
    return str(p)


def validate_archive(path: Path, expected_sha: str, source_sha: str, plan: dict) -> dict:
    if not SHA256.fullmatch(expected_sha) or not SHA1.fullmatch(source_sha):
        raise LaunchRefused("FULL_SHA_REQUIRED")
    if digest(path) != expected_sha:
        raise LaunchRefused("ARCHIVE_SHA_MISMATCH")
    with zipfile.ZipFile(path) as archive:
        names, total = set(), 0
        for info in archive.infolist():
            name = safe_relative(info.filename.rstrip("/"))
            if name in names or stat.S_ISLNK(info.external_attr >> 16):
                raise LaunchRefused("DUPLICATE_OR_SYMLINK_ARCHIVE_ENTRY")
            names.add(name)
            total += info.file_size
            if total > plan["archive_expanded_bytes_max"]:
                raise LaunchRefused("ARCHIVE_SIZE_CEILING")
        manifest = json.loads(archive.read("launch_manifest.json"))
        if manifest.get("schema_version") != 2 or manifest.get("source_sha") != source_sha:
            raise LaunchRefused("SOURCE_IDENTITY_MISMATCH")
        if manifest.get("baseline_sha") != ACCEPTED_BASELINE:
            raise LaunchRefused("ACCEPTED_BASELINE_REQUIRED")
        for key in ("pilot_dir", "meta1_dir", "meta_runtime_dir", "dependency_lock"):
            safe_relative(manifest[key])
        if manifest["pilot_dir"] != "research/CAS_META_2_COMPOSITION" or manifest["meta1_dir"] != "research/CAS_META_1_LEARNED_SELECTION" or manifest["meta_runtime_dir"] != "research/CASFORMER_v0_3_META_LOGIC_WIP":
            raise LaunchRefused("EXACT_PACKAGE_DIRECTORIES_REQUIRED")
        wheels = manifest.get("wheel_paths", [])
        dist = "research/CAS_CJT_TRANSFORMER_v0_2/artifacts/release_reproduction/dist/"
        expected_wheels = [dist+"casformer_reference-0.1.0-py3-none-any.whl",dist+"cas_neural_cjt-0.2.0-py3-none-any.whl"]
        if wheels != expected_wheels:
            raise LaunchRefused("TWO_FROZEN_WHEELS_REQUIRED")
        if manifest["dependency_lock"] != manifest["pilot_dir"]+"/requirements-gpu.txt":
            raise LaunchRefused("EXACT_CAMPAIGN_DEPENDENCY_LOCK_REQUIRED")
        hashes = manifest.get("files_sha256", {})
        actual = {i.filename for i in archive.infolist() if not i.is_dir()} - {"launch_manifest.json"}
        if set(hashes) != actual:
            raise LaunchRefused("ARCHIVE_MANIFEST_COVERAGE_MISMATCH")
        for name, sha in hashes.items():
            safe_relative(name)
            if not SHA256.fullmatch(sha) or hashlib.sha256(archive.read(name)).hexdigest() != sha:
                raise LaunchRefused("ARCHIVE_MEMBER_HASH_MISMATCH")
        baseline_bytes = archive.read(manifest["meta1_dir"]+"/BASELINE_MANIFEST.json")
        if hashlib.sha256(baseline_bytes).hexdigest() != ACCEPTED_BASELINE_MANIFEST_SHA256:
            raise LaunchRefused("PROTECTED_BASELINE_MANIFEST_CHANGED")
        protected = json.loads(baseline_bytes)
        for entry in protected["files"]:
            if hashes.get("research/"+entry["path"]) != entry["sha256"]:
                raise LaunchRefused("ACCEPTED_SOURCE_OR_WHEEL_BYTES_CHANGED")
        if not all(w in actual for w in wheels) or manifest["dependency_lock"] not in actual:
            raise LaunchRefused("DECLARED_INPUT_MISSING")
        for key in ("pilot_dir", "meta1_dir", "meta_runtime_dir"):
            if not any(n.startswith(manifest[key] + "/") for n in actual):
                raise LaunchRefused("DECLARED_DIRECTORY_MISSING")
        lock = archive.read(manifest["dependency_lock"]).decode("utf-8")
        for line in lock.splitlines():
            pin = line.strip()
            if not pin or pin.startswith("#"): continue
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*==[A-Za-z0-9_.+!-]+",pin) or pin.lower().startswith("torch==") or "+cpu" in pin:
                raise LaunchRefused("GPU_LOCK_REQUIRES_EXACT_PINS_AND_SEPARATE_TORCH")
        experiment_record(manifest, archive.read)
        return manifest


def validate_prior_packet(path: Path, manifest: dict) -> dict:
    """Only the fixed failed run is eligible. No model/checkpoint is loaded."""
    expected = {"sha256": "db52b01670c9864da7eeecac25c36446986c6b0b625f6d1b6310bbfdcad55def",
                "bytes": 74958249}
    if (not path.is_file() or any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
                                 for p in (path, *path.parents))
            or path.stat().st_size != expected["bytes"] or digest(path) != expected["sha256"]):
        raise LaunchRefused("PRIOR_PACKET_IDENTITY_MISMATCH")
    external = manifest.get("external_packet", {})
    if any(external.get(k) != v or type(external.get(k)) is not type(v)
           for k, v in expected.items()):
        raise LaunchRefused("PRIOR_PACKET_MANIFEST_BINDING_MISMATCH")
    return expected


def validate_approval(cap: str | None, plan: dict) -> None:
    try:
        supplied = Decimal(cap or "NaN")
        if not supplied.is_finite() or supplied != Decimal("400.00"):
            raise LaunchRefused("EXPLICIT_400_USD_TOTAL_CAMPAIGN_APPROVAL_REQUIRED")
    except InvalidOperation as exc:
        raise LaunchRefused("INVALID_APPROVAL_CAP") from exc
    fixed = {"schema_version":2,"approved_cap_usd_required":"400.00","owner_task_cap_usd":"400.00",
             "per_launch_reserved_cap_usd":"4.00","ancillary_reserved_usd":"1.00",
             "account_id":"807562639912","region":"us-west-2","instance_type":"g7.2xlarge",
             "instance_count":1,"gpu_count":1,"runtime_seconds_max":3600,"compute_seconds_max":3300,
             "automatic_retries":0,"ebs_gb":75,"ami_id":"ami-0fbbd0facbc9e3cff","ebs_type":"gp3",
             "on_demand_hourly_usd_max":"2.52","required_gpu_name_contains":"RTX PRO 4500",
             "ebs_encrypted":True,"delete_on_termination":True,"artifact_bytes_max":1073741824,
             "evidence_expanded_bytes_max":2147483648,
             "archive_expanded_bytes_max":536870912,"artifact_objects_max":3,"s3_retention_days":7,
             "torch_version":"2.11.0","torch_cuda_version":"12.8",
             "torch_index_url":"https://download.pytorch.org/whl/cu128",
             "local_neural_execution":False,"cloud_termination_confirmed_before_training":True,
             "inbound_rules":[],"egress_tcp_ports":[443]}
    if any(type(plan.get(k)) is not type(v) or plan.get(k) != v for k,v in fixed.items()):
        raise LaunchRefused("UNREGISTERED_RESOURCE_PLAN")
    budget.validate_plan(plan,plan["per_launch_reserved_cap_usd"])


def reserve_budget(job: str, source_sha: str, archive_sha: str, plan: dict) -> dict:
    # The CLI cap is not authority: this call verifies the preserved root-visible
    # owner approval and continued ledger, then reserves before provider mutation.
    return budget.reserve_budget(job,source_sha,archive_sha,plan["per_launch_reserved_cap_usd"],plan)


def check_tag(tags: list[dict], job: str) -> None:
    if {t["Key"]: t["Value"] for t in tags}.get("cas_meta_job") != job:
        raise LaunchRefused("RESOURCE_OWNERSHIP_MISMATCH")


def verify_launcher_identity(manifest: dict) -> dict:
    """Bind every packaged source byte to local files AND actual committed Git bytes."""
    experiment = experiment_record(manifest)
    try:
        repo, prefix = profiles.git_context(PILOT_ROOT)
        committed = profiles.git_members(repo, prefix, manifest["source_sha"])
    except (ValueError, subprocess.SubprocessError, OSError) as exc:
        raise LaunchRefused("SOURCE_COMMIT_NOT_AVAILABLE:" + str(exc)) from exc
    mapping = manifest["files_sha256"]
    if set(committed) != set(mapping):
        raise LaunchRefused("SOURCE_COMMIT_MANIFEST_MEMBER_SET_MISMATCH")
    checked = {}
    for name, raw in committed.items():
        expected = hashlib.sha256(raw).hexdigest()
        if mapping[name] != expected:
            raise LaunchRefused("SOURCE_COMMIT_MANIFEST_BYTES_MISMATCH:" + name)
        path = PILOT_ROOT.parents[1] / safe_relative(name)
        if (not path.is_file() or any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
                                     for p in (path, *path.parents))
                or digest(path) != expected):
            raise LaunchRefused("LOCAL_SOURCE_ARCHIVE_IDENTITY_MISMATCH:" + name)
        checked[name] = expected
    profile_name = profiles.PILOT + "/tools/experiment_profiles_recovery_v6.py"
    if _PROFILE_IMPORT_SHA256 != mapping[profile_name]:
        raise LaunchRefused("PROFILE_CHANGED_AFTER_IMPORT")
    if mapping[profiles.PILOT + "/aws/budget.py"] != _BUDGET_SHA256:
        raise LaunchRefused("PINNED_SHARED_BUDGET_CHANGED")
    if Path(budget.CANONICAL_LEDGER).resolve() != (PILOT_ROOT / "records/budget/campaign_ledger.json").resolve():
        raise LaunchRefused("SHARED_CANONICAL_LEDGER_REQUIRED")
    profiles.validate_recovery_spec(committed[experiment["spec_path"]])
    return checked


def verify_downloaded_packet(artifact: Path, result: dict, job: str, source_sha: str, plan: dict, *, experiment=None) -> dict:
    """Validate stored bytes and internal identity before force termination is allowed."""
    if artifact.stat().st_size != result["bytes"] or digest(artifact) != result["sha256"]:
        raise LaunchRefused("DOWNLOADED_ARTIFACT_IDENTITY_MISMATCH")
    # Windows FlushFileBuffers requires a write-capable handle. Opening r+b does
    # not truncate or alter the already verified artifact bytes.
    with artifact.open("r+b") as stream:
        stream.flush()
        os.fsync(stream.fileno())
    with zipfile.ZipFile(artifact) as archive:
        names, total = set(), 0
        for info in archive.infolist():
            name = safe_relative(info.filename.rstrip("/"))
            if name in names or stat.S_ISLNK(info.external_attr >> 16):
                raise LaunchRefused("UNSAFE_RESULT_ARCHIVE")
            names.add(name)
            total += info.file_size
            if total > plan["evidence_expanded_bytes_max"]:
                raise LaunchRefused("RESULT_EXPANDED_SIZE_CEILING")
        if archive.testzip() is not None:
            raise LaunchRefused("RESULT_ARCHIVE_CRC_FAILURE")
        record = json.loads(archive.read("artifact_collection_receipt.json"))
        if record.get("job") != job or record.get("source_sha") != source_sha or record.get("returncode") != result["returncode"]:
            raise LaunchRefused("RESULT_INTERNAL_IDENTITY_MISMATCH")
        if experiment is not None and (record.get("experiment") != experiment or result.get("experiment") != experiment):
            raise LaunchRefused("RESULT_EXPERIMENT_IDENTITY_MISMATCH")
        if result["returncode"] == 0 and (record.get("partial_evidence") is not False or record.get("omitted_full_file_count") != 0):
            raise LaunchRefused("SUCCESS_WITH_OMITTED_EVIDENCE_REFUSED")
        return record


def confirm_deleted_volumes(ec2, job: str, record) -> list[str]:
    deadline = time.monotonic() + 90
    while True:
        response = ec2.describe_volumes(Filters=[{"Name":"tag:cas_meta_job","Values":[job]}])
        if response.get("NextToken"):
            raise LaunchRefused("PAGINATED_VOLUME_CLEANUP_UNCONFIRMED")
        for volume in response["Volumes"]:
            check_tag(volume.get("Tags",[]),job)
        remaining = [volume["VolumeId"] for volume in response["Volumes"] if volume["State"] != "deleted"]
        if not remaining:
            record("TAGGED_VOLUME_DELETION_CONFIRMED",provider_response=response)
            return []
        if time.monotonic() >= deadline:
            return remaining
        time.sleep(5)


def remove_owned_auxiliary_resources(ec2, iam, scheduler, receipt, job, worker_role, timer_role, record):
    """Delete only the exact tagged resources recorded for this one job."""
    from botocore.exceptions import ClientError
    def remove(label, operation):
        try:
            operation()
            record("OWNED_AUXILIARY_RESOURCE_REMOVED",resource=label)
        except ClientError as exc:
            if exc.response["Error"]["Code"] in ("ResourceNotFoundException","NoSuchEntity","InvalidGroup.NotFound"):
                record("OWNED_AUXILIARY_RESOURCE_ALREADY_ABSENT",resource=label)
            else:
                receipt["cleanup_errors"].append(label+": "+exc.response["Error"]["Code"])
        except Exception as exc:
            receipt["cleanup_errors"].append(label+": "+type(exc).__name__+": "+str(exc))
    resources = receipt["resources"]
    if "schedule" in resources:
        def delete_schedule():
            current = scheduler.get_schedule(Name=job)
            target = current.get("Target",{})
            if current.get("Name") != job or target.get("RoleArn") != resources.get(timer_role) or json.loads(target.get("Input","{}")) != {"InstanceIds":[resources.get("instance")]}:
                raise LaunchRefused("SCHEDULE_OWNERSHIP_MISMATCH")
            scheduler.delete_schedule(Name=job)
        remove("schedule:"+job,delete_schedule)
    if "instance_profile" in resources:
        def delete_profile():
            current = iam.get_instance_profile(InstanceProfileName=worker_role)["InstanceProfile"]
            check_tag(current.get("Tags",[]),job)
            roles = current.get("Roles",[])
            if any(role.get("RoleName") != worker_role for role in roles):
                raise LaunchRefused("PROFILE_HAS_UNEXPECTED_ROLE")
            if roles: iam.remove_role_from_instance_profile(InstanceProfileName=worker_role,RoleName=worker_role)
            iam.delete_instance_profile(InstanceProfileName=worker_role)
        remove("instance-profile:"+worker_role,delete_profile)
    for name in (worker_role,timer_role):
        if name not in resources:
            continue
        def delete_role(name=name):
            current = iam.get_role(RoleName=name)["Role"]
            check_tag(current.get("Tags",[]),job)
            if current.get("Arn") != resources[name]: raise LaunchRefused("ROLE_ARN_MISMATCH")
            try:
                iam.delete_role_policy(RoleName=name,PolicyName="job-only")
            except ClientError as exc:
                if exc.response["Error"]["Code"] != "NoSuchEntity": raise
            iam.delete_role(RoleName=name)
        remove("role:"+name,delete_role)
    if "security_group" in resources:
        def delete_group():
            current = ec2.describe_security_groups(GroupIds=[resources["security_group"]])["SecurityGroups"]
            if len(current) != 1: raise LaunchRefused("EXACT_SECURITY_GROUP_REQUIRED")
            check_tag(current[0].get("Tags",[]),job)
            ec2.delete_security_group(GroupId=resources["security_group"])
        remove("security-group:"+resources["security_group"],delete_group)


def reconcile_instance(ec2, job: str) -> dict:
    """Recover an uncertain RunInstances response; no match is not proof of absence."""
    response = ec2.describe_instances(Filters=[{"Name":"tag:cas_meta_job","Values":[job]},
                                              {"Name":"client-token","Values":[job]}])
    if response.get("NextToken"):
        raise LaunchRefused("TERMINATION_UNCONFIRMED:PAGINATED_JOB_IDENTITY")
    instances = [i for r in response["Reservations"] for i in r["Instances"]]
    if len(instances) != 1:
        raise LaunchRefused("TERMINATION_UNCONFIRMED:EXPECTED_EXACTLY_ONE_JOB_INSTANCE")
    instance = instances[0]
    check_tag(instance.get("Tags",[]),job)
    if instance.get("ClientToken") != job:
        raise LaunchRefused("TERMINATION_UNCONFIRMED:CLIENT_TOKEN_MISMATCH")
    return instance


def verify_schedule(confirmed: dict, target: dict, expression: str) -> None:
    if (confirmed.get("State") != "ENABLED" or confirmed.get("ScheduleExpression") != expression
            or confirmed.get("ScheduleExpressionTimezone") != "UTC"
            or confirmed.get("FlexibleTimeWindow") != {"Mode":"OFF"}
            or confirmed.get("ActionAfterCompletion") != "DELETE"
            or any(confirmed.get("Target",{}).get(k) != v for k,v in target.items())):
        raise LaunchRefused("CLOUD_DEADLINE_NOT_CONFIRMED")


def terminate_owned_instance(ec2, instance_id: str, job: str, *, artifact_verified: bool, record) -> None:
    """Skip guest shutdown only after verified evidence is safely downloaded."""
    def owned_instance():
        instance = ec2.describe_instances(InstanceIds=[instance_id])["Reservations"][0]["Instances"][0]
        check_tag(instance.get("Tags",[]),job)
        if instance.get("ClientToken") != job:
            raise LaunchRefused("INSTANCE_CLIENT_TOKEN_MISMATCH")
        return instance
    if owned_instance()["State"]["Name"] == "terminated": return
    response = ec2.terminate_instances(InstanceIds=[instance_id])
    record("INSTANCE_NORMAL_TERMINATION_REQUESTED",instance_id=instance_id,provider_response=response)
    deadline = time.monotonic() + 60
    while True:
        state = owned_instance()["State"]["Name"]
        if state == "terminated": return
        remaining = deadline - time.monotonic()
        if remaining <= 0: break
        time.sleep(min(5,remaining))
    if not artifact_verified:
        raise LaunchRefused("TERMINATION_UNCONFIRMED:NO_VERIFIED_DOWNLOAD_FORCE_SHUTDOWN_REFUSED")
    response = ec2.terminate_instances(InstanceIds=[instance_id],Force=True,SkipOsShutdown=True)
    record("INSTANCE_SKIP_OS_SHUTDOWN_REQUESTED",instance_id=instance_id,
           verified_download_required=True,previous_state=state,provider_response=response)
    # Blackwell smoke 001 remained shutting-down beyond the former two-minute
    # observer window. Keep watching the already-requested termination; this
    # does not extend the training deadline or send more termination requests.
    record("INSTANCE_TERMINATION_OBSERVATION_STARTED",instance_id=instance_id,
           maximum_observation_seconds=600,additional_termination_requests=0)
    ec2.get_waiter("instance_terminated").wait(InstanceIds=[instance_id],WaiterConfig={"Delay":5,"MaxAttempts":120})


def build_evidence_bundle(artifact_root, bundle, limit, job_record, expanded_limit=None, force_partial=False):
    """Pure file packaging: oversize output becomes an explicit bounded failure packet."""
    import hashlib, json, pathlib, zipfile
    artifact_root, bundle = pathlib.Path(artifact_root), pathlib.Path(bundle)
    files = sorted(p for p in artifact_root.rglob('*') if p.is_file() or p.is_symlink())
    index, index_hash, total, unsafe = [], hashlib.sha256(), 0, 0
    for path in files:
        entry = {'path':path.relative_to(artifact_root).as_posix()}
        if path.is_symlink():
            entry.update(status='SYMLINK_OMITTED'); unsafe += 1
        else:
            entry['bytes'] = path.stat().st_size
            total += entry['bytes']
            h = hashlib.sha256()
            with path.open('rb') as stream:
                for block in iter(lambda:stream.read(1048576),b''): h.update(block)
            entry['sha256'] = h.hexdigest()
        index_hash.update(json.dumps(entry,sort_keys=True,separators=(',',':')).encode()+b'\n')
        index.append(entry)
    # Space for ZIP framing, receipt and manifest; logs from bootstrap are separate.
    expanded_limit = limit if expanded_limit is None else expanded_limit
    payload_limit = expanded_limit - 2097152
    partial = total > payload_limit or unsafe > 0 or force_partial
    selected, selected_bytes = [], 0
    if not partial:
        selected = [p for p in files if not p.is_symlink()]
    else:
        # Keep small receipts and candidate weights when they fit. Never alter originals.
        priorities = sorted((p for p in files if not p.is_symlink()),
                            key=lambda p:(not (p.suffix == '.pt' or p.name == 'predictions.jsonl'),p.suffix not in ('.json','.xml'),str(p)))
        mandatory = [p for p in priorities if p.suffix == '.pt' or p.name == 'predictions.jsonl']
        mandatory_bytes = sum(p.stat().st_size for p in mandatory)
        fallback_limit = min(limit-2097152,max(64*1024*1024,mandatory_bytes+2097152))
        if mandatory_bytes > fallback_limit:
            raise RuntimeError('MANDATORY_CHECKPOINT_AND_PREDICTIONS_EXCEED_FAILURE_PACKET_CEILING')
        for path in priorities:
            size = path.stat().st_size
            if path.suffix == '.pt' or path.name == 'predictions.jsonl' or (path.suffix in ('.json','.xml','.txt') and size <= 262144):
                if selected_bytes + size <= fallback_limit:
                    selected.append(path); selected_bytes += size
    selected_names = {p.relative_to(artifact_root).as_posix() for p in selected}
    record = dict(job_record)
    record.update(partial_evidence=partial, original_file_count=len(files), original_bytes=total,
                  included_full_file_count=len(selected), omitted_full_file_count=len(files)-len(selected),
                  original_file_index_sha256=index_hash.hexdigest(),
                  index_hash_format='SHA256 of canonical JSON entry plus LF for every sorted original path',
                  index_entries=index[:1000], index_entries_omitted=max(0,len(index)-1000),
                  artifact_bytes_max=limit,evidence_expanded_bytes_max=expanded_limit)
    if partial:
        record.update(returncode=1,failure=job_record.get('failure','ARTIFACT_CEILING_OR_UNSAFE_ENTRY; bounded failure evidence preserved, not a completed campaign'))
    with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED) as archive:
        for path in selected: archive.write(path,path.relative_to(artifact_root).as_posix())
        if partial:
            for index_number,path in enumerate(p for p in files if p.suffix == '.log' and not p.is_symlink()):
                if index_number >= 2: break
                with path.open('rb') as stream:
                    stream.seek(max(0,path.stat().st_size-1048576))
                    archive.writestr('failure_log_tails/'+path.name,stream.read(1048576))
        archive.writestr('artifact_collection_receipt.json',json.dumps(record,sort_keys=True,indent=2))
    if bundle.stat().st_size > limit:
        if not partial:
            failed = dict(job_record)
            failed.update(returncode=1,failure='COMPRESSED_ARTIFACT_CEILING; complete evidence not uploaded')
            return build_evidence_bundle(artifact_root,bundle,limit,failed,expanded_limit,True)
        raise RuntimeError('BOUNDED_FAILURE_PACKET_EXCEEDED_CEILING')
    return record


def sample_artifact_bytes(root):
    """SQLite WAL/SHM files can disappear as a completed task closes its store."""
    total = 0
    for path in root.rglob('*'):
        try:
            if path.is_file(): total += path.stat().st_size
        except FileNotFoundError:
            continue
    return total


def remote_program(config: dict) -> str:
    """Return remote-only bookkeeping/bootstrap. It never executes on the client."""
    if config.get('smoke_only') is not False:
        raise LaunchRefused('RECOVERY_HAS_NO_TRAINING_OR_SMOKE_MODE')
    experiment = experiment_record(config['manifest'])
    selected_entrypoint = experiment['entrypoint']
    program = "CONFIG = " + repr(config) + "\n" + inspect.getsource(build_evidence_bundle) + "\n" + inspect.getsource(sample_artifact_bytes) + "\n" + r'''
import hashlib, json, os, pathlib, platform, shutil, signal, subprocess, sys, time, traceback, zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
os.environ['CUBLAS_WORKSPACE_CONFIG'] = ':4096:8'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
root = pathlib.Path('/opt/cas-meta2')
payload = root / 'payload.zip'
def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1048576), b''): h.update(block)
    return h.hexdigest()
def run(argv, **kwargs):
    print(json.dumps({'command': argv}), flush=True)
    return subprocess.run(argv, check=True, **kwargs)
def s3_get(key, target):
    run(['aws','s3','cp','s3://'+CONFIG['bucket']+'/'+key,str(target),'--region',CONFIG['region']])
start = time.time()
returncode = 1
out = root/'early_failure'
out.mkdir(parents=True,exist_ok=True)
artifact_root = out
m = CONFIG['manifest']

def publish_progress(log_path, status):
    # Best effort: one existing result key, <=64 KiB, and at most five seconds.
    try:
        def tail(path, count):
            try:
                with path.open('rb') as stream:
                    stream.seek(max(0,path.stat().st_size-count))
                    return stream.read(count)
            except OSError: return b''
        header = json.dumps({'job':CONFIG['job'],'utc':datetime.now(timezone.utc).isoformat(),
                             'stage_log':log_path.name,**status},sort_keys=True).encode()
        progress = tail(out/'campaign'/'progress.json',8192)
        content = header+b'\nCAMPAIGN STATUS\n'+progress+b'\nCURRENT STAGE LOG TAIL\n'+tail(log_path,49152)
        target = root/'live-progress.log'
        target.write_bytes(content[:65536])
        subprocess.run(['aws','s3','cp',str(target),'s3://'+CONFIG['bucket']+'/results/bootstrap.log',
                        '--region',CONFIG['region'],'--cli-connect-timeout','5','--cli-read-timeout','5'],
                       timeout=5,check=False,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                       env={**os.environ,'AWS_MAX_ATTEMPTS':'1','AWS_PAGER':''})
    except Exception:
        pass

def bounded_process(argv, log_path, *, env, cwd, seconds, deadline):
    stage_start = time.time()
    next_progress = stage_start
    with log_path.open('w') as log:
        process = subprocess.Popen(argv,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try:
            while process.poll() is None:
                size = sample_artifact_bytes(artifact_root)
                if 'package' in globals(): size += sample_artifact_bytes(package/m['meta1_dir']/'runs')
                if size > CONFIG['evidence_expanded_bytes_max'] - 2097152 or time.time()-stage_start > seconds or time.time() > deadline-120:
                    raise RuntimeError('PROCESS_TIME_OR_ARTIFACT_CEILING')
                if time.time() >= next_progress:
                    next_progress = time.time()+30
                    publish_progress(log_path,{'state':'RUNNING','elapsed_seconds':time.time()-stage_start,'artifact_bytes':size})
                time.sleep(2)
            publish_progress(log_path,{'state':'EXITED','returncode':process.returncode,'elapsed_seconds':time.time()-stage_start})
            return process.returncode
        finally:
            # Stop the parent and all spawned workers before packaging a failed stage.
            if process.poll() is None or process.returncode != 0:
                try: os.killpg(process.pid,signal.SIGTERM)
                except ProcessLookupError: pass
                try: process.wait(timeout=15)
                except subprocess.TimeoutExpired: pass
                try: os.killpg(process.pid,signal.SIGKILL)
                except ProcessLookupError: pass
                if process.poll() is None:
                    process.wait(timeout=15)

try:
    # No training or dependency installation before the external deadline is confirmed.
    permit = root / 'permit.json'
    for attempt in range(60):
        try:
            s3_get('input/permit.json', permit)
            p = json.loads(permit.read_text())
            if p['job'] != CONFIG['job'] or p['archive_sha256'] != CONFIG['archive_sha256'] or not p['cloud_deadline_confirmed']:
                raise RuntimeError('INVALID_CLOUD_DEADLINE_PERMIT')
            break
        except subprocess.CalledProcessError: time.sleep(5)
    else: raise RuntimeError('CLOUD_DEADLINE_NOT_CONFIRMED')
    deadline = datetime.fromisoformat(p['deadline']).timestamp()
    if deadline - time.time() < 300: raise RuntimeError('INSUFFICIENT_REMAINING_CLOUD_TIME')
    s3_get('input/payload.zip', payload)
    if sha(payload) != CONFIG['archive_sha256']: raise RuntimeError('ARCHIVE_SHA_MISMATCH')
    with zipfile.ZipFile(payload) as z:
        m = json.loads(z.read('launch_manifest.json'))
        if m != CONFIG['manifest']: raise RuntimeError('MANIFEST_MISMATCH')
        for name, expected in m['files_sha256'].items():
            if hashlib.sha256(z.read(name)).hexdigest() != expected: raise RuntimeError('MEMBER_HASH_MISMATCH')
        z.extractall(root / 'package') # names and membership were checked before publication
    package = root / 'package'
    out = package / m['pilot_dir'] / 'runs' / 'cloud_job'
    out.mkdir(parents=True)
    artifact_root = out.parent
    py = root / 'venv' / 'bin' / 'python'
    run([sys.executable,'-m','venv',str(root / 'venv')],timeout=max(1,deadline-time.time()-240))
    run([str(py),'-m','pip','install','--disable-pip-version-check','torch==2.11.0','--index-url',CONFIG['torch_index_url'],'--report',str(out/'torch_install.json')],timeout=max(1,deadline-time.time()-240))
    run([str(py),'-m','pip','install','--disable-pip-version-check','-r',str(package/m['dependency_lock']),'--report',str(out/'dependency_install.json')],timeout=max(1,deadline-time.time()-240))
    run([str(py),'-m','pip','install','--no-deps',*[str(package/w) for w in m['wheel_paths']],'--report',str(out/'frozen_wheel_install.json')],timeout=max(1,deadline-time.time()-240))
    probe = "import torch,json,sys,platform; assert torch.__version__=='2.11.0+cu128'; assert torch.version.cuda=='12.8'; assert torch.cuda.is_available(); assert torch.cuda.device_count()==1; gpu=torch.cuda.get_device_name(0); assert " + repr(CONFIG['required_gpu_name_contains']) + " in gpu; x=torch.ones((32,32),device='cuda'); assert (x@x).sum().item()==32768; torch.cuda.synchronize(); print(json.dumps({'python':sys.version,'platform':platform.platform(),'torch':torch.__version__,'cuda':torch.version.cuda,'gpu':gpu,'cuda_matmul_passed':True}))"
    with (out/'runtime.json').open('w') as f: run([str(py),'-c',probe],stdout=f,timeout=60)
    with (out/'pip_freeze.txt').open('w') as f: run([str(py),'-m','pip','freeze','--all'],stdout=f,timeout=30)
    env = dict(os.environ)
    env['PYTHONPATH'] = ':'.join(str(package/m[key]) for key in ('pilot_dir','meta1_dir','meta_runtime_dir'))
    env['CUDA_VISIBLE_DEVICES'] = '0'
    env['CAS_META1_AWS_JOB_ID'] = CONFIG['job']
    env['CAS_META1_SOURCE_SHA'] = m['source_sha']
    env['CAS_META1_RUN_GPU_TESTS'] = '1'
    env['CAS_META2_AWS_JOB_ID'] = CONFIG['job']
    env['CAS_META2_SOURCE_SHA'] = m['source_sha']
    if 'experiment' in m:
        env['CAS_META2_EXPERIMENT_PROFILE'] = m['experiment']['profile']
        env['CAS_META2_EXPERIMENT_ENTRYPOINT'] = m['experiment']['entrypoint']
        env['CAS_META2_EXPERIMENT_SPEC_SHA256'] = m['experiment']['spec_sha256']
    env['OMP_NUM_THREADS'] = '1'
    env['MKL_NUM_THREADS'] = '1'
    gpu_argv = [str(py),'-m','pytest','-m','gpu','tests/test_execution_contract.py','-q','--junitxml',str(out/'gpu_contract_tests.xml'),'-p','no:cacheprovider']
    (out/'gpu_contract_command.json').write_text(json.dumps(gpu_argv,indent=2))
    if deadline-time.time() < 300: raise RuntimeError('INSUFFICIENT_GPU_PREFLIGHT_TIME')
    gpu_code = bounded_process(gpu_argv,out/'gpu_contract_tests.log',env=env,cwd=package/m['meta1_dir'],seconds=600,deadline=deadline)
    suites = list(ET.parse(out/'gpu_contract_tests.xml').getroot().iter('testsuite'))
    totals = {key:sum(int(s.get(key,'0')) for s in suites) for key in ('tests','failures','errors','skipped')}
    if gpu_code != 0 or totals != {'tests':4,'failures':0,'errors':0,'skipped':0}:
        raise RuntimeError('GPU_CONTRACT_TESTS_MUST_REPORT_EXACTLY_FOUR_PASSED:'+str(totals))
    (out/'gpu_contract_receipt.json').write_text(json.dumps({'passed':4,**totals}))
    env.pop('CAS_META1_RUN_GPU_TESTS')
    env.pop('CAS_META2_RUN_CONTRAST_TRAINING',None)
    env['CAS_META2_RUN_GPU_TESTS'] = '1'
    env['CAS_META2_RUN_CONTRAST_RECOVERY'] = '1'
    prior_packet = root/'prior_packet.zip'
    s3_get('input/prior_packet.zip',prior_packet)
    if prior_packet.stat().st_size != CONFIG['prior_packet']['bytes'] or sha(prior_packet) != CONFIG['prior_packet']['sha256']:
        raise RuntimeError('PRIOR_PACKET_IDENTITY_MISMATCH')
    effective_seconds = min(3000,CONFIG['compute_seconds_max'],int(deadline-time.time()-180))
    if effective_seconds < 2800:
        raise RuntimeError('INSUFFICIENT_RECOVERY_TIME_AFTER_GPU_GATE')
    recovery = CONFIG['manifest']['recovery']
    argv = [str(py),'-B',str(package/m['pilot_dir']/'aws/recovery_remote_v6.py'),
            '--admission',str(package/recovery['admission_path']),
            '--admission-sha256',recovery['admission_sha256'],
            '--recovery-manifest',str(package/recovery['source_manifest_path']),
            '--recovery-manifest-sha256',recovery['source_manifest_sha256'],
            '--packet',str(prior_packet),'--inputs',str(root/'recovery_input'),
            '--output',str(out/'recovery'),'--job',CONFIG['job'],
            '--max-seconds',str(effective_seconds),'--enable-native-evaluation']
    (out/'command.json').write_text(json.dumps(argv,indent=2))
    returncode = bounded_process(argv,out/'recovery.log',env=env,cwd=package/m['pilot_dir'],seconds=effective_seconds,deadline=deadline)
    if returncode == 0:
        receipt_path = out/'recovery'/'native'/'recovery_receipt.json'
        result_path = out/'recovery'/'native'/'evaluation_results.json'
        gate_path = out/'recovery'/'gpu_gate.json'
        coordinator_path = out/'recovery'/'coordinator_receipt.json'
        if any(not path.is_file() or path.stat().st_size == 0 for path in
               (receipt_path,result_path,gate_path,coordinator_path)):
            raise RuntimeError('SUCCESS_WITHOUT_REQUIRED_RECOVERY_EVIDENCE')
        recovered = json.loads(receipt_path.read_text())
        if (recovered.get('schema') != 'cas-meta2-contrast-evaluation-recovery/6'
                or recovered.get('status') != 'CAS_META2_V6_EVALUATION_RECOVERY_COMPLETED'
                or recovered.get('completed') is not True
                or recovered.get('cases') != 72 or recovered.get('arm_verdicts') != 360
                or recovered.get('original_campaign_completed') is not False
                or recovered.get('fresh_test') is not False
                or recovered.get('training_performed') is not False
                or recovered.get('predictions_reused_unchanged') is not True):
            raise RuntimeError('RECOVERY_RECEIPT_BOUNDARY_OR_COMPLETION_INVALID')
        coordinator = json.loads(coordinator_path.read_text())
        if coordinator.get('completed') is not True or coordinator.get('job') != CONFIG['job']:
            raise RuntimeError('RECOVERY_COORDINATOR_IDENTITY_OR_COMPLETION_INVALID')

except BaseException as exc:
    returncode = 1
    (out/'remote_failure.json').write_text(json.dumps({'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()},indent=2))
finally:
    if 'package' in globals() and (package/m['meta1_dir']/'runs').exists():
        try:
            shutil.copytree(package/m['meta1_dir']/'runs',artifact_root/'meta1_runs',symlinks=True)
        except BaseException as exc:
            returncode = 1
            (out/'test_evidence_copy_failure.json').write_text(json.dumps({'type':type(exc).__name__,'message':str(exc)}))
    job_record = {'job':CONFIG['job'],'source_sha':m['source_sha'],'baseline_sha':m['baseline_sha'],'archive_sha256':CONFIG['archive_sha256'],'returncode':returncode,'remote_wall_seconds':time.time()-start,'smoke_only':CONFIG['smoke_only']}
    if 'experiment' in m: job_record['experiment'] = m['experiment']
    (out/'job.json').write_text(json.dumps(job_record,indent=2))
    bundle = root/'artifacts.zip'
    collected = build_evidence_bundle(artifact_root,bundle,CONFIG['artifact_bytes_max']-2097152,job_record,CONFIG['evidence_expanded_bytes_max'])
    returncode = collected['returncode']
    run(['aws','s3','cp',str(bundle),'s3://'+CONFIG['bucket']+'/results/artifacts.zip','--region',CONFIG['region']])
    complete = {'sha256':sha(bundle),'bytes':bundle.stat().st_size,'returncode':returncode,'job':CONFIG['job'],'smoke_only':CONFIG['smoke_only'],'partial_evidence':collected['partial_evidence'],'omitted_full_file_count':collected['omitted_full_file_count']}
    if 'experiment' in m: complete['experiment'] = m['experiment']
    (root/'complete.json').write_text(json.dumps(complete))
    run(['aws','s3','cp',str(root/'complete.json'),'s3://'+CONFIG['bucket']+'/results/complete.json','--region',CONFIG['region']])
sys.exit(returncode)
'''
    return program.replace('__CAS_META2_ENTRYPOINT__', repr(selected_entrypoint))


def user_data(config: dict, remote_sha256: str | None = None) -> str:
    remote_sha256 = remote_sha256 or hashlib.sha256(remote_program(config).encode()).hexdigest()
    if not SHA256.fullmatch(remote_sha256): raise LaunchRefused("REMOTE_SCRIPT_SHA_REQUIRED")
    # Timer is armed before network access; EXIT covers bootstrap errors as well.
    text = "\n".join([
        "#!/bin/bash", "set -eu", "umask 077", "export PYTHONDONTWRITEBYTECODE=1",
        "trap 'test ! -f /opt/cas-meta2/bootstrap.log || { tail -c 1048576 /opt/cas-meta2/bootstrap.log > /opt/cas-meta2/bootstrap-tail.log; aws s3 cp /opt/cas-meta2/bootstrap-tail.log " + shlex.quote("s3://" + config["bucket"] + "/results/bootstrap.log") + " --region " + shlex.quote(config["region"]) + " || true; }; shutdown -h now' EXIT",
        "( sleep " + str(config['runtime_seconds_max']-100) + "; shutdown -h now ) >/dev/null 2>&1 &",
        "mkdir -p /opt/cas-meta2",
        "exec > /opt/cas-meta2/bootstrap.log 2>&1",
        "command -v aws >/dev/null || { echo AWS_CLI_REQUIRED; exit 1; }",
        "PY=''",
        "for p in python3.12 python3.11 /opt/conda/bin/python /opt/pytorch/bin/python /home/ubuntu/anaconda3/bin/python /home/ubuntu/miniconda3/bin/python python3; do",
        "  if command -v \"$p\" >/dev/null 2>&1 && \"$p\" -c 'import sys; assert (3,11) <= sys.version_info[:2] <= (3,12)' 2>/dev/null; then PY=\"$p\"; break; fi",
        "done",
        "test -n \"$PY\" || { echo SUPPORTED_PYTHON_REQUIRED; exit 1; }",
        "aws s3 cp " + shlex.quote("s3://"+config["bucket"]+"/input/remote.py") + " /opt/cas-meta2/remote.py --region " + shlex.quote(config["region"]),
        "echo '" + remote_sha256 + "  /opt/cas-meta2/remote.py' | sha256sum -c -",
        '"$PY" /opt/cas-meta2/remote.py', "",
    ])
    if len(text.encode()) > 16384:
        raise LaunchRefused("EC2_USER_DATA_SIZE_CEILING")
    return text



@contextmanager
def campaign_execution_lock():
    """Only serialize this v3 checkout; AWS live-job checks remain mandatory."""
    path = EXECUTION_LOCK_FILE
    if any(p.is_symlink() or getattr(p, "is_junction", lambda: False)() for p in (path, *path.parents)):
        raise LaunchRefused("EXECUTION_LOCK_LINK_REFUSED")
    path.parent.mkdir(parents=True, exist_ok=True)
    owner = {"schema": "cas-meta2-v3-execution-lock/1", "token": uuid.uuid4().hex,
             "pid": os.getpid(), "utc": datetime.now(timezone.utc).isoformat(),
             "scope": "Local v3 checkout only; not a cross-host or old-launcher lock."}
    raw = (json.dumps(owner, sort_keys=True) + "\n").encode()
    try:
        stream = path.open("xb")
    except FileExistsError as exc:
        raise LaunchRefused("V3_EXECUTION_ALREADY_LOCKED_NO_AUTOMATIC_STALE_CLEAR") from exc
    try:
        with stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        yield owner
    finally:
        if path.is_symlink() or not path.is_file() or path.read_bytes() != raw:
            raise LaunchRefused("EXECUTION_LOCK_OWNERSHIP_CHANGED_NOT_REMOVED")
        deadline = time.monotonic() + 2
        while True:
            try:
                path.unlink()
                break
            except PermissionError:
                if time.monotonic() >= deadline:
                    raise LaunchRefused("EXECUTION_LOCK_RELEASE_FAILED_CLOSED")
                time.sleep(0.05)


def execute(args: argparse.Namespace, plan: dict, manifest: dict) -> dict:
    # All source checks precede the lock write as well as budget/provider access.
    if args.smoke_only:
        raise LaunchRefused('RECOVERY_HAS_NO_TRAINING_OR_SMOKE_MODE')
    validate_approval(args.approved_cap_usd, plan)
    experiment_record(manifest)
    verify_launcher_identity(manifest)
    validate_prior_packet(Path(args.prior_packet), manifest)
    with campaign_execution_lock():
        return _execute_locked(args, plan, manifest)

def _execute_locked(args: argparse.Namespace, plan: dict, manifest: dict) -> dict:
    validate_approval(args.approved_cap_usd, plan)
    experiment = experiment_record(manifest)
    launcher_identity = verify_launcher_identity(manifest)
    prior_packet = validate_prior_packet(Path(args.prior_packet), manifest)
    continued_budget = budget.read_ledger()
    if Decimal(continued_budget["remaining_unreserved_usd"]) < Decimal(plan["per_launch_reserved_cap_usd"]):
        raise LaunchRefused("CAMPAIGN_BUDGET_EXHAUSTED")
    # boto3 is intentionally unavailable to the plan/contract-test path.
    import boto3
    from botocore.config import Config
    from botocore.exceptions import ClientError

    if not re.fullmatch(r"subnet-[0-9a-f]+", args.subnet_id or ""):
        raise LaunchRefused("EXPLICIT_SUBNET_REQUIRED")
    output = Path(args.receipt_dir).resolve()
    if not output.is_relative_to(PILOT_ROOT) or output == PILOT_ROOT or output.exists():
        raise LaunchRefused("NEW_RECEIPT_DIRECTORY_INSIDE_PILOT_REQUIRED")
    cfg = Config(connect_timeout=10, read_timeout=30, retries={"max_attempts": 0})
    session = boto3.Session(profile_name=args.profile, region_name=plan["region"])
    clients = {s: session.client(s, config=cfg) for s in ("sts", "ec2", "iam", "s3", "scheduler")}
    sts, ec2, iam, s3, scheduler = (clients[s] for s in clients)
    identity = sts.get_caller_identity()
    if identity["Account"] != plan["account_id"]:
        raise LaunchRefused("AWS_ACCOUNT_MISMATCH")
    subnet = ec2.describe_subnets(SubnetIds=[args.subnet_id])["Subnets"][0]
    images = ec2.describe_images(ImageIds=[plan["ami_id"]])["Images"]
    if len(images) != 1 or images[0]["State"] != "available" or images[0].get("RootDeviceName") != "/dev/sda1" or images[0].get("OwnerId") != "898082745236":
        raise LaunchRefused("PINNED_AMI_UNAVAILABLE")
    quota = session.client("service-quotas",config=cfg).get_service_quota(ServiceCode="ec2",QuotaCode="L-DB2E81BA")
    if quota["Quota"]["Value"] < 8:
        raise LaunchRefused("CURRENT_G_GPU_QUOTA_BELOW_EIGHT_VCPUS")
    active = ec2.describe_instances(Filters=[{"Name":"tag-key","Values":["cas_meta_job"]},{"Name":"instance-state-name","Values":["pending","running","stopping","shutting-down"]}])
    if active.get("NextToken") or any(group["Instances"] for group in active["Reservations"]):
        raise LaunchRefused("EXISTING_ACTIVE_CAS_JOB_REQUIRES_RECONCILIATION")
    pricing = session.client("pricing", region_name="us-east-1", config=cfg)
    fields = {"instanceType": plan["instance_type"], "location": "US West (Oregon)", "operatingSystem": "Linux", "tenancy": "Shared", "preInstalledSw": "NA", "capacitystatus": "Used", "marketoption":"OnDemand", "operation":"RunInstances"}
    prices = pricing.get_products(ServiceCode="AmazonEC2", Filters=[{"Type":"TERM_MATCH","Field":k,"Value":v} for k,v in fields.items()])["PriceList"]
    rates = [Decimal(d["pricePerUnit"]["USD"]) for raw in prices for t in json.loads(raw)["terms"]["OnDemand"].values() for d in t["priceDimensions"].values() if d["unit"] == "Hrs"]
    if rates != [Decimal(plan["on_demand_hourly_usd_max"])]:
        raise LaunchRefused("CURRENT_PRICE_REQUIRES_NEW_PLAN")
    job = "cas-meta2-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S") + "-" + uuid.uuid4().hex[:8]
    budget_reservation = reserve_budget(job,args.source_sha,args.sha256,plan)
    bucket = job + "-" + plan["account_id"]
    worker_role, timer_role = job + "-worker", job + "-timer"
    tags = [{"Key":"cas_meta_job","Value":job}]
    receipt = {"status":"STARTING","job":job,"smoke_only":bool(args.smoke_only),"plan":plan,"explicit_approved_cap_argument_usd":args.approved_cap_usd,"task_budget_reservation":budget_reservation,"local_launcher_identity":launcher_identity,"source_sha":args.source_sha,"archive_sha256":args.sha256,"manifest":manifest,"prior_packet":prior_packet,"caller_arn":identity["Arn"],"official_price_response":prices,"resources":{},"events":[],"cleanup_errors":[]}
    if experiment is not None: receipt["experiment"] = experiment
    output.mkdir(parents=True)
    def save():
        (output / "launch_receipt.json").write_text(json.dumps(receipt, indent=2, default=str), encoding="utf-8")
    def record(event, **details):
        receipt["events"].append({"time":datetime.now(timezone.utc).isoformat(),"event":event,**details}); save()
    def role(name, service, statements):
        trust = {"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":service},"Action":"sts:AssumeRole"}]}
        created = iam.create_role(RoleName=name, AssumeRolePolicyDocument=json.dumps(trust), Tags=tags)["Role"]
        receipt["resources"][name] = created["Arn"]; save()
        iam.put_role_policy(RoleName=name, PolicyName="job-only", PolicyDocument=json.dumps({"Version":"2012-10-17","Statement":statements}))
        return created["Arn"]
    iid = None
    launch_attempted = False
    artifact_verified = False
    try:
        s3.create_bucket(Bucket=bucket, CreateBucketConfiguration={"LocationConstraint":plan["region"]})
        receipt["resources"]["bucket"] = bucket; save()
        s3.put_bucket_tagging(Bucket=bucket,Tagging={"TagSet":tags})
        s3.put_public_access_block(Bucket=bucket, PublicAccessBlockConfiguration={k:True for k in ("BlockPublicAcls","IgnorePublicAcls","BlockPublicPolicy","RestrictPublicBuckets")})
        s3.put_bucket_encryption(Bucket=bucket,ServerSideEncryptionConfiguration={"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]})
        s3.put_bucket_lifecycle_configuration(Bucket=bucket,LifecycleConfiguration={"Rules":[{"ID":"job-seven-days","Status":"Enabled","Filter":{"Prefix":""},"Expiration":{"Days":7},"AbortIncompleteMultipartUpload":{"DaysAfterInitiation":1}}]})
        role(worker_role,"ec2.amazonaws.com",[{"Effect":"Allow","Action":["s3:GetObject"],"Resource":[f"arn:aws:s3:::{bucket}/input/{key}" for key in ("payload.zip","permit.json","remote.py","prior_packet.zip")]},{"Effect":"Allow","Action":["s3:PutObject"],"Resource":[f"arn:aws:s3:::{bucket}/results/{key}" for key in ("artifacts.zip","complete.json","bootstrap.log")]}])
        iam.create_instance_profile(InstanceProfileName=worker_role, Tags=tags)
        receipt["resources"]["instance_profile"] = worker_role; save()
        iam.add_role_to_instance_profile(InstanceProfileName=worker_role,RoleName=worker_role)
        timer_arn = role(timer_role,"scheduler.amazonaws.com",[{"Effect":"Allow","Action":"ec2:TerminateInstances","Resource":f"arn:aws:ec2:{plan['region']}:{plan['account_id']}:instance/*","Condition":{"StringEquals":{"ec2:ResourceTag/cas_meta_job":job}}}])
        sg = ec2.create_security_group(GroupName=job, Description="CAS-META-2 outbound HTTPS only", VpcId=subnet["VpcId"], TagSpecifications=[{"ResourceType":"security-group","Tags":tags}])["GroupId"]
        receipt["resources"]["security_group"] = sg; save()
        ec2.revoke_security_group_egress(GroupId=sg,IpPermissions=[{"IpProtocol":"-1","IpRanges":[{"CidrIp":"0.0.0.0/0"}]}])
        ec2.authorize_security_group_egress(GroupId=sg,IpPermissions=[{"IpProtocol":"tcp","FromPort":443,"ToPort":443,"IpRanges":[{"CidrIp":"0.0.0.0/0"}]}])
        s3.upload_file(str(Path(args.archive).resolve()),bucket,"input/payload.zip")
        validate_prior_packet(Path(args.prior_packet),manifest)
        s3.upload_file(str(Path(args.prior_packet).resolve()),bucket,"input/prior_packet.zip")
        config = {**plan,"prior_packet":prior_packet,"job":job,"bucket":bucket,"archive_sha256":args.sha256,"manifest":manifest,"smoke_only":bool(args.smoke_only)}
        # Put the complete manifest outside EC2's 16KiB user-data limit.
        remote = remote_program(config)
        s3.put_object(Bucket=bucket,Key="input/remote.py",Body=remote.encode())
        script_sha = hashlib.sha256(remote.encode()).hexdigest()
        bootstrap = user_data(config,script_sha)
        if len(bootstrap.encode()) > 16384: raise LaunchRefused("EC2_USER_DATA_SIZE_CEILING")
        record("BOOTSTRAP_PINNED",sha256=hashlib.sha256(bootstrap.encode()).hexdigest(),remote_sha256=script_sha)
        time.sleep(10) # IAM propagation, not a retry of a job.
        launch_time = datetime.now(timezone.utc)
        deadline = launch_time + timedelta(seconds=plan["runtime_seconds_max"])
        launch_attempted = True
        receipt["run_instances_client_token"] = job
        record("INSTANCE_LAUNCH_ATTEMPTED",client_token=job)
        launched = ec2.run_instances(ImageId=plan["ami_id"],InstanceType=plan["instance_type"],MinCount=1,MaxCount=1,ClientToken=job,IamInstanceProfile={"Name":worker_role},InstanceInitiatedShutdownBehavior="terminate",MetadataOptions={"HttpTokens":"required","HttpEndpoint":"enabled"},NetworkInterfaces=[{"DeviceIndex":0,"SubnetId":args.subnet_id,"Groups":[sg],"AssociatePublicIpAddress":True,"DeleteOnTermination":True}],BlockDeviceMappings=[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":75,"VolumeType":"gp3","Encrypted":True,"DeleteOnTermination":True}}],TagSpecifications=[{"ResourceType":"instance","Tags":tags},{"ResourceType":"volume","Tags":tags}],UserData=bootstrap)
        iid = launched["Instances"][0]["InstanceId"]
        receipt["provider_launch_time"] = launched["Instances"][0].get("LaunchTime",launch_time).isoformat()
        receipt["resources"]["instance"] = iid; record("INSTANCE_CREATED",instance_id=iid,deadline=deadline.isoformat())
        target = {"Arn":"arn:aws:scheduler:::aws-sdk:ec2:terminateInstances","RoleArn":timer_arn,"Input":json.dumps({"InstanceIds":[iid]}),"RetryPolicy":{"MaximumRetryAttempts":0,"MaximumEventAgeInSeconds":60}}
        expression = "at("+deadline.strftime("%Y-%m-%dT%H:%M:%S")+")"
        # Record the exact name before creation so a lost response cannot orphan it.
        receipt["resources"]["schedule"] = job; save()
        scheduler.create_schedule(Name=job,ScheduleExpression=expression,ScheduleExpressionTimezone="UTC",FlexibleTimeWindow={"Mode":"OFF"},Target=target,ActionAfterCompletion="DELETE")
        confirmed = scheduler.get_schedule(Name=job)
        verify_schedule(confirmed,target,expression)
        record("CLOUD_DEADLINE_CONFIRMED",schedule=job,target=target)
        s3.put_object(Bucket=bucket,Key="input/permit.json",Body=json.dumps({"job":job,"archive_sha256":args.sha256,"cloud_deadline_confirmed":True,"deadline":deadline.isoformat()}).encode())
        while datetime.now(timezone.utc) < deadline:
            try:
                result = json.loads(s3.get_object(Bucket=bucket,Key="results/complete.json")["Body"].read())
                if result["job"] != job or not SHA256.fullmatch(result["sha256"]) or not 0 < result["bytes"] <= plan["artifact_bytes_max"]:
                    raise LaunchRefused("REMOTE_RESULT_IDENTITY_OR_SIZE")
                if result.get("smoke_only") is not bool(args.smoke_only):
                    raise LaunchRefused("REMOTE_RESULT_MODE_MISMATCH")
                head = s3.head_object(Bucket=bucket,Key="results/artifacts.zip")
                if head["ContentLength"] != result["bytes"]: raise LaunchRefused("REMOTE_RESULT_SIZE_MISMATCH")
                artifact = output / "cloud_artifacts.zip"
                s3.download_file(bucket,"results/artifacts.zip",str(artifact))
                collection = verify_downloaded_packet(artifact,result,job,args.source_sha,plan,experiment=experiment)
                artifact_verified = True
                receipt["result"] = result
                receipt["artifact_collection"] = collection
                receipt["status"] = "AWS_JOB_FINISHED" if result["returncode"] == 0 else "AWS_JOB_FAILED"
                record("ARTIFACT_DOWNLOADED_AND_HASH_VERIFIED",path=str(artifact),sha256=result["sha256"])
                break
            except ClientError as exc:
                if exc.response["Error"]["Code"] not in ("NoSuchKey","404"): raise
            state = ec2.describe_instances(InstanceIds=[iid])["Reservations"][0]["Instances"][0]["State"]["Name"]
            if state in ("terminated","shutting-down"):
                raise LaunchRefused("INSTANCE_ENDED_WITHOUT_COMPLETION_RECEIPT")
            time.sleep(15)
        else: raise LaunchRefused("LOCAL_WATCHDOG_DEADLINE")
    except BaseException as exc:
        receipt["status"] = "AWS_JOB_BLOCKED_OR_FAILED"
        record("ERROR",error=type(exc).__name__,message=str(exc))
    finally:
        # A missing RunInstances response is not evidence that no instance exists.
        terminated = not launch_attempted
        if launch_attempted and iid is None:
            try:
                recovered = reconcile_instance(ec2,job)
                iid = recovered["InstanceId"]
                receipt["resources"]["instance"] = iid
                receipt["provider_launch_time"] = recovered["LaunchTime"].isoformat()
                record("INSTANCE_IDENTITY_RECOVERED",instance_id=iid,client_token=job)
            except Exception as exc:
                receipt["cleanup_errors"].append("TERMINATION_UNCONFIRMED: "+str(exc))
                record("INSTANCE_IDENTITY_UNCONFIRMED_RESOURCES_RETAINED")
        if iid:
            try:
                terminate_owned_instance(ec2,iid,job,artifact_verified=artifact_verified,record=record)
                terminated = True; record("INSTANCE_TERMINATION_CONFIRMED",instance_id=iid)
                seconds = (datetime.now(timezone.utc)-datetime.fromisoformat(receipt["provider_launch_time"])).total_seconds()
                receipt["cost_estimate"] = {"instance_wall_clock_seconds_upper_observation":seconds,"compute_ebs_ipv4_usd_estimate":str((Decimal(str(seconds))/Decimal(3600))*(Decimal(plan['on_demand_hourly_usd_max'])+Decimal(75)*Decimal("0.08")/Decimal(720)+Decimal("0.005"))),"excluded":"S3 requests and retention, transfer, taxes; not an AWS invoice"}
            except Exception as exc: receipt["cleanup_errors"].append("TERMINATION_UNCONFIRMED: "+str(exc))
        if terminated:
            if iid:
                try:
                    receipt["remaining_job_volumes"] = confirm_deleted_volumes(ec2,job,record)
                    if receipt["remaining_job_volumes"]: receipt["cleanup_errors"].append("EBS_DELETION_NOT_YET_CONFIRMED")
                except Exception as exc: receipt["cleanup_errors"].append("EBS_CHECK_FAILED: "+str(exc))
            remove_owned_auxiliary_resources(ec2,iam,scheduler,receipt,job,worker_role,timer_role,record)
            save()
        if "bucket" in receipt["resources"]:
            try:
                head = s3.head_object(Bucket=bucket,Key="results/bootstrap.log")
                if head["ContentLength"] > 1048576: raise LaunchRefused("BOOTSTRAP_LOG_CEILING")
                bootstrap_log = output / "bootstrap.log"
                s3.download_file(bucket,"results/bootstrap.log",str(bootstrap_log))
                receipt["bootstrap_log_sha256"] = digest(bootstrap_log)
            except ClientError as exc:
                receipt["bootstrap_log_status"] = exc.response["Error"]["Code"]
            except Exception as exc:
                receipt["bootstrap_log_status"] = type(exc).__name__ + ": " + str(exc)
        receipt["termination_confirmed"] = terminated
        if terminated and "bucket" in receipt["resources"]:
            try:
                check_tag(s3.get_bucket_tagging(Bucket=bucket)["TagSet"],job)
                if artifact_verified:
                    s3.delete_objects(Bucket=bucket,Delete={"Objects":[{"Key":"input/"+key} for key in ("payload.zip","remote.py","permit.json","prior_packet.zip")]})
                    record("OWNED_SOURCE_INPUT_OBJECTS_REMOVED_AFTER_VERIFIED_DOWNLOAD")
                result_objects = s3.list_objects_v2(Bucket=bucket,Prefix="results/")
                keys = [item["Key"] for item in result_objects.get("Contents",[])]
                if result_objects.get("IsTruncated") or not set(keys).issubset({"results/artifacts.zip","results/complete.json","results/bootstrap.log"}) or len(keys)>3:
                    raise LaunchRefused("UNEXPECTED_RESULT_OBJECTS")
                if sum(item["Size"] for item in result_objects.get("Contents",[])) > plan["artifact_bytes_max"]:
                    raise LaunchRefused("RESULT_OBJECT_TOTAL_SIZE_CEILING")
                receipt["stored_result_objects"] = result_objects.get("Contents",[])
            except Exception as exc:
                receipt["cleanup_errors"].append("S3_RETENTION_OR_OBJECT_LIMIT_UNCONFIRMED: "+str(exc))
        receipt["s3_retention"] = "Dedicated job bucket objects expire after 7 days; empty bucket may remain without storage charges. Local evidence is retained."
        if receipt["cleanup_errors"]: receipt["status"] = "CLEANUP_REQUIRES_ATTENTION"
        save()
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--smoke-only", action="store_true")
    parser.add_argument("--archive")
    parser.add_argument("--sha256")
    parser.add_argument("--source-sha")
    parser.add_argument("--prior-packet")
    parser.add_argument("--approved-cap-usd")
    parser.add_argument("--profile", default="default")
    parser.add_argument("--subnet-id")
    parser.add_argument("--receipt-dir")
    args = parser.parse_args(argv)
    plan = json.loads(PLAN_FILE.read_text(encoding="utf-8"))
    try:
        manifest = None
        if args.archive:
            manifest = validate_archive(Path(args.archive),args.sha256 or "",args.source_sha or "",plan)
        if manifest is not None:
            if not args.prior_packet: raise LaunchRefused("PINNED_PRIOR_PACKET_REQUIRED")
            validate_prior_packet(Path(args.prior_packet),manifest)
        if not args.execute:
            print(json.dumps({"plan":plan,"archive_verified":manifest is not None,"aws_actions_performed":False},indent=2)); return 0
        validate_approval(args.approved_cap_usd,plan)
        if manifest is None or not args.receipt_dir:
            raise LaunchRefused("PINNED_ARCHIVE_AND_RECEIPT_DIRECTORY_REQUIRED")
        receipt = execute(args,plan,manifest)
        print(json.dumps({"status":receipt["status"],"receipt_dir":args.receipt_dir},indent=2))
        return 0 if receipt["status"] == "AWS_JOB_FINISHED" else 1
    except (LaunchRefused,budget.BudgetRefused,KeyError,OSError,zipfile.BadZipFile,json.JSONDecodeError) as exc:
        print(json.dumps({"status":"LAUNCH_REFUSED","reason":str(exc)})); return 2


if __name__ == "__main__":
    raise SystemExit(main())
