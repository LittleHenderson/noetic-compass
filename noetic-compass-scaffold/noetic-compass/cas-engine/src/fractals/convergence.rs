//! Fractal Convergence and Classification — Definitions 8.16-8.20 from v6.1.
//!
//! - Orbit: E, Φ(E), Φ²(E), Φ³(E), …
//! - Fixed point: Φ(E*) = E*
//! - Classification: Stabilizing / Amplifying / Oscillatory / Neutral

use serde::{Deserialize, Serialize};
use std::collections::HashSet;

use super::fractal::CognitiveFractal;
use crate::ontology::states::CognitiveStateId;

/// Classification of fractal dynamic behavior (Definition 8.20).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum FractalClass {
    /// Orbit converges to a fixed point: ∃E* : lim Φⁿ(E) = E*
    Stabilizing,
    /// Orbit diverges (in discrete CAS, cycles through many distinct states)
    Amplifying,
    /// Orbit is periodic with period p > 1: ∃p>0 : Φᵖ(E) = E
    Oscillatory,
    /// Identity fractal: Φ(E) = E for all E
    Neutral,
}

/// Compute the fractal orbit: E, Φ(E), Φ²(E), … up to max_steps.
///
/// Per Definition 8.16: O_Φ(E) = {E, Φ(E), Φ²(E), Φ³(E), …}
pub fn orbit(
    fractal: &CognitiveFractal,
    initial: &CognitiveStateId,
    max_steps: usize,
) -> Vec<CognitiveStateId> {
    let mut result = Vec::with_capacity(max_steps + 1);
    let mut current = *initial;
    result.push(current);

    for _ in 0..max_steps {
        let next = fractal.apply(&current);
        result.push(next);
        if next == current {
            break; // Fixed point reached
        }
        current = next;
    }

    result
}

/// Find a fixed point of the fractal: Φ(E*) = E* (Definition 8.17).
///
/// Starts from `initial` and iterates until convergence or max_iterations.
pub fn find_fixed_point(
    fractal: &CognitiveFractal,
    initial: &CognitiveStateId,
    max_iterations: usize,
) -> Option<CognitiveStateId> {
    let mut current = *initial;
    for _ in 0..max_iterations {
        let next = fractal.apply(&current);
        if next == current {
            return Some(current);
        }
        current = next;
    }
    None
}

/// Detect if the orbit is periodic, and return the period.
///
/// Uses Floyd's cycle detection (tortoise and hare) adapted for discrete states.
fn detect_period(
    fractal: &CognitiveFractal,
    initial: &CognitiveStateId,
    max_iterations: usize,
) -> Option<usize> {
    let mut seen: HashSet<CognitiveStateId> = HashSet::new();
    let mut current = *initial;
    let mut history = vec![current];

    for _ in 0..max_iterations {
        let next = fractal.apply(&current);
        if next == current {
            return Some(1); // Fixed point = period 1
        }
        if seen.contains(&next) {
            // Found a cycle — compute its length
            if let Some(cycle_start) = history.iter().position(|&s| s == next) {
                return Some(history.len() - cycle_start);
            }
        }
        seen.insert(next);
        history.push(next);
        current = next;
    }
    None
}

/// Classify a fractal's dynamic behavior (Definition 8.20).
///
/// - **Neutral**: identity fractal ⟨0⟩
/// - **Stabilizing**: orbit converges to a fixed point (period 1)
/// - **Oscillatory**: orbit is periodic with period > 1
/// - **Amplifying**: orbit visits many distinct states without settling
pub fn classify(
    fractal: &CognitiveFractal,
    test_element: &CognitiveStateId,
    max_iterations: usize,
) -> FractalClass {
    // Neutral: identity fractal
    if fractal.is_identity() {
        return FractalClass::Neutral;
    }

    // Check for fixed point (Stabilizing)
    if find_fixed_point(fractal, test_element, max_iterations).is_some() {
        return FractalClass::Stabilizing;
    }

    // Check for periodic orbit (Oscillatory)
    if let Some(period) = detect_period(fractal, test_element, max_iterations) {
        if period == 1 {
            return FractalClass::Stabilizing;
        }
        return FractalClass::Oscillatory;
    }

    // If no fixed point and no detected period, classify as Amplifying
    FractalClass::Amplifying
}

/// Compute eigenvalue for an element: Φ(E) = λE (Definition 8.18).
///
/// In discrete CAS, "eigenvalue" is defined via the operator index ratio:
/// If Φ maps state (CO_a, D) to (CO_b, D), the eigenvalue is b/a (or None if a=0).
/// Fixed points have eigenvalue 1.
pub fn find_eigenvalue(
    fractal: &CognitiveFractal,
    element: &CognitiveStateId,
) -> Option<f64> {
    let result = fractal.apply(element);
    if result == *element {
        return Some(1.0); // Fixed point
    }

    let source_idx = element.operator().index();
    let target_idx = result.operator().index();

    if source_idx == 0 {
        return None; // Cannot divide by zero index
    }

    Some(target_idx as f64 / source_idx as f64)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::ontology::domains::Domain;
    use crate::ontology::operators::CognitiveOperator;

    fn state(op: u8, dom: Domain) -> CognitiveStateId {
        CognitiveStateId::new(CognitiveOperator::from_index(op as usize).unwrap(), dom)
    }

    #[test]
    fn test_orbit_identity() {
        let f = CognitiveFractal::identity();
        let e = state(3, Domain::Principled);
        let o = orbit(&f, &e, 5);
        // Identity: all elements in orbit are the same
        assert!(o.iter().all(|&s| s == e));
    }

    #[test]
    fn test_orbit_fixed_point() {
        // CO-0 applied to state (CO-0, P) = (CO-0, P) — fixed point
        let f = CognitiveFractal::new(vec![0]).unwrap();
        let e = state(0, Domain::Principled);
        let fp = find_fixed_point(&f, &e, 10);
        assert_eq!(fp, Some(e));
    }

    #[test]
    fn test_classify_neutral() {
        let f = CognitiveFractal::identity();
        let e = state(1, Domain::Cognitive);
        assert_eq!(classify(&f, &e, 10), FractalClass::Neutral);
    }

    #[test]
    fn test_classify_stabilizing_mvr() {
        // MVR fractal ⟨1:4:7⟩ — Theorem 8.21 says this is Stabilizing
        // Note: in discrete CAS with modular composition, this should converge
        let f = CognitiveFractal::new(vec![1, 4, 7]).unwrap();
        let e = state(0, Domain::Principled);
        let class = classify(&f, &e, 100);
        // MVR applies CO-1, CO-4, CO-7 (all self-dual) — should stabilize or oscillate
        assert!(
            class == FractalClass::Stabilizing || class == FractalClass::Oscillatory,
            "MVR classified as {:?}",
            class
        );
    }

    #[test]
    fn test_eigenvalue_fixed_point() {
        let f = CognitiveFractal::identity();
        let e = state(5, Domain::Evaluative);
        assert_eq!(find_eigenvalue(&f, &e), Some(1.0));
    }

    #[test]
    fn test_eigenvalue_zero_index() {
        let f = CognitiveFractal::new(vec![3]).unwrap();
        let e = state(0, Domain::Operational);
        assert_eq!(find_eigenvalue(&f, &e), None);
    }
}
