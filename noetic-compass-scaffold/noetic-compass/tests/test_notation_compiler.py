"""Tests for the executable CAS notation compiler."""

from pathlib import Path
import shutil
import uuid

from api.notation.compiler import (
    RegisterActivation,
    VALID_REGISTERS,
    compile_expression,
    compile_file,
    extract_register_activations,
)


def _local_tmp_dir() -> Path:
    base = Path("_tmp_lang_tests").resolve()
    base.mkdir(exist_ok=True)
    path = base / f"cas_lang_{uuid.uuid4().hex}"
    path.mkdir()
    return path


def test_compile_transition_expression():
    artifact = compile_expression("(CO-2^C_{F2} * CO-4^C_{F2}) -> CO-5^E_{F4}")
    assert artifact.valid
    assert artifact.type_info is not None
    assert artifact.type_info.kind.value == "relation"
    assert artifact.result is not None
    result = artifact.to_dict()["result"]
    assert result["kind"] == "relation"
    assert result["relation"] == "dependency"
    assert result["domain_descent_ok"] is True
    assert result["admissible"] is True
    opcodes = [ins.opcode for ins in artifact.bytecode]
    assert opcodes == ["PUSH_STATE", "PUSH_STATE", "TIMES", "PUSH_STATE", "ARROW"]


def test_invalid_domain_descent_rejected():
    artifact = compile_expression("CO-5^E_{F4} -> CO-2^C_{F2}")
    assert not artifact.valid
    assert artifact.error is not None
    assert "domain descent violated" in artifact.error


def test_invalid_operator_range_rejected():
    artifact = compile_expression("CO-11^P_{F1}")
    assert not artifact.valid
    assert artifact.error is not None
    assert "operator index must be 0-9" in artifact.error


def test_rpm_drive_expression_executes():
    artifact = compile_expression("RPM(F5)")
    assert artifact.valid
    result = artifact.to_dict()["result"]
    assert result["kind"] == "rpm"
    assert result["drive"] == "F5"
    assert result["completeness"] == 1.0


def test_fractal_expression_executes():
    artifact = compile_expression("Phi<2:5:8:3:9>")
    assert artifact.valid
    result = artifact.to_dict()["result"]
    assert result["kind"] == "fractal"
    assert result["sequence"] == [2, 5, 8, 3, 9]
    assert result["composed_operator"].startswith("CO-")


def test_co0_transition_uses_admissibility_rule():
    artifact = compile_expression("CO-0^P -> CO-0^C")
    assert artifact.valid
    result = artifact.to_dict()["result"]
    assert result["kind"] == "relation"
    assert result["domain_descent_ok"] is True
    assert result["admissible"] is False


def test_shorthand_state_reference_executes():
    artifact = compile_expression("P3 -> C3")
    assert artifact.valid
    result = artifact.to_dict()["result"]
    assert result["kind"] == "relation"
    assert result["source"]["dominant_state"] == "P3"
    assert result["target"]["dominant_state"] == "C3"


def test_circ_builds_fractal_sequence():
    artifact = compile_expression("CO-8^C ∘ CO-3^C")
    assert artifact.valid
    result = artifact.to_dict()["result"]
    assert result["kind"] == "fractal"
    assert result["sequence"] == [8, 3]
    assert result["domain"] == "C"


def test_multi_statement_program_executes():
    artifact = compile_expression("P0 -> C0; RPM(F5); Phi<2:5:8:3:9>")
    assert artifact.valid
    result = artifact.to_dict()["result"]
    assert result["kind"] == "program"
    assert len(result["results"]) == 3
    assert result["results"][0]["kind"] == "relation"
    assert result["results"][1]["kind"] == "rpm"
    assert result["final_result"]["kind"] == "fractal"


def test_let_binding_and_function_call_execute():
    artifact = compile_expression(
        "let start = CO-2^C_{F2}; fn bridge(x, y) = x -> y; bridge(start, CO-5^E_{F4})"
    )
    assert artifact.valid
    result = artifact.to_dict()["result"]
    assert result["kind"] == "program"
    assert result["results"][0]["kind"] == "binding"
    assert result["results"][1]["kind"] == "function"
    assert result["final_result"]["kind"] == "relation"


def test_builtin_function_call_executes():
    artifact = compile_expression("dominant_operator(CO-8^C)")
    assert artifact.valid
    assert artifact.to_dict()["result"] == "CO-8"


def test_typed_binding_rejects_wrong_type():
    artifact = compile_expression('let label: state[C] = "hello"; label')
    assert not artifact.valid
    assert artifact.error is not None
    assert "binding label" in artifact.error


def test_typed_function_contract_executes():
    artifact = compile_expression(
        "fn bridge(x: state[C], y: state[E]): relation = x -> y; bridge(C2, E5)"
    )
    assert artifact.valid
    result = artifact.to_dict()["result"]
    assert result["kind"] == "program"
    assert result["final_result"]["kind"] == "relation"


def test_typed_function_rejects_wrong_domain_argument():
    artifact = compile_expression(
        "fn bridge(x: state[C], y: state[E]): relation = x -> y; bridge(P2, E5)"
    )
    assert not artifact.valid
    assert artifact.error is not None
    assert "function bridge argument 1" in artifact.error


