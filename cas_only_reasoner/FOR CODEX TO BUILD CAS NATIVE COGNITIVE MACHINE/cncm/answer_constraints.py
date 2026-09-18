"""Declared-constraint layer for the typed-teaching decision step.

Pure standard library. No torch, no device, no model, no training, no run. Nothing frozen is read or
written: this module takes a packet and a score table and returns corrected selections.

Why it exists
-------------
`cas_meta2.typed_teaching.slots.score_decisions` has exactly two branches: an independent per-slot
``max``, and a joint candidate MAP for ``correspondence`` alone. Every other kind is decided slot by
slot with no knowledge of what the packet says a legal answer looks like.

**But the packet declares that, per kind, and nothing reads it.** Measured over six runs on the
recorded scores, enforcing those declarations is worth, truth-free:

    parts          declared out-edge count of the supplied `whole`   29.2453% -> 74.2138%
    definition     FOCUS_WORLD_DECLARATION_IDENTITY                  0.0000% -> 10.2381%
    edge_account   self-links are never PRESENT                      0.0000% ->  4.2857%
    context        one-world joint decode                            0.0000% ->  4.0476%

Sources: `ALL_DECLARED_CONSTRAINTS_RESULT.md`, `AUDIT_RESPONSE_AND_SELFLINKS.md`,
`STRUCTURAL_CONSTANTS_RESULT.md`, `measure_one_world_joint.py`.

This module is **additive and off by default**. It is not wired into any run, it does not modify
`slots.score_decisions`, and importing it changes no existing behaviour. It exists so that the layer
is real code with tests rather than a set of one-off scripts.

The constraints, and the evidence for each
------------------------------------------
1. **No self-links.** Across 216,576 world declarations and 649,728 declared edges there are zero
   edges whose source equals its target. So every ``edge_account`` slot for a pair (a, a) is ABSENT,
   and every ``parts`` slot for the supplied ``whole`` itself is ABSENT. Both are structural: true of
   the task, not of a run.
2. **Declared cardinality.** ``focus["contains"]`` is in the packet, so the number of PRESENT edge
   slots is known; likewise the number of declared edges whose source is the supplied ``whole``; and
   ``answers.answer_space`` declares ``participants_basis = PRIMARY_AUTHORED_LABELS_FIRST_THREE``, so
   the participant set has a declared size.
3. **One-world identity.** ``FOCUS_WORLD_DECLARATION_IDENTITY``: a ``definition`` answer is one
   world's declaration triple and a ``context`` answer is one world's setting plus participants --
   not free choices per slot. Enumerate the bank, score each world's implied answer, take the argmax.

What this module deliberately does not do
-----------------------------------------
It does not touch the encoder, the readout, the block, or `slots.score_decisions`. Round 36 measured
that a fitted readout cannot be installed through the frozen `[90, 64]` readout at all
(`RECTANGULAR_REALISATION_RESULT.md`), so a change to those components would need a new baseline.
This one does not: it corrects the decoder only, so a run using it stays comparable to every run so
far except in the decision contract's digest.
"""

from __future__ import annotations

__all__ = [
    "CONSTRAINTS",
    "apply_constraints",
    "declared_answer_shape",
    "node_positions",
    "score_decisions",
]

#: The kinds this layer has a measured constraint for. Others are returned untouched.
CONSTRAINTS = ("edge_account", "parts", "context", "definition")


def node_positions(world: dict) -> dict:
    """``{node ref: position within this world}``. The only node correspondence the packet offers."""
    return {node["ref"]: at for at, node in enumerate(world["nodes"])}


def _focus(packet: dict) -> dict:
    focus_id = packet["record"]["query"]["focus_world_id"]
    for world in packet["source"]["worlds"]:
        if world["world_id"] == focus_id:
            return world
    raise KeyError("the query's focus world is not in the supplied bank")


def declared_answer_shape(packet: dict) -> dict:
    """Everything the packet declares about the answer's shape, for the query's kind.

    Returns a dict with the declared cardinalities and, where the kind has one, the world whose
    declaration the answer must be. Nothing here is inferred from a target.
    """
    query = packet["record"]["query"]
    kind = query["kind"]
    focus = _focus(packet)
    out = {"kind": kind, "nodes": len(focus["nodes"]), "focus_world_id": focus["world_id"]}
    if kind == "edge_account":
        out["cardinality"] = len(focus["contains"])
        out["self_pairs_absent"] = True
    elif kind == "parts":
        whole = query["arguments"]["whole"]
        out["whole"] = whole
        out["cardinality"] = sum(1 for edge in focus["contains"] if edge["source"] == whole)
        out["self_pairs_absent"] = True
    elif kind == "context":
        out["cardinality"] = len(focus["declarations"]["participants"])
        out["basis"] = focus["declarations"]["participants_basis"]
    elif kind == "definition":
        out["identity"] = "FOCUS_WORLD_DECLARATION_IDENTITY"
    return out


def _field_slots(plan: dict, field: str) -> list:
    return [slot for slot in plan["slots"] if slot["field"] == field]


def _rank(slot_ids: list, scores: dict, symbol: str) -> list:
    """Slot ids ordered by ``symbol``'s score, highest first. Ties broken by slot id for determinism."""
    return sorted(slot_ids, key=lambda sid: (-scores[sid][symbol], sid))


def _apply_cardinality(selected: dict, slots: list, scores: dict, k: int) -> None:
    """Force exactly ``k`` of ``slots`` to PRESENT, choosing the ``k`` best by PRESENT minus ABSENT."""
    if k < 0 or k > len(slots):
        return
    ranked = _rank([slot["slot_id"] for slot in slots], scores, "PRESENT")
    for rank, slot_id in enumerate(ranked):
        selected[slot_id] = "PRESENT" if rank < k else "ABSENT"


