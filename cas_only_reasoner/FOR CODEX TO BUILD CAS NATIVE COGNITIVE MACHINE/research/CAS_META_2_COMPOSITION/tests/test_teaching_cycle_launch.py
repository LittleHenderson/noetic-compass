"""Injected provider and temporary ledger copies; no AWS or neural execution."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import shutil

import pytest

from aws import budget, teaching_cycle_plan as plan, teaching_cycle_launch as launch

JOB = "cas-meta2-teaching-20260908000000-abcdef12"


def envelope(value, key, *, pretty=False):
    raw = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode() if pretty else launch.canonical(value)
    return {"raw_utf8": raw.decode(), "sha256": sha256(raw).hexdigest(), "bytes": len(raw), "key": key}


def ref(enveloped):
    return {key: enveloped[key] for key in ("key", "sha256", "bytes")}


@pytest.fixture(scope="session")
def ledger_template(tmp_path_factory):
    """Copy real recorded budget history; all reservations below use this copy."""
    original = budget.CANONICAL_LEDGER
    state = budget.read_locked(original, original.with_suffix(original.suffix + ".history"))
    root = tmp_path_factory.mktemp("teaching_budget_template")
    ledger = root / "ledger.json"
    ledger.write_bytes(original.read_bytes())
    history = ledger.with_suffix(".json.history")
    shutil.copytree(original.with_suffix(original.suffix + ".history"), history)
    assert budget.read_locked(ledger, history) == state
    assert state["revision"] >= 17
    return ledger


@pytest.fixture
def prepared(tmp_path, ledger_template):
    ledger = tmp_path / "ledger.json"
    shutil.copyfile(ledger_template, ledger)
    shutil.copytree(ledger_template.with_suffix(".json.history"), ledger.with_suffix(".json.history"))
    public = tmp_path / "public.json"
    public.write_bytes(launch.canonical({split: [{} for _ in range(64)] for split in launch.SPLITS}))
    bindings = {key: sha256(key.encode()).hexdigest() for key in plan.BINDING_FIELDS}
    bindings.update(plan.FROZEN_BINDINGS)
    bindings["public_sets_sha256"] = sha256(public.read_bytes()).hexdigest()
    authority = {"schema": launch.AUTHORITY_SCHEMA, "task_scope": plan.TASK_SCOPE, "job": JOB,
                 "bindings": {key: value for key, value in bindings.items() if key != "authority_sha256"},
                 "resource_plan_sha256": plan.canonical_sha256(plan.resource_plan()), "reservation_usd": "8.00",
                 "automatic_retries": 0, "training": True, "native_execution": False,
                 "launch_authorized": True, "reuses_v9_one_shot_authorization": False}
    authority_envelope = envelope(authority, "local/authority.json")
    bindings["authority_sha256"] = authority_envelope["sha256"]
    binding = launch.ledger_snapshot(ledger)["binding"]
    request = plan.build_request(job=JOB, bindings=bindings, ledger=binding)
    return {"request": request, "authority_envelope": authority_envelope, "expected_bindings": bindings,
            "expected_ledger": binding, "public_sets_path": public, "receipt_dir": tmp_path / "receipts",
            "ledger_path": ledger}


class FakeProvider:
    def __init__(self, *, failure=None, change=None, partial=None):
        self.calls, self.failure, self.change, self.partial = [], failure, change, partial
        self.training, self.seals, self.clock = None, [], 1000.0
        self.created = False

    def mark(self, method, context):
        self.calls.append(method)
        assert (Path(context["receipt_dir"]) / "intent.json").is_file()
        receipt_method = "wait_prediction" if method.startswith("wait_prediction") else method
        assert list(Path(context["receipt_dir"]).glob("*" + receipt_method + "_intent.json"))
        if self.failure == method:
            raise RuntimeError("Injected provider failure, not an AWS operation")

    def preflight(self, context):
        self.mark("preflight", context)
        resource = context["resource_plan"]
        result = {**{key: resource[key] for key in ("account_id", "region", "instance_type", "instance_count")},
                  "read_only": True, "t4_rejected": True, "shutdown_capability_verified": False,
                  "shutdown_verification_stage": "BEFORE_WORKER_RELEASE", "conflicting_resources": [],
                  "pricing_receipt_sha256": context["bindings"]["pricing_receipt_sha256"], "rate_hourly_usd": "2.00"}
        if self.change == "price":
            result["rate_hourly_usd"] = "3.00"
        return result

    def reserve(self, context):
        self.mark("reserve", context)
        receipt = budget.reserve_budget(context["job"], context["bindings"]["source_commit"],
            context["bindings"]["archive_sha256"], "8.00", context["resource_plan"], context["ledger_path"])
        if self.change == "reserve_receipt":
            receipt["ledger_sha256"] = "9" * 64
        if self.change == "reserve_published_then_error":
            raise RuntimeError("Synthetic post-publication interruption")
        return receipt

    def launch(self, context):
        self.mark("launch", context)
        self.created = True
        result = {"job": context["job"], "instance_id": "i-123456789abcdef01", "instance_type": "g7.2xlarge",
                  "instance_count": 1, "shutdown_gate": {"verified": True, "instance_id": "i-123456789abcdef01",
                  "deadline_unix": context["deadline_unix"], "receipt_sha256": "7" * 64,
                  "worker_released_after_verification": True}}
        if self.change == "shutdown":
            result["shutdown_gate"]["verified"] = False
        return result

    @staticmethod
    def common(context):
        return {"job": context["job"], "run_id": context["run_id"],
                "source_sha256": context["bindings"]["source_sha256"],
                "manifest_sha256": context["bindings"]["manifest_sha256"],
                "material_sha256": context["bindings"]["material_receipt_sha256"]}

    def completed(self, context, artifact):
        status = self.partial or ("BLOCKED" if self.failure or self.change else "COMPLETE")
        return envelope({"schema": "cas-teaching-guest-complete/1", **self.common(context), "status": status,
                         "training_ready_sha256": context.get("training_ready_sha256"),
                         "campaign_summary_sha256": context.get("campaign_summary_sha256"),
                         "prediction_seals": context.get("prediction_seals", []), "artifact": artifact}, "results/complete.json")

    def wait_training(self, context, timeout):
        self.mark("wait_training", context)
        assert 4800 < timeout <= 6300
        if self.partial:
            archive = b"Synthetic partial exposure and checkpoint archive."
            self.partial_complete = self.completed(context, {"key": "results/artifacts.zip",
                "sha256": sha256(archive).hexdigest(), "bytes": len(archive)})
            return {"complete": self.partial_complete}
        campaign = {"schema": "cas-teaching-four-arm-campaign/1", "run_id": context["run_id"],
            "source_sha256": context["bindings"]["source_sha256"], "manifest_sha256": context["bindings"]["manifest_sha256"],
            "all_allocations_finished": True, "held_out_opened": False, "accepted_weights_updated": False, "arms": {}}
        for arm in launch.ARMS:
            family, curriculum = arm.split(".")
            initial = {"path": f"/synthetic/{arm}/txn-00000001/candidate.pt", "sha256": sha256((arm + "initial").encode()).hexdigest(),
                       "state_sha256": sha256((family + "initialstate").encode()).hexdigest(), "transaction": 1, "receipt_sha256": "5" * 64}
            selected = {"path": f"/synthetic/{arm}/txn-00000005/candidate.pt", "sha256": sha256((arm + "selected").encode()).hexdigest(),
                       "state_sha256": sha256((arm + "state4").encode()).hexdigest(), "transaction": 5, "receipt_sha256": "6" * 64}
            curve = [{"kind": "development", "epoch": epoch, "eligible": epoch >= 4,
                      "attempted": 64 if epoch >= 4 else 0, "correct": 64 if epoch == 4 else 40,
                      "checkpoint_sha256": sha256((arm + "state" + str(epoch)).encode()).hexdigest()} for epoch in range(1, 17)]
            campaign["arms"][arm] = {"run_id": context["run_id"] + "." + curriculum + "." + family,
                "curriculum": curriculum, "execution_mode": "cuda", "allocation_finished": True,
                "max_epochs": 16, "cursor": {"epoch": 16, "batch": 0, "stage": 0},
                "observed_optimizer_steps": 896, "observed_teaching_examples": 28672,
                "initial_checkpoint": initial, "selected_checkpoint": selected, "development_curve": curve}
        if self.change == "incomplete_counts":
            campaign["arms"]["cas.aligned"]["observed_optimizer_steps"] = 895
        if self.change == "wrong_checkpoint":
            campaign["arms"]["cas.aligned"]["selected_checkpoint"]["state_sha256"] = "8" * 64
        if self.change == "private_opened":
            campaign["held_out_opened"] = True
        campaign_envelope = envelope(campaign, "results/train/campaign_summary.json", pretty=True)
        ready = {"schema": "cas-teaching-training-ready/1", **self.common(context), "all_allocations_finished": True,
                 "train_exit": {"phase": "train", "pid": 101, "exit_code": 0, "exited": True},
                 "campaign_summary": ref(campaign_envelope),
                 "selected_checkpoints": {arm: value["selected_checkpoint"] for arm, value in campaign["arms"].items()}}
        if self.change == "train_alive":
            ready["train_exit"]["exited"] = False
        if self.change == "time_exhausted":
            self.clock = context["deadline_unix"]
        self.training = {"ready": envelope(ready, "results/train_ready.json"), "campaign": campaign_envelope}
        return self.training

    def release_public(self, context, release):
        self.mark("release_public", context)
        assert "wait_training" in self.calls and self.training
        assert release["training_ready_sha256"] == self.training["ready"]["sha256"]
        self.release = release
        return {"uploaded": True, "release_sha256": sha256(launch.canonical(release)).hexdigest(),
                "public_sha256": context["bindings"]["public_sets_sha256"]}

    def wait_prediction(self, context, run_index, timeout):
        self.mark("wait_prediction" + str(run_index), context)
        assert 0 < timeout <= 300
        names = {f"{arm}.{phase}.{split}.json" for arm in launch.ARMS for phase in ("untrained", "trained") for split in launch.SPLITS}
        seal = {"schema": "cas-teaching-blind-prediction-seal/1", "source_sha256": context["bindings"]["source_sha256"],
                "private_targets_opened": False, "native_execution": "UNEXECUTED",
                "artifacts": {name: {"path": "/synthetic/" + name, "sha256": "4" * 64, "bytes": 100} for name in names}}
        if self.change == "missing_prediction" and run_index == 2:
            del seal["artifacts"][sorted(names)[0]]
        seal_envelope = envelope(seal, f"results/predict{run_index}/prediction_seal.json", pretty=True)
        ready = {"schema": "cas-teaching-prediction-ready/1", **self.common(context), "run_index": run_index,
                 "training_ready_sha256": context["training_ready_sha256"], "campaign_summary_sha256": context["campaign_summary_sha256"],
                 "prediction_exit": {"phase": "predict", "pid": 101 + run_index, "exit_code": 0, "exited": True},
                 "prediction_seal": ref(seal_envelope)}
        if self.change == "same_pid" and run_index == 2:
            ready["prediction_exit"]["pid"] = 102
        return {"ready": envelope(ready, f"results/prediction{run_index}_ready.json"), "seal": seal_envelope}

    def collect(self, context, destination, timeout):
        self.mark("collect", context)
        assert timeout > 0
        raw = b"Synthetic partial exposure and checkpoint archive." if self.partial else b"Synthetic archive, no tensors, no native execution."
        path = Path(destination) / "artifacts.zip"
        path.write_bytes(raw)
        artifact = {"path": str(path), "key": "results/artifacts.zip", "sha256": sha256(raw).hexdigest(), "bytes": len(raw)}
        complete = self.partial_complete if self.partial else self.completed(context, {key: artifact[key] for key in ("key", "sha256", "bytes")})
        if self.change == "local_archive":
            path.write_bytes(raw + b"tamper")
        return {"complete": complete, "archive": artifact}

    def cleanup(self, context, retain_cloud_copy):
        self.mark("cleanup", context)
        self.retained = retain_cloud_copy
        return {"complete": True, "compute_closed": True, "instance_state": "TERMINATED" if self.created else "NOT_CREATED",
                "instance_terminated": self.created, "schedules_removed": True,
                "cloud_copy_retained": retain_cloud_copy and self.created, "cloud_copy_deleted": not retain_cloud_copy,
                "cloud_copy_state": ("OBSERVED_RETAINED" if self.created else "NOT_CREATED") if retain_cloud_copy else "DELETED_AFTER_LOCAL_VERIFICATION"}


def run(prepared, provider):
    return launch.execute(**prepared, provider=provider, now=lambda: provider.clock)


def test_full_one_shot_order_two_fresh_readers_and_verified_local_copy(prepared):
    provider = FakeProvider()
    result = run(prepared, provider)
    assert result["status"] == "TEACHING_CYCLE_COLLECTED_NOT_SCORED"
    assert provider.calls == ["preflight", "reserve", "launch", "wait_training", "release_public",
                              "wait_prediction1", "wait_prediction2", "collect", "cleanup"]
    assert result["archive"]["local_bytes_verified"] is True and provider.retained is False
    assert result["ledger_after"]["revision"] == result["ledger_before"]["revision"] + 1
    assert result["reservation"]["reservation"]["reserved_usd"] == "8.00"
    assert result["learning_results"] == "INDEPENDENT_SCORING_REQUIRED"
    assert result["native_execution"] == "UNEXECUTED"
    assert result["automatic_retries"] == 0


@pytest.mark.parametrize("method", ["preflight", "reserve", "launch", "wait_training", "release_public", "wait_prediction1", "wait_prediction2", "collect", "cleanup"])
def test_provider_failure_records_cleanup_no_reexecution(prepared, method):
    provider = FakeProvider(failure=method)
    result = run(prepared, provider)
    assert result["status"] == "TEACHING_CYCLE_BLOCKED"
    assert provider.calls.count("reserve") <= 1
    assert provider.calls.count("launch") <= 1
    assert provider.calls.count("wait_training") <= 1
    assert provider.calls.count("collect") <= 1
    assert provider.calls[-1] == "cleanup"
    assert (prepared["receipt_dir"] / "result.json").is_file()
    if method in ("preflight", "reserve", "launch", "collect"):
        assert provider.retained is True


@pytest.mark.parametrize("change,forbidden_call", [
    ("price", "reserve"), ("reserve_receipt", "launch"), ("shutdown", "wait_training"),
    ("incomplete_counts", "release_public"), ("wrong_checkpoint", "release_public"),
    ("private_opened", "release_public"), ("train_alive", "release_public"),
    ("time_exhausted", "release_public"), ("same_pid", None), ("missing_prediction", None), ("local_archive", None),
])
def test_invalid_receipt_stops_next_stage_and_preserves_evidence(prepared, change, forbidden_call):
    provider = FakeProvider(change=change)
    result = run(prepared, provider)
    assert result["status"] == "TEACHING_CYCLE_BLOCKED"
    if forbidden_call is not None:
        assert forbidden_call not in provider.calls
    assert provider.calls[-1] == "cleanup"
    if change in ("local_archive", "time_exhausted", "shutdown", "reserve_receipt", "price"):
        assert provider.retained is True


def test_incomplete_training_collects_prefix_before_cleanup_without_public_release(prepared):
    provider = FakeProvider(partial="TEACHING_INCOMPLETE")
    result = run(prepared, provider)
    assert result["status"] == "TEACHING_INCOMPLETE"
    assert provider.calls[-2:] == ["collect", "cleanup"]
    assert "release_public" not in provider.calls and "wait_prediction1" not in provider.calls
    assert result["archive"]["partial"] is True and result["archive"]["local_bytes_verified"] is True
    assert provider.retained is False


def test_failed_partial_collection_retains_sole_cloud_copy(prepared):
    provider = FakeProvider(partial="TEACHING_INCOMPLETE", failure="collect")
    result = run(prepared, provider)
    assert result["status"] == "TEACHING_INCOMPLETE"
    assert provider.retained is True and result["archive"] is None
    assert provider.calls.count("collect") == 1


def test_reservation_published_then_error_is_recorded_without_retry_or_refund(prepared):
    provider = FakeProvider(change="reserve_published_then_error")
    result = run(prepared, provider)
    assert result["status"] == "TEACHING_CYCLE_BLOCKED" and result["reservation"] is None
    assert result["ledger_after"]["revision"] == result["ledger_before"]["revision"] + 1
    assert provider.calls == ["preflight", "reserve", "cleanup"]
    assert (prepared["receipt_dir"] / "ledger_after_failure.json").is_file()


def test_evidence_sink_is_never_overwritten_or_reused(prepared):
    provider = FakeProvider()
    run(prepared, provider)
    calls = list(provider.calls)
    with pytest.raises(launch.LaunchError, match="FRESH_EVIDENCE_DIRECTORY_REQUIRED"):
        run(prepared, provider)
    assert provider.calls == calls


def test_consumed_v9_authority_rejected_before_provider(prepared):
    prepared["expected_bindings"]["authority_sha256"] = plan.V9_AUTHORITY_SHA256
    provider = FakeProvider()
    with pytest.raises(plan.PlanError, match="CONSUMED_V9_AUTHORITY_REJECTED"):
        run(prepared, provider)
    assert provider.calls == []


def test_exact_pretty_worker_raw_bytes_are_preserved():
    document = {"test": [1, 2, 3]}
    raw = envelope(document, "results/example.json", pretty=True)
    assert raw["sha256"] != sha256(launch.canonical(document)).hexdigest()
    assert launch.envelope_document(raw, key="results/example.json") == document
    raw["raw_utf8"] += " "
    with pytest.raises(launch.LaunchError, match="RAW_ENVELOPE_IDENTITY_MISMATCH"):
        launch.envelope_document(raw)


def test_preflight_refusal_reports_not_created_not_fake_termination(prepared):
    provider = FakeProvider(change="price")
    result = run(prepared, provider)
    assert result["cleanup"]["instance_state"] == "NOT_CREATED"
    assert result["cleanup"]["compute_closed"] is True
    assert result["cleanup"]["instance_terminated"] is False
