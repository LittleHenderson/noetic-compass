"""Snapshot-bound atlas addresses for acquisition frames. Read-only projection.

Return-address addendum RPA-RETURN-1 (CAS-CLOSED-LOOP-1), sections 2-4: an
exact address names episode, branch, source snapshot, board/CJT, call
occurrence and saved continuation, reusing existing runtime identifiers and
the atlas's snapshot-bound node scheme. The address is a lookup key. It is
not authority: nothing here resumes, dispatches, mutates native state or
adds a registry. The existing CompoundCoordinator remains the only writer.

Every identity used already exists in the pinned runtime:
- run_id, branch-main, root goal and root call occurrence (CompoundState);
- the unique authorized PUSH_*_ACQUISITION event that created the frame
  (sealed event id/hash, tick, pre/post state hashes);
- the frame itself (frame_id embeds the push-time state hash, call_id,
  parent call digest, return_address, resume_stage, depth);
- the atlas node ids and contexts the pinned rpa_compound_adapter assigns:
  'state-<hash>' with AtlasContext(run, VIEW_SCHEMA, 'observation-<hash>',
  'logical-tick:<n>', n) and 'frame-<frame_id>' for live frames.

Profile coordinates are never used to locate a caller. Screen focus and
layout are not inputs. There is no nearest-node fallback: an address either
resolves to the exact node or is refused with a named reason.
"""
from __future__ import annotations

import re

from cncm.canonical import canonical_json, digest
from cncm.compound_engine import CompoundMachine
from cncm.compound_model import CompoundFrame
from cncm.rpa_compound_adapter import VIEW_SCHEMA
from cncm.rpa_model import CONTEXT_SCHEMA

ADDRESS_SCHEMA = "cas.closed-loop.atlas-address/0.1"
RESOLUTION_SCHEMA = "cas.closed-loop.atlas-address-resolution/0.1"
PUSH_INTENTS = ("PUSH_COMPOUND_ACQUISITION", "PUSH_PRIMITIVE_ACQUISITION")
AUTHORITY = "READ_ONLY_ADDRESS_NOT_A_RESUME_TOKEN"
_SHA = re.compile(r"[0-9a-f]{64}\Z")
ADDRESS_FIELDS = (
    "schema", "run_id", "branch", "source_profile", "root_goal", "root_call_occurrence",
    "suspension", "snapshot_node_id", "atlas_context", "waiting_state_node_id",
    "waiting_atlas_context", "frame_node_id", "continuation", "profile_coordinates", "authority",
)


class AddressRefused(ValueError):
    """The address cannot be built or resolved; the reason is the message."""


def _require(condition, reason):
    if not condition:
        raise AddressRefused(reason)


def _validated(machine):
    _require(type(machine) is CompoundMachine, "EXACT_COMPOUND_MACHINE_REQUIRED")
    try:
        return machine.result()  # native validation of the whole chain and current state
    except Exception as error:
        raise AddressRefused("NATIVE_HISTORY_INVALID") from error


def _context(run_id, tick, state_hash):
    return {"context_id": run_id, "model_version": VIEW_SCHEMA, "observation_id": "observation-" + state_hash,
            "observation_time": "logical-tick:" + str(tick), "record_version": tick}


def suspension_event_for(observed, frame):
    """The unique authorized push event whose proposed frame is exactly this frame."""
    matches = []
    for event in observed.trace:
        for intent in event.proposed_intents:
            if (intent.intent_id in event.authorized_intent_ids and intent.intent_type.value in PUSH_INTENTS
                    and intent.mutation_dict().get("frame") == frame.to_dict()):
                matches.append(event)
    _require(len(matches) == 1, "SUSPENSION_EVENT_NOT_UNIQUE")
    event = matches[0]
    _require(event.sealed and event.event_hash == event.computed_hash(), "SUSPENSION_EVENT_UNSEALED")
    return event


def address_for_frame(machine, frame):
    """Exact, snapshot-bound address of one live acquisition frame."""
    observed = _validated(machine)
    state = observed.final_state
    _require(type(frame) is CompoundFrame and any(row == frame for row in state.rpm_stack), "FRAME_NOT_LIVE")
    event = suspension_event_for(observed, frame)
    root = state.compound_call
    body = {
        "schema": ADDRESS_SCHEMA,
        "run_id": state.run_id,
        "branch": "branch-main",
        "source_profile": machine.profile.profile_digest,
        "root_goal": machine.problem.reasoning.goal_id,
        "root_call_occurrence": root.call_id if root else None,
        "suspension": {"event_id": event.event_id, "event_hash": event.event_hash,
                       "logical_tick": event.logical_tick, "pre_state_hash": event.pre_state_hash,
                       "post_state_hash": event.post_state_hash},
        "snapshot_node_id": "state-" + event.pre_state_hash,
        "atlas_context": _context(state.run_id, event.logical_tick - 1, event.pre_state_hash),
        "waiting_state_node_id": "state-" + event.post_state_hash,
        "waiting_atlas_context": _context(state.run_id, event.logical_tick, event.post_state_hash),
        "frame_node_id": "frame-" + frame.frame_id,
        "continuation": {**frame.to_dict(), "frame_digest": digest(frame.to_dict())},
        "profile_coordinates": None,
        "authority": AUTHORITY,
    }
    return {**body, "address_digest": digest(body)}


