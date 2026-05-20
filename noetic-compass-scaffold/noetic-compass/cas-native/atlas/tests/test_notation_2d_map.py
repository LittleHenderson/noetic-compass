"""Property tests for the canonical 2D notation map (Stage 23.A).

Every assertion here corresponds to a row in the Stage 23.A acceptance
criteria table in STAGE23_ATLAS_SELF_READING_PREREG_20260519.md. If any
of these tests regresses, the canonical layout has drifted and the
preregistration boundary has been broken.
"""
from __future__ import annotations

import math
import re

import pytest

from cas_native.atlas import notation_2d_map as nm


# ── Coverage: every primitive has a position ──────────────────────────


def test_every_noetic_has_a_position() -> None:
    for n in nm.NOETICS:
        pos = nm.get_position(n)
        assert pos.kind == "noetic"
        assert isinstance(pos.x, float)
        assert isinstance(pos.y, float)


def test_every_domain_has_a_position() -> None:
    for d in nm.DOMAINS:
        pos = nm.get_position(d)
        assert pos.kind == "domain"


def test_every_drive_has_a_position() -> None:
    for f in nm.DRIVES:
        pos = nm.get_position(f)
        assert pos.kind == "drive"


def test_every_register_has_a_position() -> None:
    for r in nm.REGISTERS:
        pos = nm.get_position(r)
        assert pos.kind == "register"


def test_every_cognitive_state_has_a_position() -> None:
    for n in nm.NOETICS:
        for d in nm.DOMAINS:
            pos = nm.get_position(nm.state_id(n, d))
            assert pos.kind == "cognitive_state"


# ── Symmetry: involution pairs are reflection-symmetric ───────────────


def test_noetic_involution_pairs_reflect_across_origin() -> None:
    """For each involution pair (^a, ^b): position(^a) == -position(^b)."""
    for a, b in nm.NOETIC_INVOLUTIONS.items():
        pa = nm.get_position(a)
        pb = nm.get_position(b)
        # x_a + x_b ≈ 0, y_a + y_b ≈ 0 (reflection through origin).
        assert math.isclose(pa.x + pb.x, 0.0, abs_tol=1e-9), (
            f"Noetic involution pair {a}↔{b} not x-symmetric: "
            f"{pa.x} + {pb.x} = {pa.x + pb.x}"
        )
        assert math.isclose(pa.y + pb.y, 0.0, abs_tol=1e-9), (
            f"Noetic involution pair {a}↔{b} not y-symmetric: "
            f"{pa.y} + {pb.y} = {pa.y + pb.y}"
        )


def test_drive_involution_pairs_reflect_across_origin_x_axis() -> None:
    """Drive involution pairs reflect across x=0 (they share a y row)."""
    for a, b in nm.DRIVE_INVOLUTIONS.items():
        pa = nm.get_position(a)
        pb = nm.get_position(b)
        assert math.isclose(pa.x + pb.x, 0.0, abs_tol=1e-9), (
            f"Drive involution pair {a}↔{b} not x-symmetric: "
            f"{pa.x} + {pb.x} = {pa.x + pb.x}"
        )
        assert math.isclose(pa.y, pb.y, abs_tol=1e-9)


# ── Self-duals lie on a symmetry axis ─────────────────────────────────


def test_self_dual_noetics_lie_on_an_axis() -> None:
    """Self-dual Noetics (^0, ^1, ^4, ^7) sit on x=0 or y=0."""
    for n in nm.NOETIC_SELF_DUALS:
        pos = nm.get_position(n)
        on_axis = (
            math.isclose(pos.x, 0.0, abs_tol=1e-9)
            or math.isclose(pos.y, 0.0, abs_tol=1e-9)
        )
        assert on_axis, f"Self-dual Noetic {n} off-axis: ({pos.x}, {pos.y})"


def test_self_dual_drive_is_on_y_axis() -> None:
    """F4 (self-dual) sits at x=0."""
    pos = nm.get_position("F4")
    assert math.isclose(pos.x, 0.0, abs_tol=1e-9)


# ── Domain precedence is spatially monotone ───────────────────────────


