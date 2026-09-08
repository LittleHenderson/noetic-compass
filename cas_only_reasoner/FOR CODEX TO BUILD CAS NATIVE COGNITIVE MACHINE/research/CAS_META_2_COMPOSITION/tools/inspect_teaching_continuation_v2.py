"""Read-only inspection of the exact first continuation, never a tensor restore.

The original summary and its Linux paths remain unchanged. A structurally valid
copy still requires the original run identity and campaign path on a future
worker. This tool does not authorize, reserve, launch or retry that worker.
"""
import argparse
from copy import deepcopy
from hashlib import sha256
import importlib.abc
import json
from pathlib import Path, PurePosixPath
import re
import stat
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "records/teaching_cycle_001"
LIMIT = 2684354560
FORBIDDEN = {"torch", "numpy", "sqlite3", "_sqlite3", "casformer", "cas_cjt", "cas_meta",
             "boto3", "botocore", "jax", "tensorflow"}


def require(condition, reason):
    if not condition:
        raise ValueError("TEACHING_CONTINUATION:" + reason)


def _collected_bytes(archive, extracted, expected):
    """Compare existing extracted files with pinned ZIP members; write nothing."""
    from tools.evaluate_teaching_launch import _file_hash, _safe
    require(_file_hash(archive)[0] == expected, "COLLECTED_ARCHIVE_PIN_MISMATCH")
    extracted = _safe(extracted)
    require(extracted.is_dir(), "EXTRACTED_DIRECTORY_REQUIRED")
    names, total = set(), 0
    with ZipFile(archive) as package:
        infos = package.infolist()
        require(0 < len(infos) <= 20000, "ARCHIVE_MEMBER_BOUND")
        for info in infos:
            name = info.filename.rstrip("/")
            parts = name.split("/")
            require(info.orig_filename == info.filename and "\\" not in name
                    and not PurePosixPath(name).is_absolute()
                    and all(part not in ("", ".", "..") for part in parts)
                    and parts[0] in {"train", "train_continued_001", "restore", "predict1", "predict2", "driver", "bootstrap_evidence", "input"},
                    "ARCHIVE_PATH_INVALID")
            key = name.casefold()
            require(key not in names, "ARCHIVE_NAME_COLLISION")
            names.add(key)
            target = _safe(extracted / name)
            require(target.is_relative_to(extracted), "EXTRACTED_PATH_ESCAPE")
            if info.is_dir():
                require(info.file_size == 0 and target.is_dir(), "ARCHIVE_DIRECTORY_MISMATCH")
                continue
            require(stat.S_IFMT(info.external_attr >> 16) in (0, stat.S_IFREG)
                    and not info.flag_bits & 1, "ARCHIVE_FILE_TYPE_INVALID")
            observed = target.stat()
            require(stat.S_ISREG(observed.st_mode) and observed.st_nlink == 1
                    and observed.st_size == info.file_size, "EXTRACTED_FILE_TYPE_OR_SIZE")
            total += info.file_size
            require(total <= LIMIT, "EXTRACTED_BYTE_BOUND")
            left, right, count = sha256(), sha256(), 0
            with package.open(info) as original, target.open("rb") as copied:
                while chunk := original.read(1024 * 1024):
                    count += len(chunk)
                    require(count <= info.file_size, "ARCHIVE_STREAM_BOUND")
                    left.update(chunk)
                    right.update(copied.read(len(chunk)))
                require(not copied.read(1), "EXTRACTED_FILE_GREW")
            require(count == info.file_size and left.digest() == right.digest(), "EXTRACTED_BYTES_MISMATCH:" + name)
    actual = set()
    for path in extracted.rglob("*"):
        _safe(path)
        if path.is_file():
            actual.add(path.relative_to(extracted).as_posix().casefold())
    require(actual == {info.filename.casefold() for info in infos if not info.is_dir()}, "EXTRACTED_INVENTORY_MISMATCH")
    require(_file_hash(archive)[0] == expected, "COLLECTED_ARCHIVE_CHANGED")
    return {"files_verified": len(actual), "expanded_bytes": total}



