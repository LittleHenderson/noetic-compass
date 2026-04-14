//! CAS v7.4 Algebraic Operations
//!
//! Implements multiplication (×) and division (÷) as algebraically generative
//! operations on cognitive states. Verified by formal proof to preserve:
//! - Admissibility relations
//! - Domain descent ordering
//! - Open simplex constraints (Δ°39)
//! - RPM section-retraction structure

pub mod drives;
pub mod error;
pub mod multiplication;
pub mod division;
pub mod simplex;

pub use drives::synthesize_drives;
pub use error::AlgebraError;
pub use multiplication::multiply_states;
pub use division::divide_states;
pub use simplex::{simplex_multiply, simplex_divide};