def test_use_statement_imports_module():
    tmp_dir = _local_tmp_dir()
    try:
        helper = tmp_dir / "helper.cas"
        helper.write_text("let base = CO-2^C_{F2}; fn lift(x) = x -> CO-5^E_{F4}", encoding="utf-8")
        main = tmp_dir / "main.cas"
        main.write_text(f'use "{helper.name}"; lift(base)', encoding="utf-8")

        artifact = compile_file(str(main))
        assert artifact.valid
        result = artifact.to_dict()["result"]
        assert result["kind"] == "program"
        assert result["results"][0]["kind"] == "module"
        assert result["final_result"]["kind"] == "relation"
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_cyclic_import_rejected():
    tmp_dir = _local_tmp_dir()
    try:
        a = tmp_dir / "a.cas"
        b = tmp_dir / "b.cas"
        a.write_text(f'use "{b.name}"', encoding="utf-8")
        b.write_text(f'use "{a.name}"', encoding="utf-8")

        artifact = compile_file(str(a))
        assert not artifact.valid
        assert artifact.error is not None
        assert "cyclic import detected" in artifact.error
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_export_limits_imported_surface():
    tmp_dir = _local_tmp_dir()
    try:
        helper = tmp_dir / "helper.cas"
        helper.write_text(
            'export let base: state[C] = CO-2^C_{F2}; fn hidden(x: state[C]): relation = x -> CO-5^E_{F4}',
            encoding="utf-8",
        )
        main = tmp_dir / "main.cas"
        main.write_text(f'use "{helper.name}"; hidden(base)', encoding="utf-8")

        artifact = compile_file(str(main))
        assert not artifact.valid
        assert artifact.error is not None
        assert "undefined function hidden" in artifact.error
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_exported_symbols_survive_cached_reimport():
    tmp_dir = _local_tmp_dir()
    try:
        helper = tmp_dir / "helper.cas"
        helper.write_text(
            'export let base: state[C] = CO-2^C_{F2}; export fn bridge(x: state[C], y: state[E]): relation = x -> y',
            encoding="utf-8",
        )
        artifact = compile_expression(
            f'use "{helper}"; use "{helper}"; bridge(base, E5)'
        )
        assert artifact.valid
        result = artifact.to_dict()["result"]
        assert result["kind"] == "program"
        assert result["results"][0]["kind"] == "module"
        assert result["results"][1]["kind"] == "module"
        assert result["final_result"]["kind"] == "relation"
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_showcase_program_executes():
    artifact = compile_file(str(Path("docs/CAS_SHOWCASE_APP.cas").resolve()))
    assert artifact.valid
    result = artifact.to_dict()["result"]
    assert result["kind"] == "program"
    assert result["results"][0]["kind"] == "module"
    assert result["results"][1]["kind"] == "binding"
    assert result["results"][2]["kind"] == "binding"
    assert result["results"][3]["kind"] == "binding"
    assert result["results"][4]["kind"] == "binding"
    assert result["results"][5]["kind"] == "function"
    assert result["final_result"]["kind"] == "relation"


# ---------------------------------------------------------------------------
# CAS v7.5 Phenomenological Register tests (Clarification 8).
#
# These cover the optional `|R` register suffix on Noetic primitives, Drive
# primitives, and compound-state expressions. Register is OPTIONAL: expressions
# without `|R` remain valid and register-neutral (v7.4-compatible).
# ---------------------------------------------------------------------------


def test_v75_register_at_noetic_level():
    """(a) `^2|T` attaches the Transcendent register to a Noetic primitive."""
    artifact = compile_expression("^2|T")
    assert artifact.valid, artifact.error
    result = artifact.to_dict()["result"]
    assert result["kind"] == "state"
    assert result["dominant_operator"] == "CO-2"
    assert result["register"] == "T"
    assert result["register_name"] == "Transcendent"


def test_v75_register_at_drive_level():
    """(b) `F_2|A` attaches the Analytical register to a Drive primitive.

    The underscore form `F_n` is the CAS v7.5 Section 3 notation; the parser
    also accepts the legacy `Fn` form for backward compatibility.
    """
    artifact = compile_expression("F_2|A")
    assert artifact.valid, artifact.error
    result = artifact.to_dict()["result"]
    assert result["kind"] == "drive"
    assert result["drive"] == "F2"
    assert result["register"] == "A"
    assert result["register_name"] == "Analytical"


def test_v75_register_at_compound_level():
    """(c) `^6^C_{F2}|A` attaches register to the whole compound state."""
    artifact = compile_expression("^6^C_{F2}|A")
    assert artifact.valid, artifact.error
    result = artifact.to_dict()["result"]
    assert result["kind"] == "state"
    assert result["dominant_state"] == "C6"
    assert result["dominant_drive"] == "F2"
    assert result["register"] == "A"


def test_v75_independent_registers_on_noetic_and_drive():
    """(d) `^2|T^C_{F2|A}` specifies independent Noetic and Drive registers."""
    artifact = compile_expression("^2|T^C_{F2|A}")
    assert artifact.valid, artifact.error
    result = artifact.to_dict()["result"]
    assert result["kind"] == "state"
    assert result["dominant_state"] == "C2"
    assert result["dominant_drive"] == "F2"
    # Noetic-level register preserved on `register`; Drive-level register
    # preserved independently on `drive_register`.
    assert result["register"] == "T"
    assert result["drive_register"] == "A"


def test_v75_invalid_register_rejected():
    """(e) `^2|Q` fails with a CAS v7.5 error listing the valid register set."""
    artifact = compile_expression("^2|Q")
    assert not artifact.valid
    assert artifact.error is not None
    assert "CAS v7.5" in artifact.error
    assert "T" in artifact.error and "A" in artifact.error
    assert "f" in artifact.error and "E" in artifact.error
    assert "'Q'" in artifact.error or "Q" in artifact.error


def test_v75_register_neutral_backward_compatible():
    """(f) `^2^C_{F2}` parses as a v7.4-compatible register-neutral state.

    The resulting state dict must NOT carry register keys, so downstream
    consumers written against CAS v7.4 are unaffected.
    """
    artifact = compile_expression("^2^C_{F2}")
    assert artifact.valid, artifact.error
    result = artifact.to_dict()["result"]
    assert result["kind"] == "state"
    assert result["dominant_state"] == "C2"
    assert result["dominant_drive"] == "F2"
    assert "register" not in result
    assert "drive_register" not in result