SUMMARY_PATH = "train_continued_001/campaign_summary.json"
RETAINED_SUMMARY_PATH = "train/campaign_summary.json"
ORIGINAL_ROOT = "/opt/cas-teaching/job/train/campaign"
FROZEN_EVIDENCE = {
    "parent_sha256": "ffb42912a72759a2c440571bcd929c397a8cc653b3d288d3a758221d52e4d86d",
    "complete_sha256": "aac9bfe609b3c9d04c0ad83f8fb209bcf7da12f1c79529e02c39b4f162db7d84",
    "archive_sha256": "43795d51cdc1fba4c70b0d7c0cd27f4beaedbb7dbfbf1c89dc358946f069cd38",
    "evaluation_sha256": "cd2d7cce4a3b75385d8f8348d6628b5edc43bcb18a10134f82f62567bc04ba05",
    "summary_sha256": "2cb6f5659a0377695b00e49f5a45d9edff6f87db6fe648927c4719d26a15d33b",
    "retained_summary_sha256": "26b23bb5f23ca875375797db155e8520b947bf0b4eada71e596a9ec7493e195f",
    "logical_run_id": "cas-meta2-teaching-20260908052915-8b5df59c",
    "job": "cas-meta2-teaching-20260908080138-5518e287",
    "payload_members": 6441,
    "payload_bytes": 189306349,
    "steps": {"cas.aligned": 784, "cas.ordinary": 784, "generic.aligned": 784, "generic.ordinary": 774},
}


def _admit_evaluation(reader, evaluation_report, evaluation_sha256, parent, complete, pins):
    evaluated = reader.json(evaluation_report, evaluation_sha256)
    require(evaluated.get("schema") == "cas-teaching-continuation-collected-evaluation/1"
            and evaluated.get("status") == "PARTIAL_EXPOSURE_ONLY"
            and evaluated.get("guest_status") == "TEACHING_INCOMPLETE"
            and evaluated.get("private_targets_opened") is False
            and evaluated.get("final_scores") is None
            and evaluated.get("job") == parent["job"] and evaluated.get("run_id") == parent["run_id"]
            and all(evaluated.get(key) == value for key, value in pins.items()),
            "VALIDATED_PARTIAL_EVALUATION_REQUIRED")
    prior = evaluated.get("continuation_evidence", {})
    require(prior.get("status") == "PINNED_RESTORE_RECEIPT_AND_PRIOR_BYTES_VERIFIED"
            and prior.get("restore_receipt_sha256") == complete.get("restore_receipt_sha256")
            and prior.get("restore_ready_sha256") == complete.get("restore_ready_sha256")
            and type(prior.get("prior_members_unchanged")) is int and prior["prior_members_unchanged"] > 0,
            "PRIOR_RESTORE_AND_HISTORY_ADMISSION_REQUIRED")
    return evaluated


def _prior_bytes(root, parent, evaluated):
    from cas_meta2.teaching_cycle import continuation_package as package
    c, b = parent["continuation"], parent["bindings"]
    require(package.file_identity(package.__file__)["sha256"] == c["prior_package_validator_sha256"],
            "PREVIOUS_VALIDATOR_SOURCE_CHANGED")
    previous = package.validate_package(root / "input/prior_state.zip", root / "input/prior_state_manifest.json",
        archive_sha256=c["prior_state_archive_sha256"], manifest_sha256=c["prior_state_manifest_sha256"],
        expected_bindings={"logical_run_id": parent["run_id"], "summary_sha256": c["prior_summary_sha256"],
            "source_sha256": b["source_sha256"], "bundle_manifest_sha256": b["manifest_sha256"],
            "source_archive_sha256": b["archive_sha256"], "material_receipt_sha256": b["material_receipt_sha256"]})
    require(previous["summary_path"] == RETAINED_SUMMARY_PATH
            and previous["summary_sha256"] == FROZEN_EVIDENCE["retained_summary_sha256"]
            and len(previous["members"]) == evaluated["continuation_evidence"]["prior_members_unchanged"],
            "PREVIOUS_PACKAGE_LINEAGE_CHANGED")
    for name, identity in previous["members"].items():
        require(package.file_identity(root / name) == identity, "PREVIOUS_MEMBER_CHANGED:" + name)
    return len(previous["members"])


