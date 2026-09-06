"""Unpaid, offline preparation for the frozen saved-prefix CUDA worker.

No provider SDK, reservation, launch, executable worker plan or neural import.
The canonical budget reader takes its normal owned short-lived read lock; its
ledger/history contents must remain byte-identical. This is not a launcher.
"""
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
import argparse
import importlib.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "cas-meta2-prefix-launch-preparation/8"
WORKER_SOURCE_SHA = "13f424981d7434b1a92815d1ad5759d543bbd3be"
SOURCE_ARCHIVE_SHA = "c1e784440b408a81d28efd00444fe69680972b9ef6ce14b5c298598dc6e83be1"
SOURCE_ARCHIVE_BYTES = 7952045
PREFIX_MANIFEST_SHA = "10f3283e5dcb3045dac2131e021d3ca383c35ae8b34c9e439e7fc82ff58cdd9c"
BUNDLE_MANIFEST_SHA = "b4d7970ca59c07342942584e4752ad8c129c3125e25ecc241e3d76c9ddd1c629"
DEVELOPMENT_ARCHIVE_SHA = "1874508d0baad7d6620001505c39f184b3cb091c59de4e96197f309beee0a042"
DEVELOPMENT_ARCHIVE_BYTES = 6570836
BUDGET_SOURCE_SHA = "77a845ea8669b775a28a940552a9212f667a9506e5586deff64baba06a82eda0"
BUNDLE_SOURCE_SHA = "79f4a20b1d222d3269066372b9718a75bc8204ffcd2cf5a4c51a9196d5594560"
PILOT = "research/CAS_META_2_COMPOSITION/"
RESERVATION_PROPOSAL = "4.00"
MAX_ARCHIVE_BYTES = 32 * 1024 * 1024
MAX_EXPANDED_BYTES = 512 * 1024 * 1024
WORKER_KEYS = ["cas_initial", "cas_selected", "generic_initial", "generic_selected"]
MISSING_GATES = (
    "SEPARATE_OWNER_LAUNCH_APPROVAL",
    "CURRENT_AWS_PRICE_AND_COMPLETE_ANCILLARY_COST_CHECK",
    "CURRENT_GPU_CAPACITY_AMI_SUBNET_AND_NETWORK_CHECK",
    "COMPLETE_RESOURCE_PLAN_AND_BOUNDED_ARTIFACT_STORAGE_TRANSFER_PLAN",
    "REAL_UNIQUE_JOB_AND_CANONICAL_BUDGET_RESERVATION",
    "TESTED_PARENT_PROVISIONING_AND_STAGING_ORCHESTRATOR",
    "CONFIRMED_INDEPENDENT_INSTANCE_SHUTDOWN_BEFORE_WORKER_PERMISSION",
    "REAL_INSTANCE_ID_AND_SEALED_ENABLED_WORKER_PLAN",
    "INSTALLATION_IDENTITY_CUDA_PREFLIGHT_AND_RUNTIME_RECEIPTS",
    "FAILURE_PRESERVING_ARTIFACT_COLLECTION_AND_OWNED_RESOURCE_CLEANUP",
)


class PreparationRefused(ValueError):
    pass


def require(value, reason):
    if not value:
        raise PreparationRefused(reason)


def canonical(value):
    try:
        return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
    except (TypeError, ValueError, OverflowError) as error:
        raise PreparationRefused("NONFINITE_OR_INVALID_JSON") from error


def decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "DUPLICATE_JSON_KEY")
            result[key] = value
        return result
    def constant(value):
        raise PreparationRefused("NONFINITE_JSON")
    try:
        result = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
        canonical(result)
        return result
    except (json.JSONDecodeError, UnicodeError, RecursionError) as error:
        raise PreparationRefused("INVALID_JSON") from error


def digest(raw):
    return sha256(raw).hexdigest()


def no_links(path):
    path = Path(path).absolute()
    require(not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
                    for p in (path, *path.parents)), "LINK_REFUSED")
    return path


def read(path, maximum=MAX_ARCHIVE_BYTES):
    path = no_links(path)
    require(path.is_file() and path.stat().st_size <= maximum, "REGULAR_BOUNDED_FILE_REQUIRED")
    with path.open("rb") as stream:
        raw = stream.read(maximum + 1)
    require(len(raw) <= maximum, "FILE_SIZE_BOUND")
    return raw


