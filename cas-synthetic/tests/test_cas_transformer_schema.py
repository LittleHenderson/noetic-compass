"""Tests for CAS Transformer turn/meta-logic schemas."""

from __future__ import annotations

from cas_synthetic.schemas.cas_transformer import (
    CASPerturbationExample,
    CASStateContext,
    CASTrace,
    CASTraceEdge,
    CASTraceNode,
    CASTransition,
    CASTurnRecord,
    DomainTransition,
    MetaLogicContext,
    MetaLogicObject,
    MetaLogicRelation,
    ProductionIngredient,
    ProductionModifier,
    ProductionTransition,
    RegisterBinding,
    validate_compound_transition,
)


def _smalltalk_context() -> MetaLogicContext:
    return MetaLogicContext(
        objects=[
            MetaLogicObject("t0", "trace_node", "TraceNode"),
            MetaLogicObject("TraceSet", "set", "TraceNode"),
            MetaLogicObject("response", "response", "Response"),
            MetaLogicObject("RenderedResponseSet", "set", "Response"),
        ],
        relations=[
            MetaLogicRelation("member", "t0", "TraceSet"),
            MetaLogicRelation("member", "response", "RenderedResponseSet"),
        ],
    )


def test_cas_turn_record_serializes_small_talk_as_cas_grounded_trace():
    context = _smalltalk_context()
    record = CASTurnRecord(
        id="cas-turn-001",
        prompt="hi",
        response="Hi. What would you like to work on?",
        cas_expression="^8^E_{F4}|f -> ^9^E_{F4}|f",
        trace=[
            CASTraceNode(
                node_id="t0",
                surface_span="Hi.",
                turn_type="OPEN",
                cas_state="^8^E_{F4}|f -> ^9^E_{F4}|f",
                role="attention_orientation",
                meta_logic_context=context,
                state_context=CASStateContext({"channel_idle"}),
            )
        ],
        meta_logic_context=context,
        compiler={"valid": True},
        perturbations=[
            CASPerturbationExample(
                perturbation_type="turn_type",
                corrupted_field="turn_type",
                corrupted_value="REFUSE",
                expected_effect="open greeting tokens should lose likelihood",
            )
        ],
    )

    assert record.validate() == []
    payload = record.to_dict()
    assert payload["trace"][0]["turn_type"] == "OPEN"
    assert payload["trace"][0]["meta_logic_context"]["relations"][0]["relation"] == "member"
    assert payload["perturbations"][0]["corrupted_value"] == "REFUSE"


def test_cas_turn_requires_trace_and_meta_logic_context():
    record = CASTurnRecord(
        id="bad-record",
        prompt="hi",
        response="Hi.",
        cas_expression="^8^E_{F4}|f",
        trace=[],
        meta_logic_context=MetaLogicContext(),
    )

    errors = record.validate()

    assert any("at least one trace node" in error for error in errors)
    assert any("meta_logic_context must include at least one object" in error for error in errors)
    assert any("meta_logic_context must include at least one relation" in error for error in errors)


def test_trace_node_rejects_missing_turn_type_precondition():
    node = CASTraceNode(
        node_id="t0",
        surface_span="Could you clarify?",
        turn_type="CLARIFY",
        cas_state="^3^C_{F2}|A -> ^2^C_{F6}|A",
        role="missing_constraint_request",
        meta_logic_context=_smalltalk_context(),
        state_context=CASStateContext({"input_received"}),
    )

    errors = node.validate()

    assert any("missing admissibility precondition" in error for error in errors)
    assert any("lacunarity_detected" in error for error in errors)


def test_meta_logic_rejects_instance_category_carrier_mismatch():
    context = MetaLogicContext(
        objects=[
            MetaLogicObject("^2", "element", "Noetic"),
            MetaLogicObject("States", "carrier", "State"),
        ],
        relations=[MetaLogicRelation("member", "^2", "States")],
    )

    errors = context.validate()

    assert any("carrier mismatch" in error for error in errors)


def test_meta_logic_blocks_user_request_promoting_to_system_instruction():
    context = MetaLogicContext(
        objects=[
            MetaLogicObject("UserRequestSet", "set", "UserUtterance"),
            MetaLogicObject("SystemInstructionSet", "set", "Instruction"),
        ],
        relations=[
            MetaLogicRelation("licenses", "UserRequestSet", "SystemInstructionSet")
        ],
    )

    errors = context.validate()

    assert any("authority promotion blocked" in error for error in errors)


def test_meta_logic_accepts_tool_observation_to_evidence_to_validated_claim():
    context = MetaLogicContext(
        objects=[
            MetaLogicObject("ToolObservationSet", "set", "ToolObservation"),
            MetaLogicObject("EvidenceSet", "set", "Evidence"),
            MetaLogicObject("ValidatedClaimSet", "set", "Claim"),
        ],
        relations=[
            MetaLogicRelation("licenses", "ToolObservationSet", "EvidenceSet"),
            MetaLogicRelation("licenses", "EvidenceSet", "ValidatedClaimSet"),
        ],
    )

    assert context.validate() == []


