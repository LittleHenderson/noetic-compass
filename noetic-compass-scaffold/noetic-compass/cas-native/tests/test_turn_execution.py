import pytest

from cas_native.intent import (
    AxisBinding,
    BuilderTarget,
    IntentIR,
    RegisterIntent,
    StateAtom,
)
from cas_native.runtime import (
    CASRuntimeFrame,
    CandidateTransition,
    DriveLevel,
    DriveState,
    FeedbackEvent,
    IdentityState,
    SaliencePolicy,
    execute_turn,
)


def _intent() -> IntentIR:
    state = StateAtom(noetic=4, domain="P", drive="F4", register="f")
    return IntentIR(
        id="intent-1",
        user_prompt="families: state expression; Noetic ^4; drive F4; register |f",
        turn_type="ANSWER",
        expression_family="register_state",
        transition_kind="state",
        axis=AxisBinding(
            noetic=4,
            domain="P",
            drive="F4",
            register="f",
            states=(state,),
        ),
        register_intent=RegisterIntent(mode="single", registers=("f",)),
        builder_targets=(
            BuilderTarget(
                family="register_state",
                builder="register_state_builder",
                canonical_expression="^4^P_{F4}|f",
            ),
        ),
    )


def _frame() -> CASRuntimeFrame:
    return CASRuntimeFrame(
        identity=IdentityState(agent_id="agent", continuity_key="stable-agent"),
        drive_state=DriveState(
            levels=(
                DriveLevel(drive="F4", activation=0.8, depletion=0.1, saturation=0.0),
                DriveLevel(drive="F2", activation=0.4, depletion=0.0, saturation=0.0),
            )
        ),
        salience_policy=SaliencePolicy(
            drive_weights={"F4": 2.0},
            register_weights={"f": 1.25},
        ),
    )


def test_execute_turn_ranks_candidates_and_records_selected_trace():
    record = execute_turn(
        runtime_frame=_frame(),
        intent=_intent(),
        candidates=(
            CandidateTransition(
                expression="^4^P_{F4}|f",
                compiler_validation={"compiler_valid": True},
                diagram_summary={"available": True, "node_count": 3},
                candidate_weight=1.0,
            ),
            CandidateTransition(
                expression="^4^P_{F4}|f + ^4^P_{F5}|A",
                compiler_validation={"compiler_valid": True},
                diagram_summary={"available": True, "node_count": 5},
                candidate_weight=2.0,
            ),
        ),
        rendered_response="This selects the richer co-presence candidate.",
        drive_depletion_step=0.05,
    )

    payload = record.to_dict()

    assert record.validate() == []
    assert record.selected_expression == "^4^P_{F4}|f + ^4^P_{F5}|A"
    assert [candidate.rank for candidate in record.admissible_candidates] == [1, 2]
    assert record.admissible_candidates[0].selected is True
    assert payload["runtime_frame_pre"]["identity"]["continuity_key"] == "stable-agent"
    assert payload["runtime_frame_post"]["identity"]["continuity_key"] == "stable-agent"
    assert payload["runtime_delta"]["identity_persisted"] is True
    assert payload["compiler_validation"]["compiler_valid"] is True
    assert payload["diagram_summary"]["node_count"] == 5


def test_execute_turn_filters_invalid_candidates_before_ranking():
    record = execute_turn(
        runtime_frame=_frame(),
        intent=_intent(),
        candidates=(
            CandidateTransition(
                expression="invalid-but-heavy",
                compiler_validation={"compiler_valid": False},
                candidate_weight=100.0,
            ),
            CandidateTransition(
                expression="^4^P_{F4}|f",
                compiler_validation={"compiler_valid": True},
                candidate_weight=1.0,
            ),
        ),
    )

    assert len(record.admissible_candidates) == 1
    assert record.selected_expression == "^4^P_{F4}|f"


def test_execute_turn_raises_when_no_admissible_candidates():
    with pytest.raises(ValueError, match="no admissible candidates"):
        execute_turn(
            runtime_frame=_frame(),
            intent=_intent(),
            candidates=(
                CandidateTransition(
                    expression="bad",
                    compiler_validation={"valid": False},
                ),
            ),
        )


def test_execute_turn_adds_drive_and_feedback_delta():
    feedback = FeedbackEvent(
        event_id="fb-1",
        action_id="turn-1",
        observation="user accepted the answer",
        outcome="connection improved",
        reward_signal=0.5,
    )

    record = execute_turn(
        runtime_frame=_frame(),
        intent=_intent(),
        candidates=("^4^P_{F4}|f",),
        feedback_event=feedback,
        drive_depletion_step=0.1,
    )
    delta = record.runtime_delta.to_dict()

    assert delta["feedback_added"] == ["fb-1"]
    assert delta["facts_added"] == ["last_family:register_state", "last_turn:state"]
    assert delta["drive_deltas"]["F4"]["depletion"] == pytest.approx(0.1)
    assert delta["drive_deltas"]["F4"]["effective_weight"] < 0
    assert "feedback_history" in delta["changed_paths"]
    assert "drive_state" in delta["changed_paths"]


def test_execute_turn_can_use_intent_builder_candidates_by_default():
    record = execute_turn(runtime_frame=_frame(), intent=_intent())

    assert record.selected_expression == "^4^P_{F4}|f"
    assert record.user_input == _intent().user_prompt
    assert record.predicted_intent_ir.model_input_text() == _intent().user_prompt