def test_v75_lowercase_f_affective_register_accepted():
    """(g) `^3|f` accepts lowercase `f` as the authoritative Affective register.

    Per Clarification 8, lowercase f is the authoritative token for the
    Affective register (capital F would collide with the Drive primitive
    notation F_k).
    """
    artifact = compile_expression("^3|f")
    assert artifact.valid, artifact.error
    result = artifact.to_dict()["result"]
    assert result["kind"] == "state"
    assert result["dominant_operator"] == "CO-3"
    assert result["register"] == "f"
    assert result["register_name"] == "Affective"


def test_v75_uppercase_F_affective_rejected():
    """Uppercase `F` is NOT accepted as the Affective register.

    `|F` would be ambiguous with the Drive primitive letter F, and the
    authoritative specification per Clarification 8 uses lowercase `f`.
    """
    artifact = compile_expression("^3|F")
    assert not artifact.valid
    assert artifact.error is not None
    assert "CAS v7.5" in artifact.error


def test_v75_register_on_co_notation_also_supported():
    """Register attaches to canonical `CO-n` notation as well as `^n` shorthand.

    This keeps existing `CO-n`-style call sites forward-compatible with
    v7.5 without forcing a rewrite to `^n`.
    """
    artifact = compile_expression("CO-2^P_{F2}|T")
    assert artifact.valid, artifact.error
    result = artifact.to_dict()["result"]
    assert result["kind"] == "state"
    assert result["dominant_state"] == "P2"
    assert result["register"] == "T"


def test_v75_register_neutral_co_notation_unchanged():
    """Existing `CO-n^D_{Fk}` expressions without register behave exactly as
    they did under CAS v7.4 (no new fields appear on the state dict)."""
    artifact = compile_expression("CO-5^E_{F4}")
    assert artifact.valid, artifact.error
    result = artifact.to_dict()["result"]
    assert result["kind"] == "state"
    assert result["dominant_state"] == "E5"
    assert "register" not in result
    assert "drive_register" not in result


def test_v75_all_four_registers_accepted():
    """All four register values {T, A, f, E} are accepted on a Noetic."""
    expected = {"T": "Transcendent", "A": "Analytical", "f": "Affective", "E": "Embodied"}
    for token, name in expected.items():
        artifact = compile_expression(f"^4|{token}")
        assert artifact.valid, f"register |{token} should be valid: {artifact.error}"
        result = artifact.to_dict()["result"]
        assert result["register"] == token
        assert result["register_name"] == name


# ---------------------------------------------------------------------------
# CAS v7.6 Stoichiometric Production Semantics tests (Clarification 9).
#
# Recipe notation, production-target literals, state-vector literals, yield
# queries, leakage annotations, and catalyst/inhibitor conditions are an
# additive grammar extension over v7.5. The compiler parses recipe SYNTAX
# only; yield calculation, limiting-reagent analysis, and efficiency
# computation are Rust cas-engine responsibilities.
#
# Both ASCII aliases (Theta, Omega, Lambda, kappa, iota, eta) and Unicode
# forms (Θ, Ω, Λ, κ, ι, η) are accepted; the
# middle dot · is accepted wherever `*` is. Tests cover both families
# so notation authors can use whichever is convenient.
# ---------------------------------------------------------------------------


def test_v76_basic_recipe_parses():
    """Basic recipe: `Θ(Ω_book) = 2·F_2 + 3·F_3 → Ω_book` (ASCII form)."""
    artifact = compile_expression(
        "Theta(Omega_book) = 2*F_2 + 3*F_3 -> Omega_book"
    )
    assert artifact.valid, artifact.error
    result = artifact.to_dict()["result"]
    assert result["kind"] == "recipe"
    assert result["target"] == "book"
    assert len(result["prerequisites"]) == 2
    coeffs = [p["coefficient"] for p in result["prerequisites"]]
    assert coeffs == [2.0, 3.0]
    drives = [p["primitive"]["drive"] for p in result["prerequisites"]]
    assert drives == ["F2", "F3"]
    assert result["leakages"] == []
    assert result["catalysts"] == []
    assert result["inhibitors"] == []


def test_v76_basic_recipe_unicode_form_parses():
    """The authoritative Unicode form `Θ(Ω_book) = 2·F_2 → Ω_book` parses.

    Middle dot `·` is accepted as a coefficient separator (equivalent
    to `*`/`×`); Greek capital letters Theta and Omega are accepted
    as first-class tokens alongside their ASCII aliases.
    """
    artifact = compile_expression(
        "Θ(Ω_book) = 2·F_2 + 3·F_3 → Ω_book"
    )
    assert artifact.valid, artifact.error
    result = artifact.to_dict()["result"]
    assert result["kind"] == "recipe"
    assert result["target"] == "book"
    coeffs = [p["coefficient"] for p in result["prerequisites"]]
    assert coeffs == [2.0, 3.0]


def test_v76_recipe_with_register_annotated_prerequisites():
    """Recipe prerequisites may carry v7.5 Register annotations.

    `Θ(Ω_paper) = 3·F_2^C|A + 2·F_2^C|T → Ω_paper` — each prereq is a
    full compound CAS state with its own register. The compiler reuses
    the v7.5 parser path for each primitive.
    """
    artifact = compile_expression(
        "Theta(Omega_paper) = 3*F_2^C|A + 2*F_2^C|T -> Omega_paper"
    )
    assert artifact.valid, artifact.error
    result = artifact.to_dict()["result"]
    assert result["kind"] == "recipe"
    assert result["target"] == "paper"
    prereqs = result["prerequisites"]
    assert len(prereqs) == 2
    # Each prereq primitive is a compound state carrying a register.
    # The actual primitive shape is internal; what we verify is that the
    # registers survived parsing into the AST.
    import json as _json
    serialized = _json.dumps(prereqs)
    assert '"register": "A"' in serialized
    assert '"register": "T"' in serialized


