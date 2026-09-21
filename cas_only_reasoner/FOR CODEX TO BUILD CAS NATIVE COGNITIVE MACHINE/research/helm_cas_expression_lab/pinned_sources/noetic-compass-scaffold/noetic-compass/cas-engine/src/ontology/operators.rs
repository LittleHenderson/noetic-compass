//! Cognitive Operators (CO-0 through CO-9)
//!
//! The 10 cognitive operators form a monoid (N, compose, CO-0) where CO-0 is the identity.
//! Involution pairs: CO-2 <-> CO-3, CO-5 <-> CO-6, CO-8 <-> CO-9
//! Self-duals: CO-0, CO-1, CO-4, CO-7
//!
//! CORRECTION 1: Each operator has an admissibility relation Dk subset of I x I
//! specifying valid (source, target) pairs. D0 = diagonal only.

use serde::{Deserialize, Serialize};
use std::fmt;

use super::states::CognitiveStateId;

/// The 10 cognitive operators in the CAS framework.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[repr(u8)]
pub enum CognitiveOperator {
    CO0 = 0, // Identity (self-dual)
    CO1 = 1, // Self-dual
    CO2 = 2, // Involution pair with CO3
    CO3 = 3, // Involution pair with CO2
    CO4 = 4, // Self-dual
    CO5 = 5, // Involution pair with CO6
    CO6 = 6, // Involution pair with CO5
    CO7 = 7, // Self-dual
    CO8 = 8, // Involution pair with CO9
    CO9 = 9, // Involution pair with CO8
}

impl CognitiveOperator {
    /// All operators in order.
    pub const ALL: [CognitiveOperator; 10] = [
        Self::CO0,
        Self::CO1,
        Self::CO2,
        Self::CO3,
        Self::CO4,
        Self::CO5,
        Self::CO6,
        Self::CO7,
        Self::CO8,
        Self::CO9,
    ];

    /// The three involution pairs.
    pub const INVOLUTION_PAIRS: [(CognitiveOperator, CognitiveOperator); 3] = [
        (Self::CO2, Self::CO3),
        (Self::CO5, Self::CO6),
        (Self::CO8, Self::CO9),
    ];

    /// The four self-dual operators.
    pub const SELF_DUALS: [CognitiveOperator; 4] = [Self::CO0, Self::CO1, Self::CO4, Self::CO7];

    /// Returns the index (0-9) of this operator.
    pub fn index(self) -> usize {
        self as usize
    }

    /// Construct from index (0-9). Returns None if out of range.
    pub fn from_index(idx: usize) -> Option<Self> {
        match idx {
            0 => Some(Self::CO0),
            1 => Some(Self::CO1),
            2 => Some(Self::CO2),
            3 => Some(Self::CO3),
            4 => Some(Self::CO4),
            5 => Some(Self::CO5),
            6 => Some(Self::CO6),
            7 => Some(Self::CO7),
            8 => Some(Self::CO8),
            9 => Some(Self::CO9),
            _ => None,
        }
    }

    /// Returns the involution partner, or self if self-dual.
    pub fn involute(self) -> Self {
        match self {
            Self::CO0 => Self::CO0,
            Self::CO1 => Self::CO1,
            Self::CO2 => Self::CO3,
            Self::CO3 => Self::CO2,
            Self::CO4 => Self::CO4,
            Self::CO5 => Self::CO6,
            Self::CO6 => Self::CO5,
            Self::CO7 => Self::CO7,
            Self::CO8 => Self::CO9,
            Self::CO9 => Self::CO8,
        }
    }

    /// Whether this operator is self-dual under involution.
    pub fn is_self_dual(self) -> bool {
        matches!(self, Self::CO0 | Self::CO1 | Self::CO4 | Self::CO7)
    }

    /// Monoid composition. CO-0 is the identity element.
    /// For the general monoid, composition maps (CO-a, CO-b) -> CO-((a+b) mod 10).
    /// This gives CO-0 as identity: CO-0 compose CO-k = CO-k.
    pub fn compose(self, other: Self) -> Self {
        let idx = (self.index() + other.index()) % 10;
        Self::from_index(idx).unwrap()
    }

    /// Check admissibility: whether operator application from source to target is valid.
    /// CORRECTION 1: D0 = diagonal only (identity maps state to itself).
    /// Other operators have broader admissibility relations.
    pub fn is_admissible(self, source: CognitiveStateId, target: CognitiveStateId) -> bool {
        match self {
            // CO-0 is identity: only admissible on the diagonal
            Self::CO0 => source == target,
            // Non-identity operators: admissible when source and target share
            // the same domain (intra-domain transitions) or when the operator
            // mediates a specific cross-domain mapping.
            _ => {
                // Intra-domain transitions are always admissible for non-identity operators
                if source.domain() == target.domain() {
                    return true;
                }
                // Cross-domain: the operator index must match the target operator index
                target.operator() == self
            }
        }
    }
}

impl fmt::Display for CognitiveOperator {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "CO-{}", self.index())
    }
}

/// Dial setting for a cognitive operator. Constrained to [3, 9].
///
/// Safety constraints (hardcoded, non-overridable):
/// - No dial below 3 or above 9
/// - Involution pairs cannot diverge by more than 4 points
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct DialSetting {
    value: u8,
}

