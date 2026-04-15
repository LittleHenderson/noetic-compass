//! Cognitive States: 40 states = 10 Operators x 4 Domains
//!
//! States are identified as P0-P9, C0-C9, E0-E9, O0-O9.
//!
//! CORRECTION 4: The state space is the open probability simplex
//! S_I = Delta_39_open = { p in R^40 : pk > 0 for all k, sum(pk) = 1 }
//! NOT the discrete 40-element set.

use serde::{Deserialize, Serialize};
use std::fmt;

use super::domains::Domain;
use super::operators::CognitiveOperator;

/// Total number of cognitive states (10 operators x 4 domains).
pub const NUM_STATES: usize = 40;

/// Minimum probability for any state component (open simplex: all pk > 0).
pub const MIN_PROBABILITY: f64 = 1e-15;

/// Identifier for a single cognitive state (operator x domain pair).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct CognitiveStateId {
    operator: CognitiveOperator,
    domain: Domain,
}

impl CognitiveStateId {
    pub fn new(operator: CognitiveOperator, domain: Domain) -> Self {
        Self { operator, domain }
    }

    pub fn operator(self) -> CognitiveOperator {
        self.operator
    }

    pub fn domain(self) -> Domain {
        self.domain
    }

    /// Linear index in [0, 39]. Layout: domain-major, operator-minor.
    /// P0=0, P1=1, ..., P9=9, C0=10, ..., O9=39.
    pub fn linear_index(self) -> usize {
        self.domain.index() * 10 + self.operator.index()
    }

    /// Construct from linear index [0, 39].
    pub fn from_linear_index(idx: usize) -> Option<Self> {
        if idx >= NUM_STATES {
            return None;
        }
        let domain = Domain::from_index(idx / 10)?;
        let operator = CognitiveOperator::from_index(idx % 10)?;
        Some(Self { operator, domain })
    }

    /// All 40 state identifiers in linear order.
    pub fn all() -> [CognitiveStateId; NUM_STATES] {
        let mut states = [CognitiveStateId {
            operator: CognitiveOperator::CO0,
            domain: Domain::Principled,
        }; NUM_STATES];
        for i in 0..NUM_STATES {
            states[i] = Self::from_linear_index(i).unwrap();
        }
        states
    }
}

impl fmt::Display for CognitiveStateId {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}{}", self.domain.abbreviation(), self.operator.index())
    }
}

/// Errors related to cognitive state vectors.
#[derive(Debug, Clone, PartialEq, thiserror::Error)]
pub enum StateVectorError {
    #[error("wrong dimension: expected {NUM_STATES}, got {0}")]
    WrongDimension(usize),
    #[error("probability at index {index} is {value}, must be > 0 (open simplex)")]
    NonPositiveProbability { index: usize, value: f64 },
    #[error("probabilities sum to {0}, must be approximately 1.0")]
    NotNormalized(f64),
    #[error("probability at index {index} is NaN")]
    NaN { index: usize },
}

/// A cognitive state vector on the open probability simplex Delta_39_open.
///
/// CORRECTION 4: All components pk must be strictly positive (pk > 0)
/// and must sum to 1.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CognitiveStateVector {
    probabilities: Vec<f64>,
}

impl CognitiveStateVector {
    /// Normalization tolerance.
    const NORM_TOLERANCE: f64 = 1e-9;

    /// Create a new state vector, validating open simplex constraints.
    pub fn new(probabilities: [f64; NUM_STATES]) -> Result<Self, StateVectorError> {
        Self::from_slice(&probabilities)
    }

    /// Create from a slice, validating open simplex constraints.
    pub fn from_slice(probabilities: &[f64]) -> Result<Self, StateVectorError> {
        if probabilities.len() != NUM_STATES {
            return Err(StateVectorError::WrongDimension(probabilities.len()));
        }
        let mut sum = 0.0;
        for (i, &p) in probabilities.iter().enumerate() {
            if p.is_nan() {
                return Err(StateVectorError::NaN { index: i });
            }
            if p <= 0.0 {
                return Err(StateVectorError::NonPositiveProbability { index: i, value: p });
            }
            sum += p;
        }
        if (sum - 1.0).abs() > Self::NORM_TOLERANCE {
            return Err(StateVectorError::NotNormalized(sum));
        }
        Ok(Self {
            probabilities: probabilities.to_vec(),
        })
    }

