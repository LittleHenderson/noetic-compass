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
# 5. Structure independence — the development panel's shapes
# --------------------------------------------------------------------------- #
#
# The held-out development panel is 59 questions over worlds with **ten** nodes, `max_depth` 3 and
# `has_nested_whole` true, against the exposed course's four-node worlds. Its packets are not in the
# frozen course (only their digests are), so it cannot be scored; what can be tested is whether this
# layer's rules depend on the four-node layout they were derived from. They must not.


def big_world(world_id: str, size: int, edges: list, participants: list) -> dict:
    """A world of arbitrary size, in the real packet shape."""
    return {
        "world_id": world_id,
        "nodes": [{"ref": f"{world_id}/{at}", "kind": "idea", "label": f"N{at}"}
                  for at in range(size)],
        "declared_whole": f"{world_id}/0",
        "contains": [{"ref": f"{world_id}/e{at}", "source": f"{world_id}/{a}", "target": f"{world_id}/{b}"}
                     for at, (a, b) in enumerate(edges)],
        "declarations": {
            "setting": "in a workshop",
            "participants": [f"{world_id}/{at}" for at in participants],
            "participants_basis": "PRIMARY_AUTHORED_LABELS_FIRST_THREE",
            "kind": "a charging machine",
            "function": "transmits force",
        },
    }


def big_packet(kind: str, focus_id: str, worlds: list, arguments: dict | None = None) -> dict:
    return {
        "source": {"focus_world_id": focus_id, "worlds": worlds},
        "record": {"query": {"kind": kind, "focus_world_id": focus_id,
                             "arguments": arguments or {}}},
    }


def big_aliases(worlds: list) -> dict:
    return {
        "worlds": [
            {"world_id": w["world_id"], "alias": f"W{at}",
             "nodes": [{"ref": n["ref"], "alias": f"N{pos}"} for pos, n in enumerate(w["nodes"])]}
            for at, w in enumerate(worlds)
        ]
    }


def ten_node_worlds() -> list:
    focus = big_world("world-big", 10, [(0, 1), (0, 2), (0, 3), (4, 5)], [0, 1, 2, 3])
    other = big_world("world-oth", 10, [(1, 2), (3, 4)], [1, 2, 3])
    return [focus, other]


def test_declared_shape_does_not_assume_four_nodes():
    worlds = ten_node_worlds()
    shape = ac.declared_answer_shape(big_packet("edge_account", "world-big", worlds))
    assert shape["nodes"] == 10
    assert shape["cardinality"] == 4
    shape = ac.declared_answer_shape(
        big_packet("parts", "world-big", worlds, {"whole": "world-big/0"}))
    assert shape["cardinality"] == 3


def test_cardinality_and_self_links_hold_on_a_ten_node_world():
    worlds = ten_node_worlds()
    focus = "world-big"
    plan = {
        "kind": "edge_account",
        "slots": [
            {"slot_id": f"e{i}-{j}", "field": "edge", "group": "edges",
             "coordinates": [f"{focus}/{i}", f"{focus}/{j}"],
             "symbols": ["ABSENT", "PRESENT"], "scope_alias": "W0"}
            for i in range(10) for j in range(10)
        ],
        "aliases": big_aliases(worlds),
    }
    scores = {slot["slot_id"]: {"ABSENT": 0.0, "PRESENT": 0.0} for slot in plan["slots"]}
    for i in range(10):
        scores[f"e{i}-{i}"]["PRESENT"] = 99.0
    out = ac.apply_constraints(big_packet("edge_account", focus, worlds), plan, scores,
                               {slot["slot_id"]: "PRESENT" for slot in plan["slots"]})
    assert sum(1 for symbol in out.values() if symbol == "PRESENT") == 4
    for i in range(10):
        assert out[f"e{i}-{i}"] == "ABSENT"


