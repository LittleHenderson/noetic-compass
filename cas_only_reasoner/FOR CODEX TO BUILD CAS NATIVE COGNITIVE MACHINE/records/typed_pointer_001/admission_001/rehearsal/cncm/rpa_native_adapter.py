"""Read-only CAS-RPA projection of semantically replayed native evidence.

This adapter never imports a saved state, advances the live machine, installs a
procedure, assigns a probability, or translates Foundation/Drive namespaces.
Its action hints are necessary-condition diagnostics, never kernel authorization.
"""
from __future__ import annotations

from .canonical import canonical_json, content_id
from .model import TerminalStatus
from .native_model import NativeIntentType
from .native_profile import NATIVE_WORK_COSTS
from .native_recovery import replay_native_journal
from .rpa_model import (AtlasContext, AtlasNode, AtlasLink, AtlasSnapshot,
                        LinkType, NodeKind, NodeStatus)

VIEW_SCHEMA = "cncm.native-rpa-view/0.1"


def proposed_next_actions(machine):
    state, spec = machine.state, machine.problem.call
    call = next((row for row in state.native_calls if row.call_id == spec.call_id), None)
    blockers = []
    if state.halt_status is not TerminalStatus.RUNNING:
        return [{"action": "START_NEW_EPISODE", "readiness": "blocked" if state.rpm_stack else "requires_new_episode",
            "blockers": ["Current episode is terminal; a new episode is a separate trusted-host operation."
                if not state.rpm_stack else "Unresolved acquisition frame prevents a new episode."],
            "authority": "PROPOSAL_ONLY"}]
    if state.commitment_state.decision_status == "COMMITTED":
        action = "HALT"
    elif machine.coordinator.trace.events and machine.coordinator.trace.events[-1].rejected_intents:
        action = "RETURN_ACQUISITION" if state.rpm_stack else "HALT"
    elif call is None:
        action = "REQUEST_PROCEDURE_CALL"
    elif call.status == "REQUESTED":
        action = "PUSH_ACQUISITION"
    elif call.status == "SUSPENDED":
        if call.artifact_sha256:
            action = "RETURN_ACQUISITION"
        elif machine.coordinator.selected_artifact(spec.call_id):
            action = "INSTALL_PROCEDURE"
        else:
            action = "SELECT_PROCEDURE"
    elif call.status == "READY":
        action = "APPLY_PROCEDURE"
    elif call.status == "COMPLETE":
        action = "ORDINARY_REASONING_AND_COMMITMENT_GATES"
    else:
        action = "HALT"
    cost = NATIVE_WORK_COSTS.get(action, (0, 0))
    if state.native_budget.instructions_remaining < cost[0]:
        blockers.append("Insufficient remaining procedure instruction allocation.")
    if state.native_budget.checker_calls_remaining < cost[1]:
        blockers.append("Insufficient remaining checker-call allocation.")
    if state.budget.ticks_remaining <= 1 and action != "HALT":
        blockers.append("Last tick is reserved for halt.")
    return [{"action": action,
        "readiness": "blocked" if blockers else "necessary_conditions_present",
        "blockers": blockers, "authority": "PROPOSAL_ONLY"}]


