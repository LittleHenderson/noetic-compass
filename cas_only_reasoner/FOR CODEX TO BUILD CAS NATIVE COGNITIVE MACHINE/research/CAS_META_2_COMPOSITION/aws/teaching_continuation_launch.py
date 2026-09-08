"""One new, bounded continuation lifecycle through an injected provider only.

Adds wait_restore(context, timeout)->{ready, probe} and
release_training(context, release)->{uploaded, release_sha256, restore_receipt_sha256}
to the unchanged teaching provider protocol. No optimizer step is permitted until
the parent admits the exact restore receipt and publishes the training release.
The old worker and all old transport modules remain unchanged.
"""
from copy import deepcopy
from decimal import Decimal
from hashlib import sha256
import math
from pathlib import Path
import time

from aws import budget, teaching_cycle_launch as base
from aws import teaching_continuation_plan as plan

SCHEMA = "cas-teaching-continuation-parent-lifecycle/1"
AUTHORITY_SCHEMA = "cas-teaching-continuation-execution-authority/1"
ARMS, SPLITS = base.ARMS, base.SPLITS
CAMPAIGN_KEY = "results/train_continued_001/campaign_summary.json"
RESTORE_KEY = "results/restore/restore_receipt.json"
canonical, envelope_document, write_evidence = base.canonical, base.envelope_document, base.write_evidence
ledger_snapshot = base.ledger_snapshot
LaunchError, RemotePartial = base.LaunchError, base.RemotePartial
require, _pin, _safe, _raw, _json = base.require, base._pin, base._safe, base._raw, base._json


def _authority(envelope, request):
    document = envelope_document(envelope, expected_sha256=request["bindings"]["authority_sha256"])
    expected = {"schema": AUTHORITY_SCHEMA, "task_scope": plan.TASK_SCOPE, "job": request["job"],
        "logical_run_id": request["logical_run_id"], "continuation": request["continuation"],
        "bindings": {key: value for key, value in request["bindings"].items() if key != "authority_sha256"},
        "resource_plan_sha256": request["resource_plan_sha256"], "reservation_usd": "8.00",
        "automatic_retries": 0, "training": True, "native_execution": False,
        "launch_authorized": True, "reuses_v9_one_shot_authorization": False,
        "reuses_original_reservation": False}
    require(canonical(document) == canonical(expected), "NEW_CONTINUATION_AUTHORITY_REQUIRED")
    return document


def _prior_input(context):
    from cas_meta2.teaching_cycle import continuation_package as package
    continuation, bindings = context["continuation"], context["bindings"]
    require(sha256(_raw(Path(package.__file__))).hexdigest() == continuation["prior_package_validator_sha256"],
            "PRIOR_VALIDATOR_SOURCE_PIN_MISMATCH")
    archive, manifest = context["prior_state_archive_path"], context["prior_state_manifest_path"]
    observed = package.file_identity(archive, plan.PRIOR_ARCHIVE_BYTES_MAX)
    require(observed == {"sha256": continuation["prior_state_archive_sha256"],
                         "bytes": continuation["prior_state_archive_bytes"]}, "PRIOR_ARCHIVE_IDENTITY_MISMATCH")
    expected = {"logical_run_id": context["run_id"], "original_campaign_root": plan.ORIGINAL_CAMPAIGN_ROOT,
        "source_sha256": bindings["source_sha256"], "bundle_manifest_sha256": bindings["manifest_sha256"],
        "source_archive_sha256": bindings["archive_sha256"], "material_receipt_sha256": bindings["material_receipt_sha256"],
        "summary_sha256": continuation["prior_summary_sha256"], "parent_sha256": continuation["prior_parent_result_sha256"],
        "complete_sha256": continuation["prior_complete_sha256"], "inspection_sha256": continuation["prior_inspection_sha256"],
        "prior_result_archive_sha256": continuation["prior_result_archive_sha256"],
        "training_cases_sha256": bindings["training_cases_sha256"], "development_cases_sha256": bindings["development_cases_sha256"],
        "profile_sha256": continuation["profile_sha256"]}
    document = package.validate_package(archive, manifest, archive_sha256=continuation["prior_state_archive_sha256"],
        manifest_sha256=continuation["prior_state_manifest_sha256"], expected_bindings=expected)
    expanded = document["expanded_bytes"] + len(_raw(manifest, package.MANIFEST_LIMIT))
    require(expanded == continuation["prior_state_expanded_bytes"] <= plan.PRIOR_EXPANDED_BYTES_MAX,
            "PRIOR_FULL_EXPANDED_BYTE_MISMATCH")
    context["prior_tree_expected"] = {"files": len(document["members"]), "bytes": document["expanded_bytes"],
                                      "sha256": plan.canonical_sha256(document["members"])}
    return deepcopy(document["arms"])


