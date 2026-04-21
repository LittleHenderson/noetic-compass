//! Integration tests for the CAS v7.6 Stoichiometric Production Semantics
//! yield-calculation algorithms per Clarification 9 Section 2.
//!
//! Covers:
//! - `theoretical_yield` basic case (unique limiting reagent + surplus).
//! - `theoretical_yield` with tied limiting reagents.
//! - `limiting_reagent` single vs Multiple vs None.
//! - `excess_capacity` non-zero for non-limiting, zero for limiting.
//! - `efficiency` including η=1.0, η=0.5, η near 0, and Y_T=0 (NaN).
//! - Empty-recipe edge case.
//! - Missing primitives in state vector treated as quantity 0.

use cas_engine::ontology::{
    CognitiveOperator, CoreDrive, Domain, PrimitiveId, ProductionTarget, Recipe, Register,
    StateVector,
};
use cas_engine::scoring::yield_calc::{
    efficiency, excess_capacity, limiting_reagent, theoretical_yield, LimitingReagent, Yield,
};

fn state_from(pairs: &[(PrimitiveId, f64)]) -> StateVector {
    let mut s = StateVector::empty();
    for (p, q) in pairs {
        s.set(*p, *q);
    }
    s
}

// ---------------------------------------------------------------------------
// theoretical_yield — basic cases
// ---------------------------------------------------------------------------

#[test]
fn theoretical_yield_unique_limiting_plus_two_surplus() {
    let f1 = PrimitiveId::drive(CoreDrive::F1Unity);
    let f2 = PrimitiveId::drive(CoreDrive::F2Wisdom);
    let f3 = PrimitiveId::drive(CoreDrive::F3Vitality);
    let recipe = Recipe::new(
        ProductionTarget::new("Ω"),
        vec![(f1, 1.0), (f2, 2.0), (f3, 4.0)],
    );
    // Quantities: x1=10 (ratio 10), x2=6 (ratio 3), x3=20 (ratio 5)
    // min ratio is 3 via F2.
    let state = state_from(&[(f1, 10.0), (f2, 6.0), (f3, 20.0)]);
    let y = theoretical_yield(&recipe, &state);
    assert_eq!(y.theoretical, 3.0);
    assert_eq!(y.actual, None);
    assert_eq!(y.efficiency, None);
}

#[test]
fn theoretical_yield_all_surplus_uses_minimum_primitive() {
    // Three prerequisites, each with ratio > 0; minimum still determines Y_T.
    let f1 = PrimitiveId::drive(CoreDrive::F1Unity);
    let f2 = PrimitiveId::drive(CoreDrive::F2Wisdom);
    let recipe = Recipe::new(ProductionTarget::new("Ω"), vec![(f1, 2.0), (f2, 2.0)]);
    let state = state_from(&[(f1, 100.0), (f2, 50.0)]);
    let y = theoretical_yield(&recipe, &state);
    // x/a for f1 = 50, for f2 = 25 → min = 25.
    assert_eq!(y.theoretical, 25.0);
}

#[test]
fn theoretical_yield_with_tied_limiting_reagents() {
    // Two prerequisites at exactly the same minimum ratio.
    let f1 = PrimitiveId::drive(CoreDrive::F1Unity);
    let f2 = PrimitiveId::drive(CoreDrive::F2Wisdom);
    let f3 = PrimitiveId::drive(CoreDrive::F3Vitality);
    let recipe = Recipe::new(
        ProductionTarget::new("Ω"),
        vec![(f1, 1.0), (f2, 2.0), (f3, 1.0)],
    );
    // x1/1 = 4, x2/2 = 4 (tied), x3/1 = 10 (surplus) → Y_T = 4.
    let state = state_from(&[(f1, 4.0), (f2, 8.0), (f3, 10.0)]);
    assert_eq!(theoretical_yield(&recipe, &state).theoretical, 4.0);
}

// ---------------------------------------------------------------------------
// limiting_reagent — three-way variant correctness
// ---------------------------------------------------------------------------

#[test]
fn limiting_reagent_single() {
    let f1 = PrimitiveId::drive(CoreDrive::F1Unity);
    let f2 = PrimitiveId::drive(CoreDrive::F2Wisdom);
    let recipe = Recipe::new(ProductionTarget::new("Ω"), vec![(f1, 1.0), (f2, 2.0)]);
    let state = state_from(&[(f1, 10.0), (f2, 2.0)]);
    match limiting_reagent(&recipe, &state) {
        LimitingReagent::Primitive(p, r) => {
            assert_eq!(p, f2);
            assert_eq!(r, 1.0);
        }
        other => panic!("expected Primitive, got {:?}", other),
    }
}

