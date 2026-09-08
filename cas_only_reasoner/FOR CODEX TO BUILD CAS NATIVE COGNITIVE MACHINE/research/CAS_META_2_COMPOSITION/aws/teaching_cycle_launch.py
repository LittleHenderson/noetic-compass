"""One-shot teaching-only parent lifecycle, with an injected provider.

No provider client or CLI is imported here. The caller independently checks
current source, authority and pricing pins. An inert plan is not permission.
Every attempted provider operation has a fresh local intent/result receipt.
There are no retries, refunds or condition-v9 authorization paths.

Provider protocol (all results must be finite JSON):
 preflight(context) -> current read-only account/rate/shutdown facts
 reserve(context) -> canonical budget.reserve_budget receipt, exactly once
 launch(context) -> instance identity plus verified shutdown gate
 wait_training(context, timeout) -> {ready: envelope, campaign: envelope}
 release_public(context, release) -> {uploaded: true, release_sha256, public_sha256}
 wait_prediction(context, run_index, timeout) -> {ready: envelope, seal: envelope}
 collect(context, destination, timeout) -> {complete: envelope, archive: file receipt}
 cleanup(context, retain_cloud_copy) -> termination/schedule/storage receipts

Envelope = {raw_utf8, sha256, bytes, key}; optional document must match the raw
JSON. Object keys are relative to the provider's job prefix. Preserve the raw
worker bytes; never reserialize an existing summary/seal to calculate its SHA.
"""
from copy import deepcopy
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import re
import stat
import time

from aws import budget
from aws import teaching_cycle_plan as plan

SCHEMA = "cas-teaching-cycle-parent-lifecycle/2"
AUTHORITY_SCHEMA = "cas-teaching-cycle-execution-authority/2"
ARMS = ("cas.aligned", "cas.ordinary", "generic.aligned", "generic.ordinary")
SPLITS = ("test_fresh", "test_context", "test_names")
JSON_BOUND = 32 * 1024**2


class LaunchError(ValueError):
    pass


class RemotePartial(LaunchError):
    """Guest closed its upload with incomplete teaching or a blocked prefix."""


def require(condition, code):
    if not condition:
        raise LaunchError("TEACHING_LAUNCH:" + code)


def canonical(value):
    try:
        return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
    except (TypeError, ValueError) as error:
        raise LaunchError("TEACHING_LAUNCH:FINITE_JSON_REQUIRED") from error


def _pin(value):
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None and value != "0" * 64


def _safe(path):
    path = Path(path).absolute()
    require(".." not in path.parts and not any(item.is_symlink() or getattr(item, "is_junction", lambda: False)()
            for item in (path, *path.parents)), "LINKED_OR_PARENT_PATH_REJECTED")
    return path


def _raw(path, maximum=JSON_BOUND):
    path = _safe(path)
    info = path.stat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and 0 < info.st_size <= maximum,
            "LOCAL_FILE_TYPE_OR_SIZE")
    raw = path.read_bytes()
    require(len(raw) == info.st_size, "LOCAL_FILE_CHANGED_DURING_READ")
    return raw


def _json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "DUPLICATE_JSON_KEY")
            result[key] = value
        return result
    try:
        document = json.loads(raw, object_pairs_hook=pairs,
                              parse_constant=lambda _: require(False, "NONFINITE_JSON"))
        canonical(document)
        return document
    except (UnicodeError, json.JSONDecodeError) as error:
        raise LaunchError("TEACHING_LAUNCH:INVALID_JSON") from error


def envelope_document(envelope, *, key=None, expected_sha256=None, maximum=JSON_BOUND):
    require(type(envelope) is dict and type(envelope.get("raw_utf8")) is str
            and type(envelope.get("bytes")) is int and _pin(envelope.get("sha256")), "RAW_ENVELOPE_REQUIRED")
    raw = envelope["raw_utf8"].encode("utf-8")
    require(0 < len(raw) <= maximum and envelope["bytes"] == len(raw)
            and sha256(raw).hexdigest() == envelope["sha256"], "RAW_ENVELOPE_IDENTITY_MISMATCH")
    if key is not None:
        require(envelope.get("key") == key, "ENVELOPE_OBJECT_KEY_MISMATCH")
    if expected_sha256 is not None:
        require(envelope["sha256"] == expected_sha256, "EXTERNAL_ENVELOPE_PIN_MISMATCH")
    document = _json(raw)
    if "document" in envelope:
        require(canonical(document) == canonical(envelope["document"]), "ENVELOPE_DOCUMENT_MISMATCH")
    return document