def _preflight(facts, context):
    base._preflight(facts, context)
    require(type(facts.get("raw_prices")) is dict and
            canonical(facts.get("cost_worksheet")) == canonical(plan.worksheet(facts["raw_prices"])),
            "CONTINUATION_PRICING_WORKSHEET_REQUIRED")
    require(Decimal(facts["rate_hourly_usd"]) == Decimal(facts["cost_worksheet"]["rates_usd"]["compute"]),
            "PRICING_RATE_FIELDS_DISAGREE")


def _continued(document, context, *, restored=True):
    base._common(document, context)
    require(document.get("continuation_sha256") == plan.canonical_sha256(context["continuation"]),
            "CONTINUATION_REMOTE_BINDING_MISMATCH")
    if restored:
        require(_pin(context.get("restore_receipt_sha256")) and
                all(document.get(key) == context.get(key) for key in ("restore_ready_sha256", "restore_receipt_sha256")),
                "REMOTE_RESTORE_BINDING_MISMATCH")


def _restore(result, context, pids):
    require(type(result) is dict and set(result) == {"ready", "probe"}, "RESTORE_RECEIPTS_REQUIRED")
    ready = envelope_document(result["ready"], key="results/restore_ready.json")
    _continued(ready, context, restored=False)
    require(ready.get("schema") == "cas-teaching-continuation-restore-ready/1", "RESTORE_READY_SCHEMA_INVALID")
    base._exit(ready.get("restore_exit"), "restore", pids)
    probe = envelope_document(result["probe"], key=RESTORE_KEY)
    require(ready.get("restore_receipt") == {key: result["probe"][key] for key in ("key", "sha256", "bytes")},
            "RESTORE_RECEIPT_RAW_PIN_MISMATCH")
    expected = {"schema": "cas-teaching-gpu-restore/1", "status": "RESTORED_NO_TRAINING",
        "job": context["job"], "run_id": context["run_id"],
        "source_sha256": context["bindings"]["source_sha256"],
        "bundle_manifest_sha256": context["bindings"]["manifest_sha256"],
        "material_sha256": context["bindings"]["material_receipt_sha256"],
        "source_archive_sha256": context["bindings"]["archive_sha256"],
        "prior_archive_sha256": context["continuation"]["prior_state_archive_sha256"],
        "prior_manifest_sha256": context["continuation"]["prior_state_manifest_sha256"],
        "summary_sha256": context["continuation"]["prior_summary_sha256"],
        "probe_sha256": context["continuation"]["restore_probe_sha256"],
        "validator_sha256": context["continuation"]["prior_package_validator_sha256"],
        "input_tree_unchanged": True, "optimizer_steps_performed": 0, "predictions_run": False,
        "actual_restore": "FOUR_ARMS_RESTORED",
        "pid": ready["restore_exit"]["pid"]}
    require(type(probe) is dict and all(canonical(probe.get(key)) == canonical(value) for key, value in expected.items()),
            "EXACT_GPU_RESTORE_RECEIPT_REQUIRED")
    require(type(probe.get("wall_seconds")) in (int, float) and math.isfinite(probe["wall_seconds"])
            and 0 <= probe["wall_seconds"] <= context["resource_plan"]["restore_probe_seconds_max"], "RESTORE_TIME_BOUND")
    instance = probe.get("instance")
    require(type(instance) is dict and all(instance.get(key) == value for key, value in {
        "instanceId": context["launch"]["instance_id"], "accountId": context["resource_plan"]["account_id"],
        "region": context["resource_plan"]["region"], "instanceType": context["resource_plan"]["instance_type"]}.items()),
        "RESTORE_INSTANCE_IDENTITY_MISMATCH")
    environment = probe.get("environment")
    require(type(environment) is dict and environment.get("torch") == "2.11.0+cu128"
            and environment.get("cuda") == "12.8" and type(environment.get("gpu")) is str
            and "RTX PRO 4500" in environment["gpu"] and type(environment.get("device")) is str
            and environment["device"].startswith("cuda"), "REGISTERED_RESTORE_GPU_REQUIRED")
    tree = probe.get("prior_tree_before")
    require(type(tree) is dict and set(tree) == {"files", "bytes", "sha256"}
            and all(type(tree[key]) is int and tree[key] > 0 for key in ("files", "bytes"))
            and _pin(tree["sha256"]) and canonical(tree) == canonical(probe.get("prior_tree_after"))
            and canonical(tree) == canonical(context.get("prior_tree_expected")), "EXACT_UNCHANGED_PRIOR_TREE_REQUIRED")
    require(type(probe.get("arms")) is dict and set(probe["arms"]) == set(ARMS), "FOUR_RESTORED_ARMS_REQUIRED")
    for arm, prior in context["prior_arms"].items():
        row = probe["arms"][arm]
        require(type(row) is dict and all(canonical(row.get(key)) == canonical(value) for key, value in prior.items()),
                "RESTORE_PRIOR_ARM_MISMATCH:" + arm)
        require(row.get("training_cases_sha256") == context["bindings"]["training_cases_sha256"] and
                all(_pin(row.get(key)) for key in ("optimizer_state_sha256", "saved_optimizer_state_sha256",
                    "scope_sha256", "record_registry_sha256", "initial_state_sha256")) and
                row["optimizer_state_sha256"] == row["saved_optimizer_state_sha256"], "OPTIMIZER_OR_SCOPE_RESTORE_MISMATCH")
        require(type(row.get("optimizer_steps_performed")) is int and row["optimizer_steps_performed"] == 0
                and row.get("predictions_run") is False and type(row.get("optimizer_tensors_device_checked")) is int
                and row["optimizer_tensors_device_checked"] > 0, "ARM_RESTORE_DEVICE_OR_NO_UPDATE_REQUIRED")
    return probe


