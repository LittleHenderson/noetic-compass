"""Read-only inspection of collected teaching state, never a tensor restore.

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
                    and parts[0] in {"train", "predict1", "predict2", "driver", "bootstrap_evidence", "input"},
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


def _journal_view(root):
    """Initialize only an in-memory view; never call the creating constructor."""
    from cas_meta2.teaching_cycle import journal
    root = Path(root).absolute()
    journal._safe_path(root)
    require(root.is_dir() and (root / "journal.json").is_file(), "EXISTING_JOURNAL_REQUIRED")
    anchor, _ = journal._read_json(root / "journal.json", journal.RECEIPT_BYTES)
    require(set(anchor) == {"schema", "run_id", "identity", "identity_sha256", "max_checkpoint_bytes",
                           "max_metadata_bytes", "total_byte_limit"}
            and anchor["schema"] == journal.SCHEMA and anchor["max_checkpoint_bytes"] == 67108864
            and anchor["max_metadata_bytes"] == 33554432 and anchor["total_byte_limit"] == journal.TOTAL_BYTES
            and anchor["identity_sha256"] == sha256(journal._encode(anchor["identity"])).hexdigest(), "JOURNAL_ANCHOR_INVALID")
    view = object.__new__(journal.CheckpointJournal)
    view.root, view.anchor = root, anchor
    view.run_id, view.identity = anchor["run_id"], anchor["identity"]
    view.identity_sha256 = anchor["identity_sha256"]
    view.max_checkpoint_bytes, view.max_metadata_bytes = 67108864, 33554432
    view.incomplete_staging = []
    latest = view.latest()  # Unchanged read-only full-chain verifier.
    require(latest is not None, "NO_COMMITTED_CHECKPOINT")
    require(latest["retained_bytes"] <= journal.TOTAL_BYTES, "JOURNAL_RETAINED_BYTE_LIMIT")
    return view, latest


class _RestoreBoundary(Exception):
    pass


class _NoTensorRestore:
    def restore_checkpoint(self, path, digest):
        # All unchanged pure _resume checks precede this exact boundary.
        raise _RestoreBoundary()


def _registry_digest(cases):
    """Pure equivalent of the frozen adapter's validated record-key enumeration."""
    from cas_meta2.codec import canonical_sha256
    from cas_meta2.teaching_cycle.guided_application import make_cycle
    keys = {canonical_sha256(record) for case in cases for curriculum in ("aligned", "ordinary")
            for assistance in ("full", "faded", "none") for record in make_cycle(case, assistance, curriculum)}
    return canonical_sha256(sorted(keys))