def native_atlas_from_journal(journal, *, trusted_genesis, expected_journal_digest, profile=None):
    machine = replay_native_journal(journal, trusted_genesis=trusted_genesis,
        expected_journal_digest=expected_journal_digest, profile=profile)
    verified = machine.journal()
    state, spec = machine.state, machine.problem.call
    nodes, links, timeline = {}, [], []

    def context(run_id, tick, observation):
        return AtlasContext(context_id=run_id, model_version=VIEW_SCHEMA,
            observation_id="observation-"+observation,
            observation_time="logical-tick:"+str(tick), record_version=tick)

    current_context = context(state.run_id, state.logical_tick, state.state_hash)

    def node(node_id, label, *, ctx=current_context, status="observed",
             kind="idea_context", fields=None, evidence=(), members=None, idea=None):
        value = AtlasNode(node_id=node_id, idea_id=idea or node_id, label=label,
            context=ctx, status=NodeStatus(status), kind=NodeKind(kind),
            fields=tuple(sorted((key, str(value)) for key, value in (fields or {}).items())),
            members=members, evidence_refs=tuple(evidence))
        nodes[node_id] = value
        return node_id

    def link(source, target, relation, *, projection=None, action=None, evidence=(), transition=None):
        identity = {"source": source, "target": target, "relation": relation, "action": action}
        links.append(AtlasLink(link_id=content_id("rpa-link", identity),
            source_id=source, target_id=target, relation=LinkType(relation),
            projection=projection, action_id=action, evidence_refs=tuple(evidence),
            transition_status=transition))

    def state_id(hash_value):
        return "native-state-"+hash_value

    previous_final = None
    for episode in verified["episodes"]:
        run_id = episode["final_state"]["run_id"]
        start = episode["initial_state_hash"]
        node(state_id(start), "Episode started", ctx=context(run_id, 0, start), kind="state",
            fields={"state_hash": start, "run_id": run_id, "record": "replayed episode genesis"},
            evidence=(expected_journal_digest,))
        if previous_final:
            link(state_id(previous_final), state_id(start), "reachable_via",
                action="START_NEW_EPISODE", evidence=(expected_journal_digest,), transition="observed")
        work_by_intent = {}
        for record in episode["final_state"]["native_records"]:
            if record["kind"] == "WORK_RESERVATION":
                import json
                body = json.loads(record["body_json"])
                work_by_intent[body["intent_id"]] = body
        for event in episode["trace"]:
            authorized = set(event["authorized_intent_ids"])
            kinds = [row["intent_type"] for row in event["proposed_intents"]]
            outcome = ("PARTIALLY_ACCEPTED" if authorized and event["rejected_intents"]
                       else "REJECTED" if event["rejected_intents"] else "ACCEPTED")
            reserved = [work_by_intent[row["intent_id"]] for row in event["proposed_intents"]
                        if row["intent_id"] in work_by_intent]
            work = {"instructions_allocated": sum(row["instructions_allocated"] for row in reserved),
                "checker_calls_allocated": sum(row["checker_calls_allocated"] for row in reserved),
                "basis": "conservative_policy_units"}
            action = "+".join(kinds) or "EMPTY_BATCH"
            action_id = content_id("action", kinds) if len(kinds) > 1 else action
            node(state_id(event["post_state_hash"]), "Tick "+str(event["logical_tick"])+": "+action,
                ctx=context(run_id, event["logical_tick"], event["post_state_hash"]), kind="state",
                fields={"state_hash": event["post_state_hash"], "run_id": run_id,
                    "outcome": outcome, "event_hash": event["event_hash"],
                    "terminal_status": event["terminal_status"],
                    "work": canonical_json(work)}, evidence=(event["event_hash"],))
            link(state_id(event["pre_state_hash"]), state_id(event["post_state_hash"]), "reachable_via",
                action=action_id, evidence=(event["event_hash"],),
                transition="rejected" if outcome == "REJECTED" else "observed")
            timeline.append({"event_hash": event["event_hash"], "run_id": run_id,
                "tick": event["logical_tick"], "intent_types": kinds, "outcome": outcome,
                "authorized_intent_ids": event["authorized_intent_ids"],
                "rejected_intent_ids": [row["intent_id"] for row in event["rejected_intents"]],
                "committed_mutations": event["committed_mutations"],
                "pre_state_hash": event["pre_state_hash"], "post_state_hash": event["post_state_hash"],
                "work": work})
        previous_final = episode["final_state"]["state_hash"]

    current_id = state_id(state.state_hash)
    current = nodes[current_id]
    nodes[current_id] = AtlasNode(node_id=current.node_id, idea_id=current.idea_id,
        label="Current retained state: "+state.halt_status.value.lower().replace("_", " "),
        context=current.context, status=current.status, kind=current.kind,
        fields=current.fields, evidence_refs=current.evidence_refs)

    call = next((row for row in state.native_calls if row.call_id == spec.call_id), None)
    call_idea = content_id("call-view", {"run_id": state.run_id, "call_id": spec.call_id})
    call_id = node("current-call", "Original caller", idea=call_idea,
        fields={"call_id": spec.call_id, "goal_id": spec.goal_id, "branch_id": spec.branch_id,
                "capability": spec.capability, "stage": "NOT_REQUESTED" if call is None else call.status},
        members=("bound-call",), evidence=(expected_journal_digest,))
    link(current_id, call_id, "contains_part", projection="native_problem.call and native_calls")
    refined_id = node("bound-call-inputs", "Exact input and version requirements",
        idea=call_idea,
        fields={"call_id": spec.call_id, "goal_id": spec.goal_id, "branch_id": spec.branch_id,
                "capability": spec.capability, "stage": "NOT_REQUESTED" if call is None else call.status,
                "inputs": canonical_json(spec.inputs_dict()), "inputs_digest": spec.inputs_digest,
                "output_contract": spec.output_contract, "source_profile_digest": machine.profile.profile_digest},
        members=("bound-call",), evidence=(expected_journal_digest,))
    link(call_id, refined_id, "refines_state", evidence=(expected_journal_digest,))
    parts = [
        ("budget", "Remaining work budget", {
            "procedure_instructions": state.native_budget.instructions_remaining,
            "checker_calls": state.native_budget.checker_calls_remaining,
            "ordinary_ticks": state.budget.ticks_remaining, "units": "conservative policy allocations"}),
        ("procedure", "Installed procedure", {
            "capability": spec.capability, "active_head": dict(state.procedure_heads).get(spec.capability, "ABSENT"),
            "retained_artifact_count": len(state.procedural_artifacts)}),
        ("continuation", "Saved return point", {
            "active_goal": state.active_goal_id, "stack": canonical_json([row.to_dict() for row in state.rpm_stack]),
            "caller_resumption": "suspended" if state.rpm_stack else "no active acquisition frame"}),
        ("result", "Current call result", {
            "output": "NONE" if call is None or call.output is None else call.output,
            "call_stage": "NOT_REQUESTED" if call is None else call.status,
            "committed_conclusion": canonical_json(state.commitment_state.conclusion.to_dict())
                if state.commitment_state.conclusion else "NONE"}),
    ]
    for name, label, fields in parts:
        target = node("current-"+name, label, fields=fields, evidence=(expected_journal_digest,))
        link(current_id, target, "contains_part", projection="native_state."+name)

    for record in state.native_records:
        body = record.body_dict()
        record_id = node("record-"+record.record_digest, record.kind.replace("_", " ").title(),
            kind="evidence", fields={"record_kind": record.kind, "record_digest": record.record_digest,
                "body": record.body_json, "historical_run_id": body["run_id"]},
            evidence=(record.record_digest,))
        link(current_id, record_id, "contains_part", projection="native_records:immutable-history",
            evidence=(record.record_digest,))
    hints = proposed_next_actions(machine)
    hypothesis = None
    for index, hint in enumerate(hints):
        target = node("proposal-"+str(index), hint["action"], status="hypothetical",
            fields={"readiness": hint["readiness"], "blockers": canonical_json(hint["blockers"]),
                "authority": "PROPOSAL_ONLY"}, evidence=())
        link(current_id, target, "reachable_via", action=hint["action"], transition="candidate")
        hypothesis = target
    atlas = AtlasSnapshot(nodes=tuple(nodes.values()), links=tuple(links),
        current_state_id=current_id, focus_node_id=current_id, hypothesis_branch_id=hypothesis)
    return {"schema_version": VIEW_SCHEMA, "atlas": atlas.to_dict(),
        "native": {"current_state_hash": state.state_hash, "source_profile_digest": machine.profile.profile_digest,
            "journal_digest": expected_journal_digest, "terminal_status": state.halt_status.value,
            "output": None if call is None else call.output,
            "scope": "Read-only projection of semantically replayed native evidence. Suggestions have no write authority; CAS profiles/probabilities and Foundation-to-Drive mapping are unassigned."},
        "timeline": timeline, "next_actions": hints}
