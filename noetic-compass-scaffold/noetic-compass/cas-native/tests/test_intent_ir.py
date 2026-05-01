from cas_native.intent import (
    AxisBinding,
    BuilderTarget,
    IntentIR,
    ProductionIngredientIntent,
    ProductionIntent,
    RegisterIntent,
    StateAtom,
    build_candidate_expressions,
)


def test_state_atom_renders_full_cas_literal():
    atom = StateAtom(noetic=2, domain="P", drive="F4", register="A")

    assert atom.to_cas() == "^2^P_{F4}|A"
    assert atom.validate() == []


def test_state_atom_allows_domainless_registered_state():
    atom = StateAtom(noetic=4, drive="F2", register="E")

    assert atom.to_cas() == "^4_{F2}|E"
    assert atom.validate() == []


def test_intent_model_input_uses_prompt_only():
    intent = IntentIR(
        id="intent-1",
        user_prompt="Translate the recoverable slots.",
        turn_type="ANSWER",
        expression_family="state",
        transition_kind="state",
        cas_expression_target="^2^P_{F4}|A",
        builder_targets=(
            BuilderTarget(
                family="state",
                builder="state_literal_builder",
                canonical_expression="^2^P_{F4}|A",
            ),
        ),
    )

    assert intent.model_input_text() == "Translate the recoverable slots."
    assert "^2^P_{F4}|A" not in intent.model_input_text()
    assert intent.validate() == []


def test_production_builder_uses_typed_ingredients():
    production = ProductionIntent(
        omega_target="Omega_focus",
        ingredients=(
            ProductionIngredientIntent(
                state=StateAtom(noetic=1, domain="C", drive="F2", register="A"),
                coefficient=0.6,
            ),
            ProductionIngredientIntent(
                state=StateAtom(noetic=7, domain="P", drive="F4", register="T"),
                coefficient=0.4,
            ),
        ),
    )
    intent = IntentIR(
        id="intent-prod",
        user_prompt="Build the focus recipe.",
        turn_type="ANSWER",
        expression_family="production",
        transition_kind="production",
        production=production,
        axis=AxisBinding(
            noetic=1,
            domain="C",
            drive="F2",
            register="A",
            states=tuple(ingredient.state for ingredient in production.ingredients),
        ),
    )

    candidates = build_candidate_expressions(intent)

    assert candidates == [
        "Theta(Omega_focus) = 0.6*^1^C_{F2}|A + 0.4*^7^P_{F4}|T -> Omega_focus"
    ]
    assert intent.validate() == []


def test_validation_rejects_bad_register_mode():
    intent = IntentIR(
        id="bad-register",
        user_prompt="Bad register test.",
        turn_type="ANSWER",
        expression_family="register_state",
        transition_kind="state",
        register_intent=RegisterIntent(mode="single", registers=("A", "T")),
    )

    assert "single register mode requires exactly one register" in intent.validate()