def test_v76_state_vector_literal_parses():
    """State vector: `S = {F_2: 7, F_3: 5, ^5^C: 4}` parses to entries."""
    artifact = compile_expression("S = {F_2: 7, F_3: 5, ^5^C: 4}")
    assert artifact.valid, artifact.error
    result = artifact.to_dict()["result"]
    assert result["kind"] == "state_vector"
    entries = result["entries"]
    assert len(entries) == 3
    assert entries[0]["activation"] == 7.0
    assert entries[1]["activation"] == 5.0
    assert entries[2]["activation"] == 4.0
    assert entries[0]["primitive"]["drive"] == "F2"
    assert entries[1]["primitive"]["drive"] == "F3"
    # Third entry is a compound state `^5^C`; its AST shape exposes the
    # domain and operator.
    assert entries[2]["primitive"]["operator"] == "CO-5"
    assert entries[2]["primitive"]["domain"] == "C"


def test_v76_theoretical_yield_expression_parses():
    """`Y_T(Ω_book | S, Θ)` parses to a YieldExpression with kind='theoretical'."""
    # Simple `Y_T(Ω_book)` form -- the full three-argument form with `|`
    # separators is tested separately; here we confirm the bare query.
    artifact = compile_expression("Y_T(Omega_book)")
    assert artifact.valid, artifact.error
    result = artifact.to_dict()["result"]
    assert result["kind"] == "yield_expression"
    assert result["yield_kind"] == "theoretical"
    assert result["target"] == "book"


def test_v76_actual_yield_expression_parses():
    """`Y_A(Ω_book)` parses to a YieldExpression with kind='actual'."""
    artifact = compile_expression("Y_A(Omega_book)")
    assert artifact.valid, artifact.error
    result = artifact.to_dict()["result"]
    assert result["kind"] == "yield_expression"
    assert result["yield_kind"] == "actual"
    assert result["target"] == "book"


def test_v76_efficiency_expression_parses():
    """`η(Ω_book)` parses to a YieldExpression with kind='efficiency'.

    ASCII alias `eta` and Unicode `η` are both accepted.
    """
    artifact = compile_expression("eta(Omega_book)")
    assert artifact.valid, artifact.error
    result = artifact.to_dict()["result"]
    assert result["kind"] == "yield_expression"
    assert result["yield_kind"] == "efficiency"
    assert result["target"] == "book"
    # Also confirm the Unicode form parses equivalently.
    artifact_u = compile_expression("η(Ω_book)")
    assert artifact_u.valid, artifact_u.error
    result_u = artifact_u.to_dict()["result"]
    assert result_u["yield_kind"] == "efficiency"
    assert result_u["target"] == "book"


def test_v76_leakage_annotation_parses():
    """Leakage on RHS: `Θ(Ω_book) = 2·F_2 → Ω_book + 0.3·Ω_procrastination`.

    The leakage is recorded as a side-product with its own coefficient
    (Clarification 9 §3 leakage notation). The recipe body captures one
    leakage entry pointing at Ω_procrastination with coefficient 0.3.
    """
    artifact = compile_expression(
        "Theta(Omega_book) = 2*F_2 -> Omega_book + 0.3*Omega_procrastination"
    )
    assert artifact.valid, artifact.error
    result = artifact.to_dict()["result"]
    assert result["kind"] == "recipe"
    assert result["target"] == "book"
    assert len(result["leakages"]) == 1
    leak = result["leakages"][0]
    assert leak["target"] == "procrastination"
    assert leak["coefficient"] == 0.3


def test_v76_conditions_annotation_parses():
    """`Θ(Ω_book) = 2·F_2 | κ_deadline, ι_fatigue → Ω_book` — conditions
    before the arrow are recorded as catalysts and inhibitors.
    """
    artifact = compile_expression(
        "Theta(Omega_book) = 2*F_2 | kappa_deadline, iota_fatigue -> Omega_book"
    )
    assert artifact.valid, artifact.error
    result = artifact.to_dict()["result"]
    assert result["kind"] == "recipe"
    assert result["catalysts"] == ["deadline"]
    assert result["inhibitors"] == ["fatigue"]


def test_v76_invalid_recipe_missing_arrow_rejected():
    """A recipe without a `→` is rejected with a v7.6-specific error message.

    `Θ(Ω_book) = 2·F_2` is missing the arrow: the compiler must NOT treat
    this as a valid recipe; it must reject with a clear CAS v7.6 error so
    authors can correct the shape.
    """
    artifact = compile_expression("Theta(Omega_book) = 2*F_2")
    assert not artifact.valid
    assert artifact.error is not None
    assert "v7.6" in artifact.error
    # The specific failure mode (missing arrow) should be named so authors
    # can find and fix the typo quickly.
    assert "→" in artifact.error or "arrow" in artifact.error.lower()


def test_v76_invalid_recipe_missing_coefficient_separator_rejected():
    """Malformed coefficient (missing `·` between number and primitive).

    `Θ(Ω_book) = 2 F_2 → Ω_book` lacks the coefficient separator; the
    compiler rejects with a v7.6-specific error naming the missing `·`.
    """
    artifact = compile_expression("Theta(Omega_book) = 2 F_2 -> Omega_book")
    assert not artifact.valid
    assert artifact.error is not None
    assert "v7.6" in artifact.error


def test_v76_v75_expression_still_parses_as_state_not_recipe():
    """Backward-compat: a plain v7.5 compound-state expression `^2^C_{F_2}|A`
    continues to parse as a state (not a recipe), preserving every
    pre-v7.6 call site.
    """
    artifact = compile_expression("^2^C_{F_2}|A")
    assert artifact.valid, artifact.error
    result = artifact.to_dict()["result"]
    # It is a v7.5 STATE, not a v7.6 RECIPE.
    assert result["kind"] == "state"
    assert result["dominant_state"] == "C2"
    assert result["register"] == "A"