def write_evidence(path, value):
    path = _safe(path)
    raw = canonical(value)
    require(len(raw) <= 64 * 1024**2, "EVIDENCE_BYTE_LIMIT")
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    require(_raw(path, 64 * 1024**2) == raw, "EVIDENCE_READBACK_MISMATCH")
    return {"path": str(path), "sha256": sha256(raw).hexdigest(), "bytes": len(raw)}


def ledger_snapshot(path):
    """Read the complete canonical history without creating a lock or mutation."""
    path = _safe(path)
    raw = _raw(path)
    history = path.with_suffix(path.suffix + ".history")
    _safe(history)
    for entry in history.iterdir():
        _raw(entry)
    state = budget.read_locked(path, history)
    require(_raw(path) == raw and state == budget.decoded(raw), "LEDGER_CHANGED_DURING_READ")
    binding = {"revision": state["revision"], "sha256": sha256(raw).hexdigest(),
               "cap_usd": format(budget.amount(state["owner_task_cap_usd"]), ".2f"),
               "reserved_usd": format(budget.amount(state["total_reserved_usd"]), ".2f"),
               "unreserved_usd": format(budget.amount(state["remaining_unreserved_usd"]), ".2f")}
    return {"binding": binding, "ledger": state, "ledger_path": str(path)}


def _authority(envelope, request):
    document = envelope_document(envelope, expected_sha256=request["bindings"]["authority_sha256"])
    expected = {"schema": AUTHORITY_SCHEMA, "task_scope": plan.TASK_SCOPE, "job": request["job"],
                "bindings": {key: value for key, value in request["bindings"].items() if key != "authority_sha256"},
                "resource_plan_sha256": request["resource_plan_sha256"], "reservation_usd": "8.00",
                "automatic_retries": 0, "training": True, "native_execution": False,
                "launch_authorized": True, "reuses_v9_one_shot_authorization": False}
    require(canonical(document) == canonical(expected), "NEW_TEACHING_AUTHORITY_REQUIRED")
    return document


def _reserved(before, after, receipt, request):
    prior, current = before["ledger"], after["ledger"]
    require(current["revision"] == prior["revision"] + 1 and current["reservations"][:-1] == prior["reservations"]
            and current["previous_state_sha256"] == budget.digest(budget.encoded(prior)), "RESERVATION_NOT_APPEND_ONLY")
    for key in ("approval", "predecessor", "owner_task_cap_usd", "scope", "no_automatic_refund"):
        require(current.get(key) == prior.get(key), "RESERVATION_CONTEXT_CHANGED")
    entry = current["reservations"][-1]
    expected = {"job": request["job"], "source_sha": request["bindings"]["source_commit"],
                "archive_sha256": request["bindings"]["archive_sha256"], "reserved_usd": "8.00",
                "status": budget.STATUS, "plan": request["resource_plan"],
                "plan_sha256": budget.digest(budget.encoded(request["resource_plan"]))}
    require(all(canonical(entry.get(key)) == canonical(value) for key, value in expected.items()), "RESERVATION_IDENTITY_MISMATCH")
    require(budget.amount(current["total_reserved_usd"]) - budget.amount(prior["total_reserved_usd"]) == budget.amount("8.00")
            and budget.amount(prior["remaining_unreserved_usd"]) - budget.amount(current["remaining_unreserved_usd"]) == budget.amount("8.00"),
            "RESERVATION_AMOUNT_MISMATCH")
    require(type(receipt) is dict and receipt.get("reservation") == entry
            and receipt.get("ledger_sha256") == after["binding"]["sha256"]
            and receipt.get("ledger_path") == before["ledger_path"] == after["ledger_path"], "RESERVATION_RECEIPT_MISMATCH")
    require(all(receipt.get(key) == current[key] for key in
                ("revision", "total_reserved_usd", "remaining_unreserved_usd")), "RESERVATION_RECEIPT_TOTALS_MISMATCH")