def _replay_arms(root, campaign, retained, bundle, payloads):
    from tools import inspect_teaching_continuation as old
    from cas_meta2.teaching_cycle import evaluation, worker_contract
    from cas_meta2.codec import canonical_sha256
    for name in worker_contract.WORKER_FILES:
        require((ROOT / name).read_bytes() == payloads[name], "INSPECTOR_REPLAY_SOURCE_MISMATCH:" + name)
    scopes = {}
    reader = evaluation._Reader()
    for arm in evaluation.ARMS:
        _, latest = old._journal_view(root / "train/campaign" / arm / "journal")
        for path in (root / "train/campaign" / arm / "events").glob("*.result.json"):
            match = re.fullmatch(r"step-([0-9]{8})\.result\.json", path.name)
            require(match is not None, "EVENT_NAME_INVALID")
            if int(match[1]) > latest["metadata"]["event_count"]:
                continue
            receipt = reader.json(path).get("receipt", {})
            names = receipt.get("scope_names")
            if type(names) is list and names and all(type(name) is str for name in names):
                digest = canonical_sha256(sorted(names))
                require(digest == receipt.get("scope_sha256"), "RECEIPT_SCOPE_MISMATCH")
                scopes[digest] = sorted(names)
    registry = old._registry_digest(bundle["training_cases"])
    arms = {arm: old._inspect_arm(arm, campaign["arms"][arm], campaign, bundle,
        root / "train/campaign", scopes, registry) for arm in evaluation.ARMS}
    prefixes = {}
    for arm, row in arms.items():
        current = campaign["arms"][arm]
        require(current.get("observed_optimizer_steps") == row["committed_optimizer_steps"]
                and current.get("observed_teaching_examples") == row["committed_teaching_examples"]
                and current.get("cursor") == current.get("committed_cursor") == row["committed_cursor"]
                and current.get("uncommitted_recorded_optimizer_steps") == 0
                and current.get("incomplete_staging") == row["incomplete_staging"]
                and not row["incomplete_staging"], "LATEST_SUMMARY_STATE_MISMATCH")
        oldref = retained["arms"][arm]["last_checkpoint"]
        olddir = root / "train/campaign" / arm / "journal" / f"txn-{oldref['transaction']:08d}"
        oldmeta = reader.json(olddir / "metadata.json")
        _, latest = old._journal_view(root / "train/campaign" / arm / "journal")
        metadata = latest["metadata"]
        oldhistory, newhistory = oldmeta["history"], metadata["history"]
        require(len(newhistory) > len(oldhistory) and newhistory[:len(oldhistory)] == oldhistory,
                "OLD_HISTORY_NOT_STRICT_UNCHANGED_PREFIX")
        require(current["initial_checkpoint"] == retained["arms"][arm]["initial_checkpoint"]
                and [h for h in newhistory if h.get("kind") == "development"] == current["development_curve"],
                "INITIAL_OR_DEVELOPMENT_HISTORY_CHANGED")
        prefixes[arm] = {"previous_entries": len(oldhistory), "current_entries": len(newhistory),
                        "strict_unchanged_prefix": True}
    require(all(arms[family + ".aligned"]["initial_state_sha256"] == arms[family + ".ordinary"]["initial_state_sha256"]
                for family in ("cas", "generic")), "CURRICULUM_INITIAL_STATES_NOT_MATCHED")
    return arms, prefixes