def test_domain_precedence_is_spatially_monotone() -> None:
    """P ≻ C ≻ E ≻ O must map to monotone y positions (top-to-bottom)."""
    ys = [nm.get_position(d).y for d in ("^P", "^C", "^E", "^O")]
    for earlier, later in zip(ys, ys[1:]):
        assert earlier > later, (
            f"Domain precedence not monotone: {ys}"
        )


# ── Uniqueness: no two primitives share a coordinate ──────────────────


def test_no_two_primitives_share_a_coordinate() -> None:
    seen: dict[tuple[float, float], str] = {}
    for pos in nm.all_positions():
        key = (round(pos.x, 9), round(pos.y, 9))
        if key in seen:
            raise AssertionError(
                f"Coordinate collision at {key}: "
                f"{seen[key]!r} and {pos.primitive!r}"
            )
        seen[key] = pos.primitive


# ── Determinism: same inputs return same outputs across calls ─────────


def test_get_position_is_deterministic() -> None:
    for prim in ("^3", "^P", "F4", "|T", "^7^O"):
        first = nm.get_position(prim)
        second = nm.get_position(prim)
        assert first.x == second.x
        assert first.y == second.y
        assert first.kind == second.kind


def test_bare_E_is_ambiguous_and_raises() -> None:
    """Bare 'E' must be rejected — caller must use '^E' or '|E'."""
    with pytest.raises(ValueError, match="ambiguous"):
        nm.get_position("E")


def test_qualified_E_resolves_both_meanings() -> None:
    """'^E' is Evaluative Domain, '|E' is Embodied Register — different (x,y)."""
    eval_domain = nm.get_position("^E")
    embodied_register = nm.get_position("|E")
    assert eval_domain.kind == "domain"
    assert embodied_register.kind == "register"
    assert (eval_domain.x, eval_domain.y) != (embodied_register.x, embodied_register.y)


def test_compact_and_canonical_cognitive_state_ids_agree() -> None:
    """'^3P' (3-char compact) and '^3^P' (4-char canonical) map to same position."""
    compact = nm.get_position("^3P")
    canonical = nm.get_position("^3^P")
    assert compact.x == canonical.x
    assert compact.y == canonical.y
    # Emitted canonical id is always 4-char form.
    assert compact.primitive == "^3^P"
    assert canonical.primitive == "^3^P"


# ── Error path: unknown primitive raises ──────────────────────────────


def test_unknown_primitive_raises() -> None:
    with pytest.raises(KeyError):
        nm.get_position("^99")
    with pytest.raises(KeyError):
        nm.get_position("Q")  # not a Domain
    with pytest.raises(KeyError):
        nm.get_position("F99")
    with pytest.raises(KeyError):
        nm.get_position("Z")  # not a Register


# ── Layout payload: canonical artifact is well-formed ─────────────────


def test_canonical_layout_payload_has_required_shape() -> None:
    payload = nm.canonical_layout_payload()
    assert payload["layout_version"] == nm.LAYOUT_VERSION
    assert "stage_23_a" in payload["scope"]
    primitives = payload["primitives"]
    # Stage 23.A (65) + Stage 23.A.2 (92) + Stage 23.A.3 (12) = 169.
    # 23.A:    10 Noetics + 4 Domains + 7 Drives + 4 Registers + 40 Cognitive States = 65
    # 23.A.2:  5 Operations + 7 Inversion Axes + 28 Foundations + 5 Production
    #          + 22 RPM + 4 Set constructors + 6 Set relations + 4 Set operations
    #          + 4 Combinators + 5 Authority sets + 2 Cardinality kinds = 92
    # 23.A.3:  12 admitted Omega_* emergent registers = 12
    assert len(primitives) == 169
    # Every entry has the required shape.
    for entry in primitives:
        assert "primitive" in entry
        assert "kind" in entry
        assert "x" in entry
        assert "y" in entry


def test_layout_does_not_claim_future_capabilities() -> None:
    """Stage 23.A is foundation-only. The payload must not advertise
    reading/conditioning capabilities that belong to 23.B/23.C/23.D."""
    payload = nm.canonical_layout_payload()
    boundary = payload["boundary"].lower()
    assert "static" in boundary
    forbidden = ("trains", "conditions during inference", "atlas-self-reading enabled")
    for term in forbidden:
        assert term not in boundary, (
            f"Layout payload should not claim '{term}' at Stage 23.A"
        )


