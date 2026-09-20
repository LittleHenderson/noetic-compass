"""Byte-preserving prior-state package, not permission or proof of CUDA restore.

The validator has only standard-library dependencies and can be imported under
a private support-module name outside the unchanged neural worker package.
"""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re
import stat
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

SCHEMA = "cas-teaching-prior-state/1"
ORIGINAL_ROOT = "/opt/cas-teaching/job/train/campaign"
SUMMARY_PATH = "train/campaign_summary.json"
ARMS = ("cas.aligned", "cas.ordinary", "generic.aligned", "generic.ordinary")
BYTE_LIMIT = 2684354560
MEMBER_LIMIT = 20000
FILE_LIMIT = 64 * 1024**2
JSON_LIMIT = 32 * 1024**2
MANIFEST_LIMIT = 4 * 1024**2
ROOT = Path(__file__).resolve().parents[2]
PIN_FIELDS = ("source_sha256", "bundle_manifest_sha256", "source_archive_sha256",
    "material_receipt_sha256", "summary_sha256", "parent_sha256", "complete_sha256",
    "prior_result_archive_sha256", "inspection_sha256", "training_cases_sha256",
    "development_cases_sha256", "profile_sha256")
ARM_FIELDS = ("run_id", "committed_cursor", "committed_optimizer_steps",
    "committed_transactions", "checkpoint_file_sha256", "checkpoint_state_sha256",
    "checkpoint_receipt_sha256", "pending_development")
PROFILE = {"version": 2, "batch_size": 32, "seed": 7,
    "training_cases_count": 256, "development_cases_count": 64,
    "allocation": {"minimum_full_cycles": 1024, "maximum_cycles": 4096,
        "development_interval": 256, "consistent_checks": 3,
        "readiness_accuracy": 0.9, "minimum_unique_families": 256,
        "minimum_cycles_per_family": 4, "development_cases_count": 64}}
BOUNDARY = ("Exact prior bytes and pure structural checks only. CUDA/optimizer restoration "
    "is untested. No launch, reservation, new learning or final evaluation is authorized.")


class PackageError(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise PackageError("TEACHING_PRIOR_STATE:" + reason)


def canonical(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=True, allow_nan=False).encode("utf-8")
    except (ValueError, TypeError, RecursionError) as error:
        raise PackageError("TEACHING_PRIOR_STATE:INVALID_OR_NONFINITE_JSON") from error


def decode(raw):
    require(type(raw) is bytes and 0 < len(raw) <= JSON_LIMIT, "JSON_BYTE_BOUND")
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "DUPLICATE_JSON_KEY")
            result[key] = value
        return result
    def nonfinite(value):
        raise PackageError("TEACHING_PRIOR_STATE:NONFINITE_JSON")
    try:
        result = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=nonfinite)
        canonical(result)  # Also rejects numeric literals which overflow to infinity.
        return result
    except (ValueError, UnicodeError, RecursionError) as error:
        if isinstance(error, PackageError):
            raise
        raise PackageError("TEACHING_PRIOR_STATE:INVALID_JSON") from error


def _pin(value):
    require(type(value) is str and re.fullmatch(r"[a-f0-9]{64}", value)
            and value != "0" * 64, "EXTERNAL_DIGEST_REQUIRED")
    return value


def _safe(path):
    path = Path(path).absolute()
    require(".." not in path.parts, "PARENT_PATH_REJECTED")
    require(not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
                    for p in (path, *path.parents)), "LINK_PATH_REJECTED")
    return path


def _file(path, limit=BYTE_LIMIT):
    path = _safe(path)
    observed = path.stat()
    require(stat.S_ISREG(observed.st_mode) and observed.st_nlink == 1
            and 0 < observed.st_size <= limit, "REGULAR_SINGLE_LINK_BOUNDED_FILE_REQUIRED")
    return path, observed.st_size


def file_identity(path, limit=BYTE_LIMIT):
    path, size = _file(path, limit)
    digest, count = sha256(), 0
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            count += len(chunk)
            require(count <= size, "FILE_GREW_DURING_READ")
            digest.update(chunk)
    require(count == size, "FILE_SIZE_CHANGED")
    return {"sha256": digest.hexdigest(), "bytes": size}