def _training(result, context, pids):
    require(type(result) is dict and set(result) == {"ready", "campaign"}, "TRAINING_RECEIPTS_REQUIRED")
    ready = envelope_document(result["ready"], key="results/train_ready.json")
    _continued(ready, context)
    require(ready.get("schema") == "cas-teaching-training-ready/1" and ready.get("all_allocations_finished") is True,
            "FULL_TRAINING_SEAL_REQUIRED")
    base._exit(ready.get("train_exit"), "train", pids)
    envelope = result["campaign"]
    campaign = envelope_document(envelope, key=CAMPAIGN_KEY)
    require(ready.get("campaign_summary") == {key: envelope[key] for key in ("key", "sha256", "bytes")},
            "TRAINING_CAMPAIGN_SEAL_MISMATCH")
    expected = {"schema": "cas-teaching-four-arm-campaign/1", "run_id": context["run_id"],
        "source_sha256": context["bindings"]["source_sha256"], "manifest_sha256": context["bindings"]["manifest_sha256"],
        "resumed_summary_sha256": context["continuation"]["prior_summary_sha256"],
        "campaign_root": plan.ORIGINAL_CAMPAIGN_ROOT, "all_allocations_finished": True,
        "held_out_opened": False, "accepted_weights_updated": False}
    require(type(campaign) is dict and all(canonical(campaign.get(key)) == canonical(value) for key, value in expected.items())
            and type(campaign.get("arms")) is dict and set(campaign["arms"]) == set(ARMS), "CONTINUED_CAMPAIGN_IDENTITY_INVALID")
    selected = {}
    for arm in ARMS:
        row = campaign["arms"][arm]
        family, curriculum = arm.split(".")
        exact = {"allocation_finished": True, "curriculum": curriculum,
            "run_id": context["run_id"] + "." + curriculum + "." + family, "execution_mode": "cuda",
            "max_epochs": 16, "cursor": {"epoch": 16, "batch": 0, "stage": 0},
            "observed_optimizer_steps": 896, "observed_teaching_examples": 28672}
        require(type(row) is dict and all(canonical(row.get(key)) == canonical(value) for key, value in exact.items()),
                "DECLARED_FULL_ALLOCATION_COUNTS_MISMATCH")
        for key in ("initial_checkpoint", "selected_checkpoint"):
            ref = row.get(key)
            base._reference(ref)
            require(ref["path"] == plan.ORIGINAL_CAMPAIGN_ROOT + f"/{arm}/journal/txn-{ref['transaction']:08d}/candidate.pt",
                    "ORIGINAL_CHECKPOINT_PATH_REQUIRED")
        require(row["initial_checkpoint"]["transaction"] == 1 and row["selected_checkpoint"]["transaction"] > 1
                and row["initial_checkpoint"]["state_sha256"] == context["restore_initial_states"][arm],
                "RESTORED_INITIAL_CHECKPOINT_REQUIRED")
        curve = row.get("development_curve")
        require(type(curve) is list and len(curve) == 16 and all(type(entry) is dict for entry in curve)
                and [entry.get("epoch") for entry in curve] == list(range(1, 17)), "DEVELOPMENT_CURVE_INCOMPLETE")
        eligible = []
        for entry in curve:
            require(entry.get("kind") == "development" and type(entry.get("eligible")) is bool, "DEVELOPMENT_ENTRY_INVALID")
            if entry["eligible"]:
                require(type(entry["epoch"]) is int and entry["epoch"] >= 4 and type(entry.get("attempted")) is int
                        and entry["attempted"] == 64 and type(entry.get("correct")) is int and 0 <= entry["correct"] <= 64
                        and _pin(entry.get("checkpoint_sha256")), "DEVELOPMENT_SELECTION_INVALID")
                eligible.append(entry)
        require(bool(eligible) and row["selected_checkpoint"]["state_sha256"] == max(eligible, key=lambda item: item["correct"])["checkpoint_sha256"],
                "CHECKPOINT_NOT_DEVELOPMENT_SELECTED")
        selected[arm] = row["selected_checkpoint"]
    require(ready.get("selected_checkpoints") == selected, "SELECTED_CHECKPOINT_TRAINING_SEAL_MISMATCH")
    for family in ("cas", "generic"):
        require(context["restore_initial_states"][family + ".aligned"] == context["restore_initial_states"][family + ".ordinary"],
                "INITIAL_CONTROLS_NOT_MATCHED")
    return campaign