# ── Stage 23.A.2 — Operations ─────────────────────────────────────────


def test_every_operation_has_a_position() -> None:
    for op in nm.OPERATIONS:
        pos = nm.get_position(op)
        assert pos.kind == "operation"


def test_operation_inverse_pairs_reflect_across_y_axis() -> None:
    """×↔÷ and +↔− are positioned symmetrically across x=0."""
    plus = nm.get_position("+")
    minus = nm.get_position("−")
    times = nm.get_position("×")
    div = nm.get_position("÷")
    assert math.isclose(plus.x + minus.x, 0.0, abs_tol=1e-9)
    assert math.isclose(plus.y, minus.y, abs_tol=1e-9)
    assert math.isclose(times.x + div.x, 0.0, abs_tol=1e-9)
    assert math.isclose(times.y, div.y, abs_tol=1e-9)


def test_compose_operation_is_on_y_axis() -> None:
    """∘ is the standalone composition op; sits at x=0 like a self-dual."""
    pos = nm.get_position("∘")
    assert math.isclose(pos.x, 0.0, abs_tol=1e-9)


# ── Stage 23.A.2 — Inversion Axes ─────────────────────────────────────


def test_every_inversion_axis_has_a_position() -> None:
    for ax in nm.INVERSION_AXES:
        pos = nm.get_position(ax)
        assert pos.kind == "inversion_axis"


def test_compound_inversion_axis_is_centered() -> None:
    """Inv:P is the compound axis — sits at y=0 (center of the axis column)."""
    pos = nm.get_position("Inv:P")
    assert math.isclose(pos.y, 0.0, abs_tol=1e-9)


# ── Stage 23.A.2 — Foundations (Drive × Register) ─────────────────────


def test_every_foundation_has_a_position() -> None:
    """All 28 Foundations Fk^R must be positioned."""
    count = 0
    for drive_id in nm.DRIVES:
        for reg in ("T", "A", "f", "E"):
            pos = nm.get_position(f"{drive_id}^{reg}")
            assert pos.kind == "foundation"
            count += 1
    assert count == 28


def test_foundation_inherits_drive_x_and_register_y() -> None:
    """F1^T must share x with Drive F1 (vertical neighbor relationship)."""
    f1 = nm.get_position("F1")
    f1_T = nm.get_position("F1^T")
    assert math.isclose(f1.x, f1_T.x, abs_tol=1e-9)


def test_foundations_in_same_register_row_share_y() -> None:
    """All Fk^T (k=1..7) share the same y."""
    ys = [nm.get_position(f"F{k}^T").y for k in range(1, 8)]
    for y in ys[1:]:
        assert math.isclose(y, ys[0], abs_tol=1e-9)


# ── Stage 23.A.2 — Production primitives ──────────────────────────────


def test_every_production_primitive_has_a_position() -> None:
    for prod in nm.PRODUCTION_PRIMITIVES:
        pos = nm.get_position(prod)
        assert pos.kind == "production"


# ── Stage 23.A.2 — RPM chain (22 pathways) ────────────────────────────


def test_a0_root_has_a_position() -> None:
    pos = nm.get_position("A0")
    assert pos.kind == "rpm_pathway"
    assert math.isclose(pos.x, 0.0, abs_tol=1e-9)


def test_rpm_chain_d_w_p_rows_are_vertically_ordered() -> None:
    """A0 → Dn → Wn → Pn → outcome: each row sits below the previous."""
    a0 = nm.get_position("A0")
    d1 = nm.get_position("D1")
    w1 = nm.get_position("W1")
    p1 = nm.get_position("P1")
    assert a0.y > d1.y > w1.y > p1.y, (
        f"RPM chain rows not monotone descending: "
        f"A0={a0.y}, D={d1.y}, W={w1.y}, P={p1.y}"
    )


