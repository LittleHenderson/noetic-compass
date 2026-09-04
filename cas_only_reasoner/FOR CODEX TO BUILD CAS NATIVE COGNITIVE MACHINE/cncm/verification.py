"""Independent structural verification for retained CNCM artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .canonical import digest
from .model import ContractError, ProblemPacket, TerminalStatus


def _proposition_key(value: Mapping[str, Any]) -> str:
    predicate = value["predicate"]
    arguments = value["arguments"]
    polarity = value["polarity"]
    scope = value["scope"]
    if (
        not isinstance(predicate, str)
        or not isinstance(arguments, list)
        or any(not isinstance(item, str) for item in arguments)
        or not isinstance(polarity, bool)
        or not isinstance(scope, str)
    ):
        raise TypeError("invalid proposition projection")
    atom = f"{predicate}({','.join(arguments)})@{scope}"
    return atom if polarity else f"not:{atom}"


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


@dataclass(frozen=True, slots=True)
class VerificationReport:
    valid: bool
    checks: tuple[tuple[str, bool], ...]
    errors: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "cncm.verification/0.1",
            "valid": self.valid,
            "checks": [{"name": name, "passed": passed} for name, passed in self.checks],
            "errors": list(self.errors),
        }


def validate_problem(document: Mapping[str, Any]) -> VerificationReport:
    try:
        ProblemPacket.from_dict(document)
    except (ContractError, KeyError, TypeError, ValueError) as exc:
        return VerificationReport(False, (("problem_contract", False),), (str(exc),))
    return VerificationReport(True, (("problem_contract", True),), ())


def _verify_bundle_unchecked(bundle: Mapping[str, Any]) -> VerificationReport:
    checks: list[tuple[str, bool]] = []
    errors: list[str] = []

    def check(name: str, condition: bool, detail: str) -> None:
        checks.append((name, condition))
        if not condition:
            errors.append(detail)

    if not isinstance(bundle, Mapping):
        return VerificationReport(False, (("bundle_shape", False),), ("bundle must be an object",))
    check(
        "bundle_keys",
        set(bundle) == {"summary", "final_state", "trace", "evidence"},
        "bundle fields do not match the frozen artifact shape",
    )

    try:
        summary = bundle["summary"]
        final_state = bundle["final_state"]
        trace: Sequence[Mapping[str, Any]] = bundle["trace"]
        evidence = bundle["evidence"]
    except (KeyError, TypeError) as exc:
        return VerificationReport(False, (("bundle_shape", False),), (f"bundle shape error: {exc}",))
    if (
        not isinstance(summary, Mapping)
        or not isinstance(final_state, Mapping)
        or not isinstance(evidence, Mapping)
        or not isinstance(trace, (list, tuple))
        or any(not isinstance(event, Mapping) for event in trace)
    ):
        return VerificationReport(
            False,
            (("bundle_shape", False),),
            ("summary, final_state, evidence, and every trace event must be typed objects",),
        )

    check("trace_nonempty", bool(trace), "trace is empty")
    previous_hash = ""
    previous_event_id = None
    previous_post_hash = None
    expected_run_id = final_state.get("run_id")
    expected_runtime_version = final_state.get("runtime_version")
    for index, event in enumerate(trace):
        body = dict(event)
        retained_hash = body.pop("event_hash", None)
        computed = digest(body)
        check(f"event_{index}_hash", retained_hash == computed, f"event {index} hash mismatch")
        check(
            f"event_{index}_chain",
            event.get("previous_event_hash") == previous_hash,
            f"event {index} previous hash mismatch",
        )
        check(
            f"event_{index}_parent",
            event.get("parent_event_id") == previous_event_id,
            f"event {index} parent event mismatch",
        )
        check(f"event_{index}_sealed", event.get("sealed") is True, f"event {index} is not sealed")
        check(
            f"event_{index}_tick",
            event.get("logical_tick") == index + 1,
            f"event {index} logical tick is not contiguous",
        )
        check(
            f"event_{index}_identity",
            event.get("run_id") == expected_run_id
            and event.get("runtime_version") == expected_runtime_version,
            f"event {index} run/runtime identity mismatch",
        )
        proposed_items = event.get("proposed_intents", [])
        authorized_items = event.get("authorized_intent_ids", [])
        rejected_items = event.get("rejected_intents", [])
        intent_shapes_valid = (
            isinstance(proposed_items, list)
            and isinstance(authorized_items, list)
            and isinstance(rejected_items, list)
            and all(isinstance(item, Mapping) for item in proposed_items)
            and all(isinstance(item, str) for item in authorized_items)
            and all(isinstance(item, Mapping) for item in rejected_items)
        )
        proposed_ids = (
            [item.get("intent_id") for item in proposed_items] if intent_shapes_valid else []
        )
        authorized_ids = list(authorized_items) if intent_shapes_valid else []
        rejected_ids = (
            [item.get("intent_id") for item in rejected_items] if intent_shapes_valid else []
        )
        check(
            f"event_{index}_intent_ids",
            intent_shapes_valid
            and all(isinstance(item, str) for item in proposed_ids)
            and all(isinstance(item, str) for item in rejected_ids)
            and len(proposed_ids) == len(set(proposed_ids))
            and len(authorized_ids) == len(set(authorized_ids))
            and len(rejected_ids) == len(set(rejected_ids))
            and set(authorized_ids).isdisjoint(rejected_ids)
            and set(authorized_ids) | set(rejected_ids) == set(proposed_ids),
            f"event {index} proposed/authorized/rejected intent partition is invalid",
        )
        if previous_post_hash is not None:
            check(
                f"event_{index}_state_chain",
                event.get("pre_state_hash") == previous_post_hash,
                f"event {index} pre-state does not match prior post-state",
            )
        previous_hash = str(retained_hash or "")
        previous_event_id = event.get("event_id")
        previous_post_hash = event.get("post_state_hash")

    if trace:
        check(
            "initial_state_binding",
            trace[0].get("pre_state_hash") == evidence.get("initial_state_hash"),
            "first trace event does not bind the evidence initial state",
        )
        check(
            "trace_head",
            final_state.get("trace_head") == trace[-1].get("event_hash"),
            "final trace_head mismatch",
        )
        check(
            "final_state_event_binding",
            final_state.get("state_hash") == trace[-1].get("post_state_hash"),
            "final state is not the last traced post-state",
        )
        check(
            "terminal_event_binding",
            final_state.get("halt_status") == trace[-1].get("terminal_status"),
            "terminal status differs from final trace event",
        )
        check(
            "terminal_sequence",
            all(event.get("terminal_status") == TerminalStatus.RUNNING.value for event in trace[:-1])
            and trace[-1].get("terminal_status") != TerminalStatus.RUNNING.value,
            "terminal status appeared before the last event or is absent from the last event",
        )
        check(
            "final_tick",
            final_state.get("logical_tick") == trace[-1].get("logical_tick"),
            "final logical tick differs from the last trace event",
        )
    state_body = dict(final_state)
    retained_state_hash = state_body.pop("state_hash", None)
    state_body.pop("trace_head", None)
    check("final_state_hash", retained_state_hash == digest(state_body), "final state hash mismatch")

    evidence_body = dict(evidence)
    retained_evidence_digest = evidence_body.pop("evidence_digest", None)
    check(
        "evidence_digest",
        retained_evidence_digest == digest(evidence_body),
        "evidence digest mismatch",
    )
    check(
        "evidence_final_state",
        evidence.get("final_state_hash") == final_state.get("state_hash"),
        "evidence does not bind the final state",
    )
    check(
        "evidence_trace",
        evidence.get("trace_head") == final_state.get("trace_head")
        and evidence.get("trace_digest") == digest(trace),
        "evidence does not bind the retained trace",
    )
    check(
        "evidence_identity",
        evidence.get("run_id") == final_state.get("run_id")
        and evidence.get("runtime_version") == final_state.get("runtime_version")
        and evidence.get("terminal_status") == final_state.get("halt_status")
        and evidence.get("event_count") == len(trace),
        "evidence identity, terminal status, or event count mismatch",
    )
    try:
        workspace = final_state["global_workspace"]
        commitment = final_state["commitment_state"]
        branches = sorted(final_state["branch_table"], key=lambda item: item["branch_id"])
        if not isinstance(workspace, Mapping) or not isinstance(commitment, Mapping):
            raise TypeError("workspace and commitment must be objects")
        query = workspace["query"]
        conclusion = commitment.get("conclusion")
        supported = (
            isinstance(conclusion, Mapping)
            and isinstance(query, Mapping)
            and _proposition_key(conclusion) == _proposition_key(query)
        )
        expected_proofs = [
            proof
            for branch in branches
            for proof in branch["proof_steps"]
        ]
        expected_branch_summary = [
            {
                "branch_id": branch["branch_id"],
                "candidate_id": branch["candidate_id"],
                "status": branch["status"],
                "assumptions": [_proposition_key(item) for item in branch["assumptions"]],
                "proposition_keys": [_proposition_key(item) for item in branch["propositions"]],
                "contradictions": list(branch["contradictions"]),
                "unknowns": list(branch["unknowns"]),
                "proof_step_ids": [item["step_id"] for item in branch["proof_steps"]],
            }
            for branch in branches
        ]
        rpm_events = [
            event
            for event in trace
            if any(
                intent.get("intent_type") in {"PUSH_RPM", "RETURN_RPM"}
                for intent in event.get("proposed_intents", [])
            )
        ]
        wrote_episode = any(
            intent.get("intent_type") == "WRITE_EPISODE"
            and intent.get("intent_id") in event.get("authorized_intent_ids", [])
            for event in trace
            for intent in event.get("proposed_intents", [])
        )
        expected_projection = {
            "runtime_version": final_state["runtime_version"],
            "run_id": final_state["run_id"],
            "problem_id": workspace["problem_id"],
            "goal_id": final_state["active_goal_id"],
            "seed": final_state["seed"],
            "initial_state_hash": trace[0]["pre_state_hash"],
            "final_state_hash": final_state["state_hash"],
            "trace_head": final_state["trace_head"],
            "trace_digest": digest(trace),
            "terminal_status": final_state["halt_status"],
            "query_result": {
                "query": query,
                "supported": supported,
                "conclusion": conclusion,
                "lacunae": list(workspace["lacunae"]),
            },
            "proof_steps": expected_proofs,
            "branch_summary": expected_branch_summary,
            "rpm_summary": {
                "event_count": len(rpm_events),
                "events": rpm_events,
                "final_depth": len(final_state["rpm_stack"]),
            },
            "comparison": list(workspace["comparison_reports"]),
            "commitment_gates": dict(commitment["gate_results"]),
            "learning_disposition": "EPISODIC_WRITE_ONLY" if wrote_episode else "NO_WRITE",
            "diagnostics": list(workspace["diagnostics"]),
            "event_count": len(trace),
            "claim_boundary": {
                "status": "REFERENCE_DEMONSTRATOR_ONLY",
                "production_ready": False,
                "general_intelligence_claim": False,
                "english_understanding": False,
                "external_model_used": False,
                "external_actions_enabled": False,
                "cas_ohm_runtime_authority": False,
                "procedural_learning_enabled": False,
                "constitutional_learning_enabled": False,
            },
        }
        projection_matches = all(evidence.get(key) == value for key, value in expected_projection.items())
        evidence_keys = {
            "schema_version",
            "runtime_version",
            "run_id",
            "problem_id",
            "goal_id",
            "seed",
            "problem_packet_hash",
            "initial_state_hash",
            "final_state_hash",
            "trace_head",
            "trace_digest",
            "terminal_status",
            "query_result",
            "proof_steps",
            "branch_summary",
            "rpm_summary",
            "comparison",
            "commitment_gates",
            "learning_disposition",
            "diagnostics",
            "event_count",
            "claim_boundary",
            "evidence_digest",
        }
        projection_matches = (
            projection_matches
            and set(evidence) == evidence_keys
            and evidence.get("schema_version") == "cncm.evidence/0.1"
            and _is_sha256(evidence.get("problem_packet_hash"))
        )
    except (KeyError, TypeError, ValueError):
        projection_matches = False
    check(
        "evidence_projection",
        projection_matches,
        "evidence semantic projection differs from final state or trace",
    )
    check(
        "summary_binding",
        summary.get("final_state_hash") == final_state.get("state_hash")
        and summary.get("trace_head") == final_state.get("trace_head")
        and summary.get("trace_digest") == digest(trace)
        and summary.get("evidence_digest") == retained_evidence_digest,
        "summary binding mismatch",
    )
    check(
        "summary_identity",
        summary.get("run_id") == final_state.get("run_id")
        and summary.get("terminal_status") == final_state.get("halt_status")
        and summary.get("logical_ticks") == final_state.get("logical_tick"),
        "summary identity, terminal status, or tick mismatch",
    )
    summary_keys = {
        "schema_version",
        "run_id",
        "problem_id",
        "terminal_status",
        "conclusion",
        "logical_ticks",
        "final_state_hash",
        "trace_head",
        "trace_digest",
        "evidence_digest",
    }
    workspace_for_summary = final_state.get("global_workspace")
    commitment_for_summary = final_state.get("commitment_state")
    summary_projection_valid = (
        isinstance(workspace_for_summary, Mapping)
        and isinstance(commitment_for_summary, Mapping)
        and set(summary) == summary_keys
        and summary.get("schema_version") == "cncm.run-summary/0.1"
        and summary.get("run_id") == final_state.get("run_id")
        and summary.get("problem_id") == workspace_for_summary.get("problem_id")
        and summary.get("terminal_status") == final_state.get("halt_status")
        and summary.get("conclusion") == commitment_for_summary.get("conclusion")
        and summary.get("logical_ticks") == final_state.get("logical_tick")
        and summary.get("final_state_hash") == final_state.get("state_hash")
        and summary.get("trace_head") == final_state.get("trace_head")
        and summary.get("trace_digest") == digest(trace)
        and summary.get("evidence_digest") == retained_evidence_digest
    )
    check(
        "summary_projection",
        summary_projection_valid,
        "summary projection differs from the final state, trace, or evidence",
    )
    terminal = final_state.get("halt_status")
    check(
        "typed_terminal",
        isinstance(terminal, str)
        and terminal in {item.value for item in TerminalStatus if item is not TerminalStatus.RUNNING},
        "final status is not a typed terminal state",
    )
    return VerificationReport(not errors, tuple(checks), tuple(errors))


def verify_bundle(bundle: Mapping[str, Any]) -> VerificationReport:
    """Fail-total wrapper for adversarial retained-artifact input."""
    try:
        return _verify_bundle_unchecked(bundle)
    except (AttributeError, ContractError, IndexError, KeyError, RecursionError, TypeError, ValueError) as exc:
        return VerificationReport(
            False,
            (("bundle_shape", False),),
            (f"bundle verification failed closed: {exc}",),
        )
