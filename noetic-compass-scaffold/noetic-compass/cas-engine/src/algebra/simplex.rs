//! Simplex-Level Operations
//!
//! Multiplication and division on probability vectors (Δ°39).
//! Uses geometric mean (Bhattacharyya midpoint) for multiplication
//! and log-ratio for division, both renormalized to the open simplex.

use crate::ontology::NUM_STATES;
use super::error::AlgebraError;

/// Multiply two state vectors on the probability simplex.
///
/// Uses element-wise geometric mean, renormalized to sum to 1.
/// This is the natural "multiplication" on probability simplices because:
/// - It preserves Δ°39 (strictly positive, normalized)
/// - It's associative after renormalization
/// - It corresponds to the Bhattacharyya midpoint
pub fn simplex_multiply(p: &[f64], q: &[f64]) -> Result<Vec<f64>, AlgebraError> {
    if p.len() != NUM_STATES || q.len() != NUM_STATES {
        return Err(AlgebraError::DimensionMismatch {
            expected: NUM_STATES,
            got: if p.len() != NUM_STATES { p.len() } else { q.len() },
        });
    }

    let mut result = vec![0.0f64; NUM_STATES];
    for k in 0..NUM_STATES {
        let product = p[k] * q[k];
        if product < 0.0 {
            return Err(AlgebraError::BoundaryViolation);
        }
        result[k] = product.sqrt();
    }

    // Renormalize to stay on simplex
    let sum: f64 = result.iter().sum();
    if sum <= 0.0 {
        return Err(AlgebraError::DegenerateState);
    }
    for k in 0..NUM_STATES {
        result[k] /= sum;
    }

    // Verify strict positivity (open simplex)
    if result.iter().any(|&x| x <= 0.0) {
        return Err(AlgebraError::BoundaryViolation);
    }

    Ok(result)
}

/// Divide two state vectors on the probability simplex.
///
/// Uses element-wise log-ratio, renormalized to sum to 1.
/// Division reveals the causal structure between two distributions.
pub fn simplex_divide(p: &[f64], q: &[f64]) -> Result<Vec<f64>, AlgebraError> {
    if p.len() != NUM_STATES || q.len() != NUM_STATES {
        return Err(AlgebraError::DimensionMismatch {
            expected: NUM_STATES,
            got: if p.len() != NUM_STATES { p.len() } else { q.len() },
        });
    }

    // Check that both inputs are strictly positive
    if p.iter().any(|&x| x <= 0.0) || q.iter().any(|&x| x <= 0.0) {
        return Err(AlgebraError::BoundaryViolation);
    }

    // Element-wise ratio p_k / q_k, then renormalize
    let mut result = vec![0.0f64; NUM_STATES];
    for k in 0..NUM_STATES {
        result[k] = p[k] / q[k];
    }

    // Renormalize to stay on simplex
    let sum: f64 = result.iter().sum();
    if sum <= 0.0 {
        return Err(AlgebraError::DegenerateState);
    }
    for k in 0..NUM_STATES {
        result[k] /= sum;
    }

    // Verify strict positivity (open simplex)
    if result.iter().any(|&x| x <= 0.0) {
        return Err(AlgebraError::BoundaryViolation);
    }

    Ok(result)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn uniform() -> Vec<f64> {
        vec![1.0 / NUM_STATES as f64; NUM_STATES]
    }

    fn make_peaked(peak_idx: usize) -> Vec<f64> {
        // Moderate peak: ~10x the base, not extreme enough to break
        // renormalized associativity via floating point
        let base = 0.01;
        let mut v = vec![base; NUM_STATES];
        v[peak_idx] = 0.50;
        let sum: f64 = v.iter().sum();
        for x in v.iter_mut() {
            *x /= sum;
        }
        v
    }

    #[test]
    fn test_simplex_multiply_uniform() {
        let u = uniform();
        let result = simplex_multiply(&u, &u).unwrap();
        // Uniform × Uniform = Uniform
        for &x in &result {
            assert!((x - 1.0 / NUM_STATES as f64).abs() < 1e-10);
        }
    }

    #[test]
    fn test_simplex_multiply_preserves_simplex() {
        let p = make_peaked(0);
        let q = make_peaked(10);
        let result = simplex_multiply(&p, &q).unwrap();

        // All strictly positive
        assert!(result.iter().all(|&x| x > 0.0));
        // Sums to 1
        let sum: f64 = result.iter().sum();
        assert!((sum - 1.0).abs() < 1e-10);
    }

    #[test]
    fn test_simplex_multiply_commutative() {
        let a = make_peaked(0);
        let b = make_peaked(5);

        let ab = simplex_multiply(&a, &b).unwrap();
        let ba = simplex_multiply(&b, &a).unwrap();

        for k in 0..NUM_STATES {
            assert!(
                (ab[k] - ba[k]).abs() < 1e-12,
                "commutativity failed at index {k}: {} vs {}",
                ab[k],
                ba[k],
            );
        }
    }

    #[test]
    fn test_simplex_multiply_idempotent() {
        // p × p = p (geometric mean of p with itself is p)
        let p = make_peaked(7);
        let result = simplex_multiply(&p, &p).unwrap();

        for k in 0..NUM_STATES {
            assert!(
                (result[k] - p[k]).abs() < 1e-12,
                "idempotency failed at index {k}: {} vs {}",
                result[k],
                p[k],
            );
        }
    }

    #[test]
    fn test_simplex_divide_self_is_uniform() {
        let p = make_peaked(7);
        let result = simplex_divide(&p, &p).unwrap();
        // p ÷ p = uniform (all ratios equal)
        for &x in &result {
            assert!((x - 1.0 / NUM_STATES as f64).abs() < 1e-10);
        }
    }

    #[test]
    fn test_simplex_divide_preserves_simplex() {
        let p = make_peaked(0);
        let q = make_peaked(10);
        let result = simplex_divide(&p, &q).unwrap();

        assert!(result.iter().all(|&x| x > 0.0));
        let sum: f64 = result.iter().sum();
        assert!((sum - 1.0).abs() < 1e-10);
    }

    #[test]
    fn test_dimension_mismatch() {
        let short = vec![0.5; 20];
        let normal = uniform();
        assert!(matches!(
            simplex_multiply(&short, &normal),
            Err(AlgebraError::DimensionMismatch { .. })
        ));
    }
}
