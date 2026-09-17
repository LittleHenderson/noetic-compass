"""Pure slot syntax and public score decoding; no private target or tensor run."""
import builtins
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
import math
from pathlib import Path
import sys

import pytest

from cas_meta2.typed_teaching import answers, course, slots, source

ROOT = Path(__file__).resolve().parents[3]
COURSE_PATH = ROOT / "records/typed_course_001/checks_002/public_course.json"
COURSE_SHA = "cf7a718185172197a7441b4e87c603b1d7c7c2b06c42903ff27d34ce1cae0987"
DENIED = {"torch", "numpy", "tensorflow", "jax", "cas_cjt", "casformer", "boto3", "botocore",
          "requests", "httpx", "openai", "anthropic", "transformers"}


@pytest.fixture(autouse=True)
def no_teacher_or_numerical_execution(monkeypatch):
    original = builtins.__import__
    def guarded(name, *args, **kwargs):
        if name.split(".")[0] in DENIED or name.endswith(".checker") or name.startswith("cas_meta2.graph_teaching"):
            raise AssertionError("PROHIBITED_IMPORT:" + name)
        return original(name, *args, **kwargs)
    def forbidden(*args, **kwargs):
        raise AssertionError("PRIVATE_OR_FULL_COURSE_CONSTRUCTION")
    monkeypatch.setattr(builtins, "__import__", guarded)
    for name in ("compile_course", "prepare_course", "derive_targets_from_seal", "_worked_target"):
        monkeypatch.setattr(course, name, forbidden)
    monkeypatch.setattr(course.focal, "derive_roles", forbidden)
    monkeypatch.setattr(course.focal, "render_excerpt", forbidden)
    yield
    assert not DENIED.intersection(name.split(".")[0] for name in sys.modules)


@pytest.fixture(scope="module")
def public_course():
    raw = COURSE_PATH.read_bytes()
    assert sha256(raw).hexdigest() == COURSE_SHA
    return json.loads(raw)


@pytest.fixture(scope="module")
def prepared(public_course):
    # One compile per registry entry, never one complete course rebuild per test.
    result = {}
    for row in public_course["registry"]:
        packet = course.model_packet(public_course, row["record_id"])
        result[row["record_id"]] = (packet, slots.compile_slots(packet))
    return result


def one(prepared, kind, *, node_count=None):
    for packet, plan in prepared.values():
        focus = next(w for w in packet["source"]["worlds"] if w["world_id"] == packet["record"]["source_world_id"])
        if plan["kind"] == kind and (node_count is None or len(focus["nodes"]) == node_count):
            return packet, plan
    raise AssertionError("MISSING_FIXTURE:" + kind)


def decisions(plan, *, last=False):
    index = -1 if last else 0
    return {"schema": slots.DECISION_SCHEMA, "record_id": plan["record_id"], "query_id": plan["query_id"],
        "plan_digest": plan["plan_digest"],
        "selected": {} if plan["kind"] == "correspondence" else {s["slot_id"]: s["symbols"][index] for s in plan["slots"]},
        "correspondence_candidate_id": plan["correspondence_candidates"][index]["candidate_id"] if plan["kind"] == "correspondence" else None}


def zero_scores(plan):
    return {row["slot_id"]: {symbol: 0.0 for symbol in row["symbols"]} for row in plan["slots"]}


def test_full_retained_course_slot_coverage_and_measured_pure_counts(public_course, prepared):
    assert len(prepared) == 564
    assert {p[1]["kind"] for p in prepared.values()} == set(answers.RULES)
    assert len(public_course["presentations"]) == 1152 and len(public_course["batches"]) == 160
    assert sum(len(p[1]["slots"]) for p in prepared.values()) == 2598
    assert sum(len(prepared[p["record_id"]][1]["slots"]) for p in public_course["presentations"]) == 4613
    assert sum(b["depth"] * sum(len(prepared[key][1]["slots"]) for key in b["record_ids"])
               for b in public_course["batches"]) == 17178
    assert max(len(p[1]["slots"]) for p in prepared.values()) == 16
    for packet, plan in prepared.values():
        assert len(plan["aliases"]["worlds"]) == 64
        assert plan["profile"]["status"] == "PURE_SLOT_CONTRACT_NO_NUMERIC_OR_LEARNING_ACCEPTANCE"
        assert plan["decision_contract"]["semantic_repair"] is False


