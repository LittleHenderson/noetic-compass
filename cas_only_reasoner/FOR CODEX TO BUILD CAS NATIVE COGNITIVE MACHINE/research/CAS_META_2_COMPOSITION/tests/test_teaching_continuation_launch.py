"""Fake-provider continuation protocol checks; no AWS or canonical ledger I/O.

Existing envelope/provider fixture helpers are reused. Their budget operation is
overridden by an in-memory ledger, and prior package admission is explicitly a
fake seam here. The separate prior-package suite checks real byte validation.
"""
from copy import deepcopy
from decimal import Decimal
from hashlib import sha256
import importlib.util
import json
from pathlib import Path

import pytest

from aws import budget, teaching_continuation_plan as plan, teaching_continuation_launch as launch


def helper(name):
    spec = importlib.util.spec_from_file_location("_continuation_" + name, Path(__file__).with_name(name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


old = helper("test_teaching_cycle_launch")
plan_tests = helper("test_teaching_continuation_plan")
envelope, ref = old.envelope, old.ref


def prior_arms():
    result = {}
    for arm in launch.ARMS:
        family, curriculum = arm.split(".")
        result[arm] = {"run_id": plan.LOGICAL_RUN_ID + "." + curriculum + "." + family,
            "committed_cursor": {"epoch": 7, "batch": 2 if arm == "cas.aligned" else 0,
                                 "stage": 5 if arm == "cas.aligned" else 0},
            "committed_optimizer_steps": 411 if arm == "cas.aligned" else 392,
            "committed_transactions": 9 if arm == "cas.aligned" else 8,
            "checkpoint_file_sha256": sha256((arm + "prior-file").encode()).hexdigest(),
            "checkpoint_state_sha256": sha256((arm + "prior-state").encode()).hexdigest(),
            "checkpoint_receipt_sha256": sha256((arm + "prior-receipt").encode()).hexdigest(),
            "pending_development": False}
    return result


class FakeLedger:
    def __init__(self, path):
        self.path = str(path)
        self.state = {"revision": 21, "reservations": [], "approval": "synthetic test only",
            "predecessor": None, "owner_task_cap_usd": "400.00", "scope": "synthetic",
            "no_automatic_refund": True, "total_reserved_usd": "118.00", "remaining_unreserved_usd": "282.00"}

    def snapshot(self, path):
        assert str(path) == self.path
        state = deepcopy(self.state)
        return {"ledger_path": self.path, "ledger": state, "binding": {"revision": state["revision"],
            "sha256": budget.digest(budget.encoded(state)), "cap_usd": "400.00",
            "reserved_usd": state["total_reserved_usd"], "unreserved_usd": state["remaining_unreserved_usd"]}}

    def reserve(self, context):
        prior = deepcopy(self.state)
        row = {"job": context["job"], "source_sha": context["bindings"]["source_commit"],
            "archive_sha256": context["bindings"]["archive_sha256"], "reserved_usd": "8.00", "status": budget.STATUS,
            "plan": context["resource_plan"], "plan_sha256": budget.digest(budget.encoded(context["resource_plan"]))}
        self.state.update(revision=prior["revision"] + 1, previous_state_sha256=budget.digest(budget.encoded(prior)),
            reservations=prior["reservations"] + [row], total_reserved_usd="126.00", remaining_unreserved_usd="274.00")
        snapshot = self.snapshot(self.path)
        return {"reservation": row, "ledger_path": self.path, "ledger_sha256": snapshot["binding"]["sha256"],
            **{key: self.state[key] for key in ("revision", "total_reserved_usd", "remaining_unreserved_usd")}}


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    ledger = FakeLedger(tmp_path / "in-memory-ledger.json")
    monkeypatch.setattr(launch, "ledger_snapshot", ledger.snapshot)
    def fake_prior(context):
        context["prior_tree_expected"] = {"files": 101, "bytes": 900000, "sha256": "a" * 64}
        return prior_arms()
    monkeypatch.setattr(launch, "_prior_input", fake_prior)
    public = tmp_path / "public.json"
    public.write_bytes((Path(__file__).resolve().parents[1] / "records/teaching_cycle_001/job_003/public.json").read_bytes())
    bindings, continuation = plan_tests.bindings(), plan_tests.continuation()
    job = "cas-meta2-teaching-20260908090000-abcd1234"
    authority = {"schema": launch.AUTHORITY_SCHEMA, "task_scope": plan.TASK_SCOPE, "job": job,
        "logical_run_id": plan.LOGICAL_RUN_ID, "continuation": continuation,
        "bindings": {key: value for key, value in bindings.items() if key != "authority_sha256"},
        "resource_plan_sha256": plan.canonical_sha256(plan.resource_plan()), "reservation_usd": "8.00",
        "automatic_retries": 0, "training": True, "native_execution": False, "launch_authorized": True,
        "reuses_v9_one_shot_authorization": False, "reuses_original_reservation": False}
    authority_envelope = envelope(authority, "local/continuation_authority.json")
    bindings["authority_sha256"] = authority_envelope["sha256"]
    expected = ledger.snapshot(ledger.path)["binding"]
    request = plan.build_request(job=job, logical_run_id=plan.LOGICAL_RUN_ID, bindings=bindings,
                                 continuation=continuation, ledger=expected)
    return {"arguments": {"request": request, "authority_envelope": authority_envelope,
        "expected_bindings": bindings, "expected_continuation": continuation, "expected_ledger": expected,
        "public_sets_path": public, "prior_state_archive_path": tmp_path / "fake-prior.zip",
        "prior_state_manifest_path": tmp_path / "fake-prior-manifest.json", "receipt_dir": tmp_path / "receipts",
        "ledger_path": Path(ledger.path)}, "ledger": ledger}


class FakeProvider(old.FakeProvider):
    def __init__(self, ledger, **kwargs):
        super().__init__(**kwargs)
        self.ledger = ledger
        self.training_released = False

    @staticmethod
    def common(context):
        return {**old.FakeProvider.common(context), "continuation_sha256": plan.canonical_sha256(context["continuation"]),
            "restore_ready_sha256": context.get("restore_ready_sha256"),
            "restore_receipt_sha256": context.get("restore_receipt_sha256")}

    def preflight(self, context):
        result = super().preflight(context)
        result["rate_hourly_usd"] = "2.52" if self.change != "price" else "3.00"
        result["raw_prices"] = plan_tests.prices()
        result["cost_worksheet"] = plan.worksheet(result["raw_prices"])
        if self.change == "old_storage_worksheet":
            result["cost_worksheet"] = plan_tests.original_worksheet(result["raw_prices"])
        return result

    def reserve(self, context):
        self.mark("reserve", context)
        receipt = self.ledger.reserve(context)
        if self.change == "reserve_published_then_error":
            raise RuntimeError("Synthetic receipt failure after in-memory append")
        return receipt

    def wait_restore(self, context, timeout):
        self.mark("wait_restore", context)
        assert 180 < timeout <= 6300  # Setup/download time is not the probe's180s cap.
        probe = {"schema": "cas-teaching-gpu-restore/1", "status": "RESTORED_NO_TRAINING",
            "job": context["job"], "run_id": context["run_id"], "source_sha256": context["bindings"]["source_sha256"],
            "bundle_manifest_sha256": context["bindings"]["manifest_sha256"],
            "material_sha256": context["bindings"]["material_receipt_sha256"],
            "source_archive_sha256": context["bindings"]["archive_sha256"],
            "prior_archive_sha256": context["continuation"]["prior_state_archive_sha256"],
            "prior_manifest_sha256": context["continuation"]["prior_state_manifest_sha256"],
            "summary_sha256": context["continuation"]["prior_summary_sha256"],
            "probe_sha256": context["continuation"]["restore_probe_sha256"],
            "validator_sha256": context["continuation"]["prior_package_validator_sha256"],
            "input_tree_unchanged": True, "optimizer_steps_performed": 0, "predictions_run": False,
            "actual_restore": "FOUR_ARMS_RESTORED", "pid": 100, "wall_seconds": 25.0, "arms": {},
            "instance": {"instanceId": context["launch"]["instance_id"], "accountId": "807562639912",
                "region": "us-west-2", "instanceType": "g7.2xlarge"},
            "environment": {"torch": "2.11.0+cu128", "cuda": "12.8", "gpu": "NVIDIA RTX PRO 4500", "device": "cuda:0"},
            "prior_tree_before": context["prior_tree_expected"], "prior_tree_after": context["prior_tree_expected"]}
        for arm, row in context["prior_arms"].items():
            family = arm.split(".")[0]
            probe["arms"][arm] = {**row, "optimizer_state_sha256": "7" * 64,
                "saved_optimizer_state_sha256": "7" * 64, "scope_sha256": "8" * 64,
                "training_cases_sha256": context["bindings"]["training_cases_sha256"], "record_registry_sha256": "9" * 64,
                "initial_state_sha256": sha256((family + "initialstate").encode()).hexdigest(),
                "optimizer_steps_performed": 0, "predictions_run": False, "optimizer_tensors_device_checked": 9}
        if self.change == "restore_optimizer":
            probe["arms"]["cas.aligned"]["saved_optimizer_state_sha256"] = "6" * 64
        if self.change == "restore_cursor":
            probe["arms"]["cas.aligned"]["committed_cursor"] = {"epoch": 7, "batch": 0, "stage": 0}
        if self.change == "restore_updated":
            probe["optimizer_steps_performed"] = 1
        if self.change == "restore_boolean_zero":
            probe["optimizer_steps_performed"] = False
        if self.change == "restore_wrong_source":
            probe["source_sha256"] = "f" * 64
        if self.change == "restore_too_slow":
            probe["wall_seconds"] = 181
        if self.change == "restore_wrong_instance":
            probe["instance"]["instanceId"] = "i-00000000000000000"
        if self.change == "restore_wrong_gpu":
            probe["environment"]["gpu"] = "T4"
        if self.change == "restore_tree_changed":
            probe["prior_tree_after"] = {**probe["prior_tree_before"], "sha256": "b" * 64}
        if self.change == "restore_tree_relabelled":
            probe["prior_tree_before"] = {**probe["prior_tree_before"], "sha256": "b" * 64}
            probe["prior_tree_after"] = probe["prior_tree_before"]
        if self.change == "restore_device_unchecked":
            probe["arms"]["cas.aligned"]["optimizer_tensors_device_checked"] = 0
        probe_envelope = envelope(probe, launch.RESTORE_KEY, pretty=True)
        ready = {"schema": "cas-teaching-continuation-restore-ready/1", **self.common(context),
            "restore_receipt": ref(probe_envelope), "restore_exit": {"phase": "restore", "pid": 100, "exit_code": 0, "exited": True}}
        if self.change == "restore_raw_pin":
            ready["restore_receipt"]["sha256"] = "f" * 64
        self.restored = {"ready": envelope(ready, "results/restore_ready.json"), "probe": probe_envelope}
        return self.restored

    def release_training(self, context, release):
        self.mark("release_training", context)
        assert release["restore_receipt_sha256"] == self.restored["probe"]["sha256"]
        assert release["run_id"] == plan.LOGICAL_RUN_ID != release["job"]
        self.training_released = True
        return {"uploaded": True, "release_sha256": sha256(launch.canonical(release)).hexdigest(),
            "restore_receipt_sha256": release["restore_receipt_sha256"]}

    def wait_training(self, context, timeout):
        assert self.training_released
        result = super().wait_training(context, timeout)
        if "complete" in result:
            return result
        campaign = launch.envelope_document(result["campaign"])
        campaign["campaign_root"] = plan.ORIGINAL_CAMPAIGN_ROOT
        campaign["resumed_summary_sha256"] = context["continuation"]["prior_summary_sha256"]
        for arm, row in campaign["arms"].items():
            for key in ("initial_checkpoint", "selected_checkpoint"):
                reference = row[key]
                reference["path"] = plan.ORIGINAL_CAMPAIGN_ROOT + f"/{arm}/journal/txn-{reference['transaction']:08d}/candidate.pt"
        if self.change == "wrong_resume_summary":
            campaign["resumed_summary_sha256"] = "f" * 64
        if self.change == "relocated_campaign":
            campaign["campaign_root"] = "/opt/changed/campaign"
        campaign_envelope = envelope(campaign, launch.CAMPAIGN_KEY, pretty=True)
        ready = launch.envelope_document(result["ready"])
        ready["campaign_summary"] = ref(campaign_envelope)
        ready["selected_checkpoints"] = {arm: row["selected_checkpoint"] for arm, row in campaign["arms"].items()}
        if self.change == "reused_restore_pid":
            ready["train_exit"]["pid"] = 100
        if self.change == "lost_restore_binding":
            ready["restore_receipt_sha256"] = "f" * 64
        self.training = {"ready": envelope(ready, "results/train_ready.json"), "campaign": campaign_envelope}
        return self.training


def run(prepared, provider):
    return launch.execute(**prepared["arguments"], provider=provider, now=lambda: provider.clock)


def test_full_restore_admission_precedes_training_and_then_public_release(prepared):
    provider = FakeProvider(prepared["ledger"])
    result = run(prepared, provider)
    assert result["status"] == "TEACHING_CONTINUATION_COLLECTED_NOT_SCORED", result["failure"]
    assert provider.calls == ["preflight", "reserve", "launch", "wait_restore", "release_training", "wait_training",
        "release_public", "wait_prediction1", "wait_prediction2", "collect", "cleanup"]
    assert result["job"] != result["run_id"] == plan.LOGICAL_RUN_ID
    assert result["restore_receipt_sha256"] == provider.restored["probe"]["sha256"]
    assert result["campaign_summary_sha256"] == provider.training["campaign"]["sha256"]
    assert result["archive"]["local_bytes_verified"] is True
    assert result["learning_results"] == "INDEPENDENT_SCORING_REQUIRED"
    assert result["native_execution"] == "UNEXECUTED" and result["reuses_original_reservation"] is False
    assert result["ledger_after"]["revision"] == result["ledger_before"]["revision"] + 1


@pytest.mark.parametrize("method", ["preflight", "reserve", "launch", "wait_restore", "release_training", "wait_training",
    "release_public", "wait_prediction1", "wait_prediction2", "collect", "cleanup"])
def test_one_attempt_and_cleanup_at_every_failure_stage(prepared, method):
    provider = FakeProvider(prepared["ledger"], failure=method)
    result = run(prepared, provider)
    assert result["status"] == "TEACHING_CONTINUATION_BLOCKED"
    for one_shot in ("reserve", "launch", "wait_restore", "release_training", "wait_training", "collect"):
        assert provider.calls.count(one_shot) <= 1
    assert provider.calls[-1] == "cleanup"
    if method in ("wait_restore", "release_training"):
        assert "wait_training" not in provider.calls and "release_public" not in provider.calls


@pytest.mark.parametrize("change,forbidden", [("restore_optimizer", "release_training"), ("restore_cursor", "release_training"),
    ("restore_updated", "release_training"), ("restore_boolean_zero", "release_training"), ("restore_raw_pin", "release_training"),
    ("restore_wrong_source", "release_training"), ("restore_too_slow", "release_training"),
    ("restore_wrong_instance", "release_training"), ("restore_wrong_gpu", "release_training"),
    ("restore_tree_changed", "release_training"), ("restore_tree_relabelled", "release_training"),
    ("restore_device_unchecked", "release_training"),
    ("old_storage_worksheet", "reserve"), ("wrong_resume_summary", "release_public"), ("relocated_campaign", "release_public"),
    ("reused_restore_pid", "release_public"), ("lost_restore_binding", "release_public"),
    ("incomplete_counts", "release_public"), ("wrong_checkpoint", "release_public")])
def test_resealed_wrong_receipts_do_not_release_next_phase(prepared, change, forbidden):
    provider = FakeProvider(prepared["ledger"], change=change)
    result = run(prepared, provider)
    assert result["status"] == "TEACHING_CONTINUATION_BLOCKED"
    assert forbidden not in provider.calls
    assert provider.calls[-1] == "cleanup"


def test_incomplete_continuation_keeps_prefix_without_releasing_final_inputs(prepared):
    provider = FakeProvider(prepared["ledger"], partial="TEACHING_INCOMPLETE")
    result = run(prepared, provider)
    assert result["status"] == "TEACHING_INCOMPLETE"
    assert provider.calls[-2:] == ["collect", "cleanup"]
    assert "release_public" not in provider.calls and "wait_prediction1" not in provider.calls
    assert result["archive"]["partial"] is True


def test_collection_failure_never_deletes_sole_cloud_copy(prepared):
    provider = FakeProvider(prepared["ledger"], partial="TEACHING_INCOMPLETE", failure="collect")
    result = run(prepared, provider)
    assert result["archive"] is None and provider.retained is True
    assert provider.calls.count("collect") == 1


def test_prior_package_failure_happens_before_any_reservation(prepared, monkeypatch):
    def reject(context):
        raise launch.LaunchError("Synthetic prior-byte mismatch")
    monkeypatch.setattr(launch, "_prior_input", reject)
    provider = FakeProvider(prepared["ledger"])
    result = run(prepared, provider)
    assert provider.calls == ["cleanup"]
    assert result["reservation"] is None
    assert result["cleanup"]["instance_state"] == "NOT_CREATED"


def test_uncertain_reservation_is_observed_not_retried_or_refunded(prepared):
    provider = FakeProvider(prepared["ledger"], change="reserve_published_then_error")
    result = run(prepared, provider)
    assert result["reservation"] is None
    assert result["ledger_after"]["revision"] == result["ledger_before"]["revision"] + 1
    assert provider.calls == ["preflight", "reserve", "cleanup"]
    assert result["reservation_refunded"] is False


def test_receipt_directory_is_never_reused(prepared):
    provider = FakeProvider(prepared["ledger"])
    run(prepared, provider)
    calls = list(provider.calls)
    with pytest.raises(launch.LaunchError, match="FRESH_EVIDENCE_DIRECTORY_REQUIRED"):
        run(prepared, provider)
    assert provider.calls == calls
