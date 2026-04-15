//! Fractal Simplification — Definitions 8.9-8.11, Theorem 8.12 from v6.1.
//!
//! Dual cancellation rules (Definition 8.9):
//!   ⟨⋯ : 2 : 3 : ⋯⟩ ⇒ ⟨⋯ : 0 : ⋯⟩  (CO-2/CO-3 involution)
//!   ⟨⋯ : 3 : 2 : ⋯⟩ ⇒ ⟨⋯ : 0 : ⋯⟩
//!   ⟨⋯ : 5 : 6 : ⋯⟩ ⇒ ⟨⋯ : 0 : ⋯⟩  (CO-5/CO-6 involution)
//!   ⟨⋯ : 6 : 5 : ⋯⟩ ⇒ ⟨⋯ : 0 : ⋯⟩
//!   ⟨⋯ : 8 : 9 : ⋯⟩ ⇒ ⟨⋯ : 0 : ⋯⟩  (CO-8/CO-9 involution)
//!   ⟨⋯ : 9 : 8 : ⋯⟩ ⇒ ⟨⋯ : 0 : ⋯⟩
//!
//! Identity elimination (Definition 8.10):
//!   Remove interior zeros (unless it's the sole element).
//!
//! Canonical form (Definition 8.11): no adjacent dual pairs, no interior zeros.
//! Theorem 8.12: Every fractal has a unique canonical form (confluence + termination).

use super::fractal::CognitiveFractal;

/// The three involution pairs as (a, b) tuples.
const INVOLUTION_PAIRS: [(u8, u8); 3] = [(2, 3), (5, 6), (8, 9)];

/// Check if two adjacent operators form a dual (involution) pair.
fn is_dual_pair(a: u8, b: u8) -> bool {
    INVOLUTION_PAIRS
        .iter()
        .any(|&(x, y)| (a == x && b == y) || (a == y && b == x))
}

/// Apply one pass of dual cancellation.
/// Returns the number of cancellations applied.
fn cancel_duals_pass(ops: &mut Vec<u8>) -> usize {
    let mut cancellations = 0;
    let mut i = 0;
    while i + 1 < ops.len() {
        if is_dual_pair(ops[i], ops[i + 1]) {
            // Replace dual pair with identity (0)
            ops[i] = 0;
            ops.remove(i + 1);
            cancellations += 1;
            // Don't advance i — the new 0 might cancel with its new neighbor
            // Actually, 0 doesn't form dual pairs, so we can advance
        } else {
            i += 1;
        }
    }
    cancellations
}

/// Remove interior zeros (Definition 8.10).
/// Zeros are removed unless the sequence would become empty.
fn eliminate_identities(ops: &mut Vec<u8>) {
    if ops.len() <= 1 {
        return;
    }
    ops.retain(|&op| op != 0);
    if ops.is_empty() {
        ops.push(0); // Preserve at least ⟨0⟩
    }
}

/// Count the number of dual cancellations in a fractal (useful for analysis).
pub fn count_cancellations(fractal: &CognitiveFractal) -> usize {
    let mut ops = fractal.operators().to_vec();
    let mut total = 0;
    loop {
        let n = cancel_duals_pass(&mut ops);
        if n == 0 {
            break;
        }
        total += n;
    }
    total
}

/// Reduce a fractal to its unique canonical form (Definition 8.11, Theorem 8.12).
///
/// Repeatedly applies:
/// 1. Dual cancellation (involution pairs → identity)
/// 2. Identity elimination (remove interior zeros)
///
/// Confluence is guaranteed by Newman's lemma: the rules are locally confluent
/// and terminating (each rule reduces sequence length).
pub fn canonicalize(fractal: &mut CognitiveFractal) {
    let ops = fractal.operators_mut();

    loop {
        let cancellations = cancel_duals_pass(ops);
        let len_before = ops.len();
        eliminate_identities(ops);
        let len_after = ops.len();

        // Fixed point: no more reductions possible
        if cancellations == 0 && len_before == len_after {
            break;
        }
    }
}

