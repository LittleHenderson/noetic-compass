//! Fisher-Rao metric on the open probability simplex.
//!
//! The cognitive state space is the open probability simplex
//! Δ39° = { p ∈ R^40 : pk > 0 for all k, Σpk = 1 }.
//!
//! This module provides:
//! - Fisher-Rao inner product: g^FR_p(u, v) = Σ(uk * vk / pk)
//! - Geodesic (Bhattacharyya) distance: d(p, q) = 2 * arccos(Σ√(pk * qk))
//! - Tangent vector type with validation (components must sum to 0)
//!
//! CORRECTION 4: State space is the open simplex, not a discrete set.
//! All metric computations assume strictly positive probabilities.

use serde::{Deserialize, Serialize};

use crate::ontology::{CognitiveStateVector, NUM_STATES};

// ---------------------------------------------------------------------------
// Error type
// ---------------------------------------------------------------------------

/// Errors arising from metric computations.
#[derive(Debug, Clone, PartialEq, thiserror::Error)]
pub enum MetricError {
    /// The vector has the wrong number of components.
    #[error("wrong dimension: expected {expected}, got {got}")]
    WrongDimension { expected: usize, got: usize },

    /// The vector components do not sum to approximately zero,
    /// so it is not a valid tangent vector on the simplex.
    #[error("not a tangent vector: components sum to {sum} (must be ≈ 0)")]
    NotTangent { sum: f64 },
}

// ---------------------------------------------------------------------------
// TangentVector
// ---------------------------------------------------------------------------

/// Tolerance for checking that tangent vector components sum to zero.
const TANGENT_SUM_TOLERANCE: f64 = 1e-9;

/// A tangent vector on the open probability simplex.
///
/// For a point p on the simplex Δ39°, tangent vectors must satisfy Σ_k u_k = 0
/// because the simplex constraint Σ pk = 1 implies that infinitesimal
/// perturbations preserve the total probability.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct TangentVector {
    components: Vec<f64>,
}

impl TangentVector {
    /// Access the raw component slice.
    pub fn as_slice(&self) -> &[f64] {
        &self.components
    }

    /// Number of components (always NUM_STATES = 40).
    pub fn dim(&self) -> usize {
        self.components.len()
    }

    /// Get the component at a given index.
    ///
    /// # Panics
    /// Panics if `index >= NUM_STATES`.
    pub fn component(&self, index: usize) -> f64 {
        self.components[index]
    }
}

/// Validate a slice and construct a `TangentVector`.
///
/// Checks:
/// 1. The slice has exactly `NUM_STATES` (40) elements.
/// 2. The sum of components is approximately zero (within tolerance).
pub fn validate_tangent_vector(v: &[f64]) -> Result<TangentVector, MetricError> {
    if v.len() != NUM_STATES {
        return Err(MetricError::WrongDimension {
            expected: NUM_STATES,
            got: v.len(),
        });
    }

    let sum: f64 = v.iter().sum();
    if sum.abs() > TANGENT_SUM_TOLERANCE {
        return Err(MetricError::NotTangent { sum });
    }

    Ok(TangentVector {
        components: v.to_vec(),
    })
}

// ---------------------------------------------------------------------------
// Fisher-Rao inner product and norm
// ---------------------------------------------------------------------------

/// Compute the Fisher-Rao inner product at point `p` for tangent vectors `u` and `v`.
///
/// g^FR_p(u, v) = Σ_k (u_k * v_k / p_k)
///
/// This is the unique (up to scaling) Riemannian metric on the probability simplex
/// that is invariant under sufficient statistics. All p_k are guaranteed positive
/// by the `CognitiveStateVector` constructor.
pub fn fisher_rao_inner_product(
    p: &CognitiveStateVector,
    u: &TangentVector,
    v: &TangentVector,
) -> f64 {
    let ps = p.as_slice();
    let us = u.as_slice();
    let vs = v.as_slice();

    let mut result = 0.0;
    for k in 0..NUM_STATES {
        result += us[k] * vs[k] / ps[k];
    }
    result
}