def _pinned_json(path, expected, limit=JSON_LIMIT):
    path, size = _file(path, limit)
    with path.open("rb") as stream:
        raw = stream.read(size + 1)
    require(len(raw) == size and sha256(raw).hexdigest() == _pin(expected), "JSON_PIN_MISMATCH")
    return raw, decode(raw)


def _member_name(name):
    if name == SUMMARY_PATH:
        return True
    arm = r"(?:cas|generic)\.(?:aligned|ordinary)"
    tail = (r"(?:events/step-[0-9]{8}\.(?:intent|result)\.json|"
            r"journal/(?:journal\.json|txn-[0-9]{8}/(?:candidate\.pt|metadata\.json|receipt\.json)))")
    return type(name) is str and re.fullmatch(r"train/campaign/" + arm + "/" + tail, name) is not None


def _check_manifest(document, expected_bindings):
    fields = {"schema", "logical_run_id", "original_campaign_root", "summary_path",
              "profile", "members", "arms", "expanded_bytes", "boundary", *PIN_FIELDS}
    require(type(document) is dict and set(document) == fields and document["schema"] == SCHEMA,
            "MANIFEST_SCHEMA_INVALID")
    require(document["original_campaign_root"] == ORIGINAL_ROOT and document["summary_path"] == SUMMARY_PATH,
            "ORIGINAL_PATH_MISMATCH")
    require(type(document["logical_run_id"]) is str
            and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}", document["logical_run_id"]), "RUN_ID_INVALID")
    for key in PIN_FIELDS:
        _pin(document[key])
    require(canonical(document["profile"]) == canonical(PROFILE)
            and sha256(canonical(document["profile"])).hexdigest() == document["profile_sha256"],
            "FROZEN_PROFILE_MISMATCH")
    require(document["boundary"] == BOUNDARY, "CLAIM_BOUNDARY_CHANGED")
    if expected_bindings is not None:
        require(type(expected_bindings) is dict and bool(expected_bindings)
                and set(expected_bindings) <= set(PIN_FIELDS) | {"logical_run_id", "original_campaign_root"},
                "EXPECTED_BINDINGS_INVALID")
        require(all(document.get(key) == value for key, value in expected_bindings.items()),
                "EXTERNAL_BINDING_MISMATCH")
    members = document["members"]
    require(type(members) is dict and 1 < len(members) < MEMBER_LIMIT and SUMMARY_PATH in members,
            "MEMBER_COUNT_OR_SUMMARY_INVALID")
    names, total = set(), 0
    for name, entry in members.items():
        require(_member_name(name) and name.casefold() not in names, "MEMBER_PATH_OR_COLLISION")
        names.add(name.casefold())
        require(type(entry) is dict and set(entry) == {"bytes", "sha256"}
                and type(entry["bytes"]) is int and 0 < entry["bytes"] <= FILE_LIMIT, "MEMBER_FIELDS_INVALID")
        _pin(entry["sha256"])
        total += entry["bytes"]
    require(type(document["expanded_bytes"]) is int and document["expanded_bytes"] == total
            and total <= BYTE_LIMIT - MANIFEST_LIMIT, "EXPANDED_BYTE_BOUND")
    require(members[SUMMARY_PATH]["sha256"] == document["summary_sha256"], "SUMMARY_DIGEST_MISMATCH")
    require(type(document["arms"]) is dict and set(document["arms"]) == set(ARMS), "FOUR_ARMS_REQUIRED")
    required_members = {SUMMARY_PATH}
    for arm, row in document["arms"].items():
        require(type(row) is dict and set(row) == set(ARM_FIELDS), "ARM_FIELDS_INVALID")
        family, curriculum = arm.split(".")
        require(row["run_id"] == document["logical_run_id"] + "." + curriculum + "." + family,
                "ARM_RUN_ID_MISMATCH")
        cursor = row["committed_cursor"]
        require(type(cursor) is dict and set(cursor) == {"epoch", "batch", "stage"}
                and all(type(value) is int for value in cursor.values())
                and 0 <= cursor["epoch"] < 16 and 0 <= cursor["batch"] < 8 and 0 <= cursor["stage"] < 7,
                "INCOMPLETE_16_EPOCH_CURSOR_REQUIRED")
        require(type(row["committed_optimizer_steps"]) is int
                and row["committed_optimizer_steps"] == cursor["epoch"] * 56 + cursor["batch"] * 7 + cursor["stage"]
                and type(row["committed_transactions"]) is int and 1 <= row["committed_transactions"] <= 64
                and type(row["pending_development"]) is bool, "COMMITTED_COUNTS_INVALID")
        for key in ("checkpoint_file_sha256", "checkpoint_state_sha256", "checkpoint_receipt_sha256"):
            _pin(row[key])
        prefix = f"train/campaign/{arm}/journal/txn-{row['committed_transactions']:08d}/"
        require(members.get(prefix + "candidate.pt", {}).get("sha256") == row["checkpoint_file_sha256"]
                and members.get(prefix + "receipt.json", {}).get("sha256") == row["checkpoint_receipt_sha256"]
                and prefix + "metadata.json" in members and f"train/campaign/{arm}/journal/journal.json" in members,
                "LATEST_CHECKPOINT_MEMBER_MISMATCH")
        required_members.add(f"train/campaign/{arm}/journal/journal.json")
        required_members.update(f"train/campaign/{arm}/journal/txn-{number:08d}/{filename}"
            for number in range(1, row["committed_transactions"] + 1)
            for filename in ("candidate.pt", "metadata.json", "receipt.json"))
        required_members.update(f"train/campaign/{arm}/events/step-{number:08d}.{kind}.json"
            for number in range(1, row["committed_optimizer_steps"] + 1) for kind in ("intent", "result"))
    require(set(members) == required_members, "COMPLETE_COMMITTED_INVENTORY_REQUIRED")