def _prediction(result, context, index, pids, campaign):
    require(type(result) is dict and "ready" in result, "PREDICTION_RECEIPTS_REQUIRED")
    _continued(envelope_document(result["ready"], key=f"results/prediction{index}_ready.json"), context)
    return base._prediction(result, context, index, pids, campaign)


def _collection(result, context, destination, *, partial=False):
    require(type(result) is dict and "complete" in result, "COLLECTION_RECEIPTS_REQUIRED")
    complete = envelope_document(result["complete"], key="results/complete.json")
    _continued(complete, context, restored="restore_receipt_sha256" in context)
    return base._collection(result, context, destination, partial=partial)


def execute(request, authority_envelope, provider, *, expected_bindings, expected_continuation, expected_ledger,
            prior_state_archive_path, prior_state_manifest_path, public_sets_path, receipt_dir,
            ledger_path=budget.CANONICAL_LEDGER, now=time.time):
    """One attempt; every provider action has an intent, with cleanup on failure.

    Only the injected provider can reserve or contact AWS. Local package checking
    is pure; admission of a provider receipt is not an independent tensor test.
    """
    plan.validate_request(request, expected_bindings=expected_bindings,
                          expected_continuation=expected_continuation, expected_ledger=expected_ledger)
    authority = _authority(authority_envelope, request)
    require(provider is not None and callable(now), "INJECTED_PROVIDER_AND_CLOCK_REQUIRED")
    directory = _safe(receipt_dir)
    require(not directory.exists() and directory.parent.is_dir(), "FRESH_EVIDENCE_DIRECTORY_REQUIRED")
    started = now()
    require(type(started) in (int, float) and math.isfinite(started), "FINITE_WALL_CLOCK_REQUIRED")
    context = {"schema": SCHEMA, "job": request["job"], "run_id": request["logical_run_id"],
        "request": deepcopy(request), "authority": authority, "bindings": deepcopy(request["bindings"]),
        "continuation": deepcopy(request["continuation"]), "resource_plan": deepcopy(request["resource_plan"]),
        "request_sha256": plan.canonical_sha256(request), "receipt_dir": str(directory),
        "public_sets_path": str(_safe(public_sets_path)), "ledger_path": str(_safe(ledger_path)),
        "prior_state_archive_path": str(_safe(prior_state_archive_path)),
        "prior_state_manifest_path": str(_safe(prior_state_manifest_path)), "started_unix": started,
        "deadline_unix": started + request["resource_plan"]["runtime_seconds_max"]}
    directory.mkdir()
    write_evidence(directory / "intent.json", {**context, "authority_envelope": authority_envelope,
                    "expected_ledger": expected_ledger, "automatic_retries": 0})
    sequence, status = 0, "TEACHING_CONTINUATION_BLOCKED"
    failure = cleanup = archive_verified = before = after = reservation = None
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

    def partial_marker(result):
        if type(result) is dict and set(result) == {"complete"}:
            complete = envelope_document(result["complete"], key="results/complete.json")
            _continued(complete, context, restored="restore_receipt_sha256" in context)
            require(complete.get("schema") == "cas-teaching-guest-complete/1"
                    and complete.get("status") in ("TEACHING_INCOMPLETE", "BLOCKED"), "PARTIAL_MARKER_INVALID")
            context["partial_complete_sha256"] = result["complete"]["sha256"]
            context["partial_guest_status"] = complete["status"]
            raise RemotePartial("TEACHING_CONTINUATION:" + complete["status"])

    try:
        context["prior_arms"] = _prior_input(context)
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
        base._reserved(before, after, reservation, request)
        context["reservation"] = reservation
        remaining()
        launched = call("launch")
        base._launch(launched, context, now())
        context["launch"] = launched
        pids = set()
        timeout = remaining() - 900  # Setup precedes probe; retain shared reader/collection allowance.
        require(timeout > 0, "INSUFFICIENT_SHARED_RESTORE_TIME")
        restored = call("wait_restore", timeout=timeout)
        partial_marker(restored)
        probe = _restore(restored, context, pids)
        context["restore_ready_sha256"] = restored["ready"]["sha256"]
        context["restore_receipt_sha256"] = restored["probe"]["sha256"]
        context["restore_initial_states"] = {arm: row["initial_state_sha256"] for arm, row in probe["arms"].items()}
        common = {"job": context["job"], "run_id": context["run_id"],
            "source_sha256": context["bindings"]["source_sha256"], "manifest_sha256": context["bindings"]["manifest_sha256"],
            "material_sha256": context["bindings"]["material_receipt_sha256"],
            "continuation_sha256": plan.canonical_sha256(context["continuation"]),
            "restore_ready_sha256": context["restore_ready_sha256"], "restore_receipt_sha256": context["restore_receipt_sha256"]}
        train_release = {"schema": "cas-teaching-continuation-train-release/1", **common, "automatic_retries": 0}
        train_ref = write_evidence(directory / "train_release.json", train_release)
        remaining()
        uploaded = call("release_training", release=train_release)
        require(type(uploaded) is dict and uploaded.get("uploaded") is True and uploaded.get("release_sha256") == train_ref["sha256"]
                and uploaded.get("restore_receipt_sha256") == context["restore_receipt_sha256"], "TRAIN_RELEASE_RECEIPT_MISMATCH")
        timeout = remaining() - 900
        require(timeout > 0, "INSUFFICIENT_SHARED_TRAINING_TIME")
        training = call("wait_training", timeout=timeout)
        partial_marker(training)
        campaign = _training(training, context, pids)
        context["training_ready_sha256"] = training["ready"]["sha256"]
        context["campaign_summary_sha256"] = training["campaign"]["sha256"]
        release = {"schema": "cas-teaching-public-release/1", **common,
            "training_ready_sha256": context["training_ready_sha256"], "campaign_summary_sha256": context["campaign_summary_sha256"],
            "public_sets": {"key": "input/public.json", "sha256": context["bindings"]["public_sets_sha256"], "bytes": len(public_raw)},
            "automatic_retries": 0}
        release_ref = write_evidence(directory / "public_release.json", release)
        remaining()
        uploaded = call("release_public", release=release)
        require(type(uploaded) is dict and uploaded.get("uploaded") is True
                and uploaded.get("release_sha256") == release_ref["sha256"]
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
        status = "TEACHING_CONTINUATION_COLLECTED_NOT_SCORED"
    except BaseException as error:
        if isinstance(error, RemotePartial) and context.get("partial_guest_status") == "TEACHING_INCOMPLETE":
            status = "TEACHING_INCOMPLETE"
        failure = {"exception_type": type(error).__name__, "reason": str(error)
            if isinstance(error, (LaunchError, plan.PlanError, budget.BudgetRefused)) else "PROVIDER_OR_RUNTIME_FAILURE_DETAILS_IN_PROVIDER_RECEIPTS"}
        write_evidence(directory / "failure.json", failure)
        if before is not None and after is None:
            try:
                after = ledger_snapshot(ledger_path)
                write_evidence(directory / "ledger_after_failure.json", after)
            except Exception as observation_error:
                write_evidence(directory / "ledger_after_unavailable.json",
                    {"exception_type": type(observation_error).__name__, "automatic_retry": False})
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
                    {"exception_type": type(collection_error).__name__, "cloud_copy_must_be_retained": True, "automatic_retry": False})
    finally:
        try:
            cleanup = call("cleanup", retain_cloud_copy=archive_verified is None)
            require(type(cleanup) is dict and cleanup.get("complete") is True and cleanup.get("compute_closed") is True
                    and cleanup.get("instance_state") in ("TERMINATED", "NOT_CREATED", "REJECTED_NO_INSTANCE_OBSERVED")
                    and cleanup.get("schedules_removed") is True, "CLEANUP_INCOMPLETE")
            if archive_verified is None:
                states = {"OBSERVED_RETAINED": True, "NOT_CREATED": False, "NO_RESULT_OBJECT_OBSERVED": False, "UNKNOWN_PRESERVED": None}
                require(cleanup.get("cloud_copy_deleted") is False and cleanup.get("cloud_copy_state") in states
                        and cleanup.get("cloud_copy_retained") is states[cleanup["cloud_copy_state"]], "SOLE_CLOUD_COPY_MUST_BE_RETAINED")
        except BaseException as error:
            status = "TEACHING_CONTINUATION_BLOCKED"
            cleanup = {"complete": False, "exception_type": type(error).__name__,
                "reason": str(error) if isinstance(error, LaunchError) else "CLEANUP_PROVIDER_FAILURE",
                "provider_receipt": cleanup, "required_retain_cloud_copy": archive_verified is None}
    result = {"schema": SCHEMA, "status": status, "job": request["job"], "run_id": request["logical_run_id"],
        "request_sha256": context["request_sha256"], "bindings": request["bindings"], "continuation": request["continuation"],
        "reservation": reservation, "ledger_before": None if before is None else before["binding"],
        "ledger_after": None if after is None else after["binding"], "failure": failure, "cleanup": cleanup,
        "archive": archive_verified, "receipt_dir": str(directory), "elapsed_seconds": now() - started,
        "restore_ready_sha256": context.get("restore_ready_sha256"), "restore_receipt_sha256": context.get("restore_receipt_sha256"),
        "training_ready_sha256": context.get("training_ready_sha256"), "campaign_summary_sha256": context.get("campaign_summary_sha256"),
        "prediction_seals": context.get("prediction_seals", []), "automatic_retries": 0, "reservation_refunded": False,
        "native_execution": "UNEXECUTED", "retention_after_intervening_learning": "UNEXECUTED",
        "learning_results": "INDEPENDENT_SCORING_REQUIRED", "provider_observations_are_injected": True,
        "reuses_v9_one_shot_authorization": False, "reuses_original_reservation": False}
    write_evidence(directory / "result.json", result)
    return result