def test_all_rpm_pathways_have_positions() -> None:
    nm.get_position("A0")
    for prefix in ("D", "W", "P"):
        for i in range(1, 8):
            pos = nm.get_position(f"{prefix}{i}")
            assert pos.kind == "rpm_pathway"


# ── Stage 23.A.2 — Set primitives + Authority Sets + Cardinality ──────


def test_set_constructors_have_positions() -> None:
    for ctor in nm.SET_CONSTRUCTORS:
        pos = nm.get_position(ctor)
        assert pos.kind == "set_constructor"


def test_set_relations_have_positions() -> None:
    for rel in nm.SET_RELATIONS:
        pos = nm.get_position(rel)
        assert pos.kind == "set_relation"


def test_set_operations_have_positions() -> None:
    for op in nm.SET_OPERATIONS:
        pos = nm.get_position(op)
        assert pos.kind == "set_operation"


def test_combinators_have_positions() -> None:
    for c in nm.COMBINATORS:
        pos = nm.get_position(c)
        assert pos.kind == "combinator"


def test_authority_sets_have_positions() -> None:
    for a in nm.AUTHORITY_SETS:
        pos = nm.get_position(a)
        assert pos.kind == "authority_set"


def test_authority_sets_ordered_by_trust() -> None:
    """System (highest trust) at top, Rendered (lowest) at bottom."""
    order = [
        "SystemInstructionSet",
        "UserUtteranceSet",
        "ToolObservationSet",
        "ValidatedClaimSet",
        "RenderedResponseSet",
    ]
    ys = [nm.get_position(a).y for a in order]
    for earlier, later in zip(ys, ys[1:]):
        assert earlier > later, f"Authority trust order not monotone: {ys}"


def test_cardinality_kinds_have_positions() -> None:
    for ck in nm.CARDINALITY_KINDS:
        pos = nm.get_position(ck)
        assert pos.kind == "cardinality_kind"


# ── Stage 23.A.2 — global property: now 169 unique primitives (with 23.A.3) ─


def test_stage_23_a_3_total_primitive_count_is_169() -> None:
    positions = nm.all_positions()
    assert len(positions) == 169


def test_no_collisions_across_full_169_primitive_set() -> None:
    """The Stage 23.A no-collision invariant must still hold at 23.A.3."""
    seen: dict[tuple[float, float], str] = {}
    for pos in nm.all_positions():
        key = (round(pos.x, 9), round(pos.y, 9))
        if key in seen:
            raise AssertionError(
                f"Coordinate collision at {key}: "
                f"{seen[key]!r} and {pos.primitive!r}"
            )
        seen[key] = pos.primitive


def test_all_17_primitive_kinds_are_populated() -> None:
    """Every kind in the PrimitiveKind Literal must have at least one entry."""
    expected_kinds = {
        "noetic", "domain", "drive", "register", "cognitive_state",
        "operation", "inversion_axis", "foundation", "production",
        "rpm_pathway", "set_constructor", "set_relation",
        "set_operation", "combinator", "authority_set", "cardinality_kind",
        "emergent_omega",
    }
    observed_kinds = {p.kind for p in nm.all_positions()}
    assert observed_kinds == expected_kinds, (
        f"Missing kinds: {expected_kinds - observed_kinds}; "
        f"Extra kinds: {observed_kinds - expected_kinds}"
    )


# ── Stage 23.A.3 — Emergent Omega_* registers ─────────────────────────


def test_every_emergent_omega_has_a_position() -> None:
    """All 12 admitted Omega_* registers in EMERGENT_OMEGAS get a position."""
    assert len(nm.EMERGENT_OMEGAS) == 12
    for name in nm.EMERGENT_OMEGAS:
        pos = nm.get_position(name)
        assert pos.kind == "emergent_omega"
        assert pos.primitive == name