def _preflight(facts, context):
    resource = context["resource_plan"]
    require(type(facts) is dict and facts.get("read_only") is True, "READ_ONLY_PREFLIGHT_REQUIRED")
    for key in ("account_id", "region", "instance_type", "instance_count"):
        require(canonical(facts.get(key)) == canonical(resource[key]), "PREFLIGHT_IDENTITY_MISMATCH:" + key)
    require(facts.get("t4_rejected") is True and facts.get("shutdown_capability_verified") is False
            and facts.get("shutdown_verification_stage") == "BEFORE_WORKER_RELEASE"
            and facts.get("conflicting_resources") == [], "PREFLIGHT_RESOURCE_OR_SHUTDOWN_CONFLICT")
    require(facts.get("pricing_receipt_sha256") == context["bindings"]["pricing_receipt_sha256"]
            and budget.amount(facts.get("rate_hourly_usd"), positive=True) <= budget.amount(resource["on_demand_hourly_usd_max"]),
            "PREFLIGHT_PRICING_MISMATCH")


def _launch(document, context, now):
    require(type(document) is dict and document.get("job") == context["job"]
            and type(document.get("instance_id")) is str and re.fullmatch(r"i-(?:[0-9a-f]{8}|[0-9a-f]{17})", document["instance_id"])
            and document.get("instance_type") == context["resource_plan"]["instance_type"]
            and type(document.get("instance_count")) is int and document["instance_count"] == 1, "LAUNCH_INSTANCE_IDENTITY_INVALID")
    gate = document.get("shutdown_gate")
    require(type(gate) is dict and gate.get("verified") is True and _pin(gate.get("receipt_sha256"))
            and gate.get("instance_id") == document["instance_id"] and gate.get("worker_released_after_verification") is True
            and type(gate.get("deadline_unix")) in (int, float) and math.isfinite(gate["deadline_unix"])
            and now < gate["deadline_unix"] <= context["deadline_unix"], "VERIFIED_SHUTDOWN_BEFORE_WORKER_REQUIRED")


def _common(document, context):
    require(type(document) is dict and all(document.get(key) == value for key, value in {
        "job": context["job"], "run_id": context["run_id"], "source_sha256": context["bindings"]["source_sha256"],
        "manifest_sha256": context["bindings"]["manifest_sha256"],
        "material_sha256": context["bindings"]["material_receipt_sha256"]}.items()), "REMOTE_RUN_IDENTITY_MISMATCH")


def _exit(receipt, phase, previous_pids):
    require(type(receipt) is dict and receipt.get("phase") == phase and receipt.get("exited") is True
            and type(receipt.get("exit_code")) is int and receipt["exit_code"] == 0
            and type(receipt.get("pid")) is int and receipt["pid"] > 0 and receipt["pid"] not in previous_pids,
            "FRESH_PROCESS_EXIT_REQUIRED")
    previous_pids.add(receipt["pid"])


def _reference(reference):
    require(type(reference) is dict and set(reference) == {"path", "sha256", "state_sha256", "transaction", "receipt_sha256"}
            and type(reference["path"]) is str and re.split(r"[/\\]", reference["path"])[-1] == "candidate.pt"
            and type(reference["transaction"]) is int and 1 <= reference["transaction"] <= 100
            and all(_pin(reference[key]) for key in ("sha256", "state_sha256", "receipt_sha256")), "CHECKPOINT_REFERENCE_INVALID")