def _inspect_arm(arm, report, campaign, bundle, root, scopes, registry_sha256):
    from cas_meta2.codec import canonical_sha256
    from cas_meta2.teaching_cycle import journal, runner
    view, latest = _journal_view(root / arm / "journal")
    metadata, identity = latest["metadata"], view.identity
    manifest, profile = bundle["manifest"], bundle["manifest"]["profile"]
    expected_run = campaign["run_id"] + "." + arm.split(".")[1] + "." + arm.split(".")[0]
    require(report["run_id"] == view.run_id == expected_run, "ARM_RUN_IDENTITY_MISMATCH")
    expected_identity = {
        "schema": runner.SCHEMA, "source_sha256": manifest["source_sha256"], "curriculum": arm.split(".")[1],
        "allocation": profile["allocation"], "seed": profile["seed"],
        "execution_mode": "cuda",
        "training_cases_sha256": manifest["training_cases_sha256"],
        "development_cases_sha256": manifest["development_cases_sha256"], "record_registry_sha256": registry_sha256}
    require(set(identity) == set(expected_identity) | {"scope_sha256"}
            and all(identity.get(key) == value for key, value in expected_identity.items()), "ARM_PLAN_IDENTITY_MISMATCH")
    require(metadata.get("identity") == identity and metadata.get("schema") == runner.SCHEMA,
            "LATEST_METADATA_IDENTITY_MISMATCH")
    count = metadata.get("event_count")
    require(type(count) is int and count >= 0, "COMMITTED_EVENT_COUNT_INVALID")
    require(metadata.get("batch_size") in (None, profile["batch_size"])
            and (not count or metadata["batch_size"] == profile["batch_size"]), "RESUME_BATCH_SIZE_MISMATCH")
    events, tails, receipts = root / arm / "events", [], []
    require(events.is_dir(), "EXISTING_EVENTS_REQUIRED")
    for path in sorted(events.iterdir()):
        journal._safe_path(path)
        match = re.fullmatch(r"step-([0-9]{8})\.(intent|result)\.json", path.name)
        require(match is not None, "EVENT_NAME_INVALID")
        if int(match[1]) > count:
            size = journal._regular_file(path)
            require(size <= runner.EVENT_BYTE_LIMIT, "TAIL_EVENT_BYTE_BOUND")
            tails.append({"name": path.name, "sha256": journal._hash_file(path), "bytes": size,
                "sequence": int(match[1]), "kind": match[2], "parse_status": "UNCOMMITTED_NOT_PARSED_OR_TRUSTED"})
        elif match[2] == "result":
            event, _ = journal._read_json(path, runner.EVENT_BYTE_LIMIT)
            receipts.append(event["receipt"])
    scope = scopes.get(identity.get("scope_sha256"))
    issue = "UNCOMMITTED_TEACHING_TAIL" if tails else (None if scope else "SCOPE_NAMES_UNAVAILABLE_WITHOUT_TENSOR_RESTORE")
    session = object.__new__(runner.TrainingSession)
    session.root, session.events, session.journal = root / arm, events, view
    session.identity, session.run_id = identity, view.run_id
    session.allocation = runner.Allocation(**profile["allocation"])
    session.train_cases = sorted(deepcopy(bundle["training_cases"]), key=lambda case: case["family_id"])
    session.development_cases = deepcopy(bundle["development_cases"])
    session.curriculum, session.seed, session.execution_mode = identity["curriculum"], profile["seed"], identity["execution_mode"]
    session.scope_names, session.learner = scope, _NoTensorRestore()
    session.cursor, session.history, session.event_count = {"epoch": 0, "batch": 0, "stage": 0}, [], 0
    session.pending_development, session.event_bytes = False, 0
    committed_entries = [entry for entry in metadata["history"] if entry.get("kind") == "batch"]
    require(len(committed_entries) == count, "COMMITTED_HISTORY_COUNT_MISMATCH")
    previous = metadata["initial_state_sha256"]
    for index, entry in enumerate(committed_entries, 1):
        _, receipt = session._read_step(index, entry)
        require(receipt["before_checkpoint_sha256"] == previous, "COMMITTED_STATE_CHAIN_MISMATCH")
        previous = receipt["after_checkpoint_sha256"]
    require(previous == metadata["model_state_sha256"], "COMMITTED_FINAL_STATE_MISMATCH")
    if issue is None:
        try:
            session._resume(latest)
        except _RestoreBoundary:
            require(session.ledger.report() == metadata["exposure"], "REPLAY_EXPOSURE_MISMATCH")
        else:
            require(False, "RESTORE_BOUNDARY_NOT_REACHED")
    reference = report.get("last_checkpoint")
    expected_checkpoint_path = str(PurePosixPath(campaign["campaign_root"]) / arm / "journal"
                                   / f"txn-{latest['receipt']['sequence']:08d}" / "candidate.pt")
    require(type(reference) is dict and reference.get("sha256") == latest["checkpoint_sha256"]
            and reference.get("path") == expected_checkpoint_path
            and reference.get("state_sha256") == metadata["model_state_sha256"]
            and reference.get("transaction") == latest["receipt"]["sequence"]
            and reference.get("receipt_sha256") == latest["receipt"]["receipt_sha256"], "LAST_CHECKPOINT_REFERENCE_MISMATCH")
    initial_dir = view.root / "txn-00000001"
    initial_metadata, _ = journal._read_json(initial_dir / "metadata.json", view.max_metadata_bytes)
    initial_receipt, initial_receipt_sha = journal._read_json(initial_dir / "receipt.json", journal.RECEIPT_BYTES)
    require(initial_metadata.get("model_state_sha256") == metadata["initial_state_sha256"]
            and initial_metadata.get("identity") == identity
            and report.get("initial_checkpoint") == {
                "path": str(PurePosixPath(campaign["campaign_root"]) / arm / "journal/txn-00000001/candidate.pt"),
                "sha256": initial_receipt["checkpoint_sha256"], "state_sha256": metadata["initial_state_sha256"],
                "transaction": 1, "receipt_sha256": initial_receipt_sha}, "INITIAL_CHECKPOINT_REFERENCE_MISMATCH")
    require(report.get("committed_cursor") == metadata["cursor"], "SUMMARY_COMMITTED_CURSOR_MISMATCH")
    steps, examples = sum(row["optimizer_steps"] for row in receipts), sum(row["batch_size"] for row in receipts)
    require(steps == count, "COMMITTED_OPTIMIZER_COUNT_MISMATCH")
    maximum = profile["allocation"]["maximum_cycles"]
    exposure = metadata["exposure"]
    completed = exposure["completed_full_aligned_cycles"] + exposure["completed_ordinary_blocks"]
    require(type(completed) is int and 0 <= completed <= maximum, "COMPLETED_CYCLE_COUNT_INVALID")
    return {"run_id": view.run_id, "committed_cursor": metadata["cursor"],
        "pending_development": metadata["pending_development"], "checkpoint_file": latest["checkpoint_path"],
        "checkpoint_file_sha256": latest["checkpoint_sha256"], "checkpoint_state_sha256": metadata["model_state_sha256"],
        "checkpoint_receipt_sha256": latest["receipt"]["receipt_sha256"],
        "committed_transactions": latest["receipt"]["sequence"], "committed_optimizer_steps": steps,
        "journal_retained_bytes": latest["retained_bytes"], "journal_byte_limit": journal.TOTAL_BYTES,
        "committed_teaching_examples": examples, "committed_exposure": exposure,
        "exposure_replayed_through_unchanged_controller": issue is None,
        "initial_state_sha256": metadata["initial_state_sha256"],
        "unfinished_cycles": maximum - completed, "uncommitted_tail": tails,
        "incomplete_staging": latest["incomplete_staging"], "structural_resume_checks_passed": issue is None,
        "blocker": issue, "actual_tensor_restore": "UNEXECUTED", "new_learner_scope_identity": "UNEXECUTED",
        "state_identity_boundary": "State SHA is bound metadata; tensor contents and optimizer restore were not deserialized."}


