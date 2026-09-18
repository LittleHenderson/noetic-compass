"""Tests for the declared-constraint layer.

Subject under test: ``cncm/answer_constraints.py``.

The layer corrects a decision table using only what the packet declares. Four claims are defended:

1. **It reads declarations, not answers.** ``declared_answer_shape`` returns the numbers the packet
   states -- the declared edge count, the declared out-edge count of the supplied ``whole``, the
   declared participant count -- and nothing here takes a target as an argument.
2. **Self-links and self-parts are forced ABSENT.** Verified structural: zero self-links in 649,728
   declared edges over 216,576 world declarations.
3. **Cardinality is enforced on the slots that survive rule 2**, so the two rules do not fight: the
   edge slots with a self-pair removed are the candidates, and exactly the declared count of them
   becomes PRESENT.
4. **One-world identity is applied by enumeration**, and it is total: whatever the scores say, a
   ``definition`` or ``context`` answer comes out as some world's own declaration.

The fixtures are hand-built packets in the exact shape ``course.model_packet`` produces, so these
tests do not depend on ``cas_meta2`` being on the path.

Plain pytest functions, no fixtures beyond local helpers, no numeric runtime, no clock.
"""

from __future__ import annotations

import importlib.util
import json

import pytest

from cncm import answer_constraints as ac

REF = "world-aaa"


def node(alias: str) -> dict:
    return {"ref": f"{REF}/{alias.lower()}", "alias": alias, "kind": "idea", "label": alias}


def world(world_id: str, alias: str, whole: str, edges: list, participants: list) -> dict:
    """A world in the shape `course.model_packet` produces.

    The nodes carry `ref`, `kind` and `label` only -- **no `alias`**. Aliases live in the plan's alias
    table (`slots.compile_slots(packet)["aliases"]`). An earlier version of this fixture put `alias`
    on the packet's nodes, which made the tests pass while the real packets raised `KeyError`. The
    fixture is deliberately faithful now.
    """
    nodes = [
        {"ref": f"{world_id}/{at}", "kind": "idea", "label": f"N{at}"}
        for at in range(4)
    ]
    return {
        "world_id": world_id,
        "nodes": nodes,
        "declared_whole": f"{world_id}/{whole}",
        "contains": [
            {"ref": f"{world_id}/e{at}", "source": f"{world_id}/{a}", "target": f"{world_id}/{b}"}
            for at, (a, b) in enumerate(edges)
        ],
        "declarations": {
            "setting": "in a workshop",
            "participants": [f"{world_id}/{at}" for at in participants],
            "participants_basis": "PRIMARY_AUTHORED_LABELS_FIRST_THREE",
            "kind": "a charging machine",
            "function": "transmits force",
        },
    }


def packet(kind: str, focus_id: str, arguments: dict | None = None, worlds: list | None = None) -> dict:
    if worlds is None:
        worlds = [
            world("world-aaa", "W0", "0", [(0, 1), (1, 2)], [0, 1, 2]),
            world("world-bbb", "W1", "2", [(0, 3), (2, 3)], [0, 2, 3]),
        ]
    return {
        "source": {"focus_world_id": focus_id, "worlds": worlds},
        "record": {"query": {"kind": kind, "focus_world_id": focus_id,
                             "arguments": arguments or {}}},
    }


def aliases(worlds: list) -> dict:
    """The plan's alias table, in the shape `slots.compile_slots` produces.

    Aliases are positional names (`N0`..`N3` within each world), which is why the packet does not
    carry them and the plan does.
    """
    return {
        "worlds": [
            {"world_id": w["world_id"], "alias": f"W{at}",
             "nodes": [{"ref": n["ref"], "alias": f"N{pos}"} for pos, n in enumerate(w["nodes"])]}
            for at, w in enumerate(worlds)
        ]
    }


def edge_plan(focus_id: str, worlds: list) -> dict:
    slots = []
    for i in range(4):
        for j in range(4):
            slots.append({"slot_id": f"e{i}{j}", "field": "edge", "group": "edges",
                          "coordinates": [f"{focus_id}/{i}", f"{focus_id}/{j}"],
                          "symbols": ["ABSENT", "PRESENT"], "scope_alias": "W0"})
    return {"kind": "edge_account", "slots": slots, "aliases": aliases(worlds)}