def inspect_continuation(parent_result, complete_marker, archive, extracted_root, *,
                         parent_sha256, complete_sha256, archive_sha256,
                         evaluation_report, evaluation_sha256):
    from cas_meta2.teaching_cycle import evaluation, worker_contract
    from cas_meta2.teaching_cycle import continuation_package_v2 as package
    pins = {"parent_sha256": parent_sha256, "complete_sha256": complete_sha256, "archive_sha256": archive_sha256}
    require(all(value == FROZEN_EVIDENCE[key] for key, value in {**pins, "evaluation_sha256": evaluation_sha256}.items()),
            "EXACT_CONTINUATION001_EVIDENCE_REQUIRED")
    reader = evaluation._Reader()
    parent, complete = reader.json(parent_result, parent_sha256), reader.json(complete_marker, complete_sha256)
    require(parent.get("schema") == "cas-teaching-continuation-parent-lifecycle/1"
            and parent.get("status") in {"TEACHING_INCOMPLETE", "TEACHING_CONTINUATION_BLOCKED"}
            and parent.get("job") == FROZEN_EVIDENCE["job"]
            and parent.get("run_id") == FROZEN_EVIDENCE["logical_run_id"], "PRIOR_PARENT_IDENTITY_MISMATCH")
    bindings = parent["bindings"]
    require(complete.get("schema") == "cas-teaching-guest-complete/1"
            and complete.get("status") == "TEACHING_INCOMPLETE"
            and complete.get("job") == parent["job"] and complete.get("run_id") == parent["run_id"]
            and complete.get("source_sha256") == bindings["source_sha256"]
            and complete.get("manifest_sha256") == bindings["manifest_sha256"]
            and complete.get("material_sha256") == bindings["material_receipt_sha256"]
            and complete.get("latest_summary_path") == SUMMARY_PATH
            and complete.get("original_summary_path") == RETAINED_SUMMARY_PATH
            and complete.get("campaign_summary_sha256") == FROZEN_EVIDENCE["summary_sha256"],
            "PRIOR_COMPLETE_IDENTITY_MISMATCH")
    require(parent["archive"].get("local_bytes_verified") is True
            and parent["archive"].get("sha256") == archive_sha256
            and complete.get("artifact") == {"key": "results/artifacts.zip", "sha256": archive_sha256,
                                             "bytes": parent["archive"].get("bytes")}
            and package.file_identity(archive)["bytes"] == parent["archive"]["bytes"], "ARCHIVE_IDENTITY_MISMATCH")
    evaluated = _admit_evaluation(reader, evaluation_report, evaluation_sha256, parent, complete, pins)
    root = package._safe(extracted_root)
    copied = _collected_bytes(archive, root, archive_sha256)
    previous_members = _prior_bytes(root, parent, evaluated)
    campaign = reader.json(root / SUMMARY_PATH, FROZEN_EVIDENCE["summary_sha256"])
    retained = reader.json(root / RETAINED_SUMMARY_PATH, FROZEN_EVIDENCE["retained_summary_sha256"])
    require(campaign.get("schema") == "cas-teaching-four-arm-campaign/1"
            and campaign.get("run_id") == retained.get("run_id") == parent["run_id"]
            and campaign.get("campaign_root") == retained.get("campaign_root") == ORIGINAL_ROOT
            and campaign.get("resumed_summary_sha256") == FROZEN_EVIDENCE["retained_summary_sha256"]
            and campaign.get("all_allocations_finished") is False
            and campaign.get("source_sha256") == retained.get("source_sha256") == bindings["source_sha256"]
            and campaign.get("manifest_sha256") == retained.get("manifest_sha256") == bindings["manifest_sha256"]
            and set(campaign.get("arms", {})) == set(retained.get("arms", {})) == set(evaluation.ARMS),
            "LATEST_SUMMARY_LINEAGE_MISMATCH")
    _, payloads, bundle = worker_contract.archive_payloads(root / "input/source.zip",
        bindings["archive_sha256"], bindings["manifest_sha256"])
    require(bundle["manifest"]["source_sha256"] == bindings["source_sha256"], "BUNDLE_SOURCE_BINDING_MISMATCH")
    arms, prefixes = _replay_arms(root, campaign, retained, bundle, payloads)
    require({a: r["committed_optimizer_steps"] for a, r in arms.items()} == FROZEN_EVIDENCE["steps"],
            "LATEST_COUNTS_NOT_784_784_784_774")
    payload = {}
    with ZipFile(archive) as archive_view:
        for info in archive_view.infolist():
            if info.filename.startswith("train/campaign/") or info.filename in (SUMMARY_PATH, RETAINED_SUMMARY_PATH):
                require(not info.is_dir() and package._member_name(info.filename), "PRIOR_STATE_MEMBER_NOT_ALLOWED")
                payload[info.filename] = package.file_identity(root / info.filename, package.FILE_LIMIT)
    require(len(payload) == FROZEN_EVIDENCE["payload_members"]
            and sum(v["bytes"] for v in payload.values()) == FROZEN_EVIDENCE["payload_bytes"],
            "COMPLETE_CONTINUATION001_PAYLOAD_REQUIRED")
    require(_collected_bytes(archive, root, archive_sha256) == copied, "INPUTS_CHANGED_DURING_INSPECTION")
    reader.json(parent_result, parent_sha256)
    reader.json(complete_marker, complete_sha256)
    reader.json(evaluation_report, evaluation_sha256)
    eligible = all(row["structural_resume_checks_passed"] and not row["incomplete_staging"] for row in arms.values())
    return {"schema": "cas-teaching-continuation-inspection/2", **pins,
        "evaluation_sha256": evaluation_sha256, "extracted": copied,
        "status": "STRUCTURALLY_RESUMABLE_GPU_RESTORE_UNTESTED" if eligible else "CONTINUATION_BLOCKED",
        "structurally_resumable": eligible, "arms": arms, "history_prefixes": prefixes,
        "previous_members_unchanged": previous_members,
        "resume_summary_sha256": FROZEN_EVIDENCE["summary_sha256"], "summary_path": SUMMARY_PATH,
        "retained_summary_sha256": FROZEN_EVIDENCE["retained_summary_sha256"],
        "retained_summary_path": RETAINED_SUMMARY_PATH,
        "required_original_run_id": campaign["run_id"], "required_original_campaign_root": ORIGINAL_ROOT,
        "local_campaign_root": str(root / "train/campaign"), "allocation_finished": False,
        "payload_members": len(payload), "payload_bytes": sum(v["bytes"] for v in payload.values()),
        "private_targets_opened": False, "actual_gpu_restore": "UNEXECUTED", "actual_restart": "UNEXECUTED",
        "real_learner_construction": "UNEXECUTED", "optimizer_restore": "UNEXECUTED",
        "launch_authorized": False, "new_reservation": False, "automatic_retry": False,
        "boundary": "Exact saved bytes and frozen controller replay only. No tensors loaded, new CUDA restore, new training, or final scoring."}


