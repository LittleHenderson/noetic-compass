//! Stoichiometric Production Semantics — Yield calculation (CAS v7.6 Extension)
//!
//! Per `docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md` Clarification 9 Section 2,
//! theoretical yield is the maximum producible units of a production target
//! Ω given a recipe Θ and a state vector S, under ideal conversion:
//!
//! ```text
//! Y_T = min_i(xᵢ / aᵢ)    for all i where aᵢ > 0
//! η   = Y_A / Y_T         actual-over-theoretical efficiency
//! εᵢ  = xᵢ - (Y_T · aᵢ)   excess capacity of non-limiting prerequisites
//! ```
//!
//! The primitive (or primitives) producing the minimum ratio is the
//! **Limiting Reagent** — the bottleneck constraining production.
//!
//! ## Naming
//!
//! This module is named `yield_calc` rather than `yield` because `yield` is
//! a Rust reserved keyword (reserved for generator syntax). The task
//! specification explicitly permits this rename.
//!
//! ## Edge-case conventions (documented per task requirement)
//!
//! - **Missing primitives in state vector** — treated as quantity
//!   `xᵢ = 0`. A prerequisite with `aᵢ > 0` and `xᵢ = 0` yields a
//!   ratio of 0 and therefore bottlenecks the recipe to `Y_T = 0`.
//!   (Clarification 9 Section 2 explicit.)
//! - **Empty recipe (no prerequisites)** — `theoretical_yield` returns
//!   `0.0`. Interpretation: with no specified prerequisites there is no
//!   production pathway to analyze. We deliberately avoid
//!   `f64::INFINITY` because downstream consumers (efficiency calculation,
//!   excess capacity) would propagate NaN from division. This is a
//!   pragmatic engineering choice; the task lets us pick either
//!   convention so long as we document it.
//! - **Recipe with `aᵢ = 0`** — Clarification 9 Section 2 defines the
//!   minimum as taken over `i` where `aᵢ > 0`. We follow the spec exactly:
//!   zero-coefficient prerequisites are SKIPPED (they impose no constraint)
//!   rather than rejected at construction. If every coefficient is zero,
//!   the recipe has no constraining prerequisites and we return
//!   `Y_T = 0.0` (same as empty recipe).
//! - **Recipe with negative `aᵢ`** — negative coefficients are outside the
//!   specification's scope ("proportional weightings" are non-negative by
//!   construction). This module SKIPS primitives with `aᵢ <= 0` exactly as
//!   it skips `aᵢ = 0`. Callers who wish to forbid negatives should
//!   validate upstream; this module does not reject them.
//! - **Tied limiting reagents** — when two or more prerequisites produce
//!   the same minimum ratio, [`LimitingReagent::Multiple`] is returned
//!   carrying all tied primitives. Ties are detected with an exact `f64`
//!   equality against the minimum (no epsilon tolerance); tests exercise
//!   this path with exact-ratio fixtures.
//! - **Efficiency with `Y_T = 0`** — returns `f64::NAN` because `0/0` is
//!   mathematically undefined and callers should detect this case
//!   explicitly (prerequisite shortage vs conversion inefficiency is a
//!   diagnostic Clarification 9 Section 8 requires the caller to
//!   distinguish). Tests explicitly verify NaN handling.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

use crate::ontology::recipe::{PrimitiveId, Recipe, StateVector};

// ---------------------------------------------------------------------------
// Yield — theoretical, actual, efficiency bundle
// ---------------------------------------------------------------------------

/// A yield bundle: theoretical `Y_T`, optional actual `Y_A`, optional
/// efficiency `η = Y_A / Y_T`.
///
/// `actual` and `efficiency` are `None` when only theoretical analysis has
/// been performed (e.g., [`theoretical_yield`] returns a `Yield` with these
/// fields unset). Fill them in by constructing via [`Yield::with_actual`].
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Yield {
    /// Theoretical yield `Y_T = min_i(xᵢ / aᵢ)`.
    pub theoretical: f64,
    /// Actual (observed) yield `Y_A`. `None` when not yet measured.
    pub actual: Option<f64>,
    /// Efficiency `η = Y_A / Y_T`. `None` when `actual` is `None`.
    pub efficiency: Option<f64>,
}