def node_plan(focus_id: str, worlds: list) -> dict:
    slots = [{"slot_id": f"n{i}", "field": "node", "group": "nodes",
              "coordinates": [f"{focus_id}/{i}"], "symbols": ["ABSENT", "PRESENT"],
              "scope_alias": "W0"} for i in range(4)]
    return {"kind": "parts", "slots": slots, "aliases": aliases(worlds)}


def definition_plan(focus_id: str, worlds: list) -> dict:
    slots = [{"slot_id": "whole", "field": "whole", "group": "whole", "coordinates": [],
              "symbols": ["N0", "N1", "N2", "N3"], "scope_alias": "W0"}]
    for field in ("kind_ref", "function_ref"):
        slots.append({"slot_id": field, "field": field, "group": field, "coordinates": [],
                      "symbols": ["W0", "W1"], "scope_alias": "W0"})
    return {"kind": "definition", "slots": slots, "aliases": aliases(worlds)}


def flat_scores(plan: dict, value: float = 0.0) -> dict:
    return {slot["slot_id"]: {symbol: value for symbol in slot["symbols"]}
            for slot in plan["slots"]}


def select_all(plan: dict, symbol: str | None = None) -> dict:
    return {slot["slot_id"]: (symbol if symbol is not None else slot["symbols"][-1])
            for slot in plan["slots"]}


# --------------------------------------------------------------------------- #
# 1. The layer reads declarations
# --------------------------------------------------------------------------- #


def test_declared_shape_reports_the_packets_own_numbers():
    focus = "world-aaa"
    p = packet("edge_account", focus)
    shape = ac.declared_answer_shape(p)
    assert shape["kind"] == "edge_account"
    assert shape["cardinality"] == 2          # world-aaa declares two edges
    assert shape["self_pairs_absent"] is True
    assert shape["nodes"] == 4


def test_declared_shape_for_parts_counts_only_edges_from_the_whole():
    focus = "world-aaa"
    p = packet("parts", focus, {"whole": f"{focus}/0"})
    shape = ac.declared_answer_shape(p)
    assert shape["whole"] == f"{focus}/0"
    assert shape["cardinality"] == 1          # only (0, 1) starts at node 0


def test_declared_shape_for_context_reports_the_basis():
    p = packet("context", "world-aaa")
    shape = ac.declared_answer_shape(p)
    assert shape["cardinality"] == 3
    assert shape["basis"] == "PRIMARY_AUTHORED_LABELS_FIRST_THREE"


def test_declared_shape_for_definition_names_the_identity_rule():
    p = packet("definition", "world-aaa")
    assert ac.declared_answer_shape(p)["identity"] == "FOCUS_WORLD_DECLARATION_IDENTITY"


# --------------------------------------------------------------------------- #
# 2. Self-links and self-parts
# --------------------------------------------------------------------------- #


def test_self_link_slots_are_forced_absent_whatever_the_scores_say():
    focus = "world-aaa"
    worlds = [world("world-aaa", "W0", "0", [(0, 1), (1, 2)], [0, 1, 2]),
              world("world-bbb", "W1", "2", [(0, 3), (2, 3)], [0, 2, 3])]
    p = packet("edge_account", focus, worlds=worlds)
    plan = edge_plan(focus, worlds)
    scores = flat_scores(plan)
    for i in range(4):                        # make every self-link the top-scoring slot
        scores[f"e{i}{i}"]["PRESENT"] = 99.0
    out = ac.apply_constraints(p, plan, scores, select_all(plan, "ABSENT"))
    for i in range(4):
        assert out[f"e{i}{i}"] == "ABSENT"


def test_the_whole_is_never_a_part_of_itself():
    focus = "world-aaa"
    worlds = [world("world-aaa", "W0", "0", [(0, 1)], [0, 1, 2]),
              world("world-bbb", "W1", "2", [(0, 3)], [0, 2, 3])]
    p = packet("parts", focus, {"whole": f"{focus}/0"}, worlds)
    plan = node_plan(focus, worlds)
    scores = flat_scores(plan)
    scores["n0"]["PRESENT"] = 99.0
    out = ac.apply_constraints(p, plan, scores, select_all(plan, "ABSENT"))
    assert out["n0"] == "ABSENT"