def safe_name(name):
    require(type(name) is str and name and "\\" not in name and ":" not in name,
            "UNSAFE_ARCHIVE_PATH")
    path = PurePosixPath(name)
    require(not path.is_absolute() and path.as_posix() == name
            and all(p not in ("", ".", "..") for p in name.split("/")), "UNSAFE_ARCHIVE_PATH")
    return name


def _zip_payloads(raw, expected_count):
    """Read only in-memory checked bytes; never extract a ZIP onto the machine."""
    with ZipFile(io.BytesIO(raw)) as zipped:
        infos = zipped.infolist()
        names = [safe_name(info.filename) for info in infos]
        require(len(names) == len(set(names)) == len({name.casefold() for name in names})
                == expected_count, "ARCHIVE_COVERAGE")
        require(all(not info.is_dir() and not stat.S_ISLNK(info.external_attr >> 16)
                    and not (info.flag_bits & 1) for info in infos), "ARCHIVE_LINK_DIRECTORY_OR_ENCRYPTION")
        require(sum(info.file_size for info in infos) <= MAX_EXPANDED_BYTES, "EXPANDED_ARCHIVE_BOUND")
        return {info.filename: zipped.read(info) for info in infos}


def inspect_source_archive(path, expected_sha256=SOURCE_ARCHIVE_SHA, expected_source_sha=WORKER_SOURCE_SHA):
    require(expected_sha256 == SOURCE_ARCHIVE_SHA and expected_source_sha == WORKER_SOURCE_SHA,
            "FROZEN_DIAGNOSTIC_SOURCE_REQUIRED")
    raw = read(path)
    require(len(raw) == SOURCE_ARCHIVE_BYTES and digest(raw) == expected_sha256, "SOURCE_ARCHIVE_CHANGED")
    members = _zip_payloads(raw, 616)
    manifest_raw = members["prefix_source_manifest.json"]
    require(digest(manifest_raw) == PREFIX_MANIFEST_SHA, "PREFIX_MANIFEST_CHANGED")
    manifest = decode(manifest_raw)
    require(manifest["schema"] == "cas-meta2-prefix-source-package/8"
            and manifest["source_sha"] == expected_source_sha
            and manifest["frozen_v7_source_sha"] == "42f9164754312f12850d9b8789c062fa7fb8069f"
            and manifest["frozen_source_files"] == 603
            and manifest["protected_baseline_files"] == 316
            and manifest["addition_count"] == 11 and manifest["launch_enabled"] is False,
            "SOURCE_MANIFEST_IDENTITY")
    files = manifest["files_sha256"]
    require(type(files) is dict and len(files) == 615
            and set(members) == set(files) | {"prefix_source_manifest.json"}, "SOURCE_FILE_CLOSURE")
    for name, expected in files.items():
        safe_name(name)
        require(type(expected) is str and re.fullmatch("[0-9a-f]{64}", expected)
                and digest(members[name]) == expected, "SOURCE_MEMBER_CHANGED:" + name)
    old = decode(members["launch_manifest.json"])
    require(old["source_sha"] == manifest["frozen_v7_source_sha"]
            and old["pilot_dir"] == "research/CAS_META_2_COMPOSITION"
            and old["meta1_dir"] == "research/CAS_META_1_LEARNED_SELECTION"
            and old["meta_runtime_dir"] == "research/CASFORMER_v0_3_META_LOGIC_WIP"
            and old["dependency_lock"] == PILOT + "requirements-gpu.txt", "OLD_MANIFEST_LAYOUT_CHANGED")
    return {"path": str(no_links(path)), "sha256": expected_sha256, "bytes": len(raw),
            "source_sha": expected_source_sha, "member_count": len(members),
            "prefix_manifest_sha256": PREFIX_MANIFEST_SHA,
            "prefix_manifest_member": "prefix_source_manifest.json",
            "files_sha256": files, "package_layout": {
                "pilot_dir": old["pilot_dir"], "meta1_dir": old["meta1_dir"],
                "meta_runtime_dir": old["meta_runtime_dir"], "wheel_paths": old["wheel_paths"],
                "dependency_lock": old["dependency_lock"]}}