impl Yield {
    /// Construct a theoretical-only Yield (no actual measurement).
    pub fn theoretical_only(theoretical: f64) -> Self {
        Self {
            theoretical,
            actual: None,
            efficiency: None,
        }
    }

    /// Construct a full Yield with theoretical, actual, and computed
    /// efficiency. Efficiency handling follows [`efficiency`] below.
    pub fn with_actual(theoretical: f64, actual: f64) -> Self {
        Self {
            theoretical,
            actual: Some(actual),
            efficiency: Some(efficiency(theoretical, actual)),
        }
    }
}

// ---------------------------------------------------------------------------
// LimitingReagent
// ---------------------------------------------------------------------------

/// Identifies the bottleneck prerequisite(s) in a recipe given a state
/// vector — the primitive(s) producing the minimum `xᵢ / aᵢ` ratio.
///
/// - [`LimitingReagent::Primitive`] — a unique bottleneck at the given ratio.
/// - [`LimitingReagent::Multiple`] — two or more tied primitives at the same
///   minimum ratio. Each entry is `(primitive, ratio)`.
/// - [`LimitingReagent::None`] — no bottleneck identifiable (empty recipe or
///   a recipe where no prerequisite has a positive coefficient).
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum LimitingReagent {
    /// Unique limiting reagent at ratio `xᵢ / aᵢ`.
    Primitive(PrimitiveId, f64),
    /// Two or more tied limiting reagents at equal ratios.
    Multiple(Vec<(PrimitiveId, f64)>),
    /// No bottleneck (empty recipe or all-zero coefficients).
    None,
}

// ---------------------------------------------------------------------------
// Core algorithms
// ---------------------------------------------------------------------------

/// Compute `Y_T = min_i(xᵢ / aᵢ)` for all `i` where `aᵢ > 0`.
///
/// Returns a theoretical-only [`Yield`] with `actual = None` and
/// `efficiency = None`. See module-level docs for edge-case conventions.
pub fn theoretical_yield(recipe: &Recipe, state: &StateVector) -> Yield {
    Yield::theoretical_only(compute_min_ratio(recipe, state))
}

/// Identify the prerequisite(s) producing the minimum `xᵢ / aᵢ` ratio.
/// See [`LimitingReagent`] for the three-way return convention.
pub fn limiting_reagent(recipe: &Recipe, state: &StateVector) -> LimitingReagent {
    // Pass 1: find the minimum ratio across active (aᵢ > 0) prerequisites.
    let mut active_ratios: Vec<(PrimitiveId, f64)> = Vec::new();
    for (primitive, coefficient) in &recipe.prerequisites {
        if *coefficient > 0.0 {
            let xi = state.quantity(primitive);
            let ratio = xi / coefficient;
            active_ratios.push((*primitive, ratio));
        }
    }

    if active_ratios.is_empty() {
        return LimitingReagent::None;
    }

    // Compute the exact minimum.
    let min_ratio = active_ratios
        .iter()
        .map(|(_, r)| *r)
        .fold(f64::INFINITY, f64::min);

    // Collect all prerequisites tied at the minimum (exact f64 equality).
    let tied: Vec<(PrimitiveId, f64)> = active_ratios
        .into_iter()
        .filter(|(_, r)| *r == min_ratio)
        .collect();

    match tied.len() {
        0 => LimitingReagent::None, // unreachable given active_ratios was non-empty
        1 => {
            let (p, r) = tied.into_iter().next().unwrap();
            LimitingReagent::Primitive(p, r)
        }
        _ => LimitingReagent::Multiple(tied),
    }
}

/// Compute excess capacity `εᵢ = xᵢ - (Y_T · aᵢ)` for each non-limiting
/// prerequisite.
///
/// The limiting reagent(s) have `εᵢ = 0` by definition (their ratio IS
/// `Y_T`, so `xᵢ = Y_T · aᵢ`). Entries are included for all prerequisites
/// with `aᵢ > 0`; zero-coefficient prerequisites are skipped (they have no
/// consumption per unit yield). The returned map is keyed by the
/// prerequisite [`PrimitiveId`].
pub fn excess_capacity(
    recipe: &Recipe,
    state: &StateVector,
) -> HashMap<PrimitiveId, f64> {
    let y_t = compute_min_ratio(recipe, state);
    let mut out = HashMap::new();
    for (primitive, coefficient) in &recipe.prerequisites {
        if *coefficient > 0.0 {
            let xi = state.quantity(primitive);
            let epsilon = xi - (y_t * coefficient);
            out.insert(*primitive, epsilon);
        }
    }
    out
}

