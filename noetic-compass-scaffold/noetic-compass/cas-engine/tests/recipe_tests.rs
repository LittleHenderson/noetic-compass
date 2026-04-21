//! Integration tests for the CAS v7.6 Stoichiometric Production Semantics
//! recipe/primitive/state types per Clarification 9 Sections 2-3.
//!
//! Covers:
//! - Recipe construction with Noetic, Domain, Drive, Register, and compound
//!   prerequisites.
//! - Canonical notation for each PrimitiveId variant.
//! - Register annotation preservation (including LOWERCASE `f` from v7.5
//!   Clarification 8).
//! - StateVector missing-primitive → 0 convention.
//! - Recipe with leakages / conditions: serde round-trip preserves all
//!   fields.
//! - Backward compatibility: v7.5 types (Register, CognitiveStateVector)
//!   remain importable and untouched.

use cas_engine::ontology::{
    Catalyst, CognitiveOperator, CognitiveStateVector, Conditions, CoreDrive, Domain, Inhibitor,
    Leakage, PrimitiveId, ProductionTarget, Recipe, Register, StateVector,
};

// ---------------------------------------------------------------------------
// PrimitiveId — all five variants constructible with and without Register
// ---------------------------------------------------------------------------

#[test]
fn primitive_id_noetic_register_neutral() {
    let p = PrimitiveId::noetic(CognitiveOperator::CO2);
    assert_eq!(p.canonical_notation(), "^2");
    assert_eq!(p.register_annotation(), None);
}

#[test]
fn primitive_id_noetic_with_analytical_register() {
    let p = PrimitiveId::noetic_with_register(CognitiveOperator::CO2, Register::Analytical);
    assert_eq!(p.canonical_notation(), "^2|A");
    assert_eq!(p.register_annotation(), Some(Register::Analytical));
}

#[test]
fn primitive_id_domain_notation() {
    let p = PrimitiveId::domain(Domain::Cognitive);
    assert_eq!(p.canonical_notation(), "^C");
    let p_reg = PrimitiveId::domain_with_register(Domain::Principled, Register::Transcendent);
    assert_eq!(p_reg.canonical_notation(), "^P|T");
}

#[test]
fn primitive_id_drive_notation_affective_lowercase_f() {
    // Per CAS v7.5 Clarification 8 Section 3, the Affective register symbol
    // is LOWERCASE `f` (authoritative).
    let p = PrimitiveId::drive_with_register(CoreDrive::F2Wisdom, Register::Affective);
    assert_eq!(p.canonical_notation(), "F_2|f");
    let p_neutral = PrimitiveId::drive(CoreDrive::F7Purpose);
    assert_eq!(p_neutral.canonical_notation(), "F_7");
}

#[test]
fn primitive_id_register_only_notation() {
    let p = PrimitiveId::register(Register::Embodied);
    assert_eq!(p.canonical_notation(), "|E");
    assert_eq!(p.register_annotation(), Some(Register::Embodied));
}

#[test]
fn primitive_id_compound_notation() {
    // ^2^C_{F_2}|A — attraction, cognitive domain, wisdom drive, analytical.
    let p = PrimitiveId::compound_with_register(
        CognitiveOperator::CO2,
        Domain::Cognitive,
        CoreDrive::F2Wisdom,
        Register::Analytical,
    );
    assert_eq!(p.canonical_notation(), "^2^C_{F_2}|A");
    // Register-neutral compound.
    let p_neutral = PrimitiveId::compound(
        CognitiveOperator::CO7,
        Domain::Operational,
        CoreDrive::F6Structure,
    );
    assert_eq!(p_neutral.canonical_notation(), "^7^O_{F_6}");
}

#[test]
fn primitive_id_all_four_registers_round_trip() {
    for reg in Register::ALL {
        let p = PrimitiveId::drive_with_register(CoreDrive::F4Connection, reg);
        let expected = format!("F_4|{}", reg.symbol());
        assert_eq!(p.canonical_notation(), expected);
        assert_eq!(p.register_annotation(), Some(reg));
    }
}

// ---------------------------------------------------------------------------
// Recipe — construction with mixed primitive kinds
// ---------------------------------------------------------------------------

