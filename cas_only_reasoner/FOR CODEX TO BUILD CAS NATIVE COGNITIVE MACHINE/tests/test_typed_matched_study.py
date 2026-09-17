"""Pure admission and leakage/failure regressions for the matched study."""
import ast
import builtins
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from cas_meta2.typed_teaching import matched_contract as contract, source, development
from cncm import typed_matched_worker as worker
from aws import typed_matched_launch as launch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "a" * 40
JOB = "cas-meta2-tmat-20260917000000-aaaaaaaa-a-20260917"


@pytest.fixture(autouse=True)
def public_only(monkeypatch):
    original = builtins.__import__
    def guarded(name, *args, **kwargs):
        if name.split(".")[0] in {"torch", "numpy", "boto3", "botocore", "cas_cjt", "casformer"}:
            raise AssertionError("NUMERIC_PROVIDER_IMPORT:" + name)
        if name.endswith(("typed_teaching.checker", "graph_teaching.final_panel", "graph_teaching.reference")):
            raise AssertionError("PRIVATE_OR_FINAL_IMPORT:" + name)
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", guarded)


@pytest.fixture(scope="module")
def material():
    return contract.load_material(ROOT)


def test_compact_roundtrip_all_packets_within_package_bound(material):
    _, _, doc = material
    assert len(doc["packets"]) == 59 and doc["counts"] == {
        "families": 6, "parts": 6, "reach": 53, "packets": 59, "bank_worlds": 64, "worlds_per_packet": 65}
    compact = development.compact_development(doc)
    assert len(source.canonical(compact).encode()) < 4 * 1024 ** 2
    assert source.canonical(development.expand_development(compact)) == source.canonical(doc)
    assert doc["max_token_count"] == 28281
    assert all(len(p["source"]["worlds"]) == 65 and p["record"]["supports"] == [] for p in doc["packets"])


@pytest.mark.parametrize("change", ["record", "world", "duplicate", "digest"])
def test_compact_tamper_even_with_outer_digest_resealed(material, change):
    compact = json.loads((ROOT / contract.DEVELOPMENT_PATH).read_bytes())
    if change == "record": compact["records"][0]["record"]["instruction"] += " altered"
    if change == "world": compact["worlds"][0]["nodes"][0]["label"] += " altered"
    if change == "duplicate": compact["records"][1] = deepcopy(compact["records"][0])
    if change == "digest": compact["document_metadata"]["development_digest"] = "0" * 64
    compact["compact_digest"] = source.digest({k: v for k, v in compact.items() if k != "compact_digest"})
    with pytest.raises(ValueError): development.expand_development(compact)


def test_every_development_query_is_selected_without_answer_class_filter(material):
    doc = material[2]
    packets = contract.development_packets(doc)
    for family in doc["families"]:
        selected = [packets[key] for key in family["record_ids"]]
        focus = next(w for w in selected[0]["source"]["worlds"] if w["world_id"] == family["world_id"])
        expected = {node["ref"] for node in focus["nodes"]} - {family["root_ref"]}
        queries = [p["record"]["query"] for p in selected]
        assert sum(q["kind"] == "parts" for q in queries) == 1
        assert {q["arguments"]["part"] for q in queries if q["kind"] == "reach"} == expected


def test_main_contrast_preserves_all_information_and_depths(material):
    frozen = material[0]
    alt, sa = contract.schedule(frozen, contract.CONDITIONS[0])
    mixed, sm = contract.schedule(frozen, contract.CONDITIONS[1])
    assert len(alt) == len(mixed) == 160 and alt != mixed
    assert sa["packet_depth_multiset_digest"] == sm["packet_depth_multiset_digest"]
    assert sa["presentation_slots"] == sm["presentation_slots"] == 4613
    assert sa["planned_slot_core_passes"] == sm["planned_slot_core_passes"] == 17178
    assert sum(len(a["record_ids"]) for a, b in zip(alt, mixed) if a == b) == 896
    for cursor in (40, 80, 120, 160):
        assert Counter(k for b in alt[:cursor] for k in b["record_ids"]) == Counter(k for b in mixed[:cursor] for k in b["record_ids"])


def test_altered_frozen_course_cannot_enter_schedule(material):
    frozen = deepcopy(material[0]); frozen["batches"][0]["depth"] = 8
    with pytest.raises(ValueError, match="COURSE_BYTES"): contract.schedule(frozen, contract.CONDITIONS[0])


def test_retention_and_interference_do_not_rehearse_probe_answers(material):
    frozen = material[0]
    probes = dict(contract.retention_packets(frozen))
    assert len(probes) == 96
    assert all(p["record"]["supports"] == [] and p["record"]["query"]["kind"] in ("parts", "reach") for p in probes.values())
    registry = {r["record_id"]: r for r in frozen["registry"]}
    batches = contract.interference_batches(frozen)
    assert len(batches) == 16 and [b["cursor"] for b in batches] == list(range(160, 176))
    ids = [key for b in batches for key in b["record_ids"]]
    assert len(ids) == 128 and not set(ids).intersection(probes)
    assert all(registry[key]["supports"] == [] and registry[key]["query"]["kind"] in ("definition", "context") for key in ids)
    occurrences = [key for b in batches for key in b["occurrence_ids"]]
    assert len(set(occurrences)) == 128
    assert all(contract.re.fullmatch(r"typed-occurrence-[0-9a-f]{64}", key) for key in occurrences)