/// Compute the Fisher-Rao norm of a tangent vector at point `p`.
///
/// ||u||_p = √(g^FR_p(u, u)) = √(Σ_k u_k² / p_k)
pub fn fisher_rao_norm(p: &CognitiveStateVector, u: &TangentVector) -> f64 {
    fisher_rao_inner_product(p, u, u).sqrt()
}

// ---------------------------------------------------------------------------
// Bhattacharyya coefficient and geodesic distance
// ---------------------------------------------------------------------------

/// Compute the Bhattacharyya coefficient between two probability distributions.
///
/// BC(p, q) = Σ_k √(p_k * q_k)
///
/// This measures the overlap between two distributions. It satisfies 0 ≤ BC ≤ 1,
/// with BC = 1 if and only if p = q.
pub fn bhattacharyya_coefficient(p: &CognitiveStateVector, q: &CognitiveStateVector) -> f64 {
    let ps = p.as_slice();
    let qs = q.as_slice();

    let mut bc = 0.0;
    for k in 0..NUM_STATES {
        bc += (ps[k] * qs[k]).sqrt();
    }
    bc
}

/// Compute the Fisher-Rao geodesic distance between two points on the open simplex.
///
/// d(p, q) = 2 * arccos(Σ_k √(p_k * q_k))
///
/// This is the length of the shortest geodesic path between p and q under
/// the Fisher-Rao metric. The arccos argument is clamped to [0, 1] for
/// numerical stability (floating-point arithmetic may slightly exceed bounds).
pub fn geodesic_distance(p: &CognitiveStateVector, q: &CognitiveStateVector) -> f64 {
    let bc = bhattacharyya_coefficient(p, q);
    // Clamp to [0, 1] for numerical stability.
    let bc_clamped = bc.clamp(0.0, 1.0);
    2.0 * bc_clamped.acos()
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    /// Helper: create a CognitiveStateVector with given non-uniform weights.
    /// `weights` is a 40-element array of positive values; this function normalizes them.
    fn make_state_vector(weights: [f64; NUM_STATES]) -> CognitiveStateVector {
        let sum: f64 = weights.iter().sum();
        let probs: [f64; NUM_STATES] = {
            let mut arr = [0.0; NUM_STATES];
            for (i, &w) in weights.iter().enumerate() {
                arr[i] = w / sum;
            }
            arr
        };
        CognitiveStateVector::new(probs).expect("valid state vector")
    }

    /// Helper: create a simple non-uniform state vector by shifting mass toward index 0.
    fn shifted_vector(shift_index: usize, shift_amount: f64) -> CognitiveStateVector {
        let base = 1.0 / NUM_STATES as f64;
        let mut weights = [base; NUM_STATES];
        // Add extra weight to shift_index, remove from the rest proportionally
        weights[shift_index] += shift_amount;
        let excess_per_other = shift_amount / (NUM_STATES - 1) as f64;
        for i in 0..NUM_STATES {
            if i != shift_index {
                weights[i] -= excess_per_other;
            }
        }
        // Ensure all positive
        let min_val = weights.iter().cloned().fold(f64::INFINITY, f64::min);
        assert!(
            min_val > 0.0,
            "shift_amount too large, produced non-positive weights"
        );
        let sum: f64 = weights.iter().sum();
        // Re-normalize (should already sum to 1, but be safe)
        for w in weights.iter_mut() {
            *w /= sum;
        }
        CognitiveStateVector::new(weights).expect("valid shifted vector")
    }

    /// Helper: create a valid tangent vector. Takes a raw 40-element slice and
    /// projects it onto the tangent space (subtracts the mean so components sum to 0).
    fn make_tangent(raw: [f64; NUM_STATES]) -> TangentVector {
        let mean: f64 = raw.iter().sum::<f64>() / NUM_STATES as f64;
        let projected: Vec<f64> = raw.iter().map(|&x| x - mean).collect();
        validate_tangent_vector(&projected).expect("projected vector should be tangent")
    }

    // -----------------------------------------------------------------------
    // TangentVector validation tests
    // -----------------------------------------------------------------------

    #[test]
    fn test_validate_tangent_vector_correct() {
        // A vector that sums to 0: +1 at index 0, -1 at index 1, rest zero
        let mut v = [0.0; NUM_STATES];
        v[0] = 1.0;
        v[1] = -1.0;
        let tv = validate_tangent_vector(&v);
        assert!(tv.is_ok());
        let tv = tv.unwrap();
        assert_eq!(tv.dim(), NUM_STATES);
        assert_eq!(tv.component(0), 1.0);
        assert_eq!(tv.component(1), -1.0);
    }

    #[test]
    fn test_validate_tangent_vector_wrong_dimension() {
        let v = [0.0; 10];
        let result = validate_tangent_vector(&v);
        assert!(matches!(
            result,
            Err(MetricError::WrongDimension {
                expected: 40,
                got: 10
            })
        ));
    }

    #[test]
    fn test_validate_tangent_vector_not_tangent() {
        let v = [1.0; NUM_STATES]; // sums to 40, not 0
        let result = validate_tangent_vector(&v);
        assert!(matches!(result, Err(MetricError::NotTangent { .. })));
        if let Err(MetricError::NotTangent { sum }) = result {
            assert!((sum - 40.0).abs() < 1e-9);
        }
    }

    #[test]
    fn test_validate_tangent_vector_empty() {
        let result = validate_tangent_vector(&[]);
        assert!(matches!(
            result,
            Err(MetricError::WrongDimension {
                expected: 40,
                got: 0
            })
        ));
    }

    #[test]
    fn test_validate_tangent_vector_zero_is_valid() {
        let v = [0.0; NUM_STATES];
        let tv = validate_tangent_vector(&v);
        assert!(tv.is_ok());
    }

    // -----------------------------------------------------------------------
    // Fisher-Rao inner product tests
    // -----------------------------------------------------------------------

    #[test]
    fn test_inner_product_positive_definite() {
        // For a non-zero tangent vector, g(u, u) > 0
        let p = CognitiveStateVector::uniform();
        let raw = {
            let mut r = [0.0; NUM_STATES];
            r[0] = 3.0;
            r[1] = -2.0;
            r[2] = -1.0;
            r
        };
        let u = make_tangent(raw);
        let ip = fisher_rao_inner_product(&p, &u, &u);
        assert!(
            ip > 0.0,
            "inner product of non-zero vector must be positive, got {ip}"
        );
    }

    #[test]
    fn test_inner_product_zero_vector() {
        // g(0, 0) = 0
        let p = CognitiveStateVector::uniform();
        let zero = validate_tangent_vector(&[0.0; NUM_STATES]).unwrap();
        let ip = fisher_rao_inner_product(&p, &zero, &zero);
        assert!(
            (ip).abs() < 1e-15,
            "inner product of zero vector must be 0, got {ip}"
        );
    }

    #[test]
    fn test_inner_product_symmetry() {
        let p = CognitiveStateVector::uniform();
        let raw_u = {
            let mut r = [0.0; NUM_STATES];
            r[0] = 1.0;
            r[1] = -1.0;
            r
        };
        let raw_v = {
            let mut r = [0.0; NUM_STATES];
            r[2] = 0.5;
            r[3] = -0.5;
            r
        };
        let u = make_tangent(raw_u);
        let v = make_tangent(raw_v);
        let guv = fisher_rao_inner_product(&p, &u, &v);
        let gvu = fisher_rao_inner_product(&p, &v, &u);
        assert!(
            (guv - gvu).abs() < 1e-12,
            "inner product should be symmetric: g(u,v)={guv}, g(v,u)={gvu}"
        );
    }

    #[test]
    fn test_inner_product_bilinearity() {
        // g(au + bw, v) = a*g(u,v) + b*g(w,v)
        let p = CognitiveStateVector::uniform();
        let raw_u = {
            let mut r = [0.0; NUM_STATES];
            r[0] = 1.0;
            r[1] = -1.0;
            r
        };
        let raw_v = {
            let mut r = [0.0; NUM_STATES];
            r[2] = 0.7;
            r[3] = -0.7;
            r
        };
        let raw_w = {
            let mut r = [0.0; NUM_STATES];
            r[4] = 0.3;
            r[5] = -0.3;
            r
        };
        let u = make_tangent(raw_u);
        let v = make_tangent(raw_v);
        let w = make_tangent(raw_w);

        let a = 2.5_f64;
        let b = -1.3_f64;

        // Compute au + bw
        let combined: Vec<f64> = u
            .as_slice()
            .iter()
            .zip(w.as_slice().iter())
            .map(|(&ui, &wi)| a * ui + b * wi)
            .collect();
        let combined_tv = validate_tangent_vector(&combined).unwrap();

        let lhs = fisher_rao_inner_product(&p, &combined_tv, &v);
        let rhs =
            a * fisher_rao_inner_product(&p, &u, &v) + b * fisher_rao_inner_product(&p, &w, &v);
        assert!(
            (lhs - rhs).abs() < 1e-10,
            "bilinearity failed: lhs={lhs}, rhs={rhs}"
        );
    }

    #[test]
    fn test_inner_product_at_uniform() {
        // At uniform p = (1/40, ..., 1/40), g(u,v) = 40 * Σ(u_k * v_k)
        // because each 1/pk = 40
        let p = CognitiveStateVector::uniform();
        let mut raw_u = [0.0; NUM_STATES];
        raw_u[0] = 1.0;
        raw_u[1] = -1.0;
        let u = validate_tangent_vector(&raw_u).unwrap();

        let ip = fisher_rao_inner_product(&p, &u, &u);
        // Expected: 40 * (1^2 + (-1)^2) = 80
        let expected = NUM_STATES as f64 * 2.0;
        assert!(
            (ip - expected).abs() < 1e-10,
            "at uniform, g(u,u) should be {expected}, got {ip}"
        );
    }

    // -----------------------------------------------------------------------
    // Fisher-Rao norm tests
    // -----------------------------------------------------------------------

    #[test]
    fn test_norm_non_negative() {
        let p = CognitiveStateVector::uniform();
        let raw = {
            let mut r = [0.0; NUM_STATES];
            r[0] = 1.0;
            r[1] = -1.0;
            r
        };
        let u = make_tangent(raw);
        let n = fisher_rao_norm(&p, &u);
        assert!(n >= 0.0, "norm must be non-negative, got {n}");
    }

    #[test]
    fn test_norm_zero_vector() {
        let p = CognitiveStateVector::uniform();
        let zero = validate_tangent_vector(&[0.0; NUM_STATES]).unwrap();
        let n = fisher_rao_norm(&p, &zero);
        assert!(n.abs() < 1e-15, "norm of zero vector should be 0, got {n}");
    }

    #[test]
    fn test_norm_consistent_with_inner_product() {
        let p = CognitiveStateVector::uniform();
        let raw = {
            let mut r = [0.0; NUM_STATES];
            r[0] = 2.0;
            r[5] = -1.0;
            r[10] = -1.0;
            r
        };
        let u = make_tangent(raw);
        let norm = fisher_rao_norm(&p, &u);
        let ip = fisher_rao_inner_product(&p, &u, &u);
        assert!(
            (norm * norm - ip).abs() < 1e-12,
            "||u||^2 should equal g(u,u): norm^2={}, g(u,u)={ip}",
            norm * norm
        );
    }

    // -----------------------------------------------------------------------
    // Bhattacharyya coefficient tests
    // -----------------------------------------------------------------------

    #[test]
    fn test_bhattacharyya_identical_distributions() {
        let p = CognitiveStateVector::uniform();
        let bc = bhattacharyya_coefficient(&p, &p);
        assert!((bc - 1.0).abs() < 1e-12, "BC(p, p) should be 1.0, got {bc}");
    }

    #[test]
    fn test_bhattacharyya_in_unit_interval() {
        let p = CognitiveStateVector::uniform();
        let q = shifted_vector(0, 0.01);
        let bc = bhattacharyya_coefficient(&p, &q);
        assert!(
            (0.0..=1.0 + 1e-12).contains(&bc),
            "BC should be in [0, 1], got {bc}"
        );
    }

    #[test]
    fn test_bhattacharyya_symmetric() {
        let p = shifted_vector(0, 0.01);
        let q = shifted_vector(5, 0.005);
        let bc_pq = bhattacharyya_coefficient(&p, &q);
        let bc_qp = bhattacharyya_coefficient(&q, &p);
        assert!(
            (bc_pq - bc_qp).abs() < 1e-15,
            "BC should be symmetric: BC(p,q)={bc_pq}, BC(q,p)={bc_qp}"
        );
    }

    #[test]
    fn test_bhattacharyya_less_than_one_for_different() {
        let p = shifted_vector(0, 0.01);
        let q = shifted_vector(5, 0.01);
        let bc = bhattacharyya_coefficient(&p, &q);
        assert!(
            bc < 1.0,
            "BC for different distributions should be < 1.0, got {bc}"
        );
    }

    #[test]
    fn test_bhattacharyya_cauchy_schwarz() {
        // By Cauchy-Schwarz: (Σ√(pk * qk))² ≤ (Σpk)(Σqk) = 1
        // So BC ≤ 1 always
        let p = shifted_vector(0, 0.02);
        let q = shifted_vector(10, 0.015);
        let bc = bhattacharyya_coefficient(&p, &q);
        assert!(bc <= 1.0 + 1e-12, "BC must satisfy Cauchy-Schwarz: BC={bc}");
    }

    // -----------------------------------------------------------------------
    // Geodesic distance tests
    // -----------------------------------------------------------------------

    #[test]
    fn test_distance_non_negative() {
        let p = CognitiveStateVector::uniform();
        let q = shifted_vector(0, 0.01);
        let d = geodesic_distance(&p, &q);
        assert!(d >= -1e-15, "distance must be non-negative, got {d}");
    }

    #[test]
    fn test_distance_self_is_zero() {
        let p = CognitiveStateVector::uniform();
        let d = geodesic_distance(&p, &p);
        assert!(d.abs() < 1e-12, "d(p, p) should be 0, got {d}");
    }

    #[test]
    fn test_distance_symmetric() {
        let p = shifted_vector(0, 0.01);
        let q = shifted_vector(5, 0.005);
        let d_pq = geodesic_distance(&p, &q);
        let d_qp = geodesic_distance(&q, &p);
        assert!(
            (d_pq - d_qp).abs() < 1e-12,
            "distance should be symmetric: d(p,q)={d_pq}, d(q,p)={d_qp}"
        );
    }

    #[test]
    fn test_triangle_inequality() {
        let p = shifted_vector(0, 0.01);
        let q = shifted_vector(10, 0.015);
        let r = shifted_vector(20, 0.008);

        let d_pq = geodesic_distance(&p, &q);
        let d_qr = geodesic_distance(&q, &r);
        let d_pr = geodesic_distance(&p, &r);

        assert!(
            d_pr <= d_pq + d_qr + 1e-10,
            "triangle inequality violated: d(p,r)={d_pr} > d(p,q)+d(q,r)={}",
            d_pq + d_qr
        );
    }

    #[test]
    fn test_distance_increases_with_divergence() {
        // More shifted distributions should have larger distance
        let base = CognitiveStateVector::uniform();
        let slightly_shifted = shifted_vector(0, 0.005);
        let more_shifted = shifted_vector(0, 0.015);

        let d_small = geodesic_distance(&base, &slightly_shifted);
        let d_large = geodesic_distance(&base, &more_shifted);

        assert!(
            d_large > d_small,
            "larger shift should give larger distance: d_small={d_small}, d_large={d_large}"
        );
    }

    #[test]
    fn test_distance_bounded_by_pi() {
        // On the probability simplex mapped to the sphere, max geodesic
        // distance is π (antipodal points), but on the open simplex
        // (all pk > 0) it cannot reach π.
        let p = shifted_vector(0, 0.02);
        let q = shifted_vector(20, 0.02);
        let d = geodesic_distance(&p, &q);
        assert!(
            d < std::f64::consts::PI + 1e-12,
            "distance should be < π, got {d}"
        );
    }

    #[test]
    fn test_distance_known_value_uniform() {
        // d(uniform, uniform) = 0
        let u = CognitiveStateVector::uniform();
        assert!(geodesic_distance(&u, &u).abs() < 1e-14);
    }

    #[test]
    fn test_triangle_inequality_multiple_triples() {
        // Test several triples for the triangle inequality
        let vecs: Vec<CognitiveStateVector> = (0..5)
            .map(|i| shifted_vector(i * 8, 0.003 * (i + 1) as f64))
            .collect();

        for i in 0..vecs.len() {
            for j in 0..vecs.len() {
                for k in 0..vecs.len() {
                    let d_ij = geodesic_distance(&vecs[i], &vecs[j]);
                    let d_jk = geodesic_distance(&vecs[j], &vecs[k]);
                    let d_ik = geodesic_distance(&vecs[i], &vecs[k]);
                    assert!(
                        d_ik <= d_ij + d_jk + 1e-10,
                        "triangle ineq violated for ({i},{j},{k}): d({i},{k})={d_ik} > d({i},{j})+d({j},{k})={}",
                        d_ij + d_jk
                    );
                }
            }
        }
    }

    // -----------------------------------------------------------------------
    // Integration tests: metric consistency
    // -----------------------------------------------------------------------

    #[test]
    fn test_distance_and_bhattacharyya_consistency() {
        // d(p, q) = 2 * arccos(BC(p, q))
        let p = shifted_vector(3, 0.01);
        let q = shifted_vector(15, 0.008);
        let bc = bhattacharyya_coefficient(&p, &q);
        let d = geodesic_distance(&p, &q);
        let expected = 2.0 * bc.clamp(0.0, 1.0).acos();
        assert!(
            (d - expected).abs() < 1e-14,
            "distance should equal 2*arccos(BC): d={d}, expected={expected}"
        );
    }

    #[test]
    fn test_inner_product_with_nonuniform_base() {
        // The inner product at a non-uniform point should weight differently
        let mut weights = [1.0; NUM_STATES];
        weights[0] = 10.0; // much higher weight on index 0
        let p = make_state_vector(weights);

        let mut raw_u = [0.0; NUM_STATES];
        raw_u[0] = 1.0;
        raw_u[1] = -1.0;
        let u = validate_tangent_vector(&raw_u).unwrap();

        let ip = fisher_rao_inner_product(&p, &u, &u);
        // p0 ≈ 10/49, p1 ≈ 1/49
        // g = 1²/(10/49) + (-1)²/(1/49) = 49/10 + 49 = 4.9 + 49 = 53.9
        let p0 = p.probability_at(0);
        let p1 = p.probability_at(1);
        let expected = 1.0 / p0 + 1.0 / p1;
        assert!(
            (ip - expected).abs() < 1e-10,
            "inner product at non-uniform point: got {ip}, expected {expected}"
        );
    }

    #[test]
    fn test_norm_scaling() {
        // ||a * u|| = |a| * ||u||
        let p = CognitiveStateVector::uniform();
        let mut raw = [0.0; NUM_STATES];
        raw[0] = 1.0;
        raw[1] = -1.0;
        let u = validate_tangent_vector(&raw).unwrap();
        let norm_u = fisher_rao_norm(&p, &u);

        let a = 3.7_f64;
        let scaled: Vec<f64> = raw.iter().map(|&x| a * x).collect();
        let u_scaled = validate_tangent_vector(&scaled).unwrap();
        let norm_scaled = fisher_rao_norm(&p, &u_scaled);

        assert!(
            (norm_scaled - a.abs() * norm_u).abs() < 1e-10,
            "norm should scale linearly: ||au||={norm_scaled}, |a|*||u||={}",
            a.abs() * norm_u
        );
    }

    #[test]
    fn test_geodesic_distance_near_identical() {
        // Two very close distributions should have a very small distance
        let p = CognitiveStateVector::uniform();
        let q = shifted_vector(0, 1e-10);
        let d = geodesic_distance(&p, &q);
        assert!(
            d < 1e-4,
            "near-identical distributions should have tiny distance, got {d}"
        );
    }
}