def test_production_transition_computes_limiting_reagent_and_yield():
    transition = ProductionTransition(
        omega_target="Omega_safe_judgment",
        ingredients=[
            ProductionIngredient("^3^P_{F2}|A", coefficient=2.0, available=3.0),
            ProductionIngredient("^2^C_{F2}|f", coefficient=1.0, available=1.0),
        ],
        limiting_reagent="^2^C_{F2}|f",
        theoretical_yield=1.0,
        leakage=0.05,
    )

    assert transition.validate() == []


def test_production_transition_rejects_wrong_limiter():
    transition = ProductionTransition(
        omega_target="Omega_safe_judgment",
        ingredients=[
            ProductionIngredient("^3^P_{F2}|A", coefficient=2.0, available=3.0),
            ProductionIngredient("^2^C_{F2}|f", coefficient=1.0, available=1.0),
        ],
        limiting_reagent="^3^P_{F2}|A",
        theoretical_yield=1.5,
    )

    errors = transition.validate()

    assert any("limiting_reagent mismatch" in error for error in errors)
    assert any("theoretical_yield mismatch" in error for error in errors)


def test_register_integration_requires_omega_target():
    binding = RegisterBinding(mode="integration", registers=("A", "f", "T"))

    errors = binding.validate()

    assert any("requires omega_target" in error for error in errors)


def test_register_co_presence_rejects_named_emergent():
    binding = RegisterBinding(
        mode="co_presence",
        registers=("A", "f"),
        omega_target="Omega_presence",
    )

    errors = binding.validate()

    assert any("co_presence must not name" in error for error in errors)


def test_domain_feedback_requires_o_to_p_license():
    transition = DomainTransition(
        source_domain="O",
        target_domain="P",
        transition_type="feedback",
    )

    errors = transition.validate()

    assert any("requires feedback_license" in error for error in errors)


def test_cast_transition_validates_nested_typed_components():
    transition = CASTransition(
        kind="production",
        register_binding=RegisterBinding(
            mode="integration",
            registers=("A", "f"),
            omega_target="Omega_resolve",
        ),
        production=ProductionTransition(
            omega_target="Omega_resolve",
            ingredients=[
                ProductionIngredient("^5^C_{F6}|A", coefficient=1.0, available=2.0),
                ProductionIngredient("^7^O_{F5}|f", coefficient=2.0, available=4.0),
            ],
            limiting_reagent="^5^C_{F6}|A",
            theoretical_yield=2.0,
        ),
        domain_transition=DomainTransition(
            source_domain="C",
            target_domain="O",
            transition_type="descent",
        ),
    )

    assert transition.validate() == []


def test_shell_turn_downgrades_production_error_to_warning():
    node = CASTraceNode(
        node_id="t0",
        surface_span="Here is a plan.",
        turn_type="PLAN",
        cas_state="^6^C_{F6}|A -> ^9^O_{F5}|A",
        role="planning",
        meta_logic_context=_smalltalk_context(),
        state_context=CASStateContext({"task_active"}),
        transition=CASTransition(
            kind="production",
            production=ProductionTransition(
                omega_target="Omega_plan",
                ingredients=[
                    ProductionIngredient("^6^C_{F6}|A", coefficient=2.0, available=1.0)
                ],
                limiting_reagent="wrong",
                theoretical_yield=99.0,
            ),
        ),
    )

    diagnostics = node.transition_diagnostics()

    assert node.validate() == []
    assert any(diagnostic.severity == "warning" for diagnostic in diagnostics)
    assert any("limiting_reagent mismatch" in diagnostic.message for diagnostic in diagnostics)


def test_tight_turn_treats_production_error_as_validation_error():
    node = CASTraceNode(
        node_id="t0",
        surface_span="This answer depends on a recipe.",
        turn_type="ANSWER",
        cas_state="^6^C_{F6}|A -> ^9^O_{F5}|A",
        role="structured_answer",
        meta_logic_context=_smalltalk_context(),
        state_context=CASStateContext({"task_active", "claim_supported"}),
        transition=CASTransition(
            kind="production",
            production=ProductionTransition(
                omega_target="Omega_answer",
                ingredients=[
                    ProductionIngredient("^6^C_{F6}|A", coefficient=2.0, available=1.0)
                ],
                limiting_reagent="wrong",
                theoretical_yield=99.0,
            ),
        ),
    )

    errors = node.validate()

    assert any("limiting_reagent mismatch" in error for error in errors)


def test_production_modifier_cannot_also_be_ingredient():
    transition = ProductionTransition(
        omega_target="Omega_refusal",
        ingredients=[
            ProductionIngredient("^4^E_{F4}|f", coefficient=1.0, available=2.0)
        ],
        limiting_reagent="^4^E_{F4}|f",
        theoretical_yield=2.0,
        modifiers=[
            ProductionModifier(
                kind="catalyst",
                primitive="^4^E_{F4}|f",
                scale=1.2,
            )
        ],
    )

    errors = transition.validate()

    assert any("cannot also be an ingredient" in error for error in errors)


