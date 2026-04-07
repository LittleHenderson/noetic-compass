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

pub mod ontology;
pub mod scoring;
pub mod rpm;
pub mod inversions;
pub mod fractals;
pub mod metric;