def _bundle_module(source):
    path = ROOT / "cas_meta2/diagnostic_v8/bundle.py"
    require(digest(read(path)) == BUNDLE_SOURCE_SHA
            and source["files_sha256"][PILOT + "cas_meta2/diagnostic_v8/bundle.py"] == BUNDLE_SOURCE_SHA,
            "FROZEN_BUNDLE_HELPER_CHANGED")
    from cas_meta2.diagnostic_v8 import bundle
    require(Path(bundle.__file__).resolve() == path.resolve(), "BUNDLE_HELPER_PATH_CHANGED")
    return bundle


def inspect_development(bundle_directory, archive_path, source,
                        expected_manifest_sha256=BUNDLE_MANIFEST_SHA,
                        expected_archive_sha256=DEVELOPMENT_ARCHIVE_SHA):
    require(expected_manifest_sha256 == BUNDLE_MANIFEST_SHA
            and expected_archive_sha256 == DEVELOPMENT_ARCHIVE_SHA, "FROZEN_DEVELOPMENT_PANEL_REQUIRED")
    module = _bundle_module(source)
    loaded = module.validate_bundle(bundle_directory, expected_manifest_sha256=expected_manifest_sha256)
    raw = read(archive_path)
    require(len(raw) == DEVELOPMENT_ARCHIVE_BYTES and digest(raw) == expected_archive_sha256,
            "DEVELOPMENT_ARCHIVE_CHANGED")
    members = _zip_payloads(raw, 16)
    wanted = {"bundle_001/" + name for name in loaded["manifest"]["files"]} | {"bundle_001/manifest.json"}
    require(set(members) == wanted, "DEVELOPMENT_ARCHIVE_LAYOUT_CHANGED")
    for member, content in members.items():
        local = no_links(bundle_directory) / member.removeprefix("bundle_001/")
        require(read(local) == content, "DEVELOPMENT_ARCHIVE_DIRECTORY_MISMATCH")
    return {"directory": str(no_links(bundle_directory)), "directory_kind": "VALIDATED_16_FILE_DIRECTORY",
            "archive_path": str(no_links(archive_path)), "archive_sha256": expected_archive_sha256,
            "archive_bytes": len(raw), "archive_member_count": 16, "archive_root_prefix": "bundle_001/",
            "manifest_sha256": expected_manifest_sha256, "limits": loaded["manifest"]["limits"],
            "cohort_counts": {name: len(tasks) for name, tasks in loaded["cohorts"].items()},
            "file_identities": {**loaded["manifest"]["files"], "manifest.json": {
                "sha256": expected_manifest_sha256, "bytes": len(read(no_links(bundle_directory) / "manifest.json"))}},
            "checkpoints_deserialized": False, "final_task_files_included": False}


def _budget_module():
    path = ROOT / "aws/budget.py"
    require(digest(read(path)) == BUDGET_SOURCE_SHA, "CANONICAL_BUDGET_HELPER_CHANGED")
    spec = importlib.util.spec_from_file_location("cas_meta2_prefix_readonly_budget_v8", path)
    require(spec is not None and spec.loader is not None, "BUDGET_HELPER_UNAVAILABLE")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _budget_files(module):
    ledger, _, history = module.paths(module.CANONICAL_LEDGER)
    ledger, history = no_links(ledger), no_links(history)
    require(ledger.is_file() and history.is_dir(), "CANONICAL_BUDGET_NOT_INITIALIZED")
    raw = read(ledger)
    state = decode(raw)
    files = {str(ledger): digest(raw)}
    for item in sorted(history.iterdir()):
        item = no_links(item)
        require(re.fullmatch("[0-9]{8}[.]json", item.name), "BUDGET_HISTORY_FILE_INVALID")
        files[str(item)] = digest(read(item))
    for name in ("approval", "predecessor"):
        binding = state[name]
        require(type(binding["path"]) is str and Path(binding["path"]).is_absolute(),
                "BUDGET_EVIDENCE_ABSOLUTE_PATH_REQUIRED")
        files[str(no_links(binding["path"]))] = digest(read(binding["path"]))
    return files


def observe_budget():
    """Validated canonical history; no reservation and no state/history change."""
    module = _budget_module()
    before = _budget_files(module)
    state = module.read_ledger(module.CANONICAL_LEDGER)
    after = _budget_files(module)
    require(before == after, "BUDGET_CHANGED_DURING_OBSERVATION")
    ledger_path = str(no_links(module.CANONICAL_LEDGER))
    require(module.digest(module.encoded(state)) == before[ledger_path], "BUDGET_SERIALIZATION_MISMATCH")
    return {"ledger_path": ledger_path, "ledger_sha256": before[ledger_path],
            "revision": state["revision"], "campaign_cap_usd": state["owner_task_cap_usd"],
            "total_reserved_usd": state["total_reserved_usd"],
            "remaining_unreserved_usd": state["remaining_unreserved_usd"],
            "checked_file_sha256": before, "contents_unchanged": True,
            "temporary_owned_read_lock_used": True, "new_reservation": False,
            "history_chain_validated": True}