def _training(result, context, pids):
    require(type(result) is dict and set(result) == {"ready", "campaign"}, "TRAINING_RECEIPTS_REQUIRED")
    ready = envelope_document(result["ready"], key="results/train_ready.json")
    _common(ready, context)
    require(ready.get("schema") == "cas-teaching-training-ready/1" and ready.get("all_allocations_finished") is True,
            "FULL_TRAINING_SEAL_REQUIRED")
    _exit(ready.get("train_exit"), "train", pids)
    campaign_envelope = result["campaign"]
    campaign = envelope_document(campaign_envelope, key="results/train/campaign_summary.json")
    require(ready.get("campaign_summary") == {key: campaign_envelope[key] for key in ("key", "sha256", "bytes")},
            "TRAINING_CAMPAIGN_SEAL_MISMATCH")
    require(type(campaign) is dict and campaign.get("schema") == "cas-teaching-four-arm-campaign/1"
            and campaign.get("run_id") == context["run_id"] and campaign.get("source_sha256") == context["bindings"]["source_sha256"]
            and campaign.get("manifest_sha256") == context["bindings"]["manifest_sha256"]
            and campaign.get("all_allocations_finished") is True and campaign.get("held_out_opened") is False
            and campaign.get("accepted_weights_updated") is False and type(campaign.get("arms")) is dict
            and set(campaign["arms"]) == set(ARMS), "CAMPAIGN_TRAINING_IDENTITY_INVALID")
    selected, run_ids = {}, set()
    for arm in ARMS:
        report = campaign["arms"][arm]
        require(type(report) is dict and report.get("allocation_finished") is True
                and report.get("curriculum") == arm.split(".")[1] and type(report.get("run_id")) is str
                and report["run_id"] not in run_ids and report.get("execution_mode") == "cuda", "TRAINING_ARM_INVALID")
        run_ids.add(report["run_id"])
        require(report.get("max_epochs") == 16 and report.get("cursor") == {"epoch": 16, "batch": 0, "stage": 0}
                and report.get("observed_optimizer_steps") == 896 and report.get("observed_teaching_examples") == 28672,
                "DECLARED_FULL_ALLOCATION_COUNTS_MISMATCH")
        for key in ("initial_checkpoint", "selected_checkpoint"):
            _reference(report.get(key))
        require(report["initial_checkpoint"]["transaction"] == 1 and report["selected_checkpoint"]["transaction"] > 1,
                "INITIAL_SELECTED_PHASE_MISMATCH")
        curve = report.get("development_curve")
        require(type(curve) is list and len(curve) == 16 and [row.get("epoch") for row in curve] == list(range(1, 17)),
                "DEVELOPMENT_CURVE_INCOMPLETE")
        eligible = []
        for row in curve:
            require(type(row) is dict and row.get("kind") == "development" and type(row.get("eligible")) is bool,
                    "DEVELOPMENT_ENTRY_INVALID")
            if row["eligible"]:
                require(row["epoch"] >= 4 and row.get("attempted") == 64 and type(row.get("correct")) is int
                        and 0 <= row["correct"] <= 64 and _pin(row.get("checkpoint_sha256")), "DEVELOPMENT_SELECTION_INVALID")
                eligible.append(row)
        require(bool(eligible), "NO_ELIGIBLE_DEVELOPMENT_CHECKPOINT")
        winner = max(eligible, key=lambda row: row["correct"])
        require(report["selected_checkpoint"]["state_sha256"] == winner["checkpoint_sha256"], "CHECKPOINT_NOT_DEVELOPMENT_SELECTED")
        selected[arm] = report["selected_checkpoint"]
    require(ready.get("selected_checkpoints") == selected, "SELECTED_CHECKPOINT_TRAINING_SEAL_MISMATCH")
    for family in ("cas", "generic"):
        require(campaign["arms"][family + ".aligned"]["initial_checkpoint"]["state_sha256"] ==
                campaign["arms"][family + ".ordinary"]["initial_checkpoint"]["state_sha256"], "INITIAL_CONTROLS_NOT_MATCHED")
    return ready, campaign


def _prediction(result, context, index, pids, campaign):
    require(type(result) is dict and set(result) == {"ready", "seal"}, "PREDICTION_RECEIPTS_REQUIRED")
    ready = envelope_document(result["ready"], key=f"results/prediction{index}_ready.json")
    _common(ready, context)
    require(ready.get("schema") == "cas-teaching-prediction-ready/1" and type(ready.get("run_index")) is int
            and ready["run_index"] == index and ready.get("training_ready_sha256") == context["training_ready_sha256"]
            and ready.get("campaign_summary_sha256") == context["campaign_summary_sha256"], "PREDICTION_TRAINING_BINDING_MISMATCH")
    _exit(ready.get("prediction_exit"), "predict", pids)
    envelope = result["seal"]
    seal = envelope_document(envelope, key=f"results/predict{index}/prediction_seal.json")
    require(ready.get("prediction_seal") == {key: envelope[key] for key in ("key", "sha256", "bytes")}, "PREDICTION_SEAL_MISMATCH")
    names = {f"{arm}.{phase}.{split}.json" for arm in ARMS for phase in ("untrained", "trained") for split in SPLITS}
    require(type(seal) is dict and seal.get("schema") == "cas-teaching-blind-prediction-seal/1"
            and seal.get("source_sha256") == context["bindings"]["source_sha256"]
            and seal.get("private_targets_opened") is False and seal.get("native_execution") == "UNEXECUTED"
            and type(seal.get("artifacts")) is dict and set(seal["artifacts"]) == names, "FULL_PREDICTION_SEAL_REQUIRED")
    for name, declaration in seal["artifacts"].items():
        require(type(declaration) is dict and _pin(declaration.get("sha256")) and type(declaration.get("bytes")) is int
                and 0 < declaration["bytes"] <= JSON_BOUND and type(declaration.get("path")) is str
                and re.split(r"[/\\]", declaration["path"])[-1] == name, "PREDICTION_ARTIFACT_DECLARATION_INVALID")
    return {"run_index": index, **{key: envelope[key] for key in ("key", "sha256", "bytes")}}, ready