/// Check if a fractal is already in canonical form.
pub fn is_canonical(fractal: &CognitiveFractal) -> bool {
    let ops = fractal.operators();

    // Check no adjacent dual pairs
    for i in 0..ops.len().saturating_sub(1) {
        if is_dual_pair(ops[i], ops[i + 1]) {
            return false;
        }
    }

    // Check no interior zeros (only ⟨0⟩ itself is allowed)
    if ops.len() > 1 && ops.iter().any(|&op| op == 0) {
        return false;
    }

    true
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_dual_pair_detection() {
        assert!(is_dual_pair(2, 3));
        assert!(is_dual_pair(3, 2));
        assert!(is_dual_pair(5, 6));
        assert!(is_dual_pair(6, 5));
        assert!(is_dual_pair(8, 9));
        assert!(is_dual_pair(9, 8));
        assert!(!is_dual_pair(1, 2));
        assert!(!is_dual_pair(0, 0));
        assert!(!is_dual_pair(2, 5));
    }

    #[test]
    fn test_cancel_co2_co3() {
        let mut f = CognitiveFractal::new(vec![1, 2, 3, 4]).unwrap();
        canonicalize(&mut f);
        assert_eq!(f.operators(), &[1, 4]);
    }

    #[test]
    fn test_cancel_co3_co2() {
        let mut f = CognitiveFractal::new(vec![3, 2]).unwrap();
        canonicalize(&mut f);
        assert!(f.is_identity());
    }

    #[test]
    fn test_cancel_co5_co6() {
        let mut f = CognitiveFractal::new(vec![5, 6]).unwrap();
        canonicalize(&mut f);
        assert!(f.is_identity());
    }

    #[test]
    fn test_cancel_co8_co9() {
        let mut f = CognitiveFractal::new(vec![1, 8, 9, 7]).unwrap();
        canonicalize(&mut f);
        assert_eq!(f.operators(), &[1, 7]);
    }

    #[test]
    fn test_multiple_cancellations() {
        // ⟨2 : 3 : 5 : 6⟩ → ⟨0 : 0⟩ → ⟨0⟩
        let mut f = CognitiveFractal::new(vec![2, 3, 5, 6]).unwrap();
        canonicalize(&mut f);
        assert!(f.is_identity());
    }

    #[test]
    fn test_identity_elimination() {
        let mut f = CognitiveFractal::new(vec![1, 0, 4]).unwrap();
        canonicalize(&mut f);
        assert_eq!(f.operators(), &[1, 4]);
    }

    #[test]
    fn test_sole_identity_preserved() {
        let mut f = CognitiveFractal::identity();
        canonicalize(&mut f);
        assert!(f.is_identity());
    }

    #[test]
    fn test_already_canonical() {
        let f = CognitiveFractal::new(vec![1, 4, 7]).unwrap();
        assert!(is_canonical(&f));
    }

    #[test]
    fn test_not_canonical_dual_pair() {
        let f = CognitiveFractal::new(vec![2, 3]).unwrap();
        assert!(!is_canonical(&f));
    }

    #[test]
    fn test_not_canonical_interior_zero() {
        let f = CognitiveFractal::new(vec![1, 0, 4]).unwrap();
        assert!(!is_canonical(&f));
    }

    #[test]
    fn test_count_cancellations() {
        let f = CognitiveFractal::new(vec![2, 3, 5, 6, 8, 9]).unwrap();
        assert_eq!(count_cancellations(&f), 3);
    }

    #[test]
    fn test_polarity_fractal() {
        // Theorem 8.22: ⟨2:3⟩ ∘ ⟨2:3⟩ = ⟨2:3:2:3⟩ → ⟨0:0⟩ → ⟨0⟩
        let f = CognitiveFractal::new(vec![2, 3]).unwrap();
        let f2 = super::super::composition::compose(&f, &f);
        let mut f2_canonical = f2;
        canonicalize(&mut f2_canonical);
        assert!(f2_canonical.is_identity());
    }
}