def test_v76_recipe_with_compound_primitive_prerequisite():
    """A prerequisite may itself be a v7.5 compound state with register.

    `Θ(Ω_refusal) = 1·^3^P_{F_2}|A + 1·^3^P_{F_2}|f → Ω_refusal` -- the AI
    reliable-refusal recipe from Clarification 9 §7 uses compound
    principled-aversion states as prerequisites.
    """
    artifact = compile_expression(
        "Theta(Omega_refusal) = 1*^3^P_{F_2}|A + 1*^3^P_{F_2}|f -> Omega_refusal"
    )
    assert artifact.valid, artifact.error
    result = artifact.to_dict()["result"]
    assert result["kind"] == "recipe"
    assert result["target"] == "refusal"
    prereqs = result["prerequisites"]
    assert len(prereqs) == 2
    # Each prereq primitive is the compound state `^3^P_{F_2}` with a
    # register suffix; the AST surfaces the register on each.
    import json as _json
    serialized = _json.dumps(prereqs)
    assert '"register": "A"' in serialized
    assert '"register": "f"' in serialized
    # Operators and domain of each prereq primitive are the principled-
    # aversion shape `^3^P`.
    for prereq in prereqs:
        assert prereq["primitive"]["operator"] == "CO-3"
        assert prereq["primitive"]["domain"] == "P"


def test_v76_recipe_addition_and_subtraction_parses():
    """Recipe arithmetic (Clarification 9 §6):

      `Θ(Ω_1) + Θ(Ω_2)` — parallel production requirements
      `Θ(Ω_full) − Θ(Ω_achieved)` — remaining production requirement

    The compiler parses both without evaluating them (recipe algebra is a
    Rust cas-engine responsibility). What we verify here is that the
    additive / subtractive combination parses successfully and each
    operand recovers as a recipe reference.
    """
    art_plus = compile_expression("Theta(Omega_1) + Theta(Omega_2)")
    assert art_plus.valid, art_plus.error
    # The result of combining two recipe references is a program whose
    # entries are the two RecipeValues in order.
    result = art_plus.to_dict()["result"]
    assert result["kind"] == "program"
    recipe_results = [r for r in result["results"] if r["kind"] == "recipe"]
    assert len(recipe_results) == 2
    assert recipe_results[0]["target"] == "1"
    assert recipe_results[1]["target"] == "2"

    art_minus = compile_expression("Theta(Omega_full) - Theta(Omega_achieved)")
    assert art_minus.valid, art_minus.error


def test_v76_production_target_literal_standalone():
    """`Ω_foo` may appear as a standalone primary expression.

    A standalone production-target literal is legitimate input to a
    yield query or to higher-level algebra. The compiler accepts it and
    emits a ProductionTargetValue.
    """
    artifact = compile_expression("Omega_foo")
    assert artifact.valid, artifact.error
    result = artifact.to_dict()["result"]
    assert result["kind"] == "production_target"
    assert result["name"] == "foo"


def test_v76_recipe_with_float_coefficient():
    """Recipe coefficients may be floats.

    `Θ(Ω) = 0.5·F_2 + 2.25·F_3 → Ω` -- the compiler widens integer
    coefficients to float uniformly and accepts decimal literals.
    """
    artifact = compile_expression(
        "Theta(Omega_x) = 0.5*F_2 + 2.25*F_3 -> Omega_x"
    )
    assert artifact.valid, artifact.error
    result = artifact.to_dict()["result"]
    coeffs = [p["coefficient"] for p in result["prerequisites"]]
    assert coeffs == [0.5, 2.25]


def test_v76_recipe_with_multiple_leakages():
    """Multiple leakage terms on the RHS are accumulated in order."""
    artifact = compile_expression(
        "Theta(Omega_book) = 2*F_2 -> Omega_book "
        "+ 0.3*Omega_procrastination + 0.1*Omega_fatigue"
    )
    assert artifact.valid, artifact.error
    result = artifact.to_dict()["result"]
    leaks = result["leakages"]
    assert len(leaks) == 2
    assert leaks[0]["target"] == "procrastination"
    assert leaks[0]["coefficient"] == 0.3
    assert leaks[1]["target"] == "fatigue"
    assert leaks[1]["coefficient"] == 0.1


def test_v76_recipe_coefficient_must_be_positive():
    """Zero / negative coefficients are rejected.

    Recipe weights are proportional requirements (Clarification 9 §2); a
    zero or negative weight is structurally invalid and must surface a
    v7.6-specific error.
    """
    # The minus token in `-2*F_2` is consumed by the additive parser (it
    # becomes `- (2*F_2)` of the empty recipe), but at the coefficient
    # position inside a recipe body we still expect a NUMBER, not a
    # MINUS. Instead, exercise the explicit-zero case which hits the
    # positivity check directly.
    artifact = compile_expression("Theta(Omega_x) = 0*F_2 -> Omega_x")
    assert not artifact.valid
    assert artifact.error is not None
    assert "v7.6" in artifact.error


# ---------------------------------------------------------------------------
# CAS v7.7 Register Multiplicity and Cross-Register Integration tests
# (Clarification 10, Sections 2, 3, 4, 6).
#
# Three additions over v7.5/v7.6:
#   1. `|⟨R1,R2,...⟩` register-set specification notation.
#   2. Rule 4 admissibility — same-Noetic multi-register `×` is invalid
#      unless wrapped in an explicit emergent-result assignment.
#   3. `(... × ... × ...) = X|Ω` named emergent-result notation that
#      licenses same-Noetic multi-register `×` by naming the fused state.
#
# Both Unicode mathematical angle brackets (⟨ / ⟩, U+27E8 / U+27E9 —
# canonical) and ASCII `<` / `>` (lexer aliases) are accepted wherever
# the LANGLE / RANGLE token fold applies.
# ---------------------------------------------------------------------------


# --- (1) Register-set specification -----------------------------------------


def test_v77_register_set_basic_parsing():
    """`^3^P|⟨A,f,T⟩` parses as a state with a register-set specification."""
    artifact = compile_expression("^3^P|⟨A,f,T⟩")
    assert artifact.valid, artifact.error
    result = artifact.to_dict()["result"]
    assert result["kind"] == "state"
    assert result["dominant_state"] == "P3"
    assert result["register_set"] == ["A", "f", "T"]
    assert result["register_set_names"] == ["Analytical", "Affective", "Transcendent"]


