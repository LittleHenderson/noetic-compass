//! Error types for algebraic operations.

use std::fmt;

/// Errors that can occur during algebraic operations on cognitive states.
#[derive(Debug, Clone, PartialEq)]
pub enum AlgebraError {
    /// Multiplication attempted ascending domain (E × C) instead of descent.
    DomainAscentViolation {
        left: String,
        right: String,
    },
    /// Division requires same-domain operands.
    CrossDomainDivision {
        left: String,
        right: String,
    },
    /// Result violates admissibility relation.
    AdmissibilityViolation {
        operator: String,
        source: String,
        target: String,
    },
    /// Simplex operation produced a degenerate state (all zeros).
    DegenerateState,
    /// Simplex operation produced a boundary state (some component <= 0).
    BoundaryViolation,
    /// Input vectors have wrong dimension (expected 40).
    DimensionMismatch {
        expected: usize,
        got: usize,
    },
}

impl fmt::Display for AlgebraError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::DomainAscentViolation { left, right } => {
                write!(f, "domain ascent violation: {left} × {right} would ascend")
            }
            Self::CrossDomainDivision { left, right } => {
                write!(f, "cross-domain division: {left} ÷ {right} requires same domain")
            }
            Self::AdmissibilityViolation { operator, source, target } => {
                write!(f, "admissibility violation: {operator} not admissible for ({source}, {target})")
            }
            Self::DegenerateState => write!(f, "degenerate state: all components zero"),
            Self::BoundaryViolation => write!(f, "boundary violation: result has non-positive component"),
            Self::DimensionMismatch { expected, got } => {
                write!(f, "dimension mismatch: expected {expected}, got {got}")
            }
        }
    }
}

impl std::error::Error for AlgebraError {}
