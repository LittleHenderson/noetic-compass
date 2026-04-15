//! Cognitive Fractal Calculus — CAS v7.4 implementation
//!
//! Based on v6.1 Chapter 8: Noetic Fractal Calculus and Recursive Dynamics.
//! Fractals are finite sequences of Cognitive Operator indices (0-9) that
//! define higher-order operators on cognitive states.
//!
//! Key structures:
//! - `CognitiveFractal`: non-empty sequence ⟨k₁ : k₂ : ⋯ : kₙ⟩
//! - Composition: concatenation forming a monoid with ⟨0⟩ as identity
//! - Simplification: dual cancellation + identity elimination → canonical form
//! - Convergence: orbit computation, fixed points, classification

pub mod composition;
pub mod convergence;
pub mod fractal;
pub mod simplification;

pub use convergence::FractalClass;
pub use fractal::CognitiveFractal;