def test_v77_register_set_lowercase_f_preserved():
    """Lowercase `f` in a register set is preserved (authoritative Affective)."""
    artifact = compile_expression("^3^P|⟨A,f⟩")
    assert artifact.valid, artifact.error
    result = artifact.to_dict()["result"]
    assert "f" in result["register_set"]
    assert result["register_set"] == ["A", "f"]


def test_v77_register_set_invalid_element_rejected():
    """An invalid register letter inside a set is rejected with a v7.7 error."""
    artifact = compile_expression("^3^P|⟨A,Q,T⟩")
    assert not artifact.valid
    assert artifact.error is not None
    # Error cites the Phenomenological Register valid set and flags Q.
    assert "Q" in artifact.error
    assert "T" in artifact.error and "A" in artifact.error
    assert "f" in artifact.error and "E" in artifact.error


def test_v77_register_set_duplicate_rejected():
    """Duplicate registers inside a set are rejected per Clarification 10 §2."""
    artifact = compile_expression("^3^P|⟨A,A,T⟩")
    assert not artifact.valid
    assert artifact.error is not None
    assert "duplicate" in artifact.error.lower()
    assert "Clarification 10" in artifact.error


def test_v77_register_set_empty_rejected():
    """An empty register set `|⟨⟩` is rejected."""
    artifact = compile_expression("^3^P|⟨⟩")
    assert not artifact.valid
    assert artifact.error is not None
    assert "at least one register" in artifact.error
    assert "Clarification 10" in artifact.error


def test_v77_register_set_single_element_accepted():
    """A single-element register set `|⟨A⟩` is syntactically acceptable.

    The specification does not forbid this form; it is merely stylistically
    equivalent to the bare `|A` form. The compiler accepts it without error
    (a stylistic warning is a permitted but optional enhancement).
    """
    artifact = compile_expression("^3^P|⟨A⟩")
    assert artifact.valid, artifact.error
    result = artifact.to_dict()["result"]
    assert result["register_set"] == ["A"]


def test_v77_register_set_serialization_preserves_set_form():
    """Round-trip: AST serialization preserves register-set shape (not a
    single register). `|⟨A,T⟩` survives as a list on the serialized AST
    and the runtime state value, not collapsed to a single `register` key.
    """
    artifact = compile_expression("^3^P|⟨A,T⟩")
    assert artifact.valid, artifact.error
    # Serialized AST carries `register_set` (list), not `register` (string).
    ast_payload = artifact.to_dict()["ast"]
    assert ast_payload.get("register_set") == ["A", "T"]
    assert "register" not in ast_payload  # not collapsed
    # Runtime result surfaces the same set form.
    result = artifact.to_dict()["result"]
    assert result.get("register_set") == ["A", "T"]
    assert "register" not in result  # distinct from single-register key


# --- (2) Rule 4 admissibility enforcement -----------------------------------


def test_v77_rule4_bare_same_noetic_times_rejected():
    """`^3^P|A × ^3^P|f` is Rule 4 invalid (same Noetic+Domain, two registers,
    no emergent result specified)."""
    artifact = compile_expression("^3^P|A * ^3^P|f")
    assert not artifact.valid
    assert artifact.error is not None
    assert "Section 4" in artifact.error


def test_v77_rule4_different_noetic_times_accepted():
    """Different-Noetic `×` is valid cross-state integration (not Rule 4)."""
    artifact = compile_expression("^5^C * ^6^C")
    assert artifact.valid, artifact.error


def test_v77_rule4_different_domain_times_accepted():
    """Same Noetic, different Domain `×` is valid (not Rule 4)."""
    artifact = compile_expression("^2^P * ^2^O")
    assert artifact.valid, artifact.error


def test_v77_rule4_different_drive_times_accepted():
    """Same Noetic+Domain, different Drive `×` is valid (not Rule 4)."""
    artifact = compile_expression("^5^C_{F2} * ^5^C_{F4}")
    assert artifact.valid, artifact.error


def test_v77_rule4_same_noetic_times_with_named_result_accepted():
    """`(^3^P|A × ^3^P|f) = X` licenses same-Noetic `×` via emergent result."""
    artifact = compile_expression("(^3^P|A * ^3^P|f) = fused")
    assert artifact.valid, artifact.error
    result = artifact.to_dict()["result"]
    assert result["kind"] == "state"
    assert result.get("emergent_register") == "fused"


def test_v77_rule4_error_cites_clarification_10():
    """The Rule 4 error explicitly names 'Clarification 10 Section 4'."""
    artifact = compile_expression("^3^P|A * ^3^P|T")
    assert not artifact.valid
    assert artifact.error is not None
    assert "Clarification 10" in artifact.error
    assert "Section 4" in artifact.error


def test_v77_rule4_error_suggests_alternatives():
    """The Rule 4 error suggests all three valid alternatives: `+`, `|⟨…⟩`,
    or explicit emergent-result assignment.
    """
    artifact = compile_expression("^3^P|A * ^3^P|f")
    assert not artifact.valid
    assert artifact.error is not None
    # Three alternative shapes should appear in the suggestion text.
    assert "+" in artifact.error  # co-presence form
    assert "⟨" in artifact.error  # register-set form
    assert "=" in artifact.error  # emergent-result assignment form


# --- (3) Co-presence (+) unchanged ------------------------------------------


def test_v77_same_noetic_plus_accepted():
    """Same-Noetic `+` expressions are valid (co-presence) per §3.

    `^3^P|A + ^3^P|f + ^3^P|T` is the canonical rewrite of a rejected
    same-Noetic `×` chain when co-presence is intended.
    """
    artifact = compile_expression("^3^P|A + ^3^P|f + ^3^P|T")
    assert artifact.valid, artifact.error


def test_v77_cross_domain_plus_accepted():
    """Cross-domain `+` expressions remain valid under v7.7."""
    artifact = compile_expression("^2^P|T + ^2^O|E")
    assert artifact.valid, artifact.error