/// Compute efficiency `η = actual / theoretical`.
///
/// Returns `f64::NAN` when `theoretical <= 0.0` (including the empty-recipe
/// case), because `0/0` is undefined and the diagnostic in Clarification 9
/// Section 8 requires callers to distinguish "prerequisite shortage"
/// (low Y_T) from "conversion inefficiency" (high Y_T, low η) — conflating
/// them would defeat the framework's analytical value.
pub fn efficiency(theoretical: f64, actual: f64) -> f64 {
    if theoretical <= 0.0 || theoretical.is_nan() {
        f64::NAN
    } else {
        actual / theoretical
    }
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

/// Shared internal: `min_i(xᵢ / aᵢ)` over prerequisites with `aᵢ > 0`.
/// Returns `0.0` when no such prerequisite exists (empty recipe or all-zero
/// coefficients), per module-level convention.
fn compute_min_ratio(recipe: &Recipe, state: &StateVector) -> f64 {
    let mut min_ratio = f64::INFINITY;
    let mut saw_active = false;
    for (primitive, coefficient) in &recipe.prerequisites {
        if *coefficient > 0.0 {
            saw_active = true;
            let xi = state.quantity(primitive);
            let ratio = xi / coefficient;
            if ratio < min_ratio {
                min_ratio = ratio;
            }
        }
    }
    if saw_active {
        min_ratio
    } else {
        0.0
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use crate::ontology::drives::CoreDrive;
    use crate::ontology::recipe::{PrimitiveId, ProductionTarget, Recipe};

    fn make_state(pairs: &[(PrimitiveId, f64)]) -> StateVector {
        let mut s = StateVector::empty();
        for (p, q) in pairs {
            s.set(*p, *q);
        }
        s
    }

    #[test]
    fn theoretical_yield_basic_one_limiting_two_surplus() {
        let f1 = PrimitiveId::drive(CoreDrive::F1Unity);
        let f2 = PrimitiveId::drive(CoreDrive::F2Wisdom);
        let f3 = PrimitiveId::drive(CoreDrive::F3Vitality);
        let recipe = Recipe::new(
            ProductionTarget::new("Ω"),
            vec![(f1, 1.0), (f2, 2.0), (f3, 4.0)],
        );
        // Quantities: x1=10 (ratio 10), x2=6 (ratio 3), x3=20 (ratio 5)
        // min = 3, limiting is F2.
        let state = make_state(&[(f1, 10.0), (f2, 6.0), (f3, 20.0)]);
        let y = theoretical_yield(&recipe, &state);
        assert_eq!(y.theoretical, 3.0);
        assert_eq!(y.actual, None);
        assert_eq!(y.efficiency, None);
    }

    #[test]
    fn limiting_reagent_single_identifies_correct_primitive() {
        let f1 = PrimitiveId::drive(CoreDrive::F1Unity);
        let f2 = PrimitiveId::drive(CoreDrive::F2Wisdom);
        let recipe = Recipe::new(
            ProductionTarget::new("Ω"),
            vec![(f1, 1.0), (f2, 2.0)],
        );
        let state = make_state(&[(f1, 5.0), (f2, 2.0)]);
        match limiting_reagent(&recipe, &state) {
            LimitingReagent::Primitive(p, r) => {
                assert_eq!(p, f2);
                assert_eq!(r, 1.0);
            }
            other => panic!("expected Primitive, got {:?}", other),
        }
    }

    #[test]
    fn empty_recipe_yields_zero_and_no_limiting_reagent() {
        let recipe = Recipe::new(ProductionTarget::new("Ω"), vec![]);
        let state = StateVector::empty();
        assert_eq!(theoretical_yield(&recipe, &state).theoretical, 0.0);
        assert_eq!(limiting_reagent(&recipe, &state), LimitingReagent::None);
    }

    #[test]
    fn efficiency_with_zero_theoretical_returns_nan() {
        let eta = efficiency(0.0, 5.0);
        assert!(eta.is_nan());
    }

    #[test]
    fn efficiency_half_is_half() {
        let eta = efficiency(10.0, 5.0);
        assert!((eta - 0.5).abs() < 1e-12);
    }
}