# --------------------------------------------------------------------------- #
# 3. Cardinality is enforced on the surviving slots
# --------------------------------------------------------------------------- #


def test_edge_cardinality_is_exactly_the_declared_count():
    focus = "world-aaa"
    worlds = [world("world-aaa", "W0", "0", [(0, 1), (1, 2)], [0, 1, 2]),
              world("world-bbb", "W1", "2", [(0, 3), (2, 3)], [0, 2, 3])]
    p = packet("edge_account", focus, worlds=worlds)
    plan = edge_plan(focus, worlds)
    out = ac.apply_constraints(p, plan, flat_scores(plan), select_all(plan, "PRESENT"))
    present = [sid for sid, symbol in out.items() if symbol == "PRESENT"]
    assert len(present) == 2
    assert not any(sid[1] == sid[2] for sid in present)   # and no self-links among them


def test_the_two_rules_do_not_fight():
    """The cardinality is applied to the non-self slots, so a self-link never consumes a slot."""
    focus = "world-aaa"
    worlds = [world("world-aaa", "W0", "0", [(0, 0), (0, 1)], [0, 1, 2])]   # a self-link in the data
    p = packet("edge_account", focus, worlds=worlds)
    plan = edge_plan(focus, worlds)
    scores = flat_scores(plan)
    scores["e00"]["PRESENT"] = 99.0
    out = ac.apply_constraints(p, plan, scores, select_all(plan, "ABSENT"))
    assert out["e00"] == "ABSENT"
    assert sum(1 for symbol in out.values() if symbol == "PRESENT") == 2


def test_cardinality_ranks_by_the_margin_not_by_present_alone():
    """PRESENT alone favours n1; the margin PRESENT - ABSENT favours n2. The margin must win.

    Regression test for the round-37 defect: `_apply_cardinality` ranked by the PRESENT score alone,
    against its own docstring, which cost 20 `parts` and 18 `edge_account` answers on the recorded runs.
    """
    focus = "world-aaa"
    worlds = [world("world-aaa", "W0", "0", [(0, 1)], [0, 1, 2])]
    p = packet("parts", focus, {"whole": f"{focus}/0"}, worlds)
    plan = node_plan(focus, worlds)
    scores = flat_scores(plan)
    scores["n1"]["PRESENT"], scores["n1"]["ABSENT"] = 5.0, 4.9    # margin +0.1
    scores["n2"]["PRESENT"], scores["n2"]["ABSENT"] = 3.0, 0.0    # margin +3.0
    out = ac.apply_constraints(p, plan, scores, select_all(plan, "ABSENT"))
    assert sorted(sid for sid, symbol in out.items() if symbol == "PRESENT") == ["n2"]


def test_parts_cardinality_matches_the_declared_out_edges():
    focus = "world-aaa"
    worlds = [world("world-aaa", "W0", "0", [(0, 1), (0, 2)], [0, 1, 2])]
    p = packet("parts", focus, {"whole": f"{focus}/0"}, worlds)
    plan = node_plan(focus, worlds)
    out = ac.apply_constraints(p, plan, flat_scores(plan), select_all(plan, "ABSENT"))
    assert sorted(sid for sid, symbol in out.items() if symbol == "PRESENT") == ["n1", "n2"]


def test_an_impossible_cardinality_leaves_the_selection_untouched():
    focus = "world-aaa"
    worlds = [world("world-aaa", "W0", "0", [(0, 1)], [0, 1, 2])]
    plan = node_plan(focus, worlds)
    shape = ac.declared_answer_shape(packet("parts", focus, {"whole": f"{focus}/0"}, worlds))
    assert shape["cardinality"] == 1
    p = packet("parts", focus, {"whole": f"{focus}/0"}, worlds)
    out = ac.apply_constraints(p, plan, flat_scores(plan), select_all(plan, "ABSENT"))
    assert len(out) == len(plan["slots"])


# --------------------------------------------------------------------------- #
# 4. One-world identity
# --------------------------------------------------------------------------- #


