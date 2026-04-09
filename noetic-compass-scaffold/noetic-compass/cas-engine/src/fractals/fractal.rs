//! Core CognitiveFractal type — Definition 8.1 from v6.1.
//!
//! A Cognitive Fractal Φ = ⟨k₁ : k₂ : ⋯ : kₙ⟩ where each kᵢ ∈ {0,…,9}
//! and n ≥ 1. Application is right-to-left (innermost first):
//! Φ(E) = ν_k₁(ν_k₂(⋯ ν_kₙ(E) ⋯))

use serde::{Deserialize, Serialize};
use std::fmt;

/// A Cognitive Fractal: a non-empty sequence of operator indices (0-9).
///
/// Per v6.1 Definition 8.1, each element is a Cognitive Operator index.
/// The fractal defines a higher-order operator via right-to-left application.
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct CognitiveFractal {
    operators: Vec<u8>,
}

/// Error for invalid fractal construction.
#[derive(Debug, Clone, thiserror::Error)]
pub enum FractalError {
    #[error("Fractal sequence must be non-empty")]
    Empty,
    #[error("Operator index {0} out of range (must be 0-9)")]
    InvalidIndex(u8),
}

impl CognitiveFractal {
    /// Construct a fractal from a sequence of operator indices.
    ///
    /// # Errors
    /// Returns `FractalError::Empty` if the sequence is empty.
    /// Returns `FractalError::InvalidIndex` if any index > 9.
    pub fn new(operators: Vec<u8>) -> Result<Self, FractalError> {
        if operators.is_empty() {
            return Err(FractalError::Empty);
        }
        for &op in &operators {
            if op > 9 {
                return Err(FractalError::InvalidIndex(op));
            }
        }
        Ok(Self { operators })
    }

    /// The identity fractal ⟨0⟩ (Definition 8.7).
    /// Φ_id(E) = ν₀(E) = E
    pub fn identity() -> Self {
        Self {
            operators: vec![0],
        }
    }

    /// Length of the fractal sequence.
    pub fn len(&self) -> usize {
        self.operators.len()
    }

    /// The operator sequence as a slice.
    pub fn operators(&self) -> &[u8] {
        &self.operators
    }

    /// Mutable access to the operator sequence (for simplification).
    pub(crate) fn operators_mut(&mut self) -> &mut Vec<u8> {
        &mut self.operators
    }

    /// Whether this is the identity fractal ⟨0⟩.
    pub fn is_identity(&self) -> bool {
        self.operators.len() == 1 && self.operators[0] == 0
    }

    /// Apply the fractal to a cognitive state ID.
    ///
    /// Per Definition 8.3: Φ(E) = ν_k₁(ν_k₂(⋯ ν_kₙ(E) ⋯))
    /// Application is right-to-left (innermost first).
    ///
    /// Since CognitiveStateId tracks (operator, domain), applying operator
    /// ν_k to a state (op, dom) produces state (compose(CO_k, op), dom).
    pub fn apply(&self, element: &crate::ontology::states::CognitiveStateId) -> crate::ontology::states::CognitiveStateId {
        use crate::ontology::operators::CognitiveOperator;

        let mut current = *element;
        // Apply right-to-left: last operator in sequence is applied first
        for &op_idx in self.operators.iter().rev() {
            if let Some(op) = CognitiveOperator::from_index(op_idx as usize) {
                let composed = op.compose(current.operator());
                current = crate::ontology::states::CognitiveStateId::new(composed, current.domain());
            }
        }
        current
    }
}

impl fmt::Display for CognitiveFractal {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "⟨")?;
        for (i, op) in self.operators.iter().enumerate() {
            if i > 0 {
                write!(f, " : ")?;
            }
            write!(f, "{}", op)?;
        }
        write!(f, "⟩")
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_identity() {
        let id = CognitiveFractal::identity();
        assert_eq!(id.len(), 1);
        assert_eq!(id.operators(), &[0]);
        assert!(id.is_identity());
    }

    #[test]
    fn test_construction_valid() {
        let f = CognitiveFractal::new(vec![1, 4, 7]).unwrap();
        assert_eq!(f.len(), 3);
        assert_eq!(f.operators(), &[1, 4, 7]);
    }

    #[test]
    fn test_construction_empty() {
        assert!(CognitiveFractal::new(vec![]).is_err());
    }

    #[test]
    fn test_construction_invalid_index() {
        assert!(CognitiveFractal::new(vec![1, 15, 3]).is_err());
    }

    #[test]
    fn test_display() {
        let f = CognitiveFractal::new(vec![2, 5, 8]).unwrap();
        assert_eq!(f.to_string(), "⟨2 : 5 : 8⟩");
    }

    #[test]
    fn test_identity_display() {
        assert_eq!(CognitiveFractal::identity().to_string(), "⟨0⟩");
    }
}