#[test]
fn recipe_mixed_prerequisites_noetic_domain_drive_register_compound() {
    // Exercise all five PrimitiveId variants as prerequisites in one recipe.
    let recipe = Recipe::new(
        ProductionTarget::new("mixed_target"),
        vec![
            (PrimitiveId::noetic(CognitiveOperator::CO2), 1.0),
            (PrimitiveId::domain(Domain::Cognitive), 2.0),
            (PrimitiveId::drive(CoreDrive::F2Wisdom), 3.0),
            (PrimitiveId::register(Register::Analytical), 1.0),
            (
                PrimitiveId::compound_with_register(
                    CognitiveOperator::CO7,
                    Domain::Operational,
                    CoreDrive::F6Structure,
                    Register::Embodied,
                ),
                4.0,
            ),
        ],
    );
    assert_eq!(recipe.arity(), 5);
    assert!(!recipe.is_empty());
    assert_eq!(recipe.target.name, "mixed_target");
    assert!(recipe.leakages.is_empty());
    assert!(recipe.conditions.catalysts.is_empty());
    assert!(recipe.conditions.inhibitors.is_empty());
}

#[test]
fn empty_recipe_is_empty() {
    let recipe = Recipe::new(ProductionTarget::new("empty"), vec![]);
    assert!(recipe.is_empty());
    assert_eq!(recipe.arity(), 0);
}

#[test]
fn recipe_zero_coefficient_preserved_at_construction() {
    // Clarification 9 Section 2 defines the yield min over i where aᵢ > 0;
    // zero-coefficient prerequisites are skipped at yield time but are NOT
    // rejected at construction (documented convention). Verify the Recipe
    // keeps the entry as-specified.
    let p = PrimitiveId::drive(CoreDrive::F2Wisdom);
    let recipe = Recipe::new(ProductionTarget::new("zero_coef"), vec![(p, 0.0)]);
    assert_eq!(recipe.prerequisites.len(), 1);
    assert_eq!(recipe.prerequisites[0].1, 0.0);
}

// ---------------------------------------------------------------------------
// Leakage & Conditions — structural preservation
// ---------------------------------------------------------------------------

#[test]
fn recipe_with_leakages_preserves_list() {
    let p1 = PrimitiveId::drive(CoreDrive::F2Wisdom);
    let p2 = PrimitiveId::noetic(CognitiveOperator::CO3);
    let leakages = vec![
        Leakage::new(p1, "Ω_side_chatter", 0.4),
        Leakage::new(p2, "Ω_side_rumination", 0.2),
    ];
    let recipe = Recipe::with_leakages_and_conditions(
        ProductionTarget::new("target"),
        vec![(p1, 2.0), (p2, 1.0)],
        leakages.clone(),
        Conditions::empty(),
    );
    assert_eq!(recipe.leakages.len(), 2);
    assert_eq!(recipe.leakages[0].side_product, "Ω_side_chatter");
    assert_eq!(recipe.leakages[0].magnitude, 0.4);
    assert_eq!(recipe.leakages[1].side_product, "Ω_side_rumination");
}

#[test]
fn recipe_with_conditions_preserves_catalysts_and_inhibitors() {
    let conds = Conditions::new(
        vec![Catalyst::new("quiet_room"), Catalyst::new("rested")],
        vec![Inhibitor::new("time_pressure")],
    );
    let recipe = Recipe::with_leakages_and_conditions(
        ProductionTarget::new("target"),
        vec![(PrimitiveId::drive(CoreDrive::F2Wisdom), 1.0)],
        vec![],
        conds,
    );
    assert_eq!(recipe.conditions.catalysts.len(), 2);
    assert_eq!(recipe.conditions.inhibitors.len(), 1);
    assert_eq!(recipe.conditions.catalysts[0].name, "quiet_room");
    assert_eq!(recipe.conditions.inhibitors[0].name, "time_pressure");
}

// ---------------------------------------------------------------------------
// Serde — JSON round-trip for all new types
// ---------------------------------------------------------------------------