def test_v77_v76_recipe_plus_unchanged():
    """Backward compat: v7.6 recipe notation using `+` between prerequisites
    continues to parse as a recipe (not subject to Rule 4 since `+` is the
    co-presence operator, not `×`).
    """
    artifact = compile_expression(
        "Theta(Omega_refusal) = 1*^3^P|A + 1*^3^P|f -> Omega_refusal"
    )
    assert artifact.valid, artifact.error
    result = artifact.to_dict()["result"]
    assert result["kind"] == "recipe"
    assert result["target"] == "refusal"


# --- (4) Edge cases ---------------------------------------------------------


def test_v77_register_set_with_drive_subscript():
    """`^3^P_{F2}|⟨A,f,T⟩` — compound state with drive subscript AND register
    set attached to the compound. All v7.4/v7.5/v7.7 notation composes.
    """
    artifact = compile_expression("^3^P_{F2}|⟨A,f,T⟩")
    assert artifact.valid, artifact.error
    result = artifact.to_dict()["result"]
    assert result["kind"] == "state"
    assert result["dominant_state"] == "P3"
    assert result["dominant_drive"] == "F2"
    assert result["register_set"] == ["A", "f", "T"]


def test_v77_compound_with_register_set_operand():
    """A `×` with one operand carrying a register-set (different-Noetic case).

    `(^3^P|⟨A,f⟩ × ^6^P|T)` is different-Noetic `×` and therefore NOT a
    Rule 4 case — it is valid cross-state integration where the first
    operand carries a register-set specification and the second carries
    a single-register specification. Exercises the AST's ability to
    represent mixed register forms in a single expression.
    """
    artifact = compile_expression("(^3^P|⟨A,f⟩ * ^6^P|T)")
    assert artifact.valid, artifact.error


def test_v77_fractal_composition_with_register_sets():
    """Fractal composition `∘` accepts operands with register sets.

    `^9|⟨A,E⟩ ∘ ^4|f` combines a register-set-specified ^9 with a
    single-register ^4. Fractal composition is never subject to Rule 4
    (the restriction is on `×`, not on `∘`).
    """
    artifact = compile_expression("^9|⟨A,E⟩ ∘ ^4|f")
    assert artifact.valid, artifact.error


# ---------------------------------------------------------------------------
# Per-position register activation extraction (ADR-02 trainer integration).
#
# These tests exercise `extract_register_activations` / the
# `CompilationArtifact.activations()` convenience wrapper. The view is
# additive and opt-in: existing tests above still assert on
# `artifact.to_dict()` and ignore activations entirely, proving backward
# compatibility of the compiler's primary output.
# ---------------------------------------------------------------------------


def test_activations_register_neutral_single_state():
    """`^3^P` (no register) emits one activation with an empty register set.

    Empty registers_active is semantically distinct from "zero registers" —
    the trainer uses empty to mean "skip register supervision for this
    example" per `cas-native/training/data_format.md` masking rules.
    """
    artifact = compile_expression("^3^P")
    assert artifact.valid, artifact.error
    acts = artifact.activations()
    assert len(acts) == 1
    assert acts[0] == RegisterActivation(
        position=3,
        registers_active=frozenset(),
        is_register_set=False,
        emergent_name=None,
    )


def test_activations_single_register_each_of_four_registers():
    """Each valid register T/A/f/E parses and projects into activations."""
    for reg in VALID_REGISTERS:
        artifact = compile_expression(f"^2^C|{reg}")
        assert artifact.valid, f"|{reg}: {artifact.error}"
        acts = artifact.activations()
        assert len(acts) == 1
        assert acts[0].registers_active == frozenset({reg})
        assert acts[0].is_register_set is False
        assert acts[0].position == 12  # ^2 on domain C (DOMAIN_ORDER['C']*10+2)


def test_activations_lowercase_f_preserved_end_to_end():
    """Lowercase `|f` (Affective) survives into the activation view verbatim."""
    artifact = compile_expression("^5^E|f")
    assert artifact.valid, artifact.error
    acts = artifact.activations()
    assert len(acts) == 1
    # Explicit string check — no silent uppercasing on the trainer-facing
    # surface. Affective register is authoritatively lowercase.
    assert "f" in acts[0].registers_active
    assert "F" not in acts[0].registers_active


def test_activations_register_set_notation():
    """`^3^P|⟨A,f,T⟩` produces is_register_set=True with the 3-element set."""
    artifact = compile_expression("^3^P|⟨A,f,T⟩")
    assert artifact.valid, artifact.error
    acts = artifact.activations()
    assert len(acts) == 1
    assert acts[0].registers_active == frozenset({"A", "f", "T"})
    assert acts[0].is_register_set is True
    assert acts[0].position == 3  # ^3 on domain P


def test_activations_register_set_order_invariant():
    """Register-set ordering at the source does not affect activation equality.

    `|⟨A,f,T⟩` and `|⟨T,A,f⟩` are permutations of the same set. The
    activation view normalizes via frozenset so both compare equal.
    """
    a = compile_expression("^3^P|⟨A,f,T⟩").activations()
    b = compile_expression("^3^P|⟨T,A,f⟩").activations()
    assert a == b


def test_activations_compound_expression_preserves_source_order():
    """Multiple state positions emit activations in source (left-to-right) order.

    `^2^P|A + ^5^C|f + ^7^O|E` parses as a three-term sum (BinaryExpr). The
    walker descends left-to-right and the resulting activation list reflects
    that order so a trainer can scatter per-position supervision without
    any reordering pass.
    """
    artifact = compile_expression("^2^P|A + ^5^C|f + ^7^O|E")
    assert artifact.valid, artifact.error
    acts = artifact.activations()
    assert len(acts) == 3
    assert acts[0].position == 2   # ^2^P
    assert acts[1].position == 15  # ^5^C = DOMAIN_ORDER['C']*10 + 5 = 15
    assert acts[2].position == 37  # ^7^O = DOMAIN_ORDER['O']*10 + 7 = 37
    assert acts[0].registers_active == frozenset({"A"})
    assert acts[1].registers_active == frozenset({"f"})
    assert acts[2].registers_active == frozenset({"E"})