def resource_proposal():
    plan = {"instance_count": 1, "instance_type": "g7.2xlarge",
            "account_id": "807562639912", "region": "us-west-2",
            "runtime_seconds_max": 3600, "automatic_retries": 0,
            "on_demand_hourly_usd_max": "2.52", "ancillary_reserved_usd": "1.00"}
    module = _budget_module()
    bound = module.validate_plan(plan, RESERVATION_PROPOSAL)
    require(bound == Decimal("3.52"), "PLANNING_BOUND_CHANGED")
    return {"resource_plan": plan, "proposed_reservation_usd": RESERVATION_PROPOSAL,
            "arithmetic_cost_bound_usd": str(bound), "worker_seconds_max": 1800,
            "required_gpu_name_contains": "RTX PRO 4500", "price_checked": False,
            "price_basis": "PLANNING_CEILING_NOT_CURRENT_QUOTE",
            "ancillary_allowance_completeness_verified": False,
            "full_provisioning_plan_completed": False, "provider_cap_enforced": False}


def worker_plan_draft(source, development, proposal):
    """Deliberately fails frozen gpu.plan_bounds: no enabled or invented plan."""
    return {"schema": "cas-meta2-prefix-diagnostic-plan/8", "launch_enabled": False,
            "job": None, "instance_id": None, "source_sha": source["source_sha"],
            "bundle_manifest_sha256": development["manifest_sha256"],
            "max_seconds": 1800, "batch_size": 16, "tasks_per_checkpoint": 120, "seed": 7,
            "checkpoints": WORKER_KEYS, "max_cost_usd": RESERVATION_PROPOSAL,
            "resource_plan": proposal["resource_plan"],
            "source_manifest": {"path": None, "sha256": source["prefix_manifest_sha256"]},
            "source_archive": {"path": None, "sha256": source["sha256"]},
            "reservation_receipt": None, "ledger_snapshot": None,
            "draft_only": True, "missing_fields_must_come_from_real_parent_execution": [
                "job", "instance_id", "source_manifest.path", "source_archive.path",
                "reservation_receipt", "ledger_snapshot"]}


def command_template(source, development):
    return {"kind": "NON_EXECUTABLE_TYPED_ARGUMENT_TEMPLATE",
            "argv": ["python", "-B", "-m", "cas_meta2.diagnostic_v8.gpu",
                     "--bundle", {"slot": "remote_bundle_directory"},
                     "--output", {"slot": "new_worker_output_directory"},
                     "--job", {"slot": "reserved_unique_job"},
                     "--manifest-sha256", development["manifest_sha256"],
                     "--plan", {"slot": "sealed_enabled_worker_plan_path"},
                     "--plan-sha256", {"slot": "sealed_enabled_worker_plan_sha256"}],
            "environment_required_later": {"CAS_META2_RUN_PREFIX_DIAGNOSTIC": "1",
                                          "CAS_META2_AWS_JOB_ID": {"slot": "reserved_unique_job"}},
            "cwd": {"slot": "extracted_package_root", "suffix": source["package_layout"]["pilot_dir"]},
            "path_constraints": {
                "remote_bundle_directory": "Linux absolute directory containing the extracted bundle_001/ contents, not the ZIP path.",
                "new_worker_output_directory": "Nonexistent child at a Linux absolute path below extracted research/CAS_META_2_COMPOSITION/runs; not runs itself.",
                "source_manifest": "Linux absolute path; prefix_source_manifest.json must remain at extracted package root.",
                "source_archive": "Linux absolute path. Retain the exact source ZIP through the worker's final source_closure check.",
                "reservation_receipt": "Linux absolute path to the real parent reservation receipt, with its exact SHA-256.",
                "ledger_snapshot": "Linux absolute path to the real reserved ledger snapshot, with its exact SHA-256.",
                "sealed_enabled_worker_plan_path": "Linux absolute path; seal only after the actual instance identity exists.",
                "python_package_roots": [source["package_layout"][name] for name in ("pilot_dir", "meta1_dir", "meta_runtime_dir")]},
            "installs_required_later": {"python_allowed_versions": ["3.11", "3.12"],
                "torch": "2.11.0+cu128", "cuda_runtime": "12.8",
                "torch_index": "https://download.pytorch.org/whl/cu128",
                "requirements_member": source["package_layout"]["dependency_lock"],
                "wheel_members": source["package_layout"]["wheel_paths"],
                "resolved_environment_receipt_required": True},
            "local_execution_permitted": False, "shell_command_generated": False}