@pytest.mark.parametrize("kind", tuple(answers.RULES))
def test_first_and_last_syntactic_decisions_assemble_for_every_kind(prepared, kind):
    packet, plan = one(prepared, kind)
    for last in (False, True):
        answer = slots.assemble_answer(packet, decisions(plan, last=last))
        assert answers.validate_answer(packet["source"], packet["record"]["query"], answer) == answer


def test_all_slots_and_aliases_are_public_and_fully_scoped(prepared):
    tables = [plan["aliases"] for _, plan in prepared.values()]
    assert all(table == tables[0] for table in tables)
    worlds = tables[0]["worlds"]
    assert [w["world_id"] for w in worlds] == sorted(w["world_id"] for w in worlds)
    assert [w["alias"] for w in worlds] == ["W%d" % i for i in range(64)]
    for w in worlds:
        assert [n["ref"] for n in w["nodes"]] == sorted(n["ref"] for n in w["nodes"])
        assert [n["alias"] for n in w["nodes"]] == ["N%d" % i for i in range(len(w["nodes"]))]
    for _, plan in prepared.values():
        by_id = {w["world_id"]: w["alias"] for w in worlds}
        for slot in plan["slots"]:
            assert by_id[slot["scope_world_id"]] == slot["scope_alias"]
            assert set(slot["symbols"]) <= set(slots.SYMBOLS)


def test_full_world_definition_context_and_analogy_choices_are_not_target_filtered(prepared):
    for kind, fields in (("definition", {"kind_ref", "function_ref"}), ("context", {"setting_ref"}), ("analogy", {"world_id"})):
        packet, plan = one(prepared, kind)
        expected = [w["alias"] for w in plan["aliases"]["worlds"]]
        for slot in plan["slots"]:
            if slot["field"] in fields:
                assert slot["symbols"] == (["NO_MATCH"] + expected if kind == "analogy" else expected)
        answer = slots.assemble_answer(packet, decisions(plan, last=True))
        assert answer["kind"] == kind


def test_role_set_multilabel_is_one_exact_set_and_status_is_derived(prepared):
    packet, plan = one(prepared, "role_set")
    row = decisions(plan)
    for slot in plan["slots"]:
        row["selected"][slot["slot_id"]] = "PRESENT" if slot["coordinates"][0] in (5, 6) else "ABSENT"
    assert slots.assemble_answer(packet, row)["value"] == {"roles": [5, 6], "status": "AMBIGUOUS"}
    assert slots.assemble_answer(packet, decisions(plan))["value"] == {"roles": [], "status": "INSUFFICIENT"}


def test_edge_universe_includes_every_pair_even_wrong_self_edges(prepared):
    packet, plan = one(prepared, "edge_account", node_count=4)
    assert len(plan["slots"]) == 16
    assert sum(s["coordinates"][0] == s["coordinates"][1] for s in plan["slots"]) == 4
    answer = slots.assemble_answer(packet, decisions(plan, last=True))
    assert len(answer["value"]["edges"]) == 16


@pytest.mark.parametrize("count,expected", [(3, 7), (4, 25)])
def test_all_correspondence_bijections_and_null_remain_available(prepared, count, expected):
    packet, plan = one(prepared, "correspondence", node_count=count)
    assert len(plan["correspondence_candidates"]) == expected
    assert plan["correspondence_candidates"][0]["value"] == {"status": "NO_MATCH", "pairs": []}
    assert [r["value"] for r in plan["correspondence_candidates"]] == answers.correspondence_candidates(packet["source"], packet["record"]["query"])
    for candidate in plan["correspondence_candidates"]:
        selection = decisions(plan); selection["correspondence_candidate_id"] = candidate["candidate_id"]
        assert slots.assemble_answer(packet, selection)["value"] == candidate["value"]


def test_scalar_ties_and_public_candidate_probability_normalization(prepared):
    packet, plan = one(prepared, "correspondence", node_count=4)
    scores = zero_scores(plan)
    rows = slots.candidate_scores(packet, scores)
    assert math.isclose(sum(math.exp(row["log_probability"]) for row in rows), 1.0, abs_tol=1e-12)
    assert math.isclose(math.exp(rows[0]["log_probability"]), 0.5, abs_tol=1e-12)
    assert all(math.isclose(math.exp(row["log_probability"]), 0.5 / 24, abs_tol=1e-12) for row in rows[1:])
    assert slots.score_decisions(packet, scores)["correspondence_candidate_id"] == rows[0]["candidate_id"]
    scores[plan["slots"][0]["slot_id"]]["MAPPING"] = 100.0
    assert slots.score_decisions(packet, scores)["correspondence_candidate_id"] == rows[1]["candidate_id"]


