"""Freeze new package-only AWS job from original immutable validation payload."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import tarfile
import uuid
import xml.etree.ElementTree as ET
import zipfile

HERE = Path(__file__).resolve().parent
SOURCE = "a5fcf527b5f2c47a3a9b1f170977c55371845af0"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def freeze(prior, provider_file):
    old_freeze_raw = (prior / "freeze.json").read_bytes()
    old = json.loads(old_freeze_raw)
    if old["schema"] != "helm.validation.aws.freeze/1" or old["source_commit"] != SOURCE or old["expected_tests"] != 41:
        raise ValueError("ORIGINAL_41_TEST_SOURCE_REQUIRED")
    if sha(old_freeze_raw) != (prior / "freeze.sha256").read_text().strip():
        raise ValueError("ORIGINAL_FREEZE_HASH")
    payload_raw = (prior / "payload.zip").read_bytes()
    if sha(payload_raw) != old["payload_sha256"] or len(payload_raw) != old["payload_bytes"]:
        raise ValueError("ORIGINAL_PAYLOAD_HASH")
    terminal_raw = (prior / "evidence/terminal.json").read_bytes()
    terminal = json.loads(terminal_raw)
    archive_raw = (prior / "evidence/outputs.tar.gz").read_bytes()
    if sha(archive_raw) != terminal["sha256"] or len(archive_raw) != terminal["bytes"] or terminal["source_commit"] != SOURCE:
        raise ValueError("ORIGINAL_RESULTS_ARCHIVE_HASH")
    public_proof = {}
    with tarfile.open(prior / "evidence/outputs.tar.gz") as archive:
        for name in ("terminal_test_receipt.json", "pytest.xml", "focused_tests.stdout", "focused_tests.stderr"):
            member = archive.getmember(name)
            if not member.isfile() or member.size > 4 * 1024 * 1024:
                raise ValueError("PUBLIC_PROOF_MEMBER_BOUND")
            public_proof[name] = archive.extractfile(member).read()
    test_receipt = json.loads(public_proof["terminal_test_receipt.json"])
    if sha(public_proof["terminal_test_receipt.json"]) != terminal["test_receipt_sha256"] or test_receipt["source_commit"] != SOURCE:
        raise ValueError("PRIOR_TEST_RECEIPT_HASH")
    if test_receipt["error"] != "EXPECTED_41_PASS_WITHOUT_SKIPS":
        raise ValueError("ONLY_KNOWN_WRAPPER_COUNT_FALSE_NEGATIVE_ACCEPTED")
    test_command = next(row for row in test_receipt["commands"] if row["name"] == "focused_tests")
    if test_command["returncode"] != 0:
        raise ValueError("TEST_COMMAND_DID_NOT_PASS")
    for suffix in ("stdout", "stderr"):
        raw = public_proof["focused_tests." + suffix]
        if test_command[suffix]["sha256"] != sha(raw) or test_command[suffix]["bytes"] != len(raw):
            raise ValueError("TEST_LOG_HASH")
    cases = test_receipt["test_cases"]
    if len(cases) != 41 or any(row["status"] != "PASS" for row in cases):
        raise ValueError("PRIOR_41_TEST_CASES_REQUIRED")
    groups = {}
    for row in cases:
        module = row["classname"].split(".")[1]
        groups[module] = groups.get(module, 0) + 1
    if groups != {"test_typed_pointer_deadline_routing": 8, "test_typed_pointer_critical_mass_2x": 14,
                  "test_typed_pointer_critical_mass_2x_admission": 12, "test_typed_pointer_critical_mass_update_counts": 7}:
        raise ValueError("ALL_FOUR_ORIGINAL_SUITES_REQUIRED")
    xml = ET.fromstring(public_proof["pytest.xml"])
    suites = [xml] if xml.tag == "testsuite" else list(xml.findall("testsuite"))
    totals = {key: sum(int(s.attrib.get(key, 0)) for s in suites) for key in ("tests", "failures", "errors", "skipped")}
    if totals != {"tests": 47, "failures": 0, "errors": 0, "skipped": 0}:
        raise ValueError("PRIOR_JUNIT_SUCCESS_REQUIRED")
    if sum(len(s.findall("testcase")) for s in suites) != 41:
        raise ValueError("PRIOR_TEST_CASE_ELEMENTS_REQUIRED")
    if "41 passed, 6 subtests passed" not in public_proof["focused_tests.stdout"].decode():
        raise ValueError("EXACT_PRIOR_TEST_COMPLETION_REQUIRED")
    directive = (prior / "owner_directive.md").read_bytes()
    if sha(directive) != old["owner_directive_sha256"]:
        raise ValueError("OWNER_DIRECTIVE_HASH")
    cleanup = json.loads((prior / "execution.json").read_bytes())
    if not cleanup["cleanup_complete"] or cleanup.get("instance_terminal", {}).get("Name") != "terminated":
        raise ValueError("PRIOR_COMPUTE_CLEANUP_REQUIRED")
    provider_raw = provider_file.read_bytes()
    provider = json.loads(provider_raw)
    required_provider = ("account_id", "region", "zone", "ami", "subnet_id", "vpc_id", "root_device")
    if any(not provider.get(key) for key in required_provider) or provider["account_id"] != "807562639912" or provider["region"] != "us-west-2":
        raise ValueError("CURRENT_PUBLIC_PROVIDER_IDENTITIES_REQUIRED")
    with zipfile.ZipFile(prior / "payload.zip") as archive:
        original_manifest_raw = archive.read("payload_manifest.json")
        if sha(original_manifest_raw) != old["payload_manifest_sha256"]:
            raise ValueError("ORIGINAL_MANIFEST_HASH")
        manifest = json.loads(original_manifest_raw)
        payload = {}
        for row in manifest["files"]:
            name = row["path"]
            relative = Path(name)
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("UNSAFE_PAYLOAD_PATH")
            raw = archive.read(name)
            if len(raw) != row["bytes"] or sha(raw) != row["sha256"]:
                raise ValueError("ORIGINAL_PAYLOAD_MEMBER_CHANGED:" + name)
            payload[name] = raw
    if test_command["argv"][-4:] != manifest["test_files"]:
        raise ValueError("ORIGINAL_TEST_ARGV_REQUIRED")
    proof_files = []
    for name, raw in public_proof.items():
        path = "prior_test_evidence/" + name
        payload[path] = raw
        proof_files.append({"path": path, "bytes": len(raw), "sha256": sha(raw)})
    payload["prior_test_evidence/terminal.json"] = terminal_raw
    payload["prior_test_evidence/freeze.json"] = old_freeze_raw
    proof_files.extend([
        {"path": "prior_test_evidence/terminal.json", "bytes": len(terminal_raw), "sha256": sha(terminal_raw)},
        {"path": "prior_test_evidence/freeze.json", "bytes": len(old_freeze_raw), "sha256": sha(old_freeze_raw)},
    ])
    proof = {"schema": "helm.package-only.successful-tests/1", "source_commit": SOURCE,
             "original_validation_job": old["job_id"], "original_validation_freeze_sha256": sha(old_freeze_raw),
             "original_payload_sha256": sha(payload_raw), "original_results_archive_sha256": sha(archive_raw),
             "original_terminal_sha256": sha(terminal_raw), "test_case_count": 41,
             "junit_tests_including_subtests": 47, "successful_subtests": 6, "suite_counts": groups,
             "failures": 0, "errors": 0, "skipped": 0, "files": proof_files,
             "boundary": "Original worker status FAILED retained: aggregate-count wrapper false negative after 41 cases and 6 subtests passed. This job only builds the package; runs no tests or training."}
    payload["successful_tests.json"] = canonical(proof)
    for name in ("package.py", "worker.py", "launch.py"):
        payload[name] = (HERE / name).read_bytes()
    manifest["schema"] = "helm.package-only.payload/1"
    manifest["tests_to_execute"] = 0
    manifest["successful_test_proof_sha256"] = sha(payload["successful_tests.json"])
    manifest["files"] = [{"path": name, "bytes": len(raw), "sha256": sha(raw)} for name, raw in sorted(payload.items())]
    payload["payload_manifest.json"] = canonical(manifest)
    job = "helm-pkg-" + datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    directory = HERE / "jobs" / job
    directory.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(directory / "payload.zip", "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, raw in sorted(payload.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 9, 26, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, raw)
    packed = (directory / "payload.zip").read_bytes()
    if len(packed) > 64 * 1024 * 1024:
        raise ValueError("PAYLOAD_SIZE_BOUND")
    for name, raw in (("owner_directive.md", directive), ("provider_reference.json", provider_raw),
                      ("successful_tests.json", payload["successful_tests.json"])):
        (directory / name).write_bytes(raw)
    plan = {
        "schema": "helm.package-only.aws.freeze/1", "job_id": job, "runner": "Codex", "source_commit": SOURCE,
        "package_source_commit": SOURCE, "tests_to_execute": 0, "successful_prior_test_case_count": 41,
        "successful_test_proof_sha256": sha(payload["successful_tests.json"]),
        "original_validation_job": old["job_id"], "original_payload_sha256": sha(payload_raw),
        "owner_directive_sha256": sha(directive), "frozen_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        **{key: provider[key] for key in required_provider},
        "provider_reference_sha256": sha(provider_raw), "sdk_profile": provider.get("sdk_profile", "default"),
        "instance_type": "t3.small", "cpu_credits": "standard", "root_gib": 8,
        "jobs": 1, "retry_count": 0, "permitted_concurrent_instances": [],
        "worker_seconds": 360, "operator_seconds": 450, "os_shutdown_minutes": 8,
        "scheduler_after_seconds": 480, "hard_wall_seconds": 600,
        "maximum_all_services_usd": "0.10", "forecast_all_services_usd": "0.03",
        "combined_owner_attempt_cap_usd": "20.00",
        "combined_reserved_and_allowance_usd": "20.00",
        "budget_components_usd": {"training": "19.20", "original_validation": "0.60", "package_only": "0.10", "other_services": "0.10"},
        "purpose": "Finish previously unexecuted exact-source package build after verified successful prelaunch tests; no new tests, training or automatic retry",
        "payload_file": "payload.zip", "payload_sha256": sha(packed), "payload_bytes": len(packed),
        "payload_manifest_sha256": sha(payload["payload_manifest.json"]),
        "launcher_sha256": sha((HERE / "launch.py").read_bytes()),
        "worker_sha256": sha((HERE / "worker.py").read_bytes()),
        "package_builder_sha256": sha((HERE / "package.py").read_bytes()),
        "cleanup_required": True, "retain_private_evidence_archive": True,
    }
    raw = canonical(plan)
    (directory / "freeze.json").write_bytes(raw)
    (directory / "freeze.sha256").write_text(sha(raw) + "\n")
    print(json.dumps({"status": "FROZEN_NOT_LAUNCHED", "job_directory": str(directory),
                      "freeze_sha256": sha(raw), "payload_sha256": sha(packed),
                      "source_commit": SOURCE, "tests_to_execute": 0}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prior-job-directory", type=Path, required=True)
    parser.add_argument("--provider-file", type=Path, required=True)
    args = parser.parse_args()
    freeze(args.prior_job_directory, args.provider_file)