#[test]
fn limiting_reagent_multiple_when_two_primitives_tie() {
    let f1 = PrimitiveId::drive(CoreDrive::F1Unity);
    let f2 = PrimitiveId::drive(CoreDrive::F2Wisdom);
    let f3 = PrimitiveId::drive(CoreDrive::F3Vitality);
    let recipe = Recipe::new(
        ProductionTarget::new("Ω"),
        vec![(f1, 1.0), (f2, 2.0), (f3, 1.0)],
    );
    // x1/1 = 4, x2/2 = 4, x3/1 = 10 → f1 and f2 tied at ratio 4.
    let state = state_from(&[(f1, 4.0), (f2, 8.0), (f3, 10.0)]);
    match limiting_reagent(&recipe, &state) {
        LimitingReagent::Multiple(v) => {
            assert_eq!(v.len(), 2);
            let ids: Vec<PrimitiveId> = v.iter().map(|(p, _)| *p).collect();
            assert!(ids.contains(&f1));
            assert!(ids.contains(&f2));
            assert!(!ids.contains(&f3));
            for (_, r) in &v {
                assert_eq!(*r, 4.0);
            }
        }
        other => panic!("expected Multiple, got {:?}", other),
    }
}

#[test]
fn limiting_reagent_none_for_empty_recipe() {
    let recipe = Recipe::new(ProductionTarget::new("Ω"), vec![]);
    let state = StateVector::empty();
    assert_eq!(limiting_reagent(&recipe, &state), LimitingReagent::None);
}

#[test]
fn limiting_reagent_none_when_all_coefficients_zero() {
    // Every aᵢ = 0 → no active prerequisite → None.
    let f1 = PrimitiveId::drive(CoreDrive::F1Unity);
    let recipe = Recipe::new(ProductionTarget::new("Ω"), vec![(f1, 0.0)]);
    let state = state_from(&[(f1, 10.0)]);
    assert_eq!(limiting_reagent(&recipe, &state), LimitingReagent::None);
}

#[test]
fn limiting_reagent_identifies_zero_stock_bottleneck() {
    // State-vector quantity 0 yields ratio 0 and bottlenecks Y_T to 0.
    let f1 = PrimitiveId::drive(CoreDrive::F1Unity);
    let f2 = PrimitiveId::drive(CoreDrive::F2Wisdom);
    let recipe = Recipe::new(ProductionTarget::new("Ω"), vec![(f1, 1.0), (f2, 1.0)]);
    // Only set f1; f2 missing → treated as 0.
    let state = state_from(&[(f1, 10.0)]);
    assert_eq!(theoretical_yield(&recipe, &state).theoretical, 0.0);
    match limiting_reagent(&recipe, &state) {
        LimitingReagent::Primitive(p, r) => {
            assert_eq!(p, f2);
            assert_eq!(r, 0.0);
        }
        other => panic!("expected Primitive(f2, 0.0), got {:?}", other),
    }
}

// ---------------------------------------------------------------------------
// excess_capacity — Clarification 9 Section 2
// ---------------------------------------------------------------------------

#[test]
fn excess_capacity_zero_for_limiting_reagent_nonzero_for_surplus() {
    let f1 = PrimitiveId::drive(CoreDrive::F1Unity);
    let f2 = PrimitiveId::drive(CoreDrive::F2Wisdom);
    let f3 = PrimitiveId::drive(CoreDrive::F3Vitality);
    let recipe = Recipe::new(
        ProductionTarget::new("Ω"),
        vec![(f1, 1.0), (f2, 2.0), (f3, 4.0)],
    );
    let state = state_from(&[(f1, 10.0), (f2, 6.0), (f3, 20.0)]);
    // Y_T = 3, via f2. ε_f1 = 10 - 3·1 = 7; ε_f2 = 6 - 3·2 = 0; ε_f3 = 20 - 3·4 = 8.
    let eps = excess_capacity(&recipe, &state);
    assert_eq!(eps.get(&f1).copied(), Some(7.0));
    assert_eq!(eps.get(&f2).copied(), Some(0.0));
    assert_eq!(eps.get(&f3).copied(), Some(8.0));
}