/// Errors related to dial configuration.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum DialError {
    #[error("dial value {0} out of range [3, 9]")]
    OutOfRange(u8),
    #[error(
        "involution pair {pair:?} divergence {divergence} exceeds maximum of 4 (values: {a}, {b})"
    )]
    InvolutionDivergence {
        pair: (CognitiveOperator, CognitiveOperator),
        a: u8,
        b: u8,
        divergence: u8,
    },
}

impl DialSetting {
    pub const MIN: u8 = 3;
    pub const MAX: u8 = 9;
    pub const MAX_INVOLUTION_DIVERGENCE: u8 = 4;

    /// Create a new dial setting. Returns error if value is outside [3, 9].
    pub fn new(value: u8) -> Result<Self, DialError> {
        if value < Self::MIN || value > Self::MAX {
            return Err(DialError::OutOfRange(value));
        }
        Ok(Self { value })
    }

    pub fn value(self) -> u8 {
        self.value
    }
}

/// Complete dial configuration for all 10 operators.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct DialConfig {
    dials: [DialSetting; 10],
}

impl DialConfig {
    /// Create a new dial configuration, validating all constraints.
    pub fn new(values: [u8; 10]) -> Result<Self, DialError> {
        let mut dials = [DialSetting { value: 6 }; 10];
        for (i, &v) in values.iter().enumerate() {
            dials[i] = DialSetting::new(v)?;
        }

        let config = Self { dials };
        config.validate_involution_constraints()?;
        Ok(config)
    }

    /// Create with all dials at default value (6 = midpoint).
    pub fn default_config() -> Self {
        Self {
            dials: [DialSetting { value: 6 }; 10],
        }
    }

    /// Get the dial setting for an operator.
    pub fn get(&self, op: CognitiveOperator) -> DialSetting {
        self.dials[op.index()]
    }

    /// Set a single dial, re-validating constraints.
    pub fn set(&mut self, op: CognitiveOperator, value: u8) -> Result<(), DialError> {
        let new_dial = DialSetting::new(value)?;
        let old = self.dials[op.index()];
        self.dials[op.index()] = new_dial;

        if let Err(e) = self.validate_involution_constraints() {
            self.dials[op.index()] = old;
            return Err(e);
        }
        Ok(())
    }

    fn validate_involution_constraints(&self) -> Result<(), DialError> {
        for &(a, b) in &CognitiveOperator::INVOLUTION_PAIRS {
            let va = self.dials[a.index()].value;
            let vb = self.dials[b.index()].value;
            let divergence = va.abs_diff(vb);
            if divergence > DialSetting::MAX_INVOLUTION_DIVERGENCE {
                return Err(DialError::InvolutionDivergence {
                    pair: (a, b),
                    a: va,
                    b: vb,
                    divergence,
                });
            }
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_operator_identity() {
        for op in CognitiveOperator::ALL {
            assert_eq!(CognitiveOperator::CO0.compose(op), op);
            assert_eq!(op.compose(CognitiveOperator::CO0), op);
        }
    }

    #[test]
    fn test_involution_is_own_inverse() {
        for op in CognitiveOperator::ALL {
            assert_eq!(op.involute().involute(), op);
        }
    }

    #[test]
    fn test_self_duals() {
        for op in CognitiveOperator::SELF_DUALS {
            assert_eq!(op.involute(), op);
            assert!(op.is_self_dual());
        }
    }

    #[test]
    fn test_involution_pairs_not_self_dual() {
        for &(a, b) in &CognitiveOperator::INVOLUTION_PAIRS {
            assert_ne!(a, b);
            assert_eq!(a.involute(), b);
            assert_eq!(b.involute(), a);
            assert!(!a.is_self_dual());
            assert!(!b.is_self_dual());
        }
    }

    #[test]
    fn test_from_index_roundtrip() {
        for op in CognitiveOperator::ALL {
            assert_eq!(CognitiveOperator::from_index(op.index()), Some(op));
        }
        assert_eq!(CognitiveOperator::from_index(10), None);
    }

    #[test]
    fn test_dial_range() {
        assert!(DialSetting::new(2).is_err());
        assert!(DialSetting::new(3).is_ok());
        assert!(DialSetting::new(9).is_ok());
        assert!(DialSetting::new(10).is_err());
    }

    #[test]
    fn test_dial_involution_constraint() {
        // CO-2 at 3, CO-3 at 9 => divergence 6 > 4 => error
        let mut values = [6u8; 10];
        values[2] = 3;
        values[3] = 9;
        assert!(matches!(
            DialConfig::new(values),
            Err(DialError::InvolutionDivergence { .. })
        ));

        // CO-2 at 3, CO-3 at 7 => divergence 4 => ok
        values[3] = 7;
        assert!(DialConfig::new(values).is_ok());
    }

    #[test]
    fn test_admissibility_co0_diagonal_only() {
        let s = CognitiveStateId::new(
            CognitiveOperator::CO1,
            super::super::domains::Domain::Principled,
        );
        let t = CognitiveStateId::new(
            CognitiveOperator::CO2,
            super::super::domains::Domain::Principled,
        );
        assert!(CognitiveOperator::CO0.is_admissible(s, s));
        assert!(!CognitiveOperator::CO0.is_admissible(s, t));
    }
}