def write_report(report, output):
    from cas_meta2.teaching_cycle.journal import _safe_path, _write_new, _encode
    path = Path(output).absolute()
    _safe_path(path)
    require(".." not in path.parts and path.is_relative_to(RECORDS) and path.parent.is_dir()
            and not path.exists(), "FRESH_TEACHING_RECORD_PATH_REQUIRED")
    _write_new(path, _encode(report))
    return {"path": str(path), "sha256": sha256(path.read_bytes()).hexdigest()}


def main(argv=None):
    require(not FORBIDDEN.intersection(sys.modules), "FORBIDDEN_MODULE_ALREADY_LOADED")
    class Guard(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if fullname.split(".")[0] in FORBIDDEN:
                raise RuntimeError("TEACHING_CONTINUATION:FORBIDDEN_IMPORT:" + fullname)
    sys.meta_path.insert(0, Guard())
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(ROOT))
    def audit(event, args):
        if event.startswith("socket.") or event == "sqlite3.connect":
            raise RuntimeError("TEACHING_CONTINUATION:FORBIDDEN_OPERATION:" + event)
    sys.addaudithook(audit)
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("parent-result", "complete-marker", "archive", "extracted-root", "parent-sha256", "complete-sha256", "archive-sha256", "evaluation-report", "evaluation-sha256"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--output")
    values = vars(parser.parse_args(argv))
    output = values.pop("output")
    report = inspect_continuation(**values)
    print(json.dumps(write_report(report, output) if output else report, sort_keys=True))
    require(not FORBIDDEN.intersection(sys.modules), "FORBIDDEN_MODULE_LOADED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