def test_correspondence_row_constant_shift_cannot_bias_null_or_other_mappings(prepared):
    packet, plan = one(prepared, "correspondence", node_count=4)
    scores = zero_scores(plan)
    for i, slot in enumerate(plan["slots"]):
        scores[slot["slot_id"]] = {symbol: (i * 3 + j) / 7 for j, symbol in enumerate(slot["symbols"])}
    changed = deepcopy(scores)
    for i, slot in enumerate(plan["slots"]):
        changed[slot["slot_id"]] = {symbol: value + 30 * (i + 1) for symbol, value in changed[slot["slot_id"]].items()}
    before, after = slots.candidate_scores(packet, scores), slots.candidate_scores(packet, changed)
    assert [r["candidate_id"] for r in before] == [r["candidate_id"] for r in after]
    assert all(math.isclose(a["log_probability"], b["log_probability"], abs_tol=1e-11) for a, b in zip(before, after))
    assert slots.score_decisions(packet, scores) == slots.score_decisions(packet, changed)


def test_joint_mapping_selection_respects_bijection_without_graph_check(prepared):
    packet, plan = one(prepared, "correspondence", node_count=4)
    selected = plan["correspondence_candidates"][-1]
    scores = zero_scores(plan)
    scores[plan["slots"][0]["slot_id"]]["MAPPING"] = 100
    node_alias = {n["ref"]: n["alias"] for w in plan["aliases"]["worlds"] for n in w["nodes"]}
    by_source = {s["coordinates"][0]: s for s in plan["slots"][1:]}
    for pair in selected["value"]["pairs"]:
        scores[by_source[pair["source"]]["slot_id"]][node_alias[pair["target"]]] = 20
    decision = slots.score_decisions(packet, scores)
    assert decision["correspondence_candidate_id"] == selected["candidate_id"]
    assert slots.assemble_answer(packet, decision)["value"] == selected["value"]


def test_unequal_public_sizes_have_one_reported_forced_candidate(prepared):
    packet, _ = one(prepared, "correspondence", node_count=3)
    packet = deepcopy(packet)
    target = next(w["world_id"] for w in packet["source"]["worlds"] if len(w["nodes"]) == 4)
    packet["record"]["query"] = answers.compile_query(packet["source"], kind="correspondence", arguments={"target_world_id": target})
    packet["record"]["record_id"] = "typed-input-" + source.digest({k: v for k, v in packet["record"].items() if k != "record_id"})
    plan = slots.compile_slots(packet)
    assert plan["forced_candidate_count"] == 1
    scores = zero_scores(plan)
    assert slots.candidate_scores(packet, scores) == [{"candidate_id": plan["correspondence_candidates"][0]["candidate_id"], "log_probability": 0.0}]
    assert slots.assemble_answer(packet, slots.score_decisions(packet, scores))["value"] == {"status": "NO_MATCH", "pairs": []}


@pytest.mark.parametrize("kind", ["role_set", "definition", "context", "analogy", "parts", "edge_account", "reach"])
def test_independent_scalar_ties_use_declared_order(prepared, kind):
    packet, plan = one(prepared, kind)
    assert slots.score_decisions(packet, zero_scores(plan)) == decisions(plan)


@pytest.mark.parametrize("bad", [True, False, float("nan"), float("inf"), -float("inf"), 1000001, 10 ** 1000, "0", None])
def test_score_scalar_type_finiteness_and_bounds(prepared, bad):
    packet, plan = one(prepared, "correspondence")
    scores = zero_scores(plan)
    scores[plan["slots"][0]["slot_id"]]["NO_MATCH"] = bad
    with pytest.raises(ValueError, match="SCORE_SCALAR"): slots.score_decisions(packet, scores)


def test_extreme_bounded_scores_produce_finite_normalized_results(prepared):
    packet, plan = one(prepared, "correspondence", node_count=4)
    scores = zero_scores(plan)
    for s in plan["slots"]:
        scores[s["slot_id"]] = {v: (slots.MAX_ABS_SCORE if i % 2 else -slots.MAX_ABS_SCORE) for i, v in enumerate(s["symbols"])}
    rows = slots.candidate_scores(packet, scores)
    assert all(math.isfinite(row["log_probability"]) for row in rows)
    assert math.isclose(sum(math.exp(row["log_probability"]) for row in rows), 1.0, abs_tol=1e-9)