def _collection(result, context, destination, *, partial=False):
    require(type(result) is dict and set(result) == {"complete", "archive"}, "COLLECTION_RECEIPTS_REQUIRED")
    complete = envelope_document(result["complete"], key="results/complete.json")
    _common(complete, context)
    require(complete.get("schema") == "cas-teaching-guest-complete/1"
            and complete.get("status") in ({"TEACHING_INCOMPLETE", "BLOCKED", "COMPLETE"} if partial else {"COMPLETE"}),
            "COMPLETE_RECEIPT_MISMATCH")
    if "partial_complete_sha256" in context:
        require(result["complete"]["sha256"] == context["partial_complete_sha256"], "PARTIAL_COMPLETE_PIN_MISMATCH")
    if not partial:
        require(complete.get("training_ready_sha256") == context["training_ready_sha256"]
                and complete.get("campaign_summary_sha256") == context["campaign_summary_sha256"]
                and complete.get("prediction_seals") == context["prediction_seals"], "COMPLETE_RECEIPT_MISMATCH")
    archive = result["archive"]
    require(type(archive) is dict and set(archive) == {"path", "key", "sha256", "bytes"}
            and archive["key"] == "results/artifacts.zip" and _pin(archive["sha256"])
            and type(archive["bytes"]) is int and 0 < archive["bytes"] <= context["resource_plan"]["artifact_download_bytes_max"],
            "ARCHIVE_RECEIPT_INVALID")
    require(complete.get("artifact") == {key: archive[key] for key in ("key", "sha256", "bytes")}, "ARCHIVE_REMOTE_PIN_MISMATCH")
    path = _safe(archive["path"])
    require(path.is_relative_to(_safe(destination)), "ARCHIVE_OUTSIDE_COLLECTION_ROOT")
    info = path.stat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_size == archive["bytes"], "LOCAL_ARCHIVE_SIZE_OR_TYPE_MISMATCH")
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    require(digest.hexdigest() == archive["sha256"] and path.stat().st_size == info.st_size, "LOCAL_ARCHIVE_HASH_MISMATCH")
    return {**archive, "local_bytes_verified": True, "contents_independently_scored": False,
            "guest_status": complete["status"], "partial": partial}