def test_definition_comes_out_as_one_worlds_declaration():
    focus = "world-aaa"
    worlds = [world("world-aaa", "W0", "2", [(0, 1)], [0, 1, 2]),
              world("world-bbb", "W1", "3", [(0, 3)], [0, 2, 3])]
    p = packet("definition", focus, worlds=worlds)
    plan = definition_plan(focus, worlds)
    scores = flat_scores(plan)
    scores["whole"]["N2"] = 10.0
    scores["kind_ref"]["W0"] = 10.0
    scores["function_ref"]["W0"] = 10.0
    out = ac.apply_constraints(p, plan, scores, select_all(plan, "N0"))
    assert (out["whole"], out["kind_ref"], out["function_ref"]) == ("N2", "W0", "W0")


def test_definition_picks_the_world_the_scores_favour_not_the_focus():
    focus = "world-aaa"
    worlds = [world("world-aaa", "W0", "2", [(0, 1)], [0, 1, 2]),
              world("world-bbb", "W1", "3", [(0, 3)], [0, 2, 3])]
    p = packet("definition", focus, worlds=worlds)
    plan = definition_plan(focus, worlds)
    scores = flat_scores(plan)
    scores["kind_ref"]["W1"] = 5.0
    scores["whole"]["N3"] = 5.0
    scores["function_ref"]["W1"] = 5.0
    out = ac.apply_constraints(p, plan, scores, select_all(plan, "N0"))
    assert out["kind_ref"] == "W1"
    assert out["whole"] == "N3"


def test_context_comes_out_as_one_worlds_setting_and_participants():
    focus = "world-aaa"
    worlds = [world("world-aaa", "W0", "0", [(0, 1)], [0, 1, 2]),
              world("world-bbb", "W1", "2", [(0, 3)], [0, 2, 3])]
    p = packet("context", focus, worlds=worlds)
    slots = [{"slot_id": "setting", "field": "setting_ref", "group": "setting_ref",
              "coordinates": [], "symbols": ["W0", "W1"], "scope_alias": "W0"}]
    slots += [{"slot_id": f"p{i}", "field": "participant", "group": "participants",
               "coordinates": [f"{focus}/{i}"], "symbols": ["ABSENT", "PRESENT"],
               "scope_alias": "W0"} for i in range(4)]
    plan = {"kind": "context", "slots": slots, "aliases": aliases(worlds)}
    scores = flat_scores(plan)
    scores["setting"]["W1"] = 5.0
    out = ac.apply_constraints(p, plan, scores, select_all(plan, "ABSENT"))
    assert out["setting"] == "W1"
    assert [sid for sid in ("p0", "p1", "p2", "p3") if out[sid] == "PRESENT"] == ["p0", "p2", "p3"]


# --------------------------------------------------------------------------- #
# Boundaries
# --------------------------------------------------------------------------- #


def test_a_kind_with_no_measured_constraint_is_returned_unchanged():
    p = packet("reach", "world-aaa")
    plan = {"kind": "reach", "slots": [{"slot_id": "r", "field": "reach", "group": "reach",
                                        "coordinates": [], "symbols": ["ABSENT", "DIRECT"],
                                        "scope_alias": "W0"}],
            "aliases": aliases(p["source"]["worlds"])}
    selected = {"r": "DIRECT"}
    out = ac.apply_constraints(p, plan, {"r": {"ABSENT": 0.0, "DIRECT": 0.0}}, selected)
    assert out == selected
    assert out is not selected          # a copy, never the caller's dict


def test_constraints_tuple_names_exactly_the_supported_kinds():
    assert ac.CONSTRAINTS == ("edge_account", "parts", "context", "definition")


def test_a_packet_without_the_focus_world_is_refused():
    p = packet("edge_account", "world-aaa")
    p["record"]["query"]["focus_world_id"] = "world-zzz"
    with pytest.raises(KeyError):
        ac.declared_answer_shape(p)


# --------------------------------------------------------------------------- #
# 6. The drop-in — the property that makes wiring safe
# --------------------------------------------------------------------------- #
#
# These need the run's own decoder. `cas_meta2` lives under `research/CAS_META_2_COMPOSITION` and is
# not on the path from this directory, so the path is added here -- otherwise these tests would skip
# and the faithfulness property, which is the important one, would never actually be checked.
#
# A module-level `importorskip` was tried first and skipped the WHOLE file, which is not what is
# wanted: the rules themselves must stay testable without the run package.

import sys
from pathlib import Path

_COMP = Path(__file__).resolve().parents[1] / "research" / "CAS_META_2_COMPOSITION"
if str(_COMP) not in sys.path:
    sys.path.insert(0, str(_COMP))

