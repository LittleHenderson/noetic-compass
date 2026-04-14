//! CAS Scoring Engine for Noetic Compass
//!
//! Implements the Cognitive Architecture System v7.4 (Corrected Edition)
//! scoring algorithms for AI psychological assessment.
//!
//! CRITICAL: This crate implements four corrections from the v7.4 review:
//! 1. Admissibility Relations for operators (Dk ⊆ I × I)
//! 2. RPM as section-retraction, NOT adjunction
//! 3. Noetic Coverage uses COUNIT εI, not unit ηI
//! 4. State space is open probability simplex Δ39°

pub mod algebra;
pub mod fractals;
pub mod inversions;
pub mod language;
pub mod metric;
pub mod ontology;
pub mod rpm;
pub mod scoring;

pub use casc_ir as compiler_ir;
pub use casc_syntax as compiler_syntax;
pub use casc_types as compiler_types;

#[cfg(feature = "python")]
pub mod python_bindings;

#[cfg(feature = "python")]
pub use python_bindings::cas_engine;