def address_chain(machine):
    """Addresses for every live frame, innermost last, plus the root reference."""
    observed = _validated(machine)
    state = observed.final_state
    root = state.compound_call
    return {"schema": "cas.closed-loop.atlas-address-chain/0.1", "run_id": state.run_id,
            "state_hash": state.state_hash, "logical_tick": state.logical_tick,
            "root_goal": machine.problem.reasoning.goal_id,
            "root_call_occurrence": root.call_id if root else None,
            "frames": [address_for_frame(machine, frame) for frame in state.rpm_stack],
            "authority": AUTHORITY}


def check_address(address):
    _require(type(address) is dict and set(address) == set(ADDRESS_FIELDS) | {"address_digest"}, "ADDRESS_FIELDS_INVALID")
    _require(address["schema"] == ADDRESS_SCHEMA and address["authority"] == AUTHORITY, "ADDRESS_SCHEMA_INVALID")
    body = {key: value for key, value in address.items() if key != "address_digest"}
    _require(address["address_digest"] == digest(body), "ADDRESS_DIGEST_MISMATCH")
    suspension = address["suspension"]
    _require(type(suspension) is dict and set(suspension) == {"event_id", "event_hash", "logical_tick", "pre_state_hash", "post_state_hash"}
             and all(_SHA.fullmatch(suspension[key]) for key in ("event_hash", "pre_state_hash", "post_state_hash"))
             and type(suspension["logical_tick"]) is int and suspension["logical_tick"] >= 1, "ADDRESS_SUSPENSION_INVALID")
    _require(address["snapshot_node_id"] == "state-" + suspension["pre_state_hash"]
             and address["waiting_state_node_id"] == "state-" + suspension["post_state_hash"]
             and address["frame_node_id"] == "frame-" + address["continuation"]["frame_id"], "ADDRESS_NODE_IDS_INCONSISTENT")
    _require(address["profile_coordinates"] is None, "PROFILE_COORDINATES_HAVE_NO_ADDRESS_ROLE")
    return address


def _node_fields(node):
    return {key: value for key, value in node["fields"]}


def resolve_address(view, address):
    """Resolve an address against a rendered atlas view. Exact match or a named refusal.

    Focus, hypothesis handle and layout of the view are ignored. The result
    grants nothing: it names nodes for inspection only.
    """
    check_address(address)
    _require(type(view) is dict and view.get("schema_version") == VIEW_SCHEMA, "ATLAS_VIEW_REQUIRED")
    suspension, continuation = address["suspension"], address["continuation"]
    frame = {key: value for key, value in continuation.items() if key != "frame_digest"}
    events = [row["event"] for row in view["timeline"] if row["event"]["event_hash"] == suspension["event_hash"]]
    _require(len(events) == 1, "SUSPENSION_EVENT_NOT_IN_VIEW")
    event = events[0]
    _require(event["event_id"] == suspension["event_id"] and event["logical_tick"] == suspension["logical_tick"]
             and event["pre_state_hash"] == suspension["pre_state_hash"] and event["post_state_hash"] == suspension["post_state_hash"]
             and event["run_id"] == address["run_id"], "SUSPENSION_EVENT_MISMATCH")
    pushed = [intent for intent in event["proposed_intents"] if intent["intent_id"] in event["authorized_intent_ids"]
              and intent["intent_type"] in PUSH_INTENTS and intent["proposed_mutation"].get("frame") == frame]
    _require(len(pushed) == 1, "SUSPENSION_EVENT_FRAME_MISMATCH")
    nodes = {node["node_id"]: node for node in view["atlas"]["nodes"]}  # exact keys only; no nearest lookup
    snapshot = nodes.get(address["snapshot_node_id"])
    _require(snapshot is not None, "SNAPSHOT_NODE_NOT_FOUND")
    _require(snapshot["kind"] == "state" and snapshot["context"] == {"schema_version": CONTEXT_SCHEMA, **address["atlas_context"]}
             and _node_fields(snapshot).get("state_hash") == suspension["pre_state_hash"], "SNAPSHOT_NODE_MISMATCH")
    waiting = nodes.get(address["waiting_state_node_id"])
    _require(waiting is not None, "WAITING_NODE_NOT_FOUND")
    _require(waiting["kind"] == "state" and waiting["context"] == {"schema_version": CONTEXT_SCHEMA, **address["waiting_atlas_context"]}
             and _node_fields(waiting).get("state_hash") == suspension["post_state_hash"]
             and suspension["event_hash"] in waiting["evidence_refs"], "WAITING_NODE_MISMATCH")
    live = any(row == frame for row in view["native"]["frames"])
    frame_node = nodes.get(address["frame_node_id"])
    if live:
        expected = [[key, value if type(value) is str else canonical_json(value)] for key, value in sorted(frame.items())]
        _require(frame_node is not None and [list(row) for row in frame_node["fields"]] == expected, "LIVE_FRAME_NODE_MISSING_OR_CHANGED")
        status = "RESOLVED_LIVE_FRAME"
    else:
        _require(frame_node is None, "STALE_FRAME_NODE_PRESENT")
        status = "RESOLVED_HISTORICAL_FRAME_NOT_LIVE"
    return {"schema": RESOLUTION_SCHEMA, "status": status, "address_digest": address["address_digest"],
            "snapshot_node_id": address["snapshot_node_id"], "waiting_state_node_id": address["waiting_state_node_id"],
            "frame_node_id": address["frame_node_id"] if live else None,
            "view_current_state_id": view["atlas"]["current_state_id"],
            "view_focus_node_id": view["atlas"]["focus_node_id"],
            "authority": "READ_ONLY_RESOLUTION_NO_RESUME_NO_DISPATCH"}