@pytest.mark.parametrize("job", [JOB.replace("20260917", "20260920"), JOB.replace("-a-", "-x-"), JOB + "-retry"])
def test_unfrozen_job_parameters_rejected(job):
    with pytest.raises(ValueError): contract.parse_job(job)


def test_artifact_contract_covers_full_course_interference_and_all_checkpoints():
    names = worker.EXPECTED_ARTIFACTS
    assert len(names) == len(set(names)) < 500
    assert all(Path(n).name == n for n in names)
    for cursor in (0, 40, 80, 120, 160):
        assert "development_%03d_predictions.json" % cursor in names
        assert "development_%03d_scoring.json" % cursor in names
    assert {"main_159_update.json", "interference_015_update.json", "retained.pt", "replay_2_update.json"} <= set(names)
    assert launch.evidence_contract()["required_count"] == len(names) + 3


def test_complete_delivery_refuses_missing_evidence(tmp_path):
    artifacts = tmp_path / "artifacts"; artifacts.mkdir()
    with pytest.raises(ValueError, match="REQUIRED_ARTIFACTS"):
        worker.deliver(tmp_path, artifacts, {"job": JOB}, failed=False)
    result = worker.deliver(tmp_path, artifacts, {"job": JOB, "status": "TYPED_MATCHED_FAILED"}, failed=True)
    assert result["status"] == "TYPED_MATCHED_FAILED" and result["summary"]["learning_advantage_established"] is False


def test_worker_refuses_windows_before_any_numerical_import(tmp_path, monkeypatch, material):
    from cas_meta2.teaching_cycle import gpu_adapter
    monkeypatch.setattr(gpu_adapter.platform, "system", lambda: "Windows")
    config = contract.make_config(ROOT, source_sha=SOURCE, job=JOB, bucket=JOB + "-807562639912",
        condition=contract.CONDITIONS[0], model_seed=20260917)
    assert len(config["bucket"]) <= 63 and config["design"]["global_optimizer_updates_max"] == 178
    with pytest.raises(ValueError, match="LINUX_WORKER_REQUIRED"):
        worker.run(config, ROOT, tmp_path, tmp_path / "artifacts")
    assert json.loads((tmp_path / "result.json").read_bytes())["status"] == "TYPED_MATCHED_FAILED"


def test_rendered_worker_compiles_and_keeps_bound_worker_entrypoint():
    text = launch.render_worker()
    ast.parse(text)
    assert "typed_matched_worker.run" in text and "3300" in text
    assert launch.BOUNDS["optimizer_updates_max"] == 178
    assert launch.BOUNDS["jobs"] == 1 and launch.BOUNDS["automatic_retries"] == 0


def test_reservation_description_matches_selected_arm(monkeypatch):
    captured = []
    provider = object.__new__(launch.TypedMatchedProvider)
    provider.bound_config = {"design": {"condition": "MIXED_SAME_ITEMS", "model_seed": 20260918}}
    provider._reserved = False; provider.calls = []
    provider.job = JOB; provider.source_sha = SOURCE; provider.archive_sha256 = "b"*64; provider.ledger_path = Path("UNUSED")
    provider._event = lambda *a, **kw: None
    provider.budget = SimpleNamespace(reserve_budget=lambda *args: captured.append(args) or {"reserved": True})
    provider._record_aws_side_reservation = lambda receipt: {"status": "SYNTHETIC"}
    provider.reserve("7.00")
    assert captured[0][4]["task_scope"] == "cncm_typed_matched_development_001"
    assert captured[0][4]["frozen_budget"] == provider.bound_config["design"]
    with pytest.raises(ValueError): provider.reserve("7.00")


def test_matched_reservation_transition_preserves_shared_physical_limits():
    shared, budget = launch.shared, launch.shared.budget
    provider = object.__new__(launch.TypedMatchedProvider)
    provider.bound_config = {"design": {"condition": "MIXED_SAME_ITEMS", "model_seed": 20260918}}
    plan = provider.reservation_plan()
    budget.validate_plan(plan, "7.00")
    old = shared.reservation_plan()
    assert {k: v for k, v in plan.items() if k not in ("task_scope", "frozen_budget")} == {
        k: v for k, v in old.items() if k not in ("task_scope", "frozen_budget")}
    request = {"job": JOB, "source_sha": SOURCE, "archive_sha256": "b"*64}
    prior = {"revision": 0, "reservations": []}
    current = {"revision": 1, "previous_state_sha256": budget.digest(budget.encoded(prior)),
        "reservations": [{**request, "status": budget.STATUS, "reserved_usd": "7.00", "plan": plan,
            "plan_sha256": budget.digest(budget.encoded(plan))}]}
    before, after = {"ledger": prior}, {"ledger": current, "ledger_sha256": "c"*64}
    receipt = {"ledger_sha256": "c"*64}
    assert shared.validate_reserved_transition(before, after, receipt, request, expected_plan=plan) == receipt
    with pytest.raises(ValueError, match="RESOURCE_PLAN_MISMATCH"):
        shared.validate_reserved_transition(before, after, receipt, request)