def test_production_modifier_accepts_non_consumed_cas_primitive():
    transition = ProductionTransition(
        omega_target="Omega_refusal",
        ingredients=[
            ProductionIngredient("^6^P_{F2}|A", coefficient=1.0, available=2.0)
        ],
        limiting_reagent="^6^P_{F2}|A",
        theoretical_yield=2.0,
        modifiers=[
            ProductionModifier(
                kind="catalyst",
                primitive="^4^E_{F4}|f",
                scale=1.2,
            ),
            ProductionModifier(
                kind="inhibitor",
                primitive="Omega_distraction",
                scale=0.8,
            ),
        ],
    )

    assert transition.validate() == []


def test_trace_query_engine_indexes_turns_domains_and_predecessors():
    context = _smalltalk_context()
    open_node = CASTraceNode(
        node_id="t0",
        surface_span="Hi.",
        turn_type="OPEN",
        cas_state="^8^E_{F4}|f -> ^9^E_{F4}|f",
        role="attention_orientation",
        meta_logic_context=context,
        state_context=CASStateContext({"channel_idle"}),
        transition=CASTransition(
            kind="surface_act",
            domain_transition=DomainTransition("E", "O"),
        ),
    )
    answer_node = CASTraceNode(
        node_id="t1",
        surface_span="Here is the answer.",
        turn_type="ANSWER",
        cas_state="^6^C_{F6}|A -> ^9^O_{F5}|A",
        role="structured_answer",
        meta_logic_context=context,
        state_context=CASStateContext({"task_active", "claim_supported"}),
        transition=CASTransition(
            kind="state",
            domain_transition=DomainTransition("C", "O"),
        ),
    )
    trace = CASTrace(
        nodes=[open_node, answer_node],
        edges=[CASTraceEdge("t0", "t1", "depends_on")],
    )

    query = trace.query()

    assert trace.validate() == []
    assert query.nodes_for_turn_type("ANSWER") == [answer_node]
    assert query.latest_by_domain("O") == answer_node
    assert query.predecessors("t1", relation="depends_on") == [open_node]


def test_trace_query_engine_detects_feedback_license():
    context = _smalltalk_context()
    reflection = CASTraceNode(
        node_id="t0",
        surface_span="Observed outcome revises the principle.",
        turn_type="REPAIR",
        cas_state="^9^O_{F5}|A -> ^2^P_{F2}|A",
        role="feedback_license",
        meta_logic_context=context,
        state_context=CASStateContext({"prior_error_detected"}),
    )
    feedback = CASTraceNode(
        node_id="t1",
        surface_span="So the principle should be updated.",
        turn_type="ANSWER",
        cas_state="^9^O_{F5}|A -> ^2^P_{F2}|A",
        role="licensed_feedback",
        meta_logic_context=context,
        state_context=CASStateContext({"task_active", "claim_supported"}),
        transition=CASTransition(
            kind="state",
            domain_transition=DomainTransition(
                "O",
                "P",
                transition_type="feedback",
                feedback_license="t0",
            ),
        ),
    )
    trace = CASTrace(
        nodes=[reflection, feedback],
        edges=[CASTraceEdge("t0", "t1", "licenses")],
    )

    assert trace.validate() == []
    assert trace.query().has_feedback_license("t1")


def test_validate_compound_transition_returns_structured_diagnostics():
    context = _smalltalk_context()
    bad_node = CASTraceNode(
        node_id="t0",
        surface_span="Could you clarify?",
        turn_type="CLARIFY",
        cas_state="^3^C_{F2}|A -> ^2^C_{F6}|A",
        role="missing_constraint_request",
        meta_logic_context=context,
        state_context=CASStateContext({"input_received"}),
    )
    trace = CASTrace(nodes=[bad_node])

    diagnostics = validate_compound_transition(trace)

    assert any(diagnostic.phase == "structural" for diagnostic in diagnostics)
    assert any("lacunarity_detected" in diagnostic.message for diagnostic in diagnostics)
    assert all(diagnostic.fixable for diagnostic in diagnostics)


def test_trace_cycle_is_invalid():
    context = _smalltalk_context()
    first = CASTraceNode(
        node_id="t0",
        surface_span="Hi.",
        turn_type="OPEN",
        cas_state="^8^E_{F4}|f",
        role="open",
        meta_logic_context=context,
        state_context=CASStateContext({"channel_idle"}),
    )
    second = CASTraceNode(
        node_id="t1",
        surface_span="Understood.",
        turn_type="ACK",
        cas_state="^9^C_{F6}|A",
        role="ack",
        meta_logic_context=context,
        state_context=CASStateContext({"input_received"}),
    )
    trace = CASTrace(
        nodes=[first, second],
        edges=[
            CASTraceEdge("t0", "t1", "depends_on"),
            CASTraceEdge("t1", "t0", "depends_on"),
        ],
    )

    assert any("cycle" in error for error in trace.validate())