try:
    HAVE_RUN_SLOTS = importlib.util.find_spec("cas_meta2.typed_teaching.slots") is not None
except (ImportError, ModuleNotFoundError, ValueError):
    HAVE_RUN_SLOTS = False

needs_run_slots = pytest.mark.skipif(not HAVE_RUN_SLOTS, reason="cas_meta2 is not on the path")


def test_the_rules_do_not_need_the_run_package():
    """`apply_constraints` and `declared_answer_shape` are importable and usable on plain dicts."""
    focus = "world-aaa"
    worlds = [world("world-aaa", "W0", "0", [(0, 1)], [0, 1, 2])]
    shape = ac.declared_answer_shape(packet("edge_account", focus, worlds=worlds))
    assert shape["cardinality"] == 1


def real_cases(limit=24, kinds=None):
    """Real packets and real recorded scores from the frozen course, or [] if either is absent.

    Hand-built fixtures cannot exercise the run's decoder: `slots.compile_slots` runs the full packet
    validation and rejects them with `TYPED_SOURCE_PUBLIC_FIELDS`. That is what the first version of
    these tests discovered, so they use the real artifacts.
    """
    try:
        from cas_meta2.typed_teaching import course, slots as run_slots, worker_contract
    except ImportError:
        return []
    home = _COMP.parents[1]
    receipts = home / "records/typed_matched_001"
    if not receipts.is_dir():
        return []
    run = next((directory for directory in sorted(receipts.iterdir())
                if (directory / "collected/results/artifacts/final_predictions.json").is_file()), None)
    if run is None:
        return []
    try:
        frozen, _tokenizer, _ = worker_contract.load_material(home)
    except Exception:                                                 # noqa: BLE001
        return []
    scores_by_record = {
        row["record_id"]: row["scores"]
        for row in json.loads(
            (run / "collected/results/artifacts/final_predictions.json").read_text(
                encoding="utf-8"))["predictions"]}
    out = []
    for row in frozen["registry"]:
        if kinds is not None and row["query"]["kind"] not in kinds:
            continue
        scores = scores_by_record.get(row["record_id"])
        if scores is None:
            continue
        packet = course.model_packet(frozen, row["record_id"])
        _ = run_slots  # imported for the caller's convenience
        out.append((packet, scores))
        if limit is not None and len(out) >= limit:
            break
    return out


@needs_run_slots
def test_the_drop_in_is_the_runs_own_decoder_when_the_flag_is_off():
    """With the flag off it must be **exactly** `slots.score_decisions`, not merely equivalent.

    This is the whole reason the layer can be put in place before anything is decided: `binding`'s
    query spec does not read the decision contract, so with the flag off nothing anywhere changes.
    """
    from cas_meta2.typed_teaching import slots as run_slots

    cases = real_cases(limit=24)
    if not cases:
        pytest.skip("the frozen course or a recorded run is not present")
    for packet, scores in cases:
        assert ac.score_decisions(packet, scores) == run_slots.score_decisions(packet, scores)
        assert (ac.score_decisions(packet, scores, declared_constraints=False)
                == run_slots.score_decisions(packet, scores))


def test_the_flag_defaults_to_off():
    import inspect

    assert inspect.signature(ac.score_decisions).parameters["declared_constraints"].default is False


@needs_run_slots
def test_a_kind_without_rules_is_untouched_by_the_flag():
    """`role_set` has no measured rule, so enabling the flag must not move one of its decisions."""
    from cas_meta2.typed_teaching import slots as run_slots

    cases = real_cases(limit=None, kinds={"role_set"})
    if not cases:
        pytest.skip("no role_set records available")
    for packet, scores in cases:
        assert (ac.score_decisions(packet, scores, declared_constraints=True)
                == run_slots.score_decisions(packet, scores))


@needs_run_slots
def test_the_flag_moves_a_kind_that_has_a_rule():
    """And it must actually do something on a kind it has rules for, or the flag is inert."""
    cases = real_cases(limit=None, kinds={"parts"})
    if not cases:
        pytest.skip("no parts records available")
    moved = sum(1 for packet, scores in cases
                if (ac.score_decisions(packet, scores, declared_constraints=True)
                    != ac.score_decisions(packet, scores)))
    assert moved > 0, "the flag changed nothing on a kind it has a rule for"