def inspect_continuation(parent_result, complete_marker, archive, extracted_root, *,
                         parent_sha256, complete_sha256, archive_sha256):
    from cas_meta2.teaching_cycle import evaluation, worker_contract
    from tools.evaluate_teaching_launch import _file_hash, _safe
    reader = evaluation._Reader()
    parent, complete = reader.json(parent_result, parent_sha256), reader.json(complete_marker, complete_sha256)
    require(parent.get("schema") == "cas-teaching-cycle-parent-lifecycle/2"
            and parent.get("status") in {"TEACHING_INCOMPLETE", "TEACHING_CYCLE_BLOCKED", "TEACHING_CYCLE_COLLECTED_NOT_SCORED"},
            "PARENT_RESULT_INVALID")
    bindings = parent["bindings"]
    require(complete.get("schema") == "cas-teaching-guest-complete/1"
            and complete.get("job") == complete.get("run_id") == parent["job"]
            and complete.get("source_sha256") == bindings["source_sha256"]
            and complete.get("manifest_sha256") == bindings["manifest_sha256"]
            and complete.get("material_sha256") == bindings["material_receipt_sha256"], "COMPLETE_IDENTITY_MISMATCH")
    require(parent["archive"].get("local_bytes_verified") is True
            and parent["archive"].get("sha256") == archive_sha256
            and complete.get("artifact") == {"key": "results/artifacts.zip", "sha256": archive_sha256,
                "bytes": parent["archive"].get("bytes")}
            and _file_hash(archive)[1] == parent["archive"]["bytes"], "ARCHIVE_IDENTITY_MISMATCH")
    root = _safe(extracted_root)
    copied = _collected_bytes(archive, root, archive_sha256)
    common = {"schema": "cas-teaching-continuation-inspection/1", "parent_sha256": parent_sha256,
        "complete_sha256": complete_sha256, "archive_sha256": archive_sha256, "extracted": copied,
        "private_targets_opened": False, "actual_gpu_restore": "UNEXECUTED", "actual_restart": "UNEXECUTED",
        "real_learner_construction": "UNEXECUTED", "real_model_scope_identity": "UNEXECUTED",
        "tokenizer_and_tensor_geometry": "UNEXECUTED", "optimizer_restore": "UNEXECUTED",
        "launch_authorized": False, "new_reservation": False, "automatic_retry": False}
    summary_path = root / "train/campaign_summary.json"
    if not summary_path.is_file():
        return {**common, "status": "BLOCKED_NO_CAMPAIGN_SUMMARY", "structurally_resumable": False, "arms": {}}
    campaign = reader.json(summary_path, complete["campaign_summary_sha256"])
    require(campaign.get("schema") == "cas-teaching-four-arm-campaign/1"
            and campaign.get("run_id") == parent["job"] and set(campaign.get("arms", {})) == set(evaluation.ARMS)
            and campaign.get("source_sha256") == bindings["source_sha256"]
            and campaign.get("manifest_sha256") == bindings["manifest_sha256"], "CAMPAIGN_IDENTITY_MISMATCH")
    original_root = campaign.get("campaign_root")
    require(type(original_root) is str and PurePosixPath(original_root).is_absolute()
            and ".." not in PurePosixPath(original_root).parts, "ORIGINAL_ABSOLUTE_CAMPAIGN_PATH_REQUIRED")
    _, payloads, bundle = worker_contract.archive_payloads(root / "input/source.zip", bindings["archive_sha256"], bindings["manifest_sha256"])
    require(bundle["manifest"]["source_sha256"] == bindings["source_sha256"], "BUNDLE_SOURCE_BINDING_MISMATCH")
    # The replay code itself must equal the collected, frozen worker sources.
    for name in ("cas_meta2/codec.py", "cas_meta2/features_v2.py", *["cas_meta2/teaching_cycle/" + name + ".py" for name in
            ("worker_contract", "runner", "journal", "controller", "guided_application", "lesson_contract", "gpu_adapter")]):
        require((ROOT / name).read_bytes() == payloads[name], "INSPECTOR_REPLAY_SOURCE_MISMATCH:" + name)
    scopes = {}
    from cas_meta2.codec import canonical_sha256
    for arm in evaluation.ARMS:
        _, latest = _journal_view(root / "train/campaign" / arm / "journal")
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
    registry_sha256 = _registry_digest(bundle["training_cases"])
    arms = {arm: _inspect_arm(arm, campaign["arms"][arm], campaign, bundle, root / "train/campaign", scopes, registry_sha256)
            for arm in evaluation.ARMS}
    require(all(arms[family + ".aligned"]["initial_state_sha256"] == arms[family + ".ordinary"]["initial_state_sha256"]
                for family in ("cas", "generic")), "CURRICULUM_INITIAL_STATES_NOT_MATCHED")
    eligible = campaign.get("all_allocations_finished") is False and all(row["structural_resume_checks_passed"] for row in arms.values())
    require(_collected_bytes(archive, root, archive_sha256) == copied, "INPUTS_CHANGED_DURING_INSPECTION")
    reader.json(parent_result, parent_sha256)
    reader.json(complete_marker, complete_sha256)
    return {**common, "status": "STRUCTURALLY_RESUMABLE_GPU_RESTORE_UNTESTED" if eligible else "CONTINUATION_BLOCKED",
        "structurally_resumable": eligible, "arms": arms, "resume_summary_sha256": complete["campaign_summary_sha256"],
        "required_original_run_id": campaign["run_id"], "required_original_campaign_root": campaign["campaign_root"],
        "local_campaign_root": str(root / "train/campaign"), "allocation_finished": campaign["all_allocations_finished"],
        "relocation_boundary": "Unchanged --resume-summary uses its original absolute campaign_root and run_id. Restore the byte-identical directory at that path on the future worker; no paths or metadata were rewritten.",
        "boundary": "Storage and pure record consistency only. CUDA is a declared receipt mode, not proof of execution. Fresh learner construction, real scope/tokenizer/tensor identity and optimizer restoration require a separate AWS check. No learning, provider or continuation-budget claim."}


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
    for name in ("parent-result", "complete-marker", "archive", "extracted-root", "parent-sha256", "complete-sha256", "archive-sha256"):
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