def _check_summary(summary, manifest):
    require(type(summary) is dict and summary.get("schema") == "cas-teaching-four-arm-campaign/1"
            and summary.get("all_allocations_finished") is False
            and summary.get("run_id") == manifest["logical_run_id"]
            and summary.get("campaign_root") == ORIGINAL_ROOT
            and summary.get("source_sha256") == manifest["source_sha256"]
            and summary.get("manifest_sha256") == manifest["bundle_manifest_sha256"]
            and set(summary.get("arms", {})) == set(ARMS), "INCOMPLETE_CAMPAIGN_IDENTITY_MISMATCH")
    for arm, expected in manifest["arms"].items():
        row = summary["arms"][arm]
        require(row.get("run_id") == expected["run_id"] and row.get("max_epochs") == 16
                and row.get("allocation_finished") is False and row.get("execution_mode") == "cuda"
                and row.get("cursor") == row.get("committed_cursor") == expected["committed_cursor"]
                and row.get("observed_optimizer_steps") == expected["committed_optimizer_steps"]
                and row.get("uncommitted_recorded_optimizer_steps") == 0,
                "SUMMARY_ARM_COMMITMENT_MISMATCH")
        ref = row.get("last_checkpoint", {})
        require(ref.get("transaction") == expected["committed_transactions"]
                and ref.get("sha256") == expected["checkpoint_file_sha256"]
                and ref.get("state_sha256") == expected["checkpoint_state_sha256"]
                and ref.get("receipt_sha256") == expected["checkpoint_receipt_sha256"]
                and ref.get("path") == ORIGINAL_ROOT + f"/{arm}/journal/txn-{expected['committed_transactions']:08d}/candidate.pt",
                "SUMMARY_CHECKPOINT_REFERENCE_MISMATCH")
        require(canonical(row.get("exposure", {}).get("allocation")) == canonical(PROFILE["allocation"]),
                "SUMMARY_ALLOCATION_CHANGED")