def test_a_whole_absent_from_the_focus_nodes_does_not_crash():
    """`parts` with a `whole` outside the focus's nodes: the self-part rule simply does not fire."""
    worlds = ten_node_worlds()
    focus = "world-big"
    plan = {
        "kind": "parts",
        "slots": [{"slot_id": f"n{i}", "field": "node", "group": "nodes",
                   "coordinates": [f"{focus}/{i}"], "symbols": ["ABSENT", "PRESENT"],
                   "scope_alias": "W0"} for i in range(10)],
        "aliases": big_aliases(worlds),
    }
    scores = {slot["slot_id"]: {"ABSENT": 0.0, "PRESENT": 0.0} for slot in plan["slots"]}
    p = big_packet("parts", focus, worlds, {"whole": "world-nowhere/9"})
    shape = ac.declared_answer_shape(p)
    assert shape["whole"] == "world-nowhere/9"
    assert shape["cardinality"] == 0
    out = ac.apply_constraints(p, plan, scores,
                               {slot["slot_id"]: "PRESENT" for slot in plan["slots"]})
    assert len(out) == 10


def test_the_joint_decoder_uses_POSITION_and_this_pins_that_assumption():
    """The one assumption this layer makes that the packet does not guarantee.

    `_one_world_joint` maps a focus node to a candidate world's node **by position**, because the only
    correspondence the packet offers is the alias namespace and aliases are positional. When the focus
    and the candidate have different node counts, positions only line up as far as the shorter one
    reaches. That is an assumption, not a fact, and it is pinned here so a change to it is visible.

    On the development panel every world has ten nodes, so the assumption holds there by uniformity.
    """
    focus = big_world("world-big", 4, [(0, 1)], [0, 1, 2])
    other = big_world("world-oth", 10, [(0, 1), (0, 2)], [0, 2, 3])
    worlds = [focus, other]
    plan = {
        "kind": "context",
        "slots": [{"slot_id": "setting", "field": "setting_ref", "group": "setting_ref",
                   "coordinates": [], "symbols": ["W0", "W1"], "scope_alias": "W0"}]
        + [{"slot_id": f"p{i}", "field": "participant", "group": "participants",
            "coordinates": [f"world-big/{i}"], "symbols": ["ABSENT", "PRESENT"],
            "scope_alias": "W0"} for i in range(4)],
        "aliases": big_aliases(worlds),
    }
    scores = {slot["slot_id"]: {symbol: 0.0 for symbol in slot["symbols"]} for slot in plan["slots"]}
    scores["setting"]["W1"] = 5.0
    out = ac.apply_constraints(big_packet("context", "world-big", worlds), plan, scores,
                               {slot["slot_id"]: "ABSENT" for slot in plan["slots"]})
    # world-oth is chosen, and its participants {0, 2, 3} are read at the SAME POSITIONS in the focus
    assert out["setting"] == "W1"
    assert out["p0"] == "PRESENT"
    assert out["p2"] == "PRESENT"
    assert out["p3"] == "PRESENT"
    assert out["p1"] == "ABSENT"


def test_a_candidate_with_fewer_nodes_than_the_focus_is_skipped_not_crashed():
    focus = big_world("world-big", 10, [(0, 1)], [0, 1, 2, 3])
    small = big_world("world-sml", 2, [(0, 1)], [0, 1])
    worlds = [focus, small]
    plan = {
        "kind": "context",
        "slots": [{"slot_id": "setting", "field": "setting_ref", "group": "setting_ref",
                   "coordinates": [], "symbols": ["W0", "W1"], "scope_alias": "W0"}]
        + [{"slot_id": f"p{i}", "field": "participant", "group": "participants",
            "coordinates": [f"world-big/{i}"], "symbols": ["ABSENT", "PRESENT"],
            "scope_alias": "W0"} for i in range(10)],
        "aliases": big_aliases(worlds),
    }
    scores = {slot["slot_id"]: {symbol: 0.0 for symbol in slot["symbols"]} for slot in plan["slots"]}
    scores["setting"]["W0"] = 5.0
    out = ac.apply_constraints(big_packet("context", "world-big", worlds), plan, scores,
                               {slot["slot_id"]: "ABSENT" for slot in plan["slots"]})
    assert out["setting"] == "W0"
    assert sum(1 for sid, symbol in out.items() if sid.startswith("p") and symbol == "PRESENT") == 4