@pytest.mark.parametrize("mutation", ["missing_slot", "extra_slot", "missing_symbol", "extra_symbol"])
def test_score_shape_is_closed(prepared, mutation):
    packet, plan = one(prepared, "parts")
    scores = zero_scores(plan); first = plan["slots"][0]["slot_id"]
    if mutation == "missing_slot": del scores[first]
    elif mutation == "extra_slot": scores["teacher_answer"] = {}
    elif mutation == "missing_symbol": del scores[first]["ABSENT"]
    else: scores[first]["TEACHER"] = 1
    with pytest.raises(ValueError): slots.score_decisions(packet, scores)


@pytest.mark.parametrize("mutation", ["extra", "slot", "alias", "profile", "kind", "float", "missing"])
def test_resealed_plan_tampering_fails_reconstruction(prepared, mutation):
    packet, original = one(prepared, "parts")
    plan = deepcopy(original)
    if mutation == "extra": plan["correct"] = 1
    elif mutation == "slot": plan["slots"][0]["symbols"].reverse()
    elif mutation == "alias": plan["aliases"]["worlds"].reverse()
    elif mutation == "profile": plan["profile"]["readout_width_proposed"] = 32
    elif mutation == "kind": plan["kind"] = "reach"
    elif mutation == "float": plan["forced_candidate_count"] = 0.0
    else: plan["slots"].pop()
    plan["plan_digest"] = source.digest({k: v for k, v in plan.items() if k != "plan_digest"})
    with pytest.raises(ValueError): slots.validate_plan(packet, plan)


@pytest.mark.parametrize("mutation", ["extra", "wrong_id", "wrong_query", "wrong_plan", "missing", "symbol", "candidate"])
def test_decision_identity_and_closed_coverage(prepared, mutation):
    packet, plan = one(prepared, "parts"); row = decisions(plan)
    if mutation == "extra": row["correct"] = 1
    elif mutation == "wrong_id": row["record_id"] += "x"
    elif mutation == "wrong_query": row["query_id"] += "x"
    elif mutation == "wrong_plan": row["plan_digest"] = "0" * 64
    elif mutation == "missing": row["selected"].pop(next(iter(row["selected"])))
    elif mutation == "symbol": row["selected"][next(iter(row["selected"]))] = True
    else: row["correspondence_candidate_id"] = "not-null"
    with pytest.raises(ValueError): slots.assemble_answer(packet, row)


def test_old_decisions_cannot_bind_changed_instructional_public_input(prepared):
    packet, plan = next((p, s) for p, s in prepared.values() if p["record"]["cue"] is not None)
    changed = deepcopy(packet); changed["record"]["cue"] = None
    changed["record"]["record_id"] = "typed-input-" + source.digest({k: v for k, v in changed["record"].items() if k != "record_id"})
    other = slots.compile_slots(changed)
    assert other["packet_digest"] != plan["packet_digest"]
    assert other["plan_digest"] != plan["plan_digest"]
    with pytest.raises(ValueError, match="DECISION_BINDING"): slots.assemble_answer(changed, decisions(plan))


def test_public_extras_cannot_smuggle_teacher_or_private_lineage(prepared):
    packet, _ = one(prepared, "parts")
    for field in ("teacher_target", "expected_answer", "source_event", "plan"):
        changed = deepcopy(packet); changed["record"][field] = {}
        with pytest.raises(ValueError): slots.compile_slots(changed)


def test_unknown_mapping_candidate_and_independent_mapping_picks_are_refused(prepared):
    packet, plan = one(prepared, "correspondence")
    row = decisions(plan); row["correspondence_candidate_id"] = "invented"
    with pytest.raises(ValueError): slots.assemble_answer(packet, row)
    row = decisions(plan); row["selected"][plan["slots"][0]["slot_id"]] = "MAPPING"
    with pytest.raises(ValueError): slots.assemble_answer(packet, row)


def test_profile_symbols_dependency_pins_and_copy_isolation(prepared):
    profile = slots.profile()
    assert len(profile["symbols"]) == len(set(profile["symbols"])) == 90
    assert profile["symbols"] == list(slots.SYMBOLS)
    assert profile["course_profile"] == course.profile()
    packet, plan = one(prepared, "parts")
    rebuilt = slots.validate_plan(packet, plan)
    rebuilt["aliases"]["worlds"].clear()
    assert len(plan["aliases"]["worlds"]) == 64


def test_cyclic_plan_refused_before_canonicalization(prepared):
    packet, _ = one(prepared, "parts")
    cyclic = {}; cyclic["cycle"] = cyclic
    with pytest.raises(ValueError, match="CYCLE"): slots.validate_plan(packet, cyclic)