def validate_package(archive, manifest, *, archive_sha256, manifest_sha256, expected_bindings=None):
    """Verify a pinned package without extraction, model imports or tensor loads."""
    raw, document = _pinned_json(manifest, manifest_sha256, MANIFEST_LIMIT)
    _check_manifest(document, expected_bindings)
    archive = _safe(archive)
    require(file_identity(archive)["sha256"] == _pin(archive_sha256), "PACKAGE_ARCHIVE_PIN_MISMATCH")
    seen, total, summary = set(), 0, None
    with ZipFile(archive) as package:
        infos = package.infolist()
        require(len(infos) == len(document["members"]) + 1 and len(infos) <= MEMBER_LIMIT, "ZIP_MEMBER_COUNT")
        for info in infos:
            name = info.filename
            require(info.orig_filename == name and name.casefold() not in seen
                    and (name == "manifest.json" or name in document["members"]), "ZIP_MEMBER_SET_OR_COLLISION")
            seen.add(name.casefold())
            require(not info.is_dir() and not info.flag_bits & 1
                    and stat.S_IFMT(info.external_attr >> 16) in (0, stat.S_IFREG), "ZIP_FILE_TYPE_INVALID")
            expected = {"bytes": len(raw), "sha256": manifest_sha256} if name == "manifest.json" else document["members"][name]
            require(info.file_size == expected["bytes"], "ZIP_DECLARED_SIZE_MISMATCH")
            digest, size, pieces = sha256(), 0, []
            with package.open(info) as stream:
                while chunk := stream.read(1024 * 1024):
                    size += len(chunk)
                    require(size <= expected["bytes"], "ZIP_STREAM_BOUND")
                    digest.update(chunk)
                    if name.endswith(".json"):
                        require(size <= JSON_LIMIT, "JSON_BYTE_BOUND")
                        pieces.append(chunk)
            require(size == expected["bytes"] and digest.hexdigest() == expected["sha256"], "ZIP_MEMBER_BYTES_MISMATCH:" + name)
            total += size
            require(total <= BYTE_LIMIT, "ZIP_EXPANDED_BYTE_BOUND")
            if pieces:
                value = decode(b"".join(pieces))
                if name == SUMMARY_PATH:
                    summary = value
        require(total == document["expanded_bytes"] + len(raw), "ZIP_TOTAL_BYTES_MISMATCH")
    _check_summary(summary, document)
    require(file_identity(archive)["sha256"] == archive_sha256, "PACKAGE_ARCHIVE_CHANGED")
    _pinned_json(manifest, manifest_sha256, MANIFEST_LIMIT)
    return document