def prepare(source_archive, development_bundle, development_archive, output, *,
            expected_source_sha256=SOURCE_ARCHIVE_SHA, expected_source_sha=WORKER_SOURCE_SHA,
            expected_bundle_manifest_sha256=BUNDLE_MANIFEST_SHA,
            expected_development_archive_sha256=DEVELOPMENT_ARCHIVE_SHA):
    output = no_links(output)
    require(not output.exists() and output.resolve().is_relative_to((ROOT / "records").resolve())
            and output.resolve() != (ROOT / "records").resolve(), "NEW_IN_SCOPE_PREPARATION_OUTPUT_REQUIRED")
    adapter_before = digest(read(Path(__file__)))
    source = inspect_source_archive(source_archive, expected_source_sha256, expected_source_sha)
    development = inspect_development(development_bundle, development_archive, source,
        expected_bundle_manifest_sha256, expected_development_archive_sha256)
    budget = observe_budget()
    proposal = resource_proposal()
    require(Decimal(budget["remaining_unreserved_usd"]) >= Decimal(RESERVATION_PROPOSAL),
            "CAPACITY_BELOW_PROPOSED_RESERVATION")
    draft = worker_plan_draft(source, development, proposal)
    template = command_template(source, development)
    require(digest(read(source_archive)) == source["sha256"]
            and digest(read(development_archive)) == development["archive_sha256"]
            and digest(read(Path(__file__))) == adapter_before, "INPUT_CHANGED_DURING_PREPARATION")
    report = {"schema": SCHEMA, "status": "PREPARATION_ONLY_NO_PAID_LAUNCH",
        "launch_enabled": False, "execution_ready": False, "worker_source_sha": WORKER_SOURCE_SHA,
        "adapter_sha256": adapter_before, "observed_utc": datetime.now(timezone.utc).isoformat(),
        "source_archive": source, "development_bundle": development,
        "budget_observation": budget, "resource_proposal": proposal,
        "remaining_unreserved_if_later_reserved_usd": str(Decimal(budget["remaining_unreserved_usd"]) - Decimal(RESERVATION_PROPOSAL)),
        "worker_plan_draft": draft, "command_template": template, "missing_gates": list(MISSING_GATES),
        "boundary": {"new_reservation": False, "provider_calls": False,
            "neural_imports_or_execution": False, "native_execution": False,
            "job_created": False, "instance_identity_observed": False, "source_or_bundle_changed": False,
            "proposal_is_not_price_quote": True, "paid_parent_orchestration_implemented": False,
            "no_retry_or_deadline_extension": True,
            "budget_observation_not_launch_authority": True}}
    output.mkdir(parents=True, exist_ok=False)
    written = {}
    for name, value in (("preparation.json", report), ("worker_plan_draft.json", draft),
                        ("command_template.json", template)):
        raw = canonical(value)
        path = output / name
        with path.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        require(read(path) == raw, "PREPARATION_WRITE_MISMATCH")
        written[name] = {"bytes": len(raw), "sha256": digest(raw)}
    return {"status": report["status"], "output": str(output), "files": written,
            "launch_enabled": False, "new_reservation": False,
            "budget_revision": budget["revision"], "remaining_unreserved_usd": budget["remaining_unreserved_usd"],
            "missing_gates": report["missing_gates"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--source-archive", required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--development-bundle", required=True)
    parser.add_argument("--development-archive", required=True)
    parser.add_argument("--bundle-manifest-sha256", required=True)
    parser.add_argument("--development-archive-sha256", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    result = prepare(args.source_archive, args.development_bundle, args.development_archive, args.output,
        expected_source_sha256=args.source_sha256, expected_source_sha=args.source_sha,
        expected_bundle_manifest_sha256=args.bundle_manifest_sha256,
        expected_development_archive_sha256=args.development_archive_sha256)
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