def _one_world_joint(packet: dict, plan: dict, scores: dict, selected: dict) -> bool:
    """Score each world's implied answer and take the argmax. Returns whether anything was applied."""
    kind = plan["kind"]
    query = packet["record"]["query"]
    focus = _focus(packet)
    focus_at = node_positions(focus)
    whole = query["arguments"].get("whole")
    whole_at = focus_at.get(whole) if whole is not None else None
    aliases = {world["world_id"]: world for world in plan["aliases"]["worlds"]}

    best, best_score = None, None
    for world in packet["source"]["worlds"]:
        alias = aliases.get(world["world_id"])
        if alias is None:
            continue
        refs = [node["ref"] for node in world["nodes"]]
        positions = node_positions(world)
        # Node ALIASES live in the plan's alias table, not in `packet["source"]["worlds"]`; the
        # packet's world nodes carry `ref`, `kind` and `label` only. Reading `world["nodes"][at]
        # ["alias"]` raises KeyError on real packets, which is how this was found.
        ref_alias = {node["ref"]: node["alias"] for node in alias["nodes"]}
        declared = set(world["declarations"]["participants"])
        contains = {(edge["source"], edge["target"]) for edge in world["contains"]}
        implied, total, usable = {}, 0.0, True
        for slot in plan["slots"]:
            field = slot["field"]
            if kind == "definition":
                if field == "whole":
                    symbol = ref_alias.get(world["declared_whole"])
                    if symbol is None:
                        usable = False
                        break
                elif field in ("kind_ref", "function_ref"):
                    symbol = alias["alias"]
                else:
                    continue
            elif kind == "context":
                if field == "setting_ref":
                    symbol = alias["alias"]
                elif field == "participant":
                    at = focus_at[slot["coordinates"][0]]
                    if at >= len(refs):
                        usable = False
                        break
                    symbol = "PRESENT" if refs[at] in declared else "ABSENT"
                else:
                    continue
            else:
                continue
            if symbol not in slot["symbols"]:
                usable = False
                break
            implied[slot["slot_id"]] = symbol
            total += scores[slot["slot_id"]][symbol]
        if not usable:
            continue
        if best_score is None or total > best_score:
            best, best_score = implied, total
    if best is None:
        return False
    selected.update(best)
    return True


def apply_constraints(packet: dict, plan: dict, scores: dict, selected: dict) -> dict:
    """Correct ``selected`` using only what the packet declares. Returns a new dict.

    ``scores`` must cover every slot and symbol, as ``slots.score_decisions`` requires. ``selected``
    is the unconstrained result. Anything not covered by a measured constraint is returned unchanged.
    """
    out = dict(selected)
    kind = plan["kind"]
    if kind not in CONSTRAINTS:
        return out
    shape = declared_answer_shape(packet)

    # 1. self-links and self-parts are structurally absent
    if shape.get("self_pairs_absent"):
        if kind == "edge_account":
            for slot in _field_slots(plan, "edge"):
                if slot["coordinates"][0] == slot["coordinates"][1]:
                    out[slot["slot_id"]] = "ABSENT"
        else:
            for slot in _field_slots(plan, "node"):
                if slot["coordinates"][0] == shape.get("whole"):
                    out[slot["slot_id"]] = "ABSENT"

    # 2. declared cardinality, over the slots that survive rule 1
    if kind == "edge_account":
        candidates = [slot for slot in _field_slots(plan, "edge")
                      if slot["coordinates"][0] != slot["coordinates"][1]]
        _apply_cardinality(out, candidates, scores, shape["cardinality"])
    elif kind == "parts":
        candidates = [slot for slot in _field_slots(plan, "node")
                      if slot["coordinates"][0] != shape.get("whole")]
        _apply_cardinality(out, candidates, scores, shape["cardinality"])

    # 3. one-world identity
    if kind in ("definition", "context"):
        _one_world_joint(packet, plan, scores, out)

    return out


def score_decisions(packet: dict, scores: dict, *, declared_constraints: bool = False) -> dict:
    """Drop-in replacement for :func:`cas_meta2.typed_teaching.slots.score_decisions`.

    With ``declared_constraints=False`` -- the default -- this is **exactly** the run's own decoder and
    returns byte-identical output, which is what makes it safe to put in place of the original before
    anything is decided. With ``declared_constraints=True`` it applies :func:`apply_constraints` to
    the result.

    Measured on the recorded six-run score table, enabling the layer gives **+6.6194 points pooled**
    (34.6631% -> 41.2825%), **+12.4861** on the many-decision half and **+0.0000** on the one-decision
    half, and the gain is world-invariant. See `CONSTRAINT_LAYER_RESULT.md` and
    `WIRING_AND_INVARIANCE_RESULT.md`.

    Why a flag rather than a new function: the encoder's input does not include the decision contract
    (`binding._query_spec` reads kind, field, group, scope, coordinates and symbols only), so with the
    flag off nothing anywhere changes -- not one digest, not one score. Measured across all 564 packets
    and 2,598 slots in `measure_wiring_impact.py`. Enabling it is the owner's call; making it
    *available* while off changes nothing.

    The run's decoder is imported **here**, not at module load. The rules above operate on plain packet
    and plan dictionaries and must stay usable without `cas_meta2` on the path; only this drop-in needs
    it.
    """
    from cas_meta2.typed_teaching import slots as _slots

    plan = _slots.compile_slots(packet)
    decisions = _slots.score_decisions(packet, scores)
    if not declared_constraints:
        return decisions
    corrected = dict(decisions)
    corrected["selected"] = apply_constraints(packet, plan, scores, decisions["selected"])
    return corrected