    /// Create a uniform distribution (1/40 for each state).
    pub fn uniform() -> Self {
        Self {
            probabilities: vec![1.0 / NUM_STATES as f64; NUM_STATES],
        }
    }

    /// Get the probability for a specific state.
    pub fn probability(&self, state: CognitiveStateId) -> f64 {
        self.probabilities[state.linear_index()]
    }

    /// Get the probability at a linear index.
    pub fn probability_at(&self, index: usize) -> f64 {
        self.probabilities[index]
    }

    /// Access the raw probability slice.
    pub fn as_slice(&self) -> &[f64] {
        &self.probabilities
    }

    /// Average probability across all operators within a domain.
    pub fn domain_average(&self, domain: Domain) -> f64 {
        let start = domain.index() * 10;
        let sum: f64 = self.probabilities[start..start + 10].iter().sum();
        sum / 10.0
    }

    /// Get the probabilities for all operators within a domain.
    pub fn domain_slice(&self, domain: Domain) -> &[f64] {
        let start = domain.index() * 10;
        &self.probabilities[start..start + 10]
    }

    /// Get the probability for a specific operator, summed across all domains.
    pub fn operator_total(&self, op: CognitiveOperator) -> f64 {
        Domain::ALL
            .iter()
            .map(|&d| self.probabilities[d.index() * 10 + op.index()])
            .sum()
    }
}

impl PartialEq for CognitiveStateVector {
    fn eq(&self, other: &Self) -> bool {
        self.probabilities
            .iter()
            .zip(other.probabilities.iter())
            .all(|(a, b)| (a - b).abs() < 1e-12)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_state_id_linear_index_roundtrip() {
        for i in 0..NUM_STATES {
            let id = CognitiveStateId::from_linear_index(i).unwrap();
            assert_eq!(id.linear_index(), i);
        }
        assert!(CognitiveStateId::from_linear_index(40).is_none());
    }

    #[test]
    fn test_state_id_display() {
        let s = CognitiveStateId::new(CognitiveOperator::CO3, Domain::Evaluative);
        assert_eq!(format!("{}", s), "E3");

        let s = CognitiveStateId::new(CognitiveOperator::CO0, Domain::Principled);
        assert_eq!(format!("{}", s), "P0");
    }

    #[test]
    fn test_uniform_is_valid() {
        let v = CognitiveStateVector::uniform();
        let sum: f64 = v.as_slice().iter().sum();
        assert!((sum - 1.0).abs() < 1e-12);
        for &p in v.as_slice() {
            assert!(p > 0.0);
        }
    }

    #[test]
    fn test_open_simplex_rejects_zero() {
        let mut probs = [1.0 / NUM_STATES as f64; NUM_STATES];
        probs[0] = 0.0;
        probs[1] += 1.0 / NUM_STATES as f64; // keep sum at 1
        assert!(matches!(
            CognitiveStateVector::new(probs),
            Err(StateVectorError::NonPositiveProbability { index: 0, .. })
        ));
    }

    #[test]
    fn test_open_simplex_rejects_negative() {
        let mut probs = [1.0 / NUM_STATES as f64; NUM_STATES];
        probs[5] = -0.01;
        assert!(matches!(
            CognitiveStateVector::new(probs),
            Err(StateVectorError::NonPositiveProbability { index: 5, .. })
        ));
    }

    #[test]
    fn test_rejects_unnormalized() {
        let probs = [1.0; NUM_STATES]; // sums to 40
        assert!(matches!(
            CognitiveStateVector::new(probs),
            Err(StateVectorError::NotNormalized(_))
        ));
    }

    #[test]
    fn test_domain_average() {
        let v = CognitiveStateVector::uniform();
        for d in Domain::ALL {
            let avg = v.domain_average(d);
            assert!((avg - 1.0 / NUM_STATES as f64).abs() < 1e-12);
        }
    }

    #[test]
    fn test_all_40_states() {
        let all = CognitiveStateId::all();
        assert_eq!(all.len(), 40);
        // Check uniqueness
        let mut seen = std::collections::HashSet::new();
        for s in &all {
            assert!(seen.insert(*s));
        }
    }
}
