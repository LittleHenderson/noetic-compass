"""Tests for the executable CAS notation compiler."""

from pathlib import Path
import shutil
import uuid

from api.notation.compiler import compile_expression, compile_file


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
    assert "positive" in artifact.error.lower()