def test_every_omega_is_closer_to_its_anchor_noetic_than_to_any_other() -> None:
    """Each Ω must sit closer to its derivation anchor Noetic than to any
    other Noetic — the spatial-anchor invariant of the 23.A.3 design.
    """
    for name in nm.EMERGENT_OMEGAS:
        omega_pos = nm.get_position(name)
        anchor = nm.OMEGA_ANCHOR_NOETIC[name]
        ax, ay = nm.get_position(anchor).x, nm.get_position(anchor).y
        anchor_d2 = (omega_pos.x - ax) ** 2 + (omega_pos.y - ay) ** 2
        for other in nm.NOETICS:
            if other == anchor:
                continue
            ox, oy = nm.get_position(other).x, nm.get_position(other).y
            other_d2 = (omega_pos.x - ox) ** 2 + (omega_pos.y - oy) ** 2
            assert anchor_d2 < other_d2, (
                f"Omega {name!r} is not closer to anchor {anchor!r} "
                f"(d²={anchor_d2:.4f}) than to {other!r} (d²={other_d2:.4f})"
            )


def test_no_omega_collides_with_any_other_primitive() -> None:
    """No Ω position may coincide with any non-Ω primitive position."""
    omega_names = set(nm.EMERGENT_OMEGAS)
    omega_keys: dict[tuple[float, float], str] = {}
    other_keys: dict[tuple[float, float], str] = {}
    for pos in nm.all_positions():
        key = (round(pos.x, 9), round(pos.y, 9))
        if pos.primitive in omega_names:
            omega_keys[key] = pos.primitive
        else:
            other_keys[key] = pos.primitive
    overlap = set(omega_keys) & set(other_keys)
    assert not overlap, (
        f"Omega coordinates collide with non-Omega primitives at: "
        + ", ".join(
            f"{k} ({omega_keys[k]!r} ↔ {other_keys[k]!r})" for k in overlap
        )
    )


def test_omega_radius_is_outside_noetic_ring() -> None:
    """Each Ω must sit on a ring strictly outside the unit Noetic ring."""
    for name in nm.EMERGENT_OMEGAS:
        pos = nm.get_position(name)
        r2 = pos.x ** 2 + pos.y ** 2
        assert r2 > 1.0, (
            f"Omega {name!r} at ({pos.x}, {pos.y}) is inside the Noetic ring"
        )
        # And on the canonical Ω-ring (radius 1.8) within floating tolerance.
        assert math.isclose(math.sqrt(r2), nm.OMEGA_RADIUS, abs_tol=1e-9), (
            f"Omega {name!r} off the canonical Ω-ring of radius "
            f"{nm.OMEGA_RADIUS}: r={math.sqrt(r2)}"
        )


def test_omega_anchor_map_matches_registry_anchor_noetics() -> None:
    """The hardcoded OMEGA_ANCHOR_NOETIC mirrors the LHS Noetic of each
    derivation in cas-native/config/omega_registry.yaml. Verified here as
    a structural check that the spec and code agree on the 12 anchors.
    """
    expected = {
        "Omega_presence":   "^1",
        "Omega_refusal":    "^3",
        "Omega_grounding":  "^2",
        "Omega_alignment":  "^5",
        "Omega_clarity":    "^1",
        "Omega_resolve":    "^6",
        "Omega_witness":    "^1",
        "Omega_attunement": "^4",
        "Omega_genesis":    "^0",
        "Omega_cadence":    "^7",
        "Omega_invocation": "^8",
        "Omega_landing":    "^9",
    }
    assert nm.OMEGA_ANCHOR_NOETIC == expected


# ── Stage 23.A.1.1 — per-primitive color field ────────────────────────


_HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


def test_every_primitive_payload_entry_has_a_valid_color() -> None:
    """Every emitted primitive carries a 7-char hex color string."""
    payload = nm.canonical_layout_payload()
    for entry in payload["primitives"]:
        assert "color" in entry, (
            f"Primitive {entry.get('primitive')!r} missing 'color' field"
        )
        color = entry["color"]
        assert isinstance(color, str), (
            f"Primitive {entry['primitive']!r} color is not a str: {color!r}"
        )
        assert _HEX_COLOR_RE.match(color), (
            f"Primitive {entry['primitive']!r} color {color!r} not 7-char hex"
        )