#[test]
fn excess_capacity_skips_zero_coefficient_prerequisites() {
    let f1 = PrimitiveId::drive(CoreDrive::F1Unity);
    let f2 = PrimitiveId::drive(CoreDrive::F2Wisdom);
    let recipe = Recipe::new(ProductionTarget::new("Ω"), vec![(f1, 1.0), (f2, 0.0)]);
    let state = state_from(&[(f1, 5.0), (f2, 99.0)]);
    let eps = excess_capacity(&recipe, &state);
    assert!(eps.contains_key(&f1));
    assert!(
        !eps.contains_key(&f2),
        "zero-coefficient prerequisites must be skipped per module convention"
    );
}

#[test]
fn excess_capacity_empty_recipe_returns_empty_map() {
    let recipe = Recipe::new(ProductionTarget::new("Ω"), vec![]);
    let state = StateVector::empty();
    let eps = excess_capacity(&recipe, &state);
    assert!(eps.is_empty());
}

// ---------------------------------------------------------------------------
// efficiency
// ---------------------------------------------------------------------------

#[test]
fn efficiency_exact_one() {
    assert_eq!(efficiency(10.0, 10.0), 1.0);
}

#[test]
fn efficiency_exact_half() {
    assert!((efficiency(10.0, 5.0) - 0.5).abs() < 1e-12);
}

#[test]
fn efficiency_near_zero() {
    let eta = efficiency(100.0, 0.001);
    assert!(eta > 0.0 && eta < 1e-4);
}

#[test]
fn efficiency_zero_theoretical_returns_nan() {
    assert!(efficiency(0.0, 5.0).is_nan());
}

#[test]
fn efficiency_negative_theoretical_returns_nan() {
    // Module policy: Y_T <= 0 → NaN (engineering defensiveness; Y_T is
    // always non-negative by definition, but robustness matters).
    assert!(efficiency(-1.0, 5.0).is_nan());
}

// ---------------------------------------------------------------------------
// Yield constructor helpers
// ---------------------------------------------------------------------------

#[test]
fn yield_with_actual_computes_efficiency() {
    let y = Yield::with_actual(10.0, 7.5);
    assert_eq!(y.theoretical, 10.0);
    assert_eq!(y.actual, Some(7.5));
    assert_eq!(y.efficiency, Some(0.75));
}

#[test]
fn yield_with_actual_zero_theoretical_gives_nan_efficiency() {
    let y = Yield::with_actual(0.0, 5.0);
    assert!(y.efficiency.unwrap().is_nan());
}

// ---------------------------------------------------------------------------
// Mixed-primitive yield — exercises PrimitiveId variants end-to-end
// ---------------------------------------------------------------------------

#[test]
fn yield_works_across_all_primitive_variants() {
    // Noetic, Domain, Drive, Register, Compound — all addressable as
    // recipe prerequisites and yield-calculable uniformly.
    let noetic = PrimitiveId::noetic(CognitiveOperator::CO2);
    let domain = PrimitiveId::domain(Domain::Cognitive);
    let drive = PrimitiveId::drive(CoreDrive::F2Wisdom);
    let register = PrimitiveId::register(Register::Analytical);
    let compound = PrimitiveId::compound_with_register(
        CognitiveOperator::CO7,
        Domain::Operational,
        CoreDrive::F6Structure,
        Register::Embodied,
    );
    let recipe = Recipe::new(
        ProductionTarget::new("Ω_multi"),
        vec![
            (noetic, 1.0),
            (domain, 2.0),
            (drive, 3.0),
            (register, 4.0),
            (compound, 1.0),
        ],
    );
    // Stock each at 12 → ratios: 12, 6, 4, 3, 12. Min = 3 via register.
    let state = state_from(&[
        (noetic, 12.0),
        (domain, 12.0),
        (drive, 12.0),
        (register, 12.0),
        (compound, 12.0),
    ]);
    let y = theoretical_yield(&recipe, &state);
    assert_eq!(y.theoretical, 3.0);
    match limiting_reagent(&recipe, &state) {
        LimitingReagent::Primitive(p, r) => {
            assert_eq!(p, register);
            assert_eq!(r, 3.0);
        }
        other => panic!("expected Primitive(register, 3.0), got {:?}", other),
    }
}
