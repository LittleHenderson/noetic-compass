from cas_native.intent import (
    AmbiguityOption,
    AxisBinding,
    IntentIR,
    RegisterIntent,
    StateAtom,
)
from cas_native.runtime import (
    AffectState,
    AmbiguityState,
    CASRuntimeFrame,
    DefaultStateDistribution,
    DriveLevel,
    DriveState,
    FeedbackEvent,
    FeedbackHistory,
    IdentityState,
    SaliencePolicy,
    TemporalGrain,
)


def _intent(
    *,
    intent_id: str,
    drive: str,
    register: str,
    family: str = "register_state",
) -> IntentIR:
    state = StateAtom(noetic=4, domain="P", drive=drive, register=register)
    return IntentIR(
        id=intent_id,
        user_prompt=f"recover {drive} {register}",
        turn_type="ANSWER",
        expression_family=family,
        transition_kind="state",
        axis=AxisBinding(
            noetic=state.noetic,
            domain=state.domain,
            drive=state.drive,
            register=state.register,
            states=(state,),
        ),
        register_intent=RegisterIntent(mode="single", registers=(register,)),
    )


def test_runtime_frame_validates_continuity_and_serializes():
    frame = CASRuntimeFrame(
        identity=IdentityState(
            agent_id="cas-native-alpha",
            continuity_key="identity-root-001",
            session_id="session-1",
            persistent_tags=("auditable", "runtime"),
        ),
        temporal_grain=TemporalGrain(name="deliberation", min_ms=5_000, max_ms=60_000),
        default_state_distribution=DefaultStateDistribution(
            weights={"^4^P_{F4}|f": 0.7, "^6^C_{F6}|A": 0.3}
        ),
    )

    payload = frame.to_dict()

    assert frame.validate() == []
    assert payload["schema_version"] == "cas_runtime_frame.v1"
    assert payload["identity"]["continuity_key"] == "identity-root-001"
    assert payload["default_state_distribution"]["normalized"]["^4^P_{F4}|f"] == 0.7


def test_drive_dynamics_reduce_salience_when_depleted():
    active = DriveLevel(drive="F4", activation=0.9, depletion=0.0, saturation=0.0)
    depleted = DriveLevel(drive="F4", activation=0.9, depletion=0.8, saturation=0.0)

    assert active.effective_weight() > depleted.effective_weight()
    assert depleted.effective_weight() == 0.17999999999999997


def test_salience_policy_explains_why_one_intent_fires():
    frame = CASRuntimeFrame(
        identity=IdentityState(agent_id="agent", continuity_key="same-agent"),
        drive_state=DriveState(
            levels=(
                DriveLevel(drive="F4", activation=0.9, depletion=0.0, saturation=0.0),
                DriveLevel(drive="F2", activation=0.3, depletion=0.0, saturation=0.0),
            )
        ),
        salience_policy=SaliencePolicy(
            drive_weights={"F4": 2.0, "F2": 0.5},
            register_weights={"f": 1.5, "A": 0.8},
            domain_weights={"P": 1.1},
        ),
        affect_state=AffectState(affect_type="care", valence=0.4, arousal=0.8, register_bias="f"),
    )

    connection = frame.score_intent(_intent(intent_id="connection", drive="F4", register="f"))
    control = frame.score_intent(_intent(intent_id="control", drive="F2", register="A"))

    assert connection.score > control.score
    assert connection.components["drive_policy"] == 2.0
    assert connection.components["drive_runtime"] == 0.9
    assert connection.components["affect"] == 1.2
    assert connection.selected_drive == "F4"
    assert connection.selected_register == "f"


def test_ambiguity_can_be_held_or_force_clarification():
    held = AmbiguityState(
        options=(
            AmbiguityOption(
                path="axis.drive",
                candidates=("F3", "F4"),
                reason="prompt names growth and connection",
                confidence=0.6,
            ),
        ),
        policy="hold_until_context",
        clarification_threshold=0.75,
    )
    urgent = AmbiguityState(options=held.options, policy="clarify_now")

    assert held.should_clarify() is False
    assert held.penalty() < 1.0
    assert urgent.should_clarify() is True
    assert held.validate() == []


def test_transition_trace_records_salience_identity_feedback_and_diagram():
    intent = _intent(intent_id="intent-1", drive="F4", register="f")
    feedback = FeedbackEvent(
        event_id="feedback-1",
        action_id="prior-action",
        observation="user accepted the explanation",
        outcome="support increased",
        reward_signal=0.6,
    )
    frame = CASRuntimeFrame(
        identity=IdentityState(agent_id="agent", continuity_key="identity-stable"),
        feedback_history=FeedbackHistory(events=(feedback,)),
        salience_policy=SaliencePolicy(drive_weights={"F4": 1.5}, register_weights={"f": 1.2}),
    )

    trace = frame.trace_transition(
        intent,
        "^4^P_{F4}|f",
        validation={"compiler_valid": True},
        diagram_summary={"available": True, "node_count": 3},
    )
    payload = trace.to_dict()

    assert trace.validate() == []
    assert payload["identity"]["continuity_key"] == "identity-stable"
    assert payload["feedback_refs"] == ["feedback-1"]
    assert payload["validation"]["compiler_valid"] is True
    assert payload["diagram_summary"]["node_count"] == 3
    assert payload["salience"]["components"]["drive_policy"] == 1.5