#[test]
fn primitive_id_serde_round_trip_all_variants() {
    let cases = vec![
        PrimitiveId::noetic(CognitiveOperator::CO2),
        PrimitiveId::noetic_with_register(CognitiveOperator::CO3, Register::Affective),
        PrimitiveId::domain(Domain::Principled),
        PrimitiveId::domain_with_register(Domain::Cognitive, Register::Transcendent),
        PrimitiveId::drive(CoreDrive::F1Unity),
        PrimitiveId::drive_with_register(CoreDrive::F7Purpose, Register::Analytical),
        PrimitiveId::register(Register::Embodied),
        PrimitiveId::compound_with_register(
            CognitiveOperator::CO4,
            Domain::Evaluative,
            CoreDrive::F3Vitality,
            Register::Affective,
        ),
    ];
    for p in cases {
        let json = serde_json::to_string(&p).unwrap();
        let back: PrimitiveId = serde_json::from_str(&json).unwrap();
        assert_eq!(back, p, "round-trip failed for {}", p.canonical_notation());
    }
}

#[test]
fn recipe_full_serde_round_trip_preserves_leakages_and_conditions() {
    let p = PrimitiveId::drive(CoreDrive::F2Wisdom);
    let recipe = Recipe::with_leakages_and_conditions(
        ProductionTarget::new("paper"),
        vec![(p, 3.0)],
        vec![Leakage::new(p, "Ω_procrastination", 0.1)],
        Conditions::new(
            vec![Catalyst::new("deadline")],
            vec![Inhibitor::new("fatigue")],
        ),
    );
    let json = serde_json::to_string(&recipe).unwrap();
    let back: Recipe = serde_json::from_str(&json).unwrap();
    assert_eq!(back, recipe);
    assert_eq!(back.leakages.len(), 1);
    assert_eq!(back.conditions.catalysts.len(), 1);
    assert_eq!(back.conditions.inhibitors.len(), 1);
}

#[test]
fn state_vector_serde_round_trip() {
    use std::collections::HashMap;
    let p1 = PrimitiveId::drive(CoreDrive::F2Wisdom);
    let p2 = PrimitiveId::noetic_with_register(CognitiveOperator::CO2, Register::Analytical);
    let mut map = HashMap::new();
    map.insert(p1, 5.0);
    map.insert(p2, 3.0);
    let s = StateVector::new(map);
    let json = serde_json::to_string(&s).unwrap();
    let back: StateVector = serde_json::from_str(&json).unwrap();
    assert_eq!(back.quantity(&p1), 5.0);
    assert_eq!(back.quantity(&p2), 3.0);
}

#[test]
fn conditions_serde_round_trip() {
    let c = Conditions::new(
        vec![Catalyst::new("α"), Catalyst::new("β")],
        vec![Inhibitor::new("γ")],
    );
    let json = serde_json::to_string(&c).unwrap();
    let back: Conditions = serde_json::from_str(&json).unwrap();
    assert_eq!(back, c);
}

// ---------------------------------------------------------------------------
// StateVector — missing-primitive convention (Clarification 9 Section 2)
// ---------------------------------------------------------------------------

#[test]
fn state_vector_missing_primitive_returns_zero() {
    let s = StateVector::empty();
    assert_eq!(
        s.quantity(&PrimitiveId::drive(CoreDrive::F2Wisdom)),
        0.0,
        "per Clarification 9 Section 2, missing primitives are treated as xᵢ = 0"
    );
}

#[test]
fn state_vector_set_and_get() {
    let mut s = StateVector::empty();
    let p = PrimitiveId::drive(CoreDrive::F2Wisdom);
    s.set(p, 7.5);
    assert_eq!(s.quantity(&p), 7.5);
    assert_eq!(s.len(), 1);
    assert!(!s.is_empty());
}

// ---------------------------------------------------------------------------
// Backward compatibility — v7.4/v7.5 types remain importable and functional
// ---------------------------------------------------------------------------

#[test]
fn v75_register_type_unmodified_by_v76() {
    // All four Register values still present with canonical symbols.
    assert_eq!(Register::Transcendent.symbol(), "T");
    assert_eq!(Register::Analytical.symbol(), "A");
    assert_eq!(Register::Affective.symbol(), "f");
    assert_eq!(Register::Embodied.symbol(), "E");
}

#[test]
fn v75_cognitive_state_vector_type_unmodified_by_v76() {
    // The v7.4/v7.5 CognitiveStateVector remains usable and distinct from
    // the v7.6 ontology::recipe::StateVector.
    let v = CognitiveStateVector::uniform();
    assert!((v.probability_at(0) - 1.0 / 40.0).abs() < 1e-12);
}
