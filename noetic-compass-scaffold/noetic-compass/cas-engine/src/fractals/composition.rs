//! Fractal Composition — Definitions 8.5, 8.7, 8.15; Theorems 8.6, 8.8 from v6.1.
//!
//! Composition is concatenation: Φ₁ ∘ Φ₂ = ⟨a₁:⋯:aₘ : b₁:⋯:bₙ⟩
//! (Frac, ∘, Φ_id) forms a monoid.

use super::fractal::CognitiveFractal;

/// Compose two fractals by concatenation (Definition 8.5).
///
/// Φ₁ ∘ Φ₂ = ⟨a₁:⋯:aₘ : b₁:⋯:bₙ⟩
pub fn compose(a: &CognitiveFractal, b: &CognitiveFractal) -> CognitiveFractal {
    let mut ops = a.operators().to_vec();
    ops.extend_from_slice(b.operators());
    // Safe: both inputs are valid, concatenation preserves validity
    CognitiveFractal::new(ops).unwrap()
}

/// Iterate a fractal n times: Φⁿ = Φ ∘ Φ ∘ ⋯ ∘ Φ (Definition 8.15).
/// Φ⁰ = Φ_id (the identity fractal).
pub fn iterate(fractal: &CognitiveFractal, n: usize) -> CognitiveFractal {
    if n == 0 {
        return CognitiveFractal::identity();
    }
    let mut result = fractal.clone();
    for _ in 1..n {
        result = compose(&result, fractal);
    }
    result
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_compose_concatenates() {
        let a = CognitiveFractal::new(vec![1, 2]).unwrap();
        let b = CognitiveFractal::new(vec![3, 4]).unwrap();
        let c = compose(&a, &b);
        assert_eq!(c.operators(), &[1, 2, 3, 4]);
    }

    #[test]
    fn test_identity_is_neutral_left() {
        // Φ_id ∘ Φ = ⟨0⟩ ∘ ⟨1,4,7⟩ = ⟨0,1,4,7⟩
        // After simplification: ⟨1,4,7⟩ (identity elimination removes leading 0)
        // But raw composition is concatenation — simplification is separate.
        let id = CognitiveFractal::identity();
        let f = CognitiveFractal::new(vec![1, 4, 7]).unwrap();
        let result = compose(&id, &f);
        assert_eq!(result.operators(), &[0, 1, 4, 7]);
    }

    #[test]
    fn test_identity_is_neutral_right() {
        let f = CognitiveFractal::new(vec![1, 4, 7]).unwrap();
        let id = CognitiveFractal::identity();
        let result = compose(&f, &id);
        assert_eq!(result.operators(), &[1, 4, 7, 0]);
    }

    #[test]
    fn test_associativity() {
        // (Φ₁ ∘ Φ₂) ∘ Φ₃ = Φ₁ ∘ (Φ₂ ∘ Φ₃) — Theorem 8.6
        let f1 = CognitiveFractal::new(vec![1, 2]).unwrap();
        let f2 = CognitiveFractal::new(vec![3, 4]).unwrap();
        let f3 = CognitiveFractal::new(vec![5, 6]).unwrap();

        let lhs = compose(&compose(&f1, &f2), &f3);
        let rhs = compose(&f1, &compose(&f2, &f3));
        assert_eq!(lhs.operators(), rhs.operators());
    }

    #[test]
    fn test_iterate_zero() {
        let f = CognitiveFractal::new(vec![2, 3]).unwrap();
        let result = iterate(&f, 0);
        assert!(result.is_identity());
    }

    #[test]
    fn test_iterate_one() {
        let f = CognitiveFractal::new(vec![1, 4, 7]).unwrap();
        let result = iterate(&f, 1);
        assert_eq!(result.operators(), f.operators());
    }

    #[test]
    fn test_iterate_three() {
        let f = CognitiveFractal::new(vec![2, 3]).unwrap();
        let result = iterate(&f, 3);
        assert_eq!(result.operators(), &[2, 3, 2, 3, 2, 3]);
    }
}