def test_activations_position_index_formula_spot_checks():
    """Position index is DOMAIN_ORDER[domain]*10 + operator, at each domain."""
    cases = [
        ("^3^P", 3),   # P=0 ⇒ 0*10 + 3
        ("^3^C", 13),  # C=1 ⇒ 1*10 + 3
        ("^3^E", 23),  # E=2 ⇒ 2*10 + 3
        ("^9^O", 39),  # O=3 ⇒ 3*10 + 9
        ("^0^P", 0),
    ]
    for source, expected_pos in cases:
        acts = compile_expression(source).activations()
        assert len(acts) == 1
        assert acts[0].position == expected_pos, source


def test_activations_emergent_result_captures_emergent_name_and_operands():
    """`(^3^P|A × ^3^P|f) = fused` emits operand activations tagged with the
    emergent name, plus a trailing emergent record carrying the union of
    operand registers.
    """
    artifact = compile_expression("(^3^P|A * ^3^P|f) = fused")
    assert artifact.valid, artifact.error
    acts = artifact.activations()
    # Two operand activations + one emergent activation = 3 records.
    assert len(acts) == 3
    # Operands: each tagged with emergent_name="fused".
    assert acts[0].position == 3
    assert acts[0].registers_active == frozenset({"A"})
    assert acts[0].emergent_name == "fused"
    assert acts[0].is_register_set is False
    assert acts[1].position == 3
    assert acts[1].registers_active == frozenset({"f"})
    assert acts[1].emergent_name == "fused"
    # Emergent record: union of operand registers, flagged with name.
    assert acts[2].position == 3
    assert acts[2].registers_active == frozenset({"A", "f"})
    assert acts[2].emergent_name == "fused"
    assert acts[2].is_register_set is False


def test_activations_empty_for_pure_drive_expression():
    """Pure drive query (`RPM(F5)`) emits no state-position activations.

    DriveLiteral nodes are not projected onto the 40-state bank. See the
    module comment in compiler.py for the rationale.
    """
    artifact = compile_expression("RPM(F5)")
    assert artifact.valid, artifact.error
    assert artifact.activations() == []


def test_activations_preserve_drive_in_compound_but_only_noetic_register():
    """`^2^C_{F2}|A` — activation surfaces the Noetic-level register `|A` on
    the compound-state position; the drive subscript does not add a second
    activation (drives are a separate axis).
    """
    artifact = compile_expression("^2^C_{F2}|A")
    assert artifact.valid, artifact.error
    acts = artifact.activations()
    assert len(acts) == 1
    assert acts[0].position == 12
    assert acts[0].registers_active == frozenset({"A"})


def test_activations_valid_registers_is_single_source_of_truth():
    """The activation record never contains a register letter outside
    VALID_REGISTERS. Spot-checked by iterating every v7.5 register through
    the walker and asserting membership in the canonical tuple.
    """
    for reg in VALID_REGISTERS:
        acts = compile_expression(f"^4^E|{reg}").activations()
        assert len(acts) == 1
        for letter in acts[0].registers_active:
            assert letter in VALID_REGISTERS


def test_activations_are_hashable_and_equality_comparable():
    """RegisterActivation is a frozen dataclass — records compare equal on
    structural equality and are usable as dict keys / set members. This
    matters for downstream batching that deduplicates identical labels.
    """
    a = compile_expression("^3^P|⟨A,f,T⟩").activations()[0]
    b = compile_expression("^3^P|⟨f,T,A⟩").activations()[0]
    assert a == b
    assert hash(a) == hash(b)
    # Equality sensitive to position:
    c = compile_expression("^3^C|⟨A,f,T⟩").activations()[0]
    assert a != c


def test_activations_backward_compat_existing_compiler_output_unchanged():
    """Pre-existing CompilationArtifact fields (`valid`, `result`, `ast`,
    `to_dict()`) for a register-bearing expression are byte-identical to
    what they produced before this API was added — the per-position
    activation view is strictly additive.

    We verify by spot-checking the shapes that other consumers (parser,
    scorer, synthesizer) rely on: the result dict carries `register` as
    before, and `to_dict()` contains no `activations` key.
    """
    artifact = compile_expression("^3^P|A")
    result = artifact.to_dict()["result"]
    assert result["register"] == "A"
    # Activation view is an opt-in method, not a to_dict() field.
    assert "activations" not in artifact.to_dict()
    # But the opt-in method still works and returns the expected record.
    acts = artifact.activations()
    assert len(acts) == 1 and "A" in acts[0].registers_active


def test_activations_extract_function_on_raw_ast():
    """`extract_register_activations` accepts a raw parsed AST directly, not
    only a `CompilationArtifact`. This supports callers that have already
    parsed an expression and want the activation view without re-compiling.
    """
    artifact = compile_expression("^2^P|T + ^3^P|A")
    acts = extract_register_activations(artifact.ast)
    assert len(acts) == 2
    assert acts[0].registers_active == frozenset({"T"})
    assert acts[1].registers_active == frozenset({"A"})


def test_activations_register_set_crossing_rule4_boundary_still_extracted():
    """If an expression violates Rule 4 (same-Noetic `×` without emergent
    result), the compiler rejects it — but Rule 4 validation is a separate
    concern from activation extraction. A hand-built expression that
    exercises activation extraction on register-set operands (a different-
    Noetic compound, which Rule 4 does not flag) still emits the expected
    activations with the register-set flag propagated correctly.
    """
    artifact = compile_expression("^3^P|⟨A,f⟩ * ^6^P|T")
    assert artifact.valid, artifact.error
    acts = artifact.activations()
    assert len(acts) == 2
    assert acts[0].is_register_set is True
    assert acts[0].registers_active == frozenset({"A", "f"})
    assert acts[1].is_register_set is False
    assert acts[1].registers_active == frozenset({"T"})