def execute(request, authority_envelope, provider, *, expected_bindings, expected_ledger,
            public_sets_path, receipt_dir, ledger_path=budget.CANONICAL_LEDGER, now=time.time):
    """Perform one bounded lifecycle through injected methods; never retry.

    Local archive verification permits removal of the cloud artifact copy; it
    does not establish learning or correct archive contents. Scoring is separate.
    Cleanup is attempted on every path after the immutable intent is created.
    """
    plan.validate_request(request, expected_bindings=expected_bindings, expected_ledger=expected_ledger)
    authority = _authority(authority_envelope, request)
    require(provider is not None and callable(now), "INJECTED_PROVIDER_AND_CLOCK_REQUIRED")
    directory = _safe(receipt_dir)
    require(not directory.exists() and directory.parent.is_dir(), "FRESH_EVIDENCE_DIRECTORY_REQUIRED")
    directory.mkdir()
    started = now()
    require(type(started) in (int, float) and math.isfinite(started), "FINITE_WALL_CLOCK_REQUIRED")
    context = {"schema": SCHEMA, "job": request["job"], "run_id": request["job"],
        "request": deepcopy(request), "authority": authority, "bindings": deepcopy(request["bindings"]),
        "resource_plan": deepcopy(request["resource_plan"]), "request_sha256": plan.canonical_sha256(request),
        "receipt_dir": str(directory), "public_sets_path": str(_safe(public_sets_path)),
        "ledger_path": str(_safe(ledger_path)), "started_unix": started,
        "deadline_unix": started + request["resource_plan"]["runtime_seconds_max"]}
    write_evidence(directory / "intent.json", {**context, "authority_envelope": authority_envelope,
                    "expected_ledger": expected_ledger, "automatic_retries": 0})
    sequence, status, failure, cleanup, archive_verified = 0, "TEACHING_CYCLE_BLOCKED", None, None, None
    before, after, reservation = None, None, None
    collection_attempted = False
    def remaining(maximum=None):
        value = context["deadline_unix"] - now()
        require(math.isfinite(value) and value > 0, "SHARED_LIFETIME_EXHAUSTED")
        return min(value, maximum) if maximum is not None else value
    def call(method, **arguments):
        nonlocal sequence
        sequence += 1
        write_evidence(directory / f"{sequence:03d}_{method}_intent.json",
                       {"method": method, "request_sha256": context["request_sha256"], "arguments": arguments})
        result = getattr(provider, method)(deepcopy(context), **deepcopy(arguments))
        write_evidence(directory / f"{sequence:03d}_{method}_result.json", result)
        return result
    try:
        public_raw = _raw(public_sets_path, request["resource_plan"]["public_release_bytes_max"])
        require(sha256(public_raw).hexdigest() == request["bindings"]["public_sets_sha256"], "PUBLIC_FILE_PIN_MISMATCH")
        public = _json(public_raw)
        require(type(public) is dict and set(public) == set(SPLITS)
                and all(type(rows) is list and len(rows) == 64 for rows in public.values()), "PUBLIC_SPLIT_COUNTS_INVALID")
        before = ledger_snapshot(ledger_path)
        require(before["binding"] == expected_ledger and not any(row["job"] == request["job"] for row in before["ledger"]["reservations"]),
                "LEDGER_DRIFT_OR_JOB_ALREADY_RESERVED_NO_RETRY")
        write_evidence(directory / "ledger_before.json", before)
        remaining()
        facts = call("preflight")
        _preflight(facts, context)
        context["preflight"] = facts
        remaining()
        reservation = call("reserve")
        after = ledger_snapshot(ledger_path)
        write_evidence(directory / "ledger_after.json", after)
        _reserved(before, after, reservation, request)
        context["reservation"] = reservation
        remaining()
        launched = call("launch")
        _launch(launched, context, now())
        context["launch"] = launched
        pids = set()
        training_timeout = remaining() - 900  # Two 300s predictions + bounded collection, not a reset.
        require(training_timeout > 0, "INSUFFICIENT_SHARED_TIME_FOR_TRAIN_AND_READERS")
        training = call("wait_training", timeout=training_timeout)
        if type(training) is dict and set(training) == {"complete"}:
            complete = envelope_document(training["complete"], key="results/complete.json")
            _common(complete, context)
            require(complete.get("schema") == "cas-teaching-guest-complete/1"
                    and complete.get("status") in ("TEACHING_INCOMPLETE", "BLOCKED"), "PARTIAL_TRAINING_MARKER_INVALID")
            context["partial_complete_sha256"] = training["complete"]["sha256"]
            context["partial_guest_status"] = complete["status"]
            raise RemotePartial("TEACHING_LAUNCH:" + complete["status"])
        _, campaign = _training(training, context, pids)
        context["training_ready_sha256"] = training["ready"]["sha256"]
        context["campaign_summary_sha256"] = training["campaign"]["sha256"]
        release = {"schema": "cas-teaching-public-release/1", "job": context["job"], "run_id": context["run_id"],
            "source_sha256": context["bindings"]["source_sha256"], "manifest_sha256": context["bindings"]["manifest_sha256"],
            "material_sha256": context["bindings"]["material_receipt_sha256"],
            "training_ready_sha256": context["training_ready_sha256"], "campaign_summary_sha256": context["campaign_summary_sha256"],
            "public_sets": {"key": "input/public.json", "sha256": context["bindings"]["public_sets_sha256"], "bytes": len(public_raw)},
            "automatic_retries": 0}
        release_receipt = write_evidence(directory / "public_release.json", release)
        remaining()
        uploaded = call("release_public", release=release)
        require(type(uploaded) is dict and uploaded.get("uploaded") is True
                and uploaded.get("release_sha256") == release_receipt["sha256"]
                and uploaded.get("public_sha256") == context["bindings"]["public_sets_sha256"], "PUBLIC_RELEASE_RECEIPT_MISMATCH")
        context["prediction_seals"] = []
        for index in (1, 2):
            prediction = call("wait_prediction", run_index=index, timeout=remaining(300))
            seal, _ = _prediction(prediction, context, index, pids, campaign)
            context["prediction_seals"].append(seal)
        destination = directory / "collected"
        destination.mkdir()
        collection_attempted = True
        collected = call("collect", destination=str(destination), timeout=remaining())
        archive_verified = _collection(collected, context, destination)
        write_evidence(directory / "local_archive_verified.json", archive_verified)
        remaining()
        status = "TEACHING_CYCLE_COLLECTED_NOT_SCORED"
    except BaseException as error:
        if isinstance(error, RemotePartial) and context.get("partial_guest_status") == "TEACHING_INCOMPLETE":
            status = "TEACHING_INCOMPLETE"
        failure = {"exception_type": type(error).__name__,
                   "reason": str(error) if isinstance(error, (LaunchError, plan.PlanError, budget.BudgetRefused)) else "PROVIDER_OR_RUNTIME_FAILURE_DETAILS_IN_PROVIDER_RECEIPTS"}
        write_evidence(directory / "failure.json", failure)
        # A reserve call can fail after publishing its ledger entry. Observe the
        # current ledger once; never fabricate its missing receipt or retry it.
        if before is not None and after is None:
            try:
                after = ledger_snapshot(ledger_path)
                write_evidence(directory / "ledger_after_failure.json", after)
            except Exception as observation_error:
                write_evidence(directory / "ledger_after_unavailable.json",
                               {"exception_type": type(observation_error).__name__, "automatic_retry": False})
        # Preserve any trained prefix before termination. This is one collection
        # attempt, never a replay of train/predict or a second artifact retry.
        if "launch" in context and not collection_attempted:
            try:
                timeout = remaining(300)
                destination = directory / "partial_collected"
                destination.mkdir()
                collection_attempted = True
                collected = call("collect", destination=str(destination), timeout=timeout)
                archive_verified = _collection(collected, context, destination, partial=True)
                write_evidence(directory / "local_partial_archive_verified.json", archive_verified)
            except BaseException as collection_error:
                write_evidence(directory / "partial_collection_unavailable.json",
                    {"exception_type": type(collection_error).__name__, "cloud_copy_must_be_retained": True,
                     "automatic_retry": False})
    finally:
        try:
            cleanup = call("cleanup", retain_cloud_copy=archive_verified is None)
            require(type(cleanup) is dict and cleanup.get("complete") is True and cleanup.get("compute_closed") is True
                    and cleanup.get("instance_state") in ("TERMINATED", "NOT_CREATED", "REJECTED_NO_INSTANCE_OBSERVED")
                    and cleanup.get("schedules_removed") is True, "CLEANUP_INCOMPLETE")
            if archive_verified is None:
                copy_states = {"OBSERVED_RETAINED": True, "NOT_CREATED": False,
                               "NO_RESULT_OBJECT_OBSERVED": False, "UNKNOWN_PRESERVED": None}
                require(cleanup.get("cloud_copy_deleted") is False and cleanup.get("cloud_copy_state") in copy_states
                        and cleanup.get("cloud_copy_retained") is copy_states[cleanup["cloud_copy_state"]],
                        "SOLE_CLOUD_COPY_MUST_BE_RETAINED")
        except BaseException as error:
            status = "TEACHING_CYCLE_BLOCKED"
            cleanup = {"complete": False, "exception_type": type(error).__name__,
                       "reason": str(error) if isinstance(error, LaunchError) else "CLEANUP_PROVIDER_FAILURE",
                       "provider_receipt": cleanup, "required_retain_cloud_copy": archive_verified is None}
    result = {"schema": SCHEMA, "status": status, "job": request["job"], "request_sha256": context["request_sha256"],
        "bindings": request["bindings"], "reservation": reservation, "ledger_before": None if before is None else before["binding"],
        "ledger_after": None if after is None else after["binding"], "failure": failure, "cleanup": cleanup,
        "archive": archive_verified, "receipt_dir": str(directory), "elapsed_seconds": now() - started,
        "training_ready_sha256": context.get("training_ready_sha256"),
        "campaign_summary_sha256": context.get("campaign_summary_sha256"),
        "prediction_seals": context.get("prediction_seals", []),
        "automatic_retries": 0, "reservation_refunded": False, "native_execution": "UNEXECUTED",
        "retention_after_intervening_learning": "UNEXECUTED", "learning_results": "INDEPENDENT_SCORING_REQUIRED",
        "provider_observations_are_injected": True, "reuses_v9_one_shot_authorization": False}
    write_evidence(directory / "result.json", result)
    return result