def test_every_primitive_color_matches_kind_color_table() -> None:
    """Each emitted color must equal KIND_COLOR[kind] for that entry."""
    payload = nm.canonical_layout_payload()
    for entry in payload["primitives"]:
        kind = entry["kind"]
        expected = nm.KIND_COLOR[kind]
        assert entry["color"] == expected, (
            f"Primitive {entry['primitive']!r} (kind={kind!r}) has color "
            f"{entry['color']!r}; expected KIND_COLOR[{kind!r}] = {expected!r}"
        )


def test_kind_color_covers_every_primitive_kind() -> None:
    """Every PrimitiveKind that appears on a position must have a color."""
    observed_kinds = {p.kind for p in nm.all_positions()}
    for kind in observed_kinds:
        assert kind in nm.KIND_COLOR, (
            f"Kind {kind!r} appears on a primitive but has no KIND_COLOR entry"
        )


# ── Stage 23.A.1.1 — detection_rules payload field ────────────────────


def test_payload_has_detection_rules_list() -> None:
    payload = nm.canonical_layout_payload()
    assert "detection_rules" in payload
    rules = payload["detection_rules"]
    assert isinstance(rules, list)
    assert len(rules) >= 12


def test_every_detection_rule_has_required_keys() -> None:
    payload = nm.canonical_layout_payload()
    required = {"priority", "kind", "regex", "description"}
    for rule in payload["detection_rules"]:
        missing = required - set(rule.keys())
        assert not missing, (
            f"Detection rule {rule!r} missing keys: {missing}"
        )
        assert isinstance(rule["priority"], int)
        assert isinstance(rule["kind"], str)
        assert isinstance(rule["regex"], str)
        assert isinstance(rule["description"], str)


def test_detection_rule_priorities_are_strictly_increasing() -> None:
    payload = nm.canonical_layout_payload()
    priorities = [int(rule["priority"]) for rule in payload["detection_rules"]]
    for earlier, later in zip(priorities, priorities[1:]):
        assert later > earlier, (
            f"Detection rule priorities not strictly increasing: {priorities}"
        )


def test_every_detection_rule_kind_is_a_valid_primitive_kind() -> None:
    payload = nm.canonical_layout_payload()
    valid_kinds = {
        "noetic", "domain", "drive", "register", "cognitive_state",
        "operation", "inversion_axis", "foundation", "production",
        "rpm_pathway", "set_constructor", "set_relation",
        "set_operation", "combinator", "authority_set", "cardinality_kind",
        "emergent_omega",
    }
    for rule in payload["detection_rules"]:
        assert rule["kind"] in valid_kinds, (
            f"Detection rule kind {rule['kind']!r} is not a valid PrimitiveKind"
        )


def test_every_detection_rule_regex_is_compilable() -> None:
    """Each rule's regex must compile cleanly (Python re.compile)."""
    payload = nm.canonical_layout_payload()
    for rule in payload["detection_rules"]:
        try:
            re.compile(rule["regex"])
        except re.error as exc:  # pragma: no cover — defensive
            raise AssertionError(
                f"Detection rule regex {rule['regex']!r} failed to compile: {exc}"
            )


# ── Stage 23.A.1.1 — detect_cas_kind smoke cases ──────────────────────


def test_detect_cas_kind_smoke_cases() -> None:
    # Direct primitive lookups.
    assert nm.detect_cas_kind("^3") == "noetic"
    assert nm.detect_cas_kind("^3^P") == "cognitive_state"
    assert nm.detect_cas_kind("F4") == "drive"
    assert nm.detect_cas_kind("Omega_refusal") == "emergent_omega"
    # No-signal inputs.
    assert nm.detect_cas_kind("random text") is None
    assert nm.detect_cas_kind("") is None
    assert nm.detect_cas_kind(None) is None


def test_detect_cas_kind_regex_fallback_for_inline_primitives() -> None:
    """When direct lookup misses, the regex rules classify embedded primitives."""
    # Compound state embedded in surrounding context.
    assert nm.detect_cas_kind("the state is ^7^E here") == "cognitive_state"
    # Bare drive subscript notation.
    assert nm.detect_cas_kind("_{F2}") == "drive"
    # Omega glyph fallback.
    assert nm.detect_cas_kind("see Ω derivation") == "emergent_omega"
    # Theta spelling.
    assert nm.detect_cas_kind("apply Theta recipe") == "production"
