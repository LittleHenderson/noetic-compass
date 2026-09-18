"""Pure admission, leakage and launch-envelope regressions for the practice study (owner-approved 2026-09-18)."""
import ast
import builtins
from collections import Counter
from decimal import Decimal
from fractions import Fraction
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

# Self-contained import path: do not depend on another test module having run first.
for _extra in (Path(__file__).resolve().parents[1], Path(__file__).resolve().parents[1] / "research/CAS_META_2_COMPOSITION"):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

from cas_meta2.typed_teaching import practice_contract as contract
from cas_meta2.typed_teaching import practice_learner
from cncm import typed_practice_worker as worker
from aws import typed_practice_launch as launch
from aws import typed_matched_launch as matched_launch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "a" * 40
JOB = "cas-meta2-tprac-20260918000000-aaaaaaaa-m-20260917"


def _gates_module():
    spec = importlib.util.spec_from_file_location("practice_gates", ROOT / "records/typed_practice_001/evaluate_gates.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def public_only(monkeypatch):
    original = builtins.__import__
    def guarded(name, *args, **kwargs):
        if name.split(".")[0] in {"torch", "numpy", "boto3", "botocore", "cas_cjt", "casformer"}:
            raise AssertionError("NUMERIC_PROVIDER_IMPORT:" + name)
        if name.endswith(("graph_teaching.final_panel", "graph_teaching.reference")):
            raise AssertionError("FINAL_IMPORT:" + name)
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", guarded)


@pytest.fixture(scope="module")
def material():
    return contract.load_material(ROOT)


def test_held_back_is_whole_worlds_and_leak_free(material):
    frozen = material[0]
    held, trained, excluded = contract.split(frozen)
    worlds = set(contract.held_worlds(frozen))
    assert (len(worlds), len(held), len(trained), len(excluded)) == (5, 127, 358, 79)
    assert len(contract.held_back_questions(frozen)) == 50
    held_set, trained_set = set(held), set(trained)
    for row in frozen["registry"]:
        if row["source_world_id"] in worlds:
            assert row["record_id"] in held_set
        if row["record_id"] in trained_set:
            text = json.dumps({k: v for k, v in row.items() if k != "record_id"})
            assert not any(world in text for world in worlds), "a trained record mentions a held world"
    by_query = {}
    for row in frozen["registry"]:
        by_query.setdefault(row["query"]["query_id"], set()).add(row["record_id"])
    for records in by_query.values():
        assert records <= held_set or not records & held_set, "a question is split across the two sides"
    kinds = Counter(r["query"]["kind"] for r in frozen["registry"] if r["record_id"] in held_set)
    assert set(kinds) == set(contract.KINDS)


def test_ten_identical_passes_train_only_trained_records(material):
    frozen = material[0]
    trained = set(contract.split(frozen)[1])
    batches, stats = contract.practice_schedule(frozen)
    assert stats["main_updates"] == len(batches) == 1470 and stats["updates_per_pass"] == 147
    assert [b["cursor"] for b in batches] == list(range(len(batches)))
    passes = [[(b["record_ids"], b["depth"]) for b in batches if b["pass"] == n] for n in range(1, 11)]
    assert all(p == passes[0] for p in passes)
    assert all(key in trained for b in batches for key in b["record_ids"])
    occurrences = [o for b in batches for o in b["occurrence_ids"]]
    assert len(occurrences) == len(set(occurrences))


def test_interference_draws_only_trained_records(material):
    frozen = material[0]
    trained = set(contract.split(frozen)[1])
    inter = contract.interference_batches(frozen)
    assert len(inter) == 16 and all(len(b["record_ids"]) == 8 for b in inter)
    assert all(key in trained for b in inter for key in b["record_ids"])


def test_update_bound_is_pinned_to_the_schedule(material):
    _, stats = contract.practice_schedule(material[0])
    assert launch.OPTIMIZER_UPDATES_MAX == stats["main_updates"] + contract.INTERFERENCE_UPDATES + contract.REPLAY_UPDATES
    assert stats["main_updates"] + contract.INTERFERENCE_UPDATES <= practice_learner.PRACTICE_MAX_UPDATES
    assert worker.expected_main_delta(stats)["optimizer_updates"] == 1470


def test_gate_population_is_frozen(material):
    gates = _gates_module()
    frozen = material[0]
    held, trained, _ = contract.split(frozen)
    eligible, shortcut_hit, shortcut = gates.eligible_questions(frozen, set(trained), contract.held_back_questions(frozen))
    assert (len(eligible), len(shortcut_hit)) == (45, 5)
    assert shortcut["reach"] == '{"state": "DIRECT", "via": null}'


def test_holdout_split_rederives_from_its_rules_with_the_answer_checker(material):
    spec = importlib.util.spec_from_file_location("holdout_audit", ROOT / "records/typed_practice_001/holdout_audit.py")
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    frozen = material[0]
    derived = audit.derive(frozen)
    held, trained, excluded = contract.split(frozen)
    assert derived["held_worlds"] == list(contract.HELD_WORLDS)
    assert derived["answer_only_exposed"] == sorted(contract.ANSWER_EXPOSED_RECORD_IDS)
    assert (derived["held"], derived["trained"], derived["excluded"]) == (held, trained, excluded)
    assert len(derived["eligible_worlds"]) == 12


def test_gate_counts_questions_and_one_flip_cannot_pass():
    gates = _gates_module()
    kind_of = {"q%d" % i: ("reach" if i < 10 else "parts") for i in range(20)}
    keys = sorted(kind_of)
    before = {k: False for k in keys}
    one = dict(before, q0=True)
    assert gates.seed_test(before, one, keys, kind_of)["passed"] is False
    seven_one_kind = dict(before, **{"q%d" % i: True for i in range(7)})
    assert gates.seed_test(before, seven_one_kind, keys, kind_of)["passed"] is False      # one kind only
    seven_two_kinds = dict(before, **{"q%d" % i: True for i in (0, 1, 2, 3, 10, 11, 12)})
    result = gates.seed_test(before, seven_two_kinds, keys, kind_of)
    assert result["passed"] is True and result["p_one_sided"] == "1/128"
    records = {"r1": True, "r2": False}
    assert gates.question_outcomes(records, {"q": ["r1", "r2"]}) == {"q": False}
    one_world = {k: "w1" for k in keys}
    assert gates.seed_test(before, seven_two_kinds, keys, kind_of, one_world)["passed"] is False   # one world only
    two_worlds = dict(one_world, q10="w2")
    assert gates.seed_test(before, seven_two_kinds, keys, kind_of, two_worlds)["passed"] is True


def test_publish_is_whole_and_create_only(tmp_path):
    pin = worker._publish_bytes(tmp_path / "x.json", b"{}\n")
    assert pin["bytes"] == 3 and not (tmp_path / "x.json.partial").exists()
    with pytest.raises(ValueError, match="PUBLISH_DESTINATION"):
        worker._publish_bytes(tmp_path / "x.json", b"{}\n")


def test_artifact_contract_is_bounded_and_covers_every_checkpoint():
    names = worker.EXPECTED_ARTIFACTS
    assert len(names) == len(set(names)) < 500 and all(Path(n).name == n for n in names)
    for n in (0, 1, 10):
        assert "course_p%02d_scoring.json" % n in names
    for n in (2, 4, 6, 8):
        assert "heldback_p%02d_scoring.json" % n in names
    for n in contract.PASS_CHECKPOINTS:
        assert "development_p%02d_scoring.json" % n in names
    assert {"pass_10_batches.jsonl", "interference_updates.jsonl", "retained.pt", "replay_2_update.json",
            "pass_01.pt", "prelast.pt"} <= set(names)
    assert launch.evidence_contract()["required_count"] == len(names) + 3


def test_time_envelope_is_ordered_and_longer_than_the_shared_two_hours():
    assert (contract.WORKER_DEADLINE_SECONDS < launch.MAX_WALL_SECONDS < launch.OUTER_TIMEOUT_SECONDS
            < launch.BOOT_WATCHDOG_SECONDS < launch.INSTANCE_SECONDS_MAX)
    assert launch.shared.RESOURCE_PLAN["instance_seconds_max"] == 7200 < launch.BOOT_WATCHDOG_SECONDS
    assert launch.BOUNDS["max_wall_seconds"] == 12600 and launch.BOUNDS["reservation_usd"] == "15.00"


def test_reservation_plan_admits_fifteen_dollars_for_four_hours_and_not_seven():
    budget = launch.budget
    plan = launch.reservation_plan_for({"model_seed": 20260917})
    assert plan["runtime_seconds_max"] == 14400 and plan["task_scope"] == "cncm_typed_practice_001"
    assert budget.validate_plan(plan, "15.00") == Decimal("11.56")
    with pytest.raises(ValueError, match="RESERVATION_BELOW_DECLARED_COST_BOUND"):
        budget.validate_plan(plan, "7.00")
    assert 3 * Decimal(launch.RESERVATION_USD) <= Decimal("45.00")


def _provider(**fields):
    provider = object.__new__(launch.TypedPracticeProvider)
    provider.bound_config = {"design": {"model_seed": 20260917}, "bucket": JOB + "-807562639912"}
    provider._reserved, provider.calls = False, []
    provider.job, provider.source_sha, provider.archive_sha256 = JOB, SOURCE, "b" * 64
    provider.manifest_sha256, provider.ledger_path = "c" * 64, Path("UNUSED")
    provider._event = lambda *a, **kw: None
    for key, value in fields.items():
        setattr(provider, key, value)
    return provider


def test_reservation_uses_the_practice_amount_and_refuses_a_retry():
    captured = []
    provider = _provider(budget=SimpleNamespace(reserve_budget=lambda *args: captured.append(args) or {"reserved": True}),
                         _record_aws_side_reservation=lambda receipt: {"status": "SYNTHETIC"})
    provider.reserve("7.00")
    assert captured[0][3] == "15.00" and captured[0][4]["runtime_seconds_max"] == 14400
    with pytest.raises(ValueError):
        provider.reserve("7.00")
    with pytest.raises(ValueError, match="PRACTICE_RESERVATION_CALLER"):
        _provider(budget=None).reserve("15.00")


def test_reserved_transition_requires_the_frozen_fifteen_dollars():
    budget = launch.budget
    plan = launch.reservation_plan_for({"model_seed": 20260917})
    request = {"job": JOB, "source_sha": SOURCE, "archive_sha256": "b" * 64}
    prior = {"revision": 0, "reservations": []}
    def ledger(amount):
        return {"revision": 1, "previous_state_sha256": budget.digest(budget.encoded(prior)),
                "reservations": [{**request, "status": budget.STATUS, "reserved_usd": amount, "plan": plan,
                                  "plan_sha256": budget.digest(budget.encoded(plan))}]}
    receipt = {"ledger_sha256": "c" * 64}
    before = {"ledger": prior}
    assert launch.validate_reserved_transition(before, {"ledger": ledger("15.00"), "ledger_sha256": "c" * 64},
                                               receipt, request, expected_plan=plan) == receipt
    with pytest.raises(ValueError, match="PRACTICE_RESERVATION_AMOUNT_FROZEN"):
        launch.validate_reserved_transition(before, {"ledger": ledger("7.00"), "ledger_sha256": "c" * 64},
                                            receipt, request, expected_plan=plan)


def test_wait_continues_past_the_shared_two_hour_segment(monkeypatch):
    outcomes = iter([{"worker_status": "REMOTE_TIMED_OUT"}, {"worker_status": "REMOTE_FINISHED"}])
    seen = []
    def fake_wait(self, job, timeout, *, poll_interval=5.0):
        seen.append(timeout)
        return next(outcomes)
    monkeypatch.setattr(matched_launch.TypedMatchedProvider, "wait", fake_wait)
    provider = _provider()
    assert provider.wait(JOB, 7200) == {"worker_status": "REMOTE_FINISHED"}
    assert len(seen) == 2 and all(0 < t <= 7200 for t in seen)
    with pytest.raises(ValueError, match="PRACTICE_WAIT_CALLER"):
        provider.wait(JOB, 3600)


def test_wait_survives_a_transient_network_error_and_not_a_real_one(monkeypatch):
    events = []
    outcomes = iter([ConnectionError("wifi dropped"), {"worker_status": "REMOTE_FINISHED"}])
    def fake_wait(self, job, timeout, *, poll_interval=5.0):
        item = next(outcomes)
        if isinstance(item, Exception):
            raise item
        return item
    monkeypatch.setattr(matched_launch.TypedMatchedProvider, "wait", fake_wait)
    monkeypatch.setattr(launch.time, "sleep", lambda seconds: None)
    provider = _provider(_client_error=type("NoClientError", (Exception,), {}))
    provider._event = lambda *a, **kw: events.append(a)
    assert provider.wait(JOB, 7200) == {"worker_status": "REMOTE_FINISHED"} and events[0][0] == "wait_transient_error"
    network = type("EndpointConnectionError", (Exception,), {})
    credentials = type("NoCredentialsError", (Exception,), {})
    assert provider._transient(network("down")) is True and provider._transient(credentials("none")) is False
    def broken(self, job, timeout, *, poll_interval=5.0):
        raise ValueError("CURRICULUM_RESULT_IDENTITY")
    monkeypatch.setattr(matched_launch.TypedMatchedProvider, "wait", broken)
    with pytest.raises(ValueError, match="CURRICULUM_RESULT_IDENTITY"):
        provider.wait(JOB, 7200)


def test_guest_watchdog_uses_the_practice_envelope(monkeypatch):
    parent = matched_launch.TypedMatchedProvider.__mro__[1]
    monkeypatch.setattr(parent, "_user_data", lambda self, bucket: "#!/bin/sh\nPY=''\nrun_worker\n")
    text = _provider()._user_data(JOB + "-807562639912")
    assert "--on-boot=14100s" in text and " 13500s " in text and "boot_deadline_seconds=14100" in text
    assert "6900" not in text and "4200s" not in text


def test_rendered_worker_binds_the_practice_entrypoint():
    text = launch.render_worker()
    ast.parse(text)
    assert "typed_practice_worker" in text and "typed_matched_worker" not in text and "12600" in text


def test_practice_learner_changes_only_the_two_ceilings():
    ok = {"max_updates": 1586, "max_core_calls": 600000, "max_wall_seconds": 12300}
    assert practice_learner.validate_practice_limits(ok) == ok
    for key, bad in (("max_updates", 2049), ("max_wall_seconds", 14401), ("max_core_calls", 1000001)):
        with pytest.raises(ValueError, match="PRACTICE_LEARNER_LIMITS"):
            practice_learner.validate_practice_limits({**ok, key: bad})
    profile = practice_learner.practice_profile()
    assert profile["changes"] == "UPDATE_AND_WALL_CEILINGS_ONLY" and profile["max_updates_ceiling"] == 2048


def test_owner_record_must_name_its_own_job(tmp_path):
    record = {"schema": launch.OWNER_SCHEMA, "candidate": launch.CANDIDATE, "owner_instruction_raw": "Practice test (Recommended)",
              "job": JOB, "bounds": launch.BOUNDS}
    path = tmp_path / "owner.json"
    path.write_bytes(launch.canonical(record))
    authority = {"owner_authorization_sha256": launch.digest(path.read_bytes()), "job": JOB}
    assert launch.validate_owner(path, authority)["job"] == JOB
    with pytest.raises(ValueError, match="PRACTICE_OWNER_JOB"):
        launch.validate_owner(path, {**authority, "job": JOB.replace("20260917", "20260918")})


def test_worker_refuses_windows_before_any_numerical_import(tmp_path, monkeypatch, material):
    from cas_meta2.teaching_cycle import gpu_adapter
    monkeypatch.setattr(gpu_adapter.platform, "system", lambda: "Windows")
    config = contract.make_config(ROOT, source_sha=SOURCE, job=JOB, bucket=JOB + "-807562639912", model_seed=20260917)
    assert len(config["bucket"]) <= 63 and config["design"]["held_back_record_ids"] == contract.split(material[0])[0]
    results = tmp_path / "results"
    with pytest.raises(ValueError, match="LINUX_WORKER_REQUIRED"):
        worker.run(config, ROOT, results, results / "artifacts")
    assert json.loads((results / "result.json").read_bytes())["status"] == "TYPED_PRACTICE_FAILED"


def test_gate_arithmetic_is_exact():
    gates = _gates_module()
    assert gates.binomial_upper_tail(0, 0) == 1
    assert gates.binomial_upper_tail(10, 10) == Fraction(1, 1024)
    assert gates.binomial_upper_tail(5, 10) == Fraction(638, 1024)
    before = {"a": False, "b": True, "c": False}
    after = {"a": True, "b": False, "c": False}
    assert gates.paired(before, after, ["a", "b", "c"]) == {"wrong_to_right": 1, "right_to_wrong": 1, "pairs": 3}


@pytest.mark.parametrize("job", [JOB.replace("20260917", "20260920"), JOB.replace("-m-", "-a-"), JOB + "-retry"])
def test_unfrozen_job_parameters_rejected(job):
    with pytest.raises(ValueError):
        contract.parse_job(job)