def build_package(*, parent_result, complete_marker, archive, extracted_root, inspection_report,
                  parent_sha256, complete_sha256, archive_sha256, inspection_sha256, output_dir):
    """Recheck original evidence, then create a new byte-preserving prior ZIP."""
    output = _safe(output_dir)
    require(not output.exists() and output.parent.is_dir(), "EXCLUSIVE_FRESH_OUTPUT_REQUIRED")
    inputs = ((parent_result, parent_sha256), (complete_marker, complete_sha256),
              (inspection_report, inspection_sha256))
    documents = [_pinned_json(path, pin)[1] for path, pin in inputs]
    parent, complete, prior = documents
    root = _safe(extracted_root)
    from tools.inspect_teaching_continuation import inspect_continuation
    from cas_meta2.teaching_cycle.worker_contract import archive_payloads, WORKER_FILES
    checked = inspect_continuation(parent_result, complete_marker, archive, root,
        parent_sha256=parent_sha256, complete_sha256=complete_sha256, archive_sha256=archive_sha256)
    require(canonical(checked) == canonical(prior), "INSPECTION_SEMANTICS_CHANGED")
    require(prior.get("structurally_resumable") is True
            and prior.get("status") == "STRUCTURALLY_RESUMABLE_GPU_RESTORE_UNTESTED"
            and prior.get("required_original_campaign_root") == ORIGINAL_ROOT, "STRUCTURAL_RESUME_OR_PATH_REQUIRED")
    bindings = parent["bindings"]
    _, payloads, bundle = archive_payloads(root / "input/source.zip", bindings["archive_sha256"], bindings["manifest_sha256"])
    worker_manifest = bundle["manifest"]
    for name in WORKER_FILES:
        require(file_identity(ROOT / name)["sha256"] == sha256(payloads[name]).hexdigest(), "CURRENT_WORKER_SOURCE_CHANGED:" + name)
    require(canonical(worker_manifest["profile"]) == canonical(PROFILE), "FROZEN_PROFILE_MISMATCH")
    for key in ("source_sha256", "training_cases_sha256", "development_cases_sha256"):
        require(bindings.get(key) == worker_manifest[key], "PARENT_WORKER_BINDING_MISMATCH:" + key)
    require(complete.get("material_sha256") == bindings["material_receipt_sha256"], "MATERIAL_IDENTITY_MISMATCH")
    members = {}
    with ZipFile(archive) as original:
        for info in original.infolist():
            if info.is_dir() or not (info.filename == SUMMARY_PATH or info.filename.startswith("train/campaign/")):
                continue
            require(_member_name(info.filename), "PRIOR_STATE_MEMBER_NOT_ALLOWED")
            require(info.file_size <= FILE_LIMIT, "PRIOR_STATE_FILE_BOUND")
            digest, size = sha256(), 0
            with original.open(info) as stream:
                while chunk := stream.read(1024 * 1024):
                    size += len(chunk)
                    require(size <= info.file_size, "PRIOR_ARCHIVE_STREAM_BOUND")
                    digest.update(chunk)
            require(size == info.file_size, "PRIOR_ARCHIVE_SIZE_MISMATCH")
            members[info.filename] = {"bytes": size, "sha256": digest.hexdigest()}
        summary = decode(original.read(SUMMARY_PATH))
    manifest = {"schema": SCHEMA, "logical_run_id": prior["required_original_run_id"],
        "original_campaign_root": ORIGINAL_ROOT, "summary_path": SUMMARY_PATH,
        "source_sha256": bindings["source_sha256"], "bundle_manifest_sha256": bindings["manifest_sha256"],
        "source_archive_sha256": bindings["archive_sha256"], "material_receipt_sha256": bindings["material_receipt_sha256"],
        "summary_sha256": prior["resume_summary_sha256"], "parent_sha256": parent_sha256,
        "complete_sha256": complete_sha256, "prior_result_archive_sha256": archive_sha256,
        "inspection_sha256": inspection_sha256, "training_cases_sha256": worker_manifest["training_cases_sha256"],
        "development_cases_sha256": worker_manifest["development_cases_sha256"],
        "profile_sha256": sha256(canonical(PROFILE)).hexdigest(), "profile": deepcopy(worker_manifest["profile"]),
        "members": members, "arms": {arm: {key: deepcopy(prior["arms"][arm][key]) for key in ARM_FIELDS} for arm in ARMS},
        "expanded_bytes": sum(row["bytes"] for row in members.values()), "boundary": BOUNDARY}
    _check_manifest(manifest, None)
    _check_summary(summary, manifest)
    raw = canonical(manifest)
    require(len(raw) <= MANIFEST_LIMIT, "MANIFEST_BYTE_BOUND")
    output.mkdir()
    manifest_path, package_path = output / "manifest.json", output / "prior_state.zip"
    with manifest_path.open("xb") as stream:
        stream.write(raw)
    with package_path.open("xb") as target, ZipFile(target, "w", compression=ZIP_DEFLATED) as package, ZipFile(archive) as original:
        for name in ["manifest.json", *sorted(members)]:
            info = ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.compress_type, info.external_attr = ZIP_DEFLATED, (stat.S_IFREG | 0o600) << 16
            with package.open(info, "w", force_zip64=True) as destination:
                if name == "manifest.json":
                    destination.write(raw)
                else:
                    with original.open(name) as source:
                        count = 0
                        while chunk := source.read(1024 * 1024):
                            count += len(chunk)
                            require(count <= members[name]["bytes"], "COPY_STREAM_BOUND")
                            destination.write(chunk)
                        require(count == members[name]["bytes"], "COPY_SIZE_CHANGED")
            require(target.tell() <= BYTE_LIMIT, "PACKAGE_ARCHIVE_BYTE_BOUND")
    package_pin = file_identity(package_path)["sha256"]
    manifest_pin = sha256(raw).hexdigest()
    validate_package(package_path, manifest_path, archive_sha256=package_pin, manifest_sha256=manifest_pin,
                     expected_bindings={key: manifest[key] for key in PIN_FIELDS})
    require(file_identity(archive)["sha256"] == archive_sha256, "ORIGINAL_ARCHIVE_CHANGED")
    for path, pin in inputs:
        _pinned_json(path, pin)
    for name in WORKER_FILES:
        require(file_identity(ROOT / name)["sha256"] == sha256(payloads[name]).hexdigest(), "CURRENT_WORKER_SOURCE_CHANGED:" + name)
    receipt = {"schema": "cas-teaching-prior-state-build/1", "archive": {"path": str(package_path), **file_identity(package_path)},
        "manifest": {"path": str(manifest_path), **file_identity(manifest_path)},
        "logical_run_id": manifest["logical_run_id"], "original_campaign_root": ORIGINAL_ROOT,
        "members": len(members), "expanded_bytes": manifest["expanded_bytes"],
        "originals_unchanged": True, "private_targets_opened": False, "actual_gpu_restore": "UNEXECUTED",
        "launch_authorized": False, "new_reservation": False, "boundary": BOUNDARY}
    with (output / "receipt.json").open("xb") as stream:
        stream.write(canonical(receipt))
    return receipt
